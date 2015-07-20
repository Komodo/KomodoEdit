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

PKGNAME's are docs, installer (aka msi, dbg, aspackage).
"""

import os, sys, os, shutil
import cPickle as pickle
import time
from os.path import join, dirname, exists, isfile, basename, abspath, \
                    isdir, splitext
from fnmatch import fnmatch
import glob
import shutil
try:
    from hashlib import md5
except ImportError:
    from md5 import md5
import subprocess
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
    import kopkglib
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


# Recipe: splitall (0.2) in C:\trentm\tm\recipes\cookbook
def _splitall(path):
    r"""Split the given path into all constituent parts.

    Often, it's useful to process parts of paths more generically than
    os.path.split(), for example if you want to walk up a directory.
    This recipe splits a path into each piece which corresponds to a
    mount point, directory name, or file.  A few test cases make it
    clear:
        >>> splitall('')
        []
        >>> splitall('a/b/c')
        ['a', 'b', 'c']
        >>> splitall('/a/b/c/')
        ['/', 'a', 'b', 'c']
        >>> splitall('/')
        ['/']
        >>> splitall('C:\\a\\b')
        ['C:\\', 'a', 'b']
        >>> splitall('C:\\a\\')
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


# Recipe: relpath (0.2) in C:\trentm\tm\recipes\cookbook
def _relpath(path, relto=None):
    """Relativize the given path to another (relto).

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

def _short_ver_str_from_ver_info(ver_info):
    def isint(s):
        try:
            int(s)
        except ValueError:
            return False
        else:
            return True

    dotted = []
    for bit in ver_info:
        if bit is None:
            continue
        if dotted and isint(dotted[-1]) and isint(bit):
            dotted.append('.')
        dotted.append(str(bit))
    return ''.join(dotted)    

def _ver_info_from_long_ver_str(long_ver_str):
    """Return a version info tuple for the given long version string.
    
    Examples of a "long" version string are:
        4.0.0-alpha3-12345, 1.2.3-beta-54321, 4.2.5-2598, 5.0.0-43251
    "Short" would be more like:
        4.0.0a3, 1.2.3b, 4.2.5
    
    The returned tuple will be:
        (<major>, <minor>, <patch>, <quality>, <quality-num>, <build-num>)
    where <quality> is a letter ('a' for alpha, 'b' for beta, 'c' if not
    given). <quality-num> and <build-num> default to None. The defaults are
    chosen to make sorting result in a natural order.
    """
    def _isalpha(ch):
        return 'a' <= ch <= 'z' or 'A' <= ch <= 'Z'
    def _isdigit(ch):
        return '0' <= ch <= '9'
    def _split_quality(s):
        for i in reversed(range(1, len(s)+1)):
            if not _isdigit(s[i-1]):
                break
        if i == len(s):
            quality_name, quality_num = s, None
        else:
            quality_name, quality_num = s[:i], int(s[i:])
        quality = {'alpha': 'a', 'beta': 'b', 'rc': 'c', 'devel': 'd'}[quality_name]
        return quality, quality_num

    bits = []
    for i, undashed in enumerate(long_ver_str.split('-')):
        for undotted in undashed.split('.'):
            if len(bits) == 3:
                # This is the "quality" section: 2 bits
                if _isalpha(undotted[0]):
                    bits += list(_split_quality(undotted))
                    continue
                else:
                    bits += ['c', None]
            try:
                bits.append(int(undotted))
            except ValueError:
                bits.append(undotted)
        # After first undashed segment should have: (major, minor, patch)
        if i == 0:
            while len(bits) < 3:
                bits.append(0)
    return tuple(bits)


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
    r"""os.path.isdir() doesn't work for UNC mount points. Fake it."""
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

def _run(cmd, logstream=_RUN_DEFAULT_LOGSTREAM, cwd=None, env=None):
    """Run the given command.

        "cmd" is the command to run
        "cwd" is the directory in which the commmand is run.
        "env" is the optional environment dict to use
        "logstream" is an optional logging stream on which to log the 
            command. If None, no logging is done. If unspecifed, this 
            looks for a Logger instance named 'log' and logs the command 
            on log.debug().

    Raises OSError if the command returns a non-zero exit status.
    """
    if isinstance(cmd, (list, tuple)):
        cmd = list(cmd)
        cmdline = " ".join(cmd)
        shell = False
    else:
        cmdline = str(cmd)
        shell = True
    if cwd is not None:
        __run_log(logstream, "running '%s' in '%s'", cmdline, cwd)
    else:
        __run_log(logstream, "running '%s'", cmdline)
    p = subprocess.Popen(cmd, cwd=cwd, shell=shell, env=env)
    status = p.wait()
    if status:
        #TODO: add std OSError attributes or pick more approp. exception
        raise OSError("error running '%s': %r" % (cmdline, status))

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
    _run(cmd, logstream=None, cwd=cwd)



#---- define the Komodo configuration items

configuration = {
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
    "havePy2to3": HavePy2to3(),     # siloed Python has sufficient lib2to3 support

    "siloedDistutilsLibDirName": SiloedDistutilsLibDirName(), # e.g "lib.win32-2.4"
    "perlVersion": black.configure.std.PerlVersion(perlBinDirItemName="unsiloedPerlBinDir"),
    "activePerlBuild": black.configure.std.ActivePerlBuild(perlBinDirItemName="unsiloedPerlBinDir"),

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
    "MOZBUILD_STATE_PATH": SetMozStatePath(),
    "LD_LIBRARY_PATH": SetLdLibraryPath(),
    # TODO: setup mozLdLibraryPath and have a custom LD_LIBRARY_PATH *or*
    #       setup a generic SetPathEnvVar("LD_LIBRARY_PATH", [list of
    #       configuration items to add to it]),
    # TODO: the same kind of generic this for PATH

    #---- Microsoft Visual Studio setup ----
    "compiler": SetupCompiler(),
    "mozMake": MozMake(),
    "mozGcc": MozGcc(),
    "mozGxx": MozGxx(),
    "mozCFlags": MozCFlags(),
    "mozCxxFlags": MozCxxFlags(),
    "mozLdFlags": MozLdFlags(),
    "mozGreMilestone": MozGreMilestone(),
    "setupMozEnv": SetupMozEnv(),

    #---- komodo stuff
    # TODO: complain if Komodo debug/release conflicts with the debug/release
    #       state of the MOZ_SRC
    "platform": Platform(),
    "architecture": Architecture(),

    # Komodo build/version configuration vars.
    "sourceId": SourceId(),                                         #   e.g., 1234M
    "sccRepoName": "oksvn",                 # openkomodo.com SVN repo
    "sccType": SCCType(),
    "sccBranch": SCCBranch(),               # e.g.: "trunk"
    "sccRepo": SCCRepo(),                   # upstream repo location
    "normSCCBranch": NormSCCBranch(),       # Normalized version.
    # - base variables:                                             # Example:
    "komodoVersion": KomodoVersion(),                               #   3.10.0-alpha1
    "productType": ProductType(),                                   #   ide
    "prettyProductType": PrettyProductType(),                       #   IDE
    "productTagLine": ProductTagLine(),                             #   The professional IDE for dynamic languages
    "buildNum": BuildNum(),                                         #   123456
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
    "macKomodoAppBuildName": MacKomodoAppBuildName(),               # e.g. "Komodo.app"
    "macKomodoAppInstallName": MacKomodoAppInstallName(),           # e.g. "Komodo IDE.app"
    "msiKomodoPrettyId": MSIKomodoPrettyId(),
    "msiVccrtMsmPath": MSIVccrtMsmPath(),
    "msiVccrtRedistPath": MSIVccrtRedistPath(),
    "msiVccrtPolicyMsmPath": MSIVccrtPolicyMsmPath(),

    # OSX packaging:
    "osxCodeSignExecutable": OSXCodeSignExecutable(),
    "osxCodeSigningCert": OSXCodeSigningCert(),

    "komodoPackageBase": KomodoPackageBase(),
    "komodoUpdateManualURL": KomodoUpdateManualURL(),

    "gnomeDesktopName": GnomeDesktopName(),
    "gnomeDesktopGenericName": GnomeDesktopGenericName(),
    "gnomeDesktopCategories": GnomeDesktopCategories(),
    "gnomeDesktopShortcutName": GnomeDesktopShortcutName(),
    
    "buildType": BuildType(),               # "release" or "debug"
    "buildFlavour": BuildFlavour(),         # "dev" or "full"
    "updateChannel": UpdateChannel(),       # "nightly", "beta" or "release"
    "versionInfoFile": VersionInfoFile(),
    "KOMODO_HOSTNAME": SetKomodoHostname(),
    "withSymbols": WithSymbols(),
    "withCrashReportSymbols": WithCrashReportSymbols(),
    "PYTHONPATH": SetPythonPath(), 
    "PYTHONHOME": SetPythonHome(), 
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
    "mozResourcesDir": MozResourcesDir(),
    "mozComponentsDir": MozComponentsDir(),   #XXX necessary?
    "mozChromeDir": MozChromeDir(),   #XXX necessary?
    "mozPluginsDir": MozPluginsDir(), #XXX necessary?
    "mozExtensionDir": MozExtensionDir(),
    "KOMODO_MOZBINDIR": SetMozBinDir(),
    "komodoPythonUtilsDir": KomodoPythonUtilsDir(),  #XXX change to LibDir
    "installRelDir": InstallRelDir(),
    "userDataDir": UserDataDir(),
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
    "testBuildRelDir_ForCons": TestBuildRelDir_ForCons(), 
    "exportRelDir_ForCons": ExportRelDir_ForCons(), 
    "idlExportRelDir_ForCons": IdlExportRelDir_ForCons(), 
    "installAbsDir": InstallAbsDir(),
    "scintillaBuildDir": ScintillaBuildDir(),
    "linuxDistro": LinuxDistro(),
    "komodoInstallerPackage": KomodoInstallerPackage(),
    "configTokens": ConfigTokens(),
    "docsPackageName": DocsPackageName(),
    "mozPatchesPackageName": MozPatchesPackageName(),

    "withTests": WithTests(),
    "withCasper": WithCasper(),
    "withJSLib": WithJSLib(),
    "withDocs": WithDocs(),
    "withKomodoCix": WithKomodoCix(),
    "withWatchdogFSNotifications": WithWatchdogFSNotifications(),

    # PGO builds
    "withPGOGeneration": WithPGOGeneration(),
    "withPGOCollection": WithPGOCollection(),
    
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

def FetchDependentSources(cfg, argv, update=True):
    """get dependent sources we need (svn externals / git submodules)

    bk fetch

        This command takes no arguments.  It will attempt to download the
        required external sources (such as the documentation).
    """

    try:
        if argv[0] in ("--update", "-u"):
            update = True
            argv.pop(0)
        elif argv[0] in ("--no-update", "-n"):
            update = False
            argv.pop(0)
    except IndexError:
        pass # no argv

    if not cfg.sccType:
        # Not under scc... not sure what we are dealing with then.
        # (This might be the case for, e.g., source tarballs)
        return

    children = []
    """< This is a sequence of dicts; each has a name (for display only),
         a dir (where the result will go), and some data about how to get
         the result.  For git repos, the subkey "git" contains the
         mapping from the toplevel git repo to the url for the sub-repo;
         both are relative to the root of the server.
    """

    if cfg.withDocs:
        children.append(
            {   "name": "docs",
                "sccType": "git",
                "dir": join(cfg.komodoDevDir, "contrib", "komododoc"),
                "url": "https://github.com/Komodo/komodo-documentation.git",
            }
        )
    for child in children:
        if child["sccType"] != cfg.sccType:
            continue
        if cfg.sccType == "git":
            repo_url = child["url"]
            if exists(child["dir"]):
                if update:
                    print("Updating git %s in %r" % (child["name"], child["dir"]))
                    _run(["git", "pull", "--rebase"], cwd=child["dir"])
            else:
                if not isdir(dirname(child["dir"])):
                    os.makedirs(dirname(child["dir"]))
                print("Cloning git %s into %r" % (child["name"], child["dir"]))
                _run(["git", "clone", repo_url, child["dir"]])
        else:
            # svn doesn't reach here, svn:externals can do the job
            raise RuntimeError("Don't know how to get %s via %s"
                               % (child["name"], cfg.sccType))


def StripBinaries(topdir):
    """Remove any unnecssary information from the Komodo binaries"""
    import subprocess
    print "Stripping binaries in: %r" % (topdir, )
    if sys.platform.startswith("linux"):
        # First, ensure the binary files we want to update are write-able.
        chmod_cmd = ["find", '"%s"' % (topdir, ), "|",
                     "xargs", "file", "|",
                     "grep", "ELF", "|",
                     "cut", "-f", "1", "-d", ":", "|",
                     "xargs", "chmod", "u+w"]
        _run(" ".join(chmod_cmd))
        # Strip the binaries using the linux strip command.
        strip_cmd = ["find", '"%s"' % (topdir, ), "|",
                     "xargs", "file", "|",
                     "grep", "ELF", "|",
                     "cut", "-f", "1", "-d", ":", "|",
                     "xargs", "strip"]
        try:
            _run(" ".join(strip_cmd))
        except OSError:
            pass   # Ignore errors from trying to strip binaries.

def GenerateCaches(cfg):
    """Generate various cache files for faster loading"""

    # Generate a pickled version of the prefs file - bug 96273.
    import tmShUtil
    oldDir = os.getcwdu()
    cmd = '"%s/mozpython" src/prefs/pref_pickler.py' % (cfg.mozBin,)
    print("running '%s' in '%s'" % (cmd, cfg.komodoDevDir))
    try:
        os.chdir(cfg.komodoDevDir)
        tmShUtil.RunInContext(cfg.envScriptName,
                              [cmd])
        if not exists(join(cfg.supportDir, "prefs.xmlc")):
            raise Error("Failed to generate pickled default prefs")
    finally:
        os.chdir(oldDir)

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
            return ipkgpath(cfg.macKomodoAppInstallName, "Contents", "MacOS", *parts)
        else:
            return ipkgpath("INSTALLDIR", "lib", "mozilla", *parts)
    def iimozresourcespath(*parts):
        """Mac uses Resources folder for most data files."""
        if sys.platform == "darwin":
            return ipkgpath(cfg.macKomodoAppInstallName, "Contents", "Resources", *parts)
        else:
            return iimozbinpath(*parts)
    def iipylibpath(*parts):
        if sys.platform == "win32":
            return ipkgpath("feature-core", "INSTALLDIR", "lib", "python", "Lib", *parts)
        elif sys.platform == "darwin":
            return ipkgpath(cfg.macKomodoAppInstallName,
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
            return ipkgpath(cfg.macKomodoAppInstallName, "Contents", "bin", *parts)
        else:
            return ipkgpath("INSTALLDIR", "bin", *parts)
    def iisupportpath(*parts):
        """Image image dir for the Komodo 'support' bits."""
        if sys.platform == "darwin":
            return iicorepath(cfg.macKomodoAppInstallName, "Contents",
                              "SharedSupport", *parts)
        else:
            return iicorepath("lib", "support", *parts)
    def iisdkpath(*parts):
        """Image image dir for the Komodo SDK."""
        if sys.platform == "darwin":
            return iisupportpath("sdk", *parts)
        else:
            return iicorepath("lib", "sdk", *parts)
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
            return ipkgpath(cfg.macKomodoAppInstallName, "Contents", "Resources", *parts)
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
            ("hack-cp", mozdistpath(cfg.macKomodoAppBuildName), ipkgpath(cfg.macKomodoAppInstallName)),
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
        if cfg.msiVccrtRedistPath:
            # Need to copy the C libraries; for Python, need the CRT too.
            crt = "msvcr%s0.dll" % (cfg.compiler[2:],)
            ibits += [
                ("cp", join(cfg.msiVccrtRedistPath, "*"), iimozbinpath()),
                ("cp", join(cfg.msiVccrtRedistPath, crt), dirname(iipylibpath())),
            ]
    else:
        ibits += [
            ("cp", stubpath("komodo"+EXE), iicorebinpath("komodo"+EXE)),
        ]

    # - The prominent standalone doc bits: place somewhere appropriate
    #   in installation *and* in the base of installer package.
    ibits += [
        ("cp", readmepath("*"), iicorereadmepath()),
        ("cp", readmepath("*"), ipkgpath()),
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
            ("cp", join("src", "main", "komodo256.%s.png" % cfg.productType),
                   iicorepath("share", "icons", "komodo256.png")),
            ("cp", join("src", "main", "komodo16.%s.xpm" % cfg.productType),
                   iicorepath("share", "icons", "komodo16.xpm")),
            ("cp", join("src", "main", "komodo32.%s.xpm" % cfg.productType),
                   iicorepath("share", "icons", "komodo32.xpm")),
            ("cp", join("src", "main", "komodo48.%s.xpm" % cfg.productType),
                   iicorepath("share", "icons", "komodo48.xpm")),
            ("cp", join("src", "main", "komodo128.%s.xpm" % cfg.productType),
                   iicorepath("share", "icons", "komodo128.xpm")),
            ("cp", join("src", "main", "komodo256.%s.xpm" % cfg.productType),
                   iicorepath("share", "icons", "komodo256.xpm")),
        ]

    # - Trim some stuff.
    ibits += [
        # Remove "dev-tree" marker file.
        ("rm", iimozbinpath("is_dev_tree.txt")), 

        # Trim some files.
        ("rtrim", ".svn"),
        ("rtrim", ".consign"),
        ("rtrim", ".mkdir.done"),
        ("rtrim", "*.pyc"),
        ("rtrim", "*.pyo"),
        ("rtrim", "*.egg-info"),  # Python setup/easyinstall files.
        ("rm",    iimozbinpath("*.txt")),
        ("rm",    iimozbinpath("LICENSE")),
        ("rm",    iimozbinpath("pydbgp*")),
        ("rm",    iimozbinpath("scintilla.a")),

        # Trim Mozilla stuff.
        ("rm",    iimozbinpath("*.sh")),
        ("rm",    iimozbinpath(".gdbinit")),
        ("rm",    iimozbinpath(".lldbinit")),
        ("rm",    iimozbinpath(".purgecaches")),
        ("rm",    iimozbinpath("application.ini")),
        ("rmdir", iimozbinpath("gmp-clearkey")),
        ("rmdir", iimozbinpath("gmp-fake")),
        ("rm",    iimozbinpath("js-gdb.py")),
        ("rm",    iimozbinpath("komodo-bin")),
        ("rm",    iimozbinpath("mangle")),
        ("rm",    iimozbinpath("mozilla-xremote-client")),
        ("rm",    iimozbinpath("nsinstall")),
        ("rm",    iimozbinpath("shlibsign")),

        # Trim some unneeded stuff in siloed Python.
        ("rmdir", iipylibpath("ctypes", "test")),
        ("rmdir", iipylibpath("sqlite3", "test")),
        ("rmdir", iipylibpath("json", "tests")),
        ("rmdir", iipylibpath("lib2to3", "tests")),
        ("rmdir", iipylibpath("site-packages", "isapi", "doc")),
        ("rmdir", iipylibpath("site-packages", "isapi", "samples")),
        ("rmdir", iipylibpath("site-packages", "adodbapi", "tests")),
        ("rmdir", iipylibpath("site-packages", "win32comext", "bits", "test")),
        ("rmdir", iipylibpath("site-packages", "win32comext", "propsys", "test")),

        # Remove empty dirs
        ("rmemptydirs", iicorepath()),

        # Trim stuff from the Python install.
        ("rm", iipylibpath("lib2to3", "*.pickle")),  # lazily-generated cache grammar files

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
        # Don't need Windows debug symbol files.
        ibits += [
            ("rtrim", "*.pdb"),
            ("rm",    iimozbinpath("mangle.exe")),
            ("rm",    iimozbinpath("shlibsign.exe")),
        ]
        # We don't need the Python DLLs beside python.exe in the siloed
        # Python. The DLLs are already beside the main komodo.exe where
        # we *do* need them.
        ibits += [
            ("rm", iicorepath("lib", "python", "pythoncom*.dll")),
            ("rm", iicorepath("lib", "python", "pywintypes*.dll")),
            ("rm", iicorepath("lib", "python", "w9xpopen.exe")),
        ]

    # Trim pyxpcom component files that we don't need.
    ibits += [
        ("trim", iimozbinpath("components", "pyabout.manifest")),
        ("trim", iimozbinpath("components", "pyabout.py")),
        # Don't need the pyxpcom manifest as we have our own komodo manifest.
        ("trim", iimozbinpath("components", "pyxpcom.manifest")),
    ]

    # Mac requires most files to reside in the Resources directory.
    if sys.platform == "darwin":
        ibits += [
            ("mv", iimozbinpath("components"), iimozresourcespath("components")),
            ("mv", iimozbinpath("chrome"), iimozresourcespath("chrome")),
            ("mv", iimozbinpath("chrome.manifest"), iimozresourcespath("chrome.manifest")),
            ("mv", iimozbinpath("defaults"), iimozresourcespath("defaults")),
            ("mv", iimozbinpath("dictionaries"), iimozresourcespath("dictionaries")),
            ("mv", iimozbinpath("distribution"), iimozresourcespath("distribution")),
            ("mv", iimozbinpath("extensions"), iimozresourcespath("extensions")),
            ("mv", iimozbinpath("greprefs.js"), iimozresourcespath("greprefs.js")),
            ("mv", iimozbinpath("hyphenation"), iimozresourcespath("hyphenation")),
            ("mv", iimozbinpath("modules"), iimozresourcespath("modules")),
            ("mv", iimozbinpath("platform.ini"), iimozresourcespath("platform.ini")),
            ("mv", iimozbinpath("plugins"), iimozresourcespath("plugins")),
            ("mv", iimozbinpath("pyxpcom.manifest"), iimozresourcespath("pyxpcom.manifest")),
            ("mv", iimozbinpath("res"), iimozresourcespath("res")),
            ("mv", iimozbinpath("update.locale"), iimozresourcespath("update.locale")),
            ("mv", iimozbinpath("update-settings.ini"), iimozresourcespath("update-settings.ini")),
            ("mv", iimozbinpath("updater.ini"), iimozresourcespath("updater.ini")),
            ("mv", iimozbinpath("python"), iimozresourcespath("python")),
        ]

    GenerateCaches(cfg)

    # Start with a fresh image
    basedir = abspath("install") #ipkgpath()
    if exists(basedir): # start with a fresh INSTALLDIR/...
        shutil.rmtree(basedir)
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
            # We need the MacOS/mozpython executable to be a symlink though, but
            # the above commands will make a copy of the file instead. We
            # correct that here - bug 98441.
            assert os.path.islink(join(src2, "mozpython"))
            os.remove(join(dst2, "mozpython"))
            _run('cp -R "%s" "%s"' % (join(src2, "mozpython"),
                                      join(dst2, "mozpython")))
        elif data[0] == "cp":
            action, src, dst = data
            if not dst:
                # Some path factory functions return None to indicate
                # inapplicability on this platform.
                continue
            if not exists(dirname(dst)):
                os.makedirs(dirname(dst))
            for srcpath in glob.glob(src):
                if isdir(srcpath):
                    dstpath = isdir(dst) and join(dst, basename(srcpath)) or dst
                    log.debug("image:: cp dir %r to %r", srcpath, dstpath)
                    shutil.copytree(srcpath, dstpath)
                else:
                    log.debug("image:: cp %r to %r", srcpath, dst)
                    shutil.copy2(srcpath, dst)
        elif data[0] == "mv":
            action, src, dst = data
            if exists(dst):
                raise Error("can't move '%s' to '%s': '%s' exists"
                            % (src, dst, dst))
            log.debug("image:: mv %r to %r", src, dst)
            shutil.move(src, dst)
        elif data[0] == "rm":
            action, pattern = data
            for path in glob.glob(pattern):
                log.debug("image:: rm %r", path)
                os.unlink(path)
        elif data[0] == "rmdir":
            action, pattern = data
            for path in glob.glob(pattern):
                log.debug("image:: rmtree %r", path)
                shutil.rmtree(path)
        elif data[0] == "trim":
            # like 'rm' but doesn't error out if doesn't exist on Win
            action, pattern = data
            for path in glob.glob(pattern):
                log.debug("image:: trim %r", path)
                os.unlink(path)
        elif data[0] == "rtrim": # recursively trim given pattern
            action, pattern = data
            for dirpath, dirnames, filenames in os.walk(cfg.installRelDir):
                for path in glob.glob(join(dirpath, pattern)):
                    log.debug("image:: trim %r", path)
                    if isfile(path):
                        os.unlink(path)
                    else:
                        shutil.rmtree(path)
        elif data[0] == "rmemptydirs":
            #XXX Note that this removed a dir like:
            #     lib/mozilla/extensions/{972ce4c6-7e08-4474-a285-3208198ce6fd}
            #    Are we sure we want to do that?
            action, dname = data
            _rmemptydirs(dname)

    #---- Some manual Symlink fixes.
    # We now have four copies of libpython.so, cut that back to one copy and
    # symlink the others.
    if sys.platform not in ("win32", "darwin"):
        libpythonXYso = iicorepath("lib", "python", "lib",
                                   "libpython%s.so" % cfg.siloedPyVer)
        os.unlink(libpythonXYso)
        os.symlink("%s.1.0" % basename(libpythonXYso), libpythonXYso)
        log.debug("image:: symlinking %r => %r", libpythonXYso, "%s.1.0" % basename(libpythonXYso))

        for path in (iicorepath("lib", "mozilla", "libpython%s.so" % cfg.siloedPyVer),
                     iicorepath("lib", "mozilla", "libpython%s.so.1.0" % cfg.siloedPyVer)):
            os.unlink(path)
            os.symlink("../python/lib/%s.1.0" % basename(libpythonXYso), path)
            log.debug("image:: symlinking %r => %r", path, "../python/lib/%s.1.0" % basename(libpythonXYso))

    # Strip off any fat from the Komodo/Mozilla binaries to reduce the overall
    # size.
    # Note: This will still leave in the necessary crash-reporter information
    #       when build with "--with-crashreport-symbols".
    StripBinaries(iicorepath())


def _PackageKomodoDMG(cfg):
    from os.path import join, isdir, exists, dirname, basename
    print "packaging Komodo 'DMG'..."
    assert sys.platform == "darwin",\
        "'DMG' build on non-Mac OS X doesn't make sense"

    # Make sure "bk image" has been run.
    landmark = join(cfg.installRelDir, cfg.macKomodoAppInstallName)
    assert exists(landmark),\
        "no install image, run 'bk image': '%s' does not exist" % landmark

    # Assert that we have at least osxpkg v2.8.6 (the version when 
    # Komodo IDE 4.2 DMG template was fixed to be big enough).
    osxpkg_ver = os.popen("osxpkg --version").read().strip().split()[1]
    osxpkg_ver_tuple = tuple(map(int, osxpkg_ver.split('.')))
    assert osxpkg_ver_tuple >= (2,8,6), \
        "osxpkg is < 2.8.6: require >=2.8.6 for Komodo DMG template fixes: %r" \
        % osxpkg_ver

    # Remove unused architectures from the package, we only want to be left with
    # the Intel (i386 or x86_64) bits. We don't use the entire image, as we want
    # to exclude some things like xdebug, which may contain other useful
    # architectures (which could be used for remote debugging purposes).
    ditto_these_dirs = [
        join(landmark, "Contents", "Frameworks"),
        join(landmark, "Contents", "MacOS"),
        # Don't strip the tcl bits - as they contain attached data that would be
        # removed by ditto, which would cause these apps to fail, bug 86654.
        #join(landmark, "Contents", "SharedSupport", "tcl"),
    ]
    for original_dir in ditto_these_dirs:
        # Strip into a new directory, then copy back the stripped parts.
        stripped_dir = "%s.stripped" % (original_dir, )
        _run('ditto --rsrc --arch x86_64 "%s" "%s"' % (original_dir, stripped_dir))
        _rmtree(original_dir)
        os.rename(stripped_dir, original_dir)

    # If a code signing certificate is given, sign the binary now
    # (after we're all done mucking with it, just before we package)
    if hasattr(cfg, "osxCodeSigningCert"):
        codesignDir = os.path.join(cfg.komodoDevDir, "src/install/osx-codesign")
        try:
            codesign_exe = getattr(cfg, "osxCodeSignExecutable", None)
            sys.path.append(codesignDir)
            import codesign
            codesign.codesign(os.path.join(cfg.installRelDir, cfg.macKomodoAppInstallName),
                              cfg.osxCodeSigningCert, codesign_exe=codesign_exe)
        finally:
            sys.path.remove(codesignDir)

    productName = (cfg.productType == "openkomodo" and cfg.prettyProductType
                   or "Komodo-%s" % cfg.prettyProductType)
    majorVer = cfg.komodoVersion.split('.', 1)[0]
    template = "%s-%s" % (productName, majorVer)
    pkgPath = cfg.komodoInstallerPackage
    if exists(pkgPath):
        os.unlink(pkgPath)
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
        os.unlink(pkgPath)
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
         % (join("src", "install", "wix", "custom_actions", "custom_actions.dll"),
            join(wrkDir, "custom_actions.dll")))
    _run("copy /y %s %s"
         % (join(cfg.buildRelDir, "license_text", "LICENSE.rtf"),
            join(wrkDir, "aswixui", "License.rtf")))

    # build the file lists
    features = ("feature-core", "feature-docs")
    for feature in features:
        _run_in_dir("%s bin/gen-wxs.py %s.template.in %s.ini %s.wxs.in" %
                        (cfg.unsiloedPythonExe, feature, feature, feature),
                    wrkDir)

    # Run "autowix" to configure the WiX sources.
    # (I.e., convert '*.wxs.in' to '*.wxs'.)
    _run_in_dir("python bin\\autowix.py --force", wrkDir)

    # Check if we're unexpectedly imaging files we're not shipping
    print "---- Checking for new files we're accidentally not shipping"
    _run_in_dir("%s bin/check-wxs.py %s" %
                    (cfg.unsiloedPythonExe, " ".join(features)),
                wrkDir)

    print "---- build the MSI"
    dirs = [os.curdir] # implied by Windows shell
    dirs.extend(os.environ.get("PATH", "").split(os.pathsep))
    _run_in_dir('nmake -nologo clean all', wrkDir)

    print "---- copy MSI to packages dir"
    if not exists(dirname(cfg.komodoInstallerPackage)):
        os.makedirs(dirname(cfg.komodoInstallerPackage))
    shutil.copyfile(join(wrkDir, "komodo.msi"), cfg.komodoInstallerPackage)
    print "'%s' created" % cfg.komodoInstallerPackage



def _PackageKomodoUpdates(cfg, dryRun=False):
    print "packaging 'Komodo Updates'..."
    # Not creating updates for K7 alpha 2 (as the moz platform changed).
    if cfg.komodoVersion in ('7.0.0-alpha2', ):
        print "  not creating updates for %r" % (cfg.komodoVersion, )
        return
    mozupdate = join("util", "mozupdate.py")
    packagesDir = join(cfg.packagesRelDir, "updates")
    if not isdir(packagesDir):
        os.makedirs(packagesDir)
    wrk_dir = join(cfg.buildRelDir, "pkg_updates")
    if not exists(wrk_dir) and not dryRun:
        os.makedirs(wrk_dir)

    # Make sure "bk image" has been run.
    if sys.platform == "win32":
        landmark = join(cfg.installRelDir, "feature-core", "INSTALLDIR",
                        "lib", "mozilla", "komodo.exe")
    elif sys.platform == "darwin":
        landmark = join(cfg.installRelDir, cfg.macKomodoAppInstallName)
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
                if dryRun: continue
                _run('xcopy /s/q "%s\\INSTALLDIR" "%s"'
                     % (feature_dir, image_dir))
    elif sys.platform.startswith("linux"):
        image_dir = join(cfg.installRelDir, "INSTALLDIR")
    elif sys.platform.startswith("darwin"):
        image_dir = join(cfg.installRelDir, cfg.macKomodoAppInstallName)
    else:
        raise Error("don't know install image dir for platform %r"
                    % sys.platform)
    log.debug("image dir (for updates): '%s'", image_dir)

    # (Bug 71493) Ensure that the relocated bits of the siloed Python
    # on Linux are never *patched* by a partial update (because the MD5
    # check will always fail).
    mozupdate_clobber_arg = []
    if cfg.platform == "linux":
        mozupdate_clobber_arg = [
            "-c", "lib/python/bin/python%s" % cfg.siloedPyVer,
            "-c", "lib/python/bin/python%s-config" % cfg.siloedPyVer,
            "-c", "lib/python/bin/python-config",
            "-c", "lib/python/bin/2to3",
            "-c", "lib/python/lib/python%s/config/Makefile" % cfg.siloedPyVer,
            "-c", "lib/python/lib/python%s/site-packages/activestate.py" % cfg.siloedPyVer,
        ]

    # Partial update package(s).
    project = {"ide": "komodoide", "edit": "komodoedit",
               "openkomodo": "openkomodo"}[cfg.productType]
    guru = kopkglib.KomodoReleasesGuru(project, cfg.buildPlatform,
                                       cfg.komodoVersion)
    mar_cacher = kopkglib.KomodoMarCacher()

    removed_file_list = join(wrk_dir, "removed-files-candidates.txt")
    with open(removed_file_list, "w") as dummy_file:
        pass # make sure the file exists and is empty

    # - Always want a partial update relative to last few (for now: 3)
    #   nightly builds (for the 'nightly' channel). E.g.:
    #   Komodo-IDE-4.2.0-beta2-123456-win32-x86-partial-4.2.0-beta2-123455.mar
    NUM_PARTIAL_NIGHTLY_MARS = 3
    built_at_least_one_nightly_update = False
    for i, ref_mar_path in enumerate(guru.nightly_complete_mars(cfg.normSCCBranch)):
        if i >= NUM_PARTIAL_NIGHTLY_MARS:
            break
        ref_mar_changenum = guru.changenum_from_mar_path(ref_mar_path)
        if ref_mar_changenum == cfg.buildNum:
            # skip own build
            continue

        ref_mar_dir = mar_cacher.get_image_for_mar_path(ref_mar_path)
        ref_mar_ver = guru.version_from_mar_path(ref_mar_path)
        pkg_name = "%s-partial-%s.mar" % (cfg.komodoPackageBase, ref_mar_ver)
        pkg_path = join(packagesDir, pkg_name)
        print "creating '%s' (for 'nightly' channel)" % pkg_name
        if not dryRun:
            try:
                _run([sys.executable, mozupdate, "-q", "partial"] +
                     mozupdate_clobber_arg +
                     ["--removed-files-candidates", removed_file_list,
                      "--force", pkg_path, ref_mar_dir, image_dir])
                print "created '%s' (for 'nightly' channel)" % pkg_path
            except OSError, ex:
                log.warn("'nightly' mar failed: %r", ex)
                print "failed to create mar for 'nightly' channel - ignoring"
        built_at_least_one_nightly_update = True

        # ...and a changelog for this.
        changelog_path = join(packagesDir,
            "%s-partial-%s.html" % (cfg.komodoPackageBase, ref_mar_ver))
        start_rev = guru.changenum_from_mar_path(ref_mar_path) + 1
        end_rev = guru.changenum_from_mar_path(pkg_path)
        html = changelog.changelog_html(start_rev, end_rev)
        if not dryRun:
            open(changelog_path, 'w').write(html.encode('utf-8', 'ignore'))
        print "created '%s'" % changelog_path
    if not built_at_least_one_nightly_update:
        log.warn("no previous nightly complete .mar exists: skipping "
                 "build of partial update package for *nightly* channel")
    
    # - For betas *and* finals, want a partial update relative to the last
    #   released package, beta or not (for beta channel). Note: alphas
    #   count as a "beta" here, i.e. "beta" == "pre-release".
    ref_mar_path = last_beta_release_complete_mar \
        = guru.last_release_complete_mar
    if ref_mar_path is None:
        log.warn("no preceding release complete .mar package: skipping "
                 "build of partial update package for *beta* channel")
    elif not buildutils.remote_exists(ref_mar_path):
        log.warn("`%s' does not exist: skipping build of partial "
                 "update package for *beta* channel", ref_mar_path)
    else:
        ref_mar_dir = mar_cacher.get_image_for_mar_path(ref_mar_path)
        ref_mar_ver = guru.version_from_mar_path(ref_mar_path)
        pkg_name = "%s-partial-%s.mar" % (cfg.komodoPackageBase, ref_mar_ver)
        pkg_path = join(packagesDir, pkg_name)
        print "creating '%s' (for 'beta' channel)" % pkg_name
        if not dryRun:
            _run([sys.executable, mozupdate, "-q", "partial"] +
                 mozupdate_clobber_arg +
                 ["--removed-files-candidates", removed_file_list,
                  "--force", pkg_path, ref_mar_dir, image_dir])
        print "created '%s' (for 'beta' channel)" % pkg_path
    
    # - For all builds, want a partial update relative to the last
    #   released non-beta. This is used for the "release" channel if this
    #   is a final build (e.g. 4.2.1 -> 4.3.0). For *non-final* releases,
    #   this is used as a stepping stone into the "beta" and/or "nightly"
    #   channels (e.g. 4.2.1 user wants to start updating to the latest
    #   betas -> 4.3.0a2).
    last_final_release_complete_mar = guru.last_final_release_complete_mar
    if last_final_release_complete_mar is None:
        log.warn("no preceding final release complete .mar package: skipping "
                 "build of partial update package for *release* channel")
    elif last_final_release_complete_mar == last_beta_release_complete_mar:
        pass
    else:
        ref_mar_path = last_final_release_complete_mar
        if not buildutils.remote_exists(ref_mar_path):
            log.warn("`%s' does not exist: skipping build of partial "
                     "update package for *release* channel", ref_mar_path)
        else:
            ref_mar_dir = mar_cacher.get_image_for_mar_path(ref_mar_path)
            ref_mar_ver = guru.version_from_mar_path(ref_mar_path)
            pkg_name = "%s-partial-%s.mar" % (cfg.komodoPackageBase, ref_mar_ver)
            pkg_path = join(packagesDir, pkg_name)
            print "creating '%s' (for 'release' channel)" % pkg_name
            if not dryRun:
                _run([sys.executable, mozupdate, "-q", "partial"] +
                     mozupdate_clobber_arg +
                     ["--removed-files-candidates", removed_file_list,
                      "--force", pkg_path, ref_mar_dir, image_dir])
            print "created '%s' (for 'release' channel)" % pkg_path

    # Complete update package.
    # E.g.: Komodo-IDE-4.2.0-beta2-123456-win32-x86-complete.mar
    pkg_name = "%s-complete.mar" % cfg.komodoPackageBase
    pkg_path = join(packagesDir, pkg_name)
    if not dryRun:
        _run([sys.executable, mozupdate, "-q", "complete"] +
             ["--removed-files-candidates", removed_file_list,
              "--force", pkg_path, image_dir])
    print "created '%s'" % pkg_path

def _PackageKomodoCrashReportSymbols(cfg, dryRun=False):
    if not cfg.withCrashReportSymbols:
        return 0
    print "packaging 'Komodo Crash Report symbols'..."
    symbolsSrcDir = join(cfg.mozDist, "crashreporter-symbols")
    symbolsDstDir = join(cfg.packagesRelDir, "internal", "crashreportsymbols")
    if not exists(symbolsSrcDir):
        log.error("no 'crashreporter-symbols' directory found")
        return 1
    if not dryRun:
        if not isdir(symbolsDstDir):
            os.makedirs(symbolsDstDir)
        zippath = abspath(join(symbolsDstDir, "%s.zip" % (cfg.komodoPackageBase, )))
        import zipfile
        zip = zipfile.ZipFile(zippath, mode="w",
                              compression=zipfile.ZIP_DEFLATED)
        # This zip snippet comes from:
        # http://coreygoldberg.blogspot.com/2009/07/python-zip-directories-recursively.html
        root_len = len(symbolsSrcDir)
        for root, dirs, files in os.walk(symbolsSrcDir):
            archive_root = root[root_len:]
            for f in files:
                fullpath = join(root, f)
                archive_name = join(archive_root, f)
                #print f
                zip.write(fullpath, archive_name)
        zip.close()
        # end snippet

    return 0


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

    url = "http://grok.openkomodo.com/source/search?q=%s&path=%s"\
          % (quote(search_term), quote("/openkomodo/trunk/"))
    desktop.open(url)


def UploadKomodoPackages(cfg, argv):
    """Upload Komodo packages.

    Usage:
        bk upload <base-upload-dir>
    """
    try:
        upload_base_dir = argv[1]
    except IndexError:
        raise Error("incorrect usage, no upload dir given "
                    "(see `bk help upload')")
    log.info("upload packages in `%s' to `%s'", cfg.packagesRelDir,
             upload_base_dir)
    if buildutils.is_remote_path(upload_base_dir):
        from posixpath import join as ujoin
        from posixpath import normpath as unormpath
        from posixpath import dirname as udirname
    else:
        from os.path import join as ujoin
        from os.path import normpath as unormpath
        from os.path import dirname as udirname

    version = cfg.version
    buildNum = cfg.buildNum

    ver_info = _ver_info_from_long_ver_str(version)
    short_ver = _short_ver_str_from_ver_info(ver_info)
    d = "%s-%s-%s" % (cfg.sccRepoName, cfg.normSCCBranch, buildNum)    
    upload_dir = ujoin(upload_base_dir, short_ver, "DevBuilds", d)

    for dirpath, dirnames, filenames in os.walk(cfg.packagesRelDir):
        reldir = _relpath(dirpath, cfg.packagesRelDir).replace('\\', '/')
        for filename in filenames:
            if "pad" in reldir.split('/'):
                pass
            elif str(buildNum) not in filename and "/log" not in reldir:
                continue
            src = join(dirpath, filename)
            dst = unormpath(ujoin(upload_dir, reldir, filename))
            buildutils.remote_mkdir(udirname(dst), parents=True,
                                    log=log.info)
            buildutils.remote_cp(src, dst, log.info)


def PackageKomodo(cfg, argv):
    """Build Komodo packages.

    Usage:
        bk package [<package-names...>]
    
    Packages:
        installer       the native installer package (can also use
                        'msi', 'dmg', 'aspackage' aliases on the
                        appropriate platform)
        docs            a zip of the Komodo docs (for docs.as.com)
        mozpatches      a zip of the Mozilla patches for the used moz build
        updates         update package(s) for the autoupdate system
        pad             PAD file
        symbols         breakpad crash report symbol files

    Sets of packages:
        std             (the default) The standard set of packages for
                        this configuration.  
        all             all known packages
    
    """
    args = argv[1:] or ["std"]
    if "all" in args:
        packages = ["installer", "pad", "docs",
                    "mozpatches", "updates", "crashreportsymbols"]
    elif "std" in args:
        packages = ["installer", "pad", "crashreportsymbols"]
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
        elif package == "pad":
            retval = _PackageKomodoPAD(cfg)
        elif package == "updates":
            retval = _PackageKomodoUpdates(cfg)
        elif package == "crashreportsymbols":
            retval = _PackageKomodoCrashReportSymbols(cfg)
        else:
            raise ValueError("unknown package name: '%s'" % package)
        if retval:
            raise Error("error packaging '%s': retval=%r" % (package, retval))



def _PackageKomodoPAD(cfg):
    genpad_path = join("src", "pad", "genpad.py")
    output_dir = join(cfg.packagesAbsDir, "internal", "pad",
                      "komodo_%s" % cfg.productType)
    eula_text_path = "EULA.txt"
    if not exists(output_dir):
        os.makedirs(output_dir)

    # The PAD file.
    cmd = 'python %s -d "%s" -L "%s"' % (
        genpad_path, output_dir, eula_text_path)
    _run(cmd)

    # The screenshot file.
    plat_os = cfg.buildPlatform.split('-', 1)[0]
    _cp(join("src", "pad", "komodo_%s_%s.png" % (cfg.productType, plat_os)),
        output_dir)

    # The icon file.
    _cp(join("src", "main", "komodo32.%s.png" % cfg.productType),
        join(output_dir, "komodoedit_orb_32.png"))


def _PackageKomodoDocs(cfg):
    """Create Komodo's doc package.

    This package is used for updating docs.activestate.com.

    The 'mk ashelp' step in contrib/Conscript for "komododoc" should
    have been run by now. We will just packages it up.
    """
    from os.path import isdir, join, basename, dirname, exists

    buildDir = os.path.join(cfg.buildRelDir, cfg.docsPackageName)
    print "packaging 'docs' in '%s'" % buildDir

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
    mozilla patches applied to the moz build for the used moz build.

    Moz builds put a "mozilla-patches-<id>.zip" up in
        nas:/data/komodo/extras/mozilla-build-patches
    Currently we just find the right one and rename it.
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
            chromeDir = os.path.join(cfg.installAbsDir, cfg.macKomodoAppBuildName,
                                       "Contents", "MacOS", "chrome", chromeTree)
        else:
            chromeDir = os.path.join(cfg.installAbsDir, "INSTALLDIR",
                                       "Mozilla", "chrome", chromeTree)
    else:
        #XXX Could cfg.mozChromeDir not just be used to installer
        #    builds as well?
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
            cmd = "%s -X -r -q %s content skin locale -x \\*.consign" % (zipExe, jarFile)
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




def ExtractPrebuiltPython(cfg, argv):
    """Unzip the prebuilt python files if they don't exist.
    
    This is required for some of the Mozilla build parts (komodo/app/xre).
    """
    if sys.platform == "win32":
        zip_basename = "win32-%s-%s" % (cfg.architecture, cfg.compiler)
    elif sys.platform.startswith("darwin"):
        zip_basename = "macosx"
    elif sys.platform.startswith("linux"):
        zip_basename = "linux-%s" % (cfg.architecture)
    else:
        raise BuildError("ExtractPrebuiltPython:: unknown platform: %r",
                         sys.platform)
    prebuiltDir = join("mozilla", "prebuilt", "python%s" % cfg.siloedPyVer,
                       zip_basename)

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


def GetScintillaSource(cfg, argv):
    """Copy the scintilla source to src/scintilla/... and patch it.

    This is only done if src/scintilla doesn't already exist.
    """
    landmark = join("src", "scintilla", ".patchtree-state")
    if exists(landmark):
        return

    # Copy over clean scintilla sources.
    log.info("copy clean scintilla sources in src/scintilla")
    _cp(join("contrib", "scintilla"), join("src", "scintilla"))

    # Patch it with patches in "contrib/patches/scintilla".
    patchtree.log.setLevel(logging.INFO)
    patchtree.patch([join("contrib", "patches", "scintilla")],
                    join("src", "scintilla"),
                    config=cfg,
                    #dryRun=1,  # uncomment this line to dry-run patching
                    logDir=join(cfg.buildAbsDir, "scintilla-patch-log"))
    # Run the HFacer to generate the scintilla include files.
    _run_in_dir(sys.executable + " HFacer.py",
                join("src", "scintilla", "scripts"),
                log.debug)


def _BuildKomodo(cfg, argv):
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
    if "crashreportsymbols" in argv:
        return BuildCrashReportSymbols(cfg)
    if "caches" in argv:
        return GenerateCaches(cfg)
    if "package_md5sums" in argv:
        return _PackageUpdateMd5sums(cfg)
    noquick = "noquick" in argv
    if noquick:
        argv.remove("noquick")     

    # Fetch sub-repos if necessary
    retval = FetchDependentSources(cfg, argv, update=False)

    # Unzip the prebuilt Python if necessary.
    retval = ExtractPrebuiltPython(cfg, argv)

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
    if not retval and not noquick:
        BuildQuickBuildDB(cfg, argv)
    return retval

def humantime(sec):
    if sec <= 60:
        return '%0.2f' % (sec)
    if sec <= 3600:
        return '%dm%ds' % (sec // 60, sec % 60)
    return '%dh%dm%ds' % (sec // 3600, (sec // 60) % 60, sec % 60)

def BuildKomodo(cfg, argv):
    starttime = time.time()
    try:
        retval = _BuildKomodo(cfg, argv)
    except AttributeError, ex:
        if "'module' object has no attribute" in str(ex):
            import traceback
            traceback.print_exc()
            print "\nBuild error - perhaps you need to bk reconfigure?\n"
            return -1
        raise
    endtime = time.time()
    duration = endtime - starttime
    print "Build time - %s" % (humantime(duration))
    return retval

def CleanKomodoBuild(cfg, argv):
    """Try to clean out most of the Komodo build bits."""
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
        mozbinpath(".consign"),
        
        # This moved. Make sure it gets turfed from old moz builds.
        mozbinpath("komodo-config.py"),
        mozbinpath("komodo-config"),

        # Scintilla libraries.
        mozbinpath("SciLexer.dll"),
        mozbinpath("ScintillaHeadless.dll"),
        mozbinpath("libscintilla.dylib"),

        mozbinpath("chrome", "icons"),
        mozbinpath("chrome", "xtk"),
        mozbinpath("chrome", "xtk.jar"),
        mozbinpath("chrome", "xtk.manifest"),
        mozbinpath("chrome", "komodo-jstest"),
        mozbinpath("chrome", "komodo-jstest.manifest"),
        mozbinpath("chrome", "komodo"),
        mozbinpath("chrome", "komodo.jar"),
        mozbinpath("chrome", "komodo.manifest"),
        mozbinpath("chrome", "komododoc"),
        mozbinpath("chrome", "komododoc.jar"),
        mozbinpath("chrome", "komododoc.manifest"),
        mozbinpath("chrome", "iconsets"),
        mozbinpath("chrome", "skins"),
        mozbinpath("components", "komodo.manifest"),
        mozbinpath("components", "ko*.py"),
        mozbinpath("components", "ko*.pyc"),
        mozbinpath("components", "ko*.pyo"),
        mozbinpath("components", "ko*.js"),
        mozbinpath("components", "ko*.xpt"),
        mozbinpath("components", "ko*.dll"),
        mozbinpath("components", "ISciMoz*"),
        mozbinpath("components", "as*.xpt*"),
        mozbinpath("components", "as*.js"),
        mozbinpath("components", "libko*"),
        mozbinpath("components", "scimoz_wrapper.js"),
        mozbinpath("components", "xpcomJSElements.*"),
        mozbinpath("plugins", "npscimoz.dll"),
        mozbinpath("plugins", "libnpscimoz.so"),

        mozbinpath("extensions"),
        mozbinpath("distribution", "bundles"),
        mozbinpath("updater.ini"),

        mozbinpath("plugins", "SciMoz.plugin"), # its name on OS X
        #TODO:
        # - SciMoz plugin on other plats
    ]
    mozKomodoAppDir = join(cfg.mozObjDir, "komodo", "app")
    if sys.platform == "win32":
        bits.append(join(mozKomodoAppDir, "*.obj"))
        bits.append(join(mozKomodoAppDir, "komodo.exe"))
    else:
        bits.append(join(mozKomodoAppDir, "*.o"))

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


def DistCleanKomodoBuild(cfg, argv):
    """Completely clean out all Komodo build, package and install bits."""
    from os.path import abspath, join, isdir, isfile
    CleanKomodoBuild(cfg, argv)
    bits = [
        join(cfg.komodoDevDir, "build"),
        join(cfg.komodoDevDir, "export"),
        join(cfg.komodoDevDir, "packages"),
        join(cfg.komodoDevDir, "install"),
        join(cfg.komodoDevDir, "src", "scintilla"),
        join(cfg.komodoDevDir, "generated.pdb"),
    ]
    if cfg.sccType == "git":
        bits.append(join(cfg.komodoDevDir, "contrib", "komododoc"))
    for path in bits:
        out.write("remove '%s'\n" % path)
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
    # Do NOT run with bkconfig.bat because it sets PYTHONHOME, which screws up
    # Python linting with a version different than Komodo's own build Python...
    # among other things.
    return tmShUtil.RunCommands([ cmd ])

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
        if sys.platform.startswith("win"):
            for csidl in (shellcon.CSIDL_APPDATA, shellcon.CSIDL_COMMON_APPDATA):
                for subdir in ("Mozilla", "XRE"):
                    path = os.path.join(
                        str(shell.SHGetFolderPath(0, csidl, 0, 0)),
                        "ActiveState", "Komodo", cfg.komodoShortVersion,
                        subdir)
                    toDelete.append(path)
        elif sys.platform == 'darwin':
            from Carbon import Folder, Folders
            for domain in (Folders.kUserDomain, Folders.kLocalDomain):
                for subdir in ("Mozilla", "XRE"):
                    base = Folder.FSFindFolder(domain, 
                        Folders.kApplicationSupportFolderType,
                        Folders.kDontCreateFolder)
                    path = os.path.join(base.FSRefMakePath(),
                        "Komodo", cfg.komodoShortVersion, subdir)
                    toDelete.append(path)
        else:
            for subdir in ("Mozilla", "XRE"):
                path = os.path.join(os.path.expanduser("~/.komodo"),
                    cfg.komodoShortVersion, subdir)
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
    # "mozpython" is the Python binary in the $mozBin dir for which PyXPCOM
    # will work (paths, libs, etc. setup properly). See bug 66332.
    # Default to optimize, because asserts break the html/xml parser. Bug 99976.
    cmd = 'mozpython -O test.py'
    if "--assert" in argv:
        argv.remove("--assert")
        cmd = 'mozpython test.py'
    return tmShUtil.RunInContext(cfg.envScriptName, [
        'cd test',
        '%s %s' % (cmd, ' '.join(argv[1:]))
    ])

def TestKomodoPerf(cfg, argv):
    # Change to the test directory (in the _install_ tree)
    # and call perf.py.
    import tmShUtil
    cmd = "mozpython perf.py %s" % " ".join(argv[1:])
    if sys.platform == 'darwin':
        testDir = os.path.join(cfg.installAbsDir, cfg.macKomodoAppBuildName,
                               "Contents", "SharedSupport", "test")
    else:
        testDir = os.path.join(cfg.installAbsDir, "INSTALLDIR", "test")
    return tmShUtil.RunInContext(cfg.envScriptName,
                                 [ 'cd "%s"' % testDir, cmd ])

def _addExtensionFiles(cfg, sourceSubdir, targetSubdir, extensions, preserveSubtrees=0,
              targetSubdirPattern=None, extNameMappings=None):
    if not exists(sourceSubdir):
        return
    extensionsdir = join(cfg.mozBin, 'extensions')
    # our extensions in src are just the name, but get installed to name@ActiveState.com
    dirlist = os.listdir(sourceSubdir)
    modules = {}
    for name in dirlist:
        if not isdir(join(sourceSubdir, name)):
            continue
        extname = name
        if extNameMappings:
            extname = extNameMappings.get(extname, extname)
        # We don't have consistent naming for add-ons, some use "@ActiveState"
        # and others use "@activestate".
        for possible in ("@ActiveState.com", "@activestate.com"):
            extdir = join(extensionsdir, extname + possible)
            if isdir(extdir):
                modules[name] = extdir
                break
    #    else:
    #        print "No extension dir for %r" % (extname, )
    #pprint(modules)
    for name, targetDir in modules.items():
        _addFiles(cfg, sourceSubdir='%s/%s' % (sourceSubdir, name),
                  targetSubdir=targetDir,
                  extensions=extensions,
                  preserveSubtrees=preserveSubtrees)

# Excluded directory paths for _addFiles (relative to the given sourceSubdir).
g_excluded_relpaths = [
    join("codeintel", "play"),
    join("codeintel", "test2"),
    join("unittest", "examples"),
    join("xdebug2", "build"),
    join("xdebug2", "tmp"),
]

def _addFiles(cfg, sourceSubdir, targetSubdir, extensions, preserveSubtrees=0):
    count = 0
    sourceSubdir = os.path.normpath(os.path.abspath(sourceSubdir))
    
    assert targetSubdir

    # find possible files of interest
    for dirpath, dirnames, filenames in os.walk(sourceSubdir):
        relpath = dirpath[len(sourceSubdir)+1:]
        if relpath in g_excluded_relpaths:
            dirnames[:] = []
            continue
        #print "Walking %r" % (dirpath, )
        for fname in filenames:
            bname, ext = splitext(fname)
            if ext[1:].lower() in extensions:
                srcpath = join(dirpath, fname)
                if srcpath in _table:
                    # Skip over entries we've already processed.
                    continue
                # Target names are used for pre-processed files.
                pname = fname
                psrcpath = srcpath
                pbname, pext = splitext(bname)
                if pext in [".unprocessed", ".p"]:
                    # This is a file that will be run through the preprocessor and
                    # whose actual target name should drop the ".unprocessed".
                    pname = pbname + ext
                    psrcpath = join(dirpath, pname)
                # determine target location for files
                if preserveSubtrees:
                    # We are working with files which maintain their subdirectory
                    # structure in the target subtree.
                    target = normpath(join(targetSubdir, psrcpath[len(sourceSubdir):].lstrip(os.sep)))
                else:
                    # We are working with files which are in one of the target
                    # subdirectories.
                    target = normpath(join(targetSubdir, pname))
                if os.path.exists(target):
                    _table[srcpath] = (abspath(target), md5(open(srcpath, 'rb').read()).hexdigest())
                    count += 1
    #print 'Found %d %s files in %s' % (count, extensions, sourceSubdir)
    
def BuildQuickBuildDB(cfg, argv):
    starttime = time.time()
    if sys.platform == 'darwin':
        sharedSupportRelDir = "%s/Contents/SharedSupport" % cfg.macKomodoAppBuildName
    else:
        sharedSupportRelDir = "INSTALLDIR"
    print "Building 'bk build quick' cache from installed copy."
    _addFiles(cfg, sourceSubdir='src/chrome/',
              targetSubdir=os.path.join(cfg.mozBin, 'chrome'),
              extensions=['xul', 'xml', 'js', 'css', 'less', 'dtd', 'gif', 'png',
                          'html', 'rdf', 'properties', 'svg'],
              preserveSubtrees=1)
    _addExtensionFiles(cfg, sourceSubdir='src/modules/',
              targetSubdir=os.path.join(cfg.mozBin, 'extensions'),
              extensions=['xul', 'xml', 'js', 'css', 'less', 'dtd', 'gif', 'png', 'html', 'py'],
              preserveSubtrees=1,
              # These extensions use a different directory name.
              # TODO: We should fix some of these in Komodo 8.
              extNameMappings={
                    'rails': 'railstools',
                    'spellcheck': 'komodospellchecker',
                    })
    _addFiles(cfg, sourceSubdir='src/',
              targetSubdir=os.path.join(cfg.mozBin, 'components'),
              extensions=['py', 'js'])
    _addFiles(cfg, sourceSubdir='src/chrome/komodo/content',
              targetSubdir=os.path.join(cfg.mozBin, 'modules'),
              extensions=['js', 'jsm'])
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
    _addFiles(cfg, sourceSubdir='src/codeintel/bin',
              targetSubdir=os.path.join(cfg.supportDir, "codeintel"),
              extensions=['py'],
              preserveSubtrees=1)
    _addFiles(cfg, sourceSubdir='src/prefs',
              targetSubdir=os.path.join(cfg.supportDir),
              extensions=['xml'],
              preserveSubtrees=1)
    _addFiles(cfg, sourceSubdir='src/schemes',
              targetSubdir=os.path.join(cfg.supportDir, "schemes"),
              extensions=['kkf', 'ksf'],
              preserveSubtrees=1)
    _addFiles(cfg, sourceSubdir='src/images/icons/xpm',
              targetSubdir=os.path.join(cfg.mozBin, 'chrome', 'komodo', 'skin', 'images'),
              extensions=['xpm'],
              preserveSubtrees=1)
    
    if cfg.platform == "darwin":
        skinPlat = 'mac'
    elif cfg.platform == "win":
        skinPlat = 'win'
    else:
        skinPlat = 'gnome'

    _addFiles(cfg, sourceSubdir='src/chrome/komodo/skin/plat/'+skinPlat,
               targetSubdir=os.path.join(cfg.mozBin, 'chrome', 'komodo', 'skin'),
               extensions=['css', 'less', 'png'],
               preserveSubtrees=1)
   
    _addFiles(cfg, sourceSubdir='src/chrome/komodo/skin/plat/shared',
               targetSubdir=os.path.join(cfg.mozBin, 'chrome', 'komodo', 'skin', 'plat', 'shared'), 
               extensions=['css', 'less', 'png', 'manifest'],
               preserveSubtrees=1)

    _addFiles(cfg, sourceSubdir='src/chrome/komodo/skin/plat'+skinPlat,
              targetSubdir=os.path.join(cfg.mozBin, 'chrome', 'komodo', 'skin', 'plat', 'current'),
              extensions=['css', 'less', 'png'],
              preserveSubtrees=1)

    _addFiles(cfg, sourceSubdir='src/chrome/iconsets',
               targetSubdir=os.path.join(cfg.mozBin, 'chrome', 'iconsets'),
               extensions=['css', 'less', 'png', 'svg', 'manifest', 'jar'],
               preserveSubtrees=1)
     
    _addFiles(cfg, sourceSubdir='src/images/icons/plat/'+skinPlat,
               targetSubdir=os.path.join(cfg.mozBin, 'chrome', 'komodo', 'skin', 'images'),
               extensions=['gif', 'png', 'xpm'],
               preserveSubtrees=1)
  
    pickle.dump(_table, open('qbtable.pik', 'w'))
    endtime = time.time()
    duration = endtime - starttime
    print "Cache created - %s" % (humantime(duration))

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
            newmd5 = md5(open(source, 'rb').read()).hexdigest()
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
                                               "UPDATE_CHANNEL": cfg.updateChannel,
                                               "WITH_PLACES": 1,
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

    # save the new state of affairs
    pickle.dump(_table, open('qbtable.pik', 'w'))
    print "quick build: done"

def BuildCrashReportSymbols(cfg):
    if not cfg.withCrashReportSymbols:
        return
    
    # Needs to run with the Mozilla environment, otherwise will receive errors
    # about being unable to load required libraries.
    cmds = [
        "cd %s/mozilla" % (cfg.mozSrc,),
        "%s mach buildsymbols" % (sys.executable,)
    ]
    if sys.platform.startswith("win"):
        # Fake being in MINGW32 terminal, so paths are properly converted.
        cmds.insert(1, "set MSYSTEM=MINGW32")
    tmShUtil.RunInContext(cfg.envScriptName, cmds)
    if sys.platform.startswith("win") or sys.platform == "darwin":
        # Need to include the Komodo bits separately.
        output_dir = join(cfg.mozDist, "crashreporter-symbols")
        if not _isdir(output_dir):
            _mkdir(output_dir)
        moz_crashreporter_src_dir = join(cfg.mozSrc, "mozilla", "toolkit",
                                         "crashreporter")
        py_symbol_script = join(moz_crashreporter_src_dir, "tools", "symbolstore.py")
        options = "-c"
        if sys.platform.startswith("win"):
            if not cfg.compiler.startswith("vc"):
                raise black.BlackError("unexpected compiler %r" % (cfg.compiler, ))
            msc_ver = (int(cfg.compiler[2:], 10) + 6) * 100
            dump_symbols_exe = join(moz_crashreporter_src_dir, "tools", "win32",
                                    "dump_syms_vc%d.exe" % (msc_ver, ))
        else:
            options += " -a " + cfg.architecture   # the wanted architecture
            dump_symbols_exe = join(cfg.mozDist, "host", "bin", "dump_syms")
        cmd = ["python",
               py_symbol_script,       # python script to generate symbol info
               options,
               "-s", cfg.komodoDevDir, # the base source reference directory
               dump_symbols_exe,       # executable that dumps the symbol info
               output_dir,             # where crashreporter symbol files end up
               cfg.buildAbsDir,        # where to look for ".pdb" files
              ]

        # Ensure the Mozilla Python libraries are on the pythonpath:
        env = os.environ.copy()
        pypath = env.get('PYTHONPATH', '').split(os.pathsep)
        pypath.append(join(cfg.mozSrc, "mozilla", "python", "mozbuild"))
        pypath.append(join(cfg.mozSrc, "mozilla", "python", "jsmin"))
        env['PYTHONPATH'] = os.pathsep.join(pypath)

        _run(' '.join(cmd), env=env)


commandOverrides = {
    "fetch": FetchDependentSources,
    "build": BuildKomodo,
    "run": RunKomodo,
    "cleanprefs": CleanPreferences,
    "clean": CleanKomodoBuild,
    "distclean": DistCleanKomodoBuild,
    "package": PackageKomodo,
    "upload": UploadKomodoPackages,
    "test": TestKomodo,
    "perf": TestKomodoPerf,
    "image": ImageKomodo,
    "grok": GrokKomodo,
}

helpTemplate = """
        bk distclean        completely clean everything
        bk configure        configure to build %(name)s
        bk fetch            fetch dependent sources
        bk build            build %(name)s
        bk clean            clean %(name)s
        bk run              run the %(name)s app
        bk start <command>  execute a command in the configured environment
        bk test             run %(name)ss self-test suite

        bk package          package up %(name)s bits
        bk upload           upload %(name)s bits to staging area
        bk cleanprefs <komodo|mozilla>
                            clean Komodo or Mozilla prefs
"""
