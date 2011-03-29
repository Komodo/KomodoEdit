# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
# 
# The contents of this file are subject to the Mozilla Public License
# Version 1.1 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
# 
# Software distributed under the License is distributed on an "AS IS"
# basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
# License for the specific language governing rights and limitations
# under the License.
# 
# The Original Code is Komodo code.
# 
# The Initial Developer of the Original Code is ActiveState Software Inc.
# Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
# ActiveState Software Inc. All Rights Reserved.
# 
# Contributor(s):
#   ActiveState Software Inc
# 
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
# 
# ***** END LICENSE BLOCK *****

from xpcom import components, ServerException

from koLanguageServiceBase import *

class koLoutLanguage(KoLanguageBase):
    name = "Lout"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{ca1ef820-5a30-47fb-921d-4dcbcd0dd2dd}"
    _reg_categories_ = [("komodo-language", name)]

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
