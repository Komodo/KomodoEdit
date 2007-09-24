# Copyright (c) 2000-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

# update-files.py  -- copy named files to the destination directory
#                     if the dest files don't exist or the source files are
#                     newer.

# For now, it does no processing on the source files if they contain
# paths.  It should.

from getopt import getopt
import sys
import os
from stat import ST_MTIME
from shutil import copy

destdir=""
verbose=0
process_arg=1

# Must be a better way to process args.

def file_needs_updating (srcfile, destfile):
    try:
        src_stat = os.stat (srcfile)
    except:
        if verbose: print "Can't stat ", srcfile
        return 0
    try:
        dest_stat = os.stat (destfile)
        if verbose: print "Can't stat ", destfile
    except:
        return 1
    res = src_stat[ST_MTIME] > dest_stat[ST_MTIME]
    return res
    
def usage ():
    print "Usage: -d destdir file ...\n"

def test():
    (options, files) = getopt (sys.argv[1:], "d:hv")
    for item in options:
        arg = item[0]
        if arg == '-d':
            destdir = item[1]
            if destdir[-1] != '/' and destdir[-1] != '\\':
                destdir = destdir + "/"
        elif arg == '-h':
            usage()
            return
        elif arg == '-v':
            verbose=1
    if not destdir:
        usage()
        return

    for file in files:
        destfile = destdir + file
        if file_needs_updating(file, destfile):
            print "cp", file, destfile
            copy(file, destdir)

if __name__ == "__main__":
    test ()
