#!python
# Copyright (c) 2000-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

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

