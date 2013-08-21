import re, sys, testlib, unittest
from os.path import abspath, basename, dirname, join, splitext
from xpcom import components
from testsupport import paths_from_path_patterns

class JSTestResult(object):
    _com_interfaces_ = [components.interfaces.koIJSTestResult]
    class TracebackFrame:
        """A fake traceback frame"""

        lineno_re = re.compile(r":(\d+)$")
        filename_re = re.compile(r"@([^@]+)$")

        def __init__(self, line, tb_next):
            class attrdict(dict):
                def __getattr__(self, attr):
                    return self.get(attr, None)
                __setattr__= dict.__setitem__
                __delattr__= dict.__delitem__

            self.tb_next = tb_next
            self.tb_frame = attrdict()
            self.tb_frame.f_globals = []
            self.tb_frame.f_code = attrdict()
            self.tb_lineno = 0

            match = JSTestResult.TracebackFrame.lineno_re.search(line)
            if match:
                self.tb_lineno = int(match.group(1))
                line = line[:match.start(0)]

            match = JSTestResult.TracebackFrame.filename_re.search(line)
            if match:
                self.tb_frame.f_code.co_filename = match.group(1)
                line = line[:match.start(0)]
            else:
                self.tb_frame.f_code.co_filename = "<unknown file>"

            self.tb_frame.f_code.co_name = line

    def __init__(self, result=None):
        self.result = result
        self.clear()
    def clear(self):
        self.skip_reason = None
        self.exception = None
    def reportError(self, aErrorMessage, aStack, aErrorType=None):
        tb_frame = None
        for frame in aStack:
            if not frame:
                continue
            tb_frame = JSTestResult.TracebackFrame(frame, tb_frame)
        self.exception = (aErrorType, aErrorMessage, tb_frame)

    def reportSkip(self, aReason):
        self.skip_reason = aReason

    @unittest.result.failfast
    def addError(self, test, err):
        """Overrides unittest.result.TestResult.addError
        Called when an error has occurred. 'err' is a tuple of values as
        returned by sys.exc_info()."""
        return self.result.addError(test, self.exception or err)

    @unittest.result.failfast
    def addFailure(self, test, err):
        """Overrides unittest.result.TestResult.addFailure
        Called when an error has occurred. 'err' is a tuple of values as
        returned by sys.exc_info()."""
        return self.result.addFailure(test, self.exception or err)

    def __getattr__(self, name):
        # forward everything we don't have to the underlying result
        return getattr(self.result, name)

class _JSTestTestCase(unittest.TestCase):

    def run(self, result=None):
        """
        Override unittest.TestCase.run so we can access the TestResult
        """
        if result is None: result = self.defaultTestResult()
        self._jstest_result = result = JSTestResult(result=result)
        self._jstest_result.clear()
        return unittest.TestCase.run(self, result=result)

    def setUp(self):
        self._jstest_result.clear()
        self._case.setUp(self._jstest_result)
        if self._jstest_result.skip_reason is not None:
            raise testlib.TestSkipped(self._jstest_result.skip_reason)
        if self._jstest_result.exception:
            if self._jstest_result.exception[0] is not None:
                raise self.failureException()
            raise Exception()

    def tearDown(self):
        self._jstest_result.clear()
        self._case.tearDown(self._jstest_result)
        if self._jstest_result.skip_reason is not None:
            raise testlib.TestSkipped(self._jstest_result.skip_reason)
        if self._jstest_result.exception:
            if self._jstest_result.exception[0] is not None:
                raise self.failureException()
            raise Exception()

    def _run_one_test(self, testName):
        self._case.runTest(self._jstest_result, testName)
        if self._jstest_result.skip_reason is not None:
            raise testlib.TestSkipped(self._jstest_result.skip_reason)
        if self._jstest_result.exception:
            if self._jstest_result.exception[0] is not None:
                raise self.failureException()
            raise Exception()

def test_paths():
    """Generate the potential JS test files."""
    catman = components.classes["@mozilla.org/categorymanager;1"]\
                       .getService(components.interfaces.nsICategoryManager)
    cat_enum = catman.enumerateCategory("komodo-jstest-paths")
    dirs = []
    while cat_enum.hasMoreElements():
        entry = cat_enum.getNext()
        value = catman.getCategoryEntry("komodo-jstest-paths", str(entry))
        dirs.append(abspath(value))

    for path in paths_from_path_patterns(dirs, includes=["test_*.jsm"]):
        yield path

def test_cases():
    """
    This is a hook for testlib.testcases_from_testmod() to find the tests we
    want to be able to deal with.
    """
    # The current module (we're going to define class objects on it).
    mod = sys.modules[test_cases.__module__]

    # Hackily get a handle on the "classobj" type so we can dynamically
    # create classes. Note that these are old-style Python classes
    # -- unittest.TestCase is still as old-style class in Python <=2.6; this
    # changed in Python 2.7
    classobj = type(_JSTestTestCase)
    test_svc = components.classes['@activestate.com/koJSTestService;1']\
                         .getService(components.interfaces.koIJSTestService)

    for path in test_paths():
        for case in test_svc.getTestsForPath(path) or []:
            path_tag = splitext(basename(path))[0][len("test_"):]
            clazz = classobj(case.name, (_JSTestTestCase,),
                             {"__tags__": [path_tag],
                              "_case": case})
            setattr(mod, case.name, clazz)

            # add no-op test_* functions
            for test_name in case.getTestNames():
                def new_func(test_name):
                    return lambda self: self._run_one_test(test_name)
                setattr(clazz, test_name, new_func(test_name))

            yield clazz
