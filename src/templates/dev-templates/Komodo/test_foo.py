#!/usr/bin/env python
# Copyright (C) [[%date:%Y]] ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

"""Komodo test script for: [[%tabstop1:foo]]. [[%tabstop:# what to test (lowercase, no spaces)]]

TODO:
- Say that you are test the new Komodo "whizbang" feature.
- Copy this file to "test/suite/test_whizbang.py".
- p4 add test_whizbang.py
- s/foo/whizbang/g
- s/Foo/Whizbang/g
- Change test_spam() and test_eggs(), below, to useful tests.
- Update suite() as appropriate. (Do you have one or multiple TestCase
  classes? Do you want to filter on tags?)
"""

# You can define extra tags for this test module that will be used for
# `bk test [TAGS...]` filtering. By default the module name (i.e. "dbgp"
# for "test_dbgp.py") will always be a tag.
#
#__tags__ = ['bar', 'baz']

import os
import sys
import unittest
import logging

from testsupport import get_config, TestError, TestSkipped, verbose



class [[%tabstop:]]TestCase(unittest.TestCase):
    # define test methods here...
    def test_spam(self):
        self.failUnless(1, "Wow!")
    def test_eggs(self):
        self.failUnlessRaises(ZeroDivisionError, lambda: 1/0)


#---- mainline

def suite(tags=[]):
    #TODO: If you have one TestCase...
    return unittest.makeSuite(FooTestCase)
    #TODO: ... or if you have multiple TestCase's:
    suites = []
    suites.append( unittest.makeSuite(FooTestCase) )
    suites.append( unittest.makeSuite(BarTestCase) )
    #TODO: You may also filter on tag names.
    return unittest.TestSuite(suites)

def test_main():
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite())

if __name__ == "__main__":
    test_main()

