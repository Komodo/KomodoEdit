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
import sys
from hashlib import md5
import unittest
import tempfile
from os.path import abspath, dirname, join

import eollib
from xpcom import components, nsError, ServerException, COMException
from xpcom.server import WrapObject, UnwrapObject


class _KoDocTestCase(unittest.TestCase):
    """Base class for koIDocument test cases."""
    _fileSvcCache = None
    @property
    def _fileSvc(self):
        if self._fileSvcCache is None:
            self._fileSvcCache = components.classes["@activestate.com/koFileService;1"] \
                .getService(components.interfaces.koIFileService)
        return self._fileSvcCache

    def _koDocFromPath(self, path):
        """Return an intialized `KoDocument` instance for the given path."""
        import uriparse
        uri = uriparse.localPathToURI(path)
        return self._koDocFromURI(uri)
    
    def _koDocFromURI(self, uri):
        koFile = self._fileSvc.getFileFromURI(uri)
        koDoc = components.classes["@activestate.com/koDocumentBase;1"] \
            .createInstance(components.interfaces.koIDocument)
        koDoc.initWithFile(koFile, False);
        return koDoc


class KoDocInfoDetectionTestCase(_KoDocTestCase):
    __tags__ = ["detection"]
    
    @property
    def data_dir(self):
        return join(dirname(abspath(__file__)), "detection_data")
    
    def test_basic(self):
        for name in ("exists.py", "does not exist.py"):
            koDoc = self._koDocFromPath(join(self.data_dir, name))
            self.assertEqual(koDoc.language, "Python")
    
    def test_eol(self):
        """Test EOL detection."""
        EOL_LF = components.interfaces.koIDocument.EOL_LF
        EOL_CR = components.interfaces.koIDocument.EOL_CR
        EOL_CRLF = components.interfaces.koIDocument.EOL_CRLF
        EOL_MIXED = components.interfaces.koIDocument.EOL_MIXED
        EOL_NOEOL = components.interfaces.koIDocument.EOL_NOEOL
        data = [
            ("eol_lf.py", EOL_LF, EOL_LF),
            ("eol_cr.py", EOL_CR, EOL_CR),
            ("eol_crlf.py", EOL_CRLF, EOL_CRLF),
            ("eol_mixed.py", EOL_MIXED, eollib.EOL_PLATFORM),
            # `koIDocument.existing_line_endings` current impl. doesn't
            # return EOL_NOEOL. Instead it traps that value and returns
            # `new_line_endings`.
            ("eol_empty.py", eollib.EOL_PLATFORM, eollib.EOL_PLATFORM),
        ]
        for name, existing_line_endings, new_line_endings in data:
            koDoc = self._koDocFromPath(join(self.data_dir, name))
            koDoc.load()
            self.assertEqual(koDoc.existing_line_endings, existing_line_endings,
                "unexpected `koDoc.existing_line_endings` value for %r: "
                "expected %r, got %r" % (
                    name, existing_line_endings, koDoc.existing_line_endings))
            self.assertEqual(koDoc.new_line_endings, new_line_endings,
                "unexpected `koDoc.new_line_endings` value for %r: "
                "expected %r, got %r" % (
                    name, new_line_endings, koDoc.new_line_endings))
    

class TestKoDocumentBase(_KoDocTestCase):
    def test_createFile(self):
        text = "This is a test!"
        path = tempfile.mktemp()
        try:
            koDoc = self._koDocFromPath(path)
            koDoc.buffer = text
            koDoc.save(0)
            del koDoc
            
            koDoc2 = self._koDocFromPath(path)
            koDoc2.load()
            assert koDoc2.buffer == text
        finally:
            if os.path.exists(path):
                os.unlink(path) # clean up
        
    def test_revertFile(self):
        path = tempfile.mktemp()
        try:
            # Init the test file with some content.
            fout = open(path, 'w')
            fout.write("blah\nblah\nblah")
            fout.close()

            koDoc = self._koDocFromPath(path)
            koDoc.load()
            oldtext = koDoc.buffer
            koDoc.buffer = None
            assert not koDoc.buffer
            koDoc.revert()
            assert oldtext == koDoc.buffer
        finally:
            if os.path.exists(path):
                os.unlink(path) # clean up

    def test_readFile(self):
        path = tempfile.mktemp()
        try:
            # Init the test file with some content.
            fout = open(path, 'w')
            fout.write("blah\nblah\nblah")
            fout.close()

            koDoc = self._koDocFromPath(path)
            koDoc.load()
            assert koDoc.buffer
        finally:
            if os.path.exists(path):
                os.unlink(path) # clean up

    def test_readURI(self):
        url = 'http://downloads.activestate.com/'
        koDoc = self._koDocFromURI(url)
        koDoc.load()
        assert koDoc.buffer

    def test_changeLineEndings(self):
        path = tempfile.mktemp()
        try:
            # Init the test file with some content.
            fout = open(path, 'w')
            fout.write("blah\nblah\nblah")
            fout.close()

            koDoc = self._koDocFromPath(path)
            koDoc.load()
            # Does the document match our platform endings?
            assert koDoc.existing_line_endings == eollib.EOL_PLATFORM
            # test converting to each of our endings
            for le in eollib.eolMappings.keys():
                koDoc.existing_line_endings = le
                assert koDoc.existing_line_endings == le
            # test converting to an invalid ending, should raise exception
            try:
                koDoc.existing_line_endings = 10
            except COMException, e:
                pass
            assert koDoc.existing_line_endings != 10
        finally:
            if os.path.exists(path):
                os.unlink(path) # clean up

    def test_loadUTF8File(self):
        # expects the path to be in Komodo-devel
        p = join(dirname(                             # komodo-devel
                  dirname(                            # src
                   dirname(                           # views
                    dirname((abspath(__file__)))))),  # tests
                 "test", "stuff", "charsets", "utf-8_1.html")
        utf_path = os.path.abspath(p)
        assert os.path.isfile(utf_path)
        koDoc = self._koDocFromPath(utf_path)
        koDoc.prefs.setBooleanPref('encodingAutoDetect', 1)
        koDoc.load()
        # is utf8 identified?
        assert koDoc.encoding.python_encoding_name == 'utf-8'
        assert koDoc.codePage == 65001

    def test_forceEncoding(self):
        # expects the path to be in Komodo-devel
        p = join(dirname(                             # komodo-devel
                  dirname(                            # src
                   dirname(                           # views
                    dirname((abspath(__file__)))))),  # tests
                 "test", "stuff", "charsets", "utf-8_1.html")
        utf_path = os.path.abspath(p)
        assert os.path.isfile(utf_path)
        koDoc = self._koDocFromPath(utf_path)
        koDoc.prefs.setBooleanPref('encodingAutoDetect',1)
        koDoc.load()
        koDoc.forceEncodingFromEncodingName('latin-1')
        assert koDoc.encoding.python_encoding_name == 'latin-1'
        # this is not true any longer
        #assert koDoc.codePage == 0

    def test_autoSaveFile(self):
        path = tempfile.mktemp()
        buffer = "blah\nblah\nblah"
        try:
            # Init the test file with some content.
            fout = open(path, 'wb')
            fout.write(buffer)
            fout.close()

            koDoc = self._koDocFromPath(path)
            koDoc.load()
            assert not koDoc.haveAutoSave()
            
            # test the autosave path
            doc_asfn = os.path.basename(UnwrapObject(koDoc)._getAutoSaveFileName())
            my_asfn = "%s-%s" % (md5(koDoc.file.URI).hexdigest(),koDoc.file.baseName)
            assert doc_asfn == my_asfn
            
            # document is not dirty yet
            koDoc.doAutoSave()
            assert not koDoc.haveAutoSave()
            
            # make the document dirty then save
            koDoc.isDirty = 1
            koDoc.doAutoSave()
            assert koDoc.haveAutoSave()
            
            koDoc.buffer = "tada"
            koDoc.restoreAutoSave()
            assert koDoc.buffer == buffer
            koDoc.removeAutoSaveFile()
            assert not koDoc.haveAutoSave()
        finally:
            if os.path.exists(path):
                os.unlink(path) # clean up

#---- mainline

def suite():
    return unittest.makeSuite(TestKoDocumentBase)

def test_main():
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite())

if __name__ == "__main__":
    __file__ = os.path.abspath(sys.argv[0]) # won't be necessary in Python 2.3
    test_main()


