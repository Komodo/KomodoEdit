import unittest, os
from ctypes import *
from comtypes import IUnknown, GUID
from comtypes.automation import VARIANT, DISPPARAMS
from comtypes.typeinfo import LoadTypeLibEx, LoadRegTypeLib
from comtypes.test import is_resource_enabled

def get_refcnt(comptr):
    # return the COM reference count of a COM interface pointer
    if not comptr:
        return 0
    comptr.AddRef()
    return comptr.Release()

class VariantTestCase(unittest.TestCase):

    def test_com_refcounts(self):
        # typelib for oleaut32
        tlb = LoadRegTypeLib(GUID("{00020430-0000-0000-C000-000000000046}"), 2, 0, 0)
        rc = get_refcnt(tlb)

        p = tlb.QueryInterface(IUnknown)
        self.failUnlessEqual(get_refcnt(tlb), rc+1)

        del p
        self.failUnlessEqual(get_refcnt(tlb), rc)

    def test_com_pointers(self):
        # Storing a COM interface pointer in a VARIANT increments the refcount,
        # changing the variant to contain something else decrements it
        tlb = LoadRegTypeLib(GUID("{00020430-0000-0000-C000-000000000046}"), 2, 0, 0)
        rc = get_refcnt(tlb)

        v = VARIANT(tlb)
        self.failUnlessEqual(get_refcnt(tlb), rc+1)

        p = v.value
        self.failUnlessEqual(get_refcnt(tlb), rc+2)
        del p
        self.failUnlessEqual(get_refcnt(tlb), rc+1)

        v.value = None
        self.failUnlessEqual(get_refcnt(tlb), rc)

    def test_null_com_pointers(self):
        p = POINTER(IUnknown)()
        self.failUnlessEqual(get_refcnt(p), 0)

        v = VARIANT(p)
        self.failUnlessEqual(get_refcnt(p), 0)
        
    def test_dispparams(self):
        # DISPPARAMS is a complex structure, well worth testing.
        d = DISPPARAMS()
        d.rgvarg = (VARIANT * 3)()
        values = [1, 5, 7]
        for i, v in enumerate(values):
            d.rgvarg[i].value = v
        result = [d.rgvarg[i].value for i in range(3)]
        self.failUnlessEqual(result, values)

    def test_pythonobjects(self):
        objects = [None, 42, 3.14, True, False, "abc", u"abc", 7L]
        for x in objects:
            v = VARIANT(x)
            self.failUnlessEqual(x, v.value)

    def test_integers(self):
        import sys
        v = VARIANT()

        v.value = sys.maxint
        self.failUnlessEqual(v.value, sys.maxint)
        self.failUnlessEqual(type(v.value), int)

        v.value += 1
        self.failUnlessEqual(v.value, sys.maxint+1)
        self.failUnlessEqual(type(v.value), long)

        v.value = 1L
        self.failUnlessEqual(v.value, 1)
        self.failUnlessEqual(type(v.value), int)

    def test_datetime(self):
        import datetime
        now = datetime.datetime.now()

        v = VARIANT()
        v.value = now
        from comtypes.automation import VT_DATE
        self.failUnlessEqual(v.vt, VT_DATE)
        self.failUnlessEqual(v.value, now)

    def test_BSTR(self):
        from comtypes.automation import BSTR, VT_BSTR
        v = VARIANT()
        v.value = u"abc\x00123\x00"
        self.failUnlessEqual(v.value, "abc\x00123\x00")

        v.value = None
        # manually clear the variant
        v._.VT_I4 = 0

        # NULL pointer BSTR should be handled as empty string
        v.vt = VT_BSTR
        self.failUnless(v.value in ("", None))

class ArrayTest(unittest.TestCase):
    def test_double(self):
        import array
        for typecode in "df":
            # because of FLOAT rounding errors, whi will only work for
            # certain values!
            a = array.array(typecode, (1.0, 2.0, 3.0, 4.5))
            v = VARIANT()
            v.value = a
            self.failUnlessEqual(v.value, (1.0, 2.0, 3.0, 4.5))

    def test_int(self):
        import array
        for typecode in "bhiBHIlL":
            a = array.array(typecode, (1, 1, 1, 1))
            v = VARIANT()
            v.value = a
            self.failUnlessEqual(v.value, (1, 1, 1, 1))

################################################################

if __name__ == '__main__':
    unittest.main()
