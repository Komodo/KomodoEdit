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

"""Test simple Process.kill() usage."""

import os
import sys
import time
import pprint
import threading
import unittest

import process


class WaitTestCase(unittest.TestCase):
    def _WaitAndReturn(self, child):
        self._hitLinuxThreadsBug = 0
        try:
            child.wait()
        except OSError, ex:
            self._hitLinuxThreadsBug = 1
        else:
            self._hitLinuxThreadsBug = 0

    def test_ProcessProxy_wait(self):
        before = time.time()
        p = process.ProcessProxy(['talk'])
        p.wait()
        after = time.time()
        self.failUnless(4.0 < (after-before) < 10.0)

    def test_ProcessProxy_wait_from_parent_subthread(self):
        before = time.time()
        p = process.ProcessProxy(['talk'])
        try:
            t = threading.Thread(target=self._WaitAndReturn,
                                 kwargs={'child':p})
            t.start()
            t.join()
            after = time.time()
            if self._hitLinuxThreadsBug:
                self.fail("Hit known bug in Linux threads: cannot wait "\
                          "on a process from a different thread from "\
                          "which it was spawned.")
            self.failUnless(4.0 < (after-before) < 10.0)
        finally:
            p.kill()

    def test_ProcessOpen_wait(self):
        before = time.time()
        p = process.ProcessOpen(['talk'])
        p.wait()
        after = time.time()
        self.failUnless(4.0 < (after-before) < 10.0)

    def test_ProcessOpen_wait_from_parent_subthread(self):
        before = time.time()
        p = process.ProcessOpen(['talk'])
        try:
            t = threading.Thread(target=self._WaitAndReturn,
                                 kwargs={'child':p})
            t.start()
            t.join()
            after = time.time()
            if self._hitLinuxThreadsBug:
                self.fail("Hit known bug in Linux threads: cannot wait "\
                          "on a process from a different thread from "\
                          "which it was spawned.")
            self.failUnless(4.0 < (after-before) < 10.0)
        finally:
            p.kill()

    def test_Process_wait_multiple_times(self):
        p = process.Process(['log', 'hi'])
        rv1 = p.wait()
        rv2 = p.wait()
        self.failUnless(rv1 == rv2)

    def test_ProcessProxy_wait_multiple_times(self):
        p = process.ProcessProxy(['log', 'hi'])
        rv1 = p.wait()
        rv2 = p.wait()
        self.failUnless(rv1 == rv2)

    def test_ProcessOpen_wait_multiple_times(self):
        p = process.ProcessOpen(['log', 'hi'])
        rv1 = p.wait()
        rv2 = p.wait()
        self.failUnless(rv1 == rv2)
        


def suite():
    """Return a unittest.TestSuite to be used by test.py."""
    return unittest.makeSuite(WaitTestCase)

if __name__ == "__main__":
    import logging
    logging.basicConfig()
    testsupport.setup()
    sys.argv.insert(1, "-v") # always want verbose output
    unittest.main()

