/* ***** BEGIN LICENSE BLOCK *****
 * Version: MPL 1.1/GPL 2.0/LGPL 2.1
 * 
 * The contents of this file are subject to the Mozilla Public License
 * Version 1.1 (the "License"); you may not use this file except in
 * compliance with the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 * 
 * Software distributed under the License is distributed on an "AS IS"
 * basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
 * License for the specific language governing rights and limitations
 * under the License.
 * 
 * The Original Code is Komodo code.
 * 
 * The Initial Developer of the Original Code is ActiveState Software Inc.
 * Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
 * ActiveState Software Inc. All Rights Reserved.
 * 
 * Contributor(s):
 *   ActiveState Software Inc
 * 
 * Alternatively, the contents of this file may be used under the terms of
 * either the GNU General Public License Version 2 or later (the "GPL"), or
 * the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
 * in which case the provisions of the GPL or the LGPL are applicable instead
 * of those above. If you wish to allow use of your version of this file only
 * under the terms of either the GPL or the LGPL, and not to allow others to
 * use your version of this file under the terms of the MPL, indicate your
 * decision by deleting the provisions above and replace them with the notice
 * and other provisions required by the GPL or the LGPL. If you do not delete
 * the provisions above, a recipient may use your version of this file under
 * the terms of any one of the MPL, the GPL or the LGPL.
 * 
 * ***** END LICENSE BLOCK ***** */

try {
dump("Loading test_run_commands.js...\n");
var log = Casper.Logging.getLogger("Casper::test_run_commands");
//log.setLevel(Casper.Logging.DEBUG);
//log.setLevel(Casper.Logging.INFO);
log.setLevel(Casper.Logging.WARN);

// setup the test case
function test_run_commands() {
    // The name supplied must be the same as the class name!!
    Casper.UnitTest.TestCaseSerialClassAsync.apply(this, ["test_run_commands"]);
    /**
     * Tricky testing this on multiple platforms as you cannot guarentee that
     * the process executables will exist. So try to test with the third party
     * applications Komodo ships with and python processes:
     *   tidy
     */
    this.koDirs = Components.classes["@activestate.com/koDirs;1"].
                        getService(Components.interfaces.koIDirs);
    this.osSvc = Components.classes["@activestate.com/koOs;1"].
                        getService(Components.interfaces.koIOs);
    this.runSvc = Components.classes["@activestate.com/koRunService;1"].
                        getService(Components.interfaces.koIRunService);

    var sep = this.osSvc.sep;
    this.tidyArgv = [this.koDirs.supportDir + sep + "html" + sep + "tidy",
                     '-errors', '-quiet']
}
test_run_commands.prototype = new Casper.UnitTest.TestCaseSerialClassAsync();
test_run_commands.prototype.constructor = test_run_commands;

test_run_commands.prototype.setup = function() {
}
test_run_commands.prototype.tearDown = function() {
}

/* Utility functions */

    /**
     * Used to check settings of testcase with result
     */
    test_run_commands.prototype._passedTest = function(cmd, tags) {
        // Check if it's a knownfailure
        if (tags && tags.some(function(x) { return x == "knownfailure"; })) {
            log.warn(this.currentTest.name + " passed but is marked as a knownfailure!");
        }
    }
    
    /**
     * Log knownfailure
     */
    test_run_commands.prototype.logKnownFailure = function(cmd, ex) {
        log.info("knownfailure: " + ex.message);
    }

/* Child test cases */

// TODO:
// * test run retval
test_run_commands.prototype.test_run_and_capture_output = function() {
    var cmd = this.tidyArgv.join(" ") + " --version";
    // Run(in wstring command, in wstring cwd, in wstring env,
    //     in wstring input, out wstring output, out wstring error);
    var stdoutObj = new Object();
    var stderrObj = new Object();
    var retval = this.runSvc.RunAndCaptureOutput(cmd, null, null, null,
                                                 stdoutObj, stderrObj);
    this.assertEqual(retval, 0, "Expected retval of 0, got " + retval);
    // We expect some stdout, but no stderr
    this.assertNotEqual(stdoutObj.value, "", "Expected some stdout, got nothing.");
    this.assertEqual(stderrObj.value, "", "Expected no stderr, got '" +
                                          stderrObj.value + "'");
}

// * test run wait
test_run_commands.prototype.test_run_process = function() {
    var cmd = this.tidyArgv.join(" ") + " --version";
    // Run(in wstring command, in wstring cwd, in wstring env,
    //     in wstring input, out wstring output, out wstring error);
    var process = this.runSvc.RunAndNotify(cmd, null, null, null);
    var retval = process.wait(-1);  // Wait forever.
    this.assertEqual(retval, 0, "Expected retval of 0, got " + retval);
    // We expect some stdout, but no stderr
    var stdout = process.readStdout();
    this.assertNotEqual(stdout, "", "Expected some stdout, got nothing.");
    var stderr = process.readStderr();
    this.assertEqual(stderr, "", "Expected no stderr, got '" + stderr + "'");
}

/**
 * Test process timeout.
 * Fails on Komodo-devel on Linux as it never times out.
 * @tags knownfailure
 */
test_run_commands.prototype.test_run_process_timeout = function() {
    // This command will block forever, trying to read stdin.
    var cmd = this.tidyArgv.join(" ");
    // Run(in wstring command, in wstring cwd, in wstring env,
    //     in wstring input, out wstring output, out wstring error);
    var process = this.runSvc.RunAndNotify(cmd, null, null, null);
    try {
        var retval = process.wait(3);
    } catch (ex) {
        // We should get a python ProcessError exception, though it has
        // been turned into an nsIException after passing through xpcom.
        var expectSubstring = "ProcessError: Process timeout:";
        var actualSubstring = ex.message.substring(0, expectSubstring.length);
        this.assertEqual(actualSubstring, expectSubstring,
                         "Expected process timeout exception, got " + ex);
    } finally {
        process.kill(/* killCode, ignored value */ -9);
    }
}

// * test run termination callback
test_run_commands.prototype.test_run_termination_callback = function() {
    var cmd = this.tidyArgv.join(" ") + " --version";
    var gotretval = false;
    var self = this;
    function terminationCallback(retval) {
        gotretval = true;
        self.assertEqual(retval, 0, "Expected retval of 0, got " + retval);
    }
    ko.run.runCommand(ko.windowManager.getMainWindow() /* editor */,
                      cmd,
                      null /* cwd */,
                      null /* env */,
                      false /* insertOutput */,
                      false /* operateOnSelection */,
                      null /* doNotOpenOutputWindow */,
                      "command-output-window" /* runIn */,
                      false /* parseOutput */,
                      null /* parseRegex */,
                      false /* showParsedOutputList */,
                      null /* name */,
                      false /* clearOutputWindow */,
                      terminationCallback,
                      false /* saveInMRU */,
                      false /* saveInMacro */,
                      null /* viewData */);
    // Set a timeout to check if we got the retval.
    function checkReceivedCallback() {
        self.assertEqual(gotretval, true, "terminationCallback was not called.");
    }
    // This could actually fail on a slow machine.
    setTimeout(checkReceivedCallback, 1000);
}

// * test run kill
test_run_commands.prototype.test_kill_run_process = function() {
    // This command will block forever, trying to read stdin.
    var cmd = this.tidyArgv.join(" ");
    // Run(in wstring command, in wstring cwd, in wstring env,
    //     in wstring input, out wstring output, out wstring error);
    var process = this.runSvc.RunAndNotify(cmd, null, null, null);
    try {
        var retval = process.wait(1);
        this.fail("Process did not timeout");
    } catch (ex) {
        // We get a python ProcessError exception (turned in xpcom.COMException)
        // Ignore the exception, now kill the process.
        process.kill(/* killCode, ignored value */ -9);
        // Ensure it is actually killed, we should have a retval by now
        var retval = process.wait(1);
    }
}


/* TEST SUITE */

// we do not pass an instance of MyTestCase, they are created in MakeSuite
var suite = new Casper.UnitTest.TestSuite("Run Commands");
suite.add(new test_run_commands());
Casper.UnitTest.testRunner.add(suite);

} catch(e) {
    var CasperLog = Casper.Logging.getLogger("Casper::global");
    CasperLog.exception(e);
}
