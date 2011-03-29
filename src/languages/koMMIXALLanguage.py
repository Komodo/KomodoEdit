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

# MMIX Assembly 
# info at http://mmixmasters.sourceforge.net/
#         http://www.gnu.org/software/mdk/mdk.html

class koMMIXALLanguage(KoLanguageBase):
    name = "MMIXAL" 
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{a21da487-916c-49aa-b7cc-0b86713e8f9b}"
    _reg_categories_ = [("komodo-language", name)]

    modeNames = ['mixal', 'mmixal']
    _stateMap = {
        'default': ('SCE_MMIXAL_LEADWS',
                    'SCE_MMIXAL_LABEL',),
        'keywords': ('SCE_MMIXAL_SYMBOL',
                     'SCE_MMIXAL_OPCODE',
                     'SCE_MMIXAL_OPCODE_PRE',
                     'SCE_MMIXAL_OPCODE_VALID',
                     'SCE_MMIXAL_OPCODE_POST',),
        'unknown_opcodes': ('SCE_MMIXAL_OPCODE_UNKNOWN',),
        'keywords2': ('SCE_MMIXAL_REGISTER',),
        'keywords3': ('SCE_MMIXAL_SYMBOL',),
        'includes': ('SCE_MMIXAL_INCLUDE',),
        'comments': ('SCE_MMIXAL_COMMENT',),
        'numbers': ('SCE_MMIXAL_NUMBER',),
        'strings': ('SCE_MMIXAL_STRING',
                    'SCE_MMIXAL_CHAR',),
        'operands': ('SCE_MMIXAL_OPERANDS',),
        'refs': ('SCE_MMIXAL_REF',),
        'hex': ('SCE_MMIXAL_HEX',),
        }
    defaultExtension = '.mixal' # .mms
    commentDelimiterInfo = {}
    
    sample = """*                                                        (1)
* hello.mixal: say 'hello world' in MIXAL                (2)
*                                                        (3)
* label ins    operand     comment                       (4)
TERM    EQU    19          the MIX console device number (5)
        ORIG   1000        start address                 (6)
START   OUT    MSG(TERM)   output data at address MSG    (7)
        HLT                halt execution                (8)
MSG     ALF    "MIXAL"                                   (9)
        ALF    " HELL"                                   (10)
        ALF    "O WOR"                                   (11)
        ALF    "LD   "                                   (12)
        END    START       end of the program            (13)
"""
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(
                components.interfaces.ISciMoz.SCLEX_MMIXAL)
            self._lexer.setKeywords(0, self._opcodes)
            self._lexer.setKeywords(1, self._special_register)
            self._lexer.setKeywords(2, self._predef_symbols)
        return self._lexer

    _opcodes="""2ADDU 4ADDU 8ADDU 16ADDU ADD ADDU AND ANDNH ANDNL ANDNMH ANDNML 
            BDIF BEV BN BNN BNP BNZ BOD BP BSPEC BYTE BZ CMP CMPU CSEV CSN CSNN
            CSNP CSNZ CSOD CSP CSWAP CSZ 
            DIV DIVU ESPEC EXPR FADD FCMP FCMPE FDIV FEQL FEQLE FIX FIXU FLOT
            FLOTU FMUL FREM FSQRT FSUB FUN FUNE 
            GET GETA GO GREG I_BIT INCH INCL INCMH INCML IS JMP LDA LDB LDBU
            LDHT LDO LDOU LDSF LDT LDTU LDUNC LDVTS LDW LDWU LOC LOCAL 
            MOR MUL MULU MUX MXOR NAND NEG NEGU NNIX NOR NXOR O_BIT OCTA ODIF
            OR ORH ORL ORMH ORML ORN 
            PBEV PBN PBNN PBNP PBNZ PBOD PBP PBZ POP PREFIX PREGO PRELD PREST
            PUSHGO PUSHJ PUT 
            RESUME SAVE SET SETH SETL SETMH SETML SFLOT SFLOTU SL SLU SR SRU 
            STB STBU STCO STHT STO STOU STSF STT STTU STUNC STW STWU SUB SUBU S
            WYM SYNC SYNCD TDIF TETRA TRAP TRIP UNSAVE 
            WDIF WYDEXOR ZSEV ZSN ZSNN ZSNP ZSNZ ZSOD ZSP ZSZ""".split()
    
    _special_register="""rA rB rC rD rE rF rG rH rI rJ rK rL rM rN rO rP rQ rR rS 3
                        rT rU rV rW rX rY rZ rBB rTT rWW rXX rYY rZZ""".split()
    
    _predef_symbols="""@ Text_Segment Data_Segment Pool_Segment Stack_Segment 
            StdErr StdIn StdOut 
            Fopen Fclose Fread Fwrite Fgets Fputs Fgetws Fputws Ftell Fseek 
            TextRead TextWrite BinaryRead BinaryWrite BinaryReadWrite""".split()
