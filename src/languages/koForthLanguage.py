from xpcom import components, ServerException

from koLanguageServiceBase import *

def registerLanguage(registery):
    registery.registerLanguage(koForthLanguage())
 
class koForthLanguage(KoLanguageBase):
    name = "Forth"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{1ba65748-6b5e-4924-9513-cd011b5f89fe}"

    _stateMap = {
        'default': ('SCE_FORTH_DEFAULT',),
        'comments': ('SCE_FORTH_COMMENT',
                     'SCE_FORTH_COMMENT_ML',),
        'strings': ('SCE_FORTH_STRING',),
        'numbers': ('SCE_FORTH_NUMBER',),
        'keywords': ('SCE_FORTH_KEYWORD',),
        'identifiers': ('SCE_FORTH_IDENTIFIER',),
        'prewords': ('SCE_FORTH_PREWORD1',
                     'SCE_FORTH_PREWORD2',),
        'defwords': ('SCE_FORTH_DEFWORD',),
        'control': ('SCE_FORTH_CONTROL',),
        'locale': ('SCE_FORTH_LOCALE',),
    }
    defaultExtension = '.forth'
    commentDelimiterInfo = {
        "line": [ '\\' ],
    }

    sample = """
SAMPLE NOT AVAILABLE
"""
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(
                components.interfaces.ISciMoz.SCLEX_FORTH)
            self._lexer.setKeywords(0, self._keywords)
            self._lexer.setKeywords(1, self._keywords2)
            self._lexer.setKeywords(2, self._keywords3)
            self._lexer.setKeywords(3, self._keywords4)
            self._lexer.setKeywords(4, self._keywords5)
            self._lexer.setKeywords(5, self._keywords6)
        return self._lexer

    _keywords="""AGAIN BEGIN CASE DO ELSE ENDCASE ENDOF IF LOOP OF REPEAT THEN
                UNTIL  WHILE [IF] [ELSE] [THEN] ?DO""".split()

    _keywords2="""
        DUP DROP ROT SWAP OVER @ ! 2@ 2! 2DUP 2DROP 2SWAP 2OVER NIP R@ >R R> 2R@ 2>R 2R> 
        0= 0< SP@ SP! W@ W! C@ C! < > = <> 0<>
        SPACE SPACES KEY? KEY THROW CATCH ABORT */ 2* /MOD CELL+ CELLS CHAR+ 
        CHARS MOVE ERASE DABS TITLE HEX DECIMAL HOLD <# # #S #> SIGN 
        D. . U. DUMP (.") >NUMBER ' IMMEDIATE EXIT RECURSE UNLOOP LEAVE HERE ALLOT , 
        C, W, COMPILE, BRANCH, RET, LIT, DLIT, ?BRANCH, ", >MARK >RESOLVE1 <MARK >RESOLVE 
        ALIGN ALIGNED USER-ALLOT USER-HERE HEADER DOES> SMUDGE HIDE :NONAME LAST-WORD 
        ?ERROR ERROR2 FIND1 SFIND SET-CURRENT GET-CURRENT DEFINITIONS GET-ORDER FORTH 
        ONLY SET-ORDER ALSO PREVIOUS VOC-NAME. ORDER LATEST LITERAL 2LITERAL SLITERAL 
        CLITERAL ?LITERAL1 ?SLITERAL1 HEX-LITERAL HEX-SLITERAL ?LITERAL2 ?SLITERAL2 SOURCE 
        EndOfChunk CharAddr PeekChar IsDelimiter GetChar OnDelimiter SkipDelimiters OnNotDelimiter 
        SkipWord SkipUpTo ParseWord NextWord PARSE SKIP CONSOLE-HANDLES REFILL DEPTH ?STACK 
        ?COMP WORD INTERPRET BYE QUIT MAIN1 EVALUATE INCLUDE-FILE INCLUDED >BODY +WORD 
        WORDLIST CLASS! CLASS@ PAR! PAR@ ID. ?IMMEDIATE ?VOC IMMEDIATE VOC WordByAddrWl 
        WordByAddr NLIST WORDS SAVE OPTIONS /notransl ANSI>OEM ACCEPT EMIT CR TYPE EKEY? 
        EKEY EKEY>CHAR EXTERNTASK ERASE-IMPORTS ModuleName ModuleDirName ENVIRONMENT? 
        DROP-EXC-HANDLER SET-EXC-HANDLER HALT ERR CLOSE-FILE CREATE-FILE CREATE-FILE-SHARED 
        OPEN-FILE-SHARED DELETE-FILE FILE-POSITION FILE-SIZE OPEN-FILE READ-FILE REPOSITION-FILE 
        DOS-LINES UNIX-LINES READ-LINE WRITE-FILE RESIZE-FILE WRITE-LINE ALLOCATE FREE RESIZE 
        START SUSPEND RESUME STOP PAUSE MIN MAX TRUE FALSE ASCIIZ> 
        R/O W/O ;CLASS ENDWITH OR AND /STRING SEARCH COMPARE EXPORT ;MODULE SPACE""".split()
    
    _keywords3="""
        VARIABLE CREATE : VALUE CONSTANT VM: M: var dvar chars OBJ 
        CONSTR: DESTR: CLASS: OBJECT: POINTER 
        USER USER-CREATE USER-VALUE VECT 
        WNDPROC: VOCABULARY -- TASK: CEZ: MODULE:""".split()
    
    _keywords4="""CHAR [CHAR] POSTPONE WITH ['] TO [COMPILE] CHAR ASCII \\'""".split()
    
    _keywords5="""REQUIRE WINAPI:""".split()
    
    _keywords6="""S" ABORT" Z" " ." C\"""".split()
