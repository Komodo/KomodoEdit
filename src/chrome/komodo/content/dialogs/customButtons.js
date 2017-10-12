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

/* Generic dialog with customizable buttons.
 *
 * Usage:
 *  All dialog interaction is done via an object passed in and out as the first
 *  window argument: window.arguments[0]. All these arguments are optional.
 *      .prompt         the question to ask.
 *      .buttons        list of strings|arrays naming buttons to use, if it's
 *                      an array, the format is [label, accesskey, tooltiptext]
 *      .response       the default response, must be one of the strings in
 *                      "buttons"
 *      .text           allows you to specify a string of text that will be
 *                      display in a non-edittable selectable text box. If
 *                      "text" is null or no specified then this textbox will
 *                      no be shown.
 *      .title          the dialog title
 *      .doNotAskUI     show the "Don't ask me again" UI
 *      .style          The class attribute to be applied to the dialog icon.
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
    var dialog = document.getElementById("dialog-custombuttons")
    gAcceptButton = dialog.getButton("accept");
    gExtra1Button = dialog.getButton("extra1");
    gExtra2Button = dialog.getButton("extra2");
    gCancelButton = dialog.getButton("cancel");
    gCancelButton.setAttribute("accesskey", "C");
    var buttonWidgets = [gAcceptButton, gExtra1Button, gExtra2Button];

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

    // .buttons
    var buttons = window.arguments[0].buttons;
    var msg = null;
    if (typeof buttons == "undefined" || buttons == null) {
        msg = "Internal Error: illegal 'buttons' value for "
                  +"Custom Buttons dialog: '"+buttons+"'.";
    } else if (buttons.length == 0 || buttons.length > 4) {
        msg = "Internal Error: illegal number of buttons for "
                  +"Custom Buttons dialog: '"+buttons.length+"'.";
    } else if (buttons.length == 4 && buttons[3] != "Cancel") {
        msg = "Internal Error: there are 4 buttons to display but "
                  +"the last one is not Cancel.";
    }
    if (msg) {
        log.error(msg);
        alert(msg);
        window.close();
    }

    var i;
    var ampIdx;
    var buttonText;
    var accesskey;
    var finalText;
    // Don't modify the incoming buttons array -- write final values into a copy
    var finalButtons = new Array(buttons.length);
    for (i = 0; i < buttons.length; i++) {
        buttonText = buttons[i];
        accesskey = null;

        /*
         Would like to use JS instanceof call, but that will fail, for example
         these expressions both return false:
            var s = 'a string'; a instanceof String;
            var a = [1, 2, 3]; a instanceof Array;
         just look for a special instance method instead to determine the type.
        */
        if (buttonText.toLowerCase /* it's a string */) {
            // See http://developer.mozilla.org/en/docs/index.php?title=XUL_Accesskey_FAQ_and_Policies&printable=yes
            // for info on specifying access keys
            ampIdx = buttonText.indexOf("&");
            if (ampIdx >= 0) {
                finalText = "";
                while (true) {
                    finalText += buttonText.substring(0, ampIdx);
                    buttonText = buttonText.substring(ampIdx + 1);
                    if (buttonText.length == 0) {
                        finalText += "&";
                        break;
                    } else if (/\w/.test(buttonText[0])) {
                        // Allow underscore and digits as well
                        if (accesskey == null) {
                            accesskey = buttonText[0]; // .toLowerCase();
                            buttonWidgets[i].setAttribute("accesskey", accesskey);
                        }
                        finalText += buttonText[0];
                        buttonText = buttonText.substring(1);
                        // Keep processing rest of string for && and &x
                    } else {
                        finalText += "&";
                        if (buttonText[0] != "&") {
                            finalText += buttonText[0];
                        }
                        buttonText = buttonText.substring(1);
                    }
                    ampIdx = buttonText.indexOf("&");
                    if (ampIdx == -1) {
                        finalText += buttonText;
                        break;
                    }
                }
                finalButtons[i] = finalText;
            } else {
                finalButtons[i] = buttons[i];
            }
        } else if (buttonText.map /* it's an array */) {
            // Array of [label, accesskey, tooltiptext], with accesskey
            // and tooltiptext being optional.
            if (buttonText.length > 1 && buttonText[1]) {
                buttonWidgets[i].setAttribute("accesskey", buttonText[1]);
                if (buttonText.length > 2 && buttonText[2]) {
                    buttonWidgets[i].setAttribute("tooltiptext", buttonText[2]);
                }
            }
            finalButtons[i] = buttonText[0];
        }
    }
    // XXX: This is not supporting a localized Cancel label.
    if (finalButtons[buttons.length-1] == "Cancel") {
        for (i = 0; i < buttons.length-1; ++i) {
            buttonWidgets[i].setAttribute("label", finalButtons[i]);
        }
        for (i = buttons.length-1; i < buttonWidgets.length; ++i) {
            buttonWidgets[i].setAttribute("collapsed", true);
        }
    } else {
        for (i = 0; i < buttons.length; ++i) {
            buttonWidgets[i].setAttribute("label", finalButtons[i]);
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
    // XXX: This is not supporting a localized Cancel label.
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


