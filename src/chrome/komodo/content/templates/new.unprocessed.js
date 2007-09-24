/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

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
 *      project
 *          Indicates the project to which the "Add to Current Project"
 *          applied. Only used if type=="file".
 *      addToProjectOverride
 *          Optional boolean indicating if the "Add to Current Project"
 *          checkbox should be checked. If this is not specified, the checked
 *          state will be the last user setting. Only used if type=="file"
 *          and 'project' is set.
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
 *      addToProject
 *          Set to true if "Add to Current Project" was checked and relevant.
 *          It is not relevant if no filename was given.
 */


var log = ko.logging.getLogger("templates");
//log.setLevel(ko.logging.LOG_DEBUG);

var gPrefs = null;
var gTemplateSvc = null;
var gCategoriesView = null;
var gTemplatesView = null;

var options = null;
var elAddToProject = null;
var openButton;



//---- interface routines for XUL

function OnLoad()
{
    try {
        var el;
        gPrefs = Components.classes['@activestate.com/koPrefService;1'].
                  getService(Components.interfaces.koIPrefService).prefs;

        var dialog = document.getElementById("dialog-newtemplate")
        openButton = dialog.getButton("accept");
        openButton.setAttribute("label", "Open");
        openButton.setAttribute("accesskey", "O");
        openButton.setAttribute("disabled", "true");
        var openFolderButton = dialog.getButton("extra1");
        openFolderButton.setAttribute("label", "Open Template Folder");
        openFolderButton.setAttribute("accesskey", "F");
        openFolderButton.setAttribute("tooltiptext",
            "Open user template folder.  Place your own template files here.");
        var cancelButton = dialog.getButton("cancel");
        cancelButton.setAttribute("accesskey", "C");
        
        options = {
            type: window.arguments[0].type,
            defaultDir: window.arguments[0].defaultDir || "",
            filename: window.arguments[0].filename || "",
            project: window.arguments[0].project || null,
            addToProjectOverride: window.arguments[0].addToProjectOverride || null,
            templateOnly: window.arguments[0].templateOnly || false
        };
        
        elAddToProject = document.getElementById("add-to-project");
        if (options.type == "project") {
            document.title = "New Project";
            elAddToProject.parentNode.removeChild(elAddToProject);
            elAddToProject = null;
            // Project packages do not support remote filesystems.
            el = document.getElementById("remoteFileDir");
            el.parentNode.removeChild(el);
            el = document.getElementById("localFileDir");
            el.setAttribute('label', 'Browse...');
            el.setAttribute("accesskey", "B");
        } else if (options.templateOnly) {
            document.title = "Select File Template";
            elAddToProject.parentNode.removeChild(elAddToProject);
            elAddToProject = null;
            el = document.getElementById("filepicker");
            el.setAttribute('collapsed', 'true');
        } else if (options.project) {
            var name = options.project.name;
            if (name.slice(-4, name.length) == ".kpf") {
                name = name.slice(0, -4);  // drop .kpf extension
            }
            elAddToProject.setAttribute("label",
                "Add to '"+name+"' Project");
            if (options.addToProjectOverride != null) {
                elAddToProject.checked = options.addToProjectOverride;
            } else {
                elAddToProject.checked
                    = gPrefs.getBooleanPref("new_file_add_to_project");
            }
        } else {
            // No project.
            elAddToProject.parentNode.removeChild(elAddToProject);
            elAddToProject = null;
        }

        document.getElementById('dirname').value = options.defaultDir;
        document.getElementById('filename').value = options.filename;
        resetAddToProject();
        
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
        templatesTree.focus();
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

function resetAddToProject()
{
    if (!elAddToProject) return false;
    var filename = document.getElementById('filename');
    if (!filename.value) {
        elAddToProject.setAttribute('disabled','true');
        return false;
    } else {
        elAddToProject.removeAttribute('disabled');
    }
    return true;
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

        if (elAddToProject) {
            if (!elAddToProject.getAttribute('disabled')) {
                window.arguments[0].addToProject = elAddToProject.checked;
                if (options.addToProjectOverride == null) {
                    gPrefs.setBooleanPref("new_file_add_to_project",
                                          elAddToProject.checked);
                }
            } else {
                window.arguments[0].addToProject = false;
            }
        } else {
            window.arguments[0].addToProject = null;
        }
        
        var filename = document.getElementById('filename').value;
        if (filename) {
            var answer;

            // If there is no file extension on the filename, ask them if
            // they'd like Komodo to automatically add the appropriate one
            // (ko.filepicker.saveFile() offers this too).
            var fExt = ko.uriparse.ext(filename);
            var tExt = ko.uriparse.ext(window.arguments[0].template);
            if (options.type == "project") {
                // Projects are always .kpf files
                if (fExt != ".kpf") {
                    filename += ".kpf";
                }
            } else if (tExt && !fExt) {
                var basename = ko.uriparse.baseName(filename);
                var prompt = "The filename you entered, '"+basename+"', does "+
                             "not have an extension. Would you like Komodo to "+
                             "add the extension '"+tExt+"'?";
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
            filename = osPathSvc.join(dirname, filename);
            if (osPathSvc.exists(filename)) {
                answer = ko.dialogs.yesNo(
                    "'"+filename+"' already exists, would you like to replace the existing file?",
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
        window.arguments[0].addToProject = null;
    } catch(ex) {
        log.exception(ex, "Error canceling 'New File' dialog.");
    }
    return true;
}

