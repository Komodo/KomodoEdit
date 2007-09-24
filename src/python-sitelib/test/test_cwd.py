"""Test setting the current working dir for process launch."""

import os
import sys
import re
import pprint
import unittest
import testsupport

import process


class CwdTestCase(unittest.TestCase):
    def test_ProcessProxy_cwd_notspecified(self):
        cwd = os.getcwd()

        p = process.ProcessProxy(['printcwd'])
        output = p.stdout.read()

        pattern = re.compile("CWD is '(.*?)'")
        match = pattern.search(output)
        self.failUnless(match, "Could not find '%s' in 'printcwd' output: "\
                               "output=%r" % (pattern.pattern, output))
        self.failUnless(match.group(1) == cwd,
                        "%r != %r" % (match.group(1), cwd))

    def test_ProcessProxy_cwd_specified(self):
        wd = os.path.expanduser('~')

        p = process.ProcessProxy(['printcwd'], cwd=wd)
        output = p.stdout.read()

        pattern = re.compile("CWD is '(.*?)'")
        match = pattern.search(output)
        self.failUnless(match, "Could not find '%s' in 'printcwd' output: "\
                               "output=%r" % (pattern.pattern, output))
        actual = os.path.normcase(match.group(1))
        expected = os.path.normcase(wd)
        self.failUnless(actual == expected,
                        "%r != %r" % (actual, expected))

    def test_ProcessProxy_cwd_specified_doesnotexist(self):
        wd = "foobar"
        self.failUnlessRaises(process.ProcessError, process.ProcessProxy,
                              cmd=['printcwd'], cwd=wd)

    def test_ProcessProxy_cwd_specified_relative(self):
        wd = "mytmprelativedir"
        testsupport.mkdir(wd)

        p = process.ProcessProxy(['printcwd'], cwd=wd)
        output = p.stdout.read()

        pattern = re.compile("CWD is '(.*?)'")
        match = pattern.search(output)
        self.failUnless(match, "Could not find '%s' in 'printcwd' output: "\
                               "output=%r" % (pattern.pattern, output))
        self.failUnless(match.group(1) == os.path.abspath(wd),
                        "%r != %r" % (match.group(1), os.path.abspath(wd)))
    
        testsupport.rmtree(wd)

    def test_ProcessProxy_cwd_specified_withspaces(self):
        wd = "my tmp relative dir with spaces"
        testsupport.mkdir(wd)

        p = process.ProcessProxy(['printcwd'], cwd=wd)
        output = p.stdout.read()

        pattern = re.compile("CWD is '(.*?)'")
        match = pattern.search(output)
        self.failUnless(match, "Could not find '%s' in 'printcwd' output: "\
                               "output=%r" % (pattern.pattern, output))
        self.failUnless(match.group(1) == os.path.abspath(wd),
                        "%r != %r" % (match.group(1), os.path.abspath(wd)))
    
        testsupport.rmtree(wd)

    def test_ProcessOpen_cwd_notspecified(self):
        cwd = os.getcwd()

        p = process.ProcessOpen(['printcwd'])
        output = p.stdout.read()

        pattern = re.compile("CWD is '(.*?)'")
        match = pattern.search(output)
        self.failUnless(match, "Could not find '%s' in 'printcwd' output: "\
                               "output=%r" % (pattern.pattern, output))
        self.failUnless(match.group(1) == cwd,
                        "%r != %r" % (match.group(1), cwd))

    def test_ProcessOpen_cwd_specified(self):
        wd = os.path.expanduser('~')

        p = process.ProcessOpen(['printcwd'], cwd=wd)
        output = p.stdout.read()

        pattern = re.compile("CWD is '(.*?)'")
        match = pattern.search(output)
        self.failUnless(match, "Could not find '%s' in 'printcwd' output: "\
                               "output=%r" % (pattern.pattern, output))
        actual = os.path.normcase(match.group(1))
        expected = os.path.normcase(wd)
        self.failUnless(actual == expected,
                        "%r != %r" % (actual, expected))

    def test_ProcessOpen_cwd_specified_doesnotexist(self):
        wd = "foobar"
        self.failUnlessRaises(process.ProcessError, process.ProcessOpen,
                              cmd=['printcwd'], cwd=wd)

    def test_ProcessOpen_cwd_specified_relative(self):
        wd = "mytmprelativedir"
        testsupport.mkdir(wd)

        p = process.ProcessOpen(['printcwd'], cwd=wd)
        output = p.stdout.read()

        pattern = re.compile("CWD is '(.*?)'")
        match = pattern.search(output)
        self.failUnless(match, "Could not find '%s' in 'printcwd' output: "\
                               "output=%r" % (pattern.pattern, output))
        self.failUnless(match.group(1) == os.path.abspath(wd),
                        "%r != %r" % (match.group(1), os.path.abspath(wd)))
    
        testsupport.rmtree(wd)


def suite():
    """Return a unittest.TestSuite to be used by test.py."""
    return unittest.makeSuite(CwdTestCase)

if __name__ == "__main__":
    import logging
    logging.basicConfig()
    testsupport.setup()
    sys.argv.insert(1, "-v") # always want verbose output
    unittest.main()

