# Copyright (c) 2000-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.


import os
import unittest
import sys

from xpcom import components, COMException



class TestKoFileService(unittest.TestCase):
    def __init__(self, methodName):
        unittest.TestCase.__init__(self, methodName)
        self.__filesvc = components.classes["@activestate.com/koFileService;1"] \
                         .getService(components.interfaces.koIFileService)

    def test_service(self):
        filename = os.__file__ # returns os.pyc
        file = self.__filesvc.getFileFromURI(filename)
        assert file.exists
        files = self.__filesvc.getAllFiles()
        assert file in files
        xfile = self.__filesvc.findFileByURI(file.URI)
        assert file == xfile

    def test_weakRefFile(self):
        filename = os.__file__ # returns os.pyc
        file = self.__filesvc.getFileFromURI(filename)
        assert file.exists
        files = self.__filesvc.getAllFiles()
        assert file in files
        xfile = self.__filesvc.findFileByURI(file.URI)
        assert file == xfile
        file = xfile = files = None
        files = self.__filesvc.getAllFiles()
        assert len(files)==0
        
    def test_filesInPath(self):
        import xpcom
        myfiles = []
        myfiles.append(self.__filesvc.getFileFromURI(os.__file__))
        myfiles.append(self.__filesvc.getFileFromURI(unittest.__file__))
        file = self.__filesvc.getFileFromURI(xpcom.__file__)
        files = self.__filesvc.getFilesInBaseURI(os.path.dirname(myfiles[0].URI))
        for f in myfiles:
            assert f in files
        
    def test_fileNotExist(self):
        file = self.__filesvc.getFileFromURI(r"c:\If-You-Have-This-File-U-R-Lame-Text-1.txt")
        assert file.path == r"c:\If-You-Have-This-File-U-R-Lame-Text-1.txt"
        assert not file.exists

    def test_makeTempName(self):
        filename = self.__filesvc.makeTempName(".txt")
        assert 1
        
    def test_makeTempFile(self):
        file = self.__filesvc.makeTempFile(".txt",'w+')
        assert file.exists

    def test_makeTempFileInDir(self):
        file = self.__filesvc.makeTempFileInDir(os.getcwd(),".txt",'w+')
        assert file.exists
        self.__filesvc.deleteAllTempFiles()
        files = self.__filesvc.getFilesInBaseURI(os.getcwd())
        assert not files
        
        
#---- mainline

def suite():
    return unittest.makeSuite(TestKoFileService)

def test_main():
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite())

if __name__ == "__main__":
    test_main()



