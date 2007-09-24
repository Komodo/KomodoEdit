# Copyright (c) 2000-2007 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

"""test src/python-sitelib/uriparse.py"""

import os, sys
import unittest
try:
    from uriparse import *
except ImportError:
    print "boom"
    pass # Allow testing without PyXPCOM to proceed.


class URIParseTestCase(unittest.TestCase):
    def test_localPathToURI(self):
        if sys.platform == "win32":
            url = "file:///C:/Documents%20and%20Settings/test/My%20Documents/somefile.txt"
            path = r"C:\Documents and Settings\test\My Documents\somefile.txt"
        else:
            url = "file:///home/test/somefile.txt"
            path = "/home/test/somefile.txt"

        assert localPathToURI(path) == url
 
    def test_URIToLocalPath(self):
        if sys.platform == "win32":
            url = "file:///C:/Documents%20and%20Settings/test/My%20Documents/somefile.txt"
            path = r"C:\Documents and Settings\test\My Documents\somefile.txt"
        else:
            url = "file:///home/test/somefile.txt"
            path = "/home/test/somefile.txt"

        assert URIToLocalPath(url) == path






