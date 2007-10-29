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

#
# A set of standard (and hopefully generally useful) Black configuration
# items.
#

import os, sys, re
if sys.platform.startswith("win"):
    import _winreg
import tmShUtil
import black.configure
from black.configure import Datum, ConfigureError, RunEnvScript, BooleanDatum



#---- Black specific items



#---- general system configuration items

class SystemDirs(Datum):
    def __init__(self):
        Datum.__init__(self, "systemDirs", desc="the system directories")

    def _Determine_Do(self):
        if sys.platform.startswith("win"):
            self.applicable = 1
            try:
                sysRoot = os.environ["SystemRoot"]
            except KeyError:
                # Win98 (how about Win95?)
                sysRoot = os.environ["windir"]
            self.value = []
            self.value.append(sysRoot)
            self.value.append(os.path.join(sysRoot, "system32"))
        elif sys.platform.startswith("sunos"):
            self.applicable = 1
            self.value = ["/usr/local/bin", "/usr/bin/", "/usr/ccs/bin",
                          "/usr/ucb", "/bin"]
        else:
            self.applicable = 1
            self.value = ["/usr/local/bin", "/usr/bin", "/bin"]
        self.determined = 1


class Path(Datum):
    def __init__(self):
        Datum.__init__(self, "path", desc="the configured PATH setting")

    def _Determine_Do(self):
        # If there is a PATH configuration item, then return its value.
        # Otherwise return the value of the PATH environment variable.
        if black.configure.items.has_key("PATH"):
            pathItem = black.configure.items["PATH"]
            self.applicable = pathItem.Determine()
            if self.applicable:
                self.value = pathItem.Get()
        else:
            self.applicable = 1
            self.value = os.environ["PATH"].split(os.pathsep)
        self.determined = 1



#---- some MSVC configuration items

class MsvcInstallDir(Datum):
    def __init__(self, compilerVersion="vc6"):
        Datum.__init__(self, "msvcInstallDir",
            desc="the installation directory of Microsoft Visual %s" % (compilerVersion),
            serializeAs=[])
        self._compilerVersion = compilerVersion.lower()

    def _Determine_Sufficient(self):
        if self.value is None:
            raise ConfigureError("Could not determine %s. Do you have "\
                "Visual Studio installed? If so, then there is a bug in the "\
                "configure code or it has to be extended "\
                "for the weird way you setup your machine.\n" % self.desc)

    def _Determine_Do(self):
        if sys.platform.startswith("win"):
            self.applicable = 1
            # look in the registry:
            # HKEY_LOCAL_MACHINE/SOFTWARE/Microsoft/DevStudio/6.0/Products\
            #   /Microsoft Visual C++/ProductDir
            try:
                if self._compilerVersion.startswith("vc6"):
                    key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE,
                        "SOFTWARE\\Microsoft\\DevStudio\\6.0\\Products"\
                        "\\Microsoft Visual C++")
                elif self._compilerVersion.startswith("vc7") or \
                     self._compilerVersion.startswith("vc8"):
                    key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE,
                        "SOFTWARE\\Microsoft\\VisualStudio\\SxS\\VC7")
                else:
                    # Unknown compiler version
                    raise WindowsError("Unknown windows compiler version")
            except WindowsError:
                self.value = None
            else:
                numSubkeys, numValues, lastModified = _winreg.QueryInfoKey(key)
                for i in range(numValues):
                    valueName, valueData, dataType = _winreg.EnumValue(key, i)
                    if self._compilerVersion.startswith("vc7") and \
                        (valueName == '7.1'):
                        self.value = str(valueData)  # convert from Unicode
                        break
                    elif self._compilerVersion.startswith("vc8") and \
                        (valueName == '8.0'):
                        self.value = str(valueData)  # convert from Unicode
                        break
                    elif self._compilerVersion.startswith("vc6") and \
                        (valueName == 'ProductDir'):
                        self.value = str(valueData)  # convert from Unicode
                        break
                else:
                    # otherwise just try the default hardcoded path
                    if self._compilerVersion.startswith("vc6"):
                        installDir =\
                        "C:\\Program Files\\Microsoft Visual Studio\\VC98";
                    elif self._compilerVersion.startswith("vc7"):
                        installDir =\
                            "C:\\Program Files\\Microsoft Visual Studio .NET 2003\\Vc7";
                    elif self._compilerVersion.startswith("vc8"):
                        installDir =\
                            "C:\\Program Files\\Microsoft Visual Studio 8\\VC";
                    if os.path.isdir(installDir):
                        self.value = installDir
                    else:
                        self.value = None
        else:
            self.applicable = 0
        self.determined = 1


class SetupMsvc(RunEnvScript):
    def __init__(self):
        RunEnvScript.__init__(self, "setupMsvc",
            desc="how to setup environment for MSVC")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise ConfigureError("Could not determine %s.\n" % self.desc)

    def _Determine_Do(self):
        if sys.platform.startswith("win"):
            #XXX should this be conditional on MSDevDir???
            self.applicable = 1
            msvcInstallDir = black.configure.items['msvcInstallDir'].Get()
            vcvars32Bat = os.path.join(msvcInstallDir, 'bin', 'vcvars32.bat')
            if os.path.isfile(vcvars32Bat):
                self.value = vcvars32Bat
            else:
                self.value = None
        else:
            self.applicable = 0
            self.value = None
        self.determined = 1


class MsvcrtDebugDllsInstalled(BooleanDatum):
    def __init__(self):
        Datum.__init__(self, "msvcrtDebugDllsInstalled",
            desc="the Microsoft Runtime debugging DLLs installed")

    def _Determine_Sufficient(self):
        if not self.value:
            raise ConfigureError("The Microsoft Runtime debugging DLLs are "\
                "not installed on this machine. You have to install them.\n")

    def _Determine_Do(self):
        # optionally use the "buildType" configuration item, if defined,
        # to determine if this item is applicable
        if sys.platform.startswith("win"):
            if black.configure.items.has_key("buildType") and\
              black.configure.items["buildType"].Get() != "debug":
                self.applicable = 0
            else:
                self.applicable = 1
                if not black.configure.items.has_key("systemDirs"):
                    black.configure.items["systemDirs"] =\
                        black.configure.std.SystemDirs()
                systemDirs = black.configure.items["systemDirs"].Get()
                msvcrtdDll = tmShUtil.Which("msvcrtd.dll", systemDirs)
                msvcirtdDll = tmShUtil.Which("msvcirtd.dll", systemDirs)
                if not (msvcrtdDll and msvcirtdDll):
                    self.value = 0
                else:
                    self.value = 1
        else:
            self.applicable = 0
        self.determined = 1


#---- Python, Perl, PHP configuration items

class PythonExeName(Datum):
    def __init__(self):
        Datum.__init__(self, "pythonExeName",
            desc="the name of the Python executable")

    def _Determine_Do(self):
        self.applicable = 1
        if sys.platform.startswith("win"):
            if black.configure.items.has_key("buildType") and\
              black.configure.items["buildType"].Get() == "debug":
                self.value = "python_d.exe"
            else:
                self.value = "python.exe"
        else:
            self.value = "python"
        self.determined = 1


class PythonVersion(Datum):
    def __init__(self):
        Datum.__init__(self, "pythonVersion", desc="the python version")

    def _Determine_Do(self):
        self.applicable = 1

        if not black.configure.items.has_key("pythonExeName"):
            black.configure.items["pythonExeName"] = PythonExeName()
        pythonExeName = black.configure.items["pythonExeName"].Get()
        o = os.popen('%s -c "import sys; sys.stdout.write(\'.\'.join(map(str, sys.version_info[:3])))"' % pythonExeName)
        self.value = o.read()
        self.determined = 1


class PerlBinDir(Datum):
    def __init__(self):
        Datum.__init__(self, "perlBinDir", desc="the Perl bin directory")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise ConfigureError("Could not determine %s (could not find "\
                "perl on your path). You have to install Perl and put it on "\
                "your path.\n" % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        perlExe = tmShUtil.WhichFollowSymLinks('perl')
        if perlExe:
            self.value = os.path.dirname(perlExe)
        else:
            self.value = None
        self.determined = 1


class PhpBinDir(Datum):
    def __init__(self):
        Datum.__init__(self, "phpBinDir", desc="the PHP bin directory")

    def _Determine_Do(self):
        self.applicable = 1
        phpExe = tmShUtil.WhichFollowSymLinks('php')
        if phpExe:
            self.value = os.path.dirname(phpExe)
        else:
            self.value = None
        self.determined = 1


class PythonBinDir(Datum):
    def __init__(self):
        Datum.__init__(self, "pythonBinDir", "the Python bin directory")

    def _Determine_Sufficient(self):
        if self.value is None:
            pythonExeName = black.configure.items["pythonExeName"].Get()
            raise ConfigureError("Could not determine %s (could not find %s "\
                "on your path). You have to install Python and put it on "\
                "your path.\n" % (self.desc, pythonExeName))

    def _Determine_Do(self):
        self.applicable = 1
        if not black.configure.items.has_key("pythonExeName"):
            black.configure.items["pythonExeName"] = PythonExeName()
        pythonExeName = black.configure.items["pythonExeName"].Get()
        pythonExe = tmShUtil.WhichFollowSymLinks(pythonExeName)
        if pythonExe:
            self.value = os.path.dirname(pythonExe)
        else:
            self.value = None
        self.determined = 1


class PythonInstallDir(Datum):
    def __init__(self):
        Datum.__init__(self, "pythonInstallDir",
            desc="the Python installation directory")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise ConfigureError("Could not determine %s.\n" % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        if not black.configure.items.has_key("pythonBinDir"):
            black.configure.items["pythonBinDir"] = PythonBinDir()
        pythonBinDir = black.configure.items["pythonBinDir"].Get()
        if pythonBinDir:
            from os.path import basename, dirname
            if sys.platform.startswith("win"):
                if basename(pythonBinDir).lower() == "pcbuild":
                    self.value = dirname(pythonBinDir)
                else:
                    self.value = pythonBinDir
            elif sys.platform == 'darwin':
                # foo/Python.framework/Versions/X.Y/bin -> foo
                self.value = dirname(dirname(dirname(dirname(pythonBinDir))))
            else:
                if basename(pythonBinDir) == "bin":
                    self.value = dirname(pythonBinDir)
                else:
                    self.value = pythonBinDir
        else:
            self.value = None
        self.determined = 1


class PerlInstallDir(Datum):
    def __init__(self):
        Datum.__init__(self, "perlInstallDir",
            desc="Perl installation directory")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise ConfigureError("Could not determine %s. You have to "\
                "install Perl and put it on your path.\n" % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        if not black.configure.items.has_key("perlBinDir"):
            black.configure.items["perlBinDir"] = PerlBinDir()
        perlBinDir = black.configure.items["perlBinDir"].Get()
        if perlBinDir:
            self.value = os.path.dirname(perlBinDir)
        else:
            self.value = None
        self.determined = 1


class PerlVersion(Datum):
    def __init__(self, name=None, desc=None,
                 # The id of the configuration item describing the perl
                 # installation in which to check for these modules.
                 perlBinDirItemName="perlBinDir"):
        self.perlBinDirItemName = perlBinDirItemName
        if name is None:
            name = "perlVersion"
        if desc is None:
            desc="the Perl version number"
        Datum.__init__(self, name, desc)

    def _Determine_Do(self):
        if not black.configure.items.has_key(self.perlBinDirItemName):
            black.configure.items[self.perlBinDirItemName] = PerlBinDir()
        self.applicable = black.configure.items[self.perlBinDirItemName].Determine()
        if self.applicable:
            perlBinDir = black.configure.items[self.perlBinDirItemName].Get()
            if perlBinDir:
                perlExe = os.path.join(perlBinDir, "perl")
                o = os.popen("%s -v" % perlExe)
                perlVersionDump = o.read()
                perlVersionMatch = re.compile("This is perl, v([0-9.]+)").\
                    search(perlVersionDump)
                if perlVersionMatch:
                    self.value = perlVersionMatch.group(1) 
                else:
                    self.value = None
            else:
                self.value = None
        self.determined = 1


class ActivePerlBuild(Datum):
    def __init__(self, name=None, desc=None,
                 # The id of the configuration item describing the perl
                 # installation in which to check for these modules.
                 perlBinDirItemName="perlBinDir"):
        self.perlBinDirItemName = perlBinDirItemName
        if name is None:
            name = "activePerlBuild"
        if desc is None:
            desc="the ActivePerl build number"
        Datum.__init__(self, name, desc)

    def _Determine_Do(self):
        if not black.configure.items.has_key(self.perlBinDirItemName):
            black.configure.items[self.perlBinDirItemName] = PerlBinDir()
        self.applicable = black.configure.items[self.perlBinDirItemName].Determine()
        if self.applicable:
            perlBinDir = black.configure.items[self.perlBinDirItemName].Get()
            if perlBinDir:
                perlExe = os.path.join(perlBinDir, "perl")
                o = os.popen("%s -v" % perlExe)
                perlVersionDump = o.read()
                buildMatch = re.compile(
                    "Binary build (\d+) provided by ActiveState").\
                    search(perlVersionDump)
                if buildMatch:
                    self.value = buildMatch.group(1) 
                else:
                    self.value = None
            else:
                self.value = None
        self.determined = 1


class PerlModulesInstalled(BooleanDatum):
    def __init__(self, name=None, desc=None,
                 # The id of the configuration item describing the perl
                 # installation in which to check for these modules.
                 perlBinDirItemName="perlBinDir",
                 modules=[],    # the list of Perl module name to check for
                 fatal=1):      # true iff the modules *must* be installed
        self.perlBinDirItemName = perlBinDirItemName
        self.modules = modules
        self.fatal = fatal
        if name is None:
            name = "perlModulesInstalled"
        if desc is None:
            desc="the following Perl modules are installed: %s" % self.modules
        Datum.__init__(self, name, desc)

    def _Determine_Sufficient(self):
        if self.fatal and len(self.notInstalled) != 0:
            perlBinDir = black.configure.items[\
                self.perlBinDirItemName].Get()
            raise ConfigureError("The following required Perl modules "\
                "(%s) are not installed in your Perl installation (%s). You "\
                "have to install them.\n" % (self.notInstalled, perlBinDir))

    def _Determine_Do(self):
        self.applicable = 1
        if not black.configure.items.has_key(self.perlBinDirItemName):
            black.configure.items[self.perlBinDirItemName] = PerlBinDir()
        perlBinDir = black.configure.items[self.perlBinDirItemName].Get()
        perlExe = os.path.join(perlBinDir, "perl")
        self.value = []
        self.notInstalled = []
        for module in self.modules:
            o = os.popen('%s -m%s -e "print \'madeit\';"' % (perlExe, module))
            output = o.read()
            o.close()
            if output != "madeit":
                self.notInstalled.append(module)
            else:
                self.value.append(module)
        self.determined = 1


