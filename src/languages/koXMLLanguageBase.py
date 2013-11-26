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

from xpcom import components, ServerException
from xpcom.server import UnwrapObject

from koLanguageServiceBase import *
from koUDLLanguageBase import KoUDLLanguage, udl_family_from_style
import scimozindent

log = logging.getLogger('koXMLLanguageBase')
#log.setLevel(logging.DEBUG)

class koXMLLanguageBase(KoUDLLanguage):

    primary = 1
    commentDelimiterInfo = { "block": [ ("<!--", "-->") ]  }
    _indent_chars = u'<>'
    _indent_open_chars = u'>'
    _indent_close_chars = u'>'
    _lineup_chars = '' # don't indent ()'s and the like in XML/HTML!
    _lineup_open_chars = "" # don't indent ()'s and the like in XML/HTML!

    supportsSmartIndent = "XML"

    def __init__(self):
        KoUDLLanguage.__init__(self)
        self.softchar_accept_matching_single_quote = self._filter_quotes_in_plaintext_context
        self.softchar_accept_matching_double_quote = self._filter_quotes_in_plaintext_context

    def getEncodingWarning(self, encoding):
        if not encoding.use_byte_order_marker:
            if encoding.python_encoding_name.startswith('utf-16') or encoding.python_encoding_name.startswith('ucs-'):
                return 'Including a signature (BOM) is recommended for "%s".' % encoding.friendly_encoding_name
            else:
                return ''
        else: # It's all good
            return ''
    
    def _getTagName_Forward(self, scimoz, tagStartPos):
        p = tagStartPos
        lim = scimoz.length
        while p < lim and scimoz.getStyleAt(p) == scimoz.SCE_UDL_M_TAGNAME:
            p = scimoz.positionAfter(p)
        return scimoz.getTextRange(tagStartPos, p)
    
    def _getStartTagStartPosn_Backward(self, scimoz, tagEndPos):
        p = tagEndPos - 1
        while p > 0 and scimoz.getStyleAt(p) != scimoz.SCE_UDL_M_STAGO:
            p = scimoz.positionBefore(p)
        return p

    def insertInternalNewline_Special(self, scimoz, indentStyle, currentPos,
                                      allowExtraNewline, style_info):
        """
        Handle cases where the user presses newline between the end of a start-tag
        and the start of the following end-tag.  Tag names must match.
        Precondition: the current pos is between two characters, so we know
        0 < currentPos < scimoz.length, so we don't have to test for those boundaries.
        """
        if indentStyle is None:
            return None
        if scimoz.getStyleAt(currentPos) != scimoz.SCE_UDL_M_ETAGO:
            return None
        startTagLineNo = self._immediatelyPrecedingStartTagLineNo(scimoz, currentPos)
                  
        if startTagLineNo is None:
            # returns (startTag:s, startTag:e, endTag:s, endTag:e)
            startTagInfo = scimozindent.startTagInfo_from_endTagPos(scimoz, currentPos)
            if startTagInfo is None:
                return None
            startTagLineNo = scimoz.lineFromPosition(startTagInfo[0])
            allowExtraNewline = False
            indentStyle = 'plain'  # Don't indent new part
            
        closeIndentWidth = self._getIndentWidthForLine(scimoz, startTagLineNo)
        if indentStyle == 'smart' and self.supportsSmartIndent == 'XML':
            """
            i<foo>|</foo> ==>
            
            i<foo>
            i....<|>
            i</foo>
            
            where "i" denotes the current leading indentation
            """
            intermediateLineIndentWidth = self._getNextLineIndent(scimoz, startTagLineNo)
        else:
            """
            i<foo>|</foo> ==>
            
            i<foo>
            i<|>
            i</foo>
            
            Note that the indentation of inner attr lines are ignored, even in block-indent mode:
            i<foo
            i........attr="val">|</foo> =>
            
            i<foo
            i........attr="val">
            i</foo>
            
            On ctrl-shift-newline, we don't get an extra blank line before the end-tag.
            """
            intermediateLineIndentWidth = closeIndentWidth
        
        currentEOL = eollib.eol2eolStr[eollib.scimozEOL2eol[scimoz.eOLMode]]
        textToInsert = currentEOL + scimozindent.makeIndentFromWidth(scimoz, intermediateLineIndentWidth)
        finalPosn = currentPos + len(textToInsert) #ascii-safe
        if allowExtraNewline:
            textToInsert += currentEOL + scimozindent.makeIndentFromWidth(scimoz, closeIndentWidth)
        scimoz.addText(len(textToInsert), textToInsert) #ascii-safe
        return finalPosn
    
    def _immediatelyPrecedingStartTagLineNo(self, scimoz, currentPos):
        """
        If we're between the end of a start-tag and the start of the
        closing tag, return the line # of the start-tag's start.
        Otherwise return None.  Preconditions given as assertions.
        """
        assert scimoz.getStyleAt(currentPos) == scimoz.SCE_UDL_M_ETAGO
        prevPos = currentPos - 1 # ascii
        if scimoz.getStyleAt(prevPos) != scimoz.SCE_UDL_M_STAGC:
            return None
        closeTagName = self._getTagName_Forward(scimoz, currentPos + 2)
        startTagStartPosn = self._getStartTagStartPosn_Backward(scimoz, prevPos)
        startTagName = self._getTagName_Forward(scimoz, startTagStartPosn + 1)
        if startTagName != closeTagName:
            return None
        return scimoz.lineFromPosition(startTagStartPosn)
    
    def _filter_quotes_in_plaintext_context(self, scimoz, pos, style_info, candidate):
        """Overwrite the base class method because there are more contexts in
        XML files where we don't want to treat a single-quote as a string delimiter."""   
        if pos == 0:
            return None
        prevCharPos = scimoz.positionBefore(pos)
        style = scimoz.getStyleAt(prevCharPos)
        if (style in (scimoz.SCE_UDL_M_DEFAULT,
                      scimoz.SCE_UDL_M_PI,
                      scimoz.SCE_UDL_M_CDATA)
            or style in style_info._string_styles
            or style in style_info._comment_styles):
            return None
        return candidate

    def softchar_accept_pi_close(self, scimoz, pos, style_info, candidate):
        """return '?' if we're at the start of a PI.
        """
        if pos == 0:
            return None
        currStyle = scimoz.getStyleAt(pos)
        if currStyle != scimoz.SCE_UDL_M_PI:
            return None
        if pos == 1:
            return candidate
        prev2Pos = scimoz.positionBefore(scimoz.positionBefore(pos))
        if scimoz.getStyleAt(prev2Pos) != scimoz.SCE_UDL_M_PI:
            return candidate
        return None

    _startTagStyles = (components.interfaces.ISciMoz.SCE_UDL_M_STAGO,
                       components.interfaces.ISciMoz.SCE_UDL_M_TAGNAME,
                       components.interfaces.ISciMoz.SCE_UDL_M_TAGSPACE,
                       components.interfaces.ISciMoz.SCE_UDL_M_ATTRNAME,
                       components.interfaces.ISciMoz.SCE_UDL_M_OPERATOR,
                       components.interfaces.ISciMoz.SCE_UDL_M_STRING,
                       components.interfaces.ISciMoz.SCE_UDL_M_STAGC,)
    _endTagStyles = (components.interfaces.ISciMoz.SCE_UDL_M_ETAGO,
                     components.interfaces.ISciMoz.SCE_UDL_M_ETAGC,
                     components.interfaces.ISciMoz.SCE_UDL_M_TAGSPACE,
                     components.interfaces.ISciMoz.SCE_UDL_M_TAGNAME,)
    _ambiguousTagStyles = (components.interfaces.ISciMoz.SCE_UDL_M_STAGO,
                           components.interfaces.ISciMoz.SCE_UDL_M_TAGSPACE,
                           components.interfaces.ISciMoz.SCE_UDL_M_TAGNAME,)

    def _onTargetTag(self, scimoz, pos, styleSet, targetStyle):
        style = scimoz.getStyleAt(pos)
        if style not in styleSet:
            return False
        if style not in self._ambiguousTagStyles:
            return True
        # move to the end of the tag, and verify we're on the
        # expected tag.  We can't move to the start, because
        # empty-start tags and full-start tags start with the same style
        lim = scimoz.length
        pos = scimoz.positionAfter(pos)
        while pos < lim:
            style = scimoz.getStyleAt(pos)
            if style == targetStyle:
                return True
            if style not in styleSet and udl_family_from_style(style) == "M":
                return False
            pos = scimoz.positionAfter(pos)
        return False
    
    def onStartTag(self, scimoz, pos):
        return self._onTargetTag(scimoz, pos, self._startTagStyles,
                                scimoz.SCE_UDL_M_STAGC)
    
    def onEndTag(self, scimoz, pos):
        return self._onTargetTag(scimoz, pos, self._endTagStyles,
                                scimoz.SCE_UDL_M_ETAGC)

    def findActualStartLine(self, scimoz, startLine):
        origPos = pos = scimoz.positionFromLine(startLine)
        nextLenPos = scimoz.positionFromLine(startLine + 1)
        if nextLenPos >= scimoz.textLength:
            nextLenPos = scimoz.textLength - 1
        while pos < nextLenPos and scimoz.getStyleAt(pos) == scimoz.SCE_UDL_M_DEFAULT:
            pos += 1
        if pos == nextLenPos:
            return startLine
        style = scimoz.getStyleAt(pos)
        if style not in self._startTagStyles:
            return startLine
        if style == scimoz.SCE_UDL_M_STAGO:
            return startLine
        pos = origPos
        while pos >= 0:
            pos -= 1
            if scimoz.getStyleAt(pos) == scimoz.SCE_UDL_M_STAGO:
                return scimoz.lineFromPosition(pos)
        return startLine

    def getMatchingTagInfo(self, scimoz, pos, constrainSearchInViewPort):
        return scimozindent.findMatchingTagPosition(scimoz, pos, self,
                                                    constrainSearchInViewPort)

    def getEndTagForStartTag(self, tag):
        """Return the end tag for a start tag
        @param tag {unicode} The start tag, e.g. "<window>", "<svg foo='bar'>"
        @returns {unicode} The matching end tag, e.g., "</window>", "</svg>"
        @note If the start tag is self-closing (e.g. "<br/>"), the returned end
            tag is empty.
        """
        assert tag.startswith("<"), "getEndTagForStartTag: tag does not start with '<'"
        assert tag.endswith(">"), "getEndTagForStartTag: tag does not end with '>'"
        tag = tag[1:-1]
        if tag.endswith("/"):
            # self-closing
            return ""
        tagName = tag.split()[0]
        assert not tagName.startswith("/"), \
            "getEndTagForStartTag: got an end tag instead"
        return u"</%s>" % (tagName,)


class koHTMLLanguageBase(koXMLLanguageBase):
    isHTMLLanguage = True

    # Elements which do not have an end tag.  Naming follows
    # http://www.whatwg.org/specs/web-apps/current-work/multipage/syntax.html#void-elements
    _void_elements = set()

    def softchar_accept_styled_chars(self, scimoz, pos, style_info, candidate, constraints):
        """This method is used by some of the UDL languages to figure out
        when to generate a soft character based on typed text. Typical examples
        are RHTML <% => %, Django {% => %, and Mason's <%_ => % (where _ is a space)
        """
        if pos < len(constraints['styled_chars']):
            return None
        style = scimoz.getStyleAt(pos)
        if style != constraints.get('curr_style', scimoz.SCE_UDL_TPL_OPERATOR):
            return None
        for pair in constraints['styled_chars']:
            pos = scimoz.positionBefore(pos)
            if scimoz.getStyleAt(pos) != pair[0] or scimoz.getCharAt(pos) != pair[1]:
                return None
        return candidate

    _leadingWSRE = re.compile(r'^(\s+)')
    def dedentThisLine(self, scimoz, curLineNo, startPos):
        # Used by UDL template languages
        # Returns a tuple:
        # First item: whether the current line needed to be dedented
        # Second item: the new indentation for the current line
        
        thisLinesIndent = scimoz.getLineIndentation(curLineNo)
        prevLinesIndent = scimoz.getLineIndentation(curLineNo - 1)
        if prevLinesIndent <= thisLinesIndent:
            # We need to dedent this line
            lineStartPos = scimoz.positionFromLine(curLineNo)
            text = scimoz.getTextRange(lineStartPos, startPos)
            m = self._leadingWSRE.match(text)
            if m:
                leadingWS = m.group(1)
                tabFreeLeadingWS = leadingWS.expandtabs(scimoz.tabWidth)
                currWidth = len(tabFreeLeadingWS)
                targetWidth = currWidth - scimoz.indent
                if targetWidth < 0:
                    fixedLeadingWS = ""
                else:
                    fixedLeadingWS = scimozindent.makeIndentFromWidth(scimoz, targetWidth)
                scimoz.targetStart = lineStartPos
                scimoz.targetEnd = lineStartPos + len(leadingWS)
                scimoz.replaceTarget(len(fixedLeadingWS), fixedLeadingWS)
                return (True, fixedLeadingWS)
        return (False, None)

    def getEndTagForStartTag(self, tag):
        """Return the end tag for a start tag
        @param tag {unicode} The start tag, e.g. "<window>", "<svg foo='bar'>"
        @returns {unicode} The matching end tag, e.g., "</window>", "</svg>"
        """
        assert tag.startswith("<"), "getEndTagForStartTag: tag does not start with '<'"
        assert tag.endswith(">"), "getEndTagForStartTag: tag does not end with '>'"
        tag = tag[1:-1].strip()
        if tag.endswith("/"):
            # fake self-closing tag, "<br />" - drop that.
            # (we rely on the list of void elements instead)
            tag = tag[:-1]
        tagName = tag.split()[0]
        assert not tagName.startswith("/"), \
            "getEndTagForStartTag: got an end tag instead"
        if tagName.lower() in self._void_elements:
            # this is a void element (no close tag)
            return ""
        return u"</%s>" % (tagName,)

class KoGenericXMLLinter(object):
    """
    Moving from the get_linter mechanism to categories means that
    we can't delegate any more.  Instead, XML-based linters define
    their own XPCOM stuff, but subclass this class, and work fine.
    """
    _com_interfaces_ = [components.interfaces.koILinter]
    
    def __init__(self):
        koLintService = components.classes["@activestate.com/koLintService;1"].getService(components.interfaces.koILintService)
        self._xml_linter = koLintService.getLinterForLanguage("XML")
    
    def lint(self, request):
        return self._xml_linter.lint(request)

    def lint_with_text(self, request, text):
        return UnwrapObject(self._xml_linter).lint_with_text(request, text)


class KoDjangoTemplateFamilyBase(koHTMLLanguageBase):
    def __init__(self):
        koHTMLLanguageBase.__init__(self)
        self.matchingSoftChars["%"] = ("%", self.accept_matching_percent)
        self._style_info.update(
            _indent_styles = [components.interfaces.ISciMoz.SCE_UDL_TPL_OPERATOR]
            )
        self._indent_chars = u'{}'
        self._indent_open_chars = u'{'
        self._indent_close_chars = u'}'

    def accept_matching_percent(self, scimoz, pos, style_info, candidate):
        return self.softchar_accept_styled_chars(
            scimoz, pos, style_info, candidate,
            {'styled_chars' : [
                    (scimoz.SCE_UDL_TPL_OPERATOR, ord("{"))
                ]
            })

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

    def _doIndentHere(self, scimoz, indentStyle, continueComments, style_info):
        # Returns either None or an indent string
        pos = scimoz.positionBefore(scimoz.currentPos)
        startPos = scimoz.currentPos
        style = scimoz.getStyleAt(pos)
        if style != scimoz.SCE_UDL_TPL_OPERATOR:
            return None
        if scimoz.getWCharAt(pos) != "}":
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
                return None
        indentWidth = self._getIndentWidthForLine(scimoz, curLineNo)
        indent = scimoz.indent
        newIndentWidth = indentWidth + delta * indent
        if newIndentWidth < 0:
            newIndentWidth = 0
        return scimozindent.makeIndentFromWidth(scimoz, newIndentWidth)

    _word_matcher_re = re.compile(r'\s*\{%\s*(?P<word>\w+)\s*$')
    def _doKeyPressHere(self, ch, scimoz, style_info):
        # Returns either None or an indent string
        pos = scimoz.positionBefore(scimoz.currentPos)
        startPos = scimoz.currentPos
        if startPos < 5:
            return None
        style = scimoz.getStyleAt(pos)
        if ((style == scimoz.SCE_UDL_TPL_DEFAULT and scimoz.getWCharAt(pos) in (' ', '\t'))
            or (style == scimoz.SCE_UDL_TPL_OPERATOR
                and scimoz.getWCharAt(pos) != "}")):
            # Dedent on {% [<slider>|end*]
            curLineNo = scimoz.lineFromPosition(pos)
            lineStartPos = scimoz.positionFromLine(curLineNo)
            textThisLine = scimoz.getTextRange(lineStartPos, pos)
            m = self._word_matcher_re.match(textThisLine)
            if m:
                kwd = m.group("word")
                if kwd in self._sliders or kwd.startswith("end"):
                    didDedent, dedentAmt = self.dedentThisLine(scimoz, curLineNo, startPos)
                    if didDedent:
                        return dedentAmt
            
        if style != scimoz.SCE_UDL_TPL_OPERATOR:
            return None
        if scimoz.getWCharAt(pos) != "}":
            return None
        pos -= 1
        if style != scimoz.SCE_UDL_TPL_OPERATOR:
            return None
        if scimoz.getWCharAt(pos) != "%":
            return None
        pos -= 1
        curLineNo = scimoz.lineFromPosition(pos)
        lineStartPos = scimoz.positionFromLine(curLineNo)
        delta, numTags = self._getTagDiffDelta(scimoz, lineStartPos, startPos)
        if delta < 0 and numTags == 1 and curLineNo > 0:
            didDedent, dedentAmt = self.dedentThisLine(scimoz, curLineNo, startPos)
            if didDedent:
                return dedentAmt
        return None

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
                and chars[i] == '{'
                and chars[i + 1] == "%"):
                j = i + 2
                while (j < lim
                       and styles[j] == scimoz.SCE_UDL_TPL_DEFAULT):
                    j += 1
                if styles[j] != scimoz.SCE_UDL_TPL_WORD:
                    i = j + 1
                    continue
                wordStart = j
                while (j < lim
                       and styles[j] == scimoz.SCE_UDL_TPL_WORD):
                    j += 1
                word = chars[wordStart:j]
                if word.startswith('end'):
                    delta -= 1
                    numTags += 1
                elif word in self._startWords:
                    delta += 1
                    numTags += 1
                i = j
            else:
                i += 1
        return delta, numTags
