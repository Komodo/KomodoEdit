# -*- coding: UTF-8 -*-

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

"""test src/python-sitelib/uriparse.py"""

import os, sys
import unittest
try:
    from uriparse import *
except ImportError:
    print "boom"
    pass # Allow testing without PyXPCOM to proceed.

class Case(object):
    def __init__(self, url, path=None):
        if path is None:
            path = url
        if sys.platform == "win32":
            self.url = "file:///C:" + url
            self.path = "C:" + path.replace("/", "\\")
        else:
            self.url = "file://" + url
            self.path = path

# The name "test_cases" is reserved by the test framework.
test_items = [
    Case("/Documents%20and%20Settings/test/My%20Documents/somefile.txt",
         "/Documents and Settings/test/My Documents/somefile.txt"),
    Case("/home/test/somefile.txt"),
    Case("/path/with%25embedded%25percents/somefile.txt",
        "/path/with%embedded%percents/somefile.txt"),
    Case("/path/space%20and%25percent/somefile.txt",
         "/path/space and%percent/somefile.txt"),
    # For these two, Komodo doesn't do urlquoting because there's no space or percent
    Case(u"/french/clean/élan/ça.txt"),
    Case(u"/greek/clean/Επιφάνεια/εργασίας/Φάκελος/myproject.pl"),
    
    # For these three urlquoting fails, and Komodo returns the original string
    Case(u"/greek/dirty/space/Επιφάνεια εργασίας/Φάκελος/myproject.pl"),
    Case(u"/greek/dirty/pct/Επιφάνεια%εργασίας/Φάκελος/myproject.pl"),
    Case(u"/greek/dirty/both/Επιφάνεια εργασίας % Φάκελος/myproject.pl"),
    ]
if sys.platform.startswith("win"):
    # Url quoting can handle latin1 chars (on Windows).
    # XXX: These tests fail on Linux, I suspect it's due to the underlying
    #      system encoding.
    test_items += [
        Case(u"/french/dirty/space/%E9lan%20%E9cole/%E7a.txt",
             u"/french/dirty/space/élan école/ça.txt"),
        Case(u"/french/dirty/pct/%E9lan%25%E9cole/%E7a.txt",
             u"/french/dirty/pct/élan%école/ça.txt"),
        Case(u"/french/dirty/both/%E9lan%20space%25%E9cole/%E7a.txt",
             u"/french/dirty/both/élan space%école/ça.txt"),
    ]
    

class URIParseTestCase(unittest.TestCase):
    def test_localPathToURI(self):
        for test_case in test_items:
            url = localPathToURI(test_case.path)
            self.failUnlessEqual(url, test_case.url,
                "localPathToURI(path=%s): expected\n%s, got\n%s\n" %
                (test_case.path, test_case.url, url))
 
    def test_URIToLocalPath(self):
        for test_case in test_items:
            path = URIToLocalPath(test_case.url)
            self.failUnlessEqual(path, test_case.path,
                "URIToLocalPath(url=%s): expected\n%s, got\n%s\n" %
                (test_case.url, test_case.path, path))






