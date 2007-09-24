/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

/* -*- Mode: JavaScript; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 2 -*-
 *
 * Ask the user an OK/Cancel question.
 *
 * Usage:
 *  All dialog interaction is done via an object passed in and out as the first
 *  window argument: window.arguments[0]. All these arguments are optional.
 *      .prompt         the question to ask.
 *      .response       the default response, must be "OK" or "Cancel" (or null)
 *      .text           allows you to specify a string of text that will be
 *                      display in a non-edittable selectable text box. If
 *                      "text" is null or no specified then this textbox will
 *                      no be shown.
 *      .title          the dialog title
 *      .doNotAskUI     show the "Don't ask me again" UI
 *  On return window.arguments[0] has:
 *      .response       "OK" or "Cancel"
 *      .doNotAsk       (iff .doNotAskUI) a boolean indicating if this question
 *                      need be asked again.
 *
 */

var log = ko.logging.getLogger("dialogs.okCancel");
//log.setLevel(ko.logging.LOG_DEBUG);

var gDoNotAskUI = false; // true iff "Don't ask me again" UI is being used.


//---- interface routines for XUL

function OnLoad()
{
    var dialog = document.getElementById("dialog-okcancel")
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

    // .response
    var response = window.arguments[0].response;
    if (typeof response == "undefined" || response == null) {
        response = "OK";
    }
    log.info("default response: "+response);
    switch (response) {
    case "OK":
        // "OK" button is the hardcoded default already.
        okButton.focus();
        break;
    case "Cancel":
        okButton.removeAttribute("default");
        log.debug("set Cancel button as default");
        cancelButton.setAttribute("default", "true");
        cancelButton.focus();
        break;
    default:
        //XXX Is this the kind of error handling we want to do in onload
        //    handlers?
        var msg = "Internal Error: illegal default 'response' for "
                  +"OK/Cancel dialog: '"+response+"'.";
        log.error(msg);
        alert(msg);
        window.close();
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
    }

    window.sizeToContent();
    if (opener.innerHeight == 0) { // indicator that opener hasn't loaded yet
        dialog.centerWindowOnScreen();
    } else {
        dialog.moveToAlertPosition(); // requires a loaded opener
    }
    window.getAttention();
}


function OK()
{
    window.arguments[0].response = "OK";
    if (gDoNotAskUI) {
        var checkbox = document.getElementById("doNotAsk-checkbox");
        window.arguments[0].doNotAsk = checkbox.checked;
    }
    return true;
}

function Cancel()
{
    window.arguments[0].response = "Cancel";
    if (gDoNotAskUI) {
        // Don't skip this dialog next time if it was cancelled this time.
        window.arguments[0].doNotAsk = false;
    }
    return true;
}

