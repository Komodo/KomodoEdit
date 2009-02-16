#!/usr/bin/env python

from os.path import dirname, abspath, join
import sys
try:
    import testlib
except ImportError:
    top_dir = dirname(dirname(dirname(abspath(__file__))))
    sys.path.insert(0, join(top_dir, "util"))
    import testlib
    del sys.path[0]



default_tags = ["-knownfailure"]

def setup():
    pass

if __name__ == "__main__":
    retval = testlib.harness(setup_func=setup,
                             default_tags=default_tags)
    sys.exit(retval)