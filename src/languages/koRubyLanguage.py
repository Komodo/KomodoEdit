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

from xpcom import components, nsError, ServerException
from koLintResult import *
from koLintResults import koLintResults

from eollib import eol2eolStr, scimozEOL2eol
import logging
import os, sys, re
import tempfile
import string
import process
import koprocessutils
import scimozindent
import which
# import time  #for interal timing only

from koLanguageServiceBase import *
from koLanguageKeywordBase import KoLanguageKeywordBase

log = logging.getLogger("RubyLanguage")
#log.setLevel(logging.DEBUG)
indentlog = logging.getLogger("RubyLanguage.indent")
#indentlog.setLevel(logging.DEBUG)

sci_constants = components.interfaces.ISciMoz
ORD_SPACE = ord(' ')
ORD_TAB = ord('\t')
ORD_CR = ord('\r')
ORD_NL = ord('\n')
ORD_BS = ord('\\')
NUM_LINES_TO_ANALYZE = 100  # Make this configurable via a preference?


def isident(char):
    return "a" <= char <= "z" or "A" <= char <= "Z" or char == "_"

def isdigit(char):
    return "0" <= char <= "9"

# Inherit from KoLanguageKeywordBase instead of KoLanguageBase
# so the generic KoLanguageKeywordBase class can share code written
# specifically for Ruby.

class KoRubyLanguage(KoLanguageKeywordBase):
    name = "Ruby"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{3CFC5F18-0288-47e9-BF2D-061329D00FB6}"
    _reg_categories_ = [("komodo-language", name)]
    _com_interfaces_ = [components.interfaces.koILanguage,
                        components.interfaces.nsIObserver]

    accessKey = 'r'
    primary = 1
    defaultExtension = ".rb"
    extraFileAssociations = ["*.mab"] # .mab is Markaby
    shebangPatterns = [ re.compile(ur'\A#!.*ruby.*$', re.IGNORECASE | re.MULTILINE),]

    _lineup_chars = u"()[]"
    _lineup_open_chars = "(["
    _lineup_close_chars = ")]"
    
    styleStdin = sci_constants.SCE_RB_STDIN
    styleStdout = sci_constants.SCE_RB_STDOUT
    styleStderr = sci_constants.SCE_RB_STDERR
    
    def __init__(self):
        KoLanguageKeywordBase.__init__(self)
        self._keyword_dedenting_keywords = self._dedent_sliders
        self.prefService = components.classes["@activestate.com/koPrefService;1"].\
            getService(components.interfaces.koIPrefService)
        self._prefs = self.prefService.prefs
        self._indent_style = self._prefs.getStringPref("editAutoIndentStyle")
        self._handle_keypress = self._indent_style == 'smart'
        log.debug("Ruby indent style: %s", self._indent_style)
        try:
            self._prefs.prefObserverService.addObserver(self, "editAutoIndentStyle", 0)
            self._prefs.prefObserverService.addObserver(self, "rubyDefaultInterpreter", 0)
        except Exception, e:
            print e
        
        self._keyword_letters = string.ascii_letters
             
        self._style_info.update(
            _indent_styles = [sci_constants.SCE_RB_OPERATOR],
            _variable_styles = [sci_constants.SCE_RB_IDENTIFIER,
                                sci_constants.SCE_RB_GLOBAL,
                                sci_constants.SCE_RB_INSTANCE_VAR,
                                sci_constants.SCE_RB_CLASS_VAR],
            _lineup_close_styles = [sci_constants.SCE_RB_OPERATOR,
                                    sci_constants.SCE_RB_REGEX],
            _lineup_styles = [sci_constants.SCE_RB_OPERATOR,
                              sci_constants.SCE_RB_REGEX],
            _multiline_styles = [sci_constants.SCE_RB_STRING,
                                 sci_constants.SCE_RB_CHARACTER,
                                 sci_constants.SCE_RB_REGEX,
                                 sci_constants.SCE_RB_BACKTICKS,
                                 sci_constants.SCE_RB_STRING_Q,
                                 sci_constants.SCE_RB_STRING_QQ,
                                 sci_constants.SCE_RB_STRING_QX,
                                 sci_constants.SCE_RB_STRING_QR,
                                 sci_constants.SCE_RB_STRING_QW],
            _keyword_styles = [sci_constants.SCE_RB_WORD],
            # These handle things like <<break if test>>
            _modified_keyword_styles = [sci_constants.SCE_RB_WORD_DEMOTED],
            _default_styles = [sci_constants.SCE_RB_DEFAULT],
            _ignorable_styles = [sci_constants.SCE_RB_ERROR,
                                 sci_constants.SCE_RB_COMMENTLINE,
                                 sci_constants.SCE_RB_POD,
                                 sci_constants.SCE_RB_DATASECTION,
                                 sci_constants.SCE_RB_HERE_DELIM,
                                 sci_constants.SCE_RB_HERE_Q,
                                 sci_constants.SCE_RB_HERE_QQ,
                                 sci_constants.SCE_RB_HERE_QX],
            _regex_styles = [sci_constants.SCE_RB_DATASECTION,
                             sci_constants.SCE_RB_REGEX,
                             sci_constants.SCE_RB_STRING_QR],
            # Set this to [] in UDL
            _datasection_styles = [sci_constants.SCE_RB_DATASECTION]
        )
        self.matchingSoftChars["`"] = ("`", self.softchar_accept_matching_backquote)
        self._fastCharData = \
            FastCharData(trigger_char=";",
                         style_list=(sci_constants.SCE_RB_OPERATOR, ),
                         skippable_chars_by_style={ sci_constants.SCE_RB_OPERATOR: "])", })
        
    def observe(self, subject, topic, data):
        if topic == "editAutoIndentStyle":
            log.debug("**************** observer: subject %s, topic %s, data %s", subject, topic, data)
            self._indent_style = self._prefs.getStringPref("editAutoIndentStyle")
            self._handle_keypress = self._indent_style == 'smart'
        elif topic == "rubyDefaultInterpreter":
            if self._lexer:
                self.updateLexerVersionProperties()
        else:
            KoLanguageKeywordBase.observe(self, subject, topic, data)
        
    def getVariableStyles(self):
        return self._style_info._variable_styles

    def updateLexerVersionProperties(self):
        try:
            version = self.rubyInfoEx = components.classes["@activestate.com/koAppInfoEx?app=Ruby;1"].\
                      getService(components.interfaces.koIAppInfoEx).version
            majorVersion = int(version.split(".", 1)[0])
        except ServerException:
            majorVersion = 1
        except:
            majorVersion = 1
            log.exception("Unexpected exception in KoRubyLanguage.updateLexerVersionProperties")            
        self._lexer.setProperty("supportISymbolArray",
                                majorVersion >= 2 and "1" or "0")

    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(sci_constants.SCLEX_RUBY)
            self._lexer.setKeywords(0, self.keywords)
            self.updateLexerVersionProperties()
            self._lexer.supportsFolding = 1
        return self._lexer

    commentDelimiterInfo = {
        "line": [ "#" ],
    }
    variableIndicators = '$@'  # Won't find @@ class variables
    namedBlockRE = "^[ \t]*((?:def|module|class)\s+\w+)"
    namedBlockDescription = 'Ruby classes and methods'
    
    leading_ws_re = re.compile(r'^(\s*)')
    
    _sliders = ['else', 'elsif', 'ensure', 'rescue', 'when']
    _dedenters = ['break', 'redo', 'next', 'raise', 'retry', 'return']
    _limited_openers = ['begin', 'class', 'def', 'for', 'module', 'case',
                        'if', 'unless', 'until', 'while']
    _ending_openers = ['do']
    _openers = _limited_openers + _ending_openers
    _enders = ['end']
    _loop_kwds = ('for', 'while', 'until')
    

    _dedent_sliders = _sliders + _enders
    
    supportsSmartIndent = "keyword"  # should be overridden otherwise

    _max_lines_in_calc = 100
    sample = r"""#  Fruit salad recipe
# Let's build a fruit-salad maker
# This snippet just shows various parts of Ruby speech.

module Salad
  class Fruit
    @@class_var = 0
    attr :symbol
    def initialize(fruit_list, counts)
      @instance_var = {}
      fruit_list.zip(counts).each { |a, b| @instance_var[a] = b } # block code
    end
    def mix()
      print "double-quoted string"
      print 'single-quoted string'
      print `command`
      print %Q(Q string)
      print %q(q string)
      print %r(reg ex)
      print %x(backquoted string)
      regex = /pattern/isx
      @@class_var += 1
    end
  end
end

fruit_list = %w(guava rambutan longan mangosteen)
counts = [3, 4, 1, 5]
fruits = Salad::Fruit.new(fruit_list, counts)

print <<abc
here document
abc

=begin
rubydoc
block comment
=end

__END__
end section
    """
    
    # Pythonism
    # _dedenting_statements = [u'yield', u'raise', u'return', u'break', u'next']
    keywords = ["__FILE__", "__LINE__",
                 "BEGIN", "class", "ensure", "nil", "self", "when",
                 "END", "def", "false", "not", "super", "while",
                 "alias", "defined", "for", "or", "then", "yield",
                 "and", "do", "if", "redo", "true",
                 "begin", "else", "in", "rescue", "undef",
                 "break", "elsif", "module", "retry", "unless",
                 "case", "end", "next", "return", "until"]

    def get_interpreter(self):
        if self._interpreter is None:
            self._interpreter = components.classes["@activestate.com/koAppInfoEx?app=Ruby;1"].getService()
        return self._interpreter

    def _do_preceded_by_looper(self, tokens, do_style, style_info):
        # Don't process 'noise' do words -- if this 'do' is preceded
        # by one of 'for' 'while' 'until' do nothing
        # tokens ends with the token before the 'do' that triggered this
        check_for_rhtml = do_style == sci_constants.SCE_UDL_SSL_WORD
        for tok in reversed(tokens):
            (style, text, _) = tok.explode()
            if style in style_info._keyword_styles and text in self._loop_kwds:
                return True
            elif style in style_info._lineup_styles and text == ";":
                # Hit the end of a previous statement on one line
                return False
            elif (check_for_rhtml
                  and (style < sci_constants.SCE_UDL_SSL_DEFAULT
                       or style > sci_constants.SCE_UDL_SSL_VARIABLE)):
                return False
        return False

    def guessIndentation(self, scimoz, tabWidth, defaultUsesTabs):
        return self.guessIndentationByFoldLevels(scimoz, tabWidth, defaultUsesTabs, minIndentLevel=2)

    def _is_special_variable(self, scimoz, pos, opStyle):
        if pos == 0:
            return False;
        prevPos = scimoz.positionBefore(pos)
        if scimoz.getStyleAt(prevPos) == opStyle and chr(scimoz.getCharAt(prevPos)) == '$':
            # In Ruby $" and $` are special.
            return True
        return False

    def softchar_accept_matching_backquote(self, scimoz, pos, style_info, candidate):
        if self._is_special_variable(scimoz, pos,
                                     self.isUDL() and scimoz.SCE_UDL_SSL_VARIABLE or scimoz.SCE_RB_GLOBAL):
            return None
        return KoLanguageKeywordBase.softchar_accept_matching_backquote(self, scimoz, pos, style_info, candidate)

    def softchar_accept_matching_double_quote(self, scimoz, pos, style_info, candidate):
        """First verify that we aren't seeing $"
        """
        if self._is_special_variable(scimoz, pos,
                                     self.isUDL() and scimoz.SCE_UDL_SSL_VARIABLE or scimoz.SCE_RB_GLOBAL):
            return None
        return KoLanguageKeywordBase.softchar_accept_matching_double_quote(self, scimoz, pos, style_info, candidate)

    def _softchar_accept_match_outside_strings(self, scimoz, pos, style_info, candidate):
        """
        See KoLanguageKeywordBase._softchar_accept_match_outside_strings for docs
        """
        if pos == 0:
            return candidate
        prevPos = scimoz.positionBefore(pos)
        prevStyle = scimoz.getStyleAt(prevPos)
        if (prevStyle == scimoz.getStyleAt(pos) # we're in a string
            # Can't have a string immediately following a variable name without
            # an operator.
            or prevStyle in self.getVariableStyles()
            # Needed for embedded expressions, redundant for other languages.
            # Bug 79388: puts "... {2 + 2}<|>
            # Typing a single-quote at the cursor shouldn't generate a soft char.
            or prevStyle in style_info._indent_styles and scimoz.getWCharAt(prevPos) == "}"):
            return None
        return candidate
    
    def _getActualIndent(self, scimoz, lineNo, lineStart=None, currentPos=None):
        if lineStart is None:
            lineStart = scimoz.positionFromLine(lineNo)
        lineEnd = scimoz.getLineEndPosition(lineNo)
        line = scimoz.getTextRange(lineStart, lineEnd)
        ws = self.leading_ws_re.match(line).group(0)
        if currentPos and (currentPos - lineStart) < len(ws):
            ws2 = ws[0:(currentPos - lineStart)]
        else:
            ws2 = ws            
        return ws2

    # This not used yet, but hang on...
    def _getNormalizedIndentStr(self, scimoz, slen):
        if slen <= 0:
            return ""
        str1 = " " * slen
        if not scimoz.getUseTabs(): return str1
        tabLen = scimoz.GetTabWidth()
        if tabLen <= 0: return str1
        return str1.replace(' ' * tabLen, "\t")
        
    def _getFoldLevel(self, scimoz, line):
        # Adapted from koLanguageCommandHandler.py
        return scimoz.getFoldLevel(line) & scimoz.SC_FOLDLEVELNUMBERMASK
    
    # Override computeIndent
    def computeIndent(self, scimoz, indentStyle, continueComments):
        if continueComments:
            return KoLanguageKeywordBase.computeIndent(self, scimoz, indentStyle, continueComments)
        return self._computeIndent(scimoz, indentStyle, continueComments, self._style_info)

    def _computeIndent(self, scimoz, indentStyle, continueComments, style_info):
        # Don't rely on KoLanguageKeywordBase here.
        #super_indent = KoLanguageKeywordBase._computeIndent(self, scimoz, indentStyle, continueComments, style_info)
        #qlog.debug("super_indent: %r", super_indent)
        #if super_indent is not None:
        #    return super_indent
        if continueComments:
            #qlog.debug("continueComments: %r", continueComments)
            inBlockCommentIndent, inLineCommentIndent = self._inCommentIndent(scimoz, scimoz.currentPos, continueComments, style_info)
            if inLineCommentIndent is not None:
                return inLineCommentIndent
            elif inBlockCommentIndent is not None:
                return inBlockCommentIndent
        
        try:
            new_indent_string = self._calcIndentLevel(scimoz, scimoz.currentPos, style_info)
            #qlog.debug("new_indent_string: %r", new_indent_string)
            return new_indent_string
        except:
            log.warn("Got exception computing _calcIndentLevel", exc_info=1)
            return ''

    # This function works its way back through the buffer, to a max of
    # self._max_lines_in_calc(100) lines

    def _calcIndentLevel(self, scimoz, currentPos, style_info):
        # Check to see if we're on a continuation first
        # Use the language service base

        continuationLineIndent = self._continuationLineIndent(scimoz, currentPos)
        initialLine = curr_line = scimoz.lineFromPosition(currentPos)
        if continuationLineIndent is not None:
            lineEndPos = scimoz.getLineEndPosition(curr_line)
            log.debug("Ruby _calcIndentLevel detected continuation line[%d:%d->%d] indent of [%s](%d chars)" % (initialLine, currentPos, lineEndPos, continuationLineIndent, len(continuationLineIndent)))
            return continuationLineIndent

        minimumLine = max(initialLine - NUM_LINES_TO_ANALYZE, 0)
        lineStartPos = scimoz.positionFromLine(curr_line)
        tokens = self._get_line_tokens(scimoz, lineStartPos, currentPos, style_info, additional_ignorable_styles=style_info._default_styles)

        indent_delta = 0
        indent_amount = scimoz.indent
        if not indent_amount:
            indent_amount = 8
            
        keep_walking_back = True
        # Allows for moving up through continuation lines
        while keep_walking_back and curr_line >= 0:
            # Walk the tokens backwards
            idx = len(tokens) - 1
            # self._dump_tokens(tokens, indentlog)
            while idx >= 0:
                tok = tokens[idx]
                (style, text, tok_pos) = tok.explode()
                #indentlog.debug("tok %d: (pos %d, style %d, text [%s])", idx, tok_pos, style, text)
                # lineup-open is more important than others
                if style in style_info._lineup_styles:
                    if text in self._lineup_open_chars:
                        # Allow for keywords to the right of this spo, but an
                        # excess of 'end's doesn't make sense if we're lining up
                        # Add one to line up one to the right of the char.
                        if indent_delta < 0: indent_delta = 0
                        colPos = scimoz.getColumn(tok_pos) + 1 + indent_delta * indent_amount
                        # Check for end-of-line
                        if idx == len(tokens) - 1:
                            #indentlog.debug("this is the last token(%d)", idx)
                            lineEndPos = scimoz.getLineEndPosition(scimoz.lineFromPosition(tok_pos))
                            if tok_pos + len(text) == lineEndPos:
                                # Do a bracketing instead
                                bracketPos = self._getIndentWidthForLine(scimoz, curr_line) + indent_amount
                                if colPos > bracketPos:
                                    colPos = bracketPos
                        return scimozindent.makeIndentFromWidth(scimoz, colPos)
                    elif text in self._indent_open_chars:
                        indent_delta += 1
                    elif text in self._lineup_close_chars + self._indent_close_chars:
                        # Find the matched part and move back
                        (new_line, new_pos) = self._calcMatcher(scimoz, tok_pos)
                        if new_line is None:
                            # Base it on the indents on the current line
                            # We have an extra closer, so ignore it and keep going
                            log.debug("_calcIndentLevel: ignoring closer at (%d:%d) returned None" % (curr_line, tok_pos))
                            
                        elif new_line > curr_line:
                            log.debug("_calcIndentLevel: **** match(%d:%d) => greater line of (%d,%d)" % (curr_line, tok_pos, new_line, new_pos))
                            return self._getActualIndent(scimoz, curr_line, lineStartPos)
    
                        elif new_line < minimumLine:
                            # Can't look any further back, use the indent at this line.
                            #XXX Include delta's
                            return self._getActualIndent(scimoz, curr_line, lineStartPos)
                        # For the next two blocks,
                        # if the new position is at the start of the line,
                        # we're done
                        
                        elif new_line == curr_line:
                            # Sanity check
                            if new_pos > tok_pos:
                                log.debug("_calcIndentLevel: match(%d:%d) => same line, greater pos of (%d)" % (curr_line, tok_pos, new_pos))
                                return self._getActualIndent(scimoz, curr_line, lineStartPos)
                            # Move back until idx is < the matched char
                            new_idx = self._find_token(tokens, idx - 1, new_pos)
                            idx = new_idx
                            #log.debug("_calcIndentLevel: closer moved to idx %d, pos %d, line %d" % (idx, new_pos, curr_line))
                        else:
                            #log.debug("_calcIndentLevel: moved from (%d:%d) to (%d:%d) with %d deltas" % (curr_line, tok_pos, new_line, new_pos, indent_delta))
                            lineStartPos = scimoz.positionFromLine(new_line)
                            curr_line = new_line
                            if new_pos <= lineStartPos:
                                # We moved to the start of the line, so we're done
                                break
                            tokens = self._get_line_tokens(scimoz, lineStartPos, new_pos, style_info, additional_ignorable_styles=style_info._default_styles)
                            # self._dump_tokens(tokens)
                            idx = len(tokens) - 1
                            new_idx = self._find_token(tokens, idx, new_pos)
                            idx = new_idx
                            #log.debug("_calcIndentLevel: diff-line closer moved to idx %d, pos %d, line %d" % (idx, new_pos, curr_line))

                            # Get the tokens for a new line
                            # Leave indent_delta alone -- it's still in effect
                    else:
                        # It's another line-up, like a reg-ex thing
                        #XXX do something smarter later
                        pass
    
                elif style in style_info._keyword_styles:
                    this_delta = self._calc_keywords_change(tokens, idx, text, style_info)
                    if this_delta != 0:
                        log.debug("_calcIndentLevel: line %d: moving from del %d => %d on %s" % (curr_line, indent_delta, indent_delta + this_delta, text))
                    indent_delta += this_delta
                elif (style in style_info._multiline_styles
                      and idx == 0
                      and curr_line > 0
                      and (idx > 1 or not self._lineEndsWithStyle(scimoz, style, curr_line))
                      and self._lineEndsWithStyle(scimoz, style, curr_line - 1)):
                    # So we know we're in a string, or at its end, and the string doesn't
                    # bleed to the next line, and it did bleed from the previous.
                    
                    new_line, new_pos = self._findStartOfToken(scimoz, style, tok_pos)
                    # Check to see if the line ends with this style,
                    # and if it does use the indentation based at that line
                    if new_line is None or new_line >= curr_line:
                        log.debug("_calcIndentLevel: can't find start of token while at (%d:%d) => same line, greater pos of (%d)" % (curr_line, tok_pos, new_pos))
                        return self._getActualIndent(scimoz, curr_line, lineStartPos)
                    
                    #log.debug("_calcIndentLevel: string-moved from (%d:%d) to (%d:%d)" % (curr_line, tok_pos, new_line, new_pos))
                    lineStartPos = scimoz.positionFromLine(new_line)
                    curr_line = new_line
                    if new_pos <= lineStartPos:
                        # We moved to the start of the line, so we're done
                        #log.debug("_calcIndentLevel: string-moved to start of line")
                        break
                    tokens = self._get_line_tokens(scimoz, lineStartPos, new_pos, style_info, additional_ignorable_styles=style_info._default_styles)
                    # self._dump_tokens(tokens)
                    idx = len(tokens) - 1
                    new_idx = self._find_token(tokens, idx, new_pos)
                    idx = new_idx
                    #log.debug("_calcIndentLevel: string-moved to idx %d, pos %d, line %d" % (idx, new_pos, curr_line))
                else:
                    # Nothing interesting here
                    pass
                # end switching on the token's style
    
                idx -= 1
            # end inner while idx >= 0
            if (keep_walking_back and curr_line > 0 and
                self._is_continuation_line(scimoz, curr_line - 1, style_info)):
                curr_line -= 1
                lineStartPos = scimoz.positionFromLine(curr_line)
                currentPos = scimoz.getLineEndPosition(curr_line)
                tokens = self._get_line_tokens(scimoz, lineStartPos, currentPos, style_info, additional_ignorable_styles=style_info._default_styles)
            else:
                break
        # end outer while

        # Now calc something based on indent_delta and the
        # current indentation level in effect at whatever line
        # we ended up at.
        
        if indent_delta == 0:
            return self._getActualIndent(scimoz, curr_line, lineStartPos, currentPos)
        elif indent_delta > 0:
            new_indent_amount = self._getIndentWidthForLine(scimoz, curr_line) \
                                + indent_delta * indent_amount
            
            #log.debug("_calcIndentLevel: found %d deltas, setting indent to %d" % (indent_delta, new_indent_amount))
            return scimozindent.makeIndentFromWidth(scimoz, new_indent_amount)
        else:
            # This is the interesting one -- we have a bunch of 'end' keywords,
            # and we need to move up by fold levels to find the parent that matches
            #log.debug("_calcIndentLevel: found %d deltas, checking parents" % (indent_delta,))
            while indent_delta < 0:
                # parentLine = self._safeGetFoldParent(scimoz, curr_line)
                parentLine = scimoz.getFoldParent(curr_line)
                if parentLine is None or \
                   parentLine < minimumLine or \
                   parentLine >= curr_line:
                    #log.debug("_calcIndentLevel: parent(%d) => %s" % (curr_line, (parentLine and str(parentLine) or "<None>")))
                    break
                #log.debug("_calcIndentLevel: parent(%d) => %d" % (curr_line, parentLine))
                curr_line = parentLine
                indent_delta += 1
            istr = self._getActualIndent(scimoz, curr_line)
            #log.debug("_calcIndentLevel: indent(%d) => [%s](%d)" % (curr_line, istr, len(istr)))
            return istr
        # end if

    def _dump_tokens(self, tokens, log2=log):
        str2 = "tokens: \n"
        for tok in tokens:
            str2 += "[%d %s %d]" % (tok.explode())
        log2.debug(str2)
        
    def _lineEndsWithStyle(self, scimoz, style, curr_line):
        # This routine has a flaw:
        # If the string ends at the very end of the buffer, and we
        # press return, the EOL hasn't been styled yet, 
        endPos = scimoz.getLineEndPosition(curr_line)
        bufferSize = scimoz.length
        if endPos >= bufferSize:
            log.debug("_lineEndsWithStyle: endPos = %d, bufferSize = %d, end-style=%d, charNum=%d, setting..." % (endPos, bufferSize, style, scimoz.getCharAt(endPos)))
            endPos = bufferSize - 1
            
        endStyle = scimoz.getStyleAt(endPos)
        endCharNum = scimoz.getCharAt(endPos)
        log.debug("_lineEndsWithStyle: line %d, pos %d, charNum %d, style %d" % (curr_line, endPos, endCharNum, endStyle))
        return endStyle == style
    
    def _findStartOfToken(self, scimoz, style, pos):
        while pos > 0 and scimoz.getStyleAt(pos) == style:
            pos -= 1
        return scimoz.lineFromPosition(pos), pos
                    
    def _is_continuation_line(self, scimoz, line_no, style_info):
        eol_pos = scimoz.getLineEndPosition(line_no) - 1
        sol_pos = scimoz.positionFromLine(line_no)
        log.debug("_is_continuation_line(%d) over [%d:%d]" % (line_no, sol_pos, eol_pos))

        if eol_pos < sol_pos: # A true empty line?
            return False
        style = scimoz.getStyleAt(eol_pos)
        if style not in style_info._default_styles:
            return
        # What if it's a newline?
        chNum = scimoz.getCharAt(eol_pos)
        if chNum in [ORD_CR, ORD_NL]:
            log.debug("__is_continuation_line: have a newline")
            eol_pos -= 1
            if eol_pos < sol_pos:
                return False
            
        style = scimoz.getStyleAt(eol_pos)
        chNum = scimoz.getCharAt(eol_pos)
        log.debug("__is_continuation_line(%d) => ch(%d), style(%d)" % (line_no, chNum, style))
        if style in style_info._default_styles and chNum == ORD_BS:
            return True
        return False
    
    def _calcMatcher(self, scimoz, tok_pos):
        new_pos = scimoz.braceMatch(tok_pos)
        if new_pos is None or new_pos < 0 or new_pos >= tok_pos:
            # Contractual agreement (where's the contract?)
            return (None, None)
        new_line = scimoz.lineFromPosition(new_pos)
        return (new_line, new_pos)        
        
    def _calc_keywords_change(self, tokens, idx, curr_text, style_info):
        if curr_text in self._enders:
            return -1
        elif curr_text in self._sliders:
            # Assume these got pushed back, so we need to re-indent
            if idx == 0:
                return +1
            else:
                return 0
        elif curr_text in self._dedenters:
            #XXX Can we use fold info here?  Probably not.
            for tok in tokens[idx+1:]:
                if tok.style in style_info._modified_keyword_styles:
                    # Don't dedent if we *might* be modifying the line
                    return 0
            return -1
        elif curr_text in self._limited_openers:
            return +1
        elif curr_text in self._ending_openers:
            # Don't add an indent if this is a "noise" keyword
            if self._do_preceded_by_looper(tokens[:idx],
                                           tokens[idx].style, style_info):
                # We'll count the indent when we reach the 'looper'
                return 0
            return +1
        return 0

    # Find the opener that matches the closer, and set the token
    # pointer to point to it.
    # If we can't find it, point to the token with the smallest
    # position, or 0.
    # This routine knows that the returned index will be decremented
    # immediately.
    
    def _find_token(self, tokens, idx, target_pos):
        start_idx = idx
        while idx >= 0:
            this_pos = tokens[idx].start_pos
            if this_pos == target_pos:
                return idx
            elif this_pos < target_pos:
                break
            idx -= 1
        if idx == start_idx:
            return start_idx
        else:
            # Let the caller try the token we ended up on next iter
            return start_idx + 1

    def _handleEndDoHeader(self, ch, scimoz, style_info):
        """
        reinstate insertion of "end" on a matching line on the
        closing "|" after a do header (Bug 101194)
        A.method do | vars ... |

        If we're following `do |name {, name}*|`
        insert an end at the next line.

        Returns True if this routine makes an insertion.
        Returns False if it doesn't, expecting that the method will continue
        climbing up the inheritance tree requesting a more general method
        to process the keystroke.
        """
        currentPos = scimoz.currentPos
        currentLine = scimoz.lineFromPosition(currentPos)
        if currentPos < scimoz.length:
            # Make sure we're at the end of the line
            if currentLine == scimoz.lineCount - 1:
                lineEndPos = scimoz.length
            else:
                lineEndPos = scimoz.getLineEndPosition(currentLine)
            if currentPos < lineEndPos:
                trailingText = scimoz.getTextRange(currentPos, lineEndPos)
                if trailingText.strip():
                    return False
        lineStartPos = scimoz.positionFromLine(currentLine)
        tokens = self._get_line_tokens(scimoz, lineStartPos, currentPos,
                                       style_info,
                       additional_ignorable_styles=style_info._default_styles)
        if len(tokens) < 5:
            # We need at least the following tokens:
            # <methodName> "do" "|" <argumentName> "|"
            return False
        tokens.reverse()
        # Skip | name {, name}* |
        if tokens[0].text != "|":
            # Not a trailing |
            return False
        del tokens[0]
        while len(tokens) > 1:
            if tokens[0].style not in (scimoz.SCE_RB_IDENTIFIER,
                                       scimoz.SCE_UDL_SSL_IDENTIFIER):
                # No ident before , or |
                return False
            del tokens[0]
            if tokens[0].text != ",":
                break
            del tokens[0]
        if not tokens or tokens[0].text != "|":
            # No leading |
            return False
        del tokens[0]
        if (not tokens or tokens[0].text != "do"
                or tokens[0].style not in (scimoz.SCE_RB_WORD,
                                           scimoz.SCE_UDL_SSL_WORD)):
            # No 'do', we're in something else
            return False
        
        currIndent = self._getActualIndent(scimoz, currentLine, lineStartPos)
        currIndentWidth = len(currIndent.expandtabs())
        if currentLine < scimoz.lineCount - 1:
            nextLine = currentLine + 1
            nextLineText = scimoz.getLine(nextLine)[1]
            m = re.compile(r'(\s*)(\S*)').match(nextLineText)
            if m:
                nextIndentWidth = len(m.group(1).expandtabs())
                if nextIndentWidth > currIndentWidth:
                    # Subsequent line is already indented
                    return False
                if nextIndentWidth == currIndentWidth and m.group(2) == "end":
                    # Line with closing 'end' already in place
                    return False
            
        eol = eol2eolStr[scimozEOL2eol[scimoz.eOLMode]]
        lineToInsert = eol + currIndent + "end"
        scimoz.insertText(currentPos, lineToInsert)
        return True
    
    def _keyPressed(self, ch, scimoz, style_info):
        if self._handle_keypress and ch == '|' and self._handleEndDoHeader(ch, scimoz, style_info):
            return
        return KoLanguageKeywordBase._keyPressed(self, ch, scimoz, style_info)

class KoRubyCompileLinter:
    _com_interfaces_ = [components.interfaces.koILinter]
    _reg_desc_ = "Komodo Ruby Linter"
    _reg_clsid_ = "{9efff282-9919-4575-8c89-4a1e57512c97}"
    _reg_contractid_ = "@activestate.com/koLinter?language=Ruby;1"
    _reg_categories_ = [
         ("category-komodo-linter", 'Ruby'),
         ]

    def __init__(self):
        # From the Perl Linter
        self.sysUtils = components.classes["@activestate.com/koSysUtils;1"].\
            getService(components.interfaces.koISysUtils)
        self.infoSvc = components.classes["@activestate.com/koInfoService;1"].\
                       getService()
        self.rubyInfoEx = components.classes["@activestate.com/koAppInfoEx?app=Ruby;1"].\
                    getService(components.interfaces.koIAppInfoEx)

        self._lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"].\
            getService(components.interfaces.koILastErrorService)
        self._koVer = self.infoSvc.version

        self.warning_re = None
        # Delay compiling the Ruby RE's until we need them.
        self._word_letters = string.ascii_letters + string.digits + "_"

    def _define_res(self):
        self.warning_re = re.compile(r'^(?P<file>.*):(?P<line>\d+):\s*warning: (?P<message>.*)')
        self.error_re = re.compile(r'^(?P<file>.*):(?P<line>\d+):\s*(?P<message>.*)')
        self.caret_re = re.compile(r'^(\s*)\^')
        self.leading_res = {}
        self.trailing_res = {}
        for setup in [['w', r'\w*'], ['o', r'[^\w\s]*']]:
            self.leading_res[setup[0]] = re.compile('^(' + setup[1] + ')')
            self.trailing_res[setup[0]] = re.compile('(' + setup[1] + ')$')
        self.leading_res['s'] = re.compile(r'^(\s*\S?)')
        self.trailing_res['s'] = re.compile(r'(\S?\s*)$')
        
    def lint(self, request):
        text = request.content.encode(request.encoding.python_encoding_name)
        return self.lint_with_text(request, text)
        
    def lint_with_text(self, request, text):
        """Lint the given Ruby file.
        
        Raise an exception and set an error on koLastErrorService if there
        is a problem.
        """
        
        prefset = request.prefset
        cwd = request.cwd
        
        # Remove a possible "-d" in the shebang line, this will tell Ruby to
        # launch the debugger which.
        # Be careful to handle single-line files correctly.
        splitText = text.split("\n", 1)
        firstLine = self.RemoveDashDFromShebangLine(splitText[0])
        if len(splitText) > 1:
            text = "\n".join([firstLine, splitText[1]])
        else:
            text = firstLine

        
        #print "----------------------------"
        #print "Ruby Lint"
        #print text
        #print "----------------------------"
        # Save ruby buffer to a temporary file.
        tmpFileName = None
        if cwd:
            # Try to create the tempfile in the same directory as the ruby
            # file so that @INC additions using FindBin::$Bin work as
            # expected.
            # XXX Would really prefer to build tmpFileName from the name of
            #     the file being linted but the Linting system does not
            #     pass the file name through.
            tmpFileName = os.path.join(cwd, ".~ko-%s-rubylint~" % self._koVer)
            try:
                fout = open(tmpFileName, 'wb')
                fout.write(text)
                fout.close()
            except (OSError, IOError), ex:
                tmpFileName = None
        if not tmpFileName:
            # Fallback to using a tmp dir if cannot write in cwd.
            try:
                tmpFileName = str(tempfile.mktemp())
            except OSError, ex:
                # Sometimes get this error but don't know why:
                # OSError: [Errno 13] Permission denied: 'C:\\DOCUME~1\\trentm\\LOCALS~1\\Temp\\~1324-test'
                errmsg = "error determining temporary filename for "\
                         "Ruby content: %s" % ex
                self._lastErrorSvc.setLastError(3, errmsg)
                raise ServerException(nsError.NS_ERROR_UNEXPECTED)
            fout = open(tmpFileName, 'wb')
            fout.write(text)
            fout.close()

        lines = []
        try:
            rubyExe = self.rubyInfoEx.getExecutableFromDocument(request.koDoc)
            if not rubyExe:
                rubyExe = self.sysUtils.Which("ruby")
                if not rubyExe:
                    errmsg = "Could not find a suitable Ruby interpreter for linting."
                    self._lastErrorSvc.setLastError(1, errmsg)
                    raise ServerException(nsError.NS_ERROR_NOT_AVAILABLE)
            option = '-' + prefset.getStringPref("ruby_lintOption")
            # Note that ruby -c doesn't actually consult paths.  It doesn't
            # actually load required modules, since it doesn't need to process
            # them the way Perl does to determine how to interpret code after 'use'
            rubyExtraPaths = prefset.getStringPref("rubyExtraPaths")
            if rubyExtraPaths:
                if sys.platform.startswith("win"):
                    rubyExtraPaths = string.replace(rubyExtraPaths, '\\', '/')
                    rubyExtraPaths = [x for x in rubyExtraPaths.split(os.pathsep) if x.strip()]
                    rubyExtraPaths.insert(0, '.')
            else:
                rubyExtraPaths = ['.']
            argv = [rubyExe]
            for incpath in rubyExtraPaths:
                argv += ['-I', incpath]
            argv += [option, tmpFileName]
            cwd = cwd or None # convert '' to None (cwd=='' for new files)
            env = koprocessutils.getUserEnv()
            p = process.ProcessOpen(argv, cwd=cwd, env=env, stdin=None)
            stdout, stderr = p.communicate()
            lines = stderr.splitlines(1)
        finally:
            try:
                os.unlink(tmpFileName)
            except:
                log.warn("Got exception trying to delete temp file %s", tmpFileName, exc_info=1)
                pass
        
        results = koLintResults()
        try:
            results = self._parseRubyResults(results, lines, tmpFileName, text)
        except:
            errmsg = "Exception in Ruby linting while parsing results"
            self._lastErrorSvc.setLastError(1, errmsg)
            log.exception(errmsg)
        #print "----------------------------"
        return results

# ruby error line format
# Errors:
# filename:lineNo: <message>
# source-code-text
#      ^ at start of problem in text, usually start of a token
#        So find the token, and squiggle it
#
# Warnings:
# filename:line_no: warning: <message>

    def _add_if_new(self, results, result, reported, err_hash):
        k = "%s:%s" % (err_hash['file'], err_hash['line'])
        if not reported.has_key(k):
            results.addResult(result)
            reported[k] = None
        

    def _parseRubyResults(self, results, lines, tmpFileName, text):
        # caller does this: results = koLintResults()
        # So that if an exception is thrown the caller will
        # get a good default value.
        
        if not lines or len(lines) == 0:
            return results
        if not self.warning_re:
            self._define_res()
        datalines = re.split('\r\n|\r|\n', text)
        reported = {}
        i = 0
        numLines = len(lines)
        while i < numLines:
            line = lines[i]
            #print line
            ge = gw = None
            gw = self.warning_re.match(line)
            if gw:
                err = gw.groupdict()
            else:
                ge = self.error_re.match(line)
                if not ge:
                    log.debug("Couldn't match an error or warning with line %d:<%s>", i, line)
                    i = i + 1
                    continue
                err = ge.groupdict()
            
            # Common stuff here
            # Assume there is no caret
            result = KoLintResult()
            result.lineStart = result.lineEnd = int(err['line'])
            result.columnStart = 1
            result.columnEnd = len(datalines[result.lineEnd-1]) + 1
            result.description = err['message']

            if gw:
                result.severity = result.SEV_WARNING
                self._add_if_new(results, result, reported, err)
                i = i + 1
                continue
            
            result.severity = result.SEV_ERROR

            # See if the next line contains next or something
            if i < numLines - 2:
                caret_match = self.caret_re.match(lines[i + 2])
                if not caret_match:
                    i = i + 1
                    continue
                try:
                    caret_posn = len(caret_match.group(0))
                    if caret_posn > 0: caret_posn -= 1
                    fpart, rest = lines[i + 1][:caret_posn], lines[i + 1][caret_posn + 1:]
                    caret_char = lines[i + 1][caret_posn]
                    if caret_char in " \t":
                        re_key = 's'
                    elif caret_char in self._word_letters:
                        re_key = 'w'
                    else:
                        re_key = 'o'
                    
                    # white-space: just span white-space, and next
                    # Span to the surrounding non-white-space chars
                    ws_left_len = len(self.trailing_res[re_key].search(fpart).group(0))
                    ws_right_len = len(self.leading_res[re_key].search(rest).group(0))
                    col_left = caret_posn - ws_left_len
                    col_right = caret_posn + ws_right_len
                    if col_left < 0: col_left = 0
                    result.columnStart = col_left + 1
                    result.columnEnd = col_right + 1
                except:
                    log.warn("Got exception computing _parseRubyResults", exc_info=1)
                i += 3
            else:
                i += 1
            self._add_if_new(results, result, reported, err)
                    
        return results

    def RemoveDashDFromShebangLine(self, line):
        """Remove a possible -d ruby option from the given shebang line.
        Return the resultant string.
    
        Note that this is probably not going to handle esoteric uses of quoting
        and escaping on the shebang line.
    
            >>> from KoRubyLanguage import RemoveDashDFromShebangLine as rd
            >>> rd("foo")
            'foo'
            >>> rd("#!ruby -d")
            '#!ruby '
            >>> rd("#!ruby -d:foo")
            '#!ruby '
            >>> rd("#!ruby -cd")
            '#!ruby -c'
            >>> rd("#!ruby -0")
            '#!ruby -0'
            >>> rd("#!ruby -01d")
            '#!ruby -01'
            >>> rd("#!ruby -Mmymodule")
            '#!ruby -Mmymodule'
            >>> rd("#!ruby -dMmymodule")
            '#!ruby -Mmymodule'
            >>> rd("#!ruby -Vd")
            '#!ruby -V'
            >>> rd("#!ruby -V:d")
            '#!ruby -V:d'
            >>> rd("#!/bin/sh -- # -*- ruby -*- -p")
            '#!/bin/sh -- # -*- ruby -*- -p'
            >>> rd("#!/bin/sh -- # -*- ruby -*- -pd")
            '#!/bin/sh -- # -*- ruby -*- -p'
        """
        # ensure this is a shebang line
        if not line.startswith("#!"):
            return line
    
        # The Ruby command-line options are so much like Perl's
        # that we can probably get away with barebones.
        result = ""
        remainder = line
        # parsing only begins from where "ruby" is first mentioned
        splitter = re.compile("(ruby)", re.I)
        try:
            before, ruby, after = re.split(splitter, remainder, 1)
        except ValueError:
            # there was no "ruby" in shebang line
            return line
        else:
            result += before + ruby
            remainder = after
    
        # the remainder are ruby arguments
        tokens = re.split("(-\*|- |\s+)", remainder)
        while len(tokens) > 0:
            token = tokens[0]
            if token == "":
                tokens = tokens[1:]
            elif token in ("-*", "- "):
                # "-*" and "- " are ignored for Emacs-style mode lines
                result += token
                tokens = tokens[1:]
            elif re.match("^\s+$", token):
                # skip whitespace
                result += token
                tokens = tokens[1:]
            elif token == "--":
                # option processing stops at "--"
                result += "".join(tokens)
                tokens = []
            elif token.startswith("-"):
                # parse an option group
                # See "ruby -h". Those options with arguments (some of them
                # optional) must have 'd' in those arguments preserved.
                stripped = "-"
                token = token[1:]
                while len(token) > 0: 
                    ch = token[0]
                    if ch in ('0', 'l'):
                        # -0[octal]
                        # -l[octal]
                        stripped += ch
                        token = token[1:]
                        while len(token) > 0:
                            ch = token[0]
                            if ch in "01234567":
                                stripped += ch
                                token = token[1:]
                            else:
                                break
                    elif ch == 'd':
                        # -d[:debugger]
                        if len(token) > 1 and token[1] == ":":
                            # drop the "d:foo"
                            token = ""
                        else:
                            # drop the 'd'
                            token = token[1:]
                    elif ch in ('D', 'F', 'i', 'I', 'm', 'M', 'x'):
                        # -D[number/list]
                        # -F/pattern/
                        # -i[extension]
                        # -Idirectory
                        # -[mM][-]module
                        # -x[directory]
                        stripped += token
                        token = ""
                    elif ch == 'V':
                        # -V[:variable]
                        if len(token) > 1 and token[1] == ":":
                            stripped += token
                            token = ""
                        else:
                            stripped += ch
                            token = token[1:]
                    else:
                        stripped += ch
                        token = token[1:]
                if stripped != "-":
                    result += stripped
                tokens = tokens[1:]
            else:
                # this is a non-option group token, skip it
                result += token
                tokens = tokens[1:]
        remainder = ""
    
        return result
