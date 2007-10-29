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
