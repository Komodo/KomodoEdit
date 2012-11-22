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

import os, sys, traceback, re
from xpcom import components
from koLintResult import *
from koLintResults import koLintResults
from xml.parsers import expat
import eollib
import logging


log = logging.getLogger("koXMLLinter")


class KoXMLCompileLinter:
    _com_interfaces_ = [components.interfaces.koILinter]
    _reg_desc_ = "Komodo XML Compile Linter"
    _reg_clsid_ = "{03d1177b-1f08-4218-8f43-ccb88f00f308}"
    _reg_contractid_ = "@activestate.com/koLinter?language=XML;1"
    _reg_categories_ = [
         ("category-komodo-linter", 'XML'),
         ]

    def __init__(self):
        koLintService = components.classes["@activestate.com/koLintService;1"].getService(components.interfaces.koILintService)
        self._html_linter = koLintService.getLinterForLanguage("HTML")

    def lint(self, request):
        return self._html_linter.lint(request)
    
    def lint_with_text(self, request, text):
        """Lint the given XML content.
        
        Raise an exception and set an error on koLastErrorService if there
        is a problem.
        """

        text = encodeRequestText(request, text)
        text = eollib.convertToEOLFormat(text, eollib.EOL_LF)
        cwd = request.cwd

        parser = expat.ParserCreate()
        results = koLintResults()
        
        try:
            # We need to remove the BOM on UTF-8 data to prevent expat from
            # crashing. We should check to see if this is still necesary
            # with every new Python version (we are at 2.0 now).
            utf8bom = u'\ufeff'.encode('utf-8')
            if text.startswith(utf8bom):
                parser.Parse(text[len(utf8bom):], 1)
            else:
                parser.Parse(text, 1)
                
        except expat.error:
            result = KoLintResult()
            result.description = "XML Error: %s" % expat.ErrorString(parser.ErrorCode)

            # find an existing, non-empty line on which to display result
            # XXX This logic should be in the LintDisplayer (should
            #     rearchitect a la Trent's lintx)
            text = eollib.convertToEOLFormat(request.content, eollib.EOL_LF)
            lines = text.split("\n")
            if parser.ErrorLineNumber > len(lines):
                lineStart = len(lines)
            else:
                lineStart = parser.ErrorLineNumber
            lineStart = parser.ErrorLineNumber
            retreated = 0
            while 1:
                if lineStart <= len(lines) and len(lines[lineStart-1]):
                    break
                elif lineStart == 0:
                    log.warn("Could not find a suitable line on which "
                             "to display lint result for line %d.",
                             parser.ErrorLineNumber)
                    return None
                else:
                    lineStart -= 1
                    retreated = 1
            if retreated:
                result.description += " (error is on line %d, but displayed "\
                                      "here)" % parser.ErrorLineNumber
            result.lineStart = result.lineEnd = lineStart

            result.columnStart = 1
            result.columnEnd = len(lines[result.lineEnd-1]) + 1
            result.severity = result.SEV_ERROR
            results.addResult(result)
        return results
