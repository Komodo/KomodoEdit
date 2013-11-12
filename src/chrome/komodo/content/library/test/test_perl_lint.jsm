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

var TestPerlLint = function TestPerlLint() {
    this.log = null;
    this.log = logging.getLogger("lint.perlLint");
    this.log.setLevel(ko.logging.LOG_DEBUG);
}
TestPerlLint.prototype = new TestCase();

TestPerlLint.prototype.setUp = function TestPerlLint_setUp() {
    let loader = Cc['@mozilla.org/moz/jssubscript-loader;1']
                   .getService(Ci.mozIJSSubScriptLoader);
    this.scope = { ko: ko, __noSuchMethod__: function() {}};
    this.globalPrefs = Cc["@activestate.com/koPrefService;1"].getService(Ci.koIPrefService).prefs;
    this.fileSvc = Cc["@activestate.com/koFileService;1"].getService(Ci.koIFileService);
    this.docSvc = Cc["@activestate.com/koDocumentService;1"].getService(Ci.koIDocumentService);
    this.encodingSvc = Cc["@activestate.com/koEncodingServices;1"].getService(Ci.koIEncodingServices);
    this.perlInfoSvc = Cc["@activestate.com/koAppInfoEx?app=Perl;1"].getService(Ci.koIAppInfoEx);
    this.OSPathSvc = Cc["@activestate.com/koOsPath;1"].getService(Ci.koIOsPath);
    this.koIDocument = Ci.koIDocument;
    var this_ = this;
    this.origBooleanPrefs = {
      editUseLinting: this.globalPrefs.getBooleanPref("editUseLinting"),
      perl_lintOption_includeCurrentDirForLinter: this.globalPrefs.getBooleanPref("perl_lintOption_includeCurrentDirForLinter"),
      perl_lintOption_disableBeginBlocks: this.globalPrefs.getBooleanPref("perl_lintOption_disableBeginBlocks")
    };
    this.origStringPrefs = {
      perl_lintOption: this.globalPrefs.getStringPref("perl_lintOption"),
      perl_lintOption_perlCriticLevel: this.globalPrefs.getStringPref("perl_lintOption_perlCriticLevel"),
      perlcritic_checking_rcfile: this.globalPrefs.getStringPref("perlcritic_checking_rcfile")
    };
    for (prefName in this.origBooleanPrefs) {
        this.globalPrefs.setBooleanPref(prefName, false);
    }
    for (prefName in this.origStringPrefs) {
        this.globalPrefs.setStringPref(prefName, "");
    }
    this.globalPrefs.setBooleanPref("editUseLinting", true);
    this.globalPrefs.setBooleanPref("perl_lintOption_disableBeginBlocks", true);
    this.globalPrefs.setStringPref("perl_lintOption", "cw");
};

TestPerlLint.prototype.tearDown = function TestPerlLint_tearDown() {
    var prefName;
    for (prefName in this.origBooleanPrefs) {
        this.globalPrefs.setBooleanPref(prefName, this.origBooleanPrefs[prefName]);
    }
    for (prefName in this.origStringPrefs) {
        this.globalPrefs.setStringPref(prefName, this.origStringPrefs[prefName]);
    }
};

TestPerlLint.prototype.msgHandler =
function TestPerlLint_msgHandler(level, context, message) {
    this.fail("Message handler called in quiet mode: " +
              "level=" + level + " context=" + context +
              " message=" + message + "\n");
};

TestPerlLint.prototype.test_perl_lint_01 = function test_pylint_01() {
    //this.log.debug("\n\n\ntest_revert_01:\n\n\n")
    // Make sure we have pylint available, otherwise skip this test
    if (!this.perlInfoSvc.executablePath) {
        throw SkipTest("perl not installed");
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
{
  lineStart:1,
  lineEnd:1,
  columnStart:1,
  columnEnd:17,
  description:"Unquoted string \"object\" may clash with future reserved word.",
  severity:2
},
{
  lineStart:2,
  lineEnd:2,
  columnStart:1,
  columnEnd:31,
  description:"Unquoted string \"self\" may clash with future reserved word.",
  severity:2
},
{
  lineStart:2,
  lineEnd:2,
  columnStart:1,
  columnEnd:31,
  description:"Unquoted string \"a\" may clash with future reserved word.",
  severity:2
},
{
  lineStart:2,
  lineEnd:2,
  columnStart:1,
  columnEnd:31,
  description:"Unquoted string \"b\" may clash with future reserved word.",
  severity:2
},
{
  lineStart:3,
  lineEnd:3,
  columnStart:1,
  columnEnd:21,
  description:"Unquoted string \"a\" may clash with future reserved word.",
  severity:2
},
{
  lineStart:4,
  lineEnd:4,
  columnStart:1,
  columnEnd:5,
  description:"Semicolon seems to be missing.",
  severity:2
},
{
  lineStart:5,
  lineEnd:5,
  columnStart:1,
  columnEnd:8,
  description:"Unquoted string \"c\" may clash with future reserved word.",
  severity:2
},
{
  lineStart:6,
  lineEnd:6,
  columnStart:1,
  columnEnd:25,
  description:"Unquoted string \"c\" may clash with future reserved word.",
  severity:2
},
{
  lineStart:1,
  lineEnd:1,
  columnStart:1,
  columnEnd:17,
  // Here we would get the temporary name, so don't test, and remember to update this.expectedNumTests
  //description:"D:\Users\ericp\lab\komodo\bugs\python3\pylint02.py had compilation errors.\nsyntax error, near \"):\"",
  severity:2
}
    ];
    var origBuf = origLines.join("\n");
    var view = new ko.views.ViewMock({text:origBuf});
    file.puts(origBuf);
    file.close();
    var koDoc = this.docSvc.createNewDocumentFromURI(file.URI);
    koDoc.new_line_endings = this.koIDocument.EOL_LF;
    koDoc.language = "Perl";
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
    this.globalPrefs.setStringPref("perl_lintOption", "cw");
    this.globalPrefs.setStringPref("perl_lintOption_perlCriticLevel", "off");
    
    
    this.expectedNumTests = this.expectedMessages.length * 6 - 1;
    this.finalResult = false;
    lintSvc.addRequest(lr);
    // We fired a lint request, now stay alive so the callback can start working.
    stopTime = Date.now() + 10000; // time in msec
    while (Date.now() < stopTime) {
        Services.tm.mainThread.processNextEvent(false);
    }
    this.assertTrue(this.finalResult);
};
TestPerlLint.prototype.test_perl_critic_01 = function test_perl_critic_01() {
    //this.log.debug("\n\n\ntest_revert_01:\n\n\n")
    // Make sure we have pylint available, otherwise skip this test
    if (!this.perlInfoSvc.executablePath) {
        throw SkipTest("perl not installed");
    }
    if (!this.perlInfoSvc.isPerlCriticInstalled(/*forceCheck=*/true)) {
        throw SkipTest("perlCritic not installed");
    }
    var file = this.fileSvc.makeTempFile(".pl", 'wb');
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
{
  lineStart:1,
  lineEnd:1,
  columnStart:1,
  columnEnd:46,
  description:"Code is not tidy.",
  severity:1
},
{
  lineStart:1,
  lineEnd:1,
  columnStart:1,
  columnEnd:46,
  description:"Code not contained in explicit package.",
  severity:1
},
{
  lineStart:1,
  lineEnd:1,
  columnStart:1,
  columnEnd:46,
  description:"No package-scoped \"$VERSION\" variable found.",
  severity:1
},
{
  lineStart:9,
  lineEnd:9,
  columnStart:1,
  columnEnd:83,
  description:"Return value of flagged function ignored - print.",
  severity:1
},
{
  lineStart:9,
  lineEnd:9,
  columnStart:1,
  columnEnd:83,
  description:"Useless interpolation of literal string.",
  severity:1
},
{
  lineStart:12,
  lineEnd:12,
  columnStart:1,
  columnEnd:40,
  description:"Module does not end with \"1;\".",
  severity:1
},
{
  lineStart:12,
  lineEnd:12,
  columnStart:1,
  columnEnd:40,
  description:"Builtin function called with parentheses.",
  severity:1
},
    ];
    var origBuf = origLines.join("\n");
    var view = new ko.views.ViewMock({text:origBuf});
    file.puts(origBuf);
    file.close();
    var koDoc = this.docSvc.createNewDocumentFromURI(file.URI);
    koDoc.new_line_endings = this.koIDocument.EOL_LF;
    koDoc.language = "Perl";
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
    this.globalPrefs.setStringPref("perl_lintOption", "cw");
    this.globalPrefs.setStringPref("perl_lintOption_perlCriticLevel", "brutal");
    
    
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

TestPerlLint.prototype.test_no_begin_in_linting = function test_no_begin_in_linting() {
    //this.log.debug("\n\n\ntest_revert_01:\n\n\n")
    // Make sure we have pylint available, otherwise skip this test
    if (!this.perlInfoSvc.executablePath) {
        throw SkipTest("perl not installed");
    }
    if (!this.perlInfoSvc.isPerlCriticInstalled(/*forceCheck=*/true)) {
        throw SkipTest("perlCritic not installed");
    }
    var file = this.fileSvc.makeTempFile(".pl", 'wb');  // file created
    var textFile = this.fileSvc.makeTempName('.txt').replace(/\\/g, '/');  // file not created
    this.assertFalse(this.OSPathSvc.exists(textFile));
    
    
    // First, delete $TEMP/blix.txt
    var origLines = [ '#!/usr/bin/perl -w'
                 ,'use strict;'
                 ,'use warnings;'
                 ,''
                 ,'BEGIN {'
                    ,'    my $stuff = 3;'
                    ,'    open my $fd, ">", "' + textFile + '" or die "Can\'t create file: $!";'
                    ,'    print $fd "Uh oh\\n";'
                    ,'    close $fd;'
                 ,'}'
                 ,''
                 ,'my $abc = 3;'
                 ,'print "$abc\\n";'
                ];
    // We don't care about the lint output here,
    // only if the BEGIN block is run or not.
    this.expectedMessages = [];
    var origBuf = origLines.join("\n");
    var view = new ko.views.ViewMock({text:origBuf});
    file.puts(origBuf);
    file.close();
    var koDoc = this.docSvc.createNewDocumentFromURI(file.URI);
    koDoc.new_line_endings = this.koIDocument.EOL_LF;
    koDoc.language = "Perl";
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
    this.globalPrefs.setStringPref("perl_lintOption", "cw");
    this.globalPrefs.setStringPref("perl_lintOption_perlCriticLevel", "off");
    
    lintSvc.addRequest(lr);
    // We fired a lint request, now stay alive so the callback can start working.
    stopTime = Date.now() + 10000; // time in msec
    while (Date.now() < stopTime) {
        Services.tm.mainThread.processNextEvent(false);
    }
    // And verify the file still doesn't exist
    var tempFileExists = this.OSPathSvc.exists(textFile);
    if (tempFileExists) {
        this.fileSvc.deleteTempFile(textFile, true);
        this.assertFalse(tempFileExists, "File " + textFile + " shouldn't have been created");
    } else {
        this.assertFalse(false, "Test passed");
    }
    
    // And now verify the file is created if perl_lintOption_disableBeginBlocks is off
    // Build a new lint request object in case the lint changed the above one.
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
    this.globalPrefs.setBooleanPref("perl_lintOption_disableBeginBlocks", false);
    lintSvc.addRequest(lr);
    // We fired a lint request, now stay alive so the callback can start working.
    stopTime = Date.now() + 10000; // time in msec
    while (Date.now() < stopTime) {
        Services.tm.mainThread.processNextEvent(false);
    }
    // And verify the file still doesn't exist
    this.assertTrue(this.OSPathSvc.exists(textFile), "File " + textFile + " should have been created");
    this.fileSvc.deleteTempFile(textFile, true);
};

// this.reportResults is called by lintSvc
TestPerlLint.prototype.reportResults = function reportResults(request) {
    if (!this.expectedMessages || !this.expectedMessages.length) {
        return;
    }
    var results = request.results;
    var numTestsRun = 0;
    try {
        var displayableResults = {};
        results.getResultsInLineRange(1, 10000, displayableResults, {});
        displayableResults = displayableResults.value;
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

var JS_TESTS = ["TestPerlLint"];