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

"""
    koILinter implementation for Python Syntax Checking

    Requirements:
    - Should work for old versions of Python back to Python 1.5.2.
    - Should pick up warnings from Python's warnings framework.

    Design:
    - Run "python pycompile.py <temp_file_with_given_python_code>"
      on the given text and process the stdout (syntax errors) and
      stderr (warning's framework warnings).
"""

import os, sys
import re, which
import tempfile
import process
import koprocessutils
from xpcom import components, nsError, ServerException
import logging
from pprint import pprint# , pformat

import koLintResult
from koLintResult import KoLintResult, getProxiedEffectivePrefs
from koLintResults import koLintResults
import koprocessutils

import projectUtils

log = logging.getLogger('koPythonLinter')
#log.setLevel(logging.DEBUG)

_leading_ws_re = re.compile(r'(\s*)')

class _GenericPythonLinter(object):
    _com_interfaces_ = [components.interfaces.koILinter]

    def __init__(self):
        self._pythonInfo = components.classes["@activestate.com/koAppInfoEx?app=Python;1"]\
               .createInstance(components.interfaces.koIAppInfoEx)
        self._userPath = koprocessutils.getUserEnv()["PATH"].split(os.pathsep)
        
    def lint(self, request):
        text = request.content.encode(request.encoding.python_encoding_name)
        return self.lint_with_text(request, text)

class KoPythonPyLintChecker(_GenericPythonLinter):
    _reg_desc_ = "Komodo Python PyLint Linter"
    _reg_clsid_ = "{e9e6d883-a712-46fc-a4a5-83c827aeff44}"
    _reg_contractid_ = "@activestate.com/koLinter?language=Python&type=pylint;1"
    _reg_categories_ = [
         ("category-komodo-linter", 'Python&type=pylint'),
         ]
        
    nonIdentChar_RE = re.compile(r'^\w_.,=')
    def lint_with_text(self, request, text):
        if not text:
            return None
        prefset = getProxiedEffectivePrefs(request)
        if not prefset.getBooleanPref("lint_python_with_pylint"):
            return
        # if not prefset.getBooleanPref("lintWithPylint"): return
        pythonExe = self._pythonInfo.getExecutableFromDocument(request.koDoc)
        if not pythonExe:
            return
        tmpfilename = tempfile.mktemp() + '.py'
        fout = open(tmpfilename, 'w')
        fout.write(text)
        fout.close()
        textlines = text.splitlines()
        cwd = request.cwd
        pylintExe = "pylint"
        if sys.platform.startswith("win"):
            pylintExe += ".exe"
        try:
            pylintExe = which.which("pylint", path=self._userPath)
        except which.WhichError:
            log.warn("pylint not found")
            return
        if not pylintExe:
            log.warn("pylint not found")
            return
        rcfilePath = prefset.getStringPref("pylint_checking_rcfile")
        if rcfilePath and os.path.exists(rcfilePath):
            if self.nonIdentChar_RE.search(rcfilePath):
                rcfilePath = '"' + rcfilePath + '"'
            extraArgs = [ "--rcfile=" + rcfilePath ]
        else:
            # Hardwire in these three messages:
            extraArgs = []# [ "-d", "C0103", "-d" , "C0111", "-d", "F0401"]
        preferredLineWidth = prefset.getLongPref("editAutoWrapColumn")
        if preferredLineWidth > 0:
            extraArgs.append("--max-line-length=%d" % preferredLineWidth)
            
        cmd = [pythonExe, pylintExe, "-f", "text", "-r", "n", "-i", "y"] + extraArgs
        # Put config file entry here: .rcfile=<file>
        cmd.append(tmpfilename)
        cwd = request.cwd or None
        # We only need the stdout result.
        try:
            p = process.ProcessOpen(cmd, cwd=cwd, env=koprocessutils.getUserEnv(), stdin=None)
            stdout, _ = p.communicate()
            warnLines = stdout.splitlines(0) # Don't need the newlines.
        finally:
            os.unlink(tmpfilename)
        ptn = re.compile(r'^([A-Z])(\d+):\s*(\d+):\s*(.*)')
        results = koLintResults()
        for line in warnLines:
            m = ptn.match(line)
            if m:
                status = m.group(1)
                statusCode = m.group(2)
                lineNo = int(m.group(3))
                desc = "pylint: %s%s %s" % (status, statusCode,
                                                          m.group(4))
                if status in ("E", "F"):
                    severity = koLintResult.SEV_ERROR
                elif status in ("C", "R", "W"):
                    severity = koLintResult.SEV_WARNING
                else:
                    #log.debug("Skip %s", line)
                    continue
                koLintResult.createAddResult(results, textlines, severity, lineNo, desc)
        return results

class KoPythonPyflakesChecker(_GenericPythonLinter):
    _reg_desc_ = "Komodo Python Pyflakes Linter"
    _reg_clsid_ = "{7617c1bc-0e12-4c26-9a1a-0c03f2d8c8d2}"
    _reg_contractid_ = "@activestate.com/koLinter?language=Python&type=pyflakes;1"
    _reg_categories_ = [
         ("category-komodo-linter", 'Python&type=pyflakes'),
         ]
        
    def lint_with_text(self, request, text):
        if not text:
            return None
        prefset = getProxiedEffectivePrefs(request)
        if not prefset.getBooleanPref("lint_python_with_pyflakes"):
            return
        pythonExe = self._pythonInfo.getExecutableFromDocument(request.koDoc)
        if not pythonExe:
            return
        tmpfilename = tempfile.mktemp() + '.py'
        fout = open(tmpfilename, 'w')
        fout.write(text)
        fout.close()
        textlines = text.splitlines()
        cwd = request.cwd
        try:
            checkerExe = which.which("pyflakes", path=self._userPath)
        except which.WhichError:
            log.warn("pyflakes not found")
            return
        if not checkerExe:
            log.warn("pyflakes not found")
            return
            
        cmd = [pythonExe, checkerExe, tmpfilename]
        cwd = request.cwd or None
        # We only need the stdout result.
        try:
            p = process.ProcessOpen(cmd, cwd=cwd, env=koprocessutils.getUserEnv(), stdin=None)
            _, stderr = p.communicate()
            warnLines = stderr.splitlines(0) # Don't need the newlines.
        finally:
            os.unlink(tmpfilename)
        ptn = re.compile(r'^(.+?):(\d+):\s+(.*)')
        results = koLintResults()
        for line in warnLines:
            m = ptn.match(line)
            if m:
                lineNo = int(m.group(2))
                desc = "pyflakes: %s" % (m.group(3),)
                severity = koLintResult.SEV_ERROR
                koLintResult.createAddResult(results, textlines, severity, lineNo, desc)
        return results

class KoPythonPycheckerLinter(_GenericPythonLinter):
    """
    Instead of checking your Python code using pylinter,
      this one lints    your Python code using pychecker.
    """
    _reg_desc_ = "Komodo Python Pychecker Linter"
    _reg_clsid_ = "{d3eb77c9-fb1f-4849-8e27-2e39d15c5331}"
    _reg_contractid_ = "@activestate.com/koLinter?language=Python&type=pychecker;1"
    _reg_categories_ = [
         ("category-komodo-linter", 'Python&type=pychecker'),
         ]
        
    nonIdentChar_RE = re.compile(r'^\w_.,=')
    def lint_with_text(self, request, text):
        if not text:
            return None
        prefset = getProxiedEffectivePrefs(request)
        if not prefset.getBooleanPref("lint_python_with_pychecker"):
            return
        pychecker = prefset.getStringPref("pychecker_wrapper_location")
        if not pychecker:
            return
        if sys.platform.startswith("win") and not os.path.exists(pychecker):
            if os.path.exists(pychecker + ".bat"):
                pychecker = pychecker + ".bat"
            elif os.path.exists(pychecker + ".exe"):
                pychecker = pychecker + ".exe"
        if not os.path.exists(pychecker):
            return
        tmpfilename = tempfile.mktemp() + '.py'
        fout = open(tmpfilename, 'w')
        fout.write(text)
        fout.close()
        textlines = text.splitlines()
        cwd = request.cwd
        rcfilePath = prefset.getStringPref("pychecker_checking_rcfile")
        if rcfilePath and os.path.exists(rcfilePath):
            if self.nonIdentChar_RE.search(rcfilePath):
                rcfilePath = '"' + rcfilePath + '"'
            extraArgs = [ "--config=" + rcfilePath ]
        else:
            extraArgs = []
            
        cmd = [pychecker, "--keepgoing", "--only"] + extraArgs + [tmpfilename]
        cwd = request.cwd or None
        # We only need the stdout result.
        try:
            p = process.ProcessOpen(cmd, cwd=cwd, env=koprocessutils.getUserEnv(), stdin=None)
            stdout, stderr = p.communicate()
            warnLines = stdout.splitlines(0) # Don't need the newlines.
            errorLines = stderr.splitlines(0)
        finally:
            os.unlink(tmpfilename)
        # Check raw output for an exception
        results = koLintResults()
        re_escaped_filename = re.escape(tmpfilename)
        exception_ptn = re.compile('''Caught exception importing module.+?File "%s", line (\d+), in <module>.+?\s*(\w+(?:Error|Exception):\s+.*)''' % re_escaped_filename, re.DOTALL)
        m = exception_ptn.search(stderr)
        if m:
            lineNo = int(m.group(1))
            desc = m.group(2)
            koLintResult.createAddResult(results, textlines, koLintResult.SEV_ERROR, lineNo, desc)

        warn_ptn = re.compile(r'^%s:(\d+):\s+(.+)' % re_escaped_filename)
        error_ptn = re.compile(r'(.*[Ee]rror:.*?)\s*\(%s,\s+line\s+(\d+)\)'
                               % re_escaped_filename)
        for line in warnLines:
            m = warn_ptn.match(line)
            if m:
                lineNo = int(m.group(1))
                desc = m.group(2)
                koLintResult.createAddResult(results, textlines, koLintResult.SEV_WARNING, lineNo,
                           "pychecker: " + desc)
        for line in errorLines:
            m = error_ptn.match(line)
            if m:
                lineNo = int(m.group(2))
                desc = m.group(1)
                koLintResult.createAddResult(results, textlines, koLintResult.SEV_ERROR, lineNo,
                           "pychecker: " + desc)
        return results

class KoPythonCommonLinter(object):
    _stringType = type("")
    _simple_python3_string_encodings = ("utf-8", "ascii")
    def __init__(self):
        self._sysUtils = components.classes["@activestate.com/koSysUtils;1"].\
            getService(components.interfaces.koISysUtils)
        self._koDirSvc = components.classes["@activestate.com/koDirs;1"].\
            getService(components.interfaces.koIDirs)
        self._userPath = koprocessutils.getUserEnv()["PATH"].split(os.pathsep)

    def _getInterpreterAndPyver(self, prefset):
        pref_name = "%sDefaultInterpreter" % (self.language_name_lc)
        if prefset.hasStringPref(pref_name) and\
           prefset.getStringPref(pref_name):
            python = prefset.getStringPref(pref_name)
        else:
            if sys.platform.startswith('win'):
                exts = ['.exe']
            else:
                exts = None
            try:
                python = which.which(self.language_name_lc, exts=exts, path=self._userPath)
            except which.WhichError:
                python = None

        if python:
            pyver = self._pyverFromPython(python)
            return python, pyver
        else:
            errmsg = ("No %s interpreter with which to check syntax."
                      % self.language_name_lc)
            raise ServerException(nsError.NS_ERROR_NOT_AVAILABLE, errmsg)

    _pyverFromPythonCache = None
    def _pyverFromPython(self, python):
        if self._pyverFromPythonCache is None:
            self._pyverFromPythonCache = {}
        if python not in self._pyverFromPythonCache:
            pythonInfo = components.classes["@activestate.com/koAppInfoEx?app=%s;1"
                                             % self.language_name]\
                .createInstance(components.interfaces.koIAppInfoEx)
            pythonInfo.executablePath = python
            verStr = pythonInfo.version
            try:
                pyver = tuple(int(v) for v in verStr.split('.'))
            except ValueError:
                pyver = None
            self._pyverFromPythonCache[python] = pyver

        return self._pyverFromPythonCache[python]


    def _buildResult(self, resultDict, leadingWS):
        """Convert a pycompile.py output resultDict to a KoILintResult.
        
        A pycompile.py dict looks like this:
            {'description': 'SyntaxError: invalid syntax',
             'filename': 'foo.py',
             'lineno': 1,
             'offset': 8, # may be None
             'severity': 'ERROR',
             'text': 'asdf = \n'}
        """
        r = KoLintResult()
        r.description = resultDict["description"]
        if leadingWS:
            resultDict['lineno'] -= 1
            if resultDict['text'].startswith(leadingWS):
                resultDict['text'] = resultDict['text'][len(leadingWS):]
        if resultDict["offset"] is not None:
            if leadingWS:
                actualLineOffset = len(leadingWS)
                if resultDict['offset'] >= actualLineOffset:
                    resultDict['offset'] -= actualLineOffset
            r.description += " (at column %d)" % resultDict["offset"]
        r.lineStart = resultDict['lineno']
        r.lineEnd = resultDict['lineno']
        # Would be nice to actually underline from teh given offset, but
        # then have to be smart abouve how far after that to underline.
        r.columnStart = 1
        r.columnEnd = len(resultDict['text'])
        if resultDict['severity'] == "ERROR":
            r.severity = r.SEV_ERROR
        elif resultDict['severity'] == "WARNING":
            r.severity = r.SEV_WARNING
        return r

    def _parseWarnings(self, warntext, text, leadingWS):
        """Parse out warnings from the text like the following and return
        a list of KoLintResult's.

        Example output:
            t.py:3: SyntaxWarning: import * only allowed at module level
              def foo():
            t.py:1: DeprecationWarning: the regex module is deprecated; please use the re module
              import regex
        Also sometimes get lines like this:
            t.py: Token Error: ('EOF in multi-line string', (3, 6))
        Note that this is picked up in the SyntaxError processing so we can
        skip that here for now.
        """
        textlines = text.splitlines(1)
        if leadingWS:
            del textlines[0]
        warningRe = re.compile("^(?P<fname>.*?):(?P<line>\d+): (?P<desc>.*)$")
        results = []
        for line in warntext.splitlines():
            match = warningRe.match(line)
            if match:
                # Ignore lines that don't match this, e.g. "  def foo():"
                r = KoLintResult()
                lineNo = int(match.group('line'))
                if leadingWS:
                    lineNo -= 1
                koLintResult.createAddResult(results, textlines, r.SEV_WARNING, lineNo, match.group('desc'), leadingWS)
        return results

    def lint(self, request):
        encoding_name = request.encoding.python_encoding_name
        text = request.content.encode(encoding_name)
        return self.lint_with_text(request, text)

    def lint_with_text(self, request, text):
        encoding_name = request.encoding.python_encoding_name
        cwd = request.cwd
        prefset = getProxiedEffectivePrefs(request)
        prefName = "lint_%s_with_standard_python" % self.language_name_lc
        if not prefset.getBooleanPref(prefName):
            return
        try:
            python, pyver = self._getInterpreterAndPyver(prefset)
            if pyver and pyver >= (3, 0):
                compilePy = os.path.join(self._koDirSvc.supportDir, "python",
                                         "py3compile.py")
                if encoding_name not in self._simple_python3_string_encodings:
                    # First, make sure the text is Unicode
                    if type(text) == self._stringType:
                        text = text.decode(encoding_name)
                    # Now save it as utf-8 -- python3 knows how to read utf-8
                    text = text.encode("utf-8")
            else:
                compilePy = os.path.join(self._koDirSvc.supportDir, "python",
                                         "pycompile.py")
            if request.koDoc.displayPath.startswith("macro2://"):
                text = projectUtils.wrapPythonMacro(text)
                leadingWS = _leading_ws_re.match(text.splitlines()[1]).group(1)
            else:
                leadingWS = None

            # Save the current buffer to a temporary file.
            tmpFileName = tempfile.mktemp()
            fout = open(tmpFileName, 'wb')
            fout.write(text)
            fout.close()
    
            results = koLintResults()
            try:
                argv = [python, '-u', compilePy, tmpFileName]
                #print "---- check syntax of the following with %r" % argv
                #sys.stdout.write(text)
                #print "-"*70
    
                env = koprocessutils.getUserEnv()
                cwd = cwd or None
                if sys.platform.startswith("win") and cwd is not None\
                   and cwd.startswith("\\\\"):
                    # Don't try to switch to a UNC path because pycompile.py
                    # ends up spitting out:
                    #     CMD.EXE was started with '\\netshare\apps\Komodo\stuff' as the current directory
                    #     path.  UNC paths are not supported.  Defaulting to Windows directory.
                    # XXX Could perhaps try to ensure that command is not
                    #     run via "cmd.exe /c", but don't know if that would
                    #     help either.
                    cwd = None
                    
                pythonPath = None
                prefName = "%sExtraPaths" % self.language_name_lc
                if prefset.hasPref(prefName):
                    pythonPath = prefset.getStringPref(prefName)
                if pythonPath:
                    pythonPathEnv = env.get("PYTHONPATH", "")
                    if pythonPathEnv:
                        pythonPath += os.pathsep + pythonPathEnv

                if pythonPath:
                    if sys.platform.startswith("win"):
                        pythonPath = pythonPath.replace('\\', '/')
                    env["PYTHONPATH"] = pythonPath
                
                p = process.ProcessOpen(argv, cwd=cwd, env=env, stdin=None)
                output, error = p.communicate()
                retval = p.returncode
                #print "-"*60, "env"
                #pprint(env)
                #print "-"*60, "output"
                #print output
                #print "-"*60, "error"
                #print error
                #print "-"*70
                if retval:
                    errmsg = "Error checking syntax: retval=%s, stderr=%s"\
                             % (retval, error)
                    log.exception(errmsg)
                    raise ServerException(nsError.NS_ERROR_UNEXPECTED, errmsg)
                else:
                    # Parse syntax errors in the output.
                    dicts = eval(output)
                    for d in dicts:
                        results.addResult( self._buildResult(d, leadingWS) )
                    # Parse warnings in the error.
                    for r in self._parseWarnings(error, text, leadingWS):
                        results.addResult(r)
            finally:
                os.unlink(tmpFileName)
        except ServerException:
            log.exception("ServerException")
            raise
        except:
            # non-ServerException's are unexpected internal errors
            log.exception("unexpected internal error")
            raise
        return results

class KoPythonLinter(KoPythonCommonLinter):
    language_name = "Python"
    language_name_lc = "python"
    _com_interfaces_ = [components.interfaces.koILinter]
    _reg_desc_ = "Komodo Python Linter"
    _reg_clsid_ = "{FAA3B898-5192-4463-BD37-816EDE05A5EE}"
    _reg_contractid_ = "@activestate.com/koLinter?language=Python&type=standard;1"
    _reg_categories_ = [
         ("category-komodo-linter", language_name),
         ]


class KoPython3Linter(KoPythonCommonLinter):
    language_name = "Python3"
    language_name_lc = "python3"
    _com_interfaces_ = [components.interfaces.koILinter]
    _reg_desc_ = "Komodo Python3 Linter"
    _reg_clsid_ = "{f2c7d20a-8399-453d-bbee-7e93d30841e9}"
    _reg_contractid_ = "@activestate.com/koLinter?language=Python3&type=standard;1"
    _reg_categories_ = [
         ("category-komodo-linter", language_name),
         ]

# Use the generic aggregators for both Python & Python3
