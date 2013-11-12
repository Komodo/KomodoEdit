const {classes: Cc, interfaces: Ci, utils: Cu} = Components;
Cu.import("resource://komodo-jstest/JSTest.jsm");
Cu.import("resource://gre/modules/Services.jsm");

var ko = {};
Cu.import("resource://komodo-jstest/mock/mock.jsm", {})
  .import(ko, "views", "macros", "mru", "history", "stringutils",
          "findresults", "statusbar",
          "chrome://komodo/content/library/tabstops.js");

let logging = Components.utils.import("chrome://komodo/content/library/logging.js", {}).logging;
//let log = logging.getLogger("jstest.TestCase");

var TestPylint = function TestPylint() {
    this.log = null;
    this.log = logging.getLogger("lint.pylint");
    this.log.setLevel(ko.logging.LOG_DEBUG);
}
TestPylint.prototype = new TestCase();

TestPylint.prototype.setUp = function TestPylint_setUp() {
    let loader = Cc['@mozilla.org/moz/jssubscript-loader;1']
                   .getService(Ci.mozIJSSubScriptLoader);
    this.scope = { ko: ko, __noSuchMethod__: function() {}};
    this.globalPrefs = Cc["@activestate.com/koPrefService;1"].getService(Ci.koIPrefService).prefs;
    this.fileSvc = Cc["@activestate.com/koFileService;1"].getService(Ci.koIFileService);
    this.docSvc = Cc["@activestate.com/koDocumentService;1"].getService(Ci.koIDocumentService);
    this.encodingSvc = Cc["@activestate.com/koEncodingServices;1"].getService(Ci.koIEncodingServices);
    this.pythonInfoSvc = Cc["@activestate.com/koAppInfoEx?app=Python;1"].getService(Ci.koIAppInfoEx);
    this.python3InfoSvc = Cc["@activestate.com/koAppInfoEx?app=Python3;1"].getService(Ci.koIAppInfoEx);
    this.koIDocument = Ci.koIDocument;
    var this_ = this;
    this.origBooleanPrefs = {
      editUseLinting: this.globalPrefs.getBooleanPref("editUseLinting"),
      lint_python_with_pylint: this.globalPrefs.getBooleanPref("lint_python_with_pylint"),
      lint_python3_with_pylint3: this.globalPrefs.getBooleanPref("lint_python3_with_pylint3"),
      lint_python_with_standard_python: this.globalPrefs.getBooleanPref("lint_python_with_standard_python"),
      lint_python3_with_standard_python: this.globalPrefs.getBooleanPref("lint_python3_with_standard_python"),
      lint_python_with_pyflakes: this.globalPrefs.getBooleanPref("lint_python_with_pyflakes"),
      lint_python_with_pep8: this.globalPrefs.getBooleanPref("lint_python_with_pep8"),
      lint_python_with_pychecker: this.globalPrefs.getBooleanPref("lint_python_with_pychecker"),
      lint_python3_with_pyflakes3: this.globalPrefs.getBooleanPref("lint_python3_with_pyflakes3"),
      lint_python3_with_pep83: this.globalPrefs.getBooleanPref("lint_python3_with_pep83"),
      lint_python3_with_pychecker3: this.globalPrefs.getBooleanPref("lint_python3_with_pychecker3")
    };
    this.origStringPrefs = {
      pylint_checking_rcfile: this.globalPrefs.getStringPref("pylint_checking_rcfile"),
      pylint3_checking_rcfile: this.globalPrefs.getStringPref("pylint3_checking_rcfile"),
      pythonDefaultInterpreter: this.globalPrefs.getStringPref("pythonDefaultInterpreter"),
      python3DefaultInterpreter: this.globalPrefs.getStringPref("python3DefaultInterpreter")
    };
    for (prefName in this.origBooleanPrefs) {
        this.globalPrefs.setBooleanPref(prefName, false);
    }
    this.globalPrefs.setBooleanPref("editUseLinting", true);
};

TestPylint.prototype.tearDown = function TestPylint_tearDown() {
    var prefName;
    for (prefName in this.origBooleanPrefs) {
        this.globalPrefs.setBooleanPref(prefName, this.origBooleanPrefs[prefName]);
    }
    for (prefName in this.origStringPrefs) {
        this.globalPrefs.setStringPref(prefName, this.origStringPrefs[prefName]);
    }
};

TestPylint.prototype.msgHandler =
function TestPylint_msgHandler(level, context, message) {
    this.fail("Message handler called in quiet mode: " +
              "level=" + level + " context=" + context +
              " message=" + message + "\n");
};

TestPylint.prototype.test_no_lint = function test_no_lint() {
    // If editUseLinting is off, verify that we get zero results
    // This is Perl code --
    // normally the Python linter would find *something* to complain about
    // But in this case it shouldn't complain at all.
    var file = this.fileSvc.makeTempFile(".py", 'wb');
    var origLines = [ 'use Time::HiRes qw(gettimeofday tv_interval);'
                 ,'use strict;'
                 ,'use warnings;'
                 ,''
                 ,'my $start_time;'
                 ,'BEGIN {'
                 ,'    $start_time = [Time::HiRes::gettimeofday]'
                 ,'}'
                 ,'print "Time to startup: ", (tv_interval($start_time, [gettimeofday])), " secs\\n",;'
                 ,'use LWP::Simple;'
                 ,'my $doc = LWP::Simple::get(\'http://www.microsoft.com/\');'
                 ,'printf "Read %d chars\\n", length($doc);'
                 ,''
                ];

    this.expectedMessages = [
    ];
    var origBuf = origLines.join("\n");
    var view = new ko.views.ViewMock({text:origBuf});
    file.puts(origBuf);
    file.close();
    var koDoc = this.docSvc.createNewDocumentFromURI(file.URI);
    koDoc.new_line_endings = this.koIDocument.EOL_LF;
    koDoc.language = "Python";
    // Set the buffer before assigning the view, otherwise it will fail.
    var origBugUTF = this.encodingSvc.encode(origBuf, "utf-8", "")
    koDoc.setBufferAndEncoding(origBugUTF, "utf-8");
    view.koDoc = koDoc;
    //koDoc.addView(view.scintilla);
    var scimoz = view.scimoz;
    
    var lintSvc = Components.classes["@activestate.com/koLintService;1"].
                    getService(Components.interfaces.koILintService);
    var lr = Components.classes["@activestate.com/koLintRequest;1"].
                createInstance(Components.interfaces.koILintRequest);
    lr.rid = 1;
    lr.koDoc = koDoc;
    lr.linterType = koDoc.language;
    lr.uid = 3;
    lr.cwd = koDoc.file.dirname;
    lr.lintBuffer = this;
    lr.alwaysLint = true;
    // All other prefs are turned off
    this.globalPrefs.setBooleanPref("editUseLinting", false);
    ////////this.globalPrefs.setStringPref("pythonDefaultInterpreter", "c:\\python27\\python.exe");
    
    this.expectedNumTests = 0;
    this.finalResult = false;
    lintSvc.addRequest(lr);
    // We fired a lint request, now stay alive so the callback can start working.
    stopTime = Date.now() + 10000; // time in msec
    while (Date.now() < stopTime) {
        Services.tm.mainThread.processNextEvent(false);
    }
    this.assertTrue(this.finalResult);
}

TestPylint.prototype.test_pylint_01 = function test_pylint_01() {
    //this.log.debug("\n\n\ntest_revert_01:\n\n\n")
    // Make sure we have pylint available, otherwise skip this test
    if (!this.pythonInfoSvc.executablePath) {
        throw SkipTest("python not installed");
    }
    if (!this.pythonInfoSvc.haveModules(1, ["pylint"])) {
        throw SkipTest("pylint not installed");
    }
    var file = this.fileSvc.makeTempFile(".py", 'wb');
    var origLines = [ 'class C(object):'
                     ,'    def only_func(self, a, b):'
                     ,'        return a + 3'
                     ,'    '
                     ,'c = C()'
                     ,'print(c.only_func(5, 7))'
                    ];
    this.expectedMessages = [
{lineStart:4,
lineEnd:4,
columnStart:1,
columnEnd:5,
description: 'pylint: C0303 Trailing whitespace',
severity:1},
{lineStart:6,
lineEnd:6,
columnStart:1,
columnEnd:25,
description: 'pylint: C0304 Final newline missing',
severity:1},
{
lineStart:1,
lineEnd:1,
columnStart:1,
columnEnd:17,
description: 'pylint: C0111 Missing module docstring',
severity:1 },
{
lineStart:1,
lineEnd:1,
columnStart:1,
columnEnd:17,
description: 'pylint: C0103 Invalid class name "C"',
severity:1 },
{
lineStart:1,
lineEnd:1,
columnStart:1,
columnEnd:17,
description: 'pylint: C0111 Missing class docstring',
severity:1 },
{
lineStart:2,
lineEnd:2,
columnStart:1,
columnEnd:31,
description: 'pylint: C0103 Invalid argument name "a"',
severity:1 },
{
lineStart:2,
lineEnd:2,
columnStart:1,
columnEnd:31,
description: 'pylint: C0103 Invalid argument name "b"',
severity:1 },
{
lineStart:2,
lineEnd:2,
columnStart:1,
columnEnd:31,
description: 'pylint: C0111 Missing method docstring',
severity:1 },
{
lineStart:2,
lineEnd:2,
columnStart:1,
columnEnd:31,
description: "pylint: W0613 Unused argument 'b'",
severity:1 },
{
lineStart:2,
lineEnd:2,
columnStart:1,
columnEnd:31,
description: 'pylint: R0201 Method could be a function',
severity:1 },
{
lineStart:1,
lineEnd:1,
columnStart:1,
columnEnd:17,
description: 'pylint: R0903 Too few public methods (1/2)',
severity:1 },
{
lineStart:5,
lineEnd:5,
columnStart:1,
columnEnd:8,
description: 'pylint: C0103 Invalid constant name "c"',
severity:1 },
    ];
    var origBuf = origLines.join("\n");
    var view = new ko.views.ViewMock({text:origBuf});
    file.puts(origBuf);
    file.close();
    var koDoc = this.docSvc.createNewDocumentFromURI(file.URI);
    koDoc.new_line_endings = this.koIDocument.EOL_LF;
    koDoc.language = "Python";
    // Set the buffer before assigning the view, otherwise it will fail.
    var origBugUTF = this.encodingSvc.encode(origBuf, "utf-8", "")
    koDoc.setBufferAndEncoding(origBugUTF, "utf-8");
    view.koDoc = koDoc;
    //koDoc.addView(view.scintilla);
    var scimoz = view.scimoz;
    
    var lintSvc = Components.classes["@activestate.com/koLintService;1"].
                    getService(Components.interfaces.koILintService);
    var lr = Components.classes["@activestate.com/koLintRequest;1"].
                createInstance(Components.interfaces.koILintRequest);
    lr.rid = 1;
    lr.koDoc = koDoc;
    scimoz.colourise(0, -1);
    lr.linterType = koDoc.language;
    lr.uid = 3;
    lr.cwd = koDoc.file.dirname;
    lr.lintBuffer = this;
    lr.alwaysLint = true;
    // All other prefs are turned off
    this.globalPrefs.setBooleanPref("lint_python_with_pylint", true);
    this.globalPrefs.setStringPref("pylint_checking_rcfile", "");
    
    this.expectedNumTests = this.expectedMessages.length * 6;
    this.finalResult = false;
    lintSvc.addRequest(lr);
    // We fired a lint request, now stay alive so the callback can start working.
    stopTime = Date.now() + 10000; // time in msec
    while (Date.now() < stopTime) {
        Services.tm.mainThread.processNextEvent(false);
    }
    this.assertTrue(this.finalResult);
};

TestPylint.prototype.test_python_01 = function test_python_01() {
    //this.log.debug("\n\n\ntest_revert_01:\n\n\n")
    if (!this.pythonInfoSvc.executablePath) {
        throw SkipTest("python not installed");
    }
    var file = this.fileSvc.makeTempFile(".py", 'wb');
    var origLines = [ 'class C(object):'
                     ,'    def only_func(self, a, b)'
                     ,'        return a + 3'
                     ,'    '
                     ,'c = C('
                     ,'print(c.only_func(5, 7))'
                    ];
    this.expectedMessages = [
{lineStart:2,
lineEnd:2,
columnStart:1,
columnEnd:30,
description: 'SyntaxError: invalid syntax (at column 30)',
severity:2}
    ];
    var origBuf = origLines.join("\n");
    var view = new ko.views.ViewMock({text:origBuf});
    file.puts(origBuf);
    file.close();
    var koDoc = this.docSvc.createNewDocumentFromURI(file.URI);
    koDoc.new_line_endings = this.koIDocument.EOL_LF;
    koDoc.language = "Python";
    // Set the buffer before assigning the view, otherwise it will fail.
    var origBugUTF = this.encodingSvc.encode(origBuf, "utf-8", "")
    koDoc.setBufferAndEncoding(origBugUTF, "utf-8");
    view.koDoc = koDoc;
    //koDoc.addView(view.scintilla);
    var scimoz = view.scimoz;
    
    var lintSvc = Components.classes["@activestate.com/koLintService;1"].
                    getService(Components.interfaces.koILintService);
    var lr = Components.classes["@activestate.com/koLintRequest;1"].
                createInstance(Components.interfaces.koILintRequest);
    lr.rid = 1;
    lr.koDoc = koDoc;
    scimoz.colourise(0, -1);
    lr.linterType = koDoc.language;
    lr.uid = 3;
    lr.cwd = koDoc.file.dirname;
    lr.lintBuffer = this;
    lr.alwaysLint = true;
    // All other prefs are turned off
    this.globalPrefs.setBooleanPref("lint_python_with_standard_python", true);
    ////////this.globalPrefs.setStringPref("pythonDefaultInterpreter", "c:\\python27\\python.exe");
    
    this.expectedNumTests = this.expectedMessages.length * 6;
    this.finalResult = false;
    lintSvc.addRequest(lr);
    // We fired a lint request, now stay alive so the callback can start working.
    stopTime = Date.now() + 10000; // time in msec
    while (Date.now() < stopTime) {
        Services.tm.mainThread.processNextEvent(false);
    }
    this.assertTrue(this.finalResult);
};


TestPylint.prototype.test_pylint3_01 = function test_pylint3_01() {
    //this.log.debug("\n\n\ntest_revert_01:\n\n\n")
    // Make sure we have pylint available, otherwise skip this test
    if (!this.python3InfoSvc.executablePath) {
        throw SkipTest("python3 not installed");
    }
    if (!this.python3InfoSvc.haveModules(2, ["pylint", "astroid.utils"])) {
        throw SkipTest("pylint not installed for python3");
    }
    var file = this.fileSvc.makeTempFile(".py", 'wb');
    var origLines = [ 'class C(object):'
                     ,'    def only_func(self, a, b):'
                     ,'        return a + 3'
                     ,'    '
                     ,'c = C()'
                     ,'print(c.only_func(5, 7))'
                    ];
    this.expectedMessages = [
{lineStart:4,
lineEnd:4,
columnStart:1,
columnEnd:5,
description: 'pylint: C0303 Trailing whitespace',
severity:1},
{lineStart:6,
lineEnd:6,
columnStart:1,
columnEnd:25,
description: 'pylint: C0304 Final newline missing',
severity:1},
{
lineStart:1,
lineEnd:1,
columnStart:1,
columnEnd:17,
description: 'pylint: C0111 Missing module docstring',
severity:1 },
{
lineStart:1,
lineEnd:1,
columnStart:1,
columnEnd:17,
description: 'pylint: C0103 Invalid class name "C"',
severity:1 },
{
lineStart:1,
lineEnd:1,
columnStart:1,
columnEnd:17,
description: 'pylint: C0111 Missing class docstring',
severity:1 },
{
lineStart:2,
lineEnd:2,
columnStart:1,
columnEnd:31,
description: 'pylint: C0103 Invalid argument name "a"',
severity:1 },
{
lineStart:2,
lineEnd:2,
columnStart:1,
columnEnd:31,
description: 'pylint: C0103 Invalid argument name "b"',
severity:1 },
{
lineStart:2,
lineEnd:2,
columnStart:1,
columnEnd:31,
description: 'pylint: C0111 Missing method docstring',
severity:1 },
{
lineStart:2,
lineEnd:2,
columnStart:1,
columnEnd:31,
description: "pylint: W0613 Unused argument 'b'",
severity:1 },
{
lineStart:2,
lineEnd:2,
columnStart:1,
columnEnd:31,
description: 'pylint: R0201 Method could be a function',
severity:1 },
{
lineStart:1,
lineEnd:1,
columnStart:1,
columnEnd:17,
description: 'pylint: R0903 Too few public methods (1/2)',
severity:1 },
{
lineStart:5,
lineEnd:5,
columnStart:1,
columnEnd:8,
description: 'pylint: C0103 Invalid constant name "c"',
severity:1 },
    ];
    var origBuf = origLines.join("\n");
    var view = new ko.views.ViewMock({text:origBuf});
    file.puts(origBuf);
    file.close();
    var koDoc = this.docSvc.createNewDocumentFromURI(file.URI);
    koDoc.new_line_endings = this.koIDocument.EOL_LF;
    koDoc.language = "Python3";
    // Set the buffer before assigning the view, otherwise it will fail.
    var origBugUTF = this.encodingSvc.encode(origBuf, "utf-8", "")
    koDoc.setBufferAndEncoding(origBugUTF, "utf-8");
    view.koDoc = koDoc;
    //koDoc.addView(view.scintilla);
    var scimoz = view.scimoz;
    
    var lintSvc = Components.classes["@activestate.com/koLintService;1"].
                    getService(Components.interfaces.koILintService);
    var lr = Components.classes["@activestate.com/koLintRequest;1"].
                createInstance(Components.interfaces.koILintRequest);
    lr.rid = 1;
    lr.koDoc = koDoc;
    scimoz.colourise(0, -1);
    lr.linterType = koDoc.language;
    lr.uid = 3;
    lr.cwd = koDoc.file.dirname;
    lr.lintBuffer = this;
    lr.alwaysLint = true;
    // All other prefs are turned off
    this.globalPrefs.setBooleanPref("lint_python3_with_pylint3", true);
    this.globalPrefs.setStringPref("pylint3_checking_rcfile", "");
    
    this.expectedNumTests = this.expectedMessages.length * 6;
    this.finalResult = false;
    lintSvc.addRequest(lr);
    // We fired a lint request, now stay alive so the callback can start working.
    stopTime = Date.now() + 10000; // time in msec
    while (Date.now() < stopTime) {
        Services.tm.mainThread.processNextEvent(false);
    }
    this.assertTrue(this.finalResult);
};

TestPylint.prototype.test_python3_01 = function test_python3_01() {
    if (!this.python3InfoSvc.executablePath) {
        throw SkipTest("python3 not installed");
    }
    //this.log.debug("\n\n\ntest_revert_01:\n\n\n")
    var file = this.fileSvc.makeTempFile(".py", 'wb');
    var origLines = [ 'class C(object):'
                     ,'    def only_func(self, a, b)'
                     ,'        return a + 3'
                     ,'    '
                     ,'c = C('
                     ,'print(c.only_func(5, 7))'
                    ];
    this.expectedMessages = [
{lineStart:2,
lineEnd:2,
columnStart:1,
columnEnd:30,
description: 'SyntaxError: invalid syntax (at column 30)',
severity:2}
    ];
    var origBuf = origLines.join("\n");
    var view = new ko.views.ViewMock({text:origBuf});
    file.puts(origBuf);
    file.close();
    var koDoc = this.docSvc.createNewDocumentFromURI(file.URI);
    koDoc.new_line_endings = this.koIDocument.EOL_LF;
    koDoc.language = "Python3";
    // Set the buffer before assigning the view, otherwise it will fail.
    var origBugUTF = this.encodingSvc.encode(origBuf, "utf-8", "")
    koDoc.setBufferAndEncoding(origBugUTF, "utf-8");
    view.koDoc = koDoc;
    //koDoc.addView(view.scintilla);
    var scimoz = view.scimoz;
    
    var lintSvc = Components.classes["@activestate.com/koLintService;1"].
                    getService(Components.interfaces.koILintService);
    var lr = Components.classes["@activestate.com/koLintRequest;1"].
                createInstance(Components.interfaces.koILintRequest);
    lr.rid = 1;
    lr.koDoc = koDoc;
    scimoz.colourise(0, -1);
    lr.linterType = koDoc.language;
    lr.uid = 3;
    lr.cwd = koDoc.file.dirname;
    lr.lintBuffer = this;
    lr.alwaysLint = true;
    // All other prefs are turned off
    this.globalPrefs.setBooleanPref("lint_python3_with_standard_python", true);
    ////////this.globalPrefs.setStringPref("pythonDefaultInterpreter", "c:\\python27\\python.exe");
    
    this.expectedNumTests = this.expectedMessages.length * 6;
    this.finalResult = false;
    lintSvc.addRequest(lr);
    // We fired a lint request, now stay alive so the callback can start working.
    stopTime = Date.now() + 10000; // time in msec
    while (Date.now() < stopTime) {
        Services.tm.mainThread.processNextEvent(false);
    }
    this.assertTrue(this.finalResult);
};

// this.reportResults is called by lintSvc
TestPylint.prototype.reportResults = function reportResults(request) {
    var results = request.results;
    var numTestsRun = 0;
    try {
        var displayableResults;
        if (results === null) {
            displayableResults = [];
        } else {
            var displayableResults = {};
            results.getResultsInLineRange(1, 10000, displayableResults, {});
            displayableResults = displayableResults.value;
        }
        var lim = displayableResults.length;
        this.assertEqual(this.expectedMessages.length, lim);
        for (let i = 0; i < lim; ++i) {
            let expectedBlock = this.expectedMessages[i];
            var r = displayableResults[i];
            for (let p in expectedBlock) {
                this.assertEqual(expectedBlock[p], r[p],
                                 "Failed r[" + i + "]:, property:"
                                 + p
                                 + ", expectedValue: "
                                 + expectedBlock[p] + ", got " + r[p]);
                numTestsRun++;
            }
        }
        this.assertEqual(this.expectedNumTests, numTestsRun);
        this.finalResult = true;
    } catch(ex) {
        this.log.exception(ex, "test failed");
        this.finalResult = false;
    }
};

var JS_TESTS = ["TestPylint"];