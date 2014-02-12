#!python
# Copyright (c) 2009 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

# To run: bk test loadSchemeFromURI
# Requires availabililty of komodo.nas1.activestate.com web srver
# The catchBadURI test will display a server exception, but should still pass.

import os
from os.path import isdir, dirname, join, isfile, normpath
import sys
import unittest
import re
import logging

from xpcom import components, ServerException, nsError
from xpcom.server.enumerator import SimpleEnumerator

log = logging.getLogger("test_loadSchemeFromURI")
#log.setLevel(logging.DEBUG)

class LoadSchemeTestCase(unittest.TestCase):
    schemeService = components.classes['@activestate.com/koScintillaSchemeService;1'].getService()
    koDirs = components.classes["@activestate.com/koDirs;1"].\
             getService(components.interfaces.koIDirs)
    schemeDir = os.path.join(koDirs.userDataDir, 'schemes')
    uriBase = "http://komodo.nas1.activestate.com/extras/tests/ksfimport/"
    
    def test_works(self):
        self.assertTrue(True)

    def test_catchBadSchemeName(self):
        uri = os.path.join(self.schemeDir, "Default.ksf")
        self.assertRaises(Exception,
                          self.schemeService.loadSchemeFromURI,
                          uri, "!#@$%*")
        
    def test_catchBadURI(self):
        uri = os.path.join(self.schemeDir, 'no', 'such', 'dirs', "Default.ksf")
        self.assertRaises(Exception,
                          self.schemeService.loadSchemeFromURI,
                          uri, 'test.ksf')

    def test_dangerousContent(self):
        uri = self.uriBase + "dangerous.ksf"
        fname = "blatz.ksf"
        self.assertRaises(Exception,
                          self.schemeService.loadSchemeFromURI,
                          uri, fname)
        
    def test_okContent(self):
        uri = self.uriBase + "ok_eric.ksf"
        fname = "shOUld__nEvEr__bE__A__vAlId__schEmE_namE.ksf"
        newPath = os.path.join(self.schemeDir, fname)
        if os.path.exists(newPath):
            os.remove(newPath)
        res = self.schemeService.loadSchemeFromURI(uri, fname)
        self.assertTrue(os.path.exists(newPath))
        os.unlink(newPath)
        self.assertFalse(os.path.exists(newPath))

    def test_invalidContent(self):
        fname = "__dAta__lo.adSchemeFromURI_invalidContent.ksf"
        fullpath = os.path.join(os.getcwd(), fname)
        fd = open(fname, 'w')
        fd.write("This is not valid 'Python")
        fd.close()
        self.assertRaises(Exception,
                          self.schemeService.loadSchemeFromURI,
                          fullpath, fname)
        self.assertTrue(os.path.exists(fullpath))
        os.unlink(fullpath)
        os.unlink(os.path.join(self.schemeDir, fname))

    def test_invalidBaseName(self):
        fname = "__bad-name:__()"
        fullpath = os.path.join(os.getcwd(), fname)
        self.assertRaises(Exception,
                          self.schemeService.loadSchemeFromURI,
                          fullpath, fname)
