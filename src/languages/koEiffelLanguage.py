from xpcom import components, ServerException

from koLanguageServiceBase import *

def registerLanguage(registery):
    registery.registerLanguage(koEiffelLanguage())

class koEiffelLanguage(KoLanguageBase):
    name = "Eiffel"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{A2EBF794-8C0B-4b51-8F5C-147F97399C43}"

    defaultExtension = ".e"
    commentDelimiterInfo = {
        "line": [ "--" ],
    }
    supportsSmartIndent = "brace"
    
    def __init__(self):
        KoLanguageBase.__init__(self)
        del self.matchingSoftChars["'"]
        
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(components.interfaces.ISciMoz.SCLEX_EIFFELKW)
            self._lexer.setKeywords(0, self._keywords)
            self._lexer.supportsFolding = 1
        return self._lexer

    _keywords = ["all", "as", "class", "create", "creation", "deferred", "do", "else", "elseif",
                 "end", "ensure", "expanded", "export", "false", "feature", "from", "frozen",
                 "if", "infix", "inherit", "inspect", "interface", "invariant", "is", "local", "loop", "old",
                 "prefix", "redefine", "rename", "require", "rescue", "retry", "select", "then", "true",
                 "unique", "undefine", "until", "variant", "when"]
