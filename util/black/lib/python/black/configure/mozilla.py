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
# A set of Black configuration items specific to working with Mozilla builds.
#

import os, sys, re
if sys.platform.startswith("win"):
    import _winreg
import black.configure
from black.configure import Datum, ConfigureError, RunEnvScript, SetEnvVar, SetPathEnvVar




class SetMozBits(SetEnvVar):
    def __init__(self):
        SetEnvVar.__init__(self, "MOZ_BITS")

    def _Determine_Do(self):
        if sys.platform.startswith("win"):
            self.applicable = 1
            mozBits = os.environ.get(self.name, None)
            if mozBits:
                self.value = mozBits
            else:
                self.value = 32
        else:
            self.applicable = 0
        self.determined = 1

class SetXpcomDebugBreakDebug(SetEnvVar):
    def __init__(self):
        SetEnvVar.__init__(self, "XPCOM_DEBUG_BREAK")

    def _Determine_Do(self):
        self.applicable = 1
        self.value = os.environ.get(self.name, None)
        if self.value is None and black.configure.items.has_key("buildType"):
            buildType = black.configure.items["buildType"].Get()
            if buildType == "debug":
                self.value = 'warn'
            else:
                self.value = None
        self.determined = 1

class SetMozDebug(SetEnvVar):
    def __init__(self):
        SetEnvVar.__init__(self, "MOZ_DEBUG")

    def _Determine_Do(self):
        self.applicable = 1
        if black.configure.items.has_key("buildType"):
            buildType = black.configure.items["buildType"].Get()
            if buildType == "debug":
                self.value = 1
            else:
                self.value = None
        else:
            self.value = os.environ.get(self.name, None)
        self.determined = 1


class SetMozillaOfficial(SetEnvVar):
    def __init__(self):
        SetEnvVar.__init__(self, "MOZILLA_OFFICIAL",
                           acceptedOptions=("", ["mozilla-official="]))

    def _Determine_Do(self):
        self.applicable = 1
        for opt, optarg in self.chosenOptions:
            if opt == "--mozilla-official":
                self.value = optarg
                break
        else:
            if os.environ.has_key(self.name):
                self.value = os.environ[self.name]
            else:
                self.value = 1 # default is set
        self.determined = 1


class SetBuildOfficial(SetEnvVar):
    # only used when building Mozilla itself
    # XXX how is this diff from MOZILLA_OFFICIAL?
    def __init__(self):
        SetEnvVar.__init__(self, "BUILD_OFFICIAL",
            acceptedOptions=("", ["build-official="]))

    def _Determine_Do(self):
        self.applicable = 1
        for opt, optarg in self.chosenOptions:
            if opt == "--build-official":
                self.value = optarg
                break
        else:
            if os.environ.has_key(self.name):
                self.value = os.environ[self.name]
            else:
                self.value = 1 # default is set
        self.determined = 1


class SetMozDisableJarPackaging(SetEnvVar):
    # only used when building Mozilla itself
    def __init__(self):
        SetEnvVar.__init__(self, "MOZ_DISABLE_JAR_PACKAGING",
            acceptedOptions=("", ["moz-disable-jar-packaging="]))

    def _Determine_Do(self):
        self.applicable = 1
        for opt, optarg in self.chosenOptions:
            if opt == "--moz-disable-jar-packaging":
                self.value = optarg
                break
        else:
            if os.environ.has_key(self.name):
                self.value = os.environ[self.name]
            else:
                self.value = None # default is unset
        self.determined = 1


class SetMozDisableTests(SetEnvVar):
    def __init__(self):
        SetEnvVar.__init__(self, "DISABLE_TESTS",
            acceptedOptions=("", ["moz-disable-tests="]))

    def _Determine_Do(self):
        self.applicable = 1
        for opt, optarg in self.chosenOptions:
            if opt == "--moz-disable-tests":
                self.value = optarg
                break
        else:
            if os.environ.has_key(self.name):
                self.value = os.environ[self.name]
            else:
                self.value = 1 # default is set
        self.determined = 1


class SetMozOsTarget(SetEnvVar):
    def __init__(self):
        SetEnvVar.__init__(self, "OS_TARGET",
            acceptedOptions=("", ["moz-os-target="]))

    def _Determine_Do(self):
        if sys.platform.startswith("win"):
            self.applicable = 1
            target = None
            for opt, optarg in self.chosenOptions:
                if opt == "--moz-os-target":
                    target = optarg
            if target is not None:
                if target.lower() == "winnt":
                    self.value = "WINNT"
                elif target.lower() in ("win95", "win98", "win9x"):
                    self.value = "WIN95"
            elif os.environ.has_key(self.name):
                self.value = os.environ[self.name]
            else:
                self.value = "WINNT"  # default
        else:
            self.applicable = 0
        self.determined = 1


class SetMozWinOs(SetEnvVar):
    # a copy of OS_TARGET
    def __init__(self):
        SetEnvVar.__init__(self, "WINOS")

    def _Determine_Do(self):
        if not black.configure.items.has_key("OS_TARGET"):
            black.configure.items["OS_TARGET"] = SetMozOsTarget()
        if black.configure.items["OS_TARGET"].Determine():
            self.applicable = 1
            self.value = black.configure.items["OS_TARGET"].Get()
        else:
            self.applicable = 0
        self.determined = 1


class SetMscVer(SetEnvVar):
    def __init__(self):
        SetEnvVar.__init__(self, "_MSC_VER")

    def _Determine_Do(self):
        if sys.platform.startswith("win"):
            self.applicable = 1
            if os.environ.has_key(self.name):
                self.value = os.environ[self.name]
            else:
                self.value = 1200 # default
        else:
            self.applicable = 0
        self.determined = 1


class SetMozBranch(SetEnvVar):
    def __init__(self):
        SetEnvVar.__init__(self, "MOZ_BRANCH")

    def _Determine_Do(self):
        self.applicable = 1
        if os.environ.has_key(self.name):
            self.value = os.environ[self.name]
        else:
            self.value = None  # default is the trunk
        self.determined = 1


class CreateMozconfig(Datum):
    def __init__(self):
        Datum.__init__(self, "createMozconfig",\
            desc="create the Mozilla Unix build configuration file "\
                 "(~/.mozconfig)",
            serializeAs=[]
        )
    
    def _Determine_Do(self):
        if not sys.platform.startswith("win"):
            self.applicable = 1
            self.value = os.path.expanduser("~/.mozconfig")
            # move an existing one out of the way
            if os.path.isfile(self.value):
                saveName = self.value + ".old"
                out.write("Moving existing '%s' to '%s'...\n" %\
                    (self.value, saveName))
                os.system("mv %s %s" % (self.value, saveName))
            # create the appropriate ~/.mozconfig
            buildType = None
            if black.configure.items.has_key("buildType"):
                buildType = black.configure.items["buildType"].Get()
            buildType = black.configure.items["buildType"].Get()
            if not buildType:
                raise ConfigureError("Could not %s because the build type "\
                    "('buildType' configuration item) could not be "\
                    "determined.\n" % self.desc)
            elif buildType == "release":
                out.write("Creating %s...\n" % self.value)
                fout = open(self.value, "w")
                fout.write("""
# sh
# Build configuration script
#
# See http://www.mozilla.org/build/unix.html for build instructions.
#

# Options for 'configure' (same as command-line options).
ac_add_options --disable-tests
ac_add_options --disable-debug
ac_add_options --enable-optimize
""")
                fout.close()
            elif buildType == "debug":
                out.write("Creating %s...\n" % self.value)
                fout = open(self.value, "w")
                fout.write("""
# sh
# Build configuration script
#
# See http://www.mozilla.org/build/unix.html for build instructions.
#

# Options for 'configure' (same as command-line options).
# none
""")
                fout.close()
            else:
                raise ConfigureError("Could not %s because the build type "\
                    "(%s) is unrecognized.\n" % (self.desc, buildType))
        else:
            self.applicable = 0
        self.determined = 1


class SetMozTools(SetEnvVar):
    def __init__(self):
        SetEnvVar.__init__(self, "MOZ_TOOLS")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise ConfigureError("Could not determine value for MOZ_TOOLS. "\
                "Either manually set MOZ_TOOLS or use the --moz-tools "\
                "option.\n")
        # Have to make sure this is the NEW MOZ_TOOLS.
        # - ensure that MOZ_TOOLS/bin/gmake.exe is of version 3.79.1 or greater
        #   (In the old wintools.zip it was version 3.74)
        gmakeExe = os.path.join(self.value, "bin", "gmake.exe")
        if not os.path.isfile(gmakeExe):
            raise ConfigureError("MOZ_TOOLS is bogus, there is no gmake "\
                "executable (%s) there.\n" % gmakeExe)
        cmd = '"%s" --version' % gmakeExe
        o = os.popen(cmd)
        outputLines = o.readlines()
        o.close()
        versionRe = re.compile("^GNU Make version (?P<version>[0-9.]+)")
        minVersion = "3.79.1"
        versionMatch = versionRe.search(outputLines[0])
        if not versionMatch:
            raise ConfigureError("The first line of running '%s' did not "\
                "return a recognized version string syntax." % cmd)
        else:
            version = versionMatch.group("version")
            if version < minVersion:
                raise ConfigureError("The current version of gmake.exe in "\
                    "your MOZ_TOOLS bin directory is %s. It must be at "\
                    "least version %s. This probably indicates that you have "\
                    "the old wintools.zip package from mozilla.org. You "\
                    "need to get the new one from "\
                    "ftp://ftp.mozilla.org/pub/mozilla/source/wintools.zip "\
                    "and install it SEPARATELY from your Cygwin "\
                    "installation. " % (version, minVersion))

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


class SetMozillaFiveHome(SetPathEnvVar):
    def __init__(self):
        SetPathEnvVar.__init__(self, "MOZILLA_FIVE_HOME")

    def _Determine_Do(self):
        if not sys.platform.startswith("win"):
            self.applicable = 1
            self.value = []
            #---- add required entries to the path
            # add the Mozilla bin directory
            if not black.configure.items.has_key("mozBin"):
                black.configure.items["mozBin"] = MozBin()
            
            applicable = black.configure.items["mozBin"].Determine()
            if applicable:
                d = black.configure.items["mozBin"].Get()
                if not self.Contains(d):
                    self.value.append(d)
        else:
            self.applicable = 0
        self.determined = 1


class MozBin(Datum):
    def __init__(self):
        Datum.__init__(self, "mozBin", "the Mozilla bin directory")

    def _Determine_Sufficient(self):
        if self.value is None:
            raise ConfigureError("Could not determine %s. This probably "\
                "means that MOZ_SRC could not be determined.\n" % self.desc)

    def _Determine_Do(self):
        self.applicable = 1
        mozSrc = black.configure.items['MOZ_SRC'].Get()
        if not mozSrc:
            self.value = None
        else:
            if sys.platform.startswith('win'):
                mozBits = black.configure.items['MOZ_BITS'].Get()
                if not mozBits:
                    self.value = None
                else:
                    mozDebug = black.configure.items['MOZ_DEBUG'].Get()
                    if mozDebug:
                        objDir = "WIN%s_D.OBJ" % mozBits
                    else:
                        objDir = "WIN%s_O.OBJ" % mozBits
                    self.value = os.path.join(mozSrc, 'mozilla', 'dist',
                        objDir, 'bin')
            else:
                self.value = os.path.join(mozSrc, 'mozilla', 'dist', 'bin')
        self.determined = 1





