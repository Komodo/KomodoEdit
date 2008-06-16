#!/usr/bin/env python
# Copyright (c) 2006-2008 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

"""Test hooks functionality in codeintel."""

import os
import sys
import re
from os.path import join, dirname, abspath, exists, basename
import unittest
from pprint import pprint
import logging

from codeintel2.common import *
from codeintel2.util import indent, dedent, banner, markup_text, unmark_text

from testlib import TestError, TestSkipped, TestFailed, tag
from citestsupport import CodeIntelTestCase, writefile



log = logging.getLogger("test")


class FooTestCase(CodeIntelTestCase):
    test_dir = join(os.getcwd(), "tmp")
    _ci_extra_module_dirs_ = [
        join(dirname(__file__), "bits", "foo_hooks"),
    ]

    def test_via_scan(self):
        content = dedent("""\
            class Blam1:
                def pow(self, bb):
                    "pow man!"
                    pass
                def pif(self, aa):
                    pass
            
            # FooHookHandler adds top-level "Foo" class.
            f = Foo()
            f.<|>foo
        """)
        self.assertCompletionsInclude(content,
            [("function", "foo")],
            lang="Python")

    def test_via_db(self):
        test_dir = join(self.test_dir, "test_foo_hooks_via_db")
        path = join(test_dir, "blam2.py")
        content, positions = unmark_text(dedent("""\
            class Blam2:
                def pow(self, bb):
                    "pow man!"
                    pass
                def pif(self, aa):
                    pass
            
            # FooHookHandler adds top-level "Foo" class.
            f = Foo()
            f.<1>foo
        """))
        writefile(path, content)

        buf = self.mgr.buf_from_path(path, lang="Python")
        buf.scan_if_necessary()
        self.assertCompletionsInclude2(buf, positions[1],
            [("function", "foo")])



#---- mainline

if __name__ == "__main__":
    unittest.main()


