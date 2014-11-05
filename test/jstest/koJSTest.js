const {classes: Cc, interfaces: Ci, utils: Cu} = Components;

Cu.import("resource://gre/modules/Services.jsm");
Cu.import("resource://gre/modules/XPCOMUtils.jsm");

const {TestCase, TestError, SkipTest} =
    Cu.import("resource://komodo-jstest/JSTest.jsm", {});

var log = null;

try {
    let logging = Cu.import("chrome://komodo/content/library/logging.js", {}).logging;
    log = logging.getLogger("jstest.driver");
} catch(e) {
    log = null;
}

/**
 * Komodo JS Test Service - this is a thunk between the Python unittest
 * framework and simple JS-based tests; see /test/jstest/Readme.txt
 * @constructor
 */
function KoJSTestService() {

}

/***** koIJSTestService *****/
KoJSTestService.prototype.getTestsForPath = function KoJSTestService_getTestsForPath(aPath, aCount) {
    let loader = Cc['@mozilla.org/moz/jssubscript-loader;1']
                   .getService(Ci.mozIJSSubScriptLoader);
    let scope = {Components: Components, dump: dump};
    let testcases = []
    try {
        let file = Cc["@mozilla.org/file/local;1"].createInstance(Ci.nsILocalFile);
        file.initWithPath(aPath);
        let uri = Services.io.newFileURI(file, null, null);
        loader.loadSubScript(uri.spec, scope, "UTF-8");
        if ("JS_TESTS" in scope) {
            let found_suspects = false;
            for each (let className in scope.JS_TESTS) {
                found_suspects = true;
                let clazz = scope[className];
                if (!clazz) {
                    dump('WARNING: in "' + aPath + '", class ' + className +
                         ' could not be found.\n');
                    continue;
                }
                let proto = clazz.prototype;
                while (proto && proto !== TestCase.prototype) {
                    proto = Object.getPrototypeOf(proto);
                }
                if (!proto) {
                    // This class doesn't derive from TestCase
                    dump('WARNING: in "' + aPath + '", class ' + className +
                         " doesn't derive from TestCase; ignored.\n");
                    continue;
                }
                testcases.push(new KoJSTestCase(className, clazz));
            }
            if (!found_suspects) {
                dump('WARNING: in "' + aPath + '": no tests listed in JS_TESTS; ignored.\n');
            }
        } else {
            dump('WARNING: in "' + aPath + '": no JS_TESTS array found; ignored.\n');
        }
    } catch (ex) {
        if (log) {
            log.exception(ex);
        } else {
            dump('WARNING: Failed to load tests from "' +
                 aPath + '": ' + ex);
        }
    }
    aCount.value = testcases.length;
    return testcases;
};

/***** nsISupports *****/
KoJSTestService.prototype.classID = Components.ID("{036dc8b2-7527-469c-828e-50655b56880a}");
KoJSTestService.prototype.QueryInterface = XPCOMUtils.generateQI([Ci.koIJSTestService]);

/**
 * JS Test Case - this is a XPCOM wrapper to construct a TestCase (class)-looking
 * thing to expose to python.
 */
function KoJSTestCase(aClassName, aClass) {
    this.name = (aClass.__name__ || aClassName).replace(/^Test/, "");
    this.clazz = aClass;
}
KoJSTestCase.prototype.getTestNames = function KoJSTestCase_getTestNames(aCount) {
    let nameHash = {};
    let proto = this.clazz.prototype;
    while (proto) {
        Object.getOwnPropertyNames(proto)
              .filter(function(n) /^test_/.test(n))
              .forEach(function(n) nameHash[n] = true);
        proto = Object.getPrototypeOf(proto);
    }
    let names = Object.keys(nameHash).sort();
    if (aCount) {
        aCount.value = names.length;
    }
    return names;
};
KoJSTestCase.prototype.runTest = function KoJSTestCase_runTest(aResult, aTestName) {
    try {
        this.instance[aTestName]();
    } catch (ex if ex instanceof SkipTest) {
        aResult.reportSkip(ex.message);
    } catch (ex if ex instanceof TestError) {
        this._reportTestException(aResult, ex, ex.message || ex);
    } catch (ex) {
        this._reportTestException(aResult, ex, "While testing " + aTestName + ": " + (ex.message || ex));
    }
};

KoJSTestCase.prototype.setUp = function KoJSTestCase_setUp(aResult) {
    Cc["@mozilla.org/consoleservice;1"].getService(Ci.nsIConsoleService).reset();
    try {
        this.instance = new this.clazz();
    } catch (ex if ex instanceof SkipTest) {
        aResult.reportSkip(ex.message);
        return;
    } catch (ex) {
        this._reportTestException(aResult, ex, "While creating " + this.name + ": " + (ex.message || ex));
        return;
    }
    try {
        this.instance.setUp();
    } catch (ex if ex instanceof SkipTest) {
        aResult.reportSkip(ex.message);
    } catch (ex) {
        this._reportTestException(aResult, ex, "While setting up " + this.name + ": " + (ex.message || ex));
    }
}

KoJSTestCase.prototype.tearDown = function KoJSTestCase_tearDown(aResult) {
    try {
        this.instance.tearDown();
    } catch (ex if ex instanceof SkipTest) {
        aResult.reportSkip(ex.message);
    } catch (ex) {
        this._reportTestException(aResult, ex, "While tearing down " + this.name + ": " + (ex.message || ex));
    }
    delete this.instance;
    try {
        let messages = {};
        Cc["@mozilla.org/consoleservice;1"].getService(Ci.nsIConsoleService).getMessageArray(messages, {});
        if (!messages.value) {
            return;
        }
        for each (let message in messages.value) {
            if (message instanceof Ci.nsIScriptError) {
                let severity = "info";
                if (message.flags & Ci.nsIScriptError.exceptionFlag) {
                    severity = "exception";
                } else if (message.flags & Ci.nsIScriptError.errorFlag) {
                    severity = "error";
                }
                log[severity](message.toString());
            } else {
                log.info(message.message);
            }
        }
    } catch (ex) {
        dump(ex);
    }
}

KoJSTestCase.prototype._reportTestException = function KoJSTestCase__reportException(testcase, ex, message) {
    try {
        let stack = this._getStackForException(ex);
        testcase.reportError(message,
                            stack, stack.length,
                            ex.constructor.name);
    } catch (stackex) {
        testcase.reportError("While testing " + aTestName + ": " + (ex.message || ex),
                            [], 0, null);
    }
}

/**
 * Given an exception, return a filtered array of strings for the stack trace
 */
KoJSTestCase.prototype._getStackForException = function KoJSTestCase__getStackForException(ex) {
    if (ex instanceof Ci.nsIException) {
        return this._getStackFornsIException(ex);
    }
    let stack = ex.stack.split(/\n/);
    stack = stack.map(function(line) {
        let fileName = "", lineNumber = "";
        let match = /:\d+$/.exec(line);
        if (match) {
            lineNumber = match[0];
            line = line.substr(0, match.index);
        }
        match = /@[^@]+$/.exec(line);
        if (match) {
            fileName = match[0];
            line = line.substr(0, match.index);
        }
        if (fileName == "@" + __URI__) {
            // skip lines from this file
            return undefined;
        }
        let prefix = "@" + __URI__ + " -> ";
        if (fileName.substr(0, prefix.length) == prefix) {
            // This is a file loaded via the subscript loader, i.e. the actual
            // test file.  Strip of the prefix so it's more readable.
            fileName = "@" + fileName.substr(prefix.length);
        }
        return line + fileName + lineNumber;
    }).filter(function(line) typeof(line) != "undefined");
    return stack;
};

/**
 * Given a nsIException, returned a filtered array of strings for the stack trace
 */
KoJSTestCase.prototype._getStackFornsIException = function KoJSTestCase__getStackFornsIException(ex) {
    let stack = [];
    for (let frame = ex.location; frame; frame = frame.caller) {
        // Drop the subscript loader info
        let filename = String(frame.filename).replace(/^.*->\s*/, "");
        stack.push(frame.name + "@" + filename + ":" + frame.lineNumber);
    }
    return stack;
};

KoJSTestCase.prototype.QueryInterface = XPCOMUtils.generateQI([Ci.koIJSTestCase]);

const NSGetFactory = XPCOMUtils.generateNSGetFactory([KoJSTestService]);
