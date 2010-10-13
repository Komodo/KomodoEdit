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

/* Komodo's New File/Project dialog (presenting a number of templates)
 *
 * Input arguments (in window.arguments[0]):
 *      type
 *          One of "file" or "project" to indicate if this a "New File" or
 *          "New Project" dialog.
 *      defaultDir
 *          Optional default value to be used for the "Directory" textbox.
 *          If not specified, the Directory textbox will start empty.
 *      filename
 *          Optional default value to be used for the "Filename" textbox.
 *          If not specified, the Filename textbox will start empty.
 *      templateOnly
 *          Is an optional boolean to limit the UI to just the selection of a
 *          template path. (Used by "Add Template..." in the Toolbox).
 *          Default is false.
 *
 * Output arguments (in window.arguments[0]):
 *      template
 *          Full path to the selected template. If the dialog was cancelled
 *          this is null.
 *      filename
 *          Full path to the selected target file, or null if the user didn't
 *          specify one.
 */


var log = ko.logging.getLogger("templates");
//log.setLevel(ko.logging.LOG_DEBUG);

var gPrefs = null;
var gTemplateSvc = null;
var gCategoriesView = null;
var gTemplatesView = null;

var options = null;
var openButton;

var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
    .getService(Components.interfaces.nsIStringBundleService)
    .createBundle("chrome://komodo/locale/templates/new.properties");

//---- interface routines for XUL

function OnLoad()
{
    try {
        var el;
        gPrefs = Components.classes['@activestate.com/koPrefService;1'].
                  getService(Components.interfaces.koIPrefService).prefs;

        var dialog = document.getElementById("dialog-newtemplate")
        openButton = dialog.getButton("accept");
        openButton.setAttribute("label", _bundle.GetStringFromName("open.label"));
        openButton.setAttribute("accesskey", _bundle.GetStringFromName("open.accesskey"));
        openButton.setAttribute("disabled", "true");
        var openFolderButton = dialog.getButton("extra1");
        openFolderButton.setAttribute("label",
            _bundle.GetStringFromName("openTemplateFolder.label"));
        openFolderButton.setAttribute("accesskey",
            _bundle.GetStringFromName("openTemplateFolder.accesskey"));
        openFolderButton.setAttribute("tooltiptext",
            _bundle.GetStringFromName("openUserTemplateFolder.tooltip"));
        var cancelButton = dialog.getButton("cancel");
        cancelButton.setAttribute("accesskey", "C");
        
        options = {
            type: window.arguments[0].type,
            defaultDir: window.arguments[0].defaultDir || "",
            filename: window.arguments[0].filename || "",
            templateOnly: window.arguments[0].templateOnly || false
        };
        
        if (options.type == "project") {
            document.title = _bundle.GetStringFromName("newProject.title");
            // Project packages do not support remote filesystems.
            el = document.getElementById("remoteFileDir");
            el.parentNode.removeChild(el);
            el = document.getElementById("localFileDir");
            el.setAttribute('label', _bundle.GetStringFromName("browse.message"));
            el.setAttribute("accesskey", _bundle.GetStringFromName("browse.accesskey"));
        } else if (options.templateOnly) {
            document.title = _bundle.GetStringFromName("selectFileTemplate.title");
            el = document.getElementById("filepicker");
            el.setAttribute('collapsed', 'true');
        }

        document.getElementById('dirname').value = options.defaultDir;
        var filenameTextbox = document.getElementById('filename');
        filenameTextbox.value = options.filename;
        
        gTemplateSvc = Components.classes["@activestate.com/koTemplateService?type="+options.type+";1"].getService();
        gTemplatesView = Components.classes["@activestate.com/koTemplatesView;1"].createInstance();
        gCategoriesView = Components.classes["@activestate.com/koTemplateCategoriesView;1"].createInstance();

        var categoriesTree = document.getElementById("categories");
        var catBoxObject = categoriesTree.treeBoxObject
                .QueryInterface(Components.interfaces.nsITreeBoxObject);
        catBoxObject.view = gCategoriesView;
        var templatesTree = document.getElementById("templates");
        var tmpBoxObject = templatesTree.treeBoxObject
                .QueryInterface(Components.interfaces.nsITreeBoxObject);
        tmpBoxObject.view = gTemplatesView;

        gTemplateSvc.loadTemplates();
        gCategoriesView.initialize(gTemplateSvc, gTemplatesView);
        var index = gCategoriesView.getDefaultCategoryIndex();
        gCategoriesView.selection.select(index);

        catBoxObject.invalidate();
        tmpBoxObject.invalidate();
        updateAccept();
        filenameTextbox.focus();
    } catch(ex) {
        log.exception(ex, "Error loading new file/templates dialog.");
    }
}

function OnUnload()
{
    gCategoriesView = null;
    gTemplatesView = null;
    gTemplateSvc = null;
}

function updateAccept() {
        var filename = document.getElementById('filename').value;
        var dirname = document.getElementById('dirname').value;
        if (filename && !dirname) {
            openButton.setAttribute("disabled", true);
        } else {
            openButton.removeAttribute("disabled");
        }
}

function CategoriesOnSelectionChange()
{
    try {
        gCategoriesView.selectionChanged();
        // Select the last selected template in this category and ensure
        // it is visible.
        var index = gCategoriesView.getDefaultTemplateIndex();
        gTemplatesView.selection.select(index);
        var boxObject = document.getElementById("templates").treeBoxObject;
        boxObject.ensureRowIsVisible(index);
        _UpdateOpenButtonStatus();
    } catch(ex) {
        log.exception(ex, "Error changing categories selection.");
    }
}

function TemplatesOnSelectionChange()
{
    try {
        gCategoriesView.templateSelectionChanged();
        gTemplatesView.selectionChanged();
    } catch(ex) {
        log.exception(ex, "Error changing categories selection.");
    }
}


function _UpdateOpenButtonStatus()
{
    var openButton = document.getElementById("dialog-newtemplate").getButton("accept");
    if (gTemplatesView.rowCount && gTemplatesView.selection.count) {
        if (openButton.hasAttribute("disabled")) {
            openButton.removeAttribute("disabled");
        }
    } else {
        openButton.setAttribute("disabled", "true");
    }
}


function TemplatesOnClick(event) {
    try {
        // c.f. mozilla/mailnews/base/resources/content/threadPane.js
        var t = event.originalTarget;

        // double-click in the tree body and there is a selection
        if (event.detail == 2 && t.localName == "treechildren"
            && gTemplatesView.rowCount && gTemplatesView.selection.count) {
            // open the selected template
            if (Open()) {
                window.close();
            }
        }
    } catch(ex) {
        log.exception(ex, "Error handling templates tree click.");
    }
}


function Open()
{
    try {
        var osPathSvc = Components.classes["@activestate.com/koOsPath;1"].
                getService(Components.interfaces.koIOsPath);
        window.arguments[0].template = gTemplatesView.getSelectedTemplate();

        var filename = document.getElementById('filename').value;
        if (filename) {
            var answer;

            // If there is no file extension on the filename, ask them if
            // they'd like Komodo to automatically add the appropriate one
            // (ko.filepicker.saveFile() offers this too).
            var fExt = ko.uriparse.ext(filename);
            var tExt = ko.uriparse.ext(window.arguments[0].template);
            if (options.type == "project") {
                // Projects are always .komodoproject files
                if (fExt != ".komodoproject") {
                    filename += ".komodoproject";
                }
            } else if (tExt && !fExt) {
                var basename = ko.uriparse.baseName(filename);
                var prompt = _bundle.formatStringFromName(
                    "theFilenameYouEnteredHasNoExtension.prompt", [basename, tExt], 2);
                answer = ko.dialogs.yesNoCancel(prompt, "Yes", null, null,
                                            "ensure_new_filename_has_ext");
                if (answer == "Yes") {
                    filename = filename + tExt;
                } else if (answer == "Cancel") {
                    return false;
                } // else "No": leave path alone.
            }
            
            var dirname = document.getElementById('dirname').value;
            if (!dirname)
                return false;
            // bug 74664: resolve tilde, if any
            dirname = osPathSvc.expanduser(dirname);
            filename = osPathSvc.join(dirname, filename);
            if (osPathSvc.exists(filename)) {
                answer = ko.dialogs.yesNo(_bundle.formatStringFromName(
                        "filenameAlreadyExists.prompt", [filename], 1),
                    "No");
                if (answer == "No")
                    return false;
            }
            window.arguments[0].filename = filename;
        } else {
            window.arguments[0].filename = null;
        }
        //XXX project stuff...

        ko.mru.addFromACTextbox(document.getElementById('filename'));
        ko.mru.addFromACTextbox(document.getElementById('dirname'));

        //XXX add the template to the template MRU list

        gCategoriesView.saveSelections();
    } catch(ex) {
        log.exception(ex, "Error returning selected template.");
    }
    return true;
}

function OpenTemplateFolder()
{
    try {
        var os = Components.classes["@activestate.com/koOs;1"].getService();
        var dname = gTemplateSvc.getUserTemplatesDir();
        var sysUtilsSvc = Components.classes["@activestate.com/koSysUtils;1"].
                    getService(Components.interfaces.koISysUtils);
        sysUtilsSvc.ShowFileInFileManager(dname);
    } catch(ex) {
        log.exception(ex, "Error opening templates folder.");
    }
}


function Cancel()
{
    try {
        window.arguments[0].template = null;
        window.arguments[0].filename = null;
    } catch(ex) {
        log.exception(ex, "Error canceling 'New File' dialog.");
    }
    return true;
}

