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

