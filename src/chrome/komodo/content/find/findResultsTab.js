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

if (typeof(ko) == 'undefined') {
    var ko = {};
}

if (typeof(ko.findresults)!='undefined') {
    ko.logging.getLogger('').warn("ko.findresults was already loaded, re-creating it.\n");
} else {
    ko.findresults = {};
}

/* -*- Mode: JavaScript; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 2 -*-
 *
 * Komodo's Find and Replace results tab control (a tab in the output pane)
 *
 * TODO:
 *  - try to refind results that have moved from buffer editting since search
 */

(function() {

//---- locals

var findResultsLog = ko.logging.getLogger('findResultsTab');
var nextTabId = 1;
//findResultsLog.setLevel(ko.logging.LOG_DEBUG);

if (!("managers" in this))
    this.managers = {};

this.getTab = function FindResultsTab_GetTab(callback)
{
    findResultsLog.debug("getTab()\n");
    try {
        var id = nextTabId++;
        this.create(id, callback, function(manager) {
            this.managers[id] = manager;
            callback(manager);
        }.bind(this));
    } catch(ex) {
        findResultsLog.exception(ex);
    }
    return null;
}

this.getManager = function FindResultsTab_GetManager(id)
{
    return this.managers[id];
}

// Create/uncollapse a new find results tab and return a manager object.
//
//  "id" is the unique id to use for the tab.
//
// This is called "Create" because the Find Results tabs _used_ to be
// dynamically created. Now we just have collapsed hardcoded ones because
// (1) we are limiting to two so we can and (2) dynamically creating them
// ran into the old Komodo problem of the UI not updating until the mouse
// is moved.
this.create = function _FindResultsTab_Create(id, searchAgain, callback)
{
    if (ko.prefs.getBoolean("find_in_view", false))
    {
        return this.createWithView(id, searchAgain, callback);
        return;
    }
    
    var idstr = "findresults_tabpanel" + id;
    ko.widgets.registerWidget(idstr, "Find Results", "chrome://komodo/content/find/findResultsTab.xul", {
            defaultPane: "workspace_bottom_area",
            persist: false,
            show: true,
            iconURL: "koicon://ko-svg/chrome/icomoon/skin/binoculars.svg"
        });
    
    ko.widgets.getWidgetAsync(idstr, function(widget) {
        var panel = widget.parentNode;
        var tab = panel.tab;
        
        var manager = new ko.findresults.FindResultsTabManager();
        manager.initialize(id, searchAgain);
        
        ["mousedown", "focus"].forEach(function(eventName) {
            tab.addEventListener(eventName, function() {
                panel.tab.parentNode.selectedItem = tab;
                panel.focus();
                manager.doc.getElementById("findresults").focus();
            }, false);
        });
        
        tab.addEventListener("close-tab", function(e) {
            var findSvc = Components.classes["@activestate.com/koFindService;1"].
                      getService(Components.interfaces.koIFindService);
            findSvc.stopfindreplaceinfiles(id);
            
            ko.widgets.unregisterWidget(widget);
            delete this.managers[id];
            
            e.preventDefault();
            return false;
        }.bind(this));
        
        callback(manager);
    }.bind(this));
}

this.createWithView = function _FindResultsTab_CreateWithView(id, searchAgain, callback)
{
    var view = ko.open.findResults();

    view.addEventListener("view_closed", function(e) {
        var findSvc = Components.classes["@activestate.com/koFindService;1"].
                  getService(Components.interfaces.koIFindService);
        findSvc.stopfindreplaceinfiles(id);
        
        delete this.managers[id];
        
        e.preventDefault();
        return false;
    }.bind(this));
    
    checkReadyState = function() {
        if (view.document.readyState == "complete") {
            var manager = new ko.findresults.FindResultsTabManager();
            manager.initializeWithView(id, view, searchAgain);
            callback(manager);
            return;
        }
        setTimeout(checkReadyState, 100);
    };
    checkReadyState();
}

this.FindResultsTabManager = function FindResultsTabManager() { }
this.FindResultsTabManager.prototype.constructor = this.FindResultsTabManager;

this.FindResultsTabManager.prototype.initialize = function(id, searchAgain)
{
    try {
        this.id = id; // Number identifying this FindResultsTabManager from others.
        this._searchAgain = searchAgain;
        this._isSearchingAgain = false;
        this._idprefix = "findresults"+this.id;

        // Should be called in the onload handler for the window containing the
        // find results tab XUL.
        this.view = Components.classes['@activestate.com/koFindResultsView;1']
            .createInstance(Components.interfaces.koIFindResultsView);
        if (!this.view) {
            throw new Error("couldn't create a koFindResultsView");
        }
        this.view.id = this.id;
        this.view.rootPath = "";
        
        try {
            this.view.rootPath = ko.uriparse.URIToLocalPath(ko.places.getDirectory());
        } catch (e) {}

        // since the two find results tabs share ko.findresults.*, we can't
        // depend on |window| or |document| (or other normally window-specific
        // globals) to help us distinguish which document we want.  We need
        // to go ask the containing browser instead.
        var widget = ko.widgets.getWidget("findresults_tabpanel" + id);
        this.doc = widget.contentDocument;
        this.tab = widget.parentNode.tab;
        
        // Ensure the nsITreeView instance is bound to the <tree>.
        var treeWidget = this.doc.getElementById("findresults");
        var boxObject = treeWidget.treeBoxObject
                .QueryInterface(Components.interfaces.nsITreeBoxObject);
        if (boxObject.view == null) {
            // We are in a collapsed state -- we need to force the tree to be
            // visible before we can assign the view to it.
            findResultsLog.info("manager "+this.id+" initialize(): forcing it to show");
            this.show();
        }
        boxObject.view = this.view;

        // Make sure the tab can find its own manager
        if (widget) {
            widget.contentWindow.gFindResultsTabManager = this;
        }

        this.clear();
    } catch(ex) {
        findResultsLog.exception(ex);
    }
}

this.FindResultsTabManager.prototype.initializeWithView = function(id, view, searchAgain)
{
    try {
        this.id = id; // Number identifying this FindResultsTabManager from others.
        this._searchAgain = searchAgain;
        this._isSearchingAgain = false;
        this._idprefix = "findresults"+this.id;

        // Should be called in the onload handler for the window containing the
        // find results tab XUL.
        // THIS is HORRIBLY named and should never have been called a "view" - BEWARE
        this.view = Components.classes['@activestate.com/koFindResultsView;1']
            .createInstance(Components.interfaces.koIFindResultsView);
        if (!this.view) {
            throw new Error("couldn't create a koFindResultsView");
        }
        this.view.id = this.id;
        this.view.rootPath = "";
        try {
            this.view.rootPath = ko.uriparse.URIToLocalPath(ko.places.getDirectory());
        } catch (e) {}

        // since the two find results tabs share ko.findresults.*, we can't
        // depend on |window| or |document| (or other normally window-specific
        // globals) to help us distinguish which document we want.  We need
        // to go ask the containing browser instead.
        this.doc = view.document;
        this.tab = view.parentNode._tab;

        // Ensure the nsITreeView instance is bound to the <tree>.
        var treeWidget = this.doc.getElementById("findresults");
        var boxObject = treeWidget.treeBoxObject
                .QueryInterface(Components.interfaces.nsITreeBoxObject);
        if (boxObject.view == null) {
            // We are in a collapsed state -- we need to force the tree to be
            // visible before we can assign the view to it.
            findResultsLog.info("manager "+this.id+" initialize(): forcing it to show");
            this.show();
        }
        boxObject.view = this.view;

        // Make sure the tab can find its own manager
        view.window.gFindResultsTabManager = this;

        this.clear();
    } catch(ex) {
        findResultsLog.exception(ex);
    }
}


this.FindResultsTabManager.prototype.show = function(focus /* =false */)
{
    if (typeof(focus) == "undefined" || focus == null) focus = false;

    try {
        findResultsLog.info("[manager "+this.id+"] show");

        var widget = this.doc.defaultView.frameElement;
        if (widget.getAttribute("type") == "ko-widget")
            ko.uilayout.ensureTabShown(widget, focus);

        if (focus) {
            // Give the find results tab the focus. See bug 79487 for why
            // this *isn't* the default.
            this.doc.documentElement.firstChild.focus();
        }
    } catch(ex) {
        findResultsLog.exception(ex);
    }
}


this.FindResultsTabManager.prototype.clear = function()
{
    // Clear the list of find results.
    findResultsLog.info("FindResultsTabManager.clear()");
    this._searchInProgress = null;
    this._pattern = null;
    this._patternAlias = null;
    this._repl = null;
    this.context_ = null;
    this._options = null;

    // Clear the UI.
    this.view.Clear(0);
    this._updateSortIndicators(null);
    var descWidget = this.doc.getElementById("findresults-desc");
    descWidget.setAttribute("value", "No current find/replace results.");
    descWidget.removeAttribute("baseDesc");
    descWidget.classList.remove("find-description-highlight");
    this.doc.getElementById("findresults-jumptonext-button")
            .setAttribute("disabled", "true");
    this.doc.getElementById("findresults-jumptoprev-button")
            .setAttribute("disabled", "true");
    var searchTextbox = this.doc.getElementById("findresults-filter-textbox");
    if (searchTextbox) {  // May not exist (i.e. not yet in the TODO extension).
        searchTextbox.value = "";
    }
}

this.FindResultsTabManager.prototype.searchAgain = function()
{
    var searchWidget = this.doc.getElementById('findresults-search-textbox');
    this.clear();
    this._isSearchingAgain = true;
    this._searchAgain(this, searchWidget.value);
}

this.FindResultsTabManager.prototype.updateFilter = function()
{
    findResultsLog.info("FindResultsTabManager.updateFilter()");
    var searchTextbox = this.doc.getElementById("findresults-filter-textbox");
    this.view.SetFilterText(searchTextbox.value);
}


this.FindResultsTabManager.prototype.jumpToPrevResult = function()
{
    findResultsLog.info("FindResultsTabManager.jumpToPrevResult()");
    var treeWidget = this.doc.getElementById("findresults");
    if (treeWidget.treeBoxObject.view.rowCount < 1) {
        ko.dialogs.alert("Could not find previous result because the "+
                     "find results list is empty.");
        this.show();
        return;
    }
    var i = treeWidget.currentIndex;
    var rowCount = treeWidget.treeBoxObject.view.rowCount;
    if (i == -1 || i == 0 || i >= rowCount) {
        i = rowCount - 1;
    } else {
        i -= 1;
    }
    treeWidget.treeBoxObject.view.selection.currentIndex = i;
    treeWidget.treeBoxObject.view.selection.select(i);
    treeWidget.treeBoxObject.ensureRowIsVisible(i);
    this._doubleClick();
}


this.FindResultsTabManager.prototype.jumpToNextResult = function()
{
    findResultsLog.info("FindResultsTabManager.jumpToNextResult()");
    var treeWidget = this.doc.getElementById("findresults");
    if (treeWidget.treeBoxObject.view.rowCount < 1) {
        ko.dialogs.alert("Could not find next result because the find results "+
                     "list is empty.");
        this.show();
        return;
    }
    var i = treeWidget.currentIndex;
    if (i == -1 || i >= treeWidget.treeBoxObject.view.rowCount-1) {
        i = 0;
    } else {
        i += 1;
    }
    treeWidget.treeBoxObject.view.selection.currentIndex = i;
    treeWidget.treeBoxObject.view.selection.select(i);
    treeWidget.treeBoxObject.ensureRowIsVisible(i);
    this._doubleClick();
}


this.FindResultsTabManager.prototype.copyResults = function()
{
    findResultsLog.info("FindResultsTabManager.copyResults()");
    try {
        var treeWidget = this.doc.getElementById("findresults");
        if (treeWidget.view.rowCount < 1) {
            require("notify/notify").send("No find results to copy", "searchReplace",
                                          {priority: "warning"});
            return;
        }

        var text = "";
        for (var row=0; row < treeWidget.view.rowCount; row++) {
            for (var col=0; col < treeWidget.columns.length; col++) {
                text += treeWidget.view.getCellText(row, treeWidget.columns[col]);
                if (col+1 < treeWidget.columns.length) {
                    text += ", ";
                }
            }
            text += "\n";
        }
        // Copy to the clipboard and add message it's done.
        xtk.clipboard.setText(text);
        var msg = "Copied " + row + " find result rows to the clipboard";
        require("notify/notify").send(msg, "searchReplace");
    } catch (ex) {
        findResultsLog.exception(ex);
    }
}

this.FindResultsTabManager.prototype.stopSearch = function()
{
    var findSvc = Components.classes["@activestate.com/koFindService;1"].
              getService(Components.interfaces.koIFindService);
    findSvc.stopfindreplaceinfiles(this.id);
    this.searchFinished(false);
}


this.FindResultsTabManager.prototype.undoReplace = function()
{
    // Pass off to the "Undo Replacements" dialog.
    // This dialog runs the undo and returns true (success) or false
    // (failed or aborted).
    var args = {
        "journal_id": this._journalId
    };
    ko.windowManager.openDialog(
        "chrome://komodo/content/find/undorepl.xul",
        "komodo_undo_repl",
        "chrome,modal,titlebar,resizable=yes",
        args);
    var undoButton = this.doc.getElementById("findresults-undoreplace-button");
    if (args.retval && undoButton) {
        undoButton.setAttribute("disabled", "true");
    }
}


//XXX Not implemented yet.
//this.FindResultsTabManager.prototype.redoSearch = function()
//{
//    alert('NYI redoSearch');
//}


// 'Close Tab' button not necessary with current Find Results tab policy.
//this.FindResultsTabManager.prototype.closeTab = function()
//{
//    try {
//        // Warn if the search is still in progress, offer to stop it and.
//        if (this.isBusy()) {
//            var answer = ko.dialogs.customButtons(
//                "The search is still in progress. The search must be stopped "+
//                "before the tab can be closed.",
//                ["Stop and &Close Tab", "Cancel"],
//                "Cancel",  // default button
//                null, // text
//                null, // title
//                "stop_search_before_closing_tab");
//            if (answer == "Stop and Close Tab") {
//                this.stopSearch();
//            } else { // answer == "Cancel"
//                return;
//            }
//        }
//
//        // Remove the tab's XUL.
//        var tabs = parent.document.getElementById("output_tabs");
//        var tab = parent.document.getElementById(this._idprefix+"_tab");
//        tabs.selectedItem = tab.previousSibling; // select preceding tab
//        tabs.removeChild(tab);
//        var tabpanels = parent.document.getElementById("output_tabpanels");
//        var tabpanel = parent.document.getElementById(this._idprefix+"_tabpanel");
//        tabpanels.removeChild(tabpanel);
//
//        // Reclaim the id number.
//        //XXX Have to figure out our Find Results tab policy before working
//        //    on this.
//        //delete ko.findresults.managers[this.id];
//    } catch(ex) {
//        findResultsLog.exception(ex);
//    }
//}


this.FindResultsTabManager.prototype.setDescription = function(subDesc /* =null */,
                                                          important /* =false */)
{
    if (typeof(subDesc) == "undefined") subDesc = null;
    if (typeof(important) == "undefined") important = false;

    var descWidget = this.doc.getElementById("findresults-desc");
    var baseDesc = descWidget.getAttribute("baseDesc");
    var desc;
    if (subDesc) {
        desc = subDesc + " " + baseDesc;
    } else {
        desc = baseDesc;
    }
    descWidget.setAttribute("value", desc);
    if (important) {
        descWidget.classList.add("find-description-highlight");
    } else {
        descWidget.classList.remove("find-description-highlight");
    }

    if (important) {
        var msg = "Find in Files: "+subDesc;
        require("notify/notify").send(msg, "searchReplace");
    }
}


this.FindResultsTabManager.prototype._getBaseDescription = function(tense)
{
    // Add a description of the find process.
    var baseDesc = "";
    if (tense == "present") {
        if (this._repl != null) {
            baseDesc += "Replacing ";
        } else {
            baseDesc += "Finding ";
        }
    } else if (tense == "past") {
        return "";
    } else {
        throw new Error("illegal tense value: '"+tense+"'");
    }
    if (!this._patternAlias) {
        baseDesc += this._pattern;
    } else {
        baseDesc += this._patternAlias;
    }
    if (this._repl != null) {
        baseDesc += " with '"+this._repl+"'";
    }
    if (this.context_.type == Components.interfaces.koIFindContext.FCT_IN_FILES) {
        baseDesc += " in '"+this._options.encodedFolders+"'.";
    } else {
        baseDesc += " in "+this.context_.name+".";
    }
    return baseDesc;
}


/**
 * Configure the find results tab with information about the find/replace
 * operation.
 *
 * @param {String} pattern the pattern searched for
 * @param {String} patternAlias A more user-friendly name for the
 *      pattern. Optional, null if no alias.
 * @param {String} repl the replacement pattern. Null if this is just
 *      a find operation.
 * @param context {Components.interfaces.koIFindContext} The search
 *      context for this op. (Dev Note: this is reference to a context
 *      that can change, so this isn't reliable for 'redo' operations)
 * @param options {Components.interfaces.koIFindOptions} Holds the find
 *      options. (Dev Note: this is reference to a context
 *      that can change, so this isn't reliable for 'redo' operations)
 * @param {Boolean} opSupportsUndo Indicates in this find/replace
 *      operation supports undo. Optional, default false.
 */
this.FindResultsTabManager.prototype.configure = function(
    pattern, patternAlias, repl, context, options,
    opSupportsUndo /* =false */)
{
    if (typeof(opSupportsUndo) == "undefined" || opSupportsUndo == null)
        opSupportsUndo = false;

    // Cache find data for possible use later.
    this._pattern = pattern;
    this._patternAlias = patternAlias;
    this._repl = repl;
    this.context_ = context;  //XXX Need a _clone_ of this for redo to work.
    this._options = options; // XXX Need a _clone_ of this for redo to work.
    this._opSupportsUndo = opSupportsUndo;

    // Add a description of the find process.
    var baseDesc = this._getBaseDescription("present");
    var descWidget = this.doc.getElementById("findresults-desc");
    descWidget.setAttribute("baseDesc", baseDesc);
    this.setDescription();
    
    var filterWidget = this.doc.getElementById("findresults-filter-textbox");
    filterWidget.setAttribute("collapsed", true);
    var searchWidget = this.doc.getElementById("findresults-search-textbox");
    searchWidget.value = this._pattern;
    searchWidget.setAttribute("collapsed", true);
    
    var tab = this.tab;
    
    var prefix = this._repl ? 'Replace "' : 'Find "';
    var _pattern = pattern;
    if (pattern.length > 15) _pattern = pattern.substr(0,15) + "..";
    this._patternShort = _pattern;
    tab.setAttribute("label", prefix + _pattern + '"');

    var filenameCol = this.doc.getElementById("findresults-filename");
    if (context.type == Components.interfaces.koIFindContext.FCT_CURRENT_DOC
        || context.type == Components.interfaces.koIFindContext.FCT_SELECTION)
    {
        filenameCol.setAttribute("hidden", "true"); //XXX not "collapsed"?
    } else {
        filenameCol.setAttribute("hidden", "false");
    }

    // Make the undo button available if this find/replace operation
    // supports it.
    var undoButton = this.doc.getElementById("findresults-undoreplace-button");
    if (opSupportsUndo) {
        if (undoButton) { // because "todo"-extension is piggy-backing
            if (undoButton.hasAttribute("collapsed"))
                undoButton.removeAttribute("collapsed");
            if (undoButton.hasAttribute("hidden"))
                undoButton.removeAttribute("hidden");
            undoButton.setAttribute("disabled", "true");
        }
    } else {
        if (undoButton) { // because "todo"-extension is piggy-backing
            undoButton.setAttribute("collapsed", "true");
            undoButton.setAttribute("disabled", "true");
            undoButton.setAttribute("hidden", "true");
        }
    }
}


this.FindResultsTabManager.prototype.searchStarted = function()
{
    this._searchInProgress = true;

    var icon = this.doc.getElementById("findresults-icon");
    if (icon) { // because "todo"-extension is piggy-backing
        if (icon.hasAttribute("collapsed"))
            icon.removeAttribute("collapsed");
        if (icon.hasAttribute("hidden"))
            icon.removeAttribute("hidden");
    }

    // 'Close Tab' button not necessary with current Find Results tab policy.
    //var closeButton = document.getElementById("findresults-closetab-button");
    //if (closeButton.hasAttribute("disabled"))
    //    closeButton.removeAttribute("disabled");
    this.doc.getElementById("findresults-jumptonext-button")
        .setAttribute("disabled", "true");
    this.doc.getElementById("findresults-jumptoprev-button")
        .setAttribute("disabled", "true");
    var stopButton = this.doc.getElementById("findresults-stopsearch-button");
    if (stopButton.hasAttribute("disabled"))
        stopButton.removeAttribute("disabled");
}


this.FindResultsTabManager.prototype.isBusy = function()
{
    return this._searchInProgress;
}


/**
 * Called to indicated that the search operation has completed.
 *
 * @param {Boolean} success Indicates if the find/replace was successful.
 * @param {Number} numResults The number of find/replace hits.
 *      Optional, typically only provided for a successful completion.
 * @param {Number} numFiles The number of paths in which there were hits.
 *      Optional, typically only provided for a successful completion.
 * @param {Number} numFilesSearched The number of paths searched.
 *      Optional, typically only provided for a successful completion.
 * @param {String} journalId The identifier for the journal for a
 *      "Replace All in Files" operation. This is used to support undo.
 *      Null if not applicable.
 */
this.FindResultsTabManager.prototype.searchFinished = function(
    success, numResults /* =null */, numFiles /* =null */,
    numFilesSearched /* =null */, journalId /* =null */)
{
    if (typeof(numResults) == "undefined") numResults = null;
    if (typeof(numFiles) == "undefined") numFiles = null;
    if (typeof(numFilesSearched) == "undefined") numFilesSearched = null;
    if (typeof(journalId) == "undefined") journalId = null;

    this._journalId = journalId;

    var icon = this.doc.getElementById("findresults-icon");
    if (icon) {
        icon.setAttribute("collapsed", "true");
        icon.setAttribute("hidden", "true");
    }

    this._searchInProgress = false;
    var jumpToNextButton = this.doc.getElementById("findresults-jumptonext-button");
    if (jumpToNextButton.hasAttribute("disabled"))
        jumpToNextButton.removeAttribute("disabled");
    var jumpToPrevButton = this.doc.getElementById("findresults-jumptoprev-button");
    if (jumpToPrevButton.hasAttribute("disabled"))
        jumpToPrevButton.removeAttribute("disabled");

//XXX Not implemented yet.
//    var redoButton = this.doc.getElementById("findresults-redosearch-button");
//    if (redoButton.hasAttribute("disabled"))
//        redoButton.removeAttribute("disabled");
    var stopButton = this.doc.getElementById("findresults-stopsearch-button");
    stopButton.setAttribute("disabled", "true");
    
    var filterWidget = this.doc.getElementById("findresults-filter-textbox");
    filterWidget.removeAttribute("collapsed");
    var searchWidget = this.doc.getElementById("findresults-search-textbox");
    searchWidget.removeAttribute("collapsed");
    
    if (this._isSearchingAgain)
        searchWidget.focus();

    var desc;
    if (success) {
        var baseDesc = this._getBaseDescription("past");
        var descWidget = this.doc.getElementById("findresults-desc");
        descWidget.setAttribute("baseDesc", baseDesc);
        if (this._repl != null) {
            desc = "Replaced ";
        } else {
            desc = "Found ";
        }
        desc += numResults+" occurrences";
        if (numFiles == null && numFilesSearched != null) {
            // in $numFilesSearched file(s)
            desc += " in "+numFilesSearched+" file"
            if (numFilesSearched != 1)
                desc += "s";
        } else if (numFiles != null && numFilesSearched == null) {
            // in $numFiles file(s)
            desc += " in "+numFiles+" file"
            if (numFiles != 1)
                desc += "s";
        } else if (numFiles != null /* && numFilesSearch != null */) {
            // in $numFiles of $numFilesSearch file(s)
            desc += " in "+numFiles+" of "+numFilesSearched+" file"
            if (numFilesSearched != 1)
                desc += "s";
        }
        desc += ".";
    } else {
        desc = "Search aborted.";
    }
    this.setDescription(desc, !success);

    if (this._journalId) {
        // Ensure changes *open* files get reloaded.
        ko.window.checkDiskFiles();

        if (success) {
            var undoButton = this.doc.getElementById("findresults-undoreplace-button");
            if (undoButton) { // because "todo"-extension is piggy-backing
                if (undoButton.hasAttribute("disabled"))
                    undoButton.removeAttribute("disabled");
            }
        }
    }
}


this.FindResultsTabManager.prototype.addReplaceResult = function(
    type, url, startIndex, endIndex, value, replacement, fileName,
    lineNum, columnNum, context)
{
    findResultsLog.info("FindResultsTabManager.addReplaceResult(...)");
    //XXX should raise exception if not in replace all "mode"
    this.view.AddReplaceResult(type, url, startIndex, endIndex, value,
                               replacement, fileName, lineNum,
                               columnNum, context);
    var descWidget = this.doc.getElementById("findresults-desc");
    var desc = descWidget.getAttribute("baseDesc");
    var numHits = this.view.rowCount;
    if (numHits == 1) {
        desc += " (1 replacement made";
    } else {
        desc += " (" + numHits + " replacements made";
    }
    var numUrls = this.view.GetNumUrls();
    if (numUrls == 1) {
        desc += " in 1 file)";
    } else {
        desc += " in " + numUrls + " files)";
    }
    descWidget.setAttribute("value", desc);
}


this.FindResultsTabManager.prototype.onKeyPress = function(event)
{
    findResultsLog.info("FindResultsTabManager.onKeyPress()");
    if (event.keyCode == 13) {
        this._doubleClick();
        event.stopPropagation();
        return false;
    }
    return true;
}


this.FindResultsTabManager.prototype.onClick = function(event)
{
    findResultsLog.info("FindResultsTabManager.onClick(event)");

    // c.f. mozilla/mailnews/base/resources/content/threadPane.js
    var t = event.originalTarget;

    // single-click on a column
    if (t.localName == "treecol") {
        this._columnClick(t.id);
    }

    // double-click in the tree body
    else if (event.detail == 2 && t.localName == "treechildren") {
        this._doubleClick();
    }
}


this.FindResultsTabManager.prototype._columnClick = function(columnID)
{
    this.view.Sort(columnID);
    this._updateSortIndicators(columnID);
}


this.FindResultsTabManager.prototype._doubleClick = function()
{
    // Jump to the find/replace result.
    try {
        // Open and/or switch to the appropriate file.
        var treeWidget = this.doc.getElementById("findresults");
        var i = treeWidget.currentIndex;

        var eventType = this.view.GetType(i);
        if (eventType != "hit") {
            return;
        }

        //XXX Note that "url" is the current (bad) name for the view ID, which
        //    itself is poorly represented by the display path of the file. Note
        //    that this may not translate to a valid URL if the view is untitled.
        var displayPath = this.view.GetUrl(i);
        var this_ = this;
        ko.open.displayPath(
            displayPath, "editor",
            function(view) {
                var osPathSvc = Components.classes["@activestate.com/koOsPath;1"]
                        .getService(Components.interfaces.koIOsPath);
                if (!view || !view.koDoc ||
                    !osPathSvc.samepath(view.koDoc.displayPath, displayPath))
                {
                    // File wasn't opened for whatever reason.
                    return;
                }
                var scimoz = view.scintilla.scimoz;

                // Try to find the match or replacement result. If it cannot be
                // found then just go to the start of the line where it used to be.
                // XXX Could try and be more sophisticated in the search.
                var startCharIdx = this_.view.GetStartIndex(i);
                var start = scimoz.positionAtChar(0, startCharIdx); // a *byte* offset
                var endCharIdx = this_.view.GetEndIndex(i);
                var end = scimoz.positionAtChar(0, endCharIdx); // a *byte* offset
                var value = this_.view.GetValue(i);
                var replacement = this_.view.GetReplacement(i);
                // - first try the original indices (if the file has not changed the result
                //   should still be there)
                //   XXX This *can* fluke to the wrong result if the buffer has changed.
                //       The *correct* answer would be to only attempt this_ if the buffer
                //       is identical to when the find-/replace-all was done.
                if ((replacement && scimoz.getTextRange(start, end) == replacement)
                    || scimoz.getTextRange(start, end) == value)
                {
                    findResultsLog.info("Jump To Find Result: found at the original indices ("+start+","+end+")\n");
                }
                // - next, try using the line and column number to find it again (this_ will
                //   survive basic changes in the document that do not add or remove lines)
                else {
                    var lineNum = this_.view.GetLineNum(i);
                    var columnIndex = this_.view.GetColumnNum(i);
                    var lineStartIndex = scimoz.positionFromLine(lineNum-1);
                    var possibleValue = scimoz.getTextRange(lineStartIndex+columnIndex,
                                                            lineStartIndex+columnIndex
                                                            +value.length);
                    var possibleReplacement = scimoz.getTextRange(lineStartIndex+columnIndex,
                                                                  lineStartIndex+columnIndex
                                                                  +replacement.length);
                    if (replacement && possibleReplacement == replacement) {
                        findResultsLog.info("Jump To Find Result: found replacement, '"+
                                            replacement+"', by line:col\n");
                        start = lineStartIndex+columnIndex;
                        end = lineStartIndex+columnIndex+replacement.length;
                    } else if (possibleValue == value) {
                        findResultsLog.info("Jump To Find Result: found value by line:col\n");
                        start = lineStartIndex+columnIndex;
                        end = lineStartIndex+columnIndex+value.length;
                    }

                    // - next, try searching within the current line
                    //   XXX Note, this_ bails if there is more than one possible match on
                    //       the current line. This could attempt to be more intelligent,
                    //       like perhaps selecting the match that is closest to the
                    //       original column number.
                    else {
                        var lineText = scimoz.getTextRange(lineStartIndex,
                                        scimoz.getLineEndPosition(lineNum-1));
                        var valueIndex = lineText.indexOf(value);
                        var replacementIndex = lineText.indexOf(replacement);
                        if (replacement && replacementIndex != -1
                            && lineText.lastIndexOf(replacement) == replacementIndex)
                        {
                            findResultsLog.info("Jump To Find Result: found replacement by searching in the current line\n");
                            start = lineStartIndex+replacementIndex;
                            end = lineStartIndex+replacementIndex+replacement.length;
                        } else if (valueIndex != -1
                                   && lineText.lastIndexOf(value) == valueIndex)
                        {
                            findResultsLog.info("Jump To Find Result: found value by searching in the current line\n");
                            start = lineStartIndex+valueIndex;
                            end = lineStartIndex+valueIndex+value.length;
                        }

                        // - XXX next, could try to search a couple lines above and below
                        //   but for now will just give up
                        else {
                            findResultsLog.info("Jump To Find Result: did not find it, just using current line\n");
                            //XXX This ends up on the first line if this_ line is now off
                            //    the bottom. This should instead go to the LAST line.
                            start = lineStartIndex
                            end = lineStartIndex;

                            // Let the user know about the problem on the status bar.
                            var msg = "The specified text has been moved or deleted.";
                            require("notify/notify").send(msg, "searchReplace");
                        }
                    }
                }

                // Make the modifications in a timeout to avoid unwanted horizontal
                // scroll (bug 60117).
                // XXX - This may no longer be necessary since this is using an
                //       callback from an asynchronous function (if new view).
                setTimeout(function() {
                    var scimoz_ = view.scimoz;
                    if (start > end) {
                        // bug 91224: reverse them
                        [start, end] = [end, start];
                    }
                    // bug 91224: set currentPos explicitly so following vertical cursor
                    // movement makes sense.
                    let lineStartIndex = scimoz.lineFromPosition(start);
                    scimoz.ensureVisible(lineStartIndex);
                    let lineEndIndex = scimoz.lineFromPosition(end);
                    if (lineStartIndex !== lineEndIndex) {
                        scimoz.ensureVisible(lineEndIndex);
                    }
                    scimoz_.setSel(start, end);
                    scimoz_.currentPos = start;
                    scimoz_.anchor = end;
                    scimoz_.chooseCaretX();
                    view.setFocus();
                } , 0);

                // If the invoked find result is the last visible one and there are more,
                // then scroll the list of find results by one.
                // XXX Could also scroll up if double-clicking on top visible item.
                var box = treeWidget.treeBoxObject;
                if (box.getLastVisibleRow() <= i && this_.view.rowCount > i+1) {
                    box.scrollByLines(1);
                }
            }
        );
    } catch (ex) {
        findResultsLog.exception(ex);
    }
}


this.FindResultsTabManager.prototype._updateSortIndicators = function(sortId)
{
    var sortedColumn = null;

    // set the sort indicator on the column we are sorted by
    if (sortId) {
        sortedColumn = this.doc.getElementById(sortId);
        if (sortedColumn) {
            var sortDirection = sortedColumn.getAttribute("sortDirection");
            if (sortDirection && sortDirection == "ascending") {
                sortedColumn.setAttribute("sortDirection", "descending");
            } else {
                sortedColumn.setAttribute("sortDirection", "ascending");
            }
        }
    }

    // remove the sort indicator from all the columns
    // except the one we are sorted by
    var currCol = this.doc.getElementById("findresults").firstChild.firstChild;
    while (currCol) {
        while (currCol && currCol.localName != "treecol") {
            currCol = currCol.nextSibling;
        }
        if (currCol && (currCol != sortedColumn)) {
            currCol.removeAttribute("sortDirection");
        }
        if (currCol) {
            currCol = currCol.nextSibling;
        }
    }
}


this.FindResultsTabManager.prototype.QueryInterface = function (iid) {
    if (!iid.equals(Components.interfaces.koIFindResultsTabManager) &&
        !iid.equals(Components.interfaces.nsISupports)) {
        throw Components.results.NS_ERROR_NO_INTERFACE;
    }
    return this;
}


//---- interface routines

/**
 * Get the number of the find results tab that is currently focued
 */
this._getFocusedTabNum = function()
{
    var tabName, tabId, tab, manager;
    for (tabName in this.managers)
    {
        tabId = "findresults_tabpanel" + tabName;
        widget = ko.widgets.getWidget(tabId);
        if(widget)
        {
            tab = widget.parentNode.tab;
            if (tab && tab.selected)
            {
                return tabName;
            }
        }
    }
    return null;
}


// Called to handle the "Find Next Result" command.
//
// Seeing as there may now be multiple (or zero) find results tabs there is
// a question of _which_ set of find results to use. Here is the chosen
// algorithm: if there is a "Find Results N" tab visible, then use it,
// silently do nothing.
//
this.nextResult = function FindResultsTab_NextResult()
{
    findResultsLog.info("nextResult()");
    try {
        if (! ko.uilayout.outputPaneShown())
        {
            return;
        }
        tabNumber = this._getFocusedTabNum();
        if(tabNumber)
        {
            manager = this.managers[tabNumber];
            manager.jumpToNextResult();   
        } 
    } catch(ex) {
        findResultsLog.exception(ex);
    }
}

// Called to handle the "Find Prev Result" command.
//
// Seeing as there may now be multiple (or zero) find results tabs there is
// a question of _which_ set of find results to use. Here is the chosen
// algorithm: if there is a "Find Results N" tab visible, then use it,
// silently do nothing.
//
this.prevResult = function FindResultsTab_PrevResult()
{
    findResultsLog.info("prevResult()");
    try {
        if (! ko.uilayout.outputPaneShown()) {
            return;
        }
        tabNumber = this._getFocusedTabNum();
        if(tabNumber)
        {
            manager = this.managers[tabNumber];
            manager.jumpToPrevResult();   
        } 
    } catch(ex) {
        findResultsLog.exception(ex);
    }
}


}).apply(ko.findresults);
