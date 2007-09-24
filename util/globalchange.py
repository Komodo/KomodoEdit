# Copyright (c) 2000-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

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


