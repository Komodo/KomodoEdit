from xpcom import components, ServerException

from koLanguageServiceBase import *

class koOthersLanguage(KoLanguageBase):
    name = "Others"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{b4a008ac-1b93-42d3-9365-e43b4a999e10}"

    defaultExtension = None
    commentDelimiterInfo = {}
    
    sample = """
SAMPLE NOT AVAILABLE
"""
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(
                components.interfaces.ISciMoz.SCLEX_OTHERS)
        return self._lexer
