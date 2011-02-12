/* Copyright (c) 2000-2010 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

//---- globals

var log = ko.logging.getLogger("rails");
log.setLevel(LOG_DEBUG);

var prefExecutable = null;  // path to Rails
var appInfoEx = null;
var programmingLanguage = "Ruby";
var appInfoEx = null;
var osPathSvc = null;
var widgets = {};
var gPrefset = null;

// preferences managed by this module:
// rails.location
// rails.database

function PrefRails_OnLoad()
{
    var rubyDefaultInterpreter = null;
    appInfoEx = Components.classes["@activestate.com/koAppInfoEx?app=Ruby;1"].
            createInstance(Components.interfaces.koIRubyInfoEx);
    widgets.railsLocation = document.getElementById("rails.location");
    widgets.railsDatabase = document.getElementById("rails.database");
    widgets.railsDatabasePopupMenu = document.getElementById("rails.Database.menupopup");
    widgets.conflictBox = document.getElementById("rails-ruby-conflict-box");
    widgets.conflictMessage = document.getElementById("ruby-rails-conflict-message");
    widgets.railsDBDeck = document.getElementById("railsDBDeck");
    widgets.railsVersion = document.getElementById("railsVersion");
    widgets.mysqlPath = document.getElementById("mysqlPath");
    widgets.mysqladminPath = document.getElementById("mysqladminPath");
    widgets.oraclePath = document.getElementById("oraclePath");
    widgets.postgresqlPath = document.getElementById("postgresqlPath");
    widgets.sqlite2Path = document.getElementById("sqlite2Path");
    widgets.sqlite3Path = document.getElementById("sqlite3Path");
    osPathSvc = Components.classes["@activestate.com/koOsPath;1"].getService(Components.interfaces.koIOsPath);
    try {
        initRailsPrefs();
        parent.hPrefWindow.onpageload();
    } catch(ex) {
        dump(ex + "\n");
    }
}

function initRailsPrefs() {
    var globalPrefset = parent.hPrefWindow.prefset;
}

function OnPreferencePageInitalize(prefset) {
    // Because it's an extension we need to initialize new prefs manually.
    parent.opener.ko.extensions.rails.setDefaultPreferences(prefset);
    gPrefset = prefset;
}
    
function OnPreferencePageLoading(prefset) {
    var railsPath = widgets.railsLocation.value;
    if (!railsPath) {
        var rubyDefaultInterpreter;
        try {
            rubyDefaultInterpreter = prefset.getStringPref('rubyDefaultInterpreter');
        } catch(ex) {
            rubyDefaultInterpreter = null;
        }
        if (!rubyDefaultInterpreter) {
            rubyDefaultInterpreter = appInfoEx.executablePath;
        }
        var rubyDir = osPathSvc.dirname(rubyDefaultInterpreter);
        railsPath = osPathSvc.join(rubyDir, "rails") + osPathSvc.getExtension(rubyDefaultInterpreter)
        if (osPathSvc.exists(railsPath)) {
            prefset.setStringPref('rails.Location', railsPath);
        } else {
            railsPath = null;
        }
    }
    updateRailsVersion(railsPath);
    checkRubyRailsAlignment(railsPath);
    handleRailsDBMenuPopup(widgets.railsDatabase );
}

function OnPreferencePageSelect(prefset) {
    var path = widgets.railsLocation.value;
    if (path) {
        try {
            var rubyPath = parent.hPrefWindow.contentFrames['Ruby'].contentWindow.document.getElementById('rubyDefaultInterpreter').value;
            checkRubyRailsAlignment(path, rubyPath);
        } catch(ex) {
            dump(ex + "\n");
        }
    }  else {
    }
}

function locateRails()
{
    var currentPath = widgets.railsLocation.value;
    if (currentPath) { 
        currentPath = osPathSvc.dirname(currentPath);
    }
    var path = ko.filepicker.browseForExeFile(currentPath);
    if (path) {
        widgets.railsLocation.value = path;
        updateRailsVersion(path);
        checkRubyRailsAlignment(path);
    }
}

var checkRubyRailsAlignment_id = 0;
function timeout_checkRubyRailsAlignment(railsPath) {
    if (checkRubyRailsAlignment_id) {
        clearTimeout(checkRubyRailsAlignment_id);
    }
    checkRubyRailsAlignment_id = setTimeout(checkRubyRailsAlignment, 1000, railsPath);
}
    

function browseToFile(fieldName) {
    var path = widgets[fieldName].value;
    var defaultDir, defaultPath;
    if (path) {
        defaultPath = path;
        defaultDir = osPathSvc.dirname(defaultPath);
    } else {
        defaultDir = defaultPath = null;
    }
    var idx = fieldName.indexOf("Path");
    var baseName;
    if (idx >= 0) {
        baseName = fieldName.substring(0, idx);
    } else {
        baseName = fieldName;
    }
    var prompt = "Where is " + baseName + "?";
    var res = ko.filepicker.browseForExeFile(defaultDir, defaultPath, prompt);
    if (res) {
        widgets[fieldName].value = res;
        if (fieldName.indexOf("mysql") == 0) {
            checkMysqlValues(widgets[fieldName]);
        }
    }
}

function updateRailsVersion(railsPath) {
    var railsVersion = parent.opener.ko.extensions.rails.getRailsVersion(railsPath);
    if (railsVersion) {
        widgets.railsVersion.value = railsVersion;
    } else {
        widgets.railsVersion.value = "None";
    }
}

function checkMysqlValues(textbox) {
    var id = textbox.id;
    var ids = ['mysqladminPath', 'mysqlPath'];
    var other_id = ids[1 - ids.indexOf(id)];
    var otherTextbox = widgets[other_id];
    if (otherTextbox.value.length == 0) {
        var otherBasename = other_id.substr(0, other_id.indexOf("Path"));
        var dirname = osPathSvc.dirname(textbox.value);
        var proposedVal = osPathSvc.join(dirname, otherBasename);
        if (osPathSvc.exists(proposedVal)) {
            otherTextbox.value = proposedVal;
        }
    }
}

function checkRubyRailsAlignment(railsPath, rubyPath) {
    if (typeof(rubyPath) == "undefined" || !rubyPath) {
        rubyPath = (parent.hPrefWindow.prefset.getStringPref('rubyDefaultInterpreter')
                        || appInfoEx.executablePath);
    }
    var rubyDir = osPathSvc.dirname(rubyPath);
    var railsDir = osPathSvc.dirname(railsPath);
    var conflictBox = widgets.conflictBox;
    if (railsDir != rubyDir) {
        conflictBox.removeAttribute("collapsed");
        var txtField = widgets.conflictMessage;
        while (txtField.childNodes.length > 0) {
            txtField.removeChild(txtField.childNodes[0]);
        }
        var bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
            .getService(Components.interfaces.nsIStringBundleService)
            .createBundle("chrome://railsTools/locale/rails.properties");
        var text = bundle.formatStringFromName("Warning Komodo is using the Ruby in X but Rails in Y",
                                               [rubyDir, railsDir], 2);
        txtField.appendChild(document.createTextNode(text));
    } else {
        conflictBox.setAttribute("collapsed", true);
    }
}

function handleRailsDBMenuPopup(menulist) {
    widgets.railsDBDeck.selectedIndex = menulist.selectedIndex;   
}
