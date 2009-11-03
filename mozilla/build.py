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

    For CVS tag dates, see:
        http://developer.mozilla.org/en/docs/CVS_Tags

    Suggested convention for Komodo version numbers:
    * For development builds you should add 10 to the minor version
      number:
        Komodo Edit 5.2.x development:    -k 5.12
        Komodo IDE 5.2.x development:     -k 5.12
      This allows you to run a production and development build at the
      same time without them trying to hand off to each other.
    
    Suggested configurations are:
    * Komodo 5.2.x development builds:
        python build.py configure -k 5.12 --moz-src=cvs \
            --release --no-strip --tools
    * Komodo 6.0 development builds:
        python build.py configure -k 6.10 --moz-src=192 \
            --release --no-strip --tools
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
import string
import types
import logging

sys.path.insert(0, join(dirname(__file__), "..", "util"))
import which
import process
import preprocess
import platinfo
import patchtree
import sh
del sys.path[0]


#---- exceptions

class BuildError(Exception):
    pass

#---- library code used by komodo bk configure

def _getLinuxDistro():
    assert sys.platform.startswith("linux")
    # It would be nice to keep this in sync with
    #   ../Komodo-devel/bklocal.py::LinuxDistribution._getDistroName()
    redhatRelease = "/etc/redhat-release"
    debianVersion = "/etc/debian_version"
    suseRelease = "/etc/SuSE-release"
    if os.path.exists(redhatRelease):
        content = open(redhatRelease).read()
        pattern = re.compile("^Red Hat Linux release ([\d\.]+)")
        fedoraPattern = re.compile("^Fedora Core release ([\d\.]+)")
        match = pattern.search(content)
        fedoraMatch = fedoraPattern.search(content)
        if match:
            ver = match.group(1).split('.')[0]
            return "redhat"+ver
        elif fedoraMatch:
            ver = fedoraMatch.group(1).split('.')[0]
            return "fedoracore"+ver
        else:            
            raise BuildError(
                "Could not determine RedHat release from first "
                "line of '%s': '%s'" % (redhatRelease, content))
    elif os.path.exists(debianVersion):
        content = open(debianVersion).read()
        return content.strip().replace('.', '')
    elif os.path.exists(suseRelease):
        content = open(suseRelease).read()
        pattern = re.compile("^SuSE Linux ([\d\.]+)")
        match = pattern.search(content)
        if match:
            ver = match.group(1).split('.')[0]
            return "suse"+ver
        else:
            raise BuildError(
                "Could not determine SuSE release from first "
                "line of '%s': '%s'" % (suseRelease, content))
    else:
        raise BuildError("unknown Linux distro")


def _getValidPlatforms():
    """Return a list of platforms for which Mozilla can be built from
    the current machine.
    """
    validPlats = []
    if sys.platform == "win32":
        validPlats = ["win32-ix86"]
    elif sys.platform.startswith("linux"):
        uname = os.uname()
        if uname[4] == "ia64":
            validPlats = []
        elif re.match("i\d86", uname[4]):
            distro = _getLinuxDistro()
            validPlats = ["linux-%s-ix86" % distro]
        else:
            raise BuildError("unknown Linux architecture: '%s'" % uname[4])
    elif sys.platform.startswith("sunos"):
        #XXX Note that we don't really support Solaris builds yet.
        uname = os.uname()
        if uname[4].startswith("sun4"):
            if uname[2] == "5.6":
                validPlats = ["solaris-sparc"]
            elif uname[2] == "5.8":
                validPlats = ["solaris8-sparc", "solaris8-sparc64"]
            else:
                raise BuildError("unknown Solaris version: '%s'" % uname[2])
        else:
            raise BuildError("unknown Solaris architecture: '%s'" % uname[4])
    elif sys.platform == "darwin":
        validPlats = ['macosx-powerpc', 'macosx-x86']
    elif sys.platform.startswith("freebsd"):
        arch = os.uname()[-1]
        if re.match("i\d86", arch):
            validPlats = ['freebsd-x86']
        else:
            raise BuildError("unknown FreeBSD architecture: '%s'" % uname[4])
    return validPlats


def _getDefaultPlatform():
    """Return an appropriate default target platform for the current machine.
    
    A "platform" is a string of the form "<os>-<arch>".
    """
    try:
        return _getValidPlatforms()[0]
    except IndexError, ex:
        raise BuildError("cannot build mozilla on this platform: '%s'"
                         % sys.platform)

def _updateMd5sums(newfilename):
    """Add (or update) an entry to the MD5SUMS file for the given file.
    
    The MD5SUMS file is in the package dir and has an entry for each
    released package:
        <hexdigest> <filename>
    """
    md5sums = os.path.join(gPackagesDir, "MD5SUMS")
    
    md5sumsDict = {}
    if os.path.exists(md5sums):  # get the existing entries
        fin = open(md5sums, 'r')
        for line in fin.readlines():
            if not line.strip(): continue
            hexdigest, filename = line.strip().split(None, 1)
            md5sumsDict[filename] = hexdigest
        fin.close()
    elif not os.path.isdir(gPackagesDir):
        os.makedirs(gPackagesDir)
    
    # Determine hexdigest for the new file.
    import md5
    md5obj = md5.new()
    md5obj.update( open(newfilename, 'r').read() )
    md5sumsDict[ os.path.basename(newfilename) ] = md5obj.hexdigest()

    # Write out the new MD5SUMS file
    fout = open(md5sums, 'w')
    for filename, hexdigest in md5sumsDict.items():
        fout.write("%s %s\n" % (hexdigest, filename))
    fout.close()

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
        changenum = int(re.match("(\d+)", changestr).group(1))
        log.warn("simplifying complex changenum from 'svnversion': %s -> %s"
                 " (see `svnversion --help` for details)",
                 changestr, changenum)
    return changenum



#---- global data

log = logging.getLogger("build")

# The target platform for which Python is being built, e.g. "win32-ix86".
gPlatform = None  

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

# These extensions are now standard in moz 1.9, so remove them from
# config.
moz18Only = ['xmlextras', 'pref', 'universalchardet', 'webservices',
             'transformiix']


#---- directory structure globals

gBuildDir = "build"
gPackagesDir = "packages"
gMozSrcRepositories = [
    os.curdir, "crimper:/home/apps/Komodo/support/mozilla-source"]



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
            if not nsinstall_path.startswith(mozilla_build_dir):
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


def _determineMozCoProject(mozApp):
    if mozApp == "komodo":
        return "xulrunner"
    names = [ s.strip() for s in mozApp.split(",") ]
    if "xulrunner" not in names:
        names.append("xulrunner")
    return ",".join(names)

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
    os.environ["MOZ_CURRENT_PROJECT"] \
        = os.environ["MOZ_CO_PROJECT"] = _determineMozCoProject(config.mozApp)
    
    # ensure the mozilla build system uses our python to build with
    if config.python:
        os.environ["PYTHON"] = config.python
        if sys.platform == 'darwin':
            python_so = dirname(dirname(config.python))
            if 'DYLD_LIBRARY_PATH' in os.environ:
                ld_path =  ':%s' % os.environ['DYLD_LIBRARY_PATH']
            else:
                ld_path = ''
            os.environ["DYLD_LIBRARY_PATH"] = "%s%s" % (python_so, ld_path)
        elif sys.platform.startswith('linux'):
            python_so_dir = join(dirname(dirname(config.python)), "lib")
            ld_paths = [python_so_dir]
            if 'LD_LIBRARY_PATH' in os.environ:
                ld_paths.append(os.environ['LD_LIBRARY_PATH'])
            os.environ["LD_LIBRARY_PATH"] = os.path.pathsep.join(ld_paths)
    
    if sys.platform != "win32":
        #TODO: drop what isn't necessary here
        
        #set MOZ_SRC=/export/home/jeffh/p4/Mozilla-devel/build/moz...
        binDir = join(gBuildDir, config.srcTreeName, "mozilla",
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

        # The Python Framework is used on OSX
        if sys.platform == "darwin":
            return


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
    p = process.ProcessOpen(argv, cwd=cwd)
    p.stdin.write( open(patchFile, 'r').read() )
    p.stdin.close()
    p.stdout.close() # sometimes patch will hang if we don't close stdout
    retval = p.wait()
    if not retval: # i.e. reverse patch would apply
        log.info("Patch '%s' was already applied. Skipping.", patchFile)
        return

    # Fail if the patch would not apply cleanly.
    argv = baseArgv + ["--dry-run"] 
    log.debug("see if patch will apply cleanly: run %s in '%s'", argv, cwd)
    p = process.ProcessOpen(argv, cwd=cwd)
    p.stdin.write( open(patchFile, 'r').read() )
    p.stdin.close()
    retval = p.wait()
    if retval:
        stdout = p.stdout.read()
        stderr = p.stderr.read()
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
    p = process.ProcessOpen(argv, cwd=cwd)
    p.stdin.write( open(patchFile, 'r').read() )
    p.stdin.close()
    sys.stdout.write( p.stdout.read() )
    sys.stdout.flush()
    retval = p.wait()
    if retval:
        raise BuildError("Error applying patch '%s': argv=%r, cwd=%r"\
                         "retval=%r" % (patchFile, argv, cwd, retval))

def _cygpathFromWinPath(path):
    assert sys.platform == "win32"
    if not os.path.isabs(path):
        path = os.path.abspath(path)
    drive, tail = os.path.splitdrive(path)
    path = "/cygdrive/%s%s"\
           % (drive.strip(':').lower(), tail.replace(os.sep, '/'))
    return path

def _getMozSrcInfo(scheme, mozApp):
    """Return information about how to get the Mozilla source to use for
    building.
    
        "scheme" defines what mozilla source to use. This is the same as
            what was specified by the 'configure' target's --moz-src=
            option. It can have the following forms:
                cvs[:TAG[:DATE]]
                    Grab the source directly from Mozilla CVS. E.g.
                        cvs      # the latest CVS head
                        cvs:MOZILLA_1_8_BRANCH
                        cvs:1.8  # shortcut for 'MOZILLA_<ver>_BRANCH'
                        cvs:1.8:02/14/2006  # Valentine's Day 2006
                        cvs:HEAD:02/14/2006  # Valentine's Day 2006
                    See tinderbox.mozilla.org for hints on Mozilla CVS
                    tags.
                <path-to-tarball>
                    A path to a mozilla/firefox source tarball to use
                    for the source.
                <ver>
                    A version string indicating a specific
                    mozilla/firefox source tarball package. E.g.:
                         mozilla-<ver>-source.tar.gz
                         firefox-<ver>-source.tar.gz
        "mozApp" is one of komodo, xulrunner, suite, browser to indicate
            (sort of) which source package or CVS branch to look for.
            This is HACKy and hopefully this subtlety can be removed.
    
    The return value is a dict with the suggested configuration
    variables identifying the mozilla source.
        {'mozSrcType':      <'cvs' or 'tarball'>,
         'mozSrcName':      <an short string to *loosely* describing the
                             mozilla src>,
         # The following only if mozSrcType==cvs:
         'mozSrcCvsTag':    <None for HEAD, otherwise a Mozilla CVS tag name>,
         'mozSrcCvsDate':   <None or a date string that CVS understands>,
         'mozSrcCvsTarball':<path to a Mozilla CVS tarball with a
                             *baseline* source tree or None>,
         # The following only if mozSrcType==tarball:
         'mozSrcTarball':   <path to a Mozilla source tarball>,
        }
    """
    config = {}

    if scheme.startswith("cvs"): # cvs[:TAG[:DATE]]
        config["mozSrcType"] = "cvs"
        config["mozVer"] = 1.90

        if scheme.count(":") == 0:      # cvs
            config.update(
                mozSrcCvsTag=None,
                mozSrcCvsDate=None,
            )
        elif scheme.count(":") == 1:    # cvs:TAG
            tag_hint = scheme.split(":", 1)[1]
            config.update(
                mozSrcCvsTag=_moz_cvs_tag_from_tag_hint(tag_hint),
                mozSrcCvsDate=None,
            )
        else:                           # cvs:TAG:DATE
            _, tag_hint, date_spec = scheme.split(":", 2)
            config.update(
                mozSrcCvsTag=_moz_cvs_tag_from_tag_hint(tag_hint),
                mozSrcCvsDate=date_spec,
            )

        # Determine a nice short name loosely describing this CVS
        # source.
        tag = config["mozSrcCvsTag"]
        if tag is None:
            config["mozSrcName"] = "cvs"
        else:
            # If the tag name matches MOZILLA_<ver>_BRANCH (e.g.
            # MOZILLA_1_8_BRANCH) then use the ver.
            match = re.search(r"MOZILLA_(?P<ver>(\d+_?)+)_BRANCH", tag)
            if match:
                ver = match.group("ver").replace("_", ".")
                config["mozSrcName"] = "cvs"+ver
                if ver == "1_8":
                    config["mozSrcVer"] = 1.8
            else:
                config["mozSrcName"] = "cvs_"+tag

        config["mozSrcCvsTarball"] = None

    elif scheme.endswith(".tar.gz") or scheme.endswith(".tar.bz2"):
        suffix = scheme.endswith(".tar.gz") and ".tar.gz" or ".tar.bz2"
        if not isfile(scheme):
            raise BuildError("Configured mozilla source tarball, '%s', "\
                             "does not exist." % scheme)
        config.update(
            mozSrcType="tarball",
            mozSrcTarball=scheme,
        )

        if mozApp == "suite":
            patterns = [re.compile("^mozilla(?:-source)?-(.*?)(?:-source)?%s$"
                                 % re.escape(suffix))]
        elif mozApp in ("komodo", "browser"):
            patterns = [re.compile("^firefox-(.*?)-source%s$"
                                 % re.escape(suffix)),
                        re.compile("^xulrunner-(.*?)-source%s$"
                                 % re.escape(suffix))]
        else:
            raise BuildError("do we use the 'firefox-*-source.tar.gz' "
                             "tarballs for mozApp='%s' builds?" % mozApp)
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
                if scheme_basename.startswith("firefox"):
                    config["mozVer"] = { 3.0: 1.90,
                                         3.1: 1.91,
                                         3.5: 1.91,
                                         3.6: 1.92,
                                         3.7: 1.93,
                                        }.get(version_num)
                else:
                    config["mozVer"] = version_num
                break
        else:
            config["mozSrcName"] = name
            
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

    else:
        if mozApp == "suite":
            candidates = ["mozilla-source-%s.tar.bz2" % scheme,
                          "mozilla-source-%s.tar.gz" % scheme,
                          "mozilla-%s-source.tar.bz2" % scheme,
                          "mozilla-%s-source.tar.gz" % scheme]
        elif mozApp in ("komodo", "browser"):
            candidates = ["firefox-%s-source.tar.bz2" % scheme,
                          "firefox-%s-source.tar.gz" % scheme]
        else:
            raise BuildError("do we use the 'firefox-*-source.tar.gz' "
                             "tarballs for mozApp='%s' builds?" % mozApp)
        log.info("looking for %r in src repositories" % candidates)
        for repo, candidate in [(r,c) for r in gMozSrcRepositories
                                      for c in candidates]:
            if isdir(repo):
                tarball = os.path.join(repo, candidate)
                if os.path.isfile(tarball):
                    config["mozSrcTarball"] = tarball
                    break
            elif is_remote_path(repo):
                tarball = repo + '/' + candidate
                if remote_exists(tarball, log=log.debug):
                    config["mozSrcTarball"] = tarball
                    break
        else:
            raise BuildError("Could not find mozilla/firefox '%s' source "
                             "in any of the source repositories: %s"
                             % (scheme, gMozSrcRepositories))
        config.update(
            mozSrcType="tarball",
            mozSrcTarball=tarball,
            mozSrcName=scheme,
        )

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
                cvs[:TAG[:DATE]]
                    Grab the source directly from Mozilla CVS. E.g.
                        cvs      # the latest CVS head
                        cvs:MOZILLA_1_8_BRANCH
                        cvs:1.8  # shortcut for 'MOZILLA_<ver>_BRANCH'
                        cvs:1.8:02/14/2006  # Valentine's Day 2006
                    See tinderbox.mozilla.org for hints on Mozilla CVS
                    tags.
                <path-to-tarball>
                    A path to a mozilla/firefox source tarball to use
                    for the source.
                ver[:TAG]
                    A version string indicating a specific
                    mozilla/firefox version - the repository or tarball will be
                    automatically worked out by the build system.
            
            This table might help you pick a relevant scheme and tag.

            Scheme      Tag                     KoVer   FFVer   MozVer
            ----------  ----------------------  ------  ------  ----------
            cvs:1.8.0   MOZILLA_1_8_0_BRANCH    3.5.X   1.5.X   1.80
            cvs:1.8.1   MOZILLA_1_8_BRANCH      4.X     2.0     1.81
            cvs:1.8     MOZILLA_1_8_BRANCH      4.X     2.X     1.81
            cvs         HEAD                    5.X     3.0.X   1.90
            191         FIREFOX_3_5_3_RELEASE   5.3.X   3.5.3   1.91
            192                                 6.0.X   3.6.X   1.92

    Other Options:
        -r, --reconfigure
            Re-run configuration with the previous config options.

        --komodo (the default)
        --xulrunner
        --suite (i.e. the Mozilla suite)
        --browser (i.e. Firefox)
        --moz-app=<komodo|xulrunner|suite|browser>
            Which moz-application to build? The stub komodo app (in prep
            for full Komodo builds), xulrunner, Firefox (a.k.a. the
            browser) or the Mozilla suite?  This is called the "mozApp".

        --debug, --release, --symbols
            specify mozilla build-type (default: release)

        --universal
            create a macosx universal mozilla build

        --strip, --no-strip
            Whether to strip libraries after the build. By default
            stripping *is* done.

        --g4, --no-g4
            (Mac OS X only) Build optimized, or not, for Altivec/7400 G4
            Processors. By default this optimization is turned on for
            release builds.

        -P <pyver>, --python-version=<pyver>
            Specify the version of the local prebuilt Python to build with
            and siloed into this Mozilla build. By default the latest
            version is used (currently 2.5). 

        --python=<path>
            Instead of -P|--python-version you may use this option to
            specify a full path to a Python executable to use. No guarantees
            that this is going to work, though.

        --gtk, --gtk2
            Build for GTK version 1 or 2. The default on Linux and
            Solaris is for GTK 2. (These options really only make sense
            on Linux and Solaris.)

        --no-mar
            Do not build the bsdiff and mar modules.

        --xft
        --xinerama
        --perf      build with timeline and profiling support
        --tools     build with venkman, inspector and cview
        --jssh      extract and build JS Telnet Server to rebuild with a
                    new version of jssh, you must remove
                    mozilla/extensions/jssh and add a new jssh.zip to
                    Mozilla-devel/modules.  jssh is at
                    http://www.croczilla.com/jssh

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

        --official
            build a clean unpatched mozilla or firefox
            (Note: I don't trust that this is what you get. --TM)

        --compiler=<vc6|vc7|vc8>  # Windows-only
            There is *some* support for building Mozilla/Firefox with
            the non-default compiler on Windows. Currently we build with
            VC6 and this is the default. We have done some investigation
            with building with vc7 (mainly because Python 2.4 builds
            with VC7) but have backed off because of various problems.

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
        "buildDir": os.path.abspath(gBuildDir),
        "mozconfig": None,
        "mozApp": "komodo",
        "jsStandalone": False,
        "mozSrcScheme": BuildError("don't have a mozilla source scheme: "
                                   "use '--moz-src'"),
        "official": False,      # i.e. a plain Mozilla/Firefox build w/o Komodo stuff
        "stripBuild": True,
        "compiler": None, # Windows-only; 'vc6' (the default) or 'vc7', 'vc8'
        "mozObjDir": None,
        "universal": False,
        "patchesDirs": ["patches-new"],
    }
    if sys.platform.startswith("linux") or sys.platform.startswith("sunos"):
        config["buildOpt"].append("gtk2")
    mozBuildOptions = [
       'enable-canvas',
       'enable-svg',
       # stuff we don't want in komodo
       'disable-ldap',
       'disable-composer',
       'disable-installer',
       'disable-activex',
       'disable-activex-scripting',
       # prevents a "C++ compiler has -pedantic long long bug" configure error
       'disable-pedantic',
       # i'd like to be doing these
       # 'enable-plaintext-editor-only',
       # 'enable-single-profile',
       'disable-oji',

       # suggested by http://www.mozilla.org/build/distribution.html
       'without-system-nspr',
       'without-system-zlib',
       'without-system-jpeg',
       'without-system-png',
       'without-system-mng',
       
       'enable-updater',
    ]
    mozMakeOptions = []
    mozBuildExtensions = []
    mozRawOptions = []
       
    # Process options.
    try:
        optlist, remainder = getopt.getopt(argv[1:], "rk:P:",
            ["reconfigure",
             "debug", "release", "symbols",
             "komodo-version=", "python=", "python-version=",
             "moz-src=",
             "blessed", "universal",
             "komodo", "xulrunner", "suite", "browser", "moz-app=",
             "strip", "no-strip",
             "g4", "no-g4",
             "gtk2", "gtk",
             "no-mar",
             "with-tests", "without-tests", 
             "perf", "tools", "xft", "xinerama", "jssh", "js",
             "options=", "extensions=", "moz-config=",
             "src-tree-name=",
             "build-name=",  # this is deprecated, use --src-tree-name
             "build-tag=",
             "official",
             "p4-changenum=",
             "compiler=", "moz-objdir="])
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
            config["universal"] = True
        elif opt == "--komodo":
            config["mozApp"] = "komodo"
        elif opt == "--xulrunner":
            config["mozApp"] = "xulrunner"
        elif opt == "--suite":
            config["mozApp"] = "suite"
        elif opt == "--browser":
            config["mozApp"] = "browser"
        elif opt == "--moz-app":
            config["mozApp"] = optarg
        elif opt == "--js":
            config["jsStandalone"] = True
        elif opt == "--official":
            config["official"] = True
            config["komodoVersion"] = None
        elif opt == "--gtk":
            config["buildOpt"].append("gtk")
            if "gtk2" in config["buildOpt"]:
                config["buildOpt"].remove("gtk2")
        elif opt == "--no-mar":
            config["enableMar"] = False
        elif opt == "--xft":
            config["buildOpt"].append("xft")
        elif opt == "--xinerama":
            config["buildOpt"].append("xinerama")
        elif opt == "--gtk2":
            if "gtk2" not in config["buildOpt"]:
                config["buildOpt"].append("gtk2")
            if "gtk" in config["buildOpt"]:
                config["buildOpt"].remove("gtk")
        elif opt == "--jssh":
            config["buildOpt"].append("jssh")
            mozBuildExtensions.append('jssh')
            mozBuildExtensions.append('webservices')
        elif opt == "--perf":
            config["buildOpt"].append("perf")
        elif opt == "--tools":
            config["buildOpt"].append("tools")
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
        elif opt == "--with-tests":
            config["withTests"] = True
        elif opt == "--without-tests":
            config["withTests"] = False
        elif opt == "--strip":
            config["stripBuild"] = True
        elif opt == "--no-strip":
            config["stripBuild"] = False
            config["buildOpt"].append("ns")
        elif opt == "--g4":
            if os.uname()[-1] != 'i386':
                config["optimizeForG4"] = True
        elif opt == "--no-g4":
            config["optimizeForG4"] = False
        elif opt == "--compiler":
            assert sys.platform == "win32", \
                "'--compiler' configure option is only supported on Windows"
            validCompilers = ('vc6', 'vc7', 'vc8')
            assert optarg in validCompilers, \
                "invalid compiler value (%s), must be one of: %s"\
                % (optarg, validCompilers)
            config["compiler"] = optarg
        elif opt == "--moz-objdir":
            config["mozObjDir"] = optarg

    # Ensure all require information was specified.
    for name, value in config.items():
        if isinstance(value, Exception):
            raise value
    assert config["mozApp"] in ("komodo", "xulrunner", "suite", "browser")

    # Now determine the rest of the configuration items given the user
    # options.

    config.update(
        _getMozSrcInfo(config["mozSrcScheme"], config["mozApp"])
    )

    # Finish determining the configuration: some defaults depend on user
    # settings.
    buildType = config["buildType"] # shorthand
    if sys.platform == "darwin":
        if "optimizeForG4" not in config:
            config["optimizeForG4"] = (pi.arch != "x86"
                                       and buildType == "release")
        elif buildType == "release" and not config["optimizeForG4"]:
            config["buildOpt"].append("nog4opt")
        # See http://developer.mozilla.org/en/docs/Mac_OS_X_Build_Prerequisites#.mozconfig_Options_and_Other_Tunables
        # for issues with setting:
        #   ac_add_options --with-macos-sdk=/path/to/SDK
        #   ac_add_options --enable-macos-target=version
        #
        # building on panther, we must now specify --with-macos-sdk= due to
        # changes in quicktime (yes, it affects us).  So, for any ppc build,
        # we will use the 10.2.8 sdk
        # If building on panther, we do not want to use with-macos-sdk,
        # it is broken.

        osx_major_ver = int(os.uname()[2].split(".")[0])
        # The osx_major_ver has the following values:
        #   10: Snow Leopard (OS X 10.6)
        #   9:  Leopard (OS X 10.5)
        #   8:  Tiger (OS X 10.4)

        mozVer = config["mozVer"]
        sdk_ver = None
        if mozVer >= 1.92:
            sdk_ver = "10.5"
        elif pi.arch == "x86":
            sdk_ver = "10.4"
        else:
            sdk_ver = "10.3"

        if not sdk_ver:
            raise BuildError("You cannot build Mozilla without a platform "
                             "sdk installed. Install Xcode 1.5 and be sure "
                             "to select the 'Cross-Platform SDKs' option in "
                             "the installer.")
        sdk = "/Developer/SDKs/MacOSX%s.sdk" % ({"10.3": "10.3.9",
                                                 "10.4": "10.4u"}.get(sdk_ver, sdk_ver))
        if not os.path.exists("%s/Library" % sdk):
            raise BuildError("You must symlink %s/Library to /Library:\n"
                             "\tsudo ln -s /Library %s/Library"
                             % (sdk, sdk))
        if not os.path.exists("%s/Library/Frameworks/Python.framework" % sdk):
            #TODO: Is *Active*Python actually required here? if not just say "Python".
            raise BuildError("ActivePython is not installed to "
                             "'/Library/Frameworks'.")
    
        mozBuildOptions.append("enable-macos-target=%s" % sdk_ver)
        mozBuildOptions.append("with-macos-sdk=%s" % sdk)

        if osx_major_ver >= 10:
            # Komodo needs to be built as a 32-bit application.
            # Snow Leopard specific build details from:
            #   https://developer.mozilla.org/en/Mac_OS_X_Build_Prerequisites
            mozBuildOptions.append("target=i386-apple-darwin8.0.0")
            mozRawOptions.append('RANLIB=ranlib')
            mozRawOptions.append('AR=ar')
            mozRawOptions.append('AS=$CC')
            mozRawOptions.append('LD=ld')
            mozRawOptions.append('STRIP="strip -x -S"')
            mozRawOptions.append('CROSS_COMPILE=1')
            # Crash reporter won't build either.
            mozBuildOptions.append('disable-crashreporter')
            if mozVer <= 1.91:
                # Mozilla <= 1.9.1 must use gcc 4.0, specify that now.
                mozRawOptions.append('CC="gcc-4.0 -arch i386"')
                mozRawOptions.append('CXX="g++-4.0 -arch i386"')
                mozRawOptions.append('HOST_CC="gcc-4.0 -arch i386"')
                mozRawOptions.append('HOST_CXX="g++-4.0 -arch i386"')
            else:
                # Mozilla 1.9.2 must use gcc 4.2, specify that now.
                mozRawOptions.append('CC="gcc-4.2 -arch i386"')
                mozRawOptions.append('CXX="g++-4.2 -arch i386"')
                mozRawOptions.append('HOST_CC="gcc-4.2 -arch i386"')
                mozRawOptions.append('HOST_CXX="g++-4.2 -arch i386"')
        if mozVer >= 1.91:
            mozRawOptions.append("mk_add_options AUTOCONF=autoconf213")

    config["changenum"] = _getChangeNum()
    if sys.platform == "win32":
        if config["mozSrcScheme"].startswith("cvs:1.8"):
            defaultWinCompiler = "vc6"
        else:
            defaultWinCompiler = "vc8"
        if not config["compiler"]:
            config["compiler"] = defaultWinCompiler
        if config["compiler"] != defaultWinCompiler:
            config["buildOpt"].append(config["compiler"])

    if config["python"] is None:
        if config["pythonVersion"] is None:
            config["pythonVersion"] = "2.6"
        if config["pythonVersion"] in ("2.5", "2.6"):
            config["pyVer"] = config["pythonVersion"]
            # New Python 2.5 builds.
            if sys.platform == "win32":
                buildName = config["platform"] + '-' + config["compiler"]
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
    if sys.platform == "darwin":
        if buildType == "debug" and config["optimizeForG4"]:
            raise BuildError("cannot optmize for G4 (--g4) in a debug "
                             "build (--debug)")
    if config["buildTag"] is not None and config["srcTreeName"] is not None:
        raise BuildError("cannot use both --src-tree-name and "
                         "--build-tag options")

    # Determine the build tree name (encodes src tree config), moz
    # objdir (encodes build config), and full build name (for the packages)
    # unless specifically given.
    shortBuildType = {"release": "rel", "debug": "dbg", "symbols": "sym"}[buildType]
    shortMozApp = {"komodo": "ko", "xulrunner": "xulr",
                   "suite": "ste", "browser": "ff"}[config["mozApp"]]
    buildOpts = config["buildOpt"][:]
    buildOpts.sort()
    if config["official"]:
        srcTreeNameBits = [config["mozSrcName"]]
        config["patchesDirs"] = ["patches-official"]
    else:
        srcTreeNameBits = [config["mozSrcName"], "ko"+config["komodoVersion"]]
    mozObjDirBits = [shortMozApp, shortBuildType] + buildOpts
    if config["buildTag"]:
        srcTreeNameBits.append(config["buildTag"])
    if config["srcTreeName"] is None:
        config["srcTreeName"] = '-'.join(srcTreeNameBits)
    if config["mozObjDir"] is None:
        config["mozObjDir"] = '-'.join(mozObjDirBits)

    # Add any patches dirs, if necessary.
    if "jssh" in config["buildOpt"]:
        jsshDir = join(gBuildDir, config["srcTreeName"], "mozilla",
                       "extensions", "jssh")
        config["patchesDirs"].append(jsshDir)

    # Determine the exact mozilla build configuration (i.e. the content
    # of '.mozconfig') -- unless specifically given.
    mozVer = config["mozVer"]
    if config["mozconfig"] is None:
        if not config["official"]:
            if mozVer is None or mozVer >= 1.9:
                # help viewer was removed from normal builds, enable it for Komodo
                mozBuildOptions.append("enable-help-viewer")
                # Pyxpcom is no longer a part of the Mozilla 1.9.2+ sources.
                if mozVer < 1.92:
                    mozBuildExtensions.append('python')
            else:
                mozBuildExtensions.append('python/xpcom')

        if "withTests" not in config:
            mozBuildOptions.append("disable-tests")
        elif not config["withTests"]:
            mozBuildOptions.append("disable-tests")

        if buildType == "release":
            if sys.platform.startswith("linux"):
                mozBuildOptions.append('enable-optimize=-O2') # default -O

            if sys.platform == 'darwin':
                if config["optimizeForG4"]:
                    mozBuildOptions.append('enable-optimize="-Os -faltivec -mcpu=7400 -mtune=7400 -mpowerpc -mpowerpc-gfxopt"') # default -O
                else:
                    # moz.org uses -O2 with gcc
                    mozBuildOptions.append('enable-optimize=-O2') # default -O
            else:
                # -O2 buggy, moz.org does not use -O2
                mozBuildOptions.append('enable-optimize')
            mozBuildOptions.append('disable-debug')
            mozBuildOptions.append('disable-dtd-debug')
        elif buildType == "debug":
            mozBuildOptions.append('enable-debug')
            mozBuildOptions.append('disable-optimize')
        elif buildType == "symbols":
            if sys.platform == "win32":
                mozRawOptions.append('export MOZ_DEBUG_SYMBOLS=1')
                mozBuildOptions.append('enable-debugger-info-modules=yes')
            elif sys.platform == "darwin":
                if mozVer >= 1.91:
                    mozRawOptions.append('CFLAGS="-gdwarf-2"')
                    mozRawOptions.append('CXXFLAGS="-gdwarf-2"')
                else:
                    mozRawOptions.append('CFLAGS="-g -gfull"')
                    mozRawOptions.append('CXXFLAGS="-g -gfull"')
            elif sys.platform.startswith("linux"):
                mozRawOptions.append('CFLAGS="-gstabs+"')
                mozRawOptions.append('CXXFLAGS="-gstabs+"')

        if "perf" in config["buildOpt"]:
            mozBuildOptions.append('enable-xpctools')
            mozBuildOptions.append('enable-timeline')
            
        if "tools" in config["buildOpt"]:
            # some extensions that may help us in
            # development
            if mozVer < 1.91:
                mozBuildExtensions.append('venkman')
                mozBuildExtensions.append('inspector')
                mozBuildExtensions.append('cview')
        
        if config["mozApp"] in ("browser", "komodo"):
            # based on build options from the standard firefox distro, there
            # are likely changes we will want to make
            mozBuildOptions.append('disable-mailnews')
            mozBuildOptions.append('disable-composer')

            # Needed for building update-service packages.
            mozBuildOptions.append('enable-update-packaging')
            
            # XXX not sure if we want to do this, need to understand the options
            mozBuildOptions.append('enable-single-profile')
            mozBuildOptions.append('disable-profilesharing')
            
            # these extensions are built into firefox, we need to figure out
            # what we dont want or need.
            mozBuildExtensions.append('cookie')
            if mozVer < 1.91:
                mozBuildExtensions.append('xml-rpc')
                mozBuildExtensions.append('inspector')
            
            mozBuildExtensions.append('spellcheck')
            #mozBuildExtensions.append('typeaheadfind')
            
            # XXX these fail, but we probably dont care
            #mozBuildExtensions.append('gnomevfs')
            #mozBuildExtensions.append('negotiateauth')
            
            # XXX necessary to complete the build for now...need to find the
            # dependency so we dont build with them
            mozBuildOptions.append('enable-xsl')
            
            # in 1.9, these are no longer extensions, and need to be removed
            mozBuildExtensions.append('xmlextras')
            mozBuildExtensions.append('pref')
            mozBuildExtensions.append('universalchardet')
            mozBuildExtensions.append('webservices')
            mozBuildExtensions.append('transformiix')

        elif config["mozApp"] == "xulrunner":
            mozBuildOptions.append('enable-application=xulrunner')
        else:
            # needed for print preview, see change 67368
            # (XXX Cruft? --TM)
            mozBuildOptions.append('enable-mailnews') 

        mozMakeOptions.append('MOZ_OBJDIR=@TOPSRCDIR@/%s' % config["mozObjDir"])
            
        if "gtk" in config["buildOpt"]:
            mozBuildOptions.append('enable-default-toolkit=gtk')
        elif "gtk2" in config["buildOpt"]:
            # Note: "mozVer" can be None
            if mozVer is None or mozVer >= 1.9:
                # Assume at least mozilla 1.9 then, use cairo gtk builds.
                mozBuildOptions.append('enable-default-toolkit=cairo-gtk2')
            else:
                # A pre 1.9 mozilla source
                mozBuildOptions.append('enable-default-toolkit=gtk2')

            mozBuildOptions.append('enable-xft')
        if "xft" in config["buildOpt"]:
            mozBuildOptions.append('enable-xft')
        if "xinerama" in config["buildOpt"]:
            mozBuildOptions.append('enable-xinerama')
        
        # Platform options
        if sys.platform.startswith("sunos"):
            mozMakeOptions.append('MOZ_MAKE_FLAGS=-j2')
            mozBuildOptions.append('disable-gnomevfs')
            mozBuildOptions.append('disable-gnomeui')
        if sys.platform == 'darwin':
            mozMakeOptions.append('MOZ_MAKE_FLAGS=-j2')
            mozBuildOptions.append('enable-prebinding')

        config["mozconfig"] = "# Options for 'configure' (same as command-line options).\n"
        
        # osx universal builds
        if sys.platform == 'darwin' and config["universal"]:
            config["mozconfig"] += ". $topsrcdir/build/macosx/universal/mozconfig\n"

        if config["mozApp"] == "komodo":
            mozBuildOptions.append('enable-application=komodo')

        #TODO: This is being overridden by PYTHON being set in the
        #      environment for building in _setupMozillaEnv(). Probably
        #      best to remove the other and keep this one.
        if "python/xpcom" in mozBuildExtensions or "python/dom" in mozBuildExtensions \
            or "python" in mozBuildExtensions:
            if "python/dom" in mozBuildExtensions:
                mozBuildExtensions.append("python")
                mozBuildExtensions.remove("python/dom")
                mozBuildExtensions.remove("python/xpcom")
            if sys.platform == "win32":
                python = _msys_path_from_path(config["python"])
            else:
                python = config["python"]
            config["mozconfig"] += "PYTHON=%s\nexport PYTHON\n" % python

        if config["stripBuild"]:
            mozBuildOptions.append('enable-strip')
            mozBuildOptions.append('enable-strip-libs')

        for opt in mozMakeOptions:
            config["mozconfig"] += "mk_add_options %s\n" % opt

        for opt in mozRawOptions:
            config["mozconfig"] += "%s\n" % opt

        for opt in mozBuildOptions:
            config["mozconfig"] += "ac_add_options --%s\n" % opt
    
        config["mozBuildExtensions"] = mozBuildExtensions

        if sys.platform.startswith("linux"):
            # http://benjamin.smedbergs.us/blog/2005-10-27/gcc-40-workaround/
            # https://bugs.launchpad.net/ubuntu/+source/firefox/+bug/102518
            config["mozconfig"] += "ac_cv_visibility_pragma=no\n"

    # Error out if it looks like we will hit the subtle limitation on
    # PATH length on Windows.
    if sys.platform == "win32":
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
        mozObjPathGuess = os.path.join(os.path.abspath(gBuildDir),
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
**************************************************************************
""" % (PATH_LEN_LIMIT,
       LONGEST_SUB_PATH, len(LONGEST_SUB_PATH),
       PATH_LEN_LIMIT - len(LONGEST_SUB_PATH),
       mozObjPathGuess, len(mozObjPathGuess),
       config["srcTreeName"], len(config["srcTreeName"]),
       mozObjDirGuess, len(mozObjDirGuess),
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


def _get_js_standalone(buildDir):
    cvsroot = ":pserver:anonymous@cvs-mirror.mozilla.org:/cvsroot"
    jsconfig = os.path.join(buildDir, "mozilla", "js", "src", "config")
    if not os.path.exists(jsconfig):
        # check it out now
        cmd = "cd %s && cvs -d %s co mozilla/js/src/config"\
              % (buildDir, cvsroot)
        log.info(cmd)
        retval = os.system(cmd)
        if retval:
            raise BuildError("error running '%s'" % cmd)
    jsconfig = os.path.join(buildDir, "mozilla", "js", "src", "editline")
    if not os.path.exists(jsconfig):
        # check it out now
        cmd = "cd %s && cvs -d %s co mozilla/js/src/editline"\
              % (buildDir, cvsroot)
        log.info(cmd)
        retval = os.system(cmd)
        if retval:
            raise BuildError("error running '%s'" % cmd)


def target_silo_python(argv=["silo_python"]):
    log.info("target: silo_python")
    config = _importConfig()
    pyver = tuple(map(int, config.pyVer.split('.')))
    distDir = join(gBuildDir, config.srcTreeName, "mozilla",
                   config.mozObjDir, "dist")
    if sys.platform == "darwin":
        # The siloed Python framework goes in the app's "Frameworks"
        # dir.
        komodo_app_name = "Komodo%s" % (config.buildType == 'debug'
                                        and 'debug' or '')
        frameworks_subpath_from_mozApp = {
            "komodo": ["%s.app" % komodo_app_name, "Contents", "Frameworks"],
            "browser": ["Firefox.app", "Contents", "Frameworks"],
            "xulrunner": ["XUL.framework", "Frameworks"],
            "suite": ["SeaMonkey.app", "Contents", "Frameworks"],
        }
        siloDir = join(distDir, *frameworks_subpath_from_mozApp[config.mozApp])
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

    # Abort if it looks like it has already be siloed.
    if sys.platform == "win32":
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
        log.info("siloed Python already exists at `%s'", siloDir)
        return argv[1:]

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
        _run("copy /y %s %s" % (join(siloDir, "python.exe"),
                                join(mozBinDir, "mozpython.exe")))

    elif sys.platform == "darwin":
        src = join(srcDir, "Python.framework")
        dst = join(siloDir, "Python.framework")
        _run("mkdir -p %s" % dirname(dst))
        _run('cp -R %s %s' % (src, dst))

        # Note: Currently don't think the relocation is necessary on Mac OS X.
        #
        ## Relocate the Python install.
        #if pyver >= (2,5): # when APy's activestate.py supported relocation
        #    activestate_py_path = join(
        #        dst, "Versions", config.pyVer, "lib",
        #        "python"+config.pyVer, "site-packages", "activestate.py")
        #    cmd = "%s %s --relocate" % (sys.executable, activestate_py_path)
        #    _run(cmd, log.info)

        # Tweaks so pyxpcom stuff will work when run from the command line.
        # http://bugs.activestate.com/show_bug.cgi?id=66332
        # (a) move the main Python exe to the Komodo.app dir and
        # (b) call it 'mozpython' to avoid name conflict.
        pythonAppDir = join(siloDir, "Python.framework", "Versions",
                            config.pyVer, "Resources", "Python.app")
        oldPybinPath = join(pythonAppDir, "Contents", "MacOS", "Python")
        newPybinPath = join(dirname(siloDir), "MacOS", "mozpython")
        _run("mv -f %s %s" % (oldPybinPath, newPybinPath), log.info)
        _run("rm -rf %s" % pythonAppDir, log.info)
        # (c) correct the runtime dependency path.
        oldLibDep = "@executable_path/../../../../Python"
        newLibDep = "@executable_path/../Frameworks/Python.framework/Versions/Current/Python"
        _run("chmod +w %s && install_name_tool -change %s %s %s"
             % (newPybinPath, oldLibDep, newLibDep, newPybinPath), log.info)

        # Correct the shared object dependencies to point to the siloed
        # Python.
        log.info("relocating Python lib dependencies to the siloed Python...")
        libnames = ["_xpcom.so", "lib_xpcom.dylib", "libpyloader.dylib"]
        if config.mozVer >= 1.9:
            libnames.append("libpyxpcom.dylib")
            libnames.append("libpydom.dylib")
        libs = []
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
            if old:
                if config.mozApp == "xulrunner":
                    # xulrunner is a framework, so the path layout is
                    # slightly different
                    new = "@executable_path/../../Frameworks/Python.framework/" \
                          "Versions/%s/Python" % config.pyVer
                else:
                    new = "@executable_path/../Frameworks/Python.framework/" \
                          "Versions/%s/Python" % config.pyVer
                cmd = "chmod +w %s && install_name_tool -change %s %s %s"\
                      % (lib, old, new, lib)
                log.info("\t%s", lib)
                _run(cmd)
            else:
                log.error("PyXPCOM was not built correctly!\n%s", ''.join(linkage))

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
        _run('rm -f %s/%s' % (mozBinDir, libpythonSo))
        _run('ln -s %s %s/%s'
             % (libpythonSoVer, mozBinDir, libpythonSo),
             log.info)

        # Need a mozpython executable in the mozBin dir for "bk start mozpython"
        # to work with PyXPCOM -- for testing, etc.
        _run('ln -s ../python/bin/python%s %s/mozpython'
             % (config.pyVer, mozBinDir),
             log.info)

        # Relocate the Python install.
        if pyver >= (2,5): # when APy's activestate.py supported relocation
            activestate_py_path = join(siloDir, "lib", "python"+config.pyVer,
                                       "site-packages", "activestate.py")
            cmd = "%s %s --relocate" % (sys.executable, activestate_py_path)
            _run(cmd, log.info)

    return argv[1:]


def target_pyxpcom(argv=["pyxpcom"]):
    log.info("target: pyxpcom")
    config = _importConfig()
    _setupMozillaEnv()
    if config.mozVer <= 1.91:
        pyxpcom_dir = join(gBuildDir, config.srcTreeName, "mozilla",
                           config.mozObjDir, "extensions", "python",
                           "xpcom")
        cmd = "cd %s && make" % pyxpcom_dir
        log.info(cmd)
        os.system(cmd)
    else:
        # Run the autoconf to generate the configure script.
        cmds = []
        autoconf_command = "autoconf2.13"
        if sys.platform == "win32":
            # Windows uses a different executable name.
            autoconf_command = "autoconf-2.13"
        autoconf_path = _get_exe_path(autoconf_command)
        pyxpcom_src_dir = abspath(join(gBuildDir, config.srcTreeName, "mozilla",
                                       "extensions", "python"))
        if sys.platform == "win32":
            cmds.append("sh -c %s" % _msys_path_from_path(autoconf_path))
        else:
            cmds.append(autoconf_path)
        _run_in_dir(" && ".join(cmds), pyxpcom_src_dir, log.info)

        # Configure and build pyxpcom.
        cmds = []
        moz_obj_dir = abspath(join(gBuildDir, config.srcTreeName, "mozilla",
                                   config.mozObjDir))
        pyxpcom_obj_dir = join(moz_obj_dir, "extensions", "python")
        if not exists(pyxpcom_obj_dir):
            os.makedirs(pyxpcom_obj_dir)
        configure_flags = ''
        if sys.platform.startswith("linux"):
            configure_flags += 'PYTHON="%s"' % (config.python, )
            configure_flags += " ac_cv_visibility_pragma=no"
        elif system.platform == "darwin":
            configure_flags += 'PYTHON="%s"' % (config.python, )
            configure_flags += ' CC="gcc -arch i386" CXX="g++ -arch i386"'
        cmds = ["%s %s --with-libxul-sdk=%s --disable-tests" % (configure_flags, join(pyxpcom_src_dir, "configure"), join(moz_obj_dir, "dist")),
                "make"]
        _run_in_dir(" && ".join(cmds), pyxpcom_obj_dir, log.info)

        # The above pyxpcom build creates a "dist" directory in the
        # "extensions/python" directory, we must copy over the details to the
        # Komodo dist directory.
        if sys.platform.startswith("win"):
            copy_cmd = 'copy %s %s' % (join(pyxpcom_obj_dir, "dist"), join(moz_obj_dir, "dist"))
        else:
            copy_cmd = 'cp -r %s %s' % (join(pyxpcom_obj_dir, "dist"), join(moz_obj_dir))
        _run(copy_cmd, log.info)
    return argv[1:]


def target_src_extra_extensions(argv=["src_extra_extensions"]):
    """Add any extra mozilla extensions in our modules/... dir to
    the current mozilla source (if configured to do so).

    Currently the only extension supported is jssh (--jssh).
    """
    log.info("target: src_extra_extensions")
    config = _importConfig()
    buildDir = os.path.join(gBuildDir, config.srcTreeName)
    extDir = os.path.join(buildDir, 'mozilla', 'extensions')
    
    # jssh
    if 'jssh' in config.buildOpt:
        jsshDir = os.path.join(buildDir, 'mozilla', 'extensions', 'jssh')
        if exists(jsshDir):
            log.info("'jssh' extension already added: `%s' exists", jsshDir)
        else:
            log.info("add 'jssh' extension source to `%s'" % jsshDir)
            _run('unzip -d %s modules/jssh.zip' % extDir, log.info)
            # Note: There is a .patch in this zip to apply to mozilla.
            #       That is handled via the jsshDir having been added to
            #       config.patchesDirs.

    return argv[1:]

def _build_modules(config, buildDir):
    raise "this is a HACK and the patches this sucks, fix it"
    extDir = os.path.join(buildDir, 'mozilla', 'extensions')
    jsshDir = os.path.join(buildDir, 'mozilla', 'extensions', 'jssh')
    if 'jssh' in config.buildOpt and not os.path.exists(jsshDir):
        cmd = 'unzip -d %s modules/jssh.zip' % extDir
        retval = os.system(cmd)
        if retval:
            raise BuildError("error running '%s'" % cmd)
        # copy the patch to the build/patches dir
        jsshPatch = os.path.join(extDir, 'jssh', 'allmakefiles.sh.patch')
        print "cwd is ", os.getcwd()
        if sys.platform.startswith("win"):
            cmd = 'copy %s patches\\jssh-allmakefiles.sh.patch' % jsshPatch
        else:
            cmd = 'cp %s patches/jssh-allmakefiles.sh.patch' % jsshPatch
        print "copy command is ", cmd
        retval = os.system(cmd)
        if retval:
            raise BuildError("error running '%s'" % cmd)

def target_fastupdate(argv=["update"]):
    """update mozilla source from cvs"""
    config = _importConfig()
    if not config.mozSrcType == "cvs":
        raise BuildError("cannot update source from CVS: mozSrcType != 'cvs'")

    # Abort if there is nothing to update.
    buildDir = os.path.join(gBuildDir, config.srcTreeName)
    landmark = os.path.join(buildDir, "mozilla")
    if not os.path.exists(landmark):
        raise BuildError("cannot update: '%s' does not exist (use "
                         "'./build.py src' to checkout)" % landmark)

    # Update.
    os.environ["CVSROOT"] = ":pserver:anonymous@cvs-mirror.mozilla.org:/cvsroot"
    _run("cd %s && make -f mozilla/client.mk fast-update" % buildDir,
         log.info)
    return argv[1:]
    
def target_update(argv=["update"]):
    """update mozilla source from cvs or mercurial"""
    config = _importConfig()
    if not config.mozSrcType not in ("cvs", "hg"):
        raise BuildError("cannot update source: mozSrcType: %r not one of ('cvs', 'hg')")

    # Abort if there is nothing to update.
    buildDir = os.path.join(gBuildDir, config.srcTreeName)
    landmark = os.path.join(buildDir, "mozilla")
    if not os.path.exists(landmark):
        raise BuildError("cannot update: '%s' does not exist (use "
                         "'./build.py src' to checkout)" % landmark)

    # Update.
    if config.mozSrcType == "cvs":
        os.environ["CVSROOT"] = ":pserver:anonymous@cvs-mirror.mozilla.org:/cvsroot"
        _run("cd %s && cvs update && make" % landmark,
             log.info)
    elif config.mozSrcType == "hg":
        _run("cd %s && hg pull -u && make" % landmark,
             log.info)

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
    buildDir = os.path.join(gBuildDir, config.srcTreeName)
    mozSrcType = config.mozSrcType
    
    # Return immediately if source looks like it is already there.
    landmark = os.path.join(buildDir, "mozilla")
    force_checkout = len(argv) > 1 and argv[1] == '-f'
    if not force_checkout and os.path.exists(landmark):
        log.info("it looks like the src already exists: '%s' exists"
                 % landmark)

        # This is a HACK. If we determined that "the src already
        # exists", then we should still be doing work.
        if not config.official:
            _get_js_standalone(buildDir)
        target_src_extra_extensions()

        return argv[1:]
    
    # If there is a tarball to use, then get a local copy of it because:
    # 1. it might be a URL and
    # 2. cygwin tar cannot handle absolute paths
    if config.mozSrcType == "cvs":
        tarballPath = config.mozSrcCvsTarball
    elif config.mozSrcType == "hg":
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

    if mozSrcType == "cvs":
        CVSROOT = ":pserver:anonymous@cvs-mirror.mozilla.org:/cvsroot"
        log.info("set CVSROOT=%s", CVSROOT)
        os.environ["CVSROOT"] = CVSROOT

        if tarballLocalPath is not None:
            # Extract tarball then cvs update.
            _extract_tarball(tarballLocalPath, buildDir)
            cvs_up_args = ''
            if config.mozSrcCvsDate is not None:
                cvs_up_args = ' -D "%s"' % config.mozSrcCvsDate
            cmds = ["cd %s" % join(buildDir, "mozilla"),
                    "cvs -f -z3 update %s" % cvs_up_args]
            _run(" && ".join(cmds), log.info)
        else:
            cvs_co_args = _cvs_co_args_from_tag_and_date(
                config.mozSrcCvsTag, config.mozSrcCvsDate)
            mozApp = config.mozApp
            moz_co_config = _determineMozCoProject(mozApp)
            appCfg = config.mozApp
            if mozApp == "komodo":
                appCfg = moz_co_config

            moz_co_date = ''
            if config.mozSrcCvsDate is not None:
                moz_co_date = ' MOZ_CO_DATE="%s"' % config.mozSrcCvsDate

            cmds = ["cd %s" % buildDir,
                    "cvs co %s mozilla/client.mk mozilla/%s/config"
                        % (cvs_co_args, appCfg)]
            _run(" && ".join(cmds), log.info)

            cmds = ["cd %s" % join(buildDir, "mozilla"),
                    #XXX Should we be setting MOZ_CO_PROJECT to *all* of
                    #    these all the time? Why not use the appropriate
                    #    'mozApp' configuration setting?
                    # - "mozilla/other-licenses/bsdiff" is needed to build
                    #   mbsdiff for update packaging.
                    "make -f client.mk checkout "
                        + "MOZ_CO_PROJECT=%s " % moz_co_config
                        + "MOZ_CO_MODULE=mozilla/other-licenses/bsdiff "
                        + moz_co_date]
            _run(" && ".join(cmds), log.info)

    elif mozSrcType == "hg":
        if config.mozVer <= 1.91:
            repo_url = "http://hg.mozilla.org/releases/mozilla-1.9.1/"
        else:
            repo_url = "http://hg.mozilla.org/releases/mozilla-1.9.2/"
        revision_arg = ""
        if config.mozSrcHgTag:
            revision_arg = "--rev=%s" % (config.mozSrcHgTag)
        cmds = ["cd %s" % buildDir,
                "hg clone %s %s mozilla" % (revision_arg, repo_url, )]
        if config.mozVer >= 1.92:
            # Checkout pyxpcom as well.
            cmds += ["cd mozilla/extensions",
                     "hg clone http://hg.mozilla.org/pyxpcom/ python"]
        _run(" && ".join(cmds), log.info)

    elif mozSrcType == "tarball":
        _extract_tarball(tarballLocalPath, buildDir)

    else:
        raise BuildError("unknown mozSrcType: %r" % mozSrcType)

    # Get any extra stuff.
    target_src_extra_extensions()
    _get_js_standalone(buildDir)

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


def _cvs_co_args_from_tag_and_date(tag_name, date_spec):
    co_args = []
    if tag_name:
        co_args.append("-r "+tag_name)
    if date_spec:
        if ' ' in date_spec:
            co_args.append(' -D "%s"' % date_spec)
        else:
            co_args.append(' -D %s' % date_spec)
    return ''.join(co_args)


def _moz_cvs_tag_from_tag_hint(tag_hint):
    """Return an appropriate Mozilla CVS tag name for the given tag hint
    string.
    
    Typically this "tag hint" is the TAG portion in:
        build configure --moz-src=cvs:TAG[:DATE] ...
    """
    # A version string will be mapped to a "MOZILLA_<ver>_BRANCH".
    if re.match(r"(\d+\.?)+$", tag_hint):
        return "MOZILLA_%s_BRANCH" % tag_hint.replace('.', '_')
    elif tag_hint == "HEAD":
        return None
    else:
        return tag_hint

def _get_mozilla_objdir(convert_to_native_win_path=False, force_echo_variable=False):
    config = _importConfig()
    srcdir = os.path.join(gBuildDir, config.srcTreeName, 'mozilla')

    # Get the $OBJDIR. The target for this has changed over time in
    # the moz tree.
    objdir = None
    cmds = [ # one of these command should work
        'make -f client.mk echo-variable-OBJDIR',
        'make -f client.mk echo_objdir',
    ]
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

    if convert_to_native_win_path and sys.platform == "win32":
        # Expected output example:
        #   /c/trentm/as/Mozilla-devel/build/cvs1.8-ko4.11-play/mozilla/ko-rel-ns
        # Convert that to something sane.
        #   C:\trentm\as\Mozilla-devel\build\...
        objdir = objdir[1:]
        objdir = objdir[0].upper() + ':' + objdir[1:].replace('/', '\\')

    return objdir

    
def _msys_path_from_path(path):
    drive, subpath = os.path.splitdrive(path)
    msys_path = "/%s%s" % (drive[0].lower(),
                           subpath.replace('\\', '/'))
    return msys_path


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


def target_configure_mozilla(argv=["configure_mozilla"]):
    """configure the patched mozilla source tree"""
    log.info("target: configure_mozilla")
    global gAutoConfPath
    config = _importConfig()
    buildDir = os.path.join(gBuildDir, config.srcTreeName, "mozilla")
    
    # Bail if source isn't there.
    landmark = os.path.join(buildDir, "client.mk")
    if not os.path.exists(landmark):
        raise BuildError("There is no mozilla source at '%s'. (landmark='%s')"\
                         % (buildDir, landmark))

    # get the moz version
    extensions = config.mozBuildExtensions
    if config.mozVer >= 1.9:
        # XXX FIXME!!!!
        #if sys.platform == "win32":
        #    user_appdir = config.mozApp
        #elif sys.platform == "darwin":
        #    user_appdir = config.mozApp
        #else:
        #    user_appdir = ".%s" % config.mozApp
        #config.mozconfig += "ac_add_options --with-user-appdir=%s\n"\
        #                   % (user_appdir, config.komodoVersion)
        # remove some extensions
        extensions = [e for e in config.mozBuildExtensions if e not in moz18Only]

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
    buildDir = os.path.join(gBuildDir, config.srcTreeName, "mozilla")
    native_objdir = _get_mozilla_objdir(convert_to_native_win_path=True)

    # Bail if source isn't there.
    landmark = os.path.join(buildDir, "client.mk")
    if not os.path.exists(landmark):
        raise BuildError("There is no mozilla source at '%s'. (landmark='%s')"\
                         % (buildDir, landmark))

    _validatePython(config)

    if len(argv) > 1 and os.path.isdir(os.path.join(native_objdir, argv[1])):
        # Build in a specific mozilla subdirectory.
        buildDir = os.path.join(native_objdir, argv[1])
        _run_in_dir("make", buildDir, log.info)
        argv = argv[2:]

    else:
        koDir = os.path.join(native_objdir, 'komodo')

        _run_in_dir("make -f client.mk build", buildDir, log.info)

        if config.mozApp == "komodo":
            # argh, komodo dir does not get entered, call make there seperately
            log.info("entering directory '%s' (to build komodo separately)",
                     koDir)
            _run_in_dir('make', koDir, log.info)
        argv = argv[1:]
    return argv

def target_jsstandalone(argv=["mozilla"]):
    config = _importConfig()
    if config.official and not config.jsStandalone:
        return argv[1:]
    if config.mozVer >= 1.91:
        # Nothing to do - it's already all done.
        return argv[1:]

    # Build the javascript standalone interpreter seperately
    # the standalone makefile doesn't seem to know about some things,
    # we need to set a couple environment variables to get it
    # building release or with msvc
    _setupMozillaEnv()
    buildDir = os.path.join(gBuildDir, config.srcTreeName, "mozilla")
    topDir = os.getcwd()
    native_objdir = _get_mozilla_objdir(convert_to_native_win_path=True)
    unixy_objdir = _get_mozilla_objdir()
    jsDir = os.path.join(topDir, buildDir, 'js', 'src')

    make_env = []
    if config.buildType == 'release':
        make_env.append("BUILD_OPT=1")
    if sys.platform.startswith("win"):
        make_env.append("USE_MSVC=1")
    make_env.append("MOZ_OBJDIR=%s" % unixy_objdir)
    if sys.platform.startswith("darwin") and int(os.uname()[2].split(".")[0]) >= 10:
        # Snow leopard - ensure to use gcc-4.0 to build the standalone js.
        make_env.append('CC="gcc-4.0 -arch i386"')
    log.info("entering directory '%s' (to build js separately)",
             jsDir)
    _run_in_dir('make -f Makefile.ref clean all distbin %s'
                    % ' '.join(make_env),
                jsDir, log.info)
    return argv[1:]

def target_pluginsdk(argv=["mozilla"]):
    # Build the plugin toolkit seperately
    # (Komodo's SciMoz build depends on the plugingate_s.lib from
    # make'ing in $mozObjDir\modules\plugin\tools\sdk\samples\common).
    config = _importConfig()
    _setupMozillaEnv()
    native_objdir = _get_mozilla_objdir(convert_to_native_win_path=True)
    if config.mozVer >= 1.91:
        pluginDir = os.path.join(native_objdir, 'modules', 'plugin', 'sdk')
    else:
        pluginDir = os.path.join(native_objdir, 'modules', 'plugin',
                                 'tools', 'sdk')
    log.info("entering directory '%s' (to build plugin separately)",
             pluginDir)
    _run_in_dir('make', pluginDir, log.info)

    return argv[1:]


def target_mbsdiff(argv=["mozilla"]):
    """Build mbsdiff module needed for building update .mar packages."""
    config = _importConfig()
    if not config.enableMar:
        return
    _setupMozillaEnv()
    native_objdir = _get_mozilla_objdir(convert_to_native_win_path=True)
    builddir = os.path.join(native_objdir, 'modules', 'libbz2')
    log.info("entering directory '%s' (to build libbz2 separately)",
             builddir)
    _run_in_dir('make', builddir, log.info)

    bsdiffDir = os.path.join(native_objdir, 'other-licenses', 'bsdiff')
    log.info("entering directory '%s' (to build mbsdiff separately)",
             bsdiffDir)
    _run_in_dir('make', bsdiffDir, log.info)
    return argv[1:]

def target_libmar(argv=["mozilla"]):
    """Build libmar module needed for building update .mar packages."""
    config = _importConfig()
    if not config.enableMar:
        return
    _setupMozillaEnv()
    native_objdir = _get_mozilla_objdir(convert_to_native_win_path=True)
    libmar_dir = os.path.join(native_objdir, 'modules', 'libmar')
    log.info("entering directory '%s' (to build libmar separately)",
             libmar_dir)
    _run_in_dir('make', libmar_dir, log.info)
    return argv[1:]


def target_js(argv):
    """build the standalone javascript interpreter"""
    target_jsstandalone()


def target_all(argv):
    """get the source, patch it, and build mozilla"""
    log.info("target: all")
    target_src()
    target_patch()
    target_configure_mozilla()
    target_mozilla()
    target_jsstandalone()
    target_pluginsdk()
    target_mbsdiff()
    target_libmar()
    target_pyxpcom()
    target_silo_python()
    target_regmozbuild()
    return argv[1:]


def target_patch(argv=["patch"]):
    """patch the mozilla source"""
    config = _importConfig()
    log.info("target: patch from %r" %config.patchesDirs)

    srcDir = join("build", config.srcTreeName, "mozilla")
    logDir = join("build", config.srcTreeName,
                  "mozilla-patches-%s" % config.srcTreeName)

    # Use our local patch, if we have one.
    # - on Windows the cygwin patch can do screwy things
    # - on Solaris /usr/bin/patch isn't good enough (note that we
    #   usually *do* have GNU patch at /usr/local/bin/patch).
    if sys.platform == "win32":
        #TODO: Let's try the msys patch. If this works then just remove
        #      bin-win32/patch.exe to use it.
        patchExe = join(os.environ["MOZILLABUILD"], "msys", "bin",
                        "patch.exe")
    else:
        binDir = gPlat2BinDir[sys.platform]
        try:
            patchExe = which.which("patch", path=[binDir])
        except which.WhichError:
            try:
                patchExe = which.which("patch")
            except which.WhichError:
                raise BuildError("Could not find a 'patch' executable.")

    patchtree.log.setLevel(logging.INFO)
    patchtree.patch(config.patchesDirs,
                    srcDir,
                    config=config,
                    #dryRun=1,  # uncomment this line to dry-run patching
                    logDir=logDir,
                    patchExe=patchExe)
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

    buildDir = join("build", config.srcTreeName)
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
        dst = "komodo-build@nas:/data/komodo/extras/mozilla-build-patches/" + filename
        remote_cp(src, dst, log.info)

    return argv[1:]


def target_distclean(argv):
    """remove the configured mozilla tree (src and objdir)"""
    log.info("target: distclean")
    config = _importConfig()
    buildDir = os.path.join(gBuildDir, config.srcTreeName)
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

    objDir = join(gBuildDir, config.srcTreeName, "mozilla",
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

def _capture_output(cmd):
    o = os.popen(cmd)
    output = o.read()
    retval = o.close()
    if retval:
        raise OSError("error capturing output of `%s': %r" % (cmd, retval))
    return output

def _capture_output(cmd):
    o = os.popen(cmd)
    output = o.read()
    retval = o.close()
    if retval:
        raise OSError("error capturing output of `%s': %r" % (cmd, retval))
    return output

def _capture_status(argv):
    try:
        import subprocess
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


