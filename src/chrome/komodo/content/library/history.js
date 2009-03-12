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

const _SKIP_DBGP_FALLBACK_LIMIT = 100;

var _curr_session_name = null; // window ID might not be available at startup
    
var _log = ko.logging.getLogger('history');

var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
    .getService(Components.interfaces.nsIStringBundleService)
    .createBundle("chrome://komodo/locale/views.properties");

var _komodoBundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
    .getService(Components.interfaces.nsIStringBundleService)
    .createBundle("chrome://komodo/locale/komodo.properties");

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
    return this.historySvc.can_go_forward(_curr_session_name);
};

HistoryController.prototype.do_cmd_historyForward = function() {
    if (!this.historySvc.can_go_forward(_curr_session_name)) {
        // keybindings don't go through the is-enabled test.
        return;
    }
    ko.history.history_forward(1);
};

HistoryController.prototype.is_cmd_historyBack_supported = function() {
    return true;
};
HistoryController.prototype.is_cmd_historyBack_enabled = function() {
    return this.historySvc.can_go_back(_curr_session_name);
};

HistoryController.prototype.do_cmd_historyBack = function() {
    if (!this.historySvc.can_go_back(_curr_session_name)) {
        // keybindings don't go through the is-enabled test.
        return;
    }
    ko.history.history_back(1);
};

HistoryController.prototype.is_cmd_historyRecentLocations_supported = function() {
    return true;
};
HistoryController.prototype.is_cmd_historyRecentLocations_enabled = function() {
    return this.historySvc.have_recent_history(_curr_session_name);
};

function _appCommandEventHandler(evt) {
    // Handle the browser-back and browser-forward application-specific
    // buttons on supported mice.  Mozilla forwards these
    // as "AppCommand" events.
    // From KD 218, referencing browser/base/content/browser.js
    switch (evt.command) {
    case "Back":
        if (_controller.historySvc.can_go_back(_curr_session_name)) {
            ko.history.history_back(1);
        }
        break;
    case "Forward":
        if (_controller.historySvc.can_go_forward(_curr_session_name)) {
            ko.history.history_forward(1);
        }
        break;
    }
};

function UnloadableDBGPLocError() {}
UnloadableDBGPLocError.prototype = new Error();

this.init = function() {
    this._observerSvc = Components.classes["@mozilla.org/observer-service;1"].
                getService(Components.interfaces.nsIObserverService);
    this._observerSvc.addObserver(this, 'history_changed', false);
    ko.main.addWillCloseHandler(this.destroy, this);
    _curr_session_name = window._koNum.toString();
    window.updateCommands('history_changed');
    window.addEventListener("AppCommand", _appCommandEventHandler, true);
    var this_ = this;
    this._handle_closing_view_setup = function(event) {
        this_._handle_closing_view(event);
    };
    window.addEventListener('view_document_detaching',
                            this._handle_closing_view_setup, false);
    window.addEventListener('view_closed',
                            this._handle_closing_view_setup, false);
};

this.destroy = function() {
    window.removeEventListener('view_document_detaching',
                               this._handle_closing_view_setup, false);
    window.removeEventListener('view_closed',
                               this._handle_closing_view_setup, false);
    this._observerSvc.removeObserver(this, 'history_changed', false);
    window.removeEventListener("AppCommand", _appCommandEventHandler, true);
};

this.observe = function(subject, topic, data) {
    // Unless otherwise specified the 'subject' is the view, and 'data'
    // arguments are expected to be empty for all notifications.
    if (topic == 'history_changed') {
        window.updateCommands('history_changed');
    }
};

this.curr_session_name = function() {
    return _curr_session_name;
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
    if (view == null) {
        return null;
    }
    var viewType = view.getAttribute("type");
    return _controller.historySvc.loc_from_view_info(
            viewType,
            window._koNum,
            view.tabbedViewId,
            view,
            (viewType == 'editor' ? view.scimoz.currentPos : -1),
            _curr_session_name);
};

const MARKNUM_HISTORYLOC = 13; // Keep in sync with content/markers.js

function _mark_pos_info(view) {
    if (!view || view.getAttribute('type') != 'editor') {
        return;
    }
    var scimoz = view.scimoz;
    if (typeof(view.pos_before_last_jump) != "undefined") {
        // Free up old marker handles
        var marker_handle = view.pos_before_last_jump.marker_handle;
        if (marker_handle != -1) {
            scimoz.markerDeleteHandle(marker_handle);
        }
    }
    var pos = scimoz.currentPos;
    var line = scimoz.lineFromPosition(pos);
    view.pos_before_last_jump = {
        // 'line' is for fallback if the marker disappears (e.g. on edit)
        line: line,
        col: pos - scimoz.positionFromLine(line), // not scimoz.getColumn(pos)
        marker_handle: scimoz.markerAdd(line, MARKNUM_HISTORYLOC)
    };
}

/**
 * Note the current location.
 *
 * @param view {view} An optional view in which to get the current location.
 *      If not given the current view is used.
 * @returns {koILocation} The noted location (or null if could not determine
 *      a current loc).
 */
this.note_curr_loc = function note_curr_loc(view, /* = currentView */
                                            check_section_change /* false */
                                            ) {
    if (typeof(view) == "undefined" || view == null) view = ko.views.manager.currentView;
    if (typeof(check_section_change) == "undefined") check_section_change = false;
    var loc = _get_curr_loc(view);
    if (!loc) {
        return null;
    }
    _mark_pos_info(view);
    if (view.getAttribute('type') != 'editor') {
        view = null;
    }
    return _controller.historySvc.note_loc(loc, check_section_change, view);
};

/** 
 * Returns the view and line # based on the loc.
 *
 * @param loc {Location}.
 * @param on_load_success {Function} -- call if view is found
 * @param on_load_failure {Function} -- call if view is not found
 * @param open_if_needed {Boolean} -- true if we're moving, false if we're building a menu.
 *
 * This function might open a file asynchronously, so it invokes
 * on_load_success to do the rest of the work.
 */
function view_and_line_from_loc(loc,
                                on_load_success,
                                on_load_failure,
                                open_if_needed/*=true*/
                                ) {
    if (typeof(open_if_needed) == "undefined") open_if_needed = true;
    var uri = loc.uri;
    if (!uri) {
        _log.error("go_to_location: given empty uri");
        return null;
    }
    var lineNo = loc.line;
    var view = ko.views.manager.getViewForURI(uri, loc.view_type);
    if (view) {
        // Check for correct tabbed view
        if (loc.tabbed_view_id != null
            && loc.tabbed_view_id != view.tabbedViewId) {
            // Try the other view
            var xulDocument = view.ownerDocument.defaultView.document;
            var multiViewContainer = xulDocument.getElementById("topview");
            var multiViewNodes = xulDocument.getAnonymousNodes(multiViewContainer)[0];
            var designatedTabbedView = (loc.tabbed_view_id == 1
                                        ? multiViewNodes.firstChild
                                        : multiViewNodes.lastChild);
            var res = designatedTabbedView.getViewsByTypeAndURI(false, 'editor', uri);
            if (res && res.length > 0) {
                view = res[0];
            }
        }
        if (loc.view_type == 'editor') {
            var betterLineNo = view.scimoz.markerLineFromHandle(loc.marker_handle);
            if (betterLineNo != -1) {
                lineNo = betterLineNo;
            }
        }
        return on_load_success(view, lineNo);
    }
    if (!view) {
        if (open_if_needed) {
            if (uri.indexOf("dbgp://") == 0) {
                // We have to throw an exception here, because if we
                // try to load the URI, it's done async, and then
                // it's harder to keep looking on failure.
                throw new UnloadableDBGPLocError("unloadable");
            }
        } else {
            return on_load_success(null, lineNo);
        }
        function post_open_callback(view_) {
            if (!view_)  {
                on_load_failure();
            } else {
                on_load_success(view_, lineNo);
            }
        };
        var viewList = (loc.tabbed_view_id
                        ? document.getElementById("view-" + loc.tabbed_view_id)
                        : null);
        ko.views.manager.openViewAsync(loc.view_type, uri, viewList, null,
                                       post_open_callback);
    }
    return null;
}

this.go_to_location = function go_to_location(loc, on_load_failure) {
    function on_load_success(view, lineNo) {
        if (!view) return;
        view.makeCurrent();
        if (loc.view_type == "editor") { // 
            var scimoz = view.scimoz;
            var targetPos = scimoz.positionFromLine(lineNo) + loc.col;
            scimoz.currentPos = scimoz.anchor = targetPos;
            scimoz.gotoPos(targetPos);
        }
        window.updateCommands("history_changed");
    }
    view_and_line_from_loc(loc, on_load_success, on_load_failure, true);
};

const _dbgp_url_stripper = new RegExp('^dbgp://[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}/');

function _label_from_loc(loc) {
    var baseName = null;
    function _callback(view, lineNo) {
        var dirName = null;
        var finalLabel, label, tooltiptext;
        switch (loc.view_type) {
        case 'editor':
            if (view) {
                var labels = ko.views.labelsFromView(view, lineNo + 1, false,
                                                     loc.section_title);
                if (labels[0]) {
                    return labels[0];
                }
            }
            var koFileEx = Components.classes["@activestate.com/koFileEx;1"]
                .createInstance(Components.interfaces.koIFileEx);
            koFileEx.URI = loc.uri;
            switch (koFileEx.scheme) {
            case "file":
                dirName = koFileEx.dirName;
                baseName = koFileEx.baseName;
                break;
            case "dbgp":
                baseName = loc.uri.replace(_dbgp_url_stripper, "dbgp:///");
                break;
            default:
                baseName = loc.uri;
            }
            break;
        case 'browser':
            baseName = loc.uri;
            lineNo = null;
            break;
        case 'startpage':
            baseName = _komodoBundle.GetStringFromName("startPageDisplayPath");
            lineNo = null;
            break;
        default:
            return null;
        }
        return ko.views.labelFromPathInfo(baseName, dirName, lineNo);
    }
    // Don't open closed views.
    // This is a sync call (not async), but it's coded this way
    // so go_to_location can share common code. 
    return view_and_line_from_loc(loc, _callback, function(){}, false);
}

this.init_popup_menu_recent_locations = function(event) {
    try {
    var popupMenu = event.target;
    while (popupMenu.hasChildNodes()) {
        popupMenu.removeChild(popupMenu.lastChild);
    }
    var locList = {};
    var currentLocIdx = {};
    // _get_curr_loc can be null here
    _controller.historySvc.get_recent_locs(_get_curr_loc(),
                                           _curr_session_name,
                                           currentLocIdx, locList, {});
    currentLocIdx = currentLocIdx.value;
    locList = locList.value;
    
    var menuitem, loc;
    for (var i = 0; i < locList.length; ++i) {
        loc = locList[i];
        if (!loc) {
            // Null items can come from unhandled views, like the startPage
            continue;
        }
        var tooltip;
        var label = _label_from_loc(loc);
        if (!label) {
            // Don't display unloaded unloaded dbgp URIs in the dropdown.
            // Otherwise they show up as blank lines.
            continue;
        }
        menuitem = document.createElement("menuitem");
        menuitem.setAttribute("label", label);
        menuitem.setAttribute("index", 0);
        var handler = null;
        var delta = currentLocIdx - i;
        var cssClass = "history-nav-item";
        if (delta == 0) {
            cssClass += " history-nav-current";
            menuitem.setAttribute("type", "checkbox");
            menuitem.setAttribute("checked", "true");
            handler = "event.stopPropagation()";
            tooltip = _bundle.GetStringFromName("historyStayAtCurrentLocation");
        } else if (delta > 0) {
            // move forward, with explicit=true
            handler = "ko.history.history_forward(" + delta + ", true)";
            tooltip = _bundle.GetStringFromName("historyGoForwardToThisLocation");
        } else {
            // move back, with explicit=true
            handler = "ko.history.history_back(" + (-1 * delta) + ", true)";
            tooltip = _bundle.GetStringFromName("historyGoBackToThisLocation");
        }
        menuitem.setAttribute("class", cssClass);
        menuitem.setAttribute("tooltiptext", tooltip);
        menuitem.setAttribute("oncommand", handler);
        popupMenu.appendChild(menuitem);
    }
    } catch(ex) {
        _log.exception("init_popup_menu_recent_locations: " + ex);
    }
};


function _on_load_failure(loc, is_moving_back, delta) {
    // Move back to the old location, but don't obsolete the current one.
    // Most likely caused by a remote file on an unavailable machine.
    // Whether the machine is dead or will be back in a second, is not
    // up to Komodo to determine.
    
    // No need for a message -- Komodo already gave a message when it failed
    // to load the uri.

    var reverse_method_name = is_moving_back ? "go_forward" : "go_back";
    _controller.historySvc[reverse_method_name](loc, delta);
}

/** Common function for moving forward or back
 * @param go_method_name {String} either 'go_back' or 'go_forward',
 *        used to make this routine work for both directins.
 * @param check_method_name {String} either 'can_go_back' or 'can_go_forward',
 *        Same rationale as go_method_name
 * @param delta {Integer} # of hops to make
 * @param explicit {Boolean} if true, the user pressed the "Recent
 *        Locations" button.  Otherwise they hit the go_back
 *        or go_forward command.
 */
this._history_move = function(go_method_name, check_method_name, delta,
                              explicit) {
    if (typeof(explicit) == "undefined") explicit=false;
    var view = ko.views.manager.currentView;
    var curr_loc = _get_curr_loc(view); // curr_loc can be null here
    _mark_pos_info(view);
    var is_moving_back = (go_method_name == 'go_back');
    for (var i = 0; i < _SKIP_DBGP_FALLBACK_LIMIT; i++) {
        var loc = _controller.historySvc[go_method_name](curr_loc, delta, _curr_session_name);
        try {
            // This function could load a file asynchronously,
            // so unless it throws an exception, there's no point
            // continuing after it's called.
            this.go_to_location(loc,
                function() {
                    _on_load_failure(loc, is_moving_back, delta);
                });
            return;
        } catch(ex if ex instanceof UnloadableDBGPLocError) {
            // Remove the loc we tried to move to from the history,
            // and then either keep trying to move to the next/prev loc
            // if we didn't get here via [History|Recent Locations]
            _controller.historySvc.obsolete_uri(loc.uri, delta, is_moving_back,
                                                _curr_session_name);
            if (!_controller.historySvc[check_method_name](_curr_session_name)) {
                window.updateCommands("history_changed");
                break;
            }
            if (explicit) {
                break;
            }
            // assert(delta == 1)
            
            // We hit an obsolete URI on an arrow command.
            // Keep going in the same direction until we either
            // reach a valid URI, the end, or hit the fallback limit.
        }
    }
    var msg1;
    if (explicit) {
        msg1 = _bundle.formatStringFromName("temporaryBufferNoLongerAccessible.templateFragment",
                                          [loc.uri], 1);
    } else if (i == _SKIP_DBGP_FALLBACK_LIMIT) {
        msg1 = _bundle.formatStringFromName("historyRanIntoSequence.templateFragment",
                                          [_SKIP_DBGP_FALLBACK_LIMIT], 1);
    } else {
        msg1 = _bundle.GetStringFromName("historyRemainingLocationsAreObsolete.fragment");
    }
    var msg2 = _bundle.formatStringFromName(is_moving_back
                                         ? "historyCouldntMoveBack.template"
                                         : "historyCouldntMoveForward.template",
                                         [msg1], 1);
    ko.statusBar.AddMessage(msg2, "editor", 3000, true);
};

this.history_back = function(delta, explicit) {
    this._history_move('go_back', 'can_go_back', delta, explicit);
};

this.history_forward = function(delta, explicit) {
    this._history_move('go_forward', 'can_go_forward', delta, explicit);
};

this.move_to_loc_before_last_jump = function(view, moveToFirstVisibleChar) {
    if (typeof(view.pos_before_last_jump) == "undefined") {
        view.pos_before_last_jump = {line:0, marker_handle:-1, col:0}
    }
    var info = view.pos_before_last_jump;
    var scimoz = view.scimoz;
    var next_line = scimoz.markerLineFromHandle(info.marker_handle);
    if (next_line == -1) {
        next_line = info.line;
    }
    _mark_pos_info(view);
    if (moveToFirstVisibleChar) {
        scimoz.gotoLine(next_line);
        scimoz.vCHome();
    } else {
        scimoz.gotoPos(scimoz.positionAtColumn(next_line, info.col));
    }
};

var _controller = new HistoryController();



//---- RecentlyClosedTabs sub-system

// Core data structure is a stack of rctab objects
 
var rctabs_list = [];
var rctab_list_max_size = 10;

this._handle_closing_view = function(event) {
    var rctab = _rctab_from_event(event);
    if (rctab) {
        rctabs_note(rctab);
    }
};

function _rctab_from_event(event) {
    var view = event.originalTarget;
    var uri = null;
    var viewType = view.getAttribute('type');
    switch (viewType) {
    case "editor":
        if (event.type == "view_closed") {
            // editor views are handled on document_detaching
            return null;
        }
        var koDocument = view.document;
        if (!koDocument || !koDocument.file) {
            return null;
        }
        // FALLTHRU
    case "browser":
        uri = view.document.file.URI;
        break;
    case "startpage":
        uri = view.document.displayPath;
        break;
    default:
        _log.warn("Unexpected view type: " + viewType + "\n");
        return null;
    }
    var tabIndex = -1;
    // Use tabs, not tabpanels, as tabs get reordered when they're
    // dragged, but tabpanels don't, and we want to capture tab order.
    var tabBox = view.parentNode.parentNode.parentNode;
    var tabs = tabBox.firstChild.childNodes;
    for (var i = 0; i < tabs.length; i++) {
        var v = document.getElementById(tabs[i].linkedPanel).firstChild;
        if (v == view) {
            tabIndex = i;
            break;
        }
    }
    return {tabGroup:view.parentView.id, viewType:viewType, uri:uri,
            tabIndex:tabIndex };
}

function rctabs_note(rctab) {
    if (!rctab.viewType || !rctab.uri) {
        return;
    }
    if (rctabs_list.length >= rctab_list_max_size) {
        var diffN = rctabs_list.length - rctab_list_max_size + 1;
        // Remove the diffN oldest items.
        rctabs_list.splice(0, diffN);
    }
    rctabs_list.push(rctab);
};

function _rctabs_determine_duplicate_entries(rctabs) {
    // Determine which items should have tabGroup and/or viewType
    // information in their menu item.  Normally we want to keep this
    // info out of the menu item because for most people it will be
    // clutter -- adding "(1, editor)" to each menuitem isn't too helpful.
    
    var rctabsLength = rctabs.length;
    var rctab;
    for (var i = 0; i < rctabsLength; i++) {
        rctabs[i].hasDuplicateTabGroup = false;
        rctabs[i].hasDuplicateViewType = false;
    }
    for (var i = 0; i < rctabsLength; i++) {
        rctab = rctabs[i];
        var views = ko.views.manager.topView.findViewsForURI(rctab.uri);
        for (var j = 0; j < views.length; j++) {
            // First compare each rctab against the list of loaded views
            // We could be fancy and quit when both are set to true,
            // but that's relatively rare.
            if (views[j].getAttribute("type") != rctab.viewType) {
                rctab.hasDuplicateViewType = true;
            }
            if (views[j].tabbedViewId != rctab.tabGroup) {
                rctab.hasDuplicateTabGroup = true;
            }
        }

        // Now compare each rctab against the rest
        for (var j = i + 1; j < rctabsLength; j++) {
            var other_rctab = rctabs[j];
            if (rctab.uri == other_rctab.uri) {
                if (rctab.tabGroup != other_rctab.tabGroup) {
                    rctab.hasDuplicateTabGroup = other_rctab.hasDuplicateTabGroup = true;
                }
                if (rctab.viewType != other_rctab.viewType) {
                    rctab.hasDuplicateViewType = other_rctab.hasDuplicateViewType = true;
                }
            }
        }
    }
}

this.rctabs_build_menu = function(menupopup) {
    while (menupopup.hasChildNodes()) {
        menupopup.removeChild(menupopup.lastChild);
    }
    var num_rctabs = rctabs_list.length;
    if (num_rctabs == 0) {
        var menuitem = document.createElement("menuitem");
        menuitem.setAttribute("label",
                              _bundle.GetStringFromName("noRecentlyClosedTabsAvailable.label"));
        menuitem.setAttribute("class", "menuitem_mru");
        menuitem.setAttribute("crop", "center");
        menuitem.setAttribute("disabled", "true");
        menupopup.appendChild(menuitem);
    }
    // Normally, we don't want to put viewTypes and tagGroups in
    // the menu unless they're needed to distinguish duplicates.

    _rctabs_determine_duplicate_entries(rctabs_list);    
    var label, tooltip;
    // rctabs_list is a stack, so walk it in reverse order
    var actual_index = 0;
    for (var i = num_rctabs - 1; i >= 0; i--, actual_index++) {
        var rctab = rctabs_list[i];
        var menuitem = document.createElement("menuitem");
        if (actual_index == 0) {
            menuitem.setAttribute("accesskey", "1");
            menuitem.setAttribute("observes", "cmd_reopenLastClosedTab");
        } else if ((actual_index + 1) <= 9) {
            menuitem.setAttribute("accesskey", (actual_index + 1).toString());
        } else if ((actual_index + 1) == 10) {
            menuitem.setAttribute("accesskey", "0");
        }
        var url = rctab.uri;
        var pathPart;
        var path = ko.uriparse.displayPath(url) || url;
        var baseName, dirName = null;
        var slashIdx = path.lastIndexOf("/");
        if (slashIdx == -1) {
            slashIdx = path.lastIndexOf("\\");
        }
        if (slashIdx == -1) {
            baseName = ko.uriparse.baseName(url);
        } else {
            baseName = path.substring(slashIdx + 1);
            dirName = path.substring(0, slashIdx);
        }
        pathPart = ko.views.labelFromPathInfo(
            baseName,
            dirName,
            null,  // line #
            rctab.hasDuplicateTabGroup ? rctab.tabGroup.substring("view-".length) : null,
            rctab.hasDuplicateViewType ? rctab.viewType : null
            );
        menuitem.setAttribute("label", (actual_index + 1) + " " + pathPart);
        menuitem.setAttribute("class", "menuitem_mru");
        menuitem.setAttribute("crop", "center");
        var cmd = ("ko.history.open_rctab(" + i + ")");
        menuitem.setAttribute("oncommand", cmd);
        menupopup.appendChild(menuitem);
    }
};

// open_rctab(-1) implements cmd_reopenLastClosedTab
// open_rctab(i) called from the rctab menu in general.
this.open_rctab = function(idx) {
    var rctab = rctabs_list.splice(idx, 1)[0];
    if (!rctab) {
        _log.debug("open_rctab: no views available on rctabs_list[" + idx + "]\n");
        return;
    }
    var tabList = document.getElementById(rctab.tabGroup);
    var uri = (rctab.viewType == "startpage"
               ? "chrome://komodo/content/startpage/startpage.xml#view-startpage"
               : rctab.uri);
    this.note_curr_loc();
    ko.views.manager.doFileOpenAsync(uri, rctab.viewType, tabList, rctab.tabIndex);
};


//---- History Prefs subsystem.

this.save_prefs = function(prefs) {
    var uriPrefSet = Components.classes['@activestate.com/koPreferenceSet;1'].createInstance();
    prefs.setPref("history_rctabs", uriPrefSet);
    var nativeJSON = Components.classes["@mozilla.org/dom/json;1"]
        .createInstance(Components.interfaces.nsIJSON);
    uriPrefSet.setStringPref("rctabs_list",
                             nativeJSON.encode(rctabs_list));
};

this.restore_prefs = function(prefs) {
    if (! prefs.hasPref("history_rctabs")) {
        return;
    }
    var nativeJSON = Components.classes["@mozilla.org/dom/json;1"]
        .createInstance(Components.interfaces.nsIJSON);
    var uriPrefSet = prefs.getPref("history_rctabs");
    if (uriPrefSet.hasPref("rctabs_list")) {
        rctabs_list =
            nativeJSON.decode(uriPrefSet.getStringPref("rctabs_list"));
    }
};

}).apply(ko.history);

