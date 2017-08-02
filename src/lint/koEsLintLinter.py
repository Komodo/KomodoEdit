from xpcom import components
from koLintResult import KoLintResult, SEV_ERROR, SEV_WARNING, SEV_INFO
from koLintResults import koLintResults
import os
import logging
import tempfile
import process
import koprocessutils
import which
import json

Cc = components.classes
Ci = components.interfaces

log = logging.getLogger("koEsLintLinter")
#log.setLevel(logging.DEBUG)


class KoEsLintLinter(object):
    _com_interfaces_ = [Ci.koILinter]
    _reg_clsid_ = "{00CEDD2B-BE9E-4FD6-A9DE-5405B5B4503D}"
    _reg_contractid_ = "@addons.defman.me/koEsLintLinter;1"
    _reg_categories_ = [
        ("category-komodo-linter", 'JavaScript&type=eslint'),
        ("category-komodo-linter", 'Node.js&type=eslint'),
        ("category-komodo-linter", 'JSX&type=eslint')
    ]

    def __init__(self,):
        self.project = Cc["@activestate.com/koPartService;1"].getService(Ci.koIPartService)
        self.jshint_linter = Cc["@activestate.com/koLinter?language=JavaScript&type=JSHint;1"].getService(Ci.koILinter)

    def lint(self, request):
        text = request.content.encode(request.encoding.python_encoding_name)
        return self.lint_with_text(request, text)

    def jshint_lint(self, request, text):
        return self.jshint_linter.lint(request)

    def lint_with_text(self, request, text):
        if not request.prefset.getBoolean("lint_eslint_enabled", False):
            log.debug("EsLint: not enabled")
            return self.jshint_lint(request, text)

        is_project = False
        cwd = None
        cmd = []
        config = None

        if self.project.currentProject is not None:
            is_project = True
            cwd = self.project.currentProject.liveDirectory
            log.debug("EsLint: using current project directory")
        else:
            cwd = request.cwd
        log.debug("EsLint: cwd = %s" % (cwd))

        # priority:
        # 1 - node_modules's eslint
        # 2 - eslint binary set by user [fallback]
        # 3 - eslint binary found on $PATH [fallback]
        eslint = os.path.join(cwd, 'node_modules/.bin/eslint')
        if not os.path.exists(eslint):
            log.debug("EsLint: {} does not exist".format(eslint))
            eslint = request.prefset.getString('eslint_binary', '')
            if not os.path.exists(eslint):
                log.debug("EsLint: eslint executable is not set/not found")
                try:
                    eslint = which.which('eslint')
                    log.debug("EsLint: eslint executable found on $PATH")
                except which.WhichError:
                    log.debug("EsLint: eslint executable is not found on $PATH")
                    return self.jshint_lint(request, text)
            else:
                log.debug("EsLint: eslint executable is set by the user")


        if cwd is not None:
            # priority:
            # 1 - user config in the cwd
            # 2 - user config set by user [fallback]
            for file_format in ['js', 'yml', 'json']:
                config = os.path.join(cwd, '.eslintrc.{}'.format(file_format))
                log.debug(config)
                if os.path.exists(config):
                    break
            if not os.path.exists(config):
                config = request.prefset.getString('eslint_config', '')
        else:
            log.debug("EsLint: cwd is empty")
            return self.jshint_lint(request, text)
        if config and os.path.isfile(config):
            cmd = [eslint, '--no-color', '--format', 'json', '--config', config]
        else:
            log.info("EsLint: .eslintrc is not found")
            return self.jshint_lint(request, text)

        cmd += ['--stdin', '--stdin-filename', request.koDoc.file.encodedPath]

        log.debug("EsLint: command = %s" % (" ".join(cmd)))

        env = koprocessutils.getUserEnv()
        cwd = cwd or None
        p = process.ProcessOpen(cmd, cwd=cwd, env=env, stdin=process.PIPE)
        stdout, stderr = p.communicate(input=text)

        results = koLintResults()
        try:
            data = json.loads(stdout)[0]['messages']
        except Exception, e:
            log.warn('Failed to parse the eslint output!')
            log.warn('The output was: {}'.format(stdout))
            return self.jshint_lint(request, text)

        for message in data:
            line = message['line']
            column = message['column']
            try:
                column_end = message['endColumn']
            except:
                if column > 1:
                    column -= 1
                column_end = column + 1
            try:
                line_end = message['endLine']
            except:
                line_end = line
            if message['severity'] == 2:
                severity = SEV_ERROR
            elif message['severity'] == 1:
                severity = SEV_WARNING
            else:
                severity = SEV_INFO
            if message['ruleId'] != None:
                description = "%s: %s" % (message['ruleId'], message['message'])
            else:
                description = message['message']
            result = KoLintResult(description=description,
                                  severity=severity,
                                  lineStart=line,
                                  lineEnd=line_end,
                                  columnStart=column,
                                  columnEnd=column_end)
            results.addResult(result)
        return results
