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
 * A Command Part properties dialog
 *
 * Used for showing/editing properties of an existing command part or for
 * creating a new one.
 */

//---- globals

var log = ko.logging.getLogger("commandproperties")

var gDlg = null;    // Object to hold all XUL element references.
// "add" | "properties", indicates whether this is dialog is being used to add
// a new command or edit the properties for an existing one.
var gMode = null;
var gPart = null;
// An "item" (a.k.a. a wrapper around the part) *may* be passed in. In which
// case any part name changes should be written through to the item.
var gNameTracksCommand = false;
var gCache = {};    // Cache UI values.
var gPrefSvc = null;

var gBundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
    .getService(Components.interfaces.nsIStringBundleService)
    .createBundle("chrome://komodo/locale/run/commandproperties.properties");


//---- interface routines for commandproperties.xul

function OnLoad()
{
    try {
    // A command part is expected as the first window argument.
    gPart = window.arguments[0].part;

    gPrefSvc = Components.classes["@activestate.com/koPrefService;1"].
               getService(Components.interfaces.koIPrefService);

    gDlg = {};
    gDlg.window = document.getElementById("dialog-command-properties");
    gDlg.tabs = document.getElementById("tabs");
    gDlg.shortcut_tab = document.getElementById("shortcut_tab");
    gDlg.command_tab = document.getElementById("command_tab");
    gDlg.commandTextbox = document.getElementById("command-textbox");
    gDlg.nameTextbox = document.getElementById("name-textbox");
    gDlg.nameLabel  = document.getElementById("name-label");
    gDlg.opOnSelWidget = document.getElementById("operate-on-selection-checkbox");
    gDlg.insertOutputWidget = document.getElementById("insert-output-checkbox");
    gDlg.doNotOpenOutWinWidget = document.getElementById("do-not-open-output-window-checkbox");
    gDlg.parseOutputCheckbox = document.getElementById("parse-output-checkbox");
    gDlg.parseRegexTextbox = document.getElementById("parse-regex-textbox");
    gDlg.showParsedOutputListCheckbox = document.getElementById("show-parsed-output-list-checkbox");
    gDlg.runInMenulist = document.getElementById("run-in-menulist");
    gDlg.cwdTextbox = document.getElementById("cwd-textbox");
    gDlg.okButton = gDlg.window.getButton("accept");
    gDlg.applyButton = gDlg.window.getButton("extra1");
    gDlg.cancelButton = gDlg.window.getButton("cancel");
    gDlg.keybinding = document.getElementById('keybindings');
    gDlg.keybinding.gKeybindingMgr = opener.ko.keybindings.manager;
    gDlg.keybinding.part = gPart;
    gDlg.tabs.selectedTab = gDlg.command_tab;  // in some circumstances we may want to change this.
    update_icon(gPart.iconurl);
    Env_OnLoad();

    // Load the UI fields.
    if (gPart.value) {
        gMode = "properties";
        gDlg.commandTextbox.setAttribute("value", gPart.value);
        LoadOptionsFromPart(gPart);
    } else {
        gMode = "add";
        LoadOptionsFromPrefs();
    }
    UpdateField("command", true);
    if (gPart.hasAttribute("name")) {
        var name = gPart.getStringAttribute("name");
        gDlg.nameTextbox.setAttribute("value", name);
        gDlg.nameLabel.setAttribute("value", name);
        if (gMode == "properties") {
            document.title = gBundle.formatStringFromName("properties.title", [name], 1);
            if (name == gPart.value) {
                gNameTracksCommand = true;
            }
        } else {
            gNameTracksCommand = true;
            document.title = gBundle.GetStringFromName("addcommand.title");
        }
        UpdateField("name", true);
    } else {
        gNameTracksCommand = true;
    }

    gDlg.keybinding.commandParam = gPart.id;
    gDlg.keybinding.init();
    gDlg.keybinding.updateCurrentKey();

    gDlg.okButton.setAttribute("accesskey", "O");
    gDlg.applyButton.setAttribute("accesskey", gBundle.GetStringFromName("apply.accesskey"));
    gDlg.applyButton.setAttribute("label", gBundle.GetStringFromName("apply.label"));
    gDlg.applyButton.setAttribute("disabled", "true");
    gDlg.cancelButton.setAttribute("accesskey", "C");
    if (! gPart.value) { // then we are "adding" rather than "editting"
        gDlg.applyButton.setAttribute("collapsed", "true");
    }
    gDlg.commandTextbox.focus();
    } catch (e) {
        log.error(e);
    }
}


function OnUnload()
{
}


function LoadOptionsFromPrefs()
{
    gDlg.cwdTextbox.value = gPrefSvc.prefs.getStringPref("runCwd");
    UpdateField("cwd", true);

    var runIn = gPrefSvc.prefs.getStringPref("runRunIn");
    var menuitems = gDlg.runInMenulist.firstChild.childNodes;
    for (var i=0; i < menuitems.length; i++) {
        var menuitem = menuitems[i];
        if (menuitem.getAttribute("value") == runIn) {
            gDlg.runInMenulist.selectedIndex = i;
        }
    }
    gDlg.doNotOpenOutWinWidget.checked =
        gPrefSvc.prefs.getBooleanPref("runDoNotOpenOutWin");
    UpdateField("runIn", true);

    gDlg.parseOutputCheckbox.checked =
        gPrefSvc.prefs.getBooleanPref("runParseOutput");
    gDlg.parseRegexTextbox.value = gPrefSvc.prefs.getStringPref("runParseRegex");
    gDlg.showParsedOutputListCheckbox.checked =
        gPrefSvc.prefs.getBooleanPref("runShowParsedOutputList");
    UpdateField("parse-output", true);

    var env = gPrefSvc.prefs.getStringPref("runEnv");
    gEnvView.SetEnvironmentStrings(env);
    UpdateField("env", true);
}


function LoadOptionsFromPart(part)
{
    if (part.hasAttribute("cwd")) {
        gDlg.cwdTextbox.setAttribute("value",
            part.getStringAttribute("cwd"));
        UpdateField("cwd", true);
    }
    if (part.hasAttribute("env")) {
        var env = ko.stringutils.unescapeWhitespace(part.getStringAttribute("env"), '\n');
        gEnvView.SetEnvironmentStrings(env);
        UpdateField("env", true);
    }
    if (part.hasAttribute("insertOutput")) {
        gDlg.insertOutputWidget.setAttribute("checked",
            part.getBooleanAttribute("insertOutput"));
        UpdateField("insert-output", true);
    }
    if (part.hasAttribute("operateOnSelection")) {
        gDlg.opOnSelWidget.setAttribute("checked",
            part.getBooleanAttribute("operateOnSelection"));
        UpdateField("operate-on-selection", true);
    }
    if (part.hasAttribute("doNotOpenOutputWindow")) {
        gDlg.doNotOpenOutWinWidget.setAttribute("checked",
            part.getBooleanAttribute("doNotOpenOutputWindow"));
        UpdateField("do-not-open-output-window", true);
    }
    if (part.hasAttribute("parseOutput")) {
        gDlg.parseOutputCheckbox.setAttribute("checked",
            part.getBooleanAttribute("parseOutput"));
        UpdateField("parse-output", true);
    }
    if (part.hasAttribute("parseRegex")) {
        gDlg.parseRegexTextbox.setAttribute("value",
            part.getStringAttribute("parseRegex"));
        UpdateField("parse-regex", true);
    }
    if (part.hasAttribute("showParsedOutputList")) {
        gDlg.showParsedOutputListCheckbox.setAttribute("checked",
            part.getBooleanAttribute("showParsedOutputList"));
        UpdateField("show-parsed-output-list", true);
    }
    if (part.hasAttribute("runIn")) {
        var runIn = part.getStringAttribute("runIn");
        var menuitems = gDlg.runInMenulist.firstChild.childNodes;
        for (var i=0; i < menuitems.length; i++) {
            var menuitem = menuitems[i];
            //XXX Beware, this might not be getting the actual value. May need
            //    menuitem.value instead.
            if (menuitem.getAttribute("value") == runIn) {
                gDlg.runInMenulist.selectedIndex = i;
            }
        }
        UpdateField("runIn", true);
    }
}


function ToggleCheck(name)
{
    var id = name + "-checkbox";
    var widget = document.getElementById(id);
    widget.checked = !widget.checked;
    UpdateField(name);
}


// Do the proper UI updates for a user change.
//  "field" (string) indicates the field to update.
//  "initializing" (boolean, optional) indicates that the dialog is still
//      initializing so some updates, e.g. enabling the <Apply> button, should
//      not be done.
function UpdateField(field, initializing /* =false */)
{
    if (typeof(initializing) == "undefined" || initializing == null) initializing = false;

    // Only take action if there was an actual change. Otherwise things like
    // the <Alt-A> shortcut when in a textbox will cause a cycle in reenabling
    // the apply button.
    var changed = false;

    switch (field) {
    case "name":
        var name = gDlg.nameTextbox.value;
        if (!(field in gCache) || name != gCache[field]) {
            changed = true;
            gCache[field] = name;
            if (gMode == "properties") {
                document.title = gBundle.formatStringFromName("properties.title", [name], 1);
            }
            if (!initializing && name != gDlg.commandTextbox.value) {
                gNameTracksCommand = false;
            }
            gDlg.nameLabel.value = name;
        }
        break;

    case "command":
        var command = gDlg.commandTextbox.value;
        if (!(field in gCache) || command != gCache[field]) {
            changed = true;
            gCache[field] = command;
            if (gNameTracksCommand) {
                var shortName = command.substr(0, 20);
                gDlg.nameTextbox.setAttribute("value", shortName);
                gDlg.nameLabel.setAttribute("value", shortName);
                UpdateField("name", initializing);
            }
        }
        if (command) {
            gDlg.okButton.removeAttribute("disabled");
        } else {
            gDlg.okButton.setAttribute("disabled", "true");
        }
        break;

    case "runIn":
        var runIn = gDlg.runInMenulist.value;
        if (!(field in gCache) || runIn != gCache[field]) {
            changed = true;
            gCache[field] = runIn;
        }
        if (runIn == "command-output-window") {
            gDlg.doNotOpenOutWinWidget.removeAttribute("disabled");
            gDlg.doNotOpenOutWinWidget.removeAttribute("disabled");
            gDlg.parseOutputCheckbox.removeAttribute("disabled");
            UpdateField('parse-output', initializing);
        } else {
            gDlg.doNotOpenOutWinWidget.setAttribute("disabled", "true");
            gDlg.parseOutputCheckbox.setAttribute("disabled", "true");
            gDlg.parseRegexTextbox.setAttribute("disabled", "true");
            gDlg.showParsedOutputListCheckbox.setAttribute("disabled", "true");
        }
        break;

    case "insert-output":
        var insertOutput = gDlg.insertOutputWidget.checked;
        if (!(field in gCache) || insertOutput != gCache[field]) {
            changed = true;
            gCache[field] = insertOutput;
            if (gDlg.insertOutputWidget.checked) {
                gDlg.runInMenulist.setAttribute("disabled", "true");
                gDlg.doNotOpenOutWinWidget.setAttribute("disabled", "true");
                gDlg.parseOutputCheckbox.setAttribute("disabled", "true");
                gDlg.parseRegexTextbox.setAttribute("disabled", "true");
                gDlg.showParsedOutputListCheckbox.setAttribute("disabled", "true");
            } else {
                gDlg.runInMenulist.removeAttribute("disabled");
                UpdateField("runIn", initializing);
            }
        }
        break;

    case "operate-on-selection":
        var operateOnSelection = gDlg.opOnSelWidget.checked;
        if (!(field in gCache) || operateOnSelection != gCache[field]) {
            changed = true;
            gCache[field] = operateOnSelection;
        }
        break;

    case "cwd":
        var cwd = gDlg.cwdTextbox.value;
        if (!(field in gCache) || cwd != gCache[field]) {
            changed = true;
            gCache[field] = cwd;
        }
        break;

    case "env":
        var env = gEnvView.GetEnvironmentStrings();
        if (!(field in gCache) || env != gCache[field]) {
            changed = true;
            gCache[field] = env;
        }
        break;

    case "do-not-open-output-window":
        var doNotOpenOutputWindow = gDlg.doNotOpenOutWinWidget.checked;
        if (!(field in gCache) || doNotOpenOutputWindow != gCache[field]) {
            changed = true;
            gCache[field] = doNotOpenOutputWindow;
        }
        break;

    case "shortcut":
    case "icon":
        changed = true;
        break;

    case "parse-output":
        var parseOutput = gDlg.parseOutputCheckbox.checked;
        if (!(field in gCache) || parseOutput != gCache[field]) {
            changed = true;
            gCache[field] = parseOutput;
        }
        if (parseOutput) {
            gDlg.parseRegexTextbox.removeAttribute("disabled");
            gDlg.showParsedOutputListCheckbox.removeAttribute("disabled");
        } else {
            gDlg.parseRegexTextbox.setAttribute("disabled", "true");
            gDlg.showParsedOutputListCheckbox.setAttribute("disabled", "true");
        }
        break;

    case "parse-regex":
        var parseRegex = gDlg.parseRegexTextbox.value;
        if (!(field in gCache) || parseRegex != gCache[field]) {
            changed = true;
            gCache[field] = parseRegex;
        }
        break;

    case "show-parsed-output-list":
        var showParsedOutputList = gDlg.showParsedOutputListCheckbox.checked;
        if (!(field in gCache) || showParsedOutputList != gCache[field]) {
            changed = true;
            gCache[field] = showParsedOutputList;
        }
        break;
    }

    if (!initializing && changed) {
        gDlg.applyButton.removeAttribute("disabled");
    }
}


function OK()
{
    try {
        // Apply changes and exit.
        if (!Apply()) {
            return false;
        }
        window.arguments[0].retval = "OK";
    } catch (e) {
        log.exception(e);
    }
    return true;
}


function Apply()
{
    // Validate.
    if (! gDlg.commandTextbox.value) {
        alert(gBundle.GetStringFromName("specifyACommandString.alert"));
        gDlg.commandTextbox.focus();
        return false;
    }
    if (gDlg.parseOutputCheckbox.checked && !gDlg.parseRegexTextbox.value) {
        alert(gBundle.GetStringFromName("chosenToParseCommand.alert"));
        gDlg.parseRegexTextbox.focus();
        return false;
    }
    // The keybinding needs the commandparam to be set before the application would ever work.
    var retval = gDlg.keybinding.apply(); // This may return false if a keybinding is partially entered
    if (!retval) return false;
    if (gDlg.applyButton.hasAttribute("disabled")
        && gDlg.applyButton.getAttribute("disabled")=='true') {
        return true;
    }

    // Update the command part with info from the UI.
    gPart.value = gDlg.commandTextbox.value;
    gPart.setStringAttribute('name', gDlg.nameTextbox.value);
    gPart.setStringAttribute('cwd', gDlg.cwdTextbox.value);
    var env = gEnvView.GetEnvironmentStrings();
    gPart.setStringAttribute('env', ko.stringutils.escapeWhitespace(env));
    gPart.setBooleanAttribute('insertOutput', gDlg.insertOutputWidget.checked);
    gPart.setBooleanAttribute('operateOnSelection', gDlg.opOnSelWidget.checked);
    gPart.setBooleanAttribute('doNotOpenOutputWindow', gDlg.doNotOpenOutWinWidget.checked);
    gPart.setStringAttribute('runIn', gDlg.runInMenulist.value);
    gPart.setBooleanAttribute('parseOutput', gDlg.parseOutputCheckbox.checked);
    gPart.setStringAttribute('parseRegex', gDlg.parseRegexTextbox.value);
    gPart.setBooleanAttribute('showParsedOutputList', gDlg.showParsedOutputListCheckbox.checked);
    var iconuri = document.getElementById('commandtab_icon').getAttribute('src');
    gPart.iconurl = iconuri;

    // Update the wrapper around the part (item) if it was passed in.
    if (window.arguments[0].task != "new") {
        gPart.save();
    }

    gDlg.applyButton.setAttribute("disabled", "true");
    return true;
}


function Cancel()
{
    window.arguments[0].retval = "Cancel";
}


function _InsertShortcut(textbox, shortcut)
{
    var oldValue = textbox.value;
    var selStart = textbox.selectionStart;
    var selEnd = textbox.selectionEnd;

    var newValue = oldValue.slice(0, selStart) + shortcut
                   + oldValue.slice(selEnd, oldValue.length);
    textbox.value = newValue;
    textbox.setSelectionRange(selStart, selStart+shortcut.length);
}

function InsertCommandShortcut(shortcutWidget)
{
    // Get the shortcut string from the menuitem widget and append it to
    // the current command string.
    var shortcut = shortcutWidget.getAttribute("shortcut");
    var textbox = document.getElementById("command-textbox");
    _InsertShortcut(textbox, shortcut);
    UpdateField('command');
}

function InsertCwdShortcut(shortcutWidget)
{
    var shortcut = shortcutWidget.getAttribute("shortcut");
    var textbox = document.getElementById("cwd-textbox");
    _InsertShortcut(textbox, shortcut);
    UpdateField('cwd');
}



// Browse for a directory for the start dir.
function BrowseForCwd()
{
    // from window-functions.js
    var cwd = ko.filepicker.getFolder(gDlg.cwdTextbox.value);
    if (cwd) {
        gDlg.cwdTextbox.value = cwd;
        UpdateField('cwd');
    }
}


//---- The methods for the environment tree area.

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


function Env_OnLoad()
{
    // Should be called in the onload handler for the window containing the
    // find results tab XUL.
    gEnvView = Components.classes['@activestate.com/koRunEnvView;1']
        .createInstance(Components.interfaces.koIRunEnvView);
    var envTree = document.getElementById("env");
    envTree.treeBoxObject
               .QueryInterface(Components.interfaces.nsITreeBoxObject)
               .view = gEnvView;
}


function Env_OnClick(event)
{
    // c.f. mozilla/mailnews/base/resources/content/threadPane.js
    var t = event.originalTarget;
    var index = gEnvView.selection.currentIndex;
    var rowCount = gEnvView.rowCount;
    //dump("Env_OnClick(): start, index="+index+", rowCount="+rowCount+"\n");

    // single-click on a column
    if (t.localName == "treecol") {
        //dump("Env_OnClick: single-click on a column...");
        if (rowCount > 0) {
            //dump("run sort\n");
            Env_Sort(t.id);
        } else {
            //dump("ignored\n");
        }
    }

    // double-click in the tree body
    else if (event.detail == 2 && t.localName == "treechildren") {
        //dump("Env_OnClick: double-click in the tree body...");
        if (0 <= index && index < rowCount) {
            //dump("run edit\n");
            Env_Edit();
        } else {
            //dump("ignored\n");
        }
    }

    // single-click in the tree body
    else if (event.detail == 1 && t.localName == "treechildren") {
        //dump("Env_OnClick: single-click in the tree body...");
        if (0 <= index && index < rowCount) {
            //dump("enable buttons\n");
            document.getElementById("env-edit-button").disabled = false;
            document.getElementById("env-delete-button").disabled = false;
        } else {
            //dump("ignored\n");
        }
    }
}


function Env_Sort(columnID)
{
    gEnvView.Sort(columnID);
    _UpdateSortIndicators(columnID);
}


function Env_OnKeyPress(event)
{
    var index = gEnvView.selection.currentIndex;
    var rowCount = gEnvView.rowCount;
    //dump("Env_OnKeyPress(): start, index="+index+", rowCount="+rowCount+
    //     ", keyCode="+event.keyCode+"\n");

    if (event.keyCode == 13 /* <Enter> */) {
        //dump("Env_OnKeyPress(): <Enter> key...");
        if (0 <= index && index < rowCount) {
            //dump("run edit and cancel bubble\n");
            Env_Edit();
            event.cancelBubble = true;
        } else {
            //dump("ignored\n");
        }
    }
    return true;
}


// Add a new environment variable.
function Env_New()
{
    // Disable the other buttons and unselect any current variable while the
    // edit gDlg is up.
    document.getElementById("env").currentIndex = -1;
    document.getElementById("env-edit-button").disabled = true;
    document.getElementById("env-delete-button").disabled = true;

    var obj = ko.dialogs.editEnvVar(null, null, null, null, true);
    if (obj == null) { // Cancelled.
        return;
    }
    var addIt = "Yes";
    if (gEnvView.Have(obj.name)) {
        addIt = ko.dialogs.yesNo(
            gBundle.formatStringFromName("thereIsAlreadyAValueFor.message", [obj.name], 1),
            "No");
    }
    if (addIt == "Yes") {
        gEnvView.Set(obj.name, obj.value);

        // Select the new variable.
        var index = gEnvView.Index(obj.name);
        gEnvView.selection.currentIndex = index;
        gEnvView.selection.select(index);
        document.getElementById("env-edit-button").disabled = false;
        document.getElementById("env-delete-button").disabled = false;

        UpdateField('env');
    }
}


// Edit the currently selected environment variable row.
function Env_Edit()
{
    var index = document.getElementById("env").currentIndex;
    var rowCount = gEnvView.rowCount;
    if (index < 0 || rowCount <= index) {
        return;
    }

    var obj = ko.dialogs.editEnvVar(gEnvView.GetVariable(index),
                                gEnvView.GetValue(index),
                                null, null, true);
    if (obj == null) { // Cancelled.
        return;
    }
    gEnvView.Set(obj.name, obj.value);

    // Select the editted variable.
    index = gEnvView.Index(obj.name);
    gEnvView.selection.currentIndex = index;
    gEnvView.selection.select(index);
    document.getElementById("env-edit-button").disabled = false;
    document.getElementById("env-delete-button").disabled = false;

    UpdateField('env');
}


// Delete the currently selected environment variable row.
function Env_Delete()
{
    var index = document.getElementById("env").currentIndex;
    var rowCount = gEnvView.rowCount;
    if (index < 0 || rowCount <= index) {
        return;
    }

    gEnvView.Delete(gEnvView.selection.currentIndex);

    // Select the previous variable.
    index = gEnvView.selection.currentIndex;
    rowCount = gEnvView.rowCount;
    if (rowCount > 0 && index >= rowCount) {
        index = rowCount - 1;
        gEnvView.selection.currentIndex = index;
        gEnvView.selection.select(index);
    }

    if (index >= 0 && index < rowCount) {
        document.getElementById("env-edit-button").disabled = false;
        document.getElementById("env-delete-button").disabled = false;
    } else {
        document.getElementById("env-edit-button").disabled = true;
        document.getElementById("env-delete-button").disabled = true;
    }

    UpdateField('env');
}

function update_icon(URI)
{
    try {
        if (URI == 'chrome://komodo/skin/images/run_commands.png') {
            document.getElementById('reseticon').setAttribute('disabled', 'true');
        } else {
            if (document.getElementById('reseticon').hasAttribute('disabled')) {
                document.getElementById('reseticon').removeAttribute('disabled');
            }
        }
        document.getElementById('keybindingtab_icon').setAttribute('src', URI);
        document.getElementById('commandtab_icon').setAttribute('src', URI);
        if (URI.indexOf('_missing.png') != -1) {
            document.getElementById('commandtab_icon')
                .setAttribute('tooltiptext', gBundle.GetStringFromName("customIconMissing.tooltiptext"));
        } else {
            document.getElementById('commandtab_icon').removeAttribute('tooltiptext');
        }
    } catch (e) {
        log.exception(e);
    }
}

function pick_icon(useDefault /* false */)
{
    try {
        var URI
        if (! useDefault) {
            URI = ko.dialogs.pickIcon();
            if (!URI) return;
        } else {
            URI = 'chrome://komodo/skin/images/run_commands.png';
        }
        update_icon(URI);
        UpdateField('icon');
    } catch (e) {
        log.exception(e);
    }
}
