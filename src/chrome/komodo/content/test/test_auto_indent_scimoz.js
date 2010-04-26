
const NO_TABS = 0x00;
const USE_FILE = 0x01;
const USE_TABS = 0x02;

var currentWidth = 4;

function TestEntry(suffix, text, prefs, exp) {
    this.suffix = suffix;
    this.text = text;
    this.prefs = prefs;
    this.exp = exp;
    this.width = currentWidth;
}

TestEntry.prototype.clone = function(args) {
    var copy = new TestEntry(this.suffix,
                             this.text,
                             this.prefs,
                             this.exp);
    for (var p in args) {
        copy[p] = args[p];
    }
    return copy;
};

var ko;
var tests = [];
var prefsSvc, koDirs, osSvc, fileSvc, globalPrefs, fileAssociations;
var numTests, numPassed, numFailed;
var testSkip = [];
var testOnly = [];//24, 25, 26, 27];
var origPrefs;

function fillTests()  {
    // short lines 0
    tests = [];
    var t = new TestEntry(".py", "if 1:\n{4}if 2:", NO_TABS, "{8}");
    tests.push(t);
    tests.push(t.clone({prefs:USE_FILE}));
    tests.push(t.clone({prefs:USE_TABS, exp:"\t"}));
    tests.push(t.clone({prefs:USE_TABS|USE_FILE, exp:"\t"}));
    // long lines, no tabs 4 
    t = new TestEntry(".py", "if 1:\n{4}if 2:\n{8}if 3:", NO_TABS, "{12}");
    tests.push(t);
    tests.push(t.clone({prefs:USE_FILE}));
    tests.push(t.clone({prefs:USE_TABS, exp:"\t{4}"}));
    tests.push(t.clone({prefs:USE_TABS|USE_FILE}));
    // long lines, tabs 8
    t = new TestEntry(".py", "if 1:\n{4}if 2:\n\tif 3:", NO_TABS, "{12}");
    tests.push(t);
    var t2 = t.clone({prefs:USE_FILE, exp:"\t{4}"})
    tests.push(t2);
    tests.push(t2.clone({prefs:USE_TABS}));
    tests.push(t2.clone({prefs:USE_TABS|USE_FILE}));
    
    // Ruby - short lines 12
    currentWidth = 2;
    t = new TestEntry(".rb", "if 1\n{2}if 2\n{4}if 3\n{6}if 4", NO_TABS, "{8}");
    tests.push(t);
    tests.push(t.clone({prefs:USE_FILE}));
    tests.push(t.clone({prefs:USE_TABS, exp:"\t"}));
    tests.push(t.clone({prefs:USE_TABS|USE_FILE, exp:"\t"}));
    // Ruby - long lines, no tabs 16
    t = new TestEntry(".rb", "if 1\n{2}if 2\n{4}if 3\n{6}if 4\n{8}if 5", NO_TABS, "{10}");
    tests.push(t);
    tests.push(t.clone({prefs:USE_FILE}));
    tests.push(t.clone({prefs:USE_TABS, exp:"\t{2}"}));
    tests.push(t.clone({prefs:USE_TABS|USE_FILE})); // wrong
    // Ruby - long lines, with tabs 20
    t = new TestEntry(".rb", "if 1\n{2}if 2\n{4}if 3\n{6}if 4\n\tif 5", NO_TABS, "{10}");
    tests.push(t);
    t2 = t.clone({prefs:USE_FILE, exp:"\t{2}"})
    tests.push(t2);
    tests.push(t2.clone({prefs:USE_TABS}));
    tests.push(t2.clone({prefs:USE_TABS|USE_FILE}));
    
    // HTML - short lines 24
    t = new TestEntry(".html", "<div>\n{2}<div>\n{4}<div>\n{6}<div>", NO_TABS, "{8}");
    tests.push(t);
    tests.push(t.clone({prefs:USE_FILE}));
    tests.push(t.clone({prefs:USE_TABS, exp:"\t"}));
    tests.push(t.clone({prefs:USE_TABS|USE_FILE, exp:"\t"}));
    
    // HTML - long lines, no tabs 28
    t = new TestEntry(".html", "<div>\n{2}<div>\n{4}<div>\n{6}<div>\n{8}<div>", NO_TABS, "{10}");
    tests.push(t);
    tests.push(t.clone({prefs:USE_FILE}));
    tests.push(t.clone({prefs:USE_TABS, exp:"\t{2}"}));
    tests.push(t.clone({prefs:USE_TABS|USE_FILE})); // auto-indent fails.
    
    // HTML - long lines, with tabs 32
    t = new TestEntry(".html", "<div>\n{2}<div>\n{4}<div>\n{6}<div>\n\t<div>", NO_TABS, "{10}");
    tests.push(t);
    t2 = t.clone({prefs:USE_FILE, exp:"\t{2}"})
    tests.push(t2);
    tests.push(t2.clone({prefs:USE_TABS}));
    tests.push(t2.clone({prefs:USE_TABS|USE_FILE}));
    
    // Text - short lines 36
    // Keep in mind that text files never increase indenting, so the tests are more trivial
    t = new TestEntry(".txt", "line 1\n{4}line 2", NO_TABS, "{4}");
    tests.push(t);
    tests.push(t.clone({prefs:USE_FILE}));
    tests.push(t.clone({prefs:USE_TABS}));
    tests.push(t.clone({prefs:USE_TABS|USE_FILE}));
    
    // Text - long lines, no tabs 40
    t = new TestEntry(".txt", "line 1\n{4}line 2\n{8}line 3", NO_TABS, "{8}");
    tests.push(t);
    tests.push(t.clone({prefs:USE_FILE}));
    tests.push(t.clone({prefs:USE_TABS, exp:"\t"}));
    tests.push(t.clone({prefs:USE_TABS|USE_FILE})); // auto-indent fails.
    
    // Text - long lines, with tabs 44
    t = new TestEntry(".txt", "line 1\n{4}line 2\n\tline 3", NO_TABS, "{8}");
    tests.push(t);
    t2 = t.clone({prefs:USE_FILE, exp:"\t"})
    tests.push(t2);
    tests.push(t2.clone({prefs:USE_TABS}));
    tests.push(t2.clone({prefs:USE_TABS|USE_FILE}));
    
    // XUL - short lines 48
    currentWidth = 1;
    var prefix = ("<div>\n{1}<div>\n{2}<div>\n{3}<div>\n"
                  + "{4}<div>\n{5}<div>\n{6}<div>\n{7}<div>");
    t = new TestEntry(".xul", prefix, NO_TABS, "{8}");
    tests.push(t);
    tests.push(t.clone({prefs:USE_FILE}));
    tests.push(t.clone({prefs:USE_TABS, exp:"\t"}));
    tests.push(t.clone({prefs:USE_TABS|USE_FILE, exp:"\t"}));
    
    // XUL - long lines, no tabs 52
    t = new TestEntry(".xul", prefix + "\n{8}<div>", NO_TABS, "{9}");
    tests.push(t);
    tests.push(t.clone({prefs:USE_FILE}));
    tests.push(t.clone({prefs:USE_TABS, exp:"\t{1}"}));
    tests.push(t.clone({prefs:USE_TABS|USE_FILE})); // auto-indent fails.
    
    // XUL - long lines, with tabs 56
    t = new TestEntry(".xul", prefix + "\n\t<div>", NO_TABS, "{9}");
    tests.push(t);
    t2 = t.clone({prefs:USE_FILE, exp:"\t{1}"})
    tests.push(t2);
    tests.push(t2.clone({prefs:USE_TABS}));
    tests.push(t2.clone({prefs:USE_TABS|USE_FILE}));

}

function OnLoad() {
    fillTests();
    ko = window.arguments[0];
    prefsSvc = Components.classes["@activestate.com/koPrefService;1"].
        getService(Components.interfaces.koIPrefService);
    koDirs = Components.classes["@activestate.com/koDirs;1"].getService(Components.interfaces.koIDirs);
    osSvc = Components.classes["@activestate.com/koOs;1"].getService(Components.interfaces.koIOs);
    fileSvc = Components.classes["@activestate.com/koFileService;1"].getService(Components.interfaces.koIFileService);
    globalPrefs = Components.classes["@activestate.com/koPrefService;1"].getService(Components.interfaces.koIPrefService).prefs;
    var langRegistry = Components.classes["@activestate.com/koLanguageRegistryService;1"].getService(Components.interfaces.koILanguageRegistryService);
    var patternsObj = {};
    var langNamesObj = {};
    var lengthObj = {};
    langRegistry.getFileAssociations(lengthObj, patternsObj, {}, langNamesObj);
    fileAssociations = {};
    patternsObj = patternsObj.value;
    langNamesObj = langNamesObj.value;
    var lim = lengthObj.value;
    for (var i = 0; i < lim; i++) {
        fileAssociations[patternsObj[i].substr(1)] = langNamesObj[i];
    }
    savePrefs();
}

function savePrefs() {
    origPrefs = {
        global : {
            useSmartTabs : globalPrefs.getBooleanPref('useSmartTabs'),
            useTabs: globalPrefs.getBooleanPref('useTabs'),
            indentWidth: globalPrefs.getLongPref('indentWidth'),
            tabWidth: globalPrefs.getLongPref('tabWidth')
        }
    }
    globalPrefs.setBooleanPref('useSmartTabs', true);
    globalPrefs.setBooleanPref('useTabs', false);
    globalPrefs.setLongPref('indentWidth', 4);
    globalPrefs.setLongPref('tabWidth', 8);
    for (var test, i = 0; test = tests[i]; ++i) {
        var lang = test.suffix;
        if (!(lang in origPrefs)) {
            origPrefs[lang] = {};
            var langPrefs = getLanguagePrefs(lang);
            if (langPrefs.hasPrefHere('useTabs')) {
                origPrefs[lang].useTabs = langPrefs.getBooleanPref('useTabs');
                langPrefs.setBooleanPref('useTabs', false);
            }
            if (langPrefs.hasPrefHere('indentWidth')) {
                origPrefs[lang].indentWidth = langPrefs.getLongPref('indentWidth');
                langPrefs.setLongPref('indentWidth', 4);
            }
            if (langPrefs.hasPrefHere('tabWidth')) {
                origPrefs[lang].indentWidth = langPrefs.getLongPref('tabWidth');
                langPrefs.setLongPref('tabWidth', 8);
            }
        }
    }
}

function restorePrefs() {
    var globalOrigPrefs = origPrefs.global;
    globalPrefs.setBooleanPref('useSmartTabs', globalOrigPrefs.useSmartTabs);
    globalPrefs.setBooleanPref('useTabs', globalOrigPrefs.useTabs);
    globalPrefs.setLongPref('indentWidth', globalOrigPrefs.indentWidth);
    globalPrefs.setLongPref('tabWidth', globalOrigPrefs.tabWidth);
    for (lang in origPrefs) {
        if (lang == "global") {
            continue;
        }
        var langOrigPrefs = origPrefs[lang];
        var langPrefs = getLanguagePrefs(lang);
        if ('useTabs' in langOrigPrefs) {
            langPrefs.setBooleanPref('useTabs', langOrigPrefs.useTabs);
        }
        if ('indentWidth' in langOrigPrefs) {
            langPrefs.setLongPref('indentWidth', langOrigPrefs.indentWidth);
        }
        if ('tabWidth' in langOrigPrefs) {
            langPrefs.setLongPref('tabWidth', langOrigPrefs.tabWidth);
        }
    }    
}


function expandSpaces(s) {
    var out = [];
    var i = 0;
    var re = /^\{(\d+)\}/;
    var m, parts = s.split(/(\{\d+\})/);
    var len = parts.length;
    for (i = 0; i < len; ++i) {
        var part = parts[i];
        m = re.exec(part);
        if (!m) {
            out.push(part);
            continue;
        }
        var spaces = "";
        for (var j = parseInt(m[1]); j > 0; j--) {
            spaces += ' ';
        }
        out.push(spaces);
    }
    return out.join("");
}


function RunTest() {
    numPassed = numFailed = 0;
    setTimeout(ContinueTop, 0, tests, 0, tests.length);
}

function getLanguagePrefs(suffix) {
    var langPrefs = globalPrefs.getPref('languages');
    if (!(suffix in fileAssociations)) {
        dump("Don't recognize suffix " + suffix + "\n");
    } else {
        var languageName = fileAssociations[suffix];
        var languagePrefName = "languages/" + languageName;
        if (langPrefs.hasPrefHere(languagePrefName)) {
            return langPrefs.getPref(languagePrefName);
        }
    }
    return globalPrefs;
}

function ContinueTop(tests, i, lim) {
    if (i >= lim) {
        dump("\n" + numPassed + " passed, "
             + numFailed + " failed / "
             + lim + " tests\n"
             );
        restorePrefs();
        return;
    }
    else if (testOnly && testOnly.length && testOnly.indexOf(i) == -1) {
        // dump("Skip unwanted test " + i + "\n");
        ContinueTop(tests, i + 1, lim);
        return;
    }
    else if (testSkip && testSkip.length && testSkip.indexOf(i) != -1) {
        // dump("Skip filtered test " + i + "\n");
        ContinueTop(tests, i + 1, lim);
        return;
    }
    var test = tests[i];
    var file = fileSvc.makeTempFile(test.suffix, 'w');
    dump("Load file " + file.URI + "\n");
    file.puts(expandSpaces(test.text));
    file.close();
    var prefs = getLanguagePrefs(test.suffix);
    // Set the prefs for this test.
    globalPrefs.setBooleanPref('useSmartTabs', !!(test.prefs & USE_FILE));
    prefs.setBooleanPref('useTabs', !!(test.prefs & USE_TABS));
    var iwPrefs = prefs.hasPref('indentWidth') ? prefs : globalPrefs;
    if (test.width != iwPrefs.getLongPref('indentWidth')) {
        iwPrefs.setLongPref('indentWidth', test.width);
    }
    ko.views.manager.newViewFromURIAsync(
        file.URI,
        'editor',
        null,
        -1,
        function(view) {
            view.scimoz.viewWS = 1;
            view.setFocus();
            view.scimoz.documentEnd();
            setTimeout(ContinuePart2, 100, tests, i, lim, test, view, file);
        });
}

function ContinuePart2(tests, i, lim, test, view, file) {
    var scimoz = view.scimoz;
    var lastLineBefore = view.scimoz.lineFromPosition(view.scimoz.currentPos);
    view.scintilla.focus();
    ko.commands.doCommand('cmd_newline');
    // view.doCommand('cmd_newline');
    var lastLineAfter = view.scimoz.lineFromPosition(view.scimoz.currentPos);
    var lastLineStartPos = view.scimoz.positionFromLine(lastLineAfter);
    var lastLineEndPos = view.scimoz.getLineEndPosition(lastLineAfter);
    var newText = view.scimoz.getTextRange(lastLineStartPos, lastLineEndPos);
    var exp = expandSpaces(test.exp);
    if (newText != exp) {
        var s = ("Test "
                 + i
                 + ", file "
                 + file.URI
                 + "::\n"
                 + "failed: expected ["
                 + exp
                 + "], got ["
                 + newText
                 + "]\n"
                 + "use-file="
                 + (!!(test.prefs & USE_FILE )).toString()
                 + ", use-tabs="
                 + (!!(test.prefs & USE_TABS )).toString()
                 + "]\n");
        dump(s + "\n");
        ko.commands.doCommand('cmd_newline');
        scimoz.anchor = scimoz.currentPos;
        scimoz.home();
        scimoz.replaceSel("");
        ko.commands.doCommand('cmd_newline');
        view.scimoz.insertText(view.scimoz.currentPos, s);
        view.koDoc.isDirty = false;
        numFailed += 1;
    } else {
        numPassed += 1;
        view.closeUnconditionally();
        fileSvc.deleteTempFile(file.displayPath, true);
    }
    setTimeout(ContinueTop, 100, tests, i + 1, lim);
}
