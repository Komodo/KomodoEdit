"""Test simple Process.kill() usage."""

import os
import sys
import time
import pprint
import unittest
import threading

if not sys.platform.startswith("win"):
    import signal

import process


class KillTestCase(unittest.TestCase):
    def _KillAndReturn(self, child):
        try:
            child.kill()
        except OSError, ex:
            self._failedToKill = 1
        else:
            self._failedToKill = 0

    def test_ProcessProxy_kill(self):
        p = process.ProcessProxy(['hang'])
        time.sleep(2)
        p.kill()
        retval = p.wait()
        if not sys.platform.startswith("win"):
            # Can check on Unix if the retval indicates that the process
            # was signaled. Otherwise the test is just to ensure that we
            # got here (i.e. didn't hang).
            self.failUnless(os.WIFSIGNALED(retval))

    def test_ProcessProxy_kill_twice(self):
        # Killing an already terminated process should not raise an
        # exception.
        p = process.ProcessProxy(['hang'])
        time.sleep(2)
        p.kill()
        retval = p.wait()
        if not sys.platform.startswith("win"):
            # Can check on Unix if the retval indicates that the process
            # was signaled. Otherwise the test is just to ensure that we
            # got here (i.e. didn't hang).
            self.failUnless(os.WIFSIGNALED(retval))
        p.kill()

    if not sys.platform.startswith("win"):
        def test_ProcessProxy_kill_SIGKILL(self):
            p = process.ProcessProxy(['hang'])
            time.sleep(1)
            p.kill(sig=signal.SIGKILL)
            retval = p.wait()
            self.failUnless(os.WIFSIGNALED(retval))
            self.failUnless(os.WTERMSIG(retval) == signal.SIGKILL)

        # XXX Could add tests for other signals but would have to launch an
        #     app that would respond to those signals in a measurable way and
        #     then terminate.

    def test_ProcessProxy_kill_from_parent_subthread(self):
        p = process.ProcessProxy(['hang'])
        t = threading.Thread(target=self._KillAndReturn,
                             kwargs={'child':p})
        t.start()
        p.wait()
        t.join()
        if self._failedToKill:
            self.fail("Could not kill the child process from a thread "\
                      "spawned by the parent *after* the child was spawn.\n")

    def test_ProcessOpen_kill(self):
        p = process.ProcessOpen(['hang'])
        time.sleep(2)
        p.kill()
        retval = p.wait()
        if not sys.platform.startswith("win"):
            # Can check on Unix if the retval indicates that the process
            # was signaled. Otherwise the test is just to ensure that we
            # got here (i.e. didn't hang).
            self.failUnless(os.WIFSIGNALED(retval))

    def test_ProcessOpen_kill_twice(self):
        # Killing an already terminated process should not raise an
        # exception.
        p = process.ProcessOpen(['hang'])
        time.sleep(2)
        p.kill()
        retval = p.wait()
        if not sys.platform.startswith("win"):
            # Can check on Unix if the retval indicates that the process
            # was signaled. Otherwise the test is just to ensure that we
            # got here (i.e. didn't hang).
            self.failUnless(os.WIFSIGNALED(retval))
        p.kill()

    if not sys.platform.startswith("win"):
        def test_ProcessOpen_kill_SIGKILL(self):
            p = process.ProcessOpen(['hang'])
            time.sleep(1)
            p.kill(sig=signal.SIGKILL)
            retval = p.wait()
            self.failUnless(os.WIFSIGNALED(retval))
            self.failUnless(os.WTERMSIG(retval) == signal.SIGKILL)

        # XXX Could add tests for other signals but would have to launch an
        #     app that would respond to those signals in a measurable way and
        #     then terminate.

    def test_ProcessOpen_kill_from_parent_subthread(self):
        p = process.ProcessOpen(['hang'])
        t = threading.Thread(target=self._KillAndReturn,
                             kwargs={'child':p})
        t.start()
        p.wait()
        t.join()
        if self._failedToKill:
            self.fail("Could not kill the child process from a thread "\
                      "spawned by the parent *after* the child was spawn.\n")



def suite():
    """Return a unittest.TestSuite to be used by test.py."""
    return unittest.makeSuite(KillTestCase)

if __name__ == "__main__":
    import logging
    logging.basicConfig()
    testsupport.setup()
    sys.argv.insert(1, "-v") # always want verbose output
    unittest.main()

