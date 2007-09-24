#!python
# Copyright (c) 2000-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

import os, sys, traceback, re, time
from xpcom import components
from koLintResult import *
from koLintResults import koLintResults
import eollib, tempfile
import logging
import URIlib

log = logging.getLogger("koCSSLinter")


class KoCSSLinter:
    _com_interfaces_ = [components.interfaces.koILinter,
                        components.interfaces.nsIConsoleListener]
    _reg_desc_ = "Komodo CSS Linter"
    _reg_clsid_ = "{F770CBE7-2AAF-492C-8900-CC512CAF5046}"
    _reg_contractid_ = "@activestate.com/koLinter?language=CSS;1"

    results = None

    def __init__(self):
        # XXX unfortunately we have to do this here, since doing it in lint
        # below (which would be optimal) will not work.  The console service
        # creates a proxy back to this object which fails since either lint
        # is in a thread, or because this is a python object.  Not sure which.
        self.csvc = components.classes["@mozilla.org/consoleservice;1"].\
                getService(components.interfaces.nsIConsoleService)
        self.csvc.registerListener(self)

    def lint(self, request):
        """Lint the given CSS content.
        
        Raise an exception  if there is a problem.
        """

        fn = None
        text = request.content.encode(request.encoding.python_encoding_name)
        self.datalines = re.split('\r\n|\r|\n',text)
        cwd = request.cwd

        self.results = koLintResults()

        # save buffer to a temporary file
        try:
            self.fn = fn = tempfile.mktemp()
            self.uri = URIlib.URIParser(self.fn)
            fout = open(fn, 'wb')
            fout.write(text)
            fout.close()
            
            parser = components.classes["@activestate.com/koCSSParser;1"].createInstance(components.interfaces.koICSSParser)
            parser.parseFile(fn)
            
        except Exception, e:
            log.exception(e)

        if fn:
            os.unlink(fn)
        
        # XXX on windows, the CSS parsing appears to be asynchronous rather than
        # synchronous like OSX.  We have to do something about this, but
        # generally CSS parsing is extremely fast so we'll just sleep a little.
        time.sleep(.5)
        
        self.fn = None
        self.datalines = None
        r = self.results
        self.results = None
        return r

    def observe(self, message):
        if self.results is None:
            return
        
        message = message.queryInterface(components.interfaces.nsIScriptError)

        #print "[%s s:%s f:%s l:%s flags:%d]"%(message.errorMessage,
        #                             message.sourceName,
        #                             message.sourceLine,
        #                             message.lineNumber,
        #                             message.flags)

        # XXX TODO a better match between sourceName and self.fn
        uri = URIlib.URIParser(message.sourceName)
        if self.uri.path == uri.path:
            result = KoLintResult()
            result.description = message.errorMessage
            result.lineStart = result.lineEnd = message.lineNumber
            result.columnStart = 1
            result.columnEnd = len(self.datalines[result.lineEnd-1]) + 1
            if message.flags == components.interfaces.nsIScriptError.errorFlag:
                result.severity = result.SEV_ERROR
            elif message.flags == components.interfaces.nsIScriptError.warningFlag:
                result.severity = result.SEV_WARNING
            elif message.flags == components.interfaces.nsIScriptError.exceptionFlag:
                result.severity = result.SEV_ERROR
            elif message.flags == components.interfaces.nsIScriptError.strictFlag:
                result.severity = result.SEV_INFO
            self.results.addResult(result)

            #print "line: %d le: %d cs: %d ce: %d msg: %s" %(result.lineStart,
            #                                                result.lineEnd,
            #                                                result.columnStart,
            #                                                result.columnEnd,
            #                                                result.description)
            
