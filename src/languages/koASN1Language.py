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

class koASN1Language(KoLanguageBase):
    name = "ASN1"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{b9ae6e99-1106-475c-a36f-36f34ce11c16}"
    _reg_categories_ = [("komodo-language", name)]

    _stateMap = {
        'default': ('SCE_ASN1_DEFAULT',),
        'keywords': ('SCE_ASN1_KEYWORD',),
        'identifiers': ('SCE_ASN1_IDENTIFIER',),
        'comments': ('SCE_ASN1_COMMENT',),
        'operators': ('SCE_ASN1_OPERATOR',),
        'numbers': ('SCE_ASN1_SCALAR',),
        'strings': ('SCE_ASN1_STRING',),
        'attributes': ('SCE_ASN1_ATTRIBUTE',),
        'oid': ('SCE_ASN1_OID',),
        'descriptor': ('SCE_ASN1_DESCRIPTOR',),
        'type': ('SCE_ASN1_TYPE',),
        }
    defaultExtension = None
    commentDelimiterInfo = {}
    
    sample = """
SAMPLE NOT AVAILABLE
"""
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(components.interfaces.ISciMoz.SCLEX_ASN1)
        return self._lexer
