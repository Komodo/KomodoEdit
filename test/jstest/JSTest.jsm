/**
 * JS test harness inspired by Python's unittest module
 */

const EXPORTED_SYMBOLS = ["TestCase", "SkipTest"];

let logging = Components.utils.import("chrome://komodo/content/library/logging.js", {}).logging;
let log = logging.getLogger("jstest.TestCase");

/**
 * Base class for unit test errors.  Note that this isn't directly exported
 * from this module; it can only be obtained via BackstagePass
 */
function TestError(message, exceptionType) {
    // Sadly, using Error.apply doesn't seem to work :/
    let error = new Error();
    this.message = message;
    this.type = exceptionType;
    let stack = error.stack.split(/\n/);
    // Filter out lines from this file
    const suffix = "@" + __URI__;
    stack = stack.filter(function(line) line.replace(/:\d+$/, "").substr(-suffix.length) != suffix);
    this.stack = stack.join("\n");
}
TestError.prototype.__proto__ = new Error();

function SkipTest(message) {
    if (!(this instanceof SkipTest)) {
        // throw SkipTest() instead of throw new SkipTest()
        if (arguments.length < 1) {
            return new SkipTest();
        } else {
            return new SkipTest(message);
        }
    }
    this.message = arguments.length < 1 ? "" : String(message);
    return this;
}

function keys(obj) {
    let hash = {}, proto = obj;
    while (proto !== null) {
        Object.getOwnPropertyNames(proto).map(function(n) hash[n] = true);
        proto = Object.getPrototypeOf(proto);
    }
    return Object.keys(hash);
}

function TestCase() {
    /* Nothing to see here - actual test cases should be more exciting */
}

TestCase.TestError = TestError;

/**
 * Optional method: setUp
 * This is run before test cases
 */
TestCase.prototype.setUp = function TestCase_setUp() {};

/**
 * Optional method: tearDown
 * This is run after test cases
 */
TestCase.prototype.tearDown = function TestCase_teardown() {};

TestCase.fail =
TestCase.prototype.fail = function TestCase_fail(msg) {
    throw new TestError(msg || ("Unknown failure"), "Assert");
};
TestCase.prototype.assertFalse =
TestCase.prototype.failIf = function TestCase_failIf(expr, msg) {
    if (expr) {
        throw new TestError(msg || ("failIf: " + expr + " != true"),
                            "AssertFalse");
    }
    log.debug("PASS: " + msg);
};
TestCase.prototype.assert = TestCase.prototype.assert_ = TestCase.prototype.assertTrue =
TestCase.prototype.failUnless = function TestCase_failUnless(expr, msg) {
    if (!expr) {
        throw new TestError((msg || ("failUnless: " + expr + " != false")) + ": " + expr,
                            "AssertTrue");
    }
    log.debug("PASS: " + msg);
};
TestCase.prototype.assertRaises =
TestCase.prototype.failUnlessRaises = function TestCase_failUnlessRaises(excClass, callableObj, args, msg, callback) {
    try {
        callableObj.apply(this, args);
    } catch (ex if ex instanceof excClass) {
        // test passed
        if (callback) {
            callback(ex);
        }
        log.debug("PASS: " + msg);
        return;
    }
    throw new TestError(msg || "Exception was not raised",
                        "Assert");
};

function isValueEqual(v1, v2) {
    if (typeof(v1) != typeof(v2))
        return false;
    if (v1 != v2 && typeof(v1) == 'object')
        return this.isObjectEqual(v1, v2);
    return v1 == v2;
}

function isObjectEqual(ar1, ar2) {
    if (ar1.length != ar2.length) return false;
    for (var i in ar1) {
        if (!this.isValueEqual(ar1[i], ar2[i])) return false;
    }
    return true;
}

TestCase.prototype.assertEqual = TestCase.prototype.assertEquals =
TestCase.prototype.failUnlessEqual = function TestCase_failUnlessEqual(first, second, msg) {
    if (!isValueEqual(first, second)) {
        throw new TestError((msg || "failUnlessEqual") + ": " + first + " != " + second,
                            "AssertEquals");
    }
    log.debug("PASS: " + msg);
};
TestCase.prototype.assertNotEqual = TestCase.prototype.assertNotEquals =
TestCase.prototype.failIfEqual = function TestCase_failUnless(first, second, msg) {
    if (isValueEqual(first, second)) {
        throw new TestError((msg || "failIfEqual") + ": " + first + " == " + second,
                            "AssertNotEquals");
    }
    log.debug("PASS: " + msg);
};
TestCase.prototype.assertAlmostEqual = TestCase.prototype.assertAlmostEquals =
TestCase.prototype.failUnlessAlmostEqual = function TestCase_failUnlessAlmostEqual(first, second, places, msg) {
    if (typeof(places) == "undefined") {
        places = 7;
    }
    let difference = Math.round((first - second) * Math.pow(10, Math.max(0, places)));
    if (difference != 0) {
        throw new TestError(msg || (difference + " != 0"),
                            "AssertAlmostEqual");
    }
    log.debug("PASS: " + msg);
};
TestCase.prototype.assertNotAlmostEqual = TestCase.prototype.assertNotAlmostEquals =
TestCase.prototype.failIfAlmostEqual = function TestCase_failIfAlmostEqual(first, second, places, msg) {
    if (typeof(places) == "undefined") {
        places = 7;
    }
    let difference = Math.round((first - second) * Math.pow(10, Math.max(0, places)));
    if (difference == 0) {
        throw new TestError(msg || (difference + " == 0"),
                            "AssertNotAlmostEqual");
    }
    log.debug("PASS: " + msg);
};
TestCase.prototype.assertIn = function TestCase_assertIn(prop, obj, msg) {
    if (!(prop in obj)) {
        throw new TestError((msg || "assertIn") + ": " + prop + " in " + obj,
                            "AssertIn");
    }
    log.debug("PASS: " + msg);
};
TestCase.prototype.assertNotIn = function TestCase_assertNotIn(prop, obj, msg) {
    if (prop in obj) {
        throw new TestError((msg || "assertNotIn") + ": " + prop + " not in " + obj,
                            "AssertNotIn");
    }
    log.debug("PASS: " + msg);
};
TestCase.prototype.assertGreater = function TestCase_assertGreater(first, second, msg) {
    if (!(first > second)) {
        throw new TestError((msg || "assertGreater") + ": " + first + " > " + second,
                            "AssertGreater");
    }
    log.debug("PASS: " + msg);
};
TestCase.prototype.assertGreaterEqual = function TestCase_assertGreaterEqual(first, second, msg) {
    if (!(first >= second)) {
        throw new TestError((msg || "assertGreaterEqual") + ": " + first + " >= " + second,
                            "AssertGreaterEqual");
    }
    log.debug("PASS: " + msg);
};
TestCase.prototype.assertLess = function TestCase_assertLess(first, second, msg) {
    if (!(first < second)) {
        throw new TestError((msg || "assertLess") + ": " + first + " < " + second,
                            "AssertLess");
    }
    log.debug("PASS: " + msg);
};
TestCase.prototype.assertLessEqual = function TestCase_assertLessEqual(first, second, msg) {
    if (!(first <= second)) {
        throw new TestError((msg || "assertLessEqual") + ": " + first + " <= " + second,
                            "AssertLessEqual");
    }
    log.debug("PASS: " + msg);
};
