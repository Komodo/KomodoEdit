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

class koCobolLanguage(KoLanguageBase):
    name = "Cobol"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{9a87f3fe-4e3a-452d-990e-1b1541812f67}"
    _reg_categories_ = [("komodo-language", name)]

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
    defaultExtension = '.cbl'
    commentDelimiterInfo = {"line": [ ";" ]}
    
    sample = """No sample is available."""
    
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(
                components.interfaces.ISciMoz.SCLEX_COBOL)
            # From http://cobol.comsci.us/etymology/keywords.html
            # Cobol is case-insensitive, but the lexer doesn't convert, so assume
            # it's not 1973 anymore and people are writing in mixed case.
            keywords="""accept access add advancing after all alphabetic also alter alternate
and are area areas ascending assign at author before blank block
bottom by call cancel cd cf ch character characters clock-units close
cobol code code-set collating column comma communication comp comp-0
computational-0 configuration contains control control-area copy corr
corresponding count currency data date date-compiled date-written day
de debug-contents debug-item debug-line debug-name debug-sub-1
debug-sub-2 debug-sub-3 debugging decimal-point declaratives delete
delimited delimiter depending descending destination detail disable
display divide division down duplicates dynamic egi else emi enable
end end-of-page enter environment eop equal error esi every exception
exit extend fd file file-control filler final first footing for from
generate giving go greater group heading high-value high-values i-o
i-o-control identification if in index indexed indicate initial
initiate input input-output inspect installation into invalid just
justified key label last leading left length less limit limits linage
linage-counter line line-counter lines linkage lock low-value
low-values memory merge message mode modules more-labels multiple
multiply native negative next no not number numeric object-computer
occurs of off omitted on open optional or organization output overflow
page page-counter perform pf ph pic picture plus pointer position
positive printing procedure procedures proceed program program-id
queue quote quotes random rd read receive record records redefines
reel references relative release remainder removal renames replacing
report reporting reports rerun reserve return reversed rewind rewrite
rf rh right rounded run same sd search section security segment
segment-limit select send sentence separate sequence sequential set
sign size sort sort-merge source source-computer space spaces
special-names standard standard-1 start status stop string sub-queue-1
sub-queue-2 sub-queue-3 subtract sum super symbolic sync synchronized
tallying tape terminal terminate text than through thru time times to
top trailing type unit unstring until up upon usage use using value
values varying when with words working-storage write zero zeroes zeros
    """.split()
            self._lexer.setKeywords(0, keywords)
        return self._lexer

