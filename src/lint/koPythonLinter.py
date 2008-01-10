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

from koLintResult import *
from koLintResults import koLintResults

log = logging.getLogger('koPythonLinter')

class KoPythonLinter:
    _com_interfaces_ = [components.interfaces.koILinter]
    _reg_desc_ = "Komodo Python Linter"
    _reg_clsid_ = "{FAA3B898-5192-4463-BD37-816EDE05A5EE}"
    _reg_contractid_ = "@activestate.com/koLinter?language=Python;1"

    def __init__(self):
        self._sysUtils = components.classes["@activestate.com/koSysUtils;1"].\
            getService(components.interfaces.koISysUtils)
        self._koDirSvc = components.classes["@activestate.com/koDirs;1"].\
            getService(components.interfaces.koIDirs)
        self._userPath = koprocessutils.getUserEnv()["PATH"].split(os.pathsep)

    def _getInterpreter(self, prefset):
        if prefset.hasStringPref("pythonDefaultInterpreter") and\
           prefset.getStringPref("pythonDefaultInterpreter"):
            python = prefset.getStringPref("pythonDefaultInterpreter")
        else:
            if sys.platform.startswith('win'):
                exts = ['.exe']
            else:
                exts = None
            try:
                python = which.which("python", exts=exts, path=self._userPath)
            except which.WhichError:
                python = None

        if python:
            return python
        else:
            errmsg = "No python interpreter with which to check syntax."
            raise ServerException(nsError.NS_ERROR_NOT_AVAILABLE, errmsg)

    def _buildResult(self, dict):
        """Convert a pycompile.py output dict to a KoILintResult.
        
        A pycompile.py dict looks like this:
            {'description': 'SyntaxError: invalid syntax',
             'filename': 'foo.py',
             'lineno': 1,
             'offset': 8, # may be None
             'severity': 'ERROR',
             'text': 'asdf = \n'}
        """
        r = KoLintResult()
        r.description = dict["description"]
        if dict["offset"] is not None:
            r.description += " (at column %d)" % dict["offset"]
        r.lineStart = dict['lineno']
        r.lineEnd = dict['lineno']
        # Would be nice to actually underline from teh given offset, but
        # then have to be smart abouve how far after that to underline.
        r.columnStart = 1
        r.columnEnd = len(dict['text'])
        if dict['severity'] == "ERROR":
            r.severity = r.SEV_ERROR
        elif dict['severity'] == "WARNING":
            r.severity = r.SEV_WARNING
        return r

    def _parseWarnings(self, warntext, text):
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
        warningRe = re.compile("^(?P<fname>.*?):(?P<line>\d+): (?P<desc>.*)$")
        results = []
        for line in warntext.splitlines():
            match = warningRe.match(line)
            if match:
                # Ignore lines that don't match this, e.g. "  def foo():"
                r = KoLintResult()
                r.lineStart = int(match.group('line'))
                r.lineEnd = int(match.group('line'))
                r.columnStart = 1
                r.columnEnd = len(textlines[r.lineStart-1])
                r.description = match.group('desc')
                r.severity = r.SEV_WARNING
                results.append(r)
            
        return results

    def lint(self, request):
        text = request.content.encode(request.encoding.python_encoding_name)
        cwd = request.cwd
        prefset = request.document.getEffectivePrefs()

        try:
            python = self._getInterpreter(prefset)
            compilePy = os.path.join(self._koDirSvc.supportDir, "python",
                                     "pycompile.py")
    
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
                    #     CMD.EXE was started with '\\crimper\apps\Komodo\stuff' as the current directory
                    #     path.  UNC paths are not supported.  Defaulting to Windows directory.
                    # XXX Could perhaps try to ensure that command is not
                    #     run via "cmd.exe /c", but don't know if that would
                    #     help either.
                    cwd = None
                    
                pythonPath = None
                if prefset.hasPref("pythonExtraPaths"):
                    pythonPath = prefset.getStringPref("pythonExtraPaths")
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
                #print "-"*60, "output"
                #print output
                #print "-"*60, "error"
                #print error
                #print "-"*70
                if retval:
                    errmsg = "Error checking syntax: retval=%s, stderr=%s"\
                             % (retval, error)
                    raise ServerException(nsError.NS_ERROR_UNEXPECTED, errmsg)
                else:
                    # Parse syntax errors in the output.
                    dicts = eval(output)
                    for d in dicts:
                        results.addResult( self._buildResult(d) )
                    # Parse warnings in the error.
                    for r in self._parseWarnings(error, text):
                        results.addResult(r)
            finally:
                os.unlink(tmpFileName)
        except ServerException:
            raise
        except:
            # non-ServerException's are unexpected internal errors
            log.exception("unexpected internal error")
            raise
        return results
