#!python
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

import logging
from xpcom import components


log = logging.getLogger("KoLintDisplayer")
#log.setLevel(logging.DEBUG)

class KoLintDisplayer:
    _com_interfaces_ = [components.interfaces.koILintDisplayer]
    _reg_desc_ = "Komodo Lint Displayer"
    _reg_clsid_ = "{21648855-492F-11d4-AC24-0090273E6A60}"
    _reg_contractid_ = "@activestate.com/koLintDisplayer;1"
    DECORATOR_ERROR = components.interfaces.koILintResult.DECORATOR_ERROR
    DECORATOR_WARNING = components.interfaces.koILintResult.DECORATOR_WARNING

    def __init__(self):
        self._in_display = 0 # recursion protection.

    def _getIndicMask(self, scin):
        if scin.styleBits < 6:
            return scin.INDICS_MASK
        elif scin.styleBits == 6:
            return scin.INDIC1_MASK | scin.INDIC2_MASK
        else:
            return scin.INDIC2_MASK
        
    def displayClear(self, scin, numBits):
        # Clear all lint results from this scintilla.
        log.debug("displayClear(scin=%r, numBits=%r)", scin, numBits)
        mask = self._getIndicMask(scin)
        self._in_display = 1
        for i in [self.DECORATOR_ERROR, self.DECORATOR_WARNING]:
            scin.indicatorCurrent = i
            scin.indicatorClearRange(0, scin.length)
        try:
            prevEndStyled = scin.endStyled
            scin.startStyling(0, mask)
            scin.setStyling(scin.length, 0)
            if scin.endStyled != scin.length:
                log.error("displayClear() did not work (%d bytes were "
                          "styled)! Likely this is because this is a "
                          "re-entrant call to scintilla. displayClear() "
                          "must not be called within a scintilla OnModified "
                          "handler, or the like." % scin.endStyled)

            # ensure scin.endStyled = prevEndStyled so the lexer does not get
            # confused.
            scin.startStyling(prevEndStyled, mask)
            scin.setStyling(0,0)
            assert (prevEndStyled == scin.endStyled,
                    "unexpected end styled %d/%d!!"\
                    % (prevEndStyled, scin.endStyled))

            # This code is called by a timer, not as the text is styled for
            # painting so if we restyled anything currently on screen, we
            # need to repaint. no "clean" way to do this!
            scin.tabWidth = scin.tabWidth # this forces a repaint.
        finally:
            log.debug("leaving displayClear")
            self._in_display = 0
    
    def display(self, scin, lintResults, numBits, startPos, styleLen):
        log.debug("entering display")
        if self._in_display:
            log.debug("leaving display")
            return
        self._in_display = 1
        try:
            return self._display(scin, lintResults, numBits, startPos, styleLen);
        finally:
            log.debug("leaving display")
            self._in_display = 0

    def _display(self, scin, lintResults, numBits, startPos, styleLen):
        assert (lintResults is not None,
                "Should always have results to display")
        if scin.length == 0:
            return
        mask = self._getIndicMask(scin)

        # stash these for efficiency
        firstLine = scin.lineFromPosition(startPos)
        endLine = scin.lineFromPosition(startPos+styleLen)

        displayableResults = lintResults.getResultsInLineRange(firstLine+1,
                                                               endLine+1)

        offsetsAndValues = []
        for r in displayableResults:
            # sanity check lint results
            if ((r.columnStart >= 1 and r.columnEnd >= 1
                 and r.lineStart >= 1 and r.lineEnd >= 1)
                and
                (r.lineEnd > r.lineStart or
                 (r.lineEnd == r.lineStart and r.columnEnd >= r.columnStart))
               ):
                
                linepos = scin.positionFromLine(r.lineStart-1)
                offsetStart = scin.positionAtChar(linepos,r.columnStart-1)
                linepos = scin.positionFromLine(r.lineEnd-1)
                offsetEnd = scin.positionAtChar(linepos,r.columnEnd-1)

                if offsetEnd <= scin.length and offsetEnd >= offsetStart:
                    if r.lineEnd > scin.lineCount:
                        offsetEnd = scin.length
                    offsetsAndValues.append((offsetStart,
                                             offsetEnd - offsetStart,
                                             r.severity == r.SEV_ERROR and \
                                             self.DECORATOR_ERROR or \
                                             self.DECORATOR_WARNING))
                else:
                    log.error("Suspicious lint result discarded (offsetEnd "
                              "> scin.length or offsetStart > offsetEnd): "
                              "lineStart=%d, columnStart=%d, lineEnd=%d, "
                              "columnEnd=%d", r.lineStart, r.columnStart,
                              r.lineEnd, r.columnEnd)
            else:
                log.error("Suspicious lint result discarded (sanity "
                          "check failed): lineStart=%d, columnStart=%d, "
                          "lineEnd = %d, columnEnd = %d", r.lineStart,
                          r.columnStart, r.lineEnd, r.columnEnd)

        if not offsetsAndValues:
            return

        prevEndStyled = scin.endStyled

        for start, length, value in offsetsAndValues:
            if length > 0 and start + length < scin.length: # one last sanity check, as if that's not true it can cause a lockup
                #log.debug("Draw squiggle at pos[%d:%d], line %d:%d => %d:%d",
                #          start, start + length,
                #          scin.lineFromPosition(start),
                #          start - scin.positionFromLine(scin.lineFromPosition(start)),
                #          scin.lineFromPosition(start + length - 1),
                #          start + length - 1 - scin.positionFromLine(scin.lineFromPosition(start + length - 1)))
                scin.indicatorCurrent = value
                scin.indicatorFillRange(start, length)

        # This code is called by a timer, not as the text is styled for
        # painting so if we restyled anything currently on screen, we need
        # to repaint. no "clean" way to do this!
        scin.tabWidth = scin.tabWidth # this forces a repaint.
        assert (prevEndStyled == scin.endStyled,
                "unexpected end styled %d/%d!!"\
                % (prevEndStyled, scin.endStyled))

