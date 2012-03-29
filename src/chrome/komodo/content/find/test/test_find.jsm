const {classes: Cc, interfaces: Ci, utils: Cu} = Components;
Cu.import("resource://komodo-jstest/JSTest.jsm");
Cu.import("resource://gre/modules/Services.jsm");

var ko = {};
Cu.import("resource://komodo-jstest/mock/mock.jsm", {})
  .import(ko, "logging", "views", "macros", "mru", "history", "stringutils",
          "findresults", "statusbar",
          "chrome://komodo/content/library/tabstops.js");

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

function TestKoFind() {
    this.scope = null;
    this.context = null;
    this.log = ko.logging.getLogger("find.test");
}
TestKoFind.prototype = new TestCase();

TestKoFind.prototype.setUp = function TestKoFind_setUp() {
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
};

TestKoFind.prototype.tearDown = function TestKoFind_tearDown() {
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

TestKoFind.prototype.test_findNext = function test_findNext() {
    /**
     * Each of these functions do what's necessary to set up a different pattern
     * type then return the pattern to use for searching
     */
    let patterns = [
        function plain() {
            this.options.patternType = Ci.koIFindOptions.FOT_SIMPLE;
            return "hello";
        },
        function wildcard() {
            this.options.patternType = Ci.koIFindOptions.FOT_WILDCARD;
            return "h*o";
        },
        function re_python() {
            this.options.patternType = Ci.koIFindOptions.FOT_REGEX_PYTHON;
            return "h.(.)\\1o";
        },
    ];
    let higlightOptions = [false, true, false, true];

    this.context.type = Ci.koIFindContext.FCT_CURRENT_DOC;
    let scimoz = ko.views.currentView.scimoz = new ko.views.SciMozMock();
    scimoz.text = "hello hello hello";
    let highlightBits = [1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1];

    for each (let [setup, highlight] in permute(patterns, higlightOptions)) {
        try {
            let pattern = setup.call(this);
            Components.classes["@activestate.com/koFindSession;1"]
                      .getService(Components.interfaces.koIFindSession)
                      .Reset();
            scimoz.indicatorCurrent = Ci.koILintResult.DECORATOR_FIND_HIGHLIGHT;
            scimoz.indicatorValue = 0;
            scimoz.indicatorFillRange(0, scimoz.text.length);
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

            var checkHighlights = (function checkHighlights() {
                for (let i = 0; i < scimoz.text.length; ++i) {
                    let expected = highlightBits[i] && (1 << Ci.koILintResult.DECORATOR_FIND_HIGHLIGHT);
                    if (!highlight) expected = 0;
                    this.assertEquals(expected, scimoz.indicatorAllOnFor(i),
                                      "Unexpected indicators at " + i);
                }
            }).bind(this);

            let result = findNext(pattern);
            this.assertTrue(result, "Failed to find results for " + pattern);
            this.assertEquals(scimoz.anchor, 0, "Incorrect start position");
            this.assertEquals(scimoz.currentPos, 5, "Incorrect end position");
            checkHighlights();
            result = findNext(pattern);
            this.assertTrue(result, "Failed to find results for " + pattern);
            this.assertEquals(scimoz.anchor, 6, "Incorrect start position");
            this.assertEquals(scimoz.currentPos, 11, "Incorrect end position");
            checkHighlights();
            result = findNext(pattern);
            this.assertTrue(result, "Failed to find results for " + pattern);
            this.assertEquals(scimoz.anchor, 12, "Incorrect start position");
            this.assertEquals(scimoz.currentPos, 17, "Incorrect end position");
            checkHighlights();
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
            checkHighlights();
        } catch (ex if ex instanceof TestCase.TestError) {
            // Tack on additional information about the parameters
            ex.message += " (setup=" + setup.name + " highlight=" + highlight + ")";
            throw ex;
        }
    }
};

TestKoFind.prototype.test_findPrevious = function test_findPrevious() {
    this.context.type = Ci.koIFindContext.FCT_CURRENT_DOC;
    this.options.searchBackward = true;
    let scimoz = ko.views.currentView.scimoz = new ko.views.SciMozMock();
    scimoz.text = "hello hello hello";

    var findNext = (function findNext(pattern) {
        return ko.find.findNext(this.scope, /* editor window */
                                this.context, /* find context */
                                pattern, /* pattern */
                                "find", /* mode */
                                true, /* quiet */
                                false, /* use MRU */
                                this.msgHandler.bind(this), /* message handler */
                                false, /* highlight matches */
                                0 /* highlight timeout */);
    }).bind(this);

    let result;
    scimoz.setSelection(-1, -1);
    this.assertEquals(scimoz.anchor, scimoz.text.length);
    result = findNext("hello");
    this.assertTrue(result, "Failed to find last result");
    this.assertEquals(scimoz.anchor, 12, "Incorrect start position");
    this.assertEquals(scimoz.currentPos, 17, "Incorrect end position");
    result = findNext("hello");
    this.assertTrue(this.options.searchBackward);
    this.assertTrue(result, "Failed to find second result");
    this.assertEquals(scimoz.anchor, 6, "Incorrect start position");
    this.assertEquals(scimoz.currentPos, 11, "Incorrect end position");
    result = findNext("hello");
    this.assertTrue(this.options.searchBackward);
    this.assertTrue(result, "Failed to find first result");
    this.assertEquals(scimoz.anchor, 0, "Incorrect start position");
    this.assertEquals(scimoz.currentPos, 5, "Incorrect end position");
    result = findNext("hello");
    this.assertFalse(result, "Unexpectedly wrapped find result: [" +
                     scimoz.anchor + "," + scimoz.currentPos + "]");
    scimoz.setSelection(-1, -1);
    result = findNext("world");
    this.assertFalse(result, "Unexpected found result");
    result = findNext("hello");
    this.assertTrue(result, "Failed to find results");
    this.assertEquals(scimoz.anchor, 12, "Incorrect start position");
    this.assertEquals(scimoz.currentPos, 17, "Incorrect end position");
};

TestKoFind.prototype.test_findAll = function test_findAll() {
    this.context.type = Ci.koIFindContext.FCT_CURRENT_DOC;
    let scimoz = ko.views.currentView.scimoz = new ko.views.SciMozMock();
    scimoz.text = "hello hello hello";
    let result;
    result = ko.find.findAll(this.scope, /* editor window */
                             this.context, /* find context */
                             "hello", /* pattern */
                             "hello_alias", /* pattern alias */
                             this.msgHandler.bind(this), /* message handler */
                             false /* hightlight matches */);
    this.assertTrue(result, "Failed to find all");
    let tab = ko.findresults.getTab();
    this.assertTrue(tab.success, "Find results claimed failure");
    this.assertEquals(tab.numResults, 3, "Did not find all results");
    this.assertEquals(tab.numFiles, null, "Not expecting file counts for current doc");
    this.assertEquals(tab.numFilesSearched, null, "Not expecting file counts for current doc");

    this.assertEquals(tab.journalId, undefined, "Journal id given for non-replace findAll");
    this.assertEquals(tab.view.GetNumUrls(), 1, "Expected 1 URL");
    this.assertEquals(ko.views.currentView.koDoc.displayPath, tab.view.GetUrl(0),
                      "Unexpected URL for the document");

    this.assertEquals(tab.view.rowCount, 3, "Expected 3 results");
    for (let i = 0; i < tab.view.rowCount; ++i) {
        this.assertEquals(tab.view.getCellText(i, {id: "value"}), "hello", "Unexpected text");
        this.assertEquals(tab.view.GetValue(i), "hello", "Unexpected value");
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
};

TestKoFind.prototype.test_markAll = function test_markAll() {
    this.context.type = Ci.koIFindContext.FCT_CURRENT_DOC;
    let view = ko.views.currentView = new ko.views.ViewBookmarkableMock();
    let scimoz = view.scimoz = new ko.views.SciMozMock();
    scimoz.text = ["hello", "world", "hello", "world", "hello", "world"].join("\n");
    let result;
    result = ko.find.markAll(this.scope, /* editor */
                             this.context, /* find context */
                             "hello", /* pattern */
                             "hello_alias", /* pattern alias */
                             this.msgHandler.bind(this) /* message handler */);
    this.assertTrue(result, "Bookmarks should have been created");
    this.assertEquals(view.bookmarks, [0, 2, 4],
                      "Bookmarks in the wrong places");
};

TestKoFind.prototype.test_findAllInFiles = function test_findAllInFiles() {
    this.context = Cc["@activestate.com/koFindInFilesContext;1"]
                     .createInstance(Ci.koIFindInFilesContext);
    this.context.type = Ci.koIFindContext.FCT_IN_FILES;
    var fileSvc = Cc["@activestate.com/koFileService;1"].getService(Ci.koIFileService);
    var dirName = fileSvc.makeTempDir(".tmp", "komodo_test_find_findAllInFiles_");
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
        result = ko.find.findAllInFiles(this.scope, /* editor */
                                        this.context, /* find context */
                                        "hello", /* pattern */
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
        this.assertEquals(resultsTab.numResults, 4, "Expected 4 results");
        this.assertEquals(resultsTab.numFiles, 2, "Expected 2 files");
        this.assertEquals(resultsTab.numFilesSearched, 3, "Expected 3 files searched");
    } finally {
        fileSvc.deleteTempDir(dirName);
    }
};


TestKoFind.prototype.test_findAllInMacro = function test_findAllInMacro() {
    let scimoz = ko.views.currentView.scimoz = new ko.views.SciMozMock();
    scimoz.text = "hello hello hello";
    ko.find.findAllInMacro(this.scope, /* editor window */
                           Ci.koIFindContext.FCT_CURRENT_DOC, /* context type */
                           "hello", /* pattern */
                           Ci.koIFindOptions.FOT_SIMPLE, /* pattern type */
                           Ci.koIFindOptions.FOC_SENSITIVE, /* case sensitivity */
                           false, /* search backward */
                           true); /* match word */
    let tab = ko.findresults.getTab();
    this.assertTrue(tab.success, "Find results claimed failure");
    this.assertEquals(tab.numResults, 3, "Did not find all results");
    this.assertEquals(tab.numFiles, null, "Not expecting file counts for current doc");
    this.assertEquals(tab.numFilesSearched, null, "Not expecting file counts for current doc");

    this.assertEquals(1, tab.view.GetNumUrls(), "Expected one URL in find results");
    this.assertEquals(ko.views.currentView.koDoc.displayPath, tab.view.GetUrl(0),
                      "Unexpected URL for the document");

    this.assertEquals(tab.view.rowCount, 3, "Expected 3 results");
    for (let i = 0; i < tab.view.rowCount; ++i) {
        this.assertEquals(tab.view.getCellText(i, {id: "value"}), "hello", "Unexpected text");
        this.assertEquals(tab.view.GetValue(i), "hello", "Unexpected value");
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
};

TestKoFind.prototype.test_findNextInMacro = function test_findNextInMacro() {
    let scimoz = ko.views.currentView.scimoz = new ko.views.SciMozMock();
    scimoz.text = "hello hello hello";

    var findNextInMacro = (function findNext(pattern) {
        ko.find.findNextInMacro(this.scope, /* editor window */
                                Ci.koIFindContext.FCT_CURRENT_DOC, /* context type */
                                pattern, /* pattern */
                                Ci.koIFindOptions.FOT_SIMPLE, /* pattern type */
                                Ci.koIFindOptions.FOC_SENSITIVE, /* case sensitivity */
                                false, /* search backward */
                                false, /* match word */
                                "find", /* find */
                                true, /* quiet */
                                false); /* use MRU */
    }).bind(this);

    findNextInMacro("hello");
    this.assertEquals(scimoz.anchor, 0, "Incorrect start position");
    this.assertEquals(scimoz.currentPos, 5, "Incorrect end position");
    findNextInMacro("hello");
    this.assertEquals(scimoz.anchor, 6, "Incorrect start position");
    this.assertEquals(scimoz.currentPos, 11, "Incorrect end position");
    findNextInMacro("hello");
    this.assertEquals(scimoz.anchor, 12, "Incorrect start position");
    this.assertEquals(scimoz.currentPos, 17, "Incorrect end position");
    findNextInMacro("hello");
    scimoz.setSel(0, 0);
    findNextInMacro("world");
    this.assertEquals(scimoz.anchor, 0, "Unexpected anchor movement for failed find");
    this.assertEquals(scimoz.currentPos, 0, "Unexpected end movement for failed find");
    findNextInMacro("hello");
    this.assertEquals(scimoz.anchor, 0, "Incorrect start position");
    this.assertEquals(scimoz.currentPos, 5, "Incorrect end position");
};

TestKoFind.prototype.test_highlightAllMatches = function test_highlightAllMatches() {
    this.context.type = Ci.koIFindContext.FCT_CURRENT_DOC;
    let scimoz = ko.views.currentView.scimoz = new ko.views.SciMozMock();
    scimoz.text = "hello hello hello";

    ko.find.highlightAllMatches(scimoz, this.context, "hello", 1000);
    let expected = [1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1];
    for (let i = 0; i < scimoz.text.length; ++i) {
        let target = expected[i] && (1 << Ci.koILintResult.DECORATOR_FIND_HIGHLIGHT);
        this.assertEquals(target, scimoz.indicatorAllOnFor(i),
                          "Unexpected indicators at " + i);
    }
};

TestKoFind.prototype.test_highlightClearAll = function test_highlightClearAll() {
    this.context.type = Ci.koIFindContext.FCT_CURRENT_DOC;
    let scimoz = ko.views.currentView.scimoz = new ko.views.SciMozMock();
    scimoz.text = "hello hello hello";

    ko.find.highlightAllMatches(scimoz, this.context, "hello", 1000);
    let expected = [1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1];
    for (let i = 0; i < scimoz.text.length; ++i) {
        let target = expected[i] && (1 << Ci.koILintResult.DECORATOR_FIND_HIGHLIGHT);
        this.assertEquals(target, scimoz.indicatorAllOnFor(i),
                          "Unexpected indicators at " + i);
    }
    ko.find.highlightClearAll(scimoz);
    for (let i = 0; i < scimoz.text.length; ++i) {
        this.assertEquals(0, scimoz.indicatorAllOnFor(i),
                          "Unexpected indicators at " + i);
    }
};

TestKoFind.prototype.test_highlightClearPosition = function test_highlightClearPosition() {
    const INDIC = Ci.koILintResult.DECORATOR_FIND_HIGHLIGHT;
    this.context.type = Ci.koIFindContext.FCT_CURRENT_DOC;
    let scimoz = ko.views.currentView.scimoz = new ko.views.SciMozMock();
    scimoz.text = "hello hello hello";

    ko.find.highlightAllMatches(scimoz, this.context, "hello", 1000);
    let expected = [1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1];
    for (let i = 0; i < scimoz.text.length; ++i) {
        let target = expected[i] && (1 << INDIC);
        this.assertEquals(target, scimoz.indicatorAllOnFor(i),
                          "Unexpected indicators at " + i);
    }
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
    for (let i = 0; i < scimoz.text.length; ++i) {
        let target = expected[i] && (1 << INDIC);
        this.assertEquals(target, scimoz.indicatorAllOnFor(i),
                          "Unexpected indicators at " + i);
    }
};

TestKoFind.prototype.test_markAllInMacro = function test_markAllInMacro() {
    let view = ko.views.currentView = new ko.views.ViewBookmarkableMock();
    let scimoz = view.scimoz = new ko.views.SciMozMock();
    scimoz.text = ["hello", "world", "hello", "world", "hello", "world"].join("\n");
    ko.find.markAllInMacro(this.scope, /* editor */
                           Ci.koIFindContext.FCT_CURRENT_DOC, /* context type */
                           "hello", /* pattern */
                           Ci.koIFindOptions.FOT_SIMPLE, /* pattern type */
                           Ci.koIFindOptions.FOC_SENSITIVE, /* case sensitivity */
                           false, /* search backward */
                           false); /* match word */
    this.assertEquals(view.bookmarks, [0, 2, 4],
                      "Bookmarks in the wrong places");
};

TestKoFind.prototype.test_replace = function test_replace() {
    this.context.type = Ci.koIFindContext.FCT_CURRENT_DOC;
    let scimoz = ko.views.currentView.scimoz = new ko.views.SciMozMock();
    scimoz.text = "hello hello hello";
    let expected = ["hello hello hello", /* first time just highlights */
                    "world hello hello",
                    "world world hello",
                    "world world world"];

    let result;
    while (expected.length > 0) {
        result = ko.find.replace(this.scope, /* editor */
                                 this.context, /* context */
                                 "hello", /* pattern */
                                 "world", /* replacement */
                                 function(){}); /* msg handler */

        if (expected.length > 1) {
            this.assertTrue(result, "Replace didn't find next result");
        } else {
            this.assertFalse(result, "Replace found unexpected next result");
        }
        this.assertEquals(expected.shift(), scimoz.text,
                          "Replace didn't change the text");
    }
};

TestKoFind.prototype.test_replaceAll = function test_replaceAll() {
    this.context.type = Ci.koIFindContext.FCT_CURRENT_DOC;
    let scimoz = ko.views.currentView.scimoz = new ko.views.SciMozMock();
    scimoz.text = "hello hello hello";
    let result;
    result = ko.find.replaceAll(this.scope, /* editor */
                                this.context, /* context */
                                "hello", /* pattern */
                                "world", /* replacement */
                                false, /* show replace results */
                                false, /* first on line */
                                function() {}, /* msg handler */
                                false); /* highlight replacements */
    this.assertTrue(result, "Expected replace to find things");
    this.assertEquals(scimoz.text, "world world world",
                      "Replace all didn't replace correctly");
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

TestKoFind.prototype.test_replaceAllInMacro = function test_replaceAllInMacro() {
    let scimoz = ko.views.currentView.scimoz = new ko.views.SciMozMock();
    scimoz.text = "hello hello hello";
    ko.find.replaceAllInMacro(this.scope, /* editor */
                              Ci.koIFindContext.FCT_CURRENT_DOC, /* context type */
                              "hello", /* pattern */
                              "world", /* replacement */
                              true, /* quiet */
                              Ci.koIFindOptions.FOT_SIMPLE, /* pattern type */
                              Ci.koIFindOptions.FOC_SENSITIVE, /* case sensitivity */
                              false, /* search backward */
                              false); /* match word */
    this.assertEquals(scimoz.text, "world world world",
                      "Replace all didn't replace correctly");
};

TestKoFind.prototype.test_replaceInMacro = function test_replaceInMacro() {
    let scimoz = ko.views.currentView.scimoz = new ko.views.SciMozMock();
    scimoz.text = "hello hello hello";
    let expected = ["hello hello hello", /* first time just highlights */
                    "world hello hello",
                    "world world hello",
                    "world world world"];

    while (expected.length > 0) {
        ko.find.replaceInMacro(this.scope, /* editor */
                               Ci.koIFindContext.FCT_CURRENT_DOC, /* context type */
                               "hello", /* pattern */
                               "world", /* replacement */
                               Ci.koIFindOptions.FOT_SIMPLE, /* pattern type */
                               Ci.koIFindOptions.FOC_SENSITIVE, /* case sensitivity */
                               false, /* search backward */
                               false); /* match word */

        this.assertEquals(expected.shift(), scimoz.text,
                          "Replace didn't change the text");
    }
};

const JS_TESTS = ["TestKoFind"];
