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
 * Portions created by ActiveState Software Inc are Copyright (C) 2000-2010
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

this._dragSources = [];
this._dragIndices = [];

this._getToolData = function(expectedTypeName) {
    // See peMacro.js for handling multiple items.
    var view = ko.toolbox2.manager.view;
    var index = view.selection.currentIndex;
    var tool = view.getTool(index);
    if (!tool) {
        return [null, null, null];
    }
    if (tool.type != expectedTypeName) {
        alert("Internal error: expected a "
              + expectedTypeName
              + ", but this tool is a "
              + tool.type);
        return [view, index, null];
    }
    return [view, index, tool];
};

this._getTool = function(expectedTypeName) {
    return this._getToolData(expectedTypeName)[2];
};

// Commands
this.invoke_runCommand = function(event, tool) {
    if (typeof(tool) == 'undefined') {
        tool = this._getTool('command');
        if (!tool) return;
    }
    ko.projects.runCommand(tool);
};
 
this.editProperties_command = function(event, tool) {
    if (typeof(tool) == 'undefined') {
        tool = this._getTool('command');
        if (!tool) return;
    }
    ko.projects.commandProperties(tool);
};

this.add_command = function(view, index, parent, item) {
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

var peFile_bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
      .getService(Components.interfaces.nsIStringBundleService)
      .createBundle("chrome://komodo/locale/project/peFile.properties");
var peFolder_bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
      .getService(Components.interfaces.nsIStringBundleService)
      .createBundle("chrome://komodo/locale/project/peFolder.properties");
var partutils_bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
      .getService(Components.interfaces.nsIStringBundleService)
      .createBundle("chrome://komodo/locale/project/partutils.properties");

// Macros

this.invoke_executeMacro = function(event, tool) {
    if (typeof(tool) == 'undefined') {
        tool = this._getTool('macro');
        if (!tool) return;
    }
    ko.projects.executeMacro(tool, tool.getBooleanAttribute('async'));
};

this.invoke_editMacro = function(event, tool) {
    if (typeof(tool) == 'undefined') {
        tool = this._getTool('macro');
        if (!tool) return;
    }
    ko.open.URI(tool.url);
};

this.editProperties_macro = function(event, tool) {
    if (typeof(tool) == 'undefined') {
        tool = this._getTool('macro');
        if (!tool) return;
    }
    ko.projects.macroProperties(tool);
};

this.add_macro = function(view, index, parent, item) {
    ko.projects.addMacro(parent, item);
};

// Menus

this.add_menu = function(view, index, parent, item) {
    ko.projects.addMenu(parent, item);
};

this.editProperties_menu = function(event, tool) {
    if (typeof(tool) == 'undefined') {
        tool = this._getTool('menu');
        if (!tool) return;
    }
    ko.projects.menuProperties(tool);
};

// Snippets

this.invoke_insertSnippet = function(event, tool) {
    if (typeof(tool) == 'undefined') {
        tool = this._getTool('snippet');
        if (!tool) return;
    }
    ko.projects.snippetInsert(tool);
};

this.editProperties_snippet = function(event, tool) {
    if (typeof(tool) == 'undefined') {
        tool = this._getTool('snippet');
        if (!tool) return;
    }
    ko.projects.snippetProperties(tool);
};

this.add_snippet = function(view, index, parent, item) {
    ko.projects.addSnippet(parent, item);
};

// Templates
this.invoke_openTemplate = function(event, tool) {
    if (typeof(tool) == 'undefined') {
        tool = this._getTool('template');
        if (!tool) return;
    }
    ko.views.manager.doFileNewFromTemplateAsync(tool.url);
};

this.add_template = function(view, index, parent, item) {
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

this.add_toolbar = function(view, index, parent, item) {
    ko.projects.addToolbar(parent, item);
};

this.editProperties_toolbar = function(event, tool) {
    if (typeof(tool) == 'undefined') {
        tool = this._getTool('toolbar');
        if (!tool) return;
    }
    ko.projects.menuProperties(tool);
}

// Templates can't be edited -- Komodo 5 uses the 
// file properties dialog to edit a template, which is just wrong.

// URLs
this.invoke_openURLInBrowser = function(event, tool) {
    if (typeof(tool) == 'undefined') {
        tool = this._getTool('URL');
        if (!tool) return;
    }
    ko.browse.openUrlInDefaultBrowser(tool.value);
};

this.invoke_openURLInTab = function(event, tool) {
    if (typeof(tool) == 'undefined') {
        tool = this._getTool('URL');
        if (!tool) return;
    }
    ko.views.manager.doFileOpenAsync(tool.value, 'browser');
};

this.editProperties_URL = function(event, tool) {
    if (typeof(tool) == 'undefined') {
        tool = this._getTool('URL');
        if (!tool) return;
    }
    ko.projects.URLProperties(tool);
};

this.add_URL = function(view, index, parent, item) {
    ko.projects.addURL(parent, item);
};

// folders
this.invoke_folderCommand = function(event, tool) {
    // none of these seem to have much of an effect
    event.cancelBubble = true;
    event.stopPropagation();
    event.preventDefault();
};

this.add_folder = function(view, index, parent, item) {
    var basename = ko.dialogs.prompt(peFolder_bundle.GetStringFromName("enterFolderName"));
    if (!basename) return;
    item.setStringAttribute('name', basename);
    this.addNewItemToParent(item, parent);
};

// Templates can't be edited -- Komodo 5 uses the 
// file properties dialog to edit a template, which is just wrong.

// Generic functions on the hierarchy view tree

this.editPropertiesItem = function(event) {
    var that = ko.toolbox2;
    var view = that.manager.view;
    var index = view.selection.currentIndex;
    var tool = view.getTool(index);
    // Method construction for names like editProperties_macro
    var methodName = 'editProperties_' + tool.type; 
    var method = that[methodName];
    if (method) {
        method.call(that, event);
    } else {
        alert("toolbox2_command.js::editPropertiesItem: Interal error: Don't know how to edit properties for "
              + tool.type
              + " "
              + tool.name);
    }
};

this.addToolboxItem = function(itemType) {
    try {
    var this_ = ko.toolbox2;
    var method = this_["add_" + itemType];
    if (!method) {
        alert("toolbox2_command.js internal error: Don't know how to create a new "
              + itemType);
        return;
    }
    var view = this_.manager.view;
    var index = view.selection.currentIndex;
    var parent = view.getTool(index);
    var item = this.manager.toolsMgr.createToolFromType(itemType);
    method.call(this_, view, index, parent, item);
    } catch(ex) {
        ko.dialogs.alert("toolbox2_command.js: Internal error: Trying to add a new "
                         + itemType
                         + ": "
                         + ex);
    }
};

// Generic top-level routines

this.importFilesFromFileSystem = function(event) {
    var this_ = ko.toolbox2;
    var view = this_.manager.view;
    var index = view.selection.currentIndex;
    if (index == -1) {
        index = 0;  // For the std toolbox
    }
    var defaultDirectory = view.getPathFromIndex(index);
    var defaultFilename = null;
    var title = "Select file(s) to import into the toolbox";
    var paths = ko.filepicker.openFiles(defaultDirectory, defaultFilename,
                                        title);
    if (!paths) {
        return;
    }
    try {
        this_.manager.toolbox2Svc.importFiles(defaultDirectory, paths, paths.length);
        this_.manager.view.reloadToolsDirectoryView(index);
    } catch(ex) {
        this_.log.exception("importFilesFromFileSystem failed: " + ex);
    }
};

this.importFolderFromFileSystem = function(event) {
    var this_ = ko.toolbox2;
    var view = this_.manager.view;
    var index = view.selection.currentIndex;
    if (index == -1) {
        index = 0;  // For the std toolbox
    }
    var defaultDirectory = view.getPathFromIndex(index);
    var title = "Select a folder of tools to import into the toolbox";
    var path = ko.filepicker.getFolder(defaultDirectory, title);
    if (!path) {
        return;
    }
    try {
        this_.manager.toolbox2Svc.importDirectory(defaultDirectory, path);
        this_.manager.view.reloadToolsDirectoryView(index);
    } catch(ex) {
        this_.log.exception("importFilesFromFileSystem failed: " + ex);
    }
};
 
this.importPackage = function(event) {
    var this_ = ko.toolbox2;
    var view = this_.manager.view;
    var index = view.selection.currentIndex;
    if (index == -1) {
        index = 0;  // For the std toolbox
    }
    var targetDirectory = view.getPathFromIndex(index);
    var title = partutils_bundle.GetStringFromName("selectPackageToImport");
    var defaultDirectory = null;
    var defaultFilename = null;
    var path = ko.filepicker.openFile(defaultDirectory, defaultFilename,
                                      title,
                                      "Komodo Package", // default filter
                                      ["Komodo Package", "All"]); // filters
    if (!path) {
        return;
    }
    try {
        this_.manager.toolbox2Svc.importV5Package(targetDirectory, path);
        this_.manager.view.reloadToolsDirectoryView(index);
    } catch(ex) {
        this_.log.exception("importFilesFromFileSystem failed: " + ex);
    }
};

this._selectCurrentItems = function() {
    this.selectedIndices = this.getSelectedIndices(/*rootsOnly=*/true);
    var view = this.manager.view;
    var paths = this.selectedIndices.map(function(index) {
            return view.getPathFromIndex(index);
        });
    xtk.clipboard.setText(paths.join("\n"));
}

this.cutItem = function(event) {
    this.copying = false;
    this._selectCurrentItems();
};

this.copyItem = function(event) {
    this.copying = true;
    this._selectCurrentItems();
};

this.pasteIntoItem = function(event) {
    try {
        var this_ = ko.toolbox2;
        var view = this_.manager.view;
        var index = view.selection.currentIndex;
        var parent = view.getTool(index);
        var paths = xtk.clipboard.getText().split("\n");
        var loadedMacroURIs = this.copying ? [] : this._getLoadedMacros(paths);
        view.pasteItemsIntoTarget(index, paths, paths.length, this.copying);
        this._removeLoadedMacros(loadedMacroURIs);
    } catch(ex) {
        ko.dialogs.alert("toolbox2_command.js: Error: Trying to copy paths into the toolbox "
                         + ex);
    }
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
        var view = ko.toolbox2.manager.view;
        var index = view.selection.currentIndex;
        var path = view.getPathFromIndex(index);
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
        ko.statusBar.AddMessage(msg, "editor", 5000, true);
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
    var osPathSvc = Components.classes["@activestate.com/koOsPath;1"].
                getService(Components.interfaces.koIOsPath);
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
        var defaultFilterName = "Zip";
        var fileNames = [defaultFilterName, "All"];
        var targetPath = ko.filepicker.saveFile(default_saveToolDirectory,
                                                null,
                                                title,
                                                defaultFilterName,
                                                fileNames
                                                );
        if (!targetPath) return;
        default_saveToolDirectory = ko.uriparse.dirName(targetPath);
        numFilesZipped = ko.toolbox2.manager.view.zipSelectionToFile(targetPath);
        msg = peFolder_bundle.formatStringFromName("zippedNTools",
                                                   [numFilesZipped], 1);
        ko.statusBar.AddMessage(msg, "toolbox", 5000, true);
    } catch(ex) {
        alert(ex);
    }
};

this.reloadFolder = function(event) {
    var that = ko.toolbox2;
    var view = that.manager.view;
    var index = view.selection.currentIndex;
    if (index == -1) {
        alert("reloadFolder: can't find the clicked folder");
        return;
    } else if (!view.isContainer(index)) {
        alert("reloadFolder: not a folder");
        return;
    }
    var tool = view.getTool(index);
    that.manager.toolbox2Svc.reloadToolsDirectory(tool.path)
    that.manager.view.reloadToolsDirectoryView(index)
};

this.deleteItem = function(event) {
    var question;
    var indices = ko.toolbox2.getSelectedIndices(/*rootsOnly=*/true);
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
    var view = ko.toolbox2.manager.view;
    var i = 0;
    var lim = indices.length;
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

this._invokerNameForToolType = {
 'folder' : this.invoke_folderCommand,
 'command' : this.invoke_runCommand,
 'macro' : this.invoke_executeMacro,
 'snippet' : this.invoke_insertSnippet,
 'template' : this.invoke_openTemplate,
 'URL' : this.invoke_openURLInBrowser,
 '__EOD__':null
};

this.onDblClick = function(event) {
    if (event.which != 1) {
        dump("this.onDblClick, leaving as event.which = "
             + event.which
             + "\n");
        return;
    }
    var that = ko.toolbox2;
    var view = that.manager.view;
    var index = view.selection.currentIndex;
    var tool = view.getTool(index);
    if (!tool) {
        return;
    }
    var method = that._invokerNameForToolType[tool.type];
    if (method) {
        method.call(that, event, tool);
    } else {
        alert("Don't know what to do with "
              + tool.type
              + " "
              + tool.name);
    }
};

this.doStartDrag = function(event, tree) {
    var selectedIndices = this.getSelectedIndices(/*rootsOnly=*/true);
    var view = this.manager.view;
    var paths;
    var dt = event.dataTransfer;
    if (selectedIndices.length == 1) {
        var index = selectedIndices[0];
        var tool = view.getTool(index);
        paths = [tool.path];
        var flavors = {};
        tool.getDragFlavors(flavors, {});
        flavors = flavors.value;
        for (var i = 0; i < flavors.length; i++) {
            var flavor = flavors[i];
            var dataValue = tool.getDragDataByFlavor(flavor);
            dt.mozSetDataAt(flavor, dataValue, 0);
        }
    } else {
        paths = [];
        for (var i = 0; i < selectedIndices.length; i++) {
            var path = view.getPathFromIndex(selectedIndices[i]);
            paths.push(path);
            dt.mozSetDataAt("application/x-moz-file", path, i);
            dt.mozSetDataAt('text/plain', path, i);
        }
    }
    this._dragSources = paths;
    this._dragIndices = selectedIndices;
    if (event.ctrlKey) {
        dt.effectAllowed = this.originalEffect = "copy";
        this.copying = true;
    } else {
        dt.effectAllowed = this.originalEffect = "move";
        this.copying = false;
    }
};

this._currentRow = function(event, tree) {
    var row = {};
    tree.treeBoxObject.getCellAt(event.pageX, event.pageY, row, {},{});
    return row.value;
};

this._checkDrag = function(event, tree) {
    var inDragSource = this._checkDragSource(event, tree);
    event.dataTransfer.effectAllowed = inDragSource ? this.originalEffect : "none";
    return inDragSource;
};

this._checkDragSource = function(event, tree) {
    if (!this._dragIndices.length) {
        //dump("not dragging anything\n");
        return false;
    }
    var index = this._currentRow(event, tree);
    if (this._dragIndices.indexOf(index) != -1) {
        //dump("can't drag an item to itself\n");
        return false;
    }
    if (!this.manager.view.isContainer(index)) {
        //dump("target isn't an index\n");
        return false;
    }
    var view = this.manager.view;
    var candidateIndex;
    for (var i = this._dragIndices.length - 1; i >= 0; i--) {
        candidateIndex = this._dragIndices[i];
        if (view.getParentIndex(candidateIndex) == index) {
            /*
            dump("can't copy/paste node "
                 + candidateIndex
                 + " to its immediate parent "
                 + index
                 + "\n");
            */
            return false;
        }
        if (view.isAncestor(candidateIndex, index)) {
            /*
            dump("can't copy/paste node "
                 + candidateIndex
                 + " to its descendant "
                 + index
                 + "\n");
            */
            return false;
        }
    }
    return true;
};

this.doDragEnter = function(event, tree) {
    return this._checkDrag(event, this.manager.widgets.tree);
};

this.doDragOver = function(event, tree) {
    return this._checkDrag(event, this.manager.widgets.tree);
};

this.doDrop = function(event, tree) {
    if (!this._dragSources.length) {
        //dump("onDrop: no source indices to drop\n");
        return false;
    }
    var index = this._currentRow(event, this.manager.widgets.tree);
    try {
        var paths = this._dragSources;
        var loadedMacroURIs = this.copying ? [] : this._getLoadedMacros(paths);
        this.manager.view.pasteItemsIntoTarget(index, paths, paths.length, this.copying);
        if (!this.copying) {
            this._removeLoadedMacros(loadedMacroURIs);
        }
    } catch(ex) {
        ko.dialogs.alert("drag/drop: " + ex);
    }
    this._dragSources = [];
    this._dragIndices = [];
    return true;
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
