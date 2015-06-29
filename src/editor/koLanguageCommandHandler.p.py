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

import os
from xpcom import components, nsError, ServerException, COMException
sci_constants = components.interfaces.ISciMoz
from xpcom.server import WrapObject, UnwrapObject
import scimozindent
import itertools
import logging
import re
import eollib
log = logging.getLogger('koLanguageCommandHandler')
indentlog = logging.getLogger('koLanguageCommandHandler.indenting')
#indentlog.setLevel(logging.DEBUG)
jumplog = logging.getLogger('koLanguageCommandHandler.jump')

from zope.cachedescriptors.property import Lazy as LazyProperty

"""
The generic command handler is appropriate for all languages.

  It handles things like:
    block selection
    brace matching and jumps to matching brace
    transpose
    ctrl-space
    indentation control
    
"""

def _is_header_line(scimoz, line):
    return scimoz.getFoldLevel(line) & scimoz.SC_FOLDLEVELHEADERFLAG

def _fold_level(scimoz, line):
    return scimoz.getFoldLevel(line) & scimoz.SC_FOLDLEVELNUMBERMASK

def _tabify_repl_func(text, tabwidth):
    raw, effective = classifyws(text, tabwidth)
    ntabs, nspaces = divmod(effective, tabwidth)
    return '\t' * ntabs + ' ' * nspaces + text[raw:]

def _untabify_repl_func(text, tabwidth):
    return text.expandtabs(tabwidth)

class GenericCommandHandler:
    _com_interfaces_ = [components.interfaces.koIViewController,
                        components.interfaces.nsIController,
                        components.interfaces.nsICommandController,
                        components.interfaces.nsIObserver,
                        components.interfaces.nsIDOMEventListener]
    _reg_desc_ = "Command Handler for All files"
    _reg_contractid_ = "@activestate.com/koGenericCommandHandler;1"
    _reg_clsid_ = "{B383592C-5343-4AA7-9419-04D1B34EC906}"
    
    def __init__(self):
        log.info("in __init__ for GenericCommandHandler")
        self._completeWordState = None
        self._view = None

    @LazyProperty
    def sysUtils(self):
        return components.classes["@activestate.com/koSysUtils;1"].\
            getService(components.interfaces.koISysUtils)
    @LazyProperty
    def _koHistorySvc(self):
        return components.classes["@activestate.com/koHistoryService;1"].\
                        getService(components.interfaces.koIHistoryService)

    def set_view(self, view):
        if view:
            self._view = view.QueryInterface(components.interfaces.koIScintillaView)
        else:
            self._view = None

    def get_view(self):
        return self._view

    def _is_cmd_fontFixed_enabled(self):
        return 1

    def _do_cmd_fontFixed(self):
        view = self._view
        view.alternateFaceType = not view.alternateFaceType
        view.prefs.setBooleanPref('editUseAlternateFaceType',
                                        not view.prefs.getBooleanPref('editUseAlternateFaceType'))

    def _is_cmd_viewWhitespace_enabled(self):
        return self._view.scimoz.viewWS

    def _do_cmd_viewWhitespace(self):
        self._view.scimoz.viewWS = not self._view.scimoz.viewWS

    def _is_cmd_viewLineNumbers_enabled(self):
        return self._view.scimoz.getMarginWidthN(0) > 0

    def _do_cmd_viewLineNumbers(self):
        sm = self._view.scimoz
        alreadyShowing = sm.getMarginWidthN(sm.MARGIN_LINENUMBERS) > 0
        if alreadyShowing:
            sm.setMarginWidthN(sm.MARGIN_LINENUMBERS, 0)
        else:
            # Make margin visible and adjust width appropriately.
            sm.setMarginWidthN(sm.MARGIN_LINENUMBERS, 1)
            sm.updateMarginWidths()

    def _is_cmd_viewIndentationGuides_enabled(self):
        return self._view.scimoz.indentationGuides

    def _do_cmd_viewIndentationGuides(self):
        sm = self._view.scimoz
        sm.indentationGuides = not sm.indentationGuides

    def _is_cmd_viewEOL_enabled(self):
        return self._view.scimoz.viewEOL

    def _do_cmd_viewEOL(self):
        sm = self._view.scimoz
        sm.viewEOL = not sm.viewEOL

    def _is_cmd_wordWrap_enabled(self):
        return self._view.scimoz.wrapMode

    def _do_cmd_wordWrap(self):
        sm = self._view.scimoz
        if sm.wrapMode == sm.SC_WRAP_NONE:
            sm.wrapMode = sm.SC_WRAP_WORD
        else:
            # Bug 97600:
            # Scintilla doesn't update scimoz.firstVisibleLine,
            # but it needs to point it to the docLine
            docFirstLine = sm.docLineFromVisible(sm.firstVisibleLine)
            sm.wrapMode = sm.SC_WRAP_NONE
            # Reset firstVisibleLine on the JS side where we can do a timeout
            self._view.onWrapModeOff(docFirstLine)

    def _resolveDiffPath(self, diff, diff_file, paths):
        """Return a resolved absolute and existing path for the given
        file path indicated in a diff.
        
        Compare with `views-diff.xml::_resolvePath()`. Because we are in
        Python code here we can't query the user. We'll attempt a few values
        for strip (i.e. the '-p' option to patch.exe), using the patch file's
        current directory to see if that works.
        TODO: This heuristic should be added to views-diff.xml as well.

        @param diff {difflibex.Diff} The parsed diff.
        @param diff_file {koIFileEx} for the diff/patch file (used for a cwd).
        @param paths {list} The possible path for this diff hunk.
        @returns An existing absolute path to which `hunk_path` is pointing;
            or None if it could not be found.
        """
        from os.path import normpath, split, dirname, join, exists, abspath, isabs
        
        for hunk_path in paths:
            if isabs(hunk_path):
                path = normpath(hunk_path)
                if exists(path):
                    return path
            elif diff_file and diff_file.isLocal:
                # If the hunk path is relative, try using the patch/diff file's
                # cwd with a few values for strip (aka `patch -p$strip`).
                cwd = diff_file.dirName
                subpath = normpath(hunk_path)
                for i in range(4):  # -p0 ... -p3
                    p = join(cwd, subpath)
                    if exists(p):
                        return p
                    try:
                        subpath = subpath.split(os.sep, 1)[1]
                    except IndexError:
                        break  # out of path segments
        return None

    def _is_cmd_jumpToCorrespondingLine_enabled(self):
        return self._view.languageObj.name == 'Diff'
    
    def _do_cmd_jumpToCorrespondingLine(self):
        # Better code for doing this exists in bindings/views-diff.xml. However,
        # that code may have to query the user for info so currently has to
        # be in JS. At some point we'll want to just have these smarts in one
        # place.
        import difflibex
        
        sm = self._view.scimoz
        diff = difflibex.Diff(sm.text)

        currentPosLine = sm.lineFromPosition(sm.currentPos)
        currentPosCol = sm.currentPos - sm.positionFromLine(currentPosLine)
        try:
            currentPosFilePath, currentPosFileLine, currentPosFileCol \
                = diff.file_pos_from_diff_pos(currentPosLine, currentPosCol)
        except difflibex.DiffLibExError, ex:
            log.warn("could not jump to corresponding line: %s", ex)
            return
        
        # Ensure can use that file path (normalized, not relative,
        # etc.)
        paths = diff.possible_paths_from_diff_pos(currentPosLine, currentPosCol)
        resolvedFilePath = self._resolveDiffPath(diff, self._view.koDoc.file, paths)
        if not resolvedFilePath:
            msg = "could not jump to corresponding line: `%s' does not exist" \
                  % currentPosFilePath
            _sendStatusMessage(msg, True)
            return
        
        if sm.anchor == sm.currentPos:
            openFileArg = "%s\t%s,%s" \
                          % (resolvedFilePath,
                             currentPosFileLine+1,
                             currentPosFileCol+1)
        else:
            anchorLine = sm.lineFromPosition(sm.anchor)
            anchorCol = sm.anchor - sm.positionFromLine(anchorLine)
            try:
                anchorFilePath, anchorFileLine, anchorFileCol \
                    = diff.file_pos_from_diff_pos(anchorLine, anchorCol)
            except difflibex.DiffLibExError, ex:
                log.warn("could not jump to corresponding line: %s", ex)
                return
            
            if anchorFilePath != currentPosFilePath:
                # The selection spans files. Just use the currentPos info.
                openFileArg = "%s\t%s,%s" \
                              % (resolvedFilePath,
                                 currentPosFileLine+1,
                                 currentPosFileCol+1)
            else:
                openFileArg = "%s\t%s,%s-%s,%s" \
                              % (resolvedFilePath,
                                 anchorFileLine+1,
                                 anchorFileCol+1,
                                 currentPosFileLine+1,
                                 currentPosFileCol+1)

        observerSvc = components.classes["@mozilla.org/observer-service;1"].\
                getService(components.interfaces.nsIObserverService)
        observerSvc.notifyObservers(None, 'open_file', openFileArg)

    def _do_cmd_transientMarkSet(self):
        self._view.transientMark = self._view.scimoz.currentPos

    def _do_cmd_transientMarkPop(self):
        self._view.transientMarkPop();

    def _do_cmd_transientMarkMoveBack(self):
        view = self._view
        sm = view.scimoz
        mark = view.transientMark
        if mark == -1:
            return
        self._koHistorySvc.note_curr_editor_loc(view)
        sm.anchor = sm.currentPos = mark
        view.rotateTransientMarkRing()
        sm.scrollCaret()

    def _do_cmd_cutRegion(self):
        view = self._view
        sm = view.scimoz
        mark = view.transientMark
        if mark == -1:
            return
        sm.anchor = mark
        sm.cut()
        sm.sendUpdateCommands("clipboard")        

    def _do_cmd_copyRegion(self):
        view = self._view
        sm = view.scimoz
        mark = view.transientMark
        if mark == -1:
            return
        if mark < sm.currentPos:
            startp, endp = mark, sm.currentPos
        else:
            startp, endp = sm.currentPos, mark
        sm.copyRange(startp, endp)
        sm.sendUpdateCommands("clipboard")

    def _do_cmd_selectHomeAbsolute(self):
        """
        Used by emacs keybinding Ctrl+Shift+A
        """
        view = self._view
        sm = view.scimoz
        currentPos = sm.currentPos
        lineStartPos = sm.positionFromLine(sm.lineFromPosition(currentPos))
        #XXX
        # See bug 33211 note on updating the transientMark on selection changes
        # view.transientMark = currentPos;
        sm.gotoPos(lineStartPos)
        sm.anchor = currentPos

    def _do_cmd_transientMarkExchangeWithPoint(self):
        view = self._view
        mark = view.transientMark
        if mark == -1:
            return
        try:
            view.transientMarkPop()
        except:
            log.exception("No transientMark to pop")
        sm = view.scimoz
        view.transientMark = view.scimoz.currentPos
        self._koHistorySvc.note_curr_editor_loc(view)
        sm.currentPos = sm.anchor = mark
        sm.scrollCaret()
        
    def _do_cmd_openLine(self):
        """ emacs keybinding: insert a newline here, position to
        left of newline after"""
        sm = self._view.scimoz
        currentPos = sm.currentPos
        eol = eollib.eol2eolStr[eollib.scimozEOL2eol[sm.eOLMode]]
        sm.insertText(sm.currentPos, eol)
        sm.gotoPos(currentPos)

    def _do_cmd_splitLine(self):
        """ emacs keybinding: insert a newline here with indentation
        up to the current spot.  Position the cursor at the end
        of the current line.
        """
        sm = self._view.scimoz
        currentPos = sm.currentPos
        column = sm.getColumn(currentPos)
        newIndent = scimozindent.makeIndentFromWidth(sm, column)
        eol = eollib.eol2eolStr[eollib.scimozEOL2eol[sm.eOLMode]]
        sm.insertText(sm.currentPos, eol + newIndent)
        sm.gotoPos(currentPos)

    def _do_cmd_deleteBlankLines(self):
        """ emacs keybinding: delete blank lines like so:
            On blank line, delete all surrounding blank lines, leaving just one.
            On isolated blank line, delete that one.
            On nonblank line, delete any immediately following blank lines.
            XXX: What to do if the selection isn't empty?
        """
        sm = self._view.scimoz
        currentPos = sm.currentPos
        currentLine = sm.lineFromPosition(currentPos)
        selectionStart = sm.selectionStart
        selectionEnd = sm.selectionEnd
        self._deleteBlankLines_needWrapUndo = True
        if selectionStart == selectionEnd:
            return self._do_cmd_deleteBlankLinesAtLine(sm, currentLine, currentPos)
        selectionStartLine = sm.lineFromPosition(selectionStart)
        selectionEndLine = sm.lineFromPosition(selectionEnd)
        if selectionStartLine == selectionEndLine:
            # Non-empty selection on same line: delete a line, and if the
            # current line isn't blank retain the selection
            selectionStartOffset = selectionStart - sm.positionFromLine(selectionStartLine)
            res = self._do_cmd_deleteBlankLinesAtLine(sm, currentLine, currentPos)
            finalCurrentLine = sm.lineFromPosition(sm.currentPos)
            newSelectionStart = sm.positionFromLine(finalCurrentLine) + selectionStartOffset
            sm.selectionStart = newSelectionStart
            sm.selectionEnd = newSelectionStart + (selectionEnd - selectionStart)
            return res
        # Zap the white-space in the selection.  Use global rules for
        # blank lines at start and end of selection.
        targetLine = selectionEndLine;
        self._deleteBlankLines_needWrapUndo = False
        needWrapUndo = True
        try:
            while targetLine >= selectionStartLine:
                if self._onBlankLine(sm, targetLine):
                    prevNonBlankLine = self._findPrevNonBlankLine(sm, targetLine - 1)
                    if needWrapUndo:
                        sm.beginUndoAction()
                        needWrapUndo = False
                    self._deleteBlankLines(sm, targetLine,
                                           sm.positionFromLine(targetLine),
                                           collapseSingle=False)
                    targetLine = prevNonBlankLine - 1
                else:
                    targetLine -= 1
        finally:
            if not needWrapUndo:
                sm.endUndoAction()
                
    def _findPrevNonBlankLine(self, sm, targetLine):
        """ return -1 if no blank line is found
        """
        while targetLine >= 0:
            if not self._onBlankLine(sm, targetLine):
                return targetLine
            targetLine -= 1
        return targetLine
        
    def _do_cmd_deleteBlankLinesAtLine(self, sm, currentLine, currentPos):
        if self._onBlankLine(sm, currentLine):
            return self._deleteBlankLines(sm, currentLine, currentPos)
        else:
            return self._deleteFollowingBlankLines(sm, currentLine, currentPos)
            
    def _onBlankLine(self, sm, currentLine):
        lineStart = sm.positionFromLine(currentLine)
        lineEnd = sm.getLineEndPosition(currentLine)
        lineText = sm.getTextRange(lineStart, lineEnd)
        return not lineText.strip()

    def _wrapReplaceAndGo(self, sm, replaceString, finalPos=-1):
        # Sanity check: verify we don't delete non-white-space
        sm.searchFlags = sm.SCFIND_REGEXP
        p = r"[^\s\t\r\n]"
        res = sm.searchInTarget(len(p), p)
        if res != -1:
            targettedText = sm.getTextRange(sm.targetStart, sm.targetEnd)
            log.error("Komodo Internal Error: found non-white-space char in purported run of white-space: char %d (%r) in %r",
                      res, targettedText[res], targettedText)
            return
        if self._deleteBlankLines_needWrapUndo:
            sm.beginUndoAction()
        try:
            sm.replaceTarget(len(replaceString), replaceString)
            if finalPos >= 0:
                sm.gotoPos(finalPos)
        finally:
            if self._deleteBlankLines_needWrapUndo:
                sm.endUndoAction()
    
    def _deleteBlankLines(self, sm, currentLine, currentPos, collapseSingle=True):
        prevLine = currentLine
        while prevLine > 0:
            if self._onBlankLine(sm, prevLine - 1):
                prevLine -= 1
            else:
                break
        numLines = sm.lineFromPosition(sm.length)
        nextLine = currentLine + 1
        while nextLine <= numLines:
            if self._onBlankLine(sm, nextLine):
                nextLine += 1
            else:
                break
        if prevLine == nextLine - 1 or prevLine == numLines - 1:
            if not collapseSingle:
                return
            # Delete isolated blank line
            if currentLine == numLines - 1:
                # Delete the last line of the buffer, end up at end
                # of previous line
                sm.targetStart = sm.positionFromLine(currentLine)
                sm.targetEnd = sm.length
                if currentLine == 0:
                    finalPos = 0
                else:
                    finalPos = sm.getLineEndPosition(currentLine - 1)
            elif currentPos == sm.length:
                if prevLine < currentLine:
                    # special case: the current line is empty,
                    # and at least one line before it is blank
                    sm.targetStart = sm.positionFromLine(prevLine)
                    sm.targetEnd = currentPos
                    finalPos = sm.targetStart
                else:
                    # On the start of the last line of the buffer,
                    # this line doesn't end in an EOL,
                    # previous line isn't blank
                    return
            else:
                lineStart = sm.positionFromLine(currentLine)
                # On last line, remove white-space, move to start
                nextLineStart = sm.positionFromLine(currentLine + 1)
                sm.targetStart = lineStart
                sm.targetEnd = nextLineStart
                finalPos = sm.getLineEndPosition(currentLine - 1)
            self._wrapReplaceAndGo(sm, "", finalPos)
            return

        # Distinguish the following:
        # Inner block of white-space => collapse to current
        sm.targetStart = sm.positionFromLine(prevLine)
        sm.targetEnd = sm.positionFromLine(nextLine)
        currLineStart = sm.positionFromLine(currentLine);
        currLine = sm.getTextRange(currLineStart,
                                   sm.positionFromLine(currentLine + 1))
        # Emacs stops at the start of this line, more useful to stop
        # at the same point in it.
        self._wrapReplaceAndGo(sm, currLine,
                               sm.targetStart + currentPos - currLineStart)
        
    def _deleteFollowingBlankLines(self, sm, currentLine, currentPos):
        numLines = sm.lineFromPosition(sm.length)
        firstCandidateLine = currentLine + 1
        nextLine = firstCandidateLine
        while nextLine <= numLines:
            if self._onBlankLine(sm, nextLine):
                nextLine += 1
            else:
                break
        if nextLine == firstCandidateLine:
            # The next line isn't blank
            return
        sm.targetStart = sm.positionFromLine(firstCandidateLine)
        if nextLine > numLines:
            sm.targetEnd = sm.length
        else:
            sm.targetEnd = sm.positionFromLine(nextLine)
        # Don't move anywhere
        self._wrapReplaceAndGo(sm, "")

    def _do_cmd_editReflow(self):
        """ Reflow -- currently only works for paragraphs in text documents
        needs to be tweaked for comments and strings in code.
        """
        
        scin = self._view.scimoz
        import reflow
        # First figure out what paragraphs the current selection spans.
        # Walk back to the first blank line or to the top of the
        # document.
        # first we move the starting 'position of interest' to the beginning
        # of the current line
        startLineNo = scin.lineFromPosition(scin.selectionStart)

        if 0: # I think Trent has convinced me it's a bad idea.
            # we will swallow lines back from our current position if
            # they're not empty
            while startLineNo and getLine(scin, startLineNo-1).strip():
                startLineNo -= 1

        scin.targetStart = scin.positionFromLine(startLineNo)

        if (scin.getColumn(scin.selectionEnd) == 0 and
            scin.selectionEnd != 0 and
            scin.selectionEnd != scin.selectionStart and
            not getLine(scin, scin.lineFromPosition(scin.selectionEnd)).strip()):
            # if our selection ends after the newline chars and the next
            # line is blank, we don't want to skip over that line and go
            # on to the next paragraph.
            #
            # in other words:
            #
            #   adsa<|asdasjdlakjdas
            #   asdasdsa
            #   |>
            #
            # is a case where we don't want to deal w/ line 3 above, but
            #
            #   <|>asdlkhas dkljas kldjalkdsj saldj
            #
            # we obviously want to deal with line 1.
            #
            scin.selectionEnd -= 1
            _steppedBack = True
        else:
            _steppedBack = False

        endLineNo = scin.lineFromPosition(scin.selectionEnd)

        if (scin.selectionEnd != scin.selectionStart and 
            scin.getColumn(scin.selectionEnd) == 0):
            # we don't really want to include that line by default
            endLineNo -= 1

        # let's find out what indents we're going to count as being part of
        # the last relevant paragraph.
        para = reflow.Para(reflow.Line(getLine(scin, endLineNo)))
        
        if scin.selectionEnd == scin.selectionStart:
            # We're going to reflow including lines that are part of the
            # paragraph being considered.  To figure that out, we look for
            # lines which, among other criteria, have the same styling
            # as the current line. The styling is derived from the last
            # _non-whitespace_ character in the line we're ending with.
            curStyle = scin.getStyleAt(scin.getLineEndPosition(endLineNo)-1)
    
            while 1:
                # if we reach end of document, stop going on
                if endLineNo+1 >= scin.lineCount:
                    break
                # if the next line contains styles (not in whitespace
                # characters) which aren't like the current style, then
                # don't include said line in reflowable region
                try:
                    for pos in range(scin.positionFromLine(endLineNo+1),
                                     scin.getLineEndPosition(endLineNo+1)):
                        c = scin.getWCharAt(pos)
                        s = scin.getStyleAt(pos)
                        if c in ' \t': continue
                        if s != curStyle:
                            #print "breaking", c,s
                            raise ValueError
                        #print "ok with", c
                except ValueError:
                    break
                # if the next line doesn't fit in to the current paragraph,
                # then stop.
                if not para.accept(reflow.Line(getLine(scin, endLineNo+1))):
                    break
                para.append(reflow.Line(getLine(scin, endLineNo+1)))
                endLineNo += 1
        scin.targetEnd = scin.getLineEndPosition(endLineNo)
        start = scin.positionFromLine(startLineNo)
        end = min(scin.textLength, scin.getLineEndPosition(endLineNo))
        
        # if we have whitespace to our left we'll want to make sure that we end
        # up with whitespace to our left
        hadWhitespaceToLeft = scin.anchor <= scin.currentPos and scin.getWCharAt(scin.currentPos-1) in ' \t'

        if end <= start:  # no point -- nothing to reflow
            return
        text = scin.getTextRange(start, end)
        
        # we want to find out where (relative to non-whitespace characters) the cursor
        # is _before_ the reflow, so we can try to maintain that after reflow.
        textBeforeCurrentPos = scin.getTextRange(scin.targetStart, scin.currentPos)
        textBeforeCurrentPosNoWS = ''.join([word.strip() for word in textBeforeCurrentPos.split()])
        numChars = len(textBeforeCurrentPosNoWS)

        # we now know what text to reflow.
        # we need the eol characters to use for reflowing
        eol = eollib.eol2eolStr[eollib.scimozEOL2eol[scin.eOLMode]]
        # boom
        # reflow doesn't know how to deal with tabs of non-8-space width
        # so we'll do a conversion here, then convert back after
        text = text.expandtabs(scin.tabWidth)
        reflowed = reflow.reflow(text, scin.edgeColumn, eol)
        if scin.useTabs:
            lines = reflowed.splitlines(1)
            for pos in range(len(lines)):
                line = lines[pos]
                if line:
                    raw, effective = classifyws(line, scin.tabWidth)
                    ntabs, nspaces = divmod(effective, scin.tabWidth)
                    lines[pos] = '\t' * ntabs + ' ' * nspaces + line[raw:]
            reflowed = ''.join(lines)
        orig = scin.getTextRange(scin.targetStart, scin.targetEnd)
        if orig == reflowed:
            return  # do nothing
        # replacing what we've come up with as a selection
        scin.replaceTarget(len(reflowed), reflowed)
        # now we look for where we want to put the cursor
        # we'll move N characters from the start of the range, where
        # N is 'numChars' as determined above.
        numCharsSkipped = 0
        i = 0
        WHITESPACE = '\t\n\x0b\x0c\r '  # don't use string.whitespace (bug 81316)
        while numCharsSkipped < numChars and i < len(reflowed):
            if reflowed[i] not in WHITESPACE:
                numCharsSkipped += 1
            i += 1
        if hadWhitespaceToLeft:
            i += 1
        scin.currentPos = scin.anchor = min(scin.textLength, scin.targetStart + i)
        if _steppedBack:
            # step forward to the next line
            scin.currentPos = scin.anchor = min(scin.textLength,
                                                scin.positionFromLine(scin.lineFromPosition(scin.currentPos)+1))
        scin.xOffset = 0

    def _do_cmd_editCenterVertically(self):
        # center the buffer on the cursor (vertically)
        scimoz = self._view.scimoz
        fvl = scimoz.firstVisibleLine
        vis_curLineNo = scimoz.visibleFromDocLine(scimoz.lineFromPosition(scimoz.currentPos))
        scimoz.lineScroll(0, (vis_curLineNo - fvl) - (scimoz.linesOnScreen // 2))

    def _do_cmd_editMoveCurrentLineToTop(self):
        # scroll the buffer so the current line is at the top
        scimoz = self._view.scimoz
        fvl = scimoz.firstVisibleLine
        vis_curLineNo = scimoz.visibleFromDocLine(scimoz.lineFromPosition(scimoz.currentPos))
        scimoz.lineScroll(0, vis_curLineNo - fvl)

    def isCommandEnabled( self, command_name ):
        # Result: boolean
        # In: param0: wstring
        meth = getattr(self, "_is_%s_enabled" % (str(command_name),), None)
        if meth is None:
            rc = 1
        else:
            rc = meth()
        #log.debug("koLanguageCommandHandler - isCommandEnabled '%s' -> %d", command_name, rc)
        return rc

    def supportsCommand( self, command_name ):
        # Result: boolean
        # In: param0: wstring
        rc = hasattr(self, "_do_" + command_name)
        #log.debug("koLanguageCommandHandler - SupportsCommand '%s' -> %d", command_name, rc)
        return rc

    def doCommand( self, command_name ):
        # Result: void - None
        # In: param0: wstring
        meth = getattr(self, "_do_" + command_name)
        try:
            # Some CommandHandler's do not have a wrapper, e.g. TerminalCommandHandler
            #if self.wrapper is not None:
            #    self.wrapper.beginBatchOperation()
            #try:
                meth()
            #finally:
                #if self.wrapper is not None:
                #    self.wrapper.endBatchOperation()
        except KeyboardInterrupt: # User cancelled a dialog.
            pass

    def doCommandWithParams(self, command_name, command_params):
        """
        nsICommandController::doCommandWithParams
        @param command_name {str} THe command to execute
        @param command_params {nsICommandParams} command parameters
        @returns None
        @note This assumes parameters with integer keys (starting from 0) are
            positional arguments, and all other parameters are keyword arguments
        """
        args = []
        kwargs = {}
        seen_keys = set()

        def get_param(name, val_type):
            """Get a single argument out of the nsICommandParams
                @param name {str} The parameter name
                @param val_type {int} The parameter type, one of the
                    nsICommandParams::e*Type enumerations as returned by
                    nsICommandParams::getValueType
                @returns The argument, converted depending on the type
                """
            if val_type == components.interfaces.nsICommandParams.eBooleanType:
                return command_params.getBooleanValue(name)
            elif val_type == components.interfaces.nsICommandParams.eLongType:
                return command_params.getLongValue(name)
            elif val_type == components.interfaces.nsICommandParams.eDoubleType:
                return command_params.getDoubleValue(name)
            elif val_type == components.interfaces.nsICommandParams.eWStringType:
                return command_params.getStringValue(name)
            elif val_type == components.interfaces.nsICommandParams.eISupportsType:
                return command_params.getISupportsValue(name)
            elif val_type == components.interfaces.nsICommandParams.eStringType:
                return command_params.getCStringValue(name)
            else:
                raise COMException(nsError.NS_ERROR_UNEXPECTED,
                                   "Unexpected parameter type %r for argument %r" % (val_type, name))

        # get positional arguments
        for i in itertools.count():
            key = str(i)
            try:
                val_type = command_params.getValueType(key)
            except COMException, e:
                # out of positional arguments, probably
                break
            args.append(get_param(key, val_type))
            seen_keys.add(key)

        # get keyword arguments
        command_params.first()
        while command_params.hasMoreElements():
            key = command_params.getNext()
            if key in seen_keys:
                # we've already seen this key (probably as a position argument)
                continue
            val_type = command_params.getValueType(key)
            kwargs[key] = get_param(key, val_type)

        # actually call the method
        meth = getattr(self, "_do_" + command_name)
        meth(*args, **kwargs)

    def _do_cmd_newlineExtra(self):
        self._do_cmd_newline(None, 1)

    def _do_cmd_newlineBare(self):
        self._do_cmd_newline('none', 0)

    def _do_cmd_newlineSame(self):
        self._do_cmd_newline('plain', 0)

    def codeintel_autocomplete_selected(self, position, text):
        self._finish_autocomplete(position)

    def _finish_autocomplete(self, start_pos):
        shouldAdjust = False
        # if we're closing a </ tag, then adjust it.
        # Closing a tag means "the selected autocomplete text is preceeded by
        # "</" (since the autocomplete is the tag name plus ">")
        sm = self._view.scimoz
        if sm.selections > 1:
            # TODO: if there are multiple selections present, there's no telling
            # which of them was emitted by the "codeintel_autocomplete_selected"
            # event. Thus `start_pos` is not guaranteed to be behind
            # `sm.currentPos`; this may cause memory access errors and crashes.
            # For now, don't bother to autocomplete multiple selections; the
            # method needs to be reworked anyway.
            return
        langObj = self._view.languageObj
        if start_pos > 1 and langObj.supportsXMLIndentHere(sm, sm.currentPos):
            text = sm.getStyledText(start_pos - 2, sm.currentPos)[0::2]
            # text is "</foo>", hopefully
            if text.startswith("</"):
                shouldAdjust = True
        if shouldAdjust:
            scimozindent.adjustClosingXMLTag(sm, langObj.isHTMLLanguage)
        sm.scrollCaret()
        return

    def _do_cmd_newline(self, indentStyle=None, continueComments=0):
        view = self._view
        sm = view.scimoz
        if indentStyle is None:
            indentStyle = view.prefs.getStringPref('editAutoIndentStyle')
            # allowExtraNewline deals with the default of adding an extra
            # newline when the user presses return between two chars.
            allowExtraNewline = True
        else:
            allowExtraNewline = indentStyle != "plain"
        sm.beginUndoAction()
        try:
            if indentStyle == 'none':
                indent = ''
                languageObj = None
            else:
                languageObj = UnwrapObject(view.languageObj)
                indent = languageObj.computeIndent(view.scimoz,
                                                   indentStyle,
                                                   continueComments)
            # Optionally clean up whitespace characters to the left of cursor if there
            # is something else there (leave whitespace-only lines alone, as otherwise
            # typing { <cr><cr> } up-arrow is frustrating.
            lineNo = sm.lineFromPosition(sm.currentPos)
            lineStart = sm.positionFromLine(lineNo)
            stuffToLeft = sm.getTextRange(lineStart, sm.currentPos)
            lineEnd = sm.getLineEndPosition(lineNo)
            matchedCharPosn = None
            finalSpot = None
            if stuffToLeft.strip():
                while (sm.currentPos > lineStart and
                       sm.getWCharAt(sm.positionBefore(sm.currentPos)) in ' \t'):
                    sm.deleteBack()
                # OPTIONALLY delete whitespace to the right of the 
                # current cursor position
                if 1: # XXX make a pref, give a UI.
                    while sm.getWCharAt(sm.currentPos) in ' \t':
                        sm.clear()
                
                # if only one char is to the right, we might want to do
                # some magic with where it goes (eg., next line or the line
                # after that)
                currentPos = sm.currentPos
                textToRight = sm.getTextRange(currentPos, lineEnd)
                if (textToRight
                    and languageObj is not None
                    and (len(textToRight) == 1
                         or self._remainingCharsAreSoft(sm, currentPos))):
                    openingChar = sm.getWCharAt(sm.positionBefore(currentPos))
                    matchedChar = languageObj.getMatchingChar(openingChar)
                    if (matchedChar
                        and openingChar != matchedChar # Don't do quote-like things
                        and matchedChar == sm.getWCharAt(currentPos)):
                        matchedCharPosn = currentPos
            else:
                currentPos = sm.currentPos
                
            if matchedCharPosn is not None:
                # Pressed return between an opening char and its matching close char
                sm.indicatorCurrent = components.interfaces.koILintResult.DECORATOR_SOFT_CHAR
                sm.indicatorClearRange(currentPos, lineEnd - currentPos);
                lang_svc, style_info = \
                    self._actualLangSvcAndStyleFromPos(languageObj, sm,
                                                       matchedCharPosn)
                finalSpot = lang_svc.insertElectricNewline(sm, indentStyle, matchedCharPosn,
                                                           allowExtraNewline, style_info)
            elif (languageObj is not None
                and currentPos > lineStart
                and currentPos < lineEnd
                and sm.getWCharAt(currentPos) not in ' \t'):
                lang_svc, style_info = \
                    self._actualLangSvcAndStyleFromPos(languageObj, sm,
                                                       sm.positionBefore(currentPos))
                finalSpot = lang_svc.insertInternalNewline_Special(sm, indentStyle, currentPos,
                                                                   allowExtraNewline, style_info)

            # If finalSpot is none do default indentation
            if finalSpot is not None:
                sm.gotoPos(finalSpot)
            else:
                sm.newLine()
                if indent:
                    sm.addText(self.sysUtils.byteLength(indent), indent) # consider using replaceTarget??
        finally:
            sm.endUndoAction()
            sm.chooseCaretX() # Keep up/down arrow on new currentPos: bug 92376

    def _actualLangSvcAndStyleFromPos(self, languageObj, scimoz, pos):
        if languageObj.isUDL():
            # find the actual language service
            return languageObj.getLangSvcAndStyleInfoFromStyle(scimoz.getStyleAt(pos))
        else:
            return languageObj, languageObj._style_info
            
    def _remainingCharsAreSoft(self, scimoz, currentPos):
        softCharDecorator = components.interfaces.koILintResult.DECORATOR_SOFT_CHAR
        endPos = scimoz.indicatorEnd(softCharDecorator, currentPos)
        lineEnd = scimoz.getLineEndPosition(scimoz.lineFromPosition(currentPos))
        return endPos == lineEnd
        
    def _getIndentWidthForLine(self, lineNo, upto=None):
        indent = self._getIndentForLine(lineNo, upto)
        return len(indent.expandtabs(self._view.scimoz.tabWidth))

    def _getIndentForLine(self, lineNo, upto=None):
        sm = self._view.scimoz
        lineStart = sm.positionFromLine(lineNo)
        if upto:
            lineEnd = min(upto, sm.getLineEndPosition(lineNo))
        else:
            lineEnd = sm.getLineEndPosition(lineNo)
        line = sm.getTextRange(lineStart, lineEnd)
        indentLength = len(line)-len(line.lstrip())
        return line[:indentLength]

    def _getIndentWidthFromIndent(self, indentstring):
        """ Given an indentation string composed of tabs and spaces,
        figure out how long it is (get the tabWidth from scimoz) """
        expandedstring = indentstring.expandtabs(self._view.scimoz.tabWidth)
        return len(expandedstring)

    def _getFoldLevel(self, line):
        """Return a fold level for the current line that guarantees that:
            - if at the top level, the fold level is zero
            - the deeper you are the higher the fold level
        It does *not* guarantee that:
            - a depth of three means then level is three
        """
        
        # _getFoldLevel depends on the document being styled.  It currently
        # is only called from _do_cmd_blockSelect below, which calls this within
        # loops, so the colourise call is done first rather than here.  topFoldLevel
        # is also set before using this function
        sm = self._view.scimoz
        foldLevel = sm.getFoldLevel(line)
        foldLevel &= sm.SC_FOLDLEVELNUMBERMASK
        foldLevel -= self.__topFoldLevel
        return foldLevel

    def _do_cmd_blockSelect(self):
        """Use the lexer's fold markers to increase the selection.
        If the current selection *is* a complete "fold block" then increase
        to the next fold block. If the current selection is *not* a complete
        fold block then select the fold block of the shallowest end of the
        selection.

        The logic is complicated somewhat because, the line preceeding a
        block at a certain level should be included in the block selection.
        For example, in the following code, if "Ctrl-B" is hit with the
        cursor on the "print 1" line, the "for element in mylist:" line
        should be included in the selection.

        LEVEL   CODE
        0       def foo(a):
        1           mylist = ["hello", 42, "there", 3.14159]
        1           while 1:
        2               for element in mylist:
        3                   print 1
        3                   if type(element) == type(""):
        4                       print "element %s is a string" % element
        1           print
        """
        #log.debug("----------------- BLOCK SELECT ---------------------")
        # Ensure cursor is at the start of the current selection (so we
        # don't have to deal with the reverse condition in the calculations
        # below.
        view = self._view
        sm = view.scimoz
        if sm.anchor < sm.currentPos:
            sm.anchor, sm.currentPos =\
                sm.currentPos, sm.anchor

        startLine = sm.lineFromPosition(sm.currentPos)
        endLine = sm.lineFromPosition(sm.anchor)
        lastLine = sm.lineFromPosition(sm.textLength-1)
        
        # if the lexer doesn't support folding, select all and get out of here fast.
        lexer = view.languageObj.getLanguageService(
            components.interfaces.koILexerLanguageService)
        if not sm.getPropertyInt("fold"):
            dialogproxy = components.classes['@activestate.com/asDialogProxy;1'].\
                          getService(components.interfaces.asIDialogProxy)
            bundle = components.classes["@mozilla.org/intl/stringbundle;1"].\
                     getService(components.interfaces.nsIStringBundleService).\
                     createBundle("chrome://komodo/locale/editor.properties")
            msg = bundle.GetStringFromName("block selection requires folding")
            dialogproxy.alert(msg)
            return

        # since we need all the fold data, ensure the entire document is styled
        if sm.endStyled < sm.length:
            sm.colourise(sm.endStyled, -1)

        self.__topFoldLevel = sm.getFoldLevel(0)
        self.__topFoldLevel &= sm.SC_FOLDLEVELNUMBERMASK

        # If the next line after the startLine is "deeper" then move the
        # startLine to there. See the doc string for why this is done.
        if (startLine != lastLine and
            self._getFoldLevel(startLine+1) > self._getFoldLevel(startLine)):
            startLine += 1

        # If there is a selection and selectionEnd is at the start of a line
        # then move up the end of the previous line because this simplifies
        # the subsequent logic.
        if (sm.selText != ""
            and sm.getColumn(sm.anchor) == 0):
            endLine -= 1
            sm.anchor = sm.getLineEndPosition(endLine)
        #log.debug("BLOCKSELECT: startLine=%d, endLine=%d, lastLine=%d",
        #          startLine, endLine, lastLine)

        # Determine the minimum fold level in the current selection.
        minFoldLevel = self._getFoldLevel(startLine)
        for line in range(startLine, endLine):
            #log.debug("BLOCKSELECT: foldLevel for line %d is: %x",
            #          line, self._getFoldLevel(line))
            minFoldLevel = min(minFoldLevel, self._getFoldLevel(line))
        #log.debug("BLOCKSELECT: minFoldLevel is %x", minFoldLevel)

        # Determine if the current selection is a complete fold block.
        # - selection start must be at the start of a line
        # - selection end must be at the end of a line
        # - start and end fold level must both be at the bound of the
        #   minFoldLevel
        if (sm.getColumn(sm.currentPos) == 0
            and sm.anchor == sm.getLineEndPosition(endLine)
            and (startLine == 0
                 or (self._getFoldLevel(startLine-1) < minFoldLevel
                     and self._getFoldLevel(startLine)
                         > self._getFoldLevel(startLine-1))
                )
            and (endLine == lastLine
                 or (self._getFoldLevel(endLine+1) < minFoldLevel
                     and self._getFoldLevel(endLine)
                         > self._getFoldLevel(endLine+1))
                )
           ):
            #log.debug("BLOCKSELECT: *is* a complete fold block")
            if startLine == 0:
                targetFoldLevel = 0
            else:
                targetFoldLevel = self._getFoldLevel(startLine-1)
        else:
            #log.debug("BLOCKSELECT: condition: start of selection on column 0? %s",
            #          sm.getColumn(sm.currentPos) == 0)
            #log.debug("BLOCKSELECT: condition: end of selection at eol? %s",
            #          sm.anchor == sm.getLineEndPosition(endLine))
            #log.debug("BLOCKSELECT: condition: startLine at minFoldLevel boundary? %s",
            #          (startLine == 0 or
            #           (self._getFoldLevel(startLine-1) < minFoldLevel
            #            and self._getFoldLevel(startLine)
            #                > self._getFoldLevel(startLine-1))))
            #log.debug("BLOCKSELECT: condition: endLine at minFoldLevel boundary? %s",
            #          (endLine == lastLine or
            #           (self._getFoldLevel(endLine+1) < minFoldLevel
            #            and self._getFoldLevel(endLine)
            #                > self._getFoldLevel(endLine+1))))
            #log.debug("BLOCKSELECT: is *not* a complete fold block")
            targetFoldLevel = minFoldLevel
        #log.debug("BLOCKSELECT: targetFoldLevel is %x", targetFoldLevel)

        # increase the selection to the target fold level
        if targetFoldLevel == 0:
            #log.debug("BLOCKSELECT: select all")
            sm.anchor = sm.textLength
            sm.currentPos = 0
            sm.ensureVisibleEnforcePolicy(0)
        else:
            # expand upwards
            while startLine > 0:  #XXX are line's in SciMoz 0- or 1-based???
                #log.debug("BLOCKSELECT: level(%x) up one line(%d) > target level(%x)?",
                #          self._getFoldLevel(startLine-1), startLine-1,
                #          targetFoldLevel)
                if self._getFoldLevel(startLine-1) >= targetFoldLevel:
                    startLine -= 1
                else:
                    break 
            # select the leading line in the block as well
            if startLine != 0:
                startLine -= 1

            # expand downwards
            while endLine < lastLine:
                #log.debug("BLOCKSELECT: level(%x) down one line(%d) > target level(%x)?",
                #          self._getFoldLevel(endLine+1), endLine+1,
                #          targetFoldLevel)
                if self._getFoldLevel(endLine+1) >= targetFoldLevel:
                    endLine += 1
                else:
                    break 

            # make the selection
            #log.debug("BLOCKSELECT: startLine=%d, endLine=%d",
            #          startLine, endLine)
            if endLine == lastLine:
                sm.anchor = sm.textLength
            else:
                sm.anchor = sm.positionFromLine(endLine+1)
            startLine = UnwrapObject(self._view.languageObj).findActualStartLine(sm, startLine)
            sm.currentPos = sm.positionFromLine(startLine)
            sm.ensureVisibleEnforcePolicy(startLine)
        sm.sendUpdateCommands("select")

    def _is_cmd_comment_enabled(self):
        commenter = self._view.languageObj.getLanguageService(
            components.interfaces.koICommenterLanguageService)
        return commenter is not None

    def _do_cmd_comment(self):
        view = self._view
        commenter = view.languageObj.getLanguageService(
            components.interfaces.koICommenterLanguageService)
        if not commenter:
            # not all languages have commentor services, and the commands
            # are not always updated to improve performance.  Log it as
            # an error
            log.error("%s does not have a commenter service!",
                      view.languageObj.name)
            return
        commenter.comment(view.scimoz)

    def _is_cmd_uncomment_enabled(self):
        commenter = self._view.languageObj.getLanguageService(
            components.interfaces.koICommenterLanguageService)
        return commenter is not None

    def _do_cmd_uncomment(self):
        view = self._view
        commenter = view.languageObj.getLanguageService(
            components.interfaces.koICommenterLanguageService)
        if not commenter:
            # not all languages have commentor services, and the commands
            # are not always updated to improve performance.  Log it as
            # an error
            log.error("%s does not have a commenter service!",
                      view.languageObj.name)
            return
        commenter.uncomment(view.scimoz)

    def _lastSelectedCharPosnFromLine(self, sm, lineNo):
        selEndPos = sm.getLineSelEndPosition(lineNo)
        lastCharPos = sm.getLineEndPosition(lineNo)
        return min(lastCharPos, selEndPos)

    def _do_cmd_convertCaseByLine(self, converter):
        """ Three reasons to convert text case one line at a time:
        1. Markers are preserved
        2. Non-ASCII characters are converted correctly (
           including slavic "title-case characters" like "<Lj>")
        3. The time overhead is only about 80% over the single call
           to scimoz.upperCase() or scimoz.lowerCase(), and that
           ends up as a call to a single C++ method.  In either case,
           we're looking at about 2 extra milliseconds/line.
        """
        import inspect
        converter_fn = None
        if inspect.isfunction(converter) or inspect.isbuiltin(converter):
            converter_fn = converter
        sm = self._view.scimoz
        currentPos = sm.currentPos
        anchor = sm.anchor
        selStart = sm.selectionStart
        selEnd = sm.selectionEnd
        selStartPos = sm.selectionStart
        selEndPos = sm.selectionEnd
        lineStart = sm.lineFromPosition(selStartPos)
        lineEnd = sm.lineFromPosition(selEndPos)
        sm.beginUndoAction()
        try:
            for lineNo in range(lineStart, lineEnd + 1):
                thisSelStartPos = sm.getLineSelStartPosition(lineNo)
                thisSelEndPos = self._lastSelectedCharPosnFromLine(sm, lineNo)
                text = sm.getTextRange(thisSelStartPos, thisSelEndPos)
                if converter_fn is not None:
                    fixedText = converter_fn(text)
                else:
                    fixedText = getattr(text, converter)()
                sm.targetStart = thisSelStartPos
                sm.targetEnd = thisSelEndPos
                sm.replaceTarget(len(fixedText), fixedText) # Length in chars, not bytes
                # Adjust the selection position according to how many bytes
                # were added or removed.
                selEnd += (self.sysUtils.byteLength(fixedText) -
                           self.sysUtils.byteLength(text))
        finally:
            sm.endUndoAction()
        sm.selectionStart = selStart
        sm.selectionEnd = selEnd
        
    def _convertCaseOfRectangularBlock(self, scimoz, converter):
        actualSelStart = anchor = scimoz.anchor
        actualSelEnd = currentPos = scimoz.currentPos
        if actualSelStart > actualSelEnd:
            (actualSelStart, actualSelEnd) = (actualSelEnd, actualSelStart)
        rectangularSelectionCaret = scimoz.rectangularSelectionCaret
        rectangularSelectionAnchor = scimoz.rectangularSelectionAnchor
        rectangularSelectionCaretVirtualSpace = scimoz.rectangularSelectionCaretVirtualSpace
        rectangularSelectionAnchorVirtualSpace = scimoz.rectangularSelectionAnchorVirtualSpace
        startLine = scimoz.lineFromPosition(actualSelStart)
        endLine = scimoz.lineFromPosition(actualSelEnd)
        targetStart = scimoz.targetStart
        targetEnd = scimoz.targetEnd
        scimoz.selectionMode = scimoz.SC_SEL_STREAM
        import inspect
        converter_fn = None
        if inspect.isfunction(converter) or inspect.isbuiltin(converter):
            converter_fn = converter
        scimoz.beginUndoAction()
        try:
            finalSelStart = finalSelEnd = None
            for i in range(startLine, endLine + 1):
                selStart = scimoz.getLineSelStartPosition(i)
                selEnd = scimoz.getLineSelEndPosition(i)
                if selStart == -1 or selEnd == -1:
                    # Do nothing
                    pass
                else:
                    if finalSelStart is None:
                        finalSelStart = selStart
                    finalSelEnd = selEnd
                    text = scimoz.getTextRange(selStart, selEnd)
                    if converter_fn is not None:
                        fixedText = converter_fn(text)
                    else:
                        fixedText = getattr(text, converter)()
                    scimoz.targetStart = selStart
                    scimoz.targetEnd = selEnd
                    scimoz.replaceTarget(len(fixedText), fixedText) # Length in chars, not bytes
        finally:
            scimoz.endUndoAction()
            scimoz.anchor = anchor
            scimoz.currentPos = currentPos
            if rectangularSelectionCaret < rectangularSelectionAnchor:
                scimoz.rectangularSelectionCaret = rectangularSelectionCaret
                scimoz.rectangularSelectionAnchor = rectangularSelectionAnchor
            else:
                scimoz.rectangularSelectionAnchor = rectangularSelectionAnchor
                scimoz.rectangularSelectionCaret = rectangularSelectionCaret
            scimoz.rectangularSelectionCaretVirtualSpace = rectangularSelectionCaretVirtualSpace
            scimoz.rectangularSelectionAnchorVirtualSpace = rectangularSelectionAnchorVirtualSpace
            scimoz.targetStart = targetStart
            scimoz.targetEnd = targetEnd
            # Don't know what else needs to be restored.


    def _do_cmd_convertUpperCase(self):
        scimoz = self._view.scimoz
        if scimoz.selectionMode == scimoz.SC_SEL_RECTANGLE:
            self._convertCaseOfRectangularBlock(scimoz, "upper")
        else:
            self._do_cmd_convertCaseByLine("upper")

    def _do_cmd_convertLowerCase(self):
        scimoz = self._view.scimoz
        if scimoz.selectionMode == scimoz.SC_SEL_RECTANGLE:
            self._convertCaseOfRectangularBlock(scimoz, "lower")
        else:
            self._do_cmd_convertCaseByLine("lower")

    def _do_cmd_convertFromHex(self):
        from binascii import unhexlify
        scimoz = self._view.scimoz
        if scimoz.selectionMode == scimoz.SC_SEL_RECTANGLE:
            self._convertCaseOfRectangularBlock(scimoz, unhexlify)
        else:
            self._do_cmd_convertCaseByLine(unhexlify)

    def _do_cmd_convertToHex(self):
        from binascii import hexlify
        scimoz = self._view.scimoz
        if scimoz.selectionMode == scimoz.SC_SEL_RECTANGLE:
            self._convertCaseOfRectangularBlock(scimoz, hexlify)
        else:
            self._do_cmd_convertCaseByLine(hexlify)

    def _is_cmd_selectToMatchingBrace_enabled(self):
        sm = self._view.scimoz
        matchingBrace = sm.braceMatch(sm.positionBefore(sm.currentPos))
        log.info("matchingBrace @ %d : %d", sm.currentPos, matchingBrace)
        if matchingBrace != -1: return 1 # we're there
        # also check to the right
        if sm.currentPos < sm.textLength:
            matchingBrace = sm.braceMatch(sm.currentPos)
            log.info("matchingBrace @ %d : %d", sm.currentPos, matchingBrace)
            return matchingBrace != -1
        else:
            log.info("matchingBrace: returning 0") 
            return 0

    _is_cmd_jumpToMatchingBrace_enabled = _is_cmd_selectToMatchingBrace_enabled

    def _do_cmd_selectToMatchingBrace(self):
        self._goMatchingBrace(1)

    def _do_cmd_jumpToMatchingBrace(self):
        self._goMatchingBrace(0)

    def _goMatchingBrace(self, select):
        sm = self._view.scimoz
        braceAtCaret, braceOpposite, isInside = self._findMatchingBracePosition(sm.currentPos)
        log.info("braceAtCaret: %d, braceOpposite: %d, isInside: %s", braceAtCaret, braceOpposite, isInside)
        # Convert the character positions into caret positions based on whether
        # the caret position was inside or outside the braces.
        if isInside:
            if braceOpposite > braceAtCaret:
                braceAtCaret += 1
            else:
                braceOpposite += 1
        else: # Outside
            if braceOpposite > braceAtCaret:
                braceOpposite += 1
            else:
                braceAtCaret += 1
        if braceOpposite >= 0:
            if not select:
                self._koHistorySvc.note_curr_editor_loc(self._view)
            self._ensureRangeVisible(braceOpposite, braceOpposite)
            if select:
                sm.anchor = braceAtCaret
                sm.currentPos = braceOpposite
            else:
                sm.anchor = braceOpposite
                sm.currentPos = braceOpposite
            # Ensure the caret is visible, bug:
            #   http://bugs.activestate.com/show_bug.cgi?id=43690
            sm.scrollCaret()
        sm.chooseCaretX()

    def _ensureRangeVisible(self, posStart, posEnd, enforcePolicy=1):
        sm = self._view.scimoz
        lineStart = sm.lineFromPosition(min(posStart, posEnd))
        lineEnd = sm.lineFromPosition(max(posStart, posEnd))
        for line in range(lineStart, lineEnd+1):
            if enforcePolicy:
                sm.ensureVisibleEnforcePolicy(line)
            else:
                sm.ensureVisible(line)

    # Find the brace that matches the brace before or after the given caret
    # position. The character before has precedence if it is a brace.
    # Returns three values: whether the caret is inside the braces,
    # and the indexes of the current and the matching brace.
    def _findMatchingBracePosition(self, caretPos, sloppy=1):
        view = self._view
        sm = view.scimoz
        actualLanguageObj = UnwrapObject(view.languageObj).supportsXMLIndentHere(sm, caretPos)
        if actualLanguageObj is not None:
            matchInfo = scimozindent.findMatchingTagPosition(
                sm, caretPos, actualLanguageObj)
            if matchInfo:
                atStart, stagi, stagf, etagi, etagf = matchInfo
                isInside = False
                if atStart:
                    braceAtCaret = caretPos
                    braceOpposite = etagf
                else:
                    braceAtCaret = caretPos
                    braceOpposite = stagi
                return braceAtCaret, braceOpposite, isInside
        # Otherwise try doing standard bracket-matching
        isInside = 0
        braceAtCaret = -1
        braceOpposite = -1
        charBefore = '\0'
        styleBefore = 0
        textLength = sm.textLength
        if caretPos > textLength:
            caretPos = textLength
        if (caretPos > 0) :
            charBefore = sm.getWCharAt(sm.positionBefore(caretPos))
            styleBefore = sm.getStyleAt(sm.positionBefore(caretPos))
        # Priority goes to character before caret
        if (charBefore
            and (view.languageObj.getBraceIndentStyle(charBefore, styleBefore)
                 or (charBefore in "[]{}()"))):
            braceAtCaret = caretPos - 1
        
        colonMode = 0
        if view.languageObj.name in ('Python', 'YAML') and charBefore == ':':
            braceAtCaret = caretPos - 1
            colonMode = 1

        isAfter = 1
        if sloppy and (braceAtCaret < 0) and \
           0 <= caretPos < textLength: # XXX check last edge condition
            # No brace found so check other side
            charAfter = sm.getWCharAt(caretPos)
            if charAfter in "[](){}":
                braceAtCaret = caretPos
                isAfter = 0

            if view.languageObj.name == 'Python' and ':' == charAfter:
                braceAtCaret = caretPos
                colonMode = 1
                
        if braceAtCaret >= 0:
            if colonMode:
                lineStart = sm.lineFromPosition(braceAtCaret)
                lineMaxSubord = sm.getLastChild(lineStart, -1)
                braceOpposite = sm.getLineEndPosition(lineMaxSubord)
            else:
                braceOpposite = sm.braceMatch(braceAtCaret)
                
        if braceOpposite > braceAtCaret:
            isInside = isAfter
        else:
            isInside = not isAfter
        return braceAtCaret, braceOpposite, isInside

    def _is_cmd_folding_enabled(self):
        return self._view.languageObj.foldable

    _is_cmd_foldExpand_enabled = _is_cmd_folding_enabled
    _is_cmd_foldExpandRecursive_enabled = _is_cmd_folding_enabled
    _is_cmd_foldExpandAll_enabled = _is_cmd_folding_enabled
    _is_cmd_foldCollapse_enabled = _is_cmd_folding_enabled
    _is_cmd_foldCollapseRecursive_enabled = _is_cmd_folding_enabled
    _is_cmd_foldCollapseAll_enabled = _is_cmd_folding_enabled
    _is_cmd_foldToggle_enabled = _is_cmd_folding_enabled

    def _do_cmd_foldExpand(self):
        sm = self._view.scimoz
        lineno = sm.lineFromPosition(sm.currentPos);
        if (sm.getFoldLevel(lineno) & sm.SC_FOLDLEVELHEADERFLAG) and \
            not sm.getFoldExpanded(lineno):
            sm.toggleFold(lineno)

    def _do_cmd_foldExpandRecursive(self):
        sm = self._view.scimoz
        lineno = sm.lineFromPosition(sm.currentPos);
        
        # if we are doing this on a header, we'll want the top level to
        # start at the level just inside the fold
        if _is_header_line(sm, lineno):
            if not sm.getFoldExpanded(lineno):
                sm.toggleFold(lineno)
            lineno += 1
        # skip non-header top-level lines
        elif _fold_level(sm, lineno) == sm.SC_FOLDLEVELBASE:
            return

        # we're going to unfold everything under this level
        origlevel = _fold_level(sm, lineno)

        line_count = sm.lineCount  # Bug 82524 defensive check
        while (lineno < line_count and _fold_level(sm, lineno) >= origlevel):
            if _is_header_line(sm, lineno) and not sm.getFoldExpanded(lineno):
                sm.toggleFold(lineno)
            lineno += 1

    def _do_cmd_foldExpandAll(self):
        sm = self._view.scimoz
        for lineno in range(0, sm.lineCount):
            if (sm.getFoldLevel(lineno) & sm.SC_FOLDLEVELHEADERFLAG) and \
                not sm.getFoldExpanded(lineno):
                    sm.toggleFold(lineno)

    def _do_cmd_foldCollapse(self):
        sm = self._view.scimoz
        lineno = sm.lineFromPosition(sm.currentPos)
        while not (sm.getFoldLevel(lineno) & sm.SC_FOLDLEVELHEADERFLAG):
            if lineno == 0 or not sm.getFoldExpanded(lineno):
                return
            lineno -= 1
        sm.toggleFold(lineno)
        sm.gotoLine(lineno)

    def _do_cmd_foldCollapseAll(self):
        sm = self._view.scimoz
        if sm.endStyled < sm.length:
            sm.colourise(sm.endStyled,-1)
        for lineno in range(0, sm.lineCount):
            if (sm.getFoldLevel(lineno) & sm.SC_FOLDLEVELHEADERFLAG) and \
                sm.getFoldExpanded(lineno):
                sm.toggleFold(lineno)
        
    def _do_cmd_foldCollapseRecursive(self):
        sm = self._view.scimoz
        lineno = sm.lineFromPosition(sm.currentPos);

        if _fold_level(sm, lineno) == sm.SC_FOLDLEVELBASE:
            if not _is_header_line(sm, lineno):
                return
        else:
            # search up to the header
            while not _is_header_line(sm, lineno):
                if lineno == 0:
                    return
                lineno -= 1
        
        # get the last line visible in this fold and go up from there
        lastchild = sm.getLastChild(lineno, -1)
        lines = range(lineno, lastchild)
        lines.reverse()
        
        # close em up
        for this_lineno in lines:
            if _is_header_line(sm, this_lineno) and sm.getFoldExpanded(this_lineno):
                sm.toggleFold(this_lineno)
        sm.gotoLine(lineno)

    def _do_cmd_foldToggle(self):
        sm = self._view.scimoz
        lineno = sm.lineFromPosition(sm.currentPos)
        if (sm.getFoldLevel(lineno) & sm.SC_FOLDLEVELHEADERFLAG):
            if not sm.getFoldExpanded(lineno):
                sm.toggleFold(lineno)
            else:
                self._do_cmd_foldCollapse()

    def _asktabwidth(self):
        try:
            tabwidth = self._view.prefs.getLongPref('tabWidth')
            if tabwidth != 0:
                return tabwidth
        except COMException, ex:
            pass
        dialogproxy = components.classes['@activestate.com/asDialogProxy;1'].\
            getService(components.interfaces.asIDialogProxy)
        bundle = components.classes["@mozilla.org/intl/stringbundle;1"].\
                 getService(components.interfaces.nsIStringBundleService).\
                 createBundle("chrome://komodo/locale/editor.properties")
        msg = bundle.GetStringFromName("tabWidthBetween0and16.message")
        value = dialogproxy.prompt(msg, "8", "OK", None)
        if value is not None:
            return int(value)
        else:
            return value

    def _start_single_char_replacement(self, scimoz, restorePos):
        restoreLine = scimoz.lineFromPosition(restorePos)
        restoreCol = scimoz.getColumn(restorePos)
        prevPos = scimoz.positionBefore(restorePos)
        prevChar = scimoz.getTextRange(prevPos, restorePos)
        scimoz.targetStart = prevPos
        scimoz.targetEnd = restorePos
        scimoz.replaceTarget(len(prevChar), prevChar)
        return restoreLine, restoreCol

    def _finish_single_char_replacement(self, scimoz, restoreLine, restoreCol):
        restorePos = scimoz.positionAtColumn(restoreLine, restoreCol)
        prevPos = scimoz.positionBefore(restorePos)
        prevChar = scimoz.getTextRange(prevPos, restorePos)
        scimoz.targetStart = prevPos
        scimoz.targetEnd = restorePos
        scimoz.replaceTarget(len(prevChar), prevChar)


    def _marker_preserving_tabify(self, replFunc):
        scimoz = self._view.scimoz
        if scimoz.length == 0:
            return
        tabwidth = self._asktabwidth()
        if tabwidth is None: return
        # bug 86400: Preserve markers by changing only one line at a time.
        # Also, make a dummy change so an undo will
        # put the cursor at its current location.  (See bug 75059)
        # 
        # Note that untabify acts on all tabs in a line,
        # while tabify acts only on the leading spaces.
        if scimoz.selectionStart == scimoz.selectionEnd:
            # New for 7.0: tabify the full buffer
            lineStart = 0
            lineEndPlusOne = scimoz.lineCount
            restorePos = scimoz.currentPos
            if restorePos == 0:
                restorePos = scimoz.positionAfter(0)
            lineStartFunc = scimoz.positionFromLine
            lineEndFunc = scimoz.getLineEndPosition
        else:
            lineStart = scimoz.lineFromPosition(scimoz.selectionStart)
            lineEndPlusOne = scimoz.lineFromPosition(scimoz.selectionEnd) + 1
            restorePos = scimoz.getLineSelStartPosition(lineStart)
            if restorePos == 0:
                restorePos = scimoz.positionAfter(0)
            lineStartFunc = scimoz.getLineSelStartPosition
            lineEndFunc = scimoz.getLineSelEndPosition

        scimoz.beginUndoAction()
        origTargetStart = scimoz.targetStart
        origTargetEnd = scimoz.targetEnd
        try:
            restoreLine, restoreCol = self._start_single_char_replacement(scimoz, restorePos)
            for lineNum in range(lineStart, lineEndPlusOne):
                posStart = lineStartFunc(lineNum)
                if posStart == -1:
                    # Could happen in rectangular selections
                    continue
                posEnd   = lineEndFunc(lineNum)
                #if posEnd == -1:
                #    # Can we have posStart > -1, posEnd == -1?  Seems unlikely
                #    continue
                if posStart == posEnd:
                    # Empty line selection
                    continue
                selText  = scimoz.getTextRange(posStart, posEnd)
                replText = replFunc(selText, tabwidth)
                if replText != selText:
                    scimoz.targetStart = posStart
                    scimoz.targetEnd = posEnd
                    scimoz.replaceTarget(len(replText), replText)
        finally:
            try:
                self._finish_single_char_replacement(scimoz, restoreLine, restoreCol)
                scimoz.targetStart = origTargetStart
                scimoz.targetEnd = origTargetEnd
            finally:
                scimoz.endUndoAction()

    def _do_cmd_tabify(self):
        self._marker_preserving_tabify(_tabify_repl_func)

    def _do_cmd_untabify(self):
        self._marker_preserving_tabify(_untabify_repl_func)

    def _do_cmd_backSmart(self):
        view = self._view
        sm = view.scimoz
        # if the pref is off, just do a regular delete
        if (sm.currentPos != sm.anchor or
            not view.prefs.getBooleanPref('editBackspaceDedents')):
            sm.deleteBack()
            return
        # If there is only whitespace to the left of us (on the current line), we delete enough characters
        #    to do a proper alignment ( this is currently done by IDLE, and works well w.r.t. tabs, spaces, etc.
        # Else we just do a regular backspace.
        lineNo = sm.lineFromPosition(sm.currentPos)
        lineStart = sm.positionFromLine(lineNo)
        before = sm.getTextRange(lineStart, sm.currentPos)
        if not before or before.strip() != '':
            # we're either at the beginning of the line or
            # somewhere in the line with text to our left -- just do a backspace.
            sm.deleteBack()
            return
        # the following is taken from idle (with variable renamings)
        # here we've got only whitespace to our left.
        # Delete whitespace left, until hitting a real char or closest
        # preceding virtual tab stop.
        # Ick.  It may require *inserting* spaces if we back up over a
        # tab character!  This is written to be clear, not fast.
        tabwidth = sm.tabWidth
        indentwidth = sm.indent
        have = len(before.expandtabs(tabwidth))
        assert have > 0
        want = int((have - 1) / indentwidth) * indentwidth
        ncharsdeleted = 0
        while 1:
            before = before[:-1]
            ncharsdeleted = ncharsdeleted + 1
            have = len(before.expandtabs(tabwidth))
            if have <= want or before[-1] not in " \t":
                break
        sm.beginUndoAction()
        try:
            for i in range(ncharsdeleted):
                sm.deleteBack()
            if have < want:
                inserted = ' ' * (want - have)
                sm.replaceSel(inserted)
        finally:
            sm.endUndoAction()

    def _insertIndent(self):
        sm = self._view.scimoz
        indent = sm.indent
        if indent <= 0:
            log.warn("scimoz indent is %d - that should never happen", indent)
            indent = self._view.prefs.getLong('indentWidth', 4)
            if indent <= 0:
                log.warn("indentWidth pref is %d - that should never happen", indent)
                indent = 4
            sm.indent = indent
        currentLineNo = sm.lineFromPosition(sm.currentPos)
        lineStart = sm.positionFromLine(currentLineNo)
        toLeft = sm.getTextRange(lineStart, sm.currentPos)
        if not toLeft.strip(): # we've got nothing but whitespace to our left:
            currentIndentWidth = self._getIndentWidthForLine(currentLineNo,
                                                            sm.currentPos)
            numIndents, extras = divmod(currentIndentWidth, indent)
            numIndents += 1
            newIndentWidth = numIndents * indent
            newIndent = scimozindent.makeIndentFromWidth(sm, newIndentWidth)
            sm.anchor = sm.positionFromLine(currentLineNo)
            sm.replaceSel(newIndent)
        else:
            # this isn't quite what vs.net does -- vs.net converts
            # all of the whitespace around the cursor to tabs
            # if appropriate
            startCol = sm.getColumn(sm.currentPos)
            numIndents, extras = divmod(startCol, indent)
            numIndents += 1
            targetCol = numIndents * indent
            if sm.useTabs:
                sm.replaceSel('\t')
            else:
                sm.replaceSel(' ' * (targetCol - startCol))
        sm.scrollCaret() # Ensure caret's visible: bug 91572

    def _insertDedent(self):
        sm = self._view.scimoz
        startCol = sm.getColumn(sm.currentPos)
        if sm.indent == 0:
            log.error("scimoz indent was 0, should never happen")
            return
        numIndents, extras = divmod(startCol, sm.indent)
        if numIndents and not extras:
            numIndents -= 1
        targetCol = numIndents * sm.indent
        sm.beginUndoAction()
        try:
            while (sm.getColumn(sm.currentPos) > targetCol and
                   sm.getWCharAt(sm.positionBefore(sm.currentPos)) in ' \t'):
                sm.deleteBack()
            curCol = sm.getColumn(sm.currentPos)
            if curCol < targetCol:
                d = targetCol-curCol
                sm.addText(d, d*' ')
        finally:
            sm.endUndoAction()

    def _do_cmd_dedent(self):
        # Do the indentation and then reset the x-caret if the
        # pref and the action call for it
        self._wrap_indent_dedent(self._continue_cmd_dedent)

    def _wrap_indent_dedent(self, indent_func):
        view = self._view
        sm = view.scimoz
        x_pos_changed = indent_func(view, sm)
        if x_pos_changed and self._view.prefs.getBooleanPref("repositionCaretAfterTab"):
            # See bug 93681 (asks for pre-v7 behavior, where tab doesn't change caret)
            # and bug 95409 (asks that tabbing repositions caret horizontally)
            sm.chooseCaretX()

    def _continue_cmd_dedent(self, view, sm):
        # Do tab autocompletion, assuming it's in progress.
        if sm.autoCActive():
            sm.autoCComplete()
            sm.scrollCaret()
            return False

        if (sm.currentPos == sm.anchor
            and self._try_complete_word(sm, view)
            and self._doCompleteWord(1)):
            return False

        selectionStartLine = sm.lineFromPosition(sm.selectionStart)
        endOfSelectionStartLine = sm.getLineEndPosition(selectionStartLine)
        selectionEndLine = sm.lineFromPosition(sm.selectionEnd)
        startColumn = sm.getColumn(sm.selectionStart)

        # Do we have a selection?  If no, then it's 'insert a backwards tab'
        if sm.currentPos == sm.anchor and sm.selectionMode != sm.SC_SEL_LINES:
            if startColumn == 0:
                sm.currentPos = endOfSelectionStartLine
                self._regionShift(-1)
                sm.currentPos = sm.anchor
            else:
                self._insertDedent()
            return True

        # If we have a selection, we first figure out if it's within-line or
        # either whole-line or multi-line.
        
        if (selectionStartLine != selectionEndLine or
            sm.selectionMode == sm.SC_SEL_LINES or
            (startColumn == 0 and sm.selectionEnd == endOfSelectionStartLine)):
            self._regionShift(-1)
        else:
            self._insertDedent()
        return True

    def _do_cmd_completeWord(self):
        self._doCompleteWord(0)

    def _do_cmd_completeWordBack(self):
        self._doCompleteWord(1)

    def _doCompleteWord(self, backwards):
        # adapted from IDLE's AutoExpand code, with the additional
        # tweak of 'going backwards'
        sm = self._view.scimoz
        curinsert = sm.currentPos
        lineNo = sm.lineFromPosition(sm.currentPos)
        startofLinePos = sm.positionFromLine(lineNo)
        endofLinePos = sm.getLineEndPosition(lineNo)
        curline = sm.getTextRange(startofLinePos, endofLinePos)
        if not self._completeWordState:
            words = self._getwords()
            index = 0
        else:
            words, index, insert, line = self._completeWordState
            if insert != curinsert or line != curline:
                words = self._getwords()
                index = 0
        if not words:
            return False
        word = self._getprevword()
        sm.anchor = sm.currentPos - self.sysUtils.byteLength(word)
        sm.replaceSel('')
        if backwards:
            newword = words[(index-2)  % len(words)]
            index = (index - 1) % len(words)
        else:
            newword = words[index]
            index = (index + 1) % len(words)
        sm.replaceSel(newword)
        curinsert = sm.currentPos
        lineNo = sm.lineFromPosition(sm.currentPos)
        startofLinePos = sm.positionFromLine(lineNo)
        endofLinePos = sm.getLineEndPosition(lineNo)
        curline = sm.getTextRange(startofLinePos, endofLinePos)
        
        self._completeWordState = words, index, curinsert, curline
        sm.scrollCaret()
        return True

    def _getwords(self):
        sm = self._view.scimoz
        # this is where we would do magic to look through other buffers
        word = self._getprevword()
        if not word:
            return []
        before = sm.getTextRange(0, sm.currentPos)
        wbefore = re.findall(r"\b" + word + r"\w+\b", before, re.UNICODE)
        del before
        after = sm.getTextRange(sm.currentPos, sm.textLength)
        wafter = re.findall(r"\b" + word + r"\w+\b", after, re.UNICODE)
        del after
        if not wbefore and not wafter:
            return []
        words = []
        dict = {}
        # search backwards through words before
        wbefore.reverse()
        for w in wbefore:
            if dict.get(w):
                continue
            words.append(w)
            dict[w] = w
        # search onwards through words after
        for w in wafter:
            if dict.get(w):
                continue
            words.append(w)
            dict[w] = w
        words.append(word)
        return words

    _unicode_word_char_re = re.compile(r'\w', re.UNICODE)
    _unicode_last_word_re = re.compile(r'(\w*)$', re.UNICODE)

    def _getprevword(self):
        sm = self._view.scimoz
        curinsert = sm.currentPos
        lineno = sm.lineFromPosition(curinsert)
        startofLinePos = sm.positionFromLine(lineno)
        line = sm.getTextRange(startofLinePos, curinsert)
        return self._unicode_last_word_re.search(line).group(1)

    def _handle_tabstop(self):
        return self._view.moveToNextTabstop()

    def _try_complete_word(self, sm, view):
        return (sm.currentPos > 0
                and view.prefs.getBooleanPref('editTabCompletes')
                and self._unicode_word_char_re.match(sm.getWCharAt(sm.positionBefore(sm.currentPos))))

    def _visible_tabstop_in_sight(self, sm, selectionEnd):
        koILintResult = components.interfaces.koILintResult
        for ts in range(koILintResult.DECORATOR_TABSTOP_TS1,
                        koILintResult.DECORATOR_TABSTOP_TS5 + 1): #inclusive
            if sm.indicatorEnd(ts, selectionEnd):
                return True
        return False
    
    def _do_cmd_indent(self):
        # Do the indentation and then reset the x-caret if the
        # pref and the action call for it
        self._wrap_indent_dedent(self._continue_cmd_indent)
            
    def _continue_cmd_indent(self, view, sm):
        """
        Return true if we should consider resetting the CaretX
        Return false otherwise.
        """
        
        # Bug 99067: If we have a multi-line selection and the user presses
        # tab, favor indent over moving to a tabstop
        selectionStart = sm.selectionStart
        selectionEnd = sm.selectionEnd
        selectionStartLine = sm.lineFromPosition(selectionStart)
        selectionEndLine = sm.lineFromPosition(selectionEnd)
        
        # If there's a visible tabstop within sight, go for it
        
        if ((selectionStartLine == selectionEndLine
             or self._visible_tabstop_in_sight(sm, selectionEnd))
                and self._handle_tabstop()):
            return False
        
        if selectionStart == selectionEnd and sm.selectionMode != sm.SC_SEL_LINES:
            if self._try_complete_word(sm, view) and self._doCompleteWord(0):
                return False
    
            # Do we have a selection?  If no, then it's 'insert a tab'
            self._insertIndent()
            return True
        
        # Three kinds of selections:
        # 1: Multi-line rectangular or thin line: insert tab at each caret/replace each sel with a tab
        # 2: Multi-line "regular" selection: shift
        # 3: Complete single line is selected: shift
        # 4: Partial-line selection: replace with a tab
        # 5: No selection: insert an indent
        
        startColumn = sm.getColumn(selectionStart)
        endOfSelectionStartLine = sm.getLineEndPosition(selectionStartLine)
        if (selectionStartLine != selectionEndLine):
            if sm.selectionMode in (sm.SC_SEL_RECTANGLE, sm.SC_SEL_THIN):
                # Whether we're in thin or rectangle, insert a tab at
                # each spot
                sm.tab()
                return True
            self._regionShift(1)
            return True
        if startColumn == 0 and sm.selectionEnd == endOfSelectionStartLine:
            self._regionShift(1)
            return True

        self._insertIndent()
        return True

    def _regionShift(self, shift):
        """ This code shifts regions of text left or right depending on the
        sign of 'shift' (which should be +1 for a rightward shift or
        -1 for a leftward shift
        
        First we adjust the region (selection) to consist only of whole lines.
        
        Then we look for the delta in number of spaces that should be applied
        to the first line which has a non-zero indent.
        
        Then we apply that delta to each line in the region, ensuring that
        the indentations that result respect the use of tabs as specified
        in the widget
        """
        sm = self._view.scimoz
        indentlog.info("doing _regionShift by shift: %s", shift)
        # first adjust the selection to span full lines.
        anchorFirst = True
        anchor = sm.anchor
        currentPos = sm.currentPos
        if anchor < currentPos:
            startPos, endPos = anchor, currentPos
        else:
            anchorFirst = False
            startPos, endPos = currentPos, anchor
        startPosColumn = sm.getColumn(startPos)
        endPosColumn = sm.getColumn(endPos)
        startLineNo = sm.lineFromPosition(startPos)
        endLineNo = sm.lineFromPosition(endPos)
        ignoreEndLine = False
        if sm.selectionMode != sm.SC_SEL_LINES and endPosColumn == 0:
            # The end selection position is at the start of a line, which
            # means this end line should not be indented.
            endLineNo -= 1
            ignoreEndLine = True
        # Update the start and end positions to work on whole lines.
        startPos = sm.positionFromLine(startLineNo)
        endPos = sm.getLineEndPosition(endLineNo)

        # figure out what delta we need to apply to the first line
        for line in range(startLineNo, max(endLineNo, startLineNo+1)):
            currentIndentWidth = self._getIndentWidthForLine(line)
            if shift == 1 or currentIndentWidth:
                break
        if currentIndentWidth == 0 and shift == -1:
            return # nothing to do, nothing's indented!
        numIndents, extras = divmod(currentIndentWidth, sm.indent)
        if shift == 1:
            numIndents += 1
        elif shift == -1 and numIndents and not extras:
            numIndents -= 1
        newIndentWidth = numIndents * sm.indent
        delta = newIndentWidth - currentIndentWidth
        indentlog.info("delta = %d", delta)
        # apply that delta to each line in the region
        region = sm.getTextRange(startPos, endPos)
        lines = region.splitlines(1) # keep line ends
        data = []
        for line in lines:
            count = 0
            for char in line:
                if char in ' \t':
                    count += 1
                else:
                    break
            indent = line[:count].expandtabs(sm.tabWidth)
            rest = line[count:]
            numspaces = max(len(indent) + delta, 0)
            indent = scimozindent.makeIndentFromWidth(sm, numspaces)
            newline = indent + rest
            data.append(newline)
        region = ''.join(data)
        regionUtf8Len = self.sysUtils.byteLength(region)
        sm.targetStart = startPos
        sm.targetEnd = endPos
        # bug101318: try to keep the FVL in place, allow for wrapped lines
        # (folded blocks will be unfolded by the tab operation).
        firstVisibleLine = sm.firstVisibleLine
        firstDocLine = sm.docLineFromVisible(firstVisibleLine)
        sm.replaceTarget(len(region), region)
        sm.firstVisibleLine = sm.visibleFromDocLine(firstDocLine)
        endPos = startPos + regionUtf8Len
        if sm.selectionMode == sm.SC_SEL_LINES:
            # Maintain the same cursor position.
            startPos = sm.findColumn(startLineNo, startPosColumn + delta)
            endPos = sm.findColumn(endLineNo, endPosColumn + delta)
        elif ignoreEndLine:
            endPos = sm.positionFromLine(endLineNo + 1)
        if anchorFirst:
            sm.anchor = startPos
            sm.currentPos = endPos
        else:
            sm.currentPos = startPos
            sm.anchor = endPos

    def unexpandtabs(self, line):
        numspaces = len(line)-len(line.lstrip())
        rest = line[numspaces:]
        numtabs, numspaces = divmod(numspaces, self._view.scimoz.tabWidth)
        indent = '\t'*numtabs + ' '*numspaces
        return indent + rest

    def _do_cmd_moveToScreenTop(self):
        # move the cursor to the start of the first visible line
        view = self._view
        scimoz = view.scimoz
        linesFromTop = view.prefs.getLongPref('ySlop')
        lineno = min(scimoz.firstVisibleLine + linesFromTop, scimoz.lineCount)
        lineno = max(0, lineno)
        scimoz.gotoPos(scimoz.positionFromLine(lineno))

    def _do_cmd_moveToScreenCenter(self):
        # move the cursor to the center of the visibles lines
        scimoz = self._view.scimoz
        fvl = scimoz.firstVisibleLine
        linesOnScreen = scimoz.linesOnScreen
        lineno = min(fvl + (linesOnScreen//2), scimoz.lineCount)
        lineno = max(0, lineno)
        scimoz.gotoPos(scimoz.positionFromLine(lineno))

    def _do_cmd_moveToScreenBottom(self):
        # move the cursor to the start of the first visible line
        view = self._view
        scimoz = view.scimoz
        linesFromBottom = view.prefs.getLongPref('ySlop')
        lineno = min(scimoz.firstVisibleLine + (scimoz.linesOnScreen - linesFromBottom) - 1, scimoz.lineCount)
        lineno = max(0, lineno)
        scimoz.gotoPos(scimoz.positionFromLine(lineno))

    def _do_cmd_moveScreenTop(self):
        sm = self._view.scimoz
        sm.currentPos = max(sm.currentPos, sm.anchor)
        sm.lineEndWrap()

    def _do_cmd_newlinePrevious(self):
        sm = self._view.scimoz
        # Ensure we move to the first visible character on the line
        sm.home()
        sm.vCHomeWrap()
        self._do_cmd_newline()
        sm.lineUp()

    def _do_cmd_swapCase(self):
        sm = self._view.scimoz
        currentPos = sm.currentPos
        anchor = sm.anchor
        if currentPos == anchor:
            # Nothing selected, swap the current character position then.
            curLine = sm.lineFromPosition(currentPos)
            lineStartPos = sm.positionFromLine(curLine)
            lineEndPos = sm.getLineEndPosition(curLine)
            if currentPos >= lineEndPos:
                if currentPos == lineStartPos:
                    # There is nothing on this line.
                    return
                # Vi stops at the last character in the line, then will allow
                # to keep swapping this last character.
                currentPos = sm.positionBefore(currentPos)
            curChar = sm.getWCharAt(currentPos)
            if curChar:
                newChar = curChar.swapcase()
                sm.targetStart = currentPos
                sm.targetEnd = sm.positionAfter(currentPos)
                sm.replaceTarget(len(newChar), newChar)
                # Move the cursor right (if not at end of line)
                if currentPos < lineEndPos:
                    sm.charRight()
        else:
            sm.replaceSel(sm.selText.swapcase())
            sm.anchor = anchor
            sm.currentPos = currentPos



#---- internal support stuff

def _sendStatusMessage(msg, highlight=False, timeout=3000):
    observerSvc = components.classes["@mozilla.org/observer-service;1"]\
                  .getService(components.interfaces.nsIObserverService)
    sm = components.classes["@activestate.com/koStatusMessage;1"]\
         .createInstance(components.interfaces.koIStatusMessage)
    sm.category = "editor"
    sm.msg = msg
    sm.timeout = timeout
    sm.highlight = highlight
    try:
        observerSvc.notifyObservers(sm, "status_message", None)
    except COMException, ex:
        pass

def classifyws(s, tabwidth):
    raw = effective = 0
    for ch in s:
        if ch == ' ':
            raw = raw + 1
            effective = effective + 1
        elif ch == '\t':
            raw = raw + 1
            effective = (effective / tabwidth + 1) * tabwidth
        else:
            break
    return raw, effective

def getLine(scin, lineNo):
    lineStart = scin.positionFromLine(lineNo)
    lineEnd = scin.getLineEndPosition(lineNo)
    line = scin.getTextRange(lineStart, lineEnd)
    return line
