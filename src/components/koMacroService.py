#!/usr/bin/env python
# Copyright (c) 2003-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

import sys
from xpcom import components, nsError, ServerException, COMException
from xpcom._xpcom import PROXY_SYNC, PROXY_ALWAYS, PROXY_ASYNC



#---- component implementation

class KoMacroService:
    _com_interfaces_ = [components.interfaces.koIMacroService]
    _reg_clsid_ = "D6126643-84DC-4DDE-9101-C4BF9B40F588"
    _reg_contractid_ = "@activestate.com/koMacroService;1"
    _reg_desc_ = "Service for running Macros"

    def __init__(self):
        # ensure that the koPartService is listening
        koPartSvc = components.classes["@activestate.com/koPartService;1"]\
            .getService(components.interfaces.koIPartService)
        self._observerSvc = components.classes["@mozilla.org/observer-service;1"]\
            .getService(components.interfaces.nsIObserverService)

        # not sure why we can't create proxies -- I'm thinking that we need
        # to because the JS notification hangs the main window.
        #self._proxyMgr = components.classes["@mozilla.org/xpcomproxy;1"].\
        #    getService(components.interfaces.nsIProxyObjectManager)
        #self._proxyObserverSvc = self._proxyMgr.getProxyForObject(None,
        #    components.interfaces.nsIObserverService, self._observerSvc,
        #    PROXY_ALWAYS | PROXY_ASYNC)

    def runString(self, language, code):
        print "sending notification", language + '_macro'
        self._observerSvc.notifyObservers(self, language + '_macro', code)

    def runFile(self, language, filename):
        code = open(filename).read()
        self.runString(language, code)

