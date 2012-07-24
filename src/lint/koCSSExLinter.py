#!python
# Copyright (c) 2000-2011 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

# Use the silvercity tokenizer and parse text here
# Support for SCSS (CSS-like Sass) and Less as well.

import os.path
import process
import re
import tempfile
import which

from koLintResult import createAddResult, KoLintResult, getProxiedEffectivePrefs
import koLintResult
from koLintResults import koLintResults
import koprocessutils
import logging
from xpcom import components
from codeintel2.css_linter import CSSLinter

log = logging.getLogger("koCSSLinter")
#log.setLevel(logging.DEBUG)

class KoBasicCSSLinter(object):
    def lint(self, request):
        """Lint the given CSS content.
        
        Raise an exception  if there is a problem.
        """
        text = request.content.encode(request.encoding.python_encoding_name)
        return self.lint_with_text(request, text)
        
    def lint_with_text(self, request, text): #pylint: disable=R0201
        textlines = text.splitlines()
        results = CSSLinter().lint(text, request.koDoc.language)
        lintResults = koLintResults()
        for r in results:
            if r.line_start is None:
                createAddResult(lintResults, textlines, r.status + 1,
                                len(textlines) - 1,
                                r.message)
            else:
                result = KoLintResult(description=r.message,
                                      severity=r.status + 1,
                                      lineStart=r.line_start,
                                      lineEnd=r.line_end,
                                      columnStart=r.col_start + 1,
                                      columnEnd=r.col_end + 1)
                lintResults.addResult(result)
        return lintResults
    
class KoCSSLinter(KoBasicCSSLinter):
    """
    This class is mostly a parser.
    """
    _com_interfaces_ = [components.interfaces.koILinter,
                        components.interfaces.nsIConsoleListener]
    _reg_desc_ = "Komodo CSS Linter"
    _reg_clsid_ = "{ded22115-148a-4a2f-aef1-2ae7e12395b0}"
    _reg_contractid_ = "@activestate.com/koLinter?language=CSS;1"
    _reg_categories_ = [
         ("category-komodo-linter", 'CSS'),
         ("category-komodo-linter", 'Less'),
         ]

class KoSCCLinter(KoCSSLinter):
    _com_interfaces_ = [components.interfaces.koILinter,
                        components.interfaces.nsIConsoleListener]
    _reg_desc_ = "Komodo CSS Linter"
    _reg_clsid_ = "{32b99faa-e3aa-49dc-a54f-4a7a245ff199}"
    _reg_contractid_ = "@activestate.com/koLinter?language=SCSS;1"
    _reg_categories_ = [
         ("category-komodo-linter", 'SCSS'),
         ]
            
    def lint_with_text(self, request, text):
        try:
            prefset = getProxiedEffectivePrefs(request)
            scssLinterType = prefset.getStringPref("scssLinterType")
            if scssLinterType == "none":
                return
            if scssLinterType == "builtin":
                return KoCSSLinter.lint_with_text(self, request, text)
            scssPath = prefset.getStringPref("scssDefaultInterpreter")
            # The 'or' part handles any language for "Find on Path"
            if (not scssPath) or not os.path.exists(scssPath):
                try:
                    scssPath = which.which("scss")
                    if scssPath:
                        prefset.getStringPref("scssDefaultInterpreter")
                except which.WhichError:
                    pass
            if not scssPath or not os.path.exists(scssPath):
                log.warn("Setting scssLinterType to 'default': scss not found")
                prefset.getStringPref("scssLinterType", "builtin")
                return KoCSSLinter.lint_with_text(self, request, text)
            rubyPath = os.path.join(os.path.dirname(scssPath), "ruby") + os.path.splitext(scssPath)[1]
            if not os.path.exists(rubyPath):
                log.warn("Setting scssLinterType to 'default': no ruby found to drive scss")
                prefset.getStringPref("scssLinterType", "builtin")
                return KoCSSLinter.lint_with_text(self, request, text)
            
            # Run scss
            tmpfilename = tempfile.mktemp() + '.scss'
            fout = open(tmpfilename, 'wb')
            fout.write(text)
            fout.close()
            textlines = text.splitlines()
            cmd = [rubyPath, scssPath, "-c", tmpfilename]
            cwd = request.cwd or None
            # We only need the stderr result.
            try:
                p = process.ProcessOpen(cmd, cwd=cwd, env=koprocessutils.getUserEnv(), stdin=None)
                _, stderr = p.communicate()
                warnLines = stderr.splitlines(0) # Don't need the newlines.
            except:
                warnLines = []
            finally:
                os.unlink(tmpfilename)
        except:
            log.exception("scss: lint_with_text: big fail")
            warnLines = []
        ptn = re.compile(r'^\s*on line (\d+) of (.*)$')
        syntaxErrorPtn = re.compile(r'^Syntax error:\s*(.*)$')
        results = koLintResults()
        prevLine = ""
        for line in warnLines:
            m = ptn.match(line)
            if m:
                lineNo = int(m.group(1))
                m2 = syntaxErrorPtn.match(prevLine)
                if m2:
                    severity = koLintResult.SEV_ERROR
                    msg = m2.group(1)
                else:
                    severity = koLintResult.SEV_WARNING
                    msg = prevLine
                desc = "scss: " + msg
                koLintResult.createAddResult(results, textlines, severity, lineNo, desc)
            else:
                prevLine = line
        return results
        

