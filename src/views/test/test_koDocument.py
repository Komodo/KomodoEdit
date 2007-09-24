# Copyright (c) 2000-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

import os
import sys, md5
import unittest
import tempfile

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
        filename = 'http://www.xmethods.net/sd/2001/BabelFishService.wsdl'
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
        # expects the be in Komodo-devel
        p = os.path.join(os.getcwd(), "test", "charsets", "utf-8_1.html")
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
        # expects the be in Komodo-devel
        p = os.path.join(os.getcwd(), "test", "charsets", "utf-8_1.html")
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
            doc_asfn = os.path.basename(document.getAutoSaveFileName())
            my_asfn = "%s-%s" % (md5.new(document.file.URI).hexdigest(),document.file.baseName)
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


