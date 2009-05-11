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

import cgi, copy, re, types, os, uriparse, eollib
import Queue
import threading
import logging
import pprint

import scimozindent
import timeline
from xpcom import components
from xpcom._xpcom import PROXY_SYNC, PROXY_ALWAYS, PROXY_ASYNC, getProxyForObject

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

class KoCompletionLanguageService:
    _com_interfaces_ = [components.interfaces.koICompletionLanguageService]
    triggers = ''
    completionSeparator = ord('\n')
    triggersCallTip = None

    def __init__(self):
        pass
    
    def scanBufferCompletion(self, scimoz, filename):
        pass



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

class KoCodeIntelCompletionLanguageService:
    _com_interfaces_ = [components.interfaces.koICodeIntelCompletionLanguageService]

    # Separator btwn completions in a completion list.
    # We don't use the default, ' ', because so of our languages have
    # completions with spaces in them (e.g. Tcl).
    completionSeparator = '\n'
    # Characters that invoke the currently completion and then get added.
    # This should be overriden as necessary by the lang-specific subclasses.
    completionFillups = ""

    def __init__(self):
        self.initialized = False
        self.codeIntelSvc = components.classes["@activestate.com/koCodeIntelService;1"]\
            .getService(components.interfaces.koICodeIntelService);
        self._requests = _QueueOfOne()
        self._scheduler = threading.Thread(target=self._schedule,
            name="KoCodeIntelCompletionLanguageService Scheduler (%s)" % id(self))
        self._scheduler.start()

    def initialize(self, language):
        # Styles in which completion should not automatically happen.
        self._noImplicitCompletionStyles \
            = dict((s, True) for s in
                   language.getCommentStyles() + language.getStringStyles())

        # Styles in which completion should never happen (automatically or
        # otherwise).
        self._noCompletionStyles \
            = dict((s, True) for s in language.getNumberStyles())

        self.initialized = True

    def finalize(self):
        self._requests.put(None)  # sentinel to stop scheduler thread

    def get_completionSeparatorOrd(self):
        return ord(self.completionSeparator)

    def _schedule(self):
        """The is the Code Intel Completion UI request scheduler.
        
        It gets requests from self._requests and calls self._handleRequest
        for each. Each language-specific subclass of this class must
        implement that method.
        """
        log.info("codeintel completion UI request scheduler: start")
        while 1:
            request = self._requests.get()
            if request is None: # sentinel
                break
            try:
                self._handleRequest(request)
            except:
                # Log any errors and keep going.
                log.exception("error handling Code Intel completion UI "
                              "request for '%s' at %s:%d", request[2],
                              os.path.basename(request[0]), request[1])
        log.info("codeintel completion UI request scheduler: end")

    def requestCompletionUI(self, path, completionType, scimoz, position,
                            ciCompletionUIHandler):
        log.debug("requestCompletionUI(path=%r, '%s', scimoz, position=%d, "
                  "ciCompletionUIHandler)", path, completionType, position)
        proxiedCICompletionUIHandler = getProxyForObject(
            None, components.interfaces.koICodeIntelCompletionUIHandler,
            ciCompletionUIHandler, PROXY_ALWAYS | PROXY_SYNC)
        offset, styledText, styleMask = self._getSciMozContext(scimoz, position)
        file_id, table, id = self.codeIntelSvc.getAdjustedCurrentScope(scimoz, position)
        request = (path, scimoz.lineFromPosition(position)+1,
                   completionType, offset, styledText, styleMask, position,
                   file_id, table, id, scimoz.text,
                   proxiedCICompletionUIHandler)
        self._requests.put(request)

    def _getSciMozContext(self, scimoz, position):
        """Return styled context around 'position' for completion work."""
        # We need to pick some reasonable amount of context around the
        # trigger position.
        LINES_CONTEXT = (10, 3) # lines of context before and after
        currLine = scimoz.lineFromPosition(position)
        span = (max(0, currLine-LINES_CONTEXT[0]),  # context span (in lines)
                min(scimoz.lineCount, currLine+LINES_CONTEXT[1]+1))
        span = (scimoz.positionFromLine(span[0]),   # context span (in position)
                scimoz.positionFromLine(span[1]))
        offset = span[0]
        styledText = scimoz.getStyledText(*span)
        styleMask = (1 << scimoz.styleBits) - 1
        return (offset, styledText, styleMask)

    def triggerPrecedingCompletionUI(self, path, scimoz, startPos,
                                     ciCompletionUIHandler):
        return "'Trigger preceding completion' not implemented for this language."

    def _handleRequest(self, request):
        """Handle a single completion UI request.
        
            "request" is a 11-tuple representing the request:
                (<path>,
                 <line>, # 1-based line number of trigger point
                 <completion-type>,
                 <offset of context>,
                 <styledText of reasonable context>, # as from scimoz.getStyledText()
                 <styleMask>,
                 <position>,  # trigger point position
                 # CIDB table/id of starting scope, or None/0
                 <scopeTable>, <scopeId>,
                 # the full buffer contents (optional, required for fallback
                 # "dumb" completion handling)
                 <content>,
                 <koICodeIntelCompletionUIHandler>)
        
        The <completion-type> is one of the strings in the set returned by
        the language's getTriggerType() implementation.
        
        This is what a language-specific implementation of this method is
        supposed to do: It should determine authoritatively if the given
        position is a trigger point -- remember that .getTriggerType() may
        return false positives. If it is not a trigger point then just
        silently abort. If it is a trigger point then determine the
        completion data and pass it to the completion UI handler.
        """
        raise NotImplementedError("virtual method called: must override "
                                  "in subclass")

    def getCallTipHighlightSpan(self, enteredRegion, calltip):
        """Determine which span of the given calltip to highlight.
        
        Returns a 2-tuple giving the start and end indeces into the "calltip"
        string.
        
        Specifying -1 for the start index will abort the calltip -- i.e. the
        cursor has moved out of the call region. A calltip will automatically
        be aborted for some actions -- e.g. <End> key, <PgDn>. However,
        a good implementation of this per-language is probably necessary to
        know when to properly close the calltip.
        
        Sub-classes should implement this for their languages.
        """
        #XXX It might make sense to write a relatively general and capable
        #    one in this base class.
        log.debug("getCallTipHighlightSpan(enteredRegion=%r, calltip=%r)",
                  enteredRegion, calltip)
        return (0, 0) # don't highlight anything by default


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
    
class KoLinterLanguageService:
    """Just a way to get the contract IDs used by koLintService"""
    _com_interfaces_ = [components.interfaces.koILinterLanguageService]

    def __init__(self, linterCID):
        # this argument-laden constructor should go away --
        # not portable to other languages.
        self._linterCID = linterCID

    def get_linterCID(self):
        return self._linterCID


#---- base commenting language service classes
def getActualStyle(scimoz, pos):
    styleMask = (1 << scimoz.styleBits) - 1
    return scimoz.getStyleAt(pos) & styleMask

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

    def _commentLines(self, scimoz, startIndex, endIndex):
        """Comment the indexed lines."""
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
            scimoz.replaceTarget(len(replacement), replacement)

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
            scimoz.replaceTarget(len(replacement), replacement)

            # restore the selection and cursor position
            scimoz.selectionStart = selStart + len(prefix)
            scimoz.selectionEnd = selEnd + len(prefix)
            scimoz.hideSelection(0)
            scimoz.xOffset = xOffset

    def _uncommentLines(self, scimoz, startIndex, endIndex):
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
                    if not (commentMatch.group(3) + commentMatch.group(5)):
                        # If there is no line content after the comment
                        # delimiters then just replace the whole line with
                        # an empty line, i.e. strip out the indent as well.
                        # This allows a comment/uncomment cycle on a blank
                        # line (when part of a group of lines) to not change
                        # the line.
                        replacementLines.append(line[1])
                    else:
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
            scimoz.replaceTarget(len(replacement), replacement)

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

    def _uncommentBlock(self, scimoz, startIndex, endIndex):
        xOffset = scimoz.xOffset
        selStart = scimoz.selectionStart
        selEnd = scimoz.selectionEnd
        delimiters = self.delimiterInfo["block"]

        for prefix, suffix in delimiters:
            # Unicode: assume delimiters don't contain multi-byte characters
            pStart, pEnd = startIndex-len(prefix), startIndex
            sStart, sEnd = endIndex, endIndex+len(suffix)
            p = scimoz.getTextRange(pStart, pEnd)
            s = scimoz.getTextRange(sStart, sEnd)
            #log.debug("block uncomment delimiter match if (%s==%s and %s==%s)" % (p, prefix, s, suffix))
            if (p == prefix and s == suffix):
                scimoz.hideSelection(1)
                # remove the existing prefix and suffix (suffix first to get
                # indeces correct)
                scimoz.beginUndoAction()
                try:
                    scimoz.targetStart = sStart
                    scimoz.targetEnd = sEnd
                    scimoz.replaceTarget(0, "")
                    scimoz.targetStart = pStart
                    scimoz.targetEnd = pEnd
                    scimoz.replaceTarget(0, "")
                finally:
                    scimoz.endUndoAction()
                # restore the selection and cursor position
                scimoz.selectionStart = selStart - len(prefix)
                scimoz.selectionEnd = selEnd - len(prefix)
                scimoz.hideSelection(0)
        scimoz.xOffset = xOffset

    def _determineMethodAndDispatch(self, scimoz, workers):
        selStart = scimoz.selectionStart
        selEnd = scimoz.selectionEnd
        selStartLine = scimoz.lineFromPosition(selStart)
        selEndLine = scimoz.lineFromPosition(selEnd)
        # Handle line selection mode (as used by vi).
        if scimoz.selectionMode == scimoz.SC_SEL_LINES:
            selStart = scimoz.getLineSelStartPosition(selStartLine)
            selEnd = scimoz.getLineSelEndPosition(selEndLine)
        selStartColumn = scimoz.getColumn(selStart)
        selStartLineEndPosition = scimoz.getLineEndPosition(selStartLine)
        selEndColumn = scimoz.getColumn(selEnd)
        selEndLineEndPosition = scimoz.getLineEndPosition(selEndLine)

        # determine preferred commenting method (if the selection is _within_
        # a line then block commenting is preferred)
        if scimoz.selectionMode == scimoz.SC_SEL_LINES:
            preferBlockCommenting = 0
        elif selStart != selEnd:
            if (selStartColumn == 0 or selStart == selStartLineEndPosition) \
               and (selEndColumn == 0 or selEnd == selEndLineEndPosition):
                preferBlockCommenting = 0
            else:
                preferBlockCommenting = 1
        else:
            preferBlockCommenting = 0
        if self.DEBUG:
            print "prefer block commenting? %s"\
                  % (preferBlockCommenting and "yes" or "no")
            print "comment delimiter info: %s" % self.delimiterInfo

        # do the commenting/uncommenting
        if preferBlockCommenting and self.delimiterInfo.get("block", None):
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
        self._determineMethodAndDispatch(scimoz, commenters)
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
        self._determineMethodAndDispatch(scimoz, uncommenters)



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
        self._indent_open_styles = (10,)
        self._indent_close_styles = (10,)
        self._lineup_close_styles = (10,)
        self._lineup_styles = (10,)
        # These are all automatically calculated from styles.StateMap
        # for pure languages, overridden by UDL
            
        # Logically group some language-specific styles. It is useful in
        # some editor functionality to, for example, skip over comments or
        # strings.
    
        # Put in all values as empty tuples or None, and override
        self._block_comment_styles = ()
        self._comment_styles = ()
        self._datasection_styles = ()
        self._default_styles = ()
        self._ignorable_styles = ()
        self._regex_styles = ()
        self._indent_styles = ()
        self._keyword_styles = ()
        self._multiline_styles = ()
        self._modified_keyword_styles = ()
        self._number_styles = ()
        self._string_styles = ()
        self._variable_styles = ()

class koLangSvcStyleInfo(koLangSvcStyleInfo_Default):
    def __init__(self, **attrs):
        koLangSvcStyleInfo_Default.__init__(self)
        for k in attrs.keys():
            setattr(self, k, attrs[k])

_softCharDecorator = components.interfaces.koILintResult.DECORATOR_SOFT_CHAR

class _NextLineException(Exception):
    pass

class KoLanguageBase:
    _com_interfaces_ = [components.interfaces.koILanguage]

    _lexer = None
    _style = None
    _completer = None
    _commenter = None
    _codeintelcompleter = None
    _interpreter = None
    styleBits = 5
    stylingBitsMask = None # set by setter below
    indicatorBits = 2
    supportsBraceHighlighting = 1
    sample = '' # used in the fonts & colors dialog
    downloadURL = '' # location to download the language
    searchURL = '' # used by the language help system
    variableIndicators = ''
    supportsSmartIndent = "text"

    # Override in subclass with an extension (string) to provide a fallback
    # file association for the language. The extension string must include the
    # leading period, e.g. ".py".
    defaultExtension = None
    
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

    # These should be overriden by the language implementation
    _dedenting_statements = []
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
        components.interfaces.koILinterLanguageService: 'get_linter',
        components.interfaces.koICompletionLanguageService: 'get_completer',
        components.interfaces.koICodeIntelCompletionLanguageService: 'get_codeintelcompleter',
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

    def __init__(self):
        if not KoLanguageBase.prefset:
            KoLanguageBase.prefset = components.classes["@activestate.com/koPrefService;1"]\
                        .getService(components.interfaces.koIPrefService).prefs
        self.stylingBitsMask = 0    
        for bit in range(self.styleBits):
            self.stylingBitsMask <<= 1
            self.stylingBitsMask |= 1
    
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
 
    def actual_style(self, orig_style):
        # TODO: remove use of this function and self.stylingBitsMask
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

    # protected
    def _get_linter_from_lang(self, language):
        if not hasattr(self, "_linter"):
            try:
                self._linter = KoLinterLanguageService("@activestate.com/koLinter?language=%s;1" % language)
            except ServerException:
                self._linter = None
        return self._linter

    def get_linter(self):
        return self._get_linter_from_lang(self.name)

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
        style = style & self.stylingBitsMask
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
                                       self.stylingBitsMask,
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
        timeline.enter('guessIndentationByFoldLevels')
        try:
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
        finally:
            timeline.leave('guessIndentationByFoldLevels')
    
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
        timeline.enter('_shouldIndent')
        curLineNo = scimoz.lineFromPosition(pos)
        lineStart = scimoz.positionFromLine(curLineNo)
        data = scimoz.getStyledText(lineStart, pos+1)
        for p in range(pos-1, lineStart-1, -1):
            char = data[(p-lineStart)*2]
            style = ord(data[(p-lineStart)*2+1]) & self.stylingBitsMask
            #indentlog.debug("char = %s, style = %d", char, style)
            #indentlog.debug("indent_open_chars = %r, indent_open_styles = %r", self._indent_open_chars, style_info._indent_open_styles)
            if style in style_info._comment_styles:
                indentlog.debug("skipping comment character")
                continue
            elif char in ' \t':
                continue
            elif (char in self._indent_open_chars and
                  style in style_info._indent_open_styles):
                # need to find the beginning of the logical statement.
                lineNo = self._statementStartingLineFromPos(scimoz, p, style_info)
                indentlog.debug("we've decided that the statement starting from line %d actually starts at line %d" % (curLineNo, lineNo))
                nextIndentWidth = self._getNextLineIndent(scimoz, lineNo)
                return scimozindent.makeIndentFromWidth(scimoz, nextIndentWidth)
            break
        timeline.leave('_shouldIndent')
        return None

    def _shouldLineUp(self, scimoz, pos, style_info):
        # first we look for an unmatched 'line-up' brace, going back until
        # either we've gone back 100 lines, or we get past the indent
        # of the current line

        timeline.enter('_shouldLineUp')
        try:
            curLineNo = scimoz.lineFromPosition(pos)
            minIndent = self._getIndentWidthForLine(scimoz, curLineNo)
            startLineNo = max(curLineNo-100, 0)
            startPos = scimoz.positionFromLine(startLineNo)
            p = pos
            timeline.enter('getStyledText')
            data = scimoz.getStyledText(startPos, pos+1)
            timeline.leave('getStyledText')
            while p > startPos:
                p = p - 1
                char = data[(p-startPos)*2]
                indentlog.info("looking at char %r at position %d", char, p)
                style = ord(data[(p-startPos)*2+1]) & self.stylingBitsMask
                if char in self._lineup_close_chars and style in style_info._lineup_close_styles:
                    # skip to the match
                    braceMatch = scimoz.braceMatch(p)
                    if braceMatch == -1:
                        break
                    p = braceMatch
                    char = data[(p-startPos)*2]
                    style = ord(data[(p-startPos)*2+1]) & self.stylingBitsMask
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
                            style = ord(data[(p2-startPos)*2+1]) & self.stylingBitsMask
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
                    timeline.mark('breaking out')
                    indentlog.debug("breaking out of looking for line-up characters" +
                                    "because we've moved too far to the left at column %d < %d", col, minIndent)
                    return None
            timeline.mark("looked over %d/%d characters" % (pos-p, pos-startPos))
            return None
        finally:
            timeline.leave('_shouldLineUp')

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
            style = ord(data[(p-startOfLine)*2+1]) & self.stylingBitsMask
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

        while p > startPos:
            p = p - 1
            char = data[(p-startPos)*2]
            style = ord(data[(p-startPos)*2+1]) & self.stylingBitsMask
            #indentlog.debug("in _statementStartingLineFromPos: char = %s, style = %d", char, style)
            #indentlog.debug("indent_close_chars = %r, indent_clos_styles = %r", self._indent_close_chars, style_info._indent_close_styles)
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
        timeline.enter('_analyzeIndentNeededAtPos')
        try:
            if scimoz.getColumn(pos) == 0:
                # If we're in column zero, do me no favors
                return None
            curLineNo = scimoz.lineFromPosition(pos)
            lineStart = scimoz.positionFromLine(curLineNo)
            lineEnd = scimoz.getLineEndPosition(curLineNo)
            curLine = scimoz.getTextRange(lineStart, lineEnd)
            
            inBlockCommentIndent, inLineCommentIndent = self._inCommentIndent(scimoz, pos, continueComments, style_info)

            # see if we're in a block comment, and do 'inside-comment' indents
            if inBlockCommentIndent is not None:
                indentlog.info("we're in a block comment")
                return inBlockCommentIndent

            shouldIndent = self._shouldIndent(scimoz, pos, style_info)
            if shouldIndent is not None:
                indentlog.info("detected indent")
                return shouldIndent
            indentlog.info("did not detect indentation")

            while 1:
                jumped = self._skipOverParentheticalStatement(scimoz, pos, style_info)
                log.debug("pos = %d, jumped = %d" % (pos, jumped))
                if pos == jumped:
                    log.debug('breaking out of the jumping code')
                    break # nothing to go back to.
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

            finishedBlockCommentIndents = self._finishedBlockComment(scimoz, pos, style_info)
            if finishedBlockCommentIndents is not None:
                indentlog.info("detected block comment close")
                return finishedBlockCommentIndents[0]
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

            indentlog.info("not in comment, doing plain")
            return None
        finally:
            timeline.leave('_analyzeIndentNeededAtPos')

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
        if pos < scimoz.length:
            currLineNo = scimoz.lineFromPosition(pos)
            currLineEndPos = scimoz.getLineEndPosition(currLineNo)
            if pos < currLineEndPos and scimoz.getTextRange(pos, currLineEndPos).strip():
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
        firstCharStyle = scimoz.getStyleAt(firstCharIndex) & self.stylingBitsMask
        if firstCharStyle in style_info._comment_styles or firstCharStyle in style_info._string_styles:
            return None

        wordMatch = self.firstWordRE.match(unicode(curLine))
        if wordMatch and wordMatch.group(1) in self._indenting_statements:
            return 1
        if wordMatch and wordMatch.group(1) in self._dedenting_statements:
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
        return None

    def _finishedBlockComment(self, scimoz, pos, style_info):
        """ This function looks to see if we just ended a block comment.
        If not, it returns (None, None).
        If yes, it returns two indents -- the indent which is appropriate
        for the next line, and the indent of the beginning of the block
        statement, e.g.:
        
            ....x = 3 /* this is the start
                         and so
            ..........*/
                
        the first is four spaces, the second ten.  the first is used
        to process the newline, the second to shift the end of the
        block comment if is not preceded by non-whitespace chars on
        the same line.
        
        """
        
        # Unicode: is pos used correctly in this function?
        lineNo = scimoz.lineFromPosition(pos)
        startOfLine = scimoz.positionFromLine(lineNo)
        p = pos
        data = scimoz.getStyledText(startOfLine, pos)
        while p >= startOfLine:
            p -= 1
            # move back until we hit a character.
            char = data[(p-startOfLine)*2]
            if char in ' \t': continue
            style = ord(data[(p-startOfLine)*2+1]) & self.stylingBitsMask
            if style not in style_info._block_comment_styles:
                # we hit a non-comment character -- it can't be the
                # end of a block comment
                indentlog.info("we hit a non-comment character -- it can't be the end of a block comment")
                return None
            # see if our current position matches the ends of block comments
            blockCommentPairs = self.commentDelimiterInfo['block']
            for blockCommentStart, blockCommentEnd in blockCommentPairs:
                for i in range(len(blockCommentEnd)):
                    c = blockCommentEnd[len(blockCommentEnd)-i-1]
                    if c != data[(p-i-startOfLine)*2]:
                        indentlog.info("looking for %s, got %s",
                                       data[(p-i-startOfLine)*2],
                                       c)
                        return None
                # we have a comment end!
                # find the matching comment start
                text = scimoz.getTextRange(0, p)
                startOfComment = text.rfind(blockCommentStart)
                if startOfComment == -1:
                    indentlog.info("could not find the beginning of the block comment")
                    return None
                nextLineIndent = self._getIndentForLine(scimoz,
                                                scimoz.lineFromPosition(startOfComment))
                adjustIndent = scimozindent.makeIndentFromWidth(scimoz,
                                                   scimoz.getColumn(startOfComment))
                
                # is this block comment using markup?  If so, we want an
                # additional space in the adjustment.  This allows
                # javadoc style comments to format correctly.
                if 'markup' in self.commentDelimiterInfo:
                    markup = self.commentDelimiterInfo['markup']
                    if markup:
                        usedMarkup = text[startOfComment+len(blockCommentStart):(0-len(blockCommentEnd))].rfind('%s %s' %(adjustIndent,markup))
                        if usedMarkup != -1:
                            adjustIndent += ' '
                
                return nextLineIndent, adjustIndent
        return None
    
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
            if getActualStyle(scimoz, pos) in commentStyles and \
               (pos == 0 or getActualStyle(scimoz, pos - 1) not in commentStyles):
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

        style = scimoz.getStyleAt(pos-1) & self.stylingBitsMask
        if style not in style_info._comment_styles:
            return None, None
        
        # determine if we're in a line-style comment or a block-style comment
        if style in style_info._block_comment_styles:
            commentType = 'block'
            indentlog.debug("in block comment style")
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
                    if pos < doclen and (scimoz.getStyleAt(pos) & self.stylingBitsMask) not in style_info._comment_styles:
                        # Observed with CSS but not C/C++
                        # If the newline after the comment is not a comment,
                        # assume the comment has ended.
                        # This is because only CSS and Pascal define
                        # block comments but not any others.
                        style = getActualStyle(scimoz, pos)
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
                        style = getActualStyle(scimoz, pos)
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
        if commentType == 'line':
            # the comment started on this line -- if the line consisted of nothing but
            # comments, then continue it (except if continueComments is false)
            # If there was code on the line, then don't do anything special.
            fromStartToCommentStart = curLine[0:commentStart]
            if not continueComments or fromStartToCommentStart.strip():
                return None, None
            indent = scimozindent.makeIndentFromWidth(scimoz, indentWidth) + commentStartMarker
        else:
            indent = scimozindent.makeIndentFromWidth(scimoz, indentWidth) + (len(commentStartMarker)-len(markup))*' '

        while rest[0:len(commentStartMarker)] and rest[0:len(commentStartMarker)] == commentStartMarker:
            if commentType == 'line':
                indent += commentStartMarker
            else:
                indent += (len(commentStartMarker) - len(markup))*' '
            rest = rest[len(commentStartMarker):]
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
        for char in rest:
            if char in ' \t':
                indent += char
            else:
                break
        if commentType == 'line':
            return None, indent
        else:
            return indent, None

    def computeIndent(self, scimoz, indentStyle, continueComments):
        return self._computeIndent(scimoz, indentStyle, continueComments, self._style_info)

    def _computeIndent(self, scimoz, indentStyle, continueComments, style_info):
        try:
            if indentStyle == 'none':
                return ''
            if indentStyle == 'plain':
                return self._getPlainIndent(scimoz, style_info)
            if self.supportsSmartIndent == 'text':
                lineNo = scimoz.lineFromPosition(scimoz.currentPos)
                indentWidth = self._getIndentWidthForLine(scimoz, lineNo)
                indentWidth = min(indentWidth, scimoz.getColumn(scimoz.currentPos))
                return scimozindent.makeIndentFromWidth(scimoz, indentWidth)
            if self.supportsSmartIndent in ('brace', 'python'):
                return self._getSmartBraceIndent(scimoz, continueComments, style_info)
            if self.supportsSmartIndent == 'XML':
                return self._getSmartXMLIndent(scimoz, continueComments, style_info)
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
        timeline.enter('_getSmartBraceIndent')
        if (scimoz.getColumn(currentPos) == 0):
            return None
        try:
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
        finally:
            timeline.leave('_getSmartBraceIndent')

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
            and (scimoz.getStyleAt(pos + 1) & self.stylingBitsMask) == scimoz.SCE_UDL_M_TAGSPACE):
            # Verify there's a start-tag on this line
            curLineNo = scimoz.lineFromPosition(pos)
            lineStart = scimoz.positionFromLine(curLineNo)
            data = scimoz.getStyledText(lineStart, pos)
            idx = len(data) - 1
            while idx > 0:
                if (ord(data[idx]) & self.stylingBitsMask) == scimoz.SCE_UDL_M_TAGNAME:
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
        text = scimoz.getTextRange(0, scimoz.positionAfter(pos))
        lastLeftBraceIndex = text.rfind('<')
        lastSlashIndex = text.rfind('/')
        if lastSlashIndex == lastLeftBraceIndex + 1:
            return 'END_TAG_CLOSE'
        text = text.rstrip()
        if not text: return ''
        # Handle xml-based multi-sublanguage languages that don't
        # have a UDL definition, and end in strings like '%>'
        # Ref bug 57417
        if text[-1] == '>' and (len(text) == 1 or text[-2] not in "!@#$%^&*?]\'\""):
            # we just finished a tag, we think
            return "START_TAG_CLOSE"
        # we're likely in the text part of a <p> node for example
        return ''
    
    def _precededByText(self, scimoz, currentPos):
        assert scimoz.getWCharAt(pos) == "<"
        currentLine = scimoz.lineFromPosition(currentPos)
        lineStartPos = scimoz.positionFromLine(currentLine)
        for pos in range(currentPos - 1, lineStartPos - 1, -1):
            style = scimoz.getStyleAt(pos) & self.stylingBitsMask
            if style != scimoz.SCE_UDL_M_DEFAULT:
                # This tag is immediately followed by markup, so do traditional
                # indentation.
                # XXX This really needs continual moving up until we determine
                # that we're at the top-level, in pure data markup (no mixed
                # tags), or in mixed content.
                return False
            char = scimoz.getWCharAt(pos)
            if not char.isspace():
                # Found at least one non-whitespace text
                # character on this line preceding the start of the tag.
                return True
        return False

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
        currentLine = scimoz.lineFromPosition(scimoz.currentPos)
        startOfLine = scimoz.positionFromLine(currentLine)
        stuffToLeft = scimoz.getTextRange(startOfLine, scimoz.currentPos)
        if not stuffToLeft.strip():
            return scimozindent.makeIndentFromWidth(scimoz, scimoz.getColumn(scimoz.currentPos))
        index = scimoz.currentPos - 1
        beforeText = scimoz.getTextRange(0, scimoz.currentPos)
        tagStartPos = -1
        while index > 0:
            char = scimoz.getWCharAt(index)
            style = scimoz.getStyleAt(index) & self.stylingBitsMask
            state = self._findXMLState(scimoz, index, char, style)
            indentlog.debug("char = %r", char)
            indentlog.debug("style = %r", style)
            indentlog.debug("state = %r", state)
            if state == 'START_TAG_CLOSE':
                tagStartPos = beforeText.rfind('<')
                if self._precededByText(scimoz, tagStartPos):
                    return self._getIndentForLine(scimoz, currentLine)
                textBeforeTag = beforeText[startOfLine:tagStartPos]
                if textBeforeTag.strip():
                    # There's markup to the left of this tag -- analyze it
                    #XXX Keep moving back if there are other tags, and calculate
                    # a net indentation
                    return self._getIndentForLine(scimoz, currentLine)
                startLine = scimoz.lineFromPosition(tagStartPos)
                # convert from character offset to byte position --
                # that's what getColumn wants.
                tagStartPosForGetColumn = scimoz.positionAtChar(0, tagStartPos)
                currentIndentWidth = scimoz.getColumn(tagStartPosForGetColumn)
                nextIndentWidth = (divmod(currentIndentWidth, scimoz.indent)[0] + 1) * scimoz.indent
                indentlog.debug("currentIndentWidth = %r", currentIndentWidth)
                indentlog.debug("nextIndentWidth= %r", nextIndentWidth)
                return scimozindent.makeIndentFromWidth(scimoz, nextIndentWidth)
            elif state == "END_TAG_CLOSE":
                # find out what tag we just closed
                leftCloseIndex = beforeText.rfind('</')
                if leftCloseIndex == -1:
                    break
                startTagInfo = scimozindent.startTagInfo_from_endTagPos(scimoz, leftCloseIndex)
                if startTagInfo is None:
                    tagStartPos = -1
                else:
                    tagStartPos = startTagInfo[0]
                standard_type = True
            elif state == "START_TAG_EMPTY_CLOSE":
                tagStartPos = beforeText.rfind('<')
                standard_type = True
            elif state == "ATTRIBUTE_CLOSE":
                return self._getIndentForLine(scimoz, currentLine)
            elif state == "START_TAG_NAME" or \
                        style in [scimoz.SCE_UDL_M_TAGSPACE,
                                  scimoz.SCE_UDL_M_ATTRNAME,
                                  scimoz.SCE_UDL_M_OPERATOR]:
                # We're somewhere in a tag.
                # Find the beginning of the tag, then move to the end of that word
                tagStartPos = beforeText.rfind('<')
                if tagStartPos == -1:
                    break
                if self._precededByText(scimoz, tagStartPos):
                    return self._getIndentForLine(scimoz, currentLine)
                whitespaceRe = re.compile('(\S+)(\s*)')
                firstSpaceMatch = whitespaceRe.search(beforeText[tagStartPos:])
                if not firstSpaceMatch:
                    standard_type = True
                else:
                    if firstSpaceMatch.group(2):
                        # i.e. there is some space after the tag
                        firstSpace = firstSpaceMatch.end()
                        startAttributeColumn = scimoz.getColumn(tagStartPos + firstSpace)
                    else:
                        # e.g. we just hit return with: <foo|
                        endOfTag = firstSpaceMatch.end()
                        startAttributeColumn = scimoz.getColumn(tagStartPos + endOfTag) + 1
                    return scimozindent.makeIndentFromWidth(scimoz, startAttributeColumn)
            elif style == scimoz.SCE_UDL_M_COMMENT:
                tagStartPos = beforeText.rfind('<--')
                standard_type = True
            elif state == "":
                if style == scimoz.SCE_UDL_M_DEFAULT:
                    if not char.isspace():
                        # If we don't end the line with a tag, continue the current indentation
                        return self._getIndentForLine(scimoz, currentLine)
                    else:
                        index -= 1
                        beforeText = beforeText[:-1]
                        standard_type = False
                elif style == scimoz.SCE_UDL_M_PI:
                    if beforeText.endswith("?>"):
                        tagStartPos = beforeText.rfind('<?')
                        standard_type = True
                    else:
                        return self._getIndentForLine(scimoz, currentLine)
                elif style == scimoz.SCE_UDL_M_CDATA:
                    if beforeText.endswith("]]>"):
                        tagStartPos = beforeText.upper().rfind('<![CDATA[')
                        standard_type = True
                    else:
                        return self._getIndentForLine(scimoz, currentLine)
                else:
                    return self._getIndentForLine(scimoz, currentLine)
            
            # Common endings for "standard" types
            if tagStartPos > index:
                assert False and "tag-start pos %d > index pos %d!" % (tagStartPos, index)
                break
            if standard_type:
                if tagStartPos == -1:
                    return self._getIndentForLine(scimoz, currentLine)
                if self._precededByText(scimoz, tagStartPos):
                    return self._getIndentForLine(scimoz, currentLine)
                startLine = scimoz.lineFromPosition(tagStartPos)
                if startLine != currentLine:
                    # Use the new currentLine's indentation
                    currentLine = startLine
                    startOfLine = scimoz.positionFromLine(currentLine)
                index = tagStartPos - 1
                beforeText = beforeText[:tagStartPos]
                # If there's nothing to the left of this tag, use that indentation
                if not beforeText[startOfLine:].strip():
                    return self._getIndentForLine(scimoz, currentLine)
                
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
        if default_indentation:
            return default_indentation
        return None

    # XPCOM call handles defaults
    def keyPressed(self, ch, scimoz):
        return self._keyPressed(ch, scimoz, self._style_info)

    def _keyPressed(self, ch, scimoz, style_info):
        currentPos = scimoz.currentPos
        charPos = scimoz.positionBefore(currentPos)
        style = scimoz.getStyleAt(charPos) & self.stylingBitsMask
        #indentlog.debug("ch=%s, style=%d, indent_close_chars=%r, indent_close_styles=%r",
        #               ch, style, self._indent_close_chars, style_info._indent_close_styles)
        indent = None
        if (ch == '>' and self.supportsSmartIndent == 'XML'):
            state = self._findXMLState(scimoz, charPos, ch, style)
            if state == 'END_TAG_CLOSE':
                scimozindent.adjustClosingXMLTag(scimoz, self.isHTMLLanguage)
            return

        indent = self.getIndentForCloseChar(scimoz, charPos, ch, style, style_info, None)
        if (indent is None
            and style in style_info._comment_styles
            and 'block' in self.commentDelimiterInfo):
            blockCommentEndMarker = self.commentDelimiterInfo['block'][0][-1]
            if blockCommentEndMarker.endswith(ch):
                indents = self._finishedBlockComment(scimoz, charPos+1, style_info)
                if indents is not None:
                    indent = indents[1]
                    charPos = charPos + 1 - len(blockCommentEndMarker)
                    # Fix bug 42792 -- do this in one place

        #XXX Observe this pref instead of getting it each time
        #XXX EP Note: I tried, but an observer doesn't work for UDL languages,
        # as it looks like the sub-languages weren't getting notifications.
        if ch in self.matchingSoftChars and self.prefset.getBooleanPref("editSmartSoftCharacters"):
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
                scimoz.replaceTarget(len(indent), indent)

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

        #1. First determine that the character isn't followed by an
        #   identifier character. (bug 70834)
        nextCharPos = scimoz.positionAfter(charPos)
        lineEndPos = scimoz.getLineEndPosition(scimoz.lineFromPosition(charPos))
        
        # Use one of the following acceptanceMethods, to determine
        # where soft chars are allowed: either only at end of line,
        # or either at end of line or before ident chars
        acceptanceMethod = self._can_insert_soft_char_at_eol_only
        #acceptanceMethod = self._can_insert_soft_char_at_eol_or_before_ident
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
                self._insertCloseBraceAfterLine(scimoz, currLineNo, nextLineNo) # case 3.1.
                return None
            targetLineNo = nextLineNo + 1
            targetIndentLen = self._getIndentWidthForLine(scimoz, targetLineNo)
            if targetIndentLen > currIndentLen:
                #log.debug("Looks like there is more than one line to wrap, so do it manually")
                # Don't wrap more than one line, but don't insert a soft char either - case 3.2-true
                pass
            else:
                self._insertCloseBraceAfterLine(scimoz, currLineNo, nextLineNo) # case 3.2-false.
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
            self._insertCloseBraceAfterLine(scimoz, currLineNo, nextLineNo) # case 7
    
    def _insertCloseBraceAfterLine(self, scimoz, useIndentOfThisLineNo, insertTextAtEndOfLineNo):
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
        finally:
            scimoz.endUndoAction()

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


def _findIndent(scimoz, bitmask, chars, styles, comment_styles, tabWidth, defaultUsesTabs):
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
    
    At most the first 100 lines are looked at.
    
    As a side effect, the first 100 lines of the buffer will be 'colourised' if they
    are not already.
    """
    timeline.enter('_findIndent')
    try:
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
        usesTabs = 0
        sawSufficientWhiteSpace = False
    
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
                            usesTabs = 1
                        elif blackPos >= tabWidth:
                            sawSufficientWhiteSpace = True
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
                    style = ord(data[pos*2+1]) & bitmask
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
                                                             bitmask,
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
                                        usesTabs = 1
                                        break
                                    elif blackPos >= tabWidth:
                                        sawSufficientWhiteSpace = True
                            return guess, usesTabs or (not sawSufficientWhiteSpace and defaultUsesTabs)
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
    finally:
        timeline.leave('_findIndent')

def _findIndentedLine(scimoz, bitmask, N, lineNo, indenting, comment_styles, tabWidth, data):
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
            style = ord(data[pos*2+1]) & bitmask
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

