# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
# 
# The contents of this file are subject to the Mozilla Public License
# Version 1.1 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
# 
# Software distributed under the License is distributed on an "AS IS"
# basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
# License for the specific language governing rights and limitations
# under the License.
# 
# The Original Code is Komodo code.
# 
# The Initial Developer of the Original Code is ActiveState Software Inc.
# Portions created by ActiveState Software Inc are Copyright (C) 2000-2010
# ActiveState Software Inc. All Rights Reserved.
# 
# Contributor(s):
#   ActiveState Software Inc
# 
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
# 
# ***** END LICENSE BLOCK *****

"""Service for handling Komodo views (basically tabs in the main window(s))."""

from xpcom import components, nsError, ServerException, COMException
from xpcom.client import WeakReference
from xpcom.server import WrapObject, UnwrapObject

import logging
log = logging.getLogger('koViewService')
#log.setLevel(logging.DEBUG)

# XXX the view service needs some additional thought for supporting multi
# window capability.

class koViewService:
    _com_interfaces_ = [components.interfaces.koIViewService,
                        components.interfaces.nsIWindowMediatorListener]
    _reg_desc_ = "Komodo View Service Component"
    _reg_contractid_ = "@activestate.com/koViewService;1"
    _reg_clsid_ = "{7F78C1E7-A746-449F-951D-8BED1B502CCD}"
    
    def __init__(self):
        self._viewMgr = {}
        self.wrapped = WrapObject(self, components.interfaces.nsIWindowMediatorListener)

        self.wm = components.classes["@mozilla.org/appshell/window-mediator;1"].\
                        getService(components.interfaces.nsIWindowMediator);
        self.wm.addListener(self.wrapped)
        self._all_views_wr = set()

    def onWindowTitleChange(self, xulwindow, newTitle):
        pass
    def onOpenWindow(self, xulwindow):
        pass
    def onCloseWindow(self, xulwindow):
        # we're given a nsIXULWindow, not a nsIDOMWindow; so we need to check
        # everything we know to see if it belongs to that nsIXULWindow and
        # remove everything that matches (usually just one).
        ci = components.interfaces
        for window in self._viewMgr.keys():
            xw = window.QueryInterface(ci.nsIInterfaceRequestor).\
                        getInterface(ci.nsIWebNavigation).\
                        QueryInterface(ci.nsIDocShellTreeItem).\
                        treeOwner.\
                        QueryInterface(ci.nsIInterfaceRequestor).\
                        getInterface(ci.nsIXULWindow)
            if xw == xulwindow:
                del self._viewMgr[window]

    def setViewMgr(self, viewMgr):
        window = self.wm.getMostRecentWindow('Komodo')
        self._viewMgr[window] = viewMgr

    def get_currentView(self):
        window = self.wm.getMostRecentWindow('Komodo')
        if window in self._viewMgr:
            return self._viewMgr[window].currentView
        else:
            log.error("Trying to get currentView from the koViewService but no viewMgr has been set")

    def get_topView(self):
        window = self.wm.getMostRecentWindow('Komodo')
        if window in self._viewMgr:
            return self._viewMgr[window].topView
        else:
            log.error("Trying to get topView from the koViewService but no viewMgr has been set")

    def registerView(self, view):
        self._all_views_wr.add(WeakReference(view))

    def getAllViews(self, viewtype=""):
        all_views = []
        for viewMgr in self._viewMgr.values():
            # Bug 91744: if no views, getAllViews() returns None, not []
            all_views += (viewMgr.getAllViews(viewtype) or [])
        return all_views

    def getReferencedViewCount(self, viewtype=""):
        count = 0
        leaked = 0
        for view_weakref in list(self._all_views_wr):
            try:
                view = view_weakref()
                if view is None:
                    # An expired weak reference - remove it.
                    self._all_views_wr.discard(view_weakref)
                else:
                    count += 1
            except COMException:
                # A dead view object, someone is still holding onto it...
                count += 1
                leaked += 1
        return count, leaked

    def getAllViewMgrs(self):
        return self._viewMgr.values()
