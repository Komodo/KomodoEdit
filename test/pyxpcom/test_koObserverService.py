# Copyright (c) 2003-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

from xpcom import components, COMException
from xpcom.server import WrapObject, UnwrapObject

import unittest



class TestObserver:
    """a simple observer class"""
    _com_interfaces_ = [components.interfaces.nsIObserver]
    
    def __init__(self):
        self.observed = None
        
    def observe(self, aSubject, aTopic, aData):
        self.observed = (aSubject,aTopic,aData)
        

class TestKoObserverService(unittest.TestCase):
    def __init__(self, methodName):
        unittest.TestCase.__init__(self, methodName)
        self.observerSvc = components.classes['@activestate.com/koObserverService;1'].\
                           getService(components.interfaces.nsIObserverService)

    # test creating, adding, notifying, and removing an observer
    def test_doObserver(self):
        testobserver = TestObserver()
        xpobs = WrapObject(testobserver,components.interfaces.nsIObserver)
        self.observerSvc.addObserver(xpobs,'test',0)
        self.observerSvc.notifyObservers(None,'test','Testing')
        assert testobserver.observed == (None,'test','Testing')
        enum = self.observerSvc.enumerateObservers('test')
        assert enum.getNext() == xpobs
        enum = None
        self.observerSvc.removeObserver(xpobs,'test')
        enum = self.observerSvc.enumerateObservers('test')
        assert not enum.hasMoreElements()

    # test creating, adding, notifying, and deleting an observer without removal
    def test_doObserverWeakRef(self):
        testobserver = TestObserver()
        xpobs = WrapObject(testobserver,components.interfaces.nsIObserver)
        self.observerSvc.addObserver(xpobs,'test',0)
        self.observerSvc.notifyObservers(None,'test','Testing')
        assert testobserver.observed == (None,'test','Testing')
        enum = self.observerSvc.enumerateObservers('test')
        assert enum.getNext() == xpobs
        enum = None
        xpobs = None
        testobserver = None
        enum = self.observerSvc.enumerateObservers('test')
        assert not enum.hasMoreElements()

    # test creating, adding, notifying, and deleting an observer without removal
    def test_doObserverGlobal(self):
        testobserver = TestObserver()
        xpobs = WrapObject(testobserver,components.interfaces.nsIObserver)
        self.observerSvc.addObserver(xpobs,'',0)
        self.observerSvc.notifyObservers(None,'test','Testing')
        assert testobserver.observed == (None,'test','Testing')
        self.observerSvc.notifyObservers(None,'anothertest','Testing')
        assert testobserver.observed == (None,'anothertest','Testing')
        enum = self.observerSvc.enumerateObservers('')
        assert enum.getNext() == xpobs
        enum = None
        xpobs = None
        testobserver = None
        enum = self.observerSvc.enumerateObservers('')
        assert not enum.hasMoreElements()

    # test notifying non-existent observers
    def test_noObserversToNotify(self):
        self.observerSvc.notifyObservers(None,'does-not-exist','Testing')

    # test removing non-existent observers
    def test_noObserversToRemove(self):
        testobserver = TestObserver()
        xpobs = WrapObject(testobserver,components.interfaces.nsIObserver)
        self.observerSvc.removeObserver(xpobs,'test')


#---- mainline

def suite():
    return unittest.makeSuite(TestKoObserverService)

def test_main():
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite())

if __name__ == "__main__":
    test_main() 

