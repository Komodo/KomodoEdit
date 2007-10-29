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

# run service uses koprocessutils, we need to initialize it now
import koprocessutils
koprocessutils.initialize()

prefs = components.classes["@activestate.com/koPrefService;1"].\
    getService(components.interfaces.koIPrefService).prefs
koDirSvc = components.classes["@activestate.com/koDirs;1"].\
    getService(components.interfaces.koIDirs)
dbgpManager = components.classes["@activestate.com/koDBGPManager;1"]\
         .getService(components.interfaces.koIDBGPManager)


class interpolateData:
    def __init__(self,
                 strings=[],
                 bracketedStrings=[],
                 fileName='/home/shanec/test.txt',
                 lineNum=42,
                 word='towel',
                 selection='thanks for all the fish',
                 projectFile='project.kpf',
                 expect=[],
                 answers={}):
        self.strings = strings
        self.bracketedStrings = bracketedStrings
        self._fileName = fileName
        self._lineNum = lineNum
        self._word = word
        self._selection = selection
        self._projectFile = projectFile
        self.expect = expect
        self._answers = answers
        self._interpolate = components.classes["@activestate.com/koInterpolationService;1"] \
                         .getService(components.interfaces.koIInterpolationService)
    
    def getAnswers(self):
        for query in self.resultQueries:
            if query.question in self._answers:
                query.answer = self._answers[query.question]

    def doTest(self):
        self.resultQueries, self.resultStrings = \
                    self._interpolate.Interpolate1(
                                    self.strings,
                                    self.bracketedStrings,
                                    self._fileName,
                                    self._lineNum,
                                    self._word,
                                    self._selection,
                                    self._projectFile,
                                    None)
        if self.resultQueries:
            self.getAnswers()
            self.resultStrings = self._interpolate.Interpolate2(self.resultStrings, self.resultQueries)
            
    

class TestKoInterpolationService(unittest.TestCase):
    
    def test_interpolate(self):
        for interpolateTest in interopateList:
            interpolateTest.doTest()
            self.failUnlessEqual(interpolateTest.expect, interpolateTest.resultStrings,
                "%r != %r" % (interpolateTest.expect, interpolateTest.resultStrings))


#---- mainline

def suite():
    return unittest.makeSuite(TestKoInterpolationService)

def test_main():
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite())

if __name__ == "__main__":
    dbgpManager.start()

    interopateList = [
        interpolateData(strings = ['%F', '%f', '%D', '%d'],
                        bracketedStrings = ['[[%F]]', '[[%f]]', '[[%D]]', '[[%d]]'],
                        expect =  ['/home/shanec/test.txt', 'test.txt',
                                   '/home/shanec', 'shanec',
                                   '/home/shanec/test.txt', 'test.txt',
                                   '/home/shanec', 'shanec']),
    
        # string pref test
        interpolateData(strings = ['%(pref:tidy_errorlevel)'], expect = [prefs.getStringPref('tidy_errorlevel')]),
        # long pref test
        interpolateData(strings = ['%(pref:tabWidth)'], expect = ['%d' % prefs.getLongPref('tabWidth')]),
        # boolean pref test
        interpolateData(strings = ['%(pref:cvsEnabled)'], expect = ['%d' % prefs.getBooleanPref('cvsEnabled')]),
    
        # koIDirs test
        interpolateData(strings = ['%(path:userDataDir)',
                                   '%(path:hostUserDataDir)',
                                   '%(path:commonDataDir)',
                                   '%(path:supportDir)'],
                        expect =  [koDirSvc.userDataDir,
                                   koDirSvc.hostUserDataDir,
                                   koDirSvc.commonDataDir,
                                   koDirSvc.supportDir]),
        
        # test asking for the value
        interpolateData(strings = ['%(ask:User Data Dir:)'],
                        expect =  [koDirSvc.userDataDir],
                        answers = {'User Data Dir': koDirSvc.userDataDir}),
        
        # test asking for the value and returning a default value
        interpolateData(strings = ['%(ask:User Data Dir:'+ koDirSvc.userDataDir +')'],
                        expect =  [koDirSvc.userDataDir]),
    
        # debugger value tests
        interpolateData(strings = ['%(debugger:port)',
                                   '%(debugger:address)',
                                   '%(debugger:proxyPort)',
                                   '%(debugger:proxyAddress)',
                                   '%(debugger:proxyClientPort)',
                                   '%(debugger:proxyClientAddress)',
                                   '%(debugger:proxyKey)',
                                   ],
                        expect = [str(dbgpManager.port),
                                  dbgpManager.address,
                                  str(dbgpManager.proxyPort),
                                  dbgpManager.proxyAddress,
                                  str(dbgpManager.proxyClientPort),
                                  dbgpManager.proxyClientAddress,
                                  prefs.getStringPref('dbgpProxyKey')]),
    ]

    test_main()

    dbgpManager.stop()



