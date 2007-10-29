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

# The implementation of the Komodo Run Output Window Terminal

import os
import sys
import re
import types
import threading
import process
import time
import logging
import traceback
import Queue

from xpcom import components, nsError, ServerException, COMException
from xpcom._xpcom import PROXY_SYNC, PROXY_ALWAYS, PROXY_ASYNC, getProxyForObject
from koTreeView import TreeView

#---- globals
log = logging.getLogger('koRunTerminal')
#log.setLevel(logging.DEBUG)


#---- line markers in scintilla that we are concerned with
MARKNUM_STDERR = 12
MARKNUM_STDOUT = 11
MARKNUM_CURRENT_LINE_BACKGROUND = 10
MARKNUM_STDIN_PROMPT = 9
MARKNUM_INTERACTIVE_PROMPT_MORE = 8
MARKNUM_INTERACTIVE_PROMPT = 7
MARKNUM_PROMPTS = (1 << MARKNUM_INTERACTIVE_PROMPT) | \
                  (1 << MARKNUM_INTERACTIVE_PROMPT_MORE) | \
                  (1 << MARKNUM_STDIN_PROMPT)

#---- internal support classes and routines


def _isurl(path):
    urlpattern = re.compile("^\w+://")
    if urlpattern.match(path):
        return 1
    else:
        return 0



#---- implementation

class koTerminalHandler:
    """
    This class is to be associated with views of type 'terminal'.
    It is the argument to "initWithTerminal" for that view.
    
    It is easy to add new handlers for special keystrokes.  Look at the way
    _handle_keypress_DOM_VK_BACK_SPACE is being defined for example.  See above
    for the list of special key codes.
    """
    _com_interfaces_ = [components.interfaces.koITerminalHandler]
    _reg_clsid_ = "36C5DDAA-7A5D-444D-80CA-17D52EBDBA9A"
    _reg_contractid_ = "@activestate.com/koTerminalHandler;1"
    _reg_desc_ = "Terminal View Handler"

    def __init__(self):
        self._lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"]\
            .getService(components.interfaces.koILastErrorService)

        self.active = 0 # Initially NOT interacting with a child process.
        self.stdin = None
        self.stdinHandler = None
        self.stdout = None
        self.stderr = None
        self._lastPrompt = None
        self.lastWritePosition = 0
        
        registryService = components.classes['@activestate.com/koLanguageRegistryService;1'].\
               getService(components.interfaces.koILanguageRegistryService)
        self.language = registryService.getLanguage('Errors');
        self._proxyself = getProxyForObject(None, components.interfaces.koITerminalHandler,
                                            self,
                                            PROXY_ALWAYS | PROXY_SYNC)

    #---- koIRunTerminal methods
    def setScintilla(self, scintilla):
        log.debug("[%s] KoRunTerminal.setScintilla(%s)", self, scintilla)
        # XXX scintilla MUST NEVER be used from a thread!!!
        self._scintilla = scintilla

        # Synchronization between the terminal and its _KoRunTerminalFile's.
        self.mutex = threading.RLock()
        self.ui_mutex = threading.Lock()
        self.stateChange = threading.Condition()

    def setLanguage(self, lang):
        self.language = lang

    def startSession(self):
        self.active = 1
        self.lastWritePosition = 0

    def endSession(self):
        self.active = 0
        self.stdin = None
        self.stdout = None
        self.stderr = None

    def clear(self):
        log.debug("koTerminalHandler.clear()")

        #XXX Shouldn't these three resets be in KoRunTerminal.clear() instead
        #    of here???
        self._parseRegex = None
        self._cwd = None
        self._currentFile = None
        self.lastWritePosition = 0

    def acquireLock(self):
        #self.ui_mutex.acquire()
        pass
        #log.debug("lock is aquired")
        
    def releaseLock(self):
        #self.ui_mutex.release()
        pass
        #log.debug("lock is released")

    # this is always called from an iobuffer thread
    def addText(self, length, text, name):
        # Note, the terminal mutex *must* be acquired before this call.
        # If we write to stdin, it ends up here, so we need to pass it along
        # to the real stdin object.
        if name == '<stdin>':
            #log.debug("koTerminalHandler.addText: [%s] [%r]", name, text)
            self.stdin.write(text)
            return

        self._proxyself.proxyAddText(length, text, name)

    # this function is always called via proxy so scintilla does not need to be
    # proxied the purpose of this is to prevent other modifications to scintilla
    # while this operation is happening. If we only proxy scintilla, then other
    # scintilla operations can happen during this function call.
    #
    # The idea is to avoid writing on an interactive prompt while at the same
    # time keeping stdout/stderr in continuous blocks. 
    #
    # we keep track of the last position we wrote to, so we can keep writing
    # from that location. If that location just happens to be on a line that a
    # prompt has appeared, then we bump the prompt to the end of the buffer.
    #
    # We also use a lock so the view.terminal doesn't try to pull the rug from
    # under us.
    # 
    # now lets do the funky mojo...
    #
    def proxyAddText(self, length, text, name):
        # name is either <stderr> or <stdout>
        # Note, the terminal mutex should *must* be aquired before this call.
        #log.debug("koTerminalHandler.proxyAddText: [%s] [%r]", name, text)
        try:
          self.acquireLock()
          eventMask = self._scintilla.modEventMask
          self._scintilla.modEventMask = 0
          try:
            ro = self._scintilla.readOnly
            self._scintilla.readOnly = 0
            
            startLine = self._scintilla.lineCount - 1
            startPos = self._scintilla.positionFromLine(startLine)
            startMarker = self._scintilla.markerGet(startLine)
            styleMask = (1 << self._scintilla.styleBits) - 1;
            if self.lastWritePosition > self._scintilla.length:
                self.lastWritePosition = self._scintilla.length

            if name == '<stdout>':
                style = self.language.styleStdout
                marker = MARKNUM_STDOUT
                otherStyle = self.language.styleStderr
                otherMarker = MARKNUM_STDERR
            elif name == '<stderr>':
                style = self.language.styleStderr
                marker = MARKNUM_STDERR
                otherStyle = self.language.styleStdout
                otherMarker = MARKNUM_STDOUT

            # if we're on a stdout/err line, add a new line now. this prevents
            # stdout and stderr from appearing on the same line
            if startMarker & (1 << otherMarker):
                self._scintilla.newLine()
                self._scintilla.startStyling(startPos, styleMask)
                self._scintilla.setStyling(self._scintilla.length - startPos, otherStyle)
                startLine = self._scintilla.lineCount - 1
                startPos = self._scintilla.positionFromLine(startLine)
            
            #print "style for %s is %d" %(name, style)

            if startMarker & MARKNUM_PROMPTS:
                if self.lastWritePosition:
                    startPos = self.lastWritePosition
                    startLine = self._scintilla.lineFromPosition(startPos)
                promptTextLength = self._scintilla.length - startPos
                #log.debug("inserting text before prompt line %d", promptTextLength)
                self._scintilla.insertText(startPos, text)
                self.lastWritePosition = self._scintilla.length - promptTextLength
            else:
                #log.debug("no prompt line, adding text to end")
                self._scintilla.addText(length, text)
                self.lastWritePosition = self._scintilla.length

            endPos = startPos + length
            endLine = self._scintilla.lineFromPosition(endPos)
            self._scintilla.gotoPos(self._scintilla.length)

            lastLine = self._scintilla.lineCount - 1
            
            # if we got stdout/err on top of a marker line, then we need to move the
            # marker.  Text on the marker line was already moved, but scintilla does
            # not move markers on the current line, only on following lines, so we
            # must handle it ourselves
            if startMarker & MARKNUM_PROMPTS:
                self._moveMarker(startMarker, startLine, MARKNUM_STDIN_PROMPT, lastLine)
                self._moveMarker(startMarker, startLine, MARKNUM_INTERACTIVE_PROMPT, lastLine)
                self._moveMarker(startMarker, startLine, MARKNUM_INTERACTIVE_PROMPT_MORE, lastLine)
            
            while startLine < lastLine:
                #log.debug("Add marker 1 %d to %d", marker, startLine)
                self._scintilla.markerAdd(startLine, marker)
                startLine += 1

            # if we wrote text without a newline, then we need to add a marker on the
            # last line of the document also
            if text[-1] not in ["\r","\n"]:
                #log.debug("Add marker 2 %d to %d", marker, endLine)
                self._scintilla.markerAdd(endLine, marker)

            self._scintilla.startStyling(startPos, styleMask)
            self._scintilla.setStyling(endPos - startPos, style)
            
            self._scintilla.readOnly = ro
            self._scintilla.ensureVisible(self._scintilla.lineCount-1)
            self._scintilla.scrollCaret()
          except COMException, e:
            # XXX we're catching an xpcom exception that happens
            # at shutdown. bug #28989
            # Exception: 0x8000ffff (NS_ERROR_UNEXPECTED)
            log.exception(e)
        finally:
          self._scintilla.modEventMask = eventMask
          self.releaseLock()

    def onClose(self, name):
        # name is either <stderr> or <stdout>
        pass

    def _moveMarker(self, startMarker, startLine, marker, lastLine):
        if startMarker & (1 << marker) and startLine < lastLine:
            #log.debug("Moving marker %d from %d to %d", marker, startLine, lastLine)
            self._scintilla.markerDelete(startLine, marker)
            self._scintilla.markerAdd(lastLine, marker)
        


class KoRunTerminal(koTerminalHandler, TreeView):
    """This is the interface between run sub-processes and Komodo's command
    output window (or _one_ of the command output windows if there are ever
    more than one). This acts as the handler for events on the output
    window's <scintilla> widget. It acts as the tree view for the output
    window's <tree> widget.

    The embedded Scintilla is kept in a 'readOnly' state unless
    currently interacting with the child process (self.active is True).
    XXX Perhaps there is a better API for that (perhaps call it
    'interactive')?

    Input is buffered in line chunks, i.e. user input is forwarded to
    the child a line at a time when <Enter> is pressed. This means that
    one can use backspace on the current line only.

    If enabled, output lines are parsed with a given regular expression
    as results into its tree.
    """
    _com_interfaces_ = [components.interfaces.koITreeOutputHandler,
                        components.interfaces.nsITreeView]
    _reg_clsid_ = "{A077FDDF-DBAD-4e49-9090-4390C084893B}"
    _reg_contractid_ = "@activestate.com/koRunTerminal;1"
    _reg_desc_ = "Run Output Window Terminal Handler"

    def __init__(self):
        #print "XXX [%s] KoRunTerminal.__init__()" % id(self)
        # Initialization of tree and parsing attributes.
        TreeView.__init__(self, debug=0)
        koTerminalHandler.__init__(self)
        self._pbbuf = ""
        self._data = []
        self._sortedBy = None
        self._parseRegex = None
        self._cwd = None
        self._currentFile = None
        # These two vars are used to group update calls to the outliner,
        # .rowCountChanged(), for performance reasons.
        self._updateGroupSize = 20
        self._updateGroupCounter = 0
        # Used to proxy calls to the UI
        self._treeProxy = None

    def addText(self, length, text, name):
        # name is either <stderr> or <stdout>
        # Note, the terminal mutex should *must* be aquired before this call.
        koTerminalHandler.addText(self, length, text, name)
        
        self._pbbuf += text
        lines = self._pbbuf.splitlines(1)
        for line in lines:
            if line.endswith("\r\n") or line.endswith("\n") or line.endswith("\r"):
                self.parseAndAddLine(line)
            else:
                # This must be the last (incomplete line).
                self._pbbuf = line
                break
        else:
            self._pbbuf = ""

    def onClose(self, name):
        # name is either <stderr> or <stdout>
        if self._pbbuf:
            self.parseAndAddLine(self._pbbuf)
            self._pbbuf = ""
        self.parsedLastLine()
        
    def setParseRegex(self, parseRegex):
        try:
            self._parseRegex = re.compile(parseRegex)
        except re.error, ex:
            self._lastErrorSvc.setLastError(0, str(ex))
            raise ServerException(nsError.NS_ERROR_INVALID_ARG, str(ex))

    def setCwd(self, cwd):
        if cwd:
            self._cwd = cwd
        else:
            self._cwd = os.getcwd()

    def setCurrentFile(self, filename):
        self._currentFile = filename

    def clear(self):
        koTerminalHandler.clear(self)
        self._parseRegex = None
        self._cwd = None
        self._currentFile = None
        
        preLength = len(self._data)
        self._data = []
        self._sortedBy = None
        self._proxyRowCountChanged(0, -preLength)

    def getFile(self, index):
        return self._data[index]["file"]
    def getLine(self, index):
        return self._data[index]["line"]
    def getColumn(self, index):
        return self._data[index]["column"]

    def parseLine(self, line):
        """Parse the given line with the current regex and return:
            (file, line, column)

        Raise an exception and set an error on the last error service if
        there is no current regex or the line does not match.
        
        (This is used to handle double-clicks in the command output window's
        scintilla.)
        """
        if not self._parseRegex:
            errmsg = "There was no parse regex specified for this command.";
            self._lastErrorSvc.setLastError(0, errmsg);
            raise ServerException(nsError.NS_ERROR_NOT_AVAILABLE, errmsg)

        match = self._parseRegex.search(line)
        if not match:
            errmsg = "This line does not match the current pattern: '%s'"\
                     % self._parseRegex.pattern
            self._lastErrorSvc.setLastError(0, errmsg);
            raise ServerException(nsError.NS_ERROR_NOT_AVAILABLE, errmsg)

        datum = match.groupdict("")
        if "file" not in datum:
            if self._currentFile:
                datum["file"] = self._currentFile
            else:
                datum["file"] = ""
        elif not _isurl(datum["file"]) \
                and not os.path.isabs(datum["file"]) \
                and self._cwd:
            # If this is a relative path name then prepend the cwd.
            datum["file"] = os.path.join(self._cwd, datum["file"])
        if "line" not in datum:
            datum["line"] = ""
        if "column" not in datum:
            datum["column"] = ""
        return datum["file"], datum["line"], datum["column"]

    def sort(self, sortBy):
        """Sort the current data by the given key. If already sorted by this
        key then reverse the sorting order."""
        if self._sortedBy == sortBy:
            self._data.reverse()
        else:
            try:
                if sortBy in ('runoutput-tree-line',
                              'runoutput-tree-column'):
                    # compare the integer values (line and column string
                    # can possibly be ranges, so pick first part of range)
                    try:
                        self._data.sort(lambda dict1,dict2,sortBy=sortBy:
                                            cmp(int( dict1[sortBy].split('-')[0] ),
                                                int( dict2[sortBy].split('-')[0] ))
                                       )
                    except ValueError:
                        self._data.sort(lambda dict1,dict2,sortBy=sortBy:
                                            cmp(dict1[sortBy], dict2[sortBy])
                                       )
                elif sortBy == 'runoutput-tree-content':
                    # strip leading whitespace for content sort order
                    self._data.sort(lambda dict1,dict2,sortBy=sortBy:
                                        cmp(dict1[sortBy].lstrip(), dict2[sortBy].lstrip())
                                   )
                else:
                    self._data.sort(lambda dict1,dict2,sortBy=sortBy:
                                        cmp(dict1[sortBy], dict2[sortBy])
                                   )
            except KeyError:
                log.error("Cannot sort find results by: '%s'" % sortBy)
                raise
        self._sortedBy = sortBy
        self._tree.beginUpdateBatch()
        self._tree.invalidate()
        self._tree.endUpdateBatch()

    #---- nsITree methods
    def get_rowCount(self):
        return len(self._data)

    def getCellText(self, row, column):
        try:
            datum = self._data[row][column.id]
        except IndexError:
            # Silence this, it is too annoying.
            # c.f. http://bugs.activestate.com/Komodo/show_bug.cgi?id=27487
            #log.error("no %sth result" % row)
            return ""
        except KeyError:
            log.error("unknown result column id: '%s'" % column.id)
            return ""
        #if type(datum) not in (types.StringType, types.UnicodeType):
        #    datum = str(datum)
        return datum

    #---- non-XPCOM methods

    # Must proxy this tree call to the UI, as we are running in a separate
    # thread.
    def _proxyRowCountChanged(self, fromIndex, rowsChanged):
        if self._treeProxy is None:
            self._treeProxy = getProxyForObject(1,
                                    components.interfaces.nsITreeBoxObject,
                                    self._tree, PROXY_ALWAYS | PROXY_ASYNC)
        self._treeProxy.rowCountChanged(fromIndex, rowsChanged)

    def parseAndAddLine(self, line):
        #print "XXX KoRunTerminal.parseAndAddLine(line=%r)" % line
        if not self._parseRegex:
            return
        try:
            match = self._parseRegex.search(line)
        except RuntimeError:
            # Can get an error like the following:
            #   RuntimeError: maximum recursion limit exceeded
            # from the regex engine for rediculously long lines with
            # potential null byte content. Just silently drop those.
            return
        if match:
            datum = match.groupdict("")
            # Ensure that there are reasonable defaults for the std
            # tree column names.
            if "file" not in datum:
                if self._currentFile:
                    datum["file"] = self._currentFile
                else:
                    datum["file"] = ""
            elif not _isurl(datum["file"]) \
                 and not os.path.isabs(datum["file"]) \
                 and self._cwd:
                # If this is a relative path name then prepend the cwd.
                datum["file"] = os.path.join(self._cwd, datum["file"])
            if "line" not in datum:
                datum["line"] = ""
            if "column" not in datum:
                datum["column"] = ""
            if "content" not in datum:
                datum["content"] = line # default "content" to the whole line
            if "runoutput-tree-file" not in datum:
                datum["runoutput-tree-file"] = datum["file"]
            if "runoutput-tree-line" not in datum:
                datum["runoutput-tree-line"] = datum["line"]
            if "runoutput-tree-column" not in datum:
                datum["runoutput-tree-column"] = datum["column"]
            if "runoutput-tree-content" not in datum:
                datum["runoutput-tree-content"] = datum["content"]

            self._data.append(datum)
            self._sortedBy = None

            # Group update calls to the tree for performance.
            self._updateGroupCounter += 1
            if self._updateGroupCounter == self._updateGroupSize:
                self._proxyRowCountChanged(
                    max(0, len(self._data) - 1 - self._updateGroupCounter),
                    self._updateGroupCounter)
                self._updateGroupCounter = 0

    def parsedLastLine(self):
        """Indicates that the last line of data to parse has been send.
        
        This lets the terminal do any necessary finalization.
        """
        if self._updateGroupCounter:
            self._proxyRowCountChanged(
                max(0, len(self._data) - 1 - self._updateGroupCounter),
                self._updateGroupCounter)
            self._updateGroupCounter = 0
