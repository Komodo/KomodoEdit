# Copyright (c) 2000-2006 ActiveState Software Inc.
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
        WrapObject(self,components.interfaces.nsIObserver)
        self._observerSvc = components.classes["@mozilla.org/observer-service;1"].\
            getService(components.interfaces.nsIObserverService)
        self._observerSvc.addObserver(self,'file_status',0)
        self._observerSvc.addObserver(self,'file_status_updated',0)
        self.lock = threading.Condition()
        self.subject = None
        self.topic = None
        self.URI = None
        
    def observe(self, subject, topic, URI):
        #print "got observe (%s,%s,%s)"%(subject, topic, URI)
        self.lock.acquire()
        self.subject = subject
        self.topic = topic
        self.URI = URI
        self.lock.notify()
        self.lock.release()

class TestKoFileStatusService(unittest.TestCase):
    def __init__(self, methodName):
        unittest.TestCase.__init__(self, methodName)
        self.__fileStatusSvc = components.classes["@activestate.com/koFileStatusService;1"] \
                         .getService(components.interfaces.koIFileStatusService)
        self.__fileStatusSvc.init()
        self.__filesvc = components.classes["@activestate.com/koFileService;1"] \
                         .getService(components.interfaces.koIFileService)

    def __del__(self):
        self.__fileStatusSvc.unload()

    def test_service(self):
        file = self.__filesvc.getFileFromURI(__file__)
        assert file.exists
        self.__fileStatusSvc.getStatus(file)
        assert file.sccDirType == 'p4'

    #def test_background(self):
    #    obs = TestKoFileStatusServiceObserver()
    #    print "acquiring the lock"
    #    obs.lock.acquire()
    #    file = self.__filesvc.getFileFromURI(__file__)
    #    timeout = 10
    #    while obs.subject is None:
    #        obs.lock.wait(1)
    #        timeout -= 1
    #        if not timeout:
    #            print "timed out"
    #            break
    #    # did we succeed?
    #    print obs.subject,obs.topic,obs.URI
    #    ok = obs.subject is file
    #    obs.lock.release()
    #    assert ok

        
#---- mainline

def suite():
    return unittest.makeSuite(TestKoFileStatusService)

def test_main():
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite())

if __name__ == "__main__":
    __file__ = os.path.abspath(sys.argv[0]) # won't be necessary in Python 2.3
    test_main()



