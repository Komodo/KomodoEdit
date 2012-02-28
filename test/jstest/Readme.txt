This directory holds some simple code to test JS code.

It looks through the source tree for files named like "test_*.jsm".  For each
file found, it will:

- import the file from JS;
- look for an array named "JS_TESTS" (which should contain strings);
- for each element in the array, try to look up the class named by the string;
- for each class found, try to run it as a TestCase.

Each test case should inherit from TestCase in resource://komodo-jstest/JSTest.jsm;
it may have "setUp", "tearDown", and various "test_*" methods.  The various
assertion functions are available, e.g. assertTrue.

Test suites are currently not supported.

Any uncaught exceptions will be reported as failures.
