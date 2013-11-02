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

"""Test UDL-specific parts of codeintel."""

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
from citestsupport import CodeIntelTestCase



log = logging.getLogger("test")


class GeneralTestCase(CodeIntelTestCase):
    def test_lang_from_style(self):
        # Ensure that the the SCE_UDL_ constants haven't changed such that
        # the UDLBuffer.udl_family_from_style() function is broken.
        from SilverCity import ScintillaConstants
        from codeintel2.udl import UDLBuffer
        
        class MyUDLBuffer(UDLBuffer):
            lang = "My"
            m_lang = "M"
            css_lang = "CSS"
            csl_lang = "CSL"
            ssl_lang = "SSL"
            tpl_lang = "TPL"
        buf = MyUDLBuffer(None, None)
        langs = "M CSS CSL SSL TPL".split()
        for lang in langs:
            const_names = [n for n in dir(ScintillaConstants)
                           if n.startswith("SCE_UDL_%s_" % lang)]
            for const_name in const_names:
                const = getattr(ScintillaConstants, const_name)
                error_msg = (
                    "UDLBuffer.lang_from_style(ScintillaConstants.%s) "
                    "!= %r: the UDL lexer constants have changed, UDLBuffer "
                    "needs to be updated" % (const_name, lang))
                try:
                    actual_lang = buf.lang_from_style(const)
                except ValueError, ex:
                    self.fail(error_msg)
                else:
                    self.assertEqual(actual_lang, lang,
                                     error_msg)

    def test_is_udl_X_style(self):
        # Ensure that the the SCE_UDL_ constants haven't changed such that
        # the udl.is_udl_*_style() functions are broken.
        from SilverCity import ScintillaConstants
        from codeintel2 import udl

        checker = {
            "M": udl.is_udl_m_style,
            "CSS": udl.is_udl_css_style,
            "CSL": udl.is_udl_csl_style,
            "SSL": udl.is_udl_ssl_style,
            "TPL": udl.is_udl_tpl_style,
        }

        const_names = [n for n in dir(ScintillaConstants)
                       if n.startswith("SCE_UDL_")]
        for const_name in const_names:
            if const_name == "SCE_UDL_UPPER_BOUND":
                continue
            const = getattr(ScintillaConstants, const_name)
            udl_family = const_name[len("SCE_UDL_"):].split('_', 1)[0]
            checker_name = "is_udl_%s_style" % udl_family.lower()
            checker_func = getattr(udl, checker_name)
            self.failUnless(checker_func(const),
                "udl.%s(ScintillaConstants.%s) returned False: the UDL lexer "
                "constants have changes, udl.py:%s() must be updated"
                % (checker_name, const_name, checker_name))



class RHTMLTestCase(CodeIntelTestCase):
    """Use RHTML for this test case. Any UDL-based XML-y/HTML-y lang
    would have done.
    """
    lang = "RHTML"

    def test_udl_family_transitions(self):
        # There are subtleties with UDL family transitions. For example,
        # getting "xml-complete-end-tag" for the "</script>" to end a
        # client-side language section or for the "</style>" to end a CSS
        # section: sometimes current styling is in the markup (M) family
        # and sometimes in the CSS or CSL family.

        #--- Transition from CSS to XML
        self.assertTriggerMatches("<style>foo { color: blue; }</<|>",
                                  name="html-complete-end-tag")
        # but not in a comment
        self.assertNoTrigger("<style>/*</<|>")
        self.assertNoTrigger("<style>/* blah </<|>blah")
        # but not in a string
        self.assertNoTrigger("<style>foo { background-image: url('</<|>")
        self.assertNoTrigger("<style>foo { background-image: url('blah</<|>blah")
        
        #--- Transition from JavaScript to XML
        self.assertTriggerMatches("<script>blah blah </<|>",
                                  name="html-complete-end-tag")
        # but not in a string
        self.assertNoTrigger("<script>var foo = '</<|>")
        self.assertNoTrigger("<script>var foo = 'blah</<|>blah")
        # but not in a comment
        self.assertNoTrigger("<script> /*</<|>")
        self.assertNoTrigger("<script> /* blah </<|> blah */")
        self.assertNoTrigger("<script> //</<|>")
        self.assertNoTrigger("<script> // blah </<|> blah */")
        # but not in a regex literal
        self.assertNoTrigger("<script>var foo = /</<|>;")
        self.assertNoTrigger("<script>var foo = /blah</<|>;")

    @tag("bug101280")
    def test_udl_xml_no_scripting(self):
        """Test that UDL XML/HTML parsing skips over non-markup sections"""
        buf, _ = self._get_buf_and_data(u"""
            <html>
                <title>
                    The Unicode here is used to bloat out the offsets in case
                    We're using character positions instead of byte positions
                    \u016E\u0273\u0269\u00e7\u24de\u02a0\u212f
                    \u016E\u0273\u0269\u00e7\u24de\u02a0\u212f
                    \u016E\u0273\u0269\u00e7\u24de\u02a0\u212f
                    \u016E\u0273\u0269\u00e7\u24de\u02a0\u212f
                    \u016E\u0273\u0269\u00e7\u24de\u02a0\u212f
                    \u016E\u0273\u0269\u00e7\u24de\u02a0\u212f
                    \u016E\u0273\u0269\u00e7\u24de\u02a0\u212f
                </title>
                <body>
                    <%
                        # <ruby><expression/></ruby>
                    %>
                    <p>
                        \u016E\u0273\u0269\u00e7\u24de\u02a0\u212f
                        \u016E\u0273\u0269\u00e7\u24de\u02a0\u212f
                        \u016E\u0273\u0269\u00e7\u24de\u02a0\u212f
                        \u016E\u0273\u0269\u00e7\u24de\u02a0\u212f
                        \u016E\u0273\u0269\u00e7\u24de\u02a0\u212f
                        \u016E\u0273\u0269\u00e7\u24de\u02a0\u212f
                        \u016E\u0273\u0269\u00e7\u24de\u02a0\u212f
                        <%
                            # <ruby><expression/></ruby>
                        %>
                    </p>
                </body>
            </html>
            """, self.lang)
        for node in buf.xml_tree.nodes:
            self.assertNotIn(node.tag, ("ruby", "expression"),
                             "Got unexpected element %s at line %s column %s" %
                             (node.tag, node.start[0], node.start[1]))

#---- mainline

if __name__ == "__main__":
    unittest.main()


