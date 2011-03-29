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

class koTADS3Language(KoLanguageBase):
    name = "TADS3"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{371E0FF4-53F0-11DA-915F-000D935D3368}"
    _reg_categories_ = [("komodo-language", name)]

    commentDelimiterInfo = {
        "line": [ "//" ],
        "block": [ ("/*", "*/") ],
        "markup": "*",
    }

    defaultExtension = ".tads3" 

    supportsSmartIndent = "brace"
    sciMozLexer = components.interfaces.ISciMoz.SCLEX_TADS3

    _stateMap = {
        'default': ('SCE_T3_DEFAULT', 'SCE_T3_X_DEFAULT', 'SCE_T3_HTML_DEFAULT',),
        'keywords': ('SCE_T3_KEYWORD',),
        'identifiers': ('SCE_T3_IDENTIFIER',),
        'comments': ('SCE_T3_BLOCK_COMMENT','SCE_T3_LINE_COMMENT',),
        'operators': ('SCE_T3_OPERATOR',),
        'numbers': ('SCE_T3_NUMBER',),
        'strings': ('SCE_T3_S_STRING', 'SCE_T3_D_STRING', 'SCE_T3_X_STRING',
                    'SCE_T3_HTML_STRING',),
        'directives': ('SCE_T3_LIB_DIRECTIVE',),
        'params': ('SCE_T3_MSG_PARAM',),
        'tags': ('SCE_T3_HTML_TAG',),
        'user': ('SCE_T3_USER1', 'SCE_T3_USER2', 'SCE_T3_USER3',),
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
            self._lexer.setKeywords(3, self._keywords4)
            self._lexer.supportsFolding = 1
        return self._lexer

    _keywords = """
        break
        case
        catch
        class
        continue
        default
        definingobj
        delegated
        dictionary
        do
        else
        enum
        export
        extern
        finally
        for
        foreach
        goto
        grammar
        if
        inherited
        local
        new
        nil
        property
        propertyset
        return
        say
        self
        static
        switch
        targetobj
        targetprop
        template
        throw
        true
        try
        while
    """.split()

    _keywords2 = """
        __DEBUG
        _BYTEARR_H_
        _CHARSET_H_
        _DICT_H_
        _FILE_H_
        _GRAMPROD_H_
        _LOOKUP_H_
        _VECTOR_H_
        abortImplicit
        actorStateDobjFor
        actorStateIobjFor
        actorStateObjFor
        ADV3_H
        AlwaysAnnounce
        AnnouncedDefaultObject
        asDobjFor
        asDobjWithoutActionFor
        asExit
        asIobjFor
        asIobjWithoutActionFor
        askForDobj
        askForIobj
        askForLiteral
        askForTopic
        asObjFor
        asObjWithoutActionFor
        BannerAfter
        BannerAlignBottom
        BannerAlignLeft
        BannerAlignRight
        BannerAlignTop
        BannerBefore
        BannerFirst
        BannerLast
        BannerSizeAbsolute
        BannerSizePercent
        BannerStyleAutoHScroll
        BannerStyleAutoVScroll
        BannerStyleBorder
        BannerStyleHScroll
        BannerStyleMoreMode
        BannerStyleTabAlign
        BannerStyleVScroll
        BannerTypeText
        BannerTypeTextGrid
        BaseDefineTopicTAction
        breakLoop
        canInherit
        canInheritNext
        CharsetDisplay
        CharsetFileCont
        CharsetFileName
        ClearDisambig
        ColorAqua
        ColorBlack
        ColorBlue
        ColorCyan
        ColorFuchsia
        ColorGray
        ColorGreen
        ColorInput
        ColorLime
        ColorMagenta
        ColorMaroon
        ColorNavy
        ColorOlive
        ColorPurple
        ColorRed
        ColorRGB
        ColorSilver
        ColorStatusBg
        ColorStatusText
        ColorTeal
        ColorText
        ColorTextBg
        ColorTransparent
        ColorWhite
        ColorYellow
        cosmeticSpacingReport
        dbgShowGrammarList
        dbgShowGrammarWithCaption
        dangerous
        defaultDescReport
        DefaultObject
        defaultReport
        defDigit
        DefineAction
        DefineConvIAction
        DefineConvTopicTAction
        DefineDirection
        DefineIAction
        DefineLangDir
        DefineLiteralAction
        DefineLiteralTAction
        DefineSystemAction
        DefineTAction
        DefineTIAction
        DefineTIActionSub
        DefineTopicAction
        DefineTopicTAction
        defOrdinal
        defTeen
        defTens
        DigitFormatGroupComma
        DigitFormatGroupPeriod
        DigitFormatGroupSep
        DirPhrase
        dobjFor
        dobjList
        EndsWithAdj
        exit
        exitAction
        extraReport
        FileAccessRead
        FileAccessReadWrite
        FileAccessReadWriteKeep
        FileAccessReadWriteTrunc
        FileAccessWrite
        FileTypeBin
        FileTypeCmd
        FileTypeData
        FileTypeLog
        FileTypeT3Image
        FileTypeT3Save
        FileTypeText
        FileTypeUnknown
        FirstPerson
        FmtBigEndian
        FmtInt8
        FmtInt16BE
        FmtInt16LE
        FmtInt32BE
        FmtInt32LE
        FmtLittleEndian
        FmtSigned
        FmtSize8
        FmtSize16
        FmtSize32
        FmtUInt8
        FmtUInt16BE
        FmtUInt16LE
        FmtUnsigned
        gAction
        gActionIs
        gActor
        gCommandReports
        gDobj
        GetTimeDateAndTime
        GetTimeTicks
        getTokOrig
        getTokType
        getTokVal
        gExitLister
        gHintManager
        gIobj
        gIsNonDefaultReport
        gIssuingActor
        gLiteral
        gMessageParams
        gPlayerChar
        gReveal
        gRevealed
        gSetKnown
        gTentativeDobj
        gTentativeIobj
        gTopic
        gTranscript
        gVerifyResults
        HtmlifyKeepNewlines
        HtmlifyKeepSpaces
        HtmlifyKeepTabs
        HtmlifyKeepWhitespace
        HtmlifyTranslateSpaces
        HtmlifyTranslateTabs
        illogical
        illogicalAlready
        illogicalNow
        illogicalSelf
        inaccessible
        InDlgIconInfo
        InDlgIconError
        InDlgIconNone
        InDlgIconQuestion
        InDlgIconWarning
        InDlgLblCancel
        InDlgLblNo
        InDlgLblOk
        InDlgLblYes
        InDlgOk
        InDlgOkCancel
        InDlgYesNo
        InDlgYesNoCancel
        InEvtEndQuietScript
        InEvtEof
        InEvtHref
        InEvtKey
        InEvtLine
        InEvtNoTimeout
        InEvtTimeout
        InFileCancel
        InFileFailure
        InFileOpen
        InFileSave
        InFileSuccess
        inheritNext
        iobjFor
        iobjList
        ListContents
        ListCustomFlag
        ListLong
        ListRecurse
        ListTall
        ListerCustomFlag
        LiteralPhrase
        logical
        logicalRank
        logicalRankOrd
        LogTypeTranscript
        LogTypeCommand
        LookListPortables
        LookListSpecials
        LookRoomDesc
        LookRoomName
        M_QUIT
        M_PREV
        M_UP
        M_DOWN
        M_SEL
        mainReport
        mapPushTravelHandlers
        mapPushTravelIobj
        MatchedAll
        maybeRemapTo
        nestedAction
        nestedActorAction
        newAction
        newActorAction
        nonObvious
        NumberPhrase
        ObjAll
        ObjClasses
        objFor
        ObjInstances
        PARSER_DEBUG
        perInstance
        PluralTruncated
        PropDefAny
        PropDefDirectly
        PropDefGetClass
        PropDefInherits
        remapTIAction
        remapTo
        replaceAction
        replaceActorAction
        ReplaceAll
        ReplaceOnce
        reportAfter
        reportBefore
        reportFailure
        reportQuestion
        ScriptFileNonstop
        ScriptFileQuiet
        SecondPerson
        SENSE_CACHE
        singleDir
        singleDobj
        singleIobj
        singleLiteral
        singleNumber
        singleTopic
        SortAsc
        SortDesc
        SpellIntAndTens
        SpellIntCommas
        SpellIntTeenHundreds
        StatModeNormal
        StatModeStatus
        StrCompCaseFold
        StrCompMatch
        StrCompTrunc
        SysInfoBanners
        SysInfoHtml
        SysInfoHtmlMode
        SysInfoIClassHTML
        SysInfoIClassText
        SysInfoIClassTextGUI
        SysInfoInterpClass
        SysInfoJpeg
        SysInfoLinksFtp
        SysInfoLinksHttp
        SysInfoLinksMailto
        SysInfoLinksNews
        SysInfoLinksTelnet
        SysInfoMidi
        SysInfoMidiOvl
        SysInfoMng
        SysInfoMngTrans
        SysInfoMpeg
        SysInfoMpeg1
        SysInfoMpeg2
        SysInfoMpeg3
        SysInfoOgg
        SysInfoOsName
        SysInfoPng
        SysInfoPngAlpha
        SysInfoPngTrans
        SysInfoPrefImages
        SysInfoPrefLinks
        SysInfoPrefMusic
        SysInfoPrefSounds
        SysInfoTextColors
        SysInfoTextHilite
        SysInfoTxcAnsiFg
        SysInfoTxcAnsiFgBg
        SysInfoTxcNone
        SysInfoTxcParam
        SysInfoTxcRGB
        SysInfoVersion
        SysInfoWave
        SysInfoWavMidiOvl
        SysInfoWavOvl
        T3_H
        T3DebugBreak
        T3DebugCheck
        T3SetSayNoFunc
        T3SetSayNoMethod
        TADS_IO_HEADER
        tads_io_say
        TADSGEN_H
        TADSIO_H
        ThirdPerson
        tokRuleName
        tokRulePat
        tokRuleType
        tokRuleVal
        tokRuleTest
        TopicPhrase
        tryImplicitAction
        tryImplicitActionMsg
        TypeCode
        TypeEnum
        TypeFuncPtr
        TypeDString
        TypeInt
        TypeList
        TypeNativeCode
        TypeNil
        TypeObject
        TypeProp
        TypeSString
        TypeTrue
        UnclearDisambig
        VerbRule
        verifyNotSelfInherit
        VocabTruncated
    """.split()

    _keywords3 = """
        BigNumber
        ByteArray
        CharacterSet
        Collection
        Dictionary
        File
        function
        GrammarProd
        IntrinsicClass
        Iterator
        List
        LookupTable
        object
        Object
        RexPattern
        String
        StringComparator
        TadsObject
        Vector
        WeakRefLookupTable
        clearScreen
        dataType
        firstObj
        flushOutput
        getArg
        getFuncParams
        getLocalCharSet
        getTime
        inputDialog
        inputEvent
        inputFile
        inputKey
        inputLine
        inputLineCancel
        inputLineTimeout
        makeString
        max
        min
        morePrompt
        nextObj
        rand
        randomize
        resExists
        restartGame
        restoreGame
        rexGroup
        rexMatch
        rexReplace
        rexSearch
        saveGame
        savepoint
        setLogFile
        setScriptFile
        statusMode
        statusRight
        systemInfo
        t3AllocProp
        t3DebugTrace
        t3GetGlobalSymbols
        t3GetStackTrace
        t3GetVMBanner
        t3GetVMID
        t3GetVMPreinitMode
        t3GetVMVsn
        t3RunGC
        t3SetSay
        tadsSay
        timeDelay
        toInteger
        toString
        undo
    """.split()

    _keywords4 = """
        modify
        replace
        define
        error
        include
        elif
        if
        line
        else
        ifdef
        pragma
        endif
        ifndef
        undef
        if
        else
        endif
        charset
        """.split()
