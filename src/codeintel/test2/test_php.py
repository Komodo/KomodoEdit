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

"""Test some PHP-specific codeintel handling."""

import os
import sys
import re
from os.path import join, dirname, abspath, exists, basename, expanduser
import unittest
import logging
from glob import glob

import which

from codeintel2.common import *
from codeintel2.util import indent, dedent, banner, markup_text, unmark_text
from codeintel2.environment import SimplePrefsEnvironment
from codeintel2.tree_php import (php_magic_global_method_data,
                                 php_magic_class_method_data)

from testlib import TestError, TestSkipped, TestFailed, tag
from citestsupport import CodeIntelTestCase, writefile, init_xml_catalogs



log = logging.getLogger("test")
HTML_DOCTYPE = '''<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN">\n'''


def php_markup(s):
    return "<?php %s ?>" % (s)
php_markup_offset = len("<?php ")

def all_available_phps():
    yielded = {}
    exe_names = ("php", "php4", "php-cgi", "php-cli")
    for exe_name in exe_names:
        for php in which.whichall(exe_name):
            yielded[php] = True
            yield php
    if sys.platform == "win32":
        for dir in glob(r"C:\PHP*"):
            php = join(dir, "php.exe")
            if exists(php) and php not in yielded:
                yielded[php] = True
                yield php
    else:
        for dir in glob(expanduser("~/opt/php/*")):
            for exe_name in exe_names:
                php = join(dir, "bin", exe_name)
                if exists(php) and php not in yielded:
                    yielded[php] = True
                    yield php



class LibsTestCase(CodeIntelTestCase):
    def test_with_all_phps(self):
        # Test that the PHP libs processing works for all available
        # PHPs.
        import which

        env = SimplePrefsEnvironment()
        buf = self.mgr.buf_from_content(
                "<?php php_info(); ?>", "PHP", path="foo.php", env=env)

        for php in all_available_phps():
            env.set_pref("php", php)
            #TODO: actually assert something about the libs?
            buf.libs


class TriggerTestCase(CodeIntelTestCase):
    lang = "PHP"
    test_dir = join(os.getcwd(), "tmp")

    def test_trigger_complete_object_members(self):
        # Triggers after "->" on $variables
        #                "::" on identifiers
        #
        #    Samples:
        #        $a->myfunc();
        #        $b = $a->b;
        #        $this->func1(xyz);
        #        self::func1(xyz);
        #        parent::funcInParent(xyz);
        #        MyClass::func1(xyz);
        name = "php-complete-object-members"
        self.assertTriggerMatches(php_markup("$a-><|>myfunc();"),
                                  name=name, pos=10)
        self.assertTriggerMatches(php_markup("$this-><|>myfunc();"),
                                  name=name, pos=13)
        self.assertTriggerMatches(php_markup("$foo->bar-><|>foobar;"),
                                  name=name, pos=17)
        self.assertTriggerMatches(php_markup("$foo->bar()-><|>foobar;"),
                                  name=name, pos=19)
        self.assertTriggerMatches(php_markup("$foo->bar('sludge')-><|>foobar;"),
                                  name=name, pos=27)
        self.assertTriggerMatches(php_markup("$foo->bar('sludge', $x, 5)-><|>foobar;"),
                                  name=name, pos=34)
        # Test using the scope resolution operator "::"
        name = "php-complete-static-members"
        self.assertTriggerMatches(php_markup("myclass::<|>myfunc();"),
                                  name=name, pos=15)
        self.assertTriggerMatches(php_markup("self::<|>myfunc();"),
                                  name=name, pos=12)
        self.assertTriggerMatches(php_markup("parent::<|>myfunc();"),
                                  name=name, pos=14)
        # No trigger before or after the correct position
        #self.assertNoTrigger(php_markup("$a->myfunc();"))
        self.assertNoTrigger(php_markup("$a-<|>>myfunc();"))
        self.assertNoTrigger(php_markup("$a->m<|>yfunc();"))
        # No trigger on python like syntax
        self.assertNoTrigger(php_markup("abc.<|>def"))
        # assert no trig in strings
        self.assertNoTrigger('<?php $s = "$a-><|>alert(def);"; ?>')
        self.assertNoTrigger(php_markup("$s = '$a-><|>alert(def);';r"))
        # assert no trig in comments
        self.assertNoTrigger('''<?php /*
                                 * $myfunc-><|>callthis(arg1);
                                 */ ?>''')
        self.assertNoTrigger('<?php // $myfunc-><|>callthis(arg1); ?>')
        self.assertNoTrigger('<?php # MyClass::<|>callthis(arg1); ?>')

    def test_trigger_complete_functions(self):
        # Triggers after $ and one character
        #
        #    Samples:
        #        "$H" -> ["HTTP_COOKIE_VARS", "HTTP_ENV_VARS", ...]
        name = "php-complete-functions"
        self.assertTriggerMatches(php_markup("$i = arr<|>ay_pop($a);"),
                                  name=name, pos=11)
        # No trigger before or after the correct position
        self.assertNoTrigger(php_markup("$i = ar<|>ray_pop($a);"))
        self.assertNoTrigger(php_markup("$i = arra<|>y_pop($a);"))

    def test_trigger_complete_variables(self):
        # Triggers after $ and one character
        #
        #    Samples:
        #        "$H" -> ["HTTP_COOKIE_VARS", "HTTP_ENV_VARS", ...]
        name = "php-complete-variables"
        self.assertTriggerMatches(php_markup("$H<|>TTP_COOKIE_VARS['xxx'];"),
                                  name=name, pos=7)
        # No trigger before or after the correct position
        self.assertNoTrigger(php_markup("$<|>HTTP_COOKIE_VARS['xxx'];"))
        self.assertNoTrigger(php_markup("$HT<|>TP_COOKIE_VARS['xxx'];"))

    def test_trigger_complete_classes_from_new(self):
        # Triggers after "new "
        #
        #    Samples:
        #        "new <|>" -> ["ArrayObject", "Exception", ...]
        name = "php-complete-classes"
        self.assertTriggerMatches(php_markup("$e = new <|>Exception();"),
                                  name=name, pos=15)
        # No trigger before or after the correct position
        self.assertNoTrigger(php_markup("$e = new  <|>Exception();"))
        self.assertTriggerDoesNotMatch(php_markup("$e = new<|> Exception();"),
                                       name=name)

    def test_trigger_complete_classes_from_extends(self):
        # Triggers after "extends "
        #
        #    Samples:
        #        "class MyException extends <|>Exception" -> ["ArrayObject", "Exception", ...]
        name = "php-complete-classes"
        self.assertTriggerMatches(php_markup("class MyException extends <|>Exception {}"),
                                  name=name, pos=32)
        # No trigger before or after the correct position
        self.assertTriggerDoesNotMatch(php_markup("class MyException extends<|> Exception {}"),
                                       name=name)
        self.assertNoTrigger(php_markup("class MyException extends E<|>xception {}"))

    def test_trigger_complete_interfaces(self):
        # Triggers after "implements "
        #
        #    Samples:
        #        "class MyException implements <|>IException" -> ["IArrayObject", "IException", ...]
        name = "php-complete-interfaces"
        self.assertTriggerMatches(php_markup("class MyException implements <|>IException {}"),
                                  name=name, pos=35)
        # No trigger before or after the correct position
        self.assertTriggerDoesNotMatch(php_markup("class MyException implements<|> IException {}"),
                                       name=name)
        self.assertNoTrigger(php_markup("class MyException implements I<|>Exception {}"))

    def test_trigger_complete_classes_from_multiple_extends(self):
        # Triggers after "extends Class1, "
        #
        #    Samples:
        #        "class MyException extends <|>Exception" -> ["ArrayObject", "Exception", ...]
        name = "php-complete-classes"
        self.assertTriggerMatches(php_markup("class MyException extends ArrayObject, <|>Exception {}"),
                                  name=name, pos=45)
        # No trigger before or after the correct position
        self.assertNoTrigger(php_markup("class MyException extends ArrayObject,<|> Exception {}"))
        self.assertNoTrigger(php_markup("class MyException extends ArrayObject, E<|>xception {}"))

    def test_trigger_complete_classes_from_multiple_implements(self):
        # Triggers after "implements Class1, "
        #
        #    Samples:
        #        "class MyException implements IException, <|>" -> ["IArrayObject", "IExceptionHelper", ...]
        name = "php-complete-interfaces"
        self.assertTriggerMatches(php_markup("class MyException implements IArrayObject, <|>IException {}"),
                                  name=name, pos=49)
        # No trigger before or after the correct position
        self.assertNoTrigger(php_markup("class MyException implements IArrayObject,<|> IException {}"))
        self.assertNoTrigger(php_markup("class MyException implements IArrayObject, IE<|>xception {}"))

    def test_trigger_complete_magic_methods(self):
        # Triggers after $ and one character
        #
        #    Samples:
        #        function __<|>
        name = "php-complete-magic-methods"
        self.assertTriggerMatches(php_markup("function __<|>"),
                                  name=name, pos=15)
        # No trigger before or after the correct position
        self.assertNoTrigger(php_markup("function _<|>_"))
        self.assertNoTrigger(php_markup("function __a<|>"))

    def test_trigger_complete_namespaces(self):
        # Triggers after 'use ' or '\'
        #
        #    Samples:
        #        use <|>
        #        \<|>
        #        mynamespace\<|>
        name = "php-complete-namespaces"
        self.assertTriggerMatches(php_markup("use <|>"),
                                  name=name, pos=10)
        self.assertTriggerMatches(php_markup("\<|>"),
                                  name=name, pos=7)
        self.assertTriggerMatches(php_markup("foo\<|>"),
                                  name=name, pos=10)

        # assert no trigger in strings
        self.assertNoTrigger('<?php $s = "use <|>"; ?>')
        self.assertNoTrigger('<?php $s = "here\<|>"; ?>')

        # assert no trigger in comments
        self.assertNoTrigger('<?php /* use <|> */ ?>')
        self.assertNoTrigger('<?php /* \<|> */ ?>')
        self.assertNoTrigger('<?php # use <|>')

    def test_trigger_calltip_call_signature(self):
        # Triggers after open bracket:
        #        abc(<|>
        #
        #    Samples for global functions:
        #        bar();
        #    Samples for class:
        #        $a = new A();
        #        $a->foo();
        #        A::foo();
        #        self::myStaticMethod();
        #        parent::parentMethod();
        #        $mom->getChild()->getName();
        #
        name="php-calltip-call-signature"
        self.assertTriggerMatches(php_markup("$a = new A(<|>);"),
                                  name=name, form=TRG_FORM_CALLTIP)
        self.assertTriggerMatches(php_markup("$a->foo(<|>);"),
                                  name=name, form=TRG_FORM_CALLTIP)
        self.assertTriggerMatches(php_markup("A::foo(<|>);"),
                                  name=name, form=TRG_FORM_CALLTIP)
        self.assertTriggerMatches(php_markup("self::myStaticMethod(<|>);"),
                                  name=name, form=TRG_FORM_CALLTIP)
        self.assertTriggerMatches(php_markup("$mom->getChild(<|>)->getName();"),
                                  name=name, form=TRG_FORM_CALLTIP)
        self.assertTriggerMatches(php_markup("$mom->getChild()->getName(<|>);"),
                                  name=name, form=TRG_FORM_CALLTIP)
        self.assertTriggerMatches(php_markup("if (isset(<|>$this)) {"),
                                  name=name, form=TRG_FORM_CALLTIP)
        # Ensure we still get calltips when whitespace is between the
        # paren and the function
        self.assertTriggerMatches(php_markup("require (<|>$my_req);"),
                                  name=name, form=TRG_FORM_CALLTIP)
        self.assertTriggerMatches(php_markup("$mom->getChild (<|>)->getName();"),
                                  name=name, form=TRG_FORM_CALLTIP)
        # This calltip still triggers, though it will return None, see test
        # test_ignore_specific_calltip_keywords, for details
        self.assertTriggerMatches(php_markup('if (<|>isset($this)) {'),
                                  name=name, form=TRG_FORM_CALLTIP)
        # assert no trig for when definining a function??
        #self.assertNoTrigger('<?php final function bar(<|>) { ?>')
        # assert no trig in strings
        self.assertNoTrigger(php_markup('$s = "alert(<|>def);";'))
        self.assertNoTrigger(php_markup("$s = 'alert(<|>def);';r"))
        # assert no trig in comments
        self.assertNoTrigger('''<?php /*
                                 * myfunc.callthis(<|>arg1);
                                 */ ?>''')
        self.assertNoTrigger('<?php // myfunc.callthis(<|>arg1); ?>')
        self.assertNoTrigger('<?php # myfunc.callthis(<|>arg1); ?>')

    def test_php_calltip_call_signature_for_local_file(self):
        content, positions = unmark_text(dedent("""\
        <?php
        class MyClass {
            var $bar = 1;
            function foo($x, $y) {
                echo "this is the function foo";
            }
        }
        $a = new MyClass();
        $a->foo(<1>1, 2);
        MyClass::foo(<2>3, 4);
        ?>
        """))
        self.assertCalltipIs(markup_text(content, pos=positions[1]), "foo(x, y)")
        self.assertCalltipIs(markup_text(content, pos=positions[2]), "foo(x, y)")

    def test_citdl_expr_from_trg_simple(self):
        self.assertCITDLExprIs("foo-><|>", "foo")
        self.assertCITDLExprIs("Foo::<|>", "Foo")
        self.assertCITDLExprIs("foo->bar-><|>", "foo.bar")
        self.assertCITDLExprIs("Foo::bar-><|>", "Foo.bar")
        self.assertCITDLExprIs("foo(bar-><|>", "bar")
        self.assertCITDLExprIs("foo[bar-><|>", "bar")
        self.assertCITDLExprIs("foo{bar-><|>", "bar")
        self.assertCITDLExprIs("foo()-><|>", "foo()")
        self.assertCITDLExprIs("foo(a,b)-><|>", "foo()")
        self.assertCITDLExprIs("$a = foo-><|>", "foo")
        self.assertCITDLExprIs("$a = foo(bar-><|>, blam)", "bar")
        self.assertCITDLExprIs("blam()\nfoo-><|>", "foo")
        self.assertCITDLExprIs("blam()->\nfoo-><|>", "blam().foo")
        self.assertCITDLExprIs("blam()->\nfoo->bar-><|>", "blam().foo.bar")
        self.assertCITDLExprIs("if(!<|>is_array", "is_", trigger_name="functions")

    @tag("bug83192")
    def test_citdl_expr_from_namespace(self):
        # Examples:
        #    Foo\bar:<|>:                    Foo\bar
        #    Foo\bar::bam-<|>>               Foo\bar.bam
        #    Foo\bar(arg1, arg2)::bam-<|>>   Foo\bar().bam
        self.assertCITDLExprIs(r"foo\<|>", r"foo",
                               trigger_name="namespaces")
        self.assertCITDLExprIs(r"\foo\<|>", r"\foo",
                               trigger_name="namespaces")
        self.assertCITDLExprIs(r"foo\bar\<|>", r"foo\bar",
                               trigger_name="namespaces")
        self.assertCITDLExprIs(r"\foo\bar\<|>", r"\foo\bar",
                               trigger_name="namespaces")
        self.assertCITDLExprIs(r"Foo\bar::<|>", r"Foo\bar")
        self.assertCITDLExprIs(r"Foo\bar::bam-><|>", r"Foo\bar.bam")
        self.assertCITDLExprIs(r"Foo\bar()->bam-><|>", r"Foo\bar().bam")
        self.assertCITDLExprIs(r"Foo\bar\bam::<|>", r"Foo\bar\bam")

    @tag("bug79991")
    def test_citdl_expr_from_static_class_variables(self):
        self.assertCITDLExprIs("MyConfig::$db-><|>", "MyConfig.db")

    def test_preceding_trg_from_pos_general(self):
        calltip_trigger = "php-calltip-call-signature"
        completion_trigger = "php-complete-object-members"

        self.assertNoPrecedingTrigger(php_markup("$foo->bar <|><$>"))
        self.assertNoPrecedingTrigger(php_markup("$foo->bar<$>(<|>"))

        self.assertPrecedingTriggerMatches(php_markup("$foo->bar(<$> <|>"),
            name=calltip_trigger, pos=16)
        self.assertPrecedingTriggerMatches(php_markup("$foo->bar(<$><|>"),
            name=calltip_trigger, pos=16)

        self.assertPrecedingTriggerMatches(
            php_markup("$os->path->join(os->path->dirname('foo<$><|>"),
            name=calltip_trigger, pos=40)
        self.assertPrecedingTriggerMatches(
            php_markup("$os->path->join(os->path->dirname<$>('foo<|>"),
            name=calltip_trigger, pos=22)
        self.assertNoPrecedingTrigger(
            php_markup("$os->path->join<$>(os->path->dirname('foo<|>"))

        self.assertPrecedingTriggerMatches(
            php_markup("$os->path->join<|><$>"),
            name=completion_trigger, pos=17)
        self.assertNoPrecedingTrigger(php_markup("os->path<$>->join<|>"))

        #self.assertPrecedingTriggerMatches(
        #    dedent(php_markup("""\
        #        $os->path->join(  # try to (screw ' {] ) this up
        #            $os->path->dirname('foo<$><|>
        #    """)),
        #    name=calltip_trigger, pos=66)
        #self.assertPrecedingTriggerMatches(
        #    dedent(php_markup("""\
        #        $os->path->join(  # try to (screw ' {] ) this up
        #            $os->path->dirname<$>('foo<|>
        #    """)),
        #    name=calltip_trigger, pos=13)

        # Test in a comment.
        self.assertNoPrecedingTrigger(
            php_markup(dedent("""\
                #
                # $os->path->join(
                #    $os->path->dirname<$>('foo<|>
                #
            """)))

        # Test in a doc string.
        self.assertNoPrecedingTrigger(
            php_markup(dedent('''
                function foo()
                {
                    $x = "$os->path->join($os->path->dirname<$>('foo<|>";
                }
            ''')))

        # Test out-of-range calltip
        self.assertPrecedingTriggerMatches(
            php_markup("foo(bar('hi'), <|><$>"),
            name=calltip_trigger, pos=10)

    def test_preceding_trg_from_pos_specific(self):
        # Some extended examples, specific to PHP triggers

        # Test explicit "new " trigger
        self.assertPrecedingTriggerMatches(php_markup("$e = new Exce<$><|>('Error', 1);"),
            name="php-complete-classes", pos=15)
        self.assertPrecedingTriggerMatches(php_markup("$e = new     <$><|>;"),
            name="php-complete-classes", pos=19)
        # Test explicit variables trigger
        self.assertPrecedingTriggerMatches(php_markup("$message = 'message'; $x = $mess<$><|>;"),
            name="php-complete-variables", pos=34)
        # Test explicit functions trigger
        self.assertPrecedingTriggerMatches(php_markup("get_e<$><|>;"),
            name="php-complete-functions", pos=6)
        # Test explicit functions trigger, ensuring does not go beyond where
        # we want it to
        self.assertNoPrecedingTrigger(php_markup("get_env<$>(get_e<|>;"))
        # Test explicit classes trigger
        self.assertPrecedingTriggerMatches(php_markup("class A extends Excep<$><|>;"),
            name="php-complete-classes", pos=22)
        self.assertPrecedingTriggerMatches(php_markup("class A extends    <$><|>;"),
            name="php-complete-classes", pos=25)
        self.assertPrecedingTriggerMatches(php_markup("class A extends Exception,   <$><|>;"),
            name="php-complete-classes", pos=35)
        # Test explicit interfaces trigger
        self.assertPrecedingTriggerMatches(php_markup("class A implements IExcep<$><|>;"),
            name="php-complete-interfaces", pos=25)
        self.assertPrecedingTriggerMatches(php_markup("class A implements    <$><|>;"),
            name="php-complete-interfaces", pos=28)


    def test_curr_calltip_arg_range(self):
        # Assert can deal with calltip with no args.
        self.assertCurrCalltipArgRange(php_markup("foo(<+><|>"), "foo()", (0,0))
        self.assertCurrCalltipArgRange(php_markup("foo(<+>blah<|>"), "foo()", (0,0))
        self.assertCurrCalltipArgRange(php_markup("foo(<+>one, two<|>"), "foo()", (0,0))
        self.assertCurrCalltipArgRange(php_markup("foo(<+>blah)<|>"), "foo()", (-1,-1))

        # Should still be able to terminate properly if no signature to
        # work with.
        self.assertCurrCalltipArgRange(php_markup("foo(<+><|>"), "not a signature", (0,0))
        self.assertCurrCalltipArgRange(php_markup("foo(<+>blah<|>"), "not a signature", (0,0))
        self.assertCurrCalltipArgRange(php_markup("foo(<+>blah)<|>"), "not a signature", (-1,-1))

        self.assertCurrCalltipArgRange(php_markup("foo(<+><|>"), "foo(a, b, c)", (4,5))
        self.assertCurrCalltipArgRange(php_markup("foo(<+>art<|>"), "foo(a, b, c)", (4,5))
        self.assertCurrCalltipArgRange(php_markup("foo(<+>art,<|>"), "foo(a, b, c)", (7,8))
        self.assertCurrCalltipArgRange(php_markup("foo(<+>art,bla,<|>"), "foo(a, b, c)", (10,11))

        self.assertCurrCalltipArgRange(php_markup("$os->path->join(<+>'hi', 'there<|>"),
                                       "join(a, *p)\nJoin two or...",
                                       (8, 10))
        self.assertCurrCalltipArgRange(php_markup("main(<+>$sys->argv, 'myopts', 4<|>);"),
                                       "main(args, opts, indent)",
                                       (17, 23))
        self.assertCurrCalltipArgRange(php_markup("Foo::foo(<+>(hi, there), asdf<|>)"),
                                       "foo(a,b,c)",
                                       (6, 7))

        self.assertCurrCalltipArgRange(php_markup("foo(<+>)<|>"), "foo(a, b, c)",
                                       (-1, -1))
        self.assertCurrCalltipArgRange(php_markup("foo(<+>a=(hi, 'there()'))<|>"),
                                       "foo(a, b, c)", (-1, -1))
        self.assertCurrCalltipArgRange(php_markup("foo(<+>a=(hi, 'there()'), <|>)"),
                                       "foo(a, b, c)", (7, 8))

        for content in [php_markup("foo(<+>a=(hi, 'there()'), <|>)"),
                        php_markup("foo(<+>{'hi()', bob[1]}, blah<|>")]:
            self.assertCurrCalltipArgRange(content, "foo(a, b, c)", (7, 8))

        #XXX Add test cases for keyword and ellipsis args when have added
        #    support for that in BasicCalltipBufferMixin.

    def test_doctags(self):
        # Triggers after @ in a comment block
        #        /** @param
        cpln_trigger_name = "php-complete-phpdoc-tags"
        calltip_trigger_name = "php-calltip-phpdoc-tags"
        self.assertTriggerMatches(php_markup("/** @<|>param"),
                                  name=cpln_trigger_name,
                                  pos=5+php_markup_offset)
        self.assertTriggerMatches(php_markup("/** @param <|>"),
                                  name=calltip_trigger_name,
                                  pos=9+php_markup_offset)
        self.assertPrecedingTriggerMatches(php_markup("/** @param foo bar <$><|>"),
                                           name=calltip_trigger_name,
                                           pos=9+php_markup_offset)
        # Don't trigger in normal code or inside strings
        self.assertNoTrigger(php_markup("@<|>something"))
        self.assertNoTrigger(php_markup("$s = '@<|>something';"))

    def _unmark_text(self, text):
        """Only unmark the number"""
        result = {}
        unmarked_text, positions = unmark_text(text)
        remarked_text = markup_text(unmarked_text,
                                    start_pos=positions["start_pos"],
                                    pos=positions["pos"])
        return remarked_text, positions["trg_pos"]

    @tag("bug55737", "knownfailure")
    def test_bug55737_preceeding_trigger_inside_function_for_if(self):
        #self.assertNoPrecedingTrigger(php_markup("$foo->bar<$>(<|>"))
        content, trg_pos = self._unmark_text(php_markup("if(<+>array_<$><|>"))
        self.assertPrecedingTriggerMatches(markup_text(content),
                                  name="php-complete-functions", pos=trg_pos)

    @tag("bug54667")
    def test_trigger_heredoc_strings(self):
        # assert no trig in heredoc
        self.assertNoTrigger(php_markup("""$str = <<<EOD
                                Example of string
                                $myfunc-><|>callthis(arg1);
                                using heredoc syntax.
                                EOD;"""))
        self.assertNoTrigger(php_markup("""$str = <<<EOD
                                Example of string
                                myfunc.callthis(<|>arg1);
                                using heredoc syntax.
                                EOD;"""))

    @tag("bug70470")
    def test_function_calltip_after_completion_event(self):
        content, positions = unmark_text(dedent("""\
        <?php
        function func_foo($x, $y) { }
        $myarg = 1;
        # Trigger on both "," and ", "
        func_foo($myarg,<1>);
        func_foo($myarg, <1>);
        ?>
        """))
        self.assertCalltipIs(markup_text(content, pos=positions[1]), "func_foo(x, y)")

    @tag("bug67367")
    def test_complete_array_members(self):
        # Triggers after foo['
        #
        #    Samples:
        #        $_SERVER['    =>   [ 'SERVER_NAME', 'SERVER_ADDR', ...]
        name = "php-complete-array-members"
        self.assertTriggerMatches(php_markup("$_SERVER['<|>SERVER_NAME']"),
                                  name=name, pos=16)
        self.assertTriggerMatches(php_markup('$_SERVER["<|>SERVER_NAME"]'),
                                  name=name, pos=16)
        # Try with some additional spacing...
        self.assertTriggerMatches(php_markup("$_SERVER[  \n'<|>SERVER_NAME']"),
                                  name=name, pos=19)
        # No trigger before or after the correct position
        self.assertNoTrigger(php_markup('$_SERVER[<|>"SERVER_NAME"]'))
        # No trigger on a string.
        self.assertNoTrigger(php_markup('a"<|>SERVER_NAME"]'))

    @tag("bug78099")
    def test_variable_trigger_with_class_operator(self):
        # Should not trigger variables after "::"
        # http://bugs.activestate.com/show_bug.cgi?id=78099
        self.assertNoTrigger(php_markup("Class::$s<|>"))

    @tag("bug82165")
    def test_explicit_variable_completion(self):
        # Should trigger explicit variable completions after "$"
        # http://bugs.activestate.com/show_bug.cgi?id=82165
        self.assertTriggerMatches(php_markup("$<|>"), implicit=False,
                                  name="php-complete-variables", pos=7)


class CplnTestCase(CodeIntelTestCase):
    lang = "PHP"
    test_dir = join(os.getcwd(), "tmp")
    _ci_env_prefs_ = {
        "defaultHTMLDecl": "-//W3C//DTD HTML 4.01//EN",
    }

    def setUp(self):
        super(CplnTestCase, self).setUp()
        init_xml_catalogs()

    @tag("bug75490")
    def test_html_markup_completion(self):
        self.assertTriggerMatches("<<|>",
            name="html-complete-tags-and-namespaces")
        self.assertCompletionsInclude(HTML_DOCTYPE+"<<|>",
            [("element", "html")])
        self.assertCompletionsInclude("<<|>",
            [("element", "html")])

    def test_class_inheritance(self):
        content, positions = unmark_text(dedent(php_markup("""\
            class FooBase1 {
                function func_in_foobase1($p) { }
            }
            class FooBase2 extends FooBase1 { }
            class FooBase3 extends FooBase2 { }
            class FooBase4 extends FooBase3 {
                function func_in_foobase4() {
                    parent::<1>xyz;
                    $this-><2>xyz;
                }
            }
            class FooBase5 extends FooBase4 { }
            class FooBase6 extends FooBase5 { }
            class FooBase7 extends FooBase6 { }
            class FooBase8 extends FooBase7 { }
            class FooBase9 extends FooBase8 { }
            class FooBase10 extends FooBase9 { }
            class Foo extends FooBase10 {
                function func_in_foo($f) {
                    parent::<3>xyz;
                    $this-><4>xyz;
                }
            }
            class Bar extends Foo {
                function func_in_bar($b) { }
            }
            
            class Blah extends Bar {
                function func_in_blah($bl) {
                    $this-><5>func_in_bar(<6>);
                    $this->func_in_foo(<7>);
                    $this->func_in_foobase4(<8>);
                    $this->func_in_foobase1(<9>);
                    parent::<10>func_in_foobase1(<11>);
                }
            }
            
            $blah = new Blah();
            $blah-><12>func_in_foobase4(<13>);
       """)))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
                [("function", "func_in_foobase1")])
        self.assertCompletionsInclude(markup_text(content, pos=positions[2]),
                [("function", "func_in_foobase1"),
                 ("function", "func_in_foobase4")])
        self.assertCompletionsInclude(markup_text(content, pos=positions[3]),
                [("function", "func_in_foobase1"),
                 ("function", "func_in_foobase4")])
        self.assertCompletionsInclude(markup_text(content, pos=positions[4]),
                [("function", "func_in_foobase1"),
                 ("function", "func_in_foobase4"),
                 ("function", "func_in_foo")])
        self.assertCompletionsInclude(markup_text(content, pos=positions[5]),
                [("function", "func_in_foobase1"),
                 ("function", "func_in_foobase4"),
                 ("function", "func_in_foo"),
                 ("function", "func_in_bar"),
                 ("function", "func_in_blah")])
        self.assertCalltipIs(markup_text(content, pos=positions[6]),
                "func_in_bar(b)")
        self.assertCalltipIs(markup_text(content, pos=positions[7]),
                "func_in_foo(f)")
        self.assertCalltipIs(markup_text(content, pos=positions[8]),
                "func_in_foobase4()")
        self.assertCalltipIs(markup_text(content, pos=positions[9]),
                "func_in_foobase1(p)")
        self.assertCompletionsInclude(markup_text(content, pos=positions[10]),
                [("function", "func_in_foobase1"),
                 ("function", "func_in_foobase4"),
                 ("function", "func_in_foo"),
                 ("function", "func_in_bar")])
        self.assertCalltipIs(markup_text(content, pos=positions[11]),
                "func_in_foobase1(p)")
        self.assertCompletionsInclude(markup_text(content, pos=positions[12]),
                [("function", "func_in_foobase1"),
                 ("function", "func_in_foobase4"),
                 ("function", "func_in_foo"),
                 ("function", "func_in_bar"),
                 ("function", "func_in_blah")])
        self.assertCalltipIs(markup_text(content, pos=positions[13]),
                "func_in_foobase4()")

    def test_php_complete_object_members_for_local_file(self):
        content, positions = unmark_text(dedent("""\
        <?php
        class MyClass {
            var $bar = 1;
            function foo() {
                echo "this is the function foo";
            }
        }
        $a = new MyClass();
        $a-><1>foo();
        $b = $a-><2>bar;
        MyClass::<3>foo();
        ?>
        """))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("function", "foo"), ("variable", "bar")])
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[2]),
            [("function", "foo"), ("variable", "bar")])
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[3]),
            [("function", "foo")])

    def test_complete_classes_for_local_file_using_new(self):
        name = "php-complete-classes"
        markedup_content = dedent(php_markup("""\
            class MyClass {}
            $m = new <|>MyClass();
       """))
        self.assertCompletionsInclude(markedup_content,
            [("class", "MyClass")])

    def test_complete_interfaces_for_local_file(self):
        name = "php-complete-interfaces"
        markedup_content = dedent(php_markup("""\
            interface IMyClass {}
            class MyClass implements <|>IMyClass {}
       """))
        self.assertCompletionsInclude(markedup_content,
            [("interface", "IMyClass")])

    def test_complete_class_special_members(self):
        content, positions = unmark_text(php_markup(dedent("""\
            class MyClass {
                private $x = 1;
                function foo() {
                    $this-><1>x *= 10;
                    self::<2>x = 1;
                }
            }
            class MySecondClass extends MyClass {
                private $y = 2;
                function bar() {
                    $this-><3>y = 20;
                    self::<4>foo();
                    parent::<5>foo();
                }
            }
       """)))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("variable", "x"), ("function", "foo")])
        self.assertCompletionsInclude(markup_text(content, pos=positions[2]),
            [("function", "foo")])
        self.assertCompletionsInclude(markup_text(content, pos=positions[3]),
            [("variable", "y"), ("function", "foo"), ("function", "bar")])
        self.assertCompletionsInclude(markup_text(content, pos=positions[4]),
            [("function", "foo"), ("function", "bar")])
        self.assertCompletionsInclude(markup_text(content, pos=positions[5]),
            [("function", "foo")])

    def test_calltip_call_signature_for_builtins(self):
        markedup_content = php_markup(dedent("""\
            require(<|>"myfile.php");
       """))
        calltip = "require(file_path)\n" \
                  "Includes and evaluates the specified file, produces a\n" \
                  "Fatal Error on error."
        self.assertCalltipIs(markedup_content, calltip)

    @tag("php5")
    def test_complete_object_members_for_builtins(self):
        markedup_content = php_markup(dedent("""\
            $e = new Exception("New exception");
            $e-><|>     # should have getMessage in completion list
       """))
        self.assertCompletionsInclude(markedup_content,
            [("function", "getMessage"), ("function", "getLine")])

    def test_complete_functions_for_builtins(self):
        markedup_content = php_markup(dedent("""\
            $i = apa<|>che_getenv("QUERY_STRING");
       """))
        for i in range(20):
            self.assertCompletionsInclude(markedup_content,
                [("function", "apache_getenv"), ("function", "apache_setenv")])

    def test_complete_variables_for_builtins(self):
        markedup_content = php_markup(dedent("""\
            $G<|>["myvarname"];
       """))
        self.assertCompletionsInclude(markedup_content,
            [("variable", "GLOBALS"), ])

    @tag("php5")
    def test_complete_classes_for_builtins_using_new(self):
        markedup_content = php_markup(dedent("""\
            $e = new <|>Exception("Error", 1);
       """))
        self.assertCompletionsInclude(markedup_content,
            [("class", "ArrayObject"), ("class", "Exception")])

    #def test_ptfp_complete_classes_for_builtins_using_new(self):
    #    markedup_content = php_markup(dedent("""\
    #        $e = new Exce<$><|>("Error", 1);
    #   """))
    #    self.assertCompletionsInclude(markedup_content,
    #        [("class", "Exception")])

    @tag("php5")
    def test_php5_complete_object_members_for_builtins(self):
        markedup_content = php_markup(dedent("""\
            $e = new Exception("New exception");
            $e-><|>     # should have getMessage in completion list
       """))
        self.assertCompletionsInclude(markedup_content,
            [("function", "getMessage"), ("function", "getLine")])

    @tag("php5")
    def test_php5_calltip_call_signature_for_classes(self):
        content, positions = unmark_text(php_markup("""\
            $e = new Exception(<1>'error name', 0);
       """))
        expected_calltip = """__construct(message=NULL, code=0)
Construct an exception

@param $message Some text describing the exception
@param $code    Some code describing the exception"""
        self.assertCalltipIs(markup_text(content, pos=positions[1]),
                             expected_calltip)

    ##
    # Import handling

    def test_php_local_import_1(self):
        test_dir = join(self.test_dir, "test_php_local_import_1")
        test_content, test_positions = unmark_text(php_markup(dedent("""\
            require ("simple.php");
            $x = Sim<1>pleFunction(1, 2);
            $obj = new <2>SimpleClass();
            $obj-><3>foo();
        """)))

        manifest = [
            ("simple.php", php_markup(dedent("""
                class SimpleClass {
                    var $simple_var;
                    function foo() {
                    }
                }
                function SimpleFunction($arg1, $arg2) {
                    return "a string";
                }
             """))),
            ("test.php", test_content),
        ]
        for file, content in manifest:
            path = join(test_dir, file)
            writefile(path, content)

        buf = self.mgr.buf_from_path(join(test_dir, "test.php"), lang=self.lang)
        self.assertCompletionsInclude2(buf, test_positions[1],
            [("function", "SimpleFunction")])
        self.assertCompletionsInclude2(buf, test_positions[2],
            [("class", "SimpleClass")])
        self.assertCompletionsInclude2(buf, test_positions[3],
            [("function", "foo"), ("variable", "simple_var")])


    def test_php_local_import_2(self):
        test_dir = join(self.test_dir, "test_php_local_import_2")
        test_content, test_positions = unmark_text(php_markup(dedent("""\
            require ("simple1/simple1.php");
            require ("simple2/simple2.php");
            $x = Sim<1>pleFunction1(1, 2);
            $obj = new <2>SimpleClass2();
            $obj-><3>foo();
        """)))

        manifest = [
            ("simple1/simple1.php", php_markup(dedent("""
                class SimpleClass1 {
                    var $simple_var1;
                    function simple_func1() {
                    }
                }
                function SimpleFunction1($arg1, $arg2) {
                    return "a string";
                }
             """))),
            ("simple2/simple2.php", php_markup(dedent("""
                class SimpleClass2 {
                    var $simple_var2;
                    function simple_func2() {
                    }
                }
                function SimpleFunction2($arg1, $arg2) {
                    return "a string";
                }
             """))),
            ("test.php", test_content),
        ]
        for file, content in manifest:
            path = join(test_dir, file)
            writefile(path, content)

        buf = self.mgr.buf_from_path(join(test_dir, "test.php"), lang=self.lang)
        self.assertCompletionsInclude2(buf, test_positions[1],
            [("function", "SimpleFunction1"),
             ("function", "SimpleFunction2")])
        self.assertCompletionsInclude2(buf, test_positions[2],
            [("class", "SimpleClass1"),
             ("class", "SimpleClass2")])
        self.assertCompletionsInclude2(buf, test_positions[3],
            [("function", "simple_func2"), ("variable", "simple_var2")])

    def test_doctags(self):
        # Triggers after @ in a comment block
        #        /** @param
        content, positions = unmark_text(php_markup(dedent("""\
            /** @<1>param <2>citdl $name Some comment
        """)))
        from codeintel2.phpdoc import phpdoc_tags
        cplns = [ ("variable", x) for x in sorted(phpdoc_tags.keys()) ]
        self.assertCompletionsAre(markup_text(content, pos=positions[1]), cplns)
        self.assertCalltipIs(markup_text(content, pos=positions[2]),
                             phpdoc_tags["param"])

    def test_variable_completions_in_doctags(self):
        content, positions = unmark_text(php_markup(dedent("""\
            
            /**
             * Testing variable. $n<1>xxx
             */
            $named_test_var1 = 1;
            /**
             * My Testing Function.
             * @param string $n<2>ame Name of user.
             * @param string $f<3>xxx Fields.
             */
            function MyTestFunc($name, $fields) {}
            /**
             * Testing variable. $n<4>xxx
             */
            $named_test_var2 = 2;
        """)))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("variable", "named_test_var1"),
             ("variable", "named_test_var2")])
        self.assertCompletionsDoNotInclude(markup_text(content, pos=positions[1]),
            [("variable", "name"),
             ("variable", "name"),
             ("variable", "fields")])

        self.assertCompletionsInclude(markup_text(content, pos=positions[2]),
            [("variable", "name"),])
        self.assertCompletionsDoNotInclude(markup_text(content, pos=positions[2]),
            [("variable", "named_test_var1"),
             ("variable", "named_test_var2")])

        self.assertCompletionsInclude(markup_text(content, pos=positions[3]),
            [("variable", "fields"),])
        self.assertCompletionsDoNotInclude(markup_text(content, pos=positions[3]),
            [("variable", "named_test_var1"),
             ("variable", "named_test_var2")])

        self.assertCompletionsInclude(markup_text(content, pos=positions[4]),
            [("variable", "named_test_var1"),
             ("variable", "named_test_var2")])
        self.assertCompletionsDoNotInclude(markup_text(content, pos=positions[4]),
            [("variable", "name"),
             ("variable", "fields")])

    ##
    # Specific bug tests

    @tag("bug55347")
    def test_bug55347_trigger_inside_functions(self):
        # assert trigger
        self.assertTriggerMatches(php_markup("$x = explode(get<|>);"),
                                  name="php-complete-functions", pos=19)
        self.assertTriggerMatches(php_markup("$x = explode('123', get<|>);"),
                                  name="php-complete-functions", pos=26)
        self.assertTriggerMatches(php_markup("$x = explode($H<|>);"),
                                  name="php-complete-variables", pos=20)

    @tag("bug55717")
    def test_bug55717_preceding_trg_from_pos_with_array(self):
        content, positions = unmark_text(dedent("""\
        <?php
        function getField($arg1) {
            return "1234";
        }
        $out = array(<1>'name'=>getField(<2>"1"));
        ?>
        """))
        self.assertCalltipIs(markup_text(content, pos=positions[1]), "array(<list>)\nCreate a PHP array.")
        self.assertCalltipIs(markup_text(content, pos=positions[2]), "getField(arg1)")

    @tag("bug55897")
    def test_bug55897_preceding_trg_from_pos_with_array(self):
        markedup_content = php_markup(dedent("""
            function foo_bar() { }
            function bar() {
                # Should have access to all global functions
                foo<|>_bar();
            }
       """))
        self.assertCompletionsInclude(markedup_content, [("function", "foo_bar")])

        markedup_content = php_markup(dedent("""
            class fooclass { }
            function bar() {
                # Should have access to all global classes
                $foo = new <|>fooclass();
            }
       """))
        self.assertCompletionsInclude(markedup_content, [("class", "fooclass")])

        markedup_content = php_markup(dedent("""
            class fooclass { }
            class barclass {
                # Should have access to all global classes
                $foo = new <|>fooclass();
            }
       """))
        self.assertCompletionsInclude(markedup_content, [("class", "fooclass"),
                                                         ("class", "barclass")])

    @tag("bug55468")
    def test_bug55468_function_returns(self):
        content, positions = unmark_text(php_markup(dedent("""
            function testreturnsfromcile() {
                $node = new DOMNode();
                return $node;
            }
            $n = testreturnsfromcile();
            $n-><1>appendChild();

            class MyClass {
                function foo($x, $y) {
                    $e2 = new Exception('', 12);
                    return $e2;
                }
                function fooUsingThis($x, $y) {
                    $e2 = $this->foo();
                    return $e2;
                }
            }

            $m = new MyClass();
            $e = $m->foo(1, 2);
            $e-><2>getLine();

            $e2 = $m->fooUsingThis(1, 2);
            $e2-><3>getLine();
        """)))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("function", "hasAttributes")])
        self.assertCompletionsInclude(markup_text(content, pos=positions[2]),
            [("function", "getMessage"), ("function", "getLine")])
        self.assertCompletionsInclude(markup_text(content, pos=positions[3]),
            [("function", "getMessage"), ("function", "getLine")])

    @tag("bug55468")
    def test_bug55468_function_returns_inside_class(self):
        content, positions = unmark_text(php_markup(dedent("""
            class mine {
                function mine($arg) {
                    $x = new PDO();
                    return $x;
                }
                function yours($arg) {
                    $xx = $this->mine(1);
                    // It would be cool to get PDO member completion on $xx
                    $xx-><1>completeme();
                }
            }
        """)))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("function", "beginTransaction"), ("function", "commit")])

    @tag("bug66638")
    def test_ignore_heredocs(self):
        # assert no exceptions raised due to heredoc, just go with
        # what is available
        content, positions = unmark_text(php_markup("""
            function outside_one()
            {
                return <<<EOD

function inside_one() {
    return 0;
}
function inside_two() {
    return 0;
}
EOD;
            }
            
            $x = out<1>side_one();
            $y = ins<2>ide_one();
"""))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
                [("function", "outside_one"), ])
        self.assertCompletionsDoNotInclude(markup_text(content, pos=positions[2]),
                [("function", "inside_one"), ("function", "inside_two"), ])

    @tag("bug57647")
    def test_function_trigger_with_preceding_exclamation(self):
        content, positions = unmark_text(php_markup(dedent("""\
        if(!is_<1>array($foo))
        """)))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
                [("function", "is_array"), ("function", "is_a")])


    @tag("bug59867")
    def test_calltip_after_string_append(self):
        content, positions = unmark_text(php_markup(dedent("""\
            function testfunc() { }
            $constants = get_defined_constants();
    
            foreach($constants as $con=>$val) {
                echo $con." is of type ". testfunc(<1>);
            }
        """)))
        self.assertCalltipIs(markup_text(content, pos=positions[1]), "testfunc()")


    @tag("bug57637")
    def test_completions_on_this(self):
        content, positions = unmark_text(php_markup(dedent("""
            class mine {
                public $field1;
                public $err;
                public $ch;
                function call_me($arg) {
                    $this-><1>err = array(curl_errno($this-><2>ch),curl_error($this-><3>ch));
                }
            }
        """)))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("variable", "ch"), ("variable", "err"), ("function", "call_me")])
        self.assertCompletionsInclude(markup_text(content, pos=positions[2]),
            [("variable", "ch"), ("variable", "err"), ("function", "call_me")])
        self.assertCompletionsInclude(markup_text(content, pos=positions[3]),
            [("variable", "ch"), ("variable", "err"), ("function", "call_me")])


    # Inheritance test content, will be used in a few test so defining it here
    import1_content = php_markup(dedent("""\
        class one {
            public $x;
            function __construct() {
                $x = 1;
            }
            function mine($x,$y) {
                return func_get_args();
            } 
        }
        function _this_is_from_import_1($foo) {
            return 1;
        }
        $var_in_one = "1";
    """))

    import2_content = php_markup(dedent("""\
        class two {
            public $y;
            function __construct() {
                $y = 1;
            }
            function yours($x,$y) {
                return func_get_args();
            } 
        }
        function _this_is_from_import_2($foo) {
            return 1;
        }
        $var_in_two = "2";
    """))

    @tag("bug57887")
    def test_completion_with_multiple_imports(self):
        test_dir = join(self.test_dir, "test_bug57887_completion_with_multiple_imports")
        test_content, test_positions = unmark_text(php_markup(dedent("""\
            require_once("import_1.php");
            require_once("import_2.php");

            class ext_one extends <1>one {
                function __construct($foo) {
                    $this-><2>xxx;
                    self::<3>mine();
                    parent::<4>
                }
            }

            class ext_two extends <5>two {
                function __construct($foo) {
                    $this-><6>xxx;
                    self::<7>yours();
                    parent::<8>
                }
            }
        """)))
        manifest = [
            ("test.php", test_content),
            ("import_1.php", self.import1_content),
            ("import_2.php", self.import2_content),
        ]
        for file, content in manifest:
            path = join(test_dir, file)
            writefile(path, content)

        buf = self.mgr.buf_from_path(join(test_dir, "test.php"), lang=self.lang)
        self.assertCompletionsInclude2(buf, test_positions[1],
            [("class", "one"), ("class", "two")])
        self.assertCompletionsInclude2(buf, test_positions[2],
            [("variable", "x"), ("function", "mine"), ("function", "__construct")])
        self.assertCompletionsInclude2(buf, test_positions[3],
            [("function", "mine"), ("function", "__construct")])
        self.assertCompletionsInclude2(buf, test_positions[4],
            [("function", "mine"), ("function", "__construct")])
        self.assertCompletionsInclude2(buf, test_positions[5],
            [("class", "one"), ("class", "two")])
        self.assertCompletionsInclude2(buf, test_positions[6],
            [("variable", "y"), ("function", "yours"), ("function", "__construct")])
        self.assertCompletionsInclude2(buf, test_positions[7],
            [("function", "yours"), ("function", "__construct")])
        self.assertCompletionsInclude2(buf, test_positions[8],
            [("function", "yours"), ("function", "__construct")])

    def test_completion_with_import_inside_import(self):
        test_dir = join(self.test_dir, "test_completion_with_import_inside_import")
        test_content, test_positions = unmark_text(php_markup(dedent("""\
            require_once("import_3.php");

            class local_one extends <1>ext_three {
                function __construct($foo) {
                    $this-><2>xxx;
                    self::<3>mine();
                    parent::<4>
                }
            }

            class local_two extends <5>ext_four {
                var $local_y;
                function __construct($foo) {
                    $this-><6>xxx;
                    self::<7>yours();
                    parent::<8>
                }
            }

            $obj_one = new <9>one();
            $obj_one-><10>xyz;

            $obj_two = new local_two();
            $obj_two-><11>xyz;
        """)))
        manifest = [
            ("test.php", test_content),
            ("import_1.php", self.import1_content),
            ("import_2.php", self.import2_content),
            ("import_3.php", php_markup(dedent("""\
                require_once("import_1.php");
                require_once("import_2.php");

                class ext_three extends one {
                    function func_in_three() {
                    }
                }
    
                class ext_four extends two {
                    function func_in_four() {
                    }
                }
            """))),
        ]
        for file, content in manifest:
            path = join(test_dir, file)
            writefile(path, content)

        buf = self.mgr.buf_from_path(join(test_dir, "test.php"), lang=self.lang)
        self.assertCompletionsInclude2(buf, test_positions[1],
            [("class", "one"), ("class", "two"),
             ("class", "ext_three"), ("class", "ext_four"), ])
        self.assertCompletionsInclude2(buf, test_positions[2],
            [("variable", "x"), ("function", "mine"),
             ("function", "__construct"), ("function", "func_in_three")])
        self.assertCompletionsInclude2(buf, test_positions[3],
            [("function", "mine"),
             ("function", "__construct"), ("function", "func_in_three")])
        self.assertCompletionsInclude2(buf, test_positions[4],
            [("function", "mine"),
             ("function", "__construct"), ("function", "func_in_three")])
        self.assertCompletionsInclude2(buf, test_positions[5],
            [("class", "one"), ("class", "two"),
             ("class", "ext_three"), ("class", "ext_four"), ])
        self.assertCompletionsInclude2(buf, test_positions[6],
            [("variable", "y"), ("variable", "local_y"), ("function", "yours"),
             ("function", "__construct"), ("function", "func_in_four")])
        self.assertCompletionsInclude2(buf, test_positions[7],
            [("function", "yours"),
             ("function", "__construct"), ("function", "func_in_four")])
        self.assertCompletionsInclude2(buf, test_positions[8],
            [("function", "yours"),
             ("function", "__construct"), ("function", "func_in_four")])
        self.assertCompletionsInclude2(buf, test_positions[9],
            [("class", "one"), ("class", "two"),
             ("class", "ext_three"), ("class", "ext_four"),
             ("class", "local_one"), ("class", "local_two"), ])
        self.assertCompletionsInclude2(buf, test_positions[10],
            [("variable", "x"), ("function", "mine"),
             ("function", "__construct"), ])
        self.assertCompletionsInclude2(buf, test_positions[11],
            [("variable", "y"), ("variable", "local_y"), ("function", "yours"),
             ("function", "__construct"), ("function", "func_in_four")])

    def test_recursive_importing(self):
        test_dir = join(self.test_dir, "test_recursive_importing")
        test_content, test_positions = unmark_text(php_markup(dedent("""\
            require_once("foo.php");
            class local extends <1>foo {
                var $x_local;
                function func_in_local() { }
            }
            $obj = new <2>local();
            $obj-><3>xyz;
        """)))
        manifest = [
            ("test.php", test_content),
            ("foo.php", php_markup(dedent("""\
                require_once("bar.php");
                class foo extends bar {
                    var $x_foo;
                    function func_in_foo() { }
                }
            """))),
            ("bar.php", php_markup(dedent("""\
                require_once("baz.php");
                class bar extends baz {
                    var $x_bar;
                    function func_in_bar() { }
                }
            """))),
            ("baz.php", php_markup(dedent("""\
                require_once("foo.php");
                # Recurse back to foo
                class baz extends foo {
                    var $x_baz;
                    function func_in_baz() { }
                }
            """))),
        ]
        for file, content in manifest:
            path = join(test_dir, file)
            writefile(path, content)

        buf = self.mgr.buf_from_path(join(test_dir, "test.php"), lang=self.lang)
        self.assertCompletionsInclude2(buf, test_positions[1],
            [("class", "foo"), ("class", "bar"), ("class", "baz"), ])
        self.assertCompletionsInclude2(buf, test_positions[2],
            [("class", "foo"), ("class", "bar"), ("class", "baz"), ("class", "local"), ])
        self.assertCompletionsInclude2(buf, test_positions[3],
            [("variable", "x_local"), ("variable", "x_foo"),
             ("variable", "x_bar"),   ("variable", "x_baz"),
             ("function", "func_in_local"), ("function", "func_in_foo"),
             ("function", "func_in_bar"),   ("function", "func_in_baz"),
             ])

    @tag("bug59907")
    def test_func_list_unknown_variable(self):
        # Returning "php-complete-functions" when it should not
        self.assertNoTrigger(php_markup("$cix_gen = new php<|>"))
        self.assertNoTrigger(php_markup("class abc<|>"))
        self.assertNoTrigger(php_markup("function xyz<|>"))
        self.assertNoTrigger(php_markup("if(file_exists($file->fil<|>e"))

    @tag("bug63158")
    def test_different_php_tags(self):
        content, positions = unmark_text(dedent("""\
        <?
        class MyClass {
            var $bar = 1;
            function foo() {
                echo "this is the function foo";
            }
        }
        $a = new MyClass();
        $a-><1>foo();
        $b = $a-><2>bar;
        MyClass::<3>foo();
        ?>
        """))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("function", "foo"), ("variable", "bar")])
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[2]),
            [("function", "foo"), ("variable", "bar")])
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[3]),
            [("function", "foo")])

        # Test "<?=" tags
        content, positions = unmark_text(dedent("""\
        <?= exp<1>lode(); ?>
        """))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("function", "exp"), ("function", "explode")])

        # Test "<%" tags
        content, positions = unmark_text(dedent("""\
        <% exp<1>lode(); %>
        """))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("function", "exp"), ("function", "explode")])

        # Test "<%=" tags
        content, positions = unmark_text(dedent("""\
        <%= exp<1>lode(); %>
        """))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("function", "exp"), ("function", "explode")])

    @tag("bug63487")
    def test_argument_by_reference_calltip(self):
        content, positions = unmark_text(php_markup(dedent("""\
            function foo(&$node) {
                echo "this is the function foo, node: $node";
            }
            function foo2($arg1, & $arg2) {
                echo "this is the function foo2. Args: $arg1, $arg2";
            }
            function foo3( & $arg1, & $arg2) {
                echo "this is the function foo3. Args: $arg1, $arg2";
            }
            foo(<1>);
            foo2(<2>);
            foo3(<3>);
        """)))
        self.assertCalltipIs(markup_text(content, pos=positions[1]),
                             "foo(node)")
        self.assertCalltipIs(markup_text(content, pos=positions[2]),
                             "foo2(arg1, arg2)")
        self.assertCalltipIs(markup_text(content, pos=positions[3]),
                             "foo3(arg1, arg2)")

    @tag("bug64227")
    def test_edge_cases(self):
        content, positions = unmark_text(php_markup(dedent("""\
            req<1>
        """)))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("keyword", "require"), ("keyword", "require_once")])

    @tag("bug65159")
    def test_complete_imported_variables(self):
        test_dir = join(self.test_dir, "test_complete_imported_variables")
        test_content, test_positions = unmark_text(php_markup(dedent("""
            require_once("import_1.php");
            require_once("import_2.php");

            $v<1>ar_in_global = "local_1";
            
            function func_inside_func() {
                print "var_in_function: " . $v<2>ar_in_function . "\\n";
            }

        """)))
        manifest = [
            ("test.php", test_content),
            ("import_1.php", self.import1_content),
            ("import_2.php", self.import2_content),
        ]
        for file, content in manifest:
            path = join(test_dir, file)
            writefile(path, content)

        buf = self.mgr.buf_from_path(join(test_dir, "test.php"), lang=self.lang)
        self.assertCompletionsInclude2(buf, test_positions[1],
            [("variable", "var_in_one"), ("variable", "var_in_two"), ])
        self.assertCompletionsDoNotInclude2(buf, test_positions[2],
            [("variable", "var_in_one"),
             ("variable", "var_in_two"), ])

    @tag("bug64208")
    def test_import_with_variable_part(self):
        test_dir = join(self.test_dir, "test_import_with_variable_part")
        test_content, test_positions = unmark_text(php_markup(dedent("""\
            require ($PATH_PREFIX . "simple.php");
            $x = Sim<1>pleFunction(1, 2);
            $obj = new <2>SimpleClass();
            $obj-><3>foo();
        """)))

        manifest = [
            ("simple.php", php_markup(dedent("""
                class SimpleClass {
                    var $simple_var;
                    function foo() {
                    }
                }
                function SimpleFunction($arg1, $arg2) {
                    return "a string";
                }
             """))),
            ("test.php", test_content),
        ]
        for file, content in manifest:
            path = join(test_dir, file)
            writefile(path, content)

        buf = self.mgr.buf_from_path(join(test_dir, "test.php"), lang=self.lang)
        self.assertCompletionsInclude2(buf, test_positions[1],
            [("function", "SimpleFunction")])
        self.assertCompletionsInclude2(buf, test_positions[2],
            [("class", "SimpleClass")])
        self.assertCompletionsInclude2(buf, test_positions[3],
            [("function", "foo"), ("variable", "simple_var")])

    @tag("bug61497")
    def test_ignore_specific_calltip_keywords(self):
        content, positions = unmark_text(php_markup(dedent("""\
            if(<1>"myfile.php") { }
            elseif(<2>1) { }
            for (<3>$i=0; $i < 10; $i++) { }
            foreach (<4>) { }
            while (<5>x < 10) { x-= 1; }
        """)))
        for i in range(1, 6):
            self.assertCalltipIs(markup_text(content, pos=positions[i]), None)

    @tag("bug67094")
    def test_complete_functions(self):
        # Test after long, lots of comments
        content, positions = unmark_text(php_markup(dedent("""\
            %s
            pri<1>;
        """) % ("// Lots of comment strings here\n" * 20)))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("function", "printf"), ("function", "print_r")])

        # Test after lots of whitespace
        content, positions = unmark_text(php_markup(dedent("""\
            %s
            pri<1>;
        """) % ("                                \n" * 20)))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("function", "printf"), ("function", "print_r")])

    @tag("bug67626", "knownfailure")
    def test_complete_explicit_functions_from_keyword(self):
        # Test that we still get completions when current identifier part
        # matches to a php keyword
        content, positions = unmark_text(php_markup(dedent("""\
            var<1>;
            class<2>;
        """)))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("function", "var_dump"),
             ("function", "var_export")])
        # Try explicit triggering from a keyword
        # XXX : this actually passes in the real scintilla editor!?
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[2]),
            [("function", "class_exists"),
             ("function", "class_implements")],
            implicit=False)

    @tag("bug67696")
    def test_complete_functions_after_keyword(self):
        # Test after a keyword like "return"
        content, positions = unmark_text(php_markup(dedent("""\
            function foo($x) {
                return sub<1>($x, 1);
            }
        """)))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("function", "substr"),
             ("function", "substr_compare"),
             ("function", "substr_replace")])

    @tag("bug67329")
    def test_with_error_supression(self):
        # http://bugs.activestate.com/show_bug.cgi?id=67329
        # Test completion of functions when using an error supressor "@" char
        self.assertTriggerMatches(php_markup("@ses<|>sion_start();"),
                                  name="php-complete-functions")
        content, positions = unmark_text(php_markup(dedent("""\
            @ses<1>sion_start();
            function test_func() { }
            @test_func(<2>);
        """)))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("function", "session_start"),
             ("function", "session_name")])
        self.assertCalltipIs(markup_text(content, pos=positions[2]),
                             "test_func()")

    @tag("bug70212")
    def test_short_tags(self):
        content, positions = unmark_text(dedent("""<? pri<1> ?>"""))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("function", "printf"), ("function", "print_r")])
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("function", "printf"), ("function", "print_r")])

        content, positions = unmark_text(dedent("""<?\
            class a_temp_class {
                var $temp_var = "1";
            }
            function function_in_bar() { }
            $c_inst = new <1>a_temp_class();
            $c_inst-><2>xxx;
            fun<3>xxx;
            ?>"""))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("class", "a_temp_class")])
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[2]),
            [("variable", "temp_var")])
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[3]),
            [("function", "function_in_bar")])

    @tag("bug67774")
    def test_recursion(self):
        # http://bugs.activestate.com/show_bug.cgi?id=67774
        # Test catches recursive errors with php
        content, positions = unmark_text(php_markup(dedent("""\
            class deeper {
              function __construct() {
                $x = 1;
              }
              function _mine($foo) {
                return $foo;
              }
            }
            class top {
              public $deeper;
              function __construct() {
                  $this->deeper = new deeper();
              }
            }
            $xxx = new top();
            $xxx->deeper-><1>something;
        """)))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("function", "__construct"),
             ("function", "_mine")])

        content, positions = unmark_text(php_markup(dedent("""\
            class deep {
              function foo() {}
            }
            class deeptoo {
              function bar() {}
            }
            class top {
              public $deep;
              public $deeptoo;
              function __construct() {
                  $this->deep = new deeptoo(); # note the switch here
                  $this->deeptoo = new deep();
              }
            }
            $xxx = new top();
            $xxx->deep-><1>something;
            $xxx->deeptoo-><2>something;
        """)))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("function", "bar")])
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[2]),
            [("function", "foo")])

    @tag("bug47608")
    def test_class_as_non_keyword(self):
        # http://bugs.activestate.com/show_bug.cgi?id=47608
        content, positions = unmark_text(php_markup(dedent("""\
            class mine extends PDO {
                public $class = "";
                function __construct($class) {
                    $this->class = $class;
                    echo "Error: $class not defined!\n";
                }
            }
            $c = new mine();
            $c-><1>xxx;
        """)))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("function", "__construct"),
             ("variable", "class")])

    @tag("bug69758")
    def test_complete_magic_methods(self):
        # http://bugs.activestate.com/show_bug.cgi?id=69758

        class_magic_methods = sorted(php_magic_class_method_data.keys())
        global_magic_methods = sorted(php_magic_global_method_data.keys())

        content, positions = unmark_text(php_markup(dedent("""\
            class MyNewTestClass {
                function __<1>xxx($class) { }
            }
            function __<2>xxx() { }
            class MySecondTestClass {
                function __construct(<3>) { }
            }
        """)))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [ ("function", name) for name in class_magic_methods ])
        self.assertCompletionsDoNotInclude(markup_text(content, pos=positions[1]),
                [ ("function", name) for name in global_magic_methods ])

        self.assertCompletionsInclude(
            markup_text(content, pos=positions[2]),
            [ ("function", name) for name in global_magic_methods ])
        self.assertCompletionsDoNotInclude(markup_text(content, pos=positions[2]),
                [ ("function", name) for name in class_magic_methods ])

        self.assertCalltipIs(markup_text(content, pos=positions[3]),
                             php_magic_class_method_data.get("__construct"))

    @tag("bug41700")
    def test_complete_constants(self):
        # http://bugs.activestate.com/show_bug.cgi?id=41700

        content, positions = unmark_text(php_markup(dedent("""\
            define("MAXSIZE", 100);
            $myvar = 1;
            class ConstBaseClass {
                const base_constant;
                var $base_instance_var;
            }
            class ConstTestClass extends ConstBaseClass {
                const a_constant = 10;
                var $an_instance_var;
                function somefunc() {
                    $this-><1>xxx;
                    self::<2>xxx;
                    MAX<3>;
                }
            }
            ConstTestClass::<4>xxx;
            $x = MAX<5>;
            $c_inst = new ConstTestClass();
            $c_inst-><6>xxx;
        """)))

        self.assertCompletionsAre(markup_text(content, pos=positions[1]),
            [ ("variable", "an_instance_var"),
              ("variable", "base_instance_var"),
              ("function", "somefunc") ])

        self.assertCompletionsAre(markup_text(content, pos=positions[2]),
            [ ("constant", "a_constant"),
              ("constant", "base_constant"),
              ("function", "somefunc") ])

        self.assertCompletionsInclude(markup_text(content, pos=positions[3]),
            [ ("constant", "MAXSIZE") ])

        self.assertCompletionsAre(markup_text(content, pos=positions[4]),
            [ ("constant", "a_constant"),
              ("constant", "base_constant"),
              ("function", "somefunc") ])

        self.assertCompletionsInclude(markup_text(content, pos=positions[5]),
            [ ("constant", "MAXSIZE") ])
        self.assertCompletionsDoNotInclude(markup_text(content, pos=positions[5]),
            [ ("constant", "myvar") ])
        self.assertCompletionsDoNotInclude(markup_text(content, pos=positions[5]),
            [ ("variable", "myvar") ])

        self.assertCompletionsAre(markup_text(content, pos=positions[6]),
            [ ("variable", "an_instance_var"),
              ("variable", "base_instance_var"),
              ("function", "somefunc") ])

    # Now try using constants through imports.
    @tag("bug41700")
    def test_complete_constants_from_imports(self):
        # http://bugs.activestate.com/show_bug.cgi?id=41700

        test_dir = join(self.test_dir, "test_complete_constants_from_imports")
        test_content, test_positions = unmark_text(php_markup(dedent("""\
            require ("simple.php");
            $x = SIM<1>;
            $obj = new SimpleClassForConst();
            $obj-><2>foo();
            SimpleClassForConst::<3>xxx;
        """)))

        manifest = [
            ("simple.php", php_markup(dedent("""
                define("SIMPLE_DEFINE", 100);
                class SimpleClassForConst {
                    const simple_constant;
                    var $simple_variable;
                }
             """))),
            ("test.php", test_content),
        ]
        for file, content in manifest:
            path = join(test_dir, file)
            writefile(path, content)

        buf = self.mgr.buf_from_path(join(test_dir, "test.php"), lang=self.lang)
        self.assertCompletionsInclude2(buf, test_positions[1],
            [("constant", "SIMPLE_DEFINE")])
        self.assertCompletionsAre2(buf, test_positions[2],
            [("variable", "simple_variable")])
        self.assertCompletionsAre2(buf, test_positions[3],
            [("constant", "simple_constant")])

    @tag("bug67367")
    def test_complete_array_members(self):
        # http://bugs.activestate.com/show_bug.cgi?id=67367

        content, positions = unmark_text(php_markup(dedent("""\
            $_SERVER["<1>SERVER_NAME"];
        """)))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
                [("variable", 'SERVER_ADDR'),
                 ("variable", 'SERVER_NAME'),
                ])

    @tag("bug78042")
    def test_class_variable_ciling(self):
        # http://bugs.activestate.com/show_bug.cgi?id=78042

        content, positions = unmark_text(php_markup(dedent("""\
            class bug78042_class {
                function bug78042_func() {
                    $this-><1>xxx;
                    self::<2>yyy;
                }
            }
        """)))
        self.assertCompletionsAre(markup_text(content, pos=positions[1]),
                [("function", 'bug78042_func'), ])
        self.assertCompletionsAre(markup_text(content, pos=positions[2]),
                [("function", 'bug78042_func'), ])

    @tag("bug78050")
    def test_class_variable_ciling(self):
        # http://bugs.activestate.com/show_bug.cgi?id=78050

        content, positions = unmark_text(php_markup(dedent("""\
            class bug78050_class {
                function bug78050_func() {
                    $this-><1>xxx == 1;
                }
            }
        """)))
        self.assertCompletionsAre(markup_text(content, pos=positions[1]),
                [("function", 'bug78050_func'), ])

    @tag("bug78957")
    def test_alternative_control_syntax(self):
        # http://bugs.activestate.com/show_bug.cgi?id=78957

        content, positions = unmark_text(php_markup(dedent("""\
            if ( !function_exists('bug78957_function') ) :
            function bug78957_function($id, $name = '') { }
            endif;
            bug<1>
        """)))
        self.assertCompletionsAre(markup_text(content, pos=positions[1]),
                [("function", 'bug78957_function'), ])

    @tag("bug79003", "php5")
    def test_type_hinting(self):
        # http://ch2.php.net/language.oop5.typehinting

        content, positions = unmark_text(php_markup(dedent("""\
            <?php
            // An example class
            class bug79003Class
            {
                public function test(bug79003OtherClass $otherclass) {
                    echo $otherclass-><3>var;
                }
            
                public function test_array(array $input_array) {
                    print_r($input_array);
                }
            }
            
            class bug79003OtherClass {
                public $var = 'Hello World';
                public function test_func() {}
            }

            $inst_myclass = new bug79003Class();
            $inst_myclass->test(<1>);
            $inst_myclass->test_array(<2>);
            ?>
        """)))
        self.assertCalltipIs(markup_text(content, pos=positions[1]),
                             "test(bug79003OtherClass otherclass)")
        self.assertCalltipIs(markup_text(content, pos=positions[2]),
                             "test_array(array input_array)")
        self.assertCompletionsAre(markup_text(content, pos=positions[3]),
                [("function", 'test_func'),
                 ("variable", 'var'),])

    @tag("bug77532")
    def test_keyword_completions(self):
        # bug 77532:
        #  Test to ensure that keywords are included in the 3-character
        #  completion results.

        content, positions = unmark_text(php_markup(dedent("""\
            fun<1>ct; # completions include keywords
            if (fun<2>) {}  # do not want to include "function", "class", ... keywords
            if ( !fun<3>ction_exists('function_bug77532') ) :
                fun<4>ction fun<5>ction_bug77532($id, $name = '') { }
            endif;
        """)))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
                [('keyword',  'function'),
                 ('function', 'function_bug77532'),
                 ('function', 'function_exists')])
        self.assertCompletionsInclude(markup_text(content, pos=positions[2]),
                [('function', 'function_bug77532'),
                 ('function', 'function_exists')])
        #self.assertCompletionsDoNotInclude(markup_text(content, pos=positions[2]),
        #        [('keyword', 'function'), ])
        self.assertCompletionsInclude(markup_text(content, pos=positions[3]),
                [('function', 'function_bug77532'),
                 ('function', 'function_exists')])
        #self.assertCompletionsDoNotInclude(markup_text(content, pos=positions[3]),
        #        [('keyword', 'function'), ])
        self.assertCompletionsInclude(markup_text(content, pos=positions[4]),
                [('keyword',  'function'),
                 ('function', 'function_bug77532'),
                 ('function', 'function_exists')])
        # Don't want to trigger after "function" in this case
        self.assertNoTrigger(markup_text(content, pos=positions[5]))

    @tag("bug80512")
    def test_variable_completions_in_class_function(self):
        content, positions = unmark_text(php_markup(dedent("""\
            class bug80512_class {
                function dummyMethod() {
                    $thisVar = true;
                    $t<1>;
                }
                $t<2>;
            }
            $t<3>;
        """)))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
                [("variable", 'this'),
                 ("variable", 'thisVar'),])
        self.assertCompletionsDoNotInclude(markup_text(content, pos=positions[2]),
                [("variable", 'this'),])
        self.assertCompletionsDoNotInclude(markup_text(content, pos=positions[3]),
                [("variable", 'this'),])

    @tag("bug82721")
    def test_php4_class_constructor_calltip(self):
        content, positions = unmark_text(php_markup(dedent("""\
            class bug82721_class {
                function bug82721_class($var1, $var2, $var3) {
                    echo "code";
                }
            }
            $ac = new bug82721_class(<1>);
        """)))
        self.assertCalltipIs(markup_text(content, pos=positions[1]),
                             "bug82721_class(var1, var2, var3)")

    @tag("bug83381")
    def test_function_calltip_interface_fallback(self):
        content, positions = unmark_text(php_markup(dedent("""\
            interface HelloInterface {
               /**
                * Print the word hello.
                */
               public function printHello();
            }

            interface WorldInterface {
               /**
                * Print the word world.
                */
               public function printWorld();
            }

            class HelloWorld implements HelloInterface, WorldInterface {
            
                public function printHello() {
                    print "Hello ";
                }
                public function printWorld() {
                    print "world!";
                }
            }
            $hw_inst = new HelloWorld();
            $hw_inst->printHello(<1>);
            $hw_inst->printWorld(<2>);
        """)))
        self.assertCalltipIs(markup_text(content, pos=positions[1]),
                             "printHello()\nPrint the word hello.")
        self.assertCalltipIs(markup_text(content, pos=positions[2]),
                             "printWorld()\nPrint the word world.")


class IncludeEverythingTestCase(CodeIntelTestCase):
    lang = "PHP"
    test_dir = join(os.getcwd(), "tmp")

    def test_simple(self):
        # This is mostly pulled from php/defn/simple_import without the
        # explicit import.
        test_dir = join(self.test_dir, "test_simple")
        foo_content, foo_positions = unmark_text(php_markup(dedent("""\
            $a = $b<1>ar;
            $c = new class_in_bar();
            $c-><2>class_in_bar_var_1;

            # Test completion of an imported variable
            $c<3>_in_bar-><4>xyz;

            # Test completion of imported function names
            fun<5>;

            # Test completion of imported class names
            class myclass extends <6>aaa { };
        """)))

        manifest = [
            ("bar.php", php_markup(dedent("""
                $bar = 42;
                class class_in_bar {
                    var $class_in_bar_var_1 = "1";
                }
                $c_in_bar = new class_in_bar();
                $c_var_in_bar = 1;
                function function_in_bar() { }
             """))),
            ("foo.php", foo_content),
        ]
        for file, content in manifest:
            path = join(test_dir, file)
            writefile(path, content)

        buf = self.mgr.buf_from_path(join(test_dir, "foo.php"))
        self.assertDefnMatches2(buf, foo_positions[1],
            ilk="variable", name="bar", line=2, citdl="int",
            path=join(test_dir, "bar.php"), )
        self.assertCompletionsInclude2(buf, foo_positions[2],
            [("variable", "class_in_bar_var_1")])
        self.assertCompletionsInclude2(buf, foo_positions[3],
            [("variable", "c_in_bar"),
             ("variable", "c_var_in_bar")])
        self.assertCompletionsInclude2(buf, foo_positions[4],
            [("variable", "class_in_bar_var_1")])
        self.assertCompletionsInclude2(buf, foo_positions[5],
            [("function", "function_in_bar")])
        self.assertCompletionsInclude2(buf, foo_positions[6],
            [("class", "class_in_bar")])

    # Copied from TriggerTestCase above, just removing the require
    def test_php_local_import_1(self):
        test_dir = join(self.test_dir, "test_php_local_import_1")
        test_content, test_positions = unmark_text(php_markup(dedent("""\
            // require ("simple.php");
            $x = Sim<1>pleFunction(1, 2);
            $obj = new <2>SimpleClass();
            $obj-><3>foo();
        """)))

        manifest = [
            ("simple.php", php_markup(dedent("""
                class SimpleClass {
                    var $simple_var;
                    function foo() {
                    }
                }
                function SimpleFunction($arg1, $arg2) {
                    return "a string";
                }
             """))),
            ("test.php", test_content),
        ]
        for file, content in manifest:
            path = join(test_dir, file)
            writefile(path, content)

        buf = self.mgr.buf_from_path(join(test_dir, "test.php"), lang=self.lang)
        self.assertCompletionsInclude2(buf, test_positions[1],
            [("function", "SimpleFunction")])
        self.assertCompletionsInclude2(buf, test_positions[2],
            [("class", "SimpleClass")])
        self.assertCompletionsInclude2(buf, test_positions[3],
            [("function", "foo"), ("variable", "simple_var")])


    def test_php_local_import_2(self):
        test_dir = join(self.test_dir, "test_php_local_import_2")
        test_content, test_positions = unmark_text(php_markup(dedent("""\
            // require ("simple1/simple1.php");
            // require ("simple2/simple2.php");
            $x = Sim<1>pleFunction1(1, 2);
            $obj = new <2>SimpleClass2();
            $obj-><3>foo();
        """)))

        manifest = [
            (join(test_dir, "simple1", "simple1.php"), php_markup(dedent("""
                class SimpleClass1 {
                    var $simple_var1;
                    function simple_func1() {
                    }
                }
                function SimpleFunction1($arg1, $arg2) {
                    return "a string";
                }
             """))),
            (join(test_dir, "simple2", "simple2.php"), php_markup(dedent("""
                class SimpleClass2 {
                    var $simple_var2;
                    function simple_func2() {
                    }
                }
                function SimpleFunction2($arg1, $arg2) {
                    return "a string";
                }
             """))),
            (join(test_dir, "test.php"), test_content),
        ]
        extra_paths = []
        for filepath, content in manifest:
            writefile(filepath, content)
            if filepath != manifest[-1][0]:
                extra_paths.append(dirname(filepath))

        extra_paths = [ abspath(p) for p in extra_paths ]
        env = SimplePrefsEnvironment(phpExtraPaths=os.pathsep.join(extra_paths))

        buf = self.mgr.buf_from_path(join(test_dir, "test.php"), lang=self.lang,
                                     env=env)
        self.assertCompletionsInclude2(buf, test_positions[1],
            [("function", "SimpleFunction1"),
             ("function", "SimpleFunction2")])
        self.assertCompletionsInclude2(buf, test_positions[2],
            [("class", "SimpleClass1"),
             ("class", "SimpleClass2")])
        self.assertCompletionsInclude2(buf, test_positions[3],
            [("function", "simple_func2"), ("variable", "simple_var2")])

    # Inheritance test content, will be used in a few test so defining it here
    import1_content = php_markup(dedent("""\
        class one {
            public $x;
            function __construct() {
                $x = 1;
            }
            function mine($x,$y) {
                return func_get_args();
            } 
        }
        function _this_is_from_import_1($foo) {
            return 1;
        }
        $var_in_one = "1";
    """))

    import2_content = php_markup(dedent("""\
        class two {
            public $y;
            function __construct() {
                $y = 1;
            }
            function yours($x,$y) {
                return func_get_args();
            } 
        }
        function _this_is_from_import_2($foo) {
            return 1;
        }
        $var_in_two = "2";
    """))

    @tag("bug57887")
    def test_completion_with_multiple_imports(self):
        test_dir = join(self.test_dir, "test_bug57887_completion_with_multiple_imports")
        test_content, test_positions = unmark_text(php_markup(dedent("""\
            // require_once("import_1.php");
            // require_once("import_2.php");

            class ext_one extends <1>one {
                function __construct($foo) {
                    $this-><2>xxx;
                    self::<3>mine();
                    parent::<4>
                }
            }

            class ext_two extends <5>two {
                function __construct($foo) {
                    $this-><6>xxx;
                    self::<7>yours();
                    parent::<8>
                }
            }
        """)))
        manifest = [
            ("test.php", test_content),
            ("import_1.php", self.import1_content),
            ("import_2.php", self.import2_content),
        ]
        for file, content in manifest:
            path = join(test_dir, file)
            writefile(path, content)

        buf = self.mgr.buf_from_path(join(test_dir, "test.php"), lang=self.lang)
        self.assertCompletionsInclude2(buf, test_positions[1],
            [("class", "one"), ("class", "two")])
        self.assertCompletionsInclude2(buf, test_positions[2],
            [("variable", "x"), ("function", "mine"), ("function", "__construct")])
        self.assertCompletionsInclude2(buf, test_positions[3],
            [("function", "mine"), ("function", "__construct")])
        self.assertCompletionsInclude2(buf, test_positions[4],
            [("function", "mine"), ("function", "__construct")])
        self.assertCompletionsInclude2(buf, test_positions[5],
            [("class", "one"), ("class", "two")])
        self.assertCompletionsInclude2(buf, test_positions[6],
            [("variable", "y"), ("function", "yours"), ("function", "__construct")])
        self.assertCompletionsInclude2(buf, test_positions[7],
            [("function", "yours"), ("function", "__construct")])
        self.assertCompletionsInclude2(buf, test_positions[8],
            [("function", "yours"), ("function", "__construct")])

    def test_completion_with_import_inside_import(self):
        test_dir = join(self.test_dir, "test_completion_with_import_inside_import")
        test_content, test_positions = unmark_text(php_markup(dedent("""\
            // require_once("import_3.php");

            class local_one extends <1>ext_three {
                function __construct($foo) {
                    $this-><2>xxx;
                    self::<3>mine();
                    parent::<4>
                }
            }

            class local_two extends <5>ext_four {
                var $local_y;
                function __construct($foo) {
                    $this-><6>xxx;
                    self::<7>yours();
                    parent::<8>
                }
            }

            $obj_one = new <9>one();
            $obj_one-><10>xyz;

            $obj_two = new local_two();
            $obj_two-><11>xyz;
        """)))
        manifest = [
            ("test.php", test_content),
            ("import_1.php", self.import1_content),
            ("import_2.php", self.import2_content),
            ("import_3.php", php_markup(dedent("""\
                // require_once("import_1.php");
                // require_once("import_2.php");

                class ext_three extends one {
                    function func_in_three() {
                    }
                }

                class ext_four extends two {
                    function func_in_four() {
                    }
                }
            """))),
        ]
        for file, content in manifest:
            path = join(test_dir, file)
            writefile(path, content)

        buf = self.mgr.buf_from_path(join(test_dir, "test.php"), lang=self.lang)
        self.assertCompletionsInclude2(buf, test_positions[1],
            [("class", "one"), ("class", "two"),
             ("class", "ext_three"), ("class", "ext_four"), ])
        self.assertCompletionsInclude2(buf, test_positions[2],
            [("variable", "x"), ("function", "mine"),
             ("function", "__construct"), ("function", "func_in_three")])
        self.assertCompletionsInclude2(buf, test_positions[3],
            [("function", "mine"),
             ("function", "__construct"), ("function", "func_in_three")])
        self.assertCompletionsInclude2(buf, test_positions[4],
            [("function", "mine"),
             ("function", "__construct"), ("function", "func_in_three")])
        self.assertCompletionsInclude2(buf, test_positions[5],
            [("class", "one"), ("class", "two"),
             ("class", "ext_three"), ("class", "ext_four"), ])
        self.assertCompletionsInclude2(buf, test_positions[6],
            [("variable", "y"), ("variable", "local_y"), ("function", "yours"),
             ("function", "__construct"), ("function", "func_in_four")])
        self.assertCompletionsInclude2(buf, test_positions[7],
            [("function", "yours"),
             ("function", "__construct"), ("function", "func_in_four")])
        self.assertCompletionsInclude2(buf, test_positions[8],
            [("function", "yours"),
             ("function", "__construct"), ("function", "func_in_four")])
        self.assertCompletionsInclude2(buf, test_positions[9],
            [("class", "one"), ("class", "two"),
             ("class", "ext_three"), ("class", "ext_four"),
             ("class", "local_one"), ("class", "local_two"), ])
        self.assertCompletionsInclude2(buf, test_positions[10],
            [("variable", "x"), ("function", "mine"),
             ("function", "__construct"), ])
        self.assertCompletionsInclude2(buf, test_positions[11],
            [("variable", "y"), ("variable", "local_y"), ("function", "yours"),
             ("function", "__construct"), ("function", "func_in_four")])

    def test_recursive_importing(self):
        test_dir = join(self.test_dir, "test_recursive_importing")
        test_content, test_positions = unmark_text(php_markup(dedent("""\
            // require_once("foo.php");
            class local extends <1>foo {
                var $x_local;
                function func_in_local() { }
            }
            $obj = new <2>local();
            $obj-><3>xyz;
        """)))
        manifest = [
            ("test.php", test_content),
            ("foo.php", php_markup(dedent("""\
                // require_once("bar.php");
                class foo extends bar {
                    var $x_foo;
                    function func_in_foo() { }
                }
            """))),
            ("bar.php", php_markup(dedent("""\
                // require_once("baz.php");
                class bar extends baz {
                    var $x_bar;
                    function func_in_bar() { }
                }
            """))),
            ("baz.php", php_markup(dedent("""\
                // require_once("foo.php");
                # Recurse back to foo
                class baz extends foo {
                    var $x_baz;
                    function func_in_baz() { }
                }
            """))),
        ]
        for file, content in manifest:
            path = join(test_dir, file)
            writefile(path, content)

        buf = self.mgr.buf_from_path(join(test_dir, "test.php"), lang=self.lang)
        self.assertCompletionsInclude2(buf, test_positions[1],
            [("class", "foo"), ("class", "bar"), ("class", "baz"), ])
        self.assertCompletionsInclude2(buf, test_positions[2],
            [("class", "foo"), ("class", "bar"), ("class", "baz"), ("class", "local"), ])
        self.assertCompletionsInclude2(buf, test_positions[3],
            [("variable", "x_local"), ("variable", "x_foo"),
             ("variable", "x_bar"),   ("variable", "x_baz"),
             ("function", "func_in_local"), ("function", "func_in_foo"),
             ("function", "func_in_bar"),   ("function", "func_in_baz"),
             ])

    @tag("bug67098")
    def test_indirect_import_handling(self):
        test_dir = join(self.test_dir, "test_indirect_import_handling")
        test_content, test_positions = unmark_text(php_markup(dedent("""\
            require_once('include/class_def.php');
            require_once('include/myclass.php');
            $myClass = new MyClass();
            echo $myClass-><1>mcMyClassOne();
        """)))

        manifest = [
            (join(test_dir, "include", "class_def.php"), php_markup(dedent("""
                class MyBaseClass {
                    public function bcMethodOne() {
                        return __METHOD__;
                    }
                    public function bcMethodTwo($p1, $p2) {
                        return __METHOD__ . " $p1 $p2";
                    }
                }
             """))),
            (join(test_dir, "include", "myclass.php"), php_markup(dedent("""
                class MyClass extends MyBaseClass {
                    public function mcMyClassOne() {
                        return __METHOD__;
                    }
                }
             """))),
            (join(test_dir, "test.php"), test_content),
        ]
        for filepath, content in manifest:
            writefile(filepath, content)

        env = SimplePrefsEnvironment(phpExtraPaths=join(test_dir, "include"))
        buf = self.mgr.buf_from_path(join(test_dir, "test.php"), lang=self.lang,
                                     env=env)
        self.assertCompletionsInclude2(buf, test_positions[1],
            [("function", "mcMyClassOne"), ("function", "bcMethodOne"),
             ("function", "bcMethodTwo")])

    @tag("bug72096")
    def test_multi_var_declaration(self):
        content, positions = unmark_text(php_markup(dedent("""\
            class multi_var_test {
                private $priv1, $priv2;
                var $foo, $bar, $baz;
                var $x1 = 2, $y1 = 3, $z1 = 4;
                function mine($foo) {
                    $this-><1>xxx;
                }
            }
            $mine_1 = new multi_var_test(), $other_1 = new multi_var_test();
            $mine_1-><2>xxx;
            $other_1-><3>xxx;
        """)))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("variable", "priv1"), ("variable", "priv2"), 
             ("variable", "foo"), ("variable", "bar"), ("variable", "baz"),
             ("variable", "x1"), ("variable", "y1"), ("variable", "z1"),
             ("function", "mine"), ])
        self.assertCompletionsInclude(markup_text(content, pos=positions[2]),
            [("variable", "foo"), ("variable", "bar"), ("variable", "baz"),
             ("variable", "x1"), ("variable", "y1"), ("variable", "z1"),
             ("function", "mine"), ])
        self.assertCompletionsInclude(markup_text(content, pos=positions[3]),
            [("variable", "foo"), ("variable", "bar"), ("variable", "baz"),
             ("variable", "x1"), ("variable", "y1"), ("variable", "z1"),
             ("function", "mine"), ])

    @tag("bug71872")
    def test_completions_on_files_with_the_same_name(self):
        # In PHP, only one of these files would win, but since we include
        # everything in Komodo, we don't know which one it would be so
        # we should be checking all possible matches.
        # The bug is that Komodo is currently only ever checking one of
        # the possible files. This is because the database get_blob()
        # implementation does not keep track of same named blobs.
        test_dir = join(self.test_dir,
                        "test_completions_on_files_with_the_same_name")
        test_content, test_positions = unmark_text(php_markup(dedent("""\
            $rdata = new <1>Reg_Data();
            Reg_Data::<2>xxx;
        """)))

        manifest = [
            (join(test_dir, "include_a", "Data.php"), php_markup(dedent("""
                class blah_Data {
                    public static $a_pub_var;
                }
             """))),
            (join(test_dir, "include_b", "Data.php"), php_markup(dedent("""
                class Reg_Data {
                    public static $b_pub_var;
                }
             """))),
            (join(test_dir, "include_c", "Data.php"), php_markup(dedent("""
                class Foo_Data {
                    public static $c_pub_var;
                }
             """))),
            (join(test_dir, "test.php"), test_content),
        ]
        for filepath, content in manifest:
            writefile(filepath, content)

        extra_paths = [join(test_dir, "include_a"),
                       join(test_dir, "include_b"),
                       join(test_dir, "include_c")]
        env = SimplePrefsEnvironment(phpExtraPaths=os.pathsep.join(extra_paths))
        buf = self.mgr.buf_from_path(join(test_dir, "test.php"), lang=self.lang,
                                     env=env)
        self.assertCompletionsInclude2(buf, test_positions[1],
            [("class", "Reg_Data")])
        self.assertCompletionsInclude2(buf, test_positions[2],
            [("variable", "$b_pub_var")])
        self.assertCompletionsDoNotInclude2(buf, test_positions[2],
            [("variable", "$a_pub_var"), ("variable", "$c_pub_var")])

    @tag("bug74625")
    def test_variable_with_complex_citdl(self):
        # Need to make sure we properly obtain all the type information
        # from declared variables.
        content, positions = unmark_text(php_markup(dedent("""\
            class Bug74625 {
                public $field = "";
                public static function getInstance() {
                    return new self();
                }
            }
            $bug74625_instance = Bug74625::getInstance();
            $b<1>ug74625_instance-><2>xxx;
        """)))

        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("variable", "bug74625_instance")])
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[2]),
            [("variable", "field"), ("function", "getInstance")])

    @tag("bug74627")
    def test_doctags_variable_type_inferencing(self):
        # Test for ensuring the type inference information can be set
        # through a phpdoc comment.
        content, positions = unmark_text(php_markup(dedent("""\
            class Bug74627_dummy_class {
                public $field = "";
                public function callme() {
                }
            }
            class Bug74627 {
                /**
                 * View object
                 * @var Bug74627_dummy_class
                 */
                public $dummy;
            }
            $bug74627_instance = new Bug74627();
            $b<1>ug74627_instance-><2>dummy-><3>xxx;
        """)))

        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("variable", "bug74627_instance")])
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[2]),
            [("variable", "dummy")])
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[3]),
            [("variable", "field"), ("function", "callme")])

    @tag("bug70015")
    def test_class_and_instance_with_same_name(self):
        # Test for ensuring the citdl type can be found when the object
        # instance is the same as the class name.
        content, positions = unmark_text(php_markup(dedent("""\
            class Bug70015 {

                private $Width;
                private $Height;

                public function __construct() {
                    $this->Width = 400;
                    $this->Height = 400;
                }

                public function setMapDims($w, $h) {
                    $this->Width = $w;
                    $this-><3>Height = $h;
                }
            }
            $Bug70015 = new Bug70015();
            $B<1>ug70015-><2>setMapDims(<4>);
        """)))

        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("variable", "Bug70015")])
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[2]),
            [("function", "setMapDims")])
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[3]),
            [("function", "setMapDims"),
             ("variable", "Height"),
             ("variable", "Width")])
        self.assertCalltipIs(markup_text(content, pos=positions[4]),
                             "setMapDims(w, h)")

    @tag("bug76677")
    def test_3char_trigger_includes_classes(self):
        # Test for ensuring the citdl type can be found when the object
        # instance is the same as the class name.
        content, positions = unmark_text(php_markup(dedent("""\
            define("Bug76677_const", 100);
            function Bug76677_func() { }
            class Bug76677_class {
                var $my_var;
                public static function my_func() { }
            }
            Bug<1>;
            foo<2>;
        """)))

        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("constant", "Bug76677_const"),
             ("function", "Bug76677_func"),
             ("class", "Bug76677_class"),
            ])

        self.assertCompletionsDoNotInclude(
            markup_text(content, pos=positions[1]),
            [("class", "Exception")])

        self.assertCompletionsDoNotInclude(
            markup_text(content, pos=positions[2]),
            [("constant", "Bug76677_const"),
             ("function", "Bug76677_func"),
             ("class", "Bug76677_class"),
            ])

    @tag("bug76746")
    def test_ignore_unhelpful_variable_types(self):
        # Test for ensuring the citdl type can be found when the object
        # instance is the same as the class name.
        content, positions = unmark_text(php_markup(dedent("""\
            class bug76746_dummyDB {
                public $connection;
            }

            class bug76746_dummyclass {
                /**
                * This variable contains the instance of the database class.
                * @var object
                */
                private $objDB;
                function __construct() {
                    $this->objDB = new bug76746_dummyDB();
                }

                function foo() {
                    $this->objDB-><1>xxx;
                }
            }
        """)))

        self.assertCompletionsAre(
            markup_text(content, pos=positions[1]),
            [("variable", "connection"), ])

    @tag("bug77834")
    def test_chained_method_calls(self):
        # Test for ensuring the citdl type can be found when the methods
        # are chained together.
        content, positions = unmark_text(php_markup(dedent("""\
            class bug77834_class {
                var $x = 0;
                /**
                 * @return bug77834_class
                 */
                function func1() { }
                function func2() { }
            }
            $bug77834_inst = new bug77834_class();
            $bug77834_inst->func1()-><1>xxx;
            $bug77834_inst->func1(5)-><2>xxx;
            $bug77834_inst->func1("a string", $x)-><3>func1("bae")-><4>xxx;
        """)))

        self.assertCompletionsAre(markup_text(content, pos=positions[1]),
            [("function", "func1"), ("function", "func2"), ("variable", "x")])
        self.assertCompletionsAre(markup_text(content, pos=positions[2]),
            [("function", "func1"), ("function", "func2"), ("variable", "x")])
        self.assertCompletionsAre(markup_text(content, pos=positions[3]),
            [("function", "func1"), ("function", "func2"), ("variable", "x")])
        self.assertCompletionsAre(markup_text(content, pos=positions[4]),
            [("function", "func1"), ("function", "func2"), ("variable", "x")])

    @tag("bug79221")
    def test_function_argument_handling(self):
        # Test to ensure can handle different styles of arguments.
        content, positions = unmark_text(php_markup(dedent("""\
            function test_bug79221($one, $two = array(), $three = false) { }
            test_bug79221(<1>);
        """)))

        self.assertCalltipIs(markup_text(content, pos=positions[1]),
                "test_bug79221(one, two=array(), three=false)")


class DefnTestCase(CodeIntelTestCase):
    lang = "PHP"
    test_dir = join(os.getcwd(), "tmp")

    def test_citdl_expr_under_pos_simple(self):
        self.assertCITDLExprUnderPosIs("foo-><|>", "foo")
        self.assertCITDLExprUnderPosIs("Foo::<|>", "Foo")
        self.assertCITDLExprUnderPosIs("foo->bar-><|>", "foo.bar")
        self.assertCITDLExprUnderPosIs("Fo<|>o::bar->", "Foo")
        self.assertCITDLExprUnderPosIs("foo(bar-><|>", "bar")
        self.assertCITDLExprUnderPosIs("foo[bar-><|>", "bar")
        self.assertCITDLExprUnderPosIs("foo{bar-><|>", "bar")
        self.assertCITDLExprUnderPosIs("foo()-><|>", "foo()")
        self.assertCITDLExprUnderPosIs("foo(a,b)-><|>", "foo()")
        self.assertCITDLExprUnderPosIs("$a = foo-><|>", "foo")
        # Ensure we only grab the correct context, and not too much
        self.assertCITDLExprUnderPosIs("foo->bar->b<|>az", "foo.bar.baz")
        self.assertCITDLExprUnderPosIs("foo->b<|>ar->baz", "foo.bar")
        self.assertCITDLExprUnderPosIs("fo<|>o->bar->baz", "foo")
        self.assertCITDLExprUnderPosIs("foo()->b<|>ar()->baz", "foo().bar")
    def test_citdl_expr_under_pos_simple2(self):
        self.assertCITDLExprUnderPosIs("$a = foo(bar<|>, blam)", "bar")
        self.assertCITDLExprUnderPosIs("blam()\nfoo-><|>", "foo")
        self.assertCITDLExprUnderPosIs("blam()->\nf<|>oo->", "blam().foo")
        self.assertCITDLExprUnderPosIs("blam()->\nfoo->b<|>ar", "blam().foo.bar")
        self.assertCITDLExprUnderPosIs("if(!<|>is_array", "is_array", trigger_name="functions")
        self.assertCITDLExprUnderPosIs("require('myfile.php');\nfo<|>o->bar", "foo")

    def test_simple(self):
        test_dir = join(self.test_dir, "test_defn_simple")
        foo_content, foo_positions = unmark_text(php_markup(dedent("""\
            function test1($i) {
                $b = 0;
                if ($i > 0) {
                    $b = $i;
                }
            }
            
            $t = test<1>1(0);
        """)))

        path = join(test_dir, "foo.php")
        writefile(path, foo_content)

        buf = self.mgr.buf_from_path(path)
        self.assertDefnMatches2(buf, foo_positions[1],
            ilk="function", name="test1", line=1, path=path, )

    def test_simple_import(self):
        test_dir = join(self.test_dir, "test_simple_import")
        foo_content, foo_positions = unmark_text(php_markup(dedent("""\
            require('bar.php');
            $a = $b<1>ar;
            $c = new class_in_bar();
            $c->class_<2>in_bar_var_1;
        """)))

        manifest = [
            ("bar.php", php_markup(dedent("""
                $bar = 42;
                class class_in_bar {
                    var $class_in_bar_var_1 = "1";
                }
             """))),
            ("foo.php", foo_content),
        ]
        for file, content in manifest:
            path = join(test_dir, file)
            writefile(path, content)

        buf = self.mgr.buf_from_path(join(test_dir, "foo.php"))
        self.assertDefnMatches2(buf, foo_positions[1],
            ilk="variable", name="bar", line=2, citdl="int",
            path=join(test_dir, "bar.php"), )
        self.assertDefnMatches2(buf, foo_positions[2],
            ilk="variable", name="class_in_bar_var_1", line=4, citdl="string",
            path=join(test_dir, "bar.php"), )

    #@tag("knownfailure")
    #def test_simple_import(self):
    #    test_dir = join(self.test_dir, "test_simple_import")
    #    foo_content, foo_positions = unmark_text(php_markup(dedent("""\
    #        require('bar.php');
    #        $a = $b<1>ar;
    #    """)))
    #
    #    manifest = [
    #        ("bar.php", php_markup(dedent("""
    #            $bar = 42;
    #         """))),
    #        ("foo.php", foo_content),
    #    ]
    #    for file, content in manifest:
    #        path = join(test_dir, file)
    #        writefile(path, content)
    #
    #    buf = self.mgr.buf_from_path(join(test_dir, "foo.php"))
    #    self.assertDefnMatches2(buf, foo_positions[1],
    #        ilk="variable", name="bar", line=2, citdl="int",
    #        path=join(test_dir, "bar.php"), )


    @tag("bug68793")
    def test_imported_class_instance(self):
        # http://bugs.activestate.com/show_bug.cgi?id=68793
        test_dir = join(self.test_dir, "test_defn", "imported_class_instance")
        foo_content, foo_positions = unmark_text(php_markup(dedent("""\
            $myclass_instance->xarg<1>;
        """)))

        manifest = [
            ("foo_two.php", php_markup(dedent("""
                class myclass {
                    var $xarg = "";
                    static function blah($arg1) {
                    }
                };
                $myclass_instance = new myclass();
                """))),
            ("foo_one.php", foo_content),
        ]
        for file, content in manifest:
            path = join(test_dir, file)
            writefile(path, content)

        buf = self.mgr.buf_from_path(join(test_dir, "foo_one.php"))
        self.assertDefnMatches2(buf, foo_positions[1],
            ilk="variable", name="xarg", line=3, citdl="string",
            path=join(test_dir, "foo_two.php"), )

    @tag("bug70423")
    def test_class_scope_restrictions(self):
        content, positions = unmark_text(php_markup(dedent("""\
            class MyScopeClass {
                static $s1 = "";
                private $x = 1;
                protected $y = "";
                public $z = 0;
                function foo() {
                    $this-><1>xxx == 10;
                    $xxx = self::<2>x;
                }
            }
            class MySecondScopeClass extends MyScopeClass {
                static $s2 = 0;
                private $x2 = 1;
                protected $y2 = "";
                public $z2 = 0;
                function bar() {
                    $this-><3>xxx == 20;
                    self::<4>foo();
                    parent::<5>foo();
                }
            }

            $scopetest = new MySecondScopeClass();
            $scopetest-><6>xxx;
            MySecondScopeClass::<7>xxx;
       """)))
        # Single base class
        self.assertCompletionsAre(markup_text(content, pos=positions[1]),
            [("function", "foo"),
             ("variable", "x"), ("variable", "y"), ("variable", "z")])
        # Using class scope resolution "self::"
        self.assertCompletionsAre(markup_text(content, pos=positions[2]),
            [("function", "foo"),
             ("variable", "$s1")])
        # Inheriting class, no base class private members seen.
        self.assertCompletionsAre(markup_text(content, pos=positions[3]),
            [("function", "bar"), ("function", "foo"),
             ("variable", "x2"),
             ("variable", "y"), ("variable", "y2"),
             ("variable", "z"), ("variable", "z2")])
        # Using class scope resolution "self::"
        self.assertCompletionsAre(markup_text(content, pos=positions[4]),
            [("function", "bar"), ("function", "foo"),
             ("variable", "$s1"), ("variable", "$s2")])
        # Using class scope resolution "parent::"
        self.assertCompletionsAre(markup_text(content, pos=positions[5]),
            [("function", "foo"),
             ("variable", "$s1")])
        # Global scope, no protected or private members seen.
        self.assertCompletionsAre(markup_text(content, pos=positions[6]),
            [("function", "bar"), ("function", "foo"),
             ("variable", "z"), ("variable", "z2")])
        # Static class scope resolution, functions and static members only.
        self.assertCompletionsAre(markup_text(content, pos=positions[7]),
            [("function", "bar"), ("function", "foo"),
             ("variable", "$s1"), ("variable", "$s2")])

    @tag("bug76676")
    def test_phpdoc_overriding_variable_citdls(self):
        content, positions = unmark_text(php_markup(dedent("""\
            class bug_76676_phpdoc_override {
                var $foo;
                function bar() {}
            }
            
            function bug_76676_makeInstance($class) {
              return new $class;
            }
            
            $bug_76676_instance = bug_76676_makeInstance('bug_76676_phpdoc_override');
            /* @var bug_76676_phpdoc_override */
            $bug_76676_instance-><1>xxx;
       """)))
        # Single base class
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("variable", "foo"),
             ("function", "bar"),
            ])

    @tag("bug76676")
    def test_phpdoc_optional_var_target(self):
        content, positions = unmark_text(php_markup(dedent("""\
            class bug76676_Class {
                function bug76676_func() {}
            }
            /**
              * @var $bug_76676_optional_var_target bug76676_Class
              */
            $foo = 1;
            $bug_76676_optional_var_target-><1>xxx;
       """)))
        # Single base class
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [ ("function", "bug76676_func"), ])

    @tag("bug72960")
    def test_phpdoc_class_property(self):
        # http://bugs.activestate.com/show_bug.cgi?id=72960
        # @property shows a "magic" property variable that is found inside the
        # class.
        content, positions = unmark_text(php_markup(dedent("""\
            /**
             * show off @property, @property-read, @property-write
             *
             * @property $noCitdlOrDoc
             * @property mixed $regular regular read/write property
             * @property-read int $foo the foo prop
             * @property-write string $bar the bar prop
             */
            class Magician
            {
                private $_thingy;
                private $_bar;
             
                function __get($var)
                {
                    switch ($var) {
                        case 'foo' :
                            return 45;
                        case 'regular' :
                            return $this->_thingy;
                    }
                }
                
                function __set($var, $val)
                {
                    switch ($var) {
                        case 'bar' :
                            $this->_bar = $val;
                            break;
                        case 'regular' :
                            if (is_string($val)) {
                                $this->_thingy = $val;
                            }
                    }
                }
            }
            $magical = new Magician();
            $magical-><1>xxx;
        """)))
        # Single base class
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("variable", "noCitdlOrDoc"),
             ("variable", "regular"),
             ("variable", "foo"),
             ("variable", "bar"),
            ])


#---- mainline

if __name__ == "__main__":
    unittest.main()


