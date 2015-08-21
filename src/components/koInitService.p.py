#!python
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

# Initialization Services for Komodo

# #if BUILD_FLAVOUR == "dev"
# Record when the module was first loaded.
import time
_module_load_time = time.time()
import benchmark
benchmark.initialise(_module_load_time)   # Base time (i.e. time 0)
# #endif

# mozilla sets LC_NUMERIC which messes up the python parser if the locale
# uses something other than a period for decimal seperator.  We reset it
# here to make all consecutive files get parsed correctly.
# bug 30327
import locale
locale.setlocale(locale.LC_NUMERIC, 'C')

import sys
import os
import re
from pprint import pprint
import logging

if sys.platform == "win32":
    # Force the import of the correct PyWin32 DLLs on Windows.
    # PyWin32 has special shims for importing pywintypes and pythoncom
    # directly to ensure that the right pywintypesXY.dll and pythoncomXY.dll
    # get found and loaded. If our Python attempts to load these DLLs via,
    # say, "import win32api" -- which will use LoadLibrary(DLLFILE) -- then
    # we are screwed: because an incompatible system one might get picked up.
    #
    try:
        import pywintypes
        import pythoncom
    except ImportError:
        pass

from xpcom import components, nsError, ServerException, COMException


# Set lazily after "koLoggingService" has mucked with logging's internals.
log = None



#---- Startup support routines

if os.environ.has_key("KO_PYXPCOM_PROFILE"):
    # insert the xpcom tracer
    import pyxpcomProfiler

# #if BUILD_FLAVOUR == "dev"
if os.environ.has_key("KO_DEBUG_PORT"):
    try:
        from dbgp.client import brk
        brk(port=int(os.environ["KO_DEBUG_PORT"]))
    except Exception:
        log.exception("trying to get env")
        pass
# #endif

#----- interal support routines

def _isdir(dirname):
    """os.path.isdir() doesn't work for UNC mount points. Fake it."""
    if sys.platform[:3] == 'win' and dirname[:2] == r'\\':
        if os.path.exists(dirname):
            return os.path.isdir(dirname)
        try:
            os.listdir(dirname)
        except WindowsError:
            return 0
        else:
            return os.path.ismount(dirname)
    else:
        return os.path.isdir(dirname)


def _mkdir(newdir):
    """works the way a good mkdir should :)
        - already exists, silently complete
        - regular file in the way, raise an exception
        - parent directory(ies) does not exist, make them as well
    """
    if _isdir(newdir):
        pass
    elif os.path.isfile(newdir):
        raise OSError("a file with the same name as the desired " \
                      "dir, '%s', already exists." % newdir)
    else:
        head, tail = os.path.split(newdir)
        if head and not _isdir(head):
            _mkdir(head)
        #print "_mkdir %s" % repr(newdir)
        if tail:
            os.mkdir(newdir)


def _copy(src, dst, overwriteExistingFiles=True, ignoreErrors=False,
          ignoredDirNames=None):
    """works the way a good copy should :)
        - no source, raise an exception
        - destination directory, make a file in that dir named after src
        - source directory, recursively copy the directory to the destination
        - filename wildcarding allowed
        - when overwriteExistingFiles is False, if the destination file already
          exists it won't overwrite it.
        - when ignoreErrors is True, will log any exceptions when trying to
          copy files and then continue on.
    NOTE:
        - This copy CHANGES THE FILE ATTRIBUTES.
    """
    import string, glob, shutil

    assert src != dst, "You are try to copy a file to itself. Bad you! "\
                       "src='%s' dst='%s'" % (src, dst)
    # determine if filename wildcarding is being used
    # (only raise error if non-wildcarded source file does not exist)
    if string.find(src, '*') != -1 or \
       string.find(src, '?') != -1 or \
       string.find(src, '[') != -1:
        usingWildcards = 1
        srcFiles = glob.glob(src)
    else:
        usingWildcards = 0
        srcFiles = [src]

    for srcFile in srcFiles:
        if os.path.isfile(srcFile):
            if usingWildcards:
                srcFileHead, srcFileTail = os.path.split(srcFile)
                srcHead, srcTail = os.path.split(src)
                dstHead, dstTail = os.path.split(dst)
                if dstTail == srcTail:
                    dstFile = os.path.join(dstHead, srcFileTail)
                else:
                    dstFile = os.path.join(dst, srcFileTail)
            else:
                dstFile = dst
            dstFileHead, dstFileTail = os.path.split(dstFile)
            if dstFileHead and not _isdir(dstFileHead):
                _mkdir(dstFileHead)
            if _isdir(dstFile):
                dstFile = os.path.join(dstFile, os.path.basename(srcFile))
            #print "copy %s %s" % (srcFile, dstFile)
            mode = (os.access(srcFile, os.X_OK) and 0755 or 0644)
            if os.path.isfile(dstFile):
                if not overwriteExistingFiles:
                    continue
                # make sure 'dstFile' is writeable
                os.chmod(dstFile, mode)
            shutil.copy(srcFile, dstFile)
            # make the new 'dstFile' writeable
            os.chmod(dstFile, mode)
        elif _isdir(srcFile):
            if ignoredDirNames and os.path.basename(srcFile) in ignoredDirNames:
                log.info("Ignoring directory %r", srcFile)
                continue
            srcFiles = os.listdir(srcFile)
            if not os.path.exists(dst):
                _mkdir(dst)
            for f in srcFiles:
                s = os.path.join(srcFile, f)
                d = os.path.join(dst, f)
                try:
                    _copy(s, d, overwriteExistingFiles=overwriteExistingFiles,
                          ignoreErrors=ignoreErrors,
                          ignoredDirNames=ignoredDirNames)
                except (IOError, os.error), why:
                    if ignoreErrors:
                        log.warn("Failed to copy %r to %r - %r", s, d, why)
                    else:
                        raise OSError("Can't copy %s to %s: %s"\
                              % (repr(s), repr(d), str(why)))
                    
        elif not usingWildcards:
            raise OSError("Source file %s does not exist" % repr(srcFile))


def _rmtreeOnError(rmFunction, filePath, excInfo):
    if excInfo[0] == OSError:
        # presuming because file is read-only
        os.chmod(filePath, 0777)
        rmFunction(filePath)

def _rmtree(dirname):
    import shutil
    shutil.rmtree(dirname, 0, _rmtreeOnError)

def _splitall(path):
    r"""Split the given path into all constituent parts.

    Often, it's useful to process parts of paths more generically than
    os.path.split(), for example if you want to walk up a directory.
    This recipe splits a path into each piece which corresponds to a
    mount point, directory name, or file.  A few test cases make it
    clear:
        >>> _splitall('')
        []
        >>> _splitall('a/b/c')
        ['a', 'b', 'c']
        >>> _splitall('/a/b/c/')
        ['/', 'a', 'b', 'c']
        >>> _splitall('/')
        ['/']
        >>> _splitall('C:\\a\\b')
        ['C:\\', 'a', 'b']
        >>> _splitall('C:\\a\\')
        ['C:\\', 'a']

    (From the Python Cookbook, Files section, Recipe 99.)
    """
    allparts = []
    while 1:
        parts = os.path.split(path)
        if parts[0] == path:  # sentinel for absolute paths
            allparts.insert(0, parts[0])
            break
        elif parts[1] == path: # sentinel for relative paths
            allparts.insert(0, parts[1])
            break
        else:
            path = parts[0]
            allparts.insert(0, parts[1])
    allparts = [p for p in allparts if p] # drop empty strings 
    return allparts


def _diffFileAssociations(a, b):
    # Massage data for faster lookup.
    #       {'a': 1, 'b': 2}   ->   {('a', 1): True, ('b', 2): True}
    a_massaged = dict( ((k,v), True) for k,v in a.items() )
    b_massaged = dict( ((k,v), True) for k,v in b.items() )

    # Calculate the diffs. ('p' == pattern, 'ln' == language name)
    additions = [('+', p, ln) for (p, ln) in b_massaged.keys()
                               if (p, ln) not in a_massaged]
    deletions = [('-', p, ln) for (p, ln) in a_massaged.keys()
                               if (p, ln) not in b_massaged]
    diff = additions + deletions
    return diff



#---- main component implementation

class KoInitService(object):
    _com_interfaces_ = [components.interfaces.koIInitService,
                        components.interfaces.nsIObserver]
    _reg_clsid_ = "{BAECC764-52AC-46dc-9428-D23F05247818}"
    _reg_contractid_ = "@activestate.com/koInitService;1"
    _reg_desc_ = "Komodo Init Service"
    _reg_categories_ = [
        ("app-startup", "koInitService", "service," + _reg_contractid_),
    ]
    
    def __init__(self):
        # We need this to make sure that logging handlers get registered
        # before we do _anything_ with loggers.
        loggingSvc = components.classes["@activestate.com/koLoggingService;1"].getService()
        global log
        log = logging.getLogger("koInitService")
        #log.setLevel(logging.DEBUG)

        # Lower the Python interpreters check interval so Komodo is more
        # responsive when there are cpu-intensive threads running, bug 96340.
        # This will cause more thread context switches, but that's okay as we
        # want the main UI thread to be responsive and this is the best thing
        # we've got to make that happen.
        # http://docs.python.org/2/library/sys.html#sys.setcheckinterval
        sys.setcheckinterval(15)

        # Warn about multiple inits of init service -- possible with
        # circular usages of koIInitService (bug 81114).
        if hasattr(sys, "_komodo_initsvc_init_count_sentinel"):
            log.warn("Multiple calls to 'KoInitService.__init__()' "
                     "(see bug 81114)!")
            sys._komodo_initsvc_init_count_sentinel += 1
        else:
            sys._komodo_initsvc_init_count_sentinel = 1

        try:
            self.checkStartupFlags()
        except Exception (e):
            log.exception(e, "Exception while checking for startup flags")
            
        self.upgradeUserSettings()
        
        # Cannot be called before upgradeUserSettings, as it initiates the
        # prefs before they should be used
        self.startErrorReporter()
        
        self.installSamples(False)
        self.installSampleTools()
        self.installTemplates()
        self.setPlatformErrorMode()
        self.setEncoding()
        self.checkDefaultEncoding()
        self.initProcessUtils()

    def observe(self, subject, topic, data):
        # this exists soley for app-startup support

        def loadStartupCategories(category):
            """Load XPCOM startup services that are registered for category."""
            catman = components.classes["@mozilla.org/categorymanager;1"].\
                            getService(components.interfaces.nsICategoryManager)
            names = catman.enumerateCategory(category)
            while names.hasMoreElements():
                nameObj = names.getNext()
                nameObj.QueryInterface(components.interfaces.nsISupportsCString)
                name = nameObj.data
                cid = catman.getCategoryEntry(category, name)
                if cid.startswith("service,"):
                    cid = cid[8:]
                log.info("Adding pre startup service for %r: %r", name, cid)
                try:
                    svc = components.classes[cid].\
                        getService(components.interfaces.nsIObserver)
                    svc.observe(None, category, None)
                except Exception:
                    log.exception("Unable to start %r service: %r", name, cid)
        
        observerSvc = components.classes["@mozilla.org/observer-service;1"].\
                      getService(components.interfaces.nsIObserverService)

        if topic == "app-startup":
            observerSvc.addObserver(self, "profile-after-change", 1)

        elif topic == "profile-after-change":
            observerSvc.removeObserver(self, "profile-after-change")
            # get all komodo-startup components and instantiate them
            self.initExtensions()
            loadStartupCategories('komodo-pre-startup-service')
            observerSvc.addObserver(self, "komodo-ui-started", 1)

        elif topic == "komodo-ui-started":
            observerSvc.removeObserver(self, "komodo-ui-started")
            loadStartupCategories('komodo-startup-service')
            observerSvc.addObserver(self, "komodo-post-startup", 1)

        elif topic == "komodo-post-startup":
            observerSvc.removeObserver(self, "komodo-post-startup")
            loadStartupCategories('komodo-delayed-startup-service')
            
    def setPlatformErrorMode(self):
        if sys.platform.startswith("win"):
            try:
                # Stop Windows displaying a dialog when removable
                # media is accessed, but not available
                # (eg, when a file from a floppy is on the MRU,
                # but no floppy is in the drive)
                import ctypes
                SetErrorMode = ctypes.windll.kernel32.SetErrorMode
                SetErrorMode.argtypes = [ctypes.c_uint32]
                SetErrorMode.restype = ctypes.c_uint32
                SEM_FAILCRITICALERRORS = 1
                try:
                    GetErrorMode = ctypes.windll.kernel32.GetErrorMode
                except AttributeError:
                    # Windows XP and Windows 2003 do not have GetErrorMode.
                    import platform
                    log.warn("setPlatformErrorMode:: GetErrorMode not available on platform: %s",
                             platform.win32_ver()[0])
                    SetErrorMode(SEM_FAILCRITICALERRORS)
                else:
                    GetErrorMode.restype = ctypes.c_uint32
                    SetErrorMode(GetErrorMode() | SEM_FAILCRITICALERRORS)
            except ImportError:
                log.error("Could not import ctypes to set the "\
                         "Win32 Error Mode.")
    
    def checkStartupFlags(self):
        import shutil
        
        koDirSvc = components.classes["@activestate.com/koDirs;1"].getService()
        
        ## Clean up after temp profile use
        path = "%s-kotemp-original" % (koDirSvc.userDataDir)
        if os.path.isdir(path):
            if os.path.isdir(koDirSvc.userDataDir):
                shutil.rmtree(koDirSvc.userDataDir)
            os.rename(path, koDirSvc.userDataDir)
            
        ## Clean up after startup with no addons
        path = os.path.join(koDirSvc.userDataDir, "XRE", "extensions")
        tmpPath = "%s-kotemp-original" % (path)
        if os.path.isdir(tmpPath):
            if os.path.isdir(path):
                shutil.rmtree(path)
            os.rename(tmpPath, path)
            
        ## Clean up after startup with no toolbox
        path = os.path.join(koDirSvc.userDataDir, "tools")
        tmpPath = "%s-kotemp-original" % (path)
        if os.path.isdir(tmpPath):
            if os.path.isdir(path):
                shutil.rmtree(path)
            os.rename(tmpPath, path)
        
        ## Check if a flag was set
        path = os.path.join(koDirSvc.userDataDir, "flags")
        try:
            f = open(path)
            flag = f.read().strip()
            f.close()
            os.remove(path)
        except IOError:
            return
        
        ## Delete any file level preferences
        if flag == "cleanDocState":
            path = os.path.join(koDirSvc.userDataDir, "doc-state.xmlc")
            if os.path.isfile(path):
                os.remove(path)
            
        ## Delete the codeintel database
        elif flag == "cleanViewState":
            path = os.path.join(koDirSvc.userDataDir, "view-state.xmlc")
            if os.path.isfile(path):
                os.remove(path)
        
        ## Start with a clean profile
        elif flag == "cleanProfile":
            paths = [koDirSvc.userDataDir]
            profds = self._getProfileDirs()
            
            for d in profds:
                paths.push(d[2])
            
            for path in paths:
                n = 0
                newPath = "%s-backup" % (path)
                while os.path.isdir(newPath):
                    n = n + 1
                    newPath = "%s-backup-%d" % (path,n)
                
                if os.path.isfile(path):
                    os.rename(path, newPath)
        
        ## Start with a temporary profile
        elif flag == "tempProfile":
            path = koDirSvc.userDataDir
            newPath = "%s-kotemp-original" % (path)
            
            if os.path.isfile(path):
                os.rename(path, newPath)
            
            self.disableImportProfile = true
            
        ## Start without addons
        elif flag == "tempNoAddons":
            path = os.path.join(koDirSvc.userDataDir, "XRE", "extensions")
            newPath = "%s-kotemp-original" % (path)
            if os.path.isfile(path):
                os.rename(path, newPath)
            
        ## Start without toolbox items
        elif flag == "tempNoToolbox":
            path = os.path.join(koDirSvc.userDataDir, "tools")
            newPath = "%s-kotemp-original" % (path)
            if os.path.isfile(path):
                os.rename(path, newPath)
        
        ## Delete the codeintel database
        elif flag == "cleanCodeintel":
            import shutil
            path = os.path.join(koDirSvc.userDataDir, "codeintel")
            self._rmtree(path)
            
        ## Delete the codeintel database
        elif flag == "cleanCaches":
            import shutil
            self._rmtree(os.path.join(koDirSvc.userDataDir, "cache2"))
            self._rmtree(os.path.join(koDirSvc.userDataDir, "fileicons"))
            self._rmtree(os.path.join(koDirSvc.userDataDir, "icons"))
            self._rmtree(os.path.join(koDirSvc.userDataDir, "lessCache"))
            self._rmtree(os.path.join(koDirSvc.userDataDir, "OfflineCache"))
            self._rmtree(os.path.join(koDirSvc.userDataDir, "startupCache"))
            self._rmtree(os.path.join(koDirSvc.userDataDir, "userstyleCache"))
    
    def _rmtree(self, path):
        import shutil
        if os.path.isdir(path):
            shutil.rmtree(path)

    def startErrorReporter(self):
        prefs = components.classes["@activestate.com/koPrefService;1"]\
                .getService(components.interfaces.koIPrefService).prefs
        i = components.classes["@activestate.com/koInfoService;1"]\
                .getService(components.interfaces.koIInfoService);
        
        if not prefs.getBooleanPref("analytics_enabled"):
            return
        
        try:
            import bugsnag
            from bugsnag.handlers import BugsnagHandler
            koDirSvc = components.classes["@activestate.com/koDirs;1"].getService()
            
            bugsnag.configure(
                api_key = prefs.getString("bugsnag_key"),
                project_root = koDirSvc.installDir,
                release_stage = i.buildFlavour,
                app_version = i.version)
            
            bugsnag.configure_request(extra_data = {
                "platform": i.buildPlatform,
                "release": i.osRelease,
                "type": i.productType,
                "version": i.version,
                "build": i.buildNumber,
                "releaseStage": i.buildFlavour
            }, user = {"id": prefs.getString("analytics_ga_uid", "")})
            
            # Hook it up to our loggers
            logger = logging.getLogger()
            logger.addHandler(BugsnagHandler())
        except Exception as e:
            log.error("Failed starting bugsnag error reporter: %s" % e.message)
        

    def _safelyReloadSys(self):
        """Safely reload the sys module.

        Simply reloading the sys module will trounce the std handle
        directs that we have done in sitepyxpcom.py for output handling
        without a console.

        XXX Eventually all our setdefaultencoding should perhaps move
            out to our siloed Python's site.py (where
            sys.setdefaultencoding() is deleted) so that we don't have
            to reload(sys) at all.
        """
        savedStdout = sys.stdout
        savedStderr = sys.stderr
        reload(sys)
        sys.stdout = savedStdout
        sys.stderr = savedStderr

    def _setencoding(self,encoding=None):
        log.debug('in _setencoding, encoding=%r', encoding)
        try:
            if not encoding:
                encoding = locale.getdefaultlocale()
            if encoding is not None:
                #XXX Komodo code (specifically pref-intl.xul) requires
                #    the encoding name to be lowercase.
                encoding = (encoding[0], encoding[1].lower())
                # pref-intl.xul also requires utf8 to be "utf-8", bug 75399.
                # Python (and most software) accept both "utf8" and "utf-8".
                if encoding[1] == "utf8":
                    encoding = (encoding[0], "utf-8")

                self._safelyReloadSys()
                sys.setdefaultencoding(encoding[1])
                del sys.setdefaultencoding
                return encoding
        except ValueError, e:
            # XXX Also getting this error occassionaly (as reported on
            # Komodo-beta). Should handle that.
            #    LookupError: unknown encoding
            if encoding:
                log.error('Unsupported encoding for locale %s.%s'%\
                         (encoding[0],encoding[1]))
            else:
                log.error('Unable to set encoding for locale %s'%\
                         os.getenv('LANG'))
        except LookupError, e:
            # windows sets codepages into the locale without
            # the leading 'cp' that python wants.  If the encoding
            # we received is a number, try cp# and see if it works.
            # eg. 1252 should be turned into cp1252
            try:
                if sys.platform.startswith("win") and int(encoding[1]):
                    encoding[1] = 'cp'+encoding[1]
                    return self._setencoding(encoding)
            except ValueError,e:
                # not an int
                #XXX Change inherited (an untested) from bug 24439.
                # check if it has "cp"
                if encoding[1].startswith("cp"):
                    return encoding
            if encoding[0]:
                alias = locale.locale_alias.get(encoding[0].lower())
                if alias:
                    try:
                        return self._setencoding(locale._parse_localename(alias))
                    except ValueError, e:
                        pass
            log.debug('Unsupported encoding for locale %s.%s'%\
                     (encoding[0],encoding[1]))
        except TypeError, e:
            if not sys.platform.startswith("win") and os.getenv("LANG") == "C":
                return ("en_US","iso8859-1")
            else:
                log.debug('Unable to set encoding for locale %s'%\
                            os.getenv('LANG'))
        except Exception:
            log.debug('Unable to determine system locale settings')
        return None
    
    def _setlocale(self):
        log.debug('in _setlocale')
        try:
            locale.setlocale(locale.LC_ALL,'')
        except Exception:
            log.exception("_setlocale")
            log.warn('Unable to setlocale for %s'%os.getenv('LANG'))
            return None
        try:
            return self._setencoding()
        except Exception:
            log.exception("_setlocale")
            log.warn('Unable to set encoding for locale %s'%os.getenv('LANG'))
        return None

    def _removeEuroLocale(self):
        envvars = ['LC_ALL','LC_CTYPE','LANG','LANGUAGE']
        for var in envvars:
            orig_lang = os.getenv(var)
            if orig_lang and orig_lang.lower().endswith('@euro'):
                lang = orig_lang[:orig_lang.find('@euro')]
                os.environ[var] = lang
    
    def setEncoding(self):
        try:
            self._setEncoding()
        except Exception:
            log.exception("koInitService setEncoding failed")

    def _setEncoding(self):
        log.debug("in setEncoding")
        self._startup_locale = self._setlocale()
        if sys.platform.startswith("win"):
            # XXX - this is evil and should be dropped ASAP.
            # Changing the default encoding could impact other code.
            # Python 2.2 will have this support for all file system functions,
            # so as soon as that version is in Komodo, this MUST DIE.

            # On Windows, default python <=2.1 chokes on Unicode file
            # names.  If we change the encoding to "Latin-1", we can
            # at least support European chars transparently.
            # (and if we use "mbcs" we should be able to use
            # _any_ language supported by Windows, latin or otherwise.)
            self._safelyReloadSys()
            sys.setdefaultencoding("mbcs")
            del sys.setdefaultencoding
            log.debug("encoding set to '%s'" % sys.getdefaultencoding())
            if not self._startup_locale:
                log.warn("Unable to determine the current locale "+\
                            "settings, defaulting to en_US.cp1252")
                # set the locale to something that we can
                # least let komodo startup and run with
                self._startup_locale = ['en_US','cp1252']
        elif sys.platform.startswith('darwin'):
            # http://developer.apple.com/documentation/MacOSX/Conceptual/BPInternational/Articles/FileEncodings.html
            # on darwin, and possibly other BSD systems, filesystem is UTF8
            self._safelyReloadSys()
            sys.setdefaultencoding("utf-8")
            del sys.setdefaultencoding
            log.debug("encoding set to '%s'" % sys.getdefaultencoding())
            if not self._startup_locale:
                log.warn("Unable to determine the current locale "+\
                            "settings, defaulting to mac-roman")
                # set the locale to something that we can
                # least let komodo startup and run with
                self._startup_locale = ['','mac-roman']
        else: # Platforms other than Windows
            # Set the default encoding to that appropriate for the
            # current locale, except with UTF-8 support
            if not self._startup_locale:
                log.debug("we do not have _starup_locale")
                # XXX In python 2.2, setlocale fails if
                # the LANG envt variable has @euro at the end.
                # It's a bug in Python 2.2
                self._removeEuroLocale()
                self._startup_locale = self._setlocale()
            if not self._startup_locale:
                log.warn("Unable to determine the current locale "+\
                            "settings, please set LANG environment "+\
                            "variable. Defaulting to en_US.iso8859-1")
                # set the locale to something that we can
                # least let komodo startup and run with
                self._startup_locale = ['en_US','iso8859-1']
            elif self._startup_locale[1].lower() == 'utf':
                log.debug("It's a UTF-8 locale")
                # RH 8 likes to use 'utf' rather than UTF-8,
                # but it will accept UTF-8
                # we cannot modify _startup_locale directly, so reset it
                # completely (bug 28824)
                self._startup_locale = [self._startup_locale[0],'UTF-8']
                # we're already in utf mode, so don't bother doing
                # the settings below
                return
            if not self._startup_locale[0]:
                # OSX doesn't return this data.  Set it to C for now
                self._startup_locale = ['', self._startup_locale[1]]
                log.info("Setting LC_CTYPE to 'C'")
                locale.setlocale(locale.LC_CTYPE, "C")
                return
            # We have to set pythons encoding to utf-8 so that
            # we can have some hope of interpreting file paths
            # that are written in different encodings, and to
            # make GTK show UTF8 fonts correctly.  for instance
            # saving a file with a latin-1 filename, but starting
            # komodo with encoding ISO8859-1.  If we do not do
            # this, and a latin-1 filename is in mru, komodo fails
            # to load

            # XXX The above is not entirely correct across platforms,
            # notably breaking down on Solaris.  It would be best to
            # set the default encoding to the system encoding, but
            # that leads to conflicts with how other components (Gtk,
            # Mozilla, Scintilla) are operating.

            # XXX this will break on older unix systems that do not
            # support UTF-8 -- it would be nice to detect this and
            # let the user know.
            
            # XXX we may want to reimplement this with python 2.3, it affects
            # koDocument encoding issues.
            
            #try:
            #    # this bit is for file I/O
            #    self._safelyReloadSys()
            #    log.info("Setting default encoding to utf-8")
            #    sys.setdefaultencoding('utf-8')
            #    del sys.setdefaultencoding
            #except Exception,e:
            #    log.warn('cannot set encoding to utf-8: %s'%e)

            # this bit is the GTK important bit
            # if it's not done, GTK won't display correctly
            try:
                new_locale = self._startup_locale[0]+'.UTF-8'
                log.info("Setting LC_CTYPE to utf-8")
                locale.setlocale(locale.LC_CTYPE,new_locale)
            except Exception,e:
                log.warn("cannot reset LOCALE set to %s : %s" % (new_locale,e))

            if sys.platform.startswith("sunos"):
                # UTF-8 support on Solaris is not working correctly with
                # GTK.  If a user wishes to use non-latin-1 files (either
                # in file name or data) on Solaris, they will need to
                # ensure they have the correct language packs and fonts on
                # their machines, then export LANG=en_US.UTF-8 (or similar
                # utf-based encoding).
                # We add this LC_CTYPE call here to prevent Gdk fontset
                # warnings, improper titlebar behavior and related unicode
                # issues on Solaris. (Bug 28592, 29235)
                log.info("Setting LC_CTYPE to 'C'")
                locale.setlocale(locale.LC_CTYPE, "C")

    def getStartupLanguageCode(self):
        return self._startup_locale[0]
    def getStartupEncoding(self):
        return self._startup_locale[1]

    def checkDefaultEncoding(self):
        # Check the Komodo default file encoding, as Komodo can only handle
        # _some_ encodings out there. Typically if the set encoding is one that
        # Komodo cannot handle then we fallback to an encoding that we know
        # Komodo will handle - UTF8.
        prefs = components.classes["@activestate.com/koPrefService;1"]\
                .getService(components.interfaces.koIPrefService).prefs
        encodingSvc = components.classes["@activestate.com/koEncodingServices;1"].\
                          getService(components.interfaces.koIEncodingServices)

        # Get the default file encoding.
        defaultEncoding = prefs.getString("encodingDefault", "utf-8")
        log.debug("encoding: currently configured default is '%s'", defaultEncoding)

        # Ensure the default encoding can be handled by Komodo.
        if encodingSvc.get_encoding_index(defaultEncoding) == -1:
            # This encoding is NOT supported.
            log.debug("encoding %r is not supported - defaulting to UTF-8", defaultEncoding)
            defaultEncoding = "utf-8"
            assert encodingSvc.get_encoding_index(defaultEncoding) >= 0
            prefs.setStringPref("encodingDefault", defaultEncoding)

        # Sanity check.
        if defaultEncoding != defaultEncoding.lower():
            #XXX Komodo code requires the encodingDefault string to be lowercase
            #    and while Komodo code has been updated to guarantee this there
            #    may still be uppercase user prefs out there.
            prefs.setStringPref("encodingDefault", defaultEncoding.lower())

    def initProcessUtils(self):
        # Bug 81114: koUserEnviron needs to know to environ encoding to
        # decode startup-env.tmp.
        koUserEnviron = components.classes["@activestate.com/koUserEnviron;1"].getService()
        koUserEnviron.startupEnvironEncoding = self.getStartupEncoding()

        try:
            import koprocessutils
            koprocessutils.initialize()
        except Exception:
            log.exception("initProcessUtils")

        try:
            # Komodo 8 hack to fixup siloed Python - bug 98931.
            if sys.platform == "darwin":
                koDirSvc = components.classes["@activestate.com/koDirs;1"].getService()
                pythonExe = koDirSvc.pythonExe
                if not os.path.islink(pythonExe) and os.path.exists(pythonExe):
                    os.remove(pythonExe)
                    relPath = "../Frameworks/Python.framework/Versions/%d.%d/bin/python" % (
                                sys.version_info.major, sys.version_info.minor)
                    os.symlink(relPath, pythonExe)
        except Exception:
            log.exception("initProcessUtils:: failed mozpython symlink check - please reinstall Komodo")

    def finishInitialization(self):
        pass

    def _upgradeFiles(self, dstNameFromSrcName, srcDir, dstDir):
        for srcName, dstName in dstNameFromSrcName.items():
            src = os.path.join(srcDir, srcName)
            dst = os.path.join(dstDir, dstName)
            if not os.path.exists(src):
                # It is not an error if some of the files to upgrade
                # don't exist. The user may just not have done much with
                # the previous Komodo version to have them generated.
                log.info("skipping '%s' - does not exist" % src)
                continue
            try:
                log.info("upgrading '%s' from '%s'" % (dst, src))
                _copy(src, dst, ignoreErrors=True)
            except OSError, ex:
                log.error("Could not upgrade '%s' from '%s': %s"\
                         % (dst, src, ex))

    def _upgradeOldUserPrefs(self, prefs):
        """Upgrade any specific info in the user's prefs.xml.
        
        This is only called to upgrade old Komodo preference data: < Komodo 6.1
        """
        # Komodo 4.0 change: 'fileAssociations' was replaced with the
        # factoryFileAssociations/fileAssociationDiffs combo. This upgrade
        # ensures the user ends up with the appropriate 'fileAssociationDiffs'
        # and that 'fileAssociations' is removed (if any).
        if prefs.hasPrefHere("fileAssociations"):
            # Collect the old associations mapping.
            oldAssociations = {}
            fileAssociationsPref = prefs.getPref("fileAssociations")
            for i in range(fileAssociationsPref.length):
                p = fileAssociationsPref.getPref(i)
                oldAssociations[p.getStringPref(0)] = p.getStringPref(1)

            # The "appropriate" set of factory associations to which to compare
            # is the default "fileAssociations" value for Komodo 3.5.
            factoryAssociations = {
                '*.ada': 'Ada', '*.ant': 'Bullant', '*.asm': 'Assembler',
                '*.aux': 'LaTeX', '*.ave': 'Avenue', '*.bat': 'Batch',
                '*.bbl': 'LaTeX', '*.bc': 'Baan', '*.c': 'C++', '*.c++': 'C++',
                '*.cgi': 'Perl', '*.cix': 'XML', '*.cln': 'Baan',
                '*.cls': 'LaTeX', '*.clw': 'CLW', '*.cmd': 'Batch',
                '*.conf': 'Apache', '*.cpp': 'C++', '*.cron': 'nnCrontab',
                '*.cs': 'C#', '*.css': 'CSS', '*.cxx': 'C++', '*.diff': 'Diff',
                '*.e': 'Eiffel', '*.el': 'Lisp', '*.em': 'EScript',
                '*.erl': 'Erlang', '*.f': 'Fortran 77',
                '*.f90': 'Fortran', '*.f95': 'Fortran', '*.for': 'Fortran 77',
                '*.forth': 'Forth', '*.gc': 'Gui4Cli', '*.h': 'C++',
                '*.h++': 'C++', '*.hpp': 'C++', '*.htm': 'HTML', '*.html':
                'HTML', '*.hxx': 'C++', '*.idl': 'IDL', '*.inc': 'PHP',
                '*.java': 'Java', '*.js': 'JavaScript', '*.kix': 'Kix',
                '*.kpf': 'XML', '*.lis': 'Lisp', '*.lof': 'LaTeX', '*.lot':
                'Lot', '*.lt': 'Lout', '*.ltx': 'LaTeX', '*.lua': 'Lua',
                '*.m': 'Matlab', '*.mac': 'APDL', '*.mak': 'Makefile',
                '*.mixal': 'MMIXAL', '*.mp': 'Metapost', '*.nsi': 'Nsis',
                '*.pas': 'Pascal', '*.patch': 'Diff', '*.pb': 'PowerBasic',
                '*.php': 'PHP', '*.pl': 'Perl', '*.plex': 'Perl',
                '*.plx': 'Perl', '*.pm': 'Perl', '*.pov': 'POVRay',
                '*.ps': 'PostScript', '*.py': 'Python', '*.pyw': 'Python',
                '*.rb': 'Ruby', '*.sh': 'Bash', '*.sol': 'Scriptol',
                '*.spf': 'nnCrontab', '*.sql': 'SQL', '*.sty': 'LaTeX',
                '*.t': 'Perl', '*.tab': 'nnCrontab', '*.tcl': 'Tcl',
                '*.tex': 'LaTeX', '*.toc': 'LaTeX', '*.txt': 'Text',
                '*.v': 'Verilog', '*.vb': 'VisualBasic', '*.vbs': 'VisualBasic',
                '*.vh': 'Verilog', '*.xml': 'XML', '*.xs': 'C++',
                '*.xsl': 'XSLT', '*.xslt': 'XSLT', '*.xul': 'XML',
                '*.yaml': 'YAML', 'Conscript': 'Perl', 'Construct': 'Perl',
                'Makefile': 'Makefile', 'Makefile.*': 'Makefile',
                'makefile': 'Makefile', 'makefile.*': 'Makefile',
            }

            diff = _diffFileAssociations(factoryAssociations, oldAssociations)

            # The new UDL-based RHTML lexer is better than anything there was
            # before: override any previous setting.
            diff = [d for d in diff if d[:2] != ('+', '*.rhtml')]

            prefs.setStringPref("fileAssociationDiffs", repr(diff))
            prefs.deletePref("fileAssociations")

        if prefs.hasPrefHere("mappedPaths"):
            import upgradeutils
            upgradeutils.upgrade_mapped_uris_for_prefset(prefs)

        # Upgrade auto-save pref, turn minutes into seconds - bug 82854.
        if prefs.hasPrefHere("autoSaveMinutes"):
            autoSaveSeconds = prefs.getLongPref("autoSaveMinutes") * 60
            prefs.setLongPref("autoSaveSeconds", autoSaveSeconds)
            prefs.deletePref("autoSaveMinutes")

    # This value must be kept in sync with the value in "../prefs/prefs.p.xml"
    _current_pref_version = 20

    def _upgradeUserPrefs(self, prefs):
        """Upgrade any specific info in the user's prefs.xml.
        
        This is called after the new user data dir has been created.

        Dev note: This is also called every time Komodo is started.
        """
        if prefs.hasPrefHere("version"):
            version = prefs.getLongPref("version")
        else:
            # Prefs are from before Komodo 6.1
            self._upgradeOldUserPrefs(prefs)
            version = 0

        if version >= self._current_pref_version:
            # Nothing to upgrade.
            return

        if version < 3 and prefs.hasPref("import_exclude_matches"):
            # Add the two new Komodo project names to import_exclude_matches
            try:
                import_exclude_matches = prefs.getStringPref("import_exclude_matches")
                if import_exclude_matches.endswith(";"):
                    import_exclude_matches = import_exclude_matches[:-1]
                # From Komodo 5 (prefset version 2)
                orig_str_1 = "*.*~;*.bak;*.tmp;CVS;.#*;*.pyo;*.pyc;.svn;*%*;tmp*.html;.DS_Store"
                # From Komodo 6 (still prefset version 2)
                orig_str_2 = "*.*~;*.bak;*.tmp;CVS;.#*;*.pyo;*.pyc;.svn;_svn;.git;.hg;.bzr;*%*;tmp*.html;.DS_Store"
                if import_exclude_matches in (orig_str_1, orig_str_2):
                    suffix = ";*.komodoproject;.komodotools"
                    import_exclude_matches = orig_str_2 + suffix
                    prefs.setStringPref("import_exclude_matches",
                                        import_exclude_matches)
            except:
                log.exception("Error updating import_exclude_matches")

        if version < 5 and prefs.hasPref("import_exclude_matches"):
            # Add __pycache__ to excludes
            try:
                import_exclude_matches = prefs.getStringPref("import_exclude_matches")
                if import_exclude_matches.endswith(";"):
                    import_exclude_matches = import_exclude_matches[:-1]
                if ("*.pyc;" in import_exclude_matches
                    and ";__pycache__" not in import_exclude_matches):
                    import_exclude_matches = import_exclude_matches + ";__pycache__"
                    prefs.setStringPref("import_exclude_matches",
                                        import_exclude_matches)
            except:
                log.exception("Error updating import_exclude_matches")

        if version < 6: # Komodo 8.0.0a2
            prefs.setStringPref("ui.tabs.sidepanes.left.layout", "icons")
            prefs.setStringPref("ui.tabs.sidepanes.right.layout", "icons")

        if version < 7: # Komodo 8.1
            prefs.deletePref("koSkin_custom_skin")
            prefs.deletePref("koSkin_custom_icons")
            prefs.deletePref("runtime_manifests")

        if version < 9: # Komodo 8.5.3: new large-doc settings
            # Update the threshold prefs only if they're the same as the
            # old stock prefs
            if (prefs.getLong("documentByteCountThreshold") == 1000000
                    and prefs.getLong("documentLineCountThreshold") == 20000
                    and prefs.getLong("documentLineLengthThreshold") == 32000):
                prefs.setLongPref("documentByteCountThreshold", 2000000)
                prefs.setLongPref("documentLineCountThreshold", 40000)
                prefs.setLongPref("documentLineLengthThreshold", 100000)

        if version < 10: # Komodo 9.0.0a1
            prefs.setStringPref("analyticsLastVersion", "pre-9.0a1")

        if version < 11: # Komodo 9.0.0a1
            self._flattenLanguagePrefs(prefs)

        if version < 13:
            prefs.setBoolean("transit_commando_keybinds", True)

        if version < 14:
            oldScheme = prefs.getStringPref("editor-scheme")
            if oldScheme.startswith("Dark_"):
                prefs.setString("editor-scheme", "Tomorrow_Dark")
            elif oldScheme == "Solarized":
                prefs.setString("editor-scheme", "Solarized_Dark")
            elif oldScheme in ("BlueWater", "Bright", "Default", "Komodo",
                               "LowContrast_Zenburn", "Medium"):
                # Transition to the new light scheme.
                prefs.setString("editor-scheme", "Tomorrow_Light")
            # Else it's a custom scheme - leave it alone.

        if version < 16:
            # Default encoding changes:
            if prefs.getBoolean("encodingEnvironment", True):
                # Change default encoding to be utf-8, instead of the system
                # encoding.
                prefs.setString("defaultEncoding", "utf-8")
            # else, the user has already set it to what they want.
            # Remove obsolete pref.
            if prefs.hasPrefHere("encodingEnvironment"):
                prefs.deletePref("encodingEnvironment")
            
        if version < 17:
            prefs.setBoolean("koSkin_use_custom_scrollbars", True)
            
        if version < 18:
            # Reset skin and iconset to defaults because 9.0 is a major release
            prefs.deletePref("koSkin_custom_icons")
            prefs.deletePref("koSkin_custom_skin")
            prefs.deletePref("runtime_manifests")
            
        if version < 20: # Komodo 9.2
            activeSkin = prefs.getString("koSkin_custom_skin", "")
            if activeSkin == "chrome://abyss-skin/content/manifest/chrome.manifest":
                prefs.deletePref("koSkin_custom_icons")
                prefs.deletePref("koSkin_custom_skin")
                prefs.deletePref("runtime_manifests")
                prefs.setBoolean("removedAbyss", True)
                prefs.setBoolean("forceSkinReload", True)

        # Set the version so we don't have to upgrade again.
        prefs.setLongPref("version", self._current_pref_version)

    def _flattenLanguagePrefs(self, prefs):
        """In Komodo 9.0.0a1, we flattened the language prefs.  This needs to
        be done both in global prefs and project prefs.
        """
        if not prefs.hasPref("languages"):
            return
        allLangPrefs = prefs.getPref("languages")
        for langPrefId in allLangPrefs.getPrefIds():
            if not langPrefId.startswith("languages/"):
                continue # bad pref
            langPref = allLangPrefs.getPref(langPrefId)
            lang = langPrefId[len("languages/"):]
            for prefId in langPref.getPrefIds():
                prefType = langPref.getPrefType(prefId)
                newPrefId = prefId
                if newPrefId.startswith(lang + "/"):
                    newPrefId = newPrefId[len("/" + lang):]
                newPrefId = "languages/%s/%s" % (lang, newPrefId)
                if prefType == "string":
                    prefs.setString(newPrefId, langPref.getString(prefId))
                elif prefType == "long":
                    prefs.setLong(newPrefId, langPref.getLong(prefId))
                elif prefType == "double":
                    prefs.setDouble(newPrefId, langPref.getDouble(prefId))
                elif prefType == "boolean":
                    prefs.setBoolean(newPrefId, langPref.getBoolean(prefId))
                else:
                    prefs.setPref(newPrefId, langPref.getPref(prefId))
                langPref.deletePref(prefId)
            allLangPrefs.deletePref(langPrefId)
        prefs.deletePref("languages")


    def _hostUserDataDir(self, userDataDir):
        """Support for Komodo profiles that contain a host-$HOST directory."""
        if os.environ.has_key("KOMODO_HOSTNAME"):
            hostname = os.environ["KOMODO_HOSTNAME"]
        else:
            import socket
            hostname = socket.gethostname()
        return os.path.join(userDataDir, "host-"+hostname)

    def _upgradeXREDir(self, prevXREDir, currXREDir):
        if os.path.exists(prevXREDir):
            log.debug("upgrading XRE directory")
            ignoredDirNames = [
                # Bug 90294: klint is replaced by a builtin extension in 7.0a3
                # Ensure we don't upgrade the user-profile version of it.
                "klint@dafizilla.sourceforge.net",
                # Don't upgrade caches:
                "Cache",
                "cache2",
                "_CACHE_CLEAN_",
                "crashes",
                "lessCache",
                "minidumps",
                "startupCache",
            ]
            _copy(prevXREDir, currXREDir, overwriteExistingFiles=False,
                  ignoreErrors=True, ignoredDirNames=ignoredDirNames)
            # Another cache, but name is too common to use in ignoredDirNames.
            if os.path.exists(os.path.join(currXREDir, "icons")):
                _rmtree(os.path.join(currXREDir, "icons"))
                
    def _getProfileDirs(self):
        from os.path import dirname, basename, join, exists
        
        koDirSvc = components.classes["@activestate.com/koDirs;1"].getService()
        currUserDataDir = koDirSvc.userDataDir
        
        # Get the current version.
        infoSvc = components.classes["@activestate.com/koInfoService;1"].getService()
        currVer = infoSvc.version.split(".", 2)[:2]
        for i in range(len(currVer)):
            try:
                currVer[i] = int(currVer[i])
            except ValueError:
                pass
        currVer = tuple(currVer) # e.g. (6,0)
        
        # Determine from which Komodo userdatadir we should upgrade.
        basedir, base = os.path.split(dirname(currUserDataDir))
        if base not in ("KomodoEdit", ".komodoedit"):
            # Looks like KOMODO_USERDATADIR is being used.
            datadirs = [dirname(currUserDataDir)]
        elif sys.platform in ("win32", "darwin"):
            datadirs = [join(basedir, d) for d in ("Komodo", "KomodoEdit")]
            if sys.platform == "win32":
                # Komodo 6 on Windows moved the profile directory from the
                # roaming app data dir, to the local app data dir (applies to
                # Vista and Windows 7). Add these older roaming user data
                # directories as well.
                roaming_komodo_data_dir = dirname(dirname(koDirSvc.roamingUserDataDir))
                if roaming_komodo_data_dir != currUserDataDir:
                    datadirs += [join(roaming_komodo_data_dir, d) for d in
                                ("Komodo", "KomodoEdit")]
        else:
            datadirs = [join(basedir, d) for d in (".komodo", ".komodoedit")]
        ver_pat = re.compile(r"^\d+\.\d+$")
        vers_and_userdatadirs = []
        for datadir in datadirs:
            try:
                ver_strs = os.listdir(datadir)  # e.g. ["3.5", "4.0", "bogus"]
            except EnvironmentError, ex:
                continue
            for ver_str in ver_strs:
                if not ver_pat.match(ver_str):  # e.g. "bogus" doesn't match
                    continue
                ver = tuple(map(int, ver_str.split('.')))
                if ver < (4, 0):
                    log.debug("Skipping Komodo profile: %r - too old", ver)
                    continue # Skip versions prior to 4.0.
                if ver > currVer:
                    continue # Skip future versions, we don't downgrade.
                userdatadir = join(datadir, ver_str)
                if userdatadir == currUserDataDir:
                    continue # Skip: can't upgrade from self.
                vers_and_userdatadirs.append(
                    (ver, _splitall(userdatadir), userdatadir))
        vers_and_userdatadirs.sort()
        
        return vers_and_userdatadirs

    def _upgradeUserDataDirFiles(self):
        """Upgrade files under the USERDATADIR if necessary.

        Note: For Komodo 4.0.2 the APPDATADIR changed to include the product
        type (IDE or Edit). Before:
            windows: C:\Documents and Settings\USER\Application Data\ActiveState\Komodo\X.Y
            macosx:  ~/Library/Application Support/Komodo/X.Y
            linux:   ~/.komodo/X.Y
        After:
            windows: C:\Documents and Settings\USER\Application Data\ActiveState\Komodo[IDE|Edit]\X.Y
            macosx:  ~/Library/Application Support/Komodo[IDE|Edit]/X.Y
            linux:   ~/.komodo[ide|edit]/X.Y

        If the upgrade is necessary, this method will upgrade from a previous
        version of Komodo (Edit, Personal, Pro), but will *not* upgrade from
        a Komodo IDE profile.
        """
        from os.path import dirname, basename, join, exists

        koDirSvc = components.classes["@activestate.com/koDirs;1"].getService()
        currUserDataDir = koDirSvc.userDataDir
        currHostUserDataDir = koDirSvc.userDataDir
        
        # These are the files/dirs that we upgrade.
        filesToUpgrade = {
            "komodo-user-prefs.xml": "prefs.xml",
            "prefs.xml": "prefs.xml",
            "templates": "templates",
            "project-templates": "project-templates",
            "schemes": "schemes",
            "toolbox.sqlite": "toolbox.sqlite",
            "tools": "tools",
            "obsolete-tools": "obsolete-tools",
            "doc-state.xmlc": "doc-state.xmlc", 
            "view-state.xmlc": "view-state.xmlc", 
            "apicatalogs": "apicatalogs",
            "dictionaries": "dictionaries",
            "publishing": "publishing",
        }
        # Files under "host-$HOST" dir to upgrade:
        # Note: Prior to Komodo 6, some files were stored in a host-$HOST folder
        #       inside the Komodo profile directory.
        hostFilesToUpgrade = {
            "breakpoints.pickle": "breakpoints.pickle",
            "history.sqlite": "history.sqlite",
            "autosave": "autosave",
        }



        # First determine if we need to upgrade at all.
        # If any of the above exist in the current version's user data
        # dir then do NOT upgrade.
        for base in filesToUpgrade.keys():
            path = join(currUserDataDir, base)
            if exists(path):
                log.debug("not upgrading userdatadir files: '%s' exists", path)
                return
        for base in hostFilesToUpgrade.keys():
            path = join(currUserDataDir, base)
            if exists(path):
                log.debug("not upgrading userdatadir files: '%s' exists", path)
                return

        vers_and_userdatadirs = self._getProfileDirs()

        # This now looks like, e.g.:
        #   [((4, 0), ['C:\\', ..., 'Komodo', '4.0'],     'C:\\...\\Komodo\\4.0'),
        #    ((5, 2), ['C:\\', ..., 'KomodoEdit', '5.2'], 'C:\\...\\KomodoEdit\\5.2')]
        # I.e., the last one in the list, if any, is the dir from which to
        # upgrade.
        if not vers_and_userdatadirs:
            log.debug("not upgrading userdatadir files: no userdatadirs "
                      "from which to upgrade")
            return
        prevVer, _, prevUserDataDir = vers_and_userdatadirs[-1]

        if prevVer < (6,0):
            # Uses a separate host-$HOST directory.
            prevHostUserDataDir = self._hostUserDataDir(prevUserDataDir)
            filesToUpgrade["toolbox.kpf"] = "toolbox.kpf"
        else:
            # Host dir is the same directory as userDataDir.
            prevHostUserDataDir = prevUserDataDir

        # Upgrade.
        log.info("upgrading user settings from '%s'" % prevUserDataDir)
        self._upgradeFiles(filesToUpgrade, prevUserDataDir, currUserDataDir)
        self._upgradeFiles(hostFilesToUpgrade, prevHostUserDataDir,
                           currHostUserDataDir)
        self._upgradeXREDir(join(prevHostUserDataDir, "XRE"),
                            join(currHostUserDataDir, "XRE"))
        if prevVer[0] < currVer[0]:
            import glob
            # Remove any XRE/extensions.* files, let Moz rebuild these,
            # otherwise extensions can fail to load correctly.
            xre_dir = join(currHostUserDataDir, "XRE")
            for ext_filename in glob.glob(join(xre_dir, "extensions.*")):
                ext_filepath = join(xre_dir, ext_filename) 
                log.warn("not upgrading '%s'" % (ext_filepath, ))
                os.remove(ext_filepath)

    def upgradeUserSettings(self):
        """Called every time Komodo starts up to initialize the user profile."""
        
        if hasattr(self, 'disableImportProfile') and self.disableImportProfile:
            return
        
        try:
            self._upgradeUserDataDirFiles()
            prefs = components.classes["@activestate.com/koPrefService;1"]\
                    .getService(components.interfaces.koIPrefService).prefs
            self._upgradeUserPrefs(prefs)
        except Exception:
            log.exception("upgradeUserSettings")

    def _isMozDictionaryDir(self, dictionaryDir):
        # Return true if dictionaryDir contains at least one pair of files
        # foo.aff and foo.dic
        
        if not os.path.isdir(dictionaryDir):
            return False
        from os.path import basename, join, splitext
        import glob
        aff_bases = set(splitext(basename(p))[0]
                        for p in glob.glob(join(dictionaryDir, "*.aff")))
        dic_bases = set(splitext(basename(p))[0]
                        for p in glob.glob(join(dictionaryDir, "*.dic")))
        return len(aff_bases.intersection(dic_bases)) > 0

    def initExtensions(self):
        """'pylib' subdirectories of installed extensions are appended
        to Komodo's runtime sys.path. Also initialize the 'langinfo'
        database with these dirs.
        """
        try:
            # Add the DictD property so the spellchecker can find
            # the user's own dictionaries.  Consider only directories
            # that contain the English dictionary, or the Komodo extension
            # will fail to startup (bug 74839).
            koDirSvc = components.classes["@activestate.com/koDirs;1"].getService()
            dictionaryDir = os.path.join(koDirSvc.userDataDir, "dictionaries")
            if self._isMozDictionaryDir(dictionaryDir):
                profDir_nsFile = components.classes["@mozilla.org/file/local;1"] \
                        .createInstance(components.interfaces.nsILocalFile)
                profDir_nsFile.initWithPath(dictionaryDir)
                directoryService = components.classes["@mozilla.org/file/directory_service;1"]\
                         .getService(components.interfaces.nsIProperties)
                directoryService.set("DictD", profDir_nsFile)

            import directoryServiceUtils
            pylibDirs = directoryServiceUtils.getPylibDirectories()
            # Prime the pump for the `langinfo' database.
            import langinfo
            langinfo.set_default_dirs(pylibDirs)
        except Exception:
            log.exception("error initializing from extensions")

    def installSamples(self, force):
        try:
            koDirSvc = components.classes["@activestate.com/koDirs;1"].getService()
            #XXX The best target directory might vary for other OSes.
            dstDir = os.path.join(koDirSvc.userDataDir, "samples")
            if os.path.exists(dstDir):
                # If the older format ".kpf" files still exist, re-create the
                # samples folder.
                sampleKpfPath = os.path.join(dstDir, "sample_project.kpf")
                if os.path.exists(sampleKpfPath):
                    force = True
                if force:
                    log.info("removing old samples directory: '%s'" % dstDir)
                    _rmtree(dstDir) #XXX should handle error here
                else:
                    log.info("samples already present at '%s'" % dstDir)
                    return
            srcDir = os.path.join(koDirSvc.supportDir, "samples")
            log.info("installing Komodo samples to '%s'" % dstDir)
            _copy(srcDir, dstDir)
        except Exception:
            log.exception("installSamples")

    def installSampleTools(self):
        pref_prefix = "haveInstalledSampleToolbox-Komodo"
        try:
            prefs = components.classes["@activestate.com/koPrefService;1"].\
                    getService(components.interfaces.koIPrefService).prefs
            infoSvc = components.classes["@activestate.com/koInfoService;1"].\
                      getService(components.interfaces.koIInfoService)
            lookAtPrefName = True
            koDirs = components.classes["@activestate.com/koDirs;1"].\
                     getService(components.interfaces.koIDirs)
            stdToolsFolder = os.path.join(koDirs.userDataDir, 'tools')
            obsoleteToolsFolder = os.path.join(koDirs.userDataDir, 'obsolete-tools')
            if not os.path.exists(stdToolsFolder):
                os.mkdir(stdToolsFolder)
                lookAtPrefName = False
                
            prefName = pref_prefix + infoSvc.version
            if lookAtPrefName and prefs.hasBooleanPref(prefName) and prefs.getBooleanPref(prefName):
                return

            folder_name = "Samples (%s)" % str(infoSvc.version)
            destDir = os.path.join(stdToolsFolder, folder_name)
            srcDir = os.path.join(koDirs.supportDir, 'samples', 'tools')
            # Must ensure the destination directory exists - bug 87470.
            if not os.path.exists(destDir):
                os.makedirs(destDir)
                
            installedSampleTools = True
            import fileutils
            import shutil
            for name in os.listdir(srcDir):
                srcChild = os.path.join(srcDir, name)
                try:
                    if os.path.isdir(srcChild):
                        fileutils.copyLocalFolder(srcChild, destDir)
                    else:
                        shutil.copy(srcChild, destDir)
                except:
                    # logging doesn't always work in this file, so print the
                    # traceback as well.
                    log.exception("Failed to copy srcChild:%s to dest destDir:%s", srcChild, destDir)
                    installedSampleTools = False

            # Remove old samples
            import json
            macro_template_path = os.path.join(koDirs.supportDir, 'toolbox',
                                               'Restore Samples.komodotool')
            with open(macro_template_path, "r") as macro_source:
                macro_template = macro_source.read()
            for existing_pref_name in prefs.getPrefIds():
                try:
                    if not existing_pref_name.startswith(pref_prefix):
                        continue
                    version = existing_pref_name[len(pref_prefix):]
                    if version == str(infoSvc.version):
                        continue # shouldn't have reached here!?
                    folder_name = "Samples (%s)" % (version,)
                    old_dir = os.path.join(stdToolsFolder, folder_name)
                    if not os.path.isdir(old_dir):
                        continue # already removed (by user or us)
                    log.warn("%s is obsolete; moving it to %s",
                             folder_name, obsoleteToolsFolder)
                    if not os.path.exists(obsoleteToolsFolder):
                        os.makedirs(obsoleteToolsFolder)
                    dest_dir = os.path.join(obsoleteToolsFolder, folder_name)
                    os.rename(old_dir, dest_dir)
                    # Plop in a macro to restore the sample...
                    macro_contents = macro_template\
                                        .replace("{{version}}", version) \
                                        .replace("{{script_version}}", str(infoSvc.version))
                    macro_dir = os.path.join(stdToolsFolder, "Obsolete samples")
                    if not os.path.isdir(macro_dir):
                        os.makedirs(macro_dir)
                    macro_name = json.loads(macro_contents)["name"]
                    macro_path = os.path.join(macro_dir,
                                              macro_name + ".komodotool")
                    with open(macro_path, "w") as f:
                        f.write(macro_contents)
                except Exception:
                    log.exception("Removing old samples")

            prefs.setBooleanPref(prefName, installedSampleTools)
        except Exception:
            log.exception("installSampleTools")

    def installTemplates(self):
        try:
            for type in ("file", "project"):
                # Simply creating these services will initialize the template
                # directories on the filesystem (if they don't already exist).
                cid = "@activestate.com/koTemplateService?type=%s;1" % (type, )
                components.classes[cid].\
                        getService(components.interfaces.koITemplateService)
        except Exception:
            log.exception("installTemplates")

# #if BUILD_FLAVOUR == "dev"
    # Benchmark the known/slow methods.
    __init__ = benchmark.bench("koInitService.__init__")(__init__)
    upgradeUserSettings = benchmark.bench("koInitService.upgradeUserSettings")(upgradeUserSettings)
# #endif
