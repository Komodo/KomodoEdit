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

# Recipe: remote (0.5.1)
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
    status = capture_status(argv)
    return status == 0

def remote_mkdir(rpath, log=None):
    login, path = rpath.split(':', 1)
    if sys.platform == "win32":
        cmd = "plink -batch %s mkdir %s" % (login, path)
    else:
        cmd = "ssh -o BatchMode=yes %s mkdir %s" % (login, path)
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

def remote_cp(src, dst, log=None):
    if sys.platform == "win32":
        cmd = 'pscp -q "%s" "%s"' % (src, dst)
    else:
        cmd = 'scp -q -B "%s" "%s"' % (src, dst)
    if log:
        log(cmd)
    status = run(cmd)
    if status:
        raise OSError("error running '%s': status=%r" % (cmd, status))

def remote_symlink(src, dst, log=None):
    assert ' ' not in src and ' ' not in dst
    src_login, src_path = src.split(':', 1)
    dst_login, dst_path = dst.split(':', 1)
    assert src_login == dst_login
    cmd = "ln -s %s %s" % (src_path, dst_path)
    remote_run(src_login, cmd, log=log)

def remote_rm(rpath, log):
    assert ' ' not in rpath
    login, path = rpath.split(':', 1)
    cmd = 'rm -f %s' % path
    buildutils.remote_run(login, cmd, log=log)

def remote_glob(rpattern, log=None):
    login, pattern = rpattern.split(':', 1)
    if sys.platform == "win32":
        argv = ["plink", "-batch", login, "ls", "-d", pattern]
    else:
        argv = ["ssh", "-o", "BatchMode=yes", login, "ls", "-d",
                pattern]
    if log:
        log(' '.join(argv))
    try:
        stdout = capture_stdout(argv)
    except OSError, ex:
        rpaths = []
    else:
        rpaths = ["%s:%s" % (login, p.strip()) 
                  for p in stdout.splitlines(0) if p.strip()]
    return rpaths

def remote_md5sum(rpath, log=None):
    """Return the md5sum for the given remote path.
    
    This relies on 'md5sum' being available and runnable on the remote
    machine. Raises OSError if the md5sum could not be determined.
    """
    login, path = rpath.split(':', 1)
    rcmd = 'md5sum "%s"' % path
    if sys.platform == "win32":
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
        cmd = 'plink -batch %s "%s"' % (login, cmd)
    else:
        cmd = 'ssh -o BatchMode=yes %s "%s"' % (login, cmd)
    status = run(cmd, logstream=log)
    if status:
        raise OSError("error running '%s': status=%r" % (cmd, status))

def capture_stdout(argv, ignore_status=False):
    p = subprocess.Popen(argv,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    stdout = p.stdout.read()
    stderr = p.stderr.read()
    status = p.wait()  # raise if non-zero status?
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


#---- version string manipulation unexpected

# Recipe: ver (0.4)
def split_full_ver(ver_str):
    """
        >>> split_full_ver('4.0.0-alpha3-12345')
        (4, 0, 0, 'alpha', 3, 12345)
        >>> split_full_ver('4.1.0-beta-12345')
        (4, 1, 0, 'beta', None, 12345)
        >>> split_full_ver('4.1.0-12345')
        (4, 1, 0, None, None, 12345)
        >>> split_full_ver('4.1-12345')
        (4, 1, 0, None, None, 12345)
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
    return tuple(bits)

def split_short_ver(ver_str, intify=False):
    """Parse the given version into a tuple of "significant" parts.
   
        >>> split_short_ver("4.1.0")
        ('4', '1', '0')
        >>> split_short_ver("1.3a2")
        ('1', '3', 'a', '2')
        >>> split_short_ver("1.3a2", intify=True)
        (1, 3, 'a', 2)
    """
    def _initify(s):
        try:
            return int(s)
        except ValueError:
            return s
    if intify:
        bits = [_initify(b) for b in re.split("(\.|[a-z])", ver_str)
                if b != '.']
    else:
        bits = [b for b in re.split("(\.|[a-z])", ver_str) if b != '.']
    return tuple(bits)

def join_short_ver(ver_tuple):
    """Join the given version-tuple, inserting '.' as appropriate.
    
        >>> join_short_ver( ('4', '1', '0') )
        '4.1.0'
        >>> join_short_ver( ('1', '3', 'a', '2') )
        '1.3a2'
    """
    def isint(s):
        try:
            int(s)
        except ValueError:
            return False
        else:
            return True

    dotted = []
    for bit in ver_tuple:
        if dotted and isint(dotted[-1]) and isint(bit):
            dotted.append('.')
        dotted.append(str(bit))
    return ''.join(dotted)



#---- self-test

def _test():
    import doctest
    doctest.testmod()

if __name__ == "__main__":
    _test()

