#!/usr/bin/env python

import os
import sys

#
# USAGE: python objective_c_wrap.py %1 %2
#
# Examples:
#   python objective_c_wrap.py nsSciMoz.cxx nsSciMoz.mm

def usage():
    print "Usage: python objective_c_wrap.py %1 %2"
    print
    print "Where %1 is .cpp or .cxx file to wrap, %2 is the wrapped .mm file"

def make_objective_c_wrapper(src, dest):
    file(dest, "w").write(
"""/* Wrapper file to allow C++ code to be treated as objective-C. */

#include "%s"
""" % (os.path.basename(src)))

if __name__ == '__main__':
    if len(sys.argv) != 3:
        usage()
        sys.exit(2)

    src, dest = sys.argv[1:3]
    make_objective_c_wrapper(src, dest)
