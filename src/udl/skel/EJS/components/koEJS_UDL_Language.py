# Komodo EJS language service.
#

import re
import logging
from xpcom import components
from xpcom.server import UnwrapObject
from koXMLLanguageBase import koHTMLLanguageBase
from koLintResults import koLintResults

import scimozindent

log = logging.getLogger("koEJSLanguage")
#log.setLevel(logging.DEBUG)


def registerLanguage(registry):
    log.debug("Registering language EJS")
    registry.registerLanguage(KoEJSLanguage())


class KoEJSLanguage(koHTMLLanguageBase):
    name = "EJS"
    lexresLangName = "EJS"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" % name
    _reg_clsid_ = "{B341E24D-0857-4608-9EFE-389F8CDCD34F}"
    _reg_categories_ = [("komodo-language", name)]
    defaultExtension = '.ejs'

    lang_from_udl_family = {'CSL': 'JavaScript', 'TPL': 'EJS', 'M': 'HTML', 'CSS': 'CSS', 'SSL': 'JavaScript'}

    sample = """<ul>
<% products.forEach(funtion(product) { %>
  <li><%=  product.name %></li>
<% }); %>
</ul>
"""

    def insertInternalNewline_Special(self, scimoz, indentStyle, currentPos,
                                      allowExtraNewline, style_info):
        """
        Split %|% so the %'s are on separate lines, and there's a blank line
        in the middle.
        """
        if indentStyle is None or currentPos < 2:
            return None
        if scimoz.getStyleAt(currentPos) != scimoz.SCE_UDL_TPL_OPERATOR:
            return None
        percentChar = ord("%")
        if scimoz.getCharAt(currentPos) != percentChar:
            return None
        prevPos = currentPos - 1 # ascii
        if scimoz.getStyleAt(prevPos) != scimoz.SCE_UDL_TPL_OPERATOR:
            return None
        if scimoz.getCharAt(prevPos) != percentChar:
            return None
        prev2Pos = prevPos - 1
        if scimoz.getStyleAt(prev2Pos) != scimoz.SCE_UDL_TPL_OPERATOR:
            return None
        if scimoz.getCharAt(prev2Pos) != ord("<"):
            return None        
        lineNo = scimoz.lineFromPosition(currentPos)
        closeIndentWidth = self._getIndentWidthForLine(scimoz, lineNo)
        if indentStyle == 'smart':
            """
            i<%|% ==>
            
            i<%
            i....<|>
            i%
            
            where "i" denotes the current leading indentation
            """
            intermediateLineIndentWidth = self._getNextLineIndent(scimoz, lineNo)
        else:
            """
            i<%|% ==>
            
            i<%
            i<|>
            i%
            
            Note that the indentation of inner attr lines are ignored, even in block-indent mode:
            i<foo
            i........attr="val">|</foo> =>
            
            i<foo
            i........attr="val">
            i</foo>
            """
            intermediateLineIndentWidth = closeIndentWidth
        
        currentEOL = eollib.eol2eolStr[eollib.scimozEOL2eol[scimoz.eOLMode]]
        textToInsert = currentEOL + scimozindent.makeIndentFromWidth(scimoz, intermediateLineIndentWidth)
        finalPosn = currentPos + len(textToInsert) #ascii-safe
        if allowExtraNewline:
            textToInsert += currentEOL + scimozindent.makeIndentFromWidth(scimoz, closeIndentWidth)
        scimoz.addText(len(textToInsert), textToInsert) #ascii-safe
        return finalPosn
    
    def computeIndent(self, scimoz, indentStyle, continueComments):
        return self._computeIndent(scimoz, indentStyle, continueComments, self._style_info)

    def _computeIndent(self, scimoz, indentStyle, continueComments, style_info):
        res = self._doIndentHere(scimoz, indentStyle, continueComments, style_info)
        if res is None:
            return koHTMLLanguageBase.computeIndent(self, scimoz, indentStyle, continueComments)
        return res

    def _keyPressed(self, ch, scimoz, style_info):
        res = self._doKeyPressHere(ch, scimoz, style_info)
        if res is None:
            return koHTMLLanguageBase._keyPressed(self, ch, scimoz, style_info)
        return res

    _startWords = "begin case else elsif ensure for if rescue unless until while".split(" ")

    def _doIndentHere(self, scimoz, indentStyle, continueComments, style_info):
        pos = scimoz.positionBefore(scimoz.currentPos)
        startPos = scimoz.currentPos
        style = scimoz.getStyleAt(pos)
        if style != scimoz.SCE_UDL_TPL_OPERATOR:
            return None
        if scimoz.getWCharAt(pos) != ">":
            return None
        pos -= 1
        style = scimoz.getStyleAt(pos)
        if style != scimoz.SCE_UDL_TPL_OPERATOR:
            return None
        if scimoz.getWCharAt(pos) != "%":
            return None
        curLineNo = scimoz.lineFromPosition(pos)
        lineStartPos = scimoz.positionFromLine(curLineNo)
        delta, numTags = self._getTagDiffDelta(scimoz, lineStartPos, startPos)
        if delta < 0 and numTags == 1 and curLineNo > 0:
            didDedent, dedentAmt = self.dedentThisLine(scimoz, curLineNo, startPos)
            if didDedent:
                return dedentAmt
            else:
                # Since EJS tags end with a ">", keep the
                # HTML auto-indenter out of here.
                return self._getRawIndentForLine(scimoz, curLineNo)
        indentWidth = self._getIndentWidthForLine(scimoz, curLineNo)
        indent = scimoz.indent
        newIndentWidth = indentWidth + delta * indent
        if newIndentWidth < 0:
            newIndentWidth = 0
        #qlog.debug("new indent width: %d", newIndentWidth)
        return scimozindent.makeIndentFromWidth(scimoz, newIndentWidth)

    def _doKeyPressHere(self, ch, scimoz, style_info):
        # Returns either None or an indent string
        pos = scimoz.positionBefore(scimoz.currentPos)
        startPos = scimoz.currentPos
        style = scimoz.getStyleAt(pos)
        if style != scimoz.SCE_UDL_TPL_OPERATOR:
            return None
        if scimoz.getWCharAt(pos) != ">":
            return None
        pos -= 1
        curLineNo = scimoz.lineFromPosition(pos)
        lineStartPos = scimoz.positionFromLine(curLineNo)
        delta, numTags = self._getTagDiffDelta(scimoz, lineStartPos, startPos)
        if delta < 0 and numTags == 1 and curLineNo > 0:
            didDedent, dedentAmt = self.dedentThisLine(scimoz, curLineNo, startPos)
            if didDedent:
                return dedentAmt
        # Assume the tag's indent level is fine, so don't let the
        # HTML auto-indenter botch things up.
        return self._getRawIndentForLine(scimoz, curLineNo)

    def _getTagDiffDelta(self, scimoz, lineStartPos, startPos):
        data = scimoz.getStyledText(lineStartPos, startPos)
        chars = data[0::2]
        styles = [ord(x) for x in data[1::2]]
        lim = len(styles)
        delta = 0
        numTags = 0
        i = 0
        limSub1 = lim - 1
        while i < limSub1:
            if (styles[i] == scimoz.SCE_UDL_TPL_OPERATOR
                and styles[i + 1] == scimoz.SCE_UDL_TPL_OPERATOR
                and chars[i] == '<'
                and chars[i + 1] == "%"):
                j = i + 2
                while (j < lim
                       and styles[j] == scimoz.SCE_UDL_SSL_DEFAULT):
                    j += 1
                if styles[j] != scimoz.SCE_UDL_SSL_WORD:
                    i = j + 1
                    continue
                wordStart = j
                while (j < lim
                       and styles[j] == scimoz.SCE_UDL_SSL_WORD):
                    j += 1
                word = chars[wordStart:j]
                if word == 'end':
                    numTags += 1
                    delta -= 1
                elif word in self._startWords:
                    numTags += 1
                    delta += 1
                i = j
            else:
                i += 1
        return delta, numTags

_tplPatterns = ("EJS", re.compile('<%='), re.compile(r'%>\s*\Z', re.DOTALL))
# If the text starts with a doctype decl'n or HTML, don't insert doctype in.
_startCheck = { "HTML": (re.compile(r'<!doctype\b|<html\b', re.I), "<!DOCTYPE html>") }
class KoEJSLinter(object):
    _com_interfaces_ = [components.interfaces.koILinter]
    _reg_desc_ = "EJS Template Linter"
    _reg_clsid_ = "{4A3A959D-469F-4675-8420-9C0B9878F136}"
    _reg_contractid_ = "@activestate.com/koLinter?language=EJS;1"
    _reg_categories_ = [
        ("category-komodo-linter", 'EJS'),
    ]

    def __init__(self):
        koLintService = components.classes["@activestate.com/koLintService;1"].getService(components.interfaces.koILintService)
        self._html_linter = UnwrapObject(koLintService.getLinterForLanguage("HTML5"))
        
    def lint(self, request):
        #TODO: Hook on parts to pull templatized-parts out of jslint
        return self._html_linter.lint(request, TPLInfo=_tplPatterns,
                                      startCheck=_startCheck)

    def lint_with_text(self, request, text):
        return None
