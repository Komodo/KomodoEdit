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

class koSpecmanLanguage(KoLanguageBase):
    name = "Specman-E"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{68f7c0bf-5dc5-41d7-85b4-ed91f141919a}"
    _reg_categories_ = [("komodo-language", name)]

    _stateMap = {
        'default': ('SCE_SN_DEFAULT',),
        'keywords': ('SCE_SN_WORD',
                     'SCE_SN_WORD2',
                     'SCE_SN_WORD3',),
        'identifiers': ('SCE_SN_IDENTIFIER',),
        'comments': ('SCE_SN_COMMENTLINE',
                     'SCE_SN_COMMENTLINEBANG',),
        'numbers': ('SCE_SN_NUMBER',),
        'strings': ('SCE_SN_STRING',),
        'stringeol': ('SCE_SN_STRINGEOL',),
        'operators': ('SCE_SN_OPERATOR',),
        'code': ('SCE_SN_CODE',),
        'preprocessor': ('SCE_SN_PREPROCESSOR',),
        'regex': ('SCE_SN_REGEXTAG',),
        'signals': ('SCE_SN_SIGNAL',),
        'user': ('SCE_SN_USER',),
        }

    defaultExtension = '.e'
    commentDelimiterInfo = {"line": [ "//" ]}
    
    sample = """
SAMPLE NOT AVAILABLE
"""
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(
                components.interfaces.ISciMoz.SCLEX_SPECMAN)
            self._lexer.setKeywords(0, self._keywords)
            self._lexer.setKeywords(1, self._keywords2)
            self._lexer.setKeywords(2, self._keywords3)
            self._lexer.supportsFolding = 0
        return self._lexer

    _keywords = """struct unit
        integer real bool int long uint nibble byte bits bytes bit time string
        var instance event
        verilog vhdl
        on compute start expect check that routine
        specman is also first only with like
        list of all radix hex dec bin ignore illegal
        traceable untraceable
        cover using count_only trace_only at_least transition item ranges
        cross text call task within
        packing low high
        locker address
        body code vec chars
        byte_array external_pointer
        choose matches
        if then else when try
        case casex casez default
        and or not xor
        until repeat while for from to step each do break continue
        before next always -kind network
        index it me in new return result select
        cycle sample events forever
        wait  change  negedge rise fall delay sync sim true detach eventually emit
        gen keep keeping soft before
        define as computed type extend
        variable global sys
        import
        untyped symtab ECHO DOECHO
        initialize non_terminal testgroup delayed exit finish
        out append print outf appendf
        post_generate pre_generate setup_test finalize_test extract_test
        init run copy as_a a set_config dut_error add clear lock quit
        lock unlock release swap quit to_string value stop_run
        crc_8 crc_32 crc_32_flip get_config add0 all_indices and_all
        apply average count delete exists first_index get_indices
        has insert is_a_permutation is_empty key key_exists key_index
        last last_index max max_index max_value min min_index
        min_value or_all pop pop0 push push0 product resize reverse
        sort split sum top top0 unique clear is_all_iterations
        get_enclosing_unit hdl_path exec deep_compare deep_compare_physical
        pack unpack warning error fatal
        size
        files load module ntv source_ref script read write
        initial idle others posedge clock cycles
        statement action command member exp block num file""".split()

    # keywords2 is for highlighting secondary keywords
    _keywords2 = """TRUE FALSE MAX_INT MIN_INT NULL UNDEF""".split()

    # keywords3 is for sequence and eRM keywords and functions
    _keywords3 = """any_sequence_item sequence any_sequence_driver driver
        created_driver  parent_sequence
        bfm_interaction_mode PULL_MODE PUSH_MODE MAIN SIMPLE RANDOM
        max_random_count max_random_depth num_of_last_items
        NORMAL NONE FULL LOW HIGH MEDIUM logger message
        get_tags show_units show_actions show_message ignore_tags
        set_style set_screen set_file set_flush_frequency
        set_format set_units set_actions at_message_verbosity
        short_name short_name_path short_name_style
        
        private protected package rerun any_env
        unqualified_clk clk reset_start reset_end
        message_logger verbosity tags to_file
        
        body pre_body post_body get_next_item send_to_bfm
        get_depth get_driver nice_string get_index grab
        is_blocked is_relevant ungrab mid_do post_do post_trace
        pre_do current_grabber get_current_item get_num_items_sent
        get_sequence_trace_list get_trace_list is_grabbed
        try_next_item check_is_relevant delay_clock
        get_sub_drivers regenerate_data wait_for_sequences
        stop""".split()

