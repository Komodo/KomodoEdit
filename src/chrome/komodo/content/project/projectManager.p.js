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
 * Portions created by ActiveState Software Inc are Copyright (C) 2000-2011
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

const { classes: Cc, interfaces: Ci, utils: Cu } = Components;

var _bundle = Cc["@mozilla.org/intl/stringbundle;1"]
                .getService(Ci.nsIStringBundleService)
                .createBundle("chrome://komodo/locale/projectManager.properties");

const XUL_NS = "http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul";
this.manager = null;

var _obSvc = Cc["@mozilla.org/observer-service;1"].
        getService(Ci.nsIObserverService);

const {XPCOMUtils} = Cu.import("resource://gre/modules/XPCOMUtils.jsm", {});

//gone: ko.projects.manager.lastCurrentProject
//gone: ko.projects.manager.activeView
//gone: ko.projects.manager._projects
//gone: ko.projects.manager.getProjectsMenu (and xul tag)
//reinstated: ko.projects.manager.hasProject
//gone: ko.projects.manager.managers
//gone: ko.projects.manager.getAllProjects
//gone: ko.projects.manager.getFocusedProjectView
//gone: ko.projects.manager.findItemByAttributeValue
//gone: ko.toolboxes.importPackage -- can't import packages into toolboxes now

//----- The projectManager class manages the set of open projects and
// which project is 'current'.

// "spv" views refer to project views with one opened project + the recent projects
// "mpv" views refer to project views with multiple opened projects (where one is active)
// this._currentProject is used for both the spv and mpv views
// this._projects is used only for the mpv view

function projectManager() {
    this.name = 'projectManager';
    ko.projects.BaseManager.apply(this, []);
    this.log = ko.logging.getLogger('projectManager');
    //this.log.setLevel(ko.logging.LOG_DEBUG);
    this._projects = [];
    this._spv_urls = [];
    this._mpv_urls = [];
    this._currentProject = null;
    // register our command handlers
    this.registerCommands();
    this._ensureProjectPaneVisible = true;
    this._lastCurrentProject = null;
    this.viewMgr = null;
    this.single_project_view = !this.initProjectViewPref(ko.prefs);
    window.addEventListener("view_document_detaching",
                            this.handle_view_document_detaching,
                            false);

    // things to call upon setting this.viewMgr
    this._callbacksPendingViewMgr = [];
}

// The following two lines ensure proper inheritance (see Flanagan, p. 144).
projectManager.prototype = new ko.projects.BaseManager();
projectManager.prototype.constructor = projectManager;

projectManager.prototype.initProjectViewPref = function(prefset) {
    // This is in terms of whether to use a multiple project view or not
    const DEFAULT_MULTIPLE_PROJECT_VIEW_MODE = false;
    if (!prefset.hasPref("places.multiple_project_view")) {
        prefset.setBooleanPref("places.multiple_project_view", DEFAULT_MULTIPLE_PROJECT_VIEW_MODE);
        return DEFAULT_MULTIPLE_PROJECT_VIEW_MODE;
    }
    return prefset.getBooleanPref("places.multiple_project_view");
};

projectManager.prototype.switchProjectView = function(single_project_view) {
    var i, listLen, urlList;
    var currentProjectURL = this.currentProject === null ? null : this.currentProject.url;
    var treeOwner;
    if (single_project_view) {
        this._mpv_urls = this._projects.map(function(p) p.url);
        urlList = this._spv_urls;
        treeOwner = ko.places.projects_SPV;
    } else {
        this._spv_urls = this._projects.map(function(p) p.url);
        urlList = this._mpv_urls;
        treeOwner = ko.places.projects;
    }
    this.closeAllProjects();
    if (treeOwner.projectsTreeView) {
        treeOwner.projectsTreeView.clearTree();
    }
    // Now reopen the new view with the other type of project view.
    this.single_project_view = single_project_view;
    listLen = urlList.length;
    for (i = 0; i < listLen; i++) {
        ko.projects.open(urlList[i],
                         false /* skipRecentOpenFeature */,
                         false /* ensureVisible */);
    }
    if (single_project_view && treeOwner.projectsTreeView) {
        treeOwner.load_MRU_Projects();
    } else {
        if (currentProjectURL !== null ) {
            var openedIdx = this._projects.map(function(p) p.url).indexOf(currentProjectURL);
            if (openedIdx != -1) {
                this.currentProject = this._projects[openedIdx];
            } else {
                ko.projects.open(currentProjectURL,
                                 false /* skipRecentOpenFeature */,
                                 false /* ensureVisible */);
                //dump("**************** Need to re-activate proj " + currentProjectURL + "\n");
            }
        }
    }
};

projectManager.prototype.setViewMgr = function(projectViewMgr) {
    this.viewMgr = projectViewMgr;
    if (this.viewMgr) {
        while (this._callbacksPendingViewMgr.length > 0) {
            try {
                this._callbacksPendingViewMgr.shift()();
            } catch (ex) {
                this.log.exception(ex);
            }
        }
    }
}

projectManager.prototype.hasProject = function(project) {
    return this._projects.indexOf(project) > -1;
}

projectManager.prototype._getOpenURLsInProject = function(project) {
    // Find out if any child elements are currently open
    var docs = ko.views.manager.topView.getDocumentViewList(true);
    var opened = [];
    var url;
    for (var i = 0; i < docs.length; i++) {
        if (docs[i].koDoc && docs[i].koDoc.file) {
            url = docs[i].koDoc.file.URI;
            if (project.belongsToProject(url)) {
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

projectManager.prototype.closeProjectEvenIfDirty_SingleProjectView = function(project) {
    if (typeof(project) == "undefined") project = this.currentProject;
    if (!project) {
        // No project to close.
        return true;
    }
    ko.toolbox2.manager.toolbox2Svc.deactivateProjectToolbox(project);
    
    // the active project has been reset
    // Forget about any notifications made for this project.
    this.notifiedClearProject(project);
    this._projects.splice(0, 1);
    // Make an unopened project based on project, and add it at same position
    var newUnopenedProject = Components.classes["@activestate.com/koUnopenedProject;1"]
                    .createInstance(Components.interfaces.koIUnopenedProject);
    newUnopenedProject.url = project.url;
    newUnopenedProject.isDirty = false;
    var projectsTreeView = ko.places.projects_SPV.projectsTreeView;
    var index = projectsTreeView.getIndexByPart(project);
    project.close();
    this.currentProject = null;
    projectsTreeView.removeProject(project);

    if (index == -1) {
        projectsTreeView.addUnopenedProject(newUnopenedProject);
    } else {
        projectsTreeView.addUnopenedProjectAtPosition(newUnopenedProject, index);
    }
    ko.mru.addURL("mruProjectList", project.url);
    window.updateCommands('some_projects_open');
    return true;
}

projectManager.prototype.closeProjectEvenIfDirty = function(project) {
    if (this.single_project_view) {
        return this.closeProjectEvenIfDirty_SingleProjectView(project);
    }
    // Remove the project node/part from the Projects tree.
    if (this.viewMgr) {
        this.viewMgr.removeProject(project);
    }
    if (typeof(project) == "undefined") project = this.currentProject;
    ko.toolbox2.manager.removeProject(project);
    
    // the active project has been reset
    if (this.currentProject) {
        this._lastCurrentProject = this.currentProject;
    }
    this.setCurrentProjectFromPartService();

    // Forget about any notifications made for this project.
    this.notifiedClearProject(project);

    // remove the project from our list
    try {
        var id = this._projects.indexOf(project);
        this._projects.splice(id, 1);
    } catch(e) {
        // XXX FIXME SMC currently broken with live projects
    }
    project.close();
    
    ko.mru.addURL("mruProjectList", project.url);
    if (!ko.main.windowIsClosing) {
        // bug 101553: don't do this when shutting down
        if (this._projects.length == 0) {
            window.updateCommands('some_projects_open');
        }
        if (this.viewMgr) {
            this.viewMgr.refresh(project);
        }
        window.updateCommands('some_projects_open');
    }
    return true;
}

projectManager.prototype.closeProject = function(project /*=this.currentProject*/) {
    if (typeof(project) == "undefined") project = this.currentProject;
    if (!project) {
        // No project to close.
        return true;
    }
    if (project.isDirty  || project.isPrefDirty) {
        var doSave = false;
        if (project.isDirty) {
            var question = _bundle.formatStringFromName("saveChangesToProject.message", [project.name], 1);
            var answer = ko.dialogs.yesNoCancel(question);
            if (answer == "Cancel") {
                return false;
            } else {
                doSave = (answer == "Yes");
            }
        } else {
            doSave = true;
        }
        if (doSave) {
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

/**
 * Return a list of the opened Komodo projects.
 * 
 * @returns {array} - A copy of the projects list.
 */
projectManager.prototype.getAllProjects= function() {
    return this._projects.slice();
}

projectManager.prototype.getDirtyProjects = function() {
    return this._projects.filter(function(p) {
            return p.isDirty || p.isPrefDirty;
        });
}

projectManager.prototype._closeAllProjectsByFunc = function(func) {
    for (var i = this._projects.length - 1; i >= 0; i--) {
        if (!func.call(this, this._projects[i])) {
            this._projects.splice(i + 1);
            return false;
        }
    }
    this._projects = [];
    this.currentProject = null;
    return true;
}

projectManager.prototype.closeAllProjects = function() {
    return this._closeAllProjectsByFunc(this.closeProject);
}

projectManager.prototype.closeAllProjectsEvenIfDirty = function() {
    return this._closeAllProjectsByFunc(this.closeProjectEvenIfDirty);
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
 * @param {string} projectUrl  The URL of the project to check for.
 * @returns {Components.interfaces.koIProject}  The project found, else null.
 */
projectManager.prototype.findOtherWindowProjectInstanceForUrl = function(projectUrl) {
    var otherProject;
    var otherWindow;
    var koWindowList = ko.windowManager.getWindows();
    for (var i=0; i < koWindowList.length; i++) {
        otherWindow = koWindowList[i];
        if (otherWindow != window
            && otherWindow.ko
            && otherWindow.ko.projects) {
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
 * @param {boolean} skip_scc_check
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
        xtk.domutils.fireEvent(window, 'current_project_saved');
        window.updateCommands('project_dirty');
    }
    return true;
}

projectManager.prototype.newProject = function(url) {
    if (this.single_project_view && !this.closeProject()) {
        return false;
    }
    var project = Components.classes["@activestate.com/koProject;1"]
                                        .createInstance(Components.interfaces.koIProject);
    project.create();
    project.url = url;
    return this._saveNewProject(project) ? project : null;
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
    this._addProject(project, false);
    xtk.domutils.fireEvent(window, 'project_opened');
    try {
        _obSvc.notifyObservers(this, 'file_project', project.url);
    } catch(e) { /* exception if no listeners */ }
    return true;
}

/**
 * Browse for and return a path for a new Komodo project file.
 *
 * @param {String} directory  (Optional) The directory to create the project in.
 * @param {String} name  (Optional) The project name.
 */
projectManager.prototype._getNewProjectPath = function(directory, name) {
    const projectSuffix = ".komodoproject";
    var defaultDir;
    if (directory) {
        defaultDir = ko.uriparse.URIToLocalPath(directory);
    } else {
        defaultDir = (this.currentProject
                      ? this.currentProject.getFile().dirName
                      : ko.window.getHomeDirectory());
    }
    if (!name) {
        name = _bundle.GetStringFromName("newProject.defaultFileName");
    }

    var path = ko.filepicker.saveFile(
        defaultDir,
        name + projectSuffix, // defaultFilename
        _bundle.GetStringFromName("newProject.title"), // title
        _bundle.GetStringFromName("komodoProject.message"), // defaultFilterName
        [_bundle.GetStringFromName("komodoProject.message"),
         _bundle.GetStringFromName("all.message")]); // filterNames
    // And repeat the check from filepicker/saveFile:
    if (!path) {
        return path;
    }
    var ext = ko.uriparse.ext(path);
    if (ext != projectSuffix) {
        path += projectSuffix;
    }
    return path;
};

projectManager.prototype.newProjectFromTemplate = function(templatePath) {
    try {
        this.log.info("doing newTemplate: ");
        if (this.single_project_view && !this.closeProject()) {
            return false;
        }
        var lastErrorSvc = Components.classes['@activestate.com/koLastErrorService;1'].getService();
        var projectPath;
        if (typeof(templatePath) == "undefined") {
            // Get template selection from the user.
            var obj = new Object();
            obj.type = "project";
            obj.filename = _bundle.GetStringFromName("newProject.defaultFileName") + ".komodoproject";
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

projectManager.prototype._getRemoteURIs = function (project) {
    var items;
    var o1 = {}, o2 = {};
    project.getChildrenByType("file", true, o1, {});
    project.getChildrenByType("livefolder", true, o2, {});
    return (o1.value.concat(o2.value).
            map(function(item) item.getFile()).
            filter(function(koFile) koFile.isRemoteFile).
            map(function(koFile) koFile.URI));
};
projectManager.prototype.saveProjectAsTemplate = function (project) {
    try {
        var remote_uris = this._getRemoteURIs(project);
        if (remote_uris.length) {
            const sep = ", ";
            var uriList = remote_uris.join(sep);
            if (uriList.length > 300) {
                var lastSep = uriList.substring(0, 300).lastIndexof(sep);
                var part1 = uriList.substring(0, lastSep);
                var part2 = uriList.substring(lastSep + sep.length);
                var remainingParts = part2.split(sep).length;
                uriList = part1;
                if (remainingParts.length == 1) {
                    uriList += _bundle.GetStringFromName("and 1 other");
                } else {
                    uriList += _bundle.formatStringFromName("and X others",
                                                        [remainingParts.length], 1);
                }
            }
            uriList = (remote_uris.length == 1 ?
                       _bundle.formatStringFromName("For URI X", [uriList], 1) :
                       _bundle.formatStringFromName("For URIs X", [uriList], 1));
                       
            var msg = _bundle.GetStringFromName("Project templates with remote items arent supported");
            ko.notifications.add(msg, ["projects"], "saveProjectAsTemplate", { details: uriList,
                                 severity: Components.interfaces.koINotification.SEVERITY_INFO,} );
            return;
        }
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
    try {
        this.closeProjectEvenIfDirty(project);
    } catch(ex) {
        this.log.exception(ex);
    }
    try {
        this.loadProject(project.url);
    } catch(ex) {
        this.log.exception(ex);
    }
}

projectManager.prototype.updateProjectMenu = function(event, menupopup, projectType) {
    //XXX: See places.js:initFilesContextMenu if there's a problem
    var project = this[projectType + "Project"] || this.selectedOrCurrentProject();
    var projectBaseName = this.projectBaseName(project);
    this._projectLabel = (projectBaseName
                          ? (" (" + projectBaseName + ")")
                          : null);
    this._finishUpdateProjectMenu(menupopup);
}

projectManager.prototype.selectedOrCurrentProject = function() {
    return this.getSelectedProject() || this.currentProject;
};

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
    var childNodes = menuNode.childNodes, addLabel, label;
    var currentProjectIsClosed = !ko.projects.manager.currentProject;
    for (var i = 0; i < childNodes.length; i++) {
        var node = childNodes[i];
        switch(node.nodeName) {
            case "menuitem":
                label = node.getAttribute("label");
                if (node.getAttribute("disableIfCurrentProjectIsClosed") == "true"
                    && currentProjectIsClosed) {
                    node.setAttribute("disabled", 'true');
                    addLabel = false;
                } else {
                    node.removeAttribute("disabled");
                    if (node.getAttribute("addProjectName") == "true") {
                        addLabel = true;
                    } else {
                        break; // do nothing
                    }
                }
                if (addLabel !== null) {
                    var m = this._projectMenuMatcher.exec(label);
                    if (!m) {
                        if (this._projectLabel && addLabel) {
                            node.setAttribute("label", label + this._projectLabel);
                        }
                    } else if (!this._projectLabel || !addLabel) {
                        node.setAttribute("label", m[1]);
                    } else {
                        // Note that project might have changed since the
                        // last time this menu was updated, so update it.
                        node.setAttribute("label", m[1] + this._projectLabel);
                    }
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
    var i = 0, childNode, lim = childNodes.length;
    var refChild = null;
    // Always walk backwards when deleting nodes by index
    for (i = lim - 1; i >= 0; i--) {
        childNode = childNodes[i];
        if (childNode.id == "menu_project_builtin_templates_separator") {
            refChild = childNode;
        } else if (childNode.getAttribute("_from_template") == "true") {
            menupopup.removeChild(childNode);
        }
    }
    if (refChild === null) {
        ko.dialogs.internalError("Unexpected menu configuration",
                                 "Komodo can't find menu_project_builtin_templates_separator in the templates menu.");
        return false;
    }
    var templateSvc = Components.classes["@activestate.com/koTemplateService?type=project;1"].getService();
    templateSvc.loadTemplates();
    var tree = JSON.parse(templateSvc.getJSONTree());
    var needMenuSeparator = false;
    var menuitem;
    for (var i = 0; i < tree.length; i++) {
        var kpzPaths = tree[i];
        var kpzLen = kpzPaths.length;
        if (kpzLen > 0) {
            if (needMenuSeparator) {
                menuitem = document.createElementNS(XUL_NS, 'menuseparator');
                menuitem.id = "menu_project_popup_templates_" + i + "_separator";
                menuitem.setAttribute("_from_template", "true");
                menupopup.insertBefore(menuitem, refChild);
            } else {
                needMenuSeparator = true;
            }
        }
        for (var j = 0; j < kpzLen; j++) {
            var path = kpzPaths[j];
            menuitem = document.createElementNS(XUL_NS, "menuitem");
            var baseName = ko.uriparse.baseName(path);
            var dotPosn = baseName.lastIndexOf(".");
            if (dotPosn > 0) {
                baseName = baseName.substr(0, dotPosn);
            }
            menuitem.setAttribute("label", baseName);
            menuitem.setAttribute("oncommand",
                            ("ko.projects.manager.newProjectFromTemplate('"
                             + path.replace(/\\/g, '\\\\')
                             + "');"));
            menuitem.setAttribute("accesskey", baseName.substring(0, 1));
            menuitem.setAttribute("_from_template", "true");
            menupopup.insertBefore(menuitem, refChild);
        }
    }
    return true;
};


projectManager.prototype.loadProject = function(url) {
    if (this.getProjectByURL(url)) {
        return; // the project is already loaded
    }
    var project = this.findOtherWindowProjectInstanceForUrl(url);
    if (project) {
        ko.dialogs.alert(_bundle.formatStringFromName("projectIsAlreadyOpenInAnotherWindow.message",
                                                      [project.name], 1),
                         null /* text */,
                        _bundle.formatStringFromName("projectAlreadyOpened",
                                                     [project.name], 1) );
        return;
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
        var message = _bundle.formatStringFromName("unableToLoadProject.alert",
            [projectname, lastErrorSvc.getLastErrorMessage()], 2);
        if (!url) {
            ko.dialogs.alert(message);
        } else {
            message += " " + _bundle.GetStringFromName("unableToLoadProjectRemoveConfirm.alert");
            var remove = ko.dialogs.okCancel(message);
        }
        // Assume the error is that the file doesn't exist.
        // Currently all we can do is test against the English value of
        // lastErrorSvc.getLastErrorMessage(), but that won't work
        // if it's ever localized.
        if (url && remove == "OK") {
            ko.mru.deleteValue("mruProjectList", url, true);
            ko.places.projects_SPV.rebuildView(); // force refresh (tree.invalidate() doesnt suffice)
        }
        return;
    }
    this._addProject(project, false);
}

projectManager.prototype._addProject = function(project, delayed/*=false*/) {
    if (typeof(delayed) == "undefined") delayed = false;
    if (!delayed && !this.viewMgr) {
        // Wait for things to load...
        this._callbacksPendingViewMgr.push(this._addProject.bind(this, project, true));
        return;
    } else if (delayed && !this.viewMgr) {
        this.log.warn("_addProject: call delayed, this.viewMgr still null");
    }
    if (!this.single_project_view) {
        this._projects.push(project);
    } else {
        this._projects = [project];
    }
    // add project to project tree
    if (this.viewMgr) {
        this.viewMgr.addProject(project, 0);
        this.viewMgr.refresh(project);
    }
    this.setCurrentProject(project);
    ko.lint.initializeGenericPrefs(project.prefset)
    if (this.single_project_view) {
        ko.mru.addURL("mruProjectList", project.url);
    }
    ko.toolbox2.manager.addProject(project);

    // Let the file status service know it has work to do.
    var fileStatusSvc = Components.classes["@activestate.com/koFileStatusService;1"].
                        getService(Components.interfaces.koIFileStatusService);
    fileStatusSvc.updateStatusForAllFiles(Components.interfaces.koIFileStatusChecker.REASON_BACKGROUND_CHECK);

    ko.mru.addURL("mruProjectList", project.url);
    window.setCursor("auto");
    window.updateCommands('some_projects_open');
    
    return;
}

projectManager.prototype.getProjectByURL = function(url) {
    for (var i = this._projects.length - 1; i >= 0; --i) {
        var project = this._projects[i];
        if (project.url == url) {
            return project;
        }
    }
    return null;
}

projectManager.prototype.fireProjectChangedEvent = function(project) {
    if (this._currentProject != project) {
        this._currentProject = project;
        xtk.domutils.fireEvent(window, 'current_project_changed');
        window.updateCommands('current_project_changed');
    }
};

projectManager.prototype.__defineSetter__("currentProject",
function(project)
{
    this.fireProjectChangedEvent(project);
    var partSvc = Components.classes["@activestate.com/koPartService;1"]
        .getService(Components.interfaces.koIPartService);
    partSvc.currentProject = project;
});

projectManager.prototype.setCurrentProject = function(project) {
    this.currentProject = project;
    if (this.viewMgr) {
        this.viewMgr.setCurrentProject(project);
    }
}

projectManager.prototype.setCurrentProjectFromPartService = function() {
    var partSvc = Components.classes["@activestate.com/koPartService;1"]
        .getService(Components.interfaces.koIPartService);
    var project = partSvc.currentProject;
    this.currentProject = project;
};

projectManager.prototype.__defineGetter__("currentProject",
function()
{
    return this._currentProject;
});

projectManager.prototype.getCurrentProject = function() {
    return this.currentProject;
}

projectManager.prototype.getSelectedProject = function() {
    if (this.viewMgr) {
        var node = this.viewMgr.getSelectedItem();
        if (node) {
            return node.type == "project" ? node.project : null;
        }
    }
    return this.currentProject;
}

Object.defineProperty(projectManager.prototype, "selectedProject", {
    get: function() this.getSelectedProject(),
    configurable: true, enumerable: true,
});

projectManager.prototype.registerCommands = function() {
    var em = ko.projects.extensionManager;
    em.registerCommand("cmd_closeProject",this);
    em.registerCommand("cmd_closeAllProjects",this);
    em.registerCommand("cmd_findInCurrProject",this);
    em.registerCommand("cmd_importPackageToToolbox",this);
    em.registerCommand("cmd_newProject",this);
    em.registerCommand("cmd_openProject",this);
    em.registerCommand("cmd_sampleProject",this);
    em.registerCommand("cmd_openProjectNewWindow",this);
    em.registerCommand("cmd_openProjectFromURL",this);
    em.registerCommand("cmd_projectProperties",this);
    em.registerCommand("cmd_renameProject",this);
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
    case "cmd_closeAllProjects":
    case "cmd_findInCurrProject":
    case "cmd_importPackageToToolbox":
    case "cmd_newProject":
    case "cmd_openProject":
    case "cmd_sampleProject":
    case "cmd_openProjectNewWindow":
    case "cmd_openProjectFromURL":
    case "cmd_projectProperties":
    case "cmd_renameProject":
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
    var project;
    try {
    switch(command) {
    case "cmd_setActiveProject":
        var selectedProject = this.getSelectedProject();
        return selectedProject && this.currentProject != selectedProject;
        break;
    case "cmd_newProject":
    case "cmd_importPackageToToolbox":
    case "cmd_openProject":
    case "cmd_sampleProject":
    case "cmd_openProjectNewWindow":
    case "cmd_saveProjectAsTemplate":
        return true;
    case "cmd_closeProject":
    case "cmd_findInCurrProject":
    case "cmd_projectProperties":
    case "cmd_replaceInCurrProject":
    case "cmd_saveProjectAs":
        return this.currentProject != null;
    case "cmd_renameProject":
        project = this.currentProject;
        return project && !project.isDirty;
    case "cmd_showProjectInPlaces":
        // Verify places is loaded
        if (!ko.places) return false;
        project = this.currentProject;
        if (!project) return false;
        return !ko.places.manager.placeIsAtProjectDir(project);
    case "cmd_saveProject":
    case "cmd_revertProject":
        project = this.currentProject;
        return (project && project.isDirty);
    case "cmd_closeAllProjects":
        return this._projects.length > 0;
    }
    } catch(e) {
        this.log.exception(e);
    }
    return false; // shutup strict js
}

projectManager.prototype._parentURI = function(uri) {
    return uri.substr(0, uri.lastIndexOf("/"));
};

/**
 * Create new project.
 *
 * @param {String} directory  (Optional) The directory to create the project in.
 * @param {String} name  (Optional) The project name.
 */
projectManager.prototype.createNewProject = function(directory, name) {
    var filename = this._getNewProjectPath(directory, name);
    if (filename == null) return null;
    var uri = ko.uriparse.localPathToURI(filename);
    return this.newProject(uri);
};


/**
 * Get the selected project, and pass it to the callback
 * @param callback function
 * @param noProjectCallback function
 * @returns whatever the callbacks return, or undefined
 */

projectManager.prototype.workOnSelectedProject = function(callback, noProjectCallback) {
    var project = this.getSelectedProject();
    if (project) {
        return callback(project);
    } else if (noProjectCallback) {
        return noProjectCallback();
    } else {
        var msg = "The selected item isn't an opened project; request ignored";
        require("notify/notify").send(msg, "projects", {priority: "warning"});
        return undefined;
    }
}

projectManager.prototype.doCommand = function(command) {
    var filename, uri;
    var project;
    var this_ = this;
    switch(command) {
    case "cmd_showProjectInPlaces":
        this.workOnSelectedProject(function(project) {
            ko.places.manager.moveToProjectDir(project);
        });
        break;
    case "cmd_setActiveProject":
        this.workOnSelectedProject(function(project) {
            this_.currentProject = project;
        });
        break;
    case "cmd_newProject":
        this.createNewProject();
        break;
    case "cmd_openProject":
    case "cmd_openProjectNewWindow":
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
        if (command == "cmd_openProjectNewWindow") {
            ko.launch.newWindow(filename);
        } else {
            uri = ko.uriparse.localPathToURI(filename);
            ko.projects.open(uri);
        }
        break;
    case "cmd_sampleProject":
            try {
                var koDirSvc = Cc["@activestate.com/koDirs;1"].getService(Ci.koIDirs);
                var osPathSvc = Cc["@activestate.com/koOsPath;1"].getService(Ci.koIOsPath);
                var sampleProjectPath = osPathSvc.joinlist(3,
                        [koDirSvc.userDataDir, "samples", "sample_project.komodoproject"]);
                
                if (! osPathSvc.exists(sampleProjectPath)) {
                    var response = ko.dialogs.okCancel(_bundle.formatStringFromName(
                                "theSampleProjectCouldNotBeFound.message",
                                [sampleProjectPath], 1), "Cancel");
                    if (response == "OK") {
                        var initSvc = Cc["@activestate.com/koInitService;1"].getService(Ci.koIInitService);
                        initSvc.installSamples(true);
                    } else {
                        return;
                    }
                }
                var sampleProjectUrl = ko.uriparse.pathToURI(sampleProjectPath);
                ko.projects.open(sampleProjectUrl);
            } catch (ex) {
                this.log.exception(ex,"cmd_sampleProject error: "+ex);
            }
        break;
    case "cmd_closeProject":
        this.closeProject(this.currentProject);
        break;
    case "cmd_closeAllProjects":
        this.closeAllProjects();
        break;
    case "cmd_saveProject":
        if (this.currentProject) {
            this.saveProject(this.currentProject);
        }
        break;
    case "cmd_saveProjectAs":
        if (this.currentProject) {
            ko.projects.saveProjectAs(this.currentProject);
        }
        break;
    case "cmd_revertProject":
        if (this.currentProject) {
            this.revertProject(this.currentProject);
        }
        break;
    case "cmd_projectProperties":
        if (this.currentProject) {
            var item = ko.places.getItemWrapper(this.currentProject.url, 'project');
            ko.projects.fileProperties(item, null, true);
        }
        break;
    case "cmd_renameProject":
        if (this.currentProject) {
            ko.projects.renameProject(this.currentProject);
        }
        break;
    case "cmd_saveProjectAsTemplate":
        if (this.currentProject) {
            this.saveProjectAsTemplate(this.currentProject);
        }
        break;
    case "cmd_importPackageToToolbox":
        ko.toolboxes.importPackage();
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
        parent.addChild(part);
        if (ko.places) {
            var treeOwner = (this.single_project_view
                             ? ko.places.projects_SPV
                             : ko.places.projects);
            // Ensure the added item is visible, bug 71373.
            // Broken with v7 work: bug 91491 (SPV only?)
            treeOwner.refreshParentShowChild(parent, part);
        }
        window.updateCommands('project_dirty');
        
        return true;
    } catch(e) { }
    return false;
}


projectManager.prototype.getItemsByURL = function(url, type) {
    var items = [];
    var item;
    for (var i in this._projects) {
        item = this.findItemByURLInProject(this._projects[i], type, url);
        if (item != null) items.push(item);
    }
    return items;
}

projectManager.prototype.getPartsByURL = function(url) {
    var part;
    var parts = [];
    for (var i in this._projects) {
        part = this._projects[i].getChildByAttributeValue('url', url, true);
        if (part != null) parts.push(part);
    }
    return parts;
}

/* We may need to optimize this if these functions end up being called a lot
  Currently they're only called when the GUI builder creates new files */

projectManager.prototype.findItemByURL = function(url) {
    for (var i in this._projects) {
        var item = this.findItemByURLInProject(this._projects[i], null, url);
        if (item != null) return item;
    }
    return null;
}

projectManager.prototype.isLivePath = function(url) {
    for (var i in this._projects) {
        if (this._projects[i].containsLiveURL(url)) return true;
    }
    return false;
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
    var part;
    if (this.currentProject) {
        part = this.currentProject.getChildWithTypeAndStringAttribute(type,attribute, value, true);
        if (part) return part;
    }
    for (var i in this._projects) {
        if (this._projects[i] == this.currentProject) continue; // skip current project, already looked there
        part = this._projects[i].getChildWithTypeAndStringAttribute(type,attribute, value, true);
        if (part) return part;
    }
    return null;
}

projectManager.prototype.findPartByAttributeValue = function(attribute, value) {
    var part;
    if (this.currentProject) {
        part = this.currentProject.getChildByAttributeValue(attribute, value, true);
        if (part) return part;
    }
    for (var i in this._projects) {
        if (this._projects[i] == this.currentProject) continue; // skip current project, already looked there
        part = this._projects[i].getChildByAttributeValue(attribute, value, true);
        if (part) return part;
    }
    return null;
}

/**
 * Project state:
 * "opened_projects_v7":
 *   { "spv_projects": [ json array, but only with current project ],
 *     "mpv_projects": [ json array of projects ]
 *   }
 */

projectManager.prototype.getState = function()
{
    var i, project, url, listLen;
    var pref = Components.classes["@activestate.com/koPreferenceSet;1"].createInstance();
    pref.id = 'opened_projects_v7';
    var spv_projects = Components.classes['@activestate.com/koOrderedPreference;1'].createInstance();
    var mpv_projects = Components.classes['@activestate.com/koOrderedPreference;1'].createInstance();
    if (this.single_project_view) {
        if (this.currentProject) {
            pref.setStringPref("spv_projects", JSON.stringify([this.currentProject.url]));
        } else {
            pref.setStringPref("spv_projects", JSON.stringify([]));
        }
        pref.setStringPref("mpv_projects", JSON.stringify(this._mpv_urls));
    } else {
        pref.setStringPref("spv_projects", JSON.stringify(this._spv_urls));
        pref.setStringPref("mpv_projects", JSON.stringify(this._projects.map(function(p) p.url)));
        if (this.viewMgr) {
            this._projects.forEach(function(project) {
                    this.viewMgr.savePrefs(project);
                }.bind(this));
        }
    }
    return pref;
}

projectManager.prototype.setState = function(pref)
{
    try {
        try {
            this._spv_urls = JSON.parse(pref.getStringPref("spv_projects"));
        } catch(ex) {
            this.log.error("Can't get pref spv_projects");
            this._spv_urls = [];
        }
        try {
            this._mpv_urls = JSON.parse(pref.getStringPref("mpv_projects"));
        } catch(ex) {
            this.log.error("Can't get pref mpv_projects");
            this._mpv_urls = [];
        }
        var urlList = this.single_project_view ? this._spv_urls : this._mpv_urls;
        urlList.forEach(function(url) {
                ko.projects.open(url,
                                 false /* skipRecentOpenFeature */,
                                 false /* ensureVisible */);
            });
    } catch (e) {
        this.log.exception(e);
    }
};

projectManager.prototype._loadProjectsFromOrderedPrefSet = function(pref)
{
    var i, file_url;
    // Load projects indicated in the pref
    for (i=0; i < pref.length; i++) {
        file_url = pref.getStringPref(i);
        // skip opening of recently opened files -- that's taken care of
        // by the view persistence
        ko.projects.open(file_url, true);
    }
};

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

projectManager.prototype.handle_view_document_detaching = function(event) {
    // Don't remove the document immediately, in case we're closing
    // files due to closing their owning project.
    var view = event.originalTarget;
    if (!view || !view.koDoc || !view.koDoc.file) {
        return;
    }
    var detaching_url = view.koDoc.file.URI;
    if (!detaching_url) {
        return;
    }
    setTimeout(_finish_handle_view_document_detaching, 300, detaching_url);
};

function _finish_handle_view_document_detaching(detaching_url) {
    var currentProject = ko.projects.manager.currentProject;
    if (!currentProject)  {
        return;
    }
    var projectURL = currentProject.getFile().URI;
    var prefSvc = Components.classes["@activestate.com/koPrefService;1"].
                getService(Components.interfaces.koIPrefService);
    var viewStateMRU = prefSvc.getPrefs("viewStateMRU");
    if (!viewStateMRU.hasPref(projectURL)) {
        return;
    }
    var projectViewState = viewStateMRU.getPref(projectURL);
    if (!projectViewState) {
        return;
    }
    else if (!projectViewState.hasPref('opened_files')) {
        return;
    }
    var openedURIs = projectViewState.getPref('opened_files');
    var idx = openedURIs.findStringPref(detaching_url);
    if (idx >= 0) {
        openedURIs.deletePref(idx, 1);
        //dump("**************** Remove URI "
        //     + detaching_url
        //     + " at posn "
        //     + idx
        //     + " from project "
        //     + currentProject.url
        //     + "\n");
        projectViewState.setPref('opened_files', openedURIs);
    }
}

//-------------------------------------------------------------------------
// command implementations
//


this.open = function project_openProjectFromURL(url,
                                                skipRecentOpenFeature /* false */,
                                                ensureVisible /* true */) {
    if (ko.projects.manager.getAllProjects().map(function(p) p.url).indexOf(url) >= 0) {
        this.log.debug("Project " + url + " is already opened\n");
        return false;
    }
    if (url.indexOf("file:/") != 0) {
        ko.dialogs.alert(_bundle.formatStringFromName("remote projects arent supported for X",
                                                      [url], 1));
        return false;
    }
    if (this.manager.single_project_view) {
        if (this.manager.currentProject) {
            if (this.manager.currentProject.url == url) {
                return true;
            }
            if (!this.manager.closeProject(this.manager.currentProject)) {
                return false;
            }
        }
    }
    var action = null;
    var opened_files = [];
    if (typeof(skipRecentOpenFeature) == 'undefined') {
        skipRecentOpenFeature = false;
    }
    if (typeof(ensureVisible) == 'undefined') {
        ensureVisible = true;
    }
    if (ensureVisible) {
        // another part of the workspace restoration will show the tab if necessary
        ko.uilayout.ensureTabShown('placesViewbox');
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
    ko.projects.manager.loadProject(url);
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
    setTimeout(function() {
        // Need to remember if the project wants to be made visible, bug 87868.
        // This is required for Places project_open handling to work correctly.
        ko.projects.manager._ensureProjectPaneVisible = ensureVisible;
        xtk.domutils.fireEvent(window, 'project_opened');
        ko.projects.manager._ensureProjectPaneVisible = true;
    }, 100);
    return true;
}

this.saveProjectAs = function ProjectSaveAs(project) {
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
    if (url == project.url) {
        // Not a save-as, just a save...
        ko.projects.manager.saveProject(project);
        return true;
    }

    if (ko.projects.manager.getProjectByURL(url) != null) {
        ko.dialogs.alert(_bundle.formatStringFromName("projectIsAlreadyLoaded.alert",
            [url], 1));
        return false;
    }

    var oldURL = project.url;
    project.url = url;
    project.name = ko.uriparse.baseName(url);
    project.reassignUUIDs();
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
    if (!project) {
        ko.dialogs.alert("No project to rename");
        return;
    } else if (project.isDirty) {
        ko.dialogs.alert("Project " + project.name + " needs to be saved before renaming");
        return;
    }
    var oldKoFile = project.getFile();
    if (!oldKoFile.isLocal) {
        ko.dialogs.alert("Sorry, only local projects can be renamed");
        return;
    }
    var oldUrl = oldKoFile.URI;
    var newname = ko.dialogs.renameFileWrapper(project.name);
    if (!newname || newname == project.name) {
        return;
    }
    // bug94803: If the name matches the project file's basename, just rename
    // the project name and return
    var isSameBasename;
    if (Components.classes["@activestate.com/koInfoService;1"].
            getService(Components.interfaces.koIInfoService).platform.indexOf("linux") === 0) {
        isSameBasename = newname == project.getFile().baseName;
    } else {
        isSameBasename = newname.toLowerCase() == project.getFile().baseName.toLowerCase();
    }
    if (isSameBasename) {
        project.name = newname;
        return;
    }
    if (!this.manager.closeProject(project)) {
        return;
    }
    if (this.currentProject && this.currentProject.getFile().URI == oldUrl) {
        this.currentProject = null;
    }
        
    // closeProject added this field to the mru list, need to remove it
    // since the project with the old name soon will no longer exist.
    ko.mru.deleteValue('mruProjectList', oldUrl, true/* notify */);
        
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
        if (ko.places
            && (oldUrl.indexOf(ko.places.manager.currentPlace + "/") == 0)) {
            // Need to get places to refresh its view to show the new project file.
            ko.places.viewMgr.view.refreshView(-1);
            //XXX: The new name isn't showing up in places.
            // Not a critical bug, because .komodoproject files will
            // probably be hidden anyway.
        }
        xtk.domutils.fireEvent(window, 'current_project_changed');
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
    if (this.manager.single_project_view) {
        setTimeout(function(this_) {
                try {
                    // If the old file is still in the view, remove it
                    var part = ko.places.projects_SPV.projectsTreeView.getRowItem(1);
                    var koFile;
                    if (part) {
                        koFile = part.getFile();
                        if (koFile && koFile.URI == oldUrl) {
                            ko.places.projects_SPV.projectsTreeView.removeItems([part], 1);
                        }
                    }
                } catch(ex) {
                    this.log.exception(ex, "Error in renameProject post handler");
                }
            }, 1000, this);
    }
    return;
}

this.onload = function() {
    ko.projects.extensionManager.init();
    ko.projects.manager = new projectManager();
    ko.projects.active = this;
    ko.main.addWillCloseHandler(ko.projects.manager.closeAllProjects,
                                ko.projects.manager);
}

this.prepareForShutdown = function() {
    window.removeEventListener("view_document_detaching",
                          ko.projects.manager.handle_view_document_detaching,
                               false);
};

this.handle_parts_reload = function() {
    this.manager.applyPartKeybindings();
};

this.safeGetFocusedPlacesView = function() {
    if (ko.places) {
        try {
            return ko.places.getFocusedPlacesView();
        } catch(ex) {
            this.log.warn("Can't call ko.places.getFocusedPlacesView:\n" + ex + "\n");
        }
    }
    return false;
};

XPCOMUtils.defineLazyGetter(this, "log",
                            function() ko.logging.getLogger('ko.projects'));

}).apply(ko.projects);
