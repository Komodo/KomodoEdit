from xpcom import components, ServerException

from koLanguageServiceBase import *

def registerLanguage(registery):
    registery.registerLanguage(koADALanguage())
    
class koADALanguage(KoLanguageBase):
    name = "Ada"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{6148E361-5E42-4AA1-B22D-BB2D02DE4FB1}"

    _stateMap = {
        'default': ('SCE_ADA_DEFAULT',),
        'keywords': ('SCE_ADA_WORD',),
        'identifiers': ('SCE_ADA_IDENTIFIER',),
        'comments': ('SCE_ADA_COMMENTLINE',),
        'numbers': ('SCE_ADA_NUMBER',),
        'strings': ('SCE_ADA_CHARACTER',
                    'SCE_ADA_STRING',),
        'stringeol': ('SCE_ADA_CHARACTEREOL',
                      'SCE_ADA_STRINGEOL',),
        'illegals': ('SCE_ADA_ILLEGAL',),
        'delimiters': ('SCE_ADA_DELIMITER',),
        'labels': ('SCE_ADA_LABEL',),
        }
    commentDelimiterInfo = {
        "line": [ "--" ]
    }

    defaultExtension = ".ada"
    sample = """-- simple programming with floating-point #s
with Ada.Float_Text_IO;
use Ada.Float_Text_IO;
procedure Think is
   A, B : Float := 0.0; -- A and B initially zero; note the period.
   I, J : Integer := 1;
begin
   A := B   7.0;
   I := J * 3;
   B := Float(I)   A;
   Put(B);
end Think;
"""
    def __init__(self):
        KoLanguageBase.__init__(self)
        del self.matchingSoftChars["'"]

    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(components.interfaces.ISciMoz.SCLEX_ADA)
            self._lexer.setKeywords(0, self._keywords)
            self._lexer.supportsFolding = 0
        return self._lexer


    _keywords = ["abort", "abs", "abstract", "accept", "access"
                 "aliased", "all", "and", "array", "at", "begin", "body",
                 "case", "constant", "declare", "delay", "delta",
                 "digits", "do", "else", "elsif", "end", "entry",
                 "exception", "exit", "for", "function", "generic",
                 "goto", "if", "in", "is", "limited", "loop", "mod",
                 "new", "not", "null", "of", "or", "others", "out",
                 "package", "pragma", "private", "procedure",
                 "protected", "raise", "range", "record", "rem",
                 "renames", "requeue", "return", "reverse",
                 "select", "separate", "subtype", "tagged",
                 "task", "terminate", "then", "type", "until", "use",
                 "when", "while", "with", "xor"]