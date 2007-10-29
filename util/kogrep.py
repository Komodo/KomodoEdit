#!/usr/bin/env python
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
# Contributors:
#   Todd Whiteman (ToddW@ActiveState.com)

"""Perform a grep-like recursive search and prompt to open the matches with Komodo."""

#
# Example usage:
#                kogrep koIFTP
#                kogrep "Find this string"
#

import os, sys, re
import traceback
from optparse import OptionParser

# File patterns to include in the search
include_file_patterns = [
    '*.py',
    '*.js',
    '*.xul',
    '*.xml',
    '*.cpp',
    '*.c',
    '*.cxx',
    '*.h',
    'Con*',
    '*.css',
    '*.idl',
]

# File patterns to exclude in the search
exclude_file_patterns = [
    'webdata.js'
]

####################################################
# Should not need to customize anything below here #
####################################################

rematch = re.compile(r'^(.*?):(\d+):(.*)$')
basedir = os.getcwd()

def mainHandler(opts, args):
    grep_args = ['-n', '-r']
    if opts.ignore_case:
        grep_args.append('-i')
    grep_args = ' '.join(grep_args)

    # Work out the included files
    include_patterns = include_file_patterns
    if opts.include_types:
        include_patterns += opts.include_types
    include_types = ' --include='.join(include_patterns)
    if len(include_patterns) > 0:
        include_types = '--include=' + include_types

    # Work out the excluded files
    exclude_patterns = exclude_file_patterns
    if opts.ignore_matches:
        exclude_patterns += opts.ignore_matches
    exclude_types = ' --exclude='.join(exclude_patterns)
    if len(exclude_patterns) > 0:
        exclude_types = '--exclude=' + exclude_types

    for name in args:
        grep_command = "grep %s '%s' %s %s *" % (grep_args, name, include_types, exclude_types)
        #print grep_command
        #continue
        lines = os.popen(grep_command).readlines()
        if len(lines) == 0:
            continue
        max_len = 0
        grep_results = []
        for line in lines:
            regroups = rematch.search(line)
            if not regroups:
                print "ERROR: Re match problem on line '%s'" % (line)
                continue
            regroups = regroups.groups()
            grep_results.append(regroups)
            if len(regroups[0]) > max_len:
                max_len = len(regroups[0])

        pos = 1
        if not opts.show_long_listings:
            max_len = 38
        format = "%%%dd) %%-%ds:%%s: %%s" % (len(str(len(lines))), max_len)
        for filename, line_number, data in grep_results:
            if not opts.show_long_listings:
                if len(filename) > 40:
                    filename = "%s...%s" % (filename[:10], filename[-25:])
                data = data.strip()
            print format % (pos, filename, line_number, data)
            pos += 1

        x = raw_input("Open which one in komodo: ")
        try:
            while x:
                val = int(x)
                if val > 0 and val <= len(grep_results):
                    filename, line_number, data = grep_results[val - 1]
                    if opts.ignore_case:
                        data = data.lower()
                        name = name.lower()
                    pos_start = data.find(name) + 1
                    pos_end   = pos_start + len(name)
                    komodo_command = 'komodo -s %s,%d-%s,%d "%s"' % (line_number, pos_start, \
                                                             line_number, pos_end, \
                                                             os.path.abspath(filename))
                    print komodo_command
                    os.popen(komodo_command)
                x = raw_input("Open which one in komodo: ")
        except Exception, e:
            print e
            traceback.print_exc()
            print "Invalid number: '%s'" % (x)

# Parse the command line parameters
def main(argv=None):
    global basedir
    currentPath = os.path.abspath(os.curdir)
    try:
        if argv is None:
            argv = sys.argv
        parser = OptionParser()
        parser.add_option("-l", "--long", dest="show_long_listings",
                          action="store_true", help="don't truncate line listings")
        parser.add_option("-i", "--ignore-case", dest="ignore_case",
                          action="store_true", help="Case insensitve searching")
        parser.add_option("-p", "--path", dest="dir_path",
                          action="store", type="string", help="Search this path instead")
        parser.add_option("-v", "--invert-match", dest="ignore_matches",
                          action="append", type="string", help="Ignore this word")
        parser.add_option("-a", "--include", dest="include_types",
                          action="append", type="string", help="Include this file type (ex. --include *.cpp)")
        (opts, args) = parser.parse_args()
        #print "opts:", opts
        #print "args:", args
        if opts.dir_path:
            basedir = opts.dir_path
        os.chdir(basedir)
        mainHandler(opts, args)
    finally:
        os.chdir(currentPath)

if __name__ == "__main__":
    sys.exit(main())
