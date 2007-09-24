from xpcom import components, ServerException

from koLanguageServiceBase import *

def registerLanguage(registery):
    registery.registerLanguage(KoErrorLanguage())

class KoErrorLanguage(KoLanguageBase):
    name = "Errors"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{A0E26D4B-42E2-408F-BEE4-DF3232A08636}"

    internal = True
    styleBits = 5
    
    styleStdout = components.interfaces.ISciMoz.SCE_ERR_DEFAULT
    styleStdin = components.interfaces.ISciMoz.SCE_ERR_DEFAULT
    # Error language has lots of error levels for different languages, Komodo only
    # uses one for the terminal, which is where we use the error language lexer
    styleStderr = components.interfaces.ISciMoz.SCE_ERR_PYTHON

    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(components.interfaces.ISciMoz.SCLEX_ERRORLIST)
            self._lexer.supportsFolding = 0
        return self._lexer

