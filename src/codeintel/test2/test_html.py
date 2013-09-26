#!/usr/bin/env python
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
from codeintel2.environment import SimplePrefsEnvironment
from codeintel2.util import indent, dedent, banner, markup_text, unmark_text

from testlib import TestError, TestSkipped, TestFailed, tag
from citestsupport import CodeIntelTestCase, override_encoding



log = logging.getLogger("test")



class HTMLTestCase(CodeIntelTestCase):
    lang = "HTML"
    _ci_env_prefs_ = {
        "defaultHTMLDecl": "-//W3C//DTD HTML 4.01//EN",
    }

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

    @tag("bug99976")
    def test_completions_invalid_html(self):
        self.assertCompletionsInclude(
            dedent("""
                <html>
                    </foo>
                    <<|>
                </html>
            """),
            [("element", 'p'), ("element", 'div')])

    @tag("bug100250")
    def test_completions_dtd(self):
        sample = dedent("""
            <html>
                <body>
                    <<|>
                </body>
            </html>""")
        env = SimplePrefsEnvironment()
        buf, data = self._get_buf_and_data(sample, self.lang, env=env)

        # Test HTML4...
        env.set_pref("defaultHTMLDecl", "-//W3C//DTD HTML 4.01//EN")
        self.assertCompletionsInclude2(buf, data["pos"], [("element", "script")], unload=False)
        self.assertCompletionsDoNotInclude2(buf, data["pos"], [("element", "section")], unload=False)
        # Flip to HTML5...
        env.set_pref("defaultHTMLDecl", "-//W3C//DTD HTML 5//EN")
        self.assertCompletionsInclude2(buf, data["pos"], [("element", "script")], unload=False)
        self.assertCompletionsInclude2(buf, data["pos"], [("element", "section")], unload=False)
        # And back to HTML4 again
        env.set_pref("defaultHTMLDecl", "-//W3C//DTD HTML 4.01//EN")
        self.assertCompletionsInclude2(buf, data["pos"], [("element", "script")], unload=False)
        self.assertCompletionsDoNotInclude2(buf, data["pos"], [("element", "section")], unload=False)

    @tag("bug100557")
    @override_encoding("ascii")
    def test_unicode(self):
        self.assertCompletionsInclude(
            dedent(u"""
                <!DOCTYPE html>
                <html>
                    <body>
                        <a title="\u2603">
                            \u2603\u2603\u2603
                        </a>
                        <<|>
                    </body>
                </html>
            """),
            [("element", "p")])
