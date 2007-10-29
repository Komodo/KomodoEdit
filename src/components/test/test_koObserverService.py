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
# Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
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
        try:
            self.observerSvc.notifyObservers(None,'does-not-exist','Testing')
            assert 0
        except COMException, e:
            pass

    # test removing non-existent observers
    def test_noObserversToRemove(self):
        testobserver = TestObserver()
        xpobs = WrapObject(testobserver,components.interfaces.nsIObserver)
        try:
            self.observerSvc.removeObserver(xpobs,'test')
            assert 0
        except COMException, e:
            pass


#---- mainline

def suite():
    return unittest.makeSuite(TestKoObserverService)

def test_main():
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite())

if __name__ == "__main__":
    test_main() 

