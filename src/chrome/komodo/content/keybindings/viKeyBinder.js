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
 * Portions created by ActiveState Software Inc are Copyright (C) 2000-2011
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

/* Handling of VI editor commands for Komodo.
 *
 * See:
 *  http://www.vim.org
 *
 * Author:
 *   Todd Whiteman
 *
 * Overview of how it works:
 *  - The vi-controller loads as part of the keybinding load / initialization.
 *  - It is enabled by having one or more cmd_vim_* commands being defined in
 *    the current keybinding scheme.
 *  - It intercepts keypress events within scintilla (when enabled), and may
 *    capture and swallow keypress events there.
 *  - The keybinding manager handles the mapping of vi key codes to the actual
 *    commands.
 *  - May override existing non-vi commands, catching the commands as they are
 *    called and can result in a different action if needed.
 *  - Remembers last commands, command mode history, search patterns etc...
 *
 * Commands:
 *  - Keybinds are setup in the "schemes/_vi.(unprocessed.)kkf file"
 *  - All commands go through the vim_doCommand() handler. This is so the
 *    vi controller knows what commands have been performed and what data was
 *    used for the commands. Mainly used for repeat, redo and undo operations.
 *  - Most of the vi commands map to existing komodo commands, so a 1-to-1
 *    mapping from vim_doCommand() to ko.commands.doCommand() exists. The ones that
 *    don't have a mapping are marked as VimController.SPECIAL_COMMAND, and are
 *    then implemented as JS functions (same name to the cmd) in this file.
 *
 * Mode:
 *  - Vi has a number of states/modes (search, command, repeat) that need to
 *    remember their state information. This is handled using one class object,
 *    called the VimController (gVimController is the global variable).
 *
 */
//
//---- BUGS:
//  - various bugs when working at beginning or end of lines, as vim treats the
//    end of line a little specially.
//  - repeat count of the form [n]x[m]y, where both m and n are supplied will
//    not work as expected (n * m xy), but will interpret as (nm xy).
//
//---- PERFORMANCE:
//  - This code is another layer on top of ko.commands.doCommand code, so it has
//    a large overhead for every command performed. Some multi-commands may
//    need to be moved into the scintilla python wrapper as one-command.
//
//---- TODO:
//  - support for more command mode ":" strings
//  - read in .vimrc to add certain customized workings
//  - implement markers??
//
//  See http://www.lagmonster.org/docs/vi.html for simple overview of most vi
//  features
//

var vimlog = ko.logging.getLogger('vimlog');
//vimlog.setLevel(ko.logging.LOG_DEBUG);

var gVimController;

function VimController_onload()
{
    vimlog.info("VimController_onload");
    try {
        gVimController = new VimController();
    } catch (e) {
        vimlog.error(e);
    }
}

function VimController() {
    try {
        this.enabled = false;
        this.enabledCallback = null;  // Callback for when the overload gets loaded
        this._mode = VimController.MODE_NORMAL;
        this._operationFlags = VimController.OPERATION_NONE; // Special operation type
        this._copyMode = VimController.COPY_NORMAL; // Type of copy operation done
        this._visualMode = VimController.VISUAL_CHAR;  // Visual selection mode
        this._internalBuffer = "";          // Internal clipboard
        // Used by find char in line commands "f", "T", ";" etc...
        this._movePosBefore = false;        // Used for commands that are the same, but just one pos before the other
        this._lastMovePosBefore = false;
        this._lastFindChar = "";
        this._lastReplaceChar = "";
        // Anchor and currentPos are used to store command movements
        this._currentPos = 0;
        this._anchor = 0;
        // Undo/redo/repeat
        this._repeatCount = 0;              // Number of times to repeat the command
        this._lastMode = VimController.MODE_NORMAL;
        this._lastOperationFlags = VimController.OPERATION_NONE; // Last operation type
        this._lastModifyCommand = "";       // Last modify command performed
        this._lastRepeatCount = 1;          // Number of times command was repeated
        this._lastInsertedText = "";        // String of text used in last insert command
        // Registers to store copy/paste information
        this._currentRegister = null;
        this._registers = {};
        // Searching
        this._findSvc = Services.koFind;

        this._inputBuffer_active = false;
        this._inputBuffer_history = [];        // History of previous values
        this._inputBuffer_historyPosition = 0; // Where we are up to in history
        this._inputBuffer_savedText = "";      // Saved edited input buffer

        this._lastSearchMatchWord = false;  // the matchWord option for the last search
        this._searchOptions = [];
        this._searchDirection = VimController.SEARCH_FORWARD;
        this._findCharDirection = VimController.SEARCH_FORWARD;
        this._find_error_occurred = false;
        // Command history
        this._commandHistory = [];            // Array of past command strings
        //this._commandHistoryPosition = 0;   // Where we are up to in history, unsed for undo/redo
        //this._commandHistoryRepeats = [];   // Array of past repeat counts
        // Command history for command mode
        this._commandModeHistory = [];      // Array of past command mode strings
        // Initialize the command details service
        XPCOMUtils.defineLazyGetter(this, "_commandDetails", () =>
            Cc["@activestate.com/koViCommandDetail;1"].getService(Ci.koIViCommandDetail));
        // Vi customized settings, get loaded from preferences
        this.settings = {};
        this._initSettings();
        // for soft char handling
        this.DECORATOR_SOFT_CHAR = Components.interfaces.koILintResult.DECORATOR_SOFT_CHAR;
    } catch (e) {
        vimlog.exception(e);
    }
}

// The following two lines ensure proper inheritance (see Flanagan, p. 144).
VimController.prototype = new xtk.Controller();
VimController.prototype.constructor = VimController;

VimController.prototype.destructor = function() {
}

// Vi Exceptions
VimController.ViError = function(msg) {
    this.message = msg;
    this.stack = this.getExceptionStack();
}
// Approach was taken from AssertException in casper/unittest.js
VimController.ViError.prototype = {
    getExceptionStack: function() {
        if (!((typeof Components == "object") &&
              (typeof Components.classes == "object")))
            return "No stack trace available.";
    
        var frame = Components.stack.caller.caller;
        var str = "<Exception stack>";
        while (frame) {
            var name = frame.name ? frame.name : "[anonymous]";
            str += "\n    " + name + "@" + frame.filename +':' + frame.lineNumber;
            frame = frame.caller;
        }
        return str+"\n";
    }
}

VimController.NotImplementedException = function(msg) {
    this.message = msg + " is not implemented";
}
VimController.NotImplementedException.prototype = new VimController.ViError("");


// Used to capture mouseup/selection movements when in visual mode
var gVim_onWindowMouseUpHandler = function(event) {
    // We only want events going to the view
    if ((event.target.nodeName == 'view') &&
        (!('originalTarget' in event) ||
         (event.originalTarget.nodeName != "html:input"))) {
        gVimController.updateModeIfBufferHasSelection(true);
    }
}

// Used to capture view changes.
var gVim_onCurrentViewChanged = function(event) {
    // When the view changes - always go back to the normal mode.
    gVimController.mode = VimController.MODE_NORMAL;
    var view = event.originalTarget;
    if (view.getAttribute("type") != "editor") {
        /* Only need to look at editor views. */
        return;
    }
    gVimController.updateCaretStyle(view.scimoz);
}

// Used to capture editor text modifications.
var gVim_onEditorModified = function(event) {
    var data = event.data;
    if (data.view.getAttribute("type") != "editor") {
        /* Only need to look at editor views. */
        return;
    }
    //dump('gVim_onEditorModified:: event.data.modificationType: ' + event.data.modificationType + '\n');
    //ko.logging.dumpObject(data);

    if ((gVimController._lastMode == VimController.MODE_REPLACE_CHAR) &&
        (gVimController._lastModifyCommand == "cmd_vim_replaceChar")) {
        // The replace command works a little differently than normal input.
        return;
    }
    if (gVimController.operationFlags == VimController.OPERATION_INDENT ||
        gVimController.operationFlags == VimController.OPERATION_DEDENT) {
        // Don't need to capture indentation changes - bug 89370.
        return;
    }
    var insertedText = gVimController._lastInsertedText;

    try {

    // This is more lot complex than I'd originally wanted, in order to properly
    // handle things like "soft chars" - we need to remember the original text
    // and position where the editing started and then for each edit we compare
    // that with the new position and new text being entered.
    //
    //     Editing normally - "ab|" => user adds "c" => "abc|":
    //       data.position: 2
    //       data.text: "c"
    //       insertedText: "ab"
    //       insertedTextStartPos: 0
    //       insertedTextEndPos:   2
    // 
    //     Soft chars - "abc(|)" => user adds "d" => "abc(d|)":
    //       data.position: 4
    //       data.text    : "d"
    //       insertedText : "abc()"
    //       insertedTextStartPos: 0
    //       insertedTextEndPos:   5
    // 

        if (data.modificationType & Components.interfaces.ISciMoz.SC_MOD_INSERTTEXT) {
            /* Text was inserted. */

            if (!insertedText) {
                /* Nothing yet - reset. */
                gVimController._lastInsertedText = data.text;
                gVimController._lastInsertedStartPosition = data.position;
                gVimController._lastInsertedEndPosition = data.position + data.bytelength;
                return;
            }
            var insertStartPos = gVimController._lastInsertedStartPosition;
            var insertEndPos = gVimController._lastInsertedEndPosition;
            //dump("  inserted text, position " + data.position + ", text '" + data.text + "'\n");
            //dump('    gVimController._lastInsertedText: "' + gVimController._lastInsertedText + '"\n');
            //dump('    gVimController._lastInsertedStartPosition: ' + gVimController._lastInsertedStartPosition + '\n');
            //dump('    gVimController._lastInsertedEndPosition: ' + gVimController._lastInsertedEndPosition + '\n');
            //dump('    insertEndPos: ' + insertEndPos + '\n');
            if (data.position == insertEndPos) {
                /* Normal case - just append the text. */
                //dump("    case 1\n");
                gVimController._lastInsertedText += data.text;
                gVimController._lastInsertedEndPosition += data.bytelength;
            } else if (data.position >= insertStartPos && data.position <= insertEndPos) {
                /* Soft char case, or user manually moved back in the text. */
                // Gah - has to access scimoz in order to get the char length,
                // as we only know the byte length.
                //dump("    case 2\n");
                var scimoz = data.view.scimoz;
                var beforeText = scimoz.getTextRange(insertStartPos, data.position);
                var newInsertedText = insertedText.substring(0, beforeText.length) + data.text + insertedText.substring(beforeText.length);
                //dump('      newInsertedText: ' + newInsertedText + '\n');
                gVimController._lastInsertedText = newInsertedText;
                gVimController._lastInsertedEndPosition += data.bytelength;
            } else {
                /* A different insert position - reset. */
                //dump("    case 3\n");
                gVimController._lastInsertedText = data.text;
                gVimController._lastInsertedStartPosition = data.position;
                gVimController._lastInsertedEndPosition = data.position + data.bytelength;
            }

        } else {
            /* Text was deleted. */

            if (!insertedText) {
                /* No text - nothing to do. */
                return;
            }
    
            var insertStartPos = gVimController._lastInsertedStartPosition - data.bytelength;
            var insertEndPos = gVimController._lastInsertedEndPosition - data.bytelength;

            //dump("  removed  text, position " + data.position + ", bytelength " + data.bytelength + "\n");
            //dump('    gVimController._lastInsertedText: "' + gVimController._lastInsertedText + '"\n');
            //dump('    gVimController._lastInsertedStartPosition: ' + gVimController._lastInsertedStartPosition + '\n');
            //dump('    gVimController._lastInsertedEndPosition: ' + gVimController._lastInsertedEndPosition + '\n');
            //dump('    insertEndPos: ' + insertEndPos + '\n');
            gVimController._lastInsertedText = "";
    
            if (data.position == insertEndPos) {
                /* Normal case - just remove the text from the end. */
                //dump("    case 1\n");
                gVimController._lastInsertedText = insertedText.slice(0, -data.text.length);
                gVimController._lastInsertedEndPosition -= data.bytelength;
            } else if (data.position >= insertStartPos && data.position <= insertEndPos) {
                /* Soft char case, or user moved back in the text. */
                // Gah - has to access scimoz in order to get the char length,
                // as we only know the byte length.
                //dump("    case 2\n");
                var scimoz = data.view.scimoz;
                var beforeText = scimoz.getTextRange(insertStartPos, data.position);
                var newInsertedText = insertedText.substring(0, beforeText.length) + insertedText.substring(beforeText.length + data.text.length);
                gVimController._lastInsertedText = newInsertedText;
                //dump('      newInsertedText: ' + newInsertedText + '\n');
                gVimController._lastInsertedEndPosition -= data.bytelength;
            } else {
                /* A different insert position - reset. */
                //dump("    case 3\n");
                gVimController._lastInsertedText = "";
            }
        }
    } catch (e) {
        vimlog.exception(e);
    }
}

VimController.prototype.enable = function(enabled) {
    if (enabled && !this.enabled) {
        window.addEventListener('mouseup', gVim_onWindowMouseUpHandler, true);
        window.addEventListener('current_view_changed', gVim_onCurrentViewChanged, true);
        window.addEventListener('editor_text_modified', gVim_onEditorModified, true);
        this.loadOverlay(); // load overlay eventually sets enabled to true
    } else if (!enabled) {
        this.enabledCallback = null;
        if (this.enabled) {
            window.removeEventListener('mouseup', gVim_onWindowMouseUpHandler, true);
            window.removeEventListener('current_view_changed', gVim_onCurrentViewChanged, true);
            window.removeEventListener('editor_text_modified', gVim_onEditorModified, true);
            this.unloadOverlay(); // unload overlay sets enabled to false
        }
    }
}

VimController.prototype.NAME = "VimController";
VimController.MODE_NORMAL  = 0;
VimController.MODE_INSERT  = 1;
VimController.MODE_SELECT  = 2;
VimController.MODE_SEARCH  = 3;
VimController.MODE_COMMAND = 4; // ":" Has been used
VimController.MODE_VISUAL  = 5; // User is in visual selection mode
VimController.MODE_SET_REGISTER = 6;  // Next character should be the register they want
//VimController.MODE_CHANGE_COMMAND = 7;  // Handle special case of c9b cases?
VimController.MODE_REPLACE_CHAR = 8;  // Used for vi "r" command
VimController.MODE_OVERTYPE     = 9;  // Used for vi "R" command
VimController.MODE_FIND_CHAR    = 10; // Used for vi "f", "F", "t", "T" commands

// Matching string names for _mode
VimController.MODE_NAMES = [
    "Normal",
    "Insert",
    "Select",
    "Search",
    "Command",
    "Visual",
    "Set register",
    "",
    "Replace char",
    "Overtype",
    "Find char",
    ""
];

// Operation flags used in NORMAL_MODE, mostly used in combination with a
// movement. Such as "d w" delete word, "y y" yank line (a special case)
VimController.OPERATION_NONE = 0;
VimController.OPERATION_YANK = 1;
VimController.OPERATION_DELETE = 2;
VimController.OPERATION_CHANGE = 3;  // Combination of yank and delete
VimController.OPERATION_INDENT = 4;
VimController.OPERATION_DEDENT = 5;

VimController.OPERATION_NAMES = [
    "None",
    "Yank",
    "Delete",
    "Change",
    "Indent",
    "Dedent",
    ""
];

// Search flags, used by _searchDirection and _findCharDirection
VimController.SEARCH_FORWARD  = 0;
VimController.SEARCH_BACKWARD = 1;

// Used by _visualMode
VimController.VISUAL_CHAR  = 0;     // Char grained selection
VimController.VISUAL_LINE  = 1;     // Line grained selction
VimController.VISUAL_BLOCK = 2;     // Block grained selection

VimController.VISUAL_NAMES = [
    "Char",
    "Line",
    "Block",
    ""
];

// Command flags
VimController.NO_REPEAT_ACTION  = 0x1;
VimController.REPEATABLE_ACTION = 0x2;    // Can be repeated
VimController.ENTER_MODE_INSERT = 0x4;
VimController.MODIFY_ACTION     = 0x8;    // Action modifies document
VimController.COPY_NORMAL       = 0x10;   // Normal copy / paste handling
VimController.COPY_LINES        = 0x20;   // Special line copy / paste handling
VimController.COPY_ACTION       = VimController.COPY_NORMAL |
                                  VimController.COPY_LINES;
VimController.SPECIAL_REPEAT_HANDLING = 0x40;   // Special handling of repeats
VimController.MOVEMENT_ACTION   = 0x80;     // If this command moves the cursor
VimController.WORKS_IN_VISUAL_MODE = 0x100; // Can be used in visual mode
VimController.CANCELS_VISUAL_MODE = 0x200;  // Cancels visual mode
VimController.CHOOSE_CARET_X =  0x400;      // Sets the caret X position after the command
VimController.DELAY_MODE_INSERT = 0x800;    // Do not enter insert mode yet
VimController.NO_OP_FLAG_CHANGE = 0x1000;   // Do not change the operation flag.

// Used as representation that this command is specially handled
// Commands with this value must have a matching JS function of the same name.
VimController.SPECIAL_COMMAND = null;

// Load the vi overlay
VimController.prototype.loadOverlay = function() {
    //dump("VimController.loadOverlay\n");
    window.controllers.appendController(this);
    var callback = {
        observe : function (subject, topic, data) {
            if (topic == 'xul-overlay-merged') {
                gVimController.enabled = true;
                gVimController.updateViInternals();
                // Force keybindings to reload it's command configuration, which
                // ensures the keybinding pref window shows the vi commands.
                ko.keybindings.manager.parseGlobalData();
                if (gVimController.enabledCallback) {
                    gVimController.enabledCallback.call();
                    gVimController.enabledCallback = null;
                }
            }
        }
    };
    // Enable vi keybindings - load the vi command overlay
    //dump("Loading vi overlay\n");
    ko.keybindings.manager.document.loadOverlay("chrome://komodo/content/keybindings/vi-commands-overlay.xul", callback);
}

// Remove the vi overlay commands
VimController.prototype.unloadOverlay = function() {
    //dump("VimController.unloadOverlay\n");

    var elStatusBarMode = this.statusBarMode;
    if (elStatusBarMode) {
        elStatusBarMode.parentNode.removeChild(elStatusBarMode);
    }
    var hbox = document.getElementById("vim-hbox");
    if (hbox) {
        hbox.parentNode.removeChild(hbox);
    }

    // Disable vi keybindings - remove the vi commandset
    var vimset = ko.keybindings.manager.document.getElementById('cmdset_vim');
    if (vimset && vimset.parentNode) {
        var parentNode = vimset.parentNode;
        //dump("Removing vimset: " + vimset + "\n");
        parentNode.removeChild(vimset);
        // Force keybindings to reload it's command configuration
        ko.keybindings.manager.parseGlobalData();
    }
    window.controllers.removeController(this);

    this.enabled = false;
    this.updateViInternals();
}

/**
 * Load customized vi settings.
 * @private
 */
VimController.prototype._initSettings = function() {
    var vimSetCommand;
    var settingName;
    var alias;
    var i;
    // Prefs
    var prefsSvc = Components.classes["@activestate.com/koPrefService;1"].
                            getService(Components.interfaces.koIPrefService);
    var prefs = prefsSvc.prefs;

    for (settingName in VimController.vim_set_commands) {
        vimSetCommand = VimController.vim_set_commands[settingName];
        // Add aliases names for settings
        for (i=0; i < vimSetCommand.aliases.length; i++) {
            alias = vimSetCommand.aliases[i];
            VimController.vim_set_commands[alias] = vimSetCommand;
            //dump("Added an alias: " + alias + " for " + settingName + "\n");
        }

        // Set the default file format to the same as the current platform
        if (settingName == "fileformat") {
            var sPlatform = navigator.platform.substring(0, 3).toLowerCase();
            if (sPlatform == "lin") {
                vimSetCommand.defaultValue = "unix";
            } else if (sPlatform == "dar" || sPlatform == "mac") {
                vimSetCommand.defaultValue = "mac";
            } // Else we leave it as the default of "dos"
        }

        if ("realPrefName" in vimSetCommand) {
            if (vimSetCommand.type == String) {
                this.settings[settingName] = prefs.getStringPref(vimSetCommand.realPrefName);
            } else if (vimSetCommand.type == Number) {
                this.settings[settingName] = prefs.getLongPref(vimSetCommand.realPrefName);
            } else if (vimSetCommand.type == Boolean) {
                this.settings[settingName] = prefs.getBooleanPref(vimSetCommand.realPrefName);
            }
        } else {
            // Add default setting to our vim controller
            this.settings[settingName] = vimSetCommand.defaultValue;
        }
    }

    if (prefs.hasPref("viCustomSettings")) {
        // viCustomSettings is a preference-set
        var viPrefs = prefs.getPref("viCustomSettings");
        var viSettingNames = viPrefs.getPrefIds();
        var prefType;
        var vim_set_command;
        for (var i = 0; i < viSettingNames.length; i++) {
            settingName = viSettingNames[i];
            if (settingName in VimController.vim_set_commands) {
                vim_set_command = VimController.vim_set_commands[settingName];
                prefType = viPrefs.getPrefType(settingName);
                if (prefType == "string" && vim_set_command.type == String) {
                    this.settings[settingName] = viPrefs.getStringPref(settingName);
                } else if (prefType == "long" && vim_set_command.type == Number) {
                    this.settings[settingName] = viPrefs.getLongPref(settingName);
                } else if (prefType == "boolean" && vim_set_command.type == Boolean) {
                    this.settings[settingName] = viPrefs.getBooleanPref(settingName);
                }
            }
        }
    }
}

// Controller related code - handling of commands
VimController.prototype.isCommandEnabled = function(cmdName) {
    if (cmdName.substr(0, 8) == "cmd_vim_")
        return true;
    return false;
}

VimController.prototype.supportsCommand = VimController.prototype.isCommandEnabled;

VimController.prototype.doCommand = function(cmdName) {
    return vim_doCommand(cmdName);
}

VimController.prototype.onBufferFocus =
VimController.prototype.updateViInternals = function() {
    if (this.enabled) {
        if (ko.views.manager && ko.views.manager.currentView && ko.views.manager.currentView.scintilla) {
            this.updateCaretStyle(ko.views.manager.currentView.scimoz);
            this.updateModeIfBufferHasSelection(false);
        }
    } else {
        this.mode = VimController.MODE_NORMAL;
        // Set the cursor back to it's preferenced style. Fixes bug:
        // http://bugs.activestate.com/show_bug.cgi?id=71293
        if (typeof(ko.views.manager) != 'undefined' && ko.views.manager && ko.views.manager.currentView &&
            ko.views.manager.currentView.koDoc && ko.views.manager.currentView.scintilla) {
            var scimoz = ko.views.manager.currentView.scintilla.scimoz;
            var prefs = ko.views.manager.currentView.koDoc.getEffectivePrefs();
            scimoz.caretStyle = prefs.getLongPref('caretStyle');
            scimoz.caretWidth = prefs.getLongPref('caretWidth');
        }
    }
}

/**
 * Set the vi statusbar message.
 * @param {string} message  The message to be displayed in the statusbar
 * @param {int} timeout  If > 0, the milliseconds until message disappears
 * @param {boolean} highlight  Highlight the statusbar message.
 */
VimController.prototype.setStatusBarMessage = function(message, timeout,
                                                       highlight)
{
    require("notify/notify").send(message, "viEmulation",
                                  {priority: highlight ? "warning" : "info"});
}

VimController.prototype.updateStatusBarMode = function() {
    // Add message to status bar informing of the mode change
    var mode = this.mode;
    var modeMsg = VimController.MODE_NAMES[mode];
    if (mode == VimController.MODE_VISUAL) {
        // Show which visual mode it is
        if (this._visualMode != VimController.VISUAL_CHAR) {
            modeMsg += " " + VimController.VISUAL_NAMES[this._visualMode];
        }
    }
    this.statusBarMode.label = modeMsg;
}

VimController.prototype.updateCaretStyle = function(scimoz) {
    if (!scimoz) {
        return;
    }
    if ((this._mode == VimController.MODE_INSERT) ||
        (this._mode == VimController.MODE_OVERTYPE)) {
        //scimoz.caretWidth = 2;
        scimoz.caretStyle = scimoz.CARETSTYLE_LINE;
        //dump("VimController:: Making caret a LINE style\n");
    } else {
        //scimoz.caretWidth = 1;
        scimoz.caretStyle = scimoz.CARETSTYLE_BLOCK;
        //dump("VimController:: Making caret a BLOCK style\n");
    }
}

VimController.prototype.updateModeIfBufferHasSelection = function(fromMouseUp) {
    if (typeof(ko.views.manager) != 'undefined' && ko.views.manager && ko.views.manager.currentView &&
        ko.views.manager.currentView.koDoc && ko.views.manager.currentView.scintilla) {
        var scimoz = ko.views.manager.currentView.scintilla.scimoz;
        if ((this.mode != VimController.MODE_VISUAL) &&
            (scimoz.currentPos != scimoz.anchor)) {
            // Default will be char visual mode
            this._visualMode = VimController.VISUAL_CHAR;
            this.mode = VimController.MODE_VISUAL;
        // If we are in visual mode already, it might have been clicked away
        } else if (fromMouseUp && (this.mode == VimController.MODE_VISUAL) &&
                   (scimoz.currentPos == scimoz.anchor)) {
            this.mode = VimController.MODE_NORMAL;
        }
    }
}

// Special class getters and setters
VimController.prototype.__defineGetter__("mode", function() { return this._mode });
VimController.prototype.__defineSetter__("mode", function(new_mode) {
    var old_mode = this._mode;
    // Now update the mode
    this._mode = new_mode;

    if ((old_mode != VimController.MODE_NORMAL) &&
        (old_mode != VimController.MODE_VISUAL) &&
        (old_mode != VimController.MODE_FIND_CHAR)) {
        // Reset the repeat count
        this.repeatCount = 0;
    }

    // If the mode changed, update the vi characteristics
    if (old_mode != new_mode) {
        vimlog.debug("Vi changed mode from " + old_mode + " to " + new_mode);
        // Remember the last mode
        this._lastMode = old_mode;
        this._movePosBefore = false;
        // Set operation type back to none, find modes do not change it though,
        // on both going into and coming out of the find modes. Fixes:
        // http://bugs.activestate.com/show_bug.cgi?id=67045
        if ((new_mode != VimController.MODE_FIND_CHAR) &&
            (new_mode != VimController.MODE_SEARCH) &&
            (old_mode != VimController.MODE_FIND_CHAR) &&
            (old_mode != VimController.MODE_SEARCH)) {
            this.operationFlags = VimController.OPERATION_NONE;
        }
        var scimoz = null;
        if (old_mode == VimController.MODE_OVERTYPE) {
            // Turning off overtype mode
            ko.views.manager.currentView.scintilla.scimoz.overtype = 0;
        } else if ((new_mode == VimController.MODE_NORMAL) &&
                   (old_mode == VimController.MODE_VISUAL)) {
            // Remove any selection when leaving visual mode for normal mode
            scimoz = ko.views.manager.currentView.scimoz;
            // scimoz.cancel() used to ensure removal of the selectionmode
            // http://bugs.activestate.com/show_bug.cgi?id=65580
            scimoz.selectionMode = scimoz.SC_SEL_STREAM;
            scimoz.cancel();
            scimoz.setSel(-1, scimoz.currentPos);  // anchorPos of -1 means remove any selection
            this._visualMode = VimController.VISUAL_CHAR;
        }
        this.updateCaretStyle(scimoz || (ko.views.manager.currentView &&
                                         ko.views.manager.currentView.scimoz));
        this.updateStatusBarMode();
    }
});

VimController.prototype.__defineGetter__("repeatCount", function() { return this._repeatCount });
VimController.prototype.__defineSetter__("repeatCount", function(new_count) {
    if (this._repeatCount != new_count) {
        vimlog.debug("Setting repeatCount to: " + new_count);
        if (new_count > 0) {
            this.setStatusBarMessage("Repeat " + new_count + " times",
                                     0, false);
        } else {
            this.setStatusBarMessage("", 0, false);
        }
        this._repeatCount = new_count;
    }
});

VimController.prototype.__defineGetter__("operationFlags", function() { return this._operationFlags });
VimController.prototype.__defineSetter__("operationFlags", function(new_operationFlags) {
    if (this._operationFlags != new_operationFlags) {
        vimlog.debug("vi:: changing operationFlags from: "+
                     this.operationFlags+", to: "+new_operationFlags);
        this._operationFlags = new_operationFlags;
    }
});

// Some XUL element getters
VimController.prototype.__defineGetter__("inputBuffer",
    function() {
        return document.getElementById("vim-input-buffer");
    }
);
VimController.prototype.__defineGetter__("inputBufferLabel",
    function() {
        return document.getElementById("vim-input-label");
    }
);
VimController.prototype.__defineGetter__("statusBarDeck",
    function() {
        return document.getElementById("statusbar-message-deck");
    }
);
VimController.prototype.__defineGetter__("statusBarMode",
    function() {
        return document.getElementById("vim-statusbar-mode");
    }
);


VimController.prototype.resetCommandSettings = function() {
    if (this.mode != VimController.MODE_FIND_CHAR) {
        this.operationFlags = VimController.OPERATION_NONE;
        this._currentRegister = null;
    }
}

VimController.prototype.updateVisualModeSelection = function(scimoz,
                                                             currentPos,
                                                             anchorPos) {
    vimlog.debug("updateVisualModeSelection:: currentPos: "+currentPos+
                 ", anchorPos: "+anchorPos);
    if (this._visualMode == VimController.VISUAL_LINE) {
        scimoz.selectionMode = scimoz.SC_SEL_LINES;
    } else if (this._visualMode == VimController.VISUAL_BLOCK) {
        scimoz.selectionMode = scimoz.SC_SEL_RECTANGLE;
    }
    if (typeof(currentPos) != 'undefined' && currentPos != null) {
        scimoz.currentPos = currentPos;
    }
    if (typeof(anchorPos) != 'undefined' && anchorPos != null) {
        scimoz.anchor = anchorPos;
    }
    vimlog.debug("updateVisualModeSelection:: new currentPos: "+currentPos+
                 ", new anchorPos: "+anchorPos);
}

VimController.prototype.updateCursorAndSelection = function(scimoz,
                                                            oldCurrentPos,
                                                            newCurrentPos,
                                                            anchorPos,
                                                            setCaretX) {
    // Update the current position with scimoz if it's changed by vi
    if (gVimController.mode == VimController.MODE_VISUAL) {
        // Save these values, so we can support visual mode
        gVimController.updateVisualModeSelection(scimoz,
                                                 newCurrentPos,
                                                 anchorPos);
        scimoz.scrollCaret();
    } else if ((newCurrentPos != null) && (newCurrentPos != oldCurrentPos)) {
        vimlog.debug("updateCursorAndSelection:: Setting currentPos: "+newCurrentPos+
                     ", oldCurrentPos: "+oldCurrentPos);
        scimoz.currentPos = newCurrentPos;
        // Set anchor to the same spot, so we don't have a selection
        vimlog.debug("updateCursorAndSelection:: NOT Visual Mode: Removing any selection");
        scimoz.anchor = newCurrentPos;
        scimoz.scrollCaret();
    } else {
        vimlog.debug("updateCursorAndSelection:: Nothing changed");
    }
    if (setCaretX) {
        scimoz.chooseCaretX();
    }
}


//
// Key press handling
//

// Handling keypress, called from the main keybinding manager.
// We return true when we don't want the key binding manager to handle this
// keypress (i.e. so it does not match to a keybinding).
// This is used to allow a vi repeat count when we are in a prefix capture
// mode, i.e to allow for "d5w" command syntax. We will get the event again in
// the main keypressHandler function below, when called by xbl views-editor.
VimController.prototype.inSpecialModeHandler = function(event) {
    try {
        // If there is a key_handler (like iSearch), we don't want the
        // vi keybingings handling the event.
        // http://bugs.activestate.com/show_bug.cgi?id=65406
        if (ko.views.manager.currentView && ko.views.manager.currentView.scintilla &&
            ko.views.manager.currentView.scintilla.key_handler) {
            return true;
        }

        if ((this.mode == VimController.MODE_NORMAL) ||
            (this.mode == VimController.MODE_VISUAL)) {
            var charCode = event.charCode;
            var specialKeyUsed = event.ctrlKey || event.altKey || event.metaKey;
            if (!specialKeyUsed && 
                (((charCode == event.DOM_VK_0) &&
                  (this.repeatCount > 0)) ||
                 ((charCode >= event.DOM_VK_1) &&
                  (charCode <= event.DOM_VK_9)))) {
                return true;
            }
        }
    } catch (e) {
        vimlog.exception(e);
    }
    return false;
}


// Used to map commands into vi commands when the vi mode == MODE_NORMAL
var normalModeCommandMap = {
    'cmd_left':                 'cmd_vim_left',
    'cmd_right':                'cmd_vim_right',
    'cmd_linePrevious':         'cmd_vim_linePrevious',
    'cmd_lineNext':             'cmd_vim_lineNext',
    'cmd_pageDown':             'cmd_vim_pageDown',
    'cmd_pageUp':               'cmd_vim_pageUp',
    'cmd_lineScrollUp':         'cmd_vim_lineScrollUp',
    'cmd_lineScrollDown':       'cmd_vim_lineScrollDown',
    'cmd_newline':              'cmd_vim_lineNextHome',
    'cmd_backSmart':            'cmd_vim_left',
    'cmd_delete':               'cmd_vim_cutChar'
};

// Vi handles command
VimController.prototype.handleCommand = function(event, commandname, keylabel, multikey) {
    try {
        /* Ensure it's going to a Komodo view element. */
        if (!this.enabled || event.target.nodeName != 'view') {
            return false;
        }

        /* Ensure it's going to a Komodo Scintilla element.
           Note: Certain commands like cmd_cancel and cmd_right event can
                 arrive with an event target that is the Komodo multi view. Not
                 sure why that is - likely something to do with split view, so
                 added a special case to allow multiview event targets as well.
                 Without this, the views-browser URL base will not accept
                 cmd_delete or cursor movement events.
        */
        var view = event.target;
        try {
            // Multiview handling, we want the editor view - bug 97891.
            while (view.currentView) {
                view = view.currentView;
            }
        } catch (ex) {
            // Some views don't implement .currentView, that's okay
        }
        if (!view.scintilla) {
            return false;
        }
        if (!view.scintilla.isFocused) {
            // focusing somewhere else in the view
            return false;
        }

        if (commandname == 'cmd_cancel') {
            var cancelCmd = true;
            if (this.mode == VimController.MODE_NORMAL) {
                cancelCmd = false;
            }
            vim_doCommand('cmd_vim_cancel');
            return cancelCmd;
        } else if ((this.mode == VimController.MODE_NORMAL) ||
                   (this.mode == VimController.MODE_VISUAL)) {
            if (commandname in normalModeCommandMap) {
                var mappedCommand = normalModeCommandMap[commandname];
                //dump("commandname in handledCommandMap: true" + "\n");
                vim_doCommand(mappedCommand);
                return true;
            }
        }
    } catch (e) {
        vimlog.exception(e);
    }
    return false;
}

// Find the given character in the current line and move to it
VimController.prototype.findCharInLine = function(scimoz, charToFind,
                                                  movePosBefore,
                                                  repeatCount,
                                                  reverseDirection /* false */) {
    try {
        var findDirection = this._findCharDirection;
        vimlog.debug("findCharInLine:: charToFind: '" + charToFind + "'");
        vimlog.debug("findCharInLine:: findDirection: " + findDirection);
        vimlog.debug("findCharInLine:: movePosBefore: " + movePosBefore);
        vimlog.debug("findCharInLine:: repeatCount: " + repeatCount);
        vimlog.debug("findCharInLine:: reverseDirection: " + reverseDirection);
        if (reverseDirection) {
            findDirection = Number(!findDirection);
        }
        var currentPos = scimoz.currentPos;
        var lineNo = scimoz.lineFromPosition(currentPos);
        if (findDirection == VimController.SEARCH_BACKWARD) {
            var lineStartPos = scimoz.positionFromLine(lineNo);;
            var text = scimoz.getTextRange(lineStartPos, currentPos);
            var pos = text.lastIndexOf(charToFind);
            var foundPos = -1;
            // Use repeat count
            for (var i=1; i < repeatCount; i++) {
                foundPos = text.lastIndexOf(charToFind, pos-1);
                if (foundPos < 0)
                    break;
                pos = foundPos;
            }
            if (movePosBefore) {
                // For T command, it's the position after the char
                pos += 1;
            }
            if (pos >= 0) {
                // Found it, lets move to it then
                var newCurrentPos = lineStartPos + ko.stringutils.bytelength(text.substr(0, pos));
                vimlog.debug("findCharInLine:: currentPos: " + currentPos + ", pos: " + pos +", newCurrentPos: "+newCurrentPos);
                this._currentPos = newCurrentPos;
            }
        } else {
            var lineEndPos = scimoz.getLineEndPosition(lineNo);
            var nextPos = scimoz.positionAfter(currentPos);
            var text = scimoz.getTextRange(nextPos, lineEndPos);
            var pos = text.indexOf(charToFind);
            var foundPos = -1;
            // Use repeat count
            for (var i=1; i < repeatCount; i++) {
                foundPos = text.indexOf(charToFind, pos+1);
                if (foundPos < 0)
                    break;
                pos = foundPos;
            }
            if (movePosBefore) {
                // For T command, it's the position before the char
                pos -= 1;
            }
            if (pos >= 0) {
                // When working with the yank, change and delete operations,
                // we need to include the found character position. See:
                // http://bugs.activestate.com/show_bug.cgi?id=67045#c9
                if (this.operationFlags) {
                    pos = scimoz.positionAfter(pos);
                }
                // Found it, lets move to it then
                var newCurrentPos = nextPos + ko.stringutils.bytelength(text.substr(0, pos));
                vimlog.debug("findCharInLine:: currentPos: " + currentPos + ", pos: " + pos +", newCurrentPos: "+newCurrentPos);
                this._currentPos = newCurrentPos;
            }
        }
    } catch (e) {
        vimlog.exception(e);
    }
}

// Registers must be one of [a-zA-Z0-9:.%#*+~=-_/]
VimController.prototype.regexIsValidRegister = new RegExp('[a-zA-Z0-9\\:\\.\\%\\#\\*\\+\\~\\=\\-\\_\\/]');
VimController.prototype.regexRegisterIsReadonly = new RegExp('[\\:\\.\\%\\#\\=\\/\\~]');
// Test regex for copy/paste text type
VimController.prototype.regexContainsNewline = new RegExp(".*[\\r\\n].*");

// Handling keypress, called from the views-editor xul widget.
// We return false when we want this key event to continue on to other elements.
// Note: Returning true means the event is stopped (handled).
VimController.prototype.handleKeypress = function(event) {
    try {
        var keyCode = event.keyCode;
        var charCode = event.charCode;
        var key_char = String.fromCharCode(charCode);
        var specialKeyUsed = event.ctrlKey || event.altKey || event.metaKey;

        if (key_char == "\0") {
            // This is just so the dump/print operation works
            key_char = "\\0";
        }
        //dump(this.NAME + "::sendKeypressToScintilla: mode: " + this.mode + ", charCode: '" + key_char + "' (" + charCode + "), keyCode: " + keyCode + "\n");
    
        if (this.mode == VimController.MODE_INSERT ||
            this.mode == VimController.MODE_OVERTYPE) {
            // Any normal character should be fine to send to scintilla as is
            return false;

        } else if (this.mode == VimController.MODE_REPLACE_CHAR) {
            if (charCode != 0) {
                this._lastReplaceChar = key_char;
                vim_doCommand('cmd_vim_doReplaceChar');
                this.mode = VimController.MODE_NORMAL;
                return true;
            }
            this.mode = VimController.MODE_NORMAL;
            return false;

        } else if (this.mode == VimController.MODE_SET_REGISTER) {
            this.mode = this._lastMode;
            if ((charCode == 0) || !(this.regexIsValidRegister.test(key_char))) {
                var msg = "Invalid register character";
                if (charCode) {
                    // Add the character to the message
                    msg += ": '" + key_char + "'";
                }
                this.setStatusBarMessage(msg, 5000, true);
                return true;
            }
            this._currentRegister = key_char;
            vimlog.info("Setting register to: " + key_char);

        } else if (this.mode == VimController.MODE_FIND_CHAR) {
            // Get movePosBefore before the mode changes, otherwise it's reset
            var movePosBefore = this._movePosBefore;
            var repeatCount = this._repeatCount;
            // We set last mode here, so visual mode selection continues to work
            this.mode = this._lastMode;
            var charToFind = key_char;
            //dump("Wanting to find: " + charToFind + "\n");
            if (charToFind) {
                // Save last moved, used by repeat last find char ";" and ","
                this._lastMovePosBefore = movePosBefore;
                this._lastFindChar = charToFind;
                this._lastRepeatCount = repeatCount;
                vim_doCommand("cmd_vim_repeatLastFindCharInLine");
            }

        } else if ((this.mode == VimController.MODE_NORMAL) ||
                   (this.mode == VimController.MODE_VISUAL)) {
            // Special case for repeat counts, the repeat count gets set
            // when checking if the event should go to scintilla.
            // TAB is handled specially by the scintilla overlay.
            if (keyCode == event.DOM_VK_TAB) {
                // Leave TAB keypress alone, let the scintilla-overlay handle it
                return false;
            } else if (!specialKeyUsed &&
                       (((charCode == event.DOM_VK_0) &&
                         (this.repeatCount > 0)) ||
                        ((charCode >= event.DOM_VK_1) &&
                         (charCode <= event.DOM_VK_9)))) {
                // Repeat counts, swallows this event
                this.repeatCount = (this.repeatCount * 10) + (charCode - event.DOM_VK_0);
            } else if (event.keyCode == 0 && !specialKeyUsed) {
                // Stop normal characters going to scintilla
                //dump("    stopping the event.\n");
                event.stopPropagation();
                event.preventDefault();
                event.cancelBubble = true;
                ko.keybindings.manager.keypressHandler(event);
            } else {
                // Else, leave everything else alone
                return false;
            }

        } else if ((this.mode == VimController.MODE_SEARCH) ||
                   (this.mode == VimController.MODE_COMMAND)) {
            this.inputBufferFocus();
        }
    } catch (e) {
        vimlog.exception(e);
    }
    return true;
}

/**
 * Setup and show the vi command input buffer.
 * @param {array} commandHistory  Items to be shown though up arrow usage.
 * @param {string} initialText  Initial text to be displayed in the buffer.
 */
VimController.prototype.inputBufferStart = function (commandHistory,
                                                     label,
                                                     initialText /* "" */)
{
    try {
        if (!label) {
            this.inputBufferLabel.setAttribute("collapsed", "true");
        } else {
            this.inputBufferLabel.setAttribute("value", label);
            this.inputBufferLabel.setAttribute("collapsed", "false");
        }
        if (!initialText) {
            initialText = "";
        }
        this._inputBuffer_active = true;
        this._inputBuffer_history = commandHistory;
        this._inputBuffer_historyPosition = this._inputBuffer_history.length;
        var xulInputBuffer = this.inputBuffer;
        xulInputBuffer.value = initialText;
        this.statusBarDeck.selectedPanel = document.getElementById("vim-hbox");
        xulInputBuffer.addEventListener('keypress', vim_InputBuffer_KeyPress, false);
        xulInputBuffer.focus();
    } catch (e) {
        vimlog.exception(e);
    }
}

VimController.prototype.inputBufferFocus = function ()
{
    try {
        if (this._inputBuffer_active) {
            this.inputBuffer.focus();
        }
    } catch (e) {
        vimlog.exception(e);
    }
}

VimController.prototype.inputBufferFinish = function ()
{
    try {
        // Return the contents of the input buffer and stop buffering.
        var contents = this.inputBuffer.value;
        this.inputBuffer.value = "";
        this.statusBarDeck.selectedIndex = 0;
        this.inputBuffer.removeEventListener('keypress', vim_InputBuffer_KeyPress, false);
        this._inputBuffer_active = false;
        return contents;
    } catch (e) {
        vimlog.exception(e);
    }
    return "";
}

VimController.prototype.inputBufferPrevious = function ()
{
    try {
        var pos = this._inputBuffer_historyPosition;
        if (pos == 0) {
            // No previous commands
            return;
        }
        if (pos == this._inputBuffer_history.length) {
            // We are at the end, save the current input buffer
            this._inputBuffer_savedText = this.inputBuffer.value;
        }
        pos -= 1;
        this.inputBuffer.value = this._inputBuffer_history[pos];
        this._inputBuffer_historyPosition = pos;
    } catch (e) {
        vimlog.exception(e);
    }
}

VimController.prototype.inputBufferNext = function ()
{
    try {
        var pos = this._inputBuffer_historyPosition;
        if (pos >= this._inputBuffer_history.length) {
            // We are at the end already
            return;
        }
        pos += 1;
        if (pos == this._inputBuffer_history.length) {
            // We are at the end, restore the saved input buffer
            this.inputBuffer.value = this._inputBuffer_savedText;
        } else {
            this.inputBuffer.value = this._inputBuffer_history[pos];
        }
        this._inputBuffer_historyPosition = pos;
    } catch (e) {
        vimlog.exception(e);
    }
}

VimController.prototype.inputBufferSaveHistory = function (value)
{
    try {
        vimlog.debug("inputBufferSaveHistory: adding value '" + value + "'");
        if (this._inputBuffer_historyPosition > 0) {
            // We have previous commands, make sure it's not the same as the
            // previous command.
            if (value == this._inputBuffer_history[this._inputBuffer_historyPosition])
                return;
        }
        this._inputBuffer_history.push(value);
    } catch (e) {
        vimlog.exception(e);
    }
}

VimController.prototype._getTextFromClipboard = function () {
    try {
        return xtk.clipboard.getText();
    } catch (e) {
        vimlog.exception(e);
    }
    return "";
}

VimController.prototype._copyTextToClipboard = function(text) {
    try {
        xtk.clipboard.setText(text);
    } catch (e) {
        vimlog.exception(e);
    }
}

/**
 * Debugging: Print out the registers we have set
 */
VimController.prototype._dumpRegisters = function () {
    try {
        dump("Registers:\n");
        for (var register in this._registers) {
            dump("  [" + register + "]: '" + this._registers[register] + "'\n");
        }
    } catch (e) {
        vimlog.exception(e);
    }
}

/**
 * Handling the update of register information.
 *
 * @param {string} text the text that is copied/changed or deleted)
 * @param {bool} isDeleted if the text was deleted (by a change or delete command)
 * @private
 */
VimController.prototype.updateRegisters = function (text, isDeleted) {
    try {
        if (!this._currentRegister) {
            vimlog.debug("updateRegisters: isDeleted: " + isDeleted);
            if (isDeleted) {
                // If the text is less than one line, update the small delete
                // register "-"
                if (!this.regexContainsNewline.test(text)) {
                    this._registers["-"] = text;
                } else {
                    // Update the special register list 1-9
                    var regValue;
                    for (var i=9; i > 1; i--) {
                        regValue = this._registers[String(i-1)];
                        if (typeof(regValue) != 'undefined') {
                            this._registers[String(i)] = regValue;
                        }
                    }
                    this._registers["1"] = text;
                }
            } else {
                // It's a copy/yank text command
                // Update the "0" register, only when no other register used
                this._registers["0"] = text;
            }
        } else {
            // If there is a register in use, copy the buffer there
            if (this._currentRegister && this._currentRegister != "_" /* black hole register */) {
                if (this._currentRegister == "*" /* clipboard register */ ||
                    this._currentRegister == "+" /* alternative clipboard register */) {
                    this._copyTextToClipboard(text);
                } else if (this._currentRegister == '"' /* unnamed register */) {
                    // writing here actually write to "0"
                    this._registers["0"] = text;
                } else {
                    this._registers[this._currentRegister] = text;
                }
            }
        }
        //this._dumpRegisters();
    } catch (e) {
        vimlog.exception(e);
    }
}

/**
 * Handling copy and paste (now handled internally, this._internalBuffer)
 *
 * @param scimoz {Components.interfaces.ISciMoz} Scintilla xpcom object
 * @param {int} start start position in buffer
 * @param {int} end end position in buffer
 * @param {boolean} deleteRange remove this range once copied
 * @param {boolean} ensureEndsWithNewline
 *        ensure the copied text ends with a newline
 */
VimController.prototype.copyInternal = function (scimoz, start, end,
                                                 deleteRange /* false */,
                                                 ensureEndsWithNewline /* false */) {
    if (typeof(ensureEndsWithNewline) == 'undefined') {
        ensureEndsWithNewline = false;
    }
    try {
        if (this._currentRegister && this.regexRegisterIsReadonly.test(this._currentRegister)) {
            this.setStatusBarMessage("Cannot write to readonly register: " + this._currentRegister,
                                     5000, true);
            return;
        }
        if (this._visualMode == VimController.VISUAL_LINE) {
            // Need to include the EOL for the last line - bug 87241.
            var lineNo = scimoz.lineFromPosition(end);
            end = scimoz.positionFromLine(lineNo+1);
        }
        if (start < end) {
            this._internalBuffer += scimoz.getTextRange(start, end);
            if (deleteRange) {
                // Change or delete text command
                scimoz.targetStart = start;
                scimoz.targetEnd = end;
                scimoz.replaceTarget(0, "");
            }
            if (ensureEndsWithNewline) {
                var lastchar = this._internalBuffer[this._internalBuffer.length - 1];
                if (lastchar != '\r' && lastchar != '\n') {
                    switch (scimoz.eOLMode) {
                        case Components.interfaces.ISciMoz.SC_EOL_CR:
                            this._internalBuffer += "\r";
                            break;
                        case Components.interfaces.ISciMoz.SC_EOL_CRLF:
                            this._internalBuffer += "\r\n";
                            break;
                        default:
                            this._internalBuffer += "\n";
                            break;
                    }
                }
            }
            this.updateRegisters(this._internalBuffer, deleteRange);
        }
    } catch (e) {
        vimlog.exception(e);
    }
}

VimController.prototype._getTextForPaste = function() {
    vimlog.debug("_getTextForPaste, register is: " + this._currentRegister);
    //this._dumpRegisters();
    var buf = null;
    if (this._currentRegister) {
        // [a-zA-Z0-9\\:\\.\\%\\#\\*\\+\\~\\=\\-\\_\\/]
        if (this._currentRegister in this._registers) {
            buf = this._registers[this._currentRegister];
        } else if (this._currentRegister == "*" /* clipboard register */ ||
                   this._currentRegister == "+" /* alternative clipboard register */) {
            buf = this._getTextFromClipboard();
        } else if (this._currentRegister == "%" /* filename register */) {
            buf = view.koDoc.file.displayPath;
        } else if (this._currentRegister == "." /* last inserted text register */) {
            buf = this._lastInsertedText;
        } else if (this._currentRegister == ":" /* last command register */) {
            var historyPos = this._inputBuffer_history.length - 1;
            if (historyPos >= 0) {
                buf = this._inputBuffer_history[historyPos]
            }
        } else if (this._currentRegister == "/" /* last search register */) {
            buf = ko.mru.get("find-patternMru");
        } else if (this._currentRegister == "~" /* last drag-n-drop register */ ||
                   this._currentRegister == "=" /* expression register */ ||
                   this._currentRegister == "#" /* alternative file register */) {
            throw new VimController.NotImplementedException("Drag-n-drop register");
        }
    } else {
        buf = this._internalBuffer;
    }
    if (buf && this.regexContainsNewline.test(buf)) {
        this._copyMode = VimController.COPY_LINES;
    } else {
        this._copyMode = VimController.COPY_NORMAL;
    }
    return buf;
}

//
// Handling searches
//
VimController.prototype.initSearchForward = function () {
    try {
            // Get the list from the mru find pref
        this.inputBufferStart(ko.mru.getAll('find-patternMru', 100), "/");
        this._searchDirection = VimController.SEARCH_FORWARD;
        this.mode = VimController.MODE_SEARCH;
    } catch (e) {
        vimlog.exception(e);
    }
}

VimController.prototype.initSearchBackward = function () {
    try {
        this.inputBufferStart(ko.mru.getAll('find-patternMru', 100), "?");
        this._searchDirection = VimController.SEARCH_BACKWARD;
        this.mode = VimController.MODE_SEARCH;
    } catch (e) {
        vimlog.exception(e);
    }
}

VimController.prototype._saveFindSvcOptions = function() {
    this._findSvc_searchBackward = this._findSvc.options.searchBackward;
    this._findSvc_matchWord = this._findSvc.options.matchWord;
    this._findSvc_patternType = this._findSvc.options.patternType;
    this._findSvc_caseSensitivity = this._findSvc.options.caseSensitivity;
}

VimController.prototype._restoreFindSvcOptions = function() {
    this._findSvc.options.searchBackward = this._findSvc_searchBackward;
    this._findSvc.options.matchWord = this._findSvc_matchWord;
    this._findSvc.options.patternType = this._findSvc_patternType;
    this._findSvc.options.caseSensitivity = this._findSvc_caseSensitivity;
}

VimController.prototype._setFindSvcContext = function(type)
{
    this._findSvc.options.patternType = this._findSvc.options.FOT_REGEX_PYTHON;

    // Specified options override the current settings
    if ((type == "replace") && (this._searchOptions.indexOf('i') >= 0)) {
        this._findSvc.options.caseSensitivity = this._findSvc.options.FOC_INSENSITIVE;
    } else if ((type == "replace") && (this._searchOptions.indexOf('I') >= 0)) {
        this._findSvc.options.caseSensitivity = this._findSvc.options.FOC_SENSITIVE;
    } else if ((type == "find") && (this._searchOptions.indexOf('c') >= 0)) {
        this._findSvc.options.caseSensitivity = this._findSvc.options.FOC_INSENSITIVE;
    } else if ((type == "find") && (this._searchOptions.indexOf('C') >= 0)) {
        this._findSvc.options.caseSensitivity = this._findSvc.options.FOC_SENSITIVE;

    // else we set it from the current settings then
    } else {
        if (this.settings["smartcase"]) {
            this._findSvc.options.caseSensitivity = this._findSvc.options.FOC_SMART;
        } else if (this.settings["ignorecase"]) {
            this._findSvc.options.caseSensitivity = this._findSvc.options.FOC_INSENSITIVE;
        } else {
            this._findSvc.options.caseSensitivity = this._findSvc.options.FOC_SENSITIVE;
        }
    }
}

VimController._find_msg_callback = function (level, context, msg) {
    switch (level) {
        case "info":
            gVimController.setStatusBarMessage(msg, 5000, true);
            break;
        case "warn":
            gVimController.setStatusBarMessage(msg, 5000, true);
            break;
        case "error":
            gVimController.setStatusBarMessage(msg, 5000, true);
            gVimController._find_error_occurred = true;
            break;
        default:
            vimlog.error("unexpected msg level: "+level);
    }
}

/**
 * Perform a search on the current buffer
 * @param scimoz - Scintilla object
 * @param {string} searchString String to search for.
 * @param {bool} reverseDirection Reverse the current search direction.
 *      Optional. False by default.
 * @param {bool} matchWord Match a whole word. Optional. If not specified,
 *      then the value for the last search is used.
 */
VimController.prototype.performSearch = function (scimoz, searchString,
                                                  reverseDirection /* =false */,
                                                  matchWord /* =<last> */) {
    if (typeof reverseDirection == "undefined" || reverseDirection == null) reverseDirection = false;
    if (typeof matchWord == "undefined" || matchWord == null) {
        matchWord = this._lastSearchMatchWord;
    }
    this._lastSearchMatchWord = matchWord;
    
    try {
        // Vi starts searching from the position after the cursor/currentPos, so
        // remember currentPos then move past the current position.
        var orig_currentPos = scimoz.currentPos;
        var orig_firstVisibleLine = scimoz.firstVisibleLine;
        var orig_xOffset = scimoz.xOffset;
        var searchDirection = this._searchDirection;
        if (reverseDirection) {
            searchDirection = Number(!searchDirection);
        }
        if (searchDirection == VimController.SEARCH_FORWARD) {
            scimoz.currentPos = scimoz.positionAfter(orig_currentPos);
        } else {
            scimoz.currentPos = scimoz.positionBefore(orig_currentPos);
        }

        if (!searchString) {
            // Search again using the last know search text
            searchString = ko.mru.get("find-patternMru");
        }

        //dump("searchString: '"+searchString+"'\n");
        if (!searchString) {
            this.setStatusBarMessage("No search string has been set",
                                     5000, true);
            // Didn't find anything, ensure we move back to the start position
            scimoz.currentPos = orig_currentPos;
            return;
        }

        this._saveFindSvcOptions();
        try {
            this._findSvc.options.searchBackward = (searchDirection == VimController.SEARCH_BACKWARD);
            this._findSvc.options.matchWord = matchWord;
            this._findSvc.options.preferredContextType = this._findSvc.options.FCT_CURRENT_DOC;
            var searchContext = Components.classes["@activestate.com/koFindContext;1"]
                    .createInstance(Components.interfaces.koIFindContext);
            searchContext.type = this._findSvc.options.FCT_CURRENT_DOC;
            this._setFindSvcContext("find");
            var repeatSearchCount = Math.max(1, this.repeatCount);
            vimlog.debug("Repeating search: " + repeatSearchCount + " times");
            var msg = null;
            // Track how many times the search has looped around the document.
            var loopcount = 0;
            var loop_trackingPos = orig_currentPos;
            var searchString_byteLength = ko.stringutils.bytelength(searchString);
            // No errors yet.
            this._find_error_occurred = false;

            // Vi searches can have a repitition count.
            for (var count=0; count < repeatSearchCount; count++) {
                var findres = ko.find.findNext(window,
                                            searchContext,
                                            searchString,
                                            null,  // mode
                                            false, // quiet
                                            true,  // add pattern to find MRU
                                            VimController._find_msg_callback);
                if (this._find_error_occurred) {
                    // Do nothing, the error has already been displayed.
                    scimoz.currentPos = orig_currentPos;
                    return;
                } else if (findres == false) {
                    msg = "No occurrences of '" + searchString + "' were found";
                    // Didn't find anything, ensure we move back to the start position
                    scimoz.currentPos = orig_currentPos;
                    // Bug 99018: If the original caret was in the caret slop,
                    // make sure it's still there
                    scimoz.firstVisibleLine = orig_firstVisibleLine;
                    scimoz.xOffset = orig_xOffset;
                    break;
                } else {
                    // The search engine highlights the selection, we don't want this:
                    //   http://bugs.activestate.com/show_bug.cgi?id=65586
                    var new_currentPos = scimoz.anchor;
                    if ((count+1) < repeatSearchCount) {
                        // The next search must continue from after the found text.
                        scimoz.currentPos = new_currentPos + searchString_byteLength;
                    } else {
                        scimoz.currentPos = new_currentPos;
                    }

                    // Check if we've looped around the document.
                    if ((searchDirection == VimController.SEARCH_FORWARD) &&
                        (new_currentPos < loop_trackingPos)) {
                        loopcount++;
                        if (loopcount > 1) {
                            break;
                        }
                        msg += " (search hit BOTTOM, continuing at TOP)";
                    } else if ((searchDirection == VimController.SEARCH_BACKWARD) &&
                               (new_currentPos > loop_trackingPos)) {
                        loopcount++;
                        if (loopcount > 1) {
                            break;
                        }
                        msg += " (search hit TOP, continuing at BOTTOM)";
                    }
                    loop_trackingPos = new_currentPos;
                }
            }
            if (loopcount > 1) {
                // We've looped twice, cancel the search.
                scimoz.currentPos = orig_currentPos;
                msg = "Operation cancelled: Search looped around twice";
            }
            
            if (msg) this.setStatusBarMessage(msg, 5000, true);
        } finally {
            this._restoreFindSvcOptions();
        }
    } catch (e) {
        vimlog.exception(e);
    }
}

VimController.prototype.performReplace = function (searchString, replaceString,
                                                   startPosition, endPosition,
                                                   options) {
    try {
        vimlog.debug("performReplace:: searchString: '"+searchString+"', "+
                                       "replaceString: '"+replaceString+"', "+
                                       "startPosition: "+startPosition+", "+
                                       "endPosition: "+endPosition+", "+
                                       "options: '"+options+"'");
        //dump("Vi performReplace: " + startPos + "," + endPos + "s/" +
        //     searchString + "/" + replaceString + "/" + options + "\n";
        // Set the context
        var findContext = Components.classes[
            "@activestate.com/koRangeFindContext;1"]
            .createInstance(Components.interfaces.koIRangeFindContext);
        findContext.type = Components.interfaces.koIFindContext.FCT_SELECTION;
        // Work out the real scintilla buffer positions
        var scimoz = ko.views.manager.currentView.scimoz;
        findContext.startIndex = startPosition;
        findContext.endIndex = endPosition;

        this._saveFindSvcOptions();
        try {
            this._findSvc.options.searchBackward = false;
            this._findSvc.options.matchWord = false;
            this._searchOptions = options;
            this._setFindSvcContext("replace");
            // No errors yet.
            this._find_error_occurred = false;


            // 'g' option means "global replace". Without 'g' we only
            // replace the first hit on each line.
            var firstOnLine = options.indexOf('g') == -1;
            var findres = ko.find.findNext(window,
                                        findContext,
                                        searchString,
                                        null,  // mode, defaults to find
                                        false,  // quiet
                                        false,  // add pattern to find MRU
                                        VimController._find_msg_callback);
            if (this._find_error_occurred) {
                // Do nothing, the error has already been displayed.
                return;
            } else if (!findres) {
                this.setStatusBarMessage("'"+searchString+"' was not found in the specified range. No changes were made.",
                                         5000, true);
            } else {
                ko.find.replaceAll(window,           /* editor */
                                findContext,      /* context */
                                searchString,     /* pattern */
                                replaceString,    /* replacement */
                                false,            /* showReplaceResults */
                                firstOnLine);
            }
        } finally {
            this._restoreFindSvcOptions();
        }
    } catch (e) {
        vimlog.exception(e);
    }
}



VimController.vim_set_commands = {
    // Type of boolean means it has a no setting, i.e. noignorecase
    "ignorecase": {
        name: "ignorecase",
        aliases: [ "ic" ],
        type: Boolean,
        defaultValue: false,
        saveAsKomodoPref: true,
        help: "Ignores case for search operations."
    },
    "smartcase": {
        name: "smartcase",
        aliases: [ "scs" ],
        type: Boolean,
        defaultValue: false,
        saveAsKomodoPref: true,
        help: "Override the 'ignorecase' option if the search pattern contains upper case characters."
    },
    "tabstop": {
        name: "tabstop",
        aliases: [ "ts" ],
        type: Number,
        defaultValue: 8,
        setFunction: function(value) {
            ko.views.manager.currentView.koDoc.tabWidth = value;
        },
        saveAsKomodoPref: false,
        help: "The displayed width of tab characters."
    },
    "expandtab": {
        name: "expandtab",
        aliases: [ "et" ],
        type: Boolean,
        defaultValue: true,
        setFunction: function(value) {
            ko.views.manager.currentView.koDoc.useTabs = value;
        },
        saveAsKomodoPref: false,
        help: "Whether to use spaces instead of tab characters for indentation."
    },
    "softtabstop": {
        name: "softtabstop",
        aliases: [ "sts" ],
        type: Number,
        defaultValue: 4,
        setFunction: function(value) {
            ko.views.manager.currentView.koDoc.indentWidth = value;
        },
        saveAsKomodoPref: false,
        help: "Number of spaces used for each indent/dedent."
    },
    "fileformat": {
        name: "fileformat",
        aliases: [ "ff" ],
        type: String,
        possibleValues: [ "unix", "mac", "dos" ],
        defaultValue: "dos",
        setFunction: function(value) {
            ko.views.manager.currentView.koDoc.new_line_endings = this["possibleValues"].indexOf(value);
        },
        saveAsKomodoPref: false,
        help: "Sets the type of <EOL> characters used in the current buffer."
    },
    "whichwrap": {
        name: "whichwrap",
        aliases: [ "ww" ],
        type: String,
        // b Backspace   s Space   < Left arrow   > Right arrow
        defaultValue: "bshl<>",
        saveAsKomodoPref: true,
        help: "Allow specified keys that move the cursor left/right to move to the previous/next line when the cursor is on the first/last character in the line."
    },
    "hlsearch": {
        name: "hlsearch",
        aliases: [ "hls" ],
        type: Boolean,
        defaultValue: true,
        saveAsKomodoPref: true,
        realPrefName: "find-highlightEnabled",
        help: "Highlight search matches."
    }
}


function mapped_command_vim_set(command_details) {
    /*
Some vi settings we should probably support:
  I've marked them as starting with:
    ";" if I've implemented them
    "-" if I've decided low priority or not worth the effort

  - backspace=indent,eol,start    # Influences the working of <BS>, <Del>, CTRL-W and CTRL-U in Insert mode.
  encoding=
  equalprg  # External program to use for "=" command.
  fileencoding=utf-8
; fileformat=unix
  filetype=
  formatprg=
  history=50
; ic  noignorecase  # Ignores case whilst searching
nonumber   # Turn on/off showing of line numbers
noreadonly
  scrolloff=0  # Minimal number of screen lines to keep above and below the cursor.
  - shiftwidth=8  # Number of spaces to use for each step of (auto)indent.
;nosmartcase  # Override the 'ignorecase' option if the search pattern contains upper case characters. Only used when the search pattern is typed and 'ignorecase' option is on.
; sts softtabstop=0  # Number of spaces that a <Tab> counts for while performing editing operations, like inserting a <Tab> or using <BS>.
; ts tabstop=8  # Number of spaces that a <Tab> in the file counts for.
  - textwidth=0
;  ww  whichwrap=b,s   # Allow specified keys that move the cursor left/right to move to the previous/next line when the cursor is on the first/last character in the line.
  wrap  # This option changes how text is displayed.  It doesn't change the text in the buffer, see 'textwidth' for that.

*/

    var count = new Object();
    var args = command_details.getArguments(count, "");
    if (!command_details.leftover || (args[0] == "all")) {
        // Show the current settings, I'd prefer a GUI for this...
        // Is that possible with so many settings??
        // Maybe like the configuration editor in Firefox?
        //show_vi_custom_settings_in_ui();

        // Will use an alert textbox dialog for now...
        var prompt = "Vi settings:";
        var title = "Komodo Vi emulation settings";
        var options = "modal";
        var text = "";
        var settingName;
        var settingDetails;
        var settingValue;
        for (settingName in VimController.vim_set_commands) {
            settingDetails = VimController.vim_set_commands[settingName];
            if (settingName == settingDetails.name) {
                settingValue = gVimController.settings[settingName];
                text += settingName + "=" + settingValue + "\n";
            }
        }

        ko.dialogs.alert(prompt, text, title, null, options);

    } else {
        // Parse out the setting values
        var turnSettingOn = true;  // If a "no" preceeds the setting name
        var settingName = args[0];
        var value = "";
        var split = settingName.split("=", 2);
        if (split.length > 1) {
            settingName = split[0];
            value = split[1];
        }
        if (settingName.substring(0, 2) == "no") {
            turnSettingOn = false;
            settingName = settingName.substring(2);
        }

        // Find the matching setting
        var settingDetails = VimController.vim_set_commands[settingName];
        if (!settingDetails) {
            throw new VimController.ViError("No such setting: " + settingName);
        }

        // It's an alias, change to the correct long format setting name
        settingName = settingDetails.name;

        // Check if set value must be of a specific type
        if (settingDetails.possibleValues) {
            var matchedOkay = false;
            var possibleValue;
            for (var i=0; i < settingDetails.possibleValues.length; i++) {
                possibleValue = settingDetails.possibleValues[i];
                if (value == possibleValue) {
                    matchedOkay = true;
                }
            }
            if (!matchedOkay) {
                throw new VimController.ViError("Setting for " + settingName +
                                    " must be one of " +
                                    settingDetails.possibleValues.join(", "));
            }
        }

        if (settingDetails.type == Boolean) {
            // Allow to be set using true / false expressions
            if (value && turnSettingOn) {
                value = value.toLowerCase();
                if (value == "true" || value == "1" || value == "on") {
                    value = true;
                } else if (value == "false" || value == "0" || value == "off") {
                    value = false;
                }
            } else {
                value = turnSettingOn;
            }
        } else if (!turnSettingOn) {
            throw new VimController.ViError(settingName +
                                            " can not be set using no" +
                                            settingName);
        } else if (settingDetails.type == Number) {
            value = parseInt(value);
        }
        gVimController.settings[settingName] = value;

        // If there is a set function, call it
        if (settingDetails.setFunction) {
            settingDetails.setFunction(value);
        }

        // Show a statusbar message showing we set the value
        gVimController.setStatusBarMessage("Set " + settingName + " to " +
                                           value, 5000, true);

        // If it should be saved as a Komodo pref, then do so
        if (settingDetails.saveAsKomodoPref) {
            // Prefs
            var prefsSvc = Components.classes["@activestate.com/koPrefService;1"].
                                    getService(Components.interfaces.koIPrefService);
            var prefs = prefsSvc.prefs;
            var viPrefs;
            if (prefs.hasPref("viCustomSettings")) {
                viPrefs = prefs.getPref("viCustomSettings");
            } else {
                viPrefs = Components.classes["@activestate.com/koPreferenceSet;1"]
                                .createInstance(Components.interfaces.koIPreferenceSet);
                viPrefs.id = "viCustomSettings";
            }
            if ("realPrefName" in settingDetails) {
                settingName = settingDetails.realPrefName;
                viPrefs = prefs;
            }
            if (settingDetails.type == Number) {
                viPrefs.setLongPref(settingName, value);
            } else if (settingDetails.type == Boolean) {
                viPrefs.setBooleanPref(settingName, value);
            } else if (settingDetails.type == String) {
                viPrefs.setStringPref(settingName, value);
            }
            if (viPrefs != prefs) {
                prefs.setPref("viCustomSettings", viPrefs);
            }
        }
    }
}


function mapped_command_vim_delete(command_details) {
    var scimoz = ko.views.manager.currentView.scimoz;
    if (scimoz.selText) {
        gVimController._mode = VimController.MODE_VISUAL;
        vim_doCommand("cmd_vim_deleteOperation");
    } else {
        vim_doCommand("cmd_vim_lineCut");
    }
}

function mapped_command_vim_edit(command_details) {
    ko.commands.doCommand("cmd_revert");
}

function mapped_command_vim_help(command_details) {
    ko.commands.doCommand("cmd_helpHelp");
}

function mapped_command_vim_next(command_details) {
    ko.commands.doCommand("cmd_bufferNext");
}

function mapped_command_vim_previous(command_details) {
    ko.commands.doCommand("cmd_bufferPrevious");
}

/**
 * Horizontal split view.
 */
function mapped_command_vim_splitview(command_details) {
    ko.commands.doCommand("cmd_splittab");
}

/**
 * Vertical split view.
 */
function mapped_command_vim_vsplitview(command_details) {
    mapped_command_vim_splitview(command_details);
    ko.commands.doCommand("cmd_rotateSplitter");
}

function mapped_command_vim_closeBuffer(command_details) {
    if (ko.views.manager.currentView) {
        var doNotOfferToSave = command_details.forced;
        ko.views.manager.currentView.close(doNotOfferToSave);
    }
}

function mapped_command_vim_undo(command_details) {
    ko.commands.doCommand("cmd_vim_undo");
}


function mapped_command_vim_write(command_details) {
    if (!command_details.leftover) {
        if (command_details.forced) {
            // XXX: TODO: Need a better method than this private one!
            ko.views.manager.currentView._doSave(true);
        } else {
            ko.commands.doCommand("cmd_save");
        }
    } else {
        // Save as
        throw new VimController.NotImplementedException("Write with arguments");
    }
}

function mapped_command_vim_writequit(command_details) {
    mapped_command_vim_write(command_details);
    ko.commands.doCommand("cmd_bufferClose");
}

function mapped_command_vim_copy(command_details) {
    var scimoz = ko.views.manager.currentView.scimoz;
    if (scimoz.selText) {
        gVimController._mode = VimController.MODE_VISUAL;
        vim_doCommand("cmd_vim_yankOperation");
    } else {
        vim_doCommand("cmd_vim_yankLine");
    }
}

VimController.special_command_mappings = {
    "delete"   : mapped_command_vim_delete,
    "edit"     : mapped_command_vim_edit,
    "exit"     : mapped_command_vim_writequit,
    "help"     : mapped_command_vim_help,
    "next"     : mapped_command_vim_next,
    "previous" : mapped_command_vim_previous,
    "quit"     : mapped_command_vim_closeBuffer,
    "set"      : mapped_command_vim_set,
    "splitview": mapped_command_vim_splitview,
    "undo"     : mapped_command_vim_undo,
    "vsplitview": mapped_command_vim_vsplitview,
    "write"    : mapped_command_vim_write,
    "wq"       : mapped_command_vim_writequit,
    "xit"      : mapped_command_vim_writequit,
    "yank"     : mapped_command_vim_copy
};

/**
 * Execute the supplied command details. Will search the special command
 * mapping table for a match first, then checks for a match in the toolbox.
 * An alert is shown if no matched command is found.
 * @param {koICommandDetail} command_details Details of the command to run
 */
VimController.prototype.runCommandDetails = function(command_details) {
    var commandName = command_details.commandName;
    var name = commandName;
    //dump("Commandname: '" + commandName + "'\n");
    // Try exact match first
    var mappedFunction = VimController.special_command_mappings[commandName];
    if (!mappedFunction) {
        // Try an abbreviated command then
        for (name in VimController.special_command_mappings) {
            if ((name.length >= commandName.length) &&
                (name.substr(0, commandName.length) == commandName)) {
                mappedFunction = VimController.special_command_mappings[name];
                break;
            }
        }
    }
    if (mappedFunction) {
        // There is a mapping, perform the actions
        vimlog.debug("Performing command mapping call for '" + name + "'");
        mappedFunction(command_details);
        return;
    }

    // See if there is a VI toolbox element to give it to, so
    // lets go and check the toolbox for this name
    var tool = ko.toolbox2.getViCommand(commandName);
    if (tool) {
        // Invoke the macro
        ko.projects.invokePart(tool);
        return;
    }
    ko.dialogs.alert("Unrecognized command: '" + commandName + "'\n\n" +
                 "You can implement additional commands by creating a toolbox folder\n" +
                 "named 'Vi Commands' and then creating a userscript named '" + commandName + "'.\n" +
                 "This userscript will then be executed in it's place.");
}

// Regex for testing if this is a goto line command.
VimController.prototype.regexIsNumber = new RegExp('^\\d+$');
VimController.prototype.regexWhitespace = new RegExp('\\s+');

// Run command mode ":" string
VimController.prototype.findAndRunCommand = function (value)
{
    if (!value) {
        return;
    }
    // See if it's a number (goto line)
    if (this.regexIsNumber.test(value)) {
        var scimoz = ko.views.manager.currentView.scintilla.scimoz;
        cmd_vim_gotoLine(scimoz, parseInt(value));
        return;
    } else if (value == '$') {
        // Not sure why, but had to use this function directly, maybe
        // something to with focus.
        //ko.commands.doCommand('cmd_documentEnd');
        var scimoz = ko.views.manager.currentView.scintilla.scimoz;
        scimoz.documentEnd();
        return;
    }

    // See if it's !, which means it's a run command
    if (value[0] == '!') {
        value = value.substr(1);
        ko.run.command(value, { "cwd": "%D" });
        return;
    }

    // See if it's a ranged command, begins with "x,y" or "%", where x and y
    // can be one of: number, "$" or "."
    // If it's not ranged, it means target the current line only.
    var scimoz = ko.views.manager.currentView.scintilla.scimoz;
    var currentPos = scimoz.currentPos;
    var anchor = scimoz.anchor;
    // Initially, we only work on the current line
    var lineNo = scimoz.lineFromPosition(currentPos);
    var startPosition = scimoz.positionFromLine(lineNo);
    var endPosition = scimoz.getLineEndPosition(lineNo);

    var rangeRegex = /^((\d+|\$|\.|'[<>]),(\d+|\$|\.|'[<>])|%)/;
    var rangeRegexMatch = value.match(rangeRegex);
    if (rangeRegexMatch) {
        if (rangeRegexMatch[0] == "%") {
            // Everything
            startPosition = 0;
            endPosition   = scimoz.getLineEndPosition(scimoz.lineCount);
        } else {
            var start = rangeRegexMatch[2];
            var end   = rangeRegexMatch[3];
            // $ means end of file
            // . means current line
            // '< means start of selection
            // '> means end of selection
            if (start == '$') {
                startPosition = scimoz.getLineEndPosition(scimoz.lineCount);
            } else if (start == '.') {
                // Nothing to change
            } else if (start == "'<") {
                // Start of the selection
                startPosition = (currentPos < anchor) ? currentPos : anchor;
                if (scimoz.selectionMode == scimoz.SC_SEL_LINES) {
                    var startLineNo = scimoz.lineFromPosition(startPosition);
                    startPosition = scimoz.getLineSelStartPosition(startLineNo);
                }
            } else if (start == "'>") {
                // End of the selection
                startPosition = (currentPos > anchor) ? currentPos : anchor;
                if (scimoz.selectionMode == scimoz.SC_SEL_LINES) {
                    var startLineNo = scimoz.lineFromPosition(startPosition);
                    startPosition = scimoz.getLineSelEndPosition(startLineNo);
                }
            } else {
                /* Should be a number then, convert to scintilla line */
                var lineNo = start - 1;
                if (lineNo >= scimoz.lineCount) {
                    throw new VimController.ViError(
                                "Invalid: range given exceeds document size.");
                }
                startPosition = scimoz.positionFromLine(lineNo);
            }

            if (end == '$') {
                endPosition = scimoz.getLineEndPosition(scimoz.lineCount);
            } else if (end == '.') {
                // Nothing to change
            } else if (end == "'<") {
                // Start of the selection
                endPosition = (currentPos < anchor) ? currentPos : anchor;
                if (scimoz.selectionMode == scimoz.SC_SEL_LINES) {
                    var endLineNo = scimoz.lineFromPosition(endPosition);
                    endPosition = scimoz.getLineSelStartPosition(endLineNo);
                }
            } else if (end == "'>") {
                // End of the selection
                endPosition = (currentPos > anchor) ? currentPos : anchor;
                if (scimoz.selectionMode == scimoz.SC_SEL_LINES) {
                    var endLineNo = scimoz.lineFromPosition(endPosition);
                    endPosition = scimoz.getLineSelEndPosition(endLineNo);
                }
            } else {
                /* Should be a number then, convert to scintilla line */
                var lineNo = end - 1;
                if (lineNo >= scimoz.lineCount) {
                    throw new VimController.ViError(
                                "Invalid: range given exceeds document size.");
                }
                endPosition = scimoz.getLineEndPosition(lineNo);
            }

            // Check positions, ensure the details are valid
            startPosition = Math.max(0, startPosition);
            endPosition = Math.max(0, endPosition);
            endPosition = Math.min(scimoz.getLineEndPosition(scimoz.lineCount),
                                   endPosition);
            if (startPosition > endPosition) {
                // Swap them around then
                // Update to start/end positions as required.
                if (start != "'<" && start != "'>") {
                    // Need to move to the end of the line
                    startPosition = scimoz.getLineEndPosition(
                                scimoz.lineFromPosition(startPosition));
                }
                if (end != "'<" && end != "'>") {
                    // Need to move to the start of the line
                    endPosition = scimoz.positionFromLine(
                                scimoz.lineFromPosition(endPosition));
                }
                var tmp = startPosition;
                startPosition = endPosition;
                endPosition = tmp;
            }
        }
        // We can now remove the range part from the command
        value = value.substr(rangeRegexMatch[0].length);
    }
    //dump("startLine: " + startLine + ", endLine: " + endLine + "\n");

    // See if it's a search and replace command
    var srMatch = true;
    var c; /* current char looking at */
    var buf = ''; /* stored buffer of read in chars */
    var fields = [];
    var state = 0;
    /* state == 0 ; then searching for 's' */
    /* state == 1 ; then getting searchString */
    /* state == 2 ; then getting replaceString */
    /* state == 3 ; then getting options */
    /* state == 4 ; then skipping escaped character */
    /* state > 4  ; then did not match */
    for (var i=0; srMatch && i < value.length; i++) {
        c = value[i];

        // Deal with slash characters
        if (c == '/' && state != 4) {
            state += 1;
            fields.push(buf);
            //dump("Field " + state + " is " + buf + "\n");
            buf = '';
            continue;
        }

        buf += c;
        if (c == '\\' && state != 4) {
            state = 4;
            continue;
        }

        switch (state) {
            case 0:
                if (c != 's')
                    srMatch = false;
                break;
            case 1:
            case 2:
                break;
            case 3:
                // Only accepts 'g', 'i', 'I' here. There are other options
                // in vi though ('r', 'c', 'e', 'p', 'l', '#', 'n' ... ARGH!)
                if (c != 'g' && c != 'i' && c != 'I')
                    srMatch = false;
                break;
            case 4:
                state = fields.length;
                break;
            default:
                srMatch = false;
                break;
        }
    }
    if (srMatch) {
        if (buf.length > 0) {
            fields.push(buf);
        }
        if (fields.length >= 3 && fields.length <= 4) {
            //dump("Valid regex\n");
            //dump("fields (" + fields.length + "): " + fields + "\n");
            var currentPos = scimoz.currentPos;
            var options = '';
            if (fields.length == 4) {
                options = fields[3];
            }
            scimoz.beginUndoAction();
            try {
                this.performReplace(fields[1], fields[2], startPosition,
                                    endPosition, options);
            } catch (ex) {
                vimlog.exception(e);
            }
            scimoz.endUndoAction();
            // Unselect the selection made
            scimoz.setSel(currentPos, currentPos);
            return;
        }
    }

    // No mapping, abbreviation or matched syntax existed!
    var match = value.match(/\w+/g);
    if (match) {
        var commandName = match[0];
        // Initialize the command structure
        this._commandDetails.clear();

        var leftover = value.substring(commandName.length);
        if (leftover) {
            // Check if this is a forced command
            if (leftover[0] == "!") {
                this._commandDetails.forced = true;
                leftover = leftover.substring(1);
            }
            var argsSplit = leftover.split(this.regexWhitespace);
            // Remove any empty first field, it was just whitespace
            if (argsSplit && !argsSplit[0]) {
                var initialWhitespace = argsSplit.splice(0, 1);
                // Remove intial whitespace from leftover
                leftover = leftover.substring(initialWhitespace.length);
            }
            // Remove any empty last field, it was just whitespace
            if (argsSplit && !argsSplit[argsSplit.length - 1]) {
                argsSplit.splice(argsSplit.length - 1, 1);
            }
            // Update some command details here
            this._commandDetails.leftover = leftover;
            if (argsSplit) {
                this._commandDetails.setArguments(argsSplit.length, argsSplit);
            }
        }

        // Command details - update the rest
        this._commandDetails.startLine = scimoz.lineFromPosition(startPosition);
        this._commandDetails.endLine = scimoz.lineFromPosition(endPosition);
        this._commandDetails.commandName = commandName;
        this._commandDetails.rawCommandString = value;

        // Run the command
        this.runCommandDetails(this._commandDetails);

    } else {
        ko.dialogs.alert("Unrecognized command: '" + value + "'\n\n" +
                     "Commands need a word as the first argument\n");
    }
}




// Map vim commands to Komodo (scintilla) commands.
// These commands are a 1 to 1 mapping from vim to komodo (they don't do any
// thing special). We don't use a direct mapping from the key-bindings file as
// we want to be able to record all vim events. This mapping pass-through gives
// us the ability to run the commands as well as record what happened and thus
// enable special vim commands such as the repeat command.
VimController.command_mappings = {
// Movement actions
    "cmd_vim_left" :                [ VimController.SPECIAL_COMMAND,VimController.REPEATABLE_ACTION | VimController.MOVEMENT_ACTION | VimController.CHOOSE_CARET_X ],
    "cmd_vim_right" :               [ VimController.SPECIAL_COMMAND,VimController.REPEATABLE_ACTION | VimController.MOVEMENT_ACTION | VimController.CHOOSE_CARET_X ],
    "cmd_vim_linePrevious" :        [ VimController.SPECIAL_COMMAND,VimController.REPEATABLE_ACTION | VimController.MOVEMENT_ACTION ],
    "cmd_vim_lineNext" :            [ VimController.SPECIAL_COMMAND,VimController.REPEATABLE_ACTION | VimController.MOVEMENT_ACTION ],
    "cmd_vim_linePreviousHome" :    [ "cmd_linePreviousHome",       VimController.REPEATABLE_ACTION | VimController.MOVEMENT_ACTION ],
    "cmd_vim_lineNextHome" :        [ "cmd_lineNextHome",           VimController.REPEATABLE_ACTION | VimController.MOVEMENT_ACTION ],
    "cmd_vim_home" :                [ VimController.SPECIAL_COMMAND,VimController.NO_REPEAT_ACTION | VimController.MOVEMENT_ACTION ],
    "cmd_vim_homeAbsolute" :        [ VimController.SPECIAL_COMMAND,VimController.NO_REPEAT_ACTION | VimController.MOVEMENT_ACTION ],
    "cmd_vim_end"  :                [ VimController.SPECIAL_COMMAND,VimController.NO_REPEAT_ACTION | VimController.MOVEMENT_ACTION ],
    "cmd_vim_scrollHalfPageDown" :  [ VimController.SPECIAL_COMMAND,VimController.REPEATABLE_ACTION | VimController.MOVEMENT_ACTION ],
    "cmd_vim_scrollHalfPageUp" :    [ VimController.SPECIAL_COMMAND,VimController.REPEATABLE_ACTION | VimController.MOVEMENT_ACTION ],
    "cmd_vim_pageDown" :            [ "cmd_pageDown",               VimController.REPEATABLE_ACTION | VimController.MOVEMENT_ACTION ],
    "cmd_vim_pageUp" :              [ "cmd_pageUp",                 VimController.REPEATABLE_ACTION | VimController.MOVEMENT_ACTION ],
    "cmd_vim_wordLeft" :            [ "cmd_wordLeft",               VimController.REPEATABLE_ACTION | VimController.MOVEMENT_ACTION ],
    "cmd_vim_wordLeftEnd" :         [ "cmd_wordLeftEnd",            VimController.REPEATABLE_ACTION | VimController.MOVEMENT_ACTION ],
    "cmd_vim_wordRight" :           [ "cmd_wordRight",              VimController.REPEATABLE_ACTION | VimController.MOVEMENT_ACTION ],
    "cmd_vim_wordRightEnd" :        [ VimController.SPECIAL_COMMAND,VimController.REPEATABLE_ACTION | VimController.MOVEMENT_ACTION ],
    "cmd_vim_documentHome" :        [ "cmd_documentHome",           VimController.NO_REPEAT_ACTION | VimController.MOVEMENT_ACTION ],
    "cmd_vim_documentEnd" :         [ "cmd_documentEnd",            VimController.NO_REPEAT_ACTION | VimController.MOVEMENT_ACTION ],
    "cmd_vim_gotoLine" :            [ VimController.SPECIAL_COMMAND,VimController.NO_REPEAT_ACTION | VimController.MOVEMENT_ACTION ],
    "cmd_vim_lineScrollUp" :        [ "cmd_lineScrollUp",           VimController.REPEATABLE_ACTION | VimController.MOVEMENT_ACTION ],
    "cmd_vim_lineScrollDown" :      [ "cmd_lineScrollDown",         VimController.REPEATABLE_ACTION | VimController.MOVEMENT_ACTION ],
    "cmd_vim_jumpToMatchingBrace" : [ VimController.SPECIAL_COMMAND,VimController.NO_REPEAT_ACTION | VimController.MOVEMENT_ACTION ],
    "cmd_vim_wordLeftPastPunctuation" : [ "cmd_wordLeftPastPunctuation", VimController.REPEATABLE_ACTION | VimController.MOVEMENT_ACTION ],
    "cmd_vim_wordRightPastPunctuation" : [ "cmd_wordRightPastPunctuation", VimController.REPEATABLE_ACTION | VimController.MOVEMENT_ACTION ],
    "cmd_vim_wordRightEndPastPunctuation" : [ VimController.SPECIAL_COMMAND, VimController.REPEATABLE_ACTION | VimController.MOVEMENT_ACTION ],
    "cmd_vim_moveToScreenTop" :     [ "cmd_moveToScreenTop",        VimController.NO_REPEAT_ACTION | VimController.MOVEMENT_ACTION ],
    "cmd_vim_moveToScreenCenter" :  [ "cmd_moveToScreenCenter",     VimController.NO_REPEAT_ACTION | VimController.MOVEMENT_ACTION ],
    "cmd_vim_moveToScreenBottom" :  [ "cmd_moveToScreenBottom",     VimController.NO_REPEAT_ACTION | VimController.MOVEMENT_ACTION ],
    "cmd_vim_moveSentenceBegin" :   [ "cmd_moveSentenceBegin",      VimController.REPEATABLE_ACTION | VimController.MOVEMENT_ACTION ],
    "cmd_vim_moveSentenceEnd" :     [ "cmd_moveSentenceEnd",        VimController.REPEATABLE_ACTION | VimController.MOVEMENT_ACTION ],
    "cmd_vim_moveParagraphBegin" :  [ "cmd_moveParagraphBegin",     VimController.REPEATABLE_ACTION | VimController.MOVEMENT_ACTION ],
    "cmd_vim_moveParagraphEnd" :    [ "cmd_moveParagraphEnd",       VimController.REPEATABLE_ACTION | VimController.MOVEMENT_ACTION ],
    "cmd_vim_moveFunctionPrevious" :[ "cmd_moveFunctionPrevious",   VimController.REPEATABLE_ACTION | VimController.MOVEMENT_ACTION ],
    "cmd_vim_moveFunctionNext" :    [ "cmd_moveFunctionNext",       VimController.REPEATABLE_ACTION | VimController.MOVEMENT_ACTION ],
    "cmd_vim_jumpToLineBeforeLastJump" :    [ VimController.SPECIAL_COMMAND, VimController.MOVEMENT_ACTION | VimController.NO_REPEAT_ACTION],
    "cmd_vim_jumpToLocBeforeLastJump" :    [ VimController.SPECIAL_COMMAND, VimController.MOVEMENT_ACTION | VimController.NO_REPEAT_ACTION],
    "cmd_vim_scrollLineToCenter" :  [ "cmd_editCenterVertically",   VimController.NO_REPEAT_ACTION ],
    "cmd_vim_scrollLineToCenterHome" : [ VimController.SPECIAL_COMMAND, VimController.NO_REPEAT_ACTION | VimController.MOVEMENT_ACTION ],
    "cmd_vim_scrollLineToBottomHome" : [ VimController.SPECIAL_COMMAND, VimController.NO_REPEAT_ACTION | VimController.MOVEMENT_ACTION ],

// Select actions
    "cmd_vim_selectCharNext" :      [ "cmd_selectCharNext",         VimController.REPEATABLE_ACTION ],
    "cmd_vim_selectCharPrevious" :  [ "cmd_selectCharPrevious",     VimController.REPEATABLE_ACTION ],
    "cmd_vim_selectWordLeft" :      [ "cmd_selectWordLeft",         VimController.REPEATABLE_ACTION ],
    "cmd_vim_selectWordRight" :     [ "cmd_selectWordRight",        VimController.REPEATABLE_ACTION ],
    "cmd_vim_selectHome" :          [ "cmd_selectHome",             VimController.NO_REPEAT_ACTION ],
    "cmd_vim_selectEnd" :           [ "cmd_selectEnd",              VimController.REPEATABLE_ACTION ],
    "cmd_vim_selectLineNext" :      [ VimController.SPECIAL_COMMAND,VimController.REPEATABLE_ACTION ],
    "cmd_vim_selectLinePrevious" :  [ VimController.SPECIAL_COMMAND,VimController.REPEATABLE_ACTION ],
    "cmd_vim_selectPageDown" :      [ "cmd_selectPageDown",         VimController.REPEATABLE_ACTION ],
    "cmd_vim_selectPageUp" :        [ "cmd_selectPageUp",           VimController.REPEATABLE_ACTION ],
    "cmd_vim_selectDocumentHome" :  [ "cmd_selectDocumentHome",     VimController.NO_REPEAT_ACTION ],
    "cmd_vim_selectDocumentEnd" :   [ "cmd_selectDocumentEnd",      VimController.NO_REPEAT_ACTION ],
    "cmd_vim_editSelectAll" :       [ "cmd_selectAll",              VimController.NO_REPEAT_ACTION ],
// Insert actions
    "cmd_vim_insert" :              [ VimController.SPECIAL_COMMAND,VimController.REPEATABLE_ACTION |
                                                                    VimController.ENTER_MODE_INSERT |
                                                                    VimController.MODIFY_ACTION |
                                                                    VimController.WORKS_IN_VISUAL_MODE |
                                                                    VimController.CANCELS_VISUAL_MODE ],
    "cmd_vim_insertHome" :          [ "cmd_home",                   VimController.REPEATABLE_ACTION |
                                                                    VimController.ENTER_MODE_INSERT |
                                                                    VimController.MODIFY_ACTION |
                                                                    VimController.WORKS_IN_VISUAL_MODE |
                                                                    VimController.CANCELS_VISUAL_MODE ],
    // XXX - Will not work on line 0, as we cannot do a linePrevious
    "cmd_vim_insert_newline_previous" : [ "cmd_newlinePrevious",    VimController.REPEATABLE_ACTION |
                                                                    VimController.ENTER_MODE_INSERT |
                                                                    VimController.MODIFY_ACTION ],
    "cmd_vim_insert_newline_next" : [ VimController.SPECIAL_COMMAND,VimController.REPEATABLE_ACTION |
                                                                    VimController.ENTER_MODE_INSERT |
                                                                    VimController.MODIFY_ACTION ],
    "cmd_vim_append" :              [ VimController.SPECIAL_COMMAND,VimController.REPEATABLE_ACTION |
                                                                    VimController.ENTER_MODE_INSERT |
                                                                    VimController.MODIFY_ACTION ],
    "cmd_vim_appendEnd" :           [ "cmd_end",                    VimController.REPEATABLE_ACTION |
                                                                    VimController.ENTER_MODE_INSERT |
                                                                    VimController.MODIFY_ACTION ],
    "cmd_vim_changeChar" :          [ VimController.SPECIAL_COMMAND,VimController.REPEATABLE_ACTION |
                                                                    VimController.ENTER_MODE_INSERT |
                                                                    VimController.MODIFY_ACTION |
                                                                    VimController.SPECIAL_REPEAT_HANDLING |
                                                                    VimController.WORKS_IN_VISUAL_MODE |
                                                                    VimController.CANCELS_VISUAL_MODE ],
    "cmd_vim_changeWord" :          [ VimController.SPECIAL_COMMAND,VimController.REPEATABLE_ACTION |
                                                                    VimController.ENTER_MODE_INSERT |
                                                                    VimController.MODIFY_ACTION |
                                                                    VimController.SPECIAL_REPEAT_HANDLING ],
    "cmd_vim_changeLine" :          [ VimController.SPECIAL_COMMAND,VimController.REPEATABLE_ACTION |
                                                                    VimController.ENTER_MODE_INSERT |
                                                                    VimController.MODIFY_ACTION |
                                                                    VimController.SPECIAL_REPEAT_HANDLING ],
    "cmd_vim_changeLineEnd" :       [ VimController.SPECIAL_COMMAND,VimController.NO_REPEAT_ACTION |
                                                                    VimController.ENTER_MODE_INSERT |
                                                                    VimController.MODIFY_ACTION |
                                                                    VimController.WORKS_IN_VISUAL_MODE |
                                                                    VimController.CANCELS_VISUAL_MODE ],
// Cut/copy/delete actions
    "cmd_vim_yankLine" :            [ VimController.SPECIAL_COMMAND,VimController.REPEATABLE_ACTION |
                                                                    VimController.COPY_LINES |
                                                                    VimController.SPECIAL_REPEAT_HANDLING ],
    // Paste actions are special because of the way vim uses yanked lines
    "cmd_vim_paste" :               [ VimController.SPECIAL_COMMAND,VimController.REPEATABLE_ACTION |
                                                                    VimController.MODIFY_ACTION |
                                                                    VimController.WORKS_IN_VISUAL_MODE |
                                                                    VimController.CANCELS_VISUAL_MODE |
                                                                    VimController.SPECIAL_REPEAT_HANDLING ],
    "cmd_vim_pasteAfter" :          [ VimController.SPECIAL_COMMAND,VimController.REPEATABLE_ACTION |
                                                                    VimController.MODIFY_ACTION |
                                                                    VimController.WORKS_IN_VISUAL_MODE |
                                                                    VimController.CANCELS_VISUAL_MODE |
                                                                    VimController.SPECIAL_REPEAT_HANDLING ],
    "cmd_vim_lineCut" :             [ VimController.SPECIAL_COMMAND,VimController.REPEATABLE_ACTION |
                                                                    VimController.MODIFY_ACTION |
                                                                    VimController.COPY_LINES |
                                                                    VimController.SPECIAL_REPEAT_HANDLING |
                                                                    VimController.WORKS_IN_VISUAL_MODE |
                                                                    VimController.CANCELS_VISUAL_MODE ],
    // Same "cmd_vim_deleteLineToEnd" :     [ "cmd_deleteLineToEnd",                   VimController.REPEATABLE_ACTION ],
    "cmd_vim_lineCutEnd" :          [ VimController.SPECIAL_COMMAND,VimController.REPEATABLE_ACTION |
                                                                    VimController.MODIFY_ACTION |
                                                                    VimController.COPY_NORMAL |
                                                                    VimController.WORKS_IN_VISUAL_MODE |
                                                                    VimController.CANCELS_VISUAL_MODE ],
    "cmd_vim_cutChar" :             [ VimController.SPECIAL_COMMAND,VimController.REPEATABLE_ACTION |
                                                                    VimController.MODIFY_ACTION |
                                                                    VimController.COPY_NORMAL |
                                                                    VimController.SPECIAL_REPEAT_HANDLING |
                                                                    VimController.WORKS_IN_VISUAL_MODE |
                                                                    VimController.CANCELS_VISUAL_MODE ],
    "cmd_vim_cutCharLeft" :         [ VimController.SPECIAL_COMMAND,VimController.REPEATABLE_ACTION ],
    "cmd_vim_yankOperation": [ VimController.SPECIAL_COMMAND,       VimController.NO_REPEAT_ACTION |
                                                                    VimController.COPY_NORMAL |
                                                                    VimController.WORKS_IN_VISUAL_MODE |
                                                                    VimController.CANCELS_VISUAL_MODE ],
    "cmd_vim_deleteOperation": [ VimController.SPECIAL_COMMAND,     VimController.NO_REPEAT_ACTION |
                                                                    VimController.COPY_NORMAL |
                                                                    VimController.WORKS_IN_VISUAL_MODE |
                                                                    VimController.CANCELS_VISUAL_MODE ],
    "cmd_vim_changeOperation": [ VimController.SPECIAL_COMMAND,     VimController.NO_REPEAT_ACTION |
                                                                    VimController.COPY_NORMAL |
                                                                    VimController.WORKS_IN_VISUAL_MODE |
                                                                    VimController.CANCELS_VISUAL_MODE ],
    "cmd_vim_indentOperation": [ VimController.SPECIAL_COMMAND,     VimController.NO_REPEAT_ACTION |
                                                                    VimController.WORKS_IN_VISUAL_MODE |
                                                                    VimController.SPECIAL_REPEAT_HANDLING |
                                                                    VimController.CANCELS_VISUAL_MODE ],
    "cmd_vim_dedentOperation": [ VimController.SPECIAL_COMMAND,     VimController.NO_REPEAT_ACTION |
                                                                    VimController.WORKS_IN_VISUAL_MODE |
                                                                    VimController.SPECIAL_REPEAT_HANDLING |
                                                                    VimController.CANCELS_VISUAL_MODE ],
// Search actions
    "cmd_startIncrementalSearch" :  [ "cmd_startIncrementalSearch", VimController.NO_REPEAT_ACTION ],
    "cmd_vim_findNext" :            [ VimController.SPECIAL_COMMAND,VimController.NO_REPEAT_ACTION | VimController.MOVEMENT_ACTION ],
    "cmd_vim_findPrevious" :        [ VimController.SPECIAL_COMMAND,VimController.NO_REPEAT_ACTION | VimController.MOVEMENT_ACTION ],
    "cmd_vim_findNextResult" :      [ "cmd_findNextResult",         VimController.NO_REPEAT_ACTION | VimController.MOVEMENT_ACTION ],
    "cmd_vim_findCharInLine" :      [ VimController.SPECIAL_COMMAND,VimController.NO_REPEAT_ACTION | VimController.MOVEMENT_ACTION | VimController.DELAY_MODE_INSERT ],
    "cmd_vim_findPreviousCharInLine":[VimController.SPECIAL_COMMAND,VimController.NO_REPEAT_ACTION | VimController.MOVEMENT_ACTION | VimController.DELAY_MODE_INSERT ],
    "cmd_vim_findCharInLinePosBefore" : [ VimController.SPECIAL_COMMAND,VimController.NO_REPEAT_ACTION | VimController.MOVEMENT_ACTION | VimController.DELAY_MODE_INSERT ],
    "cmd_vim_findPreviousCharInLinePosAfter": [ VimController.SPECIAL_COMMAND,VimController.NO_REPEAT_ACTION | VimController.MOVEMENT_ACTION | VimController.DELAY_MODE_INSERT ],
    "cmd_vim_repeatLastFindCharInLine" :            [ VimController.SPECIAL_COMMAND,VimController.REPEATABLE_ACTION | VimController.MOVEMENT_ACTION | VimController.SPECIAL_REPEAT_HANDLING ],
    "cmd_vim_repeatLastFindCharInLineReversed" :    [ VimController.SPECIAL_COMMAND,VimController.REPEATABLE_ACTION | VimController.MOVEMENT_ACTION | VimController.SPECIAL_REPEAT_HANDLING ],
    "cmd_vim_findWordUnderCursor" : [ VimController.SPECIAL_COMMAND,VimController.NO_REPEAT_ACTION | VimController.MOVEMENT_ACTION ],
    "cmd_vim_findWordUnderCursorBack" : [ VimController.SPECIAL_COMMAND,VimController.NO_REPEAT_ACTION | VimController.MOVEMENT_ACTION ],
// Visual mode commands
    "cmd_vim_toggleVisualMode" :    [ VimController.SPECIAL_COMMAND,VimController.NO_REPEAT_ACTION | VimController.WORKS_IN_VISUAL_MODE ],
    "cmd_vim_toggleVisualLineMode" :[ VimController.SPECIAL_COMMAND,VimController.NO_REPEAT_ACTION | VimController.WORKS_IN_VISUAL_MODE ],
    "cmd_vim_toggleVisualBlockMode" : [ VimController.SPECIAL_COMMAND,VimController.NO_REPEAT_ACTION | VimController.WORKS_IN_VISUAL_MODE ],
// Special actions
    "cmd_vim_replaceChar" :         [ VimController.SPECIAL_COMMAND,VimController.WORKS_IN_VISUAL_MODE |
                                                                    VimController.CANCELS_VISUAL_MODE ],
    "cmd_vim_doReplaceChar" :       [ VimController.SPECIAL_COMMAND,VimController.REPEATABLE_ACTION |
                                                                    VimController.MODIFY_ACTION |
                                                                    VimController.WORKS_IN_VISUAL_MODE |
                                                                    VimController.CANCELS_VISUAL_MODE |
                                                                    VimController.SPECIAL_REPEAT_HANDLING ],
    "cmd_vim_overtype" :            [ VimController.SPECIAL_COMMAND,VimController.NO_REPEAT_ACTION ],
    "cmd_vim_swapCase" :            [ "cmd_swapCase",               VimController.REPEATABLE_ACTION | VimController.MODIFY_ACTION |
                                                                    VimController.WORKS_IN_VISUAL_MODE |
                                                                    VimController.CANCELS_VISUAL_MODE ],
    "cmd_vim_join" :                [ "cmd_join",                   VimController.REPEATABLE_ACTION | VimController.MODIFY_ACTION |
                                                                    VimController.WORKS_IN_VISUAL_MODE |
                                                                    VimController.CANCELS_VISUAL_MODE ],
    "cmd_vim_undo" :                [ "cmd_undo",                   VimController.NO_REPEAT_ACTION |
                                                                    VimController.CHOOSE_CARET_X ],
    "cmd_vim_redo" :                [ "cmd_redo",                   VimController.NO_REPEAT_ACTION |
                                                                    VimController.CHOOSE_CARET_X ],
    "cmd_vim_cancel" :              [ VimController.SPECIAL_COMMAND,VimController.NO_REPEAT_ACTION |
                                                                    VimController.WORKS_IN_VISUAL_MODE |
                                                                    VimController.CANCELS_VISUAL_MODE |
                                                                    VimController.CHOOSE_CARET_X ],
    "cmd_vim_repeatLastCommand" :   [ VimController.SPECIAL_COMMAND,VimController.REPEATABLE_ACTION |
                                                                    VimController.CHOOSE_CARET_X ],
    "cmd_vim_enterCommandMode" :    [ VimController.SPECIAL_COMMAND,VimController.NO_REPEAT_ACTION |
                                                                    VimController.WORKS_IN_VISUAL_MODE ],
    "cmd_vim_indent" :              [ VimController.SPECIAL_COMMAND,VimController.REPEATABLE_ACTION | VimController.MODIFY_ACTION |
                                                                    VimController.WORKS_IN_VISUAL_MODE |
                                                                    VimController.SPECIAL_REPEAT_HANDLING |
                                                                    VimController.CANCELS_VISUAL_MODE ],
    "cmd_vim_dedent" :              [ VimController.SPECIAL_COMMAND,VimController.REPEATABLE_ACTION | VimController.MODIFY_ACTION |
                                                                    VimController.WORKS_IN_VISUAL_MODE |
                                                                    VimController.SPECIAL_REPEAT_HANDLING |
                                                                    VimController.CANCELS_VISUAL_MODE ],
    "cmd_vim_indent_visual" :       [ VimController.SPECIAL_COMMAND,VimController.REPEATABLE_ACTION | VimController.MODIFY_ACTION |
                                                                    VimController.WORKS_IN_VISUAL_MODE |
                                                                    VimController.SPECIAL_REPEAT_HANDLING |
                                                                    VimController.CANCELS_VISUAL_MODE ],
    "cmd_vim_dedent_visual" :       [ VimController.SPECIAL_COMMAND,VimController.REPEATABLE_ACTION | VimController.MODIFY_ACTION |
                                                                    VimController.WORKS_IN_VISUAL_MODE |
                                                                    VimController.SPECIAL_REPEAT_HANDLING |
                                                                    VimController.CANCELS_VISUAL_MODE ],
    "cmd_vim_enterSearchForward" :  [ VimController.SPECIAL_COMMAND,VimController.NO_REPEAT_ACTION |
                                                                    VimController.MOVEMENT_ACTION |
                                                                    VimController.NO_OP_FLAG_CHANGE |
                                                                    VimController.WORKS_IN_VISUAL_MODE |
                                                                    VimController.DELAY_MODE_INSERT ],
    "cmd_vim_enterSearchBackward" : [ VimController.SPECIAL_COMMAND,VimController.NO_REPEAT_ACTION |
                                                                    VimController.MOVEMENT_ACTION |
                                                                    VimController.NO_OP_FLAG_CHANGE |
                                                                    VimController.WORKS_IN_VISUAL_MODE |
                                                                    VimController.DELAY_MODE_INSERT ],
    "cmd_vim_setRegister" :         [ VimController.SPECIAL_COMMAND,VimController.NO_REPEAT_ACTION |
                                                                    VimController.WORKS_IN_VISUAL_MODE ],
    "cmd_vim_saveAndClose" :        [ VimController.SPECIAL_COMMAND,VimController.NO_REPEAT_ACTION ],
    "cmd_vim_closeNoSave" :         [ VimController.SPECIAL_COMMAND,VimController.NO_REPEAT_ACTION ],
    "" :                            [ "",                           VimController.NO_REPEAT_ACTION ]
};

// Special operation commands, used in conjunction with a movement command, or
// if repeated twice (like "d d") then performs the associated action below.
VimController.operation_commands = {
    "cmd_vim_yankOperation":   [ "cmd_vim_yankLine",   VimController.OPERATION_YANK ],
    "cmd_vim_deleteOperation": [ "cmd_vim_lineCut",    VimController.OPERATION_DELETE ],
    "cmd_vim_changeOperation": [ "cmd_vim_changeLine", VimController.OPERATION_CHANGE ],
    "cmd_vim_indentOperation": [ "cmd_vim_indent",     VimController.OPERATION_INDENT ],
    "cmd_vim_dedentOperation": [ "cmd_vim_dedent",     VimController.OPERATION_DEDENT ]
}

// Visual mode commands that are different to normal mode commands.
VimController.visualmode_command_mappings = {
    "cmd_vim_cutChar":          "cmd_vim_deleteOperation",
    "cmd_vim_changeChar":       "cmd_vim_insert",
    // Left and right are handled locally as they act differently
    //"cmd_vim_left":             "cmd_vim_selectCharPrevious",
    //"cmd_vim_right":            "cmd_vim_selectCharNext",
    "cmd_vim_wordLeft" :        "cmd_vim_selectWordLeft",
    "cmd_vim_wordRight" :       "cmd_vim_selectWordRight",
    "cmd_vim_home" :            "cmd_vim_selectHome",
    // XXX - Implement 'cmd_vim_selectHomeAbsolute'
    //"cmd_vim_homeAbsolute" :    "cmd_vim_selectHomeAbsolute",
    "cmd_vim_end" :             "cmd_vim_selectEnd",
    "cmd_vim_lineNext" :        "cmd_vim_selectLineNext",
    "cmd_vim_linePrevious" :    "cmd_vim_selectLinePrevious",
    "cmd_vim_pageDown" :        "cmd_vim_selectPageDown",
    "cmd_vim_pageUp" :          "cmd_vim_selectPageUp",
    //"cmd_vim_documentHome" :    "cmd_vim_selectDocumentHome",
    "cmd_vim_documentEnd" :     "cmd_vim_selectDocumentEnd",
    "cmd_vim_indentOperation" : "cmd_vim_indent_visual",
    "cmd_vim_dedentOperation" : "cmd_vim_dedent_visual",
    // In visual mode, a pasteAfter "p" command works the same as paste "P".
    "cmd_vim_pasteAfter"      : "cmd_vim_paste",
    "": ""
}

// Execute a vim command.
function vim_doCommand(command, event)
{
    if (event) {
        // The command was called directly from the vim commandset handler.
        // Ensure to only process vi commands when focused on a Scintilla view.
        let view = event.target;
        if (view.nodeName != 'view') {
            vimlog.debug("Skipping " + command + " event from " + view.nodeName);
            return false;
        }
        try {
            while (view.currentView) {
                view = view.currentView;
            }
        } catch (ex) {
            // Some views don't implement .currentView, that's okay
        }
        if (!view.scintilla || !view.scintilla.isFocused) {
            return false;
        }
    }
    vimlog.debug("vim_doCommand(" + command + ")");
    if (!ko.views.manager.currentView) {
        vimlog.debug("vim_doCommand:: not initialized yet");
        return false;
    }
    if (!ko.views.manager.currentView.scintilla) {
        // Not a Scintilla view - we don't handle the command.
        return false;
    }

    vimlog.debug("currentRegister: " + gVimController._currentRegister);
    var rc = false;
    var original_command = command;
    try {
        var numRepeats = 1;

        // Must have a 1-to-1 mapping in the dict to be a komodo vi command.
        var mappedCommand = VimController.command_mappings[command];
        if (!(mappedCommand)) {
            // No mapping existed
            vimlog.error("vim_doCommand:: Unknown vim command: '" + command + "'");
            gVimController.resetCommandSettings();
            return false;
        }

        var movementAction = mappedCommand[1] & VimController.MOVEMENT_ACTION;
        var scimoz = ko.views.manager.currentView.scintilla.scimoz;
        // Record current position and selection (anchor is used for selection)
        var orig_currentPos = scimoz.currentPos;
        var orig_anchor = scimoz.anchor;
        gVimController._currentPos = orig_currentPos
        gVimController._anchor = orig_anchor;

        // Visual mode checks
        if (gVimController.mode == VimController.MODE_VISUAL) {
            // If in visual mode, the only things we want to see are movements
            // or special visual mode commands
            if (!movementAction &&
                !(mappedCommand[1] & VimController.WORKS_IN_VISUAL_MODE)) {
                vimlog.debug("vim_doCommand:: visual mode:: command not recogized: " + command);
                gVimController.setStatusBarMessage("Not a recognized visual mode command",
                                                   5000, true);
                gVimController.resetCommandSettings();
                // Reset the repeat count back to 0 now
                gVimController.repeatCount = 0;
                return false;
            }

            // See if we need to change how the command works
            if (command in VimController.visualmode_command_mappings) {
                command = VimController.visualmode_command_mappings[command];
                vimlog.debug("vim_doCommand:: visual mode:: command mapped to: " + command);
                mappedCommand = VimController.command_mappings[command];
                movementAction = mappedCommand[1] & VimController.MOVEMENT_ACTION;
            }
        }

        if (command == "cmd_vim_cancel") {
            gVimController.operationFlags = VimController.OPERATION_NONE;
            gVimController.repeatCount = 0;
        }

        // See if this is a operation that requires a movement command
        //   "d G", "c w", etc...
        var opMovementAction = false;
        vimlog.debug("vim_doCommand:: operationFlags: "+gVimController.operationFlags);
        if (gVimController.operationFlags) {
            // Check if the same command is repeated, then it's a special case
            if ((command in VimController.operation_commands) &&
                (gVimController.operationFlags == VimController.operation_commands[command][1])) {
                command = VimController.operation_commands[command][0];
                vimlog.debug("vim_doCommand:: operation command repeated, changing to: " + command);
                mappedCommand = VimController.command_mappings[command];
            } else {
                // If it's not a movement command or the same command again
                if (!movementAction) {
                    vimlog.debug("vim_doCommand:: operation not in conjuction with a movement");
                    gVimController.setStatusBarMessage(VimController.OPERATION_NAMES[gVimController.operationFlags]+
                                                " operation must occur in conjunction with a movement command",
                                                5000, true);
                    gVimController.resetCommandSettings();
                    return false;
                }
                vimlog.debug("vim_doCommand:: is a opMovementAction");
                opMovementAction = true;
                if ((command == 'cmd_vim_wordRight') &&
                    (gVimController.operationFlags == VimController.OPERATION_CHANGE)) {
                    // Special case command, does not eat whitespace like cmd_wordRight
                    vimlog.debug("Special casing cmd_vim_wordRight for change command, mapping to cmd_vim_changeWord instead");
                    command = 'cmd_vim_changeWord';
                    mappedCommand = VimController.command_mappings[command];
                }
            }
        }

        // There is a mapping, if repeatable, record this action
        // Only repeatable actions will be able to loop n times
        if (mappedCommand[1] & VimController.REPEATABLE_ACTION) {
            if (gVimController.repeatCount > 1) {
                numRepeats = gVimController.repeatCount;
                vimlog.debug("vim_doCommand:: Repeat command: " + numRepeats + " times");
            }
            // Reset the repeat count back to 0 now
            gVimController.repeatCount = 0;
        }

        // For copying, record what type of copy action it is
        if (mappedCommand[1] & VimController.COPY_ACTION) {
            gVimController._copyMode = mappedCommand[1] & VimController.COPY_ACTION;
            // reset the internal copy buffer
            gVimController._internalBuffer = "";
        }

        var commandName = mappedCommand[0];   // The command name
        if (commandName != VimController.SPECIAL_COMMAND) {
            // Set the command to the mapped command
            command = commandName;
        // } else {
            // Use it's own special handler in this file cmd_vim_...
        }

        // Record modifying action if makes modifications
        var modifyAction = ((mappedCommand[1] & VimController.MODIFY_ACTION) ||
                            (gVimController.operationFlags & VimController.OPERATION_DELETE));
        if (modifyAction) {
            // Use the original command, as repeat uses vim_doCommand() and
            // this requires the original command that was run.
            gVimController._lastModifyCommand = original_command;
            gVimController._lastRepeatCount = numRepeats;
            gVimController._lastOperationFlags = gVimController.operationFlags;
            gVimController._lastInsertedText = "";
            // Wrap the whole vi command in an undo action
            //dump("Vi beginUndoAction\n");
            scimoz.beginUndoAction();
        }

        // XXX - Leaving limitation of not knowing undo/redo history repitition count
        //if (gVimController._commandHistory.length > gVimController._commandHistoryPosition) {
        //    gVimController._commandHistory = gVimController._commandHistory.slice(0, gVimController._commandHistory.length);
        //}
        //gVimController._commandHistoryPosition = gVimController._commandHistory.length;
        //gVimController._commandHistory.push(mappedCommand);
        //gVimController._commandHistoryRepeats.push(numRepeats);

        try {
            if (commandName == VimController.SPECIAL_COMMAND) {
                var recordingMacro = false;
                // Handle macro recording: We turn off macro recording whilst
                // we perform the commands, as some may make calls to the
                // do_command() function, which will also record macros and we
                // don't want these recorded twice.
                if (typeof(ko.macros) != 'undefined' && ko.macros.recorder.mode == 'recording') {
                    recordingMacro = true;
                    for (var i = 0; i < numRepeats; i++) {
                        ko.macros.recorder.appendCommand(command);
                    }
                    ko.macros.recorder.mode = 'stopped';
                }
                // Local to this javascript file, call the function directly
                if (mappedCommand[1] & VimController.SPECIAL_REPEAT_HANDLING) {
                    // Uses repeat count specially
                    vimlog.debug("vim_doCommand:: Special repeat handling used");
                    eval(command + "(scimoz, " + numRepeats + ")");
                } else {
                    for (var i = 0; i < numRepeats; i++) {
                        eval(command + "(scimoz)");
                    }
                }
                if (recordingMacro) {
                    ko.macros.recorder.mode = 'recording';
                }
            } else {
                // Let the controllers find the necessary command
                for (var i = 0; i < numRepeats; i++) {
                    ko.commands.doCommand(command);
                }
            }

            if (opMovementAction &&
                !(mappedCommand[1] & VimController.NO_OP_FLAG_CHANGE)) {
                var movePos = gVimController._currentPos;
                if (movePos == orig_currentPos) {
                    // Use scimoz setting directly then
                    movePos = scimoz.currentPos;
                }
                // Ensure start offset for copyInternal is smaller than the
                // end offset.
                vimlog.debug("vim_doCommand:: opFlags:"+gVimController.operationFlags+
                          ", copying buffer between: "+orig_currentPos+
                          ", movePos:"+movePos);
                if (movePos < orig_currentPos) {
                    gVimController.copyInternal(scimoz, movePos, orig_currentPos,
                                                modifyAction);
                } else {
                    gVimController.copyInternal(scimoz, orig_currentPos, movePos,
                                                modifyAction);
                }
                // If we are just operating forwards, the cursor does not move.
                if (movePos > orig_currentPos) {
                    vimlog.debug("vim_doCommand:: moving cursor back to starting position");
                    scimoz.currentPos = orig_currentPos;
                    scimoz.anchor = orig_currentPos;
                    // Also update our settings, so updateCursorAndSelection()
                    // does not do additional highlight work.
                    //orig_anchor = orig_currentPos;
                    gVimController._currentPos = orig_currentPos;
                }
            }
        } catch(ex if ex instanceof VimController.NotImplementedException) {
            vimlog.warn(ex.message);
            gVimController.setStatusBarMessage(ex.message, 5000, true);
        } catch (ex) {
            vimlog.error("vim_doCommand:: Command '"+original_command+"' failed:");
            vimlog.exception(ex);
        } finally {
            if (modifyAction) {
                //dump("Vi endUndoAction\n");
                scimoz.endUndoAction();
            }
        }

        if (command in VimController.operation_commands) {
            // Check if it's in visual mode or we have selected text
            var selectionStart = scimoz.anchor;
            var selectionEnd = scimoz.currentPos;
            if (gVimController.mode == VimController.MODE_VISUAL) {
                if (gVimController._visualMode == VimController.VISUAL_LINE) {
                    // Visual line mode uses different settings from scimoz API
                    if (selectionStart < selectionEnd) {
                        selectionStart = scimoz.getLineSelStartPosition(scimoz.lineFromPosition(selectionStart));
                        selectionEnd = scimoz.getLineSelEndPosition(scimoz.lineFromPosition(selectionEnd));
                    } else {
                        selectionEnd = scimoz.getLineSelStartPosition(scimoz.lineFromPosition(selectionEnd));
                        selectionStart = scimoz.getLineSelEndPosition(scimoz.lineFromPosition(selectionStart));
                    }
                    // Set copyMode to line type, so pastes will work properly
                    gVimController._copyMode = VimController.COPY_LINES;
                } else if (selectionStart == selectionEnd) {
                    // Visual mode, but no selection, operate on char at currentPos
                    selectionStart = scimoz.positionAfter(selectionEnd);
                }
            }
            if (selectionStart != selectionEnd) {
                vimlog.debug("vim_doCommand:: opFlags:"+gVimController.operationFlags+
                          ", copying buffer between: "+selectionStart+
                          " and "+selectionEnd);
                if (selectionStart < selectionEnd) {
                    gVimController.copyInternal(scimoz, selectionStart, selectionEnd,
                                                (gVimController.operationFlags & VimController.OPERATION_DELETE));
                    // Move to the start of the selection after the copy/delete
                    gVimController._currentPos = selectionStart;
                } else {
                    gVimController.copyInternal(scimoz, selectionEnd, selectionStart,
                                                (gVimController.operationFlags & VimController.OPERATION_DELETE));
                }
                gVimController.resetCommandSettings();
            }
        } else if (!(mappedCommand[1] & VimController.NO_OP_FLAG_CHANGE)) {
            // Reset the operationFlags back to normal. Not done if the
            // operation actions need to be delayed, see bug:
            // http://bugs.activestate.com/show_bug.cgi?id=72695
            gVimController.resetCommandSettings();
        }

        // If we are still in visual mode, update the selection or leave
        // visual mode for special cased commands.
        if (gVimController.mode == VimController.MODE_VISUAL) {
            if (mappedCommand[1] & VimController.CANCELS_VISUAL_MODE) {
                gVimController.mode = VimController.MODE_NORMAL;
            }
            if (command == "cmd_vim_changeOperation") {
                // Change on a visual selection will enter insert mode.
                gVimController.mode = VimController.MODE_INSERT;
            }
        }

        // Enter insert mode if the command specified it or if it's a
        // change text operation (like "c w")
        if ((mappedCommand[1] & VimController.ENTER_MODE_INSERT) ||
            (opMovementAction &&
             (gVimController._lastOperationFlags == VimController.OPERATION_CHANGE) &&
             !(mappedCommand[1] & VimController.DELAY_MODE_INSERT))) {
            vimlog.debug("vim_doCommand:: Command forces INSERT mode");
            gVimController.mode = VimController.MODE_INSERT;
            // Start recording what gets entered
            gVimController._lastInsertedText = "";
        //} else {
        //    // Go back to normal mode
        //    gVimController.mode = VimController.MODE_NORMAL;
        }

        var new_currentPos = gVimController._currentPos;
        if (new_currentPos == orig_currentPos) {
            new_currentPos = null;  /* selection handler will work it out */
        }
        var set_caretx = modifyAction ||
                         (mappedCommand[1] & VimController.CHOOSE_CARET_X);
        gVimController.updateCursorAndSelection(scimoz,
                                                orig_currentPos,
                                                new_currentPos,
                                                orig_anchor,
                                                set_caretx);

        rc = true;
    } catch (e) {
        vimlog.exception(e);
        vimlog.error("vim_doCommand:: An error occurred executing the command '" + command + "'");
        throw Components.results.NS_ERROR_FAILURE;
    }
    return rc;
}


/**
 * Repeat the last Vi command.
 *
 * @param scimoz {Components.interfaces.ISciMoz} - Scimoz object.
 */
function cmd_vim_repeatLastCommand(scimoz) {
    try {
        if (gVimController._lastModifyCommand) {
            vimlog.debug("cmd_vim_repeatLastCommand: _lastModifyCommand: " + gVimController._lastModifyCommand);
            vimlog.debug("cmd_vim_repeatLastCommand: repeatCount: " + gVimController.repeatCount);
            vimlog.debug("cmd_vim_repeatLastCommand: _lastRepeatCount: " + gVimController._lastRepeatCount);
            vimlog.debug("cmd_vim_repeatLastCommand: _lastOperationFlags: " + gVimController._lastOperationFlags);
            vimlog.debug("cmd_vim_repeatLastCommand: _lastInsertedText: " + gVimController._lastInsertedText);

            // Work out how many times to perform the command
            var numRepeats = 1;
            if (gVimController.repeatCount > 1) {
                numRepeats = gVimController.repeatCount;
            }

            // Make a copy of these, as they will get modified as we run
            // commands, then restore them once were done. Bug 58627
            var currentOpFlags = gVimController.operationFlags;
            var lastRepeatCount = Math.max(1, gVimController._lastRepeatCount);
            var lastModifyCommand = gVimController._lastModifyCommand;
            var lastOperationFlags = gVimController._lastOperationFlags;
            var lastInsertedText = gVimController._lastInsertedText;
            var lastInsertedTextBytelength = ko.stringutils.bytelength(lastInsertedText);

            // Now we perform the repeat action
            //dump("Vi beginUndoAction\n");
            scimoz.beginUndoAction();
            try {
                var i, j;
                for (i=0; i < numRepeats; i++) {
                    gVimController.repeatCount = lastRepeatCount;
                    gVimController.operationFlags = lastOperationFlags;
                    vim_doCommand(lastModifyCommand);
                    // Re-add the text if there is some
                    if (lastInsertedText) {
                        scimoz.addText(lastInsertedTextBytelength, lastInsertedText);
                    }
                }
            } finally {
                //dump("Vi endUndoAction\n");
                scimoz.endUndoAction();
            }

            // Reset the state back to what it was like before the command
            vimlog.debug("Resetting state back to previous settings.")
            gVimController.mode = VimController.MODE_NORMAL;
            gVimController._lastInsertedText = lastInsertedText;
            gVimController._lastRepeatCount = lastRepeatCount;
            gVimController._lastModifyCommand = lastModifyCommand;
            gVimController._lastOperationFlags = lastOperationFlags;
            gVimController.operationFlags = currentOpFlags;
        }
    } catch (e) {
        vimlog.exception(e);
    }
}

// Movement commands
function cmd_vim_left(scimoz) {
    // Cannot move past the beginning of the current line
    var lineNo = scimoz.lineFromPosition(gVimController._currentPos);
    var lineStartPos = scimoz.positionFromLine(lineNo);
    if ((gVimController._currentPos > lineStartPos) ||
        // Or they allow it through a customized vi setting
        (gVimController.settings["whichwrap"].indexOf("<") >= 0)) {
        gVimController._currentPos = scimoz.positionBefore(gVimController._currentPos);
    }
}

function cmd_vim_right(scimoz, allowWhichWrap /* true */) {
    if (typeof(allowWhichWrap) == 'undefined') {
        allowWhichWrap = true;
    }
    // Cannot move past the end of the current line
    var lineNo = scimoz.lineFromPosition(gVimController._currentPos);
    var lineEndPos = scimoz.getLineEndPosition(lineNo);
    if ((gVimController._currentPos < lineEndPos) ||
        // Or they allow it through a customized vi setting
        (allowWhichWrap &&
         gVimController.settings["whichwrap"].indexOf(">") >= 0)) {
        gVimController._currentPos = scimoz.positionAfter(gVimController._currentPos);
    }
}

function cmd_vim_linePrevious(scimoz) {
    // Vi moves full lines at a time, so ignore word wrap - bug 87356.
    var lineNo = scimoz.lineFromPosition(gVimController._currentPos) - 1;
    if (lineNo < 0) {
        return;
    }
    // Maintain the column position.
    var column = scimoz.getColumn(gVimController._currentPos);
    var lineEndPos = scimoz.getLineEndPosition(lineNo);
    column = Math.min(column, scimoz.getColumn(lineEndPos));
    gVimController._currentPos = scimoz.positionAtColumn(lineNo, column);
}

function cmd_vim_lineNext(scimoz) {
    // Vi moves full lines at a time, so ignore word wrap - bug 87356.
    var lineNo = scimoz.lineFromPosition(gVimController._currentPos) + 1;
    if (lineNo >= scimoz.lineCount) {
        return;
    }
    // Maintain the column position.
    var column = scimoz.getColumn(gVimController._currentPos);
    var lineEndPos = scimoz.getLineEndPosition(lineNo);
    column = Math.min(column, scimoz.getColumn(lineEndPos));
    gVimController._currentPos = scimoz.positionAtColumn(lineNo, column);
}

function cmd_vim_home(scimoz) {
    // Vi moves full lines at a time, so ignore word wrap - bug 87356.
    scimoz.vCHome();
}

function cmd_vim_homeAbsolute(scimoz) {
    // Vi moves full lines at a time, so ignore word wrap - bug 87356.
    scimoz.home();
}

function cmd_vim_end(scimoz) {
    // Vi moves full lines at a time, so ignore word wrap - bug 87356.
    scimoz.lineEnd();
}

function cmd_vim_selectLinePrevious(scimoz) {
    // Vi moves full lines at a time, so ignore word wrap - bug 87356.
    cmd_vim_linePrevious(scimoz);
}

function cmd_vim_selectLineNext(scimoz) {
    // Vi moves full lines at a time, so ignore word wrap - bug 87356.
    cmd_vim_lineNext(scimoz);
}

function cmd_vim_scrollHalfPageDown(scimoz) {
    var lineNo = scimoz.lineFromPosition(gVimController._currentPos);
    var visLineNo = scimoz.visibleFromDocLine(lineNo);
    var linesToScroll = (scimoz.linesOnScreen / 2);
    scimoz.lineScroll(0, linesToScroll);
    lineNo = scimoz.docLineFromVisible(Math.min(scimoz.lineCount, visLineNo + linesToScroll));
    gVimController._currentPos = scimoz.positionFromLine(lineNo);
}

function cmd_vim_scrollHalfPageUp(scimoz) {
    var lineNo = scimoz.lineFromPosition(gVimController._currentPos);
    var visLineNo = scimoz.visibleFromDocLine(lineNo);
    var linesToScroll = (scimoz.linesOnScreen / 2);
    scimoz.lineScroll(0, -linesToScroll);
    lineNo = scimoz.docLineFromVisible(Math.max(0, visLineNo - linesToScroll));
    gVimController._currentPos = scimoz.positionFromLine(lineNo);
}

function cmd_vim_wordRightEnd(scimoz) {
    if (!gVimController.operationFlags) {
        // Special case, move to the last character in the word - bug 88394.
        scimoz.currentPos = scimoz.positionAfter(scimoz.currentPos);
        ko.commands.doCommand("cmd_wordRightEnd");
        var currentPos = scimoz.currentPos;
        var beforePos = scimoz.positionBefore(currentPos);
        scimoz.currentPos = beforePos;
        // Move anchor too.
        if (scimoz.anchor == currentPos) {
            scimoz.anchor = beforePos;
        }
    } else {
        ko.commands.doCommand("cmd_wordRightEnd");
    }
}

function cmd_vim_gotoLine(scimoz, lineNumber) {
    try {
        if (typeof(lineNumber) != 'undefined') {
            scimoz.gotoLine(lineNumber - 1);  // scimoz handles out of bounds
        } else if (gVimController.repeatCount > 0) {
            scimoz.gotoLine(gVimController.repeatCount - 1);  // scimoz handles out of bounds
            gVimController.repeatCount = 0;
        } else {
            ko.commands.doCommand('cmd_documentEnd');
        }
    } catch (e) {
        vimlog.exception(e);
    }
}

function cmd_vim_jumpToMatchingBrace(scimoz) {
    try {
        var braces = "[]{}()";
        if (["Python", "YAML"].indexOf(ko.views.manager.currentView.language)) {
            braces += ":";
        }
        var currentPos = scimoz.currentPos;
        var lineNo = scimoz.lineFromPosition(currentPos);
        var lineEndPos = scimoz.getLineEndPosition(lineNo);
        var line = scimoz.getTextRange(currentPos, lineEndPos);
        var re_expr = new RegExp("[\\" + braces.split("").join("\\") + "]");
        var match = re_expr.exec(line);
        if (match) {
            var newPos = currentPos + ko.stringutils.bytelength(line.substr(0, match.index));
            scimoz.currentPos = newPos;
            scimoz.anchor = newPos;
            ko.commands.doCommand('cmd_jumpToMatchingBrace');
            // Move one char back to the left - to keep vim compatibility.
            currentPos = scimoz.currentPos;
            lineNo = scimoz.lineFromPosition(currentPos);
            var lineStartPos = scimoz.positionFromLine(lineNo);
            if (currentPos > lineStartPos) {
                currentPos = scimoz.positionBefore(currentPos);
                scimoz.currentPos = currentPos;
                scimoz.anchor = currentPos;
            }
        }
    } catch (e) {
        vimlog.exception(e);
    }
}

function cmd_vim_wordRightEndPastPunctuation(scimoz) {
    ko.commands.doCommand("cmd_wordRightEndPastPunctuation");
    if (gVimController.operationFlags) {
        // Special case command, include last character in movement
        var currentPos = scimoz.currentPos;
        var lineNo = scimoz.lineFromPosition(currentPos);
        var lineEndPos = scimoz.getLineEndPosition(lineNo)
        if (currentPos < lineEndPos) {
            scimoz.currentPos = scimoz.positionAfter(currentPos);
        }
    }
}

function cmd_vim_jumpToLineBeforeLastJump() {
    ko.history.move_to_loc_before_last_jump(ko.views.manager.currentView, true);
}

function cmd_vim_jumpToLocBeforeLastJump() {
    ko.history.move_to_loc_before_last_jump(ko.views.manager.currentView, false);
}

function cmd_vim_scrollLineToCenterHome() {
    ko.commands.doCommand('cmd_editCenterVertically');
    ko.commands.doCommand('cmd_homeAbsolute');
    ko.commands.doCommand('cmd_home');
}

function cmd_vim_scrollLineToBottomHome(scimoz) {
    ko.commands.doCommand('cmd_homeAbsolute');
    ko.commands.doCommand('cmd_home');
    var newFVL = scimoz.lineFromPosition(scimoz.currentPos) - scimoz.linesOnScreen + 1;
    scimoz.firstVisibleLine = Math.max(0, newFVL);
}

function cmd_vim_insert(scimoz) {
    scimoz.replaceSel("");
}

function cmd_vim_append(scimoz) {
    try {
        // We don't want to go past the end of the line
        var currentPos = scimoz.currentPos;
        var lineNo = scimoz.lineFromPosition(currentPos);
        var lineEndPos = scimoz.getLineEndPosition(lineNo)
        if (currentPos < lineEndPos) {
            ko.commands.doCommand('cmd_right');
        }
    } catch (e) {
        vimlog.exception(e);
    }
}

function cmd_vim_changeChar(scimoz, repeatCount) {
    try {
        cmd_vim_cutChar(scimoz, repeatCount);
    } catch (e) {
        vimlog.exception(e);
    }
}

// We want to mimic what cmd_wordRight does, though this is a little bit
// special, as we want to eat the whitespace after all the words, except
// in the case of the the last word.
function cmd_vim_changeWord(scimoz, repeatCount) {
    try {
        var currentPos = gVimController._currentPos;
        if (repeatCount > 1) {
            // Eat both words and whitespace
            for  (var i=1; i < repeatCount; i++) {
                scimoz.wordRight();
            }
            currentPos = scimoz.currentPos;
        }
        // Now we only want to move to the end of the word, not to eat
        // the spaces. Update the internal currentPos, the deletion will
        // be taken care of by vim_doCommand() after we return.
        gVimController._currentPos = scimoz.wordEndPosition(currentPos, false);
    } catch (e) {
        vimlog.exception(e);
    }
}

function cmd_vim_changeLine(scimoz, repeatCount) {
    try {
        if (!repeatCount) {
            repeatCount = 1;
        }
        // We don't actually delete all of the last line, just till EOL
        repeatCount -= 1;
        var lineNo = scimoz.lineFromPosition(gVimController._currentPos);
        var start = scimoz.positionFromLine(lineNo);
        // If the start of the line is whitespace, move to the first word.
        if (gVimController.regexWhitespace.test(scimoz.getWCharAt(start))) {
            var startIndent = scimoz.wordEndPosition(start, false);
            if (scimoz.lineFromPosition(startIndent) == lineNo) {
                start = startIndent;
            }
        }
        var endLine = Math.min(lineNo+repeatCount, scimoz.lineCount);
        var end = scimoz.getLineEndPosition(endLine);
        gVimController.copyInternal(scimoz, start, end, true);
        gVimController._currentPos = start;
        gVimController._anchor = start;
    } catch (e) {
        vimlog.exception(e);
    }
}

function cmd_vim_yankLine(scimoz, repeatCount) {
    try {
        if (!repeatCount) {
            repeatCount = 1;
        }
        var currentPos = scimoz.currentPos;
        var lineNo = scimoz.lineFromPosition(currentPos);
        var start = scimoz.positionFromLine(lineNo);
        var endLine = Math.min(lineNo+repeatCount, scimoz.lineCount);
        var end = scimoz.positionFromLine(endLine);
        var ensureEndsWithNewline = true;
        gVimController.copyInternal(scimoz, start, end, false, ensureEndsWithNewline);
    } catch (e) {
        vimlog.exception(e);
    }
}

function cmd_vim_changeLineEnd(scimoz) {
    cmd_vim_lineCutEnd(scimoz);
}

function cmd_vim_cutChar(scimoz, repeatCount) {
    try {
        var currentPos = scimoz.currentPos;
        var lineNo = scimoz.lineFromPosition(currentPos);
        var lineEndPos = scimoz.getLineEndPosition(lineNo);
        if (currentPos < lineEndPos) {
            // delete character to the right of the cursor
            var end = scimoz.positionAfter(currentPos);
            // do not delete past the eol
            while ((repeatCount > 1) && (end < lineEndPos)) {
                end = scimoz.positionAfter(end);
                repeatCount -= 1;
            }
            gVimController.copyInternal(scimoz, currentPos, end, true);
        // Else if we are at the end of the line, we can delete the char
        // to the left if there is one, fixes bug:
        // http://bugs.activestate.com/show_bug.cgi?id=62438
        } else if ((currentPos == lineEndPos) &&
                   (currentPos > scimoz.positionFromLine(lineNo))) {
            var start = scimoz.positionBefore(currentPos);
            gVimController.copyInternal(scimoz, start, currentPos, true);
        }
    } catch (e) {
        vimlog.exception(e);
    }
}

function cmd_vim_cutCharLeft(scimoz) {
    try {
        var currentPos = scimoz.currentPos;
        var lineNo = scimoz.lineFromPosition(currentPos);
        var lineStartPos = scimoz.positionFromLine(lineNo);
        if (currentPos > lineStartPos) {
            // delete character to the right of the cursor
            var start = scimoz.positionBefore(currentPos);
            gVimController.copyInternal(scimoz, start, currentPos, true);
        }
    } catch (e) {
        vimlog.exception(e);
    }
}

function cmd_vim_deleteToDocumentEnd(scimoz) {
    try {
        gVimController.copyInternal(scimoz, scimoz.currentPos, scimoz.length,
                                    true);
    } catch (e) {
        vimlog.exception(e);
    }
}

/**
 * Start yank operation, ie: "y w", "y e", "y G", etc...
 * Have to wait for till after the movement command to see how much to yank.
 */
function cmd_vim_yankOperation(scimoz) {
    gVimController.operationFlags = VimController.OPERATION_YANK;
}

/**
 * Start delete operation, ie: "d w", "d e", "d G", etc...
 * Have to wait for till after the movement command to see how much to delete.
 */
function cmd_vim_deleteOperation(scimoz) {
    gVimController.operationFlags = VimController.OPERATION_DELETE;
}

/**
 * Start change operation, ie: "c w", "c e", "c G", etc...
 * Have to wait for till after the movement command to see how much to change.
 */
function cmd_vim_changeOperation(scimoz) {
    gVimController.operationFlags = VimController.OPERATION_CHANGE;
}

/**
 * Start indent operation, ie: "> >"
 */
function cmd_vim_indentOperation(scimoz) {
    gVimController.operationFlags = VimController.OPERATION_INDENT;
}

/**
 * Start dedent operation, ie: "< <"
 */
function cmd_vim_dedentOperation(scimoz) {
    gVimController.operationFlags = VimController.OPERATION_DEDENT;
}

function cmd_vim_insert_newline_next(scimoz) {
    var currentPos = scimoz.currentPos;
    var lineNo = scimoz.lineFromPosition(currentPos);
    var lineEndPos = scimoz.getLineEndPosition(lineNo);
    scimoz.currentPos = scimoz.anchor = lineEndPos;
    ko.commands.doCommand('cmd_newline');
}

function cmd_vim_lineCut(scimoz, repeatCount) {
    try {
        var currentPos = scimoz.currentPos;
        var lineNo = scimoz.lineFromPosition(currentPos);
        if (lineNo < scimoz.lineCount) {
            var start = scimoz.positionFromLine(lineNo);
            if ((lineNo + repeatCount) >= scimoz.lineCount) {
                repeatCount = scimoz.lineCount - lineNo;
            }
            var end = scimoz.positionFromLine(lineNo+repeatCount);
            var deletedLastLine = false;
            var endLineNo = scimoz.lineFromPosition(end);
            if ((endLineNo == lineNo) || (end == scimoz.length)) {
                // Case where deleting the last line.
                deletedLastLine = true;
            }
            var ensureEndsWithNewline = true;
            gVimController.copyInternal(scimoz, start, end, true,
                                        ensureEndsWithNewline);
            if (deletedLastLine && lineNo > 0) {
                // Move up one line (behave like vim), bug 51878.
                scimoz.lineUp();
                scimoz.home();
            }
        }
    } catch (e) {
        vimlog.exception(e);
    }
}

function cmd_vim_lineCutEnd(scimoz) {
    try {
        var currentPos = scimoz.currentPos;
        var lineNo = scimoz.lineFromPosition(currentPos);
        var end = scimoz.getLineEndPosition(lineNo);
        gVimController.copyInternal(scimoz, currentPos, end, true);
    } catch (e) {
        vimlog.exception(e);
    }
}

function _cmd_vim_pasteLines_handler(scimoz, buf, pasteAfter, repeatCount) {
    try {
        var noEOLOnLastLine = false;
        var currentPos = gVimController._currentPos;
        if (pasteAfter) {
            var lineNo = scimoz.lineFromPosition(currentPos);
            if (lineNo == (scimoz.lineCount - 1)) {
                // Case where already on the last line and no EOL, bug 81184.
                noEOLOnLastLine = true;
                scimoz.lineEnd();
                scimoz.newLine();
            } else {
                scimoz.lineDown();
            }
        }
        // Go to column 0 on current line
        scimoz.home();
        var start = scimoz.currentPos;
        // Make the complete string we are going to be pasting.
        var pasteBuffer = buf;
        for (var i=1; i < repeatCount; i++) {
            pasteBuffer += buf;
        }
        if (noEOLOnLastLine) {
            // Trim the last newline from the pasted text.
            var lastChar = pasteBuffer[pasteBuffer.length - 1];
            var secondLastChar = pasteBuffer[pasteBuffer.length - 2];
            if (lastChar == '\n' && secondLastChar == '\r') {
                pasteBuffer = pasteBuffer.substr(0, pasteBuffer.length - 2);
            } else if (lastChar == '\r' || lastChar == '\n') {
                pasteBuffer = pasteBuffer.substr(0, pasteBuffer.length - 1);
            }
        }
        // Must use a byte length here, see bug 63498
        var byteLength = ko.stringutils.bytelength(pasteBuffer);
        scimoz.addText(byteLength, pasteBuffer);
        scimoz.anchor = scimoz.currentPos;
        scimoz.currentPos = start;
        gVimController._currentPos = start;
        scimoz.vCHomeWrap();
    } catch (e) {
        vimlog.exception(e);
    }
}

function _cmd_vim_paste(scimoz, buf, repeatCount) {
    try {
        // Make the complete string we are going to be pasting.
        var pasteBuffer = buf;
        for (var i=1; i < repeatCount; i++) {
            pasteBuffer += buf;
        }
        // Must use a byte length here, see bug 63498
        var byteLength = ko.stringutils.bytelength(buf);
        scimoz.addText(byteLength * repeatCount, pasteBuffer);
        gVimController._currentPos = scimoz.currentPos;
        gVimController._anchor = gVimController._currentPos;
    } catch (e) {
        vimlog.exception(e);
    }
}

function cmd_vim_paste(scimoz, repeatCount) {
    // Any selection is removed as part of the paste
    scimoz.replaceSel("");
    var buf = gVimController._getTextForPaste();
    if (buf) {
        if (gVimController._copyMode == VimController.COPY_LINES) {
            // Special case for multiple lines
            _cmd_vim_pasteLines_handler(scimoz, buf, false, repeatCount);
        } else {
            _cmd_vim_paste(scimoz, buf, repeatCount);
        }
    }
}

function cmd_vim_pasteAfter(scimoz, repeatCount) {
    // Any selection is removed as part of the paste
    scimoz.replaceSel("");
    var buf = gVimController._getTextForPaste();
    if (buf) {
        if (gVimController._copyMode == VimController.COPY_LINES) {
            // Special case for multiple lines
            _cmd_vim_pasteLines_handler(scimoz, buf, true, repeatCount);
        } else {
            // Ensure allowWhichWrap is false so we don't go past the eol.
            cmd_vim_right(scimoz, false /* allowWhichWrap */);
            // Ensure the scimoz position reflects the vim controller position,
            // fixes pasting bug 71057.
            scimoz.currentPos = gVimController._currentPos;
            _cmd_vim_paste(scimoz, buf, repeatCount);
        }
    }
}

function cmd_vim_cancel(scimoz) {
    if (gVimController.mode == VimController.MODE_COMMAND) {
        gVimController.inputBufferFinish();
    } else if (gVimController.mode == VimController.MODE_INSERT) {
        // Normal vi will move the cursor one to the left here
        // XXX TODO - We may have a repeat count, perform multiples if needed.
        var lineNo = scimoz.lineFromPosition(gVimController._currentPos);
        var lineStartPos = scimoz.positionFromLine(lineNo);
        if (gVimController._currentPos > lineStartPos) {
            //ko.commands.doCommand('cmd_left');
            gVimController._currentPos = scimoz.positionBefore(gVimController._currentPos);
        }
        if (scimoz.autoCActive()) {
            scimoz.autoCCancel();
        }
    }
    gVimController.mode = VimController.MODE_NORMAL;
    gVimController.repeatCount = 0;
    gVimController.operationFlags = VimController.OPERATION_NONE;
}

function cmd_vim_findNext(scimoz) {
    gVimController.performSearch(scimoz, null);
}

function cmd_vim_findPrevious(scimoz) {
    gVimController.performSearch(scimoz, null, true /* reverseDirection */);
}

function cmd_vim_findCharInLine(scimoz) {
    // Next character typed, we'll search for it
    gVimController.mode = VimController.MODE_FIND_CHAR;
    gVimController._findCharDirection = VimController.SEARCH_FORWARD;
}

function cmd_vim_findPreviousCharInLine(scimoz) {
    // Next character typed, we'll search for it backwards
    gVimController.mode = VimController.MODE_FIND_CHAR;
    gVimController._findCharDirection = VimController.SEARCH_BACKWARD;
}

function cmd_vim_findCharInLinePosBefore(scimoz) {
    cmd_vim_findCharInLine(scimoz);
    gVimController._movePosBefore = true;
}

function cmd_vim_findPreviousCharInLinePosAfter(scimoz) {
    cmd_vim_findPreviousCharInLine(scimoz);
    gVimController._movePosBefore = true;
}

function cmd_vim_repeatLastFindCharInLine(scimoz, repeatCount) {
    gVimController.findCharInLine(scimoz,
                                  gVimController._lastFindChar,
                                  gVimController._lastMovePosBefore,
                                  repeatCount);
}

function cmd_vim_repeatLastFindCharInLineReversed(scimoz, repeatCount) {
    gVimController.findCharInLine(scimoz,
                                  gVimController._lastFindChar,
                                  gVimController._lastMovePosBefore,
                                  repeatCount,
                                  true /* reverseDirection */);
}

function _cmd_vim_findWordUnderCursor_wrapper(scimoz, searchDirection) {
    try {
        var currentPos = scimoz.currentPos;
        var lineNo = scimoz.lineFromPosition(currentPos);
        var lineStartPos = scimoz.positionFromLine(lineNo);
        var lineEndPos = scimoz.getLineEndPosition(lineNo);
        var text = scimoz.getTextRange(lineStartPos, lineEndPos);
        var cursorPos = currentPos - lineStartPos;
        var wordStartPos = text.search(/\w/);
        var wordEndPos = -1;
        var word = "";
        while (text && (wordStartPos >= 0)) {
            wordEndPos = text.search(/\W/);
            if (wordEndPos < 0) {
                word = text.substr(wordStartPos);
                break;
            }
            word = text.substr(wordStartPos, wordEndPos);
            // XXX - Could be better:
            // This should really be (cursorPos < wordEndPos)
            // But the find system highlights the word and moves the cursor
            // past the end of the word, so under repeating this search, the
            // word is lost and the next word in the line becomes the searched
            // for word.
            if (cursorPos <= wordEndPos) {
                break;
            }
            //dump("Word now: " + word + "\n");
            // Update the variables, moving target here
            text = text.substr(wordEndPos + 1);
            cursorPos -= (word.length + 1);
            wordStartPos = text.search(/\w/);
        }
        if (word.length > 0) {
            //dump("Find word: " + word + "\n");
            // Go and find the next sucker then
            gVimController._searchDirection = searchDirection;
            gVimController._searchOptions = [];
            gVimController.performSearch(scimoz, word, null, true /* matchWord */);
        } else {
            var msg = "Search: No word found under the cursor.";
            require("notify/notify").send(msg, "viEmulation", {priority: "warning"});
        }
    } catch (e) {
        vimlog.exception(e);
    }
}

function cmd_vim_findWordUnderCursor(scimoz) {
    _cmd_vim_findWordUnderCursor_wrapper(scimoz, VimController.SEARCH_FORWARD);
}

function cmd_vim_findWordUnderCursorBack(scimoz) {
    _cmd_vim_findWordUnderCursor_wrapper(scimoz, VimController.SEARCH_BACKWARD);
}

// Visual mode
function _toggleVisualMode(scimoz, visual_type) {
    if ((gVimController.mode != VimController.MODE_VISUAL) ||
        (gVimController._visualMode != visual_type)) {
        var wasInDifferentVisualMode = (gVimController.mode == VimController.MODE_VISUAL);
        gVimController._visualMode = visual_type;
        gVimController.mode = VimController.MODE_VISUAL;
        if (visual_type == VimController.VISUAL_CHAR) {
            scimoz.selectionMode = scimoz.SC_SEL_STREAM;
        } else if (visual_type == VimController.VISUAL_LINE) {
            scimoz.selectionMode = scimoz.SC_SEL_LINES;
        } else if (visual_type == VimController.VISUAL_BLOCK) {
            scimoz.selectionMode = scimoz.SC_SEL_RECTANGLE;
            // After setting the selection mode, need to ensure the cursor has
            // not moved:
            scimoz.anchor = gVimController._anchor;
            scimoz.currentPos = gVimController._currentPos;
        }
        if (wasInDifferentVisualMode) {
            // Ensure the status bar shows the correct visual mode
            gVimController.updateStatusBarMode();
        }
    } else {
        gVimController.mode = VimController.MODE_NORMAL;
    }
}

function cmd_vim_toggleVisualMode(scimoz) {
    _toggleVisualMode(scimoz, VimController.VISUAL_CHAR);
}

function cmd_vim_toggleVisualLineMode(scimoz) {
    _toggleVisualMode(scimoz, VimController.VISUAL_LINE);
}

function cmd_vim_toggleVisualBlockMode(scimoz) {
    _toggleVisualMode(scimoz, VimController.VISUAL_BLOCK);
}

// Special commands
function cmd_vim_doReplaceChar(scimoz, repeatCount) {
    // When in VISUAL mode with active selection, we replace the selection and ignore repeatCount
    if ((gVimController._lastMode == VimController.MODE_VISUAL) &&
        (gVimController._currentPos != gVimController._anchor)) {
        var new_currentPos = Math.min(gVimController._currentPos, gVimController._anchor);
        var newtext = gVimController._lastReplaceChar;
        for (var i=1; i < scimoz.selText.length; i++) {
            if (('\r' == scimoz.selText.charAt(i)) || ('\n' == scimoz.selText.charAt(i))) {
                newtext += scimoz.selText.charAt(i);
            } else {
                newtext += newtext[0];
            }
        }
        scimoz.replaceSel(newtext);
        gVimController._currentPos = new_currentPos;
        gVimController._lastRepeatCount = newtext.length;
    } else {
        // Only perform the deletion to the end of the line if there are characters
        var currentPos = gVimController._currentPos;
        var lineNo = scimoz.lineFromPosition(currentPos);
        var lineEndPos = scimoz.getLineEndPosition(lineNo);
        var text = scimoz.getTextRange(currentPos, lineEndPos);
        if (text.length < 1) {
            return;
        } else if (text.length < repeatCount) {
            repeatCount = text.length;
        }
        scimoz.targetStart = currentPos;
        scimoz.targetEnd = currentPos + ko.stringutils.bytelength(text.substring(0, repeatCount));
        var newtext = gVimController._lastReplaceChar;
        for (var i=1; i < repeatCount; i++) {
            newtext += newtext[0];
        }
        scimoz.replaceTarget(newtext.length, newtext);
        if (repeatCount > 1) {
            gVimController._currentPos += (newtext.length -1);
        }
    }
    gVimController._lastModifyCommand = 'cmd_vim_doReplaceChar';
    gVimController._lastInsertedText = '';
}

function cmd_vim_replaceChar(scimoz) {
    gVimController.mode = VimController.MODE_REPLACE_CHAR;
}

function cmd_vim_overtype(scimoz, turnOn) {
    try {
        if (typeof(turnOn) == 'undefined' || turnOn) {
            scimoz.overtype = 1;
            gVimController.mode = VimController.MODE_OVERTYPE;
        } else {
            scimoz.overtype = 0;
        }
    } catch (e) {
        vimlog.exception(e);
    }
}

function cmd_vim_dedent(scimoz, repeatCount, isVisual /* false */) {
    var lineNo = scimoz.lineFromPosition(Math.min(gVimController._anchor, gVimController._currentPos));
    var endLineNo;
    var anchor = scimoz.positionFromLine(lineNo);
    if (!isVisual) {
        /* No selection. */
        endLineNo = Math.min(scimoz.lineCount, lineNo + repeatCount - 1);
        // The repeatcount means the number of lines in this case.
        repeatCount = 1;
    } else {
        endLineNo = scimoz.lineFromPosition(Math.max(gVimController._anchor, gVimController._currentPos));
        // Set the last repeat count as the number of lines indented, so a
        // repeat will indent the proper number of lines.
        gVimController._lastRepeatCount = endLineNo - lineNo + 1;
        // Make it look like a vim_dedent, instead of a visual dedent.
        gVimController._lastModifyCommand = "cmd_vim_dedent";
    }
    scimoz.setSel(anchor,
                  scimoz.getLineEndPosition(endLineNo));
    for (var i=0; i < repeatCount; i++) {
        ko.commands.doCommand('cmd_dedent');
    }
    scimoz.currentPos = anchor;
    // Vi moves to the start of the text, we simulate that here.
    ko.commands.doCommand('cmd_home');
}

function cmd_vim_indent(scimoz, repeatCount, isVisual /* false */) {
    var lineNo = scimoz.lineFromPosition(Math.min(gVimController._anchor, gVimController._currentPos));
    var endLineNo;
    var anchor = scimoz.positionFromLine(lineNo);
    if (!isVisual) {
        /* No selection. */
        endLineNo = Math.min(scimoz.lineCount, lineNo + repeatCount - 1);
        // The repeatcount means the number of lines in this case.
        repeatCount = 1;
    } else {
        endLineNo = scimoz.lineFromPosition(Math.max(gVimController._anchor, gVimController._currentPos));
        // Set the last repeat count as the number of lines indented, so a
        // repeat will indent the proper number of lines.
        gVimController._lastRepeatCount = endLineNo - lineNo + 1;
        // Make it look like a vim_indent, instead of a visual indent.
        gVimController._lastModifyCommand = "cmd_vim_indent";
    }
    scimoz.setSel(anchor,
                  scimoz.getLineEndPosition(endLineNo));
    for (var i=0; i < repeatCount; i++) {
        ko.commands.doCommand('cmd_indent');
    }
    scimoz.currentPos = anchor;
    // Vi moves to the start of the text, we simulate that here.
    ko.commands.doCommand('cmd_home');
}

function cmd_vim_indent_visual(scimoz, repeatCount) {
    cmd_vim_indent(scimoz, repeatCount, true);
}

function cmd_vim_dedent_visual(scimoz, repeatCount) {
    cmd_vim_dedent(scimoz, repeatCount, true);
}

//
// Special handling for when in the command mode and search mode
//
function cmd_vim_enterCommandMode(scimoz) {
    try {
        var initialText = "";
        if (gVimController._currentPos != gVimController._anchor) {
            // Operate on the selection
            initialText = "'<,'>";
        }
        gVimController.inputBufferStart(gVimController._commandHistory,
                                        ":", initialText);
        gVimController.mode = VimController.MODE_COMMAND;
    } catch (e) {
        vimlog.exception(e);
    }
}

function cmd_vim_enterSearchForward(scimoz) {
    gVimController.initSearchForward();
}

function cmd_vim_enterSearchBackward(scimoz) {
    gVimController.initSearchBackward();
}

function cmd_vim_setRegister(scimoz) {
    gVimController.mode = VimController.MODE_SET_REGISTER;
}

function cmd_vim_saveAndClose(scimoz) {
    gVimController._commandDetails.clear();
    mapped_command_vim_writequit(gVimController._commandDetails);
}

function cmd_vim_closeNoSave(scimoz) {
    gVimController._commandDetails.clear();
    gVimController._commandDetails.forced = true;
    mapped_command_vim_closeBuffer(gVimController._commandDetails);
}



function _vi_updateSearchField(seachObject) {
    var s = seachObject.value;
    var c; /* current char looking at */
    var value = [];
    var options = [];
    var state = 0;
    /* state == 0 ; searching through the string */
    /* state == 1 ; getting an option or escape character */
    var endPos = s.length;
    for (var i=0; i < endPos; i++) {
        c = s[i];
        if (state == 0) {
            if (c == '\\') {
                state = 1;
                continue;
            }
            value.push(c);
        } else { // if (state == 1) {
            if (c == '\\') {
                value.push(c);
            } else if (c == "c" || c == "C") {
                options.push(c);
            } else {
                // Unknown option, just leave it as it looks
                value.push("\\" + c);
            }
            state = 0;
        }
    }
    seachObject.value = value.join("");
    seachObject.options = options;
}

// Has to be outside the class/object
function vim_InputBuffer_KeyPress(event)
{
    var stopEvent = false;
    try {
        var keyCode = event.keyCode;
        if (keyCode == event.DOM_VK_RETURN) {

            stopEvent = true;
            var value = gVimController.inputBufferFinish();
            var returnToMode = VimController.MODE_NORMAL;
            var scimoz = ko.views.manager.currentView.scintilla.scimoz;
            var orig_currentPos = scimoz.currentPos;
            var orig_anchorPos = scimoz.anchor;
            if (gVimController.mode == VimController.MODE_COMMAND) {
                gVimController.findAndRunCommand(value);
                // Scimoz may have disappeared/changed - bug 94948.
                if (!ko.views.manager.currentView ||
                    !ko.views.manager.currentView.scintilla) {
                    return;
                }
                scimoz = ko.views.manager.currentView.scintilla.scimoz;
            } else if (gVimController.mode == VimController.MODE_SEARCH) {
                // Command mode "/" or "?"
                // We have a search, set up the findSvc and perform the search
                if (value) {
                    // Only update the search details if there is something
                    // to update with, otherwsie we used whatever we used
                    // on the last search
                    var searchOptions = { value: value, options: null };
                    _vi_updateSearchField(searchOptions);
                    gVimController._searchOptions = searchOptions.options;
                    // Store the search text, will be retrieved by the
                    // cmd_vim_findNext command.
                    ko.mru.add("find-patternMru", searchOptions.value);
                }
                gVimController._lastSearchMatchWord = false;
                vim_doCommand("cmd_vim_findNext");
                if (gVimController._lastMode == VimController.MODE_VISUAL) {
                    returnToMode = VimController.MODE_VISUAL;
                }
            }
            // Save into the buffer history
            gVimController.inputBufferSaveHistory(value);

            // May have already changed to another mode such as INSERT_MODE,
            // so we don't want to change it again in that case. Fixes:
            // http://bugs.activestate.com/show_bug.cgi?id=73315
            if ((gVimController.mode == VimController.MODE_SEARCH) ||
                (gVimController.mode == VimController.MODE_COMMAND)) {
                // Properly reset visual mode when coming from the command mode,
                // bug 89041.
                if ((gVimController.mode == VimController.MODE_COMMAND) &&
                    (gVimController._lastMode == VimController.MODE_VISUAL)) {
                    gVimController.mode = gVimController._lastMode;
                }
                gVimController.mode = returnToMode;
            }

            gVimController.updateCursorAndSelection(scimoz, orig_currentPos,
                                                    null, orig_anchorPos, true);
            ko.views.manager.currentView.setFocus();
        } else if ((keyCode == event.DOM_VK_ESCAPE) ||
            ((keyCode == event.DOM_VK_BACK_SPACE) &&
             (gVimController.inputBuffer.value.length < 1))) {
            stopEvent = true;
            gVimController.inputBufferFinish();
            gVimController.mode = VimController.MODE_NORMAL;
            ko.views.manager.currentView.setFocus();
        } else if (keyCode == event.DOM_VK_UP) {
            stopEvent = true;
            gVimController.inputBufferPrevious();
        } else if (keyCode == event.DOM_VK_DOWN) {
            stopEvent = true;
            gVimController.inputBufferNext();
        }

    } catch (e) {
        if (e instanceof VimController.ViError) {
            // We handle and show this type of error to the user
            gVimController.setStatusBarMessage(e.message, 5000, true);
        } else {
            vimlog.exception(e);
        }
        // Error, return normal vi mode
        gVimController.mode = VimController.MODE_NORMAL;
        ko.views.manager.currentView.setFocus();
        gVimController.inputBufferFinish();
    } finally {
        if (stopEvent) {
            event.stopPropagation();
            event.preventDefault();
            event.cancelBubble = true;
        }
    }
}

function vim_InputBuffer_OnFocus(event)
{
    //try {
    //    // if it is not active the hidden input buffer should not have the focus
    //    if (!gVimController._inputBuffer_active && ko.views.manager.currentView) {
    //        // This has to be in a timeout for the controllers to work right.
    //        window.setTimeout('ko.views.manager.currentView.setFocus();', 1)
    //    }
    //} catch (e) {
    //    vimlog.exception(e);
    //}
}
