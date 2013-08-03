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

# keyword lists in lexMSSQL
# statements
# data_types
# system_tables
# global_variables
# functions
# stored_procedures
# operators

class koMSSQLLanguage(KoLanguageBase):
    name = "MSSQL"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{f1ee2866-9fcf-441e-bb1d-42274eb7f397}"
    _reg_categories_ = [("komodo-language", name)]

    _stateMap = {
        'default': ('SCE_MSSQL_DEFAULT',),
        'keywords': ('SCE_MSSQL_STATEMENT',
                     'SCE_MSSQL_DATATYPE',
                     'SCE_MSSQL_SYSTABLE',
                     'SCE_MSSQL_DEFAULT_PREF_DATATYPE',),
        'functions': ('SCE_MSSQL_FUNCTION',
                      'SCE_MSSQL_STORED_PROCEDURE',),
        'comments': ('SCE_MSSQL_COMMENT',
                     'SCE_MSSQL_LINE_COMMENT',),
        'numbers': ('SCE_MSSQL_NUMBER',),
        'strings': ('SCE_MSSQL_STRING',),
        'column_names': ('SCE_MSSQL_COLUMN_NAME',
                      'SCE_MSSQL_COLUMN_NAME_2',),
        'operators': ('SCE_MSSQL_OPERATOR',),
        'identifiers': ('SCE_MSSQL_IDENTIFIER',),
        'variables': ('SCE_MSSQL_VARIABLE',
                      'SCE_MSSQL_GLOBAL_VARIABLE',),
        }
    defaultExtension = None
    commentDelimiterInfo = {}
    
    sample = """
SAMPLE NOT AVAILABLE
"""
    def __init__(self):
        KoLanguageBase.__init__(self)
        del self.matchingSoftChars['"']
        self._fastCharData = \
            FastCharData(trigger_char=";",
                         style_list=(sci_constants.SCE_MSSQL_OPERATOR, ),
                         skippable_chars_by_style= { sci_constants.SCE_MSSQL_OPERATOR : "])", })
    
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(
                components.interfaces.ISciMoz.SCLEX_MSSQL)
            self._lexer.supportsFolding = 1
        return self._lexer
