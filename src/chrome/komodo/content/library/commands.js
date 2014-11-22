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

/* Komodo command handling.
   This file encapsulates some of the magic we do w.r.t. command handling.
   I'm not sure I don't want to get rid of some of this, but we'll see.

   There are two public functions:

        ko.command.doCommand(command)

    and
        ko.command.updateCommandset(commandset)

 */

if (typeof(ko)=='undefined') {
    var ko = {};
}
ko.commands = {};
(function() {

var _log = ko.logging.getLogger('commands');
//_log.setLevel(ko.logging.LOG_DEBUG);
//_log.setLevel(ko.logging.LOG_INFO);

// Returns "true" is the command is a "checkbox" type command - ie,
// if supported, the "isCommandEnabled()" function determines the check-state,
// rather than the grayness of the command itself.
function _isCheckCommand(node)
{
    if (node) {
        //dump("Node: " + node + "\n");
        var t = node.getAttribute("type").toLowerCase();
        if (t == "checkbox" || t == "radio") {
            return true;
        } else {
            return node.hasAttribute("toggled");
        }
    }
    return false;
}

// XXX - Unused
//// Returns true if the command is enabled or checked.
//function _command_isCommandEnabled(id) {
//    var node = top.document.getElementById(id);
//    if (node) {
//        if (_isCheckCommand(node)) {
//            return node.getAttribute("checked")
//        }
//        return !node.getAttribute("disabled")
//    }
//    _log.warn("isCommandEnabled - no ID '" + id + "'");
//    return false;
//}

// Returns true if the command was handled (even if it is disabled),
// or false if no handler can be found, or an error occurs.
this.updateCommand = function _command_updateCommand(command, commandNode, controller /* = null */) {
    if (!command) {
        throw new Error("updateCommand called with no command!");
    }
    try {
        var found = false;
        if (controller == undefined || controller == null) {
            controller = top.document.commandDispatcher.getControllerForCommand(command);
        }

        var enabled = false;
        if (controller) {
            enabled = controller.isCommandEnabled(command);
            found = true;
        } else {
            _log.info("No controller found for command: " + command);
        }
        _log.debug("Command: " + command + " is set to " + enabled)
        ko.commands.setCommandEnabled(command, commandNode, found, enabled);
    } catch (e) {
        _log.exception(e,"doing _updateCommand: " + command + ': ');
    }
    return found;
}

this.updateCommandset = function command_updateCommandset(commandset) {
    _log.info('updateCommandset: ' + commandset.id);
    var childNodes = commandset.childNodes;
    var length = childNodes.length;
    for (var i = 0; i < length; i++) {
        var commandID = childNodes[i].id;
        if (commandID) {
            if (!ko.commands.updateCommand(commandID, childNodes[i])) {
                _log.debug("updateCommandset - " + commandset.id +
                          " - command ID '" + commandID + "' - no controller available!");
            }
        } else {
            _log.warn("updateCommandset - " + commandset.id + " - element no " + i + " has no ID!!");
        }
    }
}

this.setCommandEnabled = function _command_setCommandEnabled(id, node, supported, enabled)
{
    if ( ! node ) {
        node = top.document.getElementById(id);
    }
    if ( node ) {
        var really_enabled = supported;
        if (supported && _isCheckCommand(node)) {
            if ( enabled ) {
                node.setAttribute('checked', 'true');
                node.setAttribute('toggled', 'true');
            }
            else {
                node.removeAttribute('checked');
                node.setAttribute('toggled', 'false');
            }
        } else {
            really_enabled = enabled;
        }
        if (really_enabled)
            node.removeAttribute("disabled");
        else
            node.setAttribute('disabled', 'true');
    } else {
        _log.warn("Attempting to update command '" + id + "', but no node available");
    }
}

// Execute a bit of JS code in a manner consistent with
// executing commands -- i.e. respect whether we're in macro
// mode or in "repeat next command" mode
this.doCode = function command_doCode(cmdId, code) {
    try {
        if (cmdId instanceof Node) {
            cmdId = cmdId.getAttribute("id");
        }
        // ko.macros.recorder can be undefined if we're not in the main komodo.xul window (e.g. Rx commands)
        if (typeof(ko.macros) != 'undefined' &&
            ko.macros.recorder &&
            ko.macros.recorder.mode == 'recording') {
            ko.macros.recorder.appendCommand(cmdId);
        }
        var numRepeats = 1
        // Look for the repeat commands controller, and ask it about the repeats
        var repeatController = top.controllers.getControllerForCommand("cmd_repeatNextCommandBy");
        if (repeatController) repeatController = repeatController.wrappedJSObject;
        if (repeatController && repeatController.inRepeatCounterAccumulation) {
            numRepeats = repeatController.getCount();
            repeatController.cancelMultiHandler();
            if (numRepeats > 256) {
                dump("Repeating command " + cmdId
                                        + numRepeat + 'times...\n');
            }
        }
        for (var i = 0; i < numRepeats; i++) {
            eval(code);
        }
    } catch (e) {
        _log.exception(e,"An error occurred executing the "+code+" code fragment");
        throw Components.results.NS_ERROR_FAILURE;
    }
}

this.doCodeAsync = function command_doCodeAsync(cmdId, code) {
    try {
        window.setTimeout("ko.commands.doCode('"+cmdId + '" , "' + code.replace('\\', '\\\\', 'g')+"')", 0);
    } catch (e) {
        _log.exception(e);
    }
}

this.doCommandAsync = function command_doCommandAsync(command, event) {
    // determine if this command is executed via a keybinding, if so, just
    // do the command synchronously
    if (typeof(event) != 'undefined' && event.type == "keypress") {
        // for keybindings to work properly, we must cancel the keypress event
        // that caused this command to be issued.  This prevents a key command
        // getting executed twice.
        event.cancelBubble = true;
        event.preventDefault();
        return ko.commands.doCommand(command);
    }
    // otherwise, do this in a timeout, which prevents 'sticky' menu's and such
    window.setTimeout(function(this_) {
        try {
            this_.doCommand(command, event);
        } catch (e) {
            _log.exception(e);
        }
    }, 0, this);
    return true;
}

// Execute a command.
this.doCommand = function command_doCommand(command, options) {
    _log.debug("doCommand(" + command + ", " + JSON.stringify(options) + ")");

    var suppressExceptions = options && !!options.suppressExceptions;
    var rc = false;
    try {
        var controller = top.document.commandDispatcher.getControllerForCommand(command);
        if (controller) {
            if ("wrappedJSObject" in controller) {
                // unwrapping allows us to pass in extra arguments
                controller = controller.wrappedJSObject;
            }
            var commandNode = document.getElementById(command);
            // ko.macros.recorder can be undefined if we're not in the main komodo.xul window (e.g. Rx commands)
            if (typeof(ko.macros) != 'undefined' && ko.macros.recorder && ko.macros.recorder.mode == 'recording') {
                if (commandNode && !commandNode.hasAttribute('interactive')) {
                    ko.macros.recorder.appendCommand(command);
                }
            }
            var numRepeats = 1;
            // Look for the repeat commands controller, and ask it about the repeats
            var repeatController = top.controllers.getControllerForCommand("cmd_repeatNextCommandBy");
            if (repeatController) repeatController = repeatController.wrappedJSObject;
            if (repeatController && repeatController.inRepeatCounterAccumulation) {
                numRepeats = repeatController.getCount();
                repeatController.cancelMultiHandler();
            }
            for (var i = 0; i < numRepeats; i++) {
                if (_isCheckCommand(commandNode)) {
                    // For a check command, we do the command, then re-update it,
                    // (as presumably the state has now toggled)
                    controller.doCommand.apply(controller, Array.slice(arguments));
                    ko.commands.updateCommand(command, commandNode, controller);
                } else {
                    controller.doCommand.apply(controller, Array.slice(arguments));
                }
            }
            rc = true;
        }
        else {
            _log.info("Command " + command + " has no controller.");
            // No specific handler - just execute the code then.
            var commandNode = document.getElementById(command);
            if (commandNode && commandNode.hasAttribute("oncommand")) {
                var code = commandNode.getAttribute("oncommand");
                // Basic check to avoid recursion.
                if (!ko.stringutils.strip(code).startsWith("ko.commands.doCommand")) {
                    ko.commands.doCode(command, code);
                }
            }
        }
    } catch (e) {
        if (!suppressExceptions) {
            _log.exception(e,"An error occurred executing the "+command+" command");
            require("notify/notify").send(e, "commands", {priority: "error"});
            throw Components.results.NS_ERROR_FAILURE;
        }
    }
    return rc;
}
}).apply(ko.commands);
