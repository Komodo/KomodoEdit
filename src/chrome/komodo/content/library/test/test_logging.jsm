const {classes: Cc, interfaces: Ci, utils: Cu} = Components;

Cu.import("resource://gre/modules/XPCOMUtils.jsm");
Cu.import("resource://komodo-jstest/JSTest.jsm");

/**
 * Fake logger, used to make sure all the logging calls are getting through to
 * the underlying XPCOM component
 */
function FakeLogger(name, loggers) {
    this.name = name;
    this.level = undefined;
    this.loggers = loggers;
    this.entries = [];
}

FakeLogger.prototype.setLevel = function(level) {
    this.level = Number(level);
};

FakeLogger.prototype.getEffectiveLevel = function() {
    let parts = this.name.split(".");
    while (parts.length) {
        let name = parts.join(".");
        let log = this.loggers[name] || {level: undefined};
        if (log.level !== undefined) {
            return this.loggers[name].level;
        }
        parts.pop();
    }
    return this.loggers[""].level || 0;
};

FakeLogger.prototype.isEnabledFor = function(level) {
    return this.getEffectiveLevel() <= level;
};

FakeLogger.prototype._log = function(msg, level) {
    if (this.isEnabledFor(level)) {
        this.entries.push([this.name, level, msg]);
    }
};

FakeLogger.prototype.debug = function(msg) {
    this._log(msg, Ci.koILoggingService.DEBUG);
};

FakeLogger.prototype.info = function(msg) {
    this._log(msg, Ci.koILoggingService.INFO);
};

FakeLogger.prototype.warn = function(msg) {
    this._log(msg, Ci.koILoggingService.WARN);
};

FakeLogger.prototype.error = function(msg) {
    this._log(msg, Ci.koILoggingService.ERROR);
};

FakeLogger.prototype.critical = function(msg) {
    this._log(msg, Ci.koILoggingService.CRITICAL);
};

function JSLoggingTestCase() {}

JSLoggingTestCase.prototype = new TestCase();

JSLoggingTestCase.prototype.setUp = function() {
    // Replace logging service with our fake logging service, so that we can
    // track what has been logged without spewing things out at the user
    let logMgr = this.logging.getLoggingMgr();
    let loggers = {};
    logMgr.loggingSvc = {
        getLogger: function(name) {
            if (!(name in loggers)) {
                loggers[name] = new FakeLogger(name, loggers);
            }
            return loggers[name];
        },
        QueryInterface: XPCOMUtils.generateQI([Ci.koILoggingService]),
    };
    // set default log level
    logMgr.loggingSvc.getLogger("").setLevel(Ci.koILoggingService.WARN);
};

JSLoggingTestCase.prototype.tearDown = function() {
    // Restore the original logging service
    let logMgr = this.logging.getLoggingMgr();
    logMgr.loggingSvc = Cc["@activestate.com/koLoggingService;1"]
                          .getService(Ci.koILoggingService);
    logMgr.LoggerMap = {};
};

JSLoggingTestCase.prototype.test_constants = function() {
    this.assertEqual(this.logging.LOG_NOTSET, 0, "Incorrect value for not set");
    this.assertEqual(this.logging.LOG_DEBUG, 10, "Incorrect value for debug");
    this.assertEqual(this.logging.LOG_INFO, 20, "Incorrect value for info");
    this.assertEqual(this.logging.LOG_WARN, 30, "Incorrect value for warn");
    this.assertEqual(this.logging.LOG_ERROR, 40, "Incorrect value for error");
    this.assertEqual(this.logging.LOG_CRITICAL, 50, "Incorrect value for critical");
};

JSLoggingTestCase.prototype.test_create = function() {
    let log = this.logging.getLogger("test.logging." + this.method + ".create");
    this.assertTrue(log);
    this.assertTrue("error" in log);
    this.assertTrue(log._logger instanceof FakeLogger);
};

JSLoggingTestCase.prototype.test_critical = function() {
    const kName = "test.logging." + this.method + ".critical";
    let log = this.logging.getLogger(kName);
    log.setLevel(this.logging.LOG_CRITICAL);
    this.assertTrue(log.isEnabledFor(this.logging.LOG_CRITICAL));
    this.assertFalse(log.isEnabledFor(this.logging.LOG_ERROR));
    log.critical("This is critical", true);
    log.error("This is is an error", true);
    this.assertEqual(log._logger.entries,
                     [[kName, this.logging.LOG_CRITICAL, "This is critical"]]);
};

JSLoggingTestCase.prototype.test_error = function() {
    const kName = "test.logging." + this.method + ".error";
    let log = this.logging.getLogger(kName);
    log.setLevel(this.logging.LOG_ERROR);
    this.assertFalse(log.isEnabledFor(this.logging.LOG_WARN));
    this.assertTrue(log.isEnabledFor(this.logging.LOG_ERROR));
    this.assertTrue(log.isEnabledFor(this.logging.LOG_CRITICAL));
    log.warn("This is a warning");
    log.error("This is an error", true);
    log.critical("This is critical");
    this.assertEqual(log._logger.entries,
                     [[kName, this.logging.LOG_ERROR, "This is an error"],
                      [kName, this.logging.LOG_CRITICAL, "This is critical"]]);
    log.error("This has stack");
    let [name, level, msg] = log._logger.entries.pop();
    this.assertEqual(name, log._logger.name);
    this.assertEqual(level, this.logging.LOG_ERROR);
    this.assertGreater(msg.indexOf("test_logging.jsm"), -1);
};

JSLoggingTestCase.prototype.test_warn = function() {
    const kName = "test.logging." + this.method + ".warn";
    let log = this.logging.getLogger(kName);
    log.setLevel(this.logging.LOG_WARN);
    this.assertFalse(log.isEnabledFor(this.logging.LOG_INFO));
    this.assertTrue(log.isEnabledFor(this.logging.LOG_WARN));
    this.assertTrue(log.isEnabledFor(this.logging.LOG_ERROR));
    log.info("This is some info");
    log.warn("This is a warning");
    log.error("This is an error", true);
    this.assertEqual(log._logger.entries,
                     [[kName, this.logging.LOG_WARN, "This is a warning"],
                      [kName, this.logging.LOG_ERROR, "This is an error"]]);
};

JSLoggingTestCase.prototype.test_info = function() {
    const kName = "test.logging." + this.method + ".info";
    let log = this.logging.getLogger(kName);
    log.setLevel(this.logging.LOG_INFO);
    this.assertFalse(log.isEnabledFor(this.logging.LOG_DEBUG));
    this.assertTrue(log.isEnabledFor(this.logging.LOG_INFO));
    this.assertTrue(log.isEnabledFor(this.logging.LOG_WARN));
    log.debug("This is a debug message");
    log.info("This is some info");
    log.warn("This is a warning");
    this.assertEqual(log._logger.entries,
                     [[kName, this.logging.LOG_INFO, "This is some info"],
                      [kName, this.logging.LOG_WARN, "This is a warning"]]);
};

JSLoggingTestCase.prototype.test_debug = function() {
    const kName = "test.logging." + this.method + ".debug";
    let log = this.logging.getLogger(kName);
    log.setLevel(this.logging.LOG_DEBUG);
    this.assertTrue(log.isEnabledFor(this.logging.LOG_DEBUG));
    this.assertTrue(log.isEnabledFor(this.logging.LOG_INFO));
    log.debug("This is a debug message");
    log.info("This is some info");
    this.assertEqual(log._logger.entries,
                     [[kName, this.logging.LOG_DEBUG, "This is a debug message"],
                      [kName, this.logging.LOG_INFO, "This is some info"]]);
};

JSLoggingTestCase.prototype.test_deprecated = function() {
    const kName = "test.logging." + this.method + ".deprecated";
    let log = this.logging.getLogger(kName);
    log.deprecated("This is a test");
    let entries = log._logger.entries;
    this.assertEqual(entries.length, 1);
    let [name, level, text] = entries.pop();
    this.assertEqual(name, kName);
    this.assertEqual(level, this.logging.LOG_WARN);
    let stack = text.split(/\n/);
    let message = stack.shift();
    this.assertEqual(message, "This is a test",
                     "Deprecation message does not start with supplied message");
    this.assertGreater(stack[0].indexOf("test_logging.jsm"), -1,
                       "Failed to find test file on top of stack:\n    " +
                       stack.join("    \n"));
};

JSLoggingTestCase.prototype.test_global_deprecated = function() {
    const kName = "test.logging." + this.method + ".deprecated";
    const global = (function() this)();
    const kExpected = Math.random();
    let log = this.logging.getLogger(kName);
    this.logging.globalDeprecatedByAlternative("global_var",
                                               kExpected,
                                               log,
                                               global);
    this.assertEqual(log._logger.entries, []);
    this.assertEqual(global_var, kExpected);
    delete global.global_var;
    this.assertNotIn("global_var", global);
    this.assertRaises(ReferenceError, () => global_var, [],
                      "global var not deleted");
};

JSLoggingTestCase.prototype.test_method = function() {
    this.assertEqual(this.logging.__method__, this.method);
};

/**
 * Test logging via Components.utils.import
 */
function JSLoggingViaImportTestCase() {
    this.method = "import";
}
JSLoggingViaImportTestCase.__name__ = "JSLogging/ViaImport";

JSLoggingViaImportTestCase.prototype = new JSLoggingTestCase();

JSLoggingViaImportTestCase.prototype.setUp = function() {
    this.logging =
        Cu.import("chrome://komodo/content/library/logging.js", {}).logging;
    JSLoggingTestCase.prototype.setUp.call(this);
};

/**
 * Test logging via jetpack require("ko/logging");
 */
function JSLoggingViaRequireTestCase() {
    this.method = "require";
}
JSLoggingViaImportTestCase.__name__ = "JSLogging/ViaRequire";

JSLoggingViaRequireTestCase.prototype = new JSLoggingTestCase();

JSLoggingViaRequireTestCase.prototype.setUp = function() {
    let loader = Cc["@mozilla.org/moz/jssubscript-loader;1"]
                   .createInstance(Ci.mozIJSSubScriptLoader);
    let scope = {Components: Components,
                 ko: {},
                 window: {},
                 document: {}};
    loader.loadSubScript("chrome://komodo/content/jetpack.js", scope);
    this.logging = scope.require("ko/logging");
    JSLoggingTestCase.prototype.setUp.call(this);
};

/**
 * Test loading jetpack from Cu.import
 */
function JSLoggingViaImportJetpackTestCase(args) {
    this.method = "require";
}
JSLoggingViaImportTestCase.__name__ = "JSLogging/ViaImportJetpack";

JSLoggingViaImportJetpackTestCase.prototype = new JSLoggingTestCase();

JSLoggingViaImportJetpackTestCase.prototype.setUp = function() {
    let scope = {};
    Cu.import("chrome://komodo/content/jetpack.js", scope);
    this.logging = scope.require("ko/logging");
    JSLoggingTestCase.prototype.setUp.call(this);
};

/**
 * Test logging via faking a window
 */
function JSLoggingViaWindowTestCase() {
    this.method = "require";
}
JSLoggingViaImportTestCase.__name__ = "JSLogging/ViaWindow";

JSLoggingViaWindowTestCase.prototype = new JSLoggingTestCase();

JSLoggingViaWindowTestCase.prototype.setUp = function() {
    let principal = Cc["@mozilla.org/systemprincipal;1"]
                      .createInstance(Ci.nsIPrincipal);
    let sandbox = Cu.Sandbox(principal,
                             { sandboxName: "ko/logging unit test (window)",
                               sandboxPrototype: {
                                 window: {__is_unit_test__: true},
                                 document: {},
                                 ko: {},
                               }});
    let loader = Cc["@mozilla.org/moz/jssubscript-loader;1"]
                   .createInstance(Ci.mozIJSSubScriptLoader);
    loader.loadSubScript("chrome://komodo/content/library/logging.js", sandbox);
    this.logging = sandbox.ko.logging;
    JSLoggingTestCase.prototype.setUp.call(this);
    this.__sandbox__ = sandbox;
};

JSLoggingViaWindowTestCase.prototype.test_method = function() {
    this.assertEqual(this.__sandbox__.window.__method__, "window");
    this.assertEqual(this.logging.__method__, "require");
};

const JS_TESTS = ["JSLoggingViaImportTestCase",
                  "JSLoggingViaRequireTestCase",
                  "JSLoggingViaImportJetpackTestCase",
                  "JSLoggingViaWindowTestCase"];
