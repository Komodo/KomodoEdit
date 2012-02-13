/**
 * Copyright (c) 2000-2011 ActiveState Software Inc.
 * See the file LICENSE.txt for licensing information.
 */
if (!('stackato' in ko)) ko.stackato = {};

(function() {
var prefs = ko.prefs;
// This is a list of 1 because it used to contain tclsh info as well.
["stackato.location"].forEach(function(prefName) {
    if (!prefs.hasPref(prefName)) {
        prefs.setStringPref(prefName, "");
    }
});
var bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
    .getService(Components.interfaces.nsIStringBundleService)
    .createBundle("chrome://stackatotools/locale/stackato.properties");
this.data = {};

this.getStackatoEnv = function(obj) {
    // obj.stackato and obj.path will be quoted if necessary
    // obj.cwd won't be, since it's usually passed as a separate arg.
    var prefs = ko.prefs;
    try {
        obj.stackato = prefs.getStringPref("stackato.location");
    } catch(ex) {
        dump("getting stackato: " + ex + "\n");
        obj.stackato = null;
    }
    if (!obj.stackato) {
        var prompt = bundle.GetStringFromName("Komodo needs to know where the Stackato executable is located");
        var title = bundle.GetStringFromName("Stackato Configuration");
        var defaultResponse = bundle.GetStringFromName("No");
        var response = ko.dialogs.yesNo(prompt, defaultResponse, null, title);
        if (response == bundle.GetStringFromName('Yes')) {
            prefs_doGlobalPrefs('stackatoItem');
            return;
        }
    }
    obj.stackato = this.quote_if_needed(obj.stackato);
    var sysUtilsSvc = Components.classes['@activestate.com/koSysUtils;1'].getService(Components.interfaces.koISysUtils);
    var osSvc = Components.classes["@activestate.com/koOs;1"].getService(Components.interfaces.koIOs);
    var osPathSvc = Components.classes["@activestate.com/koOsPath;1"].getService(Components.interfaces.koIOsPath);
    var environSvc = Components.classes["@activestate.com/koUserEnviron;1"].getService(Components.interfaces.koIUserEnviron);
    var path = environSvc.get("PATH");
    obj.path = this.quote_if_needed([osPathSvc.dirname(obj.stackato), path].join(osSvc.pathsep));
    try {
        var file = ko.views.manager.currentView.koDoc.file;
        if (file.scheme == "file") {
            obj.cwd = file.dirName;
        } else {
            obj.cwd = null;
        }
    } catch(ex2) {
        dump("error getting current view dir: " + ex2 + "\n");
    }
};

this.getRecentApp = function() {
    return this.getRecentFeature("appName");
};

this.setRecentApp = function(appName) {
    this.setRecentFeature("appName", appName);
};

this.getRecentFeature = function(name) {
    if (name in this.data) {
        var appObj = this.data[name];
        if (new Date().valueOf() - appObj.timestamp < 3600 * 1000) {
            return appObj.value;
        }
    }
    return "";
};

this.setRecentFeature = function(name, value) {
    if (!name in this.data || !this.data[name]) {
        this.data[name] = {};
    }
    var appObj = this.data[name];
    appObj.value = value;
    appObj.timestamp = new Date().valueOf();
};

this.getCurrentAppInfo = function(envObj) {
    var koRunSvc = Components.classes["@activestate.com/koRunService;1"].getService(Components.interfaces.koIRunService);
    var command = envObj.stackato + " apps";
    var env = "PATH=" + envObj.path;
    var output = {}, errors = {};
    var status = koRunSvc.RunAndCaptureOutput(command, null, env, null, output, errors);
    output = output.value;
    errors = errors.value;
    if (status ) {
        ko.dialogs.alert(bundle.formatStringFromName("stackato apps failed_status_X_errors", [status, errors], 2));
        return [];
    }
    var appInfoItems = [];
    dump("getCurrentAppInfo: Matching " + output + "\n");
    var pattern = /\|\s*(\S+?)\s*\|\s*(\d+)\s*\|\s*(\S+)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|/g;
    //              | app name    | count      | health     | uris       | services    | 
    var result;
    while ((result = pattern.exec(output)) !== null) {
        dump("getCurrentAppInfo: got appName " + result[1] + "\n");
        var urls = result[4].split(/\s*,\s*/);
        if (urls.length == 1 && !urls[0]) urls = [];
        appInfoItems.push({
            name: result[1],
            count: result[2],
            health: result[3],
            urls: urls,
            services: result[5]
        });
        var item = appInfoItems[appInfoItems.length - 1];
        for (var p in item) {
            dump(p + ": " + item[p] + "\n");
        }
    }
    return appInfoItems;
};

this.getCurrentAppNames = function(envObj) {
    return this.getCurrentAppInfo(envObj).map(function(item) item.name);
};

this.getSelectedApp = function(envObj, appNames) {
    if (typeof(appNames) === "undefined") {
        appNames = this.getCurrentAppNames(envObj);
    }
    if (appNames.length == 0) {
        ko.dialogs.alert(bundle.GetStringFromName("No apps have been defined"));
        this.setRecentApp(null);
        return null;
    } else if (appNames.length == 1) {
        this.setRecentApp(appNames[0]);
        return appNames[0];
    } else {
        var currentAppName = this.getRecentApp();
        var idx = currentAppName ? appNames.indexOf(currentAppName) : -1;
        var title = bundle.GetStringFromName("Select an app");
        var prompt = bundle.GetStringFromName("Select the app to run");
        var selectionCondition = "one";
        var selectedIndex = idx === -1 ? 0 : idx;
        var newAppName = ko.dialogs.selectFromList(title, prompt, appNames, selectionCondition,
                                                   null, null, null, null, selectedIndex);
        if (newAppName !== null) {
            newAppName = newAppName[0];
            this.setRecentApp(newAppName);
        }
        return newAppName;
    }
};

this.doInformationCommand = function(operation) {
    var obj = {};
    this.getStackatoEnv(obj);
    if (!obj.stackato || !obj.path) {
        dump("Bailing out of " + operation + "\n");
        return;
    }
    var command = [obj.stackato, operation].join(" ");
    var env = "PATH=" + obj.path;
    ko.run.runCommand(window, command, null, env,
                      false, false, false, "command-output-window");
};

this.quote_if_needed = function quote_if_needed(s) {
    var s1;
    if (/[^\w.:=\-\"\'\\\/]/.test(s)) {
        s1 = '"' + s + '"';
    } else {
        s1 = s;
    }
    return s1;
};

this.launchStackato = function() {
    return ko.windowManager.openOrFocusDialog(
        "chrome://stackatotools/content/stackato.xul",
        "komodo_stackato_interface",
        "chrome,all,close=yes,resizable,dependent=no",
        {ko:ko, 'window':window});
}

}).apply(ko.stackato);
if (!('extensions' in ko)) ko.extensions = {};
ko.extensions.stackato = ko.stackato; // for compatibility
