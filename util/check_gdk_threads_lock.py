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

"""
Check the current Linux system for the gdk_threads_lock Komodo symbol
dependency.

Usage:
    python check_gdk_threads_lock.py
"""

import os
import sys
import logging
import glob
import pprint

log = logging.getLogger("check")
LIB = "gdk"
SYMBOL = "gdk_threads_lock"

if __name__ == "__main__":
    logging.basicConfig()
    if not sys.platform.startswith("linux"):
        log.error("it only makes sense to run this script on linux")
        sys.exit(1)
    if len(sys.argv) > 1:
        log.error("incorrect number of arguments")
        print __doc__
        sys.exit(1)
    
    # Get the list of lib dirs to check.
    libdirs = ["/lib", "/usr/lib"]
    for line in open("/etc/ld.so.conf", 'r'):
        libdirs.append(line.strip())

    # Find all appropriate libs.
    libs = []
    for libdir in libdirs:
        libs += glob.glob(os.path.join(libdir, "lib%s-*.so*" % LIB))
        libs += glob.glob(os.path.join(libdir, "lib%s.so*" % LIB))
    pprint.pprint(libs)

    # Look for the symbol in these libs.
    for lib in libs:
        cmd = "nm -o %s | grep %s" % (lib, SYMBOL)
        status = os.system(cmd)
        if status:
            log.error("'%s' not found in '%s'", SYMBOL, lib)


