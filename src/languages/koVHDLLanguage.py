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

class koVHDLLanguage(KoLanguageBase):
    name = "VHDL"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{87D13284-5539-11DA-A814-000D935D3368}"
    _reg_categories_ = [("komodo-language", name)]

    commentDelimiterInfo = {
        "line": [ "--" ],
    }

    defaultExtension = ".vhdl" 

    supportsSmartIndent = "brace"
    sciMozLexer = components.interfaces.ISciMoz.SCLEX_VHDL

    _stateMap = {
        'default': ('SCE_VHDL_DEFAULT',),
        'keywords': ('SCE_VHDL_KEYWORD', 'SCE_VHDL_USERWORD',),
        'identifiers': ('SCE_VHDL_IDENTIFIER',),
        'comments': ('SCE_VHDL_COMMENT','SCE_VHDL_COMMENTLINEBANG',),
        'operators': ('SCE_VHDL_OPERATOR', 'SCE_VHDL_STDOPERATOR',),
        'numbers': ('SCE_VHDL_NUMBER',),
        'strings': ('SCE_VHDL_STRING', 'SCE_VHDL_STRINGEOL',),
        'attributes': ('SCE_VHDL_ATTRIBUTE',),
        'functions': ('SCE_VHDL_STDFUNCTION',),
        'package': ('SCE_VHDL_STDPACKAGE',),
        'type': ('SCE_VHDL_STDTYPE',),
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
            self._lexer.setKeywords(4, self._keywords5)
            self._lexer.setKeywords(5, self._keywords6)
            self._lexer.setKeywords(7, self._keywords7)
            self._lexer.supportsFolding = 1
        return self._lexer

    _keywords = """
        access after alias all architecture array assert attribute begin block
        body buffer bus case component configuration constant disconnect downto
        else elsif end entity exit file
        for function generate generic group guarded if impure in inertial inout
        is label library linkage literal
        loop map new next null of on open others out package port postponed
        procedure process pure range record
        register reject report return select severity shared signal subtype
        then to transport type unaffected
        units until use variable wait when while with
    """.split()

    _keywords2 = """
        abs and mod nand nor not or rem rol ror sla sll sra srl xnor xor 
    """.split()

    _keywords3 = """
        left right low high ascending image value pos val succ pred leftof
        rightof base range reverse_range       
        length delayed stable quiet transaction event active last_event
        last_active last_value driving            
        driving_value simple_name path_name instance_name
    """.split()

    _keywords4 = """
        now readline read writeline write endfile resolved to_bit to_bitvector
        to_stdulogic to_stdlogicvector     
        to_stdulogicvector to_x01 to_x01z to_UX01 rising_edge falling_edge
        is_x shift_left shift_right rotate_left
        rotate_right resize to_integer to_unsigned to_signed std_match to_01
        """.split()

    _keywords5 = """
        std ieee work standard textio std_logic_1164 std_logic_arith
        std_logic_misc std_logic_signed              
        std_logic_textio std_logic_unsigned numeric_bit numeric_std
        math_complex math_real vital_primitives       
        vital_timing
        """.split()

    _keywords6 = """
        boolean bit character severity_level integer real time delay_length
        natural positive string bit_vector    
        file_open_kind file_open_status line text side width std_ulogic
        std_ulogic_vector std_logic               
        std_logic_vector X01 X01Z UX01 UX01Z unsigned signed   
        """.split()

    _keywords7 = []