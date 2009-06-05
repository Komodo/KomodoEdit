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
import timeline

from koLanguageServiceBase import *
from koUDLLanguageBase import KoUDLLanguage
import scimozindent

log = logging.getLogger('koXMLLanguageBase')
#log.setLevel(logging.DEBUG)

class koXMLLanguageBase(KoUDLLanguage):

    primary = 1
    styleBits = 8
    supportsBraceHighlighting = 0
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
        
    def get_linter(self):
        return self._get_linter_from_lang("XML")

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
        assert indentStyle is not None
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
            if style not in styleSet:
                return False
            pos = scimoz.positionAfter(pos)
        return False
    
    def onStartTag(self, scimoz, pos):
        return self._onTargetTag(scimoz, pos, self._startTagStyles,
                                scimoz.SCE_UDL_M_STAGC)
    
    def onEndTag(self, scimoz, pos):
        return self._onTargetTag(scimoz, pos, self._endTagStyles,
                                scimoz.SCE_UDL_M_ETAGC)

    def getMatchingTagInfo(self, scimoz, pos, constrainSearchInViewPort):
        return scimozindent.findMatchingTagPosition(scimoz, pos, self,
                                                    constrainSearchInViewPort)
        

class koHTMLLanguageBase(koXMLLanguageBase):
    isHTMLLanguage = True
    
    def get_linter(self):
        return self._get_linter_from_lang("HTML")
    
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


def _findIndent(scimoz, bitmask, chars, styles, comment_styles, opening_styles):
    indenting = None
    timeline.enter("koXMLLanguage:_findIndent")
    try:
        # first, colourise the first 100 lines at most
        N = min(100, scimoz.lineCount-1)
        end = scimoz.getLineEndPosition(N)
        if scimoz.endStyled < end:
            scimoz.colourise(scimoz.endStyled, end)
        data = scimoz.getStyledText(0, end)
        # data is a list of (character, styleNo)
        WHITESPACE = '\t\n\x0b\x0c\r '  # don't use string.whitespace (bug 81316)
        
        for lineNo in range(N):
            if not scimoz.getLineIndentation(lineNo): # skip unindented lines
                continue
            lineEndPos = scimoz.getLineEndPosition(lineNo)
            lineStartPos = scimoz.positionFromLine(lineNo)
            line = scimoz.getTextRange(lineStartPos, lineEndPos)
            #start = lineEndPos
            # we're looking for the 'indenting' line
            for pos in range(lineEndPos, lineStartPos-1, -1):
                char = data[pos*2]
                style = ord(data[pos*2+1]) & bitmask
                if (char in chars) and (style in styles):
                    # partial success - we found that the first 'interesting'
                    # character from the right of the line is an
                    # indent-causing character
    
                    # now we need to find the line that _starts_ the XML tag.
                    # First look back in the document until you find a "<" character
                    # styled properly
                    for pos in range(pos, 0, -1):
                        char = data[pos*2]
                        style = ord(data[pos*2+1])
                        if char in ('<', u'<') and style in opening_styles:
                            startLineNo = scimoz.lineFromPosition(pos)
                            lineEndPos = scimoz.getLineEndPosition(startLineNo)
                            lineStartPos = scimoz.positionFromLine(startLineNo)
                            line = scimoz.getTextRange(lineStartPos, lineEndPos)
                            indenting = line
                            log.info("Found indenting line: %r" % line)
                            break
                    else:
                        log.info("couldn't find < tag")
                    break
                if char in WHITESPACE:
                    # skip whitespace
                    continue
                if style in comment_styles:
                    # skip comments
                    continue
            if indenting: break
        else:
            log.info("Couldn't find an indenting line")
            return '', ''
        lineNo += 1
        for lineNo in range(lineNo, N):
            lineEndPos = scimoz.getLineEndPosition(lineNo)
            lineStartPos = scimoz.positionFromLine(lineNo)
            line = scimoz.getTextRange(lineStartPos, lineEndPos)
            # we want to skip lines that are just comments or just whitespace
            for pos in range(lineEndPos, lineStartPos-1, -1):
                char = scimoz.getWCharAt(pos)
                style = scimoz.getStyleAt(pos) & bitmask
                if char in WHITESPACE:
                    # skip whitespace
                    continue
                if style in comment_styles:
                    # skip comments
                    continue
                # if we get here it must be a 'useful' line.
                indented = line
                log.info("Found indented line: %r" % line)
                return indenting, indented
        else:
            log.info("Couldn't find an indented line")
            return '', ''
    finally:
        timeline.leave("koXMLLanguage:_findIndent")

# taken from IDLE
# Look at the leading whitespace in s.
# Return pair (# of leading ws characters,
#              effective # of leading blanks after expanding
#              tabs to width tabwidth)

def classifyws(s, tabwidth):
    foundTabs = 0
    raw = effective = 0
    for ch in s:
        if ch == ' ':
            raw = raw + 1
            effective = effective + 1
        elif ch == '\t':
            foundTabs = 1
            raw = raw + 1
            effective = (effective / tabwidth + 1) * tabwidth
        else:
            break
    return raw, effective, foundTabs

