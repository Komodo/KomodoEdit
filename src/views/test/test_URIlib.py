# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
# 
# The contents of this file are subject to the Mozilla Public License
# Version 1.1 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
# 
# Software distributed under the License is distributed on an "AS IS"
# basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
# License for the specific language governing rights and limitations
# under the License.
# 
# The Original Code is Komodo code.
# 
# The Initial Developer of the Original Code is ActiveState Software Inc.
# Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
# ActiveState Software Inc. All Rights Reserved.
# 
# Contributor(s):
#   ActiveState Software Inc
# 
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
# 
# ***** END LICENSE BLOCK *****

import sys
from hashlib import md5
import unittest
import tempfile

from URIlib import *
win32 = sys.platform.startswith("win")

from testlib import TestSkipped, tag

def _koFileSymlinkMatchesOSPath(path, koFile):
    if os.path.islink(path):
        return koFile.isSymlink
    else:
        return not koFile.isSymlink

class TestURIParser(unittest.TestCase):
    filelist = []
    urllist = []
    filelist.append(['about:blank',  # uri
                     'about:blank',  # path
                     'about:blank',  # baseName
                     '',             # dirName
                     'about://',     # prePath
                     ])
    filelist.append(['file:///test/path/to/some:file.txt',  # uri
                     '/test/path/to/some:file.txt',  # path
                     'some:file.txt',  # baseName
                     '/test/path/to',  # dirName
                     'file://',  # prePath
                     ])
    filelist.append(['file:///test/path/to/somefile.txt',  # uri
                     '/test/path/to/somefile.txt',  # path
                     'somefile.txt',  # baseName
                     '/test/path/to',  # dirName
                     'file://',  # prePath
                     ])
    if win32:
        filelist.append(['file:///c:/test/path/to/somefile.txt',  # uri
                         r'c:\test\path\to\somefile.txt',  # path
                         'somefile.txt',  # baseName
                         r'c:\test\path\to',  # dirName
                         'file://',  # prePath
                         ])
        filelist.append(['file:///C:/Documents%20and%20Settings/shanec/Application%20Data/ActiveState/Komodo/2.4/toolbox.kpf',  # uri
                         r'C:\Documents and Settings\shanec\Application Data\ActiveState\Komodo\2.4\toolbox.kpf',  # path
                         'toolbox.kpf',  # baseName
                         r'C:\Documents and Settings\shanec\Application Data\ActiveState\Komodo\2.4',  # dirName
                         'file://',  # prePath
                         ])
        filelist.append(['file:///C:/Program%20Files/Microsoft%20Visual%20Studio/VC98/Include/WINUSER.H',  # uri
                         r'C:\Program Files\Microsoft Visual Studio\VC98\Include\WINUSER.H',  # path
                         'WINUSER.H',  # baseName
                         r'C:\Program Files\Microsoft Visual Studio\VC98\Include',  # dirName
                         'file://',  # prePath
                         ])
    else:
        # Test Windows file path handling on Unix (bug 99683).
        filelist.append(['file:///c:/test/path/to/somefile.txt',  # uri
                         'c:/test/path/to/somefile.txt',  # path
                         'somefile.txt',  # baseName
                         'c:/test/path/to',  # dirName
                         'file://',  # prePath
                         ])
    
    if win32:
        # linux basename/dirname/etc just choke on this
        filelist.append(['file:///c:/', 'c:\\', '', 'c:\\', 'file://'])
        filelist.append(['file:///c:', 'c:', '', 'c:', 'file://'])

    if sys.platform.startswith('win'):
        # Windows provides support for UNC file paths.
        filelist.append(['file://///netshare/apps/Komodo/Naming%20Rules%20for%20Tarballs.txt',  # uri
                         '//netshare/apps/Komodo/Naming Rules for Tarballs.txt',  # path
                         'Naming Rules for Tarballs.txt',  # baseName
                         '//netshare/apps/Komodo',  # dirName
                         'file://netshare',  # prePath
                         ])
        filelist.append(['file://///server/share/path/file.txt', # uri
                         r'\\server\share\path\file.txt', # path
                         'file.txt', # baseName
                         '//server/share/path', # dirName
                         'file://server', # prePath
                         ])
    else:
        # Other platforms do not use UNC file paths.
        filelist.append(['file:///apps/Komodo/Naming%20Rules%20for%20Tarballs.txt',  # uri
                         '/apps/Komodo/Naming Rules for Tarballs.txt',  # path
                         'Naming Rules for Tarballs.txt',  # baseName
                         '/apps/Komodo',  # dirName
                         'file://',  # prePath
                         ])
    urllist = list(filelist)
    urllist.append(['http://server.com/test/path/to/somefile.txt',  # uri
                    '/test/path/to/somefile.txt',  # path
                    'somefile.txt',  # baseName
                    '/test/path/to',  # dirName
                    'http://server.com',  # prePath
                    ])
    urllist.append(['ftp://somesite.com/web/info.php',  # uri
                    '/web/info.php',  # path
                    'info.php',  # baseName
                    '/web',  # dirName
                    'ftp://somesite.com',  # prePath
                    ])
    urllist.append(['ftp://somesite.com/web/info.php',  # uri
                    '/web/info.php',  # path
                    'info.php',  # baseName
                    '/web',  # dirName
                    'ftp://somesite.com',  # prePath
                    ])
    urllist.append(['ftp://somesite.com/web%20with%20space/info.php',  # uri
                    '/web with space/info.php',  # path
                    'info.php',  # baseName
                    '/web with space',  # dirName
                    'ftp://somesite.com',  # prePath
                    ])

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
        self.failUnlessSamePath(uri.baseName, test[2],
            "baseName %r != %r" % (uri.baseName, test[2]))
        # Note: leafName is just an alias for baseName
        self.failUnlessSamePath(uri.leafName, test[2],
            "leafName %r != %r" % (uri.leafName, test[2]))
        self.failUnlessSamePath(uri.dirName, test[3],
            "dirName %r != %r" % (uri.dirName, test[3]))
        self.failUnlessSamePath(uri.prePath, test[4],
            "prePath %r != %r" % (uri.prePath, test[4]))

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
        if not win32:
            raise TestSkipped("Only applicable on Windows")
        URI = URIParser()
        URI.URI = 'file://///netshare/apps/Komodo/Naming Rules for Tarballs.txt'
        self.assertEqual(URI.URI, 'file://///netshare/apps/Komodo/Naming%20Rules%20for%20Tarballs.txt')
        self.failUnlessSamePath(URI.path, r'\\netshare\apps\Komodo\Naming Rules for Tarballs.txt')

    @tag("bug106180")
    def test_doubleroot(self):
        if win32:
            raise TestSkipped("Not applicable on Windows")
        URI = URIParser()
        URI.path = '//home/toddw/file.txt'
        self.assertEqual(URI.URI, 'file:///home/toddw/file.txt')
        self.failUnlessSamePath(URI.path, '/home/toddw/file.txt')

    @tag("bug106180")
    def test_tripleroot(self):
        if win32:
            raise TestSkipped("Not applicable on Windows")
        URI = URIParser()
        URI.path = '///home/toddw/file.txt'
        self.assertEqual(URI.URI, 'file:///home/toddw/file.txt')
        self.failUnlessSamePath(URI.path, '/home/toddw/file.txt')

    def test_md5name(self):
        filename = os.path.normpath(os.path.join(tempfile.gettempdir(),'testwrite.py.txt'))
        
        URI = URIParser()
        URI.path = filename
        assert URI.md5name == md5(URI.URI).hexdigest()
        

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
        assert _koFileSymlinkMatchesOSPath(d, file)
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
        assert _koFileSymlinkMatchesOSPath(filename, file)
        assert not file.isSpecial
        assert file.isReadable
        assert file.isWriteable
        assert file.isExecutable

    def test_readFile(self):
        osPyc = os.__file__
        path = os.path.dirname(osPyc)+'/os.py'
        file = FileHandler(path)
        assert file.exists
        assert not file.isDirectory
        assert file.isFile
        assert _koFileSymlinkMatchesOSPath(path, file)
        assert not file.isSpecial
        assert file.isReadable
        assert file.isWriteable
        # XXX bogus, this changes in versions of python
        #if sys.platform.startswith("win"):
        #    assert not file.isExecutable
        #else:
        #    assert file.isExecutable
        
        file.open('rb')
        try:
            x = file.read(-1)
            assert len(x) > 0 and len(x)==file.fileSize
        finally:
            file.close()

    def test_writeFile(self):
        text = "This is a test!"
        filename = os.path.normpath(os.path.join(tempfile.gettempdir(),'testwrite.py.txt'))
        file = FileHandler(filename)
        file.open('w+')
        file.write(text)
        file.close()
        try:
            assert file.exists
            assert not file.isDirectory
            assert file.isFile
            assert _koFileSymlinkMatchesOSPath(filename, file)
            assert not file.isSpecial
            assert file.isReadable
            assert file.isWriteable
            file = FileHandler(filename)
            file.open('r+')
            try:
                assert file.read(-1) == text
            finally:
                file.close()
        finally:
            os.unlink(filename)
        
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



