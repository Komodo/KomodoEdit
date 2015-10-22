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

// -*- Mode: JavaScript; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 2 -*-

if (typeof(ko)=='undefined') {
    var ko = {};
}
if (typeof(ko.run)=='undefined') {
    ko.run = {};
}

/**
 * Assitance for Komodo's Run Command feature set.
 *
 * Notes on MRUs:
 * - The Run Command system currently used three MRUs stored under the
 *   following pref names:
 *    'run-commandMru' - stores _encoded_ command strings, used for
 *        Tools->Recent Commands
 *    'run-commandStringMru' - stores just the command string, used for
 *        command textbox MRU
 *    'run-parseRegexMru' - stores just parse regex strings, used for the
 *        parseRegex textbox MRU.
 */
(function() {

const { classes: Cc, interfaces: Ci, utils: Cu } = Components;
const {XPCOMUtils} = Cu.import("resource://gre/modules/XPCOMUtils.jsm", {});

var lazy = {};

XPCOMUtils.defineLazyGetter(lazy, "log", function() ko.logging.getLogger("run_functions"));
//lazy.log.setLevel(ko.logging.LOG_DEBUG);

XPCOMUtils.defineLazyGetter(lazy, "bundle", function()
    Cc["@mozilla.org/intl/stringbundle;1"]
    .getService(Ci.nsIStringBundleService)
    .createBundle("chrome://komodo/locale/run/run_functions.properties"));

XPCOMUtils.defineLazyGetter(lazy, "runSvc", function()
    Cc["@activestate.com/koRunService;1"]
        .getService(Components.interfaces.koIRunService));

var _processList = [];
var ISciMoz = Ci.ISciMoz;


//---- internal utility routines

function _UpdateMRU(command, encodedCommand, cwd, parseRegex)
{
    ko.mru.add("run-commandMru", encodedCommand, true /* case-sensitive */);
    ko.mru.add("run-commandStringMru", command, true /* case-sensitive */);
    if (cwd) {
        ko.mru.add("run-cwdMru", cwd, true /* case-sensitive */);
    }
    if (parseRegex) {
        ko.mru.add("run-parseRegexMru", parseRegex, true /* case-sensitive */);
    }
}

/**
 * Keep a list of processes spawned by the RunCommand system. This is necessary
 * to ensure that there are no hangs when Komodo closes because some process is
 * still running. Before closing Komodo all process must be terminated.
 */
this.registerProcess = function(command, process)
{
    //dump("_RegisterProcess(command='"+command+"', process='"+
    //     process+"')\n");

    // XXX There is some timing issue with process termination. For quick
    //     commands (e.g. 'echo hi'), the process may be a zombie before it
    //     gets here. We MUST, however, maintain a reference to it, at least
    //     until the next time around because some related things need to clean
    //     up before the ProcessProxy object destructs. Otherwise Komodo will
    //     hang. Don't know the details.
    ko.run.unregisterZombieProcess();

    var p = {};
    p['command'] = command;
    p['process'] = process;
    _processList.push(p);
}

/**
 * Remove any processes that have terminated from the list.
 */
this.unregisterZombieProcess = function()
{
    var newList = [];
    for (var i=0; i < _processList.length; i++) {
        var p = _processList[i]['process'];
        try {
            p.wait(0);
            //dump("_UnregisterZombieProcess: zombie: index="+i+
            //     ", command='"+editor._processList[i]['command']+"'\n");
        } catch (ex) {
            // Timeout exception, the process has not yet finished.
            newList[newList.length] = _processList[i];
        }
    }
    _processList = newList;
}

/**
 * koIRunTerminationListener implementation whose only job is to call
 * notify on child termination.
 */
function _terminationListener() { }
_terminationListener.prototype = {
    init: function (editor, command, callback) {
        this._editor = editor;
        this._command = command;
        this._callback = callback;
    },
    onTerminate: function (retval) {
        //dump("_terminationListener::onTerminate(retval="+retval+")\n");
        this._editor.ko.run.output.endSession(retval);
        var msg = lazy.bundle.formatStringFromName("terminateMessage", [this._command ,retval], 2);
        require("notify/notify").send(msg, "commands", {panelOnly: true});
        if (this._callback) {
            // Want the callback to come _after_ this thread of control so call
            // it in a timeout.
            //TODO: Catch exceptions raised by the callback and give a useful
            //      alert dialog with details.
            window.setTimeout(function(cback, rval) { cback(rval); },
                              10, this._callback, retval);
        }
    },
    QueryInterface: function (iid) {
        if (!iid.equals(Components.interfaces.koIRunTerminationListener) &&
            !iid.equals(Components.interfaces.nsISupports)) {
            throw Components.results.NS_ERROR_NO_INTERFACE;
        }
        return this;
    }
}


//---- public interface

this.buildRecentCommandsMenu = function Run_BuildRecentCommandsMenu(popupWidget)
{
    var globalPrefs = Components.classes["@activestate.com/koPrefService;1"]
                      .getService(Components.interfaces.koIPrefService).prefs;

    var mruPrefName = "run-commandMru";
    var mruList = globalPrefs.hasPref(mruPrefName) ?
                  globalPrefs.getPref(mruPrefName) : null;

    // clear the current list
    while (popupWidget.childNodes.length != 0)  {
        var child = popupWidget.firstChild;
        popupWidget.removeChild(child);
    }

    // if the MRU is empty then say so
    var itemWidget = null;
    if (!mruList || mruList.length == 0) {
        itemWidget = document.createElement("menuitem");
        itemWidget.setAttribute("label", lazy.bundle.GetStringFromName("mruEmpty.label"));
        itemWidget.setAttribute("disabled", "true");
        popupWidget.appendChild(itemWidget);
    }

    // otherwise, populate the menupopup
    else {
        for(var i = 0; i < mruList.length; i++) {
            itemWidget = document.createElement("menuitem");

            // special case: if there are no options then strip the leading
            // "[] " for display to the user (XXX this presumes knowledge of
            // the encoding scheme)
            var encodedCommand = mruList.getStringPref(i);
            var displayCommand = encodedCommand;
            if (encodedCommand.substring(0,3) == "[] ") {
                displayCommand = encodedCommand.substring(3,
                                   encodedCommand.length);
            }
            itemWidget.setAttribute("label", (i+1) + " " + displayCommand);

            // escape char that will get interpreter twice (XXX not confident
            // that this covers all cases)
            encodedCommand = encodedCommand.replace('\\', '\\\\', "g");
            encodedCommand = encodedCommand.replace("'", "\\'", "g");
            encodedCommand = encodedCommand.replace('"', '\\"', "g");
            var handler = "ko.run.runEncodedCommand(window, '"
                          + encodedCommand + "');";
            itemWidget.setAttribute("oncommand", handler);

            if (i <= 8) {
                itemWidget.setAttribute("accesskey", ""+(i+1));
            } else if (i == 9) {
                itemWidget.setAttribute("accesskey", "0");
            }

            popupWidget.appendChild(itemWidget);
        }
    }
}

/**
 * Run an "encoded" command.
 *
 * An encoded command is a string that describes the command and possibly a
 * number of optional arguments. The encoding is defined by
 * koIRunService.Decode().
 *
 * @param {Object} window object
 * @param {String} command string
 * @param {Function} callback optional
 *      can be a function that will
 *      be called when the command has finished. Limitation: this will only be
 *      used if "runIn='command-output-window'" (the default).
 *      [New in Komodo 4.1.]
 * @returns {Boolean} true iff the command was launched successfully.
 */
this.runEncodedCommand = function Run_RunEncodedCommand(editor, encodedCommand,
                               terminationCallback /* =null */)
{
    // decode the command string and then run it
    var commandObj = new Object();
    var cwdObj = new Object();
    var envObj = new Object();
    var insertOutputObj = new Object();
    var operateOnSelectionObj = new Object();
    var doNotOpenOutputWindowObj = new Object();
    var runInObj = new Object();
    var parseOutputObj = new Object();
    var parseRegexObj = new Object();
    var showParsedOutputListObj = new Object();
    lazy.runSvc.Decode(encodedCommand, commandObj, cwdObj, envObj,
                    insertOutputObj, operateOnSelectionObj,
                    doNotOpenOutputWindowObj, runInObj,
                    parseOutputObj, parseRegexObj, showParsedOutputListObj);

    return ko.run.runCommand(editor, commandObj.value, cwdObj.value, envObj.value,
                          insertOutputObj.value, operateOnSelectionObj.value,
                          doNotOpenOutputWindowObj.value, runInObj.value,
                          parseOutputObj.value, parseRegexObj.value,
                          showParsedOutputListObj.value,
                          null, // name
                          true, // clearOutputWindow
                          terminationCallback);
}

/**
 * @deprecated since Komodo 9.0.0, use ko.run.command() instead.
 * 
 * Run the given command.
 *  @param {Object} "editor" is the main editor window JS object.
 *  @param {String} "command" is the command string to spawn.
 *  @param {String} "cwd" is the directory to start the child process in (null to inherit from
 *      the parent).
 *  @param {String} "env" is an encoded string of environment changes to make for the child
 *      (null to inherit from the parent). Encoding scheme:
 *              "VAR1=value1\nVAR2=value2\n..."
 *  @param {Boolean} "insertOutput" specifies whether to insert the command's output
 *      into the current insertion point.
 *  @param {Boolean} "operateOnSelection" specifies whether to use the current
 *      selection as input to the given command.
 *  @param {Boolean} "doNotOpenOutputWindow" specifies that the Command Output window
 *      should *not* be opened.
 *  @param {String} "runIn" identifies where the command should be run, e.g. in a new
 *      console window, in the command output pane (this is only meaningful if
 *      the command will be run interactively). See the koIPart_command IDL for
 *      a description of the exact strings to use.
 *  @param {Boolean} "parseOutput" indicates whether to parse output lines with the
 *      given regular expression, "parseRegex".
 *  @param {String} "parseRegex" is a regex pattern to use to parse the output lines
 *      into the command output window tree.
 *  @param {Boolean} "showParsedOutputList" indicates whether to view parsed results
 *      in the tree.
 *  @param {String} "name"is an optional name for the command being run. Sometimes
 *      this name is useful when interacting with the user.
 *  @param {Boolean} "clearOutputWindow". By default the command output window is
 *      cleared before starting a new command. This option is only relevant
 *      when runIn=="command-output-window". NOTE: This option is currently NOT
 *      exposed via the Command UI, nor is it persisted in koIPart_command's.
 *      YAGNI.
 *  @param {Function} "terminationCallback" is called after the command terminates.
 *      Limitation: This is currently only implemented for
 *      runIn=="command-output-window" (the default) for simplicity sake.
 *
 * @returns {Boolean} true iff the command was launched successfully.
 */
this.runCommand = function Run_RunCommand(editor, command, cwd, env, insertOutput,
                        operateOnSelection, doNotOpenOutputWindow, runIn,
                        parseOutput /* =false */, parseRegex /* ='' */,
                        showParsedOutputList /* =false */,
                        name /* =null */,
                        clearOutputWindow /* =true */,
                        terminationCallback /* =null */,
                        saveInMRU /* =true */,
                        saveInMacro /* =true */,
                        viewData /* =null */)
{
    var options = {
        "window": editor,
        "cwd": cwd,
        "env": env,
        "insertOutput": insertOutput,
        "operateOnSelection": operateOnSelection,
        "openOutputWindow": !(doNotOpenOutputWindow),
        "runIn": runIn,
        "parseRegex": parseRegex,
        "showParsedOutputList": showParsedOutputList,
        "name": name,
        "clearOutputWindow": clearOutputWindow,
        "terminationCallback": terminationCallback,
        "saveInMRU": saveInMRU,
        "saveInMacro": saveInMacro,
        "viewData": viewData,
    };
    return this.command(command, options);
}

/**
 * Run the given command.
 *
 *  @param {String} command - The command string to execute.
 *  @param {Object} options - Optional object can contain the following:
 *   "cwd" {String} - the directory to start the process in.
 *   "env" {String} - an encoded string of environment changes to use for the
 *                    process. Encoding scheme: "VAR1=value1\nVAR2=value2\n..."
 *   "runIn" {String} - identifies where the command should be run, one of:
 *           "command-output-window" - the Komodo output pane (the default)
 *           "new-console" - in a separate console window
 *           "no-console" - in a hidden external window
 *   "insertOutput" {Boolean} - specifies whether to insert the command's output
 *                              into the current insertion point (default false).
 *   "operateOnSelection" {Boolean} - use the current selection as input to the
 *                                    command (default false).
 *   "openOutputWindow" {Boolean} specifies whether the Command Output pane
 *                                should be opened (default true).
 *   "name" {String} - alias name for the command being run, shown to the user.
 *   "editor" {Window} - a top-level Komodo window object to run inside.
 *   "saveInMRU" {Boolean} - save the command in run command MRU list (false)
 *   "saveInMacro {Boolean} - save the command in macro recordings (true)
 *   "viewData" {Object} - custom view information (null)
 *
 * When runIn == "command-output-window", the following additional options are
 * available:
 *   "parseRegex" {String} - a regex pattern to use to parse the output lines
 *                           into the command output window tree.
 *   "showParsedOutputList" {Boolean} - show regex parsed output in a list view
 *   "clearOutputWindow" {Boolean} - Whether to clear the command output window
 *                                   when starting a new command (defaults to
 *                                   true).
 *   "terminationCallback" {Function} - called after the command terminates.
 *
 * @returns {Boolean} true if the command was launched successfully.
 */
this.command = function Run_RunCommand(command, options)
{
    try {
        // Initialize options.
        options = options || {};
        var cwd = ("cwd" in options && options.cwd) || null;
        var env = ("env" in options && options.env) || null;
        var editor = ("window" in options && options.window) || window;
        var insertOutput = ("insertOutput" in options && options.insertOutput) || false;
        var operateOnSelection = ("operateOnSelection" in options && options.operateOnSelection) || false;
        var openOutputWindow = ("openOutputWindow" in options && options.openOutputWindow) || true;
        var runIn = ("runIn" in options && options.runIn) || "command-output-window";
        var parseRegex = ("parseRegex" in options && options.parseRegex) || "";
        var parseOutput = (parseRegex ? true : false);
        var showParsedOutputList = ("showParsedOutputList" in options && options.showParsedOutputList) || false;
        var name = ("name" in options && options.name) || null;
        var clearOutputWindow = ("clearOutputWindow" in options && options.clearOutputWindow) || true;
        var terminationCallback = ("terminationCallback" in options && options.terminationCallback) || null;
        var saveInMRU = ("saveInMRU" in options && options.saveInMRU) || false;
        var saveInMacro = ("saveInMacro" in options && options.saveInMacro) || true;
        var viewData = ("viewData" in options && options.viewData) || null;

        var obj, errmsg;
        var lastErrorSvc = Components.classes["@activestate.com/koLastErrorService;1"]
                           .getService(Components.interfaces.koILastErrorService);
        var scimoz = null;
        var view = editor.ko.views.manager.currentView;
        var filename = null;
        var url = null;

        if (view) {
            if (view.scintilla)
                scimoz = view.scintilla.scimoz;
            if (view.koDoc) {
                filename = view.koDoc.displayPath;
                if (view.koDoc.file) url = view.koDoc.file.URI;
            }
        }
    
        // Ensure that it is reasonable to run this command given the current state
        // of Komodo.
        if (operateOnSelection) {
            if (!view) {
                alert(lazy.bundle.GetStringFromName("cannotOperateNoCurrentFile.alert"));
                return false;
            } else if (!scimoz) {
                alert(lazy.bundle.GetStringFromName("doNotKnowHowtoOperate.alert"));
                return false;
            } else if (scimoz.selText == "") {
                alert(lazy.bundle.GetStringFromName("cannotOperateNoSelection.alert"));
                return false;
            }
        }
        if (insertOutput) {
            if (!view) {
                alert(lazy.bundle.GetStringFromName("cannotInsertOutput.alert"));
                return false;
            } else if (!scimoz) {
                alert(lazy.bundle.GetStringFromName("doNotKnowHowtoInsertOutpuNonEditorView.alert"));
                return false;
            }
        }
    
        var icommand = null;
        var icommandForDisplay = null;
        var icwd = null;
        var icwdForDisplay = null;
        var ienv = null;
        var ienvForDisplay = null;
        var env_in = [];
        if (env) env_in = [env];
        try {
            var istrings;
            if (cwd == null) {
                istrings = ko.interpolate.interpolate(editor, [command],
                                                   env_in, name, viewData);
                icommand = istrings[0];
                icommandForDisplay = istrings[1];
                if (env) {
                    ienv = istrings[2];
                    ienvForDisplay = istrings[3];
                }
            } else {
                istrings = ko.interpolate.interpolate(editor, [command, cwd],
                                                   env_in, name, viewData);
                icommand = istrings[0];
                icommandForDisplay = istrings[1];
                icwd = istrings[2];
                icwdForDisplay = istrings[3];
                if (!Components.classes["@activestate.com/koOsPath;1"].getService(Components.interfaces.koIOsPath).exists(icwd)) {
                    icwd = icwdForDisplay = ko.window.getCwd();
                }
                if (env) {
                    ienv = istrings[4];
                    ienvForDisplay = istrings[5];
                }
            }
        } catch (ex) {
            var errno = lastErrorSvc.getLastErrorCode();
            if (errno == Components.results.NS_ERROR_ABORT) {
                // Command was cancelled.
            } else if (errno == Components.results.NS_ERROR_INVALID_ARG) {
                errmsg = lastErrorSvc.getLastErrorMessage();
                var fullmsg = lazy.bundle.GetStringFromName("errorRunningCommand.alert");
                if (name) {
                    fullmsg += " [" + name + "]";
                }
                fullmsg += ": " + errmsg;
                alert(fullmsg);
            } else {
                lazy.log.error(ex);
                alert(lazy.bundle.formatStringFromName("thereWasAnUnexpectedError.alert", [ex], 1));
            }
            return false;
        }
    
        // Run the command.
        var retval = null;
        var termListener = null;
        var process = null;
        var input = null;
        var output = null;
        var error = null;
        errmsg = null;
        if (operateOnSelection && scimoz && scimoz.selText != "") {
            input = scimoz.selText;
        }
    
        if (insertOutput) {
            // Start the command and monitor it. If the process is taking a long
            // time to complete then pop up a dialog to wait for its termination
            // giving the user the option to abort the command by killing the
            // process.
            //dump("XXX RunAndNotify: about to start '"+icommand+"'\n");
            try {
                process = lazy.runSvc.RunAndNotify(icommand, icwd, ienv, input);
            } catch (ex) {
                //dump("XXX RunAndNotify: '"+icommand+"' failed to start\n");
                errmsg = lastErrorSvc.getLastErrorMessage();
                if (! errmsg) {
                    errmsg = lazy.bundle.formatStringFromName("unknownErrorRunningCommand.alert", [icommand], 1);
                }
                alert(errmsg);
                return false;
            }
            //dump("XXX RunAndNotify: '"+icommand+"' started normally\n");
    
            var cancelled = false;
            try {
                process.wait(2);  // Give the command a little bit of time to run.
                //dump("XXX RunAndNotify: child finished within 2s\n");
            } catch (ex) {
                // XXX Could getLastError here to determine if the wait failed
                //     because of WAIT_TIMEOUT or WAIT_FAILED. Should probably not
                //     ignore the latter, but punting on that for now.
                //dump("XXX RunAndNotify: 2s passed, child has NOT finished\n");
                obj = new Object();
                obj.process = process;
                obj.command = icommand;
                ko.windowManager.openOrFocusDialog(
                    "chrome://komodo/content/run/waitfortermination.xul",
                    "komodo_waitfortermination",
                    "chrome,close=no,modal=yes,resizable=yes", obj);
                if (obj.retval == "killed") { // Cancelled.
                    cancelled = true;
                }
            }
    
            if (! cancelled) {
                // The process has finished. Either the process has finished within
                // 2 seconds or the waitfortermination dialog was displayed and the
                // user then waited till the process finished. Note that the modal
                // flags of the dialog stop the code from reaching this point until
                // the dialog is closed.
                //dump("XXX RunAndNotify: get output and error\n");
                output = process.getStdout();
                error = process.getStderr();
                //dump("XXX RunAndNotify: finished getting output and error\n");
            }
    
        } else {
            if (runIn == "command-output-window") {
                try {
                    editor.ko.run.output.startSession(icommandForDisplay, parseOutput,
                                                  parseRegex, icwdForDisplay, filename,
                                                  clearOutputWindow);
                } catch (ex) {
                    alert(ex);
                    return false;
                }
                var terminal = editor.ko.run.output.getTerminal();
    
                // Setup the termination listener.
                termListener = new _terminationListener();
                termListener.init(editor, icommandForDisplay, terminationCallback);
    
                // Start the command.
                try {
                    process = lazy.runSvc.RunInTerminal(icommand, icwd, ienv,
                                                     terminal, termListener,
                                                     input);
                } catch (ex) {
                    errmsg = lastErrorSvc.getLastErrorMessage();
                    if (! errmsg) {
                        errmsg = lazy.bundle.formatStringFromName("unknownErrorRunningCommand.alert", [icommandForDisplay], 1);
                    }
                    alert(errmsg);
                    editor.ko.run.output.endSession(-1);
                    return false;
                }
    
                // Register the command and show the output window.
                // XXX Should perhaps pass in cwd here and display that in
                //     the command description for the user.
                editor.ko.run.registerProcess(icommandForDisplay, process);
                editor.ko.run.output.setProcessHandle(process);
                if (openOutputWindow) {
                    editor.ko.run.output.show(editor, showParsedOutputList);
                }
    
            } else if (runIn == "new-console") {
                try {
                    lazy.runSvc.Run(icommand, icwd, ienv, true, input);
                } catch (ex) {
                    errmsg = lastErrorSvc.getLastErrorMessage();
                    if (! errmsg) {
                        errmsg = lazy.bundle.formatStringFromName("unknownErrorRunningCommand.alert", [icommandForDisplay], 1);
                    }
                    lazy.log.error(errmsg);
                    alert(errmsg);
                    return false;
                }
    
            } else if (runIn == "no-console") {
                try {
                    lazy.runSvc.Run(icommand, icwd, ienv, false, input);
                } catch (ex) {
                    errmsg = lastErrorSvc.getLastErrorMessage();
                    if (! errmsg) {
                        errmsg = lazy.bundle.formatStringFromName("unknownErrorRunningCommand.alert", [icommandForDisplay], 1);
                    }
                    lazy.log.error(errmsg);
                    alert(errmsg);
                    return false;
                }
            } else {
                lazy.log.error("Unexpected 'runIn' value: " + runIn);
                throw new Error("Unexpected 'runIn' value: " + runIn);
            }
        }
        var encodedCommand = lazy.runSvc.Encode(command, cwd, env, insertOutput,
                                             operateOnSelection,
                                             !openOutputWindow, runIn,
                                             parseOutput, parseRegex,
                                             showParsedOutputList);
        if (saveInMRU) {
            _UpdateMRU(command, encodedCommand, cwd, parseRegex);
        }
        if (saveInMacro &&
            typeof(editor.ko.macros.recorder) != 'undefined' &&
            editor.ko.macros.recorder &&
            editor.ko.macros.recorder.mode == 'recording') {
            // escape char that will get interpreter twice (XXX not confident
            // that this covers all cases)
            encodedCommand = encodedCommand.replace('\\', '\\\\', "g");
            encodedCommand = encodedCommand.replace("'", "\\'", "g");
            encodedCommand = encodedCommand.replace('"', '\\"', "g");
            var runtxt = "ko.run.runEncodedCommand(window, '"
                          + encodedCommand + "');";
            editor.ko.macros.recorder.appendCode(runtxt);
        }
    
        // Insert the returned output if requested and select it.
        if (insertOutput && view && output) {
            scimoz.targetStart = Math.min(scimoz.anchor, scimoz.currentPos);
            scimoz.targetEnd = Math.max(scimoz.anchor, scimoz.currentPos);
    
            // Convert text to the target EOL chars.
            var eol = null;
            switch (scimoz.eOLMode) {
            case ISciMoz.SC_EOL_LF:
                eol = '\n';
                break;
            case ISciMoz.SC_EOL_CRLF:
                eol = '\r\n';
                break;
            case ISciMoz.SC_EOL_CR:
                eol = '\r';
                break;
            }
            output = output.replace(/\r\n|\n|\r/g, eol);
    
            scimoz.replaceTarget(output.length, output);
            scimoz.currentPos = scimoz.anchor + ko.stringutils.bytelength(output);
        }
    
        // Raise an alert dialog if there was error output.
        if (error) {
            ko.dialogs.alert(lazy.bundle.GetStringFromName("theCommandReturnedError.alert"), error);
        }
    
        // If the command looks like it was operating on the current file, then
        // notify that the file might have changed.
        if (url) {
            var marker;
            var markers = {"%f":1, "%F":1, "%(f":1, "%(F":1};
            var _gObserverSvc = Components.classes["@mozilla.org/observer-service;1"]
                                .getService(Components.interfaces.nsIObserverService);
            for (marker in markers) {
                if (command.indexOf(marker) != -1) {
                    try {
                        _gObserverSvc.notifyObservers(this, "file_status", url);
                    } catch (ex) { /* no one is listening */ }
                    break;
                }
            }
        }
    
        return true;
    } catch (e) {
        lazy.log.exception(e);
    }
    return false;
}

/**
 * Run the given command.
 *  @param {Object} "editor" is the main editor window JS object.
 *  @param {String} "command" is the command string to spawn.
 *  @param {String} "cwd" is the directory to start the child process in (null to inherit from
 *      the parent).
 *  @param {String} "env" is an encoded string of environment changes to make for the child
 *      (null to inherit from the parent). Encoding scheme:
 *              "VAR1=value1\nVAR2=value2\n..."
 *  @param {Boolean} "insertOutput" specifies whether to insert the command's output
 *      into the current insertion point.
 *  @param {Boolean} "operateOnSelection" specifies whether to use the current
 *      selection as input to the given command.
 *  @param {Boolean} "doNotOpenOutputWindow" specifies that the Command Output window
 *      should *not* be opened.
 *  @param {String} "runIn" identifies where the command should be run, e.g. in a new
 *      console window, in the command output pane (this is only meaningful if
 *      the command will be run interactively). See the koIPart_command IDL for
 *      a description of the exact strings to use.
 *  @param {Boolean} "parseOutput" indicates whether to parse output lines with the
 *      given regular expression, "parseRegex".
 *  @param {String} "parseRegex" is a regex pattern to use to parse the output lines
 *      into the command output window tree.
 *  @param {Boolean} "showParsedOutputList" indicates whether to view parsed results
 *      in the tree.
 *  @param {String} "name"is an optional name for the command being run. Sometimes
 *      this name is useful when interacting with the user.
 *  @param {Boolean} "clearOutputWindow". By default the command output window is
 *      cleared before starting a new command. This option is only relevant
 *      when runIn=="command-output-window". NOTE: This option is currently NOT
 *      exposed via the Command UI, nor is it persisted in koIPart_command's.
 *      YAGNI.
 *  @param {Function} "terminationCallback" is called after the command terminates.
 *      Limitation: This is currently only implemented for
 *      runIn=="command-output-window" (the default) for simplicity sake.
 *
 * @returns {Boolean} true iff the command was launched successfully.
 */
this.runRemoteCommand = function Run_RemoteRunCommand(serverAliasOrURI,
                                                      command,
                                                      terminationCallback  /* null */,
                                                      parseOutput          /* false */,
                                                      parseRegex           /* '' */,
                                                      showParsedOutputList /* false */,
                                                      clearOutputWindow    /* true */)
{
    try {
        if (!serverAliasOrURI) {
            require("notify/notify").send("runRemoteCommand: no server name provided",
                                          "remote", {priority: "error"});
            return false;
        }
        if (!command) {
            require("notify/notify").send("runRemoteCommand: no command provided",
                                          "remote", {priority: "error"});
            return false;
        }
        if (!terminationCallback) terminationCallback = null;
        if (typeof parseOutput == 'undefined' || parseOutput == null) parseOutput = false;
        if (!parseRegex) parseRegex = "";
        if (typeof showParsedOutputList == 'undefined' || showParsedOutputList == null) showParsedOutputList = false;
        if (typeof clearOutputWindow == 'undefined' || clearOutputWindow == null) clearOutputWindow = true;
    
        var obj, errmsg;
        var lastErrorSvc = Components.classes["@activestate.com/koLastErrorService;1"]
                           .getService(Components.interfaces.koILastErrorService);

        var RCService = Components.classes["@activestate.com/koRemoteConnectionService;1"].
                        getService(Components.interfaces.koIRemoteConnectionService);
        var conn = null;
        if (RCService.getServerInfoForAlias(serverAliasOrURI)) {
            conn = RCService.getConnectionUsingServerAlias(serverAliasOrURI);
        } else {
            conn = RCService.getConnectionUsingUri(serverAliasOrURI);
        }
        try {
            var ssh_conn = conn.QueryInterface(Components.interfaces.koISSHConnection)
        } catch(e) {
            require("notify/notify").send("runRemoteCommand: SFTP or SCP connection required",
                                          "remote", {priority: "error"});
            return false;
        }

        var stdout = {};
        var stderr = {};
        ssh_conn.runCommand(command, false /* combine stdout/stderr */, stdout, stderr);

        return true;
    } catch (e) {
        lazy.log.exception(e);
        require("notify/notify").send("runRemoteCommand: error: " + e,
                                          "remote", {priority: "error"});

    }
    return false;
}

/**
 * Prepare to close Komodo. Return false if cannot yet close Komodo.
 * If there are processes still running then must wait for or kill them.
 */
this.canClose = function Run_CanClose()
{
    var i;
    // If there are any still running processes, then ask the user if they want
    // to kill those processes (call kill on them and return true) or cancel
    // and wait for those processes to finish normally (return false).
    editor.ko.run.unregisterZombieProcess(window);
    if (_processList.length > 0) {
        var commands = "";
        for (i=0; i < _processList.length; i++) {
            commands += _processList[i]['command'] + '\n';
        }
        var question = lazy.bundle.GetStringFromName("theFollowingCommandsAreStillRunning.message");
        var answer = ko.dialogs.okCancel(question, "OK", commands);
        if (answer == "OK") {
            try {
                for (i=0; i < _processList.length; i++) {
                    //dump("Run_CanClose(): killing '"+
                    //     _processList[i]['command']+"'\n");
                    _processList[i]['process'].kill(-1);
                }
            } catch (ex) {
                lazy.log.error("Error killing running process when closing Komodo:"+
                         ex);
                //XXX Should this be reported to the user?
                return false;
            }
        } else if (answer == "Cancel") {
            return false;
        } else {
            throw new Error(lazy.bundle.formatStringFromName("unexpectedReturnValue.message", [answer], 1));
        }
    }
    return true;
}

}).apply(ko.run);
