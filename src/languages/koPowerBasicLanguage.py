from xpcom import components, ServerException

from koLanguageServiceBase import *

# Power Basic at http://www.powerbasic.com/

def registerLanguage(registery):
    registery.registerLanguage(koPowerBasicLanguage())
    
class koPowerBasicLanguage(KoLanguageBase):
    name = "PowerBasic"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{0bc5c569-6546-45ec-8452-4636d326e0f7}"

    _stateMap = {
        'default': ('SCE_B_DEFAULT',),
        'keywords': ('SCE_B_KEYWORD',
                     'SCE_B_KEYWORD2',
                     'SCE_B_KEYWORD3',
                     'SCE_B_KEYWORD4'),
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
    defaultExtension = '.pb'
    commentDelimiterInfo = {"line": [ "rem ", "REM " ]}
    
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
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(
                components.interfaces.ISciMoz.SCLEX_PB)
            self._lexer.setKeywords(0, self._keywords_preprocessor + \
                                       self._keywords_functions + \
                                       self._keywords_proceedures + \
                                       self._keywords_datatypes + \
                                       self._keywords_options)
            self._lexer.supportsFolding = 1
        return self._lexer

    _keywords_preprocessor = """$alias $code $com $compile $cpu $debug
        $dim $dynamic $endif $error $event $float $huge $if $include
        $inline $lib $link $optimize $option $segment $sound $stack
        $static $string all array cga chain cntlbreak com ega emulate
        exe fullfloat graph herc iprint lpt map memory none npx off
        path pbdebug procedure signed size speed unit unsigned
        vga""".split()
        
    _keywords_functions = """absolute access and any append array as
        asc ascend ascii asm at atn attrib base beep bin$ binary bit bits
        bload bsave call case cbcd cbyt cdbl cdwd ceil cext cfix chain
        chdir chdrive chr$ cint circle clear clng close cls codeptr codeseg
        collate color com command$ common cos cqud csng csrlin curdir$ cvb
        cvbyt cvd cvdwd cve cvf cvi cvl cvmd cvms cvq cvs cvwrd cwrd data
        date$ declare decr def defbcd defdbl defext deffix defflx defint
        deflng defqud defsng defstr delay delete descend dim dir$ do draw
        dynamic else elseif ems end endmem environ environ$ eof eqv eradr
        erase erdev erdev$ erl err errnum error errtest execute exit exp
        exp10 exp2 external extract$ far field fileattr files fix fixdigits
        flexchr$ flush fn for frac fre freefile from function get get$
        gosub goto hex$ if imp impabs in incr inkey$ inp input input$
        insert instat instr int interrupt ioctl ioctl$ isfalse istrue
        iterate key kill lbound lcase$ left left$ len let line list loc
        local locate lock lof log log10 log2 loop lpos lprint lset ltrim$
        map max max$ max% mempack memset mid$ min min$ min% mkb$ mkbyt$
        mkd$ mkdir mkdwd$ mke$ mkf$ mki$ mkl$ mkmd$ mkms$ mkq$ mks$ mkwrd$
        mod mtimer multiplex name next not oct$ off on open option or out
        output paint palette peek peek$ peeki peekl pen play pmap point
        poke poke$ pokei pokel popup pos preset print pset public put
        put$ quiet random randomize read redim reg rem remove$ repeat$
        replace reset restore resume return right right$ rmdir rnd rotate
        round rset rtrim$ run scan screen seek seg select setmem sgn
        shared shell shift signed sin sleep sort sound space$ spc sqr
        static step stick stop str$ strig string$ strptr strseg stuff sub
        swap system tab tagarray tally tan then time$ timer to troff tron
        type ubound ucase ucase$ uevent union unlock until using using$
        val varptr varptr$ varseg verify view wait wend while width window
        with write xor""".split()
    
    _keywords_datatypes = """any bcd byte double dword extended fix flex
        integer long quad single string word""".split()
    
    _keywords_options = """ascend byval collate delete descend dynamic
        huge local preserve public shared static sort""".split()

    _keywords_proceedures = """arraycalc arrayinfo getstralloc getstrlen
        getstrloc rlsstralloc setonexit setonmempack setuevent pbvbinbase
        pbvcpu pbvcursor1 pbvcursor2 pbvcursorvis pbvdefseg pbverr
        pbvfixdigits pbvflexchr pbvhost pbvminusone pbvnpx pbvone
        pbvrevision pbvrevltr pbvscrnapage pbvscrnbuff pbvscrncard
        pbvscrncols pbvscrnmode pbvscrnpxlattr pbvscrnrows pbvscrntxtattr
        pbvscrnvpage pbvswitch pbvuserarea pbvusingchrs pbvvtxtx1
        pbvvtxtx2 pbvvtxty1 pbvvtxty2 pbvzero""".split()

