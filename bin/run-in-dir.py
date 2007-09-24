#!python
# Copyright (c) 2000-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

#
# USAGE: python run-in-dir.py %1:d <invocation>
#
# Run the given invocation string in the given directory.
#
# Examples:
#   python run-in-dir.py build\debug\Rx python c:\bin\make-rx-module.py

if __name__ == '__main__':
    import sys, os
    targetDir, invocation = sys.argv[1], " ".join(sys.argv[2:])
    print "cd %s" % targetDir
    os.chdir(targetDir)
    print invocation
    retval = os.system(invocation)
    if not sys.platform.startswith("win"):
        retval = retval >> 8
    sys.exit(retval)
