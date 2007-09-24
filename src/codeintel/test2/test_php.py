#!/usr/bin/env python
# Copyright (c) 2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

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

from testlib import TestError, TestSkipped, TestFailed, tag
from citestsupport import CodeIntelTestCase, writefile



log = logging.getLogger("test")


def php_markup(s):
    return "<?php %s ?>" % (s)

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
        self.assertTriggerMatches(php_markup("myclass::<|>myfunc();"),
                                  name=name, pos=15)
        self.assertTriggerMatches(php_markup("self::<|>myfunc();"),
                                  name=name, pos=12)
        self.assertTriggerMatches(php_markup("parent::<|>myfunc();"),
                                  name=name, pos=14)
        self.assertTriggerMatches(php_markup("$foo->bar-><|>foobar;"),
                                  name=name, pos=17)
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

    @tag("bug54667", "knownfailure")
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


class CplnTestCase(CodeIntelTestCase):
    lang = "PHP"
    test_dir = join(os.getcwd(), "tmp")

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
            [("function", "foo"), ("variable", "bar")])

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
            [("variable", "x"), ("function", "foo")])
        self.assertCompletionsInclude(markup_text(content, pos=positions[3]),
            [("variable", "y"), ("function", "foo"), ("function", "bar")])
        self.assertCompletionsInclude(markup_text(content, pos=positions[4]),
            [("variable", "y"), ("function", "foo"), ("function", "bar")])
        self.assertCompletionsInclude(markup_text(content, pos=positions[5]),
            [("function", "foo")])

    def test_calltip_call_signature_for_builtins(self):
        markedup_content = php_markup(dedent("""\
            require(<|>"myfile.php");
       """))
        self.assertCalltipIs(markedup_content, "require(file_path)\nincludes and evaluates the specified file, produces a Fatal Error on error.")

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

    def test_php5_complete_object_members_for_builtins(self):
        markedup_content = php_markup(dedent("""\
            $e = new Exception("New exception");
            $e-><|>     # should have getMessage in completion list
       """))
        self.assertCompletionsInclude(markedup_content,
            [("function", "getMessage"), ("function", "getLine")])

    def test_php5_calltip_call_signature_for_classes(self):
        content, positions = unmark_text(php_markup("""\
            $e = new Exception(<1>'error name', 0);
       """))
        self.assertCalltipIs(markup_text(content, pos=positions[1]), "__construct(string message, int code)\nException constructor")

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
        self.assertCalltipIs(markup_text(content, pos=positions[1]), "array(<list>)\ncreate a PHP array.")
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
                    self::<2>mine();
                    parent::<3>
                }
            }

            class ext_two extends <4>two {
                function __construct($foo) {
                    self::<5>yours();
                    parent::<6>
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
            [("variable", "x"), ("function", "mine"), ("function", "__construct")])
        self.assertCompletionsInclude2(buf, test_positions[4],
            [("class", "one"), ("class", "two")])
        self.assertCompletionsInclude2(buf, test_positions[5],
            [("variable", "y"), ("function", "yours"), ("function", "__construct")])
        self.assertCompletionsInclude2(buf, test_positions[6],
            [("variable", "y"), ("function", "yours"), ("function", "__construct")])

    def test_completion_with_import_inside_import(self):
        test_dir = join(self.test_dir, "test_bug57887_completion_with_multiple_imports")
        test_content, test_positions = unmark_text(php_markup(dedent("""\
            require_once("import_3.php");

            class local_one extends <1>ext_three {
                function __construct($foo) {
                    self::<2>mine();
                    parent::<3>
                }
            }

            class local_two extends <4>ext_four {
                var $local_y;
                function __construct($foo) {
                    self::<5>yours();
                    parent::<6>
                }
            }

            $obj_one = new <7>one();
            $obj_one-><8>xyz;

            $obj_two = new local_two();
            $obj_two-><9>xyz;
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
            [("variable", "x"), ("function", "mine"),
             ("function", "__construct"), ("function", "func_in_three")])
        self.assertCompletionsInclude2(buf, test_positions[4],
            [("class", "one"), ("class", "two"),
             ("class", "ext_three"), ("class", "ext_four"), ])
        self.assertCompletionsInclude2(buf, test_positions[5],
            [("variable", "y"), ("variable", "local_y"), ("function", "yours"),
             ("function", "__construct"), ("function", "func_in_four")])
        self.assertCompletionsInclude2(buf, test_positions[6],
            [("variable", "y"), ("function", "yours"),
             ("function", "__construct"), ("function", "func_in_four")])
        self.assertCompletionsInclude2(buf, test_positions[7],
            [("class", "one"), ("class", "two"),
             ("class", "ext_three"), ("class", "ext_four"),
             ("class", "local_one"), ("class", "local_two"), ])
        self.assertCompletionsInclude2(buf, test_positions[8],
            [("variable", "x"), ("function", "mine"),
             ("function", "__construct"), ])
        self.assertCompletionsInclude2(buf, test_positions[9],
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
            [("function", "foo"), ("variable", "bar")])

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
            [("function", "require"), ("function", "require_once")])

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
                    self::<2>mine();
                    parent::<3>
                }
            }

            class ext_two extends <4>two {
                function __construct($foo) {
                    self::<5>yours();
                    parent::<6>
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
            [("variable", "x"), ("function", "mine"), ("function", "__construct")])
        self.assertCompletionsInclude2(buf, test_positions[4],
            [("class", "one"), ("class", "two")])
        self.assertCompletionsInclude2(buf, test_positions[5],
            [("variable", "y"), ("function", "yours"), ("function", "__construct")])
        self.assertCompletionsInclude2(buf, test_positions[6],
            [("variable", "y"), ("function", "yours"), ("function", "__construct")])

    def test_completion_with_import_inside_import(self):
        test_dir = join(self.test_dir, "test_bug57887_completion_with_multiple_imports")
        test_content, test_positions = unmark_text(php_markup(dedent("""\
            // require_once("import_3.php");

            class local_one extends <1>ext_three {
                function __construct($foo) {
                    self::<2>mine();
                    parent::<3>
                }
            }

            class local_two extends <4>ext_four {
                var $local_y;
                function __construct($foo) {
                    self::<5>yours();
                    parent::<6>
                }
            }

            $obj_one = new <7>one();
            $obj_one-><8>xyz;

            $obj_two = new local_two();
            $obj_two-><9>xyz;
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
            [("variable", "x"), ("function", "mine"),
             ("function", "__construct"), ("function", "func_in_three")])
        self.assertCompletionsInclude2(buf, test_positions[4],
            [("class", "one"), ("class", "two"),
             ("class", "ext_three"), ("class", "ext_four"), ])
        self.assertCompletionsInclude2(buf, test_positions[5],
            [("variable", "y"), ("variable", "local_y"), ("function", "yours"),
             ("function", "__construct"), ("function", "func_in_four")])
        self.assertCompletionsInclude2(buf, test_positions[6],
            [("variable", "y"), ("function", "yours"),
             ("function", "__construct"), ("function", "func_in_four")])
        self.assertCompletionsInclude2(buf, test_positions[7],
            [("class", "one"), ("class", "two"),
             ("class", "ext_three"), ("class", "ext_four"),
             ("class", "local_one"), ("class", "local_two"), ])
        self.assertCompletionsInclude2(buf, test_positions[8],
            [("variable", "x"), ("function", "mine"),
             ("function", "__construct"), ])
        self.assertCompletionsInclude2(buf, test_positions[9],
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
        test_dir = join(self.test_dir, "test_defn")
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
        test_dir = join(self.test_dir, "test_defn")
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
    #    test_dir = join(self.test_dir, "test_defn")
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
                private $x = 1;
                protected $y = "";
                public $z = 0;
                function foo() {
                    $this-><1>xxx == 10;
                    self::<2>x = 1;
                }
            }
            class MySecondScopeClass extends MyScopeClass {
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
       """)))
        # Single base class
        self.assertCompletionsAre(markup_text(content, pos=positions[1]),
            [("function", "foo"),
             ("variable", "x"), ("variable", "y"), ("variable", "z")])
        self.assertCompletionsAre(markup_text(content, pos=positions[2]),
            [("function", "foo"),
             ("variable", "x"), ("variable", "y"), ("variable", "z")])
        # Inheriting class
        self.assertCompletionsAre(markup_text(content, pos=positions[3]),
            [("function", "bar"), ("function", "foo"),
             ("variable", "x2"),
             ("variable", "y"), ("variable", "y2"),
             ("variable", "z"), ("variable", "z2")])
        self.assertCompletionsAre(markup_text(content, pos=positions[4]),
            [("function", "bar"), ("function", "foo"),
             ("variable", "x2"),
             ("variable", "y"), ("variable", "y2"),
             ("variable", "z"), ("variable", "z2")])
        self.assertCompletionsAre(markup_text(content, pos=positions[5]),
            [("function", "foo"),
             ("variable", "y"), ("variable", "z")])
        # Global scope
        self.assertCompletionsAre(markup_text(content, pos=positions[6]),
            [("function", "bar"), ("function", "foo"),
             ("variable", "z"), ("variable", "z2")])



#---- mainline

if __name__ == "__main__":
    unittest.main()


