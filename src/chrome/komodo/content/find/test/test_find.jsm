const {classes: Cc, interfaces: Ci, utils: Cu} = Components;
Cu.import("resource://komodo-jstest/JSTest.jsm");
Cu.import("resource://gre/modules/Services.jsm");

var ko = {};
Cu.import("resource://komodo-jstest/mock/mock.jsm", {})
  .import(ko, "logging", "views", "macros", "mru", "history", "stringutils",
          "findresults", "statusbar", "notifications",
          "chrome://komodo/content/library/tabstops.js");

// For some strange reason, we must set "ko.notifications" onto the jetpack
// module, otherwise we'll see "ko.notifications is undefined" and the tests
// will fail.
JetPack.ko.notifications = ko.notifications;

const SciMoz = Components.Constructor("@activestate.com/ISciMozHeadless;1");

/**
 * Premute the given arrays
 * Each parameter given should be an array (an axis); the generator will yield
 * the combination of each axis.  For example,
 *      permute([1, 2], [3, 4], [5, 6])
 * will yield (in some undefined order)
 *      [1, 3, 5], [1, 3, 6], [1, 4, 5], [1, 4, 6], [2, 3, 5], [2, 3, 6],
 *      [2, 4, 5], [2, 4, 6]
 */
function permute(/* axis, axis, axis... */) {
    let axes = Array.slice(arguments);
    let indices = [0 for (i in axes)];
    let last = axes.length - 1;
    for(;;) {
        let results = [];
        for (let i = 0; i < axes.length; ++i) {
            results.push(axes[i][indices[i]]);
        }
        yield results;
        ++indices[last];
        if (indices[last] >= axes[last].length) {
            // hit end of this axes, try the next one
            let i = last;
            for(;;) {
                indices[i] = 0;
                if (--i < 0) return;
                ++indices[i];
                if (indices[i] < axes[i].length) {
                    break;
                }
            }
        }
    }
}

let {FOT_SIMPLE, FOT_WILDCARD, FOT_REGEX_PYTHON,
     FOC_INSENSITIVE, FOC_SENSITIVE, FOC_SMART } = Ci.koIFindOptions;
/**
 * pre-canned test cases - given a type/case sensitivity/pattern, should we
 * expect to match the string "Hello"? (sometimes-case-sensitive)
 */
let setups = [
    // type,            case,            pattern,  match expected?
    [ FOT_SIMPLE,       FOC_INSENSITIVE, "hEllO",  true  ],
    [ FOT_SIMPLE,       FOC_SENSITIVE,   "Hello",  true  ],
    [ FOT_SIMPLE,       FOC_SENSITIVE,   "hello",  false ],
    [ FOT_SIMPLE,       FOC_SMART,       "hello",  true  ],
    [ FOT_SIMPLE,       FOC_SMART,       "Hello",  true  ],
    [ FOT_SIMPLE,       FOC_SMART,       "helLO",  false ],
    [ FOT_WILDCARD,     FOC_INSENSITIVE, "h?L?O",  true  ],
    [ FOT_WILDCARD,     FOC_SENSITIVE,   "H?l?o",  true  ],
    [ FOT_WILDCARD,     FOC_SENSITIVE,   "H?L?o",  false ],
    [ FOT_WILDCARD,     FOC_SMART,       "h?l?o",  true  ],
    [ FOT_WILDCARD,     FOC_SMART,       "H?l?o",  true  ],
    [ FOT_WILDCARD,     FOC_SMART,       "h?L?o",  false ],
    [ FOT_REGEX_PYTHON, FOC_INSENSITIVE, "h\\w+o", true  ],
    [ FOT_REGEX_PYTHON, FOC_SENSITIVE,   "H\\w+o", true  ],
    [ FOT_REGEX_PYTHON, FOC_SENSITIVE,   "h\\w+o", false ],
    [ FOT_REGEX_PYTHON, FOC_SMART,       "h\\w+o", true  ],
    [ FOT_REGEX_PYTHON, FOC_SMART,       "H\\w+o", true  ],
    [ FOT_REGEX_PYTHON, FOC_SMART,       "h\\w+O", false ],
];


function TestKoFind() {
    this.scope = null;
    this.context = null;
    this.log = ko.logging.getLogger("find.test");
}
TestKoFind.prototype = new TestCase();

TestKoFind.prototype.setUp = function TestKoFind_setUp() {
    // Replace the notify module with a mocked version, otherwise the real notify
    // module will try to use the window and dom (which don't exist).
    require.removeRequirePath("notify");
    require.setRequirePath("notify", "resource://komodo-jstest/mock/sdk");

    let loader = Cc['@mozilla.org/moz/jssubscript-loader;1']
                   .getService(Ci.mozIJSSubScriptLoader);
    this.scope = { ko: ko, __noSuchMethod__: function() {}};
    if (!("find" in ko) || !("findNext" in ko.find)) {
        loader.loadSubScript("chrome://komodo/content/find/find_functions.js", this.scope, "UTF-8");
    }
    this.context = Cc["@activestate.com/koFindContext;1"]
                     .createInstance(Ci.koIFindContext);
    this.findSvc = Cc["@activestate.com/koFindService;1"]
                     .getService(Ci.koIFindService);
    this.options = this.findSvc.options;
    this.options.patternType = Ci.koIFindOptions.FOT_SIMPLE;
    // Override any current pref setting, or file-oriented tests could fail.
    this.options.encodedIncludeFiletypes = '';
};

TestKoFind.prototype.tearDown = function TestKoFind_tearDown() {
    // Hacky - add back the real notify module.
    require.removeRequirePath("notify");
    require.setRequirePath("notify", "chrome://notify/content/sdk");

    this.options.patternType = Ci.koIFindOptions.FOT_SIMPLE;
    this.options.searchBackward = false;
    this.scope = null;
    this.context = null;
    this.findSvc = null;
    this.options = null;
};

TestKoFind.prototype.msgHandler =
function TestKoFind_msgHandler(level, context, message) {
    this.fail("Message handler called in quiet mode: " +
              "level=" + level + " context=" + context +
              " message=" + message + "\n");
};

/**
 * Check indicator status
 * @param scimoz {SciMoz} The scimoz to check
 * @param indic {Number} The indicator to set, 0 through 31 inclusive
 * @param expected {Array} Any non-zero elements are expected to have indicators set
 */
TestKoFind.prototype.checkIndicators =
function checkIndicators(scimoz, indic, expected) {
    for (let i = 0; i < scimoz.text.length; ++i) {
        let bitmap = scimoz.indicatorAllOnFor(i);
        let mask = expected[i] ? (1 << indic) : 0;
        this.assertEquals(mask, bitmap,
                          "Unexpected indicators at " + i);
    }
};

TestKoFind.prototype.test_findNext = function test_findNext() {
    let highlightOptions = [false, true, false, true];

    this.context.type = Ci.koIFindContext.FCT_CURRENT_DOC;
    let scimoz = ko.views.currentView.scimoz = new SciMoz();
    scimoz.text = "Hello Hello Hello";
    let highlightBits = [1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1];

    for each (let [[fot, foc, pattern, matchExpected], highlight] in permute(setups, highlightOptions)) {
        try {
            this.options.patternType = fot;
            this.options.caseSensitivity = foc;
            Components.classes["@activestate.com/koFindSession;1"]
                      .getService(Components.interfaces.koIFindSession)
                      .Reset();
            scimoz.indicatorCurrent = Ci.koILintResult.DECORATOR_FIND_HIGHLIGHT;
            scimoz.indicatorValue = 0;
            scimoz.indicatorClearRange(0, scimoz.text.length);
            scimoz.setSel(0, 0);

            var findNext = (function findNext(pattern) {
                return ko.find.findNext(this.scope, /* editor window */
                                        this.context, /* find context */
                                        pattern, /* pattern */
                                        "find", /* mode */
                                        true, /* quiet */
                                        false, /* use MRU */
                                        this.msgHandler.bind(this), /* message handler */
                                        highlight, /* highlight matches */
                                        -1 /* highlight timeout */);
            }).bind(this);

            let result = findNext(pattern);
            if (!matchExpected) {
                this.assertFalse(result, "Unexpected match for " + pattern);
                this.assertEquals(scimoz.anchor, 0, "Unexpected anchor movement");
                this.assertEquals(scimoz.currentPos, 0, "Unexpected position movement");
                continue;
            }

            this.assertTrue(result, "Failed to find results for " + pattern);
            this.assertEquals(scimoz.anchor, 0, "Incorrect start position");
            this.assertEquals(scimoz.currentPos, 5, "Incorrect end position");
            this.checkIndicators(scimoz, Ci.koILintResult.DECORATOR_FIND_HIGHLIGHT,
                                 highlight ? highlightBits : []);
            result = findNext(pattern);
            this.assertTrue(result, "Failed to find results for " + pattern);
            this.assertEquals(scimoz.anchor, 6, "Incorrect start position");
            this.assertEquals(scimoz.currentPos, 11, "Incorrect end position");
            this.checkIndicators(scimoz, Ci.koILintResult.DECORATOR_FIND_HIGHLIGHT,
                                 highlight ? highlightBits : []);
            result = findNext(pattern);
            this.assertTrue(result, "Failed to find results for " + pattern);
            this.assertEquals(scimoz.anchor, 12, "Incorrect start position");
            this.assertEquals(scimoz.currentPos, 17, "Incorrect end position");
            this.checkIndicators(scimoz, Ci.koILintResult.DECORATOR_FIND_HIGHLIGHT,
                                 highlight ? highlightBits : []);
            result = findNext(pattern);
            this.assertFalse(result, "Unexpectedly wrapped find result: [" +
                             scimoz.anchor + "," + scimoz.currentPos + "]");
            scimoz.setSel(0, 0);
            result = findNext("world");
            this.assertFalse(result, "Unexpected found result");
            result = findNext(pattern);
            this.assertTrue(result, "Failed to find results for " + pattern);
            this.assertEquals(scimoz.anchor, 0, "Incorrect start position");
            this.assertEquals(scimoz.currentPos, 5, "Incorrect end position");
            this.checkIndicators(scimoz, Ci.koILintResult.DECORATOR_FIND_HIGHLIGHT,
                                 highlight ? highlightBits : []);
        } catch (ex if ex instanceof TestCase.TestError) {
            // Tack on additional information about the parameters
            ex.message += " (type=" + fot + " case=" + foc +
                           " pattern=" + pattern + " match=" + matchExpected +
                           " highlight=" + highlight + ")";
            throw ex;
        }
    }
};

TestKoFind.prototype.test_findPrevious = function test_findPrevious() {
    this.context.type = Ci.koIFindContext.FCT_CURRENT_DOC;
    this.options.searchBackward = true;
    let scimoz = ko.views.currentView.scimoz = new SciMoz();
    scimoz.text = "Hello Hello Hello";

    let highlightOptions = [false, true, false, true];
    let highlightBits = [1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1];

    for each (let [[fot, foc, pattern, matchExpected], highlight] in permute(setups, highlightOptions)) {
        try {
            var findNext = (function findNext(pattern) {
                return ko.find.findNext(this.scope, /* editor window */
                                        this.context, /* find context */
                                        pattern, /* pattern */
                                        "find", /* mode */
                                        true, /* quiet */
                                        false, /* use MRU */
                                        this.msgHandler.bind(this), /* message handler */
                                        highlight, /* highlight matches */
                                        -1 /* highlight timeout */);
            }).bind(this);

            this.options.patternType = fot;
            this.options.caseSensitivity = foc;
            scimoz.indicatorCurrent = Ci.koILintResult.DECORATOR_FIND_HIGHLIGHT;
            scimoz.indicatorValue = 0;
            scimoz.indicatorClearRange(0, scimoz.text.length);

            let result;
            scimoz.setSel(-1, -1);
            this.assertEquals(scimoz.anchor, scimoz.text.length, "Anchor not at EOF");
            result = findNext(pattern);

            if (!matchExpected) {
                this.assertFalse(result, "Unexpectedly found result");
                this.assertEquals(scimoz.anchor, scimoz.length, "Incorrect start position");
                this.assertEquals(scimoz.currentPos, scimoz.length, "Incorrect end position");
                continue;
            }

            this.assertTrue(result, "Failed to find last result");
            this.assertEquals(scimoz.anchor, 12, "Incorrect start position");
            this.assertEquals(scimoz.currentPos, 17, "Incorrect end position");
            this.checkIndicators(scimoz, Ci.koILintResult.DECORATOR_FIND_HIGHLIGHT,
                                 highlight ? highlightBits : []);
            result = findNext(pattern);
            this.assertTrue(this.options.searchBackward, "searchBackward flag changed");
            this.assertTrue(result, "Failed to find second result");
            this.assertEquals(scimoz.anchor, 6, "Incorrect start position");
            this.assertEquals(scimoz.currentPos, 11, "Incorrect end position");
            this.checkIndicators(scimoz, Ci.koILintResult.DECORATOR_FIND_HIGHLIGHT,
                                 highlight ? highlightBits : []);
            result = findNext(pattern);
            this.assertTrue(this.options.searchBackward, "searchBackward flag changed");
            this.assertTrue(result, "Failed to find first result");
            this.assertEquals(scimoz.anchor, 0, "Incorrect start position");
            this.assertEquals(scimoz.currentPos, 5, "Incorrect end position");
            this.checkIndicators(scimoz, Ci.koILintResult.DECORATOR_FIND_HIGHLIGHT,
                                 highlight ? highlightBits : []);
            result = findNext(pattern);
            this.assertFalse(result, "Unexpectedly wrapped find result: [" +
                             scimoz.anchor + "," + scimoz.currentPos + "]");
            scimoz.setSel(-1, -1);
            result = findNext("world");
            this.assertFalse(result, "Unexpected found result");
            result = findNext(pattern);
            this.assertTrue(result, "Failed to find results");
            this.assertEquals(scimoz.anchor, 12, "Incorrect start position");
            this.assertEquals(scimoz.currentPos, 17, "Incorrect end position");
            this.checkIndicators(scimoz, Ci.koILintResult.DECORATOR_FIND_HIGHLIGHT,
                                 highlight ? highlightBits : []);
        } catch (ex if ex instanceof TestCase.TestError) {
            // Tack on additional information about the parameters
            ex.message += " (type=" + fot + " case=" + foc +
                           " pattern=" + pattern + " match=" + matchExpected +
                           " highlight=" + highlight + ")";
            throw ex;
        }
    }
};

TestKoFind.prototype.test_findAll = function test_findAll() {
    this.context.type = Ci.koIFindContext.FCT_CURRENT_DOC;
    let scimoz = ko.views.currentView.scimoz = new SciMoz();
    scimoz.text = "Hello Hello Hello";

    let highlightOptions = [false, true, false, true];
    let highlightBits = [1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1];

    for each (let [[fot, foc, pattern, matchExpected], highlight] in permute(setups, highlightOptions)) {
        try {
            this.options.patternType = fot;
            this.options.caseSensitivity = foc;
            scimoz.indicatorCurrent = Ci.koILintResult.DECORATOR_FIND_HIGHLIGHT;
            scimoz.indicatorValue = 0;
            scimoz.indicatorClearRange(0, scimoz.text.length);

            let result;
            let msgHandler = matchExpected ? this.msgHandler.bind(this) : function(){};
            result = ko.find.findAll(this.scope, /* editor window */
                                     this.context, /* find context */
                                     pattern, /* pattern */
                                     "hello_alias", /* pattern alias */
                                     msgHandler, /* message handler */
                                     highlight /* hightlight matches */);

            let tab = ko.findresults.getTab();
            this.assertTrue(tab.success, "Find results claimed failure");
            this.assertEquals(tab.numFiles, null, "Not expecting file counts for current doc");
            this.assertEquals(tab.numFilesSearched, null, "Not expecting file counts for current doc");
            this.assertEquals(tab.journalId, undefined, "Journal id given for non-replace findAll");

            if (!matchExpected) {
                this.assertFalse(result, "Unexpected match");
                this.assertEquals(tab.numResults, 0, "Unexpected match count");
                this.assertEquals(tab.view.GetNumUrls(), 0, "Expected no URLs");
                this.assertEquals(tab.view.rowCount, 0, "Expected 0 rows");
                continue;
            }

            this.assertTrue(result, "Failed to find all");
            this.assertEquals(tab.view.GetNumUrls(), 1, "Expected 1 URL");
            this.assertEquals(ko.views.currentView.koDoc.displayPath, tab.view.GetUrl(0),
                              "Unexpected URL for the document");

            this.assertEquals(tab.view.rowCount, 3, "Expected 3 results");
            for (let i = 0; i < tab.view.rowCount; ++i) {
                this.assertEquals(tab.view.getCellText(i, {id: "value"}), "Hello", "Unexpected text");
                this.assertEquals(tab.view.GetValue(i), "Hello", "Unexpected value");
                this.assertEquals(tab.view.GetType(i), "hit", "Unexpected tpe");
                this.assertEquals(tab.view.GetReplacement(i), "", "Should not have a replacement");
                this.assertEquals(tab.view.GetLineNum(i), 1, "Should have no lines involved");
                this.assertEquals(tab.view.GetColumnNum(i), tab.view.GetStartIndex(i) + 1,
                                  "Column numbers should match start indices");
            }

            this.assertEquals(tab.view.GetStartIndex(0), 0, "Bad first result start position");
            this.assertEquals(tab.view.GetEndIndex(0), 5, "Bad first result end position");
            this.assertEquals(tab.view.GetStartIndex(1), 6, "Bad second result start position");
            this.assertEquals(tab.view.GetEndIndex(1), 11, "Bad second result end position");
            this.assertEquals(tab.view.GetStartIndex(2), 12, "Bad third result start position");
            this.assertEquals(tab.view.GetEndIndex(2), 17, "Bad third result end position");

            this.checkIndicators(scimoz, Ci.koILintResult.DECORATOR_FIND_HIGHLIGHT,
                                 highlight ? highlightBits : []);
        } catch (ex if ex instanceof TestCase.TestError) {
            // Tack on additional information about the parameters
            ex.message += " (type=" + fot + " case=" + foc +
                           " pattern=" + pattern + " match=" + matchExpected +
                           " highlight=" + highlight + ")";
            throw ex;
        }
    }
};

TestKoFind.prototype.test_markAll = function test_markAll() {
    this.context.type = Ci.koIFindContext.FCT_CURRENT_DOC;
    let view = ko.views.currentView = new ko.views.ViewBookmarkableMock();
    let scimoz = view.scimoz = new SciMoz();
    scimoz.text = ["Hello", "world", "Hello", "world", "Hello", "world"].join("\n");

    for each (let [fot, foc, pattern, matchExpected] in setups) {
        this.options.patternType = fot;
        this.options.caseSensitivity = foc;
        view.removeAllBookmarks();
        let result;
        try {
            let msgHandler = matchExpected ? this.msgHandler.bind(this) : function(){};
            result = ko.find.markAll(this.scope, /* editor */
                                     this.context, /* find context */
                                     pattern, /* pattern */
                                     "hello_alias", /* pattern alias */
                                     msgHandler /* message handler */);
            if (matchExpected) {
                this.assertTrue(result, "Bookmarks should have been created");
                this.assertEquals(view.bookmarks, [0, 2, 4],
                                  "Bookmarks in the wrong places");
            } else {
                this.assertFalse(result, "Bookmarks should not have been created");
                this.assertEquals(view.bookmarks, [], "Unexpected bookmarks");
            }
        } catch (ex if ex instanceof TestCase.TestError) {
            // Tack on additional information about the parameters
            ex.message += " (type=" + fot + " case=" + foc +
                           " pattern=" + pattern + " match=" + matchExpected + ")";
            throw ex;
        }
    }
};

TestKoFind.prototype.test_findAllInFiles = function test_findAllInFiles() {
    this.context = Cc["@activestate.com/koFindInFilesContext;1"]
                     .createInstance(Ci.koIFindInFilesContext);
    this.context.type = Ci.koIFindContext.FCT_IN_FILES;
    var fileSvc = Cc["@activestate.com/koFileService;1"].getService(Ci.koIFileService);

    for each (let [fot, foc, pattern, matchExpected] in setups) {
        this.options.patternType = fot;
        this.options.caseSensitivity = foc;
        var dirName = fileSvc.makeTempDir(".tmp", "komodo_test_find_findAllInFiles_");
        this.context.cwd = dirName;
        var abort = false;
        try {
            var resultsTab = ko.findresults.getTab();
            var data = {
                "hello.txt": ["Hello Hello", "Hello"],
                "world.txt": ["Hello, world!"],
                "boring.txt": ["This file", "does not mention", "the magic word"],
            };
            for each (let [name, contents] in Iterator(data)) {
                let file = Cc["@activestate.com/koFileEx;1"]
                             .createInstance(Ci.koIFileEx);
                file.path = dirName + "/" + name;
                file.open("w");
                try {
                    file.puts(contents.join("\n"));
                } finally {
                    file.close();
                }
            }
            let result;
            this.options.encodedFolders = ".";
            result = ko.find.findAllInFiles(this.scope, /* editor */
                                            this.context, /* find context */
                                            pattern, /* pattern */
                                            "hello_alias", /* pattern alias */
                                            this.msgHandler.bind(this) /* message handler */);
            this.assertTrue(result, "Failed to start find in files");
            var findSvc = Cc["@activestate.com/koFindService;1"]
                            .getService(Ci.koIFindService);
            var stopTime = Date.now() + 10 * 1000; // 10 seconds
            while (!abort && resultsTab.inProgress) {
                abort = Date.now() > stopTime;
                Services.tm.mainThread.processNextEvent(false);
            }
            if (abort) {
                findSvc.stopfindreplaceinfiles(resultsTab.id);
                this.fail("Timed out waiting for the search to complete");
            }
            // Spin the event loop for a bit to let the session thread shut down :(
            stopTime = Date.now() + 200; // 0.2 seconds
            while (Date.now() < stopTime) {
                Services.tm.mainThread.processNextEvent(false);
            }
            if (findSvc.stopfindreplaceinfiles(resultsTab.id)) {
                // Getting here means the find-in-files session was stuck on the
                // background thread; give it a bit more time to shutdown, then
                // report this, assuming it's a hang
                stopTime = Date.now() + 5 * 1000; // 10 seconds
                while (Date.now() < stopTime) {
                    Services.tm.mainThread.processNextEvent(false);
                }
                this.fail("Find session was stuck in the background");
            }
            this.assertTrue(resultsTab.success, "Failed to find results");
            if (matchExpected) {
                this.assertEquals(resultsTab.numResults, 4, "Expected 4 results");
                this.assertEquals(resultsTab.numFiles, 2, "Expected 2 files");
            } else {
                this.assertEquals(resultsTab.numResults, 0, "Expected no results");
                this.assertEquals(resultsTab.numFiles, 0, "Expected no files");
            }
            this.assertEquals(resultsTab.numFilesSearched, 3, "Expected 3 files searched");
        } catch (ex if ex instanceof TestCase.TestError) {
            // Tack on additional information about the parameters
            ex.message += " (type=" + fot + " case=" + foc +
                           " pattern=" + pattern + " match=" + matchExpected + ")";
            throw ex;
        } finally {
            fileSvc.deleteTempDir(dirName);
        }
    }
};


TestKoFind.prototype.test_findAllInMacro = function test_findAllInMacro() {
    let scimoz = ko.views.currentView.scimoz = new SciMoz();
    scimoz.text = "Hello Hello Hello";

    for each (let [[fot, foc, pattern, shouldMatch], backwards] in permute(setups, [false, true])) {
        try {
            let tab = ko.findresults.getTab();
            ko.find.findAllInMacro(this.scope, /* editor window */
                                   Ci.koIFindContext.FCT_CURRENT_DOC, /* context type */
                                   pattern, /* pattern */
                                   fot, /* pattern type */
                                   foc, /* case sensitivity */
                                   backwards, /* search backward */
                                   true); /* match word */

            // "success" can mean 0 matches
            this.assertTrue(tab.success, "Find results claimed failure");
            this.assertEquals(tab.numFiles, null, "Not expecting file counts for current doc");
            this.assertEquals(tab.numFilesSearched, null, "Not expecting file counts for current doc");

            if (!shouldMatch) {
                this.assertEquals(tab.numResults, 0, "Did not find all results");
                this.assertEquals(tab.view.rowCount, 0, "Expected 0 results");
                this.assertEquals(0, tab.view.GetNumUrls(), "Not expecting URLs in find results");
                continue;
            }
            this.assertEquals(tab.numResults, 3, "Did not find all results");
            this.assertEquals(1, tab.view.GetNumUrls(), "Expected one URL in find results");
            this.assertEquals(ko.views.currentView.koDoc.displayPath, tab.view.GetUrl(0),
                              "Unexpected URL for the document");

            this.assertEquals(tab.view.rowCount, 3, "Expected 3 results");
            for (let i = 0; i < tab.view.rowCount; ++i) {
                this.assertEquals(tab.view.getCellText(i, {id: "value"}), "Hello", "Unexpected text");
                this.assertEquals(tab.view.GetValue(i), "Hello", "Unexpected value");
                this.assertEquals(tab.view.GetType(i), "hit", "Unexpected tpe");
                this.assertEquals(tab.view.GetReplacement(i), "", "Should not have a replacement");
                this.assertEquals(tab.view.GetLineNum(i), 1, "Should have no lines involved");
                this.assertEquals(tab.view.GetColumnNum(i), tab.view.GetStartIndex(i) + 1,
                                  "Column numbers should match start indices");
            }
            this.assertEquals(tab.view.GetStartIndex(0), 0, "Bad first result start position");
            this.assertEquals(tab.view.GetEndIndex(0), 5, "Bad first result end position");
            this.assertEquals(tab.view.GetStartIndex(1), 6, "Bad second result start position");
            this.assertEquals(tab.view.GetEndIndex(1), 11, "Bad second result end position");
            this.assertEquals(tab.view.GetStartIndex(2), 12, "Bad third result start position");
            this.assertEquals(tab.view.GetEndIndex(2), 17, "Bad third result end position");
        } catch (ex if ex instanceof TestCase.TestError) {
            // Tack on additional information about the parameters
            ex.message += " (type=" + fot + " case=" + foc +
                           " pattern=" + pattern +
                           " shouldMatch=" + shouldMatch +
                           " backwards=" + backwards + ")";
            throw ex;
        }
    }
};

TestKoFind.prototype.test_findNextInMacro = function test_findNextInMacro() {
    let scimoz = ko.views.currentView.scimoz = new SciMoz();
    scimoz.text = "Hello Hello Hello";

    for each (let [[fot, foc, pattern, shouldMatch], backwards] in permute(setups, [false, true])) {
        try {
            let findNextInMacro = (function findNext(pattern) {
                ko.find.findNextInMacro(this.scope, /* editor window */
                                        Ci.koIFindContext.FCT_CURRENT_DOC, /* context type */
                                        pattern, /* pattern */
                                        fot, /* pattern type */
                                        foc, /* case sensitivity */
                                        backwards, /* search backward */
                                        false, /* match word */
                                        "find", /* find */
                                        true, /* quiet */
                                        false); /* use MRU */
            }).bind(this);

            let startPosition = backwards ? scimoz.length : 0;
            scimoz.setSel(startPosition, startPosition);
            let positions = [[0, 5], [6, 11], [12, 17]];
            if (backwards) positions.reverse();
            for each (let [i, pos] in Iterator(positions)) {
                findNextInMacro(pattern);
                if (!shouldMatch) {
                    this.assertEquals(scimoz.anchor, startPosition, "Unexpected anchor movement for failed find");
                    this.assertEquals(scimoz.currentPos, startPosition, "Unexpected end movement for failed find");
                    break;
                } else {
                    this.assertEquals(scimoz.anchor, pos[0], "Incorrect start position " + i);
                    this.assertEquals(scimoz.currentPos, pos[1], "Incorrect end position " + i);
                }
            }
            scimoz.setSel(startPosition, startPosition);
            findNextInMacro("world");
            this.assertEquals(scimoz.anchor, startPosition, "Unexpected anchor movement for failed find");
            this.assertEquals(scimoz.currentPos, startPosition, "Unexpected end movement for failed find");
            findNextInMacro(pattern);
            if (!shouldMatch) {
                this.assertEquals(scimoz.anchor, startPosition, "Unexpected anchor movement for failed find");
                this.assertEquals(scimoz.currentPos, startPosition, "Unexpected end movement for failed find");
            } else {
                this.assertEquals(scimoz.anchor, positions[0][0], "Incorrect start position");
                this.assertEquals(scimoz.currentPos, positions[0][1], "Incorrect end position");
            }
        } catch (ex if ex instanceof TestCase.TestError) {
            // Tack on additional information about the parameters
            ex.message += " (type=" + fot + " case=" + foc +
                           " pattern=" + pattern +
                           " shouldMatch=" + shouldMatch +
                           " backwards=" + backwards + ")";
            throw ex;
        }
    }
};

TestKoFind.prototype.test_highlightAllMatches = function test_highlightAllMatches() {
    this.context.type = Ci.koIFindContext.FCT_CURRENT_DOC;
    let scimoz = ko.views.currentView.scimoz = new SciMoz();
    scimoz.text = "Hello Hello Hello";

    for each (let [fot, foc, pattern, matchExpected] in setups) {
        this.options.patternType = fot;
        this.options.caseSensitivity = foc;
        try {
            ko.find.highlightAllMatches(scimoz, this.context, pattern, 1000);
            let expected = [1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1];
            if (!matchExpected) expected = [0 for (i in expected)];
            this.checkIndicators(scimoz, Ci.koILintResult.DECORATOR_FIND_HIGHLIGHT,
                                 expected);
        } catch (ex if ex instanceof TestCase.TestError) {
            // Tack on additional information about the parameters
            ex.message += " (type=" + fot + " case=" + foc +
                           " pattern=" + pattern + " match=" + matchExpected + ")";
            throw ex;
        }
    }
};

TestKoFind.prototype.test_highlightClearAll = function test_highlightClearAll() {
    this.context.type = Ci.koIFindContext.FCT_CURRENT_DOC;
    let scimoz = ko.views.currentView.scimoz = new SciMoz();
    scimoz.text = "hello hello hello";

    ko.find.highlightAllMatches(scimoz, this.context, "hello", 1000);
    let expected = [1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1];
    this.checkIndicators(scimoz, Ci.koILintResult.DECORATOR_FIND_HIGHLIGHT,
                         expected);
    ko.find.highlightClearAll(scimoz);
    this.checkIndicators(scimoz, Ci.koILintResult.DECORATOR_FIND_HIGHLIGHT,
                         [0 for (i in expected)]);
};

TestKoFind.prototype.test_highlightClearPosition = function test_highlightClearPosition() {
    const INDIC = Ci.koILintResult.DECORATOR_FIND_HIGHLIGHT;
    this.context.type = Ci.koIFindContext.FCT_CURRENT_DOC;
    let scimoz = ko.views.currentView.scimoz = new SciMoz();
    scimoz.text = "hello hello hello";

    ko.find.highlightAllMatches(scimoz, this.context, "hello", 1000);
    let expected = [1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1];
    this.checkIndicators(scimoz, INDIC, expected);
    let start = [0,0,0,0,0,5,6,6,6,6,6,11,12,12,12,12,12];
    let end = [5,5,5,5,5,6,11,11,11,11,11,12,17,17,17,17,17];
    for (let i = 0; i < scimoz.text.length; ++i) {
        this.assertEquals(start[i], scimoz.indicatorStart(INDIC, i),
                          "Unexpected indicator start at " + i);
        this.assertEquals(end[i], scimoz.indicatorEnd(INDIC, i),
                          "Unexpected indicator end at " + i);
    }
    ko.find.highlightClearPosition(scimoz, 6, 2);
    expected = [1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1];
    this.checkIndicators(scimoz, INDIC, expected);
    this.options.patternType = Ci.koIFindOptions.FOT_REGEX_PYTHON;
    ko.find.highlightAllMatches(scimoz, this.context, "he|lo", 1000);
    expected = [1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 1];
    this.checkIndicators(scimoz, INDIC, expected);
    ko.find.highlightClearPosition(scimoz, 4, 6);
    expected = [1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 1, 1];
    this.checkIndicators(scimoz, INDIC, expected);
};

TestKoFind.prototype.test_markAllInMacro = function test_markAllInMacro() {
    let view = ko.views.currentView = new ko.views.ViewBookmarkableMock();
    let scimoz = view.scimoz = new SciMoz();
    scimoz.text = ["Hello", "world", "Hello", "world", "Hello", "world"].join("\n");

    for each (let [fot, foc, pattern, matchExpected] in setups) {
        try {
            view.removeAllBookmarks();
            ko.find.markAllInMacro(this.scope, /* editor */
                                   Ci.koIFindContext.FCT_CURRENT_DOC, /* context type */
                                   pattern, /* pattern */
                                   fot, /* pattern type */
                                   foc, /* case sensitivity */
                                   false, /* search backward */
                                   false); /* match word */
            if (matchExpected) {
                this.assertEquals(view.bookmarks, [0, 2, 4],
                                  "Bookmarks in the wrong places");
            } else {
                this.assertEquals(view.bookmarks, [], "Unexpected bookmarks");
            }
        } catch (ex if ex instanceof TestCase.TestError) {
            // Tack on additional information about the parameters
            ex.message += " (type=" + fot + " case=" + foc +
                           " pattern=" + pattern + " match=" + matchExpected + ")";
            throw ex;
        }
    }
};

TestKoFind.prototype.test_replace = function test_replace() {
    this.context.type = Ci.koIFindContext.FCT_CURRENT_DOC;
    let scimoz = ko.views.currentView.scimoz = new SciMoz();

    for each (let [fot, foc, pattern, matchExpected] in setups) {
        scimoz.text = "Hello Hello Hello";
        this.options.patternType = fot;
        this.options.caseSensitivity = foc;
        try {
            let expected = ["Hello Hello Hello", /* first time just highlights */
                            "World Hello Hello",
                            "World World Hello",
                            "World World World"];

            let result;
            while (expected.length > 0) {
                result = ko.find.replace(this.scope, /* editor */
                                         this.context, /* context */
                                         pattern, /* pattern */
                                         "World", /* replacement */
                                         function(){}); /* msg handler */

                if (!matchExpected) {
                    this.assertFalse(result, "Replace shouldn't have found a match");
                    expected = [expected[0]]; // breaks the loop
                } else {
                    if (expected.length > 1) {
                        this.assertTrue(result, "Replace didn't find next result");
                    } else {
                        this.assertFalse(result, "Replace found unexpected next result");
                    }
                }

                this.assertEquals(expected.shift(), scimoz.text,
                                  "Replace didn't change the text");
            }
        } catch (ex if ex instanceof TestCase.TestError) {
            // Tack on additional information about the parameters
            ex.message += " (type=" + fot + " case=" + foc +
                           " pattern=" + pattern + " match=" + matchExpected + ")";
            throw ex;
        }
    }
};

TestKoFind.prototype.test_replaceAll = function test_replaceAll() {
    this.context.type = Ci.koIFindContext.FCT_CURRENT_DOC;
    let scimoz = ko.views.currentView.scimoz = new SciMoz();
    for each (let [[fot, foc, pattern, matchExpected], highlight] in permute(setups, [false, true])) {
        this.options.patternType = fot;
        this.options.caseSensitivity = foc;
        try {
            scimoz.text = "Hello Hello Hello";
            scimoz.indicatorCurrent = Ci.koILintResult.DECORATOR_FIND_HIGHLIGHT;
            scimoz.indicatorValue = 0;
            scimoz.indicatorClearRange(0, scimoz.text.length);
            let result;
            result = ko.find.replaceAll(this.scope, /* editor */
                                        this.context, /* context */
                                        pattern, /* pattern */
                                        "World", /* replacement */
                                        false, /* show replace results */
                                        false, /* first on line */
                                        function() {}, /* msg handler */
                                        highlight); /* highlight replacements */
            expectedHighlight = [1,1,1,1,1,0,1,1,1,1,1,0,1,1,1,1,1];
            if (!highlight) expectedHighlight = [0 for (i in expectedHighlight)];
            if (matchExpected) {
                this.assertTrue(result, "Expected replace to find things");
                this.assertEquals(scimoz.text, "World World World",
                                  "Replace all didn't replace correctly");
            } else {
                this.assertFalse(result, "Expected replace to find nothing");
                this.assertEquals(scimoz.text, "Hello Hello Hello",
                                  "Replace unexpected");
                expectedHighlight = [0 for (i in expectedHighlight)];
            }
            this.checkIndicators(scimoz, Ci.koILintResult.DECORATOR_FIND_HIGHLIGHT,
                                 expectedHighlight);
        } catch (ex if ex instanceof TestCase.TestError) {
            // Tack on additional information about the parameters
            ex.message += " (type=" + fot + " case=" + foc +
                           " pattern=" + pattern + " match=" + matchExpected +
                           " highlight=" + highlight + ")";
            throw ex;
        }
    }
};

TestKoFind.prototype.test_replaceAllInFiles = function test_replaceAllInFiles() {
    this.context = Cc["@activestate.com/koFindInFilesContext;1"]
                     .createInstance(Ci.koIFindInFilesContext);
    this.context.type = Ci.koIFindContext.FCT_IN_FILES;
    var fileSvc = Cc["@activestate.com/koFileService;1"].getService(Ci.koIFileService);
    var dirName = fileSvc.makeTempDir(".tmp", "komodo_test_find_replaceAllInFiles_");
    this.context.cwd = dirName;
    var abort = false;
    try {
        var resultsTab = ko.findresults.getTab();
        var data = {
            "hello.txt": ["hello", "hello", "hello"],
            "world.txt": ["hello, world!"],
            "boring.txt": ["This file", "does not mention", "the magic word"],
        };
        for each (let [name, contents] in Iterator(data)) {
            let file = Cc["@activestate.com/koFileEx;1"]
                         .createInstance(Ci.koIFileEx);
            file.path = dirName + "/" + name;
            file.open("w");
            file.puts(contents.join("\n"));
            file.close();
        }
        let result;
        this.options.encodedFolders = ".";
        result = ko.find.replaceAllInFiles(this.scope, /* editor */
                                           this.context, /* find context */
                                           "hello", /* pattern */
                                           "world", /* replacement */
                                           false, /* confirm */
                                           this.msgHandler.bind(this) /* message handler */);
        this.assertTrue(result, "Failed to replace in files");
        var findSvc = Cc["@activestate.com/koFindService;1"]
                        .getService(Ci.koIFindService);
        var stopTime = Date.now() + 10 * 1000; // 10 seconds
        while (!abort && resultsTab.inProgress) {
            abort = Date.now() > stopTime;
            Services.tm.mainThread.processNextEvent(false);
        }
        if (abort) {
            findSvc.stopfindreplaceinfiles(resultsTab.id);
            this.fail("Timed out waiting for the replace to complete");
        }
        // Spin the event loop for a bit to let the session thread shut down :\(
        stopTime = Date.now() + 200; // 0.2 seconds
        while (Date.now() < stopTime) {
            Services.tm.mainThread.processNextEvent(false);
        }
        if (findSvc.stopfindreplaceinfiles(resultsTab.id)) {
            // Getting here means the find-in-files session was stuck on the
            // background thread; give it a bit more time to shutdown, then
            // report this, assuming it's a hang
            stopTime = Date.now() + 5 * 1000; // 10 seconds
            while (Date.now() < stopTime) {
                Services.tm.mainThread.processNextEvent(false);
            }
            this.fail("Replace session was stuck in the background");
        }
        this.assertTrue(resultsTab.success, "Failed to find results");
        this.assertEquals(resultsTab.numResults, 4, "Expected 4 results");
        this.assertEquals(resultsTab.numFiles, 2, "Expected 2 files");
        this.assertEquals(resultsTab.numFilesSearched, 3, "Expected 3 files searched");

        for each (let [name, contents] in Iterator(data)) {
            let file = Cc["@activestate.com/koFileEx;1"]
                         .createInstance(Ci.koIFileEx);
            file.path = dirName + "/" + name;
            file.open("r");
            try {
                this.assertEquals(file.readfile(),
                                  contents.join("\n").replace(/hello/g, "world"),
                                  "Replace didn't change file contents");
            } finally {
                file.close();
            }
        }
    } finally {
        fileSvc.deleteTempDir(dirName);
    }
};

TestKoFind.prototype.test_replaceAllInFilesWithBOM = function test_replaceAllInFilesWithBOM() {
    this.context = Cc["@activestate.com/koFindInFilesContext;1"]
                     .createInstance(Ci.koIFindInFilesContext);
    this.context.type = Ci.koIFindContext.FCT_IN_FILES;
    var fileSvc = Cc["@activestate.com/koFileService;1"].getService(Ci.koIFileService);
    var dirName = fileSvc.makeTempDir(".tmp", "komodo_test_find_replaceAllInFilesWithBOM_");
    this.context.cwd = dirName;
    var abort = false;
    try {
        var resultsTab = ko.findresults.getTab();
        var byteArray1 = [0xef, 0xbb, 0xbf];
        var contents1 = ("abcdef ?\n"
            + "an acute: ");
        var byteArray2 = [0xc2, 0x9b];
        var contents2 = ("\n"
                         + "that's it.\n");
        var contents = (String.fromCharCode(byteArray1) + contents1
                        + String.fromCharCode(byteArray2) + contents2);
        var fname = "bom01-utf8.txt";
        var obj_File = Cc["@mozilla.org/file/local;1"].createInstance(Ci.nsILocalFile);
        var obj_OutputStream = Cc["@mozilla.org/network/file-output-stream;1"].createInstance(Ci.nsIFileOutputStream);
        var obj_BinaryOutputStream = Cc["@mozilla.org/binaryoutputstream;1"].createInstance(Ci.nsIBinaryOutputStream);
        // Need to do init with dir + append to work correctly on Windows (due to different separators)
        obj_File.initWithPath(dirName);
        obj_File.append(fname);
        if (!obj_File.exists()) {
            obj_File.create(0, 0664);
        }
        obj_OutputStream.init(obj_File, 0x22, 4, null);
        obj_BinaryOutputStream.setOutputStream(obj_OutputStream);
        obj_BinaryOutputStream.writeByteArray(byteArray1, byteArray1.length);
        obj_BinaryOutputStream.writeBytes(contents1, contents1.length);
        obj_BinaryOutputStream.writeByteArray(byteArray2, byteArray2.length);
        obj_BinaryOutputStream.writeBytes(contents2, contents2.length);
        obj_BinaryOutputStream.flush();
        obj_BinaryOutputStream.close();
        obj_OutputStream.close();
        let result;
        this.options.encodedFolders = ".";
        result = ko.find.replaceAllInFiles(this.scope, /* editor */
                                           this.context, /* find context */
                                           "acute", /* pattern */
                                           "grave", /* replacement */
                                           false, /* confirm */
                                           this.msgHandler.bind(this) /* message handler */);
        this.assertTrue(result, "Failed to replace in files");
        var findSvc = Cc["@activestate.com/koFindService;1"]
                        .getService(Ci.koIFindService);
        var stopTime = Date.now() + 10 * 1000; // 10 seconds
        while (!abort && resultsTab.inProgress) {
            abort = Date.now() > stopTime;
            Services.tm.mainThread.processNextEvent(false);
        }
        if (abort) {
            findSvc.stopfindreplaceinfiles(resultsTab.id);
            this.fail("Timed out waiting for the replace to complete");
        }
        // Spin the event loop for a bit to let the session thread shut down :\(
        stopTime = Date.now() + 200; // 0.2 seconds
        while (Date.now() < stopTime) {
            Services.tm.mainThread.processNextEvent(false);
        }
        if (findSvc.stopfindreplaceinfiles(resultsTab.id)) {
            // Getting here means the find-in-files session was stuck on the
            // background thread; give it a bit more time to shutdown, then
            // report this, assuming it's a hang
            stopTime = Date.now() + 5 * 1000; // 10 seconds
            while (Date.now() < stopTime) {
                Services.tm.mainThread.processNextEvent(false);
            }
            this.fail("Replace session was stuck in the background");
        }
                       
        this.assertTrue(resultsTab.success, "Failed to find results");
        this.assertEquals(resultsTab.numResults, 1, "Expected 1 results");
        this.assertEquals(resultsTab.numFiles, 1, "Expected 1 files");
        this.assertEquals(resultsTab.numFilesSearched, 1, "Expected 1 file searched");

        obj_InputStream = Cc["@mozilla.org/network/file-input-stream;1"].createInstance(Ci.nsIFileInputStream);
        obj_BinaryInputStream = Cc["@mozilla.org/binaryinputstream;1"].createInstance(Ci.nsIBinaryInputStream);
        obj_InputStream.init(obj_File, -1, -1, false);
        obj_BinaryInputStream.setInputStream(obj_InputStream);
        var bytes = obj_BinaryInputStream.readBytes(obj_BinaryInputStream.available());
        obj_BinaryInputStream.close();
        obj_InputStream.close();
        
        this.assertEquals(bytes.charCodeAt(0), 0xef);
        this.assertEquals(bytes.charCodeAt(1), 0xbb);
        this.assertEquals(bytes.charCodeAt(2), 0xbf);
        var contents1_fixed = contents1.replace(/acute/g, "grave");
        this.assertEquals(bytes.substr(3, contents1_fixed.length), contents1_fixed);
        var n = 3 + contents1.length;
        this.assertEquals(bytes.charCodeAt(n), 0xc2);
        this.assertEquals(bytes.charCodeAt(n + 1), 0x9b);
        this.assertEquals(bytes.substr(n + 2), contents2);

	    // Now do an undo
	
    	function UndoReplaceControllerMock(owner) {
            this.num_hits = -1;
            this.num_paths = -1;
            this.owner = owner;
        };
    	UndoReplaceControllerMock.prototype = {
          QueryInterface: function(iid) {
                dump("UndoReplaceControllerMock.QueryInterface(" + iid + ")\n");
                if (!iid.equals(Components.interfaces.koIUndoReplaceController) &&
                    !iid.equals(Components.interfaces.nsISupports)) {
                    throw Components.results.NS_ERROR_NO_INTERFACE;
                }
                return this;
            },
          set_summary: function() {
                dump("UndoReplaceControllerMock.set_summary()\n");
            },
          report: function(num_hits, num_paths) {
                dump("UndoReplaceControllerMock.report(" + num_hits
                     + ", " + num_paths + ")\n");
            this.num_hits = num_hits;
            this.num_paths = num_paths;
            },
          error: function(errmsg) {
                dump("UndoReplaceControllerMock.error(" + errmsg + ")\n");
                owner.assertFalse(1, "undo failed: " + errmsg)
                fileSvc.deleteTempDir(dirName);
            },
          done: function() {
                dump("UndoReplaceControllerMock.done()\n");
                owner.assertTrue(1, "undo succeeded: " + errmsg)
                fileSvc.deleteTempDir(dirName);
            },
        };

        // Don't wire up the undo'er yet.
        // var journalId = resultsTab.journalId;
        // undoController = new UndoReplaceControllerMock(this);
        // var undoer = findSvc.undoreplaceallinfiles(journalId, undoController);
        // undoer.start();
    } finally {
        // Nothing to do here
        fileSvc.deleteTempDir(dirName);
    }
};

TestKoFind.prototype.test_replaceAllInMacro = function test_replaceAllInMacro() {
    let scimoz = ko.views.currentView.scimoz = new SciMoz();
    for each (let [fot, foc, pattern, matchExpected] in setups) {
        try {
            scimoz.text = "Hello Hello Hello";
            ko.find.replaceAllInMacro(this.scope, /* editor */
                                      Ci.koIFindContext.FCT_CURRENT_DOC, /* context type */
                                      pattern, /* pattern */
                                      "World", /* replacement */
                                      true, /* quiet */
                                      fot, /* pattern type */
                                      foc, /* case sensitivity */
                                      false, /* search backward */
                                      false); /* match word */
            if (matchExpected) {
                this.assertEquals(scimoz.text, "World World World",
                                  "Replace all didn't replace correctly");
            } else {
                this.assertEquals(scimoz.text, "Hello Hello Hello",
                                  "Unexpected replace");
            }
        } catch (ex if ex instanceof TestCase.TestError) {
            // Tack on additional information about the parameters
            ex.message += " (type=" + fot + " case=" + foc +
                           " pattern=" + pattern + " match=" + matchExpected + ")";
            throw ex;
        }
    }
};

TestKoFind.prototype.test_replaceInMacro = function test_replaceInMacro() {
    let scimoz = ko.views.currentView.scimoz = new SciMoz();

    for each (let [[fot, foc, pattern, matchExpected], backwards] in permute(setups, [false, true])) {
        try {
            scimoz.text = "Hello Hello Hello";
            let expected = ["Hello Hello Hello", /* first time just highlights */
                            "World Hello Hello",
                            "World World Hello",
                            "World World World"];

            if (backwards) {
                scimoz.setSel(-1, -1);
                expected = expected.map(function(s) s.split(" ").reverse().join(" "));
            }

            while (expected.length > 0) {
                ko.find.replaceInMacro(this.scope, /* editor */
                                       Ci.koIFindContext.FCT_CURRENT_DOC, /* context type */
                                       pattern, /* pattern */
                                       "World", /* replacement */
                                       fot, /* pattern type */
                                       foc, /* case sensitivity */
                                       backwards, /* search backward */
                                       false); /* match word */

                this.assertEquals(expected.shift(), scimoz.text,
                                  "Replace didn't change the text");
                if (!matchExpected) {
                    break;
                }
            }
        } catch (ex if ex instanceof TestCase.TestError) {
            // Tack on additional information about the parameters
            ex.message += " (type=" + fot + " case=" + foc +
                           " pattern=" + pattern + " match=" + matchExpected +
                           " backwards=" + backwards + ")";
            throw ex;
        }
    }
};

// bug 105541
TestKoFind.prototype.test_replace_unicode = function test_replace() {
    this.context.type = Ci.koIFindContext.FCT_CURRENT_DOC;
    let scimoz = ko.views.currentView.scimoz = new SciMoz();

    var runs = [
        {
            text: "XXXXXX兌",
            pattern: "XXXXXX",
            replacement: "",
            result: "兌",
        },
        {
            text: "XXXXXXÜÖÄ0123456\n",
            pattern: "XXXXXX",
            replacement: "",
            result: "ÜÖÄ0123456\n",
        },
        {
            text: "XXXXXX兌",
            pattern: "XXXXXX",
            replacement: "ÜÖÄ",
            result: "ÜÖÄ兌",
        },
        {
            text: "XXXXXXÜÖÄ0123456\n",
            pattern: "XXXXXX",
            replacement: "兌",
            result: "兌ÜÖÄ0123456\n",
        },
    ];
    this.options.patternType = FOT_SIMPLE;
    this.options.caseSensitivity = FOC_SENSITIVE;

    for (let run of runs) {
        var {text, pattern, replacement, result} = run;
        scimoz.text = text;
        let success = ko.find.replaceAll(this.scope, /* editor */
                                    this.context, /* context */
                                    pattern, /* pattern */
                                    replacement, /* replacement */
                                    false, /* show replace results */
                                    false, /* first on line */
                                    function() {}, /* msg handler */
                                    false); /* highlight replacements */
    
        this.assertTrue(success, "replaceAll didn't find any results");
        this.assertEquals(result, scimoz.text,
                          "Unexpected replace text result");
    }
};

const JS_TESTS = ["TestKoFind"];
