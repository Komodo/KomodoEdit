# Copyright (c) 2000-2007 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

import os
import sys
import unittest

try:
    from xpcom import components
except ImportError:
    pass # Allow testing without PyXPCOM to proceed.



#---- test cases

class EncodeDecodeTestCase(unittest.TestCase):
    def test_old_style_encoding(self):
        cmd = 'echo hi'
        bracecmd = 'perl -e "if (1) { print 1; }"'
        argsets = [
            (cmd,      cmd, 0, 0),
            (bracecmd, bracecmd, 0, 0),
            ('[i] '+cmd,      cmd, 1, 0),
            ('[i] '+bracecmd, bracecmd, 1, 0),
            ('[l] '+cmd,      cmd, 0, 1),
            ('[l] '+bracecmd, bracecmd, 0, 1),
            ('[il] '+cmd,      cmd, 1, 1),
            ('[il] '+bracecmd, bracecmd, 1, 1),
        ]
        for set in argsets:
            self._testOldStyleDecode(*set)

    def _testOldStyleDecode(self, encoded, command, insertOutput,
                            operateOnSelection):
        runSvc = components.classes["@activestate.com/koRunService;1"]\
                 .getService(components.interfaces.koIRunService)
        (d_command, d_cwd, d_env, d_insertOutput, d_operateOnSelection,
         d_doNotOpenOutputWindow, d_runIn, d_parseOutput, d_parseRegex,
         d_showParsedOutputList) = runSvc.Decode(encoded)
        self.failUnless(d_command == command)
        self.failUnless(d_cwd == '')
        self.failUnless(d_env == '')
        self.failUnless(d_insertOutput == insertOutput)
        self.failUnless(d_operateOnSelection == operateOnSelection)
        self.failUnless(d_doNotOpenOutputWindow == 0)
        self.failUnless(d_runIn == 'command-output-window')
        self.failUnless(d_parseOutput == 0)
        self.failUnless(d_parseRegex == '')
        self.failUnless(d_showParsedOutputList == 0)

    def test_just_command(self):
        #print #XXX
        runSvc = components.classes["@activestate.com/koRunService;1"]\
                 .getService(components.interfaces.koIRunService)
        # With all default options the encoded command should just be
        # the command string.
        command = 'echo hi'
        args = (command, # command
                '', # cwd
                '', # env
                0, # insertOutput
                0, # operateOnSelection
                0, # doNotOpenOutputWindow
                'command-output-window', # runIn
                0, # parseOutput
                '', # parseRegex
                0) # showParsedOutputList
        encoded = runSvc.Encode(*args)
        self.failUnless(encoded == command)
        self._testRoundTrip(*args)

        # ... except that some character escaping may be done.
        command = 'perl -e "if (1) { print 1; }"'
        args = (command, # command
                '', # cwd
                '', # env
                0, # insertOutput
                0, # operateOnSelection
                0, # doNotOpenOutputWindow
                'command-output-window', # runIn
                0, # parseOutput
                '', # parseRegex
                0) # showParsedOutputList
        encoded = runSvc.Encode(*args)
        self.failUnless(encoded != command)  # '{' and '}' will be escaped
        self._testRoundTrip(*args)

    def test_with_options(self):
        # With all default options the encoded command should just be
        # the command string.
        cmd = 'echo hi'
        bracecmd = 'perl -e "if (1) { print 1; }"'
        argsets = [
            # Change each option, one at a time.
            # (command, cwd, env, insertOutput, operateOnSelection,
            #  doNotOpenOutputWindow, runIn, parseOutput, parseRegex,
            #  showParsedOutputList)
            (cmd,      'D:\\trentm', '', 0, 0, 0, 'command-output-window', 0, '', 0),
            (bracecmd, 'D:\\trentm', '', 0, 0, 0, 'command-output-window', 0, '', 0),
            (cmd,      '', 'FOO=foo', 0, 0, 0, 'command-output-window', 0, '', 0),
            (bracecmd, '', 'FOO=foo', 0, 0, 0, 'command-output-window', 0, '', 0),
            (cmd,      '', 'FOO=foo\nBAR=bar', 0, 0, 0, 'command-output-window', 0, '', 0),
            (bracecmd, '', 'FOO=foo\nBAR=bar', 0, 0, 0, 'command-output-window', 0, '', 0),
            (cmd,      '', '', 1, 0, 0, 'command-output-window', 0, '', 0),
            (bracecmd, '', '', 1, 0, 0, 'command-output-window', 0, '', 0),
            (cmd,      '', '', 0, 1, 0, 'command-output-window', 0, '', 0),
            (bracecmd, '', '', 0, 1, 0, 'command-output-window', 0, '', 0),
            (cmd,      '', '', 0, 0, 1, 'command-output-window', 0, '', 0),
            (bracecmd, '', '', 0, 0, 1, 'command-output-window', 0, '', 0),
            (cmd,      '', '', 0, 0, 0, '', 0, '', 0),
            (bracecmd, '', '', 0, 0, 0, '', 0, '', 0),
            (cmd,      '', '', 0, 0, 0, 'new-console', 0, '', 0),
            (bracecmd, '', '', 0, 0, 0, 'new-console', 0, '', 0),
            (cmd,      '', '', 0, 0, 0, 'no-console', 0, '', 0),
            (bracecmd, '', '', 0, 0, 0, 'no-console', 0, '', 0),
            (cmd,      '', '', 0, 0, 0, 'command-output-window', 1, '', 0),
            (bracecmd, '', '', 0, 0, 0, 'command-output-window', 1, '', 0),
            (cmd,      '', '', 0, 0, 0, 'command-output-window', 0, '.*[^f]$', 0),
            (bracecmd, '', '', 0, 0, 0, 'command-output-window', 0, '.*[^f]$', 0),
            (cmd,      '', '', 0, 0, 0, 'command-output-window', 1, '.*[^f]$', 0),
            (bracecmd, '', '', 0, 0, 0, 'command-output-window', 1, '.*[^f]$', 0),
            (cmd,      '', '', 0, 0, 0, 'command-output-window', 0, '', 1),
            (bracecmd, '', '', 0, 0, 0, 'command-output-window', 0, '', 1),
            # Change all the options at once.
            (cmd,      'D:\\trentm', 'FOO=foo\nBAR=bar', 1, 1, 1, 'new-console', 0, '', 0),
            (bracecmd, 'D:\\trentm', 'FOO=foo\nBAR=bar', 1, 1, 1, 'new-console', 0, '', 0),
        ]
        for set in argsets:
            self._testRoundTrip(*set)

    def _testRoundTrip(self, command, cwd, env, insertOutput,
                       operateOnSelection, doNotOpenOutputWindow,
                       runIn, parseOutput, parseRegex,
                       showParsedOutputList):
        runSvc = components.classes["@activestate.com/koRunService;1"]\
                 .getService(components.interfaces.koIRunService)
        encoded = runSvc.Encode(command, cwd, env, insertOutput,
                                operateOnSelection,
                                doNotOpenOutputWindow, runIn,
                                parseOutput, parseRegex,
                                showParsedOutputList)

        #print "XXX encoded: %s" % encoded
        (d_command, d_cwd, d_env, d_insertOutput, d_operateOnSelection,
         d_doNotOpenOutputWindow, d_runIn, d_parseOutput, d_parseRegex,
         d_showParsedOutputList) = runSvc.Decode(encoded)

        self.failUnless(d_command == command)
        self.failUnless(d_cwd == cwd)
        self.failUnless(d_env == env)
        self.failUnless(d_insertOutput == insertOutput)
        self.failUnless(d_operateOnSelection == operateOnSelection)
        self.failUnless(d_doNotOpenOutputWindow == doNotOpenOutputWindow)
        self.failUnless(d_runIn == runIn)
        self.failUnless(d_parseOutput == parseOutput)
        self.failUnless(d_parseRegex == parseRegex,
                        "Encode->Decode round-trip error with 'parseRegex': "
                        "%r->%r" % (parseRegex, d_parseRegex))
        self.failUnless(d_showParsedOutputList == showParsedOutputList)





