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
 * Functions for accessing common and relatively generic dialogs.
 *
 * Summary of Dialogs:
 *  ko.dialogs.alert            Display an alert message with optional additional
 *                          text. (Use the plain alert() if you can.)
 *  ko.dialogs.prompt           Ask the user for a string.
 *  ko.dialogs.prompt2          Ask the user for two strings.
 *  ko.dialogs.yesNoCancel      Ask the user a Yes/No/Cancel question.
 *  ko.dialogs.yesNo            Ask the user a Yes/No question.
 *  ko.dialogs.okCancel         State a proposed action and ask the user to verify
 *                          with OK/Cancel.
 *  ko.dialogs.selectFromList   Ask the user to select from a list of strings.
 *  ko.dialogs.customButtons    Show the user some prompt and request one of a
 *                          number of responses.
 *  ko.dialogs.editEnvVar       Edit an environment variable.
 *  ko.dialogs.internalError    Notify the user of an unexpected internal error.
 *  ko.dialogs.authenticate     Username/password authentication dialog.
 *
 * Notes on common "doNotAskPref" option:
 *      Many of the ko.dialogs.*() methods in this module have a "doNotAskPref"
 *      optional argument that will result in
 *          [ ] Don't ask me again.
 *      functionality on the dialog. If the argument is null or left empty no
 *      such UI or functionality will be shown. Otherwise it is uses one or two
 *      prefs to lookup and store relevant data. Every usage will use a boolean
 *      pref of the name:
 *          donotask_<doNotAskPref>
 *      Some dialogs will also require/use a _string_ pref of the name:
 *          donotask_action_<doNotAskPref>
 *      If the boolean pref is true the dialog is NOT shown and ko.dialogs.*()
 *      will return as it did the last time the dialog was shown. See each
 *      method's documentation for details.
 *
 *      Using a new "doNotAskPref" value, say "FOO", in your code will require
 *      you to add the first or both of the following lines to
 *      default-prefs.xml:
 *          <boolean id="donotask_FOO">0</boolean>
 *          <string id="donotask_action_FOO"></string>
 *
 *      Legacy Note: Some older implementations used boolean prefs with the
 *      "dontask_" prefix (notice the slight spelling difference). The name has
 *      been changed to avoid collision.
 *
 * NOTE:
 *  Only purely generic stuff should go in here at all, since it is utilized by
 *  many XUL files!
 */


//---- globals
if (typeof(ko)=='undefined') {
    var ko = {};
}
if (typeof(ko.dialogs)=='undefined') {
    ko.dialogs = {};
}
(function() {

var log = ko.logging.getLogger("dialogs");

var _prefs = Components.classes['@activestate.com/koPrefService;1'].
                      getService(Components.interfaces.koIPrefService).prefs;



//---- public methods

// Ask the user a Yes/No/Cancel question.
//
// All arguments can be left blank or specified as null to get a default value.
//  "prompt" is question to ask.
//  "response" is the default response. This button is shown as the default.
//      Must be one of "Yes", "No", or "Cancel". If left empty of null the
//      default response is "Yes".
//  "text" allows you to specify a string of text that will be display in a
//      non-edittable selectable text box. If "text" is null or no specified
//      then this textbox will no be shown.
//  "title" is the dialog title.
//  "doNotAskPref", uses/requires the following two prefs:
//      boolean donotask_<doNotAskPref>: whether to not show the dialog
//      string donotask_action_<doNotAskPref>: "Yes" or "No"
//  "style", the class attribute to be applied to the dialog icon.
//  "helpTopic",  the help topic, to be passed to "ko.help.open()". If
//      not provided (or null) then no Help button will be shown.
//
// Returns "Yes", "No" or "Cancel", whichever the user selected.
//
this.yesNoCancel = function dialog_yesNoCancel(prompt, response, text, title,
                                               doNotAskPref, style, helpTopic)
{
    if (typeof(prompt) == 'undefined') prompt = null;
    if (typeof(response) == 'undefined') response = "Yes";
    if (typeof(text) == 'undefined') text = null;
    if (typeof(title) == 'undefined') title = null;
    if (typeof(doNotAskPref) == 'undefined') doNotAskPref = null;
    if (typeof(style) == 'undefined') style = "question-icon spaced";
    if (typeof(helpTopic) == 'undefined') helpTopic = null;

    // Break out early if "doNotAskPref" prefs so direct.
    var bpref = null, spref = null;
    if (doNotAskPref) {
        bpref = "donotask_"+doNotAskPref;
        spref = "donotask_action_"+doNotAskPref;
        if (_prefs.getBooleanPref(bpref)) {
            var action = _prefs.getStringPref(spref);
            if (action == "No" || action == "Yes") {
                return action;
            } else {
                log.error("illegal action for Yes/No/Cancel dialog in '" +
                                 spref + "' preference: '" + action + "'");
                // Reset the boolean pref.
                _prefs.setBooleanPref(bpref, false);
            }
        }
    }

    // Show the dialog.
    var obj = {};
    obj.prompt = prompt;
    obj.response = response;
    obj.text = text;
    obj.title = title;
    obj.doNotAskUI = doNotAskPref != null;
    obj.style = style;
    obj.helpTopic = helpTopic;
    window.openDialog("chrome://komodo/content/dialogs/yesNoCancel.xul",
                      "_blank",
                      "chrome,modal,titlebar,centerscreen",
                      obj);

    if (doNotAskPref && obj.doNotAsk) {
        _prefs.setBooleanPref(bpref, true);
        _prefs.setStringPref(spref, obj.response);
    }
    return obj.response;
};


// Ask the user a Yes/No question.
//
// All arguments can be left blank or specified as null to get a default value.
//  "prompt" is question to ask.
//  "response" is the default response. This button is shown as the default.
//      Must be one of "Yes" or "No". If left empty or null the default
//      response is "Yes".
//  "text" allows you to specify a string of text that will be display in a
//      non-edittable selectable text box. If "text" is null or no specified
//      then this textbox will no be shown.
//  "title" is the dialog title.
//  "doNotAskPref", uses/requires the following two prefs:
//      boolean donotask_<doNotAskPref>: whether to not show the dialog
//      string donotask_action_<doNotAskPref>: "Yes" or "No"
//  "helpTopic",  the help topic, to be passed to "ko.help.open()". If
//      not provided (or null) then no Help button will be shown.
//
// Returns "Yes" or "No", whichever the user selected. Note that cancelling the
// dialog via <Esc> (or equivalent) is taken to mean a "No" answer from the
// user; though there is a subtle difference in that the possible "Don't ask me
// again." checkbox setting is NOT honoured if the dialog is cancelled.
//
this.yesNo = function dialog_yesNo(prompt, response, text, title, doNotAskPref,
                                   helpTopic)
{
    if (typeof(prompt) == 'undefined') prompt = null;
    if (typeof(response) == 'undefined') response = null;
    if (typeof(text) == 'undefined') text = null;
    if (typeof(title) == 'undefined') title = null;
    if (typeof(doNotAskPref) == 'undefined') doNotAskPref = null;
    if (typeof(helpTopic) == 'undefined') helpTopic = null;

    // Break out early if "doNotAskPref" prefs so direct.
    var bpref = null, spref = null;
    if (doNotAskPref) {
        bpref = "donotask_"+doNotAskPref;
        spref = "donotask_action_"+doNotAskPref;
        if (_prefs.getBooleanPref(bpref)) {
            var action = _prefs.getStringPref(spref);
            if (action == "No" || action == "Yes") {
                return action;
            } else {
                log.error("illegal action for Yes/No/Cancel dialog in '" +
                                 spref + "' preference: '" + action + "'");
                // Reset the boolean pref.
                _prefs.setBooleanPref(bpref, false);
            }
        }
    }

    // Show the dialog.
    var obj = {};
    obj.prompt = prompt;
    obj.response = response;
    obj.text = text;
    obj.title = title;
    obj.doNotAskUI = doNotAskPref != null;
    obj.helpTopic = helpTopic;
    window.openDialog("chrome://komodo/content/dialogs/yesNo.xul",
                      "_blank",
                      "chrome,modal,titlebar,centerscreen",
                      obj);

    if (doNotAskPref && obj.doNotAsk) {
        _prefs.setBooleanPref(bpref, true);
        _prefs.setStringPref(spref, obj.response);
    }
    return obj.response;
};


// Ask the user a OK/Cancel question.
//
// All arguments can be left blank or specified as null to get a default value.
//  "prompt" is message to show.
//  "response" is the default response. This button is shown as the default.
//      Must be one of "OK" or "Cancel". If left empty or null the default
//      response is "OK".
//  "text" allows you to specify a string of text that will be display in a
//      non-edittable selectable text box. If "text" is null or no specified
//      then this textbox will no be shown.
//  "title" is the dialog title.
//  "doNotAskPref", uses/requires the following pref:
//      boolean donotask_<doNotAskPref>: whether to not show the dialog
//  "helpTopic",  the help topic, to be passed to "ko.help.open()". If
//      not provided (or null) then no Help button will be shown.
//
// Returns "OK" or "Cancel", whichever the user selected.
//
this.okCancel = function dialog_okCancel(prompt, response, text, title,
                                         doNotAskPref, helpTopic)
{
    if (typeof(prompt) == 'undefined') prompt = null;
    if (typeof(response) == 'undefined') response = null;
    if (typeof(text) == 'undefined') text = null;
    if (typeof(title) == 'undefined') title = null;
    if (typeof(doNotAskPref) == 'undefined') doNotAskPref = null;
    if (typeof(helpTopic) == 'undefined') helpTopic = null;

    // Break out early if "doNotAskPref" prefs so direct.
    var bpref = null;
    if (doNotAskPref) {
        bpref = "donotask_"+doNotAskPref;
        if (_prefs.getBooleanPref(bpref)) {
            return "OK";
        }
    }

    // Show the dialog.
    var obj = {};
    obj.prompt = prompt;
    obj.response = response;
    obj.text = text;
    obj.title = title;
    obj.doNotAskUI = doNotAskPref != null;
    obj.helpTopic = helpTopic;
    window.openDialog("chrome://komodo/content/dialogs/okCancel.xul",
                      "_blank",
                      "chrome,modal,titlebar,centerscreen",
                      obj);

    if (doNotAskPref && obj.doNotAsk) {
        _prefs.setBooleanPref(bpref, true);
    }
    return obj.response;
};

// Show the user some prompt and request one of a number of responses.
//
// Arguments:
//  "prompt" is message to show.
//  "buttons" is either a list of strings, each a label of a button to show, or
//      a list of array items [label, accesskey, tooltiptext], where accesskey
//      and tooltiptext are both optional.
//      Currently this is limited to three buttons, plus an optional "Cancel"
//      button. For example to mimic (mostly) ko.dialogs.yesNo use ["Yes", "No"]
//      and to mimic ko.dialogs.yesNoCancel use ["Yes", "No", "Cancel"].
//  "response" is the default response. This button is shown as the default.
//      It must be one of the strings in "buttons" or empty, in which case the
//      first button is the default.
//  "text" allows you to specify a string of text that will be display in a
//      non-edittable selectable text box. If "text" is null or no specified
//      then this textbox will not be shown.
//  "title" is the dialog title.
//  "doNotAskPref", uses/requires the following two prefs:
//      boolean donotask_<doNotAskPref>: whether to not show the dialog
//      string donotask_action_<doNotAskPref>: the name of the button pressed
//  "style", the class attribute to be applied to the dialog icon.
//
// Returns the name of the button pressed, i.e. one of the strings in
// "buttons", or "Cancel" if the dialog was cancelled (it is possible the
// cancel a dialog without a cancel button.
//
this.customButtons = function dialog_customButtons(prompt, buttons, response, text, title,
                              doNotAskPref, style)
{
    if (typeof(prompt) == 'undefined') prompt = null;
    if (typeof(buttons) == 'undefined') buttons = null;
    if (typeof(response) == 'undefined') response = null;
    if (typeof(text) == 'undefined') text = null;
    if (typeof(title) == 'undefined') title = null;
    if (typeof(doNotAskPref) == 'undefined') doNotAskPref = null;
    if (typeof(style) == 'undefined') style = "question-icon spaced";

    // Break out early if "doNotAskPref" prefs so direct.
    var bpref = null, spref = null;
    if (doNotAskPref) {
        bpref = "donotask_"+doNotAskPref;
        spref = "donotask_action_"+doNotAskPref;
        if (_prefs.getBooleanPref(bpref)) {
            return _prefs.getStringPref(spref);
        }
    }

    // Show the dialog.
    var obj = {};
    obj.prompt = prompt;
    obj.buttons = buttons;
    obj.response = response;
    obj.text = text;
    obj.title = title;
    obj.doNotAskUI = doNotAskPref != null;
    obj.style = style;
    window.openDialog("chrome://komodo/content/dialogs/customButtons.xul",
                      "_blank",
                      "chrome,modal,titlebar,centerscreen",
                      obj);

    if (doNotAskPref && obj.doNotAsk) {
        _prefs.setBooleanPref(bpref, true);
        _prefs.setStringPref(spref, obj.response);
    }
    return obj.response;
};

// Display an alert.
// NOTE: If the standard alert() meets your needs, then USE IT. Basically this
//       means that you only need the "prompt" argument. There is no point in
//       using our custom dialog when a standard one will do.
//
// All arguments can be left blank or specified as null to get a default value.
//  "prompt" is message to show.
//  "text" allows you to specify a string of text that will be display in a
//      non-edittable selectable text box. If "text" is null or no specified
//      then this textbox will no be shown.
//  "title" is the dialog title.
//  "doNotAskPref", uses/requires the following pref:
//      boolean donotask_<doNotAskPref>: whether to not show the dialog
//  "options", window.openDialog options argument, default "chrome,modal,titlebar"
//
// This function does not return anything.
//
this.alert = function dialog_alert(prompt, text, title, doNotAskPref, options)
{
    if (typeof(prompt) == 'undefined') prompt = null;
    if (typeof(text) == 'undefined') text = null;
    if (typeof(title) == 'undefined') title = null;
    if (typeof(doNotAskPref) == 'undefined') doNotAskPref = null;
    if (typeof(options) == 'undefined') options = "chrome,modal,titlebar,centerscreen";

    // Break out early if "doNotAskPref" prefs so direct.
    var bpref = null;
    if (doNotAskPref) {
        bpref = "donotask_"+doNotAskPref;
        if (_prefs.getBoolean(bpref, false)) {
            return;
        }
    }

    // Show the dialog.
    var obj = {};
    obj.prompt = prompt;
    obj.text = text;
    obj.title = title;
    obj.doNotAskUI = doNotAskPref != null;
    window.openDialog("chrome://komodo/content/dialogs/alert.xul",
                      "_blank",
                      options,
                      obj);
    if (doNotAskPref && obj.doNotAsk) {
        _prefs.setBooleanPref(bpref, true);
    }
};


// A dialog to query the user for a string in a textbox.
//
// All arguments can be left blank or specified as null to get a default value.
//  "prompt" is text to place before the input textbox.
//  "label" is a label to place on the textbox.
//  "value" is a default value for the textbox.
//  "title" is the dialog title.
//  "mruName" can be specified (a string) to get an MRU on the text box. The
//      value of the string is the namespace for the MRU.
//  "validator" is a callable object to validate the current value when the
//      user presses "OK". It is called with the current value as the only
//      argument.  If the function returns false the "OK" is ignored.
//  "multiline" is a boolean indicating that the textbox should be multiline.
//      "mruName" and "multiline" are mutually exclusive.
//  "screenX", "screenY" allow one to specify a dialog position other than
//      the alert position.
//  "tacType", "tacParam" and "tacShowCommentColumn" allow one to specify a
//      custom textbox autocomplete type and parameter. Ignored if either
//      "mruName" or "multiline" is specified.
//  "selectionStart" : index of first character of value to select
//  "selectionEnd" : point after index of last character of value to select
//      If either selectionStart or selectionEnd is null, the default is taken.
//
// It returns null if the dialog was cancelled. Otherwise it returns the value
// entered by the user.
//
// Dev Note: Not adding "doNotAsk" functionality until there is a proven need
// for it. What should the pref store: (1) a hard coded value to use?, (2) a
// special "<default>" string specifying that the given default "value" should
// just be returned?, (3) both?
//
this.prompt = function dialog_prompt(prompt, label, value, title, mruName,
                                     validator, multiline, screenX, screenY,
                                     tacType, tacParam, tacShowCommentColumn,
                                     selectionStart, selectionEnd)
{
    if (typeof(prompt) == 'undefined') prompt = null;
    if (typeof(label) == 'undefined') label = null;
    if (typeof(value) == 'undefined') value = null;
    if (typeof(title) == 'undefined') title = null;
    if (typeof(mruName) == 'undefined') mruName = null;
    if (typeof(validator) == 'undefined') validator = null;
    if (typeof(multiline) == 'undefined') multiline = null;
    if (typeof(screenX) == 'undefined') screenX = null;
    if (typeof(screenY) == 'undefined') screenY = null;
    if (typeof(tacType) == 'undefined') tacType = null;
    if (typeof(tacParam) == 'undefined') tacParam = null;
    if (typeof(tacShowCommentColumn) == 'undefined') tacShowCommentColumn = null;
    if (typeof(selectionStart) == 'undefined') selectionStart = null;
    if (typeof(selectionEnd) == 'undefined') selectionEnd = null;
    if (mruName && multiline) {
        log.warn("Cannot use both 'mruName' and 'multiline' on prompt "+
                 "dialogs. 'mruName' will be ignored.");
        mruName = null;
    }

    var obj = {};
    obj.prompt = prompt;
    obj.label = label;
    obj.value = value;
    obj.title = title;
    obj.mruName = mruName;
    obj.validator = validator;
    obj.multiline = multiline;
    obj.screenX = screenX;
    obj.screenY = screenY;
    obj.tacType = tacType;
    obj.tacParam = tacParam;
    obj.tacShowCommentColumn = tacShowCommentColumn;
    obj.selectionStart = selectionStart;
    obj.selectionEnd = selectionEnd;
    window.openDialog("chrome://komodo/content/dialogs/prompt.xul",
                      "_blank",
                      "chrome,modal,titlebar,centerscreen",
                      obj);
    if (obj.retval == "OK") {
        return obj.value;
    } else {
        return null;
    }
};


// A dialog to query the user for a string in a textbox.
//
// All arguments can be left blank or specified as null to get a default value.
//  "prompt" is text to place before the input textbox.
//  "label1" is a label to place on the first textbox.
//  "value1" is a default value for the first textbox.
//  "label2" is a label to place on the second textbox.
//  "value2" is a default value for the second textbox.
//  "title" is the dialog title.
//  "mruName1" can be specified (a string) to get an MRU on the first text box.
//      The value of the string is the namespace for the MRU.
//  "mruName2" can be specified (a string) to get an MRU on the second text box.
//      The value of the string is the namespace for the MRU.
//  "validator" is a callable object to validate the current value when the
//      user presses "OK". It is called with the current value as the only
//      argument.  If the function returns false the "OK" is ignored.
//  "multiline1" is a boolean indicating that the first textbox should be
//      multiline. "mruName1" and "multiline1" are mutually exclusive.
//  "multiline2" is a boolean indicating that the second textbox should be
//      multiline. "mruName2" and "multiline2" are mutually exclusive.
//  "screenX", "screenY" allow one to specify a dialog position other than
//      the alert position.
//
// It returns null if the dialog was cancelled. Otherwise it returns an array
// containing the two values entered by the user.
//
// Dev Note: Not adding "doNotAsk" functionality until there is a proven need
// for it. What should the pref store: (1) a hard coded value to use?, (2) a
// special "<default>" string specifying that the given default "value" should
// just be returned?, (3) both?
//
this.prompt2 = function dialog_prompt2(prompt, label1, value1, label2, value2, title,
                        mruName1, mruName2, validator, multiline1, multiline2,
                        screenX, screenY)
{
    if (typeof(prompt) == 'undefined') prompt = null;
    if (typeof(label1) == 'undefined') label1 = null;
    if (typeof(value1) == 'undefined') value1 = null;
    if (typeof(label2) == 'undefined') label2 = null;
    if (typeof(value2) == 'undefined') value2 = null;
    if (typeof(title) == 'undefined') title = null;
    if (typeof(mruName1) == 'undefined') mruName1 = null;
    if (typeof(mruName2) == 'undefined') mruName2 = null;
    if (typeof(validator) == 'undefined') validator = null;
    if (typeof(multiline1) == 'undefined') multiline1 = null;
    if (typeof(multiline2) == 'undefined') multiline2 = null;
    if (typeof(screenX) == 'undefined') screenX = null;
    if (typeof(screenY) == 'undefined') screenY = null;
    if (mruName1 && multiline1) {
        log.warn("Cannot use both 'mruName1' and 'multiline1' on prompt "+
                 "dialogs. 'mruName1' will be ignored.");
        mruName1 = null;
    }
    if (mruName2 && multiline2) {
        log.warn("Cannot use both 'mruName2' and 'multiline2' on prompt "+
                 "dialogs. 'mruName2' will be ignored.");
        mruName2 = null;
    }

    var obj = {};
    obj.prompt = prompt;
    obj.label = label1;
    obj.label2 = label2;
    obj.value = value1;
    obj.value2 = value2;
    obj.title = title;
    obj.mruName = mruName1;
    obj.mruName2 = mruName2;
    obj.validator = validator;
    obj.multiline = multiline1;
    obj.multiline2 = multiline2;
    obj.screenX = screenX;
    obj.screenY = screenY;
    window.openDialog("chrome://komodo/content/dialogs/prompt.xul",
                      "_blank",
                      "chrome,modal,titlebar,centerscreen",
                      obj);
    if (obj.retval == "OK") {
        return [ obj.value, obj.value2 ];
    } else {
        return null;
    }
};


// This dialog has the same API as the old authDialog. However it is a
// stub for ko.dialogs.authenticate2(). We should move to the later. I
// want to change the API slightly to conform more with the rest of the
// dialogs in this file.
//
// DEPRECATED. We should move to ko.dialogs.authenticate2().
this.authenticate = function dialog_authenticate(title, message, loginname, allowAnonymous,
                             allowPersist)
{
    var prompt = message;
    var username = loginname;
    return ko.dialogs.authenticate2(message, // prompt
                                       null, // server
                                       loginname, // username
                                       allowAnonymous,
                                       title, // title
                                       null); // login
};


// A dialog to get a user's username and password.
//
// All arguments can be left blank or specified as null to get a
// default value:
//  "prompt" is text to place before the input textbox.
//  "server" is the server URI to which the user is logging in.
//  "username" is a default username to start with.
//  "allowAnonymous" is a boolean indicating that the user may login
//      anonymously and to provide UI to assist with that.
//  "title" is the dialog title. Defaults to "Login As".
//  "login" is a callback to do the login. It is called when the user
//      pressed "Login". The call signature is:
//          login(server, username, password)
//      If the function returns false the "Login" is ignored.
//
// It returns null if the user cancels the dialog. Otherwise it returns
// an object with the following attributes:
//  .server        the original server passed in
//  .username   the username entered by the user
//  .password   the password entered by the user
//
this.authenticate2 = function dialog_authenticate2(prompt, server, username, allowAnonymous,
                              title, login)
{
    if (typeof(prompt) == 'undefined') prompt = null;
    if (typeof(server) == 'undefined') server = null;
    if (typeof(username) == 'undefined') username = null;
    if (typeof(allowAnonymous) == 'undefined') allowAnonymous = null;
    if (typeof(title) == 'undefined') title = null;
    if (typeof(login) == 'undefined') login = null;

    var obj = {};
    obj.prompt = prompt;
    obj.server = server;
    obj.username = username;
    obj.allowAnonymous = allowAnonymous;
    obj.title = title;
    obj.login = login;
    window.openDialog("chrome://komodo/content/dialogs/authenticate.xul",
                      "_blank",
                      "chrome,modal,titlebar,centerscreen",
                      obj);
    if (obj.retval == "Cancel") {
        return null;
    } else {
        return obj;
    }
};



// Ask the user to select from a list of strings (often a list of files/URLs).
//
// Arguments (all except "items" are optional):
//  "title" is the dialog title. If not specified (or null) a default title
//      will be used.
//  "prompt" is text to place before the listbox.
//  "items" is the list of items from which the user can choose. An "item" can
//      either simply be a string (which itself will be shown in the presented
//      listbox, or it can be a JavaScript object. If the latter, two
//      attributes are significant:
//          item.text   The string to be displayed in the listbox. (The
//                      "stringifier" argument, if used, overrides this.)
//          item.id     A string that is used to identify that particular item.
//                      This id is used in prefs when the "doNotAskPref"
//                      feature is being used.
//  "selectionCondition" is a string describing how many items can/must be
//      selected for the OK button to be enabled. The following values are
//      understood:
//          "one-or-more" (the default) requires that one or more items be
//              selected. By default all items will be selected.
//          "zero-or-more" allows any number of items to be selected. By
//              default all items will be selected.
//          "zero-or-more-default-none" allows any number of items to be
//              selected. No items are selected initially.
//          "one" only allows exactly one to be selected. By default the first
//              item will be selected.
//  "stringifier" is a function that, if non-null, will be called to stringify
//      each item for display. When your items are URIs it is common to use
//      ko.uriparse.displayPath for this argument.
//  "doNotAskPref", uses/requires the following two prefs:
//          boolean donotask_<doNotAskPref>: whether to not show the dialog
//          string donotask_action_<doNotAskPref>: "All" or "None" or item id
//      This prefs are only set in the following circumstances:
//          - selectionCondition="one-or-more" and all of the items are
//            selected (string pref set to "All")
//          - selectionCondition="zero-or-more" and all or none of the items
//            are selected (string pref set to "All" or "None")
//          - selectionCondition="one" and an item is selected (string pref set
//            to the item id or the item's string representation, see "items"
//            discussion above)
//  "yesNoCancel" is a boolean indicating that the dialog should use
//      Yes/No/Cancel buttons instead of the usual OK/Cancel. The "No" button,
//      the new one, returns an empty list for the selected items. By default
//      this is false. Note: yesNoCancel=true does not make sense if
//      selectionCondition!="zero-or-more", and an error will be raised in this
//      condition.
//  "selectedIndex" is an integer.  If given, the numbered item is selected,
//      instead of the default depending on selectionCondition
//
// It returns null if the dialog was cancelled. Otherwise it returns the list
// of selected items.
//
// Dev Note: This is getting pretty heavily burdened. Perhaps it is time for
// ko.dialogs.selectOneFromList() and ko.dialogs.selectMultiFromList().
//
this.selectFromList = function dialog_selectFromList(title, prompt, items, selectionCondition,
                               stringifier, doNotAskPref, yesNoCancel,
                               buttonNames, selectedIndex)
{
    if (typeof(title) == 'undefined') title = null;
    if (typeof(prompt) == 'undefined') prompt = null;
    if (typeof(items) == 'undefined') items = null;
    if (typeof(selectionCondition) == 'undefined') selectionCondition = "one-or-more";
    if (typeof(stringifier) == 'undefined') stringifier = null;
    if (typeof(doNotAskPref) == 'undefined') doNotAskPref = null;
    if (typeof(yesNoCancel) == 'undefined') yesNoCancel = false;
    if (typeof(buttonNames) == 'undefined') buttonNames = null;
    if (typeof(selectedIndex) == 'undefined') selectedIndex = null;

    // Break out early if "doNotAskPref" prefs so direct.
    var bpref = null, spref = null;
    if (doNotAskPref) {
        bpref = "donotask_"+doNotAskPref;
        spref = "donotask_action_"+doNotAskPref;
        if (_prefs.getBooleanPref(bpref)) {
            switch (selectionCondition) {
            case "one-or-more":
            case "zero-or-more":
                var action = _prefs.getStringPref(spref);
                if (action == "All") {
                    return items;
                } else if (action == "None") {
                    return [];
                } else {
                    log.error("illegal action for Select From List "+
                                     "dialog in '"+spref+"' preference: '"+
                                     action+"'");
                    // Reset the prefs.
                    _prefs.setBooleanPref(bpref, false);
                    _prefs.setStringPref(spref, "");
                }
                break;
            case "one":
                var id = _prefs.getStringPref(spref);
                for (var i = 0; i < items.length; ++i) {
                    var itemId = null;
                    if (typeof(items[i]) == 'string') {
                        itemId = items[i];
                    } else {
                        itemId = items[i].id;
                    }
                    if (id == itemId) {
                        return [items[i]];
                    }
                }
                log.warn("identified item, '"+id+"', for Select From "+
                                "List dialog not found in items: pref='" +
                                spref+"'")
                // Reset the prefs.
                _prefs.setBooleanPref(bpref, false);
                _prefs.setStringPref(spref, "");
                break;
            default:
                throw new Error("illegal selection condition: '"+selectionCondition+"'");
            }
        }
    }

    // Show the dialog.
    var obj = {};
    obj.title = title;
    obj.prompt = prompt;
    obj.items = items;
    obj.selectionCondition = selectionCondition;
    obj.stringifier = stringifier;
    obj.doNotAskUI = doNotAskPref != null;
    obj.yesNoCancel = yesNoCancel;
    obj.buttonNames = buttonNames;
    obj.selectedIndex = selectedIndex;
    window.openDialog("chrome://komodo/content/dialogs/selectFromList.xul",
                      "_blank",
                      "chrome,modal,titlebar,resizable=yes,centerscreen",
                      obj);

    if (doNotAskPref && obj.doNotAsk) {
        switch (selectionCondition) {
        case "one-or-more":
        case "zero-or-more":
            if (obj.selected.length == obj.items.length) {
                _prefs.setBooleanPref(bpref, true);
                _prefs.setStringPref(spref, "All");
            } else if (obj.selected.length == 0) {
                _prefs.setBooleanPref(bpref, true);
                _prefs.setStringPref(spref, "None");
            } else {
                log.error("unexpected selected list, it was not all "+
                                 "or none of the items as is required to "+
                                 "set the doNotAsk prefs");
            }
            break;
        case "one":
            _prefs.setBooleanPref(bpref, true);
            var selectedId = null;
            if (typeof(obj.selected[0]) == 'string') {
                selectedId = obj.selected[0];
            } else {
                selectedId = obj.selected[0].id;
            }
            _prefs.setStringPref(spref, selectedId);
            break;
        default:
            throw new Error("illegal selection condition: '"+selectionCondition+"'");
        }
    }
    if (obj.retval != "Cancel") {
        return obj.selected;
    } else {
        return null;
    }
}



// A dialog to query the user for a string in a textbox.
//
// All arguments can be left blank or specified as null to get a default value.
//  "name" is a default env. var. name.
//  "value" is a default env. var. value.
//  "title" is the dialog title.
//  "mruName" can be specified (a string) to get an MRU on the text box. The
//      value of the string is the namespace for the MRU. If not specified it
//      defaults to "ko.dialogs.editEnvVar". (Why not have an env var MRU be
//      default?)
//  "interpolateValues" boolean to uncollapse the interpolation shortcut menu
//
// It returns null if the dialog was cancelled. Otherwise it returns an
// object with the following attributes:
//  .name       the name entered by the user
//  .value      the value entered by the user
//
// Dev Note: a "validator" argument, a la ko.dialogs.prompt(), could easily be
// added if useful.
this.editEnvVar = function dialog_editEnvVar(name, value, title, mruName /* dialog_editEnvVar */,
                           interpolateValues)
{
    if (typeof(name) == 'undefined') name = null;
    if (typeof(value) == 'undefined') value = null;
    if (typeof(title) == 'undefined') title = null;
    if (typeof(mruName) == 'undefined' || mruName == null) mruName = "dialog_editEnvVar";
    if (typeof(interpolateValues) == 'undefined') interpolateValues = false;

    var obj = {};
    obj.name = name;
    obj.value = value;
    obj.title = title;
    obj.mruName = mruName;
    obj.interpolateValues = interpolateValues;
    window.openDialog("chrome://komodo/content/dialogs/editEnvVar.xul",
                      "_blank",
                      "chrome,modal,titlebar,resizable=yes,centerscreen",
                      obj);
    if (obj.retval == "OK") {
        return obj;
    } else {
        return null;
    }
}


// Display an internal error (and encourage the user to report it).
//
//  "error" is a short description of the error.
//  "text" is some text the user can quote in their bug report. This should
//      include the details that you would like in a bug report.
// "exception" is either an exception object, or any true value, which
//      means to pull the traceback from the logging service.
//
// This function does not return anything.
//
this.internalError = function dialog_internalError(error, text, exception)
{
    if (typeof(error) == 'undefined' || error == null)
        throw new Error("Must specify 'error' argument to ko.dialogs.internalError().");
    if (typeof(text) == 'undefined' || text == null)
        throw new Error("Must specify 'text' argument to ko.dialogs.internalError().");
    if (typeof(exception) != 'undefined' && exception) {
        text += "\n\nException: " + exception;
        var traceback = "";
        try {
            if (exception.stack) {
                traceback = exception.stack;
            } else {
                traceback = ko.logging.getStack(1);
            }
        } catch(ex) {}
        if (traceback) {
            text += "\n\nTraceback:\n" + traceback;
        }
    }
    var obj = {};
    obj.error = error;
    obj.text = text;
    window.openDialog("chrome://komodo/content/dialogs/internalError.xul",
                      "_blank",
                      "chrome,modal,titlebar,centerscreen",
                      obj);
}



// This is commonly used in dialogs that don't use the <dialog> XBL (for
// whatever reason) like so:
//    <keyset id="<some id>">
//        <key keycode="VK_ESCAPE" modifiers="" oncommand="window.close();"/>
//        <key keycode="VK_RETURN" oncommand="ko.dialogs.handleEnterKey();"/>
//    </keyset>
// Preferably, each such dialgo should be converted to use the <dialog> XBL,
// but that is not always practical.
//
this.handleEnterKey = function dialogs_handleEnterKey() {
    // 1) If button has focus, execute 'oncommand' handler
    // 2) If no button is focused, do default button (if not disabled).
    // 3) If no button is focused, and the default button is disabled, do nothing.
    // NOTE: This presumes that if a button has something to do it *is*
    // its oncommand handler (i.e. 'onclick' is no good)
    var element = document.commandDispatcher.focusedElement;
    var command = null;
    if (element && element.nodeName == "button") {
        // a button has the focus:
        // - Don't do anything, the button's oncommand handler will get
        //   called.
    } else {
        // no button has the focus:
        // - do default button's oncommand if there is one
        var buttons = document.getElementsByTagName("button");
        for (var i=0; i<buttons.length; i++) {
            var button = buttons[i];
            if (!button.disabled
                && button.hasAttribute("default")
                && buttons[i].getAttribute("default"))
            {
                command = buttons[i].getAttribute('oncommand');
            }
        }
    }
    if (command) {
        eval(command);
    }
}

this.pickIcon = function dialog_pickIcon()
{
    var obj = {};
    window.openDialog("chrome://komodo/content/dialogs/iconpicker.xul",
                      "_blank",
                      "chrome,modal,titlebar,resizable=yes,centerscreen",
                      obj);
    if (obj.retval == "OK") {
        return obj.value;
    } else {
        return null;
    }
};

var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
      .getService(Components.interfaces.nsIStringBundleService)
      .createBundle("chrome://komodo/locale/komodo.properties");

function rename_prompt_with_ext(currentName, lastDot) {
    return ko.dialogs.prompt(
                        _bundle.GetStringFromName("enterANewFilename"), // prompt
                        null, // label
                        currentName, // default
                        _bundle.GetStringFromName("renameFileOrFolder"), // title
                        null, // mruName
                        null, // validator
                        null, // multiline
                        null, // screenX
                        null, // screenY
                        null, // tacType
                        null, // tacParam
                        null, // tacShowCommentColumn
                        0, // selectionStart
                        lastDot // selectionEnd
                        );
};

function rename_prompt_no_ext(currentName, lastDot) {
    return ko.dialogs.prompt(
                             _bundle.GetStringFromName("enterANewFilename"), // prompt
                             null, // label
                             currentName, // default
                             _bundle.GetStringFromName("renameFileOrFolder")); // title
};

function filename_implies_move(name) {
    if (name.indexOf('/') != -1) return true;
    if (name.indexOf('\\') != -1) return true;
    if (name.indexOf('..') != -1) return true;
    return false;
}

// A wrapper for renaming a file by selecting only the base part,
// when there's an extension.
//
// currentName: the file's current name
// 
// returns: the new name, or null (cancel was hit)
//
this.renameFileWrapper = function(currentName) {
    var lastDot = currentName.lastIndexOf(".");
    var do_prompt = ((lastDot != -1 && lastDot < currentName.length)
                     ? rename_prompt_with_ext
                     : rename_prompt_no_ext);
    var newName;
    while (true) {
        newName = do_prompt(currentName, lastDot);
        if (!newName) return null; // cancel was hit
        if (!filename_implies_move(newName)) break;
        ko.dialogs.alert(_bundle.GetStringFromName("theFileCanBeRenamedInPlaceBut"));
    }
    return newName;
}

}).apply(ko.dialogs);
