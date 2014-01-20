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

"""Test some Python-specific codeintel handling."""

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
from citestsupport import CodeIntelTestCase, writefile



log = logging.getLogger("test")


class CatalogTestCase(CodeIntelTestCase):
    lang = "Python"
    test_catalog_dirs = [join(os.getcwd(), "tmp", "a"),
                         join(os.getcwd(), "tmp", "b")]
    _ci_db_catalog_dirs_ = test_catalog_dirs

    def test_catalog(self):
        # Create test dirs.
        for d in self.test_catalog_dirs:
            if not exists(d):
                os.makedirs(d)

        #XXX Have to decide how to handle catalog collisions before
        #    including this.
        ## Put this decoy in the second catalog dir.
        #decoy = dedent("""
        #    class Blam:
        #        def decoy(self, duck):
        #            "mwuhahaha!"
        #            pass
        #""")
        #buf = self.mgr.buf_from_content(decoy, lang=self.lang, path="blam.py")
        #open(join(self.test_catalog_dirs[1], "decoy.cix"), 'w').write(buf.cix)

        # Put this guy in the first catalog dir.
        blam = dedent("""\
            class Blam:
                def pow(self, bb):
                    "pow man!"
                    pass
                def pif(self, aa):
                    pass
        """)
        buf = self.mgr.buf_from_content(blam, lang=self.lang, path="blam.py")
        open(join(self.test_catalog_dirs[0], "blam.cix"), 'w').write(buf.cix)

        # Ensure the catalog is updated.
        self.mgr.db.get_catalogs_zone().update()

        # Need to use a custom runtime environment that ensures this
        # catalog is selected.
        env = SimplePrefsEnvironment(codeintel_selected_catalogs=['blam'])
        foo_py_a = dedent("""\
            import blam
            blam.Blam.<|>pow
        """)
        foo_py_b = dedent("""\
            from blam import Blam
            Blam.<|>pow
        """)
        foo_py_c = dedent("""\
            from blam import *
            Blam.<|>pow
        """)
        for foo_py in (foo_py_a, foo_py_b, foo_py_c):
            self.assertCompletionsInclude(foo_py,
                [("function", "pif"), ("function", "pow")],
                env=env)

class DefnTestCase(CodeIntelTestCase):
    lang = "Python"
    test_dir = join(os.getcwd(), "tmp")

    def test_citdl_expr_under_pos_simple(self):
        self.assertCITDLExprUnderPosIs("foo.<|>", "foo")
        self.assertCITDLExprUnderPosIs("foo.bar<|>", "foo.bar")
        self.assertCITDLExprUnderPosIs("f<|>oo.bar", "foo")
        self.assertCITDLExprUnderPosIs("foo(bar.<|>", "bar")
        self.assertCITDLExprUnderPosIs("foo[bar.<|>", "bar")
        self.assertCITDLExprUnderPosIs("foo{bar.<|>", "bar")
        self.assertCITDLExprUnderPosIs("foo().<|>", "foo()")
        self.assertCITDLExprUnderPosIs("foo(a,b).<|>", "foo()")
        self.assertCITDLExprUnderPosIs("a = foo.<|>", "foo")
        self.assertCITDLExprUnderPosIs("a = foo(bar.<|>, blam)", "bar")
        self.assertCITDLExprUnderPosIs("blam()\nfoo.<|>", "foo")
        # Ensure we only grab the correct context, and not too much
        self.assertCITDLExprUnderPosIs("blam()\nfoo.bar.b<|>az", "foo.bar.baz")
        self.assertCITDLExprUnderPosIs("blam()\nfoo.b<|>ar.baz", "foo.bar")
        self.assertCITDLExprUnderPosIs("blam()\nfo<|>o.bar.baz", "foo")
    def test_citdl_expr_under_pos_simple2(self):
        self.assertCITDLExprUnderPosIs("from blah import *\nfoo.bar.<|>", "foo.bar")
    def test_citdl_expr_under_pos_simple3(self):
        self.assertCITDLExprUnderPosIs("from blah import (a,b)\nfoo.bar.<|>", "foo.bar")
    def test_citdl_expr_under_pos_multiline(self):
        self.assertCITDLExprUnderPosIs("foo(bar,\nblam.<|>)", "blam")
        self.assertCITDLExprUnderPosIs("foo(bar,\nblam).spam.<|>", "foo().spam")
        self.assertCITDLExprUnderPosIs("foo.\\\nbar.<|>", "foo.bar")
        self.assertCITDLExprUnderPosIs("foo(1, # one\n2).bar.<|>", "foo().bar")
        self.assertCITDLExprUnderPosIs("foo(1, # o)ne\n2).bar.<|>", "foo().bar")
        self.assertCITDLExprUnderPosIs("foo(1, # (o)ne\n2).bar.<|>", "foo().bar")
        self.assertCITDLExprUnderPosIs("foo(1, # (one\n2).bar.<|>", "foo().bar")
        self.assertCITDLExprUnderPosIs("foo( #this is a ) comment\nb,d).<|>", "foo()")
        self.assertCITDLExprUnderPosIs("foo\\\n(',({[', {one:1,two:2}).<|>", "foo()")
    def test_citdl_expr_under_pos_extra(self):
        self.assertCITDLExprUnderPosIs("if foo.<|>(", "foo")
        self.assertCITDLExprUnderPosIs("elif foo.<|>(", "foo")
        self.assertCITDLExprUnderPosIs("for foo.<|>(", "foo")
        self.assertCITDLExprUnderPosIs("while foo.<|>(", "foo")
        self.assertCITDLExprUnderPosIs("def foo.<|>(", "foo")
        self.assertCITDLExprUnderPosIs("class foo.<|>(", "foo")
        self.assertCITDLExprUnderPosIs("import foo.<|>(", "foo")
        self.assertCITDLExprUnderPosIs("from foo.<|>(", "foo")
        self.assertCITDLExprUnderPosIs("boo3 foo.<|>(", "foo")

    def test_simple(self):
        test_dir = join(self.test_dir, "test_defn")
        foo_py_content, foo_py_positions = unmark_text(dedent("""\
            import bar
            bar.b<1>ar
        """))

        manifest = [
            ("bar.py", dedent("""
                bar = 42
             """)),
            ("foo.py", foo_py_content),
        ]
        for file, content in manifest:
            path = join(test_dir, file)
            writefile(path, content)

        buf = self.mgr.buf_from_path(join(test_dir, "foo.py"), lang=self.lang)
        #self.assertDefnMatches2(buf, foo_py_positions[1],
        #    path=join(test_dir, "bar.py"), line=1)
        self.assertDefnMatches2(buf, foo_py_positions[1],
            ilk="variable", name="bar", line=2, citdl="int",
            path=join(test_dir, "bar.py"), )
        
    @tag("bug99108")
    def test_scope_bounds(self):
        test_dir = join(self.test_dir, "scope_bounds")
        foo_content, foo_positions = unmark_text(dedent("""\
            import os, sys, ibix
            # And a comment
            def test1(i):
                b = 0;
                if i > 0:
                    b = i
                def cheeseboogie(j):
                    return b + j
                return cheeseboogie<2>(i + 1)

            t = test<1>1(0)
            print(t)
        """))
        path = join(test_dir, "scope_bounds.py")
        writefile(path, foo_content)
        buf = self.mgr.buf_from_path(path, lang=self.lang)
        self.assertDefnMatches2(buf, foo_positions[1],
            ilk="function", name="test1", line=3,
            scopestart=1, scopeend=0, path=path, )
        self.assertDefnMatches2(buf, foo_positions[2],
            ilk="function", name="cheeseboogie", line=7,
            scopestart=3, scopeend=9, path=path, )
        
    @tag("bug99108")
    def test_lpath(self):
        test_dir = join(self.test_dir, "test_defn")
        foo_content, foo_positions = unmark_text(dedent("""\
            import os, sys, ibix
            # And a comment
            class C(object):
                b = 0
                def foo(self, a, b):
                    x = 3
                    y = 3 + x
                    def inner():
                        return a + b
                    return inner<1>() + x + y

            c = C<2>()
            print(c.f<3>oo(4, 6))
        """))
        path = join(test_dir, "lpath.py")
        writefile(path, foo_content)
        buf = self.mgr.buf_from_path(path, lang=self.lang)
        self.assertDefnMatches2(buf, foo_positions[1],
            ilk="function", name="inner", line=8,
            lpath=["C", "foo"],
            scopestart=5, scopeend=10, path=path, )
        self.assertDefnMatches2(buf, foo_positions[2],
            ilk="class", name="C", line=3,
            lpath=[],
            scopestart=1, scopeend=0, path=path, )
        self.assertDefnMatches2(buf, foo_positions[3],
            ilk="function", name="foo", line=5,
            lpath=["C"],
            scopestart=3, scopeend=10, path=path, )
        
    @tag("bug99177")
    def test_argument_defn_line(self):
        test_dir = join(self.test_dir, "argument_defn_line")
        foo_content, foo_positions = unmark_text(dedent("""\
            import os, sys, ibix
            # And a comment
            def test1(ibix,
                      llama):
                b = lla<1>ma;
                if i > 0:
                    b = i
                def cheeseboogie(jammie):
                    return b + jam<2>mie
                return cheeseboogie>(ibix<3> + 1)

            t = test1(0)
            print(t)
        """))
        path = join(test_dir, "scope_bounds.py")
        writefile(path, foo_content)
        buf = self.mgr.buf_from_path(path, lang=self.lang)
        # Although llama is defined at line 4,
        # we only get enough information to tie it to the function
        # defined at line 3
        self.assertDefnMatches2(buf, foo_positions[1],
            ilk="argument", name="llama", line=3,
            path=path)
        self.assertDefnMatches2(buf, foo_positions[2],
            ilk="argument", name="jammie", line=8,
            path=path)
        self.assertDefnMatches2(buf, foo_positions[3],
            ilk="argument", name="ibix", line=3, path=path, )

    @tag("bug99178")
    def test_argument_defn_for_loop(self):
        test_dir = join(self.test_dir, "argument_defn_for_loop")
        foo_content, foo_positions = unmark_text(dedent("""\
            import os, sys, ibix
            # And a comment
            class Bickle(Frog):
                def test1():
                    for hit in hits:
                        elem, scoperef = hit<1>
                        for bickle, child, dog in elem:
                            if child<2>.tag == "variable":
                                print "Yes, found it"
                                return True
                    return False
            b = Bickle()
            print(b.test1())
        """))
        path = join(test_dir, "defn_for_loop.py")
        writefile(path, foo_content)
        buf = self.mgr.buf_from_path(path, lang=self.lang)
        self.assertDefnMatches2(buf, foo_positions[1],
            ilk="variable", name="hit", line=5,
            path=path)
        self.assertDefnMatches2(buf, foo_positions[2],
            ilk="variable", name="child", line=7,
            path=path)

    @tag("bug99205")
    def test_argument_in_with(self):
        test_dir = join(self.test_dir, "argument_in_with")
        foo_content, foo_positions = unmark_text(dedent("""\
            import os, sys, ibix
            # And a comment
            class Bickle(Frog):
                def test1(self, zog):
                    with self.db.lookup(zog) as cu:
                        for a, b in cu<1>.search():
                            return a<2> + b<3>
            b = Bickle()
            print(b.test1())
        """))
        path = join(test_dir, "in_with.py")
        writefile(path, foo_content)
        buf = self.mgr.buf_from_path(path, lang=self.lang)
        self.assertDefnMatches2(buf, foo_positions[1],
            ilk="variable", name="cu", line=5,
            path=path)
        self.assertDefnMatches2(buf, foo_positions[2],
            ilk="variable", name="a", line=6,
            path=path)
        self.assertDefnMatches2(buf, foo_positions[3],
            ilk="variable", name="b", line=6,
            path=path)

    @tag("bug99205")
    def test_argument_in_except(self):
        test_dir = join(self.test_dir, "argument_in_except")
        foo_content, foo_positions = unmark_text(dedent("""\
            import os, sys, ibix
            # And a comment
            class Bickle(Frog):
                def test1(self, zog):
                    try:
                        a = zog / 0
                    except ZeroDivideError as ex:
                        print "error: %s" % ex<1>.message
                    return 41
            b = Bickle()
            print(b.test1())
        """))
        path = join(test_dir, "in_except.py")
        writefile(path, foo_content)
        buf = self.mgr.buf_from_path(path, lang=self.lang)
        self.assertDefnMatches2(buf, foo_positions[1],
            ilk="variable", name="ex", line=7,
            path=path)

    def test_defn_at_defn(self):
        """Test that finding the definition at the declaration will return a
        valid definition"""
        test_dir = join(self.test_dir, "defn_at_defn")
        content, pos = unmark_text(dedent("""\
            class Foo<1>Class(object):
                prop<2> = 3
                def method<3>(self):
                    local_<4>var = 5
        """))
        path = join(test_dir, "defn_at_defn.py")
        writefile(path, content)
        buf = self.mgr.buf_from_path(path, lang=self.lang)
        lines = lines_from_pos(content, pos)
        self.assertDefnMatches2(buf, pos[1], line=lines[1],
                                ilk="class", name="FooClass", path=path)
        self.assertDefnMatches2(buf, pos[2], line=lines[2],
                                ilk="variable", name="prop", path=path)
        self.assertDefnMatches2(buf, pos[3], line=lines[3],
                                ilk="function", name="method", path=path)
        self.assertDefnMatches2(buf, pos[4], line=lines[4],
                                ilk="variable", name="local_var", path=path)

class PythonDocTestCase(CodeIntelTestCase):
    lang = "Python"
    test_dir = join(os.getcwd(), "tmp")

    @tag("trg")
    def test_trg_pythondoc_tags(self):
        name = "%s-complete-pythondoc-tags" % (self.lang.lower(),)
        self.assertNoTrigger("@")
        self.assertNoTrigger(" @")
        self.assertNoTrigger("#i @")
        self.assertTriggerMatches("# @", name=name, pos=3)
        self.assertTriggerMatches("#@", name=name, pos=2)
        self.assertTriggerMatches("#\t@", name=name, pos=3)
        self.assertTriggerMatches("#    @", name=name, pos=6)

    def test_pythondoc_tags(self):
        cplns = [
          ('variable', 'def'), ('variable', 'defreturn'),
          ('variable', 'exception'), ('variable', 'keyparam'),
          ('variable', 'link'), ('variable', 'linkplain'),
          ('variable', 'param'), ('variable', 'return'),
          ('variable', 'see')
        ]
        self.assertCompletionsAre("# @", cplns)


class TrgTestCase(CodeIntelTestCase):
    lang = "Python"
    test_dir = join(os.getcwd(), "tmp")

    def test_preceding_trg_from_pos(self):
        self.assertNoPrecedingTrigger("os.uname <|><$>")
        self.assertNoPrecedingTrigger("os.path.join<$>(<|>")

        self.assertPrecedingTriggerMatches("f.bar(<$> <|>",
            name="%s-calltip-call-signature" % self.lang.lower(), pos=6)
        self.assertPrecedingTriggerMatches("f.bar(<$><|>",
            name="%s-calltip-call-signature" % self.lang.lower(), pos=6)

        self.assertPrecedingTriggerMatches(
            "os.path.join(os.path.dirname('foo<$><|>",
            name="%s-calltip-call-signature" % self.lang.lower(), pos=29)
        self.assertPrecedingTriggerMatches(
            "os.path.join(os.path.dirname<$>('foo<|>",
            name="%s-calltip-call-signature" % self.lang.lower(), pos=13)
        self.assertNoPrecedingTrigger(
            "os.path.join<$>(os.path.dirname('foo<|>")
        
        self.assertPrecedingTriggerMatches(
            "os.path.join<|><$>",
            name="%s-complete-object-members" % self.lang.lower(), pos=8)
        self.assertNoPrecedingTrigger(
            "os.path<$>.join<|>")
        
        self.assertPrecedingTriggerMatches(
            dedent("""\
                os.path.join(  # try to (screw ' {] ) this up
                    os.path.dirname('foo<$><|>
            """),
            name="%s-calltip-call-signature" % self.lang.lower(), pos=66)
        self.assertPrecedingTriggerMatches(
            dedent("""\
                os.path.join(  # try to (screw ' {] ) this up
                    os.path.dirname<$>('foo<|>
            """),
            name="%s-calltip-call-signature" % self.lang.lower(), pos=13)

        # Test in a comment.
        self.assertPrecedingTriggerMatches(
            dedent("""\
                #
                # os.path.join(
                #    os.path.dirname<$>('foo<|>
                #
            """),
            name="%s-calltip-call-signature" % self.lang.lower(), pos=17)

        # Test in a doc string.
        self.assertPrecedingTriggerMatches(
            dedent('''
                def foo():
                    """blah blah blah
                        os.path.join(
                           os.path.dirname<$>('foo<|>
                    """
                    pass
            '''),
            name="%s-calltip-call-signature" % self.lang.lower(), pos=55)

        # Test out-of-range calltip
        self.assertPrecedingTriggerMatches(
            "foo(bar('hi'), <|><$>",
            name="%s-calltip-call-signature" % self.lang.lower(), pos=4)

    # this test passes, but I don't know why -- it doesn't work in the UI.
    def test_preceding_with_comments(self):
        self.assertPrecedingTriggerMatches(
            "import os\n# won't be set up correctly (with respect to settings).\nos.abort(os.access(<$><|>",
            name="%s-calltip-call-signature" % self.lang.lower(), pos=85)
        self.assertPrecedingTriggerMatches(
            "import os\n# won't be set up correctly (with respect to settings).\nos.abort(<$>os.access(<|>",
            name="%s-calltip-call-signature" % self.lang.lower(), pos=75)

    @tag("bug70627", "knownfailure")
    def test_preceding_with_numeric(self):
        self.assertPrecedingTriggerMatches(
            "c.command2k<$><|>",
            name="%s-calltip-call-signature" % self.lang.lower(), pos=2)
 
    def test_import_triggers(self):
        self.assertNoPrecedingTrigger("import<|><$>")

        self.assertPrecedingTriggerMatches("import <|><$>",
            name="%s-complete-available-imports" % self.lang.lower(), pos=7)
        self.assertPrecedingTriggerMatches("from xml import <|><$>",
            name="%s-complete-module-members" % self.lang.lower(), pos=16)
        self.assertPrecedingTriggerMatches("from xml import (dom, <|><$>",
            name="%s-complete-module-members" % self.lang.lower(), pos=22)

    def test_complete_available_imports(self):
        name = "%s-complete-available-imports" % self.lang.lower()
        self.assertTriggerMatches("import <|>", name=name)
        self.assertTriggerMatches("from <|>", name=name)
        self.assertNoTrigger("Ximport <|>", None)
        self.assertNoTrigger("Xfrom <|>", None)
        self.assertTriggerDoesNotMatch(r"from FOO\\n   import <|>", name=name)

        self.assertTriggerDoesNotMatch(r"import FOO.<|>",
                name="%s-complete-object-members" % self.lang.lower())
        self.assertTriggerMatches(r"import FOO.<|>", name=name)

        # Python import-line trigger should add the 'imp_prefix' extra
        # trigger data for subsequent evaluation.
        self.assertTriggerMatches("import <|>", name=name,
                                  imp_prefix=())
        self.assertTriggerMatches("import FOO.<|>", name=name,
                                  imp_prefix=('FOO',))
        self.assertTriggerMatches("import FOO.BAR.<|>", name=name,
                                  imp_prefix=('FOO', 'BAR'))
        self.assertTriggerMatches("from <|>", name=name,
                                  imp_prefix=())
        self.assertTriggerMatches("from FOO.<|>", name=name,
                                  imp_prefix=('FOO',))
        self.assertTriggerMatches("from FOO.BAR.<|>", name=name,
                                  imp_prefix=('FOO', 'BAR'))

    def test_complete_module_members(self):
        name = "%s-complete-module-members" % self.lang.lower()
        self.assertTriggerMatches("from FOO import <|>", name=name)
        self.assertTriggerMatches("from FOO import BAR, <|>", name=name)
        self.assertTriggerMatches("from FOO\timport BAR, <|>", name=name)
        self.assertTriggerMatches("from FOO\t import BAR, <|>", name=name)
        self.assertTriggerMatches("from FOO.BAZ import <|>", name=name)
        self.assertTriggerMatches("from FOO.BAZ import BAR, <|>", name=name)
        self.assertTriggerMatches(r"from FOO\\n   import <|>", name=name)
        self.assertTriggerMatches("from FOO import (BAR, <|>", name=name)
        self.assertTriggerMatches("from FOO import (<|>", name=name)

        self.assertNoTrigger("from FOO import (BAR.<|>")
        self.assertNoTrigger("from FOO import BAR.<|>")
        self.assertNoTrigger("from FOO import (BAR, BAZ.<|>")
        self.assertNoTrigger("from FOO import BAR, BAZ.<|>")

        self.assertTriggerMatches("from FOO import <|>", name=name,
                                  imp_prefix=('FOO',))
        self.assertTriggerMatches("from FOO.BAR import <|>", name=name,
                                  imp_prefix=('FOO', 'BAR',))
        self.assertTriggerMatches("from \tFOO.BAR   import <|>", name=name,
                                  imp_prefix=('FOO', 'BAR',))
        self.assertTriggerMatches("from\tFOO.BAR\timport <|>", name=name,
                                  imp_prefix=('FOO', 'BAR',))

    def test_calltip_call_signature(self):
        self.assertTriggerMatches("FOO(<|>",
                                  name="%s-calltip-call-signature" % self.lang.lower())
        self.assertTriggerMatches("FOO.BAR(<|>",
                                  name="%s-calltip-call-signature" % self.lang.lower())
        self.assertTriggerMatches("FOO().BAR(<|>",
                                  name="%s-calltip-call-signature" % self.lang.lower())
        self.assertTriggerMatches("FOO('blah').BAR(<|>",
                                  name="%s-calltip-call-signature" % self.lang.lower())
        self.assertNoTrigger("def foo(<|>")
        self.assertNoTrigger("class Foo(<|>")
        self.assertTriggerMatches("class Foo(bar(<|>",
                                  name="%s-calltip-call-signature" % self.lang.lower())

    @tag("knownfailure", "bug63697")
    def test_non_calltip_trgs(self):
        self.assertNoTrigger("if (<|>")
        self.assertNoTrigger("if(<|>")
        self.assertNoTrigger("elif (<|>")
        self.assertNoTrigger("elif(<|>")
        self.assertNoTrigger("foo in (<|>")

        name = "%s-complete-module-members" % self.lang.lower()
        self.assertNoTrigger("import (<|>")
        self.assertNoTrigger("import(<|>")
        self.assertTrigger("from sys import (<|>", name=name)
        self.assertTrigger("from sys import(<|>", name=name)
        self.assertNoTrigger("from (<|>")
        self.assertNoTrigger("from(<|>")

    @tag("knownfailure") # this trigger isn't yet implemented
    def test_complete_available_classes(self):
        self.assertTriggerMatches("class Base: pass\nclass FOO(<|>",
            name="%s-complete-available-classes" % self.lang.lower(),
            consumed=())
        self.assertTriggerMatches("class Base: pass\nclass FOO(BAR, <|>",
            name="%s-complete-available-classes" % self.lang.lower(),
            consumed=('BAR',))
        self.assertTriggerMatches("class Base: pass\nclass FOO(BAR, BAZ, <|>",
            name="%s-complete-available-classes" % self.lang.lower(),
            consumed=('BAR','BAZ'))

    @tag("bug62277")
    def test_decorators(self):
        self.assertTriggerMatches("@bar(<|>)\ndef baz(): pass",
                                  name="%s-calltip-call-signature" % self.lang.lower())
        self.assertTriggerMatches("@foo.bar(<|>)\ndef baz(): pass",
                                  name="%s-calltip-call-signature" % self.lang.lower())
        self.assertTriggerMatches("@foo.<|>bar()\ndef baz(): pass",
                                  name="%s-complete-object-members" % self.lang.lower())

        self.assertCITDLExprIs("@bar(<|>)\ndef baz(): pass", "bar")
        self.assertCITDLExprIs("@foo.bar(<|>)\ndef baz(): pass", "foo.bar")
        self.assertCITDLExprIs("@foo.<|>bar()\ndef baz(): pass", "foo")

    def test_complete_available_exceptions(self):
        name = "%s-complete-available-exceptions" % self.lang.lower()
        self.assertTriggerMatches("except <|>",
                                  name=name)
        self.assertTriggerMatches("  except <|>",
                                  name=name)
        self.assertTriggerMatches("\texcept <|>",
                                  name=name)
        #self.assertTriggerMatches("\texcept Ex<|>",
        #                          name=name, implicit=False)

    def test_complete_magic_symbols(self):
        name = "%s-complete-magic-symbols" % self.lang.lower()
        self.assertTriggerMatches("__<|>", name=name, symbolstype="global")
        self.assertNoTrigger("_<|>_", None)
        self.assertNoTrigger("___<|>", None)

        self.assertTriggerMatches("def __<|>", name=name, symbolstype="def")
        self.assertTriggerMatches("if __<|>", name=name, symbolstype="global",
                                  text="if")

    def test_trigger_local_symbols(self):
        name = "%s-complete-local-symbols" % self.lang.lower()
        self.assertTriggerMatches("im<|>p", name=name)
        self.assertNoTrigger("foo.im<|>p")
        self.assertNoTrigger("i<|>mp")
        self.assertNoTrigger("imp<|>")
        self.assertTriggerMatches("(im<|>p", name=name)
        self.assertNoTrigger("(i<|>")
        self.assertNoTrigger("(imp<|>")
        # Ensure don't override another completion type.
        self.assertNoTrigger("import fo<|>")
        self.assertNoTrigger("from fo<|>")
        self.assertNoTrigger("from collections import fo<|>")
        self.assertNoTrigger("class fo<|>")
        self.assertNoTrigger("def fo<|>")
        self.assertNoTrigger("except fo<|>")


class CodeintelPythonTestCase(CodeIntelTestCase):
    lang = "Python"
    _pyversion = None
    @property
    def python_version(self):
        if self._pyversion is None:
            langintel = self.mgr.langintel_from_lang(self.lang)
            ver, _, _, _, _ = langintel.python_info_from_env(self.mgr.env)
            # ver is a string like "2.7", but versions should be stored as tuples
            self._pyversion = tuple([int(x) for x in ver.split('.')])
        return self._pyversion

    def setUp(self):
        if self.lang == "Python":
            major_version = 2
        elif self.lang == "Python3":
            major_version = 3
        self.assertEquals(self.python_version[0], major_version)


class CplnTestCase(CodeintelPythonTestCase):
    test_dir = join(os.getcwd(), "tmp")

    def test_bug66812(self):
        content, positions = unmark_text(dedent("""
                def main():
                    class foo:
                        def __init__ (self):
                            self.age = 0
                            self.<1>height = 0
                
                    bar = foo()
                    bar.<2>age = 12
                    
                    print bar.age
                    
                if __name__ == "__main__":
                    main()
            """))
        self.assertCompletionsInclude(markup_text(content, positions[1]),
            [("variable", "age")])
        self.assertCompletionsInclude(markup_text(content, positions[2]),
            [("variable", "age")])

    def test_assign_with_diff_scopes(self):
        content, positions = unmark_text(dedent("""
                class Outer:
                    class Inner:
                        inner_var = 0
                    outer_var = 0
                
                def main():
                    class foo:
                        def __init__ (self):
                            self.age = 0
                            self.<1>height = 0
                
                    bar = foo()
                    bar.<2>age = 12
                    inner = Outer.Inner()
                    inner.<3>inner_var
                    
                    print bar.age
                    
                if __name__ == "__main__":
                    main()
            """))
        self.assertCompletionsInclude(markup_text(content, positions[1]),
            [("variable", "age")])
        self.assertCompletionsInclude(markup_text(content, positions[2]),
            [("variable", "age")])
        self.assertCompletionsInclude(markup_text(content, positions[3]),
            [("variable", "inner_var")])

    def test_curr_calltip_arg_range_explicit(self):
        # Test calltip range handling in comments...
        self.assertCurrCalltipArgRange("# foo(<+><|>", "foo()", (0,0),
                                       implicit=False)
        self.assertCurrCalltipArgRange("# foo(<+><|>", "foo(a, b, c)", (4,5),
                                       implicit=False)
        self.assertCurrCalltipArgRange("# foo(<+>art,<|>", "foo(a, b, c)", (7,8),
                                       implicit=False)

        # ...and in strings.
        self.assertCurrCalltipArgRange("' foo(<+><|> '", "foo()", (0,0),
                                       implicit=False)
        self.assertCurrCalltipArgRange("' foo(<+><|> '", "foo(a, b, c)", (4,5),
                                       implicit=False)
        self.assertCurrCalltipArgRange("' foo(<+>art,<|> '", "foo(a, b, c)", (7,8),
                                       implicit=False)

    def test_curr_calltip_arg_range(self):
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

        self.assertCurrCalltipArgRange("os.path.join(<+>'hi', 'there<|>",
                                       "join(a, *p)\nJoin two or...",
                                       (8, 10))
        self.assertCurrCalltipArgRange("main(<+>sys.argv, opts={'a', 'b,c'}, indent=4<|>)",
                                       "main(args, opts, indent, *more)",
                                       (17, 23))
        self.assertCurrCalltipArgRange("Foo.foo(<+>(hi, there), blah<|>)",
                                       "foo(a,b,c)",
                                       (6, 7))

        self.assertCurrCalltipArgRange("foo(<+>)<|>", "foo(a, b, c)",
                                       (-1, -1))
        self.assertCurrCalltipArgRange("foo(<+>a=(hi, 'there()'))<|>",
                                       "foo(a, b, c)", (-1, -1))
        self.assertCurrCalltipArgRange("foo(<+>a=(hi, 'there()'), <|>)",
                                       "foo(a, b, c)", (7, 8))

        for content in ["foo(<+>a=(hi, 'there()'), <|>)",
                        "foo(<+>{'hi()', bob[1]}, blah<|>"]:
            self.assertCurrCalltipArgRange(content, "foo(a, b, c)", (7, 8))

        #XXX Add test cases for keyword and ellipsis args when have added
        #    support for that in BasicCalltipBufferMixin.

    def test_complete_object_members(self):
        name = "%s-complete-object-members" % self.lang.lower()
        self.assertNoTrigger("'FOO.<|>'")
        self.assertTriggerMatches("FOO.<|>", pos=4,
                                  name="%s-complete-object-members" % self.lang.lower())
        self.assertTriggerMatches("blah()\nFOO.<|>", pos=11,
                                  name="%s-complete-object-members" % self.lang.lower())
        self.assertTriggerMatches("blah()\r\nFOO.<|>", pos=12,
                                  name="%s-complete-object-members" % self.lang.lower())
        self.assertTriggerMatches("FOO.BAR.<|>", pos=8,
                                  name="%s-complete-object-members" % self.lang.lower())
        self.assertNoTrigger(".<|>")
        self.assertTriggerMatches(r"FOO\\n  .<|>",
                                  name="%s-complete-object-members" % self.lang.lower())
        self.assertTriggerMatches("FOO().BAR.<|>",
                                  name="%s-complete-object-members" % self.lang.lower())
        self.assertTriggerMatches("FOO('blah').BAR.<|>",
                                  name="%s-complete-object-members" % self.lang.lower())

        self.assertNoTrigger("# FOO.<|>")
        self.assertTriggerMatches("# FOO.<|>", name=name, implicit=False)
        self.assertTriggerMatches("#FOO.<|>", name=name, implicit=False)

        name = "%s-complete-object-members" % self.lang.lower()
        markedup_content = dedent("""\
            import sys
            sys.<|>path    # should have path in completion list
        """)
        self.assertCompletionsInclude(markedup_content,
            [("variable", "path"), ("function", "exc_info")])

        markedup_content = dedent("""\
            import sys
            sys.path.<|>append    # should have append in completion list
        """)
        self.assertCompletionsInclude(markedup_content,
            [("function", "append"), ("function", "reverse")])

        markedup_content = dedent("""\
            class Foo:
                def bar(self): pass
            f = Foo()
            f.<|>
        """)
        self.assertCompletionsInclude(markedup_content, [("function", "bar")])

    def test_negative_cpln_assertion(self):
        self.assertCompletionsDoNotInclude(
            "import os\nos.<|>rename()",
            [("variable", "stdout")])

    def test_multilevel_import(self):
        content, positions = unmark_text(dedent("""\
            import os.path
            print os.path.<1>sep
            os.<2>stat('foo')
        """))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("function", "join"), ("variable", "sep"), ("module", "stat")])
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[2]),
            [("function", "stat"), ("function", "rmdir"), ("module", "path")])

    @tag("bug59927")
    def test_import_completion(self):
        content, positions = unmark_text(dedent("""\
            import xml.dom.domreg.<1>
        """))
        self.assertCompletionsDoNotInclude(
            markup_text(content, pos=positions[1]),
            [("module", "xml.dom.domreg")])

        content, positions = unmark_text(dedent("""\
            from django.views.decorators.auth import login_required
            from django.core.extensions import render_to_response, get_object_or_404
            import datetime
            
            @login_required
            def status(request):
                u = request.user
                account = u.get_accounts_account()
                import xml.<1>dom
        """))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("module", "dom")])

        content, positions = unmark_text(dedent("""\
            import xml.<1>sax.<2>foo
        """))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("module", "sax")])
        self.assertCompletionsDoNotInclude(
            markup_text(content, pos=positions[1]),
            [("module", "sax.xmlreader"), ("module", ".")])
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[2]),
            [("module", "xmlreader")])

        # once there was a bug thinking that pickletools somehow
        # fit in as pickle.[ools]
        content, positions = unmark_text(dedent("""\
            import pickle.<1>nothing
        """))
        self.assertCompletionsDoNotInclude(
            markup_text(content, pos=positions[1]),
            [("module", "ools")])

        content, positions = unmark_text(dedent("""\
            from xml.<1>sax.<2>xmlreader import
        """))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("module", "sax")])
        self.assertCompletionsDoNotInclude(
            markup_text(content, pos=positions[1]),
            [("module", "sax.xmlreader")])
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[2]),
            [("module", "xmlreader")])

        content, positions = unmark_text(dedent("""\
            from xml.sax import <1>
        """))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("module", "xmlreader"), ("function", "parse")])

        self.assertCompletionsInclude(
            "from pickle import <|>",
            [("class", "PickleError"), ("function", "dump")])
        
    def test_import_alias(self):
        content, positions = unmark_text(dedent("""\
            import sys as mysys
            from os import rename as myrename
            mysys.<1>stderr.write('boom')
            myrename(<2>'foo', 'bar')
        """))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("variable", "stderr"), ("function", "displayhook")])
        if self.python_version >= (3, 3):
            calltip_text = dedent("""\
                rename(src, dst, *, src_dir_fd=None, dst_dir_fd=None)
                Rename a file or directory. If either src_dir_fd or
                dst_dir_fd is not None, it should be a file descriptor open
                to a directory, and the respective path string (src or dst)
                should be relative; the path will then be relative to that
                directory.""")
        else:
            calltip_text = "rename(old, new)\nRename a file or directory."
        self.assertCalltipIs(
            markup_text(content, pos=positions[2]),
            calltip_text)

    @tag("bug55047")
    def test_os_path(self):
        # The "os" module in the stdlib effectively uses:
        #   import os.path as path
        # (as a work-around for os.py actually doing platform-specific
        # stuff) so that the following can work. This is an important
        # use case for Python programmers.
        self.assertCompletionsInclude(
            "import os\nos.path.<|>abspath",
            [("function", "abspath")])

    def test_time(self):
        self.assertCompletionsInclude(
            "import time\ntime.<|>time",
            [("function", "time")])

    def test_continue_with_unresolvable_base_class(self):
        content, positions = unmark_text(dedent("""\
            from walla.walla import Washington
            class Bugs(Washington):
                bunny = "what's up doc"
            Bugs.<1>bunny
        """))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("variable", "bunny")])

    def test_star_imports(self):
        self.assertCompletionsInclude(
            "from os import *\nsep.<|>join()",
            [("function", "join"), ("function", "strip")])
        self.assertCompletionsInclude(
            "from os import *\npath.<|>join",
            [("function", "split")])

    @tag("bug70014")
    def test_more_star_imports(self):
        test_dir = join(self.test_dir, "test_more_star_imports")
        foo_py_content, foo_py_positions = unmark_text(dedent("""\
            from mockdjango.db import models
            models.<1>CharField
        """))

        manifest = [
            ("mockdjango/__init__.py", ""),
            ("mockdjango/db/__init__.py", ""),
            ("mockdjango/db/models/__init__.py", dedent("""
                from mockdjango.db.models.fields import *
             """)),
            ("mockdjango/db/models/fields/__init__.py", dedent("""
                class Field(object):
                    pass
                class AutoField(Field):
                    pass
                class BooleanField(Field):
                    pass
                class CharField(Field):
                    pass
                class DateField(Field):
                    pass
             """)),
            ("foo.py", foo_py_content),
        ]
        for file, content in manifest:
            path = join(test_dir, file)
            writefile(path, content)

        buf = self.mgr.buf_from_path(join(test_dir, "foo.py"), lang=self.lang)
        self.assertCompletionsInclude2(buf, foo_py_positions[1],
            [("class", "Field"), ("class", "CharField")])

    @tag("bug54258")
    def test_multilevel_import2(self):
        content, positions = unmark_text(dedent("""\
            import xml.dom.minidom
            xml.dom.<3>Node
        """))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[3]),
            [("class", "Node"), ("variable", "INDEX_SIZE_ERR")])

    def test_some_more_imports(self):
        # from module import submodule as alias
        content, positions = unmark_text(dedent("""\
            from xml.dom import minidom as mini
            mini.<1>parse
        """))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("function", "parse")])

        # from module import symbol as alias
        content, positions = unmark_text(dedent("""\
            from xml.sax import default_parser_list as parsers
            parsers.<1>reverse()
        """))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("function", "reverse")])

        content, positions = unmark_text(dedent("""\
            from xml.sax import handler
            handler.<1>DTDHandler()
        """))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("class", "DTDHandler")])
        content, positions = unmark_text(dedent("""\
            from xml.sax import handler as hdlr
            hdlr.<1>DTDHandler()
        """))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("class", "DTDHandler")])

    @tag("knownfailure")
    def test_completion_packages(self):
        # even if package completion isn't good
        # names deduced from import statements should show up
        # at the completion of packages or submodules
        content, positions = unmark_text(dedent("""\
            import a.b.c
            a.<1>b.<2>
        """))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("b",)])
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[2]),
            [("c",)])

    @tag("bug56007")
    def test_yet_more_imports(self):
        test_dir = join(self.test_dir, "test_yet_more_imports_1")
        foo_py_content, foo_py_positions = unmark_text(dedent("""\
            import mytwisted
            mytwisted.<1>Interface
        """))

        manifest = [
            ("mytwisted/__init__.py", dedent("""
                from myzope.interface import Interface
             """)),
            ("myzope/__init__.py", ""),
            ("myzope/interface/__init__.py", dedent("""
                from myzope.interface.interface import Interface
             """)),
            ("myzope/interface/interface.py", dedent("""
                class InterfaceClass:
                    def interfaces(self): pass
                    def getBases(self): pass
                Interface = InterfaceClass()
             """)),
            ("foo.py", foo_py_content),
        ]
        for file, content in manifest:
            path = join(test_dir, file)
            writefile(path, content)

        buf = self.mgr.buf_from_path(join(test_dir, "foo.py"), lang=self.lang)
        self.assertCompletionsInclude2(buf, foo_py_positions[1],
            [("variable", "Interface")])


    def test_class_calltip(self):
        content, positions = unmark_text(dedent("""\
            class Alice:
                def __init__(self, a):
                    'give me an A'
            class Bob:
                def __init__(self, b):
                    'give me a B'
            class Carl(Alice, Bob):
                pass
            class Dan(Bob, Carl):
                pass
            class Earl(Carl):
                def duke_of(self):
                    return True
            class Frank:
                "Frank(let's be real)"
            class Gehry: pass
            a = Alice(<1>)
            c = Carl(<2>)
            d = Dan(<3>)
            e = Earl(<4>)
            f = Frank(<5>)
            g = Gehry(<6>)
        """))
        self.assertCalltipIs(markup_text(content, pos=positions[1]),
                             "Alice(a)\ngive me an A")
        self.assertCalltipIs(markup_text(content, pos=positions[2]),
                             "Alice(a)\ngive me an A")
        self.assertCalltipIs(markup_text(content, pos=positions[3]),
                             "Bob(b)\ngive me a B")
        self.assertCalltipIs(markup_text(content, pos=positions[4]),
                             "Alice(a)\ngive me an A")
        self.assertCalltipIs(markup_text(content, pos=positions[5]),
                             "Frank(let's be real)")
        self.assertCalltipIs(markup_text(content, pos=positions[6]),
                             "Gehry()")

    @tag("bug94079", "knownfailure")
    def test_enumerate_calltip(self):
        # This tests a case you can't get from pythoncile'd files:
        # - a class with a docstring
        # - has a ctor with*out* a docstring or a signature
        if self.python_version >= (2, 6):
            self.assertCalltipIs("enumerate(<|>",
                "enumerate(iterable[, start]) -> iterator for index, value of iterable\n"
                "Return an enumerate object.  iterable must be another object "
                "that supports iteration.  The enumerate object yields pairs "
                "containing a count (from start, which defaults to zero) and "
                "a value yielded by the iterable argument. enumerate is useful "
                "for obtaining an indexed list: (0, seq[0]), (1, seq[1]), "
                "(2, seq[2]), ...")
        else:
            self.assertCalltipIs("enumerate(<|>",
                "enumerate(iterable) -> iterator for index, value of iterable\n"
                "Return an enumerate object.  iterable must be another object "
                "that supports iteration.  The enumerate object yields pairs "
                "containing a count (from zero) and "
                "a value yielded by the iterable argument. enumerate is useful "
                "for obtaining an indexed list: (0, seq[0]), (1, seq[1]), "
                "(2, seq[2]), ...")


    def test_wacky_imports(self):
        test_dir = join(self.test_dir, "test_wacky_imports")
        bar_py_content, bar_py_positions = unmark_text(dedent("""\
            from foo import Foo
            Foo.<1>mypackage.<2>mymodule.<3>yo

            import mypackage
            from mypackage import mymodule
            from mypackage import __version__
            mymodule.<4>yo
            __version__.<5>split('.')
            mypackage.<6>yo
        """))

        manifest = [
            ("mypackage/__init__.py", dedent("""
                __version__ = '1.0.0'
                from mymodule import yo
             """)),
            ("mypackage/mymodule.py", dedent("""
                yo = "yo"
             """)),
            ("foo.py", dedent("""
                class Foo:
                    import mypackage.mymodule
             """)),
            ("bar.py", bar_py_content),
        ]
        for file, content in manifest:
            path = join(test_dir, file)
            writefile(path, content)

        buf = self.mgr.buf_from_path(join(test_dir, "bar.py"), lang=self.lang)

        self.assertCompletionsInclude2(buf, bar_py_positions[5],
            [("function", "split"), ("function", "startswith")])
        self.assertCompletionsInclude2(buf, bar_py_positions[1],
                                       [("module", "mypackage")])
        self.assertCompletionsInclude2(buf, bar_py_positions[3],
                                       [("variable", "yo")])

        TEST_IMPORT_FROM_IMPORT = False
        if TEST_IMPORT_FROM_IMPORT:
            # These execise a current limitation in sub-import handling
            # in _members_from_elem and _hit_from_elem_imports.
            self.assertCompletionsInclude2(buf, bar_py_positions[6],
                [("function", "yo"), ("variable", "__version__")])
            self.assertCompletionsInclude2(buf, bar_py_positions[4],
                                           [("function", "yo")])
            self.assertCompletionsInclude2(buf, bar_py_positions[2],
                                           [("module", "mymodule")])

    def test_extradirslib(self):
        test_dir = join(self.test_dir, "test_extradirslib")
        oracle_content, oracle_positions = unmark_text(dedent("""\
            import answers
            print "The ultimate answer is %d" % answers.<1>ULTIMATE
        """))
        manifest = [
            ("lib/answers.py", dedent("""
                __version__ = '1.0.0'
                ULTIMATE = 42
             """)),
            ("oracle.py", oracle_content),
        ]
        for file, content in manifest:
            path = join(test_dir, file)
            writefile(path, content)

        # Hack in our Environment for the Manager. Normally this is
        # passed in when creating the Manager.
        prefs = {}
        prefs["%sExtraPaths" % self.lang.lower()] = join(test_dir, "lib")
        env = SimplePrefsEnvironment(**prefs)
        self.mgr.env = env

        self.assertCompletionsInclude(
            markup_text(oracle_content, pos=oracle_positions[1]),
            [("variable", "ULTIMATE")])


    #TODO: add test case:
    #   mypath.py:
    #       from os.path import *
    #   foo.py:
    #       import mypath
    #       mypath.<|>join

    def test_error_cases(self):
        # At least while using the current Python CILE generating CIX for
        # the following isn't going to work (too many syntax errors).
        markedup_content = dedent("""\
            womba womba
            
            @womba
            foobar
            
            class Foo:
                def bar(self): pass
            f = Foo()
            f.<|>
        """)
        self.assertEvalError(markedup_content,
            log_pattern=re.compile("no %s scan info" % self.lang))

        markedup_content = dedent("""\
            womba womba
            
            @womba
            foobar
            
            class Foo:
                def bar(self): pass
            f = Foo()
            f.bar(<|>
        """)
        self.assertEvalError(markedup_content,
            log_pattern=re.compile("no %s scan info" % self.lang))

    @tag("bug55327")
    def test_skip_class_scope(self):
        # Python eval shouldn't consider the class-level
        # scope as a parent scope when resolving from the top-level.
        content, positions = unmark_text(dedent("""\
            var = "a string"
            class Foo:
                var = 42
                def foo(self):
                    var.<1>strip()  # should hit the string
            class Bar:
                var = ['a', 'list']
                def bar(self):
                    var = {'a': 'dict'}
                    def nested():
                        var.<2>items() # should hit the dict
                    nested()
        """))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [('function', 'strip')])
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[2]),
            [('function', 'items')])

    @tag("bug55327")
    def test_infinite_recursion(self):
        content, positions = unmark_text(dedent("""\
            import cElementTree as ET
            class koDOMTrreView:
                def __init__(self):
                    self.ET = ET.ElementTree()
                def foo(self):
                    ET.<1>ElementTree
        """))
        self.assertEvalError(
            markup_text(content, pos=positions[1]),
            log_pattern=re.compile("could not find data for "
                                   "%s blob 'cElementTree'" % self.lang))

    def test_complete_available_imports(self):
        self.assertCompletionsInclude("import <|>",
            [("module", "sys")])
        self.assertCompletionsDoNotInclude("import <|>",
            [("module", "distutils.command"), # should only have one level
             ("module", "*")])  # built-in should be stripped out

    def test_nodupe_imports(self):
        test_dir = join(self.test_dir, "test_nodupe_imports")
        foo_py_content, foo_py_positions = unmark_text(dedent("""\
            import <1>foo
        """))
        manifest = [
            ("os.py", "pass"),
            ("foo.py", foo_py_content),
        ]
        for file, content in manifest:
            path = join(test_dir, file)
            writefile(path, content)
        self.assertNoDuplicateCompletions(
            markup_text(foo_py_content, pos=foo_py_positions[1]))

    def test_calltip_call_signature(self):
        markedup_content = dedent("""\
            class Foo:
                def bar(self, a):
                    "howdy"
                    pass
            f = Foo()
            f.bar(<|>
        """)
        self.assertCalltipIs(markedup_content, "bar(a)\nhowdy")

    @tag("knownfailure") # this trigger isn't yet implemented
    def test_complete_available_classes(self):
        self.assertCompletionsInclude("class Base: pass\nclass FOO(<|>",
                                      [('class', 'Base')])
        self.assertCompletionsInclude("class FOO: pass\nclass FXX: pass\nclass BAR(FXX, <|>",
                                      [('class', 'FOO')])
        self.assertCompletionsDoNotInclude("class FOO: pass\nclass FXX: pass\nclass BAR(FXX, <|>",
                                      [('class', 'FXX')])
        # this doesn't work because the accessor doesn't go beyond the <|>??
        self.assertCompletionsDoNotInclude("class Base: pass\nclass Baz: pass\nclass FOO(<|>, Baz)",
                                      [('class', 'Baz')])
        self.assertCompletionsDoNotInclude("class Base: pass\nclass Baz: pass\nclass FOO(Baz, Base, <|>",
                                      [('class', 'Baz')])
#    def test_calltip_base_signature(self):
#        self.assertTriggerMatches("""
#class FOO(BAR):
#def BAZ(<|>
#""", name="python-calltip-base-signature")

    def test_citdl_expr_from_trg_simple(self):
        self.assertCITDLExprIs("foo.<|>", "foo")
        self.assertCITDLExprIs("foo.bar.<|>", "foo.bar")
        self.assertCITDLExprIs("foo(bar.<|>", "bar")
        self.assertCITDLExprIs("foo[bar.<|>", "bar")
        self.assertCITDLExprIs("foo{bar.<|>", "bar")
        self.assertCITDLExprIs("foo().<|>", "foo()")
        self.assertCITDLExprIs("foo(a,b).<|>", "foo()")
        self.assertCITDLExprIs("a = foo.<|>", "foo")
        self.assertCITDLExprIs("a = foo(bar.<|>, blam)", "bar")
        self.assertCITDLExprIs("blam()\nfoo.<|>", "foo")
        self.assertCITDLExprIs("blam()\nfoo.bar.<|>", "foo.bar")
    def test_citdl_expr_from_trg_simple2(self):
        self.assertCITDLExprIs("from blah import *\nfoo.bar.<|>", "foo.bar")
    def test_citdl_expr_from_trg_simple3(self):
        self.assertCITDLExprIs("#FOO.<|>", "FOO", implicit=False)
        self.assertCITDLExprIs("# FOO.<|>", "FOO", implicit=False)
    def test_citdl_expr_from_trg_simple4(self):
        self.assertCITDLExprIs("from blah import (a,b)\nfoo.bar.<|>", "foo.bar")
    def test_citdl_expr_from_trg_complex(self):
        self.assertCITDLExprIs("foo(',', (1+2)).<|>", "foo()")
        self.assertCITDLExprIs("foo(',({[', {one:1,two:2}).<|>", "foo()")
        self.assertCITDLExprIs("(',({[', {one:1,two:2}).<|>", "()")
    def test_citdl_expr_from_trg_multiline(self):
        self.assertCITDLExprIs("foo(bar,\nblam.<|>)", "blam")
        self.assertCITDLExprIs("foo(bar,\nblam).spam.<|>", "foo().spam")
        self.assertCITDLExprIs("foo.\\\nbar.<|>", "foo.bar")
        self.assertCITDLExprIs("foo(1, # one\n2).bar.<|>", "foo().bar")
        self.assertCITDLExprIs("foo(1, # o)ne\n2).bar.<|>", "foo().bar")
        self.assertCITDLExprIs("foo(1, # (o)ne\n2).bar.<|>", "foo().bar")
        self.assertCITDLExprIs("foo(1, # (one\n2).bar.<|>", "foo().bar")
        self.assertCITDLExprIs("foo( #this is a ) comment\nb,d).<|>", "foo()")
        self.assertCITDLExprIs("foo\\\n(',({[', {one:1,two:2}).<|>", "foo()")
    def test_citdl_expr_from_trg_extra(self):
        self.assertCITDLExprIs("if foo.<|>(", "foo")
        self.assertCITDLExprIs("elif foo.<|>(", "foo")
        self.assertCITDLExprIs("for foo.<|>(", "foo")
        self.assertCITDLExprIs("while foo.<|>(", "foo")
        self.assertCITDLExprIs("def foo.<|>(", "foo")
        self.assertCITDLExprIs("class foo.<|>(", "foo")
        self.assertCITDLExprIs("import foo.<|>(", "foo")
        self.assertCITDLExprIs("from foo.<|>(", "foo")
        self.assertCITDLExprIs("boo3 foo.<|>(", "foo")

    @tag("bug65672")
    def test_explicit_citdl_expr_with_comments(self):
        # Test we don't include the citdl expression from the comment section
        self.assertCITDLExprIs(dedent("""
            # Guide.
            document.<|>
        """), "document", implicit=False)
        self.assertCITDLExprIs(dedent("""
            \"\"\"Guide.\"\"\"
            document.<|>
        """), "document", implicit=False)
        # Test we still get the citdl expression from a comment
        self.assertCITDLExprIs(dedent("""
            document. # Guide<1>
        """), "Guide", implicit=False)

    @tag("bug52648")
    def test_tkinter(self):
        try:
            import Tkinter
        except ImportError:
            raise TestSkipped("can't test without Tkinter")
        else:
            self.assertCompletionsInclude(dedent("""\
                import Tkinter
                root = Tkinter.Tk()
                root.<|>blah
                """),
                [("function", "wm_iconbitmap"),
                 ("function", "readprofile")])

    @tag("bug62277")
    def test_decorators(self):
        content, positions = unmark_text(dedent("""\
            import os
            def mydeco(arg):
                pass

            @mydeco(<1>42)
            def baz():
                pass

            @os.<2>uname(<3>)
            def bar():
                pass
        """))
        self.assertCalltipIs(
            markup_text(content, positions[1]),
            "mydeco(arg)")
        self.assertCompletionsInclude(
            markup_text(content, positions[2]),
            [("function", "uname"),
             # Could eventually get really smart and know that "os.sep"
             # is not appropriate because it is not callable. Tough,
             # though.
             ("variable", "sep")])
        if self.python_version >= (3, 3):
            calltip_text = dedent("""\
                uname() -> uname_result
                Return an object identifying the current operating system.""")
        else:
            calltip_text = dedent("""\
                uname() -> (sysname, nodename, release, version, machine)
                Return a tuple identifying the current operating system.""")
        self.assertCalltipIs(
            markup_text(content, positions[3]),
            calltip_text)

    @tag("bug65867")
    def test_star_import_kills_subsequent_imports(self):
        if self.python_version >= (3, 3):
            help_text = dedent("""\
                exit([status])
                Exit the interpreter by raising SystemExit(status). If the
                status is omitted or None, it defaults to zero (i.e.,
                success).""")
        else:
            help_text = dedent("""\
                exit([status])
                Exit the interpreter by raising SystemExit(status).""")
        self.assertCalltipIs(
            dedent("""
                from os import *
                from sys import exit
                exit(<|>
            """),
            help_text)

    @tag("bug66214")
    def test_staticmethod(self):
        content, positions = unmark_text(dedent("""\
            class AClass(object):
                def a_method(self, a, b):
                    print "a_method(%r, %r)" % (a, b)
                
                @staticmethod
                def a_staticmethod(c, d):
                    print "a_staticmethod(%r, %r)" % (c, d)

                @classmethod
                def a_classmethod(cls, c, d):
                    print "a_classmethod(%r, %r)" % (c, d)

            a = AClass()
            a.a_method(1,2)
            a.a_staticmethod(<1>1,2)
            a.a_classmethod(<2>1,2)
        """))
        self.assertCalltipIs(
            markup_text(content, pos=positions[1]),
            "a_staticmethod(c, d) - staticmethod")
        self.assertCalltipIs(
            markup_text(content, pos=positions[2]),
            "a_classmethod(c, d) - classmethod")

    def test_string_literals(self):
        content, positions = unmark_text(dedent("""\

            # Standard string completions
            "".<1>join(<2>)
            '\\n'.<3>join()

            # Doc strings
            \"\"\"My String\"\"\".<4>strip()

            # String delimiter inside of doc string (should not trigger)
            \"\"\"My \".<5>String\"\"\"

            # Test we don't get string completions on class like usage:
            class testcls:
                def __init__(self, arg1):
                    self.arg1 = arg1
            testcls("".<6>lower()).<7>xyz;
        """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [('function', 'strip'),
             ('function', 'lower'),
             ('function', 'capitalize')])
        if self.python_version >= (3,):
            self.assertCalltipMatches(markup_text(content, pos=positions[2]),
                r"S\.join\(iterable\) -> str\nReturn a string which is the "
                "concatenation of the strings in.*?the iterable.",
                                      flags=re.DOTALL)
        elif self.python_version >= (2, 6):
            self.assertCalltipMatches(markup_text(content, pos=positions[2]),
                r"S\.join\(iterable\) -> string\nReturn a string which is the "
                "concatenation of the strings in.*?the iterable.",
                                      flags=re.DOTALL)
        else:
            self.assertCalltipIs(markup_text(content, pos=positions[2]),
                "S.join(sequence) -> string\nReturn a string which is the "
                "concatenation of the strings in the sequence.")
        self.assertCompletionsInclude(markup_text(content, pos=positions[3]),
            [('function', 'strip'),
             ('function', 'lower'),
             ('function', 'capitalize')])
        self.assertCompletionsInclude(markup_text(content, pos=positions[4]),
            [('function', 'strip'),
             ('function', 'lower'),
             ('function', 'capitalize')])
        self.assertNoTrigger(markup_text(content, pos=positions[5]))
        self.assertCompletionsInclude(markup_text(content, pos=positions[6]),
            [('function', 'strip'),
             ('function', 'lower'),
             ('function', 'capitalize')])
        # This does not yet work in Python
        #self.assertCompletionsInclude(markup_text(content, pos=positions[7]),
        #    [('variable', 'arg1'), ])

    @tag("bug71789")
    def test_base_class_calltips(self):
        content, positions = unmark_text(dedent(r'''
            class Fruit:
                def isRipe(self): pass
                def isRotten(self): pass
            
            class Orange(Fruit):
                def isFromFlorida(self): pass

            class Tangerine(Orange):
                def isSour(self): pass

            myfruit = Tangerine()
            myfruit.isRipe(<1>)
        '''))
        self.assertCalltipIs(markup_text(content, pos=positions[1]), "isRipe()")

    @tag("bug83524")
    def test_top_level_imports(self):
        content1, positions1 = unmark_text(dedent(r'''
            from x import <1>; # should see "types" and "abspath" here
        '''))

        test_dir = join(self.test_dir, "test_toplevel_imports")
        manifest = [
            ("x.py", dedent("""
                import types
                from os.path import abspath
                def fun(): pass
             """)),
            ("y.py", content1)]
        
        for f, c in manifest:
            path = join(test_dir, f)
            writefile(path, c)

        buf = self.mgr.buf_from_path(join(test_dir, "y.py"), lang=self.lang)
        self.assertCompletionsInclude2(buf, positions1[1],
            [("module", "types"),
             ("function", "abspath"),
             ("function", "fun")])

    @tag("bug45822")
    def test_relative_imports(self):
        content1, positions1 = unmark_text(dedent(r'''
            import fruits
            fruits.<1>xxx
            fruits.Banana.<2>xxx
            gsmith = fruits.GrannySmith()
            gsmith.<3>xxx
        '''))
        content2, positions2 = unmark_text(dedent(r'''
            from fruits import *
            Banana.<2>xxx
            gsmith = GrannySmith()
            gsmith.<3>xxx
        '''))

        test_dir = join(self.test_dir, "test_import_not_on_direct_path")
        manifest = [
            ("foo1.py", content1),
            ("foo2.py", content2),
            ("fruits/__init__.py", dedent("""
                from banana import *
                from apple import GrannySmith
             """)),
            ("fruits/apple.py", dedent("""
                class Apple:
                    def color(self):
                        "what color is the apple?"
                        pass
                class GrannySmith(Apple):
                    def howGreen(self): pass
                class Macintosh(Apple): pass
                class RedDelicious(Apple):
                    def howRed(self): pass
             """)),
            ("fruits/banana.py", dedent("""
                class Banana:
                    def isRipe(self): pass
                    def isFromDole(self): pass
             """)),
        ]
        for f, c in manifest:
            path = join(test_dir, f)
            writefile(path, c)

        buf = self.mgr.buf_from_path(join(test_dir, "foo1.py"), lang=self.lang)
        self.assertCompletionsInclude2(buf, positions1[1],
            [("class", "Banana"),
             ("class", "GrannySmith"),])
        self.assertCompletionsInclude2(buf, positions1[2],
            [("function", "isRipe"),
             ("function", "isFromDole"),])
        self.assertCompletionsInclude2(buf, positions1[3],
            [("function", "howGreen"),
             ("function", "color"),])

        buf = self.mgr.buf_from_path(join(test_dir, "foo2.py"), lang=self.lang)
        self.assertCompletionsInclude2(buf, positions2[2],
            [("function", "isRipe"),
             ("function", "isFromDole"),])
        self.assertCompletionsInclude2(buf, positions2[3],
            [("function", "howGreen"),
             ("function", "color"),])

    @tag("bug88971")
    def test_relative_imports_2(self):
        content, positions = unmark_text(dedent(r'''
            import extlib
            a = extlib.<1>cZip()
            a.<2>xxx
        '''))

        test_dir = join(self.test_dir, "test_relative_imports_2")
        manifest = [
            ("test_extlib.py", content),
            ("extlib/__init__.py", dedent("""
                from my_zip_lib import *
             """)),
            ("extlib/my_zip_lib.py", dedent("""
                class cZip(object):
                    def createZip(self, zipName, files = {}):
                        pass
             """)),
        ]
        for f, c in manifest:
            path = join(test_dir, f)
            writefile(path, c)

        buf = self.mgr.buf_from_path(join(test_dir, "test_extlib.py"), lang=self.lang)
        self.assertCompletionsInclude2(buf, positions[1],
            [("class", "cZip")])
        self.assertCompletionsInclude2(buf, positions[2],
            [("function", "createZip")])

    def test_smart_parent_imports(self):
        content, positions = unmark_text(dedent(r'''
            from komodo_and.<1>models import <2>Topic
            from komodo_or import <3>xxx
            t = Topic(<4>)
            t.<5>xxx
        '''))

        test_dir = join(self.test_dir, "test_smart_parent_imports")
        manifest = [
            ("komodo_and/views.py", content),
            ("komodo_and/__init__.py", ""),
            ("komodo_and/models.py", dedent("""
                class Topic(object):
                    def createTopic(self, name):
                        pass
                def Something():
                    pass
             """)),
            ("komodo_or/__init__.py", ""),
            ("komodo_or/kor.py", ""),
        ]
        for f, c in manifest:
            path = join(test_dir, f)
            writefile(path, c)

        buf = self.mgr.buf_from_path(join(test_dir, "komodo_and", "views.py"),
                                     lang=self.lang)
        self.assertCompletionsAre2(buf, positions[1],
            [("module", "models"),
             ("module", "views")])
        self.assertCompletionsAre2(buf, positions[2],
            [("function", "Something"),
             ("class", "Topic")])
        self.assertCompletionsAre2(buf, positions[3],
            [("module", "kor")])
        self.assertCalltipIs2(buf, positions[4],
            "Topic()")
        self.assertCompletionsInclude2(buf, positions[5],
            [("function", "createTopic")])

    @tag("bug78165")
    def test_dotdot_imports_completions(self):
        content1, positions1 = unmark_text(dedent(r'''
            from .<1> import <2>utils
        '''))
        content2, positions2 = unmark_text(dedent(r'''
            from ..<1> import <2>utils
        '''))
        content3, positions3 = unmark_text(dedent(r'''
            from .utils import <1>xxx
        '''))
        
        test_dir = join(self.test_dir, "test_dotdot_imports")
        manifest = [
            ('__init__.py', ""),
            ('foo/__init__.py', ""),
            ('foo/bar1.py', content1),
            ('foo/bar2.py', content2),
            ('foo/bar3.py', content3),
            ('foo/utils.py', "def neumann(): pass"),
            ('utils.py', "def morgenstern(): pass"),
            ('frank/__init__.py', ""),
            ('frank/bob.py', "def hi_there(): pass"),
        ]
        for f, c in manifest:
            path = join(test_dir, f)
            writefile(path, c)

        buf = self.mgr.buf_from_path(join(test_dir, "foo/bar1.py"), lang=self.lang)
        self.assertCompletionsInclude2(buf, positions1[1],
            [("module", "bar1"),
             ("module", "bar2"),
             ("module", "utils"),])
        self.assertCompletionsInclude2(buf, positions1[2],
            [("module", "bar1"),
             ("module", "bar2"),
             ("module", "utils"),])

        buf = self.mgr.buf_from_path(join(test_dir, "foo/bar2.py"), lang=self.lang)
        self.assertCompletionsInclude2(buf, positions2[1],
            [("module", "foo"),
             ("module", "utils"),
             ("module", "frank"),])
        self.assertCompletionsInclude2(buf, positions2[2],
            [("module", "foo"),
             ("module", "utils"),
             ("module", "frank"),])

        buf = self.mgr.buf_from_path(join(test_dir, "foo/bar3.py"), lang=self.lang)
        self.assertCompletionsInclude2(buf, positions3[1],
            [("function", "neumann"),])
            
    @tag("bug78165")
    def test_dotdot_imports(self):
        content1, positions1 = unmark_text(dedent(r'''
            import utils
            utils.<1>xxx
            from ..frank import bob
            bob.<2>xxx
        '''))
        content2, positions2 = unmark_text(dedent(r'''
            from . import utils
            utils.<1>xxx
        '''))
        content3, positions3 = unmark_text(dedent(r'''
            from .. import utils
            utils.<1>xxx
        '''))

        test_dir = join(self.test_dir, "test_dotdot_imports")
        manifest = [
            ('__init__.py', ""),
            ('foo/__init__.py', ""),
            ('foo/bar1.py', content1),
            ('foo/bar2.py', content2),
            ('foo/bar3.py', content3),
            ('foo/utils.py', "def neumann(): pass"),
            ('utils.py', "def morgenstern(): pass"),
            ('frank/__init__.py', ""),
            ('frank/bob.py', "def hi_there(): pass"),
        ]
        for f, c in manifest:
            path = join(test_dir, f)
            writefile(path, c)

        buf = self.mgr.buf_from_path(join(test_dir, "foo/bar1.py"), lang=self.lang)
        self.assertCompletionsInclude2(buf, positions1[1],
            [("function", "neumann"),])
        self.assertCompletionsInclude2(buf, positions1[2],
            [("function", "hi_there"),])

        buf = self.mgr.buf_from_path(join(test_dir, "foo/bar2.py"), lang=self.lang)
        self.assertCompletionsInclude2(buf, positions2[1],
            [("function", "neumann"),])
        
        buf = self.mgr.buf_from_path(join(test_dir, "foo/bar3.py"), lang=self.lang)
        self.assertCompletionsInclude2(buf, positions3[1],
            [("function", "morgenstern"),])

    @tag("bug91393")
    def test_relative_imports_3(self):
        test_dir = join(self.test_dir, "test_relative_imports_3")

        content, positions = unmark_text(dedent(r'''
            from .module_b import my_func_1
            import os
            os.<1>xxx
        '''))

        manifest = [
            ('module_a.py', content),
            ('module_b.py', "def my_func_1(): return 1\n"),
        ]
        for f, c in manifest:
            path = join(test_dir, f)
            writefile(path, c)

        buf = self.mgr.buf_from_path(join(test_dir, "module_a.py"), lang=self.lang)
        self.assertCompletionsInclude2(buf, positions[1],
            [("function", "rename"),])

    @tag("bug86644", "knownfailure")
    def test_binary_imports(self):
        lang = "Python"
        
        test_dir = join(self.test_dir, 'binary_import')
        if os.path.exists(test_dir):
            import shutil
            shutil.rmtree(test_dir, True)
        
        bin_py = join(test_dir, "binary.py")
        writefile(bin_py, dedent("""
            between = 'Scylla and Charybdis'
            def to_be_or_not_to_be(): pass
            class Dilemma: pass
        """))
        import compileall
        compileall.compile_dir(self.test_dir)
        os.remove(bin_py)
        
        content1, positions1 = unmark_text(dedent(r'''
            import binary
            binary.<1>xxx
        '''))

        manifest = [
            ('__init__.py', ""),
            ('foo.py', content1),
        ]
        for f, c in manifest:
            path = join(test_dir, f)
            writefile(path, c)

        buf = self.mgr.buf_from_path(join(test_dir, "foo.py"), lang=self.lang)
        self.assertCompletionsInclude2(buf, positions1[1],
            [("function", "to_be_or_not_to_be"),
             ("class", "Dilemma"),])
    
    @tag("bug94009")
    def test_multiple_package_imports(self):
        content, positions = unmark_text(dedent(r'''
            import foo.bar.bar1
            import foo.bar.bar2
            foo.bar.bar1.<1>xxx
            foo.bar.bar2.<2>xxx
        '''))

        test_dir = join(self.test_dir, "test_multiple_package_imports")
        manifest = [
            ('testcode.py', content),
            ('foo/__init__.py', ""),
            ('foo/bar/__init__.py', ""),
            ('foo/bar/bar1.py', "def bar1_method(): pass"),
            ('foo/bar/bar2.py', "def bar2_method(): pass"),
        ]
        for f, c in manifest:
            path = join(test_dir, f)
            writefile(path, c)

        buf = self.mgr.buf_from_path(join(test_dir, "testcode.py"), lang=self.lang)
        self.assertCompletionsInclude2(buf, positions[1],
            [("function", "bar1_method"),])
        self.assertCompletionsInclude2(buf, positions[2],
            [("function", "bar2_method"),])

    @tag("bug100684")
    def test_import_with_same_leaf_name(self):
        """Test that we can import a module from a different package with the
        same name as the basename of the file we're in"""
        test_dir = join(self.test_dir, "test_import_with_same_leaf_name")
        content, positions = unmark_text(dedent(r"""
            from django import models
            models.<|>yyy
        """))
        manifest = [
            ('models.py', content),
            ('django/__init__.py', ""),
            ('django/models.py', dedent("""\
                class manager(object):
                    pass
             """))
        ]
        for f, c in manifest:
            path = join(test_dir, f)
            writefile(path, c)
        buf = self.mgr.buf_from_path(join(test_dir, "models.py"), lang=self.lang)
        self.assertCompletionsInclude2(buf, positions["pos"],
            [("class", "manager"),])

    @tag("bug55687")
    def test_hit_from_function_call(self):
        content, positions = unmark_text(dedent("""\
            class MyClass:
                def func1():
                    return {}
            def myfunction(arg1):
                return "a string"
            def anotherfunction():
                return myfunction()
            
            f1 = myfunction()
            f1.<1>blah
            f2 = anotherfunction()
            f2.<2>blah
            # Test calling a class function.
            c1 = MyClass()
            f3 = c1.func1()
            f3.<3>blah
            # Test calling a variable.
            funcvar = anotherfunction()
            f4 = funcvar()
            f4.<4>blah
        """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [('function', 'strip'),
             ('function', 'lower'),
             ('function', 'capitalize')])
        self.assertCompletionsInclude(markup_text(content, pos=positions[2]),
            [('function', 'strip'),
             ('function', 'lower'),
             ('function', 'capitalize')])
        self.assertCompletionsInclude(markup_text(content, pos=positions[3]),
            [('function', 'items'),
             ('function', 'keys')])
        self.assertCompletionsInclude(markup_text(content, pos=positions[4]),
            [('function', 'strip'),
             ('function', 'lower'),
             ('function', 'capitalize')])

    @tag("bug71972", "bug71987")
    def test_builtins_function_completion(self):
        content, positions = unmark_text(dedent("""\
            mystr = "".lower()
            mystr.<1>xxx
            mylist = "".splitlines()
            mylist.<2>xxx
            import string
            def myfunction():
                s = string.split()
                s.<3>xxx
        """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [('function', 'strip'),
             ('function', 'lower'),
             ('function', 'capitalize')])
        self.assertCompletionsInclude(markup_text(content, pos=positions[2]),
            [('function', 'append'),
             ('function', 'pop'),
             ('function', 'sort')])
        if self.python_version < (3,):
            # string.split() is only in Python 2, not Python 3
            self.assertCompletionsInclude(markup_text(content, pos=positions[3]),
                [('function', 'append'),
                 ('function', 'pop'),
                 ('function', 'sort')])

    @tag("bug71989")
    def test_none_variable_type(self):
        content, positions = unmark_text(dedent("""\
            mylist = None
            mylist = "".splitlines()
            mylist.<1>xxx
        """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [('function', 'append'),
             ('function', 'pop'),
             ('function', 'sort')])
        
    @tag("bug71976", "knownfailure")
    def test_cascading_builtins_function_completion(self):
        # Test the boundary conditions only.
        content, positions = unmark_text(dedent("""\
            mystr = "foo".capitalize().capitalize().capitalize().capitalize().<1>capitalize().<2>capitalize()
        """))
        cplns = [('function', 'strip'),
                 ('function', 'lower'),
                 ('function', 'capitalize')]
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]), cplns)
        self.assertCompletionsInclude(markup_text(content, pos=positions[2]), cplns)
        # At point 6 we get a trigger, but no completions are returned.
        # this passes due to the bug:
        # self.assertCompletionsAre(markup_text(content, pos=positions[2]), None)

    def test_complete_available_exceptions(self):
        content, positions = unmark_text(dedent("""\
            try:
                foo()
            except <1>
        """))
        cplns = [('class', 'BaseException'),
                 ('class', 'Exception'),
                 ('class', 'IOError'),
                 ('class', 'ValueError'),
                 ]
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]), cplns)

    def test_complete_magic_symbols(self):
        content, positions = unmark_text(dedent("""\
            class myclass(object):
                def __<1>init__
                    pass
        """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [('function', '__init__(self'),
             ('function', '__eq__(self'),
             ('function', '__repr__(self')])

        content, positions = unmark_text(dedent("""\
            class myclass(object):
                def __init__(self):
                    pass
            def main():
                name = __<2>file__
                myclass.<3>__foo()
            if __<4>name__ == '__main__':
                main()
        """))
        self.assertCompletionsAre(markup_text(content, pos=positions[2]),
            [('variable', '__file__'),
             ('variable', '__loader__'),
             ('variable', '__name__'),
             ('variable', '__package__')])
        self.assertCompletionsInclude(markup_text(content, pos=positions[3]),
            [('variable', '__class__'),
             ('variable', '__doc__')])
        self.assertCompletionsAre(markup_text(content, pos=positions[4]),
            [('variable', '__file__'),
             ('variable', '__loader__'),
             ('variable', "__name__ == '__main__':"),
             ('variable', '__package__')])

    @tag("bug97194")
    def test_complete_magic_symbols_smart(self):
        content, positions = unmark_text(dedent("""\
            class foo:
                def __<1>x(self):
                    pass
                def __<2>y(self, arg1):
                    pass
                def __<3>z(self, *args, **kwargs):
                    pass
        """))
        for pos in range(1, 4):
            self.assertCompletionsInclude(markup_text(content, pos=positions[pos]),
                    [('function', '__init__'),
                     ('function', '__call__')])
            self.assertCompletionsDoNotInclude(markup_text(content, pos=positions[pos]),
                    [('function', '__init__(self'),
                     ('function', '__call__(self')])

    @tag("bug88419")
    def test_set_literals(self):
        content, positions = unmark_text(dedent("""\
            a_set = set([3, 4, 'blab'])
            func = a_set.<1>update
            a_set_literal = {'a', 'b'}
            func = a_set_literal.<2>update
            a_dict = {'a': 'b', 'c': 34}
            func = a_dict.<3>update
        """))
        self.assertTriggerMatches(markup_text(content, pos=positions[1]))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
          [('function', 'difference'),
           ('function', 'intersection'),
           ('function', 'update'),
           ('function', 'issuperset'),])
        self.assertTriggerMatches(markup_text(content, pos=positions[2]))
        self.assertCompletionsInclude(markup_text(content, pos=positions[2]),
          [('function', 'difference'),
           ('function', 'intersection'),
           ('function', 'update'),
           ('function', 'issuperset'),])
        self.assertTriggerMatches(markup_text(content, pos=positions[3]))
        self.assertCompletionsInclude(markup_text(content, pos=positions[3]),
          [('function', 'keys'),
          ('function', 'items'),
          ('function', 'update'),
          ('function', 'values'),])

    @tag("bug82014")
    def test_re_module(self):
        # Test the regular expressions module.
        content, positions = unmark_text(dedent("""\
            import re
            re.compile().<1>x
            re.escape().<2>x
            re.findall().<3>x
            re.match().<4>x
            re.search().<5>x
            re.split().<6>x
            re.sub().<7>x
            re.subn().<8>x
            re.template().<9>x
            re.compile().findall().<10>x
            re.compile().match().<11>x
            re.compile().search().<12>x
            re.compile().split().<13>x
            re.compile().sub().<14>x
            re.compile().subn().<15>x
        """))
        for pos in (1, 9):
            self.assertCompletionsInclude(markup_text(content, pos=positions[pos]),
                    # re pattern object completions
                    [('function', 'findall'),
                     #('variable', 'flags'),   # Some interpreters don't expose flags.
                     ('function', 'match'),
                     ('function', 'search')])
        for pos in (2, 7, 8, 14, 15):
            self.assertCompletionsInclude(markup_text(content, pos=positions[pos]),
                    # string completions
                    [('function', 'strip'),
                     ('function', 'lower'),
                     ('function', 'capitalize')])
        for pos in (3, 6, 10, 13):
            self.assertCompletionsInclude(markup_text(content, pos=positions[pos]),
                    # list completions
                    [('function', 'append'),
                     ('function', 'index'),
                     ('function', 'remove')])
        for pos in (4, 5, 11, 12):
            self.assertCompletionsInclude(markup_text(content, pos=positions[pos]),
                    # re match object completions
                    [('function', 'end'),
                     ('function', 'group'),
                     ('function', 'groups'),
                     #('variable', 'lastgroup'), # Some interpreters don't expose lastgroup
                     #('variable', 'pos'),       # Some interpreters don't expose pos
                     ('function', 'start')])

    def test_complete_local_symbols(self):
        content, positions = unmark_text(dedent("""\
            import football
            footy = 1
            def foofun():
                pass
            class fools:
                pass
            fo<1>

            class fools2(object):
                def foom(self, fooarg=2):
                    foolocal = 'hello'
                    fo<2>

            class other(object):
                fooother = 1
                def otherfunc(self):
                    fo<3>
                fo<4>
            cl<5>ass fam:
                x = cl<6>
                y = No<7>
        """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
                [('module', 'football'),
                 ('variable', 'footy'),
                 ('function', 'foofun'),
                 ('class', 'fools'),
                 ('class', 'fools2')])
        self.assertCompletionsInclude(markup_text(content, pos=positions[2]),
                [('module', 'football'),
                 ('argument', 'fooarg'),
                 ('variable', 'footy'),
                 ('variable', 'foolocal'),
                 ('function', 'foofun'),
                 ('class', 'fools'),
                 ('class', 'fools2')])
        self.assertCompletionsInclude(markup_text(content, pos=positions[3]),
                [('module', 'football'),
                 ('variable', 'footy'),
                 ('function', 'foofun'),
                 ('class', 'fools'),
                 ('class', 'fools2')])
        self.assertCompletionsDoNotInclude(markup_text(content, pos=positions[3]),
                [('variable', 'fooother')])
        self.assertCompletionsInclude(markup_text(content, pos=positions[4]),
                [('module', 'football'),
                 ('variable', 'footy'),
                 ('variable', 'fooother'),
                 ('function', 'foofun'),
                 ('class', 'fools'),
                 ('class', 'fools2')])
        self.assertCompletionsInclude(markup_text(content, pos=positions[5]),
                [('keyword', 'class')])
        self.assertCompletionsDoNotInclude(markup_text(content, pos=positions[6]),
                [('keyword', 'class')])
        self.assertCompletionsInclude(markup_text(content, pos=positions[7]),
                [('keyword', 'None')])

    @tag("bug101419")
    def test_with_statement(self):
        content, positions = unmark_text(dedent("""
                with "string" as s:
                    s.<1>s
                with ["two", "strings"] as (t, u):
                    t.<2>s
                    u.<3>s
            """))
        self.assertCompletionsInclude(markup_text(content, positions[1]),
                                      [("function", "strip")])
        self.assertCompletionsInclude(markup_text(content, positions[2]),
                                      [("function", "strip")])
        self.assertCompletionsInclude(markup_text(content, positions[3]),
                                      [("function", "strip")])

    def test_multiple_with(self):
        # This needs test_with_statement / bug 101419 to be fixed first
        content, positions = unmark_text(dedent("""
                with "string" as a, "string" as b:
                    a.<1>s
                    b.<2>s
            """))
        self.assertCompletionsInclude(markup_text(content, positions[1]),
                                      [("function", "strip")])
        self.assertCompletionsInclude(markup_text(content, positions[2]),
                                      [("function", "strip")])

    @tag("bug101782")
    def test_decl_default_arg_call(self):
        content, positions = unmark_text(dedent("""
            def foo(arg=int()):
                return "answer"
            foo().<1>strip
            """))
        self.assertCompletionsInclude(markup_text(content, positions[1]),
                                      [("function", "strip")])
        content, positions = unmark_text(dedent("""
            def foo(arg=thing[3]):
                return "answer"
            foo().<1>strip
            """))
        self.assertCompletionsInclude(markup_text(content, positions[1]),
                                      [("function", "strip")])

    @tag("knownfailure", "pep0274")
    def test_dict_comprehension(self):
        content, positions = unmark_text(dedent("""
                d = {k: v for k, v in ((1, 2), (3, 4))}
                d.<1>g
            """))
        self.assertCompletionsInclude(markup_text(content, positions[1]),
                                      [("function", "get")])


    def test_octal_literals(self):
        content, positions = unmark_text(dedent("""
                octal = 0o755
                binary = 0b101010101
                octal.<1>b
                binary.<2>b
            """))
        self.assertCompletionsInclude(markup_text(content, positions[1]),
                                      [("function", "bit_length")])
        self.assertCompletionsInclude(markup_text(content, positions[2]),
                                      [("function", "bit_length")])

    def test_byte_literals(self):
        content, positions = unmark_text(dedent("""
                literal = b"hello"
                literal.<1>d
            """))
        self.assertCompletionsInclude(markup_text(content, positions[1]),
                                      [("function", "decode")])

    def test_string_literals(self):
        content, positions = unmark_text(dedent("""
                literal = "hello"
                literal.<1>e
            """))
        self.assertCompletionsInclude(markup_text(content, positions[1]),
                                      [("function", "encode")])

class CplnEnvironTestCase(CodeintelPythonTestCase):
    """Must be a separate class test case - as it modifies the environ, which
    will only be taken into consideration when the manager initializes (i.e.
    once per class).
    """

    test_dir = join(os.getcwd(), "tmp")

    def test_envlib(self):
        test_dir = join(self.test_dir, "test_envlib")
        oracle_content, oracle_positions = unmark_text(dedent("""\
            import answers
            print "The ultimate answer is %d" % answers.<1>ULTIMATE
        """))
        manifest = [
            ("lib/answers.py", dedent("""
                __version__ = '1.0.0'
                ULTIMATE = 42
             """)),
            ("oracle.py", oracle_content),
        ]
        for file, content in manifest:
            path = join(test_dir, file)
            writefile(path, content)
        self.mgr.env.set_envvar("PYTHONPATH", join(test_dir, "lib"))
        self.mgr.env.cache.pop(self.lang + "-info", None)

        self.assertCompletionsInclude(
            markup_text(oracle_content, pos=oracle_positions[1]),
            [("variable", "ULTIMATE")])


class OldCodeIntelTestCase(CodeIntelTestCase):
    """Test case from the old codeintel v1 test/test_citdl/... dir."""
    lang = "Python"
    __tags__ = ["old"]
    test_dir = join(os.getcwd(), "tmp")

    def test_breakfast(self):
        content, positions = unmark_text(dedent('''\
            class Toast:
                def cook(self):
                    # Try to enforce CITDL that include a scope part.
                    brekyClass = Breakfast
                    brekyClass.<1>Eggs

            class Breakfast:
                items = []
                class Eggs:
                    def crack(self): pass
                    def cook(self, how="over-easy"): pass
                def __init__(self, items):
                    Toast.<2>cook
                    self.items = items
                def cook(self):
                    for item in self.items:
                        item.cook()
                def serve(self): pass
            
            def takeOrder(tableNumber):
                """takeOrder(<the table number>) -> None
                
                take an order
                """
                print "Welcome to Sunshine Diner! Can I take your order?"
                brekyClass = Breakfast
            
            takeOrder(<3>)
            Breakfast.Eggs.<4>crack
            takeOrder.<5>nada
            Breakfast.__init__.<6>nada
            takeOrder.brekyClass.<7>serve
               
            b = Breakfast()
            b.<8>cook
        '''))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("class", "Eggs"), ("function", "cook")])
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[2]),
            [("function", "cook")])
        self.assertCalltipIs(
            markup_text(content, pos=positions[3]),
            "takeOrder(<the table number>) -> None\ntake an order")
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[4]),
            [("function", "cook"), ("function", "crack")])
        #TODO: these two currently returns internal function vars
        #self.assertCompletionsAre(
        #    markup_text(content, pos=positions[5]),
        #    None)
        #self.assertCompletionsAre(
        #    markup_text(content, pos=positions[6]),
        #    None)
        self.assertCompletionsAre(
            markup_text(content, pos=positions[7]),
            None)
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[8]),
            [('function', 'cook'), ('class', 'Eggs'), ('variable', 'items'),
             ('function', 'serve'), ('function', '__init__')])

    @tag("knownfailure")
    def test_usebuiltins(self):
        content, positions = unmark_text(dedent('''\
            int(<0>)
            strvar = "foo"
            strvar.<1>split
            listvar = [1,2,3]
            listvar.<2>index
            tuplevar = (1,2,3)
            tuplevar.<3>__add__
            dictvar = {"one": 1, "two": 2, "three": 3}
            dictvar.<4>update
            nonevar = None
            nonevar.<5>__class__
            maxvar = max
            max(<6>)
        '''))
        #TODO: codeintel2 calltip processing has gotten worse
        self.assertCalltipIs(markup_text(content, pos=positions[0]),
            "int(x[, base]) -> integer\n"
            "Convert a string or number to an integer, if possible.")
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("function", "split")])
        self.assertCompletionsInclude(markup_text(content, pos=positions[2]),
            [("function", "index")])
        self.assertCompletionsInclude(markup_text(content, pos=positions[3]),
            [("function", "__add__")])
        self.assertCompletionsInclude(markup_text(content, pos=positions[4]),
            [("function", "update")])
        #TODO: special type attributes should be included
        self.assertCompletionsInclude(markup_text(content, pos=positions[5]),
            [("function", "__class__")])
        self.assertCalltipIs(markup_text(content, pos=positions[6]),
            "max(iterable[, key=func]) -> value\n"
            "max(a, b, c, ...[, key=func]) -> value\n"
            "With a single iterable argument, return its largest item.")

        content, positions = unmark_text(dedent('''\
            import _socket
            _socket.socket(<1>)
            
            # There should NOT be a calltip on module objects (c.f. change
            # 121484).
            import socket
            socket(<2>)
            socket.socket(<3>)
            socket.socket.<4>blah
        '''))
        self.assertCalltipIs(markup_text(content, pos=positions[1]),
            "socket([family[, type[, proto]]]) -> socket object\n"
            "Open a socket of the given type.  The family argument specifies the")
        self.assertCalltipIs(markup_text(content, pos=positions[2]), None)
        self.assertCalltipIs(markup_text(content, pos=positions[3]),
            "socket([family[, type[, proto]]]) -> socket object\n"
            "Open a socket of the given type.  The family argument specifies the")
        self.assertCompletionsInclude(markup_text(content, pos=positions[4]),
            [("function", "accept")])

    def test_infinity(self):
        # There is a possible infinite loop in CITDL evaluation. Because with
        # the Python CILE the last definition of a code object with a certain
        # name wins, if one is renaming a definition and creating a new one
        # that inherits from the old, base class evaluation can result in an
        # infinite loop. This happens, in particular, with process.py: with
        # the _ThreadFixer variants of the Process, ProcessOpen, and
        # ProcessProxy classes. We reproduce that here.
        content, positions = unmark_text(dedent('''\
            class ProcessOpen:
                def __init__(self, cmd, mode='t', cwd=None, env=None): pass
                def close(self): pass
                def wait(self, timeout=None): pass
                def kill(self, exitCode=0, gracePeriod=1.0, sig=None): pass
            
            if sys.platform.startswith("linux"):
                # Note that because the Python CILE does no flow analysis it cannot
                # know that this block is for Linux-only. Even so, the problem still
                # would appear on Linux even if it did this flow analysis.
                class _ThreadFixer:
                    def wait(self, timeout=None):
                        "special thread-fixing wait"
                        pass
                
                _ThreadBrokenProcessOpen = ProcessOpen
                class ProcessOpen(_ThreadFixer, _ThreadBrokenProcessOpen):
                    _pclass = _ThreadBrokenProcessOpen
            
            p = ProcessOpen()
            p.<1>wait(<2>)
        '''))

        # The _correct_ list of members really should include "close" and
        # "kill" from the original ProcessOpen, but redefinition in the same
        # scope is currently not handled by the Python CILE and codeintel
        # system. All we are ensuring here is that this does not result in an
        # infinite loop.
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("function", "wait"), ("variable", "_pclass")])
        self.assertCalltipIs(markup_text(content, pos=positions[2]),
            "wait(timeout=None)\n"
            "special thread-fixing wait")

    def test_infinity2(self):
        content, positions = unmark_text(dedent(r'''
            PREFORMATTER_ID = 'summary'
            
            __version__ = '1.0'
            __author__ = 'David Ascher'
            
            def verify_installation(request):
                return 1
            
            from Pyblosxom import tools
            
            def cb_postformat(args):
                data = args['entry_data']
                lines = data["body"].split('\n');
                entry = []
                summary = []
                target = entry
                s = "NOT"
                data['summary'] = repr(lines)
                #data['body'] 
                for line in lines:
                    line = line.rstrip()
                    if line.strip().startswith("Summary:"):
                        s = "FOO"
                        target = summary
                        continue
                    if not line.startswith(' ') and target == summary:
                        target = entry
                        continue
                    target.append(line)
            
                line.<1>rstrip
                summary = '\n'.join(summary)
                if summary:
                    data["body"] = '\n'.join(entry)
                    data["summary"] = s
                else:
                    data["summary"] = data["body"]
        '''))

        self.assertCompletionsAre(markup_text(content, pos=positions[1]),
                                  None)

    def test_basics(self):
        content, positions = unmark_text(dedent(r'''
            class ContrivedDummy:
                def __init__(self, a, b):
                    "create a contrived dummy"
                    self.ivar = "ha ha ha"
                def foo(self, c):
                    "foo baby, yeah!"
                    pass
                def bar(self):
                    self.<1>blah
                    self.foo(<2>)
                    SELF = self
                    SELF.<3>blah
                    SELF.foo(<4>)
                    FOO = self.foo
                    FOO(<5>)
                    pass
            
            class BaseDummy(ContrivedDummy):
                pass
            
            ContrivedDummy(<6>)
            BaseDummy(<7>)
            bd = BaseDummy()
            bd.<8>foo(<9>)
            
            class SortOrderClass:
                _foo = 1
                foo = 1
                __bar = 1
                _bar = 1
                bar = 1
                __Bar = 1
                _Bar = 1
                Bar = 1
                __BAR = 1
                _BAR = 1
                BAR = 1
            SortOrderClass.<10>blah
            
            def hello(a,b, msg=ContrivedDummy):
                """ say hello """
                msg.<11>blah
                print "hello from hi.py"
            hello(<12>)
        '''))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("function", "bar"), ("function", "foo"),
             ("variable", "ivar"), ("function", "__init__")])
        self.assertCalltipIs(markup_text(content, pos=positions[2]),
                             "foo(c)\nfoo baby, yeah!")
        self.assertCompletionsInclude(markup_text(content, pos=positions[3]),
            [("function", "bar"), ("function", "foo"),
             ("variable", "ivar"), ("function", "__init__")])
        self.assertCalltipIs(markup_text(content, pos=positions[4]),
                             "foo(c)\nfoo baby, yeah!")
        self.assertCalltipIs(markup_text(content, pos=positions[5]),
                             "foo(c)\nfoo baby, yeah!")
        self.assertCalltipIs(markup_text(content, pos=positions[6]),
                             "ContrivedDummy(a, b)\ncreate a contrived dummy")
        self.assertCalltipIs(markup_text(content, pos=positions[7]),
                             "ContrivedDummy(a, b)\ncreate a contrived dummy")
        self.assertCompletionsInclude(markup_text(content, pos=positions[8]),
            [("function", "bar"), ("function", "foo"),
             ("variable", "ivar"), ("function", "__init__")])
        self.assertCalltipIs(markup_text(content, pos=positions[9]),
                             "foo(c)\nfoo baby, yeah!")
        self.assertCompletionsInclude(markup_text(content, pos=positions[10]),
            [
                ('variable', 'BAR'),
                ('variable', 'Bar'),
                ('variable', 'bar'),
                ('variable', 'foo'),
                ('variable', '_Bar'),
                ('variable', '_BAR'),
                ('variable', '_bar'),
                ('variable', '_foo'),
                ('variable', '__bar'),
                ('variable', '__Bar'),
                ('variable', '__BAR'),
            ])
        self.assertCompletionsInclude(markup_text(content, pos=positions[11]),
            [("function", "bar"), ("function", "foo"),
             ("variable", "ivar"), ("function", "__init__")])
        self.assertCalltipIs(markup_text(content, pos=positions[12]),
                             "hello(a, b, msg=ContrivedDummy)\nsay hello ")

    def test_dupes(self):
        content, positions = unmark_text(dedent(r'''
            # Ensure that duplicates get removed from member lists.
            class MePlease:
                def i_do(self): pass
            class MeTooPlease:
                def i_do(self): pass
            who_wants_gum = MePlease
            who_wants_gum = MeTooPlease
            who_wants_gum.<1>i_do
        '''))
        self.assertNoDuplicateCompletions(
            markup_text(content, pos=positions[1]))

    def test_imports(self):
        content, positions = unmark_text(dedent(r'''
            # import mod
            import bye
            bye.<0>goodbye()
            
            # import mod as alias
            import bye as aurevoir
            aurevoir.<1>blah
            
            # from pkg import mod
            from fruit import apple
            apple.<2>blah
            
            # from pkg import mod as alias
            from fruit import apple as pomme
            pomme.<3>blah
            
            # from mod import symbol
            from fruit import Fruit, Banana
            Fruit.<4>blah
            Banana.<5>blah
            f = Fruit()
            f.<6>blah
            b = Banana()
            b.<7>blah
            
            from fruit.apple import GrannySmith
            GrannySmith.<8>blah
            
            # from mod import symbol as alias
            from fruit import Banana as Banane
            Banane.<9>blah
            b2 = Banane()
            b2.<10>blah
            
            # from mod import *
            from bye import *
            SettingSun.<11>blah
            from fruit import *
            Orange.<12>blah
            from fruit.apple import *
            RedDelicious.<13>blah
        '''))

        test_dir = join(self.test_dir, "test_imports")
        manifest = [
            ("foo.py", content),
            ("bye.py", dedent("""
                def goodbye():
                    print "goodbye from bye.py"
                
                class SettingSun:
                    def rideIntoThe(self): pass
             """)),
            ("fruit/__init__.py", dedent("""
                class Fruit:
                    def isRipe(self): pass
                    def isRotten(self): pass
                
                class Banana(Fruit):
                    def isRipe(self): pass # override this one, ensure it doesn't come up double
                    def isFromDole(self): pass
                
                class Orange(Fruit):
                    def isFromFlorida(self): pass
             """)),
            ("fruit/apple.py", dedent("""
                class Apple:
                    def color(self):
                        "what color is the apple?"
                        pass
                class GrannySmith(Apple):
                    def howGreen(self): pass
                class Macintosh(Apple): pass
                class RedDelicious(Apple):
                    def howRed(self): pass
             """)),
        ]
        for f, c in manifest:
            path = join(test_dir, f)
            writefile(path, c)

        buf = self.mgr.buf_from_path(join(test_dir, "foo.py"), lang=self.lang)
        self.assertCompletionsInclude2(buf, positions[0],
            [("function", "goodbye")])
        self.assertCompletionsInclude2(buf, positions[1],
            [("function", "goodbye")])
        self.assertCompletionsInclude2(buf, positions[2],
            [("class", "Apple"), ("class", "GrannySmith")])
        self.assertCompletionsInclude2(buf, positions[3],
            [("class", "Apple"), ("class", "GrannySmith")])
        self.assertCompletionsInclude2(buf, positions[4],
            [("function", "isRipe")])
        self.assertCompletionsInclude2(buf, positions[5],
            [("function", "isRipe")])
        self.assertCompletionsInclude2(buf, positions[6],
            [("function", "isRipe")])
        self.assertCompletionsInclude2(buf, positions[7],
            [("function", "isRipe")])
        self.assertCompletionsInclude2(buf, positions[8],
            [("function", "color"), ("function", "howGreen")])
        self.assertCompletionsInclude2(buf, positions[9],
            [("function", "isRipe"), ("function", "isFromDole")])
        self.assertCompletionsInclude2(buf, positions[10],
            [("function", "isRipe"), ("function", "isFromDole")])
        self.assertCompletionsInclude2(buf, positions[11],
            [("function", "rideIntoThe")])
        self.assertCompletionsInclude2(buf, positions[12],
            [("function", "isFromFlorida")])
        self.assertCompletionsInclude2(buf, positions[13],
            [("function", "howRed")])

    def test_base_class_members(self):
        content, positions = unmark_text(dedent(r'''
            class NonModuleScope:
                class BaseClass:
                    def basemethod1(self): pass
                    def basemethod2(self): pass
                class SubClass(BaseClass):
                    def submethod1(self): pass
                SubClass.<1>blah
                import fruit
                fruitClass = fruit.Fruit
                class FruitSubClass(BaseClass, fruitClass):
                    def doYouLikeFruit(self): pass
                FruitSubClass.<2>blah
                pass
            
            NonModuleScope.SubClass.<3>blah
            NonModuleScope.FruitSubClass.<4>blah
        '''))

        test_dir = join(self.test_dir, "test_base_class_members")
        manifest = [
            ("foo.py", content),
            ("fruit/__init__.py", dedent("""
                class Fruit:
                    def isRipe(self): pass
                    def isRotten(self): pass
                
                class Banana(Fruit):
                    def isRipe(self): pass # override this one, ensure it doesn't come up double
                    def isFromDole(self): pass
                
                class Orange(Fruit):
                    def isFromFlorida(self): pass
             """)),
        ]
        for f, c in manifest:
            path = join(test_dir, f)
            writefile(path, c)

        buf = self.mgr.buf_from_path(join(test_dir, "foo.py"), lang=self.lang)
        self.assertCompletionsInclude2(buf, positions[1],
                              [("function", "basemethod1"),
                               ("function", "basemethod2"),
                               ("function", "submethod1")])
        self.assertCompletionsInclude2(buf, positions[2],
                              [("function", "basemethod1"),
                               ("function", "basemethod2"),
                               ("function", "doYouLikeFruit"),
                               ("function", "isRipe"),
                               ("function", "isRotten")])
        self.assertCompletionsInclude2(buf, positions[3],
                              [("function", "basemethod1"),
                               ("function", "basemethod2"),
                               ("function", "submethod1")])
        #TODO: this one isn't picking up on fruit.Fruit methods. It is a
        #      scoperef issue.
        self.assertCompletionsInclude2(buf, positions[4],
                              [("function", "basemethod1"),
                               ("function", "basemethod2"),
                               ("function", "doYouLikeFruit"),
                               ("function", "isRipe"),
                               ("function", "isRotten")])

    def test_func_calltips(self):
        content, positions = unmark_text(dedent(r'''
            def simple(a, b, c):
                pass
            simple(<1>)
            def harder(a, b=None, *c):
                pass
            harder(<2>)
            def ctfromdoc(a, b=None, *c):
                """ctfromdoc(blah) -> womba
            
                Twiddle dee dee"""
                pass
            ctfromdoc(<3>)
            def mixed(a, b=None, *c):
                "this is what mixed is"
                pass
            mixed(<4>)
        '''))
        self.assertCalltipIs(markup_text(content, pos=positions[1]),
            "simple(a, b, c)")
        self.assertCalltipIs(markup_text(content, pos=positions[2]),
            "harder(a, b=None, *c)")
        self.assertCalltipIs(markup_text(content, pos=positions[3]),
            "ctfromdoc(blah) -> womba\nTwiddle dee dee")
        self.assertCalltipIs(markup_text(content, pos=positions[4]),
            "mixed(a, b=None, *c)\nthis is what mixed is")

    def test_class_calltips(self):
        content, positions = unmark_text(dedent(r'''
            class Animal:
                """an animal object
                
                blah blah blah
                """
                def __init__(self, genus):
                    "create an animal with the given genus"
                    pass
            class Mammal(Animal):
                def __init__(self, genus, species=None):
                    """Mammal(genus) -> a mammal
                    Mammal(genus, species) -> a more specific mammal
                    
                    Live birth!
                    """
                    pass
            class Fish(Animal):
                """Fish(GENUS) -> scaly thing
                
                Good eatin'
                """
                pass
            Animal(<1>)
            Mammal(<2>)
            Fish(<3>)
        '''))
        self.assertCalltipIs(markup_text(content, pos=positions[1]),
            "Animal(genus)\n"
            "create an animal with the given genus")
        self.assertCalltipIs(markup_text(content, pos=positions[2]),
            "Mammal(genus) -> a mammal\n"
            "Mammal(genus, species) -> a more specific mammal\n"
            "Live birth!")
        self.assertCalltipIs(markup_text(content, pos=positions[3]),
            "Fish(GENUS) -> scaly thing\nGood eatin'")
        
    @tag("bug76056")
    def test_logging_module(self):
        # Ensure we get completeions on "logging" module classes, as this is
        # commonly used in many Python programs.
        content, positions = unmark_text(dedent(r'''
            import logging
            log = logging.getLogger('some_name')
            log.<1>
        '''))
        self.assertCompletionsInclude(markup_text(content, positions[1]),
            [("function", "exception"),
             ("function", "fatal"),
             ("function", "critical"),
             ("function", "error"),
             ("function", "warn"),
             ("function", "debug"),
             ("function", "getEffectiveLevel"),
            ])



class PyWin32TestCase(CodeIntelTestCase):
    lang = "Python"
    env = SimplePrefsEnvironment(codeintel_selected_catalogs=['pywin32'])

    def test_name_and_desc(self):
        catalogs_zone = self.mgr.db.get_catalogs_zone()
        for catalog_info in catalogs_zone.avail_catalogs(["pywin32"]):
            if catalog_info['selected']:
                pywin32_info = catalog_info
                break
        else:
            self.fail("PyWin32 not found in the available catalogs")

        self.failUnlessEqual(pywin32_info["name"], "PyWin32")
        self.failUnless(pywin32_info["description"] is not None)

    def test_win32api(self):
        py_catalog_lib = self.mgr.db.get_catalog_lib("Python", ["pywin32"])
        self.failUnless(py_catalog_lib.has_blob("win32api"))

    


#---- mainline

if __name__ == "__main__":
    unittest.main()


