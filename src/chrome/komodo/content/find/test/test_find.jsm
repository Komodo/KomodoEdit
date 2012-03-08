const {classes: Cc, interfaces: Ci, utils: Cu} = Components;
Cu.import("resource://komodo-jstest/JSTest.jsm");

var ko = {};
Cu.import("resource://komodo-jstest/mock/mock.jsm", {})
  .import(ko, "logging", "views", "macros", "mru", "history", "stringutils",
          "findresults");

function TestFindInOpenFiles() {
    this.scope = null;
    this.context = null;
    this.log = ko.logging.getLogger("find.test");
}
TestFindInOpenFiles.prototype = new TestCase();

TestFindInOpenFiles.prototype.setUp = function TestFindInOpenFiles_setUp() {
    let loader = Cc['@mozilla.org/moz/jssubscript-loader;1']
                   .getService(Ci.mozIJSSubScriptLoader);
    this.scope = { ko: ko, __noSuchMethod__: function() {}};
    loader.loadSubScript("chrome://komodo/content/find/find_functions.js", this.scope, "UTF-8");
    this.context = Cc["@activestate.com/koFindContext;1"]
                     .createInstance(Ci.koIFindContext);
    this.findSvc = Cc["@activestate.com/koFindService;1"]
                     .getService(Ci.koIFindService);
    this.options = this.findSvc.options;
};

TestFindInOpenFiles.prototype.tearDown = function TestFindInOpenFiles_tearDown() {
    this.options.searchBackward = false;
    this.scope = null;
    this.context = null;
    this.findSvc = null;
    this.options = null;
};

TestFindInOpenFiles.prototype.msgHandler =
function TestFindInOpenFiles_msgHandler(level, context, message) {
    this.fail("Message handler called in quiet mode: " +
              "level=" + level + " context=" + context +
              " message=" + message + "\n");
};

TestFindInOpenFiles.prototype.test_findNext = function test_findNext() {
    this.context.type = Ci.koIFindContext.FCT_CURRENT_DOC;
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

    let result = findNext("hello");
    this.assertTrue(result, "Failed to find results");
    this.assertEquals(scimoz.anchor, 0, "Incorrect start position");
    this.assertEquals(scimoz.currentPos, 5, "Incorrect end position");
    result = findNext("hello");
    this.assertTrue(result, "Failed to find results");
    this.assertEquals(scimoz.anchor, 6, "Incorrect start position");
    this.assertEquals(scimoz.currentPos, 11, "Incorrect end position");
    result = findNext("hello");
    this.assertTrue(result, "Failed to find results");
    this.assertEquals(scimoz.anchor, 12, "Incorrect start position");
    this.assertEquals(scimoz.currentPos, 17, "Incorrect end position");
    result = findNext("hello");
    this.assertFalse(result, "Unexpectedly wrapped find result: [" +
                     scimoz.anchor + "," + scimoz.currentPos + "]");
    scimoz.setSel(0, 0);
    result = findNext("world");
    this.assertFalse(result, "Unexpected found result");
    result = findNext("hello");
    this.assertTrue(result, "Failed to find results");
    this.assertEquals(scimoz.anchor, 0, "Incorrect start position");
    this.assertEquals(scimoz.currentPos, 5, "Incorrect end position");
};

TestFindInOpenFiles.prototype.test_findPrevious = function test_findPrevious() {
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

TestFindInOpenFiles.prototype.test_findAll = function test_findAll() {
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

TestFindInOpenFiles.prototype.test_markAll = function test_markAll() {
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

const JS_TESTS = ["TestFindInOpenFiles"];
