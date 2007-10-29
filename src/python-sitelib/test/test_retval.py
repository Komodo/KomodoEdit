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

"""Test simple stdout (and stderr) hookup in spawning a child process."""

import os
import sys
import time
import pprint
import unittest

import process


class RetvalTestCase(unittest.TestCase):
    def _assertRetvalIs(self, expected, actual):
        if sys.platform.startswith("win"):
            self.failUnless(actual == expected)
        else:
            self.failUnless(os.WIFEXITED(actual))
            exitStatus = os.WEXITSTATUS(actual)
            # convert from 8-bit unsigned to signed
            if exitStatus >= 2**7: exitStatus -= 2**8
            self.failUnless(exitStatus == expected)

    def test_ProcessProxy_0(self):
        p = process.ProcessProxy(['quiet'])
        retval = p.wait()
        self._assertRetvalIs(0, retval)

    def test_ProcessProxy_42(self):
        p = process.ProcessProxy(['quiet', '42'])
        retval = p.wait()
        self._assertRetvalIs(42, retval)

    def test_ProcessProxy_minus_42(self):
        p = process.ProcessProxy(['quiet', '-42'])
        retval = p.wait()
        self._assertRetvalIs(-42, retval)

    def test_ProcessOpen_0(self):
        p = process.ProcessOpen(['quiet'])
        retval = p.wait()
        self._assertRetvalIs(0, retval)

    def test_ProcessOpen_42(self):
        p = process.ProcessOpen(['quiet', '42'])
        retval = p.wait()
        self._assertRetvalIs(42, retval)

    def test_ProcessOpen_minus_42(self):
        p = process.ProcessOpen(['quiet', '-42'])
        retval = p.wait()
        self._assertRetvalIs(-42, retval)


def suite():
    """Return a unittest.TestSuite to be used by test.py."""
    return unittest.makeSuite(RetvalTestCase)

if __name__ == "__main__":
    import logging
    logging.basicConfig()
    testsupport.setup()
    sys.argv.insert(1, "-v") # always want verbose output
    unittest.main()

