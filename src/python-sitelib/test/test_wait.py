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

