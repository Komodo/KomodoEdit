# Copyright (c) 2012-2013 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

import unittest

from xpcom import components
from xpcom.server import UnwrapObject

from testlib import tag

class koLanguageSvcTestCase(unittest.TestCase):
    """Base class for koIDocument test cases."""
    _langRegistrySvc = None
    _langRegistrySvcUnwrapped = None
    @property
    def langRegistrySvc(self):
        if self._langRegistrySvc is None:
            self._langRegistrySvc = components.classes['@activestate.com/koLanguageRegistryService;1'].\
                                        getService(components.interfaces.koILanguageRegistryService)
        return self._langRegistrySvc
    @property
    def langRegistrySvcUnwrapped(self):
        if self._langRegistrySvcUnwrapped is None:
            langRegSvc = self.langRegistrySvc
            self._langRegistrySvcUnwrapped = UnwrapObject(langRegSvc)
        return self._langRegistrySvcUnwrapped

    #######################################
    ##  Language detection from content  ##
    #######################################

    def _assertPossibleLanguagesAre(self, head, tail, expected):
        actual = self.langRegistrySvcUnwrapped.guessLanguageFromContents(head, tail)
        if actual != expected:
            errmsg = """guessed possible languages do not match expected results:
Expected: %s
Got:      %s
---------------- head of document --------------------------------
%s
---------------- tail of document --------------------------------
%s
------------------------------------------------------------------
""" % (expected, actual, head, tail)
            self.fail(errmsg)

    def _assertEmacsLocalVarsAre(self, head, tail, expected):
        actual = self.langRegistrySvcUnwrapped._getEmacsLocalVariables(head, tail)
        if actual != expected:
            errmsg = """Emacs-style local variable results are not as expected:
Expected: %s
Got:      %s
---------------- head of document --------------------------------
%s
---------------- tail of document --------------------------------
%s
------------------------------------------------------------------
""" % (expected, actual, head, tail)
            self.fail(errmsg)

    def test_perl_shebang(self):
        perlHeads = [
            "#!perl",
            "#!perl5 -w",
            "#!/bin/perl",
            "#! /bin/perl -dwh  ",
            "#!/bin/PeRl",
            "#!/bin/myperl",
        ]
        for head in perlHeads:
            self._assertPossibleLanguagesAre(head, "", ["Perl"])
        notPerlHeads = [
            "foo",
            "#!/bin/erl",
        ]
        for head in notPerlHeads:
            self._assertPossibleLanguagesAre(head, "", [])

    def test_python_shebang(self):
        pythonHeads = [
            "#!python",
            "#!python22 -w",
            "#!/bin/python",
            "#!/opt/Python-2.6.5/bin/python",
            "#! /bin/python -dwh  ",
            "#!/bin/PyThOn",
            "#!/usr/bin/env python",
            "#!/bin/mypython",
        ]
        for head in pythonHeads:
            self._assertPossibleLanguagesAre(head, "", ["Python"])
        notPythonHeads = [
            "foo",
            "#!/bin/ython",
        ]
        for head in notPythonHeads:
            self._assertPossibleLanguagesAre(head, "", [])

    def test_sh_shebang(self):
        heads = [
            "#!/bin/sh",
            "#!/bin/bash",
            "#!/usr/bin/bash",
        ]
        for head in heads:
            self._assertPossibleLanguagesAre(head, "", ["Bash"])

    def test_tcl_shebang(self):
        tclHeads = [
            "#!tclsh",
            "#!tclsh82",
            "#!/bin/tclsh",
            "#!/bin/expect",
            "#! /bin/wish -v  ",
            "#!/bin/TcLSh",
            "#!/bin/mytclsh",
        ]
        for head in tclHeads:
            self._assertPossibleLanguagesAre(head, "", ["Tcl"])
        notTclHeads = [
            "foo",
            "#!/bin/clsh",
        ]
        for head in notTclHeads:
            self._assertPossibleLanguagesAre(head, "", [])

    @tag("knownfailure", "bug 28775")
    def test_sh_to_tcl_exec(self):
        # File is executed as shell script, but then re-exec'd as a Tcl script.
        tclHeads = [
            """\
#!/bin/sh
# the next line restarts using tclsh \\
exec tclsh "$0" "$@"
""",
            """\
#!/bin/sh
# the next line restarts using tclsh \\
exec wish "$0" "$@"
""",
            """\
#!/bin/sh
# the next line restarts using tclsh \\
exec expect "$0" "$@"
""",
        ]
        for head in heads:
            self._assertPossibleLanguagesAre(head, "", ["Bash"])


    def test_emacs_local_variables(self):
        # Ensure the pref to use emacs-style local variables is on.
        globalPrefs = components.classes["@activestate.com/koPrefService;1"].\
                      getService(components.interfaces.koIPrefService).prefs
        emacsLocalModeVariableDetection = globalPrefs.getBooleanPref("emacsLocalModeVariableDetection")
        globalPrefs.setBooleanPref("emacsLocalModeVariableDetection", 1)

        headsAndTailsAndVarsAndLangs = [
            ("# -*- mode: Tcl -*-", "", {"mode": "Tcl"}, ["Tcl"]),
            ("# -*- Mode: Tcl -*-", "", {"mode": "Tcl"}, ["Tcl"]),
            ("# -*- mode: tcl -*-", "", {"mode": "tcl"}, ["Tcl"]),
            ("# *- mode: Tcl -*- blah blah", "", {}, []),
            ("", """\
# Using a prefix and suffix.
PREFIX Local Variables: SUFFIX
PREFIX mode: Tcl SUFFIX
PREFIX End: SUFFIX
""", {"mode": "Tcl"}, ["Tcl"]),
            ("", """\
Local Variables:
mode: Tcl
End:
""", {"mode": "Tcl"}, ["Tcl"]),
            ("", """\
# Using a realistic prefix.
# Local Variables:
# mode: Tcl
# End:
""", {"mode": "Tcl"}, ["Tcl"]),
            ("", """\
# Make sure the "End:" in a variable value does not screw up parsing.
PREFIX Local variables: SUFFIX
PREFIX foo: End: SUFFIX
PREFIX tab-width: 4 SUFFIX
PREFIX End: SUFFIX
""", {"foo": "End:", "tab-width": "4"}, []),
            ("", """\
# Must use proper prefix.
PREFIX Local Variables: SUFFIX
mode: Tcl SUFFIX
PREFIX End: SUFFIX
""", ValueError, []),
            ("", """\
# Must use proper suffix.
PREFIX Local Variables: SUFFIX
PREFIX mode: Tcl
PREFIX End: SUFFIX
""", ValueError, []),
            ("", """\
# Whitespace after the prefix and before the suffix is allowed.
# The suffix on the "End:" line is not checked.
PREFIX Local Variables: SUFFIX
PREFIX    mode: Tcl	SUFFIX
PREFIX End:
""", {"mode": "Tcl"}, ["Tcl"]),
            ("", """\
# In the Local Variables block variable names are NOT lowercase'd, therefore
# the user must specify the lowercase "mode" to properly set the mode.
PREFIX Local Variables: SUFFIX
PREFIX MoDe: tcl SUFFIX
PREFIX End: SUFFIX
""", {"MoDe": "tcl"}, []),
            ("# -*- Mode: perl -*-", """\
# The local variables block beats the one-liner.
Local Variables:
mode: Tcl
End:
""", {"mode": "Tcl"}, ["Tcl"]),
        ]
        for head, tail, vars, langs in headsAndTailsAndVarsAndLangs:
            if isinstance(vars, dict):
                self._assertEmacsLocalVarsAre(head, tail, vars)
            elif issubclass(vars, Exception):
                self.assertRaises(ValueError, self.langRegistrySvcUnwrapped._getEmacsLocalVariables,
                                  head, tail)
            else:
                raise "Unexpected test case 'vars' type: %s" % type(vars)
            self._assertPossibleLanguagesAre(head, tail, langs)

        # Restore the pref.
        globalPrefs.setBooleanPref("emacsLocalModeVariableDetection",
                                   emacsLocalModeVariableDetection)


    def test_bug28775(self):
        # The problem here was that if there was a blank line with an
        # LF line terminator (i.e. Unix EOLs) before the "Local Variables"
        # line, then the LF would get included in the "prefix" and
        # subsequent lines would look like they didn't have the proper
        # prefix.
        tail = """
# ;;; Local Variables: ***
# ;;; mode: tcl ***
# ;;; End: ***
"""
        self._assertEmacsLocalVarsAre("", tail, {"mode": "tcl"})


    ########################################
    ##  Language detection from filename  ##
    ########################################

    def _check_filepath_language(self, filepath, expected_lang):
        found_lang = self.langRegistrySvc.suggestLanguageForFile(filepath)
        self.assertEqual(found_lang, expected_lang,
                         "Incorrect language given for path %r, got %r, expected %r"
                         % (filepath, found_lang, expected_lang))


    def test_html_recognition(self):
        self._check_filepath_language("foo.html", "HTML")

    def test_django_recognition(self):
        self._check_filepath_language("foo.django.html", "Django")

    def test_django_recognition(self):
        self._check_filepath_language("foo.django.html", "Django")

    #def test_template_toolkit_recognition(self):
    #    self._check_filepath_language("ttk-test01.ttkt.html", "Template Toolkit")

    def test_erb_recognition(self):
        self._check_filepath_language("foo.html.erb", "RHTML")

    def test_scss_recognition(self):
        self._check_filepath_language("foo.css.scss", "SCSS")
