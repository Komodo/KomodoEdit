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

from xpcom import components, nsError, ServerException, COMException
from xpcom.client import WeakReference
from xpcom.server import WrapObject, UnwrapObject

from editorhistory import History, Location

#---- globals

log = logging.getLogger('history')
log.setLevel(logging.DEBUG)

MARKNUM_HISTORYLOC = 13 # Keep in sync with content/markers.js


#---- the components/services

class KoHistoryService(History):
    _com_interfaces_ = [components.interfaces.koIHistoryService]
    _reg_desc_ = "Komodo History Service"
    _reg_contractid_ = "@activestate.com/koHistoryService;1"
    _reg_clsid_ = "{71b1c721-9abd-4ce8-a35e-166409750248}"

    def __init__(self):
        koDirSvc = components.classes["@activestate.com/koDirs;1"].\
            getService(components.interfaces.koIDirs)
        db_path = join(koDirSvc.hostUserDataDir, "history.sqlite")
        History.__init__(self, db_path)
        self._observerSvc = components.classes["@mozilla.org/observer-service;1"].\
            getService(components.interfaces.nsIObserverService)

    def editor_loc_from_info(self, window_name, multiview_id, view):
        """Create a Location instance from the given *editor* view info.
        
        @param window_name {str} The identifier for the view's Komodo window.
        @param multiview_id {int} The identifier for the multi-tabbed view
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
        loc.window_name = window_name
        loc.multiview_id = multiview_id
        loc.marker_handle = scimoz.markerAdd(line, MARKNUM_HISTORYLOC)
        return loc    

    def note_loc(self, loc):
        #TODO: review this and move to backend
        if self._tooSimilarToCurrentSavedPoint(loc):
            return None
        res = History.note_loc(self, loc)
        #XXX:TODO: Change to history_changed_significantly (you know what
        #   I mean) b/c *most* of this "history_changed" are useless.
        try:
            self._observerSvc.notifyObservers(None, 'history_changed', "")
        except COMException, ex:
            log.warn("exception notifying 'history_changed': %s", ex)
            pass
        return res
        
    def note_curr_loc(self, view=None):
        """Note the current location in the given view (by default the current
        view).
        
        @param view {koIScintillaView} The view from which to get location
            information. Optional. If not given, defaults to the current
            view.
        @returns {Location}
        """
        if view is None:
            #XXX:TODO: this can fail. What if the current view is the Start
            #   Page (not a koIScintillaView)?
            view = components.classes["@activestate.com/koViewService;1"]\
                .getService(components.interfaces.koIViewService).currentView \
                .QueryInterface(components.interfaces.koIScintillaView)
        #XXX:TODO: This method needs to accept window_name and multiview_id
        #          a la editor_loc_from_info().
        #XXX:TODO: don't pass '-1', the IDL says unsigned
        loc = self.editor_loc_from_info("XXX", -1, view)
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

    def _tooSimilarToCurrentSavedPoint(self, candidateLoc):
        return False
