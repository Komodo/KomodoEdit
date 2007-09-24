#!python
# Copyright (c) 2004-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

import os
import sys
import md5
import logging
import shutil



log = logging.getLogger("codeintel.db")



def filter_blobnames_for_prefix(candidates, prefix, sep):
    """Given a iterator of candidate blob names, return a set of
    2-tuples indicating each match:
    
        (<sub-name>, <is-partial-match>)

    where,
        <sub-name> is the import component after the prefix
        <is-partial-match> is a boolean indicating if suffix is
            multipart.

    For example, given:
        candidates = ["LWP",
                      "LWP::Authen::Basic", "LWP::Authen::Digest",
                      "LWP::ConnCache",
                      "LWP::Protocol",
                      "LWP::Protocol::http", "LWP::Protocol::https",
                      "LWP::UserAgent"]
        prefix = ("LWP",)
        sep = "::"
    the returned items should be:
        ("Authen",    True)
        ("ConnCache", False)
        ("Protocol",  False)
        ("Protocol",  True)
        ("UserAgent", False)
    """
    matches = set()
    if not prefix:
        for name in candidates:
            if name == "*": continue  # skip "built-in" blob
            if sep in name:
                matches.add( (name[:name.index(sep)], True) )
            else:
                matches.add( (name, False) )
    else:
        sep_len = len(sep)
        sepped_prefix = sep.join(prefix)
        for name in candidates:
            if name == "*": continue  # skip "built-in" blob
            if name.startswith(sepped_prefix + sep):
                # e.g. prefix is "xml", and we see "xml.sax" and "xml.bar.foo"
                subname = name[len(sepped_prefix)+sep_len:]
                # subname is "sax" and "bar.foo"
                if sep in subname:
                    # we want to return bar, not bar.foo
                    subname = subname[:subname.index(sep)]
                    is_partial_match = True
                else:
                    is_partial_match = False
                matches.add( (subname, is_partial_match) )
    return matches


def rmdir(dir):
    """Remove the given dir. Raises an OSError on failure."""
    if sys.platform == "win32":
        # Apparent just running 'rd' (or else because run via
        # process.Process) on Windows == DOS box flash (bug 61348).
        log.debug("fs-write: rmdir `%s'", dir)
        shutil.rmtree(dir, 0, _rmtree_onerror)
    else:
        run('rm -rf "%s"' % dir)

def _rmtree_onerror(rm_func, path, exc_info):
    if exc_info[0] == OSError:
        # presuming because file is read-only
        os.chmod(path, 0777)
        rm_func(path)



#---- internal support routines

# Recipe: run (0.5.3) in /home/trentm/tm/recipes/cookbook
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

def run(cmd, logstream=_RUN_DEFAULT_LOGSTREAM):
    """Run the given command.

        "cmd" is the command to run
        "logstream" is an optional logging stream on which to log the 
            command. If None, no logging is done. If unspecifed, this 
            looks for a Logger instance named 'log' and logs the command 
            on log.debug().

    Raises OSError is the command returns a non-zero exit status.
    """
    __run_log(logstream, "running '%s'", cmd)

    # Using os.system on Windows == DOS box flash (bug 61348).
    # TODO: Perhaps we should use Process for all plats? (bug 65961).
    if sys.platform == "win32":
        import process
        p = process.Process(cmd)
        retval = p.wait()
    else:
        retval = os.system(cmd)

    if hasattr(os, "WEXITSTATUS"):
        status = os.WEXITSTATUS(retval)
    else:
        status = retval
    if status:
        #TODO: add std OSError attributes or pick more approp. exception
        raise OSError("error running '%s': %r" % (cmd, status))

def run_in_dir(cmd, cwd, logstream=_RUN_DEFAULT_LOGSTREAM):
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
        run(cmd, logstream=None)
    finally:
        os.chdir(old_dir)

