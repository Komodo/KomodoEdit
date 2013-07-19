import logging
import unittest
import sys
import time

from xpcom.components import classes as Cc, interfaces as Ci
from xpcom import nsError as Cr
from collections import namedtuple

log = logging.getLogger("test.codeintel.xpcom")

class _CodeIntelTestCaseBase(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        unittest.TestCase.__init__(self, *args, **kwargs)
        #self.log = log.getChild(self.__class__.__name__)

    @classmethod
    def setUpClass(cls):
        """Start the codeintel service once to make sure the database is ready
        """
        svc = Cc["@activestate.com/koCodeIntelService;1"].getService()
        tm = Cc["@mozilla.org/thread-manager;1"].getService(Ci.nsIThreadManager)
        start = time.time()
        ready = set()
        callback = lambda status, data: ready.add(True)
        sys.stdout.write(".")
        log.debug("[starting codeintel...]")
        svc.activate(callback, True)
        while not ready:
            tm.currentThread.processNextEvent(True)
        sys.stdout.write(".")
        log.debug("[codeintel started, stopping...]")
        svc.deactivate()
        while svc.isBackEndActive:
            tm.currentThread.processNextEvent(True)
        sys.stdout.write(".")
        log.debug("[codeintel stopped]")

    def setUp(self):
        # Start up the service
        self.svc = Cc["@activestate.com/koCodeIntelService;1"].getService()
        # Note that the service might be set up already! (when running multiple
        # tests; deactivate currently doesn't have a callback)
        self._waiting_for_activation = True
        self._active = False
        self.svc.activate(self._activate_callback, True)
        # Let codeintel start up...
        self._wait_for_callback(lambda: not self._waiting_for_activation,
                                timeout=60, action="startup")
        self.assertTrue(self._active)

    def _wait_for_callback(self, callback, timeout=None, action=""):
        """Wait for some callback to occur
        @param callback {Function} Something that should return true when ready
        @param timeout {int} Timeout in seconds
        @param action {str} Description for what to wait for (for the timeout)
        """
        tm = Cc["@mozilla.org/thread-manager;1"].getService(Ci.nsIThreadManager)
        start = time.time()
        while not callback():
            if timeout is not None:
                self.assertLess(time.time(), start + timeout,
                                "Timed out waiting: " + action)
            tm.currentThread.processNextEvent(True)

    def _activate_callback(self, status, data):
        self._active = Cr.NS_SUCCEEDED(status)
        self._waiting_for_activation = False

    def tearDown(self):
        self.svc.deactivate()
        self.svc = None

class _BufferTestCaseBase(_CodeIntelTestCaseBase):
    language = None
    trg = None
    def setUp(self):
        _CodeIntelTestCaseBase.setUp(self)
        # get a document to work with
        self.doc = Cc["@activestate.com/koDocumentBase;1"].createInstance()
        self.doc.initUntitled("<Untitled>", "UTF-8")
        if self.language:
            self.doc.language = self.language
        self.buf = self.svc.buf_from_koIDocument(self.doc)

    def tearDown(self):
        self.doc = None
        self.buf = None
        _CodeIntelTestCaseBase.tearDown(self)

class AsyncSpinner(object):
    def __init__(self, testcase, timeout=10, callback=None):
        self.testcase = testcase
        self.timeout = timeout
        self.callback = callback
    def __enter__(self):
        self._done = False
    def __exit__(self, *args):
        if any(args):
            return # Exception was raised
        tm = Cc["@mozilla.org/thread-manager;1"].getService(Ci.nsIThreadManager)
        t = tm.currentThread
        start = time.time()
        while not self._done:
            if self.timeout is not None:
                self.testcase.assertLess(time.time(), start + self.timeout,
                                         "Timed out waiting")
            time.sleep(0.1) # Rest a bit, let other things happen
            while t.hasPendingEvents():
                t.processNextEvent(True)
    def __call__(self, *args, **kwargs):
        log.debug("callback! %r %r %r", self.callback, args, kwargs)
        if self.callback:
            self.callback(*args, **kwargs)
        self._done = True

class UIHandler(object):
    _com_interfaces_ = [ Ci.koICodeIntelCompletionUIHandler ]
    _done = False
    AutoCompleteInfo = namedtuple("AutoCompleteInfo", "completion type")
    def __init__(self, callback=None):
        self.callback = callback

    def setAutoCompleteInfo(self, completions, types, trg):
        log.debug("setAutoCompleteInfo")
        self.completions = [UIHandler.AutoCompleteInfo(completion, type_)
                            for completion, type_ in zip(completions, types)]

    def setCallTipInfo(self, calltip, trg, explicit):
        log.debug("setCallTipInfo")
        self.calltip = calltip
        self.explicit = explicit

    def setDefinitionsInfo(self, defns, trg):
        log.debug("setDefinitionsInfo")
        self.defns = defns

    def setStatusMessage(self, msg, highlight):
        log.debug("setStatusMessage")
        self.msg = msg

    def updateCallTip(self):
        log.debug("updateCallTip")
        pass

    def triggerPrecedingCompletion(self, path):
        log.debug("triggerPrecedingCompletion")
        pass

    def done(self):
        log.debug("UIHandler: done")
        self._done = True
        if self.callback:
            self.callback()
