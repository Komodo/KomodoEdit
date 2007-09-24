#!/usr/bin/env python

"""
Check the current Linux system for the gdk_threads_lock Komodo symbol
dependency.

Usage:
    python check_gdk_threads_lock.py
"""

import os
import sys
import logging
import glob
import pprint

log = logging.getLogger("check")
LIB = "gdk"
SYMBOL = "gdk_threads_lock"

if __name__ == "__main__":
    logging.basicConfig()
    if not sys.platform.startswith("linux"):
        log.error("it only makes sense to run this script on linux")
        sys.exit(1)
    if len(sys.argv) > 1:
        log.error("incorrect number of arguments")
        print __doc__
        sys.exit(1)
    
    # Get the list of lib dirs to check.
    libdirs = ["/lib", "/usr/lib"]
    for line in open("/etc/ld.so.conf", 'r'):
        libdirs.append(line.strip())

    # Find all appropriate libs.
    libs = []
    for libdir in libdirs:
        libs += glob.glob(os.path.join(libdir, "lib%s-*.so*" % LIB))
        libs += glob.glob(os.path.join(libdir, "lib%s.so*" % LIB))
    pprint.pprint(libs)

    # Look for the symbol in these libs.
    for lib in libs:
        cmd = "nm -o %s | grep %s" % (lib, SYMBOL)
        status = os.system(cmd)
        if status:
            log.error("'%s' not found in '%s'", SYMBOL, lib)


