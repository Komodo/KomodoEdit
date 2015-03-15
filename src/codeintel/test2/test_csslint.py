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

    def _check_zero_results_show_error(self, code, language="CSS"):
        results = self.csslinter.lint(code, language)
        if results:
            # Show the result that triggered the failure
            self.assertEqual(0, len(results), results[0])
        self.assertEqual(0, len(results))
    
    def _check_one_result_check_error_on_line(self, code, startswith, expected, language="CSS"):
        results = self.csslinter.lint(code, language)
        self.assertEqual(1, len(results), "expected at least one error, got none")
        r = results[0]
        self.assertTrue(r.message.startswith(startswith), r.message)
        self.assertEqual(code.splitlines()[r.line_start - 1][r.col_start:r.col_end], expected)
                    
    def _check_one_result_check_error_at_eof(self, code, startswith, language="CSS"):
        results = self.csslinter.lint(code, language)
        self.assertEqual(1, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith(startswith), r)
        self.assertEqual(r.line_start, None, r)
        
    def _check_some_errors_on_line(self, code, startswith, expected, lineNo=0, language="CSS"):
        results = self.csslinter.lint(code, language)
        self.assertTrue(len(results) > 0)
        r = results[0]
        self.assertTrue(r.message.startswith(startswith),
                        r.message)
        self.assertEqual(code.splitlines()[r.line_start - 1][r.col_start:r.col_end], expected)
                    
    def test_expect_good_files(self):
        test_dir = join(self.test_dir, "bits", "css_files")
        print "Test files in path %s" % test_dir
        for path in glob.glob(join(test_dir, "*.css")):
            fd = open(path, 'r')
            code = fd.read().decode("utf-8")
            fd.close()
            #print "Test file %s" % basename(path)
            results = self.csslinter.lint(code)
            self.assertEqual([], results, "Failed to parse file %s" % path)
         
    _test_dir = abspath(__file__)
    # Running these tests via bk test gives strange results for abspath,
    # so manually adjust
    _m = re.compile(r'(.*)src[/\\]codeintel[/\\](src[/\\](?:codeintel|modules))(.*)').match(_test_dir)
    if _m:
        _test_dir = ''.join(_m.groups())
    _ko_src_dir = dirname(dirname(dirname(_test_dir)))
    _skin_dir = join(_ko_src_dir, "chrome", "komodo", "skin")
    _modules_dir = join(_ko_src_dir, "modules")
    _skipSkinFiles = [
        # Fails to parse @keyframes directives.
        join(_skin_dir, "komodo.p.css"),
    ]
    def _walk_skin_files(self, data, dirname, fnames):
        for fname in fnames:
            if fname.endswith(".css"):
                fpath = join(dirname, fname)
                if fpath in self._skipSkinFiles:
                    continue
                fd = open(fpath, 'r')
                code = fd.read().decode("utf-8")
                fd.close()
                for lang in self.langs:
                    #sys.stderr.write("Test file %s\n" % basename(fpath))
                    results = self.csslinter.lint(code, language=lang)
                    self.assertEqual([], results, "Failed to parse file %s (%s), results: %s" % (fpath, lang, [str(x) for x in results]))

    def test_komodo_skin_files_01(self):
        # Test these under CSS, SCSS, and Less
        self.assertTrue(os.path.exists(join(self._skin_dir, "codeintel.p.css")), "%s: missing codeintel.p.css" % self._skin_dir)
        os.path.walk(self._skin_dir, self._walk_skin_files, None)

    def test_komodo_skin_files_02(self):
        os.path.walk(self._modules_dir, self._walk_skin_files, None)
        
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
        self._check_zero_results_show_error(code)

    def test_css_charset_stub_01(self):
        code = "@charset "
        self._check_one_result_check_error_at_eof(code, "expecting a string after @charset")

    def test_css_charset_stub_02(self):
        code = "@charset moo"
        self._check_one_result_check_error_on_line(code, "expecting a string after @charset", 'moo')

    def test_css_charset_stub_03(self):
        code = "@charset 'utf-8'"  # missing semi-colon
        self._check_one_result_check_error_at_eof(code, "expecting ';'")

    def test_css_special_selector_01(self):
        codes = ["#", '.', ':']
        for code in codes:
            self._check_one_result_check_error_at_eof(code, "expecting an identifier after %s" % (code,))

    def test_css_special_selector_02(self):
        codes = ["#", '.', ':']
        for char in codes:
            code = char + "{}"
            self._check_one_result_check_error_on_line(code, "expecting an identifier after %s" % (char,), '{')

    def test_css_special_selector_03(self):
        codes = ["#", '.', ':']
        for char in codes:
            code = "gleep " + char
            self._check_one_result_check_error_at_eof(code, "expecting an identifier after %s" % (char,))

    def test_css_special_selector_04(self):
        codes = ["#", '.', ':']
        for char in codes:
            code = "gleep " + char + " {"
            self._check_one_result_check_error_on_line(code, "expecting an identifier after %s" % (char,), '{')

    def test_css_special_selector_05(self):
        code = dedent("""\
treechildren::-moz-tree-cell-text(showDetail) {
    background-color: infobackground;
}
""").decode("utf-8")
        self._check_zero_results_show_error(code)

    def test_css_special_selector_06(self):
        # Multiple selectors
        code = dedent("""\
treechildren::-moz-tree-cell-text(showDetail), 
treechildren::-moz-tree-cell-text(showDetail) {
    background-color: infobackground;
}
""").decode("utf-8")
        self._check_zero_results_show_error(code)

    def test_css_special_selector_missing_prop_07(self):
        # Multiple selectors
        code = dedent("""\
treechildren::-moz-tree-cell-text(), {
    background-color: infobackground;
}
""").decode("utf-8")
        self._check_one_result_check_error_on_line(code, "expecting a property name", ')')

    def test_css_special_selector_missing_paren_08(self):
        code = dedent("""\
treechildren::-moz-tree-cell-text(showDetail, 
treechildren::-moz-tree-cell-text(showDetail) {
    background-color: infobackground;
}
""").decode("utf-8")
        self._check_one_result_check_error_on_line(code, "expecting ')'", '::')

    def test_css_special_selector_missing_selector_09(self):
        code = dedent("""\
treechildren::-moz-tree-cell-text(showDetail),
{
    background-color: infobackground;
}
""").decode("utf-8")
        self._check_one_result_check_error_on_line(code, "expecting a selector", '{')

    def test_css_special_selector_bad_syntax_10(self):
        # Multiple selectors
        code = dedent("""\
treechildren::-moz-tree-cell-text(&) {
    background-color: infobackground;
}
""").decode("utf-8")
        self._check_one_result_check_error_on_line(code, "expecting a property name", '&')

    def test_css_special_selector_missing_rest_11(self):
        # Multiple selectors
        code = dedent("""\
treechildren::-moz-tree-cell-text( {
    background-color: infobackground;
}
""").decode("utf-8")
        self._check_one_result_check_error_on_line(code, "expecting a property name", '{')

    def test_css_no_selector_01(self):
        code = dedent("""\
stib + 1xya { /* bad name */
  margin: 3px
}
toolbarbutton#stb_update { /* verify the linter recovered */
  width: 10
}
""")
        self._check_one_result_check_error_on_line(code, "expecting a selector, got", '1')

    def test_css_no_selector_02(self):
        code = dedent("""\
stib + { /* no name */
  margin: 3px
}
toolbarbutton#stb_update { /* verify the linter recovered */
  width: 10
}
""")
        self._check_one_result_check_error_on_line(code, "expecting a selector, got", '{')

    def test_css_missing_second_selector(self):
        code = "@charset moo"
        self._check_one_result_check_error_on_line(code, "expecting a string after @charset", 'moo')


    def test_css_tilde_selector_01(self):
        code = dedent("""\
gortz[zoom ~= "toolbar"] {
    margin: 3px;
}
""")
        self._check_zero_results_show_error(code)

    def test_css_empty(self):
        code = ""
        self._check_zero_results_show_error(code)

    def test_css_no_directive_01(self):
        code = "@"  # missing semi-colon
        self._check_one_result_check_error_at_eof(code, "expecting an identifier after @")

    def test_css_no_directive_02(self):
        code = "@ charset 'utf8';"  # space not allowed
        self._check_one_result_check_error_on_line(code, "expecting a directive immediately after @", ' ')

    def test_css_no_directive_cascade(self):
        code = "@ charset ;"  # space not allowed
        self._check_one_result_check_error_on_line(code, "expecting a directive immediately after @", ' ')

    def test_css_missing_semicolon_01(self):
        code = dedent("""\
body {
  color:red
}
""").decode("utf-8")
        self._check_zero_results_show_error(code)

    def test_css_recover_02(self):
        code = dedent("""\
body {
  color:
}
@charset "utf-8";
h {
  color: blue;
}
""").decode("utf-8")
        results = self.csslinter.lint(code)
        self.assertEqual(2, len(results))
        r = results[0]
        self.assertTrue(r.message.startswith("expecting a value"),
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
        self._check_one_result_check_error_on_line(code, "@charset allowed only at start of file", 'charset')

    def test_css_import_missing_arg_01(self):
        code = '@import ;'
        self._check_one_result_check_error_on_line(code, "expecting a string or url", ';')

    def test_css_import_missing_arg_02(self):
        code = '@import 33'
        self._check_one_result_check_error_on_line(code, "expecting a string or url", '33')
        
    def test_css_import_missing_arg_03(self):
        code = '@import fish;'
        self._check_one_result_check_error_on_line(code, "expecting a string or url", 'fish')

    def test_css_import_missing_arg_04(self):
        code = '@import'
        self._check_one_result_check_error_at_eof(code, "expecting a string or url")

    def test_css_import_good_url_01(self):
        code = '@import url(http://wawa.moose/);'
        self._check_zero_results_show_error(code)

    def test_css_import_good_url_02(self):
        code = '@import url(http://example.com/) print;'
        self._check_zero_results_show_error(code)

    def test_css_import_bad_url_01(self):
        code = '@import url( ;'
        self._check_one_result_check_error_on_line(code, "expecting a quoted URL", ';')

    def test_css_import_bad_url_02(self):
        code = '@import url(http://example.com/) print'
        self._check_one_result_check_error_at_eof(code, "expecting ';'")

    def test_css_import_bad_position_03(self):
        code = dedent("""\
body {
  color:red;
}
@import url(http://example.com/) print;
""").decode("utf-8")
        self._check_one_result_check_error_on_line(code, "@import allowed only near start of file", 'import')
        
    def test_css_media_good_basic_01(self):
        code = dedent("""\
@media screen {
  body {
    padding: 6px;
  }
}
""").decode("utf-8")
        self._check_zero_results_show_error(code)

    def test_css_media_bad_missing_second_close_brace(self):
        code = dedent("""\
        @media screen {
  body {
    padding: 6px;
  }
""").decode("utf-8")
        self._check_one_result_check_error_at_eof(code, "expecting '}'")

    _media_list_error_1 = "expecting an identifier or a parenthesized expression"
    def test_css_media_bad_01(self):
        code = '@media'
        self._check_one_result_check_error_at_eof(code, self._media_list_error_1)

    def test_css_media_bad_02(self):
        code = '@media ;'
        self._check_one_result_check_error_on_line(code, self._media_list_error_1, ';')

    def test_css_media_bad_03(self):
        code = '@media @walrus'
        self._check_one_result_check_error_on_line(code, self._media_list_error_1, '@')

    def test_css_media_bad_04(self):
        code = '@media walrus'
        self._check_one_result_check_error_at_eof(code, "expecting '{'")

    def test_css_media_bad_05(self):
        code = '@media walrus chomps'
        self._check_one_result_check_error_on_line(code, "expecting '{'", 'chomps')

    def test_css_media_bad_06(self):
        code = '@media walrus "chomps"'
        self._check_one_result_check_error_on_line(code, "expecting '{'", '"chomps"')

    def test_css_media_bad_07(self):
        code = '@media walrus {'
        self._check_one_result_check_error_at_eof(code, "expecting '}'")

    def test_css_media_bad_08(self):
        code = '@media walrus { "chomps"'
        self._check_one_result_check_error_on_line(code, "expecting a selector", '"chomps"')

    def test_css_media_bad_09(self):
        code = '@media abc,'
        self._check_one_result_check_error_at_eof(code, "expecting an identifier")

    def test_css_media_bad_10(self):
        code = '@media abc, {'
        self._check_one_result_check_error_on_line(code, "expecting an identifier", '{')

    def test_css_media_bad_11(self):
        code = '@media abc, 765 {'
        self._check_one_result_check_error_on_line(code, "expecting an identifier", '765')
        
    def test_css_media_bad_12(self):
        code = '@media abc, { color: red; }'
        self._check_one_result_check_error_on_line(code, "expecting an identifier", '{')

    def test_css_media_bad_13(self):
        code = '@media abc, "not a string" { color: red; }'
        self._check_one_result_check_error_on_line(code, "expecting an identifier", '"not a string"')

    def test_css_media_mediaqueries_bad_01(self):
        code = '@media only stuff extraIdentifier { color: red; }'
        self._check_one_result_check_error_on_line(code, "expecting '{'", 'extraIdentifier')

    def test_css_media_mediaqueries_bad_01(self):
        code = '@media only stuff mediaqueries_bad_01 { color: red; }'
        self._check_one_result_check_error_on_line(code, "expecting '{'", 'mediaqueries_bad_01')

    def test_css_media_mediaqueries_bad_02(self):
        code = '@media onlyx stuff mediaqueries_bad_02 { color: red; }'
        self._check_one_result_check_error_on_line(code, "expecting '{'", 'stuff')

    def test_css_media_mediaqueries_bad_03(self):
        code = '@media not stuff mediaqueries_bad_03 { color: red; }'
        self._check_one_result_check_error_on_line(code, "expecting '{'", 'mediaqueries_bad_03')

    def test_css_media_mediaqueries_bad_04(self):
        code = '@media media_type1 and mediaqueries_bad_04 { color: red; }'
        self._check_one_result_check_error_on_line(code, "expecting '('", 'mediaqueries_bad_04')

    def test_css_media_mediaqueries_bad_05(self):
        # Should be an identifier
        code = '@media media_type1 and ( "mediaqueries_bad_05") { p { color: red } }'
        self._check_one_result_check_error_on_line(code, "expecting an identifier", '"mediaqueries_bad_05"')

    def test_css_media_mediaqueries_bad_06(self):
        # Multiple terms in media_expression
        code = '@media media_type1 and ( ident mediaqueries_bad_06) { p { color: red } }'
        self._check_one_result_check_error_on_line(code, "expecting ':' or ')'", 'mediaqueries_bad_06')

    def test_css_media_mediaqueries_bad_07(self):
        # Multiple terms in media_expression
        code = '@media media_type1 and ( ident : ) { p { color: red } }'
        self._check_one_result_check_error_on_line(code, "expecting a value", ')')

    def test_css_media_mediaqueries_bad_08(self):
        # Multiple terms in media_expression
        code = '@media media_type1 and ( ident : 3 ) and { p { color: red } }'
        self._check_one_result_check_error_on_line(code, "expecting '('", '{')

    def test_css_media_mediaqueries_bad_09(self):
        # Multiple terms in media_expression
        code = '@media media_type1 and ( ident : 3 ), { p { color: red } }'
        self._check_one_result_check_error_on_line(code, "expecting an identifier or a parenthesized expression", '{')

    def test_css_media_good_unrecognized_tag(self):
        code = dedent("""\
        @media screen {
  scintilla > panel[anonid="autocompletepopup"] {
    -moz-appearance: -moz-win-borderless-glass;
    padding: 6px;
  }
}
""").decode("utf-8")
        self._check_zero_results_show_error(code)

    def test_css_good_property_function(self):
        code = dedent("""\
div.flip {
    background-image: -moz-linear-gradient(rgba(0, 255, 0, 0.05), rgba(0, 255, 0, 0.01));
}
""").decode("utf-8")
        self._check_zero_results_show_error(code)

    def test_css_good_function_with_equal_val(self):
        code = dedent("""\
b {
    filter: alpha(opacity=10);
}
""").decode("utf-8")
        self._check_zero_results_show_error(code)
        
    def test_css_attr_after_star_01(self):
        code = dedent("""\
*[dub] {
  margin:44;
}
""").decode("utf-8")
        for lang in self.langs:
            self._check_zero_results_show_error(code, language=lang)
        
    def test_css_namespace_selector_01(self):
        code = dedent("""\
xul|textbox[invalid="true"] .textbox-input-box
{
  background-color: #FC8D8D;
}
""").decode("utf-8")
        for lang in self.langs:
            self._check_zero_results_show_error(code, language=lang)

    def test_css_preceding_sibling_selector_01(self):
        code = dedent("""\
a ~ b
{
  background-color: #FC8D8D;
}
""").decode("utf-8")
        for lang in self.langs:
            self._check_zero_results_show_error(code, language=lang)

    def test_css_import_good_page_01(self):
        code = '@page { background: red; }'
        self._check_zero_results_show_error(code)

    def test_css_import_good_page_02(self):
        code = '@page :fish { background: red; }'
        self._check_zero_results_show_error(code)

    def test_css_import_bad_page_01(self):
        code = '@page : { background: red; }'
        self._check_one_result_check_error_on_line(code, "expecting an identifier", '{')

    def test_css_import_bad_page_02(self):
        code = '@page woop { background: red; }'
        self._check_one_result_check_error_on_line(code, "expecting '{'", 'woop')

    def test_css_import_bad_page_03(self):
        code = '@page :: { background: red; }'
        self._check_one_result_check_error_on_line(code, "expecting '{'", '::')

    def test_css_import_bad_page_04(self):
        code = '@page { background: red;'
        self._check_one_result_check_error_at_eof(code, "expecting '}'")

    def test_css_font_face_good_01(self):
        code = dedent("""\
  @font-face {
      font-family: 'Swis721CnBTBold';
      src: url('font/swis721_cn_bt_bold-webfont.woff') format('woff'), url('font/swis721_cn_bt_bold-webfont.ttf') format('truetype');
      font-weight: normal;
      font-style: normal;
  }
""")
        for lang in self.langs:
            self._check_zero_results_show_error(code, lang)
            
    def test_less_mixins_01(self):
        code = dedent("""\
.box-shadow (@radius: 5px) {
    margin: 1px;
}
.border-radius () {
    margin: 2px;
}
.wrap() {
    text-wrap: wrap;
}

pre {
    .wrap
}

.container {
     .box-shadow(none);
     .border-radius(0);

     .content {
         padding: 10px;
     }

     border: 0;

     color: #FFF;
     font-size: 12px;
     font-weight: normal;

 }
""")
        self._check_zero_results_show_error(code, language="Less")

    def test_css_namespace_str_01(self):
        code = dedent("""\
@namespace url("http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul");
@namespace 's1';
@namespace flip1 url("http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul");
@namespace blatz2 's1';
""").decode("utf-8")
        self._check_zero_results_show_error(code)
        
    def test_css_namespace_missing_value_02(self):
        code = dedent("""\
@namespace ;
""").decode("utf-8")
        self._check_some_errors_on_line(code, "expecting a string or url", ';')
        
    def test_css_namespace_missing_value_03(self):
        code = dedent("""\
@namespace 35 ;
""").decode("utf-8")
        self._check_some_errors_on_line(code, "expecting a string or url", '35')
        
    def test_css_namespace_missing_semicolon_04(self):
        code = dedent("""\
@namespace flip "blatz" "extra";
""").decode("utf-8")
        self._check_some_errors_on_line(code, "expecting ';'", '"extra"')
        
    def test_css_ruleset_bad_04(self):
        code = 'h1 { background'
        self._check_one_result_check_error_at_eof(code, "expecting ':'")

    def test_css_missing_classname_01(self):
        code = '. { }'
        self._check_one_result_check_error_on_line(code, "expecting an identifier", '{')

    def test_css_ruleset_bad_property_01(self):
        code = 'h1 { background: '
        self._check_one_result_check_error_at_eof(code, "expecting a value")

    def test_css_ruleset_bad_property_02(self):
        code = 'h1 { background: }'
        self._check_one_result_check_error_on_line(code, "expecting a value", '}')

    def test_css_ruleset_bad_property_03(self):
        code = 'h1 { background }'
        self._check_one_result_check_error_on_line(code, "expecting ':'", '}')

    def test_css_ruleset_bad_property_04(self):
        code = 'h1 { border-width: -@shlub; }'
        self._check_one_result_check_error_on_line(code, "expecting a number", '@')

    def test_css_ruleset_bad_property_05(self):
        code = 'h1 { border-width: mssyntax:; }'
        self._check_one_result_check_error_on_line(code, "expecting an identifier", ';')

    def test_css_ruleset_bad_property_fn_06(self):
        code = 'h1 { border-width: f(10'
        self._check_one_result_check_error_at_eof(code, "expecting ')'")

    def test_css_ruleset_bad_property_fn_07(self):
        code = 'h1 { border-width: f(10 }'
        self._check_one_result_check_error_on_line(code, "expecting ')'", '}')

    def test_css_ruleset_bad_property_fn_08(self):
        code = 'h1 { border-width: f(10 ; }'
        self._check_one_result_check_error_on_line(code, "expecting ')'", ';')

    def test_css_ruleset_bad_property_09(self):
        code = 'h1 { border-width: f(10) !'
        self._check_one_result_check_error_at_eof(code, "expecting '!important'")

    def test_css_ruleset_bad_property_10(self):
        code = 'h1 { border-width: f(10) !;'
        self._check_one_result_check_error_on_line(code, "expecting '!important'", ';')

    def test_css_ruleset_bad_property_11(self):
        code = 'h1 {'
        self._check_one_result_check_error_at_eof(code, "expecting '}'")

    def test_css_ruleset_bad_property_12(self):
        code = 'h1 {;'
        self._check_one_result_check_error_on_line(code, "expecting a property name", ';')

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
        self._check_one_result_check_error_at_eof(code, "expecting an identifier")

    def test_css_bad_attribute_02(self):
        code = 'h1[='
        self._check_one_result_check_error_on_line(code, "expecting an identifier", '=')

    def test_css_bad_attribute_03(self):
        code = 'h1[ ='
        self._check_one_result_check_error_on_line(code, "expecting an identifier", '=')

    def test_css_bad_stringeol_01(self):
        code = 'h1[x = "flip\n'
        self._check_one_result_check_error_on_line(code, "missing string close-quote", '"flip')

    def test_css_bad_stringeol_02(self):
        code = 'h1[x = "flip' # ends at eof
        self._check_one_result_check_error_on_line(code, "missing string close-quote", '"flip')

    def test_css_bad_stringeol_03(self):
        code = 'h1[x = \'flip' # ends at eof
        self._check_one_result_check_error_on_line(code, "missing string close-quote", '\'flip')

    def test_css_bad_stringeol_04(self):
        code = '@charset "utf-8' # ends at eof
        self._check_one_result_check_error_on_line(code, "missing string close-quote", '"utf-8')

    def test_css_bad_stringeol_05(self):
        code = '@charset "utf-8\n' # ends at eof
        self._check_one_result_check_error_on_line(code, "missing string close-quote", '"utf-8')

    def test_css_bad_stringeol_06(self):
        code = '@import "utf-8' # ends at eof
        self._check_one_result_check_error_on_line(code, "missing string close-quote", '"utf-8')

    def test_css_bad_stringeol_07(self):
        code = '@import "utf-8\n' # ends at eof
        self._check_some_errors_on_line(code, "missing string close-quote", '"utf-8', lineNo=0)

    def test_css_bad_stringeol_08(self):
        code = 'body { font: "Verdana'
        self._check_some_errors_on_line(code, "missing string close-quote", '"Verdana', lineNo=0)

    def test_css_bad_stringeol_09(self):
        code = 'body { font: "Verdana\n'
        self._check_one_result_check_error_on_line(code, "missing string close-quote", '"Verdana')

    def test_css_bad_termid_01(self):
        code = 'body { font: Microsoft.'
        self._check_one_result_check_error_at_eof(code, "expecting an identifier")

    def test_css_bad_termid_02(self):
        code = 'body { font: Microsoft. ;}'
        self._check_one_result_check_error_on_line(code, "expecting an identifier", ';')

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
        self._check_one_result_check_error_on_line(code, "expecting ':'", 'margin-left')
        
    def test_css_quoted_urls_01(self):
        code = dedent("""\
.browser-toolbar {
  list-style-image: url("chrome://komodo/skin/images/browser_buttons.png");
}
""").decode("utf-8")
        self._check_zero_results_show_error(code)
        
    def test_css_attr_no_value(self):
        code = dedent("""\
.file-status-icons[file_scc_status] {
  /* Since we move the scc status icon to the left of the file image, we have to
     add padding for it in the parenting hbox. */
  padding-left: 4px;
}
""").decode("utf-8")
        self._check_zero_results_show_error(code)

    def test_css_not_pseudo_class(self):
        code = dedent("""\
.file-status-icon:not([file_scc_status]):not([file_status]),
.file-scc-status-extra-icon:not([file_scc_status_extra]) {
  /* Collapse scc status images that are not showing anything. */
  display: none;
}
""").decode("utf-8")
        self._check_zero_results_show_error(code)

    def test_css_moz_any_pseudo_class(self):
        code = dedent("""\
notification:not(:-moz-any([details][open])) [anonid="details"] {
  /* height is !important to override the style= set at runtime that is needed
   * to make things the right height.
   */
  height: 0 !important;
  overflow-y: hidden;
  -moz-transition-property: height;
  -moz-transition-duration: 40ms;
}
[sizemode="fullscreen"]:root :not(#main-toolboxrow) > :-moz-any(menubar, toolbar, statusbar):not([fullscreentoolbar]) {
  visibility: collapse;
}
""")
        self._check_zero_results_show_error(code)
        
    def test_css_structual_pseudo_class_good01(self):
        code = dedent("""\
table tr:nth-child(odd) {
  margin: 1px;
}

table tr:nth-child(2n + 1) {
  margin: 1px;
}

table tr:nth-child(-n) {
  margin: 1px;
}

table tr:nth-child(+3N) {
  margin: 1px;
}

table tr:nth-child(3n-2) {
  margin: 1px;
}

table tr:nth-child(-5N + 3) {
  margin: 1px;
}

table tr:nth-child(+N) {
  margin: 1px;
}

table tr:nth-child(-012) {
  margin: 1px;
}

table tr:nth-child(+44) {
  margin: 1px;
}

table tr:nth-child(odD) {
  margin: 1px;
}

table tr:nth-child(EvEn) {
  margin: 1px;
}
""")
        self._check_zero_results_show_error(code)
        
    def test_css_structual_pseudo_class_bad01(self):
        code = dedent("""\
/* bad ones:*/

table tr:nth-child() {
  margin: 1px;
}
""")
        self._check_some_errors_on_line(code, "expecting a value", ')', lineNo=2)
        
    def test_css_structual_pseudo_class_bad02(self):
        code = dedent("""\
table tr:nth-child(-) {
  margin: 1px;
}
""")
        self._check_one_result_check_error_on_line(code, "expecting a number", ')')
        
    def test_css_structual_pseudo_class_bad03(self):
        code = dedent("""\
table tr:nth-child(- 3) {
  margin: 1px;
}
""")
        self._check_one_result_check_error_on_line(code, "expecting no space before 3", '3')
        
    def test_css_structual_pseudo_class_bad04(self):
        code = dedent("""\
table tr:nth-child(4 n+5) {
  margin: 1px;
}
""")
        self._check_one_result_check_error_on_line(code, "expecting no space before n", 'n')
        
    def test_css_structual_pseudo_class_bad05(self):
        code = dedent("""\
table tr:nth-child(3 even) {
  margin: 1px;
}
""")
        self._check_one_result_check_error_on_line(code, "expecting ')'", 'even')
        
    def test_css_structual_pseudo_class_bad06(self):
        code = dedent("""\
table tr:nth-child(odd 5) {
  margin: 1px;
}
""")
        self._check_one_result_check_error_on_line(code, "expecting ')'", '5')
        
    def test_css_structual_pseudo_class_bad07(self):
        code = dedent("""\
table tr:nth-child(3 5) {
  margin: 1px;
}
""")
        self._check_one_result_check_error_on_line(code, "expecting ')'", '5')
        
    def test_css_structual_pseudo_class_bad08(self):
        code = dedent("""\
table tr:nth-child(squirt) {
  margin: 1px;
}
""")
        self._check_one_result_check_error_on_line(code, "expecting a number or N", 'squirt')
        
    def test_css_structual_pseudo_class_bad09(self):
        code = dedent("""\
table tr:nth-child(3 {
  margin: 1px;
}
""")
        self._check_one_result_check_error_on_line(code, "expecting ')'", '{')
        
    def test_css_structual_pseudo_class_bad10(self):
        code = dedent("""\
table tr:nth-child("bink") {
  margin: 1px;
}
""").decode("utf-8")
        self._check_one_result_check_error_on_line(code, "expecting a number or N", '"bink"')
        
    def test_css_tight_comment(self):
        code = dedent("""\
/*/ ? in a comment !
*/
""")
        for lang in self.langs:
            self._check_zero_results_show_error(code, language=lang)
        

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

    @tag("knownfailure", "causes unsupported utf8 exceptions on kobuild-snow")
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
        self._check_zero_results_show_error(code, language="Less")
        self._check_some_errors_on_line(code, "expecting a directive", 'color', lineNo=0, language="CSS")
        self._check_some_errors_on_line(code, "expecting a directive", 'color', lineNo=0, language="SCSS")
            
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
            self._check_some_errors_on_line(code, "expecting a value", '{', lineNo=1, language=lang)

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
        self._check_zero_results_show_error(code, language="Less")

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
        self._check_zero_results_show_error(code, language="Less")

    def test_css_less_mixins_02(self):
        # No semi-colon needed after the mixin insertion
        code = dedent("""\ 
.wrap () {
  text-wrap: wrap;
  white-space: pre-wrap;
  white-space: -moz-pre-wrap;
  word-wrap: break-word;
}

pre { .wrap }

""").decode("utf-8")
        self._check_zero_results_show_error(code, language="Less")

    def test_css_less_inherit_01(self):
        code = dedent("""\
#header        { color: black;
  .logo        { width: 300px;
    &:hover    { text-decoration: none; }
    a:visited    { text-decoration: none; }
    &::firstThing    { border: dashed; }
    zos::lastThing    { padding: 5px; }
  }
}
""").decode("utf-8")
        self._check_zero_results_show_error(code, language="Less")
        self._check_some_errors_on_line(code, "expecting a property name", '.', lineNo=1, language="CSS")
        self._check_zero_results_show_error(code, language="SCSS")

    def test_css_less_expressions(self):
        code = dedent("""\
@base: 5%;
@filler: @base * 2;
@other: @base + @filler;

#header        { color:  #888 / 4;
  .logo        { width: 300px * 1.1;
    &:hover    { background-color: @base-color + #111; }
    a:visited    { height: 100% / (2 + @filler); }
  }
}
""").decode("utf-8")
        self._check_zero_results_show_error(code, language="Less")
        for lang in ("CSS", "SCSS"):
            self._check_some_errors_on_line(code, "expecting a directive", 'base', lineNo=0, language="lang")
       
        

    def test_css_less_multiple_at_signs(self):
        code = dedent("""\
@base: 5%;
@filler: @base * 2;
@other: @base + @filler;

#header        { color:  @@base;
  .logo        { width: @@@filler;
    &:hover    { background-color: @@@@other + #111; }
  }
}
""").decode("utf-8")
        self._check_zero_results_show_error(code, language="Less")

    def test_css_less_tilde_escape(self):
        code = dedent("""\
.class {
  filter: ~"progid:DXImageTransform.Microsoft.AlphaImageLoader(src='image.png')";
}
""").decode("utf-8")
        self._check_zero_results_show_error(code, language="Less")
        self._check_some_errors_on_line(code, "expecting a value", '~', lineNo=1, language="CSS")
        self._check_some_errors_on_line(code, "expecting a value", '~', lineNo=1, language="SCSS")
   
    def test_css_less_tilde_escape_02(self):
        code = dedent("""\
@var: ~`"@{str}".toUpperCase() + '!'`;
@height: `document.body.clientHeight`;
.class {
  filter: ~"progid:DXImageTransform.Microsoft.AlphaImageLoader(src='image.png')";
  font: "stew@{height}", @var;
}
""").decode("utf-8")
        self._check_zero_results_show_error(code, language="Less")
        for lang in ("CSS", "SCSS"):
            self._check_some_errors_on_line(code, "expecting a directive", 'var', lineNo=0, language=lang)

    def test_css_scss_parse_mixins(self):
        code = dedent("""\
$flip: #334455;
$other: 34px;

@mixin table-base {
  th {
    text-align: center;
    font-weight: bold;
  }
  td, th {padding: $other;}
}

@mixin left($dist) {
  float: left;
  margin-left: $dist;
}

#data {
  @include left(10px);
  @include table-base;
}
""").decode("utf-8")
        self._check_zero_results_show_error(code, language="SCSS")
        
    def test_moz_document_directive_01(self):
        code = dedent("""\
@-moz-document url(chrome://komodo/content/notifications/notificationsWidget.xul) {
  notification .twisty > .twistyImageWrapper {
    padding-left: 0;
    padding-bottom: 0;
  }
  notification .twistyImage {
    list-style-image: none;
    -moz-appearance: treetwisty;
  }
  notification[open] .twistyImage {
    list-style-image: none;
    -moz-appearance: treetwistyopen;
  }
}
""").decode("utf-8")
        for lang in ("CSS", "SCSS", "Less"):
            self._check_zero_results_show_error(code, language=lang)

    def test_moz_document_directive_02_missing_close_brace(self):
        code = dedent("""\
@-moz-document url(chrome://komodo/content/notifications/notificationsWidget.xul) {
  notification .twisty > .twistyImageWrapper {
    padding-bottom: 0;
  }
""").decode("utf-8")
        for lang in ("CSS", "SCSS", "Less"):
            self._check_one_result_check_error_at_eof(code, "expecting '}'", language=lang)

    def test_moz_document_directive_03_moz_items(self):
        code = dedent("""\
@-moz-document url(chrome://url0) { 
  notification .twisty > .twistyImageWrapper {
    padding-bottom: 0;
  }}
@-moz-document url('chrome://url1') { 
  notification .twisty > .twistyImageWrapper {
    padding-bottom: 0;
  }}
@-moz-document url-prefix(chrome://url2) {
  notification .twisty > .twistyImageWrapper {
    padding-bottom: 0;
  } }
@-moz-document url-prefix('chrome://url3') { 
  notification .twisty > .twistyImageWrapper {
    padding-bottom: 0;
  }}
@-moz-document domain(chrome://url4) {
  notification .twisty > .twistyImageWrapper {
    padding-bottom: 0;
  } }
@-moz-document domain('chrome://url5') { 
  notification .twisty > .twistyImageWrapper {
    padding-bottom: 0;
  }}
@-moz-document regexp('chrome://url6') {
  notification .twisty > .twistyImageWrapper {
    padding-bottom: 0;
  }}
""").decode("utf-8")
        for lang in ("CSS", "SCSS", "Less"):
            self._check_zero_results_show_error(code, language=lang)
  
    def test_moz_document_directive_unquoted_regex_bad(self):
        code = dedent("""\
@-moz-document regexp(chrome://url) {
  notification .twisty > .twistyImageWrapper {
    padding-bottom: 0;
  }}
""").decode("utf-8")
        for lang in ("CSS", "SCSS", "Less"):
            self._check_some_errors_on_line(code,
                "the regexp argument must be a quoted string",
                "regexp(chrome://url)", 2, language=lang)
               
    def test_css_scss_bad_mixin_01(self):
        code = "@mixin  {"
        self._check_some_errors_on_line(code, "expecting a mixin name", '{', lineNo=0, language="SCSS")
        
    def test_css_scss_bad_mixin_02(self):
        code = "@mixin table-base missing-brace {"
        self._check_some_errors_on_line(code, "expecting '{'", 'missing-brace', lineNo=0, language="SCSS")
        
    def test_css_scss_bad_mixin_03(self):
        code = dedent("""\
@mixin table-base {
  td, th {padding: 2px;}
}

#data {
  @zeep;
}
""").decode("utf-8")
        self._check_some_errors_on_line(code, "expecting 'include'", 'zeep', lineNo=5, language="SCSS")
        
    def test_css_scss_bad_mixin_04(self):
        code = dedent("""\
@mixin table-base {
  td, th {padding: 2px;}
}

#data {
  @include;
}
""").decode("utf-8")
        self._check_some_errors_on_line(code, "expecting a mixin name", ';', lineNo=5, language="SCSS")
        
    def test_css_scss_minified_numeric_property(self):
        code = dedent("""\
body{margin:0; }

// comment
p {
    margin: 3px;
}
""").decode("utf-8")
        for lang in ("SCSS", "Less"):
            self._check_zero_results_show_error(code, language=lang)
        self._check_some_errors_on_line(code, "expecting a selector", '/', lineNo=0, language="CSS")

    def test_css_scss_parent_selector_01(self):
        code = dedent("""\
.DataTable {
    width:100%;

    & > thead {
        & > tr {
            & > th {
                background: $mcsBlue;
                color: #fff;
                font-weight: bold;
                text-align: left;
                padding: $spaceS;
            }
        }
    }
}
""").decode("utf-8")
        for lang in ("SCSS",):
            self._check_zero_results_show_error(code, language=lang)
        self._check_some_errors_on_line(code, "expecting a property name",
                                        '&', lineNo=3, language="CSS")
        self._check_some_errors_on_line(code,
                        "expecting a selector",
                                        '>', lineNo=3, language="Less")

    def test_css_scss_parent_selector_02(self):
        code = dedent("""\
.DataTable {
    & > tbody {
        & > tr {
            &:hover > td{
                background: $grayish !important;
                color: $text !important;
            }
            & > td {
                padding: $spaceS;
            }
        }
    }

    &:hover > tbody > tr> td {
        color: $finePrint;
    }

    &:hover > tbody > .even > td {
        background: lighten($lightGray, 2%);
    }
}
""").decode("utf-8")
        self._check_zero_results_show_error(code, language="SCSS")

    def test_less_parent_selector_03(self):
        code = dedent("""\
.bordered {
    &.float {
        float: left;
    }
    .top {
        margin: 5px;
    }
}
""").decode("utf-8")
        self._check_zero_results_show_error(code, language="Less")

    def test_css_bad_missing_selector(self):
        code = "td,  {padding: 2px;}"
        for lang in self.langs:
            self._check_some_errors_on_line(code, "expecting a selector", "{", lineNo=0, language=lang)
        
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

    @tag("bug92368", "knownfailure")
    def test_css_ignore_leading_space(self):
        code = "\n    " * 10 + "   ^"
        results = self.csslinter.lint(code)
        self.assertTrue(len(results) > 0)
        r = results[0]
        actualError = "Actual error: %s" % r
        self.assertTrue(r.message.startswith("expecting a selector"),
                        actualError)
        self.assertTrue(r.line_start == 11, actualError)
        self.assertTrue(r.line_end == 11, actualError)
        self.assertTrue(r.col_start == 4, actualError)
        self.assertTrue(r.col_end == 5, actualError)

    @tag("bug92321", "knownfailure")
    def test_scss_support_extend(self):
        code = dedent("""\
.error {
  border: 1px #f00;
  background-color: #fdd;
}
.seriousError {
  @extend .error;
  border-width: 3px;
}
""").decode("utf-8")
        self._check_zero_results_show_error(code, language="SCSS")

    @tag("bug92561")
    def test_less_parameterless_mixin(self):
        code = dedent("""\
.error {
  border: 1px #f00;
  background-color: #fdd;
}
div#error {
  .error;
  border-width: 3px;
}
""").decode("utf-8")
        self._check_zero_results_show_error(code, language="Less")

    @tag("bug92561")
    def test_less_continued_selectors(self):
        code = dedent("""\
body {
    > div {
        color: blue;
    }
    + p {
        color: pink;
    }
}
""").decode("utf-8")
        self._check_zero_results_show_error(code, language="Less")

    @tag("bug92561")
    def test_less_continued_selectors_with_mixin(self):
        code = dedent("""\
.mixin {
    color: red;
    }
body {
    .mixin;
    > div {
        color: blue;
    }
    + p {
        color: pink;
    }
}
""").decode("utf-8")
        self._check_zero_results_show_error(code, language="Less")

    @tag("bug92561")
    def test_less_continued_selectors_with_amp(self):
        code = dedent("""\
input {
    color: red;
    &[disabled] {
        color: grey;
    }
}
""").decode("utf-8")
        self._check_zero_results_show_error(code, language="Less")

    @tag("bug93115")
    def test_less_negative_mixin_args(self):
        code = dedent("""\
.negative_margin(@margin: 0) {
    margin-right: @margin;
}

.other_margin(@foo:0, @margin: 0) {
    margin-right: @margin;
    margin-left: @foo;
}

body {
    margin: 0;
    & input {
        font-family: sans-serif;
        .other_margin(20px, -12px);
    }
    p {
        .negative_margin(-10px);
    }
}
""").decode("utf-8")
        self._check_zero_results_show_error(code, language="Less")

    @tag("bug93115")
    def test_less_ampersand_comma_selector(self):
        code = dedent("""\
body {
    margin: 0;
    &, input {
        font-family: sans-serif;
    }
}
""").decode("utf-8")
        self._check_zero_results_show_error(code, language="Less")

    _bug_94548_full_code = dedent(u"""\
/* Bug caused by non-ascii text at line 1274 */

/*EM 'reset baseline' style rules*/
html, body, div, span, applet, object, iframe,
h1, h2, h3, h4, h5, h6, p, blockquote, pre,
a, abbr, acronym, address, big, cite, code,
del, dfn, em, font, img, ins, kbd, q, s, samp,
small, strike, strong, sub, sup, tt, var,
dd, dl, dt, li, ol, ul,
fieldset, form, label, legend,
table, caption, tbody, tfoot, thead, tr, th, td {
	margin: 0;
	padding: 0;
	border: 0;
	font-weight: inherit;
	font-style: inherit;
	font-size: 100%;
	font-family: inherit;
	text-align: left;
	vertical-align: baseline;
	background: transparent;
}

/*remember to define focus styles*/
ol, ul { list-style: none; }

/*tables still need 'cellspacing="0"' in the markup*/
table {
	border-collapse: collapse;
	border-spacing: 0;
}

caption, th, td {
	text-align: left;
	font-weight: normal;
}

a {
	color: #B70101;
	text-decoration: none;
}

a:hover { text-decoration: underline; }
q:before, q:after,
blockquote:before, blockquote:after { content: ""; }
blockquote, q { quotes: "" ""; }
img { border: none; }
acronym, abbr.initialism, dfn { cursor: help; }
abbr { speak: spell-out; }
acronym, abbr.truncation, dfn { speak: normal; }
cite { font-style: italic; }
strong { font-weight: bold; }
em { font-style: italic; }

html {
	color: #000;
	background: url("../images/window-bg-not-horizontal-menu.jpg") repeat-x scroll 0 0 #E5E3D7;
}

body {
	background-color: transparent;
	color: #333333;
	font: 100%/1.5 "Lucida Grande",Verdana,sans-serif;
	margin: 36px auto 0;
	width: 880px;
}


/* global nav menu*/
#globalnav {
	position: absolute;
	top: -26px;
	right: 0px;
}

#globalnav li {
	display: inline-block;
	padding: 0px 10px 0 10px;
	border-left: 1px solid #c9ab80;
	line-height: 1;
	font-size: 0.75em;
}
#globalnav li:first-child {
border-left: 0 none;
padding-left: 0;
}

#globalnav #uwsearch {
	padding-left: 0;
	border-left: 0;
}
#globalnav #last_tool {
  padding-right: 0;
}

#globalnav a { color: #F7F3E9; line-height: 1; margin: 0; padding: 0 0 1px 0; display: block;}

#header {
	position: relative;
	width: 100%;
	height: 97px;
	color: #fff;
	background-color: #B70101;
	z-index: 100;
	-moz-box-shadow: 0px 2px 2px rgba(60, 60, 60, 0.4);
	-webkit-box-shadow: 0px 2px 2px rgba(60, 60, 60, 0.4);
	background-image: url("../images/tan-hdr-bottom.jpg");
	background-repeat: repeat-x;
	background-position: bottom;
}

#uwhome {
	position: absolute;
	top: -26px;
	left: 75px;
}

#siteTitle {
	position: absolute;
	top: 28px; /*CUSTOMIZATION: If not using a tagline; change top: to 26px; */
	left: 80px;
	width: 600px;
}

#header h1 span {
	position: absolute;
	top: 0;
	left: 0;
	z-index: 5000;
	width: 300px; /*CUSTOMIZIZATION: Set width of your site-title.png image*/
	height: 36px;
	margin-top: 0px;
	text-indent: -999em;
	background-image: url("../images/b_wiIdea.png");
	background-repeat: no-repeat;
}

h1 a {
	display: block;
	width: 100%;
	height: 100%;
	margin-top: 0px;
	text-indent: -999em;
}

#tagline_1 {
    color: #F7F5EB;
    font-size: 0.75em;
    font-weight: bold;
    left: 84px;
    position: absolute;
    top: 60px;
}

#tagline {
	position: absolute;
	top: 15px;
	right: 25px;
	left: 480px;
}
#tagline p {
	font-family: "Trebuchet MS", Arial, Helvetica, sans-serif;
	color:#F7F5E8;
	font-size: 0.75em;
	font-style: italic;
	font-weight: bold;
	line-height: 1.5;
}

#crest {
	width: 70px;
	height: 104px;
	position: absolute;
	top: -22px;
	left: 5px;
	z-index: 100;
}

#nav {
text-align: center;
}

#main-menu {
  padding-top: 15px;
  position: relative;
  width: 100%;
  z-index: 50000;
  text-align:center;
}

#main-menu > li {
  background: none repeat scroll 0 0 #666152;
  border: 3px double #999999;
  color: #333333;
  display: inline-block;
  font-size: 0.75em;
  height: 25px;
  line-height: 25px;
  margin: 0 5px;
  position: relative;
  vertical-align: top;
}

#main-menu a {
  background-color: transparent;
  color: #FFFFFF;
  display: block;
  height: 100%;
  line-height: 24px;
  padding: 0 15px;
  position: relative;
  text-align: center;
}

#main-menu .current a {color: #333;}

#main-menu a:hover {
	text-decoration: none;
}

#main-menu > li:hover, #main-menu > a:focus, #main-menu > a:hover, #main-menu > a:active, #main-menu .current {
	background-color: #333;
	text-decoration: none;
}

/*layout*/

#shell {
  background-color: #FFFFFF;
  border-color: #C3BCA1;
  border-style: none solid solid;
  border-width: 1px 1px 2px;
  position: relative;
  width: 878px;
  z-index: 1;
  padding-top: 32px;
}

.wiscidea-in-action-home, .search #content {
	padding: 12px 0 0 0;
  background-color: #fff;
}

#content {
	padding: 0 60px 30px 80px;
	}

#content.edit, #content.delete, #content.manage {
	padding: 0 30px 30px/* 80px*/;
}



/*pages*/

#main {
  width: 500px;
  margin-right: 60px
}
.single #main {width: 550px;}
.archive #main {width: auto;}
.page-id-754 #main {width: auto;}

#main li, #main p, #sidebar li {
  font-size: .925em;
  line-height: 1.775;
	margin: 1.25em 0;
}
#sidebar li {font-size: .8125em;}
.single #sidebar li {line-height: 1.3;}
#main .wp-caption p {
  margin: 0;
  font-size: .9em;
  color: #666;
}

.alignright {float: right;}
.alignleft {float: left;}

div.wp-caption img, img.size-full {border: 1px solid #999;}
.wp-caption-text {
  font-weight: bold;
  line-height: 1.2;
  margin-bottom: 30px;
}

.page .alignleft {margin: 7px 20px 20px 0;}
.page .alignright {margin: 7px 0px 20px 30px;}


/*pages*/
.page #shell {
  padding: 0px 0;
}
.page #content {
  padding: 30px;
  margin: 0;
  background: #ffffff;
}
.page #content h1 {
font-size: 1.4em;
font-weight: bold;
line-height: 1.1;
margin-bottom: 14px;
}


.video-embed {margin: 30px 0;}


/*tables*/

table {
  border: 1px solid #666;
  border-collapse: collapse;
}

thead th, tfoot {
  background: none repeat scroll 0 0 #EFEFEF;
  font-weight: bold;
  padding: .25em;
}

th, td {
  border: 1px solid #666;
  padding: /*0.5em 1em*/.25em;
}

/* footer */
#footer {
  background-color: transparent;
  border-top: 1px solid #666152;
  color: #666666;
  font-size: 0.6875em;
  line-height: 1;
  padding-bottom: 40px;
  padding-top: 10px;
  width: 100%;
}

#footer p { text-align: center; margin-top: .5em;}

.form #footer {border-top: 0;}

/*
***************************************************
skip navigation, etc.
***************************************************
*/

#skip, #skip:hover, #skip:visited {
	position: absolute;
	top: -5000em;
	left: -5000em;

	top: 20px;
	left: 0;
	width: 1px;
	height: 1px;
	overflow: hidden;
	color: #fff;
	background-color: transparent;
}

#skip:active, #skip:focus {

	top: 0;
	left: 775px;
	width: auto;
	height: 1.2em;
	padding: 2px;
	z-index: 1000;
	line-height: 1.25;
}

#skip:hover {
	text-decoration: none;
	color: #fff;
	background-color: #cc1f46;
}

.hide {
	position: absolute;
	top: -100em;
	left: -5000em;
	height: 0;
}

.hide a, .hide a:hover, .hide a:visited {
	position: absolute;
	top: 0;
	left: -5000em;
}

.hide a:focus {
	position: static;
	width: auto;
	height: auto;
}

a:hover, a:active {outline: none;}

.clearfix:after {
    content: ".";
    display: block;
    height: 0;
    font-size: 0;
    clear: both;
    visibility: hidden;
}



/*edit stuff*/
.post-edit-link {
  font-size: 12px !important;
  font-family: verdana, arial, sans-serif !important;
  font-style: normal !important;
}
img.ui-img {
	border:medium none !important;
	float:none !important;
	margin:0 -3px 0 3px !important;
	vertical-align:text-bottom !important;
	width:16px !important;
}


#content.wiscidea-in-action-home h1 a, div#wi a { color: #000; }

#content.wiscidea-in-action-home h1 a:hover, div#wi a:hover {
	text-decoration: none;
	color: #CDA248;
}


#content h2 { font-size: 1.25em; }

.hide {
	position: absolute;
	top: -100em;
	left: -500em;
	height: 0;
}

.hide a, .hide a:hover, .hide a:visited {
	position: absolute;
	top: 0;
	left: -5000px;
}

/*visible to keyboard users when tabbing*/
.hide a:focus {
	position: static;
	width: auto;
	height: auto;
}

#content.wiscidea-in-action-home form, #content.search form { width: 500px; }
#content p { margin: 1em 0; }

#table_container {
	margin-top: 0;
	width: 100%;
}

#table_container > h2 {
	margin: 2em 0 0;
	font-size: 0.875em;
	font-weight: bold;
	padding-bottom: 4em;
}

#table_container > h2 > span {
		display: block;
	margin-top: .25em;
	font-size: .95em;
	font-weight: normal;
}

#results_list, .recent {
	width: 100%;
	margin-top: .5em;
	margin-bottom: 30px;
	border-collapse: collapse;
	clear: both;
}

#results_list th, #results_list td, #recent th, #recent td {
	border: 1px solid #999;
	padding: 10px 4px 6px;
	line-height: 1.25em;
	font-size: 0.75em;
}

#results_list .header, .recent .header {
	color: #810000;
	padding: 10px 5px;
	font-size: 0.8125em;
	background-color: #fafafa;
}

.browse_projects #results_list #project_submitter {
	width: 11%;
}

.browse_projects #results_list #create_time, .browse_projects #results_list #last_updated {
	width: 10%;
}

.search_results #results_list #project_submitter {
	width: 11%;
}

.search_results #results_list .center {
	text-align: center;
	vertical-align: middle;
}

#results_list th.left, #results_list td.left, #recent th.left, #recent td.left  {
	text-align: left;
}

#user_list {
	width: 100%;
}

#content dl { margin: 2em 0 0 0; }

#content dl dt {
	display: block;
	margin-top: 1em;
	font-weight: bold;
}

#content dl dd {
	display: block;
	margin-left: 20px;
}

#content dl dd ul { margin-left: 10px; }

#details #content #bodyText {
	width: 600px;
	background: transparent;
}

#details #content #bodyText h1 {
	font-weight: bold;
	font-size: 1.25em;
}

#details #content #bodyText h2 {
	margin: 1em 0 0 0;
	font-size: 1em;
	font-weight: bold;
}

#details #content #bodyText h2#description {
	position: absolute;
	top: -100em;
	left: -500em;
	height: 0;
}

#details #content #bodyText p { margin: 0 0; }
#details #content #bodyText p.narrative { margin: 1em 0; }
#details #content #bodyText h2 + ul { margin-left: 0; }
#details #content #bodyText h2 + ul#sites { margin: 1em 0; }

#details #content #bodyText h2 + ul#partners li {
	float: left;
	width: 48%;
}

#details #content #bodyText ul + h2 {
	clear: both;
	padding-top: 1em;
}

#details #content #updates {
	display: block;
	margin: 2em 0 0 1em;
}

#content p {
	font-size: 0.8125em;
}

/*search form*/
#content.search form {
width: 80%;
margin: 3em 0 0;
	border: 2px solid #D7D5CF;
	-moz-border-radius: 9px;
	-webkit-border-radius: 9px;
	border-radius: 9px;
padding: 20px 25px;
}

#content.search legend {
	font-weight: bold;
	font-size: 0.9375em;
	line-height: 1.4em;
}

#content.search label {
	display: block;
	margin: 2em 0 .25em;
	font-size: 0.9375em;
}


#content.search form input[type="text"] {
	font-size: 0.8125em;
}

#content.search form input[type="submit"]{
display: block;
margin: 40px 0 24px 0;
font-size: 0.9375em;
	border: 1px solid #333;
	-moz-border-radius: 6px;
	-webkit-border-radius: 6px;
}

#content.search form select
{
	font-size: 0.8125em;
	padding: 1px 0;
}


#content.search_results {padding: 0 20px;}
#results_list > thead th { font-weight: bold;}
#results_list > tbody th { font-weight: normal; padding: 8px; vertical-align: middle;}

#results_list > thead, #results_list > tbody {
	border-top: 2px solid #666;
	border-bottom: 2px solid #666;
}

/*remove the body id blocks once transition is complete*/
#content.county a#wi { width: 370px; }

#content.county #county_query_results {
	width: 50%;
}

/*error pages*/
#content.error {
	padding-bottom: 80px;
}

#sidebar {
	float:right;
	margin-top: -1em;
	margin-left: 20px;
	padding: 15px 10px;
	font-family: Georgia, Times, "Times Roman", serif;
	background-color: #FBF6E7;
	border-top: 6px double #E0CD9B;
	border-bottom: 6px double #E0CD9B;
	width: 320px;
}

#sidebar > h2 {
	font-size: 0.8125em;
	font-weight: bold;
}

#county_connections {
	width: 300px;
	max-width: 320px;
	border: 0;
}

#county_connections th, #county_connections td {
	border: 0;
}

#county_connections th {
	width: 250px;
	max-width: 65%;
}

#county_connections td {
	padding: 5px 0;
}

#content > h1 {
	margin: 1.25em 0;
	font-size: 1.125em;
	font-weight: bold;
	line-height: 1.25em;
}

#content > h2, #content > h3 {
	font-weight: bold;
}

#content.profile > h1 {
	width: auto;
}

h1 + p {
	margin-top: 2em;
}

#content.not_county h1 {
	margin-bottom: 3em;
	font-size: 1em;
	font-weight: normal;
}

#content.projects_school h1 {
	width: 500px;
}

#content .admins, #content #p_last_updated {
	margin: 1em 0;
	font-size: .75em;
}

#content .admins, #content #p_last_updated {
	margin: 1em 0;
	font-size: .75em;
}

#content #p_last_updated {
	padding-bottom: 20px;
	border-bottom: 1px solid #ccc;
}

#content #new_search, #content .admins {
	width: 150px;
	display: block;
	margin: 1.5em 0;
	padding: 3px 8px;
	font-size: 0.875em;
	text-align: center;
	line-height: 1.5;
	background-color: #fff;
	border: 1px solid #c90;
	-moz-border-radius: 6px;
	-webkit-border-radius: 6px;
}

#content.wiscidea-in-action-home .admins {
	width: 200px;
	margin-top: 50px;
	margin-left: 200px;
	padding: 10px;
}

#content.profile .admins, #content.profile #new_search {
	width: 12em;
	font-size: 0.875em;
}

#content #new_search:hover {
	color: #810000;
}

/*new results class*/
#sidebar > h2 {
	font-size: 0.8125em;
	font-weight: bold;
}

#sidebar > table {
	width: 300px;
	max-width: 320px;
	border: 0;
}

#sidebar > table td, #sidebar table th {
	border: 0;
	padding: .25em 0;
	line-height: 1.1em;
}

#sidebar > table th {
	width: 250px;
	max-width: 65%;
	font-size: 0.8125em;
}

#goprofile {
	display: block;
	margin: 1em 0 0;
	font-size: 0.8125em;
}

.results #content h1 {
	margin: 1em 0;
	width: 320px;
	font-size: 1.3em;
	font-weight: bold;
	line-height: 1.25em;
}
/*end*/

#content.profile.county h1, #content.profile.county h2,#content.profile.county h3 { font-weight: bold; }

#content.profile.county h2 {
	margin: 2.5em 0 1em;
	font-size: 0.9375em;
}

#content.profile.county h3 {
	margin: 1em 0 .25em 10px;
	font-size: 0.875em;
}

#content.profile.county h2#description {
	visibility: hidden;
	margin: 0;
}

#content.profile.county p { margin: .25em 0 .5em 20px; }
#content.profile.county ul { margin: .5em 0 .5em 20px; }

#content.profile.county ul + h2 {
	clear: both;
	padding-top: 1em;
}

#content.profile.county ul > li {
	font-size: 0.8125em;
}

#profile_county_list {
	width: 100%;
}
#content.profile #profile_county_list > li {
	width: 25%;
	display: inline-block;
	vertical-align: top;
	line-height: 1.5;
	font-size: 0.8125em;
}

#content.profile .partner_name {
	margin-bottom: .35em;
	line-height: 1.2;
}

.profile > h1, .profile > h2, .profile > h3 { font-weight: bold; }
.profile > h1 { font-size: 1.25em; }

#content .profile h2 {
	margin: 2em 0 .5em 0;
	font-size: 1.1em;
}

.profile #content h3 {
	margin: .5em 0 .25em 0;
	font-size: 1em;
}

.profile #content h2#description {
	visibility: hidden;
	margin: 0;
}

.profile #content p { margin: .25em 0 .5em 20px; }
.profile #content ul { margin: .5em 0 .5em 20px; }

.profile #content ul + h2 {
	clear: both;
	padding-top: 1em;
}

#content.profile > h2 {
	margin: 1em 0 0;
	font-size: 0.875em;
	font-weight: bold;
}

#content.profile h2 + p, #content.profile h2 + ul {
	margin-top: .15em;
}

#content.profile h2 + ul > li {
	font-size: 0.8125em;
}

/*#content.profile #description {
	text-indent: -999em;
	margin: 0;
	height: 5px;
}*/

/*end*/


/*Two-column lists*/

/*old*/
#details #content ul.long li, #content.county ul.long li, #content.profile.county ul.long li  {
	float: left;
	width: 30%;
}

/*new*/
#details #content ul.long li, body.results #content ul.long li, .profile #content ul.long li  {
	float: left;
	width: 30%;
}

#content form .clear {
	clear: both;
	padding-top: 2em;
}

#add-revise #content ol { margin: 1em 0; }

#add-revise #content ol li {
	margin: 0 0 .5em 20px;
	list-style: decimal;
}

#sitelist #content ol#sites { width: 80%; }

#sitelist #content ol#sites li {
	margin-bottom: .75em;
	font-weight: bold;
}

#sitelist #content ol#sites li span {
	display: block;
	font-weight: normal;
}

#update.search #wrap #content ul#update-options {
margin-top: 3em;
}

#update.search #wrap #content ul#update-options li {
list-style: square;
margin-left: 20px;
margin-bottom: 2em;
font-size: 1.1em;
}

/** submission form**/


#p_name {margin-top: 32px;}
#p_name label {
	display: block;
	margin-bottom: 5px;
}

#primary_leader, #work {
	margin: 2.5em 0;
}

#content.form #work label {
	font-size: 0.8125em;
}

.fw_normal {font-weight: normal;}
.numbered span {
	display: block;
	margin-bottom: 15px;
}

#work > legend {
	display: block;
	margin-bottom: .5em;
	font-size: 1em;
	font-weight: bold;
}

#primary_leader label , #partners_specific label{
	display: inline-block;
	vertical-align: top;
	width: 30%;
}

.std label {
	display: inline-block;
	vertical-align: top;
	width: 80%;
}

#focus_areas, #beneficiaries, #involved, #partners_set, #durations {
	margin: 3em 0;
	padding: 10px;
}

.checkbox_radio > .row.one_column {
		width: 70%;
}

#content.form .row.one_column.partner_type{
	margin: 1em 0 0;
	width: 100%;
}

#counties {
	margin: 1.5em 0 0;

}

#counties legend span {
	display: block;
	margin-top: 2em;
	margin-left: 25px;
	font-weight: normal;
}

#content.form #tabs-3 .partner_type  {
	margin-bottom: .5em;
}

#content.form #tabs-5.ui-tabs.ui-tabs-panel {
	padding-bottom: 80px;
}

#content.form #tabs-5 > #supplementaries_notes {
	margin-top: 2em;
}

#content.form #tabs-5 > #supplementaries_notes > .row {
	margin: 2em 0;
}


#counties.checkbox_radio .row {
	display: inline-block;
	vertical-align: top;
	width: 20%;
}

#which_counties {
	margin: 0 0 20px 25px;
}

.specify_other, #tangible_txt.row {
	margin: 1em 0;
}

#partners_specific .row, .std {
	margin-bottom: .5em;
}

#check_all {
	display: block;
	margin: 0 0 1em 0;
}

#show_errors {
	position: relative;
	margin: 2em 0 3em;
	z-index: 5000;
	width: 720px;
	padding: 15px;
	border: 1px dashed #666;
	background-color: #ffc;
}

#content.form #show_errors > h2 {
	margin: .5em 0 0;
	font-size: 1em;
	font-weight: bold;
	color: #000;
}

#content.form #show_errors img {
	vertical-align: text-bottom;
}

#content.form #show_errors ul > li {
	margin-bottom: .35em;
	font-size: 0.875em;
}

#content.form #show_errors ul {
	margin-top: 1em;
}
#error-list, #message.error {
	list-style: decimal;
	margin: 1.5em 0;
/*	color: #F20803;*/
	font-weight: bold;

}

#error-list > li, #message.error > li {
	margin-left: 20px;
	margin-bottom: .5em;
	font-size: 1.0625em;
}

#error-list, #error-list > li , #error-list > li > a,  #message.error > li > a{color: #000; font-size: 0.90em;}

#error-list > li > a {
	color: #000;
	font-weight: normal;
}

textarea {
	display: block;
	padding: 0 3px;
}

.jqEasyCounterMsg {
	margin-top: 5px;
	width: 90%!important;
}

#content.form .marked {position: absolute; top: 16px;left:  24px;background: transparent; color: #333; font-size: 0.8125em;}

#content.user.form .marked {position: static;font-size: 0.875em;}


.marker {
	font-size: 1.2em;
	font-weight: bold;
	color: #B70000;
}

.required:before {
	content: '*';
	margin-right: 3px;
	font-size: 1.2em;
	font-weight: bold;
	color: #B70000;
}

#secondary_contact_row .required:before  {
	margin-left: -10px;
}

.row.additional {margin-top: 15px;}

.view {
	display: block;
	margin: .75em 0 .25em;
	color: #b70101;
	font-size: 1em;
	font-weight: bold;
}

#messsages, #messages .success, .success {
	padding-top: 20px;
	font-size: 1.1em;
	color: /*#b70101*/green;
}

#wrap.thanks {
	padding-bottom: 80px;
}

.row > div > label {
	margin: .5em 0;
	font-size: 0.8125em;
	line-height: 1.1;
}

#content.m_notice {
	padding-top: 32px;
	padding-bottom: 100px;
}

#content.notice h1 {
	font-size: 0.9375em;
	font-weight: bold;
}

#content.notice h2 {
	font-size: 0.875em;
	font-weight: normal;
	margin: 1.5em 0 .5em;
}

#content.notice h3 {
	font-size: 0.875em;
	font-weight: bold;
	margin: 1.5em 0 0;
}

#content.notice h3 + p {
	margin-top: .5em;
}

#content.notice #go_home {
	margin-top: 50px;
	text-align: right;
}

#message.notice {
	margin-bottom: 50px;
}

#message.notice p{
	font-size: 1em;
}

#content.exit li {
	padding-bottom: 80px;
}

#content.exit  h1:before, #content.exit  p:before {
	content: url("../images/Warning_32.png");
	margin-right: 5px;
	vertical-align: -5px;
}

#content.exit > h1 {
	margin-top: 1em;
	font-size: 1.1875em;
}

#content.exit p {
	font-size: 1.125em;
	padding-bottom: 80px;
}

.inline {
	font-size: 0.875em;
}

#content.review > div h2, #content.review > div h3 {
	display: inline;
	margin-right: 5px;
	font-weight: bold;
}

#content.review h2 {
	color: #b70701;
}

#content.review form {
	margin: 40px 0;
}


#content.review form input {

	font-size: 1.0625em;

}

/*User*/

#content.form.user legend {
	display: block;
	padding: 24px 0;
	font-size: 0.875em;
}

#content.form.user .row {
	margin-top: 1.25em;
	width: 80%;
}

#content.form.user label, #content.user #register {
	display: block;
}

#content.form.user input[type='submit'] {
	margin-top: 2em;
}

#content.notice #register {
	font-size: 1.0769em;
}

#content.notice #register:after {
	content: ' ⇒';
	/*
	 *fadsjlkfsdalkj type s as fasat as you want, no problem....
	 *
	 */
	color: #b70101;
	font-size: larger;
}

#content.user #fs_roles label {
	display: inline;
}

#content.user #fs_roles {
	margin-top: 1em;
}

#content.user #fs_roles > legend {
	display: block;
	padding: .25em 0 .25em 0;
	font-size: 0.875em;

}

#content.user #fs_roles > legend > span {
	display: block;
	width: 80%;
	margin: .5em 0;
	font-size: 0.9286em;
	line-height: 1.2;
	padding: 5px 5px;
	background-color: #FFFFCC;
	border: 1px solid #b70701;
}

#content.user #fs_roles strong {
	display: inline-block;
	width: 80%;
	margin: .25em 0 0 15px;
	font-weight: bold;
	color: #b70101;
	line-height: 1.2;
}

#content.user #fs_roles img {
	vertical-align: top;
	margin-right: 5px;
}

#content.user #fs_roles > .row {
	margin: 0 0 .75em 0;
}

#content.user label {
	font-size: 0.875em;
}

#content.user.form label > span {
	display: block;
	margin: .25em 0 0;
	font-size: .9286em;
	line-height: 1.2;
}

#content.form .formlabelblock {
	display: block;
	margin-left: 25px;
}

#content.user #register {
	margin-top: 2em;
	font-size: 1em;
}

#content.user input {
	max-width: 80%;
}

#content.user #fs_roles > .row label{
	margin-left: 5px;
	font-size: 0.8125em;
}

#content.user #fs_roles span {
	margin-left: 2em;
}

.sample_format {display: block}

.label_format {display: block;}



/*Browse*/

#content.browse > h1 {
	margin: 1em 0;
}

#content.browse #add {
	margin: 1em 0;

}
#content.browse table {
	border-collapse: separate;
}
#content.browse th, #content.browse tbody td {
	border-width: 1px 0;
	border-color: #dadada;
	vertical-align: middle;

}

#content.browse tbody td {
		text-align: center;
}

#content.browse #add > span {
	margin-left: 5px;
	vertical-align: 8px;
}

table #p_name {
	border-right: 1px solid #ccc;
	width: 35%;
}

/*Edit*/

#content.edit .edit_view_profile {
	margin: 2em 0;
}
#content.edit .edit_view_profile > a {
	color: #b70101;
	background-color: #E5E3D7;
	padding: 5px;
	font-size: 1.077em; /*16/13*/
	border-radius: 6px;
	border: 1px solid #999;
}

#content.edit .edit_view_profile > a:hover {
	border-color: #b70101;
	border-width: 2px;
	text-decoration: none;
}

#content.edit {
	margin-top: 32px;
	padding: 0 20px;
}

#content.edit.user h1, #content.search_results h1 {
	display: block;
	vertical-align: baseline;
	margin: 1em 0;
}

#content.edit #meta {
	width: 50%;
	border: 1px solid #999;
	background-color: #e1dfd6;
}

#content.edit #meta h2 {
	margin-left: 10px;
}

#content.edit #meta p {
	font-size: 0.75em;
	margin-left: 10px;
}

#content.edit h2 {
	margin: 1em 0 .25em 0;
	font-size: 0.875em;
}

#content.edit li, #content.form li {
	font-size: 0.8125em;
}

#content.edit .request_shorten {
	display: block;
	width: 90%;
	font-size: .8125em;
	font-weight: normal;
	line-height: 1.25;
	color: #000;
	background-color: #fffcb5;
	margin: .5em 0;
	padding: 5px;
	border: 1px solid #999;
}

#content.edit .request_shorten:before {
	content: url("../images/Warning_24.png");
	margin-right: 10px;
}

#content.profile .edit_this {
	font-size: 0.875em;
}

#content.profile .edit_this img {
	vertical-align: bottom;
}

#content.profile .edit_this a:hover {
	text-decoration: none;
	color:  #4911FF;
}

#content.edit .option {
	display: inline-block;
	vertical-align: top;
	margin-left: 100px;
}

#content.edit #project_meta ul {
	margin-top: 16px;
}

#tabs {width: 750px; margin-top: 24px;/* margin-bottom: 64px;*/}

#content.edit #project_meta span {font-weight: bold;}

.ui-tabs-panel {width: 660px;}

#content.form legend {
	font-size: 0.875em;
	font-weight: bold;
}

#content.form legend .contact_instructions {
	display: block;
	width: 650px;
	margin: .5em 0 .5em 20px;
	font-size: .9286em;/*13/14*/
	font-weight: normal;
}

#content.form #focus_areas> legend, #content.form #beneficiaries > legend, #content.form #involved > legend, #content.form #partners_set > legend, #content.form #counties legend, #content.form #durations > legend {
	max-width: 90%;
	font-size: 0.8125em;
	font-weight: bold;
}

#content.form #counties > legend > span {
	display: block;
	font-size: 1.07692em;
}


#content.form form {
	width: 100%;
/*	padding-top: 60px;*/
	font-weight: bold;
	position: relative;
}


#content.form #p_name.row > label {font-size: 0.875em}
#content.form #p_name.row input {width: 600px;}

#content.form label {
	display: block;
	width: 90%;
}

#content.form #tangible_txt > label, #content.form #city_town_area_row > label {font-size: 0.8125em;}


#content.form #p_name.row > label {font-size: 0.875em; font-weight: bold;}
#content.form #p_name.row input {width: 600px;}
#content.form .numbered span {display: inline; margin: 0;}


#content.form label > span {
	font-size: 0.923em /* 12/13 */;
}

#content.form #web_url_label span {
	font-weight: normal;
}

#content.form #web_url_label span strong {
	font-weight: bold;
}
#content.form #p_name.row > label > span {font-size: 0.9286em /* 13/14 */;}

#content.form #project_leader_name {
	margin-top: 8px;
}
#content.form .checkbox_radio .row {margin-bottom: .35em;}

#content.form .checkbox_radio .partner_type label, #content.form #focus_areas.checkbox_radio .row label, #content.form #beneficiaries.checkbox_radio .row label, #content.form #involved.checkbox_radio .row label {
	display: inline;
	font-size: 	0.8125em;
	font-weight:  normal;
	margin-left: 4px;
}

#content.form #tabs-2 #focus_areas.checkbox_radio .row, #content.form #tabs-2 #beneficiaries.checkbox_radio .row
 {
	display: inline-block;
	width: 40%;
 }

#content.form .checkbox_radio .partner_type {
margin-right: 30px;
/*display: block;
width: 80%;*/
}

#content.form .checkbox_radio .partner_type label
{
	font-weight: bold;
	font-size: 0.8125em;
}

#content.form .checkbox_radio .partner_type input {
	font-size: 0.875em;
}

#content.form .checkbox_radio .partner_names label
{
	display: block;
	font-weight: normal;
	font-size: 0.8125em;
	line-height: 1.2;
}

#content.form #counties.checkbox_radio label
{
	display: inline;
	margin-top:  0;
}

#content.form .checkbox_radio.block {
	margin-bottom: 2em;
}

#content.form .checkbox_radio.block .row {
	display: block;
}


#content.form #counties.checkbox_radio li {
	line-height: 2.25;
}

#content.form #counties.checkbox_radio #all_counties_option {
	margin: 1.5em 0 1.5em 25px;
	width: auto;
}

#content.form #counties.checkbox_radio #county_checkboxes {
	margin-left: 25px;
}

#content.form #counties.checkbox_radio label {
	font-size: 0.875em;
	font-weight: normal;
}

#content.form #counties.checkbox_radio .county_list {
	font-size: .9286em; /* 13 / 13 */
}

#content.form #counties {
	padding-bottom: 40px;
}
#content.form .partner_names label {display: block; margin-top: .5em;}

#content.form form .checkbox_radio legend {font-weight: bold;margin-bottom: 0!important;}

#content.form form .checkbox_radio .row.one_column > label {
	display: inline;
	font-weight: normal;
	margin-left: 4px;
}


#content.form  #save_changes {
	display: block;
	width: 150px;
	margin: 3em auto;
}

#content.form  #save_changes {
	font-size: 0.875em;
	padding: 3px;
	border-radius: 4px 4px 4px 4px;
	border-style: solid;
	border-width: 1px;
	border-color: #000;
	color: #b70101;
}

#content.form  #save_changes:hover {
	border-width: 2px;
	padding: 2px;
		border-color: #b70101;
}

#content.form input  {
	font-size: 0.8125em;
}

#content.form select {
	font-size: 0.8125em;
}


#content.form textarea {
	font-size: 0.8125em;
	font-family: inherit;
}

#content.form form .durations_row.row.one_column {
	font-size: 0.8125em;
}

#content.form #web_url_label, #content.form .row.additional.textarea > label {
	font-size: 0.8125em;
}

#content.form.admin #initials {
	margin-bottom: 24px;
}

#content.form.admin #initials > label {
	font-size: 0.875em;
}

#content.form.admin .checkbox_radio .row {margin: .25em 0;}
#content.form #tabs-2 .checkbox_radio .row, #content.for tabs-3#content.form.admin #tabs-5 .checkbox_radio, #content.form.admin #tabs-5 .select {
	display: inline-block;
	width: 45%;
	vertical-align: top;
}

#content.form #tabs-2 legend {
	line-height: 1.1;
	}

#content.form.admin #tabs-2 .checkbox_radio .row.one_column {
	display: block;
}


#content.form.admin #tabs-5 .select > label, #content.form.admin #tabs-5 .textarea2 > label {
	margin-top: 0;
	font-size: 0.875em;
}


#content.form.admin #tabs-5 .checkbox_radio legend {font-size: 0.875em;}
#content.form.admin #tabs-5 .checkbox_radio label {font-weight:  normal; display: inline; margin: 0;font-size: 0.8125em;}

#content.form.admin .checkbox_radio .row {margin-bottom: 0;}

#content.form.admin #extra_text_fields {margin-top: 24px;}



#content.edit.user {margin-top: 0;}

#content.edit.user #edit_username {display: block; font-size: 0.875em;}

#content.edit.user #edit {margin: 48px 0; font-size: 0.9375em;}

#content.edit.user select {
	font-size: 0.875em;
}

#content.edit.user .project {
	margin: 0 0 .25em 20px;
	list-style: disc;
}

#content.user.form #user_form_netid {
	margin: 2em 0;
}

#content.user.form span {
	font-weight: normal;
}

#content.form #for_admins {
	margin-top: 2em;
	margin-bottom: 2em;
	font-size: 0.9375em;
	font-weight: bold;
}

#content.form form .jqEasyCounterMsg {
	font-weight: normal !important;
}

/*logged in*/

#logged_in {
	background-color: #000;
position: absolute;
top: 0;
left: 0;
width: 100%;
}

#logged_in > li {
	display: inline-block;
	line-height: 2.25;
	font-size: 0.75em;
	color: #dadada;
	margin-left: 6px;
}

#logged_in > li.after:after {
		content: '|';
	font-size: 1.125em;
	font-weight: bold;
	margin-left: 10px;
}

#logged_in > #logged_in_as {
	margin-left: 15px;
}

#logged_in > #user_home {
	margin-left: 70px;
}

#logged_in > #logged_in_as:after {

	margin-left: 10px;
}


#logged_in a {
	color: #FF9D07;
}

#logged_in  a:hover {
	color: #C4DBFF;
	text-decoration: underline;

}

#logged_in > li > #username {
	font-weight: bold;
}

.admin #logged_in #user_home > a {
	color: #dadada;
}

#content.browse_users {padding: 0 20px;}

#content.browse_users #user_list {clear: both;/* margin-top: 2em;*/}

#content.browse_users #user_list thead th {
	font-size: 0.875em;
	padding: 5px;
}

#content.browse_users #user_list tbody th, #content.browse_users #user_list td {
	font-size: 0.8125em;
}

#content.browse_users .left{
	text-align: left;
}

/*Management*/

#content.browse_users #add_user {
	margin-left: 15px;
	font-size: 0.875em;
}

#content.browse_users #add_user img {
	vertical-align: bottom;
}

#content.browse_users .center{
	text-align: center;
}

#content.manage #options {
	min-height: 200px;
	padding-top: 16px;
	padding-bottom: 20px;
	margin-bottom:  50px;
	border-bottom: 1px dashed #999;
}

#content.admin #options {
    border-bottom: 0;
}

#content.manage #project_mgt {
	display: inline-block;
	vertical-align: top;
		width: 47%;
		padding: 10px 10px 32px;
}

#content.manage #user_mgt {
	display: inline-block;
	vertical-align: top;
	width: 42%;
	margin-left: 0;
	border-left: 2px groove #c5c5c5;
	padding: 10px 10px 32px 50px;
}

#content.manage h1 {
	margin: 1em 0;
}

#content.manage #options img {
	margin-right: 3px;
	vertical-align: bottom;
}

#content.manage #options h2 {
	margin: 1em 0 1.5em;
	font-size: 1em;
	font-weight: bold;
}

#content.manage #options li {
	font-size: 0.875em;
	margin-left: 20px;
	margin-bottom: 1.5em;
}

#content.manage #options li > p {
	font-size: .929em;
}

#content.manage #options li li {
	margin-bottom: .25em;
}

#content.manage  #managed_users {
	margin: .5em 0 0 10px;
}

#content.manage #p_name {width: auto;}
#content.manage th, #content.manage td {
	padding: 6px 4px;
	font-size: 0.8125em;
}

#content.manage #proj_leader {
	width: 18%;
}

 #content.manage #proj_updated {
	width: 13%;
 }

#content.manage .minor {
	width: 7%;
}

#content.manage a:hover {
	text-decoration: none;
	color: #554eff;
}

.block {display: block}

#content.manage thead th {padding: 8px 4px;}

#content.manage thead .action {text-align: center;}

#content.manage tbody td {text-align: center; vertical-align: middle;}

#content.manage tbody th+td, #content.manage tbody th+td+td {text-align: left;}

#error_warning img {vertical-align: bottom;}

#contacts {margin-bottom: 1em;}
#contacts .row {margin-left: 24px;}
#contacts #project_leader_row {
	margin-top: 1em;
	margin-left: 20px;
	margin-bottom: .75em;
}

#contacts > legend {
	padding-bottom: 2em;
}
#contacts > #project_leader_fieldset {
	display: block;
	margin: 1em 0 .5em;
	background-color: #fafafa;
	border: 1px dashed #999;
	padding: 10px 0 10px 10px;
	position: relative;
}

#project_leader_row legend {
	position: absolute;
	top: -999em;
	left: -999em;
}

#contacts .row.leadersub {
	margin: 2em 0 1.25em 48px;
}

.error_input {
	padding: 5px 5px;
	background-color: #FFFFCC;
	border: 1px solid #b70701;
}

#content.user.form #fs_roles .login_checked {
	margin-left: 3px;
	margin-right: 5px;
	font-size: 1.5em;}

#content.error p {
	font-size: 0.9375em;
}

#content.delete form, #content.unpublish form {
	margin: 2em 0;
}

#content.delete form input, #content.unpublish form input {margin-top: 1em;font-size: .9375em;}

#contacts #secondary_contact_row.row {
	margin: 2em 0 2em 0px!important;
	position: relative;
	background-color: #fafafa;
	border: 1px dashed #999;
	padding: 20px 0 20px 30px;
}

#content.form .add_user {
	margin-top: 1em;
	margin-left: 0;
	font-size: 0.875em;
	font-weight: normal;
}

#content.form #tabs .add_user > a {
	color: #b70101;
	font-size: .9286em; /* 13/14 */
	font-weight: normal;
}

#content.form #tabs .add_user img {
vertical-align: text-bottom;
}

.ui-dialog .ui-dialog-titlebar .ui-dialog-title h2 {
	font-size: 0.875em;
	font-weight: normal;
	margin-left: 20px;
}

.ui-dialog #user_modal .row {
	margin: .5em 0;
}

.ui-dialog #user_modal label {
	font-size: 0.75em;
}

.ui-dialog #user_modal input {
	width: 90%;
	display: block;
	font-size: 0.75em;
}

.ui-dialog #user_modal #register {
	margin: 1.5em 0 1em;
	width: 150px;
	font-size: 0.75em;
}

.ui-dialog #role_select legend {
	font-size: 0.875em;
}

#modal_errors > li {
	font-size: 0.75em;
}

#role_select_model.ui-dialog-content.ui-widget-content p {
	font-size: 0.875em;
}

#leadername_search, #secondary_contact_search {
		margin-top: 2em;
}

.ac_search {
background-image: url(../images/Search_16.png);
background-position: /*0px 20px*/1% 50%;
background-repeat: no-repeat;
-khtml-opacity: .60;
-moz-opacity: .60;
opacity: .60;
}

.ac_search.no_search_bg {
	background-image: none;
-khtml-opacity: 1;
-moz-opacity: 1;
opacity: 1;
}

#content.form #contacts #project_leader_row:after {
	content: '';
	display: block;
	margin-left: 20px;
	margin-right: 30px;
	height: 3em;
	border-bottom: 1px dashed #9e9e9e;
}

#content.form #contacts .leadersub label {
font-size: .8125em;
}

#leadername_result, #secondary_contact_result {
	display: inline;
	margin-left: 20px;
	font-weight: normal;
	line-height: 1.2;
}

#leader_log, #secondary_contact_log {
	font-weight: normal;
	font-size: 0.8125em;
}

.hilite {
	background: #fff;
	border: 1px solid #ccc;
	padding: 2px;
}

.ok > span, .not_ok > span {
position: absolute;
top: -999em;
left: -999em;
}

.ok:before{
	content: url(../images/Confirm_16x16.png);
	display: inline-block;
	width: 16px;
	vertical-align: bottom;
}

.not_ok:before {
	content: url(../images/Warning_16.png);
	display: inline-block;
	width: 16px;
	vertical-align: bottom;
}



#content.form #secondary_contact_row {
	position: relative;
}

#content.form #secondary_contact_row label > #no_match {
	display: block;
	margin: .5em 0;
	font-weight: normal;
}

#content.form #contacts .clear_field:before {
	content: url(../images/User_Remove_16.png);
	display: inline-block;
	width: 16px;
	margin-right: 3px;
	vertical-align: bottom;
}

#content.form #contacts .clear_field {
	display: inline;
	margin-left: 50px;
	color: #b70101;
	cursor: pointer;
	font-weight: normal;
}

.ui-widget-content .clear_field:hover {
	text-decoration: underline;
}

.dontshow {
	display: none;
}

.show {
	display: block;
}

#content.edit_request p {
	margin-top: 2em;
	font-size: 0.875em;
}

#content.edit_request legend, #content.edit_request span {
	font-weight: bold;
}

#content.edit_request form {
	font-size: 0.875em;
	margin: 2em 0;
}

#content.edit_request form .row{
	margin: 1em 0;

}

#content.edit_request form .submit{
	margin-top: 1.5em;
	font-size: 1em;
}

#content.form .hidden {display: none; height: 0; width: 0;}

label.error {
	color: #b70101;
}
#content.userinfo {padding-top: 32px; margin-bottom: 32px;}
#content.userinfo > ul {
	margin-top: 1.5em;
}

#content.userinfo ul > li {
	font-size: 0.875em;
	line-height: 2;
}

#content.userinfo h3, #content.userinfo h3 + ul, #content.userinfo h3 + ul > li {
	display: inline;
}

#content.userinfo h3 + ul > li {
	font-size: 1em;
}

#content.userinfo h3 + ul li:first-child:after {
	content: ', ';
}

#content.edit input[type='submit']{
	margin: 1em 0 1em;
	font-size: 1em;
	height: 2em;
	width: 5em;
}

.update_tmp {
	font-size: 0.8125em;
	font-weight: bold;
	margin: 2em 0 1em;
}

#content.edit #project_meta {
	border: 1px dashed #ccc;
	padding: .5em.25em;
}

#content.edit #project_meta h2 {
	font-weight: bold;
	margin: 0 0 .5em 0;
	line-height: 1.2;
}


#content.edit #project_meta p {
	margin-bottom: 0;
}

#edit_description {display: none;}

#content.profile .editable {
	margin-bottom: 0;
}
#content.profile .trigger {
	margin-left: 5px;
	padding: 2px 4px;
	font-weight: normal;
	background-color: #e0ddce;
	border: 1px solid #c90;
	border-radius: 4px;
	font-size: 0.857em;
/*	;*/
/*
	text-align: center;
	background-color: #e0ddce;
	font-size: .9286em;


	vertical-align: top;*/
}

#content.profile .trigger:hover {
	background-color: #d4d4d4;
	border-color: #b9b9b9;
	text-decoration: underline;
}

#content.profile input, #content.profile select {
	font-size: 1.2em;
	font-family: monospace;
}

.charcounter {margin-right: 20px;}
button {font-size: 1em;}

#content.profile #project_leader_row button {font-size: 0.8125em;}

#content.profile .request_shorten {
	display: block;
	margin: 1em 0;
	font-size: 0.8125em;
	font-weight: normal;
	padding: 10px;
	border: 1px dashed #b70101;
	background: #d2d8ef;
}

#content.profile .admin_option {
	margin: 1em 0;
	padding: 5px 0;
	background-color: #ddd;
	border-bottom: 2px groove #999;
}

.admin_option a, .admin_option span {
	display: inline-block;
margin-left: 20px;
}

.admin_option.textarea a, .admin_option.textarea span {
	display: inline;
}

.admin_option .label, #content.profile .admin_option h2 {width: 280px; margin-left: 5px;}
#content.profile .admin_option h2 {font-size: 1em;}
#content.profile .admin_option .trigger {margin-left: 20px;font-size: 0.8125em;}
.admin_option.textarea a.trigger {margin-left: 20px;}
#content.profile .admin_option .value {margin-top: 1em;}
#content.profile .admin_option.textarea .value, #content.profile .admin_option.textarea #status_notes.value {
	min-height: 30px;
	width: 80%;
	padding: 3px 10px 10px;
}

.admin_option button, .admin_option select {font-size: 0.8125em;}

.break {
	margin-top: 30px;
	padding-top: 20px;
	border-top: 2px groove #999;
}

.admin_option form select {margin-right: 10px;}
.admin_option form button {margin-left: 10px;}

.admin_option .value.read {background-color: #fff; border: 1px solid #333; padding: 0 5px 10px;}
.admin_option .value.write {background-color: transparent; border: 0}

#content.profile #project_leader_row {display: none; margin-top: -.5em;}

#content.profile #leadername_search, #content.profile  #add_leader_name {font-size: .8125em;}
#content.profile #leadername_search > label {display: block;}
#content.profile  .leader_log {
	margin-bottom: .0;
}

#content.profile .leader_log {margin-bottom: .5em;}
#content.profile  #add_leader_name {margin: 1em 0;}

""")

    @tag("bug94548")
    def test_bug94548_full_code(self):
        # Full text of sample code for bug94548 (can't repro on linux/win)
        self._check_zero_results_show_error(self._bug_94548_full_code, language="Less")

    @tag("bug94548")
    def test_bug94548_partial_code(self):
        # Process randomly-selected initial prefixes of the document above,
        # looking for exceptions (not finding anyway).
        for i in range(20):
            codeLen = len(self._bug_94548_full_code)
            halfLen = codeLen / 2
            pick = int(random.uniform(halfLen, codeLen))
            #sys.stderr.write("Linting %d/%d bytes\n" % (pick, codeLen))
            partialCode = self._bug_94548_full_code[:pick]
            try:
                results = self.csslinter.lint(partialCode, "CSS")
                self.assertTrue(True, "finished linting %d bytes" % (pick,))
                if results:
                    # sys.stderr.write("results: %s\n" % "\n   ".join([str(x) for x in results]))
                    pass
            except:
                self.assertTrue(False, "Got exception while linting %d/%d bytes" % (pick, codeLen))

    unsupported_unrecognized_numeric_unit="got an unsupported or unrecognized numeric unit"

    @tag("bug94652")
    def test_validate_numeric_units(self):
        code = dedent("""\
div {
    margin-top: 1px;    /* ok */
    margin-right: 2pt;  /* ok */
    margin-bottom: 3p; /* wrong */
    margin-left: 4khz; /* syntactically correct, semantically wrong */
}
""")
        self._check_one_result_check_error_on_line(code, self.unsupported_unrecognized_numeric_unit, "p")

    @tag("bug94652")
    def test_validate_numeric_units_02(self):
        code = dedent("""\
div {
    margin-top: 1px;    /* ok */
    margin-right: 2pt;  /* ok */
    margin-bottom: 3pta; /* wrong */
    margin-left: 4khz; /* syntactically correct, semantically wrong */
}
""")
        self._check_one_result_check_error_on_line(code, self.unsupported_unrecognized_numeric_unit, "pta")

    @tag("bug94652")
    def test_validate_numeric_units_03(self):
        suffix = "ptasyntacticallycorrectsemanticallywrongwrong" * 100
        code = dedent("""\
div {
    margin-top: 1px;    /* ok */
    margin-right: 2pt;  /* ok */
    margin-bottom: 3%s; /* wrong */
    margin-left: 4khz; /* syntactically correct, semantically wrong */
}
""" % (suffix,))
        self._check_one_result_check_error_on_line(code, self.unsupported_unrecognized_numeric_unit, suffix)

    @tag("bug94621")
    def test_qualified_selector_internal_error_01(self):
        code = 'input['
        self._check_one_result_check_error_at_eof(code, "expecting an identifier")

    @tag("bug94621")
    def test_qualified_selector_internal_error_02(self):
        code = 'input[test'
        self._check_one_result_check_error_at_eof(code, "expecting one of ], =, ~=, |=, *, $, ^")


    @tag("bug94621")
    def test_qualified_selector_internal_error_03(self):
        code = 'input[test='
        self._check_one_result_check_error_at_eof(code, "expecting an identifier or string")


    @tag("bug94621")
    def test_qualified_selector_internal_error_04(self):
        code = 'input[test="'
        self._check_one_result_check_error_on_line(code, "missing string close-quote", '"')


    @tag("bug94621")
    def test_qualified_selector_internal_error_05(self):
        code = 'input[test="b'
        self._check_one_result_check_error_on_line(code, "missing string close-quote", '"b')

    @tag("bug94621")
    def test_qualified_selector_internal_error_06(self):
        code = 'input[test="b"'
        self._check_one_result_check_error_at_eof(code, "expecting a ']'")


    @tag("bug94621")
    def test_qualified_selector_internal_error_07(self):
        code = 'input[test="b"]'
        self._check_one_result_check_error_at_eof(code, "expecting a block of declarations")

    @tag("bug91721")
    def test_substring_matcher_caret_01(self):
        code = 'E[foo^="bar"] {}'
        for lang in self.langs:
            self._check_zero_results_show_error(code, language=lang)

    @tag("bug91721")
    def test_substring_matcher_dollar_01(self):
        code = 'E[foo$="bar"] {}'
        for lang in ("SCSS",): #self.langs:
            self._check_zero_results_show_error(code, language=lang)

    @tag("bug91721")
    def test_substring_matcher_star_01(self):
        code = 'E[foo*="bar"] {}'
        for lang in self.langs:
            self._check_zero_results_show_error(code, language=lang)

    @tag("bug91721")
    def test_substring_matcher_caret_missing_equal_02(self):
        code = 'E[foo^"bar"] {}'
        for lang in self.langs:
            self._check_one_result_check_error_on_line(code, "expecting '=' after substring operator '^'", '"bar"', language=lang)

    @tag("bug91721")
    def test_substring_matcher_star_missing_equal_02(self):
        code = 'E[foo*"bar"] {}'
        self._check_one_result_check_error_on_line(code, "expecting '=' after substring operator '*'", '"bar"')
        for lang in self.langs:
            self._check_one_result_check_error_on_line(code, "expecting '=' after substring operator '*'", '"bar"', language=lang)

    @tag("bug91721")
    def test_substring_matcher_dollar_missing_equal_02(self):
        code = 'E[foo$"bar"] {}'
        for lang in self.langs:
            self._check_one_result_check_error_on_line(code, "expecting '=' after substring operator '$'", '"bar"', language=lang)

    @tag("bug98538")
    def test_resolution_suffixes(self):
        code = dedent("""\
@media screen and (min-resolution: 2dppx) {
}
@media screen and (min-resolution: 8dpcm) {
}
@media screen and (min-resolution: 16dpi) {
}
""")
        self._check_zero_results_show_error(code)
        # Verify an invalid suffix
        code = dedent("""\
@media screen and (min-resolution: 23dppxdpi) {
}
""")
        self._check_one_result_check_error_on_line(code, "got an unsupported or unrecognized numeric unit:", 'dppxdpi')

    @tag("bug98753") # New numeric extensions
    def test_numeric_types(self):
        extensions = ['turn', 'vmin', 'vmax', 'rem', 'ch', 'vh', 'vw']
        code_template = "div { width: 10%s; }"
        codes = [code_template % ext for ext in extensions]
        for lang in self.langs:
            for code in codes:
                self._check_zero_results_show_error(code, language=lang)
