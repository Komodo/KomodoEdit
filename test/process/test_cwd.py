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

