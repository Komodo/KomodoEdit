#!/usr/bin/env python
# Copyright (c) 2000-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

"""Komodo-specific nsIObserverService implementation to allow the
notify/observe mechanism to be scoped on an object.

Mozilla's nsIObserverService implementation (@mozilla.org/observer-service;1)
is a global thang. This makes it inconvenient to use to pass notifications
to a specific instance of an object if there are many of them. For example:
to notify a specific Komodo document that its encoding has changed via the
global nsIObserverService would require a global listener that would then
pass the notification onto the document instance. If, however, we have a
koObserverService instance attached to the document we can call
.notifyObservers() on it and only registered observers on that particular
document will be bothered by it.

Note: The suffix "Service" on koObserverService is a misnomer because it is
NOT to be used as a service, there must be one instance per user. I.e.
createInstance() must be used instead of getService().
"""

from xpcom import components, ServerException, COMException, nsError
from xpcom.client import WeakReference
from xpcom.server.enumerator import SimpleEnumerator

import threading
import logging
log = logging.getLogger('KoObserverService')
#log.setLevel(logging.DEBUG)

# a base class to implement observer services

class KoObserverService:
    _com_interfaces_ = [components.interfaces.nsIObserverService]
    _reg_clsid_ = "3B7D0418-1533-4F03-A759-896C058A734A"
    _reg_contractid_ = "@activestate.com/koObserverService;1"
    _reg_desc_ = "Komodo Python Observer Service"
    
    def __init__(self):
        self._topics = {}
        self.cv = threading.Condition()

    # returns list of observers that are not dead
    def _getLiveObservers(self, topic):
        L = []
        if topic not in self._topics:
            return L
        for wr in self._topics[topic]:
            try:
                if not callable(wr) or wr() is not None:
                    L.append(wr)
            except Exception, e:
                # bug 72807, pyxpcom failure on trunk
                log.exception(e)
        return L

    # returns list of strong refs for observers in topic
    def _getObservers(self, topic):
        L = []
        if topic not in self._topics:
            return L
        for wr in self._topics[topic]:
            o = None
            if callable(wr):
                o = wr()
            else:
                o = wr
            if o is not None:
                L.append(o)
        return L
    
    def _removeDead(self):
        for topic in self._topics:
            self._topics[topic] = self._getLiveObservers(topic)
                
    # void addObserver( in nsIObserver anObserver, in string aTopic, in boolean ownsWeak);
    def addObserver(self, anObserver, aTopic, ownsWeak):
        if not anObserver:
            raise ServerException(nsError.NS_ERROR_FAILURE,"Invalid Observer")
        self.cv.acquire()
        try:
            if not aTopic in self._topics:
                self._topics[aTopic] = []
            else:
                self._removeDead()
    
            try:
                anObserver = WeakReference(anObserver)
            except COMException:
                pass
            self._topics[aTopic].append(anObserver)
        finally:
            self.cv.release()
    
    # void removeObserver( in nsIObserver anObserver, in string aTopic );
    def removeObserver(self, anObserver, aTopic):
        self.cv.acquire()
        try:
            self._removeDead()
            if aTopic in self._topics:
                # get non-weakref'd list of observers so
                # we can compare the observer we got with
                # that list.  This list (observers) will be the same
                # size/order as the original (self._topics[aTopic])
                # so we can use the index from the new to delete from
                # the old.  probably need to deal with thread safety here
                observers = self._getObservers(aTopic)
                if anObserver in observers:
                    del self._topics[aTopic][observers.index(anObserver)]
                else:
                    raise ServerException(nsError.NS_ERROR_FAILURE,"Observer not in topic list %s"%aTopic)
            else:
                raise ServerException(nsError.NS_ERROR_FAILURE,"No Observers for Topic %s"%aTopic)
        finally:
            self.cv.release()
    
    #void notifyObservers( in nsISupports aSubject, 
    #                      in string aTopic, 
    #                      in wstring someData );
    def notifyObservers(self, aSubject, aTopic, someData):
        self.cv.acquire()
        try:
            self._removeDead()
        finally:
            self.cv.release()
        ok = 0
        if aTopic and aTopic in self._topics:
            self.cv.acquire()
            try:
                observers = self._getObservers(aTopic)
            finally:
                self.cv.release()
            for observer in observers:
                if observer:
                    try:
                        observer.observe(aSubject, aTopic, someData)
                    except:
                        log.debug("Caught Exception on observe: %s:%s"%(aTopic, someData))
                        #raise
                    ok = 1

        # a twist, we an empty topic is global and recieves all
        # notifications!
        if '' in self._topics:
            self.cv.acquire()
            try:
                observers = self._getObservers('')
            finally:
                self.cv.release()
            for observer in observers:
                if observer:
                    try:
                        observer.observe(aSubject, aTopic, someData)
                    except:
                        log.debug("Caught Exception on observe: %s:%s"%(aTopic, someData))
                        raise
                    ok = 1
        
        if not ok:
            raise ServerException(nsError.NS_ERROR_FAILURE,"No Observers for Topic %s"%aTopic)
    
    # nsISimpleEnumerator enumerateObservers( in string aTopic );
    def enumerateObservers(self, aTopic):
        self.cv.acquire()
        try:
            self._removeDead()
            vals = self._getObservers(aTopic)
        finally:
            self.cv.release()
        return SimpleEnumerator(vals)

