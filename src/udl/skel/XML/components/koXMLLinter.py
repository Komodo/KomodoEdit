#!python
# Copyright (c) 2000-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

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

    def lint(self, request):
        """Lint the given XML content.
        
        Raise an exception and set an error on koLastErrorService if there
        is a problem.
        """

        text = eollib.convertToEOLFormat(request.content, eollib.EOL_LF)
        text = text.encode(request.encoding.python_encoding_name)
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

