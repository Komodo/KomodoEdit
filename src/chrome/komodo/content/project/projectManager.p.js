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

/* -*- Mode: JavaScript; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 2 -*-
 * projectmanager.js
 * Handle Komodo Project Files -- main part
 *
 * To be loaded in the same .xul file as projectviewer.js
 */

// Globals
xtk.include("domutils");

if (typeof(ko)=='undefined') {
    var ko = {};
}
if (typeof(ko.projects)=='undefined') {
    ko.projects = {};
}

(function () {

var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
    .getService(Components.interfaces.nsIStringBundleService)
    .createBundle("chrome://komodo/locale/projectManager.properties");

const XUL_NS = "http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul";
this.manager = null;

var _obSvc = Components.classes["@mozilla.org/observer-service;1"].
        getService(Components.interfaces.nsIObserverService);

//gone: ko.projects.manager.lastCurrentProject
//gone: ko.projects.manager.activeView
//gone: ko.projects.manager._projects
//gone: ko.projects.manager.getProjectsMenu (and xul tag)
//gone: ko.projects.manager.hasProject
//gone: ko.projects.manager.managers
//gone: ko.projects.manager.getAllProjects
//gone: ko.projects.manager.getFocusedProjectView
//gone: ko.projects.manager.findItemByAttributeValue
//gone: ko.toolboxes.importPackage -- can't import packages into toolboxes now

//----- The projectManager class manages the current project, if there is one.

function projectManager() {
    this.name = 'projectManager';
    ko.projects.BaseManager.apply(this, []);
    this.log = ko.logging.getLogger('projectManager');
    this._projects = [];
    this._currentProject = null;
    this.registerCommands();
}

// The following two lines ensure proper inheritance (see Flanagan, p. 144).
projectManager.prototype = new ko.projects.BaseManager();
projectManager.prototype.constructor = projectManager;

projectManager.prototype._getOpenURLsInProject = function(project) {
    // Find out if any child elements are currently open
    var docs = ko.views.manager.topView.getDocumentViewList(true);
    var opened = [];
    var url;
    for (var i = 0; i < docs.length; i++) {
        if (docs[i].koDoc && docs[i].koDoc.file) {
            url = docs[i].koDoc.file.URI;
            if (project.getChildByURL(url)) {
                opened.push(url);
            }
        }
    }
    return opened;
}

projectManager.prototype.forceCloseAllViewsForURL = function(url) {
    var views = ko.views.manager.getAllViewsForURI(url);
    for (var i = 0; i < views.length; ++i) {
        // we don't want dialogs to popup here!!!
        views[i].closeUnconditionally();
    }
}


projectManager.prototype._saveProjectViewState = function(project) {
    // This function goes through all of the URLs in a project,
    // finds out if any of them are "open", and saves the
    // list in a viewState Pref for the Project's KPF file.

    var prefSvc = Components.classes["@activestate.com/koPrefService;1"].
                getService(Components.interfaces.koIPrefService);
    var viewStateMRU = prefSvc.getPrefs("viewStateMRU");
    var projectViewState;
    var url = project.url;
    var opened_files = Components.classes['@activestate.com/koOrderedPreference;1'].createInstance();
    var some_opened_files = false;
    var v;

    if (viewStateMRU.hasPref(url)) {
        projectViewState = viewStateMRU.getPref(url);
    } else {
        projectViewState = Components.classes["@activestate.com/koPreferenceSet;1"].createInstance();
        projectViewState.id = url
        viewStateMRU.setPref(projectViewState);
    }
    var urls = this._getOpenURLsInProject(project);
    for (var i=0; i < urls.length; i++) {
        opened_files.appendStringPref(urls[i]);
    }
    projectViewState.setPref("opened_files", opened_files);
}

projectManager.prototype.closeProjectEvenIfDirty = function(project) {
    if (typeof(project) == "undefined") project = this.currentProject;
    if (!project) {
        // No project to close.
        return true;
    }
    ko.toolbox2.manager.toolbox2Svc.deactivateProjectToolbox(project);
    
    // the active project has been reset
    // Forget about any notifications made for this project.
    this.notifiedClearProject(project);
    project.close();
    this.currentProject = null;
    ko.mru.addURL("mruProjectList", project.url);
    window.updateCommands('some_projects_open');
    return true;
}

projectManager.prototype.closeProject = function(project /*=this.currentProject*/) {
    if (typeof(project) == "undefined") project = this.currentProject;
    if (!project) {
        // No project to close.
        return true;
    }
    if (project.isDirty) {
        var question = _bundle.formatStringFromName("saveChangesToProject.message", [project.name], 1);
        var answer = ko.dialogs.yesNoCancel(question);
        if (answer == "Cancel") {
            return false;
        } else if (answer == "Yes") {
            try {
                this.saveProject(project);
            } catch(ex) {
                var lastErrorSvc = Components.classes["@activestate.com/koLastErrorService;1"].
                    getService(Components.interfaces.koILastErrorService);
                ko.dialogs.alert(_bundle.formatStringFromName("thereWasAnErrorSavingProject.alert",
                    [project.name, lastErrorSvc.getLastErrorMessage()], 2));
                return false;
            }
        }
    }
    this._saveProjectViewState(project);
    var urls = this._getOpenURLsInProject(project);
    if (urls.length != 0) {
        var action = ko.dialogs.yesNoCancel(
                _bundle.formatStringFromName("closeTheOpenedFilesFromProjectNamed.template",
                                         [project.name], 1),
                "No", null, null, // default response, text, title
                "close_all_files_on_project_close");
        if (action == "Cancel") {
            return false;
        } else if (action == "Yes") {
            // Should find out which ones are dirty and offer to save those --
            // then _closeURL can be brutal with those that the user didn't
            // want to save.
            var modified = ko.views.manager.offerToSave(urls,
                _bundle.GetStringFromName("saveModifiedFiles.message"),
                _bundle.GetStringFromName("saveSelectedFilesBeforeClosingThem.message"));
            if (modified == false) return false;

            var i;
            for (i=0; i < urls.length; i++) {
                this.forceCloseAllViewsForURL(urls[i]);
            }
        }
    }
    return this.closeProjectEvenIfDirty(project);
}

projectManager.prototype.getDirtyProjects = function() {
    return (this.currentProject && this.currentProject.isDirty
            ? [this.currentProject]
            : []);
}

projectManager.prototype.closeAllProjects = function() {
    return this.closeProject();
}

projectManager.prototype.closeAllProjectsEvenIfDirty = function() {
    return this.closeProjectEvenIfDirty();
}

projectManager.prototype._notified_projects = {};

projectManager.prototype.notifiedClearProject = function(project) {
    if (project in this._notified_projects) {
        //dump("notified:: clearing project: " + project.url + "\n");
        delete this._notified_projects[project];
    }
}
projectManager.prototype.notifiedAddProject = function(project) {
    //dump("notified:: adding project: " + project.url + "\n");
    this._notified_projects[project] = 1;
}
projectManager.prototype.notifiedIsAlreadySetForProject = function(project) {
    //dump("notified:: already added " + (project in this._notified_projects) +
    //     " for project: " + project.url + "\n");
    return (project in this._notified_projects);
}


/**
 * Return a project instance that is opened in another Komodo window. When
 * not found this will return null. The search is done on all other Komodo
 * window instances.
 *
 * @param projectUrl {string}  The URL of the project to check for.
 * @returns {Components.interfaces.koIProject}  The project found, else null.
 */
projectManager.prototype.findOtherWindowProjectInstanceForUrl = function(projectUrl) {
    var otherProject;
    var otherWindow;
    var koWindowList = ko.windowManager.getWindows();
    for (var i=0; i < koWindowList.length; i++) {
        otherWindow = koWindowList[i];
        if (otherWindow != window) {
            otherProject = otherWindow.ko.projects.manager.getProjectByURL(projectUrl);
            if (otherProject) {
                return otherProject;
            }
        }
    }
    return null;
}

/**
 * Save the given project.
 * @param project {Components.interfaces.koIProject}
 * @param skip_scc_check {boolean}
 *        Optional (default is false). Whether to skip the file scc edit step.
 */
projectManager.prototype.saveProject = function(project, skip_scc_check) {
    // Returns true on success, false on failure.
    var file = project.getFile();

    // Check to see if the project contents have changed on disk.
    if (project.haveContentsChangedOnDisk()) {
        var prompt = _bundle.formatStringFromName("projectHasChangedOutsideKomodo.message",
                                                  [project.name], 1);
        var overwrite = _bundle.GetStringFromName("overwriteButton.label");
        var overwriteAccesskey = _bundle.GetStringFromName("overwriteButton.accesskey");
        var revert = _bundle.GetStringFromName("revertButton.label");
        var revertAccesskey = _bundle.GetStringFromName("revertButton.accesskey");
        var cancel = _bundle.GetStringFromName("cancelButton.label");
        var cancelAccesskey = _bundle.GetStringFromName("cancelButton.accesskey");
        var response = ko.dialogs.customButtons(prompt,
                                                [[overwrite, overwriteAccesskey],
                                                 [revert, revertAccesskey],
                                                 [cancel, cancelAccesskey]],
                                                cancel,
                                                null,
                                                _bundle.formatStringFromName("projectHasChangedOnDisk.message",
                                                                             [project.name], 1));
        if (response == cancel) {
            return false;
        } else if (response == revert) {
            this.revertProject(project);
            return true;
        } else if (response != overwrite) {
            this.log.error("Unexpected response from ko.dialogs.customButtons: " + response);
            return false;
        }
    }

    if (file.isReadOnly) {
        alert(_bundle.formatStringFromName("theProjectIsReadonly.alert", [project.name], 1));
        return false;
    } else {
        try {
            project.save();
        } catch(ex) {
            var lastErrorSvc = Components.classes["@activestate.com/koLastErrorService;1"].
                getService(Components.interfaces.koILastErrorService);
            ko.dialogs.alert(_bundle.formatStringFromName("thereWasAnErrorSavingProject.alert",
                [project.name, lastErrorSvc.getLastErrorMessage()], 2));
            return false;
        }

        // Clear any notifications, as the project has been updated.
        this.notifiedClearProject(project);

        try {
            _obSvc.notifyObservers(this, 'file_changed', project.url);
        } catch(e) { /* exception if no listeners */ }
        window.updateCommands('project_dirty');
    }
    return true;
}

projectManager.prototype.newProject = function(url) {
    if (!this.closeProject()) {
        return false;
    }
    var project = Components.classes["@activestate.com/koProject;1"]
                                        .createInstance(Components.interfaces.koIProject);
    project.create();
    project.url = url;
    return this._saveNewProject(project);
}
    
projectManager.prototype._saveNewProject = function(project) {
    try {
        project.save();
    } catch(ex) {
        var lastErrorSvc = Components.classes["@activestate.com/koLastErrorService;1"].
            getService(Components.interfaces.koILastErrorService);
        ko.dialogs.alert(_bundle.formatStringFromName("thereWasAnErrorSavingProject.alert",
            [project.name, lastErrorSvc.getLastErrorMessage()], 2));
        return false;
    }
    this._addProject(project);
    ko.places.manager.openURI(project.uri);
    try {
        _obSvc.notifyObservers(this, 'file_project', project.url);
    } catch(e) { /* exception if no listeners */ }
    return true;
}

projectManager.prototype._getNewProjectPath = function() {
    return ko.filepicker.saveFile(
        null, // defaultDir
        _bundle.GetStringFromName("newProject.defaultFileName") + ".komodoproject", // defaultFilename
        _bundle.GetStringFromName("newProject.title"), // title
        _bundle.GetStringFromName("komodoProject.message"), // defaultFilterName
        [_bundle.GetStringFromName("komodoProject.message"),
         _bundle.GetStringFromName("all.message")]); // filterNames
};

projectManager.prototype.newProjectFromTemplate = function(templatePath) {
    try {
        this.log.info("doing newTemplate: ");
        if (!this.closeProject()) {
            return false;
        }
        var lastErrorSvc = Components.classes['@activestate.com/koLastErrorService;1'].getService();
        var projectPath;
        if (typeof(templatePath) == "undefined") {
            // Get template selection from the user.
            var obj = new Object();
            obj.type = "project";
            obj.filename = _bundle.GetStringFromName("newProject.defaultFileName") + ".kpf";
            ko.launch.newTemplate(obj);
            if (obj.template == null || obj.filename == null) return false;
            templatePath = obj.template;
            projectPath = obj.path;            
        } else {
            projectPath = this._getNewProjectPath();
        }
        if (!projectPath) return false;
        var uri = ko.uriparse.localPathToURI(projectPath);
        var extractLocation = ko.uriparse.dirName(uri);

        var packager = Components.classes["@activestate.com/koProjectPackageService;1"]
                          .getService(Components.interfaces.koIProjectPackageService);
        var project = packager.newProjectFromPackage(templatePath, extractLocation);
        project.url = uri;
        // Next two lines fix bug 82385, fallout from bug 82050:
        // Show project name in the project tree.  Projects built from
        // templates have generic names, so we need to change them.
        // First line: make sure the project tree doesn't display the old
        // name when it's added to the view.
        // Second line: get old behavior, ensuring the project name is
        // the same as the file's basename
        project.removeAttribute('name');
        project.name = project.getFile().baseName;

        var ok = this._saveNewProject(project);
        if (ok) {
            var toolbox = ko.toolbox2.getProjectToolbox(project.url);
            if (toolbox) {
                // run the creation macro
                var macro = toolbox.getChildByTypeAndName('macro', 'oncreate', 1);
                if (macro) {
                    ko.projects.executeMacro(macro);
                } else {
                    this.log.debug("No oncreate macro found");
                }
            } else {
                this.log.debug("No toolbox found at "
                               + project.getFile().path);
            }
        } else {
            this.log.debug("Couldn't save the new project "
                           + project.getFile().path);
        }
        return ok;
    } catch(ex) {
        this.log.exception(ex, "Error in newProjectFromTemplate.");
    }
    return false;
}

projectManager.prototype.saveProjectAsTemplate = function (project) {
    try {
        if (project.isDirty) {
            var strYes = "Yes";
            var res = ko.dialogs.yesNo(
                _bundle.GetStringFromName("saveTheProjectAndContinue.message"), //prompt
                strYes, // default response
                _bundle.GetStringFromName("projectsNeedToBeSavedBeforeExport.message") // text
                );
            if (res != strYes || !this.saveProject(project)) {
                return;
            }
        }
        var os = Components.classes["@activestate.com/koOs;1"].getService();
        var templateSvc = Components.classes["@activestate.com/koTemplateService?type=project;1"].getService();
        var dname = os.path.join(templateSvc.getUserTemplatesDir(),
                _bundle.GetStringFromName("myTemplates.message"));

        var name = this.projectBaseName(project);

        var templatePath = ko.filepicker.saveFile(dname, name+".kpz");
        if (!templatePath) return;
        var packager = Components.classes["@activestate.com/koProjectPackageService;1"]
                          .getService(Components.interfaces.koIProjectPackageService);
        // save file dialog asked about overwrite, so if we got here, overwrite
        packager.packageProject(templatePath, project, true);
    } catch(ex) {
        this.log.exception(ex, "Error saving the current view as a template.");
    }
}

projectManager.prototype.revertProjectByURL = function(url) {
    var project = this.getProjectByURL(url)
    this.revertProject(project);
}

projectManager.prototype.revertProject = function(project) {
    this.closeProjectEvenIfDirty(project);
    this.loadProject(project.url);
}

projectManager.prototype.updateProjectMenu = function(event, menupopup) {
    //XXX: See places.js:initFilesContextMenu if there's a problem
    var projectRootName = ko.projects.manager.projectBaseName();
    this._projectLabel = projectRootName && (" (" + projectRootName + ")");
    this._finishUpdateProjectMenu(menupopup);
}

projectManager.prototype.projectBaseName = function(project) {
    if (typeof(project) == "undefined") {
        project = this.currentProject;
    }
    if (!project) return null;
    var file = project.getFile();
    return file.baseName.substr(0, file.baseName.length - file.ext.length);
};

projectManager.prototype._projectMenuMatcher = /^(.*?)( \(.*\))$/;
projectManager.prototype._projectTestLabelMatcher = /^t:project\|(.+)\|(.+)$/;
projectManager.prototype._finishUpdateProjectMenu = function(menuNode) {
    var childNodes = menuNode.childNodes;
    for (var i = 0; i < childNodes.length; i++) {
        var node = childNodes[i];
        switch(node.nodeName) {
            case "menuitem":
                if (node.getAttribute("addProjectName") == "true") {
                    var label = node.getAttribute("label");
                    var m = this._projectMenuMatcher.exec(label);
                    if (!m) {
                        if (!this._projectLabel) {
                            // nothing to do
                        } else {
                            node.setAttribute("label", label + this._projectLabel);
                        }
                    } else {
                        if (!this._projectLabel) {
                            node.setAttribute("label", m[1]);
                            // nothing to do
                        } else {
                            // Note that project might have changed since the
                            // last time this menu was updated, so update it.
                            node.setAttribute("label", m[1] + this._projectLabel);
                        }
                    }
                }
                if (node.hasAttribute("labelTest")) {
                    var test = node.getAttribute("labelTest");
                    var m = this._projectTestLabelMatcher.exec(test);
                    if (m) {
                        node.setAttribute("label",
                                          this._projectLabel ? m[1] : m[2]);
                    } else {
                        dump("Can't process test [" + test + "]\n");
                    }
                }
                break;
            case "menuseparator":
                if (false && node.id == "menu_project_mru_separator") {
                    var nextNode;
                    while (true) {
                        nextNode = node.nextSibling;
                        if (nextNode.id == "menu_project_properties_separator"){
                            break;
                        }
                        menuNode.removeChild(nextNode);
                    }
                    // And add the projects in two parts: first 5 inline,
                    // rest under a "More" submenu.
                    var prefName = 'mruProjectList';
                    if (!gPrefs.hasPref(prefName)) {
                        // Nothing left to do, convenient that we can break
                        break;
                    }
                    var mruList = gPrefs.getPref(prefName);
                }
                break;
            case "menu":
                break;
            case "menupopup":
                // This popup only handles the top-level nodes.
                break;
        }
    }
    return true;
};

projectManager.prototype.loadTemplateMenuItems = function(event, menupopup) {
    //XXX: See places.js:initFilesContextMenu if there's a problem
    var childNodes = menupopup.childNodes;
    if (childNodes[0].id != "menu_project_builtin_templates_separator") {
        // We already did this
        return true;
    }
    var templateSvc = Components.classes["@activestate.com/koTemplateService?type=project;1"].getService();
    templateSvc.loadTemplates();
    var tree = Components.classes["@mozilla.org/dom/json;1"]
    .createInstance(Components.interfaces.nsIJSON).decode(templateSvc.getJSONTree());
    var refChild = childNodes[0];
    for (var i = 0; i < tree.length; i++) {
        var entry = tree[i];
        
        var dirName = entry[0];
        var kpzPaths = entry[1];
        var m1 = document.createElementNS(XUL_NS, "menu");
        m1.setAttribute("label", dirName);
        m1.setAttribute("accesskey", dirName.substring(0, 1));
        var m2 = document.createElementNS(XUL_NS, "menupopup");
        for (var j = 0; j < kpzPaths.length; j++) {
            var path = kpzPaths[j];
            var m3 = document.createElementNS(XUL_NS, "menuitem");
            var baseName = ko.uriparse.baseName(path);
            m3.setAttribute("label", baseName);
            m3.setAttribute("oncommand",
                            ("ko.projects.manager.newProjectFromTemplate('"
                             + path
                             + "');"));
            m3.setAttribute("accesskey", baseName.substring(0, 1));
            m2.appendChild(m3);
        }
        m1.appendChild(m2);
        menupopup.insertBefore(m1, refChild);
    }
    return true;
};


projectManager.prototype.loadProject = function(url) {
    if (this.getProjectByURL(url)) {
        return null; // the project is already loaded
    }
    var project = this.findOtherWindowProjectInstanceForUrl(url);
    if (project) {
        ko.dialogs.alert(_bundle.formatStringFromName("projectIsAlreadyOpenInAnotherWindow.message",
                                                      [project.name], 1),
                         null /* text */,
                        _bundle.formatStringFromName("projectAlreadyOpened",
                                                     [project.name], 1) );
        return null;
    }
    project = Components.classes["@activestate.com/koProject;1"]
                        .createInstance(Components.interfaces.koIProject);
    window.setCursor("wait");
    try {
        this.log.info("loading url: " + url);
        project.load(url);
    } catch(e) {
        window.setCursor("auto");
        var lastErrorSvc = Components.classes["@activestate.com/koLastErrorService;1"].
            getService(Components.interfaces.koILastErrorService);
        var projectname;
        try {
            projectname = ko.uriparse.URIToLocalPath(url);
        } catch (ex) {
            projectname = url;
        }
        if (!projectname) {  // XXX Is this case cruft? I think so. --TM
            projectname = url;
        }
        ko.dialogs.alert(_bundle.formatStringFromName("unableToLoadProject.alert",
            [projectname, lastErrorSvc.getLastErrorMessage()], 2));
        return null;
    }
    return this._addProject(project);
}

projectManager.prototype._addProject = function(project) {
    this.setCurrentProject(project);
    // add project's toolbox to tools tree
    ko.toolbox2.manager.toolbox2Svc.activateProjectToolbox(project);

    // Let the file status service know it has work to do.
    var fileStatusSvc = Components.classes["@activestate.com/koFileStatusService;1"].
                        getService(Components.interfaces.koIFileStatusService);
    fileStatusSvc.updateStatusForAllFiles(Components.interfaces.koIFileStatusChecker.REASON_BACKGROUND_CHECK);

    ko.mru.addURL("mruProjectList", project.url);
    window.setCursor("auto");
    window.updateCommands('some_projects_open');
    
    return project;
}

projectManager.prototype.getProjectByURL = function(url) {
    if (!this.currentProject) return null;
    if (this.currentProject.url == url) return this.currentProject;
    return null;
}

projectManager.prototype.__defineSetter__("currentProject",
function(project)
{
    if (this._currentProject != project) {
        this._currentProject = project;
        xtk.domutils.fireEvent(window, 'current_project_changed');
        window.updateCommands('current_project_changed');
    }
    var partSvc = Components.classes["@activestate.com/koPartService;1"]
        .getService(Components.interfaces.koIPartService);
    partSvc.currentProject = project;
});

projectManager.prototype.setCurrentProject = function(project) {
    this.currentProject = project;
}

projectManager.prototype.__defineGetter__("currentProject",
function()
{
    return this._currentProject;
});

projectManager.prototype.getCurrentProject = function() {
    return this.currentProject;
}

projectManager.prototype.getSelectedProject = function() {
    return this.currentProject;
}

projectManager.prototype.registerCommands = function() {
    var em = ko.projects.extensionManager;
    em.registerCommand("cmd_closeProject",this);
    em.registerCommand("cmd_findInCurrProject",this);
    em.registerCommand("cmd_importFromFS_Project",this);
    em.registerCommand("cmd_importPackageToToolbox",this);
    em.registerCommand("cmd_newProject",this);
    em.registerCommand("cmd_openProject",this);
    em.registerCommand("cmd_openProjectFromURL",this);
    em.registerCommand("cmd_projectProperties",this);
    em.registerCommand("cmd_renameProject",this);
    em.registerCommand("cmd_replaceProject",this);
    em.registerCommand("cmd_replaceInCurrProject",this);
    em.registerCommand("cmd_revertProject",this);
    em.registerCommand("cmd_saveProject",this);
    em.registerCommand("cmd_saveProjectAs",this);
    em.registerCommand("cmd_saveProjectAsTemplate",this);
    em.registerCommand("cmd_setActiveProject",this);
    em.registerCommand("cmd_showProjectInPlaces",this);
}

projectManager.prototype.supportsCommand = function(command, item) {
    switch(command) {
    case "cmd_closeProject":
    case "cmd_findInCurrProject":
    case "cmd_importFromFS_Project":
    case "cmd_importPackageToToolbox":
    case "cmd_newProject":
    case "cmd_openProject":
    case "cmd_openProjectFromURL":
    case "cmd_projectProperties":
    case "cmd_renameProject":
    case "cmd_replaceProject":
    case "cmd_replaceInCurrProject":
    case "cmd_revertProject":
    case "cmd_saveProject":
    case "cmd_saveProjectAsTemplate":
    case "cmd_saveProjectAs":
    case "cmd_setActiveProject":
    case "cmd_showProjectInPlaces":
    default:
        return false;
    }
}

projectManager.prototype.isCommandEnabled = function(command) {
    try {
    switch(command) {
    case "cmd_setActiveProject":
        return this.currentProject != this.getSelectedProject();
        break;
    case "cmd_newProject":
    case "cmd_importPackageToToolbox":
    case "cmd_openProject":
    case "cmd_replaceProject": // same thing as cmd_openProject
    case "cmd_saveProjectAsTemplate":
        return true;
    case "cmd_closeProject":
    case "cmd_findInCurrProject":
    case "cmd_projectProperties":
    case "cmd_renameProject":
    case "cmd_replaceInCurrProject":
    case "cmd_saveProjectAs":
        return this.getSelectedProject() != null;
    case "cmd_showProjectInPlaces":
        // Verify places is loaded
        if (!ko.places) return false;
        var project = this.getSelectedProject();
        if (!project) return false;
        return ko.places.manager.currentPlace != this._parentURI(project.url);
    case "cmd_saveProject":
    case "cmd_revertProject":
        var project = this.getSelectedProject();
        return (project && project.isDirty);
    case "cmd_importFromFS_Project":
        return this.currentProject != null && !this.currentProject.live;
    }
    } catch(e) {
        this.log.exception(e);
    }
    return false; // shutup strict js
}

projectManager.prototype._parentURI = function(uri) {
    return uri.substr(0, uri.lastIndexOf("/"));
};

projectManager.prototype.doCommand = function(command) {
    var filename, uri;
    var project;
    switch(command) {
    case "cmd_showProjectInPlaces":
        ko.places.manager.openURI(this._parentURI(this.getSelectedProject().url));
        break;
    case "cmd_setActiveProject":
        this.currentProject = this.getSelectedProject();
        break;
    case "cmd_newProject":
        filename = this._getNewProjectPath();
        if (filename == null) return;
        uri = ko.uriparse.localPathToURI(filename);
        this.newProject(uri);
        break;
    case "cmd_openProject":
    case "cmd_replaceProject": // same thing as cmd_openProject, but here
        // This opens a project in a new window.
        var defaultDirectory = null;
        var defaultFilename = null;
        var title = _bundle.GetStringFromName("openProject.title");
        var defaultFilterName = _bundle.GetStringFromName("komodoProject.message");
        var filterNames = [_bundle.GetStringFromName("komodoProject.message"),
                           _bundle.GetStringFromName("all.message")];
        filename = ko.filepicker.browseForFile(defaultDirectory /* =null */,
                             defaultFilename /* =null */,
                             title /* ="Open File" */,
                             defaultFilterName /* ="All" */,
                             filterNames /* =null */)
        if (filename == null) return;
        if (command == "cmd_openProject") {
            ko.launch.newWindow(filename);
        } else {
            uri = ko.uriparse.localPathToURI(filename);
            ko.projects.open(uri);
        }
        break;
    case "cmd_closeProject":
        this.closeProject(this.getSelectedProject());
        break;
    case "cmd_saveProject":
        this.saveProject(this.getSelectedProject());
        break;
    case "cmd_saveProjectAs":
        ko.projects.saveProjectAs(this.getSelectedProject());
        break;
    case "cmd_revertProject":
        this.revertProject(this.getSelectedProject());
        break;
    case "cmd_projectProperties":
        ko.projects.fileProperties(ko.places.getItemWrapper(this.getSelectedProject().url, 'project'));
        break;
    case "cmd_renameProject":
        ko.projects.renameProject(this.getSelectedProject());
        break;
    case "cmd_saveProjectAsTemplate":
        this.saveProjectAsTemplate(this.getSelectedProject());
        break;
    case "cmd_importPackageToToolbox":
        ko.toolboxes.importPackage();
        break;
    case "cmd_importFromFS_Project":
        if (this.currentProject != null && !this.currentProject.live) {
            ko.projects.importFromFileSystem(this.currentProject);
            ko.projects.active.view.refresh(this.currentProject);
            ko.projects.active.view.selectPart(this.currentProject);
        }
        break;
    case "cmd_findInCurrProject":
        ko.launch.findInCurrProject();
        break;
    case "cmd_replaceInCurrProject":
        ko.launch.replaceInCurrProject();
        break;
    }
    return;
}

projectManager.prototype.removeItem = function(item, skipdialog) {
    if (ko.projects.BaseManager.prototype.removeItem.apply(this, [item, skipdialog])) {
        window.updateCommands('project_dirty');
        return true;
    }
    return false;
}

projectManager.prototype.removeItems = function(items, trash) {
    ko.projects.BaseManager.prototype.removeItems.apply(this, [items, trash]);
    window.updateCommands('project_dirty');
}

projectManager.prototype.addItem = function(/* koIPart */ part, /* koIPart */ parent) {
    var isprojectref = false;
    if (typeof(parent)=='undefined' || !parent) {
        try {
            /* if the target is not a project, then open it */
            isprojectref = part.QueryInterface(Components.interfaces.koIPart_ProjectRef) != null;
        } catch(e) {}
        if (isprojectref) {
            ko.open.URI(part.getStringAttribute('url'));
            return false; // return false so drag-move doesn't remove the original part
        }
        parent = this.getCurrentProject();
    } else {
        // throw an exception if we received an index instead of a koIPart
        try {
            parent.QueryInterface(Components.interfaces.koIPart);
        } catch(e) {
            throw new Error("AddItem API changed, see projectManager.js:projectManager.prototype.addItem");
        }
    }
    var isproject = false;
    try {
        /* we don't allow projects to be added to
           projects */
        isproject = part.QueryInterface(Components.interfaces.koIProject) != null;
        if (isproject) return false;
    } catch(e) {}

    try {
        // if the url is in the project already, quit
        if (part.hasAttribute('url')) {
            var url = part.getStringAttribute('url');
            if (parent.getChildWithTypeAndStringAttribute(part.type,'url',url,false))
                return false;
        }
        if (part.hasAttribute('name')) {
            if (parent.getChildWithTypeAndStringAttribute(part.type,'name',part.getStringAttribute('name'),false))
                return false;
        }
        parent.addChild(part);
        window.updateCommands('project_dirty');
        return true;
    } catch(e) { }
    return false;
}


projectManager.prototype.getItemsByURL = function(url, type) {
    if (this.currentProject) {
        var item = this.findItemByURLInProject(this.currentProject, type, url);
        if (item != null) return [item];
    }
    return [];
}

projectManager.prototype.getPartsByURL = function(url) {
    if (this.currentProject) {
        var part = this.currentProject.getChildByAttributeValue('url', url, true);
        if (part != null) return [part];
    }
    return [];
}

/* We may need to optimize this if these functions end up being called a lot
  Currently they're only called when the GUI builder creates new files */

projectManager.prototype.findItemByURL = function(url) {
    if (this.currentProject) {
        var item = this.findItemByURLInProject(this.currentProject, null, url);
        if (item != null) return item;
    }
    return null;
}

projectManager.prototype.isLivePath = function(url) {
    return this.currentProject && this.currentProject.containsLiveURL(url);
}

projectManager.prototype.findItemByURLInProject = function(project, type, url) {
    var child = project.getChildWithTypeAndStringAttribute(type, "url", url, true);
    if (child) return child;
    if (project.url == url || (project.hasAttribute('url')
                               && project.getStringAttribute('url') == url)) {
        return project;
    }
    return null;
}

projectManager.prototype.findPartByTypeAttributeValue = function(type, attribute, value) {
    if (this.currentProject) {
        var part = this.currentProject.getChildWithTypeAndStringAttribute(type,attribute, value, true);
        if (part) return part;
    }
    return null;
}

projectManager.prototype.findPartByAttributeValue = function(attribute, value) {
    if (this.currentProject) {
        var part = this.currentProject.getChildByAttributeValue(attribute, value, true);
        if (part) return part;
    }
    return null;
}

projectManager.prototype.getState = function ()
{
    if (!this.currentProject) {
        return null; // persist nothing
    }
    // Return a pref to add to the persisted 'workspace'
    var opened_projects = Components.classes['@activestate.com/koOrderedPreference;1'].createInstance();
    opened_projects.id = 'opened_projects';
    opened_projects.appendStringPref(this.currentProject.url);
    return opened_projects;
}


projectManager.prototype.setState = function (pref)
{
    try {
        var i, file_url;
        // Load projects indicated in the pref
        for (i=0; i < pref.length; i++) {
            file_url = pref.getStringPref(i);
            // skip opening of recently opened files -- that's taken care of
            // by the view persistence
            ko.projects.open(file_url, true);
        }
    } catch (e) {
        this.log.exception(e);
    }
}

projectManager.prototype.writeable = function () {
    // The project may not be writeable, but it can
    // be saved as...  so we'll always allow destructive or other
    // 'changing' operations'
    return true;
}


projectManager.prototype.effectivePrefs = function () {
    // return the current project prefs, or global prefs
    if (this.currentProject)
        return this.currentProject.prefset;
    var globalPrefSvc = Components.classes["@activestate.com/koPrefService;1"].getService(Components.interfaces.koIPrefService);
    return globalPrefSvc.prefs;
}

//-------------------------------------------------------------------------
// command implementations
//


this.open = function project_openProjectFromURL(url, skipRecentOpenFeature /* false */) {
    if (!this.manager.closeProject()) {
        return false;
    }
    var action = null;
    var opened_files = [];
    if (typeof(skipRecentOpenFeature) == 'undefined') {
        skipRecentOpenFeature = false;
    }
    if (!ko.workspace.restoreInProgress()) {
        // another part of the workspace restoration will show the tab if necessary
        ko.uilayout.ensureTabShown('places_tab');
    }

    var prefSvc = Components.classes["@activestate.com/koPrefService;1"].
                getService(Components.interfaces.koIPrefService);
    var viewStateMRU = prefSvc.getPrefs("viewStateMRU");
    if (!skipRecentOpenFeature && viewStateMRU.hasPref(url)) {
        var projectViewState = viewStateMRU.getPref(url);
        if (projectViewState.hasPref('opened_files')) {
            opened_files = projectViewState.getPref('opened_files');
            if (opened_files.length > 0) {
                action = ko.dialogs.yesNoCancel(
                    _bundle.GetStringFromName("openFilesLastHadOpen.message"),
                    "Yes", null, null, // default response, text, title
                    "open_recent_files_on_project_open");
                if (action == "Cancel") {
                    return false;
                }
            }
        }
    }
    var project = ko.projects.manager.loadProject(url)
    if (action == "Yes") {
        var v, file_url;
        for (var i=0; i < opened_files.length; i++) {
            file_url = opened_files.getStringPref(i);
            v = ko.views.manager.getViewForURI(file_url);
            if (v == null) { // don't re-open existing open filed -- it slows things down.
                ko.open.URI(file_url);
            }
        }
    }
    xtk.domutils.fireEvent(window, 'project_opened');
    return true;
}

this.saveProjectAs = function ProjectSaveAs(project)
{
    var localPath = ko.filepicker.saveFile(
            null, project.url, // default dir and filename
            _bundle.GetStringFromName("saveprojectas.title"), // title
            _bundle.GetStringFromName("komodoProject.message"), // default filter name
                [_bundle.GetStringFromName("komodoProject.message"),
                _bundle.GetStringFromName("all.message")]); // filter names to show
    if (localPath == null) {
        return false;
    }
    var url = ko.uriparse.localPathToURI(localPath);

    if (ko.projects.manager.getProjectByURL(url) != null) {
        ko.dialogs.alert(_bundle.formatStringFromName("projectIsAlreadyLoaded.alert",
            [url], 1));
        return false;
    }

    project.url = url;
    // project.name = ko.uriparse.baseName(url);
    try {
        project.save();
    } catch(ex) {
        var lastErrorSvc = Components.classes["@activestate.com/koLastErrorService;1"].
            getService(Components.interfaces.koILastErrorService);
        ko.dialogs.alert(_bundle.formatStringFromName("thereWasAnErrorSavingProject.alert",
            [project.name, lastErrorSvc.getLastErrorMessage()], 2));
        return false;
    }

    // Update the MRU projects list.
    ko.mru.addURL("mruProjectList", url);
    try {
        _obSvc.notifyObservers(this,'file_changed', project.url);
    } catch(e) { /* exception if no listeners */ }
    xtk.domutils.fireEvent(window, 'project_opened');
    window.updateCommands('project_dirty');
    return true;
}

/*
 * renameProject: a downgraded version of saveProjectAs, because
 * copying a v5-style project to a different directory leaves all
 * the file links pointing back at the original directory.
 */
this.renameProject = function ProjectRename(project)
{
    var oldKoFile = project.getFile();
    if (!oldKoFile.isLocal) {
        ko.dialogs.alert("Sorry, only local projects can be renamed");
        return;
    }
    var newname = ko.dialogs.renameFileWrapper(project.name);
    if (!newname) {
        return;
    }
    if (!this.manager.closeProject()) {
        return;
    }
    var osPathSvc = Components.classes["@activestate.com/koOsPath;1"]
        .getService(Components.interfaces.koIOsPath);
    var newPath = osPathSvc.join(oldKoFile.dirName, newname);
    try {
        // This call both updates the project's name field (while it isn't loaded)
        // and renames the file
        var partSvc = Components.classes["@activestate.com/koPartService;1"]
            .getService(Components.interfaces.koIPartService);
        partSvc.renameProject(oldKoFile.path, newPath);
            
        var newURL = ko.uriparse.localPathToURI(newPath);
        this.open(newURL);
        if ((ko.places.manager.currentPlace + "/").indexOf(newURL) == 0) {
            // Need to get places to refresh its view to show the new project file.
            ko.places.view.refreshView(-1);
            //XXX: The new name isn't showing up in places.
            // Not a critical bug, because .komodoproject files will
            // probably be hidden anyway.
        }
        xtk.domutils.fireEvent(window, 'current_project_changed');
        /*
        setTimeout(function(this_) {
                try {
                    this_.open(newURL);
                } catch(ex) {
                    ko.dialogs.alert("Failed to open "
                                    + newPath
                                    + ":"
                                    + ex);
                    this_.manager.log.exception(ex);
                }
            }, 10000, this);
        */
        /*
        var newProject = this.manager.currentProject;
        if (newProject) {
            // Update the project's name field.
            newProject.name = newname;
            newProject.save();
            _obSvc.notifyObservers(this, 'project_renamed', newURL + "##" + newname);
        }
        */
    } catch(ex) {
        ko.dialogs.alert("Failed to rename "
                         + oldKoFile.path
                         + " to "
                         + newPath
                         + ": "
                         + ex);
        // Reopen the project.
        this.open(oldKoFile.URI);
    }
}

this.onload = function() {
    ko.projects.extensionManager.init();
    ko.projects.manager = new projectManager();
    ko.projects.active = this;
}

this.handle_parts_reload = function() {
    this.manager.applyPartKeybindings();
};

// Backwards Compatibility API
this.addDeprecatedGetter = function(deprecatedName, ko_project_name) {
    if (typeof(ko_project_name) == "undefined") {
        ko_project_name = deprecatedName;
    }
    __defineGetter__(deprecatedName,
         function() {
             ko.main.__deprecatedNameTest(deprecatedName,
                                        "ko.projects." + ko_project_name);
             return ko.projects[ko_project_name];
        });
}

}).apply(ko.projects);

// dropped: gProjectManager // ko.projects.manager
// dropped: gFocusedProjectView // ko.projects.active
