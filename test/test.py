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

"""The Komodo test suite entry point."""

import os
from os.path import exists, join, abspath, dirname, normpath
import sys
import logging


# This is to ensure sitepyxpcom does not redirect the stdio handles.
os.environ["KOMODO_VERBOSE"] = "1"

sys.path.insert(0, normpath(join(dirname(abspath(__file__)), "..", "util")))
import testlib


testdir_from_ns = {
    None: os.curdir,
    "pyxpcom": "pyxpcom",
    "pyxpcom/views": join("..", "src", "views", "test"),
    "ci": join("..", "src", "codeintel", "test2"),
}
default_tags = ["-knownfailure"]


def setup():
    # Get the process.py from src/python-sitelib (incompatibilities
    # introduced in the new src/python-sitelib/process.py for Komodo
    # 4.3.0).
    pylib_dir = join(dirname(dirname(abspath(__file__))),
                     "src", "python-sitelib")
    sys.path.insert(0, pylib_dir)
    try:
        import process
    finally:
        del sys.path[0]
    
    codeintel_test_dir = join(dirname(dirname(abspath(__file__))),
                              "src", "codeintel", "test2")
    sys.path.insert(0, codeintel_test_dir)
    try:
        import test
        test.setup()
    except ImportError, ex:
        pass  # Don't bork if don't have full codeintel build.
    finally:
        del sys.path[0]

def _setup_for_xpcom():
    # The tests are run outside of Komodo. If run with PyXPCOM up
    # parts codeintel will try to use the nsIDirectoryService and
    # will query dirs only provided by nsXREDirProvider -- which
    # isn't registered outside of Komodo (XRE_main() isn't called).
    # The KoTestService provides a backup.
    from xpcom import components
    koTestSvc = components.classes["@activestate.com/koTestService;1"] \
        .getService(components.interfaces.koITestService)
    koTestSvc.init()

if __name__ == "__main__":
    _setup_for_xpcom()
    retval = testlib.harness(testdir_from_ns=testdir_from_ns,
                             setup_func=setup,
                             default_tags=default_tags)
    sys.exit(retval)

