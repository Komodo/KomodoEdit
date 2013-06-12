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

"""Luddite output file generation code."""

import copy
import os
from os.path import basename, dirname, join, exists
import re
import sys
import datetime
import logging
from pprint import pprint

from ludditelib.common import LudditeError, __version_info__


#---- globals

log = logging.getLogger("luddite")



#---- support stuff


def isTemplateStateName(stateName):
    return stateName.startswith("IN_TPL_")

def die(msg, cond=None):
    if not cond:
        return
    if msg[-1] != "\n":
        msg += "\n"
    sys.stderr.write(msg)
    sys.exit(0)
    # raise(msg)

def warn(fmt, *vals):
    if fmt[-1] == "\n":
        fmt2 = fmt[:-1]
    else:
        fmt2 = fmt
    sys.stderr.write(fmt2 % vals)
    sys.stderr.write("\n")


def qq(s):
    return '"' + s + '"'


def test_assign_entry(lst, idx, val, dft_val=None):
    if idx >= len(lst):
        while idx >= len(lst):
            lst.append(dft_val)
        lst[idx] = val
    elif lst[idx] is None:
        lst[idx] = val

def getSafeName(languageName):
    """Map [^-_.\w\d]+ in language name to _."""
    return re.sub(r'[^-_.\w\d]+', '_', languageName)

class MainObj:
    def __init__(self):
        self.stateTable = []
        self.stateCount = 0
        self.holdUniqueStates = {}
        self.familyList = {} # Things like lookBackTests, kwds, etc
        self.languageName = None
        self.nameTable = {}  # Hash state names to unique numbers
        self.nameInfo = []    # Keep info on state numbers
        self.verbose = False  #XXX Should go away in favour of log.debug usage
        self.families = {
            'markup' : 0,
            'css' : 1,
            'csl' : 2,
            'ssl' : 3,
            'tpl' : 4,
        }
        self._re_dollar_var = re.compile(r'\$([A-Z]+)')
        self._re_is_word = re.compile(r'^[\w_][\w\d_]+$')

        self._re_dequote_start = None
        self.languageService_xmlNames = {'namespace' : ['namespaces', {}, ],
                                         'public_id' : ['publicIdList', {}, ],
                                         'system_id' : ['systemIdList', {}, ],
                                         }

    def _get_safe_lang_name(self):
        return getSafeName(self.languageName)
    safeLangName = property(_get_safe_lang_name, None, None,
                            "an identifier-safe version of languageName")

    def calcUniqueStates(self):
        # Here we show which colors can be relied on to map to an
        # internal state.  The current position will be at the first
        # character in the buffer styled that color, so this might not
        # work in all cases.
        self.uniqueStates = {}
        for k in self.holdUniqueStates.keys():
            v = self.holdUniqueStates[k]
            if len(v.keys()) == 1:
                self.uniqueStates[k] = v.keys()[0]
                log.debug("Map style [%s] to state [%s]", k, v.keys()[0])
            log.debug("Style [%s] maps to states [%s]", k,
                      ", ".join(v.keys()))
        self.holdUniqueStates = None

    def _split_quote_string(self, s, len):
        return re.sub('(.{%d}[^ ]+) ' % (len,), '\\1"\n    " ', s)

    def _all_words(self, str_list):
        for s in str_list:
            if not self._re_is_word.match(s):
                return False
        return True

    def _has_ptn_var(self, s):
        mobj = self._re_dollar_var.search(s)
        if mobj is None: return None
        return mobj.group(1)
    
    def _state_num_from_name(self, nameTable, target_state_name, cmd):
        target_state_num = nameTable.get(target_state_name, None)
        if target_state_num is None:
            die("%s: State %s isn't defined" % (cmd, target_state_name,), True)
        return target_state_num
        
    def dumpAsTable(self, resConstants, out_file):
        self.resConstants = resConstants
        resDefinesPath = (resConstants and True)
        fout = open(out_file, 'w')
        WRITER_VERSION_MAJOR = 1
        WRITER_VERSION_MINOR = 2
        WRITER_VERSION_SUBMINOR = 0

        if not resDefinesPath:
            # Print some common declarations
            fout.write("""
                       
#define WRITER_VERSION_MAJOR	%d
#define WRITER_VERSION_MINOR	%d
#define WRITER_VERSION_SUBMINOR	%d

// We're executing inside MainInfo::Init()
TransitionTable *p_TransitionTable;
TransitionInfo *p_TranBlock;
Transition *p_Tran;
FamilyInfo *p_FamilyInfo;\n""" % (WRITER_VERSION_MAJOR, WRITER_VERSION_MINOR,
                                  WRITER_VERSION_SUBMINOR))
            if filter(lambda(x): hasattr(x, 'tokenCheckBlock'), self.familyList.values()):
                fout.write("LookBackTests *p_LBTests;\n")
                fout.write("LookBackTestObj *p_LBTestObj;\n")
    
            fout.write("p_TransitionTable = GetTable();\n") # p_MainInfo->
            fout.write("if (!p_TransitionTable) return false;\n")
            if self.languageName:
                fout.write('p_language_name = "%s";\n'
                           % self.escapeStr(self.languageName))
            
        else:
            # Write out version info for the reader
            fout.write("1:lexer resource\n")
            for name, ver in zip(["MAJOR", "MINOR", "SUBMINOR"],
                                 __version_info__):
                fout.write("%d:%d\n"
                           % (resConstants["ASTC_META_VERSION_"+name], ver))
            fout.write("%d:%d:%d:%d\n" %
                       (resConstants["ASTC_TRAN_WRITER_VERSION"],
                        WRITER_VERSION_MAJOR, WRITER_VERSION_MINOR,
                                  WRITER_VERSION_SUBMINOR))
            if self.languageName:
                self.emitScratchBuffer(fout, self.languageName)
                fout.write("%s\n" % resConstants['ASTC_LANGUAGE_NAME'])
        # otherwise this is done by the loader.

        nameTable = self.nameTable
        # Dump all the transitions
    
        # Initialize some hard-wired data
        if 1:
            family_name_pairs = [
                ('MARKUP', 'M'),
                ('CSS', 'CSS'),
                ('CSL', 'CSL'),
                ('SSL', 'SSL'),
                ('TEMPLATE', 'TPL')]
            for pair in family_name_pairs:
                (long_name, short_name) = pair
                deft_name = "IN_" + short_name + "_DEFAULT";
                if self.verbose and not (resDefinesPath or nameTable.has_key(deft_name)):
                    warn("Can't figure out a value for state %s, using 0\n",
                         deft_name)
                
                f_idx = "TRAN_FAMILY_" + long_name
                if not resDefinesPath:
                    fout.write("familyColors[%s] = %s;\n"
                               % (f_idx, self.fullStyleName(short_name + "_DEFAULT")))
                    fout.write("familyOperators[%s] = %s;\n"
                               % (f_idx, self.fullStyleName(short_name + "_OPERATOR")))
                    fout.write("familyStyles[%s] = %s; // %s\n"
                               % (f_idx, nameTable.get(deft_name, 0), deft_name))
                else:
                    fout.write("%d:%d:%d\n"
                               % (resConstants['ASTC_F_COLOR'],
                                  resConstants[f_idx],
                                  resConstants[self.fullStyleName(short_name + "_DEFAULT")]))
                    fout.write("%d:%d:%d\n"
                               % (resConstants['ASTC_F_OPERATOR'],
                                  resConstants[f_idx],
                                  resConstants[self.fullStyleName(short_name + "_OPERATOR")]))
                    fout.write("%d:%d:%d\n"
                               % (resConstants['ASTC_F_STYLE'],
                                  resConstants[f_idx],
                                  nameTable.get(deft_name, 0)))

        family_names = map(lambda x: x.lower(), self.familyList.keys())
        family_names.sort(lambda a, b: self.families[a] - self.families[b])
        globalFlipCount = 0
        for family_name in family_names:
            globalFlipCount += len(self.familyList[family_name].flippers)
    
        if globalFlipCount > 0:
            if not resDefinesPath:
                fout.write("SetFlipperCount(%d);" % globalFlipCount)
            else:
                fout.write("%d:%d\n"
                           % (resConstants['ASTC_FLIPPER_COUNT'],
                              globalFlipCount))
        flipIdx = 0
    
        for family_name in family_names:
            family_num = self.families[family_name]
            if not resDefinesPath:
                fout.write("SetCurrFamily(%d);" % family_num) # p_MainInfo->
                fout.write("p_FamilyInfo = GetCurrFamily();\n") # p_MainInfo->
            else:
                fout.write("%d:%d\n"
                           % (resConstants['ASTC_CURRENT_FAMILY'],
                              family_num))
                
            obj = self.familyList[family_name]
            if 1:
                st_name = obj.initialState
                st_val = None
                if st_name:
                    st_val = nameTable[st_name]
                else:
                    st_val = 0
                    st_name = '??'
                
                if not resDefinesPath:
                    #XXX Eric, my change from printf() to fout.write()
                    #    has *added* a newline at the end of this line.
                    #    I.e. before my change the next line
                    #    (SetSublanguageName()) was in the "// ..." comment.
                    #    Which is correct?
                    fout.write("p_FamilyInfo->Init(%d); // %s\n"
                               % (st_val, st_name))
                    if obj.subLanguageName:
                        fout.write("p_FamilyInfo->SetSublanguageName(\"%s\");"
                                   % obj.subLanguageName)
                else:
                    fout.write("%d:%d\n"
                               % (resConstants['ASTC_F_DEFAULT_STATE'],
                                  st_val))
                    if obj.subLanguageName:
                        self.emitScratchBuffer(fout, obj.subLanguageName)
                        fout.write("%s\n" % resConstants['ASTC_SUBLANGUAGE_NAME'])
            if not resDefinesPath:
                fout.write('\n')
    
            #XXX Don't worry about the constant name, as we'll be generating
            # a compiled table soon.
            keywordList = getattr(obj, 'keywordList', None)
            if keywordList:
                sorted_keywordList = copy.copy(keywordList)
                sorted_keywordList.sort()
                kstring = " ".join(sorted_keywordList)
                if not resDefinesPath:
                    kstring2 = self._split_quote_string(kstring, 68)
                    fout.write("p_FamilyInfo->SetWordList(\"%s\");\n"
                               % kstring2)
                    fout.write("p_FamilyInfo->SetKeywordStyle(%s, %s);\n\n"
                               % (self.fullStyleName(obj.keywordStyle[0]),
                                  self.fullStyleName(obj.keywordStyle[1])))
                else:
                    self.emitScratchBuffer(fout, kstring)
                    fout.write("%d\n" % resConstants['ASTC_F_WORDLIST'])
                    fout.write("%d:%d:%d\n"
                               % (resConstants['ASTC_F_KEYWORD_STYLE'],
                                  resConstants[self.fullStyleName(obj.keywordStyle[0])],
                                  resConstants[self.fullStyleName(obj.keywordStyle[1])]))

            # Now populate the LookBackTables
            tcBlock = getattr(obj, 'tokenCheckBlock', None)
            if tcBlock:
                if not resDefinesPath:
                    fout.write("p_LBTests = p_FamilyInfo->CreateNewLookBackTests();\n")
                    fout.write("if (!p_LBTests) return false;\n")
                else:
                    fout.write("%d\n" % resConstants['ASTC_F_LOOKBACK_TESTS_CREATE'])

                startStyleName = self.fullStyleName(obj.start_style)
                endStyleName = self.fullStyleName(obj.end_style)
                if not resDefinesPath:
                    fout.write("p_LBTests->Init(%s, %s - %s + 1);"
                               % (startStyleName, endStyleName,
                                  startStyleName))
                else:
                    fout.write("%d:%d:%d\n"
                               % (resConstants['ASTC_F_LOOKBACK_TESTS_INIT'],
                                  resConstants[startStyleName],
                                  resConstants[endStyleName] - resConstants[startStyleName]))

                num_tests = len(tcBlock)
                if num_tests > 0:
                    if not resDefinesPath:
                        fout.write("p_LBTests->SetTestCount(%d);" % num_tests)
                    else:
                        fout.write("%d:%d\n"
                                   % (resConstants['ASTC_F_LOOKBACK_TESTS_COUNT'],
                                      num_tests))
                    
                    for i in xrange(0, num_tests):
                        tc = tcBlock[i]
                        sel = tc['selectors']
                        name = tc['name']
                        action = tc['type']
                        if not resDefinesPath:
                            fout.write("p_LBTestObj = p_LBTests->GetTest(%d);" % i)
                            fout.write("if (p_LBTestObj) {\n")
                        else:
                            fout.write("%d:%d\n"
                                       % (resConstants['ASTC_LBT_GET'], i))


                        if 1:
                            #Fake Python "block" to reflect the generated code.
                            if not resDefinesPath:
                                fout.write("p_LBTestObj->SetActionStyle(LBTEST_ACTION_%s, %s);"
                                           % (action.upper(), self.fullStyleName(name)))
                            else:
                                fout.write("%d:%d:%d\n"
                                           % (resConstants['ASTC_LBT_ACTION_STYLE'],
                                              resConstants["LBTEST_ACTION_" + action.upper()],
                                              resConstants[self.fullStyleName(name)]))

                            if sel == 'all':
                                # We're done
                                pass
                            else:
                                die("Expecting an array, got <sel>",
                                    isinstance(sel, dict))
                                if sel:
                                    sel.sort()
                                    kstring = self.escapeStr(" ".join(sel))
                                    set_word_list = self._all_words(sel)
                                    if not resDefinesPath:
                                        kstring2 = self._split_quote_string(kstring, 68)
                                        cmd = (set_word_list and 'SetWordList') or 'SetStrings'
                                        fout.write("p_LBTestObj->%s(\"%s\");"
                                                   % (cmd, kstring2))
                                    else:
                                        self.emitScratchBuffer(fout, kstring)
                                        cmd = (set_word_list and 'ASTC_LBT_WORDLIST') or 'ASTC_LBT_STRINGS'
                                        fout.write("%s\n" % resConstants[cmd])
                                        
                            if not resDefinesPath:
                                fout.write("p_LBTests->SetTest(%d, p_LBTestObj);" % i)
                            else:
                                fout.write("%d:%d\n"
                                           % (resConstants['ASTC_LBT_TEST'], i))
                        if not resDefinesPath:
                            fout.write("}\n")
    
                # Issue the defaults
                tokenValues = {}
                vals = {'reject': 1, 'accept': 2, 'skip': 4}
                defaultActions = ["LBTEST_ACTION_REJECT", # None given, reject all
                                  "LBTEST_ACTION_ACCEPT", # Only rej, acc others
                                  "LBTEST_ACTION_REJECT", # Only acc, rej others
                                  "LBTEST_ACTION_SKIP",	# Acc|rej, skip others
                                  "LBTEST_ACTION_REJECT", # Only skip, rej others
                                  "LBTEST_ACTION_ACCEPT", # Rej|skip, acc others
                                  "LBTEST_ACTION_REJECT", # Acc|skip, rej others
                                  "LBTEST_ACTION_REJECT", # Spec all, rej others
                                 ]
                for tc in tcBlock:
                    sel = tc['selectors']
                    if isinstance(sel, (list, tuple)):
                        name = tc['name']
                        tokenValues[name] = tokenValues.get('name',
                                                            vals[tc['type']])
                style_names = tokenValues.keys()
                style_names.sort()
                for style_name in style_names:
                    if not resDefinesPath:
                        fout.write("p_LBTests->SetDefault(%s, %s);"
                                   % (self.fullStyleName(style_name),
                                      defaultActions[tokenValues[style_name]]))
                    else:
                        fout.write("%d:%d:%d\n"
                                   % (resConstants['ASTC_LBT_DEFAULT'],
                                      resConstants[self.fullStyleName(style_name)],
                                      resConstants[defaultActions[tokenValues[style_name]]]))
    
            flipCount = len(obj.flippers)
            if flipCount > 0:
                for i in xrange(flipCount):
                    node = obj.flippers[i]
                    if not resDefinesPath:
                        fout.write("SetFlipper(%d, \"%s\", %s, %d);"
                                   % (flipIdx, self.escapeStr(node['name']),
                                      self.fullStyleName(node['style']),
                                      node['value']))
                    else:
                        self.emitScratchBuffer(fout, self.escapeStr(node['name']))
                        fout.write("%d:%d:%d:%d\n"
                                   % (resConstants['ASTC_F_FLIPPER'],
                                      flipIdx,
                                      resConstants[self.fullStyleName(node['style'])],
                                      node['value']))
                    flipIdx += 1
    
        # Transition table info and unique states are global
    
        stateTable = self.stateTable
        stateSize = (stateTable and len(stateTable)) or 0
    
        us_hash = self.uniqueStates
        if us_hash:
            keys = us_hash.keys()
            i = 0
            if not resDefinesPath:
                fout.write("p_TransitionTable->SetNumUniqueStates(%d);" % len(keys))
            else:
                fout.write("%d:%d\n"
                           % (resConstants['ASTC_TTABLE_NUM_UNIQUE_STATES'],
                              len(keys)))
            if keys: keys.sort()
            for k in keys:
                k2 = self.fullStyleName(k)
                int_state_name = us_hash[k]
                if not resDefinesPath:
                    fout.write("p_TransitionTable->SetUniqueState(%d, %s, %d); // %s\n"
                               % (i, k2, nameTable[int_state_name],
                                  int_state_name))
                else:
                    fout.write("%d:%d:%d:%d\n"
                               % (resConstants['ASTC_TTABLE_UNIQUE_STATE'],
                                  i, resConstants[k2],
                                  nameTable[int_state_name]))
                i += 1
                
        if not resDefinesPath:
            fout.write("\n\n")
            
        if not (stateTable is None):
            size = len(stateTable)
            if not resDefinesPath:
                fout.write("p_TransitionTable->CreateNewTransitions(%d);"
                           % size)
            else:
                fout.write("%d:%d\n"
                           % (resConstants['ASTC_TTABLE_CREATE_TRANS'],
                              size))
                
        for i in xrange(stateSize):
            stateTrans = stateTable[i]
            if not (stateTrans is None):
                # i is the state number
                old_family_name = self.getFamilyOwner(i)
    
                if not resDefinesPath:
                    fout.write("p_TranBlock = p_TransitionTable->Get(%d);" % i)
                    fout.write("if (!p_TranBlock) return false;\n")
                else:
                    fout.write("%d:%d\n"
                               % (resConstants['ASTC_TTABLE_GET_TBLOCK'], i))

                for stateTran in stateTrans:
                    trans_value = stateTran['value']
                    state_type = None
                    final_trans_value = None
                    ignore_case = 0; # Set to 1 for patterns
                    
                    if stateTran['type'] == 'string':
                        if len(trans_value) == 0:
                            state_type = 'TRAN_SEARCH_EMPTY'
                        else:
                            state_type = 'TRAN_SEARCH_STRING'
                            final_trans_value = '"' + self.escapeStr(trans_value) + '"'
                    elif stateTran['type'] == 'pattern':
                        if len(trans_value[0]) == 0:
                            state_type = 'TRAN_SEARCH_EMPTY'
                            final_trans_value = 'NULL'
                        elif trans_value[0] == '\\z':
                            state_type = 'TRAN_SEARCH_EOF'
                            final_trans_value = 'NULL'
                        else:
                            state_type = 'TRAN_SEARCH_REGEX'
                            final_trans_value = trans_value[0]
                            ignore_case = trans_value[1]
                            
                            obj = self.familyList[old_family_name]
                            die ("Can't get a family obj for state %d" % ((stateTran.get('trans_num', i)),),
                                 obj is None)
                            # Do variable substitution
                            lim = 1000
                            i = 0
                            processed_part = ''
                            while len(final_trans_value) > 0:
                                d1 = final_trans_value.find('$')
                                if d1 == -1:
                                    processed_part += final_trans_value
                                    break
                                d2 = final_trans_value.find('\\')
                                if 0 <= d2 and d2 < d1:
                                    # Pass everything up to and including \. on
                                    # Could be \$, so don't process $ this time
                                    d2 += 2
                                    processed_part += final_trans_value[:d2]
                                    final_trans_value = final_trans_value[d2:]
                                    continue
                                ptn1 = self._has_ptn_var(final_trans_value)
                                if not ptn1:
                                    # Keep $ not followed by a letter
                                    d1 += 1
                                    processed_part += final_trans_value[:d1]
                                    final_trans_value = final_trans_value[d1:]
                                    continue
                                if not obj.patterns.has_key(ptn1):
                                    die("Undefined pattern " + ptn1 + " in str " + trans_value[0] + ", family " + family_name, True)
                                final_trans_value = final_trans_value.replace("$" + ptn1, obj.patterns[ptn1])
                                i += 1
                                if i > lim:
                                    warn("Warning: Possible infinite loop trying to resolve %s -- giving up after %d cycles at final_trans_value"
                                         % (trans_value[0], lim))
                                    processed_part += final_trans_value
                                    break
                                
                            final_trans_value = processed_part.replace('\\', '\\\\')
                            if self.verbose and trans_value[0] != final_trans_value:
                                warn("Mapped %s to %s" % (trans_value[0], final_trans_value))
                            final_trans_value = qq(final_trans_value)
                    elif stateTran['type'] == 'delimiter':
                        state_type = 'TRAN_SEARCH_DELIMITER'
                        final_trans_value = '*current delimiter*'
                    else:
                        die("cmd [%d] -- weird cmd of %s" % (i, trans_value), False)
                    # final_trans_value =~ s/([\\\"])/\\$1/g;  # Escape problem chars
                    redo = 'false'
                    no_keyword = 'false'
                    colors = {'upto' : '-1', 'include' : '-1'}
                    cmds = stateTran.get('cmds', [])
                    pushPopStateDirective = replaceStateDirective = None
                    eolDirective = setDelimiterDirective = None
                    setOppositeDelimiterDirective = None
                    keepDelimiterDirective = None
                    for cmd in cmds:
                        if cmd[0] == 'paint':
                            cmd_val = cmd[1]
                            die("Unexpected type of " + cmd_val['type'],
                                colors[cmd_val['type']] is None)
                            colors[cmd_val['type']] = self.fullStyleName(cmd_val['value'])
                        elif cmd[0] == 'redo':
                            redo = 'true'
                        elif cmd[0] == 'no_keyword':
                            no_keyword = 'true'
                        elif cmd[0] == 'spush_check':
                            target_state_name = cmd[1]
                            die("No state name to push", target_state_name is None)
                            if pushPopStateDirective:
                                die("Can't push and pop at state " +
                                    self.nameInfo[i]['name'] +
                                    " matching " + final_trans_value,
                                    True)
                            target_state_num = self._state_num_from_name(nameTable, target_state_name, cmd[0])
                            new_family_name = self.getFamilyOwner(target_state_num)
                            if not resDefinesPath:
                                pushPopStateDirective = ("p_Tran->SetPushState(%d, %s);" % (target_state_num, self.families[new_family_name]))
                            else:
                                pushPopStateDirective = \
                                    ("%d:%d:%d" % (
                                            resConstants['ASTC_TRAN_PUSH_STATE'],
                                            target_state_num,
                                            self.families[new_family_name]))
                                
                        elif cmd[0] == 'sstack_set':
                            target_state_name = cmd[1]
                            die("No state name to set", target_state_name is None)
                            target_state_num = self._state_num_from_name(nameTable, target_state_name, cmd[0])
                            new_family_name = self.getFamilyOwner(target_state_num)
                            if not resDefinesPath:
                                replaceStateDirective = ("p_Tran->ReplacePushState(%d, %s);" %
                                                         (target_state_num, self.families[new_family_name]))
                            else:
                                replaceStateDirective = \
                                    ("%d:%d:%d" % (
                                            resConstants['ASTC_TRAN_REPLACE_STATE'],
                                            target_state_num,
                                            self.families[new_family_name]))
                                
                        elif cmd[0] == 'spop_check':
                            if pushPopStateDirective:
                                die("Can't both push and pop at state " +
                                    self.nameInfo[i]['name'] +
                                    " matching " +
                                    final_trans_value, pushPopStateDirective)
                            if not resDefinesPath:
                                pushPopStateDirective = "p_Tran->SetPopState();"
                            else:
                                pushPopStateDirective = str(resConstants['ASTC_TRAN_POP_STATE'])
                        elif cmd[0] == 'at_eol':
                            target_state_name = cmd[1]
                            die("No state name at eof", target_state_name is None)
                            target_state_num = self._state_num_from_name(nameTable, target_state_name, cmd[0])
                            new_family_name = self.getFamilyOwner(target_state_num)
                            if not resDefinesPath:
                                eolDirective = ("p_Tran->SetEolTransition(%d, %s);" % (target_state_num, self.families[new_family_name]))
                            else:
                                eolDirective = \
                                    ("%d:%d:%d" % (
                                            resConstants['ASTC_TRAN_EOL_STATE'],
                                            target_state_num,
                                            self.families[new_family_name]))
                        elif cmd[0] == 'keep_delimiter':
                            if state_type != 'TRAN_SEARCH_DELIMITER':
                                raise LudditeError("The %s action can only be specified when matching against a delimiter" %
                                                   (cmd[0],));                            
                            if not resDefinesPath:
                                keepDelimiterDirective = ("p_Tran->KeepDelimiter();")
                            else:
                                keepDelimiterDirective = str(resConstants['ASTC_TRAN_KEEP_DELIMITER'])
                        elif cmd[0] == 'set_delimiter':
                            if state_type != 'TRAN_SEARCH_REGEX':
                                raise LudditeError("The %s action can only be specified when matching patterns" %
                                                   (cmd[0],));
                            if not resDefinesPath:
                                setOppositeDelimiterDirective = ("p_Tran->SetDelimiter(false, %s);" % (cmd[1]))
                            else:
                                setOppositeDelimiterDirective = \
                                    ("%d:0:%s" % (
                                            resConstants['ASTC_TRAN_SET_DELIMITER'],
                                            cmd[1]))
                        elif cmd[0] == 'set_opposite_delimiter':
                            if state_type != 'TRAN_SEARCH_REGEX':
                                raise LudditeError("The %s action can only be specified when matching patterns, %s-%s given" %
                                                   (cmd[0], stateTran['type'], trans_value or ""));
                            if not resDefinesPath:
                                setDelimiterDirective = ("p_Tran->SetDelimiter(true, %s);" % (cmd[1]))
                            else:
                                setDelimiterDirective = \
                                    ("%d:1:%s" % (
                                            resConstants['ASTC_TRAN_SET_DELIMITER'],
                                            cmd[1]))
                        elif cmd[0] == 'clear_delimiter':
                            if not resDefinesPath:
                                setDelimiterDirective = ("p_Tran->ClearDelimiter();")
                            else:
                                setDelimiterDirective = \
                                    ("%d" % (
                                            resConstants['ASTC_TRAN_CLEAR_DELIMITER'],))
                        else:
                            die("Unexpected cmd type of " + cmd[0], True)
                    if redo == 'true' and colors['include'] != '-1':
                        raise LudditeError("Error in state %s, transition %s: the include paint action and the redo action can't be given for the same transition" % (st_name, final_trans_value))
                    final_state = final_state_comment = None
                    new_family_name = None
                    final_state = stateTran.get('trans_num', None)
                    if not (final_state is None):
                        new_family_name = self.getFamilyOwner(final_state)
                        final_state_comment = (" // => %s " %
                                               (stateTran.get('trans_str', '??'),))
                    else:
                        final_state = -1
                        final_state_comment = ''
                        new_family_name = old_family_name
                    token_check = (stateTran.get('token_check', 0)) or 0
                    cmd = None
                    if not resDefinesPath:
                        cmd = ((state_type == 'TRAN_SEARCH_EOF') and 'SetEOFInfo'
                                or (((state_type == 'TRAN_SEARCH_EMPTY') and 'SetEmptyInfo')
                                    or 'Append'))
                    else:
                        cmd = ((state_type == 'TRAN_SEARCH_EOF') and 'ASTC_TBLOCK_EOF_TRAN'
                                or (((state_type == 'TRAN_SEARCH_EMPTY') and 'ASTC_TBLOCK_EMPTY_TRAN')
                                    or 'ASTC_TBLOCK_APPEND_TRAN'))
                                
                    if not resDefinesPath:
                        fout.write("p_Tran = new Transition(%s, %s, %s, %s, %s, %d, %d, %s, %d);%s\n"
                                   % (state_type, final_trans_value,
                                      colors['upto'], colors['include'],
                                      redo, final_state, token_check,
                                      ignore_case, no_keyword, final_state_comment))
                    else:
                        self.emitScratchBuffer(fout, final_trans_value)
                        fout.write("%d:%d:%d:%d:%d:%d:%d:%d:%d\n"
                                   % (resConstants['ASTC_CREATE_NEW_TRAN'],
                                      resConstants[state_type],
                                      colors['upto'] == "-1" and -1 or resConstants[colors['upto']],
                                      colors['include'] == "-1" and -1 or resConstants[colors['include']],
                                      redo == 'true' and 1 or 0,
                                      final_state,
                                      token_check and 1 or 0,
                                      ignore_case,
                                      no_keyword == 'true' and 1 or 0
                                      ))
                    for directive in [pushPopStateDirective, replaceStateDirective, eolDirective,
                                      setDelimiterDirective,
                                      setOppositeDelimiterDirective,
                                      keepDelimiterDirective]:
                        if directive:
                            fout.write(directive + "\n")
                    if not resDefinesPath:
                        fout.write("p_TranBlock->" + cmd + "(p_Tran);" + "\n")
                    else:
                        fout.write("%d\n" % resConstants[cmd])

                    if old_family_name != new_family_name:
                        if not resDefinesPath:
                            fout.write("p_Tran->SetNewFamily(%d); // %s\n"
                                       % (self.families[new_family_name],
                                          new_family_name))
                        else:
                            fout.write("%d:%d\n"
                                       % (resConstants['ASTC_TRAN_SET_F'],
                                          self.families[new_family_name]))
        fout.close()

    def dumpLanguageService(self, path, guid, ext=None, add_missing=False):
        if not self.languageName:
            raise LudditeError("'language' was not specified in .udl file")

        if add_missing:
            manifest_path = join(dirname(path), "chrome.manifest")
            if exists(manifest_path):
                leaf = basename(path)
                with open(manifest_path, "rU") as manifest:
                    for line in manifest:
                        directive = line.split()
                        if directive[:2] == ["component", guid]:
                            if directive[2:3] != ["components/%s" % leaf]:
                                return # file exists
                            break

        lang_from_udl_family = {}
        for udl_family, curr_info in self.familyList.items():
            norm_udl_family = {"csl": "CSL", "css": "CSS",
                               "markup": "M", "ssl": "SSL",
                               "tpl": "TPL"}[udl_family]
            lang_from_udl_family[norm_udl_family] = curr_info.subLanguageName
        data = {
            'langName': self.languageName,
            'safeLangName': self.safeLangName,
            'guid': guid,
            'date': datetime.datetime.now().ctime(),
            'defaultExtDecl': (ext and 'defaultExtension = %r' % ext or None),
            'lang_from_udl_family': lang_from_udl_family,
            'baseImport': "koUDLLanguageBase",
            'baseClass': "KoUDLLanguage",
        }
        if 'M' in lang_from_udl_family:
            if lang_from_udl_family["M"] == "XML":
                data['baseImport'] = "koXMLLanguageBase"
                data['baseClass'] = "koXMLLanguageBase"
            elif lang_from_udl_family["M"] == "HTML":
                data['baseImport'] = "koXMLLanguageBase"
                data['baseClass'] = "koHTMLLanguageBase"
            
        fout = open(path, "w")
        try:
            template = """# Komodo %(langName)s language service.

import logging
from %(baseImport)s import %(baseClass)s


log = logging.getLogger("ko%(safeLangName)sLanguage")
#log.setLevel(logging.DEBUG)


def registerLanguage(registry):
    log.debug("Registering language %(langName)s")
    registry.registerLanguage(Ko%(safeLangName)sLanguage())


class Ko%(safeLangName)sLanguage(%(baseClass)s):
    name = "%(langName)s"
    lexresLangName = "%(safeLangName)s"
    _reg_desc_ = "%%s Language" %% name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%%s;1" %% name
    _reg_clsid_ = "%(guid)s"
    _reg_categories_ = [("komodo-language", name)]
    %(defaultExtDecl)s

    lang_from_udl_family = %(lang_from_udl_family)r

"""
            fout.write(template % data)
            for groupMap in self.languageService_xmlNames.values():
                langSvcName = groupMap[0]
                groupVals = groupMap[1]
                names = groupVals.keys()
                if len(names) > 0:
                    #XXX escaping needed on the values?
                    fout.write('    %s = ["%s"]\n' % (langSvcName, '", "'.join(names)))
            if hasattr(self, 'sample'):
                fout.write('\n\n    sample = r"""%s"""\n' % self.sample)
        finally:
            fout.close()

    def emitScratchBuffer(self, fout, s):
        if self._re_dequote_start is None:
            self._re_dequote_start = re.compile('^[\'\"]')
            self._re_dequote_end = re.compile('[\'\"]$')

            self.re_bspair = re.compile(r'(\\)\\(.*)$')
            self.re_escaped_quote = re.compile(r'\\([\'\"])(.*)$')
            self.re_escaped_other = re.compile(r'(\\.)(.*)$')
            self.re_non_escape = re.compile(r'([^\\]+)(.*)$')
            self.re_esb_set = [self.re_bspair,
                               self.re_escaped_quote,
                               self.re_escaped_other,
                               self.re_non_escape,]
            self.re_75 = re.compile('(.{1,75})(.*)$', re.DOTALL)
            
        s1 = re.sub(self._re_dequote_end, '',
                    re.sub(self._re_dequote_start, '', s))

        # todo: unescape \' and \"
        # leave \r and \n alone
        # map all pairs \\ to \
        pieces = []
        while len(s1) > 0:
            did_match = False
            for this_re in self.re_esb_set:
                mobj = this_re.match(s1)
                if mobj:
                    pieces.append(mobj.group(1))
                    s1 = mobj.group(2)
                    did_match = True
                    break
            if not did_match:
                die("emitScratchBuffer: Can't match '" + s1 + "'", True)
        s2 = "".join(pieces)
        
        # $kstring =~ s/(?<=[^\\](?:\\\\)*)\\([\'\"])/$1/g;
        # $kstring =~ s/\\\\/\\/g;  # We don't need to escape quotes and backslashes
        fout.write("%d:%d\n"
                   % (self.resConstants['ASTC_SCRATCH_BUFFER_START'],
                      len(s2)))
        
        while len(s2) > 0:
            mobj = self.re_75.match(s2)
            die("Can't match anything on " + s2, mobj is None)
            fout.write("%d:%s\n"
                       % (self.resConstants['ASTC_SCRATCH_BUFFER_APPEND'],
                          mobj.group(1)))
            s2 = mobj.group(2)

    def escapeStr(self, s):
        return s.replace('\'', '\\\'').replace('"', '\\"').replace('\t', '\\t')

    def fullStyleName(self, k):
        if not k.startswith("SCE_UDL_"):
            k2 = 'SCE_UDL_' + k
        else:
            k2 = k
        if self.resConstants and not self.resConstants.has_key(k2):
            die("Style " + k2 + " is unknown. ", True)
        return k2

    def generateKomodoTemplateFile(self, template_path):
        f = open(template_path, "w")
        # Just an empty template for now.
        f.close()

    def getFamilyOwner(self, stateNum):
        die ("No owning family for state #" + str(stateNum),
             not self.nameInfo[stateNum].has_key('owningFamily'))
        familyName = self.nameInfo[stateNum]['owningFamily']
        die ("No owning family for state #" + str(stateNum),
             familyName is None)
        return familyName
        
    def internStateName(self, name):        
        nameTable = self.nameTable
        if not nameTable.has_key(name):
            self.stateCount += 1
            stateNum = nameTable[name] = self.stateCount
            test_assign_entry(self.nameInfo, stateNum, {})
            self.nameInfo[stateNum]['name'] = name
        return nameTable[name]

    def setFamilyOwner(self, stateNum, permFamilyInfo):
        nameInfo = self.nameInfo
        test_assign_entry(nameInfo, stateNum, {})
        nameInfo[stateNum]['owningFamily'] = nameInfo[stateNum].get('owningFamily', permFamilyInfo.currFamily)
        
class CurrentInfo:
    def __init__(self, currFamily):
        self.patterns = {}
        self.flippers = []
        self.initialState = None
        self.currFamily = currFamily
        self.subLanguageName = None
        self.specified = False

    def __repr__(self):
        return "<CurrentInfo %r>" % self.subLanguageName
    
class Analyzer:
    def __init__(self, mainObj):
        self.mainObj = mainObj
        
    def semanticCheck(self):
        familyNames = [x.lower() for x in self.mainObj.familyList.keys()]
        for k in familyNames:
            if not self.mainObj.families.has_key(k):
                warn("Family %s isn't recognized, expected one of [%s]\n",
                     k, " ".join(self.mainObj.families.keys()))
                return
        for k in familyNames:
            obj = self.mainObj.familyList[k]
            if obj.specified:
                if obj.subLanguageName is None:
                    warn("No sublanguage name specified for family %s",
                         obj.currFamily)
            if hasattr(obj, 'tokenCheckBlock'):
                if not (hasattr(obj, 'start_style')
                        and hasattr(obj, 'end_style')):
                    msg = """No %s specified.  To do look-back token checking,
        you need to specify which styles are the start_style and the end_style.
        See the sample JavaScript lexer.\n"""
                    if not hasattr(obj, 'start_style'):
                        warn(msg, 'start_style')
                    else:
                        warn(msg, 'end_style')
                    return
            if hasattr(obj, 'keywordList'):
                ok = True
                try:
                    if not (obj.keywordStyle[0] and obj.keywordStyle[1]):
                        ok = False
                except:
                    ok = False
                if not ok:
                    warn("keywords were specified, but no keyword_style statement was given,\nlike <<keyword_style CSS_IDENTIFIER => CSS_WORD>>\n")
                    return
            # Make sure no states put us in dead ends
            nameTable = self.mainObj.nameTable
            nameInfo = self.mainObj.nameInfo
            for state_name in nameTable.keys():
                state_num = nameTable[state_name]
                if not nameInfo[state_num].has_key('owningFamily'):
                    warn("At least one transition moves to undefined state " + state_name +
                    "\n This state needs to be defined somewhere.\n")
                    return
        if self.mainObj.languageName is None:
            warn("No main language declaration given -- this language needs a name")
            return
        return True

    def _assign_once_dups_ok(self, obj, attrname, new_val, extra_msg=''):
        if not hasattr(obj, attrname):
            setattr(obj, attrname, new_val)
            return
        old_val = getattr(obj, attrname)
        if old_val is None:
            setattr(obj, attrname, new_val)
            return
        if old_val == new_val:
            return
        raise LudditeError(
            'Already specified %s "%s"%s, now specifying "%s"'
            % (attrname, extra_msg, old_val, new_val))
        
    def processTree(self, tree, currFamily='markup'):
        if not self.mainObj.familyList.has_key(currFamily):
            self.mainObj.familyList[currFamily] = CurrentInfo(currFamily)
        permFamilyInfo = self.mainObj.familyList[currFamily]
        for node in tree:
            if node[0] == 'module':
                self.processTree(node[1], currFamily)
            elif node[0] == 'pattern':
                node2 = node[1]
                permFamilyInfo.patterns[node2['name']] = node2['value']
            elif node[0] == 'family':
                # Stay with names for now
                currFamily = node[1].lower()
                self.mainObj.familyList[currFamily] = self.mainObj.familyList.get(currFamily, CurrentInfo(currFamily))
                permFamilyInfo = self.mainObj.familyList[currFamily]
                permFamilyInfo.specified = True
            elif node[0] == 'initial':
                permFamilyInfo.initialState = permFamilyInfo.initialState or node[1]['name']
            elif node[0] == 'language':
                self._assign_once_dups_ok(self.mainObj, 'languageName', node[1])
            elif node[0] == 'sublanguage':
                self._assign_once_dups_ok(permFamilyInfo, 'subLanguageName', node[1],
                                          "for family " + currFamily)
            elif node[0] == 'stateBlock':
                node2 = node[1]
                stateName = node2['name']
                stateNum = self.mainObj.internStateName(stateName)
                self.mainObj.setFamilyOwner(stateNum, permFamilyInfo)
                stateBlock = node2['value']
                test_assign_entry(self.mainObj.stateTable, stateNum, [])
                stateTable = self.mainObj.stateTable[stateNum]
    
                # Variables to track for synthesizing an eof action
                common_color = None
                synthesize_eof = True
                for transition in stateBlock:
                    if transition[0] != 'transition':
                        raise LudditeError("Expecting 'transition', got %s"
                                           % transition[0])
                    
                    inner_tran = transition[1]
                    inner_data = { 'type' : inner_tran['type'],
                                   'value' : inner_tran['value'],
                                   'token_check' : inner_tran['token_check'],
                                   }
                    if inner_tran['cmds']:
                        inner_data['cmds'] = inner_tran['cmds']
                    
                    if inner_tran['trans']:
                        inner_data['trans_str'] = inner_tran['trans']
                        inner_data['trans_num'] = self.mainObj.internStateName(inner_tran['trans'])
                    
                    # Check for synthesizing eof transition
                    curr_color = self._favor_upto_color(inner_tran['cmds'])
                    if curr_color and not isTemplateStateName(stateName):
                        # These are global across all families
                        if not self.mainObj.holdUniqueStates.has_key(curr_color):
                            self.mainObj.holdUniqueStates[curr_color] = {}
                        self.mainObj.holdUniqueStates[curr_color][stateName] = None
                    
                    if synthesize_eof:
                        if not inner_tran['cmds']:
                            # A transition with no commands doesn't affect
                            # EOF-synthesis
                            pass
                        elif inner_tran['type'] == 'pattern' and inner_tran['value'] == r'\z':
                            # They specified an explicit EOF transition
                            synthesize_eof = False
                        elif not curr_color:
                            synthesize_eof = False
                        elif common_color is None:
                            common_color = curr_color
                        elif common_color != curr_color:
                            synthesize_eof = False
                        
                    stateTable.append(inner_data)
                    
                if synthesize_eof:
                    if common_color is not None:
                        inner_data = { 'type' : 'pattern',
                                       'value' : [r'\z', 0],
                                       'cmds' : [[ 'paint',
                                                   { 'type' : 'upto',
                                                     'value' : common_color},
                                                    ]],
                                       }
                        stateTable.append(inner_data)
                    else:
                        warn("State %s might need an explicit \\z pattern rule" % (stateName,))
                
            elif node[0] == 'keywordList':
                permFamilyInfo.keywordList = node[1]
            elif node[0] == 'keywordStyle':
                permFamilyInfo.keywordStyle = [node[1], node[2]]
            elif node[0] == 'tokenCheckBlock':
                permFamilyInfo.tokenCheckBlock = node[1]
            elif node[0] == 'start_style':
                permFamilyInfo.start_style = node[1]
            elif node[0] == 'end_style':
                permFamilyInfo.end_style = node[1]
            elif node[0] == 'fold':
                permFamilyInfo.flippers.append(node[1])
            elif node[0] in ('namespace', 'public_id', 'system_id'):
                name = node[1]
                self.mainObj.languageService_xmlNames[node[0]][1][name] = None

    def _favor_upto_color(self, cmds):
        # Favor the upto-color, but use the include-color if that's all they gave
        if cmds is None: return None
        color = None
        for cmd in cmds:
            if not isinstance(cmd, (list, tuple)):
                continue
            if cmd[0] == 'paint':
                if cmd[1]['type'] == 'upto':
                    return cmd[1]['value']
                else:
                    color = cmd[1]['value']
        return color
    
    
