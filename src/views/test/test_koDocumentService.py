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
import sys

from xpcom import components, COMException
from xpcom.server import WrapObject, UnwrapObject


class TestKoDocumentService(unittest.TestCase):
    def __init__(self, methodName):
        unittest.TestCase.__init__(self, methodName)
        
        self.__docsvc = components.classes["@activestate.com/koDocumentService;1"] \
                        .getService(components.interfaces.koIDocumentService)
        self.__filesvc = components.classes["@activestate.com/koFileService;1"] \
                         .getService(components.interfaces.koIFileService)

        # Grab a reference to the global preference service.  this
        # forces prefs to startup
        _globalPrefsvc = components.classes["@activestate.com/koPrefService;1"].\
                         getService(components.interfaces.koIPrefService)

    def __del__(self):
        UnwrapObject(self.__docsvc).shutdownAutoSave()

    def test_createDocumentFromURI(self):
        filename = os.__file__ # returns os.pyc
        doc = self.__docsvc.createDocumentFromURI(filename)
        doc.addReference()
        assert doc.file.exists
        docs = self.__docsvc.getAllDocuments()
        assert doc in docs
        xdoc = self.__docsvc.findDocumentByURI(doc.file.URI)
        assert doc == xdoc
        doc.releaseReference()
        docs = self.__docsvc.getAllDocuments()
        assert len(docs) == 0

    def test_createUntitledDocument(self):
        doc = self.__docsvc.createUntitledDocument('Python')
        doc.addReference()
        assert doc.baseName == 'Python-1.py', "%s != %s" % (doc.baseName, 'Python-1.py')
        docs = self.__docsvc.getAllDocuments()
        assert doc in docs
        xdoc = self.__docsvc.findDocumentByURI('Python-1.py')
        assert doc == xdoc
        doc.releaseReference()
        docs = self.__docsvc.getAllDocuments()
        assert len(docs) == 0

#---- mainline

def suite():
    return unittest.makeSuite(TestKoDocumentService)

def test_main():
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite())

if __name__ == "__main__":
    test_main()




