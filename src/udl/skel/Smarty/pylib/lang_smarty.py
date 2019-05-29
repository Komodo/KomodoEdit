#!/usr/bin/env python
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

"""Smarty support for codeintel"""

import logging

import re
from codeintel2.common import *
from codeintel2.langintel import LangIntel
from codeintel2.udl import UDLLexer, UDLBuffer, UDLCILEDriver, XMLParsingBufferMixin

#---- globals

lang = "Smarty"
log = logging.getLogger("codeintel.smarty")



smarty_tags = [
    "assign",
    "capture",
    "config_load",
    "counter",
    "cycle",
    "debug",
    "else",
    "elseif",
    "eval",
    "fetch",
    "foreach",
    "foreachelse",
    "html_checkboxes",
    "html_image",
    "html_options",
    "html_radios",
    "html_select_date",
    "html_select_time",
    "html_table",
    "if",
    "include",
    "include_php",
    "insert",
    "ldelim",
    "literal",
    "mailto",
    "math",
    "php",
    "rdelim",
    "section",
    "sectionelse",
    "string",
    "textformat"
]

smarty_default_modifier_names = [
    "capitalize",
    "cat",
    "constant",
    "count_characters",
    "count_paragraphs",
    "count_sentences",
    "count_words",
    "date_format",
    "default",
    "escape",
    "htmlspecialchars",
    "indent",
    "json_encode",
    "lower",
    "nl2br",
    "number_format",
    "print_r",
    "regex_replace",
    "replace",
    "spacify",
    "string_format",
    "strip",
    "strip_tags",
    "truncate",
    "upper",
    "var_dump",
    "wordwrap"
]

smarty_var_keys = [
    "capture",
    "config",
    "const",
    "cookies",
    "env",
    "foreach",
    "get",
    "now",
    "post",
    "request",
    "section",
    "server",
    "session",
    "template"
]

#---- language support

class SmartyLexer(UDLLexer):
    lang = lang

class SmartyBuffer(UDLBuffer, XMLParsingBufferMixin):
    lang = lang
    tpl_lang = lang
    m_lang = "HTML"
    css_lang = "CSS"
    csl_lang = "JavaScript"
    ssl_lang = "PHP"

    # Characters that should close an autocomplete UI:
    # - wanted for XML completion: ">'\" "
    # - wanted for CSS completion: " ('\";},.>"
    # - wanted for JS completion:  "~`!@#%^&*()-=+{}[]|\\;:'\",.<>?/ "
    # - dropping ':' because I think that may be a problem for XML tag
    #   completion with namespaces (not sure of that though)
    # - dropping '[' because need for "<!<|>" -> "<![CDATA[" cpln
    # - dropping '-' because causes problem with CSS (bug 78312)
    # - dropping '!' because causes problem with CSS "!important" (bug 78312)
    #TODO: adjust for PHP, if necessary
    cpln_stop_chars = "'\" (;},~`@#%^&*()=+{}]|\\;,.<>?/"


class SmartyLangIntel(LangIntel):
    lang = lang

    # Used by ProgLangTriggerIntelMixin.preceding_trg_from_pos()
    trg_chars = tuple('|{/.$')
    calltip_trg_chars = tuple()

    def trg_from_pos(self, buf, pos, implicit=True, DEBUG=False):
        """
            CODE       CONTEXT      RESULT
            '{<|>'     anywhere     tag names, i.e. {if}
            '{/<|>'     anywhere    tag names, i.e. {/if}
            '$foo|<|>'  modifiers      modifier names, i.e. {$foo|modifier} or {$foo|@modifier}
        """
        if pos < 1:
            return None
        accessor = buf.accessor
        last_pos = pos - 1
        last_char = accessor.char_at_pos(last_pos)

        # Functions/tags
        if last_char == "{" or (last_char == "/" and last_pos > 0 and accessor.char_at_pos(last_pos - 1) == "{"):
            return Trigger(lang, TRG_FORM_CPLN, "complete-tags", pos, implicit)

        # Modifiers
        if last_char == "|" or (last_char == "@" and last_pos > 0 and accessor.char_at_pos(last_pos - 1) == "|"):
            return Trigger(lang, TRG_FORM_CPLN, "complete-modifiers", pos, implicit)

        # Variables
        if last_char == "$":
            return Trigger(lang, TRG_FORM_CPLN, "complete-vars", pos, implicit)

        # Complete $smarty tags
        if last_char == "." and pos > 7 and accessor.text_range(pos - 8, pos) == "$smarty.":
            return Trigger(lang, TRG_FORM_CPLN, "complete-smarty-var", pos, implicit)

    _smartytag_cplns =    [ ("element", t) for t in sorted(smarty_tags) ]
    _smartymodifier_cplns = [ ("function", t) for t in sorted(smarty_default_modifier_names) ]
    _smartyvarkeys_cplns = [ ("variable", t) for t in sorted(smarty_var_keys) ]

    def async_eval_at_trg(self, buf, trg, ctlr):
        if _xpcom_:
            trg = UnwrapObject(trg)
            ctlr = UnwrapObject(ctlr)

        ctlr.start(buf, trg)

        # Smarty tag completions
        if trg.id == (lang, TRG_FORM_CPLN, "complete-tags"):
            completions = self._smartytag_cplns[:]
            for t in self._get_smarty_vars(buf):
                completions.append(("variable", t))
            ctlr.set_cplns(completions)
            ctlr.done("success")
            return
        elif trg.id == (lang, TRG_FORM_CPLN, "complete-modifiers"):
            ctlr.set_cplns(self._smartymodifier_cplns)
            ctlr.done("success")
            return
        elif trg.id == (lang, TRG_FORM_CPLN, "complete-vars"):
            completions = [("variable", t) for t in self._get_smarty_vars(buf) ]
            ctlr.set_cplns(completions)
            ctlr.done("success")
            return
        elif trg.id == (lang, TRG_FORM_CPLN, "complete-smarty-var"):
            ctlr.set_cplns(self._smartyvarkeys_cplns)
            ctlr.done("success")
            return

        ctlr.done("success")

    # Variable in form {assign name="..."
    _re_assign_var = re.compile(r'\{assign\s+(?:[^}]+\s)?name=[\'"](?P<variable>\w+)[\'"]', re.M|re.U)
    # Variable in form {... assign="..."
    _re_assign_attr_var = re.compile(r'\{[^}]+\sassign=[\'"](?P<variable>\w+)[\'"]', re.M|re.U)
    # Any variable used
    _re_used_var = re.compile(r'{[^}]*(?P<variable>\$\w+)', re.M|re.U)
    def _get_smarty_vars(self, buf):
        """ Get Smarty variables from this file """
        smarty_vars = ["$smarty"]
        # Add any vars assigned in this file
        for regex in [self._re_assign_var, self._re_assign_attr_var]:
            for match in re.finditer(regex, buf.accessor.text):
                groups = match.groupdict()
                this_var = "$" + groups['variable']
                if this_var not in smarty_vars:
                    smarty_vars.append(this_var)
        # Add any vars used in this file
        for match in re.finditer(self._re_used_var, buf.accessor.text):
            groups = match.groupdict()
            this_var = groups['variable']
            if this_var not in smarty_vars:
                smarty_vars.append(this_var)
        return sorted(smarty_vars)


class SmartyCILEDriver(UDLCILEDriver):
    lang = lang
    csl_lang = "JavaScript"
    ssl_lang = "PHP"
    css_lang = "CSS"



#---- registration

def register(mgr):
    """Register language support with the Manager."""
    mgr.set_lang_info(lang,
                      silvercity_lexer=SmartyLexer(),
                      buf_class=SmartyBuffer,
                      langintel_class=SmartyLangIntel,
                      import_handler_class=None,
                      cile_driver_class=SmartyCILEDriver,
                      is_cpln_lang=True)

