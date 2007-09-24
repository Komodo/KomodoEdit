#!python
# Copyright (c) 2000-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.


from xpcom import components, nsError, ServerException
from koLintResult import *
from koLintResults import koLintResults
import os, sys, re
import tempfile
import process

import logging
log = logging.getLogger("koXPCShellLinter")
#log.setLevel(logging.DEBUG)

class KoXPCShellLinter:
    _com_interfaces_ = [components.interfaces.koILinter]
    _reg_desc_ = "Komodo XPCShell JavaScript Linter"
    _reg_clsid_ = "{111FBEA1-7CA3-4858-B040-E51CF5A20CE9}"
    _reg_contractid_ = "@activestate.com/koLinter?language=JavaScript;1"

    def __init__(self):
        self.infoSvc = components.classes["@activestate.com/koInfoService;1"].\
            getService(components.interfaces.koIInfoService)
        self.isDebugBuild = self.infoSvc.buildType == "debug"

    def lint(self, request):
        text = request.content.encode(request.encoding.python_encoding_name)
        cwd = request.cwd

        # copy file-to-lint to a temp file
        jsfilename = tempfile.mktemp() + '.js'
        # convert to UNIX line terminators before splitting
        datalines = re.sub("\r\n|\r", "\n", text).split("\n")
        fout = open(jsfilename, 'w')
        fout.write(text)
        fout.close()

        koDirs = components.classes["@activestate.com/koDirs;1"].\
                              getService(components.interfaces.koIDirs)
        if sys.platform.startswith("win"):
            jsInterp = os.path.join(koDirs.mozBinDir, "js.exe")
        else:
            jsInterp = os.path.join(koDirs.mozBinDir, "js")

        # lint the temp file
        cmd = [jsInterp, "-version", "170", "-C", "-w", "-s", jsfilename]
        cwd = cwd or None
        #XXX For one reason or another, ProcessProxy does not work with the
        #    standalone js interpreter on windows, perhaps the js process is
        #    ending too quickly?  ProcessProxy will work if you touch js32.dll,
        #    which I am guessing forces the system disk cache to refetch the dll
        p = process.ProcessOpen(cmd, cwd=cwd)
        p.stdin.close()
        p.stdout.close()
        warnLines = p.stderr.readlines()
        p.close()
        os.unlink(jsfilename)
        
        # 'js' error reports come in 4 line chunks that look like
        # this:
        #    <filename>:8: SyntaxError: missing ; before statement:
        #    <filename>:8: ar asdf = 1;
        #
        #    <filename>:8: ...^
        #    <filename>:8: strict warning: function does not always return value:
        #    <filename>:8: strict warning:     },
        #
        #    <filename>:8: strict warning: ...^
        # There is one exception: if the file is only one line then
        # the third blank line is not there. THerefore we will strip
        # empty lines and parse 3 line chunks.
        strippedWarnLines = [line for line in warnLines if line.strip()]

        # Parse out the xpcshell lint results
        results = koLintResults()
        counter = 0  # count index in 3 line groups
        firstLineRe = re.compile("^%s:(?P<lineNo>\d+):\s*(?P<type>.*?):(?P<desc>.*?):\s*$" %\
            re.escape(jsfilename))
        lastLineRe = re.compile("^%s:(?P<lineNo>\d+):\s*(?P<dots>.*?)\^\s*$" %\
            re.escape(jsfilename))
        strictLineRe = re.compile("^%s:(?P<lineNo>\d+):\s*(?P<type>.*?):\s*(?P<dots>.*?)\^\s*$" %\
            re.escape(jsfilename))
        desc = None
        for line in strippedWarnLines:
            if counter == 0 and line.startswith(jsfilename):
                # first line: get the error description and line number
                firstLineMatch = firstLineRe.search(line.strip())
                if firstLineMatch:
                    lineNo = int(firstLineMatch.group("lineNo"))
                    errorType = firstLineMatch.group("type")
                    desc = firstLineMatch.group("desc")
                else:
                    # continue on this, it's likely just debug build output
                    msg = "Unexpected output when parsing JS syntax check "\
                        "output: '%s'\n" % line
                    log.debug(msg)
                    continue
            elif counter == 2:
                if not desc:
                    # if we don't have it, there is debug build lines
                    # that have messed us up, restart at zero
                    counter = 0
                    continue
                # get the column of the error
                lastLineMatch = lastLineRe.search(line.strip())
                if not lastLineMatch:
                    lastLineMatch = strictLineRe.search(line.strip())
                    
                if lastLineMatch:
                    numDots = len(lastLineMatch.group("dots"))
                else:
                    # continue on this, it's likely just debug build output
                    msg = "Unexpected output when parsing JS syntax check "\
                          "output: '%s'\n" % line
                    log.debug(msg)
                    continue
                # build lint result object
                result = KoLintResult()
                if lineNo >= len(datalines):
                    # if the error is on the last line, work back to the last
                    # character of the first nonblank line so we can display
                    # the error somewhere
                    while len(datalines[lineNo - 1]) == 0:
                        lineNo -= 1
                    result.columnEnd = len(datalines[lineNo - 1])
                    result.columnStart = result.columnEnd - 1
                else:
                    result.columnStart = numDots + 1
                    result.columnEnd = result.columnStart + 1
                result.lineStart = lineNo
                result.lineEnd = lineNo
                if (errorType.lower().find('warning') > 0):
                    result.severity = result.SEV_WARNING
                else:
                    result.severity = result.SEV_ERROR
                # This always results in a lint result spanning a single
                # character, which, given the squiggly reporting scheme is
                # almost invisible. Workaround: set the result to be the
                # whole line and append the column number to the description.
                result.description = "%s: %s (on column %d)" % (errorType,desc,result.columnStart)
                result.columnStart = 1
                result.columnEnd = len(datalines[lineNo-1])+1
                results.addResult(result)
            counter = (counter + 1) % 3

        return results


