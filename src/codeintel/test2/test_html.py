#!/usr/bin/env python
# Copyright (c) 2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

"""Test HTML codeintel support."""

import os
import sys
import re
from os.path import join, dirname, abspath, exists, basename
from glob import glob
from pprint import pprint, pformat
import unittest
import logging

from codeintel2.common import *
from codeintel2.util import indent, dedent, banner, markup_text, unmark_text

from testlib import TestError, TestSkipped, TestFailed, tag
from citestsupport import CodeIntelTestCase, init_xml_catalogs



log = logging.getLogger("test")



class HTMLTestCase(CodeIntelTestCase):
    lang = "HTML"
    _ci_env_prefs_ = {
        "defaultHTMLDecl": "-//W3C//DTD HTML 4.01//EN",
    }

    def setUp(self):
        super(HTMLTestCase, self).setUp()
        init_xml_catalogs()

    def _test_xhtml_completions_base_test(self, raw_content, expected):
        xhmltdoctypes = [
            # XHTML 1.0 Strict
            '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"\n "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">',
            # XHTML 1.0 Transitional
            '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"\n "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">',
            # XHTML 1.0 Frameset
            '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Frameset//EN"\n "http://www.w3.org/TR/xhtml1/DTD/xhtml1-frameset.dtd">',
        ]            
        for doctype in xhmltdoctypes:
            content = raw_content % doctype
            self.assertCompletionsInclude(content,expected)

    def _test_html_completions_base_test(self, raw_content, expected):
        htmldoctypes = [
            # HTML 4.01 Strict
            '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"\n "http://www.w3.org/TR/html4/strict.dtd">',
            # HTML 4.01 Transitional
            '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"\n "http://www.w3.org/TR/html4/loose.dtd">',
            '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">',
            
            # XXX the following DTD parsing fails.  frameset does not include
            # the tags our tests are running against, and 3.2/2.0 dtd is broken
            
            # HTML 4.01 Frameset
            #'<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Frameset//EN"\n "http://www.w3.org/TR/html4/frameset.dtd">',
            #'<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Frameset//EN">',
            # HTML 3.2
            #'<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">',
            # HTML 2.0
            #'<!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML//EN">',
            # No doctype
            '',
        ]
        for doctype in htmldoctypes:
            content = raw_content % doctype
            self.assertCompletionsInclude(content,expected)

    def test_completions_in_head(self):
        raw_content = dedent("""\
            %s
            <html>
            <head>
            <title>my title</title>

            <<|>

            </head>
            <body>
            </body>
            </html>
        """)
        self._test_xhtml_completions_base_test(
            raw_content, [("element", "style")])
        self._test_html_completions_base_test(
            raw_content, [("element", "style")])
        
    def test_completions_in_head_bug64997(self):
        raw_content = dedent("""\
            %s
            <html>
            <head>
            <<|>
        """)
        self._test_xhtml_completions_base_test(
            raw_content, [("element", "style")])
        self._test_html_completions_base_test(
            raw_content, [("element", "style")])
        
    def test_should_be_input_inside_form(self):
        # though common use is for input to be anywhere, it *is not valid*
        # html as defined by w3c, thus the div tag
        content = dedent("""\
            <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"
                "http://www.w3.org/TR/html4/strict.dtd">
            <html>
            <head> <title>my title</title> </head>
            <body>
                <form action="form_action.asp" method="get"><div>
                First name:
                <<|>
                </div></form>
            </body>
            </html>
        """)
        self.assertCompletionsInclude(content,
            [("element", "input")])

    def test_do_not_close_html_img(self):
        # Raised by Alex Fernandez on komodo-beta about k4b1.
        html_content = dedent("""\
            <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"
                "http://www.w3.org/TR/html4/strict.dtd">
            <html>
            <head> <title>my title</title> </head>
            <body>
                <p>blah blah...
                <img src="somefile.jpg" alt="blah">
                </<|>p>
            </body>
            </html>
        """)
        self.assertCompletionsDoNotInclude(html_content, [("element", "img>")])
        # invalid XHTML usage, without the xml declaration, it is treated like
        # html from a parser point of view, so close tags are handled differently
        html_content = dedent("""\
            <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
                "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
            <html>
            <head> <title>my title</title> </head>
            <body>
                <p>blah blah...
                <img src="somefile.jpg" alt="blah">
                </<|>
        """)
        self.assertCompletionsDoNotInclude(html_content, [("element", "img>")])

    def test_close_xhtml_img(self):
        xhtml_content = dedent("""<?xml version="1.0"?>
            <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
                "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
            <html>
            <head> <title>my title</title> </head>
            <body>
                <p>blah blah...
                <img src="somefile.jpg" alt="blah">
                </<|>img>
                </p>
            </body>
            </html>
        """)
        self.assertCompletionsAre(xhtml_content,
            [("element", "img>")])

    @tag("bug66149")
    def test_attr_enum_cpln(self):
        self.assertCompletionsAre(
            dedent("""
                <?xml version="1.0"?>
                <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
                    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
                <html dir="<|>>
                </html>
            """),
            [("attribute_value", 'ltr'), ("attribute_value", 'rtl')])
        self.assertCompletionsAre(
            dedent("""
                <?xml version="1.0"?>
                <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
                    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
                <html dir='<|>>
                </html>
            """),
            [("attribute_value", "ltr"), ("attribute_value", "rtl")])


