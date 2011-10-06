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
        self.assertEqual(1, len(results))
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
                self.assertEqual([], results, "Failed to parse file %s (%s), results: %s" % (path, lang, [str(x) for x in results]))

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

    def test_css_import_good_medialist_01(self):
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

    def test_css_import_bad_media_01(self):
        code = '@media'
        self._check_one_result_check_error_at_eof(code, "expecting an identifier for a media list")

    def test_css_import_bad_media_02(self):
        code = '@media ;'
        self._check_one_result_check_error_on_line(code, "expecting an identifier for a media list", ';')

    def test_css_import_bad_media_03(self):
        code = '@media @walrus'
        self._check_one_result_check_error_on_line(code, "expecting an identifier for a media list", '@')

    def test_css_import_bad_media_04(self):
        code = '@media walrus'
        self._check_one_result_check_error_at_eof(code, "expecting '{'")

    def test_css_import_bad_media_05(self):
        code = '@media walrus chomps'
        self._check_one_result_check_error_on_line(code, "expecting '{'", 'chomps')

    def test_css_import_bad_media_06(self):
        code = '@media walrus "chomps"'
        self._check_one_result_check_error_on_line(code, "expecting '{'", '"chomps"')

    def test_css_import_bad_media_07(self): #XXX:Finish
        code = '@media walrus {'
        self._check_one_result_check_error_at_eof(code, "expecting '}'")

    def test_css_import_bad_media_08(self): #XXX:Finish
        code = '@media walrus { "chomps"'
        self._check_one_result_check_error_on_line(code, "expecting a property name", '"chomps"')

    def test_css_import_bad_media_09(self):
        code = '@media abc,'
        self._check_one_result_check_error_at_eof(code, "expecting an identifier")

    def test_css_import_bad_media_10(self):
        code = '@media abc, {'
        self._check_one_result_check_error_on_line(code, "expecting an identifier", '{')

    def test_css_import_bad_media_11(self):
        code = '@media abc, 765 {'
        self._check_one_result_check_error_on_line(code, "expecting an identifier", '765')
        
    def test_css_import_bad_media_12(self):
        code = '@media abc, { color: red; }'
        self._check_one_result_check_error_on_line(code, "expecting an identifier", '{')

    def test_css_good_property_function(self):
        code = dedent("""\
div.flip {
    background-image: -moz-linear-gradient(rgba(0, 255, 0, 0.05), rgba(0, 255, 0, 0.01));
}
""").decode("utf-8")
        self._check_zero_results_show_error(code)

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
""")
        self._check_zero_results_show_error(code)
        
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
@mixin table-base {
  th {
    text-align: center;
    font-weight: bold;
  }
  td, th {padding: 2px;}
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
                                        '', lineNo=3, language="CSS")
        self._check_some_errors_on_line(code,
                        "expecting a class or pseudo-class selector",
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
