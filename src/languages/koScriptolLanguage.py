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

class koScriptolLanguage(KoLanguageBase):
    name = "Scriptol"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{cce047e6-ddd8-4790-b750-f53c4c2c7894}"
    _reg_categories_ = [("komodo-language", name)]

    _stateMap = {
        'default': ('SCE_SCRIPTOL_DEFAULT',),
        'keywords': ('SCE_SCRIPTOL_KEYWORD',),
        'identifiers': ('SCE_SCRIPTOL_IDENTIFIER',),
        'comments': ('SCE_SCRIPTOL_COMMENTLINE',
                     'SCE_SCRIPTOL_COMMENTBLOCK',),
        'numbers': ('SCE_SCRIPTOL_NUMBER',),
        'strings': ('SCE_SCRIPTOL_STRING',
                    'SCE_SCRIPTOL_CHARACTER',),
        'stringeol': ('SCE_SCRIPTOL_STRINGEOL',),
        'operators': ('SCE_SCRIPTOL_OPERATOR',),
        'white': ('SCE_SCRIPTOL_WHITE',),
        'persistent': ('SCE_SCRIPTOL_PERSISTENT',),
        'cstyle': ('SCE_SCRIPTOL_CSTYLE',),
        'triple': ('SCE_SCRIPTOL_TRIPLE',),
        'classnames': ('SCE_SCRIPTOL_CLASSNAME',),
        'preprocessor': ('SCE_SCRIPTOL_PREPROCESSOR',),
        }

    defaultExtension = '.sol'
    commentDelimiterInfo = {"line": [ "`" ]}
    
    sample = """
SAMPLE NOT AVAILABLE
"""
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(
                components.interfaces.ISciMoz.SCLEX_SCRIPTOL)
            self._lexer.setKeywords(0, self._keywords)
            self._lexer.supportsFolding = 0
        return self._lexer

    _keywords = """act action alias always and array as
        bool boolean break by byte
        class case catch const constant continue
        dyn def define dict do double
        echo else elsif end enum error false file for float forever function
        globak gtk
        in if ifdef import include int integer java javax
        let long match mod nil not natural null number
        or print protected public real return redo
        scan script scriptol sol short super static step until using
        var text then this true try
        void volatile while when
        undef zero""".split()