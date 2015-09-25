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

// Keybindings.js -- code related to customizable keybindings

/* The keybindingManager controls all things keybinding-related.

    It manages:
        - configurations (sets of keybindings)
        - Which keys map to what commands
        - What commands are parametrized
        - What menuitems have what what keyboard shortcuts (acceltexts)

    It doesn't yet manage:
        - Tooltips

    A few definitions:
        - Command ID: a string, the id field of the <command> element -- e.g., 'cmd_undo'
        - key: a given key id (see keys.xul), e.g. "Ctrl-A"
        - key sequence: an array of keys e.g. ['Ctrl-A', 'Ctrl-K']
        - key label: the textual representation of a key -- it's in fact the same as the key ID
        - key sequence label: the textual representation of a key sequence -- keys are separated by ', ', e.g. "Ctrl-A, Ctrl-K"
        - configuration: A set of bindings for the factory-shipped commands (those defined in XUL at this point).
          These come in two varieties -- factory defined and custom.  The former are not modifiable by the user, the latter
          are by definition written by the user.


    API:
        Apart from the initialization, and the configuration management (done by pref-keys.js), most of the calls are to:

            AssignKey
            makeKeyActive
            unlabelMenuItem
            clearBinding

        The keybindingManager is also Observing Notify's on kb-unload, to known when to clear out 'layered' bindings.
            The "subject" of the Notify has to be the part (XXX should move to a part-independent data structure)



    Internal datastructures for those reading the code:

        Configuration management:
            - currentConfiguration: the currently active configuration
            - _knownconfigs: a list of know configurations (those which have a pref, show up in the menulist, etc.)
            - _factoryConfigurations: a subset of _knownconfigs which corresponds to the factory defaults (these days just one)

        Keys:
            - The command2key mapping maps command IDs (as in "cmd_undo") to key sequence labels (as in "Ctrl-Z")
            - The keyTree is a tree of all of the current key/command assignments, so that prefix keys map to dictionaries of
              key->command or key->subtree relationships.
            - _commandParams: a mapping of command IDs to a mapping of key sequence labels to parameters.
                e.g. if Ctrl-F -> runMacro, macro1 and
                       Ctrl-G -> runMacro, macro2 then
                    _commandParams['runMacro']['Ctrl-F'] = 'macro1'
                and _commandParams['runMacro']['Ctrl-G'] = 'macro2'
                ** A command is a parametrized command if it is a key of _commandParams -- or at least there's no other way to
                   guess from inside this code.

            - commanditems: used only for the display of known keybindings -- should move away from this class in a utility
              function

            - command2key: maps the commandId to a list of key sequence labels (the last assignment goes in front)


*/
if (typeof(ko)=='undefined') {
    var ko = {};
}
if (typeof(ko.keybindings)=='undefined') {
    ko.keybindings = {};
}
(function() {
var _log = ko.logging.getLogger('keybindings');
var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
                .getService(Components.interfaces.nsIStringBundleService)
                .createBundle("chrome://komodo/locale/keybindings.properties");

//_log.setLevel(ko.logging.LOG_DEBUG);
    
this.Manager = function KeybindingManager() {
    this.commanditems = null; // XXX
    this.command2key = {}; // what key for a command?
    this.key2command= {}; // what command assigned to a key?
    this.keyTree = {};
    this.activeCommands = {};
    var line, i;
    this.prefset = ko.prefs;
    this._knownconfigs = [];
    this.keybindingSchemeService = Components.classes['@activestate.com/koKeybindingSchemeService;1'].getService();
    var schemes = new Array();
    this.keybindingSchemeService.getSchemeNames(schemes, new Object());
    this._knownconfigs = schemes.value;
    this.currentConfiguration = this.prefset.getStringPref('keybinding-scheme');
    this.currentScheme = this.keybindingSchemeService.getScheme(this.currentConfiguration);
    //dump('got currentConfiguration = ' + this.currentConfiguration + '\n');

    this._commandParams = {}
    this.currentPrefixString = '';
    this.document = document;
    var observerSvc = Components.classes["@mozilla.org/observer-service;1"].
        getService(Components.interfaces.nsIObserverService);
    // Each main window has an instance of this observer, and we shut each one down when the window is closed.
    observerSvc.addObserver(this, "kb-unload",false);
    observerSvc.addObserver(this, "kb-unload-global",false);
    observerSvc.addObserver(this, "kb-load",false);
    observerSvc.addObserver(this, "kb-load-global",false);
    observerSvc.addObserver(this, 'toolbox-loaded-local', false);
    observerSvc.addObserver(this, 'toolbox-loaded-global', false);
    observerSvc.addObserver(this, 'toolbox-loaded', false); // synonym for global
    observerSvc.addObserver(this, 'toolbox-unloaded', false);
    observerSvc.addObserver(this, 'toolbox-unloaded-local', false);
    observerSvc.addObserver(this, 'toolbox-unloaded-global', false);

    var me = this;
    this.removeListener = function() { me.finalize(); }
    window.addEventListener("unload", this.removeListener, false);
    
    // catch keystrokes on bubble, this allows widgets to specificly override
    // a keybinding, which is the case with tree's, listbox, and many more
// #if PLATFORM != 'darwin'
    // keydown is required to capture modifer+shift keybindings correctly on
    // windows and unix
    this.keyDownLabels = null;
    window.addEventListener('keydown',gKeyDownHandler, false);
    window.addEventListener('keypress', gF10KeyHandler, true);
// #endif
    window.addEventListener('keypress',gKeyHandler, false);
    this.inPrefixCapture = false;
}

this.Manager.prototype.constructor = this.Manager;

this.Manager.prototype.finalize = function(part, topic, partId) {
    window.removeEventListener('keypress', gKeyHandler, false);
// #if PLATFORM != 'darwin'
    window.removeEventListener('keypress', gF10KeyHandler, true);
    window.removeEventListener('keydown', gKeyDownHandler, false);
// #endif
    window.removeEventListener("unload", this.removeListener, false);
    var observerSvc = Components.classes["@mozilla.org/observer-service;1"].
        getService(Components.interfaces.nsIObserverService);
    observerSvc.removeObserver(this, "kb-unload");
    observerSvc.removeObserver(this, "kb-unload-global");
    observerSvc.removeObserver(this, "kb-load");
    observerSvc.removeObserver(this, "kb-load-global");
    observerSvc.removeObserver(this, 'toolbox-loaded-local');
    observerSvc.removeObserver(this, 'toolbox-loaded-global');
    observerSvc.removeObserver(this, 'toolbox-loaded'); // synonym for global
    observerSvc.removeObserver(this, 'toolbox-unloaded');
    observerSvc.removeObserver(this, 'toolbox-unloaded-local');
    observerSvc.removeObserver(this, 'toolbox-unloaded-global');
 }

this.Manager.prototype.observe = function(part, topic, partId) {
    // Two notifications are observed by the keybinding manager -- kb-load and kb-unload.
    // see the notification HOWTO for details

    if (topic.indexOf('kb-') == 0) {
        if (topic.indexOf('-global') == -1
            && ko.windowManager.getMainWindow() != window) {
            return;
        } else {
            topic = topic.indexOf('kb-load') == 0 ? 'kb-load' : 'kb-unload';
        }
        if (part.hasAttribute('keyboard_shortcut')) {
            this.manageKeyboardShortcut(part, topic, partId);
        }
    } else if (topic in ['toolbox-loaded', 'toolbox-loaded-local',
                         'toolbox-loaded-global', 'toolbox-unloaded',
                         'toolbox-unloaded-local', 'toolbox-unloaded-global']) {
        var kb_notification = topic.indexOf('toolbox-loaded') == 0 ? 'kb-load' : 'kb-unload';
        var toolboxDir = partId; // actual value;
        try {
        var parts = ko.toolbox2.getToolsWithKeyboardShortcuts(toolboxDir);
        var i;
        for (part, i = 0; part = parts[i]; i++) {
            if (!part.hasAttribute('keyboard_shortcut')) {
                dump("keybindings.p.js:: Unexpected: no keyboard_shortcut for part "
                     + part.id
                     + "\n");
                continue;
            }                 
            this.manageKeyboardShortcut(part, kb_notification, part.id);
        }
        } catch(ex) {
            dump("getToolsWithKeyboardShortcuts => " + ex + "\n");
            return;
        }
    }
}

this.Manager.prototype.manageKeyboardShortcut = function(part, topic, partId) {
    var keylabels = part.getStringAttribute('keyboard_shortcut').split('###');
    var keylabel;
    var command = 'cmd_callPart';
    for (var i in keylabels) {
        keylabel = keylabels[i];
        if (keylabel != '') {
            var keysequence = keylabel.split(', ')
                if (topic == 'kb-unload') {
                    this.clearBinding(command, partId, true);
                } else {
                    this.assignKey(command, keysequence, partId);
                    this.makeKeyActive(command, keysequence);
                }
        }
    }
}

this.Manager.prototype.reloadConfigurations = function () {
    var schemes = new Array();
    this.keybindingSchemeService.getSchemeNames(schemes, new Object());
    this._knownconfigs = schemes.value;
}

this.Manager.prototype.getConfigurations = function () {
    return this._knownconfigs;
}

this.Manager.prototype.loadConfiguration = function (configName, forceReload /* = false */) {
    try {
        if (typeof(forceReload) == 'undefined') forceReload = false;
        //dump("loading from " + configName + '\n');
        /* Clear the old scheme */
        this._clearActiveBindings();
        this.clearBindings();
        /* Load the new scheme settings */
        var scheme = this.keybindingSchemeService.getScheme(configName);
        /*
         * currentConfiguration and currentScheme both need to be set before
         * parseConfiguration is called, in case the keybinding needs to
         * get saved as part of the keybinding upgrade handling.
         * http://bugs.activestate.com/show_bug.cgi?id=78316
         */
        this.currentConfiguration = configName;
        this.currentScheme = scheme;
        this.parseConfiguration(scheme.data, forceReload);
        this.activeCommands = cloneObject(this.command2key);
        this.currentPrefixMap = this.keyTree;
        this._configDirty = false;
        this._configUnsaved = false;
        this._configKeyTree = cloneObject(this.keyTree);
    } catch (e) {
        _log.exception(e);
    }
}

this.Manager.prototype.mergeSchemeConfiguration = function (configName, forceReload /* = false */) {
    try {
        if (typeof(forceReload) == 'undefined') forceReload = false;
        //dump("loading from " + configName + '\n');
        //var data = this.currentScheme.data + this.keybindingSchemeService.getScheme(configName).data;
        var data = this.keybindingSchemeService.getScheme(configName).data;
        this.parseConfiguration(data, forceReload);
        this.activeCommands = cloneObject(this.command2key);
        this.currentPrefixMap = this.keyTree;
        this._configDirty = true;
        this._configUnsaved = true;
    } catch (e) {
        _log.exception(e);
    }
}

this.Manager.prototype.removeCommandsWithPrefix = function (prefix) {
    try {
        this._clearActiveBindings();
        this.clearBindings();
        this.parseConfiguration(this.currentScheme.data, true, prefix);
        this.activeCommands = cloneObject(this.command2key);
        this.currentPrefixMap = this.keyTree;
        this._configDirty = true;
        this._configUnsaved = true;
    } catch (e) {
        _log.exception(e);
    }
}

function cloneObject(what) {
    var f = new Object();
    for (var i in what) {
        if (typeof what[i] == 'object') {
            f[i] = new cloneObject(what[i]);
        }
        else
            f[i] = what[i];
    }
    return f;
}

/**
 * Lastest keybinding version known for this version of Komodo.
 * This number needs to be changed between Komodo releases to keep
 * the keybinding files in sync as the keybinding system gets changed.
 *
 * NOTE: When you're changing currentKeybindingVersionNumber from N to N+1,
 *       in _upgradeKeybingings add a case for N (not N+1) to modify
 *       existing keybindings to move to the state you're implementing for N+1
 *
 * Version history:
 * 48: Komodo 9.3 - Ctrl+T is now used for new tabs
 * 47: Komodo 9.3 - Add keybindings for quick bookmarks
 *                  Juggle help (and friends) and commenting keybindings to
 *                  allow quick bookmarks to take their bindings.
 * 46: Komodo 9.3 - removed cmd_addAdditionalCaret
 * 41,42: Komodo 9.0.0 - add commando commands: Ctrl+Shift+K, Ctrl+Shift+O, Ctrl+<
 * 40: Komodo 9.0.0 - add Vi commands: zz z. z-
 * 39: Komodo 8.5.0b3 - add Ctrl+D for cmd_addNextWordToCaretSet
 * 38: Komodo 8.5.0b2 - ?
 * 37: Komodo 8.5.0b2 - add Crtl+Shift+Z for cmd_htmlTagRelocator
 *                      add Meta+Shift++ for cmd_fontZoomIn
 *                      fixup Meta+Shift keybindings - bug 92880.
 *                      changed cmd_jumpToMatchingBrace to Meta+Shift+M
 * 36: Komodo 8.5.0b2 - add Ctrl+K, Ctrl+Y for cmd_addAdditionalCaret
 * 34: Komodo 8.0.0a1 - add Ctrl+K, Ctrl+R for reloadBrowserPreview.
 * 33: Komodo 7.0.1 - drop Cmd++ for cmd_fontZoomIn, still conflicts with cmd_replace
 * 32: Komodo 7.0.0b2 - remove Cmd+= for font zoom, conflicts with cmd_replace.
 * 30: Komodo 7.0.0a5 - added Alt+Backspace for Default keybinding scheme.
 * 29: Komodo 7.0.0a4 - switch to incremental find for Ctrl+F/Ctrl+Shift+F
 * 28: Komodo 7.0.0a1 - Mac: add "Cmd+Shift+{" and "Cmd+Shift+}" for buffer prev/next.
 * 27: Komodo 6.1.1 - IDE only change - ignored.
 * 26: Komodo 6.1.0a1 - add cmd_tabAwarePaste (meta+ctrl+v, ctrl+alt+v)
 * 25: Komodo 6.0.0 - drop scc folder commands (IDE-only)
 * 24: Komodo 6.0.0rc1 - additional keybindings for zoom in/out commands
 * 23: Komodo 6.0.0rc1 - add keybinding for cmd_invokeTool
 * 22: Komodo 6.0.0rc1 - remapped 'cmd_viewProjects' => 'cmd_viewPlaces'
 * 21: Komodo 6.0.0b1 - add Cmd+[1..9] tab nav keybindings for Mac
 * 20: Komodo 6.0.0b1 - rejig Debug Step *, restore Fast Open binding.
 * 19: Komodo 6.0.0a2 - add a binding for cmd_viewFullScreen : ctrl-k f11
 * 18: Komodo 6.0.0a2 - add SCC checkout keybinding: ctrl-k k
 * 17: Komodo 5.2.1 - Linux: convert ctrl-shift-u to ctrl-alt-u
 * 16: Komodo 5.2.0 - Add an invoke hyperlink command.
 * 15: Komodo 5.1.0 - Fix Meta+Shift+<x> keybindings on OS X to use the
 *                    shifted char if <x> is non-alpha
 * 14: Komodo 5.1.0 - Fix cmd_goToFile keybinding on non-Mac platforms.
 * 13: Komodo 5.1.0 - Add cmd_goToFile keybinding.
 * 12: Komodo 5.1.0 - Add cmd_reopenLastClosedTab for OS X
 * 11: Komodo 5.1.0 - Add cmd_vim_jumpToLineBeforeLastJump, cmd_vim_jumpToLocBeforeLastJump
 * 10: Komodo 5.1.0 - Add cmd_reopenLastClosedTab for Windows, Linux
 * 9: Komodo 5.1.0 - Add cmd_lineSelectionOrDuplicate
 * 8: Komodo 5.1.0 - Mac: bind %[, %] to history, %{, %} to jump/sel to matching brace
 * 7: Komodo 5.1.0 - vi: add "gg" for document home command
 * 6: Komodo 5.1.0 - add alt-left and alt-right for history
 * 5: Komodo 5.0.0 (*after* 5.0.0b1)
 * 4: Komodo 4.4.0
 * 3: Komodo 4.2.1 and above
 * 2: Komodo 4.2.0-beta2 and above
 * 1: Komodo 4.2.0-beta1 and before
 */
const currentKeybindingVersionNumber = 48;

/**
 * Remove this dictionary of keybinds.
 * @private
 */
this.Manager.prototype._remove_keybinding_sequences = function (command_to_key_sequences) {
    var i;
    var j;
    var commandId;
    var currentKeyLabels;
    var keybindingLabels;

    // Find a keymatch
    for (commandId in command_to_key_sequences) {
        keybindingLabels = command_to_key_sequences[commandId];
        currentKeyLabels = this.command2keysequences(commandId);
        for (i=0; i < currentKeyLabels.length; i++) {
            for (j=0; j < keybindingLabels.length; j++) {
                if (currentKeyLabels[i] == keybindingLabels[j]) {
                    // Found a match, remove it
                    this.clearSequence(commandId, keybindingLabels[j]);
                    _log.warn("_upgradeKeybingings:: removed keybinding '" +
                              keybindingLabels + "' for command " + commandId);
                }
            }
        }
    }
}

/**
 * Add this dictionary of keybinds.
 *
 * Example map containing three commands:
 *   {
 *     "cmd_selectAll": ["Ctrl+Shift+A"]
 *     "cmd_previewBrowser": ["Ctrl+K Ctrl+V"]      // Multi-key example
 *     "cmd_dbgStepOver": ["F10", "Ctrl+K Ctrl+O"]  // 2 different keybindings
 *   }
 *
 * @private
 */
this.Manager.prototype._add_keybinding_sequences = function (command_to_key_sequences) {
    var commandId;
    var seq;
    var keybindings;
    var keybinding;
    var keysequence;

    // Find a keymatch
    for (commandId in command_to_key_sequences) {
        keybindings = command_to_key_sequences[commandId];
        for each (keybinding in keybindings) {
            // See if the keybinding we want to add is already taken
            keysequence = keylabel2keysequence(keybinding);
            var usedbys = this.usedBy(keysequence);
            if (usedbys.length > 0) {
                // Already used
                if (usedbys[0].command != commandId) {
                    _log.warn("_upgradeKeybingings:: could not add '" +
                              keybinding + "' for command " + commandId +
                              ", binding already in use by command: " +
                              usedbys[0].command);
                }
                continue;
            }
            // See if the command already has this keybinding
            seq = this.command2keysequences(commandId);
            if (seq.indexOf(keysequence) != -1) {
                // found an existing mapping
                continue;
            }
            // Not found, need to add it in
            //seq.push(keymatch);
            this.assignKey(commandId, keysequence);
            this.makeKeyActive(commandId, keysequence);
            _log.warn("_upgradeKeybingings:: added keybinding " +
                      keysequence + " for command " + commandId);
        }
    }
}

/**
 * Upgrade the keybindings between Komodo versions.
 * @private
 * @param {int} from_version  the version to upgrade from
 * @param {boolean} vi_enabled whether uses vi key keybindings
 */
this.Manager.prototype._upgradeKeybingings = function (from_version,
                                                       vi_enabled) {
    // Loop around until it's fully upgraded
    while (from_version < currentKeybindingVersionNumber) {
        switch (from_version) {
        case 1: // Handles upgrades to Komodo 4.2
            // For Komodo 4.1 and earlier (lots of versions, lots of change)
            // - remove hard coded ctrl-tab, ctrl-shift-tab, bug 67579
            // - add goto definition, change 273493
            // - remove api browser command, change 273106
            // - replace cmd_editSelectAll with cmd_selectAll, change 266837
            // - remove obsolete disk/file explorer keybinds, change 262133
            // - remove indent/dedent bindings, now hard coded, bug 45624

            // Mapping of command to the array of different keybind(s)
            // Note: Multi key handling must use ", " for key separaters!
            this._remove_keybinding_sequences({
                "cmd_codeIntelFindSymbol":   [ "Ctrl+K, Ctrl+F" ],
                "cmd_editSelectAll":         [ "Ctrl+A" ],
                "cmd_viewDocumentOutline":   [ "Ctrl+Shift+D" ],
                "cmd_documentOutlineLocateCurrentNode": [ "Ctrl+K, Ctrl+D" ],
                "cmd_viewFileExplorer":      [ "Ctrl+Shift+K" ],
                "cmd_locateInFileExplorer":  [ "Ctrl+K, Ctrl+K" ],
                "cmd_indent":                [ "Tab" ],
                "cmd_dedent":                [ "Shift+Tab" ]
            });
            this._add_keybinding_sequences({
                "cmd_bufferNextMostRecent":  [ "Ctrl+Tab" ],
                "cmd_bufferNextLeastRecent": [ "Ctrl+Shift+Tab" ],
                "cmd_goToDefinition":        [ "Ctrl+K, Ctrl+G" ],
                "cmd_selectAll":             [ "Ctrl+A" ]
            });
            if (vi_enabled) {
                // Handle the specific vi keybinds
                // - indent/dedent command changes, bug 66778
                // - fold commands, bug 66384
                // - add "S" command, bug 67053
                // - add "ZQ" and "ZZ" commands, bug 67048
                // - add set register command, change 276284
                // - add find char commands, change 275683
                // - replace operation commands with single keybinds
                this._remove_keybinding_sequences({
                    "cmd_vim_dedent":                  [ "<, <" ],
                    "cmd_vim_indent":                  [ ">, >" ],
                    "cmd_vim_yankLine":                [ "y, y" ],
                    "cmd_vim_yankWord":                [ "y, w" ],
                    "cmd_vim_changeWord":              [ "c, w" ],
                    "cmd_vim_changeLine":              [ "c, c" ],
                    "cmd_vim_changeLineBegin":         [ "c, 0" ],
                    "cmd_vim_changeLineEnd":           [ "c, $" ],
                    "cmd_vim_cutChar":                 [ "d, l" ],
                    "cmd_vim_cutCharLeft":             [ "d, h" ],
                    "cmd_vim_cutWordLeft":             [ "d, b" ],
                    "cmd_vim_cutWordRight":            [ "d, w" ],
                    "cmd_vim_cutToWordEnd":            [ "d, e" ],
                    "cmd_vim_lineCut":                 [ "d, d" ],
                    "cmd_vim_lineCutEnd":              [ "d, $" ],
                    "cmd_vim_deleteToDocumentEnd":     [ "d, G" ]
                });
                this._remove_keybinding_sequences({
                    "cmd_vim_changeWord":              [ "c, e" ]
                });
                this._add_keybinding_sequences({
                    "cmd_vim_dedentOperation":         [ "<" ],
                    "cmd_vim_indentOperation":         [ ">" ],
                    "cmd_foldExpand":                  [ "z, o" ],
                    "cmd_foldExpandAll":               [ "z, R" ],
                    "cmd_foldCollapse":                [ "z, c" ],
                    "cmd_foldCollapseAll":             [ "z, M" ],
                    "cmd_foldToggle":                  [ "z, a" ],
                    "cmd_vim_changeLine":              [ "S" ],
                    "cmd_vim_saveAndClose":            [ "Z, Z" ],
                    "cmd_vim_closeNoSave":             [ "Z, Q" ],
                    "cmd_vim_setRegister":             [ "\"" ],
                    "cmd_vim_findCharInLinePosBefore":          [ "t" ],
                    "cmd_vim_findPreviousCharInLinePosAfter":   [ "T" ],
                    "cmd_vim_repeatLastFindCharInLine":         [ ";" ],
                    "cmd_vim_repeatLastFindCharInLineReversed": [ "," ],
                    "cmd_vim_yankOperation":           [ "y" ],
                    "cmd_vim_changeOperation":         [ "c" ],
                    "cmd_vim_deleteOperation":         [ "d" ],
                    "cmd_vim_findWordUnderCursorBack": [ "#" ],
                    "cmd_vim_toggleVisualMode":        [ "v" ],
                    "cmd_vim_toggleVisualLineMode":    [ "V" ],
                    "cmd_vim_toggleVisualBlockMode":   [ "Ctrl+V" ],
                    "cmd_goToDefinition":              [ "Ctrl+K, Ctrl+g" ]
                });
            } else {
                // vi not enabled, do some cleanup of lowercase vi bindings
                // that got into the standard keybinding set in the
                // Komodo 4.0.x builds.
                // http://bugs.activestate.com/show_bug.cgi?id=70704
                this._remove_keybinding_sequences({
                    "cmd_refreshStatus":               [ "Ctrl+K, r" ],
                    "cmd_SCCedit":                     [ "Ctrl+K, e" ],
                    "cmd_SCCremove":                   [ "Ctrl+K, o" ],
                    "cmd_SCCdiff":                     [ "Ctrl+K, d" ],
                    "cmd_SCChistory":                  [ "Ctrl+K, h" ],
                    "cmd_SCCrevert":                   [ "Ctrl+K, v" ],
                    "cmd_SCCupdate":                   [ "Ctrl+K, u" ],
                    "cmd_SCCadd":                      [ "Ctrl+K, a" ],
                    "cmd_SCCcommit":                   [ "Ctrl+K, c" ]
                });
            }
            break;
        case 2: // Handles upgrades from Komodo 4.2.0 to 4.2.1+
            if (vi_enabled) {
                // Handle the specific vi keybinds
                // - scroll commands, bug 73301
                this._remove_keybinding_sequences({
                    "cmd_vim_lineScrollUp":            [ "Ctrl+P" ]
                });
                this._add_keybinding_sequences({
                    "cmd_vim_lineScrollUp":            [ "Ctrl+Y" ],
                    "cmd_vim_scrollHalfPageUp":        [ "Ctrl+U" ],
                    "cmd_vim_scrollHalfPageDown":      [ "Ctrl+D" ]
                });
            }
            break;
        case 3:
            // No changes for OpenKomodo
            break;
        case 4:
            // No changes for OpenKomodo
            break;
        case 5:
// #if PLATFORM != 'darwin'
            // History added in keybindings version 7
            this._remove_keybinding_sequences({
                "cmd_wordPartLeft":   [ "Alt+Left" ],
                "cmd_wordPartRight":  [ "Alt+Right" ]
            });
            this._add_keybinding_sequences({
                "cmd_historyBack":    [ "Alt+Left" ],
                "cmd_historyForward": [ "Alt+Right" ]
            });
// #else
            this._remove_keybinding_sequences({
                "cmd_wordPartLeft":   [ "Meta_Alt+Left" ],
                "cmd_wordPartRight":  [ "Meta+Alt+Right" ]
            });
            this._add_keybinding_sequences({
                "cmd_historyBack":    [ "Meta+Alt+Left" ],
                "cmd_historyForward": [ "Meta+Alt+Right" ]
            });
            break;
// #endif
        case 6:
            if (vi_enabled) {
                this._add_keybinding_sequences({
                    "cmd_vim_documentHome":    [ "g, g" ]
                });
            }
            break;
// #if PLATFORM == 'darwin'
        case 7:
            this._remove_keybinding_sequences({
                "cmd_historyBack":    [ "Meta+Alt+Left" ],
                "cmd_historyForward": [ "Meta+Alt+Right" ],
                "cmd_jumpToMatchingBrace": ["Meta+]" ],
                "cmd_selectToMatchingBrace": ["Meta+Shift+]" ]
            });
            this._add_keybinding_sequences({
                "cmd_historyBack":    [ "Meta+[" ],
                "cmd_historyForward": [ "Meta+]" ],
                "cmd_jumpToMatchingBrace": ["Meta+{" ],
                "cmd_selectToMatchingBrace": ["Meta+}" ]
            });
            break;
// #endif
        case 8:
            if ('cmd_lineDuplicate' in this.command2key) {
                var keys = this.command2key['cmd_lineDuplicate'].concat([]);
                // Copy the array because
                // this.command2key['cmd_lineDuplicate']
                // is mutable.
                this._remove_keybinding_sequences({
                    'cmd_lineDuplicate': keys
                });
                this._add_keybinding_sequences({
                    'cmd_lineOrSelectionDuplicate': keys
                });
            }
            break;

        case 9:
// #if PLATFORM != 'darwin'
            this._remove_keybinding_sequences({
                'cmd_viewToolbox': ["Ctrl+Shift+T"]
            });
            this._add_keybinding_sequences({
                'cmd_viewToolbox': ["Ctrl+Shift+L"],
                'cmd_reopenLastClosedTab': ["Ctrl+Shift+T"]
            });
// #endif
            break;

        case 10:
            if (vi_enabled) {
                this._add_keybinding_sequences({
                    "cmd_vim_jumpToLineBeforeLastJump": [ "', '"],
                    "cmd_vim_jumpToLocBeforeLastJump": [ "`, `"]
                });
            }
            break;
        
        case 11:
// #if PLATFORM == 'darwin'
            this._remove_keybinding_sequences({
                'cmd_viewToolbox': ["Ctrl+Shift+T"],
                'cmd_dbgStepOut': ["Meta+Shift+T"]
            });
            this._add_keybinding_sequences({
                'cmd_viewToolbox': ["Ctrl+Shift+L"],
                'cmd_dbgStepOut': ["Ctrl+Shift+T"],
                'cmd_reopenLastClosedTab': ["Meta+Shift+T"]
            });
// #endif
            break;

        case 12:
// #if PLATFORM == 'darwin'
            this._remove_keybinding_sequences({
                'cmd_viewBottomPane': ["Meta+Shift+O"]
            });
            this._add_keybinding_sequences({
                'cmd_viewBottomPane': ["Meta+Shift+M"],
                'cmd_goToFile': ["Meta+Shift+O"]
            });
// #else
            this._remove_keybinding_sequences({
                'cmd_viewBottomPane': ["Ctrl+Shift+O"]
            });
            this._add_keybinding_sequences({
                'cmd_viewBottomPane': ["Ctrl+Shift+M"],
                'cmd_reopenLastClosedTab': ["Ctrl+Shift+O"]
            });
// #endif
            break;
        case 13:
// #if PLATFORM != 'darwin'
            // Got the keybinding wrong for this in the last upgrade (v.12),
            // fix it up now.
            this._remove_keybinding_sequences({
                'cmd_reopenLastClosedTab': ["Ctrl+Shift+O"]
            });
            this._add_keybinding_sequences({
                'cmd_goToFile': ["Ctrl+Shift+O"]
            });
// #endif
            break;
        case 14:
// #if PLATFORM == 'darwin'
            this._remove_keybinding_sequences({
                'cmd_fontZoomIn': ["Meta+Shift+="],
                'cmd_fontZoomOut': ["Meta+Shift+-"],
                'cmd_splittab': ["Meta+Shift+'"],
                'cmd_viewEOL': ["Meta+Shift+7"],
                'cmd_viewIndentationGuides': ["Meta+Shift+5"],
                'cmd_viewWhitespace': ["Meta+Shift+8"],
                'cmd_wordWrap': ["Meta+Shift+9"]
            });
            this._add_keybinding_sequences({
                'cmd_fontZoomIn': ["Meta++"],
                'cmd_fontZoomOut': ["Meta+_"],
                'cmd_splittab': ["Meta+\""],
                'cmd_viewEOL': ["Meta+&"],
                'cmd_viewIndentationGuides': ["Meta+%"],
                'cmd_viewWhitespace': ["Meta+*"],
                'cmd_wordWrap': ["Meta+("]
            });
// #endif
            break;
        case 15:
            // Add hyperlink command.
// #if PLATFORM == 'darwin'
            this._add_keybinding_sequences({
                'cmd_invokeHyperlink': ["Meta+Shift+G"]
            });
// #else
            this._add_keybinding_sequences({
                'cmd_invokeHyperlink': ["Ctrl+Shift+G"]
            });
// #endif
            break;
        case 16:
            // Bug 80230, finishing change to Default.p.kkf in r29983
// #if PLATFORM == 'linux'
            this._remove_keybinding_sequences({
                'cmd_convertLowerCase': ["Ctrl+Shift+U"]
            });
            this._add_keybinding_sequences({
                'cmd_convertLowerCase': ["Ctrl+Alt+U"]
            });
// #endif
            break;
        case 17:
            // No changes for OpenKomodo
            break;
        case 18:
// #if PLATFORM != 'darwin'
            this._add_keybinding_sequences({
                'cmd_viewFullScreen': ["Ctrl+K, F11"]
            });
// #endif
            break;
        case 19:
// #if PLATFORM == 'darwin'
            this._remove_keybinding_sequences({
                'cmd_openProject': ["Meta+Ctrl+O"]
            });
            this._add_keybinding_sequences({
                'cmd_openProject': ["Ctrl+Shift+O"]
            });
// #endif
            break;
        case 20:
// #if PLATFORM == 'darwin'
            this._add_keybinding_sequences({
                'cmd_buffer1': ["Meta+1"],
                'cmd_buffer2': ["Meta+2"],
                'cmd_buffer3': ["Meta+3"],
                'cmd_buffer4': ["Meta+4"],
                'cmd_buffer5': ["Meta+5"],
                'cmd_buffer6': ["Meta+6"],
                'cmd_buffer7': ["Meta+7"],
                'cmd_buffer8': ["Meta+8"],
                'cmd_buffer9': ["Meta+9"]
            });
// #endif
            break;
        case 21:
            // Remap the Project keybindings to Places.
            this._remove_keybinding_sequences({
                'cmd_viewProjects': ["Ctrl+Shift+P"]
            });
            this._add_keybinding_sequences({
                'cmd_viewPlaces': ["Ctrl+Shift+P"]
            });
            break;
        case 22:
// #if PLATFORM == 'darwin'
            this._add_keybinding_sequences({
                'cmd_invokeTool': ["Meta+Shift+K"]
            });
// #else
            this._add_keybinding_sequences({
                'cmd_invokeTool': ["Ctrl+Shift+K"]
            });
// #endif
            break;
        case 23:
// #if PLATFORM == 'darwin'
            this._add_keybinding_sequences({
                'cmd_fontZoomIn' : ["Meta+="],
                'cmd_fontZoomOut': ["Meta+-"],
                'cmd_fontZoomReset': ["Meta+0"]
            });
// #else
            this._add_keybinding_sequences({
                'cmd_fontZoomIn' : ["Ctrl++"],
                'cmd_fontZoomOut': ["Ctrl+-"],
                'cmd_fontZoomReset': ["Ctrl+0"]
            });
            this._add_keybinding_sequences({
                'cmd_fontZoomIn' : ["Ctrl+="]
            });
// #endif
            break;
        case 25:
            this._add_keybinding_sequences({
// #if PLATFORM == 'darwin'
                'cmd_tabAwarePaste' : ["Meta+Ctrl+V"]
// #else
                'cmd_tabAwarePaste' : ["Ctrl+Alt+V"]
// #endif
            });
            break;
        case 27:
// #if PLATFORM == 'darwin'
            this._add_keybinding_sequences({
                'cmd_bufferPrevious' : ["Meta+Shift+{"],
                'cmd_bufferNext' : ["Meta+Shift+}"]
            });
// #endif
            break;
        case 28:
// #if PLATFORM == 'darwin'
            this._remove_keybinding_sequences({
                'cmd_find': ["Meta+F"],
            })
            this._add_keybinding_sequences({
                'cmd_startIncrementalSearch' : ["Meta+F"]
            });
// #else
            this._remove_keybinding_sequences({
                'cmd_find': ["Ctrl+F"]
            })
            this._add_keybinding_sequences({
                'cmd_startIncrementalSearch' : ["Ctrl+F"]
            });
// #endif
            break;
        case 29:
// #if PLATFORM != 'darwin'
            this._add_keybinding_sequences({
                'cmd_undo' : ["Alt+Backspace"]
            });
// #endif
            break;
        case 31:
// #if PLATFORM == 'darwin'
            this._remove_keybinding_sequences({
                'cmd_fontZoomIn' : ["Meta+="],
            });
// #endif
            break;
        case 32:
// #if PLATFORM == 'darwin'
            this._remove_keybinding_sequences({
                'cmd_fontZoomIn': ["Meta++"],
            });
// #endif
            break;
        case 33:
            this._add_keybinding_sequences({
                'cmd_reloadBrowserPreview': ["Ctrl+K, Ctrl+R"],
            });
            break;
        case 34:
            if ( ! vi_enabled) {
// #if PLATFORM == 'darwin'
                this._remove_keybinding_sequences({
                    'cmd_wordRight': ["Alt+Right"],
                });
                this._remove_keybinding_sequences({
                    'cmd_selectWordRight': ["Alt+Shift+Right"],
                });
                this._add_keybinding_sequences({
                    'cmd_endOfWord': ["Alt+Right"],
                });
                this._add_keybinding_sequences({
                    'cmd_endOfWordExtend': ["Alt+Shift+Right"],
                }); 
// #endif
            }
            break;
        case 35:
            this._add_keybinding_sequences({
                    'cmd_addAdditionalCaret': ["Ctrl+K, Ctrl+Y"],
                });
            break;        
        case 36:
// #if PLATFORM == 'darwin'
            this._remove_keybinding_sequences({
                'cmd_dbgGo' :                  ["Meta+>"],
                'cmd_dbgGo' :                  ["Meta+Shift+."],
                'cmd_jumpToMatchingBrace' :    ["Meta+{"],
                'cmd_selectToMatchingBrace' :  ["Meta+}"],
                'cmd_splittab' :               ['Meta+"'],
                'cmd_viewEOL' :                ["Meta+&"],
                'cmd_viewIndentationGuides' :  ["Meta+%"],
                'cmd_viewWhitespace' :         ["Meta+*"],
                'cmd_wordWrap' :               ["Meta+("],
            });
// #endif
            this._add_keybinding_sequences({
// #if PLATFORM == 'darwin'
                'cmd_fontZoomIn' :             ["Meta+Shift++"],
                'cmd_dbgGo' :                  ["Meta+Shift+>"],
                'cmd_splittab' :               ['Meta+Shift+"'],
                'cmd_viewEOL' :                ["Meta+Shift+&"],
                'cmd_viewIndentationGuides' :  ["Meta+Shift+%"],
                'cmd_viewWhitespace' :         ["Meta+Shift+*"],
                'cmd_wordWrap' :               ["Meta+Shift+("],
                'cmd_jumpToMatchingBrace' :    ["Meta+Shift+M"],
// #endif
                'cmd_htmlTagRelocator' : ["Ctrl+Shift+Z"],
            });
            break;
        case 38:
            this._add_keybinding_sequences({
                    'cmd_addNextWordToCaretSet': ["Ctrl+D"],
                });
            break;
        case 39:
            if (vi_enabled) {
                this._add_keybinding_sequences({
                        'cmd_vim_scrollLineToCenter':     ["z, z"],
                        'cmd_vim_scrollLineToCenterHome': ["z, ."],
                        'cmd_vim_scrollLineToBottomHome': ["z, -"],
                });
            }
            break;
        case 42:
// #if PLATFORM != 'darwin'
            this._remove_keybinding_sequences({
                "cmd_goToFile":       [ "Ctrl+Shift+O" ],
                "cmd_invokeTool":     [ "Ctrl+Shift+K" ]
            });
            this._add_keybinding_sequences({
                "cmd_scope-combined-toolscmds": [ "Ctrl+Shift+K" ],
                "cmd_scope-files":              [ "Ctrl+Shift+O" ],
                "cmd_scope-openfiles":          [ "Ctrl+<" ]
            });
// #else
            this._remove_keybinding_sequences({
                "cmd_goToFile":       [ "Meta+Shift+O" ],
                "cmd_invokeTool":     [ "Meta+Shift+K" ]
            });
            this._add_keybinding_sequences({
                "cmd_scope-combined-toolscmds": [ "Meta+Shift+K" ],
                "cmd_scope-files":              [ "Meta+Shift+O" ],
                "cmd_scope-openfiles":          [ "Meta+<" ]
            });
// #endif
            break;
        case 46:
            this._remove_keybinding_sequences({
                'cmd_addAdditionalCaret': ["Ctrl+K, Ctrl+Y"],
            });
            break;
        case 47:
// #if PLATFORM != 'darwin'
            this._remove_keybinding_sequences({
                'cmd_comment':  ["Ctrl+3"],
                'cmd_uncomment':["Ctrl+2"],
                'cmd_uncomment':["Ctrl+Shift+3"],
                'cmd_viewIndentationGuides': ['Ctrl+Shift+5'],
                'cmd_viewLineNumbers': ['Ctrl+Shift+4'],
                'cmd_viewEOL': ['Ctrl+Shift+7'],
                'cmd_viewWhitespace': ['Ctrl+Shift+8'],
                'cmd_wordWrap': ['Ctrl+Shift+5'],
                'cmd_viewIndentationGuides': ['Ctrl+Shift+9'],
            });
            this._add_keybinding_sequences({
                'cmd_comment':  ["Ctrl+/"],
                'cmd_uncomment':["Ctrl+Shift+?"]
            });
// #else
            this._remove_keybinding_sequences({
                'cmd_comment':  ["Ctrl+3"],
                'cmd_uncomment':["Ctrl+2"],
                'cmd_uncomment':["Ctrl+Shift+3"],
                'cmd_helpHelp': ['Meta+?'],
                'cmd_helpHelp': ['Meta+Shift+/'],
                'cmd_helpLanguage': ['Meta+/'], // In favourite of new internal docs
                'cmd_helpLanguageAlternate':  ['Ctrl+/']
            });
            this._add_keybinding_sequences({
                'cmd_comment':  ["Meta+/"],
                'cmd_uncomment':["Meta+Shift+?"],
                'cmd_helpHelp': ['Ctrl+/']
            });
// #endif
            this._add_keybinding_sequences({
                'cmd_goToQuickBookmark_0':  ['Ctrl+0'],
                'cmd_goToQuickBookmark_1':  ['Ctrl+1'],
                'cmd_goToQuickBookmark_2':  ['Ctrl+2'],
                'cmd_goToQuickBookmark_3':  ['Ctrl+3'],
                'cmd_goToQuickBookmark_4':  ['Ctrl+4'],
                'cmd_goToQuickBookmark_5':  ['Ctrl+5'],
                'cmd_goToQuickBookmark_6':  ['Ctrl+6'],
                'cmd_goToQuickBookmark_7':  ['Ctrl+7'],
                'cmd_goToQuickBookmark_8':  ['Ctrl+8'],
                'cmd_goToQuickBookmark_9':  ['Ctrl+9'],
                'cmd_setQuickBookmark_0':  ['Ctrl+Shift+0'],
                'cmd_setQuickBookmark_1':  ['Ctrl+Shift+1'],
                'cmd_setQuickBookmark_2':  ['Ctrl+Shift+2'],
                'cmd_setQuickBookmark_3':  ['Ctrl+Shift+3'],
                'cmd_setQuickBookmark_4':  ['Ctrl+Shift+4'],
                'cmd_setQuickBookmark_5':  ['Ctrl+Shift+5'],
                'cmd_setQuickBookmark_6':  ['Ctrl+Shift+6'],
                'cmd_setQuickBookmark_7':  ['Ctrl+Shift+7'],
                'cmd_setQuickBookmark_8':  ['Ctrl+Shift+8'],
                'cmd_setQuickBookmark_9':  ['Ctrl+Shift+9'],
            });
            break;
        case 48:
// #if PLATFORM != 'darwin'
            this._remove_keybinding_sequences({
                'cmd_expandAbbrev':  ["Meta+T"]
            });
            this._add_keybinding_sequences({
                'cmd_newTab':  ["Meta+T"]
            });
// #else
            this._remove_keybinding_sequences({
                'cmd_expandAbbrev':  ["Ctrl+T"]
            });
            this._add_keybinding_sequences({
                'cmd_newTab':  ["Ctrl+T"]
            });
// #endif
            break;
        }
        from_version += 1;
    }
}

/**
 * Parse the keybinding configuration file data into commands.
 * Acitivate the keybinding commands.
 */
this.Manager.prototype.parseConfiguration = function (data,
                                                      forceReload /* =false */,
                                                      ignoreCommandPrefix /* =null */) {
    // Type check the arguments
    if (typeof(forceReload) == 'undefined') forceReload = true; // false; XXX
    if (typeof(ignoreCommandPrefix) == 'undefined') ignoreCommandPrefix = null;

    var i;
    var line;
    var lines = data.split('\n');
    var onlywhitespace = /^\s*$/;
    var version = 1; // Used to determine if the scheme needs to be upgraded

    // Find out if we are binding keys, or if we've gotten our keybindings using
    // the Mozilla persist mechanism
    var keyset = this.document.getElementById('widekeyset');
    var bindingKeys = true;
    var vi_enabled = false;
    //if (!forceReload && keyset.hasAttribute('persisted_kb') && keyset.getAttribute('persisted_kb') == 'true') {
    //    _log.info("Binding Keys is false - we got them from persisted XUL");
    //    bindingKeys = false;
    //} else {
    //    _log.info("Binding Keys is true - we're doing it ourselves");
    //}
    onlywhitespace = onlywhitespace.compile(/^\s*$/); // this seems clumsy, but appears to be the syntax required??
    var iscomment = new RegExp(/^\s*#.*$/);
    for (i in lines) {
        line = lines[i];
        //dump("looking at: " + line +'\n');
        if (iscomment.test(line) || onlywhitespace.test(line)) continue;
        var re = /(\w+)\s+(.*)\s*$/;  // Two groups - 'kind' and 'rest', separated by whitespace
        var groups = re.exec(line);
        var desc;
        var commandId;
        var keysequence;
        switch (groups[1]) {
            case 'version':
                version = parseInt(groups[2]);
                //dump("Keybindings version: " + version + "\n");
                if ((version < 1) ||
                    (version > currentKeybindingVersionNumber)) {
                    _log.warn("unknown version number: " + version +
                              " -- continuing anyway");
                    // Assume it's the current version then, it's likely a
                    // newer version keybinding scheme, thus we don't want
                    // to change it.
                    version = currentKeybindingVersionNumber;
                }
                break;
            case 'binding':
                //dump("found a binding"+ line +'\n');
                desc = groups[2].replace(/\s*$/, ''); // rstrip
                var parts = desc.split(/\s+/);
                commandId = parts[0];
                if (ignoreCommandPrefix &&
                    commandId.substr(0, ignoreCommandPrefix.length) == ignoreCommandPrefix) {
                    // We need to ignore this command
                    continue;
                }
                if (!vi_enabled && commandId.indexOf('cmd_vim') == 0) {
                    vi_enabled = true;
                }
                keysequence = parts.splice(1, parts.length);

                //dump("command = " + commandId + " bound to key sequence " + keysequence + '\n');
                // Note that keysequences can have spaces in the case of multi-key sequences -- e.g. "Ctrl-X Ctrl-C"
                var usedbys = this.usedBy(keysequence);
                if (usedbys.length > 0) {
                    _log.warn("["+keysequence+"] was used for '" +
                              usedbys[0].command + "', overriding to use '" +
                              commandId + "'");
                }
                this.assignKey(commandId, keysequence);
                if (bindingKeys) {
                    this.makeKeyActive(commandId, keysequence);
                }
                break;
            case 'parambinding':
                // Now we're dealing with a "parametrized" keybinding
                desc = groups[2].replace(/\s*$/, ''); // rstrip
                var firstQuote = desc.indexOf('"');
                var lastQuote = desc.lastIndexOf('"');
                commandId = desc.slice(0, firstQuote).replace(/\s*$/, '');
                var parameter = desc.slice(firstQuote+1, lastQuote);
                keysequence = desc.slice(lastQuote+1, desc.length).replace(/^\s*/, '').split(/\s+/);
                var usedbys = this.usedBy(keysequence);
                if (usedbys.length > 0) {
                    _log.warn("parambinding ["+keysequence+"] already in use by:" + usedbys[0].command);
                }
                this.assignKey(commandId, keysequence, parameter);
                if (bindingKeys) {
                    this.makeKeyActive(commandId, keysequence);
                }
                break;
            default:
                _log.warn("Unknown command in keybinding configuration:" + groups[1]);

        }
    }

    if (bindingKeys) {
        _log.info("setting persisted_kb to true!");
        keyset.setAttribute('persisted_kb', 'true');
    }

    // Check if we need to upgrade the keybindings
    if (version < currentKeybindingVersionNumber) {
        _log.warn("Upgrading keybindings from version: " + version +
                  " to " + currentKeybindingVersionNumber);
        // Upgrade it
        this._upgradeKeybingings(version, vi_enabled);
        // Save it, so we don't have to upgrade it again
        this.saveCurrentConfiguration();
    }

    // Ensure vi emulation is (un)loaded
    gVimController.enable(vi_enabled);
}

this.Manager.prototype.learnParameter = function (commandId, parameter, keylabel) {
    // Parameters are the parameters to "parametrized commands" -- i.e. those that require an argument
    // used in cmd_callPart
    if (!(commandId in this._commandParams)) {
        this._commandParams[commandId] = {};
    }
    //dump("Associating parameter " + parameter + " for " + commandId + " with " + keylabel +'\n');
    this._commandParams[commandId][keylabel] = parameter;
}

this.Manager.prototype._configKnown= function (newconfigname) {
    for (var i in this._knownconfigs) {
        if (this._knownconfigs[i] == newconfigname) return true;
    }
    return false;
}

this.Manager.prototype.makeNewConfiguration = function (newconfigname, prefset) {
    try {
        this.prefset = prefset;
        var alreadyExists = this._configKnown(newconfigname);
        if (alreadyExists) {
            var question = "The configuration \""+newconfigname+"\" is "+
                           "already defined.  Do you wish to overwrite the "+
                           "existing configuration?";
            if (ko.dialogs.yesNo(question) == "No") { // we bail
                return '';
            }
        } else {
            this._knownconfigs.push(newconfigname);
        }
        this.currentConfiguration = newconfigname;
        this.currentScheme = this.currentScheme.clone(newconfigname);
        this._configDirty = true;
        this._configUnsaved = true;
    } catch (e) {
        _log.exception(e);
    }
    return newconfigname;
}

this.Manager.prototype.deleteConfiguration = function (configname, prefset) {
    try {
        if (! this._configKnown(configname)) {
            alert("Error deleting configuration: " + configname);
            _log.error('KeybindingManager: Attempting to delete unknown configuration: ' + configname);
            return;
        }
        // Remove the configuration from the list of known configurations
        for (var i = this._knownconfigs.length-1; i > 0; i--) {
            if (this._knownconfigs[i] == configname) {
                this._knownconfigs.splice(i,1);
                break;
            }
        }
        this.prefset = prefset
        // Remove the preference
        this.prefset.deletePref(configname);
        var scheme = this.keybindingSchemeService.getScheme(configname);
        try {
            scheme.remove();
        } catch (e) {
            alert("Error removing scheme: " + e);
        }
        var schemes = new Array();
        this.keybindingSchemeService.getSchemeNames(schemes, new Object());
        this._knownconfigs = schemes.value;

        this._configDirty = false; // it's gone, but clean!
        // XXX - switchConfiguration only takes one argument!?
        this.switchConfiguration(this._knownconfigs[0], prefset);
        // Reset the pref corresponding to the set of known configurations
        this._saveKnownConfigs();
    } catch (e) {
        _log.exception(e);
    }
}

this.Manager.prototype.makeDirty= function() {
    this._configDirty = true;
}

this.Manager.prototype.saveCurrentConfiguration = function() {
    if (!this.configurationWriteable(this.currentConfiguration)) {
        return;  // We don't bother saving factory default configs.
    }
    // include the keybinding version number, needed for upgrade capabilities
    var lines = ["version " + currentKeybindingVersionNumber];
    var label, param, keydata;
    for (var commandname in this.command2key) {
        if (commandname in this._commandParams) {
            /*
            Parametrized commands shouldn't be saved -- they are only used in extra-scheme bindings
            such as toolbox and project items.

            for (label in this._commandParams[commandname]) {
                param = '"' + this._commandParams[commandname][label].replace('"', '\\"', 'g') +'"';
                text = text.concat('parambinding ' + commandname + ' ' + param + ' ' + label.replace(', ', ' ', 'g') + '\n');
            }
            */
        } else {
            keydata = this.command2key[commandname];
            for (var i = 0; i < keydata.length; i++) {
                label = keydata[i];
                //dump("saving: commandname = " + commandname + " label = " +
                //     label + '\n');
                lines.push('binding ' + commandname + ' ' +
                           label.replace(', ', ' ', 'g'));
            }
        }
    }
    this.currentScheme.data = lines.join("\n");
    this.currentScheme.save();
    this._configDirty = false;
}

this.Manager.prototype.configurationWriteable = function(configname) {
    var scheme = this.keybindingSchemeService.getScheme(configname);
    return scheme.writeable;
}

function isAssociativeArray(obj) {
    return ((typeof(obj) == 'object') && (typeof(obj.length) == 'undefined'));
}

function isArray(obj) {
    return ((typeof(obj) == 'object') && (typeof(obj.length) == 'number'));
}

this.Manager.prototype.applyCurrentConfiguration = function() {
    this.walk_and_apply(this.keyTree, []);
}

this.Manager.prototype.walk_and_apply = function(root, keysequence) {
    // walk the prefixTree, calling makeKeyActive each time
    for (var leaf in root) {
        //dump("leaf = " + leaf +'\n');
        switch (typeof(root[leaf])) {
            case 'string':
                // XXX To review when layered commands are in
                keysequence.push(leaf);
                //if (keysequence) {
                //    dump("making active " + root[leaf] + ': ' + keysequence +'\n');
                //}
                this.makeKeyActive(root[leaf], keysequence);
                keysequence.pop();
                break;
            case 'object':
                if (isAssociativeArray(root[leaf])) {
                    //dump("found tree under " + leaf + '\n');
                    keysequence.push(leaf);
                    this.walk_and_apply(root[leaf], keysequence);
                    keysequence.pop();
                    break;
                }
                // fall through
            default:
                //dump("found a " + typeof(root[leaf]) + ' for ' + leaf +'\n');
                break;
        }
    }
}

this.Manager.prototype._clearActiveBindings= function() {
    if (! this.activeCommands) {
        //dump("null activeCommands\n");
        return;
    }
    //dump("********* clearActiveBindings called \n");
    //dump("activeCommands = " + this.activeCommands + '\n');
    for (var command in this.activeCommands){
        //dump("CLEARING " + command +'\n');
        this.clearBinding(command, false);
    }
    this.activeCommands = null;
}

this.Manager.prototype.revertToPref = function(configname) {
    if (this._configUnsaved) {
        var configs = this._knownconfigs;
        this._knownconfigs = []
        for (var i = 0; i < configs.length; i++) {
            if (configs[i] != this.currentConfiguration) {
                this._knownconfigs.push(configs[i]);
            }
        }
    }
    this.prefset.setStringPref('keybinding-scheme', configname);
    this.currentConfiguration = configname;
    this.currentScheme = this.keybindingSchemeService.getScheme(this.currentConfiguration);
    this.loadConfiguration(this.currentConfiguration);
    ko.toolbox2.applyKeybindings(); 
}

this.Manager.prototype.saveAndApply = function(prefset) {
    try {
        var keybindings = '';
        var i, keybinding;
        this.prefset = prefset;
        if (prefset.getStringPref('keybinding-scheme') != this.currentConfiguration) {
            prefset.setStringPref('keybinding-scheme', this.currentConfiguration);
        }
        if ( ! ko.windowManager.lastWindow()) {
            ko.dialogs.alert(_bundle.GetStringFromName("restartRequiredAfterKeybindingChange"),
                             null, null, // text, title
                             "reboot_after_changing_keybindings" // doNotAskPref
                             );
        }
        this.saveCurrentConfiguration();
        this._saveKnownConfigs();
        this.loadConfiguration(this.currentConfiguration, true);
        ko.toolbox2.applyKeybindings(); 
    } catch (e) {
        _log.exception(e);
    }
}

this.Manager.prototype._saveKnownConfigs = function() {
    var keybinding;
    var keybindings = '';
    for (var i in this._knownconfigs) {
        keybinding = this._knownconfigs[i];
        keybindings += keybinding +'\n';
    }
    if (keybindings) {
        this.prefset.setStringPref('keybindings', keybindings);
        //dump('saving : keybindings -> ' + keybindings +'\n');
    } else {
        _log.error("Tried to save empty keybindings pref!");
    }
}

// On switching of configuration names, check to see if current configuration needs to be saved

this.Manager.prototype.offerToSave= function () {
    if (this._configDirty
        && ko.dialogs.yesNo("Changes to the current keyboard configuration have "
                        +"not been saved yet.  Do you wish to save them?")
           == "Yes"
       )
    {
        this.saveCurrentConfiguration();
    }
}

this.Manager.prototype.switchConfiguration= function (newconfigname) {
    if (newconfigname == this.currentConfiguration) return true; // Nothing to do
    if (!this._configKnown(newconfigname)) {
        alert("Unknown Keyboard configuration: " + newconfigname);
        _log.error("Unknown Keyboard configuration: " + newconfigname);
        return false;
    }
    this.offerToSave()
    try {
        this.loadConfiguration(newconfigname, true);
        ko.toolbox2.applyKeybindings(); 
    } catch (e) {
        _log.error(e);
    }
    return true;
    //dump("switched to " + this.currentConfiguration+'\n');
}

this.Manager.prototype.clearBindings = function () {
    this.keyTree = {};  // a sequence of key sequences
    this.command2key = {};  // a hash between commands and keys
    this.key2command = {};  // a hash from key to command
    this.activeCommands = {};
}

this.Manager.prototype.command2keylabel = function (commandId) {
    var seq = this.command2keysequences(commandId);
    return keysequence2keylabel(seq);
}

function keysequence2keylabel(keysequence) {
    if (!isArray(keysequence)) {
        _log.error("keysequence2keylabel has to be called with a sequence of key labels\n");
    }
    var keyname = '';
    var part;
    var i;
    for (i in keysequence) {
        part = keysequence[i];
        if (part[part.length-1] == '') part += '+';  // e.g. Ctrl--
        if (i == 0) keyname = part;
        else keyname += ', ' + part;
        //dump("part = " + part + '\n');
    }
    return keyname
}
this.keysequence2keylabel = keysequence2keylabel;

function keylabel2keysequence(keylabel) {
    if (typeof(keylabel) != 'string') {
        _log.error("keylabel2keysequence should be caled with a string, not with a " + typeof(keylabel) + " such as " + keylabel)
    }
    // Allows both "Ctrl+K, Ctrl+V" and "Ctrl+K Ctrl+V" formats.
    return keylabel.replace(', ', ' ', 'g').split(' ');
}
this.keylabel2keysequence = keylabel2keysequence;

this.Manager.prototype.getKey = function(keyname) {
    //_log.info("doing getKey for " + keyname);
    // XXX consider using this.key etc. to avoid creation of 4 variables on each key assignment.
    // This function is called once for each key binding at startup -- it should be as fast as possible.
    var oldkey = this.document.getElementById(keyname);
    if (oldkey) {
        //_log.debug("found old key with right id!");
        return oldkey;
    }
    if (keyname[keyname.length-1] == ',') {
	keyname = keyname.slice(0,keyname.length-1);
    }
    oldkey = this.document.getElementById(keyname);
    if (oldkey) {
        //_log.debug("found old key with right id!");
        return oldkey;
    }
    //_log.warn("unknown key for keyname:" + keyname)
    return null;
}

function dumpKey(key) {
    var i;
    dump('<key ');
    for (i = 0; i < key.attributes.length; i++) {
        dump(key.attributes[i].nodeName+'="'+key.attributes[i].nodeValue+'" ');
    }
    dump('/>');
}

this.Manager.prototype.clearBinding = function(commandId, commandParam, restore) {
    if (!(commandId in this.command2key)) {
        //dump("-- clearing binding for " + commandId + " but no binding exists \n");
        return;
    }
    var k;
    var keylabel;
    var param = '';
    if (typeof(commandParam) != 'undefined') {
        param = commandParam;
    }
    var parametrized = commandId in this._commandParams;
    var text;

    this.unsetKeyBinding(commandId);
    var kbs = this.command2key[commandId];
    for (var k = 0; k < kbs.length; ++k) {
        keylabel = kbs[k];
        if (typeof(keylabel) == 'undefined') {
            continue;
        }
        if (parametrized && this._commandParams[commandId][keylabel] != param) {
            // skip parametrized commands not bound to this parameter
            continue;
        }
        this.clearSequence(commandId, keylabel, restore);
    }
};

this.Manager.prototype._getKeyTreeRoot = function(keysequence) {
    var root = this.keyTree;
    var i;
    for (i=0; i < keysequence.length - 1; i++) {

        if (!isAssociativeArray(root)) {
            return null;
        }
        root = root[keysequence[i]];
    }
    return root;
}

this.Manager.prototype.clearSequence = function(commandId, keylabel, restore) {
    //dump("clearSequence "+commandId+", "+keylabel+", "+restore+"\n");
    try {
    if (typeof(keylabel) != 'string') {
        _log.error("clearSequence should be caled with a string, not with a" + typeof(keylabel) + " such as " + keylabel)
    }
    var root;
    var i, j;
    var keysequence;
    root = this.keyTree;
    keysequence = keylabel2keysequence(keylabel);
    root = this._getKeyTreeRoot(keysequence);
    if (!root) return;
    if (root[keysequence[keysequence.length-1]] != commandId) {
        return;
    } else {
        delete root[keysequence[keysequence.length-1]];
    }

    // remove the keybinding from this command
    this.command2key[commandId].splice(this.command2key[commandId].indexOf(keylabel),1);
    // remove the params for this binding
    if (commandId in this._commandParams) {
        delete this._commandParams[commandId][keylabel];
    }
    // unset the key element
    this.unsetKey(keylabel);

    // need to restore "configuration" keys if they exist.
    if (restore) {
        root = this._configKeyTree;
        for (i=0; i < keysequence.length - 1; i++) {
            if (!isAssociativeArray(root)) {
                return;
            }
            root = root[keysequence[i]];
        }
        if (isAssociativeArray(root)) {
            var cmd = root[keysequence[keysequence.length-1]];
            if (typeof(cmd) != 'undefined'){
                //dump("restore keybinding for "+cmd+", "+keysequence+"\n");
                this.assignKey(cmd, keysequence);
                this.makeKeyActive(cmd, keysequence);
            }
        }
    }
    } catch(e) { _log.exception(e); }
};

this.Manager.prototype.unsetKey = function(keylabel) {
    // we do not remove non-command key elements due to a mozilla crash bug
    // this unsets any command attached to the key but otherwise leaves
    // it intact
    if (keylabel in this.key2command) {
        delete this.key2command[keylabel];
    }
    var key = this.document.getElementById(keylabel);
    if (key) {
        key.removeAttribute('command');
    }
}

this.Manager.prototype.unsetKeyBinding = function(commandId) {
    // this both unsets the keybinding and clears the menu key text,
    // which is set by either acceltext, keytext, or modifiers+key|keycode
    //dump("unsetKeyBinding "+commandId+"\n");
    var cmd = this.document.getElementById(commandId);
    if (cmd)
        cmd.removeAttribute('acceltext');
    
    var key = this.document.getElementById("key_"+commandId);
    if (key) {
        key.removeAttribute('modifiers');
        key.removeAttribute('keycode');
        key.removeAttribute('key');
        key.removeAttribute('keytext');
        //key.setAttribute('command', commandId);
        if (key.hasAttribute('oncommand')) {
            key.removeAttribute('oncommand');
        }
    }
}

this.Manager.prototype.setKeyBinding = function(keysequence, commandId, commandKey) {
    // for purpose of assignment, we bind the command to the first key
    var keyname = keysequence[0]; 
    var keylabel = keysequence2keylabel(keysequence);
    var id;
    if (commandKey) {
        id = 'key_'+commandId;
    } else {
        id = keyname;
    }
    //dump('setKeyBinding for '+id+"\n");

    var key = this.document.getElementById(id);
    var exists = key != null;
    if (exists && commandKey) {
        // make sure the existing key is valid, and if so, then we're no
        // longer a commandkey
        var seqList = this.command2keysequences(commandId);
        if (seqList.indexOf(keylabel) >= 0) {
            return this.setKeyBinding(keysequence, commandId, false);
        }
    }
    if (!exists) {
        key = this.document.createElementNS("http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul", "key");
        key.setAttribute('id', id);
        key.setAttribute('command', commandId);
        this.document.getElementById('widekeyset').appendChild(key);
    } else if (!commandKey) {
        // always reset the command on non-command  key elements
        key.setAttribute('command', commandId);
    }
    if (!exists || commandKey) {
        // always reset the key bindings on command key elements
        // figure out modifiers and add them
        var modifiers, keycode;
        if (keyname[keyname.length-1] == '+') {
            keycode = '+';
            modifiers = keyname.split('+');
        } else {
            modifiers = keyname.split('+');
            keycode = modifiers[modifiers.length-1];
        }
        modifiers = modifiers.slice(0, modifiers.length-1);
        if (modifiers.length > 0) {
            var m = modifiers.indexOf('Ctrl');
            if (m >= 0) modifiers[m] = 'control';
            modifiers = modifiers.join(',').toLowerCase();
            key.setAttribute('modifiers', modifiers);
        }
    
        // figure out correct keyname
        if (keycode in VKLabels) {
            //dump("n: "+keyname+" kc: "+VKLabels[keycode]+" m: "+modifiers+"\n");
            key.setAttribute('keycode', VKLabels[keycode]);
        } else {
            keycode = keycode.toUpperCase();
            key.setAttribute('key', keycode);
            //dump("n: "+keyname+" k: "+keycode+" m: "+modifiers+"\n");
        }
        if (commandId != 'cmd_prefix')
            key.setAttribute('name', keylabel);
    }
    return key;
}

this.Manager.prototype.makeKeyActive = function(commandId, keysequence) {
  try {
    if (keysequence.length > 1) {
        //dump("makeKeyActive: " + commandId + ", keysequence: " + keysequence + "\n");
        if (!this.getKey(keysequence[0])) {
            this.setKeyBinding(keysequence, 'cmd_prefix', false);
            this.key2command[keysequence[0]] = 'cmd_prefix';
        }
        // this is necessary for multi key keybindings to get the correct thing
        // to appear in menu's. 
        var command = this.document.getElementById(commandId);
        if (command) {
            var acceltext;
            acceltext = keysequence2keylabel(keysequence);
            if (acceltext[acceltext.length-1] == '+') {
                acceltext+= '+';
            }
            command.setAttribute('acceltext', acceltext);
        }
    
    } else {
        var commandKey = commandId != 'cmd_callPart';
        this.setKeyBinding(keysequence, commandId, commandKey);
        this.keyTree[keysequence[0]] = commandId;
        this.key2command[keysequence[0]] = commandId;
    }

  } catch (e) {
    _log.exception(e);
  }
}

this.Manager.prototype.clearUsedBys= function(commandId, keysequence) {
    var usedbys = this.usedBy(keysequence)
    for (var i in usedbys) {
        this.clearSequence(usedbys[i].command, usedbys[i].label);
    }
}

this.Manager.prototype.assignKey = function(commandId, keysequence, parameter) {
    var sequencelabel = keysequence2keylabel(keysequence);
    if (typeof(parameter) == 'string' && parameter != '') {
        this.learnParameter(commandId, parameter, sequencelabel);
    }
    if (!(commandId in this.command2key)) {
        this.command2key[commandId] = [sequencelabel];
    } else {
        this.command2key[commandId] = [sequencelabel].concat(this.command2key[commandId]);
    }
    var i;
    var root = this.keyTree;
    var key;
    for (i in keysequence) {
        key = keysequence[i];
        if (i != keysequence.length-1) {
            if (!(key in root)) {
                root[key] = {}
            } else {
                if (typeof(root[key]) != 'object') {
                    root[key] = {}
                }
            }
            root = root[key];
        } else {
            root[key] = commandId;
            return;
        }
    }
}

this.Manager.prototype.parseGlobalData= function() {
    var i;
    var keyname, key, commandname, commanddesc, command;
    var keys = this.document.getElementsByTagName('key');
    var commands = this.document.getElementsByTagName('command');
    var broadcasters = this.document.getElementsByTagName('broadcaster');

    var all_commands = [];
    for (i=0; i < commands.length; i++) {
        all_commands.push(commands[i]);
    }
    for (i=0; i < broadcasters.length; i++) {
        all_commands.push(broadcasters[i]);
    }

    this.keynames = new Array();
    for (i=0; i< keys.length; i++) {
        this.keynames[keys[i].getAttribute('id')] = 1;
    }

    this.commandnames = new Array();
    this.commanditems = new Array();
    var already_got = new Array();
    var commanditem;
    var commanditem_from_name = {};
    for (i=0; i< all_commands.length; i++) {
        command = all_commands[i];
        commandname = command.getAttribute('id');
        commanditem = commanditem_from_name[commandname];
        if (commanditem) {
            // We might find a better description.
            if (!commanditem.desc && command.hasAttribute('desc')) {
                commanditem.desc = command.getAttribute('desc');
            }
            continue;
        }
        this.commandnames.push(commandname);
        commanddesc = '';
        if (command.hasAttribute('desc')) {
            commanddesc = command.getAttribute('desc');
        }
        commanditem = {};
        commanditem.desc = commanddesc;
        commanditem.name = commandname
        commanditem_from_name[commandname] = commanditem;
        this.commanditems.push(commanditem);
        //dump("adding " + commandname + ' --> ' + commanddesc + '\n');
    }
    this.commanditems.sort(sort_commanditems);
}

function sort_commanditems(a, b) {
    if (a.desc < b.desc) return -1;
    if (a.desc == b.desc) return 0;
    return 1;
}

var cssTable = "\n\
body\n\
    {\n\
    background: #FFFFFF;\n\
    font-family: Verdana, Arial, Helvetica, sans-serif;\n\
    font-weight: normal;\n\
    font-size: 90%;\n\
    }	\n\
body.toc\n\
   {\n\
   background-color: #D9D5CE; \n\
   background-image: url('images/watermark_AS.gif'); \n\
   background-repeat: no-repeat; \n\
   color: #333333;   \n\
   }\n\
td\n\
    {\n\
    font-family: Verdana, Arial, Helvetica, sans-serif;\n\
    font-weight: normal;\n\
    text-decoration: none;\n\
    font-size: 90%;\n\
    }\n\
p\n\
    {\n\
    color: #000000;\n\
    font-family: Verdana, Arial, Helvetica, sans-serif;\n\
    font-weight: normal;\n\
    }\n\
blockquote\n\
    {\n\
    color: #000000;\n\
    font-family: Verdana, Arial, Helvetica, sans-serif;\n\
    font-weight: normal;\n\
    margin-left: 15px;\n\
    }\n\
dl\n\
    {\n\
    color: #000000;\n\
    font-family: Verdana, Arial, Helvetica, sans-serif;\n\
    font-weight: normal;\n\
    }\n\
\n\
dt\n\
    {\n\
    color: #000000;\n\
    font-family: Verdana, Arial, Helvetica, sans-serif;\n\
    font-weight: normal;\n\
    }\n\
\n\
ul\n\
	{\n\
	margin-top: 5px;\n\
	margin-bottom: 5px;\n\
	}\n\
   \n\
ol\n\
    {\n\
    color: #000000;\n\
    font-family: Verdana, Arial, Helvetica, sans-serif;\n\
    font-weight: normal;\n\
    }\n\
\n\
h1\n\
    {\n\
    color: #000000;\n\
    font-weight: bold;\n\
    font-size: 130%;\n\
    background-color: #EEEEEE;\n\
    padding: 2px;\n\
    }\n\
    h2 a:hover\n\
        {\n\
        color: #000000;\n\
        text-decoration: none;\n\
        }\n\
h2\n\
    {\n\
    color: #222222;\n\
    font-weight: bold;\n\
    font-size: 100%;\n\
    padding: 2px;  \n\
    border-bottom: 1px dashed #222222; \n\
    }\n\
pre\n\
    {\n\
    font-size: 120%;\n\
    }\n\
tt\n\
    {\n\
    font-size: 120%;\n\
    }\n\
code\n\
    {\n\
    font-size: 120%;\n\
    }\n\
kbd\n\
    {\n\
    font-size: 120%;\n\
    }\n\
   \n\
/* default links */\n\
a:link\n\
	{\n\
	color: #0066CC;\n\
	text-decoration: none;\n\
	}\n\
a:visited\n\
	{\n\
	color: #0066CC;\n\
	text-decoration: none;\n\
	}\n\
a:hover\n\
	{\n\
	color: #0066CC;\n\
	text-decoration: underline;\n\
	}";



this.Manager.prototype.makeCurrentKeyBindingTable = function() {
    //if (this.commanditems == null) {
        this.parseGlobalData();
    //}
    var infoSvc = Components.classes["@activestate.com/koInfoService;1"].
                  getService(Components.interfaces.koIInfoService);
    var title = 'Komodo Keybindings [' + this.currentConfiguration + ']';
    var text = "<html><HEAD><title>" + title + "</title><STYLE TYPE=\"text/css\" MEDIA=screen><!-- " + cssTable + " --></STYLE></HEAD><body><table width=\"100%%\">";
    text = text.concat('<h2>' + title + '</h2>');
// #if PLATFORM == 'darwin'
    text = text.concat('NOTE: "Meta" in this list refers to the Command Key on OS X.');
// #endif
    var desc;
    var category;
    var key;
    this.lastcategory = '';
    var commandname;
    this.rownum = 0;
    var i, j;

    // First non-parametrized commands
    for (i = 0; i < this.commanditems.length; i++) {
        commandname = this.commanditems[i].name;
        if (commandname in this.command2key) {
            desc = this.commandId2tabledesc(commandname, '')
            category = desc.slice(0, desc.indexOf(': '));
            if (! this._commandParams[commandname]) {
                desc = desc.slice(desc.indexOf(': ')+2);
                text = text.concat(this._addRow(category, desc, this.command2key[commandname]));
            }
        }
    }
    // Then parametrized commands (these tend to be the custom ones)
    for (i = 0; i < this.commanditems.length; i++) {
        commandname = this.commanditems[i].name;
        if (commandname in this.command2key) {
            desc = this.commandId2tabledesc(commandname, '')
            category = desc.slice(0, desc.indexOf(': '));
            if (this._commandParams[commandname]) {
                for (key in this._commandParams[commandname]) {
                    desc = this.commandId2tabledesc(commandname, this._commandParams[commandname][key])
                    category = desc.slice(0, desc.indexOf(': '));
                    desc = desc.slice(desc.indexOf(': ')+2);
                    text = text.concat(this._addRow(category, desc, [key]));
                }
            }
        }
    }
    text = text.concat('</table></body></html>');
    return text;
}

this.Manager.prototype.makeCommandIdTable = function() {
    //if (this.commanditems == null) {
        this.parseGlobalData();
    //}
    var infoSvc = Components.classes["@activestate.com/koInfoService;1"].
                  getService(Components.interfaces.koIInfoService);
    var title = 'Komodo Command Id List';
    var genComment = "<!-- Generated by ko.keybindings.manager.makeCommandIdTable in keybindings.p.js -->\n";
    var text = ("<html><HEAD><title>"
                + title
                + "</title><STYLE TYPE=\"text/css\" MEDIA=screen><!-- "
                + cssTable
                + " --></STYLE>\n</head>\n"
                + genComment
                + "<body><table width=\"100%%\">"
                + '<h1>' + title + '</h1>');
    var desc;
    var category;
    var key;
    this.lastcategory = '';
    var commandname;
    this.rownum = 0;
    var i, j;

    var _commands = this.document.getElementsByTagName('command');
    var _broadcasters = this.document.getElementsByTagName('broadcaster');
    var command;
    var _desc = [];
    for (i = 0; i < _commands.length; i++) {
        command = _commands[i];
        desc = command.getAttribute('desc');
        _desc.push([desc, command.getAttribute('id')]);
    }
    for (i = 0; i < _broadcasters.length; i++) {
        command = _broadcasters[i];
        desc = command.getAttribute('desc');
        _desc.push([desc, command.getAttribute('id')]);
    }
    _desc.sort();
    for (i = 0; i < _desc.length; i++) {
        desc = _desc[i][0];
        if (!desc) continue;
        var id = _desc[i][1];
        category = desc.slice(0, desc.indexOf(': '));
        desc = desc.slice(desc.indexOf(': ')+2);
        text = text.concat(this._addRow(category, desc, [id]));
    }

    text = text.concat('</table></body></html>');
    return text;
}

this.Manager.prototype._addRow = function(category, desc, keys) {
    var text = '';
    // We may be missing some characters.
    desc = desc.replace('&', '&amp;', 'g');
    desc = desc.replace('<', '&lt;', 'g');
    desc = desc.replace('>', '&gt;', 'g');
    if (category != this.lastcategory) {
        if (this.lastcategory != '') {
            text = text.concat('</table>');
        }
        this.lastcategory = category;
        text = text.concat('<h2>' + category + '</h2><table width=\"100%%\">')
        this.rownum = 0;
    }
    if (this.rownum % 2) {
        text = text.concat('<tr>')
    } else {
        text = text.concat('<tr bgcolor="#eeeeee">')
    }
    this.rownum += 1;
    text = text.concat('<td width="50%%"><p>' + desc + '</p></td><td width="50%%">');
    text = text.concat('<table>');
    for (var j in keys) {
        text = text.concat('<tr><td><p>'+ keys[j] +'</p></td></tr>');
    }
    text = text.concat('</table>');
    text = text.concat('</td></tr>\n');
    return text;
}

this.Manager.prototype._getPartFromId = function(param) {
    var part = ko.toolbox2.findToolById(param);
    if (!part) {
        throw new Error("keybindings._getPartFromId: Couldn't find part with id: " + param + '\n');
    }
    return part;
}

this.Manager.prototype.commandId2desc= function(commandname, param, label) {
    var command = this.document.getElementById(commandname);
    if (! command) {
        return '';
    }
    var commanddesc = ''
    if (command.hasAttribute('desc')) {
        commanddesc = command.getAttribute('desc');
    }
    if (typeof(param) != 'undefined' && param && commandname == 'cmd_callPart') {
        var part = this._getPartFromId(param);
        return part.get_keybinding_description() + ' [' + label + ']';
    }
    if (commanddesc == '') {
        commanddesc = commandname;
    }
    if (commandname in this._commandParams) {
        var param2 = this._commandParams[commandname][label];
        commanddesc = commanddesc + " (called with \'" + param2 + "') [" + label + ']';
    } else {
        commanddesc = commanddesc + ' [' + label + ']';
    }
    return commanddesc;
}

this.Manager.prototype.commandId2shortdesc = function(commandname, param) {
    var command = this.document.getElementById(commandname);
    if (! command) {
        return '';
    }
    var commanddesc = ''
    if (command.hasAttribute('desc')) {
        commanddesc = command.getAttribute('desc');
    }
    if (typeof(param) != 'undefined' && param && commandname == 'cmd_callPart') {
        var part = this._getPartFromId(param);
        return part.get_keybinding_description();
    } else {
        if (commanddesc == '') {
            commanddesc = commandname;
        }
        if (commanddesc.indexOf(': ') != -1) {
            return commanddesc.slice(commanddesc.indexOf(': ')+2, commanddesc.length)
        }
    }
    return commanddesc;
}

this.Manager.prototype.commandId2tabledesc= function(commandname, param) {
    var command = this.document.getElementById(commandname);
    if (! command) {
        return '';
    }
    var commanddesc = ''
    if (command.hasAttribute('desc')) {
        commanddesc = command.getAttribute('desc');
    }
    if (typeof(param) != 'undefined' && param && commandname == 'cmd_callPart') {
        var part = this._getPartFromId(param);
        var desc = part.get_keybinding_description();
        return desc;
    }
    if (commanddesc == '') {
        commanddesc = commandname;
    }
    return commanddesc;
}

this.Manager.prototype.commandId2parameter= function(commandname, label) {
    if (commandname in this._commandParams) {
        return this._commandParams[commandname][label];
    } else {
        return '';
    }
}

this.Manager.prototype.stashIn= function(vessel, keylabel) {
    vessel.setStringAttribute('keyboard_shortcut', keylabel);
}

this.Manager.prototype.command2keysequences= function(commandId, commandParam) {
    if (!(commandId in this.command2key)) return [];
    if (!(commandId in this._commandParams)) return this.command2key[commandId]
    var seqs = [];
    var seq;
    for (seq in this._commandParams[commandId]) {
        if (this._commandParams[commandId][seq] == commandParam) {
            seqs.push(seq);
        }
    }
    return seqs;
}

this.Manager.prototype._usedbys = function(root, remainingsequence, sofarsequence, usedbys) {
    // This is a fairly delicate piece of code -- the logic is tricky to follow
    // so don't touch it if you don't really know what you're doing.
    //dump("-- remainingsequence = " + remainingsequence +'\n');
    //dump("-- sofarsequence = " + sofarsequence +'\n');
    //dump("-- usedbys = ");
    //for (i in usedbys) { dump('\t'+usedbys.desc +'\n');}
    //if (root != this.keyTree) {
        //dump("root has:\n");
        //for (var j in root) {
            //dump('\t'+j+'\t'+root[j]+'\n');
        //}
    //}
    // We need to walk the tree and collect _all_ the children of all the branch points
    // being visited.
    // Are we being specific still -- do we have more parts of the trees to prune?
    var usedby;
    var key;
    var param;
    if (remainingsequence.length > 0) {
        //dump("remaining sequence = " + remainingsequence + " and has length " + remainingsequence.length +'\n');
        key = remainingsequence[0];
        var commandMatch = root[key];
        //dump("phase 1, looking at key: " + key + ", commandMatch: " + commandMatch + '\n');
        switch (typeof(commandMatch)) {
            case 'string':
                usedby = new Object();
                usedby.command = commandMatch;
                sofarsequence.push(key);
                usedby.label = keysequence2keylabel(sofarsequence);
                if (usedby.command in this._commandParams) {
                    param = this._commandParams[usedby.command][key];
                } else {
                    param = null;
                }
                // The label isn't right -- but I'm not sure how to fix it.  To see why
                // it isn't right, create two e.g. run commands, assign F4 to one of them
                // assign F4 F1 to the other -- as you type that in, the kb dialog
                // will say "Help: Help [F4, F1]" -- but Help is just F1.
                // Maybe I'll fix it someday -- it's hardly a big problem.
                // Fixed now: ToddW, removed looping over the sequence, as when
                // the sequence is more than one, it has to be a object (multi
                // key binding), which recurses/loops over sequence already.
                usedby.desc = this.commandId2desc(usedby.command, param, usedby.label);
                usedby.shortdesc = this.commandId2shortdesc(usedby.command, param);
                usedby.parameter = this.commandId2parameter(usedby.command, usedby.label);
                usedbys.push(usedby);
                break;
            case 'object':
                sofarsequence.push(key);
                // recurse
                //dump("recursing into " + key +'\n');
                this._usedbys(commandMatch,
                              remainingsequence.slice(1, remainingsequence.length),
                              sofarsequence, usedbys);
                sofarsequence.pop();
                root = commandMatch;
                break;
            default:
                //dump("root["+key+"] is undefined!\n");
                // type is undefined, presumably
        }
    } else {
        // We've reached the end of the specification of the sequence -- the tree
        // from here on out has to be gathered.
        for (key in root) {
            //dump("phase 2, looking at "+key+'\n');
            if (typeof(root[key]) == 'string') {
                usedby = new Object();
                usedby.command = root[key];
                //dump('YYYY - pushing ' + usedby.command +'\n');
                sofarsequence.push(key);
                usedby.label = keysequence2keylabel(sofarsequence);
                if (usedby.command in this._commandParams) {
                    param = this._commandParams[usedby.command][usedby.label];
                } else {
                    param = null;
                }
                //dump("param = " + param + '\n');
                //dump("usedby.label = " + usedby.label + '\n');
                usedby.desc = this.commandId2desc(usedby.command, param, usedby.label);
                //dump("usedby.desc = " + usedby.desc + '\n');
                sofarsequence.pop();
                usedbys.push(usedby);
            } else if (typeof(root[key]) == 'object') {
                //dump("recursing in phase 2!\n");
                sofarsequence.push(key);
                // recurse
                this._usedbys(root[key], [], sofarsequence, usedbys);
                sofarsequence.pop();
            }
        }
    }
}

this.Manager.prototype.usedBy = function(sequence) {
    // This function needs to walk the keyTree starting at root and return a list
    // of objects describing the commands which would be "intercepted" by the sequence
    // being sent in.
    if (!isArray(sequence)) {
        _log.error("usedBy has to be called with a sequence of key labels\n");
    }
    var usedbys = new Array();
    // we start at the root of the tree, given the entire sequence, a working array,
    // and the return array
    this._usedbys(this.keyTree, sequence, [], usedbys);
    return usedbys;
}

function dumpUsedBys(usedbys) {
    var i;
    dump("USED BY RESULTS\n");
    for (i in usedbys) {
        dump('\t'+usedbys[i].label + ': ' + usedbys[i].desc + ': ' + usedbys[i].command +'\n');
    }
}

this.Manager.prototype.eventBindings = function (event, isKeyPressEvent) {
    if (typeof(isKeyPressEvent) == 'undefined') {
        isKeyPressEvent = true;
    }
    var possible = [];
    var k;
// #if PLATFORM == 'darwin'
    k = this.event2keylabel(event, true, isKeyPressEvent);
// #else
    // win/unix
    k = this.event2keylabel(event, false, isKeyPressEvent);
// #endif
    if (k)
        possible.push(k);
// #if PLATFORM != 'darwin' and  PLATFORM != 'win'
    if (event.shiftKey) {
        var k = this.event2keylabel(event, true, isKeyPressEvent);
        if (k && k != possible[0])
            possible.push(k);
    }
// #endif
    if (possible.length < 1) return null;
    return possible;
}

this.Manager.prototype.event2keylabel = function (event, useShift, isKeyPressEvent) {
    var data = [];
    try {
        if (typeof(useShift) == 'undefined') {
// #if PLATFORM == 'darwin' or PLATFORM == 'win'
            useShift = true;
// #else
            useShift = false;
// #endif
        }
        if (typeof(isKeyPressEvent) == 'undefined') {
            isKeyPressEvent = true;
        }
        // From an event, builds the string which corresponds to the key
        // conveniently also the menu label, pretty description, etc.
    
        // This is a little tricky because while most keystrokes that we care about spawn keypress
        // events, some only show up in keywowns.
        // if it is a modified key, then use this manager only
        //ko.logging.dumpEvent(event);
        var use_vi = false;
        if (gVimController.enabled &&
            !(event.metaKey || event.ctrlKey || event.altKey) &&
            (event.target.nodeName == 'view')) {
            let view = event.target;
            try {
                // Multiview handling, we want the editor view - bug 97891.
                while (view.currentView) {
                    view = view.currentView;
                }
            } catch (ex) {
                // Some views don't implement .currentView, that's okay
            }
            if (view.scintilla && view.scintilla.isFocused) {
                use_vi = true;
            }
        }

        var keypressed = null;
        // keydown and keyup events do not set the charCode, they only set the
        // keyCode - keypress events set the charCode.
        var normCharCode = isKeyPressEvent ? event.charCode : 0;
        if (event.keyCode &&
            event.keyCode in VKCodes &&
            !(event.keyCode in VKModifiers) ) {
            keypressed = VKCodes[event.keyCode];
        } else if (normCharCode == 32) {
            keypressed = 'Space';
        } else if (normCharCode) {
            // Vi needs lowercase/uppercase differentiation
            if (use_vi)
                keypressed = String.fromCharCode(normCharCode);
            else
            {
// #if PLATFORM == 'darwin'
                // Fix bug 74649: map unexpected charCodes to
                // the value the user intended.
                // For example, on OSX "Ctrl+[" was generating charCode 27 (ESC),
                // while on Linux and Windows it generates charCode 91 (ASCII "[")
                // This happens for these four characters: [ ] \ _
                // This array hardwires "[]\\_".split().map(lambda(c): ascii(c) - 64)
                if ([0x1b, 0x1c, 0x1d, 0x1f].indexOf(normCharCode) >= 0) {
                    normCharCode += 0x40;
                    // e.g. 0x1b + 0x40 === 27 + 64 = 91 === ord(ESC) + 64 => ord('[')
                }
// #endif
                keypressed = String.fromCharCode(normCharCode).toUpperCase();
            }
        }
        if (keypressed == null) {
            //dump("NO KEY PRESSED!!!\n");
            //ko.logging.dumpEvent(event);
            return '';
        }
        //dump("keypressed: event.keyCode: " + event.keyCode + ", " + keypressed + "\n");

        //ko.logging.dumpEvent(event);
        if (event.metaKey) data.push("Meta");
        if (event.ctrlKey) data.push("Ctrl");
        if (event.altKey) data.push("Alt");
        if (event.shiftKey) {
            // if no other modifier, and this is ascii US a-z,
            // add the shift modifier to the keylabel, otherwise, just
            // use the charcode as-is.  
            if (normCharCode == 0 || // no char code, such as DEL
                (useShift && data.length > 0) || // with modifier
// #if PLATFORM == 'darwin' or PLATFORM == 'win'
                // ctrl and meta need to always include shift in the label
                // since the os does not shift the character
                // exception is win ctrl+shift+2|6 on US kb
                (data.length > 0 && !event.altKey && normCharCode <= 127) ||
// #endif
                // Vi has no sense of shifted characters, it's uppercase or
                // lowercase
                ((!use_vi) &&
                 ((normCharCode >= 65 && normCharCode <= 90) ||
                 (normCharCode >= 97 && normCharCode <= 122)))) {
                    data.push("Shift");
            }
        }
        data.push(keypressed);
    } catch (e) {
      _log.exception(e);
    }
    return data.join('+');
}

this.Manager.prototype.evalCommand = function (event, commandname, keylabel) {
    // this handles executing multi-key bindings and toolbox related commands
    try {
        var command = this.document.getElementById(commandname);
        if (!command) {
            _log.error("FAILURE to find command " + commandname);
        }
        var expr = null;
    
        var elid = null;
        if (command.hasAttribute('docommand')) {
            elid = 'docommand';
        } else if (command.hasAttribute('oncommand')) {
            elid = 'oncommand';
        }
        if (commandname in this._commandParams) {
            // It's a "parametrized command
            if (!elid || !(keylabel in this._commandParams[commandname]))
                return false;
            expr = "var _param = '"+this._commandParams[commandname][keylabel].replace('"', '\\"', 'g') +"'; " + command.getAttribute(elid);
        } else {
            // if it's not a "real" command but just has an oncommand handler, then use that
            if (elid) {
                expr = command.getAttribute(elid);
            }
            if (!expr && ko.commands.doCommand(commandname)) {
                return true;
            }
       }
        if (expr) {
            //dump("would eval: " + expr+'\n');
            var ret = eval(expr);
            if (typeof(ret) == 'undefined') ret = true;
            return ret;
        }
    } catch(e) {
        _log.exception(e);
    }
    return false;
}

this.Manager.prototype.cancelPrefix = function (why) {
    // This function is called whenever the prefix handler business needs to "stop"
    // this happens internally when a sequence of keystrokes doesn't correspond
    // to a predefined binding.

    // If the first argument is null, then the status bar message is canceled.
    // If the first argument is _NOT_ null, then it is used as the
    // message to display on the status bar message for 3 seconds.
// #if PLATFORM != 'darwin'
    this.keyDownLabels = null;
// #endif
    this.currentPrefixString = '';
    this.currentPrefixMap = this.keyTree;
    if (!this.inPrefixCapture)
        return;
    this.inPrefixCapture = false;
    this._keyPressCaptureWindow.removeEventListener('keypress', gKeyHandler, true);
// #if PLATFORM != 'darwin'
    // keydown is required to capture modifer+shift keybindings correctly on
    // windows and unix
    this._keyPressCaptureWindow.removeEventListener('keydown', gKeyDownHandler, true);
// #endif
    this._keyPressCaptureWindow.removeEventListener('mousedown', gCancelKeyHandler, true);
    this._keyPressCaptureWindow.removeEventListener('blur', gCancelKeyHandler, false);
    this._keyPressCaptureWindow = null;
    
    require("notify/notify").hideNotificationsByProp("id", "keyCompletion");
}

this.Manager.prototype.startPrefixCapture = function() {
    this.inPrefixCapture = true;
    window.addEventListener('keypress',gKeyHandler, true);
// #if PLATFORM != 'darwin'
    window.addEventListener('keydown', gKeyDownHandler, true);
// #endif
    window.addEventListener('mousedown', gCancelKeyHandler, true);
    window.addEventListener('blur', gCancelKeyHandler, false);
    this._keyPressCaptureWindow = window;
}

var gKeyHandler = function (event) {
    if (event.defaultPrevented) {
        // somebody wanted to skip this
        return;
    }
    ko.keybindings.manager.keypressHandler(event);
}

var gF10KeyHandler = function (event) {
    /**
     * Special F10 key handling that must listen on propagation phase (instead
     * of the bubbling phase) - bug 81657.
     */
    if (event.keyCode == event.DOM_VK_F10) {
        ko.keybindings.manager.keypressHandler(event, true /* ignore phase checks */);
    }
}

// #if PLATFORM != 'darwin'
var gKeyDownHandler = function (event) {
    // get and store the keydown label
    ko.keybindings.manager.keyDownLabels = ko.keybindings.manager.eventBindings(event, false);
    //dump("gKeyDownHandler "+ko.keybindings.manager.keyDownLabels.join(", ")+"\n");
}
// #endif

var gCancelKeyHandler = function (event) {
    var msg;
    if (event.type == 'mousedown') {
        msg = 'Clicked away';
    } else {
        msg = 'Key command canceled';
    }
    ko.keybindings.manager.cancelPrefix(msg)
}

this.Manager.prototype.keypressHandler = function (event, ignorePhase) {
    try {
        //dump("keybindingManager::keypressHandler: key event "+event.type+" keycode "+event.keyCode+" phase "+event.eventPhase+"\n");

        // Vi mode does not need to check this.
        if (gVimController.enabled &&
            (event.target.nodeName == 'view') &&
            event.target.scintilla &&
            event.target.scintilla.isFocused)
        {
            if (gVimController.inSpecialModeHandler(event)) {
                return;
            }
        } else {
            //dump("Checking key binding matches\n");
            // we only want keystrokes with modifiers on the bubble (ie. when
            // not in multi key bindings)
            // if in multi key bindings (inPrefixCapture) allow single keys
            // to complete the binding
            if (!this.inPrefixCapture && ((event.eventPhase == 1 && !ignorePhase) ||
                (event.keyCode == 0 && !event.ctrlKey && !event.altKey && !event.metaKey)))
                return;
        }
        // if there is no charcode, and no keycode we can convert, then
        // ignore the binding.  This is primarily for keydown events.
        if (event.charCode == 0 && (event.keyCode == 0 || !(event.keyCode in VKCodes)))
            return;

        var keys = this.eventBindings(event, true);
// #if PLATFORM != 'darwin'
        if (this.keyDownLabels) {
            for (var kd in this.keyDownLabels) {
                if (keys.indexOf(this.keyDownLabels[kd]) < 0) {
                    keys.push(this.keyDownLabels[kd]);
                }
            }
            this.keyDownLabels = null;
        }
// #endif
        //dump("possible keys are "+keys.join(', ')+"\n");
        var key = null;
        // find the key we want to use
        for (var k in keys) {
            key = keys[k];
    
            if (key in this.currentPrefixMap) break;
        }
        
        if (key == '') return;  // but _stay_ in prefixHandler mode
        //dump("    key "+key+"\n");
        // If the key corresponds to the cmd_cancel command, cancel.
        if (this.inPrefixCapture &&
            this.command2key['cmd_cancel'] == key) {
            this.cancelPrefix(null);
        }

        if (this.currentPrefixString == '') {
            this.currentPrefixString = key;
        } else {
            this.currentPrefixString += ', ' + key;
        }

        if (!(key in this.currentPrefixMap)) {
            if (this.inPrefixCapture) {
                this.cancelPrefix('('+this.currentPrefixString + ") is not a valid key sequence.");
                event.cancelBubble = true;
                event.stopPropagation();
                event.preventDefault();
            } else {
                this.cancelPrefix(null);
            }
            this.currentPrefixMap = this.keyTree;
            return;
        }
        
        if (typeof(this.currentPrefixMap[key]) == 'string') {
            // it's a command
            var multiKey = this.inPrefixCapture;
            var keylabel = this.currentPrefixString;
            var commandname = this.currentPrefixMap[key];
            this.cancelPrefix(null);
            //dump("key: " + key + ", keylabel: " + keylabel + ", multiKey: " + multiKey + ", commandname: " + commandname + "\n");
            if (gVimController.handleCommand(event, commandname, keylabel, multiKey) ||
                this.evalCommand(event, commandname, keylabel) || multiKey) {
                // only cancel if the eval of the command works
                event.cancelBubble = true;
                event.stopPropagation();
                event.preventDefault();
            }
            this.currentPrefixMap = this.keyTree;
        } else {
            this.startPrefixCapture();
            this.currentPrefixMap = this.currentPrefixMap[key]
            var msg = this.currentPrefixString + " was pressed.  Awaiting further keys.";
            require("notify/notify").send(msg, "keybindings", {id: "keyCompletion", priority: "now"});
            event.cancelBubble = true;
            event.stopPropagation();
            event.preventDefault();
        }
    } catch (e) {
        _log.exception(e);
    }
}

this.Manager.prototype.eventMappedToCommand = function(event, cmds) {
    /**
     * cmds can be a single string, or an array of strings.
     *
     * Returns whether the key represented by event is mapped to
     * one of the supplied commands.
     */
    var label = this.event2keylabel(event, undefined, true);
    if (!label) return false;
    var cmd = this.key2command[label];
    if (!cmd) return false;
    return Array.isArray(cmds) ? cmds.indexOf(cmd) >= 0 : cmds == cmd;
};

this.onload = function keybindingManagerOnLoad()
{
    try {
        ko.keybindings.manager = new ko.keybindings.Manager();
        // Load vim key handling stuff
        VimController_onload();
        // makes it handy for other things to access in different windows
        ko.keybindings.manager.vimController = gVimController;
        ko.keybindings.manager.loadConfiguration(ko.keybindings.manager.currentConfiguration);
    } catch (e) {
        _log.error(e);
    }
}

// duplication of DOM_VK_ codes found at
// http://lxr.mozilla.org/mozilla1.8/source/dom/public/idl/events/nsIDOMKeyEvent.idl
var VKCodes = {
0x03: "cancel",
0x06: "Help",
0x08: "Backspace",
0x09: "Tab",
0x0c: "Clear",
0x0d: "Return",
0x0e: "Enter",
//0x10: "Shift",
//0x11: "Control",
//0x12: "Alt",
0x13: "Pause",
0x14: "Caps_Lock",
0x1b: "Escape",
0x1d: "]",
0x20: "Space",
0x21: "Page_Up",
0x22: "Page_Down",
0x23: "End",
0x24: "Home",
0x25: "Left",
0x26: "Up",
0x27: "Right",
0x28: "Down",
0x2c: "PrintScreen",
0x2d: "Insert",
0x2e: "Delete",
0x30: '0',
0x31: '1',
0x32: '2',
0x33: '3',
0x34: '4',
0x35: '5',
0x36: '6',
0x37: '7',
0x38: '8',
0x39: '9',
0x3b: ";",
0x3d: "=",
0x60: "NumPad-0",
0x61: "NumPad-1",
0x62: "NumPad-2",
0x63: "NumPad-3",
0x64: "NumPad-4",
0x65: "NumPad-5",
0x66: "NumPad-6",
0x67: "NumPad-7",
0x68: "NumPad-8",
0x69: "NumPad-9",
0x6a: "*",
0x6b: "+",
0x6c: "Separator",
0x6d: "-",
0x6e: ".",
0x6f: "/",
0x70: "F1",
0x71: "F2",
0x72: "F3",
0x73: "F4",
0x74: "F5",
0x75: "F6",
0x76: "F7",
0x77: "F8",
0x78: "F9",
0x79: "F10",
0x7A: "F11",
0x7B: "F12",
0x7C: "F13",
0x7D: "F14",
0x7E: "F15",
0x7F: "F16",
0x80: "F17",
0x81: "F18",
0x82: "F19",
0x83: "F20",
0x84: "F21",
0x85: "F22",
0x86: "F23",
0x87: "F24",
0x90: "Num_Lock",
0x91: "Scroll_Lock",
0xbc: ",",
0xbe: ".",
0xbf: "/",
0xc0: "`",
0xdb: "[",
0xdc: "\\",
0xdd: "]",
0xde: "\""
//0xe0: "Meta"
}
this.VKCodes = VKCodes;

var VKModifiers = {
0x10: "Shift",
0x11: "Control",
0x12: "Alt",
0xe0: "Meta"
};
this.VKModifiers = VKModifiers;

// convert our labels to VK_ codes used in the key element as the
// keycode attribute.  any key in this will be used as a keycode, many
// keys do not work at all as keycodes
var VKLabels = {
    'Cancel': 'VK_CANCEL',
    'Backspace': 'VK_BACK',
    "Tab": "VK_TAB",
    'Clear': 'VK_CLEAR',
    'Return': 'VK_RETURN',
    'Shift': 'VK_SHIFT',
    'Control': 'VK_CONTROL',
    'Alt': 'VK_ALT',
    'Pause': 'VK_PAUSE',
    'Caps_Lock': 'VK_CAPS_LOCK',
    'Escape': 'VK_ESCAPE',
    'Space': 'VK_SPACE',
    'Page_Up': 'VK_PAGE_UP',
    'Page_Down': 'VK_PAGE_DOWN',
    'End': 'VK_END',
    'Home': 'VK_HOME',
    'Left': 'VK_LEFT',
    'Up': 'VK_UP',
    'Right': 'VK_RIGHT',
    'Down': 'VK_DOWN',
    'PrintScreen': 'VK_PRINTSCREEN',
    'Insert': 'VK_INSERT',
    'Help': 'VK_HELP',
    'Delete': 'VK_DELETE',
    "NumPad-0": "VK_NUMPAD0",
    "NumPad-1": "VK_NUMPAD1",
    "NumPad-2": "VK_NUMPAD2",
    "NumPad-3": "VK_NUMPAD3",
    "NumPad-4": "VK_NUMPAD4",
    "NumPad-5": "VK_NUMPAD5",
    "NumPad-6": "VK_NUMPAD6",
    "NumPad-7": "VK_NUMPAD7",
    "NumPad-8": "VK_NUMPAD8",
    "NumPad-9": "VK_NUMPAD9",
    "Separator": "VK_SEPARATOR",
    "Decimal": "VK_DECIMAL",
    'F1': 'VK_F1',
    'F2': 'VK_F2',
    'F3': 'VK_F3',
    'F4': 'VK_F4',
    'F5': 'VK_F5',
    'F6': 'VK_F6',
    'F7': 'VK_F7',
    'F8': 'VK_F8',
    'F9': 'VK_F9',
    'F10': 'VK_F10',
    'F11': 'VK_F11',
    'F12': 'VK_F12',
    "F13": "VK_F13",
    "F14": "VK_F14",
    "F15": "VK_F15",
    "F16": "VK_F16",
    "F17": "VK_F17",
    "F18": "VK_F18",
    "F19": "VK_F19",
    "F20": "VK_F20",
    "F21": "VK_F21",
    "F22": "VK_F22",
    "F23": "VK_F23",
    "F24": "VK_F24",
    "Num_Lock": "VK_NUM_LOCK",
    "Scroll_Lock": "VK_SCROLL_LOCK",
    
// keys that have characters need to be left alone here, otherwise the
// key elements in keybindings end up with a keycode attribute and do
// not work correctly
//    ";": "VK_SEMICOLON",
//    "=": "VK_EQUALS",
//    "*": "VK_MULTIPLY",
//    '+': 'VK_ADD',
//    '-': 'VK_SUBTRACT',
//    "/": "VK_DIVIDE",
//    ",": "VK_COMMA",
//    ".": "VK_PERIOD",
//    "/": "VK_SLASH",
//    '[': 'VK_OPEN_BRACKET',
//    "`": "VK_BACK_QUOTE",
//    ']': 'VK_CLOSE_BRACKET',
//    "\\": "VK_BACK_SLASH",
//    "\"": "VK_QUOTE",

/*
    '0': 'VK_0',
    '1': 'VK_1',
    '2': 'VK_2',
    '3': 'VK_3',
    '4': 'VK_4',
    '5': 'VK_5',
    '6': 'VK_6',
    '7': 'VK_7',
    '8': 'VK_8',
    '9': 'VK_9',
    
    'a': 'VK_A',
    'b': 'VK_B',
    "c": "VK_C",
    "d": "VK_D",
    "e": "VK_E",
    "f": "VK_F",
    "g": "VK_G",
    "h": "VK_H",
    "i": "VK_I",
    "j": "VK_J",
    "k": "VK_K",
    "l": "VK_L",
    "m": "VK_M",
    "n": "VK_N",
    "o": "VK_O",
    "p": "VK_P",
    "q": "VK_Q",
    "r": "VK_R",
    "s": "VK_S",
    "t": "VK_T",
    "u": "VK_U",
    "v": "VK_V",
    "w": "VK_W",
    "x": "VK_X",
    "y": "VK_Y",
    "z": "VK_Z",

    'A': 'VK_A',
    'B': 'VK_B',
    "C": "VK_C",
    "D": "VK_D",
    "E": "VK_E",
    "F": "VK_F",
    "G": "VK_G",
    "H": "VK_H",
    "I": "VK_I",
    "J": "VK_J",
    "K": "VK_K",
    "L": "VK_L",
    "M": "VK_M",
    "N": "VK_N",
    "O": "VK_O",
    "P": "VK_P",
    "Q": "VK_Q",
    "R": "VK_R",
    "S": "VK_S",
    "T": "VK_T",
    "U": "VK_U",
    "V": "VK_V",
    "W": "VK_W",
    "X": "VK_X",
    "Y": "VK_Y",
    "Z": "VK_Z",
*/
    'Meta': 'VK_META'
}
this.VKLabels = VKLabels;

}).apply(ko.keybindings);
