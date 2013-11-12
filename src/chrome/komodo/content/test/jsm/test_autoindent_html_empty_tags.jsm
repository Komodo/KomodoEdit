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

TestHTMLAutoIndentEmptyTag.prototype._get_scimoz_and_koDoc_from_string = function(buf) {
    var view = new ko.views.ViewMock({text:buf});
    var scimoz = view.scimoz;
    //this.log.debug("We have a headless scimoz");
    // Set up the real HTML lexer (for styling information)
    var lexerSvc = Cc["@activestate.com/koLanguageRegistryService;1"]
                     .getService(Ci.koILanguageRegistryService)
                     .getLanguage("HTML5")
                     .getLanguageService(Ci.koILexerLanguageService);
    lexerSvc.setCurrent(scimoz);
    scimoz.colourise(0, -1);
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
    // Use {n} to specify where we should test, where |n| is the expected indent
    // Or use {n,m} for HTML5 / HTML4 repectively, if they should be different
    var buf_01 = [ '<!DOCTYPE HTML>'
                 ,'<head>'
                 ,'    <link id="css-3990894201" >{4}'
                 ,'    <script>{4}alert("howdy")</script>'
                 ,'    <title>title here</title>'
                 ,'    <meta name="description" content="stuff">{4}'
                 ,'    <link rel="search" type="application/opensearchdescription+xml" >'
                 ,'    <base href="flips">{4}'
                 ,'    <link rel="icon">{4}<link rel="alternate">{4}<link rel="alternate">{4}'
                 ,'</head>'
                 ,'<body>'
                 ,'<p>para here: br here<br>{0}'
                 ,'picture here: <img src="blip1">{0}<img src="blip2">{0}'
                 ,'hr here: <hr>{0}'
                 ,'Now for an object:'
                 ,'<object class="wallop">'
                 ,'<param name="n1" value="v2">{0}'
                 ,'</object>'
                 ,'<map id="map1">{4}'
                 ,'<area alt="area51" ping="wired.com">{0}'
                 ,'</map>'
                 ,'<form action="getform.php" method="get">'
                 ,'    First name: <input type="text" name="first_name" >{4}'
                 ,'     Last name: <input type="text" name="last_name"  >{5}'
                 ,'        E-mail: <input type="email" name="user_email" >{8}'
                 ,'    <input type="submit" value="Submit" >'
                 ,'    <menu>'
                 ,'        <command type="radio">{8,12}'
                 ,'    </menu>'
                 ,'    <output for="whatever">{4,8}'
                 ,'</form>'
                 ,'<table>'
                 ,'    <colgroup>'
                 ,'        <col class="column1">{8}'
                 ,'        <col class="columns2plus3" span="2">{8}'
                 ,'    </colgroup>'
                 ,'</table>'
                 ,'<figure>here\'s a figure, with an caption:'
                 ,'<figcaption id="figc2">{0,4}'
                 ,'</figure>'
                 ,'<audio src="whatever">{0,4}'
                 ,'<source >{0,4}'
                 ,'<video  >{0,4}'
                 ,'<embed  >{0,4}'
                 ,'<canvas >{0,4}'
                 ,'<keygen >{0,4}'
                 ,'<meter  >{0,4}'
                 ,''
                ];
    var text_01 = buf_01.join("\n");
    var positions_and_expecteds = [];
    var count = 0;
    text_01 = text_01.replace(/\{([^\}]+)\}/g, (match, v, offset) => {
        let args = [offset - count].concat(v.split(",").map(n => parseInt(n)));
        positions_and_expecteds.push(args);
        count += match.length;
        return "";
        });

    [scimoz, koDoc] = this._get_scimoz_and_koDoc_from_string(text_01);
    scimoz.currentPos = 63;
    scimoz.indent = 4;
    scimoz.tabWidth = 8;
    scimoz.useTabs = false;
    var part;
    var numTests = 0;
    for (var i = 0; i < positions_and_expecteds.length; i++) { 
        let [currentPos, expectedIndentHTML5, expectedIndentHTML] =
            positions_and_expecteds[i];
        scimoz.currentPos = currentPos;
        var indent = html5LangSvc.computeIndent(scimoz, "XML", false);
        let contextBefore = scimoz.getTextRange(currentPos - 10, currentPos)
                                  .replace(/\n/g, "\\n");
        let contextAfter = scimoz.getTextRange(currentPos, currentPos + 10)
                                 .replace(/\n/g, "\\n");
        this.assertEquals(expectedIndentHTML5, indent.length,
                          ("Failed at iter {i}, pos {currentPos}: " +
                           "expected HTML5 indent {expectedIndentHTML5}, got " +
                           "{indent.length} near [{contextBefore}|{contextAfter}]")
                           .replace(/\{(.*?)\}/g, (m, v) => eval(v)));
        this.assertEquals(rep(" ", expectedIndentHTML5), indent);
        
        indent = htmlLangSvc.computeIndent(scimoz, "XML", false);
        if (typeof(expectedIndentHTML) == "undefined") {
            expectedIndentHTML = expectedIndentHTML5;
        }
        this.assertEquals(expectedIndentHTML, indent.length,
                          ("Failed at iter {i}, pos {currentPos}: " +
                           "expected HTML indent {expectedIndentHTML}, got " +
                           "{indent.length}")
                           .replace(/\{(.*?)\}/g, (m, v) => eval(v)));
        this.assertEquals(rep(" ", expectedIndentHTML), indent);
        numTests += 2;
    }
    this.assertEquals(2 * positions_and_expecteds.length, numTests,
                      "Didn't execute all the expected tests")
};
const JS_TESTS = ["TestHTMLAutoIndentEmptyTag"];