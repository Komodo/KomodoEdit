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


class TestKoDocumentBase(unittest.TestCase):
    def test_createFile(self):
        filename = tempfile.mktemp()
        text = "This is a test!"
        document = components.classes["@activestate.com/koDocumentBase;1"] \
                   .createInstance(components.interfaces.koIDocument)

        try:
            document.initWithURI(filename)
            document.buffer = text
            document.save(0)
            
            document = components.classes["@activestate.com/koDocumentBase;1"] \
                       .createInstance(components.interfaces.koIDocument)
            document.initWithURI(filename)
            document.load()
            assert document.buffer == text
        finally:
            if os.path.exists(filename):
                os.unlink(filename) # clean up
        
    def test_revertFile(self):
        filename = tempfile.mktemp()
        try:
            # Init the test file with some content.
            fout = open(filename, 'w')
            fout.write("blah\nblah\nblah")
            fout.close()

            document = components.classes["@activestate.com/koDocumentBase;1"] \
                       .createInstance(components.interfaces.koIDocument)
            document.initWithURI(filename)
            document.load()
            oldtext = document.buffer
            document.buffer = None
            assert not document.buffer
            document.revert()
            assert oldtext == document.buffer
        finally:
            if os.path.exists(filename):
                os.unlink(filename) # clean up

    def test_readFile(self):
        filename = tempfile.mktemp()
        try:
            # Init the test file with some content.
            fout = open(filename, 'w')
            fout.write("blah\nblah\nblah")
            fout.close()

            document = components.classes["@activestate.com/koDocumentBase;1"] \
                       .createInstance(components.interfaces.koIDocument)
            document.initWithURI(filename)
            document.load()
            assert document.buffer
        finally:
            if os.path.exists(filename):
                os.unlink(filename) # clean up

    def test_readURI(self):
        filename = 'http://downloads.activestate.com/'
        try:
            document = components.classes["@activestate.com/koDocumentBase;1"] \
                       .createInstance(components.interfaces.koIDocument)
            document.initWithURI(filename)
            document.load()
            assert document.buffer
        finally:
            if os.path.exists(filename):
                os.unlink(filename) # clean up

    def test_changeLineEndings(self):
        filename = tempfile.mktemp()
        try:
            # Init the test file with some content.
            fout = open(filename, 'w')
            fout.write("blah\nblah\nblah")
            fout.close()

            document = components.classes["@activestate.com/koDocumentBase;1"] \
                       .createInstance(components.interfaces.koIDocument)
            document.initWithURI(filename)
            document.load()
            # does the document match our platform endings?
            assert document.existing_line_endings == eollib.EOL_PLATFORM
            # test converting to each of our endings
            for le in eollib.eolMappings.keys():
                document.existing_line_endings = le
                assert document.existing_line_endings == le
            # test converting to an invalid ending, should raise exception
            try:
                document.existing_line_endings = 10
            except COMException, e:
                pass
            assert document.existing_line_endings != 10
        finally:
            if os.path.exists(filename):
                os.unlink(filename) # clean up

    def test_loadUTF8File(self):
        from xpcom.server import WrapObject, UnwrapObject
        # expects the path to be in Komodo-devel
        p = join(dirname(                             # komodo-devel
                  dirname(                            # src
                   dirname(                           # views
                    dirname((abspath(__file__)))))),  # tests
                 "test", "stuff", "charsets", "utf-8_1.html")
        utffile = os.path.abspath(p)
        assert os.path.isfile(utffile)
        document = components.classes["@activestate.com/koDocumentBase;1"] \
                   .createInstance(components.interfaces.koIDocument)
        document.initWithURI(utffile)
        document.prefs.setBooleanPref('encodingAutoDetect',1)
        document.load()
        # is utf8 identified?
        assert document.encoding.python_encoding_name == 'utf-8'
        assert document.codePage == 65001

    def test_forceEncoding(self):
        # expects the path to be in Komodo-devel
        p = join(dirname(                             # komodo-devel
                  dirname(                            # src
                   dirname(                           # views
                    dirname((abspath(__file__)))))),  # tests
                 "test", "stuff", "charsets", "utf-8_1.html")
        utffile = os.path.abspath(p)
        assert os.path.isfile(utffile)
        document = components.classes["@activestate.com/koDocumentBase;1"] \
                   .createInstance(components.interfaces.koIDocument)
        document.initWithURI(utffile)
        document.prefs.setBooleanPref('encodingAutoDetect',1)
        document.load()
        document.forceEncodingFromEncodingName('latin-1')
        assert document.encoding.python_encoding_name == 'latin-1'
        # this is not true any longer
        #assert document.codePage == 0

    def test_autoSaveFile(self):
        filename = tempfile.mktemp()
        buffer = "blah\nblah\nblah"
        try:
            # Init the test file with some content.
            fout = open(filename, 'wb')
            fout.write(buffer)
            fout.close()

            document = components.classes["@activestate.com/koDocumentBase;1"] \
                       .createInstance(components.interfaces.koIDocument)
            document.initWithURI(filename)
            document.load()
            assert not document.haveAutoSave()
            
            # test the autosave filename
            doc_asfn = os.path.basename(UnwrapObject(document)._getAutoSaveFileName())
            my_asfn = "%s-%s" % (md5(document.file.URI).hexdigest(),document.file.baseName)
            assert doc_asfn == my_asfn
            
            # document is not dirty yet
            document.doAutoSave()
            assert not document.haveAutoSave()
            
            # make the document dirty then save
            document.isDirty = 1
            document.doAutoSave()
            assert document.haveAutoSave()
            
            document.buffer = "tada"
            document.restoreAutoSave()
            assert document.buffer == buffer
            document.removeAutoSaveFile()
            assert not document.haveAutoSave()
        finally:
            if os.path.exists(filename):
                os.unlink(filename) # clean up

#---- mainline

def suite():
    return unittest.makeSuite(TestKoDocumentBase)

def test_main():
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite())

if __name__ == "__main__":
    __file__ = os.path.abspath(sys.argv[0]) # won't be necessary in Python 2.3
    test_main()


