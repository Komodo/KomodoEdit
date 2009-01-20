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

/* Komodo history handler:
 *
 * Contents:
 * 1. Wrappers around the koHistory service
 * 2. Controller for handling the goForward and goBack commands
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


this.get_current_location = function get_current_location(view /* =current view */) {
    if (typeof(view) == "undefined" || view == null) {
        view = ko.views.manager.currentView;
    }
    if (!view || !view.document) {
        _log.info("get_current_location: no view/document -- giving up");
        return null;
    }
    var loc = this.controller.historySvc.loc_from_info(
        "main", // window_name XXX
        0, // multiview_id XXX
        view);
    
    return loc;
};

this.note_curr_loc = function note_curr_loc(view /* = currentView */) {
    var loc = this.get_current_location(view);
    if (!loc) {
        return null;
    }
    return this.controller.historySvc.note_loc(loc);
};

this.go_to_location = function go_to_location(loc) {
    //XXX Use window and view IDs
    var windowName = loc.windowName;
    var multiview_id = loc.multiview_id;
    var view_type = loc.view_type;
    if (view_type != "editor") {
        throw new Error("history: goto location of type " + view_type
                        + " not yet implemented.");
    }
    var uri = loc.uri;
    var lineNo = loc.line;
    
    var view = ko.windowManager.getViewForURI(uri);
    var is_already_open = (view != null);
    if (!view) {
        view = ko.views.manager.doFileOpenAtLineAsync(uri, lineNo);
        if (!view) {
            ko.statusBar.AddMessage(
                "Can't find file " + uri,
                "editor", 5000, false);
            return;
        }
    }
    var scimoz = view.scimoz;
    if (is_already_open) {
        var betterLineNo = scimoz.markerLineFromHandle(loc.marker_handle);
        if (betterLineNo != -1) {
            lineNo = betterLineNo;
        }
    }
    view.makeCurrent();
    var targetPos = scimoz.positionFromLine(lineNo) + loc.col;
    scimoz.currentPos = scimoz.anchor = targetPos;
    scimoz.gotoPos(targetPos);
    window.updateCommands("history_changed");
};

function labelFromLoc(loc) {
    var fname, lineNo;
    try {
        fname = loc.uri.substr(loc.uri.lastIndexOf("/") + 1);
    } catch(ex) {
        _log.exception("labelFromLoc: " + ex + "\n");
        fname = loc.uri;
    }
    try {
        lineNo = ": " + (loc.line + 1); // human views are 1-based.
    } catch(ex) {
        _log.exception("labelFromLoc: trying to get line#: " + ex + "\n");
        lineNo = "";
    }
    return fname + lineNo;
}

this.initPopupMenuRecentLocations = function(event) {
    try {
    var popupMenu = event.target;
    while (popupMenu.hasChildNodes()) {
        popupMenu.removeChild(popupMenu.lastChild);
    }
    var locList = {};
    var currentLocIdx = {};
    this.controller.historySvc.get_recent_locs(this.get_current_location(),
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
    var loc = this.controller.historySvc.go_back(this.get_current_location(), delta);
    this.go_to_location(loc);
};

this.history_forward = function(delta) {
    var loc = this.controller.historySvc.go_forward(ko.history.get_current_location(), delta);
    this.go_to_location(loc);
};

this.controller = new HistoryController();
}).apply(ko.history);

