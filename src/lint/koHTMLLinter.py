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


from xpcom import components, ServerException
from xpcom.server import UnwrapObject
from koLintResult import KoLintResult
from koLintResults import koLintResults
from xpcom.server.enumerator import *
import os, sys, re
import StringIO  # Do not use cStringIO!  See html5 class for an explanation

from zope.cachedescriptors.property import LazyClassAttribute

import eollib
import html5lib
from html5lib.constants import E as html5libErrorDict
import process

import logging
logging.basicConfig()
log = logging.getLogger("KoHTMLLinter")
#log.setLevel(logging.DEBUG)

_doctype_re = re.compile("<!doctype\s+html\s*?(.*?)\s*>", re.IGNORECASE|re.DOTALL)

class MultiLangStringBuilder(dict):
    """
    The HTML linter takes in its document's text, and then writes out subsets
    of that text destined for each separate language's linter.  It also sometimes
    needs to wrap snippets, usually with either a function definition wrapper or
    a CSS declaration, and that causes the <line,column> coordinates of some of the text
    the linter sees to deviate from the text the user sees.  This class pushes
    the injected text into the pending white space, when possible.
    """
    def __init__(self, names):
        dict.__init__(self, dict([(k, []) for k in names]))
        self._pendingWhiteSpace = dict([(k, '') for k in names])
        
    def addWhiteSpace(self, name, s):
        self._pendingWhiteSpace[name] += s
        
    def _pushBlanks(self, name):
        if self._pendingWhiteSpace[name]:
            self[name].append(self._pendingWhiteSpace[name])
        self._pendingWhiteSpace[name] = ''
        
    def __setitem__(self, name, s):
        self._pushBlanks(name)
        self[name].append(s)
        
    def finish(self):
        for name in self.keys():
            self._pushBlanks(name)
    
    def last_text_matches_pattern(self, name, ptn):
        if not self[name]:
            # If there is no text at all, count as True
            return True
        for s in self[name][-1 : -len(self[name]) - 1: -1]:
            s1 = s.rstrip()
            if not s1:
                # Ignore sequences with white-space only
                continue
            if ptn.search(s1):
                return True
            return False
    
    def replace_ending_white_space(self, name, newStr, lineNum):
        if not newStr:
            return
        numChars = len(newStr)
        ending_spaces_re = re.compile(r'[ \t]{1,%d}\Z' % numChars)
        m = ending_spaces_re.search(self._pendingWhiteSpace[name])
        if m:
            mglen = len(m.group())
            if mglen >= numChars:
                self[name].append(self._pendingWhiteSpace[name][:-numChars])
            else:
                self[name].append(self._pendingWhiteSpace[name][:-mglen])
            # Manually push everything to the 
            self._pendingWhiteSpace[name] = ''
            self[name].append(newStr)
        else:
            # Make sure the non-white item is preceded by start or a space.
            if self[name] and not self._pendingWhiteSpace[name] and not self[name][-1].isspace():
                self._pendingWhiteSpace[name] += ' '
            self[name] = newStr
            
#---- component implementation

class _CommonHTMLLinter(object):
    _com_interfaces_ = [components.interfaces.koILinter]
    
    def __init__(self):
        self._koLintService = components.classes["@activestate.com/koLintService;1"].getService(components.interfaces.koILintService)
        self._lintersByLangName = {
            "CSS": self._koLintService.getLinterForLanguage("CSS"),
            "JavaScript": self._koLintService.getLinterForLanguage("JavaScript"),
            }
     
    _nonNewlineMatcher = re.compile(r'[^\r\n]')
    def _spaceOutNonNewlines(self, markup):
        return self._nonNewlineMatcher.sub(' ', markup)
        
    def _linterByName(self, langName, currentLinters):
        if langName in currentLinters:
            return currentLinters[langName]
        if langName not in self._lintersByLangName:
            try:
                linter = self._koLintService.getLinterForLanguage(langName)
                self._lintersByLangName[langName] = linter
            except:
                log.error("No linter for language %s", langName)
                linter = None
            self._lintersByLangName[langName] = linter
            currentLinters[langName] = linter
        return self._lintersByLangName[langName]

    def _getMappedName(self, name):
        return self._mappedNames and self._mappedNames.get(name, name) or name

    def _blankOutOneLiners(self, code):
        if "\n" in code.strip():
            return code
        return self._spaceOutNonNewlines(code)

    def addLineNumbers(self, s, currLineNum):
        lines = s.splitlines(True)
        nums = range(0, len(lines))
        return "".join(["%4d:%s" % (num + currLineNum, line) for num, line in zip(nums, lines)])

    def _trim(self, s):
        if len(s) <= 500:
            return s
        return s[:100] + "..." + s[-100:]
    
    def _getLastMarkupText(self, koDoc, transitionPoints, i, textAsBytes):
        """
        Return the most recent chunk of markup text
        """
        startPt = transitionPoints[i]
        i -= 1
        while i >= 0:
            endPt = startPt
            startPt = transitionPoints[i]
            if startPt == endPt:
                continue
            origLangName = koDoc.languageForPosition(startPt)
            if origLangName in ('HTML', 'HTML5', 'XUL', 'XBL'):
                currText = textAsBytes[startPt:endPt]
                return currText
            i -= 1
        return "" # Give up.

    @LazyClassAttribute
    def _ends_with_cdata_re(self):
        return re.compile(r'(?:\s*\]\]>|\s*-->)+\s*\Z', re.DOTALL)

    @LazyClassAttribute
    def _ends_with_gt(self):
        return re.compile(r'>\s*\Z');

    @LazyClassAttribute
    def _ends_with_quote_re(self):
        return re.compile(r'[\"\']\Z');

    @LazyClassAttribute
    def _ends_with_zero(self):
        return re.compile(r'0\s*\Z', re.DOTALL)

    @LazyClassAttribute
    def _event_re(self):
        return re.compile(r'\bevent\b')

    @LazyClassAttribute
    def _function_re(self):
        return re.compile(r'\bfunction\b')

    @LazyClassAttribute
    def _js_code_end_re(self):
        return re.compile(r'[\};]\s*$', re.DOTALL)

    @LazyClassAttribute
    def _nl_re(self):
        return re.compile('\\n')

    @LazyClassAttribute
    def _return_re(self):
        return re.compile(r'\breturn\b')

    @LazyClassAttribute
    def _script_start_re(self):
        return re.compile(r'<script[^>]*>\s*\Z', re.DOTALL)

    @LazyClassAttribute
    def _starts_with_cdata_re(self):
        return re.compile(r'(?:\s*<!\[CDATA\[|\s*<!--)+\s*', re.DOTALL)

    @LazyClassAttribute
    def _xbl_field_tag_re(self):
        return re.compile(r'<(?:\w+:)?field[^>]*>\s*\Z', re.DOTALL)

    @LazyClassAttribute
    def _xbl_handler_re(self):
        return re.compile(r'<(?:\w+:)?handler[^>]*>\s*\Z', re.DOTALL)

    @LazyClassAttribute
    def _xbl_method_re(self):
        return re.compile(r'<(?:\w+:)?method\b.*?<body[^>]*>\s*\Z', re.DOTALL)

    @LazyClassAttribute
    def _xbl_method_name_re(self):
        return re.compile(r'<(?:\w+:)?method\b.*?name\s*=\s*[\'\"](\w+)', re.DOTALL)

    @LazyClassAttribute
    def _xbl_method_parameter_re(self):
        return re.compile(r'<(?:\w+:)?parameter\b.*?name\s*=\s*[\'\"](\w+)[\'\"].*?>', re.DOTALL)

    @LazyClassAttribute
    def _xbl_setter_re(self):
        return re.compile(r'<(?:\w+:)?setter[^>]*>\s*\Z', re.DOTALL)

    @LazyClassAttribute
    def _xml_decln_re(self):
        return re.compile(r'(<)<\?\?>(\?.*)', re.DOTALL)
    
    # Matching state values.  Tracking when we're in CSS or JS, and when we're in SSL code.
    _IN_M = 0x0001
    _IN_JS_SCRIPT = 0x0002
    _IN_JS_FUNCTION_DEF = 0x0004
    _IN_JS_FUNCTION_DEF_INVOCN = 0x0008
    _IN_JS_OTHER = 0x0010
    _IN_JS_SQUELCH = 0x0020
    _IN_JS_EMIT = _IN_JS_SCRIPT|_IN_JS_FUNCTION_DEF|_IN_JS_FUNCTION_DEF_INVOCN|_IN_JS_OTHER
    _IN_JS = _IN_JS_EMIT|_IN_JS_SQUELCH

    _IN_CSS_STYLE = 0x0040
    _IN_CSS_ATTR = 0x0080
    _IN_CSS_SQUELCH = 0x0100
    _IN_CSS_EMIT = _IN_CSS_STYLE|_IN_CSS_ATTR
    _IN_CSS = _IN_CSS_EMIT|_IN_CSS_ATTR
    
    _IN_SSL_EMITTER = 0x0200
    _IN_SSL_BLOCK = 0x0400
    _IN_SSL = _IN_SSL_EMITTER|_IN_SSL_BLOCK

    _take_all_languages = ("PHP",)
    # Hand these SSL languages the whole document
    # Are there others beside PHP?
    
    # This pattern is for bug 95364, support Rails-hack form of ERB to
    # support forms like <%= form_tag ... do |f| %>...<% end %>
    # Note mismatched <%= ... %><% %> -- this is deliberate in Rails 3
    @LazyClassAttribute
    def RERB_Block_PTN(self):
        return re.compile(r'.*?\s*(?:do|\{)(?:\s*\|[^|]*\|)?\s*\Z')
    def _lint_common_html_request(self, request, udlMapping=None, linters=None,
                                  TPLInfo=None,
                                  startCheck=None):
        """
        Hand off bits of text to each lexer.
        @param udlMapping:
        Example: udlMapping={"Perl":"Mason"} -- used for mapping SSL code to the actual multi-lang language
        
        @param startCheck:
        Some languages need to insert a doctype.  If there's a startCheck, it contains
        a language, a pattern, and text to insert if the pattern fails to match
        
        @param TPLInfo  (languageName, emitPattern)
        If we're matching language <languageName> and we match <emitPattern>, it means
        that an SSL language will be inserting some text into the eventual HTML document.
        If this follows CSS or JS, we need to insert some text to keep the respective
        CSS/JS linter happy.
        
        The markup lexer (HTML/HTML5/XML) sees all the core text: markup, CSS, JS
        
        PHP is handled off everything
        
        All other languages see only their own language.
        
        There are tricks for wrapping bits of JS and CSS, see below.
        
        Start in state _IN_M
        
        The JS lexer gets text between script tags passed as is.  But then there
        are other wrinkles:
        M -> JS after: /on\w+\s*=\s*["']/ ::
             If the terms 'return' and 'event' aren't used here, insert a ';' if needed
             Otherwise, insert 'function _kof##() {';, => _IN_JS_FUNCTION_DEF
             and add an 'event' arg.
        M -> JS after: /<field.*?>\s*/       :: => _IN_JS_SQUELCH
        M -> JS after: /<script.*?>\s*/       :: blank <![CDATA[, => _IN_JS_SCRIPT
        M -> JS after: />\s*/       :: insert 'function _kof##() {';  blank <![CDATA[ -- Assume not a script tag, => _IN_JS_FUNCTION_DEF_INVOCN
        M -> JS after: other:  , => _IN_JS_SQUELCH
        M -> CSS after: />\s*/ :: nothing, => _IN_CSS_STYLE
        M -> CSS after: ["'] :: insert  '_x {', => _IN_CSS_ATTR
        M -> CSS after: other:  => _IN_CSS_SQUELCH
        
        land at M, currState & _IN_JS:
            blank  /]]>\s*/
            _IN_JS_SQUELCH: emit nothing
            _IN_JS_SCRIPT: emit nothing
            _IN_JS_FUNCTION_DEF: emit '}'
        land at M, currState & _IN_CSS:
            _IN_CSS_STYLE: emit nothing
            _IN_CSS_ATTR: emit '}'
            
        (currState & _IN_JS_EMIT|_IN_CSS_EMIT) on TPL_EMITTER_START:
            insert '0' (number, not a string)'
            add state _IN_SSL_EMITTER
        
        find TPL_BLOCK_START => _IN_SSL_BLOCK
        SSL code emitted to SSL lang _IN_SSL_BLOCK
        find TPL_EMITTER_START => _IN_SSL_EMITTER
        SSL code not emitted to SSL lang when _IN_SSL_EMITTER is on
        
        find TPL_END => drop _IN_SSL
        
        Two points about this state machine:
        1. SSL_EMITTERS start with patterns like /<\?=/ or /<\?php\s+echo\b/.  They emit
           a value that the browser will see.  SSL_BLOCK doesn't emit code, so it all gets squelched.
        2. States will overlap across families.  For example, we can have JS_SQUELCH and SSL_BLOCK at the same time
        3. Whenever we end up in markup, we can end whatever is pending, and clear all
           overlapped states, ending at _IN_M
        """
        
        
        self._mappedNames = udlMapping
        # These are lines where we added text.  If the linter complains about
        # any of these lines, make sure the error message spans the entire line.
        self._emittedCodeLineNumbers = set()
        # These refer to lines where the SSL and JS and/or CSS are interleaved,
        # which could lead to possible false-positives.  Just don't report JS/CSS
        # errors/warnings on these lines.
        self._multiLanguageLineNumbers = set()
        lintersByName = {}
        # Copy working set of linters into a local var
        lintersByName.update(self._lintersByLangName)
        if linters:
            lintersByName.update(linters)
        koDoc = request.koDoc  # koDoc is a proxied object
        koDoc_language = koDoc.language
        transitionPoints = koDoc.getLanguageTransitionPoints(0, koDoc.bufferLength)
        languageNamesAtTransitionPoints = [koDoc.languageForPosition(pt)
                                           for pt in transitionPoints[:-2]]
        if not languageNamesAtTransitionPoints:
            languageNamesAtTransitionPoints = [koDoc.languageForPosition(0)]
        # We need to lint the utf-8 representation to keep coordinates
        # in sync with Scintilla
        # request.content contains a Unicode representation, even if the
        # buffer's encoding is utf-8 -- content is an AString
        textAsBytes = request.content.encode("utf-8")
        uniqueLanguageNames = dict([(k, None) for k in languageNamesAtTransitionPoints])
        if udlMapping:
            for targetName in udlMapping.values():
                try:
                    uniqueLanguageNames[targetName] = []
                except TypeError:
                    log.debug("udlMapping:%s, targetName:%r", udlMapping, targetName)
        uniqueLanguageNames = uniqueLanguageNames.keys()
        #log.debug("transitionPoints:%s", transitionPoints)
        #log.debug("uniqueLanguageNames:%s", uniqueLanguageNames)
        ###bytesByLang =OLD### dict([(k, []) for k in uniqueLanguageNames])
        bytesByLang = MultiLangStringBuilder(uniqueLanguageNames)
        lim = len(transitionPoints)
        endPt = 0
        htmlAllowedNames = ("HTML", "HTML5", "CSS", "JavaScript", "XML")
        currState = self._IN_M
        prevText = ""
        prevLanguageFamily = "M"
        currLineNum = 1
        js_func_num = 0
        js_func_name_prefix = "__kof_"
        for i in range(1, lim):
            startPt = endPt
            endPt = transitionPoints[i]
            if startPt == endPt:
                continue
            currText = textAsBytes[startPt:endPt]
            numNewLinesInCurrText = len(self._nl_re.findall(currText))
            origLangName = koDoc.languageForPosition(startPt)
            langName = self._getMappedName(origLangName)
            #log.debug("segment: raw lang name: %s, lang:%s, %d:%d [[%s]]",
            #          koDoc.languageForPosition(startPt),
            #          langName, startPt, endPt, self.addLineNumbers(currText, currLineNum))
            if TPLInfo and origLangName == TPLInfo[0]:
                for j in range(currLineNum, currLineNum + numNewLinesInCurrText + 1):
                    self._multiLanguageLineNumbers.add(j)
            squelchedText = self._spaceOutNonNewlines(currText)
            for name in bytesByLang.keys():
                if origLangName == "CSS" and langName == name:
                    if currState & self._IN_CSS:
                        # We're in a run of CSS, could be separated by SSL blocks
                        pass
                    else:
                        
                        if prevLanguageFamily != "M":
                            # Handle the case of <style><?php...?><?php ... ?>foo { ... }
                            prevText = self._getLastMarkupText(koDoc, transitionPoints, i, textAsBytes)
                            prevWasMarkup = False
                        else:
                            prevWasMarkup = True
                        if self._ends_with_quote_re.search(prevText):
                            bytesByLang.replace_ending_white_space(name, "_x{", currLineNum)
                            self._emittedCodeLineNumbers.add(currLineNum)
                            currState |= self._IN_CSS_ATTR
                            
                        elif self._ends_with_gt.search(prevText):
                            currState |= self._IN_CSS_STYLE
                        elif prevWasMarkup:
                            log.debug("Hit weird block of CSS <<<\n%r\n>>> preceded by HTML <<<\n%r>>>", self._trim(currText), self._trim(prevText))
                            currState |= self._IN_CSS_SQUELCH
                        m = self._starts_with_cdata_re.match(currText)
                        if m:
                            bytesByLang.addWhiteSpace(name, self._spaceOutNonNewlines(m.group()))
                            currText = currText[m.end():]
                    if currState & self._IN_CSS_SQUELCH:
                        bytesByLang.addWhiteSpace(name, self._spaceOutNonNewlines(currText))
                    else:
                        m = self._ends_with_cdata_re.search(currText)
                        if m:
                            bytesByLang[name] = currText[:m.start()]
                            bytesByLang.addWhiteSpace(name, self._spaceOutNonNewlines(m.group()))
                        else:
                            bytesByLang[name] = currText
                    prevLanguageFamily = "CSS"
                elif origLangName == "JavaScript" and langName == name:
                    if currState & self._IN_JS:
                        # We're in a run of JS, could be separated by SSL blocks
                        pass
                    else:
                        if prevLanguageFamily != "M":
                            # Handle the case of <script><?php...?><?php ... ?>foo { ... }
                            prevText = self._getLastMarkupText(koDoc, transitionPoints, i, textAsBytes)
                        if self._ends_with_quote_re.search(prevText):
                            # onfoo="..." -- function __kof_###() { ... }
                            if (self._return_re.search(currText)
                                or self._event_re.search(currText)):
                                if self._event_re.search(currText):
                                    args = "event"
                                else:
                                    args = ""
                                js_func_num += 1
                                bytesByLang.replace_ending_white_space(name, "function %s%d(%s) {" % (js_func_name_prefix, js_func_num, args), currLineNum)
                                self._emittedCodeLineNumbers.add(currLineNum)
                                currState |= self._IN_JS_FUNCTION_DEF
                            else:
                                if not bytesByLang.last_text_matches_pattern(name, self._js_code_end_re):
                                    bytesByLang.replace_ending_white_space(name, ';', currLineNum);
                                    self._emittedCodeLineNumbers.add(currLineNum)
                                # Don't wrap the code, because it doesn't need to look like a function
                                currState |= self._IN_JS_SCRIPT
                        elif self._script_start_re.search(prevText):
                            currState |= self._IN_JS_SCRIPT
                        elif koDoc_language == "XBL" and self._xbl_field_tag_re.search(prevText):
                            # too many jslint false positives, so squelch
                            currState |= self._IN_JS_SQUELCH
                        elif koDoc_language == "XBL" and self._xbl_setter_re.search(prevText):
                            # XBL setter elements have an implicit argument called 'val'
                            js_func_num += 1;
                            bytesByLang.replace_ending_white_space(name, "function %s%d(val) {" % (js_func_name_prefix, js_func_num), currLineNum)
                            self._emittedCodeLineNumbers.add(currLineNum)
                            currState |= self._IN_JS_FUNCTION_DEF
                        elif koDoc_language == "XBL" and self._xbl_handler_re.search(prevText):
                            # XBL setter elements have an implicit argument called 'val'
                            js_func_num += 1;
                            bytesByLang.replace_ending_white_space(name, "function %s%d(event) {" % (js_func_name_prefix, js_func_num), currLineNum)
                            self._emittedCodeLineNumbers.add(currLineNum)
                            currState |= self._IN_JS_FUNCTION_DEF
                        elif koDoc_language == "XBL" and self._xbl_method_re.search(prevText):
                            # XBL method elements define arguments in parameter elements
                            t1 = self._xbl_method_re.search(prevText).group()
                            method_name = self._xbl_method_name_re.search(t1)
                            if method_name:
                                func_name = method_name.group(1)
                            else:
                                func_name = "%s%d" % (js_func_name_prefix, js_func_num)
                                js_func_num += 1;
                            names = self._xbl_method_parameter_re.findall(t1)
                            bytesByLang.replace_ending_white_space(name, "function %s(%s) {" % (func_name, ", ".join(names)), currLineNum)
                            self._emittedCodeLineNumbers.add(currLineNum)
                            currState |= self._IN_JS_FUNCTION_DEF
                        elif self._ends_with_gt.search(prevText):
                            # Probably XBL JS elements of some kind
                            js_func_num += 1;
                            bytesByLang.replace_ending_white_space(name, "function %s%d() {" % (js_func_name_prefix, js_func_num), currLineNum)
                            self._emittedCodeLineNumbers.add(currLineNum)
                            currState |= self._IN_JS_FUNCTION_DEF
                        else:
                            log.debug("Hit weird block of JS (%s) starting with HTML %s", self._trim(currText), self._trim(prevText))
                            currState |= self._IN_JS_SQUELCH
                        m = self._starts_with_cdata_re.match(currText)
                        if m:
                            bytesByLang.addWhiteSpace(name, self._spaceOutNonNewlines(m.group()))
                            currText = currText[m.end():]
                    if currState & self._IN_JS_SQUELCH:
                        bytesByLang.addWhiteSpace(name, self._spaceOutNonNewlines(currText))
                    else:
                        m = self._ends_with_cdata_re.search(currText)
                        if m:
                            bytesByLang[name] = currText[:m.start()]
                            bytesByLang.addWhiteSpace(name, self._spaceOutNonNewlines(m.group()))
                        else:
                            bytesByLang[name] = currText
                    prevLanguageFamily = "CSL"
                elif name in ('HTML', 'HTML5', 'XML', 'XUL', 'XBL', 'XSLT'):
                    if name == langName:
                        if currState & ~self._IN_M:
                            self._closeOpenBlocks(currState, bytesByLang, currLineNum)
                            currState = self._IN_M
                        if TPLInfo:
                            m = self._xml_decln_re.match(currText)
                            if m:
                                # Hide the special escape for XML declarations in PHP files
                                bytesByLang[name] = m.group(1) + m.group(2)
                                self._emittedCodeLineNumbers.add(currLineNum)
                            else:
                                bytesByLang[name] = currText
                        else:
                            bytesByLang[name] = currText
                        prevLanguageFamily = "M"
                    elif langName == "CSS"  or langName == "JavaScript":
                        # Keep these
                        bytesByLang[name] = currText
                    else:
                        bytesByLang.addWhiteSpace(name, squelchedText)
                elif name == langName:
                    currState = self._closeOpenBlocks(currState, bytesByLang, currLineNum)
                    # It's either TPL or SSL.  TPL has transitions, SSL would be pieces of SSL code
                    # surrounded by TPL bits.
                    if TPLInfo and name == langName and origLangName == TPLInfo[0]:
                        # So here we're either going to start squelching or not
                        # Also if the prev state is JS or CSS and this is an emitter, we
                        # need to emit a 0
                        # Watch out for <style> foo { a:<?php if 1 ?><?php echo x ?>... }
                        if TPLInfo[1].match(currText):
                            currState |= self._IN_SSL_EMITTER
                        else:
                            currState |= self._IN_SSL_BLOCK
                    if ((currState & self._IN_SSL_EMITTER)
                        and (currState & (self._IN_CSS_EMIT|self._IN_JS_EMIT))):
                        # Give the JS/CSS processor something to work with
                        if currState & self._IN_CSS_EMIT:
                            checkLangName = "CSS"
                        else:
                            checkLangName = "JavaScript"
                        if not bytesByLang.last_text_matches_pattern(checkLangName, self._ends_with_zero):
                            # Avoid duplicates for multiple subsequent SSL emitters.
                            bytesByLang.replace_ending_white_space(checkLangName, "0", currLineNum)
                            self._emittedCodeLineNumbers.add(currLineNum)
                            self._multiLanguageLineNumbers.add(currLineNum)
                                
                    if ((currState & self._IN_SSL_EMITTER)
                        and name not in self._take_all_languages
                        and ((not TPLInfo) or origLangName != TPLInfo[0])):
                        if TPLInfo and len(TPLInfo) >= 5:
                            thisText = TPLInfo[3] + currText + TPLInfo[4]
                            if (len(TPLInfo) >= 6
                                and TPLInfo[5].get("supportRERB", None)
                                and self.RERB_Block_PTN.match(currText)):
                                # Do not wrap the first part!
                                # Treat as a Rails <% ... %> control-block,  not an emitter
                                # like <% form_tag ... do|f| %>
                                thisText = currText
                            bytesByLang[name] = thisText
                        else:
                            bytesByLang.addWhiteSpace(name, squelchedText)
                    else:
                        bytesByLang[name] = currText
                    prevLanguageFamily = "SSL"
                elif (currState & self._IN_SSL_EMITTER
                      and ((name == "CSS" and (currState & self._IN_CSS_EMIT))
                           or (name == "JavaScript" and (currState & self._IN_JS_EMIT)))
                      and currText.find("\n") == -1):
                    # Emit nothing, including white space
                    pass
                elif TPLInfo and name == TPLInfo[0] and name in self._take_all_languages:
                    bytesByLang[name] = currText
                else:
                    # All other mismatches: blank out the text.
                    # For example if the current text is CSS (langName), but we're looking at
                    # a snippet of Ruby code, write out blanked CSS to the Ruby stream.
                    bytesByLang.addWhiteSpace(name, squelchedText)
            # end of loop through all languages for this segment
            if TPLInfo and origLangName == TPLInfo[0] and TPLInfo[2].search(currText):
                currState &= ~self._IN_SSL
            prevText = currText
            currLineNum += numNewLinesInCurrText
        # end of main loop through the document
        self._closeOpenBlocks(currState, bytesByLang, currLineNum)
            
        # Dump pending white-space to end so we see last-line messages on each stream.
        bytesByLang.finish()
        bytesByLangFinal = {}
        for name in bytesByLang.keys():
            bytesByLangFinal[name] = "".join(bytesByLang[name])
            #log.debug("Lint doc(%s):[\n%s\n]", name, bytesByLang[name])
        bytesByLang = bytesByLangFinal

        python_encoding_name = request.encoding.python_encoding_name
        if python_encoding_name not in ('ascii', 'utf-8'):
            charsByLang = {}
            for name, byteSubset in bytesByLang.items():
                try:
                    charsByLang[name] = byteSubset.decode("utf-8").encode(python_encoding_name)
                except:
                    log.exception("Can't encode into encoding %s", python_encoding_name)
                    charsByLang[name] = byteSubset
        else:
            charsByLang = bytesByLang

        lintResultsByLangName = {}
        for langName, textSubset in charsByLang.items():
            if not textSubset.strip():
                # Don't bother linting empty documents.  XML-based languages
                # require at least one element, but that could be annoying.
                continue
            if startCheck and langName in startCheck:
                startPtn, insertion = startCheck[langName]
                if not startPtn.match(textSubset):
                    textSubset = insertion + textSubset
            if langName.startswith("HTML"):
                # Is there an explicit doctype?
                if textSubset.startswith('<?xml '):
                    langName = "HTML"
                else:
                    m = _doctype_re.match(textSubset)
                    if m:
                        if not m.group(1):
                            langName = "HTML5"
                        else:
                            langName = "HTML"
                    elif langName == "HTML" and self.lang == "HTML5":
                        # Use the correct aggregator class.
                        langName = "HTML5"
                    elif koDoc_language not in ("HTML", "HTML5"):
                        # For HTML markup langs and templating langs, use the
                        # default HTML decl to see if they want HTML5 - bug 88884.
                        if "HTML 5" in request.prefset.getStringPref("defaultHTMLDecl"):
                            langName = "HTML5"
            linter = self._linterByName(langName, lintersByName)
            if linter:
                try:
                    # UnwrapObject so we don't run the textSubset text
                    # through another xpcom decoder/encoder
                    newLintResults = UnwrapObject(linter).lint_with_text(request, textSubset)
                    if newLintResults and newLintResults.getNumResults():
                        #log.debug("**** Errors: ***** lang: %s, text:%s", langName, self.addLineNumbers(textSubset, 1))
                        #log.debug("results: %s", ", ".join([str(x) for x in newLintResults.getResults()]))
                        if langName in ("CSS", "JavaScript"):
                            newLintResults = self._filter_guessed_emitted_hits(newLintResults)
                        lintResultSet = lintResultsByLangName.get(langName)
                        if lintResultSet:
                            lintResultSet.addResults(newLintResults)
                        else:
                            lintResultsByLangName[langName] = newLintResults
                except AttributeError:
                    log.exception("No lint_with_text method for linter for language %s", langName)
            else:
                pass
                #log.debug("no linter for %s", langName)
        # If we have more than one sub-language, tag each message with the originating language.
        numLintResultSets = len(lintResultsByLangName)
        if numLintResultSets == 0:
            return koLintResults()
        elif len(charsByLang) == 1:
            return self._check_emitted_code_lines(lintResultsByLangName.values()[0], textAsBytes)
        else:
            finalLintResults = koLintResults()
            for langName, lintResultSet in lintResultsByLangName.items():
                mLangName = self._getMappedName(langName)
                for lintResult in lintResultSet.getResults():
                    lintResult.description = mLangName + ": " + lintResult.description
                finalLintResults.addResults(lintResultSet)
            return self._check_emitted_code_lines(finalLintResults, textAsBytes)
    
    def _closeOpenBlocks(self, currState, bytesByLang, currLineNum):
        if currState & self._IN_CSS_ATTR:
            bytesByLang.replace_ending_white_space("CSS", "}", currLineNum)
            self._emittedCodeLineNumbers.add(currLineNum)
            currState &= ~self._IN_CSS_ATTR
        elif currState & self._IN_JS_FUNCTION_DEF:
            bytesByLang.replace_ending_white_space("JavaScript", "}", currLineNum)
            self._emittedCodeLineNumbers.add(currLineNum)
            currState &= ~self._IN_JS_FUNCTION_DEF
        elif currState & self._IN_JS_FUNCTION_DEF_INVOCN:
            bytesByLang.replace_ending_white_space("JavaScript", "})();", currLineNum)
            self._emittedCodeLineNumbers.add(currLineNum)
            currState &= ~self._IN_JS_FUNCTION_DEF_INVOCN
        return currState
    
    def _filter_guessed_emitted_hits(self, lintResults):
        if not self._multiLanguageLineNumbers:
            return lintResults
        keepers = [lr for lr in lintResults.getResults() if
                   (lr.lineStart != lr.lineEnd
                    or lr.lineStart not in self._multiLanguageLineNumbers)]
        if len(keepers) == lintResults.getNumResults():
            return lintResults
        res = koLintResults()
        for r in keepers:
            res.addResult(r)
        return res
        
    def _check_emitted_code_lines(self, lintResults, textAsBytes):
        if not self._emittedCodeLineNumbers:
            return lintResults
        sepLines = None
        for result in lintResults.getResults():
            if result.lineStart == result.lineEnd and result.lineStart in self._emittedCodeLineNumbers:
                if sepLines is None:
                    sepLines = textAsBytes.splitlines()
                try:
                    result.columnEnd = len(sepLines[result.lineStart - 1]) + 1
                    result.columnStart = 1
                except:
                    log.exception("Problem getting length of line %d", result.lineStart)
        return lintResults

class _Common_HTMLAggregator(_CommonHTMLLinter):
    def __init__(self):
        _CommonHTMLLinter.__init__(self)
        self._koLintService_UW = UnwrapObject(self._koLintService)

    # Do all the language-separation in the aggregator.  Then each HTML
    # terminal linter will concern itself only with the full document,
    # and won't have to pick out sublanguages.
    def lint(self, request, udlMapping=None, linters=None,
             TPLInfo=None,
             startCheck=None):
        return self._lint_common_html_request(request, udlMapping, linters,
                                              TPLInfo,
                                              startCheck)

    def lint_with_text(self, request, text):
        if not text:
            #log.debug("no text")
            return
        # Your basic aggregator....
        linters = self._koLintService_UW.getTerminalLintersForLanguage(self.lang)
        finalLintResults = None  # Becomes the first results that has entries.
        for linter in linters:
            newLintResults = UnwrapObject(linter).lint_with_text(request, text)
            if newLintResults and newLintResults.getNumResults():
                if finalLintResults is None:
                    finalLintResults = newLintResults
                elif newLintResults:
                    # Keep the lint results that has the most entries, then copy
                    # the other result with lesser entries into it.
                    if newLintResults.getNumResults() > finalLintResults.getNumResults():
                        # Swap them around, so final has the most entries.
                        finalLintResults, newLintResults = newLintResults, finalLintResults
                    finalLintResults.addResults(newLintResults)
        return finalLintResults

class KoHTMLCompileLinter(_Common_HTMLAggregator):
    _reg_desc_ = "Komodo HTML Aggregate Linter"
    _reg_clsid_ = "{DBF1E5E0-91C7-43da-870B-DB1859017102}"
    _reg_contractid_ = "@activestate.com/koLinter?language=HTML&type=Aggregator;1"
    _reg_categories_ = [
         ("category-komodo-linter-aggregator", 'HTML'),
         ]
    lang = "HTML"

class KoHTML5CompileLinter(_Common_HTMLAggregator):
    _reg_desc_ = "Komodo HTML5 Aggregate Linter"
    _reg_clsid_ = "{06828f1d-7d2d-4cf7-8ed0-4d9259b875f0}"
    _reg_contractid_ = "@activestate.com/koLinter?language=HTML5&type=Aggregator;1"
    _reg_categories_ = [
         ("category-komodo-linter-aggregator", 'HTML5'),
         ]

    lang = "HTML5"
        

class CommonTidyLinter(object):
    _com_interfaces_ = [components.interfaces.koILinter]

    @LazyClassAttribute
    def _xhtml_doctype_re(self):
        return re.compile(r'(?:<\?xml[^>]*>)?<!doctype\b[^>]*?(?://W3C//DTD XHTML|/xhtml\d*\.dtd)[^>]*>', re.DOTALL|re.IGNORECASE)

    def lint_with_text(self, request, text):
        prefset = request.prefset
        if not prefset.getBooleanPref("lintHTMLTidy"):
            return
        languageName = request.koDoc.language
        # Bug 100418: We're probably in a snippet for RHTML, Django, etc.,
        # that doesn't start with a doctype/xml header, so there's no point
        # asking Tidy to for all warning messages, as the first thing it
        # will complain about is the missing Doctype header.
        #
        # Later on it's possible to request warnings and filter out ones
        # that obviously don't make sense. 
        allowTidyWarnings = (languageName in ("HTML", "HTML5", "XML")
                             or _doctype_re.match(text)
                             or text.startswith("<?xml "))
        cwd = request.cwd

        text = eollib.convertToEOLFormat(text, eollib.EOL_LF)
        datalines = text.split('\n')

        # get the tidy config file
        configFile = prefset.getStringPref('tidy_configpath')
        if configFile and not os.path.exists(configFile):
            log.debug("The Tidy configuration file does not exist, please "
                     "correct your settings in the preferences for HTML.")
            configFile = None
            
        errorLevel = prefset.getStringPref('tidy_errorlevel')
        if errorLevel != 'errors' and not allowTidyWarnings:
            errorLevel = 'errors'
        accessibility = prefset.getStringPref('tidy_accessibility')
        
        #Character encodings
        #-------------------
        #  -raw              to output values above 127 without conversion to entities
        #  -ascii            to use US-ASCII for output, ISO-8859-1 for input
        #  -latin1           to use ISO-8859-1 for both input and output
        #  -iso2022          to use ISO-2022 for both input and output
        #  -utf8             to use UTF-8 for both input and output
        #  -mac              to use MacRoman for input, US-ASCII for output
        #  -win1252          to use Windows-1252 for input, US-ASCII for output
        enc = '-raw'
        if request.encoding.python_encoding_name == 'utf-8':
            enc = '-utf8'
        elif request.encoding.python_encoding_name == 'latin-1' or \
             request.encoding.python_encoding_name.startswith('iso8859'):
            enc = '-latin1'
        elif request.encoding.python_encoding_name == 'cp1252':
            enc = '-win1252'
            
        koDirs = components.classes["@activestate.com/koDirs;1"].\
                      getService(components.interfaces.koIDirs)
        argv = [os.path.join(koDirs.supportDir, "html", "tidy"),
                '-errors', '-quiet', enc, '--show-errors', '100']
        argv += getattr(self, "html5_tidy_argv_additions", [])
        if request.koDoc.language == "HTML" and self._xhtml_doctype_re.match(text):
            argv.append("-xml")

        if allowTidyWarnings and accessibility != '0':
            argv += ['-access', accessibility]
        if allowTidyWarnings and configFile:
            argv += ['-config', configFile]
        
        cwd = cwd or None
        # Ignore stdout, as tidy dumps a cleaned up version of the input
        # file on it, which we don't care about.
        #log.debug("Running tidy argv: %r", argv)
        #print ("Running tidy argv: %s" % (" ".join(argv)))
        p = process.ProcessOpen(argv, cwd=cwd)
        stdout, stderr = p.communicate(text)
        lines = stderr.splitlines(1)

        # Tidy stderr output looks like this:
        #    Tidy (vers 4th August 2000) Parsing console input (stdin)
        #    line 12 column 1 - Error: <body> missing '>' for end of tag
        #    line 14 column 2 - Warning: <tr> isn't allowed in <body> elements
        # <snip>
        #    line 674 column 5 - Warning: <img> lacks "alt" attribute
        #    
        #    stdin: Doctype given is "-//W3C//DTD HTML 4.0 Transitional//EN"
        #    stdin: Document content looks like HTML 4.01 Transitional
        #    41 warnings/errors were found!
        #    
        #    This document has errors that must be fixed before
        #    using HTML Tidy to generate a tidied up version.
        #    
        #    The table summary attribute should be used to describe
        # <snip ...useful suggestion paragraph that we should consider using>
        # Quickly strip out uninteresting lines.
        lines = [l for l in lines if l.startswith('line ')]
        lines = self.filterLines(lines)
        results = koLintResults()
        resultRe = re.compile("""^
            line\s(?P<line>\d+)
            \scolumn\s(?P<column>\d+)
            \s-\s(?P<desc>.*)$""", re.VERBOSE)
        for line in lines:
            if enc == '-utf8':
                line = unicode(line,'utf-8')
            resultMatch = resultRe.search(line)
            if not resultMatch:
                log.warn("Could not parse tidy output line: %r", line)
                continue

            #print "KoHTMLLinter: %r -> %r" % (line, resultMatch.groupdict())
            try:
                lineStart = int(resultMatch.group("line"))
                columnStart = int(resultMatch.group("column"))
            except ValueError:
                # Tidy sometimes spits out an invalid line (don't know why).
                # This catches those lines, and ignores them.
                continue

            description = resultMatch.group("desc")
            # We keep the "Error:"/"Warning:" on the description because
            # currently we do not get green squigglies for warnings.
            if description.startswith("Error:"):
                severity = KoLintResult.SEV_ERROR
            elif description.startswith("Warning:") or \
                 description.startswith("Access:"):
                if errorLevel == 'errors':
                    # ignore warnings
                    continue
                severity = KoLintResult.SEV_WARNING
            elif description.startswith("Info:"):
                # Ignore Info: lines.
                continue
            else:
                severity = KoLintResult.SEV_ERROR

            # Set the end of the lint result to the '>' closing the tag.
            i = lineStart
            columnEnd = -1
            while i < len(datalines):
                # first pass -- go to first >, even if in attribute name
                if i == lineStart:
                    curLine = datalines[i-1][columnStart:]
                    offset = columnStart
                else:
                    curLine = datalines[i-1]
                    offset = 0
                end = curLine.find('>')
                if end != -1:
                    columnEnd = end + offset + 2
                    break
                i = i + 1
            if columnEnd == -1:
                columnEnd=len(datalines[i-1]) + 1
            lineEnd = i
            
            # Move back to the first non-blank line for errors
            # that appear on blank lines.  In empty and
            # near-empty buffers this result will end up at
            # the first line (which is 1-based in the lint system)
            if lineStart == lineEnd and \
               columnEnd <= columnStart:
                while lineStart > 0 and len(datalines[lineStart - 1]) == 0:
                    lineStart -= 1
                if lineStart == 0:
                    lineStart = 1
                lineEnd = lineStart
                columnStart = 1
                columnEnd = len(datalines[lineStart-1]) + 1

            result = KoLintResult(description=description,
                                  severity=severity,
                                  lineStart=lineStart,
                                  lineEnd=lineEnd,
                                  columnStart=columnStart,
                                  columnEnd=columnEnd)

            results.addResult(result)
        return results
    

class KoHTMLTidyLinter(CommonTidyLinter):
    _reg_clsid_ = "{47b1aa81-d872-4b24-8338-de80ec3967a1}"
    _reg_contractid_ = "@activestate.com/koHTMLTidyLinter;1"
    _reg_desc_ = "HTML Tidy Linter"
    _reg_categories_ = [
         ("category-komodo-linter", 'HTML&type=tidy'),
         ]

    def lint(self, request):
        text = request.content.encode(request.encoding.python_encoding_name)
        return self.lint_with_text(request, text)

    def filterLines(self, lines):
        return lines

class KoHTML5TidyLinter(CommonTidyLinter):
    _reg_desc_ = "Komodo HTML 5 Tidy Linter"
    _reg_clsid_ = "{06b2f705-849d-462f-aafb-bb2e4dfd6d37}"
    _reg_contractid_ = "@activestate.com/koHTML5TidyLinter;1"
    _reg_categories_ = [
         ("category-komodo-linter", 'HTML5&type=tidy'),
         ]

    
    html5_tidy_argv_additions = [
        "--new-blocklevel-tags", "section,header,footer,hgroup,main,nav,dialog,datalist,details,figcaption,figure,meter,output,progress",
        "--new-pre-tags", "article,aside,summary,mark",
        "--new-inline-tags", "video,audio,canvas,source,embed,ruby,rt,rp,keygen,menu,command,time",
    ]

    def lint(self, request):
        text = request.content.encode(request.encoding.python_encoding_name)
        return self.lint_with_text(request, text)

    def filterLines(self, lines):
        return [line for line in lines if "is not approved by W3C" not in line]


class _invokePerlLinter(object):
    _com_interfaces_ = [components.interfaces.koILinter]
    def lint(self, request):
        text = request.content.encode(request.encoding.python_encoding_name)
        return self.lint_with_text(request, text)
        
    def _lint_with_text(self, request, text, perlHTMLCheckerPrefName,
                        perlLinterBasename, args):
        if not text:
            #log.debug("<< no text")
            return
        prefset = request.prefset
        if not prefset.getBooleanPref(perlHTMLCheckerPrefName):
            return
        perlLintDir = os.path.join(components.classes["@activestate.com/koDirs;1"].\
                                    getService(components.interfaces.koIDirs).supportDir,
                                   "lint",
                                   "perl")
        perlWrapperFileName = os.path.join(perlLintDir, perlLinterBasename);
        perlExe = prefset.getStringPref("perlDefaultInterpreter")
        if not perlExe:
            perlExe = components.classes["@activestate.com/koAppInfoEx?app=Perl;1"] \
                     .getService(components.interfaces.koIAppInfoEx) \
                     .executablePath
            if not perlExe:
                log.debug("html lint with Perl: No perl interpreter found.")
                return
        cmd = [perlExe, perlWrapperFileName]
        cwd = request.cwd or None
        try:
            p = process.ProcessOpen(cmd, cwd=cwd)
            stdout, stderr = p.communicate(text)
            warnLines = stdout.splitlines() # Don't need the newlines.
        except:
            log.exception("Error perl/html linting, cmd: %s, pwd:%s", cmd, cwd)
            return
            
                
        # 'jslint' error reports come in this form:
        # jslint error: at line \d+ column \d+: explanation
        results = koLintResults()
        if perlLinterBasename == "htmltidy.pl":
            hasStatus = True
            msgRe = re.compile(r'''^input \s+ \( (?P<lineNo>\d+)
                               : (?P<columnNo>\d+) \)
                               \s+ (?P<status>Warning|Info|Error)
                               : \s* (?P<desc>.*)$''', re.VERBOSE)
        else:
            hasStatus = False
            msgRe = re.compile(r'''^\s+ \( (?P<lineNo>\d+)
                               : (?P<columnNo>\d+) \)
                               \s+
                               (?P<desc>.*)$''', re.VERBOSE)
        datalines = text.splitlines()
        numDataLines = len(datalines)
        for msgLine in warnLines:
            m = msgRe.match(msgLine)
            if m:
                status = hasStatus and m.group("status") or None
                if status == "Info":
                    # These are rarely useful
                    continue
                lineNo = int(m.group("lineNo"))
                #columnNo = int(m.group("columnNo"))
                # build lint result object
                result = KoLintResult()
                # if the error is on the last line, work back to the last
                # character of the first nonblank line so we can display
                # the error somewhere
                if lineNo >= len(datalines):
                   lineNo = len(datalines) - 1
                if len(datalines[lineNo]) == 0:
                    while lineNo > 0 and len(datalines[lineNo - 1]) == 0:
                        lineNo -= 1
                if lineNo == 0:
                    lineNo = 1
                result.columnStart =  1
                result.columnEnd = len(datalines[lineNo - 1]) + 1
                result.lineStart = result.lineEnd = lineNo
                if status == "Error":
                    result.severity = result.SEV_ERROR
                else:
                    result.severity = result.SEV_WARNING
                result.description = m.group("desc")
                results.addResult(result)

        return results
        
class KoHTMLPerl_HTMLLint_Linter(_invokePerlLinter):
    """
    Check HTML code by using Perl's HTML-Lint module
    """
    _reg_clsid_ = "{1603484f-7723-4a65-b0f5-b4f77c563d25}"
    _reg_desc_ = "Komodo HTML Linter Using Perl's HTML::Lint"
    _reg_contractid_ = "@activestate.com/koLinter?language=HTML&type=Perl:HTML::Lint;1"
    _reg_categories_ = [
         ("category-komodo-linter", 'HTML&type=Perl:HTML::Lint'),
         ]

    def lint_with_text(self, request, text):
        return self._lint_with_text(request, text,
                                    "lintHTML_CheckWith_Perl_HTML_Lint",
                                    "htmllint.pl", [])
        
class KoHTMLPerl_HTMLTidy_Linter(_invokePerlLinter):
    """
    Check HTML code by using Perl's HTML-Tidy module
    """
    _reg_clsid_ = "{6d9817fc-7b64-435b-9152-7183a9d3ffcc}"
    _reg_desc_ = "Komodo HTML Linter Using Perl's HTML::Tidy"
    _reg_contractid_ = "@activestate.com/koLinter?language=HTML&type=Perl:HTML::Tidy;1"
    _reg_categories_ = [
         ("category-komodo-linter", 'HTML&type=Perl:HTML::Tidy'),
         ]

    def lint_with_text(self, request, text):
        return self._lint_with_text(request, text,
                                    "lintHTML_CheckWith_Perl_HTML_Tidy",
                                    "htmltidy.pl", [])

    
# HTML5 can use the generic aggregator
 
class KoHTML5_html5libLinter:
    _com_interfaces_ = [components.interfaces.koILinter]
    _reg_clsid_ = "{913f43fc-d46b-4d2a-a821-0b925ca9a65b}"
    _reg_contractid_ = "@activestate.com/koHTML5_html5libLinter;1"
    _reg_desc_ = "HTML5 html5lib Linter"
    _reg_categories_ = [
         ("category-komodo-linter", 'HTML5&type=html5lib'),
         ]

    @LazyClassAttribute
    def problem_word_ptn(self):
        return re.compile(r'([ &<]?\w+\W*)$')

    @LazyClassAttribute
    def leading_ws_ptn(self):
        return re.compile(r'(\s+)')

    dictType = type({})

    def lint(self, request):
        text = request.content.encode(request.encoding.python_encoding_name)
        return self.lint_with_text(request, text)

    def lint_with_text(self, request, text):
        if not text:
            return
        prefset = request.prefset
        if not prefset.getBooleanPref('lintHTML5Lib'):
            return
        textLines = text.splitlines()
        try:
            # Use StringIO, not CStringIO!
            # CStringIO.StringIO(latin1 str).read() => ucs2 string 
            # StringIO.StringIO(latin1 str).read() => latin1 string 
            inputStream = StringIO.StringIO(text)
            parser = html5lib.HTMLParser()
            try:
                doc = parser.parse(inputStream,
                                   encoding=request.encoding.python_encoding_name)
            finally:
                inputStream.close()
            errors = parser.errors
            #log.debug("**** Errors: \n%s\n", errors)
            results = koLintResults()
            groupedErrors = {}
            # Gather the grouped results by line/col/errorName, favoring dicts
            for posnTuple, errorName, params in parser.errors:
                lineNo = int(posnTuple[0]) - 1
                endColNo = int(posnTuple[1]) + 1
                key = "%d:%d:%s" % (lineNo, endColNo, errorName)
                if key not in groupedErrors:
                    groupedErrors[key] = [lineNo, endColNo, errorName, params]
                elif type(params) == self.dictType:
                    groupedErrors[key][3] = params
                else:
                    #log.debug("Ignoring additional params: %s", params)
                    pass
            for lineNo, endColNo, errorName, params in groupedErrors.values():
                #print "KoHTMLLinter: %r -> %r" % (line, resultMatch.groupdict())
                if lineNo >= len(textLines) or len(textLines[lineNo]) == 0:
                    lineNo = len(textLines) - 1
                    while lineNo >= 0 and len(textLines[lineNo]) == 0:
                        lineNo -= 1
                    if lineNo < 0:
                        log.warn("No text to display for bug %s", errorName)
                        continue
                result = KoLintResult()
                result.lineStart = result.lineEnd = lineNo + 1
                result.columnStart = 1
                result.columnEnd = 1 + len(textLines[lineNo])
                result.description = self._buildErrorMessage(errorName, params)
                #TODO: Distinguish errors from warnings...
                result.severity = result.SEV_ERROR
                
                results.addResult(result)
        except ServerException:
            log.exception("ServerException")
            raise
        except:
            # non-ServerException's are unexpected internal errors
            log.exception("unexpected internal error")
            raise
        return results
    
    def _buildErrorMessage(self, errorName, params):
        if errorName in html5libErrorDict:
            errorTemplate = html5libErrorDict[errorName]
            try:
                return errorTemplate % params
            except (TypeError, KeyError):
                pass
        else:
            errorTemplate = errorName
        return "%s: %s" % (errorTemplate, params)
