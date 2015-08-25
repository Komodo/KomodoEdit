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



#---- globals

log = logging.getLogger("koPythonLanguage")
#log.setLevel(logging.DEBUG)


#---- Language Service component implementations

class KoPythonCommonLexerLanguageService(KoLexerLanguageService):
    
    def __init__(self):
        KoLexerLanguageService.__init__(self)
        self.setLexer(components.interfaces.ISciMoz.SCLEX_PYTHON)
        self.setProperty('tab.timmy.whinge.level', '1') # XXX make a user-accesible pref
        self.setProperty('lexer.python.keywords2.no.sub.identifiers', '1')
        self.setProperty('fold.quotes.python', '1')
        # read lexPython.cxx to understand the meaning of the levels.
        self.supportsFolding = 1

class KoPythonLexerLanguageService(KoPythonCommonLexerLanguageService):
    def __init__(self):
        KoPythonCommonLexerLanguageService.__init__(self)
        kwlist = set(keyword.kwlist)
        kwlist2 = set(['False', 'None', 'True', 'as', 'self',
                       ## built-in functions
                       'abs', 'all', 'any', 'apply', 'basestring', 'bin',
                       'bool', 'buffer', 'bytearray', 'bytes', 'callable',
                       'chr', 'classmethod', 'cmp', 'coerce', 'compile',
                       'complex', 'copyright', 'credits', 'delattr', 'dict',
                       'dir', 'divmod', 'enumerate', 'eval', 'execfile', 'exit',
                       'file', 'filter', 'float', 'format', 'frozenset',
                       'getattr', 'globals', 'hasattr', 'hash', 'help', 'hex',
                       'id', 'input', 'int', 'intern', 'isinstance',
                       'issubclass', 'iter', 'len', 'license', 'list', 'locals',
                       'long', 'map', 'max', 'memoryview', 'min', 'next',
                       'object', 'oct', 'open', 'ord', 'pow', 'print',
                       'property', 'quit', 'range', 'raw_input', 'reduce',
                       'reload', 'repr', 'reversed', 'round', 'set', 'setattr',
                       'slice', 'sorted', 'staticmethod', 'str', 'sum', 'super',
                       'tuple', 'type', 'unichr', 'unicode', 'vars', 'xrange',
                       'zip', '__import__']
                    )
        self.setKeywords(0, list(kwlist))
        self.setKeywords(1, list(kwlist2))

class KoPython3LexerLanguageService(KoPythonCommonLexerLanguageService):
    def __init__(self):
        KoPythonCommonLexerLanguageService.__init__(self)
        kwlist = set(['and', 'as', 'assert', 'break',
                      'class', 'continue', 'def', 'del', 'elif', 'else',
                      'except', 'finally', 'for', 'from', 'global', 'if',
                      'import', 'in', 'is', 'lambda', 'nonlocal', 'not', 'or',
                      'pass', 'raise', 'return', 'try', 'while', 'with', 'yield',
                      # New in 3.5
                      'async', 'await']
                     )
        kwlist2 = set(['False', 'None', 'True', 'self',
                       ## built-in functions
                       'abs', 'all', 'any', 'ascii', 'bin', 'bool', 'bytearray',
                       'bytes', 'callable', 'chr', 'classmethod', 'compile',
                       'complex', 'delattr', 'dict', 'dir', 'divmod',
                       'enumerate', 'eval', 'exec', 'exit', 'filter', 'float',
                       'format', 'frozenset', 'getattr', 'globals', 'hasattr',
                       'hash', 'help', 'hex', 'id', 'input', 'int',
                       'isinstance', 'issubclass', 'iter', 'len', 'list',
                       'locals', 'map', 'max', 'memoryview', 'min', 'next',
                       'object', 'oct', 'open', 'ord', 'pow', 'print',
                       'property', 'quit', 'range', 'repr', 'reversed', 'round',
                       'set', 'setattr', 'slice', 'sorted', 'staticmethod',
                       'str', 'sum', 'super', 'tuple', 'type', 'vars', 'zip',
                       '__import__'] )
        self.setKeywords(0, list(kwlist))
        self.setKeywords(1, list(kwlist2))


class KoPythonCommonLanguage(KoLanguageBase):
    namedBlockRE = "^[ \t]*?(def\s+[^\(]+\([^\)]*?\):|class\s+[^:]*?:)"
    namedBlockDescription = 'Python functions and classes'
    # XXX read url from some config file
    downloadURL = 'http://www.activestate.com/activepython'
    commentDelimiterInfo = { "line": [ "# ", "#" ]  }
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
        self._fastCharData = \
            FastCharData(trigger_char=";",
                         style_list=(sci_constants.SCE_P_OPERATOR,
                                     sci_constants.SCE_UDL_SSL_OPERATOR,),
                         skippable_chars_by_style={ sci_constants.SCE_P_OPERATOR : "])",
                                                    sci_constants.SCE_UDL_SSL_OPERATOR : "])",})

    def getVariableStyles(self):
        return self._style_info._variable_styles

    def get_interpreter(self):
        if self._interpreter is None:
            self._interpreter =\
                components.classes["@activestate.com/koAppInfoEx?app=%s;1"
                                   % self.name]\
                .getService(components.interfaces.koIAppInfoEx)
        return self._interpreter

    def _keyPressed(self, ch, scimoz, style_info):
	res = self._handledKeyPressed(ch, scimoz, style_info)
	if not res:
	    KoLanguageBase._keyPressed(self, ch, scimoz, style_info)

    _slidingKeywords = ('else', 'elif', 'except', 'finally')
    _firstWordRE = re.compile(r'(\s+)(\w+)')
    def _handledKeyPressed(self, ch, scimoz, style_info):
	"""
	If the user types an operator ":" at the end of the line,
	and the line starts with one of
    	    else elif except finally
	and it has the same indent as the previous non-empty line,
	dedent it.	
	"""
	if ch != ":" or not self._dedentOnColon:
	    return False
	pos = scimoz.positionBefore(scimoz.currentPos)
        style = scimoz.getStyleAt(pos)
	ch_pos = scimoz.getWCharAt(pos)
        if style not in style_info._indent_open_styles:
	    return False
	lineNo = scimoz.lineFromPosition(pos)
	if lineNo == 0:
	    #log.debug("no point working on first line")
	    return False
	thisLinesIndent = scimoz.getLineIndentation(lineNo)
	prevLinesIndent = scimoz.getLineIndentation(lineNo - 1)
	if thisLinesIndent < prevLinesIndent:
	    #log.debug("current line %d is already dedented", lineNo)
	    return False
        lineStartPos = scimoz.positionFromLine(lineNo)
	if scimoz.getStyleAt(lineStartPos) != components.interfaces.ISciMoz.SCE_P_DEFAULT:
	    #log.debug("line %d doesn't start with a whitespace char", lineNo)
	    return False
        lineEndPos = scimoz.getLineEndPosition(lineNo)
	if lineEndPos <= lineStartPos + 1:
	    #log.debug("line %d too short", lineNo)
	    return False
	text = scimoz.getTextRange(lineStartPos, lineEndPos)
	m = self._firstWordRE.match(text)
	if not m or m.group(2) not in self._slidingKeywords:
	    return False
	leadingWS = m.group(1)
	tabFreeLeadingWS = leadingWS.expandtabs(scimoz.tabWidth)
	currWidth = len(tabFreeLeadingWS)
	targetWidth = currWidth - scimoz.indent
	if targetWidth < 0:
	    fixedLeadingWS = ""
	else:
	    fixedLeadingWS = scimozindent.makeIndentFromWidth(scimoz, targetWidth)
	scimoz.targetStart = lineStartPos
	scimoz.targetEnd = lineStartPos + len(leadingWS)
	scimoz.replaceTarget(len(fixedLeadingWS), fixedLeadingWS)
	return True

    def _atOpeningStringDelimiter(self, scimoz, pos, style_info):
        #Walk backwards looking for three quotes, an optional
        #leading r or u, and an opener.
        # If we only have one quote, it's a single-line string.
        if pos < 6:
            return False
        # Look for a delim after the q-part
        prevPos = scimoz.positionBefore(pos)
        prevStyle = scimoz.getStyleAt(prevPos)
        if prevStyle not in style_info._string_styles:
            return False
        quoteChar = scimoz.getWCharAt(prevPos)
        if quoteChar not in "\'\"":
            return False

        # Allow for two more quoteChars before
        for i in range(2):
            prevPos = scimoz.positionBefore(prevPos)
            prevStyle = scimoz.getStyleAt(prevPos)
            if prevStyle not in style_info._string_styles:
                return False
            prevChar = scimoz.getWCharAt(prevPos)
            if prevChar != quoteChar:
                return False
            
        prevPos = scimoz.positionBefore(prevPos)
        prevStyle = scimoz.getStyleAt(prevPos)
        # Look for an 'r' or 'u' before three quotes
        if prevStyle in style_info._string_styles:
            prevChar = scimoz.getWCharAt(prevPos)
            if prevChar not in "ru":
                return False
            prevPos = scimoz.positionBefore(prevPos)
            
        return self._atOpeningIndenter(scimoz, prevPos, style_info)
        
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
    _reg_categories_ = [("komodo-language", name)]

    accessKey = 'y'
    primary = 1
    defaultExtension = ".py"
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
    _reg_categories_ = [("komodo-language", name)]

    accessKey = '3'
    primary = 1
    defaultExtension = ".py"
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


