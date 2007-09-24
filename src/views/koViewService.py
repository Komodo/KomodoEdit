# Copyright (c) 2000-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

# document object service and cache

from xpcom import components, nsError, ServerException, COMException
from xpcom.client import WeakReference

import logging
log = logging.getLogger('koViewService')

class koViewService:
    _com_interfaces_ = [components.interfaces.koIViewService]
    _reg_desc_ = "Komodo View Service Component"
    _reg_contractid_ = "@activestate.com/koViewService;1"
    _reg_clsid_ = "{7F78C1E7-A746-449F-951D-8BED1B502CCD}"
    
    def __init__(self):
        self._viewMgr = None
        
    def setViewMgr(self, viewMgr):
        self._viewMgr = viewMgr

    def get_currentView(self):
        if self._viewMgr:
            return self._viewMgr.currentView
        else:
            log.error("Trying to get currentView from the koViewService but no viewMgr has been set")

    def get_topView(self):
        if self._viewMgr:
            return self._viewMgr.topView
        else:
            log.error("Trying to get topView from the koViewService but no viewMgr has been set")

    def newViewFromURI(self, URI, type):
        if self._viewMgr:
            return self._viewMgr.newViewFromURI(URI, type)
        else:
            log.error("Trying to create a new view from the koViewService but no viewMgr has been set")
