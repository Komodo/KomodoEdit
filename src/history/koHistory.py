#!/usr/bin/env python
# Copyright (c) 2009 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

"""PyXPCOM bindings for editorhistory.py for a history feature in Komodo.

Database kept in $USERDATADIR/host-.../history.sqlite
"""

import sys
import os
from os.path import join
import logging

from xpcom import components, nsError, ServerException, COMException, _xpcom
from xpcom.client import WeakReference
from xpcom.server import WrapObject, UnwrapObject

from editorhistory import History, Location

#---- globals

log = logging.getLogger('history')
#log.setLevel(logging.DEBUG)


#---- the components/services

class KoHistoryService(History):
    _com_interfaces_ = [components.interfaces.koIHistoryService]
    _reg_desc_ = "Komodo History Service"
    _reg_contractid_ = "@activestate.com/koHistoryService;1"
    _reg_clsid_ = "{71b1c721-9abd-4ce8-a35e-166409750248}"

    MINIMUM_LINE_SEPARATION = 10 #TODO: Control this with an invisible pref
    def __init__(self):
        koDirSvc = components.classes["@activestate.com/koDirs;1"].\
            getService(components.interfaces.koIDirs)
        db_path = join(koDirSvc.hostUserDataDir, "history.sqlite")
        History.__init__(self, db_path)
        self._observerSvc = components.classes["@mozilla.org/observer-service;1"].\
            getService(components.interfaces.nsIObserverService)
        self._obsSvcProxy = _xpcom.getProxyForObject(1, components.interfaces.nsIObserverService,
                                          self._observerSvc, _xpcom.PROXY_SYNC | _xpcom.PROXY_ALWAYS)

    def editor_loc_from_info(self, window_num, tabbed_view_id, view):
        """Create a Location instance from the given *editor* view info.
        
        @param window_num {int} The identifier for the view's Komodo window.
        @param tabbed_view_id {int} The identifier for the multi-tabbed view
            containing `view`.
        @param view {koIScintillaView} A Komodo editor view.
        @returns {Location}
        """
        #XXX:TODO handle untitled documents
        uri = view.document.file and view.document.file.URI or ""
        scimoz = view.scimoz
        line = scimoz.lineFromPosition(scimoz.currentPos)
        col = scimoz.currentPos - scimoz.positionFromLine(line)
        view_type = "editor"
        loc = Location(uri, line, col, view_type)
        loc.window_num = window_num
        loc.tabbed_view_id = tabbed_view_id
        loc.marker_handle = scimoz.markerAdd(line, self.MARKNUM_HISTORYLOC)
        ciBuf = view.document.ciBuf
        if ciBuf and hasattr(ciBuf, "curr_section_from_line"):
            section = ciBuf.curr_section_from_line(line + 1)
            if section:
                loc.section_name = section.title
        return loc    

    def note_loc(self, loc, check_section_change=False, view=None):
        #TODO: review this and move to backend
        if self.recent_back_visits:
            prev_loc = self.recent_back_visits[0]
            if loc.uri == prev_loc.uri:
                if self._is_loc_same_line(prev_loc, loc):
                    return None
                elif check_section_change and self._is_loc_same_section(prev_loc, loc):
                    self._take_loc_marker(prev_loc, loc, view)
                    return None
            
        res = History.note_loc(self, loc)
        #XXX:TODO: Change to history_changed_significantly (you know what
        #   I mean) b/c *most* of this "history_changed" are useless.
        try:
            self._obsSvcProxy.notifyObservers(None, 'history_changed', "")
        except COMException, ex:
            log.warn("exception notifying 'history_changed': %s", ex)
            pass
        return res

    def _is_loc_same_section(self, prev_loc, loc):
        """ If at least one location has a non-empty section_name, compare
        by that.  Otherwise compare by proximity.
        """
        assert prev_loc.uri == loc.uri
        if prev_loc.section_name or loc.section_name:
            if prev_loc.section_name == loc.section_name:
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
        @returns {Location}
        """
        if view is None:
            view = components.classes["@activestate.com/koViewService;1"]\
                .getService(components.interfaces.koIViewService).currentView \
                .QueryInterface(components.interfaces.koIScintillaView)
        loc = self.editor_loc_from_info(view.windowNum, view.tabbedViewId, view)
        return self.note_loc(loc)

    def get_recent_locs(self, curr_loc):
        idx = 0
        curr_idx = 0
        loc_list = []
        try:
            for is_curr, loc in self.recent_history(curr_loc):
                loc_list.append(loc)
                if is_curr:
                    curr_idx = idx
                idx += 1
        except StopIteration:
            pass
        return curr_idx, loc_list
