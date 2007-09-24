#!python

"""
    Give some info about each directory below the current one.

    Usage:
        python dirinfo.py [<options>] <dname>

    Options:
        -h, --help      Print this help and exit.

    This can be useful for trying to track down PerlMSI DB Commit
    failures. PerlMSI on Komodo has been known to hit limits on the
    number of MSI components: directly related to the number of files in
    Komodo (limit of about 2600) or the number of files in one directory
    (limit of about 600).

    Examples:
        > python dirinfo.py . | c:\\bin\\cygwin\\bin\\sort.exe -n
"""

import os
import sys
import getopt


def _gatherDirInfo(data, dname, fnames):
    numFiles = len(fnames) # should dir names be purged
    numBytes = 0
    for fname in fnames:
        numBytes += os.stat(os.path.join(dname, fname)).st_size
    data.append((dname, numFiles, numBytes))

def dirinfo(argv):
    # Process argv.
    try:
        optlist, args = getopt.getopt(argv[1:], 'haVvq',
            ['help', 'all', 'version', 'verbose', 'quiet'])
    except getopt.GetoptError, msg:
        print "which: error: %s. Your invocation was: %s\n" % (msg, argv)
        print __doc__
        return 1
    for opt, optarg in optlist:
        if opt in ('-h', '--help'):
            print __doc__
            return 0
    if len(args) != 1:
        sys.stderr.write("dirinfo.py: incorrect number of arguments\n")
        sys.stderr.write("(Try 'python dirinfo.py --help'.)\n")
        return 1
    top = args[0]

    data = []
    os.path.walk(top, _gatherDirInfo, data)
    totalNumFiles = 0
    totalNumBytes = 0
    for dname, numFiles, numBytes in data:
        totalNumFiles += numFiles
        totalNumBytes += numBytes
        print "%d files, %d bytes - dir %s" % (numFiles, numBytes, dname)
    print "-"*60
    print "Summary: %d files, %d bytes" % (totalNumFiles, totalNumBytes)


if __name__ == "__main__":
    sys.exit( dirinfo(sys.argv) )

