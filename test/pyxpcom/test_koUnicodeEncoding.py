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
import os
from os.path import join, normpath, dirname
import unittest
import codecs

from koUnicodeEncoding import *

# Python 2.2 codecs BOM is super busted, this is from
# Ptyhon 2.3 codecs, which is correct. The below BOM codes are copied from 2.3

### Constants

#
# Byte Order Mark (BOM = ZERO WIDTH NO-BREAK SPACE = U+FEFF)
# and its possible byte string values
# for UTF8/UTF16/UTF32 output and little/big endian machines
#

# UTF-8
BOM_UTF8 = '\xef\xbb\xbf'

# UTF-16, little endian
BOM_LE = BOM_UTF16_LE = '\xff\xfe'

# UTF-16, big endian
BOM_BE = BOM_UTF16_BE = '\xfe\xff'

# UTF-32, little endian
BOM_UTF32_LE = '\xff\xfe\x00\x00'

# UTF-32, big endian
BOM_UTF32_BE = '\x00\x00\xfe\xff'

if sys.byteorder == 'little':

    # UTF-16, native endianness
    BOM = BOM_UTF16 = BOM_UTF16_LE

    # UTF-32, native endianness
    BOM_UTF32 = BOM_UTF32_LE

else:

    # UTF-16, native endianness
    BOM = BOM_UTF16 = BOM_UTF16_BE

    # UTF-32, native endianness
    BOM_UTF32 = BOM_UTF32_BE


xml_unicode_test = u"<?xml version='1.0' encoding='%s'?><abc>\u2222</abc>"
xml_ascii_test = "<?xml version='1.0' encoding='%s'?><abc>q</abc>"
unicode_test = u"\u2222"
ascii_test = "This is a simple ascii string"


class TestDetectEncoding(unittest.TestCase):
    def __init__(self, methodName='runTest'):
        unittest.TestCase.__init__(self, methodName)
    
    def _doDetectString(self,
                        teststr,
                        encoding,
                        bom=None,
                        tryXMLDecl=0,
                        tryHTMLMeta = 0,
                        tryModeline = 0,
                        wantEncoding=None,
                        defaultEncoding='iso8859-1',
                        expectFailure=0):
        try:
            data = teststr.encode(encoding)
        except UnicodeError, e:
            if expectFailure:
                return
            raise
        
        if bom:
            data = bom + data

        buffer, autoEncoding, bom = autoDetectEncoding(data,
                                                       tryXMLDecl,
                                                       wantEncoding=encoding)
        #print "%s == %s" %(autoEncoding, encoding)
        if expectFailure:
            assert autoEncoding != encoding
        else:
            assert autoEncoding == encoding

    def test_DetectXML_ASCII(self):
        enc = "ascii"
        self._doDetectString(xml_ascii_test % enc, enc)
        self._doDetectString(xml_ascii_test % enc, enc, tryXMLDecl=1)
        self._doDetectString(xml_unicode_test % enc, enc, expectFailure=1)

    def test_DetectXML_LATIN(self):
        enc = "latin-1"
        self._doDetectString(xml_ascii_test % enc, enc)
        self._doDetectString(xml_ascii_test % enc, enc, tryXMLDecl=1)
        self._doDetectString(xml_unicode_test % enc, enc, expectFailure=1)

    def test_DetectXML_ISO8859_1(self):
        enc = "iso8859-1"
        self._doDetectString(xml_ascii_test % enc, enc)
        self._doDetectString(xml_ascii_test % enc, enc, tryXMLDecl=1)
        self._doDetectString(xml_unicode_test % enc, enc, expectFailure=1)

    def test_DetectXML_UTF8(self):
        enc = "utf-8"
        self._doDetectString(xml_unicode_test % enc, enc)
        self._doDetectString(xml_unicode_test % enc, enc, tryXMLDecl=1)

    def test_DetectXML_UTF8_BOM(self):
        enc = "utf-8"
        self._doDetectString(xml_unicode_test % enc, enc, bom=BOM_UTF8)
        self._doDetectString(xml_unicode_test % enc, enc, tryXMLDecl=1, bom=BOM_UTF8)
        
    def test_DetectXML_UTF16_LE(self):
        enc = "utf-16-le"
        self._doDetectString(xml_unicode_test % enc, enc)
        self._doDetectString(xml_unicode_test % enc, enc, tryXMLDecl=1)

    def test_DetectXML_UTF16_BE(self):
        enc = "utf-16-be"
        self._doDetectString(xml_unicode_test % enc, enc)
        self._doDetectString(xml_unicode_test % enc, enc, tryXMLDecl=1)

    def test_DetectXML_UTF16_LE_BOM(self):
        enc = "utf-16-le"
        self._doDetectString(xml_unicode_test % enc, enc, bom=BOM_UTF16_LE)
        self._doDetectString(xml_unicode_test % enc, enc, tryXMLDecl=1, bom=BOM_UTF16_LE)
        
    def test_DetectXML_UTF16_BE_BOM(self):
        enc = "utf-16-be"
        self._doDetectString(xml_unicode_test % enc, enc, bom=BOM_UTF16_BE)
        self._doDetectString(xml_unicode_test % enc, enc, tryXMLDecl=1, bom=BOM_UTF16_BE)

class TestChangeEncoding(unittest.TestCase):
    def __init__(self, methodName='runTest'):
        unittest.TestCase.__init__(self, methodName)
        self.rawstr = ''
        for i in range(256): self.rawstr = self.rawstr + chr(i)

    def test_8BittoUCS2(self):
        # just to make sure bytes are preserved
        uni = unicode(self.rawstr, 'latin-1')
        raw = uni.encode('latin-1')
        assert raw == self.rawstr
        
    def test_ConvertUTF8to16(self):
        teststr=u"\u2222\u2323\u4343"
        assert makeUTF8(teststr.encode("utf-16"), "utf-16") == teststr.encode("utf-8")
    
    def test_Convert8BitEncodings(self):
        # test converting from latin-1 to koi8-r and back, verifying all bytes
        # remain correctly
        
        # make this a latin-1 unicode object
        latin1 = tryEncoding(self.rawstr, 'latin-1')
        assert latin1
        assert type(latin1) == type(u'')
        
        # convert to koi8-r
        koi8r = recode_unicode(latin1, 'latin-1', 'koi8-r')
        assert type(koi8r) == type(u'')
        koi8r_raw = makeRaw(koi8r, 'koi8-r')
        assert type(koi8r_raw) == type('')
        assert koi8r_raw == self.rawstr
        
        # now convert back to latin-1
        new_latin1 = recode_unicode(koi8r, 'koi8-r', 'latin-1')
        assert type(new_latin1) == type(u'')
        raw_latin1 = makeRaw(new_latin1, 'latin-1')
        assert type(raw_latin1) == type('')
        assert raw_latin1 == self.rawstr
        assert raw_latin1 == koi8r_raw
        #print repr(rawstr)
        #print repr(koi8r_raw)
        #print repr(raw_latin1)

    def test_Convert8BittoUTF8(self):
        # test converting from koi8-r to utf-8 and back, verifying all bytes
        # remain correctly
        from encodings.koi8_r import decoding_table

        koi8_r = tryEncoding(self.rawstr, 'koi8-r')
        utf_8 = recode_unicode(koi8_r, 'koi8-r', 'utf-8')
        for index in range(len(decoding_table)):
            assert utf_8[index] == decoding_table[index]


class TestDetectFileEncoding(unittest.TestCase):
    def __init__(self, methodName='runTest'):
        unittest.TestCase.__init__(self, methodName)
        
        # We expect files to be relative to this test script.
        test_dir = dirname(dirname(__file__))
        self._dir = normpath(join(test_dir,
            "stuff/charsets/www.kostis.net/charsets"))

        self._enc = {}
        # get all the utf-8 files in this dir, and well recode them
        names = os.listdir(self._dir)
        for name in names:
            if not os.path.isfile(os.path.join(self._dir, name)):
                continue
            enc = name.split('.')[0]
            if decoderAvailable(enc):
                self._enc[enc] = name
            #else:
            #    print "Unsuppoted Encoding: %s"% name

    def _test_recode_raw_file(self, enc, name):
        path = os.path.join(self._dir, name)
        aStr = open(path, 'rb').read()
        try:
            nStr = recode_raw(aStr, 'utf-8', enc)
        except UnicodeError, e:
            return 0
        return 1
        
    def test_recodeRawUTF8Files(self):
        sys.stderr.write('\n')
        for enc, name in self._enc.items():
            ok = self._test_recode_raw_file(enc, name)
            if not ok:
                sys.stderr.write("    recoding %s FAILED\n" % name)

    def _test_recode_unicode_file(self, encoding, name):
        path = os.path.join(self._dir, name)
        aStr = open(path, 'rb').read()
        try:
            utf8unicode = tryEncoding(aStr, 'utf-8')
            # expect all files to be utf-8 formated
            if not utf8unicode:
                return 0
            
            # convert to encoding in raw form
            encoded = recode(utf8unicode, 'utf-8', encoding, raw=1)
            # convert back to utf-8 in raw form
            recoded = recode(encoded, encoding, 'utf-8', raw=1)
            # compare original raw utf-8 with new raw utf-8
            assert(recoded == aStr)
        except UnicodeError, e:
            return 0
        return 1
        
    def test_recodeUnicodeUTF8Files(self):
        sys.stderr.write('\n')
        for enc, name in self._enc.items():
            ok = self._test_recode_unicode_file(enc, name)
            if not ok:
                sys.stderr.write("    recoding %s FAILED\n" % name)


#---- mainline

def suite():
    suites = []
    suites.append( unittest.makeSuite(TestDetectEncoding) )
    suites.append( unittest.makeSuite(TestDetectFileEncoding) )
    suites.append( unittest.makeSuite(TestChangeEncoding) )
    return unittest.TestSuite(suites)

def test_main():
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite())

if __name__ == "__main__":
    __file__ = sys.argv[0] # won't be necessary in Python 2.3
    test_main()



