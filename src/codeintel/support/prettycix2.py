#!/usr/bin/env python

"""Convert the given CIX paths to (1) pretty (2) CIX 2.0.

'p4 edit' is called on the file. The CIX file is replaced in-place.
"""

import os
import sys
import logging

try:
    import cElementTree as ET # effbot's C module
except ImportError:
    import elementtree.ElementTree as ET # effbot's pure Python module

import warnings
warnings.filterwarnings("ignore", message="using the slow elementtree here!")
from codeintel2 import Manager
from codeintel2.tree import tree_from_cix, pretty_tree_from_tree

log = logging.getLogger("prettycix2")
log.setLevel(logging.INFO)



def update_cix_file(mgr, path):
    log.info("convert `%s' to pretty CIX 2.0", path)
    cix = open(path, 'r').read()
    tree = tree_from_cix(cix) # converts to CIX 2.0
    tree = pretty_tree_from_tree(tree)
    new_cix = ET.tostring(tree)

    _run("p4 edit %s" % path)
    open(path, 'w').write(new_cix)



#---- internal support stuff


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


#---- mainline

if __name__ == "__main__":
    logging.basicConfig()
    mgr = Manager()
    try:
        for path in sys.argv[1:]:
            update_cix_file(mgr, path)
    finally:
        mgr.finalize()




