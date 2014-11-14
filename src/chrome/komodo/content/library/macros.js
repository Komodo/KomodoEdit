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

if (typeof(ko)=='undefined') {
    var ko = {};
}
if (typeof(ko.macros)=='undefined') {
    ko.macros = {};
}

(function() {

var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
                .getService(Components.interfaces.nsIStringBundleService)
                .createBundle("chrome://komodo/locale/library.properties");

this.CURRENT_MACRO_VERSION = 3;

function MacroRecorder() {
    this.mode = 'stopped';
    this._currentMacro = new Array();
    this._currentMacroText = '';
    this.log = ko.logging.getLogger('ko.macros.recorder');
}

MacroRecorder.prototype = new Object();
MacroRecorder.prototype.constructor = MacroRecorder;

MacroRecorder.prototype.__defineGetter__("currentMacro",
function()
{
    return this._currentMacro;
});

MacroRecorder.prototype.startRecording = function() {
    if (this.mode != 'paused') {
        if (this._currentMacro) {
            delete this._currentMacro;
        }
        this._currentMacro = new Array();
        this._currentMacro.push(_bundle.formatStringFromName("macroRecordedOnComment", [Date()], 1) + '\n');
        this._currentMacro.push('komodo.assertMacroVersion(' + ko.macros.CURRENT_MACRO_VERSION + ');\n');
        this._currentMacro.push("if (komodo.view) { komodo.view.setFocus(); }\n");
        this._currentMacroText = new Array();
    }
    this.mode = 'recording';
    var record = document.getElementById("macroRecord");
    window.updateCommands("macro");
    var msg = _bundle.GetStringFromName("recordingMacro");
    require("notify/notify").send(msg, "macros", {id: "macroRecording"});
}

MacroRecorder.prototype.stopRecording = function(quiet /* false */) {
    this.mode = 'stopped';
    this._finishTextMacro();
    if (typeof(quiet) == 'undefined') {
        quiet = false;
    }
    window.updateCommands("macro");
    if (!quiet) {
        var msg = _bundle.GetStringFromName("macroRecorded");
        require("notify/notify").send(msg, "macros", {id: "macroRecording"});
    }
}

MacroRecorder.prototype.pauseRecording = function() {
    this.stopRecording();  // but...
    this.mode = 'paused'; // set the mode to paused
}

MacroRecorder.prototype.suspendRecording = function() {
    // This is used to temporarily suspend recording when
    // recording a macro that executes another macro -- we don't
    // want what that macro does (i.e. launching of commands) to
    // be recorded in _this_ macro.  This must be paired with
    // a call to resumeRecording (below)
    if (this.mode == 'recording') {
        this.stopRecording(true); // but ...
        this.mode = 'suspended'; // set the mode to paused
    }
}

MacroRecorder.prototype.resumeRecording = function() {
    if (this.mode == 'suspended') {
        this.mode = 'paused';
        this.startRecording();
    }
}


MacroRecorder.prototype._finishTextMacro = function() {
    if (this._currentMacroText != '') {
        this._currentMacro.push("komodo.view.selection = '" +
                                this._currentMacroText.replace('\\', '\\\\', 'g').replace("\'", "\\'", 'g') +
                                "';\n");
        this._currentMacroText = '';
    }
}

MacroRecorder.prototype.appendCommand = function(command) {
    try {
        if (! this._currentMacro) {
            this.log.warn("Trying to append a command while not in a macro!!!");
            return;
        }
        this._finishTextMacro();
        this._currentMacro.push("ko.commands.doCommand('" + command +"')\n");
    } catch (e) {
        log.exception(e);
    }
}

MacroRecorder.prototype.recordKeyPress = function(c) {
    if (! this._currentMacro) {
        this.log.warn("Trying to record keypresses while not in a macro!!!");
        return;
    }
    this._currentMacroText += c;
}

MacroRecorder.prototype.undo = function() {
    if (this._currentMacroText != '') {
        this._currentMacroText = this._currentMacroText.slice(0, this._currentMacroText.length-1);
    } else {
        this._currentMacro.pop();
    }
}

MacroRecorder.prototype.appendCode = function(code) {
    if (! this._currentMacro) {
        this.log.warn("Trying to append code while not in a macro!!!");
        return;
    }
    this._finishTextMacro();
    this._currentMacro.push(code);
}

MacroRecorder.prototype.executeMacro = function(macro) {
    var view = ko.views.manager.currentView;
    var scin = null;

    if (view && view.getAttribute('type') == 'editor') {
        scin = view.scimoz;
        scin.beginUndoAction();
    }

    try {
        try {
            if (macro == null) {
                macro = this._currentMacro;
            }
            if (macro == null) return;
            if (this.mode == 'recording') {
                this.mode = 'stopped'; // avoid recursion!
            }
            if (scin) {
                // XXX weird stuff.
                // For some reason, Scintilla always thinks the lines are folded, which results in selection of
                // folded lines, which is typically not what we want So we unfold all the lines in the buffer.
                for (var lineno=0;lineno < scin.lineCount;lineno++)
                    if ((scin.getFoldLevel(lineno) & scin.SC_FOLDLEVELHEADERFLAG) &&
                        !scin.getFoldExpanded(lineno))
                            scin.toggleFold(lineno)
            }
            var code = (macro.join(''));
            ko.macros.evalAsJavaScript(code);
        } catch (e) {
            this.log.error(e);
        }
    } finally {
        if (scin) {
            scin.endUndoAction();
        }
    }
}

MacroRecorder.prototype.executeLastMacro = function(macro) {
    this.executeMacro(this._currentMacro);
}

MacroRecorder.prototype.saveToToolbox = function(macro) {
    var name = ko.dialogs.prompt(_bundle.GetStringFromName("macroName"),
                                 _bundle.GetStringFromName("enterNameForNewMacro"));
    if (!name) return;
    var part = ko.toolbox2.createPartFromType('macro');
    part.setStringAttribute('name', name);
    part.setStringAttribute('language', 'JavaScript');
    part.setBooleanAttribute('async', false);
    part.setBooleanAttribute('trigger_enabled', false);
    part.setStringAttribute('trigger', "trigger_postopen");  // just to have something
    part.value = this._currentMacro.join('');
    ko.toolbox2.addItem(part);
    ko.uilayout.ensureTabShown('toolbox2viewbox');
}

this.recorder = new MacroRecorder();


}).apply(ko.macros);
