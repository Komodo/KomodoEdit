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

"""Test some Perl-specific codeintel handling."""

import os
import sys
import re
from os.path import join, dirname, abspath, exists, basename
from glob import glob
import unittest
import subprocess
import logging

from codeintel2.util import (indent, dedent, banner, markup_text, unmark_text,
                             lines_from_pos)
from codeintel2.environment import SimplePrefsEnvironment

from testlib import TestError, TestSkipped, TestFailed, tag
from citestsupport import CodeIntelTestCase, writefile



#---- globals

log = logging.getLogger("test")

PERL_STDLIB_HAS_POD_INFO = False  # c.f. bug 65739



#---- the test cases

class LibsTestCase(CodeIntelTestCase):
    test_dir = join(os.getcwd(), "tmp")

    def test_with_all_perls(self):
        # Test that the @INC parsing for different kinds of Perl works.
        import which

        test_lib_dir = join(self.test_dir, "my-perl-lib")
        if not exists(test_lib_dir):
            os.makedirs(test_lib_dir)

        env = SimplePrefsEnvironment()
        env.set_envvar("PERL5LIB", abspath(test_lib_dir))
        buf = self.mgr.buf_from_content("1;", "Perl", path="foo.pl",
                                        env=env)
        for perl in which.whichall("perl"):
            env.set_pref("perl", perl)
            for lib in buf.libs: # test envlib
                if lib.name == "envlib":
                    self.failUnless(env.get_envvar("PERL5LIB") in lib.dirs,
                        "envlib for '%s' does not have the expected dirs: "
                        "lib.dirs=%r" % (perl, lib.dirs))
                    break
            else:
                self.fail("no envlib in libs for '%s': libs=%r"
                          % (perl, buf.libs))


class TrgTestCase(CodeIntelTestCase):
    lang = "Perl"

    def test_complete_star_subs(self):
        self.assertNoTrigger("><|>")
        self.assertNoTrigger(" ><|>")
        self.assertNoTrigger("-><|>")
        self.assertNoTrigger(" -><|>")
        self.assertNoTrigger("$FOO->{<|>")
        self.assertNoTrigger("$FOO->[1]-><|>")
        self.assertNoTrigger("$FOO[1]-><|>")
        # E.g., from UDDI::Lite
        #   my $auth = get_authToken({userID => 'USERID', cred => 'CRED'})->authInfo;
        self.assertNoTrigger("foo()-><|>")

        self.assertTriggerMatches("$FOO-><|>", name="perl-complete-*-subs",
                                  pos=6, length=2)
        self.assertTriggerMatches("$foo-><|>", name="perl-complete-*-subs")
        self.assertTriggerMatches("$Foo-><|>", name="perl-complete-*-subs")
        self.assertTriggerMatches("$Foo::Bar-><|>", name="perl-complete-*-subs")
        self.assertTriggerMatches("$Foo::Bar::baz-><|>", name="perl-complete-*-subs")
        self.assertTriggerMatches("Foo::bar $baz-><|>", name="perl-complete-*-subs")
        self.assertTriggerMatches("$ foo-><|>", name="perl-complete-*-subs")
        self.assertTriggerMatches("$_-><|>", name="perl-complete-*-subs")
        self.assertTriggerMatches("Foo::Bar-><|>", name="perl-complete-*-subs")
        self.assertTriggerMatches("Foo::Bar::baz-><|>", name="perl-complete-*-subs")
        self.assertTriggerMatches("foo\n  \t-><|>", name="perl-complete-*-subs")

    def test_complete_package_members(self):
        name = "perl-complete-package-members"
        self.assertNoTrigger(":<|>")
        self.assertNoTrigger("::<|>")
        self.assertNoTrigger(" :<|>")
        self.assertNoTrigger(": :<|>")
        self.assertNoTrigger("Foo: :<|>")

        self.assertTriggerMatches("FOO::<|>", name=name,
                                  pos=5, length=2)
        self.assertTriggerMatches("foo::<|>", name=name)
        self.assertTriggerMatches("Foo::<|>", name=name)
        self.assertTriggerMatches("$FOO::<|>", name=name)
        self.assertTriggerMatches("$foo::<|>", name=name)
        self.assertTriggerMatches("$Foo::<|>", name=name)
        self.assertTriggerMatches("@foo::<|>", name=name)
        self.assertTriggerMatches("\foo::<|>", name=name)
        self.assertTriggerMatches("*foo::<|>", name=name)
        self.assertTriggerMatches("%foo::<|>", name=name)
        self.assertTriggerMatches("$::<|>", name=name) # equiv to $main::

        self.assertTriggerMatches("@B::<|>SV::ISA = 'B::OBJECT';", name=name)
        self.assertTriggerMatches("@B::SV::<|>ISA = 'B::OBJECT';", name=name)
        self.assertNoTrigger("@B::SV::ISA = 'B::<|>OBJECT';\n\n")

    def test_complete_available_imports(self):
        name = "perl-complete-available-imports"
        self.assertTriggerDoesNotMatch("useFoo::", name=name)
        self.assertTriggerMatches("use Foo::", name=name, prefix="Foo")
        self.assertTriggerMatches("use Foo::<|>Bar;", name=name, prefix="Foo")
        self.assertTriggerMatches("use Foo::<|>;", name=name, prefix="Foo")

        self.assertTriggerMatches("# use Foo::<|>;", name=name,
                                  implicit=False, prefix="Foo")
        self.assertTriggerMatches("#use Foo::<|>;", name=name,
                                  implicit=False, prefix="Foo")
        self.assertTriggerDoesNotMatch("$use Foo::", name=name)
        self.assertTriggerDoesNotMatch("%use Foo::", name=name)
        self.assertTriggerDoesNotMatch("@use Foo::", name=name)
        self.assertTriggerDoesNotMatch("_use Foo::", name=name)

        self.assertTriggerMatches("no FOO::<|>", name=name, length=2, pos=8)
        self.assertTriggerMatches("no foo::<|>", name=name, prefix="foo")
        self.assertTriggerMatches("no Foo::<|>", name=name, prefix="Foo")
        self.assertTriggerMatches("no Foo::Bar::<|>", name=name, prefix="Foo::Bar")
        self.assertTriggerMatches("no Foo::<|>Bar::", name=name, prefix="Foo")
        self.assertTriggerMatches("$no Foo::<|>", name="perl-complete-package-members")
        self.assertTriggerMatches(" no Foo::<|>", name=name)
        self.assertTriggerMatches("\tno Foo::<|>", name=name)

        self.assertTriggerMatches("use FOO::<|>", name=name, length=2, pos=9)
        self.assertTriggerMatches("use foo::<|>", name=name, prefix="foo")
        self.assertTriggerMatches("use Foo::<|>", name=name, prefix="Foo")
        self.assertTriggerMatches("use Foo::Bar::<|>", name=name, prefix="Foo::Bar")
        self.assertTriggerMatches("use Foo::<|>Bar::", name=name, prefix="Foo")
        self.assertTriggerMatches("$use Foo::<|>", name="perl-complete-package-members")
        self.assertTriggerMatches(" use Foo::<|>", name=name)
        self.assertTriggerMatches("\tuse Foo::<|>", name=name)

        self.assertTriggerMatches("require FOO::<|>", name=name)
        self.assertTriggerMatches("require foo::<|>", name=name, prefix="foo")
        self.assertTriggerMatches("require Foo::<|>", name=name, prefix="Foo")
        self.assertTriggerMatches("require Foo::Bar::<|>", name=name, prefix="Foo::Bar")
        self.assertTriggerMatches("require Foo::<|>Bar::", name=name, prefix="Foo")
        self.assertTriggerMatches("$require Foo::<|>", name="perl-complete-package-members")
        self.assertTriggerMatches(" require Foo::<|>", name=name)
        self.assertTriggerMatches("\trequire Foo::<|>", name=name)

    def test_complete_variables(self):
        name = "perl-complete-variables"
        self.assertTriggerMatches("$<|>f", name=name, pos=1)
        self.assertNoTrigger("$f<|>")
        self.assertNoTrigger("<|>$f")

    def test_calltip_call_signature(self):
        self.assertNoTrigger("my (<|>$a, $b, $c) = @_")

        self.assertNoTrigger(" <|>")
        self.assertNoTrigger("((<|>")
        self.assertNoTrigger("(<|>")

        self.assertTriggerMatches("split <|>",
            name="perl-calltip-space-call-signature", pos=6, length=1)
        self.assertTriggerMatches(" split <|>", name="perl-calltip-space-call-signature")
        # Keep the scope of space-triggerred calltips low. No absolute
        # need to support more than one space away.
        self.assertNoTrigger("split  <|>")
        # Only allowTriggerOnSpace words will trigger space-calltip.
        self.assertNoTrigger("notaperlbuiltin <|>")
        self.assertNoTrigger("$split <|>")
        self.assertNoTrigger("&split <|>")
        self.assertNoTrigger("@split <|>")
        self.assertNoTrigger("%split <|>")
        self.assertNoTrigger("\\split <|>")
        self.assertNoTrigger("*split <|>")
        self.assertNoTrigger("$ split <|>")
        self.assertNoTrigger("& split <|>")
        self.assertNoTrigger("@ split <|>")
        self.assertNoTrigger("% split <|>")
        self.assertNoTrigger("\\ split <|>")
        self.assertNoTrigger("* split <|>")
        self.assertNoTrigger("sub split <|>") # can overload built-ins

        self.assertTriggerMatches(" split(<|>",
            name="perl-calltip-call-signature", pos=7, length=1)
        self.assertTriggerMatches(" split (<|>", name="perl-calltip-call-signature")
        self.assertTriggerMatches("split(<|>", name="perl-calltip-call-signature")
        self.assertTriggerMatches("split (<|>", name="perl-calltip-call-signature")
        self.assertTriggerMatches("FOO(<|>", name="perl-calltip-call-signature")
        self.assertTriggerMatches("FOO (<|>", name="perl-calltip-call-signature")
        self.assertTriggerMatches("$FOO->BAR(<|>", name="perl-calltip-call-signature")
        self.assertTriggerMatches("FOO::BAR->BAZ(<|>", name="perl-calltip-call-signature")
        # Currently unable to test this because the Perl lexer assigns
        # a number style to the cursor position in the test suite setup.
        # I can't repro that style-assignment in the normal editor and
        # it seems to work fine there, so leaving this for now.
        #self.assertTriggerMatches("FOO'BAR->BAZ(<|>", name="perl-calltip-call-signature")
        self.assertTriggerMatches("&FOO(<|>", name="perl-calltip-call-signature")
        if 1:
            self.assertNoTrigger("&$FOO(<|>")
            self.assertNoTrigger("&$ FOO(<|>")
        else:
            # Really this *is* allowed, but the current Perl completion
            # implementation practically won't be able to identify the
            # sub reference assigned to $FOO.
            self.assertTriggerMatches("&$FOO(<|>", name="perl-calltip-call-signature")
            self.assertTriggerMatches("&$ FOO(<|>", name="perl-calltip-call-signature")
        self.assertNoTrigger("$FOO(")
        self.assertNoTrigger("$ FOO(")
        self.assertNoTrigger("@FOO(")
        self.assertNoTrigger("@ FOO(")
        # We *could* have the Perl completion trigger handling trigger on
        # the following and let subsequent CITDL evaluation rule them out,
        # but for efficiency we will try to rule them out here.
        self.assertNoTrigger("sub(<|>")
        self.assertNoTrigger("sub (<|>")
        self.assertNoTrigger("sub FOO(<|>")
        self.assertNoTrigger("sub FOO::BAR(<|>")
        self.assertNoTrigger("sub FOO'BAR(<|>") # see bigrat.pl in Perl lib
        self.assertNoTrigger("sub FOO::BAR::BAZ(<|>")
        for keyword in ("if", "else", "elsif", "while", "for",
                        "sub", "unless", "my", "our"):
            self.assertNoTrigger("%s (<|>" % keyword)
            self.assertNoTrigger("%s(<|>" % keyword)
        self.assertNoTrigger("foreach $foo (<|>")
        self.assertNoTrigger("foreach my $foo (<|>")

    @tag("knownfailure")
    def test_calltip_call_signature_adv(self):
        self.assertTriggerMatches("-r <|>",
            name="perl-calltip-space-call-signature", pos=3, length=1)

        for keyword in ("if", "else", "elsif", "while", "for",
                        "sub", "unless", "my", "our", "package"):
            self.assertNoTrigger("%s <|>" % keyword)

    def test_calltip_call_signature(self):
        self.assertNoTrigger("'chdir <|>'")
        self.assertNoTrigger("# chdir <|>")
        self.assertTriggerMatches("chdir <|>",
            name="perl-calltip-space-call-signature", pos=6)

        self.assertNoTrigger("'chdir(<|>'")
        self.assertNoTrigger("# chdir(<|>")
        self.assertTriggerMatches("chdir(<|>",
            name="perl-calltip-call-signature", pos=6)

    def test_preceding_trg_from_pos(self):
        self.assertNoPrecedingTrigger("$Foo:: <|><$>")
        self.assertNoPrecedingTrigger("Foo::bar<$>(<|>")

        self.assertPrecedingTriggerMatches(
            "Foo::bar(Pow::smash('foo<$><|>",
            name="perl-calltip-call-signature", pos=20)
        self.assertPrecedingTriggerMatches(
            "Foo::bar(Pow::smash<$>('foo<|>",
            name="perl-calltip-call-signature", pos=9)
        self.assertNoPrecedingTrigger(
            "Foo::bar<$>(Pow::smash('foo<|>")

        self.assertPrecedingTriggerMatches(
            "Foo::bar<|><$>",
            name="perl-complete-package-members", pos=5)
        self.assertNoPrecedingTrigger(
            "Foo<$>::bar<|>")

        self.assertPrecedingTriggerMatches(
            "$foo->bar<|><$>",
            name="perl-complete-*-subs", pos=6)
        self.assertNoPrecedingTrigger(
            "$foo<$>->bar<|>")

        self.assertPrecedingTriggerMatches(
            dedent("""\
                Foo::bar(  # try to (screw ' {] ) this up
                    Pow::smash('foo<$><|>
            """),
            name="perl-calltip-call-signature", pos=57)
        self.assertPrecedingTriggerMatches(
            dedent("""\
                Foo::bar(  # try to (screw ' {] ) this up
                    Pow::smash<$>('foo<|>
            """),
            name="perl-calltip-call-signature", pos=9)

        # Test in a comment.
        self.assertPrecedingTriggerMatches(
            dedent("""\
                #
                # Foo::bar(
                #    Pow::smash<$>('foo<|>
                #
            """),
            name="perl-calltip-call-signature", pos=13)

        #XXX Test in POD

        # Test out-of-range calltip
        self.assertPrecedingTriggerMatches(
            "foo(bar('hi'), <|><$>",
            name="perl-calltip-call-signature", pos=4)

        # Test space-based calltips
        self.assertPrecedingTriggerMatches(
            dedent("""\
                chmod FPO # try to (screw ' {] ) this up
                    Pow::smash<$>('foo<|>
            """),
            name="perl-calltip-space-call-signature", pos=6)
        self.assertNoPrecedingTrigger(
            dedent("""\
                chmod FOO; # try to (screw ' {] ) this up
                    Pow::smash<$>('foo<|>
            """))

    @tag("knownfailure", "bug68347")
    def test_preceding_trg_from_pos_2(self):
        # This test succeeds, it's our control
        self.assertPrecedingTriggerMatches(
            "Foo::Barx<$><|>y",
            name="perl-complete-package-members", pos=5)
        # But this test fails.
        self.assertPrecedingTriggerMatches(
            "Foo::Bar2<$><|>3",
            name="perl-complete-package-members", pos=5)

class CodeintelPerlTestCase(CodeIntelTestCase):
    lang = "Perl"
    _perlVersion = None
    @property
    def perl_version(self):
        # Return a tuple of (major, minor, subminor) version numbers
        if self._perlVersion is None:
            langintel = self.mgr.langintel_from_lang(self.lang)
            ver, _, _ = langintel.perl_info_from_env(self.mgr.env)
            # ver is a string, convert to float for comparisons to work.
            self._perlVersion = tuple([int(x) for x in ver.split('.')])
        return self._perlVersion

class CplnTestCase(CodeintelPerlTestCase):
    test_dir = join(os.getcwd(), "tmp")

    def test_curr_calltip_arg_range(self):
        # Python's equivalent test case covers paren-based calltips.

        self.assertCurrCalltipArgRange("chdir <+>;<|>", "chdir DIR", (-1,-1))
        self.assertCurrCalltipArgRange("join(',', split <+>$foo)<|>",
                                       "split STRING", (-1,-1))
        self.assertCurrCalltipArgRange("$blah{join <+>',', $parts}<|>",
                                       "join SEP, LIST", (-1,-1))

        # Currently commas in regex's *will* screw up determination.
        # Best way to handle that would be with style info. Or could
        # have a lang-specific dict of block chars -- Perl would have
        # {'/': '/'} in addition to the regulars.
        #self.assertCurrCalltipArgRange("foo(<+>/first,last/, <|>'t,m');",
        #                               "foo(a, b, c)", (7,8))

    def test_complete_available_imports(self):
        name = "perl-complete-available-imports"
        self.assertTriggerMatches("use <|>;", name=name, prefix="")
        self.assertTriggerMatches("no <|>;", name=name, prefix="")
        self.assertTriggerMatches("require <|>;", name=name, prefix="")
        self.assertTriggerDoesNotMatch("use strict; <|>", name=name)

        self.assertCompletionsInclude(
            "use <|>strict",
            [("module", "strict")])
        self.assertCompletionsInclude(
            "no <|>strict",
            [("module", "strict")])
        self.assertCompletionsInclude(
            "require <|>LWP",
            [("module", "LWP")])

    def test_complete_variables(self):
        self.assertCompletionsAre(
            """
            my $varThis = 1;
            our $varThat = 2;
            $<|>
            """,
            [("variable", "varThat"),
             ("variable", "varThis")])

    def test_complete_variables_scoping(self):
        self.assertCompletionsAre(
            """
            my $varGlobal = undef;
            our $varPackage = 2;
            sub someFunc {
                my $varFunc = 1;
            }
            $<|>
            """,
            [("variable", "varGlobal"),
             ("variable", "varPackage")])

    def test_citdl_expr_and_prefix_filter_from_trg(self):
        self.assertCITDLExprIs("split <|>", "split")
        self.assertCITDLExprIs("chmod(<|>", "chmod")
        self.assertCITDLExprIs("&$make_coffee(<|>", "$make_coffee")
        self.assertCITDLExprIs("$foo . $bar-><|>", "$bar")
        self.assertCITDLExprIs("foo[split <|>", "split")
        #XXX Might want to consider aborting on the following case because
        #    barewords are allowed in Perl hash indexing.
        self.assertCITDLExprIs("foo{split <|>", "split")
        self.assertCITDLExprIs("foo()-><|>", None)
        self.assertCITDLExprIs("foo(a,b)-><|>", None)
        self.assertCITDLExprIs("my $a = $foo-><|>", "$foo")

        
        self.assertCITDLExprIs("foo;bar(<|>", "bar")
        self.assertCITDLExprIs("foo(bar,baz(<|>", "baz")
        self.assertCITDLExprIs("split join <|>", "join")
        self.assertCITDLExprIs("foo->bar(<|>", "foo.bar")
        self.assertCITDLExprIs("Win32::OLE-><|>", "Win32::OLE")
        self.assertCITDLExprIs("Win32::OLE->GetObject(<|>", "Win32::OLE.GetObject")

        self.assertCITDLExprIs("split(/foo/,\n    join(<|>", "join")
        self.assertCITDLExprIs("split(/foo()/,\n    join(<|>", "join")
        self.assertCITDLExprIs("split(/foo/,\r\n    join(<|>", "join")

        self.assertCITDLExprIs("sub foo {}\n\nsplit <|>", "split")

        # Preceding statement was not properly terminated with ';'.
        self.assertCITDLExprIs("$ua->agent()\nmy <|>", "my")

        self.assertCITDLExprIs("# Data::Dumper->\n\nDumperX(<|>",
                               # NOT Data::Dumper.DumperX
                               "DumperX")

        testcases = dedent(r"""
            Foo::Bar(<|>        # Foo.Bar
            Foo::Bar <|>        # Foo.Bar
            Foo::Bar::<|>       # Foo::Bar ''
            Foo::Bar-><|>       # Foo::Bar
            $Foo::Bar-><|>      # Foo.$Bar
            $Foo::Bar::<|>      # Foo::Bar '$'
            @Foo::Bar::<|>      # Foo::Bar '@'
            %Foo::Bar::<|>      # Foo::Bar '%'
            &Foo::Bar::<|>      # Foo::Bar ''
            *Foo::Bar::<|>      # Foo::Bar '*'
            @$Foo::Bar::<|>     # Foo::Bar '@$'
            %$Foo::Bar::<|>     # Foo::Bar '%$'
            &$Foo::Bar::<|>     # Foo::Bar '$'
            $Foo::Bar(<|>       # Foo.$Bar
            $Foo::Bar <|>       # Foo.$Bar

            m <|>         # m
            split <|>     # split
            baz::<|>      # baz
            $2baz::<|>    #
            $baz-><|>     # $baz
            @baz-><|>     # @baz
            %baz-><|>     # %baz
            *baz-><|>     # *baz
            &baz-><|>     # baz
            &$baz-><|>    # $baz
            \$baz-><|>    # \$baz
            $foo = \*baz-><|>        # \*baz
            $::bar-><|>              # $bar
            ::Bar2::_baz(<|>         # ::Bar2._baz
            $FOO::Bar2::_baz(<|>     # FOO::Bar2.$_baz
            @FOO::Bar2::_baz(<|>     # FOO::Bar2.@_baz
            %FOO::Bar2::_baz(<|>     # FOO::Bar2.%_baz
            *FOO::Bar2::_baz(<|>     # FOO::Bar2.*_baz
            &FOO::Bar2::_baz(<|>     # FOO::Bar2._baz
            &$FOO::Bar2::_baz(<|>    # FOO::Bar2.$_baz
            \$FOO::Bar2::_baz(<|>    # FOO::Bar2.\$_baz
            \*FOO::Bar2::_baz(<|>    # FOO::Bar2.\*_baz

            $ baz-><|>     # $baz
        """).splitlines(0)
        for testcase in testcases:
            if not testcase.strip(): continue
            input, expected = testcase.split('#')
            expected = expected.strip()
            if not expected:
                expected_citdl, expected_filter = None, None
            elif ' ' in expected:
                expected_citdl, expected_filter_repr = expected.split()
                expected_filter = eval(expected_filter_repr)
            else:
                expected_citdl, expected_filter = expected, None
            self.assertCITDLExprIs(input, expected_citdl,
                                   prefix_filter=expected_filter)


    def test_calltip_call_signature(self):
        self.assertCalltipIs("chdir <|>",
            "chdir EXPR\nChanges the working directory to EXPR, if possible.")
        self.assertCalltipIs("chmod <|>",
            "chmod LIST\nChanges the permissions of a list of files.")

    @tag("bug65247")        
    def test_empty_use_completion_block(self):
        self.assertCompletionsAre("use NoSuchDir::<|>", None);

    @tag("bug68900")
    def test_bug35769(self):
        # bug 35769: Inherited methods of HTTP::Request not suggested
        markedup_content = dedent("""
            use HTTP::Request;
            my $req = HTTP::Request->new(GET => "http://www.example.com");

            # This should include the members from
            # HTTP::Request's base class HTTP::Message.
            $req-><|>
        """)
        self.assertCompletionsInclude(markedup_content,
                # some methods from HTTP::Request
               [('function', 'as_string'),
                ('function', 'clone'),
                ('function', 'new'),
                # some methods from base HTTP::Message
                ('function', 'add_content'),
                ('function', 'protocol'),
                ('function', 'headers_as_string')
                ])

    @tag("bug68900c")
    def test_bug68900_1(self):
        self.assertNoTrigger("><|>")

    @tag("bug68900c")
    def test_bug68900_2(self):
        self.assertNoTrigger("><|>")

    @tag("bug68900", "bug68900b")
    def test_bug36128(self):
        content, positions = unmark_text(dedent("""
            package Bug36128;
            use Data::Dumper;

            sub foo {
                my $dumper = Data::Dumper->new(42);
                $dumper-><1>blah();
            }

            sub bar {
                use HTTP::Request;
                my $req = HTTP::Request->new(GET => "http://www.example.com");
                $req-><2>blah();
            }
        """))

        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [('function', 'Deepcopy'),
             ('function', 'Dump')]
        )

        self.assertCompletionsInclude(
            markup_text(content, pos=positions[2]),
            [# methods from HTTP::Request
             ('function', 'as_string'),
             ('function', 'clone'),
             ('function', 'new'),
             # some methods from base HTTP::Message
             ('function', 'add_content'),
             ('function', 'protocol'),
             ('function', 'headers_as_string')]
        )
        
    @tag("bug81788")
    def test_bug81788a(self):
        self.assertTriggerMatches("$req-><|>", name="perl-complete-*-subs")
        self.assertTriggerMatches("$req1-><|>", name="perl-complete-*-subs")

    @tag("bug81788")
    def test_bug81788b(self):
        """ test_bug81788b fails as long as test_bug817881 fails"""
        content, positions = unmark_text(dedent("""
            use HTTP::Request;
            my $req1 = HTTP::Request->new(GET => "http://www.example.com");
            $req1-><1>blah();
        """))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [# methods from HTTP::Request
             ('function', 'as_string'),]
        )
        
    @tag("bug68900b")
    def test_my_vars(self):
        test_dir = join(self.test_dir, "test_myvars")
        script_path = join(test_dir, "perlscript.pl")
        module_path = join(test_dir, "PerlModule.pm")
        script_content, script_positions = unmark_text(dedent("""\
            #!/usr/bin/perl -w
            use PerlModule qw(:all);

            PerlModule::<2>SubModule::<3>blah;
            $PerlModule::<4>SubModule::<5>blah;
        """))

        manifest = [
            (script_path, script_content),
            (module_path, dedent("""
                package PerlModule;
                use vars qw ($myscalar @myarray %myhash);
                require Exporter;
                @ISA = qw(Exporter);
                @EXPORT = qw(myfunc $myscalar @myarray %myhash);
                @EXPORT_OK = qw();
                %EXPORT_TAGS = (all => [ @EXPORT_OK, @EXPORT ]);

                sub myfunc {
                    my ($a, $b) = @_;
                }

                $myscalar = 42;
                @myarray = ('a', 'b', 'c');
                %myhash = ('one'=>1, 'two'=>2, 'three'=>3);


                package PerlModule::SubModule;
                use vars qw ($subscalar @subarray %subhash);
                require Exporter;
                @ISA = qw(Exporter);
                @EXPORT = qw(subfunc $subscalar @subarray %subhash);
                @EXPORT_OK = qw();
                %EXPORT_TAGS = (all => [ @EXPORT_OK, @EXPORT ]);

                sub subfunc {
                    my ($a, $b) = @_;
                }

                $subscalar = 42;
                @subarray = ('a', 'b', 'c');
                %subhash = ('one'=>1, 'two'=>2, 'three'=>3);

                my $localvar;

                1;
             """)),
        ]
        for file, content in manifest:
            path = join(test_dir, file)
            writefile(path, content)

        script_buf = self.mgr.buf_from_path(script_path)
        self.assertCompletionsAre2(script_buf, script_positions[2],
            [('function', 'myfunc'),
             ('class', 'SubModule')])
        self.assertCompletionsAre2(script_buf, script_positions[3],
            [('function', 'subfunc')])
        self.assertCompletionsAre2(script_buf, script_positions[4],
            # ensure that $localvar is NOT in the list
            [('@variable', 'myarray'),
             ('%variable', 'myhash'),
             ('$variable', 'myscalar'),
             ('class', 'SubModule')])
        self.assertCompletionsAre2(script_buf, script_positions[5],
            # ensure that $localvar is NOT in the list
            [('@variable', 'subarray'),
             ('%variable', 'subhash'),
             ('$variable', 'subscalar')])

    @tag("bug80856")
    def test_bug80856a(self):
        content, positions = unmark_text(dedent("""
            use HTTP::Request;
            my $req = new HTTP::Request(GET => "http://www.example.com");
            $req-><1>blah();
        """))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [# methods from HTTP::Request
             ('function', 'as_string'),]
        )

    def test_my_vars_2(self):
        content, positions = unmark_text(dedent("""\
            use HTTP::Request::Common;
            {
                package FooBar;
                @ISA = qw(HTTP::Request::Common);
                @EXPORT = qw(foobar_sub $foobar_scalar);

                sub foobar_sub {
                    print "hi from foobar_sub\\n";
                }
                $foobar_scalar = 23;
            }

            FooBar::<1>foobar_sub();    # should NOT include inherited subs
            $FooBar::<2>foobar_scalar;  # should NOT include inherited vars
            FooBar-><3>foobar_sub();    # SHOULD include inherited subs
        """))

        self.assertCompletionsAre(
            markup_text(content, pos=positions[1]),
            [('function', 'foobar_sub')])
        self.assertCompletionsAre(
            markup_text(content, pos=positions[2]),
            [('$variable', 'foobar_scalar')])
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[3]),
            [('function', 'boundary'),
             ('function', 'foobar_sub'),
             ('function', 'form_data'),
             ('function', 'GET'),
             ('function', 'HEAD'),
             ('function', 'POST'),
             ('function', 'PUT'),
             ('function', '_simple_req')])

    def test_localsubs(self):
        content, positions = unmark_text(dedent("""\
            =item foo($apple, $banana)

            Do some stuff!

            =cut

            sub foo {
                my ($a, $b) = @_;
            }

            sub bar {
                my ($c, $d) = @_;
            }

            foo(<1>);
            bar(<2>);
        """))
        PERL_CILE_SCANS_POD_SECTIONS = False
        if PERL_CILE_SCANS_POD_SECTIONS:
            self.assertCalltipIs(markup_text(content, pos=positions[1]),
                                 "foo($apple, $banana)\nDo some stuff!")
        else:
            self.assertCalltipIs(markup_text(content, pos=positions[1]),
                                 "foo($a, $b)")
        self.assertCalltipIs(markup_text(content, pos=positions[2]),
                             "bar($c, $d)")
        
    @tag("lwp")
    def test_lwp_includes_nodebug(self):
        perl_version = self.perl_version
        content, positions = unmark_text(dedent(r"""
            use LWP;
            my $ua = LWP::<1>UserAgent->new;
            #              -- should include Protocol and UserAgent only post 5.8
            # perl version: %s
        """ % (perl_version,)))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]), # LWP::<|>
            [("class", "Protocol"),
             ("class", "UserAgent")])
        if perl_version < (5, 9):
            # Accept any 5.8.x version or earlier.
            self.assertCompletionsInclude(
                markup_text(content, pos=positions[1]),
                [("class", "Debug")])
        elif perl_version >= (5, 12):
            self.assertCompletionsDoNotInclude(
                markup_text(content, pos=positions[1]),
                [("class", "Debug")])
        
    @tag("lwp")
    def test_lwp_includes_with_debug(self):
        content, positions = unmark_text(dedent(r"""
            use LWP;
            use LWP::Debug;
            $ua = LWP::<1>UserAgent->new;
            #              -- should include Debug as well
        """))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]), # LWP::<|>
            [("class", "Debug"),
             ("class", "Protocol"),
             ("class", "UserAgent")])


    @tag("gisle")
    def test_lwp(self):
        content, positions = unmark_text(dedent(r"""
            use LWP;
            HTTP::<1>Response::<2>blah();
            #     |            `-- should get package members here
            #     `-- should include Request, Response, Date (and
            #         arguably some others)q

            my $ua = LWP::<3>UserAgent-><4>new;
            #             `-- should include Debug, Protocol, UserAgent
            $ua-><5>mirror(<6>);
            #    |         `-- should get a reasonable calltip here
            #    `-- should include members

            # Example of subclassing derived from Gisle's C:\Perl\bin\GET.
            {
                package RequestAgent;
                @ISA = qw(LWP::UserAgent);

                sub new
                { 
                    my $self = LWP::UserAgent::new(@_);
                    $self->agent("lwp-request/$main::VERSION");
                    $self;
                }

                sub foobar {}

                sub get_basic_credentials
                {
                    my($self, $realm, $uri) = @_;
                    #...
                }
            }

            my $ra = RequestAgent-><7>new();
            #                      `-- should have local and inherited methods
            $ra-><8>get_basic_credentials(<9>);
            #    |                        `-- should get a reasonable calltip here
            #    `-- should have local and inherited methods

            # '_elem' is from LWP::MemberMixin (a base pkg of
            # LWP::UserAgent), i.e. testing recursive inheritance.
            $ra->_elem(<0>);
            # Perl version: """ + "%s" % (self.perl_version,)))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]), # HTTP::<|>
            [("class", "Request"),
             ("class", "Response"),
             ("class", "Date")])
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[2]), # HTTP::Response::<|>
            [("function", "as_string"),
             ("function", "base"),
             ("function", "clone")])
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[3]), # LWP::<|>
            [("class", "Protocol"),
             ("class", "UserAgent")])
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[4]), # LWP::UserAgent-><|>
            [("function", "new")])
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[5]), # $ua-><|>
            [("function", "agent"),
             ("function", "conn_cache"),
             ("function", "clone"),
             ("function", "mirror")])
        if PERL_STDLIB_HAS_POD_INFO:
            self.assertCalltipIs(
                markup_text(content, pos=positions[6]), # $ua->mirror(<|>)
                ("$ua->mirror( $url, $filename )\n"
                 "This method will get the document identified by $url and\n"
                 "store it in file called $filename."))
        else:
            self.assertCalltipIs(
                markup_text(content, pos=positions[6]), # $ua->mirror(<|>)
                "mirror($self, $url, $file)")
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[7]), # RequestAgent-><|>
            [# new or overriden methods
             ("function", "new"),
             ("function", "foobar"),
             ("function", "get_basic_credentials"),
             # inherited methods
             ("function", "agent"),
             ("function", "conn_cache"),
             ("function", "clone"),
             ("function", "mirror")])
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[8]), # $ra-><|>
            [# new or overriden methods
             ("function", "new"),
             ("function", "foobar"),
             ("function", "get_basic_credentials"),
             # inherited methods
             ("function", "agent"),
             ("function", "conn_cache"),
             ("function", "clone"),
             ("function", "mirror")])
        self.assertCalltipIs(
            markup_text(content, pos=positions[9]), # $ra->get_basic_credentials(<|>
            "get_basic_credentials($self, $realm, $uri)")
        if PERL_STDLIB_HAS_POD_INFO:
            self.assertCalltipIs(
                markup_text(content, pos=positions[0]),
                ("_elem($elem [, $val])\n"
                 "Internal method to get/set the value of member variable\n"
                 "$elem."))
        else:
            self.assertCalltipIs(
                markup_text(content, pos=positions[0]),
                "_elem($self, $elem)")

    @tag("import")
    def test_cpan(self):
        content, positions = unmark_text(dedent("""\
            use CPAN;
            CPAN::<1>Bundle->force();
        """))
        # CPAN.pm defines more package than just "CPAN". This test
        # ensures that those get included in "CPAN::<|>".
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]), # CPAN::<|>
            [("class", "Bundle")])

    @tag("import", "play")
    def test_imports_1(self):
        content, positions = unmark_text(dedent("""\
            use Data::Dumper;

            my @foo = ("one", "two", "three", "four");
            print Dumper(<1>@foo);
            #            `- Should work, because Dumper is in @EXPORT.
            print DumperX(<2>@foo);
            #             `- Should NOT work, because DumperX is in @EXPORT_OK, not @EXPORT.
        """))
        if PERL_STDLIB_HAS_POD_INFO:
            self.assertCalltipIs(
                markup_text(content, pos=positions[1]), # Dumper(<|>)
                ("Dumper(LIST)\n"
                 "Returns the stringified form of the values in the list,\n"
                 "subject to the configuration options below."))
        else:
            self.assertCalltipIs(
                markup_text(content, pos=positions[1]), # Dumper(<|>)
                "Dumper()")
        self.assertCalltipIs(
            markup_text(content, pos=positions[2]), # DumperX(<|>)
            None)

    @tag("import", "play", "bug65739")
    def test_imports_2(self):
        content, positions = unmark_text(dedent("""\
            use Data::Dumper qw(Dumper DumperX);
            my @foo = ("one", "two", "three", "four");
            print Dumper(<1>@foo);
            print DumperX(<2>@foo);
        """))
        if PERL_STDLIB_HAS_POD_INFO:
            self.assertCalltipIs(
                markup_text(content, pos=positions[1]), # Dumper(<|>)
                ("Dumper(LIST)\n"
                 "Returns the stringified form of the values in the list,\n"
                 "subject to the configuration options below."))
        else:
            self.assertCalltipIs(
                markup_text(content, pos=positions[1]), # Dumper(<|>)
                "Dumper()")
        self.assertCalltipIs(
            markup_text(content, pos=positions[2]), # DumperX(<|>)
            "DumperX()")

    @tag("import")
    def test_imports_3(self):
        # Test the fallback hack for handling Perl @EXPORT_TAGS.
        content, positions = unmark_text(dedent("""\
            use Benchmark qw(:all);
            timeit(<1>);
            #       `-- from Benchmark.pm's @EXPORT
            timesum(<2>);
            #       `-- from Benchmark.pm's @EXPORT_OK

            use Data::Dumper ();
            my @foo = ("one", "two", "three", "four");
            print Dumper(<3>@foo);
            #            `-- should fail
            print Data::Dumper::Dumper(<4>@foo);
            #                          `-- should work just fine
        """))
        if PERL_STDLIB_HAS_POD_INFO:
            self.assertCalltipIs(
                markup_text(content, pos=positions[1]), # timeit(<|>)
                ("timeit(COUNT, CODE)\n"
                 "Arguments: COUNT is the number of times to run the loop,\n"
                 "and CODE is the code to run."))
            self.assertCalltipIs(
                markup_text(content, pos=positions[2]), # timesum(<|>)
                ("timesum ( T1, T2 )\n"
                 "Returns the sum of two Benchmark times as a Benchmark\n"
                 "object suitable for passing to timestr()."))
        else:
            self.assertCalltipIs(
                markup_text(content, pos=positions[1]), # timeit(<|>)
                "timeit($n, $code)")
            self.assertCalltipIs(
                markup_text(content, pos=positions[2]), # timesum(<|>)
                "timesum($a, $b)")
        self.assertCalltipIs(
            markup_text(content, pos=positions[3]),
            None)
        if PERL_STDLIB_HAS_POD_INFO:
            self.assertCalltipIs(
                markup_text(content, pos=positions[4]),
                ("Dumper(LIST)\n"
                 "Returns the stringified form of the values in the list,\n"
                 "subject to the configuration options below."))
        else:
            self.assertCalltipIs(
                markup_text(content, pos=positions[4]),
                "Dumper()")

    def test_import_no_auto(self):
        """
        Check that we don't automatically import all available modules
        """
        content = dedent("""\
            Env::<|>
        """)
        self.assertCompletionsAre(content, None)

    def test_data_dumper(self):
        content, positions = unmark_text(dedent("""\
            use Data::Dumper;
            my @foo = ("one", "two", "three", "four");

            print Data::Dumper::Dumper(<1>@foo);
            print Data::Dumper-><2>Dump(<3>\@foo);
            print $Data::<4>Dumper::<5>Indent;

            my $d = Data::Dumper->new(\@foo);
            $d-><6>Dump();
            #   `-- should include Dump, Purity, Terse
        """))
        if PERL_STDLIB_HAS_POD_INFO:
            self.assertCalltipIs(
                markup_text(content, pos=positions[1]),
                ("Dumper(LIST)\n"
                 "Returns the stringified form of the values in the list,\n"
                 "subject to the configuration options below."))
        else:
            self.assertCalltipIs(
                markup_text(content, pos=positions[1]),
                "Dumper()")
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[2]), # Data::Dumper-><|>
            [("function", "Dumper")])
        if PERL_STDLIB_HAS_POD_INFO:
            self.assertCalltipIs(
                markup_text(content, pos=positions[3]),
                ("$OBJ->Dump  or  PACKAGE->Dump(ARRAYREF [, ARRAYREF])\n"
                 "Returns the stringified form of the values stored in the object\n"
                 '(preserving the order in which they were supplied to "new"), \n'
                 "subject to the configuration options below."))
        else:
            self.assertCalltipIs(
                markup_text(content, pos=positions[3]),
                "Dump()")
        self.assertCompletionsAre(
            markup_text(content, pos=positions[4]), # $Data::
            [("class", "Dumper")])
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[5]), # $Data::Dumper::<|>
            [("$variable", "Indent"),
             ("$variable", "Purity")])
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[6]),
            [("function", "Dump"),
             ("function", "Purity"),
             ("function", "Terse")])

    @tag("knownfailure")
    def test_retval_chaining(self):
        content, positions = unmark_text(dedent("""\
            use Data::Dumper;
            $d = Data::Dumper->new([$foo, $bar], [qw(foo *ary)]);
            $d-><1>Purity(<2>1)-><3>Terse(<4>1)-><5>Deepcopy(<6>1);
        """))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("function", "Purity")])
        self.assertCalltipIs(
            markup_text(content, pos=positions[2]),
            ("Purity($s, $v)"))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[3]),
            [("function", "Terse")])
        self.assertCalltipIs(
            markup_text(content, pos=positions[4]),
            ("Terse(TODO)"))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[5]),
            [("function", "Deepcopy")])
        self.assertCalltipIs(
            markup_text(content, pos=positions[6]),
            ("Deepcopy(TODO)"))

    @tag("bug65474")
    def test_complete_available_modules_prefix(self):
        #       use <|>
        # Ensure that this includes the prefix for multi-level Perl
        # modules even if there isn't a single-level version. For
        # example, there is "HTTP::Request" but there is not "HTTP"
        # module -- "HTTP" should still be a completion for the above
        # trigger.
        self.assertCompletionsInclude("use <|>",
            [("directory", "HTTP"),
             ("directory", "File"),
             ("directory", "XML"),
             ("directory", "LWP"),
             ("module", "LWP")])
        self.assertCompletionsAre("use LWP::<|>",
            [("directory", "Authen"),
             ("module", "ConnCache"),
             ("module", "Debug"),
             ("module", "DebugFile"),
             ("module", "MediaTypes"),
             ("module", "MemberMixin"),
             ("directory", "Protocol"),
             ("module", "Protocol"),
             ("module", "RobotUA"),
             ("module", "Simple"),
             ("module", "UserAgent")])

    def test_http(self):
        content, positions = unmark_text(dedent("""\
            use HTTP::<1>Request;
            HTTP::<2>Headers::<3>Util::<4>join_header_words;
        """))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("module", "Date"), ("module", "Headers"), ("module", "Message"),
             ("module", "Request")])
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[2]),
            [("class", "Date"),
             ("class", "Headers"),  # Message.pm imports HTTP::Headers (among others)
             ("class", "Message"),  # Request.pm imports HTTP::Message
             ("class", "Request"),  # directly imported
            ])
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[3]),
            [("class", "Util"), ("function", "as_string")])
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[4]),
            [("function", "join_header_words")])

    @tag("play", "bug65507")
    def test_play_lwp(self):
        content, positions = unmark_text(dedent("""\
            use LWP;
            use LWP::Debug;
            print LWP::<1>Version();
            print $LWP::<2>VERSION;

            DB-><3>blah;  # should fail b/c DB hasn't been loaded

            my $ua = LWP::UserAgent-><4>new;
            $ua-><5>mirror(<6>);
        """))
        self.assertCompletionsAre(
            markup_text(content, pos=positions[1]),
            [("class", "ConnCache"), ("class", "Debug"),
             ("class", "MediaTypes"), ("class", "MemberMixin"), 
             ("class", "Protocol"), ("class", "UserAgent"),
             ("function", "Version")])
        self.assertCompletionsAre(
            markup_text(content, pos=positions[2]),
            [("class", "ConnCache"), ("class", "Debug"),
             ("class", "MediaTypes"), ("class", "MemberMixin"), 
             ("class", "Protocol"), ("class", "UserAgent"),
             ("$variable", "VERSION")])
        self.assertCompletionsAre(
            markup_text(content, pos=positions[3]),
            None)
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[4]),
            [("function", "new"), ("function", "proxy"),
             ("function", "agent"), ("function", "redirect_ok")])

        self.assertCompletionsInclude( #TODO
            markup_text(content, pos=positions[5]),
            [("function", "mirror"), ("function", "proxy"),
             ("function", "agent"), ("function", "redirect_ok")])
        if PERL_STDLIB_HAS_POD_INFO:
            self.assertCalltipIs(
                markup_text(content, pos=positions[6]), # $ua->mirror(<|>)
                ("$ua->mirror( $url, $filename )\n"
                 "This method will get the document identified by $url and\n"
                 "store it in file called $filename."))
        else:
            self.assertCalltipIs(
                markup_text(content, pos=positions[6]), # $ua->mirror(<|>)
                "mirror($self, $url, $file)")

    @tag("play")
    def test_uri(self):
        content, positions = unmark_text(dedent("""\
            use URI;
            my $uri = URI-><1>new("http://foo.com/bar.txt");
            print $uri-><3>scheme;
        """))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("function", "new")])
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[3]),
            [("function", "scheme"), ("function", "as_string")])

    @tag("uri", "bug65516", "knownfailure")
    def test_new_calltip(self):
        content, positions = unmark_text(dedent("""\
            use URI;
            my $uri = URI->new(<2>"http://foo.com/bar.txt");
            print $uri->scheme;
        """))
        # Currently we get (which comes from scanning URI.pm):
        #   new($class, $uri, $scheme)
        if False:
            self.assertCalltipIs(
                markup_text(content, pos=positions[2]),
                "new($class, $uri, $scheme)")

        # Bug 65516 suggests that this should (at least) be:
        #   new($uri, $scheme)
        if True:
            self.assertCalltipIs(
                markup_text(content, pos=positions[2]),
                "new($uri, $scheme)")

    @tag("uri", "cpan", "knownfailure")
    def test_stdlib_calltips(self):
        content, positions = unmark_text(dedent("""\
            use URI;
            my $uri = URI->new(<2>"http://foo.com/bar.txt");
            print $uri->scheme;

            use CPAN;
            CPAN::Bundle->force(<4>);
        """))
        # For the Perl stdlib we should parse available POD docs for
        # better calltips. Also: c.f. PERL_STDLIB_HAS_POD_INFO global
        # in this module that is controlling expected results for a
        # number of tests.
        self.assertCalltipIs(
            markup_text(content, pos=positions[2]),
            dedent("""\
                new( $str )
                new( $str, $scheme )
                
                Constructs a new URI object.  The string representation of a
                URI is given as argument, together with an optional scheme
                specification.
            """))
        self.assertCalltipIs(
            markup_text(content, pos=positions[4]), # CPAN::Bundle->force(<|>)
            ("force($method,@args)\n"
             "Forces CPAN to perform a task that normally would have failed."))

    @tag("require", "import")
    def test_reasonable_require(self):
        # We generally cannot handle Perl 'require' statements because
        # they tend to use string substitution for the imported module
        # name. However, if not, then sometimes we can do it.
        test_dir = join(self.test_dir, "test_reasonable_require")
        foo_path = join(test_dir, "Foo.pm")
        foo_content, foo_positions = unmark_text(dedent("""\
            package Foo;
            require Exporter;
            @ISA = qw(Exporter);
            @EXPORT = qw();
            @EXPORT_OK = qw();

            require 'Bar.pm';

            Bar::<1>barfunc(<2>);
            print $Bar::<3>barscalar;

            1;
        """))

        manifest = [
            (foo_path, foo_content),
            (join(test_dir, "Bar.pm"), dedent("""
                package Bar;
                use vars qw ($barscalar @bararray %barhash);
                require Exporter;
                @ISA = qw(Exporter);
                @EXPORT = qw(barfunc $barscalar @bararray %barhash);
                @EXPORT_OK = qw();
                %EXPORT_TAGS = (all => [ @EXPORT_OK, @EXPORT ]);

                sub barfunc {
                    my ($a, $b) = @_;
                }

                $barscalar = 42;
                @bararray = ('a', 'b', 'c');
                %barhash = ('one'=>1, 'two'=>2, 'three'=>3);

                1;
             """)),
        ]
        for path, content in manifest:
            writefile(path, content)

        foo_buf = self.mgr.buf_from_path(foo_path)
        self.assertCompletionsAre2(foo_buf, foo_positions[1],
            [("function", "barfunc")])
        self.assertCalltipIs2(foo_buf, foo_positions[2],
            "barfunc($a, $b)")
        self.assertCompletionsAre2(foo_buf, foo_positions[3],
            [("@variable", "bararray"),
             ("%variable", "barhash"),
             ("$variable", "barscalar")])

    @tag("inheritance")
    def test_multi_level_expr_with_inheritance(self):
        content, positions = unmark_text(dedent(r"""
            use Data::Dumper;

            # Subclass Data::Dumper;
            {
                package MyData::Dumper;
                @ISA = qw(Data::Dumper);

                sub new
                { 
                    my $self = Data::Dumper::new(@_);
                    $self;
                }

                sub do_it_baby {
                    my $name = shift;
                    print "ooh baby, ooh baby\n";
                }
            }

            my @movies = ("lights", "camera", "action");
            my $d = MyData::Dumper->new(\@movies);
            print $d-><1>Dump(<2>);
            MyData::Dumper::<3>do_it_baby(<4>);
            #               `-- should NOT include Dump from Data::Dumper
            MyData::Dumper::Dump(<5>);
            #                    `-- should NOT work, but shouldn't blow up
        """))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("function", "Dump"),
             ("function", "Values"),
             ("function", "do_it_baby")])
        if PERL_STDLIB_HAS_POD_INFO:
            self.assertCalltipIs(
                markup_text(content, pos=positions[2]),
                ("$OBJ->Dump  or  PACKAGE->Dump(ARRAYREF [, ARRAYREF])\n"
                 "Returns the stringified form of the values stored in the object\n"
                 '(preserving the order in which they were supplied to "new"), \n'
                 "subject to the configuration options below."))
        else:
            self.assertCalltipIs(
                markup_text(content, pos=positions[2]),
                "Dump()")
        self.assertCompletionsAre(
            markup_text(content, pos=positions[3]),
            [("function", "do_it_baby"),
             ("function", "new")])
        self.assertCalltipIs(
            markup_text(content, pos=positions[4]),
            "do_it_baby($name)")
        self.assertCalltipIs(
            markup_text(content, pos=positions[5]),
            None)

    @tag("import", "bug88826")
    def test_multi_level_import(self):
        test_dir = join(self.test_dir, "test_multi_level_import")
        foo_path = join(test_dir, "foo.pl")
        foo_content, foo_positions = unmark_text(dedent("""\
            use Comics::Batman;
            pif(<1>);
        """))

        manifest = [
            (foo_path, foo_content),
            (join(test_dir, "Comics", "Batman.pm"), dedent("""
                package Comics::Batman;
                require Exporter;
                @ISA = qw(Exporter);
                @EXPORT = qw(pif pow);

                sub pif {
                    my $badguy = shift;
                    print "pif $badguy\\n";
                }

                sub pow {
                    my $badguy = shift;
                    print "pow $badguy\\n";
                }

                1;
             """)),
        ]
        for path, content in manifest:
            writefile(path, content)

        foo_buf = self.mgr.buf_from_path(foo_path)
        self.assertCalltipIs2(foo_buf, foo_positions[1],
            "pif($badguy)")

    def test_pkg_import_recursion(self):
        test_dir = join(self.test_dir, "test_pkg_import_recursion")
        you_path = join(test_dir, "You.pm")
        you_content, you_positions = unmark_text(dedent("""\
            package You;
            require Exporter;
            @ISA = qw(Exporter);
            @EXPORT = qw(you);

            sub you {
                print "hi from You";
            }

            use NoYou;
            noyou(<1>);
            NoYou::<2>noyou();
            NoYou-><3>noyou();

            1;
        """))

        manifest = [
            (you_path, you_content),
            (join(test_dir, "NoYou.pm"), dedent("""
                package NoYou;
                require Exporter;
                @ISA = qw(Exporter);
                @EXPORT = qw(noyou);

                sub noyou {
                    print "hi from NoYou";
                }

                use You;
                you();
                You::you();

                1;
             """)),
        ]
        for path, content in manifest:
            writefile(path, content)

        you_buf = self.mgr.buf_from_path(you_path)
        self.assertCalltipIs2(you_buf, you_positions[1],
            "noyou()")
        self.assertCompletionsAre2(you_buf, you_positions[2],
            [("function", "noyou")])
        self.assertCompletionsAre2(you_buf, you_positions[3],
            [("function", "noyou")])

    @tag("bug105308")
    def test_variable_assignment_from_property(self):
        content, positions = unmark_text(dedent(r"""
            my $arrayRef = ['a', 'b', 'c'];
            my $theNumberTwo = 2;
            
            # These parsing of these lines would accidently skip over one line,
            # causing a variable declaration to be skipped.
            my $thirdElement = $arrayRef->[$theNumberTwo];
            my $someElement = $arrayRef->[$theNumberTwo];
            my $<1>otherElement = $arrayRef->[$theNumberTwo];
        """))
        self.assertCompletionsInclude(
            markup_text(content, pos=positions[1]),
            [("variable", "thirdElement"),
             ("variable", "someElement"),
             ("variable", "otherElement")])



class DefnTestCase(CodeintelPerlTestCase):
    lang = "Perl"
    test_dir = join(os.getcwd(), "tmp")

    def test_citdl_expr_under_pos_simple(self):
        tests = [line.split() for line in """\
                    Foo::Bar::<|>       Foo::Bar
                    $Foo::Bar::<|>      Foo::Bar
                    Foo::B<|>ar->       Foo::Bar
                    $Foo::Bar-><|>      Foo.$Bar

                    $<|>foo             $foo
                    <|>$foo             $foo
                    $foo<|>             $foo
                    $fo<|>o             $foo
                    @fo<|>o             @foo
                    %fo<|>o             %foo

                    Foo::Bar->ne<|>w        Foo::Bar.new
                    Foo::Bar::Baz->ne<|>w   Foo::Bar::Baz.new

                    foo(ba<|>r          bar
                    foo[ba<|>r          bar
                    foo{ba<|>r          bar
                """.splitlines(0) if line.strip()]

        for content, citdl_expr in tests:
            self.assertCITDLExprUnderPosIs(content, citdl_expr)

    def test_simple(self):
        test_dir = join(self.test_dir, "test_defn_simple")
        foo_content, foo_positions = unmark_text(dedent("""\
            use Bar;
            b<1>arsub();
            <2>Ba<3>r-><4>ba<5>rsub();
            Ba<6>r:<7>:ba<8>rsub();
        """))

        manifest = [
            ("Bar.pm", dedent("""\
                package Bar;
                require Exporter;
                @ISA = qw(Exporter);
                @EXPORT = qw(barsub);

                sub barsub {
                    print "hi from Bar::bar";
                }

                1;
             """)),
            ("foo.pl", foo_content),
        ]
        for file, content in manifest:
            path = join(test_dir, file)
            writefile(path, content)

        barsub_expectations = dict(ilk="function", name="barsub", line=6,
                                   path=join(test_dir, "Bar.pm"), lang="Perl")
        barpkg_expectations = dict(ilk="class", name="Bar", line=1,
                                   path=join(test_dir, "Bar.pm"), lang="Perl")

        buf = self.mgr.buf_from_path(join(test_dir, "foo.pl"))
        for pos in (1,4,5,6,7,8):
            self.assertDefnMatches2(buf, foo_positions[1],
                                    **barsub_expectations)
        for pos in (2,3):
            self.assertDefnMatches2(buf, foo_positions[2],
                                    **barpkg_expectations)

    def test_defn_at_defn(self):
        test_dir = join(self.test_dir, "test_defn_at_defn")
        content, positions = unmark_text(dedent("""\
            {
                package Foo<1>;
                sub new {
                    my $class<2> = shift;
                    my $self = {_bar => 1};
                    bless $self, $class<3>;
                    return $self;
                }
                sub getBar<4>{
                    my ($self) = @_;
                    return $self->{_bar};
                }
            }
            sub makeFoo<5> {
                my $newFoo<6> = new Foo<7>;
                return $newFoo<8>;
            }
            my $foo<9> = makeFoo<10>;
        """))
        path = join(test_dir, "defn_at_defn.pl")
        writefile(path, content)
        buf = self.mgr.buf_from_path(path)
        lines = lines_from_pos(content, positions)
        self.assertDefnMatches2(buf, path=path, pos=positions[1], line=lines[1],
                                ilk="class", name="Foo")
        self.assertDefnMatches2(buf, path=path, pos=positions[2], line=lines[2],
                                ilk="argument", name="$class")
        self.assertDefnMatches2(buf, path=path, pos=positions[3], line=lines[2],
                                ilk="argument", name="$class")
        self.assertDefnMatches2(buf, path=path, pos=positions[4], line=lines[4],
                                ilk="function", name="getBar")
        self.assertDefnMatches2(buf, path=path, pos=positions[5], line=lines[5],
                                ilk="function", name="makeFoo")
        self.assertDefnMatches2(buf, path=path, pos=positions[6], line=lines[6],
                                ilk="variable", name="$newFoo")
        self.assertDefnMatches2(buf, path=path, pos=positions[7], line=lines[1],
                                ilk="class", name="Foo")
        self.assertDefnMatches2(buf, path=path, pos=positions[8], line=lines[6],
                                ilk="variable", name="$newFoo")
        self.assertDefnMatches2(buf, path=path, pos=positions[9], line=lines[9],
                                ilk="variable", name="$foo")
        self.assertDefnMatches2(buf, path=path, pos=positions[10], line=lines[5],
                                ilk="function", name="makeFoo")

    @tag("bug99105")
    def test_compound_variable_defns(self):
        test_dir = join(self.test_dir, "test_compound_variable_defns")
        foo_content, foo_positions = unmark_text(dedent("""\
            #!/usr/bin/env perl
            use strict;
            use warnings;
            my $stump = "trees";
            print $stump<1>;
            my @stuff = qw/abc def/;
            print $stuff<2>[1];
            sub subby {
               my %keys = (abc => 1, defg => 2);
               print $keys<3>{abc};
            }
            subby<4>;
            1;
        """))
        path = join(test_dir, "scope_bounds_01.pl")
        writefile(path, foo_content)
        buf = self.mgr.buf_from_path(path)
        self.assertDefnMatches2(buf, foo_positions[2],
            ilk="variable", name="@stuff", line=6,
            path=path)
        self.assertDefnMatches2(buf, foo_positions[3],
            ilk="variable", name="%keys", line=9,
            path=path)

    @tag("bug99113")
    def test_scope_bounds(self):
        test_dir = join(self.test_dir, "test_scope_bounds")
        foo_content, foo_positions = unmark_text(dedent("""\
            #!/usr/bin/env perl
            use strict;
            use warnings;
            # my $stump = "trees";
            sub testx {
                my $i = shift;
                my $b = 0;
                if ($i > 0) {
                    $b = $i;
                }
            }
            my $t1 = test<1>x(0);
            print("$t1\n");
            1;
        """))
        path = join(test_dir, "scope_bounds.pl")
        writefile(path, foo_content)
        buf = self.mgr.buf_from_path(path)
        self.assertDefnMatches2(buf, foo_positions[1],
            ilk="function", name="testx", line=5,
            path=path, scopestart=1, scopeend=0)
        
    @tag("bug99113")
    def test_scope_bounds_01(self):
        test_dir = join(self.test_dir, "test_scope_bounds_01")
        foo_content, foo_positions = unmark_text(dedent("""\
            #!/usr/bin/env perl
            use strict;
            use warnings;
            my $stump = "trees";
            print $stump<1>;
            my @stuff = qw/abc def/;
            print $stuff<2>[1];
            sub subby {
               my %keys = (abc => 1, defg => 2);
               print $keys<3>{abc};
            }
            subby<4>;
            1;
        """))
        path = join(test_dir, "scope_bounds_01.pl")
        writefile(path, foo_content)
        buf = self.mgr.buf_from_path(path)
        self.assertDefnMatches2(buf, foo_positions[1],
            ilk="variable", name="$stump", line=4,
            path=path, scopestart=1, scopeend=0)
        self.assertDefnMatches2(buf, foo_positions[2],
            ilk="variable", name="@stuff", line=6,
            path=path, scopestart=1, scopeend=0)
        self.assertDefnMatches2(buf, foo_positions[3],
            ilk="variable", name="%keys", line=9,
            path=path, scopestart=8, scopeend=11)
        self.assertDefnMatches2(buf, foo_positions[4],
            ilk="function", name="subby", line=8,
            path=path, scopestart=1, scopeend=0)

    @tag("bug99112")
    def test_get_sub_defn_with_digit(self):
        test_dir = join(self.test_dir, "test_get_sub_defn_with_digit")
        foo_content, foo_positions = unmark_text(dedent("""\
            #!/usr/bin/env perl
            use strict;
            use warnings;
            sub test1 {
                3
            }
            my $t1 = test<1>1(0);
            print("$t1\n");
            1;
        """))
        path = join(test_dir, "get_sub_defn_with_digit.pl")
        writefile(path, foo_content)
        buf = self.mgr.buf_from_path(path)
        self.assertDefnMatches2(buf, foo_positions[1],
            ilk="function", name="test1", line=4, path=path, )

    @tag("bug99108")
    def test_lpath(self):
        test_dir = join(self.test_dir, "test_lpath")
        foo_content, foo_positions = unmark_text(dedent("""\
            #!/usr/bin/env perl
            use strict;
            use warnings;
            sub test1<1> {
                3<5>
            }
            {
              package Outer {
                sub test2<2> {
                    4
                }
            }
            my $t1 = test<3>1(0);
            $t1 += Outer::test2<4>;
            print("$t1\n");
            1;
        """))
        path = join(test_dir, "lpath.pl")
        writefile(path, foo_content)
        buf = self.mgr.buf_from_path(path)
        self.assertDefnMatches2(buf, foo_positions[3],
            ilk="function", name="test1", line=4, path=path,
                                lpath=[],
            #scopestart=4, scopeend=6)
            scopestart=1, scopeend=0)
        self.assertDefnMatches2(buf, foo_positions[4],
            ilk="function", name="test2", line=9, path=path,
                                lpath=['Outer'],
            #scopestart=9, scopeend=11)
            scopestart=8, scopeend=17)
#        self.assertScopeLpathIs(
#            markup_text(foo_content, pos=foo_positions[1]),
#            [])
#        self.assertScopeLpathIs(
#            markup_text(foo_content, pos=foo_positions[5]),
#            ["test1"])
#        self.assertScopeLpathIs(
#            markup_text(foo_content, pos=foo_positions[2]),
#                                ["Outer", "test2"])
#        self.assertScopeLpathIs(
#            markup_text(foo_content, pos=foo_positions[4]),
#                                [])

    @tag("gisle")
    def test_lwp_02(self):
        content, positions = unmark_text(dedent("""\
            use LWP;

            my $ua = LWP::Use<1>rAgent->n<2>ew;
            $<3>ua->mi<5>rror();

            # Example of subclassing derived from Gisle's GET.
            {
                package RequestAgent;
                @ISA = qw(LWP::UserAgent);

                sub new<10>
                { 
                    my $self = LWP::UserAgent::new(@_);
                    $self->agent("lwp-request/$main::VERSION");
                    $self;
                }

                sub foobar {}

                sub get_basic_credentials<12>
                {
                    my($self, $realm, $uri) = @_;
                    #...
                }
            }

            my $ra<11> = Reque<6>stAgent->ne<7>w();
            $r<8>a->get_basic_<9>credentials();
        """))
        
        # When/if perl.cix grows 'src' attributes on blobs, then the
        # 'path' can be asserted for stdlib hits here.
        self.assertDefnMatches(markup_text(content, positions[1]),
                               ilk="class", name="LWP::UserAgent")
        self.assertDefnMatches(markup_text(content, positions[2]),
                               ilk="function", name="new")
        self.assertDefnMatches(markup_text(content, positions[3]),
                               ilk="variable", name="$ua", line=3)
        self.assertDefnMatches(markup_text(content, positions[5]),
                               ilk="function", name="mirror")
        self.assertDefnMatches(markup_text(content, positions[6]),
                               ilk="class", name="RequestAgent", line=8)
        self.assertDefnMatches(markup_text(content, positions[7]),
                               ilk="function", name="new", line=11,
                               lpath=["RequestAgent"])
        self.assertDefnMatches(markup_text(content, positions[8]),
                               ilk="variable", name="$ra", line=27,
                               lpath=[])
        self.assertDefnMatches(markup_text(content, positions[9]),
                               ilk="function", name="get_basic_credentials",
                               line=20, lpath=["RequestAgent"])
        self.assertScopeLpathIs(markup_text(content, positions[10]),
                          ["RequestAgent", "new"])
        self.assertScopeLpathIs(markup_text(content, positions[11]),
                          lpath=[])
        self.assertScopeLpathIs(markup_text(content, positions[12]),
                          lpath=["RequestAgent", "get_basic_credentials"])




#---- mainline

if __name__ == "__main__":
    unittest.main()


