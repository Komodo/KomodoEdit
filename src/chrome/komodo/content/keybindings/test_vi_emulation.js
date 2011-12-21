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
dump("Loading test_vi_emulation.js...\n");
var log = Casper.Logging.getLogger("Casper::vim_emulation");
//log.setLevel(Casper.Logging.DEBUG);
//log.setLevel(Casper.Logging.INFO);
log.setLevel(Casper.Logging.WARN);
// Constants
var NO_REPETITION = 0;
var TEST_REPETITION = 0x1;
var TEST_REPEAT_LAST = 0x2;
//TEST_REPEAT_LAST = 0x4;

function keypress_event(key, ctrl) {
    // COnvert char to int
    this.keyCode = key.charCodeAt(0);
    if (ctrl) {
        this.ctrlKey = ctrl;
    }
}

//keypress_event.prototype = {
//    "type":"keypress",
//    "eventPhase":1,
//    "bubbles":true,
//    "cancelable":true,
//    "detail":0,
//    "isChar":false,
//    "charCode":98,
//    "shiftKey":false,
//    "ctrlKey":false,
//    "altKey":false,
//    "keyCode":0,
//    "metaKey":false,
//    "layerX":0,
//    "layerY":0,
//    "timeStamp":2288326230,
//    "target":null,
//    "targetXPath":'/xmlns:window[@id="komodo_main"]/xmlns:deck[@id="komodo-box"]/xmlns:vbox[@id="komodo-vbox"]/xmlns:hbox[@id="komodo-hbox"]/xmlns:vbox[@id="editorviewbox"]/xmlns:view[@id="topview"]',
//    "currentTarget":null,
//    "currentTargetXPath":"/",
//    "originalTarget":null,
//    "originalTargetXPath":'/xmlns:window[@id="komodo_main"]/xmlns:deck[@id="komodo-box"]/xmlns:vbox[@id="komodo-vbox"]/xmlns:hbox[@id="komodo-hbox"]/xmlns:vbox[@id="editorviewbox"]/xmlns:view[@id="topview"]/anonymousChild()[0]/./xul:view[@id="view-1"]/anonymousChild()[0]/./xul:tabpanels/xmlns:tabpanel[3]/xmlns:view/anonymousChild()[0]/./anonymousChild()[0]/.',
//    "enabled":true,
//    "action":"fire",
//    "waitTimeout":3000
//}

keypress_event.prototype = {
    "type":"keypress",
    "eventPhase":1,
    "bubbles":true,
    "cancelable":true,
    "detail":0,
    "isChar":false,
    "charCode":97,
    "shiftKey":false,
    "ctrlKey":false,
    "altKey":false,
    "keyCode":0,
    "metaKey":false,
    "layerX":0,
    "layerY":0,
    "timeStamp":2631337768,
    "target":null,
    "targetXPath":"/xmlns:window[@id=\"komodo_main\"]/xmlns:deck[@id=\"komodo-box\"]/xmlns:vbox[@id=\"komodo-vbox\"]/xmlns:hbox[@id=\"komodo-hbox\"]/xmlns:vbox[@id=\"editorviewbox\"]/xmlns:view[@id=\"topview\"]",
    "currentTarget":null,
    "currentTargetXPath":"/",
    "originalTarget":null,
    "originalTargetXPath":"/xmlns:window[@id=\"komodo_main\"]/xmlns:deck[@id=\"komodo-box\"]/xmlns:vbox[@id=\"komodo-vbox\"]/xmlns:hbox[@id=\"komodo-hbox\"]/xmlns:vbox[@id=\"editorviewbox\"]/xmlns:view[@id=\"topview\"]/anonymousChild()[0]/./xul:view[@id=\"view-1\"]/anonymousChild()[0]/./xul:tabpanels/xmlns:tabpanel[5]/xmlns:view/anonymousChild()[0]/./anonymousChild()[0]/.",
    "enabled":true,
    "action":"fire",
    "waitTimeout":3000,
    "stopPropagation": function() {},
    "preventDefault": function() {}
}

// example of setting up a class based test case
function test_vi_emulation() {
    // The name supplied must be the same as the class name!!
    Casper.UnitTest.TestCaseSerialClassAsync.apply(this, ["test_vi_emulation"]);
}
test_vi_emulation.prototype = new Casper.UnitTest.TestCaseSerialClassAsync();
test_vi_emulation.prototype.constructor = test_vi_emulation;

test_vi_emulation.prototype.setup = function() {
    //this.kbm = new keybindingManager();
    //this.originalConfigName = this.kbm.currentConfiguration;
    //this.vim = new VimController();
    // we need a new scintilla buffer for running our tests
    // Using an internal API here -- this should be async.
    this.view = ko.views.manager._doNewView();
    this.scimoz = this.view.scimoz;
}
test_vi_emulation.prototype.tearDown = function() {
    // Close the view, don't bother saving it
    this.view.closeUnconditionally();
}

/**
 * Used to check settings of testcase with result
 */
test_vi_emulation.prototype._passedTest = function(cmd, tags) {
    // Check if it's a knownfailure
    if (tags && tags.some(function(x) { return x == "knownfailure"; })) {
        log.warn(this.currentTest.name + " passed but is marked as a knownfailure!");
    }
}

/**
 * Log knownfailure
 */
test_vi_emulation.prototype.logKnownFailure = function(cmd, ex) {
    log.info("knownfailure: " + ex.message);
}

/**
 * Reset the vi controller. Updates internal buffer, current pos, repeat count
 * mode, operation flags, anchor.
 * @param {string} text  Buffer text to be reset with
 * @param {int} linePos  Line to place the cursor at
 */
test_vi_emulation.prototype._reset = function(text, /* "" */
                                              linePos /* 0 */) {
    if (!text) {
        text = "";
    }
    if (!linePos) {
        linePos = 0;
    }
    gVimController._internalBuffer = "";
    gVimController.repeatCount = 0;
    gVimController.operationFlags = VimController.OPERATION_NONE;
    gVimController.mode = VimController.MODE_NORMAL;
    this.scimoz.text = text;
    var currentPos = 0;
    if (linePos > 0) {
        var currentPos = this.scimoz.positionFromLine(linePos);
    }
    this.scimoz.currentPos = currentPos;
    this.scimoz.anchor = currentPos;
    this.scimoz.scrollCaret();
    this.scimoz.eOLMode = this.scimoz.SC_EOL_CRLF;
}

/**
 * Test commands that use the find char with an operation mode.
 * @param {string} cmd  The command to be run
 * @param {int} repeatCount  Number of times to repeat this command
 * @param {string} bufferOrig  Starting text with caret position marked as <|>
 * @param {string} bufferNew  Resulting text with caret position marked as <|>
 * @param {array} operationFlags  The operations to run the command with
 * @param {string} register  The register to be used for the command
 * @param {array} tags  List of specific test tag names
 */
test_vi_emulation.prototype._repeatCommand = function(cmd, repeatCount,
                                                      bufferOrig, bufferNew,
                                                      operationFlags, register,
                                                      tags) {
    this._reset();
    // <|> represents the cursor position
    log.info("repeatCommand:: cmd: " + cmd + ", repeatCount: " + repeatCount);
    log.info("repeatCommand:: bufferOrig: '" + bufferOrig + "'");
    log.info("repeatCommand:: bufferNew:  '" + bufferNew + "'");
    var cursorOrigPos = bufferOrig.indexOf("<|>");
    var bufOrig = bufferOrig.replace("<|>", "");
    // Set the buffer text in scimoz
    //this.view.setFocus();
    this.scimoz.text = bufOrig;
    //this.view.initWithBuffer(bufOrig, "Text");
    if (cursorOrigPos >= 0) {
        // Set the cursor position
        //this.scimoz.anchor = cursorOrigPos;
        //this.scimoz.currentPos = cursorOrigPos;
        this.scimoz.gotoPos(cursorOrigPos);
        // Ensure we don't drift due to caretX settings
        this.scimoz.chooseCaretX();
    }
    if (cmd.substr(0, 8) != "cmd_vim_") {
        cmd = "cmd_vim_" + cmd;
    }
    // Set repeat count and then perform then command once, should
    // result in buffer matching the bufferNew.
    gVimController.repeatCount = repeatCount;
    if (operationFlags) {
        gVimController.operationFlags = operationFlags;
    }
    if (register) {
        gVimController._currentRegister = register;
    }
    // Perform the command
    vim_doCommand(cmd);
    // Compare the results
    var cursorNewPos = bufferNew.indexOf("<|>");
    var buf = bufferNew.replace("<|>", "");
    log.info("repeatCommand:: buf:         '" + buf + "'");
    log.info("repeatCommand:: scimoz.text: '" + this.scimoz.text + "'");

    try {
        this.assertEqual(buf, this.scimoz.text, cmd + ": buffer incorrect after running command repeatedly!");
        if (cursorOrigPos >= 0) {
            // Set the cursor position
            this.assertEqual(cursorNewPos, this.scimoz.currentPos, cmd + ": cursor at incorrect position! Expected: " + cursorNewPos + ", got: " + this.scimoz.currentPos);
            // Set the cursor position
            log.debug("repeatCommand:: cursorNewPos: " + cursorNewPos);
            log.debug("repeatCommand:: currentPos  : " + this.scimoz.currentPos);
        }
    } catch(ex if ex instanceof Casper.UnitTest.AssertException) {
        //dump("Expected: " + buf + "\n");
        //dump("Actual  : " + this.scimoz.text + "\n");
        // Check if it's a knownfailure
        if (tags && tags.some(function(x) { return x == "knownfailure"; })) {
            this.logKnownFailure(cmd, ex);
            return;
        } else {
            log.warn("repeatCommand:: failure: " + ex.message);
            throw ex;
        }
    }
    this._passedTest(cmd, tags);
}

test_vi_emulation.prototype._markBuffer = function(buffer, currentPos, anchor) {
    if (typeof(currentPos) == 'undefined') currentPos = -1;
    if (typeof(anchor) == 'undefined') anchor = -1;
    if (currentPos >= 0) {
        buffer = buffer.substr(0, currentPos) + "<|>" + buffer.substr(currentPos);
    }
    if (anchor >= 0) {
        if (currentPos >= 0 && anchor > currentPos)
            anchor += 3;
        buffer = buffer.substr(0, anchor) + "<^>" + buffer.substr(anchor);
    }
    return buffer;
}

/**
 * Test commands that use the find char with an operation mode.
 * @param {string} cmd  The command to be run
 * @param {array} buffers  Contains the text and caret positions
 * @param {string} register  The register to be used for the command
 * @param {object} options  Options can have any of these values:
 *        testRepeat {boolean}  Test the command using a repeat count.
 *        operationFlags {array}  The operations to run the command with
 *        tags {array}  List of specific test tag names
 *        resetMode {boolean}  Perform a vi basic reset before running.
 *        mode {int}  vi mode to start in, one of VimController.MODE_XXX.
 *        visualMode {int}  Vi visual mode, on of VimController.VISUAL_XXX.
 */
test_vi_emulation.prototype._runRegisterCommand = function(cmd,
                                                   buffers,
                                                   register,
                                                   options) {
    var testRepeat = options && options.testRepeat;
    var operationFlags = options && options.operationFlags;
    var tags = options && options.tags;
    var resetMode = options && options.resetMode;
    var mode = options && options.mode;
    var visualMode = options && options.visualMode;
    log.info("\n\n*************************************");
    log.info(cmd);
    log.info("*************************************\n");
    if (typeof(resetMode) == 'undefined' || resetMode) {
        this._reset();
    }
    if (typeof(operationFlags) == 'undefined') {
        operationFlags = 0;
    }
    // <|> represents the cursor position
    var bufferOrig = buffers[0];
    var anchorOrigPos = bufferOrig.indexOf("<^>");
    var bufOrig = bufferOrig.replace("<^>", "");
    var cursorOrigPos = bufOrig.indexOf("<|>");
    bufOrig = bufOrig.replace("<|>", "");
    // Set the buffer text in scimoz
    //this.view.setFocus();
    this.scimoz.text = bufOrig;
    //this.view.initWithBuffer(bufOrig, "Text");
    if (cursorOrigPos >= 0) {
        // Set the cursor position
        //this.scimoz.anchor = cursorOrigPos;
        //this.scimoz.currentPos = cursorOrigPos;
        this.scimoz.gotoPos(cursorOrigPos);
        // Ensure we don't drift due to caretX settings
        this.scimoz.chooseCaretX();
    }
    if (anchorOrigPos >= 0) {
        this.scimoz.anchor = anchorOrigPos;
    }
    cmd = "cmd_vim_" + cmd;
    // buffersNew is a array of buffers that we should get, one for each
    // new iteration of the command.
    var buf;
    log.debug("cursorOrigPos: " + cursorOrigPos);
    for (var i=1; i < buffers.length; i++) {
        buf = buffers[i];
        // Setup for the command.
        if (typeof(mode) != 'undefined') {
            gVimController.mode = mode;
        }
        if (typeof(visualMode) != 'undefined') {
            gVimController._visualMode = visualMode;
            if (visualMode == VimController.VISUAL_LINE) {
                this.scimoz.selectionMode = this.scimoz.SC_SEL_LINES;
            }
        }
        gVimController.operationFlags = operationFlags;
        if (register) {
            gVimController._currentRegister = register;
        }
        // Perform the command
        vim_doCommand(cmd);
        // Compare the results
        var anchorNewPos = buf.indexOf("<^>");
        buf = buf.replace("<^>", "");
        var cursorNewPos = buf.indexOf("<|>");
        buf = buf.replace("<|>", "");
        log.debug("buf[" + i + "]:      '" + buf + "'");
        log.debug("scimoz.text: '" + this.scimoz.text + "'");
        try {
            this.assertEqual(buf, this.scimoz.text, cmd + ": buffer "+i+" incorrect after running command!");
            if (cursorNewPos >= 0) {
                // Check the cursor position
                log.debug("cursorNewPos: " + cursorNewPos);
                log.debug("currentPos  : " + this.scimoz.currentPos);
                this.assertEqual(cursorNewPos, this.scimoz.currentPos, cmd + ": cursor at incorrect position! Expected: " + cursorNewPos + ", got: " + this.scimoz.currentPos);
            }
            if (anchorNewPos >= 0) {
                // Check the anchor position
                log.debug("anchorNewPos: " + anchorNewPos);
                log.debug("anchor      : " + this.scimoz.anchor);
                this.assertEqual(anchorNewPos, this.scimoz.anchor, cmd + ": anchor at incorrect position! Expected: " + anchorNewPos + ", got: " + this.scimoz.anchor);
            }
        } catch(ex if ex instanceof Casper.UnitTest.AssertException) {
            // Check if it's a knownfailure
            if (tags && tags.some(function(x) { return x == "knownfailure"; })) {
                this.logKnownFailure(cmd, ex);
                return;
            } else {
                log.warn("failure: " + ex.message + "\n" +
                         "  buf[" + i + "]:      '" + this._markBuffer(buf, cursorNewPos, anchorNewPos) + "'\n" +
                         "  scimoz.text: '" + this._markBuffer(this.scimoz.text, this.scimoz.currentPos, this.scimoz.anchor) + "'\n");
                throw ex;
            }
        }
    }

    if (testRepeat) {
        var len = buffers.length - 1;
        this._repeatCommand(cmd, len, bufferOrig, buffers[len], operationFlags, register, tags);
    }
    this._passedTest(cmd, tags);
}

/**
 * Test commands that use the find char with an operation mode.
 * @param {string} cmd  The command to be run
 * @param {array} buffers  Contains the text and caret positions
 * @param {object} options  Options can have any of these values:
 *        testRepeat {boolean}  Test the command using a repeat count.
 *        operationFlags {array}  The operations to run the command with
 *        tags {array}  List of specific test tag names
 *        resetMode {boolean}  Perform a vi basic reset before running.
 *        mode {int}  vi mode to start in, one of VimController.MODE_XXX.
 *        visualMode {int}  Vi visual mode, on of VimController.VISUAL_XXX.
 */
test_vi_emulation.prototype._runCommand = function(cmd,
                                                   buffers,
                                                   options) {
    this._runRegisterCommand(cmd, buffers, null, options);
}

/**
 * Test commands that use the find char with an operation mode.
 * @param {string} cmd  The command to be run
 * @param {array} buffers  Contains the text and caret positions
 * @param {array} tags  List of specific test tag names
 */
test_vi_emulation.prototype._runTextCommand = function(cmd, buffers, tags) {
    //log.setLevel(Casper.Logging.DEBUG);
    //vimlog.setLevel(ko.logging.LOG_DEBUG);
    log.info("\n\n*******  runTextCommand  ************");
    log.info(cmd);
    log.info("*************************************\n");
    this._reset();
    // <|> represents the cursor position
    var bufferOrig = buffers[0];

    // Get the cursor position
    var cursorOrigPos = bufferOrig.indexOf("<|>");
    if (cursorOrigPos >= 0) {
        bufferOrig = bufferOrig.replace("<|>", "");
    }
    // Get the anchor position
    var anchorPos = bufferOrig.indexOf("<^>");
    if (anchorPos >= 0) {
        bufferOrig = bufferOrig.replace("<^>", "");
    }

    // Set the buffer text in scimoz
    //this.view.setFocus();
    this.scimoz.text = bufferOrig;

    if (cursorOrigPos >= 0) {
        // Set the cursor position
        this.scimoz.gotoPos(cursorOrigPos);
        // Ensure we don't drift due to caretX settings
        this.scimoz.chooseCaretX();
    }
    if (anchorPos >= 0) {
        // Update the anchor position
        this.scimoz.anchor = anchorPos;
    }

    var buf;
    for (var i=1; i < buffers.length; i++) {
        buf = buffers[i];
        // Perform the command
        gVimController.operationFlags = VimController.OPERATION_NONE;
        //if (register) {
        //    gVimController._currentRegister = register;
        //}
        gVimController.findAndRunCommand(cmd);
        // Compare the results
        log.debug("buf[" + i + "]:      '" + buf + "'");
        log.debug("scimoz.text: '" + this.scimoz.text + "'");
        try {
            this.assertEqual(buf, this.scimoz.text, cmd + ": buffer "+i+" incorrect after running command!");
        } catch(ex if ex instanceof Casper.UnitTest.AssertException) {
            // Check if it's a knownfailure
            if (tags && tags.some(function(x) { return x == "knownfailure"; })) {
                this.logKnownFailure(cmd, ex);
                return;
            } else {
                log.warn("failure: " + ex.message);
                throw ex;
            }
        }
    }
    this._passedTest(cmd, tags);
}

/**
 * Test commands that use the find char with an operation mode.
 * @param {string} cmd  The command to be run
 * @param {string} buffer  Contains the text and caret positions
 * @param {string} register  The register to be used for the command
 * @param {boolean} testRepeat  Test the command using a repeat count.
 * @param {array} operations  The operations to run the command with
 * @param {array} tags  List of specific test tag names
 * @param {boolean} resetMode  Perform a vi basic reset before running.
 * @param {int} forcedRepeatCount  Set repeat count to this value on every op
 */
test_vi_emulation.prototype._runRegisterOperationCommands = function(cmd, buffer,
                                                             register /* null */,
                                                             testRepeat /* false */,
                                                             operations /* [ OPERATION_NONE ] */,
                                                             tags /* null */,
                                                             resetMode /* true */,
                                                             forcedRepeatCount /* 1 */) {
    // Initialize the arguments if none provided
    if (!operations) {
        operations = [ VimController.OPERATION_NONE ];
    }
    if (!tags) {
        tags = null;
    }
    if (typeof(resetMode) == 'undefined') {
        resetMode = true;
    }
    if (!forcedRepeatCount) {
        forcedRepeatCount = 1;
    }

    log.info("\n\n*************************************");
    log.info(cmd);
    log.info("*************************************\n");
    log.debug("raw buffer: '" + buffer + "'");
    if (resetMode) {
        this._reset();
    }
    var positions = {};
    var num_positions = 0;
    var posRegex = new RegExp("<[|0-9]+>");
    var match = buffer.match(posRegex);
    var pos = -1;
    while (match != null) {
        if (match[0] == "<|>") {
            positions[0] = match.index;
        } else {
            positions[parseInt(match[0].substr(1))] = match.index;
        }
        num_positions += 1;
        buffer = buffer.replace(match[0], '');
        //dump("buffer now: " + buffer + "\n");
        match = buffer.match(posRegex);
    }
    if (num_positions < 2) {
        log.warn("No positions in buffer, aborting");
        return;
    }

    log.debug("buffer now: '" + buffer + "'");
    log.debug("Positions:");
    for (var i=0; i < num_positions; i++) {
        log.debug("  positions[" + i + "]: " + positions[i]);
    }

    var cursorOrigPos = positions[0];
    cmd = "cmd_vim_" + cmd;
    // buffersNew is a array of buffers that we should get, one for each
    // new iteration of the command.
    for (var opPos=0; opPos < operations.length; opPos++) {
        var operationFlags = operations[opPos];
        log.info("cmd: " + cmd + ", operationFlags: " + operationFlags);
        // Set the buffer text in scimoz
        //this.view.setFocus();
        this.scimoz.text = buffer;
        if (cursorOrigPos >= 0) {
            // Set the cursor position
            //this.scimoz.anchor = cursorOrigPos;
            //this.scimoz.currentPos = cursorOrigPos;
            this.scimoz.gotoPos(cursorOrigPos);
            // Ensure we don't drift due to caretX settings
            this.scimoz.chooseCaretX();
        }
        var compareBuf = buffer;
        var newCursorPos = cursorOrigPos;
        var expectedInternalBuffer;
        var fromPos = cursorOrigPos;
        var toPos = -1;
        gVimController.repeatCount = forcedRepeatCount;
        for (var i=1; i < num_positions; i++) {
            // Reset the copy buffer
            gVimController._internalBuffer = "";
            log.debug("i: " + i);
            if (i > 0) {
                fromPos = positions[i-1];
            }
            toPos = positions[i];
            // Setup the expected results
            if (toPos > fromPos) {
                expectedInternalBuffer = buffer.slice(fromPos, toPos);
            } else {
                expectedInternalBuffer = buffer.slice(toPos, fromPos);
            }
            if (operationFlags & VimController.OPERATION_DELETE) {
                // Cursor does not actually move anywhere, unless changing or deleting backwards
                if (toPos <= cursorOrigPos) {
                    newCursorPos = toPos;
                    compareBuf = buffer.slice(0, toPos) + buffer.slice(cursorOrigPos);
                } else {
                    newCursorPos = cursorOrigPos;
                    compareBuf = buffer.slice(0, cursorOrigPos) + buffer.slice(toPos);
                }
            } else if (operationFlags == VimController.OPERATION_YANK) {
                // Cursor will not actually move anywhere unless yanking
                // backwards
                this.scimoz.gotoPos(fromPos);
                // Ensure we don't drift due to caretX settings
                this.scimoz.chooseCaretX();
                log.debug("Position moved to: " + fromPos);
                if (toPos > fromPos) {
                    // Move the cursor to the previous position
                    newCursorPos = fromPos;
                } else {
                    newCursorPos = toPos;
                }
            } else {
                newCursorPos = toPos;
            }
            // Perform the command
            gVimController.operationFlags = operationFlags;
            if (register) {
                gVimController._currentRegister = register;
            }
            vim_doCommand(cmd);
            // Test the results
            log.info("fromPos: "+fromPos+", toPos: "+toPos);
            log.info("newCursorPos: " + newCursorPos);
            if (operationFlags) {
                log.info("expectedInternalBuffer: '" + expectedInternalBuffer + "'");
            }
            log.info("compareBuf:  '" + compareBuf + "'");
            log.info("scimoz.text: '" + this.scimoz.text + "'");
            try {
                this.assertEqual(compareBuf, this.scimoz.text, cmd + "(op: " +operationFlags+ "): buffer "+i+" incorrect after running command!");
                if (cursorOrigPos >= 0) {
                    // Check the cursor position
                    this.assertEqual(newCursorPos, this.scimoz.currentPos, cmd + "(op: " +operationFlags+ "): cursor at incorrect position! Expected: " + newCursorPos + ", got: " + this.scimoz.currentPos);
                }
                if (operationFlags) {
                    log.debug("copyBuffer: '"+gVimController._internalBuffer+"', expected: '"+expectedInternalBuffer+"'");
                    this.assertEqual(expectedInternalBuffer, gVimController._internalBuffer, cmd + "(op: " +operationFlags+ "): copy buffer "+i+" incorrect after running command!");
                    if (operationFlags == VimController.OPERATION_CHANGE) {
                        this.assertEqual(gVimController.mode, VimController.MODE_INSERT, cmd + ": change command did not enter insert mode!");
                    }
                }

                // Test repeating the command
                if (testRepeat && ((i+1) == num_positions)) {
                    log.debug("Running repeat for cmd: " + cmd);
                    var repeatOrigBuffer = buffer.substr(0, cursorOrigPos) + "<|>" +
                                           buffer.substr(cursorOrigPos);
                    if (operationFlags == VimController.OPERATION_YANK) {
                        // Cursor will not actually move anywhere unless yanking
                        // backwards
                        if (newCursorPos > cursorOrigPos) {
                            // Move the cursor to the previous position
                            newCursorPos = cursorOrigPos;
                        }
                    }
                    var repeatResultBuffer = compareBuf.substr(0, newCursorPos) + "<|>" +
                                           compareBuf.substr(newCursorPos);
                    this._repeatCommand(cmd, i,
                                        repeatOrigBuffer,
                                        repeatResultBuffer,
                                        operationFlags, register, tags);
                    // Test using cmd_vim_repeatLastCommand "." command
                    //if (operationFlags & VimController.OPERATION_DELETE) {
                    //    this._repeatCommand("cmd_vim_repeatLastCommand", i,
                    //                        repeatOrigBuffer,
                    //                        repeatResultBuffer,
                    //                        operationFlags, register, tags);
                    //}
                }
            } catch(ex if ex instanceof Casper.UnitTest.AssertException) {
                // Check if it's a knownfailure
                if (tags && tags.some(function(x) { return x == "knownfailure"; })) {
                    this.logKnownFailure(cmd, ex);
                    return;
                } else {
                    log.warn("failure: " + ex.message);
                    throw ex;
                }
            }
        }
    }
    this._passedTest(cmd, tags);
}

/**
 * Test commands that use specific operation modes.
 * @param {string} cmd  The command to be run
 * @param {string} buffer  Contains the text and caret positions
 * @param {boolean} testRepeat  Test the command using a repeat count.
 * @param {array} operations  The operations to run the command with
 * @param {array} tags  List of specific test tag names
 */
test_vi_emulation.prototype._runOperationCommands = function(cmd, buffer,
                                                             testRepeat /* false */,
                                                             operations /* [ OPERATION_NONE ] */,
                                                             tags /* null */) {
    this._runRegisterOperationCommands(cmd, buffer, null, testRepeat, operations, tags);
}


/**
 * Test commands that use the find char with an operation mode.
 * @param {string} cmd  The command to be run
 * @param {string} buffer  Contains the text and caret positions
 * @param {string} charToFind  The character to search for
 * @param {int} searchDirection  Direction to search in
 * @param {boolean} t_style  Use the position before|after "t" command semantics
 * @param {string} register  The register to be used for the command
 * @param {boolean} testRepeat  Test the command using a repeat count.
 * @param {array} operations  The operations to run the command with
 * @param {array} tags  List of specific test tag names
 * @param {int} forcedRepeatCount  Set repeat count to this value on every op
 */
test_vi_emulation.prototype._runFindCharOperation = function(cmd, buffer,
                                                             charToFind,
                                                             searchDirection,
                                                             t_style /* false */,
                                                             register /* null */,
                                                             testRepeat /* false */,
                                                             operations /* [ OPERATION_NONE ] */,
                                                             tags /* null */,
                                                             forcedRepeatCount /* 1 */) {
    this._reset();
    // Set the character we are looking for
    gVimController._lastFindChar = charToFind;
    gVimController._findCharDirection = searchDirection;
    if (t_style) {
        gVimController._lastMovePosBefore = true;
    } else {
        gVimController._lastMovePosBefore = false;
    }
    gVimController.mode = VimController.MODE_FIND_CHAR;
    gVimController._lastRepeatCount = 1;

    this._runRegisterOperationCommands(cmd, buffer, register, testRepeat,
                                       operations, tags, false /* resetMode */,
                                       forcedRepeatCount);
}


/**
 * Test commands that use searching commands combined with an operation mode.
 * @param {string} cmd  The search command to be run.
 * @param {string} buffer  Contains the text and caret positions
 * @param {string} searchText  The text to search for
 * @param {int} searchDirection  Direction to search in
 * @param {string} register  The register to be used for the command
 * @param {boolean} testRepeat  Test the command using a repeat count.
 * @param {array} operations  The operations to run the command with
 * @param {array} tags  List of specific test tag names
 * @param {int} forcedRepeatCount  Set repeat count to this value on every op
 */
test_vi_emulation.prototype._runSearchCommandWithOperation = function(
                            cmd,
                            buffer,
                            searchText,
                            searchDirection,
                            register /* null */,
                            testRepeat /* false */,
                            operations /* [ OPERATION_NONE ] */,
                            tags /* null */,
                            forcedRepeatCount /* 1 */) {
    this._reset();
    // Set the string we are looking for, this is done using the find mru.
    ko.mru.add("find-patternMru", searchText, true);
    gVimController._searchDirection = searchDirection;
    gVimController.mode = VimController.MODE_SEARCH;
    gVimController._lastRepeatCount = 1;

    this._runRegisterOperationCommands(cmd, buffer, register, testRepeat,
                                       operations, tags, false /* resetMode */,
                                       forcedRepeatCount);
}


test_vi_emulation.prototype.test_basic_movement = function() {
    // whichwrap sets which commands allow the cursor to move past eol points
    gVimController.settings["whichwrap"] = "";
    this._runOperationCommands("right",
                               "this is<|> <1>m<2>y<3> <4>b<5>u<6>f<7>f<8>e<9>r<10><11><12>\r\nnext line\r\n",
                               TEST_REPETITION,
                               [VimController.OPERATION_NONE,
                                VimController.OPERATION_YANK,
                                VimController.OPERATION_DELETE,
                                VimController.OPERATION_CHANGE]);
    gVimController.settings["whichwrap"] = "hl<>";
    this._runOperationCommands("right",
                               "this is<|> <1>m<2>y<3> <4>b<5>u<6>f<7>f<8>e<9>r<10>\r\n<11>n<12>e<13>xt line\r\n",
                               TEST_REPETITION,
                               [VimController.OPERATION_NONE,
                                VimController.OPERATION_YANK,
                                VimController.OPERATION_DELETE,
                                VimController.OPERATION_CHANGE]);
    this._runOperationCommands("left",
                               "<9><8><7>t<6>h<5>i<4>s<3> <2>i<1>s<|> my buffer\r\n",
                               TEST_REPETITION,
                               [VimController.OPERATION_NONE,
                                VimController.OPERATION_YANK,
                                VimController.OPERATION_DELETE,
                                VimController.OPERATION_CHANGE]);
    this._runOperationCommands("lineNext",
                               "this <|>is\r\nmy bu<1>ffer\r\nThird<2> line\r\n",
                               TEST_REPETITION,
                               [VimController.OPERATION_NONE,
                                VimController.OPERATION_YANK,
                                VimController.OPERATION_DELETE,
                                VimController.OPERATION_CHANGE]);
    this._runOperationCommands("linePrevious",
                               "this <2>is\r\nmy bu<1>ffer\r\nThird<|> line\r\n",
                               TEST_REPETITION,
                               [VimController.OPERATION_NONE,
                                VimController.OPERATION_YANK,
                                VimController.OPERATION_DELETE,
                                VimController.OPERATION_CHANGE]);
}

test_vi_emulation.prototype.test_word_right = function() {
    this._runOperationCommands("wordRight",
                               "th<|>is <1>is <2>my <3>code<4>-<5>buffer<6>\r\n",
                               TEST_REPETITION,
                               [VimController.OPERATION_NONE,
                                VimController.OPERATION_YANK,
                                VimController.OPERATION_DELETE]);
    // One of the rare cases where change operation works differently to delete
    this._runOperationCommands("wordRight",
                               "th<|>is<1> <2>is<3> <4>my<5> <6>code<7>-<8>buffer<9>\r\n",
                               NO_REPETITION,
                               [VimController.OPERATION_CHANGE]);
    this._repeatCommand("wordRight", 3,
                        "th<|>is is my code-buffer\r\n",
                        "th<|> code-buffer\r\n",
                        VimController.OPERATION_CHANGE,
                        null /* register */,
                        null /* tags */);

    // Word right end works differently in an OP mode - see bug 72005.
    this._runOperationCommands("wordRightEnd",
                               "th<|>i<1>s i<2>s m<3>y cod<4>e<5>-buffe<6>r\r\n",
                               TEST_REPETITION,
                               [VimController.OPERATION_NONE]);
    this._runOperationCommands("wordRightEnd",
                               "th<|>is<1> is<2> my<3> code<4>-<5>buffer<6>\r\n",
                               TEST_REPETITION,
                               [VimController.OPERATION_DELETE,
                                VimController.OPERATION_YANK,
                                VimController.OPERATION_CHANGE]);
}

test_vi_emulation.prototype.test_word_left = function() {
    this._runOperationCommands("wordLeft",
                               "<5><4>this <3>is <2>my <1>bu<|>ffer\r\n",
                               TEST_REPETITION,
                               [VimController.OPERATION_NONE,
                                VimController.OPERATION_YANK,
                                VimController.OPERATION_DELETE,
                                VimController.OPERATION_CHANGE]);
}

test_vi_emulation.prototype.test_word_right_past_punctuation = function() {
    this._runOperationCommands("wordRightPastPunctuation",
                               "th<|>is <1>is <2>my <3>code-buffer\r\n<4>",
                               TEST_REPETITION,
                               [VimController.OPERATION_NONE,
                                VimController.OPERATION_YANK,
                                VimController.OPERATION_DELETE]);
    // One of the rare cases where change operation works differently to delete
    this._runOperationCommands("wordRightPastPunctuation",
                               "th<|>is<1> <2>is<3> <4>my<5> <6>code-buffer\r\n<7>",
                               TEST_REPETITION,
                               [VimController.OPERATION_CHANGE],
                               ["knownfailure"]);

    this._runOperationCommands("wordRightPastPunctuation",
                               "i<|>f <1>(my.func.callthis() <2>&& <3>this.bogus) <4>{\r\n<5>",
                               TEST_REPETITION,
                               [VimController.OPERATION_NONE,
                                VimController.OPERATION_YANK,
                                VimController.OPERATION_DELETE,
                                VimController.OPERATION_CHANGE]);

    // This command works differently in normal (non-operation) mode.
    this._runOperationCommands("wordRightEndPastPunctuation",
                               "<|>i<1>f (my.func.callthis(<2>) &<3>& this.bogus<4>) {<5>\r\n<6>",
                               TEST_REPETITION,
                               [VimController.OPERATION_NONE]);
    this._runOperationCommands("wordRightEndPastPunctuation",
                               "<|>if<1> (my.func.callthis()<2> &&<3> this.bogus)<4> {<5>\r\n<6>",
                               TEST_REPETITION,
                               [VimController.OPERATION_YANK,
                                VimController.OPERATION_DELETE,
                                VimController.OPERATION_CHANGE]);
}

test_vi_emulation.prototype.test_word_left_past_punctuation = function() {
    this._runOperationCommands("wordLeftPastPunctuation",
                               "<5><4>if <3>(my.func.callthis() <2>&& <1>this.bog<|>us) {\r\n",
                               TEST_REPETITION,
                               [VimController.OPERATION_NONE,
                                VimController.OPERATION_YANK,
                                VimController.OPERATION_DELETE,
                                VimController.OPERATION_CHANGE]);
}

test_vi_emulation.prototype.test_line_movement = function() {
    this._runOperationCommands("homeAbsolute",
                               "    this is\r\n<1>    my bu<|>ffer\r\n",
                               TEST_REPETITION,
                               [VimController.OPERATION_NONE,
                                VimController.OPERATION_YANK,
                                VimController.OPERATION_DELETE,
                                VimController.OPERATION_CHANGE]);
    this._runOperationCommands("homeAbsolute",
                               "    this is\r\n<1><|>    my buffer\r\n",
                               TEST_REPETITION,
                               [VimController.OPERATION_NONE,
                                VimController.OPERATION_YANK,
                                VimController.OPERATION_DELETE,
                                VimController.OPERATION_CHANGE]);
    this._runOperationCommands("homeAbsolute",
                               "    this is\r\n<1>  <|>  my buffer\r\n",
                               TEST_REPETITION,
                               [VimController.OPERATION_NONE,
                                VimController.OPERATION_YANK,
                                VimController.OPERATION_DELETE,
                                VimController.OPERATION_CHANGE]);
    this._runOperationCommands("home",
                               "    this is\r\n<2>    <1>my bu<|>ffer\r\n",
                               NO_REPETITION,
                               [VimController.OPERATION_NONE,
                                VimController.OPERATION_YANK,
                                VimController.OPERATION_DELETE,
                                VimController.OPERATION_CHANGE]);
    this._runOperationCommands("home",
                               "    this is\r\n<|>    <1>my buffer\r\n",
                               NO_REPETITION,
                               [VimController.OPERATION_NONE,
                                VimController.OPERATION_YANK,
                                VimController.OPERATION_DELETE,
                                VimController.OPERATION_CHANGE]);
    this._runOperationCommands("end",
                               "this is\r\nmy bu<|>ffer<1><2>\r\n",
                               TEST_REPETITION,
                               [VimController.OPERATION_NONE,
                                VimController.OPERATION_YANK,
                                VimController.OPERATION_DELETE,
                                VimController.OPERATION_CHANGE]);
}

test_vi_emulation.prototype.test_insert_commands = function() {
    this._runOperationCommands("insert",
                               "this is\r\nmy bu<|><1>ffer\r\n");
    this._runOperationCommands("insertHome",
                               "this is\r\n<1>my bu<|>ffer\r\n");
    this._runCommand("insert_newline_previous",
                     ["this is\r\nmy bu<|>ffer\r\n",
                      "this is\r\n<|>\r\nmy buffer\r\n"]);
    this._runCommand("insert_newline_previous",
                     ["    this is\r\n    my bu<|>ffer\r\n",
                      "    this is\r\n    <|>\r\n    my buffer\r\n"]);
    this._runCommand("insert_newline_next",
                     ["this is\r\nmy bu<|>ffer\r\n",
                      "this is\r\nmy buffer\r\n<|>\r\n"]);
    this._runCommand("insert_newline_next",
                     ["    this is\r\n    my bu<|>ffer\r\n",
                      "    this is\r\n    my buffer\r\n    <|>\r\n"]);
    this._runOperationCommands("append",
                               "this is\r\nmy bu<|>f<1>fer\r\n");
    //log.setLevel(Casper.Logging.DEBUG);
    this._runOperationCommands("appendEnd",
                               "this is\r\nmy bu<|>ffer<1>\r\n");
    //log.setLevel(Casper.Logging.WARN);
}

test_vi_emulation.prototype.test_section_movement = function() {
    return;
    this._runCommand("moveToScreenTop", "this is\r\nmy bu<|>ffer\r\n", "this <|>is\r\nmy buffer\r\n");
    this._runCommand("moveToScreenCenter", "this is\r\nmy bu<|>ffer\r\n", "this <|>is\r\nmy buffer\r\n");
    this._runCommand("moveToScreenBottom", "this is\r\nmy bu<|>ffer\r\n", "this <|>is\r\nmy buffer\r\n");
    this._runCommand("moveSentenceBegin", "this is\r\nmy bu<|>ffer\r\n", "this <|>is\r\nmy buffer\r\n");
    this._runCommand("moveSentenceEnd", "this is\r\nmy bu<|>ffer\r\n", "this <|>is\r\nmy buffer\r\n");
    this._runCommand("moveParagraphBegin", "this is\r\nmy bu<|>ffer\r\n", "this <|>is\r\nmy buffer\r\n");
    this._runCommand("moveParagraphEnd", "this is\r\nmy bu<|>ffer\r\n", "this <|>is\r\nmy buffer\r\n");
    this._runCommand("moveFunctionPrevious", "this is\r\nmy bu<|>ffer\r\n", "this <|>is\r\nmy buffer\r\n");
    this._runCommand("moveFunctionNext", "this is\r\nmy bu<|>ffer\r\n", "this <|>is\r\nmy buffer\r\n");
    this._runCommand("pageDown", "this is\r\nmy bu<|>ffer\r\n", "this <|>is\r\nmy buffer\r\n");
    this._runCommand("pageUp", "this is\r\nmy bu<|>ffer\r\n", "this <|>is\r\nmy buffer\r\n");
}

test_vi_emulation.prototype.test_scrolling_movement = function() {
    var lines = [];
    for (var i=0; i < 100; i++) {
        lines.push(i);
    }
    //lines[50] = "<|>50";
    var text = lines.join("\r\n");

    var cmd = "cmd_vim_lineScrollUp";
    this._reset(text, 50);
    var top_line = this.scimoz.firstVisibleLine;
    vim_doCommand(cmd);
    this.assertEqual(top_line - 1, this.scimoz.firstVisibleLine, cmd + ": line did not scroll up! " + (top_line - 1) + " != " + this.scimoz.firstVisibleLine);
    gVimController.repeatCount = 10;
    vim_doCommand(cmd);
    this.assertEqual(top_line - 11, this.scimoz.firstVisibleLine, cmd + ": line did not scroll up 10x! " + (top_line - 11) + " != " + this.scimoz.firstVisibleLine);
    gVimController.repeatCount = 1;

    cmd = "cmd_vim_lineScrollDown";
    this._reset(text, 50);
    top_line = this.scimoz.firstVisibleLine;
    vim_doCommand(cmd);
    this.assertEqual(top_line + 1, this.scimoz.firstVisibleLine, cmd + ": line did not scroll down! " + (top_line + 1) + " != " + this.scimoz.firstVisibleLine);
    gVimController.repeatCount = 10;
    vim_doCommand(cmd);
    this.assertEqual(top_line + 11, this.scimoz.firstVisibleLine, cmd + ": line did not scroll down 10x! " + (top_line + 11) + " != " + this.scimoz.firstVisibleLine);
    gVimController.repeatCount = 1;

    cmd = "gotoLine";
    cmd_vim_gotoLine(this.scimoz, 1);
    var currentLine = this.scimoz.lineFromPosition(this.scimoz.currentPos);
    this.assertEqual(currentLine, 0, "goto line: current line: " + currentLine + " != 0");
    cmd_vim_gotoLine(this.scimoz, 77);
    var currentLine = this.scimoz.lineFromPosition(this.scimoz.currentPos);
    this.assertEqual(currentLine, 76, "goto line: current line: " + currentLine + " != 77");
}

test_vi_emulation.prototype.test_paste_commands = function() {
    // Set the paste buffer
    gVimController._registers["a"] = "is ";
    this._runRegisterCommand("paste",
                             ["this is my <|>buffer\r\n",
                              "this is my is <|>buffer\r\n",
                              "this is my is is <|>buffer\r\n",
                             ],
                             "a",
                             { testRepeat: TEST_REPETITION });
    this._runRegisterCommand("pasteAfter",
                             ["this is my <|>buffer\r\n",
                              "this is my bis <|>uffer\r\n",
                              "this is my bis uis <|>ffer\r\n",
                             ],
                             "a");
    // Repitition works a little different with pasteAfter.
    this._repeatCommand("pasteAfter", 2,
                        "this is my <|>buffer\r\n",
                        "this is my bis is <|>uffer\r\n",
                        VimController.OPERATION_NONE,
                        "a");
    // Ensure we do not paste past the end of the line.
    this._runRegisterCommand("pasteAfter",
                             ["this is my buffer<|>\r\n",
                              "this is my bufferis <|>\r\n",
                              "this is my bufferis is <|>\r\n",
                             ],
                             "a",
                             { testRepeat: TEST_REPETITION });
    // Try multiline pasting.
    gVimController._registers["a"] = "One line.\r\n";
    this._runRegisterCommand("paste",
                             ["this is my <|>buffer\r\n",
                              "<|>One line.\r\nthis is my buffer\r\n",
                              "<|>One line.\r\nOne line.\r\nthis is my buffer\r\n",
                              "<|>One line.\r\nOne line.\r\nOne line.\r\nthis is my buffer\r\n",
                             ],
                             "a",
                             { testRepeat: TEST_REPETITION });
    this._runRegisterCommand("pasteAfter",
                             ["this is my <|>buffer\r\n",
                              "this is my buffer\r\n<|>One line.\r\n",
                              "this is my buffer\r\nOne line.\r\n<|>One line.\r\n",
                              "this is my buffer\r\nOne line.\r\nOne line.\r\n<|>One line.\r\n",
                             ],
                             "a");
    // Repitition works a little different with pasteAfter.
    this._repeatCommand("pasteAfter", 3,
                        "this is my <|>buffer\r\n",
                        "this is my buffer\r\n<|>One line.\r\nOne line.\r\nOne line.\r\n",
                        VimController.OPERATION_NONE,
                        "a");
}


test_vi_emulation.prototype.test_search_commands = function() {
    // Add word we will search for
    ko.mru.add("find-patternMru", "word", true);
    // Reset the search variables
    gVimController._searchDirection = VimController.SEARCH_FORWARD;
    gVimController._searchOptions = [];
    gVimController.settings["ignorecase"] = false;
    gVimController.settings["smartcase"] = false;

    this._runOperationCommands("findNext",
                               "word <|>is the search <1>word\r\nmy second search <2>word searched, got <3>word! Done!\r\n",
                               //TEST_REPETITION,    // Fails
                               NO_REPETITION,
                               [VimController.OPERATION_NONE,
                                VimController.OPERATION_YANK,
                                VimController.OPERATION_DELETE,
                                VimController.OPERATION_CHANGE]);
                               // Fails in repitition, i.e. "2n"
                               //["knownfailure"]);
    this._runOperationCommands("findPrevious",
                               "<4>word is the search <3>word\r\nmy second search <2>word searched, got <1>word! Done!<|>\r\n",
                               //TEST_REPETITION,    // Fails
                               NO_REPETITION,
                               [VimController.OPERATION_NONE,
                                VimController.OPERATION_YANK,
                                VimController.OPERATION_DELETE,
                                VimController.OPERATION_CHANGE]);
                               // Fails in repitition, i.e. "2n"
                               //["knownfailure"]);
    this._runOperationCommands("findPrevious",
                               "word is the search <1>wor<|>d\r\n",
                               //TEST_REPETITION,    // Fails
                               NO_REPETITION,
                               [VimController.OPERATION_NONE,
                                VimController.OPERATION_YANK,
                                VimController.OPERATION_DELETE,
                                VimController.OPERATION_CHANGE],
                               // Fails, it should pickup word at cursor position
                               ["knownfailure"]);

    // Try some case sensitive searches, case sensitive by default
    this._runOperationCommands("findNext",
                               "word <|>is the Word to search <1>word\r\nmy second Word to search <2>word searched, got <3>word! Done!\r\n",
                               NO_REPETITION,
                               [VimController.OPERATION_NONE,
                                VimController.OPERATION_YANK,
                                VimController.OPERATION_DELETE,
                                VimController.OPERATION_CHANGE]);
    // Case insensitive now
    gVimController._searchOptions = ["c"];
    this._runOperationCommands("findNext",
                               "word <|>is the <1>Word to search <2>word\r\nmy second <3>Word to search <4>word searched, got <5>word! Done!\r\n",
                               NO_REPETITION,
                               [VimController.OPERATION_NONE,
                                VimController.OPERATION_YANK,
                                VimController.OPERATION_DELETE,
                                VimController.OPERATION_CHANGE]);
    // Reset back to normal case sensitive now
    gVimController._searchOptions = [];

    // Test smartcase setting
    // Add word we will search for
    gVimController.settings["smartcase"] = true;
    this._runOperationCommands("findNext",
                               "word <|>is the <1>Word to search <2>word\r\nmy second <3>Word to search <4>word searched, got <5>word! Done!\r\n",
                               NO_REPETITION,
                               [VimController.OPERATION_NONE,
                                VimController.OPERATION_YANK,
                                VimController.OPERATION_DELETE,
                                VimController.OPERATION_CHANGE]);
    ko.mru.add("find-patternMru", "Word", true);
    this._runOperationCommands("findNext",
                               "word <|>is the <1>Word to search word\r\nmy second <2>Word to search word searched, got word! Done!\r\n",
                               NO_REPETITION,
                               [VimController.OPERATION_NONE,
                                VimController.OPERATION_YANK,
                                VimController.OPERATION_DELETE,
                                VimController.OPERATION_CHANGE]);
    // Reset back to normal case sensitive now
    gVimController.settings["smartcase"] = false;

    // Test ignorecase setting
    // Add word we will search for
    gVimController.settings["ignorecase"] = true;
    this._runOperationCommands("findNext",
                               "word <|>is the <1>Word to search <2>word\r\nmy second <3>Word to search <4>word searched, got <5>word! Done!\r\n",
                               NO_REPETITION,
                               [VimController.OPERATION_NONE,
                                VimController.OPERATION_YANK,
                                VimController.OPERATION_DELETE,
                                VimController.OPERATION_CHANGE]);
    // Reset back to normal case sensitive now
    gVimController.settings["ignorecase"] = false;

    this._runOperationCommands("findWordUnderCursor",
                               "this is <|>search word\r\nmy second <1>search word searched\r\nmy third <2<search line\r\n",
                               //TEST_REPETITION,    // Fails
                               NO_REPETITION,
                               [VimController.OPERATION_NONE,
                                VimController.OPERATION_YANK,
                                VimController.OPERATION_DELETE,
                                VimController.OPERATION_CHANGE]);
                               // Fails in repitition, i.e. "2*"
                               //["knownfailure"]);
    // Ensure it works inside a word
    this._runOperationCommands("findWordUnderCursor",
                               "this is sear<|>ch word\r\nmy second <1>search word searched\r\nmy third <2<search line\r\n",
                               //TEST_REPETITION,    // Fails
                               NO_REPETITION);
    this._runOperationCommands("findWordUnderCursorBack",
                               "this is <2>search word\r\nmy second <1>search word sea<|>rch 'ed\r\n",
                               //TEST_REPETITION,    // Fails
                               NO_REPETITION,
                               [VimController.OPERATION_NONE,
                                VimController.OPERATION_YANK]);
                               // Fails in repitition, i.e. "2*"
                               //["knownfailure"]);

    // ";", used to test that the find char code is working
    // Test 'f':
    //vimlog.setLevel(ko.logging.LOG_DEBUG);
    gVimController._lastFindChar = 's';
    gVimController._lastMovePosBefore = false;
    gVimController._findCharDirection = VimController.SEARCH_FORWARD;
    this._runOperationCommands("repeatLastFindCharInLine",
                               "<|>thi<1>s i<2>s <3>search word. My <4>second <5>search word <6>searched\r\n",
                               TEST_REPETITION,
                               [VimController.OPERATION_NONE]);
    // operations make this work slightly differently
    this._runOperationCommands("repeatLastFindCharInLine",
                               "<|>this<1> is<2> s<3>earch word. My s<4>econd s<5>earch word s<6>earched\r\n",
                               TEST_REPETITION,
                               [VimController.OPERATION_YANK,
                                VimController.OPERATION_DELETE,
                                VimController.OPERATION_CHANGE]);
    // Test 'F'
    this._runOperationCommands("repeatLastFindCharInLineReversed",
                               "thi<6>s i<5>s <4>search word. My <3>second <2>search word <1>search<|>ed\r\n",
                               TEST_REPETITION,
                               [VimController.OPERATION_NONE,
                                VimController.OPERATION_YANK,
                                VimController.OPERATION_DELETE,
                                VimController.OPERATION_CHANGE]);
    //vimlog.setLevel(ko.logging.LOG_WARN);
    // Test 't':
    gVimController._lastMovePosBefore = true;
    this._runOperationCommands("repeatLastFindCharInLine",
                               "<|>th<1>is is search word. My second search word searched\r\n",
                               NO_REPETITION,
                               [VimController.OPERATION_NONE]);
    // operations make this work slightly differently
    gVimController._lastMovePosBefore = true;
    this._runOperationCommands("repeatLastFindCharInLine",
                               "<|>thi<1>s is search word. My second search word searched\r\n",
                               NO_REPETITION,
                               [VimController.OPERATION_YANK,
                                VimController.OPERATION_DELETE,
                                VimController.OPERATION_CHANGE]);
    // Test 'T'
    this._runOperationCommands("repeatLastFindCharInLineReversed",
                               "this is search word. My second search word s<1>earch<|>ed\r\n",
                               NO_REPETITION,
                               [VimController.OPERATION_NONE,
                                VimController.OPERATION_YANK,
                                VimController.OPERATION_DELETE,
                                VimController.OPERATION_CHANGE]);
    return;
    // XXX: TODO
    // Little more tricky, require user input, which this test framework does not yet support
    this._runCommand("findCharInLine", "this is\r\nmy bu<|>ffer\r\n", "this <|>is\r\nmy buffer\r\n");
    this._runCommand("findPreviousCharInLine", "this is\r\nmy bu<|>ffer\r\n", "this <|>is\r\nmy buffer\r\n");
    this._runCommand("findCharInLinePosBefore", "this is\r\nmy bu<|>ffer\r\n", "this <|>is\r\nmy buffer\r\n");
    this._runCommand("findPreviousCharInLinePosAfter", "this is\r\nmy bu<|>ffer\r\n", "this <|>is\r\nmy buffer\r\n");
    this._runCommand("repeatLastFindCharInLine", "this is\r\nmy bu<|>ffer\r\n", "this <|>is\r\nmy buffer\r\n");
    this._runCommand("repeatLastFindCharInLineReversed", "this is\r\nmy bu<|>ffer\r\n", "this <|>is\r\nmy buffer\r\n");
}


test_vi_emulation.prototype.test_find_char_with_operation = function() {
    // [y|c|d]fW
    this._runFindCharOperation("repeatLastFindCharInLine",
                               "Word <|>is the search <1>Word, my second search <2>Word searched, got <3>Word! Done!\r\n",
                               "W" /* char to find */,
                               VimController.SEARCH_FORWARD,
                               false /* movePos[Before|After] */,
                               null /* register */,
                               TEST_REPETITION,
                               [VimController.OPERATION_NONE]);
    // operations make this work slightly differently
    this._runFindCharOperation("repeatLastFindCharInLine",
                               "Word <|>is the search W<1>ord, my second search W<2>ord searched, got W<3>ord! Done!\r\n",
                               "W" /* char to find */,
                               VimController.SEARCH_FORWARD,
                               false /* movePos[Before|After] */,
                               null /* register */,
                               TEST_REPETITION,
                               [VimController.OPERATION_YANK,
                                VimController.OPERATION_DELETE,
                                VimController.OPERATION_CHANGE]);
    // [y|c|d]FW
    this._runFindCharOperation("repeatLastFindCharInLine",
                               "Word is the search <3>Word, my second search <2>Word searched, got <1>Word! Do<|>ne!\r\n",
                               "W" /* char to find */,
                               VimController.SEARCH_BACKWARD,
                               false /* movePos[Before|After] */,
                               null /* register */,
                               TEST_REPETITION,
                               [VimController.OPERATION_NONE,
                                VimController.OPERATION_YANK,
                                VimController.OPERATION_DELETE,
                                VimController.OPERATION_CHANGE]);
    // [y|c|d]tW
    this._runFindCharOperation("repeatLastFindCharInLine",
                               "Word <|>is the search<1><2><3> Word, my second search Word searched, got Word! Done!\r\n",
                               "W" /* char to find */,
                               VimController.SEARCH_FORWARD,
                               true /* movePos[Before|After] */,
                               null /* register */,
                               NO_REPETITION,  // Repeat works differently
                               [VimController.OPERATION_NONE]);
    // operations make this work slightly differently
    this._runFindCharOperation("repeatLastFindCharInLine",
                               "Word <|>is the search <1>Word, my second search <2>Word searched, got <3>Word! Done!\r\n",
                               "W" /* char to find */,
                               VimController.SEARCH_FORWARD,
                               true /* movePos[Before|After] */,
                               null /* register */,
                               NO_REPETITION,  // Repeat works differently
                               [VimController.OPERATION_YANK,
                                VimController.OPERATION_DELETE,
                                VimController.OPERATION_CHANGE]);
    // 3[y|c|d]tW
    this._runFindCharOperation("repeatLastFindCharInLine",
                               "Word <|>is the search Word, my second search Word searched, got<1> Word! Done!\r\n",
                               "W" /* char to find */,
                               VimController.SEARCH_FORWARD,
                               true /* movePos[Before|After] */,
                               null /* register */,
                               NO_REPETITION,  // Repeat works differently
                               [VimController.OPERATION_NONE],
                               [] /* tags */,
                               3 /* forcedRepeatCount */);
    // operations make this work slightly differently
    this._runFindCharOperation("repeatLastFindCharInLine",
                               "Word <|>is the search Word, my second search Word searched, got <1>Word! Done!\r\n",
                               "W" /* char to find */,
                               VimController.SEARCH_FORWARD,
                               true /* movePos[Before|After] */,
                               null /* register */,
                               NO_REPETITION,  // Repeat works differently
                               [VimController.OPERATION_YANK,
                                VimController.OPERATION_DELETE,
                                VimController.OPERATION_CHANGE],
                               [] /* tags */,
                               3 /* forcedRepeatCount */);
  //vimlog.setLevel(ko.logging.LOG_DEBUG);
  //log.setLevel(Casper.Logging.DEBUG);
  //try {
    // [y|c|d]TW
    this._runFindCharOperation("repeatLastFindCharInLine",
                               "Word is the search Word, my second search Word searched, got W<1><2><3>ord! Do<|>ne!\r\n",
                               "W" /* char to find */,
                               VimController.SEARCH_BACKWARD,
                               true /* movePos[Before|After] */,
                               null /* register */,
                               NO_REPETITION,
                               [VimController.OPERATION_NONE,
                                VimController.OPERATION_YANK,
                                VimController.OPERATION_DELETE,
                                VimController.OPERATION_CHANGE]);
    // 3[y|c|d]TW
    this._runFindCharOperation("repeatLastFindCharInLine",
                               "Word is the search W<1>ord, my second search Word searched, got Word! Do<|>ne!\r\n",
                               "W" /* char to find */,
                               VimController.SEARCH_BACKWARD,
                               true /* movePos[Before|After] */,
                               null /* register */,
                               NO_REPETITION,
                               [VimController.OPERATION_NONE,
                                VimController.OPERATION_YANK,
                                VimController.OPERATION_DELETE,
                                VimController.OPERATION_CHANGE],
                               [] /* tags */,
                               3 /* forcedRepeatCount */);
  //} finally {
  //  vimlog.setLevel(ko.logging.LOG_WARN);
  //  log.setLevel(Casper.Logging.WARN);
  //}
}


test_vi_emulation.prototype.test_search_with_operation = function() {
    this._runSearchCommandWithOperation("findNext",
                               "Word <|>is the search <1>Word, my second Worry search <2>Word searched, got <3>Word! Done!\r\n",
                               "Word" /* text to find */,
                               VimController.SEARCH_FORWARD,
                               null /* register */,
                               TEST_REPETITION,
                               [VimController.OPERATION_NONE,
                                VimController.OPERATION_YANK,
                                VimController.OPERATION_DELETE,
                                VimController.OPERATION_CHANGE]);
}


test_vi_emulation.prototype.assertRegisterIs = function(register, value) {
    this.assertEqual(gVimController._registers[register],
                     value,
                     "Register '" + register + "' incorrect, reg: '" +
                     gVimController._registers[register] + "', expected: '" +
                     value + "'");
}

test_vi_emulation.prototype.test_registers = function() {
    gVimController._searchDirection = VimController.SEARCH_FORWARD;
    this._runRegisterOperationCommands("wordRight",
                               "th<|>is <1>is <2>my <3>code-firstbuffer\r\n",
                               "",
                               TEST_REPETITION,
                               [VimController.OPERATION_YANK]);
    this._runRegisterOperationCommands("wordRight",
                               "th<|>is <1>is <2>my <3>code<4>-<5>firstbuffer<6>\r\n",
                               "b",
                               TEST_REPETITION,
                               [VimController.OPERATION_YANK]);
    this._repeatCommand("wordRight", 3,
                        "th<|>is is my code-secondbuffer\r\n",
                        "th<|> code-secondbuffer\r\n",
                        VimController.OPERATION_CHANGE,
                        "c" /* register */,
                        null /* tags */);
    this._runRegisterOperationCommands("wordRightEnd",
                               "th<|>is<1> is<2> my<3> code<4>-<5>thirdbuffer<6>\r\n",
                               "d",
                               TEST_REPETITION,
                               [VimController.OPERATION_DELETE]);
    //gVimController._dumpRegisters();
    // Ensure the registers hold the correct values
    this.assertRegisterIs("b", "is is my code-firstbuffer");
    this.assertRegisterIs("c", "is is my");
    this.assertRegisterIs("d", "is is my code-thirdbuffer");
    // Ensure the yank and delete registers hold the correct values
    this.assertRegisterIs("0", "is is my ");
    // Try pasting
    this._runRegisterCommand("paste",
                             ["this is my <|>code-thirdbuffer\r\n",
                              "this is my is is my code-firstbuffer<|>code-thirdbuffer\r\n",
                              "this is my is is my code-firstbufferis is my code-firstbuffer<|>code-thirdbuffer\r\n",
                             ],
                             "b");
    this._runRegisterCommand("paste",
                             ["this is my <|>code-thirdbuffer\r\n",
                              "this is my is is my<|>code-thirdbuffer\r\n",
                              "this is my is is myis is my<|>code-thirdbuffer\r\n",
                             ],
                             "c");
    // TODO:
    // These are known failures because I do not yet fully understand
    // how vi(m) is handling its delete [1-9] registers, as the vi results
    // do not match the vi(m) documentation...
    try {
        this.assertEqual(gVimController._registers["2"],
                         "is is my code-secondbuffer",
                         "delete register 2: register incorrect after running command!");
        this.assertEqual(gVimController._registers["1"],
                         "is is my code-thirdbuffer",
                         "delete register 1: register incorrect after running command!");
        // Ensure small delete register is updated
        this.assertEqual(gVimController._registers["-"],
                         "is is my",
                         "small delete register: register incorrect after running command!");
    } catch(ex if ex instanceof Casper.UnitTest.AssertException) {
        this.logKnownFailure("test_registers", ex);
    }
}


test_vi_emulation.prototype.test_find_and_replace = function() {
    // Only replace the first instance in a line
    this._runTextCommand("1,1s/e/z/",
                         ["this is my code-firstbuffer\r\nthis is the second line\r\n",
                          "this is my codz-firstbuffer\r\nthis is the second line\r\n"]);
    // Try on multiple lines
    this._runTextCommand("1,2s/e/z/",
                         ["this is my code-firstbuffer\r\nthis is the second line\r\n",
                          "this is my codz-firstbuffer\r\nthis is thz second line\r\n"]);
    // Replace all the instances in a line
    this._runTextCommand("1,1s/e/z/g",
                         ["this is my code-firstbuffer\r\nthis is the second line\r\n",
                          "this is my codz-firstbuffzr\r\nthis is the second line\r\n"]);
    // try on all lines
    this._runTextCommand("%s/e/z/g",
                         ["this is my code-firstbuffer\r\nthis is the second line\r\n",
                          "this is my codz-firstbuffzr\r\nthis is thz szcond linz\r\n"]);
    // Replace all the instances in a line
    this._runTextCommand("1,2s/is/at/g",
                         ["this is my code-firstbuffer\r\nthis is the second line\r\n",
                          "that at my code-firstbuffer\r\nthat at the second line\r\n"]);
    // try on a selection,
    // "|" represents the cursor position
    // "^" represents the anchor position
    this._runTextCommand("'<,'>s/e/z/g",
                         ["this is my code-firs<|>tbuffer\r\nthis is the second<^> line\r\n",
                          "this is my code-firstbuffzr\r\nthis is thz szcond line\r\n"]);
}

test_vi_emulation.prototype.test_indenting = function() {
    // try on a selection, note that vi removes the selection after running
    // the indent/dedent command.
    // "|" represents the cursor position
    // "^" represents the anchor position
    this._runCommand("indentOperation",
                     ["line 1\r\nli<^>ne<|> 2\r\nline 3\r\n",
                      "line 1\r\n    line<^><|> 2\r\nline 3\r\n"],
                     { mode: VimController.MODE_VISUAL,
                       visualMode: VimController.VISUAL_LINE });
    this._runCommand("indentOperation",
                     ["<^>line 1\r\nline<|> 2\r\nline 3\r\n",
                      "    line 1\r\n    line<^><|> 2\r\nline 3\r\n"],
                     { mode: VimController.MODE_VISUAL,
                       visualMode: VimController.VISUAL_LINE });
    this._runCommand("dedentOperation",
                     ["line 1\r\n    li<^>ne<|> 2\r\nline 3\r\n",
                      "line 1\r\nline<^><|> 2\r\nline 3\r\n"],
                     { mode: VimController.MODE_VISUAL,
                       visualMode: VimController.VISUAL_LINE });
    this._runCommand("dedentOperation",
                     ["    <^>line 1\r\n    line<|> 2\r\nline 3\r\n",
                      "line 1\r\nline<^><|> 2\r\nline 3\r\n"],
                     { mode: VimController.MODE_VISUAL,
                       visualMode: VimController.VISUAL_LINE });
}


test_vi_emulation.prototype.test_other_commands = function() {
    return;
    this._runCommand("overtype", "this is\r\nmy bu<|>ffer\r\n", "this <|>is\r\nmy buffer\r\n");
    this._runCommand("undo", "this is\r\nmy bu<|>ffer\r\n", "this <|>is\r\nmy buffer\r\n");
    this._runCommand("redo", "this is\r\nmy bu<|>ffer\r\n", "this <|>is\r\nmy buffer\r\n");
    this._runCommand("join", "this is\r\nmy bu<|>ffer\r\n", "this <|>is\r\nmy buffer\r\n");
    this._runCommand("swapCase", "this is\r\nmy bu<|>ffer\r\n", "this <|>is\r\nmy buffer\r\n");
    this._runCommand("jumpToMatchingBrace", "this is\r\nmy bu<|>ffer\r\n", "this <|>is\r\nmy buffer\r\n");
    this._runCommand("enterCommandMode", "this is\r\nmy bu<|>ffer\r\n", "this <|>is\r\nmy buffer\r\n");
    this._runCommand("repeatLastCommand", "this is\r\nmy bu<|>ffer\r\n", "this <|>is\r\nmy buffer\r\n");
    this._runCommand("dedent", "this is\r\nmy bu<|>ffer\r\n", "this <|>is\r\nmy buffer\r\n");
    this._runCommand("indent", "this is\r\nmy bu<|>ffer\r\n", "this <|>is\r\nmy buffer\r\n");
}


test_vi_emulation.prototype.test_bug51878_delete_at_eof = function() {
    // bug 51878 - delete at the end of the file when there is no EOL.
    this._runCommand("lineCut",
                     ["this is<|>",
                      "<|>"]);
    this._runCommand("lineCut",
                     ["line 1\r\nline 2\r\nline<|> 3",
                      "line 1\r\n<|>line 2\r\n"]);
    this._runCommand("lineCut",
                     ["line 1\r\nline 2\r\nline<|> 3\r\n",
                      "line 1\r\n<|>line 2\r\n"]);
    // Ensure a count deletion "10dd" does not delete above the starting
    // position, bug 81804.
    this._repeatCommand("lineCut", 10,
                        "line 1\r\nline 2\r\nline<|> 3\r\nline 4\r\nline 5\r\n",
                        "line 1\r\n<|>line 2\r\n",
                        VimController.OPERATION_NONE,
                        null /* register */,
                        null /* tags */);
}

test_vi_emulation.prototype.test_bug62438_delete_at_eol = function() {
    // http://bugs.activestate.com/show_bug.cgi?id=62438
    this._runCommand("cutChar",
                     ["this is<|>\r\n",
                      "this i<|>\r\n",
                      "this <|>\r\n"]);
}

test_vi_emulation.prototype.test_bug83368_repeat_delete_char = function() {
    // Ensure a count char deletion "100x" does not delete before the starting
    // position, bug 83368.
    this._repeatCommand("cutChar", 100,
                        "this<|> is\r\n my test\r\n",
                        "this<|>\r\n my test\r\n",
                        VimController.OPERATION_NONE,
                        null /* register */,
                        null /* tags */);
}

test_vi_emulation.prototype.test_bug72411_search_replace = function() {
    // http://bugs.activestate.com/show_bug.cgi?id=72411
    this._runTextCommand("%s/System/run_local",
                         ['if ( $devices =~ /(\d+)\s+megadev/ ) {\n' +
                          '    System("foo");\n' +
                          '    System("n");\n' +
                          '    System("n");\n' +
                          '}\n',

                          'if ( $devices =~ /(\d+)\s+megadev/ ) {\n' +
                          '    run_local("foo");\n' +
                          '    run_local("n");\n' +
                          '    run_local("n");\n' +
                          '}\n']);
}

test_vi_emulation.prototype.test_bug81184_no_eol_at_eof = function() {
    // bug 81184 - yank/delete at the end of the file when there is no EOL.
    this._runCommand("lineCut",
                     ["this is<|>",
                      "<|>"]);
    this.assertEqual(gVimController._registers["1"],
                     "this is\r\n",
                     "'dd' on last line with no EOL failed!");
    this._runCommand("yankLine",
                     ["this is<|>",
                      "this is<|>"]);
    this.assertEqual(gVimController._registers["1"],
                     "this is\r\n",
                     "'yy' on last line with no EOL failed!");
    this._runCommand("pasteAfter",
                     ["this is<|>",
                      "this is\r\n<|>this is"],
                     { resetMode: false });
}

test_vi_emulation.prototype.test_bug81576_paste_in_visual_mode = function() {
    /* Both cmd_paste and cmd_pasteAfter should work the same in visual mode. */
    this._reset();
    gVimController.mode = VimController.MODE_VISUAL;
    gVimController._copyMode = VimController.COPY_LINES;
    gVimController._internalBuffer = "line1.5\r\n";
    this._runCommand("pasteAfter",
                     ["line1\r\n<^>line2\r\n<|>line3\r\n",
                      "line1\r\n<^><|>line1.5\r\nline3\r\n"],
                     { resetMode: false });

    this._reset();
    gVimController.mode = VimController.MODE_VISUAL;
    gVimController._copyMode = VimController.COPY_LINES;
    gVimController._internalBuffer = "line1.5\r\n";
    this._runCommand("paste",
                     ["line1\r\n<^>line2\r\n<|>line3\r\n",
                      "line1\r\n<^><|>line1.5\r\nline3\r\n"],
                     { resetMode: false });
}

test_vi_emulation.prototype.test_bug82707_changeLine = function() {
    // bug 82707 - changeLine should work from the base indentation level.
    this._runCommand("changeLine",
                     ["this is<|>",
                      "<|>"]);
    this._runCommand("changeLine",
                     ["    this is<|>",
                      "    <|>"]);
    this._runCommand("changeLine",
                     ["<|>    this is",
                      "    <|>"]);
}

/* TEST SUITE */

function vi_emulation_test_suite(name) {
    this._originalKeybindingConfigName = ko.keybindings.manager.currentConfiguration;
    Casper.UnitTest.TestSuite.apply(this, [name]);
}
vi_emulation_test_suite.prototype = new Casper.UnitTest.TestSuite();
vi_emulation_test_suite.prototype.constructor = vi_emulation_test_suite;

// Override base class run function, necessary to get proper loading
// of the vi-keybindings (due to the asynchronous overlay loading).
vi_emulation_test_suite.prototype.run = function() {
    //dump("vi_emulation_test_suite:: run()\n");

    var self = this;
    var callback = function() {
        self.setup();
        self.index = 0;
        window.setTimeout(function (me) { me.execute(); }, 0, self);
    };

    if (this._originalKeybindingConfigName != "Vi") {
        gVimController.enable(false);
        gVimController.enabledCallback = callback;
        ko.keybindings.manager.switchConfiguration("Vi");
    } else {
        callback();
    }
}

vi_emulation_test_suite.prototype.tearDown = function() {
    // Switch back the keybindings to the original set
    if (ko.keybindings.manager.currentConfiguration != this._originalKeybindingConfigName) {
        ko.keybindings.manager.switchConfiguration(this._originalKeybindingConfigName);
    }
}

// we do not pass an instance of MyTestCase, they are created in MakeSuite
var suite = new vi_emulation_test_suite("Vi Emulation");
suite.add(new test_vi_emulation());
Casper.UnitTest.testRunner.add(suite);

} catch(e) {
    var CasperLog = Casper.Logging.getLogger("Casper::global");
    CasperLog.exception(e);
}
