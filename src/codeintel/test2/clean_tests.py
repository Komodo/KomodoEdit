#!/usr/bin/env python
# Copyright (c) 2010 ActiveState Software Inc.

import sys
import os
from os.path import join
import shutil

from test_cile import gInputsDir, gOutputsDir, gTmpDir

def do_clean_unicode_directories(self, argv):
    """ Remove the unicode directories after running `ci2 test`."""
    import subprocess
    testdir = join(dirname(__file__), "test2")
    cmd = '"%s" clean_tests.py' % (sys.executable,)
    env = os.environ.copy()
    p = subprocess.Popen(cmd, cwd=testdir, env=env, shell=True)
    p.wait()
    return p.returncode

def main(argv=None):
    remove_unicode_directories()

if __name__ == "__main__":
    main(sys.argv)
