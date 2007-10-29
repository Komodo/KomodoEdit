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

