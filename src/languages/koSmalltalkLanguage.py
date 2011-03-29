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

class koSmalltalkLanguage(KoLanguageBase):
    name = "Smalltalk"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{01E22A2E-53EF-11DA-AFBB-000D935D3368}"
    _reg_categories_ = [("komodo-language", name)]

    commentDelimiterInfo = {}

    defaultExtension = ".st" 

    supportsSmartIndent = "brace"
    sciMozLexer = components.interfaces.ISciMoz.SCLEX_SMALLTALK

    _stateMap = {
        'default': ('SCE_ST_DEFAULT',),
        'keywords': ('SCE_ST_SPECIAL', 'SCE_ST_SPEC_SEL', 'SCE_ST_BOOL',
                     'SCE_ST_SELF', 'SCE_ST_SUPER', 'SCE_ST_NIL',
                     'SCE_ST_KWSEND', 'SCE_ST_RETURN',),
        'symbols': ('SCE_ST_SYMBOL',),
        'comments': ('SCE_ST_COMMENT',),
        'variables': ('SCE_ST_GLOBAL',),
        'numbers': ('SCE_ST_NUMBER', 'SCE_ST_BINARY',),
        'strings': ('SCE_ST_STRING', 'SCE_ST_CHARACTER',),
        'assign': ('SCE_ST_ASSIGN',),
        }
    sample = """
SAMPLE NOT AVAILABLE
"""

    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(self.sciMozLexer)
            self._lexer.setKeywords(0, self._keywords)
            self._lexer.supportsFolding = 0
        return self._lexer

    _keywords = """
        ifTrue: ifFalse: whileTrue: whileFalse: ifNil: ifNotNil:
        whileTrue whileFalse repeat isNil notNil
    """.split()
    
