/* Copyright (c) 2004-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

/* This is an internal test dialog with a SciMoz instance that can be
 * passed to various Komodo components that need an operable SciMoz to test.
 */

var log = ko.logging.getLogger("test_scimoz");
log.setLevel(ko.logging.LOG_DEBUG);

var widgets = null;
var view = null;


//---- interface routines for XUL

function OnLoad()
{
    log.debug("OnLoad()");
    try {
        scintillaOverlayOnLoad();

        widgets = new Object();
        widgets.testNames = document.getElementById("test-names");

        view = document.getElementById("view");
        view.init();
        view.initWithBuffer("if 1:\n    print 'hi'", "Python");
        view.scimoz.viewWS = 1;
        view.setFocus();
    } catch(ex) {
        log.exception(ex);
    }
}


function RunTest()
{
    log.debug("RunTest()");
    try {
        var testName = widgets.testNames.value;
        switch (testName) {
        case "koSciMozController":
            var sciCont = Components.classes["@ActiveState.com/scintilla/controller;1"].
                          getService(Components.interfaces.ISciMozController);
            sciCont.test_scimoz(view.scimoz);
            break;
        case "koSciUtils":
            var sciUtils = Components.classes["@activestate.com/koSciUtils;1"].
                           getService(Components.interfaces.koISciUtils);
            sciUtils.test_scimoz(view.scimoz);
            break;
        case "koPythonCodeIntelCompletionLanguageService":
            var cicLangSvc = Components.classes["@activestate.com/koPythonCodeIntelCompletionLanguageService;1"].
                             getService(Components.interfaces.koICodeIntelCompletionLanguageService);
            cicLangSvc.test_scimoz(view.scimoz);
            break;
        case "koPerlCodeIntelCompletionLanguageService":
            var cicLangSvc = Components.classes["@activestate.com/koPerlCodeIntelCompletionLanguageService;1"].
                             getService(Components.interfaces.koICodeIntelCompletionLanguageService);
            cicLangSvc.test_scimoz(view.scimoz);
            break;
        case "koRubyCodeIntelCompletionLanguageService":
            var cicLangSvc = Components.classes["@activestate.com/koRubyCodeIntelCompletionLanguageService;1"].
                             getService(Components.interfaces.koICodeIntelCompletionLanguageService);
            cicLangSvc.test_scimoz(view.scimoz);
            break;
        case "koPythonLanguage":
            var pyLang = Components.classes["@activestate.com/koLanguage?language=Python;1"].getService();
            pyLang.test_scimoz(view.scimoz);
            break;
        case "koCSSLanguage":
            var langObj = Components.classes["@activestate.com/koLanguage?language=CSS;1"].getService();
            langObj.test_scimoz(view.scimoz);
            break;
        default:
            log.error("unknown test name: '"+testName+"'\n");
        }
        view.setFocus();
    } catch(ex) {
        log.exception(ex);
    }
}
