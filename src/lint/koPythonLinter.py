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
import time
import process
import koprocessutils
from xpcom import components, nsError, ServerException
import logging
from pprint import pprint# , pformat

import koLintResult
from koLintResult import KoLintResult
from koLintResults import koLintResults

import projectUtils

log = logging.getLogger('koPythonLinter')
#log.setLevel(logging.DEBUG)

# Give identical complaints only once every 60 minutes
_COMPLAINT_PERIOD = 60 * 60 # seconds
# Map (path,message) => time
_complaints = {}

def _complainIfNeeded(messageKey, header, *parts):
    timeNow = time.time()
    if (messageKey not in _complaints
        or (timeNow - _complaints[messageKey] > _COMPLAINT_PERIOD)):
        log.error(header, *parts)
        _complaints[messageKey] = timeNow

def _getUserPath():
    return koprocessutils.getUserEnv()["PATH"].split(os.pathsep)

def _localTmpFileName():
    # Keep files out of places default view by prepending a "#"
    # Keep in mind that the pylint section strips out complains about
    # modules whose names start with '#'
    args = {'suffix':".py", 'prefix':"#"}
    
    # There are problems with the safer versions of tempfile:
    # tempfile.mkstemp returns an os-level file descriptor integer,
    # and using os.fdopen(fd, 'w') didn't create a writable object.
    # Using tempfile.TemporaryFile and tempfile.NamedTemporaryFile
    # return pseudo-file objects that give the error
    #
    # "TypeError: 'str' does not support the buffer interface"
    #
    # when I try to write to them.
    # written up at http://bugs.python.org/issue11818
    tmpFileName = tempfile.mktemp(**args)
    
    # Open files in binary mode. On windows, if we open in default text mode
    # CR/LFs  => CR/CR/LF, extra CR in each line.  Lines then get the wrong
    # line # reported with each message.
     
    # Related to bug97364: if we can't open the temporary file,
    # just throw the exception. Something is very wrong if this happens.
    fout = open(tmpFileName, 'wb')
    return fout, tmpFileName

class _GenericPythonLinter(object):
    _com_interfaces_ = [components.interfaces.koILinter]

    def __init__(self):
        self._pythonInfo = components.classes["@activestate.com/koAppInfoEx?app=%s;1" % (self.language_name, )]\
               .getService(components.interfaces.koIAppInfoEx)
        self.language_name_lc = self.language_name.lower()

    def lint(self, request):
        text = request.content.encode(request.encoding.python_encoding_name)
        return self.lint_with_text(request, text)

    def _get_fixed_env(self, prefset, cwd=None):
        env = koprocessutils.getUserEnv()
        prefName = "%sExtraPaths" % self.language_name_lc
        newParts = filter(bool, prefset.getString(prefName, "").split(os.pathsep))
        if cwd:
            newParts.append(cwd)
        if not newParts:
            # Nothing to fix up
            return env
        pythonPath = os.pathsep.join(newParts)
        pythonPathEnv = env.get("PYTHONPATH", "")
        if pythonPathEnv:
            pythonPath += os.pathsep + pythonPathEnv
        if sys.platform.startswith("win"):
            pythonPath = pythonPath.replace('\\', '/')
        env["PYTHONPATH"] = pythonPath
        return env

class KoPythonCommonPyLintChecker(_GenericPythonLinter):
    def _set_pylint_version(self, pythonExe):
        """
        Pylint pseudo-versions:
        1: Accepts -i/--include-ids
        2: No longer accepts -i Y/N, accepts --msg-template STRING
        """
        cmd = [pythonExe, '-c', 'import sys; from pylint.lint import Run; Run(["--version"])']
        try:
            env = koprocessutils.getUserEnv()
            p = process.ProcessOpen(cmd, env=env, stdin=None)
            stdout, stderr = p.communicate()
            versionInfo = re.compile(r'^.*?\s+(\d+)\.(\d+)\.(\d+)').match(stdout)
            if versionInfo:
                ver = [int(x) for x in versionInfo.groups()]
                if ver < [1, 0, 0]:
                    self._pylint_version = 1 # -f text -r n -i y --rcfile....
                else:
                    self._pylint_version = 2 # -f text -r n --include-ids y
        except:
            log.exception("_set_pylint_version: failed to get pylint version")
        if not hasattr(self, "_pylint_version"):
            # Fallback:
            self._pylint_version = 1
        
    def lint_with_text(self, request, text):
        if not text:
            return None
        prefset = request.prefset
        # self.lint_prefname: "lint_python_with_pylint" or "lint_python3_with_pylint3"
        if not prefset.getBoolean(self.lint_prefname):
            return
        pythonExe = self._pythonInfo.getExecutableFromPrefs(prefset)
        if not pythonExe:
            return
        if not hasattr(self, "_pylint_version"):
            self._set_pylint_version(pythonExe)
        cwd = request.cwd
        fout, tmpfilename = _localTmpFileName()
        try:
            tmpBaseName = os.path.splitext(os.path.basename(tmpfilename))[0]
            fout.write(text)
            fout.close()
            textlines = text.splitlines()
            env = self._get_fixed_env(prefset, cwd)
            rcfilePath = prefset.getStringPref(self.rcfile_prefname)
            rcfileToCheck = None
            if rcfilePath and os.path.exists(rcfilePath):
                extraArgs = [ '--rcfile=%s' % (rcfilePath,) ]
                rcfileToCheck = rcfilePath
            else:
                # Check for the default ~/.pylintrc
                defaultRC = os.path.expanduser(os.path.join("~", ".pylintrc"))
                if os.path.exists(defaultRC):
                    rcfileToCheck = defaultRC
                extraArgs = []
            preferredLineWidth = prefset.getLongPref("editAutoWrapColumn")
            if preferredLineWidth > 0:
                usePreferredLineWidth = True
                if rcfileToCheck is not None:
                    _max_line_length_re = re.compile(r'\s*max-line-length')
                    _disables_C0301_re = re.compile(r'\s*disable\s*=.*?\bC0301\b')
                    f = open(rcfileToCheck, "r")
                    try:
                        for txt in iter(f):
                            if _disables_C0301_re.match(txt) \
                                    or _max_line_length_re.match(txt):
                                usePreferredLineWidth = False
                                break
                    except:
                        pass
                    finally:
                        f.close()
                if usePreferredLineWidth:
                    extraArgs.append("--max-line-length=%d" % preferredLineWidth)
    
            baseArgs = [pythonExe, '-c', 'import sys; from pylint.lint import Run; Run(sys.argv[1:])']
            cmd = baseArgs + ["-f", "text", "-r", "n"] + extraArgs
            if self._pylint_version == 1:
                cmd.append("-i")
                cmd.append("y")
            else: # _pylint_version == 2
                cmd.append("--msg-template")
                cmd.append("{msg_id}: {line},{column}: {msg}")
            cmd.append(tmpfilename)
            cwd = request.cwd or None
            # We only need the stdout result.
            try:
                p = process.ProcessOpen(cmd, cwd=cwd, env=env, stdin=None)
                stdout, stderr = p.communicate()
                if stderr:
                    origStderr = stderr
                    okStrings = ["No config file found, using default configuration",]
                    for okString in okStrings:
                        stderr = stderr.replace(okString, "", 1)
                    stderr = stderr.strip()
                    if stderr:
                        pathMessageKey = "%s-%s" % (request.koDoc.displayPath, origStderr)
                        _complainIfNeeded(pathMessageKey,
                                          "Error in pylint: %s", origStderr)
                warnLines = stdout.splitlines(0) # Don't need the newlines.
            except:
                log.exception("Failed to run %s", cmd)
                stdout = ""
                warnLines = []
        finally:
            os.unlink(tmpfilename)
        ptn = re.compile(r'^([A-Z])(\d+):\s*(\d+)(?:,\d+)?:\s*(.*)')
        invalidModuleName_RE = re.compile(r'(Invalid\s+module\s+name\s+")(\#.+?)(")')
        # dependency: _localTmpFileName() prepends a '#' on the basename
        results = koLintResults()
        for line in warnLines:
            m = ptn.match(line)
            if m:
                status = m.group(1)
                statusCode = m.group(2)
                lineNo = int(m.group(3))
                message = m.group(4)
                desc = "pylint: %s%s %s" % (status, statusCode, message)
                if status in ("E", "F"):
                    severity = koLintResult.SEV_ERROR
                elif status in ("C", "R", "W"):
                    if statusCode == "0103":
                        # Don't let pylint complain about the tempname, but fake
                        # a check on the actual module name.
                        m2 = invalidModuleName_RE.match(message)
                        if m2:
                            complainedName = m2.group(2)
                            if complainedName == tmpBaseName:
                                # Not a real complaint
                                continue
                            # Don't bother further analysis, in case pylint
                            # behaves differently between python2 and python3
                            #
                            # If the message is about a bad module that isn't
                            # the temporary module, let it ride as is
                    severity = koLintResult.SEV_WARNING
                else:
                    #log.debug("Skip %s", line)
                    continue
                koLintResult.createAddResult(results, textlines, severity, lineNo, desc)
        return results
    
    def _createShouldMatchPtn(self, pseudoPtn):
        fixedPtn = pseudoPtn.replace("(", "(?:")
        try:
            return re.compile(fixedPtn)
        except:
            return re.compile(pseudoPtn)

class KoPythonPyLintChecker(KoPythonCommonPyLintChecker):
    language_name = "Python"
    _reg_desc_ = "Komodo Python PyLint Linter"
    _reg_clsid_ = "{8de9b933-d32d-4c12-b73e-9bcce4fec63c}"
    _reg_contractid_ = "@activestate.com/koLinter?language=Python&type=pylint;1"
    _reg_categories_ = [
         ("category-komodo-linter", 'Python&type=pylint'),
         ]
    lint_prefname = "lint_python_with_pylint"
    rcfile_prefname = "pylint_checking_rcfile"

class KoPython3PyLintChecker(KoPythonCommonPyLintChecker):
    language_name = "Python3"
    _reg_desc_ = "Komodo Python3 PyLint Linter"
    _reg_clsid_ = "{f1ecb86c-9fd9-4477-a40d-b8c9ee282c0f}"
    _reg_contractid_ = "@activestate.com/koLinter?language=Python3&type=pylint;1"
    _reg_categories_ = [
         ("category-komodo-linter", 'Python3&type=pylint'),
         ]
    lint_prefname = "lint_python3_with_pylint3"
    rcfile_prefname = "pylint3_checking_rcfile"
    
class KoPythonCommonPep8Checker(_GenericPythonLinter):
    def lint_with_text(self, request, text):
        if not text:
            return None
        prefset = request.prefset
        # if not prefset.getBooleanPref("lintPythonWithPep8"): return
        if not prefset.getBooleanPref(self.lint_prefname):
            return
        pythonExe = self._pythonInfo.getExecutableFromPrefs(prefset)
        if not pythonExe:
            return
        cwd = request.cwd
        fout, tmpfilename = _localTmpFileName()
        try:
            tmpBaseName = os.path.splitext(os.path.basename(tmpfilename))[0]
            fout.write(text)
            fout.close()
            textlines = text.splitlines()
            env = self._get_fixed_env(prefset, cwd)
            cmd = [pythonExe, '-m', 'pep8']
            checkRCFile = False
            rcfilePath = prefset.getStringPref(self.rcfile_prefname)
            if rcfilePath and os.path.exists(rcfilePath):
                extraArgs = [ '--config=%s' % (rcfilePath,) ]
                checkRCFile = True
            else:
                extraArgs = []
                # default location: ~/.pep8
                homeDir = os.path.expanduser("~")
                rcfilePath = os.path.join(homeDir, ".pep8")
                if not os.path.exists(rcfilePath):
                    rcfilePath = os.path.join(homeDir, ".config", "pep8")
                checkRCFile = os.path.exists(rcfilePath)
            preferredLineWidth = prefset.getLongPref("editAutoWrapColumn")
            if preferredLineWidth > 0:
                usePreferredLineWidth = True
                if checkRCFile:
                    _disables_E0501_re = re.compile(r'\s*disable\s*=.*?\bE0?501\b')
                    _max_line_length_re = re.compile(r'\s*max-line-length')
                    f = open(rcfilePath, "r")
                    try:
                        for txt in iter(f):
                            if _disables_E0501_re.match(txt) \
                                    or _max_line_length_re.match(txt):
                                usePreferredLineWidth = False
                                break
                    except:
                        log.exception("Problem checking max-line-length")
                    finally:
                        f.close()
                if usePreferredLineWidth:
                    extraArgs.append("--max-line-length=%d" % preferredLineWidth)
    
            cmd += extraArgs
            cmd.append(tmpfilename)
            cwd = request.cwd or None
            # We only need the stdout result.
            try:
                p = process.ProcessOpen(cmd, cwd=cwd, env=env, stdin=None)
                stdout, stderr = p.communicate()
                if stderr.strip():
                    pathMessageKey = "%s-%s" % (request.koDoc.displayPath, stderr)
                    _complainIfNeeded(pathMessageKey,
                                      "Error in pep8: %s", stderr)
                    return
                warnLines = stdout.splitlines(False) # Don't need the newlines.
            except:
                log.exception("Failed to run %s", cmd)
                stdout = ""
                warnLines = []
        finally:
            os.unlink(tmpfilename)
        ptn = re.compile(r'(?P<filename>.*?):(?P<lineNum>\d+):(?P<columnNum>\d+):\s*(?P<status>[EW])(?P<statusCode>\d+)\s+(?P<message>.*)')
        results = koLintResults()
        for m in map(ptn.match, warnLines):
            if m:
                lineNo = int(m.group("lineNum"))
                columnNum = int(m.group("columnNum"))
                desc = "pep8: %s%s %s" % (m.group("status"),
                                          m.group("statusCode"),
                                          m.group("message"))
                # Everything pep8 complains about is a warning, by definition
                severity = koLintResult.SEV_WARNING
                koLintResult.createAddResult(results, textlines, severity, lineNo, desc, columnStart=columnNum)
        return results

class KoPythonPep8Checker(KoPythonCommonPep8Checker):
    language_name = "Python"
    _reg_desc_ = "Komodo Python Pep8 Linter"
    _reg_clsid_ = "{1c51ad7e-2788-448d-80f4-db6465164cc9}"
    _reg_contractid_ = "@activestate.com/koLinter?language=Python&type=pep8;1"
    _reg_categories_ = [
         ("category-komodo-linter", 'Python&type=pep8'),
         ]
    lint_prefname = "lint_python_with_pep8"
    rcfile_prefname = "pep8_checking_rcfile"

class KoPython3Pep8Checker(KoPythonCommonPep8Checker):
    language_name = "Python3"
    _reg_desc_ = "Komodo Python3 Pep8 Linter"
    _reg_clsid_ = "{4eb876a9-818d-4d94-b490-837bc306492c}"
    _reg_contractid_ = "@activestate.com/koLinter?language=Python3&type=pep8;1"
    _reg_categories_ = [
         ("category-komodo-linter", 'Python3&type=pep8'),
         ]
    lint_prefname = "lint_python3_with_pep83"
    rcfile_prefname = "pep83_checking_rcfile"


class KoPythonCommonPyflakesChecker(_GenericPythonLinter):
    def _createAddResult(self, results, textlines, errorLines, severity):
        warnLinePtn = re.compile(r'^(.+?):(\d+):\s+(.*)')
        for line in errorLines:
            m = warnLinePtn.match(line)
            if m:
                lineNo = int(m.group(2))
                desc = "pyflakes: %s" % (m.group(3),)
                targetLine = textlines[lineNo - 1]
                columnEnd = len(targetLine) + 1
                result = KoLintResult(description=desc,
                                      severity=severity,
                                      lineStart=lineNo,
                                      lineEnd=lineNo,
                                      columnStart=1,
                                      columnEnd=columnEnd)
                results.addResult(result)
        
    def lint_with_text(self, request, text):
        if not text:
            return None
        prefset = request.prefset
        if not prefset.getBooleanPref(self.lint_prefname):
            return
        pythonExe = self._pythonInfo.getExecutableFromPrefs(prefset)
        if not pythonExe:
            return
        try:
            checkerExe = which.which("pyflakes", path=_getUserPath())
        except which.WhichError:
            checkerExe = None
        if not checkerExe:
            log.warn("pyflakes not found")
            return
        fout, tmpfilename = _localTmpFileName()
        try:
            fout.write(text)
            fout.close()
            textlines = text.splitlines()
            cwd = request.cwd

            # For the env, don't add a PYTHONPATH entry for cwd, as it can break
            # module import lookups for pyflakes. E.g.
            #  foo/
            #    __init__.py  - an "from foo import bar" in this file will break
            env = self._get_fixed_env(prefset, cwd=None)
            
            cmd = [pythonExe, checkerExe, tmpfilename]
            # stdout for pyflakes.checker.Checker
            # stderr for __builtin__.compile()
            p = process.ProcessOpen(cmd, cwd=cwd, env=env, stdin=None)
            stdout, stderr = p.communicate()
            warnLines = []
            errorLines = []
            if p.returncode and stderr and not stdout:
                m = re.match("^(.*?):(\d+):(\d+): invalid syntax", stderr)
                if m is None:
                    _complainIfNeeded(stderr, "Error running pyflakes on file %r\n%s",
                                      request.koDoc.displayPath, stderr)
                # It's a syntax error - convert it.
                error = "%s:%s: invalid syntax (at column %s)" % (
                            m.group(1), m.group(2), m.group(3))
                errorLines = [error]
            else:
                warnLines = stdout.splitlines()
                errorLines = stderr.splitlines(0) # Don't need the newlines.
        finally:
            os.unlink(tmpfilename)
        results = koLintResults()

        # "createAddResult" will change lineno in some situation, so we use our version
        self._createAddResult(results, textlines, errorLines, koLintResult.SEV_ERROR)
        self._createAddResult(results, textlines, warnLines, koLintResult.SEV_WARNING)
        return results

class KoPythonPyflakesChecker(KoPythonCommonPyflakesChecker):
    language_name = "Python"
    _reg_desc_ = "Komodo Python Pyflakes Linter"
    _reg_clsid_ = "{5e040c73-814d-4151-b6aa-a6201e43a627}"
    _reg_contractid_ = "@activestate.com/koLinter?language=Python&type=pyflakes;1"
    _reg_categories_ = [
         ("category-komodo-linter", 'Python&type=pyflakes'),
         ]
    lint_prefname = "lint_python_with_pyflakes"

class KoPython3PyflakesChecker(KoPythonCommonPyflakesChecker):
    language_name = "Python3"
    _reg_desc_ = "Komodo Python3 Pyflakes Linter"
    _reg_clsid_ = "{25ced8c6-b37e-4bc1-9efc-dc6d60696d22}"
    _reg_contractid_ = "@activestate.com/koLinter?language=Python3&type=pyflakes;1"
    _reg_categories_ = [
         ("category-komodo-linter", 'Python3&type=pyflakes'),
         ]
    lint_prefname = "lint_python3_with_pyflakes3"


class KoPythonCommonPycheckerLinter(_GenericPythonLinter):
    """
    Instead of checking your Python code using pylinter,
      this one lints    your Python code using pychecker.
    """
        
    def lint_with_text(self, request, text):
        if not text:
            return None
        prefset = request.prefset
        if not prefset.getBooleanPref(self.lint_prefname):
            return
        pychecker = prefset.getStringPref(self.wrapper_location)
        if not pychecker:
            return
        if sys.platform.startswith("win") and not os.path.exists(pychecker):
            if os.path.exists(pychecker + ".bat"):
                pychecker = pychecker + ".bat"
            elif os.path.exists(pychecker + ".exe"):
                pychecker = pychecker + ".exe"
        if not os.path.exists(pychecker):
            return
        fout, tmpfilename = _localTmpFileName()
        try:
            fout.write(text)
            fout.close()
            textlines = text.splitlines()
            cwd = request.cwd
            env = self._get_fixed_env(prefset, cwd)
            rcfilePath = prefset.getStringPref(self.rcfile_prefname)
            if rcfilePath and os.path.exists(rcfilePath):
                extraArgs = [ '--config=%s' % (rcfilePath,) ]
            else:
                extraArgs = []
                
            cmd = [pychecker, "--keepgoing", "--only"] + extraArgs + [tmpfilename]
            cwd = request.cwd or None
            # We only need the stdout result.
            p = process.ProcessOpen(cmd, cwd=cwd, env=env, stdin=None)
            stdout, stderr = p.communicate()
            warnLines = stdout.splitlines(0) # Don't need the newlines.
            errorLines = stderr.splitlines(0)
        finally:
            try:
                os.unlink(tmpfilename)
                 # pychecker leaves .pyc files around, so delete them as well
                os.unlink(tmpfilename + "c")
            except:
                pass
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

class KoPythonPycheckerLinter(KoPythonCommonPycheckerLinter):
    language_name = "Python"
    _reg_desc_ = "Komodo Python Pychecker Linter"
    _reg_clsid_ = "{93b2d525-ed2f-4b77-8312-ab784632c8b8}"
    _reg_contractid_ = "@activestate.com/koLinter?language=Python&type=pychecker;1"
    _reg_categories_ = [
         ("category-komodo-linter", 'Python&type=pychecker'),
         ]
    lint_prefname = "lint_python_with_pychecker"
    wrapper_location = "pychecker_wrapper_location"
    rcfile_prefname = "pychecker_checking_rcfile"

class KoPython3PycheckerLinter(KoPythonCommonPycheckerLinter):
    language_name = "Python3"
    _reg_desc_ = "Komodo Python3 Pychecker Linter"
    _reg_clsid_ = "{76ba1bf9-6766-4f75-a92f-008c66652cec}"
    _reg_contractid_ = "@activestate.com/koLinter?language=Python3&type=pychecker;1"
    _reg_categories_ = [
         ("category-komodo-linter", 'Python3&type=pychecker'),
         ]
    lint_prefname = "lint_python3_with_pychecker3"
    wrapper_location = "pychecker3_wrapper_location"
    rcfile_prefname = "pychecker3_checking_rcfile"


class KoPythonCommonLinter(_GenericPythonLinter):
    _stringType = type("")
    _simple_python3_string_encodings = ("utf-8", "ascii")
    def __init__(self):
        _GenericPythonLinter.__init__(self)
        self._sysUtils = components.classes["@activestate.com/koSysUtils;1"].\
            getService(components.interfaces.koISysUtils)
        self._koDirSvc = components.classes["@activestate.com/koDirs;1"].\
            getService(components.interfaces.koIDirs)

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
        results = koLintResults()
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
        prefset = request.prefset
        prefName = "lint_%s_with_standard_python" % self.language_name_lc
        if not prefset.getBooleanPref(prefName):
            return
        try:
            # Get the Python interpreter (prefs or first valid one on the path).
            interpreter_pref_name = "%sDefaultInterpreter" % (self.language_name_lc, )
            python = prefset.getString(interpreter_pref_name)
            if not python:
                python = self._pythonInfo.getExecutableFromPrefs(prefset)
                if not python:
                    return
            if not self._pythonInfo.isSupportedBinary(python):
                raise ServerException(nsError.NS_ERROR_FAILURE,
                                      "Invalid %r executable: %r" %
                                      (self.language_name, python))
            # Determine the pycompile settings.
            if self.language_name == "Python3":
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
                leading_ws_re = re.compile(r'(\s*)')
                leadingWS = leading_ws_re.match(text.splitlines()[1]).group(1)
            else:
                leadingWS = None

            # Save the current buffer to a temporary file.
            cwd = cwd or None
            # Standard Python syntax-checking files can live in a tmp directory
            # because the checker doesn't attempt to verify or read imported
            # modules.
            fout, tmpFileName = _localTmpFileName()
            fout.write(text)
            fout.close()
    
            results = koLintResults()
            try:
                argv = [python, '-u', compilePy, tmpFileName]
                #print "---- check syntax of the following with %r" % argv
                #sys.stdout.write(text)
                #print "-"*70
    
                env = self._get_fixed_env(prefset)
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
                    results.addResults(self._parseWarnings(error, text, leadingWS))
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
