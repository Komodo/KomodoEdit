#!python
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

"""Python-specific Language Services implementations."""

import os
import sys, re
import keyword
import cStringIO, StringIO  # cStringIO doesn't work well with unicode strings! 
import pprint
import tokenize
import token

import logging
from xpcom import components, ServerException
from koLanguageServiceBase import *
import sciutils


def registerLanguage(registery):
    registery.registerLanguage(KoPythonLanguage())
    registery.registerLanguage(KoPython3Language())
    

#---- globals

log = logging.getLogger("koPythonLanguage")
#log.setLevel(logging.DEBUG)

#---- internal support routines

def classifyws(s, tabwidth):
    # taken from IDLE
    # Look at the leading whitespace in s.
    # Return pair (# of leading ws characters,
    #              effective # of leading blanks after expanding
    #              tabs to width tabwidth)
    foundTabs = 0
    raw = effective = 0
    for ch in s:
        if ch == ' ':
            raw = raw + 1
            effective = effective + 1
        elif ch == '\t':
            foundTabs = 1
            raw = raw + 1
            effective = (effective / tabwidth + 1) * tabwidth
        else:
            break
    return raw, effective, foundTabs

def isident(char):
    return "a" <= char <= "z" or "A" <= char <= "Z" or char == "_"

def isdigit(char):
    return "0" <= char <= "9"

def getLastLogicalLine(text):
    lines = text.splitlines(0) or ['']
    logicalline = lines.pop()
    while lines and lines[-1].endswith('\\'):
        logicalline = lines.pop()[:-1] + ' ' + logicalline
    return logicalline


#---- Language Service component implementations

class KoPythonCommonLexerLanguageService(KoLexerLanguageService):
    
    def __init__(self):
        KoLexerLanguageService.__init__(self)
        self.setLexer(components.interfaces.ISciMoz.SCLEX_PYTHON)
        self.setProperty('tab.timmy.whinge.level', '1') # XXX make a user-accesible pref
        # read lexPython.cxx to understand the meaning of the levels.
        self.supportsFolding = 1

class KoPythonLexerLanguageService(KoPythonCommonLexerLanguageService):
    def __init__(self):
        KoPythonCommonLexerLanguageService.__init__(self)
        kwlist = set(keyword.kwlist)
        kwlist.update(['None', 'as', 'with', 'True', 'False'])
        self.setKeywords(0, list(kwlist))
    
class KoPython3LexerLanguageService(KoPythonCommonLexerLanguageService):
    def __init__(self):
        KoPythonCommonLexerLanguageService.__init__(self)
        kwlist = set(['False', 'None', 'True', 'and', 'as', 'assert', 'break',
                      'class', 'continue', 'def', 'del', 'elif', 'else',
                      'except', 'finally', 'for', 'from', 'global', 'if',
                      'import', 'in', 'is', 'lambda', 'nonlocal', 'not', 'or',
                    'pass', 'raise', 'return', 'try', 'while', 'with', 'yield']
                     )
        self.setKeywords(0, list(kwlist))

class KoPythonCommonLanguage(KoLanguageBase):
    accessKey = 'y'
    primary = 1
    namedBlockRE = "^[ \t]*?(def\s+[^\(]+\([^\)]*?\):|class\s+[^:]*?:)"
    namedBlockDescription = 'Python functions and classes'
    defaultExtension = ".py"
    # XXX read url from some config file
    downloadURL = 'http://www.activestate.com/activepython'
    commentDelimiterInfo = { "line": [ "#" ]  }
    _indent_open_chars = ':{[('
    _lineup_open_chars = "([{" 
    _lineup_close_chars = ")]}"
    _dedenting_statements = [u'raise', u'return', u'pass', u'break', u'continue']
    supportsSmartIndent = "python"
    sample = """import math
class Class:
    \"\"\" this is a docstring \"\"\"
    def __init__(self, arg): # one line comment
        self.x = arg + math.cos(arg + arg)
        s = 'a string'
"""

    styleStdin = sci_constants.SCE_P_STDIN
    styleStdout = sci_constants.SCE_P_STDOUT
    styleStderr = sci_constants.SCE_P_STDERR

    def __init__(self):
        KoLanguageBase.__init__(self)
        # Classes that want to define their own variable styles need to
        # let the base class initialize the style info first, and then
        # fill in the details this way.
        self._style_info._variable_styles = [sci_constants.SCE_P_IDENTIFIER]
        self.matchingSoftChars["`"] = ("`", self.softchar_accept_matching_backquote)

    def getVariableStyles(self):
        return self._style_info._variable_styles

    def get_interpreter(self):
        if self._interpreter is None:
            self._interpreter =\
                components.classes["@activestate.com/koAppInfoEx?app=%s;1"
                                   % self.name]\
                .getService(components.interfaces.koIAppInfoEx)
        return self._interpreter

    def test_scimoz(self, scimoz):
        CommenterTestCase.lang = self
        testCases = [
            CommenterTestCase,
        ]
        sciutils.runSciMozTests(testCases, scimoz)

class KoPythonLanguage(KoPythonCommonLanguage):
    name = "Python"
    _reg_desc_ = "%s Language" % (name)
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{D90FF5C7-1FD4-4535-A0D2-47B5BDC3E7FE}"

    shebangPatterns = [
        re.compile(ur'\A#!.*python(?!3).*$', re.IGNORECASE | re.MULTILINE),
    ]

    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoPythonLexerLanguageService()
        return self._lexer

class KoPython3Language(KoPythonCommonLanguage):
    name = "Python3"
    _reg_desc_ = "%s Language" % (name)
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{db8d60b3-f104-4622-b4d5-3324787d5149}"

    shebangPatterns = [
        re.compile(ur'\A#!.*python3.*$', re.IGNORECASE | re.MULTILINE),
    ]

    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoPython3LexerLanguageService()
        return self._lexer


#---- test suites
#
# Run via "Test | SciMoz Tests" in a Komodo dev build.
#

class CommenterTestCase(sciutils.SciMozTestCase):
    """Test Python auto-(un)commenting."""
    # Set in test_scimoz() driver to the koPythonLanguage instance.
    lang = None

    def test_simple(self):
        self.assertAutocommentResultsIn(self.lang,
            "foo<|>bar",
            "#foo<|>bar")
        self.assertAutouncommentResultsIn(self.lang,
            "#foo<|>bar",
            "foo<|>bar")

    def test_non_ascii_issues(self):
        self.assertAutocommentResultsIn(self.lang,
            u"foo \xe9 bar<|>",
            u"#foo \xe9 bar<|>")
        self.assertAutouncommentResultsIn(self.lang,
            u"#foo \xe9 bar<|>",
            u"foo \xe9 bar<|>")


