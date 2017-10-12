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
 * Show progress for (and provide the ability to cancel) some long process.
 *
 * Usage:
 *  All input args are via an object passed in and out as the first window
 *  argument: window.arguments[0].
 *      .processor      is a object implementing koIShowsProgress. The
 *                      progress controller (koIProgressController) will be
 *                      passed to this object.
 *      .prompt         is a short description of the process that will be
 *                      carried out.
 *      .title          is the dialog title.
 *      .is_cancellable is a boolean (default true) indicating if this
 *                      process can be cancelled.
 *      .cancel_warning is a message that will be displayed warning the user
 *                      of consequences of cancelling. If not specified no
 *                      confirmation of cancel will be done.
 *
 * On return, window.arguments[0] has:
 *      .retval     One of "cancel", "error" or "ok".
 *
 * TODO: disabling cancel
 */

var log = ko.logging.getLogger("dialogs.progress");
//log.setLevel(ko.logging.LOG_DEBUG);


var gProcessor = null;
var gProgressController = null;
var gCancelButton = null;
var gCancelWarning = null;
var gCancelThreshold = 5;
var gCancelAttempts;


//---- interface routines for XUL

function OnLoad()
{
    var dialog = document.getElementById("dialog-progress");
    gCancelButton = dialog.getButton("cancel");
    gCancelButton.setAttribute("accesskey", "C");

    var is_cancellable = window.arguments[0].is_cancellable;
    if (typeof(is_cancellable) == 'undefined') is_cancellable = true;
    if (!is_cancellable) {
        gCancelButton.setAttribute("collapsed", "true");
    }
    
    // .prompt
    var promptWidget = document.getElementById("prompt");
    var prompt = window.arguments[0].prompt;
    if (typeof prompt != "undefined" && prompt != null) {
        var textUtils = Components.classes["@activestate.com/koTextUtils;1"]
                            .getService(Components.interfaces.koITextUtils);
        prompt = textUtils.break_up_words(prompt, 50);
        var textNode = document.createTextNode(prompt);
        promptWidget.appendChild(textNode);
    } else {
        promptWidget.setAttribute("collapsed", "true");
    }

    // .title
    if (typeof window.arguments[0].title != "undefined" &&
        window.arguments[0].title != null) {
        document.title = window.arguments[0].title;
    } else {
        document.title = "Komodo";
    }

    // .cancel_warning
    if (typeof window.arguments[0].cancel_warning != "undefined" &&
        window.arguments[0].cancel_warning != null) {
        gCancelWarning = window.arguments[0].cancel_warning;
    }

    window.sizeToContent();
    if (opener.innerHeight == 0) { // indicator that opener hasn't loaded yet
        dialog.centerWindowOnScreen();
    } else {
        dialog.moveToAlertPosition(); // requires a loaded opener
    }

    gProgressController = new ProgressController(is_cancellable);
    gProcessor = window.arguments[0].processor;
    gProcessor.set_controller(gProgressController);

    gCancelAttempts = 0;
}


function Cancel()
{
    
    if (!gProgressController.is_cancellable) {
        if (++gCancelAttempts < gCancelThreshold) {
            log.debug("Cancel: not cancellable, ignore");
            log.warning("Try "
                      + (gCancelThreshold - gCancelAttempts)
                      + " more time"
                      + ((gCancelThreshold - gCancelAttempts) > 1 ? "s" : "")
                      + " to really cancel\n");
            return;
        }
    } else if (gProgressController.cancelling) {
        log.debug("Cancel: already cancelling, ignore");
        return;
    } else if (gCancelWarning) {
        log.debug("Cancel: have warning message, confirm");
        var answer = ko.dialogs.customButtons("Are you sure you want to cancel? "
                                            + gCancelWarning,
                                          ["Continue", "Yes, Cancel"],
                                          "Continue");
        if (answer != "Yes, Cancel") {
            log.debug("Cancel: cancel aborted in confirmation");
            return;
        }
    }

    log.debug("Cancel: cancelling");
    gProgressController.cancelling = true;
    document.title += " (Cancelling)";
    gCancelButton.setAttribute("disabled", "true");
    gProcessor.cancel();
}


//---- Progress Controller component

function ProgressController(is_cancellable)
{
    this.log = log;
    log.debug("ProgressController()");
    try {
        this.is_cancellable = is_cancellable;
        this.cancelling = false;  // set to true when the dialog is cancelled

        this.widgets = new Object();
        this.widgets.stage = document.getElementById("stage");
        this.widgets.desc = document.getElementById("desc");
        this.widgets.progressmeter = document.getElementById("progressmeter");
    } catch(ex) {
        log.exception(ex);
    }
}
ProgressController.prototype.constructor = ProgressController;

ProgressController.prototype.QueryInterface = function(iid) {
    if (!iid.equals(Components.interfaces.koIProgressController) &&
        !iid.equals(Components.interfaces.nsISupports)) {
        throw Components.results.NS_ERROR_NO_INTERFACE;
    }
    return this;
}

ProgressController.prototype.set_stage = function(stage)
{
    this.log.debug("ProgressController.set_stage('"+stage+"')");
    try {
        this.widgets.stage.setAttribute("value", stage);
    } catch(ex) {
        this.log.exception(ex);
    }
}

ProgressController.prototype.set_desc = function(desc)
{
    this.log.debug("ProgressController.set_desc('"+desc+"')");
    try {
        this.widgets.desc.setAttribute("value", desc);
    } catch(ex) {
        this.log.exception(ex);
    }
}

ProgressController.prototype.set_progress_mode = function(mode)
{
    this.log.debug("ProgressController.set_progress_mode('"+mode+"')");
    try {
        if (mode != "determined" && mode != "undetermined") {
            throw new Error("illegal progress mode: '"+mode+"'");
        }
        this.widgets.progressmeter.setAttribute("mode", mode);
    } catch(ex) {
        this.log.exception(ex);
    }
}

ProgressController.prototype.set_progress_value = function(percent)
{
    this.log.debug("ProgressController.set_progress_value("+percent+")");
    try {
        this.widgets.progressmeter.setAttribute("value", percent);
    } catch(ex) {
        this.log.exception(ex);
    }
}

// Called by the processor to close this dialog.
ProgressController.prototype.done = function(errmsg /*=null*/, errtext /*=null*/)
{
    if (typeof(errmsg) == 'undefined') errmsg = null;
    if (typeof(errtext) == 'undefined') errtext = null;

    try {
        if (errmsg) {
            this.log.debug("ProgressController.done: error");
            ko.dialogs.alert(errmsg, errtext);
            window.arguments[0].retval = "error";
        } else if (this.cancelling) {
            this.log.debug("ProgressController.done: cancel");
            window.arguments[0].retval = "cancel";
        } else {
            this.log.debug("ProgressController.done: ok");
            window.arguments[0].retval = "ok";
        }
        window.close();
    } catch(ex) {
        this.log.exception(ex);
    }
}


