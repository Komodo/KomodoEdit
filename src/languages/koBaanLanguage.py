from xpcom import components, ServerException

from koLanguageServiceBase import *

def registerLanguage(registery):
    registery.registerLanguage(koBaanLanguage())
    
class koBaanLanguage(KoLanguageBase):
    name = "Baan"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{E060D09B-27FB-4b25-8DE0-E12FBF200285}"

    defaultExtension = ".bc"
    commentDelimiterInfo = {
        "line": [ "|" ],
        "block": [ ("dllusage", "enddllusage") ],
    }
    sample = """	#pragma nowarnings
	#include <include>	|include functions
	
function main()
{
| Comments go here

	string	tmp.file(1024)		| Temporary file name.
	tmp.file = creat.tmp.file$( bse.tmp.dir$() )
	wait.and.activate("foobar", argv$(1), tmp.file, argv$(3),argv$(4))
}

    def __init__(self):
        KoLanguageBase.__init__(self)
        self._style_info.update(
            _block_comment_styles = [sci_constants.SCE_BAAN_COMMENT,
                                     sci_constants.SCE_BAAN_COMMENTDOC]
            )
"""
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(components.interfaces.ISciMoz.SCLEX_BAAN)
        return self._lexer


