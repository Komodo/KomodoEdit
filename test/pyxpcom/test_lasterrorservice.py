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

