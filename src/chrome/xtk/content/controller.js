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

/* * *
 * Contributors:
 *   David Ascher <davida@activestate.com>
 *   Shane Caraveo <shanec@activestate.com>
 */

/* -*- Mode: JavaScript; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 2 -*- */

if (typeof(xtk)=='undefined') {
    var xtk = {};
}

/*
 * Base class for controllers.  Subclasses need only implement
 * is_<command>_enabled() and do_<command>() functions for each
 * command to get basic controller functionality.

 * If a command does not have an is_<command>_enabled() function,
 * it will always be enabled.

 * If controllers need to change the response to supportsCommand() for
 * particular commands (as in checkbox commands), they can implement
 * is_<command>_supported() for those commands.
 */
xtk.Controller = function Controller() {}
xtk.Controller.prototype = {

supportsCommand: function(command) {
    var result;
    var query = "is_" + command + "_supported";
    if (query in this) {
        result = this[query]();
    } else {
        var doer = "do_" + command;
        result = doer in this;
    }
    return result;
},

isCommandEnabled: function(command) {
    var result;
    var query = "is_" + command + "_enabled";
    if (query in this) {
        result = this[query]();
    } else {
        var doer = "do_" + command;
        result = doer in this;
    }
    return result;
},

doCommand: function(command) {
    var func = "do_" + command;
    if (func in this) {
        this[func].apply(this, Array.slice(arguments, 1));
    }
},

onEvent: function(event) {
}

};

/**
 * Controller that forwards everything to sub-controllers
 * @constructor
 * @param aController {Array of (XULElement or nsIControllers or nsIController)}
 *      Array of controllers to forward to; each element may be a nsIController,
 *      or a nsIControllers (in which case the best controller is used), or a
 *      XUL element (in which case its controllers are used)
 */
xtk.ForwardingController = function ForwardingController(aControllers) {
    this.wrappedJSObject = this;
    this.commandAliases = {
        /**
         * Merge in the given alias map
         * @param aObject {Object} Hash to merge
         */
        merge: function(aObject) {
            for (let [k, v] in Iterator(aObject)) this[k] = v;
        }
    };
    if (!Array.isArray(aControllers)) {
        aControllers = [aControllers];
    }
    this._controllers = [];
    for (let controller of aControllers) {
        if (controller instanceof Components.interfaces.nsIDOMXULElement) {
            this._controllers.push(controller.controllers);
        } else if (controller instanceof Components.interfaces.nsIController ||
                   controller instanceof Components.interfaces.nsIControllers)
        {
            this._controllers.push(controller);
        } else {
            throw new Error("Invalid controller");
        }
    }
}

/**
 * Default set of aliases useful for normal text boxes; these are useful on
 * <textbox>s so that we actually do the expected things instead of editing in
 * some related <scintilla> widget.  The keys are the Komodo command names, and
 * the values are the Mozilla ones.
 */
xtk.ForwardingController.aliases_textEntry = {
    "cmd_left": "cmd_charPrevious",
    "cmd_right": "cmd_charNext",
    "cmd_home": "cmd_beginLine",
    "cmd_end": "cmd_endLine",
    "cmd_selectHome": "cmd_selectBeginLine",
    "cmd_selectEnd": "cmd_selectEndLine",
    "cmd_selectDocumentHome": "cmd_selectTop",
    "cmd_selectDocumentEnd": "cmd_selectBottom",
    "cmd_documentHome": "cmd_moveTop",
    "cmd_documentEnd": "cmd_moveBottom",
    "cmd_wordLeft": "cmd_wordPrevious",
    "cmd_wordRight": "cmd_wordNext",
    "cmd_selectWordLeft": "cmd_selectWordPrevious",
    "cmd_selectWordRight": "cmd_selectWordNext",
    "cmd_cut": "cmd_cutOrDelete",
    "cmd_deleteWordRight": "cmd_deleteWordForward",
    "cmd_deleteWordLeft": "cmd_deleteWordBackward",
    "cmd_pageUp": "cmd_movePageUp",
    "cmd_pageDown": "cmd_movePageDown",
    "cmd_back": null,
    "cmd_backSmart": null,
};

/**
 * Get the controller for a given command
 * @returns Two-element array, [controller, command name]
 * The command name returned may be different if the was mapping involved, or
 * it may be null if it's not found.
 * The returned controller will always implement the nsIController interface,
 * though it may not do anything useful if no matching controller is found.
 */
xtk.ForwardingController.prototype._getControllerForCommand =
function ForwardingController__getControllerForCommand(aCommand) {
    let defaultController = {
        /* default disabled controller if not found */
        isCommandEnabled: function(aCommand) false,
        supportsCommand: function(aCommand) false,
        doCommand: function(aCommand) {},
        onEvent: function(aEventName) {},
    };
    if (aCommand in this.commandAliases) {
        if (this.commandAliases[aCommand]) {
            let [alternate, command] = this._getControllerForCommand(this.commandAliases[aCommand]);
            if (alternate) {
                return [alternate, command];
            }
        } else {
            // disable the command
            return [defaultController, null];
        }
    }
    let flattendControllers = []
    for (let controller of this._controllers) {
        if (controller instanceof Components.interfaces.nsIControllers) {
            for (let i = 0; i < controller.getControllerCount(); ++i) {
                let subcontroller = controller.getControllerAt(i);
                if ("wrappedJSObject" in subcontroller &&
                    subcontroller.wrappedJSObject === this)
                {
                    continue;
                }
                flattendControllers.push(subcontroller);
            }
        } else {
            flattendControllers.push(controller);
        }
    }
    for (let controller of flattendControllers) {
        if (controller && controller.supportsCommand(aCommand)) {
            return [controller, aCommand];
        }
    }
    return [defaultController, null];
};

xtk.ForwardingController.prototype.isCommandEnabled =
function ForwardingController_isCommandEnabled(aCommand) {
    let [controller, command] =  this._getControllerForCommand(aCommand);
    return command && controller.isCommandEnabled(command);
};

xtk.ForwardingController.prototype.supportsCommand =
function ForwardingController_supportsCommand(aCommand) {
    let [controller, command] =  this._getControllerForCommand(aCommand);
    return command && controller.supportsCommand(command);
};

xtk.ForwardingController.prototype.doCommand =
function ForwardingController_doCommand(aCommand) {
    let [controller, command] =  this._getControllerForCommand(aCommand);
    controller.doCommand(command);
}

xtk.ForwardingController.prototype.onEvent =
function ForwardingController_onEvent(aEventName) {
    for each (let controller in this._controllers) {
        if (controller instanceof Components.interfaces.nsIControllers) {
            let controllers = [];
            for (let i = 0; i < this._controller.getControllerCount(); ++i) {
                controllers.push(this._controller.getControllerById(i));
            }
            for each (let subcontroller in controllers) {
                try {
                    subcontroller.onEvent(aEventName);
                } catch (e) {
                    Components.utils.reportError(e);
                }
            }
        } else {
            try {
                this._controller.onEvent(aEventName);
            } catch (e) {
                Components.utils.reportError(e);
            }
        }
    }
};
