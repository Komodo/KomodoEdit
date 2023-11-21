from xpcom import components
from koLintResult import KoLintResult, SEV_ERROR, SEV_WARNING, SEV_INFO
from koLintResults import koLintResults
import os
import logging
import process
import koprocessutils
import which
import json
import tempfile

Cc = components.classes
Ci = components.interfaces

log = logging.getLogger("koRustLinter")
log.setLevel(logging.DEBUG)


class KoRustLinter(object):
    _com_interfaces_ = [Ci.koILinter]
    _reg_clsid_ = "{850fb06c-c8b7-4743-b22c-3d59da3e8f0a}"
    _reg_contractid_ = "@activestate.com/koLinter?language=Rust;1"
    _reg_categories_ = [
        ("category-komodo-linter", 'Rust'),
    ]

    def __init__(self,):
        self.file_ext = '.rs'
        self.project = Cc["@activestate.com/koPartService;1"].getService(Ci.koIPartService)

    def lint(self, request):
        text = request.content.encode(request.encoding.python_encoding_name)
        return self.lint_with_text(request, text)
    
    def _lint_lookup(self, request, linter_name):
        try:
            linter = request.prefset.getString(
                "rust.linter.binaries.{}".format(linter_name),
                ""
            )
            if linter == "":
                log.debug("Rust: looking for the {} executable on $PATH"
                          .format(linter_name))
            linter = which.which(linter_name)
        except which.WhichError:
            log.debug("Rust: {} is not found".format(linter_name))
        return linter

    def lint_with_text(self, request, text):
        if not request.prefset.getBoolean("rust.linter.enabled", False):
            log.debug("Rust: not enabled")
            return koLintResults()
        
        cwd = None
        cmd = []

        if self.project.currentProject is not None:
            if not request.prefset.getBoolean("rust.linter.cargo.enabled", False):
                log.debug("Rust: cargo check is disabled")
                return koLintResults()
            cwd = self.project.currentProject.liveDirectory
            linter = {
                "type": "cargo",
                "binary": self._lint_lookup(request, "cargo")
            }
            log.debug("Rust: using current project directory and cargo")
        else:
            cwd = request.cwd
            linter = {
                "type": "rustc",
                "binary": self._lint_lookup(request, "rustc")
            }
        log.debug("Rust: cwd = {}".format(cwd))

        if linter["type"] == "rustc":
            tmpfilename = tempfile.mktemp() + self.file_ext
            fout = open(tmpfilename, 'wb')
            fout.write(text)
            fout.close()
            cmd = [linter["binary"], "--error-format=json", tmpfilename]
        else:
            cmd = [linter["binary"], "check", "--message-format", "json", "--color", "never"]

        log.debug("Rust: command = {}".format(" ".join(cmd)))

        env = koprocessutils.getUserEnv()
        cwd = cwd or None
        p = process.ProcessOpen(cmd, cwd=cwd, env=env, stdin=process.PIPE)
        results = koLintResults()
        
        if linter["type"] == "rustc":
            stdout, stderr = p.communicate(input=text)
            log.debug(stderr)
            errors = map(lambda line: json.loads(line), stderr.splitlines(0))
        else:
            stdout, stderr = p.communicate()
            log.debug(stdout)
            errors = map(lambda line: json.loads(line), stdout.splitlines(0))
        

        for error in errors:
            try:
                if error['features']:
                    continue
            except KeyError:
                if linter["type"] == "cargo":
                    error = error["message"]
                message = error["message"]
                if error["level"] == "error":
                    severity = SEV_ERROR
                elif error["level"] == "warning":
                    severity = SEV_WARNING
                else:
                    severity = SEV_INFO
                for span in error['spans']:
                    line = span['line_start'] - 1
                    for h in span["text"]: # each highlight is a line
                        line += 1
                        column_start = h["highlight_start"]
                        column_end = h["highlight_end"]
                        result = KoLintResult(description=message,
                                            severity=severity,
                                            lineStart=line,
                                            lineEnd=line,
                                            columnStart=column_start,
                                            columnEnd=column_end)
                        results.addResult(result)
        return results
