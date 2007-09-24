# just to check for duplicate key bindings in our kkf files
import os, sys

f = open(sys.argv[1],'r')
lines = f.readlines()
f.close()

records = {}
for l in lines:
    r = l.split(' ',2)
    #print r
    if (len(r) < 3): continue
    if r[2] in records:
        print "binding for %s is duplicated" % r[2]
    records[r[2]] = l
