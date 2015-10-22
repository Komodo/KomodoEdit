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

"""JavaScript-specific Language Services implementations."""

import re

from xpcom import components, ServerException

from langinfo_prog import JavaScriptLangInfo, CoffeeScriptLangInfo
from koLanguageServiceBase import *

log = logging.getLogger('koJavaScriptLanguage')
#log.setLevel(logging.DEBUG)

class KoJavaScriptLexerLanguageService(KoLexerLanguageService):
    def __init__(self):
        KoLexerLanguageService.__init__(self)
        self.setLexer(components.interfaces.ISciMoz.SCLEX_CPP)
        self.supportsFolding = 1
        self.setProperty('lexer.cpp.allow.dollars', '1')
        self.setProperty('fold.cpp.syntax.based', '1')
        self.setKeywords(0, JavaScriptLangInfo.keywords)

class KoCoffeeScriptLexerLanguageService(KoLexerLanguageService):
    def __init__(self):
        KoLexerLanguageService.__init__(self)
        self.setLexer(components.interfaces.ISciMoz.SCLEX_COFFEESCRIPT)
        self.supportsFolding = 1
        self.setKeywords(0, CoffeeScriptLangInfo.keywords)

class koJSLikeLanguage(KoLanguageBase):
    variableIndicators = '$'
    def __init__(self):
        KoLanguageBase.__init__(self)
        self._style_info.update(
            _block_comment_styles = [sci_constants.SCE_C_COMMENT,
                                     sci_constants.SCE_C_COMMENTDOC,
                                     sci_constants.SCE_C_COMMENTDOCKEYWORD,
                                     sci_constants.SCE_C_COMMENTDOCKEYWORDERROR],
            _variable_styles = [components.interfaces.ISciMoz.SCE_C_IDENTIFIER]
            )
        self._setupIndentCheckSoftChar()
        self._fastCharData = \
            FastCharData(trigger_char=";",
                         style_list=(sci_constants.SCE_C_OPERATOR,
                                     sci_constants.SCE_UDL_CSL_OPERATOR,),
                         skippable_chars_by_style={ sci_constants.SCE_C_OPERATOR : "])",
                                    sci_constants.SCE_UDL_CSL_OPERATOR : "])",
                                    },
                         for_check=True)
        
    def getVariableStyles(self):
        return self._style_info._variable_styles


class koJavaScriptLanguage(koJSLikeLanguage, KoLanguageBaseDedentMixin):
    name = "JavaScript"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{0DD83914-E2F6-478a-A77E-7307833A7601}"
    _reg_categories_ = [("komodo-language", name)]

    shebangPatterns = [
        re.compile(r'\A#!.*(javascript).*$', re.I | re.M),
    ]

    accessKey = 'j'
    primary = 1
    defaultExtension = ".js"
    commentDelimiterInfo = {
        "line": [ "//" ],
        "block": [ ("/*", "*/") ],
        "markup": "*",
    }
    _dedenting_statements = [u'throw', u'return', u'break', u'continue']
    searchURL = "https://developer.mozilla.org/en/JavaScript/Reference"
    
    # matches:
    # function name
    # name: function
    # name = function
    # class.prototype.name = function
    namedBlockDescription = 'JavaScript functions and classes'
    namedBlockRE = r'^[ |\t]*?(?:([\w|\.|_]*?)\s*=\s*function|function\s*([\w|\_]*?)|([\w|\_]*?)\s*:\s*function).*?$'
    supportsSmartIndent = "brace"
    sample = """function chkrange(elem,minval,maxval) {
    // Comment
    if (elem.value < minval - 1 ||
        elem.value > maxval + 1) {
          alert("Value of " + elem.name + " is out of range!");
    }
}
"""

    styleStdin = components.interfaces.ISciMoz.SCE_C_STDIN
    styleStdout = components.interfaces.ISciMoz.SCE_C_STDOUT
    styleStderr = components.interfaces.ISciMoz.SCE_C_STDERR

    def __init__(self):
        koJSLikeLanguage.__init__(self)
        KoLanguageBaseDedentMixin.__init__(self)
    
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoJavaScriptLexerLanguageService()
        return self._lexer

class koJSONLanguage(koJavaScriptLanguage):
    name = "JSON"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{879fa591-80f4-4f6c-b571-a7999d97a8cd}"
    _reg_categories_ = [("komodo-language", name)]

    shebangPatterns = [
        re.compile(r'\A#!.*json.*$', re.I | re.M),
    ]

    accessKey = 'n'
    primary = 1
    defaultExtension = ".json"

    sample = """{
    "glossary": {
        "title": "example glossary",
        "GlossDiv": {
           "example": "foo"
        }
    }
}
"""

class koNodeJSLanguage(koJavaScriptLanguage):
    name = "Node.js"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{21a9b248-4fc3-4264-9bb8-2e9b0bb5f436}"
    _reg_categories_ = [("komodo-language", name)]

    shebangPatterns = [
        re.compile(r'\A#!.*node\b$', re.I | re.M),
    ]

    accessKey = 'n'
    primary = 1
    defaultExtension = ".js"
    searchURL = "http://nodejs.org/docs/latest/api/index.html"

    sample = """
var fs = require('fs');
var events = require('events');
var dns = require('dns');

input.on('data', function(data) {
     self._normalWrite(data);
   });
"""

class koCoffeeScriptLanguage(koJSLikeLanguage):
    name = "CoffeeScript"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{7a0ab511-bcc9-416e-95e6-db29694226e9}"
    _reg_categories_ = [("komodo-language", name)]

    shebangPatterns = [
        re.compile(r'\A#!.*(coffee).*$', re.I | re.M),
    ]

    accessKey = 'C'
    primary = 1
    defaultExtension = ".coffee"
    commentDelimiterInfo = {
        "line": [ "#" ],
        "block": [ ("/*", "*/") ],
        "markup": "*",
    }
    _indent_open_chars = "{[(:"
    _indenting_keywords = [u'if', u'while', u'else', u'for', u'try', u'catch',
                           u'catch', u'finally', u'switch', u'when']
    _dedenting_statements = [u'throw', u'return', u'break', u'continue']
    _indenting_statements = [u'case']
    searchURL = "http://coffeescript.org/#language"
    
    # matches:
    # function name
    # name: function
    # name = function
    # class.prototype.name = function
    namedBlockDescription = 'CoffeeScript functions and classes'
    namedBlockRE = r'^[ |\t]*?(?:([\w|\.|_]*?)\s*[=:]\s*\(.*\)\s*=>).*?$'
    supportsSmartIndent = "python"
    sample = \
"""chkrange = (elem, minval, maxval) =>
# Comment
if elem.value < minval - 1 || elem.value > maxval + 1
    alert("Prob:" + elem.name + " is out of range!")
chkrange {name:'five', value:5}, 7, 12
@valid = false
"""

    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoCoffeeScriptLexerLanguageService()
        return self._lexer
    
    expnRE = re.compile(r"\s*(\w+).+?\bif\b(.*)");
    thenRE = re.compile(r"\bthen\b")
    ifRE = re.compile(r"\bif\b")
    def finishProcessingDedentingStatement(self, scimoz, pos, curLine):
        """ This is similar to the code in koLanguageServiceBase.py,
            but doesn't trigger an indent in the following cases:
            [dedenter] if ... <no then>
            """
        expnMatch = self.expnRE.match(curLine)
        if not expnMatch:
            return koJSLikeLanguage.finishProcessingDedentingStatement(self, scimoz, pos, curLine)
        kwd = expnMatch.group(1)
        val = expnMatch.group(2)
        if self.ifRE.search(val):
            # Found <kwd> ... if ... if
            #log.debug("Expression is too complex, don't dedent")
            return None
        if self.thenRE.search(val):
            #log.debug("Got if ... then here, assume <kwd> ... if test val then val")
            return koJSLikeLanguage.finishProcessingDedentingStatement(self, scimoz, pos, curLine)
        #log.debug("Found %s if ... no then here, no dedent", kwd)
        return None
    
    _initial_word_re = re.compile("\s*(\w+)")
    def _shouldIndent(self, scimoz, pos, style_info):
        """ Override KoLanguageBase._shouldIndent to handle -> at EOL
        See comments in koLanguageServiceBase.py
        """
        curLineNo = scimoz.lineFromPosition(pos)
        lineStart = scimoz.positionFromLine(curLineNo)
        data = scimoz.getStyledText(lineStart, pos+1)
        for p in range(pos-1, lineStart-1, -1):
            char = data[(p-lineStart)*2]
            style = ord(data[(p-lineStart)*2+1])
            if style in style_info._comment_styles:
                continue
            elif char in ' \t':
                continue
            elif (char == ">" and style in style_info._indent_open_styles):
                if (p >= lineStart + 1
                    and ord(data[(p - lineStart - 1) * 2 + 1]) == style
                    and data[(p - lineStart - 1) * 2] in "-="):
                    # => and -> both denote functions, => rebinds 'this'
                    return self._findIndentationBasedOnStartOfLogicalStatement(scimoz, pos, style_info, curLineNo)
            elif (char == '=' and style in style_info._indent_open_styles):
                # Only indent on '=' if it occurs at the end of a code line.
                # Retrieve all text beyond '=' and verify it does not have any
                # non-whitespace, non-comment character.
                # Note: For lines like "x = [[...]", the open '[' is recognized
                # first, and the code below is never reached.
                equalsAtEnd = True
                lineEnd = scimoz.getLineEndPosition(curLineNo)
                dataEnd = scimoz.getStyledText(p + 1, lineEnd)
                for p2 in range(0, lineEnd-p-1):
                    nextChar = dataEnd[p2*2]
                    nextStyle = ord(dataEnd[p2*2+1])
                    if nextStyle in style_info._comment_styles:
                        break # equalsAtEnd remains True since a comment ends the line
                    if not nextChar in ' \t':
                        equalsAtEnd = False
                        break
                if equalsAtEnd:
                    return self._findIndentationBasedOnStartOfLogicalStatement(scimoz, pos, style_info, curLineNo)
            eol_pos = p + 1
            break

        # Now look to see if the line ends with a standard indenting
        # character.  This is easier to look for than matching keywords
        # at the start of the line.
        if p > lineStart + 1:
            # Continue looking using the base class method,
            # but don't look at the characters in [p .. pos)
            indentString =  KoLanguageBase._shouldIndent(self, scimoz, eol_pos, style_info)
            if indentString:
                return indentString
                           
        # Now look at the start of the line for a keyword
        # Since coffeescript is so punctuation-adverse, a line that
        # starts with 'return', 'if', etc. will be indented on the next line

        lineString = data[0::2]
        m = self._initial_word_re.match(lineString)
        if m and m.group(1) in self._indenting_keywords:
            return self._findIndentationBasedOnStartOfLogicalStatement(scimoz, eol_pos, style_info, curLineNo)
        return None
