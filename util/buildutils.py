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

"""Some utils for Komodo's build system."""

import os
from os.path import (join, dirname, basename, isdir, isfile, abspath,
                     splitext, exists, expanduser)
import sys
from glob import glob
import re
import logging
import socket
from pprint import pprint
import getpass
import subprocess



#---- globals

log = logging.getLogger("buildutils")



#---- process running utilities

# Recipe: run (0.7)
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
        #TODO: add std OSError attributes or pick more approp. exception
        raise OSError("error running '%s': %r" % (cmd, status))

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


#---- text manipulation utilities

# Recipe: dedent (0.1.2) in C:\trentm\tm\recipes\cookbook
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

def dedent(text, tabsize=8, skip_first_line=False):
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


# Recipe: banner (1.0.1)
def banner(text, ch='=', length=78):
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



#---- path manipulation utilities

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


def relpath(path, relto=None):
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
    #print "relpath: pathPaths=%s" % pathParts
    #print "relpath: relToPaths=%s" % relToParts
    for pathPart, relToPart in zip(pathParts, relToParts):
        if _equal(pathPart, relToPart):
            # drop the leading common dirs
            del pathParts[0]
            del relToParts[0]
    #print "relpath: pathParts=%s" % pathParts
    #print "relpath: relToParts=%s" % relToParts
    # Relative path: walk up from "relto" dir and walk down "path".
    relParts = [os.curdir] + [os.pardir]*len(relToParts) + pathParts
    #print "relpath: relParts=%s" % relParts
    relPath = os.path.normpath( os.path.join(*relParts) )
    return relPath



#---- remote file utilities

# Recipe: remote (0.7.4)
_remote_path_re = re.compile("(\w+@)?\w+:/(?!/)")
def is_remote_path(rpath):
    return _remote_path_re.search(rpath) is not None

def remote_exists(rpath, log=None):
    login, path = rpath.split(':', 1)
    if sys.platform == "win32":
        if '@' not in login:
            login = "%s@%s" % (getpass.getuser(), login)
        argv = ["plink", "-batch", login, "ls", path]
    else:
        argv = ["ssh", "-o", "BatchMode=yes", login, "ls", path]
    if log:
        log(' '.join(argv))
    status = capture_status(argv)
    return status == 0

def remote_mkdir(rpath, parents=False, log=None):
    login, path = rpath.split(':', 1)
    opts = ""
    if parents:
        opts = " -p"
    if sys.platform == "win32":
        if '@' not in login:
            login = "%s@%s" % (getpass.getuser(), login)
        cmd = "plink -batch %s mkdir%s %s" % (login, opts, path)
    else:
        cmd = "ssh -o BatchMode=yes %s mkdir%s %s" % (login, opts, path)
    if log:
        log(cmd)
    status = run(cmd)
    if status:
        raise OSError("error running '%s': status=%r" % (cmd, status))

def remote_makedirs(rpath, log=None):
    from posixpath import join
    parts = rpath.split('/')
    parts[0] += '/'
    for i in range(2, len(parts)+1):
        rpath_part = join(*parts[:i])
        if not remote_exists(rpath_part, log):
            remote_mkdir(rpath_part, log)

def remote_cp(src, dst, log=None, hard_link_if_can=False):
    if is_remote_path(src) and is_remote_path(dst):
        # This is harder, because remote to remote copying is not
        # supported by scp.
        assert ' ' not in src and ' ' not in dst
        src_login, src_path = src.split(':', 1)
        dst_login, dst_path = dst.split(':', 1)
        if src_login == dst_login:
            if hard_link_if_can:
                rcmd = 'ln -f %s %s' % (src_path, dst_path)
            else:
                rcmd = 'cp -f %s %s' % (src_path, dst_path)
        else:
            rcmd = 'scp -q -B %s %s' % (src_path, dst)
        remote_run(src_login, rcmd, log=log)
    else:
        if sys.platform == "win32":
            cmd = 'pscp -q "%s" "%s"' % (src, dst)
        else:
            cmd = 'scp -q -B "%s" "%s"' % (src, dst)
        if log:
            log(cmd)
        status = run(cmd)
        if status:
            raise OSError("error running '%s': status=%r" % (cmd, status))

def remote_mv(src, dst, log=None):
    if is_remote_path(src) and is_remote_path(dst):
        if src_login != dst_login:
            raise ValueError("src and dst must live on the same remote server")
        # This is harder, because remote to remote copying is not
        # supported by scp.
        assert ' ' not in src and ' ' not in dst
        src_login, src_path = src.split(':', 1)
        dst_login, dst_path = dst.split(':', 1)
        rcmd = 'mv -f %s %s' % (src_path, dst_path)
        remote_run(src_login, rcmd, log=log)
    else:
        if sys.platform == "win32":
            cmd = 'move /Y "%s" "%s"' % (src, dst)
        else:
            cmd = 'mv -f "%s" "%s"' % (src, dst)
        if log:
            log(cmd)
        status = run(cmd)
        if status:
            raise OSError("error running '%s': status=%r" % (cmd, status))

def remote_relpath(rpath, relto):
    """Relativize the given remote path to another.
    
    >>> remote_relpath('server:/home/trentm', 'server:/home')
    'server:trentm'
    >>> remote_relpath('server:/home/trentm/tmp', 'server:/home')
    'server:trentm/tmp'
    >>> remote_relpath('server:/home', 'server:/home/trentm')
    'server:..'
    
    Requirements:
    - both 'rpath' and 'relto' are on the same server
    - both are absolute paths (there is no cwd with which to make
      them absolute)
    - presuming the remote server uses Unix paths ('/' dir sep,
      case-sensitive)
    """
    from posixpath import isabs, join, normpath

    login, path = rpath.split(':', 1)
    relto_login, relto_path = relto.split(':', 1)
    assert login == relto_login
    assert isabs(path) and isabs(relto_path)

    path_parts = path[1:].split('/') # drop the leading root dir
    relto_path_parts = relto_path[1:].split('/') # drop the leading root dir

    for path_part, relto_path_part in zip(path_parts, relto_path_parts):
        if path_part == relto_path_part:
            # drop the leading common dirs
            del path_parts[0]
            del relto_path_parts[0]
    # Relative path: walk up from "relto" dir and walk down "path".
    rel_parts = ['.'] + ['..']*len(relto_path_parts) + path_parts
    rel_path = normpath(join(*rel_parts))
    return login + ':' + rel_path

def remote_symlink(src, dst, log=None):
    assert ' ' not in src and ' ' not in dst
    dst_login, dst_path = dst.split(':', 1)
    src_path = src
    if ':' in src:
        src_login, src_path = src.split(':', 1)
        assert src_login == dst_login
    cmd = "ln -s %s %s" % (src_path, dst_path)
    remote_run(dst_login, cmd, log=log)

def remote_rm(rpath, log=None):
    assert ' ' not in rpath
    login, path = rpath.split(':', 1)
    cmd = 'rm -f %s' % path
    remote_run(login, cmd, log=log)

def remote_rm_recursive(rpath, log=None):
    assert ' ' not in rpath
    login, path = rpath.split(':', 1)
    cmd = 'rm -rf %s' % path
    remote_run(login, cmd, log=log)

def remote_glob(rpattern, log=None):
    login, pattern = rpattern.split(':', 1)
    norm_login = login
    if sys.platform == "win32":
        if '@' not in login:
            norm_login = "%s@%s" % (getpass.getuser(), login)
        argv = ["plink", "-batch", norm_login, "ls", "-d", pattern]
    else:
        argv = ["ssh", '-A', "-o", "BatchMode=yes", norm_login,
                "ls", "-d", pattern]
    if log:
        log(' '.join(argv))
    rpaths = []
    try:
        output = capture_stdout(argv)
    except OSError, ex:
        pass
    else:
        # Skip stderr lines like this (see ActiveState bug 79857):
        #   id: cannot find name for group ID \d+
        skip_res = [
            re.compile(r"^id: cannot find name for group ID \d+$")
        ]
        for line in output.splitlines(0):
            if not line.strip():
                continue
            skip_it = False
            for skip_re in skip_res:
                if skip_re.search(line):
                    skip_it = True
                    break
            if skip_it:
                continue
            rpaths.append("%s:%s" % (login, line.strip()))
    return rpaths

def remote_find(rdir, options={}, log=None):
    argv = ["find", rdir]
    for opt, val in options:
        argv.append(opt)
        if val is not None:
            argv.append(val)

    try:
        # Don't use `capture_stdout` -- results in hang with plink on
        # Windows (see Komodo bug 79857). Eventual best fix is probably
        # to use `subprocess.Popen().communicate()`.
        output = capture_output(argv)
    except OSError, ex:
        pass
    else:
        remote_run(src_login, " ".join(cmd), log=log)

def remote_listdir(rdir, log=None):
    """Return a tuple of (dirnames, filenames) for the remote dir.
    
    This presumes a GNU-like `ls` on the remote machine.
    """
    login, dir = rdir.split(':', 1)
    norm_login = login
    if sys.platform == "win32":
        if '@' not in login:
            norm_login = "%s@%s" % (getpass.getuser(), login)
        argv = ["plink", "-batch", norm_login, "ls", "-aF", dir]
    else:
        argv = ["ssh", "-o", "BatchMode=yes", norm_login, "ls", "-aF", dir]
    if log:
        log(' '.join(argv))
    p = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    dnames = []
    fnames = []
    for name in p.stdout.read().splitlines(0):
        sigil = ""
        if name[-1] in "*/=>@|":
            name, sigil = name[:-1], name[-1]
        if name in ('.', '..'):
            continue
        if sigil == '/':
            dnames.append(name)
        else:
            fnames.append(name)
    return dnames, fnames

def remote_walk(rdir, log=None):
    """Like os.walk(dir), but for a remote dir.
    
    This presumes a GNU-like `ls` on the remote machine.
    """
    from posixpath import join

    login, dir = rdir.split(':', 1)
    dirs = [dir]
    while dirs:
        dpath = dirs.pop(0)
        dnames, fnames = remote_listdir(login + ":" + dpath)
        yield login+":"+dpath, dnames, fnames
        dirs += [join(dpath, n) for n in dnames]

def remote_md5sum(rpath, log=None):
    """Return the md5sum for the given remote path.
    
    This relies on 'md5sum' being available and runnable on the remote
    machine. Raises OSError if the md5sum could not be determined.
    """
    login, path = rpath.split(':', 1)
    rcmd = 'md5sum "%s"' % path
    if sys.platform == "win32":
        if '@' not in login:
            login = "%s@%s" % (getpass.getuser(), login)
        argv = ["plink", "-batch", login, rcmd]
    else:
        argv = ["ssh", "-o", "BatchMode=yes", login, rcmd]
    if log:
        log(' '.join(argv))

    stdout = capture_stdout(argv)
    try:
        md5sum, rv_path = stdout.splitlines(0)[0].split()
        assert path == rv_path
        assert len(md5sum) == 32
    except (AssertionError, ValueError, IndexError), ex:
        raise OSError("error getting remote md5sum: unexpected output: %r"
                      % stdout)
    return md5sum

def remote_size(rpath, log=None):
    """Return the size of the given remote path.
    
    This relies on 'du -b' working on the remote machine. Raises OSError if
    the size could not be determined.
    """
    login, path = rpath.split(':', 1)
    rcmd = 'du -b "%s"' % path
    if sys.platform == "win32":
        if '@' not in login:
            login = "%s@%s" % (getpass.getuser(), login)
        argv = ["plink", "-batch", login, rcmd]
    else:
        argv = ["ssh", "-o", "BatchMode=yes", login, rcmd]
    if log:
        log(' '.join(argv))

    stdout = capture_stdout(argv)
    
    try:
        bytes, rv_path = stdout.splitlines(0)[0].split()
        assert path == rv_path
        bytes = int(bytes)
    except (AssertionError, ValueError, IndexError), ex:
        raise OSError("error getting remote md5sum: unexpected output: %r"
                      % stdout)
    return bytes

def remote_run(login, cmd, log=None):
    if sys.platform == "win32":
        if '@' not in login:
            login = "%s@%s" % (getpass.getuser(), login)
        cmd = 'plink -A -batch %s "%s"' % (login, cmd)
    else:
        cmd = 'ssh -A -o BatchMode=yes %s "%s"' % (login, cmd)
    status = run(cmd, logstream=log)
    if status:
        raise OSError("error running '%s': status=%r" % (cmd, status))

def capture_stdout(argv, ignore_status=False):
    p = subprocess.Popen(argv,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    status = p.returncode  # raise if non-zero status?
    if status and not ignore_status:
        raise OSError("running '%s' failed: %d: %s"
                      % (' '.join(argv), status, stderr))
    return stdout

def capture_status(argv):
    p = subprocess.Popen(argv,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT)
    output = p.stdout.read()
    retval = p.wait()
    return retval

def remote_run_capture_all(login, cmd, log=None):
    """Run the remote command and return the (retval, stdout, stderr) result."""
    if sys.platform == "win32":
        if '@' not in login:
            login = "%s@%s" % (getpass.getuser(), login)
        cmd = 'plink -A -batch %s "%s"' % (login, cmd)
    else:
        cmd = 'ssh -A -o BatchMode=yes %s "%s"' % (login, cmd)
    __run_log(logstream, "running '%s'", cmd)
    p = subprocess.Popen(argv,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    status = p.returncode
    return status, stdout, stderr



#---- version string manipulation unexpected

# Recipe: ver (1.1.0)
def split_full_ver(ver_str):
    """Split a full version string to component bits.

    >>> split_full_ver('4.0.0-alpha3-12345')
    (4, 0, 0, 'alpha', 3, 12345)
    >>> split_full_ver('4.1.0-beta-12345')
    (4, 1, 0, 'beta', None, 12345)
    >>> split_full_ver('4.1.0-12345')
    (4, 1, 0, None, None, 12345)
    >>> split_full_ver('4.1-12345')
    (4, 1, 0, None, None, 12345)
    >>> split_full_ver('4.3.0')
    (4, 3, 0, None, None, None)
    """
    def _isalpha(ch):
        return 'a' <= ch <= 'z' or 'A' <= ch <= 'Z'
    def _isdigit(ch):
        return '0' <= ch <= '9'
    def split_quality(s):
        for i in reversed(range(1, len(s)+1)):
            if not _isdigit(s[i-1]):
                break
        if i == len(s):
            quality, quality_num = s, None
        else:
            quality, quality_num = s[:i], int(s[i:])
        return quality, quality_num

    bits = []
    for i, undashed in enumerate(ver_str.split('-')):
        for undotted in undashed.split('.'):
            if len(bits) == 3:
                # This is the "quality" section: 2 bits
                if _isalpha(undotted[0]):
                    bits += list(split_quality(undotted))
                    continue
                else:
                    bits += [None, None]
            try:
                bits.append(int(undotted))
            except ValueError:
                bits.append(undotted)
        # After first undashed segment should have: (major, minor, patch)
        if i == 0:
            while len(bits) < 3:
                bits.append(0)
    
    while len(bits) < 6:
        bits.append(None)
    
    return tuple(bits)

_short_ver_re = re.compile("(\d+)(\.\d+)*([a-z](\d+)?)?")
def split_short_ver(ver_str, intify=False, pad_zeros=None):
    """Parse the given version into a tuple of "significant" parts.

    @param intify {bool} indicates if numeric parts should be converted
        to integers.
    @param pad_zeros {int} is a number of numeric parts before any
        "quality" letter (e.g. 'a' for alpha).
   
    >>> split_short_ver("4.1.0")
    ('4', '1', '0')
    >>> split_short_ver("1.3a2")
    ('1', '3', 'a', '2')
    >>> split_short_ver("1.3a2", intify=True)
    (1, 3, 'a', 2)
    >>> split_short_ver("1.3a2", intify=True, pad_zeros=3)
    (1, 3, 0, 'a', 2)
    >>> split_short_ver("1.3", intify=True, pad_zeros=3)
    (1, 3, 0)
    >>> split_short_ver("1", pad_zeros=3)
    ('1', '0', '0')
    """
    def isint(s):
        try:
            int(s)
        except ValueError:
            return False
        else:
            return True
    def do_intify(s):
        try:
            return int(s)
        except ValueError:
            return s

    if not _short_ver_re.match(ver_str):
        raise ValueError("%r is not a valid short version string" % ver_str)

    hit_quality_bit = False
    bits = []
    for bit in re.split("(\.|[a-z])", ver_str):
        if bit == '.':
            continue
        if intify:
            bit = do_intify(bit)
        if pad_zeros and not hit_quality_bit and not isint(bit):
            hit_quality_bit = True
            while len(bits) < pad_zeros:
                bits.append(not intify and "0" or 0)
        bits.append(bit)
    if pad_zeros and not hit_quality_bit:
        while len(bits) < pad_zeros:
            bits.append(not intify and "0" or 0)
    return tuple(bits)

def join_short_ver(ver_tuple, pad_zeros=None):
    """Join the given version-tuple, inserting '.' as appropriate.

    @param pad_zeros {int} is a number of numeric parts before any
        "quality" letter (e.g. 'a' for alpha).
    
    >>> join_short_ver( ('4', '1', '0') )
    '4.1.0'
    >>> join_short_ver( ('1', '3', 'a', '2') )
    '1.3a2'
    >>> join_short_ver(('1', '3', 'a', '2'), pad_zeros=3)
    '1.3.0a2'
    >>> join_short_ver(('1', '3'), pad_zeros=3)
    '1.3.0'
    """
    def isint(s):
        try:
            int(s)
        except ValueError:
            return False
        else:
            return True

    if pad_zeros:
        bits = []
        hit_quality_bit = False
        for bit in ver_tuple:
            if not hit_quality_bit and not isint(bit):
                hit_quality_bit = True
                while len(bits) < pad_zeros:
                    bits.append(0)
            bits.append(bit)
        if not hit_quality_bit:
            while len(bits) < pad_zeros:
                bits.append(0)
    else:
        bits = ver_tuple

    dotted = []
    for bit in bits:
        if dotted and isint(dotted[-1]) and isint(bit):
            dotted.append('.')
        dotted.append(str(bit))
    return ''.join(dotted)

def short_ver_from_full_ver(full_ver):
    full_bits = split_full_ver(full_ver)
    short_bits = list(full_bits[:3])
    if full_bits[3] is not None:
        short_bits.append(full_bits[3][0])
        if full_bits[4] is not None:
            short_bits.append(full_bits[4])
    return join_short_ver(short_bits)


#---- self-test

def _test():
    import doctest
    doctest.testmod()

if __name__ == "__main__":
    _test()

