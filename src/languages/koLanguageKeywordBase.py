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
# Portions created by ActiveState Software Inc are Copyright (C) 2000-2012
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

"""Language service base class for keyword-based languages"""
import os, sys, re
import logging

from xpcom import components
from xpcom.server import WrapObject
from koLanguageServiceBase import KoLanguageBase
import scimozindent

log = logging.getLogger('koLanguageKeywordBase')
#log.setLevel(logging.DEBUG)

sci_constants = components.interfaces.ISciMoz

class Token:
    def __init__(self, style, text, start_pos):
        self.style = style
        self.text = text
        self.start_pos = start_pos
        
    def __str__(self):
        return "<Token style:%d, text:%r, pos:%d>" % (self.explode())

    def explode(self):
        return (self.style, self.text, self.start_pos)

class KeywordLangException(Exception):
    pass

class KoLanguageKeywordBase(KoLanguageBase):
    # These mark the end of a block
    # Note that 'else' can also be an indenter.
    _keyword_dedenting_keywords = [] # eg: 'end', 'esac', 'done', 'fi', 'else'

    # Allow all these characters to work as line-up, as the keywords
    # manage indenting.
    _lineup_chars = u"{}()[]"
    _lineup_open_chars = "([{"
    _lineup_close_chars = ")]}"
    
    def __init__(self, call_super=True):
        if call_super:
            KoLanguageBase.__init__(self)
        if not self._style_info._default_styles:
            self._style_info._default_styles = [0]
        self.prefService = components.classes["@activestate.com/koPrefService;1"].\
            getService(components.interfaces.koIPrefService)
        self._prefs = self.prefService.prefs
        self._dedent_on_last_char = self._prefs.getBooleanPref("edit.indent.keyword.dedent_on_last_char")
        self._editAutoIndentStyle = self._prefs.getStringPref("editAutoIndentStyle")
        try:
            self._prefs.prefObserverService.addObserver(self, "edit.indent.keyword.dedent_on_last_char", 0)
            self._prefs.prefObserverService.addObserver(self, "editAutoIndentStyle", 0)
        except Exception, e:
            print e

    def observe(self, subject, topic, data):
        if topic == "edit.indent.keyword.dedent_on_last_char":
            self._dedent_on_last_char = self._prefs.getBooleanPref(topic)
        elif topic == "editAutoIndentStyle":
            self._editAutoIndentStyle = self._prefs.getStringPref("editAutoIndentStyle")
        
    def _get_line_tokens(self, scimoz, start_pos, end_pos, style_info,
                         additional_ignorable_styles=None):
        test_line = scimoz.lineFromPosition(start_pos)
        tokens = []
        prev_style = -1
        curr_text = ""
        if additional_ignorable_styles:
            ignorable_styles = additional_ignorable_styles + style_info._ignorable_styles
        else:
            ignorable_styles = style_info._ignorable_styles
        if scimoz.getWCharAt(end_pos) in self._indent_close_chars + self._lineup_close_chars:
            end_pos -= 1
        if end_pos >= scimoz.length:
            end_pos = scimoz.length - 1
        for pos in range(start_pos, end_pos + 1):
            curr_style = scimoz.getStyleAt(pos)
            curr_char_val = scimoz.getCharAt(pos)
            if curr_char_val < 0:
                curr_char_val += 256
            curr_char = chr(curr_char_val)
            if (curr_style in ignorable_styles
                or curr_style != prev_style) and len(curr_text) > 0:
                tokens.append(Token(prev_style, curr_text, prev_pos))
                curr_text = ""

            if curr_style in ignorable_styles:
                pass # nothing to do
            elif curr_style in style_info._indent_styles:
                # No reason to keep it for another round
                tokens.append(Token(curr_style, curr_char, pos))
                curr_text = ""
            elif len(curr_text) == 0:
                # Start a token
                prev_style = curr_style
                curr_text = curr_char
                prev_pos = pos
            else:
                # Keep appending
                curr_text += curr_char
        if len(curr_text) > 0:
            tokens.append(Token(prev_style, curr_text, prev_pos))
        return tokens

    def getTokenDataForComputeIndent(self, scimoz, style_info):
        currentPos = scimoz.currentPos
        lineNo = scimoz.lineFromPosition(currentPos)
        lineStartPos = scimoz.positionFromLine(lineNo)
        tokens = self._get_line_tokens(scimoz, lineStartPos, currentPos, style_info)
        non_ws_tokens = [tok for tok in tokens
                         if tok.style not in style_info._default_styles]
        calculatedData = {
            'currentPos': currentPos,
            'lineNo': lineNo,
            'lineStartPos': lineStartPos,
            'tokens':tokens,
            'non_ws_tokens':non_ws_tokens,
        }
        return calculatedData

    def computeIndent(self, scimoz, indentStyle, continueComments,
                      calculatedData=None):
        """
        calculatedData: a dict containing info already calculated by
        a lower method
        """
        if continueComments:
            return KoLanguageBase.computeIndent(self, scimoz, indentStyle, continueComments)
        # Don't end up calling a subclass routine.
        indent = KoLanguageKeywordBase._computeIndent(self, scimoz, indentStyle, continueComments, self._style_info, calculatedData)
        if indent is not None:
            return indent
        return KoLanguageBase._computeIndent(self, scimoz, indentStyle, continueComments, self._style_info)

    def _computeIndent(self, scimoz, indentStyle, continueComments, style_info,
                       calculatedData=None):
        """
        If the current line starts with an indenter, count all the keywords
        on the line to decide what the final indent should be.
        """
        if calculatedData is None:
            calculatedData = self.getTokenDataForComputeIndent(scimoz, style_info)
        non_ws_tokens = calculatedData['non_ws_tokens']
        if len(non_ws_tokens) == 0:
            return
        if non_ws_tokens[0].style not in style_info._keyword_styles:
            return
        if non_ws_tokens[0].text not in self._indenting_statements:
            # Do this only if the line starts with an indenter.
            # Otherwise we want to use the general language-service's indenter
            # to look for braces to match.
            return
        delta = 1
        for tok in non_ws_tokens[1:]:
            if tok.style in style_info._keyword_styles:
                text = tok.text
                if text in self._indenting_statements:
                    delta += 1
                # not an elif, because some keywords are both indenters and dedenters
                # This works because if the first keyword is only counted as an indenter.
                if text in self._keyword_dedenting_keywords:
                    delta -= 1
        
        tok0 = calculatedData['tokens'][0]
        if tok0.style not in style_info._default_styles:
            currentIndentWidth = 0
        else:
            currentIndentWidth = len(tok0.text.expandtabs(scimoz.tabWidth))
        nextIndentWidth = currentIndentWidth + delta * scimoz.indent
        return scimozindent.makeIndentFromWidth(scimoz, nextIndentWidth)

    def _keyPressed(self, ch, scimoz, style_info):
        # This returns True if it did something....
        try:
            self._keyPressedAux(ch, scimoz, style_info)
        except:
            log.exception("_keyPressed threw an exception")
        # Always have the base class do its thing
        return KoLanguageBase._keyPressed(self, ch, scimoz, style_info)

    def _thisLineAlreadyDedented(self, scimoz, currLineNo, expected_indent):
        """
        In a keyword-based language, an ending keyword might already be
        in place.  We need to check on the last char of the keyword as
        well as on the character after the keyword
        """
        #XXX: There's a flaw here -- if the parent line encompasses 
        # several lines due to parens and line-continuations,
        # we might get it wrong.
        prevLineIndentWidth = self._getIndentWidthForLine(scimoz, currLineNo - 1)
        return prevLineIndentWidth > len(expected_indent.expandtabs(scimoz.tabWidth))
        
    def _checkIndentingCurrentAndPreviousLine(self, ch, scimoz, style_info):
        # This is complicated because the computeIndent was called to calculate
        # the indentation of the current line, so we need to check both this line
        # and the previous line.
        currentPos = scimoz.currentPos
        lastCharPos = scimoz.positionBefore(currentPos)
        currLineNo = scimoz.lineFromPosition(lastCharPos)
        if currLineNo <= 1:
            # Nothing to do on the first line
            return
        lineStartPos = scimoz.positionFromLine(currLineNo)
        # First make sure this line is all blank
        # If we aren't at the end of the line, back out.
        tokens = self._get_line_tokens(scimoz, lineStartPos, lastCharPos, style_info)
        if not tokens:
            # Nothing to do
            return
        if (len(tokens) != 1
            or tokens[0].style not in style_info._default_styles):
            return
        # Now look at the previous line.
        prevLineNo = currLineNo - 1
        prevLineStartPos = scimoz.positionFromLine(prevLineNo)
        prevLineEndPos = scimoz.getLineEndPosition(prevLineNo)
        prevTokens = self._get_line_tokens(scimoz, prevLineStartPos, prevLineEndPos - 1, style_info)
        if len(prevTokens) != 2:
            return
        if prevTokens[0].style not in style_info._default_styles:
            return
        if (prevTokens[1].style not in style_info._keyword_styles
            or prevTokens[1].text not in self._keyword_dedenting_keywords):
            return
        if len(prevTokens[0].text) > len(tokens[0].text):
            return
        # So now figure out what currLine - 2 indentation should have been
        currentPos = scimoz.currentPos
        scimoz.currentPos = scimoz.getLineEndPosition(prevLineNo - 1)
        try:
            expected_indent = self.computeIndent(scimoz, 'keyword', False)
        finally:
            scimoz.currentPos = currentPos
        expected_indent_sp = expected_indent.expandtabs(scimoz.tabWidth)
        leadingWS_sp = prevTokens[0].text.expandtabs(scimoz.tabWidth)
        currWSLen = len(leadingWS_sp)
        
        if len(expected_indent_sp) != currWSLen:
            return
        if self._thisLineAlreadyDedented(scimoz, prevLineNo, expected_indent):
            return
        # Dedent!
        ws_reduced = [None, None]
        newWSLen = currWSLen - scimoz.indent
        if newWSLen <= 0:
            ws_reduced[0] = ""
            posDelta = len(tokens[0].text)
        else:
            ws_reduced[0] = scimozindent.makeIndentFromWidth(scimoz, newWSLen)
            posDelta = scimoz.indent
        currWSLen = len(prevTokens[0].text.expandtabs(scimoz.tabWidth))
        newWSLen = currWSLen - scimoz.indent
        if newWSLen <= 0:
            ws_reduced[1] = ""
            posDelta += len(prevTokens[0].text)
        else:
            ws_reduced[1] = scimozindent.makeIndentFromWidth(scimoz, newWSLen)
            posDelta += scimoz.indent
        scimoz.beginUndoAction()
        try:
            # Dedent the second line first
            scimoz.targetStart = tokens[0].start_pos
            scimoz.targetEnd = tokens[0].start_pos + len(tokens[0].text)
            scimoz.replaceTarget(len(ws_reduced[0]), ws_reduced[0])
            scimoz.targetStart = prevTokens[0].start_pos
            scimoz.targetEnd = prevTokens[0].start_pos + len(prevTokens[0].text)
            scimoz.replaceTarget(len(ws_reduced[1]), ws_reduced[1])
            scimoz.currentPos = scimoz.anchor = currentPos - posDelta
        finally:
            scimoz.endUndoAction()
        return True
    
        
    def _keyPressedAux(self, ch, scimoz, style_info):
        """
        If we're at the start of a line, we're at the end of a dedenting_statement
        (Consult pref edit.indent.keyword.dedent_on_last_char to determine whether
        to do this on the last char of the keyword, or one after the last char),
        1. get the parent indent
        2. subtract one tabwidth from the current indent
        3. convert the leading white-space to tabs, if necessary
        4. replace the leading white-space with new white-space
        
        5. Assume self._keyword_dedenting_keywords is non-empty.
           Otherwise why would the subclass be using this as a superclass?
        """
        if self._editAutoIndentStyle != "smart":
            return
        if ch in ('\n', '\r'):
            return self._checkIndentingCurrentAndPreviousLine(ch, scimoz, style_info)
        currentPos = scimoz.currentPos
        lastCharPos = scimoz.positionBefore(currentPos)
        currLineNo = scimoz.lineFromPosition(lastCharPos)
        if currLineNo == 0:
            # Nothing to do on the first line
            return
        lineStartPos = scimoz.positionFromLine(currLineNo)
        # If we aren't at the end of the line, back out.
        tokens = self._get_line_tokens(scimoz, lineStartPos, lastCharPos, style_info)
        if (len(tokens) not in (2, 3)
            or tokens[0].style not in style_info._default_styles):
            return
        if not self._dedent_on_last_char and len(tokens) == 2:
            return
        word2Style = tokens[1].style
        if len(tokens) == 3:
            if (tokens[2].style not in style_info._default_styles
                or len(tokens[2].text) != 1
                or word2Style not in style_info._keyword_styles):
                return
        elif word2Style not in (style_info._keyword_styles + style_info._variable_styles):
            return
        # If the edit.indent.keyword.dedent_on_last_char pref is on, we can dedent
        # either on the last char on the pref, or one after.
        # If it's off, dedent only one after.
        if tokens[1].text not in self._keyword_dedenting_keywords:
            return
        # Next figure out what this line's indent should be based on the previous line.
        # If it's not the current indent, then the buffer's been changed, and don't
        # bother second-guessing the user.
        scimoz.currentPos = scimoz.getLineEndPosition(currLineNo - 1)
        try:
            expected_indent = self.computeIndent(scimoz, 'keyword', False)
        finally:
            scimoz.currentPos = currentPos
        leadingWS_sp = tokens[0].text.expandtabs(scimoz.tabWidth)
        currWSLen = len(leadingWS_sp)
        expected_indent_sp = expected_indent.expandtabs(scimoz.tabWidth)
        if len(expected_indent_sp) != currWSLen:
            return
        # If the parent line triggered a dedent (expected_indent < that line's
        # leading white-space, then we've already done it.
        #
        if self._thisLineAlreadyDedented(scimoz, currLineNo, expected_indent):
            return
                       
        # Dedent!
        newWSLen = currWSLen - scimoz.indent
        if newWSLen <= 0:
            ws_reduced = ""
        else:
            ws_reduced = scimozindent.makeIndentFromWidth(scimoz, newWSLen)
        scimoz.targetStart = lineStartPos
        scimoz.targetEnd = lineStartPos + len(tokens[0].text)
        scimoz.beginUndoAction()
        try:
            scimoz.replaceTarget(len(ws_reduced), ws_reduced)
        finally:
            scimoz.endUndoAction()
        return True

class KoCommonBasicLanguageService(KoLanguageKeywordBase):
    """
    So many variants of Basic with the same indenting handling, so put
    them all here.
    """
    supportsSmartIndent = "keyword"
    # Problems: 'private' and 'public' and 'shared' can come before a function name.
    # Need to add that then.
    _indenting_statements = ['do', 'for', 'while', 'if', 'sub', 'with', 'class', 'function', 'select', 'property', 'else']
    _dedenting_statements = ['exit', 'case',]
    _keyword_dedenting_keywords = """loop next wend else elseif end
    enddatasection endenumeration endif endinterface endprocedure 
                endselect endstructure endstructureunion""".split()

    def __init__(self):
        KoLanguageKeywordBase.__init__(self)
        self._style_info.update(
            _indent_styles = [sci_constants.SCE_B_OPERATOR],
            _variable_styles = [sci_constants.SCE_B_IDENTIFIER],
            _lineup_close_styles = [sci_constants.SCE_B_OPERATOR],
            _lineup_styles = [sci_constants.SCE_B_OPERATOR],
            _multiline_styles = [sci_constants.SCE_B_STRING],
            _keyword_styles = [sci_constants.SCE_B_KEYWORD,
                               sci_constants.SCE_B_KEYWORD2,
                               sci_constants.SCE_B_KEYWORD3,
                               sci_constants.SCE_B_KEYWORD4,
                               ],
            _default_styles = [sci_constants.SCE_B_DEFAULT],
            _ignorable_styles = [sci_constants.SCE_B_ERROR,
                                 sci_constants.SCE_B_COMMENT,
                                 sci_constants.SCE_B_NUMBER],
            )

    # Look for private/protected/public modifiers on sub/function definitions
    def computeIndent(self, scimoz, indentStyle, continueComments):
        calculatedData = self.getTokenDataForComputeIndent(scimoz, self._style_info)
        indent = self._computeIndent(scimoz, indentStyle, continueComments, self._style_info, calculatedData)
        if indent is not None:
            return indent
        return KoLanguageKeywordBase.computeIndent(self, scimoz, indentStyle, continueComments, calculatedData=calculatedData)

    def _computeIndent(self, scimoz, indentStyle, continueComments, style_info,
                       calculatedData):
        if not self._lookingAtReturnFunction(calculatedData['non_ws_tokens'],
                                             style_info):
            return None
        tok0 = calculatedData['tokens'][0]
        if tok0.style in style_info._default_styles:
            currWSLen = len(tok0.text.expandtabs(scimoz.tabWidth))
            newWSLen = currWSLen + scimoz.indent
        else:
            newWSLen = scimoz.indent
        return scimozindent.makeIndentFromWidth(scimoz, newWSLen)

    def _lookingAtReturnFunction(self, non_ws_tokens, style_info):
        if len(non_ws_tokens) <= 1:
            return False
        if non_ws_tokens[0].style not in style_info._keyword_styles:
            return False
        if non_ws_tokens[1].style not in style_info._keyword_styles:
            return False
        function_idx = 1
        if non_ws_tokens[0].text.lower() == 'public':
            if non_ws_tokens[1].text.lower() == 'default':
                if len(non_ws_tokens) == 2:
                    return False
                if non_ws_tokens[2].style not in style_info._keyword_styles:
                    return False
                function_idx = 2
        elif non_ws_tokens[0].text.lower() != 'private':
            return False
        if non_ws_tokens[function_idx].text.lower() not in ('sub', 'function'):
            return False
        return True
