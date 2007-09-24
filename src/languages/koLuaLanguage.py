from xpcom import components, ServerException

from koLanguageServiceBase import *

def registerLanguage(registery):
    registery.registerLanguage(koLuaLanguage())
    
class koLuaLanguage(KoLanguageBase):
    name = "Lua"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{D3C94E8B-B75C-4fa4-BC4D-986F68ACD33C}"

    defaultExtension = ".lua"
    commentDelimiterInfo = {
        "line": [ "--" ],
        "block": [ ("--[[", "]]") ],
    }

    def __init__(self):
        KoLanguageBase.__init__(self)
        self._style_info.update(
            _block_comment_styles = [sci_constants.SCE_LUA_COMMENT,
                                     sci_constants.SCE_LUA_COMMENTDOC]
            )

    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(components.interfaces.ISciMoz.SCLEX_LUA)
            self._lexer.setKeywords(0, self._keywords)
        return self._lexer


    _keywords = ["and", "do", "else", "elseif", "end", "function",
                 "if", "local", "nil", "not", "or", "repeat", "return", "then",
                 "until", "while"]  

