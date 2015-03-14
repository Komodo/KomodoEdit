# -*- coding: utf-8 -*-

import os
import sys
import time
import unittest
import tempfile
import threading

from xpcom import components, COMException
from xpcom.server import WrapObject, UnwrapObject

from zope.cachedescriptors.property import LazyClassAttribute

from testlib import tag

Cc = components.classes
Ci = components.interfaces

class Encodings(unittest.TestCase):
    _com_interfaces_ = [Ci.nsIObserver,
                        Ci.koILintBuffer]

    def __init__(self, methodName):
        unittest.TestCase.__init__(self, methodName)

    @LazyClassAttribute
    def jsLinter(self):
        return Cc["@activestate.com/koLinter?language=JavaScript;1"].getService(Ci.koILinter)

    @LazyClassAttribute
    def docSvc(self):
        return Cc["@activestate.com/koDocumentService;1"].getService(Ci.koIDocumentService)

    @tag("bug105635")
    def test_latin1(self):
        file_contents = u"(; // ß"
        fd, path = tempfile.mkstemp(suffix=".js")
        try:
            os.write(fd, file_contents.encode("latin-1"))
            os.close(fd)
            # Create the koDoc
            koDoc = self.docSvc.createDocumentFromURI(path)
            koDoc.load()
            if koDoc.language != "JavaScript":
                koDoc.language = "JavaScript"
            self.assertEqual(koDoc.encoding.short_encoding_name, "Latin-1")
            # Create the koILintRequest
            request = Cc["@activestate.com/koLintRequest;1"].createInstance(Ci.koILintRequest)
            request.koDoc = koDoc
            request.encoding = koDoc.encoding
            request.content = file_contents
            request.cwd = os.path.dirname(path)
            # Do the linting (synchronously).
            results = self.jsLinter.lint(request)
            self.assertEqual(results.getNumErrors(), 1, "Should have been one warning")
            entries = results.getResults()
            self.assertEqual(len(entries), 1, "Should have been one entry")
            result = entries[0]
            self.assertEqual(result.severity, Ci.koILintResult.SEV_ERROR, "Excepting error severity")
            self.assertEqual(result.description, "SyntaxError:  expected expression, got ';': (on column 1)")
        finally:
            os.remove(path)
