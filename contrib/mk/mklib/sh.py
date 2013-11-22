# Copyright (c) 2005-2007 ActiveState Software Ltd.

"""Utilities for running various common shell commands."""

__all__ = ["run", "run_in_dir",
           "rm", "mkdir", "cp",
           "touch"]

import os
import sys
from glob import glob
from os.path import normcase, normpath, isabs, abspath, isfile, \
                    isdir, join
import logging
import stat

log = logging.getLogger("sh")



#---- running commands on the shell
#TODO: would like to clean up the logging story for these

# Recipe: run (0.7.1)
_RUN_DEFAULT_LOGSTREAM = ("RUN", "DEFAULT", "LOGSTREAM")
def __run_log(logstream, msg, *args, **kwargs):
    if logstream is None:
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

def run(cmd, logstream=_RUN_DEFAULT_LOGSTREAM, dry_run=False):
    """Run the given command.

        "cmd" is the command to run
        "logstream" is an optional logging stream on which to log the 
            command. If None, no logging is done. If unspecifed, this 
            looks for a Logger instance named 'log' and logs the command 
            on log.debug().

    Raises OSError is the command returns a non-zero exit status.
    """
    __run_log(logstream, "running '%s'", cmd)
    if dry_run:
        return
    fixed_cmd = cmd
    if sys.platform == "win32" and cmd.count('"') > 2:
        fixed_cmd = '"' + cmd + '"'
    retval = os.system(fixed_cmd)
    if hasattr(os, "WEXITSTATUS"):
        status = os.WEXITSTATUS(retval)
    else:
        status = retval
    if status:
        raise OSError(status, "error running '%s'" % cmd)

def run_in_dir(cmd, cwd, logstream=_RUN_DEFAULT_LOGSTREAM, dry_run=False):
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
        if not dry_run:
            os.chdir(cwd)
        __run_log(logstream, "running '%s' in '%s'", cmd, cwd)
        if dry_run:
            return
        run(cmd, logstream=None)
    finally:
        if not dry_run:
            os.chdir(old_dir)


#---- common shell commands
#TODO: rehash this as a `class SH' with a default instance, proper
#      log handling, `self.sh' on Tasks

def mkdir(newdir, mode=0777, log=None, dry_run=False):
    """works the way a good mkdir should :)
        - already exists, silently complete
        - regular file in the way, raise an exception
        - parent directory(ies) does not exist, make them as well
    """
    if isdir(newdir):
        pass
    elif isfile(newdir):
        raise OSError("a file with the same name as the desired " \
                      "dir, '%s', already exists." % newdir)
    else:
        if log: log.info("mkdir `%s'", newdir)
        if dry_run:
            return
        head, tail = os.path.split(newdir)
        if head and not isdir(head):
            mkdir(head, mode)
        if tail:
            #if log: log.debug("mkdir `%s'", newdir)
            os.mkdir(newdir, mode)


#TODO: Just using the shell's 'rm', 'del', 'rd' might work better.
#      Need a test suite and perf comparisons to decide which.
#      Here is a start at that:
#        assert ' ' not in path,\
#            "_rm: can't handle paths in spaces: '%s'" % path
#        if sys.platform == "win32":
#            path = path.replace("/", "\\")
#            assert "*" not in path and "?" not in path,\
#                "_rm on win32: can't yet handle wildcards: '%s'" % path
#            if not exists(path):
#                pass
#            elif isdir(path):
#                _run("rd /s/q %s" % path, logstream=logstream)
#            else:
#                if not os.access(path, os.W_OK):
#                    _run("attrib -R %s" % path, logstream=logstream)
#                _run("del /q %s" % path, logstream=logstream)
#        else:
#            _run("rm -rf %s" % path, logstream=logstream)
def rm(path, log=None, dry_run=False):
    """Remove the given path (be it a file or directory).
    
    Raises OSError if the given path does not exist. Can also raise an
    EnvironmentError if the path cannot be removed for some reason.
    """
    if log: log.info("rm `%s'", path)
    if dry_run:
        return

    if path.find('*') != -1 or path.find('?') != -1 or path.find('[') != -1:
        paths = glob(path)
        if not paths:
            raise OSError(2, "No such file or directory: '%s'" % path)
    else:
        paths = [path]    

    for path in paths:
        if os.path.isfile(path) or os.path.islink(path):
            try:
                os.remove(path)
            except OSError, ex:
                if ex.errno == 13: # OSError: [Errno 13] Permission denied
                    os.chmod(path, 0777)
                    os.remove(path)
                else:
                    raise
        elif os.path.isdir(path):
            for f in os.listdir(path):
                rm(join(path, f))
            os.rmdir(path)
        else:
            raise OSError(2, "No such file or directory", path)


def mv(src, dst, log=None, dry_run=False):
    """My little lame cross-platform 'mv'"""
    if log: log.info("mv `%s' `%s'", src, dst)
    if dry_run:
        return
    if sys.platform == "win32":
        run('move "%s" "%s"' % (src, dst))
    else:
        run('mv "%s" "%s"' % (src, dst))


def old_cp(src, dst, log=None, dry_run=False):
    """Copy src to dst.
    
    DEPRECATED: use the new cp().
    """
    if log: log.info("cp `%s' `%s'", src, dst)
    if dry_run:
        return
    
    #if src.find('*') != -1 or src.find('?') != -1 or src.find('[') != -1:
    #    raise ValueError("globbing not yet supported: %r" % src)

    norm_src = normcase(normpath(abspath(src)))
    norm_dst = normcase(normpath(abspath(dst)))
    if norm_src == norm_dst:
        raise OSError("cannot copy file onto itself: src=%r, dst=%r"
                      % (src, dst))
        
    if sys.platform == "win32":
        src = src.replace("/", "\\")
        dst = dst.replace("/", "\\")
        #TODO: cp("somedir/*", "destdir") does not do the expected here
        #      b/c 'isdir(src) is False'.
        if isdir(src):
            run('xcopy /e/i/y/q "%s" "%s"' % (src, dst))
        else:
            run('copy /y "%s" "%s" >nul' % (src, dst))
        # Problem: 'copy' and 'xcopy' preserve the mtime by default
        # (with no option to not do so). As a result, any make target
        # with two copies will always end up being out of date. By
        # default 'cp' on other platforms does NOT preserve the mtime.
        # We want that behaviour here -- but that means using 'xcopy'
        # is a pain.
    else:
        if isdir(src):
            run('cp -R "%s" "%s"' % (src, dst))
        else:
            run('cp "%s" "%s"' % (src, dst))


def cp(src, dst=None, dstdir=None, force=False, recursive=False,
       preserve=False, noglob=False, log=None, verbose=False):
    """copy files and directories

    Usage:
        cp(SOURCE, DEST, ...)                   # one file
        cp(SOURCES, DIRECTORY, ...)             # many files to a dir
        cp(SOURCE(S), dstdir=DIRECTORY, ...)    # one or many files to a dir

    Arguments:
        "src" is a file, file pattern (glob syntax) or sequence (or generator)
            of file or file patterns to copy.
        "dst" is a target destination.
        "dstdir" is a target directory. One of "dst" or "dstdir" must be
            specified. "dstdir" can be useful to avoid mistakenly copying
            a source file to a dest _file_ if a target directory was
            intended, just because the target did not happen to exist.

    Options:
        "force" (boolean, default false) if an existing destination file
            cannot be written to, remove it and try again
        "recursive" (boolean, default false) copy directories recursively.
            If false an error is raised on an attempt to copy a directory.
        "preserve" (boolean, default false), if true, will attempt to
            preserve file attributes. Currently the mode and timestamps
            are preserved.
        "noglob" (boolean, default false) do not treat "src" as
            file patterns
        "log" is a log method (e.g. logging.Logger.info) on which to
            write messages or None (the default) for no output.
        "verbose" (boolean, default false) more verbose logging output.

    Notes:
    - Difference from GNU-cp
         $ cp existing-dir-a existing-file existing-dir-b
         cp: omitting directory `existing-dir-a'
      This command will still copy 'existing-file' to 'existing-dir-b'
      and return non-zero. This cp() implementation will raise an
      exception for this saying that "recursive" must be used for
      this.
    - Limitation w.r.t. samefile on Windows: In some cases this cp() can
      be tricked into copying a file onto itself if their are distinct
      paths on separate drives (or on separate UNC shares) to the same
      file.
    - Preserve: This option may grow to support everything that GNU cp's
      -p and --preserve options provide.

    Raises TypeError for invalid arguments and EnvironmentError for all
    other errors. There is no return value.
    """
    if dst is not None and dstdir is None:
        target_path = dst
    elif dst is None and dstdir is not None:
        target_path = dstdir
    else:
        raise TypeError("must specify exactly one of 'dst' or 'dstdir'")
    try:
        target_stat = os.stat(target_path)
    except OSError:
        target_stat = None
    target = (target_path, target_stat)

    first_source = None
    for source in _gen_sources(src, target_path, noglob, log, verbose):
        if first_source is None: # defer handling first file
            first_source = source
            continue
        elif first_source: # handle deferred first file
            # There is more than one source file: target must be a dir.
            if not target_stat or not stat.S_ISDIR(target_stat.st_mode):
                raise OSError(0, "copying multiple files, but target is not a directory",
                              target_path)
            _cp(first_source, target, force, recursive, preserve, log, verbose)
            first_source = False # signal that first file has been handled
            # Fall through...
        _cp(source, target, force, recursive, preserve, log, verbose)
    if first_source:
        # Copying one file. If 'dstdir' was used to specify the target
        # then make sure that there is such a directory.
        if dstdir is not None \
           and (not target_stat or not stat.S_ISDIR(target_stat.st_mode)):
            raise OSError(0, "specified target 'dstdir' is not a directory",
                          target)
        _cp(first_source, target, force, recursive, preserve, log, verbose)




def touch(path, log=None, dry_run=False):
    if log: log.info("touch `%s'", path)
    if dry_run:
        return
    if os.path.exists(path):
        os.utime(path, None)
    else:
        f = open(path, 'w')
        f.close()



#---- internal support stuff

def _getumask():
    oldumask = os.umask(077)
    os.umask(oldumask)
    return oldumask

def _samefile(a, b):
    """Return true iff paths 'a' and 'b' refer to the same file."""
    if sys.platform == "win32":
        #XXX Will not properly handle LONGNAME == SHORTNAME. Nor will it
        #    handle multiple paths to the same file with different drives
        #    or UNC shares.
        norma  = normcase(normpath(a))
        normb = normcase(normpath(b))
        if isabs(norma) or isabs(normb):
            norma = abspath(norma)
            normb = abspath(normb)
        return norma == normb
    else:
        return os.path.samefile(a, b)

def _gen_sources(patterns, target, noglob=False, log=None,
                 verbose=False):
    """Generate sources to process.

    Note: "target", "log", and "verbose" are just for logging.

    Generates 2-tuples: (<path>, <stat result>).
    Raises OSError if a specified path does not exist.
    """
    if isinstance(patterns, (str, unicode)):
        patterns = [patterns]
    elif not patterns:
        raise TypeError("no sources specified: %r" % patterns)
    for pattern in patterns:
        if log and not verbose: log("cp %s %s", pattern, target)
        if noglob:
            yield (pattern, os.stat(pattern))
        else:
            matches = False
            for path in glob(pattern):
                yield (path, os.stat(path))
                matches = True
            if not matches:
                # Raise appropriate OSError, e.g.:
                #   No such file or directory: 'foo'
                #   Not a directory: 'foo/'
                os.stat(pattern)

def _basename(path):
    """An os.path.basename() that deals with trailing slashes as we want.
    
    c.f. test 'sh/cp/forcedir'
    """
    if path.endswith(os.sep):
        path = path[:-len(os.sep)]
    return os.path.basename(path)

def _cp(source, target, force, recursive, preserve, log, verbose,
        __recursion=0):
    # '__recursion' is an internal var used to track if this is a recursive
    # call to this function or not
    DEBUG = False
    if DEBUG:
        print "_cp(source=%r, target=%r, force=%r, recursive=%r, "\
              "preserve=%r, log, verbose=%r)"\
              % (source[0], target[0], force, recursive, preserve, verbose)
    spath, sstat = source
    smode = sstat.st_mode
    tpath, tstat = target

    if stat.S_ISREG(smode):
        if not __recursion and tstat and stat.S_ISDIR(tstat.st_mode):
            tpath = os.path.join(tpath, _basename(spath))
            try:
                tstat = os.stat(tpath)
            except OSError:
                tstat = None
            target = (tpath, tstat)
        if tstat:
            if _samefile(spath, tpath):
                raise OSError(0, "`%s' and `%s' are the same file" % (spath, tpath), tpath)
            elif stat.S_ISDIR(tstat.st_mode):
                raise OSError(0, "cannot overwrite directory `%s' with non-directory" % tpath, spath)
        if not os.access(spath, os.R_OK):
            raise OSError(0, "cannot open source for reading: permission denied", spath)
        if tstat and not os.access(tpath, os.W_OK):
            # Note: There is where GNU 'cp -i ...' would catch
            # "Permission denied" and offer:
            #   cp: overwrite `<target>', overriding mode 0444?
            if force:
                os.chmod(tpath, 0777)
                os.remove(tpath)
                tstat = None
                target = (tpath, tstat)
            else:
                raise OSError(0, "cannot open target for writing: permission denied", tpath)

        if log and verbose:
            log("`%s' -> `%s'", spath, tpath)
        fsrc = open(spath, 'rb')
        try:
            ftarget = open(tpath, 'wb')
            try:
                #XXX Should this be done in chunks?
                ftarget.write(fsrc.read())
            finally:
                ftarget.close()
        finally:
            fsrc.close()
        
        # Rules for setting permissions:
        # - if preserve is true: then preserve
        # - if target already existed: don't change permissions
        # - otherwise: set perms to perm(source) & ~umask
        if preserve:
            os.chmod(tpath, stat.S_IMODE(smode))
            os.utime(tpath, (sstat.st_atime, sstat.st_mtime))
        elif not tstat: # i.e. the target did not exist before the copy
            perm = stat.S_IMODE(smode) & ~_getumask()
            os.chmod(tpath, perm)
    
    elif stat.S_ISDIR(smode):
        if not recursive:
            raise OSError(0, "must specify 'recursive' to copy a directory", spath)
        if not __recursion and tstat and stat.S_ISDIR(tstat.st_mode):
            tpath = os.path.join(tpath, _basename(spath))
            try:
                tstat = os.stat(tpath)
            except OSError:
                tstat = None
            target = (tpath, tstat)

        # Get list of files to copy over before creation of target dir
        # to avoid infinite loop if copying dir into itself.
        subfiles = os.listdir(spath)

        if not tstat:
            if log and verbose:
                log("`%s' -> `%s'", spath, tpath)
            os.mkdir(tpath)

        # Set attributes properly.
        if preserve:
            os.chmod(tpath, stat.S_IMODE(smode))
            os.utime(tpath, (sstat.st_atime, sstat.st_mtime))
        elif not tstat: # i.e. the target did not exist before the copy
            perm = stat.S_IMODE(smode) & ~_getumask()
            os.chmod(tpath, perm)

        for subfile in subfiles:
            subsource_path = os.path.join(spath, subfile)
            subsource = (subsource_path, os.stat(subsource_path))
            subtarget_path = os.path.join(tpath, subfile)
            try:
                subtarget_stat = os.stat(subtarget_path)
            except OSError:
                subtarget_stat = None
            subtarget = (subtarget_path, subtarget_stat)
            _cp(subsource, subtarget, force, recursive, preserve, log,
                verbose, __recursion=1)

    elif stat.S_ISLNK(smode):
        raise NotImplementedError("don't yet know how to copy symbolic links: `%s'" % spath)
    elif stat.S_ISCHR(smode):
        raise NotImplementedError("don't yet know how to copy character special device files: `%s'" % spath)
    elif stat.S_ISBLK(smode):
        raise NotImplementedError("don't yet know how to copy block special device files: `%s'" % spath)
    elif stat.S_ISFIFO(smode):
        raise NotImplementedError("don't yet know how to copy a FIFO (named pipe): `%s'" % spath)
    elif stat.S_ISSOCK(smode):
        raise NotImplementedError("don't yet know how to copy a socket: `%s'" % spath)
    else:
        raise NotImplementedError("unknown file type: `%s' (mode bits: %s)"
                                  % (spath, oct(stat.S_IFMT(smode))))
