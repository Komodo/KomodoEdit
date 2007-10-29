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
 USAGE: python patch-template.py <templatefile> <outputfile>
           [[<key> <replacement-string>|@<replacement-file>]... ]

 Patch the given template file (<templatefile>) with the given dictionary
 (string of key, value pairs on the command line). If the replacement value
 begins with '@' and identifies a file then the contents of the file (instead
 of the string itself) are used as the replacement value. The output is written
 to <outputfile>.

 Examples:
   python patch-template.py install.sh.template install.sh
       __DEFAULT_INSTALLDIR__ /usr/local/Komodo-1.0
   python patch-template.py LICENSE.html.template LICENSE.html
       __LICENSE_TEXT__ @src/doc/LICENSE.txt
"""

import sys, os

# process the command line
if len(sys.argv) < 3 or len(sys.argv) % 2 != 1:
    sys.stderr.write("%s: error: invalid number of args\n" % sys.argv[0])
    sys.stderr.write(sys.modules["__main__"].__doc__)
    sys.exit(1)
inFileName, outFileName = sys.argv[1:3]
theRest = sys.argv[3:]
if inFileName == outFileName:
    sys.stderr.write("%s: error: Can't handle in-place patching.\n" %\
        sys.argv[0])

templateMap = {}
while theRest:
    key, value, theRest = theRest[0], theRest[1], theRest[2:]
    if value.startswith('@'):
        fname = value[1:]
        fin = open(fname, "r")
        value = fin.read()
        fin.close()
    templateMap[key] = value

print "Creating '%s' from template file '%s'.\n" % (outFileName, inFileName)

# process file
fin = open(inFileName, "r")
fout = open(outFileName, "w")

for line in fin.readlines():
    for pattern in templateMap.keys():
        line = line.replace(pattern, templateMap[pattern])
    fout.write(line)

fin.close()
fout.close()

