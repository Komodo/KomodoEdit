#!python
# Copyright (c) 2000-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.


from xpcom import components
from koLintResult import *
from koLintResults import koLintResults


class KoTestLinter:
    _com_interfaces_ = [components.interfaces.koILinter]
    _reg_desc_ = "Komodo Linter"
    _reg_clsid_ = "{2164884E-492F-11d4-AC24-0090273E6A60}"
    _reg_contractid_ = "@activestate.com/koLinter?language=Test;1"

    def __init__(self):
        pass

    def lint(self, request):
        """Return a list of koILintResult's given a ISciMoz object."""
        text = request.content.encode(request.encoding.python_encoding_name)
        cwd = request.cwd

        import re
        lines = text.split('\n')
        lineNum = 1
        complainRe = re.compile(r'\bself\b')
        results = koLintResults()
        for line in lines:
            # for testing, lets just bitch about the word 'self'
            print 'linting:', repr(line)
            complainMatch = complainRe.search(line)
            if complainMatch:
                r = KoLintResult()
                r.lineStart = lineNum
                r.lineEnd = lineNum
                r.columnStart = complainMatch.start() + 1
                r.columnEnd = complainMatch.end() + 1
                r.description = "I don't like you use of 'self' there pardner."
                r.severity = r.SEV_WARNING 
                results.addResult(r)
                print 'error: (%d,%d)(%d,%d): %s' %\
                    (r.lineStart, r.lineEnd, r.columnStart, r.columnEnd,
                    r.description)
            lineNum = lineNum + 1
        return results

