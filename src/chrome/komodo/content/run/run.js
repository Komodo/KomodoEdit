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

/* -*- Mode: JavaScript; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 2 -*-
 *
 * Komodo's Run dialog
 *
 * This dialog allows the user to run an arbitrary command string. Some
 * tweaks try to make it more useful to the user. E.g. the string is
 * interpolated to translate '%' to the full name of the file currently being
 * editted... etc. Basically the plan is to be able to do what can be done with
 * the various incarnations of ":!<shell-command>" in Vim.
 *
 * TODO:
 * - HTML documentation.
 * - "help" button in run dialog leading to this documentation
 */

//---- globals

var log = ko.logging.getLogger("run");

// object to hold all XUL element references
var dialog;

var _gPrefSvc = null;

var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
    .getService(Components.interfaces.nsIStringBundleService)
    .createBundle("chrome://komodo/locale/run/run.properties");


//---- interface routines for run.xul

function OnLoad()
{
    try {
        dialog = {};
        dialog.runButton = document.getElementById('run');
        dialog.closeButton = document.getElementById('close');
        dialog.moreOptionsBox = document.getElementById('more-options-box');
        dialog.commandTextbox = document.getElementById("command-textbox");
        dialog.opOnSelWidget = document.getElementById("operate-on-selection-checkbox");
        dialog.insertOutputWidget = document.getElementById("insert-output-checkbox");
        dialog.doNotOpenOutWinWidget = document.getElementById("do-not-open-output-window-checkbox");
        dialog.parseOutputCheckbox = document.getElementById("parse-output-checkbox");
        dialog.parseRegexTextbox = document.getElementById("parse-regex-textbox");
        dialog.showParsedOutputListCheckbox = document.getElementById("show-parsed-output-list-checkbox");
        dialog.runInMenulist = document.getElementById("run-in-menulist");
        dialog.cwdTextbox = document.getElementById("cwd-textbox");
        dialog.addToToolboxWidget = document.getElementById("add-to-toolbox-checkbox");
        dialog.saveOptsCheckbox = document.getElementById("save-options-checkbox");

        _gPrefSvc = Components.classes["@activestate.com/koPrefService;1"].
                    getService(Components.interfaces.koIPrefService);

        // Determine if there is a current selection. If so then presume the user
        // wants to operate on that selection.
        var view = opener.ko.views.manager.currentView;
        if (view && "scimoz" in view) {
            var scimoz = view.scimoz;
            var selectedText = scimoz.selText;
            if (selectedText != "") {
                // If the selected text has newline characters in it or *is* an
                // entire line (without the end-of-line) then "operate on
                // selection".
                var curLineObj = new Object;
                scimoz.getCurLine(curLineObj);
                var curLine = curLineObj.value;
                if (selectedText.search(/\n/) != -1
                    || selectedText == curLine.substring(0,curLine.length-1))
                {
                    dialog.opOnSelWidget.checked = true;
                    dialog.insertOutputWidget.checked = true;
                }
            }
        }

        RunEnv_OnLoad();
        RestoreUIPrefs();

        // Insert any text from the input buffer and give the command textbox the
        // initial focus.
        var inputBufferContents = opener.ko.inputBuffer.finish();
        if (inputBufferContents) {
            dialog.commandTextbox.setAttribute('value', inputBufferContents);
        }
        var mruName = dialog.commandTextbox.getAttribute("autocompletesearchparam");
        dialog.commandTextbox.value = ko.mru.get(mruName);
        dialog.commandTextbox.focus();
        dialog.commandTextbox.select();
        UpdateCommand();
    } catch(ex) {
        log.exception(ex, "Error loading run command dialog");
    }
}


function OnUnload()
{
    SaveUIPrefs();
}


function ToggleCheck(name)
{
    var id = name + "-checkbox";
    var widget = document.getElementById(id);
    widget.checked = !widget.checked;

    if (name == "insert-output") {
        UpdateInsertOutput();
    }
}


function RestoreUIPrefs()
{
    // Restore run dialog UI preferences.
    var showMoreOptions = _gPrefSvc.prefs.getBooleanPref("runShowMoreOptions");
    if (showMoreOptions) {
        ToggleMoreOptions();
    }

    dialog.cwdTextbox.value = _gPrefSvc.prefs.getStringPref("runCwd");

    var runIn = _gPrefSvc.prefs.getStringPref("runRunIn");
    var menuitems = dialog.runInMenulist.firstChild.childNodes;
    for (var i=0; i < menuitems.length; i++) {
        var menuitem = menuitems[i];
        if (menuitem.getAttribute("value") == runIn) {
            dialog.runInMenulist.selectedIndex = i;
        }
    }
    dialog.doNotOpenOutWinWidget.checked =
        _gPrefSvc.prefs.getBooleanPref("runDoNotOpenOutWin");
    dialog.parseOutputCheckbox.checked =
        _gPrefSvc.prefs.getBooleanPref("runParseOutput");
    dialog.parseRegexTextbox.value =
        _gPrefSvc.prefs.getStringPref("runParseRegex");
    dialog.showParsedOutputListCheckbox.checked =
        _gPrefSvc.prefs.getBooleanPref("runShowParsedOutputList");
    UpdateRunIn();

    var env = _gPrefSvc.prefs.getStringPref("runEnv");
    gRunEnvView.SetEnvironmentStrings(env);
}


function SaveUIPrefs()
{
    // Save dialog UI preferences.
    if (dialog.moreOptionsBox.getAttribute("hidden") == "false") {
        _gPrefSvc.prefs.setBooleanPref("runShowMoreOptions", true);
    } else {
        _gPrefSvc.prefs.setBooleanPref("runShowMoreOptions", false);
    }

    if (dialog.saveOptsCheckbox.checked) {
        _gPrefSvc.prefs.setStringPref("runCwd", dialog.cwdTextbox.value);
        _gPrefSvc.prefs.setStringPref("runRunIn", dialog.runInMenulist.value);
        _gPrefSvc.prefs.setBooleanPref("runDoNotOpenOutWin",
                                       dialog.doNotOpenOutWinWidget.checked);
        _gPrefSvc.prefs.setBooleanPref("runParseOutput",
                                       dialog.parseOutputCheckbox.checked);
        _gPrefSvc.prefs.setStringPref("runParseRegex",
                                      dialog.parseRegexTextbox.value);
        _gPrefSvc.prefs.setBooleanPref("runShowParsedOutputList",
                                       dialog.showParsedOutputListCheckbox.checked);
        _gPrefSvc.prefs.setStringPref("runEnv",
                                      gRunEnvView.GetEnvironmentStrings());
    }
}


function RunCommandAndExit()
{
    // Validate.
    if (! dialog.commandTextbox.value) {
        alert(_bundle.GetStringFromName("specifyACommandString.alert"));
        dialog.commandTextbox.focus();
        return;
    }
    if (dialog.parseOutputCheckbox.checked && !dialog.parseRegexTextbox.value) {
        alert(_bundle.GetStringFromName("specifyARegularExpression.alert"));
        dialog.parseRegexTextbox.focus();
        return;
    }

    // Get the information from the UI
    var cmd = dialog.commandTextbox.value;
    var opt = {
        "window": opener,
        "cwd": dialog.cwdTextbox.value,
        "env": gRunEnvView.GetEnvironmentStrings(),
        "insertOutput": dialog.insertOutputWidget.checked,
        "operateOnSelection": dialog.opOnSelWidget.checked,
        "openOutputWindow": !(dialog.doNotOpenOutWinWidget.checked),
        "runIn": dialog.runInMenulist.value,
        "parseRegex": dialog.parseRegexTextbox.value,
        "showParsedOutputList": dialog.showParsedOutputListCheckbox.checked,
        "saveInMRU": true
    };

    if (cmd == "") {
        alert(_bundle.GetStringFromName("specifyACommand.alert"));
        return;
    }

    // Run the command.
    var launched = ko.run.command(cmd, opt);
    if (!launched) {
        // Don't close the window if there was an error launching.
        return;
    }

    // Add the command to the toolbox (need a better UI for this).
    if (dialog.addToToolboxWidget.checked) {
        opener.ko.toolboxes.addCommand(cmd,
                                       opt.cwd,
                                       opt.env,
                                       opt.insertOutput,
                                       opt.operateOnSelection,
                                       opt.doNotOpenOutputWindow,
                                       opt.runIn,
                                       opt.parseRegex ? true : false,
                                       opt.parseRegex,
                                       opt.showParsedOutputList);
    }

    // Exit
    window.close();
}


function Exit()  {
    window.close();
}


function _InsertShortcut(textbox, shortcut)
{
    log.info("_InsertShortcut(textbox="+textbox+", shortcut='"+shortcut+"')");
    var oldValue = textbox.value;
    var selStart = textbox.selectionStart;
    var selEnd = textbox.selectionEnd;

    var newValue = oldValue.slice(0, selStart) + shortcut
                   + oldValue.slice(selEnd, oldValue.length);
    textbox.value = newValue
    textbox.setSelectionRange(selStart, selStart + shortcut.length);
}

function InsertCommandShortcut(shortcutWidget)
{
    log.info("InsertCommandShortcut(shortcutWidget='"+shortcutWidget+"')");
    try {
        // Get the shortcut string from the menuitem widget and append it to
        // the current command string.
        var shortcut = shortcutWidget.getAttribute("shortcut");
        var textbox = document.getElementById("command-textbox");
        _InsertShortcut(textbox, shortcut);
    } catch(ex) {
        log.error("InsertCommandShortcut error: "+ex);
    }
}

function InsertCwdShortcut(shortcutWidget)
{
    var shortcut = shortcutWidget.getAttribute("shortcut");
    var textbox = document.getElementById("cwd-textbox");
    _InsertShortcut(textbox, shortcut);
}


function ToggleMoreOptions()
{
    var moreOptionsBox = document.getElementById("more-options-box");
    var moreOptionsButton = document.getElementById("more-options-button");
    var hidden = moreOptionsBox.getAttribute("hidden");

    if (hidden == "true") {
        moreOptionsBox.setAttribute("hidden", "false");
        moreOptionsButton.setAttribute("label",
            _bundle.GetStringFromName("less.label"));
        moreOptionsButton.setAttribute("open", "false");
    } else if (hidden == "false") {
        moreOptionsBox.setAttribute("hidden", "true");
        moreOptionsButton.setAttribute("label",
            _bundle.GetStringFromName("more.label"));
        moreOptionsButton.setAttribute("open", "true");
    } else {
        throw new Error("Unexpected 'hidden' state for 'more-options-box': "
                        + hidden);
    }
    window.sizeToContent();
}


// Make changes necessary for a change in the "Insert Output" checkbox.
// - The "Run in:" section is immaterial if we are capturing the output.
function UpdateInsertOutput()
{
    if (dialog.insertOutputWidget.checked) {
        dialog.runInMenulist.setAttribute("disabled", "true");
        dialog.doNotOpenOutWinWidget.setAttribute("disabled", "true");
        dialog.parseOutputCheckbox.setAttribute("disabled", "true");
        dialog.parseRegexTextbox.setAttribute("disabled", "true");
        dialog.showParsedOutputListCheckbox.setAttribute("disabled", "true");
    } else {
        dialog.runInMenulist.removeAttribute("disabled");
        UpdateRunIn();
    }
}


function UpdateRunIn()
{
    // Make changes necessary for a change in the "Run In" menulist.
    if (dialog.runInMenulist.value == "command-output-window") {
        dialog.doNotOpenOutWinWidget.removeAttribute("disabled");
        dialog.parseOutputCheckbox.removeAttribute("disabled");
        UpdateParseOutput();
    } else {
        dialog.doNotOpenOutWinWidget.setAttribute("disabled", "true");
        dialog.parseOutputCheckbox.setAttribute("disabled", "true");
        dialog.parseRegexTextbox.setAttribute("disabled", "true");
        dialog.showParsedOutputListCheckbox.setAttribute("disabled", "true");
    }
}


function UpdateParseOutput()
{
    if (dialog.parseOutputCheckbox.checked) {
        dialog.parseRegexTextbox.removeAttribute("disabled");
        dialog.showParsedOutputListCheckbox.removeAttribute("disabled");
    } else {
        dialog.parseRegexTextbox.setAttribute("disabled", "true");
        dialog.showParsedOutputListCheckbox.setAttribute("disabled", "true");
    }
}


// Make changes necessary for a change in the command string.
function UpdateCommand()
{
    if (dialog.commandTextbox.value) {
        dialog.runButton.removeAttribute("disabled");
    } else {
        dialog.runButton.setAttribute("disabled", "true");
    }
}


function BrowseForCwd()
{
    // from window-functions.js
    var currentValue = dialog.cwdTextbox.value;
    if (currentValue.indexOf("%") >= 0) {
        var env_in = [];
        var name = null;
        var viewData = null;
        var istrings = ko.interpolate.interpolate(opener, [currentValue],
                                              env_in, name, viewData);
        if (istrings && istrings[0]) {
            currentValue = istrings[0];
        }
    }
    var cwd = ko.filepicker.getFolder(currentValue);
    if (cwd) {
        dialog.cwdTextbox.value = cwd;
    }
}


//---- The methods for the run environment tree area.

function _UpdateSortIndicators(sortId)
{
    var sortedColumn = null;

    // Set the sort indicator on the column we are sorted by.
    if (sortId) {
        sortedColumn = document.getElementById(sortId);
        if (sortedColumn) {
            var sortDirection = sortedColumn.getAttribute("sortDirection");
            if (sortDirection && sortDirection == "ascending") {
                sortedColumn.setAttribute("sortDirection", "descending");
            } else {
                sortedColumn.setAttribute("sortDirection", "ascending");
            }
        }
    }

    // Remove the sort indicator from all the columns except the one we are
    // sorted by.
    var currCol = document.getElementById("env").firstChild.firstChild;
    while (currCol) {
        while (currCol && currCol.localName != "treecol") {
            currCol = currCol.nextSibling;
        }
        if (currCol && (currCol != sortedColumn)) {
            currCol.removeAttribute("sortDirection");
        }
        if (currCol) {
            currCol = currCol.nextSibling;
        }
    }
}


function RunEnv_OnLoad()
{
    // Should be called in the onload handler for the window containing the
    // find results tab XUL.
    gRunEnvView = Components.classes[
        '@activestate.com/koRunEnvView;1']
        .createInstance(Components.interfaces.koIRunEnvView);
    var envTree = document.getElementById("env");
    envTree.treeBoxObject
               .QueryInterface(Components.interfaces.nsITreeBoxObject)
               .view = gRunEnvView;
}


function RunEnv_OnClick(event)
{
    // c.f. mozilla/mailnews/base/resources/content/threadPane.js
    var t = event.originalTarget;
    var index = gRunEnvView.selection.currentIndex;
    var rowCount = gRunEnvView.rowCount;
    //dump("RunEnv_OnClick(): start, index="+index+", rowCount="+rowCount+"\n");

    // single-click on a column
    if (t.localName == "treecol") {
        //dump("RunEnv_OnClick: single-click on a column...");
        if (rowCount > 0) {
            //dump("run sort\n");
            RunEnv_Sort(t.id);
        } else {
            //dump("ignored\n");
        }
    }

    // double-click in the tree body
    else if (event.detail == 2 && t.localName == "treechildren") {
        //dump("RunEnv_OnClick: double-click in the tree body...");
        if (0 <= index && index < rowCount) {
            //dump("run edit\n");
            RunEnv_Edit();
        } else {
            //dump("ignored\n");
        }
    }

    // single-click in the tree body
    else if (event.detail == 1 && t.localName == "treechildren") {
        //dump("RunEnv_OnClick: single-click in the tree body...");
        if (0 <= index && index < rowCount) {
            //dump("enable buttons\n");
            document.getElementById("env-edit-button").disabled = false;
            document.getElementById("env-delete-button").disabled = false;
        } else {
            //dump("ignored\n");
        }
    }
}


function RunEnv_Sort(columnID)
{
    gRunEnvView.Sort(columnID);
    _UpdateSortIndicators(columnID);
}


function RunEnv_OnKeyPress(event)
{
    var index = gRunEnvView.selection.currentIndex;
    var rowCount = gRunEnvView.rowCount;
    //dump("RunEnv_OnKeyPress(): start, index="+index+", rowCount="+rowCount+
    //     ", keyCode="+event.keyCode+"\n");

    if (event.keyCode == 13 /* <Enter> */) {
        //dump("RunEnv_OnKeyPress(): <Enter> key...");
        if (0 <= index && index < rowCount) {
            //dump("run edit and cancel bubble\n");
            RunEnv_Edit();
            event.cancelBubble = true;
        } else {
            //dump("ignored\n");
        }
    }
    return true;
}


// Add a new environment variable.
function RunEnv_New()
{
    // Disable the other buttons and unselect any current variable while the
    // edit dialog is up.
    document.getElementById("env").currentIndex = -1;
    document.getElementById("env-edit-button").disabled = true;
    document.getElementById("env-delete-button").disabled = true;

    var obj = ko.dialogs.editEnvVar(null, null, null, null, true);
    if (obj == null) { // Cancelled.
        return;
    }
    var addIt = "Yes";
    if (gRunEnvView.Have(obj.name)) {
        addIt = ko.dialogs.yesNo(
            _bundle.formatStringFromName("thereIsAlreadyAValueFor.message", [obj.name], 1),
            "No");
    }
    if (addIt == "Yes") {
        gRunEnvView.Set(obj.name, obj.value);

        // Select the new variable.
        var index = gRunEnvView.Index(obj.name);
        gRunEnvView.selection.currentIndex = index;
        gRunEnvView.selection.select(index);
        document.getElementById("env-edit-button").disabled = false;
        document.getElementById("env-delete-button").disabled = false;
    }
}


// Edit the currently selected environment variable row.
function RunEnv_Edit()
{
    var index = document.getElementById("env").currentIndex;
    var rowCount = gRunEnvView.rowCount;
    if (index < 0 || rowCount <= index) {
        return;
    }

    var obj = ko.dialogs.editEnvVar(gRunEnvView.GetVariable(index),
                                gRunEnvView.GetValue(index),
                                null, null, true);
    if (obj == null) { // Cancelled.
        return;
    }
    gRunEnvView.Set(obj.name, obj.value);

    // Select the editted variable.
    index = gRunEnvView.Index(obj.name);
    gRunEnvView.selection.currentIndex = index;
    gRunEnvView.selection.select(index);
    document.getElementById("env-edit-button").disabled = false;
    document.getElementById("env-delete-button").disabled = false;
}


// Delete the currently selected environment variable row.
function RunEnv_Delete()
{
    var index = document.getElementById("env").currentIndex;
    var rowCount = gRunEnvView.rowCount;
    if (index < 0 || rowCount <= index) {
        return;
    }

    gRunEnvView.Delete(gRunEnvView.selection.currentIndex);

    // Select the previous variable.
    index = gRunEnvView.selection.currentIndex;
    rowCount = gRunEnvView.rowCount;
    if (rowCount > 0 && index >= rowCount) {
        index = rowCount - 1;
        gRunEnvView.selection.currentIndex = index;
        gRunEnvView.selection.select(index);
    }

    if (index >= 0 && index < rowCount) {
        document.getElementById("env-edit-button").disabled = false;
        document.getElementById("env-delete-button").disabled = false;
    } else {
        document.getElementById("env-edit-button").disabled = true;
        document.getElementById("env-delete-button").disabled = true;
    }
}

