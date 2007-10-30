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





