/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

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
//    ko.trace.get().startTimer('    updating command: ' + command);
    try {
        var found = false;
        if (controller == undefined || controller == null) {
            controller = _getControllerForCommand(command);
        }

        var enabled = false;
        if (controller) {
            enabled = controller.isCommandEnabled(command);
            found = true;
        }
        _log.debug("Command: " + command + " is set to " + enabled)
        ko.commands.setCommandEnabled(command, commandNode, found, enabled);
    } catch (e) {
        _log.exception(e,"doing _updateCommand: " + command + ': ');
    }
//    ko.trace.get().stopTimer('    updating command: ' + command);
//    ko.trace.get().markTimer('    updating command: ' + command);
    return found;
}

this.updateCommandset = function command_updateCommandset(commandset) {
//    ko.trace.get().startTimer('updating commandset: ' + commandset.id);
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
//    ko.trace.get().stopTimer('updating commandset: ' + commandset.id);
//    ko.trace.get().markTimer('updating commandset: ' + commandset.id);
}

function _getControllerForCommand(command) {
    var commandDispatcher = top.document.commandDispatcher
    var focusedElement = commandDispatcher.focusedElement;
    var controller;

    // If html:embed tag, *must* go directly to its controller.
    // Can not use the commandDispatcher first, as some builtin commands
    // will always be satisfied, and never defer to the plugin.
    // this works in combination with our plugin events patch, which
    // must be present for the plugin to get key events in the first place
    if (focusedElement && focusedElement.parentNode &&
        (focusedElement.tagName == "html:embed")) {
        controller = focusedElement.parentNode.controllers.getControllerForCommand(command);
    }

    if (!controller)
        controller = commandDispatcher.getControllerForCommand(command);
    return controller
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
                node.setAttribute('checked', 'false');
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
        // ko.macros.recorder can be undefined if we're not in the main komodo.xul window (e.g. Rx commands)
        if (typeof(ko.macros) != 'undefined' &&
            ko.macros.recorder &&
            ko.macros.recorder.mode == 'recording') {
            ko.macros.recorder.appendCommand(cmdId);
        }
        var numRepeats = 1
        // if commands.js is included (e.g. in a dialog) but not isearch.js,
        // then ko.isearch.controller is undefined -- we obviously can't be in
        // a 'repeated command' situation
        if (typeof(ko.isearch.controller) != 'undefined' &&
            ko.isearch.controller.inRepeatCounterAccumulation) {
            numRepeats = ko.isearch.controller.getCount();
            ko.isearch.controller.cancelMultiHandler();
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
    // do the command synchrounously
    if (typeof(event) != 'undefined' && event.type == "keypress") {
        // for keybindings to work properly, we must cancel the keypress event
        // that caused this command to be issued.  This prevents a key command
        // getting executed twice.
        event.cancelBubble = true;
        event.preventDefault();
        return ko.commands.doCommand(command);
    }
    // otherwise, do this in a timeout, which prevents 'sticky' menu's and such
    try {
        window.setTimeout("ko.commands.doCommand('"+command.replace('\\', '\\\\', 'g')+"')", 0);
    } catch (e) {
        _log.exception(e);
    }
    return true;
}

// Execute a command.
this.doCommand = function command_doCommand(command) {
    _log.debug("doCommand(" + command + ")");
    var rc = false;
    try {
        var controller = _getControllerForCommand(command);
        if (controller) {
            var commandNode = document.getElementById(command);
            // ko.macros.recorder can be undefined if we're not in the main komodo.xul window (e.g. Rx commands)
            if (typeof(ko.macros) != 'undefined' && ko.macros.recorder && ko.macros.recorder.mode == 'recording') {
                if (commandNode && !commandNode.hasAttribute('interactive')) {
                    ko.macros.recorder.appendCommand(command);
                }
            }
            var numRepeats = 1
            // if commands.js is included (e.g. in a dialog) but not isearch.js,
            // then ko.isearch.controller is undefined -- we obviously can't be in
            // a 'repeated command' situation
            if (typeof(ko.isearch) != 'undefined' &&
                ko.isearch.controller.inRepeatCounterAccumulation) {
                numRepeats = ko.isearch.controller.getCount();
                ko.isearch.controller.cancelMultiHandler();
            }
            for (var i = 0; i < numRepeats; i++) {
                if (_isCheckCommand(commandNode)) {
                    // For a check command, we do the command, then re-update it,
                    // (as presumably the state has now toggled)
                    // XXX - Can have params here
                    controller.doCommand(command);
                    ko.commands.updateCommand(command, commandNode, controller)
                } else {
                    // XXX - Can have params here
                    controller.doCommand(command);
                }
            }
            rc = true;
        }
        else {
            _log.info("Command " + command + " has no controller.");
        }
    }
    catch (e) {
        _log.exception(e,"An error occurred executing the "+command+" command");
        throw Components.results.NS_ERROR_FAILURE;
    }
    return rc;
}
}).apply(ko.commands);


var command_doCommand = ko.commands.doCommand;
var command_doCommandAsync = ko.commands.doCommandAsync;
var command_updateCommandset = ko.commands.updateCommandset;
var command_doCode = ko.commands.doCode;
var command_doCodeAsync = ko.commands.doCodeAsync;

