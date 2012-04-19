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

"""Test RHTML codeintel support."""

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
from citestsupport import CodeIntelTestCase, writefile



log = logging.getLogger("test")


class LexRHTMLTestCase(CodeIntelTestCase):
    lang = "RHTML"

    def test_basic(self):
        self.assertLex(dedent("""
            <html><head><title>foo</title><head> 
            <body>
            <SCE_UDL_TPL_OPERATOR><%</SCE_UDL_TPL_OPERATOR><SCE_UDL_SSL_COMMENTBLOCK># foo </SCE_UDL_SSL_COMMENTBLOCK><SCE_UDL_TPL_OPERATOR>%></SCE_UDL_TPL_OPERATOR>
            <body></html>
        """))


# Access with command
# ci2 test udl RHTMLCpln

class RHTMLCplnTestCase(CodeIntelTestCase):
    lang = "RHTML"

    def test_pass(self):
        self.assertEqual(1, 1)

class RHTMLCpln2TestCase(CodeIntelTestCase):
    lang = "RHTML"
    test_dir = join(os.getcwd(), "tmp")
    
    # Some basic tests patterned on tests in test_ruby
    
    @tag("knownfailure")
    def test_citdl_expr_from_trg(self):
        self.assertCITDLExprIs("<%= z.<|>", "z")

class RHTMLTestCase(CodeIntelTestCase):
    lang = "RHTML"
    test_dir = join(os.getcwd(), "tmp", "rhtml")

    @tag("knownfailure")
    def test_ruby_complete(self):
        # Tests for Ruby mode in UDL files.
        #
        # These are copied and pasted out of the RubyTestCase class.
        # I would have preferred to pull the functions out, add a prolog
        # to each string argument to put the code into Ruby mode,
        # but that doesn't seem easy to do in Python.
        ruby1 = "<%= "
        # New tests
        rails_view_name = "ruby-complete-rails-view-methods"
        object_methods_name = "ruby-complete-object-methods"
        
        self.assertTriggerMatches(ruby1 + "opti", name=rails_view_name)
        self.assertTriggerMatches(ruby1 + "opt", name=rails_view_name)
        self.assertNoTrigger(ruby1 + "op")
        self.assertNoTrigger(ruby1 + "o")
        self.assertNoTrigger(ruby1 + " ")
        self.assertNoTrigger(ruby1 + "\t")
        self.assertNoTrigger(ruby1 + "\n")
        self.assertNoTrigger(ruby1 + " opt")
        self.assertTriggerMatches(ruby1 + "opt", name=rails_view_name)
        self.assertTriggerMatches(ruby1 + "Time.", name=object_methods_name)

        # Tests from existing items
        calltip_sig_name = "ruby-complete-calltip-call-signature"
        self.assertTriggerMatches(ruby1 + dedent("""\
                                                 b2 = String.new("testing")
                                                 b2.between?("""),
                                  name=calltip_sig_name)
        self.assertTriggerMatches(ruby1 + dedent("""\
                                                 require 'fileutils'
                                                 FileUtils::cd("""),
                                  name=calltip_sig_name)
        self.assertTriggerMatches(ruby1 + dedent("""\
                                                 require 'fileutils'
                                                 include FileUtils
                                                 cd("""),
                                  name=calltip_sig_name)
        self.assertNoTrigger(ruby1 + "print 'cd(")  # string
        self.assertNoTrigger(ruby1 + "# cd(") # comment
        self.assertNoTrigger(ruby1 + "if(")   # reserved word
        self.assertNoTrigger(ruby1 + dedent("""\
                                            require 'fileutils'
                                            include FileUtils
                                            cd ("""))  #space
                                                 
        self.assertTriggerMatches(dedent("""<%\
                                         require 'net/imap'
                                         imap = Net::IMAP.new('example.com')
                                         imap."""),
                                  name=object_methods_name)
        self.assertTriggerMatches(dedent("""<%\
                                         class MyClass
                                           def method1(arg1, rest)
                                           end
                                           def method2
                                           end
                                         end
                                         myc = MyClass."""),
                                  name=object_methods_name)
        self.assertTriggerMatches(dedent("""<%\
                                         class MyClass
                                           def method1(arg1, rest)
                                           end
                                           def method2
                                           end
                                         end
                                         myc = MyClass.new
                                         myc."""),
                                  name=object_methods_name)
        
        module_methods_name = "ruby-complete-module-names"
        self.assertTriggerMatches(dedent("""<%\
                                         require 'fileutils'
                                         FileUtils::"""),
                                  name=module_methods_name)
        self.assertTriggerMatches("<%= ActionView::Helpers::DateHelper::",
                                  name=module_methods_name)
        
        instance_vars_name = "ruby-complete-instance-vars"
        class_vars_name = "ruby-complete-class-vars"
        global_vars_name = "ruby-complete-global-vars"
        
        self.assertTriggerMatches("<%= @", name=instance_vars_name)
        self.assertTriggerMatches("<% if @", name=instance_vars_name)
        self.assertTriggerMatches("<%= @@", name=class_vars_name)
        self.assertTriggerMatches("<% if @@", name=class_vars_name)
        self.assertTriggerMatches("<%= $", name=global_vars_name)
        self.assertTriggerMatches("<% if $", name=global_vars_name)
        # These aren't styled as variables
        self.assertNoTrigger("<%# @")
        self.assertNoTrigger("<%# @@")
        self.assertNoTrigger("<%# $")
        self.assertNoTrigger("<%= 'a string: @")
        self.assertNoTrigger("<%= 'a string: @@")
        self.assertNoTrigger("<%= \"a string: @")
        self.assertNoTrigger("<%= \"a string: $")
        

    def _setup_gansta_rhtml_buf(self):
        gangsta_rhtml = join(self.test_dir, "gangsta.rhtml")
        writefile(gangsta_rhtml, dedent("""
            <html>
            <head> <title>this RHTML file has JS and Ruby code</title>
            <script type="application/x-javascript">
                function yoyoyo(span) {
                    //...
                }
            </script>
            </head>
            <body>
            <h1>Gansta Rap</h1>
            <% def spitit
                "word"
               end %>
            <ul> <li onclick="yoyoyo();"><%= spitit %></li> </ul>
            </body>
            </html>
        """))
        gangsta_buf = self.mgr.buf_from_path(gangsta_rhtml, lang="RHTML")
        return gangsta_buf

    def test_multiple_blobs(self):
        lang = "RHTML"
        buf = self._setup_gansta_rhtml_buf()

        rb_blob = buf.blob_from_lang["Ruby"]
        self.failUnless(rb_blob is not None)
        self.failUnless(rb_blob[0].get("name") == "spitit")

        js_blob = buf.blob_from_lang["JavaScript"]
        self.failUnless(js_blob is not None)
        self.failUnless(js_blob[0].get("name") == "yoyoyo")


class Nothing:
    def test_citdl_expr_from_trg(self):
        test_cases = """
            z.<|>                       z
            send(<|>                    send
            foo.instance_of?(<|>        foo.instance_of?
            File.open(<|>               File.open
            Zlib::Deflate.deflate(<|>   Zlib::Deflate.deflate

            # These trigger types are disabled until eval for them is
            # implemented.
            #@assigned.<|>               @assigned
            #@@foo.<|>                   @foo
            #$blah.<|>                   @blah
            
            # Skipping this one for now because we'd need to do the smarter
            # convert-literals-to-class-instance thang first.
            #0.step(<|>                  Numeric.step

            @ingredients.<|>             @ingredients
            @ingredients.has_key?(<|>    @ingredients.has_key?

            # Literals
            0.<|>                       Fixnum
            3.14.<|>                    Float
            1e-6.<|>                    Float
            '...'.<|>                   String
            "...".<|>                   String
            ''.<|>                      String
            "".<|>                      String
            [].<|>                      Array
            {}.<|>                      Hash

            0.step(<|>                  Fixnum.step
            '...'.step(<|>              String.step
            [1,2,3].each(<|>            Array.each
        """
        for line in test_cases.splitlines(0):
            if not line.strip(): continue
            if line.lstrip().startswith("#"): continue
            buffer, expected_citdl_expr = line.split()
            buffer = "<%= " + buffer + "%>"
            self.assertCITDLExprIs(buffer, expected_citdl_expr)

        self.assertCITDLExprIs("<%= z = Zlib::Deflate.new()\nz.<|> %>", "z")



#---- mainline

if __name__ == "__main__":
    unittest.main()


