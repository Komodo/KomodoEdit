import inspect
import logging
import uuid
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

    svc = None
    __has_codeintel_db_been_setup = False

    @classmethod
    def setUpClass(cls):
        """Start the codeintel service once to make sure the database is ready
        """
        if _CodeIntelTestCaseBase.__has_codeintel_db_been_setup:
            return
        sys.stdout.write("Setting up codeintel database...\n")
        _CodeIntelTestCaseBase.svc = svc = Cc["@activestate.com/koCodeIntelService;1"].getService()
        tm = Cc["@mozilla.org/thread-manager;1"].getService(Ci.nsIThreadManager)
        start = time.time()
        ready = set()
        callback = lambda status, data: ready.add(True)
        svc.addActivateCallback(callback)
        svc.activate(True)
        while not ready:
            tm.currentThread.processNextEvent(True)
        svc.removeActivateCallback(callback)
        sys.stdout.write("Codeintel database initialization completed\n")
        _CodeIntelTestCaseBase.__has_codeintel_db_been_setup = True

    def run(self, result=None):
        try:
            log.debug("Running test %s...", self._testMethodName)
        except AttributeError:
            pass
        return super(_CodeIntelTestCaseBase, self).run(result=result)


class _BufferTestCaseBase(_CodeIntelTestCaseBase):
    language = None
    trg = None
    def setUp(self):
        _CodeIntelTestCaseBase.setUp(self)
        # get a document to work with
        self.doc = Cc["@activestate.com/koDocumentBase;1"].createInstance()
        self.doc.initUntitled("<Untitled-%s>" % (uuid.uuid1(),), "UTF-8")
        if self.language:
            self.doc.language = self.language
        self.buf = self.svc.buf_from_koIDocument(self.doc)

    def tearDown(self):
        self.doc = None
        self.buf = None
        _CodeIntelTestCaseBase.tearDown(self)

class AsyncSpinner(object):
    def __init__(self, testcase, timeout=30, callback=None):
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
                now = time.time()
                self.testcase.assertLess(now, start + self.timeout,
                                         ("Timed out waiting in %s::%s "
                                          "(%s seconds elapsed)") %
                                         (self.testcase, self.callback,
                                          now - start))
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

    completions = []
    calltip = ""
    defns = []
    msg = ""

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
