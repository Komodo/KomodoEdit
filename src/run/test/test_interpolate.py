# Copyright (c) 2000-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.


import unittest

from xpcom import components

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
        # Make expect a doubled list: from (1, 2, 3) we make (1, 1, 2, 2, 3, 3).
        self.expect = [item for sublist in zip(expect, expect) for item in sublist]
        self._answers = answers
        self._interpolate = components.classes["@activestate.com/koInterpolationService;1"] \
                         .getService(components.interfaces.koIInterpolationService)
    
    def getAnswers(self):
        for query in self.resultQueries:
            if query.question in self._answers:
                query.answer = self._answers[query.question]

    def doTest(self, testcase):
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

        testcase.failUnlessEqual(self.expect, self.resultStrings)


class TestKoInterpolationService(unittest.TestCase):
    def setUp(self):
        prefs = components.classes["@activestate.com/koPrefService;1"].\
            getService(components.interfaces.koIPrefService).prefs
        koDirSvc = components.classes["@activestate.com/koDirs;1"].\
            getService(components.interfaces.koIDirs)

        interpolateData(strings = ['%F', '%f', '%D', '%d'],
                        bracketedStrings = ['[[%F]]', '[[%f]]', '[[%D]]', '[[%d]]'],
                        expect =  ['/home/shanec/test.txt', 'test.txt',
                                   '/home/shanec', 'shanec',
                                   '/home/shanec/test.txt', 'test.txt',
                                   '/home/shanec', 'shanec'])\
                       .doTest(self)

        # string pref test
        interpolateData(strings = ['%(pref:tidy_errorlevel)'], expect = [prefs.getStringPref('tidy_errorlevel')]),
        # long pref test
        interpolateData(strings = ['%(pref:tabWidth)'], expect = ['%d' % prefs.getLongPref('tabWidth')]),
        # boolean pref test
        interpolateData(strings = ['%(pref:useTabs)'], expect = ['%d' % prefs.getBooleanPref('useTabs')]),
    
        # koIDirs test
        interpolateData(strings = ['%(path:userDataDir)',
                                   '%(path:commonDataDir)',
                                   '%(path:supportDir)'],
                        expect =  [koDirSvc.userDataDir,
                                   koDirSvc.commonDataDir,
                                   koDirSvc.supportDir])\
                       .doTest(self)

        # test asking for the value
        interpolateData(strings = ['%(ask:User Data Dir:)'],
                        expect =  [koDirSvc.userDataDir],
                        answers = {'User Data Dir': koDirSvc.userDataDir})\
                       .doTest(self)

        # test asking for the value and returning a default value
        interpolateData(strings = ['%(ask:User Data Dir:'+ koDirSvc.userDataDir +')'],
                        expect =  [koDirSvc.userDataDir])\
                       .doTest(self)

    def test_interpolate_content(self):
        template = "@ 1\n@  2\n@   3"
        res_template = template + "\n"

        # multiple selection lines
        interpolateData(bracketedStrings = ['[[%s]]\n [[%s]]\n     [[%s]]\n'],
                        selection = template.replace('@', ''),
                        expect =  [
                                   (res_template.replace('@', '')
                                   + res_template.replace('@', ' ')
                                   + res_template.replace('@', ' ' * 5))]
                        ).doTest(self)
        # Mix tabs and spaces
        interpolateData(bracketedStrings = ['[[%s]]\n \t\t[[%s]]\n'],
                        selection = template.replace('@', ''),
                        expect =  [
                                   (res_template.replace('@', '')
                                   + res_template.replace('@', ' \t\t'))]
                        ).doTest(self)
        # crlf / crlf
        interpolateData(strings = ['   %s'],
                        bracketedStrings = ['   [[%s]]'],
                        selection = "cashew\r\n  brazil\r\nalmonds",
                        expect =  [
                                   "   cashew\r\n  brazil\r\nalmonds",
                                   "   cashew\r\n     brazil\r\n   almonds",
                                   ]
                        ).doTest(self)
        # lf / lf
        interpolateData(strings = ['   %s'],
                        bracketedStrings = ['   [[%s]]'],
                        selection = "cashew\n  brazil\nalmonds",
                        expect =  [
                                   "   cashew\n  brazil\nalmonds",
                                   "   cashew\n     brazil\n   almonds",
                                   ]
                        ).doTest(self)
        # crlf / lf
        interpolateData(strings = ['if (1) {\r\n    %s\r\n}'],
                        bracketedStrings = ['if (1) {\r\n    [[%s]]\r\n}'],
                        selection = "cashew\n  brazil\nalmonds",
                        expect =  [
                                   'if (1) {\r\n    cashew\n  brazil\nalmonds\r\n}',
                                   'if (1) {\r\n    cashew\n      brazil\n    almonds\r\n}',
                                   ]
                        ).doTest(self)
        # lf / crlf
        interpolateData(strings = ['if (1) {\n    %s\n}'],
                        bracketedStrings = ['if (1) {\n    [[%s]]\n}'],
                        selection = "cashew\r\n  brazil\r\nalmonds",
                        expect =  [
                                   'if (1) {\n    cashew\r\n  brazil\r\nalmonds\n}',
                                   'if (1) {\n    cashew\r\n      brazil\r\n    almonds\n}',
                                   ]
                        ).doTest(self)

    def test_interpolate_python3(self):
        prefs = components.classes["@activestate.com/koPrefService;1"].\
            getService(components.interfaces.koIPrefService).prefs
        orig_py3exe = prefs.getString("python3DefaultInterpreter")
        prefs.setStringPref("python3DefaultInterpreter", __file__)
        try:
            interpolateTest = interpolateData(strings=['%python3'],
                                              expect=[__file__])
            interpolateTest.doTest(self)
        finally:
            prefs.setStringPref("python3DefaultInterpreter", orig_py3exe)

    def test_interpolate_nodejs(self):
        prefs = components.classes["@activestate.com/koPrefService;1"].\
            getService(components.interfaces.koIPrefService).prefs
        orig_node_exe = prefs.getString("nodejsDefaultInterpreter")
        prefs.setStringPref("nodejsDefaultInterpreter", __file__)
        try:
            interpolateTest = interpolateData(strings=['%node'],
                                              expect=[__file__])
            interpolateTest.doTest(self)
            interpolateTest = interpolateData(strings=['%nodejs'],
                                              expect=[__file__])
            interpolateTest.doTest(self)
            interpolateTest = interpolateData(strings=['%node.js'],
                                              expect=[__file__])
            interpolateTest.doTest(self)
        finally:
            prefs.setStringPref("nodejsDefaultInterpreter", orig_node_exe)
