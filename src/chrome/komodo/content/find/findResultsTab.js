/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

/* -*- Mode: JavaScript; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 2 -*-
 *
 * Komodo's Find and Replace results tab control (a tab in the output pane)
 *
 * TODO:
 *  - try to refind results that have moved from buffer editting since search
 */

var findResultsLog = ko.logging.getLogger('findResultsTab');
//findResultsLog.setLevel(ko.logging.LOG_DEBUG);

var gFindResultsView_Bound = false; // Is the nsITreeView instance is bound to
                                    // the find results <tree>.


//---- internal utility routines

function _OptionDesc(options, pattern)
{
    var optionDesc = "";
    if (options.matchWord) {
        optionDesc += " Match whole word.";
    }
    if (options.caseSensitivity == options.FOC_SENSITIVE
        ||
         (
           options.caseSensitivity == options.FOC_SMART
           &&
           pattern.toLowerCase() != pattern
         )
       )
    {
        optionDesc += " Match case.";
    }
    return optionDesc;
}


//---- the new FindResultsTab functionality (new ones are created on the fly)
//
// Usage:
//      var manager = FindResultsTab_GetTab(1); // or 2
//      if (manager == null) {
//          // user aborted
//      }
//      manager.configure(...find info...);
//      // Use mananger.view and the manager's koIFindResultsManager
//      // interface to fill in the data. The FindSvc provides methods
//      // to do most of this...
//

// Mapping from find results tab id (1 or 2) to a tab manager instance.
// If the key's value is null the tab XUL needs to be created.
var _gFindResultsTab_managers = {1: null, 2: null};

// Return a usable (not busy, cleared) Find Results tab manager.
//
//  "preferredId" must be 1 or 2, the number of the requested tab.
//      Note that the returned tab might not be the requested one if it
//      is busy.
//
// The number of Find Results tabs is limited (here) to two. This function
// will return a working tab manager if a free one could be had. Otherwise it
// will return null. If the requested one is busy it may ask the user if it
// the other one would be fine or if the current busy operation should be
// stopped and overridden.
//
// XXX: Am I going to go to the trouble of ensuring synchronicity here? I.e.
// this "GetTab" method would have to lock out other requests for this one
// until released. Dunno.
function FindResultsTab_GetTab(preferredId)
{
    findResultsLog.debug("FindResultsTab_GetTab(preferredId="+preferredId+")\n");
    try {
        var otherId = null;
        if (preferredId == 1) {
            otherId = 2;
        } else if (preferredId == 2) {
            otherId = 1;
        } else {
            throw("Illegal Find Results tab preferredId: "+preferredId+"\n");
        }

        // Determine which find results tab will be used.
        var id, answer;
        if (_gFindResultsTab_managers[preferredId] == null) {
            id = preferredId;
        } else if (!_gFindResultsTab_managers[preferredId].isBusy()) {
            id = preferredId;
        } else if (_gFindResultsTab_managers[otherId] == null ||
                   !_gFindResultsTab_managers[otherId].isBusy()) {
            // Offer the other tab (it is free) or to stop the preferred one.
            answer = ko.dialogs.customButtons(
                "'Find Results "+preferredId+"' is busy. Would you like to use "+
                "the other find results tab, stop the current search and use "+
                "the requested tab, or cancel this operation?",
                ["Use &Other Tab",
                 "&Stop and Use Requested Tab",
                 "Cancel"],
                "Use Other Tab",  // default button
                null, // text
                null, // title
                "which_find_results_tab_to_use_when_requested_tab_busy");
            if (answer == "Use Other Tab") {
                id = otherId
            } else if (answer == "Stop and Use Requested Tab") {
                _gFindResultsTab_managers[preferredId].stopSearch()
                id = preferredId;
            } else { // answer == "Cancel"
                return null;
            }
        } else {
            // Both are busy. Offer to stop the current one.
            answer = ko.dialogs.customButtons(
                "Both Find Results tab are busy. Would you like to stop the "+
                "search in 'Find Results "+preferredId+"' and use it or cancel "+
                "this operation?",
                ["&Stop and Use Requested Tab",
                 "Cancel"],
                "Stop and Use Requested Tab",  // default button
                null, // text
                null, // title
                "which_find_results_tab_to_use_when_all_tabs_busy");
            if (answer == "Stop and Use Requested Tab") {
                _gFindResultsTab_managers[preferredId].stopSearch()
                id = preferredId;
            } else { // answer == "Cancel"
                return null;
            }
        }

        // Create the tab or clear it and return its manager.
        var manager = _gFindResultsTab_managers[id];
        if (manager == null) {
            manager = _FindResultsTab_Create(id);
            _gFindResultsTab_managers[id] = manager;
        } else {
            manager.clear();
        }
        return manager;
    } catch(ex) {
        findResultsLog.exception(ex);
    }
    return null;
}

function FindResultsTab_GetManager(id)
{
    return _gFindResultsTab_managers[id];
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
function _FindResultsTab_Create(id)
{
    if (1) { // just uncollapsed the hardcoded find results tabs
        var tab = document.getElementById("findresults"+id+"_tab");
        if (tab.hasAttribute("collapsed"))
            tab.removeAttribute("collapsed");
        // <tabbox> Ctrl+Tab handling uses the "hidden" attribute.
        if (tab.hasAttribute("hidden"))
            tab.removeAttribute("hidden");
        var tabpanel = document.getElementById("findresults"+id+"_tabpanel");
        if (tabpanel.hasAttribute("collapsed"))
            tabpanel.removeAttribute("collapsed");
    } else { // code to manually create the XUL
        // Create the new XUL.
        var tab, tabpanel, hbox, vbox, label, separator,
            tree, treecols, treecol1, treecol2, treecol3, splitter1, splitter2,
            treechildren, button0, button1, button2, button3, button4;
        var idprefix = "findresults"+id;
        // Add one of these to "output_tabs":
        //    <tab id="findresultsN_tab" label="Find Results N"
        //         onmousedown="document.getElementById('findresultsN-body').focus();"
        //         onfocus="document.getElementById('findresultsN-body').focus();"/>
        var tabs = document.getElementById("output_tabs");
        tab = document.createElement("tab");
        tab.setAttribute("id", idprefix+"_tab");
        tab.setAttribute("label", "Find Results "+id);
        tab.setAttribute("onmousedown",
                         "document.getElementById('"+idprefix+"-body').focus();");
        tab.setAttribute("onfocus",
                         "document.getElementById('"+idprefix+"-body').focus();");
        tabs.appendChild(tab);

        // Add the new <tabpanel/> to "output_tabpanels":
        var tabpanels = document.getElementById("output_tabpanels");
        //    <tabpanel id="findresultsN_tabpanel" orient="vertical" flex="1">
        tabpanel = document.createElement("tabpanel");
        tabpanel.setAttribute("id", idprefix+"_tabpanel");
        tabpanel.setAttribute("orient", "vertical");
        tabpanel.setAttribute("flex", "1");
        //        <hbox align="center">
        hbox = document.createElement("hbox");
        hbox.setAttribute("align", "center");
        //            <label id="findresultsN-desc" style="height: 15px;"
        //                   flex="1" crop="center"/>
        label = document.createElement("label");
        label.setAttribute("id", idprefix+"-desc");
        label.setAttribute("style", "height: 15px");
        label.setAttribute("flex", "1");
        label.setAttribute("crop", "center");
        //            <separator flex="1"/>
        separator = document.createElement("separator");
        separator.setAttribute("flex", "1");
        //            <button id="findresultsN-jumptonext-button"
        //                    class="list-item-down-icon button-toolbar-a"
        //                    tooltiptext="Jump To Next Result"
        //                    oncommand="mgr.jumpToNextResult();"/>
        button0 = document.createElement("button");
        button0.setAttribute("id", idprefix+"-jumptoprev-button");
        button0.setAttribute("class", "list-item-up-icon button-toolbar-a");
        button0.setAttribute("tooltiptext", "Jump To Previous Result");
        button0.setAttribute("oncommand", "FindResultsTab_GetManager("+id+").jumpToPrevResult();");
        //            <button id="findresultsN-jumptonext-button"
        //                    class="list-item-down-icon button-toolbar-a"
        //                    tooltiptext="Jump To Next Result"
        //                    oncommand="mgr.jumpToNextResult();"/>
        button1 = document.createElement("button");
        button1.setAttribute("id", idprefix+"-jumptonext-button");
        button1.setAttribute("class", "list-item-down-icon button-toolbar-a");
        button1.setAttribute("tooltiptext", "Jump To Next Result");
        button1.setAttribute("oncommand", "FindResultsTab_GetManager("+id+").jumpToNextResult();");
        //            <button id="findresultsN-stopsearch-button"
        //                    class="find-stop-icon button-toolbar-a"
        //                    tooltiptext="Stop Search"
        //                    oncommand="mgr.stopSearch();"
        //                    disabled="true"/>
        button2 = document.createElement("button");
        button2.setAttribute("id", idprefix+"-stopsearch-button");
        //XXX Want a stop-sign-type icon for this. Or could use the buttondbgStop button that we have now.
        button2.setAttribute("class", "find-stop-icon button-toolbar-a");
        button2.setAttribute("tooltiptext", "Stop Search");
        button2.setAttribute("oncommand", "FindResultsTab_GetManager("+id+").stopSearch();");
        button2.setAttribute("disabled", "true");
        //            <button id="findresultsN-redosearch-button"
        //                    class="list-item-down-icon button-toolbar-a"
        //                    tooltiptext="Redo Search"
        //                    oncommand="mgr.redoSearch();"
        //                    disabled="true"/>
        button3 = document.createElement("button");
        button3.setAttribute("id", idprefix+"-redosearch-button");
        //XXX Want a recycle-type icon for this.
        button3.setAttribute("class", "list-item-down-icon button-toolbar-a");
        button3.setAttribute("tooltiptext", "Redo Search");
        button3.setAttribute("oncommand", "FindResultsTab_GetManager("+id+").redoSearch();");
        button3.setAttribute("disabled", "true");
        // 'Close Tab' button not necessary with current Find Results tab policy.
        ////            <button id="findresultsN-close-button"
        ////                    class="small-x-icon button-toolbar-a"
        ////                    tooltiptext="Close Tab"
        ////                    oncommand="mgr.closeTab();"
        ////                    disabled="true"/>
        //button4 = document.createElement("button");
        //button4.setAttribute("id", idprefix+"-closetab-button");
        //button4.setAttribute("class", "small-x-icon button-toolbar-a");
        //button4.setAttribute("tooltiptext", "Close Tab");
        //button4.setAttribute("oncommand", "FindResultsTab_GetManager("+id+").closeTab();");
        //button4.setAttribute("disabled", "true");
        //        </hbox>
        hbox.appendChild(label);
        hbox.appendChild(separator);
        hbox.appendChild(button0);
        hbox.appendChild(button1);
        hbox.appendChild(button2);
        hbox.appendChild(button3);
        //        <tree id="findresultsN" flex="1"
        //              seltype="single"
        //              onclick="mgr.onClick(event);"
        //              onkeypress="return mgr.onKeyPress(event);"
        tree = document.createElement("tree");
        tree.setAttribute("id", idprefix);
        tree.setAttribute("flex", "1");
        tree.setAttribute("seltype", "single");
        tree.setAttribute("onclick", "FindResultsTab_GetManager("+id+").onClick(event);");
        tree.setAttribute("onkeypress", "return FindResultsTab_GetManager("+id+").onKeyPress(event);");
        //            <treecols>
        treecols = document.createElement("treecols");
        //                <treecol primary="true"
        //                         id="findresults-filename"
        //                         label="File" flex="6"
        //                         persist="width"
        //                         crop="left"/>
        treecol1 = document.createElement("treecol");
        treecol1.setAttribute("primary", "true");
        //treecol1.setAttribute("id", "findresults-filename");
        treecol1.setAttribute("id", idprefix+"-filename");
        treecol1.setAttribute("label", "File");
        treecol1.setAttribute("flex", "6");
        treecol1.setAttribute("persist", "width");
        treecol1.setAttribute("crop", "left");
        //                <splitter class="tree-splitter"/>
        splitter1 = document.createElement("splitter");
        splitter1.setAttribute("class", "tree-splitter");
        //                <treecol id="findresults-linenum"
        //                         label="Line" align="right"
        //                         persist="width"
        //                         style="width: 4em;"/>
        treecol2 = document.createElement("treecol");
        //treecol2.setAttribute("id", "findresults-linenum");
        treecol2.setAttribute("id", idprefix+"-linenum");
        treecol2.setAttribute("label", "Line");
        treecol2.setAttribute("align", "right");
        treecol2.setAttribute("persist", "width");
        treecol2.setAttribute("style", "width: 4em;");
        //                <splitter class="tree-splitter"/>
        splitter2 = document.createElement("splitter");
        splitter2.setAttribute("class", "tree-splitter");
        //                <treecol id="findresults-context"
        //                         persist="width"
        //                         label="Content" flex="12"/>
        treecol3 = document.createElement("treecol");
        //treecol3.setAttribute("id", "findresults-context");
        treecol3.setAttribute("id", idprefix+"-context");
        treecol3.setAttribute("label", "Content");
        treecol3.setAttribute("flex", "12");
        treecol3.setAttribute("persist", "width");
        //            </treecols>
        treecols.appendChild(treecol1);
        treecols.appendChild(splitter1);
        treecols.appendChild(treecol2);
        treecols.appendChild(splitter2);
        treecols.appendChild(treecol3);
        //            <treechildren id="findresultsN-body" flex="1"/>
        treechildren = document.createElement("treechildren");
        treechildren.setAttribute("id", idprefix+"-body");
        treechildren.setAttribute("flex", "1");
        //        </tree>
        tree.appendChild(treecols);
        tree.appendChild(treechildren);
        //    </tabpanel>
        tabpanel.appendChild(hbox);
        tabpanel.appendChild(tree);
        tabpanels.appendChild(tabpanel);
    }

    var manager = new FindResultsTabManager();
    manager.initialize(id);
    return manager;
}


function FindResultsTabManager() { }
FindResultsTabManager.prototype.constructor = FindResultsTabManager;

FindResultsTabManager.prototype.initialize = function(id)
{
    try {
        this.id = id; // Number identifying this FindResultsTabManager from others.
        this._idprefix = "findresults"+this.id;

        // Should be called in the onload handler for the window containing the
        // find results tab XUL.
        this.view = Components.classes['@activestate.com/koFindResultsView;1']
            .createInstance(Components.interfaces.koIFindResultsView);
        if (!this.view) {
            throw("couldn't create a koFindResultsView");
        }
        this.view.id = this.id;

        // Ensure the nsITreeView instance is bound to the <tree>.
        var treeWidget = document.getElementById(this._idprefix);
        var boxObject = treeWidget.treeBoxObject
                .QueryInterface(Components.interfaces.nsITreeBoxObject);
        if (boxObject.view == null) {
            // We are in a collapsed state -- we need to force the tree to be
            // visible before we can assign the view to it.
            findResultsLog.info("manager "+this.id+" initialize(): forcing it to show");
            this.show();
        }
        boxObject.view = this.view;

        this.clear();
    } catch(ex) {
        findResultsLog.exception(ex);
    }
}


FindResultsTabManager.prototype.show = function()
{
    try {
        findResultsLog.info("[manager "+this.id+"] show");

        // If necessary, open output pane in komodo.xul
        ko.uilayout.ensureOutputPaneShown(window);

        // switch to proper tab
        var tabsWidget = document.getElementById("output_tabs");
        var tabWidget = document.getElementById(this._idprefix+"_tab");
        tabsWidget.selectedItem = tabWidget;

        // (controversial?) give the find results tab the focus
        //XXX This does not work because the input buffer is passing focus back
        //    to the editor.
        var findResultsWidget = document.getElementById(this._idprefix+"-body");
        findResultsWidget.focus();
    } catch(ex) {
        findResultsLog.exception(ex);
    }
}


FindResultsTabManager.prototype.clear = function()
{
    // Clear the list of find results.
    findResultsLog.info("FindResultsTabManager.clear()");
    this._searchInProgress = null;
    this._pattern = null;
    this._patternAlias = null;
    this._replacement = null;
    this.context_ = null;
    this._options = null;

    // Clear the UI.
    this.view.Clear(0);
    this._updateSortIndicators(null);
    var descWidget = document.getElementById(this._idprefix+"-desc");
    descWidget.setAttribute("value", "No current find/replace results.");
    descWidget.removeAttribute("baseDesc");
    descWidget.style.setProperty("color", "black", "");
    document.getElementById(this._idprefix+"-jumptonext-button")
            .setAttribute("disabled", "true");
    document.getElementById(this._idprefix+"-jumptoprev-button")
            .setAttribute("disabled", "true");
}


FindResultsTabManager.prototype.jumpToPrevResult = function()
{
    findResultsLog.info("FindResultsTabManager.jumpToPrevResult()");
    var treeWidget = document.getElementById(this._idprefix);
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


FindResultsTabManager.prototype.jumpToNextResult = function()
{
    findResultsLog.info("FindResultsTabManager.jumpToNextResult()");
    var treeWidget = document.getElementById(this._idprefix);
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


FindResultsTabManager.prototype.stopSearch = function()
{
    var findSvc = Components.classes["@activestate.com/koFindService;1"].
              getService(Components.interfaces.koIFindService);
    findSvc.stopfindallinfiles(this.id);
    this.searchFinished(false);
}


//XXX Not implemented yet.
//FindResultsTabManager.prototype.redoSearch = function()
//{
//    alert('NYI redoSearch');
//}


// 'Close Tab' button not necessary with current Find Results tab policy.
//FindResultsTabManager.prototype.closeTab = function()
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
//        var tabs = document.getElementById("output_tabs");
//        var tab = document.getElementById(this._idprefix+"_tab");
//        tabs.selectedItem = tab.previousSibling; // select preceding tab
//        tabs.removeChild(tab);
//        var tabpanels = document.getElementById("output_tabpanels");
//        var tabpanel = document.getElementById(this._idprefix+"_tabpanel");
//        tabpanels.removeChild(tabpanel);
//
//        // Reclaim the id number.
//        //XXX Have to figure out our Find Results tab policy before working
//        //    on this.
//        //delete _gFindResultsTab_managers[this.id];
//    } catch(ex) {
//        findResultsLog.exception(ex);
//    }
//}


FindResultsTabManager.prototype.setDescription = function(subDesc /* =null */,
                                                          important /* =false */)
{
    if (typeof(subDesc) == "undefined") subDesc = null;
    if (typeof(important) == "undefined") important = false;

    var descWidget = document.getElementById(this._idprefix+"-desc");
    var baseDesc = descWidget.getAttribute("baseDesc");
    var desc;
    if (subDesc) {
        desc = subDesc + " (" + baseDesc + ")";
    } else {
        desc = baseDesc;
    }
    descWidget.setAttribute("value", desc);
    if (important) {
        descWidget.style.setProperty("color", "#bb0000", ""); // dark red to not appear "neon" against grey.
    } else {
        descWidget.style.setProperty("color", "black", "");
    }

    if (important) {
        var msg = "Find in Files: "+subDesc;
        ko.statusBar.AddMessage(msg, "find_in_files", 3000, 1);
    }
}


FindResultsTabManager.prototype._getBaseDescription = function(tense)
{
    // Add a description of the find process.
    var baseDesc = "";
    if (tense == "present") {
        if (this._replacement != null) {
            baseDesc += "Replacing all ";
        } else {
            baseDesc += "Finding all ";
        }
    } else if (tense == "past") {
        if (this._replacement != null) {
            baseDesc += "Replaced all ";
        } else {
            baseDesc += "Found all ";
        }
    } else {
        throw("illegal tense value: '"+tense+"'");
    }
    if (!this._patternAlias) {
        baseDesc += "occurrences of '" + this._pattern + "'";
    } else {
        baseDesc += this._patternAlias;
    }
    if (this._replacement != null) {
        baseDesc += " with '"+this._replacement+"'";
    }
    if (this.context_.type == Components.interfaces.koIFindContext.FCT_IN_FILES) {
        if (!this._options.encodedIncludeFiletypes
            && !this._options.encodedExcludeFiletypes) {
            baseDesc += " in all files in '"+this._options.encodedFolders+"'.";
        } else if (!this._options.encodedExcludeFiletypes) {
            baseDesc += " in all '"+this._options.encodedIncludeFiletypes+
                        "' files in '"+this._options.encodedFolders+"'.";
        } else if (!this._options.encodedIncludeFiletypes) {
            baseDesc += " in all files except '"+
                        this._options.encodedExcludeFiletypes+
                        "' files in '"+this._options.encodedFolders+"'.";
        } else {
            baseDesc += " in all '"+this._options.encodedIncludeFiletypes+
                        "' files except '"+this._options.encodedExcludeFiletypes+
                        "' files in '"+this._options.encodedFolders+"'.";
        }
    } else {
        baseDesc += " in "+this.context_.name+".";
    }
    baseDesc += _OptionDesc(this._options, this._pattern);
    return baseDesc;
}


FindResultsTabManager.prototype.configure = function(
    pattern, patternAlias, replacement, context, options)
{
    // Cache find data for possible use later.
    this._pattern = pattern;
    this._patternAlias = patternAlias;
    this._replacement = replacement;
    this.context_ = context;  //XXX Need a _clone_ of this for redo to work.
    this._options = options; // XXX Need a _clone_ of this for redo to work.

    // Add a description of the find process.
    var baseDesc = this._getBaseDescription("present");
    var descWidget = document.getElementById(this._idprefix+"-desc");
    descWidget.setAttribute("baseDesc", baseDesc);
    this.setDescription();

    var filenameCol = document.getElementById(this._idprefix+"-filename");
    if (context.type == Components.interfaces.koIFindContext.FCT_CURRENT_DOC
        || context.type == Components.interfaces.koIFindContext.FCT_SELECTION)
    {
        filenameCol.setAttribute("hidden", "true"); //XXX not "collapsed"?
    } else {
        filenameCol.setAttribute("hidden", "false");
    }
}


FindResultsTabManager.prototype.searchStarted = function()
{
    this._searchInProgress = true;
    // 'Close Tab' button not necessary with current Find Results tab policy.
    //var closeButton = document.getElementById(this._idprefix+"-closetab-button");
    //if (closeButton.hasAttribute("disabled"))
    //    closeButton.removeAttribute("disabled");
    document.getElementById(this._idprefix+"-jumptonext-button")
        .setAttribute("disabled", "true");
    document.getElementById(this._idprefix+"-jumptoprev-button")
        .setAttribute("disabled", "true");
    var stopButton = document.getElementById(this._idprefix+"-stopsearch-button");
    if (stopButton.hasAttribute("disabled"))
        stopButton.removeAttribute("disabled");
}


FindResultsTabManager.prototype.isBusy = function()
{
    return this._searchInProgress;
}


FindResultsTabManager.prototype.searchFinished = function(
    success, numResults /* =null */, numFiles /* =null */,
    numFilesSearched /* =null */)
{
    if (typeof(numResults) == "undefined") numResults = null;
    if (typeof(numFiles) == "undefined") numFiles = null;
    if (typeof(numFilesSearched) == "undefined") numFilesSearched = null;

    this._searchInProgress = false;
    var jumpToNextButton = document.getElementById(this._idprefix+"-jumptonext-button");
    if (jumpToNextButton.hasAttribute("disabled"))
        jumpToNextButton.removeAttribute("disabled");
    var jumpToPrevButton = document.getElementById(this._idprefix+"-jumptoprev-button");
    if (jumpToPrevButton.hasAttribute("disabled"))
        jumpToPrevButton.removeAttribute("disabled");

//XXX Not implemented yet.
//    var redoButton = document.getElementById(this._idprefix+"-redosearch-button");
//    if (redoButton.hasAttribute("disabled"))
//        redoButton.removeAttribute("disabled");
    var stopButton = document.getElementById(this._idprefix+"-stopsearch-button");
    stopButton.setAttribute("disabled", "true");

    var desc;
    if (success) {
        var baseDesc = this._getBaseDescription("past");
        var descWidget = document.getElementById(this._idprefix+"-desc");
        descWidget.setAttribute("baseDesc", baseDesc);
        desc = "Found "+numResults+" occurrences";
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
}


FindResultsTabManager.prototype.addReplaceResult = function(
    url, startIndex, endIndex, value, replacement, fileName, lineNum,
    columnNum, context)
{
    findResultsLog.info("FindResultsTabManager.addReplaceResult(...)");
    //XXX should raise exception if not in replace all "mode"
    this.view.AddReplaceResult(url, startIndex, endIndex, value,
                               replacement, fileName, lineNum,
                               columnNum, context);
    var descWidget = document.getElementById(this._idprefix+"-desc");
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


FindResultsTabManager.prototype.onKeyPress = function(event)
{
    findResultsLog.info("FindResultsTabManager.onKeyPress()");
    if (event.keyCode == 13) {
        this._doubleClick();
        return false;
    }
    return true;
}


FindResultsTabManager.prototype.onClick = function(event)
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


FindResultsTabManager.prototype._columnClick = function(columnID)
{
    this.view.Sort(columnID);
    this._updateSortIndicators(columnID);
}


FindResultsTabManager.prototype._doubleClick = function()
{
    // Jump to the find/replace result.
    try {
        // Open and/or switch to the appropriate file.
        var treeWidget = document.getElementById(this._idprefix);
        var i = treeWidget.currentIndex;
        //XXX Note that "url" is the current (bad) name for the view ID, which
        //    itself is poorly represented by the display path of the file. Note
        //    that this may not translate to a valid URL if the view is untitled.
        var displayPath = this.view.GetUrl(i);
        try {
            var views = ko.views.manager.topView.getViews(true);
            var needopen = true;
            for (var v = 0; v < views.length; ++v) {
                if (views[v].document && views[v].document.displayPath == displayPath) {
                    views[v].makeCurrent();
                    needopen = false;
                    break;
                }
            }
            if (needopen) {
                // Fallback to open URI.
                var retval = ko.open.URI(displayPath);
                if (retval != null) { // indicates success opening file
                    window.setTimeout(function(me){ me._doubleClick(); }, 1, this);
                }
                return;
            }
        } catch(ex) {
            var msg = "Error opening '"+displayPath+"'.";
            ko.dialogs.alert(msg);
            findResultsLog.exception(ex, msg);
            return;
        }
        var view = ko.views.manager.currentView;
        var scimoz = view.scintilla.scimoz;

        // Try to find the match or replacement result. If it cannot be
        // found then just go to the start of the line where it used to be.
        // XXX Could try and be more sophisticated in the search.
        var start = this.view.GetStartIndex(i);
        var end = this.view.GetEndIndex(i);
        var value = this.view.GetValue(i);
        var replacement = this.view.GetReplacement(i);
        // - first try the original indeces (if the file has not changed the result
        //   should still be there)
        //   XXX This *can* fluke to the wrong result if the buffer has changed.
        //       The *correct* answer would be to only attempt this if the buffer
        //       is identical to when the find-/replace-all was done.
        if ((replacement && scimoz.getTextRange(start, end) == replacement)
            || scimoz.getTextRange(start, end) == value)
        {
            findResultsLog.info("Jump To Find Result: found at the original indices ("+start+","+end+")\n");
        }
        // - next, try using the line and column number to find it again (this will
        //   survive basic changes in the document that do not add or remove lines)
        else {
            var lineNum = this.view.GetLineNum(i);
            var columnIndex = this.view.GetColumnNum(i);
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
            //   XXX Note, this bails if there is more than one possible match on
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
                    //XXX This ends up on the first line if this line is now off
                    //    the bottom. This should instead go to the LAST line.
                    start = lineStartIndex
                    end = lineStartIndex;

                    // Let the user know about the problem on the status bar.
                    ko.statusBar.AddMessage(
                        "The specified text has been moved or deleted.", "find",
                        3000, true);
                }
            }
        }
        scimoz.setSel(start, end);

        // If the invoked find result is the last visible one and there are more,
        // then scroll the list of find results by one.
        // XXX Could also scroll up if double-clicking on top visible item.
        var box = treeWidget.treeBoxObject;
        if (box.getLastVisibleRow() <= i && this.view.rowCount > i+1) {
            box.scrollByLines(1);
        }
        scimoz.chooseCaretX();

        // transfer focus to the editor
        view.setFocus();
    } catch (ex) {
        log.exception(ex);
    }
}


FindResultsTabManager.prototype._updateSortIndicators = function(sortId)
{
    var sortedColumn = null;

    // set the sort indicator on the column we are sorted by
    if (sortId) {
        sortedColumn = document.getElementById(sortId);
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
    var currCol = document.getElementById(this._idprefix).firstChild.firstChild;
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


FindResultsTabManager.prototype.QueryInterface = function (iid) {
    if (!iid.equals(Components.interfaces.koIFindResultsTabManager) &&
        !iid.equals(Components.interfaces.nsISupports)) {
        throw Components.results.NS_ERROR_NO_INTERFACE;
    }
    return this;
}



//---- interface routines

function FindResultsTab_OnLoad()
{
}

// Called to handle the "Find Next Result" command.
//
// Seeing as there may now be multiple (or zero) find results tabs there is
// a question of _which_ set of find results to use. Here is the chosen
// algorithm: if there is a "Find Results N" tab visible, then use it,
// silently do nothing.
//
function FindResultsTab_NextResult()
{
    findResultsLog.info("FindResultsTab_NextResult()");
    try {
        if (! ko.uilayout.outputPaneShown()) {
            return;
        }

        var tabName, tabId, tab, manager;
        for (tabName in _gFindResultsTab_managers) {
            tabId = "findresults"+tabName+"_tab";
            tab = document.getElementById(tabId);
            if (tab && tab.selected) {
                manager = _gFindResultsTab_managers[tabName];
                manager.jumpToNextResult();
                break;
            }
        }
    } catch(ex) {
        findResultsLog.exception(ex);
    }
}

