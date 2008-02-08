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
import tempfile

from xpcom import components, COMException
from testlib import tag

import uriparse



class URIParseTestCase(unittest.TestCase):
    relative = [
        # base,      relative,               full,                  common
        (r'c:\atest',   r''        ,            r'c:\atest',            r'c:\atest'),
        (r'c:\btest',   r'test.txt',            r'c:\btest\test.txt',   r'c:\btest'),
        ( '/ctest',      '/ctesting/file.txt',    '/ctesting/file.txt',   ''),
        (r'c:\dtest',   r'c:\dtesting\file.txt', r'c:\dtesting\file.txt', 'c:'),
        (r'd:\etest',   r'c:\etesting\file.txt', r'c:\etesting\file.txt', ''),
        # Test perfect match with and without end-slashes
        (r'c:\ftest',   r'',                    r'c:\ftest',            r'c:\ftest'),
        ( 'c:\\gtest\\', r'',                   r'c:\gtest',            r'c:\gtest'),
        ( 'c:\\htest\\', r'',                    'c:\\htest\\',          'c:\\htest\\'),
        ( 'c:\\h2test', r'',                    'c:\\h2test\\',          'c:\\h2test\\'),
        ]
    if sys.platform == "win32":
        relative += [
        # Same as previous three, but ignoring case on Windows
        (r'c:\itest',  r'',                    r'C:\iTest',            r'C:\iTest'),
        ( 'c:\\jtest\\',r'',                    r'C:\jTest',            r'C:\jTest'),
        ( 'c:\\ktest\\',r'',                     'C:\\kTest\\',            'C:\\kTest\\'),
        ( 'c:\\k2test',r'',                     'C:\\k2Test\\',            'C:\\k2Test\\'),
        ]
    full_relativize = [
        ('/home/shanec/test/somepath','../bad/a:b','/home/shanec/test/bad/a:b','/home/shanec/test'),
        ('/test/a/b','../testing/file.txt','/test/a/testing/file.txt', '/test/a'),
        ('/home/shanec/test/somepath/anotherpath/andyetanother','../../../bad/a:b','/home/shanec/test/bad/a:b','/home/shanec/test'),
        (r'c:\test\a\b',r'..\testing\file.txt',r'c:\test\a\testing\file.txt', r'c:\test\a'),
    ]

    def __init__(self, methodName):
        unittest.TestCase.__init__(self, methodName)
        initSvc = components.classes["@activestate.com/koInitService;1"] \
                      .getService(components.interfaces.koIInitService)
        initSvc.setEncoding()
        
        self.__file = components.classes["@activestate.com/koFileEx;1"] \
                      .createInstance(components.interfaces.koIFileEx)

    def failUnlessSamePath(self, p1, p2):
        _p1 = p1.replace('\\','/')
        _p2 = p2.replace('\\','/')
        self.failUnlessEqual(_p1, _p2, "%r != %r"%(p1,p2))

    if sys.platform == "win32":
        def test_localpaths(self):
            paths = [
                ("path", "Normal windows local path",
                        r"c:\test\test.txt", "file:///c:/test/test.txt"),
                ("path", "Windows UNC path",
                        r"\\planer\d\trentm\tmp\foo.txt", "file://planer/d/trentm/tmp/foo.txt"),
            ]
            for test in paths:
                uri = uriparse.localPathToURI(test[2].replace("\\","/"))
                self.failUnlessSamePath(uri, test[3].replace("\\","/"))

        def test_urls(self):
            urls = [
                ("url",  "Windows UNC URI (2 slashes)", "file://planer/d/trentm/tmp/foo.txt",
                        r"\\planer\d\trentm\tmp\foo.txt"),
                ("url",  "Windows UNC URI (5 slashes)", "file://///planer/d/trentm/tmp/foo.txt",
                        r"\\planer\d\trentm\tmp\foo.txt"),
                ("url",  "File URI with spaces", "file://breakfast/spam and eggs.txt",
                        r"\\breakfast\spam and eggs.txt"),
                #("url",  "Windows UNC URI (1 slashes)", "file:/planer/d/trentm/tmp/foo.txt"),
                #("url",  "Windows UNC URI (3 slashes)", "file:///planer/d/trentm/tmp/foo.txt"),
                #("url",  "Windows UNC URI (4 slashes)", "file:////planer/d/trentm/tmp/foo.txt"),
            ]
            for test in urls:
                path = uriparse.URIToLocalPath(test[2])
                self.failUnlessSamePath(path,test[3])

    def test_relativize(self):
        for base, rel, fullpath, common in self.relative:
            path = uriparse.RelativizeURL(base, fullpath)
            self.failUnlessSamePath(path, rel)

    def test_UNrelativize(self):
        import URIlib
        relative = self.relative + self.full_relativize
        for base, rel, fullpath, common in relative:
            URI = uriparse.UnRelativizeURL(base, rel)
            fullURI = URIlib.URIParser(URI)
            # We need to canonicalize the result from unrelativize
            # compared to the original full path we expect to see.
            if fullpath[-1] in ('/', '\\'):
                fullpath = fullpath[:-1]
            self.failUnlessSamePath(os.path.normcase(fullURI.path), os.path.normcase(fullpath))
            

class _dummyPrefsClass(object):
    def __init__(self, string_prefs=None):
        self.parent = None
        if string_prefs is None:
            self.string_dict = {}
        else:
            self.string_dict = string_prefs
    # XXX: What does PrefHere do?
    def hasPrefHere(self, pref_name):
        return pref_name in self.string_dict
    def hasStringPref(self, pref_name):
        return pref_name in self.string_dict
    def getStringPref(self, pref_name):
        return self.string_dict.get(pref_name, "")

class URIMappingTestCase(unittest.TestCase):
    def test_getMappedURI(self):
        mappingdata_for_mappedPaths = {
            "": {
                "file:///tmp/file1.txt":        "file:///tmp/file1.txt",
                "http://server/tmp/file2.txt":  "http://server/tmp/file2.txt",
                "file:///f.c":                  "file:///f.c",
                "sftp://remote/tmp/file3.txt":  "sftp://remote/tmp/file3.txt",
                "C:\\tmp\\file4.txt":           "C:\\tmp\\file4.txt",
                },
            "http://server/tmp##/tmp::"\
            "sftp://remote##/remote": {
                "file:///tmp/file1.txt":        "file:///tmp/file1.txt",
                "http://server/tmp/file2.txt":  "file:///tmp/file2.txt",
                "file:///f.c":                  "file:///f.c",
                "sftp://remote/tmp/file3.txt":  "file:///remote/tmp/file3.txt",
                "C:\\tmp\\file4.txt":           "C:\\tmp\\file4.txt",
                },
        }
        for mappedPath, mappingData in mappingdata_for_mappedPaths.items():
            prefs = _dummyPrefsClass({"mappedPaths": mappedPath})
            for uri, expected_uri in mappingData.items():
                mapped_uri = uriparse.getMappedURI(uri, prefs)
                self.failUnlessEqual(mapped_uri, expected_uri,
                                     "Mapped URI was not expected: %r != %r" %
                                     (mapped_uri, expected_uri))

    def test_getMappedPath(self):
        mappingdata_for_mappedPaths = {
            "": {
                "/tmp/file1.txt":         "/tmp/file1.txt",
                "/server/tmp/file2.txt":  "/server/tmp/file2.txt",
                "/f.c":                   "/f.c",
                "/remote/tmp/file3.txt":  "/remote/tmp/file3.txt",
                "C:\\tmp\\file4.txt":     "C:\\tmp\\file4.txt",
                },
            "http://server/tmp##/tmp::"\
            "sftp://remote##/remote": {
                "/tmp/file1.txt":         "http://server/tmp/file1.txt",
                "/server/tmp/file2.txt":  "/server/tmp/file2.txt",
                "/f.c":                   "/f.c",
                "/remote/tmp/file3.txt":  "sftp://remote/tmp/file3.txt",
                "C:\\tmp\\file4.txt":     "C:\\tmp\\file4.txt",
                },
        }
        for mappedPath, mappingData in mappingdata_for_mappedPaths.items():
            prefs = _dummyPrefsClass({"mappedPaths": mappedPath})
            for path, expected_uri in mappingData.items():
                mapped_uri = uriparse.getMappedPath(path, prefs)
                self.failUnlessEqual(mapped_uri, expected_uri,
                                     "Mapped URI was not expected: %r != %r" %
                                     (mapped_uri, expected_uri))

    def test_getMappedPathForHost(self):
        mappingdata_for_mappedPaths = {
            "": ({
                "/tmp/file1.txt":         "/tmp/file1.txt",
                "/server/tmp/file2.txt":  "/server/tmp/file2.txt",
                "/f.c":                   "/f.c",
                "/remote/tmp/file3.txt":  "/remote/tmp/file3.txt",
                "C:\\tmp\\file4.txt":     "C:\\tmp\\file4.txt",
                },
                ""),
            "http://server/tmp##/tmp::"\
            "sftp://remote##/remote": ({
                "/tmp/file1.txt":         "http://server/tmp/file1.txt",
                "/server/tmp/file2.txt":  "/server/tmp/file2.txt",
                "/f.c":                   "/f.c",
                "/remote/tmp/file3.txt":  "/tmp/file3.txt",
                "C:\\tmp\\file4.txt":     "C:\\tmp\\file4.txt",
                },
                "server"),
            "http://server/tmp##/tmp::"\
            "sftp://remote##/remote": ({
                "/tmp/file1.txt":         "/tmp/file1.txt",
                "/server/tmp/file2.txt":  "/server/tmp/file2.txt",
                "/f.c":                   "/f.c",
                "/remote/tmp/file3.txt":  "sftp://remote/tmp/file3.txt",
                "C:\\tmp\\file4.txt":     "C:\\tmp\\file4.txt",
                },
                "remote"),
        }
        for mappedPath, mappingData in mappingdata_for_mappedPaths.items():
            mappingData, host = mappingData
            prefs = _dummyPrefsClass({"mappedPaths": mappedPath})
            for path, expected_uri in mappingData.items():
                mapped_uri = uriparse.getMappedPath(path, prefs, host)
                self.failUnlessEqual(mapped_uri, expected_uri,
                                     "Mapped URI was not expected: %r != %r" %
                                     (mapped_uri, expected_uri))

    @tag("knownfailure")
    def test_URIUnmapping(self):
        # Testcase to show where the current mapped uri system falls down
        mappingdata_for_mappedPaths = {
            "": {
                "file://myserver/tmp/file1.txt":  "file://myserver/tmp/file1.txt",
            },
            "file://myserver/tmp##file://C:/tmp": {
                "file://myserver/tmp/file1.txt":  "file:///C:/tmp/file1.txt",
            },
            "file://myserver/tmp##C:\\tmp": {
                "file://myserver/tmp/file1.txt":  "file:///C:/tmp/file1.txt",
            },
        }
        for mappedPath, mappingData in mappingdata_for_mappedPaths.items():
            prefs = _dummyPrefsClass({"mappedPaths": mappedPath})
            for path, expected_uri in mappingData.items():
                mapped_uri = uriparse.getMappedURI(path, prefs)
                self.failUnlessEqual(mapped_uri, expected_uri,
                                     "Mapped URI was not expected: %r != %r (mappedPath: %r)" %
                                     (mapped_uri, expected_uri, mappedPath))
                unmapped_path = uriparse.getMappedPath(mapped_uri, prefs)
                self.failUnlessEqual(unmapped_path, path,
                                     "Mapped URI was not unmapped correctly: %r != %r (mappedPath: %r)" %
                                     (unmapped_path, path, mappedPath))


#---- mainline

def suite():
    testsuite1 = unittest.makeSuite(Test_uriparse)
    testsuite2 = unittest.makeSuite(Test_URIMapping)
    return unittest.TestSuite([testsuite1, testsuite2])

def test_main():
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite())

if __name__ == "__main__":
    __file__ = os.path.abspath(sys.argv[0]) # won't be necessary in Python 2.3
    test_main()

