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

class koFortran77Language(KoLanguageBase):
    name = "Fortran 77"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{2B5E00B3-904E-456B-BB12-B27FBD6D81E2}"
    _reg_categories_ = [("komodo-language", name)]

    defaultExtension = ".f"
    commentDelimiterInfo = { "line": [ "!", "C " ]  }
    supportsSmartIndent = "brace"

    _keywords1 = """
    allocatable allocate assignment associate backspace block 
    blockdata call case character class close common complex contains continue 
    cycle data deallocate default dimension direct do double doubleprecision 
    elemental else elseif elsewhere end endassociate endblock endblockdata enddo endfile 
    endforall endfunction endif endinterface endmodule endprogram endselect 
    endsubroutine endtype endwhere entry equivalence err exist exit external final forall 
    format formatted function generic go goto if implicit in inout include 
    inquire integer intent interface intrinsic iolength iostat kind 
    len logical module namelist none nopass null nullify only open operator optional 
    parameter pass pointer position precision print private procedure program public pure 
    out read readwrite real rec recursive result return rewind save select selectcase 
    sequence sequential stat status
    stop subroutine target then to type unformatted unit use where while write
    """.split()
    
    # keywords2 is for highlighting intrinsic and extended functions
    _keywords2 = """
    abs achar acos acosd adjustl adjustr 
    aimag aimax0 aimin0 aint ajmax0 ajmin0 akmax0 akmin0 all allocated alog 
    alog10 amax0 amax1 amin0 amin1 amod anint any asin asind associated 
    atan atan2 atan2d atand bitest bitl bitlr bitrl bjtest bit_size bktest break 
    btest cabs ccos cdabs cdcos cdexp cdlog cdsin cdsqrt ceiling cexp char 
    clog cmplx conjg cos cosd cosh count cpu_time cshift csin csqrt dabs 
    dacos dacosd dasin dasind datan datan2 datan2d datand date 
    date_and_time dble dcmplx dconjg dcos dcosd dcosh dcotan ddim dexp 
    dfloat dflotk dfloti dflotj digits dim dimag dint dlog dlog10 dmax1 dmin1 
    dmod dnint dot_product dprod dreal dsign dsin dsind dsinh dsqrt dtan dtand 
    dtanh eoshift epsilon errsns exp exponent float floati floatj floatk floor fraction 
    free huge iabs iachar iand ibclr ibits ibset ichar idate idim idint idnint ieor ifix 
    iiabs iiand iibclr iibits iibset iidim iidint iidnnt iieor iifix iint iior iiqint iiqnnt iishft 
    iishftc iisign ilen imax0 imax1 imin0 imin1 imod index inint inot int int1 int2 int4 
    int8 iqint iqnint ior ishft ishftc isign isnan izext jiand jibclr jibits jibset jidim jidint 
    jidnnt jieor jifix jint jior jiqint jiqnnt jishft jishftc jisign jmax0 jmax1 jmin0 jmin1 
    jmod jnint jnot jzext kiabs kiand kibclr kibits kibset kidim kidint kidnnt kieor kifix 
    kind kint kior kishft kishftc kisign kmax0 kmax1 kmin0 kmin1 kmod knint knot kzext 
    lbound leadz len len_trim lenlge lge lgt lle llt log log10 logical lshift malloc matmul 
    max max0 max1 maxexponent maxloc maxval merge min min0 min1 minexponent minloc 
    minval mod modulo mvbits nearest nint not nworkers number_of_processors pack popcnt 
    poppar precision present product radix random random_number random_seed range real 
    repeat reshape rrspacing rshift scale scan secnds selected_int_kind 
    selected_real_kind set_exponent shape sign sin sind sinh size sizeof sngl snglq spacing 
    spread sqrt sum system_clock tan tand tanh tiny transfer transpose trim ubound unpack verify
    """.split()

    # keywords3 are nonstardard, extended and user defined functions
    _keywords3 = """
    cdabs cdcos cdexp cdlog cdsin cdsqrt cotan cotand 
    dcmplx dconjg dcotan dcotand decode dimag dll_export dll_import doublecomplex dreal 
    dvchk encode find flen flush getarg getcharqq getcl getdat getenv gettim hfix ibchng 
    identifier imag int1 int2 int4 intc intrup invalop iostat_msg isha ishc ishl jfix 
    lacfar locking locnear map nargs nbreak ndperr ndpexc offset ovefl peekcharqq precfill 
    prompt qabs qacos qacosd qasin qasind qatan qatand qatan2 qcmplx qconjg qcos qcosd 
    qcosh qdim qexp qext qextd qfloat qimag qlog qlog10 qmax1 qmin1 qmod qreal qsign qsin 
    qsind qsinh qsqrt qtan qtand qtanh ran rand randu rewrite segment setdat settim system 
    timer undfl unlock union val virtual volatile zabs zcos zexp zlog zsin zsqrt
    """
    
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(components.interfaces.ISciMoz.SCLEX_F77)
            self._lexer.setKeywords(0, self._keywords1)
            self._lexer.setKeywords(1, self._keywords2)
            self._lexer.setKeywords(2, self._keywords3)
            self._lexer.supportsFolding = 1
        return self._lexer

    def getEncodingWarning(self, encoding):
        if not encoding.use_byte_order_marker:
            if encoding.python_encoding_name.startswith('utf-16') or encoding.python_encoding_name.startswith('ucs-'):
                return 'Including a signature (BOM) is recommended for "%s".' % encoding.friendly_encoding_name
            else:
                return ''
        else: # It's all good
            return ''
        
class koFortranLanguage(koFortran77Language):
    name = "Fortran"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{24736599-C6DD-4769-978C-C688710F0A1F}"
    _reg_categories_ = [("komodo-language", name)]

    defaultExtension = ".f95"
    commentDelimiterInfo = { "line": [ "!", "C " ]  }
    
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(components.interfaces.ISciMoz.SCLEX_FORTRAN)
            self._lexer.setKeywords(0, self._keywords1)
            self._lexer.setKeywords(1, self._keywords2)
            self._lexer.setKeywords(2, self._keywords3)
            self._lexer.supportsFolding = 1
        return self._lexer

