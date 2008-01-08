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

"""Test simple stdout (and stderr) hookup in spawning a child process."""

import os
import sys
import time
import pprint
import unittest

import process


class MyOutFile:
    def __init__(self):
        self.log = []
    def write(self, text):
        self.log.append( (time.time(), 'write', text) )
    def close(self):
        self.log.append( (time.time(), 'close', None) )
    def getOutput(self):
        output = ''
        for timestamp, event, data in self.log:
            if event == 'write':
                output += data
        return output

class StdoutTestCase(unittest.TestCase):
    def test_ProcessProxy_stdout_buffer(self):
        p = process.ProcessProxy(['talk'])
        output = p.stdout.read()
        self.failUnless(output == 'o0o1o2o3o4')
        error = p.stderr.read()
        self.failUnless(error == 'e0e1e2e3e4')

    def test_ProcessProxy_my_stdout_with_buffered_child(self):
        p = process.ProcessProxy(['talk'], stdout=MyOutFile(),
                                 stderr=MyOutFile())
        p.wait()
        p.close()
        output = p.stdout.getOutput()
        error = p.stderr.getOutput()
        self.failUnless(output == 'o0o1o2o3o4')
        self.failUnless(error == 'e0e1e2e3e4')

        #XXX Cannot test this part until the setvbuf work is done to
        #    make the child pipes unbuffered. Update: even with the
        #    setvbuf calls (done via os.fdopen(..., bufsize=0)) stdout
        #    and stderr do *not* seem to be unbuffered. It *does* make a
        #    difference for stdin though. Perhaps setvbuf can only be
        #    used to affect *write* end of pipe, i.e. we cannot affect
        #    what the child side of stdout/stderr will do. I suspect
        #    that the only way to get this to work is to get the parent
        #    side of stdout (and possibly stderr) to look like a tty.
        #    This might require platform-specific hack, if it is indeed
        #    possibly at all. How does Cygwin's bash do it? or 4DOS?
        ## Ensure that the writes came in one about every second.

    def test_ProcessProxy_my_stdout_with_unbuffered_child(self):
        p = process.ProcessProxy(['talk_setvbuf'], stdout=MyOutFile(),
                                 stderr=MyOutFile())
        p.wait()
        self.failUnless(p.stdout.getOutput() == 'o0o1o2o3o4')
        self.failUnless(p.stderr.getOutput() == 'e0e1e2e3e4')

        # Ensure that the writes are spread over about 5 seconds.
        writeEvents = [e for e in p.stdout.log if e[1] == 'write']
        timespan = writeEvents[-1][0] - writeEvents[0][0]
        epsilon = 1.0
        self.failUnless(timespan > epsilon,
                        "Write events were not spread over a few seconds."\
                        "timespan=%r" % timespan)

    def test_ProcessProxy_read_all(self):
        p = process.ProcessProxy(['talk'])
        output = p.stdout.read()
        self.failUnless(output == 'o0o1o2o3o4')
        error = p.stderr.read()
        self.failUnless(error == 'e0e1e2e3e4')

    def test_ProcessProxy_readline(self):
        p = process.ProcessProxy('hello10')
        for i in range(10):
            output = p.stdout.readline()
            self.failUnless(output == "hello\n")

    def test_ProcessProxy_readlines(self):
        p = process.ProcessProxy('hello10')
        output = p.stdout.readlines()
        self.failUnless(output == ["hello\n"]*10)
        p = process.ProcessProxy('hello10noeol')
        output = p.stdout.readlines()
        self.failUnless(output == ["hello\n"]*9 + ["hello"])

    def test_ProcessOpen_read_all(self):
        p = process.ProcessOpen(['talk'])
        output = p.stdout.read()
        self.failUnless(output == 'o0o1o2o3o4')
        error = p.stderr.read()
        self.failUnless(error == 'e0e1e2e3e4')

    def test_ProcessOpen_readline(self):
        p = process.ProcessOpen('hello10')
        for i in range(10):
            output = p.stdout.readline()
            self.failUnless(output == "hello\n")

    def test_ProcessOpen_readlines(self):
        p = process.ProcessOpen('hello10')
        output = p.stdout.readlines()
        self.failUnless(output == ["hello\n"]*10)



def suite():
    """Return a unittest.TestSuite to be used by test.py."""
    return unittest.makeSuite(StdoutTestCase)

if __name__ == "__main__":
    import logging
    logging.basicConfig()
    testsupport.setup()
    sys.argv.insert(1, "-v") # always want verbose output
    unittest.main()

