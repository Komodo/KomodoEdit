/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

/* Generic dialog with customizable buttons.
 *
 * Usage:
 *  All dialog interaction is done via an object passed in and out as the first
 *  window argument: window.arguments[0]. All these arguments are optional.
 *      .prompt         the question to ask.
 *      .buttons        list of strings naming buttons to use
 *      .response       the default response, must be one of the strings in
 *                      "buttons"
 *      .text           allows you to specify a string of text that will be
 *                      display in a non-edittable selectable text box. If
 *                      "text" is null or no specified then this textbox will
 *                      no be shown.
 *      .title          the dialog title
 *      .doNotAskUI     show the "Don't ask me again" UI
 *  On return window.arguments[0] has:
 *      .response       the name of button used
 *      .doNotAsk       (iff .doNotAskUI) a boolean indicating if this question
 *                      need be asked again.
 */

var log = ko.logging.getLogger("dialogs.customButtons");
//log.setLevel(ko.logging.LOG_DEBUG);

var gDoNotAskUI = false; // true iff "Don't ask me again" UI is being used.
var gAcceptButton = null;
var gExtra1Button = null;
var gExtra2Button = null;
var gCancelButton = null;


//---- interface routines for XUL

function OnLoad()
{
    var i;
    var dialog = document.getElementById("dialog-custombuttons")
    gAcceptButton = dialog.getButton("accept");
    gExtra1Button = dialog.getButton("extra1");
    gExtra2Button = dialog.getButton("extra2");
    gCancelButton = dialog.getButton("cancel");
    gCancelButton.setAttribute("accesskey", "c");
    var buttonWidgets = [gAcceptButton, gExtra1Button, gExtra2Button];

    // .prompt
    var descWidget = document.getElementById("prompt");
    var desc = window.arguments[0].prompt;
    if (typeof desc != "undefined" && desc != null) {
        var textNode = document.createTextNode(desc);
        descWidget.appendChild(textNode);
    } else {
        descWidget.setAttribute("collapsed", "true");
    }

    // .buttons
    var buttons = window.arguments[0].buttons;
    if (typeof buttons == "undefined" || buttons == null) {
        var msg = "Internal Error: illegal 'buttons' value for "
                  +"Custom Buttons dialog: '"+buttons+"'.";
        log.error(msg);
        alert(msg);
        window.close();
    } else if (buttons.length == 0 || buttons.length > 4) {
        var msg = "Internal Error: illegal number of buttons for "
                  +"Custom Buttons dialog: '"+buttons.length+"'.";
        log.error(msg);
        alert(msg);
        window.close();
    } else if (buttons.length == 4 && buttons[3] != "Cancel") {
        var msg = "Internal Error: there are 4 buttons to display but "
                  +"the last one is not Cancel.";
        log.error(msg);
        alert(msg);
        window.close();
    } else if (buttons[buttons.length-1] == "Cancel") {
        for (i = 0; i < buttons.length-1; ++i) {
            buttonWidgets[i].setAttribute("label", buttons[i]);
        }
        for (i = buttons.length-1; i < buttonWidgets.length; ++i) {
            buttonWidgets[i].setAttribute("collapsed", true);
        }
    } else {
        for (i = 0; i < buttons.length; ++i) {
            buttonWidgets[i].setAttribute("label", buttons[i]);
        }
        for (i = buttons.length; i < buttonWidgets.length; ++i) {
            buttonWidgets[i].setAttribute("collapsed", true);
        }
        gCancelButton.setAttribute("collapsed", true);
    }

    var style = window.arguments[0].style;
    document.getElementById("dialog-icon").setAttribute('class', style);

    // .response
    var response = window.arguments[0].response;
    if (typeof response == "undefined" || response == null) {
        // gAcceptButton (the first one) is already the default
    } else if (response == "Cancel") {
        dialog.setAttribute('defaultButton', 'cancel');
        gAcceptButton.removeAttribute("default");
        gCancelButton.setAttribute("default", true);
        gCancelButton.focus();
    } else {
        gAcceptButton.removeAttribute("default");
        for (i = 0; i < buttonWidgets.length; ++i) {
            if (buttonWidgets[i].getAttribute("label") == response) {
                // XXX FIXME dialog.setAttribute('defaultButton', 'extra1');
                buttonWidgets[i].setAttribute("default", true);
                buttonWidgets[i].focus();
                break;
            }
        }
        // Note: we are not raising an error or warning if the default response
        // does not match one of the given button names. No big deal.
    }

    // .text
    if (typeof window.arguments[0].text != "undefined" &&
        window.arguments[0].text != null) {
        var textWidget = document.getElementById("text");
        textWidget.removeAttribute("collapsed");
        textWidget.value = window.arguments[0].text;
    }

    // .title
    if (typeof window.arguments[0].title != "undefined" &&
        window.arguments[0].title != null) {
        document.title = window.arguments[0].title;
    } else {
        document.title = "Komodo";
    }

    // .doNotAskUI
    if (typeof window.arguments[0].doNotAskUI != "undefined" &&
        window.arguments[0].doNotAskUI != null) {
        gDoNotAskUI = window.arguments[0].doNotAskUI;
    }
    if (gDoNotAskUI) {
        document.getElementById("doNotAsk-checkbox")
                .removeAttribute("collapsed");

        // Check for possible conflict with prefs system limitations.
        for (i = 0; i < buttons.length; ++i) {
            if (buttons[i].indexOf(',') != -1) {
                log.warn("Your 'Custom Buttons' dialog has one or more buttons with a comma in its name and you are using the 'Do not ask me again' feature. If you attempt to provide a UI for the 'Do not ask me again' prefs in the Komodo preferences panel you are likely going to hit a limitation in that commas cannot be used in multiple-prefs-per-widget magic hookup. Consider NOT using a comma in your button names.")
                break;
            }
        }
    }

    window.sizeToContent();
    if (opener.innerHeight == 0) { // indicator that opener hasn't loaded yet
        dialog.centerWindowOnScreen();
    } else {
        dialog.moveToAlertPosition(); // requires a loaded opener
    }
    window.getAttention();
}


function Accept()
{
    window.arguments[0].response = gAcceptButton.getAttribute("label");
    if (gDoNotAskUI) {
        var checkbox = document.getElementById("doNotAsk-checkbox");
        window.arguments[0].doNotAsk = checkbox.checked;
    }
    return true;
}

function Extra1()
{
    window.arguments[0].response = gExtra1Button.getAttribute("label");
    if (gDoNotAskUI) {
        var checkbox = document.getElementById("doNotAsk-checkbox");
        window.arguments[0].doNotAsk = checkbox.checked;
    }
    // This is one of the "extra" <dialog/> buttons. Only the "accept" and
    // "cancel" button actions will automatically close the window, so we have
    // to do it manually here.
    window.close();
    return true;
}

function Extra2()
{
    window.arguments[0].response = gExtra2Button.getAttribute("label");
    if (gDoNotAskUI) {
        var checkbox = document.getElementById("doNotAsk-checkbox");
        window.arguments[0].doNotAsk = checkbox.checked;
    }
    // This is one of the "extra" <dialog/> buttons. Only the "accept" and
    // "cancel" button actions will automatically close the window, so we have
    // to do it manually here.
    window.close();
    return true;
}

function Cancel()
{
    window.arguments[0].response = gCancelButton.getAttribute("label");
    if (gDoNotAskUI) {
        // Don't skip this dialog next time, if it was cancelled this time.
        window.arguments[0].doNotAsk = false;
    }
    return true;
}


