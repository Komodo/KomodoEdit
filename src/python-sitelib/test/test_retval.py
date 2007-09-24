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

