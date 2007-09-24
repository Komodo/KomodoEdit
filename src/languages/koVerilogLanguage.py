from xpcom import components, ServerException

from koLanguageServiceBase import *

def registerLanguage(registery):
    registery.registerLanguage(koVerilogLanguage())
    
class koVerilogLanguage(KoLanguageBase):
    name = "Verilog"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{4891482d-f3ed-4016-8b3a-6880cbcdade7}"

    _stateMap = {
        'default': ('SCE_V_DEFAULT',),
        'keywords': ('SCE_V_WORD',
                     'SCE_V_WORD2',
                     'SCE_V_WORD3',
                     'SCE_V_USER',),
        'identifiers': ('SCE_V_IDENTIFIER',),
        'comments': ('SCE_V_COMMENT',
                     'SCE_V_COMMENTLINE',
                     'SCE_V_COMMENTLINEBANG',),
        'numbers': ('SCE_V_NUMBER',),
        'strings': ('SCE_V_STRING',),
        'stringeol': ('SCE_V_STRINGEOL',),
        'operators': ('SCE_V_OPERATOR',),
        'preprocessor': ('SCE_V_PREPROCESSOR',),
        }

    defaultExtension = '.v' # .vh
    commentDelimiterInfo = {
        "line": [ "//" ],
        "block": [ ("/*", "*/") ],
        "markup": "*",
    }
    
    sample = """
SAMPLE NOT AVAILABLE
"""
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(
                components.interfaces.ISciMoz.SCLEX_VERILOG)
            self._lexer.setKeywords(0, self._keywords)
            self._lexer.setKeywords(2, self._keywords3)
            self._lexer.supportsFolding = 1
        return self._lexer

    # SCE_V_WORD
    _keywords = """always and assign begin
        xbuf buf bufif0 bufif1 case casex casez cmos
        default defparam else end endcase
        endfunction endmodule endprimitive endspecify
        endtable endtask event for force forever
        fork function if initial inout input
        integer join macromodule makefile module
        nand negedge nmos nor not notif0 notif1
        or output parameter pmos posedge primitive
        pulldown pullup rcmos real realtime reg
        repeat rnmos rpmos rtran rtranif0 rtranif1
        signed specify specparam supply supply0 supply1 table
        task time tran tranif0 tranif1 tri tri0
        tri1 triand trior trireg vectored wait
        wand while wire wor xnor xor""".split()
    
    # SCE_V_WORD2
    _keywords2 = []
    
    # SCE_V_WORD3
    _keywords3 = """$readmemb $readmemh $sreadmemb $sreadmemh
        $display $write $strobe $monitor $fdisplay $fwrite $fstrobe
        $fmonitor $fopen $fclose $time $stime $realtime $scale
        $printtimescale $timeformat $stop $finish $save
        $incsave $restart $input $log $nolog $key $nokey $scope
        $showscopes $showscopes $showvars $showvars
        $countdrivers $list $monitoron $monitoroff $dumpon
        $dumpoff $dumpfile $dumplimit $dumpflush $dumpvars
        $dumpall $reset $reset $reset $reset $reset $random
        $getpattern $rtoi $itor $realtobits $bitstoreal
        $setup $hold $setuphold $period $width $skew
        $recovery""".split()
        
    # SCE_V_USER
    _keywords4 = []