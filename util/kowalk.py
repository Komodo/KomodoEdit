#!/usr/bin/env python
# Copyright (c) 2004-2006 ActiveState Software Inc.
#
# Contributors:
#   Trent Mick (TrentM@ActiveState.com)

"""
    kowalk - Walk the Komodo source tree and talk some action on files.
    
    Usage:
        kowalk [options...] <dirs...>

    General Options:
        -h, --help          print this help and exit
        -V, --version       print version and exit
        -v, --verbose       verbose output
        -R, --recursive     recursively descend into directories

    Actions:
        --remove-trailing-whitespace, -W
"""


import os
import sys
import getopt
import logging
import re

# Avoid stupid FCNTL.py warning in tempfile.py in Python 2.3.
import warnings
warnings.filterwarnings("ignore", module="fcntl")

try:
    import p4lib
except ImportError:
    sys.stderr.write("kowalk: error: could not import 'p4lib', get it from starship.python.net/~tmick")
    sys.exit(1)


#---- exceptions

class Error(Exception):
    pass


#---- global data

_version_ = (0, 1, 0)
log = logging.getLogger("kowalk")



#---- internal routines and classes

def _is_binary(filename):
    """Return true iff the given filename is binary.

    Raises an EnvironmentError if the file does not exist or cannot be
    accessed.
    """
    fin = open(filename, 'rb')
    try:
        CHUNKSIZE = 1024
        while 1:
            chunk = fin.read(CHUNKSIZE)
            if '\0' in chunk: # found null byte
                return 1
            if len(chunk) < CHUNKSIZE:
                break # done
    finally:
        fin.close()
    return 0


#---- public module interface

def remove_trailing_whitespace(fpath, p4):
    """Remove trailing whitespace from this file, if appropriate.
    
    Returns true if the file was modified (and opened from Perforce).
    """
    log.debug("remove_trailing_whitespace(fpath='%s')", fpath)
    if _is_binary(fpath):
        log.debug("skip binary file: '%s'", fpath)
        return False

    f = open(fpath, 'rb')
    try:
        content = f.read()
    finally:
        f.close()

    changed = False
    cleaned = re.sub(r"[ \t]+(\r\n|\r|\n)", r"\1", content)
    if content == cleaned:
        log.debug("no trailing whitespace in '%s'", fpath)
        return False

    if p4.opened(fpath):
        log.warn("skipping removing trailing whitespace from '%s': file "
                 "is already open from Perforce", fpath)
        return False

    print "removing trailing whitespace in '%s'" % fpath
    p4.edit(fpath)
    f = open(fpath, 'wb')
    try:
        f.write(cleaned)
    finally:
        f.close()
    return True
    
    

def kowalk(action, walkdirs, recursive=False):
    p4 = p4lib.P4()
    for walkdir in walkdirs:
        log.info("traversing '%s'...", walkdir)
        if recursive:
            p4files = p4.have(walkdir+"/...")
        else:
            p4files = p4.have(walkdir+"/*")
        for p4file in p4files:
            action(p4file["localFile"], p4=p4)



#---- mainline

def main(argv):
    logging.basicConfig()
    log.setLevel(logging.INFO)

    # Parse options.
    try:
        opts, args = getopt.getopt(argv[1:], "VvhWR",
            ["version", "verbose", "help", "remove-trailing-whitespace",
             "recursive"])
    except getopt.GetoptError, ex:
        log.error(str(ex))
        log.error("Try `kowalk --help'.")
        return 1
    recursive = False
    action = None
    for opt, optarg in opts:
        if opt in ("-h", "--help"):
            sys.stdout.write(__doc__)
            return
        elif opt in ("-V", "--version"):
            ver = '.'.join([str(part) for part in _version_])
            print "kowalk %s" % ver
            return
        elif opt in ("-v", "--verbose"):
            log.setLevel(logging.DEBUG)
        elif opt in ("-R", "--recursive"):
            recursive = True
        elif opt in ("-W", "--remove-trailing-whitespace"):
            action = remove_trailing_whitespace

    # Carry out action.
    try:
        if action is None:
            raise Error("no action option was specified")
        kowalk(action, args, recursive=recursive)
    except Error, ex:
        log.error(str(ex))
        if log.isEnabledFor(logging.DEBUG):
            print
            import traceback
            traceback.print_exception(*sys.exc_info())
        return 1
    except KeyboardInterrupt:
        log.debug("user abort")
        pass


if __name__ == "__main__":
    sys.exit( main(sys.argv) )

