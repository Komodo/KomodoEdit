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

// Each TestPylintRC object is created once per test, not like Python, so we have
// to use a module var make sure a class-like method is called only once.
var didInitRCFile = false;

var TestPylintRC = function TestPylintRC() {
    this.log = null;
    this.log = logging.getLogger("lint.pylint");
    this.log.setLevel(ko.logging.LOG_DEBUG);
}
TestPylintRC.prototype = new TestCase();

TestPylintRC.prototype.setUp = function TestPylintCommon_setUp() {
    var prefs;
    prefs = this.globalPrefs = Cc["@activestate.com/koPrefService;1"].getService(Ci.koIPrefService).prefs;
    this.fileSvc = Cc["@activestate.com/koFileService;1"].getService(Ci.koIFileService);
    this.docSvc = Cc["@activestate.com/koDocumentService;1"].getService(Ci.koIDocumentService);
    this.encodingSvc = Cc["@activestate.com/koEncodingServices;1"].getService(Ci.koIEncodingServices);
    this.pythonInfoSvc = Cc["@activestate.com/koAppInfoEx?app=Python;1"].getService(Ci.koIAppInfoEx);
    this.python3InfoSvc = Cc["@activestate.com/koAppInfoEx?app=Python3;1"].getService(Ci.koIAppInfoEx);
    this.lintSvc = Cc["@activestate.com/koLintService;1"].getService(Ci.koILintService);
    this.koIDocument = Ci.koIDocument;
    
    var pyLintNames = prefs.getAllPrefIds().
        filter(function(x) (x.indexOf("lint_python") === 0
                            && prefs.getPrefType(x) == "boolean"));
               
    this.origBooleanPrefs = {
      editUseLinting: prefs.getBooleanPref("editUseLinting")
    };
    pyLintNames.forEach(function(x) {
        this.origBooleanPrefs[x] = prefs.getBooleanPref(x);
    }.bind(this));
    this.origStringPrefs = {
      pylint_checking_rcfile: prefs.getStringPref("pylint_checking_rcfile"),
      pylint3_checking_rcfile: prefs.getStringPref("pylint3_checking_rcfile"),
      pythonDefaultInterpreter: prefs.getStringPref("pythonDefaultInterpreter"),
      python3DefaultInterpreter: prefs.getStringPref("python3DefaultInterpreter")
    };
    for (prefName in this.origBooleanPrefs) {
        prefs.setBooleanPref(prefName, false);
    }
    prefs.setBooleanPref("editUseLinting", true);
    prefs.setBooleanPref("lint_python_with_pylint", true);
    
    this.osSvc = Cc["@activestate.com/koOs;1"].getService(Ci.koIOs);
    this.osPathSvc = Cc["@activestate.com/koOsPath;1"].getService(Ci.koIOsPath);
    // And save the .pylintrc file that other tests might modify
    // Set defaults for tearDown
    this.homeDir = this.osPathSvc.expanduser("~");
    this.pylintRcPath = this.pylintRcContents = null;
    try {
        this.pylintRcPath = this.osPathSvc.join(this.homeDir, ".pylintrc");
        if (this.osPathSvc.exists(this.pylintRcPath)) {
            this.pylintRcContents = this.osSvc.readfile(this.pylintRcPath);
        }
    } catch(ex) {
        this.log.exception("Can't find pylintrc");
    }
    this.pythonCode = [ 'class C(object):'
                     ,'    def only_func(self, a, b):'
                     ,'        print("long line: 86.312345678.412345678.512345678.612345678.712345678.812345")'
                     ,'        return a + 3'
                     ,'    '
                     ,'c = C()'
                     ,'print(c.only_func(5, 7))'
                     ,''
                    ];
    if (!didInitRCFile) {
        didInitRCFile = true;
        this._initRCFile();
    }
};

TestPylintRC.prototype._initRCFile = function _initRCFile() {
    if (this.pylintRcContents) {
        // Save .pylintrc into .pylintrc.bak in case something goes wrong
        
        let pylintRcBak = this.osPathSvc.join(this.homeDir, ".pylintrc.bak");
        let writeToBakFile = true;
        if (this.osPathSvc.exists(pylintRcBak)) {
            let pylintBakContents = this.osSvc.readfile(pylintRcBak);
            if (pylintBakContents == this.pylintRcContents) {
                writeToBakFile = false;
            } else {
                this.log.warn("Overwriting "
                              + pylintRcBak
                              + ": had "
                              + pylintBakContents.length
                              + " chars, replacing with a copy of .pylintrc containing "
                              + this.pylintRcContents.length
                              + " chars");
            }
        }
        if (writeToBakFile) {
            this.osSvc.writefile(pylintRcBak, this.pylintRcContents);
        }
    }
};

TestPylintRC.prototype.tearDown = function TestPylintCommon_tearDown() {
    var prefName;
    for (prefName in this.origBooleanPrefs) {
        this.globalPrefs.setBooleanPref(prefName, this.origBooleanPrefs[prefName]);
    }
    for (prefName in this.origStringPrefs) {
        this.globalPrefs.setStringPref(prefName, this.origStringPrefs[prefName]);
    }
    
    if (this.pylintRcContents) {
        this.osSvc.writefile(this.pylintRcPath, this.pylintRcContents);
    }
};

TestPylintRC.prototype.pylintCheck = function pylintCheck() {
    // Make sure we have pylint available, otherwise skip this test
    //this.log.debug(">> pylintCheck")
    //this.log.debug("this.pythonInfoSvc.executablePath: "
    //               + this.pythonInfoSvc.executablePath)
    if (!this.pythonInfoSvc.executablePath) {
        throw SkipTest("python not installed");
    }
    //this.log.debug('this.pythonInfoSvc.haveModules(1, ["pylint"]: '
    //               + this.pythonInfoSvc.haveModules(1, ["pylint"]));
    if (!this.pythonInfoSvc.haveModules(1, ["pylint"])) {
        throw SkipTest("pylint not installed");
    }
}

TestPylintRC.prototype.msgHandler =
function TestPylintRC_msgHandler(level, context, message) {
    this.fail("Message handler called in quiet mode: " +
              "level=" + level + " context=" + context +
              " message=" + message + "\n");
};

TestPylintRC.prototype._setupCommonParts =
function _setupCommonParts() {
    var file = this.fileSvc.makeTempFile(".py", 'wb');
    var origBuf = this.pythonCode.join("\n");
    var view = new ko.views.ViewMock({text:origBuf});
    file.puts(origBuf);
    file.close();
    var koDoc = this.docSvc.createNewDocumentFromURI(file.URI);
    koDoc.new_line_endings = this.koIDocument.EOL_LF;
    koDoc.language = "Python";
    koDoc.buffer = origBuf;
    koDoc.prefs.setLongPref("editAutoWrapColumn", 80);
    var scimoz = view.scimoz;
    
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
    return lr;
};

TestPylintRC.prototype.test_usingNoPylintrc = function test_usingNoPylintrc() {
    this.pylintCheck();
    if (this.pylintRcPath) {
        this.osSvc.writefile(this.pylintRcPath, "");
    }
    var lr = this._setupCommonParts();
    // All other prefs are turned off
    this.globalPrefs.setStringPref("pylint_checking_rcfile", this.pylintRcPath);
    
    this.expectedMessages = [
{
  lineStart:3,
  lineEnd:3,
  columnStart:1,
  columnEnd:88,
  description: "pylint: C0301 Line too long (87/80)",
  severity:1
},
{
  lineStart:5,
  lineEnd:5,
  columnStart:1,
  columnEnd:5,
  description:"pylint: C0303 Trailing whitespace",
  severity:1,
},
{
  lineStart:1,
  lineEnd:1,
  columnStart:1,
  columnEnd:17,
  description:"pylint: C0111 Missing module docstring",
  severity:1,
},
{
  lineStart:1,
  lineEnd:1,
  columnStart:1,
  columnEnd:17,
  description:"pylint: C0103 Invalid class name \"C\"",
  severity:1,
},
{
  lineStart:1,
  lineEnd:1,
  columnStart:1,
  columnEnd:17,
  description:"pylint: C0111 Missing class docstring",
  severity:1,
},
{
  lineStart:2,
  lineEnd:2,
  columnStart:1,
  columnEnd:31,
  description:"pylint: C0103 Invalid argument name \"a\"",
  severity:1,
},
{
  lineStart:2,
  lineEnd:2,
  columnStart:1,
  columnEnd:31,
  description:"pylint: C0103 Invalid argument name \"b\"",
  severity:1,
},
{
  lineStart:2,
  lineEnd:2,
  columnStart:1,
  columnEnd:31,
  description:"pylint: C0111 Missing method docstring",
  severity:1,
},
{
  lineStart:2,
  lineEnd:2,
  columnStart:1,
  columnEnd:31,
  description:"pylint: W0613 Unused argument 'b'",
  severity:1,
},
{
  lineStart:2,
  lineEnd:2,
  columnStart:1,
  columnEnd:31,
  description:"pylint: R0201 Method could be a function",
  severity:1,
},
{
  lineStart:1,
  lineEnd:1,
  columnStart:1,
  columnEnd:17,
  description:"pylint: R0903 Too few public methods (1/2)",
  severity:1,
},
{
  lineStart:6,
  lineEnd:6,
  columnStart:1,
  columnEnd:8,
  description:"pylint: C0103 Invalid constant name \"c\"",
  severity:1,
}
        ];
    this._finishTest(lr)
}

TestPylintRC.prototype.test_usingChangedDefaultPylintrc = function test_usingChangedDefaultPylintrc() {
    this.pylintCheck();
    if (this.pylintRcPath) {
        let newContents = [
             '[MESSAGES CONTROL]'
            ,'disable=C0303'
            ,'[FORMAT]'
            ,'max-line-length=100'
        ]
        this.osSvc.writefile(this.pylintRcPath, newContents.join("\n"));
    }
    var lr = this._setupCommonParts();
    // All other prefs are turned off
    this.globalPrefs.setStringPref("pylint_checking_rcfile", "");
    
    this.expectedMessages = [
{
  lineStart:1,
  lineEnd:1,
  columnStart:1,
  columnEnd:17,
  description:"pylint: C0111 Missing module docstring",
  severity:1,
},
{
  lineStart:1,
  lineEnd:1,
  columnStart:1,
  columnEnd:17,
  description:"pylint: C0103 Invalid class name \"C\"",
  severity:1,
},
{
  lineStart:1,
  lineEnd:1,
  columnStart:1,
  columnEnd:17,
  description:"pylint: C0111 Missing class docstring",
  severity:1,
},
{
  lineStart:2,
  lineEnd:2,
  columnStart:1,
  columnEnd:31,
  description:"pylint: C0103 Invalid argument name \"a\"",
  severity:1,
},
{
  lineStart:2,
  lineEnd:2,
  columnStart:1,
  columnEnd:31,
  description:"pylint: C0103 Invalid argument name \"b\"",
  severity:1,
},
{
  lineStart:2,
  lineEnd:2,
  columnStart:1,
  columnEnd:31,
  description:"pylint: C0111 Missing method docstring",
  severity:1,
},
{
  lineStart:2,
  lineEnd:2,
  columnStart:1,
  columnEnd:31,
  description:"pylint: W0613 Unused argument 'b'",
  severity:1,
},
{
  lineStart:2,
  lineEnd:2,
  columnStart:1,
  columnEnd:31,
  description:"pylint: R0201 Method could be a function",
  severity:1,
},
{
  lineStart:1,
  lineEnd:1,
  columnStart:1,
  columnEnd:17,
  description:"pylint: R0903 Too few public methods (1/2)",
  severity:1,
},
{
  lineStart:6,
  lineEnd:6,
  columnStart:1,
  columnEnd:8,
  description:"pylint: C0103 Invalid constant name \"c\"",
  severity:1,
}
        ];
    this._finishTest(lr)
};

TestPylintRC.prototype.test_usingChangedExplicitDefaultPylintrc = function test_usingChangedExplicitDefaultPylintrc() {
    this.pylintCheck();
    if (!this.pylintRcPath) {
        throw SkipTest("Can't figure out where ~/.pylintrc is");
    }
    let newContents = [
         '[MESSAGES CONTROL]'
        ,'disable=C0303,C0103'
        ,'[FORMAT]'
        ,'max-line-length=100'
    ]
    this.osSvc.writefile(this.pylintRcPath, newContents.join("\n"));
    var lr = this._setupCommonParts();
    // All other prefs are turned off
    this.globalPrefs.setStringPref("pylint_checking_rcfile", this.pylintRcPat);
    
    this.expectedMessages = [
{
  lineStart:1,
  lineEnd:1,
  columnStart:1,
  columnEnd:17,
  description:"pylint: C0111 Missing module docstring",
  severity:1,
},
{
  lineStart:1,
  lineEnd:1,
  columnStart:1,
  columnEnd:17,
  description:"pylint: C0111 Missing class docstring",
  severity:1,
},
{
  lineStart:2,
  lineEnd:2,
  columnStart:1,
  columnEnd:31,
  description:"pylint: C0111 Missing method docstring",
  severity:1,
},
{
  lineStart:2,
  lineEnd:2,
  columnStart:1,
  columnEnd:31,
  description:"pylint: W0613 Unused argument 'b'",
  severity:1,
},
{
  lineStart:2,
  lineEnd:2,
  columnStart:1,
  columnEnd:31,
  description:"pylint: R0201 Method could be a function",
  severity:1,
},
{
  lineStart:1,
  lineEnd:1,
  columnStart:1,
  columnEnd:17,
  description:"pylint: R0903 Too few public methods (1/2)",
  severity:1,
}
        ];
    this._finishTest(lr)
};

TestPylintRC.prototype.test_usingCustomPylintrc = function test_usingCustomPylintrc() {
    this.pylintCheck();
    if (!this.pylintRcPath) {
        throw SkipTest("Can't figure out where ~/.pylintrc is");
    }
    let newContents = [
         '[MESSAGES CONTROL]'
        ,'disable=C0303,C0103,C0111'
        ,'[FORMAT]'
        ,'max-line-length=100'
    ]
    this.osSvc.writefile(this.pylintRcPath, "");
    var tmpPylintRcPath = this.fileSvc.makeTempFile(".pylintrc", 'wb');
    this.osSvc.writefile(this.pylintRcPath, newContents.join("\n"));
    var lr = this._setupCommonParts();
    this.globalPrefs.setStringPref("pylint_checking_rcfile", tmpPylintRcPath);
    
    this.expectedMessages = [
{
  lineStart:2,
  lineEnd:2,
  columnStart:1,
  columnEnd:31,
  description:"pylint: W0613 Unused argument 'b'",
  severity:1,
},
{
  lineStart:2,
  lineEnd:2,
  columnStart:1,
  columnEnd:31,
  description:"pylint: R0201 Method could be a function",
  severity:1,
},
{
  lineStart:1,
  lineEnd:1,
  columnStart:1,
  columnEnd:17,
  description:"pylint: R0903 Too few public methods (1/2)",
  severity:1,
}
        ];
    this._finishTest(lr)
    this.fileSvc.deleteTempFile(tmpPylintRcPath, true);
};

TestPylintRC.prototype._finishTest = function _finishTest(lr) {
    this.expectedNumTests = this.expectedMessages.length * 6;
    this.finalResult = false;
    this.lintSvc.addRequest(lr);
    // We fired a lint request, now stay alive so the callback can start working.
    stopTime = Date.now() + 10000; // time in msec
    while (Date.now() < stopTime) {
        Services.tm.mainThread.processNextEvent(false);
    }
    this.assertTrue(this.finalResult);
        
};

// this.reportResults is called by lintSvc
TestPylintRC.prototype.reportResults = function reportResults(request) {
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
        //this.log.debug("Got " + lim + " displayableResults");
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
var JS_TESTS = ["TestPylintRC"];