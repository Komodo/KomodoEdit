#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
# 
# The contents of this file are subject to the Mozilla Public License
# Version 1.1 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
# 
# Software distributed under the License is distributed on an "AS IS"
# basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
# License for the specific language governing rights and limitations
# under the License.
# 
# The Original Code is Komodo code.
# 
# The Initial Developer of the Original Code is ActiveState Software Inc.
# Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
# ActiveState Software Inc. All Rights Reserved.
# 
# Contributor(s):
#   ActiveState Software Inc
# 
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
# 
# ***** END LICENSE BLOCK *****

import sys, os, re, string
import os.path
import tempfile
import threading
from xpcom import components, ServerException, COMException, nsError

import process
import koprocessutils
import which
import logging
from zope.cachedescriptors.property import LazyClassAttribute

log = logging.getLogger('koAppInfo')
#log.setLevel(logging.DEBUG)

#---- components
class KoAppInfoEx:

    _com_interfaces_ = [components.interfaces.koIAppInfoEx,
                        components.interfaces.nsIObserver]

    # Class variables.
    exenames = []  # List of possible executable names.
    defaultInterpreterPrefName = ''
    # When looking for executables, do version validation to ensure the version
    # is a valid and supported version and only store the valid versions.
    versionCheckExecutables = False
    haveLicense = 0
    buildNumber = 0
    localHelpFile = ''
    webHelpURL = ''
    _executables = None
    # The installationPath and executablePath can be used to manually override
    # the executables found and used by the AppInfo classes. Setting these will
    # manually inject the path as the first postition in the _executables list.
    _installationPath = ''
    _executablePath = ''

    # Lazily loaded class variables.
    @LazyClassAttribute
    def _prefs(self):
        return components.classes["@activestate.com/koPrefService;1"].\
                    getService(components.interfaces.koIPrefService).\
                    prefs
    @LazyClassAttribute
    def _userPath(self):
        return koprocessutils.getUserEnv().get("PATH", "").split(os.pathsep)

    def __init__(self):

        self._executable_is_valid_cache = {}

        # Listen for changes to the user environment. This must be called on the
        # main thread - bug 96530.
        @components.ProxyToMainThread
        def ProxyAddObserver(obj):
            # TODO: This will cause a leak - as we don't remove the observer, but
            #       since these are mostly services, it's not a big problem.
            obsSvc = components.classes["@mozilla.org/observer-service;1"]. \
                            getService(components.interfaces.nsIObserverService)
            obsSvc.addObserver(obj, "user_environment_changed", False)
        ProxyAddObserver(self)

        try:
            self._prefs.prefObserverService.addObserver(self, self.defaultInterpreterPrefName, 0)
        except Exception, e:
            log.warn("Unable to listen for preference change for: %r",
                     self.defaultInterpreterPrefName)

    def observe(self, subject, topic, data):
        if topic == self.defaultInterpreterPrefName:
            self.reset()
        elif topic == "user_environment_changed":
            # Re-create the user path and drop any caches.
            self._userPath = koprocessutils.getUserEnv().get("PATH", "").split(os.pathsep)
            self.reset()

    def reset(self):
        self._installationPath = ''
        self._executablePath = ''
        self._executables = None

    def haveModules(self, _):
        raise ServerException(nsError.NS_ERROR_NOT_IMPLEMENTED)

    # Unimplemented base stubs - to be implemented by the AppInfo class.
    def getVersionForBinary(self, exe):
        raise ServerException(nsError.NS_ERROR_NOT_IMPLEMENTED)
    def get_buildNumber(self):
        raise ServerException(nsError.NS_ERROR_NOT_IMPLEMENTED)
    def get_localHelpFile(self):
        raise ServerException(nsError.NS_ERROR_NOT_IMPLEMENTED)
    def get_webHelpURL(self):
        raise ServerException(nsError.NS_ERROR_NOT_IMPLEMENTED)

    def get_installationPath(self):
        if self._installationPath:
            # Return the manually set path.
            return self._installationPath
        # Else, go and look for it from prefs or on the system.
        installPaths = self.FindInstallationPaths()
        if installPaths:
            return installPaths[0]
        return ''

    def set_installationPath(self, path):
        if not os.path.isdir(path):
            log.warn("_installationPath should be a directory, but was: %r",
                     path)
            path = os.path.dirname(path)
        exepath = ""
        for installpath in (path, os.path.join(path, "bin")):
            for exename in self.exenames:
                if os.path.exists(os.path.join(installpath, exename)):
                    exepath = os.path.join(installpath, exename)
                    self.set_executablePath(exepath)
                    break
            if exepath:
                break

        # Reset the executable path as well.
        self.set_executablePath('')
        self._installationPath = path

    def get_executablePath(self):
        if self._executablePath:
            # Return the manually set path.
            return self._executablePath
        # Else, go and look for it from prefs or on the system.
        executables = self.FindExecutables()
        if executables:
            return executables[0]
        return ''

    def set_executablePath(self, path):
        # Remove any previous manually set executable.
        if self._executablePath and \
           self._executables and self._executables[0] == self._executablePath:
            self._executables = self._executables[1:]

        path = path or ''  # Ensure it's always a string (not None)
        self._executablePath = path
        self._installationPath = ''
        self._executables = self.FindExecutables()
        if path:
            self._executables.insert(0, path)

    def get_version(self):
        path = self.get_executablePath()
        if not path:
            raise ServerException(nsError.NS_ERROR_FILE_NOT_FOUND,
                                  "Can't find executable for %s" % (getattr(self, "exenames", ["?"])[0],))
        return self.getVersionForBinary(path)

    def _isValidExecutableVersion(self, exe):
        try:
            ver = self.getVersionForBinary(exe)
            versionParts = split_short_ver(ver, intify=True)
            #print '      versionParts: %r' % (versionParts, )
            if tuple(versionParts) < self.minVersionSupported:
                return False
            if hasattr(self, "maxVersionTuple"):
                if tuple(versionParts) > self.maxVersionTuple:
                    return False
            return True
        except AttributeError, ValueError:
            log.exception("Unable to determine version for executable %r", exe)
            return False
        except ServerException, ex:
            if ex.errno != nsError.NS_ERROR_FILE_NOT_FOUND:
                raise
        return False

    def _isValidExecutable(self, exe):
        """Return if the supplied exe is valid for Komodo usage."""
        # Class may optionally set a minVersionSupported and maxVersionTuple that
        # will be used to perform this check.
        if not hasattr(self, "minVersionSupported"):
            raise ServerException(nsError.NS_ERROR_NOT_IMPLEMENTED)
        if not exe:
            return False
        #print '  exe: %r' % (exe, )
        isvalid = self._executable_is_valid_cache.get(exe)
        if isvalid is None:
            try:
                isvalid = self._isValidExecutableVersion(exe)
            except Exception as ex:
                # Something went wrong; report that the executable is unusable
                log.exception("Failed to check version of executable %s" % (exe,))
                isvalid = False
            self._executable_is_valid_cache[exe] = isvalid
        #print '    isvalid: %r' % (isvalid, )
        return isvalid

    def get_valid_version(self):
        """Return if the version is valid for Komodo usage."""
        exe = self.get_executablePath()
        return self._isValidExecutable(exe)

    def isSupportedBinary(self, exe):
        """Return if the given exe version is valid for Komodo usage."""
        return self._isValidExecutable(exe)

    def getExecutableFromPrefs(self, prefset):
        interpPath = prefset.getString(self.defaultInterpreterPrefName, "")
        if interpPath and os.path.exists(interpPath):
            return interpPath
        return self.get_executablePath()

    def getExecutableFromDocument(self, koDoc):
        return self.getExecutableFromPrefs(koDoc.getEffectivePrefs())

    def _locateExecutables(self, exeName, interpreterPrefName=None, exts=None, paths=None):
        is_windows = sys.platform.startswith('win')
        if exts is None and is_windows:
            exts = ['.exe']
        if paths is None:
            paths = self._userPath
        executables = which.whichall(exeName, exts=exts, path=paths)
        if self.versionCheckExecutables:
            # Only want supported versions.
            # _isValidExecutable can throw exceptions, so don't use a
            # list comprehension
            valid_executables = []
            for exe in executables:
                try:
                    if self._isValidExecutable(exe):
                        valid_executables.append(exe)
                except ValueError:
                    pass
            executables = valid_executables
                    
        if interpreterPrefName:
            prefexe = self._prefs.getString(interpreterPrefName, "")
            if prefexe and os.path.exists(prefexe):
                if is_windows or sys.platform.startswith('darwin'):
                    prefexe_lc = prefexe.lower()
                    executables_lc = [x.lower() for x in executables]
                else:
                    prefexe_lc = prefexe
                    executables_lc = executables
                # Make sure the user-chosen interpreter is always first
                if prefexe_lc not in executables_lc:
                    executables.insert(0, prefexe)
                else:
                    found_prefexe = executables_lc.index(prefexe_lc)
                    if found_prefexe > 0:
                        del executables[found_prefexe]
                        executables.insert(0, prefexe)
        return [os.path.normcase(os.path.normpath(exe)) for exe in executables]

    def FindExecutables(self):
        if self._executables is None:
            self._executables = []
            for count, exename in enumerate(self.exenames):
                if count == 0:
                    # First time around, include the configured interpreter.
                    self._executables += self._locateExecutables(exename, self.defaultInterpreterPrefName)
                else:
                    self._executables += self._locateExecutables(exename)
        return self._executables

    def FindExecutablesAsync(self, callback):
        # Remeber the thread who called us.
        threadMgr = components.classes["@mozilla.org/thread-manager;1"]\
                        .getService(components.interfaces.nsIThreadManager)
        starting_thread = threadMgr.currentThread

        # The function run by the thread, passing results to the callback.
        def FindExecutablesThread(instance, callbackObj):
            executables = []
            result = components.interfaces.koIAsyncCallback.RESULT_ERROR
            try:
                executables = instance.FindExecutables()
                result = components.interfaces.koIAsyncCallback.RESULT_SUCCESSFUL
            except Exception, ex:
                log.warn("FindExecutables failed: %r", str(ex))

            class CallbackRunnable(object):
                """Used to fire callback on the original thread."""
                _com_interfaces_ = [components.interfaces.nsIRunnable]
                def __init__(self, handler, result, executables):
                    self.handler = handler
                    self.args = (result, executables)
                def run(self, *args):
                    self.handler.callback(*self.args)
                    # Null out values.
                    self.handler = None
                    self.args = None
            runnable = CallbackRunnable(callbackObj, result, executables)
            try:
                starting_thread.dispatch(runnable, components.interfaces.nsIThread.DISPATCH_SYNC)
            except COMException, e:
                log.warn("FindExecutables: callback failed: %s", str(e))

        # Start the thread.
        t = threading.Thread(target=FindExecutablesThread,
                             args=(self, callback),
                             name="koIAppInfoEx.FindExecutablesThread for %r" % (self.exenames[:1]))
        t.setDaemon(True)
        t.start()

    def FindInstallationPaths(self):
        exepaths = self.FindExecutables()
        return [self.getInstallationPathFromBinary(p) for p in exepaths]

    def getInstallationPathFromBinary(self, binaryPath):
        # The binary is expected to be in a bin/ subdirectory, except on
        # Windows when sometimes it isn't :\
        dirname = os.path.dirname(binaryPath)
        parent, leaf = os.path.split(dirname)
        if leaf == "bin":
            dirname = parent
        return dirname


class KoPerlInfoEx(KoAppInfoEx):
    _com_interfaces_ = [components.interfaces.koIAppInfoEx,
                        components.interfaces.koIPerlInfoEx,
                        components.interfaces.nsIObserver]
    _reg_clsid_ = "adb73505-eed5-46c5-8425-ce0bd8a5ec47"
    _reg_contractid_ = "@activestate.com/koAppInfoEx?app=Perl;1"
    _reg_desc_ = "Extended Perl Information"
    
    exenames = ["perl"]
    defaultInterpreterPrefName = "perlDefaultInterpreter"
    minVersionSupported = (5, 6)

    _havePerlCritic = None
    _perlCriticVersion = None

    # koIAppInfoEx routines
    def get_haveLicense(self):
        return 1

    _perlVersionFromPath = {}
    def getVersionForBinary(self, perlExe):
        if not os.path.exists(perlExe):
            raise ServerException(nsError.NS_ERROR_FILE_NOT_FOUND)
        if perlExe in self._perlVersionFromPath:
            return self._perlVersionFromPath.get(perlExe)
        argv = [perlExe, "-v"]
        p = process.ProcessOpen(argv, stdin=None)
        perlVersionDump, stderr = p.communicate()
        # Old perls look like: This is perl, version 5.005_03 built for MSWin32-x86-object
        # New perls look like: This is perl, v5.6.1 built for MSWin32-x86-multi-thread
        patterns = ["This is perl, v(?:ersion )?([0-9._]+)",
                    "This is perl \d+, version \d+, subversion \d+ \(v([0-9._]+)\)",
                    ]
        version = ''
        for ptn in patterns:
            perlVersionMatch = re.search(ptn, perlVersionDump)
            if perlVersionMatch:
                version = perlVersionMatch.group(1)
                break
        # Cache the result.
        self._perlVersionFromPath[perlExe] = version
        return version

    def get_buildNumber(self):
        argv = [self.get_executablePath(), "-v"]
        p = process.ProcessOpen(argv, stdin=None)
        versionDump, stderr = p.communicate()
        pattern = re.compile("Binary build (\d+(\.\d+)?)( \[\d+\])? provided by ActiveState")
        match = pattern.search(versionDump)
        if match:
            return int(match.group(1))
        else:
            # This is likely not an ActivePerl installation.
            raise ServerException(nsError.NS_ERROR_UNEXPECTED)
 
    def get_localHelpFile(self):
        """Return a path to a launchable local help file, else return None.
        If there is an html/index.html in the install directory found
        via `which perl`. An *Active*Perl installation could be found via the
        registry on Windows (see get_installed()) since this is the only type
        of Perl installation likely to have the html/index.html subfile.
        However the current suffices.
        """
        perlExe = self.get_executablePath()
        if perlExe:
            indexHtml = os.path.join(os.path.dirname(perlExe),
                                     "..", "html", "index.html")
            if os.path.isfile(indexHtml):
                return indexHtml
        return None

    def get_webHelpURL(self):
        """Return a web URL for help on this app, else return None."""
        return "http://docs.activestate.com/activeperl/"
    
    # koIPerlInfoEx routines
    def getExtraPaths(self):
        perlExtraPaths = self._prefs.getString("perlExtraPaths", "")
        if not perlExtraPaths:
            return []
        if sys.platform.startswith("win"):
            perlExtraPaths = string.replace(perlExtraPaths, '\\', '/')
        perlExtraPaths = [x.strip() for x in perlExtraPaths.split(os.pathsep)]
        return [x for x in perlExtraPaths if x]

    def haveModules(self, modules):
        perlExe = self.get_executablePath()
        if not perlExe:
            return False
        argv = [perlExe] \
               + ["-I" + path for path in self.getExtraPaths()] \
               + ["-M" + mod for mod in modules] \
               + ["-e1"]
        p = process.ProcessOpen(argv, stdin=None)
        stdout, stderr = p.communicate()
        retval = p.wait()
        if retval: # if returns non-zero, then don't have that module
            return 0
        else:
            return 1

    def isPerlCriticInstalled(self, forceCheck=False):
        if self._havePerlCritic is None or forceCheck:
            self._havePerlCritic = bool(self.haveModules(["criticism", "Perl::Critic"]))
        return self._havePerlCritic

    def getPerlCriticVersion(self):
        if self._perlCriticVersion is not None or not self.isPerlCriticInstalled():
            return self._perlCriticVersion
        perlExe = self.get_executablePath()
        argv = [perlExe, "-MPerl::Critic", '-e', 'print $Perl::Critic::VERSION']
        p = process.ProcessOpen(argv, stdin=None)
        stdout, stderr = p.communicate()
        retval = p.wait()
        m = re.compile(r'^(\d+(?:\.\d*)?)').match(stdout)
        if m:
            self._perlCriticVersion = float(m.group(1))
        else:
            log.error("Can't find a version # in %s", stdout)
        return self._perlCriticVersion
        
        

class KoPythonCommonInfoEx(KoAppInfoEx):
    # We only want valid Python executables, otherwise we end up with a mix of
    # Python2 and Python3 executables.
    versionCheckExecutables = True

    # koIAppInfoEx routines
    def get_haveLicense(self):
        return 1

    def getVersionForBinary(self, pythonExe):
        """Get the $major.$minor version (as a string) of the current
        Python executable. Returns the empty string if cannot determine
        version.
        
        Dev Notes:
        - Specify cwd to avoid accidentally running in a dir with a
          conflicting Python DLL.
        """
        if not os.path.exists(pythonExe):
            raise ServerException(nsError.NS_ERROR_FILE_NOT_FOUND)

        version = ""

        if pythonExe is None:
            return version
        cwd = os.path.dirname(pythonExe)
        env = koprocessutils.getUserEnv()

        argv = [pythonExe, "-c", "import sys; sys.stdout.write(sys.version)"]
        p = process.ProcessOpen(argv, cwd=cwd, env=env, stdin=None)
        stdout, stderr = p.communicate()
        if not p.returncode:
            # Some example output:
            #   2.0 (#8, Mar  7 2001, 16:04:37) [MSC 32 bit (Intel)]
            #   2.5.2 (r252:60911, Mar 27 2008, 17:57:18) [MSC v.1310 32 bit (Intel)]
            #   2.6rc2 (r26rc2:66504, Sep 26 2008, 15:20:44) [MSC v.1500 32 bit (Intel)]
            version_re = re.compile(r"^(\d+\.\d+)")
            match = version_re.match(stdout)
            if match:
                version = match.group(1)

        return version

    def get_localHelpFile(self):
        """Return a path to a launchable local help file, else return None.
        Windows:
            If there is a
            'HKLM/Software/Python/PythonCore/<major>.<minor>/Help/Main Python Documentation'
            and if the identified file exists.
        Linux/Solaris:
            If there is an html/index.html in the install directory found
            via `which python`.
        """
        if sys.platform.startswith("win"):
            import _winreg
            preferred_version = self.get_version()
            preferred_result = None
            # Versions will be a list of (version, regkey)
            versions = []
            docKeys = ("Main Python Documentation",
                       "Pythonwin Reference")
            for regkey in ("SOFTWARE\\Python\\PythonCore",
                           "SOFTWARE\\Wow6432Node\\Python\\PythonCore"):
                try:
                    pythonCoreKey = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE,
                                                    "SOFTWARE\\Python\\PythonCore")
                except EnvironmentError:
                    continue
                # get a list of each installed version 
                index = 0
                while 1:
                    try:
                        version = _winreg.EnumKey(pythonCoreKey, index)
                        versions.append((version, regkey))
                        if version == preferred_version:
                            preferred_result = (version, regkey)
                    except EnvironmentError:
                        break
                    index += 1
            if not versions:
                return None
            # try to find a existing help file (prefering the latest
            # installed version)
            versions.sort()
            if preferred_result:
                # Ensure the ensure's selected Python version is the last one,
                # bug 88547.
                versions.append(preferred_result)
            versions.reverse()
            for version, regkey in versions:
                try:
                    helpFileKeyStr = "%s\\%s\\Help" % (regkey, version)
                    helpFileKey = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE,
                                                  helpFileKeyStr)
                    for docKeyStr in docKeys:
                        try:
                            docKey = _winreg.OpenKey(helpFileKey, docKeyStr)
                        except WindowsError:
                            continue
                        try:
                            helpFile, keyType = _winreg.QueryValueEx(docKey, "")
                        except WindowsError:
                            continue
                        if os.path.isfile(helpFile):
                            return helpFile
                except EnvironmentError:
                    pass
            return None
        else:
            try:
                pythonExe = which.which(self.exenames[0], path=self._userPath)
            except which.WhichError:
                return None
            indexHtml = os.path.join(os.path.dirname(pythonExe),
                                     "..", "html", "index.html")
            if os.path.isfile(indexHtml):
                return indexHtml
            else:
                return None

    def get_webHelpURL(self):
        """Return a web URL for help on this app, else return None."""
        return "http://docs.activestate.com/activepython/"

    def haveModules(self, modules):
        interpreter = self.get_executablePath()
        if not interpreter:
            log.info("%s: path not set", self.exenames[0])
            return False
        argv = [interpreter, '-c',
                ' '.join(['import ' + str(mod) + ';' for mod in modules])]
        env = koprocessutils.getUserEnv()
        try:
            p = process.ProcessOpen(argv, env=env, stdin=None)
        except:
            log.error("KoPythonCommonInfoEx.haveModules: Failed to run cmd %s", argv)
            return False

        retval = p.wait()
        return not retval

class KoPythonInfoEx(KoPythonCommonInfoEx):
    _reg_clsid_ = "{b76bc2ee-261e-4597-b1ef-446e9bb89d7c}"
    _reg_contractid_ = "@activestate.com/koAppInfoEx?app=Python;1"
    _reg_desc_ = "Extended Python Information"
    exenames = ["python", "python2"]
    defaultInterpreterPrefName = "pythonDefaultInterpreter"
    minVersionSupported = (2, 4)
    maxVersionTuple = (2, 99, 99)

class KoPython3InfoEx(KoPythonCommonInfoEx):
    _reg_clsid_ = "{e98c16e6-0b9f-4f11-8505-5012555a19b2}"
    _reg_contractid_ = "@activestate.com/koAppInfoEx?app=Python3;1"
    _reg_desc_ = "Extended Python3 Information"
    exenames = ["python3", "python"]
    defaultInterpreterPrefName = "python3DefaultInterpreter"
    minVersionSupported = (3, 0)
    maxVersionTuple = (3, 99, 99)

    def get_webHelpURL(self):
        """Return a web URL for help on this app, else return None."""
        return "http://docs.activestate.com/activepython/3.2/"

#---- components

class KoRubyInfoEx(KoAppInfoEx):
    _reg_clsid_ = "{e1ce6f0d-839e-480a-b131-36de0dc35965}"
    _reg_contractid_ = "@activestate.com/koAppInfoEx?app=Ruby;1"
    _reg_desc_ = "Extended Ruby Information"

    exenames = ["ruby"]
    defaultInterpreterPrefName = "rubyDefaultInterpreter"
    minVersionSupported = (1, 8, 4)

    def get_haveLicense(self):
        return 1

    def getVersionForBinary(self, rubyExe):
        if not os.path.exists(rubyExe):
            raise ServerException(nsError.NS_ERROR_FILE_NOT_FOUND)
        argv = [rubyExe, "-v"]
        p = process.ProcessOpen(argv, stdin=None)
        rubyVersionDump, stderr = p.communicate()
        pattern = re.compile("ruby ([\w\.]+) ")
        match = pattern.search(rubyVersionDump)
        if match:
            return match.group(1)
        else:
            msg = "Can't find a version in `%s -v` output of '%s'/'%s'" % (rubyExe, rubyVersionDump, stderr)
            raise ServerException(nsError.NS_ERROR_UNEXPECTED, msg)
    
    def get_localHelpFile(self):
        #XXX Return rdoc or something
        return None

    def get_webHelpURL(self):
        """Return a web URL for help on this app, else return None."""
        return "http://www.ruby-doc.org/"


class KoTclInfoEx(KoAppInfoEx):
    _com_interfaces_ = [components.interfaces.koIAppInfoEx,
                        components.interfaces.koITclInfoEx,
                        components.interfaces.nsIObserver]
    _reg_clsid_ = "DF64A66F-FD69-4F5E-92B2-B3C9F8638F66"
    _reg_contractid_ = "@activestate.com/koAppInfoEx?app=Tcl;1"
    _reg_desc_ = "Extended Tcl Information"

    exenames = ["tclsh"]
    defaultInterpreterPrefName = "tclshDefaultInterpreter"
    minVersionSupported = (8, 4)

    # koIAppInfoEx routines
    def _isInstallationLicensed(self, installationPath):
        return 1

    def get_haveLicense(self):
        return self._isInstallationLicensed(self.get_installationPath())

    def getVersionForBinary(self, tclshExe):
        if not os.path.exists(tclshExe):
            raise ServerException(nsError.NS_ERROR_FILE_NOT_FOUND)
        argv = [tclshExe]
        p = process.ProcessOpen(argv)
        p.stdin.write("puts [info tclversion]\n")
        stdout, stderr = p.communicate()
        pattern = re.compile("([\w\.]+)")
        match = pattern.search(stdout)
        if match:
            return match.group(1)
        else:
            msg = "Can't determine tcl version\n  stdout: %r\n  stderr: %r" % (stdout, stderr)
            raise ServerException(nsError.NS_ERROR_UNEXPECTED, msg)

    def get_localHelpFile(self):
        """Return a path to a launchable local help file, else return None.
        Windows:
            If there is a 'HKLM\Software\ActiveState\ActiveTcl\<CurVer>\Help'
            and if the identified file exists.
        Linux/Solaris:
            Nada. Just man files, which I don't consider "launchable" in a
            browser context. XXX Perhaps they *are* in Nautilus? 
        """
        if sys.platform.startswith("win"):
            import _winreg
            # get the base ActiveTcl registry key
            try:
                activeTclKey = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE,
                                               "SOFTWARE\\ActiveState\\ActiveTcl")
            except EnvironmentError:
                return None
            # get a list of each installed version 
            versions = []
            index = 0
            while 1:
                try:
                    versions.append(_winreg.EnumKey(activeTclKey, index))
                except EnvironmentError:
                    break
                index += 1
            # try to find a existing help file (prefering the latest
            # installed version)
            versions.sort()
            versions.reverse()
            for version in versions:
                try:
                    helpFileKey = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE,
                        "SOFTWARE\\ActiveState\\ActiveTcl\\%s\\Help" % version)
                    helpFile, keyType = _winreg.QueryValueEx(helpFileKey, "")
                    if os.path.isfile(helpFile):
                        return helpFile
                except EnvironmentError:
                    pass
        return None

    def get_webHelpURL(self):
        return "http://docs.activestate.com/activetcl/"

    def get_tclsh_path(self):
        return self.get_executablePath()

    def get_wish_path(self):
        wish_exes = self._locateExecutables("wish", "wishDefaultInterpreter")
        if wish_exes:
            return wish_exes[0]
        return None

class KoPHPInfoInstance(KoAppInfoEx):
    _com_interfaces_ = [components.interfaces.koIAppInfoEx,
                        components.interfaces.koIPHPInfoEx,
                        components.interfaces.nsIObserver]
    _reg_clsid_ = "E2066A3A-FC6D-4157-961E-E03C020594BE"
    _reg_contractid_ = "@activestate.com/koPHPInfoInstance;1"
    _reg_desc_ = "PHP Information"

    exenames = ['php', 'php4', 'php-cli', 'php-cgi']
    defaultInterpreterPrefName = "phpDefaultInterpreter"
    minVersionSupported = (4, 4)

    # the purpose of KoPHPInfoInstance is to be able to define
    # what executable and ini path are used without prefs getting
    # in the way.  If you want to use prefs, use koPHPInfoEx.
    def __init__(self):
        KoAppInfoEx.__init__(self)
        self._executable = None
        self._info = {}
        try:
            self._prefs.prefObserverService.addObserver(self, "phpConfigFile", 0)
        except Exception, e:
            log.warn("Unable to listen for preference change for: 'phpConfigFile'")

    def observe(self, subject, topic, data):
        KoAppInfoEx.observe(self, subject, topic, data)
        if topic == "phpConfigFile":
            self.reset()

    def reset(self):
        KoAppInfoEx.reset(self)
        self._info = {}

    def _getInterpreterConfig(self):
        if 'cfg_file_path' in self._info:
            return self._info['cfg_file_path']
        return None

    def _GetPHPOutputAndError(self, phpCode, php=None):
        """Run the given PHP code and return the output.

        If some error occurs then the error is logged and the empty
        string is returned. (Basically we are taking the position that
        PHP is unreliable.)
        """
        if php is None:
            php = self.get_executablePath()
        if not php:
            # XXX Would be better, IMO, to raise an exception here.
            return None, "No PHP executable could be found."
        env = koprocessutils.getUserEnv()
        ini = self._getInterpreterConfig()
        if ini:
            env["PHPRC"] = ini
        argv = [php, '-q']
        
        if not "PHPRC" in env:
            # php will look in cwd for php.ini also.
            cwd = os.path.dirname(php)
        else:
            cwd = None


        fd, filepath = tempfile.mkstemp(suffix=".php")
        try:
            os.write(fd, phpCode)
            os.close(fd)
            argv.append(filepath)
            try:
                p = process.ProcessOpen(argv, cwd=cwd, env=env)
            except OSError, e:
                if e.errno == 0 or e.errno == 32:
                    # this happens if you are playing
                    # in prefs and change the executable, but
                    # not the ini file (ie ini is for a different
                    # version of PHP)
                    log.error("Caught expected PHP execution error, don't worry be happy: %s", e.strerror)
                else:
                    log.error("Caught PHP execution exception: %s", e.strerror)
                return None, e.strerror
            try:
                p.wait(5)
            except process.ProcessError:
                # Timed out.
                log.error("PHP command timed out: %r", argv)
                return None, "PHP interpreter did not return in time."
            stdout = p.stdout.read()
            stderr = p.stderr.read()
            return stdout.strip(), stderr.strip()
        finally:
            os.remove(filepath)

    def _GetPHPOutput(self, phpCode):
        """Run the given PHP code and return the output.

        If some error occurs then the error is logged and the empty
        string is returned. (Basically we are taking the position that
        PHP is unreliable.)
        """
        return self._GetPHPOutputAndError(phpCode)[0]

    def _parsedOutput(self, out):
        """Parse the given output from running PHP.

        If it looks like there is no relevant output, the empty string
        is returned.

        XXX This makes the assumption that all interesting output is on
            one line because only the last non-empty line is used. Any
            leading lines are presumed to be load time errors from PHP.
        """
        if not out: return ""
        # If PHP has load time errors, such as failure loading extension
        # dll's, it spits out a bunch of errors first, then the last
        # line has what we're asking for.  So only get the last line of
        # output.
        lines = re.split('\r\n|\n|\r',out) #XXX should use .splitlines() here
        #XXX Shane, you are doing exactly what you think you are here.
        #    If "out" is a bunch of error lines followed by a blank line
        #    then the last error line is returned here.
        # depending on version of php, we may have a
        # blank last line, check for it.
        if not lines[-1]:
            del lines[-1]
            if not lines: return ""
        return lines[-1]
        
    def _GetPHPConfigVar(self, varName):
        # always output a newline, some versions of php need it
        out = self._GetPHPOutput("<?php echo(get_cfg_var('%s').\"\\n\"); ?>"\
                                  % varName)
        return self._parsedOutput(out)
    
    def _GetPHPIniVar(self, varName):
        # always output a newline, some versions of php need it
        out = self._GetPHPOutput("<?php echo(ini_get('%s').\"\\n\"); ?>"\
                                  % varName)
        return self._parsedOutput(out)

    def _findInstallationExecutables(self, paths=None, defaultInterpreterPrefName=None):
        return self._locateExecutables("php", defaultInterpreterPrefName, paths=paths) + \
                            self._locateExecutables('php-cgi', paths=paths) + \
                            self._locateExecutables('php4',    paths=paths) + \
                            self._locateExecutables('php-cli', paths=paths)

    # koIAppInfoEx routines
    def set_executablePath(self, exe):
        KoAppInfoEx.set_executablePath(self, exe)
        self._info = {}

    def set_installationPath(self, path):
        KoAppInfoEx.set_installationPath(self, path)
        self._info = {}

    def get_haveLicense(self):
        return 1

    def getVersionForBinary(self, phpExe):
        if not os.path.exists(phpExe):
            raise ServerException(nsError.NS_ERROR_FILE_NOT_FOUND)
        out, err = self._GetPHPOutputAndError(
            "<?php echo(phpversion().\"\\n\"); ?>", php=phpExe)
        if not out:
            # (Bug 73485) With some esp. borked PHP setups, even
            # getting the version dies. Logging this case is the least
            # we can do. A better (but more onerous to verify as being
            # safe) change would be to pass up the error and show it
            # in the using UI (e.g. the PHP prefs panel).
            log.error("could not determine PHP version number for "
                      "'%s':\n----\n%s\n----",
                      self.get_executablePath(), err)
        return self._parsedOutput(out)

    def get_valid_version(self):
        # Versions of php that xdebug works with, highest versions must
        # be first.  5.0.0-5.0.1 and before 4.3.10 dont work due to
        # missing symbols.
        if not KoAppInfoEx.get_valid_version(self):
            return False
        version = self.get_version()
        if version:
            try:
                versionParts = split_short_ver(version, intify=True)
                if tuple(versionParts) >= (5,0,0) and \
                   tuple(versionParts) < (5,0,3):
                    return False
            except AttributeError:
                pass
            except ServerException, ex:
                if ex.errno != nsError.NS_ERROR_FILE_NOT_FOUND:
                    raise
        return True

    def get_localHelpFile(self):
        """Return a path to a launchable local help file, else return None.
        Nada for PHP. There is no *standard* local documentation link or any
        real de facto standard.
        """
        return None

    def get_webHelpURL(self):
        return "http://www.php.net/docs.php"

    # additional koIPHPInfoEx routines
    # XXX php takes a directory as an argument to define where to find
    # the ini file, but if you query php for this, it returns a file
    def get_cfg_file_path(self):
        if 'cfg_file_path' not in self._info:
            out = self._GetPHPConfigVar("cfg_file_path")
            self._info['cfg_file_path'] =  self._parsedOutput(out)
        return self._info['cfg_file_path']
    
    def set_cfg_file_path(self,path):
        self._info = {}
        if path:
            self._info['cfg_file_path'] = path
        
    def get_include_path(self):
        if 'include_path' not in self._info:
            out = self._GetPHPIniVar("include_path")
            self._info['include_path'] =  self._parsedOutput(out)
        return self._info['include_path']

    def GetIncludePathArray(self):
        includePath = self.get_include_path().split(os.pathsep)
        # cull out any empty entries (resulting from, say, include_path="a;;b")
        includePath = [path for path in includePath if path]
        return includePath
    
    def get_extension_dir(self):
        if 'extension_dir' not in self._info:
            out = self._GetPHPIniVar("extension_dir")
            self._info['extension_dir'] = self._parsedOutput(out)
        return self._info['extension_dir']

    def autoConfigureDebugger(self):
        # get the phpconfigurator and autoconfigure
        if self._prefs.getString("phpConfigFile", ""):
            if not self.get_isDebuggerExtensionLoadable():
                return "Unable to load XDebug"
            return "" 
        configure = components.classes["@activestate.com/koPHPConfigurator;1"].\
                createInstance(components.interfaces.koIPHPConfigurator)
        return configure.autoConfigure(self)
        
    def get_isDebuggerExtensionLoadable(self):
        # always output a newline, some versions of php need it
        if 'xdebug' not in self._info:
            out = self._GetPHPOutput("<?php echo extension_loaded('xdebug')?\"Yes\\n\":\"No\\n\"; ?>")
            self._info['xdebug'] = self._parsedOutput(out)
        return self._info['xdebug'] == "Yes"

    def get_sapi(self):
        # always output a newline, some versions of php need it
        if 'sapi' not in self._info:
            out = self._GetPHPOutput("<?php echo(php_sapi_name().\"\\n\"); ?>")
            self._info['sapi'] = self._parsedOutput(out)
        return self._info['sapi']

class KoPHPInfoEx(KoPHPInfoInstance):
    _reg_clsid_ = "ea1519a8-4e4d-4767-aec4-2f0342c33e7a"
    _reg_contractid_ = "@activestate.com/koAppInfoEx?app=PHP;1"
    _reg_desc_ = "PHP Information"

    def _getInterpreterConfig(self):
        phpConfigFile = None
        # Not using the proxied pref observer due to getting Komodo lockups
        # at start time:
        # http://bugs.activestate.com/show_bug.cgi?id=74474
        phpConfigFile = self._prefs.getString("phpConfigFile", "")
        return phpConfigFile or KoPHPInfoInstance._getInterpreterConfig(self)

    def _get_namedExe(self, name):
        exe = self.get_executablePath()
        if self.get_sapi()[:3] != name:
            phpAppInfoEx = components.classes["@activestate.com/koPHPInfoInstance;1"].\
                    createInstance(components.interfaces.koIPHPInfoEx);
            # find the cgi executable
            avail = self._findInstallationExecutables(paths=[os.path.dirname(exe)])
            if len(avail) == 1: # only have a cli executable
                return None
            avail = [x for x in avail if x is not exe]
            exe = None
            for e in avail:
                phpAppInfoEx.executablePath = e
                if phpAppInfoEx.sapi[:3] == name:
                    return e
        return exe
        
    def get_cliExecutable(self):
        if 'cli-executable' not in self._info:
            cli_exe = self._get_namedExe('cli')
            self._info['cli-executable'] = cli_exe
            return cli_exe
        return self._info.get('cli-executable')
    
    def get_cgiExecutable(self):
        if 'cgi-executable' not in self._info:
            cgi_exe = self._get_namedExe('cgi')
            self._info['cgi-executable'] = cgi_exe
            return cgi_exe
        return self._info.get('cgi-executable')

class KoNodeJSInfoEx(KoAppInfoEx):
    _reg_clsid_ = "{d5f5f120-2322-4cdf-8fbf-cd4a5861cc5a}"
    _reg_contractid_ = "@activestate.com/koAppInfoEx?app=NodeJS;1"
    _reg_desc_ = "Extended NodeJS Information"

    exenames = ["node"]
    defaultInterpreterPrefName = "nodejsDefaultInterpreter"
    minVersionSupported = (0, 4)

    def getVersionForBinary(self, nodejsExe):
        if not os.path.exists(nodejsExe):
            raise ServerException(nsError.NS_ERROR_FILE_NOT_FOUND)
        argv = [nodejsExe, "-v"]
        p = process.ProcessOpen(argv, stdin=None)
        nodejsVersionDump, stderr = p.communicate()
        pattern = re.compile("v([\w\.]+)")
        match = pattern.match(nodejsVersionDump)
        if match:
            return match.group(1)
        else:
            msg = "Can't find a version in `%s -v` output of '%s'/'%s'" % (nodejsExe, nodejsVersionDump, stderr)
            raise ServerException(nsError.NS_ERROR_UNEXPECTED, msg)
    
    def get_localHelpFile(self):
        return None

    def get_webHelpURL(self):
        """Return a web URL for help on this app, else return None."""
        return "http://www.nodejs.org/docs/" + "v" + self.get_version()
        # On newer systems the docs are at nodejs.org/docs/<version>/api,
        # but this varies for older versions, and could change in the future.

class KoCVSInfoEx(KoAppInfoEx):
    _reg_clsid_ = "C3A7A887-D0D3-426A-8C67-2CC3E2946636"
    _reg_contractid_ = "@activestate.com/koAppInfoEx?app=CVS;1"
    _reg_desc_ = "CVS Information"

    exenames = ["cvs"]
    defaultInterpreterPrefName = "cvsExecutable"

    # koIAppInfoEx routines
    def get_haveLicense(self):
        return 1

    def getVersionForBinary(self, cvsExe):
        """A CVS version include not only the standard 1.2.3-type numbers
        but also the "build family", of which CVSNT is a different one.
        For example:
            1.11.2 CVS
            1.11.1.3 CVSNT
        Returns None if the version cannot be determined.
        """
        if not os.path.exists(cvsExe):
            raise ServerException(nsError.NS_ERROR_FILE_NOT_FOUND)
        p = process.ProcessOpen([cvsExe, '-v'], stdin=None)
        output, error = p.communicate()
        retval = p.returncode
        
        versionRe = re.compile(r'\((?P<family>.+?)\)\s+(?P<version>[\d\.\w]+?)[\s\-]',
                               re.MULTILINE)
        match = versionRe.search(output)
        if match:
            version = "%s %s" % (match.group('version'),
                                 match.group('family'))
            return version
        else:
            log.warn('Could not determine CVS version [%s] "%s"', cvsExe, output)
            return None
 

# ------------ Utility functions ---------------- #

_short_ver_re = re.compile("(\d+)(\.\d+)*([a-z](\d+)?)?")
def split_short_ver(ver_str, intify=False, pad_zeros=None):
    """Parse the given version into a tuple of "significant" parts.

    @param intify {bool} indicates if numeric parts should be converted
        to integers.
    @param pad_zeros {int} is a number of numeric parts before any
        "quality" letter (e.g. 'a' for alpha).
   
    >>> split_short_ver("4.1.0")
    ('4', '1', '0')
    >>> split_short_ver("1.3a2")
    ('1', '3', 'a', '2')
    >>> split_short_ver("1.3a2", intify=True)
    (1, 3, 'a', 2)
    >>> split_short_ver("1.3a2", intify=True, pad_zeros=3)
    (1, 3, 0, 'a', 2)
    >>> split_short_ver("1.3x", intify=True)
    (1, 3, 'x')
    >>> split_short_ver("1.3x", intify=True, pad_zeros=3)
    (1, 3, 0, 'x')
    >>> split_short_ver("1.3", intify=True, pad_zeros=3)
    (1, 3, 0)
    >>> split_short_ver("1", pad_zeros=3)
    ('1', '0', '0')
    """
    def isint(s):
        try:
            int(s)
        except ValueError:
            return False
        else:
            return True
    def do_intify(s):
        try:
            return int(s)
        except ValueError:
            return s

    if not _short_ver_re.match(ver_str):
        raise ValueError("%r is not a valid short version string" % ver_str)

    hit_quality_bit = False
    bits = []
    for bit in re.split("(\.|[a-z])", ver_str):
        if len(bit) == 0 or bit == '.':
            continue
        if intify:
            bit = do_intify(bit)
        if pad_zeros and not hit_quality_bit and not isint(bit):
            hit_quality_bit = True
            while len(bits) < pad_zeros:
                bits.append(not intify and "0" or 0)
        bits.append(bit)
    if pad_zeros and not hit_quality_bit:
        while len(bits) < pad_zeros:
            bits.append(not intify and "0" or 0)
    return tuple(bits)


#---- self test code

if __name__ == "__main__":
    def getCOMAttribute(obj, property, default = 'not implemented'):
        try:
            return getattr(obj, property)
        except COMException, e:
            if e.errno == nsError.NS_ERROR_NOT_IMPLEMENTED:
                return default
            else:
                raise
                    
    for app in ["Perl", "Python", "PHP"]:
        appInfoExe = components.classes["@activestate.com/koAppInfoEx?app=%s;1"%app]\
                   .createInstance()
        
        installations = appInfoExe.FindInstallationPaths()
        for installation in installations:
            appInfoExe.installationPath = installation
            print "+------ %s installation: %s" % (app, appInfoExe.installationPath)
            print "| haveLicense: %s" % getCOMAttribute(appInfoExe, 'haveLicense')
            print "| executable location: %s" % getCOMAttribute(appInfoExe, 'executablePath')
            print "| version: %s" % getCOMAttribute(appInfoExe, 'version')
            print "| localHelpFile: %s" % getCOMAttribute(appInfoExe, 'localHelpFile')
            print "| webHelpURL: %s" % getCOMAttribute(appInfoExe, 'webHelpURL')
            
            if app == "PHP":
                print "|\t+------ PHP extra features ------"
                print "|\t| cfg_file_path: %s" % appInfoExe.cfg_file_path
                print "|\t| include_path: %s %s" % (appInfoExe.include_path,
                                                    appInfoExe.GetIncludePathArray())
                print "|\t| extension_dir: %s" % appInfoExe.extension_dir
                print "|\t+---------------------------------"
            
            print "+---------------------------------"
    


