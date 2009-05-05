# Copyright (c) 2000-2009 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.


import os
import unittest
import sys, time

from xpcom import components, COMException
from xpcom.server import WrapObject, UnwrapObject

import threading

class TestKoFileStatusServiceObserver:
    _com_interfaces_ = [components.interfaces.nsIObserver]
    
    def __init__(self):
        self.lock = threading.Condition()
        self.clear()
        observerSvc = components.classes["@mozilla.org/observer-service;1"].\
            getService(components.interfaces.nsIObserverService)
        self.__wrappedSelf = WrapObject(self, components.interfaces.nsIObserver)
        observerSvc.addObserver(self.__wrappedSelf, 'file_status', 0)

    def __del__(self):
        observerSvc = components.classes["@mozilla.org/observer-service;1"].\
            getService(components.interfaces.nsIObserverService)
        observerSvc.removeObserver(self.__wrappedSelf, 'file_status')

    def clear(self):
        self.lock.acquire()
        try:
            self.subject = None
            self.topic = None
            self.updated_uris = set()
        finally:
            self.lock.release()

    def observe(self, subject, topic, data):
        #print "got observe (%s,%s,%s)"%(subject, topic, URI)
        self.lock.acquire()
        try:
            self.subject = subject
            self.topic = topic
            for URI in data.split("\n"):
                print "Got a file_status notification: %r" % (URI, )
                self.updated_uris.add(URI)
            self.lock.notifyAll()
        finally:
            self.lock.release()

class TestKoFileStatusService(unittest.TestCase):
    def __init__(self, methodName):
        unittest.TestCase.__init__(self, methodName)
        self.__obs = TestKoFileStatusServiceObserver()
        self.__fileStatusSvc = components.classes["@activestate.com/koFileStatusService;1"] \
                         .getService(components.interfaces.koIFileStatusService)
        from xpcom.server import UnwrapObject
        UnwrapObject(self.__fileStatusSvc).init()
        self.__filesvc = components.classes["@activestate.com/koFileService;1"] \
                         .getService(components.interfaces.koIFileService)

    def __del__(self):
        self.__fileStatusSvc.unload()

    def setUp(self):
        self.__obs.clear()

    def test_service(self):
        if sys.platform.startswith("win"):
            uri = "file:///" + os.path.abspath(__file__).replace("\\", "/")
        else:
            uri = "file://" + os.path.abspath(__file__)
        file = self.__filesvc.getFileFromURI(uri)
        assert file.exists
        self.__fileStatusSvc.updateStatusForFiles([file], False)
        # Give some time to get the status.
        # Note: Edit does not have scc handling.
        #self.__obs.lock.acquire()
        #try:
        #    # XXX: The observer does not work in a standalone environment,
        #    #      not sure why, so this will *always* wait 3 seconds.
        #    self.__obs.lock.wait(3)
        #finally:
        #    self.__obs.lock.release()
        #assert file.sccDirType == 'svn'
        #assert file.sccType == 'svn'

#---- mainline

def suite():
    return unittest.makeSuite(TestKoFileStatusService)

def test_main():
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite())

if __name__ == "__main__":
    __file__ = os.path.abspath(sys.argv[0]) # won't be necessary in Python 2.3
    test_main()
