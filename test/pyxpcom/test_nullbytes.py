# Copyright (c) 2000-2009 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

import os
import sys
import unittest

try:
    from xpcom import components
except ImportError:
    pass # Allow testing without PyXPCOM to proceed.


# Test Komodo's handling of null bytes in various services.

class NullBytesTestCase(unittest.TestCase):

    uni_string = u"This code contains a \0 null byte"
    enc_string = uni_string.decode("utf8")

    def test_document(self):
        doc = components.classes['@activestate.com/koDocumentBase;1'].\
                         getService(components.interfaces.koIDocument)
        doc.initUntitled("test_null_bytes", "utf8")
        doc.buffer = self.uni_string
        self.failUnlessEqual(doc.buffer, self.uni_string)
        self.failUnlessEqual(doc.bufferLength, len(self.uni_string))
        doc.setBufferAndEncoding(self.uni_string, "utf8")
        self.failUnlessEqual(doc.buffer, self.uni_string)
        self.failUnlessEqual(doc.bufferLength, len(self.uni_string))

    def test_sysutils_bytelength(self):
        sysUtils = components.classes['@activestate.com/koSysUtils;1'].\
                         getService(components.interfaces.koISysUtils)
        bytelen = sysUtils.byteLength(self.uni_string)
        self.failUnlessEqual(bytelen, len(self.enc_string),
                             "Null bytes were not handled correctly")

    def test_encoding_service(self):
        encodingSvc = components.classes['@activestate.com/koEncodingServices;1'].\
                         getService(components.interfaces.koIEncodingServices)
        text = encodingSvc.encode(self.uni_string, "utf8", "replace")
        self.failUnlessEqual(len(text), len(self.enc_string),
                             "Null bytes were not correctly decoded")
        text = encodingSvc.unicode(self.enc_string, "utf8", "replace")
        self.failUnlessEqual(len(text), len(self.uni_string),
                             "Null bytes were not correctly encoded")
        text, encoding_name, bom = encodingSvc.getUnicodeEncodedString(self.enc_string)
        self.failUnlessEqual(len(text), len(self.uni_string),
                             "Null bytes were not correctly decoded, text: %r" % (text, ))

    def test_find(self):
        findSvc = components.classes['@activestate.com/koFindService;1'].\
                         getService(components.interfaces.koIFindService)
        findResult = findSvc.find("file:///dummy_url",
                                  self.uni_string,
                                  u"byte",
                                  0,
                                  len(self.uni_string))
        self.failUnless(findResult is not None, "Text was not found")
        self.failUnlessEqual(findResult.start, self.uni_string.find("byte"),
                             "Text found at the wrong position")

