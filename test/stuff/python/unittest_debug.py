# Copyright (c) 2000-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

import sys
import unittest


class TestDebugger(unittest.TestCase):
    def test_assert(self):
        x = 0
        for i in range(10):
            x = x + 1
            print "hello unittest ", x
        assert 1

    def test_success(self):
        assert 1

#---- mainline

def suite():
    suites = []
    suites.append( unittest.makeSuite(TestDebugger) )
    return unittest.TestSuite(suites)

def test_main():
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite())

if __name__ == "__main__":
    __file__ = sys.argv[0] # won't be necessary in Python 2.3
    test_main()



