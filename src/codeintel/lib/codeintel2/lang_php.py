#!/usr/bin/env python
# Copyright (c) 2006 ActiveState Software Inc.
# See LICENSE.txt for license details.
#
# Contributors:
#   Shane Caraveo (ShaneC@ActiveState.com)
#   Trent Mick (TrentM@ActiveState.com)
#   Todd Whiteman (ToddW@ActiveState.com)

"""codeintel support for PHP"""

import os
from os.path import isdir, join
import sys
import md5
import re
import logging
import time
import warnings
from cStringIO import StringIO
import weakref
from os.path import basename, splitext
from glob import glob

from SilverCity.ScintillaConstants import (SCE_UDL_SSL_DEFAULT,
                                           SCE_UDL_SSL_OPERATOR,
                                           SCE_UDL_SSL_IDENTIFIER,
                                           SCE_UDL_SSL_WORD,
                                           SCE_UDL_SSL_VARIABLE,
                                           SCE_UDL_SSL_STRING,
                                           SCE_UDL_SSL_NUMBER,
                                           SCE_UDL_SSL_COMMENT,
                                           SCE_UDL_SSL_COMMENTBLOCK)

from codeintel2.parseutil import *
from codeintel2.citadel import ImportHandler
from codeintel2.udl import UDLBuffer, UDLLexer, UDLCILEDriver, is_udl_csl_style, XMLParsingBufferMixin
from codeintel2.common import *
from codeintel2 import util
from codeintel2.indexer import PreloadBufLibsRequest
from codeintel2.gencix_utils import *
from codeintel2.tree_php import PHPTreeEvaluator
from codeintel2.langintel import (LangIntel, ParenStyleCalltipIntelMixin,
                                  ProgLangTriggerIntelMixin)
from codeintel2.accessor import AccessorCache

try:
    from xpcom.server import UnwrapObject
    _xpcom_ = True
except ImportError:
    _xpcom_ = False



#---- global data

lang = "PHP"
log = logging.getLogger("codeintel.php")
#log.setLevel(logging.DEBUG)


#---- language support


# XXX later these need to be centralized.
# XXX - Move this crud!!
keywords = [
            # new to php5
            "public", "private", "protected", "final",
            "abstract", "interface", "implements",
            "try", "catch", "throw", "instanceof",
            # existed in php4
            "define", "true", "false", 
            "int", "integer", "real", "double",
            "float", "string",  "object", "bool", "boolean",
            "this", "self", "virtual", "parent", "null",
            # http://www.php.net/manual/en/reserved.php#reserved.keywords
            "and", "or", "xor", "__file__", "__line__",
            "array", "as", "break", "case", "cfunction",
            "class", "const", "continue", "declare"
            "default", "die", "do", "echo", "else",
            "elseif", "empty", "enddeclare", "endfor", "endforeach",
            "endif", "endswitch", "endwhile", "eval", "exit",
            "extends", "for", "foreach", "function", "global",
            "if", "include", "include_once", "isset", "list",
            "new", "old_function", "print", "require", "require_once",
            "return", "static", "switch", "unset", "use",
            "var", "while", "_function_", "_class_",
            # http://www.php.net/manual/en/reserved.constants.core.php
            "php_version",
            "php_os",
            "default_include_path",
            "pear_install_dir",
            "pear_extension_dir",
            "php_extension_dir",
            "php_bindir",
            "php_libdir",
            "php_datadir",
            "php_sysconfdir",
            "php_localstatedir",
            "php_config_file_path",
            "php_output_handler_start",
            "php_output_handler_cont",
            "php_output_handler_end",
            "e_error",
            "e_warning",
            "e_parse",
            "e_notice",
            "e_core_error",
            "e_core_warning",
            "e_compile_error",
            "e_compile_warning",
            "e_user_error",
            "e_user_warning",
            "e_user_notice",
            "e_all",
            # http://www.php.net/manual/en/reserved.constants.standard.php
            "extr_overwrite",
            "extr_skip",
            "extr_prefix_same",
            "extr_prefix_all",
            "extr_prefix_invalid",
            "extr_prefix_if_exists",
            "extr_if_exists",
            "sort_asc",
            "sort_desc",
            "sort_regular",
            "sort_numeric",
            "sort_string",
            "case_lower",
            "case_upper",
            "count_normal",
            "count_recursive",
            "assert_active",
            "assert_callback",
            "assert_bail",
            "assert_warning",
            "assert_quiet_eval",
            "connection_aborted",
            "connection_normal",
            "connection_timeout",
            "ini_user",
            "ini_perdir",
            "ini_system",
            "ini_all",
            "m_e",
            "m_log2e",
            "m_log10e",
            "m_ln2",
            "m_ln10",
            "m_pi",
            "m_pi_2",
            "m_pi_4",
            "m_1_pi",
            "m_2_pi",
            "m_2_sqrtpi",
            "m_sqrt2",
            "m_sqrt1_2",
            "crypt_salt_length",
            "crypt_std_des",
            "crypt_ext_des",
            "crypt_md5",
            "crypt_blowfish",
            "directory_separator",
            "seek_set",
            "seek_cur",
            "seek_end",
            "lock_sh",
            "lock_ex",
            "lock_un",
            "lock_nb",
            "html_specialchars",
            "html_entities",
            "ent_compat",
            "ent_quotes",
            "ent_noquotes",
            "info_general",
            "info_credits",
            "info_configuration",
            "info_modules",
            "info_environment",
            "info_variables",
            "info_license",
            "info_all",
            "credits_group",
            "credits_general",
            "credits_sapi",
            "credits_modules",
            "credits_docs",
            "credits_fullpage",
            "credits_qa",
            "credits_all",
            "str_pad_left",
            "str_pad_right",
            "str_pad_both",
            "pathinfo_dirname",
            "pathinfo_basename",
            "pathinfo_extension",
            "char_max",
            "lc_ctype",
            "lc_numeric",
            "lc_time",
            "lc_collate",
            "lc_monetary",
            "lc_all",
            "lc_messages",
            "abday_1",
            "abday_2",
            "abday_3",
            "abday_4",
            "abday_5",
            "abday_6",
            "abday_7",
            "day_1",
            "day_2",
            "day_3",
            "day_4",
            "day_5",
            "day_6",
            "day_7",
            "abmon_1",
            "abmon_2",
            "abmon_3",
            "abmon_4",
            "abmon_5",
            "abmon_6",
            "abmon_7",
            "abmon_8",
            "abmon_9",
            "abmon_10",
            "abmon_11",
            "abmon_12",
            "mon_1",
            "mon_2",
            "mon_3",
            "mon_4",
            "mon_5",
            "mon_6",
            "mon_7",
            "mon_8",
            "mon_9",
            "mon_10",
            "mon_11",
            "mon_12",
            "am_str",
            "pm_str",
            "d_t_fmt",
            "d_fmt",
            "t_fmt",
            "t_fmt_ampm",
            "era",
            "era_year",
            "era_d_t_fmt",
            "era_d_fmt",
            "era_t_fmt",
            "alt_digits",
            "int_curr_symbol",
            "currency_symbol",
            "crncystr",
            "mon_decimal_point",
            "mon_thousands_sep",
            "mon_grouping",
            "positive_sign",
            "negative_sign",
            "int_frac_digits",
            "frac_digits",
            "p_cs_precedes",
            "p_sep_by_space",
            "n_cs_precedes",
            "n_sep_by_space",
            "p_sign_posn",
            "n_sign_posn",
            "decimal_point",
            "radixchar",
            "thousands_sep",
            "thousep",
            "grouping",
            "yesexpr",
            "noexpr",
            "yesstr",
            "nostr",
            "codeset",
            "log_emerg",
            "log_alert",
            "log_crit",
            "log_err",
            "log_warning",
            "log_notice",
            "log_info",
            "log_debug",
            "log_kern",
            "log_user",
            "log_mail",
            "log_daemon",
            "log_auth",
            "log_syslog",
            "log_lpr",
            "log_news",
            "log_uucp",
            "log_cron",
            "log_authpriv",
            "log_local0",
            "log_local1",
            "log_local2",
            "log_local3",
            "log_local4",
            "log_local5",
            "log_local6",
            "log_local7",
            "log_pid",
            "log_cons",
            "log_odelay",
            "log_ndelay",
            "log_nowait",
            "log_perror"
            ]

PHP_KEYWORDS_LOOKUP = util.make_short_name_dict(keywords, length=2)

class PHPLexer(UDLLexer):
    lang = lang

class PHPLangIntel(LangIntel, ParenStyleCalltipIntelMixin,
                   ProgLangTriggerIntelMixin):
    # Used by ProgLangTriggerIntelMixin.preceding_trg_from_pos()
    trg_chars = tuple('$>:(, ')
    calltip_trg_chars = tuple('(')

    # named styles used by the class
    whitespace_style = SCE_UDL_SSL_DEFAULT
    operator_style   = SCE_UDL_SSL_OPERATOR
    identifier_style = SCE_UDL_SSL_IDENTIFIER
    keyword_style    = SCE_UDL_SSL_WORD
    variable_style   = SCE_UDL_SSL_VARIABLE
    ignore_styles    = (SCE_UDL_SSL_COMMENT, SCE_UDL_SSL_COMMENTBLOCK)
    # ignore_styles_ws, includes whitespace styles
    ignore_styles_ws = ignore_styles + (whitespace_style, )

    def _functionCalltipTrigger(self, ac, pos, DEBUG=False):
        # Implicit calltip triggering from an arg separater ",", we trigger a
        # calltip if we find a function open paren "(" and function identifier
        #   http://bugs.activestate.com/show_bug.cgi?id=70470
        if DEBUG:
            print "Arg separater found, looking for start of function"
        # Move back to the open paren of the function
        paren_count = 0
        p = pos
        min_p = max(0, p - 200) # look back max 200 chars
        while p > min_p:
            p, c, style = ac.getPrecedingPosCharStyle(ignore_styles=self.ignore_styles)
            if style == self.operator_style:
                if c == ")":
                    paren_count += 1
                elif c == "(":
                    if paren_count == 0:
                        # We found the open brace of the func
                        trg_from_pos = p+1
                        p, ch, style = ac.getPrevPosCharStyle()
                        if DEBUG:
                            print "Function start found, pos: %d" % (p, )
                        if style in self.ignore_styles_ws:
                            # Find previous non-ignored style then
                            p, c, style = ac.getPrecedingPosCharStyle(style, self.ignore_styles_ws)
                        if style in (self.identifier_style, self.keyword_style):
                            return Trigger(lang, TRG_FORM_CALLTIP,
                                           "call-signature",
                                           trg_from_pos, implicit=True)
                    else:
                        paren_count -= 1
                elif c in ";{}":
                    # Gone too far and noting was found
                    if DEBUG:
                        print "No function found, hit stop char: %s at p: %d" % (c, p)
                    return None
        # Did not find the function open paren
        if DEBUG:
            print "No function found, ran out of chars to look at, p: %d" % (p,)
        return None

    #@util.hotshotit
    def trg_from_pos(self, buf, pos, implicit=True, DEBUG=False, ac=None):
        if pos < 4:
            return None

        #DEBUG = True
        # Last four chars and styles
        if ac is None:
            ac = AccessorCache(buf.accessor, pos, fetchsize=4)
        last_pos, last_char, last_style = ac.getPrevPosCharStyle()
        prev_pos, prev_char, prev_style = ac.getPrevPosCharStyle()
        # Bump up how much text is retrieved when cache runs out
        ac.setCacheFetchSize(20)

        if DEBUG:
            print "\nphp trg_from_pos"
            print "  last_pos: %s" % last_pos
            print "  last_char: %s" % last_char
            print "  last_style: %r" % last_style
            ac.dump()

        try:
            if last_style == self.whitespace_style:
                if DEBUG:
                    print "Whitespace style"
                WHITESPACE = tuple(" \t\n\r\v\f")
                if not implicit:
                    # If we're not already at the keyword style, find it
                    if prev_style != self.keyword_style:
                        prev_pos, prev_char, prev_style = ac.getPrecedingPosCharStyle(last_style, self.ignore_styles)
                        if DEBUG:
                            print "Explicit: prev_pos: %d, style: %d, ch: %r" % (prev_pos, prev_style, prev_char)
                else:
                    prev_pos = pos - 2
                if last_char in WHITESPACE and \
                    (prev_style == self.keyword_style or
                     (prev_style == self.operator_style and prev_char == ",")):
                    p = prev_pos
                    style = prev_style
                    ch = prev_char
                    #print "p: %d" % p
                    while p > 0 and style == self.operator_style and ch == ",":
                        p, ch, style = ac.getPrecedingPosCharStyle(style, self.ignore_styles_ws)
                        #print "p 1: %d" % p
                        if p > 0 and style == self.identifier_style:
                            # Skip the identifier too
                            p, ch, style = ac.getPrecedingPosCharStyle(style, self.ignore_styles_ws)
                            #print "p 2: %d" % p
                    if DEBUG:
                        ac.dump()
                    p, text = ac.getTextBackWithStyle(style, self.ignore_styles, max_text_len=len("implements"))
                    if DEBUG:
                        print "ac.getTextBackWithStyle:: pos: %d, text: %r" % (p, text)
                    if text in ("new", "extends"):
                        return Trigger(lang, TRG_FORM_CPLN, "classes", pos, implicit)
                    elif text in ("implements", ):
                        return Trigger(lang, TRG_FORM_CPLN, "interfaces", pos, implicit)
                    elif prev_style == self.operator_style and \
                         prev_char == "," and implicit:
                        return self._functionCalltipTrigger(ac, prev_pos, DEBUG)
            elif last_style == self.operator_style:
                if DEBUG:
                    print "  lang_style is operator style"
                    print "Prev char: %r" % (prev_char)
                    ac.dump()
                if last_char == ":":
                    if not prev_char == ":":
                        return None
                    ac.setCacheFetchSize(10)
                    p, c, style = ac.getPrecedingPosCharStyle(prev_style, self.ignore_styles)
                    if DEBUG:
                        print "Preceding: %d, %r, %d" % (p, c, style)
                    if style is None:
                        return None
                    elif style == self.keyword_style:
                        # Check if it's a "self::" or "parent::" expression
                        p, text = ac.getTextBackWithStyle(self.keyword_style,
                                                          # Ensure we don't go too far
                                                          max_text_len=6)
                        if DEBUG:
                            print "Keyword text: %d, %r" % (p, text)
                            ac.dump()
                        if text not in ("parent", "self"):
                            return None
                    return Trigger(lang, TRG_FORM_CPLN, "object-members",
                                   pos, implicit)
                elif last_char == ">":
                    if prev_char == "-":
                        p, c, style = ac.getPrecedingPosCharStyle(prev_style, self.ignore_styles)
                        if style in (self.variable_style, self.identifier_style):
                            return Trigger(lang, TRG_FORM_CPLN, "object-members",
                                           pos, implicit)
                        elif DEBUG:
                            print "Preceding style is not a variable, pos: %d, style: %d" % (p, style)
                elif last_char in "(,":
                    # where to trigger from, updated by "," calltip handler
                    if DEBUG:
                        print "Checking for function calltip"

                    # Implicit calltip triggering from an arg separater ","
                    #   http://bugs.activestate.com/show_bug.cgi?id=70470
                    if implicit and last_char == ',':
                        return self._functionCalltipTrigger(ac, prev_pos, DEBUG)

                    if prev_style in self.ignore_styles_ws:
                        # Find previous non-ignored style then
                        p, c, prev_style = ac.getPrecedingPosCharStyle(prev_style, self.ignore_styles_ws)
                    if prev_style in (self.identifier_style, self.keyword_style):
                        return Trigger(lang, TRG_FORM_CALLTIP, "call-signature",
                                       pos, implicit)
            elif last_style == self.variable_style:
                if DEBUG:
                    print "Variable style"
                # Completion for variables (builtins and user defined variables),
                # must occur after a "$" character.
                if not implicit and last_char == '$':
                    # Explicit call, move ahead one for real trigger position
                    pos += 1
                if not implicit or prev_char == "$":
                    return Trigger(lang, TRG_FORM_CPLN, "variables",
                                   pos-1, implicit)
            elif last_style in (self.identifier_style, self.keyword_style):
                if DEBUG:
                    if last_style == self.identifier_style:
                        print "Identifier style"
                    else:
                        print "Identifier keyword style"
                # Completion for keywords,function and class names
                # Works after first 3 characters have been typed
                #if DEBUG:
                #    print "identifier_style: pos - 4 %s" % (accessor.style_at_pos(pos - 4))
                #third_char, third_style = last_four_char_and_styles[2]
                #fourth_char, fourth_style = last_four_char_and_styles[3]
                if prev_style == last_style:
                    trig_pos, ch, style = ac.getPrevPosCharStyle()
                    if style == last_style:
                        p, ch, style = ac.getPrevPosCharStyle(ignore_styles=self.ignore_styles)
                        # style is None if no change of style (not ignored) was
                        # found in the last x number of chars
                        #if not implicit and style == last_style:
                        #    if DEBUG:
                        #        print "Checking back further for explicit call"
                        #    p, c, style = ac.getPrecedingPosCharStyle(style, max_look_back=100)
                        #    if p is not None:
                        #        trg_pos = p + 3
                        if style in (None, self.whitespace_style,
                                     self.operator_style):
                            # Ensure we are not in another trigger zone, we do
                            # this by checking that the preceeding text is not
                            # one of "->", "::", "new", "function", "class", ...
                            if style == self.whitespace_style:
                                p, c, style = ac.getPrecedingPosCharStyle(self.whitespace_style, max_look_back=30)
                            if style is None:
                                return Trigger(lang, TRG_FORM_CPLN, "functions",
                                               trig_pos, implicit)
                            prev_text = ac.getTextBackWithStyle(style, max_text_len=15)
                            if DEBUG:
                                print "prev_text: %r" % (prev_text, )
                            if prev_text[1] not in ("->", "::", "new", "function",
                                                    "class", "interface", "implements",
                                                    "public", "private", "protected",
                                                    "final", "abstract", "instanceof",):
                                return Trigger(lang, TRG_FORM_CPLN, "functions",
                                               trig_pos, implicit)
                        # If we want implicit triggering on more than 3 chars
                        #elif style == self.identifier_style:
                        #    p, c, style = ac.getPrecedingPosCharStyle(self.identifier_style)
                        #    return Trigger(lang, TRG_FORM_CPLN, "functions",
                        #                   p+1, implicit)
                        elif DEBUG:
                            print "identifier preceeded by an invalid style: " \
                                  "%r, p: %r" % (style, p, )
            elif DEBUG:
                print "trg_from_pos: no handle for style: %d" % last_style
        except IndexError:
            # Not enough chars found, therefore no trigger
            pass

        return None

    #@util.hotshotit
    def preceding_trg_from_pos(self, buf, pos, curr_pos,
                               preceding_trg_terminators=None, DEBUG=False):
        #DEBUG = True
        # Try the default preceding_trg_from_pos handler
        trg = ProgLangTriggerIntelMixin.preceding_trg_from_pos(
                self, buf, pos, curr_pos, preceding_trg_terminators,
                DEBUG=DEBUG)
        if trg is not None:
            return trg

        # Else, let's try to work out some other options
        accessor = buf.accessor
        prev_style = accessor.style_at_pos(curr_pos - 1)
        if prev_style in (self.identifier_style, self.keyword_style):
            # We don't know what to trigger here... could be one of:
            # functions:
            #   apache<$><|>_getenv()...
            #   if(get_e<$><|>nv()...
            # classes:
            #   new Exce<$><|>ption()...
            #   extends Exce<$><|>ption()...
            # interfaces:
            #   implements apache<$><|>_getenv()...
            ac = AccessorCache(accessor, curr_pos)
            pos_before_identifer, ch, prev_style = \
                     ac.getPrecedingPosCharStyle(prev_style)
            if DEBUG:
                print "\nphp preceding_trg_from_pos, first chance for identifer style"
                print "  curr_pos: %d" % (curr_pos)
                print "  pos_before_identifer: %d" % (pos_before_identifer)
                print "  ch: %r" % ch
                print "  prev_style: %d" % prev_style
                ac.dump()
            if pos_before_identifer < pos:
                resetPos = min(pos_before_identifer + 4, accessor.length() - 1)
                ac.resetToPosition(resetPos)
                if DEBUG:
                    print "preceding_trg_from_pos:: reset to position: %d, ac now:" % (resetPos)
                    ac.dump()
                # Trigger on the third identifier character
                return self.trg_from_pos(buf, resetPos,
                                         implicit=False, DEBUG=DEBUG, ac=ac)
            elif DEBUG:
                print "Out of scope of the identifier"


    #@util.hotshotit
    def async_eval_at_trg(self, buf, trg, ctlr):
        if _xpcom_:
            trg = UnwrapObject(trg)
            ctlr = UnwrapObject(ctlr)
        pos = trg.pos
        ctlr.start(buf, trg)
        #print "trg.type: %r" % (trg.type)
        if trg.type in ("classes", "interfaces"):
            # Triggers from zero characters, thus calling citdl_expr_from_trg
            # is no help
            line = buf.accessor.line_from_pos(pos)
            evalr = PHPTreeEvaluator(ctlr, buf, trg, "", line)
            buf.mgr.request_eval(evalr)
        else:
            try:
                citdl_expr = self.citdl_expr_from_trg(buf, trg)
            except CodeIntelError, ex:
                ctlr.error(str(ex))
                ctlr.done("error")
                return
            line = buf.accessor.line_from_pos(pos)
            evalr = PHPTreeEvaluator(ctlr, buf, trg, citdl_expr, line)
            buf.mgr.request_eval(evalr)

    def _citdl_expr_from_pos(self, buf, pos, implicit=True,
                             include_forwards=False, DEBUG=False):
        #PERF: Would dicts be faster for all of these?
        WHITESPACE = tuple(" \t\n\r\v\f")
        EOL = tuple("\r\n")
        BLOCKCLOSES = tuple(")}]")
        STOPOPS = tuple("({[,&$+=^|%/<;:->!.@?")
        EXTRA_STOPOPS_PRECEDING_IDENT = BLOCKCLOSES # Might be others.

        #TODO: This style picking is a problem for the LangIntel move.
        if implicit:
            skip_styles = buf.implicit_completion_skip_styles
        else:
            skip_styles = buf.completion_skip_styles

        citdl_expr = []
        accessor = buf.accessor

        # Use a cache of characters, easy to keep track this way
        i = pos
        ac = AccessorCache(accessor, i)

        if include_forwards:
            try:
                # Move ahead to include forward chars as well
                lastch_was_whitespace = False
                while 1:
                    i, ch, style = ac.getNextPosCharStyle()
                    if DEBUG:
                        print "include_forwards:: i now: %d, ch: %r" % (i, ch)
                    if ch in WHITESPACE:
                        lastch_was_whitespace = True
                        continue
                    lastch_was_whitespace = False
                    if ch in STOPOPS:
                        if DEBUG:
                            print "include_forwards:: ch in STOPOPS, i:%d ch:%r" % (i, ch)
                        break
                    elif ch in BLOCKCLOSES:
                        if DEBUG:
                            print "include_forwards:: ch in BLOCKCLOSES, i:%d ch:%r" % (i, ch)
                        break
                    elif lastch_was_whitespace:
                        # Two whitespace separated words
                        if DEBUG:
                            print "include_forwards:: ch separated by whitespace, i:%d ch:%r" % (i, ch)
                        break
                # Move back to last valid char
                i -= 1
                if DEBUG:
                    if i > pos:
                        print "include_forwards:: Including chars from pos %d up to %d" % (pos, i)
                    else:
                        print "include_forwards:: No valid chars forward from pos %d, i now: %d" % (pos, i)
            except IndexError:
                # Nothing forwards, user what we have then
                i = min(i, accessor.length() - 1)
                if DEBUG:
                    print "include_forwards:: No more buffer, i now: %d" % (i)
            ac.resetToPosition(i)

        ch = None
        try:
            while i >= 0:
                if ch == None and include_forwards:
                    i, ch, style = ac.getCurrentPosCharStyle()
                else:
                    i, ch, style = ac.getPrevPosCharStyle()
                if DEBUG:
                    print "i now: %d, ch: %r" % (i, ch)

                if ch in WHITESPACE:
                    while ch in WHITESPACE:
                        # drop all whitespace
                        next_char = ch
                        i, ch, style = ac.getPrevPosCharStyle()
                        if ch in WHITESPACE \
                           or (ch == '\\' and next_char in EOL):
                            if DEBUG:
                                print "drop whitespace: %r" % ch
                    # If there are two whitespace-separated words then this is
                    # (likely or always?) a language keyword or declaration
                    # construct at which we want to stop. E.g.
                    #   if foo<|> and ...
                    #   def foo<|>(...
                    if citdl_expr and _isident(citdl_expr[-1]) \
                       and (_isident(ch) or _isdigit(ch)):
                        if DEBUG:
                            print "stop at (likely?) start of keyword or "\
                                  "declaration: %r" % ch
                        break
                    # Not whitespace anymore, move into the main checks below
                    if DEBUG:
                        print "Out of whitespace: i now: %d, ch: %s" % (i, ch)

                if style in skip_styles: # drop styles to ignore
                    while i >= 0 and style in skip_styles:
                        i, ch, style = ac.getPrevPosCharStyle()
                        if DEBUG:
                            print "drop char of style to ignore: %r" % ch
                elif ch in ":>" and i > 0:
                    # Next char has to be ":" or "-" respectively
                    prev_pos, prev_ch, prev_style = ac.getPrevPosCharStyle()
                    if (ch == ">" and prev_ch == "-") or \
                       (ch == ":" and prev_ch == ":"):
                        citdl_expr.append(".")
                        if DEBUG:
                            print "Turning member accessor '%s%s' into '.'" % (prev_ch, ch)
                        i -= 2
                    else:
                        if DEBUG:
                            print "citdl_expr: %r" % (citdl_expr)
                            print "stop at special stop-operator %d: %r" % (i, ch)
                        break
                elif (ch in STOPOPS or ch in EXTRA_STOPOPS_PRECEDING_IDENT) and \
                     (ch != ")" or (citdl_expr and citdl_expr[-1] != ".")):
                    if DEBUG:
                        print "citdl_expr: %r" % (citdl_expr)
                        print "stop at stop-operator %d: %r" % (i, ch)
                    break
                elif ch in BLOCKCLOSES:
                    if DEBUG:
                        print "found block at %d: %r" % (i, ch)
                    citdl_expr.append(ch)
        
                    BLOCKS = { # map block close char to block open char
                        ')': '(',
                        ']': '[',
                        '}': '{',
                    }
                    stack = [] # stack of blocks: (<block close char>, <style>)
                    stack.append( (ch, style, BLOCKS[ch], i) )
                    while i >= 0:
                        i, ch, style = ac.getPrevPosCharStyle()
                        if DEBUG:
                            print "finding matching brace: ch %r (%s), stack %r"\
                                  % (ch, ', '.join(buf.style_names_from_style_num(style)), stack)
                        if ch in BLOCKS and style not in skip_styles:
                            stack.append( (ch, style, BLOCKS[ch]) )
                        elif ch == stack[-1][2] and style not in skip_styles:
                            #XXX Replace the second test with the following
                            #    when LexPython+SilverCity styling bugs are fixed
                            #    (spurious 'stderr' problem):
                            #       and style == stack[-1][1]:
                            stack.pop()
                            if not stack:
                                if DEBUG:
                                    print "jump to matching brace at %d: %r" % (i, ch)
                                citdl_expr.append(ch)
                                break
                    else:
                        # Didn't find the matching brace.
                        if DEBUG:
                            print "couldn't find matching brace"
                        raise EvalError("could not find matching brace for "
                                        "'%s' at position %d"
                                        % (stack[-1][0], stack[-1][3]))
        
                else:
                    if DEBUG:
                        style_names = buf.style_names_from_style_num(style)
                        print "add char: %r (%s)" % (ch, ', '.join(style_names))
                    citdl_expr.append(ch)
                    i -= 1
        except IndexError:
            # Nothing left to consume, return what we have
            pass

        # Remove any unecessary starting dots
        while citdl_expr and citdl_expr[-1] == ".":
            citdl_expr.pop()
        citdl_expr.reverse()
        citdl_expr = ''.join(citdl_expr)
        if DEBUG:
            print "return: %r" % citdl_expr
            print util.banner("done")
        return citdl_expr

    def citdl_expr_from_trg(self, buf, trg):
        """Return a PHP CITDL expression preceding the given trigger.

        The expression drops newlines, whitespace, and function call
        arguments -- basically any stuff that is not used by the codeintel
        database system for determining the resultant object type of the
        expression. For example (in which <|> represents the given position):
        
            GIVEN                       RETURN
            -----                       ------
            foo-<|>>                    foo
            Foo:<|>:                    Foo
            foo(bar-<|>>                bar
            foo(bar,blam)-<|>>          foo()
            foo(bar,                    foo()
                blam)-<|>>
            foo(arg1, arg2)->bar-<|>>   foo().bar
            Foo(arg1, arg2)::bar-<|>>   Foo().bar
        """
        #DEBUG = True
        DEBUG = False
        if DEBUG:
            print util.banner("%s citdl_expr_from_trg @ %r" % (buf.lang, trg))

        if trg.form == TRG_FORM_CPLN:
            # "->" or "::"
            if trg.type in ("classes"):
                i = trg.pos
            elif trg.type in ("functions"):
                i = trg.pos + 2 # skip ahead of the trigger char
            elif trg.type in ("variables"):
                i = trg.pos
            else:
                i = trg.pos - 3 # skip past the trigger char
        elif trg.form == TRG_FORM_DEFN:
            return self.citdl_expr_under_pos(buf, trg.pos, DEBUG)
        else:   # trg.form == TRG_FORM_CALLTIP:
            # "->" or "::"
            i = trg.pos - 2 # skip past the trigger char
        return self._citdl_expr_from_pos(buf, i+1, trg.implicit, DEBUG=DEBUG)

    def citdl_expr_under_pos(self, buf, pos, DEBUG=False):
        """Return a PHP CITDL expression around the given pos.

        Similar to citdl_expr_from_trg(), but looks forward to grab additional
        characters.

            GIVEN                       RETURN
            -----                       ------
            foo-<|>>                    foo
            F<|>oo::                    Foo
            foo->ba<|>r                 foo.bar
            f<|>oo->bar                 foo
            foo(bar-<|>>                bar
            foo(bar,blam)-<|>>          foo()
            foo(bar,                    foo()
                blam)-<|>>
            foo(arg1, arg2)->bar-<|>>   foo().bar
            Foo(arg1, arg2)::ba<|>r->   Foo().bar
            Fo<|>o(arg1, arg2)::bar->   Foo
        """
        #DEBUG = True
        expr = self._citdl_expr_from_pos(buf, pos-1, implicit=True,
                                         include_forwards=True, DEBUG=DEBUG)
        if expr:
            # Chop off any trailing "." characters
            return expr.rstrip(".")
        return expr


    def libs_from_buf(self, buf):
        env = buf.env

        # A buffer's libs depend on its env and the buf itself so
        # we cache it on the env and key off the buffer.
        if "php-buf-libs" not in env.cache:
            env.cache["php-buf-libs"] = weakref.WeakKeyDictionary()
        cache = env.cache["php-buf-libs"] # <buf-weak-ref> -> <libs>

        if buf not in cache:
            # - curdirlib
            # Using the dirname of this buffer isn't always right, but
            # hopefully is a good first approximation.
            cwd = dirname(buf.path)
            if cwd == "<Unsaved>":
                libs = []
            else:
                libs = [ self.mgr.db.get_lang_lib("PHP", "curdirlib",
                                          [dirname(buf.path)], "PHP") ]

            libs += self._buf_indep_libs_from_env(env)
            cache[buf] = libs
        return cache[buf]

    def _php_from_env(self, env):
        import which
        path = [d.strip() 
                for d in env.get_envvar("PATH", "").split(os.pathsep)
                if d.strip()]
        for exe_name in ("php", "php4", "php-cgi", "php-cli"):
            try:
                return which.which(exe_name, path=path) 
            except which.WhichError:
                pass
        return None

    def _php_info_from_php(self, php, env):
        """Call the given PHP and return:
            (<version>, <include_path>)
        Returns (None, []) if could not determine.
        """
        import process

        # Use a marker to separate the start of output from possible
        # leading lines of PHP loading errors/logging.
        marker = "--- Start of Good Stuff ---"
        info_cmd = (r'<?php '
                    + r'echo("%s\n");' % marker
                    + r'echo(phpversion()."\n");'
                    + r'echo(ini_get("include_path")."\n");'
                    + r' ?>')
        argv = [php]
        envvars = env.get_all_envvars()
        php_ini_path = env.get_pref("phpConfigFile")
        if php_ini_path:
            envvars["PHPRC"] = php_ini_path

        log.debug("run `%s < ...'", php)
        p = process.ProcessOpen(argv, env=env.get_all_envvars())
        p.stdin.write(info_cmd)
        p.stdin.close()
        stdout_lines = p.stdout.read().splitlines(0)
        stderr = p.stderr.read()
        retval = p.wait()
        p.close()
        if retval:
            log.warn("failed to determine PHP info:\n"
                     "  path: %s\n"
                     "  retval: %s\n"
                     "  stdout:\n%s\n"
                     "  stderr:\n%s\n",
                     php, retval, util.indent('\n'.join(stdout_lines)),
                     util.indent(stderr))
            return None, []

        stdout_lines = stdout_lines[stdout_lines.index(marker)+1:]
        php_ver = stdout_lines[0]
        include_path = [p.strip() for p in stdout_lines[1].split(os.pathsep)
                        if p.strip()]

        return php_ver, include_path

    def _extra_dirs_from_env(self, env):
        extra_dirs = set()
        proj_base_dir = env.get_proj_base_dir()
        if proj_base_dir is not None:
            extra_dirs.add(proj_base_dir)  # Bug 68850.
        for pref in env.get_all_prefs("phpExtraPaths"):
            if not pref: continue
            extra_dirs.update(d.strip() for d in pref.split(os.pathsep)
                              if exists(d.strip()))
        if extra_dirs:
            log.debug("PHP extra lib dirs: %r", extra_dirs)
            max_depth = env.get_pref("codeintel_max_recursive_dir_depth", 10)
            php_assocs = env.assoc_patterns_from_lang("PHP")
            extra_dirs = tuple(
                util.gen_dirs_under_dirs(extra_dirs,
                    max_depth=max_depth,
                    interesting_file_patterns=php_assocs)
            )
        else:
            extra_dirs = () # ensure retval is a tuple
        return extra_dirs

    def _buf_indep_libs_from_env(self, env):
        """Create the buffer-independent list of libs."""
        cache_key = "php-libs"
        if cache_key not in env.cache:
            env.add_pref_observer("php", self._invalidate_cache)
            env.add_pref_observer("phpExtraPaths",
                self._invalidate_cache_and_rescan_extra_dirs)
            env.add_pref_observer("phpConfigFile",
                                  self._invalidate_cache)
            env.add_pref_observer("codeintel_selected_catalogs",
                                  self._invalidate_cache)
            env.add_pref_observer("codeintel_max_recursive_dir_depth",
                                  self._invalidate_cache)
            # (Bug 68850) Both of these 'live_*' prefs on the *project*
            # prefset can result in a change of project base dir. It is
            # possible that we can false positives here if there is ever
            # a global pref of this name.
            env.add_pref_observer("import_live",
                self._invalidate_cache_and_rescan_extra_dirs)
            env.add_pref_observer("import_dirname",
                self._invalidate_cache_and_rescan_extra_dirs)

            db = self.mgr.db

            # Gather information about the current php.
            php = None
            if env.has_pref("php"):
                php = env.get_pref("php").strip() or None
            if not php or not exists(php):
                php = self._php_from_env(env)
            if not php:
                log.warn("no PHP was found from which to determine the "
                         "import path")
                php_ver, include_path = None, []
            else:
                php_ver, include_path \
                    = self._php_info_from_php(php, env)
                
            libs = []

            # - extradirslib
            extra_dirs = self._extra_dirs_from_env(env)
            if extra_dirs:
                libs.append( db.get_lang_lib("PHP", "extradirslib",
                                             extra_dirs, "PHP") )

            # - inilib (i.e. dirs in the include_path in PHP.ini)
            include_dirs = [d for d in include_path
                            if d != '.'  # handled separately
                            if exists(d)]
            if include_dirs:
                max_depth = env.get_pref("codeintel_max_recursive_dir_depth", 10)
                php_assocs = env.assoc_patterns_from_lang("PHP")
                include_dirs = tuple(
                    util.gen_dirs_under_dirs(include_dirs,
                        max_depth=max_depth,
                        interesting_file_patterns=php_assocs)
                )
                if include_dirs:
                    libs.append( db.get_lang_lib("PHP", "inilib",
                                                 include_dirs, "PHP") )

            # Warn the user if there is a huge number of import dirs that
            # might slow down completion.
            num_import_dirs = len(extra_dirs) + len(include_dirs)
            if num_import_dirs > 100:
                db.report_event("This buffer is configured with %d PHP "
                                "import dirs: this may result in poor "
                                "completion performance" % num_import_dirs)

            # - cataloglib, stdlib
            catalog_selections = env.get_pref("codeintel_selected_catalogs")
            libs += [
                db.get_catalog_lib("PHP", catalog_selections),
                db.get_stdlib("PHP", php_ver)
            ]
            env.cache[cache_key] = libs

        return env.cache[cache_key]

    def _invalidate_cache(self, env, pref_name):
        for key in ("php-buf-libs", "php-libs"):
            if key in env.cache:
                log.debug("invalidate '%s' cache on %r", key, env)
                del env.cache[key]

    def _invalidate_cache_and_rescan_extra_dirs(self, env, pref_name):
        self._invalidate_cache(env, pref_name)
        extra_dirs = self._extra_dirs_from_env(env)
        if extra_dirs:
            extradirslib = self.mgr.db.get_lang_lib(
                "PHP", "extradirslib", extra_dirs)
            request = PreloadLibRequest(extradirslib)
            self.mgr.idxr.stage_request(request, 1.0)

    #---- code browser integration
    cb_import_group_title = "Includes and Requires"   

    def cb_import_data_from_elem(self, elem):
        #XXX Not handling symbol and alias
        module = elem.get("module")
        detail = 'include "%s"' % module
        return {"name": module, "detail": detail}


class PHPBuffer(UDLBuffer, XMLParsingBufferMixin):
    lang = lang
    m_lang = "HTML"
    css_lang = "CSS"
    csl_lang = "JavaScript"
    ssl_lang = "PHP"

    cb_show_if_empty = True

    #cpln_fillup_chars = "" #XXX none for now, should probably add some.
    # Fillup chars for PHP: basically, any non-identifier char.
    #cpln_fillup_chars = "("
    cpln_fillup_chars = ""
    #TODO: c.f. cpln_stop_chars stuff in lang_html.py
    # - dropping '[' because need for "<!<|>" -> "<![CDATA[" cpln
    cpln_stop_chars = "~`!@#$%^&*()-=+{}]|\\;:'\",.<>?/ "

    def __init__(self, *args, **kwargs):
        super(PHPBuffer, self).__init__(*args, **kwargs)
        
        # Encourage the database to pre-scan dirs relevant to completion
        # for this buffer -- because of recursive-dir-include-everything
        # semantics for PHP this first-time scan can take a while.
        request = PreloadBufLibsRequest(self)
        self.mgr.idxr.stage_request(request, 1.0)

    @property
    def libs(self):
        return self.langintel.libs_from_buf(self)

    @property
    def stdlib(self):
        return self.libs[-1]


class PHPImportHandler(ImportHandler):
    sep = '/'

    def setCorePath(self, compiler=None, extra=None):
        #XXX To do this independent of Komodo this would need to do all
        #    the garbage that koIPHPInfoEx is doing to determine this. It
        #    might also require adding a "rcfile" argument to this method
        #    so the proper php.ini file is used in the "_shellOutForPath".
        #    This is not crucial now because koCodeIntel._Manager() handles
        #    this for us.
        if not self.corePath:
            raise CodeIntelError("Do not know how to determine the core "
                                 "PHP include path. 'corePath' must be set "
                                 "manually.")

    def _findScannableFiles(self, (files, searchedDirs), dirname, names):
        if sys.platform.startswith("win"):
            cpath = dirname.lower()
        else:
            cpath = dirname
        if cpath in searchedDirs:
            while names:
                del names[0]
            return
        else:
            searchedDirs[cpath] = 1
        for i in range(len(names)-1, -1, -1): # backward so can del from list
            path = os.path.join(dirname, names[i])
            if os.path.isdir(path):
                pass
            elif os.path.splitext(names[i])[1] in (".php", ".inc",
                                                   ".module", ".tpl"):
                #XXX The list of extensions should be settable on
                #    the ImportHandler and Komodo should set whatever is
                #    set in prefs. ".module" and ".tpl" are for
                #    drupal-nerds until CodeIntel gets this right.
                #XXX This check for files should probably include
                #    scripts, which might likely not have the
                #    extension: need to grow filetype-from-content smarts.
                files.append(path)

    def genScannableFiles(self, path=None, skipRareImports=False,
                          importableOnly=False):
        if path is None:
            path = self._getPath()
        searchedDirs = {}
        for dirname in path:
            if dirname == os.curdir:
                # Do NOT traverse '.' if it is in the include_path. Not sure
                # if this is at all common for PHP.
                continue
            files = []
            os.path.walk(dirname, self._findScannableFiles,
                         (files, searchedDirs))
            for file in files:
                yield file

    def find_importables_in_dir(self, dir):
        """See citadel.py::ImportHandler.find_importables_in_dir() for
        details.

        Importables for PHP look like this:
            {"foo.php": ("foo.php", None, False),
             "bar.inc": ("bar.inc", None, False),
             "somedir": (None,      None, True)}

        TODO: log the fs-stat'ing a la codeintel.db logging.
        """
        from os.path import join, isdir
        from fnmatch import fnmatch

        if dir == "<Unsaved>":
            #TODO: stop these getting in here.
            return {}

        try:
            names = os.listdir(dir)
        except OSError, ex:
            return {}
        dirs, nondirs = set(), set()
        for name in names:
            if isdir(join(dir, name)):
                dirs.add(name)
            else:
                nondirs.add(name)

        importables = {}
        patterns = self.mgr.env.assoc_patterns_from_lang("PHP")
        for name in nondirs:
            for pattern in patterns:
                if fnmatch(name, pattern):
                    break
            else:
                continue
            if name in dirs:
                importables[name] = (name, None, True)
                dirs.remove(name)
            else:
                importables[name] = (name, None, False)
        for name in dirs:
            importables[name] = (None, None, True)
        return importables


class PHPCILEDriver(UDLCILEDriver):
    lang = lang
    ssl_lang = "PHP"
    csl_lang = "JavaScript"

    def XXXscan_purelang(self, buf):
      try:
        #XXX Remove md5sum and mtime when move to CIX 2.0.
        mtime = "XXX"
        phpciler = PHPParser(buf.path, buf.accessor.text, mtime)
        phpciler.scan_multilang_content(buf.accessor.text)
        # Get the CIX tree.
        tree = createCixRoot()
        phpciler.convertToElementTreeFile(tree)
        return tree
      except Exception, e:
          import traceback
          traceback.print_exc()
          raise

    def scan_multilang(self, buf, csl_cile_driver=None):
      #try:
        """Scan the given multilang (UDL-based) buffer and return a CIX
        element tree.

            "buf" is the multi-lang Buffer instance (e.g.
                lang_rhtml.RHTMLBuffer for RHTML).
            "csl_cile_driver" (optional) is the CSL (client-side language)
                CILE driver. While scanning, CSL tokens should be gathered and,
                if any, passed to the CSL scanner like this:
                    csl_cile_driver.scan_csl_tokens(
                        file_elem, blob_name, csl_tokens)
                The CSL scanner will append a CIX <scope ilk="blob"> element
                to the <file> element.
        """
        # Create the CIX tree.
        mtime = "XXX"
        fullpath = buf.path
        cixtree = createCixRoot()
        cixfile = createCixFile(cixtree, fullpath, lang=buf.lang)
        if sys.platform.startswith("win"):
            fullpath = fullpath.replace('\\', '/')
        basepath = os.path.basename(fullpath)
        cixblob = createCixModule(cixfile, basepath, "PHP", src=fullpath)

        phpciler = PHPParser(fullpath, buf.accessor.text, mtime)
        csl_tokens = phpciler.scan_multilang_content(buf.accessor.text)
        phpciler.convertToElementTreeModule(cixblob)

        # Hand off the csl tokens if any
        if csl_cile_driver and csl_tokens:
            csl_cile_driver.scan_csl_tokens(cixfile, basepath, csl_tokens)

        return cixtree

      #except Exception, e:
      #    import traceback
      #    traceback.print_exc()
      #    raise



#---- internal routines and classes


# States used by PHP scanner when parsing information
S_DEFAULT = 0
S_IN_ARGS = 1
S_IN_ASSIGNMENT = 2
S_IGNORE_SCOPE = 3
S_OBJECT_ARGUMENT = 4
S_GET_HEREDOC_MARKER = 5
S_IN_HEREDOC = 6
# Special tags for multilang handling (i.e. through UDL)
S_OPEN_TAG  = 10
S_CHECK_CLOSE_TAG = 11
S_IN_SCRIPT = 12

# Types used by JavaScriptScanner when parsing information
TYPE_NONE = 0
TYPE_FUNCTION = 1
TYPE_VARIABLE = 2
TYPE_GETTER = 3
TYPE_SETTER = 4
TYPE_MEMBER = 5
TYPE_OBJECT = 6
TYPE_CLASS = 7
TYPE_PARENT = 8


def _sortByLineCmp(val1, val2):
    try:
    #if hasattr(val1, "line") and hasattr(val2, "line"):
        return cmp(val1.linestart, val2.linestart)
    except AttributeError:
        return cmp(val1, val2)

def sortByLine(seq):
    seq.sort(_sortByLineCmp)
    return seq


class PHPArgs:
    def __init__(self, arglist, typelist=None, optionalArgs=None):
        """Set function arguments:
    @param arglist {list} of argument names
    @param typelist {list} of argument types
    @param optionalArgs {list} of lists [arg name, arg default value, arg type]
"""
        if arglist is None:
            arglist = []
        if optionalArgs is None:
            optionalArgs = []
        self.args = arglist
        self.typelist = typelist
        self.optionalArgs = optionalArgs
        arglineValues = arglist[:]
        for optArg, optArgValue, optArgType in optionalArgs:
            arglineValues.append("%s=%s" % (optArg, optArgValue))
        self.argline = ", ".join(arglineValues)

    def __repr__(self):
        args = []
        for arg in self.args:
            args.append(repr(arg))
        return string.join(args, ', ')

    def toElementTree(self, cixelement):
        for argIndex in range(len(self.args)):
            arg = self.args[argIndex]
            typename = None
            if self.typelist:
                typename = self.typelist[argIndex]
            addCixArgument(cixelement, arg, argtype=typename)
        for optArg, optArgValue, optArgType in self.optionalArgs:
            cixarg = addCixArgument(cixelement, optArg, argtype=optArgType)
            cixarg.attrib["default"] = optArgValue


class PHPVariable:
    def __init__(self, name, line, vartype='', attributes=''):
        self.name = name
        self.types = [(line, vartype)]
        self.linestart = line
        if attributes:
            if not isinstance(attributes, list):
                attributes = attributes.strip().split()
            self.attributes = ' '.join(attributes)
        else:
            self.attributes = None

    def addType(self, line, type):
        self.types.append((line, type))

    def __repr__(self):
        return "var %s line %s type %s attributes %s\n"\
               % (self.name, self.linestart, self.types, self.attributes)

    def toElementTree(self, cixblob):
        vartype = None
        # Work out the best vartype
        if self.types:
            d = {}
            max_count = 0
            for line, vtype in self.types:
                if vtype:
                    count = d.get(vtype, 0) + 1
                    d[vtype] = count
                    if count > max_count:
                        # Best found so far
                        vartype = vtype
                        max_count = count
        cixelement = createCixVariable(cixblob, self.name, vartype=vartype,
                                       attributes=self.attributes)
        cixelement.attrib["line"] = str(self.linestart)

class PHPFunction:
    def __init__(self, funcname, args, optionalArgs, lineno, depth=0,
                 attributes=None, doc=None, classname='', classparent='',
                 returnType=None):
        self.name = funcname
        self.linestart = lineno
        self.lineend = None
        self.depth = depth
        self.classname = classname
        self.classparent = classparent
        self.returnType = returnType
        self.variables = {} # all variables used in class
        # build the signature before we add any attributes that are not part
        # of the signature
        self.signature = '%s' % (self.name)
        if attributes:
            attrs = ' '.join(attributes)
            self.shortSig = '%s %s' % (attrs, self.name)
        else:
            self.shortSig = self.name
        # both php 4 and 5 constructor methods
        if funcname == '__construct' or (classname and funcname.lower() == classname.lower()):
            attributes.append('__ctor__')
# if we add destructor attributes...
#        elif funcname == '__destruct':
#            attributes += ['__dtor__']
        self.attributes = ' '.join(attributes)
        self.doc = None

        # Setup the function arguments
        if args:
            argTypes = [None] * len(args)
        else:
            argTypes = []
        if doc:
            if isinstance(doc, list):
                doc = "".join(doc)
            docinfo = parseDocString(doc)
            self.doc = docinfo[0]
            if docinfo[1]:
                for argInfo in docinfo[1]:
                    try:
                        argIndex = args.index(argInfo[1])
                        argTypes[argIndex] = argInfo[0]
                    except ValueError:
                        # No such element, see if it's an optional argument
                        for optArgInfo in optionalArgs:
                            if optArgInfo[0] == argInfo[1]:
                                optArgInfo[2] = argInfo[0]
                                break
                        else:
                            args.append(argInfo[1])
                            argTypes.append(argInfo[0])
            if docinfo[2]:
                self.returnType = docinfo[2][0]
        self.signature += "("
        if args or optionalArgs:
            self.args = PHPArgs(args, argTypes, optionalArgs)
            self.signature += self.args.argline
        else:
            self.args = None
        self.signature += ")"

    def addReturnType(self, returnType):
        if self.returnType is None:
            self.returnType = returnType

    def __str__(self):
        return self.signature
        # The following is busted and outputting multiple lines from __str__
        # and __repr__ is bad form: make debugging prints hard.
        #if self.doc:
        #    if self.args:
        #        return "%s(%s)\n%s" % (self.shortSig, self.args.argline, self.doc)
        #    else:
        #        return "%s()\n%s" % (self.shortSig, self.doc)
        #return "%s(%s)" % (self.shortSig, self.argline)

    def __repr__(self):
        return self.signature

    def toElementTree(self, cixblob):
        cixelement = createCixFunction(cixblob, self.name,
                                       attributes=self.attributes)
        cixelement.attrib["line"] = str(self.linestart)
        if self.lineend is not None:
            cixelement.attrib['lineend'] = str(self.lineend)
        setCixSignature(cixelement, self.signature)
        if self.doc:
            setCixDoc(cixelement, self.doc)
        if self.args:
            self.args.toElementTree(cixelement)
        if self.returnType:
            addCixReturns(cixelement, self.returnType)
        # Add a "this" and "self" member for class functions
        #if self.classname:
        #    createCixVariable(cixelement, "this", vartype=self.classname)
        #    createCixVariable(cixelement, "self", vartype=self.classname)
        # Add a "parent" member for class functions that have a parent
        #if self.classparent:
        #    createCixVariable(cixelement, "parent", vartype=self.classparent)

        # XXX for variables inside functions
        for v in self.variables.values():
            v.toElementTree(cixelement)

class PHPInterface:
    def __init__(self, name, extends, lineno, depth, doc=None):
        self.name = name
        self.extends = extends
        self.linestart = lineno
        self.lineend = None
        self.depth = depth
        self.members = {} # declared class variables
        self.variables = {} # all variables used in class
        self.functions = {}
        self.doc = None
        if doc:
            self.doc = uncommentDocString(doc)

    def __repr__(self):
        # dump our contents to human readable form
        r = "INTERFACE %s" % self.name
        if self.extends:
            r += " EXTENDS %s" % self.extends
        r += '\n'

        if self.members:
            r += "Members:\n"
            for m in self.members:
                r += "    var %s line %s\n"  % (m, self.members[m])

        if self.functions:            
            r += "functions:\n"
            for f in self.functions.values():
                r += "    %r" % f

        if self.variables:
            r += "variables:\n"
            for v in self.variables.values():
                r += "    %r" % v
            
        return r + '\n'

    def toElementTree(self, cixblob):
        cixelement = createCixInterface(cixblob, self.name)
        cixelement.attrib["line"] = str(self.linestart)
        if self.lineend is not None:
            cixelement.attrib["lineend"] = str(self.lineend)
        signature = "%s" % (self.name)
        if self.extends:
            signature += " extends %s" % (self.extends)
            for name in self.extends.split(","):
                addInterfaceRef(cixelement, name.strip())
            #SubElement(cixelement, "classref", name=self.extends)
        cixelement.attrib["signature"] = signature

        if self.doc:
            setCixDoc(self.doc)

        allValues = self.functions.values() + self.members.values() + \
                    self.variables.values()
        for v in sortByLine(allValues):
            v.toElementTree(cixelement)

class PHPClass:
    def __init__(self, name, extends, lineno, depth, attributes=None,
                 interfaces=None, doc=None):
        self.name = name
        self.extends = extends
        self.linestart = lineno
        self.lineend = None
        self.depth = depth
        self.members = {} # declared class variables
        self.variables = {} # all variables used in class
        self.functions = {}
        if interfaces:
            self.interfaces = interfaces.split(',')
        else:
            self.interfaces = []
        if attributes:
            self.attributes = ' '.join(attributes)
        else:
            self.attributes = None
        self.doc = None
        if doc:
            if isinstance(doc, list):
                doc = "".join(doc)
            self.doc = uncommentDocString(doc)

    def __repr__(self):
        # dump our contents to human readable form
        r = "CLASS %s" % self.name
        if self.extends:
            r += " EXTENDS %s" % self.extends
        r += '\n'

        if self.members:
            r += "Members:\n"
            for m in self.members:
                r += "    var %s line %s\n"  % (m, self.members[m])

        if self.functions:            
            r += "functions:\n"
            for f in self.functions.values():
                r += "    %r" % f

        if self.variables:
            r += "variables:\n"
            for v in self.variables.values():
                r += "    %r" % v
            
        return r + '\n'

    def toElementTree(self, cixblob):
        cixelement = createCixClass(cixblob, self.name)
        cixelement.attrib["line"] = str(self.linestart)
        if self.lineend is not None:
            cixelement.attrib["lineend"] = str(self.lineend)
        if self.attributes:
            cixelement.attrib["attributes"] = self.attributes

        if self.doc:
            setCixDoc(cixelement, self.doc)

        if self.extends:
            addClassRef(cixelement, self.extends)

        for i in self.interfaces:
            addInterfaceRef(cixelement, i.strip())

        allValues = self.functions.values() + self.members.values() + \
                    self.variables.values()
        for v in sortByLine(allValues):
            v.toElementTree(cixelement)

class PHPFile:
    """CIX specifies that a <file> tag have zero or more
    <scope ilk="blob"> children.  In PHP this is a one-to-one
    relationship, so this class represents both (and emits the XML tags
    for both).
    """
    def __init__(self, filename, content=None, mtime=None):
        self.filename = filename
        self.content = content
        self.mtime = mtime
        self.error = None
        
        self.content = content
        if mtime is None:
            self.mtime = int(time.time())

        self.functions = {} # functions declared in file
        self.classes = {} # classes declared in file
        self.variables = {} # all variables used in file
        self.includes = {} # files included into this file
        self.interfaces = {} # interfaces declared in file

    def __repr__(self):
        # dump our contents to human readable form
        r = "FILE %s\n" % self.filename

        for f, l in self.includes.items():
            r += "include %s on line %d\n" % (f, l)

        r += "functions:\n"
        for f in self.functions.values():
            r += "    %r" % f

        r += "variables:\n"
        for v in self.variables.values():
            r += "    %r" % v

        r += "classes:\n"
        for c in self.classes.values():
            r += repr(c)

        return r + '\n'

    def convertToElementTreeModule(self, cixmodule):
        for fn in self.includes:
            SubElement(cixmodule, "import", module=fn, line=str(self.includes[fn]))

        allValues = self.functions.values() + self.interfaces.values() + \
                    self.variables.values() + self.classes.values()
        for v in sortByLine(allValues):
            v.toElementTree(cixmodule)

    def convertToElementTreeFile(self, cix):
        if sys.platform.startswith("win"):
            path = self.filename.replace('\\', '/')
        else:
            path = self.filename
        cixfile = createCixFile(cix, path, lang="PHP", mtime=str(self.mtime))
        if self.error:
            cixfile.attrib["error"] = self.error
        cixmodule = createCixModule(cixfile, os.path.basename(self.filename),
                                    "PHP")
        self.convertToElementTreeModule(cixmodule)

class PHPcile:
    def __init__(self):
        # filesparsed contains all files parsed
        self.filesparsed={}
        # needfile contains a list of files included by the file that is the key
        self.needfile={}
        # infile contains a list of files that the key file is included in 
        self.infile={}
        # classindex tells us what file a class definition is contained in
        self.classindex={}
        # functionindex tells us what file a function is defined in
        self.functionindex={}
        # interfaceindex tells us what file an interface definition is contained in
        self.interfaceindex={}

    def _clearindex(self, filename, index):
        tmp = [k for k in index if index[k] == filename]
        for k in tmp:
            del index[k]
        
    def clear(self, filename):
        # clear include links from the cache
        if filename not in self.filesparsed:
            return
        del self.filesparsed[filename]
        
        if filename in self.needfile:
            for f in self.needfile[filename]:
                i = self.infile[f].index(filename)
                del self.infile[f][i]
            del self.needfile[filename]
        
        self._clearindex(filename, self.classindex)
        self._clearindex(filename, self.functionindex)
        self._clearindex(filename, self.interfaceindex)
        
    def __repr__(self):
        r = ''
        for f in self.filesparsed:
            r += repr(self.filesparsed[f])
        return r + '\n'

    #def toElementTree(self, cix):
    #    for f in self.filesparsed.values():
    #        f.toElementTree(cix)

    def convertToElementTreeModule(self, cixmodule):
        for f in self.filesparsed.values():
            f.convertToElementTreeModule(cixmodule)

    def convertToElementTreeFile(self, cix):
        for f in self.filesparsed.values():
            f.convertToElementTreeFile(cix)


class PHPParser:

    PHP_COMMENT_STYLES = (SCE_UDL_SSL_COMMENT, SCE_UDL_SSL_COMMENTBLOCK)

    def __init__(self, filename, content=None, mtime=None):
        self.filename = filename
        self.cile = PHPcile()
        self.fileinfo = PHPFile(self.filename, content, mtime)

        # Working variables, used in conjunction with state
        self.classStack = []
        self.currentClass = None
        self.currentInterface = None
        self.currentFunction = None
        self.csl_tokens = []
        self.lineno = 0
        self.depth = 0
        self.styles = []
        self.linenos = []
        self.text = []
        self.comment = []
        self.heredocMarker = None

        # state : used to store the current JS lexing state
        # return_to_state : used to store JS state to return to
        # multilang_state : used to store the current UDL lexing state
        self.state = S_DEFAULT
        self.return_to_state = S_DEFAULT
        self.multilang_state = S_DEFAULT

        self.PHP_WORD        = SCE_UDL_SSL_WORD
        self.PHP_IDENTIFIER  = SCE_UDL_SSL_IDENTIFIER
        self.PHP_VARIABLE    = SCE_UDL_SSL_VARIABLE
        self.PHP_OPERATOR    = SCE_UDL_SSL_OPERATOR
        self.PHP_STRINGS     = (SCE_UDL_SSL_STRING,)
        self.PHP_NUMBER      = SCE_UDL_SSL_NUMBER

        # XXX bug 44775
        # having the next line after scanData below causes a crash on osx
        # in python's UCS2 to UTF8.  leaving this here for later
        # investigation, see bug 45362 for details.
        self.cile.filesparsed[self.filename] = self.fileinfo

    def idfunc(self, m):
        log.debug("ID: %r",m.group(0))
        return m.group(0)

    # parses included files
    def include_file(self, filename):
        # XXX Very simple prevention of include looping.  Really should
        # recurse the indices to make sure we are not creating a loop
        if self.filename == filename:
            return ""

        # add the included file to our list of included files
        if filename not in self.fileinfo.includes:
            self.fileinfo.includes[filename] = self.lineno

        # add the included file to our list of included files
        if self.filename not in self.cile.needfile:
            self.cile.needfile[self.filename] = []
        try:
            self.cile.needfile[self.filename].index(filename)
        except ValueError, e:
            self.cile.needfile[self.filename].append(filename)

        # add this file to the infile list
        if filename not in self.cile.infile:
            self.cile.infile[filename] = []
        try:
            self.cile.infile[filename].index(self.filename)
        except ValueError, e:
            self.cile.infile[filename].append(self.filename)

    def incBlock(self):
        self.depth = self.depth+1
        # log.debug("depth at %d", self.depth)

    def decBlock(self):
        self.depth = self.depth-1
        # log.debug("depth at %d", self.depth)
        if self.currentClass and self.currentClass.depth == self.depth:
            # log.debug("done with class %s at depth %d", self.currentClass.name, self.depth)
            self.currentClass.lineend = self.lineno
            self.currentClass = self.classStack.pop()
        if self.currentInterface and self.currentInterface.depth == self.depth:
            # log.debug("done with interface %s at depth %d", self.currentClass.name, self.depth)
            self.currentInterface.lineend = self.lineno
            self.currentInterface = None
        elif self.currentFunction and self.currentFunction.depth == self.depth:
            self.currentFunction.lineend = self.lineno
            # XXX stacked functions used to work in php, need verify still is
            self.currentFunction = None

    def addFunction(self, name, args=None, optionalArgs=None, attributes=None,
                    doc=None):
        log.debug("FUNC: %s(%r %r) on line %d", name, args, optionalArgs, self.lineno)
        classname = ''
        extendsName = ''
        if self.currentClass:
            classname = self.currentClass.name
            extendsName = self.currentClass.extends
        elif self.currentInterface:
            classname = self.currentInterface.name
            extendsName = self.currentInterface.extends
        self.currentFunction = PHPFunction(name,
                                           args,
                                           optionalArgs,
                                           self.lineno,
                                           self.depth,
                                           attributes=attributes,
                                           doc=doc,
                                           classname=classname,
                                           classparent=extendsName)
        if self.currentClass:
            self.currentClass.functions[self.currentFunction.name] = self.currentFunction
        elif self.currentInterface:
            self.currentInterface.functions[self.currentFunction.name] = self.currentFunction
        else:
            self.fileinfo.functions[self.currentFunction.name] = self.currentFunction
            self.cile.functionindex[self.currentFunction.name] = self.fileinfo.filename
        if self.currentInterface or self.currentFunction.attributes.find('abstract') >= 0:
            self.currentFunction.lineend = self.lineno
            self.currentFunction = None

    def addReturnType(self, typeName):
        if self.currentFunction:
            log.debug("RETURN TYPE: %r on line %d", typeName, self.lineno)
            self.currentFunction.addReturnType(typeName)
        else:
            log.debug("addReturnType: No current function for return value!?")

    def addClass(self, name, extends=None, attributes=None, interfaces=None, doc=None):
        if name not in self.fileinfo.classes:
            # push the current class onto the class stack
            self.classStack.append(self.currentClass)
            # make this class the current class
            self.currentClass = PHPClass(name,
                                         extends,
                                         self.lineno,
                                         self.depth,
                                         attributes,
                                         interfaces,
                                         doc=doc)
            self.fileinfo.classes[self.currentClass.name] = self.currentClass
            # log.debug("adding classindex[%s]=%s", m.group('name'), self.fileinfo.filename)
            self.cile.classindex[self.currentClass.name]=self.fileinfo.filename
            log.debug("CLASS: %s extends %s interfaces %s attributes %s on line %d in %s at depth %d\nDOCS: %s",
                     self.currentClass.name, self.currentClass.extends, 
                     self.currentClass.interfaces, self.currentClass.attributes,
                     self.currentClass.linestart, self.filename, self.depth,
                     self.currentClass.doc)
        else:
            # shouldn't ever get here
            pass
    
    def addClassMember(self, name, vartype, attributes=None, doc=None, forceToClass=False):
        if self.currentFunction and not forceToClass:
            if name not in self.currentFunction.variables:
                phpVariable = self.currentClass.members.get(name)
                if phpVariable is None:
                    log.debug("Class FUNC variable: %r", name)
                    self.currentFunction.variables[name] = PHPVariable(name,
                                                                       self.lineno,
                                                                       vartype)
                elif vartype:
                    log.debug("Adding type information for VAR: %r, vartype: %r",
                              name, vartype)
                    phpVariable.addType(self.lineno, vartype)
        elif self.currentClass:
            phpVariable = self.currentClass.members.get(name)
            if phpVariable is None:
                log.debug("CLASSMBR: %r", name)
                self.currentClass.members[name] = PHPVariable(name, self.lineno,
                                                              vartype,
                                                              attributes)
            elif vartype:
                log.debug("Adding type information for CLASSMBR: %r, vartype: %r",
                          name, vartype)
                phpVariable.addType(self.lineno, vartype)

    def addInterface(self, name, extends=None, doc=None):
        if name not in self.fileinfo.classes:
            # push the current class onto the class stack
            self.classStack.append(self.currentClass)
            # make this class the current class
            self.currentInterface = PHPInterface(name,extends, self.lineno, self.depth)
            self.fileinfo.interfaces[name] = self.currentInterface
            # log.debug("adding classindex[%s]=%s", name, self.fileinfo.filename)
            self.cile.interfaceindex[name] = self.fileinfo.filename
            log.debug("INTERFACE: %s extends %s on line %d in %s at depth %d",
                     name, extends, self.lineno, self.filename, self.depth)
        else:
            # shouldn't ever get here
            pass

    def addVariable(self, name, vartype='', attributes=None, doc=None):
        log.debug("VAR: %r type: %r on line %d", name, vartype, self.lineno)
        if self.currentFunction:
            phpVariable = self.currentFunction.variables.get(name)
            if phpVariable is None:
                self.currentFunction.variables[name] = PHPVariable(name, self.lineno, vartype, attributes)
            elif vartype:
                log.debug("Adding type information for VAR: %r, vartype: %r",
                          name, vartype)
                phpVariable.addType(self.lineno, vartype)
        elif self.currentClass:
            pass
            # XXX this variable is local to a class method, what to do with it?
            #if m.group('name') not in self.currentClass.variables:
            #    self.currentClass.variables[m.group('name')] =\
            #        PHPVariable(m.group('name'), self.lineno)
        else:
            phpVariable = self.fileinfo.variables.get(name)
            if phpVariable is None:
                self.fileinfo.variables[name] = PHPVariable(name, self.lineno, vartype, attributes)
            elif vartype:
                log.debug("Adding type information for VAR: %r, vartype: %r",
                          name, vartype)
                phpVariable.addType(self.lineno, vartype)

    def _getArgumentsFromPos(self, styles, text, pos):
        """Return a tuple (arguments, optional arguments, next position)
        
        arguments: list of argument names
        optional arguments: list of lists [arg name, arg default value, arg type]
        """

        # Arguments can be of the form:
        #  foo($a, $b, $c)
        #  foo(&$a, &$b, &$c)
        #  foo($a, &$b, $c)
        #  foo($a = "123")
        #  makecoffee($types = array("cappuccino"), $coffeeMaker = NULL)

        log.debug("_getArgumentsFromPos: text: %r", text[pos:])
        if pos < len(styles) and styles[pos] == self.PHP_OPERATOR and text[pos] == "(":
            ids = []
            optionals = []
            pos += 1
            start_pos = pos
            while pos < len(styles):
                if styles[pos] == self.PHP_VARIABLE:
                    varname = self._removeDollarSymbolFromVariableName(text[pos])
                    if pos + 3 < len(styles) and text[pos+1] == "=":
                        # It's an optional argument
                        valueType, p = self._getVariableType(styles, text, pos+1)
                        if valueType:
                            valueType = valueType[0]
                        if valueType == "array" and text[pos+3] == "(":
                            # special handling for array initializers
                            value_pos = pos+2
                            pos = self._skipPastParenArguments(styles, text, pos+4)
                            if pos < len(styles):
                                optionals.append([varname, "".join(text[value_pos:pos]), valueType])
                        else:
                            optionals.append([varname, text[pos+2], valueType])
                            pos += 2
                    else:
                        ids.append(varname)
                elif styles[pos] != self.PHP_OPERATOR or text[pos] not in "&,":
                    break
                pos += 1
            return ids, optionals, pos
        return None, None, pos

    def _getIdentifiersFromPos(self, styles, text, pos, identifierStyle=None):
        if identifierStyle is None:
            identifierStyle = self.PHP_IDENTIFIER
        log.debug("_getIdentifiersFromPos: text: %r", text[pos:])
        start_pos = pos
        ids = []
        last_style = self.PHP_OPERATOR
        while pos < len(styles):
            style = styles[pos]
            #print "Style: %d, Text[%d]: %r" % (style, pos, text[pos])
            if style == identifierStyle:
                if last_style != self.PHP_OPERATOR:
                    break
                ids.append(text[pos])
            elif style == self.PHP_OPERATOR:
                t = text[pos]
                if ((t != "&" or last_style != self.PHP_OPERATOR) and \
                    (t != ":" or last_style != identifierStyle)):
                    break
            else:
                break
            pos += 1
            last_style = style
        return ids, pos

    def _skipPastParenArguments(self, styles, text, p):
        paren_count = 1
        while p < len(styles):
            if styles[p] == self.PHP_OPERATOR:
                if text[p] == "(":
                    paren_count += 1
                elif text[p] == ")":
                    if paren_count == 1:
                        return p+1
                    paren_count -= 1
            p += 1
        return p

    def _getVariableType(self, styles, text, p, assignmentChar="="):
        """Set assignmentChar to None to skip over looking for this char first"""

        log.debug("_getVariableType: text: %r", text[p:])
        typeNames = []
        if p+1 < len(styles) and (assignmentChar is None or \
                                  (styles[p] == self.PHP_OPERATOR and \
                                   text[p] == assignmentChar)):
            # Assignment to the variable
            if assignmentChar is not None:
                p += 1
            if styles[p] == self.PHP_WORD:
                # Keyword
                keyword = text[p]
                p += 1
                if keyword == "new":
                    typeNames, p = self._getIdentifiersFromPos(styles, text, p)
                    #if not typeNames:
                    #    typeNames = ["object"]
                elif keyword in ("true", "false"):
                    typeNames = ["boolean"];
                elif keyword == "array":
                    typeNames = ["array"];
            elif styles[p] in self.PHP_STRINGS:
                p += 1
                typeNames = ["string"]
            elif styles[p] == self.PHP_NUMBER:
                p += 1
                typeNames = ["int"]
            elif styles[p] == self.PHP_IDENTIFIER:
                typeNames, p = self._getIdentifiersFromPos(styles, text, p)
                # Don't record null, as it doesn't help us with anything
                if typeNames == ["NULL"]:
                    typeNames = []
                elif typeNames and p < len(styles) and \
                   styles[p] == self.PHP_OPERATOR and text[p][0] == "(":
                    typeNames[-1] += "()"
            elif styles[p] == self.PHP_VARIABLE:
                typeNames, p = self._getIdentifiersFromPos(styles, text, p, self.PHP_VARIABLE)
                if typeNames:
                    typeNames[0] = self._removeDollarSymbolFromVariableName(typeNames[0])
                log.debug("p: %d, text left: %r", p, text[p:])
                # Grab additional fields
                # Example: $x = $obj<p>->getFields()->field2
                while p+2 < len(styles) and styles[p] == self.PHP_OPERATOR and \
                      text[p] in (":->"):
                    p += 1
                    log.debug("while:: p: %d, text left: %r", p, text[p:])
                    if styles[p] == self.PHP_IDENTIFIER:
                        additionalNames, p = self._getIdentifiersFromPos(styles, text, p)
                        log.debug("p: %d, additionalNames: %r", p, additionalNames)
                        if additionalNames:
                            typeNames.append(additionalNames[0])
                            if p < len(styles) and \
                               styles[p] == self.PHP_OPERATOR and text[p][0] == "(":
                                typeNames[-1] += "()"
                                p = self._skipPastParenArguments(styles, text, p+1)
                                log.debug("_skipPastParenArguments:: p: %d, text left: %r", p, text[p:])
                    
        return typeNames, p

    def _getKeywordArguments(self, styles, text, p, keywordName):
        arguments = None
        while p < len(styles):
            if styles[p] == self.PHP_WORD and text[p] == keywordName:
                # Grab the definition
                p += 1
                arguments = []
                last_style = self.PHP_OPERATOR
                while p < len(styles):
                    if styles[p] == self.PHP_IDENTIFIER and \
                       last_style == self.PHP_OPERATOR:
                        arguments.append(text[p])
                    elif styles[p] != self.PHP_OPERATOR or text[p] != ",":
                        break
                    last_style = styles[p]
                    p += 1
                arguments = ", ".join(arguments)
                break
            p += 1
        return arguments

    def _getExtendsArgument(self, styles, text, p):
        return self._getKeywordArguments(styles, text, p, "extends")

    def _getImplementsArgument(self, styles, text, p):
        return self._getKeywordArguments(styles, text, p, "implements")

    def _unquoteString(self, s):
        """Return the string without quotes around it"""
        if len(s) >= 2 and s[0] in "\"'":
            return s[1:-1]
        return s

    def _removeDollarSymbolFromVariableName(self, name):
        if name[0] == "$":
            return name[1:]
        return name

    def _getIncludePath(self, styles, text, p):
        """Work out the include string and return it (without the quotes)"""
        # Some examples (include has identical syntax):
        #   require 'prepend.php';
        #   require $somefile;
        #   require ('somefile.txt');
        # From bug: http://bugs.activestate.com/show_bug.cgi?id=64208
        # We just find the first string and use that
        #   require_once(CEON_CORE_DIR . 'core/datatypes/class.CustomDT.php');
        # Skip over first brace if it exists
        if p < len(styles) and \
           styles[p] == self.PHP_OPERATOR and text[p] == "(":
            p += 1
        while p < len(styles):
            if styles[p] in self.PHP_STRINGS:
                requirename = self._unquoteString(text[p])
                if requirename:
                    # Return with the first string found, we could do better...
                    return requirename
            p += 1
        return None

    def _addAllVariables(self, styles, text, p):
        while p < len(styles):
            if styles[p] == self.PHP_VARIABLE:
                namelist, p = self._getIdentifiersFromPos(styles, text, p, self.PHP_VARIABLE)
                if len(namelist) == 1:
                    name = self._removeDollarSymbolFromVariableName(namelist[0])
                    # Don't add special internal variable names
                    if name in ("this", "self"):
                        # Lets see what we are doing with this
                        if p+3 < len(styles) and "".join(text[p:p+2]) in ("->", "::"):
                            # Get the variable the code is accessing
                            namelist, p = self._getIdentifiersFromPos(styles, text, p+2)
                            typeNames, p = self._getVariableType(styles, text, p)
                            if len(namelist) == 1 and typeNames:
                                log.debug("Assignment through %r for variable: %r", name, namelist)
                                self.addClassMember(namelist[0],
                                                    ".".join(typeNames),
                                                    doc=self.comment,
                                                    forceToClass=True)
                    elif name is not "parent":
                        # If next text/style is not an "=" operator, then add
                        # __not_defined__, which means the variable was not yet
                        # defined at the position it was ciled.
                        attributes = None
                        if p < len(styles) and text[p] != "=":
                            attributes = "__not_yet_defined__"
                        self.addVariable(name, attributes=attributes)
            p += 1

    def _variableHandler(self, styles, text, p, attributes, doc=None):
        log.debug("_variableHandler:: text: %r, attributes: %r", text[p:],
                  attributes)
        classVar = False
        if attributes:
            classVar = True
            if "var" in attributes:
                attributes.remove("var")  # Don't want this in cile output
        looped = False
        while p < len(styles):
            if looped:
                if text[p] != ",":  # Variables need to be comma delimited.
                    p += 1
                    continue
                p += 1
            else:
                looped = True
            namelist, p = self._getIdentifiersFromPos(styles, text, p,
                                                      self.PHP_VARIABLE)
            if not namelist:
                break
            log.debug("namelist:%r, p:%d", namelist, p)
            # Remove the dollar sign
            name = self._removeDollarSymbolFromVariableName(namelist[0])
            # Parse special internal variable names
            if name == "parent":
                continue
            if name in ("this", "self", ):
                classVar = True
                if p+3 < len(styles) and text[p:p+2] in (["-", ">"], [":", ":"]):
                    namelist, p = self._getIdentifiersFromPos(styles, text, p+2,
                                                              self.PHP_IDENTIFIER)
                    log.debug("namelist:%r, p:%d", namelist, p)
                    if not namelist:
                        continue
                    name = namelist[0]
                else:
                    continue
            if len(namelist) != 1:
                log.info("warn: invalid variable namelist (ignoring): "
                         "%r, line: %d in file: %r", namelist,
                         self.lineno, self.filename)
                continue

            assignChar = text[p]
            typeNames = []
            if p+1 < len(styles) and styles[p] == self.PHP_OPERATOR and \
                                         assignChar in "=":
                # Assignment to the variable
                typeNames, p = self._getVariableType(styles, text, p, assignChar)
                # Skip over paren arguments from class, function calls.
                if typeNames and p < len(styles) and \
                   styles[p] == self.PHP_OPERATOR and text[p] == "(":
                    p = self._skipPastParenArguments(styles, text, p+1)
            if p < len(styles) and styles[p] == self.PHP_OPERATOR and \
                                         text[p] in ",;":
                log.debug("Line %d, variable definition: %r",
                         self.lineno, namelist)
                if classVar and self.currentClass is not None:
                    self.addClassMember(name, ".".join(typeNames),
                                        attributes=attributes, doc=self.comment)
                else:
                    self.addVariable(name, ".".join(typeNames),
                                     attributes=attributes, doc=self.comment)

    def _addCodePiece(self, newstate=S_DEFAULT, varnames=None):
        styles = self.styles
        if len(styles) == 0:
            return
        text = self.text
        lines = self.linenos

        log.debug("*** Line: %d ********************************", self.lineno)
        #log.debug("Styles: %r", self.styles)
        log.debug("Text: %r", self.text)
        #log.debug("Comment: %r", self.comment)
        #log.debug("")

        pos = 0
        attributes = []
        firstStyle = styles[pos]

        try:
            # Eat special attribute keywords
            while firstStyle == self.PHP_WORD and \
                  text[pos] in ("var", "public", "protected", "private",
                                "final", "static", "const", "abstract"):
                attributes.append(text[pos])
                pos += 1
                firstStyle = styles[pos]
    
            if firstStyle == self.PHP_WORD:
                keyword = text[pos]
                pos += 1
                if pos >= len(lines):
                    # Nothing else here, go home
                    return
                self.lineno = lines[pos]
                if keyword in ("require", "include", "require_once", "include_once"):
                    # Some examples (include has identical syntax):
                    # require 'prepend.php';
                    # require $somefile;
                    # require ('somefile.txt');
                    # XXX - Below syntax is not handled...
                    # if ((include 'vars.php') == 'OK') {
                    namelist = None
                    if pos < len(styles):
                        requirename = self._getIncludePath(styles, text, pos)
                        if requirename:
                            self.include_file(requirename)
                        else:
                            log.debug("Could not work out requirename. Text: %r",
                                      text[pos:])
                elif keyword == "function":
                    namelist, p = self._getIdentifiersFromPos(styles, text, pos)
                    log.debug("namelist:%r, p:%d", namelist, p)
                    if namelist:
                        args, optionals, p = self._getArgumentsFromPos(styles, text, p)
                        log.debug("Line %d, function: %r(%r, optionals: %r)",
                                 self.lineno, namelist, args, optionals)
                        if len(namelist) != 1:
                            log.info("warn: invalid function name (ignoring): "
                                     "%r, line: %d in file: %r", namelist,
                                     self.lineno, self.filename)
                            return
                        self.addFunction(namelist[0], args, optionals, attributes, doc=self.comment)
                elif keyword == "class":
                    # Examples:
                    #   class SimpleClass {
                    #   class SimpleClass2 extends SimpleClass {
                    #   class MyClass extends AbstractClass implements TestInterface, TestMethodsInterface {
                    #
                    namelist, p = self._getIdentifiersFromPos(styles, text, pos)
                    if namelist and "{" in text:
                        if len(namelist) != 1:
                            log.info("warn: invalid class name (ignoring): %r, "
                                     "line: %d in file: %r", namelist,
                                     self.lineno, self.filename)
                            return
                        extends = self._getExtendsArgument(styles, text, p)
                        implements = self._getImplementsArgument(styles, text, p)
                        #print "extends: %r" % (extends)
                        #print "implements: %r" % (implements)
                        self.addClass(namelist[0], extends=extends,
                                      attributes=attributes,
                                      interfaces=implements, doc=self.comment)
                elif keyword == "interface":
                    # Examples:
                    #   interface Foo {
                    #   interface SQL_Result extends SeekableIterator, Countable {
                    #
                    namelist, p = self._getIdentifiersFromPos(styles, text, pos)
                    if namelist and "{" in text:
                        if len(namelist) != 1:
                            log.info("warn: invalid interface name (ignoring): "
                                     "%r, line: %d in file: %r", namelist,
                                     self.lineno, self.filename)
                            return
                        extends = self._getExtendsArgument(styles, text, p)
                        self.addInterface(namelist[0], extends, doc=self.comment)
                elif keyword == "return":
                    # Returning value for a function call
                    #   return 123;
                    #   return $x;
                    typeNames, p = self._getVariableType(styles, text, pos, assignmentChar=None)
                    log.debug("typeNames:%r", typeNames)
                    if typeNames:
                        self.addReturnType(".".join(typeNames))
                else:
                    log.debug("Ignoring keyword: %s", keyword)
                    self._addAllVariables(styles, text, pos)
    
            elif firstStyle == self.PHP_IDENTIFIER:
                log.debug("Ignoring when starting with identifier")
            elif firstStyle == self.PHP_VARIABLE:
                # Defining scope for action
                self._variableHandler(styles, text, pos, attributes,
                                      doc=self.comment)
            else:
                log.debug("Unhandled first style:%d", firstStyle)
        finally:
            self._resetState(newstate)

    def _resetState(self, newstate=S_DEFAULT):
        self.state = newstate
        self.styles = []
        self.linenos = []
        self.text = []
        self.comment = []

    def token_next(self, style, text, start_column, start_line, **other_args):
        """Loops over the styles in the document and stores important info.
        
        When enough info is gathered, will perform a call to analyze the code
        and generate subsequent language structures. These language structures
        will later be used to generate XML output for the document."""
        #log.debug("text: %r", text)

        if self.state == S_GET_HEREDOC_MARKER:
            self.heredocMarker = text
            log.debug("getting heredoc marker: %r, now in heredoc state", text)
            self._resetState(S_IN_HEREDOC)

        elif self.state == S_IN_HEREDOC:
            # Heredocs *must* be on the start of a newline
            if text == self.heredocMarker and self.lastText and \
               self.lastText[-1] in "\r\n":
                log.debug("end of heredoc: %r", self.heredocMarker)
                self._resetState(self.return_to_state)
            else:
                log.debug("ignoring heredoc material")

        elif (style in (self.PHP_WORD, self.PHP_IDENTIFIER,
                      self.PHP_OPERATOR, self.PHP_NUMBER, self.PHP_VARIABLE) or
            style in (self.PHP_STRINGS)):
            # We keep track of these styles and the text associated with it.
            # When we gather enough info, these will be sent to the
            # _addCodePiece() function which will analyze the info.
            self.lineno = start_line + 1

            if style != self.PHP_OPERATOR:
                # Have to trim whitespace, as the identifier style is
                # also the default whitespace style... ugly!
                if style == self.PHP_IDENTIFIER:
                    text = text.strip()
                if text:
                    self.text.append(text)
                    self.styles.append(style)
                    self.linenos.append(self.lineno)
                    #print "Text:", text
            else:
                # Do heredoc parsing, since UDL cannot as yet
                if text == "<<<":
                    self.return_to_state = self.state
                    self.state = S_GET_HEREDOC_MARKER
                # Remove out any "<?php" and "?>" tags, see syntax description:
                #   http://www.php.net/manual/en/language.basic-syntax.php
                elif text.startswith("<?"):
                    if text.startswith("<?php"):
                        text = text[len("<?php"):]
                    elif text.startswith("<?="):
                        text = text[len("<?="):]
                    else:
                        text = text[len("<?"):]
                elif text.startswith("<%"):
                    if text.startswith("<%="):
                        text = text[len("<%="):]
                    else:
                        text = text[len("<%"):]
                if text.endswith("?>"):
                    text = text[:-len("?>")]
                elif text.endswith("<%"):
                    text = text[:-len("%>")]

                col = start_column + 1
                #for op in text:
                #    self.styles.append(style)
                #    self.text.append(op)
                #log.debug("token_next: line %d, %r" % (self.lineno, text))
                for op in text:
                    self.styles.append(style)
                    self.text.append(op)
                    self.linenos.append(self.lineno)
                    if op == "(":
                        # We can start defining arguments now
                        #log.debug("Entering S_IN_ARGS state")
                        self.return_to_state = self.state
                        self.state = S_IN_ARGS
                    elif op == ")":
                        #log.debug("Entering state %d", self.return_to_state)
                        self.state = self.return_to_state
                    elif op == "=":
                        if text == op:
                            #log.debug("Entering S_IN_ASSIGNMENT state")
                            self.state = S_IN_ASSIGNMENT
                    elif op == "{":
                        # Increasing depth/scope, could be an argument object
                        self._addCodePiece()
                        self.incBlock()
                    elif op == "}":
                        # Decreasing depth/scope
                        self._addCodePiece()
                        self.decBlock()
                    elif op == ";":
                        # Statement is done
                        self._addCodePiece()
                    col += 1
        elif style in self.PHP_COMMENT_STYLES:
            self.comment.append(text)
        elif is_udl_csl_style(style):
            self.csl_tokens.append({"style": style,
                                    "text": text,
                                    "start_column": start_column,
                                    "start_line": start_line})
        self.lastText = text

    def scan_multilang_content(self, content):
        """Scan the given PHP content, only processes SSL styles"""
        PHPLexer().tokenize_by_style(content, self.token_next)
        return self.csl_tokens

    def convertToElementTreeFile(self, cixelement):
        """Store PHP information into the cixelement as a file(s) sub element"""
        self.cile.convertToElementTreeFile(cixelement)

    def convertToElementTreeModule(self, cixblob):
        """Store PHP information into already created cixblob"""
        self.cile.convertToElementTreeModule(cixblob)


#---- internal utility functions

def _isident(char):
    return "a" <= char <= "z" or "A" <= char <= "Z" or char == "_"

def _isdigit(char):
    return "0" <= char <= "9"


#---- public module interface


#---- registration

def register(mgr):
    """Register language support with the Manager."""
    mgr.set_lang_info(lang,
                      silvercity_lexer=PHPLexer(),
                      buf_class=PHPBuffer,
                      langintel_class=PHPLangIntel,
                      import_handler_class=PHPImportHandler,
                      cile_driver_class=PHPCILEDriver,
                      is_cpln_lang=True)
