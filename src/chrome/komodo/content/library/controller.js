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

/* -*- Mode: JavaScript; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 2 -*- */

xtk.include("controller");

(function() {

var handlers = {
    'cmd_helpAbout': 'ko.launch.about()',
    'cmd_viewBottomPane': function() ko.uilayout.togglePane("workspace_bottom_area"),
    'cmd_viewLeftPane': function() ko.uilayout.togglePane("workspace_left_area"),
    'cmd_viewRightPane': function() ko.uilayout.togglePane("workspace_right_area"),
    'cmd_viewToolbox': function() ko.uilayout.toggleTab("toolbox2viewbox"),
    'cmd_focusProjectPane': function() ko.uilayout.focusPane("workspace_left_area"),
    'cmd_focusToolboxPane': function() ko.uilayout.focusPane("workspace_right_area"),
    'cmd_focusBottomPane': function() ko.uilayout.focusPane("workspace_bottom_area"),
    'cmd_focusEditor': function() { var view = ko.views.manager.currentView;
                                    if (view) view.setFocus(); },
    'cmd_focusSource': function() { var view = ko.views.manager.currentView;
                                    if (view) view.viewSource(); },
    'cmd_toggleMenubar': 'ko.uilayout.toggleMenubar()',
    'cmd_toggleToolbars': 'ko.uilayout.toggleToolbars()',
    'cmd_toggleButtonText': 'ko.uilayout.toggleButtons()',
    'cmd_viewedittoolbar': 'ko.uilayout.toggleToolbarVisibility(\'standardToolbar\')',
    'cmd_viewtoolstoolbar': 'ko.uilayout.toggleToolbarVisibility(\'toolsToolbar\')',
    'cmd_viewmacrotoolbar': 'ko.uilayout.toggleToolbarVisibility(\'macrosToolbar\')',
    'cmd_viewkomodotoolbar': 'ko.uilayout.toggleToolbarVisibility(\'komodoToolbar\')',
    'cmd_viewworkspacetoolbar': 'ko.uilayout.toggleToolbarVisibility(\'workspaceToolbar\')',
    'cmd_viewdebugtoolbar': 'ko.uilayout.toggleToolbarVisibility(\'debuggerToolbar\')',
    'cmd_viewfindtoolbar': 'ko.uilayout.toggleToolbarVisibility(\'findToolbar\')',
    'cmd_viewFullScreen': 'ko.uilayout.fullScreen()',
    'cmd_editPrefs': 'prefs_doGlobalPrefs(null)',
    'cmd_helpHelp': 'ko.help.open()',
    'cmd_helpShowKeybindings': 'ko.browse.showKeybindings()',
    'cmd_helpPerlRef_Local': 'ko.browse.localHelp("Perl")',
    'cmd_helpPerlRef_Web': 'ko.browse.webHelp("Perl")',
    'cmd_helpPerlMailingLists': 'ko.browse.aspnMailingList("Perl")',
    'cmd_helpPythonRef_Local': 'ko.browse.localHelp("Python")',
    'cmd_helpPythonRef_Web': 'ko.browse.webHelp("Python")',
    'cmd_helpPythonMailingLists': 'ko.browse.aspnMailingList("Python")',
    'cmd_helpPython3Ref_Local': 'ko.browse.localHelp("Python3")',
    'cmd_helpPython3Ref_Web': 'ko.browse.webHelp("Python3")',
    // No mailing lists for python3
    'cmd_helpPHPRef_Web': 'ko.browse.webHelp("PHP")',
    'cmd_helpPHPMailingLists': 'ko.browse.aspnMailingList("PHP")',
    'cmd_helpRubyRef_Web': 'ko.browse.webHelp("Ruby")',
    'cmd_helpRubyMailingLists': 'ko.browse.aspnMailingList("Ruby")',
    'cmd_helpTclRef_Local': 'ko.browse.localHelp("Tcl")',
    'cmd_helpTclRef_Web': 'ko.browse.webHelp("Tcl")',
    'cmd_helpTclMailingLists': 'ko.browse.aspnMailingList("Tcl")',
    'cmd_helpXSLTMailingLists': 'ko.browse.openUrlInDefaultBrowser("http://www.biglist.com/lists/xsl-list/archives/")',
    'cmd_helpXSLTRef_Web': 'ko.browse.openUrlInDefaultBrowser("http://developer.mozilla.org/en/docs/XSLT")',
    'cmd_helpKomodoMailLists': 'ko.browse.browseTag("mailLists")',
    'cmd_helpCommunity': 'ko.browse.browseTag("community")',
    'cmd_helpViewBugs': 'ko.browse.browseTag("bugs")',
    'cmd_helpContactUs': 'ko.browse.browseTag("contactus")',
    'cmd_helpLanguage': 'ko.help.language()',
    'cmd_helpLanguageAlternate': 'ko.help.alternate()',
    'cmd_helpViewErrorLog': 'ko.help.viewErrorLog()',
    'cmd_komodoMemoryUsage': 'ko.help.memoryUsage()',
    'cmd_toolsWatchFile': 'ko.launch.watchLocalFile()',
    'cmd_toolsRunCommand': 'ko.launch.runCommand()',
    'cmd_newWindow': 'ko.launch.newWindow()',
    'cmd_nextWindow': 'ko.windowManager.focusNextWindow()',
    'cmd_previousWindow': 'ko.windowManager.focusPreviousWindow()',
    'cmd_open': 'ko.open.filePicker()',
    'cmd_open_remote': 'ko.filepicker.openRemoteFiles()',
    'cmd_openTemplate': 'ko.open.templatePicker()',
    'cmd_new': 'ko.views.manager.doNewViewAsync()',
    'cmd_newTab': 'ko.open.quickStart()',
    'cmd_newTemplate': 'ko.views.manager.newTemplateAsync()',
    'cmd_quit': 'ko.main.quitApplication()',
    'cmd_findInFiles': 'ko.launch.findInFiles()',
    'cmd_replaceInFiles': 'ko.launch.replaceInFiles()',
    'cmd_nextLintResult': 'ko.lint.jumpToNextLintResult()',
    'cmd_lintClearResults': 'ko.lint.clearResults()',
    'cmd_lintNow': 'ko.lint.doRequest(true)'
}

// The following controller is for any <command> or <broadcaster>
// that doesn't fit into any other controller.  It is generally
// used for commands that don't ever get disabled.

function broadcasterController() {
    if (typeof(ko.main) != "undefined") {
        ko.main.addWillCloseHandler(this.destructor, this);
    } else {
        // ko.main will not be defined in dialogs that load controller.js.
        var self = this;
        window.addEventListener("unload", function() { self.destructor(); }, false);
    }
}

// The following two lines ensure proper inheritance (see Flanagan, p. 144).
broadcasterController.prototype = new xtk.Controller();
broadcasterController.prototype.constructor = broadcasterController;

broadcasterController.prototype.destructor = function() {
    window.controllers.removeController(this);
}

broadcasterController.prototype.isCommandEnabled = function(cmdName) {
    if (cmdName in handlers) {
        return true;
    };
    return false;
}

broadcasterController.prototype.supportsCommand = broadcasterController.prototype.isCommandEnabled;

broadcasterController.prototype.doCommand = function(cmdName) {
    if (cmdName in handlers) {
        if (handlers[cmdName] instanceof Function) {
            return handlers[cmdName]();
        } else {
            return eval(handlers[cmdName]);
        }
    };
    return false;
}

window.controllers.appendController(new broadcasterController());


}).apply();
