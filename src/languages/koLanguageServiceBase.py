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

"""Base classes for languages and language services"""

import copy, re, types, eollib
import Queue
import logging

import scimozindent
from xpcom import components

#---- globals

log = logging.getLogger('koLanguageServiceBase')
#log.setLevel(logging.DEBUG)
indentlog = logging.getLogger('koLanguageServiceBase.indenting')
#indentlog.setLevel(logging.DEBUG)
log_styles = logging.getLogger('koLanguageServiceBase.styles')
#log_styles.setLevel(logging.DEBUG)

#sclog = logging.getLogger('koLanguageServiceBase.softchars')
#sclog.setLevel(logging.DEBUG)

sci_constants = components.interfaces.ISciMoz
numWordLists = 8 # from KEYWORDSET_MAX Scintilla.iface
isIdentRE = re.compile(r'\w', re.UNICODE)

def sendStatusMessage(msg, timeout=3000, highlight=1):
    observerSvc = components.classes["@mozilla.org/observer-service;1"]\
                  .getService(components.interfaces.nsIObserverService)
    sm = components.classes["@activestate.com/koStatusMessage;1"]\
         .createInstance(components.interfaces.koIStatusMessage)
    sm.category = "language_registry"
    sm.msg = msg
    sm.timeout = timeout     # 0 for no timeout, else a number of milliseconds
    sm.highlight = highlight # boolean, whether or not to highlight
    try:
        observerSvc.notifyObservers(sm, "status_message", None)
    except COMException, e:
        # do nothing: Notify sometimes raises an exception if (???)
        # receivers are not registered?
        pass

#---- language services implementations

class _QueueOfOne(Queue.Queue):
    """A thread-safe queue where an item always replaces any existing one.
    I.e. there will only ever be zero or one (the latest) items on the queue.
    """
    def _put(self, item):
        self.queue = [item]
    # The following are to ensure a *list* is being used as the internal
    # Queue data structure. Python 2.4 switched to using a deque.
    def _init(self, maxsize):
        self.maxsize = maxsize
        self.queue = []
    def _get(self):
        return self.queue.pop(0)

class KoLexerLanguageService:
    _com_interfaces_ = [components.interfaces.koILexerLanguageService]

    def __init__(self):
        self._lexer = None
        self._keywords = []
        for i in range(numWordLists):
            self._keywords.append([])
        self._properties = {}
        self.supportsFolding = 0

    def setLexer(self, sciLexer):
        self._lexer = sciLexer

    def setKeywords(self, keywordSet, keywords):
        assert keywordSet >= 0 and keywordSet < numWordLists
        self._keywords[keywordSet] = keywords

    def setProperty(self, property, value):
        self._properties[property] = value

    def setCurrent(self, scimoz):
        if self._lexer is None:
            scimoz.lexer = scimoz.SCLEX_NULL
        else:
            scimoz.lexer = self._lexer

        for i in range(len(self._keywords)):
            scimoz.setKeyWords(i, " ".join(self._keywords[i]))

        for prop in self._properties.keys():
            scimoz.setProperty(prop, self._properties[prop])

#---- base commenting language service classes

##
# @deprecated since Komodo 9.0
#
def getActualStyle(scimoz, pos):
    import warnings
    warnings.warn("getActualStyle is deprecated, use scimoz.getStyleAt(pos) instead",
                  category=DeprecationWarning)
    return scimoz.getStyleAt(pos)

class KoCommenterLanguageService:
    _com_interfaces_ = [components.interfaces.koICommenterLanguageService]
    DEBUG = 0 # set to true for debugging

    def __init__(self, delimiterInfo):
        """'delimiterInfo' is a dictionary describing how comments are
        specified in the given language. The used keys are as follows:
            line:   an ordered list of prefixes to remove for line 
                    uncommenting, the first one is prefixed for line
                    commenting
            block:  an ordered list of (prefix, suffix) pair tuples
                    for block commenting and uncommenting
        If 'line' is defined then the language supports line commenting --
        Python and Perl. If 'block' is defined then the language supports
        block commenting -- XML. A language may support both -- C++. Which
        style is applied depends on the current selection in scimoz.
        """
        self.delimiterInfo = delimiterInfo
        self._sysUtilsSvc = components.classes["@activestate.com/koSysUtils;1"].\
                getService(components.interfaces.koISysUtils)
        
    def _commentLinesInRectangleSelection(self, scimoz, delimiterInfo):
        actualSelStart = scimoz.anchor
        actualSelEnd = scimoz.currentPos
        if actualSelStart > actualSelEnd:
            (actualSelStart, actualSelEnd) = (actualSelEnd, actualSelStart)

        startLine = scimoz.lineFromPosition(actualSelStart)
        endLine = scimoz.lineFromPosition(actualSelEnd)
        scimoz.selectionMode = scimoz.SC_SEL_STREAM
        scimoz.beginUndoAction()
        currentPos = scimoz.currentPos
        finalSelStart = finalSelEnd = None
        if scimoz.anchor < currentPos:
            currentPos = scimoz.anchor
        try:
            posns = []
            for i in range(startLine, endLine + 1):
                selStart = scimoz.getLineSelStartPosition(i)
                selEnd = scimoz.getLineSelEndPosition(i)
                lineEndPos = scimoz.getLineEndPosition(i)
                if selEnd > lineEndPos:
                    selEnd = lineEndPos
                if selStart == -1 or selEnd == -1:
                    pass # skip these
                else:
                    if finalSelStart is None:
                        finalSelStart = selStart
                    finalSelEnd = selEnd
                    posns.append((selStart, selEnd))
            posns.reverse()
            prefix = delimiterInfo[0]
            if type(prefix) == types.TupleType:
                prefix, suffix = prefix
            else:
                suffix = ''
            for startPos, endPos in posns:
                if suffix:
                    scimoz.targetStart = endPos
                    scimoz.targetEnd = endPos
                    # Bug 101506 - 'len' only a problem if suffix contains
                    # high-bit characters, unlikely for a comment delimiter.
                    scimoz.replaceTarget(suffix)
                    finalSelEnd += len(suffix)
                if prefix:
                    scimoz.targetStart = startPos
                    scimoz.targetEnd = startPos
                    # Bug 101506 - 'len' only a problem if prefix contains
                    # high-bit characters, unlikely for a comment delimiter.
                    scimoz.replaceTarget(prefix)
                    finalSelEnd += len(prefix)
        finally:
            scimoz.endUndoAction()
            self._adjustNewRectangularSelection(scimoz, finalSelStart, finalSelEnd,
                                                currentPos, startLine)
            
    def _adjustNewRectangularSelection(self, scimoz, finalSelStart, finalSelEnd,
                                       currentPos, startLine):
        if finalSelStart is not None and finalSelEnd is not None:
            scimoz.selectionMode = scimoz.SC_SEL_RECTANGLE
            scimoz.rectangularSelectionCaret = finalSelStart
            scimoz.rectangularSelectionAnchor = finalSelEnd
        else:
            scimoz.selectionMode = scimoz.SC_SEL_STREAM
            if currentPos != finalSelStart:
                # Give up, move to start of that line
                currentPos = scimoz.positionFromLine(startLine)
            scimoz.currentPos = scimoz.anchor = currentPos

    def _commentLines(self, scimoz, startIndex, endIndex):
        """Comment the indexed lines."""
        if scimoz.selectionMode == scimoz.SC_SEL_RECTANGLE:
            self._commentLinesInRectangleSelection(scimoz, self.delimiterInfo["line"])
            return
        if self.DEBUG:
            print "'line' autocomment: %s-%s" % (startIndex, endIndex)
        xOffset = scimoz.xOffset
        selStart = scimoz.selectionStart
        selEnd = scimoz.selectionEnd
        anchor = scimoz.anchor
        currentPos = scimoz.currentPos
        anchorFirst = (anchor <= currentPos)
        if anchorFirst:
            startCursorColumn = scimoz.getColumn(anchor)
            endCursorColumn = scimoz.getColumn(currentPos)
        else:
            startCursorColumn = scimoz.getColumn(currentPos)
            endCursorColumn = scimoz.getColumn(anchor)
        # Handle line selection mode (as used by vi).
        if scimoz.selectionMode == scimoz.SC_SEL_LINES:
            startLineNo = scimoz.lineFromPosition(selStart)
            endLineNo = scimoz.lineFromPosition(selEnd)
            selStart = scimoz.getLineSelStartPosition(startLineNo)
            selEnd = scimoz.getLineSelEndPosition(endLineNo)
        if selStart != selEnd and scimoz.getColumn(selEnd) == 0:
            # if at the start of a line, work from the end of the previous
            # line.  Subtracting 1 is safe because the endIndex
            # follows a newline character.
            workingEndIndex = scimoz.getLineEndPosition(
                scimoz.lineFromPosition(endIndex) - 1)
        else:
            workingEndIndex = endIndex
        original = scimoz.getTextRange(startIndex, workingEndIndex)
        prefix = self.delimiterInfo["line"][0]
        if type(prefix) == types.TupleType:
            prefix, suffix = prefix
        else:
            suffix = ''
        # Update the column offsets to include the comment prefix.
        startCursorColumn += len(prefix)
        endCursorColumn += len(prefix)
        if self.DEBUG:
            print "original text: %r" % original

        # For easier line terminator handling turn this:
        #      original = 'asdf\nqwer\r\nzxcv\rasdf'
        # in this:
        #      originalLines = [('asdf', '\n'), ('qwer', '\r\n'),
        #                       ('zxcv', '\r'), ('asdf', '')]
        lines = re.split("(\r\n|\n|\r)", original)
        originalLines = []
        for i in range(0, len(lines), 2):
            try:
                originalLines.append( (lines[i], lines[i+1]) )
            except IndexError:
                originalLines.append( (lines[i], '') )
        if self.DEBUG:
            import pprint
            print "original text (as lines for easier processing):"
            pprint.pprint(originalLines)

        # Find the maximum common whitespace offset of all the lines (comment
        # delimiters will be indented to this level). Skip blank lines
        # when determining this.
        linesToGetIndent = [line[0] for line in originalLines if line[0].strip()]
        indentRe = re.compile("^(?P<indent>\s+).*$")
        if len(linesToGetIndent) > 0:
            indentMatch = indentRe.search(linesToGetIndent[0])
            if indentMatch:
                commonIndent = indentMatch.group("indent")
            else:
                commonIndent = ""
        else:
            commonIndent = ""
        for line in linesToGetIndent:
            indentMatch = indentRe.search(line)
            if indentMatch:
                indent = indentMatch.group("indent")
                while commonIndent:
                    if indent.startswith(commonIndent):
                        break
                    commonIndent = commonIndent[:-1]
                else:
                    break
            else:
                commonIndent = ""
                break
        if self.DEBUG:
            print "common indent: %r" % commonIndent

        # make the replacments
        replacementLines = []
        for line in originalLines:
            r = commonIndent + prefix + line[0][len(commonIndent):] \
                + suffix + line[1]
            if self.DEBUG:
                print "%r -> %r" % (line[0], r)
            replacementLines.append(r)
        replacement = "".join(replacementLines)
        #log.debug("line comment: '%s' -> '%s'" % (original, replacement))

        if original != replacement:
            scimoz.hideSelection(1)
            startIndexLine = scimoz.lineFromPosition(startIndex)
            endIndexLine = scimoz.lineFromPosition(endIndex)
            selStartColumn = scimoz.getColumn(selStart)

            # apply the commenting change
            scimoz.targetStart = startIndex
            scimoz.targetEnd = workingEndIndex
            if self.DEBUG:
                print "replacement length: naive=%r encoding-aware=%r"\
                      % (len(replacement),
                         self._sysUtilsSvc.byteLength(replacement))
            scimoz.replaceTarget(replacement)

            # restore the selection and cursor position
            if scimoz.selectionMode == scimoz.SC_SEL_LINES:
                # For line selection mode, restore the cursor positions
                # according to the column and line number they started at.
                startPos = scimoz.findColumn(startLineNo, startCursorColumn)
                endPos = scimoz.findColumn(endLineNo, endCursorColumn)
                if anchorFirst:
                    scimoz.anchor = startPos
                    scimoz.currentPos = endPos
                else:
                    scimoz.anchor = endPos
                    scimoz.currentPos = startPos
            elif selStart != selEnd:
                scimoz.selectionStart = scimoz.positionFromLine(startIndexLine)
                if endIndex == workingEndIndex:
                    scimoz.selectionEnd = scimoz.getLineEndPosition(
                        endIndexLine)
                else:
                    scimoz.selectionEnd = scimoz.positionFromLine(
                        endIndexLine)
            else:
                if selStartColumn <= len(commonIndent):
                    scimoz.selectionStart = selStart
                    scimoz.selectionEnd = selEnd
                else:
                    scimoz.selectionStart = selStart + len(prefix)
                    scimoz.selectionEnd = selEnd + len(prefix)
            scimoz.hideSelection(0)
            scimoz.xOffset = xOffset

    def _commentBlock(self, scimoz, startIndex, endIndex):
        """Comment the indexed block."""
        if scimoz.selectionMode == scimoz.SC_SEL_RECTANGLE:
            self._commentLinesInRectangleSelection(scimoz, self.delimiterInfo["block"])
            return
        if self.DEBUG:
            print "'block' autocomment: %s-%s" % (startIndex, endIndex)
        xOffset = scimoz.xOffset
        original = scimoz.getTextRange(startIndex, endIndex)
        prefix, suffix = self.delimiterInfo["block"][0]

        replacement = prefix + original + suffix
        #log.debug("block comment: '%s' -> '%s'" % (original, replacement))

        if original != replacement:
            scimoz.hideSelection(1)
            selStart = scimoz.selectionStart
            selEnd = scimoz.selectionEnd

            # apply the commenting change
            scimoz.targetStart = startIndex
            scimoz.targetEnd = endIndex
            scimoz.replaceTarget(replacement)

            # restore the selection and cursor position
            scimoz.selectionStart = selStart + len(prefix)
            scimoz.selectionEnd = selEnd + len(prefix)
            scimoz.hideSelection(0)
            scimoz.xOffset = xOffset

    def _uncommentLinesInRectangleSelection(self, scimoz, uncommenter):
        actualSelStart = scimoz.anchor
        actualSelEnd = scimoz.currentPos
        if actualSelStart > actualSelEnd:
            (actualSelStart, actualSelEnd) = (actualSelEnd, actualSelStart)
        startLine = scimoz.lineFromPosition(actualSelStart)
        endLine = scimoz.lineFromPosition(actualSelEnd)
        scimoz.selectionMode = scimoz.SC_SEL_STREAM
        scimoz.beginUndoAction()
        currentPos = scimoz.currentPos
        if scimoz.anchor < currentPos:
            currentPos = scimoz.anchor
        try:
            posns = []
            finalSelStart = finalSelEnd = None
            for i in range(startLine, endLine + 1):
                selStart = scimoz.getLineSelStartPosition(i)
                selEnd = scimoz.getLineSelEndPosition(i)
                if selStart == -1 or selEnd == -1:
                    pass # Do nothing on a blank line.
                else:
                    if finalSelStart is None:
                        finalSelStart = selStart
                    finalSelEnd = selEnd
                    posns.append((selStart, selEnd))
            posns.reverse()
            for startPos, endPos in posns:
                # All uncommenters return a non-positive number, giving
                # the change in the size of the document
                finalSelEnd += uncommenter(scimoz, startPos, endPos)
        finally:
            scimoz.endUndoAction()
            self._adjustNewRectangularSelection(scimoz, finalSelStart, finalSelEnd,
                                                currentPos, startLine)

    def _uncommentLines(self, scimoz, startIndex, endIndex):
        if scimoz.selectionMode == scimoz.SC_SEL_RECTANGLE:
            self._uncommentLinesInRectangleSelection(scimoz, self._uncommentLines)
            return
        xOffset = scimoz.xOffset
        selStart = scimoz.selectionStart
        selEnd = scimoz.selectionEnd
        anchor = scimoz.anchor
        currentPos = scimoz.currentPos
        anchorFirst = (anchor <= currentPos)
        if anchorFirst:
            startCursorColumn = scimoz.getColumn(anchor)
            endCursorColumn = scimoz.getColumn(currentPos)
        else:
            startCursorColumn = scimoz.getColumn(currentPos)
            endCursorColumn = scimoz.getColumn(anchor)
        # Handle line selection mode (as used by vi).
        if scimoz.selectionMode == scimoz.SC_SEL_LINES:
            startLineNo = scimoz.lineFromPosition(selStart)
            endLineNo = scimoz.lineFromPosition(selEnd)
            selStart = scimoz.getLineSelStartPosition(startLineNo)
            selEnd = scimoz.getLineSelEndPosition(endLineNo)
        if selStart != selEnd and scimoz.getColumn(selEnd) == 0:
            # if at the start of a line, work from the end of the previous
            # line
            # See comment on multi-byte safeness in self._commentLines()
            workingEndIndex = scimoz.getLineEndPosition(
                scimoz.lineFromPosition(endIndex) - 1)
        else:
            workingEndIndex = endIndex
        original = scimoz.getTextRange(startIndex, workingEndIndex)
        prefixes = self.delimiterInfo["line"]

        # For easier line terminator handling turn this:
        #      original = 'asdf\nqwer\r\nzxcv\rasdf'
        # in this:
        #      originalLines = [('asdf', '\n'), ('qwer', '\r\n'),
        #                       ('zxcv', '\r'), ('asdf', '')]
        lines = re.split("(\r\n|\n|\r)", original)
        originalLines = []
        for i in range(0, len(lines), 2):
            try:
                originalLines.append( (lines[i], lines[i+1]) )
            except IndexError:
                originalLines.append( (lines[i], '') )

        replacementLines = []
        lastIndent = lastPrefix = ""  # for restoring the position below
        firstLine = True
        for line in originalLines:
            for prefix in prefixes:
                if type(prefix) == types.TupleType: # block comments
                    prefix, suffix = prefix
                    commentRe = re.compile("^(\s*)(%s)(.*)(%s)(\s*)$"
                                           % (re.escape(prefix),
                                              re.escape(suffix)))
                else: # line comments
                    suffix = None
                    commentRe = re.compile("^(\s*)(%s)(.*)()()$" % re.escape(prefix))
                commentMatch = commentRe.search(line[0])
                if commentMatch:
                    replacementLines.append(commentMatch.group(1) +
                                            commentMatch.group(3) +
                                            commentMatch.group(5) +
                                            line[1])
                    lastIndent = commentMatch.group(1)
                    lastPrefix = commentMatch.group(2)
                    if firstLine:
                        # Update start cursor column to remove the prefix.
                        startCursorColumn -= len(lastPrefix)
                    break
            else:
                replacementLines.append(line[0] + line[1])
            firstLine = False
        # Update end cursor column to remove the prefix.
        endCursorColumn -= len(lastPrefix)
        replacement = "".join(replacementLines)
        #log.debug("line uncomment: '%s' -> '%s'" % (original, replacement))

        if original != replacement:
            scimoz.hideSelection(1)
            startIndexLine = scimoz.lineFromPosition(startIndex)
            endIndexLine = scimoz.lineFromPosition(endIndex)
            selStartColumn = scimoz.getColumn(selStart)

            # apply the commenting change
            scimoz.targetStart = startIndex
            scimoz.targetEnd = workingEndIndex
            scimoz.replaceTarget(replacement)
            delta = len(replacement) - (workingEndIndex - startIndex)

            # restore the selection and cursor position
            if scimoz.selectionMode == scimoz.SC_SEL_LINES:
                # For line selection mode, restore the cursor positions
                # according to the column and line number they started at.
                startPos = scimoz.findColumn(startLineNo, startCursorColumn)
                endPos = scimoz.findColumn(endLineNo, endCursorColumn)
                if anchorFirst:
                    scimoz.anchor = startPos
                    scimoz.currentPos = endPos
                else:
                    scimoz.anchor = endPos
                    scimoz.currentPos = startPos
            elif selStart != selEnd:
                scimoz.selectionStart = scimoz.positionFromLine(startIndexLine)
                if endIndex == workingEndIndex:
                    scimoz.selectionEnd = scimoz.getLineEndPosition(
                        endIndexLine)
                else:
                    scimoz.selectionEnd = scimoz.positionFromLine(
                        endIndexLine)
            else:
                if selStartColumn <= len(lastIndent):
                    scimoz.selectionStart = selStart
                    scimoz.selectionEnd = selEnd
                else:
                    scimoz.selectionStart = selStart - len(lastPrefix)
                    scimoz.selectionEnd = selEnd - len(lastPrefix)
            scimoz.hideSelection(0)
            scimoz.xOffset = xOffset
        else:
            delta = 0
        return delta
            
    def _getSelectionDelimiterPositions(self, scimoz, startIndex, endIndex,
                                        prefix, suffix):
        # Unicode: assume delimiters don't contain multi-byte characters
        p = None
        # First look to see if the selection starts immediately after the prefix
        if startIndex >= len(prefix):
            pStart, pEnd = startIndex-len(prefix), startIndex
            p = scimoz.getTextRange(pStart, pEnd)
            if p != prefix:
                p = None
        if p is None:
            # Does the selection start with the prefix?
            if startIndex + len(prefix) < endIndex:
                pStart, pEnd = startIndex, startIndex + len(prefix)
                p = scimoz.getTextRange(pStart, pEnd)
                if p != prefix:
                    p = None
        if p is None:
            return None
        # Same with the suffix.  Note that we handle
        # /*|abc|*/   |/*abc*/|  |/*abc|*/   /*|abc*/|
        # where '|' marks the selection points
            
        s = None
        if endIndex < scimoz.length - len(suffix):
            sStart, sEnd = endIndex, endIndex+len(suffix)
            s = scimoz.getTextRange(sStart, sEnd)
            if s != suffix:
                s = None
        if s is None and pEnd <= endIndex - len(suffix):
            # Try finding the suffix at the end of the selection
            sStart, sEnd = endIndex - len(suffix), endIndex
            s = scimoz.getTextRange(sStart, sEnd)
            if s != suffix:
                s = None
        if s is None:
            return None
        return pStart, pEnd, sStart, sEnd

    def _uncommentBlock(self, scimoz, startIndex, endIndex):
        if scimoz.selectionMode == scimoz.SC_SEL_RECTANGLE:
            self._uncommentLinesInRectangleSelection(scimoz, self._uncommentBlock)
            return
        delimiters = self.delimiterInfo["block"]

        delta = 0
        for prefix, suffix in delimiters:
            coordinates = self._getSelectionDelimiterPositions(scimoz,
                                startIndex, endIndex, prefix, suffix)
            if coordinates is None:
                continue
            pStart, pEnd, sStart, sEnd = coordinates
            xOffset = scimoz.xOffset
            selStart = scimoz.selectionStart
            selEnd = scimoz.selectionEnd
            scimoz.hideSelection(1)
            # remove the existing prefix and suffix (suffix first to get
            # indices correct)
            scimoz.beginUndoAction()
            try:
                scimoz.targetStart = sStart
                scimoz.targetEnd = sEnd
                scimoz.replaceTarget(0, "")
                scimoz.targetStart = pStart
                scimoz.targetEnd = pEnd
                scimoz.replaceTarget(0, "")
                # delta should be negative
                delta += (sStart - sEnd) + (pStart - pEnd)
            finally:
                scimoz.endUndoAction()
            # restore the selection and cursor position
            scimoz.selectionStart = pStart
            scimoz.selectionEnd = sStart - len(prefix)
            scimoz.hideSelection(0)
            scimoz.xOffset = xOffset
            break
        return delta

    _val_sp = ord(' ')
    _val_tab = ord('\t')
    def _inLeadingWhiteSpace(self, scimoz, pos, lineStartPos, lineEndPos):
        firstVisiblePosn = lineStartPos
        while firstVisiblePosn < lineEndPos:
            ch = scimoz.getCharAt(firstVisiblePosn)
            if ch != self._val_sp and ch != self._val_tab:
                break
            # No need to use positionAfter, as we're looking for ascii chars
            firstVisiblePosn += 1
        if firstVisiblePosn == lineEndPos:
            return True # It's all whitespace
        else:
            return lineStartPos <= pos <= firstVisiblePosn
    
    def _inTrailingWhiteSpace(self, scimoz, pos, lineStartPos, lineEndPos):
        lastVisiblePosn = lineEndPos - 1
        while lastVisiblePosn >= lineStartPos:
            ch = scimoz.getCharAt(lastVisiblePosn)
            if ch != self._val_sp and ch != self._val_tab:
                break
            # No need to use positionAfter, as we're looking for ascii chars
            lastVisiblePosn -= 1
        if lastVisiblePosn < lineStartPos:
            return True  # It's all white space
        else:
            return lastVisiblePosn < pos <= lineEndPos

    def _inOuterWhiteSpace(self, scimoz, pos, lineNo):
        lineStartPosn = scimoz.positionFromLine(lineNo)
        lineEndPosition = scimoz.getLineEndPosition(lineNo)
        return (self._inLeadingWhiteSpace(scimoz, pos, lineStartPosn, lineEndPosition)
                or self._inTrailingWhiteSpace(scimoz, pos, lineStartPosn, lineEndPosition))

    def _determineMethodAndDispatch(self, scimoz, workers, commenting=True):
        selStart = scimoz.selectionStart
        selEnd = scimoz.selectionEnd
        if not commenting and selEnd > selStart:
            # Don't bother looking at line positions yet -- if the selection
            # starts and ends with a particular delimiter pair, use it
            for prefix, suffix in self.delimiterInfo.get("block", []):
                coordinates = self._getSelectionDelimiterPositions(scimoz, selStart, selEnd,
                                        prefix, suffix)
                if coordinates:
                    workers["block"](scimoz, selStart, selEnd)
                    return
                
        selStartLine = scimoz.lineFromPosition(selStart)
        selEndLine = scimoz.lineFromPosition(selEnd)
        # Handle line selection mode (as used by vi).
        if scimoz.selectionMode == scimoz.SC_SEL_LINES:
            selStart = scimoz.getLineSelStartPosition(selStartLine)
            selEnd = scimoz.getLineSelEndPosition(selEndLine)                   

        # determine preferred commenting method (if the selection starts or ends
        # _within_ a line (ignoring leading and trailing white-space)
        # then block commenting is preferred)
        #
        # Otherwise go with block commenting whenever possible.
        if (scimoz.selectionMode == scimoz.SC_SEL_LINES
            or selStart == selEnd
            or scimoz.selectionMode == scimoz.SC_SEL_RECTANGLE):
            preferBlockCommenting = 0
        elif self._inOuterWhiteSpace(scimoz, selStart, selStartLine)\
              and self._inOuterWhiteSpace(scimoz, selEnd, selEndLine):
            preferBlockCommenting = 0
        else:
            preferBlockCommenting = 1

        if self.DEBUG:
            print "prefer block commenting? %s"\
                  % (preferBlockCommenting and "yes" or "no")
            print "comment delimiter info: %s" % self.delimiterInfo

        # do the commenting/uncommenting
        if (self.delimiterInfo.get("block", None)
            and (preferBlockCommenting
                 or (not self.delimiterInfo.has_key("line")
                     and selStart < selEnd))):
            workers["block"](scimoz, selStart, selEnd)
        elif self.delimiterInfo.get("line", None):
            textStart = scimoz.positionFromLine(selStartLine)
            if selStart != selEnd and scimoz.getColumn(selEnd) == 0:
                # if at the start of a line, then do NOT include that line
                textEnd = selEnd
            else:
                textEnd = scimoz.getLineEndPosition(selEndLine)
            workers["line"](scimoz, textStart, textEnd)
        elif self.delimiterInfo.get("block", None):
            # This lang only has block delimiters but the selection is such
            # that it looks like line commenting should be done. Sneak
            # the block delimiter tuple in as line delimiters.
            self.delimiterInfo["line"] = self.delimiterInfo["block"]
            textStart = scimoz.positionFromLine(selStartLine)
            if selStart != selEnd and scimoz.getColumn(selEnd) == 0:
                # if at the start of a line, then do NOT include that line
                textEnd = selEnd
            else:
                textEnd = scimoz.getLineEndPosition(selEndLine)
            workers["line"](scimoz, textStart, textEnd)
        else:
            log.warn("Could not comment code because no appropriate "\
                     "comment delimiter info exists for the current "\
                     "language.\n")

    def comment(self, scimoz):
        """Comment the current line or current selection."""
        commenters = {
            "line"  : self._commentLines,
            "block" : self._commentBlock
        }
        if self.DEBUG:
            import sciutils
            print
            sciutils._printBanner("autocomment (before)")
            sciutils._printBufferContext(
                0, # offset
                scimoz.getStyledText(0, scimoz.textLength), # styledText
                scimoz.currentPos, # position
            )
        self._determineMethodAndDispatch(scimoz, commenters, commenting=True)
        if self.DEBUG:
            sciutils._printBanner("autocomment (after)")
            sciutils._printBufferContext(
                0, # offset
                scimoz.getStyledText(0, scimoz.textLength), # styledText
                scimoz.currentPos, # position
            )

    def uncomment(self, scimoz):
        """Uncomment the current line or current selection."""
        uncommenters = {
            "line"  : self._uncommentLines,
            "block" : self._uncommentBlock
        }
        self._determineMethodAndDispatch(scimoz, uncommenters, commenting=False)



# A simple container class for managing sets of language-specific 
# styles.  Allow quick switching between UDL-based and pure languages.

class koLangSvcStyleInfo_Base:
    def clone(self, **attrs):
        cobj = copy.copy(self)
        for k in attrs.keys():
            setattr(cobj, k, attrs[k])
        return cobj
    
    def update(self, **attrs):
        for k in attrs.keys():
            setattr(self, k, attrs[k])


# the following four (four? --TM) are used by the getBraceIndentStyle call
#XXX David: these need better documentation --TM
# All of the following may be overriden by the language implementation

class koLangSvcStyleInfo_Default(koLangSvcStyleInfo_Base):
    def __init__(self):
        # Should be overriden by the lang-specific
        # implementation if that lang has block
        # comments.
        self._indent_open_styles = [10,]
        self._indent_close_styles = [10,]
        self._lineup_close_styles = [10,]
        self._lineup_styles = [10,]
        # These are all automatically calculated from styles.StateMap
        # for pure languages, overridden by UDL
            
        # Logically group some language-specific styles. It is useful in
        # some editor functionality to, for example, skip over comments or
        # strings.
    
        # Put in all values as empty tuples or None, and override
        self._block_comment_styles = []
        self._comment_styles = []
        self._datasection_styles = []
        self._default_styles = []
        self._ignorable_styles = []
        self._regex_styles = []
        self._indent_styles = []
        self._keyword_styles = []
        self._multiline_styles = []
        self._modified_keyword_styles = []
        self._number_styles = []
        self._string_styles = []
        self._variable_styles = []

class koLangSvcStyleInfo(koLangSvcStyleInfo_Default):
    def __init__(self, **attrs):
        koLangSvcStyleInfo_Default.__init__(self)
        for k in attrs.keys():
            setattr(self, k, attrs[k])

_softCharDecorator = components.interfaces.koILintResult.DECORATOR_SOFT_CHAR

# Used for line-comment auto-indentation
_COMMENT_STYLE_RUN_CODE = 1
_COMMENT_STYLE_RUN_SPACE = 2
_COMMENT_STYLE_RUN_SPACE_COMMENT = 3

class _NextLineException(Exception):
    pass

class FastCharData(object):
    """Used to determine when a termination character should move
    to the end of a run of soft characters, as long as that run
    ends at the end of the line.
    Format:
    FastCharData(trigger_char, # only one allowed, the char to move to the end
                 style_list, # [array of allowed styles]
                  # array for both UDL and standard
                 skippable_chars, #{hash of style : list of characters to skip},
                for_check # boolean
                )
    The idea is that if a fast_character is typed, and its style is one of
    the styles we're interested in, we pick it up and move it to the right
    of a contiguous sequence of soft characters where the character's style
    is in the hash, and the character's byte value is in that hash's list.

    The 'for_check' option prevents moving ';' after
    for(<init>;[)]
    and 
    for(<init>; <cond>;[)]
    but allows it to move with the unlikely
    for(<init>; <cond>; <postAction>;[)]
    """
    def __init__(self, trigger_char, style_list,
                 skippable_chars_by_style, for_check=False):
        self.trigger_char = trigger_char
        self.style_list = style_list
        # pairs hashes styles to strings
        # convert the strings to a list of ord(c)
        #if sci_constants.SCE_UDL_SSL_OPERATOR in style_list:
        #    log.debug("FastCharData.__init__: skippable_chars_by_style:%s",
        #              skippable_chars_by_style)
        self.skippable_chars = dict([(closeCharStyle,
                                       [ord(c) for c in closeChars])
                                      for (closeCharStyle, closeChars)
                                      in skippable_chars_by_style.items()])
        self.for_check = for_check
        
    _ends_with_for_re = re.compile(r'\bfor\s*\Z')
    def finishingForStmt(self, scimoz, pos):
        """
        Return True only if the current close-paren has a matching
        open-paren that follows the 'for' keyword.

        If we're doing this here, we're in a language where 'for'
        is a reserved keyword, so we don't need to check the style.
        """
        openPos = scimoz.braceMatch(pos)
        if openPos == scimoz.INVALID_POSITION:
            return False, openPos
        lineStartPos = scimoz.positionFromLine(scimoz.lineFromPosition(openPos))
        leadingText = scimoz.getTextRange(lineStartPos, openPos)
        m = self._ends_with_for_re.search(leadingText)
        if m:
            return True, lineStartPos + m.start()
        return False, openPos
    
    def sawAllForHeaderSemiColons(self, scimoz, forStartPos, pos, opStyle):
        assert forStartPos < pos
        charsAndStyles = scimoz.getStyledText(forStartPos + 3, pos)
        # Keep only the operator-styled characters between the end of
        # the 'for' and the current semi-colon.  Note that we count
        # both the opening '(' and the current ';'.
        opChars = [charsAndStyles[2 * i]
                   for i, style in enumerate(charsAndStyles[1::2])
                   if ord(style) == opStyle]
        nestingLevel = 0
        numSemiColons = 0
        # Have we seen two semi-colons at the top-level?
        # Note the top-level should be at nestingLevel = 1
        # because we're starting at "for ("
        for ch in opChars:
            if ch in ("(", "[", "{"):
                nestingLevel += 1
            elif ch in ("}", "]", ")") and nestingLevel > 0:
                nestingLevel -= 1
            elif nestingLevel == 1 and ch == ";":
                numSemiColons += 1
                if numSemiColons == 3:
                    return True
        return False
 
    def moveCharThroughSoftChars(self, ch, scimoz):
        """
        If the language has defined a FastCharData structure, move the character
        we typed to the end of the appropriate sequence of soft characters,
        and return True.  Otherwise return None.
        """
        currentPos = scimoz.currentPos # char to right of trigger-char
        currentLineNo = scimoz.lineFromPosition(currentPos)
        lineEndPos = scimoz.getLineEndPosition(currentLineNo)
        # If we have some non-soft characters between the current pos
        # and eol, don't move the character
        pos = currentPos
        while pos < lineEndPos:
            if not scimoz.indicatorValueAt(_softCharDecorator, pos):
                return False
            pos = scimoz.positionAfter(pos)
        
        opStyle = scimoz.getStyleAt(currentPos - 1)
        if opStyle not in self.style_list:
            return False
        startOfRange_Left = endOfRange_Left = currentPos - 1
        pos = currentPos
        allowed_pairs = self.skippable_chars
        while pos < lineEndPos:
            style = scimoz.getStyleAt(pos)
            chars = allowed_pairs.get(style)
            if chars is None:
                break
            if scimoz.getCharAt(pos) not in chars:
                break
            if self.for_check and scimoz.getCharAt(pos) == ord(")"):
                inForStmt, forStartPos = self.finishingForStmt(scimoz, pos)
                if inForStmt:
                    # Check to see if we've completed it
                    if not self.sawAllForHeaderSemiColons(scimoz, forStartPos, pos, opStyle):
                        break
            endOfRange_Left = pos
            pos = pos + 1 # ascii-safe, as we work with byte values here.
        if startOfRange_Left < endOfRange_Left:
            scimoz.beginUndoAction()
            try:
                scimoz.indicatorCurrent = _softCharDecorator
                scimoz.indicatorClearRange(startOfRange_Left + 1,
                                           endOfRange_Left - startOfRange_Left)
                scimoz.insertText(endOfRange_Left + 1, ch)
                scimoz.targetStart = currentPos - 1
                scimoz.targetEnd = currentPos
                scimoz.replaceTarget(0, "")
                scimoz.gotoPos(endOfRange_Left + 1)
            finally:
                scimoz.endUndoAction()
            return True


class KoLanguageBase:
    _com_interfaces_ = [components.interfaces.koILanguage,
    			components.interfaces.nsIObserver]

    _lexer = None
    _style = None
    _completer = None
    _commenter = None
    _codeintelcompleter = None
    _interpreter = None

    sample = '' # used in the fonts & colors dialog
    downloadURL = '' # location to download the language
    searchURL = '' # used by the language help system
    variableIndicators = ''
    supportsSmartIndent = "text"

    # Override in subclass with an extension (string) to provide a fallback
    # file association for the language. The extension string must include the
    # leading period, e.g. ".py".
    defaultExtension = None

    # Override in subclass to provide additional file associations (on top of
    # the defaultExtension above). e.g. ["*.python"]
    extraFileAssociations = []

    # use something as a default.  Not the best, but the most we can do until
    # all scintilla lexers have io styles
    styleStdin = 0
    styleStdout = 0
    styleStderr = 0

    # This is like a table to drive indentation calculation by the
    # editor.  Style info needs to be wrapped in a koLangSvcStyleInfo
    # block to allow for multi-language buffers.

    _indent_chars = "{}"
    _indent_open_chars = "{"
    _indent_close_chars = "}"
    _lineup_chars = "()[]{}"
    _lineup_open_chars = "(["
    _lineup_close_chars = ")]"
    _dedent_chars = ""

    # These should be overriden by the language implementation
    # "statements" should have been "keywords"
    # These mark what should be the last line in the block.
    # They don't work for Perl-like languages where you can say
    #     return if <test>
    _dedenting_statements = []  # eg: break, continue, return

    # These are used in both brace- and keyword-based languages
    _indenting_statements = []

    _stateMap = {}
    
    #XXX The list of block comment styles is only being used (currently)
    #    is auto-indent (and perhaps reflow) stuff. This should be removed
    #    because you cannot reliably use the current character style to
    #    differentiate between being in a line or block comment (because
    #    there are shared styles between the two).

    commentDelimiterInfo = {}
    
    _svcdict = {
        components.interfaces.koILexerLanguageService: 'get_lexer',
        components.interfaces.koICompletionLanguageService: 'get_completer',
        components.interfaces.koICommenterLanguageService: 'get_commenter',
        components.interfaces.koIAppInfoEx: 'get_interpreter',
    }
    namedBlockRE = ''
    namedBlockDescription = ''

    modeNames = []
    shebangPatterns = []
    primary = 0
    internal = 0
    accessKey = ''

    # used in determination of language types.  The language service should
    # specify what publid/system id's and namespaces match the language
    # either the doctype declaration, or the primary namespace of the root
    # element will be used to determine the language name
    publicIdList = []
    systemIdList = []
    namespaces = []
    prefset = None
    
    isHTMLLanguage = False

    ##
    # Deprecated scimoz mask helpers.
    # @deprecated since Komodo 9.0
    @property
    def styleBits(self):
        import warnings
        warnings.warn("koILanguage.styleBits are deprecated - no longer needed",
                      category=DeprecationWarning)
        return 32
    @property
    def stylingBitsMask(self):
        import warnings
        warnings.warn("koILanguage.stylingBitsMask are deprecated - no longer needed",
                      category=DeprecationWarning)
        return (1 << self.styleBits) - 1
    @property
    def indicatorBits(self):
        import warnings
        warnings.warn("koILanguage.indicatorBits are deprecated - no longer needed",
                      category=DeprecationWarning)
        return 2


    def __init__(self):
        if not KoLanguageBase.prefset:
            KoLanguageBase.prefset = components.classes["@activestate.com/koPrefService;1"]\
                        .getService(components.interfaces.koIPrefService).prefs
    
        # we define stateMaps for some languages in the styles module,
        # others we define in the language module itself
        import styles
        if not self._stateMap and self.name in styles.StateMap:
            self._stateMap = styles.StateMap[self.name]
        else:
            # Make a copy of the statemap to be used by the scheme colorization
            # routines. If this is not a copy, then some languages will not
            # colorize correctly (see bug 83023).
            styles.StateMap[self.name] = self._stateMap.copy()
            # Add the shared styles (linenumbers, badbrace, etc...) - bug 83023.
            styles.addSharedStyles(styles.StateMap[self.name])

        #log_styles.debug("**************** Setting string-styles etc. for language %s", self.name)
        
        self._style_info = koLangSvcStyleInfo_Default()
        
        string_style_names = list(self._stateMap.get('strings', []))\
                             + list(self._stateMap.get('stringeol', []))
        string_styles = [getattr(components.interfaces.ISciMoz, style_name)
                         for style_name in string_style_names]
        self._style_info._string_styles = string_styles
            
        comment_style_names = list(self._stateMap.get('comments', []))\
                              + list(self._stateMap.get('here documents', []))
        comment_styles = [getattr(components.interfaces.ISciMoz, style_name)
                          for style_name in comment_style_names]
        self._style_info._comment_styles = comment_styles

        number_style_names = self._stateMap.get('numbers', [])
        number_styles = [getattr(components.interfaces.ISciMoz, style_name)
                         for style_name in number_style_names]
        self._style_info._number_styles = number_styles
            
        variable_style_names = self._stateMap.get('variables', [])
        variable_styles = [getattr(components.interfaces.ISciMoz, style_name)
                           for style_name in variable_style_names]
        self._style_info._variable_styles = variable_styles
        
        regex_style_names = self._stateMap.get('regex', [])
        regex_styles = [getattr(components.interfaces.ISciMoz, style_name)
                         for style_name in regex_style_names]
        self._style_info._regex_styles = regex_styles

        self.matchingSoftChars = {"(": (")", None),
                                  "{": ("}", None),
                                  "[": ("]", None),
                                  '"': ('"', self.softchar_accept_matching_double_quote),
                                  "'": ("'", self.softchar_accept_matching_single_quote),
                                  }

        prefObserver = self.prefset.prefObserverService
        prefObserver.addObserver(self, 'indentStringsAfterParens', True)
        prefObserver.addObserver(self, 'editSmartSoftCharacters', True)
        prefObserver.addObserver(self, 'dedentOnColon', True)
        prefObserver.addObserver(self, 'codeintelAutoInsertEndTag', True)
        self._indentStringsAfterParens = self.prefset.getBooleanPref("indentStringsAfterParens")
        self._editSmartSoftCharacters = self.prefset.getBooleanPref("editSmartSoftCharacters")
        self._dedentOnColon = self.prefset.getBooleanPref("dedentOnColon")
        self._codeintelAutoInsertEndTag = self.prefset.getBooleanPref("codeintelAutoInsertEndTag")
        self._fastCharData = None

        # nsIObserverService must be called on the main thread - bug 96530.
        @components.ProxyToMainThread
        def ProxyAddObserver(obj):
            obsSvc = components.classes["@mozilla.org/observer-service;1"].\
                           getService(components.interfaces.nsIObserverService)
            obsSvc.addObserver(obj, 'xpcom-shutdown', False)
        ProxyAddObserver(self)


    def observe(self, subject, topic, data):
        if topic == 'xpcom-shutdown':
            prefObserver = self.prefset.prefObserverService
            prefObserver.removeObserver(self, 'indentStringsAfterParens')
            prefObserver.removeObserver(self, 'editSmartSoftCharacters')
            prefObserver.removeObserver(self, 'dedentOnColon')
            prefObserver.removeObserver(self, 'codeintelAutoInsertEndTag')
        elif topic in ('indentStringsAfterParens',
                       'editSmartSoftCharacters', 'dedentOnColon',
                       'codeintelAutoInsertEndTag'):
            setattr(self, "_" + topic,
                    self.prefset.getBooleanPref(topic))

    def getExtraFileAssociations(self):
        return self.extraFileAssociations
    def getSubLanguages(self):
        return [self.name]
    def getLanguageForFamily(self, family):
        return self.name
    def getPublicIdList(self):
        return self.publicIdList
    def getSystemIdList(self):
        return self.systemIdList
    def getNamespaces(self):
        return self.namespaces

    def getCommentStyles(self):
        return self._style_info._comment_styles
    def getStringStyles(self):
        return self._style_info._string_styles
    def getNumberStyles(self):
        return self._style_info._number_styles
    def getVariableStyles(self):
        return self._style_info._variable_styles
    def getNamedStyles(self, name):
        _style_names = self._stateMap.get(name, [])
        _styles = [getattr(components.interfaces.ISciMoz, style_name)
                         for style_name in _style_names]
        return _styles

    def isUDL(self):
        return False
 
    ##
    # @deprecated since Komodo 9.0
    #
    def actual_style(self, orig_style):
        import warnings
        warnings.warn("actual_style is deprecated, use scimoz.getStyleAt(pos) instead",
                      category=DeprecationWarning)
        return orig_style

    def getLanguageService(self, iid):
        if self._svcdict.has_key(iid):
            return getattr(self, self._svcdict[iid])()
        return None

    # override these getters if you need to override the language services

    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(components.interfaces.ISciMoz.SCLEX_NULL)
        return self._lexer

    def get_foldable(self):
        lexer = self.get_lexer()
        return lexer.supportsFolding
    
    # Not used
    #def get_style(self):
    #    if self._style is None:
    #        self._style = KoStyleLanguageService()
    #    return self._style

    # Specific language implementations should only implement one of the
    # following two. The former for the old completion system and the
    # latter for the new Code Intel-based completion system.
    def get_completer(self):
        return self._completer
    def get_codeintelcompleter(self):
        return self._codeintelcompleter

    def get_interpreter(self):
        return self._interpreter
    
    def get_commenter(self):
        if self._commenter is None and self.commentDelimiterInfo:
            self._commenter = KoCommenterLanguageService(
                self.commentDelimiterInfo)
        return self._commenter

    def getEncodingWarning(self, encoding):
        if not encoding.encoding_info.ascii_superset:
            return '"%s" is not a recommended encoding for %s. Using ASCII or an ASCII superset is recommended.'\
                    % (encoding.friendly_encoding_name, self.name)
        elif encoding.use_byte_order_marker:
            return 'Including a signature (BOM) is not recommended for %s.' % self.name
        else: # It's all good
            return ''

    def getBraceIndentStyle(self, ch, style):
        return self._getBraceIndentStyle(ch, style, self._style_info)
    
    def _getBraceIndentStyle(self, ch, style, style_info):
        if ch in self._indent_chars and style in style_info._indent_styles:
            return components.interfaces.koILanguage.INDENT_BRACE
        
        if ch in self._lineup_chars and style in style_info._lineup_styles:
            return components.interfaces.koILanguage.LINEUP_BRACE
        return 0

    def getMatchingChar(self, ch):
        if self.matchingSoftChars.has_key(ch):
            return self.matchingSoftChars[ch][0]
        else:
            return None

    def guessIndentation(self, scimoz, tabWidth, defaultUsesTabs):
        return self._guessIndentation(scimoz, tabWidth, defaultUsesTabs, self._style_info)

    def _guessIndentation(self, scimoz, tabWidth, defaultUsesTabs, style_info):
        indent, usesTabs = _findIndent(scimoz,
                                       self._indent_open_chars,
                                       style_info._indent_open_styles,
                                       style_info._comment_styles,
                                       tabWidth,
                                       defaultUsesTabs)
        return indent, usesTabs
    
    def guessIndentationByFoldLevels(self, scimoz, tabWidth, defaultUsesTabs, minIndentLevel):
        """This routine is needed because the base-class routine
        assumes indenting lines end with an operator and open-char.
        In Ruby and XML they don't.
        
        See comment in _findIndent for definitions
        of terminology like 'indenting', 'indented'...
        XXX to DavidA - why didn't the routine use Scintilla's levels before?
        """
        comment_styles = None
        textLength = scimoz.length
        if textLength == 0:
            return 0, 0
        # first, colourise the first 100 lines at most so we have
        # styling information.
        N = min(100, scimoz.lineCount)
        end = scimoz.getLineEndPosition(N - 1)
        if scimoz.endStyled < end:
            scimoz.colourise(scimoz.endStyled, end)
    
        for lineNo in range(N):
            # the outer loop tries to find the 'indenting' line.
            level = scimoz.getFoldLevel(lineNo)
            if level % scimoz.SC_FOLDLEVELHEADERFLAG == 0: # Not an indenting line
                indentlog.debug("line %d is white", lineNo)
                continue
            indentedLineNo = self._findChildLine(scimoz, level, lineNo + 1, N)
            if indentedLineNo is None:
                indentlog.debug("reject line %d", lineNo)
                continue
            if comment_styles is None:
                # Lazily loaded.
                comment_styles = self.getCommentStyles()
            indentEndPosition = scimoz.getLineIndentPosition(indentedLineNo)
            style = scimoz.getStyleAt(indentEndPosition)
            if style in comment_styles: # skip comments
                indentlog.debug("reject line %d - it's a comment", lineNo)
                continue

            ws_info = [classifyws(scimoz.getTextRange(scimoz.positionFromLine(aLine),
                                                   scimoz.getLineIndentPosition(aLine)), tabWidth)
                    for aLine in [lineNo, indentedLineNo]]
            # each entry in ws_info consists of a (raw, indent length, foundTabs bool) tuple
            guess = ws_info[1][1] - ws_info[0][1]
            foundTabs = ws_info[0][2] or ws_info[1][2]
            # If the guess is reasonable, use it -- indents less than
            # 2 don't qualify.
            if guess >= minIndentLevel:
                indentlog.debug("return guess=%r, foundTabs=%r", guess, foundTabs)
                if not foundTabs:
                    # Look at all lines but the first to see if any of them use leading tabs
                    sawSufficientWhiteSpace = False
                    for subLineNo in range(1, N):
                        level = scimoz.getFoldLevel(subLineNo)
                        if level % scimoz.SC_FOLDLEVELWHITEFLAG == 0: continue
                        # Just look at the first character
                        lineStartPos = scimoz.positionFromLine(subLineNo)
                        lineEndPos = scimoz.getLineEndPosition(subLineNo)
                        # lineEndPos is ok at the end of buffer, as we
                        # don't index with it here.
                            
                        line = scimoz.getTextRange(lineStartPos, lineEndPos)
                        blackPos = len(line) - len(line.lstrip())
                        # Make sure the indentation is big enough to count
                        if '\t' in line[:blackPos]:
                            foundTabs = 1
                            break
                        elif blackPos >= tabWidth:
                            sawSufficientWhiteSpace = True
                return guess, foundTabs or (not sawSufficientWhiteSpace and defaultUsesTabs)
            else:
                indentlog.warn("Found non-positive guess of %r (min %r)", guess, minIndentLevel)
                # Try the next parent-child pair
        return 0, 0
    
    def _findChildLine(self, scimoz, headerLevel, startLineNo, endLineNo):
        #indentlog.debug("find an indented line for line %d", startLineNo)
        FOLDLEVELMASK = 0x3ff
        headerFoldLevel = headerLevel & FOLDLEVELMASK
        for lineNo in range(startLineNo, endLineNo):
            level = scimoz.getFoldLevel(lineNo)
            if level & scimoz.SC_FOLDLEVELWHITEFLAG:
                #indentlog.debug("line %d is white", lineNo)
                continue
            elif (level & FOLDLEVELMASK) == headerFoldLevel + 1:
                #indentlog.debug("line %d is a child", lineNo)
                return lineNo
            else:
                #indentlog.debug("reject line %d, level 0x%04x, parent 0x%04x", lineNo, level, headerLevel)
                # Most likely we hit the end of a block with no inner statements
                return None
        return None
    
    def _getNextLineIndent(self, scimoz, lineNo):
        currentIndentWidth = self._getIndentWidthForLine(scimoz, lineNo)
        indent = scimoz.indent
        if indent == 0:
            indentlog.error('indent was 0, defaulting to 8')
            indent = 8
        return (divmod(currentIndentWidth, indent)[0] + 1) * indent        
    
    def _shouldIndent(self, scimoz, pos, style_info):
        # The first phase is to look for indenting statements.
        # these can be followed on the current line by comments.
        #
        # look past any comments to the left until hit either beginning
        # of line or a character.
        # if that character is an indenting brace, then indent.

        # Note that koCoffeeScriptLanguage overrides this method.
        curLineNo = scimoz.lineFromPosition(pos)
        lineStart = scimoz.positionFromLine(curLineNo)
        data = scimoz.getStyledText(lineStart, pos+1)
        for p in range(pos-1, lineStart-1, -1):
            char = data[(p-lineStart)*2]
            style = ord(data[(p-lineStart)*2+1])
            #indentlog.debug("char = %s, style = %d", char, style)
            #indentlog.debug("indent_open_chars = %r, indent_open_styles = %r", self._indent_open_chars, style_info._indent_open_styles)
            if style in style_info._comment_styles:
                indentlog.debug("skipping comment character")
                continue
            elif char in ' \t':
                continue
            elif (char in self._indent_open_chars and
                  style in style_info._indent_open_styles):
                return self._findIndentationBasedOnStartOfLogicalStatement(scimoz, pos, style_info, curLineNo)
            break
        return None

    def _findIndentationBasedOnStartOfLogicalStatement(self, scimoz, pos, style_info, curLineNo):
        # need to find the beginning of the logical statement.
        lineNo = self._statementStartingLineFromPos(scimoz, pos, style_info)
        indentlog.debug("we've decided that the statement starting from line %d actually starts at line %d" % (curLineNo, lineNo))
        nextIndentWidth = self._getNextLineIndent(scimoz, lineNo)
        return scimozindent.makeIndentFromWidth(scimoz, nextIndentWidth)

    def _shouldLineUp(self, scimoz, pos, style_info):
        # first we look for an unmatched 'line-up' brace, going back until
        # either we've gone back 100 lines, or we get past the indent
        # of the current line
        curLineNo = scimoz.lineFromPosition(pos)
        minIndent = self._getIndentWidthForLine(scimoz, curLineNo)
        startLineNo = max(curLineNo-100, 0)
        startPos = scimoz.positionFromLine(startLineNo)
        p = pos
        data = scimoz.getStyledText(startPos, pos+1)
        while p > startPos:
            p = p - 1
            char = data[(p-startPos)*2]
            indentlog.info("looking at char %r at position %d", char, p)
            style = ord(data[(p-startPos)*2+1])
            if char in self._lineup_close_chars and style in style_info._lineup_close_styles:
                # skip to the match
                braceMatch = scimoz.braceMatch(p)
                if braceMatch == -1:
                    break
                p = braceMatch
                char = data[(p-startPos)*2]
                style = ord(data[(p-startPos)*2+1])
                lineNo = scimoz.lineFromPosition(p)
                minIndent = self._getIndentWidthForLine(scimoz, lineNo)
                continue # keep looking
            if char in self._lineup_open_chars and style in style_info._lineup_close_styles:
                # aha!
                # is there something to our right?
                indentlog.info("We've got a line up open char!: %r in %r", char, self._lineup_open_chars)
                lineNo = scimoz.lineFromPosition(p)
                lineEnd = scimoz.getLineEndPosition(lineNo)
                # Unicode: assume open-chars are not multi-byte
                line = scimoz.getTextRange(p+1, lineEnd)
                indentlog.info("Looking to what's to the right of us: %r", line)
                if line.strip():
                    indentlog.info("look forward until the first non-comment non-whitespace char until EOL")
                    for p2 in range(p, min(pos, lineEnd)):
                        ch2 = data[(p2-startPos)*2]
                        if ch2 in '  \t':
                            continue
                        style = ord(data[(p2-startPos)*2+1])
                        if style in style_info._comment_styles:
                            continue
                        indentlog.info("we're here -- this is the column that we should use for indenting")
                        column = scimoz.getColumn(p2)+1
                        return scimozindent.makeIndentFromWidth(scimoz, column)
                elif p == pos - 1:
                    # First char after bracket means we should do a brace-style indent
                    #indentlog.info("the line-up char is the last on the line, so do brace-style indenting")
                    column = self._getNextLineIndent(scimoz, lineNo)
                    return scimozindent.makeIndentFromWidth(scimoz, column)
                else:
                    indentlog.info("it's a whitespace line, use the indent of the opened brace + 1")
                    column = scimoz.getColumn(p)+1
                    return scimozindent.makeIndentFromWidth(scimoz, column)
            col = scimoz.getColumn(p)
            if col <= minIndent:
                indentlog.debug("breaking out of looking for line-up characters" +
                                "because we've moved too far to the left at column %d < %d", col, minIndent)
                return None
        return None

    def _skipOverParentheticalStatement(self, scimoz, pos, style_info):
        # we may just have finished a multi-line statement -- those involve
        # braces:
        #  if (x and y \
        #      and z)!
        # then we need to indent with the indent of the line with
        # the matching brace

        curLineNo = scimoz.lineFromPosition(pos)
        startOfLine = scimoz.positionFromLine(curLineNo)
        p = pos
        data = scimoz.getStyledText(startOfLine, pos+2)
        while p > startOfLine:
            p = p - 1
            char = data[(p-startOfLine)*2]
            style = ord(data[(p-startOfLine)*2+1])
            # if we encounter an _opening_ brace, then we should stop.
            if char in self._lineup_open_chars and \
               style in style_info._lineup_close_styles:
                return pos
            # if we encounter a closing brace, we skip to its match
            # and move on.
            if char in self._lineup_close_chars and \
               style in style_info._lineup_close_styles:
                # skip to the match
                braceMatch = scimoz.braceMatch(p)
                if braceMatch == -1:
                    return pos
                else: # we'll use the indent of this line
                    return braceMatch
        return pos
        
    def _statementStartingLineFromPos(self, scimoz, position, style_info):
        """ This function looks for the line that starts
        the statement which encompasses the position 'position'
        """
        curLineNo = scimoz.lineFromPosition(position)

        indentlog.info("looking for statement starting line from line %d", curLineNo)

        # we'll look at most 40 lines back # should be adjustable?
        startLineNo = max(curLineNo-40, 0) # curLineNo
        startPos = scimoz.positionFromLine(startLineNo)
        p = position
        lineNo = scimoz.lineFromPosition(p)
        data = scimoz.getStyledText(startPos, p)
        minIndent = self._getIndentWidthForLine(scimoz, curLineNo)
        indentlog.info("startPos = %d, p = %d", startPos, p)
        # moving back through the buffer, look for and 'end-condition', i.e.
        # something which indicates the start of a statement.
        #  - we run out of characters (40 lines back)
        #  - we find an indenting statement
        # If we encounter a line-up brace, we skip to the matching brace
        # and keep going.

        #indentlog.debug("indent_close_chars = %r, indent_close_styles = %r", self._indent_close_chars, style_info._indent_close_styles)
        while p > startPos:
            p = p - 1
            char = data[(p-startPos)*2]
            style = ord(data[(p-startPos)*2+1])
            #indentlog.debug("in _statementStartingLineFromPos: char = %s, style = %d", char, style)
            lineNo = scimoz.lineFromPosition(p)
            indentlog.debug("\np = %d (%r) - going until %d" % (p, char, startPos))
            if char in self._lineup_close_chars and \
               style in style_info._lineup_close_styles:
                # we found an closing brace, we want to skip back to the beginning.
                indentlog.info("found closing brace, skipping back")
                next_p = self._skipOverParentheticalStatement(scimoz, p+1, style_info)
                lineNo = scimoz.lineFromPosition(next_p)
                minIndent = self._getIndentWidthForLine(scimoz, lineNo)
                indentlog.debug("SKIPPED from %d to %d" %(p+1, next_p))
                if p+1 == next_p:
                    indentlog.debug("SKIPPED nowhere!")
                    return lineNo
                p = next_p
                lineNo = scimoz.lineFromPosition(p)
                minIndent = self._getIndentWidthForLine(scimoz, lineNo)
                continue # we've skipped over parens, keep going
                #indentlog.info("jumped to line %d" % lineNo)
                #return lineNo
            if scimoz.getColumn(p) <= minIndent:
                # if we've gone past the indent of the current position, it
                # may be time to call it quits. The only exception to that
                # is if the line _before_ ours ends with a continuation line.
                indentlog.debug("Got to column %d and minIndent is %d", scimoz.getColumn(p), minIndent)
                if lineNo == 0: return lineNo  # there can't be a continuation line before us
                prevLineNo = lineNo - 1
                lineStart = scimoz.positionFromLine(prevLineNo)
                lineEnd = scimoz.getLineEndPosition(prevLineNo)
                prevLine = scimoz.getTextRange(lineStart, lineEnd)
                indentlog.debug("previous line is: %r"% prevLine)
                if prevLine.rstrip().endswith('\\'):
                    indentlog.debug("skipping back")
                    p = lineEnd
                    lineNo = scimoz.lineFromPosition(p)
                    minIndent = self._getIndentWidthForLine(scimoz, lineNo)
                    continue
                indentlog.debug("we stop here")
                return lineNo
        # if we find nothing, we just give up and assume the statement
        # starts on the line containing 'position'.
        indentlog.info("Found nothing, returning the line we ended up at.")
        return lineNo
    
    def _analyzeIndentNeededAtPos(self, scimoz, pos, continueComments, style_info):
        """ This function returns:
        
          - None if a 'plain' style indent should be done

          - 1 if an indent should be done

          - -1 if a dedent should be done
          
          - a string which should be used as the indent otherwise.
          
        """
        if scimoz.getColumn(pos) == 0:
            # If we're in column zero, do me no favors
            return None
        
        inBlockCommentIndent, inLineCommentIndent = self._inCommentIndent(scimoz, pos, continueComments, style_info)

        # see if we're in a block comment, and do 'inside-comment' indents
        if inBlockCommentIndent is not None:
            indentlog.info("we're in a block comment")
            return inBlockCommentIndent
        if continueComments and inLineCommentIndent is not None:
            return inLineCommentIndent
        
        # Bug 85020 special-case indendation after [op|opener str-open-delim return]
        if self._indentStringsAfterParens:
            res = self._atOpeningStringDelimiter(scimoz, pos, style_info)
            if res:
                return 1

        curLineNo = scimoz.lineFromPosition(pos)
        lineStart = scimoz.positionFromLine(curLineNo)
        lineEnd = scimoz.getLineEndPosition(curLineNo)
        shouldIndent = self._shouldIndent(scimoz, pos, style_info)
        if shouldIndent is not None:
            indentlog.info("detected indent")
            return shouldIndent
        indentlog.info("did not detect indentation")

        jumped = self._skipOverParentheticalStatement(scimoz, pos, style_info)
        log.debug("pos = %d, jumped = %d" % (pos, jumped))
        if pos != jumped:
            # recurse from the beginning of the statement
            return self._analyzeIndentNeededAtPos(scimoz, jumped, continueComments, style_info)

        # We're not indenting.  We may be doing a line-up,
        # having just finished a line-up
        # closing a comment, or doing a comment prefix

        shouldLineUp = self._shouldLineUp(scimoz, pos, style_info)
        if shouldLineUp is not None:
            indentlog.info("detected line-up")
            return shouldLineUp

        indentlog.info("did not detect line-up")

            
        ## We may just have finished a multi-line statement.  We need
        ## to align with the line that started the statement.
        #finishedMultiLineStatement = self._finishedMultiLineStatement(scimoz, pos)
        #if finishedMultiLineStatement is not None:
        #    indentlog.info("detected multi line statement")
        #    return finishedMultiLineStatement
        #
        #indentlog.info("did not detect end of multi-line statement")

        # See if we just closed a block comment, in which case we need to
        # dedent by a variable amount depending on the commenting style.

        if 'block' in self.commentDelimiterInfo:
            finishedBlockCommentIndent = self._finishedBlockComment(scimoz, pos, style_info)
            if finishedBlockCommentIndent is not None:
                indentlog.info("detected block comment close")
                return finishedBlockCommentIndent
            indentlog.info("did not detect block comment close")

        # See if we just closed a block comment, in which case we need to
        # dedent by a variable amount depending on the commenting style.

        continuationLineIndent = self._continuationLineIndent(scimoz, pos)
        if continuationLineIndent is not None:
            indentlog.info("detected continuation line indent")
            return continuationLineIndent
        indentlog.info("did not detect continuationLineIndent")

        # see if we're in a comment, and do 'inside-comment' indents
        if inLineCommentIndent is not None:
            indentlog.info("we're in a comment")
            return inLineCommentIndent

        indentingOrDedentingStatementIndent = self._indentingOrDedentingStatement(scimoz, pos, style_info)
        if indentingOrDedentingStatementIndent is not None:
            indentlog.info("detected indenting/dedenting statement")
            return indentingOrDedentingStatementIndent
        indentlog.info("did not detect indenting/dedenting statement")

        if 'line' in self.commentDelimiterInfo and not continueComments:
            indent = self._analyzeLineCommentIndent(scimoz, curLineNo, lineStart, pos, style_info)
            if indent is not None:
                return indent
            
        indentlog.info("not in comment, doing plain")
        return None

    def _analyzeLineCommentIndent(self, scimoz, curLineNo, lineStart, pos, style_info):
        """
        Returns:
        Either the string to use to indent the next line, or None, indicating
        the caller should take an alternative approach to find the indent string,
        or return None, and let its caller deal with it.
        
        See http://bugs.activestate.com/show_bug.cgi?id=94569
        Fix r72181 for http://bugs.activestate.com/show_bug.cgi?id=94508
        was incomplete.
        # Look for a case where we're ending a list of hanging comments:
        if 1: # start line *press shift-newline*
              # another line  *press shift-newline*
              # last line[|] (*press newline*) -- should indent based on first line containing comments
              
        We might have been at a situation like this:
        ..... code    # comment <shift-return>
        ..............# continue comment <shift-return>
        ..............# continue comment <return>
        
        Or maybe it was just this:
        .... header code:
        ....... #comment
        
        So if the current line is _COMMENT_STYLE_RUN_SPACE_COMMENT, walk up
        looking for a code line.  If the code line ends with a comment that
        starts at the same position as the current line's comment, indent
        based on that line. Otherwise indent based on the current line.
        
        So this skips any intervening empty and all-white-space lines.
        
        If we start with a CODE line, return None, which will end up returning
        the simple indent.
        """
        current_line_style_runs = self._getCommentStyleRunsForLine(scimoz, curLineNo, style_info, lineStartPos=lineStart, lineEndPos=pos)
        if (current_line_style_runs[0] != _COMMENT_STYLE_RUN_SPACE_COMMENT
            or current_line_style_runs[1] == 0):
            # We're only interested in lines that have non-empty leading
            # white-space followed by a comment, no code.
            return None
        for prevLineNo in range(curLineNo - 1, -1, -1):
            prev_line_style_runs = self._getCommentStyleRunsForLine(scimoz, prevLineNo, style_info)
            if prev_line_style_runs[0] == _COMMENT_STYLE_RUN_SPACE:
                # Ignore lines containing only white-space (including 0 chars)
                continue
            elif prev_line_style_runs[0] == _COMMENT_STYLE_RUN_SPACE_COMMENT:
                if current_line_style_runs[1] != prev_line_style_runs[1]:
                    # leading white-space differs, so go with the current line's indentation
                    return None
            elif prev_line_style_runs[3] == 0:
                # The code line has no comment, so go with the current line's indentation
                return None
            elif prev_line_style_runs[1] + prev_line_style_runs[2] != current_line_style_runs[1]:
                # The comments on the curr line and prev line start at
                # different positions, so go with the current line.
                return None
            else:
                # We hit the code line that started the current run of comments.
                # Base the indentation on it.
                currentPos = scimoz.currentPos
                anchor = scimoz.anchor
                scimoz.currentPos = scimoz.anchor = scimoz.getLineEndPosition(prevLineNo)
                try:
                    prevLineIndent = self._getSmartBraceIndent(scimoz, False, style_info)
                finally:
                    scimoz.currentPos = currentPos
                    scimoz.anchor = anchor
                return prevLineIndent

    def _getCommentStyleRunsForLine(self, scimoz, curLineNo, style_info, lineStartPos=None, lineEndPos=None):
        """
        Return a 4-tuple containing the line-type, followed by
        the line type
        len leading white-space
        len code
        len trailing comment
        
        There are only 3 line types:
         contains code: _COMMENT_STYLE_RUN_CODE (1)
         white-space only/empty: _COMMENT_STYLE_RUN_SPACE (2) 
         comment, no code. Leading white-space ok: _COMMENT_STYLE_RUN_SPACE_COMMENT (3)
        
        """
        if lineStartPos is None:
            lineStartPos = scimoz.positionFromLine(curLineNo)
        if lineEndPos is None:
            lineEndPos = scimoz.getLineEndPosition(curLineNo)
        data = scimoz.getStyledText(lineStartPos, lineEndPos)
        if not data:
            # empty line
            return (_COMMENT_STYLE_RUN_SPACE, 0, 0, 0)
        styles = [ord(x) for x in data[1::2]]
        text = [x for x in data[0::2]]
        lim = len(styles)
        if styles[0] in style_info._comment_styles:
            # Starts with a comment
            return (_COMMENT_STYLE_RUN_SPACE_COMMENT, 0, 0, lim)
        currIndex = 0
        # Find the end of the leading white-space.
        # Default styles in languages with line-comments should always be white-space
        # The language lexer is probably incomplete if this isn't the case, but check anyway
        while (currIndex < lim
               and (styles[currIndex] in style_info._default_styles
                    or styles[currIndex] == 0)
               and text[currIndex] in " \t"):
            currIndex += 1
        if currIndex == lim:
            # All default/blank
            return (_COMMENT_STYLE_RUN_SPACE, lim, 0, 0)
        if styles[currIndex] in style_info._comment_styles:
            # Comment follows leading white-space
            return (_COMMENT_STYLE_RUN_SPACE_COMMENT, currIndex, 0, lim - currIndex)
        lastCommentIdx = lim
        while styles[lastCommentIdx - 1] in style_info._comment_styles:
            lastCommentIdx -= 1
        # Line contains code.
        return (_COMMENT_STYLE_RUN_CODE, currIndex, lastCommentIdx - currIndex, lim - lastCommentIdx)
            
    def _atOpeningStringDelimiter(self, scimoz, pos, style_info):
        if pos < 3:
            return False
        prevPos = scimoz.positionBefore(pos)
        prevStyle = scimoz.getStyleAt(prevPos)
        if prevStyle not in style_info._string_styles:
            return False
        prevChar = scimoz.getWCharAt(prevPos)
        if prevChar not in "\"\'":
            return False
        return self._atOpeningIndenter(scimoz, scimoz.positionBefore(prevPos), style_info)
        
    def _atOpeningIndenter(self, scimoz, pos, style_info):
        prevStyle = scimoz.getStyleAt(pos)
        if prevStyle not in style_info._indent_open_styles:
            return False
        prevChar = scimoz.getWCharAt(pos)
        return prevChar in self._lineup_open_chars

    def _continuationLineIndent(self, scimoz, pos):
        """ This function looks to see if the line we just ended ends
        with a continuation symbol ('\' in all languages AFAIK).
        
        If yes, it looks to see if the line _before_ ours ends in a \
        as well, and if so, returns that line's indent.
        
        If not, it looks at the beginning of the current _logical_ line
        for an assignment (<>, =, or any of [|&<>]= ).  If it finds one, it returns
        an indent corresponding to the first non-whitespace character
        after the = sign.  If not, it returns an indent corresponding
        to the first non-whitespace characted in that line.
        """
        lineNo = scimoz.lineFromPosition(pos)
        lineStart = scimoz.positionFromLine(lineNo)
        # Unicode: pos is Unicode-safe value, set with
        # scimoz.currentPos in _getSmartBraceIndent
        curLine = scimoz.getTextRange(lineStart, pos)
        if not curLine.rstrip().endswith('\\'):
            #print "last line did NOT end with a \\"
            return None  # easy answer
        if lineNo:
            prevLineNo = lineNo - 1
            lineStart = scimoz.positionFromLine(prevLineNo)
            lineEnd = scimoz.getLineEndPosition(prevLineNo)
            prevLine = scimoz.getTextRange(lineStart, lineEnd)
            log.info("prevLine = %r", prevLine)
            if prevLine.rstrip().endswith('\\'):
                #print "last line is %r, ends with \\" % prevLine
                return self._getIndentForLine(scimoz, lineNo)
        m = self.assignmentRE.match(curLine)
        if m is None:
            #print "match failed, line = %r" % curLine
            return self._getIndentForLine(scimoz, lineNo)
        return scimozindent.makeIndentFromWidth(scimoz,
                                         len(m.group(1)) +
                                         len(m.group(2)) +
                                         len(m.group(3)))
    assignmentRE = re.compile(r"(.+?)(!=|<=|>=|<>|=|&=)(\s*)(.*)")

    firstWordRE = re.compile(r"\s*(\w*)");
    def _indentingOrDedentingStatement(self, scimoz, pos, style_info):
        """ This function looks to see if we just finished a dedenting
        statement (e.g. a pass, return, raise, yield in Python)
        or an indenting statement (e.g. an if or else that is not
        followed by a brace). 
        """
        originalPos = self._originalPos
        if originalPos < scimoz.length:
            currLineNo = scimoz.lineFromPosition(originalPos)
            currLineEndPos = scimoz.getLineEndPosition(currLineNo)
            if originalPos < currLineEndPos and scimoz.getTextRange(originalPos, currLineEndPos).strip():
                # Bug 80748: dedent/indent only when return is at end of line
                
                # Bug 80960: don't get the text at start of last line of the buffer
                return None
        
        lineNo = self._statementStartingLineFromPos(scimoz, pos-1, style_info)
        lineStart = scimoz.positionFromLine(lineNo)
        lineEnd = scimoz.getLineEndPosition(lineNo)
        curLine = scimoz.getTextRange(lineStart, lineEnd)
        indentlog.debug('got curLine = %r', curLine)

        # if we're in a string or comment, don't bother
        firstCharIndex = lineStart + len(curLine)-len(curLine.lstrip())
        firstCharStyle = scimoz.getStyleAt(firstCharIndex)
        if firstCharStyle in style_info._comment_styles or firstCharStyle in style_info._string_styles:
            return None

        wordMatch = self.firstWordRE.match(unicode(curLine))
        if wordMatch and wordMatch.group(1) in self._indenting_statements:
            return 1
        if wordMatch and wordMatch.group(1) in self._dedenting_statements:
            return self.finishProcessingDedentingStatement(scimoz, pos, curLine)
        return None

    def finishProcessingDedentingStatement(self, scimoz, pos, curLine):
        lineNo = scimoz.lineFromPosition(pos)
        currentIndentWidth = self._getIndentWidthForLine(scimoz, lineNo)
        indent = scimoz.indent
        if indent == 0:
            log.error('indent was 0, defaulting to 8')
            indent = 8 # XXX
        indentLevel, extras = divmod(currentIndentWidth, indent)
        if indentLevel and not extras:
            indentLevel -= 1
        nextIndentWidth = indentLevel * scimoz.indent
        return scimozindent.makeIndentFromWidth(scimoz, nextIndentWidth)

    def findActualStartLine(self, scimoz, startLine):
        return startLine

    def _finishedBlockComment(self, scimoz, pos, style_info):
        """ This function looks to see if we just ended a block comment.
        If not, it returns None
        If yes, it returns the indent appropriate
        for the next line -- e.g.:
        
            ....x = 3 /* this is the start
                         and so
            ..........*/
            
        Return a four-space string to be used for indenting the next line.
        
        This method used to return two strings, the nextLineIndent and a
        current-line indent. But with the change in r71995, there's never a need
        to adjust a comment-end
        """
        
        # Unicode: is pos used correctly in this function?
        lineNo = scimoz.lineFromPosition(pos)
        startOfLine = scimoz.positionFromLine(lineNo)
        p = pos
        data = scimoz.getStyledText(startOfLine, pos)
        while p > startOfLine:
            p -= 1
            # move back until we hit a non-whitespace character.
            char = data[(p-startOfLine)*2]
            if char in ' \t': continue
            style = ord(data[(p-startOfLine)*2+1])
            if style not in style_info._block_comment_styles:
                # we hit a non-comment character -- it can't be the
                # end of a block comment
                indentlog.info("we hit a non-comment character -- it can't be the end of a block comment")
                return None
            # Break out of the loop. Either we're at the end of a blockCommentEnd, and can
            # process it, or we aren't, and return None
            break
        
        # see if our current position matches the ends of block comments
        # Pascal has two sets of block-comments, so look to see if we're looking at one.
        # Assume no language has multiple blockCommentEnds where one is a suffix of
        # the other.
        blockCommentPairs = self.commentDelimiterInfo['block']
        pRel = p - startOfLine + 1
        for blockCommentPair in blockCommentPairs:
            blockCommentEnd = blockCommentPair[1]
            if pRel >= len(blockCommentEnd):
                if "".join(data[(pRel - len(blockCommentEnd))*2 : pRel *2 : 2]) == blockCommentEnd:
                    blockCommentStart = blockCommentPair[0]
                    break
        else:
            return None
        
        # we have a comment end!
        # find the matching comment start
        #XXX: Note it would be better to walk up skipping through sequences of
        #
        # ... */ some code /* ...
        #                   *
        #                   */
        # Don't stop at the line that contains 'some code' -- keep walking upwards.
        
        text = scimoz.getStyledText(0, p)[0::2] # Stay with bytes, not ucs-2 chars
        startOfComment = text.rfind(blockCommentStart)
        if startOfComment == -1:
            indentlog.info("could not find the beginning of the block comment")
            return None
        return self._getIndentForLine(scimoz, scimoz.lineFromPosition(startOfComment))
    
    def shiftRegionByDelta(self, scimoz, startLineNo, endLineNo, delta):
        for lineNo in range(startLineNo, endLineNo+1):
            indentWidth = self._getIndentWidthForLine(scimoz, lineNo)
            indentWidth = max(0, indentWidth+delta)
            indent = scimozindent.makeIndentFromWidth(scimoz, indentWidth)
            start = scimoz.positionFromLine(lineNo)
            end = scimoz.getLineEndPosition(lineNo)
            line = scimoz.getTextRange(start, end)
            for i in range(len(line)):
                if line[i] not in ' \t': break
            line = indent + line[i:]
            scimoz.anchor = start
            scimoz.currentPos = end
            scimoz.replaceSel(line) # optimize

    def _reverse(self, s):
        l = list(s)
        l.reverse()
        return ''.join(l)

    # Return the start point of the earliest comment in the list
    # This allows things like /*...*/ ... /* ... */ on one line
    # Relative to the start of the line
    # It also returns the marker used, for convenience
    
    def _findCommentStart(self, scimoz, curLine, lineStartPos, lineEndPos, commentStartMarkerList, style_info):
        commentStyles = style_info._comment_styles
        for pos in range(lineStartPos, lineEndPos):
            if scimoz.getStyleAt(pos) in commentStyles and \
               (pos == 0 or scimoz.getStyleAt(pos-1) not in commentStyles):
                # Bug 98467 note
                # Don't continue if scimoz.getCharAt(pos - 1) == 10
                # because block comments look like this.
                #
                # The LexOther lexer doesn't end comments at newline.
                line_pos = pos - lineStartPos
                for marker in commentStartMarkerList:
                    if curLine[line_pos : line_pos + len(marker)] == marker:
                        # indentlog.debug(" found it at pos %d", line_pos)
                        return (marker, line_pos)
                    else:
                        #substr2 = curLine[line_pos : line_pos + len(marker)]
                        #indentlog.debug("substr is %s, marker is %s", substr2, marker)
                        pass
        # Semi-reasonable fallback: point to the first marker in the list
        return (commentStartMarkerList[0], -1)

    # Hardwired RE when we know comments start with "/*"
    # Perf optimization
    _singleLineCommentRE = re.compile(r'\s*/\*.*\*/\s*$')    
    def _blockCommentOnSingleLineIndent(self, commentStartMarker, curLine, commentStart):
        """ If a complete block comment sits on a single line the indenter
        has less to do, and should indent as if the user gave a line-comment.
        """
        if commentStartMarker == '/*':
            if self._singleLineCommentRE.match(curLine):
                return curLine[0:commentStart]
            else:
                return None   
        # Build an RE and check for single-line
        commentEndMarkers = [markerPair[1]
                             for markerPair in self.commentDelimiterInfo['block']
                             if markerPair[0] == commentStartMarker]
        if len(commentEndMarkers) == 0:
            return None
        # If one start marker maps to more than one end-marker,
        # go with the first given in the list.  It's possible,
        # but I can't name any languages that does this.
        # An example would be a language where both
        # /* ... */ and /* ... <<@@! are valid comments.
        
        thisSingleLineCommentRE = re.compile(r'\s*'
                                           + re.escape(commentStartMarker)
                                           + '.*'
                                           + re.escape(commentEndMarkers[0])
                                           + r'\s*$')
        if thisSingleLineCommentRE.match(curLine):
            return curLine[0:commentStart]
        return None

    def _inCommentIndent(self, scimoz, pos, continueComments, style_info):
        # this function returns two arguments -- if the first
        # is non-None, then we're in a block comment and should
        # indent the next line w/ the returned value.  If the
        # second is non None, then we're in a line comment and
        # _if no other indentation takes precendence_, we should
        # indent w/ the returned value.  If both values are None,
        # then we're in no kind of comment.
        
        #indentlog.debug("==> _inCommentIndent(%d, %d)", pos, continueComments)
        if pos == 0:
            return None, None

        style = scimoz.getStyleAt(pos-1)
        if style not in style_info._comment_styles:
            return None, None
        
        # determine if we're in a line-style comment or a block-style comment
        if style in style_info._block_comment_styles and \
           'block' in self.commentDelimiterInfo:
            commentType = 'block'
            indentlog.debug("in block comment style")
            # see if our current position matches the ends of block comments
            # This assumes all comment delim chars are ascii
            commentEndMarkers = [markerPair[1]
                                 for markerPair in self.commentDelimiterInfo['block']]
            max_comment_len = max([len(x) for x in commentEndMarkers])
            lastTextPart = scimoz.getTextRange(pos - max_comment_len, pos)
            for commentEndMarker in commentEndMarkers:
                if lastTextPart.endswith(commentEndMarker):
                    #indentlog.debug("found a comment-end at pos:%d", pos)
                    return None, None
            commentStartMarkerList = [x[0] for x in self.commentDelimiterInfo[commentType]]
        else:
            commentType = 'line'
            indentlog.debug("in line comment style")
            if commentType not in self.commentDelimiterInfo:
                log.error("The style %d is not recognized as a block comment, but there are no line-style comments for this language", style)
                return None, None
            commentStartMarkerList = self.commentDelimiterInfo[commentType]
            
        curLineNo = scimoz.lineFromPosition(pos)
        lineStart = scimoz.positionFromLine(curLineNo)
        lineEnd = scimoz.getLineEndPosition(curLineNo)
        curLine = scimoz.getTextRange(lineStart, lineEnd)
        # Does the comment start on this line?
        # commentStart = curLine.find(commentStartMarker)
        
        commentStartMarker, commentStart = self._findCommentStart(scimoz, curLine, lineStart, lineEnd, commentStartMarkerList, style_info)
        #indentlog.debug("    commentStart(%d,%d) => %d", lineStart, lineEnd, commentStart)
        
        if commentType == 'block':
            if commentStart == -1:
                # The block marker we looked for didn't start on this line
                # 
                # It could be that we're in a line comment type, but the lexers
                # aren't rich enough to tell the difference.
                #
                # We'll look for the beginning of a line marker and treat
                # the comment as a line
                if 'line' in self.commentDelimiterInfo:
                    commentType = 'line'
                    commentStartMarker = self.commentDelimiterInfo[commentType][0]
                    # XXX should actually look at all comment start markers for
                    # languages where there are more than one.
                    if commentStartMarker:
                        commentStart = curLine.find(commentStartMarker)
                else:
                    doclen = scimoz.length
                    if pos < doclen and scimoz.getStyleAt(pos) not in style_info._comment_styles:
                        # Observed with CSS but not C/C++
                        # If the newline after the comment is not a comment,
                        # assume the comment has ended.
                        # This is because only CSS and Pascal define
                        # block comments but not any others.
                        return None, None
                    elif pos == doclen:
                        # We're at the end of the doc, so look to see
                        # if the current line ends with a comment-end sequence
                        revCurLine = self._reverse(curLine)
                        for comment_tuples in self.commentDelimiterInfo["block"]:
                            c_end = self._reverse(comment_tuples[1])
                            if revCurLine.find(c_end) == 0:
                                # indentlog.debug("bailing out -- we found %s at endof line %s", comment_tuples[0], curLine)
                                return None, None
                        # indentlog.debug("we didn't find any of %s in line [%s] (%s)", self.commentDelimiterInfo["block"], curLine, revCurLine)
                    else:
                        # We're at the end of the file, and probably the newline
                        # character hasn't been processed yet.
                        pass
                        # style = scimoz.getStyleAt(pos)
                        # indentlog.debug("staying, no line style: pos=%d, len=%d, curr style=%d, char %d", pos, doclen, style, ord(str(scimoz.getWCharAt(pos))))
            else:
                indent = self._blockCommentOnSingleLineIndent(commentStartMarker, curLine, commentStart)
                if indent is not None:
                    return indent, None

        # We want to find out what part of the beginning of the line
        # we want to duplicate -- whitespace, as well as any "markup"
        # characters, as in:
        #  /*<-- that's the comment start marker
        #   *<-- that's markup
        #
        markup = self.commentDelimiterInfo.get('markup', '')
        duplicate = ' \t' + markup
        
        # did the comment start on this line?  If no, then just
        # do an indent that duplicates whatever markup there is.
        if commentStart == -1: # look for 'markup' that should be duplicated
            if markup == '': # just do a standard indent
                return None, None
            indent = ''
            # Unicode: pos is unicode-safe, set as scimoz.currentPos in the caller
            curLineUntilPos = scimoz.getTextRange(lineStart, pos)
            for ch in curLineUntilPos:
                if ch in duplicate:
                    indent += ch
                else:
                    break
            if commentType == 'line':
                return None, indent
            else:
                return indent, None

        rest = curLine[commentStart+len(commentStartMarker):]
        indentWidth =len(curLine[:commentStart].expandtabs(scimoz.tabWidth))
        addMarkup = False
        if commentType == 'line':
            # the comment started on this line -- if the line consisted of nothing but
            # comments, then continue it (except if continueComments is false)
            # If there was code on the line, then don't do anything special.
            fromStartToCommentStart = curLine[0:commentStart]
            if not continueComments:# or fromStartToCommentStart.strip():
                return None, None
            indent = scimozindent.makeIndentFromWidth(scimoz, indentWidth) + commentStartMarker
        else:
            indent = scimozindent.makeIndentFromWidth(scimoz, indentWidth) + (len(commentStartMarker)-len(markup))*' '
            if markup and not rest.startswith(markup):
                addMarkup = True
                
        if rest.startswith(commentStartMarker):
            while rest.startswith(commentStartMarker):
                if commentType == 'line':
                    indent += commentStartMarker
                else:
                    indent += (len(commentStartMarker) - len(markup))*' '
                rest = rest[len(commentStartMarker):]
        elif addMarkup:
            # bug84868 - contine /*-type comments, not just /** comments
            indent += markup
            
        if rest[0:1] and rest[0:1] in duplicate:
            indent += rest[0:1]
            rest = rest[1:]
        # add any remaining whitespace indent after the markup prefixes, so that e.g.:
        #
        #      ###      foo<|>
        #
        # yields
        #      ###      foo
        #      ###     <|>
        #
        ignoreMarkup = True
        for char in rest:
            if char in ' \t':
                indent += char
                ignoreMarkup = False
            elif char in markup and ignoreMarkup:
                # Ignore the markup chars in rest, we're looking for white-space
                # This causes
                # /***** *** <CR>
                # =>
                #  * <|>
                pass
            else:
                break
        if commentType == 'line':
            return None, indent
        else:
            return indent, None

    def computeIndent(self, scimoz, indentStyle, continueComments):
        # Make sure we call this method on this class, and not on a subclass
        # that's bubbling up.
        return KoLanguageBase._computeIndent(self, scimoz, indentStyle, continueComments, self._style_info)

    def _computeIndent(self, scimoz, indentStyle, continueComments, style_info):
        try:
            currentPos = scimoz.currentPos
            prevPos = scimoz.positionBefore(currentPos)
            prevStyle = scimoz.getStyleAt(prevPos)
            if continueComments and prevStyle in style_info._comment_styles:
                # bug 98467: If we're continuing comments in any type of
                # language (including non-indenting ones), check comments first.
                possibleIndent = self._getSmartBraceIndent(scimoz, continueComments, style_info)
                if possibleIndent:
                    return possibleIndent
            if indentStyle == 'none':
                return ''
            if indentStyle == 'plain':
                return self._getPlainIndent(scimoz, style_info)
            if self.supportsSmartIndent == 'text':
                lineNo = scimoz.lineFromPosition(scimoz.currentPos)
                indentWidth = self._getIndentWidthForLine(scimoz, lineNo)
                indentWidth = min(indentWidth, scimoz.getColumn(scimoz.currentPos))
                return scimozindent.makeIndentFromWidth(scimoz, indentWidth)
            if self.supportsSmartIndent in ('brace', 'python', 'keyword'):
                retVal = self._getSmartBraceIndent(scimoz, continueComments, style_info)
                if retVal or self.supportsSmartIndent == 'python':
                    return retVal
            if self.supportsSmartIndent == 'XML':
                retVal = self._getSmartXMLIndent(scimoz, continueComments, style_info)
                if retVal is not None:
                    return retVal
            # If we're at column 0, return the previous line's indentation.
            # But only do this if the current line is empty, and has a
            # non-zero fold level.
            pos = scimoz.currentPos
            currentLineNo = scimoz.lineFromPosition(pos)
            if (pos > 0
                and scimoz.getColumn(pos) == 0
                and scimoz.getLineEndPosition(currentLineNo) == pos
                and (scimoz.getFoldLevel(currentLineNo) & 0x3ff) > 0):
                return self._getIndentForLine(scimoz, currentLineNo - 1)
        except Exception, e:
            log.warn("Got exception computing indent", exc_info=1)
            return ''
        
    def insertElectricNewline(self, scimoz, indentStyle, closingCharPosn,
                              allowExtraNewline, style_info):
        """Called when newline is pressed between a soft-creating char and its
        closing match, where the closing match char is still soft.
        closingCharPosn points to the closing char posn. Returns: the position
        the cursor should move to, or None if no split occurred. Assumes: open
        and closing chars, and all white-space are ascii.
        """
        if indentStyle == 'none':
            return None
        openCharPosn = scimoz.positionBefore(closingCharPosn)
        openStyle = scimoz.getStyleAt(openCharPosn)
        openChar = chr(scimoz.getCharAt(openCharPosn))
        currentEOL = eollib.eol2eolStr[eollib.scimozEOL2eol[scimoz.eOLMode]]
        textToInsert = currentEOL
        smartBraceIndent = (indentStyle == 'smart' and
                            self.supportsSmartIndent in ('brace', 'python', 'keyword'))

        # These blocks show the effect of each path. The leading "i" marks the
        # indentation at the effective line containing the character to the left
        # of the cursor. We press return, and get one of the following four
        # results:
        if smartBraceIndent and \
                (openChar in self._indent_open_chars or openChar in self._lineup_open_chars):
            # Indent next line, dedent the closing line
            # i{<|>} =>
            # i{
            # i....<|>
            # i}
            #
            # If they pressed ctrl-shift-newline, produce ==>
            #
            # i{
            # i....<|>}
            #
            lineNo = self._statementStartingLineFromPos(scimoz, openCharPosn, style_info)
            closeIndentWidth = self._getIndentWidthForLine(scimoz, lineNo)
            nextIndentWidth = self._getNextLineIndent(scimoz, lineNo)
            indentColumn = scimoz.getColumn(closingCharPosn)
            textToInsert += scimozindent.makeIndentFromWidth(scimoz, nextIndentWidth)
            finalPosn = closingCharPosn + len(textToInsert)
            textToInsert += currentEOL + scimozindent.makeIndentFromWidth(scimoz, closeIndentWidth)
        else:
            # Keep current indent, but add an extra newline, and start at the empty line
            # i(<|>) =>
            # i(
            # i<|>
            # i)
            #
            # If they pressed ctrl-shift-newline, produce ==>
            #
            # i{
            # i<|>}
            
            lineNo = self._statementStartingLineFromPos(scimoz, closingCharPosn, style_info)
            currentIndentWidth = self._getIndentWidthForLine(scimoz, lineNo)
            textToInsert += scimozindent.makeIndentFromWidth(scimoz, currentIndentWidth)
            finalPosn = closingCharPosn + len(textToInsert)
            if allowExtraNewline:
                textToInsert += currentEOL + scimozindent.makeIndentFromWidth(scimoz, currentIndentWidth)
        scimoz.addText(len(textToInsert), textToInsert)
        return finalPosn

    def insertInternalNewline_Special(self, scimoz, indentStyle, currentPos,
                                      allowExtraNewline, style_info):
        return None
        
    def _getSmartBraceIndent(self, scimoz, continueComments, style_info):
        """ return the indent for the next line using the 'smart' algorithm"""
        currentPos = scimoz.currentPos
        if (scimoz.getColumn(currentPos) == 0):
            return None
        # Save the current pos in case we end up checking for an
        # indenting/dedenting keyword
        self._originalPos = currentPos
        analysis = self._analyzeIndentNeededAtPos(scimoz, currentPos, continueComments, style_info)
        #indentlog.debug("_getSmartBraceIndent: self._analyzeIndentNeededAtPos(%d,%d) => <<%s>>", currentPos, continueComments, repr(analysis))
        if analysis == None:
            return self._getPlainIndent(scimoz, style_info)
        # did we get a special prefix?  If yes, use that as the indent
        if analysis == 1: # doing an indent
            # need to find the beginning of the logical statement.
            lineNo = self._statementStartingLineFromPos(scimoz, currentPos-1, style_info)
            indentlog.info("doing an INDENT to the indent of line: %d" % lineNo)
            currentIndentWidth = self._getIndentWidthForLine(scimoz, lineNo)
            nextIndentWidth = (divmod(currentIndentWidth, scimoz.indent)[0] + 1) * scimoz.indent
            return scimozindent.makeIndentFromWidth(scimoz, nextIndentWidth)
        elif analysis == -1: # doing an dedent
            lineNo = self._statementStartingLineFromPos(scimoz, currentPos-1, style_info)
            #lineNo = scimoz.lineFromPosition(currentPos)
            indentlog.info("doing an DEDENT from the indent of line: %d" % lineNo)
            currentIndentWidth = self._getIndentWidthForLine(scimoz, lineNo)
            indent = scimoz.indent
            if indent == 0:
                log.error('indent was 0, defaulting to 8')
                indent = 8 # XXX
            indentLevel, extras = divmod(currentIndentWidth, indent)
            if indentLevel and not extras:
                indentLevel -= 1
            nextIndentWidth = indentLevel * scimoz.indent
            return scimozindent.makeIndentFromWidth(scimoz, nextIndentWidth)
        # return whatever we got
        return analysis

    def _findXMLState(self, scimoz, pos, char, style):
        """ Return one of the following regarding the nature of
        character 'char' of style 'style' at position 'pos' in the
        'scimoz' scintilla:
        
          - 'START_TAG_CLOSE': <foo ... >|
          
          - 'END_TAG_CLOSE': </foo ...>|
          
          - 'START_TAG_EMPTY_CLOSE': <foo ... />|
          
          - 'COMMENT_CLOSE': <!-- ... -->|
          
        For XML, we use styles. For HTML we do slower, probably slightly
        inaccurate logic.
        """
        #log.debug("_findXMLState, pos=%d, char=%r, style=%d",
        #          pos, char, style)
        #log.debug("         next: pos=%d, char=%r, style=%d",
        #          pos + 1, scimoz.getWCharAt(pos + 1), scimoz.getStyleAt(pos + 1))
        if style == scimoz.SCE_UDL_M_TAGNAME:
            return "START_TAG_NAME"
        if (style == scimoz.SCE_UDL_M_STRING and char in ('"', "'") 
            and scimoz.getStyleAt(pos + 1) in (scimoz.SCE_UDL_M_TAGSPACE,
                                               scimoz.SCE_UDL_M_DEFAULT)):
            # Verify there's a start-tag on this line
            curLineNo = scimoz.lineFromPosition(pos)
            lineStart = scimoz.positionFromLine(curLineNo)
            data = scimoz.getStyledText(lineStart, pos)
            idx = len(data) - 1
            while idx > 0:
                if ord(data[idx]) == scimoz.SCE_UDL_M_TAGNAME:
                    return "START_TAG_NAME"
                idx -= 2;
            indentlog.debug("found no start-tag, returning empty-string")
            return "ATTRIBUTE_CLOSE"
        if char != '>':
            return ''
        if style == scimoz.SCE_UDL_M_STAGC:
            return 'START_TAG_CLOSE'
        if style == scimoz.SCE_UDL_M_ETAGC:
            return 'END_TAG_CLOSE'
        if style == scimoz.SCE_UDL_M_EMP_TAGC:
            return 'START_TAG_EMPTY_CLOSE'
        indentlog.debug("scimoz.getWCharAt(pos-1) = %r", scimoz.getWCharAt(pos-1))
        if (pos > 2 and
            scimoz.getWCharAt(pos-1) == '/'):
            return 'START_TAG_EMPTY_CLOSE'
        if (style == scimoz.SCE_UDL_M_COMMENT and pos > 3 and
            scimoz.getWCharAt(pos-2) == '-' and
            scimoz.getWCharAt(pos-1) == '-'):
            return 'COMMENT_CLOSE'
        # Since we don't use the absolute locations of items in this chunk
        # of text, using characters instead of bytes is ok
        text = scimoz.getTextRange(0, scimoz.positionAfter(pos))
        lastLeftBraceIndex = text.rfind('<')
        lastSlashIndex = text.rfind('/')
        if lastSlashIndex == lastLeftBraceIndex + 1:
            return 'END_TAG_CLOSE'
        text = text.rstrip()
        if not text:
            return ''
        # Handle xml-based multi-sublanguage languages that don't
        # have a UDL definition, and end in strings like '%>'
        # Ref bug 57417
        if text[-1] == '>' and (len(text) == 1 or text[-2] not in "!@#$%^&*?]\'\""):
            # we just finished a tag, we think
            return "START_TAG_CLOSE"
        # we're likely in the text part of a <p> node for example
        return ''
    
    _precededByText_non_white_re = re.compile(r'[^ \t]')
    def _precededByText(self, scimoz, startPos, endPos,
                        beforeText, beforeStyles):
        assert beforeText[endPos] == "<"
        # If there's a non-whitespace character before the start of line
        # (startPos) and the start of the tag (endPos), return True.
        # XXX This really needs continual moving up until we determine
        # that we're at the top-level, in pure data markup (no mixed
        # tags), or in mixed content.
        return (self._precededByText_non_white_re.search(beforeText[startPos:endPos])
                or any([style != scimoz.SCE_UDL_M_DEFAULT
                        for style in beforeStyles[startPos:endPos]]))

    def _getTagStartLineStartPos_Buf(self, scimoz, tagStartPos_Buf,
                                     startOfLine_Buf, startPos_Doc):
        # Return the start of the line in Buffer coordinates
        # If the start tag starts before the current line does,
        # return the position of the start tag's line-start, in
        # buffer coordinates.
        if tagStartPos_Buf >= startOfLine_Buf:
            return startOfLine_Buf
        # the start of the tag moved to an earlier line, so find its
        # buffer-coordinate point
        prevLineNum = scimoz.lineFromPosition(tagStartPos_Buf + startPos_Doc)
        return scimoz.positionFromLine(prevLineNum) - startPos_Doc
    
    def _getSmartXMLIndent(self, scimoz, continueComments, style_info):
        """Smartest XML indentation we can figure.
        
        * if there is only whitespace to the left of the cursor,
          align w/ current line
        
        * if the closest character to the left of the cursor is
          the right bracket '>' of a begin tag (i.e. <foo>|), then indent
          by one more indent than the matching left '<'
          
        * if the closest character to the left of the cursor is
          the right bracket '>' of an end tag (i.e. </foo>|), then indent
          to the opening brace of the matching start tag (i.e. |<foo>),
          when the opening "<" is the first non-white-space character on
          the line.
          
        * if the closest character to the left of the cursor is
          the right bracket '>' of an empty tag (i.e. <foo/>|) then
          keep the same indent as the line on which the tag begins,
          when the opening "<" is the first non-white-space character on
          the line.
          
        * if the closest character to the left of the cursor is either
          the name of the tag (<foo|) or the right quote after an attribute
          value (<foo bar="baz"|), then indent to the first space after the
          tag name (in this case align with the '<foo '),
          when the opening "<" is the first non-white-space character on
          the line.

        * conditions 3, 4, and 5 need to be handled when there is more
          than a single, possibly complex element on the line.  For Komodo 4.0
          we implement one extra condition, and then fallback to original
          conditions.  If the opening tag's "<" character is preceded by
          a non-white-space, non-markup character, we align with the
          current line, as in condition 2.          
          
        * in all other cases, align w/ current line
        """
        import HTMLTreeParser
        currentPos = scimoz.currentPos
        currentLine = scimoz.lineFromPosition(currentPos)
        """ Note use of Doc/Buf coordinates.  *_Doc variables refer to coordinates
            in the scimoz space.  *_Buf variables refer to coordinates in the
            beforeText and beforeStyles buffers.
            
            (1) X_Doc  = X_Buf + startPos_Doc
            
            Both types of coordinates are in terms of bytes (utf-8)
        """
        startOfLine_Doc = scimoz.positionFromLine(currentLine)
        stuffToLeft = scimoz.getTextRange(startOfLine_Doc, currentPos)
        if not stuffToLeft.strip():
            return scimozindent.makeIndentFromWidth(scimoz, scimoz.getColumn(currentPos))
        index_Doc = currentPos - 1
        # Bug 100371: Try to process a reasonable amount of text
        # Try to look at the last 100 lines, assume avg of 60 chars/line: 6000
        #TODO: Prefize these values.  A non-positive value means ignore 
        limNumLines = 100
        limNumChars = 6000
        # Point startPos_Doc to the point in the doc that marks the start
        # of the buffer we work with.
        if index_Doc <= limNumChars:
            startPos_Doc = 0
        else:
            if currentLine > limNumLines:
                startPos_Doc = scimoz.positionFromLine(currentLine - limNumLines)
            else:
                startPos_Doc = 0
            if startPos_Doc < index_Doc - limNumChars:
                # Long lines: just process the last <limNumChars> characters
                # But always start at the beginning of a line.
                startPos_Doc = scimoz.positionFromLine(scimoz.lineFromPosition(index_Doc - limNumChars))
            
        beforeText = scimoz.getTextRange(startPos_Doc, currentPos).encode('utf-8')
        beforeStyles = scimoz.getStyleRange(startPos_Doc, currentPos)
        tagStartPos_Buf = -1
        startOfLine_Buf = startOfLine_Doc - startPos_Doc
        index_Buf = index_Doc - startPos_Doc
        index_Buf_Prev = -1
        
        while index_Buf > 0:
            
            # Avoid getting stuck in an infinite loop, see bug #186
            if index_Buf_Prev == index_Buf:
                index_Buf -= 1
            index_Buf_Prev = index_Buf
            
            char = beforeText[index_Buf]
            style = beforeStyles[index_Buf] # scimoz.getStyleAt(index_Doc)
            state = self._findXMLState(scimoz, index_Doc, char, style)
            if state == 'START_TAG_CLOSE':
                tagStartPos_Buf = beforeText.rfind('<', 0, index_Buf)
                standard_type = False
                # If we have an empty tag, set standard_type to True, and continue
                # to the end of block processing.
                if tagStartPos_Buf >= 0:
                    m = re.compile(r'([\w\-]+)').search(beforeText, tagStartPos_Buf)
                    if m:
                        if ((self.name.startswith("HTML")
                             and m.group(1) in HTMLTreeParser.html_no_close_tags)
                            or (self.name == "HTML5"
                                and m.group(1) in HTMLTreeParser.html5_no_close_tags)):
                            # Retry, treating it like a "<.../>" tag.
                            state = "START_TAG_EMPTY_CLOSE"
                            standard_type = True
                if not standard_type:
                    if tagStartPos_Buf < startOfLine_Buf:
                        if tagStartPos_Buf == -1:
                            # We failed to find it in the subset, so replace the buffers with the full thing,
                            # and retry
                            index_Doc = index_Buf + startPos_Doc + 1
                            startPos_Doc = 0
                            styledText = scimoz.getStyledText(startPos_Doc, index_Doc)
                            beforeText = styledText[0::2]
                            beforeStyles = [ord(c) for c in styledText[1::2]]
                            startOfLine_Buf = startOfLine_Doc
                            index_Buf = index_Doc - 1
                            continue
                            
                        # Update the "currentLine" arguments
                        currentLine = scimoz.lineFromPosition(tagStartPos_Buf + startPos_Doc)
                        startOfLine_Doc = scimoz.positionFromLine(currentLine)
                        startOfLine_Buf = startOfLine_Doc - startPos_Doc
                    if self._precededByText(scimoz, startOfLine_Buf,
                                            tagStartPos_Buf,
                                            beforeText, beforeStyles):
                        return self._getIndentForLine(scimoz, currentLine)
                    # convert from character offset to byte position --
                    # that's what getColumn wants.
                    tagStartPos_Doc = tagStartPos_Buf + startPos_Doc
                    currentIndentWidth = scimoz.getColumn(tagStartPos_Doc)
                    nextIndentWidth = (divmod(currentIndentWidth, scimoz.indent)[0] + 1) * scimoz.indent
                    indentlog.debug("currentIndentWidth = %r", currentIndentWidth)
                    indentlog.debug("nextIndentWidth= %r", nextIndentWidth)
                    return scimozindent.makeIndentFromWidth(scimoz, nextIndentWidth)
            elif state == "END_TAG_CLOSE":
                # find out what tag we just closed
                leftCloseIndex_Buf = beforeText.rfind('</', 0, index_Buf)
                if leftCloseIndex_Buf == -1:
                    break
                startTagInfo = scimozindent.startTagInfo_from_endTagPos(scimoz, leftCloseIndex_Buf + startPos_Doc)
                if startTagInfo is None:
                    tagStartPos_Buf = -1
                else:
                    tagStartPos_Doc = startTagInfo[0]
                    tagStartPos_Buf = tagStartPos_Doc - startPos_Doc
                    if tagStartPos_Buf < 0:
                        # We went past the start of the partial buffer, so just
                        # get the line the tag starts on, and return its indentation.
                        log.info("Looking for matching start-tag moved to pos %d, before startPos_Doc %d",
                                 tagStartPos_Doc, startPos_Doc)
                        currentLine = scimoz.lineFromPosition(tagStartPos_Doc)
                        tagStartPos_Buf = -1
                standard_type = True
            elif state == "START_TAG_EMPTY_CLOSE":
                tagStartPos_Buf = beforeText.rfind('<', 0, index_Buf)
                standard_type = True
            elif state == "ATTRIBUTE_CLOSE":
                return self._getIndentForLine(scimoz, currentLine)
            elif state == "START_TAG_NAME" or \
                        style in [scimoz.SCE_UDL_M_TAGSPACE,
                                  scimoz.SCE_UDL_M_ATTRNAME,
                                  scimoz.SCE_UDL_M_OPERATOR]:
                # We're somewhere in a tag.
                # Find the beginning of the tag, then move to the end of that word
                tagStartPos_Buf = beforeText.rfind('<', 0, index_Buf)
                if tagStartPos_Buf == -1:
                    break
                prevLinePos_Buf = self._getTagStartLineStartPos_Buf(scimoz,
                                                                    tagStartPos_Buf,
                                                                    startOfLine_Buf,
                                                                    startPos_Doc)
                if self._precededByText(scimoz, prevLinePos_Buf,
                                        tagStartPos_Buf,
                                        beforeText, beforeStyles):
                    return self._getIndentForLine(scimoz, currentLine)
                whitespaceRe = re.compile('(\S+)(\s*)')
                # Is there a space between the "<" and the current index position ?
                firstSpaceMatch = whitespaceRe.search(beforeText, tagStartPos_Buf, index_Buf)
                if not firstSpaceMatch:
                    standard_type = True
                else:
                    tagStartPos_Doc = tagStartPos_Buf + startPos_Doc
                    if firstSpaceMatch.group(2):
                        # i.e. there is some space after the tag
                        firstSpace_Buf = firstSpaceMatch.end() - tagStartPos_Buf
                        startAttributeColumn = scimoz.getColumn(tagStartPos_Doc + firstSpace_Buf)
                    else:
                        # e.g. we just hit return with: <foo|
                        endOfTag_Buf = firstSpaceMatch.end() - tagStartPos_Buf
                        startAttributeColumn = scimoz.getColumn(tagStartPos_Doc + endOfTag_Buf) + 1
                    return scimozindent.makeIndentFromWidth(scimoz, startAttributeColumn)
            elif state == "COMMENT_CLOSE":
                tagStartPos_Buf = beforeText.rfind('<!--', 0, index_Buf)
                standard_type = True
            elif state == "":
                if style == scimoz.SCE_UDL_M_DEFAULT:
                    if char.isspace():
                        index_Doc -= 1
                        index_Buf -= 1
                        standard_type = False # effective continue
                    else:
                        # If we don't end the line with a tag, continue the current indentation
                        return self._getIndentForLine(scimoz, currentLine)
                elif style == scimoz.SCE_UDL_M_PI:
                    if beforeText.endswith("?>", 0, index_Buf + 1):
                        tagStartPos_Buf = beforeText.rfind('<?', 0, index_Buf)
                        standard_type = True
                    else:
                        return self._getIndentForLine(scimoz, currentLine)
                elif style == scimoz.SCE_UDL_M_CDATA:
                    if beforeText.endswith("]]>", 0, index_Buf + 1):
                        tagStartPos_Buf = beforeText.upper().rfind('<![CDATA[', 0, index_Buf + 1)
                        standard_type = True
                    else:
                        return self._getIndentForLine(scimoz, currentLine)
                else:
                    return self._getIndentForLine(scimoz, currentLine)
            
            # Common endings for "standard" types
            if tagStartPos_Buf > index_Doc:
                assert False and "tag-start pos %d > index_Doc pos %d!" % (tagStartPos_Buf, index_Doc)
                break
            if standard_type:
                if tagStartPos_Buf == -1:
                    return self._getIndentForLine(scimoz, currentLine)
                if tagStartPos_Buf < startOfLine_Buf:
                    # Update the "currentLine" arguments
                    currentLine = scimoz.lineFromPosition(tagStartPos_Buf + startPos_Doc)
                    startOfLine_Doc = scimoz.positionFromLine(currentLine)
                    startOfLine_Buf = startOfLine_Doc - startPos_Doc
                # If there's nothing to the left of this tag, use that indentation
                # If we've moved to the start of the line, we'll return 0 chars indentation here,
                # so we never have to decrement the currentLine # when going through this path.
                if not beforeText[startOfLine_Buf:tagStartPos_Buf].strip():
                    return self._getIndentForLine(scimoz, currentLine)
                tagStartPos_Doc = tagStartPos_Buf + startPos_Doc
                index_Doc = tagStartPos_Doc - 1
                index_Buf -= 1
        # end of main while loop
                
        indentlog.debug("doing plain indent")
        return self._getPlainIndent(scimoz, style_info)
    
    def _getPlainIndent(self, scimoz, style_info):
        """ return the indent for the next line using the 'plain' algorithm:
             return the 'equivalent' indent as the current logical line """
        log.info("doing _getPlainIndent")
        lineNo = self._statementStartingLineFromPos(scimoz, scimoz.currentPos, style_info)
        return scimozindent.makeIndentFromWidth(scimoz,
                                         len(self._getIndentForLine(scimoz, lineNo, scimoz.currentPos).expandtabs(scimoz.tabWidth)))

    def _getRawIndentForLine(self, scimoz, lineNo, upto=None):
        lineStart = scimoz.positionFromLine(lineNo)
        if upto:
            lineEnd = min(upto, scimoz.getLineEndPosition(lineNo))
        else:
            lineEnd = scimoz.getLineEndPosition(lineNo)
        line = scimoz.getTextRange(lineStart, lineEnd)
        indentLength = len(line)-len(line.lstrip())
        return line[:indentLength]

    def _getIndentWidthForLine(self, scimoz, lineNo, upto=None):
        indent = self._getIndentForLine(scimoz, lineNo, upto)
        return len(indent.expandtabs(scimoz.tabWidth))

    def _getIndentForLine(self, scimoz, lineNo, upto=None):
        indent = self._getRawIndentForLine(scimoz, lineNo, upto)
        return scimozindent.makeIndentFromWidth(scimoz,
                                         len(indent.expandtabs(scimoz.tabWidth)))

    def _getIndentWidthFromIndent(self, scimoz, indentstring):
        """ Given an indentation string composed of tabs and spaces,
        figure out how long it is (get the tabWidth from scimoz) """
        expandedstring = indentstring.expandtabs(scimoz.tabWidth)
        return len(expandedstring)

    # Could be called across xpcom, so don't use optional args
    def getIndentForCloseChar(self, scimoz, charPos, ch, style, style_info,
                              default_indentation):
        if (ch in self._indent_close_chars and 
            style in style_info._indent_close_styles):
            indentlog.debug("got a closing brace")
            # need to find the matching brace
            braceMatch = scimoz.braceMatch(charPos)
            if braceMatch == -1:
                indentlog.debug("no matching brace")
                # no match, do nothing
                return None
            startLine = self._statementStartingLineFromPos(scimoz, braceMatch, style_info)
            return self._getIndentForLine(scimoz, startLine)
        elif (ch in self._lineup_close_chars and 
            style in style_info._lineup_close_styles):
            braceMatch = scimoz.braceMatch(charPos)
            if braceMatch == -1:
                # no match, do nothing
                return None
            
            proposed_indent = scimoz.getColumn(braceMatch)
            curr_indent = scimoz.getLineIndentation(scimoz.lineFromPosition(charPos))
            #indentlog.debug("Curr indent:%d, proposed indent:%d", curr_indent, proposed_indent)
            if proposed_indent < curr_indent:
                # If there's non white-space between proposed_indent
                # and curr_indent, the new indent will be ignored
                return scimozindent.makeIndentFromWidth(scimoz, proposed_indent)
        elif (ch in self._dedent_chars
              and style in style_info._indent_close_styles
              and hasattr(self, 'getIndentBasedOnDedentChar')):
            # The hasattr test is to see if a subclass included the mixin.
            # This is more performant than including a null getIndentBasedOnDedentChar
            # in this class and having to search the mixin class first for
            # every other method.
            new_indent = self.getIndentBasedOnDedentChar(scimoz, charPos, style_info)
            if new_indent is not None:
                # Do the indent here, and return 'None'
                start = scimoz.positionFromLine(scimoz.lineFromPosition(charPos))
                end = charPos
                # Unicode: charPos is safe
                stuffToLeft = scimoz.getTextRange(start, end)
                leadingWS = re.compile(r'^(\s+)').match(stuffToLeft)
                if leadingWS:
                    # all white-space on our left, so replace it
                    scimoz.targetStart = start
                    scimoz.targetEnd = start + len(leadingWS.group(1))
                    scimoz.replaceTarget(new_indent)
                    return None
        if default_indentation:
            return default_indentation
        return None

    # XPCOM call handles defaults
    def keyPressed(self, ch, scimoz):
        return self._keyPressed(ch, scimoz, self._style_info)

    def _keyPressed(self, ch, scimoz, style_info):
        if (self._fastCharData
            and ch == self._fastCharData.trigger_char
            and self._fastCharData.moveCharThroughSoftChars(ch, scimoz)):
            return
        currentPos = scimoz.currentPos
        charPos = scimoz.positionBefore(currentPos)
        style = scimoz.getStyleAt(charPos)
        #indentlog.debug("ch=%s, style=%d, indent_close_chars=%r, indent_close_styles=%r",
        #               ch, style, self._indent_close_chars, style_info._indent_close_styles)
        indent = None
        if (ch == '>' and self.supportsSmartIndent == 'XML'):
            state = self._findXMLState(scimoz, charPos, ch, style)
            if state == 'END_TAG_CLOSE':
                scimozindent.adjustClosingXMLTag(scimoz, self.isHTMLLanguage)
            elif state == 'START_TAG_CLOSE':
                # try to insert the closing tag; i.e. if the user types
                # "<html>|", insert "</html>" after the cursor
                if not self._codeintelAutoInsertEndTag:
                    # we don't want to automatically insert the closing tag
                    return
                if style != scimoz.SCE_UDL_M_STAGC:
                    # _findXMLState returns START_TAG_CLOSE on things that are
                    # wrong (e.g. "<window>>|") - don't trust it.
                    return
                targetStart = scimoz.targetStart
                targetEnd = scimoz.targetEnd
                searchFlags = scimoz.searchFlags
                try:
                    scimoz.targetStart = currentPos
                    scimoz.searchFlags = 0
                    while True:
                        # Bug 94854: look for start-tag-start characters,
                        # Skip <%= ... %> internal PHP things
                        # Set scimoz.targetEnd before each search, not just the first.
                        scimoz.targetEnd = 0
                        tagStart = scimoz.searchInTarget(1, "<")
                        if tagStart == -1:
                            # we shouldn't get here (how did we end up in
                            # START_TAG_CLOSE!?), but we should deal gracefully
                            log.warning("KoLanguageBase::_keyPressed: Failed to "
                                        "find start of tag in START_TAG_CLOSE")
                            return
                        tagStartStyle = scimoz.getStyleAt(tagStart)
                        if tagStartStyle == scimoz.SCE_UDL_M_STAGO:
                            break
                        scimoz.targetStart = scimoz.positionBefore(tagStart)
                        # And keep looking for a true start-tag "<"
                            
                    tagText = scimoz.getTextRange(tagStart, currentPos)
                    endTag = self.getEndTagForStartTag(tagText)
                    if endTag:
                        # check that the end tag doesn't already exist at the
                        # cursor position. (bug 91796)
                        posEnd = currentPos
                        for i in range(len(endTag)):
                            posEnd = scimoz.positionAfter(posEnd)
                        existingText = scimoz.getTextRange(currentPos, posEnd)
                        if endTag != existingText:
                            try:
                                scimoz.beginUndoAction()
                                scimoz.insertText(currentPos, endTag)
                                # Don't make the new text soft characters; that
                                # produces odd problems (they never harden
                                # correctly; deleting the start tag will only delete
                                # the first soft character, not the range).  It
                                # turns out to be a better experience to make
                                # everything hard (but undo-able).
                            finally:
                                scimoz.endUndoAction()
                finally:
                    # restore search states
                    scimoz.targetStart = targetStart
                    scimoz.targetEnd = targetEnd
                    scimoz.searchFlags = searchFlags
            return

        indent = self.getIndentForCloseChar(scimoz, charPos, ch, style, style_info, None)
        if (indent is None
            and style in style_info._comment_styles
            and 'block' in self.commentDelimiterInfo):
            blockCommentEndMarker = self.commentDelimiterInfo['block'][0][-1]
            if blockCommentEndMarker.endswith(ch):
                nextLineIndent = self._finishedBlockComment(scimoz, charPos+1, style_info)
                if nextLineIndent is not None:
                    charPos = charPos + 1 - len(blockCommentEndMarker)
                    # Fix bug 42792 -- do this in one place

        # Something in scintilla breaks on multiple-carets after a soft
        # character is inserted, and updates only happen at first caret.
        if (self._editSmartSoftCharacters
            and ch in self.matchingSoftChars
            and scimoz.selections == 1):
            soft_chars = self.determine_soft_char(ch, scimoz, charPos, style_info)
        else:
            soft_chars = None
        if soft_chars:
            new_pos = scimoz.positionAfter(currentPos)
            scimoz.insertText(currentPos, soft_chars)
            scimoz.indicatorCurrent = _softCharDecorator
            scimoz.indicatorFillRange(currentPos, len(soft_chars)) #only ascii chars here
        if indent is not None:                                   
            start = scimoz.positionFromLine(scimoz.lineFromPosition(charPos))
            end = charPos
            # Unicode: charPos is safe
            stuffToLeft = scimoz.getTextRange(start, end)
            if not stuffToLeft.strip():
                # all white-space on our left, so replace it
                scimoz.targetStart = start
                scimoz.targetEnd = end
                scimoz.replaceTarget(indent)

    def _softchar_accept_match_outside_strings(self, scimoz, pos, style_info, candidate):
        """
        Don't bother trying to figure out whether a quoting char is the start of a
        quote in unstructured styles like strings, regexes, and comments.  Users
        don't get the benefit of soft quotes, but they never get in their way either.
        Sample scenario:
        HTML file.  Type <p>a quote "to be or ..." ... </p>
        Now put the cursor after "to be" and type a double-quote.  We don't want
        a double-quote at this point here.  This code will give one only when
        the entered quote char starts a new style.
        """
        if scimoz.getStyleAt(pos) == 0:
            # No soft-chars for unstyled characters (see bug 80929).
            return None
        if pos == 0:
            return candidate
        prevPos = scimoz.positionBefore(pos)
        prevStyle = scimoz.getStyleAt(prevPos)
        if (prevStyle == scimoz.getStyleAt(pos) # we're in a string
            # Can't have a string immediately following a variable name without
            # an operator.
            or prevStyle in self.getVariableStyles()):
            return None
        return candidate

    # soft-character acceptance callback routines follow.  These can be overridden
    # by base-classes to implement language-specific behavior.  For example, in
    # Ruby $" is a variable name and shouldn't trigger a soft dquote.

    def softchar_accept_matching_double_quote(self, scimoz, pos, style_info, candidate):
        return self._softchar_accept_match_outside_strings(scimoz, pos, style_info, candidate)
    
    def softchar_accept_matching_single_quote(self, scimoz, pos, style_info, candidate):
        return self._softchar_accept_match_outside_strings(scimoz, pos, style_info, candidate)
    
    def softchar_accept_matching_backquote(self, scimoz, pos, style_info, candidate):
        return self._softchar_accept_match_outside_strings(scimoz, pos, style_info, candidate)

    def _can_insert_soft_char_at_eol_or_before_ident(self, scimoz, nextCharPos, lineEndPos):
        """Don't insert a soft character if we're not at the end of the
        line and there's an ident char to the right.
        """
        # Accept if we're at the end of the line
        if nextCharPos == lineEndPos:
            return True
        # Accept if we aren't followed by an ident char
        return not isIdentRE.match(scimoz.getWCharAt(nextCharPos))

    def _can_insert_soft_char_at_eol_only(self, scimoz, nextCharPos, lineEndPos):
        """Allow only soft characters at the end of the line"""
        # Accept if we're at the end of the line
        if nextCharPos == lineEndPos:
            return True
        # Accept if we're followed by soft chars
        return scimoz.indicatorValueAt(_softCharDecorator, nextCharPos) != 0
    
    def determine_soft_char(self, ch, scimoz, charPos, style_info):
        """
        @param {string} ch - the character that was typed.
        @param {object} scimoz
        @param {int} charPos - position of the character ch
        @param {object} style_info

        Precondition: ch is in self.matchingSoftChars, so it's
        potentially matchable.
        
        This routine should not be overridden.  Use the
        softchar_accept_* API instead to override base-class behavior.
        """

        # Bug 92392:
        # If we aren't in a stream selection, don't emit soft chars
        # Also, in multi-selection mode, scimoz.selectionMode refers
        # to the main selection, so no soft chars if we have multiple selections
        if (scimoz.selectionMode != scimoz.SC_SEL_STREAM
            or scimoz.selections > 1):
            return None

        #1. First determine that the character isn't followed by an
        #   identifier character. (bug 70834)
        nextCharPos = scimoz.positionAfter(charPos)
        lineEndPos = scimoz.getLineEndPosition(scimoz.lineFromPosition(charPos))
        
        # Use one of the following acceptanceMethods, to determine
        # where soft chars are allowed: either only at end of line,
        # or either at end of line or before ident chars
        if self.prefset.getBooleanPref("enableSmartSoftCharactersInsideLine"):
            acceptanceMethod = self._can_insert_soft_char_at_eol_or_before_ident
        else:
            acceptanceMethod = self._can_insert_soft_char_at_eol_only
        if not acceptanceMethod(scimoz, nextCharPos, lineEndPos):
            return None

        #2. Now look for a callback.  If there is one, use its output, which might
        # be None, which means no soft chars will be inserted.        
        matchingCharInfo = self.matchingSoftChars[ch]
        if matchingCharInfo[1] is None:
            return matchingCharInfo[0]
        return (matchingCharInfo[1])(scimoz, charPos, style_info, matchingCharInfo[0])

    def _setupIndentCheckSoftChar(self):
        try:
            tuple = self.matchingSoftChars["{"]
            if tuple[1] is None:
                self.matchingSoftChars["{"] = (tuple[0],
                                               self._acceptUnlessNextLineIsIndented)
        except KeyError, ex:
            log.exception(ex)

    def _acceptUnlessNextLineIsIndented(self, scimoz, charPos, style_info, candidate):
        """
        Check to see if we have this condition:
        .... | .... |if (condition) <|>{
        .... | .... | .... single_statement;
        .... | .... |more code...
        
        The idea is when the user types a "{" at the caret, we check to see if
        we want to put a line containing an indented "}" under the following line.
        
        These are the following conditions for inserting a new line containing an
        indented close-brace.
        
        Terminology:
        * Current line: line containing the cursor and "{"
        * Next line: line under the current line
        * Brace-match line: line containing the "}" the *would* match the "{"
        
        1. We're at end of buffer, so insert a soft "}" immediately
        2. The next line isn't indented under the current line: emit a soft "}"
        3. If there is no current matching close-brace:
           3.1. The next line is at the end of the buffer, so wrap it
           3.2. If the line after the next line is indented w.r.t. the current line, do nothing
                Otherwise wrap the next line.
        4. The brace-match is *before* the current character: shouldn't happen, so do nothing
        5. The matching close-brace is on the next line: do nothing, as this is unusual coding style
        6. The matching close-brace's line isn't intended outside the current block, following usual style,
           so do nothing
        7. Either the line after the next line is the brace-match line, or the line after the
           brace-match line is indented outside the current block.  If so, we'll wrap the block.
           If not, we'll do nothing.  There is room for improvement here by walking back from
           the brace-match-line checking indentation levels and ignoring white-space/comment lines,
           but I think this is still hard to get correct 100%.  This approach gets the common use-case
           correct: converting an unbraced single-line statement to a braced, multi-line statement. 
        """
        currLineNo = scimoz.lineFromPosition(charPos)
        #log.debug("_acceptUnlessNextLineIsIndented: Called at pos %d, scimoz.currentPos = %d, line %d",
        #          charPos, scimoz.currentPos, currLineNo)
        if scimoz.getLineEndPosition(currLineNo) == scimoz.textLength:
            #log.debug("There are no further lines, do a soft match")
            return candidate # case 1
        currIndentLen = self._getIndentWidthForLine(scimoz, currLineNo)
        nextLineNo = currLineNo + 1
        nextIndentLen = self._getIndentWidthForLine(scimoz, nextLineNo)
        #log.debug("curr line indent(%r) = %d, next line indent(%d) = %r", currLineNo, currIndentLen,
        #          nextLineNo, nextIndentLen)
        if nextIndentLen <= currIndentLen:
            #log.debug("**** Add a soft char?")
            return candidate
    
        braceMatchPos = scimoz.braceMatch(charPos)
        #log.debug("braceMatch(%d) = %d, braceMatch(%d) = %d",
        #          charPos, braceMatchPos, scimoz.currentPos, scimoz.braceMatch(scimoz.currentPos))
        if braceMatchPos == -1:
            if scimoz.getLineEndPosition(nextLineNo) == scimoz.textLength:
                # The next line is the only line left in the buffer, so wrap it
                self._insertCloseBraceAfterLine(scimoz, currLineNo, nextLineNo, charPos) # case 3.1.
                return None
            targetLineNo = nextLineNo + 1
            targetIndentLen = self._getIndentWidthForLine(scimoz, targetLineNo)
            if targetIndentLen > currIndentLen:
                #log.debug("Looks like there is more than one line to wrap, so do it manually")
                # Don't wrap more than one line, but don't insert a soft char either - case 3.2-true
                pass
            else:
                self._insertCloseBraceAfterLine(scimoz, currLineNo, nextLineNo, charPos) # case 3.2-false.
            return None
        elif braceMatchPos <= charPos: # case 4
            # Shouldn't happen?
            assert False and "braceMatch('{') moved backwards"
            return None
        braceMatchLineNo = scimoz.lineFromPosition(braceMatchPos)
        if braceMatchLineNo <= nextLineNo:
            # Forget it, looks like there's a close brace already in place - # case 5.
            return None
        braceMatchIndentLen = self._getIndentWidthForLine(scimoz, braceMatchLineNo)
        #log.debug("braceMatchLineNo = %d, braceMatchIndentLen = %d", braceMatchLineNo, braceMatchIndentLen)
        if braceMatchIndentLen >= currIndentLen:
            # Forget it, looks like the outer closing brace is too deeply indented - case 6.
            return None
        if braceMatchLineNo == nextLineNo + 1 \
            or self._getIndentWidthForLine(scimoz, nextLineNo + 1) <= currIndentLen:
            # Both conditions indicate that there's exactly one line to wrap 
            self._insertCloseBraceAfterLine(scimoz, currLineNo, nextLineNo, charPos) # case 7
    
    def _insertCloseBraceAfterLine(self, scimoz, useIndentOfThisLineNo, insertTextAtEndOfLineNo, charPos):
        # If the indent of the line before that is >= the nextLine, insert it there
        textToInsert = (eollib.eol2eolStr[eollib.scimozEOL2eol[scimoz.eOLMode]]
                        + self._getRawIndentForLine(scimoz, useIndentOfThisLineNo)
                        + "}")
        scimoz.beginUndoAction()
        try:
            pos = scimoz.currentPos
            # No Unicode text here
            scimoz.insertText(scimoz.getLineEndPosition(insertTextAtEndOfLineNo), textToInsert)
            scimoz.gotoPos(pos)
            matchedPos = scimoz.braceMatch(charPos)
            if matchedPos != -1:
                scimoz.braceHighlight(charPos, matchedPos)
        finally:
            scimoz.endUndoAction()
            
    def supportsXMLIndentHere(self, scimoz, caretPos):
        if self.supportsSmartIndent == "XML":
            return self

    def test_scimoz_(self, scimoz):
        raise NotImplementedError("No tests for UDL languages defined")

    def lookForHotspots(self, scimoz):
        # here we'll look for common things like URLs
        pos = scimoz.currentPos
        curLineNo = scimoz.lineFromPosition(pos)
        lineStart = scimoz.positionFromLine(curLineNo)
        lineEnd = scimoz.getLineEndPosition(curLineNo)
        curLine = scimoz.getTextRange(lineStart, lineEnd)
        firstHit = curLine.find('http://')
        mask = int('1'*self.styleBits, 2)
        styleNum = int('1'*self.styleBits, 2)-1
        scimoz.styleSetHotSpot(styleNum, 1)
        scimoz.styleSetFore(styleNum, 0x666666)
        scimoz.styleSetBack(styleNum, 0xeeeeee)
        scimoz.styleSetBold(styleNum, 1)
        scimoz.setHotspotActiveUnderline(1)
        while firstHit != -1:
            start = firstHit
            end = start + len(curLine[firstHit:].split()[0])
            # Set up the style
            scimoz.startStyling(lineStart + start, mask);
            scimoz.setStyling(end-start, styleNum);
            curLine = curLine[end:]
            firstHit = curLine.find('http://')


class KoLanguageBaseDedentMixin(object):
    def __init__(self):
        # Override the defaults from KoLanguageBase
        self._dedent_chars = ":"   # Only when line starts with 'case' or 'default'
        self._indenting_statements = [u'case', u'default']
    
    _caseOrDefaultStmtRE = re.compile(r'^(\s*)(?:case\b.+|default)\s*:(.*)$')
    def getIndentBasedOnDedentChar(self, scimoz, charPos, style_info):
        """
        If current line matches ^\s+case.*:$ or default
        and the previous line matches ^\s+case\b or default
        do a dedent
        """
        currLineNo = self._statementStartingLineFromPos(scimoz, charPos-1, style_info)
        currLineStart = scimoz.positionFromLine(currLineNo)
        currLineEnd = scimoz.getLineEndPosition(currLineNo)
        currLine = scimoz.getTextRange(currLineStart, currLineEnd)
        m1 = self._caseOrDefaultStmtRE.match(currLine)
        if (not m1) or m1.group(2):
            # Don't accept if this isn't the first ":" on the line.
            return None
        prevLineNo = currLineNo - 1
        prevLineStart = scimoz.positionFromLine(prevLineNo)
        prevLineEnd = scimoz.getLineEndPosition(prevLineNo)
        prevLine = scimoz.getTextRange(prevLineStart, prevLineEnd)
        m2 = self._caseOrDefaultStmtRE.match(prevLine)
        if not m2:
            return None
        prevWhiteSequence = m2.group(1)
        prevWhiteLen = len(prevWhiteSequence)
        prevNonWhiteColumn = scimoz.getColumn(prevLineStart + prevWhiteLen)
        currWhiteLen = len(m1.group(1))
        currNonWhiteColumn = scimoz.getColumn(currLineStart + currWhiteLen)
        if currNonWhiteColumn > prevNonWhiteColumn:
            return prevWhiteSequence

def _findIndent(scimoz, chars, styles, comment_styles, tabWidth, defaultUsesTabs):
    """
    This code is fairly sophisticated, and a tad tricky.  Here's how it works.
    We're looking for an "indenting line" followed by an "indented line".
    Indenting lines are defined as lines that end in a special character in a special style,
    ignoring trailing whitespace and comments.  For example,
            if foo() { // asdasd
    is an indenting line in C++, but:
            if foo() // {
    is not, since the { character would not be styled as an 'indenting char'.

    Indented lines are lines that contain non-comment and non-whitespace characters
    which are indented by a positive amount compared to the indented line.  Thus
    in the code:

        [scriptable, uuid(96A8CC18-168B-4137-8435-E633D13F7925)]
        interface koILanguageService : nsISupports {
                // template interface for language services
        };
        
        [scriptable, uuid(29098AA5-7F16-4671-823D-FC0817250A7C)]
        interface koILanguage : nsISupports {
          readonly attribute string name;

    The _last_ line is the first valid 'indented' line, and so the computed
    indent is 2 (the first interface definition contains only comments, so is
    ignored.
  
    The code ignores indenting lines that are not followed by an indented line 
    
    The arguments are:
        scimoz:
            the scintilla object with the buffer being processed
        chars:
            a sequence of _unicode_ characters which are used in the
            specific language to indicate block openings (typically u'{')
        styles:
            a sequence of Scintilla style numbers which are valid for
            block-opening characters
        comment_styles:
            a sequence of Scintilla style numbers which corresponds
            to comments or other code to be ignored
        tabWidth:
            what a tab character should be counted as (almost always 8).
    
    At most the first 300 lines are looked at.
    
    As a side effect, the first 300 lines of the buffer will be 'colourised' if they
    are not already.
    """
    textLength = scimoz.length
    if textLength == 0:
        return 0, 0
    indenting = None
    # first, colourise the first 300 lines at most so we have
    # styling information.
    N = min(300, scimoz.lineCount)
    end = scimoz.getLineEndPosition(N - 1)
    if end < textLength:
        end = scimoz.positionFromLine(N)
    if scimoz.endStyled < end:
        scimoz.colourise(scimoz.endStyled, end)
    data = scimoz.getStyledText(0, end)
    # data is a list of (character, styleNo)
    tabcount = 0
    spacecount = 0

    for lineNo in range(N):
        # the outer loop tries to find the 'indenting' line.
        if not scimoz.getLineIndentation(lineNo+1): # skip unindented lines
            # check this line's indentation for leading tabs.
            lineStartPos = scimoz.positionFromLine(lineNo)
            if scimoz.getWCharAt(lineStartPos) in ' \t':
                lineEndPos = scimoz.getLineEndPosition(lineNo)
                if lineEndPos > lineStartPos:
                    line = scimoz.getTextRange(lineStartPos, lineEndPos)
                    blackPos = len(line) - len(line.lstrip())
                    if '\t' in line[:blackPos]:
                        tabcount += 1
                    elif blackPos >= tabWidth:
                        spacecount += 1
            continue
        lineEndPos = scimoz.getLineEndPosition(lineNo)
        if lineNo == N - 1 and lineEndPos == end:
            lineEndPos = scimoz.getPositionBefore(end)
        lineStartPos = scimoz.positionFromLine(lineNo)
        WHITESPACE = '\t\n\x0b\x0c\r '  # don't use string.whitespace (bug 81316)
        try:
            # we'll look for each character in the line, going from
            # the back, for an 'indenting' character
            for pos in range(lineEndPos, lineStartPos-1, -1):
                char = data[pos*2]
                if char in WHITESPACE: # skip whitespace
                    continue
                style = ord(data[pos*2+1])
                if style in comment_styles: # skip comments
                    continue
                if (char in chars) and (style in styles):
                    # we found that the first 'interesting'
                    # character from the right of the line is an
                    # indent-causing character
                    indenting = scimoz.getTextRange(lineStartPos, lineEndPos)
                    log.info("Found indenting line: %r" % indenting)
                    # look for an indented line after this line
                    guess, foundTabs = _findIndentedLine(scimoz,
                                                         N, lineNo, indenting,
                                                         comment_styles, tabWidth, data)
                    if guess is not None:
                        # if the indent is a divisor of the tab width, then we should check
                        # if there are tabs used for indentation
                        if tabWidth % guess == 0:
                            for lineNo in range(lineNo + 1, N):
                                lineStartPos = scimoz.positionFromLine(lineNo)
                                # skip lines that aren't indented at all
                                if scimoz.getWCharAt(lineStartPos) not in ' \t':
                                    continue
                                lineEndPos = scimoz.getLineEndPosition(lineNo)
                                line = scimoz.getTextRange(lineStartPos, lineEndPos)
                                blackPos = len(line) - len(line.lstrip())
                                if '\t' in line[:blackPos]:
                                    tabcount += 1
                                    break
                                elif blackPos >= tabWidth:
                                    spacecount += 1
                        return guess, tabcount > spacecount or (tabcount and defaultUsesTabs)
                    else:
                        # probably an empty block
                        raise _NextLineException()
                else:
                    # We've found a character which is not a block opener
                    # so this can't be an indenting line.
                    raise _NextLineException()
        except _NextLineException:
            continue
    log.info("Couldn't find indentation information from the file")
    return 0, 0

def _findIndentedLine(scimoz, N, lineNo, indenting, comment_styles, tabWidth, data):
    """
    This function looks through the 'scimoz' buffer until at most the line number
    'N' for a line which is 'indented' relative to the 'indenting' line, ignoring
    characters styled as one of the styles in 'comment_styles'.
    
    N points 1 past the last line to look at.
    """
    indentedLineNo = lineNo + 1
    guess = None
    textLength = scimoz.length
    WHITESPACE = '\t\n\x0b\x0c\r '  # don't use string.whitespace (bug 81316)
    for indentedLineNo in range(indentedLineNo, N):
        if not scimoz.getLineIndentation(indentedLineNo): # skip unindented lines
            continue
        lineEndPos = scimoz.getLineEndPosition(indentedLineNo)
        if lineEndPos >= textLength:
            # Bug in Scintilla:
            # lineEndPos(lastLine) == doc.textLength
            lineEndPos = textLength - 1 
        lineStartPos = scimoz.positionFromLine(indentedLineNo)
        # we want to skip characters that are just comments or just whitespace
        for pos in range(lineEndPos, lineStartPos-1, -1):
            char = data[pos*2]
            if char in WHITESPACE: # skip whitespace
                continue
            style = ord(data[pos*2+1])
            if style in comment_styles: # skip comments
                continue
            # We have an indenting and an indented.
            indented = scimoz.getTextRange(lineStartPos, lineEndPos)
            log.info("opener: %r" % indenting)
            log.info("indented: %r" % indented)
            raw, indentsmall, foundTabsInOpener = classifyws(indenting, tabWidth)
            raw, indentlarge, foundTabsInIndented = classifyws(indented, tabWidth)
            foundTabs = foundTabsInOpener or foundTabsInIndented
            guess = indentlarge - indentsmall
            # If the guess is reasonable, use it -- indents less than
            # 2 don't qualify.
            if guess > 1:
                return guess, foundTabs
            else:
                log.warn("Found non-positive guess")
                return None, None
    return None, None
    
# taken from IDLE
# Look at the leading whitespace in s.
# Return pair (# of leading ws characters,
#              effective # of leading blanks after expanding
#              tabs to width tabwidth)

def classifyws(s, tabwidth):
    foundTabs = 0
    raw = effective = 0
    for ch in s:
        if ch == ' ':
            raw = raw + 1
            effective = effective + 1
        elif ch == '\t':
            foundTabs = 1
            raw = raw + 1
            effective = (effective / tabwidth + 1) * tabwidth
        else:
            break
    return raw, effective, foundTabs

