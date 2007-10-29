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

# Analyze a "sql.log" sqlite connection SQL statement log for potential
# duplicate SQL queries that could be optimized away.

import os
import sys
import pprint

sqllog = "sql.log"
queries = {}

for i,line in enumerate(open(sqllog, 'r')):
    line = line.strip()
##    print "%d: %s" % (i, line)
    info = queries.setdefault(line, [])
    info.append(i)

dupes = []
numdupes = 0
numwastes = 0
for query, linenums in queries.items():
    if len(linenums) > 1:
        dupes.append((len(linenums), query))
        numdupes += 1
        numwastes += len(linenums) - 1

dupes.sort()
for dupe in dupes:
    print "%4d repeats: %s" % dupe

print
print "Number of dupes: %r" % numdupes
print "Theoretical max number of wasted queries: %r" % numwastes

