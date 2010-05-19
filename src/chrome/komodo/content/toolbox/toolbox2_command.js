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

this._get_tool_data = function(expected_type_name) {
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

this._get_tool = function(expected_type_name) {
    return this._get_tool_data(expected_type_name)[2];
};

// Commands
this.invoke_runCommand = function(event, tool) {
    if (typeof(tool) == 'undefined') {
        tool = this._get_tool('command');
        if (!tool) return;
    }
    ko.projects.runCommand(tool);
};
 
this.editProperties_runCommand = function(event, tool) {
    if (typeof(tool) == 'undefined') {
        tool = this._get_tool('command');
        if (!tool) return;
    }
    ko.projects.commandProperties(tool);
};

// DirectoryShortcuts
this.invoke_openDirectoryShortcut = function(event, tool) {
    if (typeof(tool) == 'undefined') {
        tool = this._get_tool('DirectoryShortcut');
        if (!tool) return;
    }
    ko.projects.openDirectoryShortcut(tool);
};

var peFile_bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
      .getService(Components.interfaces.nsIStringBundleService)
      .createBundle("chrome://komodo/locale/project/peFile.properties");

this.editProperties_DirectoryShortcut = function(event, tool) {
    if (typeof(tool) == 'undefined') {
        tool = this._get_tool('DirectoryShortcut');
        if (!tool) return;
    }
    // From peFile.p.js -- unexported prototype, so copy the code here, and
    // update its style.
    var obj = {
        item : tool,
        task: 'edit',
        imgsrc: 'chrome://komodo/skin/images/open.png',
        'type': 'DirectoryShortcut',
        prettytype: peFile_bundle.GetStringFromName("directoryShortcut")
    };
    window.openDialog(
        "chrome://komodo/content/project/simplePartProperties.xul",
        "Komodo:DirectoryShortcutProperties",
        "chrome,close=yes,dependent=yes,modal=yes,resizable=yes", obj);
};

// Macros

this.invoke_executeMacro = function(event, tool) {
    if (typeof(tool) == 'undefined') {
        tool = this._get_tool('macro');
        if (!tool) return;
    }
    ko.toolbox2.executeMacro(tool);
};

this.invoke_editMacro = function(event, tool) {
    if (typeof(tool) == 'undefined') {
        tool = this._get_tool('macro');
        if (!tool) return;
    }
    ko.open.URI(tool.url);
};

this.editProperties_macro = function(event, tool) {
    if (typeof(tool) == 'undefined') {
        tool = this._get_tool('macro');
        if (!tool) return;
    }
    ko.projects.macroProperties(tool);
};

// Snippets

this.invoke_insertSnippet = function(event, tool) {
    if (typeof(tool) == 'undefined') {
        tool = this._get_tool('snippet');
        if (!tool) return;
    }
    ko.projects.snippetInsert(tool);
};

this.editProperties_snippet = function(event, tool) {
    if (typeof(tool) == 'undefined') {
        tool = this._get_tool('snippet');
        if (!tool) return;
    }
    ko.projects.snippetProperties(tool);
};

// Templates
this.invoke_openTemplate = function(event, tool) {
    if (typeof(tool) == 'undefined') {
        tool = this._get_tool('template');
        if (!tool) return;
    }
    ko.views.manager.doFileNewFromTemplateAsync(tool.url);
};

// Templates can't be edited -- Komodo 5 uses the 
// file properties dialog to edit a template, which is just wrong.

// URLs
this.invoke_openURLInBrowser = function(event, tool) {
    if (typeof(tool) == 'undefined') {
        tool = this._get_tool('URL');
        if (!tool) return;
    }
    ko.browse.openUrlInDefaultBrowser(tool.value);
};

this.invoke_openURLInTab = function(event, tool) {
    if (typeof(tool) == 'undefined') {
        tool = this._get_tool('URL');
        if (!tool) return;
    }
    var docSvc = Components.classes['@activestate.com/koDocumentService;1']
    .getService(Components.interfaces.koIDocumentService);
    var doc = docSvc.createDocumentFromURI(tool.value);
    ko.views.manager.topView.createViewFromDocument(doc, 'browser', -1);
};

this.editProperties_URL = function(event, tool) {
    if (typeof(tool) == 'undefined') {
        tool = this._get_tool('URL');
        if (!tool) return;
    }
    ko.projects.URLProperties(tool);
};

// Generic functions on the hierarchy view tree

this._propertyEditorNameForToolType = {
 'command' : this.editProperties_runCommand,
 'DirectoryShortcut': this.editProperties_DirectoryShortcut,
 'macro': this.editProperties_macro,
 'snippet': this.editProperties_snippet,
 'template': this.editProperties_template,
 'URL': this.editProperties_URL,
 '__EOD__':null
};

this.editPropertiesItem = function(event) {
    var that = ko.toolbox2;
    var view = that.manager.view;
    var index = view.selection.currentIndex;
    var tool = view.getTool(index);
    var method = that._propertyEditorNameForToolType[tool.toolType];
    if (method) {
        method.call(that, event);
    } else {
        alert("Don't know how to edit properties for "
              + tool.toolType
              + " "
              + tool.name);
    }
};    

this._invokerNameForToolType = {
 'command' : this.invoke_runCommand,
 DirectoryShortcut: this.invoke_openDirectoryShortcut,
 macro : this.invoke_executeMacro,
 snippet : this.invoke_insertSnippet,
 template : this.invoke_openTemplate,
 URL : this.invoke_openURLInBrowser,
 __EOD__:null
};

this.onDblClick = function(event) {
    var that = ko.toolbox2;
    var view = that.manager.view;
    var index = view.selection.currentIndex;
    var tool = view.getTool(index);
    var method = that._invokerNameForToolType[tool.toolType];
    if (method) {
        method.call(that, event, tool);
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
