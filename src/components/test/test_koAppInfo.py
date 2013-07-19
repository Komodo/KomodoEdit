import os
from os.path import abspath, basename, dirname, exists, join, split, normcase, normpath
import sys
import unittest

from xpcom import components, COMException, nsError
from xpcom.server import UnwrapObject

import which
import koprocessutils

Cc = components.classes
Ci = components.interfaces

class _BaseAppInfoTestCase(unittest.TestCase):

    lang = ""
    exenames = []
    _cachedAppInfo = None

    def assertFilepathsEqual(self, p1, p2):
        if sys.platform == "win32":
            if isinstance(p1, (list, tuple)):
                p1 = [normcase(normpath(x)) for x in p1]
                p2 = [normcase(normpath(x)) for x in p2]
            else:
                assert isinstance(p1, (str, unicode))
                p1 = normcase(normpath(p1))
                p2 = normcase(normpath(p2))
        self.assertEqual(p1, p2)

    @property
    def freshAppInfo(self):
        return Cc["@activestate.com/koAppInfoEx?app=%s;1" % (self.lang)].\
                createInstance(Ci.koIAppInfoEx)

    @property
    def cachedAppInfo(self):
        if self._cachedAppInfo is None:
            self._cachedAppInfo = self.freshAppInfo
        return self._cachedAppInfo

    def _getExecutableFromRegistry(self, exeName):
        """Windows allow application paths to be registered in the registry."""
        import _winreg
        try:
            key = "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\" +\
                  exeName
            registered = _winreg.QueryValue(_winreg.HKEY_LOCAL_MACHINE, key)
            if registered and os.path.exists(registered):
                return registered
        except _winreg.error:
            pass
        return None

    def _getPathsForInterpreters(self, interpNames):
        from testsupport import findPathsForInterpreters
        return findPathsForInterpreters(interpNames, lang=self.lang,
                                        env=koprocessutils.getUserEnv())

    def _getInstallLocationsForInterpreters(self, interpNames):
        def getInstallDir(exepath):
            installdir = dirname(exepath)
            if basename(installdir) == "bin":
                installdir = dirname(installdir)
            return installdir
        return map(getInstallDir, self._getPathsForInterpreters(interpNames))

    _prefs = None
    @property
    def prefs(self):
        if self._prefs is None:
            self._prefs = Cc["@activestate.com/koPrefService;1"].\
                            getService(Ci.koIPrefService).prefs
        return self._prefs

    def _getEncodedUserEnv(self):
        env = koprocessutils.getUserEnv()
        encoding = sys.getfilesystemencoding()
        _enc_env = {}
        for key, value in env.items():
            try:
                _enc_env[key.encode(encoding)] = value.encode(encoding)
            except UnicodeEncodeError:
                pass
        return _enc_env

    def test_basics(self):
        self.prefs.setStringPref(self.defaultInterpreterPrefName, "")

        # Check it without a default pref.
        exe_paths = self._getPathsForInterpreters(self.exenames)
        expected_executablePath = ""
        expected_installationPath = ""
        if exe_paths:
            expected_executablePath = exe_paths[0]
            expected_installationPath = dirname(expected_executablePath)
            if basename(expected_installationPath) == "bin":
                expected_installationPath = dirname(expected_installationPath)
        self.assertFilepathsEqual(self.freshAppInfo.executablePath, expected_executablePath)
        self.assertFilepathsEqual(self.cachedAppInfo.executablePath, expected_executablePath)
        self.assertFilepathsEqual(self.freshAppInfo.installationPath, expected_installationPath)
        self.assertFilepathsEqual(self.cachedAppInfo.installationPath, expected_installationPath)

        # Set the pref and then check it.
        expected_executablePath = normcase(normpath(abspath(__file__)))
        expected_installationPath = dirname(expected_executablePath)
        self.prefs.setStringPref(self.defaultInterpreterPrefName, expected_executablePath)
        self.assertFilepathsEqual(self.freshAppInfo.executablePath, expected_executablePath)
        self.assertFilepathsEqual(self.cachedAppInfo.executablePath, expected_executablePath)
        self.assertFilepathsEqual(self.freshAppInfo.installationPath, expected_installationPath)
        self.assertFilepathsEqual(self.cachedAppInfo.installationPath, expected_installationPath)

    def test_FindExecutables(self):
        self.prefs.setStringPref(self.defaultInterpreterPrefName, "")

        # Check it without a default pref.
        exe_paths = self._getPathsForInterpreters(self.exenames)
        self.assertFilepathsEqual(self.freshAppInfo.FindExecutables(), exe_paths)
        self.assertFilepathsEqual(self.cachedAppInfo.FindExecutables(), exe_paths)

        # Set the pref and then check it.
        expected_executablePath = normcase(normpath(abspath(__file__)))
        expected_installationPath = dirname(expected_executablePath)
        expected_exe_paths = [expected_executablePath] + exe_paths
        self.prefs.setStringPref(self.defaultInterpreterPrefName, expected_executablePath)
        self.assertFilepathsEqual(self.freshAppInfo.FindExecutables(), expected_exe_paths)
        self.assertFilepathsEqual(self.cachedAppInfo.FindExecutables(), expected_exe_paths)

    def test_FindExecutablesAsync(self):
        import time
        import threading
        self.prefs.setStringPref(self.defaultInterpreterPrefName, "")

        # Check it without a default pref.
        exe_paths = self._getPathsForInterpreters(self.exenames)
        results = {}
        event = threading.Event()
        def callback(result, data):
            results["result"] = result
            results["exe_paths"] = data
            event.set()
        def wait(timeout=None):
            # Process pending Mozilla events in order to receive the observer
            # notifications, based on Mozilla xpcshell test class here:
            # http://mxr.mozilla.org/mozilla-central/source/testing/xpcshell/head.js#75
            currentThread = components.classes["@mozilla.org/thread-manager;1"] \
                                .getService().currentThread
            start_time = time.time()
            while 1:
                if timeout is not None:
                    if (time.time() - start_time) > timeout:
                        break
                # Give some time to gather more events.
                event.wait(0.1)
                if event.isSet():
                    break
                # Process events, such as the pending observer notifications.
                while currentThread.hasPendingEvents():
                    currentThread.processNextEvent(True)

        event.clear()
        results.clear()
        self.freshAppInfo.FindExecutablesAsync(callback)
        wait(30)
        self.assertEqual(components.interfaces.koIAsyncCallback.RESULT_SUCCESSFUL, results.get("result", -1))
        self.assertFilepathsEqual(exe_paths, results.get("exe_paths"))

        event.clear()
        results.clear()
        self.cachedAppInfo.FindExecutablesAsync(callback)
        wait(30)
        self.assertEqual(components.interfaces.koIAsyncCallback.RESULT_SUCCESSFUL, results.get("result", -1))
        self.assertFilepathsEqual(exe_paths, results.get("exe_paths"))

        # Set the pref and then check it.
        expected_executablePath = normcase(normpath(abspath(__file__)))
        expected_installationPath = dirname(expected_executablePath)
        expected_exe_paths = [expected_executablePath] + exe_paths
        self.prefs.setStringPref(self.defaultInterpreterPrefName, expected_executablePath)

        event.clear()
        results.clear()
        self.freshAppInfo.FindExecutablesAsync(callback)
        wait(30)
        self.assertEqual(components.interfaces.koIAsyncCallback.RESULT_SUCCESSFUL, results.get("result", -1))
        self.assertFilepathsEqual(expected_exe_paths, results.get("exe_paths"))

        event.clear()
        results.clear()
        self.cachedAppInfo.FindExecutablesAsync(callback)
        wait(30)
        self.assertEqual(components.interfaces.koIAsyncCallback.RESULT_SUCCESSFUL, results.get("result", -1))
        self.assertFilepathsEqual(expected_exe_paths, results.get("exe_paths"))

    def test_FindInstallationPaths(self):
        self.prefs.setStringPref(self.defaultInterpreterPrefName, "")

        # Check it without a default pref.
        expected_install_paths = self._getInstallLocationsForInterpreters(self.exenames)
        self.assertFilepathsEqual(self.freshAppInfo.FindInstallationPaths(), expected_install_paths)
        self.assertFilepathsEqual(self.cachedAppInfo.FindInstallationPaths(), expected_install_paths)

        # Set the pref and then check it.
        expected_install_paths = [dirname(abspath(__file__))] + expected_install_paths
        self.prefs.setStringPref(self.defaultInterpreterPrefName, abspath(__file__))
        self.assertFilepathsEqual(self.freshAppInfo.FindInstallationPaths(), expected_install_paths)
        self.assertFilepathsEqual(self.cachedAppInfo.FindInstallationPaths(), expected_install_paths)

    def test_overiding_executables(self):
        self.prefs.setStringPref(self.defaultInterpreterPrefName, "")

        appInfo = self.freshAppInfo
        original_executablePath = appInfo.executablePath
        original_installationPath = appInfo.installationPath
        expected_executablePath = abspath(__file__)
        expected_installationPath = dirname(expected_executablePath)

        # Override the exe path and then check it.
        appInfo.executablePath = expected_executablePath
        self.assertFilepathsEqual(appInfo.executablePath, expected_executablePath)
        self.assertFilepathsEqual(appInfo.installationPath, expected_installationPath)
        # Reset it
        appInfo.executablePath = ""
        self.assertFilepathsEqual(appInfo.executablePath, original_executablePath)
        self.assertFilepathsEqual(appInfo.installationPath, original_installationPath)

        # Override the install path and then check it.
        appInfo.installationPath = expected_installationPath
        # Note: The executable path will not have changed, as there will be no
        #       interpreter found in the given install path!
        self.assertFilepathsEqual(appInfo.executablePath, original_executablePath)
        self.assertFilepathsEqual(appInfo.installationPath, expected_installationPath)
        # Reset it
        appInfo.executablePath = ""
        self.assertFilepathsEqual(appInfo.executablePath, original_executablePath)
        self.assertFilepathsEqual(appInfo.installationPath, original_installationPath)

    def test_getVersionForBinary(self):
        self.prefs.setStringPref(self.defaultInterpreterPrefName, "")

        # We arn't actually testing anything here, we just make sure the code
        # executes with/out exceptions.
        appInfo = self.freshAppInfo
        exe = appInfo.executablePath
        if exe:
            self.assertEqual(appInfo.getVersionForBinary(exe), appInfo.version)
        #else:
        #    self.failUnlessRaises(appInfo.getVersionForBinary(exe))

    def test_valid_version(self):
        self.prefs.setStringPref(self.defaultInterpreterPrefName, "")

        appInfo = self.freshAppInfo
        exe = appInfo.executablePath
        if exe:
            self.assertTrue(appInfo.valid_version)

class _PythonAppInfoTestCase(_BaseAppInfoTestCase):
    def setUp(self):
        self._pyHomeOriginal = koprocessutils._gUserEnvCache.get("PYTHONHOME")
        if self._pyHomeOriginal:
            koprocessutils._gUserEnvCache.pop("PYTHONHOME")

    def tearDown(self):
        if self._pyHomeOriginal:
            koprocessutils._gUserEnvCache["PYTHONHOME"] = self._pyHomeOriginal
            self._pyHomeOriginal = None

class PythonAppInfoTestCase(_PythonAppInfoTestCase):
    lang = "Python"
    exenames = ["python", "python2"]
    defaultInterpreterPrefName = "pythonDefaultInterpreter"

    def test_python2_over_python3(self):
        self.prefs.setStringPref(self.defaultInterpreterPrefName, "")
        cachedInfo = self.cachedAppInfo
        py2 = self.freshAppInfo
        py3 = Cc["@activestate.com/koAppInfoEx?app=Python3;1"].\
                createInstance(Ci.koIAppInfoEx)
        py2exe = py2.executablePath
        py3exe = py3.executablePath
        if py2exe and py3exe:
            self.assertTrue(py2.valid_version)
            self.assertTrue(py3.valid_version)
            orig_path = koprocessutils._gUserEnvCache.get("PATH", "")
            try:
                # Stick py3 at the start of the path.
                new_path = dirname(py3exe) + os.pathsep + orig_path
                appInfo = self.freshAppInfo
                self.assertFilepathsEqual(appInfo.executablePath, py2exe)
                self.assertTrue(appInfo.valid_version)
                # Make sure nothing changed with py3.
                py3appInfo = Cc["@activestate.com/koAppInfoEx?app=Python3;1"].\
                        createInstance(Ci.koIAppInfoEx)
                self.assertFilepathsEqual(py3appInfo.executablePath, py3exe)
                self.assertTrue(py3appInfo.valid_version)
            finally:
                koprocessutils._gUserEnvCache["PATH"] = orig_path
            # Ensure the cached one still has the same executable.
            self.assertFilepathsEqual(cachedInfo.executablePath, py2exe)
        else:
            self.skip("Could not find both Python2 and Python3 executables")

class Python3AppInfoTestCase(_PythonAppInfoTestCase):
    lang = "Python3"
    exenames = ["python3", "python"]
    defaultInterpreterPrefName = "python3DefaultInterpreter"

    def test_python3_over_python2(self):
        self.prefs.setStringPref(self.defaultInterpreterPrefName, "")
        cachedInfo = self.cachedAppInfo
        py2 = Cc["@activestate.com/koAppInfoEx?app=Python;1"].\
                createInstance(Ci.koIAppInfoEx)
        py3 = self.freshAppInfo
        py2exe = py2.executablePath
        py3exe = py3.executablePath
        if py2exe and py3exe:
            self.assertTrue(py2.valid_version)
            self.assertTrue(py3.valid_version)
            orig_path = koprocessutils._gUserEnvCache.get("PATH", "")
            try:
                # Stick py2 at the start of the path.
                new_path = dirname(py2exe) + os.pathsep + orig_path
                appInfo = self.freshAppInfo
                self.assertFilepathsEqual(appInfo.executablePath, py3exe)
                self.assertTrue(appInfo.valid_version)
                # Make sure nothing changed with py2.
                py2appInfo = Cc["@activestate.com/koAppInfoEx?app=Python;1"].\
                        createInstance(Ci.koIAppInfoEx)
                self.assertFilepathsEqual(py2appInfo.executablePath, py2exe)
                self.assertTrue(py2appInfo.valid_version)
            finally:
                koprocessutils._gUserEnvCache["PATH"] = orig_path
            # Ensure the cached one still has the same executable.
            self.assertFilepathsEqual(cachedInfo.executablePath, py3exe)
        else:
            self.skip("Could not find both Python2 and Python3 executables")

class PHPAppInfoTestCase(_BaseAppInfoTestCase):
    lang = "PHP"
    exenames = ["php", "php-cli", "php-cgi"]
    defaultInterpreterPrefName = "phpDefaultInterpreter"

class RubyAppInfoTestCase(_BaseAppInfoTestCase):
    lang = "Ruby"
    exenames = ["ruby"]
    defaultInterpreterPrefName = "rubyDefaultInterpreter"

class PerlAppInfoTestCase(_BaseAppInfoTestCase):
    lang = "Perl"
    exenames = ["perl"]
    defaultInterpreterPrefName = "perlDefaultInterpreter"

    def test_haveModules(self):
        self.prefs.setStringPref(self.defaultInterpreterPrefName, "")

        appInfo = self.freshAppInfo
        exe = appInfo.executablePath
        if exe:
            try:
                self.assertFalse(appInfo.haveModules(["foozball22"]))
            except COMException, ex:
                if ex.errno != nsError.NS_ERROR_NOT_IMPLEMENTED:
                    raise

        appInfo = self.freshAppInfo
        exe = appInfo.executablePath
        if exe:
            self.assertTrue(appInfo.haveModules(["Socket", "warnings"]))

class NodejsAppInfoTestCase(_BaseAppInfoTestCase):
    lang = "NodeJS"
    exenames = ["node"]
    defaultInterpreterPrefName = "nodejsDefaultInterpreter"

class TclAppInfoTestCase(_BaseAppInfoTestCase):
    lang = "Tcl"
    exenames = ["tclsh"]
    defaultInterpreterPrefName = "tclshDefaultInterpreter"
