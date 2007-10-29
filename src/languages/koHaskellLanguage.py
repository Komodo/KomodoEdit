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

def registerLanguage(registery):
    registery.registerLanguage(koHaskellLanguage())

# see http://haskell.org/
class koHaskellLanguage(KoLanguageBase):
    name = "Haskell"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{2545AA9A-53EB-11DA-BF7A-000D935D3368}"

    commentDelimiterInfo = {
        "line": [ "--" ]
    }

    defaultExtension = ".hs" 

    supportsSmartIndent = "brace"
    sciMozLexer = components.interfaces.ISciMoz.SCLEX_HASKELL

    _stateMap = {
        'default': ('SCE_HA_DEFAULT',),
        'keywords': ('SCE_HA_KEYWORD',),
        'identifiers': ('SCE_HA_IDENTIFIER',),
        'comments': ('SCE_HA_COMMENTLINE','SCE_HA_COMMENTBLOCK',
                     'SCE_HA_COMMENTBLOCK2', 'SCE_HA_COMMENTBLOCK3',),
        'operators': ('SCE_HA_OPERATOR',),
        'numbers': ('SCE_HA_NUMBER',),
        'strings': ('SCE_HA_STRING', 'SCE_HA_CHARACTER',),
        'class': ('SCE_HA_CLASS',),
        'module': ('SCE_HA_MODULE',),
        'data': ('SCE_HA_DATA',),
        'capital': ('SCE_HA_CAPITAL',),
        'import': ('SCE_HA_IMPORT',),
        'instance': ('SCE_HA_INSTANCE',),
        }
    sample = """
SAMPLE NOT AVAILABLE
"""

    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(self.sciMozLexer)
            self._lexer.setKeywords(0, self._keywords)
            self._lexer.supportsFolding = 1
        return self._lexer

    _keywords = [
        "absolute value", "addition", "and", "array",
        "boolean",
        "ceiling", "character", "concatenate", "concatenation", "constant", "continuation passing style", "cosine", "cosine hyperbolic", "cosine hyperbolic inverse", "cosine inverse",
        "division",
        "empty", "equality", "even",
        "floor", "function composition",
        "index",
        "lazy evaluation", "length", "list", "list calculation", "list construction", "list insertion", "list item",
        "modulo", "monad", "multiplication",
        "nint",
        "odd", "or", "order",
        "power",
        "round",
        "sine", "sine hyperbolic", "sine hyperbolic inverse", "sine inverse", "split", "string", "subtraction", "sum",
        "tangent", "tangent hyperbolic", "tangent hyperbolic inverse", "tangent inverse", "trigonometry", "truncation", "tuple"
                ]
