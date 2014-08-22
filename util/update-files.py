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
