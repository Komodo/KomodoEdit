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

class koGui4CliLanguage(KoLanguageBase):
    name = "Gui4Cli"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{2d7a3802-5582-4c58-b7b1-bcfb88f3107b}"
    _reg_categories_ = [("komodo-language", name)]

    _stateMap = {
        'default': ('SCE_GC_DEFAULT',),
        'comments': ('SCE_GC_COMMENTLINE',
                     'SCE_GC_COMMENTBLOCK',),
        'strings': ('SCE_GC_STRING',),
        'globals': ('SCE_GC_GLOBAL',),
        'keywords': ('SCE_GC_COMMAND',),
        'operators': ('SCE_GC_OPERATOR',),
        'attributes': ('SCE_GC_ATTRIBUTE',),
        'control': ('SCE_GC_CONTROL',),
        'events': ('SCE_GC_EVENT',),
    }
    defaultExtension = '.gc'
    commentDelimiterInfo = {
        "line": [ "//" ],
        "block": [ ("/*", "*/") ],
        "markup": "*",
    }
    
    sample = """
SAMPLE NOT AVAILABLE
"""
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(
                components.interfaces.ISciMoz.SCLEX_GUI4CLI)
            self._lexer.supportsFolding = 1
        return self._lexer
