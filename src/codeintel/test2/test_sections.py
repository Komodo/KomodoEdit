#!/usr/bin/env python
# coding: utf-8
# Copyright (c) 2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

"""Test the `buf.sections` implementations."""

import os
import sys
import re
from os.path import join, dirname, abspath, exists, basename
from glob import glob
import unittest
from pprint import pprint
import logging

from codeintel2.common import *
from codeintel2.util import indent, dedent, banner, markup_text, unmark_text, lines_from_pos
from codeintel2.environment import SimplePrefsEnvironment

from testlib import TestError, TestSkipped, TestFailed, tag
from citestsupport import CodeIntelTestCase, writefile, override_encoding



log = logging.getLogger("test")


class CitadelTestCase(CodeIntelTestCase):
    def test_python(self):
        lang = "Python"
        content = dedent("""\
            class Blam:
                def pow(self, bb):
                    "pow man!"
                    pass
                def pif(self, aa):
                    pass
        """)
        self.assertSectionIs(0, content, lang,
            lang=lang, title="Blam", line=1, id="Blam", type="class",
            level=0)
        self.assertSectionIs(1, content, lang,
            lang=lang, title="pow", line=2, id="pow", type="function",
            level=1)
        self.assertSectionIs(2, content, lang,
            lang=lang, title="pif", line=5, id="pif", type="function",
            level=1)

    def test_perl(self):
        lang = "Perl"
        content = dedent("""\
            sub foo {
                print "hello world\\n";
            }
            sub bar {
                my ($a, $b) = @_;
            }
        """)
        self.assertSectionIs(0, content, lang,
            lang=lang, title="foo", line=1, id="foo", type="function",
            level=0)
        self.assertSectionIs(1, content, lang,
            lang=lang, title="bar", line=4, id="bar", type="function")

    def test_ruby(self):
        lang = "Ruby"
        content = dedent("""\
            class Foo
                def foo
                    puts "hello"
                end
                def bar
                    42
                end
            end
        """)
        self.assertSectionIs(0, content, lang,
            lang=lang, title="Foo", line=1, id="Foo", type="class",
            level=0)
        self.assertSectionIs(1, content, lang,
            lang=lang, title="foo", line=2, id="foo", type="function",
            level=1)
        self.assertSectionIs(2, content, lang,
            lang=lang, title="bar", line=5, id="bar", type="function",
            level=1)

    def test_php(self):
        lang = "PHP"
        content = dedent("""\
            <?php
            class Foo {
                var $a;
                var $b;
                function display() {
                    echo "This is class Foo\\n";
                    echo "a = ".$this->a."\\n";
                    echo "b = ".$this->b."\\n";
                }
                function mul() {
                    return $this->a*$this->b;
                }
            };
            ?>
        """)
        self.assertSectionIs(0, content, lang,
            lang=lang, title="Foo", line=2, id="Foo", type="class",
            level=0)
        self.assertSectionIs(1, content, lang,
            lang=lang, title="display", line=5, id="display", type="function",
            level=1)
        self.assertSectionIs(2, content, lang,
            lang=lang, title="mul", line=10, id="mul", type="function",
            level=1)

    def test_javascript(self):
        lang = "JavaScript"
        content = dedent("""\
            function foo() {
                alert("hello");
            }
            function bar() {
                // ...
            }
        """)
        self.assertSectionIs(0, content, lang,
            lang=lang, title="foo", line=1, id="foo", type="function")
        self.assertSectionIs(1, content, lang,
            lang=lang, title="bar", line=4, id="bar", type="function")

    @tag("knownfailure", "todo")
    def test_javascript_brace_on_next_line(self):
        lang = "JavaScript"
        content = dedent("""\
            function myfunc()
            {
                alert("myfunc");
            }

            var foo =
            {
              bar: function()
              {
                alert('bar');
              }
            };
            """)
        # Want the section line numbers to be where the "function" is,
        # and not where the opening brace, "{", is.
        self.assertSectionIs(0, content, lang,
            lang=lang, title="myfunc", line=1, id="myfunc", type="function")
        self.assertSectionIs(1, content, lang,
            lang=lang, title="foo", line=6, id="foo", type="class")
        self.assertSectionIs(2, content, lang,
            lang=lang, title="bar", line=8, id="bar", type="function")

    def test_tcl(self):
        lang = "Tcl"
        content = dedent("""\
            namespace eval ::zoo {
                proc moreFeather {} {
                    ::set ::var "I'm a string"
                }
            }
            ::zoo::moreFeather
        """)#'
        self.assertSectionIs(0, content, lang,
            lang=lang, title="zoo", line=1, id="zoo", type="namespace")
        self.assertSectionIs(1, content, lang,
            lang=lang, title="moreFeather", line=2, id="moreFeather",
            type="function")

    @override_encoding("ascii")
    def test_encoding(self):
        """Test encoding related issues with codeintel.
        This will temporarily force the system default encoding to ASCII in
        order to force errors to surface.
        """
        lang = "Python"
        buf, data = self._get_buf_and_data(dedent(u"""\
            # coding: utf-8
            # This is a comment with ůɳíčóďé: â
            class Blam:<1>
                def pow(self, bb):<2>
                    "pow man!"
                    pass
                def pif(self, aa):<3>
                    pass
        """), lang)
        lines = lines_from_pos(buf.accessor.text, data)
        buf.get_sections()
        self.assertSectionIs2(0, buf,
            lang=lang, title="Blam", line=lines[1], id="Blam", type="class",
            level=0)
        self.assertSectionIs2(1, buf,
            lang=lang, title="pow", line=lines[2], id="pow", type="function",
            level=1)
        self.assertSectionIs2(2, buf,
            lang=lang, title="pif", line=lines[3], id="pif", type="function",
            level=1)


class CPPTestCase(CodeIntelTestCase):
    __tags__ = ["regex"]

    def test_cpp(self):
        lang = "C++"
        content = dedent("""\
            class BaseClass { };

            int
            a_function(float f, EmptyClassA e) {
            }

            int main(void)
            {
              return 0;
            }
        """)
        self.assertSectionIs(0, content, lang,
            lang=lang, title="BaseClass", line=1, id="BaseClass",
            type="class")
        self.assertSectionIs(1, content, lang,
            lang=lang, title="a_function", line=3, id="a_function",
            type="function")
        self.assertSectionIs(2, content, lang,
            lang=lang, title="main", line=7, id="main",
            type="function")

    def test_cpp_retval_types(self):
        lang = "C++"
        content = dedent("""\
            char one();
            char* one();
            char** one();
            char * one();
            char ** one();
            char *one();
            char **one();
            SomeClass& one();
        """)
        self.assertNoSections(content, lang)

    @tag("bug78046")
    def test_cpp_function_with_arg_comments(self):
        lang = "C++"
        content = dedent("""\
            static void
            SetTimer(
                Tcl_Time *timePtr)      /* Timeout value, may be NULL. */
            {
                //...
            }
        """)
        self.assertSectionIs(0, content, lang,
            lang=lang, title="SetTimer", line=1, id="SetTimer",
            type="function")

        content = dedent("""\
            static void
            SetTimer2(
                Tcl_Time *timePtr)      // Timeout value, may be NULL.
            {
                //...
            }
        """)
        self.assertSectionIs(0, content, lang,
            lang=lang, title="SetTimer2", line=1, id="SetTimer2",
            type="function")

    def test_cpp_method_initializer(self):
        #raise TestSkipped("Fix this test: either change the declarations to definitions, or make the test fail")
        lang = "C++"
        content = dedent("""\
            class FooClass {
                int foo(GUSIDescriptorTable * table): fTable(table) {};
                GUSIDescriptorTable::iterator & operator++() {};
            }
        """)
        self.assertSectionIs(1, content, lang,
            lang=lang, title="foo", line=2, id="foo",
            type="function")
        self.assertSectionIs(2, content, lang,
            lang=lang, title="operator++", line=3,
            type="function")

    def test_cpp_typedef_struct(self):
        lang = "C++"
        content = dedent("""\
             typedef struct FileState {
                Tcl_Channel channel; /* Channel associated with this file. */
                int fd; /* File handle. */
                int validMask; /* OR'ed combination of TCL_READABLE,
                                * TCL_WRITABLE, or TCL_EXCEPTION: indicates
                                * which operations are valid on the file. */
            } FileState;
        """)
        self.assertSectionIs(0, content, lang,
            lang=lang, title="FileState", line=1, id="FileState",
            type="class")

    # The current function regex still missed class ctors and dtors.
    # Not sure I want to allow them as that change in the regex opens
    # the door for many false-positives.
    @tag("knownfailure")
    def test_cpp_class_methods(self):
        lang = "C++"
        content = dedent("""\
            class XPM {
            public:
                XPM(const char *textForm);
                XPM(const char * const *linesForm);
                ~XPM();
                void Init(const char *textForm);
                char *foo(int a);
            };
        """)
        self.assertSectionIs(0, content, lang, lang=lang,
            title="XPM", line=1, type="class")
        self.assertSectionIs(1, content, lang, lang=lang,
            title="XPM", line=3, type="function")
        self.assertSectionIs(2, content, lang, lang=lang,
            title="XPM", line=4, type="function")
        self.assertSectionIs(3, content, lang, lang=lang,
            title="~XPM", line=5, type="function")
        self.assertSectionIs(4, content, lang, lang=lang,
            title="Init", line=6, type="function")
        self.assertSectionIs(5, content, lang, lang=lang,
            title="foo", line=7, type="function")



class XMLTestCase(CodeIntelTestCase):
    def test_xml(self):
        lang = "XML"
        content = dedent("""\
            <?xml version="1.0"?>
            <people>
                <albert id="a">
                <bertha id="b">
                <carl id="c">
            </people>
        """)
        self.assertSectionIs(0, content, lang,
            lang=lang, id="a", line=3, title="a (albert)",
            type="element")
        self.assertSectionIs(1, content, lang,
            lang=lang, id="b", line=4, title="b (bertha)",
            type="element")
        self.assertSectionIs(2, content, lang,
            lang=lang, id="c", line=5, title="c (carl)",
            type="element")

    def test_html(self):
        lang = "HTML"
        content = dedent("""\
            <?xml version="1.0" encoding="UTF-8"?>
            <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
            <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
            <head>
            </head>
            <body>
                <div id="header">
                    <p id="here">blah</p>
                </div>
                <div id="footer">
                    <p id="here">blah</p>
                </div>
            </body>
            </html>
        """)
        self.assertSectionIs(0, content, lang,
            lang=lang, id="header", line=7, title="header (div)",
            type="element")
        self.assertSectionIs(1, content, lang,
            lang=lang, id="here", line=8, title="here (p)",
            type="element")
        self.assertSectionIs(2, content, lang,
            lang=lang, id="footer", line=10, title="footer (div)",
            type="element")

class OtherTestCase(CodeIntelTestCase):
    def test_css(self):
        lang = "CSS"
        content, pos = unmark_text(dedent(u"""\
            blockquote address:before<1> {
                content: "\2015";
            }

             .remark<2>
            {
                color: #666;
                font-size: smaller;
            }

            #header<3> {
                text-align: center;
            }
        """))
        lines = lines_from_pos(content, pos)
        self.assertSectionIs(0, content, lang,
            lang=lang, id="blockquote address:before", line=lines[1],
            title="blockquote address:before", type="element")
        self.assertSectionIs(1, content, lang,
            lang=lang, id=".remark", line=lines[2],
            title=".remark", type="class")
        self.assertSectionIs(2, content, lang,
            lang=lang, id="#header", line=lines[3],
            title="#header", type="id")
        
    def test_less(self):
        lang = "Less"
        content, pos = unmark_text(dedent(u"""\
            @nice-blue: #5B83AD;
            @light-blue: @nice-blue + #111;
            
            #header<1> {
              color: @light-blue;
              .navigation {
                font-size: 12px;
              }
              .logo {
                width: 300px;
              }
            }
            
            .post a<2> {
              color: #111;
              .bordered;
            }
            
            .my-inline-block() when (@mode=huge)<3> {
                display: inline-block;
              font-size: 0;
            }
            
            #foo (@bg: #f5f5f5, @color: #900)<4> {
                background: @bg;
                color: @color;
            }
        """))
        lines = lines_from_pos(content, pos)
        self.assertSectionIs(0, content, lang,
            lang=lang, id="#header", line=lines[1],
            title="#header", type="id")
        self.assertSectionIs(1, content, lang,
            lang=lang, id=".post a", line=lines[2],
            title=".post a", type="class")
        self.assertSectionIs(2, content, lang,
            lang=lang, id=".my-inline-block", line=lines[3],
            title=".my-inline-block", type="class")
        self.assertSectionIs(3, content, lang,
            lang=lang, id="#foo", line=lines[4],
            title="#foo", type="id")

    def test_rst(self):
        lang = "reStructuredText"
        content = dedent("""\
            Main Header
            ===========
            blah

            Sub Header 1
            ------------
            blah

            Sub Header 2
            ~~~~~~~~~~~~
            blah
        """)
        self.assertSectionIs(0, content, lang,
            lang=lang, id="Main-Header", line=1, title="Main Header",
            type="header")
        self.assertSectionIs(1, content, lang,
            lang=lang, id="Sub-Header-1", line=5, title="Sub Header 1",
            type="header")
        self.assertSectionIs(2, content, lang,
            lang=lang, id="Sub-Header-2", line=9, title="Sub Header 2",
            type="header")

    def test_markdown(self):
        lang = "Markdown"
        content = dedent("""\
            Main Header
            ===========
            blah

            ## Sub Header 1

            blah

            ### Sub Header 2 ###

            blah
        """)
        self.assertSectionIs(0, content, lang,
            lang=lang, id="Main-Header", line=1, title="Main Header",
            type="header")
        self.assertSectionIs(1, content, lang,
            lang=lang, id="Sub-Header-1", line=5, title="Sub Header 1",
            type="header")
        self.assertSectionIs(2, content, lang,
            lang=lang, id="Sub-Header-2", line=9, title="Sub Header 2",
            type="header")

class MultiLangTestCase(CodeIntelTestCase):
    @tag("knownfailure")
    def test_rhtml(self):
        XXX

    def test_html(self):
        lang = "HTML"
        content = dedent("""\
            <?xml version="1.0" encoding="UTF-8"?>
            <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
            <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
            <head>
            <script>
                function foo() {
                    alert('hi from foo');
                }
            </script>
            <style>
                body {
                    background-color: blue;
                }
            </style>
            </head>
            <body>
                <div id="header">
                    <p id="here">blah</p>
                </div>
                <div id="footer">
                    <p id="here">blah</p>
                </div>
            </body>
            </html>
        """)
        self.assertSectionIs(0, content, lang,
            lang="JavaScript", id="foo", line=6, title="foo",
            type="function")
        self.assertSectionIs(1, content, lang,
            lang="CSS", id="body", line=11, title="body",
            type="element")
        self.assertSectionIs(2, content, lang,
            lang=lang, id="header", line=17, title="header (div)",
            type="element")
        self.assertSectionIs(3, content, lang,
            lang=lang, id="here", line=18, title="here (p)",
            type="element")
        self.assertSectionIs(4, content, lang,
            lang=lang, id="footer", line=20, title="footer (div)",
            type="element")

    @tag("css")
    def test_css_in_attr(self):
        lang = "HTML"
        content = dedent("""\
            <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
            <head>
            </head>
            <body style="
                         background: red;
                        ">
                <div style="background-color: blue;">
                    <p id="here">blah</p>
                </div>
            </body>
            </html>
        """)
        # Effective testing that the "style" attributes do NOT get
        # marked as CSS sections.
        self.assertSectionIs(0, content, lang,
            lang=lang, id="here", line=8, title="here (p)",
            type="element")

    @tag("css", "django")
    def test_css_in_attr2(self):
        lang = "Django"  # use Komodo's name for this lang
        content = dedent("""\
            <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
            <head>
            </head>
            <body>
                <div class="totals-num-box" style="background-color: #{{ colors.personal }};">
                    <p id="here">blah</p>
                </div>
            </body>
            </html>
        """)
        # Effective testing that the "style" attributes do NOT get
        # marked as CSS sections.
        self.assertSectionIs(0, content, lang,
            lang="HTML", id="here", line=6, title="here (p)",
            type="element")

    def test_php(self):
        lang = "PHP"
        content = dedent("""\
            <<??>?xml version="1.0" encoding="UTF-8"?>
            <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
            <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
            <head>
            <script>
                function foo() {
                    alert('hi from foo');
                }
            </script>
            <style>
                #header { /* stuff */ }
            </style>
            </head>
            <body>
                <div id="header">
                    <p id="here">blah</p>
                </div>
                <?php
                    function blah() {
                        print_r("<p>hi</p>");
                    }
                    blah();
                ?>
                <div id="footer">
                    <p id="here">blah</p>
                </div>
            </body>
            </html>
        """)
        self.assertSectionIs(0, content, lang,
            lang="JavaScript", id="foo", line=6, title="foo",
            type="function")
        self.assertSectionIs(1, content, lang,
            lang="CSS", id="#header", line=11, title="#header",
            type="id")
        self.assertSectionIs(2, content, lang,
            lang="HTML", id="header", line=15, title="header (div)",
            type="element")
        self.assertSectionIs(3, content, lang,
            lang="HTML", id="here", line=16, title="here (p)",
            type="element")
        self.assertSectionIs(4, content, lang,
            lang="PHP", id="blah", line=19, title="blah",
            type="function")
        self.assertSectionIs(5, content, lang,
            lang="HTML", id="footer", line=24, title="footer (div)",
            type="element")
        
    @tag("css", "mason")
    def test_css_in_mason(self):
        lang = "Mason"
        content = dedent("""\
            <html>
            <head>
                <style type="text/css">
                    h3 { border-width: 1px; }
                    .article { margin-left: 1em; }
                </style>
            </head>
            <body>
              <%class>
              use Date::Format;
              my $date_fmt = "%A, %B %d, %Y  %I:%M %p";
              </%class>
              
              <%args>
              $.article => (required => 1)
              </%args>
              
              <div class="article">
                <h3><% $.article->title %></h3>
                <h4><% time2str($date_fmt, $.article->create_time) %></h4>
                <% $.article->content %>
              </div>
            </body>
            </html>
        """)
        self.assertSectionIs(0, content, lang,
            lang="CSS", id="h3", line=4, title="h3",
            type="element")
        self.assertSectionIs(1, content, lang,
            lang="CSS", id=".article", line=5, title=".article",
            type="class")
        
    @tag("css", "rhtml")
    def test_css_in_rhtml(self):
        lang = "RHTML"
        content = dedent("""\
            <html>
            <head>
              <style type="text/css">
                #content {
                  /* something */
                }
                ul {
                  /* something else */
                }
              </style>
            </head>
            <body>
            <div id="content">
              <ul>
                <% @products.each do |p| %>
                  <li><%=  @p.name %></li>
                <% end %>
              </ul>
            </div>
        """)
        self.assertSectionIs(0, content, lang,
            lang="CSS", id="#content", line=4, title="#content",
            type="id")
        self.assertSectionIs(1, content, lang,
            lang="CSS", id="ul", line=7, title="ul",
            type="element")
        self.assertSectionIs(2, content, lang,
            lang="HTML", id="content", line=13, title="content (div)",
            type="element")
        
    @tag("css", "django")
    def test_css_in_django(self):
        lang = "Django"
        content = dedent("""\
            <html>
            <head>
              <style type="text/css">.hidden { display: none; }</style>
            </head>
            <body>
            </body>
            </html>
        """)
        self.assertSectionIs(0, content, lang,
            lang="CSS", id=".hidden", line=3, title=".hidden",
            type="class")
        
    @tag("css", "mustache")
    def test_css_in_mustache(self):
        lang = "Mustache"
        content = dedent("""\
            <html>
            <head>
              <style type="text/css">.hidden { display: none; }</style>
            </head>
            <body>
            </body>
            </html>
        """)
        self.assertSectionIs(0, content, lang,
            lang="CSS", id=".hidden", line=3, title=".hidden",
            type="class")


#---- mainline

if __name__ == "__main__":
    unittest.main()
