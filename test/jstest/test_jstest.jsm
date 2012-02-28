/**
 * This is a test of the jstest unit testing harness
 */

const {classes: Cc, interfaces: Ci, utils: Cu} = Components;
let {TestError} = Cu.import("resource://komodo-jstest/JSTest.jsm");

function DummyTestCase() {

}

DummyTestCase.prototype.__proto__ = TestCase.prototype;
DummyTestCase.prototype.test_no_op = function DummyTestCase_test_no_op() {
    /* This doesn't do anything */
};

DummyTestCase.prototype.test_fail = function DummyTestCase_fail() {
    this.fail("This should fail");
};

DummyTestCase.prototype.test_failIf = function() {
    this.failIf(false, "FailIf should pass");
    this.failIf(true, "FailIf should fail");
}

DummyTestCase.prototype.test_failUnless = function() {
    this.failUnless(true, "failUnless should pass");
    this.failUnless(false, "failUnless should fail");
}

DummyTestCase.prototype.test_failUnlessRaises = function() {
    this.failUnlessRaises(TestError, (function() {
        this.fail("This should be caught")
    }).bind(this), [], "failUnlessRaises should pass");
    this.failUnlessRaises(TestError, (function() {
        /* nothing */
    }).bind(this), [], "failUnlessRaises should fail");
}

DummyTestCase.prototype.test_failUnlessEqual = function() {
    this.failUnlessEqual(123, 123, "failUnlessEqual should pass");
    this.failUnlessEqual(123, 321, "failUnlessEqual should fail");
}

DummyTestCase.prototype.test_failIfEqual = function() {
    this.failIfEqual(123, 321, "failIfEqual should pass");
    this.failIfEqual(123, 123, "failIfEqual should fail");
}

DummyTestCase.prototype.test_failUnlessAlmostEqual = function() {
    this.failUnlessAlmostEqual(123.00000005,
                               123.00000001,
                               7,
                               "failUnlessAlmostEqual should pass");
    this.failUnlessAlmostEqual(123.00000005,
                               123.00000001,
                               8,
                               "failUnlessAlmostEqual should fail");
}

DummyTestCase.prototype.test_failIfAlmostEqual = function() {
    this.failIfAlmostEqual(123.00000005,
                           123.00000001,
                           8,
                           "failIfAlmostEqual should pass");
    this.failIfAlmostEqual(123.00000005,
                           123.00000001,
                           7,
                           "failIfAlmostEqual should fail");
}

function SetUpTestCase_String() {}
SetUpTestCase_String.prototype.__proto__ = TestCase.prototype;
SetUpTestCase_String.prototype.test_no_op = function () {};
SetUpTestCase_String.prototype.setUp = function() {
    throw "Intentional error in setUp() (as a String)";
}

function SetUpTestCase_Error() {}
SetUpTestCase_Error.prototype.__proto__ = TestCase.prototype;
SetUpTestCase_Error.prototype.test_no_op = function () {};
SetUpTestCase_Error.prototype.setUp = function() {
    throw new Error("Intentional error in setUp() (as an Error)");
}

function TearDownTestCase_String() {}
TearDownTestCase_String.prototype.__proto__ = TestCase.prototype;
TearDownTestCase_String.prototype.test_no_op = function () {};
TearDownTestCase_String.prototype.tearDown = function() {
    throw "Intentional error in tearDown() (as a String)";
}
function TearDownTestCase_Error() {}
TearDownTestCase_Error.prototype.__proto__ = TestCase.prototype;
TearDownTestCase_Error.prototype.test_no_op = function () {};
TearDownTestCase_Error.prototype.tearDown = function() {
    throw new Error("Intentional error in tearDown() (as an Error)");
}
function TearDownTestCase_WithFailure() {}
TearDownTestCase_WithFailure.prototype.__proto__ = TestCase.prototype;
TearDownTestCase_WithFailure.prototype.test_intentional_failure = function () {
    this.fail("Intentional failure - expecting tearDown to still occur");
};
TearDownTestCase_WithFailure.prototype.tearDown = function() {
    throw new Error("Intentional error in tearDown() (as an Error)");
}

var JS_TESTS = ["DummyTestCase",
                "SetUpTestCase_String", "SetUpTestCase_Error",
                "TearDownTestCase_String", "TearDownTestCase_Error",
                "TearDownTestCase_WithFailure",];

// This skips running all the tests (which would fail intentionally), to avoid
// standard test runs having a bunch of failures
JS_TESTS = [];
