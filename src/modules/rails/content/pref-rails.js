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

//---- globals

var log = ko.logging.getLogger("rails");
log.setLevel(ko.logging.LOG_DEBUG);

var prefExecutable = null;  // path to Rails
var programmingLanguage = "Ruby";
var osPathSvc = null;
var widgets = {};
var gPrefset = null;
var rubyPrefFrame = null;

// preferences managed by this module:
// rails.location
// rails.database

function PrefRails_OnLoad()
{
    var rubyDefaultInterpreter = null;
    widgets.railsLocation = document.getElementById("rails.location");
    widgets.railsDatabase = document.getElementById("rails.database");
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
        log.exception("Error loading Rails prefs: " + ex);
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

function getCurrentRubyInterpreterPath() {
    if (!rubyPrefFrame) {
        var mainVersion = parseInt(Components.classes["@activestate.com/koInfoService;1"]
            .getService(Components.interfaces.koIInfoService)
            .version.split('.')[0]);
        if (mainVersion < 7) {
            rubyPrefFrame = "Ruby";
        } else {
            rubyPrefFrame = "chrome://komodo/content/pref/pref-ruby.xul";
        }
    }
    var contentFrames = parent.hPrefWindow.contentFrames;
    if (rubyPrefFrame in contentFrames) {
        try {
            return contentFrames[rubyPrefFrame].contentDocument.getElementById("rubyDefaultInterpreter").value;
        } catch(ex) {
            log.exception("Can't get current Ruby interpreter:" + ex);
        }
    }
    return null;
}
    
function OnPreferencePageLoading(prefset) {
    /**
     * If we don't have a Rails path coming in, it means that there's no Rails pref.
     * So look at the Ruby path to figure out where Rails should be.
     */
    var railsPath = widgets.railsLocation.value;
    var currentRubyPath;
    var rubyDir;
    var possiblePaths = [];
    if (!railsPath) {
        currentRubyPath = getCurrentRubyInterpreterPath();
        if (currentRubyPath) {
            rubyDir = ko.uriparse.dirName(currentRubyPath);
            if (rubyDir) {
                // There should be a "rails" with no extension on windows as well
                // If not, we lose some smart info, but not much
                railsPath = osPathSvc.join(rubyDir, "rails");
                if (osPathSvc.exists(railsPath)) {
                    widgets.railsLocation.value = railsPath;
                }
            }
        }
    }
    if (!railsPath) {
        var rubyDefaultInterpreter;
        try {
            rubyDefaultInterpreter = prefset.getStringPref('rubyDefaultInterpreter');
        } catch(ex) {
            rubyDefaultInterpreter = null;
        }
        if (!rubyDefaultInterpreter) {
            var appInfoEx = Components.classes["@activestate.com/koAppInfoEx?app=Ruby;1"].
                        createInstance(Components.interfaces.koIAppInfoEx);
            rubyDefaultInterpreter = appInfoEx.executablePath;
        }
        if (rubyDefaultInterpreter && rubyDefaultInterpreter != currentRubyPath) {
            rubyDir = osPathSvc.dirname(rubyDefaultInterpreter);
            railsPath = osPathSvc.join(rubyDir, "rails");
            if (osPathSvc.exists(railsPath)) {
                widgets.railsLocation.value = railsPath;
            }
        }
    }
    updateRailsVersion(railsPath);
    handleRailsDBMenuPopup(widgets.railsDatabase );
}

function locateRails()
{
    // If the Ruby location has changed, favor it.
    var startingDir;
    var currentRubyPath = getCurrentRubyInterpreterPath();
    var preferredRubyPath = gPrefset.getStringPref('rubyDefaultInterpreter');
    if (currentRubyPath && preferredRubyPath != currentRubyPath) {
        startingDir = osPathSvc.dirname(currentRubyPath);
    } else {
        var currentPath = widgets.railsLocation.value;
        if (currentPath) { 
            startingDir = osPathSvc.dirname(currentPath);
        } else if (currentRubyPath) {
            startingDir = osPathSvc.dirname(currentRubyPath);
        } else if (preferredRubyPath) {
            startingDir = osPathSvc.dirname(preferredRubyPath);
        } else {
            startingDir = null;
        }
    }
    var path = ko.filepicker.browseForExeFile(startingDir);
    if (path) {
        widgets.railsLocation.value = path;
    }
    updateRailsVersion(path);
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

function handleRailsDBMenuPopup(menulist) {
    widgets.railsDBDeck.selectedIndex = menulist.selectedIndex;   
}
