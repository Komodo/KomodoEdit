// Run tests on HTML autoindenting

const {classes: Cc, interfaces: Ci, utils: Cu, results: Cr} = Components;
Cu.import("resource://komodo-jstest/JSTest.jsm");
Cu.import("resource://gre/modules/Services.jsm");

var ko = {};
Cu.import("resource://komodo-jstest/mock/mock.jsm", {})
  .import(ko, "logging", "views", "stringutils");

function TestHTMLAutoIndentEmptyTag() {
    this.log = ko.logging.getLogger("TestHTMLAutoIndentEmptyTag.test");
    //this.log.setLevel(ko.logging.LOG_DEBUG);
}


var htmlLangSvc = Cc["@activestate.com/koLanguageRegistryService;1"]
                     .getService(Ci.koILanguageRegistryService)
                     .getLanguage("HTML");
var html5LangSvc = Cc["@activestate.com/koLanguageRegistryService;1"]
                     .getService(Ci.koILanguageRegistryService)
                     .getLanguage("HTML5");
                         
TestHTMLAutoIndentEmptyTag.prototype = new TestCase();

TestHTMLAutoIndentEmptyTag.prototype.setUp = function TestHTMLAutoIndent_setUp() {
};

TestHTMLAutoIndentEmptyTag.prototype.tearDown = function TestHTMLAutoIndent_tearDown() {
};

TestHTMLAutoIndentEmptyTag.prototype._get_scimoz_and_koDoc_from_string = function(buf, styles_01) {
    var view = new ko.views.ViewMock({text:buf});
    var scimoz = view.scimoz;
    if ('@activestate.com/ISciMozHeadless;1' in Cc) {
        //this.log.debug("We have a headless scimoz");
        // Set up the real HTML lexer (for styling information)
        var lexerSvc = Cc["@activestate.com/koLanguageRegistryService;1"]
                         .getService(Ci.koILanguageRegistryService)
                         .getLanguage("HTML5")
                         .getLanguageService(Ci.koILexerLanguageService);
        lexerSvc.setCurrent(scimoz);
        scimoz.colourise(0, -1);
    } else {
        //this.log.debug(":((((( No headless scimoz");
        scimoz.startStyling(0, ~0);
        scimoz.setStylingEx(styles_01.length,
                            styles_01.map(c => String.fromCharCode(c)).join(""));
    }
    return [scimoz, view.koDoc, view];
};

function rep(str, count) {
    var a = [];
    while (--count >= 0) {
        a.push(str);
    }
    return a.join("");
}

TestHTMLAutoIndentEmptyTag.prototype.test_implicitEmptyStartTagCloseIndent01 =
function test_implicitEmptyStartTagCloseIndent01() {
    // bug 100715 don't increase indent after an empty tag like "<img...>"
    var buf_01 = [ '<!DOCTYPE HTML>'
                 ,'<head>'
                 ,'    <link id="css-3990894201" >'
                 ,'    <script>alert("howdy")</script>'
                 ,'    <title>title here</title>'
                 ,'    <meta name="description" content="stuff">'
                 ,'    <link rel="search" type="application/opensearchdescription+xml" >'
                 ,'    <base href="flips">'
                 ,'    <link rel="icon"><link rel="alternate"><link rel="alternate">'
                 ,'</head>'
                 ,'<body>'
                 ,'<p>para here: br here<br>'
                 ,'picture here: <img src="blip1"><img src="blip2">'
                 ,'hr here: <hr>'
                 ,'Now for an object:'
                 ,'<object class="wallop">'
                 ,'<param name="n1" value="v2">'
                 ,'</object>'
                 ,'<map id="map1">'
                 ,'<area alt="area51" ping="wired.com">'
                 ,'</map>'
                 ,'<form action="getform.php" method="get">'
                 ,'    First name: <input type="text" name="first_name" >'
                 ,'     Last name: <input type="text" name="last_name"  >'
                 ,'        E-mail: <input type="email" name="user_email" >'
                 ,'    <input type="submit" value="Submit" >'
                 ,'    <menu>'
                 ,'        <command type="radio">'
                 ,'    </menu>'
                 ,'    <output for="whatever">'
                 ,'</form>'
                 ,'<table>'
                 ,'    <colgroup>'
                 ,'        <col class="column1">'
                 ,'        <col class="columns2plus3" span="2">'
                 ,'    </colgroup>'
                 ,'</table>'
                 ,'<figure>here\'s a figure, with an caption:'
                 ,'<figcaption id="figc2">'
                 ,'</figure>'
                 ,'<audio src="whatever">'
                 ,'<source >'
                 ,'<video  >'
                 ,'<embed  >'
                 ,'<canvas >'
                 ,'<keygen >'
                 ,'<meter  >'
                 ,''
                ];
    // Styles include 10
    var styles_01 = [ 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
 1, 2, 2, 2, 2, 6, 0,
 0, 0, 0, 0, 1, 2, 2, 2, 2, 3, 4, 4, 5, 8, 8, 8, 8, 8, 8, 8, 8,
 8, 8, 8, 8, 8, 8, 8, 8, 3, 6, 0,
 0, 0, 0, 0, 1, 2, 2, 2, 2, 2, 2, 6, 28, 28, 28, 28, 28, 29, 26, 26, 26,
 26, 26, 26, 26, 29, 9, 9, 2, 2, 2, 2, 2, 2, 10, 0,
 0, 0, 0, 0, 1, 2, 2, 2, 2, 2, 6, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
 9, 9, 2, 2, 2, 2, 2, 10, 0,
 0, 0, 0, 0, 1, 2, 2, 2, 2, 3, 4, 4, 4, 4, 5, 8, 8, 8, 8, 8, 8,
 8, 8, 8, 8, 8, 8, 8, 3, 4, 4, 4, 4, 4, 4, 4, 5, 8, 8, 8, 8, 8,
 8, 8, 6, 0,
 0, 0, 0, 0, 1, 2, 2, 2, 2, 3, 4, 4, 4, 5, 8, 8, 8, 8, 8, 8, 8,
 8, 3, 4, 4, 4, 4, 5, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8,
 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8,
 8, 8, 8, 8, 3, 6, 0,
 0, 0, 0, 0, 1, 2, 2, 2, 2, 3, 4, 4, 4, 4, 5, 8, 8, 8, 8, 8, 8,
 8, 6, 0,
 0, 0, 0, 0, 1, 2, 2, 2, 2, 3, 4, 4, 4, 5, 8, 8, 8, 8, 8, 8, 6,
 1, 2, 2, 2, 2, 3, 4, 4, 4, 5, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8,
 6, 1, 2, 2, 2, 2, 3, 4, 4, 4, 5, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8,
 8, 6, 0,
 9, 9, 2, 2, 2, 2, 10, 0,
 1, 2, 2, 2, 2, 6, 0,
 1, 2, 6, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
 1, 2, 2, 6, 0,
 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 2, 2, 2, 3, 4, 4,
 4, 5, 8, 8, 8, 8, 8, 8, 8, 6, 1, 2, 2, 2, 3, 4, 4, 4, 5, 8, 8,
 8, 8, 8, 8, 8, 6, 0,
 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 2, 2, 6, 0,
 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
 1, 2, 2, 2, 2, 2, 2, 3, 4, 4, 4, 4, 4, 5, 8, 8, 8, 8, 8, 8, 8,
 8, 6, 0,
 1, 2, 2, 2, 2, 2, 3, 4, 4, 4, 4, 5, 8, 8, 8, 8, 3, 4, 4, 4, 4,
 4, 5, 8, 8, 8, 8, 6, 0,
 9, 9, 2, 2, 2, 2, 2, 2, 10, 0,
 1, 2, 2, 2, 3, 4, 4, 5, 8, 8, 8, 8, 8, 8, 6, 0,
 1, 2, 2, 2, 2, 3, 4, 4, 4, 5, 8, 8, 8, 8, 8, 8, 8, 8, 3, 4, 4,
 4, 4, 5, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 6, 0,
 9, 9, 2, 2, 2, 10, 0,
 1, 2, 2, 2, 2, 3, 4, 4, 4, 4, 4, 4, 5, 8, 8, 8, 8, 8, 8, 8, 8,
 8, 8, 8, 8, 8, 3, 4, 4, 4, 4, 4, 4, 5, 8, 8, 8, 8, 8, 6, 0,
 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 2, 2, 2, 2,
 2, 3, 4, 4, 4, 4, 5, 8, 8, 8, 8, 8, 8, 3, 4, 4, 4, 4, 5, 8, 8,
 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 3, 6, 0,
 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 2, 2, 2, 2,
 2, 3, 4, 4, 4, 4, 5, 8, 8, 8, 8, 8, 8, 3, 4, 4, 4, 4, 5, 8, 8,
 8, 8, 8, 8, 8, 8, 8, 8, 8, 3, 3, 6, 0,
 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 2, 2, 2, 2,
 2, 3, 4, 4, 4, 4, 5, 8, 8, 8, 8, 8, 8, 8, 3, 4, 4, 4, 4, 5, 8,
 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 3, 6, 0,
 0, 0, 0, 0, 1, 2, 2, 2, 2, 2, 3, 4, 4, 4, 4, 5, 8, 8, 8, 8, 8,
 8, 8, 8, 3, 4, 4, 4, 4, 4, 5, 8, 8, 8, 8, 8, 8, 8, 8, 3, 6, 0,
 0, 0, 0, 0, 1, 2, 2, 2, 2, 6, 0,
 0, 0, 0, 0, 0, 0, 0, 0, 1, 2, 2, 2, 2, 2, 2, 2, 3, 4, 4, 4, 4,
 5, 8, 8, 8, 8, 8, 8, 8, 6, 0,
 0, 0, 0, 0, 9, 9, 2, 2, 2, 2, 10, 0,
 0, 0, 0, 0, 1, 2, 2, 2, 2, 2, 2, 3, 4, 4, 4, 5, 8, 8, 8, 8, 8,
 8, 8, 8, 8, 8, 6, 0,
 9, 9, 2, 2, 2, 2, 10, 0,
 1, 2, 2, 2, 2, 2, 6, 0,
 0, 0, 0, 0, 1, 2, 2, 2, 2, 2, 2, 2, 2, 6, 0,
 0, 0, 0, 0, 0, 0, 0, 0, 1, 2, 2, 2, 3, 4, 4, 4, 4, 4, 5, 8, 8,
 8, 8, 8, 8, 8, 8, 8, 6, 0,
 0, 0, 0, 0, 0, 0, 0, 0, 1, 2, 2, 2, 3, 4, 4, 4, 4, 4, 5, 8, 8,
 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 3, 4, 4, 4, 4, 5, 8, 8,
 8, 6, 0,
 0, 0, 0, 0, 9, 9, 2, 2, 2, 2, 2, 2, 2, 2, 10, 0,
 9, 9, 2, 2, 2, 2, 2, 10, 0,
 1, 2, 2, 2, 2, 2, 2, 6, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
 1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 3, 4, 4, 5, 8, 8, 8, 8, 8, 8,
 8, 6, 0,
 9, 9, 2, 2, 2, 2, 2, 2, 10, 0,
 1, 2, 2, 2, 2, 2, 3, 4, 4, 4, 5, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8,
 6, 0,
 1, 2, 2, 2, 2, 2, 2, 3, 6, 0,
 1, 2, 2, 2, 2, 2, 3, 3, 6, 0,
 1, 2, 2, 2, 2, 2, 3, 3, 6, 0,
 1, 2, 2, 2, 2, 2, 2, 3, 6, 0,
 1, 2, 2, 2, 2, 2, 2, 3, 6, 0,
 1, 2, 2, 2, 2, 2, 3, 3, 6, 0];
    var text_01 = buf_01.join("\n");
    [scimoz, koDoc] = this._get_scimoz_and_koDoc_from_string(text_01, styles_01);
    var positions_and_expecteds = [
        [54, 4],
        [67, 4],
        [166, 4],
        [260, 4],
        [282, 4],
        [304, 4],
        [326, 4],
        [367, 0],
        [399, 0],
        [416, 0],
        [430, 0],
        [502, 0],
        [528, 4],
        [565, 0],
        [668, 4],
        [723, 5],
        [779, 8],
        [863, 8, 12],
        [903, 4, 8],
        [964, 8],
        [1009, 8],
        [1100, 0, 4],
        [1133, 0, 4],
        [1143, 0, 4],
        [1153, 0, 4],
        [1163, 0, 4],
        [1173, 0, 4],
        [1183, 0, 4],
        [1193, 0, 4]
    ]
    scimoz.currentPos = 63;
    scimoz.indent = 4;
    scimoz.tabWidth = 8;
    scimoz.useTabs = false;
    var part, expectedIndentHTML5, currentPos, expectedIndentHTML;
    var numTests = 0;
    for (var i = 0; i < positions_and_expecteds.length; i++) { 
        [currentPos, expectedIndentHTML5, expectedIndentHTML] = positions_and_expecteds[i];
        scimoz.currentPos = currentPos;
        var indent = html5LangSvc.computeIndent(scimoz, "XML", false);
        this.assertEquals(expectedIndentHTML5, indent.length,
                          ("Failed at iter " + i + ", pos: "
                           + currentPos
                           + ", expectedIndentHTML5: " + expectedIndentHTML5));
        this.assertEquals(rep(" ", expectedIndentHTML5), indent);
        
        indent = htmlLangSvc.computeIndent(scimoz, "XML", false);
        if (typeof(expectedIndentHTML) == "undefined") {
            expectedIndentHTML = expectedIndentHTML5;
        }
        this.assertEquals(expectedIndentHTML, indent.length,
                          ("Failed at iter " + i + ", pos: "
                           + currentPos
                           + ", expectedIndentHTML: " + expectedIndentHTML));
        this.assertEquals(rep(" ", expectedIndentHTML), indent);
        numTests += 2;
    }
    this.assertEquals(2 * positions_and_expecteds.length, numTests,
                      "Didn't execute all the expected tests")
};
const JS_TESTS = ["TestHTMLAutoIndentEmptyTag"];