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



