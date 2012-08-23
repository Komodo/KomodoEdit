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

/* Dialog to edit an environment variable.
 *
 * Usage:
 *  All dialog interaction is done via an object passed in and out as the first
 *  window argument: window.arguments[0]. All these arguments are optional.
 *      .name           default name for env. var.
 *      .value          default value for env. var.
 *      .title          the dialog title
 *      .mruName        if set this will be used to identify an MRU preference
 *                      set and an MRU will be provided
 *  On return window.arguments[0] has:
 *      .retval         "OK" or "Cancel" indicating how the dialog was exitted
 *  and iff .retval == "OK":
 *      .name           the name to user entered
 *      .value          the value to user entered
 *
 */

//---- globals

var _gUsingMRU = false;
var log = ko.logging.getLogger("dialogs.editEnvVar");
log.setLevel(ko.logging.LOG_DEBUG)


//---- interface routines for XUL

function OnLoad()
{
    var dialog = document.getElementById("dialog-editenvvar")
    var okButton = dialog.getButton("accept");
    var cancelButton = dialog.getButton("cancel");
    var interpolateMenu = document.getElementById("shortcuts-menubutton");
    okButton.setAttribute("accesskey", "o");
    cancelButton.setAttribute("accesskey", "c");

    // .name
    var name = window.arguments[0].name;
    if (typeof name == "undefined" || name == null) {
        name = "";
    }
    var nameWidget = document.getElementById("name");
    nameWidget.setAttribute("value", name);

    // .value
    var value = window.arguments[0].value;
    if (typeof value == "undefined" || value == null) {
        value = "";
    }
    var valueWidget = document.getElementById("value");
    valueWidget.setAttribute("value", value);

    // .title
    if (typeof window.arguments[0].title != "undefined" &&
        window.arguments[0].title != null) {
        document.title = window.arguments[0].title;
    } else {
        document.title = "Edit Variable";
    }

    // .mruName
    var mruName = window.arguments[0].mruName;
    if (typeof mruName != "undefined" && mruName != null) {
        nameWidget.setAttribute("autocompletesearchparam", mruName+"_name_mru");
        nameWidget.removeAttribute("disableautocomplete");
        nameWidget.setAttribute("enablehistory", "true");
        valueWidget.setAttribute("autocompletesearchparam", mruName+"_value_mru");
        valueWidget.removeAttribute("disableautocomplete");
        valueWidget.setAttribute("enablehistory", "true");
        _gUsingMRU = true;
    }

    var interpolateValues = window.arguments[0].interpolateValues;
    if (typeof interpolateValues != "undefined" && interpolateValues) {
        interpolateMenu.removeAttribute('collapsed');
    }

    window.sizeToContent();
    if (opener.innerHeight == 0) { // indicator that opener hasn't loaded yet
        dialog.centerWindowOnScreen();
    } else {
        dialog.moveToAlertPosition(); // requires a loaded opener
    }

    if (name) {
        valueWidget.focus();
    } else {
        nameWidget.focus();
    }
}

function OnUnload()
{
    log.info("OnUnload()");
    try {
    if (typeof window.arguments[0].retval == "undefined") {
        // This happens when "X" window close button is pressed.
        window.arguments[0].retval = "Cancel";
    } else if (window.arguments[0].retval == "OK") {
        var nameWidget = document.getElementById("name");
        window.arguments[0].name = nameWidget.value;
        if (_gUsingMRU) {
            ko.mru.addFromACTextbox(nameWidget);
        }
        var valueWidget = document.getElementById("value");
        window.arguments[0].value = valueWidget.value;
        if (_gUsingMRU) {
            ko.mru.addFromACTextbox(valueWidget);
        }
    }
    } catch(ex) {
        log.error("error in OnUnload: "+ex);
    }
}


function AddPath()
{
// #if PLATFORM == "win"
    var pathsep = ";";
// #else
    var pathsep = ":";
// #endif

    var prefName = "editEnvVar.AddPath"
    var default_dir = ko.filepicker.internDefaultDir(prefName);
    var dname = ko.filepicker.getFolder(default_dir);
    if (dname) {
        var valueWidget = document.getElementById("value");
        ko.filepicker.internDefaultDir(prefName, dname);
        if (!valueWidget.value) {
            valueWidget.value = dname
        } else {
            var value = valueWidget.value;
            if (value[value.length-1] != pathsep)
                value += pathsep
            value += dname;
            valueWidget.value = value
        }
    }
}

function OK()
{
    window.arguments[0].retval = "OK";
    return true;
}


function Cancel()
{
    window.arguments[0].retval = "Cancel";
    return true;
}

function InsertShortcut(shortcutWidget)
{
    // Get the shortcut string from the menuitem widget and append it to
    // the current command string.
    var shortcut = shortcutWidget.getAttribute("shortcut");
    var textbox = document.getElementById("value");
    _InsertShortcut(textbox, shortcut);
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
