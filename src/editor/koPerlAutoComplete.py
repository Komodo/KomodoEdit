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

# stolen from brian wing's autocompletecomserver, which was stolen from mark hammond's code

# AutoCompleteCOMServer.py - A simple COM server which:
# takes the entire edit buffer along with the current cursor position (number
# of characters from the beginning of the buffer) which is
# hopefully over the '.' of the user typing in "modulename."
# returns a list of methods defined in modulename
# Much of this code was borrowed from Pythonwin's Pythonwin\pywin\scintilla\view.py

from xpcom import components
import array
import string
import sys
import types
import struct
import re

wordbreaks = "_->:$%@" + string.uppercase + string.lowercase + string.digits

class PerlAutoComplete:
    _com_interfaces_ = [components.interfaces.koIAutoComplete]
    _reg_desc_ = "Perl AutoComplete Engine"
    _reg_contractid_ = "@activestate.com/koPerlAutoComplete;1"
    _reg_clsid_ = "{f1b7ac6b-a427-4377-84a6-f147b378becb}"    

    def AutoComplete(self, pos, text):
        self.pos = pos
        self.text = text
        try:
            return self._DoAutoComplete()
        finally:
            self.text = None
            self.pos = None

    def _DoAutoComplete(self):
        # Heuristics a-la AutoExpand
        # The idea is to find other usages of the current binding
        # and assume, that it refers to the same object (or at least,
        # to an object of the same type)
        # Contributed by Vadim Chugunov [vadimch@yahoo.com]
        left, right = self._GetWordSplit()
        if left=="": # Ignore standalone dots
            return None
        # We limit our search to the current class, if that
        # information is available
        try:
            list = re.findall(re.escape(left) + "->\w+",self.text)
        except re.error:
            # parens etc may make an invalid RE, but this code wouldnt
            # benefit even if the RE did work :-)
            list = []
        prefix = len(left)+len("->")
        unique = {}
        for li in list:
            unique[li[prefix:]] = 1
            
        items = filter(lambda word: word[:2]!='__' or word[-2:]!='__', unique.keys())
        # Ignore the word currently to the right of the dot - probably a red-herring.
        try:
            items.remove(right[1:])
        except ValueError:
            pass

        if items:
            items.sort()
            self._removeDuplicates(items)
            # XXX should take completionSeparator for koLanguageServiceBase
            return string.join(items, '\n')

    def _GetWordSplit(self, bAllowCalls = 0):
        limit = len(self.text)
        before = []
        after = []
        index = self.pos-len("->")
        wordbreaks_use = wordbreaks
        if bAllowCalls: wordbreaks_use = wordbreaks_use + "()[]"
        while index>=0:
            char = self.text[index]
            if char not in wordbreaks_use: break
            before.insert(0, char)
            index = index-1
        index = self.pos
        while index<limit:
            char = self.text[index]
            if char not in wordbreaks_use: break
            after.append(char)
            index=index+1
        return string.join(before,''), string.join(after,'')

    def _removeDuplicates(self, list):
        """Remove duplicate items from a sorted list"""
        i = 1
        while i < len(list):
            if list[i-1] == list[i]:
                del list[i]
            i += 1

