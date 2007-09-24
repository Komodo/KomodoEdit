from xpcom import components, ServerException

from koLanguageServiceBase import *

def registerLanguage(registery):
    registery.registerLanguage(koMPTLotLanguage())
    
class koMPTLotLanguage(KoLanguageBase):
    name = "Lot"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{073ad8ca-efa2-49d8-b694-1de9edf9da28}"

    _stateMap = {
        'default': ('SCE_LOT_DEFAULT',),
        'headers': ('SCE_LOT_BREAK',),
        'set': ('SCE_LOT_SET',),
        'pass': ('SCE_LOT_PASS',),
        'fail': ('SCE_LOT_FAIL',),
        'abort': ('SCE_LOT_ABORT',),
        }
    defaultExtension = '.lot'
    commentDelimiterInfo = {}
    
    sample = """
SAMPLE NOT AVAILABLE
"""
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(
                components.interfaces.ISciMoz.SCLEX_LOT)
        return self._lexer
