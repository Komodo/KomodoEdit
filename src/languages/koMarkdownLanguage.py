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

class koMarkdownLanguage(KoLanguageBase):
    name = "Markdown"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{6bb5154a-4e58-4778-8dbb-a550c3830769}"
    _reg_categories_ = [("komodo-language", name)]

    _stateMap = {
        'default': ('SCE_MARKDOWN_DEFAULT',),
        'strings': ('SCE_MARKDOWN_STRONG1',
                    'SCE_MARKDOWN_STRONG2',
                    'SCE_MARKDOWN_EM1',
                    'SCE_MARKDOWN_EM2',
                    ),
        'numbers': ('SCE_MARKDOWN_BLOCKQUOTE',
                      'SCE_MARKDOWN_STRIKEOUT',
                      'SCE_MARKDOWN_HRULE',
                      'SCE_MARKDOWN_LINK',
                      ),
        'comments': ('SCE_MARKDOWN_HEADER1',
                     'SCE_MARKDOWN_HEADER2',
                     'SCE_MARKDOWN_HEADER3',),
        'variables': ('SCE_MARKDOWN_HEADER4',
                     'SCE_MARKDOWN_HEADER5',
                     'SCE_MARKDOWN_HEADER6',),
        'keywords': ('SCE_MARKDOWN_PRECHAR',),
        'operators': ('SCE_MARKDOWN_ULIST_ITEM',
                      'SCE_MARKDOWN_OLIST_ITEM'
                      ),
        'functions': ('SCE_MARKDOWN_LINE_BEGIN',),
        'macros': ('SCE_MARKDOWN_CODE',
                   'SCE_MARKDOWN_CODE2',
                   ),
        'identifiers': ('SCE_MARKDOWN_CODEBK',),
    }
    defaultExtension = '.md'
    primary = 1
    commentDelimiterInfo = {"line": [ ";" ]}
    
    sample = """
Heading
=======

Sub-heading
-----------

### Another deeper heading

Paragraphs are separated by a blank line.

Let 2 spaces at the end of a line to do a line break

Text attributes *italic*, **bold**, `monospace`, ~~strikethrough~~ .

A [link](http://example.com). <<<   No space between ] and (  >>>

Shopping list:

  * apples
  * oranges
  * pears

Numbered list:

  1. apples
  2. oranges
  3. pears

The rain---not the reign---in Spain.
"""
    
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(
                components.interfaces.ISciMoz.SCLEX_MARKDOWN)
            self._lexer.setKeywords(0, self._keywords)
        return self._lexer

    # These keywords are commands
    _keywords="""
    """.split()
