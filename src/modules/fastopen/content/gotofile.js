/* Copyright (c) 2009 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

/* "Go To File" dialog for quickly opening a file. */

//---- globals

var log = ko.logging.getLogger("gotofile");

var gWidgets = null;
var gUIDriver = null;  // FastOpenUIDriver instance (implements koIFastOpenUIDriver)
var gSession = null;   // koIFastOpenSession
var gSep = null;       // path separator for this platform
var gOsPath = null;

var _gCurrQuery = null; // the query string last used to search


//---- routines called by dialog

function onLoad()
{
    try {
        gWidgets = {
            query: document.getElementById("query"),
            throbber: document.getElementById("throbber"),
            results: document.getElementById("results"),
            statusbarPath: document.getElementById("statusbar-path")
        }
        
        var osSvc = Components.classes["@activestate.com/koOs;1"]
            .getService(Components.interfaces.koIOs);
        gSep = osSvc.sep;
        gOsPath = Components.classes["@activestate.com/koOsPath;1"]
            .getService(Components.interfaces.koIOsPath);
        
        var foSvc = Components.classes["@activestate.com/koFastOpenService;1"]
            .getService(Components.interfaces.koIFastOpenService);
        gSession = foSvc.getSession(new FastOpenUIDriver());
        
        // Configure the session.
        var partSvc = Components.classes["@activestate.com/koPartService;1"]
                .getService(Components.interfaces.koIPartService);
        gSession.setCurrProject(partSvc.currentProject);
        var openViews = [];
        var hist = opener.ko.views.manager.topView.viewhistory;
        //hist._debug_recentViews();
        for (view in hist.genRecentViews()) {
            openViews.push(view);
        }
        gSession.setOpenViews(openViews.length, openViews);
        gSession.setCurrHistorySession(opener.ko.history.curr_session_name());

        gWidgets.query.focus();
        findFiles(gWidgets.query.value);
    } catch(ex) {
        log.exception(ex, "error loading gotofile dialog");
    }
    window.getAttention();
}

function onUnload()
{
    try {
        if (gSession) {
            gSession.abortSearch();
        }
    } catch(ex) {
        log.exception(ex, "error unloading gotofile dialog");
    }
}
 

function handleDblClick() {
    if (_openSelectedHits()) {
        window.close();
    }
}


function handleWindowKeyPress(event) {
    if (event.keyCode == KeyEvent.DOM_VK_ENTER
        || event.keyCode == KeyEvent.DOM_VK_RETURN)
    {
        _handleEnter();
    } else if (event.keyCode == KeyEvent.DOM_VK_ESCAPE) {
        window.close();
    }
    //TODO: Cmd+W / Ctrl+W: see Todd's code for plat determination
}


var _gIgnoreNextFindFiles = false;
function handleQueryKeyPress(event) {
    var index;
    var keyCode = event.keyCode;
    if (keyCode == KeyEvent.DOM_VK_ENTER
        || keyCode == KeyEvent.DOM_VK_RETURN)
    {
        _handleEnter();
    } else if (keyCode == KeyEvent.DOM_VK_UP && event.shiftKey) {
        index = gWidgets.results.currentIndex - 1;
        if (index >= 0) {
            _extendSelectTreeRow(gWidgets.results, index);
        }
        event.preventDefault();
    } else if (keyCode == KeyEvent.DOM_VK_DOWN && event.shiftKey) {
        index = gWidgets.results.currentIndex + 1;
        if (index < 0) {
            index = 0;
        }
        if (index < gWidgets.results.view.rowCount) {
            _extendSelectTreeRow(gWidgets.results, index);
        }
        event.preventDefault();
    } else if (keyCode == KeyEvent.DOM_VK_TAB && event.shiftKey) {
        _completeSelectionOrMove(false, true);
        event.preventDefault();
    } else if (keyCode == KeyEvent.DOM_VK_TAB) {
        _completeSelectionOrMove(true, true);
        event.preventDefault();
    } else if (keyCode == KeyEvent.DOM_VK_UP
            /* Ctrl+p for Emacs-y people. */
            || (event.ctrlKey && event.charCode === 112)) {
        index = gWidgets.results.currentIndex - 1;
        if (index >= 0) {
            _selectTreeRow(gWidgets.results, index);
        }
        event.preventDefault();
    } else if (keyCode == KeyEvent.DOM_VK_DOWN
            /* Ctrl+n for Emacs-y people. */
            || (event.ctrlKey && event.charCode === 110)) {
        index = gWidgets.results.currentIndex + 1;
        if (index < 0) {
            index = 0;
        }
        if (index < gWidgets.results.view.rowCount) {
            _selectTreeRow(gWidgets.results, index);
        }
        event.preventDefault();
    }
    //TODO: page up/down
}

function findFiles(query) {
    if (_gIgnoreNextFindFiles) {
        _gIgnoreNextFindFiles = false;
    } else {
        _gCurrQuery = query;
        gSession.findFiles(query);
    }
}




//---- UI driver class

function FastOpenUIDriver() {
}
FastOpenUIDriver.prototype.constructor = FastOpenUIDriver;

FastOpenUIDriver.prototype.QueryInterface = function (iid) {
    if (!iid.equals(Components.interfaces.koIFastOpenUIDriver) &&
        !iid.equals(Components.interfaces.nsISupports)) {
        throw Components.results.NS_ERROR_NO_INTERFACE;
    }
    return this;
}

FastOpenUIDriver.prototype.setTreeView = function(view) {
    gWidgets.results.treeBoxObject.view = view;
}


FastOpenUIDriver.prototype.setCurrPath = function(path) {
    gWidgets.statusbarPath.label = path;
}

FastOpenUIDriver.prototype.searchStarted = function() {
    _startThrobber();
}
FastOpenUIDriver.prototype.searchAborted = function() {
    if (window.document) {
        _stopThrobber();
    }
}
FastOpenUIDriver.prototype.searchCompleted = function() {
    if (window.document) {
        _stopThrobber();
    }
}



//---- internal support routines

function _startThrobber() {
    gWidgets.throbber.setAttribute("busy", "true");
}

function _stopThrobber() {
    gWidgets.throbber.removeAttribute("busy");
}

function _extendSelectTreeRow(tree, index) {
    tree.view.selection.rangedSelect(index, index, true);
    tree.treeBoxObject.ensureRowIsVisible(index);
}

function _selectTreeRow(tree, index) {
    tree.view.selection.select(index);
    tree.treeBoxObject.ensureRowIsVisible(index);
}

/* Handle <Enter> (or <Return>) being pressed to use the current
 * filter/selection state.
 */
function _handleEnter() {
    if (gWidgets.query.value != _gCurrQuery) {
        // The current set of results in now invalid. Need to get the first
        // new hit, if any, from the new query.
        _gIgnoreNextFindFiles = true;  // Cancel coming `findFiles`.
        // Only wait for a few seconds (don't want to hang on this).
        var hit = gSession.findFileSync(gWidgets.query.value, 3.0);
        if (! hit) {
            // No hit - this will leave the window open.
            _gIgnoreNextFindFiles = false;
            findFiles(gWidgets.query.value);
        } else if (_openHits([hit])) {
            window.close();
        } 
    } else if (_openSelectedHits()) {
        window.close();
    }
}

/* Open the views/paths selected in the results tree.
 *
 * @returns {Boolean} True iff successfully opened/switched-to files/tabs.
 *      For example, this returns false for a selected dir -- which isn't opened
 *      but set into the query box.
 */
function _openSelectedHits() {
    return _openHits(gWidgets.results.view.getSelectedHits({}));
}

/* Open the given hits.
 *
 * @param hits {list of koIFastOpenHit} The hits to open.
 * @returns {Boolean} True iff successfully opened/switched-to files/tabs.
 *      For example, this returns false for a selected dir -- which isn't opened
 *      but set into the query box.
 */
function _openHits(hits) {
    var hit, viewType, tabGroup;
    var fileUrlsToOpen = [];
    var dirsToOpen = [];
    for (var i in hits) {
        var hit = hits[i];
        if (hit.type == "path" && hit.isdir) {
            dirsToOpen.push(hit.base);
        } else if (hit.type == "open-view") {
            hit.view.makeCurrent();
        } else {
            //TODO: For history hits could perhaps restore viewType. Would need
            // changes to the back end for that.
            fileUrlsToOpen.push(ko.uriparse.pathToURI(hit.path));
        }
    }
    if (fileUrlsToOpen.length) {
        opener.ko.open.multipleURIs(fileUrlsToOpen);
    } else if (dirsToOpen.length) {
        // Selecting a dir should just enter that dir into the filter box.
        gWidgets.query.value = gOsPath.join(
            gOsPath.dirname(gWidgets.query.value), dirsToOpen[0]) + gSep;
        findFiles(gWidgets.query.value);
        return false;
    }
    return true;
}


/* Complete the currently selected item in the results tree.
 * This is typically hooked up to <Tab>. Its main usefulness is in descending
 * into the currently matching directory in path mode.
 *
 * If zero or more than one items are selected in the results tree, then
 * this is no-op.
 *
 * @param moveForward {Boolean} Whether to move forward in the list. I.e. if
 *      this is false, then move backwards.
 * @param allowAdvance {Boolean} Whether to allow advancing.
 */
function _completeSelectionOrMove(moveForward, allowAdvance) {
    var hits = gWidgets.results.view.getSelectedHits(new Object());
    if (hits.length != 1) {
        return null;
    }
    var hit = hits[0];
    
    // Determine the new value to which to complete.
    var currValue = gWidgets.query.value;
    var newValue = gOsPath.join(
            gOsPath.dirname(gWidgets.query.value), hit.base);
    if (hit.isdir) {
        // Selecting a dir should just enter that dir into the filter box.
        newValue += gSep;
    }

    // If the new value we'd complete to is already the selected value then
    // advance to the next result.
    if (allowAdvance && newValue == currValue) {
        var index;
        if (moveForward) {
            index = gWidgets.results.currentIndex + 1;
            if (index < 0) {
                index = 0;
            }
            if (index < gWidgets.results.view.rowCount) {
                _selectTreeRow(gWidgets.results, index);
            }
        } else {
            index = gWidgets.results.currentIndex - 1;
            if (index >= 0) {
                _selectTreeRow(gWidgets.results, index);
            }
        }
        // `allowAdvance=false` to not jump over multiple entries with the
        // same basename (e.g. all the "Conscript" files in Komodo source tree).
        return _completeSelectionOrMove(moveForward, false);
    }

    // Set the new value. If it is a dir, then descend into it.
    gWidgets.query.value = _gCurrQuery = newValue;
    if (hit.isdir) {
        findFiles(newValue);
    }
    return null;
}



