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

# yaml.org
    
class koYAMLLanguage(KoLanguageBase):
    name = "YAML"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{9a7eb39b-5e5a-44a7-9161-94b4b82ce9be}"
    _reg_categories_ = [("komodo-language", name)]

    _stateMap = {
        'default': ('SCE_YAML_DEFAULT',),
        'keywords': ('SCE_YAML_KEYWORD',),
        'identifiers': ('SCE_YAML_IDENTIFIER',),
        'comments': ('SCE_YAML_COMMENT',),
        'numbers': ('SCE_YAML_NUMBER',),
        'strings': ('SCE_YAML_TEXT',),
        'references': ('SCE_YAML_REFERENCE',),
        'documents': ('SCE_YAML_DOCUMENT',),
        'errors': ('SCE_YAML_ERROR',),
        'operators': ('SCE_YAML_OPERATOR',),
        }

    defaultExtension = '.yaml' # .yml
    commentDelimiterInfo = {"line": [ "#" ]}
    
    _indent_open_chars = ':'
    supportsSmartIndent = 'python'
    
    sample = """---
players:
  Vladimir Kramnik: &kramnik
    rating: 2700
    status: GM
  Deep Fritz: &fritz
    rating: 2700
    status: Computer
  David Mertz: &mertz
    rating: 1400
    status: Amateur

matches:
  -
    Date: 2002-10-04
    White: *fritz
    Black: *kramnik
    Result: Draw
  -
    Date: 2002-10-06
    White: *kramnik
    Black: *fritz
    Result: White
"""
    def __init__(self):
        KoLanguageBase.__init__(self)
        self._style_info.update(
            _indent_styles = [sci_constants.SCE_YAML_OPERATOR],
            _indent_open_styles = [sci_constants.SCE_YAML_OPERATOR],
            )

    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(sci_constants.SCLEX_YAML)
            self._lexer.setKeywords(0, self._keywords)
            self._lexer.supportsFolding = 1
        return self._lexer

    _keywords = ['true', 'false', 'yes', 'no']
