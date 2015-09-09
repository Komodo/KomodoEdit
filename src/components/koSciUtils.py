#!python
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

# Scintilla/SciMoz utilities for Komodo.

import os
import sys

import logging
from xpcom import components
import sciutils



#---- globals

log = logging.getLogger("koSciUtils")
#log.setLevel(logging.DEBUG)

#XXX This "has" to be manually kept in sync with values in the scintilla
#    code. Mind you, this is only used for debugging (right now anyway) so
#    it is not _that_ crucial. I have not added all languages b/c I don't
#    need them.
_gLang2StyleNum2Name = {
    "Python": {
        components.interfaces.ISciMoz.SCE_P_DEFAULT: "P_DEFAULT",
        components.interfaces.ISciMoz.SCE_P_COMMENTLINE: "P_COMMENTLINE",
        components.interfaces.ISciMoz.SCE_P_NUMBER: "P_NUMBER",
        components.interfaces.ISciMoz.SCE_P_STRING: "P_STRING",
        components.interfaces.ISciMoz.SCE_P_CHARACTER: "P_CHARACTER",
        components.interfaces.ISciMoz.SCE_P_WORD: "P_WORD",
        components.interfaces.ISciMoz.SCE_P_TRIPLE: "P_TRIPLE",
        components.interfaces.ISciMoz.SCE_P_TRIPLEDOUBLE: "P_TRIPLEDOUBLE",
        components.interfaces.ISciMoz.SCE_P_CLASSNAME: "P_CLASSNAME",
        components.interfaces.ISciMoz.SCE_P_DEFNAME: "P_DEFNAME",
        components.interfaces.ISciMoz.SCE_P_OPERATOR: "P_OPERATOR",
        components.interfaces.ISciMoz.SCE_P_IDENTIFIER: "P_IDENTIFIER",
        components.interfaces.ISciMoz.SCE_P_COMMENTBLOCK: "P_COMMENTBLOCK",
        components.interfaces.ISciMoz.SCE_P_STRINGEOL: "P_STRINGEOL",
    },
    "Perl" : {
        components.interfaces.ISciMoz.SCE_PL_DEFAULT: "PL_DEFAULT",
        components.interfaces.ISciMoz.SCE_PL_ERROR: "PL_ERROR",
        components.interfaces.ISciMoz.SCE_PL_COMMENTLINE: "PL_COMMENTLINE",
        components.interfaces.ISciMoz.SCE_PL_POD: "PL_POD",
        components.interfaces.ISciMoz.SCE_PL_NUMBER: "PL_NUMBER",
        components.interfaces.ISciMoz.SCE_PL_WORD: "PL_WORD",
        components.interfaces.ISciMoz.SCE_PL_STRING: "PL_STRING",
        components.interfaces.ISciMoz.SCE_PL_CHARACTER: "PL_CHARACTER",
        components.interfaces.ISciMoz.SCE_PL_PUNCTUATION: "PL_PUNCTUATION",
        components.interfaces.ISciMoz.SCE_PL_PREPROCESSOR: "PL_PREPROCESSOR",
        components.interfaces.ISciMoz.SCE_PL_OPERATOR: "PL_OPERATOR",
        components.interfaces.ISciMoz.SCE_PL_IDENTIFIER: "PL_IDENTIFIER",
        components.interfaces.ISciMoz.SCE_PL_SCALAR: "PL_SCALAR",
        components.interfaces.ISciMoz.SCE_PL_ARRAY: "PL_ARRAY",
        components.interfaces.ISciMoz.SCE_PL_HASH: "PL_HASH",
        components.interfaces.ISciMoz.SCE_PL_SYMBOLTABLE: "PL_SYMBOLTABLE",
        components.interfaces.ISciMoz.SCE_PL_VARIABLE_INDEXER: "PL_VARIABLE_INDEXER",
        components.interfaces.ISciMoz.SCE_PL_REGEX: "PL_REGEX",
        components.interfaces.ISciMoz.SCE_PL_REGSUBST: "PL_REGSUBST",
        components.interfaces.ISciMoz.SCE_PL_LONGQUOTE: "PL_LONGQUOTE",
        components.interfaces.ISciMoz.SCE_PL_BACKTICKS: "PL_BACKTICKS",
        components.interfaces.ISciMoz.SCE_PL_DATASECTION: "PL_DATASECTION",
        components.interfaces.ISciMoz.SCE_PL_HERE_DELIM: "PL_HERE_DELIM",
        components.interfaces.ISciMoz.SCE_PL_HERE_Q: "PL_HERE_Q",
        components.interfaces.ISciMoz.SCE_PL_HERE_QQ: "PL_HERE_QQ",
        components.interfaces.ISciMoz.SCE_PL_HERE_QX: "PL_HERE_QX",
        components.interfaces.ISciMoz.SCE_PL_STRING_Q: "PL_STRING_Q",
        components.interfaces.ISciMoz.SCE_PL_STRING_QQ: "PL_STRING_QQ",
        components.interfaces.ISciMoz.SCE_PL_STRING_QX: "PL_STRING_QX",
        components.interfaces.ISciMoz.SCE_PL_STRING_QR: "PL_STRING_QR",
        components.interfaces.ISciMoz.SCE_PL_STRING_QW: "PL_STRING_QW",
        components.interfaces.ISciMoz.SCE_PL_FORMAT_IDENT: "PL_FORMAT_IDENT",
        components.interfaces.ISciMoz.SCE_PL_FORMAT: "PL_FORMAT",
        components.interfaces.ISciMoz.SCE_PL_STRING_VAR: "STRING_VAR",
        components.interfaces.ISciMoz.SCE_PL_XLAT: "PL_XLAT",
        components.interfaces.ISciMoz.SCE_PL_REGEX_VAR: "PL_REGEX_VAR",
        components.interfaces.ISciMoz.SCE_PL_REGSUBST_VAR: "PL_REGSUBST_VAR",
        components.interfaces.ISciMoz.SCE_PL_BACKTICKS_VAR: "PL_BACKTICKS_VAR",
        components.interfaces.ISciMoz.SCE_PL_HERE_QQ_VAR: "PL_HERE_QQ_VAR",
        components.interfaces.ISciMoz.SCE_PL_HERE_QX_VAR: "PL_HERE_QX_VAR",
        components.interfaces.ISciMoz.SCE_PL_STRING_QQ_VAR: "PL_STRING_QQ_VAR",
        components.interfaces.ISciMoz.SCE_PL_STRING_QX_VAR: "PL_STRING_QX_VAR",
        components.interfaces.ISciMoz.SCE_PL_STRING_QR_VAR: "PL_STRING_QR_VAR",
    },
    "Ruby" : {
        components.interfaces.ISciMoz.SCE_RB_DEFAULT: "RB_DEFAULT",
        components.interfaces.ISciMoz.SCE_RB_ERROR: "RB_ERROR",
        components.interfaces.ISciMoz.SCE_RB_COMMENTLINE: "RB_COMMENTLINE",
        components.interfaces.ISciMoz.SCE_RB_POD: "RB_POD",
        components.interfaces.ISciMoz.SCE_RB_NUMBER: "RB_NUMBER",
        components.interfaces.ISciMoz.SCE_RB_WORD: "RB_WORD",
        components.interfaces.ISciMoz.SCE_RB_STRING: "RB_STRING",
        components.interfaces.ISciMoz.SCE_RB_CHARACTER: "RB_CHARACTER",
        components.interfaces.ISciMoz.SCE_RB_CLASSNAME: "RB_CLASSNAME",
        components.interfaces.ISciMoz.SCE_RB_DEFNAME: "RB_DEFNAME",
        components.interfaces.ISciMoz.SCE_RB_OPERATOR: "RB_OPERATOR",
        components.interfaces.ISciMoz.SCE_RB_IDENTIFIER: "RB_IDENTIFIER",
        components.interfaces.ISciMoz.SCE_RB_REGEX: "RB_REGEX",
        components.interfaces.ISciMoz.SCE_RB_GLOBAL: "RB_GLOBAL",
        components.interfaces.ISciMoz.SCE_RB_SYMBOL: "RB_SYMBOL",
        components.interfaces.ISciMoz.SCE_RB_MODULE_NAME: "RB_MODULE_NAME",
        components.interfaces.ISciMoz.SCE_RB_INSTANCE_VAR: "RB_INSTANCE_VAR",
        components.interfaces.ISciMoz.SCE_RB_CLASS_VAR: "RB_CLASS_VAR",
        components.interfaces.ISciMoz.SCE_RB_BACKTICKS: "RB_BACKTICKS",
        components.interfaces.ISciMoz.SCE_RB_DATASECTION: "RB_DATASECTION",
        components.interfaces.ISciMoz.SCE_RB_HERE_DELIM: "RB_HERE_DELIM",
        components.interfaces.ISciMoz.SCE_RB_HERE_Q: "RB_HERE_Q",
        components.interfaces.ISciMoz.SCE_RB_HERE_QQ: "RB_HERE_QQ",
        components.interfaces.ISciMoz.SCE_RB_HERE_QX: "RB_HERE_QX",
        components.interfaces.ISciMoz.SCE_RB_STRING_Q: "RB_STRING_Q",
        components.interfaces.ISciMoz.SCE_RB_STRING_QQ: "RB_STRING_QQ",
        components.interfaces.ISciMoz.SCE_RB_STRING_QX: "RB_STRING_QX",
        components.interfaces.ISciMoz.SCE_RB_STRING_QR: "RB_STRING_QR",
        components.interfaces.ISciMoz.SCE_RB_STRING_QW: "RB_STRING_QW",
        components.interfaces.ISciMoz.SCE_RB_WORD_DEMOTED: "RB_WORD_DEMOTED",
        components.interfaces.ISciMoz.SCE_RB_STDIN: "RB_STDIN",
        components.interfaces.ISciMoz.SCE_RB_STDOUT: "RB_STDOUT",
        components.interfaces.ISciMoz.SCE_RB_STDERR: "RB_STDERR",
        components.interfaces.ISciMoz.SCE_RB_UPPER_BOUND: "RB_UPPER_BOUND",
    },
    "Errors" : {
        components.interfaces.ISciMoz.SCE_ERR_DEFAULT: "ERR_DEFAULT",
        components.interfaces.ISciMoz.SCE_ERR_PYTHON: "ERR_PYTHON",
        components.interfaces.ISciMoz.SCE_ERR_GCC: "ERR_GCC",
        components.interfaces.ISciMoz.SCE_ERR_MS: "ERR_MS",
        components.interfaces.ISciMoz.SCE_ERR_CMD: "ERR_CMD",
        components.interfaces.ISciMoz.SCE_ERR_BORLAND: "ERR_BORLAND",
        components.interfaces.ISciMoz.SCE_ERR_PERL: "ERR_PERL",
        components.interfaces.ISciMoz.SCE_ERR_NET: "ERR_NET",
        components.interfaces.ISciMoz.SCE_ERR_LUA: "ERR_LUA",
        components.interfaces.ISciMoz.SCE_ERR_CTAG: "ERR_CTAG",
        components.interfaces.ISciMoz.SCE_ERR_DIFF_CHANGED: "ERR_DIFF_CHANGED",
        components.interfaces.ISciMoz.SCE_ERR_DIFF_ADDITION: "ERR_DIFF_ADDITION",
        components.interfaces.ISciMoz.SCE_ERR_DIFF_DELETION: "ERR_DIFF_DELETION",
        components.interfaces.ISciMoz.SCE_ERR_DIFF_MESSAGE: "ERR_DIFF_MESSAGE",
        components.interfaces.ISciMoz.SCE_ERR_PHP: "ERR_PHP",
        components.interfaces.ISciMoz.SCE_ERR_ELF: "ERR_ELF",
        components.interfaces.ISciMoz.SCE_ERR_IFC: "ERR_IFC",
    },
    "Diff" : {
        components.interfaces.ISciMoz.SCE_DIFF_DEFAULT: "DIFF_DEFAULT",
        components.interfaces.ISciMoz.SCE_DIFF_COMMENT: "DIFF_COMMENT",
        components.interfaces.ISciMoz.SCE_DIFF_COMMAND: "DIFF_COMMAND",
        components.interfaces.ISciMoz.SCE_DIFF_HEADER: "DIFF_HEADER",
        components.interfaces.ISciMoz.SCE_DIFF_POSITION: "DIFF_POSITION",
        components.interfaces.ISciMoz.SCE_DIFF_DELETED: "DIFF_DELETED",
        components.interfaces.ISciMoz.SCE_DIFF_ADDED: "DIFF_ADDED",
    },
    "CSS" : {
        components.interfaces.ISciMoz.SCE_CSS_DEFAULT: "CSS_DEFAULT",
        components.interfaces.ISciMoz.SCE_CSS_TAG: "CSS_TAG",
        components.interfaces.ISciMoz.SCE_CSS_CLASS: "CSS_CLASS",
        components.interfaces.ISciMoz.SCE_CSS_PSEUDOCLASS: "CSS_PSEUDOCLASS",
        components.interfaces.ISciMoz.SCE_CSS_UNKNOWN_PSEUDOCLASS: "CSS_UNKNOWN_PSEUDOCLASS",
        components.interfaces.ISciMoz.SCE_CSS_OPERATOR: "CSS_OPERATOR",
        components.interfaces.ISciMoz.SCE_CSS_IDENTIFIER: "CSS_IDENTIFIER",
        components.interfaces.ISciMoz.SCE_CSS_UNKNOWN_IDENTIFIER: "CSS_UNKNOWN_IDENTIFIER",
        components.interfaces.ISciMoz.SCE_CSS_VALUE: "CSS_VALUE",
        components.interfaces.ISciMoz.SCE_CSS_COMMENT: "CSS_COMMENT",
        components.interfaces.ISciMoz.SCE_CSS_ID: "CSS_ID",
        components.interfaces.ISciMoz.SCE_CSS_IMPORTANT: "CSS_IMPORTANT",
        components.interfaces.ISciMoz.SCE_CSS_DIRECTIVE: "CSS_DIRECTIVE",
        components.interfaces.ISciMoz.SCE_CSS_DOUBLESTRING: "CSS_DOUBLESTRING",
        components.interfaces.ISciMoz.SCE_CSS_SINGLESTRING: "CSS_SINGLESTRING",
    },
    "XML" : {
        components.interfaces.ISciMoz.SCE_XML_DEFAULT: "XML_DEFAULT",
        components.interfaces.ISciMoz.SCE_XML_PROLOG: "XML_PROLOG",
        components.interfaces.ISciMoz.SCE_XML_START_TAG_OPEN: "XML_START_TAG_OPEN",
        components.interfaces.ISciMoz.SCE_XML_START_TAG_NAME: "XML_START_TAG_NAME",
        components.interfaces.ISciMoz.SCE_XML_START_TAG_CLOSE: "XML_START_TAG_CLOSE",
        components.interfaces.ISciMoz.SCE_XML_START_TAG_EMPTY_CLOSE: "XML_START_TAG_EMPTY_CLOSE",
        components.interfaces.ISciMoz.SCE_XML_START_TAG_ATTR_NAME: "XML_START_TAG_ATTR_NAME",
        components.interfaces.ISciMoz.SCE_XML_START_TAG_ATTR_EQUALS: "XML_START_TAG_ATTR_EQUALS",
        components.interfaces.ISciMoz.SCE_XML_START_TAG_ATTR_QUOT_OPEN: "XML_START_TAG_ATTR_QUOT_OPEN",
        components.interfaces.ISciMoz.SCE_XML_START_TAG_ATTR_QUOT_CONTENT: "XML_START_TAG_ATTR_QUOT_CONTENT",
        components.interfaces.ISciMoz.SCE_XML_START_TAG_ATTR_QUOT_CLOSE: "XML_START_TAG_ATTR_QUOT_CLOSE",
        components.interfaces.ISciMoz.SCE_XML_START_TAG_ATTR_APOS_OPEN: "XML_START_TAG_ATTR_APOS_OPEN",
        components.interfaces.ISciMoz.SCE_XML_START_TAG_ATTR_APOS_CONTENT: "XML_START_TAG_ATTR_APOS_CONTENT",
        components.interfaces.ISciMoz.SCE_XML_START_TAG_ATTR_APOS_CLOSE: "XML_START_TAG_ATTR_APOS_CLOSE",
        components.interfaces.ISciMoz.SCE_XML_END_TAG_OPEN: "XML_END_TAG_OPEN",
        components.interfaces.ISciMoz.SCE_XML_END_TAG_NAME: "XML_END_TAG_NAME",
        components.interfaces.ISciMoz.SCE_XML_END_TAG_CLOSE: "XML_END_TAG_CLOSE",
        components.interfaces.ISciMoz.SCE_XML_START_TAG_ATTR_NUMBER: "XML_START_TAG_ATTR_NUMBER",
        components.interfaces.ISciMoz.SCE_XML_ENTITY_REF: "XML_ENTITY_REF",
        components.interfaces.ISciMoz.SCE_XML_CHAR_REF: "XML_CHAR_REF",
        components.interfaces.ISciMoz.SCE_XML_DATA_NEWLINE: "XML_DATA_NEWLINE",
        components.interfaces.ISciMoz.SCE_XML_DATA_CHARS: "XML_DATA_CHARS",
        components.interfaces.ISciMoz.SCE_XML_CDATA_SECT_OPEN: "XML_CDATA_SECT_OPEN",
        components.interfaces.ISciMoz.SCE_XML_CDATA_SECT_CONTENT: "XML_CDATA_SECT_CONTENT",
        components.interfaces.ISciMoz.SCE_XML_CDATA_SECT_CLOSE: "XML_CDATA_SECT_CLOSE",
        components.interfaces.ISciMoz.SCE_XML_COMMENT_OPEN: "XML_COMMENT_OPEN",
        components.interfaces.ISciMoz.SCE_XML_COMMENT_CONTENT: "XML_COMMENT_CONTENT",
        components.interfaces.ISciMoz.SCE_XML_COMMENT_CLOSE: "XML_COMMENT_CLOSE",
        components.interfaces.ISciMoz.SCE_XML_PI_OPEN: "XML_PI_OPEN",
        components.interfaces.ISciMoz.SCE_XML_PI_CONTENT: "XML_PI_CONTENT",
        components.interfaces.ISciMoz.SCE_XML_PI_CLOSE: "XML_PI_CLOSE",
        components.interfaces.ISciMoz.SCE_XML_XML_DECL_OPEN: "XML_XML_DECL_OPEN",
        components.interfaces.ISciMoz.SCE_XML_XML_DECL_CONTENT: "XML_XML_DECL_CONTENT",
        components.interfaces.ISciMoz.SCE_XML_XML_DECL_CLOSE: "XML_XML_DECL_CLOSE",
        components.interfaces.ISciMoz.SCE_XML_BOM: "XML_BOM",
        components.interfaces.ISciMoz.SCE_XPATH_TAG_NAME: "XPATH_TAG_NAME",
        components.interfaces.ISciMoz.SCE_XPATH_ATTR_NAME: "XPATH_ATTR_NAME",
        components.interfaces.ISciMoz.SCE_XPATH_OPEN: "XPATH_OPEN",
        components.interfaces.ISciMoz.SCE_XPATH_CONTENT_QUOT: "XPATH_CONTENT_QUOT",
        components.interfaces.ISciMoz.SCE_XPATH_CONTENT_APOS: "XPATH_CONTENT_APOS",
        components.interfaces.ISciMoz.SCE_XPATH_CLOSE: "XPATH_CLOSE",
        components.interfaces.ISciMoz.SCE_XML_START_TAG_WHITE_SPACE: "XML_START_TAG_WHITE_SPACE",
        components.interfaces.ISciMoz.SCE_XML_START_TAG_ATTR_UNQUOTED: "XML_START_TAG_ATTR_UNQUOTED",
        components.interfaces.ISciMoz.SCE_XML_END_TAG_WHITE_SPACE: "XML_END_TAG_WHITE_SPACE",
        components.interfaces.ISciMoz.SCE_XML_DECLARATION_OPEN: "XML_DECLARATION_OPEN",
        components.interfaces.ISciMoz.SCE_XML_DECLARATION_TYPE: "XML_DECLARATION_TYPE",
        components.interfaces.ISciMoz.SCE_XML_DECLN_WHITE_SPACE: "XML_DECLN_WHITE_SPACE",
        components.interfaces.ISciMoz.SCE_XML_DECLN_NAME: "XML_DECLN_NAME",
        components.interfaces.ISciMoz.SCE_XML_DECLN_CLOSE: "XML_DECLN_CLOSE",
        components.interfaces.ISciMoz.SCE_XML_DECLN_QUOT_CONTENT: "XML_DECLN_QUOT_CONTENT",
        components.interfaces.ISciMoz.SCE_XML_DECLN_APOS_CONTENT: "XML_DECLN_APOS_CONTENT",
        components.interfaces.ISciMoz.SCE_XML_DECLN_DATA_CHARS: "XML_DECLN_DATA_CHARS",
        components.interfaces.ISciMoz.SCE_XML_UPPER_BOUND: "XML_UPPER_BOUND",
    },
    "Tcl" : {
        components.interfaces.ISciMoz.SCE_TCL_DEFAULT: "TCL_DEFAULT",
        components.interfaces.ISciMoz.SCE_TCL_COMMENT: "TCL_COMMENT",
        components.interfaces.ISciMoz.SCE_TCL_VARIABLE: "TCL_VARIABLE",
        components.interfaces.ISciMoz.SCE_TCL_ARRAY: "TCL_ARRAY",
        components.interfaces.ISciMoz.SCE_TCL_NUMBER: "TCL_NUMBER",
        components.interfaces.ISciMoz.SCE_TCL_WORD: "TCL_WORD",
        components.interfaces.ISciMoz.SCE_TCL_STRING: "TCL_STRING",
        components.interfaces.ISciMoz.SCE_TCL_CHARACTER: "TCL_CHARACTER",
        components.interfaces.ISciMoz.SCE_TCL_LITERAL: "TCL_LITERAL",
        components.interfaces.ISciMoz.SCE_TCL_IDENTIFIER: "TCL_IDENTIFIER",
        components.interfaces.ISciMoz.SCE_TCL_OPERATOR: "TCL_OPERATOR",
        components.interfaces.ISciMoz.SCE_TCL_EOL: "TCL_EOL",
        components.interfaces.ISciMoz.SCE_TCL_UPPER_BOUND: "TCL_UPPER_BOUND",
    },
}


#---- internal support stuff


#---- component implementation

class KoSciUtils:
    _com_interfaces_ = [components.interfaces.koISciUtils]
    _reg_clsid_ = "{C2CDA47E-0F85-4DD1-96C6-33E9CAC87B3C}"
    _reg_contractid_ = "@activestate.com/koSciUtils;1"
    _reg_desc_ = "Komodo Scintilla/SciMoz Utility Service"

    #XXX Move this into sciutils.py and just provide an XPCOM shim here.
    def styleNameFromNum(self, language, styleNum):
        log.info("KoSciUtils.styleNameFromNum(language='%s', styleNum=%d)",
                 language, styleNum)
        try:
            return _gLang2StyleNum2Name[language][styleNum]
        except KeyError:
            return "unknown"

    def test_scimoz(self, scimoz):
        reload(sciutils)  # reload so we can re-test w/o re-starting Komodo
        testCases = [sciutils.SciUtilsTestCase]
        sciutils.runSciMozTests(testCases, scimoz)
