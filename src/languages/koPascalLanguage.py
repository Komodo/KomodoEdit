from xpcom import components, ServerException

from koLanguageServiceBase import *

def registerLanguage(registery):
    registery.registerLanguage(koPascalLanguage())
    
class koPascalLanguage(KoLanguageBase):
    name = "Pascal"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{8AE35E4C-0EC9-49f2-A534-8FEAB91D261D}"

    defaultExtension = ".pas"
    commentDelimiterInfo = {
        # See the following for info on Pascal comments:
        #  http://www.math.uni-hamburg.de/it/software/fpk/ref/node7.html
        #XXX The line Pascal comment is a Delphi only thing, so I am leaving
        #    it out for now.
        #"line": [ "//" ],
        "block": [ ("{",  "}"),
                   ("(*", "*)") ],
    }
    supportsSmartIndent = "brace"
    
    def __init__(self):
        KoLanguageBase.__init__(self)
        self._style_info.update(
            _block_comment_styles = [sci_constants.SCE_C_COMMENT,
                                     sci_constants.SCE_C_COMMENTDOC,
                                     sci_constants.SCE_C_COMMENTDOCKEYWORD,
                                     sci_constants.SCE_C_COMMENTDOCKEYWORDERROR]
            )

    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(components.interfaces.ISciMoz.SCLEX_PASCAL)
            self._lexer.setKeywords(0, self._keywords)
            self._lexer.setKeywords(1, self._keywords2)
            self._lexer.supportsFolding = 1
        return self._lexer

    _keywords = """and array asm begin case cdecl class const constructor default 
destructor div do downto else end end. except exit exports external far file 
finalization finally for function goto if implementation in index inherited 
initialization inline interface label library message mod near nil not 
object of on or out overload override packed pascal private procedure program 
property protected public published raise read record register repeat resourcestring 
safecall set shl shr stdcall stored string then threadvar to try type unit 
until uses var virtual while with write xor""".split()

    _keywords2 = """write read default public protected private property
            published stored""".split()

