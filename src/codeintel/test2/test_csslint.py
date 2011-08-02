#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

"""Test some CSS-specific codeintel handling."""

import os
import sys
import re
import random
from os.path import join, dirname, abspath, exists, basename
import glob
import unittest
import logging

from codeintel2.common import *
from codeintel2.util import indent, dedent, banner, markup_text, \
                            unmark_text, CompareNPunctLast
from testlib import TestError, TestSkipped, TestFailed, tag
from citestsupport import CodeIntelTestCase
from codeintel2.css_linter import CSSLinter

log = logging.getLogger("test")

class CSSLintTest(CodeIntelTestCase):
    lang = "CSS"
    test_dir = os.getcwd()
    csslinter = CSSLinter()
    
    langs = ("CSS", "SCSS", "Less")

    def test_expect_good_files(self):
        test_dir = join(self.test_dir, "bits", "css_files")
        print "Test files in path %s" % test_dir
        for path in glob.glob(join(test_dir, "*.css")):
            fd = open(path, 'r')
            code = fd.read().decode("utf-8")
            fd.close()
            print "Test file %s" % basename(path)
            results = self.csslinter.lint(code)
            self.assertEqual([], results, "Failed to parse file %s" % path)

    def test_komodo_skin_files_01(self):
        # Test these under CSS, SCSS, and Less
        skin_dir = join(dirname(dirname(dirname(abspath(__file__)))), "chrome", "komodo", "skin")
        self.assertTrue(os.path.exists(join(skin_dir, "codeintel.css")), skin_dir)
        for path in glob.glob(join(skin_dir, "*.css")):
            fd = open(path, 'r')
            code = fd.read().decode("utf-8")
            fd.close()
            for lang in self.langs:
                #sys.stderr.write("Test file %s\n" % basename(path))
                results = self.csslinter.lint(code, language=lang)
                self.assertEqual([], results, "Failed to parse file %s/%s" % (path, lang))

    def test_jezdez(self):
        path = join(self.test_dir, "bits", "bad_css_files", "jezdez-reset-fonts-grids.css")
        fd = open(path, 'r')
        code = fd.read().decode("utf-8")
        fd.close()
        print "Test file %s" % basename(path)
        results = self.csslinter.lint(code)
        self.assertTrue(len(results) > 0)            
            

    def test_css_charset_selector(self):
        code = dedent("""\
@charset "utf-8";
h1 {
  color: blue;
}
""").decode("utf-8")
        results = self.csslinter.lint(code)
        self.assertEqual(0, len(results))

    # Error tests

    def test_css_charset_stub_01(self):
        code = "@charset "
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        if len(results) >= 1:
            r = results[0]
            self.assertEqual(r.message,
                             "expecting a string after @charset, got ")
            self.assertEqual(r.line_start, None)

    def test_css_charset_stub_02(self):
        code = "@charset moo"
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        if len(results) >= 1:
            r = results[0]
            self.assertEqual(r.message,
                             "expecting a string after @charset, got moo")
            self.assertEqual(r.line_start, 1)
            self.assertEqual(code[r.col_start:r.col_end], "moo")

    def test_css_charset_stub_03(self):
        code = "@charset 'utf-8'"  # missing semi-colon
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        if len(results) >= 1:
            r = results[0]
            self.assertTrue(r.message.startswith("expecting ';'"), r.message)
            self.assertEqual(r.line_start, None)

    def test_css_special_selector_01(self):
        codes = ["#", '.', ':']
        for code in codes:
            results = self.csslinter.lint(code)
            self.assertEqual(1, len(results))
            if len(results) >= 1:
                r = results[0]
                self.assertTrue(r.message.startswith("expecting an identifier after %s" % (code,)), "unexpected message:%s" % r.message)
                self.assertEqual(r.line_start, None)

    def test_css_special_selector_02(self):
        codes = ["#", '.', ':']
        for char in codes:
            code = char + "{}"
            results = self.csslinter.lint(code)
            self.assertEqual(1, len(results))
            if len(results) >= 1:
                r = results[0]
                self.assertTrue(r.message.startswith("expecting an identifier after %s" % (char,)), "unexpected message:%s" % r.message)
                self.assertEqual(code[r.col_start:r.col_end], "{")

    def test_css_special_selector_03(self):
        codes = ["#", '.', ':']
        for char in codes:
            code = "gleep " + char
            results = self.csslinter.lint(code)
            self.assertEqual(1, len(results))
            if len(results) >= 1:
                r = results[0]
                self.assertTrue(r.message.startswith("expecting an identifier after %s" % (char,)), "unexpected message:%s" % r.message)
                self.assertEqual(r.line_start, None)

    def test_css_special_selector_04(self):
        codes = ["#", '.', ':']
        for char in codes:
            code = "gleep " + char + " {"
            results = self.csslinter.lint(code)
            self.assertEqual(1, len(results))
            if len(results) >= 1:
                r = results[0]
                self.assertTrue(r.message.startswith("expecting an identifier after %s" % (char,)), "unexpected message:%s" % r.message)
                self.assertEqual(code[r.col_start:r.col_end], "{", "expected complaint about {, got %s" % r)


    def test_css_special_selector_05(self):
        code = dedent("""\
treechildren::-moz-tree-cell-text(showDetail) {
    background-color: infobackground;
}
""").decode("utf-8")
        results = self.csslinter.lint(code)
        self.assertEqual(0, len(results))

    def test_css_special_selector_06(self):
        # Multiple selectors
        code = dedent("""\
treechildren::-moz-tree-cell-text(showDetail), 
treechildren::-moz-tree-cell-text(showDetail) {
    background-color: infobackground;
}
""").decode("utf-8")
        results = self.csslinter.lint(code)
        self.assertEqual(0, len(results))

    def test_css_special_selector_missing_prop_07(self):
        # Multiple selectors
        code = dedent("""\
treechildren::-moz-tree-cell-text(), {
    background-color: infobackground;
}
""").decode("utf-8")
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("expecting a property name"),
                        r.message)
        self.assertEqual(code.splitlines()[r.line_start - 1][r.col_start:r.col_end], ")")

    def test_css_special_selector_missing_paren_08(self):
        code = dedent("""\
treechildren::-moz-tree-cell-text(showDetail, 
treechildren::-moz-tree-cell-text(showDetail) {
    background-color: infobackground;
}
""").decode("utf-8")
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("expecting ')'"),
                        r.message)
        self.assertEqual(code.splitlines()[r.line_start - 1][r.col_start:r.col_end], "::")


    def test_css_special_selector_missing_selector_09(self):
        code = dedent("""\
treechildren::-moz-tree-cell-text(showDetail),
{
    background-color: infobackground;
}
""").decode("utf-8")
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("expecting a selector"),
                        r.message)
        self.assertEqual(code.splitlines()[r.line_start - 1][r.col_start:r.col_end], "{", str(r))

    def test_css_special_selector_bad_syntax_10(self):
        # Multiple selectors
        code = dedent("""\
treechildren::-moz-tree-cell-text(&) {
    background-color: infobackground;
}
""").decode("utf-8")
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("expecting a property name"),
                        r.message)
        self.assertEqual(code.splitlines()[r.line_start - 1][r.col_start:r.col_end], "&", str(r))

    def test_css_special_selector_missing_rest_11(self):
        # Multiple selectors
        code = dedent("""\
treechildren::-moz-tree-cell-text( {
    background-color: infobackground;
}
""").decode("utf-8")
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("expecting a property name"),
                        r.message)
        self.assertEqual(code.splitlines()[r.line_start - 1][r.col_start:r.col_end], "{", str(r))

    def test_css_no_selector_01(self):
        code = "{ font: red; }"  # missing semi-colon
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        if len(results) >= 1:
            r = results[0]
            self.assertTrue(r.message.startswith("expecting a selector, got "),
                            r.message)
            self.assertEqual(code[r.col_start:r.col_end], "{")

    def test_css_empty(self):
        code = ""
        results = self.csslinter.lint(code)
        self.assertEqual(0, len(results))

    def test_css_no_directive_01(self):
        code = "@"  # missing semi-colon
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        if len(results) >= 1:
            r = results[0]
            self.assertTrue(r.message.startswith("expecting an identifier after @"),
                            r.message)
            self.assertEqual(r.line_start, None)

    def test_css_no_directive_02(self):
        code = "@ charset 'utf8';"  # space not allowed
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        if len(results) >= 1:
            r = results[0]
            self.assertTrue(r.message.startswith("expecting a directive immediately after @"),
                            r.message)
            self.assertEqual(code[r.col_start:r.col_end], " ")

    def test_css_no_directive_cascade(self):
        code = "@ charset ;"  # space not allowed
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        if len(results) >= 1:
            r = results[0]
            self.assertTrue(r.message.startswith("expecting a directive immediately after @"),
                            r.message)
            self.assertEqual(code[r.col_start:r.col_end], " ")

    def test_css_missing_semicolon_01(self):
        code = dedent("""\
body {
  color:red
}
""").decode("utf-8")
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("expecting ';'"),
                        r.message)
        self.assertEqual(code.splitlines()[2][r.col_start:r.col_end], "}")

    def test_css_recover_02(self):
        code = dedent("""\
body {
  color:red
}
@charset "utf-8";
h {
  color: blue;
}
""").decode("utf-8")
        results = self.csslinter.lint(code)
        self.assertEqual(2, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("expecting ';'"),
                        r.message)
        self.assertEqual(code.splitlines()[2][r.col_start:r.col_end], "}")
        r = results[1]
        self.assertTrue(r.message.startswith("@charset allowed only at start of file"),
                        r.message)
        self.assertEqual(code.splitlines()[3][r.col_start:r.col_end], "charset")

    def test_css_charset_too_late(self):
        code = dedent("""\
body {
  color:red;
}
@charset "utf-8";
""").decode("utf-8")
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        if len(results) >= 1:
            r = results[0]
            self.assertTrue(r.message.startswith("@charset allowed only at start of file"),
                            r.message)
            self.assertEqual(code.splitlines()[3][r.col_start:r.col_end], "charset")

    def test_css_import_missing_arg_01(self):
        code = '@import ;'
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("expecting a string or url"),
                        r.message)
        self.assertEqual(code.splitlines()[0][r.col_start:r.col_end], ";")

    def test_css_import_missing_arg_02(self):
        code = '@import 33'
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("expecting a string or url"),
                        r.message)
        self.assertEqual(code.splitlines()[0][r.col_start:r.col_end], "33")

    def test_css_import_missing_arg_03(self):
        code = '@import fish;'
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("expecting a string or url"),
                        r.message)
        self.assertEqual(code.splitlines()[0][r.col_start:r.col_end], "fish")

    def test_css_import_missing_arg_04(self):
        code = '@import'
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("expecting a string or url"),
                        r.message)
        self.assertEqual(r.line_start, None)

    def test_css_import_good_url_01(self):
        code = '@import url(http://wawa.moose/);'
        results = self.csslinter.lint(code)
        if results:
            self.assertEqual(0, len(results), results[0])
        self.assertEqual(0, len(results))

    def test_css_import_good_medialist_01(self):
        code = '@import url(http://example.com/) print;'
        results = self.csslinter.lint(code)
        if results:
            self.assertEqual(0, len(results), results[0])
        self.assertEqual(0, len(results))

    def test_css_import_bad_url_01(self):
        code = '@import url( ;'
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("expecting a quoted URL"),
                        r.message)
        self.assertEqual(code.splitlines()[0][r.col_start:r.col_end], ";")

    def test_css_import_bad_url_02(self):
        code = '@import url(http://example.com/) print'
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertEqual(r.line_start, None, r)

    def test_css_import_bad_position_03(self):
        code = dedent("""\
body {
  color:red;
}
@import url(http://example.com/) print;
""").decode("utf-8")
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("@import allowed only near start of file"),
                        r.message)
        self.assertEqual(code.splitlines()[3][r.col_start:r.col_end], "import")

    def test_css_import_bad_media_01(self):
        code = '@media'
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("expecting an identifier for a media list"),
                        r.message)
        self.assertEqual(r.line_start, None, r.message)

    def test_css_import_bad_media_02(self):
        code = '@media ;'
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("expecting an identifier for a media list"),
                        r.message)
        self.assertEqual(code.splitlines()[0][r.col_start:r.col_end], ";")

    def test_css_import_bad_media_03(self):
        code = '@media @walrus'
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("expecting an identifier for a media list"),
                        r.message)
        self.assertEqual(code.splitlines()[0][r.col_start:r.col_end], "@")

    def test_css_import_bad_media_04(self):
        code = '@media walrus'
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("expecting '{'"),
                        r.message)
        self.assertEqual(r.line_start, None, r.message)

    def test_css_import_bad_media_05(self):
        code = '@media walrus chomps'
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("expecting '{'"),
                        r.message)
        self.assertEqual(code.splitlines()[0][r.col_start:r.col_end], "chomps")

    def test_css_import_bad_media_06(self):
        code = '@media walrus "chomps"'
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("expecting '{'"),
                        r.message)
        self.assertEqual(code.splitlines()[0][r.col_start:r.col_end], '"chomps"')

    def test_css_import_bad_media_07(self): #XXX:Finish
        code = '@media walrus {'
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("expecting '}'"),
                        r.message)
        self.assertEqual(r.line_start, None, r.message)

    def test_css_import_bad_media_08(self): #XXX:Finish
        code = '@media walrus { "chomps"'
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("expecting a property name"),
                        r.message)
        self.assertEqual(code.splitlines()[0][r.col_start:r.col_end], '"chomps"')

    def test_css_import_bad_media_09(self):
        code = '@media abc,'
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("expecting an identifier"),
                        r.message)
        self.assertEqual(r.line_start, None, r.message)

    def test_css_import_bad_media_10(self):
        code = '@media abc, {'
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("expecting an identifier"),
                        r.message)
        self.assertEqual(code.splitlines()[0][r.col_start:r.col_end], '{')

    def test_css_import_bad_media_11(self):
        code = '@media abc, 765 {'
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("expecting an identifier"),
                        r.message)
        self.assertEqual(code.splitlines()[0][r.col_start:r.col_end], '765')

    def test_css_import_bad_media_12(self):
        code = '@media abc, { color: red; }'
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("expecting an identifier"),
                        r.message)
        self.assertEqual(code.splitlines()[0][r.col_start:r.col_end], '{')


    def test_css_good_property_function(self):
        code = dedent("""\
div.flip {
    background-image: -moz-linear-gradient(rgba(0, 255, 0, 0.05), rgba(0, 255, 0, 0.01));
}
""").decode("utf-8")
        results = self.csslinter.lint(code)
        if results:
            self.assertEqual(0, len(results), results[0])
        self.assertEqual(0, len(results))

    def test_css_import_good_page_01(self):
        code = '@page { background: red; }'
        results = self.csslinter.lint(code)
        if results:
            self.assertEqual(0, len(results), results[0])
        self.assertEqual(0, len(results))

    def test_css_import_good_page_02(self):
        code = '@page :fish { background: red; }'
        results = self.csslinter.lint(code)
        if results:
            self.assertEqual(0, len(results), results[0])
        self.assertEqual(0, len(results))

    def test_css_import_bad_page_01(self):
        code = '@page : { background: red; }'
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("expecting an identifier"),
                        r.message)
        self.assertEqual(code.splitlines()[0][r.col_start:r.col_end], '{')

    def test_css_import_bad_page_02(self):
        code = '@page woop { background: red; }'
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("expecting '{'"),
                        r.message)
        self.assertEqual(code.splitlines()[0][r.col_start:r.col_end], 'woop')

    def test_css_import_bad_page_03(self):
        code = '@page :: { background: red; }'
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("expecting '{'"),
                        r.message)
        self.assertEqual(code.splitlines()[0][r.col_start:r.col_end], '::')

    def test_css_import_bad_page_04(self):
        code = '@page { background: red;'
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("expecting '}'"),
                        r.message)
        self.assertEqual(r.line_start, None, r.message)

    def test_css_ruleset_bad_04(self):
        code = 'h1 { background'
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("expecting ':'"),
                        r.message)
        self.assertEqual(r.line_start, None, r.message)

    def test_css_missing_classname_01(self):
        code = '. { }'
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("expecting an identifier"),
                        r.message)
        self.assertEqual(code.splitlines()[0][r.col_start:r.col_end], '{')

    def test_css_ruleset_bad_property_01(self):
        code = 'h1 { background: '
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("expecting a value"),
                        r.message)
        self.assertEqual(r.line_start, None, r.message)

    def test_css_ruleset_bad_property_02(self):
        code = 'h1 { background: }'
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("expecting a value"),
                        r.message)
        self.assertEqual(code.splitlines()[0][r.col_start:r.col_end], '}')

    def test_css_ruleset_bad_property_03(self):
        code = 'h1 { background }'
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("expecting ':'"),
                        r.message)
        self.assertEqual(code.splitlines()[0][r.col_start:r.col_end], '}')

    def test_css_ruleset_bad_property_04(self):
        code = 'h1 { border-width: -@shlub; }'
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("expecting a number"),
                        r.message)
        self.assertEqual(code.splitlines()[0][r.col_start:r.col_end], '@')

    def test_css_ruleset_bad_property_05(self):
        code = 'h1 { border-width: mssyntax:; }'
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("expecting an identifier"),
                        r.message)
        self.assertEqual(code.splitlines()[0][r.col_start:r.col_end], ';')

    def test_css_ruleset_bad_property_fn_06(self):
        code = 'h1 { border-width: f(10'
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("expecting ')'"),
                        r.message)
        self.assertEqual(r.line_start, None, r.message)

    def test_css_ruleset_bad_property_fn_07(self):
        code = 'h1 { border-width: f(10 }'
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("expecting ')'"),
                        r.message)
        self.assertEqual(code.splitlines()[0][r.col_start:r.col_end], '}')

    def test_css_ruleset_bad_property_fn_08(self):
        code = 'h1 { border-width: f(10 ; }'
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("expecting ')'"),
                        r.message)
        self.assertEqual(code.splitlines()[0][r.col_start:r.col_end], ';')

    def test_css_ruleset_bad_property_09(self):
        code = 'h1 { border-width: f(10) !'
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("expecting '!important'"),
                        r.message)
        self.assertEqual(r.line_start, None, r.message)

    def test_css_ruleset_bad_property_10(self):
        code = 'h1 { border-width: f(10) !;'
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("expecting '!important'"),
                        r.message)
        self.assertEqual(code.splitlines()[0][r.col_start:r.col_end], ';')

    def test_css_ruleset_bad_property_11(self):
        code = 'h1 {'
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("expecting '}'"),
                        r.message)
        self.assertEqual(r.line_start, None, r.message)

    def test_css_ruleset_bad_property_12(self):
        code = 'h1 {;'
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("expecting a property name"),
                        r.message)
        self.assertEqual(code.splitlines()[0][r.col_start:r.col_end], ';')

    def test_css_depends_nested_blocks_01(self):
        code = dedent("""\
body {
  h1 {
    color: blue;
  }
}
""").decode("utf-8")
        results = self.csslinter.lint(code)
        self.assertEqual(2, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("expecting ':'"),
                        r.message)
        self.assertEqual(code.splitlines()[1][r.col_start:r.col_end], '{')
        r = results[1]
        self.assertTrue(r.message.startswith("expecting a value"),
                        r.message)
        self.assertEqual(code.splitlines()[2][r.col_start:r.col_end], 'color')

    def test_css_bad_attribute_01(self):
        code = 'h1['
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("expecting an identifier"),
                        r.message)
        self.assertEqual(r.line_start, None, r.message)

    def test_css_bad_attribute_02(self):
        code = 'h1[='
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("expecting an identifier"),
                        r.message)
        self.assertEqual(code.splitlines()[0][r.col_start:r.col_end], '=')

    def test_css_bad_attribute_03(self):
        code = 'h1[ ='
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("expecting an identifier"),
                        r.message)
        self.assertEqual(code.splitlines()[0][r.col_start:r.col_end], '=')

    def test_css_bad_stringeol_01(self):
        code = 'h1[x = "flip\n'
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("missing string close-quote"),
                        r.message)
        self.assertEqual(code.splitlines()[0][r.col_start:r.col_end], '"flip')

    def test_css_bad_stringeol_02(self):
        code = 'h1[x = "flip' # ends at eof
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("missing string close-quote"),
                        r.message)
        self.assertEqual(code.splitlines()[0][r.col_start:r.col_end], '"flip')

    def test_css_bad_stringeol_03(self):
        code = 'h1[x = \'flip' # ends at eof
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("missing string close-quote"),
                        r.message)
        self.assertEqual(code.splitlines()[0][r.col_start:r.col_end], '\'flip')

    def test_css_bad_stringeol_04(self):
        code = '@charset "utf-8' # ends at eof
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("missing string close-quote"),
                        r.message)
        self.assertEqual(code.splitlines()[0][r.col_start:r.col_end], '"utf-8')

    def test_css_bad_stringeol_05(self):
        code = '@charset "utf-8\n' # ends at eof
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("missing string close-quote"),
                        r.message)
        self.assertEqual(code.splitlines()[0][r.col_start:r.col_end], '"utf-8')

    def test_css_bad_stringeol_06(self):
        code = '@import "utf-8' # ends at eof
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("missing string close-quote"),
                        r.message)
        self.assertEqual(code.splitlines()[0][r.col_start:r.col_end], '"utf-8')

    def test_css_bad_stringeol_07(self):
        code = '@import "utf-8\n' # ends at eof
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("missing string close-quote"),
                        r.message)
        self.assertEqual(code.splitlines()[0][r.col_start:r.col_end], '"utf-8')

    def test_css_bad_stringeol_08(self):
        code = 'body { font: "Verdana'
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("missing string close-quote"),
                        r.message)
        self.assertEqual(code.splitlines()[0][r.col_start:r.col_end], '"Verdana')

    def test_css_bad_stringeol_09(self):
        code = 'body { font: "Verdana\n'
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("missing string close-quote"),
                        r.message)
        self.assertEqual(code.splitlines()[0][r.col_start:r.col_end], '"Verdana')

    def test_css_bad_termid_01(self):
        code = 'body { font: Microsoft.'
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("expecting an identifier"),
                        r.message)
        self.assertEqual(r.line_start, None, r.message)

    def test_css_bad_termid_02(self):
        code = 'body { font: Microsoft. ;}'
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("expecting an identifier"),
                        r.message)
        self.assertEqual(code.splitlines()[0][r.col_start:r.col_end], ';')

    def test_css_ms_hack_property_name_01(self):
        code = '.yui-gb .yui-u{*margin-left:1.9%;*width:31.9%;}'
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("Use of non-standard property-name '*margin-left'"),
                        r.message)
        self.assertEqual(code.splitlines()[0][r.col_start:r.col_end], '*margin-left')
        self.assertEqual(r.status, 0, "%s:%r" % (r.message, r.status))

    def test_css_ms_hack_property_name_botched_02(self):
        code = '.yui-gb .yui-u{* margin-left:1.9%;*    width:31.9%;}'
        results = self.csslinter.lint(code)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("expecting ':',"),
                        r.message)
        self.assertEqual(code.splitlines()[0][r.col_start:r.col_end], 'margin-left')
        
    def test_css_quoted_urls_01(self):
        code = dedent("""\
.browser-toolbar {
  list-style-image: url("chrome://komodo/skin/images/browser_buttons.png");
}
""").decode("utf-8")
        results = self.csslinter.lint(code)
        self.assertEqual(0, len(results))
        
    def test_css_attr_no_value(self):
        code = dedent("""\
.file-status-icons[file_scc_status] {
  /* Since we move the scc status icon to the left of the file image, we have to
     add padding for it in the parenting hbox. */
  padding-left: 4px;
}
""").decode("utf-8")
        results = self.csslinter.lint(code)
        self.assertEqual(0, len(results))

    def test_css_not_psuedo_class(self):
        code = dedent("""\
.file-status-icon:not([file_scc_status]):not([file_status]),
.file-scc-status-extra-icon:not([file_scc_status_extra]) {
  /* Collapse scc status images that are not showing anything. */
  display: none;
}
""").decode("utf-8")
        results = self.csslinter.lint(code)
        if results:
            r = results[0]
            self.assertTrue(r.message.startswith("blif"),
                            r.message)
            self.assertEqual(code.splitlines()[0][r.col_start:r.col_end], 'flib')
        self.assertEqual(0, len(results))

    _nested_block_code_01 = dedent("""\
body.abc {
    ul.def {
        color: red;
        background: white;
        li.ghi {
            background-color: flip;
        }
        
    }
}
""").decode("utf-8")
    def test_css_nested_block_01(self):
        # Fail: it's plain CSS
        code = self._nested_block_code_01
        results = self.csslinter.lint(code, language="CSS")
        self.assertEqual(2, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("expecting ':'"),
                        r.message)
        self.assertEqual(code.splitlines()[1][r.col_start:r.col_end], '.', r)
        r = results[1]
        # This tests a recovery algorithm, so it's more volatile.
        self.assertTrue(r.message.startswith("expecting ':'"),
                        r.message)
        cdo = code.splitlines()[4][r.col_start:r.col_end]
        self.assertEqual(code.splitlines()[4][r.col_start:r.col_end], '.', r)

    def test_css_nested_block_02(self):
        # Allow, it's Less
        code = self._nested_block_code_01
        results = self.csslinter.lint(code, language="Less")
        self.assertEqual(0, len(results))
        if results:
            r = results[0]
            self.assertTrue(r.message.startswith("expecting ':'"),
                            r.message)
            self.assertEqual(code.splitlines()[1][r.col_start:r.col_end], '.', r)
            r = results[1]
            # This tests a recovery algorithm, so it's more volatile.
            self.assertTrue(r.message.startswith("expecting ':'"),
                            r.message)
            cdo = code.splitlines()[4][r.col_start:r.col_end]
            self.assertEqual(code.splitlines()[4][r.col_start:r.col_end], '.', r)

    def test_css_bad_random_input_01(self):
        import string, random
        chars = string.letters + string.digits\
            + string.punctuation + string.whitespace
        prog = []
        for i in range(1000):
            prog.append(random.choice(chars))
        code = "".join(prog)
        #print code
        #f = open("/tmp/code.css", 'w')
        #f.write(code)
        #f.close()
        for lang in self.langs:
            results = self.csslinter.lint(code, language=lang)
            #print "\n".join([str(x) for x in results])
            self.assertTrue(len(results) > 0, "this code passed!:<<%s/%s>>" % (lang, code,))
   
    def test_css_less_atsign_assignment(self):
        code = dedent("""\
@color: #4D926F;

#header {
  color: @color;
}
h2 {
  color: @color;
}
""").decode("utf-8")
        results = self.csslinter.lint(code, language="Less")
        if results:
            r = results[0]
            self.assertTrue(r.message.startswith("blif"),
                            r)
            self.assertEqual(code.splitlines()[0][r.col_start:r.col_end], 'flib')
        self.assertEqual(0, len(results))
        
        for lang in ("CSS", "SCSS"):
            results = self.csslinter.lint(code, language=lang)
            self.assertTrue(len(results) > 0, "Expecting at least one CSS error")
            r = results[0]
            self.assertTrue(r.message.startswith("expecting a directive after @"),
                            r)
            self.assertEqual(code.splitlines()[0][r.col_start:r.col_end], 'color', r)
            
    def test_css_scss_nested_properties(self):
        code = dedent("""\
li {
  font: {
    family: serif;
    weight: bold;
    size: 1.2em;
  }
}
""").decode("utf-8")
        results = self.csslinter.lint(code, language="SCSS")
        if results:
            r = results[0]
            self.assertTrue(r.message.startswith("blif"),
                            r)
            self.assertEqual(code.splitlines()[0][r.col_start:r.col_end], 'flib')
        self.assertEqual(0, len(results))
        for lang in ("CSS", "Less"):
            results = self.csslinter.lint(code, language=lang)
            self.assertTrue(len(results) > 0, "Expecting at least one error for lang %s" % (lang,))
            r = results[0]
            self.assertTrue(r.message.startswith("expecting a value"),
                            r)
            self.assertEqual(code.splitlines()[1][r.col_start:r.col_end], '{', r)
        

    def test_css_less_operators(self):
        code = dedent("""\ 
        @the-border: 1px;
@base-color: #111;
@red:        #842210;

#header {
  color: @base-color * 3;
  border-left: @the-border;
  border-right: @the-border * 2;
}
#footer { 
  color: @base-color + #003300;
  border-color: desaturate(@red, 10%);
}
""").decode("utf-8")
        results = self.csslinter.lint(code, language="Less")
        if results:
            r = results[0]
            self.assertTrue(r.message.startswith("blif"),
                            r)
            self.assertEqual(code.splitlines()[0][r.col_start:r.col_end], 'flib')
        self.assertEqual(0, len(results))

    def test_css_less_mixins_01(self):
        code = dedent("""\ 
.rounded-corners (@radius: 5px) {
  border-radius: @radius;
  -webkit-border-radius: @radius;
  -moz-border-radius: @radius;
}

#header {
  .rounded-corners;
}
#footer {
  .rounded-corners(10px);
}
""").decode("utf-8")
        results = self.csslinter.lint(code, language="Less")
        if results:
            r = results[0]
            self.assertTrue(r.message.startswith("blif"),
                            r)
            self.assertEqual(code.splitlines()[0][r.col_start:r.col_end], 'flib')
        self.assertEqual(0, len(results))

    def _x_test_css_stuff(self):
        code = dedent("""\
@import url(http://example.com/) print

h1[ =
""")
        results = self.csslinter.lint(code)
        self.assertTrue(len(results) > 0)
        r = results[0]
        self.assertTrue(r.message.startswith("zobs"),
                        r)
        self.assertEqual(code.splitlines()[0][r.col_start:r.col_end], ';')

    def test_css_bad_noted_input_01(self):
        code = dedent("""\ 
Ot/ {sa @(-"ZqMn3b	Of1f<$0
gL0K.2n9ux@@_co:
.{(>VK{
""")
        results = self.csslinter.lint(code)
        self.assertTrue(len(results) > 0)
