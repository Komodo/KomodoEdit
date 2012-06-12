#!python
# Copyright (c) 2001-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

"""HLSL-specific Language Services implementations."""

from xpcom import components, ServerException

from koLanguageServiceBase import KoLanguageBase, sci_constants, KoLexerLanguageService
from langinfo_prog import HLSLLangInfo


class koHLSLLanguage(KoLanguageBase):
    name = "HLSL"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{fd0846b3-ff7f-41af-b324-179783084469}"
    _reg_categories_ = [("komodo-language", name)]

    primary = 0
    defaultExtension = ".hlsl"
    commentDelimiterInfo = {
        "line": [ "//" ],
        "block": [ ("/*", "*/") ],
        "markup": "*",
    }
    _dedenting_statements = [u'throw', u'return', u'break', u'continue']
    _indenting_statements = [u'case']
    searchURL = "http://www.google.com/search?q=hlsl+site%3Amicrosoft.com%2F+%W"
    # matches:
    # function name
    # name: function
    # name = function
    # class.prototype.name = function
    namedBlockDescription = 'HLSL functions and classes'
    namedBlockRE = r'^[ |\t]*?(?:([\w|\.|_]*?)\s*=\s*function|function\s*([\w|\_]*?)|([\w|\_]*?)\s*:\s*function).*?$'
    supportsSmartIndent = "brace"
    sample = """
     float4 normal = mul(IN.Normal, ModelViewIT);
     normal.w = 0.0;
     normal = normalize(normal);
     float4 light = normalize(LightVec);
     float4 eye = float4(1.0, 1.0, 1.0, 0.0);
     float4 vhalf = normalize(light + eye);
"""
    styleStdin = sci_constants.SCE_C_STDIN
    styleStdout = sci_constants.SCE_C_STDOUT
    styleStderr = sci_constants.SCE_C_STDERR

    def __init__(self):
        # Same as JavaScript's
        KoLanguageBase.__init__(self)
        self._style_info.update(
            _block_comment_styles = [sci_constants.SCE_C_COMMENT,
                                     sci_constants.SCE_C_COMMENTDOC,
                                     sci_constants.SCE_C_COMMENTDOCKEYWORD,
                                     sci_constants.SCE_C_COMMENTDOCKEYWORDERROR],
            _variable_styles = [sci_constants.SCE_C_IDENTIFIER]
            )
        self._setupIndentCheckSoftChar()
        
    def getVariableStyles(self):
        # Same as JavaScript's
        return self._style_info._variable_styles
    
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(sci_constants.SCLEX_CPP)
            self._lexer.setKeywords(0, HLSLLangInfo.keywords)
            self._lexer.setProperty('fold.cpp.syntax.based', '1')
            self._lexer.supportsFolding = 1
        return self._lexer
