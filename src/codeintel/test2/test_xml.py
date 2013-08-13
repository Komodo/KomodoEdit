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

"""Test XML codeintel support."""

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



#---- globals

log = logging.getLogger("test")

xmlprefix = """<?xml version="1.0"?>
"""



#---- the test cases

class XULTestCase(CodeIntelTestCase):
    lang = "XUL"

    def test_trg_from_pos(self):
        # Tests for markup(XML) mode in UDL files.
        self.assertTriggerMatches(xmlprefix+"<<|>", name="xml-complete-tags-and-namespaces")
        self.assertNoTrigger(xmlprefix+"<![CDATA[ <<|>")
        self.assertNoTrigger(xmlprefix+"<!DOCTYPE <|>")
        self.assertNoTrigger(xmlprefix+"<?<|>")
        self.assertTriggerMatches(xmlprefix+"<!<|>", name="xml-complete-gt-bang")
        self.assertTriggerMatches(xmlprefix+"<ns:<|>", name="xml-complete-ns-tags")
        self.assertTriggerMatches(xmlprefix+"<ns:name <|>", name="xml-complete-tag-attrs")
        # The second ":" is ignored, treated like a tagname char
        self.assertNoTrigger(xmlprefix+"<ns:name:<|>")
        self.assertTriggerMatches(xmlprefix+"<ns:name: <|>", name="xml-complete-tag-attrs")
        self.assertTriggerMatches(xmlprefix+"<elt <|>", name="xml-complete-tag-attrs")
        # Erroneous XML here, but fallback is to stay in start-tag mode.
        self.assertTriggerMatches(xmlprefix+"<ns: <|>", name="xml-complete-tag-attrs")
        self.assertTriggerMatches(xmlprefix+"<ns:elt <|>", name="xml-complete-tag-attrs")
        self.assertTriggerMatches(xmlprefix+"<ns:elt attr1='val1' <|>", name="xml-complete-tag-attrs")
        self.assertTriggerMatches(xmlprefix+"<ns:elt attr2=\"val2\" <|>", name="xml-complete-tag-attrs")
        #self.assertTriggerMatches("<ns:elt attr3=val1 <|>", name="xml-complete-tag-attrs")
        self.assertTriggerMatches(xmlprefix+"<ns:elt\t<|>", name="xml-complete-tag-attrs")
        self.assertTriggerMatches(xmlprefix+"<ns:elt\n<|>", name="xml-complete-tag-attrs")
        #self.assertTriggerMatches("<ns:elt attr4=val1\t<|>", name="xml-complete-tag-attrs")
        #self.assertTriggerMatches("<ns:elt attr2=\"val2\" attr3=val1\t<|>", name="xml-complete-tag-attrs")
        #self.assertTriggerMatches("<ns:elt attr2=\"val2\" attr3=val1\n<|>", name="xml-complete-tag-attrs")
        
        # Attributes
        self.assertTriggerMatches(xmlprefix+"<x:foo y:<|>", name="xml-complete-ns-tags-attrs")
        self.assertNoTrigger(xmlprefix+"<x:foo ns:part1:<|>")
        
        # Attribute values
        self.assertNoTrigger(xmlprefix+"<x a=<|>")
        self.assertTriggerMatches(xmlprefix+"<x a='<|>",
                                  name="xml-complete-attr-enum-values")
        self.assertTriggerMatches(xmlprefix+"<x a=\"<|>",
                                  name="xml-complete-attr-enum-values")
        self.assertTriggerMatches(xmlprefix+"<x ns:a='<|>",
                                  name="xml-complete-attr-enum-values")
        self.assertTriggerMatches(xmlprefix+"<x ns:a=\"<|>",
                                  name="xml-complete-attr-enum-values")
        self.assertTriggerMatches(xmlprefix+"<x ns:a:='<|>",
                                  name="xml-complete-attr-enum-values")
        self.assertTriggerMatches(xmlprefix+"<x ns:a:=\"<|>",
                                  name="xml-complete-attr-enum-values")
        self.assertTriggerMatches(xmlprefix+"<x ns:a:b='<|>",
                                  name="xml-complete-attr-enum-values")
        self.assertTriggerMatches(xmlprefix+"<x ns:a:b=\"<|>",
                                  name="xml-complete-attr-enum-values")
        self.assertNoTrigger(xmlprefix+"<x a='val'<|>")
        self.assertNoTrigger(xmlprefix+"<x a=\"val\"<|>")
        
        # Namespace URIs (with commonly used prefixes)
        
        self.assertTriggerMatches(xmlprefix+"<x xmlns:<|>",
                                  name="xml-complete-well-known-ns")
        self.assertTriggerMatches(xmlprefix+"<x xmlns:pfx1='urn:bogus' xmlns:<|>",
                                  name="xml-complete-well-known-ns")
        
        # End tags
        self.assertTriggerMatches(xmlprefix+"<x></<|>",
                                  name="xml-complete-end-tag")
        self.assertTriggerMatches(xmlprefix+"<x</<|>",
                                  name="xml-complete-end-tag")
        self.assertTriggerMatches(xmlprefix+"<</<|>",
                                  name="xml-complete-end-tag")
        # Now with tag forms
        doclet1 = dedent(xmlprefix+"""\
                         <c1>
                           <c2 a1="1" a2='1' a3=val>
                             <e1 />
                             <e2 f1="1" f2 = '33' />""")
        self.assertTriggerMatches(doclet1 + "</<|>",
                                  name="xml-complete-end-tag")
        self.assertTriggerMatches(doclet1 + "</c2  >  </<|>",
                                  name="xml-complete-end-tag")
        
        #self.assertTriggerMatches("<?xml <|>", name="xml-complete-prolog")

    @tag("bug61748", "bug61777", "failsintermittently")
    def test_trg_with_cuddled_tag_close(self):
        name = "xml-complete-tag-attrs"
        self.assertTriggerMatches(xmlprefix+"<tag <|>/>", name=name)
        self.assertTriggerMatches(xmlprefix+"<ns: <|>/>", name=name)
        self.assertTriggerMatches(xmlprefix+"<ns:tag <|>/>", name=name)
        self.assertTriggerMatches(xmlprefix+"<ns:tag attr1='val1' <|>/>", name=name)

        self.assertCompletionsInclude(dedent(xmlprefix+"""\
            <window xmlns:html="http://www.w3.org/1999/xhtml"
                    xmlns="http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul">
                <button <|>/>
            </window>
            """),
            [("attribute", "accesskey=")],
            lang="XUL")

        # bug 61777
        self.assertCompletionsInclude(dedent(xmlprefix+"""\
            <window xmlns:html="http://www.w3.org/1999/xhtml"
                    xmlns="http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul">
                <button <|>
            """),
            [("attribute", "label=")],
            lang="XUL")
        
    @tag("bug65200")
    def test_tag_style_context_on_trg(self):
        self.assertNoTrigger(xmlprefix+"<x a <|>='val'></x>")
        self.assertNoTrigger(xmlprefix+"<x a= <|>'val'></x>")
        self.assertNoTrigger(xmlprefix+"<?x <|>'val'?>")
        self.assertNoTrigger(xmlprefix+"<?x abc <|>='val'?>")
        self.assertNoTrigger(xmlprefix+"<?x abc = <|>'val'?>")
        self.assertNoTrigger(xmlprefix+"<?x abc = 'val' <|>?>")

    def test_completions(self):
        doclet1 = dedent(xmlprefix+"""\
                         <c1>
                           <c2 a1="1" a2='1' a3='val'>
                             <e1 />
                             <e2 f1="1" f2 = '33' />""")

        self.assertCompletionsInclude(xmlprefix+"<!<|>",
            [("comment", "--")])
        self.assertCompletionsAre(xmlprefix+"<!<|>",
            [('doctype', 'DOCTYPE'), ('cdata', '[CDATA['), ('comment', '--')])
        from codeintel2.lang_xml import common_namespace_cplns
        self.assertCompletionsAre(xmlprefix+"<x xmlns:<|>", common_namespace_cplns)
        self.assertCompletionsAre(doclet1 + "</<|>", [('element', 'c2>')])
        self.assertCompletionsAre(doclet1 + "</c2  >  </<|>", [('element', 'c1>')])
        self.assertCompletionsAre(doclet1 + "<c3 a='1'>blah</c3></c2  >  </<|>", [('element', 'c1>')])
        self.assertCompletionsAre(doclet1 + "</c2  > </c1></<|>", None)
        
    def test_xulclose(self):
        xml = dedent(xmlprefix+"""\
                     <hbox>
                        <splitter><grippy/></<|>
                      </hbox>""")
        self.assertCompletionsAre(xml, [('element', 'splitter>')])
        xml = dedent(xmlprefix+"""\
                     <xul:hbox  xmlns:xul="http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul">
                        <xul:splitter><xul:grippy/></<|>
                      </xul:hbox>""")
        self.assertCompletionsAre(xml, [('element', 'xul:splitter>')])

    def test_preceding_trg_from_pos(self):
        # tags
        plen = len(xmlprefix)
        
        self.assertPrecedingTriggerMatches(xmlprefix+"<<|><$>", name="xml-complete-tags-and-namespaces", pos=1+plen)
        self.assertPrecedingTriggerMatches(xmlprefix+"<!<|><$>", name="xml-complete-gt-bang", pos=2+plen)
        self.assertPrecedingTriggerMatches(xmlprefix+"<!DOC<|><$>TYPE", name="xml-complete-gt-bang", pos=2+plen)
        self.assertPrecedingTriggerMatches(xmlprefix+"<<|><$>!DOCTYPE", name="xml-complete-tags-and-namespaces", pos=1+plen)

        self.assertPrecedingTriggerMatches(xmlprefix+"<c1  >  </<|><$>", name="xml-complete-end-tag")
        self.assertPrecedingTriggerMatches(xmlprefix+"<na<$><|>me", name="xml-complete-tags-and-namespaces", pos=1+plen)

        # ns tags
        self.assertPrecedingTriggerMatches(xmlprefix+"<ns:name<$><|>", name="xml-complete-ns-tags", pos=4+plen)
        self.assertPrecedingTriggerMatches(xmlprefix+"<ns:<$><|>", name="xml-complete-ns-tags", pos=4+plen)
        self.assertPrecedingTriggerMatches(xmlprefix+"<ns:na<$><|>me", name="xml-complete-ns-tags", pos=4+plen)

        # namespaces
        self.assertPrecedingTriggerMatches(xmlprefix+"<x xmlns:<|><$>", name="xml-complete-well-known-ns")

        # attributes
        self.assertPrecedingTriggerMatches(xmlprefix+"<ns:name <|><$>", name="xml-complete-tag-attrs")
        self.assertPrecedingTriggerMatches(xmlprefix+"<ns:name foo<|><$>", name="xml-complete-tag-attrs")
        self.assertPrecedingTriggerMatches(xmlprefix+"<ns:name foo:bar<|><$>", name="xml-complete-ns-tags-attrs")
        self.assertPrecedingTriggerMatches(xmlprefix+"<x a='<|><$>", name="xml-complete-attr-enum-values")
        self.assertPrecedingTriggerMatches(xmlprefix+'<x a="<|><$>', name="xml-complete-attr-enum-values")
        self.assertPrecedingTriggerMatches(xmlprefix+"<x a='foo<|><$>", name="xml-complete-attr-enum-values")
        self.assertPrecedingTriggerMatches(xmlprefix+'<x a="foo<|><$>', name="xml-complete-attr-enum-values")
        self.assertPrecedingTriggerMatches(xmlprefix+"<x ns:a='<|><$>", name="xml-complete-attr-enum-values")
        self.assertPrecedingTriggerMatches(xmlprefix+'<x ns:a="<|><$>', name="xml-complete-attr-enum-values")
        
