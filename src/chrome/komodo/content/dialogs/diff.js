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

/* A diff viewer window.
 *
 * Arguments to be passed into window.arguments[0]:
 *
 *  .diff: the diff content
 *  .title: a window title to use
 *  .message: (optional) message text to display in the view's status area
 *  .cwd: (optional) the base directory from which the diff was generated
 */

//
// Globals
//
var _dw_log = ko.logging.getLogger("diff");
//_dw_log.setLevel(ko.logging.LOG_DEBUG);
var _diffWindow = null;
var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
    .getService(Components.interfaces.nsIStringBundleService)
    .createBundle("chrome://komodo/locale/dialogs/diff.properties");
var _g_view_initialized = false;

//
// Diff window object
//
function DiffWindow()
{
    scintillaOverlayOnLoad();

    document.title = window.arguments[0].title;
    xtk.include('domutils');
    var view = document.getElementById('view');
    view.init();
    // Ensure the context menu is the diff-specific menu.
    view.setAttribute("mozcontext", "diffContextMenu");

    try {
        var diff = '';
        if (!window.arguments[0].diff) {
            if (window.arguments[0].async_op) {
                // Display the notification widget that it's running asynchronously.
                var label = _bundle.GetStringFromName("fetchingDiffInfo.label");
                var value = null;
                var asyncSvc = Components.classes["@activestate.com/koAsyncService;1"].
                                getService(Components.interfaces.koIAsyncService);
                var image_src = asyncSvc.asynchronous_icon_url;
                view.notificationbox.appendNotification(label, value, image_src);
                diff = _bundle.GetStringFromName("loadingAsync.message");
            } else {
                _dw_log.error('The diff was not specified for diff.xul');
            }
        } else {
            diff = window.arguments[0].diff;
        }

        var cwd = window.arguments[0].cwd;
        if (typeof(cwd) == 'undefined') {
            cwd = null;
        }

        loadDiffResult(diff, cwd);

    } catch(e) {
        _dw_log.exception(e);
    }

    if (window.arguments[0].message) {
        view.message = window.arguments[0].message;
    }
    window.controllers.appendController(this);

    // Update the imported commands
    for each (let commandset in Array.slice(document.getElementsByTagName("commandset"))) {
        ko.commands.updateCommandset(commandset);
    }
}

//
// Controller related code - handling of commands
//
DiffWindow.prototype.isCommandEnabled = function(cmdName) {
    if (cmdName == "cmd_bufferClose") {
        return true;
    }
    return false;
}

DiffWindow.prototype.supportsCommand = DiffWindow.prototype.isCommandEnabled;

DiffWindow.prototype.doCommand = function(cmdName) {
    if (cmdName == "cmd_bufferClose") {
        window.close();
        return true;
    }
    return false;
}


function loadDiffResult(result, cwd) {
    try {
        var diff = result;
        var diffView = document.getElementById('view');
        _dw_log.debug("diff.length: " + diff.length);
        if (!_g_view_initialized) {
            _g_view_initialized = true;
            diffView.initWithBuffer(diff, "Diff");
        } else {
            diffView.setBufferText(diff);
        }

        // Force scintilla buffer to readonly mode, bug:
        //   http://bugs.activestate.com/show_bug.cgi?id=27910
        diffView.scimoz.readOnly = true;
        //this._languageObj = this._diffDocument.languageObj;
        diffView.setFocus();
        // Remove the notification widget.
        diffView.notificationbox.removeAllNotifications(true /* false means to slide away */);

        // On Mac OSX, ensure the Scintilla view is visible by forcing a repaint.
        // TODO: investigate why this happens and come up with a better solution.
        // NOTE: repainting a Scintilla view by itself is not sufficient;
        // Mozilla needs to repaint the entire window.
        if (navigator.platform.match(/^Mac/)) {
            window.setTimeout(function() {
                window.resizeBy(1, 0);
                window.resizeBy(-1, 0);
            }, 10);
        }

    } catch(ex) {
        _dw_log.exception(ex, "error loading diff window dialog.");
    }
}


//
// Main loading and unloading of the diff window
//
function OnLoad() {
    try {
        _diffWindow = new DiffWindow();
    } catch(ex) {
        _dw_log.exception(ex, "error loading diff window dialog.");
    }
}

function OnUnload()
{
    var view = document.getElementById('view');
    // The "close" method ensures the scintilla view is properly cleaned up.
    view.close();
    window.controllers.removeController(_diffWindow);
    scintillaOverlayOnUnload();
}
