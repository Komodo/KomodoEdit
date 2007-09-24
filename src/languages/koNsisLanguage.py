from xpcom import components, ServerException

from koLanguageServiceBase import *

def registerLanguage(registery):
    registery.registerLanguage(koNsisLanguage())

class koNsisLanguage(KoLanguageBase):
    name = "Nsis"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" % (name)
    _reg_clsid_ = "{fe5b419f-c978-4bbe-8fc0-0c54313387c1}"

    _stateMap = {
        'default': ('SCE_NSIS_DEFAULT',),
        'defines': ('SCE_NSIS_USERDEFINED',
                    'SCE_NSIS_SECTIONDEF',
                    'SCE_NSIS_SUBSECTIONDEF',
                    'SCE_NSIS_IFDEFINEDEF'),
        'macros': ('SCE_NSIS_MACRODEF',),
        'comments': ('SCE_NSIS_COMMENT',),
        'numbers': ('SCE_NSIS_NUMBER',),
        'strings': ('SCE_NSIS_STRINGDQ',
                    'SCE_NSIS_STRINGLQ',
                    'SCE_NSIS_STRINGRQ',
                    'SCE_NSIS_STRINGVAR',),
        'functions': ('SCE_NSIS_FUNCTION',),
        'variables': ('SCE_NSIS_VARIABLE',),
        'labels': ('SCE_NSIS_LABEL',),
        }

    defaultExtension = '.nsi'
    commentDelimiterInfo = {}
    
    sample = """
SAMPLE NOT AVAILABLE
"""
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(
                components.interfaces.ISciMoz.SCLEX_NSIS)
            self._lexer.setKeywords(0, self._keywords)
            self._lexer.setKeywords(1, self._keywords2)
            self._lexer.setKeywords(2, self._keywords3)
        return self._lexer

    # Functions:
    _keywords="""What Abort AddSize AllowRootDirInstall AutoCloseWindow
        BGGradient BrandingText BringToFront CRCCheck Call CallInstDLL Caption ClearErrors
        CompletedText ComponentText CopyFiles CreateDirectory CreateShortCut Delete
        DeleteINISec DeleteINIStr DeleteRegKey DeleteRegValue DetailPrint DetailsButtonText
        DirShow DirText DisabledBitmap EnabledBitmap EnumRegKey EnumRegValue Exch Exec
        ExecShell ExecWait ExpandEnvStrings File FileClose FileErrorText FileOpen FileRead
        FileReadByte FileSeek FileWrite FileWriteByte FindClose FindFirst FindNext FindWindow
        Function FunctionEnd GetCurrentAddress GetDLLVersionLocal GetDllVersion GetFileTime
        GetFileTimeLocal GetFullPathName GetFunctionAddress GetLabelAddress GetTempFileName
        Goto HideWindow Icon IfErrors IfFileExists IfRebootFlag InstProgressFlags InstType
        InstallButtonText InstallColors InstallDir InstallDirRegKey IntCmp IntCmpU IntFmt IntOp
        IsWindow LicenseData LicenseText MessageBox MiscButtonText Name OutFile Pop Push
        Quit RMDir ReadEnvStr ReadINIStr ReadRegDword ReadRegStr Reboot RegDLL Rename
        Return SearchPath Section SectionDivider SectionEnd SectionIn SendMessage SetAutoClose
        SetCompress SetCompressor SetDatablockOptimize SetDateSave SetDetailsPrint SetDetailsView SetErrors
        SetFileAttributes SetOutPath SetOverwrite SetRebootFlag ShowInstDetails ShowUninstDetails
        SilentInstall SilentUnInstall Sleep SpaceTexts StrCmp StrCpy StrLen SubCaption UnRegDLL
        UninstallButtonText UninstallCaption UninstallEXEName UninstallIcon UninstallSubCaption
        UninstallText WindowIcon WriteINIStr WriteRegBin WriteRegDword WriteRegDWORD WriteRegExpandStr
        WriteRegStr WriteUninstaller SectionGetFlags SectionSetFlags SectionSetText SectionGetText
        LogText LogSet CreateFont SetShellVarContext SetStaticBkColor SetBrandingImage PluginDir
        SubSectionEnd SubSection CheckBitmap ChangeUI SetFont AddBrandingImage XPStyle Var
        LangString !define !undef !ifdef !ifndef !endif !else !macro !echo !warning !error !verbose
        !macroend !insertmacro !system !include !cd !packhdr !addplugindir""".split()
    
    # Variables:
    _keywords2="""$0 $1 $2 $3 $4 $5 $6 $7 $8 $9
        $R0 $R1 $R2 $R3 $R4 $R5 $R6 $R7 $R8 $R9 $CMDLINE $DESKTOP
        $EXEDIR $HWNDPARENT $INSTDIR $OUTDIR $PROGRAMFILES ${NSISDIR} $\n $\r
        $QUICKLAUNCH $SMPROGRAMS $SMSTARTUP $STARTMENU $SYSDIR $TEMP $WINDIR""".split()
    
    # Lables:
    _keywords3="""ARCHIVE FILE_ATTRIBUTE_ARCHIVE FILE_ATTRIBUTE_HIDDEN
        FILE_ATTRIBUTE_NORMAL FILE_ATTRIBUTE_OFFLINE FILE_ATTRIBUTE_READONLY
        FILE_ATTRIBUTE_SYSTEM FILE_ATTRIBUTE_TEMPORARY HIDDEN HKCC HKCR HKCU
        HKDD HKEY_CLASSES_ROOT HKEY_CURRENT_CONFIG HKEY_CURRENT_USER HKEY_DYN_DATA
        HKEY_LOCAL_MACHINE HKEY_PERFORMANCE_DATA HKEY_USERS HKLM HKPD HKU IDABORT
        IDCANCEL IDIGNORE IDNO IDOK IDRETRY IDYES MB_ABORTRETRYIGNORE MB_DEFBUTTON1
        MB_DEFBUTTON2 MB_DEFBUTTON3 MB_DEFBUTTON4 MB_ICONEXCLAMATION
        MB_ICONINFORMATION MB_ICONQUESTION MB_ICONSTOP MB_OK MB_OKCANCEL
        MB_RETRYCANCEL MB_RIGHT MB_SETFOREGROUND MB_TOPMOST MB_YESNO MB_YESNOCANCEL
        NORMAL OFFLINE READONLY SW_SHOWMAXIMIZED SW_SHOWMINIMIZED SW_SHOWNORMAL
        SYSTEM TEMPORARY auto colored false force hide ifnewer nevershow normal
        off on show silent silentlog smooth true try""".split()

