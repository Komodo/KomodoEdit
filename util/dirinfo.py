#!python

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

