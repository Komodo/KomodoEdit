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
import threading
from pprint import pprint
import logging

from xpcom import components, nsError, ServerException, COMException
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

    Important: The Scintilla instance should only be used and referenced in
    this class when self.active is True, otherwise there is a chance that the
    Scintilla widget has been removed/destroyed and things will then go bad.
    """
    _com_interfaces_ = [components.interfaces.koITerminalHandler]
    _reg_clsid_ = "36C5DDAA-7A5D-444D-80CA-17D52EBDBA9A"
    _reg_contractid_ = "@activestate.com/koTerminalHandler;1"
    _reg_desc_ = "Terminal View Handler"

    # This handler can be in any one of the following states:

    # Initialized means that there is no process running yet, there may or may
    # not be a scintilla widget attached.
    STATUS_INITIALIZED = 0
    # Running means the process is running and a scintilla widget is attached.
    STATUS_RUNNING = 1
    # Stopping means the process is stopped, but there is still a scintilla
    # widget attached. There may be additional io to come from the stdout/stderr
    # handles that needs to be passed to the scintilla widget.
    STATUS_STOPPING = 2
    # Done means the scintilla widget has been removed. Even if there is a
    # process still running, it should not try to forward on any communications.
    STATUS_DONE = 3

    # A callback handler to be notified when addText is called (i.e. when the
    # scintilla document receives more text).
    _addTextCallbackHandler = None

    def __init__(self):
        self._lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"]\
            .getService(components.interfaces.koILastErrorService)

        self.status = self.STATUS_INITIALIZED
        self.stdin = None
        self.stdinHandler = None
        self.stdout = None
        self.stderr = None
        self._stdout_thread = None
        self._stderr_thread = None
        self._lastPrompt = None
        self.lastWritePosition = 0

        # The io lock is to ensure that multiple waitForIOToFinish() calls do
        # not intersect, otherwise an exception can be generated in some
        # circumstances (when the timing is right).
        self.__io_thread_lock = threading.Lock()

        registryService = components.classes['@activestate.com/koLanguageRegistryService;1'].\
               getService(components.interfaces.koILanguageRegistryService)
        self.language = registryService.getLanguage('Errors');

    #---- koIRunTerminal methods

    @property
    def active(self):
        # active is when the terminal can interact with the process.
        return self.status == self.STATUS_RUNNING

    def setScintilla(self, scintilla):
        log.debug("[%s] KoRunTerminal.setScintilla(%s)", self, scintilla)
        # XXX scintilla MUST NEVER be used from a thread!!!
        self._scintilla = scintilla
        if not scintilla:
            self.status = self.STATUS_DONE

        # Does not look like these are necessary anymore... [ToddW]
        # Synchronization between the terminal and its _KoRunTerminalFile's.
        #self.mutex = threading.Lock()
        #self.ui_mutex = threading.Lock()
        #self.stateChange = threading.Condition()

    def setLanguage(self, lang):
        self.language = lang

    def startSession(self):
        """We must have a Scintilla widget by the time this call is made"""
        log.debug("Start session")
        assert(self._scintilla)
        self.status = self.STATUS_RUNNING
        self.lastWritePosition = 0

    def hookIO(self, stdin, stdout, stderr, name=None):
        # Setup hooks to pipe the stdin, stdout and stderr between the
        # io handles supplied and the Komodo terminal/Scintilla.
        with self.__io_thread_lock:
            if stdin:
                self.stdin = _TerminalWriter("<stdin>", stdin, self, name)
            if stdout:
                self._stdout_thread = _TerminalReader("<stdout>", stdout, self, name)
                self._stdout_thread.start()
            if stderr:
                self._stderr_thread = _TerminalReader("<stderr>", stderr, self, name)
                self._stderr_thread.start()

    def waitForIOToFinish(self, timeout=None):
        # This method is used to wait for the stdout/stderr threads to finish
        # reading all of the available data. Note: the process may actually
        # have finished, but there could still be data to read from the process
        log.debug("[%s] waitForIOToFinish", self)
        with self.__io_thread_lock:
            if self.stdin:
                log.debug("[%s] waitForIOToFinish:: closing stdin", self)
                self.stdin.close()
            if self._stdout_thread:
                log.debug("[%s] waitForIOToFinish:: joining stdout", self)
                self._stdout_thread.join(timeout)
                self._stdout_thread = None
            if self._stderr_thread:
                log.debug("[%s] waitForIOToFinish:: joining stderr", self)
                self._stderr_thread.join(timeout)
                self._stderr_thread = None
        log.debug("[%s] waitForIOToFinish:: done", self)

    def endSession(self):
        self.status = self.STATUS_STOPPING
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

        # If we write to stdin, it ends up here, so we need to pass it along
        # to the real stdin object.
        if name == '<stdin>':
            #log.debug("koTerminalHandler.addText: [%s] [%r]", name, text)
            # The stdin interaction requires an active process.
            if self.status != self.STATUS_RUNNING:
                return
            self.stdin.write(text)
            return

        # The stdout/stderr interaction requires a scintilla widget.
        if self.status in (self.STATUS_RUNNING, self.STATUS_STOPPING):
            self.proxyAddText(length, text, name)

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
    @components.ProxyToMainThread
    def proxyAddText(self, length, text, name):
        # name is either <stderr> or <stdout>
        # Note, the terminal mutex should *must* be aquired before this call.
        #log.debug("koTerminalHandler.proxyAddText: [%s] [%r]", name, text)
        eventMask = 0
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
            self._scintilla.emptyUndoBuffer();
            if self._addTextCallbackHandler is not None:
                self._addTextCallbackHandler.callback(0, text)
          except COMException, e:
            # XXX we're catching an xpcom exception that happens
            # at shutdown. bug #28989
            # Exception: 0x8000ffff (NS_ERROR_UNEXPECTED)
            log.exception(e)
        finally:
          self._scintilla.modEventMask = eventMask
          self.releaseLock()

    def setAddTextCallback(self, handler):
        self._addTextCallbackHandler = handler

    def _moveMarker(self, startMarker, startLine, marker, lastLine):
        if startMarker & (1 << marker) and startLine < lastLine:
            #log.debug("Moving marker %d from %d to %d", marker, startLine, lastLine)
            self._scintilla.markerDelete(startLine, marker)
            self._scintilla.markerAdd(lastLine, marker)

    def notifyEOF(self, channel_name):
        """Notification that there is no more data coming for this io channel.
        This lets the terminal do any necessary finalization.
        """
        pass


class KoRunTerminal(koTerminalHandler, TreeView):
    """This is the interface between run sub-processes and an output
    window, which is implemented as a view element with type=terminal
    (such as the command output window). This acts as the handler for
    events on the output window's <scintilla> widget. It also acts as
    the tree view for the output window's <tree> widget.

    The embedded Scintilla is kept in a 'readOnly' state unless
    currently interacting with the child process (self.active is True).

    Important: The Scintilla instance should only be used and referenced in
    this class when self.active is True, otherwise there is a chance that the
    Scintilla widget has been removed/destroyed and things will then go bad.

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

    def endSession(self):
        koTerminalHandler.endSession(self)
        if self._pbbuf:
            self.parseAndAddLine(self._pbbuf)
            self._pbbuf = ""

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
            # c.f. http://bugs.activestate.com/show_bug.cgi?id=27487
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
    @components.ProxyToMainThreadAsync
    def _proxyRowCountChanged(self, fromIndex, rowsChanged):
        self._tree.rowCountChanged(fromIndex, rowsChanged)

    def parseAndAddLine(self, line):
        if not self._parseRegex:
            return
        if self.status not in (self.STATUS_RUNNING, self.STATUS_STOPPING):
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

    def notifyEOF(self, channel_name):
        """Notification that there is no more data coming for this io channel.
        This lets the terminal do any necessary finalization.
        """
        if self.status not in (self.STATUS_RUNNING, self.STATUS_STOPPING):
            return
        if self._updateGroupCounter:
            self._proxyRowCountChanged(
                max(0, len(self._data) - 1 - self._updateGroupCounter),
                self._updateGroupCounter)
            self._updateGroupCounter = 0

#---- helpers

class _TerminalWriter(object):
    """Give the terminal the ability to safely write to stdin of a process.

    Keeps stdin synchronized so it can be used between different threads.
    """

    _com_interfaces_ = [components.interfaces.koIFile]

    def __init__(self, name, stdin, terminal, cmd=None):
        """Create the link between the terminal and the process stdin.
            "name" is the alias for this type of io.
            "stdin" is the process stdin file handle.
            "terminal" is a koTerminalHandler.
            "cmd" is the process run command that stdin is linked to.
        """
        log.debug("_TerminalWriter.__init__")
        self.__name = name
        self.__stdin = stdin
        self.__terminal = terminal
        self.__cmd = cmd
        # A state change is defined as the buffer being closed or a
        # write occuring.
        self.__closed = 0

    def write(self, s):
        log.debug("_TerminalWriter.write:: s: %r", s)
        # Silently drop writes after the buffer has been close()'d.
        if self.__closed:
            return
        # If empty write, close buffer (mimicking behaviour from
        # koprocess.cpp.)
        if not s:
            self.close()
            return

        #self.__terminal.mutex.acquire()
        try:
            self.__stdin.write(s)
            self.__stdin.flush()
        finally:
            #self.__terminal.mutex.release()
            pass
        log.debug("_TerminalWriter.write:: written succssfully.")

    def writelines(self, list):
        self.write(''.join(list))

    def puts(self, data):
        self.write(data)

    def close(self):
        if not self.__closed:
            log.info("_TerminalWriter.close %r" % self.__name)
            try:
                self.__stdin.close()
            except IOError, ex:
                # The file is already closed or is owned by another thread (see
                # bug 83303) - treat it as if it had closed successfully.
                pass
            self.__closed = 1

class _TerminalReader(threading.Thread):
    """Give the process the ability to safely write to the terminal.

    Ensures all stdout/stderr output is passed on the terminal.
    """

    def __init__(self, name, stdio, terminal, cmd=None):
        """Create the link between the terminal and the process output.
            "name" is the alias for this type of io.
            "stdio" is the process stdout/stderr file handle.
            "terminal" is a koTerminalHandler.
            "cmd" is the process run command that stdin is linked to.
        """
        threading.Thread.__init__(self, name="Process piping thread")
        self.setDaemon(True)
        self.__name = name
        self.__stdio = stdio
        self.__terminal = terminal
        self.__cmd = cmd

    def run(self):
        running = True
        encodingServices = components.classes['@activestate.com/koEncodingServices;1'].\
                         getService(components.interfaces.koIEncodingServices);
        fileno = self.__stdio.fileno()
        name = self.__name
        try:
            while running:
                # We use "os.read()" as it will block until data is available,
                # but it will return when there is at least some data there,
                # though it may not be the full 4096 bytes.
                data = os.read(fileno, 4096)
                if not data:
                    break
                # Anything we get in must be converted to unicode if it
                # isn't already.  Try utf-8 first, if that fails, fallback to
                # the default system encoding.
                try:
                    data, enc, bom = encodingServices.\
                                        getUnicodeEncodedStringUsingOSDefault(data)
                    l = len(data.encode('utf-8'))
                except:
                    l = len(data)
                #self.__terminal.mutex.acquire()
                #try:
                self.__terminal.addText(l, data, name)
                #finally:
                    #self.__terminal.mutex.release()
        except Exception, ex:
            log.exception("_TerminalReader:: exception during %r socket read "
                          "for cmd: %r", name, self.__cmd)
        self.__terminal.notifyEOF(name)
        log.debug("_TerminalReader finished reading %r for cmd: %r",
                  name, self.__cmd)

