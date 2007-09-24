/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

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

    var dname = ko.filepicker.getFolder();
    if (dname) {
        var valueWidget = document.getElementById("value");
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
