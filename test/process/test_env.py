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

