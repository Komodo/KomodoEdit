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

class koAPDLLanguage(KoLanguageBase):
    name = "APDL"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{799aeb24-33a0-4f64-8ee1-9dfac22ed828}"
    _reg_categories_ = [("komodo-language", name)]

    _stateMap = {
        'default': ('SCE_APDL_DEFAULT',),
        'keywords': ('SCE_APDL_WORD',),
        'identifiers': ('SCE_ADA_IDENTIFIER',),
        'comments': ('SCE_APDL_COMMENT',
                     'SCE_APDL_COMMENTBLOCK'),
        'numbers': ('SCE_APDL_NUMBER',),
        'strings': ('SCE_APDL_STRING',),
        'functions': ('SCE_APDL_FUNCTION',),
        'keywords': ('SCE_APDL_COMMAND',
                     'SCE_APDL_SLASHCOMMAND',
                     'SCE_APDL_STARCOMMAND',),
        'processor': ('SCE_APDL_PROCESSOR',),
        'arguments': ('SCE_APDL_ARGUMENT',),
        }

    defaultExtension = ".mac"
    commentDelimiterInfo = {
        "line": [ "/COM," ],
    }
    
    sample = """
/BATCH                     !Batch input
/FILE,punch                !Define jobname
/NOPR                      !Suppress printout

/COM, small example

*VWRITE
('*NSET,NSET=NTOP')
LSEL,S,LOC,Y,FTHK
NSLL,S,1
*GET,NNOD,NODE,,COUNT
NNUM = 0
*DO,I,1,NNOD,1
NNUM = NDNEXT(NNUM)
*VWRITE,NNUM
(F7.0,TL1,',')
*ENDDO
ALLSEL
"""
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(components.interfaces.ISciMoz.SCLEX_APDL)
        return self._lexer
