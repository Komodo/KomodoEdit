#!/usr/bin/env python
# Copyright (c) 2010 ActiveState Software Inc.

import sys
from os.path import join, dirname, abspath, exists
import subprocess
import shutil

def do_clean_unicode_directories():
    """ Remove the unicode directories after running `ci2 test`."""
    dirpath = dirname(abspath(__file__))
    for name in ("scan_inputs", "scan_outputs", "scan_actual"):
        unipath = join(dirpath, name, "unicode")
        if exists(unipath):
            if sys.platform.startswith("win"):
                # Must use the Windows rd command, as the Python tools will
                # break trying to walk over the directory contents.
                cmd = ["rd", "/s", "/q"]
                cmd.append(unipath)
                p = subprocess.Popen(cmd, cwd=dirpath, shell=True)
                retval = p.wait()
            else:
                shutil.rmtree(unipath)

def main():
    do_clean_unicode_directories()

if __name__ == "__main__":
    main()
