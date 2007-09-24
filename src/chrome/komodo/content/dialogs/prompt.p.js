/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

/* -*- Mode: JavaScript; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 2 -*-
 *
 * Generic prompt dialog.
 *
 * This dialog allows you to ask the user for a single string input.  Normally
 * this dialog is called indirectly via dialogs.js::prompt_dialog().
 * See the usage documentation there first.
 *
 * Features:
 *  - OK and Cancel buttons.
 *  - Optional leading prompt.
 *  - Configurable dialog title and textbox label.
 *  - Dialog is resizable and it remembers its dimensions.
 *  - Can have an MRU for the textbox.
 *  - Can specify a validator for the value.
 *
 * Usage:
 *  All dialog interaction is done via an object passed in and out as the first
 *  window argument: window.arguments[0]. All these arguments are optional.
 *      .prompt         a leading <description/> to the textbox.
 *                      XXX Note that newlines are not handled nicely. I
 *                      suppose it would be nice to treat these like paragraph
 *                      separators and create separate <description/> blocks
 *                      for them.
 *      .label          the textbox's label
 *      .value          default value for textbox
 *      .title          the dialog title
 *      .mruName        if set this will be used to identify an MRU preference
 *                      set and an MRU will be provided
 *      .validator      A callable object to validate the current value.  It
 *                      will be called with the current value and should return
 *                      true iff the value is acceptable.
 *      .multiline      if true, makes the input box a multiline edit box.
 *                      Multiline and autocomplete (i.e. usage of 'mruName')
 *                      are mutually exclusive.
 *      .screenX, .screenY allow one to specify a dialog position other than
 *                      the alert position.
 *  Support for a second prompt field (these are used by
 *  ko.dialogs.prompt2()):
 *      .label2
 *      .value2
 *      .mruName2
 *      .multiline2
 *  If a type of textbox autocomplete other than "mru" is wanted, it can
 *  be done with the following. (Note: if 'mruName' or 'multiline' are
 *  specified then these are ignored.)
 *      .tacType        textbox autocomplete type
 *      .tacParam       "autocompletesearchparam" textbox attribute value
 *      .tacShowCommentColumn  a boolean setting for "showcommentcolumn" attr
 *
 *  On return window.arguments[0] has:
 *      .retval         "OK" or "Cancel" indicating how the dialog was exitted
 *  and iff .retval == "OK":
 *      .value          is the content of the textbox on exit.
 *      .value2         (if the second prompt field is enabled)
 *
 */

//---- globals

var log = ko.logging.getLogger("dialogs.prompt");

var _gValidator = null; // Function to validate entered value.
var _gUsingMRU = false;
var _gUsingMRU2 = false;


//---- internal support routines

function _safeMoveTo(newX, newY) {
    if (newX == null) newX = opener.screenX;
    if (newY == null) newY = opener.screenY;

    // Ensure the new position is on screen.
    if (newX < screen.availLeft)
        newX = screen.availLeft + 20;
    if ((newX + window.outerWidth) > (screen.availLeft + screen.availWidth))
        newX = (screen.availLeft + screen.availWidth)
               - window.outerWidth - 20;
    if (newY < screen.availTop)
        newY = screen.availTop + 20;
    if ((newY + window.outerHeight) > (screen.availTop + screen.availHeight))
        newY = (screen.availTop + screen.availHeight)
               - window.outerHeight - 60;

    window.moveTo(newX, newY);
}


//---- interface routines for prompt.xul

function OnLoad()
{
    try {
        var dialog = document.getElementById("dialog-prompt")
        var okButton = dialog.getButton("accept");
        var cancelButton = dialog.getButton("cancel");
        okButton.setAttribute("accesskey", "o");
        cancelButton.setAttribute("accesskey", "c");

        // .prompt
        var descWidget = document.getElementById("prompt");
        var desc = window.arguments[0].prompt;
        if (typeof desc != "undefined" && desc != null) {
            var textNode = document.createTextNode(desc);
            descWidget.appendChild(textNode);
        } else {
            descWidget.setAttribute("collapsed", "true");
        }

        // .label
        var label = window.arguments[0].label;
        var labelWidget = document.getElementById("label");
        if (typeof label == "undefined" || label == null) {
            labelWidget.setAttribute("collapsed", "true");
        } else {
            labelWidget.setAttribute("value", label);
        }

        // .value
        var value = window.arguments[0].value;
        if (typeof value == "undefined" || value == null) {
            value = "";
        }
        var textboxWidget = document.getElementById("textbox");
        textboxWidget.setAttribute("value", value);

        // .label2
        var label2 = window.arguments[0].label2;
        var labelWidget2 = document.getElementById("label2");
        if (typeof label2 == "undefined" || label2 == null) {
            labelWidget2.setAttribute("collapsed", "true");
        } else {
            labelWidget2.setAttribute("value", label2);
        }

        // .value2
        var value2 = window.arguments[0].value2;
        var hbox2 = document.getElementById("hbox2");
        if (typeof value2 == "undefined" || value2 == null) {
            value2 = "";
            hbox2.setAttribute("collapsed", "true");
        } else {
            hbox2.setAttribute("collapsed", "false");
        }
        var textboxWidget2 = document.getElementById("textbox2");
        textboxWidget2.setAttribute("value", value2);

        // .title
        if (typeof window.arguments[0].title != "undefined" &&
            window.arguments[0].title != null) {
            document.title = window.arguments[0].title;
        } else {
            document.title = "Komodo";
        }

        // .mruName
        var mruName = window.arguments[0].mruName;
        if (typeof mruName != "undefined" && mruName != null) {
            textboxWidget.setAttribute("autocompletesearchparam", mruName+"_mru");
            textboxWidget.removeAttribute("disableautocomplete");
            textboxWidget.setAttribute("enablehistory", "true");
            _gUsingMRU = true;
        }
        
        // .tacType, .tacParam and .tacShowCommentColumn
        var tacType = window.arguments[0].tacType;
        var tacParam = window.arguments[0].tacParam;
        var tacShowCommentColumn = window.arguments[0].tacShowCommentColumn;
        if (!_gUsingMRU && typeof tacType != "undefined" && tacType != null) {
            textboxWidget.setAttribute("autocompletesearch", tacType);
            if (typeof tacParam != "undefined" && tacParam != null) {
                textboxWidget.setAttribute("autocompletesearchparam", tacParam);
            }
            if (typeof tacShowCommentColumn != "undefined"
                && tacShowCommentColumn) {
                textboxWidget.setAttribute("showcommentcolumn", "true");
            }
            textboxWidget.removeAttribute("disableautocomplete");
            textboxWidget.setAttribute("enablehistory", "true");
            _gUsingMRU = true;
        }

        // .mruName2
        var mruName2 = window.arguments[0].mruName2;
        if (typeof mruName2 != "undefined" && mruName2 != null) {
            textboxWidget2.setAttribute("autocompletesearchparam", mruName2+"_mru");
            textboxWidget2.removeAttribute("disableautocomplete");
            textboxWidget2.setAttribute("enablehistory", "true");
            _gUsingMRU2 = true;
        }

        // .validator
        var validator = window.arguments[0].validator;
        if (typeof validator != "undefined" && validator != null) {
            _gValidator = validator;
        }

        // .multiline
        if (typeof(window.arguments[0].multiline) != 'undefined' &&
            window.arguments[0].multiline) {
            textboxWidget.setAttribute("multiline", "true");
            textboxWidget.setAttribute("rows", "5"); //XXX could make this configurable
            // Autocomplete interferes with multiline (warning about this is
            // done by dialogs.js::ko.dialogs.prompt()).
            textboxWidget.removeAttribute("type");
        }

        // .multiline2
        if (typeof(window.arguments[0].multiline2) != 'undefined' &&
            window.arguments[0].multiline2) {
            textboxWidget2.setAttribute("multiline", "true");
            textboxWidget2.setAttribute("rows", "5"); //XXX could make this configurable
            // Autocomplete interferes with multiline (warning about this is
            // done by dialogs.js::ko.dialogs.prompt()).
            textboxWidget2.removeAttribute("type");
        }

        // Size to content before moving so calculations are correct.
        window.sizeToContent();
        var screenX = window.arguments[0].screenX;
        if (typeof(screenX) == "undefined") screenX = null;
        var screenY = window.arguments[0].screenY;
        if (typeof(screenY) == "undefined") screenY = null;
        if (screenX || screenY) {
            _safeMoveTo(screenX, screenY);
        } else {
            if (opener.innerHeight == 0) { // indicator that opener hasn't loaded yet
                dialog.centerWindowOnScreen();
            } else {
                dialog.moveToAlertPosition(); // requires a loaded opener
            }
        }

        document.getElementById("textbox").focus();
    } catch(ex) {
        log.exception(ex, "Error loading prompt dialog.");
    }
    window.getAttention();
}


function OnUnload()
{
    if (typeof window.arguments[0].retval == "undefined") {
        // This happens when "X" window close button is pressed.
        window.arguments[0].retval = "Cancel";
    } else if (window.arguments[0].retval == "OK") {
        var textboxWidget = document.getElementById("textbox");
        window.arguments[0].value = textboxWidget.value;
        if (_gUsingMRU) {
            ko.mru.addFromACTextbox(textboxWidget);
        }
        var textboxWidget2 = document.getElementById("textbox2");
        window.arguments[0].value2 = textboxWidget2.value;
        if (_gUsingMRU2) {
            ko.mru.addFromACTextbox(textboxWidget2);
        }
    }
}


function OK()
{
    window.arguments[0].retval = "OK";
    var textboxWidget = document.getElementById("textbox");

    try {
        if (_gValidator && !_gValidator(window, textboxWidget.value)) {
            textboxWidget.focus();
            return false; 
        }
    } catch(ex) {
        var errmsg = "Unexpected error while validating your value.";
        log.error(errmsg);
        ko.dialogs.internalError(errmsg, errmsg+"\n"+ex);
        textboxWidget.focus();
        return false;
    }

    return true;
}


function Cancel()
{
    window.arguments[0].retval = "Cancel";
    return true;
}


