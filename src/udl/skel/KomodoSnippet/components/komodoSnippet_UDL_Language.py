# Registers the EJS.text language in Komodo.

import re, sys
import logging
from xpcom import components
from xpcom.server import UnwrapObject
from koUDLLanguageBase import KoUDLLanguage
from koLintResults import koLintResults
from koLintResult import createAddResult, SEV_ERROR

log = logging.getLogger("komodoSnippetLanguage")
#log.setLevel(logging.DEBUG)

def registerLanguage(registry):
    log.debug("Registering language komodoSnippet")
    registry.registerLanguage(komodoSnippetLanguage())

class komodoSnippetLanguage(KoUDLLanguage):

    # ------------ Komodo Registration Information ------------ #

    name = "Komodo Snippet"
    lexresLangName = "Komodo_Snippet"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" % name
    _reg_categories_ = [("komodo-language", name)]
    _reg_clsid_ = "5042e8d9-7a1e-44bc-9552-d37f60f14c47"
    defaultExtension = '.snippet'

    # ------------ Commenting Controls ------------ #

    commentDelimiterInfo = {
        "block": [
                ('<%#', '%>')   # Pascal-style block comments
                ],
    }
    
    supportsSmartIndent = "brace"
    lang_from_udl_family = {'CSL': 'JavaScript', 'TPL': 'EJS', 'M': 'HTML'}

    sample = """
<% if (ko.snippets.rightOfFirstKeyword()) {%>
if [[%tabstop:test]]
	[[%tabstop:#code]]
        <%= blipper() %>
end
[[%tabstop: ]]
<% } else {
  throw new ko.snippets.RejectedSnippet("not at start of line");
   } %>
    """
class KoKomodoSnippetLinter(object):
    _com_interfaces_ = [components.interfaces.koILinter]
    _reg_desc_ = "EJS Template Linter"
    _reg_clsid_ = "{597b8e69-c0bd-4f27-be01-7e07d26120de}"
    _reg_contractid_ = "@activestate.com/koLinter?language=Komodo%20Snippet;1"
    _reg_categories_ = [
        ("category-komodo-linter", 'Komodo Snippet'),
    ]

    def __init__(self):
        self._jsLinter = UnwrapObject(components.classes["@activestate.com/koLintService;1"].getService(components.interfaces.koILintService).getLinterForLanguage("JavaScript"))
    
    def lint(self, request):
        return self.lint_with_text(request, request.content)

    def _escapeVerbatimLine(self, s):
        return s.replace('\\', '\\\\').replace("'", "\\'")
    
    def _addVerbatimPieces(self, finalPieces, s):
        for line in s.splitlines(True):
            lead = line.splitlines()[0]
            nl = line[len(lead):]
            if lead:
                piece = "__ViewO.push('" + self._escapeVerbatimLine(lead)
                if nl:
                    piece += "\\n');" + nl
                else:
                    piece += "');"
                finalPieces.append(piece)
            elif nl:
                finalPieces.append(nl)

    def _addJSPieces(self, finalPieces, s):
        # This is simple
        finalPieces.append(s)

    def _addEmittedPieces(self, finalPieces, s):
        finalPieces.append("__ViewO.push(%s);" % (s))
        #for line in s.splitlines():
        #   finalPieces.append("__ViewO.push(%s);\n" % (line,))

    # states:
    # 0: default
    # 1: emitted JS
    # 2: control JS
    # 3: EJS comment block
    _dot_to_space_re = re.compile(r'[^\r\n]')
    def lint_with_text(self, request, text):
        # Pull out the EJS parts and wrap into a single JS file
        textAsBytes = text.encode("utf-8")
        lim = len(textAsBytes)
        finalPieces = ["var __ViewO = []; "]
        i = 0
        state = 0
        results = koLintResults()
        textLines = textAsBytes.splitlines()
        lineNum = 1
        haveJS = False
        while i < lim:
            if state == 0:
                idx = textAsBytes.find("<%", i)
                if idx == -1:
                    thisBit = textAsBytes[i:]
                else:
                    thisBit = textAsBytes[i:idx]
                lineNum += thisBit.count("\n")
                self._addVerbatimPieces(finalPieces, thisBit)
                if idx == -1:
                    break
                try:
                    c = textAsBytes[idx + 2]
                    if c == '=':
                        haveJS = True
                    elif c == '#':
                        haveJS = True
                    elif c == '%':
                        pass # stay at state 0
                    else:
                        raise IndexError()
                    i = idx + 3
                    finalPieces.append("   ")
                except IndexError:
                    state = 2
                    i = idx + 2
                    finalPieces.append("  ")
            else:
                idx = textAsBytes.find("%%>", i)
                if idx >= 0:
                    finalPieces.append("   ")
                    i = idx + 3
                    continue
                idx = textAsBytes.find("%>", i)
                if idx == -1:
                    thisBit = textAsBytes[i:]
                else:
                    thisBit = textAsBytes[i:idx]
                lineNum += thisBit.count("\n")
                if state == 1:
                    self._addEmittedPieces(finalPieces, thisBit)
                elif state == 2:
                    self._addJSPieces(finalPieces, thisBit)
                else:
                    # Convert the comment block into spaces
                    finalPieces.append(self._dot_to_space_re.sub(' ', thisBit))
                finalPieces.append("  ")
                if idx == -1:
                    createAddResult(results, textLines, SEV_ERROR, lineNum, "Missing closing '%>'")
                    break
                i = idx + 2
                state = 0
        if haveJS:
            jsText = ("").join(finalPieces)
            jsResults = self._jsLinter.lint_with_text(request, jsText)
            results.addResults(jsResults)
        return results
