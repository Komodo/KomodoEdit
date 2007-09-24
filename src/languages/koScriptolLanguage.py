from xpcom import components, ServerException

from koLanguageServiceBase import *

def registerLanguage(registery):
    registery.registerLanguage(koScriptolLanguage())
    
class koScriptolLanguage(KoLanguageBase):
    name = "Scriptol"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{cce047e6-ddd8-4790-b750-f53c4c2c7894}"

    _stateMap = {
        'default': ('SCE_SCRIPTOL_DEFAULT',),
        'keywords': ('SCE_SCRIPTOL_KEYWORD',),
        'identifiers': ('SCE_SCRIPTOL_IDENTIFIER',),
        'comments': ('SCE_SCRIPTOL_COMMENTLINE',
                     'SCE_SCRIPTOL_COMMENTBLOCK',),
        'numbers': ('SCE_SCRIPTOL_NUMBER',),
        'strings': ('SCE_SCRIPTOL_STRING',
                    'SCE_SCRIPTOL_CHARACTER',),
        'stringeol': ('SCE_SCRIPTOL_STRINGEOL',),
        'operators': ('SCE_SCRIPTOL_OPERATOR',),
        'white': ('SCE_SCRIPTOL_WHITE',),
        'persistent': ('SCE_SCRIPTOL_PERSISTENT',),
        'cstyle': ('SCE_SCRIPTOL_CSTYLE',),
        'triple': ('SCE_SCRIPTOL_TRIPLE',),
        'classnames': ('SCE_SCRIPTOL_CLASSNAME',),
        'preprocessor': ('SCE_SCRIPTOL_PREPROCESSOR',),
        }

    defaultExtension = '.sol'
    commentDelimiterInfo = {"line": [ "`" ]}
    
    sample = """
SAMPLE NOT AVAILABLE
"""
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(
                components.interfaces.ISciMoz.SCLEX_SCRIPTOL)
            self._lexer.setKeywords(0, self._keywords)
            self._lexer.supportsFolding = 0
        return self._lexer

    _keywords = """act action alias always and array as
        bool boolean break by byte
        class case catch const constant continue
        dyn def define dict do double
        echo else elsif end enum error false file for float forever function
        globak gtk
        in if ifdef import include int integer java javax
        let long match mod nil not natural null number
        or print protected public real return redo
        scan script scriptol sol short super static step until using
        var text then this true try
        void volatile while when
        undef zero""".split()