
"""Blackfile for Komodo.

Usage:
    bk configure ...    # configure a Komodo build
    bk build            # build it
    bk package          # create a package (default is the native installer)

Typical commands for a Komodo development build:

    bk configure --release --moz-src=../path/to/moz/build
    bk build
    bk run          # run it, test it

Typical commands for building all Komodo bits:

    bk configure --release --moz-src=../path/to/moz/build --full
    bk build                # build all the bits
    bk image                # put the install image together
    bk package [PKGNAME]    # package up everything, don't specify a
                            # PKGNAME to build all packages that this
                            # platform can build

PKGNAME's are docs, aspndocs, installer (aka msi, dbg,
aspackage).
"""

import os, sys, os, shutil, pickle
import time
from os.path import join, dirname, exists, isfile, basename, abspath, \
                    isdir, splitext
from posixpath import join as urljoin
import pprint
import glob
import md5
import operator
import logging


import black, black.configure, black.configure.std
import tmShUtil

sys.path.insert(0, "")
from bklocal import *     # local Black configuration items

sys.path.insert(0, "util")
try:
    import patchtree
    import platinfo
    import buildutils
    import pkgutils
    import applib
    import changelog
finally:
    del sys.path[0]



#---- exceptions

class Error(Exception):
    pass



#---- globals

log = logging.getLogger("build")
if 1:
    # Remove logging setup if/when "bk" grows real logging control.
    logging.basicConfig()
    log.setLevel(logging.INFO)

out = sys.stdout
_table = {} # for "build quick"

if sys.platform == "win32":
    EXE = ".exe"
else:
    EXE = ""



#---- internal support routines

# Recipe: paths_from_path_patterns (0.3.6)
def _should_include_path(path, includes, excludes):
    """Return True iff the given path should be included."""
    from os.path import basename
    from fnmatch import fnmatch

    base = basename(path)
    if includes:
        for include in includes:
            if fnmatch(base, include):
                try:
                    log.debug("include `%s' (matches `%s')", path, include)
                except (NameError, AttributeError):
                    pass
                break
        else:
            log.debug("exclude `%s' (matches no includes)", path)
            return False
    for exclude in excludes:
        if fnmatch(base, exclude):
            try:
                log.debug("exclude `%s' (matches `%s')", path, exclude)
            except (NameError, AttributeError):
                pass
            return False
    return True

_NOT_SPECIFIED = ("NOT", "SPECIFIED")
def _paths_from_path_patterns(path_patterns, files=True, dirs="never",
                              recursive=True, includes=[], excludes=[],
                              on_error=_NOT_SPECIFIED):
    """_paths_from_path_patterns([<path-patterns>, ...]) -> file paths

    Generate a list of paths (files and/or dirs) represented by the given path
    patterns.

        "path_patterns" is a list of paths optionally using the '*', '?' and
            '[seq]' glob patterns.
        "files" is boolean (default True) indicating if file paths
            should be yielded
        "dirs" is string indicating under what conditions dirs are
            yielded. It must be one of:
              never             (default) never yield dirs
              always            yield all dirs matching given patterns
              if-not-recursive  only yield dirs for invocations when
                                recursive=False
            See use cases below for more details.
        "recursive" is boolean (default True) indicating if paths should
            be recursively yielded under given dirs.
        "includes" is a list of file patterns to include in recursive
            searches.
        "excludes" is a list of file and dir patterns to exclude.
            (Note: This is slightly different than GNU grep's --exclude
            option which only excludes *files*.  I.e. you cannot exclude
            a ".svn" dir.)
        "on_error" is an error callback called when a given path pattern
            matches nothing:
                on_error(PATH_PATTERN)
            If not specified, the default is look for a "log" global and
            call:
                log.error("`%s': No such file or directory")
            Specify None to do nothing.

    Typically this is useful for a command-line tool that takes a list
    of paths as arguments. (For Unix-heads: the shell on Windows does
    NOT expand glob chars, that is left to the app.)

    Use case #1: like `grep -r`
      {files=True, dirs='never', recursive=(if '-r' in opts)}
        script FILE     # yield FILE, else call on_error(FILE)
        script DIR      # yield nothing
        script PATH*    # yield all files matching PATH*; if none,
                        # call on_error(PATH*) callback
        script -r DIR   # yield files (not dirs) recursively under DIR
        script -r PATH* # yield files matching PATH* and files recursively
                        # under dirs matching PATH*; if none, call
                        # on_error(PATH*) callback

    Use case #2: like `file -r` (if it had a recursive option)
      {files=True, dirs='if-not-recursive', recursive=(if '-r' in opts)}
        script FILE     # yield FILE, else call on_error(FILE)
        script DIR      # yield DIR, else call on_error(DIR)
        script PATH*    # yield all files and dirs matching PATH*; if none,
                        # call on_error(PATH*) callback
        script -r DIR   # yield files (not dirs) recursively under DIR
        script -r PATH* # yield files matching PATH* and files recursively
                        # under dirs matching PATH*; if none, call
                        # on_error(PATH*) callback

    Use case #3: kind of like `find .`
      {files=True, dirs='always', recursive=(if '-r' in opts)}
        script FILE     # yield FILE, else call on_error(FILE)
        script DIR      # yield DIR, else call on_error(DIR)
        script PATH*    # yield all files and dirs matching PATH*; if none,
                        # call on_error(PATH*) callback
        script -r DIR   # yield files and dirs recursively under DIR
                        # (including DIR)
        script -r PATH* # yield files and dirs matching PATH* and recursively
                        # under dirs; if none, call on_error(PATH*)
                        # callback
    """
    from os.path import basename, exists, isdir, join
    from glob import glob

    assert not isinstance(path_patterns, basestring), \
        "'path_patterns' must be a sequence, not a string: %r" % path_patterns
    GLOB_CHARS = '*?['

    for path_pattern in path_patterns:
        # Determine the set of paths matching this path_pattern.
        for glob_char in GLOB_CHARS:
            if glob_char in path_pattern:
                paths = glob(path_pattern)
                break
        else:
            paths = exists(path_pattern) and [path_pattern] or []
        if not paths:
            if on_error is None:
                pass
            elif on_error is _NOT_SPECIFIED:
                try:
                    log.error("`%s': No such file or directory", path_pattern)
                except (NameError, AttributeError):
                    pass
            else:
                on_error(path_pattern)

        for path in paths:
            if isdir(path):
                # 'includes' SHOULD affect whether a dir is yielded.
                if (dirs == "always"
                    or (dirs == "if-not-recursive" and not recursive)
                   ) and _should_include_path(path, includes, excludes):
                    yield path

                # However, if recursive, 'includes' should NOT affect
                # whether a dir is recursed into. Otherwise you could
                # not:
                #   script -r --include="*.py" DIR
                if recursive and _should_include_path(path, [], excludes):
                    for dirpath, dirnames, filenames in os.walk(path):
                        dir_indeces_to_remove = []
                        for i, dirname in enumerate(dirnames):
                            d = join(dirpath, dirname)
                            if dirs == "always" \
                               and _should_include_path(d, includes, excludes):
                                yield d
                            if not _should_include_path(d, [], excludes):
                                dir_indeces_to_remove.append(i)
                        for i in reversed(dir_indeces_to_remove):
                            del dirnames[i]
                        if files:
                            for filename in sorted(filenames):
                                f = join(dirpath, filename)
                                if _should_include_path(f, includes, excludes):
                                    yield f

            elif files and _should_include_path(path, includes, excludes):
                yield path


def _cp(src, dst):
    if sys.platform == "win32":
        if isdir(src):
            if not exists(dst): 
                os.makedirs(dst)
            _run('xcopy /q/s "%s" "%s"' % (src, dst))
        elif '*' in src or '?' in src:
            if not exists(dst): 
                os.makedirs(dst)
            for path in glob.glob(src):
                _run('copy "%s" "%s"' % (path, dst))
        else:
            if not exists(dirname(dst)):
                os.makedirs(dirname(dst))
            _run('copy "%s" "%s"' % (src, dst))
    else:
        if '*' in src or '?' in src:
            _run('mkdir -p "%s"' % dst)
            for path in glob.glob(src):
                _run('cp -R "%s" "%s"' % (path, dst))
        else:
            _run('mkdir -p "%s"' % dirname(dst))
            _run('cp -R "%s" "%s"' % (src, dst))


def _isdir(dirname):
    r"""os.path.isdir() doesn't work for UNC mount points. Fake it.
    
    # For an existing mount point (want: _isdir() == 1)
    os.path.ismount(r"\\crimper\apps") -> 1
    os.path.exists(r"\\crimper\apps") -> 0
    os.path.isdir(r"\\crimper\apps") -> 0
    os.listdir(r"\\crimper\apps") -> [...contents...]
    # For a non-existant mount point (want: _isdir() == 0)
    os.path.ismount(r"\\crimper\foo") -> 1
    os.path.exists(r"\\crimper\foo") -> 0
    os.path.isdir(r"\\crimper\foo") -> 0
    os.listdir(r"\\crimper\foo") -> WindowsError
    # For an existing dir under a mount point (want: _isdir() == 1)
    os.path.mount(r"\\crimper\apps\Komodo") -> 0
    os.path.exists(r"\\crimper\apps\Komodo") -> 1
    os.path.isdir(r"\\crimper\apps\Komodo") -> 1
    os.listdir(r"\\crimper\apps\Komodo") -> [...contents...]
    # For a non-existant dir/file under a mount point (want: _isdir() == 0)
    os.path.ismount(r"\\crimper\apps\foo") -> 0
    os.path.exists(r"\\crimper\apps\foo") -> 0
    os.path.isdir(r"\\crimper\apps\foo") -> 0
    os.listdir(r"\\crimper\apps\foo") -> []  # as if empty contents
    # For an existing file under a mount point (want: _isdir() == 0)
    os.path.ismount(r"\\crimper\apps\Komodo\latest.komodo-devel.txt") -> 0
    os.path.exists(r"\\crimper\apps\Komodo\latest.komodo-devel.txt") -> 1
    os.path.isdir(r"\\crimper\apps\Komodo\latest.komodo-devel.txt") -> 0
    os.listdir(r"\\crimper\apps\Komodo\latest.komodo-devel.txt") -> WindowsError
    """
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


def _rmtreeOnError(rmFunction, filePath, excInfo):
    if excInfo[0] == OSError:
        # presuming because file is read-only
        os.chmod(filePath, 0777)
        rmFunction(filePath)

def _rmtree(dirname):
    import shutil
    shutil.rmtree(dirname, 0, _rmtreeOnError)


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


def _copy(src, dst):
    """works the way a good copy should :)
        - no source, raise an exception
        - destination directory, make a file in that dir named after src
        - source directory, recursively copy the directory to the destination
        - filename wildcarding allowed
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
            if os.path.isfile(dstFile):
                # make sure 'dstFile' is writeable
                os.chmod(dstFile, 0755)
            shutil.copy(srcFile, dstFile)
            # make the new 'dstFile' writeable
            os.chmod(dstFile, 0755)
        elif _isdir(srcFile):
            srcFiles = os.listdir(srcFile)
            if not os.path.exists(dst):
                _mkdir(dst)
            for f in srcFiles:
                s = os.path.join(srcFile, f)
                d = os.path.join(dst, f)
                try:
                    _copy(s, d)
                except (IOError, os.error), why:
                    raise OSError("Can't copy %s to %s: %s"\
                          % (repr(s), repr(d), str(why)))
        elif not usingWildcards:
            raise OSError("Source file %s does not exist" % repr(srcFile))


def _escapeArg(arg):
    """Escape the given command line argument for the shell."""
    #XXX There is a probably more that we should escape here.
    return arg.replace('"', r'\"')


def _joinArgv(argv):
    r"""Join an arglist to a string appropriate for running.

        >>> import os
        >>> _joinArgv(['foo', 'bar "baz'])
        'foo "bar \\"baz"'
    """
    cmdstr = ""
    for arg in argv:
        if ' ' in arg or ';' in arg:
            cmdstr += '"%s"' % _escapeArg(arg)
        else:
            cmdstr += _escapeArg(arg)
        cmdstr += ' '
    if cmdstr.endswith(' '): cmdstr = cmdstr[:-1]  # strip trailing space
    return cmdstr


# Recipe: run (0.5.3) in C:\trentm\tm\recipes\cookbook
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



#---- ensure have the necessary version of Black

_minBlackVersion = (0, 4, 1)
if black.GetVersionTuple() < _minBlackVersion:
    raise black.BlackError("Insufficient version of Black. The current "
        "version is '%s' but version '%s' or greater is required. The "
        "version in 'util/black' should be sufficient -- add that dir "
        "to your PATH."
        % (black.GetPrettyVersion(),
           ".".join([str(i) for i in _minBlackVersion])))


#---- define the Komodo configuration items

configuration = {
    "name": "Komodo-open", #TODO: remove if not used, use "branch" instead
    "branch": "Komodo-open",

    "PATH": SetPath(), 
    "systemDirs": black.configure.std.SystemDirs(), 
    "path": black.configure.std.Path(), 

    "prebuiltPaths": PrebuiltPaths(),

    "siloedPythonExeName": SiloedPythonExeName(), # "python", "python.exe", "python_d.exe"
    "siloedPythonInstallDir": SiloedPythonInstallDir(),
    "siloedPythonBinDir": SiloedPythonBinDir(),
    "siloedPythonVersion": SiloedPythonVersion(), # e.g. "2.4.1"
    "siloedPyVer": SiloedPyVer(), # e.g. "2.4"
    "siloedPython": SiloedPython(), # e.g. /full/path/to/siloed/bin/python

    "siloedDistutilsLibDirName": SiloedDistutilsLibDirName(), # e.g "lib.win32-2.4"
    "perlVersion": black.configure.std.PerlVersion(perlBinDirItemName="unsiloedPerlBinDir"),
    "activePerlBuild": black.configure.std.ActivePerlBuild(perlBinDirItemName="unsiloedPerlBinDir"),

    # "perl56" added below for all bug Mac OS X
    "perl58": PerlExe(version=(5,8)),

    "unsiloedPerlBinDir": UnsiloedPerlBinDir(),
    "unsiloedPerlExe": UnsiloedPerlExe(),
    "unsiloedPythonBinDir": UnsiloedPythonBinDir(),
    "unsiloedPythonExe": UnsiloedPythonExe(),
    "consInstallDir": ConsInstallDir(),
    "consVersion": ConsVersion(),

    #---- mozilla environment settings
    "MOZ_DEBUG": black.configure.mozilla.SetMozDebug(),
    "XPCOM_DEBUG_BREAK": black.configure.mozilla.SetXpcomDebugBreakDebug(),
    "MOZ_SRC": SetMozSrc(),
    "LD_LIBARY_PATH": SetLdLibraryPath(),
    # TODO: setup mozLdLibraryPath and have a custom LD_LIBRARY_PATH *or*
    #       setup a generic SetPathEnvVar("LD_LIBRARY_PATH", [list of
    #       configuration items to add to it]),
    # TODO: the same kind of generic this for PATH

    #---- Microsoft Visual Studio setup ----
    "msvcrtDebugDllsInstalled": black.configure.std.MsvcrtDebugDllsInstalled(), 
    "compiler": SetupCompiler(),
    "setupMozEnv": SetupMozEnv(),

    #---- komodo stuff
    # TODO: complain if Komodo debug/release conflicts with the debug/release
    #       state of the MOZ_SRC
    "platform": Platform(),
    "architecture": Architecture(),
    "libcppVersion": LibCPPVersion(),
    "glibcVersion": GLibCVersion(),

    # Komodo version configuration vars.
    # - base variables:                                             # Example:
    "komodoVersion": KomodoVersion(),                               #   3.10.0-alpha1
    "productType": ProductType(),                                   #   ide
    "prettyProductType": PrettyProductType(),                       #   IDE
    "productTagLine": ProductTagLine(),                             #   The professional IDE for dynamic languages
    "buildNum": BuildNum(),                                         #   123456
    "sourceId": SourceId(),                                         #   e.g., 1234M
    # - derived from base variables:
    "komodoShortVersion": KomodoShortVersion(),                     #   3.10
    "komodoMarketingVersion": KomodoMarketingVersion(),             #   3.X-alpha1  (dropping '0' here for effect)
    "komodoMarketingShortVersion": KomodoMarketingShortVersion(),   #   3.X
    "komodoPrettyVersion": KomodoPrettyVersion(),                   #   3.X Alpha 1
    "komodoFullPrettyVersion": KomodoFullPrettyVersion(),           #   Komodo IDE 3.X Alpha 1 (Build 123456)
    "komodoTitleBarName": KomodoTitleBarName(),                     #   ActiveState Komodo IDE 3.X
    "komodoAppDataDirName": KomodoAppDataDirName(),                 #   KomodoIDE or komodoide (plat-dep)
    "version": Version(),                                           # alias for 'komodoVersion' (kept for compat)
    # - MSI variables:
    "msiProductName": MSIProductName(),                             #   ActiveState Komodo IDE 3.X Alpha 1
    "msiInstallName": MSIInstallName(),                             #   ActiveState Komodo 3.X
    "msiKomodoVersion": MSIKomodoVersion(),                         #   3.10.0 (XXX need to have more differentiation here!)
    "msiKomodoId": MSIKomodoId(),                                   #   Komod310 (XXX has to be max 8 chars!)
    "msiRegistryId": MSIRegistryId(),                               #   3.10-ide
    "macKomodoAppName": MacKomodoAppName(),   # e.g. "Komodo.app", "Komodo IDE.app"
    "msiKomodoPrettyId": MSIKomodoPrettyId(),

    "komodoPackageBase": KomodoPackageBase(),
    "komodoUpdateManualURL": KomodoUpdateManualURL(),

    "gnomeDesktopName": GnomeDesktopName(),
    "gnomeDesktopGenericName": GnomeDesktopGenericName(),
    "gnomeDesktopCategories": GnomeDesktopCategories(),
    "gnomeDesktopShortcutName": GnomeDesktopShortcutName(),
    
    "buildType": BuildType(),               # "release" or "debug"
    "buildFlavour": BuildFlavour(),         # "dev" or "full"
    "versionInfoFile": VersionInfoFile(),
    "KOMODO_HOSTNAME": SetKomodoHostname(),
    "withSymbols": WithSymbols(),
    "PYTHONPATH": SetPythonPath(), 
    "MOZILLA_FIVE_HOME": SetMozillaFiveHome(), 
    "komodoDevDir": KomodoDevDir(),
    "mozillaDevDir": MozillaDevDir(),
    "komodoDefaultUserInstallDir": KomodoDefaultUserInstallDir(),
    "mozSrc": MozSrc(),
    "mozObjDir": MozObjDir(),
    "mozDist": MozDist(),
    "mozDevelDist": MozDevelDist(),
    "mozBin": MozBin(),
    "mozDevelBin": MozDevelBin(),
    "mozApp": MozApp(),
    "mozExe": MozExe(),
    "mozVersion": MozVersion(),
    "mozVersionNumber": MozVersionNumber(),
    "mozMajorVersion": MozMajorVersion(),
    "mozMinorVersion": MozMinorVersion(),
    "mozResourcesDir": MozResourcesDir(),
    "mozComponentsDir": MozComponentsDir(),   #XXX necessary?
    "mozChromeDir": MozChromeDir(),   #XXX necessary?
    "mozPluginsDir": MozPluginsDir(), #XXX necessary?
    "mozExtensionDir": MozExtensionDir(),
    "KOMODO_MOZBINDIR": SetMozBinDir(),
    "komodoPythonUtilsDir": KomodoPythonUtilsDir(),  #XXX change to LibDir
    "installRelDir": InstallRelDir(),
    "supportDir": SupportDir(),
    "sdkDir": SDKDir(),
    "stubDir": StubDir(),       # the build dir for the Komodo starter stub
    "docChromeDir": DocChromeDir(),         # the area in the dev-tree to place the docs
    "docDir": DocDir(),         # the area in the dev-tree to place the docs
    "readmeDir": ReadmeDir(),   # prominent dir for a few standalone doc bits
    "sysdllsDir": SysdllsDir(), # dir for system DLLs to install (if necessary)
    "installSupportDir": InstallSupportDir(), # dir for installer support files
    "buildRelDir": BuildRelDir(), 
    "buildAbsDir": BuildAbsDir(), 
    "packagesRelDir": PackagesRelDir(), 
    "packagesAbsDir": PackagesAbsDir(), 
    "exportRelDir": ExportRelDir(), 
    "idlExportRelDir": IdlExportRelDir(), 
    "installRelDir_ForCons": InstallRelDir_ForCons(), 
    "buildRelDir_ForCons": BuildRelDir_ForCons(), 
    "contribBuildRelDir_ForCons": ContribBuildRelDir_ForCons(), 
    "exportRelDir_ForCons": ExportRelDir_ForCons(), 
    "idlExportRelDir_ForCons": IdlExportRelDir_ForCons(), 
    "installAbsDir": InstallAbsDir(),
    "scintillaBuildDir": ScintillaBuildDir(),
    "linuxDistro": LinuxDistro(),
    "komodoInstallerPackage": KomodoInstallerPackage(),
    "configTokens": ConfigTokens(),
    "aspnDocsPackageName": ASPNDocsPackageName(),
    "docsPackageName": DocsPackageName(),
    "mozPatchesPackageName": MozPatchesPackageName(),

    "withCrypto": WithCrypto(), # configure with Crypto support
    "withCasper": WithCasper(),
    "withJSLib": WithJSLib(),
    "withDocJarring": WithDocJarring(),
    "withKomodoCix": WithKomodoCix(),
    "xulrunner": XULRunnerApp(), # xulrunner based builds
    "universal": UniversalApp(), # ppc+i386 builds

    "ludditeVersion": LudditeVersion(),

    "isGTK2Siloed": IsGTK2Siloed(),

    "buildTime": BuildTime(),
    "buildASCTime": BuildASCTime(),
    "buildPlatform": BuildPlatform(),

    #---- items necessary for building a Komodo installer
    # (i.e. not required for plain development builds),
    "jarring": Jarring(),
}
if sys.platform != "darwin":
    configuration["perl56"] = PerlExe(version=(5,6))
if sys.platform == "darwin":
    configuration["applePython23NeedsFixing"] = ApplePython23NeedsFixing()
if sys.platform == "win32":
    configuration["nonMsysPerl"] = NonMsysPerlExe()




#---- command overrides specific to this Komodo branch

def _Tar(argline):
    """just call 'tar' with the given argument line and fail gracefully"""
    # XXX replace this or get rid of it
    out.write("run: 'tar %s'\n" % argline)
    if not tmShUtil.Which("tar"):
        raise black.BlackError("no 'tar' on path")
    else:
        return os.system("tar " + argline)

def _rmemptydirs(dirname):
    for subdir in os.listdir(dirname):
        subdir = os.path.join(dirname, subdir)
        if not os.path.islink(subdir) and os.path.isdir(subdir):
            _rmemptydirs(subdir)
    if not os.listdir(dirname):
        out.write("rmdir %s\n" % dirname)
        os.rmdir(dirname)

def _banner(text, ch='=', length=78):
    """Return a banner line centering the given text.
    
        "text" is the text to show in the banner. None can be given to have
            no text.
        "ch" (optional, default '=') is the banner line character (can
            also be a short string to repeat).
        "length" (optional, default 78) is the length of banner to make.

    Examples:
        >>> banner("Peggy Sue")
        '================================= Peggy Sue =================================='
        >>> banner("Peggy Sue", ch='-', length=50)
        '------------------- Peggy Sue --------------------'
        >>> banner("Pretty pretty pretty pretty Peggy Sue", length=40)
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

def ImageKomodo(cfg, argv):
    """Build the Komodo install image."""
    from os.path import join, isdir, exists, dirname, basename
    print "creating install image in '%s'..." % cfg.installRelDir

    # Handy (and platform-independent) path factory functions.
    def mozdistpath(*parts):
        return join(cfg.mozDist, *parts)
    def chromepath(*parts):
        return join(cfg.mozChromeDir, *parts)
    def stubpath(*parts):
        return join(cfg.stubDir, *parts)
    def supportpath(*parts):
        return join(cfg.supportDir, *parts)
    def sdkpath(*parts):
        return join(cfg.sdkDir, *parts)
    def docpath(*parts):
        return join(cfg.docDir, *parts)
    def docchromepath(*parts):
        return join(cfg.docChromeDir, *parts)
    def readmepath(*parts):
        return join(cfg.readmeDir, *parts)
    def sysdllspath(*parts):
        return join(cfg.sysdllsDir, *parts)
    def installsupportpath(*parts):
        return join(cfg.installSupportDir, *parts)

    def ipkgpath(*parts):
        """Base dir for files in the installer package."""
        return join(cfg.installRelDir, *parts)
    def iicorepath(*parts):
        """Install image dir for the 'core' feature."""
        if sys.platform == "win32":
            return ipkgpath("feature-core", "INSTALLDIR", *parts)
        elif sys.platform == "darwin":
            return ipkgpath(*parts)
        else:
            return ipkgpath("INSTALLDIR", *parts)
    def iimozbinpath(*parts):
        """Install image dir for the 'core' feature."""
        if sys.platform == "win32":
            return ipkgpath("feature-core", "INSTALLDIR", "lib", "mozilla", *parts)
        elif sys.platform == "darwin":
            return ipkgpath(cfg.macKomodoAppName, "Contents", "MacOS", *parts)
        else:
            return ipkgpath("INSTALLDIR", "lib", "mozilla", *parts)
    def iipylibpath(*parts):
        if sys.platform == "win32":
            return ipkgpath("feature-core", "INSTALLDIR", "lib", "python", "Lib", *parts)
        elif sys.platform == "darwin":
            return ipkgpath(cfg.macKomodoAppName,
                            "Contents/Frameworks/Python.framework/Versions",
                            "%s/lib/python%s" % (cfg.siloedPyVer, cfg.siloedPyVer),
                            *parts)
        else:
            return ipkgpath("INSTALLDIR", "lib", "python", "lib",
                            "python%s" % cfg.siloedPyVer, *parts)
    def iipysitelibpath(*parts):
        """Install image lib/mozilla/python/komodo/... path"""
        return iimozbinpath("python", "komodo", *parts)
    def iisysdllspath(*parts):
        """Install image SystemFolder dir for the 'core' feature."""
        if sys.platform == "win32":
            return ipkgpath("feature-core", "SystemFolder", *parts)
        else:
            return None
    def iicorebinpath(*parts):
        """Install image main binaries dir for the 'core' feature."""
        if sys.platform == "win32":
            return ipkgpath("feature-core", "INSTALLDIR", *parts)
        elif sys.platform == "darwin":
            return ipkgpath(cfg.macKomodoAppName, "Contents", "bin", *parts)
        else:
            return ipkgpath("INSTALLDIR", "bin", *parts)
    def iisupportpath(*parts):
        """Image image dir for the Komodo 'support' bits."""
        if sys.platform == "darwin":
            return iicorepath(cfg.macKomodoAppName, "Contents",
                              "SharedSupport", *parts)
        else:
            return iicorepath("lib", "support", *parts)
    def iisdkpath(*parts):
        """Image image dir for the Komodo SDK."""
        if sys.platform == "darwin":
            return iisupportpath("sdk", *parts)
        else:
            return iicorepath("lib", "sdk", *parts)
    def iidocpath(*parts):
        """Install image dir for the Komodo docs."""
        if sys.platform == "win32":
            return ipkgpath("feature-docs", "INSTALLDIR", "lib", "mozilla",
                            "chrome", "komododoc", "locale", "en-US",
                            *parts)
        else:
            return iimozbinpath("chrome", "komododoc", "locale",
                                "en-US", *parts)
    def iidocchromepath(*parts):
        """Install image dir for the Komodo docs."""
        if sys.platform == "win32":
            return ipkgpath("feature-docs", "INSTALLDIR", "lib", "mozilla",
                            "chrome", "komododoc", *parts)
        else:
            return iimozbinpath("chrome", "komododoc", *parts)
    def iicorereadmepath(*parts):
        """Install image dir for the "prominent standalone doc bits"."""
        if sys.platform == "win32":     # ...in the root install dir
            return ipkgpath("feature-core", "INSTALLDIR", *parts)
        elif sys.platform == "darwin":  # ...in the .app bundle Resources dir
            return ipkgpath(cfg.macKomodoAppName, "Contents", "Resources", *parts)
        else:                           # ...in the root doc area
            return ipkgpath("INSTALLDIR", "share", "doc", *parts)

    # Define the steps to build the install image.
    # Note that Mac OS X is quite different -- with the .app bundle
    # structure and the differences in the Mozilla build to accomodate
    # that.
    ibits = []  # the steps to build the install image
    # - Copy over the main bits: Mozilla build, siloed Python, Komodo
    #   support grabbag
    if sys.platform == "darwin":
        # A dilemma here: "Komodo.app/Contents/MacOS/..." is a bunch of
        # symlinks that we want to follow when copying. Same as Linux &
        # Solaris. However,
        # "Komodo.app/Contents/Frameworks/Python.framework/..." has two
        # *self-referential* symlinks that *cannot* be followed and we
        # want to keep. Grr. HACK around this.
        ibits += [
            ("hack-cp", mozdistpath("Komodo.app"), ipkgpath(cfg.macKomodoAppName)),
        ]
    else:
        ibits += [
            # Note: This creates a lib/mozilla/... with one problem. See
            # "Some manual fixes" below.
            ("cp", mozdistpath("bin"),    iicorepath("lib", "mozilla")),
            ("cp", mozdistpath("python"), iicorepath("lib", "python")),
        ]
    ibits += [
        ("cp", supportpath(), iisupportpath()),
        ("cp", sdkpath(), iisdkpath()),
        ("cp", join("src", "codeintel", "share", "cix-2.0.rng"),
               iisdkpath("share", "cix-2.0.rng")),
        ("rm", iimozbinpath("xpidl"+EXE)),
        ("rm", iimozbinpath("xpt_dump"+EXE)),
        ("rm", iimozbinpath("xpt_link"+EXE)),
        #TODO: might be able to drop regxpcom as well (it is in sdk/bin).
    ]
    if sys.platform == "win32" and cfg.jarring:
        # Remove unjarred directories on windows (already handled for
        # other platforms).
        ibits += [
            ("rmdir", iicorepath("lib", "mozilla", "chrome", "xtk")),
            ("rmdir", iicorepath("lib", "mozilla", "chrome", "komodo")),
        ]

    # - Add the Komodo starter stub(s)
    if sys.platform == "darwin":
        #XXX Not currently implemented for Darwin
        pass
    elif sys.platform == "win32":
        ibits += [
            ("cp", stubpath("komodo"+EXE), iicorebinpath("komodo"+EXE)),
            ("cp", stubpath("ko"+EXE), iicorebinpath("ko"+EXE)),
        ]
    else:
        ibits += [
            ("cp", stubpath("komodo"+EXE), iicorebinpath("komodo"+EXE)),
        ]

    # - 'komodo-config' belongs in the installed bin dir, not the
    #   moz-bin dir.
    komodo_config_name = (sys.platform == "win32" and "komodo-config.py"
                          or "komodo-config")
    ibits += [
        ("cp", mozdistpath("bin", komodo_config_name), iicorebinpath(komodo_config_name)),
        ("rm", iimozbinpath(komodo_config_name)),
    ]

    # - The prominent standalone doc bits: place somewhere appropriate
    #   in installation *and* in the base of installer package.
    ibits += [
        ("cp", readmepath("*.txt"), iicorereadmepath()),
        ("cp", readmepath("*.txt"), ipkgpath()),
    ]
    if sys.platform == "darwin":
        ibits += [
            # No room for FEEDBACK.txt in the DMG root
            ("rm", ipkgpath("FEEDBACK.txt")),
        ]

    # - The main Komodo docs. (Only need to worry about these separately
    # on Windows because the MSI divides the install image by feature,
    # and the docs are a separate "MSI feature".)
    if sys.platform == "win32":
        ibits += [
            # First need to remove the komododoc chrome from the
            # feature-core/... area where it was copied by steps above.
            ("rmdir", iicorepath("lib", "mozilla", "chrome", "komododoc")),
            ("rm", iicorepath("lib", "mozilla", "chrome", "komododoc.manifest")),
            # The manifest.
            ("cp", chromepath("komododoc.manifest"),
             ipkgpath("feature-docs", "INSTALLDIR", "lib", "mozilla", 
                      "chrome", "komododoc.manifest")),
        ]
        if cfg.withDocJarring:
            ibits += [
                ("rm", iicorepath("lib", "mozilla", "chrome", "komododoc.jar")),
                ("cp", chromepath("komododoc.jar"),
                 ipkgpath("feature-docs", "INSTALLDIR", "lib", "mozilla", 
                          "chrome", "komododoc.jar")),
            ]
        else:
            ibits += [
                ("cp", docchromepath(), iidocchromepath()),
            ]

    # - Installer support files
    ibits += [
        ("cp", installsupportpath("*"), ipkgpath()),
    ]

    # - System DLLs to update on the target system (generally Windows
    #   only).
    ibits += [
        ("cp", sysdllspath("*.dll"), iisysdllspath()),
    ]

    # - Un*x share bits
    if sys.platform not in ("win32", "darwin"):
        ibits += [
            ("cp", join("src", "main", "komodo16.%s.png" % cfg.productType),
                   iicorepath("share", "icons", "komodo16.png")),
            ("cp", join("src", "main", "komodo32.%s.png" % cfg.productType),
                   iicorepath("share", "icons", "komodo32.png")),
            ("cp", join("src", "main", "komodo48.%s.png" % cfg.productType),
                   iicorepath("share", "icons", "komodo48.png")),
            ("cp", join("src", "main", "komodo128.%s.png" % cfg.productType),
                   iicorepath("share", "icons", "komodo128.png")),
            ("cp", join("src", "main", "komodo16.%s.xpm" % cfg.productType),
                   iicorepath("share", "icons", "komodo16.xpm")),
            ("cp", join("src", "main", "komodo32.%s.xpm" % cfg.productType),
                   iicorepath("share", "icons", "komodo32.xpm")),
            ("cp", join("src", "main", "komodo48.%s.xpm" % cfg.productType),
                   iicorepath("share", "icons", "komodo48.xpm")),
            ("cp", join("src", "main", "komodo128.%s.xpm" % cfg.productType),
                   iicorepath("share", "icons", "komodo128.xpm")),
        ]

    # - Trim some stuff.
    ibits += [
        # Remove "dev-tree" marker file.
        ("rm", iimozbinpath("is_dev_tree.txt")), 

        # Trim some files.
        ("rtrim", ".consign"),
        ("rtrim", "*.pyc"),
        ("rtrim", "*.pyo"),
        ("rm",    iimozbinpath("*.txt")),
        ("rm",    iimozbinpath("LICENSE")),

        # Trim some unneeded stuff in siloed Python.
        ("rmdir", iipylibpath("ctypes", "test")),
        ("rmdir", iipylibpath("sqlite3", "test")),
        ("rmdir", iipylibpath("site-packages", "isapi", "doc")),
        ("rmdir", iipylibpath("site-packages", "isapi", "samples")),

        # Remove empty dirs
        ("rmemptydirs", iicorepath()),

        #XXX:TODO
        #XXX trim other generated tmp files?
        #XXX trim Python lib/python/libs
        #XXX trim Python lib/python/DLLs/_testcapi.pyd
        #XXX can we trim down the PyWin32 bits a bit?
        #XXX (eventually) doc/...
        #XXX (eventually) etc/...
        #XXX (eventually) share/...
        #XXX (eventually) samples outside of support/...
    ]
    if sys.platform == "win32":
        # We don't need the Python DLLs beside python.exe in the siloed
        # Python. The DLLs are already beside the main komodo.exe where
        # we *do* need them.
        ibits += [
            ("rm", iicorepath("lib", "python", "py*.dll")),
            ("rm", iicorepath("lib", "python", "w9xpopen.exe")),
        ]
    # Don't know why, but my Moz build on Windows sometimes has these two
    # regxpcom by-products (may be a side-effect of the komodo.cix
    # generation).
    ibits += [
        ("trim", iimozbinpath("components", "compreg.dat")),
        ("trim", iimozbinpath("components", "xpti.dat")),
    ]

    # Start with a fresh image
    basedir = "install" #ipkgpath()
    if exists(basedir): # start with a fresh INSTALLDIR/...
        if sys.platform == "win32":
            _run("rd /s/q %s" % basedir)
        else:
            _run("rm -rf %s" % basedir)
    os.makedirs(basedir)

    # Solaris doesn't support the -L
    if sys.platform.startswith("sunos"):
        cplink = "cp -R"
    else:
        cplink = "cp -R -L"

    # Create the install image according to the instruction in 'ibits'.
    for data in ibits:
        print ' '.join([d or '' for d in data]) # Guard against None
        if data[0] == "hack-cp":
            # A "cp" action that HACKs around the problem described
            # above: symlink issues copying Komodo.app. The HACK:
            # - copy once NOT following symlinks
            # - copy only the MacOS/... bit, this time following
            #   symlinks
            action, src, dst = data
            assert sys.platform == "darwin" and basename(src) == "Komodo.app"
            _run('mkdir -p "%s"' % dirname(dst))
            _run('cp -R -P "%s" "%s"' % (src, dst))
            src2 = join(src, "Contents", "MacOS")
            dst2 = join(dst, "Contents", "MacOS")
            _run('rm -rf "%s"' % dst2)
            _run('%s "%s" "%s"' % (cplink, src2, dst2))
        elif data[0] == "cp":
            action, src, dst = data
            if not dst:
                # Some path factory functions return None to indicate
                # inapplicability on this platform.
                continue 
            if sys.platform == "win32":
                if isdir(src):
                    if not exists(dst): 
                        os.makedirs(dst)
                    _run('xcopy /q/s "%s" "%s"' % (src, dst))
                elif '*' in src or '?' in src:
                    if not exists(dst): 
                        os.makedirs(dst)
                    for path in glob.glob(src):
                        _run('copy "%s" "%s"' % (path, dst))
                else:
                    if not exists(dirname(dst)):
                        os.makedirs(dirname(dst))
                    _run('copy "%s" "%s"' % (src, dst))
            else:
                if '*' in src or '?' in src:
                    _run('mkdir -p "%s"' % dst)
                    for path in glob.glob(src):
                        _run('%s "%s" "%s"' % (cplink, path, dst))
                else:
                    _run('mkdir -p "%s"' % dirname(dst))
                    _run('%s "%s" "%s"' % (cplink, src, dst))
        elif data[0] == "mv":
            action, src, dst = data
            if exists(dst):
                raise Error("can't move '%s' to '%s': '%s' exists"
                            % (src, dst, dst))
            if sys.platform == "win32":
                _run('move "%s" "%s"' % (src, dst))
            else:
                _run('mv "%s" "%s"' % (src, dst))
        elif data[0] == "rm":
            action, pattern = data
            if sys.platform == "win32":
                assert ' ' not in pattern,\
                    "cannot yet handle a space in '%s'" % pattern
                _run("del /q %s" % pattern)
            else:
                _run('rm -f "%s"' % pattern)
        elif data[0] == "rmdir":
            action, pattern = data
            if sys.platform == "win32":
                assert ' ' not in pattern,\
                    "cannot yet handle a space in '%s'" % pattern
                _run("rd /s /q %s" % pattern)
            else:
                _run('rm -rf "%s"' % pattern)
        elif data[0] == "trim":
            # like 'rm' but doesn't error out if doesn't exist on Win
            action, pattern = data
            if sys.platform == "win32":
                assert ' ' not in pattern,\
                    "cannot yet handle a space in '%s'" % pattern
                if glob.glob(pattern):
                    _run("del /q %s" % pattern)
            else:
                _run('rm -f "%s"' % pattern)
        elif data[0] == "rtrim": # recursively trim given pattern
            action, pattern = data
            if sys.platform == "win32":
                cmd = "del /s/q %s || exit 0" % pattern
                _run_in_dir(cmd, cfg.installRelDir)
            elif sys.platform.startswith("sunos"):
                # Solaris' 'find' and 'xargs' generally do not support
                # '-print0' and '-0', respectively.
                for dirpath, dirnames, filenames in os.walk(cfg.installRelDir):
                    for filepath in glob.glob(join(dirpath, pattern)):
                        os.unlink(filepath)
            else:
                cmd = 'find . -name "%s" -print0 | xargs -0 -n1 rm -f' % pattern
                _run_in_dir(cmd, cfg.installRelDir)
        elif data[0] == "rmemptydirs":
            #XXX Note that this removed a dir like:
            #     lib/mozilla/extensions/{972ce4c6-7e08-4474-a285-3208198ce6fd}
            #    Are we sure we want to do that?
            action, dname = data
            _rmemptydirs(dname)

    #---- Some manual fixes
    # The copying above destroyed this symlink in ".../lib/mozilla":
    #   libpythonX.Y.so -> libpythonX.Y.so.1.0
    # Having two independent libpythonX.Y.so's results in the following
    # on Solaris:
    #   Fatal Python error: Interpreter not initialized (version mismatch?)
    # when doing PyXPCOM registration on startup. I don't know why on
    # Solaris and not on Linux. Restore the symlink for both.
    if sys.platform not in ("win32", "darwin"):
        libpythonXYso = iicorepath("lib", "mozilla",
                                   "libpython%s.so" % cfg.siloedPyVer)
        _run("rm -f "+libpythonXYso)
        _run_in_dir("ln -s %s.1.0 %s"
                    % (basename(libpythonXYso), basename(libpythonXYso)),
                    dirname(libpythonXYso))

    # Ensure that there is a <image>/lib/mozilla/extensions directory
    # (bug 42497).
    extensions_dir = iimozbinpath("extensions")
    if not exists(extensions_dir):
        os.makedirs(extensions_dir)

def _PackageKomodoDMG(cfg):
    from os.path import join, isdir, exists, dirname, basename
    print "packaging Komodo 'DMG'..."
    assert sys.platform == "darwin",\
        "'DMG' build on non-Mac OS X doesn't make sense"

    # Make sure "bk image" has been run.
    landmark = join(cfg.installRelDir, cfg.macKomodoAppName)
    assert exists(landmark),\
        "no install image, run 'bk image': '%s' does not exist" % landmark

    # Assert that we have at least osxpkg v2.8.6 (the version when 
    # Komodo IDE 4.2 DMG template was fixed to be big enough).
    osxpkg_ver = os.popen("osxpkg --version").read().strip().split()[1]
    osxpkg_ver_tuple = tuple(map(int, osxpkg_ver.split('.')))
    assert osxpkg_ver_tuple >= (2,8,6), \
        "osxpkg is < 2.8.6: require >=2.8.6 for Komodo DMG template fixes: %r" \
        % osxpkg_ver

    template = "Komodo-%s-%s" % (cfg.prettyProductType,
                                 cfg.komodoMarketingShortVersion)
    pkgPath = cfg.komodoInstallerPackage
    if exists(pkgPath):
        _run("rm %s" % pkgPath)
    if not exists(dirname(pkgPath)):
        os.makedirs(dirname(pkgPath))
    _run("osxpkg mkdmg -T %s %s %s" % (template, pkgPath, cfg.installRelDir))
    print "created '%s'" % pkgPath


def _PackageKomodoASPackage(cfg):
    from os.path import join, isdir, exists, dirname, basename
    print "packaging 'AS Package'..."
    assert sys.platform != "win32",\
        "'AS Package' build doesn't support Windows yet"

    # Make sure "bk image" has been run.
    landmark = join(cfg.installRelDir, "INSTALLDIR", "lib",
                    "mozilla", "komodo")
    assert exists(landmark),\
        "no install image, run 'bk image': '%s' does not exist" % landmark

    pkgPath = cfg.installRelDir+".tar.gz"
    pkgName = basename(cfg.installRelDir)
    cmd = "tar czf %s %s" % (basename(pkgPath), pkgName)
    if exists(pkgPath):
        _run("rm %s" % pkgPath)
    _run_in_dir(cmd, dirname(pkgPath))
    if not isdir(cfg.packagesRelDir):
        os.makedirs(cfg.packagesRelDir)
        
    _run("cp --preserve=timestamps %s %s"
         % (pkgPath, cfg.komodoInstallerPackage))
    print "created '%s'" % cfg.komodoInstallerPackage


def _PackageKomodoMSI(cfg):
    from os.path import join, isdir, exists, dirname, basename
    print "packaging Komodo MSI..."
    assert sys.platform == "win32",\
        "MSI build + %s no makie sense" % sys.platform

    # Make sure "bk image" has been run.
    wrkDir = cfg.installRelDir
    landmark = join(wrkDir, "feature-core", "INSTALLDIR", "lib",
                    "mozilla", "komodo.exe")
    assert exists(landmark),\
        "no install image, run 'bk image': '%s' does not exist" % landmark

    # Copy the MSI build/support bits over to the working dir.
    print "---- copy over MSI build/support bits"
    wixBitsDir = os.path.join(cfg.buildRelDir, "install", "wix")
    _run("xcopy /e/q/y %s %s" % (wixBitsDir, wrkDir))
    _run("copy /y %s %s"
         % (join("src", "install", "startw.exe"), join(wrkDir, "startw.exe")))
    _run("copy /y %s %s"
         % (join("src", "install", "rmtree", "rmtreew.exe"),
            join(wrkDir, "rmtreew.exe")))
    _run("copy /y %s %s"
         % (join(cfg.buildRelDir, "docs", "license", "LICENSE.rtf"),
            join(wrkDir, "aswixui", "License.rtf")))

    # Run "autowix" to configure the WiX sources.
    # (I.e., convert '*.wxs.in' to '*.wxs'.)
    _run_in_dir("python bin\\autowix.py --force", wrkDir)

    # Use "wax.py" (WiX project file update tool) to see if the WiX
    # Project files are out of date. If wax generates any
    # "feature-*-wax.wxs" files then we need to incorporate those
    # changes.
    print "---- see if WiX Project files are out of date"
    pattern = join(wrkDir, "feature-*-wax.wxs")
    if glob.glob(pattern):
        _run("del /f/q %s" % pattern)
    wax = join("src", "install", "wix", "bin", "wax.py")
    cmd = "python %s --project-file *.wxs --write-files" % abspath(wax)
    _run_in_dir(cmd, wrkDir)
    updates = glob.glob(pattern)
    if updates:
        raise Error("""\
The Komodo WiX Project files are out of date. I.e. there are
new files in the Komodo install image that are not included in the
WiX project files. You need to incorporate these WiX fragment(s)
into the appropriate .wxs files in "src/install/wix":

    %s
""" % '\n    '.join(updates))

    print "---- build the MSI"
    #XXX Hack for finding 'nmake'.
    nmake = r"C:\Program Files\Microsoft Visual Studio\VC98\Bin\nmake.exe"
    if not exists(nmake):
        raise Error("don't know where 'nmake' is on your machine")
    cmd = '"PATH=%s;%%PATH%%" && nmake -nologo clean all' % dirname(nmake)
    _run_in_dir(cmd, wrkDir)

    print "---- copy MSI to packages dir"
    if not exists(dirname(cfg.komodoInstallerPackage)):
        os.makedirs(dirname(cfg.komodoInstallerPackage))
    shutil.copyfile(join(wrkDir, "komodo.msi"), cfg.komodoInstallerPackage)
    print "'%s' created" % cfg.komodoInstallerPackage




def _PackageKomodoUpdates(cfg):
    print "packaging 'Komodo Updates'..."
    mozupdate = join("util", "mozupdate.py")
    if not isdir(cfg.packagesRelDir):
        os.makedirs(cfg.packagesRelDir)
    wrk_dir = join(cfg.buildRelDir, "pkg_updates")
    if not exists(wrk_dir):
        os.makedirs(wrk_dir)

    # Make sure "bk image" has been run.
    if sys.platform == "win32":
        landmark = join(cfg.installRelDir, "feature-core", "INSTALLDIR",
                        "lib", "mozilla", "komodo.exe")
    elif sys.platform == "darwin":
        landmark = join(cfg.installRelDir, cfg.macKomodoAppName)
    else:
        landmark = join(cfg.installRelDir, "INSTALLDIR", "lib",
                        "mozilla", "komodo")
    assert exists(landmark),\
        "no install image, run 'bk image': '%s' does not exist" % landmark

    # The install image to work from.
    # - On Windows we have to make a copy because it is split into multiple
    #   dirs for WiX building.
    if sys.platform == "win32":
        image_dir = join(wrk_dir, "image_for_updates")
        if not exists(image_dir):
            log.info("create merged install image in `%s'" % image_dir)
            os.makedirs(image_dir)
            for feature_dir in glob.glob(join(cfg.installRelDir, "feature-*")):
                if '.' in basename(feature_dir): continue
                if not isdir(feature_dir): continue
                _run('xcopy /s/q "%s\\INSTALLDIR" "%s"'
                     % (feature_dir, image_dir))
    elif sys.platform.startswith("linux"):
        image_dir = join(cfg.installRelDir, "INSTALLDIR")
    elif sys.platform.startswith("darwin"):
        image_dir = join(cfg.installRelDir,
                         "Komodo %s.app" % cfg.prettyProductType)
    else:
        raise Error("don't know install image dir for platform %r"
                    % sys.platform)
    log.debug("image dir (for updates): '%s'", image_dir)

    # (Bug 71493) Ensure that the relocated bits of the siloed Python
    # on Linux are never *patched* by a partial update (because the MD5
    # check will always fail).
    mozupdate_clobber_arg = ""
    if cfg.platform == "linux":
        mozupdate_clobber_arg = " ".join([
            r"-c lib/python/bin/python2.5",
            r"-c lib/python/bin/python2.5-config",
            r"-c lib/python/bin/python-config",
            r"-c lib/python/lib/python2.5/config/Makefile",
            r"-c lib/python/lib/python2.5/site-packages/activestate.py",

            # This is only needed for the 4.2.0 (final) release to ensure
            # that the Linux partial update 4.2b7 -> 4.2 works. See bug
            # 72119 for details.
            r"-c bin/komodo",
        ])

    # Partial update package(s).
    guru = pkgutils.KomodoReleasesGuru(
        cfg.buildPlatform, cfg.prettyProductType, cfg.komodoVersion)
    mar_cacher = pkgutils.KomodoMarCacher()

    # - Always want a partial update relative to last build in devbuilds
    #   (for nightly channel). E.g.:
    #   Komodo-IDE-4.2.0-beta2-123456-win32-x86-partial-4.2.0-beta2-123455.mar
    ref_mar_path = guru.last_dev_complete_mar(ignore_changenum=cfg.buildNum)
    if ref_mar_path:
        ref_mar_dir = mar_cacher.get_image_for_mar_path(ref_mar_path)
        ref_mar_ver = guru.version_from_mar_path(ref_mar_path)
        pkg_name = "%s-partial-%s.mar" % (cfg.komodoPackageBase, ref_mar_ver)
        pkg_path = join(cfg.packagesRelDir, pkg_name)
        _run('python %s -q partial %s --force %s "%s" "%s"'
             % (mozupdate, mozupdate_clobber_arg,
                pkg_path, ref_mar_dir, image_dir))
        print "created '%s' (for 'nightly' channel)" % pkg_path
        
        # ...and a changelog for this.
        changelog_path = join(cfg.packagesRelDir,
            "%s-partial-%s.html" % (cfg.komodoPackageBase, ref_mar_ver))
        start_rev = guru.changenum_from_mar_path(ref_mar_path) + 1
        end_rev = guru.changenum_from_mar_path(pkg_path)
        html = changelog.changelog_html(start_rev, end_rev)
        open(changelog_path, 'w').write(html)
        print "created '%s'" % changelog_path
    else:
        log.warn("no previous dev complete .mar exists: skipping build of "
                 "partial update package for *nightly* channel")
    
    # - For betas *and* finals, want a partial update relative to the last
    #   released package, beta or not (for beta channel). Note: alphas
    #   count as a "beta" here, i.e. "beta" == "pre-release".
    ref_mar_path = guru.last_release_complete_mar
    if not buildutils.remote_exists(ref_mar_path):
        log.warn("`%s' does not exist: skipping build of partial "
                 "update package for *beta* channel", ref_mar_path)
    else:
        ref_mar_dir = mar_cacher.get_image_for_mar_path(ref_mar_path)
        ref_mar_ver = guru.version_from_mar_path(ref_mar_path)
        pkg_name = "%s-partial-%s.mar" % (cfg.komodoPackageBase, ref_mar_ver)
        pkg_path = join(cfg.packagesRelDir, pkg_name)
        _run('python %s -q partial %s --force %s "%s" "%s"'
             % (mozupdate, mozupdate_clobber_arg,
                pkg_path, ref_mar_dir, image_dir))
        print "created '%s' (for 'beta' channel)" % pkg_path
    
    # - For non-betas, want a partial update relative to the last released
    #   non-beta (for release channel).
    ver_bits = cfg.komodoVersion.split('-')
    is_final = len(ver_bits) == 1
    if is_final and (guru.last_final_release_complete_mar
                     != guru.last_release_complete_mar):
        ref_mar_path = guru.last_final_release_complete_mar
        if not buildutils.remote_exists(ref_mar_path):
            log.warn("`%s' does not exist: skipping build of partial "
                     "update package for *release* channel", ref_mar_path)
        else:
            ref_mar_dir = mar_cacher.get_image_for_mar_path(ref_mar_path)
            ref_mar_ver = guru.version_from_mar_path(ref_mar_path)
            pkg_name = "%s-partial-%s.mar" % (cfg.komodoPackageBase, ref_mar_ver)
            pkg_path = join(cfg.packagesRelDir, pkg_name)
            _run('python %s -q partial %s --force %s "%s" "%s"'
                 % (mozupdate, mozupdate_clobber_arg,
                    pkg_path, ref_mar_dir, image_dir))
            print "created '%s' (for 'release' channel)" % pkg_path

    # Complete update package.
    # E.g.: Komodo-IDE-4.2.0-beta2-123456-win32-x86-complete.mar
    pkg_name = "%s-complete.mar" % cfg.komodoPackageBase
    pkg_path = join(cfg.packagesRelDir, pkg_name)
    _run('python %s -q complete --force %s "%s"'
         % (mozupdate, pkg_path, image_dir))
    print "created '%s'" % pkg_path



def GrokKomodo(cfg, argv):
    """Search this Komodo branch using our OpenGrok service

    Usage:
        bk grok <search-terms>
    """
    from urllib import quote
    sys.path.insert(0, "util")
    import desktop
    del sys.path[0]

    if len(argv) < 2:
        log.error("no grok search term given, usage: 'bk grok <search-term>'")
        return 1

    def escape(arg):
        if ' ' in arg:
            return '"' + arg + '"'
        else:
            return arg
    escaped_search_terms = [escape(a) for a in argv[1:]]
    search_term = ' '.join(escaped_search_terms)

    url = "http://plow.activestate.com/source/search?q=%s&path=%s"\
          % (quote(search_term), quote("/depot/main/Apps/"+cfg.branch))
    desktop.open(url)


def PackageKomodo(cfg, argv):
    """Build Komodo packages.

    Usage:
        bk package [<package-names...>]
    
    Packages:
        installer       the native installer package (can also use
                        'msi', 'dmg', 'aspackage' aliases on the
                        appropriate platform)
        docs            a zip-up of the Komodo docs
        mozpatches      a zip of the Mozilla patches for the used moz build
        updates         update package(s) for the autoupdate system

    Sets of packages:
        std             (the default) The standard set of packages for
                        this configuration.  
        all             all known packages
    
    """
    args = argv[1:] or ["std"]
    if "all" in args:
        packages = ["installer", "docs", "mozpatches", "updates"]
    elif "std" in args:
        packages = ["installer"]
        if cfg.productType == "ide":
            if sys.platform == "win32":
                # Only build the doc packages on Windows: only need one
                # and multiples cause collisions when uploading to
                # network share (crimper).
                packages.append("docs")
                packages.append("mozpatches")
            # Put this *after* the possible doc packages, because building
            # these packages is the least reliable and I don't want
            # their breakage to break building the doc packages.
        #XXX Disable building update packages temporarily to build
        #    beta1 RC's.
        #XXX Re-enabling for quick builds.
        packages.append("updates")
    else:
        packages = args

    if sys.platform == "win32":    installerName = "msi"
    elif sys.platform == "darwin": installerName = "dmg"
    else:                          installerName = "aspackage"

    for package in packages:
        retval = None
        if package == "docs":
            retval = _PackageKomodoDocs(cfg)
        elif package == "mozpatches":
            retval = _PackageKomodoMozillaPatches(cfg)
        elif package in ("installer", installerName):
            if sys.platform == "win32":
                retval = _PackageKomodoMSI(cfg)
            elif sys.platform == "darwin":
                retval = _PackageKomodoDMG(cfg) 
            else:
                retval = _PackageKomodoASPackage(cfg)
        elif package == "updates":
            retval = _PackageKomodoUpdates(cfg)
        else:
            raise ValueError("unknown package name: '%s'" % package)
        if retval:
            raise Error("error packaging '%s': retval=%r" % (package, retval))

    _PackageUpdateMd5sums(cfg)


def _PackageUpdateMd5sums(cfg):
    """The "nightly" channel code on the Komodo update server needs a way
    to get the size and MD5 of .mar files that it gives as updates. We'd
    like to get that info via HTTP rather than `ssh` for cleaner deployment
    on production servers. This .md5sums file (which provides the size and
    MD5 for all built packages) provides that.
    """
    md5sums_path = join(cfg.packagesRelDir, cfg.komodoPackageBase + ".md5sums")
    info = []
    pat = join(cfg.packagesRelDir, "*%s*" % cfg.buildNum)
    for path in glob.glob(pat):
        if path == md5sums_path:
            continue
        size = os.stat(path).st_size
        md5sum = md5.new(open(path, 'rb').read()).hexdigest()
        info.append((md5sum, size, basename(path)))

    if exists(md5sums_path):
        os.remove(md5sums_path)
    if info:
        fout = open(md5sums_path, 'w')
        fout.write('\n'.join("%s %s %s" % i for i in info))
        fout.close()
        log.info("'%s' created", md5sums_path)


def _PackageKomodoDocs(cfg):
    """The Komodo "doc" package is just a simple packaging up of the
    built Komodo doc tree.  This is most useful for the ActiveCD. It can
    also be useful for just separately distributing or viewing the
    Komodo docs.
    """
    from os.path import isdir, join, basename, dirname, exists

    buildDir = os.path.join(cfg.buildRelDir, cfg.docsPackageName)
    print "packaging 'docs' in '%s'" % buildDir
    if os.path.isdir(buildDir):
        _rmtree(buildDir)
    os.makedirs(buildDir)
    _copy(cfg.docDir, buildDir)
    
    # Trim some junk files
    for dirpath, dirnames, filenames in os.walk(buildDir):
        if ".consign" in filenames:
            os.unlink(join(dirpath, ".consign"))

    # Zip it up.
    zipfile = join(cfg.buildRelDir, cfg.docsPackageName+".zip")
    if exists(zipfile):
        os.remove(zipfile)
    cmd = "zip -rq %s %s" % (basename(zipfile), cfg.docsPackageName)
    _run_in_dir(cmd, dirname(zipfile))
    
    # Copy it to packages dir.
    if not isdir(cfg.packagesAbsDir):
        os.makedirs(cfg.packagesAbsDir)
    dst = join(cfg.packagesRelDir, basename(zipfile))
    _copy(zipfile, dst)
    print "created '%s'" % dst

def _PackageKomodoMozillaPatches(cfg):
    """The Komodo "mozpatches" package is just a simple packaging up of the
    mozilla patches applied to the moz build for the used moz build. This is
    put up here: http://aspn.activestate.com/ASPN/Mozilla/

    Moz builds put a "mozilla-patches-<id>.zip" up in
    "\\crimper\apps\Komodo\support\mozilla-builds". Currently we just
    find the right one and rename it.
    
    As per bug 68441 we may want to remove some bits from that zip.
    """
    buildDir = os.path.join(cfg.buildRelDir, cfg.mozPatchesPackageName)
    print "packaging 'mozpatches' in '%s'" % buildDir
    if os.path.isdir(buildDir):
        _rmtree(buildDir)

    # Get the raw patches from the moz build.
    raw_patches_dir = glob.glob(join(cfg.mozSrc, "mozilla-patches-*"))[0]
    if sys.platform == "win32":
        os.makedirs(buildDir)
        _run("xcopy /e /q /y %s %s" % (raw_patches_dir, buildDir), log.info)
    else:
        _run("cp -R %s %s" % (raw_patches_dir, buildDir), log.info)
    
    # Trim out some Komodo-specific bits.
    to_trim = [
        "komodo_app",
        "komodo*patch",
        join("*", "komodo*patch"),
    ]
    for subpath in to_trim:
        path_pattern = join(buildDir, subpath)
        for path in _paths_from_path_patterns([path_pattern], recursive=False,
                                              dirs="always"):
            log.info("rm %s", path)
            if sys.platform != "win32":
                _run("rm -rf %s" % path, log.debug)
            elif isdir(path):
                _run("rd /s/q %s" % path, log.debug)
            elif exists(path):
                os.remove(path)
    
    # Zip it up.
    zipfile = join(cfg.buildRelDir, cfg.mozPatchesPackageName+".zip")
    if exists(zipfile):
        os.remove(zipfile)
    cmd = "zip -rq %s %s" % (basename(zipfile), cfg.mozPatchesPackageName)
    _run_in_dir(cmd, dirname(zipfile))
    
    # Copy it to packages dir.
    if not isdir(cfg.packagesAbsDir):
        os.makedirs(cfg.packagesAbsDir)
    dst = join(cfg.packagesRelDir, basename(zipfile))
    _copy(zipfile, dst)
    print "created '%s'" % dst


def JarChrome(chromeTree, cfg, argv):
    out.write("Jarring chrome.\n")
    if sys.platform.startswith("win"):
        zipExe = os.path.join(cfg.komodoDevDir, "bin", "zip.exe")
    else:
        zipExe = tmShUtil.Which("zip")

    if hasattr(cfg, "installerType"):
        if sys.platform == 'darwin':
            chromeDir = os.path.join(cfg.installAbsDir, "Komodo.app",
                                       "Contents", "MacOS", "chrome", chromeTree)
        else:
            chromeDir = os.path.join(cfg.installAbsDir, "INSTALLDIR",
                                       "Mozilla", "chrome", chromeTree)
    else:
        #XXX Could cfg.mozChromeDir not just be used to installer
        #    builds as well? This is what Construct::RegisterChrome
        #    does.
        chromeDir = os.path.join(cfg.mozChromeDir, chromeTree)
    if os.path.isdir(chromeDir):
        oldDir = os.getcwd()
        try:
            os.chdir(chromeDir)
            jarFile = os.path.join("..", chromeTree+".jar")
            if os.path.isfile(jarFile):
                #XXX Shouldn't have to do this if using "zip -u" but it
                #    refuses to update if (I think this is the reason)
                #    the files to update are somewhere below the
                #    top-level dir (i.e. relying on '-r').
                os.unlink(jarFile)
            cmd = "%s -r -q %s content skin locale" % (zipExe, jarFile)
            out.write("running '%s' in '%s'\n" % (cmd, chromeDir))
            failed = os.system(cmd)
            if failed:
                out.write("\n*** Jarring '%s' chrome tree failed!\n"
                          % chromeTree)
                return failed
        finally:
            os.chdir(oldDir)
            # XXX might not want to unlink in dev builds later on
            if sys.platform == "win32":
                # XXX cannot remove this, so that the komododoc package
                # gets built correctly
                
                #assert ' ' not in chromeDir,\
                #    "cannot yet handle a space in '%s'" % chromeDir
                #_run("rd /s /q %s" % chromeDir)
                pass
            else:
                _run('rm -rf "%s"' % chromeDir)




def GetScintillaSource(cfg, argv):
    """Copy the scintilla source to src/scintilla/... and patch it.

    This is only done if src/scintilla doesn't already exist.
    """
    landmark = join("src", "scintilla", "version.txt")
    if exists(landmark):
        return

    # Copy over clean scintilla sources.
    log.info("copy clean scintilla sources in src/scintilla")
    _cp(join("contrib", "scintilla"), join("src", "scintilla"))

    # Find a sane patch executable.
    # - on Windows the cygwin patch can do screwy things
    # - on Solaris /usr/bin/patch isn't good enough (note that we
    #   usually *do* have GNU patch at /usr/local/bin/patch).
    ko_bin_dir = join("util", "bin-"+platinfo.platname())
    try:
        patch_exe = which.which("patch", path=[ko_bin_dir])
    except which.WhichError:
        try:
            patch_exe = which.which("patch")
        except which.WhichError:
            raise Error("Could not find a 'patch' executable.")

    # Patch it with patches in "contrib/patches/scintilla".
    patchtree.log.setLevel(logging.INFO)
    patchtree.patch([join("contrib", "patches", "scintilla")],
                    join("src", "scintilla"),
                    config=cfg,
                    #dryRun=1,  # uncomment this line to dry-run patching
                    logDir=join(cfg.buildAbsDir, "scintilla-patch-log"),
                    patchExe=patch_exe)


def BuildKomodo(cfg, argv):
    if "jarxtk" in argv:
        return JarChrome("xtk", cfg, argv)
    if "jarkomodo" in argv:
        return JarChrome("komodo", cfg, argv)
    if "jardocs" in argv:
        return JarChrome("komododoc", cfg, argv)
    if "rebuildquickdb" in argv:
        return BuildQuickBuildDB(cfg, argv)
    if "quickdump" in argv:
        return DumpQuickBuildDB(cfg, argv)
    if "quick" in argv:
        out.write("*** Doing quick build -- not everything will be rebuilt! ***\n")
        return QuickBuild(cfg, argv, pickle.load(open('qbtable.pik', 'r')))
    if "scintilla_src" in argv:
        return GetScintillaSource(cfg, argv)
    if "package_md5sums" in argv:
        return _PackageUpdateMd5sums(cfg)

    # Get and patch the scintilla source if necessary.
    retval = GetScintillaSource(cfg, argv)

    # Build Komodo
    if not retval:
        perlExe = (sys.platform == "win32"
                   and cfg.nonMsysPerl
                   or cfg.unsiloedPerlExe)
        retval = tmShUtil.RunInContext(cfg.envScriptName,
            [ "%s %s %s" % (perlExe,
                            os.path.join(cfg.komodoDevDir, "bin", "cons.pl"),
                            #XXX should escape args with spaces
                            " ".join(argv[1:])) ]
            )
    if not retval and cfg.jarring:
        retval = JarChrome("xtk", cfg, argv)
    if not retval and cfg.jarring:
        retval = JarChrome("komodo", cfg, argv)
    if not retval and cfg.withDocJarring:
        retval = JarChrome("komododoc", cfg, argv)
    if not retval:
        BuildQuickBuildDB(cfg, argv)
    return retval

def CleanKomodoBuild(cfg, argv):
    """Try to clean out move of the Komodo build bits."""
    from os.path import abspath, join, isdir, isfile
    def mozpath(*parts): return join(cfg.mozSrc, *parts)
    def mozdistpath(*parts): return mozpath(cfg.mozDist, *parts)
    def mozbinpath(*parts): return join(cfg.mozBin, *parts)
    bits = [
        cfg.buildAbsDir,
        cfg.installAbsDir,
        abspath(cfg.exportRelDir),
        mozdistpath("komodo-bits"),

        mozbinpath("python", "komodo"),
        mozbinpath("python", "komodo.pth"),
        mozbinpath("is_dev_tree.txt"),

        mozbinpath("chrome", "app-chrome.manifest"),
        mozbinpath("chrome", "icons"),
        mozbinpath("chrome", "jaguar"), # for old time sakes
        mozbinpath("chrome", "jaguar.manifest"),
        mozbinpath("chrome", "xtk"),
        mozbinpath("chrome", "xtk.jar"),
        mozbinpath("chrome", "xtk.manifest"),
        mozbinpath("chrome", "ascore"),
        mozbinpath("chrome", "ascore.jar"),
        mozbinpath("chrome", "ascore.manifest"),
        mozbinpath("chrome", "komodo"),
        mozbinpath("chrome", "komodo.jar"),
        mozbinpath("chrome", "komodo.manifest"),
        mozbinpath("chrome", "komododoc"),
        mozbinpath("chrome", "komododoc.jar"),
        mozbinpath("chrome", "komododoc.manifest"),
        mozbinpath("components", "ko*.py"),
        mozbinpath("components", "ko*.pyo"),
        mozbinpath("components", "ko*.xpt"),
        mozbinpath("components", "ISciMoz*"),
        mozbinpath("components", "as*.xpt*"),
        mozbinpath("components", "as*.js"),
        mozbinpath("extensions"),

        mozbinpath("plugins", "SciMoz.plugin"), # its name on OS X
        #TODO:
        # - SciMoz plugin on other plats
    ]

    for bit in bits:
        paths = glob.glob(bit)
        if paths:
            out.write("remove '%s'\n" % bit)
            for path in paths:
                if sys.platform == "win32":
                    if isdir(path):
                        _run('rd /s/q "%s"' % path)
                    else:
                        _run('attrib -R "%s"' % path)
                        _run('del "%s"' % path)
                else:
                    _run('rm -rf "%s"' % path)


def RunKomodo(cfg, argv):
    if sys.platform == "darwin":    # No komodo starter stub on Mac OS X.
        if not os.path.exists(cfg.mozExe):
            raise black.BlackError("can't run Komodo: 'mozExe' does not "
                                   "exist: '%s'" % cfg.mozExe)
        cmd = cfg.mozExe
    elif sys.platform == "win32":   # Run the subsystem:console stub.
        cmd = os.path.join(cfg.stubDir, "ko.exe")
    else:                           # Run komodo starter stub.
        cmd = os.path.join(cfg.stubDir, "komodo")

    for arg in argv[1:]:
        if " " in arg:
            cmd += ' "%s"' % arg
        else:
            cmd += ' %s' % arg
    return tmShUtil.RunInContext(cfg.envScriptName, [ cmd ])

def CleanPreferences(cfg, argv):
    """remove Komodo and Mozilla preference files
    These must be kept in sync with the directory naming in koDirs,
    or maybe I could acutally query koDirs.
    """
    if len(argv) != 2:
        raise black.BlackError("Wrong number of arguments to 'clean'. You "\
            "have to specify one argument, namely what preferences to "\
            "clean: 'komodo' or 'mozilla'.")    
    else:
        what = argv[1]

    toDelete = []
    if sys.platform.startswith("win"):
        from win32com.shell import shellcon, shell
        ##  XXX win32com.shellcon is missing CSIDL_COMMON_APPDATA
        shellcon.CSIDL_COMMON_APPDATA = 0x23
    if what.startswith("ko"):
        #---- komodo preference files
        if sys.platform.startswith("win"):
            base = str(shell.SHGetFolderPath(0, shellcon.CSIDL_APPDATA,
                                             0, 0))
            toDelete.append(os.path.join(base, "ActiveState", "Komodo"))
            base = str(shell.SHGetFolderPath(0, shellcon.CSIDL_COMMON_APPDATA,
                                             0, 0))
            toDelete.append(os.path.join(base, "ActiveState", "Komodo"))
        elif sys.platform == 'darwin':
            from Carbon import Folder, Folders
            for domain in (Folders.kUserDomain, Folders.kLocalDomain):
                base = Folder.FSFindFolder(domain,
                    Folders.kApplicationSupportFolderType,
                    Folders.kDontCreateFolder)
                dir = os.path.join(base.FSRefMakePath(), "Komodo")
                toDelete.append(dir)
        else:
            toDelete.append(os.path.expanduser("~/.komodo"))
            toDelete.append("/etc/komodo")
    elif what.startswith("moz"):
        #---- mozilla prefs dir
        import socket
        hostsubdir = "host-"+socket.gethostname()
        if sys.platform.startswith("win"):
            for csidl in (shellcon.CSIDL_APPDATA, shellcon.CSIDL_COMMON_APPDATA):
                for subdir in ("Mozilla", "XRE"):
                    path = os.path.join(
                        str(shell.SHGetFolderPath(0, csidl, 0, 0)),
                        "ActiveState", "Komodo", cfg.komodoShortVersion,
                        hostsubdir, subdir)
                    toDelete.append(path)
        elif sys.platform == 'darwin':
            from Carbon import Folder, Folders
            for domain in (Folders.kUserDomain, Folders.kLocalDomain):
                for subdir in ("Mozilla", "XRE"):
                    base = Folder.FSFindFolder(domain, 
                        Folders.kApplicationSupportFolderType,
                        Folders.kDontCreateFolder)
                    path = os.path.join(base.FSRefMakePath(),
                        "Komodo", cfg.komodoShortVersion, hostsubdir, subdir)
                    toDelete.append(path)
        else:
            for subdir in ("Mozilla", "XRE"):
                path = os.path.join(os.path.expanduser("~/.komodo"),
                    cfg.komodoShortVersion, hostsubdir, subdir)
                toDelete.append(path)
    # delete files
    numDeleted = 0
    for fname in toDelete:
        if os.path.isfile(fname):
            out.write("deleting '%s'...\n" % fname)
            os.unlink(fname)
            numDeleted += 1
        elif os.path.isdir(fname):
            out.write("deleting '%s'...\n" % fname)
            shutil.rmtree(fname)
            numDeleted += 1
        else:
            out.write("'%s' does not exist...\n" % fname)
    if numDeleted == 0:
        out.write("nothing to remove\n")


def TestKomodo(cfg, argv):
    import tmShUtil
    return tmShUtil.RunInContext(cfg.envScriptName,
                ['cd test',
                 'python test.py %s' % ' '.join(argv[1:])])

def TestKomodoPerf(cfg, argv):
    # Change to the test directory (in the _install_ tree)
    # and call perf.py.
    import tmShUtil
    cmd = "python perf.py %s" % " ".join(argv[1:])
    import bkconfig
    if sys.platform == 'darwin':
        testDir = os.path.join(bkconfig.installAbsDir, "Komodo.app", "Contents",
                               "SharedSupport", "test")
    else:
        testDir = os.path.join(bkconfig.installAbsDir, "INSTALLDIR", "test")
    return tmShUtil.RunInContext(cfg.envScriptName,
                                 [ 'cd "%s"' % testDir, cmd ])

def _addExtensionFiles(cfg, sourceSubdir, targetSubdir, extensions, preserveSubtrees=0,
              targetSubdirPattern=None):
    if not os.path.exists(sourceSubdir):
        return
    # our extensions in src are just the name, but get installed to name@ActiveState.com
    dirlist = os.listdir(sourceSubdir)
    modules = {}
    for dir in dirlist:
        if os.path.isdir(os.path.join(sourceSubdir, dir)):
            modules[dir] = "%s@ActiveState.com"%dir
    for srcDir, targetDir in modules.items():
        _addFiles(cfg, sourceSubdir='%s/%s' % (sourceSubdir,srcDir),
                  targetSubdir=os.path.join(cfg.mozBin, 'extensions', targetDir),
                  extensions=['xul', 'xml', 'js', 'css', 'dtd', 'gif', 'png', 'html', 'py'],
                  preserveSubtrees=1)
        

def _addFiles(cfg, sourceSubdir, targetSubdir, extensions, preserveSubtrees=0):
    count = 0
    sourceSubdir = os.path.normpath(os.path.abspath(sourceSubdir))
    
    # XXX find on osx doesn't build paths correctly, hack around it
    if sys.platform != 'darwin':
        sourceSubdir += os.sep
    
    assert targetSubdir

    # find possible files of interest
    possibles = []
    for extension in extensions:
        if sys.platform[:3] == 'win':
            cmd = "DIR %(sourceSubdir)s /A-D /S /B | grep \\.%(extension)s" % locals()
        else:
            cmd = "find %(sourceSubdir)s -name '*.%(extension)s'" % locals()
        possibles += os.popen(cmd).readlines()
    possibles = [line[:-1] for line in possibles if line[-1] == '\n']
    # XXX find on osx doesn't build paths correctly, hack around it
    if sys.platform == 'darwin':
        sourceSubdir += os.sep

    # determine target location for files
    for possible in possibles:
        if preserveSubtrees:
            # We are working with files which maintain their subdirectory
            # structure in the target subtree.
            target = os.path.normpath(os.path.join(targetSubdir, possible[len(sourceSubdir):]))
        else:
            # We are working with files which are in one of the target
            # subdirectories.
            target = os.path.normpath(os.path.join(targetSubdir, os.path.basename(possible)))
        pext = os.path.splitext(os.path.splitext(target)[0])[1]
        if pext in [".unprocessed", ".p"]:
            # This is a file that will be run through the preprocessor and
            # whose actual target name should drop the ".unprocessed".
            base, ext = os.path.splitext(target)
            base = os.path.splitext(base)[0]
            target = base + ext
        if os.path.exists(target):
            _table[possible] = (os.path.abspath(target), md5.new(open(possible, 'rb').read()).hexdigest())
            count += 1
    #print 'Found %d %s files in %s' % (count, extensions, sourceSubdir)
    
def BuildQuickBuildDB(cfg, argv):
    if sys.platform == 'darwin':
        sharedSupportRelDir = "Komodo.app/Contents/SharedSupport"
    else:
        sharedSupportRelDir = "INSTALLDIR"
    print "Building 'bk build quick' cache from installed copy."
    _addFiles(cfg, sourceSubdir='src/chrome/',
              targetSubdir=os.path.join(cfg.mozBin, 'chrome'),
              extensions=['xul', 'xml', 'js', 'css', 'dtd', 'gif', 'png', 'html', 'rdf'],
              preserveSubtrees=1)
    _addExtensionFiles(cfg, sourceSubdir='src/modules/',
              targetSubdir=os.path.join(cfg.mozBin, 'extensions'),
              extensions=['xul', 'xml', 'js', 'css', 'dtd', 'gif', 'png', 'html', 'py'],
              preserveSubtrees=1)
    _addFiles(cfg, sourceSubdir='src/',
              targetSubdir=os.path.join(cfg.mozBin, 'components'),
              extensions=['py', 'js'])
    _addFiles(cfg, sourceSubdir='src/',
              targetSubdir=cfg.komodoPythonUtilsDir,
              extensions=['py'])
    # This _addFiles will result in redundantly adding
    # src/python-sitelib/*.py but is the only easy way to properly get
    # src/python-sitelib/.../*.py into the Quick Build DB.
    _addFiles(cfg, sourceSubdir='src/python-sitelib',
              targetSubdir=cfg.komodoPythonUtilsDir,
              extensions=['py'],
              preserveSubtrees=1)
    _addFiles(cfg, sourceSubdir='src/codeintel/lib',
              targetSubdir=cfg.komodoPythonUtilsDir,
              extensions=['py', 'cix'],
              preserveSubtrees=1)
    _addFiles(cfg, sourceSubdir='src/schemes',
              targetSubdir=os.path.join(cfg.supportDir, "schemes"),
              extensions=['kkf', 'ksf'],
              preserveSubtrees=1)
    _addFiles(cfg, sourceSubdir='src/images/icons/xpm',
              targetSubdir=os.path.join(cfg.mozBin, 'chrome', 'komodo', 'skin', 'images'),
              extensions=['xpm'],
              preserveSubtrees=1)
    pickle.dump(_table, open('qbtable.pik', 'w'))

def DumpQuickBuildDB(cfg, argv):
    sys.stderr.write("Dumping quick build cache...\n");
    cache = pickle.load(open('qbtable.pik', 'r'))
    for source, (target, checksum) in cache.items():
        print "%s (%s): %s" % (source, checksum, target)

def QuickBuild(cfg, argv, _table):
    todo = []
    for source, (target, oldmd5) in _table.items():
        # We don't just want > because p4 revert (and possibly `hg
        # revert') brings the date back.
        if os.path.isfile(target):
            newmd5 = md5.new(open(source, 'rb').read()).hexdigest()
            if newmd5 != oldmd5:
                todo.append((source, target))
                _table[source] = (target, newmd5)
    if not len(todo):
        print "quick build: No need to copy any files."
    else:
        print "Need to (possibly preprocess and) copy %d files" % (len(todo))
        sys.path.insert(0, "util")
        import preprocess
        sys.path.pop(0)
        for source, target in todo:
            pext = os.path.splitext(os.path.splitext(source)[0])[1]
            if pext in [".unprocessed", ".p"]:
                print "Preprocess %s and copy to %s" % (source, target)
                
                preprocess.preprocess(source, target,
                                      defines={"PLATFORM": cfg.platform,
                                               "PRODUCT_TYPE": cfg.productType,
                                               "MOZILLA_VERSION": cfg.mozVersion,
                                               "BUILD_FLAVOUR": cfg.buildFlavour,
                                               "WITH_CRYPTO": cfg.withCrypto,
                                               "WITH_CASPER": cfg.withCasper},
                                      force=1,
                                      keepLines=1,
                                      substitute=True)
            else:
                print "Copying %s to %s" % (source, target)
                _copy(source, target)

    if cfg.jarring:
        retval = JarChrome("xtk", cfg, argv)
        retval = JarChrome("komodo", cfg, argv)
    if cfg.withDocJarring:
        retval = JarChrome("komododoc", cfg, argv)

    # save the new state of affairs
    pickle.dump(_table, open('qbtable.pik', 'w'))
    print "quick build: done"


commandOverrides = {
    "build": BuildKomodo,
    "run": RunKomodo,
    "cleanprefs": CleanPreferences,
    "clean": CleanKomodoBuild,
    "package": PackageKomodo,
    "test": TestKomodo,
    "perf": TestKomodoPerf,
    "image": ImageKomodo,
    "grok": GrokKomodo,
}





