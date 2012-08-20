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

"""parser for Luddite, using PLY

See http://systems.cs.uchicago.edu/ply for more information on PLY, the
lexer/parser framework this code uses.
"""

import os
from os.path import dirname, join, exists
import re
import sys
from types import *
import logging

from ludditelib.common import LudditeError
from ludditelib import yacc
from ludditelib.lexer import Lexer, tokens  # tokens is used by Yacc stuff


log = logging.getLogger("luddite")



#XXX review and Pythonify
def keep_non_empty_dicts(lst):
    return filter(lambda(x): x and type(x) == DictType and len(x.keys()) > 0, lst)

#XXX review and Pythonify
def keep_non_empty_lists(lst):
    return filter(lambda(x): x and type(x) == ListType and len(x) > 0, lst)

#XXX review and Pythonify
def combine_filter_list_dict(list1, item2):
    list2 = keep_non_empty_dicts(list1 or [])
    if type(item2) == DictType:
        list2.append(item2)
    return list2

#XXX review and Pythonify
def combine_filter_list_item(list1, item2):
    k = keep_non_empty_lists(list1 + [item2])
    return k

#XXX review and Pythonify
def combine_filter_list(list1, item2):
    k = [x for x in (list1 + [item2]) if x]
    return k

def p_program(p):
    'program : statements'
    p[0] = p[1]

def p_statements(p):
    '''statements : statements_1
    | statements_2'''
    p[0] = p[1]

def p_statements_1(p):
    'statements_1 : statements statement'
    p[0] = combine_filter_list_item(p[1], p[2])

def p_statements_2(p):
    'statements_2 : empty'
    p[0] = []

def p_statement(p):
    '''statement : statement_1
    | statement_2'''
    p[0] = p[1]

def p_statement_1(p):
    '''statement_1 :  pattern eol_seq
|  namespace_decln eol_seq
|  public_id_decln eol_seq
|  system_id_decln eol_seq
|  family_decln eol_seq
|  fold_stmt eol_seq
|  include eol_seq
|  initial eol_seq
|  keyword_list eol_seq
|  keyword_style eol_seq
|  xlanguage eol_seq
|  stateBlock
|  sublanguage eol_seq
|  tokenCheckBlock
|  start_style_stmt
|  end_style_stmt'''  # newline handling has to be handled in the lexer/rule
    p[0] = p[1]

def p_statement_2(p):
    'statement_2 : eol'
    p[0] = []

def p_pattern(p):
    'pattern : HT_PATTERN name EQUALS string_const'
    p[0] = ['pattern', { 'name' : p[2], 'value' : p[4] }]

def p_fold_stmt(p):
    'fold_stmt : HT_FOLD name_or_string LB_NAME plus_or_minus'
    p[0] = ['fold', { 'name' : p[2], 'style' : p[3], 'value' : p[4] }]

def p_plus_or_minus(p):
    '''plus_or_minus : PLUS
| MINUS'''
    if p[1] == '+': p[0] = 1
    else: p[0] = -1

def p_include(p):
    'include : HT_INCLUDE name_or_string'
    p[0] = ['include', p[2]]

def p_namespace_decln(p):
    'namespace_decln : HT_X_NAMESPACE name_or_string'
    p[0] = ['namespace', p[2]]

def p_public_id_decln(p):
    'public_id_decln : HT_PUBLIC_ID name_or_string'
    p[0] = ['public_id', p[2]]

def p_system_id_decln(p):
    'system_id_decln : HT_SYSTEM_ID name_or_string'
    p[0] = ['system_id', p[2]]

def p_family_decln(p):
    'family_decln : HT_FAMILY name'
    p[0] = ['family', p[2]]

def p_initial(p):
    'initial : HT_INITIAL name'
    p[0] = ['initial', {'name' : p[2]}]

def p_keyword_list(p):
    'keyword_list : HT_KEYWORDS name_and_string_list'
    p[0] = ['keywordList', p[2]]

def p_keyword_style(p):
    'keyword_style : HT_KEYWORD_STYLE name ARROW name'
    p[0] = ['keywordStyle', p[2], p[4]]

# Calling this 'language' will make the parser-generator unhappy.

def p_xlanguage(p):
    'xlanguage : HT_LANGUAGE name_or_string'
    p[0] = ['language', p[2]]

# Calling this 'sub_language' will make the parser unhappy.

def p_sublanguage(p):
    'sublanguage : HT_SUBLANGUAGE name'
    p[0] = ['sublanguage', p[2]]

#XXX : Turn newlines on and off
def p_name_and_string_list(p):
    'name_and_string_list : OBRACKET names_and_strings CBRACKET'
    p[0] = p[2]

def p_stateBlock(p):
    'stateBlock :  HT_STATE state_name opt_colon_eol transitions'
    p[0] = ['stateBlock', { 'name' : p[2], 'value' : p[4]}]

def p_transitions(p):
    '''transitions : transitions_1
    | transitions_2'''
    p[0] = p[1]

def p_transitions_1(p):
    'transitions_1 : transitions transition'
    p[0] = combine_filter_list_item(p[1], p[2])

def p_transitions_2(p):    
    'transitions_2 : empty'
    p[0] = []

def p_transition(p):
    '''transition : transition_1
    | transition_2
    | transition_3
    | transition_4'''
    p[0] = p[1]

def p_transition_1(p):
    'transition_1 : string_const opt_token_check opt_colon cmds_and_trans eol_seq'
    p[0] = ['transition', { 'type' : 'string', 'value' : p[1], 'token_check' : p[2], 'cmds' : p[4][0], 'trans' : p[4][1]}]
    
def p_transition_2(p):
    'transition_2 : pattern_const opt_token_check opt_colon cmds_and_trans eol_seq'
    p[0] = ['transition', { 'type' : 'pattern', 'value' : p[1], 'token_check' : p[2], 'cmds' : p[4][0], 'trans' : p[4][1]}]

def p_transition_3(p):
    'transition_3 : HT_DELIMITER opt_token_check opt_colon cmds_and_trans eol_seq'
    p[0] = ['transition', { 'type' : 'delimiter', 'value' : '', 'token_check' : p[2], 'cmds' : p[4][0], 'trans' : p[4][1]}]

def p_transition_4(p):
    'transition_4 : eol'
    p[0] = None

def p_cmds_and_trans(p):
    '''cmds_and_trans : cmds_and_trans_1
    | cmds_and_trans_2
    | cmds_and_trans_3
    | cmds_and_trans_4
    | cmds_and_trans_5'''
    p[0] = p[1]

def p_cmds_and_trans_1(p):
    'cmds_and_trans_1 : state_tran'
    p[0] = [None, p[1]]

def p_cmds_and_trans_2(p):
    'cmds_and_trans_2 : cmds COMMA state_tran'
    p[0] = [ p[1],  p[3] ]

def p_cmds_and_trans_3(p):
    'cmds_and_trans_3 : cmds state_tran'
    p[0] = [ p[1],  p[2] ]

def p_cmds_and_trans_4(p):
    'cmds_and_trans_4 : cmds'
    p[0] = [ p[1],  None ]

def p_cmds_and_trans_5(p):
    'cmds_and_trans_5 : empty'
    p[0] = [None, None]

def p_state_tran(p):
    'state_tran : ARROW state_name'
    p[0] = p[2]

def p_tokenCheckBlock(p):
    'tokenCheckBlock : HT_TOKEN_CHECK COLON eol_seq tokenCheckDeclns'
    p[0] = ['tokenCheckBlock', p[4]]

def p_tokenCheckDeclns(p):
    '''tokenCheckDeclns : tokenCheckDeclns_1
    | tokenCheckDeclns_2'''
    p[0] = p[1]
        
def p_tokenCheckDeclns_1(p):
    'tokenCheckDeclns_1 : tokenCheckDeclns tokenCheckDecln'
    p[0] = combine_filter_list_dict(p[1], p[2])
    
def p_tokenCheckDeclns_2(p):
    'tokenCheckDeclns_2 : empty'
    p[0] = None
    
def p_tokenCheckDecln(p):
    '''tokenCheckDecln : tokenCheckDecln1
| tokenCheckDecln2'''
    p[0] = p[1]

def p_tokenCheckDecln1(p):
    'tokenCheckDecln1 : name COLON action_type action_selectors opt_term'
    p[0] = {'name' : p[1], 'type' : p[3], 'selectors' : p[4]}

def p_tokenCheckDecln2(p):
    'tokenCheckDecln2 : eol'
    p[0] = None

def p_action_type(p):
    '''action_type : HT_REJECT
    | HT_SKIP
    | HT_ACCEPT'''
    p[0] = p[1]

def p_action_selectors(p):
    '''action_selectors : HT_ALL
| name_and_string_list'''
    p[0] = p[1]

def p_start_style_stmt(p):
    'start_style_stmt : HT_START_STYLE name'
    p[0] = ['start_style', p[2]]

def p_end_style_stmt(p):
    'end_style_stmt : HT_END_STYLE name'
    p[0] = ['end_style', p[2]]
    
def p_string_const(p):
    'string_const : LB_STRING'
    # dequote the start of the raw string
    value1 = re.sub(r'^[\'\"]', '', p[1])
    value2 = re.sub(r'[\'\"]$', '', value1)
    if '\\' not in value2:
        p[0] = value2
    else:
        # Now handle only escaped quotes and tabs, all other backslashed
        # items will be handled by the generator.
        target = []
        esc_chars = {'"':'"',
                     "'":"'",
                     "t":"\t",
                     }
        srclen = len(value2)
        srclenSub1 = srclen - 1
        i = 0
        while i < srclen:
            if value2[i] == '\\':
                if i < srclenSub1:
                    c = esc_chars.get(value2[i + 1], None)
                    if c:
                        target.append(c)
                    else:
                        # Pass the backslash along when it doesn't
                        # precede a quote or t
                        target.append('\\')
                        target.append(value2[i+1])
                    i += 2
                    continue
            target.append(value2[i])
            i += 1
        p[0] = "".join(target)

def p_pattern_const(p):
    'pattern_const : LB_REGEX'
    ptn = p[1]
    if ptn[-1] == 'i':
        ignore_case = True
        ptn = ptn[:-1]
    else:
        ignore_case = False
    ptn1 = re.sub('^/', '', ptn)
    ptn2 = re.sub('/$', '', ptn1)
    p[0] = [ptn2, ignore_case]

def p_state_name(p):
    'state_name : LB_NAME'
    p[0] = p[1]

def p_cmds(p):
    '''cmds : cmds_1
| cmds_2'''
    p[0] = p[1]

def p_cmds_1(p):
    'cmds_1 : cmds COMMA cmd'
    p[0] = combine_filter_list_item(p[1], p[3])

def p_cmds_2(p):
    'cmds_2 : cmd'
    p[0] = [p[1]]

def p_cmd(p):
    '''cmd : paint_cmd
    | at_eoltran_cmd
    | clear_delimiter_cmd
    | keep_delimiter_cmd
    | no_keyword_cmd
    | redo_cmd
    | set_delimiter_cmd
    | set_opposite_delimiter_cmd
    | spush_check_cmd
    | spop_check_cmd
    | sstack_set_cmd'''
    p[0] = p[1]

def p_paint_cmd(p):
    'paint_cmd : HT_PAINT OPAREN paint_name COMMA color_sym CPAREN'
    p[0] = ['paint', {'type' : p[3], 'value' : p[5]}]

def p_paint_name(p):
    '''paint_name : HT_INCLUDE
| HT_UPTO'''
    p[0] = p[1]

def p_no_keyword_cmd(p):
    'no_keyword_cmd : HT_NOKEYWORD'
    p[0] = ['no_keyword']

def p_at_eoltran_cmd(p):
    'at_eoltran_cmd : HT_AT_EOL opt_paren_state_name'
    p[0] = [ 'at_eol', p[2] ]

def p_redo_cmd(p):
    'redo_cmd : HT_REDO'
    p[0] = ['redo']

def p_clear_delimiter_cmd(p):
    'clear_delimiter_cmd : HT_CLEAR_DELIMITER'
    p[0] = ['clear_delimiter']

def p_keep_delimiter_cmd(p):
    'keep_delimiter_cmd : HT_KEEP_DELIMITER'
    p[0] = ['keep_delimiter']

def p_set_delimiter_cmd(p):
    'set_delimiter_cmd : HT_SET_DELIMITER opt_paren_number'
    p[0] = [p[1], p[2]]

def p_set_opposite_delimiter_cmd(p):
    'set_opposite_delimiter_cmd : HT_SET_OPPOSITE_DELIMITER opt_paren_number'
    p[0] = [p[1], p[2]]

def p_spush_check_cmd(p):
    'spush_check_cmd : HT_SPUSH_CHECK opt_paren_state_name'
    p[0] = [ 'spush_check', p[2] ]

def p_sstack_set_cmd(p):
    'sstack_set_cmd : HT_SSTACK_SET opt_paren_state_name'
    p[0] = [ 'sstack_set', p[2] ]

def p_opt_paren_state_name(p):
    '''opt_paren_state_name : opt_paren_state_name_1
| opt_paren_state_name_2'''
    p[0] = p[1]

def p_opt_paren_state_name_1(p):
    'opt_paren_state_name_1 : OPAREN opt_paren_state_name CPAREN'
    p[0] = p[2]

def p_opt_paren_state_name_2(p):
    'opt_paren_state_name_2 : state_name'
    p[0] = p[1]

def p_spop_check_cmd(p):
    'spop_check_cmd : HT_SPOP_CHECK'
    p[0] = [p[1]]

def p_color_sym(p):
    'color_sym : LB_NAME'
    p[0] = p[1]

def p_name(p):
    'name : LB_NAME'
    p[0] = p[1]

def p_names_and_strings(p):
    '''names_and_strings : names_and_strings_1
    | names_and_strings_2'''
    p[0] = p[1]
    
def p_names_and_strings_1(p):
    'names_and_strings_1 : names_and_strings name_or_string_opt_comma'
    p[0] = combine_filter_list(p[1], p[2])
    
def p_names_and_strings_2(p):
    'names_and_strings_2 : empty'
    p[0] = []

def p_name_or_string_opt_comma(p):
    '''name_or_string_opt_comma : name_or_string_opt_comma_1
| name_or_string_opt_comma_2'''
    p[0] = p[1]

def p_name_or_string_opt_comma_1(p):
    'name_or_string_opt_comma_1 : name_or_string opt_comma'
    p[0] = p[1]

def p_name_or_string_opt_comma_2(p):
    'name_or_string_opt_comma_2 : eol'
    p[0] = None

def p_name_or_string(p):
    '''name_or_string : name
| string_const'''
    p[0] = p[1]

def p_opt_paren_number(p):
    '''opt_paren_number : paren_number
| NUMBER'''
    p[0] = p[1]

def p_paren_number(p):
    'paren_number : OPAREN NUMBER CPAREN'
    p[0] = p[2]

def p_eol_seq(p):
    'eol_seq : opt_term eol'
    p[0] = None

def p_opt_colon_eol(p):
    'opt_colon_eol : opt_colon eol'
    p[0] = None

def p_eol(p):
    'eol : LB_NL'
    p[0] = None

def p_opt_colon(p):
    '''opt_colon : COLON
| empty'''
    p[0] = p[1]

def p_opt_comma(p):
    '''opt_comma : COMMA
| empty'''
    p[0] = p[1]

def p_opt_term(p):
    '''opt_term : SCOLON
| empty'''
    p[0] = p[1]

def p_opt_token_check(p):
    '''opt_token_check : HT_TOKEN_CHECK
| empty'''
    p[0] = (p[1] == 'token_check' and 1) or 0

def p_empty(p):
    'empty : '
    pass
    # p[0] = None

def p_error(p):
    global num_errs
    print "Syntax error at or near line %d, token '%s'" % (p.lexer.lineno,
                                                           p.value)
    num_errs += 1



#---- the driver

def _wrap_read_file(fname, include_path):
    # Read in the file contents.
    if fname == '-':
        fin = sys.stdin
        s = fin.read()
    else:
        for p in [os.curdir] + include_path:
            fpath = join(p, fname)
            if exists(fpath):
                break
        else:
            raise LudditeError("`%s' does not exist on include path: '%s'"
                               % (fname, "', '".join(include_path)))
        fin = open(fpath, 'r')
        try:
            s = fin.read()
        finally:
            fin.close()
    return s

def _read_file(fname, include_path):
    s = _wrap_read_file(fname, include_path)
    if s[-1] != "\n":
        s = s + "\n"
    return s    

def parse_udl_path(udl_path, include_path=None, debug_level=1):
    log.debug("parse_udl_path('%s')", udl_path)
    if include_path is None:
        include_path = []

    dname = dirname(udl_path) or os.curdir
    if dname not in include_path and os.path.abspath(dname) != os.getcwd():
        include_path.append(dname)

    lexer = Lexer()
    content = _read_file(udl_path, include_path)
    lexer.input(content)

    global num_errs
    num_errs = 0
    # `write_tables=0` because we don't want 'parsetab.py' file. It can
    # cause subtle problems if the cwd changes.
    yacc.yacc(write_tables=0)
    p2 = yacc.parse(debug=debug_level, lexer=lexer)
    
    # Because 'include' is part of the language, and not a pre-processor
    # language, we need to parse each included module separately.
    if p2:
        for nodes in p2:
            if nodes[0] == 'include':
                udl_path2 = nodes[1]
                t2 = parse_udl_path(udl_path2, include_path=include_path,
                                    debug_level=debug_level)
                nodes[0] = 'module'
                nodes[1] = t2
    return p2

