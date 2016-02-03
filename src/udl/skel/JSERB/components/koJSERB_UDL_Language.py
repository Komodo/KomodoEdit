# Komodo JSERB language service.
# Use erb to do #define-type processing on JS files.

import re
import logging
from xpcom import components
from xpcom.server import UnwrapObject
from koXMLLanguageBase import koHTMLLanguageBase
from koLintResults import koLintResults

import scimozindent

log = logging.getLogger("koJSERBLanguage")
#log.setLevel(logging.DEBUG)


def registerLanguage(registry):
    log.debug("Registering language JSERB")
    registry.registerLanguage(KoJSERBLanguage())


class KoJSERBLanguage(koHTMLLanguageBase):
    name = "JSERB"
    lexresLangName = "JSERB"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" % name
    _reg_clsid_ = "{75C71FDC-B09A-4924-BE99-D06A47A24109}"
    _reg_categories_ = [("komodo-language", name)]
    defaultExtension = '.js.erb'

    lang_from_udl_family = {'CSL': 'JavaScript', 'TPL': 'JSERB', 'SSL':'Ruby'}

    sample = """<ul>
// Starts with JS code....
// JS code...
<% if Debug %> // Ruby inside the blocks
this.dump("QQQ: Something weird happening here: " + var);
<% end %>
// Back to regular js code
"""

    # Removed: insertInternalNewline_Special
    
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

_tplPatterns = ("JSERB", re.compile('<%='), re.compile(r'%>\s*\Z', re.DOTALL))

class KoJSERBLinter(object):
    _com_interfaces_ = [components.interfaces.koILinter]
    _reg_desc_ = "JSERB Template Linter"
    _reg_clsid_ = "{F412478A-6DA6-4DF8-A6D6-E26A1DADF1A4}"
    _reg_contractid_ = "@activestate.com/koLinter?language=JSERB;1"
    _reg_categories_ = [
        ("category-komodo-linter", 'JSERB'),
    ]

    def __init__(self):
        koLintService = components.classes["@activestate.com/koLintService;1"].getService(components.interfaces.koILintService)
        # Still need to use HTML's _lint_common_html_request to pull out the
        # erb directives
        self._html_linter = UnwrapObject(koLintService.getLinterForLanguage("HTML5"))
        
    def lint(self, request):
        #TODO: Hook on parts to pull templatized-parts out of jslint
        return self._html_linter.lint(request, TPLInfo=_tplPatterns)

    def lint_with_text(self, request, text):
        return None
