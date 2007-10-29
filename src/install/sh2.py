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
    Shell utilities.

    Includes:
        cp()        copy files and directories
        mkdir()     create directories
        rm()        remove files and directories

    Minimum requirements: Python 2.2.1 (when True/False and generators
    were added). To test: `python test_sh2.py`
"""
#TODO:
# - chmod that accepts "u+w" and recursive=True
# - cp():
#   - symlink support
#   - supporting other file types: special files, NTFS junctions,
#     sockets, FIFOs
#   - consider other GNU cp options: backups, symlink-related options
#     (-H, -l|--link, -L|--dereference, --no-dereference, -d, ...),
#     interactive (-i), update (-u), file system (-x|--one-file-system), 
#   - Could add a 'verify' option to cp() -- kind of like `copy /V' on
#     Windows.
#   - Absolutely proper handling of trailing slashes for sources and
#     dests is confused. Would be nice to clarify that at some point.
# - pick other shell utils to add: chmod that accepts u+x, for example,
#   and that supports a recursive option; mv, rm (with a force stronger
#   than rm's '-f' option -- which will not move into dirs without
#   execute permission)
# - unicode path support (not sure if there are problems there)
# - ListCmd-based command-line iface a la GNU sh-utils -- "sh.py cp ..."
# - look for sh-utils re-inventions of the wheel in, e.g., distutils,
#   SCons, etc. and see if mine have enough features to be compelling
#   replacements for them
# - Is adding a "mkdir=True" option a good idea? `cp' does not have
#   such an option.

import os
import sys
import glob
import stat



#---- globals

__authors__ = ["Trent Mick <TrentM@ActiveState.com>"]
__version__ = (0, 1, 0)
__revision__ = "$Id$"



#---- internal support routines

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
        norma  = os.path.normcase(os.path.normpath(a))
        normb = os.path.normcase(os.path.normpath(b))
        if os.path.isabs(norma) or os.path.isabs(normb):
            norma = os.path.abspath(norma)
            normb = os.path.abspath(normb)
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
            for path in glob.glob(pattern):
                yield (path, os.stat(path))
                matches = True
            if not matches:
                # Raise appropriate OSError, e.g.:
                #   No such file or directory: 'foo'
                #   Not a directory: 'foo/'
                os.stat(pattern)

def _basename(path):
    """An os.path.basename() that deals with trailing slashes as we want.
    
    c.f. test_sh2.py::cp.test_forcedir()
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



#---- public interface


##def mkdir(newdir, mode=0777):
##    """works the way a good mkdir should :)
##        - already exists, silently complete
##        - regular file in the way, raise an exception
##        - parent directory(ies) does not exist, make them as well
##    """
##    if isdir(newdir):
##        pass
##    elif os.path.isfile(newdir):
##        raise OSError("a file with the same name as the desired " \
##                      "dir, '%s', already exists." % newdir)
##    else:
##        head, tail = os.path.split(newdir)
##        if head and not isdir(head):
##            mkdir(head, mode)
##        if tail:
##            log.debug('mkdir "%s"' % newdir)
##            os.mkdir(newdir, mode)

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
            a source file to a dest _file_ if a target directory was intended,
            just because the target did not happen to exist.

    Options:
        "force" (boolean, default false) if an existing destination file
            cannot be written to, remove it and try again
        "recursive" (boolean, default false) copy directories recursively.
            If false an error is raised on an attempt to copy a directory.
        "preserve" (boolean, default false), if true, will attempt to
            preserve file attributes. Currently the mode and timestamps
            are preserved.
        "noglob" (boolean, default false) do not treat "src" as file patterns
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

    Raises TypeError for invalid arguments and EnvironmentError for all other
    errors. There is no return value.
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


# Interesting from GNU rm:
#   $ rm -rf dirb
#   rm: cannot chdir from `.' to `dirb': Permission denied
# It is chdir'ing into dirs to recursively remove.

##def rm(path):
##    """Remove the given path (be it a file or directory).
##    
##    Raises OSError if the given path does not exist. Can also raise an
##    EnvironmentError if the path cannot be removed for some reason.
##    """
##    if path.find('*') != -1 or path.find('?') != -1 or path.find('[') != -1:
##        paths = glob.glob(path)
##        if not paths:
##            raise OSError(2, "No such file or directory: '%s'" % path)
##    else:
##        paths = [path]    
##
##    for path in paths:
##        if os.path.isfile(path) or os.path.islink(path):
##            try:
##                os.remove(path)
##            except OSError, ex:
##                if ex.errno == 13: # OSError: [Errno 13] Permission denied
##                    os.chmod(path, 0777)
##                    os.remove(path)
##                else:
##                    raise
##        elif os.path.isdir(path):
##            for f in os.listdir(path):
##                rm(os.path.join(path, f))
##            os.rmdir(path)
##        else:
##            raise OSError(2, "No such file or directory", path)



#---- mainline

if __name__ == "__main__":
    import logging
    log = logging.getLogger("cp")
    logging.basicConfig()
    log.setLevel(logging.INFO)

    import getopt
    optlist, args = getopt.getopt(sys.argv[1:], 'vfr',
        ['verbose', 'force', 'recursive', 'noglob'])
    verbose = False
    recursive = False
    force = False
    noglob = False
    for opt, optarg in optlist:
        if opt in ('-v', '--verbose'):
            verbose = True
        if opt in ('-f', '--force'):
            force = True
        elif opt in ('-r', '--recursive'):
            recursive = True
        elif opt in ('--noglob',):
            noglob = True
    if len(args) == 0:
        src = None
        dst = None
    elif len(args) == 1:
        src = args[0]
        dst = None
    elif len(args) == 2:
        src, dst = args
    else:
        src = args[:-1]
        dst = args[-1]

    cp(src, dst, force=force, recursive=recursive, noglob=noglob,
       log=log.info, verbose=verbose)



