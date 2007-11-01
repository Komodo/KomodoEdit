import unittest
from comtypes.safearray import SafeArray_FromSequence
from comtypes.client import CreateObject
from comtypes.client.dynamic import _Dispatch

class Test(unittest.TestCase):
    def test(self):
        d = CreateObject("MSScriptControl.ScriptControl")
        d.Language = "jscript"
        d.AddCode('function x() { return [3, "spam foo", 3.14]; };')
        result = d.Run("x", SafeArray_FromSequence([]))
        self.failUnless(isinstance(result, _Dispatch))
        self.failUnlessEqual(result[0], 3)
        self.failUnlessEqual(result[1], "spam foo")
        self.failUnlessEqual(result[2], 3.14)
        self.assertRaises(IndexError, lambda: result[3])

if __name__ == "__main__":
    unittest.main()
