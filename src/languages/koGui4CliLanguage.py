from xpcom import components, ServerException

from koLanguageServiceBase import *

def registerLanguage(registery):
    registery.registerLanguage(koGui4CliLanguage())

class koGui4CliLanguage(KoLanguageBase):
    name = "Gui4Cli"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{2d7a3802-5582-4c58-b7b1-bcfb88f3107b}"

    _stateMap = {
        'default': ('SCE_GC_DEFAULT',),
        'comments': ('SCE_GC_COMMENTLINE',
                     'SCE_GC_COMMENTBLOCK',),
        'strings': ('SCE_GC_STRING',),
        'globals': ('SCE_GC_GLOBAL',),
        'keywords': ('SCE_GC_COMMAND',),
        'operators': ('SCE_GC_OPERATOR',),
        'attributes': ('SCE_GC_ATTRIBUTE',),
        'control': ('SCE_GC_CONTROL',),
        'events': ('SCE_GC_EVENT',),
    }
    defaultExtension = '.gc'
    commentDelimiterInfo = {
        "line": [ "//" ],
        "block": [ ("/*", "*/") ],
        "markup": "*",
    }
    
    sample = """
SAMPLE NOT AVAILABLE
"""
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(
                components.interfaces.ISciMoz.SCLEX_GUI4CLI)
            self._lexer.supportsFolding = 1
        return self._lexer
