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

class koNimrodLanguage(KoLanguageBase):
    name = "Nimrod"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{edf6481c-4b58-4b7f-acde-4506eeaca77f}"
    _reg_categories_ = [("komodo-language", name)]

    _stateMap = {
        'default': ('SCE_P_DEFAULT',),
        'strings': ('SCE_P_STRING',
                    'SCE_P_CHARACTER',),
        'numbers': ('SCE_P_NUMBER',),
        'comments': ('SCE_P_COMMENTLINE',),
        'keywords': ('SCE_P_WORD',),
        'operators': ('SCE_P_OPERATOR',),
        'identifiers': ('SCE_P_IDENTIFIER',),
    }
    defaultExtension = '.nim'
    
    sample = """No sample is available."""
    
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(
                components.interfaces.ISciMoz.SCLEX_PYTHON)
            self._lexer.setKeywords(0, self._keywords)
        return self._lexer

    # http://force7.de/nimrod/manual.html#identifiers-keywords
    _keywords="""addr and as asm
bind block break
case cast const continue converter
discard distinct div
elif else end enum except
finally for from generic
if implies import in include is isnot iterator
lambda
macro method mod
nil not notin
object of or out
proc ptr
raise ref return
shl shr
template try tuple type
var
when while with without
xor
yield
    """.split()
