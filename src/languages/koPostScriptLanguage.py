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

class koPSLanguage(KoLanguageBase):
    name = "PostScript"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{b92e8d2e-513c-4cd7-87a8-bd866c683499}"
    _reg_categories_ = [("komodo-language", name)]

    _stateMap = {
        'default': ('SCE_PS_DEFAULT',
                    'SCE_PS_TEXT',),
        'keywords': ('SCE_PS_KEYWORD',),
        'identifiers': ('SCE_PS_NAME',),
        'comments': ('SCE_PS_COMMENT',
                     'SCE_PS_DSC_COMMENT',),
        'numbers': ('SCE_PS_NUMBER',),
        'strings': ('SCE_PS_HEXSTRING',
                    'SCE_PS_BASE85STRING',),
        'badstring': ('SCE_PS_BADSTRINGCHAR',),
        'variables': ('SCE_PS_DSC_VALUE',
                      'SCE_PS_IMMEVAL',),
        'literals': ('SCE_PS_LITERAL',),
        'parens': ('SCE_PS_PAREN_ARRAY',
                   'SCE_PS_PAREN_DICT',
                   'SCE_PS_PAREN_PROC',),
        }
    defaultExtension = '.ps'
    commentDelimiterInfo = {"line": [ "%" ]}
    
    sample = """
SAMPLE NOT AVAILABLE
"""
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(
                components.interfaces.ISciMoz.SCLEX_PS)
            self._lexer.setKeywords(0, self._keywords)
            self._lexer.setKeywords(1, self._keywords2)
            self._lexer.setKeywords(2, self._keywords3)
            self._lexer.setKeywords(3, self._keywords4)
            self._lexer.supportsFolding = 0
        return self._lexer

    # Postscript level 1 operators
    _keywords = """$error = == FontDirectory StandardEncoding UserObjects abs add aload
anchorsearch and arc arcn arcto array ashow astore atan awidthshow begin bind
bitshift bytesavailable cachestatus ceiling charpath clear cleardictstack
cleartomark clip clippath closefile closepath concat concatmatrix copy copypage
cos count countdictstack countexecstack counttomark currentcmykcolor
currentcolorspace currentdash currentdict currentfile currentflat currentfont
currentgray currenthsbcolor currentlinecap currentlinejoin currentlinewidth
currentmatrix currentmiterlimit currentpagedevice currentpoint currentrgbcolor
currentscreen currenttransfer cvi cvlit cvn cvr cvrs cvs cvx def defaultmatrix
definefont dict dictstack div dtransform dup echo end eoclip eofill eq
erasepage errordict exch exec execstack executeonly executive exit exp false
file fill findfont flattenpath floor flush flushfile for forall ge get
getinterval grestore grestoreall gsave gt idetmatrix idiv idtransform if ifelse
image imagemask index initclip initgraphics initmatrix inustroke invertmatrix
itransform known kshow le length lineto ln load log loop lt makefont mark
matrix maxlength mod moveto mul ne neg newpath noaccess nor not null nulldevice
or pathbbox pathforall pop print prompt pstack put putinterval quit rand rcheck
rcurveto read readhexstring readline readonly readstring rectstroke repeat
resetfile restore reversepath rlineto rmoveto roll rotate round rrand run save
scale scalefont search setblackgeneration setcachedevice setcachelimit
setcharwidth setcolorscreen setcolortransfer setdash setflat setfont setgray
sethsbcolor setlinecap setlinejoin setlinewidth setmatrix setmiterlimit
setpagedevice setrgbcolor setscreen settransfer setvmthreshold show showpage
sin sqrt srand stack start status statusdict stop stopped store string
stringwidth stroke strokepath sub systemdict token token transform translate
true truncate type ueofill undefineresource userdict usertime version vmstatus
wcheck where widthshow write writehexstring writestring xcheck xor""".split()
    
   # Postscript level 2 operators
    _keywords2 = """
GlobalFontDirectory ISOLatin1Encoding SharedFontDirectory UserObject arct
colorimage cshow currentblackgeneration currentcacheparams currentcmykcolor
currentcolor currentcolorrendering currentcolorscreen currentcolorspace
currentcolortransfer currentdevparams currentglobal currentgstate
currenthalftone currentobjectformat currentoverprint currentpacking
currentpagedevice currentshared currentstrokeadjust currentsystemparams
currentundercolorremoval currentuserparams defineresource defineuserobject
deletefile execform execuserobject filenameforall fileposition filter
findencoding findresource gcheck globaldict glyphshow gstate ineofill infill
instroke inueofill inufill inustroke languagelevel makepattern packedarray
printobject product realtime rectclip rectfill rectstroke renamefile
resourceforall resourcestatus revision rootfont scheck selectfont serialnumber
setbbox setblackgeneration setcachedevice2 setcacheparams setcmykcolor setcolor
setcolorrendering setcolorscreen setcolorspace setcolortranfer setdevparams
setfileposition setglobal setgstate sethalftone setobjectformat setoverprint
setpacking setpagedevice setpattern setshared setstrokeadjust setsystemparams
setucacheparams setundercolorremoval setuserparams setvmthreshold shareddict
startjob uappend ucache ucachestatus ueofill ufill undef undefinefont
undefineresource undefineuserobject upath ustroke ustrokepath vmreclaim
writeobject xshow xyshow yshow""".split()

# Postscript level 3 operators
    _keywords3 = """
cliprestore clipsave composefont currentsmoothness findcolorrendering
setsmoothness shfill""".split()

    # RIP-specific operators (Ghostscript)
    _keywords4 = """
.begintransparencygroup .begintransparencymask .bytestring .charboxpath
.currentaccuratecurves .currentblendmode .currentcurvejoin .currentdashadapt
.currentdotlength .currentfilladjust2 .currentlimitclamp .currentopacityalpha
.currentoverprintmode .currentrasterop .currentshapealpha
.currentsourcetransparent .currenttextknockout .currenttexturetransparent
.dashpath .dicttomark .discardtransparencygroup .discardtransparencymask
.endtransparencygroup .endtransparencymask .execn .filename .filename
.fileposition .forceput .forceundef .forgetsave .getbitsrect .getdevice
.inittransparencymask .knownget .locksafe .makeoperator .namestring .oserrno
.oserrorstring .peekstring .rectappend .runandhide .setaccuratecurves
.setblendmode .setcurvejoin .setdashadapt .setdebug .setdefaultmatrix
.setdotlength .setfilladjust2 .setlimitclamp .setmaxlength .setopacityalpha
.setoverprintmode .setrasterop .setsafe .setshapealpha .setsourcetransparent
.settextknockout .settexturetransparent .stringbreak .stringmatch .tempfile
.type1decrypt .type1encrypt .type1execchar .unread arccos arcsin copydevice
copyscanlines currentdevice finddevice findlibfile findprotodevice flushpage
getdeviceprops getenv makeimagedevice makewordimagedevice max min
putdeviceprops setdevice""".split()
