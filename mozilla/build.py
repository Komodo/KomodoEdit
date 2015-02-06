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

r"""
    build.py -- Main build script for Mozilla-devel

    Usage:
        python build.py [<options>] configure <configure-options>
        python build.py [<options>] all
        python build.py [<options>] <some-other-target>

    Standalone Options:
        -h, --help          Print this help and exit
        -t, --targets       Dump a list of supported build targets.
        -h <targ>           Print help on a specific target.
        -v, --verbose       Increase the verbosity of output
        -f, -c, --config <file>
                            Use specified config file

    This script is meant to feel like a makefile. For example you just
    call it with the targets that you want to build. If not target is
    specified then the default 'all' target is used.

    Suggested convention for Komodo version numbers:
    * For development builds you should add 10 to the minor version
      number:
        Komodo Edit 9.0.x development:    -k 9.10
        Komodo IDE 9.0.x development:     -k 9.10
      This allows you to run a production and development build at the
      same time without them trying to hand off to each other.
    
    Suggested configurations are:
    * Komodo 9.0.x release builds:
        python build.py configure -k 9.0 --with-crashreport-symbols
    * Komodo 9.0 development builds:
        python build.py configure -k 9.10
"""
#
# Development Notes:
#   - In general, all relative paths are relative to the root Mozilla-devel
#     dir (i.e. the same dir as this script).
#   - API for methods implementing targets:
#     Any top-level method named target_* is a target for this build
#     file. Each such method should follow the API described here. A
#     target should accept an argv list:
#       def target_foo(argv): ...
#     This argv is akin to the sys.argv that a python script would
#     recieve. For example the call "build configure --foo bar baz"
#     would call target_configure(['configure', '--foo', 'bar', 'baz']).
#     This allows a target to easily use getopt to process options.
#
#     Any target must also return unused elements of argv. This allows
#     the user to call multiple targets in one go: "build clean all"
#     should call target_clean() AND target_all(). This only works if
#     target_clean() properly returns the unused argv element "all".
#     Here is the intented call sequence:
#       target_clean(['clean', 'all') ... returns ['all']
#       target_all(['all']) ... returns []
#
#     If a target cannot build it should raise a BuildError.
#
# TODO:
#   - Consider moving 'build configure' into its own script so the argv
#     burden does not exist for all targets. Or maybe a less burdensome
#     argv mechanism can be devised. Maybe "build configure" could just
#     be special.
#   - targets: patch, package_patchedsrc, mozilla,
#     release_*, clean_*
#   - Maybe make "build all" not force a re-run of Mozilla's 'configure'
#     script. This causes a lot of unnecessary re-building. Then add a
#     -f|--force option to force reconfiguring or it could figure it out
#     properly based on timestamps.
#

import os
from os.path import abspath, join, dirname, basename, isdir, isfile, \
                    exists, isabs
import sys
if sys.platform == "win32" and sys.version.startswith("2.3."):
    import warnings
    warnings.filterwarnings("ignore", module="fcntl", lineno=7)
import getopt
import re
import shutil
import pprint
import time
import glob
import urllib
import urllib2
import string
import types
import logging
import subprocess

sys.path.insert(0, join(dirname(__file__), "..", "util"))
import which
import preprocess
import platinfo
import patchtree
import sh
del sys.path[0]


#---- exceptions

class BuildError(Exception):
    pass

def _getChangeNum():
    # Note that this can be a fairly complex string (perhaps not
    # suitable for inclusion in a filename if ':' is in it). See
    # "svnversion --help" for details.
    up_one_dir = dirname(dirname(abspath(__file__)))
    changestr = _capture_output('svnversion "%s"' % up_one_dir).strip()

    if changestr == "exported":
        changestr = 0  # fallback
    try:
        changenum = int(changestr)
    except ValueError, ex:
        # pull off front number (good enough for our purposes)
        try:
            changenum = int(re.match("(\d+)", changestr).group(1))
            log.warn("simplifying complex changenum from 'svnversion': %s -> %s"
                     " (see `svnversion --help` for details)",
                     changestr, changenum)
        except AttributeError, ex:
            changenum = 0
            log.warn("Failed to get changenum, using 0 instead")
    return changenum



#---- global data

log = logging.getLogger("build")

# Mapping of sys.platform -> support bin directory
gPlat2BinDir = {
    'win32': os.path.abspath('bin-win32'),
    'sunos5': os.path.abspath('bin-solaris-sun'),
    'linux2': os.path.abspath('bin-linux-x86'),
    'hp-uxB': os.path.abspath('bin-hpux'),
    'darwin': os.path.abspath('bin-darwin'),
    'freebsd6': os.path.abspath('bin-freebsd-x86'),
}



#---- configuration globals

gConfigFileName = "config.py" # default config file name

#---- directory structure globals

gPackagesDir = "packages"


#---- internal support stuff

# Recipe: run (0.5.3) in /home/trentm/tm/recipes/cookbook
_RUN_DEFAULT_LOGSTREAM = ("RUN", "DEFAULT", "LOGSTREAM")
def __run_log(logstream, msg, *args, **kwargs):
    if not logstream:
        pass
    elif logstream is _RUN_DEFAULT_LOGSTREAM:
        try:
            log
        except NameError:
            pass
        else:
            if hasattr(log, "debug"):
                log.debug(msg, *args, **kwargs)
    else:
        logstream(msg, *args, **kwargs)

def _run(cmd, logstream=_RUN_DEFAULT_LOGSTREAM):
    """Run the given command.

        "cmd" is the command to run
        "logstream" is an optional logging stream on which to log the 
            command. If None, no logging is done. If unspecifed, this 
            looks for a Logger instance named 'log' and logs the command 
            on log.debug().

    Raises OSError is the command returns a non-zero exit status.
    """
    __run_log(logstream, "running '%s'", cmd)
    retval = os.system(cmd)
    if hasattr(os, "WEXITSTATUS"):
        status = os.WEXITSTATUS(retval)
    else:
        status = retval
    if status:
        #TODO: add std OSError attributes or pick more approp. exception
        raise OSError("error running '%s': %r" % (cmd, status))

def _run_in_dir(cmd, cwd, logstream=_RUN_DEFAULT_LOGSTREAM):
    """Run the given command in the given working directory.

        "cmd" is the command to run
        "cwd" is the directory in which the commmand is run.
        "logstream" is an optional logging stream on which to log the 
            command. If None, no logging is done. If unspecifed, this 
            looks for a Logger instance named 'log' and logs the command 
            on log.debug().

    Raises OSError is the command returns a non-zero exit status.
    """
    old_dir = os.getcwd()
    try:
        os.chdir(cwd)
        __run_log(logstream, "running '%s' in '%s'", cmd, cwd)
        _run(cmd, logstream=None)
    finally:
        os.chdir(old_dir)


def _importConfig():
    import imp
    f = open(gConfigFileName)
    try:
        config = imp.load_source("config", gConfigFileName, f)
    finally:
        f.close()
    return config

def _validateEnv():
    """Setup (if able) and ensure that the environment is appropriate
    for the current config.
    """
    if sys.platform.startswith("win"):
        # Cygwin will cause subtle (or not) build failures.
        try:
            cygpath_path = which.which("cygpath")
        except which.WhichError:
            pass
        else:
            raise BuildError("you have cygwin on your PATH ('cygpath' was "
                             "found at '%s'): we've switched to using the "
                             "new MozillaBuild-based system, cygwin gets "
                             "in the way" % cygpath_path)

        # Ensure have run the MozillaBuild setenv batch file.
        if "MOZILLABUILD" not in os.environ:
            raise BuildError("it doesn't look like you've run the "
                             "MozillaBuild setenv script ('MOZILLABUILD' "
                             "build envvar is not set): run the appropriate"
                             "'setenv-moz-msvc?.bat' in your shell")
        mozilla_build_dir = os.environ["MOZILLABUILD"]
        
        # Some checks to ensure the old MOZ_TOOLS package isn't in the way.
        try:
            nsinstall_path = which.which("nsinstall")
        except which.WhichError:
            raise BuildError("couldn't find 'nsinstall' on the PATH: "
                             "that's weird, you should have it after "
                             "having run the appropriate 'setenv-moz-msvc?.bat'")
        else:
            # on Windows, paths are normally case-insensitive
            if not nsinstall_path.lower().startswith(mozilla_build_dir.lower()):
                raise BuildError("the first 'nsinstall' on your PATH, '%s', "
                                 "is not from the new MozillaBuild package "
                                 "(%s): your old MOZ_TOOLS directory "
                                 "should be removed and removed from "
                                 "your PATH"
                                 % (nsinstall_path, mozilla_build_dir))

        # Ensure have sufficient MozillaBuild version.
        autoconf_213_path = join(mozilla_build_dir, "msys", "local", "bin",
                                 "autoconf-2.13")
        if not exists(autoconf_213_path):
            raise BuildError("couldn't find autoconf 2.13 at '%s': you "
                             "need to install MozillaBuild version 1.1 "
                             "or later" % autoconf_213_path)

        #TODO: Perhaps put a warning out if MOZCONFIG is set because it will
        #      be overridden.


def _validatePython(config):
    """On Mac OS X, even though the Mozilla configure will properly pick
    up our siloed Python (passed in via "PYTHON" in the .mozconfig) there
    is a Mac OS X bug such that the usage of '-framework Python' (or other
    related linking options) *cannot be used to specify a particular Python
    framework*. Instead it'll pick the latest one from /Library/Frameworks.
    
    This is fine as long as
        /Library/Frameworks/Python.framework/Versions/Current
    is of the same X.Y version as the siloed Python.
    
    If that isn't the case, this function will raise an exception with a
    description of how to set the current Python version appropriately.
    """
    return
    if not sys.platform == "darwin":
        return
    
    curr_path = "/Library/Frameworks/Python.framework/Versions/Current"
    curr_pyver = os.readlink(curr_path)
    if curr_pyver == config.pyVer:
        return

    if exists("/Library/Frameworks/Python.framework/Versions/"+config.pyVer):
        err = _dedent("""\
            Your current Python in '/Library/Frameworks'
            is version %s, but you are attempting to build Mozilla/PyXPCOM
            with a siloed Python of version %s. This cannot work on Mac OS X
            because of a limitation in Mac OS X's build tools (viz
            '-framework Python').
            
            To build Mozilla you need to temporarily switch your current
            Python to %s by running:
                sudo support/set-curr-python.py %s
            and then re-run the build.
            
            Afterwards, if you'd like to switch back to Python %s as the
            current, you can run the following:
                sudo support/set-curr-python.py %s
        """ % (curr_pyver, config.pyVer,
               config.pyVer, config.pyVer,
               curr_pyver, curr_pyver))
    else:
        err = _dedent("""\
            Your current Python in '/Library/Frameworks'
            is version %s, but you are attempting to build Mozilla/PyXPCOM
            with a siloed Python of version %s. This cannot work on Mac OS X
            because of a limitation in Mac OS X's build tools (viz
            '-framework Python').
            
            To build Mozilla you need to install ActivePython %s and then
            re-run the build.
            
            Afterwards, if you'd like to switch back to Python %s as the
            current, you can run the following:
                sudo support/set-curr-python.py %s
        """ % (curr_pyver, config.pyVer,
               config.pyVer,
               curr_pyver, curr_pyver))
    raise BuildError(err)

def _getAutoconfVersion(autoconf=None):
    """Return the version of the given autoconf.

        "autoconf" is a fullpath to the autoconf to check
            It may be left out to default to the first autoconf on the
            PATH.

    Raises an exception if not 'autoconf' can be found. The version is
    returned as a tuple of numbers. For example, version 2.57 is
    returned as: (2, 57). This is convenient for comparison.
    """
    if autoconf is None:
        autoconf = which.which("autoconf")
    elif not os.path.isfile(autoconf):
        raise ValueError("'%s' does not exist" % autoconf)

    # Ask 'autoconf' for its version.
    o = os.popen("autoconf --version")
    firstline = o.readlines()[0]
    o.close()

    # Parse out the version. Example output:
    #
    #   autoconf (GNU Autoconf) 2.57
    #   ...
    #
    #   Autoconf version 2.12
    #
    patterns = [re.compile("\d+\.\d+")]
    for pattern in patterns:
        match = pattern.search(firstline)
        if match:
            versionStr = match.group()
            break
    else:
        raise BuildError("Could not determine version of '%s' from "
                         "the first --version line output: '%s'"
                         % (autoconf, firstline))

    # Make a version tuple.
    version = []
    for part in versionStr.split('.'):
        try:
            version.append(int(part))
        except ValueError:
            version.append(part)

    return tuple(version)


def _setupMozillaEnv():
    """Setup the required environment variables for building Mozilla."""
    config = _importConfig()
    
    #TODO: I suspect that some of these are no longer necessary.
    #      Most or all moz config should be handled by ".mozconfig".
    os.environ["NO_BUILD_REFCNT_LOGGING"] = "0"
    os.environ["XPC_TOOLS_SUPPORT"] = "1"
    #XXX Should still define "MOZILLA_OFFICIAL" to get rebasing (see
    #    top-level Makefile).
    os.environ["MOZILLA_OFFICIAL"] = "1"
    os.environ["BUILD_OFFICIAL"] = "1"
    os.environ["DISABLE_TESTS"] = "1"
    os.environ["MOZ_BITS"] = "32"
    os.environ["FORCE_BUILD_REFCNT_LOGGING"] = "0"

    os.environ["MOZBUILD_STATE_PATH"] = join(config.buildDir, "moz-state")
    
    if config.withCrashReportSymbols:
        os.environ['MOZ_DEBUG_SYMBOLS'] = '1'
        if sys.platform == "darwin" or \
           sys.platform.startswith("linux"):
            os.environ['CFLAGS'] = "-gdwarf-2"
            os.environ['CXXFLAGS'] = "-gdwarf-2"

    if sys.platform == "win32":
        # Important: Tell make to use msys
        os.environ["MSYSTEM"] = "MINGW32"

        # Mozilla SDK checks fails when using msys perl (not sure why), so we
        # ensure ActivePerl is the first perl on the path.
        p = subprocess.Popen("where perl", shell=True, stdout=subprocess.PIPE)
        stdout, _ = p.communicate()
        perl_exes = stdout.splitlines(0)
        if perl_exes and "msys" in perl_exes[0]:
            for alt_perl in perl_exes[1:]:
                if "msys" not in alt_perl:
                    # Insert ActivePerl first on the path.
                    paths = os.environ.get("PATH", "").split(os.pathsep)
                    paths.insert(0, dirname(alt_perl))
                    os.environ["PATH"] = os.pathsep.join(paths)
                    log.info("Placing non-msys perl first on path: %s", alt_perl)
                    break
            else:
                log.warn("Could not find non-msys perl - Windows SDK check may fail")
        else:
            log.warn("Could not find msys perl")

        # This is in conflict with above!
        # Mozilla requires using Msys perl rather than AS perl; use the one
        # bundled with MozillaBuild
        if not "PERL" in os.environ:
            os.environ["PERL"] = os.path.join(os.environ["MOZILLABUILD"],
                                              "msys", "bin", "perl.exe").replace("\\", "/")
    else:
        #TODO: drop what isn't necessary here
        
        #set MOZ_SRC=/export/home/jeffh/p4/Mozilla-devel/build/moz...
        binDir = join(config.buildDir, config.srcTreeName, "mozilla",
                      config.mozObjDir, "dist", "bin")
        os.environ["PATH"] = binDir + os.pathsep + os.environ["PATH"]
        
        # Ensure have the required autoconf version (use our own).
        autoconfPrefix = abspath(join(dirname(__file__), "support", "autoconf-2.13"))
        os.environ["PATH"] = join(autoconfPrefix, "bin") + os.pathsep + os.environ["PATH"]
        os.environ["AC_MACRODIR"] = join(autoconfPrefix, "share", "autoconf")
        autoconf = which.which("autoconf")
        autoconfVer = _getAutoconfVersion(autoconf)
        if autoconfVer > (2, 13):
            verStr = '.'.join([str(i) for i in autoconfVer])
            raise BuildError("Incorrect autoconf version. '%s' is of "
                             "version '%s'. You must have autoconf "
                             "version 2.13 or less first on your PATH "
                             "to build mozilla."
                             % (autoconf, verStr))

        # zsh shell fails when configuring mozilla - so force bash instead.
        if "zsh" in os.environ.get("SHELL", ""):
            log.info("shell: zsh detected, replacing SHELL environment with bash")
            os.environ["SHELL"] = "/bin/bash"

    # Check for Centos 6, and add appropriate LDFLAGS.
    if sys.platform == "linux" and exists("/etc/redhat-release"):
        contents = file("/etc/redhat-release").read()
        if "CentOS release 6." in contents:
            ldflags = os.environ.get('LDFLAGS', '').split(' ')
            ldflags.append("-lrt")
            os.environ['LDFLAGS'] = ' '.join(ldflags)


def _applyMozillaPatch(patchFile, mozSrcDir):
    """apply the given patch to the mozilla source and fail gracefully
    
    "patchFile" is the path to the patch file
    "mozSrcDir" is the path to the mozilla source tree

    If the patch looks like it has already been applied then skip it.
    """
    log.debug("apply mozilla patch '%s' to '%s'", patchFile, mozSrcDir)
    dryRun = 0 # set to 1 for debugging, 0 for normal operation

    # All mozilla patches are presumed to be applicable from the
    # "mozilla" directory.
    cwd = os.path.join(mozSrcDir, "mozilla")
    binDir = gPlat2BinDir[sys.platform]
    try:
        patch = which.which("patch", path=[binDir])
    except which.WhichError:
        try:
            patch = which.which("patch")
        except which.WhichError:
            raise BuildError("Could not find a 'patch' executable.")
    baseArgv = [patch, "-f", "-p0"]


    # Patching fuzz is a problem for us. If not increased then one (at
    # least) patch will not apply. If increased xpcom.patch (at least)
    # will faultily think it has been applied already and not apply.
    if os.path.basename(patchFile) == "xpcom.patch":
        pass
    elif os.path.basename(patchFile) == "extra-timeline-entries.patch":
        #XXX Should fix this requirement because this option can cause
        #    subtle problems.
        baseArgv.append('-F3')
    else:
        pass
        #baseArgv.append('-F3')

    # Skip out if the patch has already been applied.
    argv = baseArgv + ["--dry-run", "-R"] 
    log.debug("see if patch already applied: run %s in '%s'", argv, cwd)
    p = subprocess.Popen(argv, cwd=cwd, shell=True,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    stdout, stderr = p.communicate(open(patchFile, 'r').read())
    retval = p.wait()
    if not retval: # i.e. reverse patch would apply
        log.info("Patch '%s' was already applied. Skipping.", patchFile)
        return

    # Fail if the patch would not apply cleanly.
    argv = baseArgv + ["--dry-run"] 
    log.debug("see if patch will apply cleanly: run %s in '%s'", argv, cwd)
    p = subprocess.Popen(argv, cwd=cwd, shell=True,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    stdout, stderr = p.communicate(open(patchFile, 'r').read())
    retval = p.wait()
    if retval:
        raise BuildError("""\
Patch '%s' will not apply cleanly:
   argv:    %s
   stdin:   %s
   cwd:     %s
   stdout:
%s
   stderr:
%s
""" % (patchFile, argv, patchFile, cwd, stdout, stderr))

    # Apply the patch.
    if dryRun:
        argv = baseArgv + ["--dry-run"]
    else:
        argv = baseArgv
    log.debug("apply patch: run %s in '%s'", argv, cwd)
    p = subprocess.Popen(argv, cwd=cwd, shell=True)
    p.communicate(open(patchFile, 'r').read())
    retval = p.wait()
    if retval:
        raise BuildError("Error applying patch '%s': argv=%r, cwd=%r"\
                         "retval=%r" % (patchFile, argv, cwd, retval))

def _getMozSrcInfo(scheme):
    """Return information about how to get the Mozilla source to use for
    building.
    
        "scheme" defines what mozilla source to use. This is the same as
            what was specified by the 'configure' target's --moz-src=
            option. It can have the following forms:
                <ver>
                    A version string indicating a specific
                    mozilla/firefox source tarball package. E.g.:
                         900 - correstponds to Mozilla 9.0
                <path-to-tarball>
                    A path to a mozilla/firefox source tarball to use
                    for the source.

    The return value is a dict with the suggested configuration
    variables identifying the mozilla source.
        {
         'mozVer':          The Mozilla version number as a float, i.e. 35.0
         'mozSrcType':      <'hg', 'git' or 'tarball'>,
         'mozSrcName':      <a short string to *loosely* describing the mozilla src>,
         # The following only if mozSrcType==hg:
         'mozSrcHgRepo':    HG repository to checkout from.
         'mozSrcHgTag':     HG repository tag.
         # The following only if mozSrcType==tarball:
         'mozSrcTarball':   <path to a Mozilla source tarball>,
        }
    """
    config = {}

    if scheme.endswith(".tar.gz") or scheme.endswith(".tar.bz2"):
        suffix = scheme.endswith(".tar.gz") and ".tar.gz" or ".tar.bz2"
        if not isfile(scheme):
            raise BuildError("Configured mozilla source tarball, '%s', "\
                             "does not exist." % scheme)
        config.update(
            mozSrcType="tarball",
            mozSrcTarball=scheme,
        )

        patterns = [re.compile("^firefox-(.*?)-source%s$"
                             % re.escape(suffix))]
        for pattern in patterns:
            scheme_basename = basename(scheme)
            match = pattern.match(scheme_basename)
            if match:
                config["mozSrcName"] = match.group(1)
                ver_match = re.match(r"(\d+\.\d+)\..*", match.group(1))
                if not ver_match:
                    raise BuildError("Could not detect source file version: %r"
                                     % (scheme_basename, ))
                version_num = float(ver_match.group(1))
                # Set the Mozilla version.
                config["mozVer"] = version_num
                break
        else:
            config["mozSrcName"] = name

    elif scheme.startswith("git:"):
        # "git:1700" for "Gecko 17", or "git:FIREFOX_16_0_1_RELEASE" for a tag
        config.update(
            mozSrcType="git",
            mozSrcGitRev=scheme.split(":", 1)[-1],
        )
        if re.match(r"^\d+$", config["mozSrcGitRev"]):
            config["mozVer"] = round(int(config["mozSrcGitRev"]) / 100.0, 2) # all numbers
        else:
            # tag
            verString = re.search(r"\d+(?:_\d+)*", config["mozSrcGitRev"]).group(0)
            verList = verString.split("_") + ["0", "0"]
            config["mozVer"] = float(verList[0] + "." + "".join(verList[1:])[:2])
        config["mozSrcName"] = "moz%s" % (int(config["mozVer"] * 100), )

    elif re.match(r"^(?P<ver>(\d+?)+)(:(?P<tag>\w+))?$", scheme): # VER[:TAG]
        match = re.match(r"^(?P<ver>(\d+?)+)(:(?P<tag>\w+))?$", scheme)
        config.update(
            mozSrcType="hg",
            mozSrcHgRepo=match.group("ver"),
            mozSrcHgTag=match.group("tag"),
        )
        # Determine a nice short name loosely describing this Mercurial
        # source.
        config["mozSrcName"] = "moz%s" % (config["mozSrcHgRepo"], )
        config["mozVer"] = round(int(config["mozSrcHgRepo"]) / 100.0, 2)

    elif re.match(r"^FIREFOX_.*_RELEASE$", scheme): # TAG
        # Determine the version from the tag.
        match = re.match(r"^FIREFOX_(?P<ver>\d+\_\d+\_\d+)(?P<type>esr)?_RELEASE$", scheme)
        if not match:
            raise BuildError("Unexpected mozSrc tag %r" % scheme)
        config["mozSrcType"] = "hg"
        config["mozSrcHgTag"] = scheme
        ver = match.group("ver").replace("_", "")
        hgtype = match.group("type") or ""
        config["mozVer"] = round(int(ver) / 100.0, 2)
        config["mozSrcHgRepo"] = ver + hgtype
        config["mozSrcName"] = "moz%s" % (config["mozSrcHgRepo"], )
    else:
        raise BuildError("Unexpected mozSrc %r" % scheme)

    return config


def _reporthook(numblocks, blocksize, filesize, url=None):
    #print "reporthook(%s, %s, %s)" % (numblocks, blocksize, filesize)
    base = os.path.basename(url)
    #XXX Should handle possible filesize=-1.
    try:
        percent = min((numblocks*blocksize*100)/filesize, 100)
    except:
        percent = 100
    if numblocks != 0:
        sys.stdout.write("\b"*70)
    sys.stdout.write("%-66s%3d%%" % (base, percent))

def _download_url(url, dst):
    log.info("get url '%s' to '%s'", url, dst)
    if sys.stdout.isatty():
        urllib.urlretrieve(url, dst,
                           lambda nb, bs, fs, url=url: _reporthook(nb,bs,fs,url))
        sys.stdout.write('\n')
    else:
        urllib.urlretrieve(url, dst)


# Recipe: dedent (0.1.2)
def _dedentlines(lines, tabsize=8, skip_first_line=False):
    """_dedentlines(lines, tabsize=8, skip_first_line=False) -> dedented lines
    
        "lines" is a list of lines to dedent.
        "tabsize" is the tab width to use for indent width calculations.
        "skip_first_line" is a boolean indicating if the first line should
            be skipped for calculating the indent width and for dedenting.
            This is sometimes useful for docstrings and similar.
    
    Same as dedent() except operates on a sequence of lines. Note: the
    lines list is modified **in-place**.
    """
    DEBUG = False
    if DEBUG: 
        print "dedent: dedent(..., tabsize=%d, skip_first_line=%r)"\
              % (tabsize, skip_first_line)
    indents = []
    margin = None
    for i, line in enumerate(lines):
        if i == 0 and skip_first_line: continue
        indent = 0
        for ch in line:
            if ch == ' ':
                indent += 1
            elif ch == '\t':
                indent += tabsize - (indent % tabsize)
            elif ch in '\r\n':
                continue # skip all-whitespace lines
            else:
                break
        else:
            continue # skip all-whitespace lines
        if DEBUG: print "dedent: indent=%d: %r" % (indent, line)
        if margin is None:
            margin = indent
        else:
            margin = min(margin, indent)
    if DEBUG: print "dedent: margin=%r" % margin

    if margin is not None and margin > 0:
        for i, line in enumerate(lines):
            if i == 0 and skip_first_line: continue
            removed = 0
            for j, ch in enumerate(line):
                if ch == ' ':
                    removed += 1
                elif ch == '\t':
                    removed += tabsize - (removed % tabsize)
                elif ch in '\r\n':
                    if DEBUG: print "dedent: %r: EOL -> strip up to EOL" % line
                    lines[i] = lines[i][j:]
                    break
                else:
                    raise ValueError("unexpected non-whitespace char %r in "
                                     "line %r while removing %d-space margin"
                                     % (ch, line, margin))
                if DEBUG:
                    print "dedent: %r: %r -> removed %d/%d"\
                          % (line, ch, removed, margin)
                if removed == margin:
                    lines[i] = lines[i][j+1:]
                    break
                elif removed > margin:
                    lines[i] = ' '*(removed-margin) + lines[i][j+1:]
                    break
            else:
                if removed:
                    lines[i] = lines[i][removed:]
    return lines

def _dedent(text, tabsize=8, skip_first_line=False):
    """_dedent(text, tabsize=8, skip_first_line=False) -> dedented text

        "text" is the text to dedent.
        "tabsize" is the tab width to use for indent width calculations.
        "skip_first_line" is a boolean indicating if the first line should
            be skipped for calculating the indent width and for dedenting.
            This is sometimes useful for docstrings and similar.
    
    textwrap.dedent(s), but don't expand tabs to spaces
    """
    lines = text.splitlines(1)
    _dedentlines(lines, tabsize=tabsize, skip_first_line=skip_first_line)
    return ''.join(lines)


# Recipe: banner (1.0+) in C:\trentm\tm\recipes\cookbook
def _banner(text, ch='=', length=78):
    """Return a banner line centering the given text.
    
        "text" is the text to show in the banner. None can be given to have
            no text.
        "ch" (optional, default '=') is the banner line character (can
            also be a short string to repeat).
        "length" (optional, default 78) is the length of banner to make.

    Examples:
        >>> _banner("Peggy Sue")
        '================================= Peggy Sue =================================='
        >>> _banner("Peggy Sue", ch='-', length=50)
        '------------------- Peggy Sue --------------------'
        >>> _banner("Pretty pretty pretty pretty Peggy Sue", length=40)
        'Pretty pretty pretty pretty Peggy Sue'
    """
    if text is None:
        return ch * length
    elif len(text) + 2 + len(ch)*2 > length:
        # Not enough space for even one line char (plus space) around text.
        return text
    else:
        remain = length - (len(text) + 2)
        prefix_len = remain / 2
        suffix_len = remain - prefix_len
        if len(ch) == 1:
            prefix = ch * prefix_len
            suffix = ch * suffix_len
        else:
            prefix = ch * (prefix_len/len(ch)) + ch[:prefix_len%len(ch)]
            suffix = ch * (suffix_len/len(ch)) + ch[:suffix_len%len(ch)]
        return prefix + ' ' + text + ' ' + suffix



#---- the targets

def target_regmozbuild(argv=["regmozbuild"]):
    """Register the current mozilla build."""
    log.info("target: regmozbuild")
    sys.path.insert(0, "support")
    try:
        import regmozbuild
    finally:
        del sys.path[0]
    regmozbuild.register_build(gConfigFileName)
    return argv[1:]


def target_configure(argv):
    r"""configure some options for building Mozilla
    
    Common Options:
        -k #.#, --komodo-version=#.#
            komodo version for which to build mozilla

        --blessed
            Komodo production releases only use so-called "blessed"
            Mozilla build. This is just a boolean flag set in its
            configuration to help ensure that we don't release Komodo
            using a development Mozilla build.
        
        --moz-src=<scheme>
            Specify what mozilla source to use. Can be:
                ver[:TAG]
                    A version string indicating a specific
                    mozilla/firefox version - the repository or tarball will be
                    automatically worked out by the build system.
                <path-to-tarball>
                    A path to a mozilla/firefox source tarball to use
                    for the source.
            
            This table might help you pick a relevant scheme and tag.

            Scheme      Tag                     KoVer   FFVer   MozVer
            ----------  ----------------------  ------  ------  ----------
            3100        FIREFOX_31_0_RELEASE    9.0.X  31.0.X   31.00
            3500        FIREFOX_35_0_RELEASE    9.0.X  35.0.X   35.00

    Other Options:
        -r, --reconfigure
            Re-run configuration with the previous config options.

        --komodo (the default)
        --suite (i.e. the Mozilla suite)
        --browser (i.e. Firefox)
        --moz-app=komodo (the only possible choice)
        --debug, --release, --symbols
            specify mozilla build-type (default: release)

        --universal
            create a macosx universal mozilla build

        --strip, --no-strip
            Whether to strip libraries after the build. By default
            stripping is *not* done.

        --with-crashreport-symbols
            Enable builds that contain crash reporting symbols.

        -P <pyver>, --python-version=<pyver>
            Specify the version of the local prebuilt Python to build with
            and siloed into this Mozilla build. By default the latest
            version is used (currently 2.7).

        --python=<path>
            Instead of -P|--python-version you may use this option to
            specify a full path to a Python executable to use. No guarantees
            that this is going to work, though.

        --no-mar
            Do not build the bsdiff and mar modules.

        --options=
            additional mozilla build options that may
            not be in our default configuration
            example: --options=enable-jprof,enable-leaky
        
        --extensions=
            additional mozilla extensions to build
            example: --extensions=inspector,irc
        
        --moz-config=<.mozconfig>
            Specify a .mozconfig file to use instead
            all above options will be ignored
    
        --build-dir=<dir>
            By default the build directory is named "build" top-level dir.
            This directory can be changed with this configuration option.

        --build-tag=<tag>
        --src-tree-name=<name>
            By default the src tree is "named" based on the --moz-src
            (and often the komodo version). This is the directory under
            the "build" top-level dir.
            
            This can be further specialize by giving a --build-tag: it
            is appended to the src tree name.
            
            Alternatively the --src-tree-name option can be used to
            completely override this name (though this should be rarely
            necessary).

        --with-tests, --without-tests
            Whether or not to build the mozilla tests (which include the
            sample plugin in modules/plugin/samples/simple). If not
            specified then tests are NOT built for release builds and
            ARE for debug builds.

        --compiler=<vc9|vc11>  # Windows-only
            There is *some* support for building Mozilla/Firefox with
            the non-default compiler on Windows. Currently we build with
            VC11 and this is the default.

        --gcc=<gcc44>  # Unix-only
        --gxx=<g++44>  # Unix-only
            There is *some* support for building Mozilla/Firefox with
            the non-default compiler on Linux. Currently we build with
            gcc44, g++44 and this is the default.

        --moz-objdir=<name>
            Specify a name to use for the MOZ_OBJDIR: the directory in
            the mozilla tree under which all build products go.

    The configure target creates a persistent configuration in
    "config.py". The specified configuration is used by other targets.

    See "build.py -h" for some typical configurations argument sets.
    """
    log.info("target: configure")

    # Configuration defaults.
    pi = platinfo.PlatInfo()
    config = {
        "blessed": False,
        "platform": pi.name("os", "arch"),
        "platinfo": pi.as_dict(),
        "configureOptions": argv[1:],
        "buildType": "release",
        "buildOpt": [],
        "enableMar": True,
        "komodoVersion": BuildError("don't have a Komodo version: use '--komodo-version'"),
        "python": None,
        "pythonVersion": None,
        "buildTag": None,
        "srcTreeName": None,
        "buildDir": abspath("build"),
        "mozconfig": None,
        "jsStandalone": False,
        "mozSrcScheme": "3500",
        "withCrashReportSymbols": False,
        "withPGOGeneration": False,
        "withPGOCollection": False,
        "stripBuild": False,
        "compiler": None, # Windows-only; 'vc11' (the default)
        "gcc": None, # Unix-only; 'gcc44' (the default)
        "gxx": None, # Unix-only; 'g++44' (the default)
        "mozObjDir": None,
        "universal": False,
        "patchesDirs": ["patches-new"],
    }

    mozBuildOptions = []
    if sys.platform.startswith("linux"):
        # Avoid having a dependency on libstdc++
        mozBuildOptions.append('enable-stdcxx-compat')
        # Disable gstreamer.
        mozBuildOptions.append('disable-gstreamer')

    mozMakeOptions = []
    mozBuildExtensions = []
    mozRawOptions = []
       
    # Process options.
    try:
        optlist, remainder = getopt.getopt(argv[1:], "rk:P:j:",
            ["reconfigure",
             "debug", "release", "symbols",
             "komodo-version=", "python=", "python-version=",
             "moz-src=",
             "blessed", "universal",
             "komodo", "moz-app=",
             "with-crashreport-symbols",
             "with-pgo-generation",
             "with-pgo-collection",
             "strip", "no-strip",
             "no-mar",
             "with-tests", "without-tests", 
             "js",
             "options=", "extensions=", "moz-config=",
             "build-dir=",
             "src-tree-name=",
             "build-name=",  # this is deprecated, use --src-tree-name
             "build-tag=",
             "p4-changenum=",
             "compiler=", "gcc=", "gxx=",
             "moz-objdir="])
    except getopt.GetoptError, msg:
        raise BuildError("configure: %s" % str(msg))

    for opt, optarg in optlist:
        if opt in ("-r", "--reconfigure"):
            log.info("reconfiguring...")
            old_config = _importConfig()
            new_argv = ["configure"] \
                       + old_config.configureOptions \
                       + argv[1:]
            new_argv.remove(opt)
            return target_configure(new_argv)
        elif opt == "--debug":
            config["buildType"] = "debug"
        elif opt == "--symbols":
            config["buildType"] = "symbols"
        elif opt == "--release":
            config["buildType"] = "release"
        elif opt == "--blessed":
            config["blessed"] = True
        elif opt == "--universal":
            if sys.platform != "darwin":
                raise BuildError("Universal builds are only supported on Mac OSX")
            config["universal"] = True
        elif opt == "--js":
            config["jsStandalone"] = True
        elif opt == "--no-mar":
            config["enableMar"] = False
        elif opt in ("-k", "--komodo-version"):
            if not re.match("^\d+\.\d+$", optarg):
                raise BuildError("illegal value for --komodo-version, it "\
                                 "must be of the form #.#: %r" % optarg)
            config["komodoVersion"] = optarg
            config["komodoUndottedVersion"] = optarg.replace('.', '')
            config["komodoCommaVersion"] = optarg.replace('.', ',')
        elif opt == "--python":
            config["python"] = optarg
        elif opt in ("-P", "--python-version"):
            config["pythonVersion"] = optarg
        elif opt == "--build-dir":
            config["buildDir"] = abspath(os.path.expanduser(optarg))
        elif opt == "--build-tag":
            config["buildTag"] = optarg
        elif opt == "--build-name":
            raise BuildError("the '--build-name' option is obsolete, "
                             "use '--src-tree-name' instead")
        elif opt == "--src-tree-name":
            config["srcTreeName"] = optarg
        elif opt == "--moz-src":
            config["mozSrcScheme"] = optarg
        elif opt == "--moz-config":
            f = open(optarg)
            config["mozconfig"] = f.read()
            f.close()
        elif opt == "--options":
            for o in optarg.split(','):
                mozBuildOptions.append(o)
        elif opt == "--extensions":
            for ext in optarg.split(','):
                mozBuildExtensions.append(ext)
        elif opt == "--with-crashreport-symbols":
            config["withCrashReportSymbols"] = True
        elif opt == "--with-pgo-generation":
            config["withPGOGeneration"] = True
        elif opt == "--with-pgo-collection":
            config["withPGOCollection"] = True
        elif opt == "--with-tests":
            config["withTests"] = True
        elif opt == "--without-tests":
            config["withTests"] = False
        elif opt == "--strip":
            config["stripBuild"] = True
        elif opt == "--no-strip":
            config["stripBuild"] = False
            config["buildOpt"].append("ns")
        elif opt == "--compiler":
            assert sys.platform == "win32", \
                "'--compiler' configure option is only supported on Windows"
            validCompilers = ('vc9', 'vc11')
            assert optarg in validCompilers, \
                "invalid compiler value (%s), must be one of: %s"\
                % (optarg, validCompilers)
            config["compiler"] = optarg
        elif opt == "--gcc" or opt == "--gxx":
            assert sys.platform != "win32", \
                "'--gcc' configure option is only supported on Unix"
            config[opt[2:]] = optarg
        elif opt == "--moz-objdir":
            config["mozObjDir"] = optarg
        elif opt == "-j":
            if not re.match(r"^\d+$", optarg):
                raise BuildError("Invalid value for -j, integer expected: %r" %
                                 optarg)
            config["parallel"] = int(optarg)

    # Ensure all require information was specified.
    for name, value in config.items():
        if isinstance(value, Exception):
            raise value

    if sys.platform.startswith("win") and config["buildDir"][1] == ":":
        # NSS builds fail if the object directory doesn't use a lower case
        # drive letter :(
        config["buildDir"] = config["buildDir"][0].lower() + config["buildDir"][1:]

    # Now determine the rest of the configuration items given the user
    # options.

    config.update(
        _getMozSrcInfo(config["mozSrcScheme"])
    )

    # Finish determining the configuration: some defaults depend on user
    # settings.
    buildType = config["buildType"] # shorthand
    if sys.platform == "darwin":
        # See http://developer.mozilla.org/en/docs/Mac_OS_X_Build_Prerequisites#.mozconfig_Options_and_Other_Tunables
        # for issues with setting:
        #   ac_add_options --enable-macos-target=version

        osx_major_ver = int(os.uname()[2].split(".")[0])
        # The osx_major_ver has the following values:
        #   14: Yosemite (OS X 10.10)
        #   13: Mavericks (OS X 10.9)
        #   12: Mountain Lion (OS X 10.8)
        #   11: Lion (OS X 10.7)
        #   10: Snow Leopard (OS X 10.6)

        mozVer = config["mozVer"]

        # Komodo 9 supports Mavericks and higher.
        macosx_min_version = "10.9"
        mozBuildOptions.append("enable-macos-target=%s" % macosx_min_version)

        gcc = config.get("gcc") or os.environ.get("CC")
        gxx = config.get("gxx") or os.environ.get("CXX")
        if gcc is None or gxx is None:
            # Prefer clang when it's available.
            try:
                gcc = which.which("clang")
                gxx = which.which("clang++")
            except which.WhichError:
                gcc = None
        if gcc is None:
            try:
                # prefer gcc/g++ 4.2
                gcc = which.which("gcc-4.2")
                gxx = which.which("g++-4.2")
            except which.WhichError:
                gcc = None
        if gcc is None:
            gcc = which.which("gcc")
            gxx = which.which("g++")
        assert gcc
        assert gxx

        # Bug 95983 - jemalloc is killing us when forking (Python subprocess).
        mozBuildOptions.append("disable-jemalloc")
        #if "gcc" in gcc and osx_major_ver <= 10: # aka Snow Leopard or lesser
        #    # Disable jemalloc, as it fails to build when using gcc.
        #    mozBuildOptions.append("disable-jemalloc")
        # check if we're using gcc or clang

        version_string = _capture_output("%s --version" % (gcc,))
        is_gcc = ("Free Software Foundation" in version_string)
        if osx_major_ver >= 10: # aka Snow Leopard or greater
            if is_gcc:
                version = version_string.split(" ")[2]
                from distutils.version import LooseVersion
                if LooseVersion(version) < "4.2":
                    raise BuildError("GCC 4.2 or higher is required, " \
                                     "you have GCC %s, please install a " \
                                     "newer version." \
                                     % version)
            # Force x86_64 for now
            mozRawOptions.append('export CC="%s -arch x86_64"' % (gcc,))
            mozRawOptions.append('export CXX="%s -arch x86_64"' % (gxx,))
            mozRawOptions.append("mk_add_options AUTOCONF=autoconf213")
        config["gcc"] = gcc
        config["gxx"] = gxx

    elif sys.platform.startswith("linux"):
        gcc = config.get("gcc") or os.environ.get("CC")
        gxx = config.get("gxx") or os.environ.get("CXX")
        if gcc is None:
            try:
                # prefer gcc/g++ 4.4 (for CentOS 5.5)
                gcc = which.which("gcc44")
                gxx = which.which("g++44")
            except which.WhichError:
                pass
        if gcc is None:
            gcc = which.which("gcc")
            gxx = which.which("g++")
        version = _capture_output("%s --version" % (gcc,)).split(" ")[2]
        from distutils.version import LooseVersion
        if LooseVersion(version) < "4.2":
            machine = _capture_output("%s -dumpmachine" % (gcc,)).split("-")[0]
            if machine == "x86_64":
                error = "GCC 4.2 or higher is required due to visibility-" \
                        "related issues; you have GCC %s, please install a " \
                        "newer version. " \
                        % version
                if "distro" in config["platinfo"]:
                    if config["platinfo"]["distro"] == "centos":
                        error += "For CentOS, please try the gcc44-c++ package."
                raise BuildError(error)
            else:
                # we don't _need_ gcc44 here...
                log.warn("Using outdated gcc %s", version)
        config["gcc"] = gcc
        config["gxx"] = gxx
        mozRawOptions.append("export CC=%s" % gcc)
        mozRawOptions.append("export CXX=%s" % gxx)
        # Try to enable gold linker where available.
        mozBuildOptions.append('enable-gold')

    config["changenum"] = _getChangeNum()
    if sys.platform == "win32":
        defaultWinCompiler = "vc11"
        if not config["compiler"]:
            # Attempt to auto-detect the compiler version number
            try:
                ver_info = _capture_output("cl -?", capture_stderr=True).splitlines()[0]
                # Match for 4 runs of digits separated by period or comma
                # (to account for European locales)
                match = re.search(r"([0-9]+[.,]){3}[0-9]", ver_info)
                if match:
                    version = match.group(0).split(",", 1)[0].split(".", 1)[0]
                else:
                    version = None
            except:
                version = None # Failed to auto-detect version
            config["compiler"] = {
                # version numbers taken from https://en.wikipedia.org/wiki/Visual_C++
                "14": "vc8",   # Visual C++ 2005
                "15": "vc9",   # Visual C++ 2008
                "16": "vc10",  # Visual C++ 2010
                "17": "vc11",  # Visual C++ 2012
                "18": "vc12",  # Visual C++ 2013
                "19": "vc13",  # Visual C++ 2015
            }.get(version, defaultWinCompiler)
        if config["compiler"] != defaultWinCompiler:
            config["buildOpt"].append(config["compiler"])

    if config["python"] is None:
        if config["pythonVersion"] is None:
            config["pythonVersion"] = "2.7"
        if config["pythonVersion"] in ("2.6", "2.7"):
            config["pyVer"] = config["pythonVersion"]
            # Extract the prebuilt Python directory.
            if sys.platform == "win32":
                # bug 96253: we only support 32-bit windows for now
                buildName = "win32-x86-%s" % (config["compiler"],)
            elif sys.platform == "darwin":
                buildName = "macosx"
            else:
                buildName = config["platform"]
            prebuiltDir = join("prebuilt", "python%s" % config["pyVer"],
                               buildName)

            # If the dirs exists and is out-of-date: remove it.
            mtime_zip = os.stat(prebuiltDir+".zip").st_mtime
            if exists(prebuiltDir) \
               and os.stat(prebuiltDir).st_mtime < mtime_zip:
                log.info("removing out of date unzip of prebuilt python "
                         "in `%s'", prebuiltDir)
                if sys.platform == "win32":
                    _run('rd /s/q "%s"' % prebuiltDir)
                else:
                    _run('rm -rf "%s"' % prebuiltDir)

            # If the dir doesn't exist then we need to crack it there.
            if not exists(prebuiltDir):
                log.info("unzipping prebuilt python in `%s'", prebuiltDir)
                prebuiltZip = prebuiltDir + ".zip"
                if not exists(prebuiltZip):
                    raise BuildError("prebuilt Python zip doesn't exist: %s"
                                     % prebuiltZip)
                _run_in_dir("unzip -q -d %s %s"
                            % (basename(prebuiltDir), basename(prebuiltZip)),
                            dirname(prebuiltDir), log.debug)
        else:
            raise BuildError("unexpected value for 'pythonVersion' "
                             "(a.k.a. --python-version): %r"
                             % config["pythonVersion"])

        # Find the Python binary under here.
        if sys.platform == "win32":
            if config["buildType"] == "debug":
                pythonExe = join(prebuiltDir, "python_d.exe")
            else:
                pythonExe = join(prebuiltDir, "python.exe")
        elif sys.platform == "darwin":
            # we can link against a release version of the python framework just fine
            pattern = join(prebuiltDir, "Python.framework", "Versions", 
                           "?.?", "bin", "python")
            pythonExe = glob.glob(pattern)[0]
        else:
            pythonExe = join(prebuiltDir, "bin", "python")
        config["python"] = abspath(pythonExe)

    # Validate options: some combinations don't make sense.
    if config["buildTag"] is not None and config["srcTreeName"] is not None:
        raise BuildError("cannot use both --src-tree-name and "
                         "--build-tag options")

    # Determine the build tree name (encodes src tree config), moz
    # objdir (encodes build config), and full build name (for the packages)
    # unless specifically given.
    shortBuildType = {"release": "rel", "debug": "dbg", "symbols": "sym"}[buildType]
    buildOpts = config["buildOpt"][:]
    buildOpts.sort()
    srcTreeNameBits = [config["mozSrcName"], "ko"+config["komodoVersion"]]
    mozObjDirBits = ["ko", shortBuildType] + buildOpts
    if config["buildTag"]:
        srcTreeNameBits.append(config["buildTag"])
    if config["srcTreeName"] is None:
        config["srcTreeName"] = '-'.join(srcTreeNameBits)
    if config["mozObjDir"] is None:
        config["mozObjDir"] = '-'.join(mozObjDirBits)

    # Determine the exact mozilla build configuration (i.e. the content
    # of '.mozconfig') -- unless specifically given.
    mozVer = config["mozVer"]
    if config["mozconfig"] is None:
        # help viewer was removed from normal builds, enable it for Komodo
        mozBuildOptions.append("enable-help-viewer")

        if not config.get("withTests", False):
            mozBuildOptions.append("disable-tests")
        else:
            mozBuildOptions.append("enable-tests")

        if buildType == "release":
            mozBuildOptions.append('enable-optimize')
            mozBuildOptions.append('disable-debug')
        elif buildType == "debug":
            mozBuildOptions.append('enable-debug')
            mozBuildOptions.append('disable-optimize')
            mozBuildOptions.append('disable-jemalloc')
            mozBuildOptions.append('disable-crashreporter')

        if config.get("withCrashReportSymbols"):
            mozRawOptions.append('# Debug Symbols')
            mozRawOptions.append('export MOZ_DEBUG_SYMBOLS=1')
            if sys.platform == "win32":
                mozBuildOptions.append('enable-debugger-info-modules=yes')
            else:
                mozBuildOptions.append('enable-debug-symbols=-gdwarf-2')
                mozRawOptions.append('export CFLAGS="-gdwarf-2"')
                mozRawOptions.append('export CXXFLAGS="-gdwarf-2"')

        # Needed for building update-service packages.
        # mozBuildOptions.append('enable-update-packaging')

        mozMakeOptions.append('MOZ_OBJDIR=@TOPSRCDIR@/%s' % config["mozObjDir"])
        
        if "parallel" in config:
            mozMakeOptions.append('MOZ_MAKE_FLAGS=-j%i' % config["parallel"])
        else:
            # No need to specify count, mach will do parallel builds by default
            pass

        config["mozconfig"] = "# Options for 'configure' (same as command-line options).\n"
        
        # osx universal builds
        if sys.platform == 'darwin' and config["universal"]:
            config["mozconfig"] += ". $topsrcdir/build/macosx/universal/mozconfig\n"

        mozBuildOptions.append('enable-application=komodo')

        if config["stripBuild"]:
            mozBuildOptions.append('enable-strip')

        for opt in mozMakeOptions:
            config["mozconfig"] += "mk_add_options %s\n" % opt

        for opt in mozRawOptions:
            config["mozconfig"] += "%s\n" % opt

        for opt in mozBuildOptions:
            config["mozconfig"] += "ac_add_options --%s\n" % opt
    
        config["mozBuildExtensions"] = mozBuildExtensions

    # Error out if it looks like we will hit the subtle limitation on
    # PATH length on Windows.
    if sys.platform == "win32":
        # check if nsinstall is the obsolete version that came with
        # MozillaBuild, which 1) is ANSI, and 2) has a path lenth limitation
        badNsinstall = not _capture_status(["grep",
                                            "-q",
                                            "GetOEMCP",
                                            which.which("nsinstall")])
    if sys.platform == "win32" and badNsinstall:
        # This guy is 192 chars long and fails:
        #   C:\trentm\as\openkomodo-moz19\mozilla\build\cvs-ko5.19-okmoz19\mozilla\ko-rel-ns\_tests\testing\mochitest\tests\dom\tests\mochitest\ajax\scriptaculous\test\unit\_ajax_inplaceeditor_result.html
        # This guy (tweaked) is 189 chars and works:
        #   C:\trentm\as\openkomodo-moz19\mozilla\build\cvs-ko5.19-okmoz19\mozilla\ko-rel-ns\_tests\testing\mochitest\tests\dom\tests\mochitest\ajax\scriptaculous\test\unit\_ajax_inplaceeditor_tex.html
        # I believe the path length limit in the msys/mozilla build-tools
        # somewhere (perhaps in 'nsinstall'?) is 189 characters.
        #
        # Perhaps the actual limit depends on some transformation of the
        # path -- e.g. the msys/cygwin path.
        PATH_LEN_LIMIT = 189 # best guess from experimentation
        # This is the longest subpath in the Mozilla tree that I've come
        # across in builds.
        LONGEST_SUB_PATH = r"\_tests\testing\mochitest\tests\dom\tests\mochitest\ajax\scriptaculous\test\unit\_ajax_inplaceeditor_result.html"
        # Normally we would get the objdir from _get_mozilla_objdir(),
        # but that requires a configured mozilla source tree and we
        # haven't even cracked the source yet. If --moz-objdir was
        # specified then we can calculate it, otherwise we have to guess
        # a little bit.
        mozObjDirGuess = config["mozObjDir"].replace("@CONFIG_GUESS@",
                                                     "i586-pc-msvc")
        mozObjPathGuess = os.path.join(os.path.abspath(config["buildDir"]),
                                       config["srcTreeName"],
                                       "mozilla", mozObjDirGuess)
        longestPathGuess = os.path.join(mozObjPathGuess, LONGEST_SUB_PATH)
        if len(longestPathGuess) > PATH_LEN_LIMIT:
            raise BuildError("""
**************************************************************************
There is a path length limitation in the Mozilla build tool chain of %s
characters (that is a best guess). (I suspect it is cygwin but don't
know that for sure.) If you exceed this you will see subtle errors like
the following when all paths involved *do* exist:

    nsinstall: cannot copy install.rdf to <some-long-path>: \\
        The system cannot find the path specified.

Currently the longest known sub-path in the Mozilla tree is:

    %%MOZ_OBJDIR%%\%s
    (length %s)

which means that your MOZ_OBJDIR cannot be any longer than %s
characters. Yours is:

    %s
    (length %s)

You need to do one or more of the following to work around this problem
(in order of quickest-hack to better long-term solution):

1. Use the "--src-tree-name" and/or "--build-tag" configure options to
   specify a shorter name than the current:
        %s (length %s)
   For example:
        python build.py configure --src-tree-name=FOO ...
        python build.py -h configure
   You might also want to pester Trent to reduce the default name here
   to be shorter.

2. Use the "--moz-objdir" configure option to specify a shorter name
   than the current:
        %s (length %s)
   For example:
        python build.py configure --moz-objdir=obj-FOO ...
        python build.py -h configure
   Note: You have to make sure your value doesn't conflict with any
   top-level files/dirs in the Mozilla source tree. E.g. "dom" is a
   conflict.

3. Change where you check out your Komodo source tree to a shorter
   path. For example, I check out mine to "$HOME/as/komodo".

4. Grab nsinstall.exe from a new XULRunner SDK and replace the one shipped
   in MozillaBuild (%s).
**************************************************************************
""" % (PATH_LEN_LIMIT,
       LONGEST_SUB_PATH, len(LONGEST_SUB_PATH),
       PATH_LEN_LIMIT - len(LONGEST_SUB_PATH),
       mozObjPathGuess, len(mozObjPathGuess),
       config["srcTreeName"], len(config["srcTreeName"]),
       mozObjDirGuess, len(mozObjDirGuess),
       which.which("nsinstall")
      ))

    # Write out configuration.
    fout = open(gConfigFileName, 'w')
    fout.write("""\
#
# config.py -- Mozilla-devel build configuration file
#
# Note: This file is automatically generated by "build configure". Your
# changes will be lost the next time that is run.
#
# See "build -h configure" for details.

""")
    items = config.items()
    items.sort()
    for name, value in items:
        #XXX Might need to do some type checking here to ensure
        #    serialization will work.
        line = "%s = %r\n" % (name, value)
        fout.write(line)
        sys.stdout.write(line)
    fout.close()
    log.info("'%s' config file created", gConfigFileName)

    return remainder

def _relocatePyxpcom(config):
    if sys.platform != "darwin":
        return
    # Correct the shared object dependencies to point to the siloed
    # Python.
    log.info("relocating Python lib dependencies to the siloed Python...")
    libnames = ["_xpcom.so", "lib_xpcom.dylib", "libpyloader.dylib",
                "libpyxpcom.dylib", "libpydom.dylib"]
    libs = []
    distDir = join(config.buildDir, config.srcTreeName, "mozilla",
                   config.mozObjDir, "dist")
    for libname in libnames:
        found = {}
        # we cant use -type f here because different apps will handle
        # files differently, some symlinking while other copying.  We
        # have to resolve the symlink then veryify this is a file
        cmd = "find %s -name %s" % (distDir, libname)
        for line in os.popen(cmd).readlines():
            p = os.path.realpath(line.strip())
            if os.path.isfile(p):
                found[p]=1
        libs += found.keys()
    for lib in libs:
        # Ensure the lib was built against a Python of the correct version.
        landmark = "Python.framework/Versions/%s/Python" % config.pyVer
        old = None
        linkage = os.popen("otool -L %s" % lib).readlines()
        for line in linkage:
            if line.find(landmark) == -1: continue
            old = line.strip().split(None, 1)[0]
            break
        else:
            # Failed to find via path; try looking for the right compat version instead
            landmark = "/Python (compatibility version %s.0, current version %s.0)" % (config.pyVer, config.pyVer)
            for line in linkage:
                if line.strip().endswith(landmark):
                    old = line.strip().split(None, 1)[0]
        if old:
            new = "@rpath/../Frameworks/Python.framework/" \
                  "Versions/%s/Python" % config.pyVer
            cmd = "chmod +w %s && install_name_tool -change %s %s %s"\
                  % (lib, old, new, lib)
            log.info("\t%s", lib)
            _run(cmd)

            # Fix up rpaths so that mozpython launched via bk test can find things.
            # install_name_tool -add_rpath fails if the rpaths already exists, so
            # we need to go read the file first and grep the load commands.
            rpaths = set()
            in_rpath_command = False
            process = subprocess.Popen(["otool", "-l", lib], stdout=subprocess.PIPE)
            output, unused_err = process.communicate()
            if process.poll() != 0:
                raise BuildError("otool -l returned %s" % (process.returncode,))
            for line in output.splitlines():
                if line.startswith("Load command"):
                    in_rpath_command = False # new load command
                elif line.strip() == "cmd LC_RPATH":
                    in_rpath_command = True # This is a LC_RPATH load command
                elif in_rpath_command and line.strip().startswith("path "):
                    # this is an rpath; add it to what we know
                    rpaths.add(line.strip()[len("path "):].rsplit(" (offset ")[0])
            for rpath_rel in [
                        "/.",       # Running Komodo, @executable_path is mozBin
                        "/.." * 7,  # Running tests, @executable_path is siloed python
                    ]:
                rpath = "@executable_path" + rpath_rel
                if rpath not in rpaths:
                    _run('install_name_tool -add_rpath "%s" "%s"' % (rpath, lib))
        else:
            log.error("PyXPCOM was not built correctly!\n%s", ''.join(linkage))


def _disablePythonUserSiteFeature(site_filepath):
    """Turn off the ENABLE_USER_SITE (PEP 370) feature (bug 85725)."""

    log.info("Disabling user site feature in: %r", site_filepath)
    contents = file(site_filepath, "rb").read()
    assert "ENABLE_USER_SITE = None" in contents
    contents = contents.replace("ENABLE_USER_SITE = None",
                                "ENABLE_USER_SITE = False")

    # Disable system site-packages on the Mac - bug 98957.
    if sys.platform == "darwin":
        assert contents.count('if sys.platform == "darwin":') == 1
        contents = contents.replace('if sys.platform == "darwin":', 'if 0: # disabled for KOMODO')

    file(site_filepath, "wb").write(contents)


def target_silo_python(argv=["silo_python"]):
    argv = argv[1:]
    log.info("target: silo_python")
    config = _importConfig()
    pyver = tuple(map(int, config.pyVer.split('.')))
    distDir = join(config.buildDir, config.srcTreeName, "mozilla",
                   config.mozObjDir, "dist")
    if sys.platform == "darwin":
        # The siloed Python framework goes in the app's "Frameworks"
        # dir.
        komodo_app_name = "Komodo%s" % (config.buildType == 'debug'
                                        and 'debug' or '')
        siloDir = join(distDir, "%s.app" % komodo_app_name, "Contents", "Frameworks")
        # In a clean build the "Frameworks" dir may not yet have been
        # created, but the dir up one level should be there.
        if not exists(dirname(siloDir)):
            raise BuildError("error determining main app 'Frameworks' parent "
                             "dir: `%s' does not exist" % dirname(siloDir))
        if not exists(siloDir):
            log.info("mkdir `%s'", siloDir)
            os.mkdir(siloDir)
    else:
        siloDir = join(distDir, "python")
    mozBinDir = join(distDir, "bin")
    mozLibDir = join(distDir, "lib")

    # Abort if it looks like it has already be siloed.
    if sys.platform == "win32":
        if config.buildType == 'debug':
            landmark = join(siloDir, "python_d.exe")
        else:
            landmark = join(siloDir, "python.exe")
    elif sys.platform == "darwin":
        pythons = glob.glob(join(siloDir, "Python.framework",
                                 "Versions", "*", "bin", "python"))
        if pythons:
            landmark = pythons[0]
        else:
            landmark = None
    else:
        landmark = os.path.join(siloDir, "bin", "python")
    if landmark and exists(landmark):
        if argv and argv[0] == "--force":
            argv = argv[1:]
            shutil.rmtree(siloDir)
        else:
            log.info("siloed Python already exists at `%s'", siloDir)
            return argv

    # Copy the configured Python to the silo dir.
    if sys.platform == "win32":
        srcDir = dirname(config.python)
    elif sys.platform == "darwin":
        srcDir = dirname(                       # Python.framework/
                  dirname(                      #  Versions/
                   dirname(                     #   ?.?/
                    dirname(                    #    bin/
                     dirname(config.python))))) #     python
    else:
        srcDir = dirname(dirname(config.python))
    log.info("siloing `%s' to `%s'", srcDir, siloDir)
    if sys.platform == "win32":
        if isdir(siloDir):
            _run("rd /s/q %s" % siloDir)
        os.makedirs(siloDir)
        _run("xcopy /e/q %s %s" % (srcDir, siloDir))

        # Top-level DLLs and w9xpopen.exe need to be in the main
        # executable's dir: i.e. the mozBin dir.
        mozBinBits = [
            join(siloDir, "py*.dll"),
            join(siloDir, "w9xpopen.exe"),
        ]
        for pattern in mozBinBits:
            for path in glob.glob(pattern):
                # *Copy* instead of moving to allow the Python
                # executable to still be run in-place.
                _run("copy /y %s %s" % (path, mozBinDir))
        
        # Need a mozpython.exe in the mozBin dir for "bk start mozpython"
        # to work with PyXPCOM -- for testing, etc.
        _run("copy /y %s %s" % (landmark,
                                join(mozBinDir, "mozpython.exe")))

        siteFile = join(siloDir, "Lib", "site.py")
        _disablePythonUserSiteFeature(siteFile)

    elif sys.platform == "darwin":
        src = join(srcDir, "Python.framework")
        dst = join(siloDir, "Python.framework")
        _run("mkdir -p %s" % dirname(dst))
        _run('cp -R %s %s' % (src, dst))

        # Tweaks so pyxpcom stuff will work when run from the command line.
        # http://bugs.activestate.com/show_bug.cgi?id=66332
        # (a) symlink the main Python exe to the Komodo.app dir and
        # (b) call it 'mozpython' to avoid name conflict.
        relativePythonBin = join("..", "Frameworks", "Python.framework",
                                 "Versions", config.pyVer, "bin", "python")
        mozpythonBin = join(dirname(siloDir), "MacOS", "mozpython")
        if os.path.islink(mozpythonBin):
            os.unlink(mozpythonBin)
        os.symlink(relativePythonBin, mozpythonBin)

        _relocatePyxpcom(config)

        siteFile = join(siloDir, "Python.framework", "Versions", config.pyVer,
                        "lib", "python%s" % (config.pyVer), "site.py")
        _disablePythonUserSiteFeature(siteFile)

    else:
        _run('cp -R "%s" "%s"' % (srcDir, siloDir), log.info)

        # PyXPCOM on Linux (Solaris too I suppose) requires a
        # libpythonXXX.so on the dl load path. We'll just put it in the
        # mozilla bin dir, which will be on the dl load path.
        if config.platinfo["os"] == "freebsd":
            libpythonSoVer = "libpython%s.so.1" % config.pyVer
        else:
            libpythonSoVer = "libpython%s.so.1.0" % config.pyVer
        libpythonSo = "libpython%s.so" % config.pyVer
        _run('cp -f %s/lib/%s %s' % (siloDir, libpythonSoVer, mozBinDir),
             log.info)

        # Relocate the Python install.
        if pyver >= (2,5): # when APy's activestate.py supported relocation
            activestate_py_path = join(siloDir, "lib", "python"+config.pyVer,
                                       "site-packages", "activestate.py")
            if not exists(activestate_py_path):
                # It might be located in the main lib directory.
                activestate_py_path = join(siloDir, "lib",
                                           "python"+config.pyVer,
                                           "activestate.py")
            cmd = "%s %s --relocate" % (config.python, activestate_py_path)
            _run(cmd, log.info)

        # Create a bunch of symlinks.  Note that relocating will force copy
        # everything (and they will no longer be symlinks), so do this after
        # relocating.

        mozbinPythonSoPath = join(mozBinDir, libpythonSo)
        _run('ln -s ./%s %s' % (libpythonSoVer, mozbinPythonSoPath), log.info)
        # Also symlink into the lib dir, to aid in linking - bug 95668.
        mozlibPythonSoPath = join(mozLibDir, libpythonSo)
        _run('ln -s ../bin/%s %s' % (libpythonSo, mozlibPythonSoPath), log.info)

        # Need a mozpython executable in the mozBin dir for "bk start mozpython"
        # to work with PyXPCOM -- for testing, etc.
        _run('ln -s ../python/bin/python%s %s/mozpython' % (config.pyVer, mozBinDir, ),
             log.info)

        siteFile = join(siloDir, "lib", "python%s" % (config.pyVer), "site.py")
        _disablePythonUserSiteFeature(siteFile)

    return argv


def target_pyxpcom_distclean(argv=["pyxpcom_distclean"]):
    log.info("target: pyxpcom_distclean")
    config = _importConfig()
    _setupMozillaEnv()
    moz_obj_dir = join(config.buildDir, config.srcTreeName, "mozilla",
                       config.mozObjDir)
    pyxpcom_obj_dir = join(moz_obj_dir, "extensions", "python")
    if exists(pyxpcom_obj_dir):
        shutil.rmtree(pyxpcom_obj_dir)
    pyxpcom_src_dir = join(config.buildDir, config.srcTreeName, "mozilla",
                           "extensions", "python")
    if exists(pyxpcom_src_dir):
        shutil.rmtree(pyxpcom_src_dir)
    return argv[1:]

def target_src_pyxpcom(argv=["src_pyxpcom"]):
    """Download PyXPCOM sources"""
    log.info("target: src_pyxpcom")
    config = _importConfig()

    pyxpcom_src_dir = join(config.buildDir, config.srcTreeName, "mozilla",
                           "extensions", "python")
    if not exists(pyxpcom_src_dir):
        # Checkout pyxpcom - ensure we use the matching version to mozilla.
        repo_url = "http://hg.mozilla.org/pyxpcom/"
        repo_rev = None
        if int(config.mozVer) <= 31:
            # Requires the matching branch.
            repo_rev = "TAG_MOZILLA_%d" % (int(config.mozVer), )
        cmd = "hg clone"
        if repo_rev is not None:
            cmd += " -r %s" % (repo_rev, )
        cmd += " %s python" % (repo_url, )
        _run_in_dir(cmd, dirname(pyxpcom_src_dir), log.info)
    return argv[1:]

def target_patch_pyxpcom(argv=["patch_pyxpcom"]):
    """Patch PyXPCOM with Komodo-specific patches"""
    log.info("target: patch_pyxpcom")
    target_patch(patch_target='pyxpcom', logFilename="__patchlog_pyxpcom__.py",
                 srcSubDir="extensions/python")
    return argv[1:]

def target_pyxpcom(argv=["pyxpcom"]):
    """Build PyXPCOM and install it into the main Mozilla objdir"""
    log.info("target: pyxpcom")
    config = _importConfig()
    _setupMozillaEnv()

    pyxpcom_src_dir = join(config.buildDir, config.srcTreeName, "mozilla",
                          "extensions", "python")
    if not exists(pyxpcom_src_dir):
        # Get it and patch it!
        try:
            target_src_pyxpcom()
            target_patch_pyxpcom()
        except:
            # If something failed - we nuke the pyxpcom src dir, as we don't
            # know if it's in a working state!
            if exists(pyxpcom_src_dir):
                shutil.rmtree()
            raise

    assert exists(pyxpcom_src_dir), "Pyxpcom source directory does not exist:" \
                                    "%r" % (pyxpcom_src_dir, )

    # Run the autoconf to generate the configure script.
    cmds = []
    # Note: autoconf-2.13 has a special meaning for _get_exe_path()
    autoconf_command = "autoconf-2.13"
    autoconf_path = _get_exe_path(autoconf_command)
    if sys.platform == "win32":
        cmds.append("sh -c %s" % _msys_path_from_path(autoconf_path))
    else:
        cmds.append(autoconf_path)
    _run_in_dir(" && ".join(cmds), pyxpcom_src_dir, log.info)

    # Configure and build pyxpcom.
    cmds = []
    moz_obj_dir = join(config.buildDir, config.srcTreeName, "mozilla",
                       config.mozObjDir)
    pyxpcom_obj_dir = join(moz_obj_dir, "extensions", "python")
    if not exists(pyxpcom_obj_dir):
        os.makedirs(pyxpcom_obj_dir)
    configure_flags = 'PYTHON="%s"' % (_unix_path_from_path(config.python), )
    configure_options = []
    if sys.platform.startswith("linux"):
        configure_flags += " ac_cv_visibility_pragma=no"
        # Need to pass in the same compiler as used in the Moz build,
        # otherwise Linux-x86_64 builds will complain about needing to
        # recompile with -fPIC.
        if config.gcc:
            configure_flags += " CC=%s" % (config.gcc)
        if config.gxx:
            configure_flags += " CXX=%s" % (config.gxx)
    elif sys.platform == "darwin":
        configure_flags += " CC=%s" % (config.gcc or "gcc",)
        configure_flags += " CXX=%s" % (config.gxx or "g++",)

    # Add any custom build FLAGS using the command line args - bug 91389.
    cflags = os.environ.get('CFLAGS', '')
    cxxflags = os.environ.get('CXXFLAGS', '')
    ldflags = os.environ.get('LDFLAGS', '')

    # Support for PGO.
    if config.withPGOGeneration:
        if sys.platform.startswith("linux"):
            cflags   += " -fprofile-generate"
            cxxflags += " -fprofile-generate"
            ldflags  += " -fprofile-generate"
    elif config.withPGOCollection:
        if sys.platform.startswith("linux"):
            cflags   += " -fprofile-use -fprofile-correction"
            cxxflags += " -fprofile-use -fprofile-correction"
            ldflags  += " -fprofile-use -fprofile-correction"

    if cflags:
        configure_flags += ' CFLAGS="%s"' % (cflags)
    if cxxflags:
        configure_flags += ' CXXFLAGS="%s"' % (cxxflags)

    if sys.platform.startswith("linux"):
        # On Linux, manually set the runtime library path (rpath) to pick up the
        # correct Python libraries. Without this, Komodo (pyxpcom) may load the
        # system Python library which will cause Komodo to crash - bug 92707.
        #
        # The magic sauce - need to escape the $ so it's not shell-translated.
        # Note that we want to end up with:
        #   "$ORIGIN:$ORIGIN/../python/lib"
        ldflags += " -Wl,-rpath=\\\\$\\$ORIGIN:\\\\$\\$ORIGIN/../python/lib"
    if ldflags:
        configure_flags += ' LDFLAGS="%s"' % (ldflags, )
    if config.buildType == "debug":
        configure_options.append("--enable-debug")
        configure_options.append("--disable-optimize")
    configure_path = join(pyxpcom_src_dir, "configure")
    cmds = ["%s %s --with-libxul-sdk=%s --disable-tests %s" % (configure_flags, _msys_path_from_path(configure_path), _msys_path_from_path(join(moz_obj_dir, "dist")), " ".join(configure_options)),
            "make"]
    if sys.platform.startswith("win"):
        # on Windows, we must run configure (a shell script) via /bin/sh, with quoting to pass args
        cmds[0] = "sh -c '%s'" % (cmds[0])
    _run_in_dir(" && ".join(cmds), pyxpcom_obj_dir, log.info)

    # The above pyxpcom build creates a "dist" directory in the
    # "extensions/python" directory, we must copy over the details to the
    # Komodo dist directory.
    if sys.platform.startswith("win"):
        copy_cmd = 'xcopy "%s" "%s" /E /K /Y' % (join(pyxpcom_obj_dir, "dist"), join(moz_obj_dir, "dist"))
    else:
        copy_cmd = 'cp -r %s %s' % (join(pyxpcom_obj_dir, "dist"), join(moz_obj_dir))
    _run(copy_cmd, log.info)

    if sys.platform == 'darwin':
        # Also copy into the Komodo.app directory if it exists.
        # Note: Komodo build normally does this, but if we rebuilt pyxpcom then
        #       this step needs to be done now.
        distDir = join(config.buildDir, config.srcTreeName, "mozilla",
                       config.mozObjDir, "dist")
        komodo_app_name = "Komodo%s" % (config.buildType == 'debug'
                                        and 'debug' or '')
        siloDir = join(distDir, "%s.app" % komodo_app_name, "Contents", "Frameworks")
        komodoAppPath = join(dirname(siloDir), "MacOS")
        if exists(komodoAppPath):
            copy_cmd = 'cp -r %s %s' % (join(pyxpcom_obj_dir, "dist", "bin", "*"), komodoAppPath)
            _run(copy_cmd, log.info)
    elif sys.platform.startswith("linux"):
        # Ensure pyxpcom library is loaded at startup, otherwise Komodo will
        # fail to load pyxpcom components.
        dependentlibs_path = join(moz_obj_dir, "dist", "bin", "dependentlibs.list")
        assert exists(dependentlibs_path)
        if "libpyxpcom.so" not in file(dependentlibs_path).read():
            file(dependentlibs_path, "a").write("libpyxpcom.so\n")
            log.info("pyxpcom: added libpyxpcom.so to dependentlibs.list")

    _relocatePyxpcom(config)

    return argv[1:]


def target_update(argv=["update"]):
    """update mozilla source from mercurial"""
    config = _importConfig()
    if not config.mozSrcType != "hg":
        raise BuildError("cannot update source: mozSrcType must be 'hg', not %r" % (config.mozSrcType, ))

    # Abort if there is nothing to update.
    buildDir = os.path.join(config.buildDir, config.srcTreeName)
    landmark = os.path.join(buildDir, "mozilla")
    if not os.path.exists(landmark):
        raise BuildError("cannot update: '%s' does not exist (use "
                         "'./build.py src' to checkout)" % landmark)

    _run("cd %s && hg pull -u && make" % landmark, log.info)

    return argv[1:]


def _extract_tarball(tarball, buildDir):
    log.info("extracting '%s' into '%s'", tarball, buildDir)
    if tarball.endswith(".tar.bz2"):
        cmd = "cd %s && tar xjf %s"\
          % (buildDir, _relpath(tarball, buildDir))
    else:
        cmd = "cd %s && tar xzf %s"\
          % (buildDir, _relpath(tarball, buildDir))
    log.info(cmd)
    retval = os.system(cmd)
    if retval:
        raise BuildError("error running '%s'" % cmd)


def target_src(argv=["src"]):
    """get and extract mozilla source into the working directory"""
    log.info("target: src")
    config = _importConfig()
    buildDir = os.path.join(config.buildDir, config.srcTreeName)
    mozSrcType = config.mozSrcType
    
    # Return immediately if source looks like it is already there.
    landmark = os.path.join(buildDir, "mozilla")
    force_checkout = len(argv) > 1 and argv[1] == '-f'
    if not force_checkout and os.path.exists(landmark):
        log.info("it looks like the src already exists: '%s' exists"
                 % landmark)

        return argv[1:]
    
    # If there is a tarball to use, then get a local copy of it because:
    # 1. it might be a URL and
    # 2. cygwin tar cannot handle absolute paths
    if config.mozSrcType != "tarball":
        tarballPath = None
    else:
        tarballPath = config.mozSrcTarball

    if tarballPath is None:
        tarballLocalPath = None
    elif tarballPath.startswith("http://") \
         or tarballPath.startswith("ftp://"):
        tarballLocalPath = tarballPath[tarballPath.rfind('/')+1:]
        if not exists(tarballLocalPath):
            _download_url(tarballPath, tarballLocalPath)
        else:
            log.info("already have `%s'", tarballLocalPath)
    elif is_remote_path(tarballPath):
        tarballLocalPath = tarballPath[tarballPath.rfind('/')+1:]
        if not exists(tarballLocalPath):
            remote_cp(tarballPath, tarballLocalPath, log.info)
        else:
            log.info("already have `%s'", tarballLocalPath)
    else:
        tarballLocalPath = basename(tarballPath)
        # Ensure we don't copy over same file (causes corruption).
        src, dst = abspath(tarballPath), abspath(tarballLocalPath)
        if sys.platform.startswith("win"):
            src = src.lower()
            dst = dst.lower()
        log.debug("src: '%s'", src)
        log.debug("dst: '%s'", dst)
        if src != dst:
            if exists(tarballLocalPath):
                os.remove(tarballLocalPath)
            log.info("copy '%s' to current dir", tarballLocalPath)
            sh.copy(tarballPath, tarballLocalPath)

    # Extract tarball (if have one) into the build directory.
    # Get the source
    if not os.path.exists(buildDir):
        log.info("mkdir `%s'", buildDir)
        os.makedirs(buildDir)

    if mozSrcType == "hg":
        supportDir = os.path.abspath("support")
        try:
            sys.path.append(supportDir)
            from get_mozilla_tree import getTreeFromVersion, getRepoFromTree, fixRemoteRepo
        finally:
            sys.path.remove(supportDir)
        hgTag = config.mozSrcHgTag
        treeName, hgTag = getTreeFromVersion(hgTag or str(config.mozVer))
        repoURL = getRepoFromTree(treeName)
        hgRepo = os.path.join(buildDir, "mozilla")
        bundleFile = os.path.abspath("%s.hg" % (treeName,))
        bundleURL = "http://ftp.mozilla.org/pub/mozilla.org/firefox/bundles/%s.hg" % (treeName,)

        def inside_activestate_network():
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(("gmail.com",80))
            except:
                return 
            ip_address = s.getsockname()[0]
            s.close()
            return ip_address.startswith("192.168.68.") or ip_address.startswith("192.168.69.")

        if inside_activestate_network():
            try:
                internal_url = "http://komodo.nas1.activestate.com/build-support/mozilla-build/%s.hg" % (treeName,)
                # check that the URL can be opened (not 404, etc.) We don't need to read it.
                urllib2.urlopen(internal_url, None, 10).close()
                bundleURL = internal_url
            except IOError:
                # assume we're not in ActiveState's internal network and can't get
                # access to the local mirror; use the canonical mozilla.org server
                log.info("Failed to reach ActiveState internal mercurial mirror, "
                         "using Mozilla canonical server")

        _run("wget -t 5 -T 30 --progress=dot:mega -O %s %s" % (bundleFile, bundleURL), log.info)
        _run("hg init %s" % (hgRepo,), log.info)
        _run("hg --cwd %s unbundle %s" % (hgRepo, bundleFile), log.info)
        os.unlink(bundleFile)
        fixRemoteRepo(treeName, hgRepo)
        _run("hg --cwd %s pull" % (hgRepo,), log.info)
        if hgTag:
            _run("hg --cwd %s up --rev %s" % (hgRepo, hgTag), log.info)

    elif mozSrcType == "git":
        srcRepo = os.path.join(buildDir, "mozilla")
        _run("git clone --no-checkout --progress -- git://github.com/mozilla/mozilla-central.git \"%s\"" % (srcRepo,))
        _run_in_dir("git fetch --tags", srcRepo)
        tags = _capture_output("git --git-dir=\"%s/.git\" tag -l" % (srcRepo,)).splitlines()
        if config.mozSrcGitRev in tags:
            branch = config.mozSrcGitRev
        elif config.mozSrcGitRev.translate(None, "0123456789") == "":
            from distutils.version import LooseVersion, StrictVersion
            versions = []
            for tag in tags:
                if not (tag.startswith("FIREFOX_") and tag.endswith("_RELEASE")):
                    continue
                version = LooseVersion(".".join(tag.split("_")[1:-1]))
                if version.version[-2] in ("a", "b"):
                    continue # skip alphas and betas
                versions.append(version)
            lastVerMajor = max(versions).version[0]
            targetVer = LooseVersion(".".join(map(str, [int(config.mozVer),
                                                        int(config.mozVer * 10 % 10),
                                                        int(config.mozVer * 100 % 10)])))
            if lastVerMajor >= targetVer.version[0]:
                if not targetVer in versions and targetVer.version[-1] == 0:
                    # try without the last part, for x.0 vs x.0.0
                    targetVer = LooseVersion(targetVer.vstring.rsplit(".", 1)[0])
                if not targetVer in versions:
                    raise BuildError("Can't find version %s" % (config.mozVer,))
                branch = "FIREFOX_%s_RELEASE" % (targetVer.vstring.replace(".", "_"),)
            else:
                for branch in ("beta", "aurora", "master"):
                    milestone = _capture_output("git --git-dir=\"%s/.git\" show "
                                                "origin/%s:config/milestone.txt" %
                                                (srcRepo, branch))
                    for line in milestone.splitlines():
                        if (line.lstrip() + "#").startswith("#"):
                            continue # empty or comment
                        break
                    else:
                        continue
                    version = LooseVersion(line.strip())
                    if version.version[0] == targetVer.version[0]:
                        break
                else:
                    raise BuildError("Can't find branch for %s" % targetVer)
        else:
            raise BuildError("unknown git version \"%s\"" % (config.mozSrcGitRev,))
        _run_in_dir("git checkout %s" % (branch,), srcRepo)

    elif mozSrcType == "tarball":
        _extract_tarball(tarballLocalPath, buildDir)

    else:
        raise BuildError("unknown mozSrcType: %r" % mozSrcType)

    if force_checkout:
        return argv[2:]
    return argv[1:]


__digits = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
def str2int(num, base=10):
    if not num:
        return 0
    else:
        result = ""
        for c in num:
            if c not in __digits[:base]:
                break
            result += c
        return int(result)


def _get_mozilla_objdir(convert_to_native_win_path=False, force_echo_variable=False):
    config = _importConfig()
    srcdir = os.path.join(config.buildDir, config.srcTreeName, 'mozilla')

    # Get the $OBJDIR. The target for this has changed over time in
    # the moz tree.
    objdir = None
    cmds = [ # one of these command should work
        'make -f client.mk echo-variable-OBJDIR',
        'make -f client.mk echo_objdir',
    ]
    if sys.platform.startswith("win"):
        cmds.insert(0, 'mozmake -f client.mk echo-variable-OBJDIR')
    old_cwd = os.getcwd()
    os.chdir(srcdir)
    try:
        for cmd in cmds:
            try:
                output = _capture_output(cmd)
                objdir = output.splitlines(0)[0].strip()
            except OSError:
                pass  # try the next command
            else:
                if objdir:
                    break
        else:
            raise BuildError("could not determine $OBJDIR using client.mk")
    finally:
        os.chdir(old_cwd)

    if convert_to_native_win_path and sys.platform == "win32" and objdir.startswith("/"):
        # Expected output example:
        #   /c/trentm/as/Mozilla-devel/build/cvs1.8-ko4.11-play/mozilla/ko-rel-ns
        # Convert that to something sane.
        #   C:\trentm\as\Mozilla-devel\build\...
        objdir = objdir[1:]
        objdir = objdir[0].upper() + ':' + objdir[1:].replace('/', '\\')

    return objdir

    
def _msys_path_from_path(path):
    if not sys.platform.startswith("win"):
        return path
    drive, subpath = os.path.splitdrive(path)
    msys_path = "/%s%s" % (drive[0].lower(),
                           subpath.replace('\\', '/'))
    return msys_path


def _unix_path_from_path(path):
    """Convert a path to unix-compatible (i.e. forward-slash) path."""
    return path.replace(os.sep, "/")


def _get_exe_path(cmd):
    """Get an appropriate full path to the named command.
    
    Some names are handle specially to point to special versions.
    """
    if cmd == "autoconf-2.13":
        if sys.platform == "win32":
            return join(os.environ["MOZILLABUILD"], "msys", "local", "bin",
                        "autoconf-2.13")
        else:
            return abspath(join("support", "autoconf-2.13", "bin",
                                "autoconf"))
    else:
        return which.which(cmd)

def _get_make_command(config, srcDir):
    """Get the command to use for make

    Returns a mozmake command line on Windows, and make elsewhere
    """
    if sys.platform.startswith("win") :
        return "mozmake"
    return "make"

def target_configure_mozilla(argv=["configure_mozilla"]):
    """configure the patched mozilla source tree"""
    log.info("target: configure_mozilla")
    global gAutoConfPath
    config = _importConfig()
    buildDir = os.path.join(config.buildDir, config.srcTreeName, "mozilla")
    
    # Bail if source isn't there.
    landmark = os.path.join(buildDir, "client.mk")
    if not os.path.exists(landmark):
        raise BuildError("There is no mozilla source at '%s'. (landmark='%s')"\
                         % (buildDir, landmark))

    # get the moz version
    extensions = config.mozBuildExtensions
    config.mozconfig += "ac_add_options --enable-extensions=%s\n"\
                           % ','.join(extensions)
    # Copy in .mozconfig and set MOZCONFIG.
    mozconfig = os.path.join(buildDir, ".mozconfig")
    log.info("create '%s' and point MOZCONFIG to it", mozconfig)
    fout = open(mozconfig, 'w')
    fout.write(config.mozconfig)
    fout.close()
    os.environ["MOZCONFIG"] = os.path.abspath(mozconfig)
    
    _setupMozillaEnv()

    autoconf_path = _get_exe_path("autoconf-2.13")
    if sys.platform == "win32":
        cmd = "sh -c %s" % _msys_path_from_path(autoconf_path)
    else:
        cmd = autoconf_path
    _run_in_dir(cmd, buildDir, log.info)

    # Clean out the configure cache.
    configCache = os.path.join(buildDir, "config.cache")
    if os.path.exists(configCache):
        log.info("rm %s", configCache)
        os.remove(configCache)

    # Add komodo build dir to .hgignore file.
    hgignore_filepath = join(buildDir, ".hgignore")
    contents = file(hgignore_filepath).read()
    entry = "^" + config.mozObjDir + "/*"
    file(hgignore_filepath, "w").write(contents + "\n" + entry + "\n")

    return argv[1:]

def target_mozilla(argv=["mozilla"]):
    """build the given patched mozilla source tree
    
    Usage:
        build mozilla [<subdir>]

    You can give a mozilla subdirectory in which to limit the build. For
    example:
        build mozilla xpfe\\bootstrap
    """
    log.info("target: mozilla")
    config = _importConfig()
    _setupMozillaEnv()
    buildDir = os.path.join(config.buildDir, config.srcTreeName, "mozilla")
    native_objdir = _get_mozilla_objdir(convert_to_native_win_path=True)

    # Bail if source isn't there.
    landmark = os.path.join(buildDir, "client.mk")
    if not os.path.exists(landmark):
        raise BuildError("There is no mozilla source at '%s'. (landmark='%s')"\
                         % (buildDir, landmark))

    _validatePython(config)

    if len(argv) > 1 and os.path.isdir(os.path.join(native_objdir, argv[1])):
        # Build in a specific mozilla subdirectory.
        targetDir = os.path.join(native_objdir, argv[1])
        _run_in_dir(_get_make_command(config, buildDir), targetDir, log.info)
        argv = argv[2:]

    else:
        # New enough to use mach
        # Make sure mach has the state directory working
        try:
            _run_in_dir("python mach mach-commands", buildDir, log.info)
        except OSError:
            pass # mach errors out on first run, that's okay

        # do the build
        build_args = ""

        # XXX: Mozilla PGO builds require a huge amount of memory, so we've
        #      disabled the mozilla PGO building for now.
        #if config.withPGOGeneration:
        #    build_args = "MOZ_PROFILE_GENERATE=1 MOZ_PGO_INSTRUMENTED=1"
        #elif config.withPGOCollection:
        #    build_args = "MOZ_PROFILE_USE=1"
        #
        #_run_in_dir("python mach --log-file %s configure %s" %
        #                (join(buildDir, "mach.log"), build_args),
        #            buildDir, log.info)
        _run_in_dir("python mach --log-file %s build %s" %
                        (join(buildDir, "mach.log"), build_args),
                    buildDir, log.info)

    if int(config.mozVer) >= 35 and sys.platform.startswith("darwin"):
        # Copy 'dependentlibs.list' into the Resources directory.
        distDir = join(config.buildDir, config.srcTreeName, "mozilla",
                       config.mozObjDir, "dist")
        komodo_app_name = "Komodo%s" % (config.buildType == 'debug'
                                        and 'debug' or '')
        binDepPath = join(distDir, "%s.app" % komodo_app_name, "Contents", "MacOS", "dependentlibs.list")
        resDepPath = join(distDir, "%s.app" % komodo_app_name, "Contents", "Resources", "dependentlibs.list")
        if exists(binDepPath):
            shutil.move(binDepPath, resDepPath)

        argv = argv[1:]
    return argv

def target_symbols(argv=["symbols"]):
    """collect the crash reporter symbols"""
    config = _importConfig()
    if config.withCrashReportSymbols:
        log.info("target: symbols")
        native_objdir = _get_mozilla_objdir(convert_to_native_win_path=True)
        topsrcdir = os.path.join(config.buildDir, config.srcTreeName, "mozilla")
        _run_in_dir("%s buildsymbols" % (_get_make_command(config, topsrcdir),),
                    native_objdir, log.info)
    return argv[1:]

def target_komodoapp_distclean(argv=["komodoapp_distclean"]):
    """remove the komodo bits"""
    config = _importConfig()
    buildDir = os.path.join(config.buildDir, config.srcTreeName, "mozilla")
    native_objdir = _get_mozilla_objdir(convert_to_native_win_path=True)
    paths = [
        join(buildDir, "komodo", "app"),
        join(buildDir, "komodo", "config"),
        join(native_objdir, "komodo", "app"),
    ]
    for path in paths:
        if exists(path):
            shutil.rmtree(path)
    return argv[1:]

def target_komodoapp(argv=["komodoapp"]):
    """add the komodo bits and build them"""
    config = _importConfig()
    target_patch(patch_target='komodoapp', logFilename="__patchlog_komodoapp__.py")
    topsrcdir = os.path.join(config.buildDir, config.srcTreeName, "mozilla")
    log.info("building komodo app")
    _run_in_dir("python mach --log-file %s build komodo" % (join(buildDir, "mach.log")),
                topsrcdir, log.info)
    return argv[1:]

def target_mbsdiff(argv=["mozilla"]):
    """Build mbsdiff module needed for building update .mar packages."""
    config = _importConfig()
    if not config.enableMar:
        return
    _setupMozillaEnv()
    native_objdir = _get_mozilla_objdir(convert_to_native_win_path=True)
    builddir = os.path.join(native_objdir, 'modules', 'libbz2')
    topsrcdir = os.path.join(config.buildDir, config.srcTreeName, "mozilla")
    log.info("entering directory '%s' (to build libbz2 separately)",
             builddir)
    _run_in_dir(_get_make_command(config, topsrcdir), builddir, log.info)

    bsdiffDir = os.path.join(native_objdir, 'other-licenses', 'bsdiff')
    log.info("entering directory '%s' (to build mbsdiff separately)",
             bsdiffDir)
    _run_in_dir(_get_make_command(config, topsrcdir), bsdiffDir, log.info)
    return argv[1:]

def target_libmar(argv=["mozilla"]):
    """Build libmar module needed for building update .mar packages."""
    config = _importConfig()
    if not config.enableMar:
        return
    _setupMozillaEnv()
    native_objdir = _get_mozilla_objdir(convert_to_native_win_path=True)
    libmar_dir = os.path.join(native_objdir, 'modules', 'libmar')
    topsrcdir = os.path.join(config.buildDir, config.srcTreeName, "mozilla")
    log.info("entering directory '%s' (to build libmar separately)",
             libmar_dir)
    _run_in_dir(_get_make_command(config, topsrcdir), libmar_dir, log.info)
    return argv[1:]


def target_all(argv):
    """get the source, patch it, and build mozilla"""
    log.info("target: all")
    target_src()
    target_src_pyxpcom()
    target_patch()
    target_patch_pyxpcom()
    target_patch_komodo()
    target_configure_mozilla()
    target_mozilla()
    target_pyxpcom()
    target_silo_python()
    target_regmozbuild()
    return argv[1:]


def target_patch(argv=["patch"], patch_target="mozilla", logFilename=None,
                 srcSubDir=None):
    """patch the mozilla source"""
    config = _importConfig()
    log.info("target: patch %s from %r",
             patch_target, config.patchesDirs)

    srcDir = join(config.buildDir, config.srcTreeName, "mozilla")
    if srcSubDir is not None:
        srcDir = join(srcDir, srcSubDir)
    logDir = join(config.buildDir, config.srcTreeName,
                  "mozilla-patches-%s" % config.srcTreeName, patch_target)

    # Use our local patch, if we have one.
    # - on Windows the cygwin patch can do screwy things
    # - on Solaris /usr/bin/patch isn't good enough (note that we
    #   usually *do* have GNU patch at /usr/local/bin/patch).
    # - on Windows 7 we must use our own patch.exe, otherwise the OS may block
    #   the patch application thinking it requires security priviledges.
    binDir = gPlat2BinDir[sys.platform]
    try:
        patchExe = which.which("patch", path=[binDir])
    except which.WhichError:
        try:
            patchExe = which.which("patch")
        except which.WhichError:
            raise BuildError("Could not find a 'patch' executable.")

    patchtree.log.setLevel(logging.INFO)
    # Temporarily add a patch target, which we'll remove when done patching.
    config.patch_target = patch_target
    try:
        patchtree.patch(config.patchesDirs,
                        srcDir,
                        config=config,
                        #dryRun=1,  # uncomment this line to dry-run patching
                        logDir=logDir,
                        patchExe=patchExe,
                        logFilename=logFilename)
    finally:
        del config.patch_target

    return argv[1:]

def target_patch_komodo(argv=["patch_komodo"]):
    """Patch Mozilla sources with Komodo parts (for startup)"""
    target_patch(patch_target='komodoapp', logFilename="__patchlog_komodoapp__.py")
    return argv[1:]

def target_packages(argv=["packages"]):
    """create required packages for this Mozilla build"""
    log.info("target: packages")
    target_package_patches()
    return argv[1:]


def target_package_patches(argv=["package_patches"]):
    """zip up the patches used for this build"""
    log.info("target: package_patches")
    config = _importConfig()
    if not exists(gPackagesDir):
        os.makedirs(gPackagesDir)

    buildDir = join(config.buildDir, config.srcTreeName)
    patchesDir = "mozilla-patches-%s" % config.srcTreeName
    packagePath = join(gPackagesDir,
                       "%s-%s.zip" % (patchesDir, config.platform))
    if exists(packagePath):
        os.remove(packagePath)
    _run_in_dir("zip -qr %s %s" % (abspath(packagePath), patchesDir),
                buildDir,
                log.info)
    log.info("created patches package: `%s'", packagePath)

    return argv[1:]


def target_upload(argv=["upload"]):
    """Upload built packages to network share area.
    
    These will be used later as a release package for Komodo builds.
    """
    log.info("target: upload")
    config = _importConfig()

    packages = {
        "patches": "mozilla-patches-%s-%s.zip"
                   % (config.srcTreeName, config.platform),
    }
    for name, filename in packages.items():
        src = join(gPackagesDir, filename)
        if not exists(src):
            log.warn("could not upload %s package: `%s' does not exist",
                     name, src)
            continue
        dst = "komodo@mule:/data/komodo/extras/mozilla-build-patches/" + filename
        remote_cp(src, dst, log.info)

    return argv[1:]


def target_distclean(argv):
    """remove the configured mozilla tree (src and objdir)"""
    log.info("target: distclean")
    config = _importConfig()
    buildDir = os.path.join(config.buildDir, config.srcTreeName)
    if os.path.exists(buildDir):
        log.info("removing '%s'...", buildDir)
        if sys.platform == "win32":
            cmd = "rd /s/q "+buildDir
        else:
            cmd = "rm -rf "+buildDir
        retval = os.system(cmd)
        if retval:
            raise BuildError("error running: '%s'" % cmd)
    return argv[1:]


def target_clean(argv):
    """remove the configured mozilla obj dir (i.e. the build products)"""
    log.info("target: clean")
    config = _importConfig()

    objDir = join(config.buildDir, config.srcTreeName, "mozilla",
                  config.mozObjDir)
    if exists(objDir):
        log.info("rm `%s'", objDir)
        if sys.platform == "win32":
            _run("rd /s/q "+  objDir)
        else:
            _run("rm -rf "+objDir)

    return argv[1:]


#---- internal support routines
#TODO: move support routines from above here

def _splitall(path):
    r"""Return list of all split directory parts.

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


def _relpath(path, relto=None):
    """Return a relative path of the given path.

    "relto" indicates a directory to which to make "path" relative.
        It default to the cwd if not specified.
    """
    if not os.path.isabs(path):
        path = os.path.abspath(path)
    if relto is None:
        relto = os.getcwd()
    else:
        relto = os.path.abspath(relto)

    if sys.platform.startswith("win"):
        def _equal(a, b): return a.lower() == b.lower()
    else:
        def _equal(a, b): return a == b

    pathDrive, pathRemainder = os.path.splitdrive(path)
    if not pathDrive:
        pathDrive = os.path.splitdrive(os.getcwd())[0]
    relToDrive, relToRemainder = os.path.splitdrive(relto)
    if not _equal(pathDrive, relToDrive):
        # Which is better: raise an exception or return ""?
        return ""
        #raise OSError("Cannot make '%s' relative to '%s'. They are on "\
        #              "different drives." % (path, relto))

    pathParts = _splitall(pathRemainder)[1:] # drop the leading root dir
    relToParts = _splitall(relToRemainder)[1:] # drop the leading root dir
    #print "_relpath: pathPaths=%s" % pathParts
    #print "_relpath: relToPaths=%s" % relToParts
    for pathPart, relToPart in zip(pathParts, relToParts):
        if _equal(pathPart, relToPart):
            # drop the leading common dirs
            del pathParts[0]
            del relToParts[0]
    #print "_relpath: pathParts=%s" % pathParts
    #print "_relpath: relToParts=%s" % relToParts
    # Relative path: walk up from "relto" dir and walk down "path".
    relParts = [os.curdir] + [os.pardir]*len(relToParts) + pathParts
    #print "_relpath: relParts=%s" % relParts
    relPath = os.path.normpath( os.path.join(*relParts) )
    return relPath



#---- some remote file utils

def _capture_output(cmd, capture_stderr=False):
    if capture_stderr:
        stderr = subprocess.STDOUT
    else:
        stderr = None
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=stderr, shell=True)
    output = p.stdout.read()
    retval = p.returncode
    if retval:
        raise OSError("error capturing output of `%s': %r" % (cmd, retval))
    return output

def _capture_status(argv):
    try:
        p = subprocess.Popen(argv, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
        stdout = p.stdout.read()
        status = p.wait()
        return status
    except:
        # WindowsError: [Error 2] The system cannot find the file specified
        return -1

_remote_path_re = re.compile("(\w+@)?\w+:/(?!/)")
def is_remote_path(rpath):
    return _remote_path_re.search(rpath) is not None

def remote_exists(rpath, log=None):
    login, path = rpath.split(':', 1)
    if sys.platform == "win32":
        argv = ["plink", "-batch", login, "ls", path]
    else:
        argv = ["ssh", "-o", "BatchMode=yes", login, "ls", path]
    if log:
        log(' '.join(argv))
    status = _capture_status(argv)
    return status == 0

def remote_mkdir(rpath):
    login, path = rpath.split(':', 1)
    if sys.platform == "win32":
        cmd = "plink -batch %s mkdir %s" % (login, path)
    else:
        cmd = "ssh -o BatchMode=yes %s mkdir %s" % (login, path)
    status = _run(cmd)

def remote_cp(src, dst, log=None):
    if sys.platform == "win32":
        cmd = "pscp %s %s" % (src, dst)
    else:
        cmd = "scp -B %s %s" % (src, dst)
    if log:
        log(cmd)
    status = _run(cmd)

def remote_run(login, cmd, log=None):
    if sys.platform == "win32":
        cmd = 'plink -batch %s "%s"' % (login, cmd)
    else:
        cmd = 'ssh -o BatchMode=yes %s "%s"' % (login, cmd)
    if log:
        log(cmd)
    status = _run(cmd)


#---- mainline

def build(argv):
    while argv:
        # Determine the target method to run.
        target = argv[0]
        try:
            targetFunc = getattr(sys.modules[__name__], 'target_' + target)
        except AttributeError, e:
            log.error("no '%s' (function target_%s()) target exists"\
                      % (target, target))
            return 1

        # Run the target.
        try:
            newArgv = targetFunc(argv)
        except BuildError, ex:
            log.error("%s: %s", target, str(ex))
            if log.isEnabledFor(logging.DEBUG):
                print
                import traceback
                traceback.print_exception(*sys.exc_info())
            return 1

        # Do some sanity checking on argv.
        if not isinstance(newArgv, (tuple, list)):
            raise BuildError("Illegal return value from target '%s': %r. "\
                             "A target must return an argv sequence."\
                             % (target, newArgv))
        if len(newArgv) >= len(argv):
            raise BuildError("Illegal return value from target '%s': %r. "\
                             "The argv vector is not smaller than the one"\
                             "passed in: %r." % (target, newArgv, argv))
        argv = newArgv


def _helpOnTargets(targets):
    """Print help for the given targets."""
    for target in targets:
        try:
            targetFunc = getattr(sys.modules[__name__], 'target_' + target)
        except AttributeError, e:
            log.error("no '%s' (function target_%s()) target exists"\
                      % (target, target))
            return 1
        doc = targetFunc.__doc__
        if doc:
            print target+" -- "+doc
        else:
            print "No help for target '%s'." % target


def _listTargets():
    """Dump a table listing all targets in the module.

    A "target" is a method named target_*.
    """
    docmap = {}
    for target, attr in sys.modules[__name__].__dict__.items():
        if target[:7] == 'target_':
            if attr.__doc__:
                doc = attr.__doc__
            else:
                doc = ''
            docmap[target[7:]] = doc
    targets = docmap.keys()

    # Sort the targets into groups
    groupMap = { # mapping of group regex to group order and title
        "^(distclean|configure|all|packages|upload)$": (0, "Primary targets"),
        "^(clean|mozilla)$": (1, "Targets for re-building the current mozilla"),
        "^package_": (2, "Targets to create build packages"),
        None: (3, "Other targets"),
    }
    grouped = {
        # <group title>: [<member targets>...]
    }
    for target in targets:
        for pattern, (order, title) in groupMap.items():
            if pattern and re.search(pattern, target):
                if title in grouped:
                    grouped[title].append(target)
                else:
                    grouped[title] = [target]
                break
        else:
            title = "Other targets"
            if title in grouped:
                grouped[title].append(target)
            else:
                grouped[title] = [target]
    for memberList in grouped.values(): memberList.sort()
    groups = []
    titles = groupMap.values()
    titles.sort()

    print "                    Mozilla-devel BUILD TARGETS"
    print "                    ==========================="
    for order, title in titles:
        if title not in grouped: continue
        print '\n' + title + ':'
        #XXX long form output
        #for target in grouped[title]:
        #    print "  %-20s" % target
        #    doc = docmap[target]
        #    if doc:
        #        print "    "+doc
        #    if "\n" not in doc:
        #        print
        for target in grouped[title]:
            doc = docmap[target]
            if doc:
                doc = doc.splitlines()[0]
            if len(doc) > 53:
                doc = doc[:50] + "..."
            print "  %-20s  %s" % (target, doc)


# Recipe: pretty_logging (0.1) in C:\trentm\tm\recipes\cookbook
class _PerLevelFormatter(logging.Formatter):
    """Allow multiple format string -- depending on the log level.
    
    A "fmtFromLevel" optional arg is added to the constructor. It can be
    a dictionary mapping a log record level to a format string. The
    usual "fmt" argument acts as the default.
    """
    def __init__(self, fmt=None, datefmt=None, fmtFromLevel=None):
        logging.Formatter.__init__(self, fmt, datefmt)
        if fmtFromLevel is None:
            self.fmtFromLevel = {}
        else:
            self.fmtFromLevel = fmtFromLevel
    def format(self, record):
        record.levelname = record.levelname.lower()
        if record.levelno in self.fmtFromLevel:
            #XXX This is a non-threadsafe HACK. Really the base Formatter
            #    class should provide a hook accessor for the _fmt
            #    attribute. *Could* add a lock guard here (overkill?).
            _saved_fmt = self._fmt
            self._fmt = self.fmtFromLevel[record.levelno]
            try:
                return logging.Formatter.format(self, record)
            finally:
                self._fmt = _saved_fmt
        else:
            return logging.Formatter.format(self, record)

def _setup_logging():
    hdlr = logging.StreamHandler()
    defaultFmt = "%(name)s: %(levelname)s: %(message)s"
    infoFmt = "%(message)s"
    fmtr = _PerLevelFormatter(fmt=defaultFmt,
                              fmtFromLevel={logging.INFO: infoFmt})
    hdlr.setFormatter(fmtr)
    logging.root.addHandler(hdlr)


def main(argv):
    _setup_logging()
    log.setLevel(logging.INFO)

    # Process options.
    try:
        optlist, args = getopt.getopt(argv[1:], "htvf:c:",
            ["help", "targets", "verbose", "config"])
    except getopt.GetoptError, msg:
        log.error(str(msg))
        log.error("Your invocation was: %s. Try 'build --help'.\n" % argv)
        return 1

    for opt, optarg in optlist:
        if opt in ("-h", "--help"):
            if args:
                _helpOnTargets(args)
            else:
                sys.stdout.write(__doc__)
            return 0
        elif opt in ("-t", "--targets"):
            return _listTargets()
        elif opt in ("-v", "--verbose"):
            log.setLevel(logging.DEBUG)
        elif opt in ("-f", "-c", "--config"):
            global gConfigFileName
            gConfigFileName = optarg

    # Process arguments.
    if len(args) == 0:
        log.warn("no targets given")
        return 0

    _validateEnv()
    return build(args)


if __name__ == "__main__":
    sys.exit( main(sys.argv) )


