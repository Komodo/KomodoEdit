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

"""JavaScript-specific Language Services implementations."""

from xpcom import components, ServerException

from langinfo_prog import JavaScriptLangInfo
from koLanguageServiceBase import *


def registerLanguage(registery):
    registery.registerLanguage(koJavaScriptLanguage())

class koJavaScriptLanguage(KoLanguageBase):
    name = "JavaScript"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{0DD83914-E2F6-478a-A77E-7307833A7601}"

    accessKey = 'j'
    primary = 1
    defaultExtension = ".js"
    commentDelimiterInfo = {
        "line": [ "//" ],
        "block": [ ("/*", "*/") ],
        "markup": "*",
    }
    _dedenting_statements = [u'throw', u'return', u'break', u'continue']
    _indenting_statements = [u'case']
    searchURL = "http://www.google.com/search?q=site%3Ahttp%3A%2F%2Fdeveloper.mozilla.org%2Fen%2Fdocs%2FCore_JavaScript_1.5_Reference+%W"
    # matches:
    # function name
    # name: function
    # name = function
    # class.prototype.name = function
    namedBlockDescription = 'JavaScript functions and classes'
    namedBlockRE = r'^[ |\t]*?(?:([\w|\.|_]*?)\s*=\s*function|function\s*([\w|\_]*?)|([\w|\_]*?)\s*:\s*function).*?$'
    supportsSmartIndent = "brace"
    sample = """function chkrange(elem,minval,maxval) {
    // Comment
    if (elem.value < minval - 1 ||
        elem.value > maxval + 1) {
          alert("Value of " + elem.name + " is out of range!");
    }
}
"""

    styleStdin = components.interfaces.ISciMoz.SCE_C_STDIN
    styleStdout = components.interfaces.ISciMoz.SCE_C_STDOUT
    styleStderr = components.interfaces.ISciMoz.SCE_C_STDERR

    def __init__(self):
        KoLanguageBase.__init__(self)
        self._style_info.update(
            _block_comment_styles = [sci_constants.SCE_C_COMMENT,
                                     sci_constants.SCE_C_COMMENTDOC,
                                     sci_constants.SCE_C_COMMENTDOCKEYWORD,
                                     sci_constants.SCE_C_COMMENTDOCKEYWORDERROR],
            _variable_styles = [components.interfaces.ISciMoz.SCE_C_IDENTIFIER]
            )
        self._setupIndentCheckSoftChar()
        
    def getVariableStyles(self):
        return self._style_info._variable_styles
    
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(components.interfaces.ISciMoz.SCLEX_CPP)
            self._lexer.setKeywords(0, JavaScriptLangInfo.keywords)
            self._lexer.supportsFolding = 1
        return self._lexer

