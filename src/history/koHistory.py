#!/usr/bin/env python
# Copyright (c) 2009 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

"""PyXPCOM bindings for editorhistory.py for a history feature in Komodo.

Database kept in $USERDATADIR/history.sqlite
"""

import sys
import os
from os.path import join
import logging

from xpcom import components, COMException

from editorhistory import History, Location

#---- globals

log = logging.getLogger('history')
#log.setLevel(logging.DEBUG)


#---- the components/services

class KoHistoryService(History):
    _com_interfaces_ = [components.interfaces.koIHistoryService,
                        components.interfaces.nsIObserver]
    _reg_desc_ = "Komodo History Service"
    _reg_contractid_ = "@activestate.com/koHistoryService;1"
    _reg_clsid_ = "{71b1c721-9abd-4ce8-a35e-166409750248}"

    MARKNUM_HISTORYLOC = 13 # Keep in sync with content/markers.js
    
    #TODO: better name for this constant
    MINIMUM_LINE_SEPARATION = 10 #TODO: Control this with an invisible pref
    
    def __init__(self):
        koDirSvc = components.classes["@activestate.com/koDirs;1"].\
            getService(components.interfaces.koIDirs)
        db_path = join(koDirSvc.userDataDir, "history.sqlite")
        History.__init__(self, db_path)
        self._observerSvc = components.classes["@mozilla.org/observer-service;1"].\
            getService(components.interfaces.nsIObserverService)
        self._observerSvc.addObserver(self, 'xpcom-shutdown', False)

    def finalize(self):
        self.close()

    def observe(self, subject, topic, data):
        if topic == "xpcom-shutdown":
            self.finalize()

    @components.ProxyToMainThreadAsync
    def notifyObservers(self, subject, topic, data):
        self._observerSvc.notifyObservers(subject, topic, data)

    def loc_from_view_info(self, view_type,
                           window_num, tabbed_view_id, view,
                           pos=-1, session_name="",
                           callback=None):
        """Create a Location instance from the given view info.
        
        @param view_type {string}
        @param window_num {int} the identifier for the view's Komodo window.
        @param tabbed_view_id {int} the identifier for the multi-tabbed view
            containing `view`.
        @param view {koIView} a Komodo view.
        @param pos {int} position of view to record
            ignored for some non-editor views, conventionally -1
        @param session_name {str} the current history session. Default is the
            empty string.
        @param callback {callable} The callback to invoke when the location has
            been found; takes a single Location argument.
        """
        if view.koDoc.file:
            uri = view.koDoc.file.URI
        elif view_type == 'editor':
            # Internal URI scheme used for unsaved buffers
            uri = "kotemporary://" + view.uid + "/" + view.koDoc.displayPath;
        else:
            uri = ""

        def on_have_location(section=None):
            if section:
                loc.section_title = section.title
            loc.window_num = window_num
            loc.tabbed_view_id = tabbed_view_id
            loc.session_name = session_name
            if hasattr(callback, "onHaveLocation"):
                callback.onHaveLocation(loc)
            elif loc:
                callback(loc)

        pending = False
        if view_type == 'editor':
            view = view.QueryInterface(components.interfaces.koIScintillaView)
            scimoz = view.scimoz
            if pos == -1:
                pos = scimoz.currentPos
            line = scimoz.lineFromPosition(pos)
            loc = Location(uri, line,
                           scimoz.getColumn(pos),
                           view_type)
            loc.marker_handle = scimoz.markerAdd(line, self.MARKNUM_HISTORYLOC)
            ciBuf = view.koDoc.ciBuf
            if ciBuf and hasattr(ciBuf, "section_from_line"):
                try:
                    ciBuf.section_from_line(line + 1,
                                            ciBuf.SECTION_CURRENT,
                                            False,
                                            on_have_location)
                except COMException:
                    # See bug 82776.  Don't know why we get this when
                    # ctrl-tabbing across a tab group.
                    log.exception("can't get the section")
                else:
                    pending = True
        else:
            loc = Location(uri, -1, -1, view_type)
        if not pending:
            on_have_location()

    def note_loc(self, loc, check_section_change=False, view=None):
        # If the given loc is sufficiently close to the previous one, then
        # don't bother noting this new one.
        recent_back_visits = self.get_session(loc.session_name).recent_back_visits
        if recent_back_visits:
            prev_loc = recent_back_visits[0]
            if loc.uri == prev_loc.uri:
                if self._is_loc_same_line(prev_loc, loc):
                    return None
                elif check_section_change and view and self._is_loc_same_section(prev_loc, loc):
                    self._take_loc_marker(prev_loc, loc, view)
                    return None

        res = History.note_loc(self, loc)
        #XXX:TODO: Change to history_changed_significantly (you know what
        #   I mean) b/c *most* of this "history_changed" are useless.
        try:
            self.notifyObservers(None, 'history_changed', "")
        except COMException, ex:
            log.warn("exception notifying 'history_changed': %s", ex)
            pass
        return res

    def _is_loc_same_line(self, candidate_loc, other_loc):
        return (other_loc.uri == candidate_loc.uri
                and other_loc.line == candidate_loc.line)

    def _is_loc_same_section(self, prev_loc, loc):
        """ If at least one location has a non-empty section_title, compare
        by that.  Otherwise compare by proximity.
        """
        assert prev_loc.uri == loc.uri
        if prev_loc.section_title or loc.section_title:
            if prev_loc.section_title == loc.section_title:
                return True
        return self._is_loc_close_line(prev_loc, loc)
            
    def _is_loc_close_line(self, prev_loc, loc):
        assert prev_loc.uri == loc.uri
        return abs(prev_loc.line - loc.line) < self.MINIMUM_LINE_SEPARATION

    def _take_loc_marker(self, prev_loc, loc, view):
        # Update the previous location to point at this line,
        # and update the scimoz marker.
        old_line = prev_loc.line
        new_line = loc.line
        scimoz = view.scimoz
        scimoz.markerDeleteHandle(prev_loc.marker_handle)
        prev_loc.marker_handle = scimoz.markerAdd(new_line, self.MARKNUM_HISTORYLOC)
        prev_loc.line = new_line
        
    def note_curr_editor_loc(self, view=None):
        """Note the current location in the given *editor* view (by default
        the current view).
        
        @param view {koIScintillaView} The view from which to get location
            information. Optional. If not given, defaults to the current
            view.
        """
        if view is None:
            try:
                view = components.classes["@activestate.com/koViewService;1"]\
                       .getService(components.interfaces.koIViewService).currentView \
                       .QueryInterface(components.interfaces.koIScintillaView)
            except:
                return None

        self.loc_from_view_info("editor",
                                view.windowNum, view.tabbedViewId,
                                view, view.scimoz.currentPos,
                                view.historySessionName,
                                self.note_loc)

    def get_recent_locs(self, curr_loc, session_name="", callback=None):
        idx = 0
        curr_idx = 0
        loc_list = []
        try:
            for is_curr, loc in self.recent_history(curr_loc,
                    merge_curr_loc=True, session_name=session_name):
                loc_list.append(loc)
                if is_curr:
                    curr_idx = idx
                idx += 1
        except StopIteration:
            pass
        callback.onHaveLocations(loc_list, curr_idx)
