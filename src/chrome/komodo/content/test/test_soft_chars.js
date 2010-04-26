var ko;
var tests = [];
var prefsSvc, koDirs, osSvc, fileSvc, globalPrefs, fileAssociations;
var numTests, numPassed, numFailed;
var testSkip = [];
var testOnly = [];//24, 25, 26, 27];
var origPrefs;

const DECORATOR_SOFT_CHAR = Components.interfaces.koILintResult.DECORATOR_SOFT_CHAR;

var lastTestEntry = {};
function TestEntry(obj) {
    for (var p in lastTestEntry) {
        this[p] = lastTestEntry[p];
        //dump("Copying property p:" + p + " => " + this[p] + "\n");
    }
    for (var p in obj) {
        this[p] = obj[p];
    }
    lastTestEntry = this;
}

function fillTests()  {
    tests = [];
    // 0
    tests.push(new TestEntry({
        suffix: ".py",
                string: "print ",
                posn: 0,
                _char: "'",
                exp: "'",
                __none__: null
                    }));
    tests.push(new TestEntry({
                _char: '"',
                exp: '"'
                    }));
    tests.push(new TestEntry({
                _char: '(',
                exp: ')'
                    }));
    tests.push(new TestEntry({
                _char: '[',
                exp: ']'
                    }));
    tests.push(new TestEntry({
                _char: '{',
                exp: '}'
                    }));
    // 5
    tests.push(new TestEntry({
                _char: ']',
                exp: ''
                    }));
    tests.push(new TestEntry({_char: 'x'}));
    tests.push(new TestEntry({_char: '<'}));
    tests.push(new TestEntry({_char: '>'}));
    tests.push(new TestEntry({
        suffix: ".py",
                string: "items = 3",
                posn: -4,
                _char: "[",
                exp: null,
                __none__: null
                    }));
    // 10
    tests.push(new TestEntry({
        suffix: ".php",
                string: "<?php\n$abc",
                posn: 0,
                _char: "[",
                exp: "]",
                __none__: null
                    }));
    tests.push(new TestEntry({
                string: "<?php\nprint ",
                _char: "'",
                exp: "'",
                __none__: null
                    }));
    tests.push(new TestEntry({
                _char: '"',
                exp: '"'
                    }));
    tests.push(new TestEntry({
                _char: '(',
                exp: ')'
                    }));
    tests.push(new TestEntry({
                _char: '[',
                exp: ']'
                    }));
    // 15
    tests.push(new TestEntry({
                _char: '{',
                exp: '}'
                    }));
    tests.push(new TestEntry({
                _char: ']',
                exp: null
                    }));
    tests.push(new TestEntry({
                string: "<?php\n$abc = 3;",
                posn: -5,
                _char: "[",
                exp: "]",
                inner: 1
                    }));
    tests.push(new TestEntry({
                exp: null,
                inner: null
                    }));
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
            editSmartSoftCharacters :
                globalPrefs.getBooleanPref('editSmartSoftCharacters'),
            enableSmartSoftCharactersInsideLine:
                globalPrefs.getBooleanPref('enableSmartSoftCharactersInsideLine')
        }
    }
    globalPrefs.setBooleanPref('editSmartSoftCharacters', true);
    globalPrefs.setBooleanPref('enableSmartSoftCharactersInsideLine', false);
}

function restorePrefs() {
    var globalOrigPrefs = origPrefs.global;
    globalPrefs.setBooleanPref('editSmartSoftCharacters', globalOrigPrefs.editSmartSoftCharacters);
}

function RunTest() {
    numPassed = numFailed = 0;
    setTimeout(ContinueTop, 0, tests, 0, tests.length);
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
    if (test.inner) {
        globalPrefs.setBooleanPref('enableSmartSoftCharactersInsideLine', true);
    }
    var file = fileSvc.makeTempFile(test.suffix, 'w');
    //dump("Load file " + file.URI + "\n");
    file.puts(test.string);
    file.close();
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
    view.scintilla.focus();
    scimoz.documentEnd();
    if (test.posn < 0) {
        for (var j = test.posn; j < 0; j++) {
            scimoz.charLeft();
        }
    }
    scimoz.insertText(scimoz.currentPos, test._char);
    scimoz.charRight();
    setTimeout(function() {
            if (view.languageObj &&
                view.prefs.getBooleanPref("editElectricBrace")) {
                // "keyPressed" is the poorly named mechanism to initiate
                // auto-indenting functionality.
                //dump("About to do keyPressed\n");
                view.languageObj.keyPressed(test._char, scimoz);
            } else {
                if (!view.languageObj) {
                    dump("**************** No lang obj\n");
                } else {
                    dump("**************** elecBrace Pref : " +
                         view.prefs.getBooleanPref("editElectricBrace")
                         + "\n");
                }
            }
            view.koDoc.isDirty = false;
            setTimeout(ContinuePart3, 100, tests, i, lim, test, view, file);
        }, 300);
}

function ContinuePart3(tests, i, lim, test, view, file) {
    var scimoz = view.scimoz;
    // view.scintilla.focus();
    var currentPos = scimoz.currentPos;
    var ch;
    var lines = [];
    if (test.exp) {
        ch = scimoz.getWCharAt(currentPos);
        if (ch == test.exp) {
            if (scimoz.indicatorValueAt(DECORATOR_SOFT_CHAR, currentPos)) {
            } else {
                lines.push("No indicator at posn " + currentPos);
            }
        } else {
            lines.push("Expected char " + test.exp
                       + ", got char " + ch);
        }
    } else if (currentPos == scimoz.positionBefore(scimoz.textLength)) {
    } else if (!scimoz.indicatorValueAt(DECORATOR_SOFT_CHAR, currentPos)) {
        // Make sure the current char isn't indicated
    } else {
        lines.push("Found char:"
                   + scimoz.getWCharAt(currentPos)
                   + " at pos:" + currentPos
                   + ", indicator: "
                   + scimoz.indicatorValueAt(DECORATOR_SOFT_CHAR, currentPos));
    }
    if (lines.length) {
        scimoz.insertText(scimoz.textLength, "\n\n" + lines.join("\n"));
        numFailed += 1;
    } else {
        numPassed += 1;
        view.closeUnconditionally();
    }
    if (test.inner) {
        // set the pref back to the default.
        globalPrefs.setBooleanPref('enableSmartSoftCharactersInsideLine', false);
    }
    setTimeout(ContinueTop, 100, tests, i + 1, lim);
}
        
