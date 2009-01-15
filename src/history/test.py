#!/usr/bin/env python

from os.path import *
import sys
sys.path.insert(0, expanduser("~/tm/sandbox/testlib")) #XXX
import testlib



default_tags = ["-knownfailure"]

def setup():
    pass

if __name__ == "__main__":
    retval = testlib.harness(#testdir_from_ns=testdir_from_ns,
                             setup_func=setup,
                             default_tags=default_tags)
    sys.exit(retval)