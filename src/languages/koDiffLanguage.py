from xpcom import components, ServerException

from koLanguageServiceBase import *

def registerLanguage(registery):
    registery.registerLanguage(koDiffLanguage())
    
class koDiffLanguage(KoLanguageBase):
    name = "Diff"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{d255390c-84b8-4071-8a8b-acda4e748146}"

    defaultExtension = ".diff"
    
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(components.interfaces.ISciMoz.SCLEX_DIFF)
            self._lexer.supportsFolding = 1
        return self._lexer


