from xpcom import components, ServerException

from koLanguageServiceBase import *

def registerLanguage(registery):
    registery.registerLanguage(koLatexLanguage())
 
class koLatexLanguage(KoLanguageBase):
    name = "LaTeX"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{124b728e-6c0c-4800-ba75-33be4fe8729c}"

    defaultExtension = ".tex"
    commentDelimiterInfo = {
        "line": [ "%" ],
    }
    
    def __init__(self):
        KoLanguageBase.__init__(self)
        del self.matchingSoftChars["'"]
        del self.matchingSoftChars['"']
    
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(components.interfaces.ISciMoz.SCLEX_LATEX)
        return self._lexer