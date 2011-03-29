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

from xpcom import components, ServerException

from koLanguageServiceBase import *

from xpcom import components, COMException, ServerException, nsError

class _koTandemComputerLanguage(KoLanguageBase):
    _stateMap = {
        'default': ('SCE_C_DEFAULT',),
        'strings': ('SCE_C_STRING', 'SCE_C_CHARACTER',),
        'numbers': ('SCE_C_NUMBER',),
        'comments': ('SCE_C_COMMENT', 'SCE_C_COMMENTLINE',
                     'SCE_C_COMMENTDOC',),
        'keywords': ('SCE_C_WORD',),
        'operators': ('SCE_C_OPERATOR',),
        'identifiers': ('SCE_C_IDENTIFIER',),
    }
    sample = """No sample is available."""
    
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(self.scimozLexer)
            self._lexer.setKeywords(0, self._keywords)
        return self._lexer

    #
    _keywords="""
    """.split()
    
class koTACLLanguage(_koTandemComputerLanguage):
    name = "TACL"
    _reg_clsid_ = "{e16a35cf-3481-4c9c-9bb4-c70baba79fd5}"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_categories_ = [("komodo-language", name)]
    defaultExtension = '.tacl'
    scimozLexer = components.interfaces.ISciMoz.SCLEX_TACL

class koTALLanguage(_koTandemComputerLanguage):
    name = "TAL"
    _reg_clsid_ = "{491b9764-9cb3-4303-80ae-dcc11c52dc18}"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_categories_ = [("komodo-language", name)]
    defaultExtension = '.tal'
    scimozLexer = components.interfaces.ISciMoz.SCLEX_TAL
