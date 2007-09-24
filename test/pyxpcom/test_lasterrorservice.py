# Copyright (c) 2000-2007 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

"""Test the koILastErrorService."""

import sys
import threading
import time
import unittest

try:
    from xpcom import components
except ImportError:
    pass # Allow testing without PyXPCOM to proceed.


class LastErrorTestCase(unittest.TestCase):
    def test_no_last_error_set(self):
        # Create a new thread for which we are sure there is no last
        # error and ensure that the last error is (0, '').
        t = GetLastErrorThread(name='test_no_last_error_set')
        t.start()
        t.join()
        self.failUnless(t.lastError == (0, ''))

    def test_set_and_get_error(self):
        lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"]\
                       .getService(components.interfaces.koILastErrorService)
        lastErrorSvc.setLastError(42, "test_set_and_get_error")
        self.failUnless(lastErrorSvc.getLastError() ==\
                        (42, "test_set_and_get_error"))
        self.failUnless(lastErrorSvc.getLastErrorCode() == 42)
        self.failUnless(lastErrorSvc.getLastErrorMessage() ==\
                        "test_set_and_get_error")

    def test_multiple_threads_do_not_conflict(self):
        t1cond = threading.Condition()
        t1 = SetWaitGet('test_multiple_threads_do_not_conflict_1', t1cond)
        t2cond = threading.Condition()
        t2 = SetWaitGet('test_multiple_threads_do_not_conflict_2', t2cond)
        
        # Start t1 and wait until it has .setLastError(). (XXX Should
        # really use a condition for this.)
        t1.start()
        time.sleep(1)

        # Start t2 and let is set and get its last error.
        t2.start()
        while t2.isAlive():
            t2cond.acquire()
            t2cond.notify()
            t2cond.release()
            t2.join(1)

        # Now let t1 complete and ensure that its .getLastError() has
        # not been stomped by t2's use of .setLastError().
        while t1.isAlive():
            t1cond.acquire()
            t1cond.notify()
            t1cond.release()
            t1.join(1)
        self.failUnless(t1.lastError == (0, t1.getName()))

    # XXX Should really test that koILastErrorService works with alien
    #     threads. Currently we are presuming that "alien" threads (i.e.
    #     those threads that were not created via the Python threading
    #     module) return a unique value for .getName(). If so then all
    #     is well, if not then koILastErrorService has a subtle bug.
    #     We could test this with an nsIThread (punt), or a perhaps a
    #     thread created via PyWin32 (there is only a binding for the
    #     weird MFC CWinThread, not thw Win32 API CreateThread call,
    #     punt) or a C extension using native C API calls (punt).
    #def test_alien_thread(self):

#---- internal support stuff

class GetLastErrorThread(threading.Thread):
    def run(self):
        lastErrorSvc =\
            components.classes["@activestate.com/koLastErrorService;1"]\
                      .getService(components.interfaces.koILastErrorService)
        self.lastError = lastErrorSvc.getLastError()

class SetWaitGet(threading.Thread):
    def __init__(self, name, cond):
        threading.Thread.__init__(self, name=name)
        self.cond = cond
    def run(self):
        lastErrorSvc =\
            components.classes["@activestate.com/koLastErrorService;1"]\
                      .getService(components.interfaces.koILastErrorService)
        lastErrorSvc.setLastError(0, self.getName())
        self.cond.acquire()
        self.cond.wait()
        self.cond.release()
        self.lastError = lastErrorSvc.getLastError()

