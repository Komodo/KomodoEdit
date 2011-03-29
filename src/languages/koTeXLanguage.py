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

class koTeXLanguage(KoLanguageBase):
    name = "TeX"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{5b8a7183-313e-4119-9649-347dce868e7d}"
    _reg_categories_ = [("komodo-language", name)]

    _stateMap = {
        'default': ('SCE_TEX_DEFAULT',),
        'special': ('SCE_TEX_SPECIAL',),
        'groups': ('SCE_TEX_GROUP',),
        'symbols': ('SCE_TEX_SYMBOL',),
        'commands': ('SCE_TEX_COMMAND',),
        'strings': ('SCE_TEX_TEXT',),
        }
    #file.patterns.tex=*.tex;*.sty;
    #file.patterns.latex=*.tex;*.sty;*.aux;*.toc;*.idx;
    #file.patterns.context=*.tex;*.tui;*.tuo;*.sty;
    defaultExtension = '.tex' 
    commentDelimiterInfo = {"line": [ "%" ]}
    
    sample = """
SAMPLE NOT AVAILABLE
"""    
    def __init__(self):
        KoLanguageBase.__init__(self)
        del self.matchingSoftChars["'"]
        del self.matchingSoftChars['"']
    
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(
                components.interfaces.ISciMoz.SCLEX_TEX)
            self._lexer.setKeywords(0, self._tex_all)
        return self._lexer

    # TeX: keywords (incomplete, just for testing and as example)
    _primitives_tex="""
        above abovedisplayshortskip abovedisplayskip
        abovewithdelims accent adjdemerits advance afterassignment
        aftergroup atop atopwithdelims
        badness baselineskip batchmode begingroup
        belowdisplayshortskip belowdisplayskip binoppenalty botmark
        box boxmaxdepth brokenpenalty
        catcode char chardef cleaders closein closeout clubpenalty
        copy count countdef cr crcr csname
        day deadcycles def defaulthyphenchar defaultskewchar
        delcode delimiter delimiterfactor delimeters
        delimitershortfall delimeters dimen dimendef discretionary
        displayindent displaylimits displaystyle
        displaywidowpenalty displaywidth divide
        doublehyphendemerits dp dump
        edef else emergencystretch end endcsname endgroup endinput
        endlinechar eqno errhelp errmessage errorcontextlines
        errorstopmode escapechar everycr everydisplay everyhbox
        everyjob everymath everypar everyvbox exhyphenpenalty
        expandafter 
        fam fi finalhyphendemerits firstmark floatingpenalty font
        fontdimen fontname futurelet
        gdef global group globaldefs
        halign hangafter hangindent hbadness hbox hfil horizontal
        hfill horizontal hfilneg hfuzz hoffset holdinginserts hrule
        hsize hskip hss horizontal ht hyphenation hyphenchar
        hyphenpenalty hyphen
        if ifcase ifcat ifdim ifeof iffalse ifhbox ifhmode ifinner
        ifmmode ifnum ifodd iftrue ifvbox ifvmode ifvoid ifx
        ignorespaces immediate indent input inputlineno input
        insert insertpenalties interlinepenalty
        jobname
        kern
        language lastbox lastkern lastpenalty lastskip lccode
        leaders left lefthyphenmin leftskip leqno let limits
        linepenalty line lineskip lineskiplimit long looseness
        lower lowercase
        mag mark mathaccent mathbin mathchar mathchardef mathchoice
        mathclose mathcode mathinner mathop mathopen mathord
        mathpunct mathrel mathsurround maxdeadcycles maxdepth
        meaning medmuskip message mkern month moveleft moveright
        mskip multiply muskip muskipdef
        newlinechar noalign noboundary noexpand noindent nolimits
        nonscript scriptscript nonstopmode nulldelimiterspace
        nullfont number
        omit openin openout or outer output outputpenalty over
        overfullrule overline overwithdelims
        pagedepth pagefilllstretch pagefillstretch pagefilstretch
        pagegoal pageshrink pagestretch pagetotal par parfillskip
        parindent parshape parskip patterns pausing penalty
        postdisplaypenalty predisplaypenalty predisplaysize
        pretolerance prevdepth prevgraf
        radical raise read relax relpenalty right righthyphenmin
        rightskip romannumeral
        scriptfont scriptscriptfont scriptscriptstyle scriptspace
        scriptstyle scrollmode setbox setlanguage sfcode shipout
        show showbox showboxbreadth showboxdepth showlists showthe
        skewchar skip skipdef spacefactor spaceskip span special
        splitbotmark splitfirstmark splitmaxdepth splittopskip
        string
        tabskip textfont textstyle the thickmuskip thinmuskip time
        toks toksdef tolerance topmark topskip tracingcommands
        tracinglostchars tracingmacros tracingonline tracingoutput
        tracingpages tracingparagraphs tracingrestores tracingstats
        uccode uchyph underline unhbox unhcopy unkern unpenalty
        unskip unvbox unvcopy uppercase
        vadjust valign vbadness vbox vcenter vfil vfill vfilneg
        vfuzz voffset vrule vsize vskip vsplit vss vtop
        wd widowpenalty write
        xdef xleaders xspaceskip
        year""".split()
    
    _primitives_etex="""
        beginL beginR botmarks
        clubpenalties currentgrouplevel currentgrouptype
        currentifbranch currentiflevel currentiftype
        detokenize dimexpr displaywidowpenalties
        endL endR eTeXrevision eTeXversion everyeof
        firstmarks fontchardp fontcharht fontcharic fontcharwd
        glueexpr glueshrink glueshrinkorder gluestretch
        gluestretchorder gluetomu
        ifcsname ifdefined iffontchar interactionmode
        interactionmode interlinepenalties
        lastlinefit lastnodetype
        marks topmarks middle muexpr mutoglue
        numexpr
        pagediscards parshapedimen parshapeindent parshapelength
        predisplaydirection
        savinghyphcodes savingvdiscards scantokens showgroups
        showifs showtokens splitdiscards splitfirstmarks
        TeXXeTstate tracingassigns tracinggroups tracingifs
        tracingnesting tracingscantokens
        unexpanded unless
        widowpenalties""".split()
    
    _primitives_pdftex="""
        pdfadjustspacing pdfannot pdfavoidoverfull
        pdfcatalog pdfcompresslevel
        pdfdecimaldigits pdfdest pdfdestmargin
        pdfendlink pdfendthread
        pdffontattr pdffontexpand pdffontname pdffontobjnum pdffontsize
        pdfhorigin
        pdfimageresolution pdfincludechars pdfinfo
        pdflastannot pdflastdemerits pdflastobj
        pdflastvbreakpenalty pdflastxform pdflastximage
        pdflastximagepages pdflastxpos pdflastypos
        pdflinesnapx pdflinesnapy pdflinkmargin pdfliteral
        pdfmapfile pdfmaxpenalty pdfminpenalty pdfmovechars
        pdfnames
        pdfobj pdfoptionpdfminorversion pdfoutline pdfoutput
        pdfpageattr pdfpageheight pdfpageresources pdfpagesattr
        pdfpagewidth pdfpkresolution pdfprotrudechars
        pdfrefobj pdfrefxform pdfrefximage
        pdfsavepos pdfsnaprefpoint pdfsnapx pdfsnapy pdfstartlink
        pdfstartthread
        pdftexrevision pdftexversion pdfthread pdfthreadmargin
        pdfuniqueresname
        pdfvorigin
        pdfxform pdfximage""".split()
    
    _primitives_omega="""
        odelimiter omathaccent omathchar oradical omathchardef omathcode odelcode
        leftghost rightghost
        charwd charht chardp charit
        localleftbox localrightbox
        localinterlinepenalty localbrokenpenalty
        pagedir bodydir pardir textdir mathdir
        boxdir nextfakemath
        pagewidth pageheight pagerightoffset pagebottomoffset
        nullocp nullocplist ocp externalocp ocplist pushocplist popocplist clearocplists ocptracelevel
        addbeforeocplist addafterocplist removebeforeocplist removeafterocplist
        OmegaVersion
        InputTranslation OutputTranslation DefaultInputTranslation DefaultOutputTranslation
        noInputTranslation noOutputTranslation
        InputMode OutputMode DefaultInputMode DefaultOutputMode
        noInputMode noOutputMode noDefaultInputMode noDefaultOutputMode""".split()
    
    # only the macros that make sense:
    
    _macros_plain_partial="""
        TeX
        bgroup egroup endgraf space empty null
        newcount newdimen newskip newmuskip newbox newtoks newhelp newread newwrite newfam newlanguage newinsert newif
        maxdimen magstephalf magstep
        frenchspacing nonfrenchspacing normalbaselines obeylines obeyspaces raggedright ttraggedright
        thinspace negthinspace enspace enskip quad qquad
        smallskip medskip bigskip removelastskip topglue vglue hglue
        break nobreak allowbreak filbreak goodbreak smallbreak medbreak bigbreak
        line leftline rightline centerline rlap llap underbar strutbox strut
        cases matrix pmatrix bordermatrix eqalign displaylines eqalignno leqalignno
        pageno folio tracingall showhyphens fmtname fmtversion
        hphantom vphantom phantom smash""".split()
    
    _macros_eplain_partial="""
        eTeX
        newmarks grouptype interactionmode nodetype iftype
        tracingall loggingall tracingnone""".split()
    
    _primitives_all= _primitives_tex + _primitives_etex + \
                     _primitives_pdftex + _primitives_omega

    # collections
    _tex_all= _primitives_tex + _macros_plain_partial
    
    _etex_all= _primitives_tex + _primitives_etex + \
               _macros_plain_partial + _macros_eplain_partial
    
    _latex_all= _primitives_tex + _primitives_etex

    _pdflatex_all= _primitives_tex + _primitives_etex + \
                   _primitives_pdftex

    # we can't use $(_primitives_all) here due to some kind of
    # limitation in nesting
    
    _context_all= _primitives_tex + _primitives_etex + \
                   _primitives_pdftex + _primitives_omega + \
                   _macros_plain_partial + _macros_eplain_partial
    
#TODO: Note koLatexLanguage is defined in koLatexLanguage.py as well, should probably
# win over this one.
class koLaTeXLanguage(koTeXLanguage):
    name = "LaTeX"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{a57119f8-6f19-40de-8e9e-cb0d2c139e32}"
    _reg_categories_ = [("komodo-language", name)]

    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(
                components.interfaces.ISciMoz.SCLEX_TEX)
            self._lexer.setKeywords(0, self._latex_all)
        return self._lexer

class koConTeXLanguage(koLaTeXLanguage):
    name = "ConTeX"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{2735fba9-940e-486d-825c-3d0bff0c709d}"
    _reg_categories_ = [("komodo-language", name)]
    defaultExtension = None

    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(
                components.interfaces.ISciMoz.SCLEX_TEX)
            self._lexer.setKeywords(0, self._context_all)
            self._lexer.setKeywords(1, []) # nl
            self._lexer.setKeywords(2, []) # en
            self._lexer.setKeywords(3, []) # de
            self._lexer.setKeywords(4, []) # cz
            self._lexer.setKeywords(5, []) # it
            self._lexer.setKeywords(6, []) # ro
            self._lexer.setKeywords(7, self._pdflatex_all)
        return self._lexer

