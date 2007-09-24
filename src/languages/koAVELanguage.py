from xpcom import components, ServerException

from koLanguageServiceBase import *

def registerLanguage(registery):
    registery.registerLanguage(koAVELanguage())

class koAVELanguage(KoLanguageBase):
    name = "Avenue"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{3c27e841-7155-4f6b-8fc3-8c6b391a2037}"

    _stateMap = {
        'operators': ('SCE_AVE_OPERATOR',),
        'enum': ('SCE_AVE_ENUM',),
        'default': ('SCE_AVE_DEFAULT',),
        'numbers': ('SCE_AVE_NUMBER',),
        'identifiers': ('SCE_AVE_IDENTIFIER',),
        'strings': ('SCE_AVE_STRING',),
        'comments': ('SCE_AVE_COMMENT',),
        'stringeol': ('SCE_AVE_STRINGEOL',),
        'keywords': ('SCE_AVE_WORD',),
        'keywords2': ('SCE_AVE_WORD1',
                      'SCE_AVE_WORD2',
                      'SCE_AVE_WORD3',
                      'SCE_AVE_WORD4',
                      'SCE_AVE_WORD5',
                      'SCE_AVE_WORD6',),
        }
    defaultExtension = '.ave'
    commentDelimiterInfo = {
        "line": [ "'--" ],
        "block": [ ("'--", "'--") ],
    }
    
    sample = """
SAMPLE NOT AVAILABLE
"""
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(components.interfaces.ISciMoz.SCLEX_AVE)
            self._lexer.setKeywords(0, self.keywords)
        return self._lexer

    keywords = """nil true false else for if while then elseif end av self
                in exit"""

