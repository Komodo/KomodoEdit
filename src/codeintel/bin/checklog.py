
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

