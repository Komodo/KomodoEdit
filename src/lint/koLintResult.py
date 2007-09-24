#!python
# Copyright (c) 2000-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.


from xpcom import components
import re

class KoLintResult:
    _com_interfaces_ = [components.interfaces.koILintResult]
# This object is never actually registered and created by contract ID.
# Our language linters create them explicitly.
#    _reg_desc_ = "Komodo Lint Result"
#    _reg_clsid_ = "{21648850-492F-11d4-AC24-0090273E6A60}"
#    _reg_contractid_ = "Komodo.LintResult"

    SEV_INFO    = components.interfaces.koILintResult.SEV_INFO
    SEV_WARNING = components.interfaces.koILintResult.SEV_WARNING
    SEV_ERROR   = components.interfaces.koILintResult.SEV_ERROR

    def __init__(self):
        self.lineStart = -1
        self.lineEnd = -1
        self.columnStart = -1
        self.columnEnd = -1
        self.description = ""
        self.encodedDescription = None
        self.severity = None

    def _encode_string(self, s):
        return re.sub(# match 0x00-0x1f except TAB(0x09), LF(0x0A), and CR(0x0D)
                   '([\x00-\x08\x0b\x0c\x0e-\x1f])',
                   # replace with XML decimal char entity, e.g. '&#7;'
                   lambda m: '\\x%02X'%ord(m.group(1)),
                   s)

    # XXX since this object is not created through xpcom createinstance,
    # using a setter doesn't work.  However, we access it through xpcom
    # from javascript, so we can do our encoding once in the getter
    # to prevent UI crashes.
    def get_description(self):
        if self.encodedDescription is None:
            _gEncodingServices = components.classes['@activestate.com/koEncodingServices;1'].\
                     getService(components.interfaces.koIEncodingServices)
            try:
                unicodebuffer, encoding, bom = _gEncodingServices.\
                                                 getUnicodeEncodedString(self.description)
                self.encodedDescription  = self._encode_string(unicodebuffer)
            except Exception, e:
                self.encodedDescription  = repr(self.description)[1:-1] # remove quotes
        return self.encodedDescription
