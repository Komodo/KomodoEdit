import os
import unittest as ut
from ctypes import POINTER, byref
from comtypes import GUID, COMError
from comtypes.automation import DISPATCH_METHOD
from comtypes.typeinfo import LoadTypeLibEx, LoadRegTypeLib, \
     QueryPathOfRegTypeLib, TKIND_INTERFACE, TKIND_DISPATCH, TKIND_ENUM

# We should add other test cases for Windows CE.
if os.name == "nt":
    class Test(ut.TestCase):
        # No LoadTypeLibEx on windows ce
        def test_LoadTypeLibEx(self):
            # IE 6 uses shdocvw.dll, IE 7 uses ieframe.dll
            if os.path.exists(os.path.join(os.environ["SystemRoot"],
                                           "system32", "ieframe.dll")):
                dllname = "ieframe.dll"
            else:
                dllname = "shdocvw.dll"

            self.assertRaises(WindowsError, lambda: LoadTypeLibEx("<xxx.xx>"))
            tlib = LoadTypeLibEx(dllname)
            self.failUnless(tlib.GetTypeInfoCount())
            tlib.GetDocumentation(-1)
            self.failUnlessEqual(tlib.IsName("iwebbrowser"), "IWebBrowser")
            self.failUnlessEqual(tlib.IsName("IWEBBROWSER"), "IWebBrowser")
            self.failUnless(tlib.FindName("IWebBrowser"))
            self.failUnlessEqual(tlib.IsName("Spam"), None)
            tlib.GetTypeComp()

            attr = tlib.GetLibAttr()
            info = attr.guid, attr.wMajorVerNum, attr.wMinorVerNum
            other_tlib = LoadRegTypeLib(*info)
            self.failUnlessEqual(tlib, other_tlib)

    ##         for n in dir(attr):
    ##             if not n.startswith("_"):
    ##                 print "\t", n, getattr(attr, n)

            for i in range(tlib.GetTypeInfoCount()):
                ti = tlib.GetTypeInfo(i)
                ti.GetTypeAttr()
                tlib.GetDocumentation(i)
                tlib.GetTypeInfoType(i)

                c_tlib, index = ti.GetContainingTypeLib()
                self.failUnlessEqual(c_tlib, tlib)
                self.failUnlessEqual(index, i)

            guid_null = GUID()
            self.assertRaises(COMError, lambda: tlib.GetTypeInfoOfGuid(guid_null))

            self.failUnless(tlib.GetTypeInfoOfGuid(GUID("{EAB22AC1-30C1-11CF-A7EB-0000C05BAE0B}")))

            path = QueryPathOfRegTypeLib(*info)
            path = path.split("\0")[0]
            self.failUnless(path.lower().endswith(dllname))

        def test_TypeInfo(self):
            tlib = LoadTypeLibEx("shdocvw.dll")
            for index in range(tlib.GetTypeInfoCount()):
                ti = tlib.GetTypeInfo(index)
                ta = ti.GetTypeAttr()
                ti.GetDocumentation(-1)
                if ta.typekind in (TKIND_INTERFACE, TKIND_DISPATCH):
                    if ta.cImplTypes:
                        href = ti.GetRefTypeOfImplType(0)
                        base = ti.GetRefTypeInfo(href)
                        base.GetDocumentation(-1)
                        ti.GetImplTypeFlags(0)
                for f in range(ta.cFuncs):
                    fd = ti.GetFuncDesc(f)
                    names = ti.GetNames(fd.memid, 32)
                    ti.GetIDsOfNames(*names)
                    ti.GetMops(fd.memid)

                for v in range(ta.cVars):
                    ti.GetVarDesc(v)

if __name__ == "__main__":
    unittest.main()
