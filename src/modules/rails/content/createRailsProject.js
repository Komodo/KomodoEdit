/***** BEGIN LICENSE BLOCK *****
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

if (!('extensions' in ko)) {
    ko.extensions = {};
}
if (!('rails' in ko.extensions)) {
    ko.extensions.rails = {};
}

(function createRailsProject() {

var os = Components.classes["@activestate.com/koOs;1"].getService();
var ospath = os.path;

var firstRun = true;

var bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
            .getService(Components.interfaces.nsIStringBundleService)
            .createBundle("chrome://railstools/locale/rails.properties");
//var toolbox2Svc = ko.toolbox2.manager.toolbox2Svc;
//var toolsMgr = ko.toolbox2.manager.toolsMgr;
//var toolboxView = ko.toolbox2.manager.view;

function executableExists(osPathSvc, path) {
    if (osPathSvc.exists(path)) {
        return true;
    }
    if (Components.classes['@activestate.com/koInfoService;1'].
        getService(Components.interfaces.koIInfoService).platform.substring(0, 3) == "win") {
        for (var suffix in {cmd:null, bat:null, exe:null, com:null}) {
            if (osPathSvc.exists(path + "." + suffix)) {
                return true;
            }
        }
    }
    return false;
}       
    
// This function does lots of checking to help make the initial experience
// as smooth as possible.
function getRailsExecutable() {
    var msgs = {};
    var railsPath;
    var gprefs = Components.classes["@activestate.com/koPrefService;1"]
        .getService(Components.interfaces.koIPrefService).prefs;
    // Is there a Ruby?
    var osPathSvc = Components.classes["@activestate.com/koOsPath;1"].getService(Components.interfaces.koIOsPath);
    if (gprefs.hasPref('rails.location')) {
        railsPath = gprefs.getStringPref('rails.location');
        if (executableExists(osPathSvc, railsPath)) {
            return railsPath;
        }
    }
    var rubyPath = ko.interpolate.interpolateString("%(ruby)");
    if (!rubyPath) {
        msgs.prompt = bundle.GetStringFromName("Komodo couldnt find any Ruby executable");
        msgs.title = bundle.GetStringFromName("Ruby not found");
    }
    // Is the thing called Ruby most likely Ruby, and not some renamed program?
    var rubyDir;
    var output = null;
    if (rubyPath) {
        rubyDir = osPathSvc.dirname(rubyPath);
        if (/[^\w.:\-\"\'\\\/]/.test(rubyPath)) {
            rubyPath = '"' + rubyPath + '"';
        }
        var runSvc = Components.classes["@activestate.com/koRunService;1"].getService();
        output = {};
        var error = {};                
        runSvc.RunAndCaptureOutput(rubyPath + ' --version',
                                   '', '', '',
                                   output, error);
        output = output.value;
        if (!output) {
            msgs.prompt = bundle.formatStringFromName("Running X e puts RUBY_VERSION failed to work",
                                        [rubyPath], 1);
            msgs.title = bundle.GetStringFromName("Unexpected result from running the current selected ruby");
        }
        //dump("output = " + output + "\n");
    }
    // Is the Ruby recent enough?
    if (!msgs.prompt) {
        if (!/^ruby\s+([\d\.]+)/.test(output)) {
            msgs.prompt = bundle.formatStringFromName("Running rubyPath version gave unexpected output of Y",
                                                      [rubyPath, output], 2);
            msgs.title = bundle.GetStringFromName("Unexpected result from running the current selected ruby");
        } else {
            var items = RegExp.$1.split(".");
            if (items.length < 3) {
                if (items.length < 2) {
                    items[1] = 0;
                }
                items[2] = 0;
            }
            var verNum = 100 * ((100 * parseInt(items[0])) + parseInt(items[1])) + parseInt(items[2]);
            if (verNum < 10806) { // 1.8.3 => 100 * ((100 * 1) + 8) + 3;
                msgs.prompt = bundle.formatStringFromName("Komodo needs to work with at least version X of Ruby",
                                                          ['1.8.6', output], 2);
                msgs.title = bundle.formatStringFromName("Ruby version X isnt supported by Komodo",
                                                         [output], 1);
            }
        }
    }
    // Is there a Rails installed with that Ruby?
    if (!msgs.prompt) {
        railsPath = osPathSvc.join(rubyDir, "rails");
        if (executableExists(osPathSvc, railsPath)) {
            // Everything should work.
            return railsPath;
        }
        msgs.prompt = bundle.formatStringFromName("Komodo is currently using the Ruby installation at X",
                                                  [rubyDir], 1);
        msgs.title = bundle.GetStringFromName("Rails not found in the currently selected Ruby configuration");
    }
    var dialogAction = ko.dialogs.customButtons(msgs.prompt,
                                                ['OK', 'Help', 'Preferences'], // buttons
                                                null, // default response (OK)
                                                null, // text -- inner selectable box
                                                msgs.title);
    if (dialogAction == 'Preferences') {
        prefs_doGlobalPrefs('rubyItem');
    } else if (dialogAction == 'Help') {
        ko.help.open('rails_tutorial');
    }
    return null;
}


this.runRailsCommand = function runRailsCommand() {
    var project;
    var mainVersion = parseInt(Components.classes["@activestate.com/koInfoService;1"]
       .getService(Components.interfaces.koIInfoService).version.split('.')[0]);
    if (mainVersion < 7) {
        // stuff;
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
    var railsDirName = ospath.basename(projectDirPath);
    var databaseYamlPath = ospath.joinlist(3, [projectDirPath, "config", "database.yml"]);
    var ok = true;

    if (ospath.exists(databaseYamlPath)) {
        var title = bundle.GetStringFromName("Doing a partial install in a nonempty directory");
        var info = bundle.formatStringFromName("The directory X isnt empty",
                                               [projectDirPath, railsDirName, railsDirName, ospath.dirname(projectDirPath)], 4);
        var prompt = bundle.GetStringFromName("Rails directory not empty");
        ko.dialogs.alert(title, info, prompt);
        ok = false;
    }            
    if (/\W/.test(railsDirName)) {
        var prompt = bundle.GetStringFromName('Install here anyway');
        var info = bundle.GetStringFromName('This is not a recommended name for a Rails project');
        ok = ko.dialogs.okCancel(prompt, "OK", info) == "OK";
    }
    if (!ok) {
        return;
    }
    var containingDirPath = ospath.dirname(projectDirPath);
    var gprefs = Components.classes["@activestate.com/koPrefService;1"]
        .getService(Components.interfaces.koIPrefService).prefs;
    if (firstRun) {
        firstRun = false;
        ko.extensions.rails.setDefaultPreferences(gprefs);
    }
    var railsPath = getRailsExecutable();
    if (!railsPath) {
        return;
    }
    var database;
    try {
        database = gprefs.getStringPref("rails.database");
    } catch(ex) {
        dump("Can't get rails.database global pref: " + ex + "\n");
        database = null;
    }
    if (!database) {
    // Rails 2 uses sqlite by default, so get the choice of DB from the user
        var db_list = ["sqlite3", "mysql", "postgresql", "oracle", "sqlite2"];
        var database = ko.dialogs.selectFromList(
            bundle.GetStringFromName("Select a database"), // title,
            bundle.GetStringFromName("Which database do you want to use for this project"), // prompt,
            db_list, // items
            "one"); // selectionCond: exactly one
        if (database == null) {
            // canceled out
            return;
        } else if (!database) {
            database = db_list[0];
            gprefs.setStringPref("rails.database", database);
        }
    }
    if (/[^\w.:\-\"\'\\\\/]/.test(railsPath)) {
        railsPath = '"' + railsPath + '"';
    }
    var railsProjectName = projectFileEx.baseName;
    var ext = projectFileEx.ext;
    if (ext) {
        railsProjectName = railsProjectName.slice(0, -1 * ext.length);
    }
    
    // Arguments for the commands

    var cmd_by_version = {
        2: '%(railsPath) %(railsDirName) --skip --database=%(database)',
        3: '%(railsPath) new %(projectDirPath) --ruby=%(rubyPath) --skip --database=%(database)'
    }
    var versionNo = ko.extensions.rails.getRailsVersionInRange(2, 3, railsPath);
    var config = {
        railsPath: railsPath,
        rubyPath: ko.extensions.rails.get_path_by_ko_pref('ruby'),
        railsDirName: railsDirName,
        projectDirPath: projectDirPath,
        projectPath: projectPath,
        database: database
    }
    var cmd = ko.extensions.rails.interpolate(cmd_by_version[versionNo], config);
    var dir = containingDirPath;
    var env = '';
    var insertOutput = false;
    var operateOnSelection = false;
    var doNotOpenOutputWindow = false;
    var runIn = "command-output-window";
    var parseOutput = false;
    var parseRegex = '';
    var showParsedOutputList = false;
    var name = null;
    var clearOutputWindow = true;
    var terminationCallback = function() {
        // copied from rails_init.js
        var wrapper = {
            _eol_strs : ["\r\n", "\n", "\r"],
        
            append_terminal_output : function(str) {
                try {
                    // Before v7, runoutput-scintilla lived on the main form
                    // With 7.0 and on, it's in its own panel.
                    var scintillaThing =
                        (document.getElementById("runoutput-scintilla")
                         || document.getElementById("runoutput-desc-tabpanel").
                                     contentDocument.
                                     getElementById("runoutput-scintilla"));
                    var scimoz = scintillaThing.scimoz;
                    var currNL = this._eol_strs[scimoz.eOLMode];
                    var full_str = (scimoz.getColumn(scimoz.length) === 0) ? "" : currNL;
                    full_str = full_str.replace(/\x1b\[\d+m/, '');
                    full_str += "*************************************" + currNL + str + currNL;
                    var full_str_byte_length = ko.stringutils.bytelength(full_str);
                    var ro = scimoz.readOnly;
                    try {
                        scimoz.readOnly = false;
                        scimoz.appendText(full_str_byte_length, full_str);
                    } finally {
                        scimoz.readOnly = ro;
                    }
                } catch(ex) {
                    alert(ex);
                }
            },
            
            update_config_file: function() {
                try {
                    // Turn off pretty coloring
                    var osPathSvc = Components.classes["@activestate.com/koOsPath;1"].getService(Components.interfaces.koIOsPath);
                    var appConfigPath = osPathSvc.join(osPathSvc.join(projectDirPath,
                                                          "config"),
                                           "application.rb");
                    var fobj = Components.classes["@activestate.com/koFileEx;1"].
                        createInstance(Components.interfaces.koIFileEx);
                    fobj.URI = appConfigPath;
                    fobj.open('r');
                    var data = fobj.readfile();
                    fobj.close();
                    var newData = null;
                    var m = /((?:.*\n)*)([ \t]*)(config\..*?)(\r?\n)((?:.|\n)*)/.exec(data)
                    if (m) {
                        newData = (m[1] + m[2] + m[3] + m[4]
                                   + m[4]
                                   + m[2] + "# This line added by Komodo's CreateRailsProject function" + m[4]
                                   + m[2] + "config.colorize_logging = false" + m[4]
                                   + m[5] );
                        dump("Read " + data.length + "bytes, writing out "
                             + newData.length
                             +  " bytes\n");
                    } else {
                        dump("Can't match app.config data\n");
                    }
                    if (newData) {
                        fobj.open('w');
                        fobj.puts(newData);
                        fobj.close();
                    }
                } catch(ex) {
                    dump("Problems updating application.rb: " + ex + "\n");
                }
            }
        };
        wrapper.append_terminal_output("The " + railsDirName + " project is built\n");
        wrapper.update_config_file();
        ko.places.viewMgr.view.refreshFullTreeView();
    };
    ko.run.runCommand(self, cmd, dir, env, insertOutput,
                      operateOnSelection, doNotOpenOutputWindow,
                      runIn, parseOutput, parseRegex, showParsedOutputList,
                      name, clearOutputWindow, terminationCallback);
    // While the command is running, update the test-plan preferences
    // to point at this directory.
    if ('sleuth' in ko && ko.sleuth) {
        this.updateTestPlanDirectories(project, projectDirPath);
    }
}

this.updateTestPlanDirectories = function updateTestPlanDirectories(project, projectDirPath) {
    var prefset = project.prefset;
    if (!prefset) {
        prefset = Components.classes['@activestate.com/koPreferenceSet;1'].
                                     createInstance(Components.interfaces.koIPreferenceSet)
        project.prefset = prefset;
    }
    var prefset2 = Components.classes['@activestate.com/koPreferenceSet;1'].
                                     createInstance(Components.interfaces.koIPreferenceSet)
    prefset.setPref("testPlans", prefset2);
    var testPlans = [
        ["test all", "rake test",],
        ["test:functionals", "rake test:functionals"],
        ["test:integration", "rake test:integration"],
        ["test:plugins", "rake test:plugins"],
        ["test:units", "rake test:units"],
    ];
    for (var testPlan, i = 0; testPlan = testPlans[i]; i++) {
        var testPlanPref = Components.classes['@activestate.com/koPreferenceSet;1'].
                                         createInstance(Components.interfaces.koIPreferenceSet)
        testPlanPref.setStringPref("command_line", testPlan[1]);
        testPlanPref.setStringPref("directory", project.getFile().dirName);
        testPlanPref.setStringPref("language", "Ruby - Rake tests");
        prefset2.setPref(testPlan[0], testPlanPref);
        
        ko.sleuth.manager.setPrefToDir(testPlanPref,
                                       projectDirPath);
    }
}

this.createRailsProject = function() {
    this.runRailsCommand();
};
}).apply(ko.extensions.rails);
