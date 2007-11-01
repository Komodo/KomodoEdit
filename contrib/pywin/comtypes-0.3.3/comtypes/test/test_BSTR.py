import unittest, os
from ctypes import *
from comtypes import BSTR
from comtypes.test import requires

##requires("memleaks")

try:
    any
except NameError:
    from comtypes.test.find_memleak import any

from comtypes.test.find_memleak import find_memleak

class Test(unittest.TestCase):
    def check_leaks(self, func):
        leaks = find_memleak(func)
        self.failIf(any(leaks), "Leaks %d bytes: %s" % (sum(leaks), leaks))

    def test_creation(self):
        def doit():
            BSTR(u"abcdef" * 100)
        doit()
        self.check_leaks(doit)

    def test_from_param(self):
        def doit():
            BSTR.from_param(u"abcdef")
        self.check_leaks(doit)

    def test_paramflags(self):
        prototype = WINFUNCTYPE(c_void_p, BSTR)
        func = prototype(("SysStringLen", oledll.oleaut32))
        func.restype = c_void_p
        func.argtypes = (BSTR, )
        def doit():
            func(u"abcdef")
            func(u"abc xyz")
            func(BSTR(u"abc def"))
        self.check_leaks(doit)

    def test_inargs(self):
        SysStringLen = windll.oleaut32.SysStringLen
        SysStringLen.argtypes = BSTR,
        SysStringLen.restype = c_uint

        self.failUnlessEqual(SysStringLen("abc xyz"), 7)
        def doit():
            SysStringLen("abc xyz")
            SysStringLen(u"abc xyz")
            SysStringLen(BSTR(u"abc def"))
        self.check_leaks(doit)

if __name__ == "__main__":
    unittest.main()
