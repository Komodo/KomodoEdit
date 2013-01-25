# Copyright (c) 2013 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

import unittest
import threading

from xpcom import components

class _CallbackHandler:
    _com_interfaces_ = [components.interfaces.koIRunAsyncCallback]

    def __init__(self, condition):
        self.condition = condition
        self.returncode = None
        self.stdout = None
        self.stderr = None
        self.command = None

    def callback(self, command, returncode, stdout, stderr):
        self.command = command
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        # Notify waiting threaed.
        self.condition.acquire()
        self.condition.notifyAll()
        self.condition.release()

class TestKoRunService(unittest.TestCase):
    def test_runasync(self):
        runSvc = components.classes["@activestate.com/koRunService;1"]\
                 .getService(components.interfaces.koIRunService)
        # With all default options the encoded command should just be
        # the command string.
        command = 'echo hi'
        condition = threading.Condition()
        callbackHandler = _CallbackHandler(condition)
        runSvc.RunAsync(command, callbackHandler)
        condition.acquire()
        condition.wait(10)  # Timeout after 10 seconds of waiting.
        condition.release()
        self.assertNotEqual(callbackHandler.returncode, None,
                            "no callback received for command %r" % (command))
        self.assertIn("hi", callbackHandler.stdout)
        self.assertEqual("", callbackHandler.stderr)
