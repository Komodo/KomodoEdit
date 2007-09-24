# Copyright (c) 2000-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

import os
import unittest
import sys, md5
import tempfile

from xpcom import components, COMException



class TestKoFileEx(unittest.TestCase):
    def __init__(self, methodName):
        unittest.TestCase.__init__(self, methodName)
        initSvc = components.classes["@activestate.com/koInitService;1"] \
                      .getService(components.interfaces.koIInitService)
        initSvc.setEncoding()
        
        self.__file = components.classes["@activestate.com/koFileEx;1"] \
                      .createInstance(components.interfaces.koIFileEx)

    def failUnlessSamePath(self, p1, p2, errmsg = None):
        p1 = p1.replace('\\','/')
        p2 = p2.replace('\\','/')
        self.failUnlessEqual(p1, p2, errmsg)

    def test_assignFileURI(self):
        url = "file:///c:/test/path/to/somefile.txt"
        path = r'c:\test\path\to\somefile.txt'
        dirname = os.path.dirname(path.replace('\\','/'))
        self.__file.URI = url
        assert self.__file.leafName == 'somefile.txt'
        assert self.__file.baseName == 'somefile.txt'
        self.failUnlessSamePath(self.__file.URI, url,
                           "%r != %r" %(self.__file.URI, url))
        self.failUnlessSamePath(self.__file.path, path,
                           "%r != %r" %(self.__file.path, path))
        self.failUnlessSamePath(self.__file.dirName, dirname,
                           "%r != %r" %(self.__file.dirName, dirname))

    def test_assignFileURIToPath(self):
        url = "file:///C:/Program%20Files/Microsoft%20Visual%20Studio/VC98/Include/WINUSER.H"
        path = r'C:\Program Files\Microsoft Visual Studio\VC98\Include\WINUSER.H'
        dirname = os.path.dirname(path.replace('\\','/'))
        self.__file.path = url
        assert self.__file.leafName == 'WINUSER.H'
        assert self.__file.baseName == 'WINUSER.H'
        self.failUnlessSamePath(self.__file.URI, url,
                           "%r != %r" %(self.__file.URI, url))
        self.failUnlessSamePath(self.__file.path, path,
                           "%r != %r" %(self.__file.path, path))
        self.failUnlessSamePath(self.__file.dirName, dirname,
                           "%r != %r" %(self.__file.dirName, dirname))
        
    def test_assignFilePathToURI(self):
        path = r'c:\test\path\to\somefile.txt'
        self.__file.URI = path
        self.failUnlessSamePath(self.__file.URI, 'file:///c:/test/path/to/somefile.txt',
                           "%r != %r" %(self.__file.URI, 'file:///c:/test/path/to/somefile.txt'))
        self.failUnlessSamePath(self.__file.path, path,
                           "%r != %r" %(self.__file.path, path))
        assert self.__file.leafName == 'somefile.txt'
        assert self.__file.baseName == 'somefile.txt'
        self.failUnlessSamePath(self.__file.dirName, r'c:\test\path\to',
                           "%r != %r" %(self.__file.dirName, r'c:\test\path\to'))
        
    def test_assignFilePath(self):
        path = r'c:\test\path\to\somefile.txt'
        self.__file.path = path
        self.failUnlessSamePath(self.__file.URI, 'file:///c:/test/path/to/somefile.txt',
                           "%r != %r" %(self.__file.URI, 'file:///c:/test/path/to/somefile.txt'))
        self.failUnlessSamePath(self.__file.path, path,
                           "%r != %r" %(self.__file.path, path))
        assert self.__file.leafName == 'somefile.txt'
        assert self.__file.baseName == 'somefile.txt'
        self.failUnlessSamePath(self.__file.dirName, r'c:\test\path\to',
                           "%r != %r" %(self.__file.dirName, r'c:\test\path\to'))

    def test_rootIsDir(self):
        d = os.path.normpath(os.path.abspath(os.path.dirname(__file__)))
        if sys.platform.startswith("win"):
            uri = "file:///" + d.replace("\\", "/")
        else:
            uri = "file://" + d
        self.__file.URI = uri
        assert self.__file.exists
        assert self.__file.isDirectory
        assert not self.__file.isFile
        assert not self.__file.isSymlink
        assert not self.__file.isSpecial
        assert self.__file.isReadable
        assert self.__file.isWriteable

    def test_tempIsDir(self):
        self.__file.path = tempfile.gettempdir()
        assert self.__file.exists
        assert self.__file.isDirectory
        assert not self.__file.isFile
        assert not self.__file.isSymlink
        assert not self.__file.isSpecial
        assert self.__file.isReadable
        assert self.__file.isWriteable

    def test_readFile(self):
        filename = os.__file__ # returns os.pyc
        self.__file.path = os.path.dirname(filename)+'/os.py'
        assert self.__file.exists
        assert not self.__file.isDirectory
        assert self.__file.isFile
        assert not self.__file.isSymlink
        assert not self.__file.isSpecial
        assert self.__file.isReadable
        assert self.__file.isWriteable
        self.__file.open('rb')
        x = self.__file.read(-1)
        assert len(x) > 0 and len(x)==self.__file.fileSize
        self.__file.close()

    def test_writeFile(self):
        filename = tempfile.mktemp()
        try:
            text = "This is a test!"
            self.__file.URI = filename
            self.__file.open('w');
            self.__file.write(text)
            self.__file.close()
            assert self.__file.exists
            assert not self.__file.isDirectory
            assert self.__file.isFile
            assert not self.__file.isSymlink
            assert not self.__file.isSpecial
            assert self.__file.isReadable
            assert self.__file.isWriteable
            self.__file.URI = filename
            self.__file.open('r')
            assert self.__file.read(-1) == text
            self.__file.close()
        finally:
            if os.path.isfile(filename):
                os.remove(filename) # clean up
                assert self.__file.hasChanged
                assert not self.__file.exists
        
    def test_stat(self):
        filename = os.__file__ # returns os.pyc
        self.__file.path = os.path.dirname(filename)+'/os.py'
        assert self.__file.lastModifiedTime != 0

    def test_path(self):
        url = 'file:///c:/test/path/to/somefile.txt'
        path = r'c:\test\path\to\somefile.txt'
        dirname = os.path.dirname(path.replace('\\','/'))
        self.__file.URI = url
        self.failUnlessSamePath(self.__file.URI, url,
                           "%r != %r" %(self.__file.URI, url))
        self.failUnlessSamePath(self.__file.path, path,
                           "%r != %r" %(self.__file.path, path))
        self.failUnlessSamePath(self.__file.dirName, dirname,
                           "%r != %r" %(self.__file.dirName, dirname))

        url = 'http://someserver.com/test/path/to/somefile.txt'
        path = r'\test\path\to\somefile.txt'
        dirname = os.path.dirname(path.replace('\\','/'))
        self.__file.URI = url
        self.failUnlessSamePath(self.__file.URI, url,
                           "%r != %r" %(self.__file.URI, url))
        self.failUnlessSamePath(self.__file.path, path,
                           "%r != %r" %(self.__file.path, path))
        self.failUnlessSamePath(self.__file.dirName, dirname,
                           "%r != %r" %(self.__file.dirName, dirname))

        url = 'file:///c:/path%20with%20spaces/path/to/somefile.txt'
        path = r'c:\path with spaces\path\to\somefile.txt'
        dirname = os.path.dirname(path.replace('\\','/'))
        self.__file.URI = url
        self.failUnlessSamePath(self.__file.URI, url,
                           "%r != %r" %(self.__file.URI, url))
        self.failUnlessSamePath(self.__file.path, path,
                           "%r != %r" %(self.__file.path, path))
        self.failUnlessSamePath(self.__file.dirName, dirname,
                           "%r != %r" %(self.__file.dirName, dirname))

        # we can set a URI to a file, and get the right thing
        self.__file.URI = path
        self.failUnlessSamePath(self.__file.URI, url,
                           "%r != %r" %(self.__file.URI, url))
        self.failUnlessSamePath(self.__file.path, path,
                           "%r != %r" %(self.__file.path, path))
        self.failUnlessSamePath(self.__file.dirName, dirname,
                           "%r != %r" %(self.__file.dirName, dirname))
 
    def test_fileNotExist(self):
        self.__file.URI = "Text-1.txt"
        assert not self.__file.exists

    def test_md5name(self):
        filename = os.path.normpath(os.path.join(tempfile.gettempdir(),'testwrite.py.txt'))
        self.__file.path = filename
        assert self.__file.md5name == md5.new(self.__file.URI).hexdigest()

#---- mainline

def suite():
    return unittest.makeSuite(TestKoFileEx)

def test_main():
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite())

if __name__ == "__main__":
    __file__ = os.path.abspath(sys.argv[0]) # won't be necessary in Python 2.3
    test_main()



