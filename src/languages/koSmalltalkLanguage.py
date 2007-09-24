from xpcom import components, ServerException

from koLanguageServiceBase import *

def registerLanguage(registery):
    registery.registerLanguage(koSmalltalkLanguage())

class koSmalltalkLanguage(KoLanguageBase):
    name = "Smalltalk"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{01E22A2E-53EF-11DA-AFBB-000D935D3368}"

    commentDelimiterInfo = {}

    defaultExtension = ".st" 

    supportsSmartIndent = "brace"
    sciMozLexer = components.interfaces.ISciMoz.SCLEX_SMALLTALK

    _stateMap = {
        'default': ('SCE_ST_DEFAULT',),
        'keywords': ('SCE_ST_SPECIAL', 'SCE_ST_SPEC_SEL', 'SCE_ST_BOOL',
                     'SCE_ST_SELF', 'SCE_ST_SUPER', 'SCE_ST_NIL',
                     'SCE_ST_KWSEND', 'SCE_ST_RETURN',),
        'symbols': ('SCE_ST_SYMBOL',),
        'comments': ('SCE_ST_COMMENT',),
        'variables': ('SCE_ST_GLOBAL',),
        'numbers': ('SCE_ST_NUMBER', 'SCE_ST_BINARY',),
        'strings': ('SCE_ST_STRING', 'SCE_ST_CHARACTER',),
        'assign': ('SCE_ST_ASSIGN',),
        }
    sample = """
SAMPLE NOT AVAILABLE
"""

    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(self.sciMozLexer)
            self._lexer.setKeywords(0, self._keywords)
            self._lexer.supportsFolding = 0
        return self._lexer

    _keywords = """
        ifTrue: ifFalse: whileTrue: whileFalse: ifNil: ifNotNil:
        whileTrue whileFalse repeat isNil notNil
    """.split()
    
