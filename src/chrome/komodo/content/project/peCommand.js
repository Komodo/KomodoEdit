/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

// The "command" project extension.
//
// This extension manages "run command" project entries.
//

if (typeof(ko)=='undefined') {
    var ko = {};
}
if (typeof(ko.projects)=='undefined') {
    ko.projects = {};
}

(function() {
//---- The extension implementation.

function peCommand() {
    this.name = 'peCommand';
}

// The following two lines ensure proper inheritance (see Flanagan, p. 144).
peCommand.prototype.constructor = peCommand;

peCommand.prototype.init = function() {
}

peCommand.prototype.registerCommands = function() {
    ko.projects.extensionManager.registerCommand('cmd_runCommand', this);
}

peCommand.prototype.registerEventHandlers = function() {
    ko.projects.extensionManager.addEventHandler(Components.interfaces.koIPart_command,
                                     'ondblclick', this);
}

peCommand.prototype.registerMenus = function() {
    ko.projects.extensionManager.createMenuItem(Components.interfaces.koIPart_command,
                                    'Run', 'cmd_runCommand',
                                    null,
                                    null,
                                    true);
}

peCommand.prototype.ondblclick = function(item,event) {
    if (item.type != 'command') return;
    ko.projects.runCommand(item);
}

peCommand.prototype.supportsCommand = function(command, part) {
    var view = ko.projects.active;
    if (!view) return false;
    //dump("supportsCommand for " + command +'\n');
    switch (command) {
    case 'cmd_runCommand':
        var items = ko.projects.active.getSelectedItems();
        if (items.length == 1 && items[0]
            && items[0].type == 'command') {
            return true;
        } else {
            return false;
        }
    default:
        break;
    }
    return false;
}

peCommand.prototype.isCommandEnabled = peCommand.prototype.supportsCommand;

peCommand.prototype.doCommand = function(command) {
    var item = null;
    switch (command) {
    case 'cmd_runCommand':
        item = ko.projects.active.getSelectedItem();
        ko.projects.runCommand(item);
        break;
    default:
        break;
    }
}

// this is hidden away now, no namespce, the registration keeps the reference
// we need
ko.projects.registerExtension(new peCommand());
}).apply();


(function() {


this.addCommand = function peCommand_addCommand(item)
{
    var part = item.project.createPartFromType('command');
    part.setStringAttribute('name', "New Command");
    var obj = new Object();
    obj.part = part;
    ko.windowManager.openOrFocusDialog(
        "chrome://komodo/content/run/commandproperties.xul",
        "Komodo:CommandProperties",
        "chrome,close=yes,modal=yes,dependent=yes", obj);
    if (obj.retval == "OK") {
        if (typeof(item)=='undefined' || !item)
            item = ko.projects.active.getSelectedItem();
        ko.projects.addItem(part,item);
    }
}

this.commandProperties = function command_editProperties(item)
{
    var obj = new Object();
    obj.part = item;
    window.openDialog(
        "chrome://komodo/content/run/commandproperties.xul",
        "Komodo:CommandProperties",
        "chrome,close=yes,dependent=yes,modal=yes", obj);
}

this.runCommand = function Run_CommandPart(cmdPart) {
    // Have to guard against new (since Komodo 2.0.0 release) command
    // attributes not being defined.
    var parseOutput = null;
    if (cmdPart.hasAttribute("parseOutput")) {
        parseOutput = cmdPart.getBooleanAttribute("parseOutput");
    }
    var parseRegex = null;
    if (cmdPart.hasAttribute("parseOutput")) {
        parseRegex = cmdPart.getStringAttribute("parseRegex");
    }
    var showParsedOutputList = null;
    if (cmdPart.hasAttribute("parseOutput")) {
        showParsedOutputList = cmdPart.getBooleanAttribute("showParsedOutputList");
    }
    var clearOutputWindow = true;
    var terminationCallback = null;
    var saveInMRU = true;
    var saveInMacro = false;
    var viewData = {};
    viewData.prefSet = cmdPart.prefset;
    ko.run.runCommand(
        window,
        cmdPart.value,
        cmdPart.getStringAttribute("cwd"),
        stringutils_unescapeWhitespace(cmdPart.getStringAttribute("env"), '\n'),
        cmdPart.getBooleanAttribute("insertOutput"),
        cmdPart.getBooleanAttribute("operateOnSelection"),
        cmdPart.getBooleanAttribute("doNotOpenOutputWindow"),
        cmdPart.getStringAttribute("runIn"),
        parseOutput,
        parseRegex,
        showParsedOutputList,
        cmdPart.getStringAttribute("name"),
        clearOutputWindow,
        terminationCallback,
        saveInMRU,
        saveInMacro,
        viewData
    );
    ko.macros.recordPartInvocation(cmdPart);
}

}).apply(ko.projects);

var peCommand_addCommand = ko.projects.addCommand;
var command_editProperties = ko.projects.commandProperties;
var Run_CommandPart = ko.projects.runCommand;
