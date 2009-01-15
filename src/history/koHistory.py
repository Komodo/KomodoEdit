#!/usr/bin/env python
# Copyright (c) 2009 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

"""PyXPCOM bindings for editorhistory.py for a history feature in Komodo."""

import sys
import os
from os.path import join
import logging

from xpcom import components, nsError, ServerException, COMException
from xpcom.client import WeakReference
from xpcom.server import WrapObject, UnwrapObject

from editorhistory import History



#---- globals

log = logging.getLogger('history')
log.setLevel(logging.DEBUG)



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

        #TODO:XXX Need to review this. Not sure it can work. Kills
        #         threadsafety.
        self._ignoreUpdates = False

    #TODO: s/canMoveBack/can_go_back/
    #TODO: s/canMoveForward/can_go_forward/
    #TODO: s/moveBack/go_back/
    #TODO: s/moveForward/go_forward/

    def note_loc(self, loc):
        #TODO: review use of _ignoreUpdates
        if self._ignoreUpdates:
            return None
        #TODO: review this and move to backend
        elif self._tooSimilarToCurrentSavedPoint(loc):
            return None
        return History.note_loc(self, loc)

    def _tooSimilarToCurrentSavedPoint(self, candidateLoc):
        return False

    #TODO: review the use of these
    def ignore_updates(self):
        self._ignoreUpdates = True
    def resume_updates(self):
        self._ignoreUpdates = False
