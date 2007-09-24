# Copyright (c) 2000-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

import sys, md5
import unittest
import tempfile

from URIlib import *
win32 = sys.platform.startswith("win")

class TestURIParser(unittest.TestCase):
    filelist = []
    urllist = []
    # uri, path, leafName, baseName, dirName
    filelist.append(["about:blank",
                     'about:blank', 'about:blank',
                     'about:blank', ''])
    filelist.append(["file:///test/path/to/some:file.txt",
                     '/test/path/to/some:file.txt', 'some:file.txt',
                     'some:file.txt', '/test/path/to'])
    filelist.append(["file:///test/path/to/somefile.txt",
                     '/test/path/to/somefile.txt', 'somefile.txt',
                     'somefile.txt', '/test/path/to'])
    filelist.append(["file:///c:/test/path/to/somefile.txt",
                 r'c:\test\path\to\somefile.txt', 'somefile.txt',
                 'somefile.txt', r'c:\test\path\to'])
    filelist.append(["file:///C:/Documents%20and%20Settings/shanec/Application%20Data/ActiveState/Komodo/2.4/toolbox.kpf",
                 r'C:\Documents and Settings\shanec\Application Data\ActiveState\Komodo\2.4\toolbox.kpf',
                 'toolbox.kpf', 'toolbox.kpf',
                 r'C:\Documents and Settings\shanec\Application Data\ActiveState\Komodo\2.4'
                 ])
    filelist.append(["file:///C:/Program%20Files/Microsoft%20Visual%20Studio/VC98/Include/WINUSER.H",
                 r'C:\Program Files\Microsoft Visual Studio\VC98\Include\WINUSER.H',
                 'WINUSER.H', 'WINUSER.H',
                 r'C:\Program Files\Microsoft Visual Studio\VC98\Include'
                 ])
    
    if win32:
        # linux basename/dirname/etc just choke on this
        filelist.append(["file:///c:/", 'c:\\', '', '', 'c:\\'])
        filelist.append(["file:///c:", 'c:', '', '', 'c:'])

    filelist.append(["file://crimper/apps/Komodo/Naming Rules for Tarballs.txt",
                     '//crimper/apps/Komodo/Naming Rules for Tarballs.txt', 'Naming Rules for Tarballs.txt',
                     'Naming Rules for Tarballs.txt', '//crimper/apps/Komodo'])
    urllist = list(filelist)
    urllist.append(["http://server.com/test/path/to/somefile.txt",
                    r'/test/path/to/somefile.txt', 'somefile.txt',
                    'somefile.txt', '/test/path/to'])
    urllist.append([r'kodebugger://php/c:/web/info.php',
                    r'c:\web\info.php','info.php','info.php',
                    r'c:\web'])
    urllist.append([r'koremote://test/ftp://somesite.com/web/info.php',
                    r'ftp://somesite.com/web/info.php','info.php','info.php',
                    r'ftp://somesite.com/web'])
    urllist.append([r'koremote:///ftp://somesite.com/web/info.php',
                    r'ftp://somesite.com/web/info.php','info.php','info.php',
                    r'ftp://somesite.com/web'])
    urllist.append([r'koremote:///ftp://somesite.com/web with space/info.php',
                    r'ftp://somesite.com/web with space/info.php','info.php','info.php',
                    r'ftp://somesite.com/web with space'])
    urllist.append([r'dbgp:///file:///web with space/info.php',
                    r'file:///web with space/info.php','info.php','info.php',
                    r'file:///web with space'])

    def failUnlessSamePath(self, p1, p2, errmsg = None):
        p1 = p1.replace('\\','/')
        p2 = p2.replace('\\','/')
        self.failUnlessEqual(p1, p2, errmsg)

    def _assertTest(self,uri,test):
        #uri.dump()
        self.failUnlessSamePath(uri.URI, test[0],
            "URI %r != %r" % (uri.URI, test[0]))
        self.failUnlessSamePath(uri.path, test[1],
            "path %r != %r" % (uri.path, test[1]))
        self.failUnlessSamePath(uri.dirName, test[4],
            "dirName %r != %r" % (uri.dirName, test[4]))
        self.failUnlessSamePath(uri.leafName, test[2],
            "leafName %r != %r" % (uri.leafName, test[2]))
        self.failUnlessSamePath(uri.baseName, test[3],
            "baseName %r != %r" % (uri.baseName, test[3]))

    def test_constructFileURI(self):
        for test in self.urllist:
            URI = URIParser(test[0])
            self._assertTest(URI,test)

    def test_constructFilePath(self):
        for test in self.filelist:
            URI = URIParser(test[1])
            self._assertTest(URI,test)

    def test_assignFileURI(self):
        for test in self.urllist:
            URI = URIParser()
            URI.URI = test[0]
            self._assertTest(URI,test)

    def test_assignFilePathToURI(self):
        for test in self.filelist:
            URI = URIParser()
            URI.URI = test[1]
            self._assertTest(URI,test)

    def test_assignFilePath(self):
        for test in self.filelist:
            URI = URIParser()
            URI.path = test[1]
            self._assertTest(URI,test)

    def test_assignNetscapeUNC(self):
        URI = URIParser()
        URI.URI = 'file://///crimper/apps/Komodo/Naming Rules for Tarballs.txt'
        assert URI.URI == 'file://crimper/apps/Komodo/Naming Rules for Tarballs.txt'
        self.failUnlessSamePath(URI.path, r'\\crimper\apps\Komodo\Naming Rules for Tarballs.txt')

    def test_md5name(self):
        filename = os.path.normpath(os.path.join(tempfile.gettempdir(),'testwrite.py.txt'))
        
        URI = URIParser()
        URI.path = filename
        assert URI.md5name == md5.new(URI.URI).hexdigest()
        

class TestFileHandler(unittest.TestCase):
    def test_rootIsDir(self):
        d = os.path.abspath(os.path.dirname(__file__))
        if sys.platform.startswith("win"):
            url = "file:///" + d
        else:
            url = "file://" + d
        file = FileHandler(url)
        assert file.exists
        assert file.isDirectory
        assert not file.isFile
        assert not file.isSymlink
        assert not file.isSpecial
        assert file.isReadable
        assert file.isWriteable
        assert file.isExecutable

    def test_tempIsDir(self):
        filename = tempfile.gettempdir()
        file = FileHandler(filename)
        assert file.exists
        assert file.isDirectory
        assert not file.isFile
        assert not file.isSymlink
        assert not file.isSpecial
        assert file.isReadable
        assert file.isWriteable
        assert file.isExecutable

    def test_readFile(self):
        osPyc = os.__file__
        file = FileHandler(os.path.dirname(osPyc)+'/os.py')
        assert file.exists
        assert not file.isDirectory
        assert file.isFile
        assert not file.isSymlink
        assert not file.isSpecial
        assert file.isReadable
        assert file.isWriteable
        # XXX bogus, this changes in versions of python
        #if sys.platform.startswith("win"):
        #    assert not file.isExecutable
        #else:
        #    assert file.isExecutable
        
        file.open('rb')
        x = file.read(-1)
        assert len(x) > 0 and len(x)==file.fileSize
        file.close()

    def test_writeFile(self):
        text = "This is a test!"
        filename = os.path.normpath(os.path.join(tempfile.gettempdir(),'testwrite.py.txt'))
        file = FileHandler(filename)
        file.open('w+')
        file.write(text)
        file.close()
        assert file.exists
        assert not file.isDirectory
        assert file.isFile
        assert not file.isSymlink
        assert not file.isSpecial
        assert file.isReadable
        assert file.isWriteable
        file = FileHandler(filename)
        file.open('r+')
        assert file.read(-1) == text
        
#---- mainline

def suite():
    suites = []
    suites.append( unittest.makeSuite(TestURIParser) )
    suites.append( unittest.makeSuite(TestFileHandler) )
    return unittest.TestSuite(suites)

def test_main():
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite())

if __name__ == "__main__":
    __file__ = sys.argv[0] # won't be necessary in Python 2.3
    test_main()



