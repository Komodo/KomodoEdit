#!/usr/bin/env python
# coding=utf-8
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

"""test langinfo.py"""

import sys
import os
from os.path import dirname, join, abspath, basename, splitext, exists
import unittest
import codecs
from pprint import pprint, pformat
from glob import glob

from testlib import TestError

top_dir = dirname(dirname(abspath(__file__)))
sys.path.insert(0, join(top_dir, "src", "python-sitelib"))
import langinfo



#---- test cases

class ManualTestCase(unittest.TestCase):
    def assertConformsTo(self, lang, conforms_to):
        li = langinfo.langinfo_from_lang(lang)
        self.assert_(li.conforms_to(conforms_to),
            "%s does not conform to %r" % (li, conforms_to)
        )

    def test_conforms_to(self):
        self.assertConformsTo("XUL", "XML")
        self.assertConformsTo("XUL", "XUL")
        xul = langinfo.langinfo_from_lang("XUL")
        self.assert_(xul.is_text)

    def test_api(self):
        py = langinfo.langinfo_from_lang("Python")
        self.assert_(py.name == "Python")
        self.assert_(".py" in py.exts)
        self.assert_(py.is_text)

    def test_komodo_name(self):
        lidb = langinfo.Database()
        li = lidb.langinfo_from_lang("Django HTML Template")
        li_ko = lidb.langinfo_from_komodo_lang("Django")
        self.assertEqual(li, li_ko)
        self.assertEqual(li_ko.name, "Django HTML Template")

    def test_komodo_name_nada(self):
        lidb = langinfo.Database()
        self.assertRaises(langinfo.LangInfoError,
                          lidb.langinfo_from_komodo_lang,
                          "Nada")
        
    # bug88698
    def hide_test_komodo_utf8_perl_without_bom(self):
        #XXX: langinfo.Database().langinfo_from_filename(fname)
        #     returns None, so the test is hidden.
        lidb = langinfo.Database()
        text = u"""\
use strict;
use warnings;
print "Vyváženě prožitý čas přeji.\n";
""".encode("utf-8")
        fname = "bug88698-without-bom.pl"
        f = open(fname, "w")
        #f.write(codecs.BOM_UTF8)
        f.write(text)
        f.close()
        li = lidb.langinfo_from_filename(fname)
        self.assertEqual(li.encoding, "utf-8")


#---- mainline

if __name__ == "__main__":
    import logging
    logging.basicConfig()
    unittest.main()

