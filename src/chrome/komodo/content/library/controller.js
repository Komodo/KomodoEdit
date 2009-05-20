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

// backwards compatibility APIs
xtk.include("controller");
var Controller = xtk.Controller;



(function() {

var handlers = {
    'cmd_helpAbout': 'ko.browse.about()',
    'cmd_viewBottomPane': 'ko.uilayout.togglePane(\'bottom_splitter\', \'output_tabs\', \'cmd_viewBottomPane\');',
    'cmd_viewLeftPane': 'ko.uilayout.togglePane(\'workspace_left_splitter\', \'project_toolbox_tabs\', \'cmd_viewLeftPane\');',
    'cmd_viewRightPane': 'ko.uilayout.togglePane(\'workspace_right_splitter\', \'right_toolbox_tabs\', \'cmd_viewRightPane\');',
    'cmd_viewProjects': 'ko.uilayout.toggleTab(\'project_tab\')',
    'cmd_viewToolbox': 'ko.uilayout.toggleTab(\'toolbox_tab\')',
    'cmd_focusProjectPane': 'ko.uilayout.focusPane(\'project_toolbox_tabs\')',
    'cmd_focusToolboxPane': 'ko.uilayout.focusPane(\'right_toolbox_tabs\')',
    'cmd_focusBottomPane': 'ko.uilayout.focusPane(\'output_tabs\')',
    'cmd_focusEditor': 'ko.views.manager.currentView.setFocus()',
    'cmd_focusSource': 'ko.views.manager.currentView.viewSource()',
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
    'cmd_openStartPage': 'ko.open.startPage()',
    'cmd_helpHelp': 'ko.help.open()',
    'cmd_helpShowKeybindings': 'ko.browse.showKeybindings()',
    'cmd_helpPerlRef_Local': 'ko.browse.localHelp("Perl")',
    'cmd_helpPerlRef_Web': 'ko.browse.webHelp("Perl")',
    'cmd_helpPerlMailingLists': 'ko.browse.aspnMailingList("Perl")',
    'cmd_helpPythonRef_Local': 'ko.browse.localHelp("Python")',
    'cmd_helpPythonRef_Web': 'ko.browse.webHelp("Python")',
    'cmd_helpPythonMailingLists': 'ko.browse.aspnMailingList("Python")',
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
    'cmd_helpLanguage': 'ko.help.language()',
    'cmd_helpLanguageAlternate': 'ko.help.alternate()',
    'cmd_toolsWatchFile': 'ko.launch.watchLocalFile()',
    'cmd_toolsRunCommand': 'ko.launch.runCommand()',
    'cmd_newWindow': 'ko.launch.newWindow()',
    'cmd_open': 'ko.open.filePicker()',
    'cmd_open_remote': 'ko.filepicker.openRemoteFiles()',
    'cmd_openTemplate': 'ko.open.templatePicker()',
    'cmd_new': 'ko.views.manager.doNewViewAsync()',
    'cmd_newTemplate': 'ko.views.manager.newTemplateAsync()',
    'cmd_quit': 'ko.main.quitApplication()',
    'cmd_findInFiles': 'ko.launch.findInFiles()',
    'cmd_replaceInFiles': 'ko.launch.replaceInFiles()',
    'cmd_nextLintResult': 'ko.lint.jumpToNextLintResult()',
    'cmd_lintClearResults': 'ko.lint.clearResults()',
    'cmd_lintNow': 'ko.lint.doRequest()'
}

// The following controller is for any <command> or <broadcaster>
// that doesn't fit into any other controller.  It is generally
// used for commands that don't ever get disabled.

function broadcasterController() {}

// The following two lines ensure proper inheritance (see Flanagan, p. 144).
broadcasterController.prototype = new Controller();
broadcasterController.prototype.constructor = broadcasterController;

broadcasterController.prototype.destructor = function() {
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
        return eval(handlers[cmdName]);
    };
    return false;
}

window.controllers.appendController(new broadcasterController());


}).apply();
