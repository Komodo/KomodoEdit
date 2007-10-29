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

import sys, os
names = {}

print sys.argv[1]
map = eval(open(sys.argv[1]).read())

import re

for fname in sys.argv[2:]:
    data = open(fname).read()
    for orig, target in map:
        p = re.compile(orig, re.M)
        matched = re.search(p, data)
        if matched:
            if not names.has_key(fname):
                names[fname] = []
            names[fname].append((orig, target))
import pprint
#pprint.pprint(names)
if 1:
    for fname in names.keys():
        print 'do fname', fname,  names[fname]
        os.system('p4 edit ' + fname)
        data = open(fname).read()
        for orig, target in names[fname]:
            p = re.compile(orig, re.M)
            data = re.sub(p, target, data)
        open(fname, 'w').write(data)


