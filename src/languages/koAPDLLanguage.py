from xpcom import components, ServerException

from koLanguageServiceBase import *

def registerLanguage(registery):
    registery.registerLanguage(koAPDLLanguage())

class koAPDLLanguage(KoLanguageBase):
    name = "APDL"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{799aeb24-33a0-4f64-8ee1-9dfac22ed828}"

    _stateMap = {
        'default': ('SCE_APDL_DEFAULT',),
        'keywords': ('SCE_APDL_WORD',),
        'identifiers': ('SCE_ADA_IDENTIFIER',),
        'comments': ('SCE_APDL_COMMENT',
                     'SCE_APDL_COMMENTBLOCK'),
        'numbers': ('SCE_APDL_NUMBER',),
        'strings': ('SCE_APDL_STRING',),
        'functions': ('SCE_APDL_FUNCTION',),
        'keywords': ('SCE_APDL_COMMAND',
                     'SCE_APDL_SLASHCOMMAND',
                     'SCE_APDL_STARCOMMAND',),
        'processor': ('SCE_APDL_PROCESSOR',),
        'arguments': ('SCE_APDL_ARGUMENT',),
        }

    defaultExtension = ".mac"
    commentDelimiterInfo = {
        "line": [ "/COM," ],
    }
    
    sample = """
/BATCH                     !Batch input
/FILE,punch                !Define jobname
/NOPR                      !Suppress printout

/COM, small example

*VWRITE
('*NSET,NSET=NTOP')
LSEL,S,LOC,Y,FTHK
NSLL,S,1
*GET,NNOD,NODE,,COUNT
NNUM = 0
*DO,I,1,NNOD,1
NNUM = NDNEXT(NNUM)
*VWRITE,NNUM
(F7.0,TL1,',')
*ENDDO
ALLSEL
"""
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(components.interfaces.ISciMoz.SCLEX_APDL)
        return self._lexer
