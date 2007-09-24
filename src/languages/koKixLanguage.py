from xpcom import components, ServerException

from koLanguageServiceBase import *

# KiXtart info at kixtart.org

# KiXtart is a logon script processor and enhanced batch scripting
# language for computers running Windows XP, Windows 2000, Windows
# NT or Windows 9x in a Windows Networking environment.

def registerLanguage(registery):
    registery.registerLanguage(koKixLanguage())
    
class koKixLanguage(KoLanguageBase):
    name = "Kix"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{fad493c5-33a3-4ad3-bb99-ed5e86f42918}"

    _stateMap = {
        'default': ('SCE_KIX_DEFAULT',),
        'strings': ('SCE_KIX_STRING1',
                    'SCE_KIX_STRING2',),
        'numbers': ('SCE_KIX_NUMBER',),
        'comments': ('SCE_KIX_COMMENT',),
        'variables': ('SCE_KIX_VAR',),
        'keywords': ('SCE_KIX_KEYWORD',),
        'operators': ('SCE_KIX_OPERATOR',),
        'functions': ('SCE_KIX_FUNCTIONS',),
        'macros': ('SCE_KIX_MACRO',),
        'identifiers': ('SCE_KIX_IDENTIFIER',),
    }
    defaultExtension = '.kix'
    commentDelimiterInfo = {"line": [ ";" ]}
    
    sample = """
$strComputer = "."
$objWMIService = GetObject("winmgmts:\\" + $strComputer + "\root\cimv2")
$colServices = $objWMIService.ExecQuery("Select * from Win32_Service")

For Each $objService in $colServices
    ? $objService.Name + " -- " + $objService.State
Next
"""

    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(
                components.interfaces.ISciMoz.SCLEX_KIX)
            self._lexer.setKeywords(0, self._keywords)
            self._lexer.setKeywords(0, self._keywords2)
            self._lexer.setKeywords(0, self._keywords3)
        return self._lexer

    # These keywords are commands
    _keywords="""? and beep big break call cd cls color cookie1 copy 
        debug del dim display do until exit flushkb for each next function endfunction 
        get gets global go gosub goto if else endif md or password play quit 
        rd redim return run select case endselect set setl setm settime 
        shell sleep small use while loop""".split()

    # This keywords are functions
    _keywords2="""abs addkey addprinterconnection addprogramgroup 
        addprogramitem asc ascan at backupeventlog box cdbl chr cint cleareventlog 
        close comparefiletimes createobject cstr dectohex delkey delprinterconnection 
        delprogramgroup delprogramitem deltree delvalue dir enumgroup enumipinfo enumkey 
        enumlocalgroup enumvalue execute exist existkey expandenvironmentvars fix 
        formatnumber freefilehandle getdiskspace getfileattr getfilesize getfiletime 
        getfileversion getobject iif ingroup instr instrrev int isdeclared join 
        kbhit keyexist lcase left len loadhive loadkey logevent logoff ltrim 
        memorysize messagebox open readline readprofilestring readtype readvalue 
        redirectoutput right rnd round rtrim savekey sendkeys sendmessage setascii 
        setconsole setdefaultprinter setfileattr setfocus setoption setsystemstate 
        settitle setwallpaper showprogramgroup shutdown sidtoname split srnd substr 
        trim ubound ucase unloadhive val vartype vartypename writeline 
        writeprofilestring writevalue""".split()

    # This keywords are macros if preceeded by @
    _keywords3="""address build color comment cpu crlf csd curdir 
        date day domain dos error fullname homedir homedrive homeshr hostname 
        inwin ipaddress0 ipaddress1 ipaddress2 ipaddress3 kix lanroot ldomain 
        ldrive lm logonmode longhomedir lserver maxpwage mdayno mhz monthno 
        month msecs pid primarygroup priv productsuite producttype pwage ras 
        result rserver scriptdir scriptexe scriptname serror sid site startdir 
        syslang ticks time userid userlang wdayno wksta wuserid ydayno
        year""".split()


