const {classes: Cc, interfaces: Ci, utils: Cu} = Components;
Cu.import("resource://komodo-jstest/JSTest.jsm");
Cu.import("resource://gre/modules/Services.jsm");

var ko = {};
Cu.import("resource://komodo-jstest/mock/mock.jsm", {})
  .import(ko, "views", "macros", "mru", "history", "stringutils",
          "findresults", "statusbar",
          "chrome://komodo/content/library/tabstops.js");

let logging = Components.utils.import("chrome://komodo/content/library/logging.js", {}).logging;

var rubyLangSvc = Cc["@activestate.com/koLanguageRegistryService;1"]
                     .getService(Ci.koILanguageRegistryService)
                     .getLanguage("Ruby");
                     
function TestRubyLangSvc() {
    this.log = null;
    this.log = logging.getLogger("rubyLangSvc.TestCase");
    this.log.setLevel(ko.logging.LOG_DEBUG);
}
TestRubyLangSvc.prototype = new TestCase();

TestRubyLangSvc.prototype.setUp = function TestRubyLangSvc_setUp() {
    let loader = Cc['@mozilla.org/moz/jssubscript-loader;1']
                   .getService(Ci.mozIJSSubScriptLoader);
    this.scope = { ko: ko, __noSuchMethod__: function() {}};
    this.fileSvc = Cc["@activestate.com/koFileService;1"].getService(Ci.koIFileService);
    this.docSvc = Cc["@activestate.com/koDocumentService;1"].getService(Ci.koIDocumentService);
    this.globalPrefs = Cc["@activestate.com/koPrefService;1"].getService(Ci.koIPrefService).prefs;
    this.encodingSvc = Cc["@activestate.com/koEncodingServices;1"].getService(Ci.koIEncodingServices);
    this.koIDocument = Ci.koIDocument;
    var this_ = this;
    this.origPrefs = {
      ensureFinalEOL: this_.globalPrefs.getBooleanPref("ensureFinalEOL"),
      cleanLineEnds: this_.globalPrefs.getBooleanPref("cleanLineEnds"),
      cleanLineEnds_CleanCurrentLine: this_.globalPrefs.getBooleanPref("cleanLineEnds_CleanCurrentLine"),
      cleanLineEnds_ChangedLinesOnly: this_.globalPrefs.getBooleanPref("cleanLineEnds_ChangedLinesOnly")
    };
};

TestRubyLangSvc.prototype.setPrefsShortcut = function TestRubyLangSvc_setPrefsShortcut(prefsObj) {
    for (var p in prefsObj) {
        this.globalPrefs.setBooleanPref(p, prefsObj[p]);
    }
};

TestRubyLangSvc.prototype.tearDown = function TestRubyLangSvc_tearDown() {
    var prefName;
    for (prefName in this.origPrefs) {
        this.globalPrefs.setBooleanPref(prefName, this.origPrefs[prefName]);
    }
};

TestRubyLangSvc.prototype.msgHandler =
function TestRubyLangSvc_msgHandler(level, context, message) {
    this.fail("Message handler called in quiet mode: " +
              "level=" + level + " context=" + context +
              " message=" + message + "\n");
};

TestRubyLangSvc.prototype.sp = function sp(len) {
    var val = "";
    var padChar = " ";
    while (val.length < len) {
        val = "" + padChar + val;
    }
    return val;
};

TestRubyLangSvc.prototype._get_scimoz_and_koDoc_from_string = function(buf, styles_01) {
    var view = new ko.views.ViewMock({text:buf});
    var scimoz = view.scimoz;
    // Easier to always use LF line endings for tests (at least be consistent)
    scimoz.eOLMode = scimoz.SC_EOL_LF;
    if ('@activestate.com/ISciMozHeadless;1' in Cc) {
        //this.log.debug("We have a headless scimoz");
        // Set up the real HTML lexer (for styling information)
        var lexerSvc = Cc["@activestate.com/koLanguageRegistryService;1"]
                         .getService(Ci.koILanguageRegistryService)
                         .getLanguage("Ruby")
                         .getLanguageService(Ci.koILexerLanguageService);
        lexerSvc.setCurrent(scimoz);
        scimoz.colourise(0, scimoz.length);
        if (styles_01) {
            let actual_styles = scimoz.getStyleRange(0, scimoz.length);
            this.assertEquals(actual_styles, styles_01,
                              "Style mismatch:\n" +
                              actual_styles + "\n" +
                              styles_01);
        }
    } else {
        //this.log.debug(":((((( No headless scimoz");
        scimoz.startStyling(0, ~0);
        scimoz.setStylingEx(styles_01.length,
                            styles_01.map(c => String.fromCharCode(c)).join(""));
    }
    return [scimoz, view.koDoc, view];
};

TestRubyLangSvc.prototype.test_add_bar_at_doc_end = function test_add_bar_at_doc_end() {
    var file = this.fileSvc.makeTempFile(".rb", 'wb');
    var buf_01 = [ 'class C'
                   ,'  def zipper(a, b)'
                   ,'    a.each do | yop, dewer, zak '];
    var styles_01 = [ 5, 5, 5, 5, 5, 0, 8, 0,
 0, 0, 5, 5, 5, 0, 9, 9, 9, 9, 9, 9, 10, 11, 10, 0, 11, 10, 0,
 0, 0, 0, 0, 11, 10, 11, 11, 11, 11, 0, 5, 5, 0, 10, 0, 11, 11, 11, 10, 0,

 11, 11, 11, 11, 11, 10, 0, 11, 11, 11, 0];
    var text_01 = buf_01.join("\n");
    [scimoz, koDoc] = this._get_scimoz_and_koDoc_from_string(text_01, styles_01);
    scimoz.indent = 2;
    scimoz.tabWidth = 8;
    // Add the new character
    scimoz.currentPos = scimoz.length;
    scimoz.addText(1, "|");
    if ("colourise" in scimoz) {
        scimoz.colourise(text_01.length, scimoz.length);
    } else {
        scimoz.styles.push(10);
    }
    this.assertEquals(text_01 + "|", scimoz.text);
    scimoz.currentPos += 1;
    rubyLangSvc.keyPressed("|", scimoz);
    let expected = text_01 + "|" + "\n" + this.sp(4) + "end";
    this.assertEquals(expected, scimoz.text,
                      "Mismatch:\n" +
                      escape(expected) + "\n" +
                      escape(scimoz.text));
};

TestRubyLangSvc.prototype.test_add_bar_in_middle_01 = function test_add_bar_in_middle_01() {
    var file = this.fileSvc.makeTempFile(".rb", 'wb');
    var buf_01 = [ 'class C'
                   ,'  def zipper(a, b)'
                   ,'    a.each do | yop, dewer, zak  '
                   ,'  end'];
    var styles_01 = [
        5, 5, 5, 5, 5, 0, 8, 0,
      //c  l  a  s  s     C  \n
        0, 0, 5, 5, 5, 0, 9, 9, 9, 9, 9, 9, 10, 11, 10, 0, 11, 10, 0,
      //      d  e  f     z  i  p  p  e  r   (   a   ,      b   )  \n
        0, 0, 0, 0, 11, 10, 11, 11, 11, 11, 0, 5, 5, 0, 10, 0, 11, 11, 11, 10, 0,
      //             a   .   e   a   c   h     d  o      |      y   o   p   ,
            11, 11, 11, 11, 11, 10, 0, 11, 11, 11, 0, 0, 0,
          // d   e   w   e   r   ,      z   a   k        \n
        0, 0, 5, 5, 5];
      //      e  n  d
    var text_01 = buf_01.join("\n");
    [scimoz, koDoc] = this._get_scimoz_and_koDoc_from_string(text_01, styles_01);
    scimoz.indent = 2;
    scimoz.tabWidth = 8;
    // Add the new character
    var changePosn = scimoz.getLineEndPosition(2) - 1;
    //this.log.debug("text: "
    //               + text_01.substr(0, changePosn)
    //               + "<***<"
    //               + text_01[changePosn]
    //               + ">***>"
    //               + text_01.substr(changePosn + 1));
    scimoz.targetStart = changePosn;
    scimoz.targetEnd = changePosn + 1;
    scimoz.currentPos = changePosn;
    scimoz.replaceTarget(1, "|");
    if ("colourise" in scimoz) {
        scimoz.colourise(scimoz.targetStart, scimoz.targetEnd);
    } else {
        scimoz.styles[scimoz.currentPos] = 10;
    }
    var text_02 = text_01.substr(0, changePosn) + "|" + text_01.substr(changePosn + 1);
    this.assertEquals(text_02, scimoz.text);
    scimoz.currentPos += 1;
    rubyLangSvc.keyPressed("|", scimoz);
    var newExpectedText = (text_01.substr(0, changePosn) + "|\n"
                           + this.sp(4) + "end\n"
                           + buf_01[3]);
    this.assertEquals(newExpectedText, scimoz.text);
};

var JS_TESTS = ["TestRubyLangSvc"];