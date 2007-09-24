# Copyright (c) 2000-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

# A simple XPCOM server which: accepts a string which is a line of
# python ending with the opening parentheses (but not including the
# parentheses) of a method call returns a documentation string
# suitable for a calltip this code only supports built-in modules and
# methods Much of this code was borrowed from Pythonwin's
# Pythonwin\pywin\idle\calltips.py

# modified from Brian Wing's code for VS7. [david ascher]

from xpcom import components

import re
import string
import sys
import types

class PerlCallTips:
    _com_interfaces_ = [components.interfaces.koICallTips]
    _reg_desc_ = "Perl CallTips"
    _reg_contractid_ = "@activestate.com/koPerlCallTips;1"
    _reg_clsid_ = "{cccefc6d-5821-48bd-96cd-b4ee61e7da0c}"

    def CallTips(self, source_line, text):
        return None

    def get_word_at_cursor(self, source_line,
                           wordchars="_->:$%@" + string.uppercase + string.lowercase + string.digits):
        chars = str(source_line)
        i = len(chars)
        while i and chars[i-1] in wordchars:
            i = i-1
        return chars[i:]

def make_arg_string(arg):
    """
    Return a string represnting an argument and its type
    """
    (name, type) = arg
    return "%s %s" % (type, name)


def rsplit(s, sep=" ", maxsplit=None):
    """
    Just like string.split(), but splits starting from the end of the
    string, rather than from the beginning.  Caveat: string.split()
    defaults to split on any whitespace.  Meeting that reqirement
    would be difficult, and is not worth the effort ATM.
    """
    if maxsplit == None:
        return s.split(sep)
    else:
        list = s.split(sep)
        return [sep.join(list[:-maxsplit])] + list[-maxsplit:]
