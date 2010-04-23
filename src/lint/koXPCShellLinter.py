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


from xpcom import components, nsError, ServerException
from xpcom._xpcom import PROXY_SYNC, PROXY_ALWAYS, PROXY_ASYNC
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
        proxyMgr = components.classes["@mozilla.org/xpcomproxy;1"].\
                    getService(components.interfaces.nsIProxyObjectManager)
        prefSvc = components.classes["@activestate.com/koPrefService;1"].\
                    getService(components.interfaces.koIPrefService)
        self._prefProxy = proxyMgr.getProxyForObject(None,
                    components.interfaces.koIPrefService, prefSvc,
                    PROXY_ALWAYS | PROXY_SYNC)

    def lint(self, request):
        text = request.content.encode(request.encoding.python_encoding_name)
        cwd = request.cwd

        # copy file-to-lint to a temp file
        jsfilename = tempfile.mktemp() + '.js'
        # convert to UNIX line terminators before splitting
        isMacro = request.koDoc.displayPath.startswith("macro://")
        if isMacro:
            funcName = request.koDoc.file.leafName;
            lastDot = funcName.rfind('.')
            if lastDot >= 0:
                funcName = funcName[:lastDot]
            # Append "_macro" to avoid collisions with any js keywords
            funcName = re.sub(r'[\W]+', '_', funcName) + "_macro"
            textToAnalyze = "function " + funcName + "() {\n" + text + "\n}";
        else:
            textToAnalyze = text
        datalines = re.sub("\r\n|\r", "\n", text).split("\n")
        fout = open(jsfilename, 'w')
        fout.write(textToAnalyze)
        fout.close()

        koDirs = components.classes["@activestate.com/koDirs;1"].\
                              getService(components.interfaces.koIDirs)
        if sys.platform.startswith("win"):
            jsInterp = os.path.join(koDirs.mozBinDir, "js.exe")
        else:
            jsInterp = os.path.join(koDirs.mozBinDir, "js")

        # Lint the temp file, the jsInterp options are described here:
        # https://developer.mozilla.org/en/Introduction_to_the_JavaScript_shell
        cmd = [jsInterp, "-version", "170", "-C"]

        # Set the JS linting preferences.
        enableWarnings = self._prefProxy.prefs.getBooleanPref('lintJavaScriptEnableWarnings')
        if enableWarnings:
            cmd.append("-w")
            enableStrict = self._prefProxy.prefs.getBooleanPref('lintJavaScriptEnableStrict')
            if enableStrict:
                cmd.append("-s")
        else:
            cmd.append("-W")

        cmd.append(jsfilename)
        cwd = cwd or None
        # We only need the stderr result.
        try:
            p = process.ProcessOpen(cmd, cwd=cwd, stdin=None)
            stdout, stderr = p.communicate()
            warnLines = stderr.splitlines(0) # Don't need the newlines.
        finally:
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
                    if isMacro:
                        if lineNo > len(datalines) + 1:
                            lineNo = len(datalines)
                        else:
                            lineNo -= 1
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


