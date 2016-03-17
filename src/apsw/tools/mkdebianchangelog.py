#!/usr/bin/env python

import sys
import os
import time

desiredversion=sys.argv[1]
debver=sys.argv[2]
maintainer=sys.argv[3]
series=sys.argv[4]

if os.path.exists("debian/changelog"):
    os.remove("debian/changelog")

lines=[l.rstrip() for l in open("doc/changes.rst", "rtU").readlines()]
found=False
for i in range(len(lines)):
    if lines[i]==desiredversion and lines[i+1].startswith("===="):
        found=True
        lines=lines[i+2:]
        break

if not found:
    raise Exception("Could not find version "+desiredversion+" in doc/changes.rst")

found=False
for i in range(len(lines)):
    if lines[i].startswith("===="):
        found=True
        lines=lines[:i-1]
        break

# Strip blank lines
while len(lines[0])==0:
    lines=lines[1:]

while len(lines[-1])==0:
    lines=lines[:-1]

out=open("debian/changelog", "wt")
print >> out, "python-apsw (%s-%s) %s; urgency=low" % (desiredversion, debver, series)
print >> out
for l in lines:
    print >> out, "  "+l
print >> out
print >> out, " -- %s  %s" % (maintainer, time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime()))
out.close()
                              
