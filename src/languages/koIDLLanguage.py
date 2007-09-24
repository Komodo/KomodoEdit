from xpcom import components, ServerException

from koLanguageServiceBase import *

def registerLanguage(registery):
    registery.registerLanguage(koIDLLanguage())

class koIDLLanguage(KoLanguageBase):
    name = "IDL"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{E9A451B7-E13D-4d71-883C-93BD457A3D9F}"

    accessKey = 'i'
    defaultExtension = ".idl"
    commentDelimiterInfo = {
        "line": [ "//" ],
        "block": [ ("/*", "*/") ],
        "markup": "*",
    }
    supportsSmartIndent = "brace"

    def __init__(self):
        KoLanguageBase.__init__(self)
        self._style_info.update(
            _block_comment_styles = [sci_constants.SCE_C_COMMENT,
                                     sci_constants.SCE_C_COMMENTDOC,
                                     sci_constants.SCE_C_COMMENTDOCKEYWORD,
                                     sci_constants.SCE_C_COMMENTDOCKEYWORDERROR]
            )

    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(components.interfaces.ISciMoz.SCLEX_CPP)
            self._lexer.setKeywords(0, self._keywords)
            self._lexer.supportsFolding = 1
        return self._lexer

    _keywords = [
                       # keywords appearing outside of brackets
                       "attribute", "boolean", "char", "const", "double", "float", "in", "inout",
                       "int", "interface", "long", "native", "octet", "out", "readonly", "string",
                       "unsigned", "void", "wchar", "wstring", "fixed",
                       # keywords appearing inside brackets
                       "array", "nsid", "ptr", "ref", "retval", "scriptable", "shared",
                       "iid_is", "notxpcom", "noscript", "uuid"]

