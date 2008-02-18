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

/* Confirm a "Replace All in Files" operation.
 *
 * Usage:
 *  All input args are via an object passed in and out as the first window
 *  argument: window.arguments[0].
 *      .editor     The main Komodo editor window
 *      .pattern    The search pattern string.
 *      .repl       The replacement string.
 *      .context    A `koIFindContext` for this replacement.
 *
 * On return, window.arguments[0] has:
 *      .replacer   A `koIConfirmReplacerInFiles` record of the selected
 *                  replacements to make, or null if aborted.
 */

var log = ko.logging.getLogger("find.confirmrepl");
log.setLevel(ko.logging.LOG_DEBUG);

var widgets = null; // object storing interesting XUL element references

var _g_find_svc = null;
var _g_replacer = null;     // the <koIConfirmReplacerInFiles> handler of replacements
var _g_controller = null;   // Controller instance managing this dialog's UI.



//---- interface routines for XUL

function on_load()
{
    try {
        _g_find_svc = Components.classes["@activestate.com/koFindService;1"]
                      .getService(Components.interfaces.koIFindService);

        _init_widgets();
        _init();

        window.sizeToContent();
    } catch (ex) {
        log.exception(ex);
    }
}

function repls_on_select()
{
    // <http://www.xulplanet.com/references/xpcomref/ifaces/nsITreeView.html#method_selectionChanged>
    // says:
    //    Should be called from a XUL onselect handler whenever the
    //    selection changes.
    //TODO: Do we have to do the handling to see if it is a selection *change*?
    try {
        widgets.repls.view.selectionChanged();
        
        if (_get_selected_indeces().length >= 1) {
            _enable_widget(widgets.show_selected_changes_btn);
        } else {
            _disable_widget(widgets.show_selected_changes_btn);
        }
    } catch (ex) {
        log.exception(ex);
    }
}

function repls_on_keypress(event)
{
    try {
        if (event.charCode == 32) { /* spacebar */
            var selection = widgets.repls.view.selection;
            var num_ranges = selection.getRangeCount();
            for (var i = 0; i < num_ranges; ++i) {
                var min = {}, max = {};
                selection.getRangeAt(i, min, max);
                for (var j = min.value; j <= max.value; ++j) {
                    _g_replacer.toggle_mark(j);
                }
            }
            return false;
        }
    } catch(ex) {
        log.exception(ex);
    }
    return true;
}

function show_selected_changes()
{
    try {
        var selected_indeces = _get_selected_indeces();
        var diff = _g_replacer.diff_from_indeces(selected_indeces.length,
                                                 selected_indeces);
        ko.launch.diff(diff, "Selected Changes");
    } catch(ex) {
        log.exception(ex);
    }
}

function show_marked_changes()
{
    try {
        var diff = _g_replacer.marked_diff();
        ko.launch.diff(diff, "Marked Changes");
    } catch(ex) {
        log.exception(ex);
    }
}

function make_changes()
{
    window.arguments[0].replacer = _g_replacer;
    return true;
}

function cancel()
{
    if (!_g_replacer.isAlive() && _g_replacer.num_hits == 0) {
        // No need to confirm.
    } else {
        var answer = ko.dialogs.customButtons(
                "Are you sure you want to cancel and throw away the "
                    + "determined replacements?",
                ["Continue", "Yes, Cancel"],
                "Continue");
        if (answer != "Yes, Cancel") {
            // Cancel the 'cancel'.
            return false;
        }
    }

    _g_replacer.stop();
    
    // Return semantics:
    //  replacer == null        means replacement was aborted
    //  replacer is empty       means no hits were found
    if (_g_replacer.num_hits == 0) {
        window.arguments[0].replacer = _g_replacer;
    } else {
        window.arguments[0].replacer = null;
    }
    
    return true;
}



//---- internal support stuff
    
function _init_widgets()
{
    widgets = new Object();
    widgets.dialog = document.getElementById("dialog-confirm-repl");
    widgets.accept_btn = widgets.dialog.getButton("accept");
    widgets.cancel_btn = widgets.dialog.getButton("cancel");

    widgets.repls_notebox = document.getElementById("repls-notebox");
    widgets.repls = document.getElementById("repls");
    widgets.status_img = document.getElementById("status-img");
    widgets.status_lbl = document.getElementById("status-lbl");
    widgets.show_selected_changes_btn = document.getElementById("show-selected-changes-btn");
    widgets.show_marked_changes_btn = document.getElementById("show-marked-changes-btn");
}

function _init()
{
    widgets.accept_btn.setAttribute("label", "Make Changes")
    widgets.accept_btn.setAttribute("accesskey", "M");
    widgets.accept_btn.setAttribute("disabled", true);

    widgets.cancel_btn.setAttribute("label", "Cancel")
    widgets.cancel_btn.setAttribute("accesskey", "C");

    var async_svc = Components.classes["@activestate.com/koAsyncService;1"]
            .getService(Components.interfaces.koIAsyncService);
    widgets.status_img.setAttribute("src", async_svc.asynchronous_icon_url);

    // Hook up and start the "Replace in Files" process.
    var args = window.arguments[0];
    _g_controller = new Controller();
    _g_replacer = _g_find_svc.confirmreplaceallinfiles(
        args.pattern, args.repl, args.context.cwd, _g_controller);
    widgets.repls.treeBoxObject.view = _g_replacer;
    _g_replacer.start();
}


function _get_selected_indeces()
{
    var selected_indeces = Array();
    var selection = widgets.repls.view.selection;
    var num_ranges = selection.getRangeCount();
    for (var i = 0; i < num_ranges; ++i) {
        var min = {}, max = {};
        selection.getRangeAt(i, min, max);
        for (var j = min.value; j <= max.value; ++j) {
            selected_indeces.push(j);
        }
    }
    return selected_indeces;
}


function _disable_widget(widget) {
    widget.setAttribute("disabled", "true");
}
function _enable_widget(widget) {
    if (widget.hasAttribute("disabled")) {
        widget.removeAttribute("disabled");
    }
}



//---- Controller component for koIFindService to manage the UI.

function Controller()
{
    this.log = log;
    this._have_had_first_report_with_hits = false;

    this.num_hits = 0;
    this.num_paths_with_hits = 0;
    this.num_paths_searched = 0;
}
Controller.prototype.constructor = Controller;

Controller.prototype.QueryInterface = function(iid) {
    if (!iid.equals(Components.interfaces.koIConfirmReplaceController) &&
        !iid.equals(Components.interfaces.nsISupports)) {
        throw Components.results.NS_ERROR_NO_INTERFACE;
    }
    return this;
}

Controller.prototype.report = function(num_hits, num_paths_with_hits,
                                       num_paths_searched)
{
    try {
        this.num_hits = num_hits;
        this.num_paths_with_hits = num_paths_with_hits;
        this.num_paths_searched = num_paths_searched;

        if (!this._have_had_first_report_with_hits && num_hits != 0) {
            // When we have the first hit, select that row.
            widgets.repls.view.selection.select(0);
            widgets.repls.focus();
            _enable_widget(widgets.show_marked_changes_btn);
            this._have_had_first_report_with_hits = true;
        }
        
        var hits_s_str = (num_hits == 1 ? "": "s");
        var paths_s_str = (num_paths_searched == 1 ? "": "s");
        widgets.status_lbl.setAttribute("value",
            num_hits + " replacement" + hits_s_str
            + " in " + num_paths_with_hits + " of "
            + num_paths_searched + " file" + paths_s_str + " searched");
    } catch(ex) {
        this.log.exception(ex);
    }
}

Controller.prototype.done = function()
{
    try {
        if (this.num_hits == 0) {
            widgets.status_img.setAttribute("src",
                "chrome://famfamfamsilk/skin/icons/exclamation.png");
            widgets.status_lbl.setAttribute("value",
                "The pattern was not found ("
                + this.num_paths_searched + " files searched).");

            widgets.cancel_btn.setAttribute("label", "Close");
            widgets.cancel_btn.setAttribute("accesskey", "s");

            widgets.accept_btn.removeAttribute("default");
            widgets.cancel_btn.setAttribute("default", "true");
            widgets.dialog.setAttribute("defaultButton", "cancel");
        } else {
            widgets.status_img.setAttribute("src",
                "chrome://famfamfamsilk/skin/icons/information.png");
            widgets.accept_btn.removeAttribute("disabled");
        }
    } catch(ex) {
        this.log.exception(ex);
    }
}


