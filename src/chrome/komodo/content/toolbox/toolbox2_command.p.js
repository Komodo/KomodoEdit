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
 * Portions created by ActiveState Software Inc are Copyright (C) 2000-2012
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

// The "command" tool
//

if (typeof(ko)=='undefined') {
    var ko = {};
}
if (typeof(ko.toolbox2)=='undefined') {
    ko.toolbox2 = {};
}

(function() {

var log = ko.logging.getLogger("toolbox");

var osSvc = (Components.classes["@activestate.com/koOs;1"]
             .getService(Components.interfaces.koIOs));
var osPathSvc = (Components.classes["@activestate.com/koOsPath;1"]
             .getService(Components.interfaces.koIOsPath));
    
this._getSelectedTool = function(assertOfType /* =type */) {
    var view = ko.toolbox2.manager.view;
    var tool = view.getTool(view.selection.currentIndex);
    if (assertOfType && tool.type != assertOfType) {
        /* Note: This whole "assertOfType" is just a dev sanity check. Can be pulled out sometime. */
        alert("Internal error: expected a "
              + expectedTypeName
              + ", but this tool is a "
              + tool.type);
        return null;
    }
    return tool;
};

// Commands
this.invoke_runCommand = function(tool) {
    if (typeof(tool) == 'undefined') {
        tool = this._getSelectedTool('command');
        if (!tool) return;
    }
    ko.projects.runCommand(tool);
};

this.editProperties_command = function(tool) {
    if (typeof(tool) == 'undefined') {
        tool = this._getSelectedTool('command');
        if (!tool) return;
    }
    ko.projects.commandProperties(tool);
};

this.add_command = function(parent, item) {
    // Code from peCommand.addCommand, since enough of it will change.
    item.setStringAttribute('name', "New Command");
    var obj = {
        part:item,
        task:'new'
    };
    ko.windowManager.openOrFocusDialog(
        "chrome://komodo/content/run/commandproperties.xul",
        "Komodo:CommandProperties",
        "chrome,close=yes,modal=yes,dependent=yes,centerscreen",
        obj);
    if (obj.retval == "OK") {
        this.addNewItemToParent(item, parent);
    }
};

var peFolder_bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
      .getService(Components.interfaces.nsIStringBundleService)
      .createBundle("chrome://komodo/locale/project/peFolder.properties");
var komodo_bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
      .getService(Components.interfaces.nsIStringBundleService)
      .createBundle("chrome://komodo/locale/komodo.properties");

// Macros

this.invoke_executeMacro = function(tool) {
    if (typeof(tool) == 'undefined') {
        tool = this._getSelectedTool('macro');
        if (!tool) return;
    }
    ko.projects.executeMacro(tool, tool.getBooleanAttribute('async'));
};

this.invoke_editMacro = function(tool) {
    if (typeof(tool) == 'undefined') {
        tool = this._getSelectedTool('macro');
        if (!tool) return;
    }
    ko.open.URI(tool.url);
};

this.editProperties_macro = function(tool) {
    if (typeof(tool) == 'undefined') {
        tool = this._getSelectedTool('macro');
        if (!tool) return;
    }
    ko.projects.macroProperties(tool);
};

this.add_macro = function(parent, item) {
    ko.projects.addMacro(parent, item);
};

// Menus

this.add_menu = function(parent, item) {
    ko.projects.addMenu(parent, item);
};

this.editProperties_menu = function(tool) {
    if (typeof(tool) == 'undefined') {
        tool = this._getSelectedTool('menu');
        if (!tool) return;
    }
    ko.projects.menuProperties(tool);
};

// Snippets

this.invoke_insertSnippet = function(tool) {
    if (typeof(tool) == 'undefined') {
        tool = this._getSelectedTool('snippet');
        if (!tool) return;
    }
    if (!tool.value) {
        // Bug 98835: initially, we don't always have the item's text
        // Don't know why, but getting its value will make an initial
        // call to the database to init the tool
        var koFileEx = tool.getFile();
        koFileEx.open("r");
        tool.value = koFileEx.readfile();
        koFileEx.close();
    }
    ko.projects.snippetInsert(tool);
};

this.invoke_editSnippet = function(tool) {
    if (typeof(tool) == 'undefined') {
        tool = this._getSelectedTool('snippet');
        if (!tool) return;
    }
    ko.open.URI(tool.url);
};

this.editProperties_snippet = function(tool) {
    if (typeof(tool) == 'undefined') {
        tool = this._getSelectedTool('snippet');
        if (!tool) return;
    }
    ko.projects.snippetProperties(tool);
};

this.add_snippet = function(parent, item) {
    ko.projects.addSnippet(parent, item);
};

// Templates
this.invoke_openTemplate = function(tool) {
    if (typeof(tool) == 'undefined') {
        tool = this._getSelectedTool('template');
        if (!tool) return;
    }
    ko.views.manager.doFileNewFromTemplateAsync(tool.url);
};

this.add_template = function(parent, item) {
    // ref code peTemplate.js::addTemplate
    var obj = { type:'file',
                templateOnly:true
    };
    ko.launch.newTemplate(obj);
    if (obj.template == null) return;
    // Avoid multiple calls to uriparse.*
    var templateName = ko.uriparse.baseName(obj.template);
    item.setStringAttribute('name', templateName);
    item.value = ko.uriparse.localPathToURI(obj.template);
    this.addNewItemToParent(item, parent);
};

// Toolbars

this.add_toolbar = function(parent, item) {
    ko.projects.addToolbar(parent, item);
};

this.editProperties_toolbar = function(tool) {
    if (typeof(tool) == 'undefined') {
        tool = this._getSelectedTool('toolbar');
        if (!tool) return;
    }
    ko.projects.menuProperties(tool);
}

// Templates can't be edited -- Komodo 5 uses the 
// file properties dialog to edit a template, which is just wrong.

// URLs
this.invoke_openURLInBrowser = function(tool) {
    if (typeof(tool) == 'undefined') {
        tool = this._getSelectedTool('URL');
        if (!tool) return;
    }
    ko.browse.openUrlInDefaultBrowser(tool.value);
};

this.invoke_openURLInTab = function(tool) {
    if (typeof(tool) == 'undefined') {
        tool = this._getSelectedTool('URL');
        if (!tool) return;
    }
    ko.views.manager.doFileOpenAsync(tool.value, 'browser');
};

this.editProperties_URL = function(tool) {
    if (typeof(tool) == 'undefined') {
        tool = this._getSelectedTool('URL');
        if (!tool) return;
    }
    ko.projects.URLProperties(tool);
};

this.add_URL = function(parent, item) {
    ko.projects.addURL(parent, item);
};

// folders
this.add_folder = function(parent, item) {
    var basename = ko.dialogs.prompt(peFolder_bundle.GetStringFromName("enterFolderName"));
    if (!basename) return;
    item.setStringAttribute('name', basename);
    this.addNewItemToParent(item, parent);
};

// Templates can't be edited -- Komodo 5 uses the 
// file properties dialog to edit a template, which is just wrong.

// Generic functions on the hierarchy view tree

this.addToolboxItem_common = function(parent, itemType) {
    try {
        var method = this["add_" + itemType];
        if (!method) {
            alert("toolbox2_command.js internal error: Don't know how to create a new "
                  + itemType);
            return;
        }
        var item = this.manager.toolsMgr.createToolFromType(itemType);
        method.call(this, parent, item);
    } catch(ex) {
        ko.dialogs.alert("toolbox2_command.js: Internal error: Trying to add a new "
                         + itemType
                         + ": "
                         + ex);
    }
}

this.addToolboxItem = function(itemType) {
    var parent;
    if (this._clickedOnRoot()) {
        parent = this.manager.toolbox2Svc.getStandardToolbox();
    } else {
        var view = this.manager.view;
        var index = view.selection.currentIndex;
        parent = view.getTool(index);
    }
    this.addToolboxItem_common(parent, itemType);
};

this.addToolboxItemToStdToolbox = function(itemType) {
    var parent = this.manager.toolbox2Svc.getStandardToolbox();
    this.addToolboxItem_common(parent, itemType);
};

// Generic top-level routines

this._clickedOnRoot = function() {
    return (this.manager.view.selection.count == 0
            && document.popupNode
            && document.popupNode.id == "toolbox2-hierarchy-treebody");
};

this._determineTargetDirectory_CallMethod = function(method) {
    var view = this.manager.view;
    var index;
    var defaultDirectory;
    if (this._clickedOnRoot()) {
        index = -1;  // For the std toolbox
        defaultDirectory = this.manager.toolbox2Svc.getStandardToolbox().path;
    } else {
        index = view.selection.currentIndex;
        defaultDirectory = view.getPathFromIndex(index);
    }
    method.call(this, defaultDirectory, index);
 };

this.importFilesFromFileSystem_common = function(defaultDirectory, index) {
    var title = komodo_bundle.GetStringFromName("selectFilesToImportToolbox");
    var defaultFilename = null;
    var defaultFilterName = "Komodo Tool";
    var filterNames = [defaultFilterName, "Zip", "All"]
    var paths = ko.filepicker.browseForFiles(defaultDirectory, defaultFilename,
                                        title,
                                        defaultFilterName, filterNames);
    if (!paths) {
        return;
    }
    try {
        this.manager.toolbox2Svc.importFiles(defaultDirectory, paths.length, paths);
        this.manager.view.reloadToolsDirectoryView(index);
    } catch(ex) {
        var msg = komodo_bundle.formatStringFromName("importFilesFromFileSystemFailed.template", [ex], 1);
        this.log.exception(msg);
        alert(msg);
    }
};

this.importFilesFromFileSystem = function(event) {
    ko.toolbox2._determineTargetDirectory_CallMethod(this.importFilesFromFileSystem_common);
}

this.importFolderFromFileSystem_common = function(defaultDirectory, index) {
    var title = komodo_bundle.GetStringFromName("selectFolderOfToolsToImport");
    var path = ko.filepicker.getFolder(defaultDirectory, title);
    if (!path) {
        return;
    }
    try {
        this.manager.toolbox2Svc.importDirectory(defaultDirectory, path);
        this.manager.view.reloadToolsDirectoryView(index);
    } catch(ex) {
        var msg = komodo_bundle.formatStringFromName("importFolderFromFileSystemFailed.template", [ex], 1);
        this.log.exception(msg);
        alert(msg);
    }
};

this.importFolderFromFileSystem = function(event) {
    ko.toolbox2._determineTargetDirectory_CallMethod(this.importFolderFromFileSystem_common);
}

this.importPackage_common = function(targetDirectory, index) {
    var prompt = komodo_bundle.GetStringFromName("specifyURLThatContainsAPackageFile");
    var label = "URL";
    var value = "";
    var title = komodo_bundle.GetStringFromName("importVersion5Package");
    var defaultDirectory = null;
    var defaultFilename = null;
    
    var path = ko.filepicker.browseForFile(defaultDirectory, defaultFilename,
                                      title,
                                      "Komodo Package", // default filter
                                      ["Komodo Package", "All"]); // filters
    if (!path) {
        return;
    }
    try {
        this.manager.toolbox2Svc.importV5Package(targetDirectory, path);
        this.manager.view.reloadToolsDirectoryView(index);
    } catch(ex) {
        var msg = komodo_bundle.formatStringFromName("importPackageFailed.template", [ex], 1);
        this.log.exception(msg);
        alert(msg);
    }
};

this.importPackage = function(event) {
    ko.toolbox2._determineTargetDirectory_CallMethod(this.importPackage_common);
};
 
this._webPackageURL = "";
this.importPackageFromWeb_common = function(targetDirectory, index) {
    var prompt = komodo_bundle.GetStringFromName("specifyURLThatContainsAPackageFile");
    var label = "URL";
    var value = this._webPackageURL;
    var title = komodo_bundle.GetStringFromName("extractAPackageFromTheWeb");
    var url = ko.dialogs.prompt(prompt, label, value, title);
    if (!url) {
        return;
    }
    this._webPackageURL = url;
    try {
        this.manager.toolbox2Svc.importV5Package(targetDirectory, url);
        this.manager.view.reloadToolsDirectoryView(index);
    } catch(ex) {
        var msg = "importPackageFromWeb failed: " + ex;
        this.log.exception(msg);
        alert(msg);
    }
};

this.importPackageFromWeb = function(event) {
    ko.toolbox2._determineTargetDirectory_CallMethod(this.importPackageFromWeb_common);
};

// Routines that import into the top-level standard toolbox
// These are called by changing the menu item commands in
// ko.toolbox2.Toolbox2Manager._fixCogPopupmenu

this.importFilesFromFileSystem_toStdToolbox = function(event) {
    this.importFilesFromFileSystem_common(this.manager.toolbox2Svc.getStandardToolbox().path, -1);
};

this.importFolderFromFileSystem_toStdToolbox = function(event) {
    var targetDirectory = this.manager.toolbox2Svc.getStandardToolbox().path;
    this.importFolderFromFileSystem_common(targetDirectory, -1);
};

this.importPackage_toStdToolbox = function(event) {
    var targetDirectory = this.manager.toolbox2Svc.getStandardToolbox().path;
    this.importPackage_common(targetDirectory, -1);
};
 
this.importPackageFromWeb_toStdToolbox = function(event) {
    var targetDirectory = this.manager.toolbox2Svc.getStandardToolbox().path;
    this.importPackageFromWeb_toStdToolbox_common(targetDirectory, -1);
};

this.editPropertiesItem = function(event) {
    var view = ko.toolbox2.manager.view;
    var tool = view.getTool(view.selection.currentIndex);
    this.editPropertiesTool(tool);
};

this.renameItem = function(event) {
    var this_ = ko.toolbox2;
    var view = this_.manager.view;
    var index = view.selection.currentIndex;
    var prompt, text, title;
    var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
    .getService(Components.interfaces.nsIStringBundleService)
    .createBundle("chrome://komodo/locale/komodo.properties");
    if (index == -1) {
        var title = _bundle.GetStringFromName("errorTryingRenameTool");
        var text = _bundle.GetStringFromName("noItemSelectedRename");
        prompt = null;
        ko.dialogs.alert(prompt, text, title);
    }
    var tool = view.getTool(index);
    var oldName = tool.name;
    prompt = _bundle.GetStringFromName("enterANewFilename");
    var label = null;
    var value = tool.name;
    title = _bundle.GetStringFromName("renameFileOrFolder");
    var mruName = null;
    var validator = function(window, suggestedValue) {
        if (!suggestedValue) {
            alert(_bundle.GetStringFromName("toolNameCannotBeEmpty"));
            return false;
        } else if (/^\s+$/.test(suggestedValue)) {
            alert(_bundle.GetStringFromName("toolNameShouldContainNonSpaceCharacters"));
        }
        return true;
    };
    var newName = ko.dialogs.prompt(
        prompt,
        label,
        value,
        title,
        null, // mruName
        validator,
        null, // multiline
        null, // screenX
        null, // screenY
        null, // tacType
        null, // tacParam
        null, // tacShowCommentColumn
        0, // selectionStart
        oldName.length // selectionEnd
                                    );
    if (!newName) {
        return;
    }
    try {
        view.renameTool(index, newName);
    } catch(ex) {
        title = _bundle.GetStringFromName("errorTryingRenameTool");
        prompt = null;
        text = ex.message;
        ko.dialogs.alert(prompt, text, title);
    }
}

this._selectCurrentItems = function(isCopying) {
    var paths, pathList;
    if (this._clickedOnRoot()) {
        if (!isCopying) {
            var msg = peFolder_bundle.GetStringFromName("cantCutStandardToolbox");
            ko.dialogs.alert(msg);
            return;
        }
        pathList = this.manager.toolbox2Svc.getStandardToolbox().path;
        paths = [pathList];
    } else {
        this.selectedIndices = this.getSelectedIndices(/*rootsOnly=*/true);
        var paths = this.getToolboxResolvedPaths(this.selectedIndices);
        pathList = paths.join("\n");
    }
    var uriList = paths.map(ko.uriparse.localPathToURI).join("\n");
    var transferable = xtk.clipboard.addTextDataFlavor("text/uri-list", uriList);
    xtk.clipboard.addTextDataFlavor("text/unicode", pathList, transferable);
    xtk.clipboard.addTextDataFlavor("text/plain", pathList, transferable);
    xtk.clipboard.addTextDataFlavor("x-application/komodo-toolbox",
                                    isCopying ? "1" : "0" , transferable);
    xtk.clipboard.copyFromTransferable(transferable);
    window.setTimeout(window.updateCommands, 1, "clipboard");
}

this.cutItem = function(event) {
    if (this._clickedOnRoot()) {
        // Don't allow the standard toolbox to be "cut"
        require("notify/notify").send(msg, "toolbox", {priority: "warning"});

        return;
    }
    this._selectCurrentItems(false);
};

this.copyItem = function(event) {
    if (typeof(event) == "undefined") event = null;
    this._selectCurrentItems(true);
};

this.getContainerForIndex = function(index) {
    if (index != -1 && !this.manager.view.isContainer(index)) {
        // Get the parent (or the std toolbox) and use that
        var parentIndex = this.manager.view.getParentIndex(index);
        if (this.manager.view.isContainer(parentIndex)) {
            return parentIndex;
        } else if (this.manager.view.getLevel(index) == 0
                   && (this.manager.view.getImageSrc(index, None)
                       != 'chrome://fugue/skin/icons/toolbox.png')) {
            // It's a top-level node in the std toolbox?
            dump("Looks like we're dropping into the std toolbox\n");
            return -1;
        }
    }
    return index;
};

this.pasteIntoItem = function(event) {
    if (typeof(event) == "undefined") event = null;
    try {
        var view = this.manager.view;
        var index = this._clickedOnRoot() ?  -1 : view.selection.currentIndex;
        index = this.getContainerForIndex(index);
        var paths = xtk.clipboard.getText().split("\n");
        var isCopying = true;
        if (xtk.clipboard.containsFlavors(["x-application/komodo-toolbox"])) {
            isCopying = parseInt(xtk.clipboard.getTextFlavor("x-application/komodo-toolbox"));
        }
        if (isCopying && paths.length == 1) {
            var container = this.getContainerFromIndex(index);
            var targetDirectory = container.path;
            var newPath = osPathSvc.join(targetDirectory, osPathSvc.basename(paths[0]));
            if (osPathSvc.exists(newPath) && !osPathSvc.isdir(newPath)) {
                var fixedPath = this._getUniqueFileName(targetDirectory, newPath);
                if (!fixedPath) {
                    return;
                } else if (fixedPath != newPath) {
                    view.copyItemIntoTargetWithNewName(index, paths[0], osPathSvc.basename(fixedPath));
                    return;
                }
            }
        }
        view.pasteItemsIntoTarget(index, paths, paths.length, isCopying);
        if (!isCopying) {
            this._removeLoadedMacros(this._getLoadedMacros(paths));
        }
    } catch(ex) {
        ko.dialogs.alert("toolbox2_command.js: Error: Trying to copy paths into the toolbox: "
                         + ex);
    }
};

this._getUniqueFileName = function(targetDirectory, newPath) {
    if (!osPathSvc.exists(newPath)) {
        return newPath;
    }
    var newName, selectionStart, selectionEnd;
    [newName, selectionStart, selectionEnd] =
        this._getNewSuggestedName(osPathSvc.basename(newPath), targetDirectory);
    var suffix = ".komodotool"
    if (newName.indexOf(suffix) > -1) {
        newName = newName.substring(0, newName.length - suffix.length);
    }
    newName = ko.dialogs.prompt("Enter the basename for the new tool",
                                "Filename:", newName, "A tool exists with this name",
                                null, // mruName
                                null, // validator
                                null, // multiline
                                null, // screenX
                                null, // screenY
                                null, // tacType
                                null, // tacParam
                                null, // tacShowCommentColumn
                                selectionStart,
                                selectionEnd
                                );
    if (!newName) return null;
    if (newName.indexOf(suffix) == -1) {
        newName += suffix;
    }
    return osPathSvc.join(targetDirectory, newName);
};

this._getNewSuggestedName = function(srcBaseName, targetDirPath) {
    var newName, selectionStart, selectionEnd;
    var copyPart = "_Copy";
    var ptn = new RegExp('^(.*?)(?:(' + copyPart + ')(?:_(\\d+))?)?(\\..*)?$');
    var m = ptn.exec(srcBaseName);
    if (!m) {
        newName = srcBaseName + copyPart;
        selectionStart = srcBaseName.length;
        selectionEnd = newName.length;
    } else {
        var i = 0;
        var saneLimit = 1000; // prevent runaway loop, if code hits this hard.
        while (true) {
            if (m[4] === undefined) m[4] = "";
            if (m[3] !== undefined) {
                newName = m[1] + m[2] + "_" + (parseInt(m[3]) + 1) + m[4];
            } else if (m[2] !== undefined) {
                newName = m[1] + m[2] + "_2" + m[4];
            } else {
                newName = m[1] + copyPart + m[4];
            }
            i += 1;
            if (i >= saneLimit || !osPathSvc.exists(osPathSvc.join(targetDirPath, newName))) {
                selectionStart = m[1].length;
                selectionEnd = newName.length - m[4].length;
                break;
            }
            m = ptn.exec(newName);
            if (!m) {
                selectionStart = newName.length;
                newName += copyPart;
                selectionEnd = newName.length;
                break;
            }
        }
    }
    return [newName, selectionStart, selectionEnd];
};

this._getLoadedMacros = function(paths) {
    var toolsMgr = this.manager.toolsMgr;
    var cleanMacros = [];
    var dirtyMacros = [];
    var viewsManager = ko.views.manager;
    for (var i = 0; i < paths.length; i++) {
        var path = paths[i];
        var tool = toolsMgr.getToolFromPath(path);
        if (tool && tool.type == 'macro') {
            var url = tool.url;
            var v = viewsManager.getViewForURI(url);
            if (v) {
                if (v.isDirty) {
                    dirtyMacros.push(url);
                } else {
                    cleanMacros.push(url);
                }
            }
        }
    }
    if (dirtyMacros.length) {
        var title = "Save unchanged macros?";
        var prompt = "Some of the macros to move are loaded in the editor with unsaved changes";
        var selectionCondition = "zero-or-more";
        var i = 0;      
        var itemsToSave = ko.dialogs.selectFromList(title, prompt, dirtyMacros, selectionCondition);
        for (i = 0; i < itemsToSave.length; i++) {
            var url = itemsToSave[i];
            var v = viewsManager.getViewForURI(url);
            if (v) {
                v.save(true /* skipSccCheck */);
            }
            cleanMacros.push(url);
        }
    }
    return cleanMacros;
};

this._removeLoadedMacros = function(loadedMacroURIs) {
    loadedMacroURIs.map(function(uri) {
            var v = ko.views.manager.getViewForURI(uri);
            if (v) {
                v.closeUnconditionally();
            }
        });
};

this.showInFileManager = function(itemType) {
    try {
        var path;
        if (this._clickedOnRoot()) {
            path = this.manager.toolbox2Svc.getStandardToolbox().path;
        } else {
            var view = ko.toolbox2.manager.view;
            var index = view.selection.currentIndex;
            path = view.getPathFromIndex(index);
        }
        var sysUtilsSvc = Components.classes["@activestate.com/koSysUtils;1"].
        getService(Components.interfaces.koISysUtils);
        sysUtilsSvc.ShowFileInFileManager(path);
    } catch(ex) {
        ko.dialogs.alert("toolbox2_command.js: Internal error: Trying to show "
                         + path
                         + " in a file manager window: "
                         + ex);
    }
};

var default_saveToolDirectory = null;

this.saveToolsAs = function(event) {
    try {
        var numFiles, numFolders;
        [numFiles, numFolders] = this.saveToolsAs_aux(event);
        // Who cares about (s) -- it's only a statusbar msg
        var msg = peFolder_bundle.formatStringFromName("copied_X_Files_Y_Folders",
                                 [numFiles,
                                  numFolders], 2);
        require("notify/notify").send(msg, "toolbox");
    } catch(ex) {
        alert(ex);
    }
};

this.saveToolsAs_aux = function(event) {
    var this_ = ko.toolbox2;
    var selectedIndices = this_.getSelectedIndices(/*rootsOnly=*/true);
    if (selectedIndices.length == 0) return [0, 0]; // shouldn't happen
    var toolTreeView = this_.manager.view;
    var askForFile = (selectedIndices.length == 1
                      && !toolTreeView.isContainer(selectedIndices[0]));
    var targetPath;
    var shutil = Components.classes["@activestate.com/koShUtil;1"].
                getService(Components.interfaces.koIShUtil)
    var tool, srcPath;
    var numFiles = 0, numFolders = 0;
    if (askForFile) {
        var title = peFolder_bundle.GetStringFromName("locationToSaveThisItem");
        //todo: handle filters.
        srcPath = toolTreeView.getPathFromIndex(selectedIndices[0]);
        targetPath = ko.filepicker.saveFile(default_saveToolDirectory,
                                            srcPath);
        if (!targetPath) return [0, 0];
        default_saveToolDirectory = ko.uriparse.dirName(targetPath);
        // They've already been asked if they want to overwrite
        shutil.copy(srcPath, targetPath);
        numFiles = 1;
    } else {
        var prompt = peFolder_bundle.GetStringFromName("locationToSaveTheseItems");
        targetPath = ko.filepicker.getFolder(default_saveToolDirectory,
                                             prompt);
        if (!targetPath) return [0, 0];
        default_saveToolDirectory = targetPath;
        var overwrites = [];
        var overwritesAreFile = {};
        var i = 0;
        var lim = selectedIndices.length;
        var finalTargetPath;
        while (i < lim) {
            var index = selectedIndices[i];
            srcPath = toolTreeView.getPathFromIndex(index);
            if (toolTreeView.isContainer(index)) {
                finalTargetPath = osPathSvc.join(targetPath,
                                            osPathSvc.basename(srcPath));
                if (osPathSvc.exists(finalTargetPath)) {
                    overwrites.push(srcPath);
                    overwritesAreFile[srcPath] = false;
                } else {
                    toolTreeView.copyLocalFolder(srcPath, targetPath);
                    numFolders += 1;
                }
                // Skip to the next sibling if it's open
            } else {
                finalTargetPath = osPathSvc.join(targetPath,
                                            osPathSvc.basename(srcPath));
                if (osPathSvc.exists(finalTargetPath)) {
                    overwrites.push(srcPath);
                    overwritesAreFile[srcPath] = true;
                } else {
                    shutil.copy(srcPath, finalTargetPath);
                    numFiles += 1;
                }
            }
            i += 1;
        }
        if (overwrites.length) {
            var title = peFolder_bundle.GetStringFromName("overwriteFilesPrompt");
            var prompt = peFolder_bundle.GetStringFromName("selectWhichFilesDirectories");
            var selectionCondition = "zero-or-more";
            var i = 0;      
            var itemsToSave = ko.dialogs.selectFromList(title, prompt, overwrites, selectionCondition);
            if (itemsToSave) {
                itemsToSave.map(function(path) {
                        finalTargetPath = osPathSvc.join(targetPath,
                                                         osPathSvc.basename(path));
                        if (overwritesAreFile[path]) {
                            shutil.copy(path, finalTargetPath);
                            numFiles += 1;
                        } else {
                            toolTreeView.copyLocalFolder(path, targetPath);
                            numFolders += 1;
                        }
                });
            }
        }
    }
    return [numFiles, numFolders];
};

this.exportAsZipFile = function(event) {
    try {
        var title = peFolder_bundle.GetStringFromName("saveItemsToZipFileAs");
        var defaultFilterName = "zip";
        var fileNames = [defaultFilterName, "All"];
        var targetPath = ko.filepicker.saveFile(default_saveToolDirectory,
                                                null,
                                                title,
                                                defaultFilterName,
                                                fileNames
                                                );
        if (!targetPath) return;
        // Add a ".zip" if saveFile didn't provide one -- zip currently
        // isn't a language, so there's no auto-extension tagging.
        var ext = ko.uriparse.ext(targetPath);
        if (!ext) {
            targetPath += ".zip";
        }
        default_saveToolDirectory = ko.uriparse.dirName(targetPath);
        var numFilesZipped = ko.toolbox2.manager.view.zipSelectionToFile(targetPath, this._clickedOnRoot());
        var msg = peFolder_bundle.formatStringFromName("zippedNTools",
                                                   [numFilesZipped], 1);
        require("notify/notify").send(msg, "toolbox");
    } catch(ex) {
        alert(ex);
    }
};

this.reloadFolder = function(event) {
    var index, tool;
    var view = this.manager.view;
    if (this._clickedOnRoot()) {
        index = -1;
        tool = this.manager.toolbox2Svc.getStandardToolbox();
    } else {
        index = view.selection.currentIndex;
        if (index == -1) {
            alert("reloadFolder: can't find the clicked folder");
            return;
        } else if (!view.isContainer(index)) {
            alert("reloadFolder: not a folder");
            return;
        }
        tool = view.getTool(index);
    }
    this.manager.toolbox2Svc.reloadToolsDirectory(tool.path)
    this.manager.view.reloadToolsDirectoryView(index)
};

this.deleteItem = function(event) {
    var question;
    var indices = ko.toolbox2.getSelectedIndices(/*rootsOnly=*/true);
    var view = ko.toolbox2.manager.view;
    var i;
    var lim = indices.length;
    var index;
    for (i = 0; i < lim; i++) {
        index = indices[i];
        if (view.isToolboxRow(index)) {
            var msg = peFolder_bundle.formatStringFromName("cantDeleteToolbox.format",
                                                           [view.getCellText(index, {id:"name"})], 1);
            ko.dialogs.alert(msg);
            return;
        }
    }
        
    if (indices.length > 1) {
        question = peFolder_bundle.formatStringFromName("doYouWantToRemoveThe", [indices.length], 1);
    } else {
        question = peFolder_bundle.GetStringFromName("doYouWantToRemoveTheItemYouHaveSelected");
    }
    var response = "No";
    var text = null;
    var title = peFolder_bundle.GetStringFromName("deleteSelectedItems");
    var result = ko.dialogs.yesNo(question, response, text, title);
    //TODO: Add a do-not-ask pref
    if (result != "Yes") {
        return;
    }
    i = 0;
    while (i < lim) {
        var index = indices[i];
        if (view.get_toolType(index) == 'macro') {
            var tool = view.getTool(index);
            var url = tool.url;
            if (ko.views.manager.getViewForURI(url)) {
                var response = "No";
                var text = null;
                var title = ("Do you want to close the macro "
                             + tool.name
                             + "?");
                var result = ko.dialogs.yesNoCancel(question, response, text, title);
                if (result == "Cancel") {
                    return;
                } else if (result == "No") {
                    // Pull it out of the list
                    indices = indices.splice(i, 1);
                    lim -= 1;
                    i -= 1;
                }
            }
        }
        i++;
    }
    for (i = indices.length - 1; i >= 0; i--) {
        view.deleteToolAt(indices[i]);
    }
    // ko.toolbox2.manager.deleteCurrentItem();
};    


/* Invoke the given koITool. */
this.invokeTool = function(tool) {
    var _invoker = {
        'command': this.invoke_runCommand,
        'macro': this.invoke_executeMacro,
        'snippet': this.invoke_insertSnippet,
        'template': this.invoke_openTemplate,
        'URL': this.invoke_openURLInBrowser
    }[tool.type];
    _invoker(tool);
}

/* Edit properties of the given koITool. */
this.editPropertiesTool = function(tool) {
    var methodName = 'editProperties_' + tool.type; 
    var method = ko.toolbox2[methodName];
    if (method) {
        method.call(ko.toolbox2, tool);
    } else {
        alert("Interal error: don't know how to edit properties for "
            + tool.type + " " + tool.name);
    }
};


this.onTreeClick = function(event) {
    var index = this._currentRow(event, this.manager.widgets.tree);
    if (index == -1) {
        this.manager.view.selection.clearSelection();
    }
};

this.onDblClick = function(event, checkMouseClick/*=true*/) {
    if (typeof(checkMouseClick) == "undefined") checkMouseClick = true;
    if (checkMouseClick && event.which != 1) {
        return;
    }
    // Verify that we're still on an item
    if (this._currentRow(event, this.manager.widgets.tree) == -1) {
        this.manager.view.selection.clearSelection();
        return;
    }
    var that = ko.toolbox2;
    var view = that.manager.view;
    var index = view.selection.currentIndex;
    var tool = view.getTool(index);
    if (!tool) {
        return; 
    } else if (tool.type == "folder") { /* "folder" tools aren't really tools */
        // none of these seem to have much of an effect
        event.cancelBubble = true;
        event.stopPropagation();
        event.preventDefault();
        return;
    }
    this.invokeTool(tool);
};

this._addFlavors = function(dt, currentFlavors, path, index) {
    const mozFileFlavor = "application/x-moz-file";
    const uriListFlavor = "text/uri-list";
    const textUnicodeFlavor = "text/unicode";
    const textPlainFlavor = "text/plain";
    if (currentFlavors.indexOf(mozFileFlavor) == -1) {
        var nsLocalFile = Components.classes["@mozilla.org/file/local;1"]
            .createInstance(Components.interfaces.nsILocalFile);
        nsLocalFile.initWithPath(path);
        dt.mozSetDataAt(mozFileFlavor, nsLocalFile, index);
    }
    if (currentFlavors.indexOf(uriListFlavor) == -1) {
        dt.mozSetDataAt(uriListFlavor, ko.uriparse.localPathToURI(path), index);
    }
    if (currentFlavors.indexOf(textPlainFlavor) == -1) {
        dt.mozSetDataAt(textPlainFlavor, path, index);
    }
    if (currentFlavors.indexOf(textUnicodeFlavor) == -1) {
        dt.mozSetDataAt(textUnicodeFlavor, path, index);
    }
};

this.getToolboxResolvedPaths = function(selectedIndices) {
     var view = this.manager.view;
     var index;
     var path, paths = [];
     for (var j = 0; j < selectedIndices.length; j++) {
         index = selectedIndices[j];
         path = view.getPathFromIndex(index);
         if (view.isToolboxRow(index)) {
             // Cut/Copy the contents of a toolbox, but not the top part.
             var subPaths = osSvc.listdir(path, {}).
                 filter(function(basename) {
                         // Copy folders that start with a ".", but not
                         // files, and of course skip "." and ".."
                         return (basename != '.'
                                 && basename != '..'
                                 && (osPathSvc.isdir(osPathSvc.join(path, basename))
                                     || basename[0] != "."));
                     }).map(function(basename) osPathSvc.join(path, basename));
             paths = paths.concat(subPaths);
         } else {
             paths.push(path);
         }
     }
     return paths;
};

this.doStartDrag = function(event, tree) {
    var selectedIndices = this.getSelectedIndices(/*rootsOnly=*/true);
    var view = this.manager.view;
    var paths;
    var dt = event.dataTransfer;
    if (selectedIndices.some(function(index) view.isToolboxRow(index))) {
        paths = this.getToolboxResolvedPaths(selectedIndices);
        for (var i = 0; i < paths.length; i++) {
            this._addFlavors(dt, [], paths[i], i);
        }
    } else if (selectedIndices.length == 1) {
        var index = selectedIndices[0];
        var tool = view.getTool(index);
        var flavors = {};
        tool.getDragFlavors(flavors, {});
        flavors = flavors.value;
        for (var i = 0; i < flavors.length; i++) {
            var flavor = flavors[i];
            var dataValue = tool.getDragDataByFlavor(flavor);
            if (flavor == "application/x-moz-file") {
                // XPCOM limitation -- we only get a string back.
                var nsLocalFile = Components.classes["@mozilla.org/file/local;1"]
                    .createInstance(Components.interfaces.nsILocalFile);
                nsLocalFile.initWithPath(dataValue);
                dataValue = nsLocalFile;
            }
            dt.mozSetDataAt(flavor, dataValue, 0);
        }
        this._addFlavors(dt, flavors, tool.path, 0);
    } else {
        for (var i = 0; i < selectedIndices.length; i++) {
            var path = view.getPathFromIndex(selectedIndices[i]);
            this._addFlavors(dt, [], path, i);
        }
    }
    dt.effectAllowed = "copymove";
};

this._currentRow = function(event, tree) {
    var row = {};
    tree.treeBoxObject.getCellAt(event.pageX, event.pageY, row, {},{});
    return row.value;
};

this.doDragDefault = function(event) {
    event.preventDefault();
    return true;
};


var _lastDropEventTimeStamp = 0;

this.doDrop = function(event, tree) {

    // Detect and ignore duplicated drop events - bug 103113. A second drop
    // event within one second of last event is considered a duplicate.
    var lastTimeStamp = _lastDropEventTimeStamp;
    _lastDropEventTimeStamp = event.timeStamp;
    if ((event.timeStamp - lastTimeStamp) < 1000) {
        log.warn("Duplicated drop event detected - ignoring drop event");
        return false;
    }

    var index = this._currentRow(event, this.manager.widgets.tree);
    // Here we have to verify what we're doing.
    index = this.getContainerForIndex(index);
    var dt = event.dataTransfer;
    var dropEffect = dt.dropEffect;
    // The dropEffect field is only good for internal drag/drop.
    // If we're dropping from an external source on OSX, like
    // a finder window, dt.dropEffect will be "none" and none
    // of the event.*Key modifiers will be true, so always copy.
    var copying = dropEffect != "move";
    // We're either moving/copying one or more tools to a folder,
    // or we're dropping a blob of text, and will turn it into a snippet.
    try {
        var koDropDataList = ko.dragdrop.unpackDropData(dt);
        this._handleDroppedURLs(index, koDropDataList, copying);
        event.cancelBubble = true;
        event.stopPropagation();
        event.preventDefault();
        return true;
    } catch(ex) {
        alert("toolbox2_command.js: doDrop: error: " + ex);
        this.log.exception("ko.toolbox2.doDrop: " + ex);
        return false;
    }
};

this._addTrailingSlash = function(uri) {
    if (uri[uri.length - 1] != "/") {
        return uri + "/";
    }
    return uri;
};

this._removeTrailingSlash = function(uri) {
    if (uri[uri.length - 1] == "/") {
        return uri.substring(0, uri.length - 1);
    }
    return uri;
};

this._findCommonParent = function(currentParentDir, nextParentDir) {
    if (currentParentDir == nextParentDir) {
        return currentParentDir;
    } else {
        // Give up, invalidate everything after.
        return "";
    }
}

this._canonicalizeURI = function _canonicalizeURI(uri) {
    return ko.uriparse.localPathToURI(ko.uriparse.URIToLocalPath(uri));
};

this._handleDroppedURLs = function(index, koDropDataList, copying) {
    var koDropData;
    var targetDirectory;
    if (index == -1) {
        targetDirectory = this.manager.toolsMgr.getToolById(this.manager.toolbox2Svc.getStandardToolboxID()).path;
    } else {
        targetDirectory = this.manager.view.getPathFromIndex(index);
    }
    var parent = this.getContainerFromIndex(index);
    var targetURI = this._removeTrailingSlash(ko.uriparse.localPathToURI(targetDirectory));
    var loadedSomething = false;
    var sourceURI, url;
    var view = this.manager.view;
    var msg;
    var moduleName = "ko.toolbox2.doDrop";
    // First verify that all of the items can be dropped on the target.
    for (var i = 0; i < koDropDataList.length; i++) {
        koDropData = koDropDataList[i];
        // Bug 96385: because we do string-matching on URIs to test for
        // identity, don't trust the drag-drop service to correctly escape
        // all the characters that koIFileEx does.
        try {
            sourceURI = this._canonicalizeURI(this._removeTrailingSlash(koDropData.value));
        } catch(ex) {
            msg = peFolder_bundle.formatStringFromName("Problem trying to canonicalize the URI for X", [koDropData.value], 1);
            this.log.exception(ex, msg);
            ko.dialogs.alert("Internal Error: " + msg);
            continue;
        }
        if (targetURI == sourceURI) {
            msg = peFolder_bundle.formatStringFromName("X cant drop directory Y onto itself",
                         [moduleName, sourceURI], 2);
            this.log.error(msg)
            ko.dialogs.alert(msg);
            return false;
        }
        var sourceURIParent = sourceURI.substr(0, sourceURI.lastIndexOf("/"));
        if (targetURI == sourceURIParent && !copying) {
            msg = peFolder_bundle.formatStringFromName("X cant drop item Y onto its parent",
                       [moduleName, sourceURI], 2);
            this.log.error(msg)
            ko.dialogs.alert(msg);
            return false;
        }
        else if (targetURI.indexOf(this._addTrailingSlash(sourceURI)) == 0) {
            msg = peFolder_bundle.formatStringFromName("X cant drop item Y onto its descendant Z",
                       [moduleName, sourceURI, targetURI], 3);
            this.log.error(msg)
            ko.dialogs.alert(msg);
            return false;
        }
    }
    var urls = [];
    for (var i = 0; i < koDropDataList.length; i++) {
        koDropData = koDropDataList[i];
        if (koDropData.isText) {
            // Bug 88392 -- check for text-like URIs before file-like URIs
            // Create a snippet
            ko.projects.addSnippetFromText(koDropData.value, parent);
            loadedSomething = true;
            break;
        } else if (koDropData.isKpzURL) {
            url = koDropData.value;
            this._webPackageURL = url;
            try {
                this.manager.toolbox2Svc.importV5Package(targetDirectory, url);
                loadedSomething = true;
            } catch(ex) {
                alert("toolbox2_command.js:importV5Package failed: " + ex);
                this.log.exception("importV5Package failed: " + ex);
            }
        } else if (koDropData.isKomodoToolURL || koDropData.isZipURL) {
            url = koDropData.value;
            if (/\.komodotool$/.test(url)) {
                urls.push(url);
            }
            try {
                var path = ko.uriparse.URIToLocalPath(url);
                if (!path) {
                    this.log.error("Remote URIs not yet supported");
                    continue;
                }
                var targetPath, newPath = null;
                if (koDropData.isKomodoToolURL) {
                    targetPath = osPathSvc.join(targetDirectory,
                                                 osPathSvc.basename(path));
                    if (osPathSvc.exists(targetPath)
                        && !osPathSvc.isdir(targetPath)) {
                        newPath = this._getUniqueFileName(targetDirectory, path);
                        if (newPath && newPath == path) {
                            newPath = null;
                        }
                    }
                }
                if (newPath) {
                    this.manager.toolbox2Svc.importFileWithNewName(targetDirectory, path, newPath);
                } else {
                    this.manager.toolbox2Svc.importFiles(targetDirectory, 1, [path]);
                }
                //TODO: Add an arg to importFiles to delete the imported file if
                // importing succeeds.
                loadedSomething = true;
            } catch(ex) {
                alert("toolbox2_command.js:importFiles failed: " + ex);
                this.log.exception("importFiles failed: " + ex);
            }
        } else if (koDropData.isDirectoryURL) {
            url = koDropData.value;
            urls.push(url);
            try {
                var path = ko.uriparse.URIToLocalPath(url);
                if (!path) {
                    this.log.error("Remote URIs not yet supported");
                    continue;
                }
                this.manager.toolbox2Svc.importDirectory(targetDirectory, path, 1);
                loadedSomething = true;
            } catch(ex) {
                var msg = ("drag/drop directory " + path + " failed: " + ex);
                alert("toolbox2_command.js: " + msg);
                this.log.exception("importFiles failed: " + msg);
            }
        } else {
            alert("Internal error: Komodo doesn't know how to drag/drop "
                           + koDropData.value);
            // dump("something else\n");
        }
    }
    if (loadedSomething) {
        this.manager.toolbox2Svc.reloadToolsDirectory(targetDirectory);
        if (index == -1) {
            // This forces redoing the whole tree, since we don't
            // have a hook to the target node's parent.
            var observerSvc = Components.classes["@mozilla.org/observer-service;1"]
                    .getService(Components.interfaces.nsIObserverService);
            try {
                observerSvc.notifyObservers(null, 'toolbox-tree-changed', targetDirectory);
            } catch(ex) {
                this.log.exception("Failed to send toolbox-tree-changed: " + ex);
            }
        } else {
            this.manager.view.reloadToolsDirectoryView(index);
        }
        if (!copying) {
            var path, paths = [];
            var srcParentDir = null;
            var targetFileObj = Components.classes["@activestate.com/koFileEx;1"].
                          createInstance(Components.interfaces.koIFileEx);
            var koSysUtilsSvc = Components.classes["@activestate.com/koSysUtils;1"].
                          getService(Components.interfaces.koISysUtils);
            targetFileObj.path = targetDirectory;
            for (var url, i = 0; url = urls[i]; i++) {
                var srcFileObj = Components.classes["@activestate.com/koFileEx;1"].
                    createInstance(Components.interfaces.koIFileEx);
                srcFileObj.URI = url;
                path = srcFileObj.path;
                targetFileObj.URI = targetDirectory + "/" + srcFileObj.baseName;
                var deleted = false;
                if (srcParentDir === null) {
                    srcParentDir = srcFileObj.dirName;
                } else if (srcParentDir === "") {
                    // Nothing to do
                } else {
                    srcParentDir = this._findCommonParent(srcParentDir,
                                                          srcFileObj.dirName);
                }
                if (targetFileObj.exists) {
                    var tool = this.manager.toolsMgr.getToolFromPath(path);
                    if (tool) {
                        index = this.manager.view.getIndexByTool(tool);
                        if (index != -1) {
                            this.manager.view.deleteToolAt(index);
                            deleted = true;
                            paths.push(path);
                        }
                    }
                    if (!deleted) {
                        koSysUtilsSvc.MoveToTrash(path);
                        paths.push(path);
                    }
                }
            }
            this._removeLoadedMacros(this._getLoadedMacros(paths));
            var refreshTree = false;
            if (srcParentDir === null) {
                // Nothing to do
            } else if (srcParentDir === "") {
                refreshTree = true;
            } else {
                var tool = this.manager.toolsMgr.getToolFromPath(srcParentDir);
                if (!tool) {
                    refreshTree = true;
                } else {
                    var id = this.manager.view.getIndexByTool(tool);
                    if (id == -1) {
                        refreshTree = true;
                    } else {
                        this.manager.toolbox2Svc.reloadToolsDirectory(srcParentDir);
                        this.manager.view.reloadToolsDirectoryView(id);
                    }
                }
            }
            if (refreshTree) {
                this.manager.view.refreshFullView();
            }
        }
    }
    this.manager.widgets.tree.treeBoxObject.invalidate();
    return loadedSomething;
};

this.onTreeKeyPress = function(event) {
    try {
        var t = event.originalTarget;
        if (t.localName != "treechildren" && t.localName != 'tree') {
            return false;
        }
        if (this._arrowKeys.indexOf(event.keyCode) >= 0) {
            // Nothing to do but squelch the keycode
            event.cancelBubble = true;
            event.stopPropagation();
            event.preventDefault();
            return true;
        }
        if (event.shiftKey || event.ctrlKey || event.altKey) {
            return false;
        }
        if (event.keyCode == event.DOM_VK_RETURN) {
            // Unlike places, allow only one item to be acted on.
            var view = this.manager.view;
            var selectedIndices = ko.treeutils.getSelectedIndices(view, true);
            if (selectedIndices.length > 1) {
                var msg = peFolder_bundle.GetStringFromName("onlyInvokeOneTool");
                alert(msg);
            } else {
                var index = selectedIndices[0];
                if (view.isContainer(index)) {
                    view.toggleOpenState(index);
                } else {
                    this.invokeTool(view.getTool(index));
                }
                view.selection.select(index);
            }
        } else if (event.keyCode == event.DOM_VK_DELETE) {
            this.deleteItem(event);
        } else {
            return false;
        }
        event.cancelBubble = true;
        event.stopPropagation();
        event.preventDefault();
        return true;
    } catch(ex) {
        this.log.exception("onTreeKeyPress: error: " + ex + "\n");
    }
    return false;
}

this.onFocusWindow = function(event) {
    if (event.originalTarget == window) {
        document.getElementById("toolbox2-filter-textbox").focus();
    }
};

var ToolboxController = function() {
    this.log = ko.logging.getLogger("ToolboxController");
    this.log.setLevel(ko.logging.LOG_DEBUG);
};
ToolboxController.prototype = {
    _toolbox_can_take_keycommands: function() {
        return true;
    },
    is_cmd_cut_enabled: function() {
        return this._toolbox_can_take_keycommands();
    },
    do_cmd_cut: function() {
        ko.toolbox2.cutItem();
    },
    is_cmd_copy_enabled: function() {
        return this._toolbox_can_take_keycommands();
    },
    do_cmd_copy: function() {
        if (!this.is_cmd_copy_enabled()) {
            this.log.debug("do_cmd_copy: invoked, but not enabled")
            return;
        }
        ko.toolbox2.copyItem();
    },
    is_cmd_paste_enabled: function() {
        return (this._toolbox_can_take_keycommands()
                && xtk.clipboard.containsFlavors(["x-application/komodo-toolbox",
                                                  "text/uri-list"]));
    },
    do_cmd_paste: function() {
        if (!this.is_cmd_paste_enabled()) {
            this.log.debug("do_cmd_paste: invoked, but not enabled");
            return;
        }
        ko.toolbox2.pasteIntoItem();
    },
    supportsCommand: function(command) {
        return ("is_" + command + "_enabled") in this;
    },
    isCommandEnabled: function(command) {
        return this["is_" + command + "_enabled"]();
    },
    doCommand: function(command) {
        return this["do_" + command]();
    },
    __EOD__: null
};

 window.addEventListener("load", function() {
   try {
     document.getElementById("toolbox2-hierarchy-tree").controllers.insertControllerAt(0, new ToolboxController());
     window.addEventListener("focus", ko.toolbox2.onFocusWindow, false);
   } catch(ex) {
     log.exception(ex, "Failed to set a toolbox controller");
   }
 }, true);

}).apply(ko.toolbox2);
