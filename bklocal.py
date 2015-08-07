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

# The local set of Black configuration items for Komodo-devel.


import os
from os.path import join, exists, expanduser, dirname, basename, \
                    abspath, normpath, isdir, isfile
import sys
import glob
import re
import time
from pprint import pprint
import warnings
import socket
import subprocess

if sys.platform.startswith('win'):
    import _winreg

import black.configure
from black.configure import ConfigureError
import tmShUtil

sys.path.insert(0, os.path.join("src", "python-sitelib"))
import which
sys.path.pop(0)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "util"))
import platinfo
import gitutils
del sys.path[0]


#---- output control (use black's output stream if available)

out = black.configure.out



#---- configuration (i.e. info that might need to change for new Komodo versions)

#---- utils

def _getLinuxDistro():
    assert sys.platform.startswith("linux")
    return platinfo.platname("distro+distro_ver")


def _getPrettyVersion(version):
    """Transform the given version to a "pretty" form
    "pretty" representation as used for the "Product Name" in the MSI
    installer.

    Examples:
        2.0.0                       2.0.0
        2.0.1-beta                  2.0.1 Beta
        2.3.0-beta1                 2.3.0 Beta 1
    """
    parts = version.split('-')
    if len(parts) == 1:
        return version
    elif len(parts) == 2:
        ver, quality = parts
        match = re.match("([a-z]+)(\d+)?", quality)
        qualityType, qualityVer = match.groups()
        if qualityVer is None:
            return "%s %s" % (ver, qualityType.capitalize())
        else:
            return "%s %s %s" % (ver, qualityType.capitalize(), qualityVer)
    else:
        raise "Invalid version string: '%s'. Can only be one hyphen."\
              % version


def _capture_stdout(argv, ignore_retval=False, cwd=None, env=None):
    # Only available on python 2.4 and above
    import subprocess
    p = subprocess.Popen(argv, cwd=cwd, stdout=subprocess.PIPE, env=env)
    stdout = p.stdout.read()
    retval = p.wait()
    if retval and not ignore_retval:
        raise RuntimeError("error running '%s'" % ' '.join(argv))
    return stdout


def _getValidPlatforms(linuxDistro=False, macUniversal=True):
    """Return a list of platforms for which Mozilla can be built from
    the current machine.

    @param linuxDistro {bool} Indicates if linux distro should be included
        in the name.
    @param macUniversal {bool} Indicates if the package/whatever using this
        platform name is universal (i.e. shouldn't include the arch).
    """
    validPlats = []
    if sys.platform == "win32":
        validPlats = ["win32-x86"]
    elif sys.platform.startswith("linux"):
        uname = os.uname()
        if uname[4] == "ia64":
            validPlats = []
        elif re.match("i\d86", uname[4]):
            config = ""
            if linuxDistro:
                config += "-" + _getLinuxDistro()
            validPlats = ["linux%s-x86" % config]
        elif uname[4] == "x86_64":
            config = ""
            if linuxDistro:
                config += "-" + _getLinuxDistro()
            validPlats = ["linux%s-x86_64" % config]
        else:
            raise ConfigureError("unknown Linux architecture: '%s'"
                                 % uname[4])
    elif sys.platform.startswith("sunos"):
        #XXX Note that we don't really support Solaris builds yet.
        uname = os.uname()
        if uname[4].startswith("sun4"):
            if uname[2] == "5.6":
                validPlats = ["solaris-sparc"]
            elif uname[2] == "5.8":
                validPlats = ["solaris8-sparc", "solaris8-sparc64"]
            else:
                raise ConfigureError("unknown Solaris version: '%s'"
                                     % uname[2])
        else:
            raise ConfigureError("unknown Solaris architecture: '%s'"
                                 % uname[4])
    elif sys.platform == "darwin":
        if macUniversal:
            validPlats = ["macosx"]
        else:
            uname = os.uname()
            if uname[-1] == 'i386':
                validPlats = ["macosx-x86"]
            elif uname[-1] == 'x86_64':
                validPlats = ["macosx-x86_64"]
            else:
                raise ConfigureError("unexpected macosx architecture: '%s'"
                                     % uname[4])
    return validPlats


def _getDefaultPlatform(linuxDistro=False, macUniversal=True):
    """Return an appropriate default target platform for the current machine.
    
    @param linuxDistro {bool} Indicates if linux distro should be included
        in the name.
    @param macUniversal {bool} Indicates if the package/whatever using this
        platform name is universal (i.e. shouldn't include the arch).
    
    A "platform" is a string of the form "<os>[-<config>][-<arch>]".
    """
    try:
        return _getValidPlatforms(linuxDistro=linuxDistro,
                                  macUniversal=macUniversal)[0]
    except IndexError, ex:
        raise ConfigureError("cannot build mozilla on this platform: '%s'"
                             % sys.platform)

gMozDefines = None
gMozSubsts = None
def _getMozDefinesAndSubsts(mozObjDir):
    """Load Mozilla's config.status Python file."""
    # TODO: This should eventually use Mozilla's ConfigStatus.py file.
    global gMozDefines
    global gMozSubsts
    if gMozDefines is None:
        mozconfig = join(mozObjDir, "config.status")
        cfg_globals = {"__file__": mozconfig}
        cfg_locals = {}
        execfile(mozconfig, cfg_globals, cfg_locals)
        gMozDefines = dict(cfg_locals.get("defines"))
        gMozSubsts = dict(cfg_locals.get("substs"))
    return gMozDefines, gMozSubsts



#---- particular Data for the Komodo world

class SiloedPythonExeName(black.configure.std.Datum):
    def __init__(self):
        black.configure.std.Datum.__init__(self, "siloedPythonExeName",
            desc="the name of the siloed Python executable")

    def _Determine_Do(self):
        self.applicable = 1
        if sys.platform.startswith("win"):
            buildType = black.configure.items["buildType"].Get()
            if buildType == "debug":
                self.value = "python_d.exe"
            else:
                self.value = "python.exe"
        else:
            self.value = "python"
        self.determined = 1


class SiloedPythonInstallDir(black.configure.std.Datum):
    """The full path to the siloed Python bin directory.
    
    The first thing the Komodo build system does is copy the siloed
    Python (from its location in prebuilt/...) to the appropriate place
    in the mozilla/dist/... area.
    
    Windows dev build:
        $mozSrc/dist/
            bin/
                komodo.exe
                python/         # PyXPCOM site lib (can't use this dir)
            python/             # proposed siloed Python base install dir

    Windows installer build:
        <installdir>/
            Mozilla/
                komodo.exe
            python/             # proposed siloed Python base install dir
                python.exe

    Mac OS X dev build:
        $mozSrc/dist/
            bin/
                komodo
                komodo-bin
                python/         # PyXPCOM site lib (can't use this dir)
        
            Komodo.app/Contents/
                MacOS/
                    komodo      # same as the one above in bin/
                    komodo-bin  # same as the one above in bin/
                Frameworks/
                    Python.framework/... # siloed Python base install dir

    Mac OS X installer build:
        <install-.app-dir>/Contents/
            MacOS/
                komodo
                komodo-bin
            Frameworks/
                Python.framework/...     # siloed Python base install dir

    Linux/Solaris dev build:
        $mozSrc/dist/
            bin/
                komodo.exe
                python/         # PyXPCOM site lib (can't use this dir)
            python/             # siloed Python base install dir

    Linux/Solaris installer build:
        <installdir>/
            lib/
                mozilla/
                    komodo
                    komodo-bin
                komodo.exe
                python/         # siloed Python base install dir

    Basically the above makes this config var easy: the siloed Python in
    dev trees is always in $mozSrc/mozilla/dist/python/... except on Mac
    OS X.
    
    Note: It would be nice if this "appropriate" place worked with how
    Firefox is current distributed (e.g. so that a separate PyXPCOM
    Firefox extension and/or Komodo that installs as an add on to a
    xulrunner install or something like that could work.) No guarantees
    this time around.
    """
    def __init__(self):
        black.configure.std.Datum.__init__(self, "siloedPythonInstallDir",
            desc="the siloed Python bin directory")

    def _Determine_Sufficient(self):
        if self.value is None:
            siloedPythonExeName = black.configure.items['siloedPythonExeName'].Get()
            raise black.configure.ConfigureError(\
                "Could not determine %s (something bad happened)" % self.desc)

    def _Determine_Do(self):
        from os.path import join
        self.applicable = 1
        mozDist = black.configure.items["mozDist"].Get()
        if sys.platform == "darwin":
            macKomodoAppBuildName = black.configure.items['macKomodoAppBuildName'].Get()
            self.value = join(mozDist, macKomodoAppBuildName,
                "Contents", "Frameworks")
        else:
            self.value = join(mozDist, "python")
        self.determined = 1

class SiloedPythonBinDir(black.configure.std.Datum):
    def __init__(self):
        black.configure.std.Datum.__init__(self, "siloedPythonBinDir",
            desc="the siloed Python bin directory")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s (something bad happened)" % self.desc)

    def _Determine_Do(self):
        from os.path import join
        self.applicable = 1
        siloedPythonInstallDir = black.configure.items["siloedPythonInstallDir"].Get()
        if sys.platform == "darwin":
            siloedPyVer = black.configure.items["siloedPyVer"].Get()
            self.value = join(siloedPythonInstallDir, "Python.framework",
                              "Versions", siloedPyVer, "bin")
        else:
            self.value = siloedPythonInstallDir
            if sys.platform != "win32":
                self.value = join(self.value, "bin")
        self.determined = 1

class SiloedPython(black.configure.std.Datum):
    def __init__(self):
        black.configure.std.Datum.__init__(self, "siloedPython",
            desc="path to the siloed Python executable")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s (something bad happened)" % self.desc)

    def _Determine_Do(self):
        from os.path import join
        self.applicable = 1
        siloedPythonBinDir = black.configure.items["siloedPythonBinDir"].Get()
        siloedPythonExeName = black.configure.items["siloedPythonExeName"].Get()
        self.value = join(siloedPythonBinDir, siloedPythonExeName)
        self.determined = 1

class SiloedPythonVersion(black.configure.std.Datum):
    def __init__(self):
        black.configure.std.Datum.__init__(self, "siloedPythonVersion",
            desc="the python version")

    def _Determine_Do(self):
        from os.path import join
        self.applicable = 1
        siloedPythonExeName = black.configure.items["siloedPythonExeName"].Get()
        siloedPythonInstallDir = black.configure.items["siloedPythonInstallDir"].Get()
        if sys.platform == "win32":
            env = ""
            pythonExe = join(siloedPythonInstallDir, siloedPythonExeName)
        elif sys.platform == "darwin":
            env = ""
            pythonExe = join(siloedPythonInstallDir, "Python.framework",
                             "Versions", "*", "bin",
                             siloedPythonExeName)
            try:
                pythonExe = glob.glob(pythonExe)[0]
            except IndexError, ex:
                raise black.configure.ConfigureError(
                    "Could not determine %s: `%s' doesn't exist" % (
                    self.desc, pythonExe))
        else:
            pythonExe = join(siloedPythonInstallDir, "bin",
                             siloedPythonExeName)
            env = "LD_LIBRARY_PATH=%s/lib" % siloedPythonInstallDir
        cmd = '%s %s -c "import sys; sys.stdout.write(\'.\'.join(map(str, sys.version_info[:3])))"'\
              % (env, pythonExe)
        o = os.popen(cmd)
        self.value = o.read()
        self.determined = 1


class SiloedPyVer(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "siloedPyVer",
            desc="the siloed Python <major>.<minor> version")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(
                "Could not determine %s." % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        siloedPythonVersion = black.configure.items["siloedPythonVersion"].Get()
        self.value = '.'.join(siloedPythonVersion.split('.',2)[:2])
        self.determined = 1

class SiloedDistutilsLibDirName(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "siloedDistutilsLibDirName",
            desc="the platform-specific lib dir name that a distutils build will use")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(
                "Could not determine %s." % self.desc)

    def _Determine_Do(self):
        import distutils.util
        self.applicable = 1
        siloedPyVer = black.configure.items["siloedPyVer"].Get()
        siloedPython = black.configure.items["siloedPython"].Get()
        ld_path_list = black.configure.items["LD_LIBRARY_PATH"].Get()

        # the distutils platform name
        cmd = [siloedPython, '-c', "from distutils.util import get_platform; print get_platform()"]
        # Ensure we use the correct LD_LIBRARY_PATH required by the siloed
        # Python executable.
        env = os.environ.copy()
        if sys.platform.startswith("linux"):
            if 'LD_LIBRARY_PATH' in env:
                ld_path_list.append(env['LD_LIBRARY_PATH'])
            env["LD_LIBRARY_PATH"] = os.path.pathsep.join(ld_path_list)
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, env=env)
        status = p.wait()
        platname = p.stdout.read().strip()
        assert status == 0 and platname, \
            "empty distutils platname: running the cmd must have failed: %s" % cmd

        self.value = "lib.%s-%s" % (platname, siloedPyVer)
        self.determined = 1

class HavePy2to3(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "havePy2to3",
            desc="whether the siloed Python has a sufficient 2to3 library for the Komodo build")

    def _Determine_Do(self):
        self.applicable = 1
        siloedPython = black.configure.items["siloedPython"].Get()
        argv = [siloedPython, "-c", "from lib2to3.main import main"]
        p = subprocess.Popen(argv, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        status = p.wait()
        if status:
            self.value = False
        else:
            self.value = True
        self.determined = 1

class SetMozTools(black.configure.SetEnvVar):
    def __init__(self):
        black.configure.SetEnvVar.__init__(self, "MOZ_TOOLS",
            acceptedOptions=("", ["moz-tools="]))

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine value for MOZ_TOOLS. "\
                "Either manually set MOZ_TOOLS or use the --moz-tools "\
                "option.\n")
        # Have to make sure this is the NEW MOZ_TOOLS.
        # - ensure that MOZ_TOOLS/bin/gmake.exe is of version 3.79.1 or greater
        #   (In the old wintools.zip it was version 3.74)
        gmakeExe = os.path.join(self.value, "bin", "gmake.exe")
        if not os.path.isfile(gmakeExe):
            raise black.configure.ConfigureError(\
                "MOZ_TOOLS is bogus, there is no gmake "\
                "executable (%s) there.\n" % gmakeExe)
        cmd = '"%s" --version' % gmakeExe
        o = os.popen(cmd)
        outputLines = o.readlines()
        o.close()
        versionRe = re.compile("^GNU Make version (?P<version>[0-9.]+)")
        minVersion = "3.79.1"
        versionMatch = versionRe.search(outputLines[0])
        if not versionMatch:
            raise black.configure.ConfigureError(\
                "The first line of running '%s' did not "\
                "return a recognized version string syntax." % cmd)
        else:
            version = versionMatch.group("version")
            if version < minVersion:
                raise black.configure.ConfigureError(\
                    "The current version of gmake.exe in "\
                    "your MOZ_TOOLS bin directory is %s. It must be at "\
                    "least version %s. This probably indicates that you have "\
                    "the old wintools.zip package from mozilla.org. You "\
                    "need to get the new one from "\
                    "ftp://ftp.mozilla.org/pub/mozilla/source/wintools.zip "\
                    "and install it SEPARATELY from your Cygwin "\
                    "installation. Alternatively, main/Apps/Mozilla comes "\
                    "with the build tools that it needs (under bin/...) so "\
                    "you should only have to undefine MOZ_TOOLS and rerun "\
                    "the configure step." % (version, minVersion))

    def _Determine_Do(self):
        if sys.platform.startswith("win"):
            self.applicable = 1
            for opt, optarg in self.chosenOptions:
                if opt == "--moz-tools":
                    self.value = os.path.abspath(os.path.normpath(optarg))
                    break
            else:
                if os.environ.has_key(self.name):
                    self.value = os.environ[self.name]
                else:
                    self.value = None
        else:
            self.applicable = 0
        self.determined = 1


class SetKomodoHostname(black.configure.SetEnvVar):
    """A Mozilla patch now requires that KOMODO_HOSTNAME be set when
    Mozilla is run. This is just the hostname of the current machine.
    """
    def __init__(self):
        black.configure.SetEnvVar.__init__(self, "KOMODO_HOSTNAME",
            "the hostname of the current machine")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s.\n" % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        self.value = socket.gethostname()
        self.determined = 1


class KomodoDevDir(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "komodoDevDir",\
            desc="the root Komodo development directory")
    
    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s. You must run 'bk configure' in "\
                "the dir containing the 'Construct' file.\n" % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        # use the current working directory if it has a Construct file
        if os.path.isfile("Construct"):
            self.value = os.getcwd()
        else:
            self.value = None
        self.determined = 1


class MozillaDevDir(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "mozillaDevDir",\
            desc="the root Mozilla development directory")
    
    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s." % self.desc)
        elif not exists(self.value):
            raise black.configure.ConfigureError(
                "%s (%s) does not exist" % (self.desc, self.value))

    def _Determine_Do(self):
        self.applicable = 1
        komodoDevDir = black.configure.items["komodoDevDir"].Get()
        candidates = [
            join(abspath(komodoDevDir), "mozilla"),
        ]
        for candidate in candidates:
            if isdir(candidate):
                self.value = candidate
                break
        else:
            self.value = None
        self.determined = 1


class ProductType(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "productType",
            desc="the Komodo product type")

    def _Determine_Do(self):
        self.applicable = 1
        prettyProductType = black.configure.items["prettyProductType"].Get()
        self.value = prettyProductType.lower()
        assert ' ' not in self.value
        self.determined = 1


class MacKomodoAppInstallName(black.configure.Datum):
    """The .app directory name for the *installed* Komodo on Mac OS X.
    Note that this is different than the *build* name: for both Komodo
    IDE and Edit the .app dir name during the build doesn't include the
    product-type (see `macKomodoAppBuildName`).
    """
    def __init__(self):
        black.configure.Datum.__init__(self, "macKomodoAppInstallName",
            desc="the Komodo .app dir name on Mac OS X (for installation)")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(
                "Could not determine %s." % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        prettyProductType = black.configure.items["prettyProductType"].Get()
        productType = black.configure.items["productType"].Get()
        komodoVersion = black.configure.items["komodoVersion"].Get()
        majorVer = komodoVersion.split('.', 1)[0]
        name = (productType == "openkomodo" and prettyProductType
                or "Komodo %s %s" % (prettyProductType, majorVer))
        self.value = name + ".app"
        self.determined = 1

class MacKomodoAppBuildName(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "macKomodoAppBuildName",
            desc="the Komodo .app dir name on Mac OS X (during the build)")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(
                "Could not determine %s." % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        buildType = black.configure.items["buildType"].Get()
        if buildType == "release":
            self.value = "Komodo.app"
        elif buildType == "debug":
            self.value = "KomodoDebug.app"
        else:
            raise ValueError("unexpected value of buildType: %r" % buildType)
        self.determined = 1

class ProductType(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "productType",
            desc="the Komodo product type",
            acceptedOptions=("", ["product-type="]))
        self.knownValues = ["edit", "openkomodo"]

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s. Use the "\
                "--product-type configure option to specify this. "\
                "The currently valid values for this are %s\n" %\
                (self.desc, self.knownValues))
        else:
            if self.value not in self.knownValues:
                raise black.configure.ConfigureError(\
                    "The specified product type '%s' is "\
                    "not one of the known values: %s" %\
                    (self.value, self.knownValues))

    def _Determine_Do(self):
        self.applicable = 1
        self.value = "edit" # default
        for opt, optarg in self.chosenOptions:
            if opt == "--product-type":
                self.value = optarg
        self.determined = 1


class PrettyProductType(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "prettyProductType",
            desc="the Komodo product type with proper capitalization")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(
                "Could not determine %s." % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        productType = black.configure.items["productType"].Get()
        self.value = {"openkomodo": "OpenKomodo",
                      "edit": "Edit",
                     }[productType]
        self.determined = 1

class ProductTagLine(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "productTagLine",
            desc="the Komodo product tag line",
            acceptedOptions=("", ["product-tag-line="]))

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(
                "Could not determine %s." % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        productType = black.configure.items["productType"].Get()
        self.value = {
            "edit": "Free multi-platform editor that makes it easy to write quality code.",
            "openkomodo": "The IDE for the Open Web",
        }[productType]
        for opt, optarg in self.chosenOptions:
            if opt == "--product-tag-line":
                self.value = optarg
        self.determined = 1

class GnomeDesktopShortcutName(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "gnomeDesktopShortcutName",
            desc="Gnome desktop shortcut filename for Komodo")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(
                "Could not determine %s." % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        productType = black.configure.items["productType"].Get()
        name = (productType == "openkomodo" and "openkomodo"
                or "komodo-"+productType)
        komodoVersion = black.configure.items["komodoVersion"].Get()
        majorVer = komodoVersion.split('.', 1)[0]
        updateChannel = black.configure.items["updateChannel"].Get()
        self.value = "%s-%s%s.desktop" % (name, majorVer,
                                          updateChannel == "nightly" and "-nightly" or "")
        self.determined = 1

class GnomeDesktopName(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "gnomeDesktopName",
            desc="'Name' field for Gnome desktop entry for Komodo")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(
                "Could not determine %s." % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        productType = black.configure.items["productType"].Get()
        prettyProductType = black.configure.items["prettyProductType"].Get()
        name = (productType == "openkomodo" and prettyProductType
                or "Komodo %s" % prettyProductType)
        komodoVersion = black.configure.items["komodoVersion"].Get()
        majorVer = komodoVersion.split('.', 1)[0]
        updateChannel = black.configure.items["updateChannel"].Get()
        self.value = "%s %s%s" % (name, majorVer,
                                  updateChannel == "nightly" and " nightly" or "")
        self.determined = 1

class GnomeDesktopGenericName(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "gnomeDesktopGenericName",
            desc="'GenericName' field for Gnome desktop entry for Komodo")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(
                "Could not determine %s." % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        productType = black.configure.items["productType"].Get()
        self.value = {
            "edit": "Editor",
        }.get(productType, "IDE")
        self.determined = 1

class GnomeDesktopCategories(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "gnomeDesktopCategories",
            desc="'Categories' field for Gnome desktop entry for Komodo")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(
                "Could not determine %s." % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        productType = black.configure.items["productType"].Get()
        self.value = "ActiveState;Application;Development;Editor;Utility;TextEditor;"
        self.determined = 1


class SetMozBinDir(black.configure.SetEnvVar):
    def __init__(self):
        black.configure.SetEnvVar.__init__(self, "KOMODO_MOZBINDIR",
            desc="the Mozilla build's binaries dir (only set for dev builds)")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s. This probably "\
                "means that the Mozilla bin directory could not be "\
                "determined.\n" % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        self.value = black.configure.items["mozBin"].Get()
        self.determined = 1


class PrebuiltPaths(black.configure.Datum):
    # See discussion for "UnsiloedPythonBinDir".
    def __init__(self):
        black.configure.Datum.__init__(self, "prebuiltPaths",
            desc="the full path to the prebuilt directory")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s.\n" % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        platform = black.configure.items["platform"].Get()
        buildType = black.configure.items["buildType"].Get()
        if sys.platform.startswith("linux"):
            candidates = [os.path.abspath(os.path.join(
                            "prebuilt", platform, buildType))]
            self.value = [c for c in candidates if os.path.exists(c)]
        elif sys.platform.startswith("darwin"):
            platName = _getDefaultPlatform()
            self.value = [os.path.abspath(os.path.join(
                                 "prebuilt", "%s" % (platName), buildType))]
        else:
            self.value = [os.path.abspath(os.path.join(
                            "prebuilt", platform, buildType))]
        self.determined = 1

class PerlExe(black.configure.Datum):
    """Determine the full path to a Perl of the given version. The Perl used
    is found as follows:
        - if the "--perlXY" option is specified, then that value is used
        - the first Perl of the correct version on the PATH is used
        - some platform-specific well-known locations are checked
    """
    def __init__(self, version):
        self.version = version  # 2-tuple (<major>, <minor>)
        self.longopt = "perl%s%s" % self.version
        black.configure.Datum.__init__(self, "perl%s%s" % self.version,
            desc="the full path to an unsiloed Perl %s.%s executable" % self.version,
            acceptedOptions=("", [self.longopt + "="]))

    def _getVersion(self, perl):
        ver_pat = re.compile(r"\(revision (\d+)(?:\.\d+)? version (\d+) subversion \d+\)")
        ver_output = _capture_stdout([perl, "-V"]).strip()
        ver_match = ver_pat.search(ver_output)
        if ver_match is None:
            raise black.configure.ConfigureError("""\
could not determine Perl version for '%s':
/%s/ does not match `perl -V` output:
-------------------------------------------------
%s
-------------------------------------------------
""" % (perl, ver_pat.pattern, ver_output))
        ver = (int(ver_match.group(1)), int(ver_match.group(2)))
        return ver

    def _Determine_Sufficient(self):
        buildFlavour = black.configure.items["buildFlavour"].Get()
        if buildFlavour == "full":
            ver = "%s.%s" % self.version
            if not self.value:
                raise black.configure.ConfigureError(
                    "Could not find a Perl %s executable. You must (1) "
                    "identify one with the --%s configure option; or (2) "
                    "put one on your PATH (doesn't have to be first); or "
                    "(3) install one in one of the 'well-known' locations: "
                    "%s" % (ver, self.longopt, self.candidates))
            actualVersion = self._getVersion(self.value)
            if actualVersion != self.version:
                raise black.configure.ConfigureError(\
                    "'%s' is not Perl version %s" % (self.value, ver))
            
    def _Determine_Do(self):
        # Only applicable for Komodo installer builds, but to deal with
        # limited Perl+Cons variable Import/Export we define empty values
        # for non-installer-build configurations.
        self.applicable = 1
        buildFlavour = black.configure.items["buildFlavour"].Get()
        if buildFlavour == "full":
            #XXX Might have to follow symlinks for any values.
            # First see if the Perl was specified with a command argument.
            for opt, optarg in self.chosenOptions:
                if opt == "--"+self.longopt:
                    self.value = optarg
                    return

            # Else, check each Perl on the PATH.
            perl_exe_name = (sys.platform == "win32" and "perl.exe" or "perl")
            for perl in which.whichall(perl_exe_name):
                try:
                    version = self._getVersion(perl)
                except ValueError:
                    pass
                else:
                    if version == self.version:
                        self.value = perl
                        return
            
            # Else, look in some well-known install locations.
            if sys.platform.startswith("win"):
                systemDrive = os.environ.get("SystemDrive", "C:")
                self.candidates = [
                    os.path.join(systemDrive, os.sep, "Perl%s%s" % self.version),
                    os.path.join(systemDrive, os.sep, "Perl"),
                ]
            else:
                self.candidates = []
                basenames = [
                    "ActivePerl-%s.%s*" % self.version,
                    "ActivePerl",
                    "perl-%s.%s*" % self.version,
                    "perl",
                ]
                dirnames = [
                    os.path.expanduser("~/local"),
                    os.path.expanduser("~/opt"),
                    "/opt",
                    "/usr/local",
                    "/usr",
                ]
                for dirname in dirnames:
                    for basename in basenames:
                        self.candidates += glob.glob(os.path.join(dirname, basename, "bin"))
            for bindir in self.candidates:
                perl = os.path.join(bindir, perl_exe_name)
                if not os.path.isfile(perl): continue
                version = self._getVersion(perl)
                if version == self.version:
                    self.value = perl
                    return
        else:
            self.value = ""
        self.determined = 1


class NonMsysPerlExe(black.configure.Datum):
    """The full path to a Perl on Windows that isn't msys Perl.
    The reason is we need a Perl with MD5 (for Cons) and the Perl in
    the MozillaBuild package (likely to be first on a builders PATH)
    doesn't have it -- and I don't have the time to build one for it
    now (gcc on Windows build "fun").
    
    Note that even with the MD5 module, I'm not certain the unix-y msys
    Perl build would work with Komodo build system which is why this
    config var is "nonMsysPerl" rather than just "perlWithMD5".
    """
    def __init__(self):
        black.configure.Datum.__init__(self, "nonMsysPerl",
            desc="non MSYS Perl executable")

    def _isNotMsysPerl(self, perl):
        ver_output = _capture_stdout([perl, "-V"]).strip()
        msys_pat = re.compile(r'Built under msys')
        if msys_pat.search(ver_output):
            return False
        return True

    def _Determine_Sufficient(self):
        if self.applicable and not self.value:
            raise black.configure.ConfigureError(
                "Could not find a non-msys Perl executable. The "
                "current Komodo Cons-based build system needs a Perl "
                "with the MD5 module and the msys Perl from the "
                "MozillaBuild package doesn't have this module. Please "
                "install ActivePerl. If you know that it does, please "
                "report a Komodo bug to fix 'bk configure'.")

    def _Determine_Do(self):
        if sys.platform == "win32":
            self.applicable = True

            # Else, check each Perl on the PATH.
            for perl in which.whichall("perl.exe"):
                if self._isNotMsysPerl(perl):
                    self.value = perl
                    break
            
            # Else, look in some well-known install locations.
            if self.value is None:
                systemDrive = os.environ.get("SystemDrive", "C:")
                self.candidates = [
                    os.path.join(systemDrive, os.sep, "Perl"),
                ]
                if hasattr(self, "version"):
                    self.candidates.insert(0,
                        os.path.join(systemDrive, os.sep, "Perl%s%s" % self.version))

                # check the registry for AS Perl installs
                import _winreg, itertools
                for flags in 0, _winreg.KEY_WOW64_32KEY, _winreg.KEY_WOW64_64KEY:
                    try:
                        parent = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE,
                                                 r"Software\ActiveState\ActivePerl",
                                                 0,
                                                 _winreg.KEY_READ | flags)
                        for i in itertools.count():
                            # EnumKey will raise WindowsError when done
                            version = _winreg.EnumKey(parent, i)
                            directory = _winreg.QueryValue(parent, version)
                            self.candidates.append(os.path.join(directory, "bin"))
                    except WindowsError:
                        pass

                for bindir in self.candidates:
                    perl = os.path.join(bindir, "perl.exe")
                    if os.path.isfile(perl) and self._isNotMsysPerl(perl):
                        self.value = perl
                        break
        self.determined = 1

class PythonExe(black.configure.Datum):
    """Determine the full path to a non-Komodo-siloed Python of the
    given version. The Python used is found as follows:
        - if the "--pythonXY" option is specified, then that value is used
        - the first Python of the correct version on the PATH is used
        - some platform-specific well-known locations are checked
    """
    def __init__(self, version):
        self.version = version  # 2-tuple (<major>, <minor>)
        self.longopt = "python%s%s" % self.version
        black.configure.Datum.__init__(self, "python%s%s" % self.version,
            desc="the full path to an unsiloed Python %s.%s executable" % self.version,
            acceptedOptions=("", [self.longopt+'=']))

    def _getVersion(self, python):
        cmd = '%s -c "import sys; print(hex(sys.hexversion))"' % python
        o = os.popen(cmd)
        hexverstr = o.read().strip()
        retval = o.close()
        if not hexverstr:
            raise ValueError("no output from running '%s'" % cmd)
        if retval:
            raise ValueError("could not determine Python version of '%s'"
                             % python)
        #print "HEXVER: %s" % hexverstr
        hexver = eval(hexverstr)
        major = int((hexver & 0xff000000L) >> 24)
        minor = int((hexver & 0x00ff0000L) >> 16)
        return (major, minor)

    def _Determine_Sufficient(self):
        buildFlavour = black.configure.items["buildFlavour"].Get()
        if buildFlavour == "full":
            ver = "%s.%s" % self.version
            if not self.value:
                raise black.configure.ConfigureError(
                    "Could not find a Python %s executable. You must (1) "
                    "identify one with the --%s configure option; or (2) "
                    "put one on your PATH (doesn't have to be first); or "
                    "(3) install one in one of the 'well-known' locations: "
                    "%s" % (ver, self.longopt, self.candidates))
            actualVersion = self._getVersion(self.value)
            if actualVersion != self.version:
                raise black.configure.ConfigureError(\
                    "'%s' is not Python version %s" % (self.value, ver))

    def _Determine_Do(self):
        # Only applicable for Komodo installer builds, but to deal with
        # limited Perl+Cons variable Import/Export we define empty values
        # for non-installer-build configurations.
        self.applicable = 1
        buildFlavour = black.configure.items["buildFlavour"].Get()
        if buildFlavour == "full":
            #XXX Might have to follow symlinks for any values.
            # First see if the Python was specified with a command argument.
            for opt, optarg in self.chosenOptions:
                if opt == "--"+self.longopt:
                    self.value = optarg
                    return

            # Else, check each Python on the PATH.
            siloedPythonExeName = black.configure.items['siloedPythonExeName'].Get()
            names = set([siloedPythonExeName, 
                         "python", 
                         "python%s.%s" % self.version,
                         "python%s%s" % self.version,
                         ])
            for name in names:
                for python in which.whichall(name):
                    try:
                        version = self._getVersion(python)
                    except ValueError:
                        pass
                    else:
                        if version == self.version:
                            self.value = python
                            return
            
            # Else, look in some well-known install locations.
            if sys.platform.startswith("win"):
                systemDrive = os.environ.get("SystemDrive", "C:") + os.sep
                self.candidates = [
                    os.path.join(systemDrive, "Python%s%s" % self.version),
                    os.path.join(systemDrive, "Python"),
                    os.path.join(systemDrive, "Python", "Python%s%s" % self.version),
                ]
            elif sys.platform == "darwin":
                self.candidates = [
                    "/Library/Frameworks/Python.framework/Versions/%s.%s/bin/python" % self.version,
                    "/usr/local/bin/python%s.%s" % self.version,
                    "/usr/local/bin/python",
                    "/usr/bin/python",
                ]
            else:
                self.candidates = []
                basenames = [
                    "ActivePython-%s.%s*" % self.version,
                    "ActivePython",
                    "python-%s.%s*" % self.version,
                    "python",
                ]
                dirnames = [
                    os.path.expanduser("~/local"),
                    "/opt",
                    "/usr/local",
                    "/usr",
                ]
                for dirname in dirnames:
                    for basename in basenames:
                        self.candidates += glob.glob(os.path.join(dirname, "bin", basename))
            # Candidates are either full paths to the Python binary or the
            # directory in which contains a Python binary.
            for candidate in self.candidates:
                if os.path.isdir(candidate):
                    python = os.path.join(candidate, siloedPythonExeName)
                else:
                    python = candidate
                if not os.path.isfile(python): continue
                version = self._getVersion(python)
                if version == self.version:
                    self.value = python
                    return
        else:
            self.value = ""
        self.determined = 1

class UnsiloedPythonExe(black.configure.Datum):
    # See discussion for "UnsiloedPythonBinDir".
    def __init__(self):
        black.configure.Datum.__init__(self, "unsiloedPythonExe",
            desc="the full path to the unsiloed Python executable")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s (could not find "\
                "python on your path). You have to install Python and put "\
                "it on your path.\n" % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        # We are already running python; it's perfectly clear which one we want
        self.value = sys.executable
        self.determined = 1

class UnsiloedPerlExe(black.configure.Datum):
    # See discussion for "UnsiloedPerlBinDir".
    def __init__(self):
        black.configure.Datum.__init__(self, "unsiloedPerlExe",
            desc="the full path to the unsiloed Perl executable")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s (could not find "\
                "perl on your path). You have to install Perl and put it on "\
                "your path.\n" % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        for opt, optarg in self.chosenOptions:
            if opt == "--perl":
                self.value = os.path.abspath(os.path.normpath(optarg))
                break
        else:
            perlExe = tmShUtil.WhichFollowSymLinks('perl')
            if perlExe:
                self.value = perlExe
            else:
                self.value = None
        self.determined = 1

class KomodoDefaultUserInstallDir(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "komodoDefaultUserInstallDir",
            desc="the default Komodo install directory on a user's machine")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s.\n" % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        platform = black.configure.items["platform"].Get()
        productType = black.configure.items["productType"].Get()
        prettyProductType = black.configure.items["prettyProductType"].Get()
        name_bits = (productType == "openkomodo" and [prettyProductType]
                     or ["Komodo", prettyProductType])
        komodoVersion = black.configure.items["komodoVersion"].Get()
        majorVer = komodoVersion.split('.', 1)[0]
        if platform == "win":
            self.value = "C:\\Program Files\\ActiveState %s %s" \
                         % (' '.join(name_bits), majorVer)
        elif platform == 'darwin':
            self.value = '/Applications/%s.app' % ' '.join(name_bits)
        elif platform in ("linux", "solaris"):
            self.value = "~/%s-%s" % ('-'.join(name_bits), majorVer)
        else:
            self.value = None
        self.determined = 1


class UnsiloedPythonBinDir(black.configure.Datum):
    """When not siloing this is the same as the PythonBinDir but
    when siloing the Komodo build system has need of a Python that
    should not be the siloed Python (because this would put Komodo
    build requirements on the siloed Python, that should only have
    Komodo *run* requirements.
    """
    def __init__(self):
        black.configure.Datum.__init__(self, "unsiloedPythonBinDir",
            desc="the unsiloed Python bin directory")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s (could not find "\
                "python on your path). You have to install Python and put it on "\
                "your path.\n" % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        pythonExeName = "python"
        if sys.platform.startswith("win"):
            pythonExeName = "python.exe"
        pythonExe = tmShUtil.WhichFollowSymLinks(pythonExeName)
        if pythonExe:
            self.value = os.path.dirname(pythonExe)
        else:
            self.value = None
        self.determined = 1


class UnsiloedPerlBinDir(black.configure.Datum):
    """When not siloing this is the same as the PerlBinDir but
    when siloing the Komodo build system has need of a Perl that
    should not be the siloed Perl (because this would put Komodo
    build requirements on the siloed Perl, that should only have
    Komodo *run* requirements.
    
    For example, Cons needs the Perl MD5 module, but the Komodo
    runtime does not necessarily.
    """
    def __init__(self):
        black.configure.Datum.__init__(self, "unsiloedPerlBinDir",
            desc="the unsiloed Perl bin directory")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s (could not find "\
                "perl on your path). You have to install Perl and put it on "\
                "your path.\n" % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        unsiloedPerlExe = black.configure.items["unsiloedPerlExe"].Get()
        self.value = os.path.dirname(unsiloedPerlExe)
        self.determined = 1


#XXX could probably standardize this in Black.
class ConsInstallDir(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "consInstallDir",
            desc="Cons installation directory")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s. You have to "\
                "install Cons and put it on your path.\n" % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        # try the bin directory off of the komodoDevDir
        komodoDevDir = black.configure.items["komodoDevDir"].Get()
        if komodoDevDir:
            self.value = os.path.join(komodoDevDir, "bin") 
        else:
            self.value = None
        self.determined = 1


class ConsVersion(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "consVersion",
            desc="the Cons version number")

    def _Determine_Do(self):
        self.applicable = 1
        perlExe = black.configure.items["unsiloedPerlExe"].Get()
        installDir = black.configure.items["consInstallDir"].Get()
        consExeName = os.path.join(installDir, "cons.pl")
        #XXX I am relying on .pl->Perl.exe association on windows here
        #    I should not.
        o = os.popen('%s %s -V' % (perlExe, consExeName))
        consVersionLine = o.read()
        consVersionMatch = re.compile('This is Cons ([0-9\.]+) ').\
            search(consVersionLine)
        if consVersionMatch:
            self.value = consVersionMatch.group(1) 
        else:
            self.value = None
        self.determined = 1

class MD5PerlModuleInstalled(black.configure.BooleanDatum):
    def __init__(self):
        black.configure.Datum.__init__(self, "MD5PerlModuleInstalled",
            desc="MD5 Perl module is installed")

    def _Determine_Sufficient(self):
        if not self.value:
            raise black.configure.ConfigureError(\
                "The MD5 Perl module is not installed in "\
                "your generic Perl installation. You "\
                "have to install it.\n")

    def _Determine_Do(self):
        self.applicable = 1
        unsiloedPerlBinDir = black.configure.items["unsiloedPerlBinDir"].Get()
        o = os.popen('%s -mMD5 -e "print \'madeit\';"' %\
            os.path.join(unsiloedPerlBinDir, "perl"))
        if o.read() == 'madeit':
            self.value = 1
        else:
            self.value = 0
        self.determined = 1


class WithSymbols(black.configure.BooleanDatum):
    def __init__(self):
        black.configure.Datum.__init__(self, "withSymbols",
            desc="should generate debugging symbols in C/C++ compilation of "\
                 "Komodo components on Linux",
            acceptedOptions=("", ["with-symbols", "without-symbols"]))

    def _Determine_Do(self):
        # Only really applicable on Linux but Cons will freak out if
        # $withSymbols is not defined for its Export() command on Windows.
        self.applicable = 1
        self.value = 0   # do *not* include debugging symbols be default
        for opt, optarg in self.chosenOptions:
            if opt == "--with-symbols":
                self.value = 1
            elif opt == "--without-symbols":
                self.value = 0
        self.determined = 1


class WithCrashReportSymbols(black.configure.BooleanDatum):
    def __init__(self):
        black.configure.Datum.__init__(self, "withCrashReportSymbols",
            desc="should generate special crash report symbols in C/C++ "\
                 "compilation of Komodo components",
            acceptedOptions=("", ["with-crashreport-symbols", "without-crashreport-symbols"]))

    def _Determine_Do(self):
        self.applicable = 1
        self.value = 0   # do *not* include crash report symbols be default
        for opt, optarg in self.chosenOptions:
            if opt == "--with-crashreport-symbols":
                self.value = 1
            elif opt == "--without-crashreport-symbols":
                self.value = 0
        self.determined = 1

class WithTests(black.configure.BooleanDatum):
    def __init__(self):
        black.configure.Datum.__init__(self, "withTests",
            desc="build Komodo with testing components",
            acceptedOptions=("", ["with-tests", "without-tests"]))
    def _Determine_Do(self):
        self.applicable = 1
        configTokens = black.configure.items["configTokens"].Get()
        buildFlavour = black.configure.items["buildFlavour"].Get()
        if buildFlavour == "full":
            self.value = False
        else:
            self.value = True
        for opt, optarg in self.chosenOptions:
            if opt == "--with-tests":
                if not self.value: configTokens.append("tests")
                self.value = True
            elif opt == "--without-tests":
                if self.value: configTokens.append("notests")
                self.value = False
        self.determined = 1

class WithCasper(black.configure.BooleanDatum):
    def __init__(self):
        black.configure.Datum.__init__(self, "withCasper",
            desc="build Komodo with Casper",
            acceptedOptions=("", ["with-casper", "without-casper"]))
    def _Determine_Do(self):
        self.applicable = 1
        configTokens = black.configure.items["configTokens"].Get()
        buildFlavour = black.configure.items["buildFlavour"].Get()
        if buildFlavour == "full":
            self.value = False
        else:
            self.value = True
        for opt, optarg in self.chosenOptions:
            if opt == "--with-casper":
                if not self.value: configTokens.append("casper")
                self.value = True
            elif opt == "--without-casper":
                if self.value: configTokens.append("nocasper")
                self.value = False
        self.determined = 1

class WithJSLib(black.configure.BooleanDatum):
    def __init__(self):
        black.configure.Datum.__init__(self, "withJSLib",
            desc="build Komodo with jslib")
    def _Determine_Do(self):
        self.applicable = 1
        self.value = black.configure.items["withCasper"].Get()
        self.determined = 1

class WithDocs(black.configure.BooleanDatum):
    def __init__(self):
        black.configure.Datum.__init__(self, "withDocs",
            desc="include Komodo's docs",
            acceptedOptions=("", ["with-docs", "without-docs"]))
    def _Determine_Do(self):
        self.applicable = 1
        configTokens = black.configure.items["configTokens"].Get()
        productType = black.configure.items["productType"].Get()
        buildFlavour = black.configure.items["buildFlavour"].Get()
        self.value = True  # DO include by default
        if buildFlavour == "dev":
            self.value = False  # But not for dev builds
        for opt, optarg in self.chosenOptions:
            if opt == "--with-docs":
                if not self.value: configTokens.append("docs")
                self.value = True
            elif opt == "--without-docs":
                self.value = False
        self.determined = 1

class WithKomodoCix(black.configure.BooleanDatum):
    def __init__(self):
        black.configure.Datum.__init__(self, "withKomodoCix",
            desc="build komodo.cix and the komodo JS API docs",
            acceptedOptions=("", ["with-komodo-cix", "without-komodo-cix"]))
    def _Determine_Do(self):
        self.applicable = 1
        withDocs = black.configure.items["withDocs"].Get()
        self.value = withDocs  # Only include it when we're making docs.
        for opt, optarg in self.chosenOptions:
            if opt == "--with-komodo-cix":
                self.value = 1
            elif opt == "--without-komodo-cix":
                self.value = 0
        self.determined = 1

class WithWatchdogFSNotifications(black.configure.BooleanDatum):
    def __init__(self):
        black.configure.Datum.__init__(self, "withWatchdogFSNotifications",
            desc="Use the new filesystem notification module based on watchdog",
            acceptedOptions=("", ["with-watchdog-fs-notifications", "without-watchdog-fs-notifications"]))
    def _Determine_Do(self):
        self.applicable = 1
        configTokens = black.configure.items["configTokens"].Get()
        productType = black.configure.items["productType"].Get()
        self.value = 1 # included by default
        for opt, optarg in self.chosenOptions:
            if opt == "--with-watchdog-fs-notifications":
                self.value = 1
            elif opt == "--without-watchdog-fs-notifications":
                self.value = 0
        self.determined = 1

class WithPGOGeneration(black.configure.BooleanDatum):
    def __init__(self):
        black.configure.Datum.__init__(self, "withPGOGeneration",
            desc="Generate profile guided optimization data",
            acceptedOptions=("", ["with-pgo-generation", "without-pgo-generation"]))
    def _Determine_Do(self):
        self.applicable = 1
        configTokens = black.configure.items["configTokens"].Get()
        self.value = 0 # off by default
        for opt, optarg in self.chosenOptions:
            if opt == "--with-pgo-generation":
                self.value = 1
            elif opt == "--without-pgo-generation":
                self.value = 0
        self.determined = 1

class WithPGOCollection(black.configure.BooleanDatum):
    def __init__(self):
        black.configure.Datum.__init__(self, "withPGOCollection",
            desc="Collect profile guided optimization data",
            acceptedOptions=("", ["with-pgo-collection", "without-pgo-collection"]))
    def _Determine_Do(self):
        self.applicable = 1
        configTokens = black.configure.items["configTokens"].Get()
        self.value = 0 # off by default
        for opt, optarg in self.chosenOptions:
            if opt == "--with-pgo-collection":
                self.value = 1
            elif opt == "--without-pgo-collection":
                self.value = 0
        self.determined = 1


class LudditeVersion(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "ludditeVersion",
            desc="luddite version")

    def _Determine_Do(self):
        self.applicable = 1

        cmd = '%s src/udl/luddite.py --version' % (sys.executable)
        i, o = os.popen2(cmd)
        i.close()
        output = o.read()
        retval = o.close()
        if retval:
            raise black.configure.ConfigureError(\
                "error running '%s'" % cmd)
        self.value = output.strip().split(None, 1)[1]
        self.determined = 1

class IsGTK2Siloed(black.configure.BooleanDatum):
    # XXX keep this around for potential future siloing
    def __init__(self):
        black.configure.Datum.__init__(self, "isGTK2Siloed",
            desc="a boolean indicating if GTK2 is siloed with this build")

    def _Determine_Do(self):
        buildFlavour = black.configure.items["buildFlavour"].Get()
        self.applicable = 1
        self.value = 0   
        self.determined = 1


class UniversalApp(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "universal",
            desc="build Komodo as a universal binary",
            acceptedOptions=("", ["with-universal", "without-universal"]))

    def _Determine_Do(self):
        self.applicable = 1
        self.value = 0
        for opt, optarg in self.chosenOptions:
            if opt == "--with-universal":
                self.value = 1
            elif opt == "--without-universal":
                self.value = 0
        self.determined = 1


class MozResourcesDir(black.configure.Datum):
    """The resource directory is where chrome, components, etc. go"""
    def __init__(self):
        black.configure.Datum.__init__(self, "mozResourcesDir",
            desc="the Komodo resources directory")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s.\n" % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        self.value = black.configure.items["mozBin"].Get()
        self.determined = 1

class MozComponentsDir(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "mozComponentsDir",
            desc="the Mozilla components directory")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s.\n" % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        base = black.configure.items["mozResourcesDir"].Get()
        self.value = os.path.join(base, "components")
        self.determined = 1

class MozChromeDir(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "mozChromeDir",
            desc="the Mozilla chrome directory")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s.\n" % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        base = black.configure.items["mozResourcesDir"].Get()
        self.value = os.path.join(base, "chrome")
        self.determined = 1

class MozPluginsDir(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "mozPluginsDir",
            desc="the Mozilla plugins directory")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s.\n" % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        base = black.configure.items["mozResourcesDir"].Get()
        self.value = os.path.join(base, "plugins")
        self.determined = 1


class MozExtensionDir(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "mozExtensionDir",
            desc="the Mozilla plugins directory")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s.\n" % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        base = black.configure.items["mozResourcesDir"].Get()
        self.value = os.path.join(base, "extensions")
        self.determined = 1

#TODO: Change the name of this to "komodoPyXPCOMSiteDir" or something
#      like that.
class KomodoPythonUtilsDir(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "komodoPythonUtilsDir",
            desc="Komodo's Python 'site lib' dir")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s." % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        # The "python" directory under the main komodo/mozilla/firefox
        # executable is automatically added to sys.path by PyXPCOM (when
        # it loads). We'll add a "komodo" sub-element to this (to keep
        # the separation clear) and use a "komodo.pth" file to add that
        # subdir.
        #TODO: put this discussion in the install_layout spec.
        #TODO: ensure this works for dev builds as well
        base = black.configure.items["mozResourcesDir"].Get()
        self.value = os.path.join(base, "python", "komodo")
        self.determined = 1


class SetPath(black.configure.SetPathEnvVar):
    # On Windows 7 this must be serialized to `bkconfig.bat` *after* the call to
    # "setenv-moz-msvcN.bat" to ensure that "mozilla\bin-win32" is on the PATH
    # before "C:\mozilla-build\msys\bin" so that Komodo's "patch.exe" is the
    # one that gets used.
    serializationOrdinal = 150

    def __init__(self):
        if sys.platform.startswith("win"):
            pathExt = os.environ.get("PATHEXT", None)
            if pathExt:
                exts = pathExt.split(os.pathsep)
            else:
                exts = [".EXE", ".COM", ".BAT"]
        else:
            exts = []
        black.configure.SetPathEnvVar.__init__(self, "PATH",
            serializeAs=["env"], exts=exts)

    def _Determine_Do(self):
        self.applicable = 1
        self.value = []
        #---- add other require entries to the path
        applicable = black.configure.items["systemDirs"].Determine()
        if applicable:
            systemDirs = black.configure.items["systemDirs"].Get()
        else:
            systemDirs = []

        # Add the local plat-specific bin dir, if any.
        platBinDir = join(dirname(abspath(__file__)), "mozilla",
            "bin-%s" % (sys.platform))
        if exists(platBinDir):
            self.value.append(platBinDir)

        # add the Python bin directory
        applicable = black.configure.items["siloedPythonBinDir"].Determine()
        if applicable:
            d = black.configure.items["siloedPythonBinDir"].Get()
            if d and not self.Contains(d) and not d in systemDirs:
                self.value.append(d)

        # add the Cons install directory
        #TODO remove this if not necessary
        applicable = black.configure.items["consInstallDir"].Determine()
        if applicable:
            d = black.configure.items["consInstallDir"].Get()
            if d and not self.Contains(d) and not d in systemDirs:
                self.value.append(d)

        # add the Perl bin directory
        applicable = black.configure.items["unsiloedPerlBinDir"].Determine()
        if applicable:
            d = black.configure.items["unsiloedPerlBinDir"].Get()
            if d and not self.Contains(d) and not d in systemDirs:
                self.value.append(d)

        #XXX Should eventually add the "Komodo install image *bin* dir"
        #    when that gets added back. This is the dir where the Komodo
        #    shim will be (for plats that have that). See
        #    specs/tech/install_layout.txt for details.
        # add the Mozilla bin directory
        applicable = black.configure.items["mozBin"].Determine()
        if applicable:
            d = black.configure.items["mozBin"].Get()
            if d and not self.Contains(d) and not d in systemDirs:
                self.value.append(d)

        applicable = black.configure.items["mozDevelBin"].Determine()
        if applicable:
            d = black.configure.items["mozDevelBin"].Get()
            if d and not self.Contains(d) and not d in systemDirs:
                self.value.append(d)

        # The 'mk' bin dir.
        d = join(dirname(abspath(__file__)), "contrib", "mk", "bin")
        if d and not self.Contains(d):
            self.value.append(d)

        self.determined = 1

    def _Serialize_AsBatch(self, stream):
        # for now append to PATH because of interaction with vcvars32.bat
        systemDirs = black.configure.items["systemDirs"].Get()
        paths = self.value + ["%PATH%"] + systemDirs
        stream.write('set PATH=%s\n' % (os.pathsep.join(paths)))

    def _Serialize_AsBash(self, stream):
        # for now append to PATH because of interaction with vcvars32.bat
        systemDirs = black.configure.items["systemDirs"].Get()
        paths = self.value + ["$PATH"] + systemDirs
        pathsep = os.pathsep
        if sys.platform.startswith("win"):
            for i, path in enumerate(paths):
                if len(path) > 1 and path[1] == ":":
                    path = "/%s/%s" % (path[0], path[3:])
                path = path.replace(os.sep, "/")
                paths[i] = path
            pathsep = ":"
        stream.write('export PATH=%s\n' % (pathsep.join(paths)))


class SetupMozEnv(black.configure.RunEnvScript):
    def __init__(self):
        black.configure.RunEnvScript.__init__(self, "setupMozEnv",
            desc="setup Mozilla build environment")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise ConfigureError("Could not determine %s.\n" % self.desc)
        elif not exists(self.value):
            raise ConfigureError("%s (%s) does not exist"
                                 % (self.desc, self.value))

    def _Determine_Do(self):
        if sys.platform == "win32":
            self.applicable = 1
            mozillaDevDir = black.configure.items['mozillaDevDir'].Get()
            compiler = black.configure.items['compiler'].Get()
            compiler_ver = compiler
            if compiler_ver.startswith("vc"):
                compiler_ver = compiler_ver[2:]
            setenvFile = "setenv-moz-msvc%s.bat" % compiler_ver
            setenvFile = join(mozillaDevDir, setenvFile)
            if not exists(setenvFile):
                # No version available...
                mozBuild = os.environ.get("MOZILLABUILD")
                startMozFile = "start-msvc%s.bat" % compiler_ver
                startMozFile = join(mozBuild, startMozFile)
                if not exists(startMozFile):
                    raise ConfigureError("No Mozilla environment for %s "
                                         "available" % compiler)
                # Try to build our file from the Mozilla one
                try:
                    with open(setenvFile, "w") as out_file:
                        out_file.write("@rem This file is automatically "
                                       "generated from Mozilla's "
                                       "start-msvc%s.bat.  Do not modify this "
                                       "file manually; just delete it and "
                                       "re-run bk configure.\n" % compiler_ver)
                        out_file.write("@pushd")
                        with open(startMozFile, "r") as in_file:
                            for line in in_file:
                                if r'msys\bin\bash" --login -i' in line:
                                    continue
                                # This file is in the wrong directory; be dumber
                                # about locating MozillaBuild.
                                line = line.replace("%~dp0",
                                                    os.environ["MOZILLABUILD"])
                                out_file.write(line)
                        # Add in extra paths
                        for prefix in ("msys/local/bin", "msys/bin", "wget",
                                       "info-zip", "wix-351728", "yasm"):
                            out_file.write("set PATH=%%MOZILLABUILD%%\%s;%%PATH%%\n"
                                           % prefix.replace("/", os.sep))
                        # Include NSIS just so mozilla configure doesn't complain
                        for suffix in "nsis-2.46u", "nsis-2.33u", "nsis-2.22":
                            out_file.write("set PATH=%%PATH%%;%%MOZILLABUILD%%\%s\n"
                                           % suffix.replace("/", os.sep))
                        # Force the first directory on the path to be our own custom
                        # bin directory to use our patch.exe
                        out_file.write("set PATH=%s;%%PATH%%\n" %
                                       join(dirname(abspath(__file__)), "mozilla",
                                            "bin-%s" % (sys.platform)))
                        out_file.write("popd");
                except:
                    os.remove(setenvFile) # Remove broken file
                    raise
            if not exists(setenvFile):
                raise ConfigureError("No Mozilla environment for %s "
                                     "available" % compiler)
            self.value = setenvFile
        else:
            self.applicable = 0
            self.value = None
        self.determined = 1



class SetLdLibraryPath(black.configure.SetPathEnvVar):
    def __init__(self):
        if sys.platform == 'darwin':
            self._envname = "DYLD_LIBRARY_PATH"
        else:
            self._envname = "LD_LIBRARY_PATH"
        black.configure.SetPathEnvVar.__init__(self, self._envname,
                                                   serializeAs=["env"])
            
    def _Determine_Do(self):
        if sys.platform.startswith("linux") or sys.platform == "darwin":
            self.applicable = 1
            self.value = []
            #---- add required entries to the path
            # add the Mozilla bin directory
            # (This is only needed on Mac to let bk test find the dependent
            # libraries for the _xpcom Python module)
            applicable = black.configure.items["mozBin"].Determine()
            if applicable:
                d = black.configure.items["mozBin"].Get()
                if not self.Contains(d):
                    self.value.append(d)
##XXX
##XXX Is this necessary with the new build system now?
##XXX
            # Add the siloed Python lib dir (in the install tree) for
            # installer builds so that Python extensions (like our build
            # of sgmlop) can be built against it.
            if sys.platform.startswith("linux"):
                pythonExecutable = black.configure.items["siloedPython"].Get()
                pythonLibPath = join(dirname(dirname(pythonExecutable)), "lib")
                if not self.Contains(pythonLibPath):
                    self.value.append(pythonLibPath)
        else:
            self.applicable = 0
        self.determined = 1

    def _Serialize_AsBatch(self, stream):
        # for append to LD_LIBRARY_PATH
        
        stream.write('set %s=%s;%%%s%%\n' % \
                     (self._envname, os.pathsep.join(self.value),
                      self._envname))

    def _Serialize_AsBash(self, stream):
        # for now append to LD_LIBRARY_PATH 
        stream.write('export %s=%s:$%s\n' % \
                     (self._envname, os.pathsep.join(self.value),
                      self._envname))


class SetMozillaFiveHome(black.configure.SetPathEnvVar):
    """This needs to be set properly on Linux to get PyXPCOM to work in
    `bk start mozpython` (and `bk start python`).
    """
    def __init__(self):
        black.configure.SetPathEnvVar.__init__(self, "MOZILLA_FIVE_HOME",
            serializeAs=["env"])

    def _Determine_Do(self):
        if sys.platform.startswith("linux") or sys.platform == "darwin":
            self.applicable = 1
            self.value = black.configure.items["mozBin"].Get()
        else:
            self.applicable = 0
        self.determined = 1

class SetPythonHome(black.configure.SetPathEnvVar):
    """This needs to be set properly on Windows to get PyXPCOM to work in
    `bk start mozpython`.
    """
    def __init__(self):
        black.configure.SetPathEnvVar.__init__(self, "PYTHONHOME",
            serializeAs=["env"])

    def _Determine_Do(self):
        if sys.platform == "win32":
            self.applicable = 1
            mozDist = black.configure.items["mozDist"].Get()
            self.value = join(mozDist, "python")
        else:
            self.applicable = 0
        self.determined = 1

class SetPythonPath(black.configure.SetPathEnvVar):
    def __init__(self):
        black.configure.SetPathEnvVar.__init__(self, "PYTHONPATH",
            serializeAs=["env"], exts=[".py", ".pyc"])

    def _Determine_Do(self):
        self.applicable = 1
        self.value = []
        #---- add other require entries to the path
        # add the Komodo Python utils dir
        applicable = black.configure.items["komodoPythonUtilsDir"].Determine()
        if applicable:
            d = black.configure.items["komodoPythonUtilsDir"].Get()
            if not self.Contains(d):
                self.value.append(d)
        # add the Mozilla python lib directory
        applicable = black.configure.items["mozBin"].Determine()
        if applicable:
            d = os.path.join(black.configure.items["mozBin"].Get(), "python")
            if not self.Contains(d):
                self.value.append(d)
        self.determined = 1

class SetMozSrc(black.configure.SetEnvVar):
    """The mozSrc/MOZ_SRC for the Komodo build. This is the mozilla source
    directory with a "mozilla" subdir.

    Usage:
        bk configure
            Defaults to the value of $MOZ_SRC or, failing that "latest".
        bk configure --moz-src=latest
            Looks for the latest registered moz build for this Komodo
            version.
        bk configure --moz-src=blessed
            Looks for the latest *blessed* regsitered moz build for this
            Komodo version. "Blessed" builds are those marked for use for
            production/release-quality builds.

        bk configure --moz-src=<path>
            Uses the given path.
    """
    def __init__(self):
        black.configure.SetEnvVar.__init__(self, "MOZ_SRC",
            acceptedOptions=("", ["moz-src="]))

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(
                "Could not determine value for MOZ_SRC. "
                "Either manually set MOZ_SRC or use the --moz-src option.\n")

    def _Determine_Do(self):
        self.applicable = 1
        mozObjDir = black.configure.items['mozObjDir'].Get()
        # The 'mozObjDir' is either one or two dirs deeper than
        # 'mozSrc'.
        if basename(mozObjDir) == "mozilla":
            self.value = dirname(mozObjDir)
        else:
            self.value = dirname(dirname(mozObjDir))
        self.determined = 1


class MozConfig(black.configure.Datum):
    """Get the mozilla config that was used for building Mozilla-devel.
    
    This uses the already set MOZ_SRC config item to get the right file.
    """
    def __init__(self):
        black.configure.Datum.__init__(self, "mozConfigFile",
            desc="the config used for building the Mozilla source tree")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s. This probably "\
                "means that MOZ_SRC could not be determined.\n" % self.desc)

    def _Determine_Do(self):
        sys.path.insert(0, join("mozilla", "support"))
        try:
            import regmozbuild
        except ImportError:
            del sys.path[0]

        self.applicable = 1
        moz_src = black.configure.items['MOZ_SRC'].Get()
        buildDir = os.path.dirname(moz_src)
        if sys.platform.startswith("win") and buildDir[1] == ":":
            # on Windows, drive letters are case-insensitive; lower it here
            # to match MSYS (pwd -W).
            buildDir = buildDir[0].lower() + buildDir[1:]
        srcTreeName = os.path.basename(moz_src)
        self.value = regmozbuild.find_latest_mozilla_config(buildDir=buildDir,
                                                    srcTreeName=srcTreeName)
        self.determined = 1


class MozSrc(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "mozSrc",
            desc="the base of the Mozilla source tree")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s. This probably "\
                "means that MOZ_SRC could not be determined.\n" % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        self.value = black.configure.items['MOZ_SRC'].Get()
        self.determined = 1


class MozObjDir(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "mozObjDir",
            acceptedOptions=("", ["moz-src=","moz-objdir="]),
            desc="the base of the Mozilla build, i.e. the 'obj' dir")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s. This probably "\
                "means that MOZ_SRC could not be determined.\n" % self.desc)

    def _get_moz_src_scheme(self):
        for opt, optarg in self.chosenOptions:
            if opt == "--moz-src":
                scheme = optarg
                break
        else:
            if os.environ.has_key("MOZ_SRC"):
                scheme = os.environ["MOZ_SRC"]
            else:
                scheme = "latest"
        return scheme

    def _find_registered_mozobjdir(self, blessed, mozObjDir=None):
        sys.path.insert(0, join("mozilla", "support"))
        try:
            import regmozbuild
        finally:
            del sys.path[0]

        komodoShortVersion = black.configure.items["komodoShortVersion"].Get()
        buildType = black.configure.items["buildType"].Get()
        mozObjDir = regmozbuild.find_latest_build(
            komodoVersion=komodoShortVersion,
            buildType=buildType,
            blessed=blessed,
            mozObjDir=mozObjDir,
        )
        return mozObjDir

    def _mozobjdir_from_mozsrc(self, mozsrc):
        srcdir = os.path.join(mozsrc, 'mozilla')
        # XXX we cannot get the version number yet, so try both
        make = 'make'
        env = None
        if sys.platform == "win32":
            make = 'mozmake.exe'
            # Windows mozmake requires setting MSYSTEM environ variable.
            env = os.environ.copy()
            env['MSYSTEM'] = 'MINGW32'
        cmd = make + ' -s -f client.mk echo-variable-OBJDIR'
        p = subprocess.Popen(cmd, cwd=srcdir, shell=True, env=env,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        objdir = stdout.splitlines()[-1].strip()
        if p.returncode != 0:
            raise black.configure.ConfigureError(\
                "error running %r, stderr:\n%s\n" % (cmd, stderr))

        if sys.platform == "win32":
            if re.match(r"/\w/", objdir):
                # This is an msys path:
                #   /c/trentm/as/Mozilla-devel/build/...
                # Convert that to something sane.
                #   C:\trentm\as\Mozilla-devel\build\...
                objdir = objdir[1:] # drop leading '/'
                objdir = objdir[0].upper() + ':' + objdir[1:].replace('/', '\\')
            elif re.match(".:/", objdir):
                # This is a half-mingw path, with forward slashes
                objdir = objdir.replace('/', '\\')
            else:
                assert re.match(".:\\", objdir), \
                    "unexpected objdir path on Windows: " + objdir

        return objdir

    def _get_mozilla_objdir(self):
        scheme = self._get_moz_src_scheme()
        if scheme == "blessed":
            # blessed: This is a special value meaning "find the
            # appropriate registered 'blessed' moz build for this Komodo
            # version".
            return self._find_registered_mozobjdir(True)
        elif scheme == "latest":
            # latest: This is a special value meaning "find the latest
            # registered moz build for this Komodo version".
            return self._find_registered_mozobjdir(False)
        else:
            # 'scheme' is a path to the moz-src tree.
            #
            # Unforunately this method always picks up the *last*-used
            # obj-dir in the given moz-src tree.
            mozSrc = abspath(normpath(expanduser(scheme)))
            return self._mozobjdir_from_mozsrc(mozSrc)

    def _use_mozilla_objdir(self, objdir):
        return self._find_registered_mozobjdir(False, mozObjDir=objdir)
    
    def _Determine_Do(self):
        self.applicable = 1
        method = "moz-src"
        method_arg = None
        for opt, optarg in self.chosenOptions:
            if opt == "--moz-src":
                method = "moz-src"
            elif opt == "--moz-objdir":
                method = "moz-objdir"
                method_arg = optarg

        if method == "moz-src":
            self.value = self._get_mozilla_objdir()
        elif method == "moz-objdir":
            self.value = self._use_mozilla_objdir(method_arg)
        else:
            raise black.configure.ConfigureError("bogus method: %r" % method)

        self.determined = 1

class MozDevelDist(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "mozDevelDist",
            desc="the base of the Mozilla-devel build, i.e. the 'dist' dir")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s. This probably "\
                "means that MOZ_SRC could not be determined.\n" % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        mozObjDir = black.configure.items['mozObjDir'].Get()
        self.value = os.path.join(mozObjDir, "dist")
        self.determined = 1

class MozDevelBin(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "mozDevelBin",
            desc="the Mozilla Development bin directory")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s. This probably "\
                "means that MOZ_SRC could not be determined.\n" % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        mozDist = black.configure.items['mozDevelDist'].Get()
        self.value = os.path.join(mozDist, 'bin')
        self.determined = 1

class MozDist(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "mozDist",
            desc="the base of the Komodo build, i.e. the 'dist' dir")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s. This probably "\
                "means that MOZ_SRC could not be determined.\n" % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        self.value = black.configure.items['mozDevelDist'].Get()
        self.determined = 1

class SetMozStatePath(black.configure.SetEnvVar):
    """The Mozilla/mach state path, MOZBUILD_STATE_PATH.
    """
    def __init__(self):
        black.configure.SetEnvVar.__init__(self, "MOZBUILD_STATE_PATH",
            "The Mozilla mach state directory")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(
                "Could not determine value for %s.\n" % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        self.value = join(dirname(black.configure.items['mozSrc'].Get()),
                          "moz-state")
        self.determined = 1

class MozBin(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "mozBin",
            desc="the Komodo bin directory")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s. This probably "\
                "means that MOZ_SRC could not be determined.\n" % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        mozDist = black.configure.items['mozDist'].Get()
        if sys.platform.startswith('darwin'):
            macKomodoAppBuildName = black.configure.items['macKomodoAppBuildName'].Get()
            self.value = os.path.join(mozDist, macKomodoAppBuildName,
                                      "Contents", "MacOS")
        else:
            self.value = os.path.join(mozDist, 'bin')
        self.determined = 1

class MozApp(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "mozApp",
            desc="the Mozilla application, i.e. the thing you start to run Komodo")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s. This probably "\
                "means that MOZ_SRC could not be determined.\n" % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        buildType = black.configure.items['buildType'].Get()
        if sys.platform == 'darwin':
            # we 'open Komodo.app' rather than execute the komodo binary
            mozDist = black.configure.items['mozDist'].Get()
            macKomodoAppBuildName = black.configure.items['macKomodoAppBuildName'].Get()
            self.value = os.path.join(mozDist, macKomodoAppBuildName)
        else:
            mozBin = black.configure.items['mozBin'].Get()
            if sys.platform.startswith("win"):
                self.value = os.path.join(mozBin, "komodo.exe")
            else:
                self.value = os.path.join(mozBin, "komodo")
        self.determined = 1

class MozExe(black.configure.Datum):
    def __init__(self):
        # Note: This is *slightly* different that "mozApp".
        black.configure.Datum.__init__(self, "mozExe",
            desc="the Mozilla excutable, i.e. the thing you start to run Komodo")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s. This probably "\
                "means that MOZ_SRC could not be determined.\n" % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        if sys.platform == "darwin":
            mozBin = black.configure.items['mozBin'].Get()
            self.value = os.path.join(mozBin, "komodo")
        else:
            self.value = black.configure.items['mozApp'].Get()
        self.determined = 1

digits = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

def str2int(num,base=10):
    if not num:
        return 0
    else:
        result = ""
        for c in num:
            if c not in digits[:base]:
                break
            result += c
        return int(result)

class MozVersion(black.configure.Datum):
    # note, this is the version in the source tree
    # ff 1.0 == moz 1.7
    # ff 1.1 == moz 1.8
    def __init__(self):
        black.configure.Datum.__init__(self, "mozVersion",
            desc="the Mozilla source version (eg. 1.7, 1.8)")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s. This probably "\
                "means that MOZ_SRC could not be determined.\n" % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        mozSrc = os.path.join(black.configure.items['MOZ_SRC'].Get(), 'mozilla')
        milestone = os.path.join(mozSrc, 'config', 'milestone.pl')
        if sys.platform.startswith("win"):
            # Mozilla's milestone.pl stupidly only works with UNIX path
            # separators. Perl is fine with that on windows so just use those.
            milestone = milestone.replace('\\', '/')

        perlExe = black.configure.items["unsiloedPerlExe"].Get()
        cmd = '%s %s -topsrcdir %s' % (perlExe, milestone, mozSrc)
        i, o, e = os.popen3(cmd)
        i.close()
        output = o.read()
        o.close()
        stderr = e.read()
        retval = e.close()
        if retval:
            raise black.configure.ConfigureError(
                "error running '%s': stdout='%r' stderr='%r'"
                % (cmd, output, stderr))
    
        # only use the first 2 parts of the version
        ver = output.split('.')[:2]
        # strip extra info, such as 8b2
        ver[1] = "%d" % str2int(ver[1]) 
        self.value = '.'.join(ver)
        self.determined = 1

class MozVersionNumber(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "mozVersionNumber",
            desc="the Mozilla source minor version number")
    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError("Could not determine %s")
    def _Determine_Do(self):
        self.applicable = 1
        mozSrc = os.path.join(black.configure.items['MOZ_SRC'].Get(), 'mozilla')
        milestone = os.path.join(mozSrc, 'config', 'milestone.pl')
        if sys.platform.startswith("win"):
            # Mozilla's milestone.pl stupidly only works with UNIX path
            # separators. Perl is fine with that on windows so just use those.
            milestone = milestone.replace('\\', '/')

        perlExe = black.configure.items["unsiloedPerlExe"].Get()
        cmd = '%s %s -topsrcdir %s' % (perlExe, milestone, mozSrc)
        i, o, e = os.popen3(cmd)
        i.close()
        output = o.read()
        o.close()
        stderr = e.read()
        retval = e.close()
        if retval:
            raise black.configure.ConfigureError(
                "error running '%s': stdout='%r' stderr='%r'"
                % (cmd, output, stderr))
    
        # Only use the first 3 parts of the version, strip extra info,
        # such as 8b2 by using str2int.
        ver = output.split('.')[:3]
        self.value = (int(ver[0]) * 100)
        self.value += (str2int(ver[1]) * 10)
        if len(ver) > 2:
            self.value += str2int(ver[2])
        self.determined = 1

class BuildType(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "buildType",
            desc="the Komodo build type",
            acceptedOptions=("", ["build-type=", "release", "debug"]))

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s. Use the "\
                "--buildtype configure option to specify this.\n" % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        #XXX default should change to a release build I think, or maybe
        #    release for installer builds
        self.value = "release"   # default to debug build
        for opt, optarg in self.chosenOptions:
            if opt == "--build-type":
                self.value = optarg
            elif opt == "--release":
                self.value = "release"
            elif opt == "--debug":
                self.value = "debug"
        self.determined = 1


class BuildFlavour(black.configure.Datum):
    """The "flavour" of Komodo build.

    One of "dev" (the default, for development builds, use the "--dev"
    configure option) or "full" (for full builds, use the "--full"
    configure option). A "full" build implies that everything that the
    build system can build can be built with this configuration. The
    prime example here is the installer package. Most developers don't
    need to build the installer package. A "full" build flavour
    configuration implies more dependencies, e.g.:
        - InstallShield on Windows
        - 'osxpkg' on Mac OS X
        - Python 2.2, Python 2.3 and Python 2.4 installations for the
          PyDBGP extensions;
    and possibly others (see README.txt for full details).
    
    This is (mostly) independent to the "buildType" (values "release" or
    "debug").
    """
    def __init__(self):
        black.configure.Datum.__init__(self, "buildFlavour",
            desc="the Komodo build flavour ('dev' or 'full')",
            acceptedOptions=("", ["dev", "full"]))

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s. Use one "\
                "of the '--dev' or '--full' configure options\n" % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        # default to a dev build (fewer system prereqs, enough for development)
        self.value = "dev"   
        for opt, optarg in self.chosenOptions:
            if opt == "--dev":
                self.value = "dev"
            elif opt == "--full":
                self.value = "full"
        self.determined = 1


class UpdateChannel(black.configure.Datum):
    """The update channel used for auto-updating Komodo.

    Must be one of the following channels:
        - release
        - beta
        - nightly
    """
    def __init__(self):
        black.configure.Datum.__init__(self, "updateChannel",
            desc="the Komodo build flavour ('release', 'beta' or 'nightly')",
            acceptedOptions=("", ["update-channel="]))

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s. Use the --update-channel "\
                "configure option\n" % self.desc)
        elif self.value not in ("release", "beta", "nightly"):
            raise black.configure.ConfigureError(\
                "Invalid %s. Must be one of 'release', 'beta' or 'nightly'\n"\
                % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        for opt, optarg in self.chosenOptions:
            if opt == "--update-channel":
                self.value = optarg
                break
        else:
            # Set the channel from the Komodo version.
            version = black.configure.items["komodoVersion"].Get()
            if "-" in version:
                self.value = "beta"
            else:
                self.value = "release"
        self.determined = 1


class Platform(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "platform",
            desc="the Komodo build platform")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s.\n" % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        if sys.platform.startswith("win"):
            self.value = "win"
        elif sys.platform.startswith("linux"):
            self.value = "linux"
        elif sys.platform.startswith("sunos"):
            self.value = "solaris"
        elif sys.platform == "darwin":
            self.value = "darwin"
        else:
            self.value = None
        self.determined = 1

class Architecture(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "architecture",
            desc="the Komodo build architecture")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s.\n" % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        if sys.platform == "win32":
            self.value = "x86"
        else:
            uname = os.uname()
            if re.match("i\d86", uname[4]):
                #XXX Currently disabling linux-distro differentiation until
                #    we have a concrete reason for it.
                #distro = _getLinuxDistro()
                #validPlats = ["linux-%s-x86" % distro]
                self.value = 'x86'
            else:
                self.value = uname[4]
        self.determined = 1

class BuildNum(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "buildNum",
            desc="the Komodo build number",
            acceptedOptions=("", ["komodo-buildnum="]))

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s. Maybe because "\
                "you do not currently have direct Perforce access. See the "\
                "--komodo-buildnum configure option to override.\n" % self.desc)

    def _get_hg_changeset(self):
        changeset_re = re.compile("changeset:\s+(\d+):")
        cmd = "hg tip"
        o = os.popen(cmd)
        stdout = o.read()
        retval = o.close()
        if retval:
            raise black.configure.ConfigureError(
                "error running '%s'" % cmd)
        rev_str = changeset_re.search(stdout).group(1)
        return int(rev_str)

    def _get_git_build_num(self):
        """Get the build number for current git repo"""
        return gitutils.buildnum_from_revision()

    def _get_simplified_svn_version(self):
        # Note that this can be a fairly complex string (perhaps not
        # suitable for inclusion in a filename if ':' is in it). See
        # "svn info --help" for details.
        cmd = ["svn", "info", "--xml", dirname(__file__)]
        try:
            xml = _capture_stdout(cmd)
        except RuntimeError:
            raise black.configure.ConfigureError(
                "error running '%s'" % (" ".join(cmd),))
        from xml.etree import ElementTree as ET
        root = ET.fromstring(xml)
        changestr = root.find("entry").find("commit").get("revision")
        # Simplify the possibly-complex svn version.
        try:
            changenum = int(changestr)
        except ValueError, ex:
            # pull off front number (good enough for our purposes)
            try:
                changenum = int(re.match("(\d+)", changestr).group(1))
                sys.stderr.write("configure: simplifying complex changenum "
                                 "from 'svn commit revision': %s -> %s\n"
                                 % (changestr, changenum))
            except AttributeError:
                changenum = 0
        return changenum

    def _Determine_Do(self):
        self.applicable = 1
        for opt, optarg in self.chosenOptions:
            if opt == "--komodo-buildnum":
                self.value = int(optarg)
                break
        else:
            scc_type = black.configure.items["sccType"].Get()
            if scc_type == "svn":
                self.value = self._get_simplified_svn_version()
            elif scc_type == "git":
                self.value = self._get_git_build_num()
            elif scc_type == "hg":
                self.value = self._get_hg_changeset()
            else:
                sys.stderr.write("configure: cannot determine build number "
                                 "due to unknown source code control, "
                                 "using 0 as fallback\n")
                self.value = 0
        self.determined = 1


class SourceId(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "sourceId",
            desc="an id string for the source (`svnversion` output)")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(
                "Could not determine %s." % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        cmd = 'svnversion "%s"' % dirname(__file__)
        o = os.popen(cmd)
        stdout = o.read()
        retval = o.close()
        if retval:
            raise black.configure.ConfigureError(
                "error running '%s'" % cmd)
        self.value = stdout.strip()
        self.determined = 1

class SCCType(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "sccType",
            desc="the SCC system the source tree is using")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(
                "Could not determine %s." % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        dir = dirname(__file__)
        for name, path in [
                ("svn", ".svn"),
                ("svn", "_svn"), # "asp.net hack" on windows, r16244 (svn, not komodo)
                ("git", ".git"),
                ("hg", ".hg"), # ???
                ]:
            if exists(join(dir, path)):
                self.value = name
                break
        else:
            self.value = "none" # using a tarball or something
        self.determined = 1

class SCCBranch(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "sccBranch",
            desc="the SCC branch this source tree is on")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(
                "Could not determine %s." % self.desc)

    def _get_scc_branch(self, dir):
        from posixpath import basename as ubasename
        
        scc_type = black.configure.items["sccType"].Get()

        if scc_type == "git":
            stdout = _capture_stdout(['git', 'branch', '-l'])
            for line in stdout.splitlines(0):
                if line.startswith("*"):
                    scc_branch = line[1:].strip()
                    break
        else:
            return ""
        return scc_branch

    def _Determine_Do(self):
        self.applicable = 1
        self.value = self._get_scc_branch(dirname(__file__))
        self.determined = 1

class NormSCCBranch(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "normSCCBranch",
            desc="normalized version of SCC branch for use in upload dirs")

    def _Determine_Do(self):
        self.applicable = 1
        sccBranch = black.configure.items["sccBranch"].Get()
        self.value = re.sub(r'[^\w\.]', '_', sccBranch).lower()
        self.determined = 1

class SCCRepo(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "sccRepo",
            desc="upstream SCC repository")

    def _get_svn_repo(self):
        cmd = ["svn", "info", "--xml"]
        try:
            xml = _capture_stdout(cmd)
        except RuntimeError:
            raise black.configure.ConfigureError(
                "error running '%s'" % (" ".join(cmd),))
        from xml.etree import ElementTree as ET
        root = ET.fromstring(xml)
        return root.find("entry").find("url").text

    def _get_git_repo(self):
        # Find the current branch
        env = os.environ.copy()
        env["LANG"] = "C"
        cmd = ["git", "describe", "--all", "--candidates=0", "HEAD"]
        branch = _capture_stdout(cmd).strip()
        if branch.startswith("heads/"):
            branch = branch.split("/", 1)[-1] # strip leading "heads/"
        cmd = ["git", "config", "--get", "branch.%s.remote" % (branch,)]
        try:
            remote = _capture_stdout(cmd).strip()
        except RuntimeError:
            # No remotes configured - that's okay, we tried.
            return ""
        cmd = ["git", "remote", "show", "-n", remote]
        for line in _capture_stdout(cmd, env=env).splitlines(False):
            if line.strip().startswith("Push  URL:"):
                return line.split(":", 1)[-1].strip()
        return ""

    def _Determine_Do(self):
        scc_type = black.configure.items["sccType"].Get()
        self.applicable = True
        if scc_type == "svn":
            self.value = self._get_svn_repo()
        elif scc_type == "git":
            self.value = self._get_git_repo()
        else:
            self.value = ""
            self.applicable = False
        self.determined = True


class VersionInfoFile(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "versionInfoFile",
            desc="the Komodo version info filename")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s." % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        # first look for a target dependent one ("version.<target>.txt"),
        # if not default to the common one ("version.txt").
        komodoDevDir = black.configure.items["komodoDevDir"].Get()
        productType = black.configure.items["productType"].Get()
        candidates = [
            "version.%s.%s.txt" % (productType, platinfo.platname("os", "arch")),
            "version.%s.txt" % productType,
            "version.%s.txt" % platinfo.platname("os", "arch"),
            "version.txt",
        ]
        for candidate in candidates:
            version_txt_path = os.path.join(komodoDevDir, "src", candidate)
            if os.path.exists(version_txt_path):
                self.value = version_txt_path
                break
        else:
            self.value = None
        self.determined = 1


class KomodoVersion(black.configure.Datum):
    # see KOMODO_VERSION for the a Komodo version description.
    def __init__(self):
        black.configure.Datum.__init__(self, "komodoVersion",
            desc="the Komodo version",
            acceptedOptions=("V:", ["komodo-version="]))
    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s. Maybe because "\
                "you do not currently have direct access to the Komodo "\
                "source code. See the --komodo-version "\
                "configure option to override.\n" % self.desc)
        # Ensure correct version string form.
        ver_pat = re.compile(r"^\d+\.\d+\.\d+(-(alpha\d+|beta\d+|rc\d+|devel))?$")
        if not ver_pat.search(self.value):
            raise black.configure.ConfigureError(
                "invalid komodo version string: %r  (must match '%s')"
                % (self.value, ver_pat.pattern))
        
    def _Determine_Do(self):
        self.applicable = 1
        for opt, optarg in self.chosenOptions:
            if opt in ("-V", "--komodo-version"):
                self.value = optarg
                break
        else:
            versionInfoFile = black.configure.items["versionInfoFile"].Get()
            if versionInfoFile:
                self.value = open(versionInfoFile).readline().strip()
            else:
                self.value = None
        self.determined = 1

class Version(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "version",
            desc="the Komodo version (alias for 'komodoVersion' for compat)")

    def _Determine_Do(self):
        self.applicable = 1
        self.value = black.configure.items["komodoVersion"].Get()
        self.determined = 1

class KomodoShortVersion(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "komodoShortVersion",
            desc="Komodo's short <major>.<minor> version string")
    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(
                "Could not determine %s\n." % self.desc)
    def _Determine_Do(self):
        self.applicable = 1
        komodoVersion = black.configure.items["komodoVersion"].Get()
        parts = re.split(r"-|\.", komodoVersion)
        self.value = '.'.join(parts[:2])
        self.determined = 1

class KomodoMarketingVersion(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "komodoMarketingVersion",
            desc="Komodo's full *marketing* version string")
    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(
                "Could not determine %s\n." % self.desc)
    def _Determine_Do(self):
        self.applicable = 1
        self.value = black.configure.items["komodoVersion"].Get()
        self.determined = 1

class KomodoMarketingShortVersion(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "komodoMarketingShortVersion",
            desc="Komodo's short <major>.<minor> *marketing* version string")
    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(
                "Could not determine %s\n." % self.desc)
    def _Determine_Do(self):
        self.applicable = 1
        komodoMarketingVersion = black.configure.items["komodoMarketingVersion"].Get()
        parts = re.split(r"-|\.", komodoMarketingVersion)
        self.value = '.'.join(parts[:2])
        self.determined = 1

class KomodoPrettyVersion(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "komodoPrettyVersion",
            desc="Komodo's *pretty* version string")
    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(
                "Could not determine %s\n." % self.desc)
    def _Determine_Do(self):
        self.applicable = 1
        komodoMarketingVersion = black.configure.items["komodoMarketingVersion"].Get()
        self.value = _getPrettyVersion(komodoMarketingVersion)
        self.determined = 1

class KomodoFullPrettyVersion(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "komodoFullPrettyVersion",
            desc="Komodo's long-form pretty version string")
    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(
                "Could not determine %s\n." % self.desc)
    def _Determine_Do(self):
        self.applicable = 1
        productType = black.configure.items["productType"].Get()
        prettyProductType = black.configure.items["prettyProductType"].Get()
        komodoMarketingVersion = black.configure.items["komodoMarketingVersion"].Get()
        buildNum = black.configure.items["buildNum"].Get()
        productName = (productType == "openkomodo" and prettyProductType
                       or "Komodo %s" % prettyProductType)
        updateChannel = black.configure.items["updateChannel"].Get()
        self.value = "%s %s%s (Build %s)"\
                     % (productName,
                        _getPrettyVersion(komodoMarketingVersion),
                        updateChannel == "nightly" and " nightly" or "",
                        buildNum)
        self.determined = 1

class KomodoTitleBarName(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "komodoTitleBarName",
            desc="Komodo's ID in the main title bar")
    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(
                "Could not determine %s\n." % self.desc)
    def _Determine_Do(self):
        self.applicable = 1
        productType = black.configure.items["productType"].Get()
        prettyProductType = black.configure.items["prettyProductType"].Get()
        productName = (productType == "openkomodo" and prettyProductType
                       or "Komodo %s" % prettyProductType)
        komodoMarketingShortVersion = black.configure.items["komodoMarketingShortVersion"].Get()
        updateChannel = black.configure.items["updateChannel"].Get()
        self.value = "%s %s%s"\
                     % (productName, komodoMarketingShortVersion,
                        updateChannel == "nightly" and " nightly" or "")
        self.determined = 1

class KomodoAppDataDirName(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "komodoAppDataDirName",
            desc="dirname used for app in appdata dir path")
    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(
                "Could not determine %s\n." % self.desc)
    def _Determine_Do(self):
        self.applicable = 1
        productType = black.configure.items["productType"].Get()
        prettyProductType = black.configure.items["prettyProductType"].Get()
        name = (productType == "openkomodo" and prettyProductType
                or "Komodo"+prettyProductType)
        if sys.platform in ("win32", "darwin"):
            self.value = name
        else:
            self.value = name.lower()
        self.determined = 1

class MSIVccrtMsmPath(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "msiVccrtMsmPath",
            desc="Full path to Visual C++ CRT merge module.")

    def _Determine_Do(self):
        self.applicable = 1
        if sys.platform == "win32":
            architecture = black.configure.items["architecture"].Get()
            assert architecture == "x86", \
                "get the right merge module path for arch=%r" % architecture
            compiler = black.configure.items["compiler"].Get()
            base = "Microsoft_%s0_CRT_x86.msm" % compiler.upper()
            mergeModulesDir = join(os.environ["CommonProgramFiles"],
                                   "Merge Modules")
            self.value = join(mergeModulesDir, base)
        else:
            # Helps with Cons to have *some* value defined.
            self.value = ""
        self.determined = 1

class MSIVccrtRedistPath(black.configure.Datum):
    """Path to MSVC redistributables, needed for upgrades across CRT versions
    (Komodo 8.0 shipped with MSVC9, 8.5 shipped with MSVC11, and app update
    can't update the MSM installer)"""
    def __init__(self):
        black.configure.Datum.__init__(self, "msiVccrtRedistPath",
            desc="full path to Visual C++ CRT redistributables")

    def _Determine_Do(self):
        if sys.platform != "win32":
            self.applicable = False
            return
        compiler = black.configure.items["compiler"].Get()
        assert compiler.startswith("vc"), "Invalid compiler version"
        compiler_ver = compiler[2:]
        self.applicable = True
        if int(compiler_ver) < 11:
            # We don't need this
            self.value = ""
            self.determined = True
            return
        import _winreg
        with _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE,
                             r"SOFTWARE\Wow6432Node\Microsoft\VisualStudio\SxS\VC7"
                             ) as regkey:
            vc_path, value_type = _winreg.QueryValueEx(regkey, "%s.0" % (compiler_ver,))
            redist_dir = join(vc_path, "redist", "x86",
                              "Microsoft.VC%s0.CRT" % (compiler_ver,))
            if not exists(redist_dir):
                raise ConfigureError("Failed to find CRT redist")
            self.value = redist_dir
            self.determined = True

class MSIVccrtPolicyMsmPath(black.configure.Datum):
    # Note: I don't know *what* the "policy" MSM is for.
    def __init__(self):
        black.configure.Datum.__init__(self, "msiVccrtPolicyMsmPath",
            desc="Full path to Visual C++ CRT Policy merge module.")

    def _Determine_Do(self):
        self.applicable = 1
        if sys.platform == "win32":
            architecture = black.configure.items["architecture"].Get()
            assert architecture == "x86", \
                "get the right merge module path for arch=%r" % architecture
            compiler = black.configure.items["compiler"].Get()
            assert compiler.startswith("vc"), "Invalid compiler version"
            compiler_ver = compiler[2:]
            if 7 <= float(compiler_ver) <= 10:
                base = "policy_%s_0_Microsoft_%s_CRT_x86.msm" % \
                    (compiler_ver, compiler.upper())
                mergeModulesDir = join(os.environ["CommonProgramFiles"],
                                       "Merge Modules")
                self.value = join(mergeModulesDir, base)
            else:
                # MSVC, as of 2012 / VC11, no longer has policy msms
                self.value = ""
        else:
            # Helps with Cons to have *some* value defined.
            self.value = ""
        self.determined = 1

class MSIKomodoPrettyId(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "msiKomodoPrettyId",
            desc="Pretty name for Komodo exe shortcuts in MSI")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(
                "Could not determine %s." % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        productType = black.configure.items["productType"].Get()
        prettyProductType = black.configure.items["prettyProductType"].Get()
        productName = (productType == "openkomodo" and prettyProductType
                       or "Komodo %s" % prettyProductType)
        updateChannel = black.configure.items["updateChannel"].Get()
        komodoVersion = black.configure.items["komodoVersion"].Get()
        majorVer = komodoVersion.split('.', 1)[0]
        self.value = "%s %s" % (productName, majorVer)
        if updateChannel == "nightly":
            self.value += " nightly"
        self.determined = 1

class MSIProductName(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "msiProductName",
            desc="The 'ProductName' for Komodo's MSI")
    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(
                "Could not determine %s\n." % self.desc)
    def _Determine_Do(self):
        self.applicable = 1
        productType = black.configure.items["productType"].Get()
        prettyProductType = black.configure.items["prettyProductType"].Get()
        productName = (productType == "openkomodo" and prettyProductType
                       or "Komodo %s" % prettyProductType)
        komodoPrettyVersion = black.configure.items["komodoPrettyVersion"].Get()
        updateChannel = black.configure.items["updateChannel"].Get()
        self.value = "ActiveState %s %s" % (productName, komodoPrettyVersion)
        if updateChannel == "nightly":
            self.value += " nightly"
        self.determined = 1

class MSIInstallName(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "msiInstallName",
            desc="The install (and Start Menu) name for Komodo's MSI")
    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(
                "Could not determine %s\n." % self.desc)
    def _Determine_Do(self):
        self.applicable = 1
        productType = black.configure.items["productType"].Get()
        prettyProductType = black.configure.items["prettyProductType"].Get()
        productName = (productType == "openkomodo" and prettyProductType
                       or "Komodo %s" % prettyProductType)
        updateChannel = black.configure.items["updateChannel"].Get()
        komodoVersion = black.configure.items["komodoVersion"].Get()
        majorVer = komodoVersion.split('.', 1)[0]
        self.value = "ActiveState %s %s" % (productName, majorVer)
        if updateChannel == "nightly":
            self.value += " nightly"
        elif updateChannel == "beta":
            self.value += " Beta"
        self.determined = 1


class MSIKomodoVersion(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "msiKomodoVersion",
            desc="Komodo *MSI* version number")
    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(
                "Could not determine %s\n." % self.desc)
    def _Determine_Do(self):
        self.applicable = 1
        #XXX Currently we just use the first part of the version number,
        #    e.g. "3.5.0" from "3.5.0-alpha1". However, there are some
        #    MSI versioning issues that we may run into with this. Need
        #    to look into this and use a better scheme to differentiate
        #    all packages that get into the wild. Using our "buildNum"
        #    *would* have been great except MSI stupidly limits a single
        #    version component to 2**15==32768.
        komodoVersion = black.configure.items["komodoVersion"].Get()
        if '-' in komodoVersion:
            self.value = komodoVersion.split('-')[0]
        else:
            self.value = komodoVersion
        self.determined = 1

class MSIKomodoId(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "msiKomodoId",
            desc="short 8-char KomodoXY string for MSI id's")
    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(
                "Could not determine %s\n." % self.desc)
        elif len(self.value) > 8:
            raise black.configure.ConfigureError(
                "Invalide value for 'msiKomodoId' config var (%s): "
                "the MSI fields in which this is used require that "
                "it be a maximum of 8-chars: %r"
                % (self.desc, self.value))

    def _Determine_Do(self):
        self.applicable = 1
        komodoShortVersion = black.configure.items["komodoShortVersion"].Get()
        XY = re.sub(r"\.", "", komodoShortVersion)
        productType = black.configure.items["productType"].Get()
        if 2 <= len(XY) <= 3:
            self.value = {
                # Notes:
                # - The prefix here is intentionally different for
                #   "Edit" vs. "IDE" to ensure that MSI thinks they are
                #   different where necessary.
                # - Intentionally NOT using "KoEdit" because we changed the
                #   edit icon post-public release. The ID change is necessary
                #   to not get the old icon (from Windows' icon cache) on
                #   user's machines. An alternative would be a custom action
                #   to delete "C:\Documents and Settings\Username\Local
                #   Settings\Application Data\IconCache.db".
                "edit": "KoEd"+XY,
                "ide": "KoIDE"+XY,
                "openkomodo": "OKo"+XY,
            }[productType]
        else:
            raise black.configure.ConfigureError(
                "Why is your Komodo XY, %r, version number so long?"
                "With it this long it is hard to make a sufficiently "
                "unique 8-char id for it (required for MSI builds)."
                % XY)
        self.determined = 1


class MSIRegistryId(black.configure.Datum):
    """The key name used under HKLM/Software/ActiveState/Komodo to
    identify this Komodo install in the Windows registry. We are
    allowing side-by-side install of Komodo Edit and IDE of the same
    <major>.<minor> version, so it is has to distinguish these:

        <major>.<minor>-<productType>
    """
    def __init__(self):
        black.configure.Datum.__init__(self, "msiRegistryId",
            desc="a (relatively short) string to ID this Komodo ver in the registry")
    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(
                "Could not determine %s\n." % self.desc)
    def _Determine_Do(self):
        self.applicable = 1
        komodoShortVersion = black.configure.items["komodoShortVersion"].Get()
        productType = black.configure.items["productType"].Get()
        self.value = "%s-%s" % (komodoShortVersion, productType)
        self.determined = 1


class OSXCodeSignExecutable(black.configure.Datum):
    """Optional codesign executable to sign the Mac application bundle with."""
    def __init__(self):
        self.longopt = "with-osx-codesign-executable"
        black.configure.Datum.__init__(self, "osxCodeSignExecutable",
            desc="Path to codesign executable for Mac OSX code signing",
            acceptedOptions=("", [self.longopt + "="]))

    def _Determine_Sufficient(self):
        if not self.applicable:
            return
        if self.value is not None:
            if not os.path.exists(self.value):
                raise black.configure.ConfigureError(
                    "OSX codesign executable does not exist %r" % (self.value,))

    def _Determine_Do(self):
        if sys.platform == "darwin":
            self.applicable = True
            for opt, optarg in self.chosenOptions:
                if opt == "--"+self.longopt:
                    self.value = os.path.abspath(optarg)
                    break
        else:
            self.applicable = False
        self.determined = True


class OSXCodeSigningCert(black.configure.Datum):
    """The code signing certificate to use to sign the Mac OSX application
    bundle. It should be a PKCS12 or x509/PEM file with no password."""
    def __init__(self):
        self.longopt = "with-osx-codesign-certificate"
        black.configure.Datum.__init__(self, "osxCodeSigningCert",
            desc="Path to code certificate for Mac OSX code signing",
            acceptedOptions=("", [self.longopt + "="]))

    def _Determine_Sufficient(self):
        if not self.applicable:
            return
        if self.value is not None:
            if not os.path.exists(self.value):
                raise black.configure.ConfigureError(
                    "OSX code-signing certificate %s does not exist" % (self.value,))

    def _Determine_Do(self):
        if sys.platform == "darwin":
            self.applicable = True
            for opt, optarg in self.chosenOptions:
                if opt == "--"+self.longopt:
                    self.value = os.path.abspath(optarg)
                    break
        else:
            self.applicable = False
        self.determined = True


class InstallRelDir(black.configure.Datum):
    """The root of the Komodo installation image dir relative to the root of
    Komodo project."""
    def __init__(self):
        black.configure.Datum.__init__(self, "installRelDir",
            desc="the root of the Komodo install image")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s\n." % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        buildType = black.configure.items["buildType"].Get()
        if sys.platform == "win32":
            self.value = os.path.join("install", buildType)
        else:
            productType = black.configure.items["productType"].Get()
            prettyProductType = black.configure.items["prettyProductType"].Get()
            productName = (productType == "openkomodo" and prettyProductType
                           or "Komodo-%s" % prettyProductType)
            assert ' ' not in productName
            komodoMarketingVersion = black.configure.items["komodoMarketingVersion"].Get()
            buildNum = black.configure.items["buildNum"].Get()
            platName = _getDefaultPlatform(macUniversal=False)
            base = "%s-%s-%s-%s" % (productName, komodoMarketingVersion,
                                      buildNum, platName)
            self.value = os.path.join("install", buildType, base)
        self.determined = 1


class UserDataDir(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "userDataDir",
            desc="Komodo app data dir for the current user")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s\n." % self.desc)

    def _Determine_Do(self):
        # Dev Note: This logic must match that in:
        #   src/components/koDirs.py::KoDirs.get_userDataDir()
        # This should really be shared code somewhere.
        from os.path import join
        self.applicable = 1
        komodoShortVersion = black.configure.items["komodoShortVersion"].Get()
        komodoAppDataDirName = black.configure.items["komodoAppDataDirName"].Get()
        if "KOMODO_USERDATADIR" in os.environ:
            userAppDataPath = os.environ["KOMODO_USERDATADIR"]
        else:
            import applib
            userAppDataPath = applib.user_data_dir(komodoAppDataDirName,
                                                   "ActiveState")
        self.value = join(userAppDataPath, komodoShortVersion)
        self.determined = 1


class SupportDir(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "supportDir",
            desc="Komodo's 'support' dir (in a dev tree)")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s\n." % self.desc)

    def _Determine_Do(self):
        from os.path import dirname, join
        self.applicable = 1
        mozDist = black.configure.items["mozDist"].Get()
        self.value = join(mozDist, "komodo-bits", "support")
        self.determined = 1


class SDKDir(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "sdkDir",
            desc="Komodo SDK dir (in a dev tree)")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s\n." % self.desc)

    def _Determine_Do(self):
        from os.path import dirname, join
        self.applicable = 1
        mozDist = black.configure.items["mozDist"].Get()
        self.value = join(mozDist, "komodo-bits", "sdk")
        self.determined = 1


class StubDir(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "stubDir",
            desc="Komodo's starter 'stub' dir (in a dev tree)")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s\n." % self.desc)

    def _Determine_Do(self):
        from os.path import dirname, join
        self.applicable = 1
        mozDist = black.configure.items["mozDist"].Get()
        self.value = join(mozDist, "komodo-bits", "stub")
        self.determined = 1

class DocChromeDir(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "docChromeDir",
            desc="Komodo's doc chrome (in a dev tree)")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s\n." % self.desc)

    def _Determine_Do(self):
        from os.path import dirname, join
        self.applicable = 1
        mozChrome = black.configure.items["mozChromeDir"].Get()
        self.value = join(mozChrome, "komododoc")
        self.determined = 1


class DocDir(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "docDir",
            desc="Komodo's doc dir (in a dev tree)")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s\n." % self.desc)

    def _Determine_Do(self):
        from os.path import dirname, join
        self.applicable = 1
        chrome = black.configure.items["docChromeDir"].Get()
        self.value = join(chrome, "locale", "en-US")
        self.determined = 1


class ReadmeDir(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "readmeDir",
            desc="a prominent dir for a few standalone doc bits (in the dev tree)")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s\n." % self.desc)

    def _Determine_Do(self):
        from os.path import dirname, join
        self.applicable = 1
        mozDist = black.configure.items["mozDist"].Get()
        self.value = join(mozDist, "komodo-bits", "readme")
        self.determined = 1

class SysdllsDir(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "sysdllsDir",
            desc="dir for system DLLs to install if necessary (in the dev tree)")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s\n." % self.desc)

    def _Determine_Do(self):
        from os.path import dirname, join
        self.applicable = 1
        mozDist = black.configure.items["mozDist"].Get()
        self.value = join(mozDist, "komodo-bits", "sysdlls")
        self.determined = 1

class InstallSupportDir(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "installSupportDir",
            desc="dir (in the dev tree) for installer support files")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s\n." % self.desc)

    def _Determine_Do(self):
        from os.path import dirname, join
        self.applicable = 1
        mozDist = black.configure.items["mozDist"].Get()
        self.value = join(mozDist, "komodo-bits", "installsupport")
        self.determined = 1


class BuildRelDir(black.configure.Datum):
    """The root of the Komodo build tree relative to the root of 
    Komodo project."""
    def __init__(self):
        black.configure.Datum.__init__(self, "buildRelDir",
            desc="the root of the Komodo build tree relative to "\
                 "the Komodo root dir")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s\n." % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        buildType = black.configure.items["buildType"].Get()
        if not buildType:
            self.value = None
        else:
            self.value = os.path.join("build", buildType)
        self.determined = 1


class BuildAbsDir(black.configure.Datum):
    """The root of the Komodo build tree."""
    def __init__(self):
        black.configure.Datum.__init__(self, "buildAbsDir",
            desc="the root of the Komodo build tree")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s\n." % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        buildRelDir = black.configure.items["buildRelDir"].Get()
        self.value = os.path.abspath(buildRelDir)
        self.determined = 1


class PackagesRelDir(black.configure.Datum):
    """The root of the Komodo build tree relative to the root of 
    Komodo project."""
    def __init__(self):
        black.configure.Datum.__init__(self, "packagesRelDir",
            desc="the directory in which built packages are placed")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s\n." % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        self.value = "packages"
        self.determined = 1


class PackagesAbsDir(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "packagesAbsDir",
            desc="the directory in which built packages are placed")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s\n." % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        packagesRelDir = black.configure.items["packagesRelDir"].Get()
        self.value = os.path.abspath(packagesRelDir)
        self.determined = 1


class ExportRelDir(black.configure.Datum):
    """The root of the Komodo export tree relative to the root of
    Komodo project."""
    def __init__(self):
        black.configure.Datum.__init__(self, "exportRelDir",
            desc="the root of the Komodo export tree")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s\n." % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        buildType = black.configure.items["buildType"].Get()
        if not buildType:
            self.value = None
        else:
            self.value = os.path.join("export", buildType)
        self.determined = 1


class IdlExportRelDir(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "idlExportRelDir",
            desc="the .idl export directory")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s\n." % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        exportRelDir = black.configure.items["exportRelDir"].Get()
        if exportRelDir:
            self.value = os.path.join(exportRelDir, "idl")
        else:
            self.value = None
        self.determined = 1


class InstallRelDir_ForCons(black.configure.Datum):
    """The project-root relative install dir with the Cons "relative to
    project to root" marker."""
    def __init__(self):
        black.configure.Datum.__init__(self, "installRelDir_ForCons",
            desc="the Cons marked project relative install dir")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s\n." % self.desc)

    def _Determine_Do(self):
        self.applicable = black.configure.items["installRelDir"].Determine()
        if self.applicable:
            self.value = "#" + black.configure.items["installRelDir"].Get()
        self.determined = 1


class BuildRelDir_ForCons(black.configure.Datum):
    """The project-root relative build dir with the Cons "relative to
    project to root" marker."""
    def __init__(self):
        black.configure.Datum.__init__(self, "buildRelDir_ForCons",
            desc="the Cons marked project relative build dir")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s\n." % self.desc)

    def _Determine_Do(self):
        self.applicable = black.configure.items["buildRelDir"].Determine()
        if self.applicable:
            self.value = "#" + black.configure.items["buildRelDir"].Get()
        self.determined = 1


class ContribBuildRelDir_ForCons(black.configure.Datum):
    """The project-root relative build dir *for contributed 3rd-party code* with
    the Cons "relative to project to root" marker.
    """
    def __init__(self):
        black.configure.Datum.__init__(self, "contribBuildRelDir_ForCons",
            desc="the Cons marked project relative contrib build dir")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s\n." % self.desc)

    def _Determine_Do(self):
        self.applicable = black.configure.items["buildRelDir_ForCons"].Determine()
        if self.applicable:
            self.value = os.path.join(
                black.configure.items["buildRelDir_ForCons"].Get(),
                "contrib")
        self.determined = 1


class TestBuildRelDir_ForCons(black.configure.Datum):
    """The project-root relative build dir *for test code* with
    the Cons "relative to project to root" marker.
    """
    def __init__(self):
        black.configure.Datum.__init__(self, "testBuildRelDir_ForCons",
            desc="the Cons marked project relative test build dir")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s\n." % self.desc)

    def _Determine_Do(self):
        self.applicable = black.configure.items["buildRelDir_ForCons"].Determine()
        if self.applicable:
            self.value = os.path.join(
                black.configure.items["buildRelDir_ForCons"].Get(),
                "test")
        self.determined = 1


class ExportRelDir_ForCons(black.configure.Datum):
    """The project-root relative export dir with the Cons "relative to
    project to root" marker."""
    def __init__(self):
        black.configure.Datum.__init__(self, "exportRelDir_ForCons",
            desc="the Cons marked project relative export dir")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s\n." % self.desc)

    def _Determine_Do(self):
        self.applicable = black.configure.items["exportRelDir"].Determine()
        if self.applicable:
            self.value = "#" + black.configure.items["exportRelDir"].Get()
        self.determined = 1


class IdlExportRelDir_ForCons(black.configure.Datum):
    """The project-root relative idl export dir with the Cons "relative to
    project to root" marker."""
    def __init__(self):
        black.configure.Datum.__init__(self, "idlExportRelDir_ForCons",
            desc="the Cons marked project relative .idl export dir")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s\n." % self.desc)

    def _Determine_Do(self):
        self.applicable = black.configure.items["idlExportRelDir"].Determine()
        if self.applicable:
            self.value = "#" + black.configure.items["idlExportRelDir"].Get()
        self.determined = 1


class InstallAbsDir(black.configure.Datum):
    """The root of the Komodo install image."""
    def __init__(self):
        black.configure.Datum.__init__(self, "installAbsDir",
            desc="the root of the Komodo install image tree")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s\n." % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        baseDir = black.configure.items["komodoDevDir"].Get()
        relativeDir = black.configure.items["installRelDir"].Get()
        if not baseDir or not relativeDir:
            self.value = None
        else:
            self.value = os.path.join(baseDir, relativeDir)
        self.determined = 1


class ScintillaBuildDir(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "scintillaBuildDir",
            desc="the Scintilla build root directory")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s.\n" % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        buildRelDir_ForCons = black.configure.items["buildRelDir_ForCons"].Get()
        if buildRelDir_ForCons:
            self.value = os.path.join(buildRelDir_ForCons, "scintilla")
        else:
            self.value = None
        self.determined = 1


class DocsPackageName(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "docsPackageName",
            desc="the base name of the Komodo 'docs' package")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s\n." % self.desc)

    def _Determine_Do(self):
        # e.g.: Komodo-3.0.0-12345-doc
        self.applicable = 1
        komodoMarketingVersion = black.configure.items["komodoMarketingVersion"].Get()
        buildNum = black.configure.items["buildNum"].Get()
        productType = black.configure.items["productType"].Get()
        name = (productType == "openkomodo" and "OpenKomodo" or "Komodo")
        self.value = "%s-%s-%s-docs" % (name, komodoMarketingVersion, buildNum)
        self.determined = 1

class MozPatchesPackageName(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "mozPatchesPackageName",
            desc="the base name of the Komodo 'mozpatches' package")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s\n." % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        ver = black.configure.items["komodoMarketingShortVersion"].Get()
        productType = black.configure.items["productType"].Get()
        name = (productType == "openkomodo" and "OpenKomodo" or "Komodo")
        self.value = "%s-%s-mozilla-patches" % (name, ver)
        self.determined = 1

class LinuxDistro(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "linuxDistro",
            desc="the linux distribution name and version")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise black.configure.ConfigureError(\
                "Could not determine %s." % self.desc)

    def _Determine_Do(self):
        if sys.platform.startswith("linux"):
            self.applicable = 1
            self.value = _getLinuxDistro()
        else:
            self.applicable = 0
        self.determined = 1


class Jarring(black.configure.BooleanDatum):
    def __init__(self):
        black.configure.Datum.__init__(self, "jarring",
            desc="whether to JAR Komodo's chrome or not",
            acceptedOptions=("", ["with-jarring", "without-jarring"]))

    def _Determine_Do(self):
        self.applicable = 1
        buildFlavour = black.configure.items["buildFlavour"].Get()
        if buildFlavour == "full":
            self.value = 1
        else:
            self.value = 0

        for opt, optarg in self.chosenOptions:
            if opt == "--with-jarring":
                self.value = 1
            elif opt == "--without-jarring":
                self.value = 0

        self.determined = 1

class BuildPlatform(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "buildPlatform",
            desc="a platform and arch description of the build machine")

    def _Determine_Do(self):
        self.applicable = 1
        self.value = platinfo.platname("os", "arch")
        if sys.platform == "darwin":
            # Use universal naming on the Mac.
            self.value = platinfo.platname("os")
        self.determined = 1

class BuildTime(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "buildTime",
            desc="the number of seconds from the epoch at which Komodo was built")

    def _Determine_Do(self):
        self.applicable = 1
        self.value = int(time.time())
        self.determined = 1

class BuildASCTime(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "buildASCTime",
            desc="a human readable form of the Komodo build time")

    def _Determine_Do(self):
        self.applicable = 1
        buildTime = black.configure.items["buildTime"].Get()
        # Use localtime, as it's more useful for us humans :)
        self.value = time.asctime(time.gmtime(buildTime))
        self.determined = 1

class ConfigTokens(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "configTokens",
            desc="a list of short strings representing the non-std "
                 "config for this build")

    def _Determine_Do(self):
        self.applicable = 1
        self.value = []
        # Other config vars append to this if they are set to a
        # non-default value.
        self.value.sort()
        self.determined = 1


class KomodoInstallerPackage(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "komodoInstallerPackage",
            desc="the relative path to the Komodo installer file to be built")

    def _Determine_Do(self):
        self.applicable = 1
        platform = black.configure.items["platform"].Get()
        productType = black.configure.items["productType"].Get()
        prettyProductType = black.configure.items["prettyProductType"].Get()
        productName = (productType == "openkomodo" and prettyProductType
                       or "Komodo-"+prettyProductType)
        assert ' ' not in productName
        version = black.configure.items["komodoMarketingVersion"].Get()
        buildNum = black.configure.items["buildNum"].Get()
        packagesRelDir = black.configure.items["packagesRelDir"].Get()
        if platform == "win":
            self.value = os.path.join(packagesRelDir,
                "%s-%s-%s.msi"\
                % (productName, version, buildNum))
        elif sys.platform == 'darwin':
            installRelDir = black.configure.items["installRelDir"].Get()
            base = os.path.basename(installRelDir)
            self.value = os.path.join(packagesRelDir, "%s.dmg" % base)
        else:
            installRelDir = black.configure.items["installRelDir"].Get()
            base = os.path.basename(installRelDir)
            self.value = os.path.join(packagesRelDir, "%s.tar.gz" % base)
        self.determined = 1

class KomodoPackageBase(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "komodoPackageBase",
            desc="the base name for binary Komodo packages")

    def _Determine_Do(self):
        # E.g. Komodo-IDE-4.2.0-beta2-123456-win32-x86
        self.applicable = 1
        buildPlatform = black.configure.items["buildPlatform"].Get()
        prettyProductType = black.configure.items["prettyProductType"].Get()
        productType = black.configure.items["productType"].Get()
        productName = (productType == "openkomodo" and prettyProductType
                       or "Komodo-"+prettyProductType)
        assert ' ' not in prettyProductType
        komodoMarketingVersion = black.configure.items["komodoMarketingVersion"].Get()
        buildNum = black.configure.items["buildNum"].Get()
        self.value = "%s-%s-%s-%s" % (
            productName,
            komodoMarketingVersion,
            buildNum,
            buildPlatform
        )
        self.determined = 1


class KomodoUpdateManualURL(black.configure.Datum):
    """This is the URL presented in the update wizard if the auto-update
    fails. I.e., the user should get here if auto-update is failing to
    do a manual update.
    
    This becomes the "app.update.url.manual" JS pref.
    """
    def __init__(self):
        black.configure.Datum.__init__(self, "komodoUpdateManualURL",
            desc="URL to go to when auto-updating fails")

    def _Determine_Do(self):
        self.applicable = 1
        self.value = "http://www.komodoide.com/download/#edit"
        self.determined = 1


class SetupCompiler(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "compiler",
            desc="compiler used for Mozilla build")

    def _Determine_Sufficient(self):
        if sys.platform == "win32" and re.match(r"vc\d+$", self.value) is None:
            raise black.configure.ConfigureError(\
                "unexpected compiler value for win32: %r" % self.value)

    def _Determine_Do(self):
        self.applicable = 1
        mozConfig = MozConfig().Get()
        self.value = mozConfig.compiler
        if self.value is None: # ...as is currently is on non-Windows
            # Don't use None, because Black will then not serialize the
            # var to the config file, and then Cons starts barfing.
            self.value = ''
        self.determined = 1



class MozMake(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "mozMake",
            desc="make to use for Mozilla build")

    def _Determine_Do(self):
        self.applicable = 1
        if sys.platform.startswith("win"):
            self.value = [which.which("mozmake")]
        else:
            self.value = [which.which("make")]
        assert self.value is not None
        self.determined = 1


class MozGcc(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "mozGcc",
            desc="gcc compiler used for Mozilla build")

    def _Determine_Do(self):
        if sys.platform.startswith("win"):
            self.applicable = 0
        else:
            self.applicable = 1
            mozConfig = MozConfig().Get()
            self.value = mozConfig.gcc
        self.determined = 1


class MozGxx(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "mozGxx",
            desc="g++ compiler used for Mozilla build")

    def _Determine_Do(self):
        if sys.platform.startswith("win"):
            self.applicable = 0
        else:
            self.applicable = 1
            mozConfig = MozConfig().Get()
            self.value = mozConfig.gxx
        self.determined = 1


def stripConflictingCFlags(flags):
    """Remove compile flags that are known to break other Komodo components."""
    flags_split = flags.split(" ")
    # Python uses this in PyString_FromStringAndSize:
    while "-Werror=pointer-sign" in flags_split:
        flags_split.remove("-Werror=pointer-sign")
    return " ".join(flags_split)

class MozCFlags(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "mozCFlags",
            desc="CFLAGS used for Mozilla build")

    def _Determine_Do(self):
        self.applicable = 1
        mozObjDir = black.configure.items['mozObjDir'].Get()
        cmd = black.configure.items['mozMake'].Get() + ["echo-variable-CFLAGS"]
        self.value = _capture_stdout(cmd, cwd=mozObjDir).strip()
        self.value = stripConflictingCFlags(self.value)
        self.determined = 1


def stripConflictingCxxFlags(flags):
    """Remove compile flags that are known to break other Komodo components."""
    flags_split = flags.split(" ")
    # Scintilla uses these for struct initialization:
    while "-Werror=missing-braces" in flags_split:
        flags_split.remove("-Werror=missing-braces")
    # Scintilla uses these for UTF comparison:
    while "-Werror=type-limits" in flags_split:
        flags_split.remove("-Werror=type-limits")
    return " ".join(flags_split)

class MozCxxFlags(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "mozCxxFlags",
            desc="CXXFLAGS used for Mozilla build")

    def _Determine_Do(self):
        self.applicable = 1
        mozObjDir = black.configure.items['mozObjDir'].Get()
        cmd = black.configure.items['mozMake'].Get() + ["echo-variable-CXXFLAGS"]
        self.value = _capture_stdout(cmd, cwd=mozObjDir).strip()
        self.value = stripConflictingCxxFlags(self.value)
        self.determined = 1


class MozLdFlags(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "mozLdFlags",
            desc="LDFLAGS used for Mozilla build")

    def _Determine_Do(self):
        self.applicable = 1
        mozObjDir = black.configure.items['mozObjDir'].Get()
        cmd = black.configure.items['mozMake'].Get() + ["echo-variable-LDFLAGS"]
        self.value = _capture_stdout(cmd, cwd=mozObjDir).strip()
        self.determined = 1


class MozGreMilestone(black.configure.Datum):
    def __init__(self):
        black.configure.Datum.__init__(self, "mozGreMilestone",
            desc="GRE_MILESTONE set for Mozilla build")

    def _Determine_Do(self):
        self.applicable = 1
        mozObjDir = black.configure.items['mozObjDir'].Get()
        mozDefines, mozSubsts = _getMozDefinesAndSubsts(mozObjDir)
        # GRE_MILESTONE is not defined on older Mozilla builds (e.g. moz 18).
        self.value = mozSubsts.get("GRE_MILESTONE") or mozSubsts.get("MOZILLA_VERSION")
        self.determined = 1
