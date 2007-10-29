/* ***** BEGIN LICENSE BLOCK *****
 * Version: MPL 1.1/GPL 2.0/LGPL 2.1
 * 
 * The contents of this file are subject to the Mozilla Public License
 * Version 1.1 (the "License"); you may not use this file except in
 * compliance with the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 * 
 * Software distributed under the License is distributed on an "AS IS"
 * basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
 * License for the specific language governing rights and limitations
 * under the License.
 * 
 * The Original Code is Komodo code.
 * 
 * The Initial Developer of the Original Code is ActiveState Software Inc.
 * Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
 * ActiveState Software Inc. All Rights Reserved.
 * 
 * Contributor(s):
 *   ActiveState Software Inc
 * 
 * Alternatively, the contents of this file may be used under the terms of
 * either the GNU General Public License Version 2 or later (the "GPL"), or
 * the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
 * in which case the provisions of the GPL or the LGPL are applicable instead
 * of those above. If you wish to allow use of your version of this file only
 * under the terms of either the GPL or the LGPL, and not to allow others to
 * use your version of this file under the terms of the MPL, indicate your
 * decision by deleting the provisions above and replace them with the notice
 * and other provisions required by the GPL or the LGPL. If you do not delete
 * the provisions above, a recipient may use your version of this file under
 * the terms of any one of the MPL, the GPL or the LGPL.
 * 
 * ***** END LICENSE BLOCK ***** */

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
