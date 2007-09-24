from xpcom import components, ServerException

from koLanguageServiceBase import *

def registerLanguage(registery):
    registery.registerLanguage(koHaskellLanguage())

# see http://haskell.org/
class koHaskellLanguage(KoLanguageBase):
    name = "Haskell"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{2545AA9A-53EB-11DA-BF7A-000D935D3368}"

    commentDelimiterInfo = {
        "line": [ "--" ]
    }

    defaultExtension = ".hs" 

    supportsSmartIndent = "brace"
    sciMozLexer = components.interfaces.ISciMoz.SCLEX_HASKELL

    _stateMap = {
        'default': ('SCE_HA_DEFAULT',),
        'keywords': ('SCE_HA_KEYWORD',),
        'identifiers': ('SCE_HA_IDENTIFIER',),
        'comments': ('SCE_HA_COMMENTLINE','SCE_HA_COMMENTBLOCK',
                     'SCE_HA_COMMENTBLOCK2', 'SCE_HA_COMMENTBLOCK3',),
        'operators': ('SCE_HA_OPERATOR',),
        'numbers': ('SCE_HA_NUMBER',),
        'strings': ('SCE_HA_STRING', 'SCE_HA_CHARACTER',),
        'class': ('SCE_HA_CLASS',),
        'module': ('SCE_HA_MODULE',),
        'data': ('SCE_HA_DATA',),
        'capital': ('SCE_HA_CAPITAL',),
        'import': ('SCE_HA_IMPORT',),
        'instance': ('SCE_HA_INSTANCE',),
        }
    sample = """
SAMPLE NOT AVAILABLE
"""

    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(self.sciMozLexer)
            self._lexer.setKeywords(0, self._keywords)
            self._lexer.supportsFolding = 1
        return self._lexer

    _keywords = [
        "absolute value", "addition", "and", "array",
        "boolean",
        "ceiling", "character", "concatenate", "concatenation", "constant", "continuation passing style", "cosine", "cosine hyperbolic", "cosine hyperbolic inverse", "cosine inverse",
        "division",
        "empty", "equality", "even",
        "floor", "function composition",
        "index",
        "lazy evaluation", "length", "list", "list calculation", "list construction", "list insertion", "list item",
        "modulo", "monad", "multiplication",
        "nint",
        "odd", "or", "order",
        "power",
        "round",
        "sine", "sine hyperbolic", "sine hyperbolic inverse", "sine inverse", "split", "string", "subtraction", "sum",
        "tangent", "tangent hyperbolic", "tangent hyperbolic inverse", "tangent inverse", "trigonometry", "truncation", "tuple"
                ]
