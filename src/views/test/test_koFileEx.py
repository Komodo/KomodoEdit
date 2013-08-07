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

import os
import unittest
import re, sys
from hashlib import md5
import tempfile

from xpcom import components, COMException

win32 = sys.platform.startswith("win")

def _koFileSymlinkMatchesOSPath(path, koFile):
    if os.path.islink(path):
        return koFile.isSymlink
    else:
        return not koFile.isSymlink

class TestKoFileEx(unittest.TestCase):
    def __init__(self, methodName):
        unittest.TestCase.__init__(self, methodName)
        initSvc = components.classes["@activestate.com/koInitService;1"] \
                      .getService(components.interfaces.koIInitService)
        initSvc.setEncoding()
        
        self.__file = components.classes["@activestate.com/koFileEx;1"] \
                      .createInstance(components.interfaces.koIFileEx)

    win_file_ptn = re.compile(r'(\w):(.*)')
    win_uri_ptn = re.compile(r'file:///(\w):/(.*)')
    if win32:
        def _normalizePath(self, winPath):
            return winPath
        
        def _normalizeURI(self, winPath):
            return winPath
    else:
        def _normalizePath(self, winPath):
            m = self.win_file_ptn.match(winPath)
            if m:
                return m.group(2).replace('\\', '/')
            return winPath
        
        def _normalizeURI(self, winPath):
            m = self.win_uri_ptn.match(winPath)
            if m:
                return 'file:///' + m.group(2)
            return winPath

    def failUnlessSamePath(self, p1, p2, errmsg = None):
        p1 = p1.replace('\\','/')
        p2 = p2.replace('\\','/')
        self.failUnlessEqual(p1, p2, errmsg)

    def test_assignFileURI(self):
        url = self._normalizeURI("file:///c:/test/path/to/somefile.txt")
        path = self._normalizePath(r'c:\test\path\to\somefile.txt')
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
        url = self._normalizeURI("file:///C:/Program%20Files/Microsoft%20Visual%20Studio/VC98/Include/WINUSER.H")
        path = self._normalizePath(r'C:\Program Files\Microsoft Visual Studio\VC98\Include\WINUSER.H')
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
        url = self._normalizeURI("file:///c:/test/path/to/somefile.txt")
        path = self._normalizePath(r'c:\test\path\to\somefile.txt')
        self.__file.URI = path
        self.failUnlessSamePath(self.__file.URI, url,
                           "%r != %r" %(self.__file.URI, url))
        self.failUnlessSamePath(self.__file.path, path,
                           "%r != %r" %(self.__file.path, path))
        assert self.__file.leafName == 'somefile.txt'
        assert self.__file.baseName == 'somefile.txt'
        dir = self._normalizePath(r'c:\test\path\to')
        self.failUnlessSamePath(self.__file.dirName, dir,
                           "%r != %r" %(self.__file.dirName, dir))
        
    def test_assignFilePath(self):
        url = self._normalizeURI("file:///c:/test/path/to/somefile.txt")
        path = self._normalizePath(r'c:\test\path\to\somefile.txt')
        self.__file.path = path
        self.failUnlessSamePath(self.__file.URI, url,
                           "%r != %r" %(self.__file.URI, url))
        self.failUnlessSamePath(self.__file.path, path,
                           "%r != %r" %(self.__file.path, path))
        assert self.__file.leafName == 'somefile.txt'
        assert self.__file.baseName == 'somefile.txt'
        dir = self._normalizePath(r'c:\test\path\to')
        self.failUnlessSamePath(self.__file.dirName, dir,
                           "%r != %r" %(self.__file.dirName, dir))

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
        assert _koFileSymlinkMatchesOSPath(d, self.__file)
        assert not self.__file.isSpecial
        assert self.__file.isReadable
        assert self.__file.isWriteable

    def test_tempIsDir(self):
        d = tempfile.gettempdir()
        self.__file.path = d
        assert self.__file.exists
        assert self.__file.isDirectory
        assert not self.__file.isFile
        assert _koFileSymlinkMatchesOSPath(d, self.__file)
        assert not self.__file.isSpecial
        assert self.__file.isReadable
        assert self.__file.isWriteable

    def test_readFile(self):
        filename = os.__file__ # returns os.pyc
        self.__file.path = os.path.dirname(filename)+'/os.py'
        assert self.__file.exists
        assert not self.__file.isDirectory
        assert self.__file.isFile
        assert _koFileSymlinkMatchesOSPath(filename, self.__file)
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
            assert _koFileSymlinkMatchesOSPath(filename, self.__file)
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
                assert self.__file.updateStats()
                assert not self.__file.exists

    def test_fileChanged(self):
        filename = tempfile.mktemp()
        try:
            text = "This is a test!"
            self.__file.URI = filename
            self.__file.open('w');
            self.__file.write(text)
            self.__file.close()
            assert not self.__file.updateStats()
            self.__file.URI = filename
            self.__file.open('w')
            self.__file.write(text * 2)
            self.__file.close()
            assert self.__file.updateStats()
            # updateStats() will update the stats, next call will be different
            assert not self.__file.updateStats()
        finally:
            if os.path.isfile(filename):
                os.remove(filename) # clean up

    def test_stat(self):
        filename = os.__file__ # returns os.pyc
        self.__file.path = os.path.dirname(filename)+'/os.py'
        assert self.__file.lastModifiedTime != 0

    def test_path(self):
        url = self._normalizeURI("file:///c:/test/path/to/somefile.txt")
        path = self._normalizePath(r'c:\test\path\to\somefile.txt')
        dirname = os.path.dirname(path.replace('\\','/'))
        self.__file.URI = url
        self.failUnlessSamePath(self.__file.URI, url,
                           "%r != %r" %(self.__file.URI, url))
        self.failUnlessSamePath(self.__file.path, path,
                           "%r != %r" %(self.__file.path, path))
        self.failUnlessSamePath(self.__file.dirName, dirname,
                           "%r != %r" %(self.__file.dirName, dirname))

        url = 'http://someserver.com/test/path/to/somefile.txt'
        path = self._normalizePath(r'\test\path\to\somefile.txt')
        dirname = os.path.dirname(path.replace('\\','/'))
        self.__file.URI = url
        self.failUnlessSamePath(self.__file.URI, url,
                           "%r != %r" %(self.__file.URI, url))
        self.failUnlessSamePath(self.__file.path, path,
                           "%r != %r" %(self.__file.path, path))
        self.failUnlessSamePath(self.__file.dirName, dirname,
                           "%r != %r" %(self.__file.dirName, dirname))

        url = self._normalizeURI('file:///c:/path%20with%20spaces/path/to/somefile.txt')
        path = self._normalizePath(r'c:\path with spaces\path\to\somefile.txt')
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
 
    def test_path_with_percent(self):
        # Ensure the koIFileEx routines do not try to unquote the path,
        # bug 82660.
        path = self._normalizePath(r'c:\test\path\to\file with percent_%ab.txt')
        uri = self._normalizeURI(r'file:///c:/test/path/to/file%20with%20percent_%25ab.txt')
        self.__file.path = path
        self.failUnlessEqual(self.__file.URI, uri)
        self.__file.URI = uri
        self.failUnlessEqual(self.__file.path, path)

    def test_fileNotExist(self):
        self.__file.URI = "Text-1.txt"
        assert not self.__file.exists

    def test_md5name(self):
        filename = os.path.normpath(os.path.join(tempfile.gettempdir(),'testwrite.py.txt'))
        self.__file.path = filename
        assert self.__file.md5name == md5(self.__file.URI).hexdigest()

    def test_fwdSlashWinPathIsFile(self):
        # bug99683: verify that remote paths from Windows aren't
        # treated as a URI-type scheme on non-Windows systems.
        # Applies to paths with forward slashes
        if win32:
            # Verify nothing weird is happening on Windows
            path_bs =  os.path.normpath(__file__)
            path_fs = path_bs.replace('\\', '/')
        else:
            path_bs = path_fs = "c:/nonexistent/placeholder/for/test_koFileEx.py"
        self.__file.URI = path_fs
        assert self.__file.scheme == "file"
        if win32:
            assert self.__file.isFile
        self.failUnlessEqual(self.__file.path, path_bs)
        self.failUnlessEqual(self.__file.baseName, "test_koFileEx.py")
        self.failUnlessEqual(self.__file.dirName,
                             path_bs[:path_fs.rindex("/")])
        self.failUnlessEqual(self.__file.scheme, "file")
        if win32:
            assert self.__file.exists

#---- mainline

def suite():
    return unittest.makeSuite(TestKoFileEx)

def test_main():
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite())

if __name__ == "__main__":
    __file__ = os.path.abspath(sys.argv[0]) # won't be necessary in Python 2.3
    test_main()



