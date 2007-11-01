import glob
import os
import unittest
import warnings
import comtypes.typeinfo
import comtypes.client
import comtypes.client._generate
from comtypes.test import requires

requires("typelibs")

# filter warnings about interfaces without a base interface; they will
# be skipped in the code generation.
warnings.filterwarnings("ignore",
                        "Ignoring interface .* which has no base interface",
                        UserWarning)

# don't print messages when typelib wrappers are generated
comtypes.client._generate.__verbose__ = False

sysdir = os.path.join(os.environ["SystemRoot"], "system32")

progdir = os.environ["ProgramFiles"]

# This test takes quite some time.  It tries to build wrappers for ALL
# .dll, .tlb, and .ocx files in the system directory which contain typelibs.

class Test(unittest.TestCase):
    def setUp(self):
        "Do not write the generated files into the comtypes.gen directory"
        comtypes.client.gen_dir = None

    def tearDown(self):
        comtypes.client.gen_dir = comtypes.client._find_gen_dir()
    
number = 0

def add_test(fname):
    global number
    def test(self):
        try:
            comtypes.typeinfo.LoadTypeLibEx(fname)
        except WindowsError:
            return
        comtypes.client.GetModule(fname)

    test.__doc__ = "test GetModule(%r)" % fname
    setattr(Test, "test_%d" % number, test)
    number += 1

for fname in glob.glob(os.path.join(sysdir, "*.ocx")):
    add_test(fname)

for fname in glob.glob(os.path.join(sysdir, "*.tlb")):
    add_test(fname)

for fname in glob.glob(os.path.join(progdir, r"Microsoft Office\Office*\*.tlb")):
    add_test(fname)

for fname in glob.glob(os.path.join(progdir, r"Microsoft Office\Office*\*.olb")):
    add_test(fname)

for fname in glob.glob(os.path.join(sysdir, "*.dll")):
    # these typelibs give errors:
    if os.path.basename(fname).lower() in (
        "syncom.dll", # interfaces without base interface
        "msvidctl.dll", # assignment to None
        "scardssp.dll", # assertionerror sizeof()
        "sccsccp.dll", # assertionerror sizeof()

        # Typeinfo in comsvcs.dll in XP 64-bit SP 1 is broken.
        # Oleview decompiles this code snippet (^ marks are m):
        #[
        #  odl,
        #  uuid(C7B67079-8255-42C6-9EC0-6994A3548780)
        #]
        #interface IAppDomainHelper : IDispatch {
        #    HRESULT _stdcall pfnShutdownCB(void* pv);
        #    HRESULT _stdcall Initialize(
        #                    [in] IUnknown* pUnkAD, 
        #                    [in] IAppDomainHelper __MIDL_0028, 
        #                         ^^^^^^^^^^^^^^^^
        #                    [in] void* pPool);
        #    HRESULT _stdcall pfnCallbackCB(void* pv);
        #    HRESULT _stdcall DoCallback(
        #                    [in] IUnknown* pUnkAD, 
        #                    [in] IAppDomainHelper __MIDL_0029, 
        #                         ^^^^^^^^^^^^^^^^
        #                    [in] void* pPool);
        #};
        "comsvcs.dll", 
        ):
        continue
    add_test(fname)

if __name__ == "__main__":
    unittest.main()
