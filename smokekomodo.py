#!/usr/bin/env python
# Copyright (c) 2003-2007 ActiveState Software Inc.
# See License.txt for license details.

r"""
    Make Komodo installer builds.

    Usage:
        python smokekomodo.py [<options>...]

    Common Options:
        -h, --help          print this help and exit
        -V, --version       print the current version and exit
        -v, --verbose       verbose output

        -p, --product-type=<type>
                            What kind of Komodo product to build. Valid
                            values are: "edit", "ide" (the default).

    Other Options:
        -r, --rev=<rev>     Revision number at which to start build Komodo.
                            This may also be a revision list/range, e.g.:
                                123-125,129
                            (Defaults to the latest revision.)

        --moz-build=<scheme>
            Specify what mozilla build to use. Can be:
              latest    use the latest local build (in Mozilla-devel/...)
              <config>  path to the config file for a particular build
                        in Mozilla-devel
              <dir>     path to a particular mozsrc dir to use
                        (Note that this may change to requiring a path
                        to a particular moz *obj* dir.)

        --config-opts=<config-opts>
            An extra string to pass to the "bk configure" command.
"""

class Error(Exception):
    pass


import os
from os.path import join, isfile, isdir, exists, dirname, basename
import sys
import pprint
import getopt
import time
import re
import glob
import shutil
import threading

sys.path.insert(0, "util")
try:
    import p4lib # get it from http://trentm.com/projects/px/
    import which # get it from http://trentm.com/projects/which/
finally:
    del sys.path[0]

try:
    import logging
except ImportError, ex:
    raise Error(str(ex)+". This script requires the 'logging' "
        "Python module. This module will be standard in Python 2.3, but "
        "until then you can get the logging package from here: "
        "http://www.red-dove.com/python_logging.html#download")

sys.path.insert(0, "util")
import sh
import platinfo
del sys.path[0]



#---- globals

gP4Base = "//depot/main/Apps/Komodo-devel"
gP4Tree = gP4Base+"/..."

_version_ = (0, 3, 0)
log = logging.getLogger("smokekomodo")

gWrkDir = "t-smoke"         # Temp working directory.
gDevBuildsDir = "crimper:/home/apps/Komodo/DevBuilds"


#---- internal support stuff

def _getLinuxDistro():
    assert sys.platform.startswith("linux")
    # It would be nice to keep this in sync with
    #   ../Komodo-*/bklocal.py::LinuxDistribution._getDistroName()
    redhatRelease = "/etc/redhat-release"
    debianVersion = "/etc/debian_version"
    suseRelease = "/etc/SuSE-release"
    if os.path.exists(redhatRelease):
        content = open(redhatRelease).read()
        pattern = re.compile("^Red Hat Linux release ([\d\.]+)")
        match = pattern.search(content)
        if match:
            ver = match.group(1).split('.')[0]
            return "redhat"+ver
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


# Recipe: indent (0.2.1) in C:\trentm\tm\recipes\cookbook
def _indent(s, width=4, skip_first_line=False):
    """_indent(s, [width=4]) -> 's' indented by 'width' spaces

    The optional "skip_first_line" argument is a boolean (default False)
    indicating if the first line should NOT be indented.
    """
    lines = s.splitlines(1)
    indentstr = ' '*width
    if skip_first_line:
        return indentstr.join(lines)
    else:
        return indentstr + indentstr.join(lines)


def _getKomodoVersionTuple():
    """Return a tuple representing the version of the Komodo that this
    build will be for.

    Must get this directly from Perforce because the local copy might be
    changed.
    """
    versionTxts = []
    #XXX Would be nice to automatically determine the proper Komodo-* base.
    if sys.platform.startswith("win"):
        versionTxts.append(gP4Base+"/src/version.win.txt")
    elif sys.platform.startswith("linux"):
        versionTxts.append(gP4Base+"/src/version.linux.txt")
    elif sys.platform.startswith("solaris"):
        versionTxts.append(gP4Base+"/src/version.solaris.txt")
    elif sys.platform.startswith("darwin"):
        versionTxts.append(gP4Base+"/src/version.darwin.txt")
    versionTxts.append(gP4Base+"/src/version.txt")

    versionStr = None
    for versionTxt in versionTxts:
        versionStr = os.popen("p4 print -q %s" % versionTxt).read().strip()
        if versionStr:
            break
    if versionStr is None:
        raise BuildError("no version.txt file: %s" % versionTxts)

    parts = versionStr.split('-')
    allparts = []
    for part in parts:
        allparts += part.split('.')

    return tuple(allparts)


def _getRegmozbuildDir():
    log.debug("trying to find 'regmozbuild.py'")
    def candidates():
        yield join("mozilla", "support")

    attempts = []
    for candidate in candidates():
        attempts.append(candidates)
        if exists(join(candidate, "regmozbuild.py")):
            return candidate
    else:
        raise Error("""\
Could not find regmozbuild.py in any of:
    %s
""" % "\n    ".join(attempts))


def _getMozBuildInfo(scheme):
    """Return the path to a mozilla build (as appropriate for using for
    Komodo's "bk configure --moz-src=<path>").

        "scheme" defines what mozilla build to look for. This is the
            same as what was specified by the --moz-build option.  See
            "smokekomodo -h" for legal values.
    """
    ver = _getKomodoVersionTuple()
    kover = "ko%s.%s" % (ver[0], ver[1])

    if scheme == "latest":
        sys.path.insert(0, _getRegmozbuildDir())
        try:
            import regmozbuild
        finally:
            del sys.path[0]
        conditions = dict(
            mozApp="komodo",
            komodoVersion=("%s.%s" % ver[:2]),
            buildType="release",
            blessed=True,
        )
        mozObjDir = regmozbuild.find_latest_build(**conditions)
        # The 'mozObjDir' is either one or two dirs deeper than
        # 'mozSrc'.
        if basename(mozObjDir) == "mozilla":
            mozSrc = dirname(mozObjDir)
        else:
            mozSrc = dirname(dirname(mozObjDir))

        if log.isEnabledFor(logging.INFO):
            config = regmozbuild.find_latest_mozilla_config(**conditions)
            config_path = config.__file__
            if config_path.endswith(".pyc"):
                config_path = config_path[:-1]
            log.info("---- mozilla build configuration ----\n"
                     + _indent(open(config_path, 'r').read().rstrip()))
            log.info("-------------------------------------")

    elif isdir(scheme):
        mozSrc = scheme
        raise NotImplementedError("moz build scheme dir")
    elif isfile(scheme):
        raise NotImplementedError("moz build scheme config file")
    else:
        raise Error("invalid moz build scheme: '%s'" % scheme)

    # Sanity check the 'mozSrc' dir.
    landmark = join(mozSrc, "mozilla")
    if not exists(landmark):
        raise Error("bogus mozSrc: `%s' does not exist" % mozSrc)

    log.info("using mozilla build at '%s'", mozSrc)
    return mozSrc


def _createP4Client():
    """Create a temporary test p4 client rooted at 'gWrkDir'.

    It returns the name of created client.
    """
    # Determine temporary client name.
    import getpass
    user = getpass.getuser()
    import socket
    machine = socket.gethostname()
    p4client = "%s-%s-smokekomodo" % (user, machine)
    log.info("creating temporary '%s' p4 client", p4client)

    # It is an error if the client exists already.
    p4 = p4lib.P4()
    p4clients = [c["client"] for c in p4.clients()]
    if p4client in p4clients:
        raise Error("Temporary p4 client '%s' already exists. "
            "Aborting (for fear of screwing up another currently running "
            "instance of this script)." % p4client)

    # Build the client spec.
    clientspec = {
        "client": p4client,
        "description": """\
Created by smokekomodo.py -- an automated build/test script for Komodo.
""",
        "root": os.path.abspath(gWrkDir),
        "view": "%s //%s/Komodo/..." % (gP4Tree, p4client),
    }

    # Create the client.
    p4 = p4lib.P4(client=p4client)
    retval = p4.client(client=clientspec)
    return p4client


def _deleteP4Client(p4client):
    log.info("deleting '%s' p4 client", p4client)
    p4 = p4lib.P4(client=p4client)
    p4.client(name=p4client, delete=1)


# Recipe: run (0.5.3) in /Users/trentm/tm/recipes/cookbook
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


def _rmbigtree(dname, use_sudo=False):
    """On Windows removing a huge tree can take a *really* long time if
    the NTFS has been thrashed for a long time. For large deletes let's
    try to move the dir out of the way and do the delete in a subthread
    (or perhaps a subprocess).
    """
    if not os.path.exists(dname):
        return
    if False and sys.platform.startswith("win"):
        # Disabled for now: It seems to leave around t-smoke.death-row
        # dirs (hence isn't useful passed the first one) and since I now
        # have the faster Windows build box (belt), this isn't as helpful
        # anymore.
        death_row_dname = dname + ".death-row"
        if os.path.exists(death_row_dname):
            log.warn("`%s' exists: falling back to regular delete",
                     death_row_dname)
            _rmtree(dname)
        else:
            os.rename(dname, death_row_dname)
            threading.Thread(target=_rmtree, args=(death_row_dname,))
    else:
        _rmtree(dname, use_sudo=use_sudo)

def _rmtree(dname, use_sudo=True):
    if not os.path.exists(dname):
        return
    if sys.platform.startswith("win"):
        _run('attrib -R /s "%s"' % dname)
        _run('rd /s/q "%s"' % dname)
    elif use_sudo:
        _run('sudo chmod -R 0777 "%s"' % dname)
        _run('sudo rm -rf "%s"' % dname)
    else:
        _run('chmod -R 0777 "%s"' % dname)
        _run('rm -rf "%s"' % dname)


def get_relcandi_path():
    if sys.platform == "win32":
        candidates = [r"\\crimper\apps\Komodo\RelCandi"]
    else:
        candidates = ["/nfs/crimper/home/apps/Komodo/RelCandi",
                      "/mnt/crimper.home/apps/Komodo/RelCandi",
                      "/mnt/crimper/apps/Komodo/RelCandi",
                      "/mnt/crimper/home/apps/Komodo/RelCandi"]
    for candidate in candidates:
        if os.path.isdir(candidate): # first one wins
            return candidate
    else:
        raise Error("Could not find a mount point for Komodo's RelCandi "
                    "dir on crimper")


def get_relcandi_changenum():
    relcandi = get_relcandi_path()
    patterns = [os.path.join(relcandi, "Komodo-IDE-*-*.msi"), # final
                os.path.join(relcandi, "Komodo-IDE-*-*-*.msi")] # beta/alpha
    for pattern in patterns:
        builds = glob.glob(pattern)
        if builds: break
    else:
        raise Error("could not find a preceding Komodo IDE MSI in RelCandi")
    changenums = [int(os.path.splitext(b)[0].split('-')[-1]) for b in builds]
    changenums.sort()
    return changenums[-1]

def get_local_changelog_script_path():
    tmpdir = "tmp"
    script = os.path.join("tmp", "change-range-bugs.pl")
    p4paths = {
        "//depot/main/Apps/PDK/Bugzilla/change-range-bugs.pl": os.path.join(tmpdir, "change-range-bugs.pl"),
        "//depot/main/Apps/PDK/Bugzilla/lib/ActiveState/BugzillaDB.pm": os.path.join(tmpdir, "lib", "ActiveState", "BugzillaDB.pm"),
    }
    for p4path, localpath in p4paths.items():
        if not os.path.exists(localpath):
            p4 = p4lib.P4()
            text = p4.print_(p4path)[0]["text"]
            dname = os.path.dirname(localpath)
            if not os.path.isdir(dname):
                os.makedirs(dname)
            open(localpath, 'w').write(text)
    return p4paths["//depot/main/Apps/PDK/Bugzilla/change-range-bugs.pl"]

def get_changelog(lastrev, rev):
    changelog_script = get_local_changelog_script_path()
    dname,basename = os.path.split(changelog_script)
    olddir = os.getcwd()
    try:
        os.chdir(dname)
        cmd = "perl -I lib %s --product Komodo-devel %d %d"\
              % (basename, lastrev, rev)
        o = os.popen(cmd)
        changelog = o.read()
        retval = o.close()
        if retval:
            raise Error("error running '%s' in '%s': retval=%r"
                        % (cmd, os.getcwd(), retval))
    finally:
        os.chdir(olddir)

    title = "Changes since Komodo build %s" % lastrev
    changelog = title + "\n" + "="*len(title) + "\n\n" + changelog
    return changelog



#---- some remote file utils

def _capture_status(argv):
    import subprocess
    p = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    status = p.wait()
    return status

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
        cmd = "pscp -q %s %s" % (src, dst)
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



#---- main worker routines

def checkenv():
    if sys.platform.startswith("win"):
        try:
            # Ensure env. is setup for build.
            which.which("cl.exe")
        except which.WhichError, ex:
            raise Error("""\
%s
Not properly setup for MSVC build.
Do you need to run this:
    "C:\Program Files\Microsoft Visual Studio\VC98\Bin\VCVARS32.BAT"
""" % ex)
    which.which("zip")
    which.which("unzip")

def get(p4client, rev):
    log.debug("get(p4client=%r, rev=%r)", p4client, rev)

    if os.path.exists(gWrkDir):
        log.info("remove old wrk dir: '%s'", gWrkDir)
        if sys.platform.startswith("darwin"):
            _rmbigtree(gWrkDir, use_sudo=True)
        else:
            _rmbigtree(gWrkDir)
    os.makedirs(gWrkDir)

    log.info("doing forced sync of '%s'", gP4Tree)
    p4 = p4lib.P4(client=p4client)
    p4.sync(gP4Tree, force=1)


def build(rev, mozSrc, productType="ide", configOpts=None):
    """Build Komodo in the given working directory.

    Return the build result.
    """
    log.debug("build(rev=%r, mozSrc=%r, productType=%r)",
              rev, mozSrc, productType)
    koDir = os.path.abspath(os.path.join(gWrkDir, "Komodo"))
    log.info("building Komodo in '%s'", koDir)

    blog = ""
    try:
        configure_argv = ["bk", "configure",
                          "--moz-src="+mozSrc,
                          "--komodo-buildnum=%s" % rev]
        configure_argv += ["--release",
                           "--product-type="+productType,
                           "--full"]
        if configOpts:
            configure_argv += configOpts.split(' ') #XXX naive cmdln split

        # Configure, build, and package.
        CAT = (sys.platform == "win32" and "type" or "cat")
        argvs = [
            configure_argv,
            [CAT, "bkconfig.py"],
            ["bk", "clean"],
            ["bk", "build"],
            ["bk", "image"],
            ["bk", "package"],
        ]
        for argv in argvs:
            _run_in_dir(' '.join(argv), koDir, log.info)
    except Error, ex:
        build_result = 1
    else:
        build_result = 0

    # Upload installer to network share.
    import imp
    file, path, desc = imp.find_module("bkconfig",
                                       [os.path.join(gWrkDir, "Komodo")])
    bkconfig = imp.load_module("bkconfig", file, path, desc)

    buildNum = bkconfig.buildNum
    packagesDir = bkconfig.packagesAbsDir
    if sys.platform.startswith("win"):
        subdir = "Windows"
    elif sys.platform.startswith("linux"):
        subdir = "Linux"
        if not glob.glob(os.path.join(packagesDir, "Komodo-*.tar.gz")):
            raise Error("Could not find installer package "
                                   "(expected a 'Komodo-*.tar.gz' in '%s'"
                                   % packagesDir)
    elif sys.platform.startswith("sunos"):
        subdir = "Solaris"
    elif sys.platform.startswith("darwin"):
        subdir = "MacOSX"
    else:
        raise Error("unknown platform: %s" % sys.platform)

    if sys.platform.startswith("win") and productType == "ide":
        # Only need to do this for one build.
        try:
            lastrev = get_relcandi_changenum()
            changelog = get_changelog(lastrev, rev)
            changelogFile = os.path.join(packagesDir, "Komodo-ChangeLog-%s-%s.txt" % (lastrev, rev))
            open(changelogFile,'w').write(changelog)
        except Error, ex:
            log.warn("could not create changelog: %s" % ex)

    packages = glob.glob(os.path.join(packagesDir, "*%s*" % buildNum))
    packages += glob.glob(os.path.join(packagesDir, "dbgp-*"))
    packages += glob.glob(os.path.join(packagesDir, "*.xpi"))
    packages += glob.glob(os.path.join(packagesDir, "*mozilla-patches*"))
    if not gDevBuildsDir:
        raise Error("no accessible DevBuild repos to which to copy "
                    "built packages: '%s'" % "', '".join(packages))
    if isdir(gDevBuildsDir):
        for package in packages:
            src = package
            base = os.path.basename(src)
            dst = os.path.join(gDevBuildsDir, subdir, base)
            log.info("uploading '%s' to '%s'", src, dst)
            shutil.copyfile(src, dst)
            try:
                os.chmod(dst, 0777)
            except EnvironmentError, ex:
                pass
    elif is_remote_path(gDevBuildsDir):
        for package in packages:
            src = package
            dst = gDevBuildsDir + '/' + subdir + '/' + basename(src)
            remote_cp(src, dst, log.info)
    else:
        raise Error("what kind of path is this thing: '%s'"
                    % gDevBuildsDir)


    return build_result


def _parseRevRange(p4client, revRanges):
    p4 = p4lib.P4(client=p4client)

    if revRanges is None:
        # None -> latest change
        revs = [c["change"] for c in p4.changes(gP4Tree, max=1)]
    else:
        allrevs = [c["change"] for c in p4.changes(gP4Tree)]
        revs = []
        for revRange in revRanges.split(','):
            if revRange.find('-') != -1:
                try:
                    lower, upper = revRange.split('-')
                    lower = int(lower)
                    upper = int(upper)
                except ValueError, ex:
                    raise Error("error in rev-ranges string: "
                                           "%s: '%s'" % (ex, revRanges))
                for r in allrevs:
                    r = int(r)
                    if lower <= r <= upper:
                        revs.append(r)
            else:
                try:
                    revs.append(int(revRange))
                except ValueError, ex:
                    raise Error("error in rev-ranges string: "
                                           "%s: '%s'" % (ex, revRanges))
    return revs


def smoke(revRanges=None, mozBuildScheme="latest",
          productType="ide",
          configOpts=None):
    log.debug("smoke(revRanges=%r, mozBuildScheme=%r, productType=%r, "
              "configOpts=%r)", revRanges, mozBuildScheme, productType,
              configOpts)

    checkenv()

    # Change this to use the "http://p4.activestate.com/" service (but
    # keep the old code around).
    p4client = _createP4Client()
    try:
        revs = _parseRevRange(p4client, revRanges)
        mozSrc = _getMozBuildInfo(mozBuildScheme)

        for rev in revs:
            print
            log.info("---- smoke komodo rev %s ---------------", rev)
            get(p4client, rev)
            build_result = build(rev, mozSrc, productType, configOpts)
    finally:
        _deleteP4Client(p4client)
    return build_result


#---- mainline

def main(argv):
    logging.basicConfig()
    log.setLevel(logging.INFO)

    try:
        optlist, args = getopt.getopt(argv[1:], "hVvr:m:p:",
            ["help", "version", "verbose", "rev=",
             "moz-dist=", "product-type=",
             "config-opts="])
    except getopt.GetoptError, msg:
        log.error("%s: argv=%s", msg, argv)
        return 1
    revRanges = None
    mozBuildScheme = "latest"
    productType = "ide"
    configOpts = None
    for opt, optarg in optlist:
        if opt in ("-h", "--help"):
            sys.stdout.write(__doc__)
            return 0
        elif opt in ("-V", "--version"):
            print "smokekomodo %s" % '.'.join([str(i) for i in _version_])
            return 0
        elif opt in ("-v", "--verbose"):
            log.setLevel(logging.DEBUG)
        elif opt in ("-r", "--rev"):
            revRanges = optarg
        elif opt in ("-m", "--moz-build"):
            mozBuildScheme = optarg
        elif opt in ("-p", "--product-type"):
            productType = optarg
        elif opt == "--config-opts":
            configOpts = optarg

    if len(args) != 0:
        log.error("incorrect number of arguments: args=%s", args)
        return 1

    try:
        return smoke(revRanges, mozBuildScheme, productType, configOpts)
    except Error, ex:
        log.error(str(ex))
        if log.isEnabledFor(logging.DEBUG):
            print
            import traceback
            traceback.print_exception(*sys.exc_info())
        return 1


if __name__ == "__main__":
    __file__ = os.path.abspath(sys.argv[0])
    sys.exit( main(sys.argv) )

