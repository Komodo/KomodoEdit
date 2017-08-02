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

log = logging.getLogger("koRubocopLinter")
#log.setLevel(logging.DEBUG)


class KoRubocopLinter(object):
    _com_interfaces_ = [Ci.koILinter]
    _reg_clsid_ = "{0BED01B1-6BAD-4B55-A407-3C6273C0032D}"
    _reg_contractid_ = "@addons.defman.me/koRubocopLinter;1"
    _reg_categories_ = [
        ("category-komodo-linter", 'Ruby'),
    ]

    def __init__(self,):
        self.ignore_cops = ["Style/FileName"]
        self.file_ext = '.rb'
        self.project = Cc["@activestate.com/koPartService;1"].getService(Ci.koIPartService)

    def lint(self, request):
        text = request.content.encode(request.encoding.python_encoding_name)
        return self.lint_with_text(request, text)

    def lint_with_text(self, request, text):
        if not request.prefset.getBoolean("lint_rubocop_enabled", False):
            log.debug("Rubocop: not enabled")
            return
        try:
            rubocop = request.prefset.getString('rubocop_binary' ,'')
            if rubocop == '':
                log.debug('Rubocop: looking for the rubocop executable on $PATH')
                rubocop = which.which('rubocop')
        except which.WhichError:
            log.debug("Rubocop: rubocop is not found")
            return

        cwd = None
        cmd = []
        rbfile = None

        if self.project.currentProject is not None:
            cwd = self.project.currentProject.liveDirectory
            log.debug("Rubocop: using current project directory")
        else:
            cwd = request.cwd
        log.debug("Rubocop: cwd = %s" % (cwd))

        if cwd is not None:
            for ext in ['yaml', 'yml']:
                config = os.path.join(cwd, '.rubocop.{}'.format(ext))
                if os.path.exists(config):
                    log.debug("Config file: {}".format(config))
                    break
        else:
            config = request.prefset.getString('rubocop_config', '')
            log.debug("Config file (set by user): {}".format(config))
        if config and os.path.isfile(config):
            cmd = [rubocop, '--format', 'json', '--config', config]
        else:
            cmd = [rubocop, '--format', 'json']
            log.debug("Rubocop: .rubocop.yml or .rubocop.yaml are not found")

        cmd += ['--stdin', request.koDoc.file.encodedPath]

        log.debug("Rubocop: command = %s" % (" ".join(cmd)))

        env = koprocessutils.getUserEnv()
        cwd = cwd or None
        p = process.ProcessOpen(cmd, cwd=cwd, env=env, stdin=process.PIPE)
        stdout, stderr = p.communicate(input=text)
        
        results = koLintResults()
        data = json.loads(stdout)['files'][0]

        for offense in data['offenses']:
            if offense['cop_name'] in self.ignore_cops:
                log.debug("Rubocop: cop '%s' ignored" % (offense['cop_name']))
                continue
            line = offense['location']['line']
            column = offense['location']['column']
            column_end = column + offense['location']['length']
            if offense['severity'] in ['refactor', 'convention']:
                severity = SEV_INFO
            elif offense['severity'] == "warning":
                severity = SEV_WARNING
            else:
                severity = SEV_ERROR
            description = "%s: %s" % (offense['cop_name'], offense['message'])
            result = KoLintResult(description=description,
                                  severity=severity,
                                  lineStart=line,
                                  lineEnd=line,
                                  columnStart=column,
                                  columnEnd=column_end)
            results.addResult(result)
        log.debug("Rubocop: lint results: %d" % (len(data['offenses'])))
        return results
