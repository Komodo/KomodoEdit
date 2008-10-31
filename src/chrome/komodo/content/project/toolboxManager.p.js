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

/* Toolbox Manager
 *
 * The Toolbox manager reads items from a "per-user" project file called
 * "toolbox.kpf" in the user's userDataDir. There is also a possible
 * "Shared Toolbox" (and associated manager) in Komodo IDE builds.
 *
 * The Toolboxes are heavily modeled on the Project Manager.
 */
// Dev Notes:
// - This module would better be named toolbox.js and that prefix should
//   then be used more regularly in here.

//---- globals
xtk.include('controller');

if (typeof(ko)=='undefined') {
    var ko = {};
}
if (typeof(ko.toolboxes)=='undefined') {
    ko.toolboxes = {};
}

(function() {
//---- Public generic Toolbox methods
var _toolboxCtrl = null;
var _prefs = Components.classes["@activestate.com/koPrefService;1"].
                getService(Components.interfaces.koIPrefService).prefs;
var _obSvc = Components.classes["@mozilla.org/observer-service;1"].
        getService(Components.interfaces.nsIObserverService);
var _fileStatusSvc = Components.classes["@activestate.com/koFileStatusService;1"].
                    getService(Components.interfaces.koIFileStatusService);
var _uuidGenerator = Components.classes["@mozilla.org/uuid-generator;1"].
                    getService(Components.interfaces.nsIUUIDGenerator);

this.user = null;
this.shared  = null;

this.onload = function Toolbox_onLoad()
{
    ko.toolboxes.user = new toolboxManager();
    ko.toolboxes.user.init();

    _toolboxCtrl = new toolboxController();
    window.controllers.appendController(_toolboxCtrl);
}

//---- A common virtual base class for both toolbox managers (user and shared)
// Dev Notes:
// - Originally there was only the one "user" or "personal" toolbox (called
//   just the "Toolbox"). When the "Shared Toolbox" was added this base
//   class was factored out. There may be remnants of "Toolbox"-specific
//   stuff in here.
//

function toolboxBaseManager() {
    // Reload other instances of the toolbox if it changes.
    this._reloadOnToolboxChanges = false;
}

// The following two lines ensure proper inheritance (see Flanagan, p. 144).
toolboxBaseManager.prototype = new ko.projects.BaseManager();
toolboxBaseManager.prototype.constructor = toolboxBaseManager;

// Common init code for all toolboxes. This loads the toolbox data, creating
// and empty .kpf file if necessary. If the toolbox data is corrupt it is
// moved out of the way and a new empty one is created.
//
//  "prettyName" is a human readable name, useful for error messages and
//      debugging.
//  "elementId" is the id of the <partviewer/> XUL element for this toolbox.
//  "fname" is the full local path to the toolbox KPF file.
//
// This method returns null if successful. Otherwise it returns one of the
// following error strings:
//  "could not create": The toolbox file did not exist and an attempt to
//      create an empty starter one failed. The actual error is available
//      via koILastErrorService.
//  "could not load": The toolbox file could not be loaded for whatever
//      reason (perhaps it is corrupt?).
//
toolboxBaseManager.prototype._init = function(prettyName, elementid, fname) {
    try {
        ko.main.addCanCloseHandler(this.canUnload, this);
        ko.main.addWillCloseHandler(this.unload, this);
        this.TOOLBOX_CHANGED_EVENT = this.name + " _toolbox_changed";
        if (this._reloadOnToolboxChanges) {
            // Add a toolbox change observer.
            _obSvc.addObserver(this, this.TOOLBOX_CHANGED_EVENT, false);
        }
        this.lastErrorSvc = Components.classes["@activestate.com/koLastErrorService;1"].
                getService(Components.interfaces.koILastErrorService);
        var osPath = Components.classes["@activestate.com/koOsPath;1"].
                     getService(Components.interfaces.koIOsPath);

        // Marker to tell if the project in the process of shutting down.
        this._isShuttingDown = false;
        // Unique identifier for this toolbox instance.
        this._uuid = _uuidGenerator.generateUUID();
        this.prettyName = prettyName;
        this.log = ko.logging.getLogger('toolboxManager: ' + elementid);
        //this.log.setLevel(ko.logging.LOG_DEBUG);
        this.log.info('initializing toolboxBaseManager');
        this.viewMgr = document.getElementById(elementid);
        this.viewMgr.onLoad(this);
        // XXX our one and only datapoint for the toolbox
        //this.viewMgr.view.datapoints['Name']='Name';

        this.toolbox = Components.classes["@activestate.com/koProject;1"]
                       .createInstance(Components.interfaces.koIProject);
        this.toolboxURL = ko.uriparse.localPathToURI(fname);

        // Create an empty toolbox file if there currently isn't one.
        if (!osPath.exists(fname)) {
            this.log.info("The "+prettyName+" at '"+fname+"' does not "+
                          "exist. Creating a new empty one.");
            try {
                this.toolbox.create();
                this.toolbox.prefset.setBooleanPref("import_live", false);
                this.toolbox.url = this.toolboxURL;
                this.toolbox.save();
            } catch(ex) {
                this.toolbox = null;
                return "could not create";
            }
        }

        // Make sure that there is always a ko.projects.active
        ko.projects.active = this.viewMgr;
        ko.projects.managers.push(this);

        // Load the toolbox file.
        try {
            this.log.info("Loading "+prettyName+" from '"+this.toolboxURL+"'");
            this.toolbox.load(this.toolboxURL);
            this.toolbox.prefset.setBooleanPref("import_live", false);
        } catch(ex) {
            log.exception(ex);
            return "could not load";
        }

        this.loadFromProject(this.toolbox);

        // Find out if we're read-only or not.
        if (this.viewMgr.hasAttribute('lock_icon_id')) {
            var lockId = this.viewMgr.getAttribute('lock_icon_id');
            var lockIcon = document.getElementById(lockId);
            if (this.writeable()) {
                lockIcon.removeAttribute('readonly');
            } else {
                lockIcon.setAttribute('readonly',"chrome://komodo/skin/images/small_lock.png");
            }
        }

        // Let the file status service know it has work to do.
        // XXX - This should only be done for the first instance, not on every
        //       window instance loading the toolbox.
        _fileStatusSvc.updateStatusForAllFiles(Components.interfaces.koIFileStatusChecker.REASON_BACKGROUND_CHECK);

        return null;
    } catch (e) {
        log.exception(e);
    }
    return "An unknown exception occurred";
}

toolboxBaseManager.prototype.close = function(doSave /* true */) {
    try {
        if (typeof(doSave) == 'undefined') {
            doSave = true;
        }
        if (this.toolbox) {
            if (doSave && !this.toolbox.getFile().isReadOnly) {
                this.save();
            }
            this.toolbox.close();
            this.viewMgr.view.toolbox = null;
        }
    } catch (e) {
        log.exception(e);
    }
}

toolboxBaseManager.prototype.writeable = function () {
    // Return true if the current toolbox is writeable
    // Note: We don't trust
    //           this.wrappedproject.properties["isReadOnly"]
    //       because it is using a bogus algorithm (see URIlib.py). Instead we
    //       do our own checking using os.access().
    /// XXX nice to know, too bad there is no further explanation in URIlib.py - smc
    var os = Components.classes["@activestate.com/koOs;1"].
             getService(Components.interfaces.koIOs);
    var fname = ko.uriparse.URIToLocalPath(this.toolboxURL);
    return os.access(fname, os.W_OK);
}

toolboxBaseManager.prototype.removeItem = function(item, skipdialog)
{
    if (ko.projects.BaseManager.prototype.removeItem.apply(this, [item,skipdialog])) {
        // XXX fixme, project needs to make view refresh
        this.viewMgr.view.refresh(item.parent);
        this.save();
    }
}

toolboxBaseManager.prototype.removeItems = function(items, trash) {
    ko.projects.BaseManager.prototype.removeItems.apply(this, [items, trash]);
    this.save();
}

toolboxBaseManager.prototype.addItem = function(/* koIPart */ part, /* koIPart */ parent) {
    if (typeof(parent)=='undefined' || !parent) {
        parent = this.viewMgr.view.toolbox;
    } else {
        // throw an exception if we received an index instead of a koIPart
        try {
            parent.QueryInterface(Components.interfaces.koIPart);
        } catch(e) {
            throw new Error("AddItem API changed, see toolboxManager.js:toolboxBaseManager.prototype.addItem");
        }
    }
    var isproject = false;
    try {
        /* we don't allow projects to be added to the
           toolbox, but we do allow links to projects, which
           allows us to open projects from the toolbox */
        isproject = part.QueryInterface(Components.interfaces.koIProject) != null;
    } catch(e) {}

    if (isproject) {
        var p_part = this.toolbox.createPartFromType('ProjectRef');
        p_part.setStringAttribute('url', part.url);
        p_part.setStringAttribute('name', os.path.withoutExtension(part.getStringAttribute('name')));
        part = p_part;
    }

    try {
        // XXX FIXME, I'm still not happy with this
        // if the parent is not a container, find a container
        try {
            parent.QueryInterface(Components.interfaces.koIContainerBase);
        } catch(e) {
            parent = parent.parent;
        }
        parent.addChild(part);
        this.viewMgr.view.refresh(part.parent);
        this.viewMgr.view.selection.select(this.viewMgr.view.getIndexByPart(part));

        // this will prevent projects from being removed from project pane
        // if the project is dragged into the toolbox
        this.save();
        return !isproject;
    } catch(e) { this.log.error('toolboxBaseManager addItem exception: '+e+'\n'); }
    return false;
}

toolboxBaseManager.prototype.hasProject = function(project) {
    return project == this.toolbox;
}

toolboxBaseManager.prototype.getItemsByURL = function(url) {
    var items = [];
    var item = this.findItemByURL(this.toolbox, null, url);
    if (item != null) items.push(item);
    return items;
}

toolboxBaseManager.prototype.findItemByURL = function (parent, type, url) {
    var child = parent.getChildWithTypeAndStringAttribute(type, "url", url, true);
    if (child) return child;
    if (parent.url == url || (parent.hasAttribute('url')
            && parent.getStringAttribute('url') == url)) {
        return parent;
    }
    return null;
}

toolboxBaseManager.prototype.isLivePath = function(url) {
    return this.toolbox.containsLiveURL(url);
}

toolboxBaseManager.prototype.getSelectedProject = function() {
    return this.toolbox;
}

toolboxBaseManager.prototype.findItemByAttributeValue= function (attribute, value) {
    return this.findChildByAttributeValue(this.toolbox, attribute, value);
}

toolboxBaseManager.prototype.findPartByTypeAttributeValue= function (type, attribute, value) {
    return this.toolbox.getChildWithTypeAndStringAttribute(type, attribute, value,true);
}

toolboxBaseManager.prototype.findPartByAttributeValue= function (attribute, value) {
    return this.toolbox.getChildByAttributeValue(attribute, value, true);
}

toolboxBaseManager.prototype.applyPartKeybindings = function () {
    this.toolbox.applyKeybindings(true);
}

toolboxBaseManager.prototype.getPartsByURL = function (url) {
    var part = this.toolbox.getChildByAttributeValue('url', url, true);
    if (part != null) return [part];
    return [];
}

toolboxBaseManager.prototype.loadFromProject = function(project) {
    ko.trace.get().enter('loadFromProject');
    this.viewMgr.view.toolbox = project;
    this.viewMgr.view.refresh(null);
    if (this.viewMgr.view.rowCount && this.viewMgr.view.selection) {
        this.viewMgr.view.selection.select(0);
    }
    ko.trace.get().leave('loadFromProject');
}

toolboxBaseManager.prototype.loadToolboxFromURL = function(url)
{
    this.toolbox = Components.classes["@activestate.com/koProject;1"]
                                .createInstance(Components.interfaces.koIProject);
    this.toolbox.load(url);
    this.toolbox.prefset.setBooleanPref("import_live", false);
    this.loadFromProject(this.toolbox);
}

/**
 * Close the toolbox (without saving) and then load the toolbox data
 * from the koIProject again.
 */
toolboxBaseManager.prototype.reloadToolbox = function()
{
    this.log.info("reloadToolbox:: reloading: " + this.toolboxURL);
    this.close(/* doSave */ false);
    this.loadToolboxFromURL(this.toolboxURL);
}

toolboxBaseManager.prototype.verifyUnchanged = function() {
    if (this.toolbox && this.toolbox.haveContentsChangedOnDisk()) {
        var prompt = 'Your '+this.prettyName+' has changed outside Komodo, '+
                  'Saving it now will overwrite changes made outside Komodo. '+
                  'You can overwrite those changes, or load the changes which '+
                  'will overwrite the changes you have made in your toolbox.';
        var response = ko.dialogs.customButtons(prompt, ["Overwrite","Reload","Cancel"],"Cancel", null, this.prettyName+" has changed on disk");
        if (response == "Cancel") {
            return false;
        } else if (response == "Reload") {
            this.reloadToolbox();
            try {
                _obSvc.notifyObservers(this.toolbox, this.TOOLBOX_CHANGED_EVENT,
                                       this._uuid);
            } catch(e) { /* exception if no listeners */ }
            return false;
        }
    }
    return true;
}

// This is occassionally used as a Komodo "can close" handler, so it
// returns true if successful, false otherwise.
toolboxBaseManager.prototype.save = function() {
    if (this.toolbox && this.toolbox.isDirty) {
        try {
            if (!this.verifyUnchanged()) {
                return false;
            }
            this.toolbox.save();
            return true;
        } catch(ex) {
            var lastErrorSvc = Components.classes["@activestate.com/koLastErrorService;1"].
                getService(Components.interfaces.koILastErrorService);
            var answer = ko.dialogs.yesNoCancel(
                "There was an error saving the "+this.prettyName+". Would " +
                    "you like to save it to another location?", // prompt
                "Yes", // default answer
                lastErrorSvc.getLastErrorMessage(), // text
                "Toolbox Error"); // title
            if (answer == "Yes") {
                while (1) {
                    var filename = ko.filepicker.saveFile(
                            null, // default dir
                            ko.uriparse.baseName(this.toolboxURL), // default filename
                            "Backup "+this.prettyName, // title
                            "Komodo Project", // default filter
                            ["Komodo Project", "All"]); // filters
                    if (!filename) return false;

                    this.toolbox.url = ko.uriparse.localPathToURI(filename);
                    try {
                        this.toolbox.save();
                    } catch(ex) {
                        answer = ko.dialogs.yesNoCancel(
                            "There was an error saving the "+this.prettyName+
                                "to '"+filename+"'. Would you like to save "+
                                "it to different location?", // prompt
                            "Yes", // default answer
                            lastErrorSvc.getLastErrorMessage(), // text
                            "Toolbox Error"); // title
                        if (answer == "Yes") {
                            continue;
                        } else if (answer == "No") {
                            // do nothing
                        } else /* answer == "Cancel" */ {
                            return false;
                        }
                    }
                    break;
                }
            } else if (answer == "No") {
                // do nothing
            } else /* answer == "Cancel" */ {
                return false;
            }
        } finally {
            if (!this._isShuttingDown && !this.toolbox.isDirty) {
                // The user saved the toolbox.
                try {
                    _obSvc.notifyObservers(this.toolbox, this.TOOLBOX_CHANGED_EVENT,
                                           this._uuid);
                } catch(e) { /* exception if no listeners */ }
            }
        }
    }
    return true;
}

toolboxBaseManager.prototype.observe = function(subject, topic, data)
{
    if (topic == this.TOOLBOX_CHANGED_EVENT) {
        // subject: a koIProject instance from the toolbox that was changed.
        // data:    the uuid of the toolboxManager instance that was changed.
        if (this._uuid != data) {
            this.log.info("reloading " + this.name + " because another toolbox instance has changed");
            this.reloadToolbox();
        }
    }
};

toolboxBaseManager.prototype.canUnload = function() {
    return this.save();
}

toolboxBaseManager.prototype.unload = function() {
    this._isShuttingDown = true;
    if (this.toolbox) {
        try {
            // Save folding-related information, which change doesn't
            // dirty a project.
            this.viewMgr.view.savePrefs(this.viewMgr.view.toolbox);
        } catch(ex) {
            this.log.exception(ex);
        }
    }
    if (this._reloadOnToolboxChanges) {
        // Remove the toolbox change observer originally added.
        _obSvc.removeObserver(this, this.TOOLBOX_CHANGED_EVENT);
    }
}

toolboxBaseManager.prototype.__defineGetter__("currentProject",
function()
{
    return this.toolbox;
});

toolboxBaseManager.prototype.getCurrentProject = function() {
    return this.toolbox;
}




/******************************************************/
/*                   User Toolbox                     */
/******************************************************/


//---- Support for the user/personal Toolbox

function toolboxManager() {
    this._reloadOnToolboxChanges = true;
}

// The following two lines ensure proper inheritance (see Flanagan, p. 144).
toolboxManager.prototype = new toolboxBaseManager();
toolboxManager.prototype.constructor = toolboxManager;

toolboxManager.prototype.init = function() {
    try {
        // Find out what our fname should be
        var koDirs = Components.classes["@activestate.com/koDirs;1"].
                getService(Components.interfaces.koIDirs);
        var os = Components.classes["@activestate.com/koOs;1"].
                getService(Components.interfaces.koIOs);
        var userDataDir = koDirs.userDataDir;
        var fname = os.path.join(userDataDir, 'toolbox.kpf');

        // Do the init
        this.name = "PersonalToolbox";
        var err = toolboxBaseManager.prototype._init.apply(this,
                    ["Toolbox", 'toolboxview', fname]);
        if (err == "could not create") {
            var lastErrorSvc = Components.classes["@activestate.com/koLastErrorService;1"].
                               getService(Components.interfaces.koILastErrorService);
            ko.dialogs.internalError("Could not create a blank toolbox file.",
                                 lastErrorSvc.getLastErrorMessage());
        } else if (err == "could not load") {
            // create a backup and start with a blank one
            var badfname = fname+".error.txt";
            this.log.error("Unable to load '"+fname+"', "+
                           "a backup will be made at '"+badfname+"'.");
            alert("There was an error loading the Toolbox from '"+fname+"'. "+
                  "A backup will be made at '"+badfname+"' and a new "+
                  "toolbox will be created.");
            try {
                var shutil = Components.classes["@activestate.com/koShUtil;1"]
                                       .getService(Components.interfaces.koIShUtil);
                shutil.copyfile(fname, badfname);
            } catch (ex) {
                // Ignore it -- we can just go along w/ an empty toolbox (see below).
                alert("Could not backup toolbox data file: " +
                      this.lastErrorSvc.getLastErrorMessage());
            }
        }

        // Install sample toolbox for a particular version if necessary
        var sampletoolbox = os.path.join(koDirs.supportDir, 'samples');
        sampletoolbox = os.path.join(sampletoolbox, 'toolbox.kpf');
        var infoSvc = Components.classes["@activestate.com/koInfoService;1"].
            getService(Components.interfaces.koIInfoService);
        var prefName = "haveInstalledSampleToolbox-Komodo" + infoSvc.version;
        if (! _prefs.hasBooleanPref(prefName) || ! _prefs.getBooleanPref(prefName)) {
            this.log.info("Installing sample toolbox for version " + infoSvc.version);
            this.installSamples(sampletoolbox, infoSvc.version);
            _prefs.setBooleanPref(prefName, "true");
        }
        this.loadFromProject(this.toolbox);
        // let the status service know it has work to do
        
        var _partSvc = Components.classes["@activestate.com/koPartService;1"]
                .getService(Components.interfaces.koIPartService);
        _partSvc.toolbox = this.toolbox;

        // Let the file status service know it has work to do.
        _fileStatusSvc.updateStatusForAllFiles(Components.interfaces.koIFileStatusChecker.REASON_BACKGROUND_CHECK);

    } catch (e) {
        log.exception(e);
    }
}

toolboxManager.prototype.installSamples = function(sampleToolboxPath, version) {
    ko.trace.get().enter('toolboxManager.installSamples');
    var sample_project = Components.classes["@activestate.com/koProject;1"]
                                .createInstance(Components.interfaces.koIProject);
    sample_project.prefset.setBooleanPref("import_live", false);
    var folder = sample_project.createPartFromType('folder');

    sample_project.load(ko.uriparse.localPathToURI(sampleToolboxPath));
    folder.name = "Samples (" + version + ")";
    this.log.info("installing samples: " + folder.name );
    var i;
    var children = new Array();
    sample_project.getChildren(children, new Object());
    children = children.value;
    for (i = 0; i < children.length; i++) {
        this.log.info("adding child " + children[i]);
        folder.addChild(children[i].clone());
    }
    this.toolbox.addChild(folder);
    ko.trace.get().leave('toolboxManager.installSamples');
}

function toolboxController() {
}

// The following two lines ensure proper inheritance (see Flanagan, p. 144).
toolboxController.prototype = new xtk.Controller();
toolboxController.prototype.constructor = toolboxController;

toolboxController.prototype.destructor = function() {
}

toolboxController.prototype.is_cmd_toolboxExportPackage_enabled = function () {
    try {
        return (ko.projects.active && ko.projects.active.getSelectedItems().length > 0);
    } catch (e) {
        log.exception(e);
    }
    return false;
}

toolboxController.prototype.do_cmd_toolboxExportPackage = function () {
    if (ko.projects.active) {
        ko.projects.exportPackageItems(ko.projects.active.getSelectedItems());
    }
}

this.importPackage = function Toolbox_ImportPackage(filename) {
    ko.projects.importFromPackage(ko.toolboxes.user.toolbox, filename);
    ko.toolboxes.user.viewMgr.view.refresh(ko.toolboxes.user.toolbox);
}


this.addCommand = function AddCommandToToolbox(command, cwd, env, insertOutput,
                             operateOnSelection, doNotOpenOutputWindow, runIn,
                             parseOutput, parseRegex, showParsedOutputList,
                             name /* default=command */ )
{
    var toolboxMgr = ko.toolboxes.user;
    var part = toolboxMgr.toolbox.createPartFromType('command');
    part.type = 'command';
    part.value = command;
    if (typeof(name) == 'undefined' || ! name) {
        name = command;
    }
    part.setStringAttribute('name', name);
    part.setStringAttribute('cwd', cwd);
    part.setStringAttribute('env', ko.stringutils.escapeWhitespace(env));
    part.setBooleanAttribute('insertOutput', insertOutput);
    part.setBooleanAttribute('operateOnSelection', operateOnSelection);
    part.setBooleanAttribute('doNotOpenOutputWindow', doNotOpenOutputWindow);
    part.setStringAttribute('runIn', runIn);
    part.setBooleanAttribute('parseOutput', parseOutput);
    part.setStringAttribute('parseRegex', parseRegex);
    part.setBooleanAttribute('showParsedOutputList', showParsedOutputList);
    toolboxMgr.addItem(part);
    ko.uilayout.ensureTabShown('toolbox_tab');
}

}).apply(ko.toolboxes);

(function() { // ko.projects
this.exportItems = function Toolbox_ExportItems(items) {
    var defaultfilename = "exported.kpf";
    var filename = ko.filepicker.saveFile(
            null, defaultfilename, // default dir and filename
            "Export Selected Items To...", // title
            "Komodo Project", // default filter
            ["Komodo Project", "All"]); // filters
            // When have .ktf files changes to this:
            //"Komodo Toolbox", // default filter
            //["Komodo Toolbox", "Komodo Project", "All"]);
    if (filename == null)
        return;

    var project = Components.classes["@activestate.com/koProject;1"]
                  .createInstance(Components.interfaces.koIProject);
    try {
        var url = ko.uriparse.localPathToURI(filename);
        project.create();
        project.prefset.setBooleanPref("import_live", false);
        project.url = url;
        var i;
        for (i = 0; i < items.length; i++) {
            project.addChild(items[i]);
        }
        project.save();
    } catch(ex) {
        var lastErrorSvc = Components.classes["@activestate.com/koLastErrorService;1"].
            getService(Components.interfaces.koILastErrorService);
        alert('There was an error exporting project "' +
              project.name + '": ' +
              lastErrorSvc.getLastErrorMessage());
    }
}

this.exportPackageItems = function Toolbox_ExportPackageItems(items) {
    if (typeof(items) == 'undefined' || !items || items.length < 1) {
        ko.dialogs.alert("Please select items in the toolbox to export first.");
        return;
    }
    var localPath = ko.filepicker.saveFile(
            null, items[0].name + ".kpz", // default dir and filename
            "Export Selected Items to a Package", // title
            "Komodo Package", // default filter name
            ["All"]); // filter names to show
    if (localPath == null) {
        return;
    }
    var packager = Components.classes["@activestate.com/koProjectPackageService;1"]
                      .getService(Components.interfaces.koIProjectPackageService);
    packager.packageParts(localPath, items.length, items, true);
}


}).apply(ko.projects);

// Backwards Compatibility API
var Toolbox_ExportItems = ko.projects.exportItems;
var Toolbox_ExportPackageItems = ko.projects.exportPackageItems;
var Toolbox_ImportPackage = ko.toolboxes.importPackage;
__defineGetter__("toolboxMgr",
function()
{
    ko.projects.manager.log.error("DEPRECATED: toolboxMgr, use ko.toolboxes.user\n");
    return ko.toolboxes.user;
});
