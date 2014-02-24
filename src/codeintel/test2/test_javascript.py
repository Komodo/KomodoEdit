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

"""Test some JavaScript-specific codeintel handling."""

import os
import sys
import re
from os.path import join, dirname, abspath, exists, basename
from glob import glob
import unittest
import subprocess
import logging

from codeintel2.common import *
from codeintel2.util import (indent, dedent, banner, markup_text, unmark_text,
                             lines_from_pos)
from codeintel2.environment import SimplePrefsEnvironment

from testlib import TestError, TestSkipped, TestFailed, tag
from citestsupport import CodeIntelTestCase, writefile



log = logging.getLogger("test")



class LangJavaScriptTestCase(CodeIntelTestCase):
    """Direct testing of the lang_javascript ciler."""
    lang = "JavaScript"

    @tag("bug92884")
    def test_getVariableType(self):
        # Ensure variable ciling is working for "new this."
        from codeintel2 import lang_javascript
        pure = lang_javascript.PureJavaScriptStyleClassifier()
        OP = pure.operator_style
        KW = pure.keyword_style
        ID = pure.identifier_style
        text =   ['x', '=', 'new', 'this', '.', 'Internal1', '(', ')', ';']
        styles = [ KW,  OP,  KW,    KW,     OP,  ID,          OP,  OP,  OP]
        self.assertEqual(len(text), len(styles))
        ciler = lang_javascript.JavaScriptCiler(None)
        # Test the citdl type handler.
        citdl, p = ciler._getCitdlTypeInfo(styles, text, p=3)
        self.assertEqual(citdl, ["this", "Internal1()"])
        self.assertEqual(p, 8)
        # Test the variable type handler.
        citdl, p, isAlias = ciler._getVariableType(styles, text, p=1)
        self.assertEqual(citdl, ["this", "Internal1"])
        self.assertEqual(p, 8)

    @tag("bug99286")
    def test_tokenize_citdl(self):
        """Direct testing of the citdl tokenizer"""
        buf, trg = self._get_buf_and_trg("foo.<|>", self.lang)
        ctlr = EvalController()

        from codeintel2 import tree_javascript
        evlr = tree_javascript.CandidatesForTreeEvaluator(ctlr, buf, trg,
                                                          None, None)
        def get_tokens(expr):
            return list(evlr._tokenize_citdl_expr(expr))

        self.assertEqual(get_tokens(""), [])
        self.assertEqual(get_tokens("array_members[]"),
                         ["array_members", "[]"])
        self.assertEqual(get_tokens("property.access"),
                         ["property", "access"])
        self.assertEqual(get_tokens("method_call()"),
                         ["method_call", "()"])
        self.assertEqual(get_tokens("array['member']"),
                         ["array", "member"])
        self.assertEqual(get_tokens('array["string_member"]'),
                         ["array", "string_member"])
        self.assertEqual(get_tokens("chained['string']['member']"),
                         ["chained", "string", "member"])
        # This one isn't actually possible
        #self.assertEqual(get_tokens("nested[string['member']]"),
        #                 ["nested", "string", "member"])


class TriggerTestCase(CodeIntelTestCase):
    lang = "JavaScript"

    def test_complete_object_members(self):
        # Triggers after full stop on identifiers:
        #        abc.<|>
        self.assertTriggerMatches("abc.<|>def",
                                  name="javascript-complete-object-members",
                                  pos=4)
        self.assertNoTrigger("abc.d<|>ef")
        self.assertNoTrigger("abcd<|>.def")
        # assert no trig in strings or comments
        self.assertNoTrigger('var s = "abc.<|>def";')
        self.assertNoTrigger("var s = 'abc.<|>def';r")
        self.assertNoTrigger('/* abc.<|>def */')
        self.assertNoTrigger('// abc.<|>def')

    def test_calltip_call_signature(self):
        # Triggers after open bracket:
        #        abc(<|>
        self.assertTriggerMatches("alert(<|>'myAlert');",
                                  name="javascript-calltip-call-signature",
                                  form=TRG_FORM_CALLTIP)
        # assert no trig from non-identifer words
        self.assertNoTrigger('if (<|>myValue) {')
        # assert no trig in strings or comments
        self.assertNoTrigger('var s = "alert(<|>def);";')
        self.assertNoTrigger("var s = 'alert(<|>def);';r")
        self.assertNoTrigger('/* myfunc.callthis(<|>arg1); */')
        self.assertNoTrigger('// myfunc.callthis(<|>arg1);')

    def test_calltip_call_signature_comma(self):
        # Triggers after open bracket:
        #        abc(<|>
        self.assertTriggerMatches("parseInt('22',<|>);",
                                  name="javascript-calltip-call-signature",
                                  form=TRG_FORM_CALLTIP)
        # assert no trig from non-identifer words
        self.assertNoTrigger('function parseInt("22",<|>')
        # More complicated example.
        self.assertTriggerMatches("parseInt(document.getElementById('foo').value,<|>);",
                                  name="javascript-calltip-call-signature",
                                  form=TRG_FORM_CALLTIP,
                                  pos=9)

    def test_doctags(self):
        # Triggers after @ in a comment block
        #        /** @param
        cpln_trigger_name = "javascript-complete-jsdoc-tags"
        calltip_trigger_name = "javascript-calltip-jsdoc-tags"
        self.assertTriggerMatches("/** @<|>param",
                                  name=cpln_trigger_name,
                                  pos=5)
        self.assertTriggerMatches("/** @param <|>",
                                  name=calltip_trigger_name,
                                  pos=9)
        self.assertPrecedingTriggerMatches("/** @param foo bar <$><|>",
                                           name=calltip_trigger_name,
                                           pos=9)
        # Don't trigger in normal code or inside strings
        self.assertNoTrigger("@<|>something")
        self.assertNoTrigger("var s = '@<|>something';")

    @tag("toddw")
    def test_bug53247(self):
        self.assertTriggerMatches(dedent("""\
                function Cat(name){
                    this.<|>name = name;
                }
            """),
            name="javascript-complete-object-members")

    @tag("bug70627", "knownfailure")
    def test_preceding_with_numeric(self):
        self.assertPrecedingTriggerMatches(
            "c.command2k<$><|>",
            name="javascript-complete-object-members", pos=2)

    @tag("bug62767")
    def test_trigger_names(self):
        self.assertTriggerMatches("abc<|>",
                                  name="javascript-complete-names",
                                  pos=0)
        self.assertNoTrigger("ab<|>")
        self.assertNoTrigger("abcd<|>")
        self.assertPrecedingTriggerMatches(
            "alert(document<$><|>",
            name="javascript-complete-names", pos=6)
        self.assertPrecedingTriggerMatches(
            "alert(<$>document<|>",
            name="javascript-calltip-call-signature", pos=6)

    @tag("bug76711")
    def test_complete_array_members(self):
        # Triggers after foo['
        #
        #    Samples:
        #        $_SERVER['    =>   [ 'SERVER_NAME', 'SERVER_ADDR', ...]
        name = "javascript-complete-array-members"
        type = "array-members"
        self.assertTriggerMatches("_SERVER['<|>SERVER_NAME']",
                                  name=name, pos=9)
        self.assertTriggerMatches('_SERVER["<|>SERVER_NAME"]',
                                  name=name, pos=9)
        # Try with some additional spacing...
        self.assertTriggerMatches("_SERVER[  \n'<|>SERVER_NAME']",
                                  name=name, pos=12)
        # No trigger before or after the correct position
        self.assertNoTrigger('_SERVER[<|>"SERVER_NAME"]')
        self.assertNoTrigger('_SERVER["S<|>ERVER_NAME"]')
        # No trigger at the end of the string.
        self.assertNoTrigger('_SERVER["SERVER_NAME"<|>]')

        # Test the expression retrieval.
        self.assertCITDLExprIs("foo['<|>item']", "foo",
                               trigger_name=type, bracket_pos=3)
        self.assertCITDLExprIs("foo.bar['<|>item']", "foo.bar",
                               trigger_name=type, bracket_pos=7)
        # This one is a little advanced, maybe one day...
        #self.assertCITDLExprIs("foo.bar['item'].<|>", "foo.bar.item")

class CplnTestCase(CodeIntelTestCase):
    lang = "JavaScript"
    test_dir = join(os.getcwd(), "tmp")

    def test_doctags(self):
        # Triggers after @ in a comment block
        #        /** @param
        content, positions = unmark_text(dedent("""\
            /** @<1>param <2>name Some comment
        """))
        from codeintel2.jsdoc import jsdoc_tags
        cplns = [ ("variable", x) for x in sorted(jsdoc_tags.keys()) ]
        self.assertCompletionsAre(markup_text(content, pos=positions[1]), cplns)
        self.assertCalltipIs(markup_text(content, pos=positions[2]),
                             jsdoc_tags["param"])

    @tag("bug68727")
    def test_jsdoc_parsing(self):
        # http://bugs.activestate.com/show_bug.cgi?id=68727
        content, positions = unmark_text(dedent("""\
            function dummyfunction() { }
            /* some unrelated comment */

            /**
             * open window
             * @param {String} page  a page tag
             */
            myopen = function(page) { }
            myopen(<1>);
        """))
        self.assertCalltipIs(markup_text(content, pos=positions[1]),
                             "myopen(page)\nopen window")

    @tag("bug102314")
    def test_jsdoc_constructor(self):
        content, positions = unmark_text(dedent("""\
            /**
             * A module representing an Animal.
             * @constructor
             */
            function Animal()
            {
              this.owner = "Homeless";
            }
            var myAnimal = new Animal();
            myAnimal.<1>
        """))
        self.assertCompletionsAre(markup_text(content, pos=positions[1]),
            [("variable", "owner")]);

    @tag("bug53217", "bug53237")
    def test_local(self):
        # JS completion for stuff in just the local file.
        content, positions = unmark_text(dedent("""\
            function Mammal(name){
                this.name=name;
                this.offspring=[];
            }
            Mammal.prototype.haveABaby=function(){
                var newBaby=new Mammal("Baby "+this.name);
                this.offspring.push(newBaby);
                return newBaby;
            }
            Cat.prototype = new Mammal();
            Cat.prototype.constructor=Cat;
            function Cat(name){
                this.<7>name = name;
                name.<8>toLowerCase();
            }
            Cat.prototype.meow = function() { dump("meow"); }

            var felix = new Cat(<4>'Felix');
            felix.<1>meow(<5>);
            felix.haveABaby(<6>);

            function comics() {
                var garfield = new Cat('Garfield');
                dump(garfield.<2>name);
                alert(felix.<3>name);
            }
        """))
        cat_instance_cplns = [("function", "haveABaby"),
                              ("function", "meow"),
                              ("variable", "name"),
                              ("variable", "offspring")]
        for marker in range(1, 4):
            self.assertCompletionsAre(
                markup_text(content, pos=positions[marker]),
                cat_instance_cplns)

        self.assertCalltipIs(
            markup_text(content, pos=positions[6]), "haveABaby()")
        self.assertCalltipIs(
            markup_text(content, pos=positions[5]), "meow()")
        self.assertCalltipIs(
            markup_text(content, pos=positions[4]), "Cat(name)")

        # This is bug 53237.
        self.assertCompletionsAre(
            markup_text(content, pos=positions[7]),
            cat_instance_cplns)

        # Testing that completion on a var for which we have no type
        # inference info doesn't blow up. I'm cheating because I
        # know what "name" here doesn't have type info.
        self.assertCompletionsAre(
            markup_text(content, pos=positions[8]),
            None)

    #TODO:
    # - Test case where a JS class' ctor is NOT the same name as the
    #   class. E.g., is it possible for class Cat in test_local()
    #   above to not define it's own ctor -- i.e. just use Mammal's?

    def test_local2(self):
        # JS completion for stuff in just the local file.
        content, positions = unmark_text(dedent("""\
            var treeView2 = {
               treebox : null,
               setTree: function(treebox){ this.<1>treebox = treebox; }
            };
        """))
        self.assertCompletionsAre(
            markup_text(content, pos=positions[1]),
            [("function", "setTree"),
             ("variable", "treebox")])

    def test_private_variables(self):
        # JS completion for stuff in just the local file.
        content, positions = unmark_text(dedent("""\
            function testme() {
                var name = "testme";
                this.treebox = null;
                this.setTree = function(treebox) { this.treebox = treebox; }
            };
            var t = new testme();
            t.<1>xxx;
        """))
        # Should not include name, due to it being private
        self.assertCompletionsAre(
            markup_text(content, pos=positions[1]),
            [("function", "setTree"),
             ("variable", "treebox")])

    def test_global_accessor(self):
        # JS completion for stuff in just the local file.
        content, positions = unmark_text(dedent("""\
            window.foo = new Array();
            foo.<1>;
        """))
        # Should not include name, due to it being private
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("function", "concat")])

    def test_ctor_scope_cheat(self):
        # At one point was getting this error:
        #     error: error evaluating 'this.baz' at rand20#7: ValueError: too many values to unpack (/home/trentm/as/Komodo-devel/src/codeintel/lib/codeintel2/tree.py#854 in get_parent_scope)
        # Make sure we don't anymore.
        #
        # Also, we need to deal with our ctor cheat. If the start
        # scope for evaluation a CITDL expression is at class scope,
        # then we should push it to the ctor's scope. Otherwise, in
        # this example, we'd never be able to resolve "Robin" for
        # this.robin.
        content, positions = unmark_text(dedent("""\
            function Batman() { this.pow = 42; }
            Batman.prototype.pif = function() {}
            function Comic() {
                function Robin() { this.blim = 42; }
                Robin.prototype.blam = function() {}
                this.batman = new Batman();
                this.robin = new Robin();
            }
            Comic.prototype.read = function() {
                this.batman.<1>pif();
                this.robin.<2>blam();
            }
        """))
        self.assertCompletionsAre(
            markup_text(content, pos=positions[1]),
            [("function", "pif"), ("variable", "pow")])
        self.assertCompletionsAre(
            markup_text(content, pos=positions[2]),
            [("function", "blam"), ("variable", "blim")])

    def test_event_heuristic(self):
        # JS completion for event heuristic.
        content, positions = unmark_text(dedent("""\
            Foo.prototype.onTreeKeyPress = function(event) {
                event.<1>target;
            }
        """))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("variable", "target")])

    @tag("bug57037")
    def test_builtin_types(self):
        # JS completion for event heuristic.
        content, positions = unmark_text(dedent("""\
            String.<1>toLowerCase(<2>);
            RegExp.<3>ignoreCase;
            Object.<4>valueOf();
        """))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("function", "toLowerCase")])
        self.assertCalltipIs(
            markup_text(content, pos=positions[2]),
            "toLowerCase() -> String\nReturn a lowercase version of the string.")
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[3]),
            [("variable", "ignoreCase")])
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[4]),
            [("function", "valueOf")])

    def test_builtin_vars(self):
        content, positions = unmark_text(dedent("""\
            document.<1>getElementById(<2>);
            window.<3>blur(<4>);
        """))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("function", "getElementById")])
        self.assertCalltipIs(
            markup_text(content, pos=positions[2]),
            dedent("""\
                getElementById(elementId)
                Returns the Element whose ID is given by elementId. If no
                such element exists, returns null."""))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[3]),
            [("function", "blur"), ("variable", "scrollX")])
        self.assertCalltipIs(
            markup_text(content, pos=positions[4]),
            dedent("""\
                blur()
                Shifts focus away from the window. The window.blur() method
                is the programmatic equivalent of the user shifting focus
                away from the current window."""))

    @tag("bug58307")
    def test_builtin_funcs(self):
        content, positions = unmark_text(dedent("""\
            dump(<1>"yo yo yo");
            alert(<2>"yowzer!");
        """))
        self.assertCalltipIs(
            markup_text(content, pos=positions[1]),
            "dump(text)\n"
            "Prints messages to the console. window.dump is commonly used\n"
            "to debug JavaScript.")
        self.assertCalltipIs(
            markup_text(content, pos=positions[2]),
            dedent("""\
                alert(text)
                Display an alert dialog with the specified text. The alert
                dialog should be used for messages which do not require any
                response of the part of the user, other than the
                acknowledgement of the message."""))

    def test_prototype_vars(self):
        content = dedent("""\
            function Foo() {}
            Foo.prototype = {}
            Foo.prototype.bar = function() {}
            Foo.prototype.baz = 0;
            var foo = new Foo();
            foo.<|>
        """)
        self.assertCompletionsInclude(
            content,
            [("function", "bar"), ("variable", "baz")])

    @tag("bug93496")
    def test_prototype_class(self):
        content = dedent("""\
            function Player() {}
            Player.prototype = {};
            Player.prototype.FighterStyles = {
                Blue : 0,
                Cyan : 1,
                Green : 2
            };
            Player.prototype.hitBox = [4, 4];
            var player = new Player();
            player.<|>
        """)
        self.assertCompletionsInclude(content,
            [("namespace", "FighterStyles"),
             ("variable", "hitBox")])

    @tag("assertScopeLpathIs")
    def test_intermixed_class_definitions(self):
        # JS completion when intermixing class definitions
        content, positions = unmark_text(dedent("""\
                // Define class 1
                function intermixed_test_code() {
                    this.field1 = null;
                    this.field2 = null;
                }

                // Define class 2
                function intermixed_test_event(key, ctrl) {
                    this.keyCode = key;
                    if (ctrl) {
                        this.ctrlKey = ctrl;
                    }
                }

                // Define class 1 function
                intermixed_test_code.prototype.sendKeyPressEvent = function(key, ctrl) {
                    this.<1>field1 = 1;
                }

                // Third class
                function intermixed_test_result() {
                    this.result = 0;
                }

                // Define class 2 function
                intermixed_test_event.prototype.getResult = function() {
                    this.<2>keyCode = 101;
                }
                """))
        self.assertScopeLpathIs(
            markup_text(content, pos=positions[1]),
            ["intermixed_test_code", "sendKeyPressEvent"])
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("variable", "field1"), ("variable", "field2")])
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[2]),
            [("variable", "keyCode"), ("variable", "ctrlKey")])

    @tag("assertScopeLpathIs")
    def test_finding_start_scope_in_var_scope(self):
        content, positions = unmark_text(dedent("""\
            <1>
            var treeView2 = {
                <2>
                rowCount : 10000, <3>
                treebox : null,
                getCellText : function(row,column){ <4>
                    <5>
                    if (column.id == "namecol") return "Row "+row;
                    else return "February 18";
                },
            };
            <6>
        """))
        self.assertScopeLpathIs(
            markup_text(content, pos=positions[1]),
            [])
        self.assertScopeLpathIs(
            markup_text(content, pos=positions[2]),
            ["treeView2"])
        self.assertScopeLpathIs(
            markup_text(content, pos=positions[3]),
            ["treeView2"])
        self.assertScopeLpathIs(
            markup_text(content, pos=positions[4]),
            ["treeView2", "getCellText"])
        self.assertScopeLpathIs(
            markup_text(content, pos=positions[5]),
            ["treeView2", "getCellText"])
        self.assertScopeLpathIs(
            markup_text(content, pos=positions[6]),
            [])

    @tag("bug58157")
    def test_calltip_from_function_definition(self):
        # Assert we don't have a calltip when defining a function
        self.assertNoTrigger("function abc(<|>) {}")

    @tag("bug62528", "knownfailure")
    def test_obj_var_with_method_assignment(self):
        # Such as XMLHttpRequest callback:
        self.assertCompletionsInclude(
            dedent("""\
                http_request = new XMLHttpRequest();
                http_request.onreadystatechange = function() { alertContents(http_request); };
                http_request.<|>open('GET', url, true);
                http_request.send(null);
            """),
            [("function", "onreadystatechange"),
             ("function", "open"),
             ("function", "send"),
             ("function", "abort")])

    def test_files_in_same_dir(self):
        test_dir = join(self.test_dir, "test_files_in_same_dir")
        foo_js_content, foo_js_positions = unmark_text(dedent("""\
            var b = new Bar(<1>"blah blah");
            b.<2>bar();
        """))

        manifest = [
            ("bar.js", dedent("""
                function Bar(name) {
                    this.name = name;
                }
                Bar.prototype = {
                    bar: function() { alert('bar'); }
                };
             """)),
            ("foo.js", foo_js_content),
        ]
        for file, content in manifest:
            path = join(test_dir, file)
            writefile(path, content)

        buf = self.mgr.buf_from_path(join(test_dir, "foo.js"),
                                     lang="JavaScript")
        self.assertCalltipIs2(buf, foo_js_positions[1], "Bar(name)");
        self.assertCompletionsInclude2(buf, foo_js_positions[2],
            [("function", "bar"), ("variable", "name")])

    def test_override_stdlib_class(self):
        env = SimplePrefsEnvironment(codeintel_selected_catalogs=['prototype'])
        content, positions = unmark_text(dedent("""\
            var String = {
                foo: function(a, b) {}
            };

            String.<1>foo; // should still get stdlib String attrs here
        """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [# local extensions:
             ("function", "foo"),
             # prototype extensions:
             ("function", "camelize"),
             ("function", "escapeHTML"),
             # std String attrs:
             ("variable", "length"),
             ("function", "concat"),
            ],
            env=env)

    @tag("bug65447")
    def test_cpln_with_unknown_parent(self):
        content, positions = unmark_text(dedent("""\
            function test_cplns() {
                this.x = 1;
            }
            
            test_cplns.prototype = new UnknownParentX();
            test_cplns.prototype.constructor = test_cplns;
            
            test_cplns.prototype.showMe = function(arg1) {
                alert(arg1);
            }
            
            var tc = new test_cplns();
            tc.<1>abc;
        """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("variable", "x"),
             ("function", "showMe"),])

    @tag("bug59127")
    def test_builtin_object_calltips(self):
        self.assertCalltipIs("var foo = new String(<|>);",
            "String(...)")
        self.assertCalltipIs("var foo = new Boolean(<|>);",
            "Boolean(...)")

    @tag("bug65277")
    def test_citdl_expr_with_exclamation(self):
        self.assertCITDLExprIs("!foo.<|>", "foo")

    @tag("bug65672")
    def test_explicit_citdl_expr_with_comments(self):
        # Test we don't include the citdl expression from the comment section
        self.assertCITDLExprIs(dedent("""
            // Guide.
            document.<|>
        """), "document", implicit=False)
        self.assertCITDLExprIs(dedent("""
            /* Guide. */
            document.<|>
        """), "document", implicit=False)
        # Test we still get the citdl expression from a comment
        self.assertCITDLExprIs(dedent("""
            document. // Guide<1>
        """), "Guide", implicit=False)

    @tag("bug66637")
    def test_function_return_types(self):
        content, positions = unmark_text(dedent("""
            // Function type return
            function test() { return "abc"; }
            var s = test();
            s.<1>x;

            // Function variable return from function variable
            function test2() { var d = document.getElementById("mydomElement"); return d; }
            var dEl = test2();
            dEl.<2>x;

            // Function inside function return
            function test3() {
                function test4() {
                    return "xyz";
                }
                var x = test4();
                return x;
            }
            var t3 = test3();
            t3.<3>x;

            // Test dom example
            var domEl = document.getElementById("mydomElement");
            domEl.<4>x;
            var newNode = domEl.insertBefore(a, b);
            newNode.<5>x;
        """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("variable", "length"),
             ("function", "indexOf"),])
        self.assertCompletionsInclude(markup_text(content, pos=positions[2]),
            [("variable", "nodeName"),
             ("function", "appendChild"),])
        self.assertCompletionsInclude(markup_text(content, pos=positions[3]),
            [("variable", "length"),
             ("function", "indexOf"),])
        self.assertCompletionsInclude(markup_text(content, pos=positions[4]),
            [("variable", "nodeName"),
             ("function", "appendChild"),])
        self.assertCompletionsInclude(markup_text(content, pos=positions[5]),
            [("variable", "nodeName"),
             ("function", "appendChild"),])

    @tag("bug66842")
    def test_function_return_chaining(self):
        content, positions = unmark_text(dedent("""
            function returnString() {
              return 'abc';
            }
            var x = returnString();
            // <1> String choices
            // <2> Array choices
            var y = x.<1>split('').<2>;
        """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("variable", "length"),
             ("function", "indexOf"),])
        self.assertCompletionsInclude(markup_text(content, pos=positions[2]),
            [("variable", "length"),
             ("function", "push"),])

    @tag("bug67123")
    def test_named_function(self):
        # http://bugs.activestate.com/show_bug.cgi?id=67123
        # Should ignore the optional function name "my_f"
        content, positions = unmark_text(dedent("""
            var functest = function my_f(a, b) { };
            functest(<1>);
            var functestnew = new function my_f(a, b) { };
            functestnew(<2>);
        """))
        self.assertCalltipIs(
            markup_text(content, pos=positions[1]), "functest(a, b)")
        self.assertCalltipIs(
            markup_text(content, pos=positions[2]), "functestnew(a, b)")

    def test_string_literals(self):
        content, positions = unmark_text(dedent("""\

            // Standard string completions
            "".<1>charAt(<2>);
            '\\n'.<3>charAt();

            // String delimiter inside string (should not trigger)
            "My '.<4>field";
            'My ".<5>field';

            // Test we don't get string completions on function returns like:
            function test(arg1) { return document; }
            test("".<6>charAt()).<7>xyz;

            // There is/was something wierd with this in my Komodo, so
            // adding a testcase for this sucker.
            function test2(arg1) { return 1; }
            test2("abc").<8>xyz;
        """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [('function', 'concat'),
             ('function', 'toLowerCase'),
             ('function', 'indexOf')])
        self.assertCalltipIs(markup_text(content, pos=positions[2]),
            "charAt(pos) -> String\nReturn the character at a particular "
            "index in the string.")
        self.assertCompletionsInclude(markup_text(content, pos=positions[3]),
            [('function', 'concat'),
             ('function', 'toLowerCase'),
             ('function', 'indexOf')])
        self.assertNoTrigger(markup_text(content, pos=positions[4]))
        self.assertNoTrigger(markup_text(content, pos=positions[5]))
        self.assertCompletionsInclude(markup_text(content, pos=positions[6]),
            [('function', 'concat'),
             ('function', 'toLowerCase'),
             ('function', 'indexOf')])
        self.assertCompletionsInclude(markup_text(content, pos=positions[7]),
            [('function', 'getElementById'), ])
        self.assertCompletionsInclude(markup_text(content, pos=positions[8]),
            [('function', 'toPrecision'), ])

    @tag("bug71343")
    def test_instance_defined_in_class_function(self):
        content, positions = unmark_text(dedent("""\
            function test_scope() {
            }
            test_scope.prototype.setup = function() {
                var tmpStr = new String();
                this.str = tmpStr.<1>replace("x", "y");
            }
            var v = new test_scope();
            v.str.<2>;
        """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("function", "charAt"),
             ("function", "concat")])
        self.assertCompletionsInclude(markup_text(content, pos=positions[2]),
            [("function", "charAt"),
             ("function", "concat")])

    @tag("bug71345")
    def test_find_scope_from_line(self):
        content, positions = unmark_text(dedent("""\
            function test_scope() {
            }
            test_scope.prototype.setup = function() {
                var tmpStr = new String();
                this.str = tmpStr.<1>replace("x", "y");
            }
        """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("function", "charAt"),
             ("function", "concat")])

    @tag("bug71666")
    def test_instance_name_same_as_class(self):
        content, positions = unmark_text(dedent("""\
            var test_scope = {};
            (function() {
                function test_this_class() {
                    this.name = "";
                }
                test_this_class.prototype.setup = function() {
                    this.str = "Test class";
                    return this.str;
                }
                this.test_this_class = test_this_class;
            }).apply(test_scope);
            var t = new test_scope.test_this_class();
            t.<1>;
            var myvalue = t.setup(<2>);
            myvalue.<3>;
        """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("variable", "name"),
             ("variable", "str"),
             ("function", "setup")])
        self.assertCalltipIs(markup_text(content, pos=positions[2]),
            "setup()")
        self.assertCompletionsInclude(markup_text(content, pos=positions[3]),
            [("variable", "length"),
             ("function", "toLowerCase"),
             ("function", "indexOf")])

    @tag("bug72159")
    def test_variable_call(self):
        content, positions = unmark_text(dedent("""\
            function testme() {
                return "";
            }
            var x = testme;
            var s = x();
            s.<1>xxx;    // Expect string completions
            x().<2>xxx;  // Test function chaining.
        """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("variable", "length"),
             ("function", "toLowerCase"),
             ("function", "indexOf")])
        self.assertCompletionsInclude(markup_text(content, pos=positions[2]),
            [("variable", "length"),
             ("function", "toLowerCase"),
             ("function", "indexOf")])

    @tag("bug76504")
    def test_function_completions(self):
        # Ensure we get completions on actual function hits.
        # http://bugs.activestate.com/show_bug.cgi?id=76504
        content, positions = unmark_text(dedent("""\
            function func_bug76504() { }
            func_bug76504.<1>xxx;

            var var_to_func_bug76504 = func_bug76504;
            var_to_func_bug76504.<2>xxx;
        """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("variable", "constructor"),
             ("variable", "length"),
             ("variable", "prototype"),
             ("variable", "length"),
             ("function", "apply"),
             ("function", "call"),
             ("function", "toString"),
             ("function", "valueOf"),
            ])
        self.assertCompletionsInclude(markup_text(content, pos=positions[2]),
            [("variable", "constructor"),
             ("variable", "length"),
             ("variable", "prototype"),
             ("variable", "length"),
             ("function", "apply"),
             ("function", "call"),
             ("function", "toString"),
             ("function", "valueOf"),
            ])

    def test_function_extra_completions(self):
        # Ensure we can get extra things off of functions we hang things off of
        content, positions = unmark_text(dedent("""\
            function func_extras() { }
            func_extras.hello = function() {};
            func_extras.<1>;
        """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("function", "hello"),
             ("function", "apply"),
            ])

    @tag("bug80880")
    def test_function_calltips(self):
        # Ensure we get calltips on actual function hits. Bug 80880.
        content, positions = unmark_text(dedent("""\
            function func_bug80880() { }
            func_bug80880.apply(<1>);

            var var_to_func_bug80880 = func_bug80880;
            var_to_func_bug80880.apply(<2>);
        """))
        calltip = dedent("""\
            apply(thisScope, args) -> Object
            Call the function/method, optionally setting a new scope for this and passing in parameters via an array.""")
        self.assertCalltipIs(markup_text(content, pos=positions[1]), calltip)
        self.assertCalltipIs(markup_text(content, pos=positions[2]), calltip)

    @tag("bug76711")
    def test_hash_completions(self):
        content, positions = unmark_text(dedent("""\
            var test_bug76711 = {
              'property' : value,
              'name': value
            }
            test_bug76711["<1>"];
            test_bug76711['<2>'];
        """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("variable", "name"),
             ("variable", "property"), ])
        self.assertCompletionsInclude(markup_text(content, pos=positions[2]),
            [("variable", "name"),
             ("variable", "property"), ])

    @tag("bug78185")
    def test_keyword_completions(self):
        content, positions = unmark_text(dedent("""\
            fun<1>ction fun<2>time() { }
            if (typ<3>) {}
        """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("keyword", "function"),
             ("function", "funtime"), ])
        # Should not trigger a names-completion after "function".
        self.assertNoTrigger(markup_text(content, pos=positions[2]))
        self.assertCompletionsInclude(markup_text(content, pos=positions[3]),
            [("keyword", "typeof"), ])

    @tag("bug78497")
    def test_object_assignment_ciling(self):
        content, positions = unmark_text(dedent("""\
            function class_bug78497(){
                this.ab={};
                this.ab['xyz']={one:1,"two":2};
                this.ab[unknownvar]={one:1,"two":2};
            }
            var inst_bug78497 = new class_bug78497();
            inst_bug78497.<1>;
        """))
        self.assertCompletionsAre(markup_text(content, pos=positions[1]),
            [("namespace", "ab"), ])

    @tag("bug90823")
    def test_implied_globals_not_exported(self):
        """Test that global variables that are implied and not assigned to do
           not get exported"""
        test_dir = join(self.test_dir, "test_implied_globals_not_exported")
        target_js_content, target_js_positions = unmark_text(dedent("""\
            exists.<1>dummy = 3;
            implicit.<2>no_such_prop = 4;
            function dummy() {
                var local = other.implicit.object;
                local.prop = 4;
                other.<3>;
            }
        """))

        manifest = {
            "other.js": dedent("""
                var exists = {};
                exists.newprop = 4;
                function foo() {
                    var local = implicit.object.reference;
                    local.prop = 3;
                    var dummy = exists.implicit.property;
                    dummy.prop = 4;
                }
             """),
            "target.js": target_js_content,
        }
        for file, content in manifest.items():
            path = join(test_dir, file)
            writefile(path, content)

        buf = self.mgr.buf_from_path(join(test_dir, "target.js"),
                                     lang="JavaScript")
        # make sure we picked up things from other.js
        self.assertCompletionsInclude2(buf, target_js_positions[1],
            [("variable", "newprop")])
        # but not implicitly declared properties on exported globals
        self.assertCompletionsDoNotInclude2(buf, target_js_positions[1],
            [("namespace", "implicit")])
        # also no implicitly declared globals
        self.assertCompletionsDoNotInclude2(buf, target_js_positions[2],
            [("namespace", "object")])
        # but we should get implicit properties in the same file
        self.assertCompletionsInclude2(buf, target_js_positions[3],
            [("namespace", "implicit")])

    @tag("bug91476")
    def test_function_alias_no_parens(self):
        """Test that assigning to method aliases does not result in completions
           that end with parentheses"""
        content, positions = unmark_text(dedent("""\
            (function () {
                var a = obj.foo();
                a.v = b;
                obj.<1>;
            })();
        """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("namespace", "foo")])
        self.assertCompletionsDoNotInclude(markup_text(content, pos=positions[1]),
            [("namespace", "foo()")])

    @tag("bug93858")
    def test_local_variable_completions(self):
        content, positions = unmark_text(dedent("""\
            function _somefunction() {
                var myWin;
                myW<1>;
            }
        """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("variable", "myWin")])

    def test_fat_arrow_functions(self):
        """Test fat arrow functions (ES6) for binding"""
        buf, pos = self._get_buf_and_data(dedent("""\
            function Class() {
                this.member = 1;
                this.private_method = arg_name => {
                    this.<1>;
                    arg<2>;
                };
                this.not_a_method = arg = > {
                    "There cannot be spaces between = and >";
                };
            }
            Class.prototype.method = function() {
                var callback = (arg1, arg2) => {
                    this.<3>;
                    arg<4>
                }
                var lambda = arg => this.<5>;
            };
        """), lang=self.lang)

        for i in (1, 3, 5):
            self.assertCompletionsInclude2(buf, pos[i],
                [("variable", "member"),
                 ("function", "method"),
                 ("function", "private_method")])
            self.assertCompletionsDoNotInclude2(buf, pos[i],
                [("function", "not_a_method")])
        self.assertCompletionsInclude2(buf, pos[2],
            [("argument", "arg_name")])
        self.assertCompletionsInclude2(buf, pos[4],
            [("argument", "arg1"),
             ("argument", "arg2")])

class DOMTestCase(CodeIntelTestCase):
    lang = "JavaScript"
    @tag("bug86391")
    def test_html_style_attribute(self):
        content, positions = unmark_text(dedent("""\
            document.getElementById("foo").<1>style.<2>;
        """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("variable", "style")])
        self.assertCompletionsInclude(markup_text(content, pos=positions[2]),
            [("variable", "background"),
             ("variable", "azimuth"),
             ("function", "getPropertyCSSValue"),
             ("function", "setProperty")])

class HTMLJavaScriptTestCase(CodeIntelTestCase):
    lang = "HTML"

    @tag("bug92394")
    def test_inside_html(self):
        content, positions = unmark_text(dedent("""\
            <html>
            <head>
                <script type="application/x-javascript" src="bar.js" />
                <script type="application/x-javascript">
                    document.<1>getElementById(<2>).<3>;
                </script>
            </head>
            <body>
            </html>
        """))

        self.assertCompletionsInclude(
                markup_text(content, pos=positions[1]),
                [("function", "getElementById")])
        self.assertCalltipIs(
                markup_text(content, pos=positions[2]),
                dedent("""\
                    getElementById(elementId)
                    Returns the Element whose ID is given by elementId. If no
                    such element exists, returns null."""))
        self.assertCompletionsInclude(markup_text(content, pos=positions[3]),
                [("variable", "nodeName"),
                 ("function", "appendChild"),])

    @tag("bug95946")
    def test_html_onattributes(self):
        content, positions = unmark_text(dedent("""\
            <html>
            <body onload="document.<1>getElementById(<2>).<3>;">
            </body>
            </html>
        """))

        self.assertCompletionsInclude(
                markup_text(content, pos=positions[1]),
                [("function", "getElementById")])
        self.assertCalltipIs(
                markup_text(content, pos=positions[2]),
                dedent("""\
                    getElementById(elementId)
                    Returns the Element whose ID is given by elementId. If no
                    such element exists, returns null."""))
        self.assertCompletionsInclude(markup_text(content, pos=positions[3]),
                [("variable", "nodeName"),
                 ("function", "appendChild"),])

    @tag("bug102993")
    def test_html5_canvas(self):
        content, positions = unmark_text(dedent("""\
            <!DOCTYPE html>
            <html>
            <head>
            <title>HTML 5 Canvas</title>
            <script type="text/javascript">
                function draw() {
                    var canvas = document.getElementById("canvas");
                    var ctx = canvas.getContext("2d");
                    ctx.fillStyle = "rgb(200,0,0)";
                    document.<1>foo;
                }
            </script>
            </head>
            <body onload="draw()">
            <canvas id='canvas' width="300" height="300">
                Fallback text when canvas is not available.
            </canvas>
            </body>
            </html>
        """))

        self.assertCompletionsInclude(
                markup_text(content, pos=positions[1]),
                [("function", "getElementById")])

class JSDocTestCase(CodeIntelTestCase):
    lang = "JavaScript"
    def test_jsdoc_extends(self):
        content, positions = unmark_text(dedent("""\
            function myfoo1() {
                this.foo1 = 1;
            }
            function myfoo2() {
                this.foo2 = 2;
            }
            /**
             * @extends myfoo1
             * @extends myfoo2
             */
            function myinheritor() {
                this.<1>x = 1;
            }
        """))
        self.assertCompletionsAre(markup_text(content, pos=positions[1]),
            [("variable", "foo1"),
             ("variable", "foo2"),
             ("variable", "x")])

    @tag("bug93261")
    def test_jsdoc_object_extends(self):
        content, positions = unmark_text(dedent("""\
            var Foo = {
                'f1': 1
            }
            /**
             * @extends Foo
             */
            var Foo2 = {
                'f2': 2
            }
            var myfoo2 = new Foo2();
            myfoo2.<1>x = 1;
        """))
        self.assertCompletionsAre(markup_text(content, pos=positions[1]),
            [("variable", "f1"),
             ("variable", "f2")])

    @tag("bug92803")
    def test_jsdoc_type_comments(self):
        content, positions = unmark_text(dedent("""\
            function Foopy() {
                this.poit = 1;
            }
            var obj = {
                /** @type Foopy */
                foo: undefined,
                /** @type {Foopy} */
                bar: undefined,
                /** @type {Foopy} Now With Comments */
                baz: undefined,
            };
            obj.foo.<1>x;
            obj.bar.<2>y;
            obj.bar.<3>z;
        """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("variable", "poit")])
        self.assertCompletionsInclude(markup_text(content, pos=positions[2]),
            [("variable", "poit")])
        self.assertCompletionsInclude(markup_text(content, pos=positions[3]),
            [("variable", "poit")])

    @tag("bug98344", "knownfailure")
    def test_jsdoc_type_comments(self):
        content, positions = unmark_text(dedent("""\
            function Blah() {
                /** @type Array */
                Object.defineProperty(this, "propName", { get: function() { return something}});
            }
            b = new Blah();
            b.propNam.<1>;
        """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("method", "push"), ("method", "shift")])

class MochiKitTestCase(CodeIntelTestCase):
    lang = "JavaScript"

    @tag("bug62967")
    def test_basics(self):
        env = SimplePrefsEnvironment(codeintel_selected_catalogs=['mochikit'])
        content, positions = unmark_text(dedent("""\
            MochiKit.<1>Visual.<2>roundElement(<3>);
            roundElement(<4>);

            MochiKit.<5>DateTime.<6>toISODate(<7>);
            toISODate(<8>);
        """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("namespace", "Visual"), ("namespace", "DateTime")],
            env=env)
        self.assertCompletionsInclude(markup_text(content, pos=positions[2]),
            [("function", "roundElement"), ("function", "roundClass")],
            env=env)
        calltip = dedent("""\
            roundElement(element[, options])
            Immediately round the corners of the specified element.
            element: An element ID string or a DOM node (see
            MochiKit.DOM.getElement).""")
        self.assertCalltipIs(markup_text(content, pos=positions[3]),
            calltip, env=env)
        self.assertCalltipIs(markup_text(content, pos=positions[4]),
            calltip, env=env)

        self.assertCompletionsInclude(markup_text(content, pos=positions[5]),
            [("namespace", "Visual"), ("namespace", "DateTime")],
            env=env)
        self.assertCompletionsInclude(markup_text(content, pos=positions[6]),
            [("function", "toISODate"),
             ("function", "toAmericanDate")],
            env=env)
        calltip = dedent("""\
            toISODate(date)
            Convert a Date object to an ISO 8601 [1] date string (YYYY-
            MM-DD) Availability: Available in MochiKit 1.3.1+""")
        self.assertCalltipIs(markup_text(content, pos=positions[7]),
            calltip, env=env)
        self.assertCalltipIs(markup_text(content, pos=positions[8]),
            calltip, env=env)

    @tag("bug63228")
    def test_repr_with_collision(self):
        # There had been some collision btwn repr() in mochikit and dojo that
        # causes:
        #    ...
        #      File ".../codeintel2/tree_javascript.py", line 68, in eval_calltips
        #        return self._calltips_from_hits(hits)
        #      File ".../codeintel2/tree_javascript.py", line 249, in _calltips_from_hits
        #        calltips.append(self._calltip_from_class(elem))
        #      File ".../codeintel2/tree_javascript.py", line 230, in _calltip_from_class
        #        ctor = elem.names[name]
        #    KeyError: 'repr'
        #    test_repr_with_collision (test_javascript.MochiKitTestCase) ... FAIL
        env = SimplePrefsEnvironment(
                codeintel_selected_catalogs=['mochikit', 'dojo'])
        self.assertCalltipIs("repr(<|>)",
            ('repr(obj)\n'
             'Return a programmer representation for obj. See the\n'
             'Programmer Representation overview for more information\n'
             'about this function.'),
            env=env)

    @tag("bug59477", "knownfailure")
    def test_deferred(self):
        env = SimplePrefsEnvironment(codeintel_selected_catalogs=['mochikit'])
        content, positions = unmark_text(dedent("""\
            function gotDocument(json) { /* ... */ }
            function delay(res) { return wait(2.0, res); }
            var d = loadJSONDoc('example.json');
            d.<1>addCallback(<2>delay);
            d.addCallback(gotDocument);   
        """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("function", "addCallback"), ("function", "addErrback"),
             ("function", "cancel")],
            env=env)
        self.assertCalltipIs(markup_text(content, pos=positions[2]),
            "addCallback(...) blah blah", env=env)

    @tag("bug65370")
    def test_class_ctor(self):
        env = SimplePrefsEnvironment(codeintel_selected_catalogs=['mochikit'])
        expected_signature = """Logger([maxSize])
A basic logger object that has a buffer of recent messages
plus a listener dispatch mechanism for "real-time" logging
of important messages. maxSize is the maximum number of
entries in the log."""

        content, positions = unmark_text(dedent("""\
            var log = new MochiKit.Logging.Logger(<1>);
            log.<2>xyz();
        """))
        self.assertCalltipIs(markup_text(content, pos=positions[1]),
            expected_signature, env=env)
        self.assertCompletionsInclude(markup_text(content, pos=positions[2]),
            [("function", "addListener"),
             ("function", "baseLog"),
             ("function", "clear")],
            env=env)


class DojoTestCase(CodeIntelTestCase):
    lang = "JavaScript"

    _ci_env_prefs_ = {
        "codeintel_selected_catalogs": ["dojo"],
    }

    @tag("bug63087")
    def test_toplevel(self):
        content, positions = unmark_text(dedent("""\
            dojo.<1>addOnLoad(<2>);
            dojo.byId(<3>);
        """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("function", "addOnLoad"), ("function", "byId"),
             ("function", "require")])
        expectedCalltip = "addOnLoad(obj)\nRegisters a function to be " \
                          "triggered after the DOM and dojo.require() calls " \
                          "have finished loading."
        self.assertCalltipIs(markup_text(content, pos=positions[2]),
                             expectedCalltip)
        expectedCalltip = "byId(id,doc)\nReturns DOM node with matching `id` " \
                          "attribute or `null` if not found. If `id` is a " \
                          "DomNode, this function is a no-op."
        self.assertCalltipIs(markup_text(content, pos=positions[3]),
                             expectedCalltip)

    @tag("bug75069")
    def test_dojo_extend(self):
        """Test the handling of dojo.extend"""
        content, positions = unmark_text(dedent("""\
            function class_bug75069 {
                this.name = 'bug75069';
            }
            dojo.extend(class_bug75069, {
                extended_fn: function() {
                    // Do something
                }
            });
            var inst_bug75069 = new class_bug75069();
            inst_bug75069.<1>
        """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("variable", "name"),
             ("function", "extended_fn")])

    @tag("bug75069")
    def test_dojo_declare(self):
        """Test the handling of dojo.declare"""
        content, positions = unmark_text(dedent("""\
            // Same code from the Dojo wiki documentation:
            // http://manual.dojotoolkit.org/WikiHome/DojoDotBook/Book20
            // Note: Dojo (0.9+) uses "constructor" instead of "initializer"
            dojo.declare("Person_bug75069", null, {
                    //acts like a java constructor
                    constructor: function(name, age, currentResidence) {
                        this.name=name;
                        this.age=age;
                        this.currentResidence=currentResidence;
                    },
            
                    moveToNewCity: function(newState) 
                    {
                        this.currentResidence=newState;
                    } 
            });
            var matt_bug75069 = new Person_bug75069(<1>'Matt', 25, 'New Mexico');
            matt_bug75069.<2>moveToNewCity(<3>
        """))
        self.assertCalltipIs(markup_text(content, pos=positions[1]),
            "Person_bug75069(name, age, currentResidence)")
        self.assertCompletionsInclude(markup_text(content, pos=positions[2]),
            [("variable", "name"),
             ("variable", "age"),
             ("variable", "currentResidence"),
             ("function", "moveToNewCity")])
        self.assertCalltipIs(markup_text(content, pos=positions[3]),
            "moveToNewCity(newState)")


class YUITestCase(CodeIntelTestCase):
    lang = "JavaScript"
    _ci_env_prefs_ = {
        "codeintel_selected_catalogs": ["yui"],
        "codeintel_max_recursive_dir_depth": 10,
    }

    def test_toplevel(self):
        self.assertCompletionsInclude("YAHOO.<|>",
            [("namespace", "util"), ("namespace", "widget")])

    @tag("bug63258", "bug63297")
    def test_util(self):
        # Try more than once to test alternate code path after caching.
        for i in range(2):
            self.assertCompletionsInclude("YAHOO.<|>util",
                [("namespace", "util")])
            self.assertCompletionsInclude("YAHOO.<|>util.<|>",
                [("class", "Anim"), 
                 ("class", "DD"),
                 ("namespace", "Dom"), # bug 63297
                ])
            # bug 63258
            self.assertCompletionsInclude("YAHOO.<|>util.DD.<|>",
                [("function", "alignElWithMouse"), 
                 ("function", "autoScroll"),
                 ("variable", "scroll"),
                ])

    @tag("bug60048")
    def test_yui_with_local_YAHOO(self):
        self.assertCompletionsInclude(
            dedent("""\
                YAHOO.util.Easing.<|>;

                YAHOO.example.init = function() {   
                  var anim = new YAHOO.util.Anim('demo', { width: {to: 500} }, 1,
                                 YAHOO.util.Easing.);
                  YAHOO.util.Event.on(document, 'click', anim.animate, anim, true);
                };
                YAHOO.util.Event.onAvailable('demo', YAHOO.example.init);
            """),
            [("function", "easeBoth"), ("function", "bounceIn")])


class PrototypeTestCase(CodeIntelTestCase):
    lang = "JavaScript"
    env = SimplePrefsEnvironment(codeintel_selected_catalogs=['prototype'])

    @tag("bug63098")
    def test_dollar_func(self):
        self.assertCalltipIs("$(<|>)",
            ("$(elementId [, ...]) --> Element\n"
             "The $() function is a handy shortcut to the all-too-frequent\n"
             "document.getElementById() function of the DOM. Like the DOM\n"
             "function, this one returns the element that has the id\n"
             "passed as an argument."),
            env=self.env)

    def test_basics(self):
        # Some basic prototype definitions.
        content, positions = unmark_text(dedent("""\
            Ajax.<1>activeRequestCount;
            Enumerable.<2>each(<3>);
        """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("variable", "activeRequestCount"),
             ("namespace", "Responders"),
             ("function", "getTransport"),
             ("class", "Base")],
            env=self.env)
        self.assertCompletionsInclude(markup_text(content, pos=positions[2]),
            [("function", "each"),
             ("function", "all"),
             ("function", "grep")],
            env=self.env)
        self.assertCalltipIs(markup_text(content, pos=positions[3]),
            ("each(iterator)\n"
             "Calls the given iterator function passing each element in\n"
             "the list in the first argument and the index of the element\n"
             "in the second argument"),
            env=self.env)
        
    @tag("bug63137", "bug63208")
    def test_extend_builtins1(self):
        # Test some of the places in which prototype extends JS builtins.
        content, positions = unmark_text(dedent("""\
            String.<1>stripTags(<2>);
        """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("function", "toUpperCase"),   # from JS String
             ("variable", "length"),        # from JS String
             ("function", "toString"),      # from JS Object
             ("function", "stripTags"),     # from Prototype's String
             ("function", "camelize"),      # from Prototype's String
             ("function", "inspect"),       # from Prototype's Object
             ],
            env=self.env)
        self.assertCalltipIs(markup_text(content, pos=positions[2]),
            ("stripTags()\n"
             "Returns the string with any HTML or XML tags removed"),
            env=self.env)

    @tag("bug63137")
    def test_extend_builtins2(self):
        # Test some of the places in which prototype extends JS builtins.
        content, positions = unmark_text(dedent("""\
            document.<3>getElementsByClassName(<4>);
        """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[3]),
            [("function", "getElementById"),            # from JS
             ("function", "getElementsByClassName"),    # from Prototype
             ],
            env=self.env)
        self.assertCalltipIs(markup_text(content, pos=positions[4]),
            ("getElementsByClassName(className [, parentElement])\n"
             "Returns all the elements that are associated with the given\n"
             "CSS class name. If no parentElement id given, the entire\n"
             "document body will be searched."),
            env=self.env)

    @tag("bug63297", "knownfailure")
    def test_self_invoking_functions(self):
        # XXX - I'm still not 100% sure this is correct and viable js syntax
        content, positions = unmark_text(dedent("""\
            (function() {
              TestCode = function(a1) {
                  this.a1 = a1;
              }
              TestCode.prototype = {
                  c1: "c1",
                  test: function() {},
                  enabled: true
              }
            })();
            t = new TestCode(<1>"a1");
            t.<2>c1 = "new c1";
        """))
        self.assertCalltipIs(markup_text(content, pos=positions[1]),
            ("TestCode(a1)"))
        self.assertCompletionsInclude(markup_text(content, pos=positions[2]),
            [("variable", "a1"),
             ("variable", "c1"),
             ("function", "test"),
             ("variable", "enabled")])

    @tag("bug65197")
    def test_multiple_variable_assignment(self):
        content, positions = unmark_text(dedent("""\
            TestCode = function(a1) {
                this.a1 = a1;
            }
            TestCode.prototype = {
                c1: "c1",
                test: function() {},
                enabled: true
            }
            var x;
            var t = x = new TestCode("a1");
            t.<1>c1 = "new c1";
            x.<2>test();

            var item1 = 7, item2 = 'cat', item3 = [];
            item2.<3>toString();
            item3.<4>toString();
        """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("variable", "a1"),
             ("variable", "c1"),
             ("function", "test"),
             ("variable", "enabled")])
        self.assertCompletionsInclude(markup_text(content, pos=positions[2]),
            [("variable", "a1"),
             ("variable", "c1"),
             ("function", "test"),
             ("variable", "enabled")])
        self.assertCompletionsInclude(markup_text(content, pos=positions[3]),
            [("function", "toUpperCase"),   # from JS String
             ("variable", "length"),        # from JS String
             ("function", "toString"),      # from JS Object
             ])
        self.assertCompletionsInclude(markup_text(content, pos=positions[4]),
            [("function", "push"),          # from JS Array
             ("variable", "length"),        # from JS Array
             ("function", "toString"),      # from JS Object
             ])

    @tag("knownfailure", "bug63717")
    def test_try_calltip(self):
        # Note that *creating a Try instance* isn't really typical
        # usage:
        #   http://www.sergiopereira.com/articles/prototype.js.html#TryThese
        self.assertCalltipIs("Try(<|>", "Try(...)", env=self.env)

    @tag("bug62767")
    def test_complete_names(self):
        content, positions = unmark_text(dedent("""\
            var bug62767 = "My bug";
            function bug62767_function(args) {};
            function bug62767_class(args) { this.args = args };
            bug62767_class.prototype.somefunc = function() {};

            bug<1>
        """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("variable", "bug62767"),
             ("function", "bug62767_function"),
             ("class", "bug62767_class")])

    @tag("bug62767")
    def test_complete_names_for_bultins(self):
        content, positions = unmark_text(dedent("""\
            # Test we get global variables like window.
            var mywindow = win<1>;
            # Test we get all window defined variables as well.
            doc<2>;
            # Check for cplns at different positions.
            var myvar = 1 + par<3>;
            1 + (par<4>);
            x += par<5>;
            field | par<6>;
        """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("variable", "window")])
        self.assertCompletionsInclude(markup_text(content, pos=positions[2]),
            [("variable", "document")])
        self.assertCompletionsInclude(markup_text(content, pos=positions[3]),
            [("function", "parseFloat"), ("function", "parseInt")])
        self.assertCompletionsInclude(markup_text(content, pos=positions[4]),
            [("function", "parseFloat"), ("function", "parseInt")])
        self.assertCompletionsInclude(markup_text(content, pos=positions[5]),
            [("function", "parseFloat"), ("function", "parseInt")])
        # We should not trigger here.
        self.assertNoTrigger("window.        doc<|>;")


# ext JS framework
class ExtTestCase(CodeIntelTestCase):
    lang = "JavaScript"
    env = SimplePrefsEnvironment(codeintel_selected_catalogs=['ext'])

    #def test_toplevel(self):
    #    self.assertCompletionsInclude("YAHOO.<|>",
    #        [("variable", "util"), ("variable", "widget")])

    @tag("bug70684")
    def test_intelligent_type_scanning(self):
        # Try more than once to test alternate code path after caching.
        content, positions = unmark_text(dedent("""\
            Ext = {};
            Ext.Element = function(element, forceNew) {
                this.dom = element;
            }
            var El = Ext.Element;
            El.prototype = {
                originalDisplay : "",
                visibilityMode : 1
            }
            var myElem = new Ext.Element();
            myElem.<1>;
        """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("variable", "dom"),
             ("variable", "originalDisplay"),
             ("variable", "visibilityMode"),
             ])


class ExtendTestCase(CodeIntelTestCase):
    lang = "JavaScript"
    test_dir = join(os.getcwd(), "tmp")

    @tag("bug63258", "yui")
    def test_yahoo_extend(self):
        content, positions = unmark_text(dedent("""\
            function Mammal(name){ 
                    this.name=name;
                    this.offspring=[];
            }
            Mammal.prototype.haveABaby=function(){ 
                    var newBaby=new Mammal("Baby "+this.name);
                    this.offspring.push(newBaby);
                    return newBaby;
            }
            Mammal.prototype.toString=function(){ 
                    return '[Mammal "'+this.name+'"]';
            }
            
            function Dog(name) {
                    this.name=name;
            }
            YAHOO.extend(Dog, Mammal, {
                    colour: 'brown',
                    toString: function() {
                            return '[Dog "'+this.name+'"]';
                    }
            });
            
            var myDog = new Dog('Rover');
            myDog.<1>haveABaby();
        """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("variable", "name"),          # From Dog
             ("variable", "offspring"),     # From Mammel
             ("variable", "colour"),        # From Dog extension
             ("function", "toString"),      # From Dog extension
             ("function", "haveABaby")])    # From Mammel


class DefnTestCase(CodeIntelTestCase):
    lang = "JavaScript"
    test_dir = join(os.getcwd(), "tmp")

    def test_citdl_expr_under_pos_simple(self):
        self.assertCITDLExprUnderPosIs("foo.<|>", "foo")
        self.assertCITDLExprUnderPosIs("foo.bar<|>", "foo.bar")
        self.assertCITDLExprUnderPosIs("f<|>oo.bar", "foo")
        self.assertCITDLExprUnderPosIs("foo(bar.<|>", "bar")
        self.assertCITDLExprUnderPosIs("foo[b<|>ar.", "bar")
        self.assertCITDLExprUnderPosIs("foo{bar.<|>", "bar")
        self.assertCITDLExprUnderPosIs("foo().<|>", "foo()")
        self.assertCITDLExprUnderPosIs("foo(a,b).<|>", "foo()")
        self.assertCITDLExprUnderPosIs("a = fo<|>o.", "foo")
        self.assertCITDLExprUnderPosIs("a = foo(ba<|>r., blam)", "bar")
        self.assertCITDLExprUnderPosIs("blam()\nfoo.<|>", "foo")
        self.assertCITDLExprUnderPosIs("blam()\nfoo.bar.<|>", "foo.bar")
        # Ensure we only grab the correct context, and not too much
        self.assertCITDLExprUnderPosIs("foo.bar.baz<|>", "foo.bar.baz")
        self.assertCITDLExprUnderPosIs("foo.b<|>ar.baz", "foo.bar")
        self.assertCITDLExprUnderPosIs("<|>foo.bar.baz", "foo")
    def test_citdl_expr_under_pos_multiline(self):
        self.assertCITDLExprUnderPosIs("foo(bar,\nblam.<|>)", "blam")
        self.assertCITDLExprUnderPosIs("foo(bar,\nblam).spam.<|>", "foo().spam")
        self.assertCITDLExprUnderPosIs("foo.\\\nbar.<|>", "foo.bar")
        self.assertCITDLExprUnderPosIs("foo(1, // one\n2).bar.<|>", "foo().bar")
        self.assertCITDLExprUnderPosIs("foo(1, // o)ne\n2).b<|>ar.", "foo().bar")
        self.assertCITDLExprUnderPosIs("foo(1, // (o)ne\n2).bar.<|>", "foo().bar")
        self.assertCITDLExprUnderPosIs("foo(1, // (one\n2).bar.<|>", "foo().bar")
        self.assertCITDLExprUnderPosIs("foo( //this is a ) comment\nb,d).<|>", "foo()")
        self.assertCITDLExprUnderPosIs("foo\\\n(',({[', {one:1,two:2}).<|>", "foo()")
    def test_citdl_expr_under_pos_extra(self):
        self.assertCITDLExprUnderPosIs("if (foo.<|>(", "foo")
        self.assertCITDLExprUnderPosIs("else if (foo.<|>(", "foo")
        self.assertCITDLExprUnderPosIs("while (foo.<|>(", "foo")
        self.assertCITDLExprUnderPosIs("foo.pr<|>ototype(", "foo.prototype")

    def test_simple(self):
        test_dir = join(self.test_dir, "test_defn_simple")
        foo_content, foo_positions = unmark_text(dedent("""\
            function test1(i) {
                var b = 0;
                if (i > 0) {
                    b = i;
                }
            }
            
            t = test<1>1(0);
        """))

        path = join(test_dir, "foo.js")
        writefile(path, foo_content)

        buf = self.mgr.buf_from_path(path)
        self.assertDefnMatches2(buf, foo_positions[1],
            ilk="function", name="test1", line=1, path=path, )
        
    @tag("bug99108")
    def test_scope_scopestart_is_int(self):
        test_dir = join(self.test_dir, "test_defn_scope_scopestart_is_int")
        foo_content, foo_positions = unmark_text(dedent("""\
            // Leading comments and stuff
            // La dee dah
            // var stump = "trees";
            function test1(i)<4> {
                var b = 0;
                if (i > 0) {
                    b = i;
                }
                var cheeseboogie = function bebsi(j) {
                    return b + j;
                }
                return cheeseboogie<2>(i + 1);
            }    
            var t = test<1>1(0)<3>;
            print(t);
        """))
        path = join(test_dir, "scope_bounds.js")
        writefile(path, foo_content)
        buf = self.mgr.buf_from_path(path)
        self.assertDefnMatches2(buf, foo_positions[1],
            ilk="function", name="test1", line=4,
                                lpath=[],
            scopestart=1, scopeend=0, path=path, )
        self.assertDefnMatches2(buf, foo_positions[2],
            ilk="function", name="cheeseboogie", line=9,
                                lpath=['test1'],
            scopestart=4, scopeend=13, path=path, )
        self.assertScopeLpathIs(
            markup_text(foo_content, pos=foo_positions[3]),
            [])
        self.assertScopeLpathIs(
            markup_text(foo_content, pos=foo_positions[4]),
                                ["test1"])


    @tag("knownfailure")
    def test_simple_import(self, fn=None):
        test_dir = join(self.test_dir, "test_simple_import")
        foo_content, foo_positions = unmark_text(dedent("""\
            <html>
            <head>
                <script type="application/x-javascript" src="bar.js" />
                <script type="application/x-javascript">
                    t = test<1>1(0);
                </script>
            </head>
            <body>
            </html>
        """))

        bar_content, bar_positions = unmark_text(dedent("""\
            function test1(i)<2> {
                var b = 0;
                if (i > 0) {
                    b = i;
                }
            }
        """))

        manifest = [
            ("bar.js", bar_content),
            ("foo.js", foo_content),
        ]
        for file, content in manifest:
            path = join(test_dir, file)
            writefile(path, content)

        bar_lines = lines_from_pos(bar_content, bar_positions)

        buf = self.mgr.buf_from_path(join(test_dir, "foo.js"))

        if fn is None:
            fn = self.assertDefnMatches2
        fn(buf, foo_positions[1],
            ilk="function", name="test1", line=bar_lines[2],
            path=join(test_dir, "bar.js"), )

    def test_simple_import_incorrect_order(self):
        self.test_simple_import(fn=self.assertDefnIncludes)

    @tag("bug65366")
    def test_duplicate_defns(self):
        # Setup
        test_dir = join(self.test_dir, "test_duplicate_defns")
        foo_path = join(test_dir, "foo.js")
        foo_content, foo_positions = unmark_text(dedent("""\
            function startSessionInterval()
            {
                // 5second ping
                sessionK<1>eepAlive(); // just to get an answer fast.
                var sessionInterval = setInterval(sessionKeepAlive, 5000);
            };

            function sessionKeepAlive()
            {
                //...
            };
        """))
        writefile(foo_path, foo_content)

        # Test away...
        buf = self.mgr.buf_from_path(foo_path)
        self.assertNoDuplicateDefns2(buf, foo_positions[1])

    def test_defn_at_defn(self):
        """Test looking up definitions at the definition site"""
        test_dir = join(self.test_dir, "test_defn_at_defn")
        path = join(test_dir, "foo.js")
        content, positions = unmark_text(dedent("""\
            function Class<1>() {
                this._foo<2> = 3;
            }
            Class.prototype.getFoo<3> = function() {
                var bar<4> = this._foo<5> + 1;
                return bar<6>;
            }
            var c<7> = Class<8>();
            print(c<9>.getFoo<10>());
        """))
        writefile(path, content);
        lines = lines_from_pos(content, positions);
        buf = self.mgr.buf_from_path(path);

        self.assertDefnMatches2(buf, path=path, pos=positions[1],
                                ilk="class", name="Class", line=lines[1])
        self.assertDefnMatches2(buf, path=path, pos=positions[2],
                                ilk="variable", name="_foo", line=lines[2])
        self.assertDefnMatches2(buf, path=path, pos=positions[3],
                                ilk="function", name="getFoo", line=lines[3])
        self.assertDefnMatches2(buf, path=path, pos=positions[4],
                                ilk="variable", name="bar", line=lines[4])
        self.assertDefnMatches2(buf, path=path, pos=positions[5],
                                ilk="variable", name="_foo", line=lines[2])
        self.assertDefnMatches2(buf, path=path, pos=positions[6],
                                ilk="variable", name="bar", line=lines[4])
        self.assertDefnMatches2(buf, path=path, pos=positions[7],
                                ilk="variable", name="c", line=lines[7])
        self.assertDefnMatches2(buf, path=path, pos=positions[8],
                                ilk="class", name="Class", line=lines[1])
        self.assertDefnMatches2(buf, path=path, pos=positions[9],
                                ilk="variable", name="c", line=lines[7])
        self.assertDefnMatches2(buf, path=path, pos=positions[10],
                                ilk="function", name="getFoo", line=lines[3])

    @tag("bug70438")
    def test_list_tuple_exception(self):
        test_dir = join(self.test_dir, "test_defn_list_tuple_exception")
        path = join(test_dir, "bug70438.js")
        content, positions = unmark_text(dedent("""\
            var ko = {};
            ko.test = {};
            ko.test.func_test = function() { };
            ko.test.class_test = function() { this.var1 = 1; };
            ko.test.class_test.prototype.getName = function() { };
            var t1 = ko.test.func<1>_test();
            var t2 = new ko.test.class<2>_test();
            t2.getNa<3>me();
             """))
        writefile(path, content)

        buf = self.mgr.buf_from_path(path)
        self.assertDefnMatches2(buf, positions[1],
            ilk="function", name="func_test", line=3, path=path, )
        self.assertDefnMatches2(buf, positions[2],
            ilk="class", name="class_test", line=4, path=path, )
        self.assertDefnMatches2(buf, positions[3],
            ilk="function", name="getName", line=5, path=path, )


#---- mainline

if __name__ == "__main__":
    unittest.main()


