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
log.setLevel(Casper.Logging.WARN);
//log.setLevel(Casper.Logging.INFO);
//log.setLevel(Casper.Logging.DEBUG);

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
    var stdout = process.getStdout();
    this.assertNotEqual(stdout, "", "Expected some stdout, got nothing.");
    var stderr = process.getStderr();
    this.assertEqual(stderr, "", "Expected no stderr, got '" + stderr + "'");
}

    /**
     * Test process timeout.
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
        var expectSubstring = "Process timeout: waited 3 seconds, process not yet finished";
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
    ko.run.command(cmd,
                   {
                    "window": ko.windowManager.getMainWindow(),
                    "openOutputWindow": false,
                    "clearOutputWindow": false,
                    "terminationCallback": terminationCallback,
                    "saveInMacro": false,
                   });
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

    /**
     * Test large amounts of stdout, stderr and mixed combos.
     * This ensures that the run processes do not get blocked when
     * large amounts of data are passed through the stdout/stderr handles.
     */
test_run_commands.prototype.test_large_stdout_stderr = function() {
    var fileSvc = Components.classes["@activestate.com/koFileService;1"].
                    getService(Components.interfaces.koIFileService);
    // koIFile for writing a python program contents.
    var koIFile = fileSvc.makeTempFile(".py", "w");
    koIFile.close();

    // Python file contents that will output the stdout/stderr.
    var fileStdoutContents = "\n\
import sys\n\
len_stdout_written = 0\n\
while len_stdout_written < 65536:\n\
    sys.stdout.write(sys.copyright)\n\
    #sys.stderr.write(sys.copyright)\n\
    len_stdout_written += len(sys.copyright)\n\
";
    var outputTestType = "";
    var cmd = "python \"" + koIFile.path + "\"";
    // Unset the PYTHONHOME environment variable on Linux, MacOS.
    var infoSvc = Components.classes["@activestate.com/koInfoService;1"].
                    getService(Components.interfaces.koIInfoService);
    if (!infoSvc.platform.toLowerCase().match(/^win/)) {
        // Python home environment variable can cause a "import site" failed
        // error message to be printed to stderr, which can cause the tests to
        // fail, so we get rid of the environment variable here.
        cmd = "unset PYTHONHOME && " + cmd;
    }
    // loop_replacements is used for alternating the fileContents between
    // outputting to stdout/stderr or to both.
    var loop_replacements = [
                               // Stdout only.
                               [],
                               // Stderr only.
                               [["sys.stdout.write", "#sys.stdout.write"],
                                ["#sys.stderr.write", "sys.stderr.write"]],
                               // Both stdout and stderr.
                               [["#sys.stdout.write", "sys.stdout.write"]]
                            ];

    log.debug("test_large_stdout_stderr:: cmd '" + cmd + "'");
    for (var i=0; i < loop_replacements.length; i++) {
        var replacements = loop_replacements[i];
        if (i == 0) {
            outputTestType = "stdout only";
        } else if (i == 1) {
            outputTestType = "stderr only";
        } else if (i == 2) {
            outputTestType = "stdout and stderr";
        }
        for (var j=0; j < replacements.length; j++) {
            fileStdoutContents = fileStdoutContents.replace(replacements[j][0],
                                                            replacements[j][1]);
        }
        koIFile.open("w");
        koIFile.puts(fileStdoutContents);
        //dump("fileStdoutContents[" + i + "]: " + fileStdoutContents + "\n");
        koIFile.close();

        var cmdName;
        var retval;
        var stdout;
        var stderr;
        var cmdNames = ["RunAndCaptureOutput",
                        "RunAndNotify",
                        "RunInTerminal",
                        "Run"];
        // Run for each run command available.
        log.debug("test_large_stdout_stderr:: output test type: " + outputTestType);
        for (j=0; j < cmdNames.length; j++) {
            cmdName = cmdNames[j];
            log.debug("test_large_stdout_stderr:: testing " + cmdName);
            try {
                if (cmdName == "RunAndCaptureOutput") {
                    var stdoutObj = new Object();
                    var stderrObj = new Object();
                    retval = this.runSvc.RunAndCaptureOutput(cmd,
                                                             null /* cwd */,
                                                             null /* env */,
                                                             null /* input */,
                                                             stdoutObj,
                                                             stderrObj);
                    stdout = stdoutObj.value;
                    stderr = stderrObj.value;
                } else if (cmdName == "RunAndNotify") {
                    var process = this.runSvc.RunAndNotify(cmd,
                                                           null /* cwd */,
                                                           null /* env */,
                                                           null /* input */);
                    retval = process.wait(10);  // Wait 10 seconds before failing.
                    stdout = process.getStdout();
                    stderr = process.getStderr();
                } else if (cmdName == "RunInTerminal") {
                    var process = this.runSvc.RunInTerminal(cmd,
                                                            null /* cwd */,
                                                            null /* env */,
                                                            null /* koITreeOutputHandler */,
                                                            null /* koIRunTerminationListener */,
                                                            null /* input */);
                    retval = process.wait(10);  // Wait 10 seconds before failing.
                    stdout = process.getStdout();
                    stderr = process.getStderr();
                } else if (cmdName == "Run") {
                    this.runSvc.Run(cmd,
                                    null  /* cwd */,
                                    null  /* env */,
                                    false /* console */,
                                    null  /* input */);
                    continue;
                }
            } catch(ex) {
                if (ex.message.search("Process timeout") >= 0) {
                    this.fail(cmdName + " '" + outputTestType + "' failed to return!");
                    return;
                } else {
                    throw ex;
                }
            }
            cmdName += " '" + outputTestType + "'";

            if (retval != 0)
                log.warn("test_large_stdout_stderr:: stderr: " + stderrObj.value.substr(0, 200));
            this.assertEqual(retval, 0, cmdName +": Expected retval of 0, got " + retval);
            // We expect some stdout, but no stderr
            if (i == 0 || i == 2) {
                this.assertTrue((stdoutObj.value.length >= 65536), cmdName +":Expected stdout length >= 65536, but only got: " + stdoutObj.value.length);
                if (i == 0) {
                    this.assertEqual(stderrObj.value, "", cmdName +":Expected no stderr, got '" +
                                                          stderrObj.value + "'");
                }
            }
            if (i == 1 || i == 2) {
                this.assertTrue((stderrObj.value.length >= 65536), cmdName +":Expected stderr length >= 65536, but only got: " + stderrObj.value.length);
                if (i == 1) {
                    this.assertEqual(stdoutObj.value, "", cmdName +":Expected no stdout, got '" +
                                                          stdoutObj.value + "'");
                }
            }
        }
    }
}

    // * test running with unicode input.
    //   http://bugs.activestate.com/show_bug.cgi?id=74750
test_run_commands.prototype.test_unicode_input = function() {
    var infoSvc = Components.classes["@activestate.com/koInfoService;1"].
                    getService(Components.interfaces.koIInfoService);
    // Only running this command on Linux, as I don't know what applications
    // are default on OSX and Windows which support passing of unicode input.
    if (infoSvc.platform.toLowerCase().match(/^linux/)) {
        var cmd = "tr ' ' _";
        var input = "My Конференцию command.";
        var process = this.runSvc.RunAndNotify(cmd, null, null, input);
        var retval = process.wait(-1);  // Wait forever.
        this.assertEqual(retval, 0, "Expected retval of 0, got " + retval);
        // We expect some stdout, but no stderr
        var stdout = process.getStdout();
        this.assertEqual(stdout, "My_Конференцию_command.", "Stdout is wrong: '" + stdout + "'");
        var stderr = process.getStderr();
        this.assertEqual(stderr, "", "Expected no stderr, got '" + stderr + "'");
    }
}

    // * test killing a process that is using "tail -f ...".
test_run_commands.prototype.test_tail_command = function() {
    var infoSvc = Components.classes["@activestate.com/koInfoService;1"].
                    getService(Components.interfaces.koIInfoService);
    // Only running this command on Linux and OSX, as I don't know what
    // application to use on Windows.
    if (!infoSvc.platform.toLowerCase().match(/^win/)) {
        var fileSvc = Components.classes["@activestate.com/koFileService;1"].
                        getService(Components.interfaces.koIFileService);
        // koIFile for writing a python program contents.
        var koIFile = fileSvc.makeTempFile(".py", "w");
        koIFile.close();
        var cmd = "tail -f " + koIFile.path;
        var process = this.runSvc.RunInTerminal(cmd, null, null, ko.run.output.getTerminal(), null, null);
        try {
            var retval = process.wait(2);  // Wait till timeout.
            this.fail("Process did not timeout");
        } catch (ex) {
            process.kill(-9);
        }
        try {
            var retval = process.wait(2);  // Should not timeout.
        } catch (ex) {
            this.fail("Process timed out after killing");
        }
        this.assertEqual(retval, -9, "Expected retval of -9, got " + retval);
    }
}

    // * test running a command using the API that the run command dialog uses.
    //   - test pass selection as input
    //   - test insert output
test_run_commands.prototype.test_run_command_dialog = function() {
    // Make a simple Python program to echo the output twice.
    var fileSvc = Components.classes["@activestate.com/koFileService;1"].
                    getService(Components.interfaces.koIFileService);
    // koIFile for writing a python program contents.
    var koIFile = fileSvc.makeTempFile(".py", "w");
    // Python file contents that will output the stdout/stderr.
    var fileContents = "\n\
import sys\n\
sys.stdout.write(sys.stdin.read())\n\
";
    koIFile.puts(fileContents);
    koIFile.close();

    var input = "This is line 1\nThis is line 2\n";
    var cmd = "python \"" + koIFile.path + "\"";
    var process = this.runSvc.RunAndNotify(cmd, null, null, input);

    try {
        var retval = process.wait(5);  // Wait till timeout.
    } catch (ex) {
        this.fail("Process timeout out");
        process.kill(-9);
        return;
    }
    var output = process.getStdout();
    this.assertEqual(output, input, "Output does not match the input.");
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
