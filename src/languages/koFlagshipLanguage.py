from xpcom import components, ServerException

from koLanguageServiceBase import *

def registerLanguage(registery):
    registery.registerLanguage(koFlagshipLanguage())

# see http://fship.com/
class koFlagshipLanguage(KoLanguageBase):
    name = "Flagship"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{995A405E-5549-11DA-A58F-000D935D3368}"

    commentDelimiterInfo = {
        "line": [ "//~" ],
        "block": [ ("/*", "*/") ],
        "markup": "*",
    }

    defaultExtension = ".prg" 

    supportsSmartIndent = "brace"
    sciMozLexer = components.interfaces.ISciMoz.SCLEX_FLAGSHIP

    _stateMap = {
        'default': ('SCE_FS_DEFAULT',),
        'keywords': ('SCE_FS_KEYWORD', 'SCE_FS_KEYWORD2', 'SCE_FS_KEYWORD3',
                     'SCE_FS_KEYWORD4',),
        'identifiers': ('SCE_FS_IDENTIFIER',),
        'comments': ('SCE_FS_COMMENT','SCE_FS_COMMENTLINE',
                     'SCE_FS_COMMENTDOC', 'SCE_FS_COMMENTLINEDOC',
                     'SCE_FS_COMMENTDOCKEYWORD', 'SCE_FS_COMMENTDOCKEYWORDERROR',),
        'operators': ('SCE_FS_OPERATOR',),
        'numbers': ('SCE_FS_NUMBER', 'SCE_FS_HEXNUMBER', 'SCE_FS_BINNUMBER',),
        'strings': ('SCE_FS_STRING', 'SCE_FS_STRINGEOL',),
        'constants': ('SCE_FS_CONSTANT',),
        'preprocessor': ('SCE_FS_PREPROCESSOR',),
        'date': ('SCE_FS_DATE',),
        'asm': ('SCE_FS_ASM',),
        'label': ('SCE_FS_LABEL',),
        'error': ('SCE_FS_ERROR',),
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
        ? @ accept access all alternate announce ansi any append as assign autolock average
        begin bell bitmap blank box
        call cancel case century charset checkbox clear close cls color combobox commit
        confirm console constant continue copy count create cursor
        date dbread dbwrite decimals declare default delete deleted delimiters device dir
        directory display do draw
        edit else elseif eject end endcase enddo endif endtext epoch erase error escape eval eventmask
        exact exclusive extended external extra
        field file filter find fixed font for form format from
        get gets global global_extern go goto gotop guialign guicolor guicursor guitransl
        html htmltext
        if image index input intensity
        join
        key keyboard keytransl
        label lines list listbox local locate
        margin memory memvar menu message method multibyte multilocks
        next nfs nfslock nfs_force note
        on openerror order outmode
        pack parameters path pixel pop printer private prompt public push pushbutton
        quit
        radiobutton radiogroup read recall refresh reindex relation release rename replace report request restore
        richtext rowadapt rowalign run
        save say scoreboard scrcompress screen seek select sequence set setenhanced setstandard setunselected
        skip softseek sort source static store struct structure sum
        tag tbrowse text to total type typeahead
        unique unlock update use
        wait while with wrap
        xml zap zerobyteout
    """.split()
    
    _keywords2 = """
        _displarr _displarrerr _displarrstd _displobj _displobjerr _displobjstd
        aadd abs achoice aclone acopy adel adir aelemtype aeval afields afill ains alert alias alltrim altd ansi2oem
        appiomode appmdimode appobject array asc ascan asize asort at atail atanychar autoxlock
        between bin2i bin2l bin2w binand binlshift binor binrshift binxor bof break browse
        cdow chr chr2screen cmonth col col2pixel color2rgb colorselect colvisible consoleopen consolesize crc32 ctod curdir
        date datevalid day dbappend dbclearfilter dbclearindex dbclearrelation dbcloseall dbclosearea dbcommit dbcommitall
        dbcreate dbcreateindex dbdelete dbedit dbeval dbf dbfilter dbfinfo dbflock dbfused dbgetlocate dbgobottom dbgoto
        dbgotop dbobject dbrecall dbreindex dbrelation dbrlock dbrlocklist dbrselect dbrunlock dbseek dbselectarea
        dbsetdriver dbsetfilter dbsetindex dbsetlocate dbsetorder dbsetrelation dbskip dbstruct dbunlock dbunlockall
        dbusearea default deleted descend devout devoutpict devpos directory diskspace dispbegin dispbox dispcount
        dispend dispout doserror doserror2str dow drawline dtoc dtos
        empty eof errorblock errorlevel eval execname execpidnum exp
        fattrib fclose fcount fcreate ferase ferror ferror2str fieldblock fielddeci fieldget fieldgetarr fieldlen fieldname
        fieldpos fieldput fieldputarr fieldtype fieldwblock file findexefile fklabel fkmax flagship_dir flock flockf fopen
        found fread freadstdin freadstr freadtxt frename fs_set fseek fwrite
        getactive getalign getapplykey getdosetkey getenv getenvarr getfunction getpostvalid getprevalid getreader guidrawline
        hardcr header hex2num
        i2bin iif indexcheck indexcount indexdbf indexext indexkey indexnames indexord infobox inkey inkey2read inkey2str inkeytrap
        instdchar instdstring int int2num isalpha isbegseq iscolor isdbexcl isdbflock isdbmultip isdbmultiple isdbmultipleopen
        isdbrlock isdigit isfunction isguimode islower isobjclass isobjequiv isobjproperty isprinter isupper
        l2bin lastkey lastrec left len listbox lock log lower ltrim lupdate
        macroeval macrosubst max max_col max_row maxcol maxrow mcol mdblck mdiclose mdiopen mdiselect memocode memodecode
        memoedit memoencode memoline memoread memory memotran memowrit memvarblock mhide min minmax mlcount mlctopos mleftdown
        mlpos mod month mpostolc mpresent mreststate mrightdown mrow msavestate msetcursor msetpos mshow mstate
        neterr netname nextkey num2hex num2int
        objclone oem2ansi onkey ordbagext ordbagname ordcond ordcondset ordcreate orddescend orddestroy ordfor ordisinique
        ordkey ordkeyadd ordkeycount ordkeydel ordkeygoto ordkeyno ordkeyval ordlistadd ordlistclear ordlistrebui ordname
        ordnumber ordscope ordsetfocu ordsetrelat ordskipunique os outerr outstd
        padc padl padr param parameters pcalls pcol pcount pixel2col pixel2row printstatus procfile procline procname procstack proper prow
        qout qout2 qqout qqout2
        rat rddlist rddname rddsetdefault readexit readinsert readkey readkill readmodal readsave readupdated readvar reccount recno recsize
        replicate restscreen right rlock rlockverify round row row2pixel rowadapt rowvisible rtrim
        savescreen scrdos2unix screen2chr scroll scrunix2dos seconds secondscpu select serial set setansi setblink setcancel setcol2get
        setcolor setcolorba setcursor setevent setguicursor setkey setmode setpos setprc setvarempty sleep sleepms soundex space
        sqrt statbarmsg statusmessage stod str strlen strlen2col strlen2pix strlen2space strpeek strpoke strtran strzero stuff substr
        tbcolumnnew tbmouse tbrowsearr tbrowsedb tbrowsenew tempfilename time tone transform trim truepath type
        updated upper used usersactive usersdbf usersmax
        val valtype version
        webdate weberrorhandler webgetenvir webgetformdata webhtmlbegin webhtmlend weblogerr webmaildomain weboutdata websendmail word
        year
    """.split()
    
    _keywords3 = "function procedure return exit".split()
    _keywords4 = "class instance export hidden protect prototype".split()

