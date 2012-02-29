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
    this.context = Components.classes["@activestate.com/koFindContext;1"]
                    .createInstance(Components.interfaces.koIFindContext);
};

TestFindInOpenFiles.prototype.tearDown = function TestFindInOpenFiles_tearDown() {
    this.scope = null;
    this.context = null;
};

TestFindInOpenFiles.prototype.msgHandler =
function TestFindInOpenFiles_msgHandler(level, context, message) {
    this.fail("Message handler called in quiet mode: " +
              "level=" + level + " context=" + context +
              "message=" + message);
};

TestFindInOpenFiles.prototype.test_forwards = function test_forwards() {
    this.context.type = Ci.koIFindContext.FCT_CURRENT_DOC;
    let scimoz = ko.views.currentView.scimoz = new ko.views.SciMozMock();
    scimoz.text = "hello hello hello";

    let result = ko.find.findNext(this.scope, /* editor window */
                                  this.context, /* find context */
                                  "hello", /* pattern */
                                  "find", /* mode */
                                  true, /* quiet */
                                  false, /* use MRU */
                                  this.msgHandler.bind(this), /* message handler */
                                  false, /* highlight matches */
                                  0 /* highlight timeout */);

    this.assertTrue(result, "Failed to find results");
    this.assertEquals(scimoz.anchor, 0, "Incorrect start position");
    this.assertEquals(scimoz.currentPos, 5, "Incorrect end position");
};

const JS_TESTS = ["TestFindInOpenFiles"];
