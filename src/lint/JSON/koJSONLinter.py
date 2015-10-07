#!python
# Copyright (c) 2000-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

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

log = logging.getLogger("koJSONLinter")


class KoJSONLinter:
    _com_interfaces_ = [components.interfaces.koILinter]
    _reg_desc_ = "Komodo XPCShell JSON Linter"
    _reg_clsid_ = "{bcd7d132-734c-4d06-811c-383705ccb514}"
    _reg_contractid_ = "@activestate.com/koLinter?language=JSON;1"
    _reg_categories_ = [
         ("category-komodo-linter", "JSON"),
         ]

    # Lazily generated class properties.
    @LazyClassAttribute
    def koDirs(self):
        return components.classes["@activestate.com/koDirs;1"].\
                getService(components.interfaces.koIDirs)
    @LazyClassAttribute
    def mozBinDir(self):
        return self.koDirs.mozBinDir
    @LazyClassAttribute
    def jsonlint_filepath(self):
        return os.path.join(self.koDirs.supportDir, "lint", "json",
                            "xpcshell_jsonlint.js")
    @LazyClassAttribute
    def xpcshell_exe(self):
        if sys.platform.startswith("win"):
            return os.path.join(self.mozBinDir, "xpcshell.exe")
        return os.path.join(self.mozBinDir, "xpcshell")

    def _setEnv(self):
        env = koprocessutils.getUserEnv()
        ldLibPath = env.get("LD_LIBRARY_PATH", None)
        if ldLibPath:
            env["LD_LIBRARY_PATH"] = self.mozBinDir + ":" + ldLibPath
        else:
            env["LD_LIBRARY_PATH"] = self.mozBinDir
        env['PYTHONPATH'] = os.pathsep.join(sys.path)
        return env

    def lint(self, request):
        """Lint the given JSON content.
        
        Raise an exception  if there is a problem.
        """
        text = request.content.encode(request.encoding.python_encoding_name)
        return self.lint_with_text(request, text)

    def lint_with_text(self, request, text):
        if not text:
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
        cmd = [self.xpcshell_exe, self.jsonlint_filepath, filepath]
        stdout = None

        # We only need the stdout result.
        try:
            p = process.ProcessOpen(cmd, cwd=cwd, env=self._setEnv(),
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

