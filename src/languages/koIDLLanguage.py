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

class koIDLLanguage(KoLanguageBase):
    name = "IDL"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{E9A451B7-E13D-4d71-883C-93BD457A3D9F}"
    _reg_categories_ = [("komodo-language", name)]

    accessKey = 'i'
    defaultExtension = ".idl"
    commentDelimiterInfo = {
        "line": [ "//" ],
        "block": [ ("/*", "*/") ],
        "markup": "*",
    }
    supportsSmartIndent = "brace"

    def __init__(self):
        KoLanguageBase.__init__(self)
        self._style_info.update(
            _block_comment_styles = [sci_constants.SCE_C_COMMENT,
                                     sci_constants.SCE_C_COMMENTDOC,
                                     sci_constants.SCE_C_COMMENTDOCKEYWORD,
                                     sci_constants.SCE_C_COMMENTDOCKEYWORDERROR]
            )

    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(components.interfaces.ISciMoz.SCLEX_CPP)
            self._lexer.setKeywords(0, self._keywords)
            self._lexer.setProperty('fold.cpp.syntax.based', '1')
            self._lexer.supportsFolding = 1
        return self._lexer

    _keywords = [
                       # keywords appearing outside of brackets
                       "attribute", "boolean", "char", "const", "double", "float", "in", "inout",
                       "int", "interface", "long", "native", "octet", "out", "readonly", "string",
                       "unsigned", "void", "wchar", "wstring", "fixed",
                       # keywords appearing inside brackets
                       "array", "nsid", "ptr", "ref", "retval", "scriptable", "shared",
                       "iid_is", "notxpcom", "noscript", "uuid",
                       # Corba idl keywords that are not supported by Mozilla,
                       # but are still reserved keywords.
                       # http://www.mozilla.org/scriptable/xpidl/notes/keywords.txt
                       "any", "case", "context", "default", "enum", "exception",
                       "fixed", "module", "none", "oneway", "raises",
                       "sequence", "struct", "switch", "union",
    ]

