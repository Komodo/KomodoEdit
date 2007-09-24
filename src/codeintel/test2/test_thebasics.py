#!/usr/bin/env python
# Copyright (c) 2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

"""Test just the basic support for all APIs for all languages.

TODO:
- add std cb_* tests
"""

import os
import sys
from os.path import join, dirname, abspath, exists, basename
import unittest
import logging
from pprint import pprint

from codeintel2.common import *
from codeintel2.util import indent, dedent, banner, markup_text, unmark_text

from testlib import TestError, TestSkipped, TestFailed, tag
from citestsupport import CodeIntelTestCase, writefile, init_xml_catalogs



#---- globals

log = logging.getLogger("test")

HTML_DOCTYPE = '''<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN">\n'''
XHTML_DOCTYPE = '''<?xml version="1.0"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">\n'''
XUL_DOCTYPE = '''<?xml version="1.0"?>\n<!DOCTYPE window PUBLIC "-//MOZILLA//DTD XUL V1.0//EN" "http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul">\n'''
XBL_DOCTYPE = '''<?xml version="1.0"?>\n<!DOCTYPE bindings PUBLIC "-//MOZILLA//DTD XBL V1.0//EN" "http://www.mozilla.org/xbl">\n'''



#---- the test cases

class _TheBasicsTestCase(CodeIntelTestCase):
    lang = None

    @tag("knownfailure")
    def test_trg_from_pos(self):
        raise NotImplementedError("%s test_trg_from_pos" % self.lang)

    @tag("knownfailure")
    def test_preceding_trg_from_pos(self):
        raise NotImplementedError("%s test_preceding_trg_from_pos" % self.lang)

    @tag("knownfailure")
    def test_calltips(self):
        raise NotImplementedError("%s test_calltips" % self.lang)

    @tag("knownfailure")
    def test_cplns(self):
        raise NotImplementedError("%s test_cplns" % self.lang)

    @tag("knownfailure")
    def test_defns(self):
        raise NotImplementedError("%s test_defns" % self.lang)

    @tag("knownfailure")
    def test_curr_calltip_arg_range(self):
        raise NotImplementedError("%s test_curr_calltip_arg_range" % self.lang)
    # Also, add the following if applicable for the language:
    #def test_built_in_blob(self):


class PythonTestCase(_TheBasicsTestCase):
    lang = "Python"
    def test_trg_from_pos(self):
        self.assertTriggerMatches("FOO.<|>",
            name="python-complete-object-members", pos=4)
    def test_preceding_trg_from_pos(self):
        self.assertPrecedingTriggerMatches("f.bar(<$> <|>",
            name="python-calltip-call-signature", pos=6)
    def test_calltips(self):
        self.assertCalltipIs("def foo(a):pass\nfoo(<|>)", "foo(a)")
    def test_cplns(self):
        self.assertCompletionsInclude("import sys\nsys.<|>path",
            [("variable", "path"), ("function", "exc_info")])
    def test_defns(self):
        self.assertDefnMatches(
            "import sys\nsys.pa<|>th",
            ilk="variable", name="path", )
    def test_curr_calltip_arg_range(self):
        self.assertCurrCalltipArgRange("foo(<+>art,<|>", "foo(a, b, c)", (7,8))
    def test_built_in_blob(self):
        stdlib = self.mgr.db.get_stdlib(self.lang)
        assert stdlib.has_blob("*")
        builtins = stdlib.get_blob("*")
        assert "int" in builtins.names


class JavaScriptTestCase(_TheBasicsTestCase):
    lang = "JavaScript"
    def test_trg_from_pos(self):
        self.assertTriggerMatches(" foo.<|> ",
            name="javascript-complete-object-members")
        self.assertTriggerMatches("<script> foo.<|> </script>",
            name="javascript-complete-object-members", lang="HTML")
    def test_preceding_trg_from_pos(self):
        self.assertPrecedingTriggerMatches(" foo.<|><$> ",
            name="javascript-complete-object-members")
        self.assertPrecedingTriggerMatches("<script> foo.<|><$> </script>",
            name="javascript-complete-object-members", lang="HTML")
    def test_calltips(self):
        self.assertCalltipIs("function foo(a){}\nfoo(<|>);",
                             "foo(a)")
        self.assertCalltipIs("<script> function foo(a){}\nfoo(<|>); </script>",
                             "foo(a)", lang="HTML")
    def test_cplns(self):
        self.assertCompletionsInclude(
            "var foo = new String();\nfoo.<|>toLowerCase();",
            [("function", "toLowerCase")])
        self.assertCompletionsInclude(
            "<script> var foo = new String();\nfoo.<|>toLowerCase(); </script>",
            [("function", "toLowerCase")], lang="HTML")
    def test_curr_calltip_arg_range(self):
        self.assertCurrCalltipArgRange("foo(<+>art,<|>", "foo(a, b, c)", (7,8))
        self.assertCurrCalltipArgRange("<script> foo(<+>art,<|> </script>",
            "foo(a, b, c)", (7,8), lang="HTML")
    def test_defns(self):
        self.assertDefnMatches(
            "var foo = new String();\nfoo.toLower<|>Case();",
            ilk="function", name="toLowerCase", )
        self.assertDefnMatches(
            "<script> var foo = new String();\nfoo.toLow<|>erCase(); </script>",
            lang="HTML",
            ilk="function", name="toLowerCase", )
    def test_built_in_blob(self):
        stdlib = self.mgr.db.get_stdlib(self.lang)
        assert stdlib.has_blob("*")
        builtins = stdlib.get_blob("*")
        assert "Object" in builtins.names

class HTMLTestCase(_TheBasicsTestCase):
    lang = "HTML"
    def setUp(self):
        super(HTMLTestCase, self).setUp()
        init_xml_catalogs()
    def test_trg_from_pos(self):
        self.assertTriggerMatches("<<|>",
            name="html-complete-tags-and-namespaces")
        self.assertTriggerMatches("<style> b<|>ody {} </style>",
            name="css-complete-tag-names")
        self.assertTriggerMatches("<script> foo.<|> </script>",
            name="javascript-complete-object-members")
    def test_preceding_trg_from_pos(self):
        self.assertPrecedingTriggerMatches("<foo<|><$>",
            name="html-complete-tags-and-namespaces")
        self.assertPrecedingTriggerMatches("<style> b<|><$>ody {} </style>",
            name="css-complete-tag-names")
        self.assertPrecedingTriggerMatches("<script> foo.<|><$> </script>",
            name="javascript-complete-object-members")
    def test_calltips(self):
        self.assertCalltipIs("<script>function foo(a){}\nfoo(<|>);</script>",
                             "foo(a)")
        self.assertCalltipIs("<style> selector { font-weight:<|> asdf; } </style>",
                             "Specifies the weight of the font")
    def test_cplns(self):
        self.assertCompletionsInclude(HTML_DOCTYPE+"<<|>",
            [("element", "html")])
        self.assertCompletionsInclude(
            "<script>\nvar foo='';\nfoo.<|>toLowerCase();\n</script>",
            [("function", "toLowerCase")])
        self.assertCompletionsInclude("<style> b<|>ody {} </style>",
            [("element", "body")])  # Off-by-one error? --TM
    def test_defns(self):
        self.assertDefnMatches(
            "<script> var foo = new String();\nfoo.toLow<|>erCase(); </script>",
            ilk="function", name="toLowerCase", returns="String", )
    def test_curr_calltip_arg_range(self):
        self.assertCurrCalltipArgRange("<script> foo(<+>art,<|> </script>",
                                       "foo(a, b, c)", (7,8))
        self.assertCurrCalltipArgRange("<style> body { color:<+><|> </style>",
                                       "blah blah", (0,0))

class PHPTestCase(HTMLTestCase):
    lang = "PHP"
    def test_trg_from_pos_php(self):
        self.assertTriggerMatches("<?php $a-><|> ?>",
            name="php-complete-object-members", pos=10)
    def test_preceding_trg_from_pos_php(self):
        self.assertPrecedingTriggerMatches("<?php $foo->bar(<|><$> ?>",
            name="php-calltip-call-signature", pos=16)
    def test_calltips_php(self):
        self.assertCalltipIs("<?php function foo($x,$y) {}\nfoo(<|>); ?>",
                             "foo(x, y)")
    @tag("php5")
    def test_cplns_php(self):
        self.assertCompletionsInclude(
            "<?php $e = new Exception('eek!');\n$e-><|> ?>",
            [("function", "getMessage"), ("function", "getLine")])
    @tag("php5")
    def test_defns_php(self):
        self.assertDefnMatches(
            "<?php $e = new Exception('eek!');\n$e<|>; ?>",
            ilk="variable", name="e", citdl="Exception", )
    def test_curr_calltip_arg_range_php(self):
        self.assertCurrCalltipArgRange("<?php foo(<+>art,<|> ?>",
                                       "foo(a, b, c)", (7,8))
    def test_built_in_blob(self):
        stdlib = self.mgr.db.get_stdlib(self.lang)
        assert stdlib.has_blob("*")
        builtins = stdlib.get_blob("*")
        assert "stat" in builtins.names

class SmartyTestCase(HTMLTestCase):
    lang = "Smarty"
    def test_trg_from_pos_php(self):
        self.assertTriggerMatches("<?php $a-><|> ?>",
            name="php-complete-object-members", pos=10)
    def test_preceding_trg_from_pos_php(self):
        self.assertPrecedingTriggerMatches("<?php $foo->bar(<|><$> ?>",
            name="php-calltip-call-signature", pos=16)
    def test_calltips_php(self):
        self.assertCalltipIs("<?php function foo($x,$y) {}\nfoo(<|>); ?>",
                             "foo(x, y)")
    @tag("php5")
    def test_cplns_php(self):
        self.assertCompletionsInclude(
            "<?php $e = new Exception('eek!');\n$e-><|>",
            [("function", "getMessage"), ("function", "getLine")])
    @tag("php5")
    def test_defns_php(self):
        self.assertDefnMatches(
            "<?php $e = new Exception('eek!');\n$e<|>; ?>",
            ilk="variable", name="e", citdl="Exception", )
    def test_curr_calltip_arg_range_php(self):
        self.assertCurrCalltipArgRange("<?php foo(<+>art,<|> ?>",
                                       "foo(a, b, c)", (7,8))

class DjangoTestCase(HTMLTestCase):
    lang = "Django"

class TemplateToolkitTestCase(HTMLTestCase):
    lang = "TemplateToolkit"

class MasonTestCase(HTMLTestCase):
    lang = "Mason"

class XMLTestCase(_TheBasicsTestCase):
    lang = "XML"
    def setUp(self):
        super(XMLTestCase, self).setUp()
        init_xml_catalogs()
    def test_trg_from_pos(self):
        self.assertTriggerMatches("<<|>",
            name="xml-complete-tags-and-namespaces")
        self.assertTriggerMatches(XHTML_DOCTYPE+"<<|>",
            name="xml-complete-tags-and-namespaces")
    def test_preceding_trg_from_pos(self):
        self.assertPrecedingTriggerMatches("<foo<|><$>",
            name="xml-complete-tags-and-namespaces")
    def test_cplns(self):
        self.assertCompletionsInclude(XHTML_DOCTYPE+"<<|>",
            [("element", "html")])
    def test_curr_calltip_arg_range(self):
        raise TestSkipped("no calltips in XML")
    def test_calltips(self):
        raise TestSkipped("no calltips in XML")
    def test_defns(self):
        raise TestSkipped("'Go To Definition' N/A for XML")


class XULTestCase(XMLTestCase):
    lang = "XUL"
    def setUp(self):
        super(XULTestCase, self).setUp()
        init_xml_catalogs()
    def test_trg_from_pos(self):
        self.assertTriggerMatches("<<|>",
            name="xml-complete-tags-and-namespaces")
        self.assertTriggerMatches("<script> foo.<|> </script>",
            name="javascript-complete-object-members")
    def test_preceding_trg_from_pos(self):
        self.assertPrecedingTriggerMatches("<foo<|><$>",
            name="xml-complete-tags-and-namespaces")
        self.assertPrecedingTriggerMatches("<script> foo.<|><$> </script>",
            name="javascript-complete-object-members")
    def test_calltips(self):
        self.assertCalltipIs("<script>function foo(a){}\nfoo(<|>);</script>",
                             "foo(a)")
    def test_cplns(self):
        self.assertCompletionsInclude(XUL_DOCTYPE+"<<|>",
            [("element", "window")])
        self.assertCompletionsInclude(
            "<script>\nvar foo='';\nfoo.<|>toLowerCase();\n</script>",
            [("function", "toLowerCase")])
    def test_defns(self):
        self.assertDefnMatches(
            "<script>\nvar foo='';\nfoo.<|>toLowerCase();\n</script>",
            ilk="function", name="toLowerCase", returns="String", )
    def test_curr_calltip_arg_range(self):
        self.assertCurrCalltipArgRange("<script><![CDATA[ foo(<+>art,<|> ]]></script>",
                                       "foo(a, b, c)", (7,8))

class XBLTestCase(XMLTestCase):
    lang = "XBL"
    def setUp(self):
        super(XBLTestCase, self).setUp()
        init_xml_catalogs()
    def test_trg_from_pos(self):
        self.assertTriggerMatches("<<|>",
            name="xml-complete-tags-and-namespaces")
        self.assertTriggerMatches("<body><![CDATA[ foo.<|> ]]></body>",
            name="javascript-complete-object-members")
    def test_preceding_trg_from_pos(self):
        self.assertPrecedingTriggerMatches("<foo<|><$>",
            name="xml-complete-tags-and-namespaces")
        self.assertPrecedingTriggerMatches("<body><![CDATA[ foo.<|><$> ]]></body>",
            name="javascript-complete-object-members")
    @tag("knownfailure")
    def test_calltips(self):
        self.assertCalltipIs("<body><![CDATA[function foo(a){}\nfoo(<|>);]]></body>",
                             "foo(a)")
    @tag("knownfailure")
    def test_cplns(self):
        self.assertCompletionsInclude(XBL_DOCTYPE+"<<|>",
            [("element", "bindings")])
        self.assertCompletionsInclude(
            "<body><![CDATA[\nvar foo='';\nfoo.<|>toLowerCase();\n]]></body>",
            [("function", "toLowerCase")])
    @tag("knownfailure")
    def test_defns(self):
        self.assertDefnMatches(
            "<body><![CDATA[\nvar foo='';\nfoo.toL<|>owerCase();\n]]></body>",
            ilk="function", name="toLowerCase", returns="String", )
    def test_curr_calltip_arg_range(self):
        self.assertCurrCalltipArgRange("<body><![CDATA[ foo(<+>art,<|> ]]></body>",
                                       "foo(a, b, c)", (7,8))

xslt_prefix = """<?xml version="1.0"?> 
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">
  <xsl:output method="html" indent="yes"/>
"""

class XSLTTestCase(XMLTestCase):
    lang = "XSLT"
    _ci_env_prefs_ = {"defaultHTMLDecl":"-//W3C//DTD HTML 4.01//EN"}
    def setUp(self):
        super(XSLTTestCase, self).setUp()
        init_xml_catalogs()
    def test_trg_from_pos(self):
        self.assertTriggerMatches(xslt_prefix+"<<|>",
            name="xml-complete-tags-and-namespaces")
    def test_preceding_trg_from_pos(self):
        self.assertPrecedingTriggerMatches(xslt_prefix+"<foo<|><$>",
            name="xml-complete-tags-and-namespaces")
    def test_cplns(self):
        self.assertCompletionsInclude(xslt_prefix+"<<|>",
            [("element", "xsl:template")])
        self.assertCompletionsInclude(xslt_prefix+"<xsl:template match='asdf'>\n<html><<|>",
            [("element", "BODY")])
    def test_curr_calltip_arg_range(self):
        raise TestSkipped("no calltips in XSLT")
    def test_calltips(self):
        raise TestSkipped("no calltips in XSLT")

#class PerlTestCase(_TheBasicsTestCase):
#    lang = "Perl"
#class RubyTestCase(_TheBasicsTestCase):
#    lang = "Ruby"
#class RHTMLTestCase(_TheBasicsTestCase):
#    lang = "RHTML"
#class CSSTestCase(_TheBasicsTestCase):
#    lang = "CSS"



#---- mainline

if __name__ == "__main__":
    unittest.main()


