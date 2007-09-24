"""Test various command strings for process launch."""

import os
import sys
import re
import pprint
import unittest
import shutil
import testsupport

import process
import which


class CmdTestCase(unittest.TestCase):
    def test_Process_simple_cmd(self):
        logfile = "log.log"
        if os.path.exists(logfile): os.unlink(logfile)
        p = process.Process('log hi there')
        p.wait()
        output = open(logfile, 'r').readlines()
        self.failUnless(output[1:] == ['hi\n', 'there\n'])

    def test_Process_cmd_with_space(self):
        logfile = "log.log"
        if os.path.exists(logfile): os.unlink(logfile)
        p = process.Process('"log space" hi there')
        p.wait()
        output = open(logfile, 'r').readlines()
        self.failUnless(output[1:] == ['hi\n', 'there\n'])

    def test_Process_cmd_with_spaces(self):
        logfile = "log.log"
        if os.path.exists(logfile): os.unlink(logfile)
        p = process.Process('"log space" "hi there"')
        p.wait()
        output = open(logfile, 'r').readlines()
        self.failUnless(output[1:] == ['hi there\n'])

    def test_Process_simple_argv(self):
        logfile = "log.log"
        if os.path.exists(logfile): os.unlink(logfile)
        p = process.Process(['log', 'hi', 'there'])
        p.wait()
        output = open(logfile, 'r').readlines()
        self.failUnless(output[1:] == ['hi\n', 'there\n'])

    def test_Process_argv_with_space(self):
        logfile = "log.log"
        if os.path.exists(logfile): os.unlink(logfile)
        p = process.Process(['log space', 'hi', 'there'])
        p.wait()
        output = open(logfile, 'r').readlines()
        self.failUnless(output[1:] == ['hi\n', 'there\n'])

    def test_Process_argv_with_spaces(self):
        logfile = "log.log"
        if os.path.exists(logfile): os.unlink(logfile)
        p = process.Process(['log space', 'hi there'])
        p.wait()
        output = open(logfile, 'r').readlines()
        self.failUnless(output[1:] == ['hi there\n'])

    if sys.platform.startswith("win"):
        def test_Process_simple_cmd_new_console(self):
            logfile = "log.log"
            if os.path.exists(logfile): os.unlink(logfile)
            flags = process.Process.CREATE_NEW_CONSOLE
            p = process.Process('log hi there', flags=flags)
            p.wait()
            output = open(logfile, 'r').readlines()
            self.failUnless(output[1:] == ['hi\n', 'there\n'])

        def test_Process_cmd_with_space_new_console(self):
            logfile = "log.log"
            if os.path.exists(logfile): os.unlink(logfile)
            flags = process.Process.CREATE_NEW_CONSOLE
            p = process.Process('"log space" hi there', flags=flags)
            p.wait()
            output = open(logfile, 'r').readlines()
            self.failUnless(output[1:] == ['hi\n', 'there\n'])

        def test_Process_cmd_with_spaces_new_console(self):
            logfile = "log.log"
            if os.path.exists(logfile): os.unlink(logfile)
            flags = process.Process.CREATE_NEW_CONSOLE
            p = process.Process('"log space" "hi there"', flags=flags)
            p.wait()
            output = open(logfile, 'r').readlines()
            self.failUnless(output[1:] == ['hi there\n'])

        def test_Process_simple_argv_new_console(self):
            logfile = "log.log"
            if os.path.exists(logfile): os.unlink(logfile)
            flags = process.Process.CREATE_NEW_CONSOLE
            p = process.Process(['log', 'hi', 'there'], flags=flags)
            p.wait()
            output = open(logfile, 'r').readlines()
            self.failUnless(output[1:] == ['hi\n', 'there\n'])

        def test_Process_argv_with_space_new_console(self):
            logfile = "log.log"
            if os.path.exists(logfile): os.unlink(logfile)
            flags = process.Process.CREATE_NEW_CONSOLE
            p = process.Process(['log space', 'hi', 'there'], flags=flags)
            p.wait()
            output = open(logfile, 'r').readlines()
            self.failUnless(output[1:] == ['hi\n', 'there\n'])

        def test_Process_argv_with_spaces_new_console(self):
            logfile = "log.log"
            if os.path.exists(logfile): os.unlink(logfile)
            flags = process.Process.CREATE_NEW_CONSOLE
            p = process.Process(['log space', 'hi there'], flags=flags)
            p.wait()
            output = open(logfile, 'r').readlines()
            self.failUnless(output[1:] == ['hi there\n'])

    def test_ProcessProxy_simple_cmd(self):
        try:
            p = process.ProcessProxy('echo hi there')
        except (process.ProcessError, which.WhichError):
            # On Win9x the shell is not prefixed.
            p = process.ProcessProxy('command.com /c echo hi there')
        output = p.stdout.read()
        self.failUnless(output.strip() == 'hi there')

    def test_ProcessProxy_cmd_with_quotes(self):
        try:
            p = process.ProcessProxy('echo hi "there"')
        except (process.ProcessError, which.WhichError):
            # On Win9x the shell is not prefixed.
            p = process.ProcessProxy('command.com /c echo hi "there"')
        output = p.stdout.read()
        if sys.platform.startswith("win"):
            expected = 'hi "there"'
        else:
            expected = 'hi there'
        self.failUnless(output.strip() == expected)

    def test_ProcessProxy_cmd_with_multiples_quoted_args(self):
        dname = "program files"
        if not os.path.exists(dname):
            os.makedirs(dname)
        if sys.platform.startswith("win"):
            talk = "talk.exe"
        else:
            talk = "talk"
        talkWithSpaces = os.path.join(dname, talk)
        shutil.copy(talk, talkWithSpaces)

        try:
            p = process.ProcessProxy('"%s" and here are "some" args'\
                                     % talkWithSpaces)
            output = p.stdout.read()
            self.failUnless(output.strip() == 'o0o1o2o3o4')
        finally:
            if os.path.exists(talkWithSpaces):
                os.unlink(talkWithSpaces)
            if os.path.exists(dname):
                os.removedirs(dname)

    def test_ProcessOpen_simple_cmd(self):
        try:
            p = process.ProcessOpen('echo hi there')
        except (process.ProcessError, which.WhichError):
            # On Win9x the shell is not prefixed.
            p = process.ProcessOpen('command.com /c echo hi there')
        output = p.stdout.read()
        self.failUnless(output.strip() == 'hi there')

    def test_ProcessOpen_cmd_with_quotes(self):
        try:
            p = process.ProcessOpen('echo hi "there"')
        except (process.ProcessError, which.WhichError):
            # On Win9x the shell is not prefixed.
            p = process.ProcessOpen('command.com /c echo hi "there"')
        output = p.stdout.read()
        if sys.platform.startswith("win"):
            expected = 'hi "there"'
        else:
            expected = 'hi there'
        self.failUnless(output.strip() == expected)

    def test_ProcessOpen_cmd_with_multiples_quoted_args(self):
        dname = "program files"
        if not os.path.exists(dname):
            os.makedirs(dname)
        if sys.platform.startswith("win"):
            talk = "talk.exe"
        else:
            talk = "talk"
        talkWithSpaces = os.path.join(dname, talk)
        shutil.copy(talk, talkWithSpaces)

        try:
            p = process.ProcessOpen('"%s" and here are "some" args'\
                                    % talkWithSpaces)
            output = p.stdout.read()
            self.failUnless(output.strip() == 'o0o1o2o3o4')
        finally:
            if os.path.exists(talkWithSpaces):
                os.unlink(talkWithSpaces)
            if os.path.exists(dname):
                os.removedirs(dname)


def suite():
    """Return a unittest.TestSuite to be used by test.py."""
    return unittest.makeSuite(CmdTestCase)

if __name__ == "__main__":
    import logging
    logging.basicConfig()
    testsupport.setup()
    sys.argv.insert(1, "-v") # always want verbose output
    unittest.main()

