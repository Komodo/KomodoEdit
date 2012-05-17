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

from koLanguageServiceBase import KoLexerLanguageService
from koLanguageKeywordBase import KoCommonBasicLanguageService

class basicBase(KoCommonBasicLanguageService):
    _keywords = None
    _keywords2 = None
    sciMozLexer = None

    commentDelimiterInfo = {
        "line": [ "'",  "rem ", "REM "  ],
    }


    _stateMap = {
        'default': ('SCE_B_DEFAULT',),
        'keywords': ('SCE_B_KEYWORD',
                     'SCE_B_KEYWORD2',
                     'SCE_B_KEYWORD3',
                     'SCE_B_KEYWORD4',),
        'identifiers': ('SCE_B_IDENTIFIER',),
        'comments': ('SCE_B_COMMENT',),
        'numbers': ('SCE_B_NUMBER',),
        'strings': ('SCE_B_STRING',),
        'stringeol': ('SCE_B_STRINGEOL',),
        'operators': ('SCE_B_OPERATOR',),
        'preprocessor': ('SCE_B_PREPROCESSOR',),
        'date': ('SCE_B_DATE',),
        'constants': ('SCE_B_CONSTANT',),
        'assembly': ('SCE_B_ASM',),
        }


    sample = """
INPUT "What is your name"; UserName$
PRINT "Hello "; UserName$
DO
   INPUT "How many stars do you want"; NumStars
   Stars$ = ""
   Stars$ = REPEAT$("*", NumStars)   ' <- ANSI BASIC
   --or--
   Stars$ = STRING$(NumStars, "*")   ' <- MS   BASIC
   PRINT Stars$
   DO
      INPUT "Do you want more stars";  Answer$
   LOOP UNTIL Answer$ <> ""
   Answer$ = LEFT$(Answer$, 1);
LOOP WHILE  UCASE$(Answer$) = "Y"
PRINT "Goodbye ";
FOR I = 1 TO 200
   PRINT UserName$; " ";
NEXT I
PRINT
"""
    
    def __init__(self):
        KoCommonBasicLanguageService.__init__(self)
        del self.matchingSoftChars["'"]
        
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(self.sciMozLexer)
            self._lexer.setKeywords(0, self._keywords)
            if self._keywords2:
                self._lexer.setKeywords(1, self._keywords2)
            self._lexer.supportsFolding = 1
        return self._lexer
    
# see http://www.freebasic.net/
class koFreeBasicLanguage(basicBase):
    name = "FreeBasic"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{37BF2C34-5549-11DA-B909-000D935D3368}"
    _reg_categories_ = [("komodo-language", name)]

    defaultExtension = ".bas"
    supportsSmartIndent = "brace"
    sciMozLexer = components.interfaces.ISciMoz.SCLEX_FREEBASIC
    
    # list obtained from http://msdn.microsoft.com/library/default.asp?url=/library/en-us/vblr7/html/vaorivblangkeywordsall.asp
    _keywords =  """append as asc asin asm atan2 atn beep bin binary bit bitreset bitset bload 
                    bsave byref byte byval call callocate case cbyte cdbl cdecl chain chdir chr 
                    cint circle clear clng clngint close cls color command common cons const 
                    continue cos cshort csign csng csrlin cubyte cuint culngint cunsg curdir 
                    cushort custom cvd cvi cvl cvlongint cvs cvshort data date deallocate declare 
                    defbyte defdbl defined defint deflng deflngint defshort defsng defstr defubyte 
                    defuint defulngint defushort dim dir do double draw dylibload dylibsymbol else 
                    elseif end enum environ environ$ eof eqv erase err error exec exepath exit exp 
                    export extern field fix flip for fre freefile function get getjoystick getkey 
                    getmouse gosub goto hex hibyte hiword if iif imagecreate imagedestroy imp 
                    inkey inp input instr int integer is kill lbound lcase left len let lib line 
                    lobyte loc local locate lock lof log long longint loop loword lset ltrim 
                    mid mkd mkdir mki mkl mklongint mks mkshort mod multikey mutexcreate 
                    mutexdestroy mutexlock mutexunlock name next not oct on once open option or out 
                    output overload paint palette pascal pcopy peek peeki peeks pipe pmap point 
                    pointer poke pokei pokes pos preserve preset print private procptr pset ptr 
                    public put random randomize read reallocate redim rem reset restore resume 
                    resume next return rgb rgba right rmdir rnd rset rtrim run sadd screen 
                    screencopy screeninfo screenlock screenptr screenres screenset screensync 
                    screenunlock seek statement seek function selectcase setdate setenviron 
                    setmouse settime sgn shared shell shl short shr sin single sizeof sleep space 
                    spc sqr static stdcall step stop str string string strptr sub swap system tab 
                    tan then threadcreate threadwait time time timer to trans trim type ubound 
                    ubyte ucase uinteger ulongint union unlock unsigned until ushort using va_arg 
                    va_first va_next val val64 valint varptr view viewprint wait wend while width 
                    window windowtitle with write xor zstring""".split()

    _keywords2 = """#define #dynamic #else #endif #error #if #ifdef #ifndef #inclib #include #print #static #undef""".split()

# see http://www.purebasic.com/
class koPureBasicLanguage(basicBase):
    name = "PureBasic"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{3B88E3E4-5549-11DA-B27F-000D935D3368}"
    _reg_categories_ = [("komodo-language", name)]
    
    sciMozLexer = components.interfaces.ISciMoz.SCLEX_PUREBASIC
    defaultExtension = ".pb"

    _keywords="""and break case continue data 
                datasection declare declarecdll declaredll default deftype dim else 
                elseif end enddatasection endenumeration endif endinterface endprocedure 
                endselect endstructure endstructureunion enumeration extends fakereturn 
                for foreach forever global gosub goto if includebinary includefile 
                includepath interface newlist next or procedure procedurecdll 
                proceduredll procedurereturn protected read repeat restore return select 
                shared static step structure structureunion to until wend while xincludefile""".split()

# see http://www.blitzbasic.com/Products/blitzmax.php
class koBlitzBasicLanguage(basicBase):
    name = "BlitzBasic"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{3EF4DCC6-5549-11DA-B774-000D935D3368}"
    _reg_categories_ = [("komodo-language", name)]
    
    sciMozLexer = components.interfaces.ISciMoz.SCLEX_BLITZBASIC
    defaultExtension = ".bb"

    _keywords = """abs accepttcpstream acos after and apptitle asc asin atan atan2
                    automidhandle autosuspend availvidmem backbuffer banksize before bin calldll
                    case ceil changedir channelpan channelpitch channelplaying channelvolume chr
                    closedir closefile closemovie closetcpserver closetcpstream closeudpstream cls
                    clscolor color colorblue colorgreen colorred commandline const copybank copyfile
                    copyimage copypixel copypixelfast copyrect copystream cos countgfxdrivers
                    countgfxmodes counthostips createbank createdir createimage createnetplayer
                    createprocess createtcpserver createtimer createudpstream currentdate currentdir
                    currenttime data debuglog default delay delete deletedir deletefile
                    deletenetplayer desktopbuffer dim dottedip drawblock drawblockrect drawimage
                    drawimagerect drawmovie each else else if elseif end end function end if end
                    select end type endgraphics endif eof execfile exit exp false field filepos
                    filesize filetype first flip float floor flushjoy flushkeys flushmouse
                    fontheight fontname fontsize fontstyle fontwidth for forever freebank freefont
                    freeimage freesound freetimer frontbuffer function gammablue gammagreen gammared
                    getcolor getenv getkey getmouse gfxdrivername gfxmodedepth gfxmodeexists
                    gfxmodeformat gfxmodeheight gfxmodewidth global gosub goto grabimage graphics
                    graphicsbuffer graphicsdepth graphicsformat graphicsheight graphicswidth
                    handleimage hex hidepointer hostip hostnetgame if imagebuffer imageheight
                    imagerectcollide imagerectoverlap imagescollide imagesoverlap imagewidth
                    imagexhandle imageyhandle include input insert instr int joinnetgame joydown
                    joyhat joyhit joypitch joyroll joytype joyu joyudir joyv joyvdir joyx joyxdir
                    joyy joyyaw joyydir joyz joyzdir keydown keyhit keywait last left len line
                    loadanimimage loadbuffer loadfont loadimage loadsound local lockbuffer
                    lockedformat lockedpitch lockedpixels log log10 loopsound lower lset maskimage
                    mid midhandle millisecs mod morefiles mousedown mousehit mousex mousexspeed
                    mousey mouseyspeed mousez mousezspeed movemouse movieheight movieplaying
                    moviewidth netmsgdata netmsgfrom netmsgto netmsgtype netplayerlocal
                    netplayername new next nextfile not null openfile openmovie opentcpstream or
                    origin oval pausechannel pausetimer peekbyte peekfloat peekint peekshort pi
                    playcdtrack playmusic playsound plot pokebyte pokefloat pokeint pokeshort print
                    queryobject rand read readavail readbyte readbytes readdir readfile readfloat
                    readint readline readpixel readpixelfast readshort readstring rect rectsoverlap
                    recvnetmsg recvudpmsg repeat replace resettimer resizebank resizeimage restore
                    resumechannel resumetimer return right rnd rndseed rotateimage rset runtimeerror
                    sar savebuffer saveimage scaleimage scanline seedrnd seekfile select sendnetmsg
                    sendudpmsg setbuffer setenv setfont setgamma setgfxdriver sgn shl showpointer
                    shr sin soundpan soundpitch soundvolume sqr startnetgame step stop stopchannel
                    stopnetgame str string stringheight stringwidth systemproperty tan tcpstreamip
                    tcpstreamport tcptimeouts text tformfilter tformimage then tileblock tileimage
                    timerticks to totalvidmem trim true type udpmsgip udpmsgport udpstreamip
                    udpstreamport udptimeouts unlockbuffer until updategamma upper viewport vwait
                    waitkey waitmouse waittimer wend while write writebyte writebytes writefile
                    writefloat writeint writeline writepixel writepixelfast writeshort writestring
                    xor""".split()
