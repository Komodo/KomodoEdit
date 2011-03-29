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

# see http://caml.inria.fr/
class koCsoundLanguage(KoLanguageBase):
    name = "Csound"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{24986A86-53E8-11DA-8731-000D935D3368}"
    _reg_categories_ = [("komodo-language", name)]

    commentDelimiterInfo = {}

    # file.patterns.csound=*.orc;*.sco;*.csd
    defaultExtension = ".orc" # and .mli

    supportsSmartIndent = "brace"
    sciMozLexer = components.interfaces.ISciMoz.SCLEX_CSOUND

    _stateMap = {
        'default': ('SCE_CSOUND_DEFAULT',),
        'keywords': ('SCE_CSOUND_USERKEYWORD',),
        'identifiers': ('SCE_CSOUND_IDENTIFIER',),
        'comments': ('SCE_CSOUND_COMMENT','SCE_CSOUND_COMMENTBLOCK',),
        'operators': ('SCE_CSOUND_OPERATOR',),
        'numbers': ('SCE_CSOUND_NUMBER',),
        'strings': ('SCE_CSOUND_STRINGEOL',),
        'variables': ('SCE_CSOUND_GLOBAL_VAR', 'SCE_CSOUND_ARATE_VAR',
                      'SCE_CSOUND_KRATE_VAR', 'SCE_CSOUND_IRATE_VAR',),
        'opcode': ('SCE_CSOUND_OPCODE',),
        'parameters': ('SCE_CSOUND_PARAM',),
        'statements': ('SCE_CSOUND_HEADERSTMT',),
        'instructions': ('SCE_CSOUND_INSTR',),
        }
    sample = """
SAMPLE NOT AVAILABLE
"""

    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(self.sciMozLexer)
            self._lexer.setKeywords(0, self._keywords)
            self._lexer.setKeywords(1, self._keywords2)
            self._lexer.setKeywords(2, self._keywords3)
            self._lexer.supportsFolding = 1
        return self._lexer

    _keywords = """
        a i db in or zr Add Dec Div Inc Mul Sub abs and cos dam dec div exp
        fin fof fog inh ino inq ins int inx inz lfo log mac mod mul not out
        pan pow rms rnd shl sin sqr sub sum tab tan tb0 tb1 tb2 tb3 tb4 tb5
        tb6 tb7 tb8 tb9 urd vco xin xor zar zaw zir ziw zkr zkw adsr babo
        buzz cent clip comb cosh diff divz fini fink fmb3 fof2 fold fout
        frac ftsr gain goto in32 inch init line maca moog mute nrpn outc
        outh outo outq outs outx outz peak port pset pvoc rand seed sinh
        sqrt stix tabw tanh tb10 tb11 tb12 tb13 tb14 tb15 tone vadd vco2
        vdiv vexp vibr vmap vmul vpow wrap xout xyin zacl zarg zawm ziwm
        zkcl zkwm FLbox FLjoy FLrun adsyn ampdb atone birnd bqrez butbp
        butbr buthp butlp clear ctrl7 dbamp dconv delay dumpk endin endop
        event expon fouti foutk ftgen ftlen gauss gbuzz grain guiro igoto
        ihold instr integ kgoto limit linen log10 loopg loopl lpf18 madsr
        max_k metro noise nsamp oscil out32 outch outic outkc outq1 outq2
        outq3 outq4 outs1 outs2 pareq pitch pluck portk print pvadd randh
        randi rbjeq readk reson rezzy rnd31 scans scanu sense space tab_i
        table tbvcf tempo timek times tival tonek tonex vaddv vbap4 vbap8
        vbapz vcomb vcopy vdecr vdivv veloc vexpv vibes vincr vmult voice
        vport vpowv vpvoc vsubv vwrap wgbow xadsr zamod zkmod FLhide FLkeyb
        FLknob FLpack FLshow FLtabs FLtext active adsynt alpass areson
        atonek atonex bamboo bbcutm bbcuts biquad cabasa cauchy cggoto
        cigoto ckgoto clfilt cngoto convle cosinv cpsoct cpspch cpstun
        cpuprc cross2 crunch ctrl14 ctrl21 delay1 delayk delayr delayw
        deltap denorm diskin dumpk2 dumpk3 dumpk4 envlpx expseg filesr
        fiopen fmbell follow foscil foutir ftlen2 ftload ftmorf ftsave
        grain2 grain3 harmon hrtfer initc7 interp jitter linenr lineto
        linseg locsig loopge loople lorenz loscil lowres lpread lpslot
        mandel mandol mclock mdelay midic7 midiin midion mirror moscil
        mpulse mrtmsg mxadsr nlfilt noteon notnum ntrpol octave octcps
        octpch opcode oscbnk oscil1 oscil3 oscili osciln oscils oscilx
        outiat outipb outipc outkat outkpb outkpc pchoct phasor planet
        poscil printk prints pvread pvsftr pvsftw random readk2 readk3
        readk4 reinit resonk resonr resonx resony resonz reverb rigoto
        s16b14 s32b14 sekere sfload sfplay shaker sininv spat3d spdist
        spsend strset table3 tablei tablew tabw_i taninv tigoto timout
        turnon upsamp vbap16 vcella vco2ft vdel_k vdelay vlimit vmultv
        vrandh vrandi wgclar xscans xscanu FLcolor FLcount FLgroup FLlabel
        FLpanel FLvalue aftouch ampdbfs ampmidi aresonk balance bexprnd
        biquada changed clockon cps2pch cpsmidi cpstmid cpstuni cpsxpch
        dbfsamp dcblock deltap3 deltapi deltapn deltapx dispfft display
        envlpxr exprand expsega expsegr filelen filter2 flanger fmmetal
        fmrhode fmvoice follow2 foscili fprints ftchnls ftloadk ftlptim
        ftsavek gogobel granule hilbert initc14 initc21 invalue jitter2
        jspline linrand linsegr locsend logbtwo loopseg loscil3 lowresx
        lphasor lposcil lpreson lpshold marimba massign midic14 midic21
        midichn midion2 midiout moogvcf noteoff nreverb nstrnum octmidi
        oscil1i outic14 outipat outkc14 outkpat pcauchy pchbend pchmidi
        phaser1 phaser2 pinkish poisson polyaft poscil3 printk2 printks
        product pvcross pvsanal pvsinfo pvsynth randomh randomi release
        repluck reverb2 rspline rtclock seqtime sfilist sfinstr sfplay3
        sfplaym sfplist slider8 sndwarp soundin spat3di spat3dt specsum
        streson tableiw tablekt tableng tablera tablewa taninv2 tempest
        tlineto transeg trigger trigseq trirand turnoff unirand valpass
        vco2ift vdelay3 vdelayk vdelayx vexpseg vibrato vlinseg vlowres
        vmirror waveset weibull wgbrass wgflute wgpluck wguide1 wguide2
        xtratim zakinit FLbutton FLcolor2 FLprintk FLroller FLscroll
        FLsetBox FLsetVal FLslider FLupdate betarand butterbp butterbr
        butterhp butterlp chanctrl clockoff convolve cpsmidib ctrlinit
        cuserrnd deltapxw distort1 downsamp duserrnd filepeak fmpercfl
        fmwurlie fprintks hsboscil lowpass2 lpfreson lpinterp lposcil3
        maxalloc midictrl multitap nestedap octmidib oscilikt outvalue
        pchmidib powoftwo prealloc pvinterp pvsadsyn pvscross pvsfread
        pvsmaska rireturn samphold schedule semitone sensekey setksmps
        sfinstr3 sfinstrm sfplay3m sfpreset slider16 slider32 slider64
        slider8f soundout specaddm specdiff specdisp specfilt spechist
        specptrk specscal spectrum sprintks subinstr svfilter tablegpw
        tableikt tablemix tableseg tablewkt tablexkt tb0_init tb1_init
        tb2_init tb3_init tb4_init tb5_init tb6_init tb7_init tb8_init
        tb9_init tempoval vco2init vdelayxq vdelayxs vdelayxw vecdelay
        wgpluck2 wterrain xscanmap zfilter2 FLbutBank FLgetsnap FLpackEnd
        FLprintk2 FLsetFont FLsetSize FLsetText FLsetsnap FLslidBnk
        FLtabsEnd dripwater eventname ktableseg noteondur osciliktp
        oscilikts pgmassign phasorbnk pitchamdf pvbufread readclock
        sandpaper scantable schedwhen sfinstr3m sfpassign slider16f
        slider32f slider64f sndwarpst soundoutc soundouts tablecopy
        tableigpw tableimix tablexseg tb10_init tb11_init tb12_init
        tb13_init tb14_init tb15_init timeinstk timeinsts vbap4move
        vbap8move vbapzmove vdelayxwq vdelayxws xscansmap FLgroupEnd
        FLloadsnap FLpack_end FLpanelEnd FLsavesnap FLsetAlign FLsetColor
        FLsetVal_i FLtabs_end filenchnls noteondur2 scanhammer schedkwhen
        tableicopy tambourine vbap16move vbaplsinit wgbowedbar FLgroup_end
        FLpanel_end FLscrollEnd FLsetColor2 mididefault midinoteoff
        sleighbells FLscroll_end subinstrinit FLsetPosition FLsetTextSize
        FLsetTextType midinoteoncps midinoteonkey midinoteonoct
        midinoteonpch midipitchbend schedwhenname FLsetTextColor
        schedkwhenname midicontrolchange midiprogramchange
        midipolyaftertouch midichannelaftertouch
    """.split()
    
    _keywords2 = "sr kr ar ksmps nchnls".split()
    _keywords3 = ""
