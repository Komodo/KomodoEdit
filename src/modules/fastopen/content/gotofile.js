/* Copyright (c) 2009 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

/* "Go To File" dialog for quickly opening a file. */

//---- globals

var log = ko.logging.getLogger("gotofile");

var gWidgets = null;
var gUIDriver = null;  // FastOpenUIDriver instance (implements koIFastOpenUIDriver)
var gSession = null;   // koIFastOpenSession



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
        
        var foSvc = Components.classes["@activestate.com/koFastOpenService;1"]
            .getService(Components.interfaces.koIFastOpenService);
        gSession = foSvc.getSession(new FastOpenUIDriver());
        
        // Configure the session.
        var partSvc = Components.classes["@activestate.com/koPartService;1"]
                .getService(Components.interfaces.koIPartService);
        gSession.project = partSvc.currentProject;
        var view = opener.ko.views.manager.currentView;
        if (view != null &&
            view.getAttribute("type") == "editor" &&
            view.document.file &&
            view.document.file.isLocal)
        {
            gSession.cwd = view.document.file.dirName;
        }
        
        gWidgets.query.focus();
        findFiles(gWidgets.query.value);
    } catch(ex) {
        log.exception(ex, "error loading gotofile dialog");
    }
    window.getAttention();
}


function handleDblClick() {
    _openSelectedPaths();
    window.close();
}


function handleWindowKeyPress(event) {
    if (event.keyCode == KeyEvent.DOM_VK_ENTER
        || event.keyCode == KeyEvent.DOM_VK_RETURN)
    {
        _openSelectedPaths();
        window.close();
    } else if (event.keyCode == KeyEvent.DOM_VK_ESCAPE) {
        window.close();
    }
    //TODO: Cmd+W / Ctrl+W: see Todd's code for plat determination
}

var _gIgnoreNextFindFiles = false;
function handleQueryKeyPress(event) {
    var index;
    if (event.keyCode == KeyEvent.DOM_VK_ENTER
        || event.keyCode == KeyEvent.DOM_VK_RETURN)
    {
        // Can't turn off <Enter> firing oncommand on the <textbox type="timed">,
        // therefore tell the handler to ignore the coming one.
        _gIgnoreNextFindFiles = true;
    } else if (event.keyCode == KeyEvent.DOM_VK_UP) {
        index = gWidgets.results.currentIndex - 1;
        if (index >= 0) {
            _selectTreeRow(gWidgets.results, index);
        }
    } else if (event.keyCode == KeyEvent.DOM_VK_DOWN) {
        index = gWidgets.results.currentIndex + 1;
        if (index < 0) {
            index = 0;
        }
        if (index < gWidgets.results.view.rowCount) {
            _selectTreeRow(gWidgets.results, index);
        }
    }
    //TODO: page up/down
}

function findFiles(query) {
    if (_gIgnoreNextFindFiles) {
        _gIgnoreNextFindFiles = false;
    } else {
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
    _stopThrobber();
}
FastOpenUIDriver.prototype.searchCompleted = function() {
    _stopThrobber();
}

/*
FastOpenUIDriver.prototype.echo = function(msg) {
    try {
        gWidgets.statusbarPath.label = "echo: " + msg;
    } catch(ex) {
        log.exception(ex);
    }
}
*/



//---- internal support routines

function _startThrobber() {
    gWidgets.throbber.setAttribute("busy", "true");
}

function _stopThrobber() {
    gWidgets.throbber.removeAttribute("busy");
}

function _selectTreeRow(tree, index) {
    tree.view.selection.select(index);
    tree.treeBoxObject.ensureRowIsVisible(index);
}

function _openSelectedPaths() {
    var paths = gWidgets.results.view.getSelectedPaths(new Object());
    for (var i in paths) {
        opener.ko.views.manager.openViewAsync("editor", paths[i]);
    }
}


