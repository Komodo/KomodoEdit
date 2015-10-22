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
 * Ask the user a Yes/No question.
 *
 * Usage:
 *  All dialog interaction is done via an object passed in and out as the first
 *  window argument: window.arguments[0]. All these arguments are optional.
 *      .prompt         the question to ask.
 *      .response       the default response, must be "Yes" or "No"
 *      .text           allows you to specify a string of text that will be
 *                      display in a non-edittable selectable text box. If
 *                      "text" is null or no specified then this textbox will
 *                      no be shown.
 *      .title          the dialog title
 *      .doNotAskUI     show the "Don't ask me again" UI
 *      .helpTopic      Help topic, to be passed to "ko.help.open()"
 *  On return window.arguments[0] has:
 *      .response       "Yes" or "No"
 *      .doNotAsk       (iff .doNotAskUI) a boolean indicating if this question
 *                      need be asked again.
 */

var log = ko.logging.getLogger("dialogs.yesNo");
//log.setLevel(ko.logging.LOG_DEBUG);

var gDoNotAskUI = false; // true iff "Don't ask me again" UI is being used.
var gHelpTopic = null;

var yes, no;


//---- interface routines for XUL

function OnLoad()
{
    yes = window.arguments[0].yes ? window.arguments[0].yes : "Yes";
    no = window.arguments[0].no ? window.arguments[0].no : "No";
    var yesA = yes.substr(0,1).toLowerCase();
    var noA = no.substr(0,1).toLowerCase();

    if ("classNames" in window.arguments[0] && window.arguments[0].classNames) {
        var classes = window.arguments[0].classNames.split(/\s+/);
        for (let c in classes)
        {
            dialog.classList.add(classes[c]);
        }
    }

    if ("hidechrome" in window.arguments[0]) {
        document.documentElement.setAttribute("hidechrome", "yes");
    }

    var dialog = document.getElementById("dialog-yesno");
    var yesButton = dialog.getButton("accept");
    var noButton = dialog.getButton("cancel");
    yesButton.setAttribute("label", yes);
    yesButton.setAttribute("accesskey", yesA);
    noButton.setAttribute("label", no);
    noButton.setAttribute("accesskey", noA);

    // .prompt
    var descWidget = document.getElementById("prompt");
    var desc = window.arguments[0].prompt;
    if (typeof desc != "undefined" && desc != null) {
        var textUtils = Components.classes["@activestate.com/koTextUtils;1"]
                            .getService(Components.interfaces.koITextUtils);
        desc = textUtils.break_up_words(desc, 50);
        var textNode = document.createTextNode(desc);
        descWidget.appendChild(textNode);
    } else {
        descWidget.setAttribute("collapsed", "true");
    }

    // .response
    var response = window.arguments[0].response;
    if (typeof response == "undefined" || response == null) {
        response = yes;
    }
    log.info("default response: "+response);
    switch (response) {
    case yes:
        // "Yes" button is the hardcoded default already.
        yesButton.focus();
        break;
    case no:
        yesButton.removeAttribute("default");
        log.debug("set No button as default");
        noButton.setAttribute("default", "true");
        noButton.focus();
        break;
    default:
        //XXX Is this the kind of error handling we want to do in onload
        //    handlers?
        var msg = "Internal Error: illegal default 'response' for "
                  +"Yes/No dialog: '"+response+"'.";
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

    // .helpTopic
    if (window.arguments[0].helpTopic) {
        var helpButton = dialog.getButton("help");
        helpButton.removeAttribute("hidden");
        helpButton.removeAttribute("disabled");
        gHelpTopic = window.arguments[0].helpTopic;
    }

    window.sizeToContent();
    if (opener.innerHeight == 0) { // indicator that opener hasn't loaded yet
        dialog.centerWindowOnScreen();
    } else {
        dialog.moveToAlertPosition(); // requires a loaded opener
    }
    //See bug 88189: on OSX, when the opener is the main ko window
    // (not a pref), tab keys are ignored, and handling of the
    // enter key doesn't look at which button has the focus.
    if (navigator.platform.match(/^Mac/)) {
        window.addEventListener("keypress", handleKeys, true);
    }
    window.getAttention();
}

function handleKeys(event) {
    var dialog = document.getElementById("dialog-yesno");
    var yesButton = dialog.getButton("accept");
    var noButton = dialog.getButton("cancel");
    switch(event.keyCode) {
        case event.DOM_VK_RETURN:
            var retFunc;
            if (yesButton.hasAttribute("default")) {
                retFunc = Yes;
            } else if (noButton.hasAttribute("default")) {
                retFunc = No;
            } else {
                retFunc = null;
                //dump("Neither has default attr???\n")
            }
            event.preventDefault();
            event.stopPropagation();
            if (retFunc) {
                retFunc();
                window.close();
            }
            break;
    }
}

function Yes()
{
    window.arguments[0].response = yes;
    if (gDoNotAskUI) {
        var checkbox = document.getElementById("doNotAsk-checkbox");
        window.arguments[0].doNotAsk = checkbox.checked;
    }
    return true;
}

function No()
{
    window.arguments[0].response = no;
    if (gDoNotAskUI) {
        var checkbox = document.getElementById("doNotAsk-checkbox");
        window.arguments[0].doNotAsk = checkbox.checked;
    }
    return true;
}

function Help()
{
    ko.windowManager.getMainWindow().ko.help.open(gHelpTopic);
    return true;
}

