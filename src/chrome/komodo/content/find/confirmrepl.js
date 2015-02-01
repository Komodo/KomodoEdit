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

xtk.include("controller");

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
var _g_controller = null;   // FindReplaceController instance managing this dialog's UI.



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

function filter_skipped_paths(checkbox)
{
    try {
        _g_replacer.filterSkippedPaths(checkbox.checked);
    } catch(ex) {
        log.exception(ex);
    }
}

function _set_selected_checkboxes(value)
{
    try {
        var selected_indeces = _get_selected_indeces();
        var treeCol = widgets.repls.columns.getFirstColumn();
        var out = {};
        for (var i=0; i < selected_indeces.length; i++) {
            _g_replacer.setCellValue(selected_indeces[i], treeCol, value);
        }
    } catch(ex) {
        log.exception(ex);
    }
}

function check_selected()
{
    _set_selected_checkboxes("true");
}

function uncheck_selected()
{
    _set_selected_checkboxes("false");
}

function associateAsLanguage(elem) {
    try {
        var lang = elem.getAttribute("language");
        var path = _g_replacer.getPath(_get_selected_indeces()[0]);
        var bname = ko.uriparse.baseName(path);
        var ext = ko.uriparse.ext(path);
        var pattern;
        if (!ext || ext == bname) {
            // Take the whole name then.
            pattern = ko.uriparse.baseName(path);
        } else {
            pattern = "*" + ext;
        }
        var answer = ko.dialogs.customButtons(
                "Create association '" + ext +"' to language '" + lang + "'?",
                ["Associate", "Cancel"],
                "Associate");
        if (answer == "Associate") {
            // Save the new association.
            var langRegistrySvc = Components.classes["@activestate.com/koLanguageRegistryService;1"]
                                    .getService(Components.interfaces.koILanguageRegistryService);
            var patternsObj = new Object();
            var languageNamesObj = new Object();
            langRegistrySvc.getFileAssociations(new Object(), patternsObj,
                                                new Object(), languageNamesObj);
            var patterns = patternsObj.value;
            var languageNames = languageNamesObj.value;
            patterns.push(pattern);
            languageNames.push(lang);
            langRegistrySvc.saveFileAssociations(patterns.length, patterns,
                                                 languageNames.length, languageNames);
        }
    } catch(ex) {
        log.exception(ex);
    }
}

function updateLanguageCommandElement(elem)
{
    if (elem.nodeName == "menuitem" && elem.getAttribute("oncommand")) {
        elem.setAttribute("oncommand", "associateAsLanguage(this)");
    }
    var limit = elem.childNodes.length;
    for (var i=0; i < limit; i++) {
        updateLanguageCommandElement(elem.childNodes[i]);
    }
}

function updateAssociateLanguageMenu(menupopup)
{
    try {
        if (!menupopup.hasAttribute("komodo_language_menu_already_built")) {
            // Build the menu;
            ko.uilayout.buildViewAsLanguageMenu(menupopup);
            // Update commands
            updateLanguageCommandElement(menupopup);
            menupopup.setAttribute("komodo_language_menu_already_built", "true");
        }
    } catch(ex) {
        log.exception(ex);
    }
}

function addIgnoredAssociation(elem) {
    try {
        var path = _g_replacer.getPath(_get_selected_indeces()[0]);
        var bname = ko.uriparse.baseName(path);
        var ext = ko.uriparse.ext(path);
        var pattern = ext;
        if (!ext || ext == bname) {
            // Take the whole name then.
            pattern = ko.uriparse.baseName(path);
        } else {
            pattern = "*" + ext;
        }
        var answer = ko.dialogs.customButtons(
                "Exclude filepaths like '" + pattern +"'?",
                ["Yes, Exclude", "Cancel"],
                "Yes, Exclude");
        if (answer == "Yes, Exclude") {
            // Save the new association.
            var prefs = Components.classes["@activestate.com/koPrefService;1"]
                .getService(Components.interfaces.koIPrefService).prefs;
            var excludePrefs = prefs.getPref("find-excludeFiletypes");
            excludePrefs.appendString(pattern);
            // Update the excludes textbox in the find dialog.
            var excludes_textbox = opener.document.getElementById("excludes");
            if (excludes_textbox) {
                var pathsep = navigator.platform.startsWith("Win") ? ";" : ":";
                var excludes = excludes_textbox.value.split(pathsep);
                excludes.push(pattern);
                excludes_textbox.value = excludes.join(pathsep);
                opener.update("excludes");
            }
        }
    } catch(ex) {
        log.exception(ex);
    }
}

function onTreeContextMenuShowing()
{
    try {
        var assoc_menuitem = document.getElementById("context_menu_associate");
        var ignore_menuitem = document.getElementById("context_menu_ignore");
        assoc_menuitem.setAttribute("disabled", "true");
        ignore_menuitem.setAttribute("disabled", "true");
        var selected_indeces = _get_selected_indeces();
        if (selected_indeces.length == 1) {
            var idx = selected_indeces[0];
            if (_g_replacer.getSkippedReason(idx) == Components.interfaces.koIConfirmReplacerInFiles.SKIPPED_UNKNOWN_LANG) {
                assoc_menuitem.removeAttribute("disabled");
                ignore_menuitem.removeAttribute("disabled");
            }
        }
    } catch(ex) {
        log.exception(ex);
    }
}

function show_selected_changes()
{
    try {
        var selected_indeces = _get_selected_indeces();
        var diff = _g_replacer.diff_from_indeces(selected_indeces.length,
                                                 selected_indeces);
        ko.launch.diff(diff, "Selected Changes", null,
                       {modalChild: navigator.platform.match(/^Mac/)});
    } catch(ex) {
        log.exception(ex);
    }
}

function show_marked_changes()
{
    try {
        var diff = _g_replacer.marked_diff();
        ko.launch.diff(diff, "Marked Changes", null,
                       {modalChild: navigator.platform.match(/^Mac/)});
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
    _g_controller = new FindReplaceController();
    _g_replacer = _g_find_svc.confirmreplaceallinfiles(
        args.pattern, args.repl, args.context, _g_controller);
    if (document.getElementById('filter-skipped-paths').checked) {
        _g_replacer.filterSkippedPaths(true);
    }
    
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

function FindReplaceController()
{
    this.log = log;
    this._have_had_first_report_with_hits = false;

    this.num_hits = 0;
    this.num_paths_with_hits = 0;
    this.num_paths_searched = 0;
    this.num_paths_skipped = 0;
}
FindReplaceController.prototype.constructor = xtk.Controller;

FindReplaceController.prototype.QueryInterface = function(iid) {
    if (!iid.equals(Components.interfaces.koIConfirmReplaceController) &&
        !iid.equals(Components.interfaces.nsISupports)) {
        throw Components.results.NS_ERROR_NO_INTERFACE;
    }
    return this;
}

FindReplaceController.prototype.report = function(num_hits, num_paths_with_hits,
                                       num_paths_searched,
                                       num_paths_skipped)
{
    try {
        this.num_hits = num_hits;
        this.num_paths_with_hits = num_paths_with_hits;
        this.num_paths_searched = num_paths_searched;
        this.num_paths_skipped = num_paths_skipped;

        if (!this._have_had_first_report_with_hits && num_hits != 0) {
            // When we have the first hit, select that row.
            widgets.repls.view.selection.select(0);
            widgets.repls.focus();
            _enable_widget(widgets.show_marked_changes_btn);
            this._have_had_first_report_with_hits = true;
        }
        
        var hits_s_str = (num_hits == 1 ? "": "s");
        var paths_s_str = (num_paths_searched == 1 ? "": "s");
        var status = num_hits + " replacement" + hits_s_str
                + " in " + num_paths_with_hits + " of "
                + num_paths_searched + " file" + paths_s_str + " searched";
        if (num_paths_skipped > 0) {
            var skipped_s_str = (num_paths_skipped == 1 ? "": "s");
            status += " ("+num_paths_skipped+" path"+skipped_s_str+" skipped)";
        }
        widgets.status_lbl.setAttribute("value", status);
    } catch(ex) {
        this.log.exception(ex);
    }
}

FindReplaceController.prototype.done = function()
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


