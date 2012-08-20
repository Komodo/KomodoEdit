#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
# 
# The contents of this file are subject to the Mozilla Public License
# Version 1.1 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
# 
# Software distributed under the License is distributed on an "AS IS"
# basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
# License for the specific language governing rights and limitations
# under the License.
# 
# The Original Code is Komodo code.
# 
# The Initial Developer of the Original Code is ActiveState Software Inc.
# Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
# ActiveState Software Inc. All Rights Reserved.
# 
# Contributor(s):
#   ActiveState Software Inc
# 
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
# 
# ***** END LICENSE BLOCK *****

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
LEXUDL_CXX_PATH = join(SCINTILLA_DIR, "lexers", "LexUDL.cxx")



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

