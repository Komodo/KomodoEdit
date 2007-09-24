from xpcom import components, ServerException

from koLanguageServiceBase import *

def registerLanguage(registery):
    registery.registerLanguage(koLoutLanguage())
 
class koLoutLanguage(KoLanguageBase):
    name = "Lout"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{ca1ef820-5a30-47fb-921d-4dcbcd0dd2dd}"

    _stateMap = {
        'default': ('SCE_LOUT_DEFAULT',),
        'comments': ('SCE_LOUT_COMMENT',),
        'numbers': ('SCE_LOUT_NUMBER',),
        'strings': ('SCE_LOUT_STRING',),
        'operators': ('SCE_LOUT_OPERATOR',),
        'identifiers': ('SCE_LOUT_IDENTIFIER',),
        'stringeol': ('SCE_LOUT_STRINGEOL',),
        'keywords': ('SCE_LOUT_WORD',),
        'keywords2': ('SCE_LOUT_WORD2',
                      'SCE_LOUT_WORD3',
                      'SCE_LOUT_WORD4',),
    }
    defaultExtension = '.lt'
    commentDelimiterInfo = {"line": [ "#" ]}
    
    sample = """
SAMPLE NOT AVAILABLE
"""
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(
                components.interfaces.ISciMoz.SCLEX_LOUT)
            self._lexer.setKeywords(0, self._keywords)
            self._lexer.setKeywords(1, self._keywords2)
            self._lexer.setKeywords(2, self._keywords3)
        return self._lexer

    _keywords = """@OptGall @Filter @FilterIn @FilterOut 
@FilterErr @FontDef @Family @Face @Name @Metrics @ExtraMetrics 
@Mapping @Recode @Common @Rump @Meld @Insert @OneOf @Next @Plus 
@Minus @Wide @High @HShift @VShift @BeginHeaderComponent 
@EndHeaderComponent @SetHeaderComponent @ClearHeaderComponent @OneCol 
@OneRow @HScale @VScale @HCover @VCover @Scale @KernShrink @HContract 
@VContract @HLimited @VLimited @HExpand @VExpand @StartHVSpan 
@StartHSpan @StartVSpan @HSpan @VSpan @PAdjust @HAdjust @VAdjust 
@Rotate @Background @IncludeGraphic @SysIncludeGraphic @Graphic 
@LinkSource @LinkDest @URLLink @PlainGraphic @Verbatim @RawVerbatim 
@Case @Yield @BackEnd @Char @Font @Space @YUnit @ZUnit @Break 
@Underline @SetColour @SetColor @SetTexture @Outline @Language 
@CurrLang @CurrFamily @CurrFace @CurrYUnit @CurrZUnit @LEnv @LClos 
@LUse @LEO @Open @Use @NotRevealed @Tagged @Database @SysDatabase 
@Include @SysInclude @IncludeGraphicRepeated @PrependGraphic 
@SysIncludeGraphicRepeated @SysPrependGraphic @Target @Null 
@PageLabel @Galley @ForceGalley @LInput @Split @Tag @Key @Optimize 
@Merge @Enclose @Begin @End @Moment @Second @Minute @Hour @Day @Month 
@Year @Century @WeekDay @YearDay @DaylightSaving @@A @@B @@C @@D @@E @@V""".split()

    _keywords2 = """&&& && & ^// ^/ ^|| ^| ^& // / || |""".split()

    _keywords3 = """def langdef force horizontally into 
extend import export precedence associativity left right body macro 
named compulsory following preceding foll_or_prec now""".split()
