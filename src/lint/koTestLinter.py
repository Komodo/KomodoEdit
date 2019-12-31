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


from __future__ import print_function
from xpcom import components
from koLintResult import *
from koLintResults import koLintResults


class KoTestLinter:
    _com_interfaces_ = [components.interfaces.koILinter]
    _reg_desc_ = "Komodo Linter"
    _reg_clsid_ = "{2164884E-492F-11d4-AC24-0090273E6A60}"
    _reg_contractid_ = "@activestate.com/koLinter?language=Test;1"
    _reg_categories_ = [
         ("category-komodo-linter", 'Test'),
         ]

    def __init__(self):
        pass

    def lint(self, request):
        text = request.content.encode(request.encoding.python_encoding_name)
        return self.lint_with_text(request, text)
        
    def lint_with_text(self, request, text):
        """Return a list of koILintResult's given a ISciMoz object."""
        cwd = request.cwd

        import re
        lines = text.split('\n')
        lineNum = 1
        complainRe = re.compile(r'\bself\b')
        results = koLintResults()
        for line in lines:
            # for testing, lets just bitch about the word 'self'
            print('linting:', repr(line))
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
                print('error: (%d,%d)(%d,%d): %s' %\
                    (r.lineStart, r.lineEnd, r.columnStart, r.columnEnd,
                    r.description))
            lineNum = lineNum + 1
        return results

