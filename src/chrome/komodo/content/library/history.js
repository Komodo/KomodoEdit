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
 * Portions created by ActiveState Software Inc are Copyright (C) 2000-2009
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

/* UI-side handler for Komodo history functionality.
 *
 * Contents:
 * 1. Wrappers around the koHistory service
 * 2. Controller for handling the forward and back commands
 * 3. Methods to implement the controller commands.
 */

xtk.include('controller');

if (typeof(ko)=='undefined') {
    var ko = {};
}

ko.history = {};
(function() {
    
var _log = ko.logging.getLogger('history');

function HistoryController() {
    this.historySvc = Components.classes["@activestate.com/koHistoryService;1"].
                getService(Components.interfaces.koIHistoryService);
    window.controllers.appendController(this);
    window.updateCommands("history_changed");
}

HistoryController.prototype = new xtk.Controller();
HistoryController.prototype.constructor = HistoryController;
HistoryController.prototype.destructor = function() { };

HistoryController.prototype.is_cmd_historyForward_supported = function() {
    return true;
};
HistoryController.prototype.is_cmd_historyForward_enabled = function() {
    return this.historySvc.can_go_forward();
};

HistoryController.prototype.do_cmd_historyForward = function() {
    if (!this.historySvc.can_go_forward()) {
        // keybindings don't go through the is-enabled test.
        return;
    }
    ko.history.history_forward(1);
};

HistoryController.prototype.is_cmd_historyBack_supported = function() {
    return true;
};
HistoryController.prototype.is_cmd_historyBack_enabled = function() {
    return this.historySvc.can_go_back();
};

HistoryController.prototype.do_cmd_historyBack = function() {
    if (!this.historySvc.can_go_back()) {
        // keybindings don't go through the is-enabled test.
        return;
    }
    ko.history.history_back(1);
};

HistoryController.prototype.is_cmd_historyRecentLocations_supported = function() {
    return true;
};
HistoryController.prototype.is_cmd_historyRecentLocations_enabled = function() {
    return this.historySvc.have_recent_history();
};

this.init = function() {
    this._observerSvc = Components.classes["@mozilla.org/observer-service;1"].
                getService(Components.interfaces.nsIObserverService);
    this._observerSvc.addObserver(this, 'history_changed', false);
    ko.main.addWillCloseHandler(this.destroy, this);
    window.updateCommands('history_changed');
};

this.destroy = function() {
    this._observerSvc.removeObserver(this, 'history_changed', false);
};

this.observe = function(subject, topic, data) {
    // Unless otherwise specified the 'subject' is the view, and 'data'
    // arguments are expected to be empty for all notifications.
    if (topic == 'history_changed') {
        window.updateCommands('history_changed');
    }
};


/**
 * Get the current location.
 *
 * @param view {view} An optional view in which to get the current location.
 *      If not given the current view is used.
 * @returns {koILocation} or null if could not determine a current loc.
 */
function _get_curr_loc(view /* =current view */) {
    if (typeof(view) == "undefined" || view == null) {
        view = ko.views.manager.currentView;
    }
    var loc = null;
    if (!view) {
        // pass
    } else if (view.getAttribute("type") == "editor") {
        loc = _controller.historySvc.editor_loc_from_info(
            "main", // window_name XXX
            0, // multiview_id XXX
            view);
    } else {
        _log.warn("cannot get current location for '"
                  +view.getAttribute("type")+"' view: "+view);
    }
    return loc;
};


/**
 * Note the current location.
 *
 * @param view {view} An optional view in which to get the current location.
 *      If not given the current view is used.
 * @returns {koILocation} The noted location (or null if could not determine
 *      a current loc).
 */
this.note_curr_loc = function note_curr_loc(view /* = currentView */) {
    var loc = _get_curr_loc(view);
    if (!loc) {
        return null;
    }
    return _controller.historySvc.note_loc(loc);
};

/** 
 * Returns the view and line # based on the loc.
 *
 * @param loc {Location}.
 * @returns undefined
 *
 * This function might open a file asynchronously, so it invokes
 * handle_view_line_callback to do the rest of the work.
 */
function view_and_line_from_loc(loc, handle_view_line_callback, open_if_needed/*=true*/) {
    if (typeof(open_if_needed) == "undefined") open_if_needed = true;
    var uri = loc.uri;
    if (!uri) {
        _log.error("go_to_location: given empty uri");
        return null;
    }
    var lineNo = loc.line;
    
    var view = ko.windowManager.getViewForURI(uri);
    var is_already_open = (view != null);
    function local_callback(view_) {
        if (is_already_open) {
            var betterLineNo = view_.scimoz.markerLineFromHandle(loc.marker_handle);
            if (betterLineNo != -1) {
                lineNo = betterLineNo;
            }
        }
        return handle_view_line_callback(view_, lineNo);
    }
    if (!view) {
        if (!open_if_needed) {
            return handle_view_line_callback(null, lineNo);
        }
        function callback(view_) {
            if (!view_)  {
                ko.statusBar.AddMessage(
                    "Can't find file " + uri,
                    "editor", 5000, false);
                return null;
            }
            return handle_view_line_callback(view_, lineNo);
        };
        view = ko.views.manager.doFileOpenAtLineAsync(uri, lineNo,
                                                      null, // viewType='editor'
                                                      null, // viewList=null
                                                      null, // index=-1
                                                      callback);
    }
    return local_callback(view);
}

this.go_to_location = function go_to_location(loc) {
    //XXX Use window and view IDs
    var windowName = loc.windowName;
    var multiview_id = loc.multiview_id;
    var view_type = loc.view_type;
    if (view_type != "editor") {
        throw new Error("history: goto location of type " + view_type
                        + " not yet implemented.");
    }
    function _callback(view, lineNo) {
        if (!view) return;
        var scimoz = view.scimoz;
        view.makeCurrent();
        var targetPos = scimoz.positionFromLine(lineNo) + loc.col;
        scimoz.currentPos = scimoz.anchor = targetPos;
        scimoz.gotoPos(targetPos);
        window.updateCommands("history_changed");
    }
    view_and_line_from_loc(loc, _callback, true);
};

function labelFromLoc(loc) {
    var fname = null, view, lineNo;
    function _callback(view, lineNo) {
        lineNo += 1;
        var fullPath = null;
        var finalLabel;
        try {
            if (view) {
                try {
                    fname = view.document.file.leafName;
                    fullPath = view.document.displayPath;
                } catch(ex) {}
            }
            if (!fname) {
                fname = loc.uri.substr(loc.uri.lastIndexOf("/") + 1);
            }
        } catch(ex) {
            _log.exception("labelFromLoc: " + ex + "\n");
            fname = loc.uri;
        }
        var finalLabel = fname + ":" + lineNo;
        if (fullPath) {
            finalLabel += " - " + fullPath;
        }
        return finalLabel;
    }
    // This is a sync call (not async), but it's coded this way
    // so go_to_location can share common code. 
    return view_and_line_from_loc(loc, _callback, false); // don't open closed views
}

this.initPopupMenuRecentLocations = function(event) {
    try {
    var popupMenu = event.target;
    while (popupMenu.hasChildNodes()) {
        popupMenu.removeChild(popupMenu.lastChild);
    }
    var locList = {};
    var currentLocIdx = {};
    _controller.historySvc.get_recent_locs(_get_curr_loc(),
                                               currentLocIdx, locList, {});
    currentLocIdx = currentLocIdx.value;
    locList = locList.value;
    
    var menuitem, loc;
    for (var loc, i = 0; loc = locList[i]; ++i) {
        menuitem = document.createElement("menuitem");
        menuitem.setAttribute("label", labelFromLoc(loc));
        menuitem.setAttribute("index", 0);
        var handler = null;
        var delta = currentLocIdx - i;
        if (delta == 0) {
            menuitem.setAttribute("class", "history-nav-current");
            menuitem.setAttribute("type", "radio");
            handler = "event.stopPropagation()";
        } else if (delta > 0) {
            handler = ("ko.history.history_forward(" + delta + ")");
        } else {
            handler = ("ko.history.history_back(" + (-1 * delta) + ")");
        }
        menuitem.setAttribute("oncommand", handler);
        popupMenu.appendChild(menuitem);
    }
    } catch(ex) {
        _log.exception("initPopupMenuRecentLocations: " + ex);
    }
}

this.history_back = function(delta) {
    var loc = _controller.historySvc.go_back(_get_curr_loc(), delta);
    this.go_to_location(loc);
};

this.history_forward = function(delta) {
    var loc = _controller.historySvc.go_forward(_get_curr_loc(), delta);
    this.go_to_location(loc);
};

var _controller = new HistoryController();
}).apply(ko.history);

