from xpcom import components, ServerException

from koLanguageServiceBase import *

def registerLanguage(registery):
    registery.registerLanguage(koMakefileLanguage())
    
class koMakefileLanguage(KoLanguageBase):
    name = "Makefile"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{C9FEB44E-AEEF-490b-8E63-2551B19DF2DF}"

    defaultExtension = ".mak"
    commentDelimiterInfo = {
        "line": [ "#" ],
    }
    
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(components.interfaces.ISciMoz.SCLEX_MAKEFILE)
        return self._lexer


