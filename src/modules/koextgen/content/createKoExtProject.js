// Copyright (c) 2000-2011 ActiveState Software Inc.
// See the file LICENSE.txt for licensing information.

/* Do stuff when the user chooses to create one of these projects.
 *
 * Based on rails createRailsProject.js
 */

if (typeof(ko) == 'undefined') {
    var ko = {};
}
if (!('koextgen' in ko)) {
    ko.koextgen = {};
}

(function() {
var os = Components.classes["@activestate.com/koOs;1"].getService();
var ospath = os.path;

var firstRun = true;

var bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
            .getService(Components.interfaces.nsIStringBundleService)
            .createBundle("chrome://koextgen/locale/koextgen.properties");

this.createExtGenProject = function(targetName) {
    var mainVersion = parseInt(Components.classes["@activestate.com/koInfoService;1"]
       .getService(Components.interfaces.koIInfoService).version.split('.')[0]);
    var project;
    if (mainVersion < 7) {
        // Bug 90957 -- ko.projects.manager.createNewProject not in earlier versions, so use its code guts.
        var filename = ko.projects.manager._getNewProjectPath();
        if (filename == null) {
            return;
        }
        var uri = ko.uriparse.localPathToURI(filename);
        project = Components.classes["@activestate.com/koProject;1"]
            .createInstance(Components.interfaces.koIProject);
        project.create();
        project.url = uri;
        if (!ko.projects.manager._saveNewProject(project)) {
            return;
        }
    } else {
        project = ko.projects.manager.createNewProject();
    }
    if (!project) {
        return;
    }
    var projectURI = project.url;
    var projectFileEx = project.getFile();
    // Get the project's location, then from one point higher populate it.
    var projectPath = projectFileEx.path;
    var projectDirPath = projectFileEx.dirName;
    var toolbox = ko.toolbox2.getProjectToolbox(project.url);

    var koExt = ko.koextgen.extensionLib;
    
    var prefset = project.prefset;
    var baseName = projectFileEx.baseName;
    var ext = projectFileEx.ext;
    baseName = baseName.substr(0, baseName.length - ext.length);
    //XXX: Reinstate ability to modify settings.
    var data = {};
    data = {
        'valid': false,
        'configured': false,
        'vars': {
            'id': '',
            'name': baseName + ' Extension',
            'creator': 'Me',
            'version': '0.1',
            'description': '',
            'homepageURL': '',
            'ext_name': baseName
        }
    };
    var setup_xul_uri = "chrome://koextgen/content/resources/setup.xul";
    window.openDialog(
        setup_xul_uri,
        "_blank",
        "centerscreen,chrome,resizable,scrollbars,dialog=no,close,modal=yes",
    data);
    if (data.valid) {
        if(koExt.updateProject(projectDirPath, targetName, data.vars)) {
            prefset.setBooleanPref('configured', true);
            //var configureMacro = ko.toolbox2.createPartFromType("macro");
            //ko.toolbox2.addItem(configureMacro, toolbox, /*selectItem=*/false);
            //configureMacro.value = "alert('ready are we recording')";
            //TODO: Finish building the configure macro
            var msg = 'Extension Project ' + data.vars.name + ' configured!';
            ko.statusBar.AddMessage(msg, 'project', 3000, true);
            ko.projects.manager.saveProject(project);

            var buildMacroContents = ko.koextgen.extensionLib.getTemplateContents("build.js");
            var buildMacro = ko.toolbox2.createPartFromType("macro");
            buildMacro.name = 'Build';
            buildMacro.value = buildMacroContents;
            buildMacro.iconurl = "chrome://fugue/skin/icons/building--plus.png";
            ko.toolbox2.addItem(buildMacro, toolbox, /*selectItem=*/true);
            buildMacro.setBooleanAttribute('trigger_enabled', false);
            
            buildMacro.setLongAttribute('rank', 100);
            buildMacro.setBooleanAttribute('async', true);
            buildMacro.setStringAttribute('language', "JavaScript");
            buildMacro.save();
        } else {
            alert('Error encountered: '+koExt.error+"\nConfiguration aborted.");
        }
    }
};
}).apply(ko.koextgen);
