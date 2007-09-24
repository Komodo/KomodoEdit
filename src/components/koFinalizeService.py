#!/usr/bin/env python
# Copyright (c) 2004-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

"""Service to help other Komodo services finalize at Komodo shutdown."""

from xpcom import components, COMException, ServerException, nsError
from xpcom.server import WrapObject, UnwrapObject


class KoFinalizeService:
    _com_interfaces_ = [components.interfaces.koIFinalizeService,
                        components.interfaces.nsIObserver]
    _reg_clsid_ = "{ED97B6BF-70C1-45D6-93FC-64E8B4DE435A}"
    _reg_contractid_ = "@activestate.com/koFinalizeService;1"
    _reg_desc_ = "Finalize registered components on Komodo shutdown"

    def __init__(self):
        self.finalizers = []
        obsvc = components.classes["@mozilla.org/observer-service;1"].\
                    getService(components.interfaces.nsIObserverService)
        self._observer = WrapObject(self, components.interfaces.nsIObserver)
        obsvc.addObserver(self._observer, 'xpcom-shutdown', 1)
        
    def registerFinalizer(self, finalizer):
        self.finalizers.append(finalizer)

    def finalize(self):
        for finalizer in self.finalizers:
            #print "KoFinalizeService: finalizing %r" % finalizer
            finalizer.finalize()

    def observe(self, subject, topic, data):
        if topic == 'xpcom-shutdown':
            log.debug("pref service status got xpcom-shutdown, unloading");
            self.finalize()
 