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
import codecs
import koUnicodeEncoding

from xpcom.server.enumerator import SimpleEnumerator
from xpcom import components, ServerException, nsError

class koEncodingHierarchyCategory:
    _com_interfaces_ = [components.interfaces.koIHierarchyItem]
    _reg_clsid_ = "{39d7c528-8d20-4752-be5a-4ea29eaea63d}"
    _reg_contractid_ = "@activestate.com/koEncodingHierarchyCategory;1"
    _reg_desc_ = "Information about an encoding category"
    def __init__(self, name, children):
        self.name = name
        self.children = []
        for child in children:
            if isinstance(child, koEncodingHierarchyCategory) or isinstance(child, koEncodingHierarchyEncodingInfo):
                self.children.append(child)
            else:
                self.children.append(apply(koEncodingHierarchyEncodingInfo,child))
                
    def get_available_types(self):
        return components.interfaces.koIHierarchyItem.ITEM_HAS_OBJECT

    def get_container(self):
        return len(self.children) > 0

    def getChildren(self):
        return self.children
    
class koEncodingHierarchyEncodingInfo:
    _com_interfaces_ = [components.interfaces.koIHierarchyItem]
    _reg_clsid_ = "{30a5c3ed-f97b-43dc-ba5a-b18c08a36b79}"
    _reg_contractid_ = "@activestate.com/koEncodingHierarchyEncodingInfo;1"
    _reg_desc_ = "Information about an encoding item"
    def __init__(self, *encodingArgs):
        self.encodingInfo = self.item_object = apply(koEncodingInfo,encodingArgs)
        self.container = 0
        self.available_types = components.interfaces.koIHierarchyItem.ITEM_HAS_OBJECT
        self.name = self.encodingInfo.friendly_encoding_name

class koEncodingInfo:
    _com_interfaces_ = [components.interfaces.koIEncodingInfo]
    _reg_clsid_ = "{fa786db7-7507-40e2-af53-a38ec2db0561}"
    _reg_contractid_ = "@activestate.com/koEncodingInfo;1"
    _reg_desc_ = "Information about a Unicode encoding"
    
    def __init__(self, pythonEncodingName, friendlyEncodingName, \
                 shortName, BOM, asciiSuperSet, fontspec):
        #print "koEncodingInfo ",fontspec
        self.python_encoding_name = pythonEncodingName
        self.friendly_encoding_name = friendlyEncodingName
        self.short_encoding_name = shortName
        self.byte_order_marker = BOM
        self.ascii_superset = asciiSuperSet
        self.fontspec = fontspec
        




class koEncodingServices:
    _com_interfaces_ = [components.interfaces.koIEncodingServices]
    _reg_clsid_ = "{3da9261d-b4e8-4a9e-bb1d-7d907eabcaf9}"
    _reg_contractid_ = "@activestate.com/koEncodingServices;1"
    _reg_desc_ = "Unicode Encoding Services"
    
    def __init__(self):
        self.lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"]\
                .getService(components.interfaces.koILastErrorService)
        self._globalPrefSvc = components.classes["@activestate.com/koPrefService;1"].\
                            getService(components.interfaces.koIPrefService)
        self._globalPrefs = self._globalPrefSvc.prefs
        self._encodingHierarchy =\
            koEncodingHierarchyCategory(
                'Root',
                # Python name, friendly name, short name, BOM, is ASCII-superset, fontspec
                [
                ('ascii', 'ASCII', 'ASCII', '', 1,'iso8859-1'),
                ('utf-8', 'UTF-8', 'UTF-8', codecs.BOM_UTF8, 1,'iso10646-1'),
                
                ('utf-16-be', 'UTF-16 (Big Endian)', 'UTF-16 (BE)', codecs.BOM_UTF16_BE, 0,'iso10646-1'),
                ('utf-16-le', 'UTF-16 (Little Endian)', 'UTF-16 (LE)', codecs.BOM_UTF16_LE, 0,'iso10646-1'),

                koEncodingHierarchyCategory(
                    'Eastern Europe',
                    [
                    ('iso8859-4', 'Baltic (Latin-4/ISO-8859-4)', '8859-4', '', 1,'iso8859-4'),
                    ('iso8859-13', 'Baltic (Latin-7/ISO-8859-13)', '8859-13', '', 1,'iso8859-13'),
                    ('cp1257', 'Baltic (CP-1257)', 'CP1257', '', 1,'cp1257'),
                    ('iso8859-2', 'Central European (Latin-2/ISO-8859-2)', '8859-2', '', 1,'iso8859-2'),
                    ('cp1250', 'Central European (CP-1250)', 'CP1250', '', 1,'cp1250'),
                    ('mac-latin2', 'Central European (Mac-Latin2)', 'Mac-Latin2', '', 1,'mac-latin2'),
                    ('iso8859-5', 'Cyrillic (ISO-8859-5)', '8859-5', '', 1,'iso8859-5'),
                    ('koi8-r', 'Cyrillic (KOI8-R)', 'KOI8-R', '', 1,'koi8-r'),
                    ('cp1251', 'Cyrillic (CP-1251)', 'CP1251', '', 1,'cp1251'),
                    ('mac-cyrillic', 'Cyrillic (Mac-Cyrillic)', 'Mac-Cyrillic', '', 1,'mac-cyrillic'),
                    ('iso8859-9', 'Turkish (Latin-5/ISO-8859-9)', '8859-9', '', 1,'iso8859-9'),
                    ('mac-turkish', 'Turkish (Mac-Turkish)', 'Mac-Turkish', '', 1,'mac-turkish')
                    ]
                ),

                koEncodingHierarchyCategory(
                    'Western Europe',
                    [
                    ('iso8859-1', 'Western European (Latin-1/ISO-8859-1)', 'Latin-1', '', 1,'iso8859-1'),
                    ('mac-roman', 'Western European (Mac-Roman)', 'Mac-Roman', '', 1,'mac-roman'),
                    ('iso8859-15', 'Western European (Latin-9/ISO-8859-15)', '8859-15', '', 1,'iso8859-15'),
                    ('cp1252', 'Western European (CP-1252)', 'CP1252', '', 1,'cp1252'),
                    ('iso8859-14', 'Celtic (Latin-8/ISO-8859-14)', '8859-14', '', 1,'iso8859-14'),
                    ('iso8859-7', 'Greek (ISO-8859-7)', '8859-7', '', 1,'iso8859-7'),
                    ('cp1253', 'Greek (CP-1253)', 'CP1253', '', 1,'cp1253'),
                    ('mac-greek', 'Greek (Mac-Greek)', 'Mac-Greek', '', 1,'mac-greek'),
                    ('iso8859-10', 'Nordic (Latin-6/ISO-8859-10)', '8859-10', '', 1,'iso8859-10'),
                    ('mac-iceland', 'Iceland (Mac-Iceland)', 'Mac-Iceland', '', 1,'mac-iceland'),
                    ('iso8859-4', 'Northern European (ISO-8859-4)', '8859-4', '', 1,'iso8859-4'),
                    ('iso8859-3', 'Southern European (ISO-8859-3)', '8859-3', '', 1,'iso8859-3')
                    ]
                ),

                koEncodingHierarchyCategory(
                    'Asia',
                    [
                    ('gb18030', "Simplified Chinese (GB18030)", 'GB18030', '', 1,'gb18030'),
                    ('gb2312', "Simplified Chinese (GB2312-1980)", 'GB2312-1980', '', 1,'gb2312'),
                    ('hz', 'Simplified Chinese (Hz)', 'Hz', '', 1,'hz'),
                    ('big5', 'Traditional Chinese (Big5)', 'Big5', '', 1,'big5'),
                    ('cp950', 'Traditional Chinese (Microsoft CP-950)', 'CP950', '', 1,'cp950'),
                    ('big5hkscs', 'Traditional Chinese (HKSCS)', 'HKSCS', '', 1,'big5hkscs'),

                    ('iso_2022_jp', 'Japanese (ISO-2022-JP)', 'ISO-2022-JP', '', 1, 'iso_2022_jp'),
                    ('shift_jis', 'Shift JIS', 'Shift JIS', '', 1,'shift_jis'),
                    ('shift_jis_2004', 'Shift JIS 2004', 'Shift JIS 2004', '', 1,'shift_jis_2004'),
                    ('shift_jisx0213', 'Shift JIS X 0208', 'Shift JIS X 0208', '', 1,'shift_jisx0213'),
                    ('cp932', 'Shift JIS (CP-932)', 'CP932', '', 1,'cp932'),

                    ('euc_jp', 'Japanese (EUC-JP)', 'EUC-JP', '', 1, 'euc_jp'),
                    ('euc_kr', 'Korean (EUC-KR)', 'EUC-KR', '', 1, 'euc_kr'),
                    ('cp949', 'Korean (UHC)', 'UHC', '', 1, 'cp949'),
                    ('johab', 'Korean (JOHAB)', 'JOHAB', '', 1, 'johab'),
                    ('iso_2022_kr', 'Korean (ISO-2022-KR)', 'ISO-2022-KR', '', 1, 'iso_2022_kr'),
                    
                    ('gbk', 'GBK (CP-936/GBK)', 'CP936/GBK', '', 1,'gbk'),
                    ]
                ),

                koEncodingHierarchyCategory(
                    'Middle East',
                    [
                    ('cp1255', 'Hebrew (CP-1255)', 'CP1255', '', 1,'cp1255'),
                    ('iso8859-8', 'Hebrew (ISO-8859-8)', '8859-8', '', 1,'iso8859-8'),
                    ('cp1256', 'Arabic (CP-1256)', 'CP1256', '', 1,'cp1256'),
                    ]
            )])
        self._encodingInfoList = []
        self._generateList(self._encodingInfoList, self._encodingHierarchy)

    def _generateList(self, infoList, hierarchyItem):
        if isinstance(hierarchyItem, koEncodingHierarchyEncodingInfo):
            infoList.append(hierarchyItem.encodingInfo)
        elif isinstance(hierarchyItem, koEncodingHierarchyCategory):
            for i in hierarchyItem.children:
                self._generateList(infoList, i)
        else:
            assert(0)

    def enumerateEncodings(self):
        return self._encodingInfoList
        
    def get_encoding_index(self, python_encoding_name):
        for i in range(0, len(self._encodingInfoList)):
            try:
                if codecs.lookup(self._encodingInfoList[i].python_encoding_name) == codecs.lookup(python_encoding_name):
                    return i
            except LookupError, e:
                pass

        return -1

    def get_canonical_python_encoding_name(self, python_encoding_name):
        index = self.get_encoding_index(python_encoding_name)
        if index == -1:
            return python_encoding_name
        else:
            return self._encodingInfoList[index].python_encoding_name
        
    def get_encoding_hierarchy(self):
        return self._encodingHierarchy
    
    def get_encoding_info(self, python_encoding_name):
        for encodingInfo in self._encodingInfoList:
            try:
                if codecs.lookup(encodingInfo.python_encoding_name) == codecs.lookup(python_encoding_name):
                    return encodingInfo
            except LookupError, e:
                # if we receive a bad encoding, try utf-8 instead
                python_encoding_name = 'utf-8'
                

        # It's not in our list of supported encodings but it is supported by Python so let's try to figure out
        # the information that we need.
        try:
            u'\ufeff'.encode(python_encoding_name)
            isUnicode = 1
        except UnicodeError:
            isUnicode = 0

        try:
            asciiSuperSet = 1
            for i in range(0,128):
                if unichr(i).encode(python_encoding_name) != chr(i):
                    asciiSuperSet = 0
                    break
            if isUnicode:
                fontspec = 'iso10646-1'
            else:
                fontspec = 'iso8859-1'
        except UnicodeError:
            asciiSuperSet = 0
            fontspec = '*-*'
                 
        return koEncodingInfo(python_encoding_name, \
                              python_encoding_name, \
                              python_encoding_name, \
                              '', asciiSuperSet, fontspec)
    
    def unicode(self, encoded_string, encoding, errors):
        try:
            unistring = unicode(encoded_string, encoding, errors)
        except Exception, ex:
            self.lastErrorSvc.setLastError(0, str(ex))
            raise ServerException(nsError.NS_ERROR_INVALID_ARG, str(ex))
        return unistring
    
    def encode(self, unicode_string, encoding, errors):
        try:
            decoded_string = unicode_string.encode(encoding, errors)
        except Exception, ex:
            self.lastErrorSvc.setLastError(0, str(ex))
            raise ServerException(nsError.NS_ERROR_INVALID_ARG, str(ex))
        return decoded_string

    def getUnicodeEncodedString(self, s):
        encoding_name = self._globalPrefs.getStringPref('encodingDefault')
        encoding = self.get_encoding_info(encoding_name).python_encoding_name
        unicodebuffer, encoding, bom =\
            koUnicodeEncoding.autoDetectEncoding(s, defaultEncoding=encoding)
        return unicodebuffer, encoding, bom

    def getUnicodeEncodedStringUsingOSDefault(self, s):
        encoding_name = sys.getfilesystemencoding()
        encoding = self.get_encoding_info(encoding_name).python_encoding_name
        unicodebuffer, encoding, bom =\
            koUnicodeEncoding.autoDetectEncoding(s, defaultEncoding=encoding)
        return unicodebuffer, encoding, bom
