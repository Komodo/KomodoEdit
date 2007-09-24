/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

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
    'cmd_helpCommunity': 'ko.browse.browseTag("community")',
    'cmd_helpViewBugs': 'ko.browse.browseTag("bugs")',
    'cmd_helpLanguage': 'ko.help.language()',
    'cmd_helpLanguageAlternate': 'ko.help.alternate()',
    'cmd_toolsWatchFile': 'ko.launch.watchLocalFile()',
    'cmd_toolsRunCommand': 'ko.launch.runCommand()',
    'cmd_open': 'ko.open.filePicker()',
    'cmd_open_remote': 'ko.filepicker.openRemoteFiles()',
    'cmd_openTemplate': 'ko.open.templatePicker()',
    'cmd_new': 'ko.views.manager.doNewView()',
    'cmd_newTemplate': 'ko.views.manager.newTemplate()',
    'cmd_quit': 'goQuitApplication()',
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
