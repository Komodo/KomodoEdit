#!/usr/bin/env python
# Copyright (c) 2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

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
from citestsupport import CodeIntelTestCase, init_xml_catalogs



#---- globals

log = logging.getLogger("test")

xmlprefix = """<?xml version="1.0"?>
"""



#---- the test cases

class XULTestCase(CodeIntelTestCase):
    lang = "XUL"

    def setUp(self):
        super(XULTestCase, self).setUp()
        init_xml_catalogs()

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
        
