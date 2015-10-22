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

import os
import sys
import json
import logging
import tempfile

from xpcom import components

import URIlib
import process
import koprocessutils
from zope.cachedescriptors.property import LazyClassAttribute
from koLintResult import KoLintResult
from koLintResults import koLintResults
from codeintel2.lang_css import CSSLangIntel   # TODO ?

log = logging.getLogger("koCSSLinter")


class KoCSSLinter:
    _com_interfaces_ = [components.interfaces.koILinter]
    _reg_desc_ = "Komodo Mozilla CSS Linter"
    _reg_clsid_ = "{F770CBE7-2AAF-492C-8900-CC512CAF5046}"
    _reg_contractid_ = "@activestate.com/koLinter?language=CSS&type=Mozilla;1"
    _reg_categories_ = [
         ("category-komodo-linter", 'CSS&type=Mozilla'),
         ]
    lint_prefname = "lint_css_mozilla_parser_enabled"

    # Lazily generated class properties.
    @LazyClassAttribute
    def koDirs(self):
        return components.classes["@activestate.com/koDirs;1"].\
                getService(components.interfaces.koIDirs)
    @LazyClassAttribute
    def mozBinDir(self):
        return self.koDirs.mozBinDir
    @LazyClassAttribute
    def csslint_filepath(self):
        return os.path.join(self.koDirs.supportDir, "lint", "css",
                            "xpcshell_csslint.js")
    @LazyClassAttribute
    def xpcshell_exe(self):
        if sys.platform.startswith("win"):
            return os.path.join(self.mozBinDir, "xpcshell.exe")
        return os.path.join(self.mozBinDir, "xpcshell")

    def _setLDLibraryPath(self):
        env = koprocessutils.getUserEnv()
        ldLibPath = env.get("LD_LIBRARY_PATH", None)
        if ldLibPath:
            env["LD_LIBRARY_PATH"] = self.mozBinDir + ":" + ldLibPath
        else:
            env["LD_LIBRARY_PATH"] = self.mozBinDir
        return env

    def lint(self, request):
        """Lint the given CSS content.
        
        Raise an exception  if there is a problem.
        """
        text = request.content.encode(request.encoding.python_encoding_name)
        return self.lint_with_text(request, text)

    def lint_with_text(self, request, text):
        if not text:
            return None
        if not request.prefset.getBoolean(self.lint_prefname, True):
            return None

        # Save buffer to a temporary file and parse it.
        cwd = request.cwd or None
        fn = tempfile.mktemp()
        try:
            file(fn, 'wb').write(text)
            return self.parse(fn, cwd=cwd)
        except Exception, e:
            log.exception(e)
        finally:
            os.unlink(fn)

    def parse(self, filepath, cwd=None):
        results = koLintResults()

        entries = []
        cmd = [self.xpcshell_exe, self.csslint_filepath, filepath]
        stdout = None

        # We only need the stdout result.
        try:
            p = process.ProcessOpen(cmd, cwd=cwd, env=self._setLDLibraryPath(),
                                    stdin=None)
            stdout, stderr = p.communicate()
            entries = json.loads(stdout or "[]")
        except:
            log.exception("Problem running xcshell: %r\n,output:%r\n", cmd, stdout)
            return results

        for entry in entries:
            # Convert to Komodo lint result object.
            #print 'entry: %r' % (entry, )
            results.addResult(KoLintResult(description=entry.get('description', ''),
                                           severity=entry.get('severity', 1),
                                           lineStart=entry.get('lineStart', 0),
                                           lineEnd=entry.get('lineEnd', -1),
                                           columnStart=entry.get('columnStart', 0),
                                           columnEnd=entry.get('columnEnd', 0)))

        return results

