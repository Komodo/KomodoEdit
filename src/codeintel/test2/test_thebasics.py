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
from citestsupport import CodeIntelTestCase, writefile



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
                             "Specifies the weight of the font\n(CSS1, CSS2, CSS3)")
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
    def test_script_onx_attrs_dquotes(self):
        script = """
        <html>
            <head></head>
            <body onload="parseInt(); var x = ''; x.foo;">
            </body>
        </html>
        """
        self.assertCompletionsInclude(script.replace("parseInt", "par<|>seInt"),
            [("function", "parseFloat"),
             ("function", "parseInt"),])
        self.assertCompletionsInclude(script.replace("x = ''", "''.<|>"),
            [("variable", "length"),
             ("function", "toLowerCase"),])
        self.assertCompletionsInclude(script.replace("x.foo", "x.<|>foo"),
            [("variable", "length"),
             ("function", "toLowerCase"),])
    def test_script_onx_attrs_squotes(self):
        script = """
        <html>
            <head></head>
            <body onload='parseInt(); var x = ""; x.foo;'>
            </body>
        </html>
        """
        self.assertCompletionsInclude(script.replace('parseInt', 'par<|>seInt'),
            [('function', 'parseFloat'),
             ('function', 'parseInt'),])
        self.assertCompletionsInclude(script.replace('x = ""', '"".<|>'),
            [('variable', 'length'),
             ('function', 'toLowerCase'),])
        self.assertCompletionsInclude(script.replace('x.foo', 'x.<|>foo'),
            [('variable', 'length'),
             ('function', 'toLowerCase'),])

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
                             "foo($x, $y)")
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
                             "foo($x, $y)")
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
    @tag("knownfailure")
    def test_curr_calltip_arg_range(self):
        raise TestSkipped("no calltips in %s" % (self.lang))
    @tag("knownfailure")
    def test_calltips(self):
        raise TestSkipped("no calltips in %s" % (self.lang))
    @tag("knownfailure")
    def test_defns(self):
        raise TestSkipped("'Go To Definition' N/A for %s" % (self.lang))


class XULTestCase(XMLTestCase):
    lang = "XUL"
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
    def test_calltips(self):
        self.assertCalltipIs("<body><![CDATA[function foo(a){}\nfoo(<|>);]]></body>",
                             "foo(a)")
    def test_cplns(self):
        self.assertCompletionsInclude(XBL_DOCTYPE+"<<|>",
            [("element", "bindings")])
        self.assertCompletionsInclude(
            "<body><![CDATA[\nvar foo='';\nfoo.<|>toLowerCase();\n]]></body>",
            [("function", "toLowerCase")])
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
            [("element", "body")])

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


