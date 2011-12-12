from xpcom import components, ServerException

from koLanguageServiceBase import *

class koIniLanguage(KoLanguageBase):
    name = "Ini"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{a19a42e9-f61f-4bf7-b39d-d4f5c7dd1edf}"
    _reg_categories_ = [("komodo-language", name)]

    defaultExtension = ".ini"
    commentDelimiterInfo = { "line": [ ";", "#", "!" ]  }
    
    _stateMap = {
        'default': ('SCE_PROPS_DEFAULT',),
        'comments': ('SCE_PROPS_COMMENT',),
        'keywords': ('SCE_PROPS_SECTION',),
        'identifier': ('SCE_PROPS_KEY',),
        'functions': ('SCE_PROPS_DEFVAL',),
        'operators': ('SCE_PROPS_ASSIGNMENT',),
        }

    sample = """
;;;;;;;;;;;;;;;;;;;
; Module Settings ;
;;;;;;;;;;;;;;;;;;;

[Date]
; Defines the default timezone used by the date functions
; http://php.net/date.timezone
date.default_latitude = 31.7667
ibase.timeformat = "%H:%M:%S"
"""

    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(components.interfaces.ISciMoz.SCLEX_PROPERTIES)
            self._lexer.setKeywords(0, self._keywords)
        return self._lexer

    _keywords = []

