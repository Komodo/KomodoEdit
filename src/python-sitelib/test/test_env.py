"""Test setting the environment for process launch."""

import os
import sys
import re
import pprint
import unittest
import testsupport

import process


class EnvTestCase(unittest.TestCase):
    def test_ProcessProxy_env_unspecified(self):
        talkenv = ''

        p = process.ProcessProxy(['printenv'])
        output = p.stdout.read()

        pattern = re.compile("TALK_ENV is '(.*?)'")
        match = pattern.search(output)
        self.failUnless(match, "Could not find '%s' in 'printenv' output: "\
                               "output=%r" % (pattern.pattern, output))
        self.failUnless(match.group(1) == talkenv,
                        "%r != %r" % (match.group(1), talkenv))

    def test_ProcessProxy_env_inherited(self):
        talkenv = 'foo'
        os.environ['TALK_ENV'] = 'foo'

        p = process.ProcessProxy(['printenv'])
        output = p.stdout.read()

        pattern = re.compile("TALK_ENV is '(.*?)'")
        match = pattern.search(output)
        self.failUnless(match, "Could not find '%s' in 'printenv' output: "\
                               "output=%r" % (pattern.pattern, output))
        self.failUnless(match.group(1) == talkenv,
                        "%r != %r" % (match.group(1), talkenv))

        os.environ['TALK_ENV'] = ''

    def test_ProcessProxy_env_specified(self):
        talkenv = 'bar'
        env = {'TALK_ENV': talkenv}

        p = process.ProcessProxy(['printenv'], env=env)
        output = p.stdout.read()

        pattern = re.compile("TALK_ENV is '(.*?)'")
        match = pattern.search(output)
        self.failUnless(match, "Could not find '%s' in 'printenv' output: "\
                               "output=%r" % (pattern.pattern, output))
        self.failUnless(match.group(1) == talkenv,
                        "%r != %r" % (match.group(1), talkenv))

    def test_ProcessProxy_env_overridden(self):
        os.environ['TALK_ENV'] = 'spam'
        talkenv = 'eggs'
        env = {'TALK_ENV': talkenv}

        p = process.ProcessProxy(['printenv'], env=env)
        output = p.stdout.read()

        pattern = re.compile("TALK_ENV is '(.*?)'")
        match = pattern.search(output)
        self.failUnless(match, "Could not find '%s' in 'printenv' output: "\
                               "output=%r" % (pattern.pattern, output))
        self.failUnless(match.group(1) == talkenv,
                        "%r != %r" % (match.group(1), talkenv))

        self.failUnless(os.environ['TALK_ENV'] == 'spam')
        os.environ['TALK_ENV'] = ''

    def test_ProcessOpen_env_unspecified(self):
        talkenv = ''

        p = process.ProcessOpen(['printenv'])
        output = p.stdout.read()

        pattern = re.compile("TALK_ENV is '(.*?)'")
        match = pattern.search(output)
        self.failUnless(match, "Could not find '%s' in 'printenv' output: "\
                               "output=%r" % (pattern.pattern, output))
        self.failUnless(match.group(1) == talkenv,
                        "%r != %r" % (match.group(1), talkenv))

    def test_ProcessOpen_env_inherited(self):
        talkenv = 'foo'
        os.environ['TALK_ENV'] = 'foo'

        p = process.ProcessOpen(['printenv'])
        output = p.stdout.read()

        pattern = re.compile("TALK_ENV is '(.*?)'")
        match = pattern.search(output)
        self.failUnless(match, "Could not find '%s' in 'printenv' output: "\
                               "output=%r" % (pattern.pattern, output))
        self.failUnless(match.group(1) == talkenv,
                        "%r != %r" % (match.group(1), talkenv))

        os.environ['TALK_ENV'] = ''

    def test_ProcessOpen_env_specified(self):
        talkenv = 'bar'
        env = {'TALK_ENV': talkenv}

        p = process.ProcessOpen(['printenv'], env=env)
        output = p.stdout.read()

        pattern = re.compile("TALK_ENV is '(.*?)'")
        match = pattern.search(output)
        self.failUnless(match, "Could not find '%s' in 'printenv' output: "\
                               "output=%r" % (pattern.pattern, output))
        self.failUnless(match.group(1) == talkenv,
                        "%r != %r" % (match.group(1), talkenv))

    def test_ProcessOpen_env_overridden(self):
        os.environ['TALK_ENV'] = 'spam'
        talkenv = 'eggs'
        env = {'TALK_ENV': talkenv}

        p = process.ProcessOpen(['printenv'], env=env)
        output = p.stdout.read()

        pattern = re.compile("TALK_ENV is '(.*?)'")
        match = pattern.search(output)
        self.failUnless(match, "Could not find '%s' in 'printenv' output: "\
                               "output=%r" % (pattern.pattern, output))
        self.failUnless(match.group(1) == talkenv,
                        "%r != %r" % (match.group(1), talkenv))

        self.failUnless(os.environ['TALK_ENV'] == 'spam')
        os.environ['TALK_ENV'] = ''


def suite():
    """Return a unittest.TestSuite to be used by test.py."""
    return unittest.makeSuite(EnvTestCase)

if __name__ == "__main__":
    import logging
    logging.basicConfig()
    testsupport.setup()
    sys.argv.insert(1, "-v") # always want verbose output
    unittest.main()

