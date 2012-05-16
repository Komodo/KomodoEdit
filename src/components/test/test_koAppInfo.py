import os
from os.path import abspath, basename, dirname, exists, join, split
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

    @property
    def freshAppInfo(self):
        return Cc["@activestate.com/koAppInfoEx?app=%s;1" % (self.lang)].\
                createInstance(Ci.koIAppInfoEx)

    @property
    def cachedAppInfo(self):
        if self._cachedAppInfo is None:
            self._cachedAppInfo = self.freshAppInfo
        return self._cachedAppInfo

    def _getPathsForInterpreters(self, interpNames):
        exe_paths = []
        possible_paths = koprocessutils.getUserEnv()["PATH"].split(os.pathsep)
        for interpName in interpNames:
            if sys.platform.startswith("win"):
                interpName += ".exe"
            for dirpath in possible_paths:
                exe = join(dirpath, interpName)
                if exists(exe) and exe not in exe_paths:
                    exe_paths.append(exe)
        return exe_paths

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
        self.assertEqual(self.freshAppInfo.executablePath, expected_executablePath)
        self.assertEqual(self.cachedAppInfo.executablePath, expected_executablePath)
        self.assertEqual(self.freshAppInfo.installationPath, expected_installationPath)
        self.assertEqual(self.cachedAppInfo.installationPath, expected_installationPath)

        # Set the pref and then check it.
        expected_executablePath = abspath(__file__)
        expected_installationPath = dirname(expected_executablePath)
        self.prefs.setStringPref(self.defaultInterpreterPrefName, expected_executablePath)
        self.assertEqual(self.freshAppInfo.executablePath, expected_executablePath)
        self.assertEqual(self.cachedAppInfo.executablePath, expected_executablePath)
        self.assertEqual(self.freshAppInfo.installationPath, expected_installationPath)
        self.assertEqual(self.cachedAppInfo.installationPath, expected_installationPath)

    def test_FindExecutables(self):
        self.prefs.setStringPref(self.defaultInterpreterPrefName, "")

        # Check it without a default pref.
        exe_paths = self._getPathsForInterpreters(self.exenames)
        self.assertEqual(self.freshAppInfo.FindExecutables(), exe_paths)
        self.assertEqual(self.cachedAppInfo.FindExecutables(), exe_paths)

        # Set the pref and then check it.
        expected_executablePath = abspath(__file__)
        expected_installationPath = dirname(expected_executablePath)
        expected_exe_paths = [expected_executablePath] + exe_paths
        self.prefs.setStringPref(self.defaultInterpreterPrefName, expected_executablePath)
        self.assertEqual(self.freshAppInfo.FindExecutables(), expected_exe_paths)
        self.assertEqual(self.cachedAppInfo.FindExecutables(), expected_exe_paths)

    def test_FindInstallationPaths(self):
        self.prefs.setStringPref(self.defaultInterpreterPrefName, "")

        # Check it without a default pref.
        expected_install_paths = self._getInstallLocationsForInterpreters(self.exenames)
        self.assertEqual(self.freshAppInfo.FindInstallationPaths(), expected_install_paths)
        self.assertEqual(self.cachedAppInfo.FindInstallationPaths(), expected_install_paths)

        # Set the pref and then check it.
        expected_install_paths = [dirname(abspath(__file__))] + expected_install_paths
        self.prefs.setStringPref(self.defaultInterpreterPrefName, abspath(__file__))
        self.assertEqual(self.freshAppInfo.FindInstallationPaths(), expected_install_paths)
        self.assertEqual(self.cachedAppInfo.FindInstallationPaths(), expected_install_paths)

    def test_overiding_executables(self):
        self.prefs.setStringPref(self.defaultInterpreterPrefName, "")

        appInfo = self.freshAppInfo
        original_executablePath = appInfo.executablePath
        original_installationPath = appInfo.installationPath
        expected_executablePath = abspath(__file__)
        expected_installationPath = dirname(expected_executablePath)

        # Override the exe path and then check it.
        appInfo.executablePath = expected_executablePath
        self.assertEqual(appInfo.executablePath, expected_executablePath)
        self.assertEqual(appInfo.installationPath, expected_installationPath)
        # Reset it
        appInfo.executablePath = ""
        self.assertEqual(appInfo.executablePath, original_executablePath)
        self.assertEqual(appInfo.installationPath, original_installationPath)

        # Override the install path and then check it.
        appInfo.installationPath = expected_installationPath
        # Note: The executable path will not have changed, as there will be no
        #       interpreter found in the given install path!
        self.assertEqual(appInfo.executablePath, original_executablePath)
        self.assertEqual(appInfo.installationPath, expected_installationPath)
        # Reset it
        appInfo.executablePath = ""
        self.assertEqual(appInfo.executablePath, original_executablePath)
        self.assertEqual(appInfo.installationPath, original_installationPath)

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

class PythonAppInfoTestCase(_BaseAppInfoTestCase):
    lang = "Python"
    exenames = ["python"]
    defaultInterpreterPrefName = "pythonDefaultInterpreter"

class Python3AppInfoTestCase(_BaseAppInfoTestCase):
    lang = "Python3"
    exenames = ["python3"]
    defaultInterpreterPrefName = "python3DefaultInterpreter"

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
