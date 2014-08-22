/**
 * Copyright (c) 2000-2011 ActiveState Software Inc.
 * See the file LICENSE.txt for licensing information.
 */

//---- globals

//alert("Loading pref-stackato.js");

var log = ko.logging.getLogger("stackato.prefs");
log.setLevel(ko.logging.LOG_DEBUG);

var appInfoEx = null;
var osPathSvc = null;
var isWindows;
var widgets = {};
var runSvc;
var bundle;

// preferences managed by this module:
// stackato.location

function PrefStackato_OnLoad()
{
    widgets.stackatoLocation = document.getElementById("stackato.location");
    osPathSvc = Components.classes["@activestate.com/koOsPath;1"].getService(Components.interfaces.koIOsPath);
    isWindows = Components.classes["@activestate.com/koInfoService;1"].
            getService(Components.interfaces.koIInfoService).
            platform.toLowerCase().indexOf("win") === 0;
    bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
    .getService(Components.interfaces.nsIStringBundleService)
    .createBundle("chrome://stackatotools/locale/stackato.properties");
    try {
        parent.hPrefWindow.onpageload();
    } catch(ex) {
        dump(ex + "\n");
    }
}

function locateStackato() {
    var stackatoPath = widgets.stackatoLocation.value;
    var defaultDir = null;
    var baseName = "stackato";
    if (stackatoPath) {
        defaultDir = osPathSvc.dirname(stackatoPath);
    } else if (!isWindows) {
        var path = osPathSvc.joinlist(3, [top.opener.ko.window.getHomeDirectory(), ".local", "bin"]);
        if (osPathSvc.exists(path) && osPathSvc.exists(osPathSvc.join(path, baseName))) {
            defaultDir = path;
            stackatoPath = osPathSvc.join(path, baseName);
        }
    }
    var prompt = bundle.formatStringFromName("Where is X", [baseName], 1);
    var res = ko.filepicker.browseForExeFile(defaultDir, stackatoPath, prompt);
    if (res) {
        widgets.stackatoLocation.value = res;
    }
}
