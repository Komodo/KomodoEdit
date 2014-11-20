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

// The New Plan:
//    - This module is reponsible for MRUs (examples: recent files, recent
//      projects, recent find/replace patterns).
//    - It has the smarts to tie an MRU to a koIOrderedPreference so that
//      it is serialized.
//    - It has the smarts to observe changes in relevant prefs which affect
//      the MRUs, e.g. mruProjectSize.
//      XXX IMO, This is the wrong place to do this. Ideally there would be a
//          koIMRU interface with separate implementations for the various
//          MRUs (and possibly subclassed interfaces for special behaviour).
//    - As required, other modules will call this module's MRU_* methods
//      to note changes in particular MRUs.
//    - This module will send out a "mru_changed" notification whenever an
//      MRU changes. It is up to the various UIs (e.g. File->Recent Files,
//      Getting Started) to observe this notification and act accordingly.
//

//---- globals
if (typeof(ko)=='undefined') {
    var ko = {};
}

ko.mru = {};
(function() {
    
var gMRUPrefObserver = null;
var _log = ko.logging.getLogger('ko.mru');
var _os_case_sensitive = navigator.platform.toLowerCase().substr(0, 3) != "win";

var bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
                .getService(Components.interfaces.nsIStringBundleService)
                .createBundle("chrome://komodo/locale/library.properties");
//_log.setLevel(ko.logging.LOG_DEBUG);


//---- internal support routines

function _notifyOfMRUChange(prefName)
{
    try {
        var observerSvc = Components.classes["@mozilla.org/observer-service;1"].
                    getService(Components.interfaces.nsIObserverService);
        observerSvc.notifyObservers(null, 'mru_changed', prefName);
    } catch(e) {
        // Raises exception if no observers are registered. Just ignore that.
    }
}

var pref_observer_topics = [
    'mruProjectSize',
    'mruFileSize',
    'mruTemplateSize',
];

/* Observe changes to MRUs *size* prefs matching the name "mru*Size" and trim
 * the associated "mru*List" pref if necessary.
 */
function _MRUPrefObserver()
{
    this.prefSvc = Components.classes["@activestate.com/koPrefService;1"].
                  getService(Components.interfaces.koIPrefService);
    var prefObserverService = this.prefSvc.prefs.prefObserverService;
    prefObserverService.addObserverForTopics(this,
                                             pref_observer_topics.length,
                                             pref_observer_topics,
                                             true);
};
_MRUPrefObserver.prototype.destroy = function()
{
    this.prefSvc = Components.classes["@activestate.com/koPrefService;1"].
                  getService(Components.interfaces.koIPrefService);
    var prefObserverService = this.prefSvc.prefs.prefObserverService;
    prefObserverService.removeObserverForTopics(this,
                                                pref_observer_topics.length,
                                                pref_observer_topics);
    this.prefSvc = null;
}
_MRUPrefObserver.prototype.observe = function(prefSet, sizePrefName, data)
{
    // Adjust the size of MRUs if the size preference for that MRU changes.
    _log.info("observed pref '" + sizePrefName);
    var listPrefName = sizePrefName.replace("Size", "List");
    var mruList = null;
    if (this.prefSvc.prefs.hasPref(listPrefName)) {
        mruList = this.prefSvc.prefs.getPref(listPrefName);
    }
    if (mruList) {
        // Chop the list to the correct size.
        var maxEntries = ko.mru.maxEntries(listPrefName);
        while (mruList.length > maxEntries) {
            mruList.deletePref(mruList.length - 1);
        }
        _notifyOfMRUChange(listPrefName);
    }
};


//---- public methods

this.initialize = function MRU_initialize()
{
    _log.info("initialize()");
    gMRUPrefObserver = new _MRUPrefObserver();
    ko.main.addWillCloseHandler(ko.mru.finalize);
}


this.finalize = function MRU_finalize()
{
    _log.info("finalize()");
    gMRUPrefObserver.destroy();
    gMRUPrefObserver = null;
}


this.maxEntries = function MRU_maxEntries(listPrefName)
{
    _log.info("maxEntries(listPrefName="+listPrefName+")");
    // XXX:HACK This should be an attribute on difference instances of a
    //          koIMRU interface.
    var maxEntries = 50; // Bigger?
    var prefSvc = Components.classes["@activestate.com/koPrefService;1"].
                  getService(Components.interfaces.koIPrefService);
    if (listPrefName.slice(0, 3) == "mru"
        && listPrefName.slice(-4) == "List")
    {
        var sizePrefName = listPrefName.replace("List", "Size");
        maxEntries = prefSvc.prefs.getLong(sizePrefName, maxEntries);
    }
    return maxEntries;
}


this.add = function MRU_add(prefName, entry, caseSensitive)
{
    _log.info("MRU_add(prefName="+prefName+", entry="+entry+
                ", caseSensitive="+caseSensitive+")");

    // Add the given "entry" (a string) to the given MRU (indentified by
    // the name of pref, "prefName", with which it is associated).
    // "caseSensitive" is a boolean indicating how to match "entry" with
    // existing MRU entries.
    var prefSvc = Components.classes["@activestate.com/koPrefService;1"].
                  getService(Components.interfaces.koIPrefService);

    // Validate arguments.
    var errmsg;
    if (!prefName) {
        errmsg = "MRU_add: invalid argument: prefName='"+prefName+"'";
        _log.error(errmsg);
        throw(errmsg);
    }
    if (!entry) {
        errmsg = "MRU_add: warning: no entry: prefName='"+prefName+
                 "', entry='"+entry+"'";
        _log.warn(errmsg)
    }

    var mruList = null;
    if (prefSvc.prefs.hasPref(prefName)) {
        mruList = prefSvc.prefs.getPref(prefName);
    } else {
        // Create a preference-set with this name.
        mruList = Components.classes["@activestate.com/koOrderedPreference;1"]
                  .createInstance();
        mruList.id = prefName;
        // Add the MRU list to the global preference set.
        prefSvc.prefs.setPref(prefName, mruList);
    }

    // If the mru list already contains this entry, first remove it so
    // that it will be reinserted at the top of the list again.
    if (caseSensitive) {
        mruList.findAndDeleteStringPref(entry);
    } else {
        mruList.findAndDeleteStringPrefIgnoringCase(entry);
    }

    // Also: keep the list constrained to the correct size.
    var maxEntries = ko.mru.maxEntries(prefName);
    while (mruList.length >= maxEntries && mruList.length > 0) {
        mruList.deletePref(mruList.length - 1);
    }

    // "Push" the entry onto the mru "stack".
    if (maxEntries > 0) {
        mruList.insertStringPref(0, entry);
    }

    _notifyOfMRUChange(prefName);
}


/**
 * Remove the given "entry" (a string) from the given MRU if it exists.
 *
 * @param {string} prefName  The mru preference with which it is associated.
 * @param {string} entry  The entry to remove from the mru.
 * @param {boolean} caseSensitive  How to match the entry.
 */
this.remove = function MRU_remove(prefName, entry, caseSensitive)
{
    _log.info("MRU_remove(prefName="+prefName+", entry="+entry+
                ", caseSensitive="+caseSensitive+")");

    // Validate arguments.
    var errmsg;
    if (!prefName) {
        errmsg = "MRU_add: invalid argument: prefName='"+prefName+"'";
        _log.error(errmsg);
        throw(errmsg);
    }
    if (!entry) {
        errmsg = "MRU_add: warning: no entry: prefName='"+prefName+
                 "', entry='"+entry+"'";
        _log.warn(errmsg)
    }

    var prefSvc = Components.classes["@activestate.com/koPrefService;1"].
                  getService(Components.interfaces.koIPrefService);

    if (!prefSvc.prefs.hasPref(prefName)) {
        // Nothing to remove from.
        return;
    }

    var was_deleted;
    var mruList = prefSvc.prefs.getPref(prefName);
    if (caseSensitive) {
        was_deleted = mruList.findAndDeleteStringPref(entry);
    } else {
        was_deleted = mruList.findAndDeleteStringPrefIgnoringCase(entry);
    }
    if (was_deleted) {
        _notifyOfMRUChange(prefName);
    }
}


this.addURL = function MRU_addURL(prefName, url)
{
    _log.info("MRU_addURL(prefName="+prefName+", url="+url+")");

    // Never want to add dbgp:// URLs to our MRUs.
    // XXX:HACK This should be a special case of a sub-classed implementation
    //          of koIMRU for the recent files and projects MRUs.
    if (url.indexOf("dbgp://") == 0) {
        return;
    }

    // max entries should itself come from a preference!
    ko.mru.add(prefName, url, _os_case_sensitive);
}


/**
 * Remove the given URL from the mru preference (if it exists).
 *
 * @param {string} prefName  The mru preference with which it is associated.
 * @param {string} url  The URL to remove from the mru.
 */
this.removeURL = function MRU_removeURL(prefName, url)
{
    _log.info("MRU_removeURL(prefName="+prefName+", url="+url+")");

    this.remove(prefName, url, _os_case_sensitive);
}


this.addFromACTextbox = function MRU_addFromACTextbox(widget)
{
    var searchType = widget.getAttribute("autocompletesearch");
    var searchParam = widget.searchParam;
    var prefName;
    var errmsg;
    switch (searchType) {
    case "mru":
        prefName = searchParam;
        if (prefName.contains("mru:")) {
            // Allow the "mru: ..." format too, bug 99395.
            prefName = ko.stringutils.getSubAttr(searchParam, "mru");
        }
        break;
    default:
        prefName = ko.stringutils.getSubAttr(searchParam, "mru");
    }
    if (!prefName) {
        errmsg = "MRU_addFromACTextbox: warning: could not determine "+
                 "pref name from search param: '"+searchParam+"'";
        _log.warn(errmsg);
        return;
    }
    if (!widget.value) {
        return;
    }

    _log.info("MRU_addFromACTextbox(widget): widget.value='"+widget.value+
                "', prefName="+prefName);
    ko.mru.add(prefName, widget.value, true);
}


this.get = function MRU_get(prefName, index /* =0 */)
{
    if (typeof(index) == "undefined" || index == null) index = 0;
    _log.info("MRU_get(prefName="+prefName+", index="+index+")");

    var prefSvc = Components.classes["@activestate.com/koPrefService;1"].
                  getService(Components.interfaces.koIPrefService);
    var retval = null;
    if (!prefSvc.prefs.hasPref(prefName)) {
        retval = "";
    } else {
        var mruList = prefSvc.prefs.getPref(prefName);
        if (index >= mruList.length) {
            retval = "";
        } else {
            retval = mruList.getStringPref(index);
        }
    }
    _log.info("Returning: " + retval);
    return retval;
}

this.del = function MRU_del(prefName, index, notify)
{
    _log.info("MRU_del(prefName="+prefName+", index="+index+")");
    if (typeof(notify) == 'undefined')
        notify = true;
    // Remove the identified entry from the MRU list.
    var prefSvc = Components.classes["@activestate.com/koPrefService;1"].
                  getService(Components.interfaces.koIPrefService);
    if (prefSvc.prefs.hasPref(prefName)) {
        var mruList = prefSvc.prefs.getPref(prefName);
        mruList.deletePref(index);
        if (notify)
            _notifyOfMRUChange(prefName);
    }
}

this.deleteValue = function MRU_deleteValue(prefName, prefValue, notify)
{
    _log.info("MRU_deleteByValue(prefName="+prefName+", prefValue="+prefValue+")");
    if (typeof(notify) == 'undefined')
        notify = true;
    // Remove the identified entry from the MRU list.
    var prefSvc = Components.classes["@activestate.com/koPrefService;1"].
                  getService(Components.interfaces.koIPrefService);
    if (prefSvc.prefs.hasPref(prefName)) {
        var mruList = prefSvc.prefs.getPref(prefName);
        var index = mruList.findStringPref(prefValue);
        if (index != -1) {
            mruList.deletePref(index);
            if (notify) {
                _notifyOfMRUChange(prefName);
            }
        }
    }
}

this.reset = function MRU_reset(prefName)
{
    _log.info("MRU_reset(prefName="+prefName+")");
    // Reset (a.k.a remove all elements) from the given MRU list.
    var prefSvc = Components.classes["@activestate.com/koPrefService;1"].
                  getService(Components.interfaces.koIPrefService);
    if (prefSvc.prefs.hasPref(prefName)) {
        var mruList = prefSvc.prefs.getPref(prefName);
        mruList.reset();
        _notifyOfMRUChange(prefName);
    }
}

/*
 * Returns an array of strings set in the given mru.
 * The order is from most recently used to least frequently used.
 * @public
 * @param {string} prefName name of the mru
 * @param {int} maxLength maximum number of entries to return, default is all.
 */
this.getAll = function MRU_getAll(prefName, maxLength /* all */)
{
    if (typeof(maxLength) == "undefined") maxLength = null;
    _log.info("MRU_get(prefName="+prefName+", maxLength="+maxLength+")");

    var prefSvc = Components.classes["@activestate.com/koPrefService;1"].
                  getService(Components.interfaces.koIPrefService);
    var retval = [];
    if (prefSvc.prefs.hasPref(prefName)) {
        var mruList = prefSvc.prefs.getPref(prefName);
        var startOffset = mruList.length - 1;
        var endOffset = -1;
        if (maxLength != null) {
            // Ensure the input is sane
            maxLength = Math.max(0, maxLength);
            // Set the endOffset so we only get a max of maxLength entries
            if (maxLength < mruList.length) {
                endOffset = (mruList.length - maxLength) - 1;
            }
        }
        for (var i=startOffset; i > endOffset; i--) {
            var entry = mruList.getStringPref(i);
            retval.push(entry);
        }
    }
    _log.info("Returning: " + retval);
    return retval;
}

this._prettyPrefNamePlural_From_PrefName = {
    mruProjectList: 'projects',
    mruFileList: 'files',
    mruTemplateList: 'templates',
    __XXZZ__: null
};

var joinWithLeader = function(osPathSvc, partList) {
    if (osPathSvc.dirname(partList[0]) != partList[0]) {
        partList = ["..."].concat(partList);
    }
    return osPathSvc.joinlist(partList.length, partList);
};

var pathDisplayers = {
  full_path: function(uri) {
        try {
            return ko.uriparse.displayPath(uri);
        } catch(ex) {
            dump("full_path failed:" + ex + "\n");
        }
        return uri;
    },
  basename: function(uri) {
        try {
            return ko.uriparse.baseName(uri);
        } catch(ex) {
            dump("basename failed:" + ex + "\n");
        }
        return uri;
    },
  parent_1: function(uri) {
        try {
            var path = ko.uriparse.displayPath(uri);
            var osPathSvc = Components.classes["@activestate.com/koOsPath;1"].getService(Components.interfaces.koIOsPath);
            var dirPart = osPathSvc.dirname(path);
            if (!dirPart || dirPart == path) return this.full_path(uri);
            return joinWithLeader(osPathSvc,
                                  [osPathSvc.basename(dirPart),
                                   osPathSvc.basename(path)]);
        } catch(ex) {
            dump("parent_1 failed:" + ex + "\n");
        }
        return uri;
    },
  parent_2: function(uri) {
        try {
            var path = ko.uriparse.displayPath(uri);
            var osPathSvc = Components.classes["@activestate.com/koOsPath;1"].getService(Components.interfaces.koIOsPath);
            var dirPart = osPathSvc.dirname(path);
            if (!dirPart || dirPart == path) return this.full_path(uri);
            var dir2Part = osPathSvc.dirname(dirPart);
            if (!dir2Part || dir2Part == dirPart) return this.parent_1(uri);
            return joinWithLeader(osPathSvc,
                                  [osPathSvc.basename(dir2Part),
                                   osPathSvc.basename(dirPart),
                                   osPathSvc.basename(path)]);
        } catch(ex) {
            dump("parent_2 failed:" + ex + "\n");
        }
        return uri;
    },
  __EOF__: null
};

this.manageMRUList = function(prefName) {
    var prettyPrefNamePlural = this._prettyPrefNamePlural_From_PrefName[prefName];
    if (!prettyPrefNamePlural) {
        prettyPrefNamePlural = prefName;
    }
    var title = bundle.formatStringFromName("Manage the X MRU List",
                                            [prettyPrefNamePlural], 1);
    var prompt = bundle.formatStringFromName("Select the X to remove from the Most-Recently-Used list",
                                            [prettyPrefNamePlural], 1);
    var items = this.getAll(prefName);
    var selectionCondition = "zero-or-more-default-none";
    var mru_project_path_display = (prefName == "mruProjectList"
                                    ? ko.prefs.getStringPref("mru_project_path_display")
                                    : "full_path");
    var stringifier = (pathDisplayers[mru_project_path_display]
                       || pathDisplayers["full_path"]);
    var projectURIs = ko.dialogs.selectFromList(title, prompt, items,
                                        selectionCondition, stringifier);
    if (projectURIs && projectURIs.length) {
        var projectsTreeView = ((ko.places && ko.places.projects)
                                ? ko.projects.manager.viewMgr.owner.projectsTreeView
                                : null);
        projectURIs.forEach(function(uri) {
            try {
                this.removeURL(prefName, uri);
                if (projectsTreeView) {
                    var part = projectsTreeView.getRowItemByURI(uri);
                    if (part) {
                        projectsTreeView.removeProject(part);
                    }
                }
            } catch(ex) {
                _log.exception(ex, "mru.js:manageMRUList: Problemo: ");
            }
        }.bind(this));
    }
}

}).apply(ko.mru);

