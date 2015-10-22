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



if (typeof(ko) == 'undefined') {
    var ko = {};
}
if (typeof(ko.views)=='undefined') {
    ko.views = {};
}
(function() {

/**
 * view history controller
 * 
 *
 * Recently-visited views:
 * 
 * The viewhistory object maintains a stack of recently visited lists. This
 * information can be used to switch to recent views. The semantics of the
 * following methods are as follows:
 *  - .getNextMostRecentView() and .getNextLeastRecentView() are used by the
 *    buffer switching commands to know which views to switch to.
 *  - .enterBufferSwitchingSession() and .exitBufferSwitchingSession() are
 *    called by the buffer swiching commands to help .setMostRecentView() know
 *    how to behave (the "recent views" stack is NOT updated during such a
 *    session). Note that .enter...() may be called multiple times for one
 *    .exit...() call.
 *  - .setMostRecentView() is called by the view manager's .selectView() and can
 *    be called directly by the buffer switching commands for proper session
 *    handling.
 * 
 *  NOTE: THIS BEHAVIOR IS TURNED OFF BY SETTING "handlestctrltab" to false on the tabbed view.
 */
this.ViewHistory = function viewhistory() {
    this._recentViews = [];
    this.inBufferSwitchingSession = false;
    this._observingCtrlKeyUp = false;
    this.log = ko.logging.getLogger('viewhistory');
    //this.log.setLevel(ko.logging.LOG_DEBUG);
    this._currentView = null;
    var self = this;
    this.handle_current_view_changed = function(event) {
        self._currentView = event.originalTarget;
        self.setMostRecentView(self._currentView);
    };
    this.handle_view_list_closed = function(event) {
        self._currentView = null;
    };
    this.handle_view_closed = function(event) {
        self.removeRecentView(event.originalTarget);
    };
    this.handle_view_opened = function(event) {
        self.setMostRecentView(event.originalTarget);
    };
    window.addEventListener('current_view_changed',
                            this.handle_current_view_changed, false);
    window.addEventListener('view_list_closed',
                            this.handle_view_list_closed, false);
    window.addEventListener('view_closed', this.handle_view_closed, false);
    window.addEventListener('view_opened', this.handle_view_opened, false);
    ko.main.addWillCloseHandler(this.finalize, this);
}

this.ViewHistory.prototype.constructor = this.ViewHistory;

this.ViewHistory.prototype.finalize = function()
{
    window.removeEventListener('current_view_changed',
                               this.handle_current_view_changed, false);
    window.removeEventListener('view_list_closed',
                               this.handle_view_list_closed, false);
    window.removeEventListener('view_closed', this.handle_view_closed, false);
    window.removeEventListener('view_opened', this.handle_view_opened, false);
}
this.ViewHistory.prototype.doNextMostRecentView = function()
{
    this.log.info("doNextMostRecentView");
    var v = this.getNextMostRecentView();
    if (v != null) {
        this.enterBufferSwitchingSession();
        this._setKeyListener()
        v.makeCurrent();
    }
}

this.ViewHistory.prototype.doNextLeastRecentView = function()
{
    this.log.info("doNextLeastRecentView");
    var v = this.getNextLeastRecentView();
    if (v != null) {
        this.enterBufferSwitchingSession();
        this._setKeyListener()
        v.makeCurrent();
    }
}

this.ViewHistory.prototype._setKeyListener = function()
{
    if (this._keylistener) return;
    var me = this;
    this._keylistener = function (event) {
        me.ctrlup(event);
    }
    window.addEventListener("keyup", this._keylistener, true);
}

this.ViewHistory.prototype.ctrlup = function(event)
{
    var endSession;
    // if it's not the ctrl key (or alternatively the meta key on OS X), get out
// #if PLATFORM != 'darwin'
    endSession = (event.keyCode == 17);
// #else
    endSession = (event.keyCode == 17 || event.keyCode == 224);
// #endif
// #if PLATFORM == 'darwin'
    // Workaround for bug 82486:
    // On OS X, when the ctrl and tab keys are released nearly
    // simultaneously, the ctrl-up event is lost, and the tab-up event
    // has event.ctrlKey set to true.  The workaround is to
    // realize that we're still in a session, continue processing keyup
    // events, and end the session as soon as we get an event
    // when the ctrl key is no longer up.
    if (!endSession && !event.ctrlKey && !event.metaKey) {
        endSession = true;
    }
// #endif
    if (!endSession) {
        return;
    }

    window.removeEventListener("keyup", this._keylistener, true);
    this._keylistener = null;
    this.exitBufferSwitchingSession();
    this.setMostRecentView(this._currentView);
    this._currentView.doFocus(); // needed to possibly start lint XXX want better API
}

this.ViewHistory.prototype._debug_recentViews = function()
{
    dump("Recent views: have " + this._recentViews.length + " views in history:\n");
    for (var i = 0; i < this._recentViews.length; i++) {
        dump('[' + i + ']: ');
        try {
            if (!this._recentViews[i]) {
                dump('<null>\n');
            } else {
                var v = this._recentViews[i];
                v = v.koDoc ? v.koDoc.baseName : "[doc not set]";
                if (this._recentViews[i] == this._currentView) {
                    dump('*** ');
                }
                dump(v + '\n');
            }
        } catch (e) {
            this.log.error(e);
            dump("...\n");
        }
    }
}

/**
 * Generate the view history views in order (current view first, then the
 * next most recent view, ...).
 */
this.ViewHistory.prototype.genRecentViews = function() {
    for (var i = 0; i < this._recentViews.length; i++) {
        if (!this._recentViews[i]) {
            continue;
        }
        yield this._recentViews[i];
    }
}

this.ViewHistory.prototype._getCurrentViewIdx = function() {
    if (!this._recentViews || this._recentViews.length < 2) {
        this.log.info("no _recentViews in viewGetter");
        //this._debug_recentViews();
        return -1;
    }
    var currIndex = this._recentViews.indexOf(this._currentView);
    if (currIndex == -1) {
        var msg = "Can't find the current view ";
        try {
            msg += this._currentView.koDoc.baseName;
        } catch(e) {}
        this.log.info(msg);
        //this._debug_recentViews();
    }
    return currIndex;
}

this.ViewHistory.prototype.getNextMostRecentView = function()
{
    this.log.info("getNextMostRecentView");
    var currIndex = this._getCurrentViewIdx();
    if (currIndex == -1) {
        return null;
    }
    // Find the current view in the "_recentViews" stack and return the
    // preceding view.
    var index = (currIndex + 1) % this._recentViews.length;
    var view = this._recentViews[index];
    if (typeof(view) == 'undefined' || !view) {
        // The "recent urls" list is out of date. Remove this entry and try
        // again.
        var newStack = new Array();
        for (i in this._recentViews) {
            i = Number(i);
            if (this._recentViews[i] != view) {
                newStack[newStack.length] = this._recentViews[i];
            }
        }
        this._recentViews = newStack;
        this.log.debug("getNextMostRecentView(): recents list is out of date, remove");
        return this.getNextMostRecentView();
    } else {
        return view;
    }
}

this.ViewHistory.prototype.getNextLeastRecentView = function()
{
    this.log.info("getNextLeastRecentView");
    var currIndex = this._getCurrentViewIdx();
    if (currIndex == -1) {
        return null;
    }
    // Find the current view in the "recent views" stack and return the
    // succeeding view.
    // XXX JavaScript get's modulus wrong for negative values, so add the
    //     .length to ensure the value is not negative.
    var index = (currIndex - 1 + this._recentViews.length) %
                this._recentViews.length;

    var view = this._recentViews[index];
    if (typeof(view) == 'undefined' || !view) {
        // The "recent urls" list is out of date. Remove this entry and try
        // again.
        var newStack = new Array();
        for (i in this._recentViews) {
            i = Number(i);
            if (this._recentViews[i] != view) {
                newStack[newStack.length] = this._recentViews[i];
            }
        }
        this._recentViews = newStack;
        //this.log.debug("getNextLeastRecentView(): curr=" + currUrl +
        //          ", recents list is out of date, remove " + url);
        return this.getNextLeastRecentView();
    } else {
        this.log.debug("TabViewManager.getNextLeastRecentView()");
        return view;
    }
}

this.ViewHistory.prototype.enterBufferSwitchingSession = function()
{
    this.log.debug("enterBufferSwitchingSession()");
    this.inBufferSwitchingSession = true;
}

this.ViewHistory.prototype.exitBufferSwitchingSession = function()
{
    this.log.debug("exitBufferSwitchingSession()");
    this.inBufferSwitchingSession = false;
    // Perf: Now that the user has finished switching to the tab they want, we
    //       can update all of the necessary commands for the new view.
    ko.views.manager.updateCommands();
}

this.ViewHistory.prototype.setMostRecentView = function (view)
{
    this.log.info("setMostRecentView");
    //if (view) {
    //    this.log.debug("in setMostRecentView" + view.koDoc.baseName);
    //}
    // Bring the given view to front of the "recent views" stack (note: it may
    // not yet be *in* the stack) *unless* we are currently in a buffer
    // switching session (e.g. press <Ctrl> and hold, hit <Tab> a few times,
    // release <Ctrl>).  Have to do the "unless" checking in here because
    // .selectView() calls this method.
    //this._debug_recentViews();
    var v;
    if (! this.inBufferSwitchingSession) {
        var idx = this._recentViews.indexOf(view);
        if (idx != 0) {
            // If 0, leave it at the start
            if (idx > 0) {
                ko.history.note_loc_unless_history_move(this._recentViews[0]);
                this._recentViews.splice(idx, 1);
            }
            this._recentViews.unshift(view);
        }
        //this._debug_recentViews();
        //this.log.debug("setMostRecentView(" + view +
        //          "): new stack: " + this._recentViews);
    }
    else {
        this.log.debug("setMostRecentView(" + view + "): ignored because in buffer switching session");
    }
}


this.ViewHistory.prototype.removeRecentView = function (view)
{
    this.log.info("removeRecentView");
    // this._debug_recentViews();
    var idx = this._recentViews.indexOf(view);
    if (idx >= 0) {
        this._recentViews.splice(idx, 1);
    }
    // this._debug_recentViews();
}

this.ViewHistory.prototype.setState = function (state, viewcontainer)
{
    this.log.info("setState");
    // This function sets a control-tab history from a pref
    // it is called by the onload handler that restores 'workspace'.
    // It stomps over whatever recent view history is established
    // by loading of views.  It needs to be called _after_
    // the views are available. It ignores URIs for views that
    // aren't loaded.
    var _recentViews = [];
    var marker = '?parentId=';
    var markerLength = marker.length;
    var identifier, URI, parent, parentId, views, view;
    var index, i, j;
    for (i = 0; i < state.length; i++) {
        identifier = state.getStringPref(i);
        index = identifier.indexOf(marker);
        URI = identifier.slice(0, index);
        parentId = identifier.slice(index+markerLength);
        parent = document.getElementById(parentId);
        views = parent.findViewsForURI(URI);
        if (views.length > 0) {
            _recentViews.push(views[0]);
        }
    }
    // now merge in any previously opened files that
    // were not in the prefs
    var found;
    for (i = 0; i < this._recentViews.length; i++) {
        view = this._recentViews[i];
        found = false;
        for (j = 0; j < _recentViews.length; j++) {
            if (view == _recentViews[j]) {
                found = true;
                break;
            }
        }
        if (!found) {
            _recentViews.push(view);
        }
    }
    this._recentViews = _recentViews;
}

this.ViewHistory.prototype.getState = function ()
{
    this.log.info("getState");
    // This function returns a pref which can be used in conjunction
    // with .setState() to serialize the 'recent views' history.
    var state = Components.classes['@activestate.com/koOrderedPreference;1'].createInstance();
    var index, v;
    for (var i = 0; i < this._recentViews.length; i++) {
        v = this._recentViews[i];
        if (v && v.parentView &&
            v.koDoc && !v.koDoc.isUntitled &&
            v.koDoc.file && v.koDoc.file.URI) {
            state.appendStringPref(v.koDoc.file.URI + '?parentId=' + v.parentView.getAttribute('id'));
        }
    }
    return state;
}

}).apply(ko.views);

