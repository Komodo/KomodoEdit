const {classes: Cc, interfaces: Ci, utils: Cu} = Components;
Cu.import("resource://komodo-jstest/JSTest.jsm");

var ko = {};
ko.logging = Cu.import("chrome://komodo/content/library/logging.js", {}).logging;
Cu.import("resource://komodo-jstest/mock/mock.jsm", {})
  .import(ko, "views", "macros", "history", "stringutils");

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
              "message=" + message);
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

const JS_TESTS = ["TestFindInOpenFiles"];
