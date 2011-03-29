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

class koForthLanguage(KoLanguageBase):
    name = "Forth"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{1ba65748-6b5e-4924-9513-cd011b5f89fe}"
    _reg_categories_ = [("komodo-language", name)]

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
