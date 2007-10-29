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


import logging
from xpcom import components
from xpcom.server.enumerator import *
from koLanguageServiceBase import KoCompletionLanguageService


log = logging.getLogger("koPerlCompletion")


class KoPerlCompletion(KoCompletionLanguageService):
    _com_interfaces_ = [components.interfaces.koICompletionLanguageService]
    _reg_desc_ = "Perl Calltip/AutoCompletion Service"
    _reg_clsid_ = "{3d166878-3731-4941-b74b-8d9a06f5bfdb}"
    _reg_contractid_ = "@activestate.com/koPerlCompletionLanguageService;1"

    # styles in which autocomplete and calltips should not occur
    _suppressedStyles = (components.interfaces.ISciMoz.SCE_PL_COMMENTLINE,
                         components.interfaces.ISciMoz.SCE_PL_STRING)

    def __init__(self):
        self._calltips = components.classes['@activestate.com/koPerlCallTips;1'].createInstance(components.interfaces.koICallTips)
        self._autocomplete = components.classes['@activestate.com/koPerlAutoComplete;1'].createInstance(components.interfaces.koIAutoComplete)
        self.triggers = '>'
        self.triggersCallTip = '(),'
        self._braceCount = 0
        self._scintilla = None
        self.sysUtils = components.classes["@activestate.com/koSysUtils;1"].\
            getService(components.interfaces.koISysUtils)

    def StartCallTip(self, ch, scimoz):
        s = self._scintilla = scimoz
        selStart, selEnd = s.selectionStart, s.selectionEnd
        if selEnd == selStart and selStart > 0:
            #XXX do we need to mask the style?
            style = s.getStyleAt(s.positionBefore(selStart))
            if style in self._suppressedStyles:
                return

            if s.callTipActive():
                if ch == ')':
                    self._braceCount = self._braceCount - 1
                    if (self._braceCount < 1):
                        s.callTipCancel()
                elif ch == '(':
                    self._braceCount = self._braceCount + 1
                else:
                    self._ContinueCallTip()
            elif s.autoCActive():
                if ch == '(':
                    self._braceCount = self._braceCount + 1
                    self._StartCallTip()
                elif ch == ')':
                    self._braceCount = self._braceCount - 1
            else:
                if ch == '(':
                    self._braceCount = 1
                    self._StartCallTip()

    def AutoComplete(self, ch, scimoz):
        self._scintilla = scimoz
        s = scimoz

        # prevent completion in comments, strings, etc.
        styleMask = 127 #XXX shouldn't hardcode
        pos = self._getLastTypedCharPos()
        style = s.getStyleAt(pos) & styleMask 
        # print "keyPressed style: ",style," char: ", s.text[s.currentPos-1]

        if ch == '>' and s.getWCharAt(s.positionBefore(pos)) == "-" and \
           style not in self._suppressedStyles:
            self._StartAutoComplete()

    def _StartAutoComplete(self):
        # autocomplete works with _entire_ buffer as it scans it for attributes.
        s = self._scintilla
        completions = self._autocomplete.AutoComplete(
            self._getLastTypedCharPos(), s.text)
        if completions:
            s.autoCShow(0, completions)

    def _StartCallTip(self):
        s = self._scintilla
        lastline = self._getCurLine()
        lastpos = self._getLastTypedCharPos()
        bytepos = lastpos - self._getLineStartFromPosition(lastpos)
        pos = self.sysUtils.charIndexFromPosition(lastline, bytepos)
        text = lastline[:pos]
        tip = self._calltips.CallTips(text, self._scintilla.text)
        if tip:
            self._funcdef = tip.split('\n')[0]
            self._scintilla.callTipShow(lastpos, tip)
            self._ContinueCallTip()
        
    def _ContinueCallTip(self):
        s = self._scintilla
        start = 0
        current = self._getCurLine()
        funcdef = self._funcdef

        if not funcdef:
            log.warn("funcdef is false")
            return

        # XXX hack
        # Highlight the current parameter
        # XXX does not handle commas in strings, lists, dicts or
        # tuples properly
        
        commas = current.count(',')
        firstLParen = funcdef.find('(')
        if firstLParen != -1:
            start = firstLParen + 1
        while (start < len(funcdef) and commas > 0) :
            if (funcdef[start] == ',' or funcdef[start] == ')'):
                commas = commas - 1
            start = start + 1
        if (start < len(funcdef) and (funcdef[start] == ',' or funcdef[start] == ')')):
            start = start + 1
        end = start
        if (end < len(funcdef)):
            end = end + 1
        while (end < len(funcdef) and funcdef[end] != ',' and funcdef[end] != ')'):
            end = end + 1
        s.callTipSetHlt(start, end)

    def _getCurLine(self):
        """Returns the line on which the cursor rests.

        Hides uglyness of Scintilla's getCurLine() method, which
        returns a length and a buffer.  The buffer may contain garbage
        beyond buffer[length-1].

        XXX 8/13/03 SMC This hack should no longer be necessary,
        but am leaving in place for now.  The 'garbage' was probably
        just mis-handling of utf-8 data and byte positions in
        scintilla
        """
        
        length, buffer = self._scintilla.getCurLine()
        return buffer[:len(buffer)]

    def _getLineStartFromPosition(self, pos):
        """Returns the position of the beginning of the line."""
        
        s = self._scintilla
        return s.positionFromLine(s.lineFromPosition(pos))

    def _getLastTypedCharPos(self):
        """Returns the position of the last char typed.

        Assumes last action was typing a character.  Makes no attempt
        to deal with cursor movement, backspace etc.

        """
        
        s = self._scintilla
        #XXX does this correctly handle the begginings of lines?
        return s.positionBefore(s.currentPos)
