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
 * The interface for using the run output window (where run command output goes
 * to, in the bottom pane of the Komodo workspace).
 *
 * Expected usage:
 *  - Someone calls ko.run.output.initialize() at startup and ko.run.output.finalize() at
 *    shutdown.
 *  - When a command is to be run in the output window do this:
 *       * announce intention to start session
 *      ko.run.output.startSession(...);
 *       *... setup and start running the actual command calling
 *       *    ko.run.output.getTerminal() and ko.run.output.show() as needed
 *      ko.run.output.setProcessHandle(p);   * to allow user to kill process
 *       *... setup ko.run.output.endSession() to be run when the process
 *       *    terminates.
 */
ko.run.output = {};
(function() {

var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
    .getService(Components.interfaces.nsIStringBundleService)
    .createBundle("chrome://komodo/locale/run/runOutputWindow.properties");

var _log = ko.logging.getLogger("ko.run.output");    
var _gTerminalHandler = null;
var _gTerminalView = null;
var _gProcess = null;
var _gParseOutput = 0;

//---- internal support routines

function _ClearUI()
{
    _UpdateSortIndicators(window, null);
    _gParseOutput = 0;

    var descWidget = document.getElementById("runoutput-desc");
    descWidget.removeAttribute("value");
    descWidget.removeAttribute("_command");
    descWidget.style.removeProperty("color");
}



//---- public interface
this.initialize = function RunOutput_Init() {
    try {
        // Create a terminal for the output window. The terminal has std handlers
        // that proxy read/write events between the scintilla and a spawned child
        // process.
        _gTerminalHandler = Components.classes['@activestate.com/koRunTerminal;1']
                     .createInstance(Components.interfaces.koITreeOutputHandler);
    
        if (!_gTerminalHandler) {
            _log.error("initialize: couldn't create a koRunTerminal");
            return;
        }
        _ClearUI();

        var treeWidget = document.getElementById("runoutput-tree");
        var boxObject = treeWidget.treeBoxObject
                      .QueryInterface(Components.interfaces.nsITreeBoxObject);
    
        if (boxObject.view == null) {
            // We are in a collapsed state-- we need to force the tree to be visible
            // before we can assign the view to it.
            ko.run.output.show(window);
        }
        _gTerminalView = document.getElementById("runoutput-scintilla");
        _gTerminalView.scintilla.symbolMargin = false; // No need for margins.
        _gTerminalView.init();
        _gTerminalView.initWithTerminal(_gTerminalHandler);
        boxObject.view = _gTerminalHandler;

        ["mousedown", "focus"].forEach(function(eventname) {
            window.frameElement.addEventListener(eventname, function(event) {
                if (event.originalTarget == event.target) {
                    document.getElementById("runoutput-deck").focus();
                }
            }, false);
        });
        window.frameElement.hookupObservers("runoutput-commandset");
        scintillaOverlayOnLoad();
    } finally {
        ko.main.addWillCloseHandler(ko.run.output.finalize);
    }
}


this.finalize = function RunOutput_Fini()
{
    if (_gTerminalView) {
        _gTerminalView.finalizeTerminal();
        _gTerminalView = null;
    }
    _gTerminalHandler = null;
    if (!ko.main.windowIsClosing) {
        ko.main.removeWillCloseHandler(ko.run.output.finalize);
    }
    scintillaOverlayOnUnload();
}


this.getTerminal = function RunOutput_GetTerminal()
{
    return _gTerminalHandler;
}

/**
 * Start a terminal session in the output window with the given command.
 * This raises an exception if the run output window is currently busy.
 *    "command" is the command being run (note that this is the command string
 *      *for display* which might be slight different -- passwords obscured --
 *      than the actual command)
 *    "parseOutput" is a boolean indicating whether to parse output lines
 *    "parseRegex" is the regular expression to use to parse output lines
 *    "cwd" is the directory in which the command is being run (note: ditto
 *      *for display* subtlety withh "command")
 *    "filename" is the current editor filename (if any)
 *    "clearContent" is a boolean indicating whether to clear the
 *      output window content (by default "true", i.e. the window _is_
 *      cleared).
 */
this.startSession = function RunOutput_StartSession(command, parseOutput, parseRegex, cwd,
                                filename, clearContent /* =true */)
{
    if (typeof clearContent == 'undefined') clearContent = true;

    if (_gTerminalHandler.active) {
        throw new Error(_bundle.GetStringFromName("aPreviousCommandIsRunning.message"));
    }
    _ClearUI();

    // Setup the terminal.
    var lastErrorSvc = Components.classes["@activestate.com/koLastErrorService;1"]
                       .getService(Components.interfaces.koILastErrorService);
    _gTerminalView.startSession(clearContent);
    _gParseOutput = parseOutput;
    if (_gParseOutput) {
        try {
            _gTerminalHandler.setParseRegex(parseRegex);
        } catch (ex) {
            _gTerminalView.endSession();
            var errmsg = lastErrorSvc.getLastErrorMessage();
            errmsg =_bundle.formatStringFromName("errorInRegex.message", [parseRegex, errmsg], 2);
            throw(errmsg);
        }
    }
    _gTerminalHandler.setCwd(cwd);
    var terminalView = document.getElementById("runoutput-scintilla");
    terminalView.cwd = cwd;
    if (filename) _gTerminalHandler.setCurrentFile(filename);

    var descWidget = document.getElementById("runoutput-desc");
    //XXX Bug: This attribute change doesn't actually show up until the cursor
    //    is moved, triggering some gecko redraw. Cannot use
    //    window.sizeToContent() because that does bad (though non-fatal)
    //    things to komodo.xul.
    // XXX Maybe want to add cwd to this string?
        descWidget.setAttribute("value",
            _bundle.formatStringFromName("running.message", [command], 1));
    // Store the command name for later use.
    descWidget.setAttribute("_command", command);

    // If not clearing the output window and we are not parsing output this
    // time around, do not muck with the parsed output view (no need to disturb
    // possible results from the previous command).
    if (clearContent || _gParseOutput) {
        var listButton = document.getElementById("runoutput-list-button");
        if (_gParseOutput) {
            listButton.removeAttribute("disabled");
        } else {
            listButton.setAttribute("disabled", "true");
        }

        // Determine what columns to show.
        if (_gParseOutput) {
            var fileCol = document.getElementById("runoutput-tree-file");
            if (parseRegex.indexOf("?P<file>") == -1) {
                fileCol.setAttribute("hidden", "true");
            } else {
                fileCol.setAttribute("hidden", "false");
            }
            var lineCol = document.getElementById("runoutput-tree-line");
            if (parseRegex.indexOf("?P<line>") == -1) {
                lineCol.setAttribute("hidden", "true");
            } else {
                lineCol.setAttribute("hidden", "false");
            }
            var columnCol = document.getElementById("runoutput-tree-column");
            if (parseRegex.indexOf("?P<column>") == -1) {
                columnCol.setAttribute("hidden", "true");
            } else {
                columnCol.setAttribute("hidden", "false");
            }
        }
    }
}

/**
 * Complete a terminal session. The command exited with the given value.
 */
this.endSession = function RunOutput_EndSession(retval)
{
    //dump("XXX RunOutput_EndSession(retval="+retval+")\n");
    _gTerminalView.endSession();

    var descWidget = document.getElementById("runoutput-desc");
    var command = descWidget.getAttribute("_command");
    var msg = null;
    var osSvc = Components.classes["@activestate.com/koOs;1"]
                       .getService(Components.interfaces.koIOs);
    if (retval < 0 && osSvc.name == "posix") {
        msg = _bundle.formatStringFromName("commandWasTerminatedBySignal.message", [command, (-retval)], 2);
    } else {
        msg = _bundle.formatStringFromName("commandReturned.message", [command, (retval)], 2);
    }
    if (retval != 0) {
        descWidget.style.setProperty("color", "#bb0000", ""); // dark red to not appear "neon" against grey.
    }
    descWidget.setAttribute("value", msg);

    _gProcess = null;
    var closeButton = document.getElementById("runoutput-close-button");
    closeButton.setAttribute("disabled", "true");
}

/**
 * Show the command output window.
 *
 * @param {Object} editor  The XUL window holding the command output window.
 * @param {bool} showParseOutputList  Indicated whether to show the
 *                                    parsed output list view.
 * @param {bool} focusPane  Whether focus is changed to the command output pane.
 */
this.show = function RunOutput_Show(editor, showParsedOutputList, focusPane)
{
    if (!editor) {
        _log.error("show: 'editor' is not true");
    }
    // Make sure the tab is visible
    ko.uilayout.ensureTabShown(window.frameElement.id, focusPane);

    // open the proper command output view
    _SetView(editor, showParsedOutputList);
}

/**
 * Pass a koIRunProcess reference to the output window so it can manipulate the
 * process that is being run in its terminal, if necessary.
 */
this.setProcessHandle = function RunOutput_SetProcessHandle(process)
{
    if (_gTerminalHandler.active) {
        _gProcess = process;
        var closeButton = document.getElementById("runoutput-close-button");
        closeButton.removeAttribute("disabled");
    }
}


/**
 * Kill the process currently running in the output window's terminal, if any.
 */
this.kill = function RunOutput_Kill(retval)
{
    if (_gProcess) {
        _gProcess.kill(retval);
    }
}


function _SetView(editor, showParsedOutputList)
{
    // ignore |editor|, always use the window we're in
    var deckWidget = window.document.getElementById("runoutput-deck");
    if (showParsedOutputList) {
        deckWidget.setAttribute("selectedIndex", 1);
    } else {
        deckWidget.setAttribute("selectedIndex", 0);
    }
}


this.toggleView = function RunOutput_ToggleView()
{
    var deckWidget = document.getElementById("runoutput-deck");
    if (deckWidget.getAttribute("selectedIndex") == 1) {
        _SetView(window, 0);
    } else {
        _SetView(window, 1);
    }
}



//---- Run output tree UI support routines.

this.scintillaOnClick = function RunOutput_ScintillaOnClick(event)
{
    // double-click in scintilla
    if (event.detail == 2 && _gParseOutput) {
        // Get the line double-clicked on.
        var x = event.layerX < 0 ? 0 : event.layerX;
        var y = event.layerY < 0 ? 0 : event.layerY;
        var scimoz = document.getElementById("runoutput-scintilla").scimoz;
        var lineNum = scimoz.lineFromPosition(scimoz.positionFromPoint(x,y));
        var lineObj = new Object();
        scimoz.getCurLine(lineObj);
        var line = lineObj.value;

        // Get the parsed result.
        var lastErrorSvc = Components.classes["@activestate.com/koLastErrorService;1"]
                           .getService(Components.interfaces.koILastErrorService);
        var fileObj = new Object();
        var lineNumObj = new Object();
        var columnNumObj = new Object();
        try {
            _gTerminalHandler.parseLine(line, fileObj, lineNumObj, columnNumObj);
        } catch (ex) {
            var errmsg = lastErrorSvc.getLastErrorMessage();
            alert(errmsg);
            return;
        }

        _JumpToResult(fileObj.value, lineNumObj.value,
                                columnNumObj.value);
        //XXX Does this cancel work?
        event.cancelBubble = true;
        event.preventDefault();
    }
}


this.treeOnClick = function RunOutput_TreeOnClick(event)
{
    // c.f. mozilla/mailnews/base/resources/content/threadPane.js
    var t = event.originalTarget;

    // single-click on a column
    if (t.localName == "treecol") {
        _gTerminalHandler.sort(t.id);
        _UpdateSortIndicators(window, t.id);
    }

    // double-click in the tree body
    else if (event.detail == 2 && t.localName == "treechildren") {
        var treeWidget = document.getElementById("runoutput-tree");
        var i = treeWidget.currentIndex;
        _JumpToResult(_gTerminalHandler.getFile(i),
                                _gTerminalHandler.getLine(i),
                                _gTerminalHandler.getColumn(i));

        // If the invoked result is the last visible one and there are more,
        // then scroll the list of find results by one.
        // XXX Could also scroll up if double-clicking on top visible item.
        var box = treeWidget.treeBoxObject;
        if (box.getLastVisibleRow() <= i && _gTerminalHandler.rowCount > i+1) {
            box.scrollByLines(1);
        }
    }
}


function _JumpToResult(file, line, column)
{
    // Jump to the parsed command output result.
    try {
        ko.open.displayPath(
            file, null,
            function(view) {
                if (!view) return;
                var scimoz = view.scintilla.scimoz;

                // If have line and column information then select that region.
                // XXX Have not tested this with line and column ranges yet.
                if (line) {
                    var start, end; // start and end positions to select

                    var firstLine, lastLine;
                    if (line.indexOf("-") == -1) {  // e.g., line == "4"
                        firstLine = line;
                        lastLine = line;
                    } else { // e.g., line == "3-6"
                        var lines = line.split("-");
                        firstLine = lines[0];
                        lastLine = lines[1];
                    }

                    if (column) {
                        var firstCol, lastCol;
                        if (column.indexOf("-") == -1) {  // e.g., column == "4"
                            firstCol = column;
                            lastCol = column;
                        } else { // e.g., column == "3-6"
                            var columns = column.split("-");
                            firstCol = columns[0];
                            lastCol = columns[1];
                        }

                        if (firstLine == lastLine && firstCol == lastCol) {
                            start = scimoz.positionFromLine(firstLine-1) + (firstCol-1);
                            end = start; // don't select if no range is given
                        } else {
                            start = scimoz.positionFromLine(firstLine-1) + (firstCol-1);
                            end = scimoz.positionFromLine(lastLine-1) + (lastCol-1);
                        }

                    } else {
                        start = scimoz.positionFromLine(firstLine - 1);
                        end = scimoz.getLineEndPosition(lastLine - 1);
                    }

                    scimoz.setSel(start, end);
                }

                scimoz.chooseCaretX();

                // transfer focus to the editor
                view.setFocus();
            }
        );
    } catch(ex) {
        _log.error("jumpToResult Could not open '"+file+"': "+ex);
        return;
    }
}


this.treeOnKeyPress = function RunOutput_TreeOnKeyPress(event)
{
    if (event.keyCode == 13) {
        // Open and/or switch to the appropriate file.
        var treeWidget = document.getElementById("runoutput-tree");
        var i = treeWidget.currentIndex;
        var file = _gTerminalHandler.getFile(i);
        var line = _gTerminalHandler.getLine(i);
        var column = _gTerminalHandler.getColumn(i);
        _JumpToResult(file, line, column);
        return false;
    }
    return true;
}


function _UpdateSortIndicators(mainWindow, sortId)
{
    var sortedColumn = null;

    // set the sort indicator on the column we are sorted by
    if (sortId) {
        sortedColumn = mainWindow.document.getElementById(sortId);
        if (sortedColumn) {
            var sortDirection = sortedColumn.getAttribute("sortDirection");
            if (sortDirection && sortDirection == "ascending") {
                sortedColumn.setAttribute("sortDirection", "descending");
            } else {
                sortedColumn.setAttribute("sortDirection", "ascending");
            }
        }
    }

    // remove the sort indicator from all the columns
    // except the one we are sorted by
    var currCol = mainWindow.document.getElementById("runoutput-tree").firstChild.firstChild;
    while (currCol) {
        while (currCol && currCol.localName != "treecol") {
            currCol = currCol.nextSibling;
        }
        if (currCol && (currCol != sortedColumn)) {
            currCol.removeAttribute("sortDirection");
        }
        if (currCol) {
            currCol = currCol.nextSibling;
        }
    }
}

this.onFocus = function RunOutput_OnFocus(event) {
    if (event.originalTarget != window) {
        // bubbled event
        return;
    }
    var selected = window.document.getElementById("runoutput-deck").selectedPanel;
    if ("scintilla" in selected) {
        selected.scintilla.focus();
    } else {
        selected.focus();
    }
};

window.addEventListener("focus", this.onFocus, false);

}).apply(ko.run.output);

window.addEventListener("load", ko.run.output.initialize, false);
