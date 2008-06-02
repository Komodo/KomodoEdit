# Copyright (c) 2000-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.


import os
import unittest
import sys

from xpcom import components, COMException

if __name__ == "__main__":
    koInitSvc = components.classes["@activestate.com/koInitService;1"].\
    getService(components.interfaces.koIInitService)
    koInitSvc.setEncoding()

import koprocessutils
koprocessutils.initialize()

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
        for interpolateTest in interpolateList:
            interpolateTest.doTest()
            zres = zip(interpolateTest.expect, interpolateTest.resultStrings)
            i = 1
            for exp, rec in zres:
                if exp != rec:
                    print "Failed test %d: expected\n%r, got\n%r" % (i,
                                                               str(exp),
                                                               str(rec))
                i += 1
                                                                   
            self.failUnlessEqual(interpolateTest.expect, interpolateTest.resultStrings,
                "%r != %r" % (interpolateTest.expect, interpolateTest.resultStrings))


def suite():
    return unittest.makeSuite(TestKoInterpolationService)

def test_main():
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite())

if __name__ == "__main__":
    template = "@ 1\n@  2\n@   3"
    res_template = template + "\n"
    interpolateList = [
        # multiple selection lines
        interpolateData(strings = [],
                        bracketedStrings = ['[[%s]]\n [[%s]]\n     [[%s]]\n'],
                        selection = template.replace('@', ''),
                        expect =  [
                                   (res_template.replace('@', '')
                                   + res_template.replace('@', ' ' * 1)
                                   + res_template.replace('@', ' ' * 5))] * 2
                         ),
        # Mix tabs and spaces
        interpolateData(strings = [],
                        bracketedStrings = ['[[%s]]\n \t\t[[%s]]\n'],
                        selection = template.replace('@', ''),
                        expect =  [
                                   (res_template.replace('@', '')
                                   + res_template.replace('@', ' \t\t'))] * 2
                         ),
        # crlf / crlf
        interpolateData(strings = ['   %s'],
                        bracketedStrings = ['   [[%s]]'],
                        selection = "cashew\r\n  brazil\r\nalmonds",
                        expect =  [
                                   "   cashew\r\n  brazil\r\nalmonds",
                                   "   cashew\r\n  brazil\r\nalmonds",
                                   "   cashew\r\n     brazil\r\n   almonds",
                                   "   cashew\r\n     brazil\r\n   almonds",
                                   ]),
        # lf / lf
        interpolateData(strings = ['   %s'],
                        bracketedStrings = ['   [[%s]]'],
                        selection = "cashew\n  brazil\nalmonds",
                        expect =  [
                                   "   cashew\n  brazil\nalmonds",
                                   "   cashew\n  brazil\nalmonds",
                                   "   cashew\n     brazil\n   almonds",
                                   "   cashew\n     brazil\n   almonds",
                                   ]),
        # crlf / lf
        interpolateData(strings = ['if (1) {\r\n    %s\r\n}'],
                        bracketedStrings = ['if (1) {\r\n    [[%s]]\r\n}'],
                        selection = "cashew\n  brazil\nalmonds",
                        expect =  [
                                   'if (1) {\r\n    cashew\n  brazil\nalmonds\r\n}',
                                   'if (1) {\r\n    cashew\n  brazil\nalmonds\r\n}',
                                   'if (1) {\r\n    cashew\n      brazil\n    almonds\r\n}',
                                   'if (1) {\r\n    cashew\n      brazil\n    almonds\r\n}',
                                   ]),
        # lf / crlf
        interpolateData(strings = ['if (1) {\n    %s\n}'],
                        bracketedStrings = ['if (1) {\n    [[%s]]\n}'],
                        selection = "cashew\r\n  brazil\r\nalmonds",
                        expect =  [
                                   'if (1) {\n    cashew\r\n  brazil\r\nalmonds\n}',
                                   'if (1) {\n    cashew\r\n  brazil\r\nalmonds\n}',
                                   'if (1) {\n    cashew\r\n      brazil\r\n    almonds\n}',
                                   'if (1) {\n    cashew\r\n      brazil\r\n    almonds\n}',
                                   ]),
        ]

    test_main()
