/* Copyright (c) 2000-2010 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

// The "command" tool
//

if (typeof(ko)=='undefined') {
    var ko = {};
}
if (typeof(ko.toolbox2)=='undefined') {
    ko.toolbox2 = {};
}

(function() {

this.addCommand = function addCommand(item)
{
    var part = item.project.createPartFromType('command');
    part.setStringAttribute('name', "New Command");
    var obj = new Object();
    obj.part = part;
    ko.windowManager.openOrFocusDialog(
        "chrome://komodo/content/run/commandproperties.xul",
        "Komodo:CommandProperties",
        "chrome,close=yes,modal=yes,dependent=yes,centerscreen",
        obj);
    if (obj.retval == "OK") {
        if (typeof(item)=='undefined' || !item)
            item = ko.toolbox2.active.getSelectedItem();
        ko.toolbox2.addItem(part,item);
    }
}

this.commandProperties = function command_editProperties(item)
{
    var obj = {part:item};
    window.openDialog(
        "chrome://komodo/content/run/commandproperties.xul",
        "Komodo:CommandProperties",
        "chrome,close=yes,dependent=yes,modal=yes,centerscreen",
        obj);
}

this.invoke_runCommand = function(event) {
    gEvent = event;
    var view = ko.toolbox2.manager.view;
    var index = view.selection.currentIndex;
    var tool = view.getTool(index);
    if (tool.toolType != "command") {
        alert("Internal error: expected a command, but this tool is a "
              + tool.toolType);
        return;
    }
    var parseOutput = null;
    if (tool.hasAttribute("parseOutput")) {
        parseOutput = tool.getBooleanAttribute("parseOutput");
    }
    var parseRegex = null;
    if (tool.hasAttribute("parseRegex")) {
        parseRegex = tool.getStringAttribute("parseRegex");
    }
    var showParsedOutputList = null;
    if (tool.hasAttribute("showParsedOutputList")) {
        showParsedOutputList = tool.getBooleanAttribute("showParsedOutputList");
    }
    var clearOutputWindow = true;
    var terminationCallback = null;
    var saveInMRU = true;
    var saveInMacro = false;
    var viewData = {prefSet: null}; //XXX: tool.prefset};
    ko.run.runCommand(
        window,
        tool.value,
        tool.getStringAttribute("cwd"),
        stringutils_unescapeWhitespace(tool.getStringAttribute("env"), '\n'),
        tool.getBooleanAttribute("insertOutput"),
        tool.getBooleanAttribute("operateOnSelection"),
        tool.getBooleanAttribute("doNotOpenOutputWindow"),
        tool.getStringAttribute("runIn"),
        parseOutput,
        parseRegex,
        showParsedOutputList,
        tool.getStringAttribute("name"),
        clearOutputWindow,
        terminationCallback,
        saveInMRU,
        saveInMacro,
        viewData
    );
    //XXX Reinstate on tools
    //ko.macros.recordPartInvocation(tool);
};

this._get_tool = function(expected_type_name) {
     var view, index, tool;
    // See peMacro.js for handling multiple items.
    var view = ko.toolbox2.manager.view;
    var index = view.selection.currentIndex;
    var tool = view.getTool(index);
    if (tool.toolType != expected_type_name) {
        alert("Internal error: expected a "
              + expected_type_name
              + ", but this tool is a "
              + tool.toolType);
        return [view, index, null];
    }
    return [view, index, tool];
};

// Commands
this.invoke_runCommand = function(event) {
    var tool = this._get_tool('command')[2];
    if (!tool) return;
    ko.projects.runCommand(tool);
};

// Macros

this.invoke_executeMacro = function(event) {
    var view, index, tool;
    [view, index, tool] = this._get_tool('macro');
    if (!tool) return;
    ko.toolbox2.executeMacro(tool);
};

this.invoke_editMacro = function(event) {
    var view, index, tool;
    [view, index, tool] = this._get_tool('macro');
    if (!tool) return;
    ko.open.URI(tool.url);
};

// Snippets

this.invoke_insertSnippet = function(event) {
    var tool = this._get_tool('snippet')[2];
    if (!tool) return;
    ko.projects.snippetInsert(tool);
};

// Generic functions on the hierarchy view tree

this.onTreeKeyPress = function(event) {
    // If it's a return, do it.
};

this._invokerNameForToolType = {
 'command' : 'invoke_runCommand',
 macro : 'invoke_executeMacro',
 snippet : 'invoke_insertSnippet',
 __EOD__:null
};

this.onDblClick = function(event) {
    var view = ko.toolbox2.manager.view;
    var index = view.selection.currentIndex;
    var tool = view.getTool(index);
    var method = this._invokerNameForToolType[tool.toolType];
    if (method in this) {
        this[method](event);
    } else {
        alert("Don't know what to do with "
              + tool.toolType
              + " "
              + tool.name);
    }
};

this.onTreeKeyPress = function(event) {
    try {
        if (event.keyCode == event.DOM_VK_ENTER
            || event.keyCode == event.DOM_VK_RETURN)
        {
            event.cancelBubble = true;
            event.stopPropagation();
            event.preventDefault();
            this.onDblClick(event);
        }
    } catch(ex) {
        dump("onTreeKeyPress: error: " + ex + "\n");
    }
}

}).apply(ko.toolbox2);
