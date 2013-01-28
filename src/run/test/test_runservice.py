# Copyright (c) 2013 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

import time
import unittest
import threading

from xpcom import components

class _CallbackHandler:
    _com_interfaces_ = [components.interfaces.koIRunAsyncCallback]

    def __init__(self, event):
        self.event = event
        self.returncode = None
        self.stdout = None
        self.stderr = None
        self.command = None
        self.threadname = None

    def callback(self, command, returncode, stdout, stderr):
        self.command = command
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.threadname = threading.currentThread().name
        # Notify waiting thread.
        self.event.set()

class TestKoRunService(unittest.TestCase):
    def _wait(self, event, timeout=None):
        # Process pending Mozilla events in order to receive the observer
        # notifications, based on Mozilla xpcshell test class here:
        # http://mxr.mozilla.org/mozilla-central/source/testing/xpcshell/head.js#75
        currentThread = components.classes["@mozilla.org/thread-manager;1"] \
                            .getService().currentThread
        start_time = time.time()
        while 1:
            if timeout is not None:
                if (time.time() - start_time) > timeout:
                    break
            # Give some time to gather more events.
            if event.wait(0.25):
                break
            # Process events, such as the pending observer notifications.
            while currentThread.hasPendingEvents():
                currentThread.processNextEvent(True)

    def test_runasync(self):
        runSvc = components.classes["@activestate.com/koRunService;1"]\
                 .getService(components.interfaces.koIRunService)
        # With all default options the encoded command should just be
        # the command string.
        command = 'echo hi'
        event = threading.Event()
        callbackHandler = _CallbackHandler(event)
        runSvc.RunAsync(command, callbackHandler)
        self._wait(event, 10)  # Timeout after 10 seconds of waiting.
        self.assertNotEqual(callbackHandler.returncode, None,
                            "no callback received for command %r" % (command))
        self.assertIn("hi", callbackHandler.stdout)
        self.assertEqual("", callbackHandler.stderr)
        self.assertEqual(threading.currentThread().name, callbackHandler.threadname)

    def _threaded_runasync(self, callbackHandler):
        callbackHandler.original_threadname = threading.currentThread().name
        runSvc = components.classes["@activestate.com/koRunService;1"]\
                 .getService(components.interfaces.koIRunService)
        # With all default options the encoded command should just be
        # the command string.
        command = 'echo hi'
        runSvc.RunAsync(command, callbackHandler)
        self._wait(callbackHandler.event, 10)  # Timeout after 10 seconds of waiting.
    def test_runasync_different_thread(self):
        event = threading.Event()
        callbackHandler = _CallbackHandler(event)
        t = threading.Thread(target=self._threaded_runasync,
                             args=(callbackHandler, ))
        t.setDaemon(True)
        t.start()
        t.join(15)
        self.assertNotEqual(callbackHandler.returncode, None,
                            "no callback received for command %r" %
                            (callbackHandler.command))
        self.assertIn("hi", callbackHandler.stdout)
        self.assertEqual("", callbackHandler.stderr)
        self.assertEqual(callbackHandler.original_threadname, callbackHandler.threadname)
