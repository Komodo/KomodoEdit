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
const XUL_NS = "http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul";
this.manager = null;

var _activeView = null;

/**
 * The active view is the last project view to have received focus.  It does
 * not mean that the view currently has focus.
 */
this.__defineGetter__("active",
function()
{
    return _activeView;
});

this.__defineSetter__("active",
function(view)
{
    _activeView = view;
});

/**
 * does the active view have real focus, if so, return it, otherwise null.
 */
this.getFocusedProjectView = function projects_getFocusedProjectView() {
    if (_activeView && xtk.domutils.elementInFocus(_activeView.manager.viewMgr))
        return _activeView;
    return null;
}

//----- The projectManager class manages the set of open projects and
// which project is 'current'.

function projectManager() {
    ko.trace.get().enter('projectManager()');
    this.name = 'projectManager';
    ko.projects.BaseManager.apply(this, ["projectsChanged"]);
    this.log = ko.logging.getLogger('projectManager');
    this._projects = [];
    this.viewMgr = document.getElementById('projectview');
    if (!this.viewMgr) {
        this.log.error("couldnt' find id 'projectview'");
        return;
    }
    this.viewMgr.onLoad(this);
    ko.projects.managers.push(this);
    // Make sure that there is always a active view
    ko.projects.active = this.viewMgr;
    // register our command handlers
    this.registerCommands();
    // add our default datapoint
    this.viewMgr.addColumns(ko.projects.extensionManager.datapoints);
    ko.projects.extensionManager.datapoints['Name']='Name';
    this.observer = new ProjectEventObserver();
    this._currentProject = null;
    ko.trace.get().leave('projectManager()');
}

// The following two lines ensure proper inheritance (see Flanagan, p. 144).
projectManager.prototype = new ko.projects.BaseManager();
projectManager.prototype.constructor = projectManager;

projectManager.prototype.getProjectsMenu = function(popup)
{
    // used by top level project->set active menu
    var children = popup.childNodes;
    var i,mi;
    for (i = children.length - 1; i >= 0; i--) {
        popup.removeChild(children[i]);
    }
    if (this._projects.length > 0) {
        for (var project in this._projects) {
            mi = document.createElementNS(XUL_NS, 'menuitem');
            mi.setAttribute('label',this._projects[project].name);
            mi.setAttribute('oncommand','ko.projects.manager.setCurrentProject(this.value);');
            mi.setAttribute('type','checkbox');
            mi.value = this._projects[project];
            if (this.currentProject == this._projects[project]) {
                mi.setAttribute('checked','true');
            }
            popup.appendChild(mi);
        }
    } else {
        // add an 'empty' menu item
        mi = document.createElementNS(XUL_NS, 'menuitem');
        mi.setAttribute('label','No Open Projects');
        mi.setAttribute('disabled','true');
        popup.appendChild(mi);
    }
    return true;
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
        if (docs[i].document && docs[i].document.file) {
            url = docs[i].document.file.URI;
            if (project.getChildByURL(url)) {
                opened.push(url);
            }
        }
    }
    return opened;
}

projectManager.prototype.forcedCloseURL = function(url) {
    var v = ko.views.manager.getViewForURI(url);
    if (v) {
        // we don't want dialogs to popup here!!!
        v.closeUnconditionally();
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
    if (gCodeIntelActive)
        gCodeIntelSvc.ideEvent("closing_project", null, project);
    // Remove the project node/part from the Projects tree.
    this.viewMgr.view.removeProject(project);
    // the active project has been reset

    // remove the project from our list
    try {
        var id = this._projects.indexOf(project);
        this._projects.splice(id, 1);
    } catch(e) {
        // XXX FIXME SMC currently broken with live projects
    }
    project.close();

    ko.mru.addURL("mruProjectList", project.url);
    if (this._projects.length == 0) {
        window.updateCommands('some_projects_open');
    }
    this.viewMgr.view.invalidate();
    return true;
}

projectManager.prototype.closeProject = function(project) {
    if (project.isDirty) {
        var question = "Save changes to project '"+project.name+"'?";
        var answer = ko.dialogs.yesNoCancel(question);
        if (answer == "Cancel") {
            return false;
        } else if (answer == "Yes") {
            try {
                this.saveProject(project);
            } catch(ex) {
                var lastErrorSvc = Components.classes["@activestate.com/koLastErrorService;1"].
                    getService(Components.interfaces.koILastErrorService);
                ko.dialogs.alert('There was an error saving project, "' +
                      project.name + '": ' +
                      lastErrorSvc.getLastErrorMessage());
                return false;
            }
        }
    }
    this._saveProjectViewState(project);
    var urls = this._getOpenURLsInProject(project);
    if (urls.length != 0) {
        var action = ko.dialogs.yesNoCancel(
                "Would you like Komodo to close the opened files from "+
                    "this project?",
                "No", null, null, // default response, text, title
                "close_all_files_on_project_close");
        if (action == "Cancel") {
            return false;
        } else if (action == "Yes") {
            // Should find out which ones are dirty and offer to save those --
            // then _closeURL can be brutal with those that the user didn't
            // want to save.
            var modified = ko.views.manager.offerToSave(urls, "Save Modified Files", "Save selected files before closing them?");
            if (modified == false) return false;

            var i;
            for (i=0; i < urls.length; i++) {
                this.forcedCloseURL(urls[i]);
            }
        }
    }
    return this.closeProjectEvenIfDirty(project);
}

projectManager.prototype.getDirtyProjects= function() {
    var dirty = new Array();
    for (var i = 0; i < this._projects.length; i++) {
        if (this._projects[i].isDirty) {
            dirty.push(this._projects[i]);
        }
    }
    return dirty;
}

projectManager.prototype.closeAllProjects = function() {
    for (var i = 0; i < this._projects.length; i++) {
        if (!this.closeProject(this._projects[i])) return false;
    }
    return true;
}

projectManager.prototype.closeAllProjectsEvenIfDirty = function() {
    for (var i = 0; i < this._projects.length; i++) {
        if (!this.closeProjectEvenIfDirty(this._projects[i])) return false;
    }
    return true;
}

projectManager.prototype.saveProject = function(project) {
    // Returns true on success, false on failure.
    var file = project.getFile();

    if (file.isReadOnly) {
        alert("The project '" + project.name +
              "' is a read only file and cannot be saved.");
        return false;
    } else {
        try {
            project.save();
        } catch(ex) {
            var lastErrorSvc = Components.classes["@activestate.com/koLastErrorService;1"].
                getService(Components.interfaces.koILastErrorService);
            ko.dialogs.alert('There was an error saving project "' +
                  project.name + '": ' +
                  lastErrorSvc.getLastErrorMessage());
            return false;
        }
        // invalidate so the dirty status shows correctly
        // XXX fixme, can we optimize this?  is it necessary?
        this.viewMgr.tree.treeBoxObject.invalidate();
        var obSvc = Components.classes["@mozilla.org/observer-service;1"].
                getService(Components.interfaces.nsIObserverService);
        try {
            obSvc.notifyObservers(this, 'file_changed', project.url);
        } catch(e) { /* exception if no listeners */ }
        window.updateCommands('project_dirty');
    }
    return true;
}

projectManager.prototype.newProject = function(url) {
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
        ko.dialogs.alert('There was an error saving project "' +
              project.name + '": ' +
              lastErrorSvc.getLastErrorMessage());
        return false;
    }
    this._addProject(project);
    var obSvc = Components.classes["@mozilla.org/observer-service;1"].
            getService(Components.interfaces.nsIObserverService);
    try {
        obSvc.notifyObservers(this, 'file_project', project.url);
    } catch(e) { /* exception if no listeners */ }
    if (gCodeIntelActive) {
        // We delay launching the code browser for a little while to provide a
        // smoother project-opening experience. It's not a big deal that the
        // code browser gets populated a tad late.
        window.setTimeout(
            function(codeIntelSvc, msg, url, project) {
                codeIntelSvc.ideEvent(msg, url, project);
            },
            1000, gCodeIntelSvc, "opened_project", project.url, project
        );
    }
    return true;
}

projectManager.prototype.newProjectFromTemplate = function() {
    try {
        this.log.info("doing newTemplate: ");
        var lastErrorSvc = Components.classes['@activestate.com/koLastErrorService;1'].getService();
        var template;
        // Get template selection from the user.
        var obj = new Object();
        obj.type = "project";
        obj.filename = "MyProject.kpf";
        window.openDialog("chrome://komodo/content/templates/new.xul",
                          "_blank",
                          "chrome,modal,titlebar",
                          obj);
        if (obj.template == null || obj.filename == null) return false;

        var uri = ko.uriparse.localPathToURI(obj.filename);
        var extractLocation = ko.uriparse.dirName(uri);

        var packager = Components.classes["@activestate.com/koProjectPackageService;1"]
                          .getService(Components.interfaces.koIProjectPackageService);
        var project = packager.newProjectFromPackage(obj.template, extractLocation);
        project.url = uri;

        var ok = this._saveNewProject(project);
        if (ok) {
            // run the creation macro
            var macro = project.getChildWithTypeAndStringAttribute('macro', 'name', 'oncreate', 1);
            if (macro)
                ko.projects.executeMacro(macro);
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
            var res = ko.dialogs.yesNo("Save the project and continue?", //prompt
                                       strYes, // default response
                                       "Projects need to be saved before Komodo will export them as a package.\nDo you want Komodo to save the project and continue?" // text
                                       );
            if (res != strYes || !this.saveProject(project)) {
                return;
            }
        }
        var os = Components.classes["@activestate.com/koOs;1"].getService();
        var templateSvc = Components.classes["@activestate.com/koTemplateService?type=project;1"].getService();
        var dname = os.path.join(templateSvc.getUserTemplatesDir(), 'My Templates');

        var file = project.getFile();
        var basename = file.baseName;
        var name = basename.slice(0, basename.length-file.ext.length);

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

projectManager.prototype.loadProject = function(url) {
    var project = Components.classes["@activestate.com/koProject;1"]
                        .createInstance(Components.interfaces.koIProject);

    if (this.getProjectByURL(url)) {
        return null; // the project is already loaded
    }
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
        ko.dialogs.alert("Unable to load project \"" + projectname + "\": " +
              lastErrorSvc.getLastErrorMessage());
        return null;
    }
    return this._addProject(project);
}

projectManager.prototype._addProject = function(project) {
    this._projects[this._projects.length] = project;
    // add project to project tree
    this.viewMgr.view.addProject(project);
    this.viewMgr.view.refresh(project);
    this.setCurrentProject(project);

    // Let the file status service know it has work to do.
    var fileStatusSvc = Components.classes["@activestate.com/koFileStatusService;1"].
                        getService(Components.interfaces.koIFileStatusService);
    fileStatusSvc.updateStatusForAllFiles(Components.interfaces.koIFileStatusChecker.REASON_BACKGROUND_CHECK);

    ko.mru.addURL("mruProjectList", project.url);
    window.setCursor("auto");
    this.viewMgr.focus(); // always set focus here when loading projects
    window.updateCommands('some_projects_open');
    
    return project;
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

projectManager.prototype.__defineSetter__("currentProject",
function(project)
{
    this.viewMgr.view.currentProject = project;
    this._currentProject = project;
    if (gCodeIntelActive) {
        gCodeIntelSvc.ideEvent("current_project_changed", null,project);
    }
    /* XXX FIXME SMC old logic, broken with live projects
    if (this._projects.indexOf(project) >= 0) {
        this.viewMgr.view.currentProject = project;
        if (gCodeIntelActive) {
            gCodeIntelSvc.ideEvent("current_project_changed", null,project);
        }
    } else {
        log.error("trying to set a project as current project, but it is not in the projects list "+project.name+" "+this._projects.indexOf(project)+"\n");
        dump("projects...\n");
        for (var i = 0; i < this._projects.length; i++) {
            dump("   project "+i+" is "+ this._projects[i].name+"\n");
            dump("    "+this._projects[i].QueryInterface(Components.interfaces.nsISupports)+" == "+project.QueryInterface(Components.interfaces.nsISupports)+" ? "+(this._projects[i].QueryInterface(Components.interfaces.nsISupports)==project.QueryInterface(Components.interfaces.nsISupports)?"YES":"NO")+"\n");
            this._projects[i].dump(0);
        }
        project.dump(0);
    }
    */
    this.refreshView();
    window.updateCommands('current_project_changed');
});

projectManager.prototype.setCurrentProject = function(project) {
    this.currentProject = project;
}

projectManager.prototype.__defineGetter__("currentProject",
function()
{
    // At shutdown the projects are unloaded from the view
    // before the saveWorkspace routine runs.
    return this.viewMgr.view.currentProject || this._currentProject;
});

projectManager.prototype.getCurrentProject = function() {
    return this.currentProject;
}

projectManager.prototype.getSelectedProject = function() {
    var node = this.viewMgr.view.getSelectedItem();
    if (node) return node.project;
    return this.currentProject;
}

projectManager.prototype.registerCommands = function() {
    var em = ko.projects.extensionManager;
    em.registerCommand("cmd_newProject",this);
    em.registerCommand("cmd_newProjectFromTemplate",this);
    em.registerCommand("cmd_openProject",this);
    em.registerCommand("cmd_openProjectFromURL",this);
    em.registerCommand("cmd_setActiveProject",this);
    em.registerCommand("cmd_closeProject",this);
    em.registerCommand("cmd_saveProject",this);
    em.registerCommand("cmd_saveProjectAs",this);
    em.registerCommand("cmd_saveProjectAsTemplate",this);
    em.registerCommand("cmd_revertProject",this);
    em.registerCommand("cmd_importFromFS_Project",this);
    em.registerCommand("cmd_reimportFromFS_Project",this);
    em.registerCommand("cmd_importPackageToToolbox",this);
    em.registerCommand("cmd_findInCurrProject",this);
    em.registerCommand("cmd_replaceInCurrProject",this);

    em.createMenuItem(Components.interfaces.koIProject,
                                    'Make Active Project','cmd_setActiveProject');
    em.createMenuItem(Components.interfaces.koIProject,
                                    'Close Project','cmd_closeProject');
    em.createMenuItem(Components.interfaces.koIProject,
                                    'Save Project','cmd_saveProject');
    em.createMenuItem(Components.interfaces.koIProject,
                                    'Save Project As...','cmd_saveProjectAs');
    em.createMenuItem(Components.interfaces.koIProject,
                                    'Create Template From Project...','cmd_saveProjectAsTemplate');
    em.createMenuItem(Components.interfaces.koIProject,
                                    'Revert Project','cmd_revertProject');
    em.createMenuItem(Components.interfaces.koIToolbox,
                                    'Import Package into Toolbox...','cmd_importPackageToToolbox');
}

projectManager.prototype.supportsCommand = function(command, item) {
    // avoid startup confusion
    if (!ko.projects.active) return false;

    switch(command) {
    case "cmd_setActiveProject":
    case "cmd_newProjectFromTemplate":
    case "cmd_newProject":
    case "cmd_openProject":
    case "cmd_openProjectFromURL":
    case "cmd_closeProject":
    case "cmd_saveProjectAs":
    case "cmd_importPackageToToolbox":
    case "cmd_saveProjectAsTemplate":
    case "cmd_importFromFS_Project":
    case "cmd_reimportFromFS_Project":
    case "cmd_findInCurrProject":
    case "cmd_replaceInCurrProject":
        return true;
    case "cmd_revertProject":
    case "cmd_saveProject":
        var prj = this.getSelectedProject();
        return (prj && prj.isDirty);
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
    case "cmd_newProjectFromTemplate":
    case "cmd_newProject":
    case "cmd_openProject":
    case "cmd_importPackageToToolbox":
    case "cmd_saveProjectAsTemplate":
        return true;
    case "cmd_closeProject":
        var broadcaster = document.getElementById('broadcaster_projectCurrent');
        if (this._projects.length == 0) {
            broadcaster.setAttribute('disabled', 'true');
        } else if (broadcaster.hasAttribute('disabled')) {
            broadcaster.removeAttribute('disabled');
        }
        return this.getSelectedProject() != null;
    case "cmd_saveProject":
    case "cmd_revertProject":
        var project = this.getSelectedProject();
        return (project && project.isDirty);
    case "cmd_importFromFS_Project":
    case "cmd_reimportFromFS_Project":
        return this.currentProject != null && !this.currentProject.live;
    case "cmd_findInCurrProject":
    case "cmd_replaceInCurrProject":
    case "cmd_saveProjectAs":
        return this.getSelectedProject() != null;
    }
    } catch(e) {
        this.log.exception(e);
    }
    return false; // shutup strict js
}

projectManager.prototype.doCommand = function(command) {
    var filename, uri;
    var project;
    switch(command) {
    case "cmd_setActiveProject":
        this.currentProject = this.getSelectedProject();
        break;
    case "cmd_newProject":
        filename = ko.filepicker.saveFile(
            null, // defaultDir
            "MyProject.kpf", // defaultFilename
            "New Project", // title
            "Komodo Project", // defaultFilterName
            ["Komodo Project", "All"]); // filterNames
        if (filename == null) return;
        uri = ko.uriparse.localPathToURI(filename);
        this.newProject(uri);
        break;
    case "cmd_newProjectFromTemplate":
        this.newProjectFromTemplate();
        break;
    case "cmd_openProject":
        var defaultDirectory = null;
        var defaultFilename = null;
        var title = "Open Project";
        var defaultFilterName = 'Komodo Project';
        var filterNames = ['Komodo Project', 'All'];
        filename = ko.filepicker.openFile(defaultDirectory /* =null */,
                             defaultFilename /* =null */,
                             title /* ="Open File" */,
                             defaultFilterName /* ="All" */,
                             filterNames /* =null */)
        if (filename == null) return;
        uri = ko.uriparse.localPathToURI(filename);
        ko.projects.open(uri);
        break;
    case "cmd_closeProject":
        this.closeProject(this.getSelectedProject());
        break;
    case "cmd_saveProject":
        this.saveProject(this.getSelectedProject());
        break;
    case "cmd_revertProject":
        this.revertProject(this.getSelectedProject());
        break;
    case "cmd_saveProjectAs":
        ko.projects.saveProjectAs(this.getSelectedProject());
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
    case "cmd_reimportFromFS_Project":
        if (this.currentProject != null && !this.currentProject.live) {
            ko.projects.reimportFromFileSystem(this.currentProject);
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
        this.viewMgr.view.refresh(part.parent);
        this.viewMgr.view.selection.select(this.viewMgr.view.getIndexByPart(part));
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

projectManager.prototype.findItemByURLInProject = function (project, type, url) {
    var child = project.getChildWithTypeAndStringAttribute(type, "url", url, true);
    if (child) return child;
    if (project.url == url || (project.hasAttribute('url')
            && project.getStringAttribute('url') == url)) {
        return project;
    }
    return null;
}

projectManager.prototype.findItemByAttributeValue = function(attribute, value) {
    var item;
    for (var i in this._projects) {
        item = this.findChildByAttributeValue(this._projects[i], attribute, value);
        if (item != null) return item;
    }
    return null;
}

projectManager.prototype.findPartByTypeAttributeValue= function (type, attribute, value) {
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

projectManager.prototype.findPartByAttributeValue= function (attribute, value) {
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

projectManager.prototype.getState = function ()
{
    if (this._projects.length == 0) {
        return null; // persist nothing
    }
    // Return a pref to add to the persisted 'workspace'
    var opened_projects = Components.classes['@activestate.com/koOrderedPreference;1'].createInstance();
    opened_projects.id = 'opened_projects';
    var i, project, url;
    for (i = 0; i < this._projects.length; i++) {
        project = this._projects[i];
        url = project.url;
        this.viewMgr.view.savePrefs(project);
        opened_projects.appendStringPref(url);
    }
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
    var action = null;
    var opened_files = [];
    if (typeof(skipRecentOpenFeature) == 'undefined') {
        skipRecentOpenFeature = false;
    }
    if (!ko.workspace.restoreInProgress()) {
        // another part of the workspace restoration will show the tab if necessary
        ko.uilayout.ensureTabShown('project_tab');
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
                    "Would you like to open files that you last had open "+
                        "in this project?",
                    "Yes", null, null, // default response, text, title
                    "open_recent_files_on_project_open");
                if (action == "Cancel") {
                    return;
                }
            }
        }
    }
    var project = ko.projects.manager.loadProject(url)
    if (gCodeIntelActive) {
        // We delay launching the code browser for a little while to provide a
        // smoother project-opening experience. It's not a big deal that the
        // code browser gets populated a tad late.
        window.setTimeout(
            function(codeIntelSvc, msg, url, project) {
                codeIntelSvc.ideEvent(msg, url, project);
            },
            1000, gCodeIntelSvc, "opened_project", url, project
        );
    }
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
}

this.saveProjectAs = function ProjectSaveAs(project)
{
    var localPath = ko.filepicker.saveFile(
            null, project.url, // default dir and filename
            "Save Project As", // title
            "Komodo Project", // default filter name
            ["Komodo Project", "All"]); // filter names to show
    if (localPath == null) {
        return false;
    }
    var url = ko.uriparse.localPathToURI(localPath);

    if (ko.projects.manager.getProjectByURL(url) != null) {
        ko.dialogs.alert("Sorry, but project " + url + " is already loaded.");
        return false;
    }

    project.url = url;
    project.name = ko.uriparse.baseName(url);
    try {
        project.save();
    } catch(ex) {
        var lastErrorSvc = Components.classes["@activestate.com/koLastErrorService;1"].
            getService(Components.interfaces.koILastErrorService);
        ko.dialogs.alert('There was an error saving project "' +
              project.name + '": ' +
              lastErrorSvc.getLastErrorMessage());
        return false;
    }

    // Update the MRU projects list.
    ko.mru.addURL("mruProjectList", url);
    var obSvc = Components.classes["@mozilla.org/observer-service;1"].
            getService(Components.interfaces.nsIObserverService);
    try {
        obSvc.notifyObservers(this,'file_changed', project.url);
    } catch(e) { /* exception if no listeners */ }
    window.updateCommands('project_dirty');
    return true;
}

// support parts_reload which is notified from keybindings manager
function ProjectEventObserver() {
    window.addEventListener("parts_reload", this.handle_parts_reload, false);
    var me = this;
    this.removeListener = function() { me.finalize(); }
    window.addEventListener("unload", this.removeListener, false);
};

ProjectEventObserver.prototype = {
    finalize: function() {
        if (!this.removeListener) return;
        window.removeEventListener("unload", this.removeListener, false);
        this.removeListener = null;
        window.removeEventListener("parts_reload", this.handle_parts_reload, false);
    },
    handle_parts_reload: function(event) {
        var managers = ko.projects.managers;
        for (var i=0; i < managers.length; i++) {
            managers[i].applyPartKeybindings();
        }
    },

    QueryInterface: function (iid) {
        if (!iid.equals(nsIObserver))
        throw Components.results.NS_ERROR_NO_INTERFACE;
        return this;
    }
};

this.onload = function() {
    ko.projects.extensionManager.init();
    ko.projects.manager = new projectManager();
}

}).apply(ko.projects);

// Backwards Compatibility API
__defineGetter__("gProjectManager",
function()
{
    ko.projects.manager.log.error("DEPRECATED: gProjectManager, use ko.projects.manager\n");
    return ko.projects.manager;
});

__defineGetter__("gFocusedProjectView",
function()
{
    ko.projects.manager.log.error("DEPRECATED: gFocusedProjectView, use ko.projects.active\n");
    return ko.projects.active;
});

