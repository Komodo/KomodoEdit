from xpcom import components, ServerException

from koLanguageServiceBase import *

def registerLanguage(registery):
    registery.registerLanguage(konnCrontabLanguage())

class konnCrontabLanguage(KoLanguageBase):
    name = "nnCrontab"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{49F53DE0-67D3-4172-868A-CE5DF6EB5809}"

    defaultExtension = ".tab"
    commentDelimiterInfo = {"line": [ "#" ]}
    
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(components.interfaces.ISciMoz.SCLEX_NNCRONTAB)
            self._lexer.setKeywords(0, self._keywords)
        return self._lexer

    _keywords = ["Action", "Command", "Rule", "QCommand", "Time" \
                    "Days", "Hours", "Minutes", "Months", "WeekDays ", "Years" \
                    "AGAIN", "AND", "BEGIN", "CASE", "COMPARE", "CREATE", "DO" \
                    "ELSE", "ENDCASE", "ENDOF", "I", "IF", "LEAVE", "LOOP" \
                    "NOT", "OF", "OFF", "ON", "OR", "THEN", "TO", "VALUE", "VARIABLE"]

