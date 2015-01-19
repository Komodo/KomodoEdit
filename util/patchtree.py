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

"""
    patchtree.py -- applying sets of patches to source trees

    Module Usage:
        import patchtree
        patchtree.patch(<patchesdir>, <srcdir>, config=<config object>,
                        logDir=<logdir>, dryRun=<boolean>)
        patchtree.unpatch(<srcdir>, <logdir>, dryRun=<boolean>)
    
    Command Line Usage:
        python patchtree.py [<options>...] <srcdir> <patchesdir>...
    
    Options:
        -h, --help          Print this help and exit.
        -V, --version       Print this script's version and exit.
        -v, --verbose       Increase the verbosity of output.
        --dry-run           Go through motions but don't change anything.
        
        -c, --config <configfile>
                            Specify a Python configuration module to be
                            passed to __patchinfo__.py control files.
        -L, --log-dir <logdir>
                            Specify a log directory in which all patches
                            that are actually applied are placed.
        -R                  Reverse patch, i.e. backout previous patches.

    This module defines a system for applying sets of patches to source
    trees. Which patches are applied can be controlled by meta-data files --
    which themselves can run Python code to determine if a certain patch (or
    patches) should be applied. The details and cross-platform pains of
    applying patches is hidden. It is intelligent to know if the patch set is
    already applied. Applying the patch set is mostly atomic. Etc.


    Here is how it works. You specify a source directory and a number of
    patch directories (or files). Any directory may have a __patchinfo__.py
    Python module to control how that directory tree of patches is applied.
    That module may define any of the following special functions:
    
        def applicable(config)
            Should return true if this directory tree should be considered
            for patching and false otherwise. Presumed to be true if this
            function is not defined.
        def patchfile_applicable(config, filepath)
            Should return true if this patch file should be considered
            for patching and false otherwise. Presumed to be true if this
            function is not defined.
        def remove(config)
            Should return a list of file or directory paths to remove from
            the source tree. All paths should be relative to the base of the
            source tree. Presumed to return the empty list if this function
            is not defined.
        def add(config)
            Should return a list of 2- or 3-tuples of the form
                (<src-filename>, <dest-filepath>[, "force"])
            where <src-filename> is the name of a file in that directory
            and <dest-filepath> is a destination file path (relative to
            the base of the source tree). Specifying "force" will allow
            the added file to clobber an existing file. Note that the
            use of "force" currently means that unpatching does not
            properly revert to the starting state. Presumed to return
            the empty list if this function is not defined.
            If any file being added is named like BASE.p.EXT, it will be
            preprocessed.
        def patch_args(config):
            Return None or a list of command line args to add to patch.exe
            invocations. E.g. to set the fuzz level to 3 one would return
            ['-F3']. Note that spaces in args are quoted so separate args as
            separate list elements. In the previous example, ['-F 3'] is wrong
            but ['-F3'] or ['-F', '3'] or ['--fuzz', '3'] are okay.
            XXX Should use this patch arg info for unpatching.
        def patch_order(config):
            Return a list of patch file names in the order they should be
            applied.  Each patch file will go through the normal
            patchfile_applicable() checks; this is used only for ordering.  If
            this function is not defined, but a file named "series" does, that
            is used instead, with each file name on its own line.  If that does
            not exist either, all patch files (*.patch, *.diff, *.ppatch) in the
            directory are used in an undefined order.
    
    where "config" is a configuration object specified via patch()'s "config"
    argument or the --config command-line option. If no config is specified
    then this is None.
    
    If a directory is being considered then all *.patch and *.diff files are
    considered to be patches and all *.ppatch files are considered to be
    patches that must first be preprocessed (see preprocess.py,
    http://starship.python.net/crew/tmick/#preprocess). The given "config"
    is used to create a set of preprocessor defines in the following way:
        
        type(config)        Conversion to preprocess defines
        ------------------  -----------------------------------------------
        <type 'module'>     Convert all globals to PT_CONFIG_<varname>
                            defines. For example, this module:
                                name = "kermit"
                                animal = "frog"
                            will have PT_CONFIG_name and PT_CONFIG_animal
                            defines. Globals that start with an underscore
                            are excluded.
        <type 'dict'>       Convert all string/unicode keys to
                            PT_CONFIG_<varname> defines. Keys that start
                            with an underscore are excluded.
        otherwise           punt, no preprocessor defines

    If a "series" file exists within a patch directory, it is used for patch
    ordering.
"""
# TODO:
# - break this out into a separate project
# - add a test suite

__version_info__ = (0, 4, 3)
__version__ = '.'.join(map(str, __version_info__))

import collections
import os
from os.path import join, normpath, splitext, exists, dirname, isdir, \
                    isfile, basename
import sys
import traceback
import time
import re
import tempfile
import logging
import getopt
import imp
import pprint
import glob
import types
try:
    from hashlib import md5
except ImportError:
    from md5 import md5
import difflib

try:
    # Prefer the Python 2.4 standard subprocess module.
    import subprocess
except ImportError:
    # Fallback to my process.py module (which is available for earlier Python
    # versions, but depends on PyWin32).
    import process as subprocess
import preprocess
import sh
try:
    import which
except SyntaxError:
    import which21 as which



#---- exceptions

class Error(Exception):
    pass


log = logging.getLogger("patchtree")


#---- internal support stuff

def _is_content_binary(content):
    """Return true iff the given file content is binary."""
    if '\0' in content:
        return True
    else:
        return False
_SCC_control_dirs = ("CVS", ".svn", ".hg", ".git")

def _run(argv, cwd=None, stdin=None):
    if subprocess.__name__ == "subprocess":
        p = subprocess.Popen(argv, cwd=cwd, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, stdin=subprocess.PIPE)
        if stdin is not None:
            p.stdin.write(stdin)
        p.stdin.close()
        stdout = p.stdout.read()
        stderr = p.stderr.read()
        retval = p.wait()
    elif subprocess.__name__ == "process":
        p = subprocess.ProcessOpen(argv, cwd=cwd)
        if stdin is not None:
            p.stdin.write(stdin)
        p.stdin.close()
        # Shouldn't have to worry about buffer overflow blocking for the
        # commands being run by this module.
        stdout = p.stdout.read()
        stderr = p.stderr.read()
        retval = p.wait()
        p.close()
    else:
        raise Error("no subprocess module to work with")
    return stdout, stderr, retval

def _getPatchInfo(dirname):
    if "__patchinfo__" in sys.modules:
        del sys.modules["__patchinfo__"]
    for p in glob.glob(join(dirname, "__patchinfo__.py[co]")):
        try:
            os.remove(p)
        except EnvironmentError:
            pass
    try:
        file, path, desc = imp.find_module("__patchinfo__", [dirname])
    except ImportError, ex:
        return None
    try:
        patchinfo = imp.load_module("__patchinfo__", file, path, desc)
        return patchinfo
    except SyntaxError, ex:
        errinfo = ex.args[1]
        raise Error("syntax error in patchinfo file: %s:%d: %r"
                    % (errinfo[0], errinfo[1], errinfo[3]))
        return None

def _determinePatchesFromDirectory(base, actions, config):
    """Process a given patch directory recursively for appropriate patch actions
    """
    for dirpath, subdirs, names in os.walk(base):
        log.debug("process patch dir '%s'", dirpath)
        patchinfo = _getPatchInfo(dirpath)
        if patchinfo: log.debug("    patchinfo: %r", patchinfo)

        # Always skip SCC control dirs.
        for exclude_dir in _SCC_control_dirs:
            if exclude_dir in subdirs and isdir(join(dirpath, exclude_dir)):
                subdirs.remove(exclude_dir)

        # Skip this dir if patchinfo says it should not be applied.
        if patchinfo and hasattr(patchinfo, "applicable"):
            if not patchinfo.applicable(config):
                log.debug("    skip: applicable() returned false")
                del subdirs[:]
                continue
        subdirs[:] = sorted(subdirs)

        # Add "add" and "remove" actions action to the patchinfo, if any.
        # - Must do "remove" first, if necessary for the subsequent "add" action.
        #   E.g., if replacing "File.Ext" with a "file.ext" on Windows (case
        #   difference in the name), then "File.Ext" must first be removed to
        #   get the desired case.
        if hasattr(patchinfo, "remove"):
            retval = patchinfo.remove(config)
            try:
                if isinstance(retval, basestring):
                    raise TypeError
                retval = iter(retval)
            except TypeError:
                raise Error("invalid return type from remove() in %s, "
                            "must return a sequence: retval=%r"
                            % (patchinfo.__file__, retval))
            for dst in retval:
                action = ("remove", dirpath, dst)
                log.debug("    action: %r", action)
                actions.append(action)

        if hasattr(patchinfo, "add"):
            retval = patchinfo.add(config)
            try:
                if isinstance(retval, basestring):
                    raise TypeError
                retval = iter(retval)
            except TypeError:
                raise Error("invalid return type from add() in %s, "
                            "must return a sequence: retval=%r"
                            % (patchinfo.__file__, retval))
            for add_record in retval:
                if len(add_record) == 2:
                    filename, dst = add_record
                    force = False
                else:
                    filename, dst = add_record[:2]
                    assert add_record[2] == "force", \
                        "unexpected add record (3rd arg not 'force'): %r" \
                        % (add_record,)
                    force = True
                try:
                    # If a subdirectory is being used for an "add" action,
                    # then don't consider it as a patchtree.
                    subdirs.remove(filename)
                except ValueError:
                    pass
                action = ("add", dirpath, filename, dst, force)
                log.debug("    action: %r", action)
                actions.append(action)

        # See if there are any special patch_args for patches in this dir.
        if patchinfo and hasattr(patchinfo, "patch_args"):
            patch_args = patchinfo.patch_args(config) or []
            if not isinstance(patch_args, list):
                raise Error("patch_args() in '%s' did not return a list "
                            "(or None): %s" % (patchinfo.__file__, patch_args))
        else:
            patch_args = []

        patch_applicable_fn = getattr(patchinfo, "patchfile_applicable",
                                      lambda config, patchfile: True)

        # Find patch files.
        # By deafult, use sorted order, to at least be consistent across runs
        patch_names = sorted(n for n in names if splitext(n)[-1] in
                             (".patch", ".diff", ".ppatch"))

        if hasattr(patchinfo, "patch_order"):
            patch_names = patch_names.patch_order(config)
        elif exists(join(dirpath, "series")):
            expected_patch_names = set(patch_names)
            with open(join(dirpath, "series")) as series_file:
                patch_names = filter(None, map(lambda n: n.strip(), series_file))
            actual_patch_names = set(patch_names)
            if expected_patch_names ^ actual_patch_names:
                missing = sorted(actual_patch_names - expected_patch_names)
                extra = sorted(expected_patch_names - actual_patch_names)
                msg = ["Series file doesn't match patches actually available:"]
                if missing:
                    msg.append("\tPatch files not found: " + ", ".join(missing))
                if extra:
                    msg.append("\tExtra entries in series: " + ", ".join(extra))
                raise Error("\n".join(msg))

        for patchfile in patch_names:
            if not patch_applicable_fn(config, patchfile):
                log.debug("    skip: patchfile_applicable() returned false "
                          "for %r", patchfile)
                continue
            action_name = {
                ".patch": "apply",
                ".diff": "apply",
                ".ppatch": "process & apply"
            }.get(splitext(patchfile)[-1])
            if not action_name:
                raise Error("Don't know how to process patch file %s; its name "
                            "should end with .patch, .diff, or .ppatch" %
                            (join(dirpath, patchfile),))
            action = (action_name, dirpath, patchfile, patch_args)
            log.debug("    action: %r", action)
            actions.append(action)

def _getPreprocessorDefines(config):
    defines = {}
    if isinstance(config, types.ModuleType):
        for key, value in config.__dict__.items():
            if type(key) in (types.StringType, types.UnicodeType) and not key.startswith("_"):
                defines["PT_CONFIG_"+key] = value
    elif isinstance(config, dict):
        for key, value in config.items():
            if type(key) in (types.StringType, types.UnicodeType) and not key.startswith("_"):
                defines["PT_CONFIG_"+key] = value
    else:
        for name in dir(config):
            if type(name) in (types.StringType, types.UnicodeType) and not name.startswith("_"):
                defines["PT_CONFIG_"+name] = getattr(config, name)
    return defines

def _getPatchExe(patchExe=None):
    if patchExe is None:
        try:
            patchExe = which.which("patch")
        except which.WhichError:
            raise Error("could not find a 'patch' executable on your PATH")
    # Assert that it exists.
    if not os.path.exists(patchExe):
        raise Error("'%s' does not exist" % patchExe)
    # Assert that this isn't cygwin patch on Windows.
    if re.search("(?i)cygwin", os.path.abspath(patchExe)):
        raise Error("'%s' looks like it is from Cygwin. This patch.exe "
                    "tends to convert EOLs to Unix-style willy-nilly. "
                    "Find a native patch.exe. (Note: Trent and Gsar "
                    "have one.)" % patchExe)
    #XXX Assert that it isn't the sucky default Solaris patch.
    return patchExe


def _assertCanApplyPatch(patchExe, patchFile, sourceDir, reverse=0,
                         patchSrcFile=None, patchArgs=[]):
    """Raise an error if the given patch will not apply cleanly (does not
    raise if the patch is already applied).
    
        "patchExe" is a path to a patch executable to use.
        "patchFile" is the path the the patch file.
        "sourceDir" is the base directory of the source tree to patch. All
            patches are presumed to be applicable from this directory.
        "reverse" (optional, default false) is a boolean indicating if the
            patch should be considered in reverse.
        "patchSrcFile" (optional) is the path to the patch _source_ location
            for helpful error messages -- the patch may have been processed.
        "patchArgs" (optional) is a list of patch executable arguments to
            include in invocations.
    """
    inReverse = (reverse and " in reverse" or "")
    log.debug("assert can apply patch%s: %s", inReverse, patchFile)
    baseArgv = [patchExe, "-f", "-p0", "-g0"] + patchArgs
    patchContent = open(patchFile, 'r').read()

    # Skip out if the patch has already been applied.
    argv = baseArgv + ["--dry-run"]
    if not reverse:
        argv.append("-R")
    log.debug("    see if already applied%s: run %s in '%s'", inReverse,
              argv, sourceDir)
    stdout, stderr, retval = _run(argv, cwd=sourceDir, stdin=patchContent)
    if not retval: # i.e. reverse patch would apply
        log.debug("    patch already applied%s: skipping", inReverse)
        return

    # Fail if the patch would not apply cleanly.
    argv = baseArgv + ["--dry-run"]
    if reverse:
        argv.append("-R")
    log.debug("    see if will apply cleanly%s: run %s in '%s'", inReverse,
              argv, sourceDir)
    stdout, stderr, retval = _run(argv, cwd=sourceDir, stdin=patchContent)
    if retval:
        raise Error("""\
patch '%s' will not apply cleanly%s:
   patch source: %s
   argv:         %s
   stdin:        %s
   cwd:          %s
   stdout:
%s
   stderr:
%s
""" % (patchFile, inReverse, patchSrcFile or patchFile,
       argv, patchFile, sourceDir, stdout, stderr))


def _diffPaths(a, b):
    return list(difflib.unified_diff(
        open(a, 'r').readlines(),
        open(b, 'r').readlines(),
        fromfile=a,
        tofile=b,
    ))

def _getPathsInPatch(patch, argv):
    """Given the contents of a patch file, return the file paths involved
    @param patch {file or str}
    @param argv {iterable} arguments to patch; used to calculate depth
    @returns a tuple of length 2; the first item is the set of files that were
        removed, the second is the set that were added.
    """
    if isinstance(patch, basestring):
        patch = patch.splitlines()
    removed = set()
    added = set()
    # These are in English because the typical Komodo developer works on English
    # systems; we really could use a proper patch parser... :|
    filter_expressions = (
        re.compile(r"\s+\(revision \d+\)$"),
        re.compile(r"\s+(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+"
                     "(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+"
                     "\d+\s+(?:\d+:?)+\s+\d+$")
    )
    depth = 0
    for argi, arg in enumerate(argv or []):
        if arg.startswith("-p"):
            if arg == "-p":
                depth = int(argv[argi + 1])
            else:
                depth = int(arg[len("-p"):])
        elif arg.startswith("--strip"):
            if arg == "--strip":
                depth = int(argv[argi + 1])
            else:
                depth = int(arg[len("--strip=")])

    for line in patch:
        line = line.rstrip("\r\n")
        action = None
        if line.startswith("--- "):
            action = removed
            path = line.split(" ", 1)[-1]
        elif line.startswith("+++ "):
            action = added
            path = line.split(" ", 1)[-1]
        elif line.startswith("rename from ") or line.startswith("copy from "):
            action = removed
            path = line.split(" ", 2)[-1]
        elif line.startswith("rename to ") or line.startswith("copy to "):
            action = added
            path = line.split(" ", 2)[-1]
        else:
            continue
        path = path.split("\t", 1)[0]
        for expr  in filter_expressions:
            match = expr.search(path)
            if match:
                path = path[:match.start()] + path[match.end():]
        if path in ("/dev/null",):
            continue
        action.add("/".join(path.rstrip().split("/")[depth:]))
    return (removed, added)

def _shouldPreprocess(filename):
    """Determine if should preprocess the given file.
    We preprocess FILE.p.EXT and FILE.p files.

    Returns a two-tuple:
        First element is whether preprocessing should take place (True/False)
        Second element is the file name (without .p if it should be
            preprocessed, same as the input otherwise)
    """
    parts_a = splitext(filename)
    if parts_a[1] == '.p':
        return (True, parts_a[0])
    parts_b = splitext(parts_a[0])
    if parts_b[1] == '.p':
        return (True, parts_b[0]+parts_a[1])
    return (False, filename)

def _applyPatch(patchExe, baseDir, patchRelPath, sourceDir, reverse=0,
                dryRun=0, patchArgs=[]):
    """Apply a patch file to the given source directory.
    
        "patchExe" is a path to a patch executable to use.
        "baseDir" is the base directory of the working patch set image.
        "patchRelPath" is the relative path of the patch under the working
            directory.
        "sourceDir" is the base directory of the source tree to patch. All
            patches are presumed to be applicable from this directory.
        "reverse" (optional, default false) is a boolean indicating if the
            patch should be considered in reverse.
        "dryRun" (optional, default false), if true, indicates that
            everything but the actual patching should be done.
        "patchArgs" (optional) is a list of patch executable arguments to
            include in invocations.
    """
    inReverse = (reverse and " in reverse" or "")
    baseArgv = [patchExe, "-f", "-p0", "-g0"] + patchArgs
    # ToddW: "--binary" breaks patching of Scintilla.
    #if sys.platform.startswith("win"):
    #    baseArgv.insert(1, "--binary")
    patchFile = os.path.join(baseDir, patchRelPath)
    with open(patchFile, "r") as patchStream:
        patchContent = patchStream.read()

    # Skip out if the patch has already been applied.
    argv = baseArgv + ["--dry-run"]
    if not reverse:
        argv.append("-R")
    stdout, stderr, retval = _run(argv, cwd=sourceDir, stdin=patchContent)
    if not retval: # i.e. reverse patch would apply
        log.info("skip application of '%s'%s: already applied", patchRelPath,
                 inReverse)
        return

    lineEndingFixes = {} # path -> expected line ending
    if not dryRun and sys.platform.startswith("win"):
        # on Windows, we need to convert everything to use DOS line endings, so
        # that patch.exe can deal with them - and then convert back after
        for resultRelPath in _getPathsInPatch(patchContent, baseArgv)[1]:
            if not resultRelPath:
                continue
            resultPath = join(sourceDir, resultRelPath)
            if exists(resultPath):
                with open(resultPath, "rU") as destFile:
                    filter(lambda n: False, destFile)
                    lineEndingFixes[resultRelPath] = destFile.newlines
            else:
                log.debug("Failed to find file %s", resultPath)

    log.debug("line endings: %s", lineEndingFixes)

    # Apply the patch.
    if dryRun:
        log.info("apply '%s'%s (dry run)", patchRelPath, inReverse)
        argv = baseArgv + ["--dry-run"]
    else:
        log.info("apply '%s'%s", patchRelPath, inReverse)
        argv = baseArgv
    sys.stdout.write("apply '%s'%s\n" % (patchRelPath, inReverse))
    if reverse:
        argv.append("-R")
    log.debug("run %s in '%s' (stdin '%s')", argv, sourceDir, patchFile)
    stdout, stderr, retval = _run(argv, cwd=sourceDir, stdin=patchContent)
    sys.stdout.write(stdout)
    sys.stdout.flush()
    if retval:
        raise Error("error applying patch '%s'%s: argv=%r, cwd=%r, retval=%r"
                    % (patchFile, inReverse, argv, sourceDir, retval))

    # Fix up line endings
    if not dryRun and sys.platform.startswith("win"):
        for resultRelPath, lineEnds in lineEndingFixes.items():
            log.debug("File %s: %r", resultRelPath, lineEnds)
            if lineEnds == "\n":
                path = join(sourceDir, resultRelPath)
                if not exists(path):
                    continue
                log.debug("Fixing line endings for %s", path)
                tempDir = tempfile.mkdtemp()
                try:
                    tempFile = join(tempDir, basename(resultRelPath))
                    os.rename(path, tempFile)
                    try:
                        with open(tempFile, "rU") as infile:
                            with open(path, "wb") as outfile:
                                for line in infile.read().splitlines(False):
                                    outfile.write(line + "\n")
                        os.remove(tempFile)
                    except:
                        if exists(tempFile):
                            os.rename(tempFile, path)
                finally:
                    sh.rm(tempDir)

def _loadPatchLog(logDir, logFilename=None):
    """Return the given patch log as a module"""
    if logFilename is None:
        logFilename = "__patchlog__.py"
    patchLogFile = os.path.join(logDir, logFilename)
    patchLogName = os.path.splitext(os.path.basename(patchLogFile))[0]
    patchLogPyc = os.path.splitext(patchLogFile)[0] + ".pyc"
    if os.path.isfile(patchLogPyc):
        # If the .py is newer than the .pyc, the .pyc sometimes (always?)
        # gets imported instead, causing problems.
        os.remove(patchLogPyc)
    try:
        file, path, desc = imp.find_module(patchLogName, [logDir])
        patchLog = imp.load_module(patchLogName, file, path, desc)
    except ImportError, ex:
        raise Error("could not find a patch log in the given log "
                    "directory, '%s': %s" % (logDir, ex))
    return patchLog

def _areFilesEqual(leftPath, rightPath):
    """Check if the two given files (or, if they are directories, their
    contents) are equal."""
    if isdir(leftPath):
        if not isdir(rightPath):
            return False
        found_paths = set()
        for dirpath, dirnames, filenames in os.walk(leftPath):
            for filename in filenames:
                relpath = os.path.relpath(join(dirpath, filename), leftPath)
                if not _areFilesEqual(join(leftPath, relpath),
                                      join(rightPath, relpath)):
                    return False
                found_paths.add(join(rightPath, relpath))
        for dirpath, dirnames, filenames in os.walk(rightPath):
            for filename in filenames:
                if join(dirpath, filename) not in found_paths:
                    return False
        return True
    try:
        with open(leftPath, "rb") as left_file:
            left_md5 = md5(left_file.read())
        with open(rightPath, "rb") as right_file:
            right_md5 = md5(right_file.read())
    except IOError as ex:
        log.debug("left path %s, right path %s: IO Error %s",
                  leftPath, rightPath, ex)
        return False
    if left_md5.hexdigest ()!= right_md5.hexdigest():
        log.debug("left path %s != right path %s: %s/%s",
                  leftPath, rightPath, left_md5.hexdigest(), right_md5.hexdigest())
        return False
    return True

def _unapplyOneAction(action, sourceDir, logDir, dryRun, patchExe, info=log.info):
    if action[0] in ("apply", "preprocess & apply"):
        _applyPatch(patchExe, logDir, action[2], sourceDir, reverse=1,
                    dryRun=dryRun, patchArgs=action[3])
    elif action[0] == "add":
        # ("add", <patches-basedir>, <src-relpath>, <dst-relpath>,
        #  <force>)
        # e.g. ("add", "patches", "hpux_cpp_ext\\thingy.s", "python",
        #       False)
        baseToDel = os.path.join(action[3], os.path.basename(action[2]))
        toDel = os.path.join(sourceDir, baseToDel)
        if not os.path.exists(toDel):
            info("skipping undo add of '%s': not found", baseToDel)
        elif dryRun:
            info("undo add of '%s' (dry run)", baseToDel)
        else:
            info("undo add of '%s'", baseToDel)
            sh.rm(toDel)
    elif action[0] == "remove":
        # ("remove", <patches-basedir>, <dst-relpath>)
        atticLoc = os.path.join(logDir, "__attic__", action[2])
        sourceLoc = os.path.join(sourceDir, action[2])
        if os.path.exists(sourceLoc) and os.path.isfile(atticLoc):
            # Try to intelligently skip the re-add if it is not
            # necessary.
            with open(atticLoc, 'rb') as fin:
                atticmd5 = md5(fin.read()).hexdigest()
            if os.path.isfile(sourceLoc):
                sourceFile = sourceLoc
            else:
                sourceFile = os.path.join(dst, os.path.basename(sourceLoc))
            if os.path.exists(sourceFile):
                with open(sourceFile, 'rb') as fin:
                    sourcemd5 = md5(fin.read()).hexdigest()
                if atticmd5 == sourcemd5:
                    info("skip restoration of '%s' from attic: "
                         "already restored", action[2])
                    return
        if dryRun:
            info("restore '%s' from attic (dry run)", action[2])
        else:
            info("restore '%s' from attic", action[2])
            sh.copy(atticLoc, sourceLoc)
    else:
        raise Error("unknown action, '%s', in patch log: %s"
                    % (action[0], action))

#---- public API

def unpatch(sourceDir, logDir, dryRun=0, patchExe=None, logFilename=None):
    """Backout the given patches from the given source tree.

        "sourceDir" is the base directory of the source tree to unpatch.
        "logDir" is the directory in which the patch set to unpatch was
            logged.
        "dryRun" (optional, default false) is a boolean indicating that
            everything except actually unpatching should be done.
        "patchExe" (optional) can be used to specify a particular patch
            executable to use. Otherwise one is automatically found from
            the environment.

    The given patch tree (or patch trees) is processed as described in the
    module docstring above. First, the set of patches that should be backed
    out is determined. Then is it checked that all patches _can_ be backed
    out. Then all unpatching is done. "Error" is raised if all patches cannot
    be backed out. There is no return value. An error is NOT raised if it
    looks like all patches have already been backed out.
    """
    log.debug("unpatch(logDir=%r, dryRun=%r)", logDir, dryRun)

    # Find the patch log and import it, or error out.
    patchLog = _loadPatchLog(logDir, logFileName)
    #pprint.pprint(patchLog.actions)

    # Check that all actions can be undone.
    patchExe = _getPatchExe(patchExe)
    for action in patchLog.actions:
        if action[0] in ("apply", "preprocess & apply"):
            # Check that the patch can be applied in reverse.
            _assertCanApplyPatch(patchExe,
                                 os.path.join(logDir, action[2]),
                                 sourceDir,
                                 reverse=1,
                                 patchArgs=action[3])
        elif action[0] == "add":
            # Should always just be able to remove the file.
            pass
        elif action[0] == "remove":
            # Ensure that the file is in the attic.
            atticLoc = os.path.join(logDir, "__attic__", action[2])
            if not os.path.exists(atticLoc):
                raise Error("cannot undo removal of '%s': removed file is "
                            "not in the attic: %s" % (action[2], atticLoc))
        else:
            raise Error("unknown action, '%s', in patch log: %s"
                        % (action[0], action))

    # Undo each action
    for action in patchLog.actions:
        _unapplyOneAction(action, sourceDir, logDir, dryRun, patchExe)

def patch(patchesDir, sourceDir, config=None, logDir=None, dryRun=0,
          patchExe=None, logFilename=None):
    """Patch the given source tree with the given patches.
    
        "patchesDir" is a directory tree of patches to apply or a single
            patch file to apply. Alternatively it may be _list of_ patch
            directories and/or files.
        "sourceDir" is the base directory of the source tree to patch.
        "config" is a configuration object to pass to __patchinfo__.py
            special control functions. Typically it is a configuration
            module object but can be any object expected by the given
            patch directories.
        "logDir" (optional, default None) is a directory in which applied
            patches are logged. By default this is not created, however some
            projects want to create a package including all differences
            applied to a base source tree. If the package dir already exists
            it is deleted and re-created. As well, using a logDir is required
            to be able to unpatch().
        "dryRun" (optional, default false) is a boolean indicating that
            everything except actually applying patches should be done.
        "patchExe" (optional) can be used to specify a particular patch
            executable to use. Otherwise one is automatically found from
            the environment.
    
    The given patch tree (or patch trees) is processed as described in the
    module docstring above. First, the set of patches that should be applied
    is determined. Then is it checked that all patches _can_ be applied.
    Then all patches are applied. "Error" is raised if all patches cannot
    be applied. There is no return value. An error is NOT raised if it looks
    like all patches have already been applied.
    """
    log.debug("patch(patchesDir=%r, sourceDir=%r, config=%r, logDir=%r, "
              "dryRun=%r)", patchesDir, sourceDir, config, logDir, dryRun)

    # Determine what patch actions should be carried out.
    # "actions" is a list of the following possible actions:
    #   ("apply",              <patches-basedir>, <patchfile-relpath>, <patch-args>)
    #   ("preprocess & apply", <patches-basedir>, <patchfile-relpath>, <patch-args>)
    #   ("add",                <patches-basedir>, <src-relpath>, <dst-relpath>, <force>)
    #   ("remove",             <patches-basedir>, <dst-relpath>)
    # Some notes:
    # - The "add" and "remove" paths can be directories.
    # - When add'ing a file, if its basename is of the form
    #   "BASE.p.EXT", then it will be preprocessed to "BASE.EXT".
    # - Actions will always be in the order (remove, add, apply)
    actions = []
    for patchSpec in patchesDir:
        if os.path.isfile(patchSpec):
            actions.append( ("apply", os.path.dirname(patchSpec),
                             os.path.basename(patchSpec)) )
        elif os.path.isdir(patchSpec):
            # Always skip SCC control dirs.
            if basename(patchSpec) in _SCC_control_dirs:
                continue
            _determinePatchesFromDirectory(patchSpec, actions, config)
        else:
            raise Error("patches directory or file does not exist: '%s'"
                        % patchSpec)
    log.debug("patch set: %s" % pprint.pformat(actions))

    # We will use a working directory to apply all patches.  We will:
    # 1. Preprocess any patches as necessary
    # 2. Copy files to be removed into the attic (of the patchlog), as well as
    #    a pristine copy of what we will be adding.
    # 3. If a logDir is available, figure out how much of the patch is already
    #    applied; undo conflicting actions and only do the rest of the actions
    # 4. Determine all files that will be patched (i.e. the --- files)
    # 5. Copy all of those files into the working directory
    # 6. Apply all the actions in order
    # 7. Store the patch log
    # 8. Remove files to be deleted for real
    # 9. Copy the working directory into the destination
    # We're doing everything in the working directory to ensure that the patches
    # can be applied *without* trying a dry run first; this is necessary because
    # patches might depend on previous patches in the queue.
    # Note that we'll also be dropping a ".patchtree-state" file in the source
    # (i.e. patched) directory; this is used as a marker to make sure that if
    # that directory is deleted re-fetched we will be able to re-apply the
    # patches.

    if logFilename is None:
        logFilename = "__patchlog__.py"
    patchExe = _getPatchExe(patchExe)

    # Create a clean working directory.
    tempDir = tempfile.mkdtemp()
    if sys.platform.startswith("win"):
        # Windows patching leaves around temp files, so we work around this
        # problem by setting a different temp directory, which is later removed
        # at the end of this patching.
        oldTmpDir = os.environ.get("TMP")
        os.mkdir(join(tempDir, "tempdir"))
        os.environ["TMP"] = join(tempDir, "tempdir")
    log.debug("created patch working dir: '%s'" % tempDir)

    try:
        tmpLogDir = join(tempDir, "patchlog")
        os.makedirs(join(tmpLogDir, "__attic__")) # for unpatching removed files

        # 1. Preprocess any patches as necessary
        defines = None # preprocessor defines are lazily calculated
        for action in actions:
            if action[0] not in ("apply", "preprocess & apply"):
                continue
            # Copy the patch file over; it's easier to deal with
            src = join(action[1], action[2])
            dst = join(tmpLogDir, action[2])
            if os.path.isfile(dst):
                raise Error("conflicting patch file '%s': you have a "
                            "patch of the same name in more than one "
                            "patches tree", action[2])
            if not isdir(dirname(dst)):
                os.makedirs(dirname(dst))
            if action[0] == "preprocess & apply":
                if defines is None:
                    defines = _getPreprocessorDefines(config)
                    #log.debug("defines: %s", pprint.pformat(defines))
                log.debug("preprocess '%s' to '%s'",
                          src, os.path.relpath(dst, tempDir))
                preprocess.preprocess(src, dst, defines=defines,
                                      substitute=1)
            else:
                log.debug("cp '%s' to '%s'", src, os.path.relpath(dst, tempDir))
                sh.copy(src, dst)

        # 2. Copy files to be removed into the attic (of the patchlog), as well
        #    as a pristine copy of what we will be adding.
        atticDir = join(tmpLogDir, "__attic__")
        oldAtticDir = join(logDir, "__attic__")
        for action in actions:
            if action[0] == "add":
                src = join(action[1], action[2])
                dst = join(tmpLogDir, action[2])
                log.debug("cp '%s' to '%s'", src, join("patchlog", action[2]))
                for dirpath, dirnames, filenames in os.walk(src):
                    for filename in filenames:
                        srcpath = join(dirpath, filename)
                        relpath = os.path.relpath(srcpath, src)
                        do_preprocess, dstpath = \
                            _shouldPreprocess(join(dirpath, join(dst, relpath)))
                        if do_preprocess:
                            if defines is None:
                                defines = _getPreprocessorDefines(config)
                            log.info("add '%s' to '%s' (with preprocessing",
                                     relpath, dst)
                            dstparent = os.path.dirname(dstpath)
                            if not exists(dstparent):
                                os.makedirs(dstparent)
                            preprocess.preprocess(srcpath, dstpath,
                                                  defines=defines, substitute=1)
                        else:
                            log.info("add '%s' to '%s'", srcpath, relpath)
                            sh.copy(srcpath, dstpath)
            elif action[0] == "remove":
                if not exists(atticDir):
                    os.makedirs(atticDir)
                origLoc = join(sourceDir, action[2])
                oldAtticLoc = join(oldAtticDir, action[2])
                atticLoc = join(atticDir, action[2])
                for location in [oldAtticLoc, origLoc]:
                    if exists(location):
                        log.debug("cp '%s' to attic", origLoc)
                        sh.copy(location, atticLoc)
                        break

        # (At this point, the patchlog is complete; it has everything needed to
        # bring an unpatched source into the patched state.)

        # 3. If a logDir is available, figure out how much of the patch is
        #    already applied; undo conflicting actions and only do the rest of
        #    the actions
        firstInvalidActionIndex = 0 # default to do everything...
        if logDir and isdir(logDir):
            log.debug("logDir exists, examining patch state...")
            patchLog = _loadPatchLog(logDir, logFilename)
            if patchLog.sourceDir != sourceDir:
                raise Error("Patch log exists, but is for a different source "
                            "directory (%s instead of %s); please unapply "
                            "patches manually or use a different patch log "
                            "directory." % (patchLog.sourceDir, sourceDir))
            firstInvalidActionIndex = len(patchLog.actions)
            for index, action in reversed(tuple(enumerate(patchLog.actions))):
                try:
                    if repr(actions[index]) != repr(action):
                        # action isn't even the same one; make sure to unapply it
                        firstInvalidActionIndex = index
                        continue
                except IndexError:
                    firstInvalidActionIndex = index
                    continue
                if action[0] in ("apply", "preprocess & apply"):
                    relpath = action[2]
                    if not _areFilesEqual(join(logDir, relpath),
                                          join(tmpLogDir, relpath)):
                        firstInvalidActionIndex = index
                elif action[0] == "add":
                    relpath = action[2]
                    if not _areFilesEqual(join(logDir, relpath),
                                          join(tmpLogDir, relpath)):
                        firstInvalidActionIndex = index
                elif action[0] == "remove":
                    relpath = action[2]
                    if not _areFilesEqual(join(logDir, "__attic__", relpath),
                                          join(tmpLogDir, "__attic__", relpath)):
                        firstInvalidActionIndex = index
                else:
                    raise Error("Don't know how to deal with previously recorded "
                                "action %s", action[0])

            invalidActions = patchLog.actions[firstInvalidActionIndex:]

            if firstInvalidActionIndex > 0:
                expected_md5 = md5(repr(patchLog.actions)).hexdigest()
                logFileFullName = join(logDir, logFilename)
                log.debug("full name: %s", logFileFullName)
                with open(join(sourceDir, ".patchtree-state"), "a+") as state_file:
                    for line in state_file:
                        parts = line.strip().rsplit(None, 1)
                        if len(parts) != 2:
                            continue # invalid state?
                        log.debug("got: %s", parts[0])
                        if parts[0] == logFileFullName:
                            if parts[1] not in (expected_md5, "ignore"):
                                log.warn("Patch state does not match patch log, "
                                         "assuming no patches are applied")
                                firstInvalidActionIndex = 0
                                invalidActions = []
                            break
                    else:
                        log.warn("Patch state missing for the given log, "
                                 "assuming no patches are applied")
                        firstInvalidActionIndex = 0
                        invalidActions = []

            log.debug("Will unapply %s actions from old patch out of %s",
                      len(invalidActions), len(patchLog.actions))

            # Un-apply all the actions that are now invalid
            for action in reversed(invalidActions):
                _unapplyOneAction(action, sourceDir, logDir, False,
                                  patchExe, info=lambda *args: None)

            if firstInvalidActionIndex > 0:
                action = patchLog.actions[firstInvalidActionIndex - 1]
                log.info("Skipping %s patches already applied; "
                         "last skipped patch is %s %s",
                         firstInvalidActionIndex, action[0], action[2])

        # 4. Determine all files that will be patched (i.e. the --- files)
        modified_relpaths = set()
        for action in actions[firstInvalidActionIndex:]:
            if action[0] not in ("apply", "preprocess & apply"):
                continue
            with open(join(tmpLogDir, action[2]), "r") as patch_contents:
                modified_relpaths.update(_getPathsInPatch(patch_contents, action[3])[0])
        log.debug("All modified files: %s", pprint.pformat(sorted(modified_relpaths)))

        # 5. Copy all of those files into the working directory
        workDir = join(tempDir, "workdir")
        if not exists(workDir):
            os.makedirs(workDir)
        for modified_relpath in modified_relpaths:
            modified_srcpath = join(sourceDir, modified_relpath)
            modified_destpath = join(workDir, modified_relpath)
            # source might not exist if we're adding it later
            if exists(modified_destpath):
                pass
            elif exists(modified_srcpath):
                log.debug("copy '%s' -> '%s'", modified_srcpath, modified_destpath)
                sh.copy(modified_srcpath, modified_destpath)

        # 6. Apply all the actions in order
        def _add_it(s, d, force=False):
            """A little helper for doing the 'add' action with appropriate
            logging.
            """
            if not exists(dirname(d)):
                os.makedirs(dirname(d))
            if _areFilesEqual(s, d):
                log.info("skip add of '%s' to '%s': "
                         "no changes",
                         os.path.relpath(s, tempDir),
                         os.path.relpath(d, tempDir))
            else:
                log.info("%s '%s' to '%s'",
                         "replace" if exists(d) else "add",
                         os.path.relpath(s, tempDir),
                         os.path.relpath(d, tempDir))
                sh.copy(s, d)

        for action in actions[firstInvalidActionIndex:]:
            if action[0] in ("apply", "preprocess & apply"):
                log.debug("Applying patch %s", action[2])
                _applyPatch(patchExe, tmpLogDir, action[2],
                            workDir, patchArgs=action[3])
            elif action[0] == "add":
                src = join(tmpLogDir, action[2])
                dst = join(workDir, action[3])
                log.debug("add %s -> %s", src, dst)
                if isdir(src):
                    for dirpath, dirnames, filenames in os.walk(src):
                        subpath = (dirpath == src
                                   and os.curdir
                                   or dirpath[len(src)+1:])
                        for filename in filenames:
                            s = join(dirpath, filename)
                            d = normpath(join(dst, subpath, filename))
                            _add_it(s, d, force=action[4])
                else:
                    d = isfile(dst) and dst or join(dst, basename(src))
                    _add_it(src, d, force=action[4])
            elif action[0] == "remove":
                dst = join(workDir, action[2])
                if exists(dst):
                    sh.rm(dst)
            else:
                raise Error("unknown patch action '%s': %r"
                                % (action[0], action))

        # Up to this point, we still haven't actually changed the sourceDir.
        # Bail out now if we're really just doing a dry run.
        if dryRun:
            return
        log.info("Patch verification complete, copying results back...")

        # 7. Store the patch log
        if logDir:
            # Log actions.
            patchLogFile = join(tmpLogDir, logFilename)
            with open(patchLogFile, "w") as patchLog:
                patchLog.write("""\
# Patch log (%s)
#
# WARNING: This file is automatically generated by patchtree.py. Any
#          Changes you make will be lost.

sourceDir = %r
actions = %s
""" % (time.asctime(), sourceDir, pprint.pformat(actions)))
            if exists(logDir):
                sh.rmtree(logDir)
            sh.copy(tmpLogDir, logDir)

            state = {}
            logFileFullName = join(logDir, logFilename)
            with open(join(sourceDir, ".patchtree-state"), "a+") as state_file:
                for line in state_file:
                    parts = line.strip().rsplit(None, 1)
                    if len(parts) != 2:
                        continue # invalid state?
                    state[parts[0]] = parts[1]
            state[logFileFullName] = md5(repr(actions)).hexdigest()
            with open(join(sourceDir, ".patchtree-state"), "w") as state_file:
                for k, v in state.items():
                    state_file.write("%s %s\n" % (k, v))

        # 8. Remove files to be deleted for real
        for action in actions[firstInvalidActionIndex:]:
            if action[0] != "remove":
                continue
            dst = os.path.join(sourceDir, action[2])
            if not os.path.exists(dst):
                log.info("skip removal of '%s': already removed",
                         action[2])
            elif dryRun:
                log.info("remove '%s' (dry run)", action[2])
            else:
                log.info("remove '%s'", dst)
                sh.rm(dst)

        # 9. Copy the working directory into the destination
        absSourceDir = os.path.abspath(sourceDir)
        for dirpath, dirnames, filenames in os.walk(workDir):
            for name in filenames:
                src = join(workDir, dirpath, name)
                dst = join(absSourceDir, os.path.relpath(dirpath, workDir), name)
                log.debug("cp '%s' to '%s'", src, dst)
                sh.copy(src, dst)

    finally:
        log.debug("removing temporary working dir '%s'", tempDir)
        try:
            sh.rm(tempDir)
        except EnvironmentError, ex:
            log.warn("could not remove temp working dir '%s': %s",
                     tempDir, ex)
        if sys.platform.startswith("win") and oldTmpDir is not None:
            os.environ["TMP"] = oldTmpDir



#---- mainline

def main(argv):
    # Process options.
    log.setLevel(logging.INFO)
    try:
        optlist, args = getopt.getopt(argv[1:], "hvVc:L:R",
            ["help", "verbose", "version", "config=", "log-dir=",
             "dry-run"])
    except getopt.GetoptError, msg:
        raise Error("patchtree: %s" % str(msg))
    config = None
    logDir = None
    dryRun = 0
    action = "patch"
    for opt, optarg in optlist:
        if opt in ("-h", "--help"):
            sys.stdout.write(__doc__)
            return 0
        elif opt in ("-V", "--version"):
            print "patchtree %s" % __version__
            return 0
        elif opt in ("-v", "--verbose"):
            log.setLevel(logging.DEBUG)
        elif opt in ("-L", "--log-dir"):
            logDir = optarg
        elif opt in ("-c", "--config"):
            ext = os.path.splitext(optarg)[1]
            if sys.platform == "win32":
                ext = ext.lower()
            for desc in imp.get_suffixes():
                if desc[0] == ext:
                    fin = open(optarg, 'r')
                    config = imp.load_module("config", fin, optarg, desc)
                    break
            else:
                raise Error("given config file does not look like an "
                            "importable Python module: %s" % optarg)
        elif opt in ("--dry-run",):
            dryRun = 1
        elif opt in ("-R",):
            action = "unpatch"
    
    # Process arguments
    if len(args) < 2:
        raise Error("not enough arguments: you must specify a source "
                    "directory and at least one patches dir "
                    "(or file): %r" % args)
    src, patches = args[0], args[1:]
    
    if action == "patch":
        patch(patches, src, config=config, logDir=logDir, dryRun=dryRun)
    elif action == "unpatch":
        unpatch(src, logDir=logDir, dryRun=dryRun)
    else:
        raise Error("unknown action: '%s'" % action)


if __name__ == "__main__":
    logging.basicConfig()
    try:
        retval = main(sys.argv)
    except KeyboardInterrupt:
        sys.exit(1)
    except:
        exc_info = sys.exc_info()
        if log.isEnabledFor(logging.DEBUG):
            print
            traceback.print_exception(*exc_info)
        else:
            log.error("%s: %s", exc_info[0].__name__, exc_info[1])
        sys.exit(1)
    else:
        sys.exit(retval)


