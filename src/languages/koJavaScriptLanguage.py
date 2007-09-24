#!python
# Copyright (c) 2001-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

"""JavaScript-specific Language Services implementations."""

from xpcom import components, ServerException

from codeintel2 import lang_javascript
from koLanguageServiceBase import *


def registerLanguage(registery):
    registery.registerLanguage(koJavaScriptLanguage())

class koJavaScriptLanguage(KoLanguageBase):
    name = "JavaScript"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{0DD83914-E2F6-478a-A77E-7307833A7601}"

    accessKey = 'j'
    primary = 1
    defaultExtension = ".js"
    commentDelimiterInfo = {
        "line": [ "//" ],
        "block": [ ("/*", "*/") ],
        "markup": "*",
    }
    _dedenting_statements = [u'throw', u'return', u'break', u'continue']
    _indenting_statements = [u'case']
    searchURL = "http://www.google.com/search?q=site%3Ahttp%3A%2F%2Fdeveloper.mozilla.org%2Fen%2Fdocs%2FCore_JavaScript_1.5_Reference+%W"
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
        KoLanguageBase.__init__(self)
        self._style_info.update(
            _block_comment_styles = [sci_constants.SCE_C_COMMENT,
                                     sci_constants.SCE_C_COMMENTDOC,
                                     sci_constants.SCE_C_COMMENTDOCKEYWORD,
                                     sci_constants.SCE_C_COMMENTDOCKEYWORDERROR],
            _variable_styles = [components.interfaces.ISciMoz.SCE_C_IDENTIFIER]
            )
        
    def getVariableStyles(self):
        return self._style_info._variable_styles
    
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(components.interfaces.ISciMoz.SCLEX_CPP)
            self._lexer.setKeywords(0, lang_javascript.keywords)
            self._lexer.supportsFolding = 1
        return self._lexer

