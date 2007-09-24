from xpcom import components, ServerException

from koLanguageServiceBase import *

def registerLanguage(registery):
    registery.registerLanguage(koRegexLanguage())
    
class koRegexLanguage(KoLanguageBase):
    name = "Regex"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" % name
    _reg_clsid_ = "{806CA851-3B1A-4112-9601-DCBF72895B31}"

    styleBits = 5
    internal = 1
    
    def __init__(self):
        KoLanguageBase.__init__(self)

        # Softchars in Rx really get in the way.
        self.matchingSoftChars = {}
    
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(components.interfaces.ISciMoz.SCLEX_NULL)
            self._lexer.supportsFolding = 0
        return self._lexer
