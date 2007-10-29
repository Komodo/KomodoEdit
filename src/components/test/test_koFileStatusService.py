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



