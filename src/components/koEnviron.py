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

import sys, os, re
from xpcom import components, ServerException, nsError
import koprocessutils
import logging

from zope.cachedescriptors.property import Lazy as LazyProperty


log = logging.getLogger('koEnviron')
#log.setLevel(logging.DEBUG)



#---- globals

if sys.platform.startswith("win"):
    _gBashEnvStrRe = re.compile("^(?P<name>[^&=\r\n\t]+)=(?P<value>.*)$")
    _gEnvStrResToSkip = []
else:
    _gBashEnvStrRe = re.compile("^(?P<name>[\w]+)=(?P<value>.*)$")
    _gCshEnvStrRe = re.compile("^(?P<name>[\w]+)\t(?P<value>.*)$")
    # On linux we want to skip function definitions like this:
    #
    #    mc=()
    #    {
    #        echo hello;
    #        ls --color=auto ~;
    #        echo bye
    #    }
    # 
    # or this:
    #
    #    mc=() {  mkdir -p $HOME/.mc/tmp 2>/dev/null;
    #     chmod 700 $HOME/.mc/tmp;
    #     MC=$HOME/.mc/tmp/mc-$$;
    #     /usr/bin/mc -P "$@" >"$MC";
    #     cd "`cat $MC`";
    #     rm -i -f "$MC";
    #     unset MC
    #    }
    #
    _gEnvStrResToSkip = [re.compile("^[_\w]+=\(\).*$"),  # function defs
                         re.compile("^\s+.*$"), # leading whitespace == in function def
                         re.compile("^{.*$"), # function start
                         re.compile("^}$"), # function end
                        ]


#---- support routines

def _ParseBashEnvStr(envStr):
    """Return the (env var name, env var value) pair from the given
    'name=value' environment string.
    """
    # skip unwanted lines formats
    for reToSkip in _gEnvStrResToSkip:
        if reToSkip.search(envStr):
            return None

    # parse out name and value
    envStrMatch = _gBashEnvStrRe.search(envStr)
    if envStrMatch:
        name = envStrMatch.group("name")
        if sys.platform.startswith("win"):
            name = name.upper()  # put everything upper on Windows
        value = envStrMatch.group("value")
        return name, value
    elif envStr:
        log.warn("skipping environment string: '%s'" % envStr)

def parse_bash_set_output(output):
    """Parse Bash-like 'set' output"""
    if not sys.platform.startswith("win"):
        # Replace "\"-continued lines in *Linux* environment dumps.
        # Cannot do this on Windows because a "\" at the end of the
        # line does not imply a continuation.
        output = output.replace("\\\n", "")
    environ = {}
    for line in output.splitlines(0):
        line = line.rstrip()
        if not line: continue  # skip black lines
        item = _ParseBashEnvStr(line)
        if item:
            environ[item[0]] = item[1]
    return environ



def run(cmd, stdin=None):
    log.debug("run '%s'...", cmd)
    try:
        i,o,e = os.popen3(cmd)
        # we ignore ioerrors here, which do get raised in some situations,
        # however even when they are, we still get stdout output from
        # printenv
        try:
            if stdin:
                i.write(stdin)
            i.close()
        except IOError, e:
            pass
        try:
            stdout = o.read()
        except IOError, e:
            pass
        try:
            stderr = e.read()
        except IOError, e:
            pass
        o.close()
        retval = e.close()
        #print stdout
        return stdout, stderr, retval
    finally:
        log.debug("...done.")


#---- component/service implementations

# simple interface to be able to work with the environment
class KoEnviron:
    _com_interfaces_ = [components.interfaces.koIEnviron]
    _reg_clsid_ = "{68E2A458-186F-4e2c-898E-99F3B21DA819}"
    _reg_contractid_ = "@activestate.com/koEnviron;1"
    _reg_desc_ = "System Environment Interaction Service"

    def has(self, key):
        return os.environ.has_key(key)
    def get(self, key, default=None):
        return os.environ.get(key, default)
    def set(self, key, value):
        os.environ[key] = value
    def remove(self, key):
        del os.environ[key]


class KoUserEnviron:
    _com_interfaces_ = [components.interfaces.koIUserEnviron,
                        components.interfaces.nsIObserver]
    _reg_clsid_ = "{B6289D1A-983E-46e0-85E2-75221D44A5FC}"
    _reg_contractid_ = "@activestate.com/koUserEnviron;1"
    _reg_desc_ = "User Environmnet Interaction Service"

    startupEnvironEncoding = None

    def __init__(self, startupEnvFileName=None):
        # By default the startup environment file is in the Komodo AppData
        # directory. For testing purposes, though, it can be useful to
        # specify a test file.
        self._origStartupEnv = None
        self._userEnviron = None
        if startupEnvFileName is None:
            self._startupEnvBaseName = "startup-env.tmp"
            self.startupEnvFileName = os.path.join(self.koDirs.userDataDir,
                                                   "startup-env.tmp")
        else:
            self.startupEnvFileName = startupEnvFileName
    
    # save for possible future use, this gets terminal.app settings, or trys
    # using netinfo.  I think pwd.getpwnam returns the same info that netinfo
    # would.
    #def _getOSXShell(self, plist):
    #    try:
    #        plist = os.path.expanduser("~/Library/Preferences/com.apple.Terminal.plist")
    #        if os.path.isfile(plist):
    #            import plistlib
    #            info = plistlib.Plist.fromFile(plist)
    #            return info['Shell']
    #        # we can get the shell from the user, but we may not have the
    #        # DOMAIN (first param after -readprop)
    #        if 'USER' in os.environ and os.environ['USER']:
    #            cmd = "/bin/sh -c \"niutil -readprop / /users/%s shell\"" % os.environ['USER']
    #            stdout, stderr, retval = run(cmd)
    #            if not retval:
    #                return stdout.strip()
    #        return None
    #    except Exception, e:
    #        log.exception(e)
    #        return None
        
    def _determineShell(self):
        if sys.platform == "win32":
            return None
        prefs = components.classes["@activestate.com/koPrefService;1"]\
                .getService(components.interfaces.koIPrefService).prefs
        shell = prefs.getString("environ_userShell", "")
        if shell:
            return shell
        try:
            import pwd
            return pwd.getpwnam(os.environ['USER'])[6]
        except Exception, e:
            log.exception(e)
        return None
        
    def _initialize(self):
        if self._userEnviron is None:
            prefs = components.classes["@activestate.com/koPrefService;1"]\
                    .getService(components.interfaces.koIPrefService).prefs
            prefs.prefObserverService.addObserver(self, "userEnvironmentStartupOverride", 0)
            self._UpdateFromStartupEnv()
        
        # enable the following if we want to try executing shells
        #if self._userEnviron is None:
        #    shell = self._determineShell()
        #    if shell:
        #        err = self.UpdateFromShell(shell)
        #        if err:
        #            log.warn("could not get environment from '%s' shell: %s",
        #                     shell, err)
        #            self._UpdateFromStartupEnv() # fallback
        #    else:
        #        self._UpdateFromStartupEnv()

    def _UpdateFromStartupEnv(self):
        if self.startupEnvironEncoding is None:
            raise RuntimeError("cannot decode startup environment: "
                               "`startupEnvironEncoding' is not set")

        self._userEnviron = {}
        # read in startup env delta file and fill in the startup env
        try:
            fin = open(self.startupEnvFileName, "r")
        except EnvironmentError, ex:
            self._userEnviron = os.environ.copy()
        else:
            content = fin.read()
            fin.close()
            if not sys.platform.startswith("win"):
                # Replace "\"-continued lines in *Linux* environment dumps.
                # Cannot do this on Windows because a "\" at the end of the
                # line does not imply a continuation.
                content = content.replace("\\\n", "")
            content = unicode(content, self.startupEnvironEncoding)
            for line in content.split("\n"):
                line = line.rstrip()
                if not line:
                    continue  # skip black lines
                item =  _ParseBashEnvStr(line)
                if item:
                    self._userEnviron[item[0]] = item[1]
                    
        self._removeProtectedVars()
        self._origStartupEnv = self._userEnviron.copy()
        self._updateWithUserOverrides()

    @LazyProperty
    def koDirs(self):
        return components.classes["@activestate.com/koDirs;1"].\
            getService(components.interfaces.koIDirs)

    @LazyProperty
    def _isDevTree(self):
        """Return true if this Komodo is running in a dev tree layout."""
        landmark = os.path.join(self.koDirs.mozBinDir, "is_dev_tree.txt")
        return os.path.isfile(landmark)

    def _removeProtectedVars(self):
        from uriparse import UnRelativizePath

        fullname = ['_']
        startingwith = ['MOZILLA_', 'XRE_', 'MRE_', 'MOZ_', 'KOMODO_']
        dangerouspaths = ['PATH', 'LD_LIBRARY_PATH', 'DYLD_LIBRARY_PATH',
                          'PYTHONPATH', 'PYTHONHOME', 'LIBRARY_PATH', 'LIBPATH',
                          'ADDON_PATH', 'SHLIB_PATH']
        
        for item in fullname:
            if item in self._userEnviron.keys():
                del self._userEnviron[item]

        for item in startingwith:
            for key in self._userEnviron.keys():
                if key.startswith(item):
                    del self._userEnviron[key]
                    
        # this is more touchy, remove any path from paths that contain our
        # install directory
        if self._isDevTree:
            # get down to the mozilla src trunk
            installDir = os.path.dirname(os.path.dirname(self.koDirs.installDir))
            installDir = installDir.upper()
        else:
            installDir = self.koDirs.installDir.upper()
        cwd = os.getcwd().upper()
        for item in dangerouspaths:
            value = self._userEnviron.get(item)
            if value:
                paths = value.split(os.pathsep)
                # The paths may be relative, so we must get the absolute path
                # in order to properly check these values - bug 89345.
                for i, path in reversed(list(enumerate(paths))):
                    fullpath = UnRelativizePath(cwd, path.upper())
                    if fullpath.find(installDir) >= 0:
                        del paths[i]
                if paths:
                    self._userEnviron[item] = os.pathsep.join(paths)
                else:
                    del self._userEnviron[item]

    _last_project_env_override = ""

    def addProjectEnvironment(self, project):
        project_overrides = ""
        if project:
            prefs = project.prefset
            if prefs and prefs.hasPrefHere("userEnvironmentStartupOverride"):
                project_overrides = prefs.getString("userEnvironmentStartupOverride", "")

        if project_overrides == self._last_project_env_override:
            # Nothing changed, so nothing to do.
            return

        self._last_project_env_override = project_overrides
        self._updateWithUserOverrides(project_overrides)

    def _updateWithUserOverrides(self, project_overrides=None):
        self._userEnviron = self._origStartupEnv.copy()
        
        # now overwrite with the userEnvironment preference
        prefs = components.classes["@activestate.com/koPrefService;1"]\
                .getService(components.interfaces.koIPrefService).prefs
        _environUtils = components.classes[
            "@activestate.com/koEnvironUtils;1"] \
            .getService(components.interfaces.koIEnvironUtils)
        havePATHOverride = False
        all_overrides = [prefs.getString("userEnvironmentStartupOverride", ""),
                         project_overrides]
        for overrides in all_overrides:
            if overrides:
                env = re.split('\r?\n|\r', overrides, re.U)
                if not env: env = []
                sysenv = self.GetEnvironmentStrings()
                newenv = _environUtils.MergeEnvironmentStrings(sysenv, env)
                if not newenv:
                    return
                self._userEnviron = {}
                for line in newenv:
                    item =  _ParseBashEnvStr(line)
                    if item:
                        if item[0] == "PATH":
                            havePATHOverride = True
                        self._userEnviron[item[0]] = item[1]
        
        # For some platforms we implicitly add some common dirs to the PATH.
        # It is common, for example, on Mac OS X for a Komodo user to have
        # "/usr/local/bin" on the PATH in their shell, but not in Komodo
        # because Mac applications don't start from a login shell. This is
        # confusing to users. (Bug 80656.)
        implicitPathAdditionsFromPlat = {
            "darwin": ["/usr/local/bin",
                       "/opt/local/bin"],  # Mac Ports
            "linux2": ["/usr/local/bin"],
        }
        if (not havePATHOverride
            and sys.platform in implicitPathAdditionsFromPlat
            and prefs.getBoolean("userEnvironmentAllowImplicitPATHAdditions", True)):
            implicitPathAdditions = implicitPathAdditionsFromPlat[sys.platform]
            path = self._userEnviron.get("PATH", "").split(os.pathsep)
            if sys.platform in ("darwin", "win32"):
                comparePath = set(p.lower() for p in path) # case-insensitive comparison
            else:
                comparePath = set(path)
            for ipa in implicitPathAdditions:
                compareIpa = (sys.platform in ("darwin", "win32")
                              and ipa.lower() or ipa)
                if compareIpa not in comparePath:
                    path.append(ipa)
            if path:
                self._userEnviron["PATH"] = os.pathsep.join(path)

        # we must reset this in order for some services to pick up on the
        # changes (eg. SCC services)
        koprocessutils.resetUserEnv()

    def observe(self, obj, topic, data):
        if topic == "userEnvironmentStartupOverride":
            self._updateWithUserOverrides()

    def has(self, key):
        self._initialize()
        if sys.platform.startswith("win"):
            key = key.upper()  # put everything upper on Windows
        return self._userEnviron.has_key(key)

    def get(self, key, default=None):
        self._initialize()
        if sys.platform.startswith("win"):
            key = key.upper()  # put everything upper on Windows
        return self._userEnviron.get(key, default)

    def keys(self):
        return self._userEnviron.keys()

    def GetEnvironmentStrings(self):
        self._initialize()
        return ["%s=%s" % (item[0], item[1])\
            for item in self._userEnviron.items()]

    def GetEncodedEnvironment(self):
        self._initialize()
        envStrings = self.GetEnvironmentStrings()
        return '\n'.join(envStrings)

    def GetEncodedStartupEnvironment(self):
        self._initialize()
        envStrings = ["%s=%s" % (item[0], item[1])\
            for item in self._origStartupEnv.items()]
        return '\n'.join(envStrings)

    def UpdateFromShell(self, shell):
        """Update the internal user environment cache from the given shell.

        Returns None is successful, otherwise returns an error message.
        """
        import koprocessutils
        assert sys.platform != "win32", "'UpdateFromShell' is not available for Windows"

        ##XXX Disable updating user environment from the shell. This can
        ##    be a source of hangs! See bug 38216.
        #return "updating user environment with shell is disabled"

        if not shell:
            self._UpdateFromStartupEnv()
            koprocessutils.resetUserEnv()
            return
        if not (os.path.isfile(shell)):
            return "given shell path does not exist: %r" % shell

        # Determine what class of shell this is: bash, csh, etc.
        patterns = [  # pattern to match against basename
            ("csh", re.compile("csh")),
            ("korn", re.compile("ksh")),
            ("zorn", re.compile("zsh")),
            ("bash", re.compile("bash|^sh$")),
            ("ash", re.compile("^ash$")),
        ]
        basename = os.path.basename(shell)
        type = None
        for name, pattern in patterns:  
            if pattern.search(basename):
                type = name
                break
        else:
            return "Don't know what kind of shell '%s' is. It doesn't look "\
                   "like any of Bash, csh, zorn or ash." % shell

        # Run the correct voodoo to get the environment from this shell.
        # the important part here is that the shell must be a login shell,
        # and should not be an interactive shell.  interactive shells
        # have a tendency to lock up komodo (at least on tiger)
        stdin = None
        if ' ' in shell:
            return "cannot yet handle spaces in shell path: %r" % shell

        if type == "bash":
            # interactive bash locks up on tiger
            cmd = "%s -lc printenv" % shell

        elif type == "csh":
            # first *arg* is '-' or -l for login shell, so we must use stdin
            cmd = "%s -l" % shell
            stdin = "printenv"

        # all other shell man pages I looked at say 
        # first char of arg 0 is - means login shell, so -c printenv should
        # be fine.
        else:
            cmd = "%s -c printenv" % shell

        stdout, stderr, retval = run(cmd, stdin)
        if retval:
            return "error getting environment from '%s'" % cmd
        if not stdout:
            return "no stdout received from printenv"
        self._userEnviron = parse_bash_set_output(stdout)
        koprocessutils.resetUserEnv()



class KoEnvironUtils:
    _com_interfaces_ = [components.interfaces.koIEnvironUtils]
    _reg_clsid_ = "{cb1e55b4-6837-4659-a9e0-9f6ab4acb54d}"
    _reg_contractid_ = "@activestate.com/koEnvironUtils;1"
    _reg_desc_ = "Environment Variable Utilities"

    def MergeEnvironmentStrings(self, baseEnvStrs, diffEnvStrs):
        envDict = {}
        #print "MergeEnvironmentStrings: merge %r into %r" % (diffEnvStrs,
        #                                                     baseEnvStrs)
        for baseEnvStr in baseEnvStrs:
            item = _ParseBashEnvStr(baseEnvStr)
            if item:
                envDict[item[0]] = item[1]
        for diffEnvStr in diffEnvStrs:
            #print "merge in '%s' ..." % diffEnvStr
            item = _ParseBashEnvStr(diffEnvStr)
            if item:
                name = item[0]
                value = item[1]
            else:
                continue
            # an empty value means: remove env. var.
            if value == "":
                if envDict.has_key(name):
                    del envDict[name]
                #print "... delete '%s' variable" % name
            # interpolate any other value into the resultant dictionary
            else:
                value = self._Interpolate(value, envDict)
                envDict[name] = value
                #print "... %s=%s" % (name, value)
        return ["%s=%s" % item for item in envDict.items()]

    def _Interpolate(self, envValue, envDict):
        """Interpolate the variable in the given envDict into the envValue.
        Use platform-specific syntax, i.e. %FOO% on Windows and $FOO or $(FOO)
        elsewhere.
        """
        if sys.platform.startswith("win"):
            envRefRe = re.compile("""
                (?P<envRef>%                    # env. var. reference
                    (?P<envName>[^&=\r\n\t%]+)  # env. var. name
                %)
                """, re.VERBOSE)
        else:
            envRefRe = re.compile(r"""
                (?P<envRef>
                    \$\b(?P<envName>\w+)\b      # simple $FOO like reference
                    |
                    \$\((?P<envName2>\w+)\)     # parenthesized $(FOO) like ref
                )
                """, re.VERBOSE)
        interpolated = envValue
        replacements = {}
        for envRefMatch in envRefRe.finditer(interpolated):
            envName = envRefMatch.group("envName") \
                      or envRefMatch.group("envName2")
            if sys.platform.startswith("win"):
                envName = envName.upper()
            # Tough call on how interpolation of undefined variables
            # should be handled because:
            #    windows> echo %NOTDEFINED%
            #    %NOTDEFINED%
            #    linux> echo $NOTDEFINED
            #
            # We will expect the Linux behaviour on both Windows and Linux
            # for now.
            #
            # because of bug 45297 we are switching the behaviour to match
            # windows, rather than linux.  This is because url encoded data
            # from cgi emulation is/was getting interpolated, breaking
            # cgi debugging in a pretty bad way
            if envName in envDict:
                replacements[envRefMatch.group("envRef")] = envDict[envName]
        for old, new in replacements.items():
            interpolated = interpolated.replace(old, new)
            
        #print "_Interpolate: interpolate '%s' -> '%s'" % (envValue, interpolated)
        return interpolated

    def GetUserShells(self):
        assert sys.platform != "win32", "'GetUserShells' is not available for Windows"
        shells = []
        skips = ["false", "true", "passwd"]
        shellsFile = "/etc/shells"
        fin = open(shellsFile, 'r')
        try:
            for line in fin:
                shell = line.strip()
                if not shell: continue                        # empty line
                if shell.startswith("#"): continue            # comment line
                if os.path.basename(shell) in skips: continue # not really "shells"
                shells.append(shell)
        finally:
            fin.close()
        return shells

