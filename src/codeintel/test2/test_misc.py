#!/usr/bin/env python
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

"""Test miscellaneous bits of the Code Intelligence system."""

import unittest
import pprint
import logging

from testlib import TestError, TestSkipped, TestFailed, tag
from citestsupport import CodeIntelTestCase



#---- globals

log = logging.getLogger("test")



#---- test cases

class MiscTestCase(unittest.TestCase):
    def test_parsePyFuncDoc(self):
        from codeintel2.util import parsePyFuncDoc as parse
        cases = [
            ("read", "read([s]) -- Read s characters, or the rest of the string",
             ["read([s])"], ["Read s characters, or the rest of the string"]),
            ("b2a_qp", """b2a_qp(data, quotetabs=0, istext=1, header=0) -> s; 
 Encode a string using quoted-printable encoding. 

On encoding, when istext is set, newlines are not encoded, and white 
space at end of lines is.  When istext is not set, \r and \n (CR/LF) are 
both encoded.  When quotetabs is set, space and tabs are encoded.""",
             ["b2a_qp(data, quotetabs=0, istext=1, header=0) -> s;"],
             [" Encode a string using quoted-printable encoding. ",
              "",
              "On encoding, when istext is set, newlines are not encoded, and white ",
              "space at end of lines is.  When istext is not set, ",
              " and ",
              " (CR/LF) are ",
              "both encoded.  When quotetabs is set, space and tabs are encoded."]),
            ("new_module", """new_module(name) -> module
Create a new module.  Do not enter it in sys.modules.
The module name must include the full package name, if any.""",
             ["new_module(name) -> module"],
             ["Create a new module.  Do not enter it in sys.modules.",
              "The module name must include the full package name, if any."]),
            ("getaddrinfo", """getaddrinfo(host, port [, family, socktype, proto, flags])
    -> list of (family, socktype, proto, canonname, sockaddr)

Resolve host and port into addrinfo struct.
""",
             ["getaddrinfo(host, port [, family, socktype, proto, flags])"],
             ["    -> list of (family, socktype, proto, canonname, sockaddr)",
              "",
              "Resolve host and port into addrinfo struct."]),
            ("MessageBeep", """MessageBeep(x) - call Windows MessageBeep(x). x defaults to MB_OK.""",
             ["MessageBeep(x)"],
             ["call Windows MessageBeep(x). x defaults to MB_OK."]),
            ("logreader", """logreader(filename) --> log-iterator
Create a log-reader for the timing information file.""",
             ["logreader(filename) --> log-iterator"],
             ["Create a log-reader for the timing information file."]),
            ("resolution", """resolution() -> (performance-counter-ticks, update-frequency)""",
             ["resolution() -> (performance-counter-ticks, update-frequency)"],
             []),
            ("gethostbyname", """gethostbyname(host) -> address

Return the IP address (a string of the form '255.255.255.255') for a host.""",
             ["gethostbyname(host) -> address"],
             ["Return the IP address (a string of the form '255.255.255.255') for a host."]),
            ("replace", """replace (str, old, new[, maxsplit]) -> string

Return a copy of string str with all occurrences of substring
old replaced by new. If the optional argument maxsplit is
given, only the first maxsplit occurrences are replaced.""",
             ["replace (str, old, new[, maxsplit]) -> string"],
             ["Return a copy of string str with all occurrences of substring",
              "old replaced by new. If the optional argument maxsplit is",
              "given, only the first maxsplit occurrences are replaced."]),
            ("joinfields", """join(list [,sep]) -> string
joinfields(list [,sep]) -> string

Return a string composed of the words in list, with
intervening occurrences of sep.  Sep defaults to a single
space.

(join and joinfields are synonymous)""",
             ["join(list [,sep]) -> string",
              "joinfields(list [,sep]) -> string"],
             ["Return a string composed of the words in list, with",
              "intervening occurrences of sep.  Sep defaults to a single",
              "space.",
              "",
              "(join and joinfields are synonymous)"]),
            ("QueryValueEx", """value,type_id = QueryValueEx(key, value_name) - Retrieves the type and data for a specified value name associated with an open registry key.

key is an already open key, or any one of the predefined HKEY_* constants.
value_name is a string indicating the value to query""",
             ["QueryValueEx(key, value_name) -> value,type_id"],
             ["Retrieves the type and data for a specified value name",
              "associated with an open registry key."]),
            ("StringIO", """class StringIO([buffer])

    When a StringIO object is created, it can be initialized to an existing
    string by passing the string to the constructor. If no string is given,
    the StringIO will start empty.

    The StringIO object can accept either Unicode or 8-bit strings, but
    mixing the two may take some care. If both are used, 8-bit strings that
    cannot be interpreted as 7-bit ASCII (that use the 8th bit) will cause
    a UnicodeError to be raised when getvalue() is called.
    """,
             ["class StringIO([buffer])"],
             ["When a StringIO object is created, it can be initialized to an existing",
              "string by passing the string to the constructor. If no string is given,",
              "the StringIO will start empty.",
              "",
              "The StringIO object can accept either Unicode or 8-bit strings, but",
              "mixing the two may take some care. If both are used, 8-bit strings that",
              "cannot be interpreted as 7-bit ASCII (that use the 8th bit) will cause",
              "a UnicodeError to be raised when getvalue() is called."]),
        ]
        for funcname, doc, siglines, desclines in cases:
            actual_siglines, actual_desclines = parse(doc, funcname=funcname)
            self.failUnless(
                (actual_siglines, actual_desclines) == (siglines, desclines),
                "stdcix._parsePyFuncDoc() returned an unexpected result:\n"+
                "======================= doc:\n"+str(doc)+
                "\n======================= expected:\n"
                +pprint.pformat(siglines)+"\n"+pprint.pformat(desclines)+
                "\n======================= actual:\n"
                +pprint.pformat(actual_siglines)+"\n"+pprint.pformat(actual_desclines)
            )



#---- mainline

if __name__ == "__main__":
    unittest.main()

