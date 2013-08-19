from xpcom import components, COMException
from xpcom.server import WrapObject, UnwrapObject
from os.path import abspath, join, split
import inspect, imp, sys
import unittest, testlib
import logging
log = logging.getLogger("TestKoWindowsIntegrationService")

if sys.platform.startswith("win"):
    class TestKoWindowsIntegrationService(unittest.TestCase):
        def __init__(self, methodName):
            unittest.TestCase.__init__(self, methodName)
            self.real_import = __builtins__["__import__"]
            self.winIntegSvc = None

        def setUp(self):
            if not sys.platform.startswith("win"):
                raise testlib.TestSkipped()
            self.winIntegSvc = components.classes["@activestate.com/koWindowsIntegrationService;1"]\
                                         .getService(components.interfaces.koIWindowsIntegrationService)
            sys.path.insert(0, self._libpath)
            try:
                import fake_winreg
            finally:
                sys.path.pop(0)
            self.fakeWinReg = fake_winreg
            self.fakeWinReg.elevated = False
            __builtins__["__import__"] = self.fake_import

        def tearDown(self):
            if not sys.platform.startswith("win"):
                return
            __builtins__["__import__"] = self.real_import
            self.winIntegSvc = None

        @property
        def _libpath(self):
            """ The path needed to be inserted into sys.path to find fake_winreg """
            return join(split(abspath(__file__))[0], "windowsIntegration")

        def fake_import(self, name, *args, **kwargs):
            """Fake __import__ that redirects requests for "_winreg" to the
            "fake_winreg" module
            """
            #print "\nimport %r [%r]\n" % (name, inspect.stack()[1])
            if name == "_winreg":
                caller = split(inspect.stack()[1][1])[-1] # caller frame, file name, leaf
                log.debug("__import__ caller: %s", caller)
                if caller in ("koWindowsIntegration.py", "wininteg.py"):
                    sys.path.insert(0, self._libpath)
                    try:
                        return self.real_import("fake_winreg", *args, **kwargs)
                    finally:
                        sys.path.pop(0)
            return self.real_import(name, *args, **kwargs)

        @property
        def _appName(self):
            """ Getter for the app name """
            return components.classes["@mozilla.org/xre/app-info;1"]\
                             .getService(components.interfaces.nsIXULAppInfo)\
                             .name

        @property
        def _appExe(self):
            """ Getter for the application executable """
            koDirs = components.classes["@activestate.com/koDirs;1"]\
                .getService(components.interfaces.koIDirs)
            exe = join(koDirs.binDir, "komodo.exe")
            if " " in exe:
                exe = '"%s"' % (exe,)
            return exe

        @property
        def _HKLM_edit(self):
            return r"HKLM\Software\ActiveState\Komodo\editAssociations"
        @property
        def _HKLM_editWith(self):
            return r"HKLM\Software\ActiveState\Komodo\editWithAssociations"
        @property
        def _HKCU_edit(self):
            return r"HKCU\Software\ActiveState\%s\editAssociations" % self._appName
        @property
        def _HKCU_editWith(self):
            return r"HKCU\Software\ActiveState\%s\editWithAssociations" % self._appName
        @property
        def _commandLine(self):
            return '%s "%%1" %%*' % (self._appExe,)
        @property
        def _editWith(self):
            return "Edit with %s" % (self._appName,)

        def test_getEditAssociations_empty(self):
            """ Test that having no existing associations works correctly """
            self.fakeWinReg.setData({})
            assoc = self.winIntegSvc.getEditAssociations()
            self.assertEquals(assoc, "")
            assoc = self.winIntegSvc.getEditWithAssociations()
            self.assertEquals(assoc, "")

        def test_getEditAssociations_existing_system(self):
            """ Test that system associations are honoured """
            self.fakeWinReg.setData({self._HKLM_edit: ".pikachu"})
            assoc = self.winIntegSvc.getEditAssociations()
            self.assertEquals(assoc, ".pikachu")
            assoc = self.winIntegSvc.getEditWithAssociations()
            self.assertEquals(assoc, "")

        def test_getEditWithAssociations_existing_system_case(self):
            """ Test that system associations are honoured, case-normalizing """
            self.fakeWinReg.setData({self._HKLM_editWith: ".hello;.WORLD"})
            assoc = self.winIntegSvc.getEditAssociations()
            self.assertEquals(assoc, "")
            assoc = self.winIntegSvc.getEditWithAssociations()
            self.assertEquals(assoc, ".hello;.world")

        def test_getEditAssociations_existing_user_system(self):
            """ Test that user associations win over system associations """
            self.fakeWinReg.setData({self._HKLM_edit: ".pikachu",
                                     self._HKCU_edit: ".foo"})
            assoc = self.winIntegSvc.getEditAssociations()
            self.assertEquals(assoc, ".foo")
            assoc = self.winIntegSvc.getEditWithAssociations()
            self.assertEquals(assoc, "")

        def test_getEditWithAssociations_existing_user_system(self):
            """ Test that existing associations are fetched case-normalizing """
            self.fakeWinReg.setData({self._HKLM_editWith: ".hello;.WORLD",
                                     self._HKCU_editWith: ".bar"})
            assoc = self.winIntegSvc.getEditAssociations()
            self.assertEquals(assoc, "")
            assoc = self.winIntegSvc.getEditWithAssociations()
            self.assertEquals(assoc, ".bar")

        def test_setEditAssociations_clean(self):
            """ Test that setting associations are correct with no existing data """
            self.fakeWinReg.setData({})
            self.winIntegSvc.setEditAssociations(".pikachu")
            self.assertEquals(self.fakeWinReg.getData(), {
                r'HKCU\Software\Classes\.pikachu''\\': 'PIKACHUFile',
                r'HKCU\Software\Classes\PIKACHUFile\shell\Edit\command''\\': self._commandLine,
                self._HKCU_edit: ".pikachu"})

        def test_setEditAssociations_customType(self):
            """ Test that we correctly handle extensions with an existing custom type """
            self.fakeWinReg.setData({
                r'HKLM\Software\Classes\.hello''\\': 'hello_auto_file'})
            self.winIntegSvc.setEditAssociations(".hello")
            self.assertEquals(self.fakeWinReg.getData(), {
                r'HKLM\Software\Classes\.hello''\\': 'hello_auto_file',
                r'HKCU\Software\Classes\hello_auto_file\shell\Edit\command''\\': self._commandLine,
                self._HKCU_edit: ".hello"})

        def test_setEditWithAssociations_existing_user(self):
            """ Test that we correctly remove existing HKCU-based associations """
            self.fakeWinReg.setData({
                r'HKCU\Software\Classes\.pants''\\': "pantaloons",
                r'HKCU\Software\Classes\pantaloons\shell\Edit''\\': self._editWith,
                r'HKCU\Software\Classes\pantaloons\shell\Edit\command''\\': self._commandLine,
                self._HKCU_editWith: ".pants"})
            self.winIntegSvc.setEditWithAssociations(".fjords")
            self.assertEquals(self.fakeWinReg.getData(), {
                r'HKCU\Software\Classes\.fjords''\\': "FJORDSFile",
                r'HKCU\Software\Classes\FJORDSFile\shell\Edit''\\': self._editWith,
                r'HKCU\Software\Classes\FJORDSFile\shell\Edit\command''\\': self._commandLine,
                self._HKCU_editWith: ".fjords"})

        def test_setEditWithAssociations_existing_system_other(self):
            """ Test that we handle having existing HKLM-based commands gracefully """
            self.fakeWinReg.setData({
                r'HKLM\Software\Classes\.moo''\\': 'silly_walks',
                r'HKLM\Software\Classes\silly_walks\shell\Edit\command''\\': 'pants'})
            self.winIntegSvc.setEditWithAssociations(".moo")
            self.assertEquals(self.fakeWinReg.getData(), {
                r'HKLM\Software\Classes\.moo''\\': 'silly_walks',
                r'HKLM\Software\Classes\silly_walks\shell\Edit\command''\\': 'pants',
                r'HKCU\Software\Classes\silly_walks\shell\Edit2''\\': self._editWith,
                r'HKCU\Software\Classes\silly_walks\shell\Edit2\command''\\': self._commandLine,
                self._HKCU_editWith: ".moo"})

        def test_setEditAssociations_existing_system_elevated(self):
            """ Test that we attempt to remove old HKLM-based associations when elevated """
            self.fakeWinReg.elevated = True
            self.fakeWinReg.setData({
                r'HKLM\Software\Classes\.rabbit''\\': 'vicious',
                r'HKLM\Software\Classes\vicious\shell\Edit\command''\\': self._commandLine,
                self._HKLM_edit: ".rabbit"})
            self.winIntegSvc.setEditAssociations(".coconuts")
            self.assertEquals(self.fakeWinReg.getData(), {
                r'HKCU\Software\Classes\.coconuts''\\': 'COCONUTSFile',
                r'HKCU\Software\Classes\COCONUTSFile\shell\Edit\command''\\': self._commandLine,
                self._HKCU_edit: ".coconuts"})

        def test_setEditAssociations_existing_system_no_permissions(self):
            """ Test that attempting to change existing system permissions when not elevated fails """
            self.fakeWinReg.setData({
                r'HKLM\Software\Classes\.rabbit''\\': 'vicious',
                r'HKLM\Software\Classes\vicious\shell\Edit\command''\\': self._commandLine,
                self._HKLM_edit: ".rabbit"})
            self.assertRaises(COMException, self.winIntegSvc.setEditAssociations, ".coconuts")
            self.assertEquals(self.fakeWinReg.getData(), {
                r'HKLM\Software\Classes\.rabbit''\\': 'vicious',
                r'HKLM\Software\Classes\vicious\shell\Edit\command''\\': self._commandLine,
                self._HKLM_edit: ".rabbit"})

        def test_setEditWithAssociations_existing_system_migrate_no_permissions(self):
            """ Test attempting to migrate existing Edit With associations without permissions """
            self.fakeWinReg.setData({
                r'HKLM\Software\Classes\.ni''\\': 'flesh_wound',
                r'HKLM\Software\Classes\flesh_wound\shell\Edit''\\': 'Edit with Komodo',
                r'HKLM\Software\Classes\flesh_wound\shell\Edit\command''\\': self._commandLine,
                self._HKLM_editWith: ".ni"})
            self.winIntegSvc.setEditWithAssociations(".ni")
            self.assertEquals(self.fakeWinReg.getData(), {
                r'HKLM\Software\Classes\.ni''\\': 'flesh_wound',
                r'HKLM\Software\Classes\flesh_wound\shell\Edit''\\': 'Edit with Komodo',
                r'HKLM\Software\Classes\flesh_wound\shell\Edit\command''\\': self._commandLine,
                self._HKCU_editWith: ".ni",
                self._HKLM_editWith: ".ni"})

        def test_setEditWithAssociations_existing_system_migrate_yes_permissions(self):
            """ Test attempting to migrate existing Edit With associations with permissions """
            self.fakeWinReg.elevated = True
            self.fakeWinReg.setData({
                r'HKLM\Software\Classes\.ni''\\': 'flesh_wound',
                r'HKLM\Software\Classes\flesh_wound\shell\Edit''\\': 'Edit with Komodo',
                r'HKLM\Software\Classes\flesh_wound\shell\Edit\command''\\': self._commandLine,
                self._HKLM_editWith: ".ni"})
            self.winIntegSvc.setEditWithAssociations(".ni")
            self.assertEquals(self.fakeWinReg.getData(), {
                r'HKCU\Software\Classes\.ni''\\': 'NIFile',
                r'HKCU\Software\Classes\NIFile\shell\Edit''\\': self._editWith,
                r'HKCU\Software\Classes\NIFile\shell\Edit\command''\\': self._commandLine,
                self._HKCU_editWith: ".ni"})


    #---- mainline

    def suite():
        return unittest.makeSuite(TestKoWindowsIntegrationService)

    def test_main():
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite())

    if __name__ == "__main__":
        test_main()
