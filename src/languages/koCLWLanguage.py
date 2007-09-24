from xpcom import components, ServerException

from koLanguageServiceBase import *

def registerLanguage(registery):
    registery.registerLanguage(koCLWLanguage())

class koCLWLanguage(KoLanguageBase):
    name = "CLW"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{76459319-02e4-4c45-b529-c90fa2d28825}"

    _stateMap = {
        'operators': ('SCE_CLW_COMPILER_DIRECTIVE',
                      'SCE_CLW_STRUCTURE_DATA_TYPE',
                      'SCE_CLW_ATTRIBUTE',
                      'SCE_CLW_STANDARD_EQUATE',),
        'labels': ('SCE_CLW_LABEL',),
        'errors': ('SCE_CLW_ERROR',),
        'default': ('SCE_CLW_DEFAULT',),
        'numbers': ('SCE_CLW_INTEGER_CONSTANT',
                    'SCE_CLW_REAL_CONSTANT',),
        'identifiers': ('SCE_CLW_USER_IDENTIFIER',),
        'strings': ('SCE_CLW_STRING',
                    'SCE_CLW_PICTURE_STRING',),
        'comments': ('SCE_CLW_COMMENT',),
        'functions': ('SCE_CLW_BUILTIN_PROCEDURES_FUNCTION',),
        'keywords': ('SCE_CLW_KEYWORD',),
        }
    defaultExtension = '.clw'
    commentDelimiterInfo = {}
    
    sample = """
SAMPLE NOT AVAILABLE
"""
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(components.interfaces.ISciMoz.SCLEX_CLW)
        return self._lexer
