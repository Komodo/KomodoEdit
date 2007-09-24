from xpcom import components, ServerException

from koLanguageServiceBase import *

def registerLanguage(registery):
    registery.registerLanguage(koCamlLanguage())

# see http://caml.inria.fr/
class koCamlLanguage(KoLanguageBase):
    name = "Objective Caml"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{23CCAA5C-53E5-11DA-9353-000D935D3368}"

    commentDelimiterInfo = {
        "block": [ ("(*", "*)") ]
    }

    defaultExtension = ".ml" # and .mli

    supportsSmartIndent = "brace"
    sciMozLexer = components.interfaces.ISciMoz.SCLEX_CAML

    _stateMap = {
        'default': ('SCE_CAML_DEFAULT',),
        'keywords': ('SCE_CAML_KEYWORD', 'SCE_CAML_KEYWORD2',),
        'identifiers': ('SCE_CAML_IDENTIFIER',),
        'comments': ('SCE_CAML_COMMENT','SCE_CAML_COMMENT1',
                     'SCE_CAML_COMMENT2', 'SCE_CAML_COMMENT3',),
        'operators': ('SCE_CAML_OPERATOR',),
        'numbers': ('SCE_CAML_NUMBER',),
        'strings': ('SCE_CAML_STRING', 'SCE_CAML_CHAR',),
        'linenumber': ('SCE_CAML_LINENUM',),
        'tagname': ('SCE_CAML_TAGNAME',),
        }
    sample = """
SAMPLE NOT AVAILABLE
"""

    def __init__(self):
        KoLanguageBase.__init__(self)
        del self.matchingSoftChars["'"]
        
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(self.sciMozLexer)
            self._lexer.setKeywords(0, self._keywords)
            self._lexer.setKeywords(1, self._keywords2)
            self._lexer.supportsFolding = 1
        return self._lexer

    _keywords = [
        "and", "as", "assert", "asr", "begin", "class",
        "constraint", "do", "done", "downto", "else", "end",
        "exception", "external", "false", "for", "fun", "function",
        "functor", "if", "in", "include", "inherit", "initializer",
        "land", "lazy", "let", "lor", "lsl", "lsr",
        "lxor", "match", "method", "mod", "module", "mutable",
        "new", "object", "of", "open", "or", "private",
        "rec", "sig", "struct", "then", "to", "true",
        "try", "type", "val", "virtual", "when", "while",
        "with"]
    
    _keywords2 = ["option", "Some", "None", "ignore", "ref"]
