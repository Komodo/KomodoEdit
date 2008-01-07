#!/usr/bin/env python
# Copyright (c) 2005-2007 ActiveState Corp.
# Author:
#   Trent Mick (TrentM@ActiveState.com)

"""test langinfo.py"""

import sys
import os
from os.path import dirname, join, abspath, basename, splitext, exists
import unittest
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




#---- mainline

if __name__ == "__main__":
    import logging
    logging.basicConfig()
    unittest.main()

