# Copyright (c) 2000-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

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

