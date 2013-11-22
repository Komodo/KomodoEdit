#!/usr/bin/env python
# Copyright (c) 2007 ActiveState Software Inc.

"""The doit test suite entry point."""

import os
from os.path import dirname, abspath
import sys
import logging

import testlib


testdir_from_ns = {
    None: os.curdir,
}

def setup():
    sys.path.insert(0, dirname(dirname(abspath(__file__))))

if __name__ == "__main__":
    retval = testlib.harness(testdir_from_ns=testdir_from_ns,
                             setup_func=setup)
    sys.exit(retval)

