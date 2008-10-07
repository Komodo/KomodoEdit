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
    already applied. Applying the patch set is atomic. Etc.
    

    Here is how it works. You specify a source directory and a number of
    patch directories (or files). Any directory may have a __patchinfo__.py
    Python module to control how that directory tree of patches is applied.
    That module may define any of the following special functions:
    
        def applicable(config)
            Should return true if this directory tree should be considered
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
        def patch_args(config):
            Return None or a list of command line args to add to patch.exe
            invocations. E.g. to set the fuzz level to 3 one would return
            ['-F3']. Note that spaces in args are quoted so separate args as
            separate list elements. In the previous example, ['-F 3'] is wrong
            but ['-F3'] or ['-F', '3'] or ['--fuzz', '3'] are okay.
            XXX Should use this patch arg info for unpatching.
    
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
"""
# TODO:
# - break this out into a separate project
# - add a test suite

__version_info__ = (0, 4, 1)
__version__ = '.'.join(map(str, __version_info__))

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

def _createTempDir():
    """Create a temporary directory and return the path to it."""
    if hasattr(tempfile, "mkdtemp"): # use the newer mkdtemp is available
        path = tempfile.mkdtemp()
    else:
        path = tempfile.mktemp()
        os.makedirs(path)
    return path

def _getPatchInfo(dirname):
    if "__patchinfo__" in sys.modules:
        del sys.modules["__patchinfo__"]
    for p in glob(join(dirname, "__patchinfo__.py[co]")):
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

def _shouldBeApplied((base, actions, config), dirname, names):
    """os.path.walk visitor to process patch directories for appropriate
    patch actions.
    """
    log.debug("process patch dir '%s'", dirname)
    patchinfo = _getPatchInfo(dirname)
    if patchinfo: log.debug("    patchinfo: %r", patchinfo)
    
    # Always skip SCC control dirs.
    for exclude_dir in (".svn", ".hg", "CVS"):
        if exclude_dir in names and isdir(join(dirname, exclude_dir)):
            names.remove(exclude_dir)
    
    # Skip this dir if patchinfo says it should not be applied.
    if patchinfo and hasattr(patchinfo, "applicable") and\
       not patchinfo.applicable(config):
        log.debug("    skip: applicable() returned false")
        while names:
            del names[0]
        return

    # See if there are any special patch_args for patches in this dir.
    if patchinfo and hasattr(patchinfo, "patch_args"):
        patch_args = patchinfo.patch_args(config) or []
        if not isinstance(patch_args, list):
            raise Error("patch_args() in '%s' did not return a list (or None): %s"\
                        % (patchinfo.__file__, patch_args))
    else:
        patch_args = []

    # Add "apply" actions for patch files.
    for pattern in ("*.patch", "*.diff"):
        for patchfile in glob.glob(os.path.join(dirname, pattern)):
            patchfile = patchfile[len(base+os.sep):]
            action = ("apply", base, patchfile, patch_args)
            log.debug("    action: %r", action)
            actions.append(action)
    for pattern in ("*.ppatch",):
        for patchfile in glob.glob(os.path.join(dirname, pattern)):
            patchfile = patchfile[len(base+os.sep):]
            action = ("preprocess & apply", base, patchfile, patch_args)
            log.debug("    action: %r", action)
            actions.append(action)

    # Add "add" and "remove" actions action to the patchinfo, if any.
    if patchinfo and hasattr(patchinfo, "add"):
        retval = patchinfo.add(config)
        if type(retval) not in (types.TupleType, types.ListType):
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
            src = os.path.join(dirname, filename)
            if os.path.isdir(src) and os.path.basename(src) in names:
                # If a subdirectory is being used for an "add" action,
                # then don't consider it as a patchtree.
                names.remove(os.path.basename(src))
            src = src[len(base+os.sep):]
            action = ("add", base, src, dst, force)
            log.debug("    action: %r", action)
            actions.append(action)
    if patchinfo and hasattr(patchinfo, "remove"):
        retval = patchinfo.remove(config)
        if type(retval) not in (types.TupleType, types.ListType):
            raise Error("invalid return type from remove() in %s, "
                        "must return a sequence: retval=%r"
                        % (patchinfo.__file__, retval))
        for dst in retval:
            action = ("remove", base, dst)
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


def _assertCanAddFile(src, dst, patchSrcPath):
    """Raise an Error if the target file exists and is
    different than the source.
    """
    if os.path.isfile(dst):
        dstPath = dst
    else:
        dstPath = os.path.join(dst, os.path.basename(src))
    if not os.path.exists(dstPath):
        return
    fin = open(src, 'rb')
    try:
        src_content = fin.read()
        src_md5 = md5(src_content).hexdigest()
    finally:
        fin.close()
    fin = open(dstPath, 'rb')
    try:
        dst_content = fin.read()
        dst_md5 = md5(dst_content).hexdigest()
    finally:
        fin.close()
    if src_md5 != dst_md5:
        if _is_content_binary(src_content) or _is_content_binary(dst_content):
            raise Error("cannot add `%s': changes in `%s' would be lost "
                        "(binary files differ)" % (patchSrcPath, dstPath))
        else:
            diff = list(difflib.unified_diff(
                src_content.splitlines(1),
                dst_content.splitlines(1),
                fromfile=src,
                tofile=dstPath,
            ))
            diff = '    '.join(diff)
            raise Error("""\
cannot add `%s': changes in `%s' would be lost:
    %s""" % (patchSrcPath, dstPath, diff))


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


def _shouldPreprocess(filename):
    """Determine if should preprocess the given file.
    We preprocess FILE.p.EXT and FILE.p files.

    Returns:
        (<True or False>, <filename-without-.p-if-True>)
    """
    parts_a = splitext(filename)
    if parts_a[1] == '.p':
        return (True, parts_a[0])
    parts_b = splitext(parts_a[0])
    if parts_b[1] == '.p':
        return (True, parts_b[0]+parts_a[1])
    return (False, None)

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
    patchFile = os.path.join(baseDir, patchRelPath)
    patchContent = open(patchFile, 'r').read()

    # Skip out if the patch has already been applied.
    argv = baseArgv + ["--dry-run"]
    if not reverse:
        argv.append("-R")
    stdout, stderr, retval = _run(argv, cwd=sourceDir, stdin=patchContent)
    if not retval: # i.e. reverse patch would apply
        log.info("skip application of '%s'%s: already applied", patchRelPath,
                 inReverse)
        return

    # Apply the patch.
    if dryRun:
        log.info("apply '%s'%s (dry run)", patchRelPath, inReverse)
        argv = baseArgv + ["--dry-run"]
    else:
        log.info("apply '%s'%s", patchRelPath, inReverse)
        argv = baseArgv
    if reverse:
        argv.append("-R")
    log.debug("run %s in '%s' (stdin '%s')", argv, sourceDir, patchFile)
    stdout, stderr, retval = _run(argv, cwd=sourceDir, stdin=patchContent)
    sys.stdout.write(stdout)
    sys.stdout.flush()
    if retval:
        raise Error("error applying patch '%s'%s: argv=%r, cwd=%r, retval=%r"
                    % (patchFile, inReverse, argv, sourceDir, retval))



#---- public API

def unpatch(sourceDir, logDir, dryRun=0, patchExe=None):
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
    patchLogFile = os.path.join(logDir, "__patchlog__.py")
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
    #pprint.pprint(patchLog.actions)

    # Check that all actions can be undone.
    patchExe = _getPatchExe(patchExe)
    for action in patchLog.actions:
        if action[0] in ("apply", "preprocess & apply"):
            # Check that the patch can be applied in reverse.
            _assertCanApplyPatch(patchExe,
                                 os.path.join(logDir, action[2]),
                                 sourceDir,
                                 reverse=1)
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
                log.info("skip removal of '%s': already removed",
                         baseToDel)
            elif dryRun:
                log.info("remove '%s' (dry run)", baseToDel)
            else:
                log.info("remove '%s'", baseToDel)
                sh.rm(toDel)
        elif action[0] == "remove":
            # ("remove", <patches-basedir>, <dst-relpath>)
            atticLoc = os.path.join(logDir, "__attic__", action[2])
            sourceLoc = os.path.join(sourceDir, action[2])
            if os.path.exists(sourceLoc) and os.path.isfile(atticLoc):
                # Try to intelligently skip the re-add if it is not
                # necessary.
                fin = open(atticLoc, 'rb')
                try:
                    atticmd5 = md5(fin.read()).hexdigest()
                finally:
                    fin.close()
                if os.path.isfile(sourceLoc):
                    sourceFile = sourceLoc
                else:
                    sourceFile = os.path.join(dst, os.path.basename(sourceLoc))
                if os.path.exists(sourceFile):
                    fin = open(sourceFile, 'rb')
                    try:
                        sourcemd5 = md5(fin.read()).hexdigest()
                    finally:
                        fin.close()
                    if atticmd5 == sourcemd5:
                        log.info("skip restoration of '%s' from attic: "
                                 "already restored", action[2])
                        continue
            if dryRun:
                log.info("restore '%s' from attic (dry run)", action[2])
            else:
                log.info("restore '%s' from attic", action[2])
                sh.copy(atticLoc, sourceLoc)
        else:
            raise Error("unknown action, '%s', in patch log: %s"
                        % (action[0], action))


def patch(patchesDir, sourceDir, config=None, logDir=None, dryRun=0,
          patchExe=None):
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
    actions = []
    for patchSpec in patchesDir:
        if os.path.isfile(patchSpec):
            actions.append( ("apply", os.path.dirname(patchSpec),
                             os.path.basename(patchSpec)) )
        elif os.path.isdir(patchSpec):
            # Always skip SCC control dirs.
            if basename(patchSpec) in ("CVS", ".svn", ".hg"):
                continue
            os.path.walk(patchSpec, _shouldBeApplied,
                         (patchSpec, actions, config))
        else:
            raise Error("patches directory or file does not exist: '%s'"
                        % patchSpec)
    log.debug("patch set: %s" % pprint.pformat(actions))

    # Create a clean working directory.
    workDir = _createTempDir()
    log.debug("created patch working dir: '%s'" % workDir)
    try:
        # Create a patch image in the working dir (i.e. copy over patches and
        # files to add and preprocessed versions of those that need it.)
        defines = None # preprocessor defines are lazily calculated
        for action in actions:
            if action[0] in ("apply", "add"):
                src = os.path.join(action[1], action[2])
                dst = os.path.join(workDir, action[2])
                if action[0] == "apply" and os.path.isfile(dst):
                    raise Error("conflicting patch file '%s': you have a "
                                "patch of the same name in more than one "
                                "patches tree", action[2])
                if os.path.isfile(src):
                    preprocess_me, new_filename \
                        = _shouldPreprocess(basename(src))
                    if preprocess_me:
                        if defines is None:
                            defines = _getPreprocessorDefines(config)
                        d = join(dirname(dst), new_filename)
                        log.debug("preprocess '%s' to '%s'", src, d)
                        if not exists(dirname(d)):
                            os.makedirs(dirname(d))
                        preprocess.preprocess(src, d, defines=defines,
                                              substitute=1)
                    else:
                        log.debug("cp '%s' to '%s'", src, dst)
                        sh.copy(src, dst)
                elif os.path.isdir(src):
                    for dirpath, dirnames, filenames in os.walk(src):
                        subpath = (dirpath == src
                                   and os.curdir
                                   or dirpath[len(src)+1:])
                        for exclude_dir in (".svn", "CVS", ".hg"):
                            if exclude_dir in dirnames:
                                dirnames.remove(exclude_dir)
                        for filename in filenames:
                            s = join(dirpath, filename)
                            preprocess_me, new_filename \
                                = _shouldPreprocess(filename)
                            if preprocess_me:
                                d = normpath(join(dst, subpath, new_filename))
                                if defines is None:
                                    defines = _getPreprocessorDefines(config)
                                log.debug("preprocess '%s' to '%s'", s, d)
                                if not exists(dirname(d)):
                                    os.makedirs(dirname(d))
                                preprocess.preprocess(s, d, defines=defines,
                                                      substitute=1)
                            else:
                                d = normpath(join(dst, subpath, filename))
                                log.debug("cp '%s' to '%s'", s, d)
                                sh.copy(s, d)
                else:
                    raise Error("unknown file type for `%s'" % src)
            elif action[0] == "preprocess & apply":
                src = os.path.join(action[1], action[2])
                dst = os.path.join(workDir, action[2])
                if os.path.isfile(dst):
                    raise Error("conflicting patch file '%s': you have a "
                                "patch of the same name in more than one "
                                "patches tree", action[2])
                if defines is None:
                    defines = _getPreprocessorDefines(config)
                    #log.debug("defines: %s", pprint.pformat(defines))
                log.debug("preprocess '%s' to '%s'", src, dst)
                if not os.path.exists(os.path.dirname(dst)):
                    os.makedirs(os.path.dirname(dst))
                preprocess.preprocess(src, dst, defines=defines,
                                      substitute=1)
            elif action[0] == "remove":
                pass
            else:
                raise Error("unknown patch action '%s': %r"
                            % (action[0], action))
    
        # Ensure that each patch action can be carried out.
        patchExe = _getPatchExe(patchExe)
        for action in actions:
            if action[0] in ("apply", "preprocess & apply"):
                _assertCanApplyPatch(patchExe,
                                     os.path.join(workDir, action[2]),
                                     sourceDir,
                                     patchSrcFile=os.path.join(action[1], action[2]),
                                     patchArgs=action[3])
            elif action[0] == "add":
                # ("add", <patches-basedir>, <src-relpath>, <dst-relpath>, <force>)
                # e.g. ("add", "patches", "hpux_cpp_ext\\thingy.s", "python", False)
                #
                # Ensure that we won't clobber a target file that
                # differs.
                src = os.path.join(workDir, action[2])
                dst = os.path.join(sourceDir, action[3])
                if os.path.isdir(src):
                    for dirpath, dirnames, filenames in os.walk(src):
                        subpath = (dirpath == src
                                   and os.curdir
                                   or dirpath[len(src)+1:])
                        for filename in filenames:
                            s = join(dirpath, filename)
                            d = normpath(join(dst, subpath, filename))
                            # 'actual_s' might actually have a '.p' in there.
                            actual_s = join(action[1], action[2], subpath,
                                            filename)
                            if not action[4]:
                                _assertCanAddFile(s, d, actual_s)
                else:
                    if not action[4]:
                        _assertCanAddFile(src, dst,
                                          os.path.join(action[1], action[2]))
            elif action[0] == "remove":
                pass
            else:
                raise Error("unknown patch action '%s': %r"
                            % (action[0], action))

        if logDir:
            # Log actions.
            patchLogFile = os.path.join(workDir, "__patchlog__.py")
            patchLog = open(patchLogFile, "w")
            try:
                patchLog.write("""\
# Patch log (%s)
#
# WARNING: This file is automatically generated by patchtree.py. Any
#          Changes you make will be lost.

sourceDir = %r
actions = %s
""" % (time.asctime(), sourceDir, pprint.pformat(actions)))
            finally:
                patchLog.close()

            # Write files scheduled for removal to the attic for possible
            # retrieval during unpatch().
            atticDir = os.path.join(workDir, "__attic__")
            oldAtticDir = os.path.join(logDir, "__attic__")
            for action in actions:
                if action[0] == "remove":
                    # ("remove", <patches-basedir>, <dst-relpath>)
                    origLoc = os.path.join(sourceDir, action[2])
                    oldAtticLoc = os.path.join(oldAtticDir, action[2])
                    atticLoc = os.path.join(atticDir, action[2])
                    possibleLocs = [origLoc, oldAtticLoc]
                    for location in possibleLocs:
                        if os.path.exists(location):
                            log.debug("copy '%s' to attic", origLoc)
                            sh.copy(location, atticLoc)

        # A little helper for doing the 'add' action with appropriate
        # logging.
        def _add_it(s, d, actual_s, force=False, dryRun=False):
            if not exists(d):
                if dryRun:
                    log.info("add '%s' to '%s' (dry run)",
                             actual_s, d)
                else:
                    log.info("add '%s' to '%s'", actual_s, d)
                    sh.copy(s, d)
            elif not _diffPaths(s, d):
                log.info("skip add of '%s' to '%s': "
                         "no changes", actual_s, d)
            else:
                if dryRun:
                    log.info("replace '%s' to '%s' (dry run)",
                             actual_s, d)
                else:
                    log.info("replace '%s' to '%s'",
                             actual_s, d)
                    sh.copy(s, d)

        # Carry out each patch action.
        for action in actions:
            if action[0] in ("apply", "preprocess & apply"):
                _applyPatch(patchExe, workDir, action[2], sourceDir,
                            dryRun=dryRun, patchArgs=action[3])
            elif action[0] == "add":
                # ("add", <patches-basedir>, <src-relpath>, <dst-relpath>, <force>)
                # e.g. ("add", "patches", "hpux_cpp_ext\\thingy.s", "python", False)
                #
                #XXX Could improve logging here to only log one message
                #    in certain circumstances: no changes, all files
                #    were added.
                src = os.path.join(workDir, action[2])
                dst = os.path.join(sourceDir, action[3])
                if isdir(src):
                    for dirpath, dirnames, filenames in os.walk(src):
                        subpath = (dirpath == src
                                   and os.curdir
                                   or dirpath[len(src)+1:])
                        for filename in filenames:
                            s = join(dirpath, filename)
                            d = normpath(join(dst, subpath, filename))
                            # 'actual_s' might actually have a '.p' in there.
                            actual_s = join(action[1], action[2], subpath,
                                            filename)
                            _add_it(s, d, actual_s, force=action[4],
                                    dryRun=dryRun)
                else:
                    d = isfile(dst) and dst or join(dst, basename(src))
                    actual_s = join(action[1], action[2])
                    _add_it(src, d, actual_s, force=action[4], dryRun=dryRun)
            elif action[0] == "remove":
                # ("remove", <patches-basedir>, <dst-relpath>)
                dst = os.path.join(sourceDir, action[2])
                if not os.path.exists(dst):
                    log.info("skip removal of '%s': already removed",
                             action[2])
                elif dryRun:
                    log.info("remove '%s' (dry run)", action[2])
                else:
                    log.info("remove '%s'", action[2])
                    sh.rm(dst)
            else:
                raise Error("unknown patch action '%s': %r"
                            % (action[0], action))

        # If a log dir was specified then copy working dir there.
        if logDir:
            if dryRun:
                log.info("creating patch log in '%s' (dry run)", logDir)
            else:
                if os.path.exists(logDir):
                    sh.rm(logDir)
                log.info("creating patch log in '%s'", logDir)
                sh.copy(workDir, logDir)
    finally:    
        log.debug("removing temporary working dir '%s'", workDir)
        try:
            sh.rm(workDir)
        except EnvironmentError, ex:
            log.warn("could not remove temp working dir '%s': %s",
                     workDir, ex)



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
        unpatch(patches, src, config=config, logDir=logDir, dryRun=dryRun)
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


