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

// Compatibility functions

// Unless noted, none of the methods below are called by 3rd-party extensions,
//
(function() {

var _deprecated_getters_noted = {};
this.__defineGetter__('user',
    function() {
        if (!('user' in _deprecated_getters_noted)) {
            _deprecated_getters_noted['user'] = true;
            ko.projects.manager.log.error("DEPRECATED: "
                                          + 'ko.toolboxes.user'
                                          + ", use ko.toolbox2"
                                          + "\n");
        }
        return ko.toolbox2;
});

function toolboxBaseManager() {
}
// The following two lines ensure proper inheritance (see Flanagan, p. 144).
toolboxBaseManager.prototype = new ko.projects.BaseManager();
toolboxBaseManager.prototype.constructor = toolboxBaseManager;
toolboxBaseManager.prototype._init = function(prettyName, elementid, fname) {
  this.log = ko.logging.getLogger('toolboxManager: ' + elementid);
  this.log.setLevel(ko.logging.LOG_DEBUG);
  this.log.debug("Calling toolboxBaseManager._init");
};

//gone: close(doSave)
//gone: writeable()
//gone: removeItem()
//gone: removeItems()
//gone: shared
//gone: user
//gone: scc

//****Compatibility alias
toolboxBaseManager.prototype.addItem = function(/* koIPart */ part, /* koIPart */ parent) {
    this.log.debug("Calling toolboxBaseManager.addItem");
    if (typeof(parent)=='undefined' || !parent) {
        parent = ko.toolbox2.getStandardToolbox();
    }
    ko.toolbox2.addItem(part, parent);
}

//gone: hasProject(project)
//gone: getItemsByURL(url)
//gone: findItemByURL(parent, type, url)
//gone: isLivePath(url)
//gone: getSelectedProject()

//**** Compatibility:
// only called on ko.toolboxes.user
// and attribute is always 'name'.
toolboxBaseManager.prototype.findItemByAttributeValue = function(attribute, value) {
  this.log.debug("Calling toolboxBaseManager.findItemByAttributeValue");
  var toolbox = ko.toolbox2.getStandardToolbox();
  var tools = ko.toolbox2.manager.toolsMgr.getToolsByTypeAndName(attribute, value);
  return tools.length ? tools[0]: null;
}

//gone: findPartByTypeAttributeValue(type, attribute, value)
//gone: findPartByAttributeValue(attribute, value)
//gone: applyPartKeybindings()
//gone: getPartsByURL(url)
//gone: loadFromProject(project)
//gone: loadToolboxFromURL(url)
//gone: reloadToolbox()
//gone: partServiceSetToolbox(toolbox)
//gone: verifyUnchanged()
//gone: save()
//gone: toolboxBaseManager.prototype.observe = function(subject, topic, data);
//gone: canUnload()
//gone: unload()
//gone: getter currentProject
//gone: getCurrentProject()
this.toolboxBaseManager = toolboxBaseManager;



/******************************************************/
/*                   User Toolbox                     */
/******************************************************/


//---- Support for the user/personal Toolbox

function toolboxManager() {
}

// The following two lines ensure proper inheritance (see Flanagan, p. 144).
toolboxManager.prototype = new toolboxBaseManager();
toolboxManager.prototype.constructor = toolboxManager;

//gone: toolboxManager.prototype.init()
//gone: partServiceSetToolbox(toolbox)
//gone: installSamples(sampleToolboxPath, version)
//gone: sharedToolboxManager()
//gone: partServiceSetToolbox(toolbox)
//gone: Toolbox_ExportItems and ko.projects.exportItems

// This is still needed for exporting projects.

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

this.addCommand = function AddCommandToToolbox(command, cwd, env, insertOutput,
                             operateOnSelection, doNotOpenOutputWindow, runIn,
                             parseOutput, parseRegex, showParsedOutputList,
                             name /* default=command */ )
{
    var part = ko.toolbox2.createPartFromType('command');
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
    ko.toolbox2.addItem(part);
    ko.uilayout.ensureTabShown('toolbox2viewbox');
}


window.addEventListener("komodo-ui-started", function() {
    window.controllers.appendController(new toolboxController());
});

}).apply(ko.toolboxes);






(function() { // ko.projects

var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
      .getService(Components.interfaces.nsIStringBundleService)
      .createBundle("chrome://komodo/locale/project/peFolder.properties");

this.exportItems = function Toolbox_ExportItems(items) {
    if (items.length == 0) {
        log.error("No items to package");
        return;
    }
    var defaultfilename = _bundle.GetStringFromName("exported.komodoproject");
    var defaultDir = items[0].project.getFile().dirName;
    var komodoProjectLabel = _bundle.GetStringFromName("Komodo Project");
    var filename = ko.filepicker.saveFile(
            defaultDir, defaultfilename,
            _bundle.GetStringFromName("Export Selected Items To..."), // title
            komodoProjectLabel, // default filter
            [komodoProjectLabel, "All"]); // filters
    if (filename == null) {
        return;
    }
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
        ko.dialogs.alert(
            _bundle.formatStringFromName('There was an error exporting project X:X',
                                         [project.name,
                                          lastErrorSvc.getLastErrorMessage()], 2));
    }
}

this.exportPackageItems = function Toolbox_ExportPackageItems(items) {
    if (typeof(items) == 'undefined' || !items || items.length < 1) {
        ko.dialogs.alert(_bundle.GetStringFromName("Please select items in the toolbox to export first."));
        return;
    }
    var defaultDir = items[0].project.getFile().dirName;
    var localPath = ko.filepicker.saveFile(
            defaultDir, items[0].name + ".kpz", // default dir and filename
            _bundle.GetStringFromName("Export Selected Items to a Package"), // title
            _bundle.GetStringFromName("Komodo Package"), // default filter name
            ["All"]); // filter names to show
    if (localPath == null) {
        return;
    }
    var packager = Components.classes["@activestate.com/koProjectPackageService;1"]
                      .getService(Components.interfaces.koIProjectPackageService);
    packager.packageParts(localPath, items.length, items, true);
}

}).apply(ko.projects);
