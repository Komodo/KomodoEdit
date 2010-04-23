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

import os, sys
import threading
import time
from xpcom import components, nsError, ServerException, COMException
from xpcom._xpcom import PROXY_SYNC, PROXY_ALWAYS, PROXY_ASYNC, getProxyForObject
from xpcom.server import WrapObject, UnwrapObject
from koLintResult import KoLintResult
from koLintResults import koLintResults

import logging
log = logging.getLogger("koLintService")
#log.setLevel(logging.DEBUG)

class RequestQueue:
    # This is a modification if Python's std Queue.Queue class:
    #   - drop maxsize related stuff
    #   - calls are always blocking
    #   - add .prepend() and .remove_uid()
    def __init__(self):
        import thread
        self._init()
        self.mutex = thread.allocate_lock()
        self.esema = thread.allocate_lock() # if acquired, then queue is empty
        self.esema.acquire()

    def put(self, item):
        """Put an item into the queue."""
        log.debug("in RequestQueue.put, acquiring mutex")
        self.mutex.acquire()
        log.debug("in RequestQueue.put, acquired mutex")
        try:
            was_empty = self._empty()
            self._append(item)
            # If we fail before here, the empty state has
            # not changed, so we can skip the release of esema
            if was_empty:
                log.debug("in RequestQueue.put, releasing esema")
                self.esema.release()
        finally:
            # Catching system level exceptions here (RecursionDepth,
            # OutOfMemory, etc) - so do as little as possible in terms
            # of Python calls.
            log.debug("in RequestQueue.put, releasing mutex")
            self.mutex.release()

    def prepend(self, item):
        """Prepend an item to the queue."""
        log.debug("in RequestQueue.prepend, acquiring mutex")
        self.mutex.acquire()
        log.debug("in RequestQueue.prepend, acquired mutex")
        try:
            was_empty = self._empty()
            self._prepend(item)
            # If we fail before here, the empty state has
            # not changed, so we can skip the release of esema
            if was_empty:
                log.debug("in RequestQueue.prepend, releasing esema")
                self.esema.release()
        finally:
            # Catching system level exceptions here (RecursionDepth,
            # OutOfMemory, etc) - so do as little as possible in terms
            # of Python calls.
            log.debug("in RequestQueue.prepend, releasing mutex")
            self.mutex.release()

    def get(self):
        """Remove and return an item from the queue.

        Block if necessary until an item is available.
        """
        log.debug("in RequestQueue.get, acquiring esema")
        self.esema.acquire()
        log.debug("in RequestQueue.get, acquired esema")
        log.debug("in RequestQueue.get, acquiring mutex")
        self.mutex.acquire()
        log.debug("in RequestQueue.get, acquired mutex")
        release_esema = 1
        try:
            item = self._get()
            # Failure means empty state also unchanged - release_esema
            # remains true.
            release_esema = not self._empty()
        finally:
            if release_esema:
                log.debug("in RequestQueue.get, releasing esema")
                self.esema.release()
            log.debug("in RequestQueue.get, releasing mutex")
            self.mutex.release()
        return item

    def remove_uid(self, uid):
        """Remove all current requests with the given uid.

        Does not return anything.
        """
        log.debug("in RequestQueue.remove_uid, acquiring esema")
        if not self.esema.acquire(0): # do not block to acquire lock
            # return if could not acquire: means queue is empty and
            # therefore do not have any items to remove
            log.debug("in RequestQueue.remove_uid, did not acquire esema")
            return
        log.debug("in RequestQueue.remove_uid, acquired mutex")
        log.debug("in RequestQueue.remove_uid, acquiring mutex")
        self.mutex.acquire()
        release_esema = 1
        try:
            self._remove_uid(uid)
            # Failure means empty state also unchanged - release_esema
            # remains true.
            release_esema = not self._empty()
        finally:
            if release_esema:
                log.debug("in RequestQueue.remove_uid, releasing esema")
                self.esema.release()
            log.debug("in RequestQueue.remove_uid, releasing mutex")
            self.mutex.release()

    #---- Override these methods to implement other queue organizations
    # (e.g. stack or priority queue). These will only be called with
    # appropriate locks held.

    # Initialize the queue representation
    def _init(self):
        self.queue = []

    # Check whether the queue is empty
    def _empty(self):
        return not self.queue

    # Put a new item in the queue
    def _append(self, item):
        self.queue.append(item)
    def _prepend(self, item):
        self.queue.insert(0, item)

    # Get an item from the queue
    def _get(self):
        item = self.queue[0]
        del self.queue[0]
        return item

    # Remove all requests with the given uid.
    def _remove_uid(self, uid):
        self.queue = [item for item in self.queue
                      if hasattr(item, "uid") and item.uid != uid]


class KoLintRequest:
    _com_interfaces_ = [components.interfaces.koILintRequest]
    _reg_desc_ = "Komodo Lint Request"
    _reg_clsid_ = "{845A872F-293F-4a82-8552-40849A92EC80}"
    _reg_contractid_ = "@activestate.com/koLintRequest;1"

    def __init__(self):
        self.rid = None
        self.koDoc = None
        self.uid = ''
        self.linterType = ''
        self.cwd = ''
        
        self.content = None
        self.encoding = None
        self.linter = None
        self.results = None
        self.errorString = ''
    
    @property
    def document(self):
        log.debug("`koILintRequest.document` was DEPRECATED in Komodo "
            "6.0.0b1, use `koILintRequest.koDoc`.")
        return self.koDoc
    
    def describe(self):
        return "<KoLintRequest: %s on uid %s>" % (self.linterType, self.uid)


class KoLintService:
    _com_interfaces_ = [components.interfaces.koILintService,
                        components.interfaces.nsIObserver]
    _reg_desc_ = "Komodo Lint Management Service"
    _reg_clsid_ = "{9FD67601-CB60-411D-A212-ED21B3D25C15}"
    _reg_contractid_ = "@activestate.com/koLintService;1"

    def __init__(self):
        log.info("KoLintService.__init__()")

        self._linterCache = {} # mapping of linterCID to koILinter instance
        self.requests = RequestQueue() # an item of None is the quit sentinel
        self._shuttingDown = 0
        self.manager = threading.Thread(target=self.run, name="Linter")
        self.manager.setDaemon(True)
        self.manager.start()

        self._wrapped = WrapObject(self, components.interfaces.nsIObserver)
        _observerSvc = components.classes["@mozilla.org/observer-service;1"].\
            getService(components.interfaces.nsIObserverService)
        _observerSvc.addObserver(self._wrapped, 'xpcom-shutdown', 1)
        self._prefs = components.classes["@activestate.com/koPrefService;1"].\
            getService(components.interfaces.koIPrefService).prefs

    def observe(self, subject, topic, data):
        #print "file status service observed %r %s %s" % (subject, topic, data)
        if topic == 'xpcom-shutdown':
            log.debug("file status got xpcom-shutdown, unloading");
            self.terminate()

    def terminate(self):
        log.info("KoLintService.terminate()")
        self.requests.prepend(None) # prepend the quit sentinel
        self._shuttingDown = 1
        # Do NOT attempt to .join() the manager thread because it is nigh on
        # impossible to avoid all possible deadlocks.

    def _getLinter(self, linterCID):
        """Return a koILinter XPCOM component of the given linterCID.
        
        This method cache's linter instances. If there is no such linter
        then an exception is raised.
        """
        if linterCID not in self._linterCache:
            if linterCID not in components.classes.keys():
                linter = None
            else:
                try:
                    linter = components.classes[linterCID].createInstance(components.interfaces.koILinter)
                except COMException, ex:
                    errmsg = "Internal Error creating a linter with CID '%s': %s"\
                        % (linterCID, ex)
                    raise ServerException(nsError.NS_ERROR_UNEXPECTED, errmsg)
            self._linterCache[linterCID] = linter

        return self._linterCache[linterCID]

    def addRequest(self, request):
        """Add the given request to the queue.
        
        If there is an error (e.g. bogus linterType) an exception is raised.
        """
        log.info("KoLintService.addRequest(%s)", request.describe())
        
        # Fill out the request (because document access and component
        # creation must often be done in the main thread).
        request.content = request.koDoc.buffer
        request.encoding = request.koDoc.encoding
        if request.linterType:
            request.linter = self._getLinter(request.linterType)
        # Proxy this so the worker thread can report results on this iface.
        request.lintBuffer = getProxyForObject(None,
            components.interfaces.koILintBuffer, request.lintBuffer,
            PROXY_ALWAYS | PROXY_SYNC)

        self.requests.put(request)

    def cancelPendingRequests(self, uid):
        log.info("KoLintService.cancelPendingRequests(uid='%s')", uid)
        self.requests.remove_uid(uid)
        # This does nothing to stop the reporting of results from a
        # possible _currently running_ lint request for this uid.
        # This is currently handled on the JavaScript side via the
        # koILintRequest.rid attribute.

    def _getEncodingLintResults(self, content, encoding):
        """Return lint results for encoding errors in the given document.
        
            "content" is the document content as a unicode string
            "encoding" is the currently selected encoding for the document
        
        Returns a koLintResults instance.
        """
        try:
            encodedString = content.encode(encoding.python_encoding_name,
                                           "strict")
        except UnicodeError, ex:
            pass  # errors are handled after the try/except/else block
        else:
            return koLintResults() # no encoding errors
        
        # Find the specific errors by encoding with "replace" and finding
        # where those replacements were.
        escapedContent = content.replace('?', 'X')
        encodedString = escapedContent.encode(encoding.python_encoding_name,
                                              "replace")
        offset = 0
        indeces = []
        while 1:
            index = encodedString.find('?', offset)
            if index == -1:
                break
            indeces.append(index)
            offset = index + 1
        log.debug("encoding errors at indeces %s", indeces)
            
        results = koLintResults()
        lines = content.splitlines(1) # keep line terminators
        offset = 0 # the current offset in the document
        for i in range(len(lines)):
            line = lines[i]
            while indeces and indeces[0] < offset + len(line):
                index = indeces.pop(0) # this index is on this line
                r = KoLintResult()
                r.description = "This character cannot be represented with "\
                                "the current encoding: '%s'"\
                                % encoding.python_encoding_name
                r.lineStart = i+1
                r.lineEnd = i+1
                r.columnStart = index - offset + 1
                r.columnEnd = r.columnStart + 1
                log.debug("encoding error: index=%d: %d,%d-%d,%d", index,
                          r.lineStart, r.columnStart, r.lineEnd, r.columnEnd)
                r.severity = r.SEV_ERROR
                results.addResult(r)
            if not indeces:
                break
            offset += len(line)
        else:
            raise ValueError("Did not find line and column for one or "
                             "more indeces in content: %s" % indeces)

        return results

    def _addMixedEOLWarnings(self, results, content, expectedEOL):
        """Add lint results (at the WARNING level) for each line that has
        an unexpected EOL.
        
            "results" in a koILintResults to which to add mixed EOL results.
            "content" is the content to analyze
            "expectedEOL" is the currently configured EOL for the document,
                this must be on of the EOL_LF, EOL_CR, EOL_CRLF constants.
        """
        import eollib
        mixedEOLs = eollib.getMixedEOLLineNumbers(content, expectedEOL)
        if not mixedEOLs:
            return

        # Add a warning lint result for each such line.
        expectedEOLStr = eollib.eol2eolPref[expectedEOL]
        lines = content.splitlines(1)
        for lineNum in mixedEOLs:
            r = KoLintResult()
            r.description = "This line does not end with the expected "\
                            "EOL: '%s' (select View | View EOL Markers)"\
                            % expectedEOLStr
            r.lineStart = lineNum+1
            r.lineEnd = lineNum+1
            r.columnStart = 1
            r.columnEnd = len(lines[lineNum]) + 1
            r.severity = r.SEV_WARNING
            results.addResult(r)

    def run(self):
        """Process lint requests serially until told to stop.
        
        Before the requested linter is run on a document it is first checked
        for encoding problems (i.e. encoding is not sufficient for current
        content).
        """
        TIME_LINTS = False
        log.info("manager thread: start")
        while 1:
            try:
                # wait for next request
                request = self.requests.get()
                
                # quit if request is the quit sentinel
                if request is None:
                    log.info("manager thread: quit sentinel")
                    break
    
                # process the request
                if TIME_LINTS: startlint = time.clock()
                log.info("manager thread: process request: %r", request)
                try:
                    # Look for encoding errors first.
                    results = self._getEncodingLintResults(request.content,
                                                           request.encoding)
                    if TIME_LINTS: endencodinglint = time.clock()

                    # If there were no encoding errors, try the
                    # requested linter.
                    if not results.getNumResults() and request.linter:
                        #XXX This is where context-sensitive linting args should
                        #    be passed in, but linters don't support this yet.
                        log.debug("manager thread: call linter.lint(request)")
                        results = request.linter.lint(request)
                        log.debug("manager thread: linter.lint(request) returned")
                    if TIME_LINTS: endlintlint = time.clock()

                    if request.koDoc.prefs.getBooleanPref("lintEOLs"):
                        # Also look for mixed-line endings warnings.
                        self._addMixedEOLWarnings(results, request.content,
                            request.koDoc.new_line_endings)

                    if TIME_LINTS:
                        endeollint = time.clock()
                        print "lint of '%s': encoding=%.3fs  lint=%.3fs  eol=%.3fs"\
                              % (request.koDoc.baseName,
                                 endencodinglint-startlint,
                                 endlintlint-endencodinglint,
                                 endeollint-endlintlint)
    
                    request.results = results
                except (ServerException, COMException), ex:
                    request.errorString = str(ex)
                except:
                    # Any exceptions that are not ServerException or
                    # COMException are unexpected internal errors.
                    err = "unexpected internal error checking '%s' with '%s' linter"\
                          % (request.koDoc.baseName, request.linterType)
                    log.exception(err)
                    request.errorString = err
                else:
                    log.info("manager thread: lint results for uid %s: %r",
                             request.uid, results)

                # Notify of request completion
                # Note: this is not guaranteed to properly guard the proxy
                # call because a context switch could happen in between the
                # condition check and body. That is ok though. At worst it
                # will raise an exception that will be trapped just below.
                # The point is to catch the common case. I am pretty sure
                # that there is no way to do this properly without going
                # to great lengths.
                if not self._shuttingDown:
                    try:
                        request.lintBuffer.reportResults(request)
                    except COMException, ex:
                        # Ignore this error, which will happen if results
                        # are reported after the buffer has gone away (i.e.
                        # the file owning that buffer was closed):
                        #   Traceback (most recent call last):
                        #     File "...\koLintService.py", line 370, in run
                        #       request.lintBuffer.reportResults(request)
                        #     File "<XPCOMObject method 'reportResults'>", line 3, in reportResults
                        #   Exception: 0x80570021 ()
                        errno = ex.args[0]
                        if errno == 0x80570021:
                            pass
                        else:
                            raise
            except:
                # Something bad happened, but don't let this thread die.
                log.exception("unexpected error in the linting thread")
            
        log.info("manager thread: end")



if __name__ == "__main__":
    logging.basicConfig()
    import pprint
    class TestRequest:
        def __init__(self, uid):
            self.uid = uid
        def __repr__(self):
            return "<TestRequest: uid=%s>" % self.uid
    q = RequestQueue()

    if 0:
        q.put(TestRequest("id_1"))
        q.remove_uid("id_1")
        print "item:"
        sys.stdout.flush()
        print q.get()
    
    if 1:    
        q.put(TestRequest("id_1"))
        q.put(TestRequest("id_2"))
        pprint.pprint(q.queue)
        print "item: ", q.get()
        q.put(TestRequest("id_3"))
        q.put(TestRequest("id_4"))
        q.put(TestRequest("id_3"))
        q.prepend(None)
        pprint.pprint(q.queue)
        q.remove_uid("id_3")
        pprint.pprint(q.queue)
        q.remove_uid("id_3")
        sys.stdout.flush()
        pprint.pprint(q.queue)
        q.remove_uid("id_4")
        pprint.pprint(q.queue)
        print "item: ", q.get()
        print "item: ", q.get()
        pprint.pprint(q.queue)

