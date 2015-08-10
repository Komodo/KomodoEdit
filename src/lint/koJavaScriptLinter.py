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


from xpcom import components
import koLintResult
from koLintResult import KoLintResult
from koLintResults import koLintResults
import os, sys, re, which
import tempfile
import process
import koprocessutils

from zope.cachedescriptors.property import Lazy as LazyProperty

import logging
log = logging.getLogger("koJavaScriptLinter")
#log.setLevel(logging.DEBUG)

# States for matching standard JS/spidermonkey messages
_JS_STATE_EXP_MESSAGE = 0
_JS_STATE_EXP_CODE = 1
_JS_STATE_EXP_DOTS = 2

_complained = {}

class CommonJSLinter(object):
    _is_macro_re = re.compile("macro2?://")

    @LazyProperty
    def koDirs(self):
        return components.classes["@activestate.com/koDirs;1"]\
                         .getService(components.interfaces.koIDirs)

    def _make_tempfile_from_text(self, request, text):
        # copy file-to-lint to a temp file
        jsfilename = tempfile.mktemp() + '.js'
        # convert to UNIX line terminators before splitting
        isMacro = self._is_macro_re.match(request.koDoc.displayPath)
        if isMacro:
            funcName = request.koDoc.file.leafName;
            lastDot = funcName.rfind('.')
            if lastDot >= 0:
                funcName = funcName[:lastDot]
            # Append "_macro" to avoid collisions with any js keywords
            funcName = re.sub(r'[\W]+', '_', funcName) + "_macro"
            textToAnalyze = "function " + funcName + "() { " + text + "\n}";
        else:
            textToAnalyze = text
        if request.koDoc.language == "XBL":
            # The HTML sub-lang splitter polluted the text, so we need to get
            # the original text from the request object.  This doesn't get
            # analyzed, just underlined by the error displayer.
            datalines = request.content.encode(request.encoding.python_encoding_name).splitlines()
        else:
            datalines = text.splitlines()
        fout = open(jsfilename, 'wb')
        fout.write(textToAnalyze)
        fout.close()
        return jsfilename, isMacro, datalines
    
    def _get_js_interp_path(self):
        if sys.platform.startswith("win"):
            return os.path.join(self.koDirs.mozBinDir, "js.exe")
        else:
            return os.path.join(self.koDirs.mozBinDir, "js")

    def _setLDLibraryPath(self):
        env = koprocessutils.getUserEnv()
        ldLibPath = env.get("LD_LIBRARY_PATH", None)
        if ldLibPath:
            env["LD_LIBRARY_PATH"] = self.koDirs.mozBinDir + ":" + ldLibPath
        else:
            env["LD_LIBRARY_PATH"] = self.koDirs.mozBinDir
        return env

    def lint(self, request):
        text = request.content.encode(request.encoding.python_encoding_name)
        return self.lint_with_text(request, text)

    def _createAddResult(self, results, datalines, errorType, lineNo, desc, numDots):
        # build lint result object
        result = KoLintResult()
        if lineNo >= len(datalines):
            lineNo = len(datalines) - 1
            # if the error is on the last line, work back to the last
            # character of the first nonblank line so we can display
            # the error somewhere
            while lineNo >= 0 and not datalines[lineNo]:
                lineNo -= 1
            if lineNo < 0:
                return
            result.columnEnd = len(datalines[lineNo - 1]) + 1
            result.columnStart = 1
            lineNo += 1
        else:
            if numDots is None:
                result.columnStart = 1
            else:
                result.columnStart = numDots + 1
            result.columnEnd = result.columnStart + 1
        result.lineStart = lineNo
        result.lineEnd = lineNo
        if (errorType.lower().find('warning') >= 0):
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

    _firstLineRe = re.compile(r"^(?P<type>.*?):(?P<desc>.*?)\s*$")
    _lastLineRe = re.compile(r"^(?P<dots>\.*?)\^\s*$")
    _strictLineRe = re.compile(r"^(?P<type>.*?):\s*(?P<dots>\.*?)\^\s*$")
    def lint_with_text(self, request, text):
        encoding_name = request.encoding.python_encoding_name
        if encoding_name not in ("ascii", "utf-8"):
            try:
                # Spidermonkey will choke on latin1 file input - bug 105635 - so try
                # and use UTF-8, else fall back to the original encoding.
                utext = text.decode(request.encoding.python_encoding_name)
                text = utext.encode("utf-8")
            except UnicodeError:
                pass  # Just go with the original text then.
        jsfilename, isMacro, datalines = self._make_tempfile_from_text(request, text)
        cwd = request.cwd
        jsInterp = self._get_js_interp_path()

        # Lint the temp file, the jsInterp options are described here:
        # https://developer.mozilla.org/en/Introduction_to_the_JavaScript_shell
        cmd = [jsInterp, "-c"]

        # Set the JS linting preferences.
        prefset = request.prefset
        if not prefset.getBooleanPref("lintJavaScript_SpiderMonkey"):
            return
        enableWarnings = prefset.getBooleanPref('lintJavaScriptEnableWarnings')
        if enableWarnings:
            cmd.append("-w")
            enableStrict = prefset.getBooleanPref('lintJavaScriptEnableStrict')
            if enableStrict:
                cmd.append("-s")
        else:
            cmd.append("-W")

        cmd.append(jsfilename)
        cwd = cwd or None
        # We only need the stderr result.
        try:
            p = process.ProcessOpen(cmd, cwd=cwd, env=self._setLDLibraryPath(), stdin=None)
            stdout, stderr = p.communicate()
            warnLines = stderr.splitlines(0) # Don't need the newlines.
        except:
            log.exception("Problem running CommonJSLinter")
            warnLines = []
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
        state = _JS_STATE_EXP_MESSAGE  # count index in 3 line groups
        # Mozilla 8 lines have a "0" after the line # -- ignore it
        headerPartRe = re.compile(r"^%s:(?P<lineNo>\d+):\d*\s*(?P<rest>.*)$" % re.escape(jsfilename))

        lineNo = desc = numDots = None
        # Implement this state machine:
        # Start => <starts with filename>
        # Message, ends with desc =>
        # Code, echoes code, not interesting =>
        # Num Dots, shows where on line error starts => Start
        i = -1
        limSub1 = len(strippedWarnLines) - 1
        while i < limSub1:
            i += 1
            line = strippedWarnLines[i]
            if not line:
                continue
            headerMatch = headerPartRe.match(line)
            if not headerMatch:
                if state == _JS_STATE_EXP_CODE:
                    desc += " " + line
                continue
            restLine = headerMatch.group("rest").strip()
            thisLineNo = int(headerMatch.group("lineNo"))
            if state == _JS_STATE_EXP_MESSAGE:
                # first line: get the error description and line number
                firstLineMatch = self._firstLineRe.match(restLine)
                if firstLineMatch:
                    lineNo = thisLineNo
                    if isMacro:
                        if lineNo > len(datalines) + 1:
                            lineNo = len(datalines)
                    errorType = firstLineMatch.group("type")
                    desc = firstLineMatch.group("desc")
                    state = _JS_STATE_EXP_CODE
                else:
                    # continue on this, it's likely just debug build output
                    msg = "Unexpected output when parsing JS syntax check(1) "\
                        "output: '%s'\n" % line
                    log.debug(msg)
                    state = _JS_STATE_EXP_MESSAGE
                continue
            
            if lineNo != thisLineNo:
                # This is actually the start of a new message, so log the current one,
                # and start fresh
                self._createAddResult(results, datalines, errorType, lineNo, desc, 0)
                state = _JS_STATE_EXP_MESSAGE
                desc = None
                i -= 1 # Redo this line
            elif state == _JS_STATE_EXP_CODE:
                # We don't care about this line
                state = _JS_STATE_EXP_DOTS
                continue

            # Now we should be looking at dots
            assert state == _JS_STATE_EXP_DOTS
            lastLineMatch = self._lastLineRe.search(restLine)
            if not lastLineMatch:
                lastLineMatch = self._strictLineRe.search(restLine)
                if not lastLineMatch:
                    # continue on this, it's likely just debug build output
                    msg = "Unexpected output when parsing JS syntax check(2) "\
                          "output: '%s'\n" % line
                    log.debug(msg)
                    continue
            if not desc:
                # if we don't have it, there are debug build lines
                # that have messed us up, restart at zero
                counter = _JS_STATE_EXP_MESSAGE
                continue
            # get the column of the error
            numDots = len(lastLineMatch.group("dots"))
            self._createAddResult(results, datalines, errorType, lineNo, desc, numDots)
            state = _JS_STATE_EXP_MESSAGE
            desc = None

        if desc is not None:
            self._createAddResult(results, datalines, errorType, lineNo, desc, 0)
        return results


class KoJavaScriptLinter(CommonJSLinter):
    _com_interfaces_ = [components.interfaces.koILinter]
    _reg_desc_ = "Komodo XPCShell JavaScript Linter"
    _reg_clsid_ = "{111FBEA1-7CA3-4858-B040-E51CF5A20CE9}"
    _reg_contractid_ = "@activestate.com/koLinter?language=JavaScript;1"
    _reg_categories_ = [
         ("category-komodo-linter", 'JavaScript&type=jsShell'),
         ("category-komodo-linter", 'Node.js&type=jsShell'),
         ]

class KoJSONLinter(CommonJSLinter):
    _com_interfaces_ = [components.interfaces.koILinter]
    _reg_desc_ = "Komodo XPCShell JSON Linter"
    _reg_clsid_ = "{bcd7d132-734c-4d06-811c-383705ccb514}"
    _reg_contractid_ = "@activestate.com/koLinter?language=JSON;1"
    _reg_categories_ = [
         ("category-komodo-linter", "JSON"),
         ]

    def lint_with_text(self, request, text):
        return CommonJSLinter.lint_with_text(self, request, "var x = " + text)
        
class GenericJSLinter(CommonJSLinter):

    def lint(self):
        text = request.content.encode(request.encoding.python_encoding_name)
        return self.lint_with_text(request, text)

    strict_option_re = re.compile(r'\bstrict=')
    def _jslint_with_text(self, request, text, prefSwitchName, prefOptionsName):
        if not text:
            #log.debug("<< no text")
            return
        prefset = request.prefset
        if not prefset.getBooleanPref(prefSwitchName):
            return
        jsfilename, isMacro, datalines = self._make_tempfile_from_text(request, text)
        jsInterp = self._get_js_interp_path()
        jsLintDir = os.path.join(self.koDirs.supportDir, "lint", "javascript")
        jsLintApp = os.path.join(jsLintDir, "lintWrapper.js")
        jsLintBasename = None
        if prefSwitchName == "lintWithJSLint":
            appName = "jslint"
        else:
            appName = "jshint"
        try:
            customJSLint = prefset.getStringPref(appName + "_linter_chooser")
            if customJSLint == "specific":
                p = prefset.getStringPref(appName + "_linter_specific")
                if p and os.path.exists(p):
                    jsLintDir = os.path.dirname(p) + "/"
                    jsLintBasename = os.path.basename(p)
        except:
            log.exception("Problem finding the custom lintjs file")
        options = prefset.getStringPref(prefOptionsName).strip()
        # Lint the temp file, the jsInterp options are described here:
        # https://developer.mozilla.org/en/Introduction_to_the_JavaScript_shell
        cmd = [jsInterp, jsLintApp, "--include=" + jsLintDir]
        if jsLintBasename:
            if prefSwitchName == "lintWithJSLint":
                cmd.append("--jslint-basename=" + jsLintBasename)
            else:
                cmd.append("--jshint-basename=" + jsLintBasename)
        elif prefSwitchName == "lintWithJSHint":
            cmd.append("--jshint")
        if options:
            # Drop empty parts.
            otherParts = [s for s in re.compile(r'\s+').split(options)]
            cmd += [s for s in re.compile(r'\s+').split(options)]
        if request.koDoc.language == "Node.js":
            if not "node=" in options:
                cmd.append("node=1")
        if (prefSwitchName == "lintWithJSHint"
            and not self.strict_option_re.match(options)
            and 'globalstrict=' not in options):
            # jshint tests options.strict !== false, otherwise strict is on
            # Other options are tested as simply !options.strict
            cmd.append('strict=false')

        fd = open(jsfilename)
        cwd = request.cwd or None
        # We only need the stderr result.
        try:
            p = process.ProcessOpen(cmd, cwd=cwd, env=self._setLDLibraryPath(), stdin=fd)
            stdout, stderr = p.communicate()
            if stderr:
                log.warn("Error in jslint/jshint: stderr: %s, command was: %s",
                         stderr, cmd)
            #log.debug("jslint(%s): stdout: %s, stderr: %s", prefSwitchName, stdout, stderr)
            warnLines = stdout.splitlines() # Don't need the newlines.
            i = 0
            outputStart = "++++JSLINT OUTPUT:"
            while i < len(warnLines):
                if outputStart in warnLines[i]:
                    warnLines = warnLines[i + 1:]
                    break
                i += 1
        except:
            log.exception("Problem running GenericJSLinter")
        finally:
            try:
                fd.close()
            except:
                log.error("Problem closing file des(%s)", jsfilename)
            try:
                os.unlink(jsfilename)
            except:
                log.error("Problem deleting file des(%s)", jsfilename)
                
        # 'jslint' error reports come in this form:
        # jslint error: at line \d+ column \d+: explanation
        results = koLintResults()
        msgRe = re.compile("^jslint error: at line (?P<lineNo>\d+) column (?P<columnNo>\d+):\s*(?P<desc>.*?)$")
        numDataLines = len(datalines)
        if len(warnLines) % 2 == 1:
            warnLines.append("")
        for i in range(0, len(warnLines), 2):
            msgLine = warnLines[i]
            evidenceLine = warnLines[i + 1]
            m = msgRe.match(msgLine)
            if m:
                lineNo = int(m.group("lineNo"))
                #columnNo = int(m.group("columnNo"))
                # build lint result object
                result = KoLintResult()
                evidenceLineNo = lineNo
                if evidenceLineNo >= numDataLines:
                    evidenceLineNo = numDataLines - 1
                if evidenceLine in datalines[evidenceLineNo]:
                    lineNo = evidenceLineNo
                    pass
                elif evidenceLineNo > 0 and evidenceLine in datalines[evidenceLineNo - 1]:
                    lineNo = evidenceLineNo - 1
                elif lineNo >= numDataLines:
                    lineNo = numDataLines - 1
                # if the error is on the last line, work back to the last
                # character of the first nonblank line so we can display
                # the error somewhere
                if len(datalines[lineNo]) == 0:
                    while lineNo > 0 and len(datalines[lineNo - 1]) == 0:
                        lineNo -= 1
                result.columnStart =  1
                result.columnEnd = len(datalines[lineNo]) + 1
                result.lineStart = result.lineEnd = lineNo + 1
                result.severity = result.SEV_WARNING
                result.description = m.group("desc")
                results.addResult(result)

        return results


class KoJSLintLinter(GenericJSLinter):
    _com_interfaces_ = [components.interfaces.koILinter]
    _reg_desc_ = "Komodo JSLint Linter"
    _reg_clsid_ = "{6048c9c2-b197-4fca-a718-c0a73d252876}"
    _reg_contractid_ = "@activestate.com/koLinter?language=JavaScript&type=JSLint;1"
    _reg_categories_ = [
         ("category-komodo-linter", 'JavaScript&type=jslint'),
         ("category-komodo-linter", 'Node.js&type=jslint'),
         ]
        
    def lint_with_text(self, request, text):
        return self._jslint_with_text(request, text,
                                      prefSwitchName="lintWithJSLint",
                                      prefOptionsName="jslintOptions")

class KoJSHintLinter(GenericJSLinter):
    """
    JSHint is a fork of JSLint.  It's supposedly more flexible, and
    supports a different set of options.
    """
    _com_interfaces_ = [components.interfaces.koILinter]
    _reg_desc_ = "Komodo JSHint Linter"
    _reg_clsid_ = "{41491bd5-a68f-4397-a66d-22eda3aa8314}"
    _reg_contractid_ = "@activestate.com/koLinter?language=JavaScript&type=JSHint;1"
    _reg_categories_ = [
         ("category-komodo-linter", 'JavaScript&type=jshint'),
         ("category-komodo-linter", 'Node.js&type=jshint'),
         ]
        
    def lint_with_text(self, request, text):
        return self._jslint_with_text(request, text,
                                      prefSwitchName="lintWithJSHint",
                                      prefOptionsName="jshintOptions")

class KoCoffeeScriptLinter(object):
    _com_interfaces_ = [components.interfaces.koILinter]
    _reg_desc_ = "Komodo CoffeeScript Linter"
    _reg_clsid_ = "{85dd97d8-719d-48f2-8c97-9de992ba0ce9}"
    _reg_contractid_ = "@activestate.com/koLinter?language=CoffeeScript&type=;1"
    _reg_categories_ = [
         ("category-komodo-linter", 'CoffeeScript'),
         ]

    def __init__(self):
        try:
            self._userPath = koprocessutils.getUserEnv()["PATH"].split(os.pathsep)
        except:
            msg = "KoCoffeeScriptLinter: can't get user path"
            if msg not in _complained:
                _complained[msg] = None
                log.exception(msg)
            self._userPath = None
        
    def lint(self, request):
        text = request.content.encode(request.encoding.python_encoding_name)
        return self.lint_with_text(request, text)

    def lint_with_text(self, request, text):
        if not text:
            return None
        prefset = request.prefset
        if not prefset.getBooleanPref("lint_coffee_script"):
            return
        try:
            coffeeExe = which.which("coffee", path=self._userPath)
            if not coffeeExe:
                return
            if sys.platform.startswith("win") and os.path.exists(coffeeExe + ".cmd"):
                coffeeExe += ".cmd"
        except which.WhichError:
            msg = "coffee not found"
            if msg not in _complained:
                _complained[msg] = None
                log.error(msg)
            return
        tmpfilename = tempfile.mktemp() + '.coffee'
        fout = open(tmpfilename, 'wb')
        fout.write(text)
        fout.close()
        textlines = text.splitlines()
        cwd = request.cwd
        cmd = [coffeeExe, "-l", "-c", tmpfilename]
        # We only need the stderr result.
        try:
            p = process.ProcessOpen(cmd, cwd=cwd, stdin=None)
            _, stderr = p.communicate()
            warnLines = stderr.splitlines(0) # Don't need the newlines.
        except:
            log.exception("Problem running %s", coffeeExe)
            warnLines = []
        finally:
            os.unlink(tmpfilename)
        ptn = re.compile(r'^Error: In (.*),\s*(.*) on line (\d+):\s*(.*)')
        syntaxErrorPtn = re.compile(r'^SyntaxError: In (.*),\s*(.*) on line (\d+)')
        results = koLintResults()
        for line in warnLines:
            m = ptn.match(line)
            if m:
                part1 = m.group(2)
                lineNo = int(m.group(3))
                part2 = m.group(4)
                desc = "%s on line %d: %s" % (part1, lineNo, part2)
                severity = koLintResult.SEV_ERROR
                koLintResult.createAddResult(results, textlines, severity,
                                             lineNo, desc)
            else:
                m = syntaxErrorPtn.match(line)
                if m:
                    part1 = m.group(2)
                    lineNo = int(m.group(3))
                    desc = "SyntaxError: %s on line %d" % (part1, lineNo)
                    severity = koLintResult.SEV_ERROR
                    koLintResult.createAddResult(results, textlines, severity,
                                                 lineNo, desc)
        return results
