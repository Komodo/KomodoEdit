#!/usr/bin/env python
# Copyright (c) 2007 ActiveState Software Inc.

"""
    svn_add_ignore - add the given strings to svn:ignore properties

    Usage:
        svn_add_ignore IGNORE-PATTERN PATH...


    Add the given IGNORE-PATTERN to the svn:ignore list for the given
    paths. Useful when starting out a new project and have lots of
    directories for which you want to add a particular 'svn:ignore' --
    "*.pyc" is a typical one.

    Please report inadequacies to Trent Mick <trentm at google's mail thing>.
"""

__version_info__ = (1, 0, 0)
__version__ = '.'.join(map(str, __version_info__))

import os
import sys
import optparse
import logging
import glob
import stat
import tempfile



#---- globals

log = logging.getLogger("svn_add_ignore")



#---- main routines

def svn_add_ignore(ignore_pattern, paths, strip_basename=False):
    """
    "strip_basename" is a boolean (default False) indicating if the basename
        should be stripped from each path. This is convenient for
        copy-'n-pasting output from 'svn status' to set 'svn:ignore' on
        the *dirs* of the mentioned files.
    """
    if sys.platform == "win32":
        value_path = tempfile.mktemp()
    for path in paths:
        if strip_basename:
            path = os.path.dirname(path)
            assert os.path.isdir(path)
        props = _quick_proplist(path)
        if 'svn:ignore' in props:
            ignores = props["svn:ignore"].split('\n')
            if ignore_pattern in ignores:
                log.info("`%s' already in 'svn:ignore' for `%s'",
                         ignore_pattern, path)
                continue
            assert props['svn:ignore'].endswith('\n')
            value = props['svn:ignore'] + ignore_pattern
        else:
            value = ignore_pattern
        log.info("adding `%s' to 'svn:ignore' for `%s'",
                 ignore_pattern, path)
        if sys.platform == "win32":
            open(value_path, 'w').write(value)
            cmd = '''svn ps -F "%s" svn:ignore "%s"''' % (value_path, path)
        else:
            cmd = '''svn ps svn:ignore '%s' "%s"''' % (value, path)
        _run(cmd, log.debug)
    if sys.platform == "win32":
        if os.path.exists(value_path):
            os.remove(value_path)


#---- internal support stuff

# Adapted from core python's svneol.py::proplist().
def _quick_proplist(path):
    "Return a list of property names for file fn in directory root"
    if os.path.isdir(path):
        path = os.path.join(path, ".svn", "dir-props")
    else:
        root, fn = os.path.split(path)
        path = os.path.join(root, ".svn", "props", fn+".svn-work")
    try:
        f = open(path)
    except IOError:
        # no properties file: not under version control
        return {}
    result = {}
    while 1:
        # key-value pairs, of the form
        # K <length>
        # <keyname>NL
        # V length
        # <value>NL
        # END
        line = f.readline()
        if line.startswith("END"):
            break
        assert line.startswith("K ")
        L = int(line.split()[1])
        key = f.read(L)
        f.readline()
        line = f.readline()
        assert line.startswith("V ")
        L = int(line.split()[1])
        result[key] = f.read(L)
        f.readline()
    f.close()
    return result


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

def _run(cmd, logstream=_RUN_DEFAULT_LOGSTREAM, dry_run=False):
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

def _run_in_dir(cmd, cwd, logstream=_RUN_DEFAULT_LOGSTREAM, dry_run=False):
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
        _run(cmd, logstream=None)
    finally:
        if not dry_run:
            os.chdir(old_dir)



#---- mainline

class _NoReflowFormatter(optparse.IndentedHelpFormatter):
    """An optparse formatter that does NOT reflow the description."""
    def format_description(self, description):
        return description or ""

def main(argv=sys.argv):
    usage = "usage: %prog [OPTIONS...]"
    version = "%prog "+__version__
    parser = optparse.OptionParser(prog="svn_add_ignore", usage=usage,
        version=version, description=__doc__,
        formatter=_NoReflowFormatter())
    parser.add_option("-v", "--verbose", dest="log_level",
                      action="store_const", const=logging.DEBUG,
                      help="more verbose output")
    parser.add_option("-s", "--strip-basename", action="store_true",
                      help="strip basename from given paths")
    parser.set_defaults(log_level=logging.INFO, strip_basename=False)
    opts, args = parser.parse_args()
    log.setLevel(opts.log_level)

    ignore_pattern, paths = args[0], args[1:]
    return svn_add_ignore(ignore_pattern, paths, opts.strip_basename)


if __name__ == "__main__":
    logging.basicConfig()
    sys.exit( main(sys.argv) )


