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

class koTextLanguage(KoLanguageBase):
    name = "Text"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{CDFF6BC6-C21B-420c-9796-C90C37377FE6}"
    _reg_categories_ = [("komodo-language", name)]

    accessKey = 'e'
    primary = 1
    defaultExtension = ".txt"
    commentDelimiterInfo = { }
    sample = "Text files only have one style."

    def __init__(self):
        """In plain text we can't tell when a quote starts a sentence and
        when it means something else, so we simply never provide a close-quote.
        """
        KoLanguageBase.__init__(self)
        del self.matchingSoftChars["'"]
        del self.matchingSoftChars['"']

    def getEncodingWarning(self, encoding):
            return ''
        
    def guessIndentation(self, scimoz, tabWidth, defaultUsesTabs):
        guess = 0
        usesTabs = 0
        N = min(scimoz.lineCount, 100)
        for lineNo in range(N):
            lineStartPos = scimoz.positionFromLine(lineNo)
            lineEndPos = scimoz.getLineEndPosition(lineNo)
            line = scimoz.getTextRange(lineStartPos, lineEndPos)
            blackPos = len(line) - len(line.lstrip())
            if blackPos:
                guess = scimoz.getColumn(lineStartPos + blackPos)
                break
        if not guess:
            return 0, defaultUsesTabs
        # investigate whether tabs are used
        sawSufficientWhiteSpace = False
        for lineNo in range(lineNo, N):
            lineStartPos = scimoz.positionFromLine(lineNo)
            lineEndPos = scimoz.getLineEndPosition(lineNo)
            line = scimoz.getTextRange(lineStartPos, lineEndPos)
            blackPos = len(line) - len(line.lstrip())
            front = line[:blackPos]
            if '\t' in front or u'\t' in front:
                usesTabs = 1
                break
            elif scimoz.getColumn(lineStartPos + blackPos) >= tabWidth:
                sawSufficientWhiteSpace = True
        return guess, usesTabs or (not sawSufficientWhiteSpace and defaultUsesTabs)

    def get_commenter(self):
        if self._commenter is None:
            self._commenter = KoTextCommenterLanguageService()
        return self._commenter

class KoTextCommenterLanguageService(KoCommenterLanguageService):
    # Bug 90001 - make sure auto-comment on text files does nothing.
    def __init__(self):
        # Don't call the superclass
        pass

    def comment(self, scimoz):
        # Do nothing
        return
    
    def uncomment(self, scimoz):
        # Do nothing
        return
