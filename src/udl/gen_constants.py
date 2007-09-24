#!/usr/bin/env python
# Copyright (c) 2006 ActiveState Software Inc.

"""Update ludditelib/constants.py from the current LexUDL.cxx and
Scintilla.iface.

Usage:
    p4 edit ludditelib/constants.py
    python gen_constants.py > ludditelib/constants.py
    p4 submit ludditelib/constants.py  # if there are any changes

This script presumes that the Scintilla sources are at ../scintilla
relative to the current directory.
"""

import os
from os.path import join
import pprint
import re
import sys
import datetime


SCINTILLA_DIR = join("..", "scintilla")
SCINTILLA_IFACE_PATH = join(SCINTILLA_DIR, "include", "Scintilla.iface")
LEXUDL_CXX_PATH = join(SCINTILLA_DIR, "src", "LexUDL.cxx")



def get_constants():
    def1_re = re.compile(r'#define\s+([^\s]+)\s+(\d+)')
    resConstants = {}
    fh = open(LEXUDL_CXX_PATH)
    # First look for where the import started
    while True:
        line = fh.readline()
        if not line: break
        elif line.find("Classes from UDL_Tables.h") >= 0: break
    if line:
        while True:
            line = fh.readline()
            if not line: break
            elif line.find("End UDL_Tables.h classes") >= 0: break
            mo1 = def1_re.match(line)
            if mo1:
                resConstants[mo1.group(1)] = int(mo1.group(2))
    fh.close()
    if len(resConstants.keys()) == 0:
        sys.stderr.write("Couldn't find any defines in file "
                         + LEXUDL_CXX_PATH + "\n")
        sys.exit(1)

    def2_re = re.compile(r'val (SCE_UDL.*)=(\d+)\s*$')
    fh = open(SCINTILLA_IFACE_PATH)
    while True:
        line = fh.readline()
        if not line: break
        mo1 = def2_re.match(line)
        if mo1:
            resConstants[mo1.group(1)] = int(mo1.group(2))
    fh.close()
    if len(resConstants.keys()) == 0:
        sys.stderr.write("Couldn't find any defines in file "
                         + SCINTILLA_IFACE_PATH + "\n")
        sys.exit(1)
    return resConstants


def gen_constants():
    resConstants = get_constants()
    print "# Generated on ", datetime.datetime.now().ctime()
    print "#"
    print "# List of constants used by luddite"
    print
    print "vals = ",
    pprint.PrettyPrinter(indent=4).pprint(resConstants)

if __name__ == "__main__":
    gen_constants()

