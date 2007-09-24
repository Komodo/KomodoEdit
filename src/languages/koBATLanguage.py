from xpcom import components, ServerException

from koLanguageServiceBase import *

def registerLanguage(registery):
    registery.registerLanguage(koBatchLanguage())
    
class koBatchLanguage(KoLanguageBase):
    name = "Batch"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{12e65384-fe22-4c25-9922-069760da24d8}"

    accessKey = 'b'
    defaultExtension = ".bat"
    commentDelimiterInfo = {
        "line": [ "rem ", "REM " ],
    }
    
    sample = """
    @echo off
REM comment
SET SOUND=C:\PROGRA~1\CREATIVE\CTSND
SET BLASTER=A220 I5 D1 H5 P330 E620 T6
SET PATH=C:\WINDOWS;C:\ 
LH C:\WINDOWS\COMMAND\MSCDEX.EXE /D:123 
LH C:\MOUSE\MOUSE.EXE
DOSKEY
CLS
"""
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(components.interfaces.ISciMoz.SCLEX_BATCH)
        return self._lexer
