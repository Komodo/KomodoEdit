#---- self test code
# "bk start src/components/test/test_koEnviron.py" to run it. Requires Python
# 2.1 or at least requires PyUnit on the PythonPath.

import os
import unittest
import sys
import locale

from xpcom import components, COMException
from xpcom.server import UnwrapObject

# Hack around xpcom to setup the class.
def KoUserEnviron(startupEnvFileName=None):
    koEnviron = components.classes[ "@activestate.com/koUserEnviron;1"] \
                .createInstance(components.interfaces.koIUserEnviron)
    if startupEnvFileName:
        environ = UnwrapObject(koEnviron)
        environ.__init__(startupEnvFileName)
        current_encoding = locale.getlocale()[1]
        # For some reason this can be the value 'None' when running in
        # the pyxpcom test suite, so fall back to the expected default
        # platform encoding.
        if not current_encoding:
            if sys.platform.startswith('win'):
                current_encoding = 'mbcs'
            elif sys.platform.startswith('darwin'):
                current_encoding = 'mac-roman'
            elif sys.platform.startswith('linux'):
                current_encoding = 'utf-8'
        environ.startupEnvironEncoding = current_encoding

    return koEnviron

def KoEnvironUtils():
    return components.classes[ "@activestate.com/koEnvironUtils;1"] \
            .getService(components.interfaces.koIEnvironUtils)

class UserEnvironParsingTestCase(unittest.TestCase):
    def _GetUserEnviron(self, content):
        import tempfile
        tmpFileName = tempfile.mktemp()
        tmpFile = open(tmpFileName, "w")
        tmpFile.write(content)
        tmpFile.close()
        return KoUserEnviron(tmpFileName)

    def test_simple(self):
        userEnviron = self._GetUserEnviron("FOO=bar")
        self.assert_(userEnviron.has("FOO"))
        self.assertEqual(userEnviron.get("FOO"), "bar")

    def test_spaces(self):
        # this should only be possible on windows
        if sys.platform.startswith("win"):
            userEnviron = self._GetUserEnviron("FOO =bar")
            self.assert_(userEnviron.has("FOO "))
            self.assertEqual(userEnviron.get("FOO "), "bar")

    def test_leading_semicolon(self):
        # This should only be possible on windows. This sort of this
        # should just be skipped as it is obviously an error in the users
        # environment.
        if sys.platform.startswith("win"):
            userEnviron = self._GetUserEnviron(";Path=blah")
            self.assert_(not userEnviron.has("Path"))
            self.assert_(userEnviron.has(";Path"))

    def test_quotes(self):
        userEnviron = self._GetUserEnviron('FOO=bar;"spam";"eggs and ham"')
        self.assert_(userEnviron.has("FOO"))
        self.assertEqual(userEnviron.get("FOO"),
                         'bar;"spam";"eggs and ham"')

    def test_merge_simple1(self):
        utils = KoEnvironUtils()
        base = ["MOZ_BITS=32"]
        diff = ["MOZ_BITS=52"]
        merged = utils.MergeEnvironmentStrings(base, diff)
        self.assert_("MOZ_BITS=52" in merged)

    def test_merge_simple2(self):
        utils = KoEnvironUtils()
        base = ["MOZ_BITS=32", "FOO=bar"]
        diff = ["MOZ_BITS=52"]
        merged = utils.MergeEnvironmentStrings(base, diff)
        self.assert_("MOZ_BITS=52" in merged)

    def test_merge_interpolate1(self):
        utils = KoEnvironUtils()
        base = ["MOZ_BITS=32", "FOO=bar"]
        if sys.platform.startswith("win"):
            diff = ["MOZ_BITS=MOZ_BITS was %MOZ_BITS%"]
        else:
            diff = ["MOZ_BITS=MOZ_BITS was $MOZ_BITS"]
        merged = utils.MergeEnvironmentStrings(base, diff)
        self.assert_("MOZ_BITS=MOZ_BITS was 32" in merged)

    def test_merge_interpolate2(self):
        utils = KoEnvironUtils()
        base = ["MOZ_BITS=32", "FOO=bar"]
        if sys.platform.startswith("win"):
            diff = ["MOZ_BITS=MOZ_BITS was %MOZ_BITS%"]
        else:
            # different interp form than for test_merge_interpolate1()
            diff = ["MOZ_BITS=MOZ_BITS was $(MOZ_BITS)"]
        merged = utils.MergeEnvironmentStrings(base, diff)
        self.assert_("MOZ_BITS=MOZ_BITS was 32" in merged)

    def test_merge_interpolate3(self):
        # interpolating an undefined variable
        utils = KoEnvironUtils()
        base = ["MOZ_BITS=32", "FOO=bar"]
        if sys.platform.startswith("win"):
            diff = ["MOZ_BITS=MOZ_BITS was not %MOZ_NOTDEFINED%"]
        else:
            diff = ["MOZ_BITS=MOZ_BITS was not $(MOZ_NOTDEFINED)"]
        merged = utils.MergeEnvironmentStrings(base, diff)
        # koEnviron will leave an undefined variable as is.
        #self.assert_("MOZ_BITS=MOZ_BITS was not " in merged)
        self.assert_(diff[0] in merged)

    def test_environment_function1(self):
        if sys.platform.startswith("win"): return
        # Data is from bug
        # http://bugs.activestate.com/show_bug.cgi?id=18855
        envStrings = """
LC_COLLATE=en_US
CURRENT_PROJECT=ADB-QA
mc=() {  mkdir -p $HOME/.mc/tmp 2>/dev/null;
 chmod 700 $HOME/.mc/tmp;
 MC=$HOME/.mc/tmp/mc-$$;
 /usr/bin/mc -P "$@" >"$MC";
 cd "`cat $MC`";
 rm -i -f "$MC";
 unset MC
}
_=./komodo
"""
        userEnviron = self._GetUserEnviron(envStrings)
        self.assert_(userEnviron.has("LC_COLLATE"))
        self.assertEqual(userEnviron.get("LC_COLLATE"), 'en_US')
        # "_" is always removed from the environment by Komodo
        #self.assert_(userEnviron.has("_"))
        #self.assertEqual(userEnviron.get("_"), './komodo')
        self.assert_(not userEnviron.has("_"))

    def test_environment_function2(self):
        if sys.platform.startswith("win"): return
        # This is the way *my* bash shows defined functions.
        envStrings = """
LC_COLLATE=en_US
CURRENT_PROJECT=ADB-QA
mc=()
{
    echo hello;
    ls --color=auto ~;
    echo bye
}
_=./komodo
"""
        userEnviron = self._GetUserEnviron(envStrings)
        self.assert_(userEnviron.has("LC_COLLATE"))
        self.assertEqual(userEnviron.get("LC_COLLATE"), 'en_US')
        # "_" is always removed from the environment by Komodo
        #self.assert_(userEnviron.has("_"))
        #self.assertEqual(userEnviron.get("_"), './komodo')
        self.assert_(not userEnviron.has("_"))

    def test_environment_function3(self):
        # See http://bugs.activestate.com/show_bug.cgi?id=20685
        # Basically just want to make sure that this environment can
        # be parsed -- properly skipping the first (bogus?) arg.
        if not sys.platform.startswith("win"): return
        # This is the way *my* bash shows defined functions.
        envStrings = """
=\\Umax\umax c=\\Umax\umax c\WINDOWS\FONTS\
ALLUSERSPROFILE=C:\Documents and Settings\All Users
APPDATA=C:\Documents and Settings\Larry\Application Data
CLIENTNAME=Console
CommonProgramFiles=C:\Program Files\Common Files
COMPUTERNAME=LARRY_DELL
ComSpec=C:\WINDOWS\system32\cmd.exe
HOMEDRIVE=C:
HOMEPATH=\Documents and Settings\Larry
LOGONSERVER=\\LARRY_DELL
NUMBER_OF_PROCESSORS=1
OS=Windows_NT
Path=C:\Program Files\Python\.;C:\Perl\bin\;C:\WINDOWS\system32;C:\WINDOWS;C:\WINDOWS\System32\Wbem
PATHEXT=.COM;.EXE;.BAT;.CMD;.VBS;.VBE;.JS;.JSE;.WSF;.WSH;.py;.pyc;.pyo;.pyw;.pys
PROCESSOR_ARCHITECTURE=x86
PROCESSOR_IDENTIFIER=x86 Family 15 Model 2 Stepping 4, GenuineIntel
PROCESSOR_LEVEL=15
PROCESSOR_REVISION=0204
ProgramFiles=C:\Program Files
SESSIONNAME=Console
SystemDrive=C:
SystemRoot=C:\WINDOWS
TEMP=C:\DOCUME~1\Larry\LOCALS~1\Temp
TMP=C:\DOCUME~1\Larry\LOCALS~1\Temp
USERDOMAIN=LARRY_DELL
USERNAME=Larry
USERPROFILE=C:\Documents and Settings\Larry
windir=C:\WINDOWS
"""
        userEnviron = self._GetUserEnviron(envStrings)
        self.assert_(userEnviron.has("CLIENTNAME"))
        self.assertEqual(userEnviron.get("CLIENTNAME"), 'Console')


if __name__ == '__main__':
    unittest.main()

