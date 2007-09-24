#!/usr/bin/env python
# Copyright (c) 2000-2007 ActiveState Software Inc.

"""The Komodo test suite entry point."""

import os
from os.path import exists, join, abspath, dirname, normpath
import sys
import logging

sys.path.insert(0, normpath(join(dirname(abspath(__file__)), "..", "util")))
import testlib


testdir_from_ns = {
    None: os.curdir,
    "pyxpcom": "pyxpcom",
    "ci": join("..", "src", "codeintel", "test2"),
}


def setup():
    codeintel_test_dir = join(dirname(dirname(abspath(__file__))),
                              "src", "codeintel", "test2")
    sys.path.insert(0, codeintel_test_dir)
    try:
        import test
        test.setup()
    finally:
        del sys.path[0]


if __name__ == "__main__":
    retval = testlib.harness(testdir_from_ns=testdir_from_ns,
                             setup_func=setup)
    sys.exit(retval)

