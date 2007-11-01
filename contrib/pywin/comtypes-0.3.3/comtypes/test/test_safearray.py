import unittest
from comtypes.automation import VARIANT, VT_ARRAY, VT_VARIANT, VT_I4, VT_R4, VT_R8

class TestCase(unittest.TestCase):
    def test_1(self):
        v = VARIANT()
        v.value = ((1, 2, 3), ("foo", "bar", None))
        self.failUnlessEqual(v.vt, VT_ARRAY | VT_VARIANT)
        self.failUnlessEqual(v.value, ((1, 2, 3), ("foo", "bar", None)))

    def test_double_array(self):
        import array
        a = array.array("d", (3.14, 2.78))
        v = VARIANT(a)
        self.failUnlessEqual(v.vt, VT_ARRAY | VT_R8)
        self.failUnlessEqual(tuple(a.tolist()), v.value)

    def test_float_array(self):
        import array
        a = array.array("f", (3.14, 2.78))
        v = VARIANT(a)
        self.failUnlessEqual(v.vt, VT_ARRAY | VT_R4)
        self.failUnlessEqual(tuple(a.tolist()), v.value)

    def test_2dim_array(self):
        data = ((1, 2, 3, 4),
                (5, 6, 7, 8),
                (9, 10, 11, 12))
        from comtypes.safearray import SafeArray_FromSequence, UnpackSafeArray
        a = SafeArray_FromSequence(data)
        self.failUnlessEqual(UnpackSafeArray(a), data)

if __name__ == "__main__":
    unittest.main()
