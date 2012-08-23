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

(function __rails_init() {
    
var log = ko.logging.getLogger('rails');
var bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
            .getService(Components.interfaces.nsIStringBundleService)
            .createBundle("chrome://railstools/locale/rails.properties");
this.bundle = bundle;

this.version = 0.70;

this.gprefs = Components.classes["@activestate.com/koPrefService;1"]
        .getService(Components.interfaces.koIPrefService).prefs;
        
this.CmdSequenceRunner = function(editor, cmds, end_note) {
    this.editor = editor;
    this.cmds = cmds;
    this.end_note = end_note;
    this.options = {};
}

this.getRailsVersion = function(railsPath/* =undefined*/) {
    if (!railsPath) {
        try {
            railsPath = this.gprefs.getStringPref('rails.location');
        } catch(ex) {
            dump("Error getting rails version:  " + ex + "\n");
        }
        if (!railsPath) {
            throw new Error(bundle.GetStringFromName("Please use Preferences to specify rails location"));
        }
    }
    var runSvc = Components.classes["@activestate.com/koRunService;1"].
        getService(Components.interfaces.koIRunService);
    var output = {}, errors = {};
    runSvc.RunAndCaptureOutput(railsPath + " -v", null, null, null,
                               output, errors);
    if (errors.value) {
        //log.error("Error getting rails version: " + errors.value);
        throw new Error("Error getting rails version: " + errors.value);
    }
    return output.value.replace(/Rails\s+/i, "").replace(/\n/, "");
}

this.getRailsVersionAsTuple = function(railsPath) {
    var str = this.getRailsVersion(railsPath);
    return str.split(".").map(function(s) parseInt(s));
}

this.validateVersion = function(appPath, appName) {
    // do a sanity check:
    var runSvc = Components.classes["@activestate.com/koRunService;1"].getService();
    var output = {};
    var error = {};                
    runSvc.RunAndCaptureOutput('"' + appPath + '" --version',
                               '', '', '',
                               output, error);
    var re = new RegExp(appName + '(?:\\.exe)?\\s+Ver[\\s\\d\.]+Distrib[\\s\\d\\.]+',
                        'i');
    var res = re.test(output.value);
    if (!res) {
        dump("Expecting " + appName
             + " from " + appPath
             + ", got " + output.value + "\n");
    }
    return res;
};
this.mysqlAdminFinder = function() {
    if (this.mysqladminPath) {
        return this.mysqladminPath;
    }
    var prefName = "rails.mysqladminPath";
    this.mysqladminPath = this.gprefs.getStringPref(prefName);
    if (this.mysqladminPath) {
        return this.mysqladminPath;
    }
    var default_dir = ko.filepicker.internDefaultDir(prefName);
    var path = ko.filepicker.browseForExeFile(default_dir, null,
                                              bundle.GetStringFromName("Where is mysqladmin located"),
                                              null,
                                              null
                                              );
    if (path) {
        ko.filepicker.updateDefaultDirFromPath(prefName, path);
        return this.mysqladminPath = path;
    }
    throw new Error(bundle.GetStringFromName("Please specify the location of mysqladmin before continuing"));
};

this.db_adapters = {},
this.db_adapter_handlers = null,
this.db_adapter_commands = {
    mysql : {
        'create' : "-u %(username) --password=%(password) %?(host) %?(socket)  create %(database)",
        'delete' : "-u %(username) --password=%(password) %?(host) %?(socket) --force drop %(database)"
    },
    __END__ : null
};
this.db_adapter_commands.mysql2 = this.db_adapter_commands.mysql;

this.MissingInfoException = function() {};
this.MissingInfoException.prototype = new Error();

// This function does the following:
// 1. Get the root name of the database from the yaml file
// 2. Get the username and password from the yaml file
// 3. Verify we know how to handle the specified adapter        
// 4. Build or delete the databases

// @param {Object} "editor"-- the top-level object macros execute in
// @param {String} "displayOperation"-- one of 'create' or 'delete'
// @param {String} "displayOperationGerund"-- one of 'creation' or 'deletion'
this.manageDatabases = function(editor, displayOperation, displayOperationGerund) {
    try {
        this.manageDatabases_aux(editor, displayOperation, displayOperationGerund);
        return;
    } catch(ex if ex instanceof this.MissingInfoException) {
        var prompt = ex.message;
        var title =  bundle.formatStringFromName("Komodo needs more information to finish Xing the database",
                                                 [displayOperationGerund], 1);
        var dialogAction = ko.dialogs.customButtons(prompt,
                                                ['OK', 'Help', 'Preferences'], // buttons
                                                null, // default response (OK)
                                               null, // text -- inner selectable box
                                                title);
        if (dialogAction == 'Preferences') {
            prefs_doGlobalPrefs('RailsSettings');
        } else {
            if (dialogAction == 'Help') {
                var prefPanel = ex.prefPanelID || 'rails_tutorial';
                ko.help.open(prefPanel);
            }
            return;
        }
    }
}

this._supportsManageDatabases = {
    'mysql' : true,
    'oracle' : true,
    'postgres' : true
};

this._implementsManageDatabases = {
    'mysql' : true
};

this.manageDatabases_aux = function(editor, displayOperation, displayOperationGerund) {
    try {
        var config = this.parseConfig();
    } catch(ex) {
        alert(ex + "\n");
        return;
    }
    try {
        var preferredDB = this.gprefs.getStringPref("rails.database");
    } catch(ex) {
        preferredDB = null;
    }
    if (!preferredDB) {
        var ex = new this.MissingInfoException(bundle.GetStringFromName("No Rails Database has been set"));
        ex.prefPanelID = "Rails.database"
        throw ex;
    }
    var macro = ko.macros.current;
    if (!this._supportsManageDatabases[preferredDB]) {
        throw new Error(bundle.formatStringFromName("The macro X cant be used with the Y",
                                                    [macro.name , preferredDB], 2));
    }
    if (!this.db_adapter_handlers) {
        this.db_adapter_handlers = {};
    }
    if (!(preferredDB in this.db_adapter_handlers)) {
        //TODO: generalize
        switch (preferredDB) {
            case 'mysql': 
            this.db_adapter_handlers.mysql2 = this.db_adapter_handlers.mysql = this.mysqlAdminFinder;
            break;
        }
        // put other handlers here.
    }
    var cmds = [];
    for (var type in {'development':null, 'test':null, 'production':null}) {
        var thisConfig = config[type];
        var dbname = thisConfig.database;
        if (!dbname) {
            ko.extensions.rails.append_terminal_output(bundle.formatStringFromName("No database specified for type X",
                                                                                   [type], 1));
            continue;
        }
        var adapter = thisConfig['adapter'];
        if (!(adapter in this.db_adapters)) {
            if (adapter.toLowerCase() in this.db_adapter_handlers) {
                this.db_adapters[adapter] = this.db_adapter_handlers[adapter.toLowerCase()].apply(this);
            } else {
                this.db_adapters[adapter] = null;
            }
        }
        if (!this.db_adapters[adapter]) {
            ko.extensions.rails.append_terminal_output(bundle.formatStringFromName("Sorry youll have to manually X database Y",
                                                                                   [displayOperation, dbname, adapter], 3));
            continue;
        }
        var rawCommand = this.db_adapter_commands[adapter][displayOperation];
        var finishedCommand = (this.quote_if_needed(this.db_adapters[adapter]) + " "
                               + this.interpolate(rawCommand, thisConfig));
        
        cmds.push(finishedCommand);
    }
    if (cmds.length > 0) {
        (new this.CmdSequenceRunner(editor, cmds,
            bundle.formatStringFromName("Database Xing done", [displayOperationGerund], 1))).runner();
    }
};
this._check_opt = function(options, arg, default_val) {
    return typeof(options[arg]) == "undefined" ? default_val : options[arg];
};

this.getRailsVersionInRange = function(startVal, endVal, railsPath) {
    if (typeof(railsPath) == "undefined") {
        railsPath = this.gprefs.getStringPref('rails.location');
    }
    var railsVersion = ko.extensions.rails.getRailsVersionAsTuple(railsPath);
    var versionNo = railsVersion[0];
    if (railsVersion[0] < startVal) {
        versionNo = startVal;
    } else if (railsVersion[0] > endVal) {
        versionNo = endVal;
    }
    return versionNo;
}
/**
 * %(name) => replace with dict[name], quoting if necessary
 * %*(name) => dict[name], never quoted
 * %?(name) ==> --name=quoteIfNecessary(dict[name])
 *
 * %% => %
 *
 * All other sequences are copied as is, including %x => %x
 * These might be reinterpreted in future versions, so it's
 * safer to always escape a literal '%' as '%%'.
 *
 */

this.interpolate = function(rawCommand, dict) {
    var finishedCommand = "";
    var m;
    while (rawCommand.length > 0) {
        if ((m = /^%([\?\*]?)\((.*?)\)(.*)/.exec(rawCommand))) {
            var prefix = m[1];
            var name = m[2];
            var val = dict[name];
            if (val) {
                if (prefix == "*") {
                    finishedCommand += val; // never quote
                } else if (prefix == "?") {
                    finishedCommand += ("--" + name + "=" +
                                        this.quote_if_needed(val));
                } else {
                    finishedCommand += this.quote_if_needed(val);
                }
            }
            rawCommand = m[3];
        } else if (rawCommand[0] == "%" && rawCommand.length > 1
                   && rawCommand[1] == "%") {
            finishedCommand += "%";
            rawCommand = rawCommand.substr(2);
        } else {
            var x = rawCommand.indexOf('%');
            if (x > -1) {
                finishedCommand += rawCommand.substr(0, x);
                rawCommand = rawCommand.substr(x);
            } else {
                finishedCommand += rawCommand
                rawCommand = "";
            }
        }
    }
    return finishedCommand;
};
    
this.runCommand = function(editor, cmd, options, terminationCallback) {
    if (!('dir' in options)) {
        options.dir = ko.projects.manager.currentProject.getFile().dirName;
    }
    // Check for undefined commands
    ko.run.runCommand(editor, cmd,
                      options.dir,
                      this._check_opt(options, 'env', ''),
                      this._check_opt(options, 'insertOutput', false),
                      this._check_opt(options, 'operateOnSelection', false),
                      this._check_opt(options, 'doNotOpenOutputWindow', false),
                      this._check_opt(options, 'runIn', "command-output-window"),
                      this._check_opt(options, 'parseOutput', false),
                      this._check_opt(options, 'parseRegex', ''),
                      this._check_opt(options, 'showParsedOutputList', false),
                      this._check_opt(options, 'name', null),
                      this._check_opt(options, 'clearOutputWindow', true),
                      terminationCallback);
};
// return an array of environment strings
this.fixUserEnvPath = function fixUserEnvPath(targetPath) {
    var userEnvSvc = Components.classes["@activestate.com/koUserEnviron;1"].getService(Components.interfaces.koIUserEnviron);
    var countHolder = {};
    var envStrings = userEnvSvc.GetEnvironmentStrings(countHolder);
    var osSvc = Components.classes["@activestate.com/koOs;1"].getService(Components.interfaces.koIOs);
    var pathsep = osSvc.pathsep;
    for (var i = 0; i < envStrings.length; i++) {
        var env = envStrings[i];
        var parts = env.split('=', 2);
        if (parts[0].toLowerCase() == "path") {
            var pathdirs = parts[1].split(pathsep);
            if (pathdirs[0] != targetPath) {
                pathdirs.unshift(targetPath);
                return (parts[0] + '=' + pathdirs.join(pathsep));
            }
            break;
        }
    }
    return null;
};
this.get_path_by_ko_pref = function get_path_by_ko_pref(appName) {
    var path = null;
    try {
        path = ko.interpolate.interpolateString("%(" + appName + ")");
    } catch(ex) {
        dump("get_path_possibly_quoted: " + ex + "\n");
    }
    return path;
};
this.quote_if_needed = function quote_if_needed(s) {
    var s1;
    if (/[^\w.:\-\"\'\\\/]/.test(s)) {
        s1 = '"' + s + '"';
    } else {
        s1 = s;
    }
    return s1;
};
this.get_path_possibly_quoted = function get_path_possibly_quoted(appName) {
    var path = this.get_path_by_ko_pref(appName);
    if (path) {
        path = this.quote_if_needed(path);
    }
    return path;
};
this.generateRailsObject = function generateRailsObject(editor,
                                                        extensions,
                                                        railsTypeName,
                                                        part_names) {
    var name;
    var project = ko.projects.manager.currentProject;
    if (part_names) {
        var name_list;
        if (part_names.length == 2) {
            var values_prompt = bundle.formatStringFromName("Please enter values for the X", [railsTypeName], 1);
            name_list = ko.dialogs.prompt2(ko.extensions.rails.capitalize(railsTypeName) + " values",
                                           part_names[0] + ":", "", part_names[1] + ":", "",
                                           values_prompt,
                                           "rails:" + part_names[0], "rails:" + part_names[1]);
            if (!name_list) return;
        } else {
            name_list = [];
            for (var i = 0; i < part_names.length; i++) {
                var part_name = part_names[i];
                var part_name_prompt = bundle.formatStringFromName("Please enter a name for the X", [part_name], 1);
                var n = ko.dialogs.prompt(ko.extensions.rails.capitalize(railsTypeName) + " " + part_name + " name",
                                          railsTypeName + "/" + part_name, "",
                                          part_name_prompt,
                                          "rails:" + part_name);
                if (!n) return;
                name_list.push(n);
            }
        }
        name = name_list.join(" ");
    } else {
        var part_name_prompt = bundle.formatStringFromName("Please enter a name for a X", [part_name], 1);
        name = ko.dialogs.prompt(ko.extensions.rails.capitalize(railsTypeName) + " name",
                                 railsTypeName, "",
                                 part_name_prompt);
    }
    if (!name) {
        return;
    }
    var projectDirURL = project.url.substring(0, project.url.lastIndexOf("/"));
    var terminationCallback = function(retval) {
        try {
            var termscin;
            var mainVersion = parseInt(Components.classes["@activestate.com/koInfoService;1"]
.getService(Components.interfaces.koIInfoService).version.split('.')[0]);
            if (mainVersion < 7) {
                termscin = document.getElementById("runoutput-scintilla").scimoz;
            } else {
                termscin = document.getElementById("runoutput-desc-tabpanel").contentDocument.getElementById("runoutput-scintilla").scimoz;
            }
            var text = termscin.text;
            var textLines = text.split(/\r?\n/);
            for (var i = 0; i < textLines.length; i++) {
                try {
                    var a = textLines[i].split(/\s+/);
                    if (a[0].length == 0) a.shift();
                    if (a[1] && a[1].indexOf(".") != -1) {
                        var doit = (!extensions);
                        if (!doit) {
                            for (var ext in extensions) {
                                if (a[1].lastIndexOf(ext) == a[1].length - ext.length) {
                                    doit = true;
                                    break;
                                }
                            }
                        }
                        if (doit) {
                            var fname = project.getFile().dirName + "/" + a[1];
                            fname = projectDirURL + "/" + a[1];
                            ko.open.URI(fname);
                        }
                    }
                } catch(ex) { dump(textLines[i] + ": " + ex + "\n"); }
            }
        } catch(ex) { dump(ex + "\n"); }
    };
    
    // Arguments for the commands

    var cmd_by_version = {
        2: '%(rubyPath) script/generate %(railsTypeName) %*(name) --skip',
        3: '%(rubyPath) script/rails generate %(railsTypeName) %*(name) --skip'
    }
    var rubyPath = this.get_path_by_ko_pref('ruby');
    var versionNo = ko.extensions.rails.getRailsVersionInRange(2, 3);
    var config = {
        rubyPath: rubyPath,
        railsTypeName: railsTypeName,
        name:name
    }
    var cmd = this.interpolate(cmd_by_version[versionNo], config);
    var options = {
        dir: project.getFile().dirName,
        env: this.fixUserEnvPath(rubyPath),
        __END__ : null
    };
    ko.extensions.rails.runCommand(editor, cmd, options, terminationCallback);
};

this.noRuby = function() {
    throw new Error(bundle.GetStringFromName("No Komodo pref for Ruby was found"));
}

this.installPlugin = function installPlugin(editor, plugin, terminationCallback) {
    if (typeof(terminationCallback) == "undefined") terminationCallback = null;
    var rubyPath = this.get_path_by_ko_pref('ruby');
    if (!rubyPath) {
        this.noRuby();
    }
    var cmd_by_version = {
        2: '%(rubyPath) script/plugin install %(plugin)',
        3: '%(rubyPath) script/rails plugin install %(plugin)'
    }
    var versionNo = ko.extensions.rails.getRailsVersionInRange(2, 3);
    var config = {
        rubyPath: rubyPath,
        plugin:plugin
    }
    var cmd = this.interpolate(cmd_by_version[versionNo], config);
    var options = {
        env: this.fixUserEnvPath(rubyPath),
        __END__ : null
    };
    this.runCommand(editor, cmd, options, terminationCallback);
};
     
this.setup_associated_paths_env = function setup_associated_paths_env(obj) {
    var rawRubyPath = this.get_path_by_ko_pref('ruby');
    if (!rawRubyPath) {
        this.noRuby();
    }
    var osPathSvc = Components.classes["@activestate.com/koOsPath;1"].getService(Components.interfaces.koIOsPath);
    var rootDir = osPathSvc.dirname(rawRubyPath);
    if ('base' in obj) {
        obj[obj.base] = this.quote_if_needed(osPathSvc.join(rootDir, obj.base));
    }
    obj.ruby = this.quote_if_needed(rawRubyPath);
    obj.env = this.fixUserEnvPath(rawRubyPath);
};

this.launchRubyAppInConsole = function launchRubyAppInConsole(editor, cmd_args_str) {
    var rawRubyPath = this.get_path_by_ko_pref('ruby');
    if (!rawRubyPath) {
        this.noRuby();
    }
    var options = { runIn: "new-console",
                    env: this.fixUserEnvPath(rawRubyPath),
                    __END__ : null
    };
    var rubyPath = this.quote_if_needed(rawRubyPath);
    var cmd = rubyPath + '  ' + cmd_args_str;
    ko.extensions.rails.runCommand(editor, cmd, options);
};
this.mysqladminPath = null,

this.getConfig = function() {
    var project = (Components.classes["@activestate.com/koPartService;1"].getService().
                   runningMacro.project);
    var os = Components.classes["@activestate.com/koOs;1"].getService();
    var ospath = os.path;
    var parts = [project.getFile().dirName, 'config', 'database.yml'];
    var configPath = ospath.joinlist(parts.length, parts);
    if (!ospath.exists(configPath)) {
        throw new Error(bundle.formatStringFromName("Cant find file X", [configPath], 1));
    }
    var contents = os.readfile(configPath);
    return contents;
};
this.parseConfig = function(configText) {
    function mergeConfigs(curr_hash, template_hash) {
        for (var p in template_hash) {
            curr_hash[p] = template_hash[p];
        }
    }
    if (!configText) {
        configText = this.getConfig();
    }
    var lines = configText.split(/\r?\n/);
    var hash = {development:{}, test:{}, production:{}};
    var curr_hash = null;
    var aliases = {};
    for (var i = 0; i < lines.length; i++) {
        var line = lines[i];
        if (/^(\w+)s*:\s+\&(\w+)/.test(line)) {
            var anchor_name = RegExp.$2;
            if (!aliases[anchor_name]) {
                aliases[anchor_name] = {}
            }
            curr_hash = aliases[anchor_name];
        } else if (/<<\s*:\s*\*(\w+)/.test(line)) {
            var anchor = RegExp.$1;
            if (!aliases[anchor]) {
                dump("rails_init: parseConfig: Anchor " + anchor + " not recognized\n");
            } else {
                mergeConfigs(curr_hash, aliases[anchor]);
            }
        } else if (/^(development|test|production):/.test(line)) {
            curr_hash = hash[RegExp.$1];
        } else if (/^\s+(\w+)s*:\s*(.*?)\s*$/.test(line)) {
            curr_hash[RegExp.$1] = RegExp.$2;
        }
    }
    return hash;
};
this.configSupported = function configSupported(config, requirements) {
    for (var i in requirements) {
        var opt = requirements[i];
        var field = opt[0];
        if (config[field] && config[field] != opt[1]) {
            return opt[2];
        }
    }
    return null;
};
// put helper functions here

this.capitalize = function capitalize(s) {
    if (s.length == 0) return s;
    else if (s.length == 1) return s.toUpperCase()
    else return s[0].toUpperCase() + s.substr(1);
};
this._eol_strs = ["\r\n", "\n", "\r"],

this.append_terminal_output = function(str) {
try {
var scimoz = document.getElementById("runoutput-scintilla").scimoz;
var currNL = this._eol_strs[scimoz.eOLMode];
var full_str = (scimoz.getColumn(scimoz.length) == 0) ? "" : currNL;
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
// dump(ex + "\n");
// We failed to write str to the output-window, so alert it.
alert(str);
}
};

this.setDefaultPreferences = function(prefset /* undef */) {
    if (!prefset) {
        prefset = this.gprefs; 
    }
    var defaultValues = {
        'rails.location': '', 'rails.database': 'sqlite3',
        'rails.oraclePath' : '',
        'rails.mysqlPath' : '',
        'rails.mysqladminPath' : '',
        'rails.postgresqlPath' : '',
        'rails.sqlite2Path' : '',
        'rails.sqlite3Path' : ''
    };
    var setPrefs = [];
    for (var p in defaultValues) {
        if (!prefset.hasPref(p)) {
            setPrefs.push(p);
            prefset.setStringPref(p, defaultValues[p]);
        }
    }
    if (setPrefs.length) {
        dump("setDefaultPreferences: set prefs [" + setPrefs.join(", ") + "]\n");
    }

}

this.CmdSequenceRunner.prototype = {
terminationCallback: function() {
    try {
    this.clearOutputWindow = false;
    this.cmds.shift();
    if (this.cmds.length > 0) {
        this.options.clearOutputWindow = false;
        this.runner();
    } else if (this.end_note) {
        ko.extensions.rails.append_terminal_output(this.end_note);
    }
    }catch(ex)  { alert(ex + "\n"); }
},
runner: function() {
    var self = this;
    var tcb = function() {
        self.terminationCallback();
    }
    ko.extensions.rails.runCommand(this.editor, this.cmds[0], this.options, tcb);
}
};

}).apply(ko.extensions.rails);
