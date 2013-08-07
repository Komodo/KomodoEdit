
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

"""Test some Ruby-specific codeintel handling."""

import os
import sys
import random
import re
from os.path import join, dirname, abspath, exists, basename
from glob import glob
import unittest
import subprocess
import which
import logging
from pprint import pprint, pformat

from codeintel2.util import indent, dedent, banner, markup_text, unmark_text, lines_from_pos

from testlib import TestError, TestSkipped, TestFailed, tag
from citestsupport import CodeIntelTestCase, writefile



log = logging.getLogger("test")



class _BaseTestCase(CodeIntelTestCase):
    """Base class for test cases to run for both pure-Ruby and
    Ruby-in-multilang. Sub-class must implement the following:

        lang = <lang>
        ext = <ext>
    """
    test_dir = join(os.getcwd(), "tmp")

    # Set up some commonly used strings here
    #TODO: this is only used in one test case, move it there
    _var_check_string = dedent("""\
            class C
               def initialize
                 <*>num = 3
                 <*>num.<1>ab
                 <*>string = ""
                 <*>string.<2>conc
                 <*>array = []
                 <*>array.<3>indi
                 <*>hash = {}
                 <*>hash.<4>eac
               end
            end
        """)

    def test_binary_import_1(self):
        content, positions = unmark_text(dedent("""\
            require 'zlib'
            z = Zlib::<1>Deflate.<2>new
            z.<3>def
        """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("class", "Deflate"),
             ("class", "ZStream"),
             ])
        self.assertCompletionsInclude(markup_text(content, pos=positions[2]),
            [("function", "new"),
             ])
        self.assertCompletionsInclude(markup_text(content, pos=positions[3]),
            [("function", "deflate"),
             ("function", "flush"),
             ("function", "params"),
             ])
        
    def _finish_testing_step_calltip(self, markedup_content, implicit=True):
        self.assertCalltipMatches(markedup_content,
        dedent(r"""(?:num.)?step\(.*?\).*?Invokes.*?with the sequence of numbers starting at.*?on each call. The loop finishes.*?when the value to be passed to the block is greater than"""),
                                  flags=re.DOTALL, implicit=implicit)

    # bug 48858
    def test_binary_import_2(self):
        content, positions = unmark_text(dedent("""\
            require 'zlib'
            z = Zlib::<1>Deflate.<2>new
            z.<3>def
        """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("class", "Deflate"),
             ("class", "ZStream"),
             ])
        self.assertCompletionsInclude(markup_text(content, pos=positions[2]),
            [("function", "new"),
             ])
        self.assertCompletionsInclude(markup_text(content, pos=positions[3]),
            [("function", "deflate"),
             ("function", "flush"),
             ("function", "params"),
             ])

    @tag("bug56127")
    def test_binary_include(self):
        content, positions = unmark_text(dedent("""\
            require 'zlib'
            include Zlib
            Zlib::<1>Nothing
            z = Deflate.<2>new
            z.<3>def
        """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("class", "Deflate"),
             ("class", "ZStream"),
             ])
        self.assertCompletionsInclude(markup_text(content, pos=positions[2]),
            [("function", "new"),
             ])
        self.assertCompletionsInclude(markup_text(content, pos=positions[3]),
            [("function", "deflate"),
             ("function", "flush"),
             ("function", "params"),
             ])

    @tag("k4b2", "bug56127", "bug65600", "bug65708")
    def test_include_stmt(self):
        test_dir = join(self.test_dir, "test_include_stmt")
        bar_filename = "bar%s" % self.ext
        bar_content, bar_positions = \
          unmark_text(self.adjust_content(dedent("""\
            require 'foo'
            require 'other.rb'
            fa = FooModule::<1>FooClass.<2>new
            fa.<3>foo_method

            include FooModule
            fb = FooClass.<4>new
            fb.<5>foo_method
            
            fc = Oth<8>erModule::<6>OtherClass.new
            fc.<7>other_method
        """)))
        manifest = [
            ("foo.rb", dedent("""
                module FooModule
                    class FooClass
                        def foo_method
                            "fubar"
                        end
                    end
                end
             """)),
            ("other.rb", dedent("""
                module OtherModule
                    class OtherClass
                        def other_method
                            "other stuff"
                        end
                    end
                end
             """)),
            (bar_filename, bar_content),
        ]
        for file, content in manifest:
            path = join(test_dir, file)
            writefile(path, content)
        bar_buf = self.mgr.buf_from_path(join(test_dir, bar_filename))

        self.assertCompletionsInclude2(bar_buf, bar_positions[1],
            [("class", "FooClass")])
        self.assertCompletionsInclude2(bar_buf, bar_positions[2],
            [("function", "new")])
        self.assertCompletionsInclude2(bar_buf, bar_positions[3],
            [("function", "foo_method")])

        self.assertCompletionsInclude2(bar_buf, bar_positions[4],
            [("function", "new")])
        self.assertCompletionsInclude2(bar_buf, bar_positions[5],
            [("function", "foo_method")])
        
        self.assertCompletionsInclude2(bar_buf, bar_positions[6],
            [("class", "OtherClass")])
        self.assertCompletionsInclude2(bar_buf, bar_positions[7],
            [("function", "other_method")])
        self.assertCompletionsInclude2(bar_buf, bar_positions[8],
            [("namespace", "OtherModule")])

    @tag("k4b2", "bug56127")
    def test_require_include_in_diff_scopes(self):
        test_dir = join(self.test_dir, "test_require_include_in_diff_scopes")
        bar_filename = "bar%s" % self.ext
        bar_content, bar_positions = \
          unmark_text(self.adjust_content(dedent("""\
            require 'foo'
            class C1
              include FooModule
              def f
                x = FooClass.new.<1>foo_method
        """)))
        manifest = [
            ("foo.rb", dedent("""
                module FooModule
                    class FooClass
                        def foo_method
                            "fubar"
                        end
                    end
                end
             """)),
            (bar_filename, bar_content),
        ]
        for file, content in manifest:
            path = join(test_dir, file)
            writefile(path, content)
        bar_buf = self.mgr.buf_from_path(join(test_dir, bar_filename))
        self.assertCompletionsInclude2(bar_buf, bar_positions[1],
            [("function", "foo_method")])

    @tag("bug72417", "knownfailure")
    def test_require_through_three_files(self):
        test_dir = join(self.test_dir, "test_require_through_three_files")
        main_filename = "main%s" % self.ext
        main_content, main_positions = \
          unmark_text(self.adjust_content(dedent("""\
            require 'boy'
            b = Boy.new(12, "Charlie")
            puts b.<1>age
            puts b.<2>sex
            puts b.<3>print_name
        """)))
        manifest = [
            ("boy.rb", dedent("""
                require 'male'
                class Boy < Male
                  attr_accessor :age
                  def initialize(age, name)
                    @age = age
                    super(name)
                  end
                end
             """)),
            ("male.rb", dedent("""
                require 'human'
                class Male < Human
                  def sex
                    'male'
                  end
                end
             """)),
            ("human.rb", dedent("""
                class Human
                    # size of people
                    attr :size, true
                    def name  
                      @name     
                    end
                    def lastname
                      @name.capitalize
                    end
                    # name : name
                    def initialize(name)
                      @name = name
                    end
                    
                    # give mug
                    def print_name(mug)
                      "#{@name} : #{mug}"
                    end
                  end
             """)),
            (main_filename, main_content),
        ]
        for file, content in manifest:
            path = join(test_dir, file)
            writefile(path, content)
        main_buf = self.mgr.buf_from_path(join(test_dir, main_filename))
        self.assertCompletionsInclude2(main_buf, main_positions[1],
            [("function", "age")])
        self.assertCompletionsInclude2(main_buf, main_positions[2],
            [("function", "sex")])
        self.assertCompletionsInclude2(main_buf, main_positions[3],
            [("function", "print_name")])


    @tag("bug72417", "knownfailure")
    def test_require_inherits_required_names(self):
        test_dir = join(self.test_dir, "test_require_inherits_required_names")
        main_filename = "main%s" % self.ext
        main_content, main_positions = \
          unmark_text(self.adjust_content(dedent("""\
            require 'boy'
            #  No need to do this: require 'male'
            m = Male.new("George")
            puts m.<1>print_name
        """)))
        manifest = [
            ("boy.rb", dedent("""
                require 'male'
                class Boy < Male
                  attr_accessor :age
                  def initialize(age, name)
                    @age = age
                    super(name)
                  end
                end
             """)),
            ("male.rb", dedent("""
                require 'human'
                class Male < Human
                  def sex
                    'male'
                  end
                end
             """)),
            ("human.rb", dedent("""
                class Human
                    # size of people
                    attr :size, true
                    def name  
                      @name     
                    end
                    def lastname
                      @name.capitalize
                    end
                    # name : name
                    def initialize(name)
                      @name = name
                    end
                    
                    # give mug
                    def print_name(mug)
                      "#{@name} : #{mug}"
                    end
                  end
             """)),
            (main_filename, main_content),
        ]
        for file, content in manifest:
            path = join(test_dir, file)
            writefile(path, content)
        main_buf = self.mgr.buf_from_path(join(test_dir, main_filename))
        self.assertCompletionsInclude2(main_buf, main_positions[1],
            [("function", "print_name")])

    def test_stdlib_import_1(self):
        content, positions = unmark_text(dedent("""\
            require 'yaml'
            puts YAML::<1>parse('blah')
        """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("function", "parse")])
        self.assertCompletionsDoNotInclude(markup_text(content, pos=positions[1]),
            [("function", "no_such_func")])

    # bug56228
    def test_stdlib_handle_terse_method_defs(self):
        content, positions = unmark_text(dedent("""\
            require 'yaml'
            puts YAML::<1>parse('blah')
        """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("function", "emitter"), ("function", "generic_parser")])
        self.assertCompletionsDoNotInclude(markup_text(content, pos=positions[1]),
            [("function", "emitter;"), ("function", "generic_parser;")])

    # @tag("bug55417")
    def test_stdlib_import_1_2(self):
        content = dedent("""\
            require 'net/http'
            req = Net::<|>
        """)
        self.assertCompletionsInclude(content,
            [("class", "HTTP"), ("class", "HTTPRequest")])

    # @tag("bug56127")
    def test_stdlib_import_include_1(self):
        content, positions = unmark_text(dedent("""\
            require 'net/http'
            include Net
            req = HTTPGenericRequest.new
            req.<1>method()
        """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("function", "method"),
             ("function", "body"),
             ("function", "path")
             ])

    # class HTTPRequest is resolved in the Net namespace
    # (inside loaded blob net/http), but it inherits from
    # class HTTPGenericRequest.  When we try to resolve the
    # type name HTTPGenericRequest, we no longer know that it
    # was evaluated against namespace net/http::Net, and come
    # up empty-handled.
    # 
    @tag("k4b2", "bug56277") #was 57057 - this is a python bug
    def test_carry_classref_scope(self):
        content = dedent("""\
            require 'net/http'
            req1 = Net::HTTPRequest.new.<|>method
        """)
        self.assertCompletionsInclude(content,
            [("function", "method"),
             ("function", "body"),
             ("function", "path")
             ])

    @tag("bug57077")
    def test_cross_module_classref(self):
        # Test the completion only.
        test_dir = join(self.test_dir, "test_cross_module_classref")
        bar_filename = "bar%s" % self.ext
        bar_content, bar_positions = \
          unmark_text(self.adjust_content(dedent("""\
            require 'b'
            x = B2::C2.new
            y = x.<1>foo_c2(<2>)
        """)))
        manifest = [
            ("a.rb", dedent("""\
                module A1
                  class C1
                    def foo_c1(d,e,f)
                    end
                  end
                end""")),
            ("b.rb", dedent("""\
                module B2
                  require 'a'
                  include A1
                  class C2 < C1
                    def foo_c2(g,h,i)
                    end
                  end
                end""")),
            (bar_filename, bar_content),
            ]
        for file, content in manifest:
            path = join(test_dir, file)
            writefile(path, content)
        bar_buf = self.mgr.buf_from_path(join(test_dir, bar_filename))
        self.assertCompletionsInclude2(bar_buf, bar_positions[1],
            [("function", "foo_c1"), ("function", "foo_c2")])
        self.assertCalltipIs2(bar_buf, bar_positions[2],
                              dedent("foo_c2(g,h,i)"))

    @tag("k4b2", "bug57087")
    def test_imports_multi_level(self):
        content, positions = unmark_text(dedent("""\
            # Import a bunch of modules here, but
            # include them at various points in the hierarchy
            require 'yaml'
            require 'base64'
            require 'net/ftp'
            include YAML
            module MyClient
              include Base64
              module MySubClient
                include Net
                def foo
                  digest = encode64(<1>"abc")
                  digest_x = encode64 <4>"abc"
                end
              end
            end

            obj = MyClient::MySubClient::<2>FTP.new(<3>host, port)
            """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[2]),
            [("class", "FTP"),
             ("function", "foo")])
        ptn =  r'.*?\(bin\).*?Returns the Base64-encoded version of (\+?)(?:str|bin)\1'
        self.assertCalltipMatches(markup_text(content, pos=positions[1]),
            ptn, flags=re.DOTALL)
        self.assertCalltipMatches(markup_text(content, pos=positions[4]),
            ptn, flags=re.DOTALL)
        # The evaluator can't see anything off "FTP"
        #sys.stderr.write("calltip 3: %r\n\n" % markup_text(content, pos=positions[3]))
        #self.assertCalltipMatches(markup_text(content, pos=positions[3]),
        #    r'.*?Enters exclusive section', flags=re.DOTALL)

    @tag("bug56277")
    def test_stdlib_class_association(self):
        content, positions = unmark_text(dedent("""\
            require 'net/http'
            req = Net::<2>HTTPRequest.<3>new
            req.<4>
        """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[2]),
            [("class", "HTTP"), ("class", "HTTPRequest")])
        self.assertCompletionsInclude(markup_text(content, pos=positions[3]),
            [("function", "new")])
        self.assertCompletionsDoNotInclude(markup_text(content, pos=positions[3]),
            [("function", "no_such_func")])
        self.assertCompletionsInclude(markup_text(content, pos=positions[4]),
            [("function", "body"),
             ("function", "body="),
             ("function", "path")])

    @tag("bug57308")
    def test_stdlib_import_deep(self):
        content, positions = unmark_text(dedent("""\
            require 'net/http'
            require 'net/ftp'
            puts Net::<1>HTTP.<2>get()
            puts Net::FTP.<3>get()
        """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("class", "HTTP"), ("class", "FTP")])
        self.assertCompletionsInclude(markup_text(content, pos=positions[2]),
            [("function", "get")])
        self.assertCompletionsDoNotInclude(markup_text(content, pos=positions[2]),
            [("function", "wombawombawomba")])

    def test_namespace_simple(self):
        content, positions = unmark_text(dedent("""\
            module A
              class B
                def b1(y, z)
                end
              end
              class C
                def c1(x)
                end
              end
              class D < A::B
                def bar
                end
              end
            end
            A::<1>B.new.<2>b1(<3>1)
            A::C.new.<4>c1(<5>2)
            A::D.new.<6>b1(<7>3)
       """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("class", "B"), ("class", "C")])
        self.assertCompletionsInclude(markup_text(content, pos=positions[2]),
            [("function", "b1")])
        self.assertCalltipIs(markup_text(content, pos=positions[3]),
            "b1(y, z)")
        self.assertCompletionsInclude(markup_text(content, pos=positions[4]),
            [("function", "c1")])
        self.assertCalltipIs(markup_text(content, pos=positions[5]),
            "c1(x)")
        self.assertCompletionsInclude(markup_text(content, pos=positions[6]),
            [("function", "b1")])
        self.assertCalltipIs(markup_text(content, pos=positions[7]),
            "b1(y, z)")

    #XXX Merge all the different sub-tests in test_module_internal_include
    #    when they're all passing.

    @tag("bug68427")
    def test_module_internal_include_0(self):
        content, positions = unmark_text(dedent("""\
            require 'logger'
            log = Logger.new
            log.<1>level = Logger::<2>Debug
            log.<1>level = Logger::Severity::<3>Info
            """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("function", "level"), ("function", "level=")])
        self.assertCompletionsInclude(markup_text(content, pos=positions[2]),
            [("namespace", "Severity")])

    @tag("knownfailure", "bug68427")
    def test_module_internal_include_1(self):
        content, positions = unmark_text(dedent("""\
            require 'logger'
            log = Logger.new
            log.<1>level = Logger::<2>Debug
            log.<1>level = Logger::Severity::<3>Info
            """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[2]),
            [("variable", "Debug")])

    @tag("knownfailure", "bug68427")
    def test_module_internal_include_2(self):
        content, positions = unmark_text(dedent("""\
            require 'logger'
            log = Logger.new
            log.<1>level = Logger::<2>Debug
            log.<1>level = Logger::Severity::<3>Info
            """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[3]),
            [("variable", "Debug")])

    # This test should be run to verify that the evaluator
    # is catching loops.
    @tag("potentialloop")
    def test_module_recursion_check_1(self):
        content, positions = unmark_text(dedent("""\
            module A
              class B < A::B
                def bar
                end
              end
            end
            A::B.new.<1>gleep(<2>
            """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("function", "bar")])
        self.assertCompletionsDoNotInclude(markup_text(content, pos=positions[1]),
            [("function", "gleep")])

    # This test should be run to verify that the evaluator
    # is catching loops.  It can never succeed.
    def test_module_recursion_check_2(self):
        content, positions = unmark_text(dedent("""\
            module A
              class B < A::B # Error but we need to deal with it
                def bar(x,y)
                end
              end
            end
            A::B.new.<1>bar(<2>
            """))
        self.assertCalltipIs(markup_text(content, pos=positions[2]),
            "bar(x,y)\nError but we need to deal with it")

    def test_var_assignment(self):
        # As brought up on 10-Oct-2006 "Ruby Code Tip" post ot
        # komodo-beta.
        content, positions = unmark_text(dedent("""\
            a = Array.<1>new
            puts a.<2>class
            b = a
            puts b.<3>class
            """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("function", "new")])
        self.assertCompletionsInclude(markup_text(content, pos=positions[2]),
            [("function", "at"), ("function", "class")])
        self.assertCompletionsInclude(markup_text(content, pos=positions[3]),
            [("function", "flatten!"), ("function", "class")])

    @tag("knownfailure")
    def test_loop_var_type_inference(self):
        # As brought up on 10-Oct-2006 "Ruby Code Tip" post ot
        # komodo-beta.
        content, positions = unmark_text(dedent("""\
            file.each_line do |line|
                puts line.<1>split
            end
            """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("function", "split")])

    def test_loop_var_recursive_dependencies(self):
        content, positions = unmark_text(dedent("""\
            a = b
            b = c
            c = d
            d = a
            a.<1>class
            """))
        # Everything is an object, but this should fail.
        self.assertCompletionsAre(markup_text(content, pos=positions[1]), None)

    def test_loop_var_recursive_dependencies_calltips(self):
        content, positions = unmark_text(dedent("""\
            #XXX Should be aliases.
            a = b
            b = c
            c = d
            d = a
            a(<1>1)
            """))
        # Everything is an object, but this should fail.
        self.assertCalltipIs(markup_text(content, pos=positions[1]), None)

    def test_curr_calltip_arg_range(self):
        # Python's equivalent test case covers paren-based calltips.
        # We'll just test a couple to make sure things are turned on for
        # Ruby.

        # Assert can deal with calltip with no args.
        self.assertCurrCalltipArgRange("foo(<+><|>", "foo()", (0,0))
        self.assertCurrCalltipArgRange("foo(<+>blah<|>", "foo()", (0,0))
        self.assertCurrCalltipArgRange("foo(<+>one, two<|>", "foo()", (0,0))
        self.assertCurrCalltipArgRange("foo(<+>blah)<|>", "foo()", (-1,-1))

        # Should still be able to terminate properly if no signature to
        # work with.
        self.assertCurrCalltipArgRange("foo(<+><|>", "not a signature", (0,0))
        self.assertCurrCalltipArgRange("foo(<+>blah<|>", "not a signature", (0,0))
        self.assertCurrCalltipArgRange("foo(<+>blah)<|>", "not a signature", (-1,-1))

        self.assertCurrCalltipArgRange("foo(<+><|>", "foo(a, b, c)", (4,5))
        self.assertCurrCalltipArgRange("foo(<+>art<|>", "foo(a, b, c)", (4,5))
        self.assertCurrCalltipArgRange("foo(<+>art,<|>", "foo(a, b, c)", (7,8))
        self.assertCurrCalltipArgRange("foo(<+>art,bla,<|>", "foo(a, b, c)", (10,11))

        # Currently commas in regex's *will* screw up determination.
        # Best way to handle that would be with style info. Or could
        # have a lang-specific dict of block chars -- Perl would have
        # {'/': '/'} in addition to the regulars.
        #self.assertCurrCalltipArgRange("foo(<+>/first,last/, <|>'t,m');",
        #                               "foo(a, b, c)", (7,8))

    @tag("trg")
    def test_preceding_trg_from_pos(self):
        self.assertNoPrecedingTrigger("Foo. <|><$>")
        self.assertNoPrecedingTrigger("Module:: <|><$>")
        self.assertNoPrecedingTrigger("Foo.bar<$>(<|>")
        self.assertNoPrecedingTrigger("Module::bar<$>(<|>")

        self.assertPrecedingTriggerMatches(
            "Foo::bar(Pow::smash('foo<$><|>",
            name="ruby-calltip-call-signature", pos=20)
        self.assertPrecedingTriggerMatches(
            "Foo::bar(Pow::smash<$>('foo<|>",
            name="ruby-calltip-call-signature", pos=9)
        self.assertNoPrecedingTrigger(
            "Foo::bar<$>(Pow::smash('foo<|>")

        self.assertPrecedingTriggerMatches(
            "Foo::bar<|><$>",
            name="ruby-complete-module-names", pos=5)
        self.assertNoPrecedingTrigger(
            "Foo<$>::bar<|>")

        self.assertPrecedingTriggerMatches(
            "$foo.bar<|><$>",
            name="ruby-complete-object-methods", pos=5)
        self.assertNoPrecedingTrigger(
            "$foo<$>.bar<|>")

        self.assertPrecedingTriggerMatches(
            dedent("""\
                Foo::bar(  # try to (screw ' {] ) this up
                    Pow::smash('foo<$><|>
            """),
            name="ruby-calltip-call-signature", pos=57)
        self.assertPrecedingTriggerMatches(
            dedent("""\
                Foo::bar(  # try to (screw ' {] ) this up
                    Pow::smash<$>('foo<|>
            """),
            name="ruby-calltip-call-signature", pos=9)

        # Test in a comment.
        self.assertNoPrecedingTrigger(
            dedent("""\
                #
                # Foo::bar(
                #    Pow::smash<$>('foo<|>
                #
            """))

        # Test out-of-range calltip
        self.assertPrecedingTriggerMatches(
            "foo(bar('hi'), <|><$>",
            name="ruby-calltip-call-signature", pos=4)

        # Test 'require' stmt completions.
        self.assertPrecedingTriggerMatches("require 'foo<$><|>",
            name="ruby-complete-lib-paths", pos=9)
        self.assertPrecedingTriggerMatches('require "foo<$><|>',
            name="ruby-complete-lib-paths", pos=9)
        self.assertPrecedingTriggerMatches('require("foo<$><|>',
            name="ruby-calltip-call-signature", pos=8)
        self.assertPrecedingTriggerMatches('require "foo<$><|>',
            name="ruby-complete-lib-paths", pos=9)
        self.assertPrecedingTriggerMatches('require <$>"foo<|>',
            name="ruby-calltip-call-signature", pos=8)

        self.assertPrecedingTriggerMatches("require 'foo/bar<$><|>",
            name="ruby-complete-lib-subpaths", pos=13)
        self.assertPrecedingTriggerMatches("require 'foo<$>/bar<|>",
            name="ruby-calltip-call-signature", pos=8)
        self.assertPrecedingTriggerMatches('require "foo/bar<$><|>',
            name="ruby-complete-lib-subpaths", pos=13)
        self.assertPrecedingTriggerMatches('require "foo<$>/bar<|>',
            name="ruby-calltip-call-signature", pos=8)

    @tag("trg", "bug70627", "knownfailure")
    def test_preceding_with_numeric_fails(self):
        self.assertPrecedingTriggerMatches(
            "c.command2k<$><|>",
            name="ruby-complete-object-methods", pos=2)

    @tag("trg")
    def test_preceding_trg_object_methods(self):
        name="ruby-complete-object-methods"
        self.assertPrecedingTriggerMatches("Foo.<$>cla<|>",
                                           name=name, pos=4)

    @tag("trg")
    def test_preceding_trg_complete_names(self):
        name = "ruby-complete-names"
        ct_name = "ruby-calltip-call-signature"
        content_base = dedent("""
        varname1 = 10
        varname2 = 20
        varname3 = 30
        """)
        suffix = list("ame3")
        prefix = "puts v<$>"
        all_names = ['varname1', 'varname2', 'varname3']
        all_names = [('variable', x) for x in all_names]
        for i in range(1, 5):
            content = ("%s\nputs varn<$>%s<|>%s" %
                       (content_base,
                        "".join(suffix[0:i - 1]),
                        "".join(suffix[i - 1:])))
            code, positions = unmark_text(content)
            start_pos = positions["start_pos"] - 4
            self.assertPrecedingTriggerMatches(content,
                                               name=ct_name, pos=start_pos)
            self.assertCompletionsAre(content, all_names, implicit=False);
            
    @tag("trg")
    def test_hit_class_calltip(self):
        code = dedent("""\
            # null line due to rhtml codeintel bug on line 1
            class SampleClass <1>
            end
            
            d = SampleClass(<2>)
            e = SampleClass <3>
            f = 10
            # Now create a bogus calltip on f, which gets mapped to
            # class Fixnum, and then filtered out because classes
            # don't have calltips
            f <4> = (<5>3 + 5) * 10 # Verify calltips don't trigger on all parens
        """)
        fixed_code, positions = unmark_text(code)
        # unroll the loop to see where test failures occur
        trg_name = "ruby-calltip-call-signature"
        this_code = markup_text(fixed_code, pos=positions[1])
        if self.heredoc_support:
            self.assertNoTrigger(this_code)
        else:
            self.assertTriggerMatches(this_code, name=trg_name)
            self.assertCalltipIs(this_code,
                                 None)
            
        self.assertTriggerMatches(markup_text(fixed_code, pos=positions[2]), name=trg_name)
        self.assertCalltipIs(markup_text(fixed_code, pos=positions[2]),
                             None)
        
        self.assertTriggerMatches(markup_text(fixed_code, pos=positions[3]), name=trg_name)
        self.assertCalltipIs(markup_text(fixed_code, pos=positions[3]),
                             None)
        
        self.assertTriggerMatches(markup_text(fixed_code, pos=positions[4]), name=trg_name)
        self.assertCalltipIs(markup_text(fixed_code, pos=positions[4]),
                             None)

        self.assertNoTrigger(markup_text(fixed_code, pos=positions[5]))

    @tag("trg", "explicitName")
    def test_preceding_trg_complete_keyword(self):
        name = "ruby-complete-names"
        
        self.assertPrecedingTriggerMatches(
            "# test starts on line 2.\n<$>clas<|>",
            name=name, pos=25)
        
        ct_name = "ruby-calltip-call-signature"
        content_base = dedent("""
        varname1 = 10
        varname2 = 20
        varname3 = 30
        """)
        suffix = list("ame3")
        prefix = "puts v<$>"
        all_names = ['varname1', 'varname2', 'varname3']
        all_names = [('variable', x) for x in all_names]
        for i in range(1, 5):
            content = ("%s\nputs varn<$>%s<|>%s" %
                       (content_base,
                        "".join(suffix[0:i - 1]),
                        "".join(suffix[i - 1:])))
            code, positions = unmark_text(content)
            start_pos = positions["start_pos"] - 4
            self.assertPrecedingTriggerMatches(content,
                                               name=ct_name, pos=start_pos)
            self.assertCompletionsAre(content, all_names, implicit=False);

            
    @tag("trg", "knownfailure")
    # This won't work until we implement global-name lists
    def test_preceding_trg_global_names(self):
        all_names = [
                     ('class', 'Clipper'),
                     ('class', 'Exception'),
                     ('function', 'require'),
                     ('variable', 'buzz')]
        name = "ruby-complete-names"
        content = dedent("""
        buzz = 10
        class Clipper
           def moose
           end
        end
        <$><|>
        """)
        code, positions = unmark_text(content)
        start_pos = positions["pos"] - 1
        self.assertPrecedingTriggerMatches(content, name=name, pos=start_pos)
        self.assertCompletionsInclude(content, all_names, implicit=False);
        

    def test_preceding_trg_complete_names_test1(self):
        name = "ruby-complete-names"
        content = dedent("""
        varname1 = 10
        varname2 = 20
        varname3 = 30
        puts v<$>arna<|>me3
        """)
        all_names = [('variable', x) for x in ['varname1', 'varname2', 'varname3']]
        self.assertCompletionsAre(content, all_names, implicit=False);

    #XXX Combine all bug68454 passing tests into one test as the problems
    # are fixed.
    
    @tag("trg", "bug68454")
    def test_no_complete_names_trg_in_blocks_01(self):
        self.assertNoTrigger("[1].each {|xyz<|>")
        self.assertNoTrigger("[1].each do |xyz<|>")
        self.assertNoTrigger("[1].each {|abc, xyz<|>")
        self.assertNoTrigger("[1].each do |abc, xyz<|>")
        self.assertNoTrigger("[1].each {\n|xyz<|>")
        self.assertNoTrigger("[1].each do \n |xyz<|>")
        self.assertNoTrigger("[1].each {\n |abc, xyz<|>")
        self.assertNoTrigger("[1].each do \n |abc, xyz<|>")
        self.assertNoTrigger("[1].each {\n |abc, \n xyz<|>")
        self.assertNoTrigger("[1].each do \n |abc, \n xyz<|>")

    @tag("trg")
    def test_complete_names_triggers(self):
        name = "ruby-complete-names"
        ctip = "ruby-calltip-call-signature"
        self.assertNoTrigger("<|>")
        self.assertNoTrigger(" <|>")
        self.assertNoTrigger(". <|>")
        self.assertNoTrigger("v<|>")
        self.assertTriggerMatches("v <|>", name=ctip)
        self.assertNoTrigger("va<|>")
        self.assertTriggerMatches("va <|>", name=ctip)
        self.assertTriggerMatches("val<|>", name=name)
        self.assertTriggerMatches("val <|>", name=ctip)
        self.assertNoTrigger("vali<|>")
        self.assertTriggerMatches("vali <|>", name=ctip)
        
    @tag("trg")
    def test_complete_names_explicit_triggers(self):
        name = "ruby-complete-names"
        self.assertTriggerMatches("val<|>", name=name, implicit=False)
        self.assertTriggerMatches("va<|>", name=name, implicit=False)
        self.assertTriggerMatches("v<|>", name=name, implicit=False)
        empty_doc = "<|>"
        self.assertNoTrigger(empty_doc, implicit=False)

    @tag("trg", "knownfailure")
    def test_complete_names_explicit_triggers_empty_code(self):
        name = "ruby-complete-names"
        # This now fails
        self.assertTriggerMatches(" <|>", name=name, implicit=False)

    @tag("trg")
    def test_trg_complete_object_methods(self): # FOO.|
        name = "ruby-complete-object-methods"
        # Test with various surrounding whitespace.
        self.assertTriggerMatches("foo.", name=name)
        self.assertTriggerMatches("\nfoo.", name=name)
        self.assertTriggerMatches(" foo.", name=name)
        self.assertTriggerMatches("\n foo.<|>\n", name=name)
        # Trigger with various surrounding context.
        self.assertTriggerMatches("Foo.", name=name)
        self.assertTriggerMatches("@foo.", name=name)
        self.assertTriggerMatches("@@foo.", name=name)
        self.assertTriggerMatches("::foo.", name=name)
        self.assertNoTrigger("(foo + 1).")
        self.assertNoTrigger("foo .")
        self.assertNoTrigger("foo\t.")
        self.assertNoTrigger("foo\n.")
        self.assertTriggerMatches("foo2.", name=name)
        # Don't trigger in a string.
        self.assertNoTrigger("\nbar = 'foo.<|>\n")
        self.assertNoTrigger('\nbar = "foo.<|>\n')
        self.assertNoTrigger("\nbar = 'foo.<|>baz'\n")
        self.assertNoTrigger('\nbar = "foo.<|>baz"\n')
        # Don't trigger in a comment.
        self.assertNoTrigger("\n# foo.<|>\n")

        hdoc = dedent("""\
            string = <<END_OF_STRING
            foo.<|>
            END_OF_STRING
            """)
        if self.heredoc_support:
            self.assertNoTrigger(hdoc)
        else:
            self.assertTriggerMatches(hdoc, name=name)

    @tag("trg")
    def test_trg_complete_lib_paths(self):
        # require '|
        # require "|
        name = "ruby-complete-lib-paths"
        self.assertTriggerMatches("require '<|>", name=name)
        self.assertTriggerMatches('require "<|>foo', name=name)
        self.assertTriggerMatches("require  '<|>", name=name)
        self.assertTriggerMatches('require  "<|>foo', name=name)
        self.assertTriggerMatches("require\t'<|>", name=name)
        self.assertTriggerMatches('require\t"<|>foo', name=name)
        self.assertTriggerMatches("\nrequire '<|>", name=name)
        self.assertTriggerMatches('\nrequire "<|>foo', name=name)

        self.assertNoTrigger("equire '<|>")
        self.assertNoTrigger('equire "<|>foo')
        self.assertNoTrigger("\nrrequire '<|>")
        self.assertNoTrigger('\nrrequire "<|>foo')
        self.assertNoTrigger("\n;require '<|>")
        self.assertNoTrigger('\n;require "<|>foo')

    def test_complete_lib_paths(self):
        self.assertCompletionsInclude("require '<|>'",
            [('module', 'cgi'), ('directory', 'yaml')])
        self.assertCompletionsInclude('require "<|>"',
            [('module', 'cgi'), ('directory', 'yaml')])
        self.assertCompletionsInclude("\nrequire '<|>'",
            [('module', 'cgi'), ('directory', 'yaml')])
        self.assertCompletionsInclude(" require '<|>'",
            [('module', 'cgi'), ('directory', 'yaml')])
        #self.assertCompletionsAre("require '<|>'", [('foo', 'bar')])
                #"lib-paths",                # require '|, require "|
                #"lib-subpaths",             # require 'foo/|, require "foo/


    @tag("trg")
    def test_trg_complete_lib_subpaths(self):
        # require 'foo/|
        # require "foo/|
        name = "ruby-complete-lib-subpaths"
        self.assertTriggerMatches("require 'foo/<|>", name=name)
        self.assertTriggerMatches('require "foo/<|>bar', name=name)
        self.assertTriggerMatches("require  'foo/<|>", name=name)
        self.assertTriggerMatches('require  "foo/<|>bar', name=name)
        self.assertTriggerMatches("require\t'foo/<|>", name=name)
        self.assertTriggerMatches('require\t"foo/<|>bar', name=name)
        self.assertTriggerMatches("\nrequire 'foo/<|>", name=name)
        self.assertTriggerMatches('\nrequire "foo/<|>bar', name=name)

        self.assertNoTrigger("equire 'foo/<|>")
        self.assertNoTrigger('equire "foo/<|>bar')
        self.assertNoTrigger("\nrrequire 'foo/<|>")
        self.assertNoTrigger('\nrrequire "foo/<|>bar')
        self.assertNoTrigger("\n;require 'foo/<|>")
        self.assertNoTrigger('\n;require "foo/<|>bar')

        # Don't trigger in comments, here docs, etc.
        self.assertNoTrigger('# require "foo/<|>bar')

        # Don't trigger in a non string.
        self.assertNoTrigger('require foo/<|>')

        hdoc = dedent("""\
            string = <<END_OF_STRING
            require "foo/<|>"
            END_OF_STRING
        """)
        if self.heredoc_support:
            self.assertNoTrigger(hdoc)
        else:
            self.assertTriggerMatches(hdoc, name=name)
        
    def test_complete_lib_subpaths(self):
        candidates = [('module', 'ftp'), ('module', 'http')]
        self.assertCompletionsInclude("require 'net/<|>'",
            candidates)
        self.assertCompletionsInclude("\nrequire 'net/<|>'",
            candidates)
        self.assertCompletionsInclude(" require 'net/<|>'",
            candidates)


    #TODO: should this be re-enabled or removed?
    def DISABLED_test_complete_available_modules(self): # include |
        name = "ruby-complete-available-modules"
        self.assertTriggerMatches("include <|>", name=name)
        self.assertTriggerMatches(" include <|>", name=name)
        self.assertTriggerMatches("\ninclude <|>", name=name)

        # Edge cases
        self.assertNoTrigger("e <|>")
        self.assertNoTrigger(" <|>")

        # Don't trigger in comments, here docs, etc.
        self.assertNoTrigger("# include <|>")
        self.assertNoTrigger("'include <|>")
        self.assertNoTrigger("foo = 'include <|>")
        hdoc = dedent("""\
            string = <<END_OF_STRING
                include <|>
            END_OF_STRING
            """)
        if self.heredoc_support:
            self.assertNoTrigger(hdoc)
        else:
            self.assertTriggerMatches(hdoc, name=name)

    #TODO: should this be re-enabled or removed?
    def DISABLED_test_complete_available_modules_and_classes(self):
        name = "ruby-complete-available-modules-and-classes"
        self.assertTriggerMatches("class Foo < ", name=name)
        self.assertTriggerMatches("class Foo < <|>", name=name)
        self.assertTriggerMatches(" class Foo < <|>", name=name)
        self.assertTriggerMatches(" class  Foo  < <|>", name=name)
        self.assertTriggerMatches("\n\tclass\tFoo  < <|>", name=name)

        self.assertNoTrigger("\n\tclass\tFoo  <\t<|>")

        # Edge cases
        self.assertNoTrigger("< <|>")
        self.assertNoTrigger(" <|>")

        # Don't trigger in comments, here docs, etc.
        self.assertNoTrigger("# class Foo < <|>")
        self.assertNoTrigger("'class Foo < <|>")
        self.assertNoTrigger("foo = 'class Foo < <|>")
        hdoc = dedent("""\
            string = <<END_OF_STRING
            class Foo < <|>
            END_OF_STRING
        """)
        if self.heredoc_support:
            self.assertNoTrigger(hdoc)
        else:
            self.assertTriggerMatches(hdoc, name=name)

    def test_calltip_call_signature(self): # FOO(
        name = "ruby-calltip-call-signature"
        self.assertTriggerMatches("FOO(<|>", name=name)
        self.assertTriggerMatches("Foo(<|>", name=name)
        self.assertTriggerMatches("foo(<|>", name=name)
        self.assertTriggerMatches("Foo::Bar(<|>", name=name)

        self.assertTriggerMatches("foo (<|>", name=name)
        self.assertTriggerMatches(" foo (<|>", name=name)
        self.assertTriggerMatches("\nfoo (<|>", name=name)
        self.assertTriggerMatches("foo\t(<|>", name=name)
        self.assertTriggerMatches("foo\n(<|>", name=name)
        self.assertTriggerMatches("foo\r\n(<|>", name=name)
        self.assertTriggerMatches(" foo \n \t (<|>", name=name)

        self.assertTriggerMatches("f (<|>", name=name)
        self.assertTriggerMatches("f(<|>", name=name)
        self.assertTriggerMatches("f(<|>", name=name)

        self.assertTriggerMatches("bar = foo(<|>", name=name)
        self.assertTriggerMatches("bar(foo(<|>", name=name)

        self.assertTriggerMatches("foo_(<|>", name=name)
        self.assertTriggerMatches("_(<|>", name=name)
        self.assertTriggerMatches("_foo(<|>", name=name)
        self.assertTriggerMatches("f3(<|>", name=name)

        self.assertNoTrigger("3(<|>")

        # Don't trigger in comments, here docs, etc.
        self.assertNoTrigger("# foo(<|>")
        self.assertNoTrigger("'foo(<|>")
        self.assertNoTrigger("bar = 'foo(<|>")
        hdoc = dedent("""\
            string = <<END_OF_STRING
            require "foo(<|>"
            END_OF_STRING
        """)
        self.assertNoTrigger(hdoc)

        #XXX Can't yet test this because don't have a convenient way to
        #    ensure 'delegate' module is loaded into CIDB.
        #self.assertCalltipIs("require 'delegate'\nDelegator.new(<|>",
        #    dedent("""\
        #    new(..."""))
        
        # This is broken because we don't currently handle actually checking
        # for a class "new" method (having deferred to looking for the more
        # typical "initialize"). Calltip eval *should* fallback to "new".
        #self.assertCalltipIs("require 'zlib'\nZlib::Deflate.new(<|>",
        #    dedent("""\
        #    Zlib::Deflate.new(level=nil, windowBits=nil, memlevel=nil, strategy=nil)
        #    Creates a new deflate stream for compression. See zlib.h for
        #    details of each argument."""))

        #XXX Builtins don't get calltip info
        self._finish_testing_step_calltip("Numeric.step(<|>")

    def test_delayed_type_info(self):
        code = dedent("""\
            class NoType
                attr_reader :unknown
                def foo
                    @unknown = eat_eggs(3, 'type undefined')
                    @unknown.<1>what? # no type info here
                end
            class Foo
                attr_reader :inst
                def foo
                    @inst = 55
                    puts "blah blah blah"
                    @inst.<2>ceil(<3>
                end
            end
        """)
        fixed_code, positions = unmark_text(code)
        self.assertCompletionsAre(
            markup_text(fixed_code, pos=positions[1]),
            None)
        self.assertCompletionsInclude(
            markup_text(fixed_code, pos=positions[2]),
            [("function", "ceil"),])
        self.assertCalltipMatches(markup_text(fixed_code, pos=positions[3]),
        dedent(r"""(?:ceil\().*?Returns the smallest Integer greater than or equal to num\. Class Numeric achieves this by converting itself to a Float then invoking Float#ceil|.*?As `int' is already an Integer, all these methods simply.*?return the receiver\."""),
                                  flags=re.DOTALL)
    #    self.assertCalltipIs(
    #        
    #        dedent("""\
    #int.to_i      => int
    #int.to_int    => int
    #int.floor     => int
    #int.ceil      => int
    #int.round     => int
    #int.truncate  => int
    #As `int' is already an Integer, all these methods simply
    #return the receiver."""))

    def test_fixnum(self):
        ruby_literals, positions = unmark_text(dedent("""
            10.step(<0>1)
            """))
        self._finish_testing_step_calltip(markup_text(ruby_literals, pos=positions[0]))

    @tag("bug60687")
    def test_literals(self):
        #XXX BUG: add a line-continuation to this snippet to have
        #    the first trigger on line *0* and you'll get a failure
        #    about no module rows for <path>#0. There is a 0-based vs.
        #    1-based line problem somewhere.
        # Fixed in change 272648 (bug 62198)?
        ruby_literals, positions = unmark_text(dedent("""
            3.14.<2>class
            1e-6.<3>class
            '...'.<4>class
            "...".<5>class
            ''.<6>class
            "".<7>class
            [].<8>class
            {}.<9>class
        """))
        trg_name = "ruby-complete-literal-methods"

        for marker in range(2, 10):
            self.assertTriggerMatches(
                markup_text(ruby_literals, pos=positions[marker]),
                name=trg_name)
        for marker in (2,3):
            self.assertCompletionsInclude(
                markup_text(ruby_literals, pos=positions[marker]),
                [("function", "abs"),
                 ("function", "div"),
                 ("function", "round")])
        for marker in (4,5,6,7):
            self.assertCompletionsInclude( # String.<|>
                markup_text(ruby_literals, pos=positions[marker]),
                [("function", "capitalize!"),   # String
                 ("function", "capitalize"),    # String
                 ("function", "between?")])     # Comparable
        self.assertCompletionsInclude( # Array.<|>
            markup_text(ruby_literals, pos=positions[8]),
            [("function", "slice!"),        # Array
             ("function", "slice"),         # Array
             ("function", "collect")])      # Enumerable
        self.assertCompletionsInclude( # Hash.<|>
            markup_text(ruby_literals, pos=positions[9]),
            [("function", "key?"),          # Hash
             ("function", "keys"),          # Hash
             ("function", "collect")])      # Enumerable


        ruby_literals, positions = unmark_text(dedent("""
            '...'.downcase(<1>)
            [1,2,3].slice(<2>)
            {}.taint(<3>)
        """))
        ptn = (r'.*?downcase().*?'
             + r'Returns a copy of .?str.? with all uppercase letters replaced.*?'
             + r'with their lowercase counterparts. The operation is locale.*?'
             + r'insensitive---only characters.*?are affected.''')
        self.assertCalltipMatches(
            markup_text(ruby_literals, pos=positions[1]),
            ptn, flags=re.DOTALL)
        self.assertCalltipMatches(
            markup_text(ruby_literals, pos=positions[2]),
            (r'.*?Element Reference---Returns the element at.*?, or.*?'
           + r'returns a subarray starting at .start. and continuing for.*?'
           + r'.length. elements, or returns a subarray specified by.*?'
           + r'range.\. Negative indices count backward from the end of the.*?'
           + r'array \(-1 is the last element\).'), flags=re.DOTALL)
        self.assertCalltipMatches(
            markup_text(ruby_literals, pos=positions[3]),
            (r'.*?taint.*?Marks.*?obj.*?as tainted---if the \$SAFE level is set.*?'
           + r'appropriately, many method calls which might alter the.*?'
           + r'running programs environment will refuse to accept tainted.*?'
           + r'strings.'), flags=re.DOTALL)
        ruby_literals, positions = unmark_text(dedent("""
            # These should trigger.
            ['a', 'b', 'c'].<0>class
            @tk_table_list = [].<1>taint
            foo = [
                1,
                2,
                3
            ].<2>

            # These should not trigger 'literal-methods'
            attributes.collect{|name, value| blah}.<3>to_s
            FileTest.exist?("#{@filename}.<4>#{i}")
            @result = Thread.new { perform_with_block }.<5>value
            @@services[host][port].<6>stop
            foo[blah].<7>bang
            foo2.<8>
        """))
        for marker in (0,1,2):
            self.assertTriggerMatches(
                markup_text(ruby_literals, pos=positions[marker]),
                name=trg_name)
        for marker in (3,4,5,6,7,8):
            self.assertTriggerDoesNotMatch(
                markup_text(ruby_literals, pos=positions[marker]),
                name=trg_name)

    @tag("bug62397")
    def test_literal_fixnums(self):
        # Track bug 
        ruby_literals, positions = unmark_text(dedent("""
            0.<1>class
        """))
        trg_name = "ruby-complete-literal-methods"
        self.assertTriggerMatches(
                markup_text(ruby_literals, pos=positions[1]),
                implicit=False,
                name=trg_name)
        self.assertCompletionsInclude(
                markup_text(ruby_literals, pos=positions[1]),
                [("function", "abs"),
                 ("function", "div"),
                 ("function", "round")],
                implicit=False)
        self.assertNoTrigger(
                markup_text(ruby_literals, pos=positions[1]),
                implicit=True)
        self.assertNoTrigger(
                markup_text(ruby_literals, pos=positions[1]))

        ruby_literals, positions = unmark_text(dedent("""
            10.step(<0>)
        """))
        self._finish_testing_step_calltip(markup_text(ruby_literals, pos=positions[0]), implicit=False)

    def test_hash_var_1(self):
        content = dedent("""
                h = {}
                h.<|>eac""")
        exp_list = [("function", "all?"),
             ("function", "delete_if"),
             ("function", "each")]
        self.assertCompletionsInclude(content, exp_list)

    def _do_std_vars(self, var_check_string):
        vars_string, positions = unmark_text(var_check_string)
        _numeric_members = [("function", "abs"),
             ("function", "zero?")]
        self.assertCompletionsInclude(markup_text(vars_string, pos=positions[1]), _numeric_members)
        _pure_string_members = [("function", "downcase"),
             ("function", "eql?")
            ]
        self.assertCompletionsInclude(markup_text(vars_string, pos=positions[2]), _pure_string_members)
        array_literals = [("function", "all?"),
             ("function", "partition"),]
        self.assertCompletionsInclude(markup_text(vars_string, pos=positions[3]), array_literals)
        hash_literals = [
             ("function", "each_key"),
             ("function", "merge!"),
                             ]
        self.assertCompletionsInclude(markup_text(vars_string, pos=positions[4]), hash_literals)

    def test_std_vars(self):
        # Std vars
        self._do_std_vars(self._var_check_string.replace("<*>", ""))
        # Instance vars
        self._do_std_vars(self._var_check_string.replace("<*>", "@"))
        # Class vars
        self._do_std_vars(self._var_check_string.replace("<*>", "@@"))
        # Global vars
        self._do_std_vars(self._var_check_string.replace("<*>", "$"))

    def test_fruit_salad(self):
        # A bunch of Ruby completion tests based on this snippet.
        ruby_fruit_salad, positions = unmark_text(dedent("""\
            require '<6>yaml/<7>dbm'

            class FruitSalad
              @@times_called = 0
              def initialize(fruits)
                @@times_called += 1
                @ingredients = {}
                @num_served = 0
                add(<4>fruits)
              end
            
              def add(fruits)
                fruits.each do | name, count |
                  @ingredients[name] = 0 unless @ingredients.has_key?(<2>name)
                  @ingredients[name] += count
                end
              end
              
              def accumulate(sum, item)
                sum + item[1]
              end
            
              def servings()
                # Step into a block
                total_fruits = @ingredients.<1>inject(0) {|sum, item| accumulate(sum, item)}
                total_fruits - @num_served
              end
            
              def serve(n=1)
                s = servings
                raise "Not enough fruit -- requested #{n}, have #{s}" if n > s
                @num_served += n
              end
            end
            
            fs = FruitSalad.<5>new(<0>{'apples' => 4, 'bananas' => 3})
            fs.<8>add('peaches' => 3)
        """))
        
        self.assertCalltipIs( # FruitSalad.new(<|>
            markup_text(ruby_fruit_salad, pos=positions[0]),
            "new(fruits)")
        self.assertCompletionsInclude( # @ingredients.<|>
            markup_text(ruby_fruit_salad, pos=positions[1]),
            [("function", "all?"),
             ("function", "delete_if"),
             ("function", "each")])
        self.assertCalltipMatches( # @ingredients.has_key?(<|>
            markup_text(ruby_fruit_salad, pos=positions[2]),
            '.*?Returns true if the given key is present in.*?hsh',
            flags=re.DOTALL)
        self.assertCalltipIs( # add(<|>
            markup_text(ruby_fruit_salad, pos=positions[4]),
            "add(fruits)")
        self.assertCompletionsInclude( # FruitSalad.<|>
            markup_text(ruby_fruit_salad, pos=positions[5]),
            [("function", "new"),])
        self.assertCompletionsInclude( # FruitSalad.<|>
            markup_text(ruby_fruit_salad, pos=positions[8]),
            [("function", "add"),
             ("function", "serve"),
             ("function", "is_a?"),
             ("function", "object_id")])
        self.assertCompletionsInclude( # require '<|>
            markup_text(ruby_fruit_salad, pos=positions[6]),
            [("module", "uri"),
             ("module", "weakref"),
             ("directory", "yaml")])
        self.assertCompletionsInclude( # require 'yaml/
            markup_text(ruby_fruit_salad, pos=positions[7]),
            [("module", "dbm"),
             ("module", "store")])


    def test_complete_module_names(self): # MODULE::
        name = "ruby-complete-module-names"
        self.assertTriggerMatches("Module::<|>", name=name)
        self.assertTriggerMatches("M::<|>", name=name)
        self.assertTriggerMatches("\tModule::<|>", name=name)
        self.assertTriggerMatches("\nModule::<|>", name=name)
        self.assertTriggerMatches(" Module::<|>", name=name)
        self.assertTriggerMatches(" M3::<|>", name=name)

        #XXX These might need to change to actually trigger.
        self.assertNoTrigger("Module ::<|>")
        self.assertNoTrigger("::<|>")

        # Don't trigger in comments, here docs, etc.
        self.assertNoTrigger("# Module::<|>")
        self.assertNoTrigger("'Module::<|>")
        self.assertNoTrigger("bar = 'Module::<|>")

    def DISABLED_test_complete_class_vars(self): # @@|
        name = "ruby-complete-class-vars"
        self.assertTriggerMatches("@@<|>", name=name)
        self.assertTriggerMatches(" @@<|>", name=name)
        self.assertTriggerMatches("\n@@<|>", name=name)
        self.assertTriggerMatches("\t@@<|>", name=name)

        # Don't trigger in comments, here docs, etc.
        self.assertNoTrigger("# @@<|>")
        self.assertNoTrigger("'@@<|>")
        self.assertNoTrigger("bar = '@@<|>")
        hdoc = dedent("""\
            string = <<END_OF_STRING
                @@<|>
            END_OF_STRING
            """)
        if self.heredoc_support:
            self.assertNoTrigger(hdoc)
        else:
            self.assertTriggerMatches(hdoc, name=name)

    def DISABLED_test_complete_instance_vars(self): # @|
        name = "ruby-complete-instance-vars"
        self.assertTriggerMatches("@<|>", name=name)
        self.assertTriggerMatches(" @<|>", name=name)
        self.assertTriggerMatches("\n@<|>", name=name)
        self.assertTriggerMatches("\t@<|>", name=name)

        # Don't trigger in comments, here docs, etc.
        self.assertNoTrigger("# @<|>")
        self.assertNoTrigger("'@<|>")
        self.assertNoTrigger("bar = '@<|>")
        hdoc = dedent("""\
            string = <<END_OF_STRING
                @<|>
            END_OF_STRING
            """)
        if self.heredoc_support:
            self.assertNoTrigger(hdoc)
        else:
            self.assertTriggerMatches(hdoc, name=name)

    def DISABLED_test_complete_global_vars(self): # $|
        name = "ruby-complete-global-vars"
        self.assertTriggerMatches("$<|>", name=name)
        self.assertTriggerMatches(" $<|>", name=name)
        self.assertTriggerMatches("\n$<|>", name=name)
        self.assertTriggerMatches("\t$<|>", name=name)

        # Don't trigger in comments, here docs, etc.
        self.assertNoTrigger("# $<|>")
        self.assertNoTrigger("'$<|>")
        self.assertNoTrigger("bar = '$<|>")
        hdoc = dedent("""\
            string = <<END_OF_STRING
                $<|>
            END_OF_STRING
            """)
        if self.heredoc_support:
            self.assertNoTrigger(hdoc)
        else:
            self.assertTriggerMatches(hdoc, name=name)

    @tag("knownfailure")
    def test_literal_hash(self):
        # Currently the Ruby literal trigger on a hash isn't that useful.
        # The following should work.
        self.assertTriggerMatches("{'abc'=> 1, 'def' => 2}.<|>keys",
                                  name="ruby-complete-literal-methods")
    #    
    #def _assertCompletionsDoNotInclude(self, *args):
    #    try:
    #        self.assertCompletionsInclude(*args)
    #        res = False
    #    except:
    #        res = True
    #    self.assertTrue(res)
    #    
    @tag("knownfailure", "54847")
    def test_numeric_not_complex(self):
        content = dedent("""\
            a = 4
            a.<|>ceil
        """)
        self.assertCompletionsInclude(content, [("function", "ceil")])
        self.assertCompletionsDoNotInclude(content, [("function", "polar")])
        
    def test_numeric_float_missing_nan(self):
        content = "4.2.<|>"
        self.assertCompletionsInclude(content, [("function", "nan?")])
        
    @tag("bug60678")
    def test_exponential_floats_not_recognized(self):
        content, positions = unmark_text(dedent("""
            a3 = 12.3e-4
            a3.<4>class
            """))
        _object_members = [
             ("function", "class"),
             ("function", "clone"),
             ("function", "display"),
             ("function", "dup"),
             ("function", "singleton_methods"),
             ("function", "untaint"),
             ]
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[4]), _object_members)
        
    @tag("knownfailure", "bug62247")
    def test_not_a_number(self):
        content, positions = unmark_text(dedent("""
            puts 12.3e-4e6.<1>class
            """))
        self.assertCompletionsDoNotInclude(
            markup_text(content, pos=positions[1]),
            [("function", "abs")])
        

    def test_everything_is_an_object(self):
        content, positions = unmark_text(dedent("""
            a1 = 42
            a1.<1>class
            a2 = 12.3
            a2.<2>class
            a4 = {}
            a4.<3>keys # Hash
            a5 = "string"
            a5.<4>class
            a6 = [1,2,3]
            a6.<5>class
            """))
        _object_members = [
             ("function", "class"),
             ("function", "clone"),
             ("function", "display"),
             ("function", "dup"),
             ("function", "singleton_methods"),
             ("function", "untaint"),
             ]
        # Verify none of these items include kernel items.
        _kernel_members = [
             ("function", "abort"),
             ("function", "p"),
             ("function", "require"),
            ]
        for i in range(1, 6):
            self.assertCompletionsInclude(
                markup_text(content, pos=positions[i]), _object_members)
            self.assertCompletionsDoNotInclude(
                markup_text(content, pos=positions[i]), _kernel_members)

    # Test completions on literals
    @tag("bug60687")
    def test_literals_2(self):
        content, positions = unmark_text(dedent("""
            42.<1>class
            12.3.<2>class
            12.3e-4.<3>class
            "hi there".<4>tolower
            [1,2,3].<5>each
            {}.<6>keys # Hash
            """))
        # Test basic completions
        _numeric_members = [("function", "abs"),
             ("function", "between?"),
             ("function", "extend"),
             ("function", "floor"),
             ("function", "freeze"),
             ("function", "frozen?"),
             ("function", "zero?")]
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]), _numeric_members,
            implicit=False)
            
        _float_members = [
             ("function", "divmod"),
             ("function", "integer?"),
             ("function", "nonzero?"),
             ## Precision included module dropped in 1.9
             #("function", "prec"),
             #("function", "prec_f"),
             #("function", "prec_i"),
             ("function", "quo"),
             ("function", "remainder"),
                        ]
        _pure_string_members = [
            ("function", "each_byte"),
             ("function", "each_line"),
             ("function", "concat"),
             ("function", "count"),
             ("function", "delete!"),
             ("function", "dump"),
             ("function", "empty?")
            ]
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[2]), _float_members)
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[3]), _float_members)
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[4]), _pure_string_members)
        array_literals = [("function", "all?"),
             ("function", "concat"),
             ("function", "delete"),
             ("function", "fill"),
             ("function", "values_at"),
             ("function", "length"),
             ("function", "partition"),
             ("function", "zip")]
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[5]), array_literals)
        pure_hash_literals = [
             ("function", "each_key"),
             ("function", "each_pair"),
             ("function", "each_value"),
             ("function", "each_with_index"),
             ("function", "has_key?"),
             ("function", "has_value?"),
             ("function", "merge"),
             ("function", "merge!"),
                             ]
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[6]), pure_hash_literals)
    
    @tag("bug94237")    
    def test_nested_literals_3(self):
        # lower-case names work
        content, positions = unmark_text(dedent("""
            a = [1,2,3]
            puts a.<1>size
            """))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("function", "size"),])
        # but the tree walker fails to handle names starting with a capital
        content, positions = unmark_text(dedent("""
            Aa = [1,2,3]
            puts Aa.<1>size
            """))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("function", "size"),])
        
    @tag("bug94237")
    def test_builtin_class_cplns(self):
        content, positions = unmark_text(dedent("""
            puts Array.<1>new
            """))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("function", "new"),])
        
    @tag("bug94237")
    def test_builtin_class_calltip(self):
        content, positions = unmark_text(dedent("""
            puts Array(<1>1337)
            """))
        ptn = (r'Array\(\w+\).*?Returns `?arg\'? as an Array.\s*'
             + r'First tries to call `?arg\'?\.to_ary,\s*'
             + r'then `?arg\'?.to_a\.')
        self.assertCalltipMatches(markup_text(content, pos=positions[1]),
            ptn, flags=re.DOTALL)
        
    def test_foo2(self):
        content, positions = unmark_text(dedent("""
            class Bar
                def bar
                end
            end

            class Foo < Bar
                def foo
                end
            end

            foo = Foo.new
            foo.<1>bar
        """))
        # Test basic completions on objects
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("function", "bar"),
             ("function", "foo")])
        
    def test_class_new_init(self):
        # test Foo.new
        # test Foo.initialize
        content = dedent("""
        class Foo
            def initialize(a, b, *c)
                @blah = 3
            end
        end
        myfoo = Foo.<|>""")
        self.assertCompletionsInclude(content, [("function", "new")])
        
    # These tests are used to differentiate class methods from
    # instance methods
    _class_methods_text = dedent("""
        class Foo
            def Foo.cls_met1(x); end
            def inst_met2(x); end
            def initialize; end
            def Foo.<3>another_cls_met1(x); end
        end
        x = Foo.<1>c
        myfoo = Foo.new
        myfoo.<2>i
        """)
    def test_class_methods_1(self):
        content, positions = unmark_text(self._class_methods_text)
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("function", "cls_met1")])
        
    @tag("bug54998") # 
    def test_class_methods_2(self):
        content, positions = unmark_text(self._class_methods_text)
        self.assertCompletionsDoNotInclude(
            markup_text(content, pos=positions[1]),
            [("function", "inst_met2")])
        
    def test_class_methods_3(self):
        content, positions = unmark_text(self._class_methods_text)
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[2]),
            [("function", "inst_met2")])

    @tag("bug54998") # 
    def test_class_methods_4(self):
        content, positions = unmark_text(self._class_methods_text)
        self.assertCompletionsDoNotInclude(
            markup_text(content, pos=positions[2]),
            [("function", "cls_met1"), ("function", "new")])

    @tag("bug62327") # 
    def test_class_methods_5(self):
        content, positions = unmark_text(self._class_methods_text)
        self.assertNoTrigger(markup_text(content, pos=positions[3]))
    
    _class_methods_alias_text = dedent("""
        class Foo
            def Foo.cls_met1(x); end
            def inst_met2(x); end
        end
        fooClass = Foo
        fooClass.<1>c
        x = fooClass.new
        x.<2>i
        """)

    @tag("knownfailure") # bug 55008
    def test_class_methods_alias_1(self):
        content, positions = unmark_text(self._class_methods_alias_text)
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("function", "cls_met1"), ("function", "new")])

    # bugs 55008 and 54998, currently passing due to
    # negative universe implications
    @tag("knownfailure") # bug 55008
    def test_class_methods_alias_2(self):
        content, positions = unmark_text(self._class_methods_alias_text)
        self.assertCompletionsDoNotInclude(
            markup_text(content, pos=positions[1]),
            [("function", "inst_met2")])
        
    def test_class_methods_alias_3(self):
        content, positions = unmark_text(self._class_methods_alias_text)
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[2]),
            [("function", "inst_met2")])

    # see also bug 54998 -- see test_class_methods_alias_2
    @tag("bug55008") # 
    def test_class_methods_alias_4(self):
        content, positions = unmark_text(self._class_methods_alias_text)
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[2]),
            [("function", "inst_met2")])
        self.assertCompletionsDoNotInclude(
            markup_text(content, pos=positions[2]),
            [("function", "cls_met1"), ("function", "new")])
        
    def test_class_implicit_new(self):
        content = "class Foo2 ; end ; myfoo = Foo2.<|>"
        self.assertCompletionsInclude(content, [("function", "new")])
        
    @tag("trg", "bug62327")
    def test_class_method_no_trg(self):
        content, positions = unmark_text(dedent("""\
            class MyClass
                def MyClass.<1>cls_met1
                end
                def MyClass.cls_met2
                end
                def inst_met3
                end
            end
            x = MyClass.<2>new
            y = x.<3>blah
        """))
        self.assertNoTrigger(markup_text(content, pos=positions[1]))
            
    def test_kernel_methods_calltips_explicit(self):
        """Test for calltips on the kernel methods
        """
        self._finish_rand_test('a = Kernel.rand(<1>2.3)')
        
    @tag("bug69499")
    def test_kernel_methods_calltips_implicit(self):
        """Test for calltips on the kernel methods, without the
           explicit 'Kernel'
        """
        self._finish_rand_test('a = rand(<1>2.3)')
        
    def _finish_rand_test(self, code):
        content, positions = unmark_text(code)
        # calltip changed in 1.9.3
        expected = (r'(?:rand.*?Converts.*?to an integer using max1 = max\.to_i\.abs.*?'
                  + r'result is zero, returns a pseudorandom floating point'
                  + r'|rand\(p1 = v1\).*?'
                  + r'If max is .*?Range.*?, returns a pseudorandom number where '
                  + r'range\.member\(number\) == true\.)') 
        self.assertCalltipMatches(markup_text(content, pos=positions[1]),
                             expected, flags=re.DOTALL)
        

    def test_foo3(self):
        content, positions = unmark_text(dedent("""
            mystring = "hi there"
            mynum = 42
            mynum.<1>round
            mystring.<2>tolower

            class Bar
                def bar
                end
            end

            class Foo < Bar
                def foo
                end
            end

            foo = Foo.new
            foo.<3>bar
        """))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[3]),
            [("function", "bar"),
             ("function", "foo")])
        self.assertCompletionsInclude(
          markup_text(content, pos=positions[1]),
          [("function", "abs"),
           ("function", "between?")])

    def test_builtin_module_completions(self):
        _loadable_module_completions_text = dedent("""\
            Process.<|>""")
        self.assertCompletionsInclude(
            _loadable_module_completions_text,
            [("function", "detach")])

    def test_loadable_module_completions(self):
        _loadable_module_completions_text = dedent("""\
            require 'find'
            Find.<|>
        """)
        self.assertCompletionsInclude(
            _loadable_module_completions_text,
            [("function", "find")])

     # Verify that both '.' and '::' work as scope resolution
     # operators on modules when accessing module-level methods - bug 55018
    def test_loadable_module_completions_2(self):
        content, positions = unmark_text(dedent("""
            require "fileutils"
            FileUtils.<1>c
            FileUtils::<2>p
            FileUtils.cd(<3>'x')
            FileUtils::cd(<4>'x')
        """))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("function", "cd"),
             ("function", "rm_rf")])
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[2]),
            [("function", "mkdir"),
             ("function", "touch")])
        name = "ruby-calltip-call-signature"
        self.assertTriggerMatches(markup_text(content, pos=positions[3]), name=name)
        self.assertTriggerMatches(markup_text(content, pos=positions[4]), name=name)
        
        expected = r'.*?\(dir, options.*\).*Options: verbose'
        #dedent("""
        #           (dir, options = {}) {|dir| ...}
        #           Options: verbose
        #    """).strip()
        self.assertCalltipMatches(
            markup_text(content, pos=positions[3]), expected, flags=re.DOTALL)            
        self.assertCalltipMatches(
            markup_text(content, pos=positions[4]), expected, flags=re.DOTALL)
        
    @tag("bug56218")
    # This works when the aliases are captured in YAML docs
    def test_loadable_module_completions_3(self):
        content, positions = unmark_text(dedent("""
            require "fileutils"
            FileUtils.<1>xxx
        """))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("function", "mkdir")])
        
    @tag("bug56218")
    # rubycile doesn't grok aliases yet.
    def test_alias_methods(self):
        content, positions = unmark_text(dedent("""
            class Bug56218
               def real_method(x)
                   return 4 * x
               end
               alias faker_method real_method
               # Args to alias are symbols or names
            end
            obj = Bug56218.new
            obj.<1>faker_method(<2>3)
        """))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("function", "faker_method"),
            ("function", "real_method"),])
        self.assertCalltipIs(
            markup_text(content, pos=positions[2]), "faker_method(x)")

    # Test was incorrectly formulated ("Net::" instead of "Net::FTP.").
    def test_find_included_namespace(self):
        content, positions = unmark_text(dedent("""\
            require 'net/http'  # red herring
            require 'net/ftp'
            puts Net::FTP::<1>new
            puts Net::FTP.new.<3>passive
            puts Net::<2>
        """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("class", "ConditionVariable")])
        self.assertCompletionsDoNotInclude(markup_text(content, pos=positions[1]),
            [("function", "passive")])
        self.assertCompletionsInclude(markup_text(content, pos=positions[2]),
            [("class", "FTP"), ("class", "HTTPRequest")])
        self.assertCompletionsInclude(markup_text(content, pos=positions[3]),
            [("function", "passive")])
        self.assertCompletionsDoNotInclude(markup_text(content, pos=positions[3]),
            [("class", "ConditionVariable")])
        
    @tag("bug44831")
    # The tree walker has to allow for multiple occurrences of nested
    # classes within a container.
    def test_class_colon_colon_class_1(self):
        content, positions = unmark_text(dedent("""
            require 'net/http'
            getter = Net::HTTP::Get.new
            res = getter.<1>request()
        """))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("function", "body_stream"),])

    @tag("bug44831")
    # The tree walker has to allow for multiple occurrences of nested
    # classes within a container.
    def test_class_colon_colon_class_2(self):
        content, positions = unmark_text(dedent("""
            require 'net/http'
            include Net
            getter = HTTP::Get.new
            res = getter.<1>request()
        """))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("function", "body_stream"),])

    @tag("bug44831")
    # The tree walker has to allow for multiple occurrences of nested
    # classes within a container.
    def test_class_colon_colon_class_3(self):
        content, positions = unmark_text(dedent("""
            require 'net/http'
            class C
              getter = Net::HTTP::Get.new
              res = getter.<1>request()
        """))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("function", "body_stream"),])

    @tag("bug44831")
    # The tree walker has to allow for multiple occurrences of nested
    # classes within a container.
    def test_class_colon_colon_class_4(self):
        content, positions = unmark_text(dedent("""
            require 'net/http'
            include Net
            class C
              getter = HTTP::Get.new
              res = getter.<1>request()
        """))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("function", "body_stream"),])

    @tag("bug44831")
    # The tree walker has to allow for multiple occurrences of nested
    # classes within a container.
    def test_class_colon_colon_class_5(self):
        content, positions = unmark_text(dedent("""
            require 'net/http'
            class C
              include Net
              getter = HTTP::Get.new
              res = getter.<1>request()
        """))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("function", "body_stream"),])

    @tag("bug50597")
    def test_quick_completions(self):
        content, positions = unmark_text(dedent("""
            class C
              def x ; end
            end
            Hash.new.<1>[]
            C.new.<2>x
            Regexp.new.<3>match
        """))
        cplns = ['', 'has_key?', 'x', 'match']
        for i in range(1, 4):
            self.assertCompletionsInclude(
            markup_text(content, pos=positions[i]), [('function', cplns[i])])

    # The calltip walker has to do the same kind of analysis as the
    # completion walker.                                        
    def test_peer_classes_1(self):
        content, positions = unmark_text(dedent("""
            require 'net/http'
            class C
              include Net
              getter = HTTPGenericRequest.new
              res = getter.<1>request()
              ctip = getter.body_stream(<2>'xyz')
              better_getter = HTTP::Get.new
              res = better_getter.<3>request()
              ctip = better_getter.body_stream(<4>'xyz')
        """))
        for i in (0, 2):
            self.assertCompletionsInclude(
                markup_text(content, pos=positions[i + 1]),
                [("function", "body_stream="),])
            expected = "body_stream(...)"
            self.assertCalltipIs(
                markup_text(content, pos=positions[i + 2]), expected)

    @tag("knownfailure", "bug65066")
    def test_multi_level_include(self):
        content, positions = unmark_text(dedent("""
            module A
              module B
                module C
                  module D
                    class C1
                      def foo_c1(x,y)
                      end
                    end
                  end
                end
              end
            end
            include A::B::C::D
            c = A::B::C::D::C1.new
            c.<1>foo_c1(<2>3, 4)
            d = C1.new
            d.<3>foo_c1(<4>5, 6)
        """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
                                      [("function", "foo_c1")])
        self.assertCalltipIs(markup_text(content, pos=positions[2]),
            'foo_c1(x,y)')
        self.assertCompletionsInclude(markup_text(content, pos=positions[3]),
                                      [("function", "foo_c1")])
        self.assertCalltipIs(markup_text(content, pos=positions[4]),
            'foo_c1(x,y)')

    @tag("bug60957")
    def test_file_is_io(self):
        content, positions = unmark_text("File.<1>new")
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
                                      [("function", "open")])


    @tag("knownfailure", "bug58908")
    def test_class_extension(self):
        content, positions = unmark_text(dedent("""
            class Foo
                def self.cmethod(a, b, c)
                    return 42
                end
                
                def imethod(d1, e2, *f3)
                    return "Hello"
                end

                def extend_me()
                    class << self
                      def imethod_2(x)
                          return 2 * x
                      end
                    end
                end
            end
            f3 = Foo.new
            f3.<1>imethod
        """))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("function", "imethod_2"),])
                         
    @tag("bug62598")
    def test_class_compound_names(self):
        content, positions = unmark_text(dedent("""\
            require 'drb/drb'
            x1 = DRb::<1>DRbUnknown
            x2 = DRb::DRbUnknown.<2>new
            x2.<3>expires
        """))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("class", "DRbUnknown"), ("namespace", "DRbUndumped")])
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[2]),
            [("function", "new")])
        self.assertCompletionsDoNotInclude(
            markup_text(content, pos=positions[2]),
            [("function", "exception"),])
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[3]),
            [("function", "exception"),("function", "reload")])
        self.assertCompletionsDoNotInclude(
            markup_text(content, pos=positions[3]),
            [("function", "new"),])

                         
    # Looks like bug 62338, but was broken only for RHTML.
    def test_attr_accessor_local(self):
        content, positions = unmark_text(dedent("""\
            class Bug62338
                attr_accessor :acc
                attr_reader :rdr
                attr_writer :wtr
                def initialize
                    @acc = 1
                    @rdr = 2
                    @wtr = 3
                end
            end
            b = Bug62338.<1>new
            puts b.<2>acc
        """))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("function", "new"),
             ])
        self.assertCompletionsDoNotInclude(
            markup_text(content, pos=positions[1]),
            [("function", "acc"),
             ("function", "rdr"),
             ("function", "wtr=")])
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[2]),
            [("function", "acc"),
             ("function", "rdr"),
             ("function", "wtr=")])
        self.assertCompletionsDoNotInclude(
            markup_text(content, pos=positions[2]),
            [("function", "new"),
             ])

    @tag("bug62338")
    def test_class_compound_names_attr_accessors(self):
        content, positions = unmark_text(dedent("""\g
            require 'cgi/session'
            x1 = CGI::<1>Session
            x2 = CGI::Session.<2>new
            x2.<3>delete
        """))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[3]),
            [("function", "close"),
             ("function", "delete"),
             ("function", "update"),
             ])
        

    @tag("bug62778")
    def test_class_class_instance_method_name_collision(self):
        content, positions = unmark_text(dedent("""\
            class Foo
                def chuck ; end
                def Foo.chuck ; end
                def Foo.blick ; end
            end
            f = Foo.<1>new()
            puts f.<2>chuck
        """))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("function", "new"),
             ("function", "chuck"),
             ("function", "blick"),
             ])
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[2]),
             [("function", "chuck"),
             ])
        self.assertCompletionsDoNotInclude(
            markup_text(content, pos=positions[2]),
            [("function", "new"),
             ("function", "blick"),
             ])

    @tag("knownfailure", "bug62817")
    def test_resolve_multiple_module_relativeclassrefs(self):
        # Test the completion only.
        test_dir = join(self.test_dir, "test_bug62817")
        main_filename = "main%s" % self.ext
        main_content, main_positions = \
          unmark_text(self.adjust_content(dedent("""\
            require 'a'
            require 'b'
            x1 = A1::B1::C1.<1>new
            x2 = A1::B1::C2.new
            y1 = x1.<2>foo_c1()
            y2 = x2.<3>foo_c2()
        """)))
        manifest = [
            ("a.rb", dedent("""\
                module A1
                  module B1
                    class C1
                      def foo_c1(d,e,f)
                    end
                  end
                end""")),
            ("b.rb", dedent("""\
                module A1
                  module B1
                    class C2 < C1
                      def foo_c2(g,h,i)
                      end
                    end
                  end
                end""")),
            (main_filename, main_content),
            ]
        for file, content in manifest:
            path = join(test_dir, file)
            writefile(path, content)
        main_buf = self.mgr.buf_from_path(join(test_dir, main_filename))
        self.assertCompletionsInclude2(main_buf, main_positions[1],
            [("function", "new"),
             ])
        self.assertCompletionsInclude2(main_buf, main_positions[2],
            [("function", "foo_c1"),
             ])
        self.assertCompletionsInclude2(main_buf, main_positions[2],
            [("function", "foo_c1"),
             ("function", "foo_c2"),
             ])

    @tag("global", "trg", "bug69362")
    def test_trg_after_scope_operator(self):
        # Verify that triggers don't work after . and ::
        name = "ruby-complete-names"
        content, positions = unmark_text(dedent("""\
            s = Str<1>ing.c<3>ap<2>itali
        """))
        self.assertTriggerMatches(markup_text(content, pos=positions[1]),
                                  name=name)
        self.assertNoTrigger(markup_text(content, pos=positions[2]))
        
        self.assertNoTrigger(markup_text(content, pos=positions[3]))

    @tag("global")
    def test_cull_single_cplns(self):
        # It's annoying having a current-name calltip appear when
        # it contains only one item, and it's already been typed.
        # These tests verify they've been squelched.
        name = "ruby-complete-names"
        content, positions = unmark_text(dedent("""\
            class Xkw
               def q4e
                   x_3 = 22
                   return x_3<1>
               end
               def other
                   return q4e<2>
               end
               def mx4e(i)
                   y7pi = i
                   if y7p<3>i < 10
                     return mx4<4>e(i + 1)
                   end
                   zyo8u = 12
                   puts zyo<6>8u
               end
            end
            thing = Xkw<5>.new
            class Sdrof
               def got_it
               end
               def other
                 got<7>_it()
               end
            end
            thing2 = Sdr<8>of.new
            thing2.<9>other
        """))
        # Verify we don't trigger on 4-char
        non_targets = [
            ("variable", "x_3"),
            ("function q4e"),
            ("class Xkw"),
            ("variable", "y7pi"),
            ("function mx4e"),
            ]
        for i in range(len(non_targets)):
            self.assertCompletionsDoNotInclude(markup_text(content, pos=positions[i + 1]),
            [non_targets[i]])
            
        targets = [
            ("variable", "zyo8u"),
            ("function", "got_it"),
            ("class", "Sdrof"),
            ("function", "other"),
            ]
            # Verify we don't trigger on 5-char
        pos_offset = len(non_targets) + 1
        for i in range(0, len(targets)):
            self.assertCompletionsInclude(markup_text(content, pos=positions[i + pos_offset]),
            [targets[i]])

    @tag("global")
    def test_basic_toplevel(self):
        content, positions = unmark_text(dedent("""
            req<1>uire 'cgi'                # kernel
            long_name_here = 22
            raise Flo<2>     # built-in class
            other = 'other'
            lon<3>g += 5        # local scope
            yie<4>ld                      # keyword
            
            """))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("function", "require"),
             ])
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[2]),
            [
             ("class", "Float"),
             ("class", "FloatDomainError"),
             ])
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[3]),
            [
             ("variable", "long_name_here"),
             ])
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[4]),
            [
             ("function", "yield"),  # Actually a keyword, see bug 64087
             ])
        for i in range(1, 5):
            self.assertCompletionsDoNotInclude(
                markup_text(content, pos=positions[i]),
            [
             ("function", "autoload"),
             ("class", "Coimparable"),
             ("namespace", "Enumerable"),
             ("function", "for"),
             ("variable", "other"),
             ])
            
    @tag("global")
    def test_basic_top_level_in_class(self):
        content, positions = unmark_text(dedent("""
        class C1
            def func1
                long_var_name1 = 10
                long_var_name2 = 20
                long_var_name3 = 30
                puts lon<1>g_var_name
                fun<2>c
            end
            def func2
                long_var_name4 = 10
                long_var_name5 = 20
                long_var_name6 = 30
                puts lon<3>g_var_name
                fun<4>c
            end
        end
        class C3
            def func3
                long_var_name7 = 10
                long_var_name8 = 20
                long_var_name9 = 30
                puts lon<5>g_var_name
                fun<6>c
            end
        end
            """))
        var_set_1 = [
             ("variable", "long_var_name1"),
             ("variable", "long_var_name2"),
             ("variable", "long_var_name3"),
             ]
        var_set_2 = [
             ("variable", "long_var_name4"),
             ("variable", "long_var_name5"),
             ("variable", "long_var_name6"),
             ]
        var_set_3 = [
             ("variable", "long_var_name7"),
             ("variable", "long_var_name8"),
             ("variable", "long_var_name9"),
             ]
        func_set_1 = [
             ("function", "func1"),
             ("function", "func2"),
             ]
        func_set_2 = [
             ("function", "func3"),
             ]
        var_exp = (var_set_1, var_set_2, var_set_3)
        var_not = (var_set_2 +  var_set_3, var_set_1 + var_set_3, var_set_1 + var_set_2)
        func_exp = (func_set_1, func_set_1, func_set_2)
        func_not = (func_set_2, func_set_2, func_set_1)

        for i in range(3):
            self.assertCompletionsInclude(
                markup_text(content, pos=positions[2 * i + 1]),
                var_exp[i])
            self.assertCompletionsDoNotInclude(
                markup_text(content, pos=positions[2 * i + 1]),
                var_not[i])
            self.assertCompletionsInclude(
                markup_text(content, pos=positions[2 * i + 2]),
                func_exp[i])
            self.assertCompletionsDoNotInclude(
                markup_text(content, pos=positions[2 * i + 2]),
                func_not[i])
           
    @tag("defns") 
    def test_inline_defns(self):
        test_dir = join(self.test_dir, "test_inline_defns")
        main_filename = "main%s" % self.ext
        main_path = join(test_dir, main_filename)
        # For this test, a variable at position N is defined at position 100+N
        main_content, main_positions = \
          unmark_text(self.adjust_content(dedent("""\
          module M1<101>
            class C1<102>
              def f1a<103>
              end
              def f1b
                v1 = 22
                @x = 33
              end
              def sum_these
                puts v1<10> + @<11>
              end
            end #C1
          end #M1
          module M2<104>
            class C2<105>
              def f2a<106>
              end
              def f2b
                v2 = '22'
                @x = 33
              end
              def diff_these
                puts v2<12> - @x<13>
              end
            end #C2
          end #M2
          c1 = M1<1>::C1<2>.new
          c1.f1a<3>
          c2 = M<4>2::C2<5>.new
          c2.f<6>2a
        """)))
        writefile(main_path, main_content)
        buf = self.mgr.buf_from_path(main_path)
        lines = lines_from_pos(main_content, main_positions)
        self.assertDefnMatches2(buf, main_positions[1],
            ilk="namespace", name="M1", line=lines[101])
        self.assertDefnMatches2(buf, main_positions[2],
            ilk="class", name="C1", line=lines[102])
        self.assertDefnMatches2(buf, main_positions[3],
            ilk="function", name="f1a", line=lines[103])

        self.assertDefnMatches2(buf, main_positions[4],
            ilk="namespace", name="M2", line=lines[104])
        self.assertDefnMatches2(buf, main_positions[5],
            ilk="class", name="C2", line=lines[105])
        self.assertDefnMatches2(buf, main_positions[6],
            ilk="function", name="f2a", line=lines[106])

        # Test that getting defns at their definition works
        self.assertDefnMatches2(buf, main_positions[101],
            ilk="namespace", name="M1", line=lines[101])
        self.assertDefnMatches2(buf, main_positions[102],
            ilk="class", name="C1", line=lines[102])
        self.assertDefnMatches2(buf, main_positions[103],
            ilk="function", name="f1a", line=lines[103])

        self.assertDefnMatches2(buf, main_positions[104],
            ilk="namespace", name="M2", line=lines[104])
        self.assertDefnMatches2(buf, main_positions[105],
            ilk="class", name="C2", line=lines[105])
        self.assertDefnMatches2(buf, main_positions[106],
            ilk="function", name="f2a", line=lines[106])
        
    @tag("defns")
    def test_peer_module_defns(self):
        test_dir = join(self.test_dir, "test_peer_module_defns")
        main_filename = "main%s" % self.ext
        main_path = join(test_dir, main_filename)
        main_content, main_positions = \
          unmark_text(self.adjust_content(dedent("""\
            require 'rhino'
            require 'dolphin/fin'
            include Dolp<1>hin
            f = Fi<2>n.new
            puts f.loc<3>ation(), f.language<4>
            g = Rhi<5>no.new
            puts g.horn_cou<6>nt, g.lang<7>uage
        """)))
        rhino_path = join(test_dir, "rhino.rb")
        fin_path = join(test_dir, "dolphin", "fin.rb")
        manifest = [
            (rhino_path, dedent("""\
                 class Rhino
                   def horn_count  ; 1
                   end
                   def language
                      return "JavaScript"
                   end
                 end
             """)),
            (fin_path, dedent("""\
                 module Dolphin
                   class Fin
                     def location
                         return "saragasso"
                     end
                     def language
                        'mysql'
                     end
                 end
             """)),
            (main_path, main_content),
        ]
        for path, content in manifest:
            writefile(path, content)
        buf = self.mgr.buf_from_path(main_path)
        self.assertDefnMatches2(buf, main_positions[1],
            ilk="namespace", name="Dolphin", path=fin_path, line=1)
        self.assertDefnMatches2(buf, main_positions[2],
            ilk="class", name="Fin", line=2)
        self.assertDefnMatches2(buf, main_positions[3],
            ilk="function", name="location", line=3)
        self.assertDefnMatches2(buf, main_positions[4],
            ilk="function", name="language", line=6)
        self.assertDefnMatches2(buf, main_positions[5],
            ilk="class", name="Rhino", line=1)
        self.assertDefnMatches2(buf, main_positions[6],
            ilk="function", name="horn_count", line=2)
        self.assertDefnMatches2(buf, main_positions[7],
            ilk="function", name="language", line=4)
        # path=rhino_path, 
           
    @tag("defns")  
    def test_inline_variables(self):
        test_dir = join(self.test_dir, "test_inline_variables")
        main_filename = "main%s" % self.ext
        main_path = join(test_dir, main_filename)
        main_content, main_positions = \
          unmark_text(self.adjust_content(dedent("""\
            class C1
              def f1a
                v1 = 22
                puts v1<1>
              end
            end #C1
            class C2
              def f2b
                v2 = '22'
                puts v2<3>
              end
            end #C2
        """)))
        writefile(main_path, main_content)
        buf = self.mgr.buf_from_path(main_path)

        self.assertDefnMatches2(buf, main_positions[1],
            ilk="variable", name="v1", citdl="Fixnum", line=3)
        self.assertDefnMatches2(buf, main_positions[3],
            ilk="variable", name="v2", citdl="String", line=9)

    @tag("bug65403", "defns", "knownfailure")
    def test_inst_var_cplns(self):
        test_dir = join(self.test_dir, "test_inst_var_cplns")
        main_filename = "main%s" % self.ext
        main_path = join(test_dir, main_filename)
        main_content, main_positions = \
          unmark_text(self.adjust_content(dedent("""\
            class C1
              def setup
                @@cls_var = 2
                @inst_var1 = 33
                @inst_var2 = 33
              end
              def use
                puts @inst_var<1>1
                puts @ins<2>t_var1
                puts @<3>inst_var2 + @@cls<4>_va<6>r
              end
            end #C1
        """)))
        writefile(main_path, main_content)
        buf = self.mgr.buf_from_path(main_path)
        self.assertCompletionsAre2(buf, main_positions[1],
                                   [("variable", "@inst_var1"),
                                    ("variable", "@inst_var2"),
                                    ])
        self.assertDefnMatches2(buf, main_positions[2],
            ilk="variable", name="@inst_var1", citdl="Fixnum", line=4)
        self.assertDefnMatches2(buf, main_positions[3],
            ilk="variable", name="@inst_var1", citdl="Fixnum", line=5)
        self.assertCompletionsAre2(buf, main_positions[4],
                                   [("variable", "@@cls_var"),
                                    ])
        self.assertDefnMatches2(buf, main_positions[5],
            ilk="variable", name="@@cls_var", citdl="Fixnum", line=3)
                                                      
    @tag("bug99108")
    def test_scope_bounds(self):
        test_dir = join(self.test_dir, "test_defn")
        foo_content, foo_positions = unmark_text(dedent("""\
            require 'net/http'
            # And a comment
            def test1(i)
                b = i > 0 ? i : 0
                return b
            end
            t = test1<1>(0)
            print(t)
        """))
        path = join(test_dir, "scope_bounds.rb")
        writefile(path, foo_content)
        buf = self.mgr.buf_from_path(path)
        self.assertDefnMatches2(buf, foo_positions[1],
            ilk="function", name="test1", line=3,
            scopestart=1, scopeend=0, path=path, )
                                                      
    @tag("bug99108")
    def test_scope_bounds_02(self):
        test_dir = join(self.test_dir, "test_defn")
        foo_content, foo_positions = unmark_text(dedent("""\
            require 'net/http'
            # And a comment
            class C
                def test1(i)
                    b = i > 0 ? i : 0
                end
                def cheeseboogie(j)
                    return test1<1>(j - 5)
                end
            end
            cx = C.new
            t = cx.cheeseboogie<2>(7)
            puts(t)
        """))
        path = join(test_dir, "scope_bounds_02.rb")
        writefile(path, foo_content)
        buf = self.mgr.buf_from_path(path)
        self.assertDefnMatches2(buf, foo_positions[1],
            ilk="function", name="test1", line=4,
            scopestart=3, scopeend=10, path=path, )
        self.assertDefnMatches2(buf, foo_positions[2],
            ilk="function", name="cheeseboogie", line=7,
            scopestart=3, scopeend=10, path=path, )

    @tag("bug99177")
    def test_argument_defn_line(self):
        test_dir = join(self.test_dir, "argument_defn_line")
        foo_content, foo_positions = unmark_text(dedent("""\
            # And a comment
            def nop
            end
            def test1(ibix,
                      llama)
                b = lla<1>ma
                return b + ibix<2> + 1

            t = test1(0, 3)
            print(t)
        """))
        path = join(test_dir, "scope_bounds.rb")
        writefile(path, foo_content)
        buf = self.mgr.buf_from_path(path)
        # Although llama is defined at line 5,
        # we only get enough information to tie it to the function
        # defined at line 4
        self.assertDefnMatches2(buf, foo_positions[1],
            ilk="argument", name="llama", line=4,
            path=path)
        self.assertDefnMatches2(buf, foo_positions[2],
            ilk="argument", name="ibix", line=4, path=path, )


class PureTestCase(_BaseTestCase):
    lang = "Ruby"
    ext = ".rb"
    heredoc_support = True
    
    #XXX Figure out how to express this in mixedlang mode as well.
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
            self.assertCITDLExprIs(buffer, expected_citdl_expr)

        self.assertCITDLExprIs("z = Zlib::Deflate.new()\nz.<|>", "z")

    @tag("knownfailure")
    def test_citdl_expr_under_pos_simple(self):
        # XXX - Eric, CHECK: I'm not sure this is actually what we would want
        #                    to return.
        test_cases = """
            z.<|>                       z
            send(<|>                    send
            foo.in<|>stance_of?(        foo.instance_of?
            File.op<|>en(               File.open
            Zlib::Deflate.def<|>late(   Zlib::Deflate.deflate

            # Ensure don't go grab too much of the expr
            F<|>ile.open(               File
            Zlib::Def<|>late.deflate(   Zlib::Deflate
            Zli<|>b::Deflate.deflate(   Zlib

            # These trigger types are disabled until eval for them is
            # implemented.
            #@assigned.<|>               @assigned
            #@@foo.<|>                   @foo
            #$blah.<|>                   @blah
            
            # Skipping this one for now because we'd need to do the smarter
            # convert-literals-to-class-instance thang first.
            #0.step(<|>                  Numeric.step

            @ingr<|>edients.             @ingredients
            @ingredients.<|>has_key?(    @ingredients.has_key?
            @ingre<|>dients.has_key?(    @ingredients

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
            '...'.s<|>tep(              String.step
            [1,2,3].each(<|>            Array.each
        """
        for line in test_cases.splitlines(0):
            if not line.strip(): continue
            if line.lstrip().startswith("#"): continue
            buffer, expected_citdl_expr = line.split()
            self.assertCITDLExprUnderPosIs(buffer, expected_citdl_expr)

        self.assertCITDLExprUnderPosIs("z = Zlib::Deflate.new()\nz.<|>", "z")

    def test_create_root_level_file(self):
        # XXX: This path may not exist (i.e. on Windows).
        main_path = "/tmp/foo.rb"
        main_content, main_positions = \
                      unmark_text(self.adjust_content(dedent("""\
                      class Foo
                          def mouse
                          end
                      end
                      f = Foo.new.<1>mouse
                      """)))
        writefile(main_path, main_content)
        try:
            main_buf = self.mgr.buf_from_path(main_path)
            class_targets = [
                ("function", "mouse"),
            ]
            self.assertCompletionsInclude2(main_buf, main_positions[1],
                                           class_targets)
        finally:
            os.unlink(main_path)
     
    @tag("defns")
    def test_external_defns(self):
        main_content, main_positions = \
          unmark_text(self.adjust_content(dedent("""\
            require 'net/http'
            require 'net/ftp'
            req = Ne<1>t::HTTPGener<2>icRequest.ne<3>w
            req.send_request_with_body<4>
        """)))
        path = os.path.join("<Unsaved>", "rand%d" % random.randint(0, 100))
        buf = self.mgr.buf_from_content(main_content, lang="Ruby", path=path)
        # Don't provide line numbers because they change from version to version of
        # Ruby, and they aren't used by Komodo, so we no longer write line attributes
        # into the cix files.
        self.assertDefnMatches2(buf, main_positions[2], 
            ilk="class", name="HTTPGenericRequest")
        self.assertDefnMatches2(buf, main_positions[1], 
            ilk="namespace", name="Net")

    def test_complete_module_names_heredoc(self): # MODULE::
        name = "ruby-complete-module-names"
        hdoc = self.adjust_content(dedent("""\
            string = <<END_OF_STRING
                Module::<|>
            END_OF_STRING
            """))
        if self.heredoc_support:
            self.assertNoTrigger(hdoc)
        else:
            self.assertTriggerMatches(hdoc, name=name)

    def _verify_icalendar(self):
        rubyBaseDir = dirname(dirname(which.which("ruby")))
        gemDir1 = join(rubyBaseDir, "lib", "ruby", "gems")
        if not exists(gemDir1):
            raise TestSkipped("No gems dir in %s" % rubyBaseDir)
        things = os.listdir(gemDir1)
        if not things:
            raise TestSkipped("Gems dir %s is empty" % gemDir1)
        gemDir2 = join(gemDir1, things[0], "gems")
        if not exists(gemDir2):
            raise TestSkipped("No ver/gems dir in %s" % gemDir1)
        things = [x for x in os.listdir(gemDir2) if x.startswith("icalendar-")]
        if not things:
            raise TestSkipped("icalendar not installed in %s" % gemDir2)
        # Now that we know we have icalendar, run the test.
        
    @tag("cplns")
    def test_dispersed_module_defns_01(self):
        self._verify_icalendar()
        content, positions = unmark_text(dedent("""\
            require 'rubygems'
            require 'icalendar'
            a = Icalendar::<1>Calendar.new
            puts a.<2>find_event
        """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("class", "Calendar"), ("class", "Geo")])
  
    @tag("bug72335", "cplns")
    def test_dispersed_module_defns_02(self):
        """
        Verify that we can walk nodes when we have more than
        one top-level hit.
        """
        self._verify_icalendar()
        content, positions = unmark_text(dedent("""\
            require 'rubygems'
            require 'icalendar'
            a = Icalendar::<1>Calendar.new
            puts a.<2>find_event
        """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[2]),
            [("function", "find_event"), ("function", "todo")])
  
re_cursor = re.compile(r'<[\|\d]+>')

class MultiLangTestCase(_BaseTestCase):
    lang = "RHTML"
    ext = ".rhtml"
    heredoc_support = False

    _rhtml_prefix = "<body><p><% "
    _rhtml_suffix = " %>"
    def adjust_content(self, content):
        if not re_cursor.search(content):
            content += "<|>"
        return self._rhtml_prefix + content + self._rhtml_suffix
    def adjust_pos(self, pos):
        return pos + len(self._rhtml_prefix)

    @tag("defns", "knownfailure")
    def test_external_defns(self):
        main_content, main_positions = \
          unmark_text(self.adjust_content(dedent("""\
            require 'net/http'
            require 'net/ftp'
            req = Ne<1>t::HTTPGener<2>icRequest.ne<3>w
            req.send_request_with_body<4>
        """)))
        path = os.path.join("<Unsaved>", "rand%d" % random.randint(0, 100))
        buf = self.mgr.buf_from_content(main_content, lang="Ruby", path=path)
        self.assertDefnMatches2(buf, main_positions[2], 
            ilk="class", name="HTTPGenericRequest", line=1431)
        self.assertDefnMatches2(buf, main_positions[1], 
            ilk="namespace", name="Net", line=31)

    @tag("bug70747", "knownfailure")
    def test_complete_module_names_heredoc(self): # MODULE::
        """When bug 70747 is fixed delete
        PureTestCase.test_complete_module_names_heredoc and
        put this code back into
        _BaseTestCase.test_complete_module_names
        """
        name = "ruby-complete-module-names"
        hdoc = self.adjust_content(dedent("""\
            string = <<END_OF_STRING
                Module::<|>
            END_OF_STRING
            """))
        if self.heredoc_support:
            self.assertNoTrigger(hdoc)
        else:
            self.assertTriggerMatches(hdoc, name=name)

#---- mainline

if __name__ == "__main__":
    unittest.main()


