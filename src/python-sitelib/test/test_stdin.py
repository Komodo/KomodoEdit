"""Test simple stdout (and stderr) hookup in spawning a child process."""

import os
import sys
import time
import pprint
import threading
import unittest

import process


class MyInFile:
    def __init__(self, buf):
        self._inBuffer = buf
        self._stateChange = threading.Condition()
        self._closed = 0
    def read(self, size):
        #XXX Should this be a 'while' to wait until 'size' bytes and in
        #    the _inBuffer before returning (unless _closed, of course).
        if not self._closed and not self._inBuffer:
            self._stateChange.acquire()
            self._stateChange.wait()
            self._stateChange.release()

        text, self._inBuffer = self._inBuffer[:size], self._inBuffer[size:]
        return text
    def close(self):
        self._stateChange.acquire()
        self._closed = 1
        self._stateChange.notifyAll()
        self._stateChange.release()

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

class StdinTestCase(unittest.TestCase):
    def test_ProcessProxy_stdin_handle_cleanup_1(self):
        p1 = process.ProcessProxy(['ask'])
        p2 = process.ProcessProxy(['ask'])
        p1.stdin.write("Trent\n")
        p2.stdin.write("Andrew\n")
        p1.stdin.close()
        p2.stdin.close()

        p1.wait()
        del p1
        p2.wait()

        p1 = process.ProcessProxy(['ask'])
        p2 = process.ProcessProxy(['ask'])
        p1.stdin.write("Mick\n")
        p1.stdin.close()

        output = p1.stdout.read()
        expected = "What is your name?\nYour name is 'Mick'.\n"
        self.failUnless(output == expected,
                        "Unexpected stdout output: %r" % output)
        p2.kill()

    def test_ProcessProxy_stdin_handle_cleanup_2(self):
        p1 = process.ProcessProxy(['ask'])
        p2 = process.ProcessProxy(['ask'])
        p1.stdin.write("Trent\n")
        p2.stdin.write("Andrew\n")
        p1.stdin.close()
        p2.stdin.close()

        p1.wait()
        p2.wait()

        p1 = process.ProcessProxy(['ask'])
        p2 = process.ProcessProxy(['ask'])
        p1.stdin.write("Mick\n")
        p1.stdin.close()

        p2.kill()

    def test_ProcessProxy_stdin_buffer(self):
        p = process.ProcessProxy(['ask'])
        p.stdin.write("Trent\n")
        p.stdin.close()
        output = p.stdout.read()
        expected = "What is your name?\nYour name is 'Trent'.\n"
        self.failUnless(output == expected,
                        "Unexpected stdout output: %r" % output)

    def test_ProcessProxy_stdin_buffer_nonewline(self):
        p = process.ProcessProxy(['ask'])
        p.stdin.write("Tre")
        # Note that we have not sent a newline, so the scanf() (or
        # fread() or whatever) in ask.exe is still waiting for input.
        # This is testing that the subsequent p.stdin.close()
        # successfully communicates to the child that the pipe is closed
        # and no more data is forth coming. (This relies on the pipe
        # inheritability having been properly set.)
        p.stdin.close()
        output = p.stdout.read()
        expected = "What is your name?\nYour name is 'Tre'.\n"
        self.failUnless(output == expected,
                        "Unexpected stdout output: %r" % output)

    def test_ProcessProxy_stdin_donotrespond(self):
        p = process.ProcessProxy(['ask_then_talk'],
                            stdout=MyOutFile(), stderr=MyOutFile())
        # Expect this to hang, as the child waits for input that we do
        # not send it.
        time.sleep(6)
        # There should be no output, other that
        output = ''.join([item[2] for item in p.stdout.log])
        try:
            self.failUnless(output == "What is your name?\n",
                "Stdout has unexpectedly received other than one "\
                "'What is your name?' write. The process should "\
                "be hung. log=%r" % p.stdout.log)
        finally:
            p.kill()

    ## This is left commented out because the use of 'sys.stdin' requires
    ## user interaction -- not really an automated test suite then.
    #def test_ProcessProxy_stdin_sysstdin(self):
    #    p = process.ProcessProxy(['ask'], stdin=sys.stdin)
    #    output = p.stdout.read()
    #    expected = "What is your name?\nYour name is"
    #    self.failUnless(output.find(expected) != -1,
    #                    "Unexpected stdout output: %r" % output)

    def test_ProcessProxy_stdin_text_mode(self):
        # On Linux:
        #   There is no distinction btwn text- and binary-modes. So this
        #   really is not providing that useful a test.
        p = process.ProcessProxy(['sort'])
        p.stdin.write("2\n")
        p.stdin.write("1\n")
        p.stdin.write("3\n")
        p.stdin.close()
        output = p.stdout.read()
        expected = "1\n2\n3\n"
        self.failUnless(output == expected,
                        "Unexpected stdout output: %r (expected: %r). "\
                        "Pipes are not doing text translation."\
                        % (output, expected))

    if sys.platform.startswith("win"):
        def test_ProcessProxy_stdin_binary_mode(self):
            p = process.ProcessProxy(['sort'], mode='b')
            p.stdin.write("2\n")
            p.stdin.write("1\n")
            p.stdin.write("3\n")
            p.stdin.close()
            output = p.stdout.read()
            expected = "???\r\n"
            self.failUnless(output == expected,
                            "Unexpected stdout output: %r (expected: %r). "\
                            "Pipes are not doing text translation."\
                            " Make sure that the Windows sort.exe is first on the path."\
                            % (output, expected))
        
            # Note: reusing 'p' here is subtly testing another aspect of the
            #       ProcessProxy stuff. If self._hChildStdinWr (and the
            #       stdout/stderr equivs) are not handled in ProcessProxy.__del__
            #       then a win32api error on CloseHandle is raised when the
            #       C runtime closes these handles asynchronously.

            p = process.ProcessProxy(['sort'], mode='b')
            p.stdin.write("2\r\n")
            p.stdin.write("1\r\n")
            p.stdin.write("3\r\n")
            p.stdin.close()
            output = p.stdout.read()
            expected = "1\r\n2\r\n3\r\n"
            self.failUnless(output == expected,
                            "Unexpected stdout output: %r (expected: %r). "\
                            "Pipes are not doing text translation."\
                            % (output, expected))

    def test_ProcessProxy_stdin_buffering_with_mystdin(self):
        p = process.ProcessProxy(['ask'], stdin=MyInFile("Trent\n"))
        output = p.stdout.read()
        expected = "What is your name?\nYour name is 'Trent'.\n"
        self.failUnless(output == expected,
                        "Unexpected stdout output: %r" % output)

    def test_ProcessOpen_stdin_handle_cleanup_1(self):
        p1 = process.ProcessOpen(['ask'])
        p2 = process.ProcessOpen(['ask'])
        p1.stdin.write("Trent\n")
        p2.stdin.write("Andrew\n")
        p1.stdin.close()
        p2.stdin.close()

        p1.wait()
        p1.close()
        del p1
        p2.wait()
        p2.close()

        p1 = process.ProcessOpen(['ask'])
        p2 = process.ProcessOpen(['ask'])
        p1.stdin.write("Mick\n")
        p1.stdin.close()

        output = p1.stdout.read()
        expected = "What is your name?\nYour name is 'Mick'.\n"
        self.failUnless(output == expected,
                        "Unexpected stdout output: %r" % output)
        p2.kill()
        p1.close()
        p2.close()

    def test_ProcessOpen_stdin_handle_cleanup_2(self):
        p1 = process.ProcessOpen(['ask'])
        p2 = process.ProcessOpen(['ask'])
        p1.stdin.write("Trent\n")
        p2.stdin.write("Andrew\n")
        p1.stdin.close()
        p2.stdin.close()

        p1.wait()
        p1.close()
        p2.wait()
        p2.close()

        p1 = process.ProcessOpen(['ask'])
        p2 = process.ProcessOpen(['ask'])
        p1.stdin.write("Mick\n")
        p1.stdin.close()

        p2.kill()
        p2.close()
        p1.close()

    def test_ProcessOpen_stdin_buffer(self):
        p = process.ProcessOpen(['ask'])
        p.stdin.write("Trent\n")
        p.stdin.close()
        output = p.stdout.read()
        p.close()
        expected = "What is your name?\nYour name is 'Trent'.\n"
        self.failUnless(output == expected,
                        "Unexpected stdout output: %r" % output)

    def test_ProcessOpen_stdin_buffer_nonewline(self):
        p = process.ProcessOpen(['ask'])
        p.stdin.write("Tre")
        # Note that we have not sent a newline, so the scanf() (or
        # fread() or whatever) in ask.exe is still waiting for input.
        # This is testing that the subsequent p.stdin.close()
        # successfully communicates to the child that the pipe is closed
        # and no more data is forth coming. (This relies on the pipe
        # inheritability having been properly set.)
        p.stdin.close()
        output = p.stdout.read()
        p.close()
        expected = "What is your name?\nYour name is 'Tre'.\n"
        self.failUnless(output == expected,
                        "Unexpected stdout output: %r" % output)

    def test_ProcessOpen_stdin_donotrespond(self):
        p = process.ProcessOpen('ask_then_talk')
        # Expect this to hang, as the child waits for input that we do
        # not send it.
        time.sleep(2)
        try:
            output = p.stdout.read(4092)
            self.failUnless(output.strip() == "What is your name?",
                "Stdout has unexpectedly received other than one "\
                "'What is your name?' write. The process should "\
                "be hung. output=%r" % output)
        finally:
            p.kill()
            p.close()

    ## This is left commented out because the use of 'sys.stdin' requires
    ## user interaction -- not really an automated test suite then.
    #def test_ProcessOpen_stdin_sysstdin(self):
    #    p = process.ProcessOpen(['ask'], stdin=sys.stdin)
    #    output = p.stdout.read()
    #    expected = "What is your name?\nYour name is"
    #    self.failUnless(output.find(expected) != -1,
    #                    "Unexpected stdout output: %r" % output)

    def test_ProcessOpen_stdin_text_mode(self):
        # On Linux:
        #   There is no distinction btwn text- and binary-modes. So this
        #   really is not providing that useful a test.
        p = process.ProcessOpen(['sort'])
        p.stdin.write("2\n")
        p.stdin.write("1\n")
        p.stdin.write("3\n")
        p.stdin.close()
        output = p.stdout.read()
        p.close()
        expected = "1\n2\n3\n"
        self.failUnless(output == expected,
                        "Unexpected stdout output: %r (expected: %r). "\
                        "Pipes are not doing text translation."\
                        % (output, expected))

    if sys.platform.startswith("win"):
        def test_ProcessOpen_stdin_binary_mode(self):
            p = process.ProcessOpen(['sort'], mode='b')
            p.stdin.write("2\n")
            p.stdin.write("1\n")
            p.stdin.write("3\n")
            p.stdin.close()
            output = p.stdout.read()
            p.close()
            expected = "???\r\n"
            self.failUnless(output == expected,
                            "Unexpected stdout output: %r (expected: %r). "\
                            "Binary mode pipes are not working as expected."\
                            " Make sure that the Windows sort.exe is first on the path."\
                            % (output, expected))
        
            # Note: reusing 'p' here is subtly testing another aspect of the
            #       ProcessOpen stuff. If self._hChildStdinWr (and the
            #       stdout/stderr equivs) are not handled in ProcessOpen.__del__
            #       then a win32api error on CloseHandle is raised when the
            #       C runtime closes these handles asynchronously.

            p = process.ProcessOpen(['sort'], mode='b')
            p.stdin.write("2\r\n")
            p.stdin.write("1\r\n")
            p.stdin.write("3\r\n")
            p.stdin.close()
            output = p.stdout.read()
            p.close()
            expected = "1\r\n2\r\n3\r\n"
            self.failUnless(output == expected,
                            "Unexpected stdout output: %r (expected: %r). "\
                            "Pipes are not doing text translation."\
                            " Make sure that the Windows sort.exe is first on the path."\
                            % (output, expected))


def suite():
    """Return a unittest.TestSuite to be used by test.py."""
    return unittest.makeSuite(StdinTestCase)

if __name__ == "__main__":
    import logging
    logging.basicConfig()
    testsupport.setup()
    sys.argv.insert(1, "-v") # always want verbose output
    unittest.main()

