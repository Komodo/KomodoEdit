# Copyright (c) 2000-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

import os
import unittest
import sys

from xpcom import components, COMException



class TestKoDocumentService(unittest.TestCase):
    def __init__(self, methodName):
        unittest.TestCase.__init__(self, methodName)
        
        self.__docsvc = components.classes["@activestate.com/koDocumentService;1"] \
                        .getService(components.interfaces.koIDocumentService)
        self.__filesvc = components.classes["@activestate.com/koFileService;1"] \
                         .getService(components.interfaces.koIFileService)

        # Grab a reference to the global preference service.  this
        # forces prefs to startup
        _globalPrefsvc = components.classes["@activestate.com/koPrefService;1"].\
                         getService(components.interfaces.koIPrefService)

    def __del__(self):
        self.__docsvc.unload();

    def test_createDocumentFromURI(self):
        filename = os.__file__ # returns os.pyc
        doc = self.__docsvc.createDocumentFromURI(filename)
        doc.addReference()
        assert doc.file.exists
        docs = self.__docsvc.getAllDocuments()
        assert doc in docs
        xdoc = self.__docsvc.findDocumentByURI(doc.file.URI)
        assert doc == xdoc
        doc.releaseReference()
        docs = self.__docsvc.getAllDocuments()
        assert len(docs) == 0

    def test_createDocumentFromFile(self):
        filename = os.__file__ # returns os.pyc
        file = self.__filesvc.getFileFromURI(filename)
        doc = self.__docsvc.createDocumentFromFile(file)
        doc.addReference()
        assert doc.file.exists
        docs = self.__docsvc.getAllDocuments()
        assert doc in docs
        xdoc = self.__docsvc.findDocumentByURI(doc.file.URI)
        assert doc == xdoc
        doc.releaseReference()
        docs = self.__docsvc.getAllDocuments()
        assert len(docs) == 0

    def test_createUntitledDocument(self):
        doc = self.__docsvc.createUntitledDocument('Python')
        doc.addReference()
        assert doc.baseName == 'Python-1.py', "%s != %s" % (doc.baseName, 'Python-1.py')
        docs = self.__docsvc.getAllDocuments()
        assert doc in docs
        xdoc = self.__docsvc.findDocumentByURI('Python-1.py')
        assert doc == xdoc
        doc.releaseReference()
        docs = self.__docsvc.getAllDocuments()
        assert len(docs) == 0

#---- mainline

def suite():
    return unittest.makeSuite(TestKoDocumentService)

def test_main():
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite())

if __name__ == "__main__":
    test_main()




