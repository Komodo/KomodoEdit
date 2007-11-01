import unittest as ut
import comtypes.client
from ctypes import POINTER

# create the typelib wrapper and import it
comtypes.client.GetModule("msscript.ocx")
from comtypes.gen import MSScriptControl

import comtypes.test
comtypes.test.requires("ui")

class Test(ut.TestCase):
    def test_progid(self):
        # create from ProgID
        obj = comtypes.client.CreateObject("MSScriptControl.ScriptControl")
        self.failUnless(isinstance(obj, POINTER(MSScriptControl.IScriptControl)))

    def test_clsid(self):
        # create from the CoClass' clsid
        obj = comtypes.client.CreateObject(MSScriptControl.ScriptControl)
        self.failUnless(isinstance(obj, POINTER(MSScriptControl.IScriptControl)))

    def test_clsid_string(self):
        # create from string clsid
        comtypes.client.CreateObject(unicode(MSScriptControl.ScriptControl._reg_clsid_))
        comtypes.client.CreateObject(str(MSScriptControl.ScriptControl._reg_clsid_))

    def test_remote(self):
        ie = comtypes.client.CreateObject("InternetExplorer.Application",
                                          machine="localhost")
        self.failUnlessEqual(ie.Visible, False)
        ie.Visible = 1
        # on a remote machine, this may not work.  Probably depends on
        # how the server is run.
        self.failUnlessEqual(ie.Visible, True)
        self.failUnlessEqual(0, ie.Quit()) # 0 == S_OK

def test_main():
    from test import test_support
    test_support.run_unittest(Test)

if __name__ == "__main__":
    ut.main()
