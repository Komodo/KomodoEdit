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

/* Komodo's Find and Replace dialog (rev 2).
 *
 */

//---- globals

var log = ko.logging.getLogger("find");
//log.setLevel(ko.logging.LOG_DEBUG);

var parentWindow = opener;    // a hook back to the parent window
var g_find_svc = null;
var _gFindContext; // the context in which to search
var widgets = null; // object storing interesting XUL element references


//---- public methods for the dialog

function on_load() {
    try {
        g_find_svc = Components.classes["@activestate.com/koFindService;1"].
                   getService(Components.interfaces.koIFindService);
        _init_widgets();
        window.focus();
        update_replace_ui();
        update_search_in_ui();
    } catch (ex) {
        log.exception(ex);
    }    
}

function on_unload() {
}

function update_replace_ui() {
    var repl = widgets.opt_repl.checked;
    _collapse_widget(widgets.repl_lbl, !repl);
    _collapse_widget(widgets.repl, !repl);
    update_button_ui();
}

function update_search_in_ui() {
    switch (widgets.search_in_menu.value) {
    case "files":
        _collapse_widget(widgets.dirs_row, false);
        _collapse_widget(widgets.subdirs_row, false);
        _collapse_widget(widgets.include_row, false);
        _collapse_widget(widgets.exclude_row, false);
        break;
    default:
        _collapse_widget(widgets.dirs_row, true);
        _collapse_widget(widgets.subdirs_row, true);
        _collapse_widget(widgets.include_row, true);
        _collapse_widget(widgets.exclude_row, true);
    }
    update_button_ui();
    window.sizeToContent();
}

function update_button_ui() {
    //TODO:
    // - set the correct default button
    // - whither "Display results in Find Results 2 tab" checkbox?
    // - whither "Show 'Replace All' Results" checkbox?
    
    if (widgets.opt_repl.checked) {
        switch (widgets.search_in_menu.value) {
        case "project":
        case "files":
            // Replace in Files: Replace All, Close, Help
            dump("update_button_ui: replace in files\n");
            _collapse_widget(widgets.find_prev_btn, true);
            _collapse_widget(widgets.find_next_btn, true);
            _collapse_widget(widgets.replace_btn, true);
            _collapse_widget(widgets.find_all_btn, true);
            _collapse_widget(widgets.replace_all_btn, false);
            //_collapse_widget(widgets.mark_all_btn, true);
            break
        default:
            // Replace: Find Next, Replace*, Replace All, Close, Help
            dump("update_button_ui: replace\n");
            _collapse_widget(widgets.find_prev_btn, true);
            _collapse_widget(widgets.find_next_btn, false);
            _collapse_widget(widgets.replace_btn, false);
            _collapse_widget(widgets.find_all_btn, true);
            _collapse_widget(widgets.replace_all_btn, false);
            //_collapse_widget(widgets.mark_all_btn, true);
        }
    } else {
        switch (widgets.search_in_menu.value) {
        case "project":
        case "files":
            // Find in Files: Find All*, Close, Help
            dump("update_button_ui: find in files\n");
            _collapse_widget(widgets.find_prev_btn, true);
            _collapse_widget(widgets.find_next_btn, true);
            _collapse_widget(widgets.replace_btn, true);
            _collapse_widget(widgets.find_all_btn, false);
            _collapse_widget(widgets.replace_all_btn, true);
            //_collapse_widget(widgets.mark_all_btn, true);
            break
        default:
            // Find: Find Previous, Find Next*, Find All, Mark All, Close, Help
            dump("update_button_ui: find\n");
            _collapse_widget(widgets.find_prev_btn, false);
            _collapse_widget(widgets.find_next_btn, false);
            _collapse_widget(widgets.replace_btn, true);
            _collapse_widget(widgets.find_all_btn, false);
            _collapse_widget(widgets.replace_all_btn, true);
            //_collapse_widget(widgets.mark_all_btn, false);
        }
    }
}

function toggle_error() {
    if (widgets.pattern_error_box.hasAttribute("collapsed")) {
        widgets.pattern_error_box.removeAttribute("collapsed");
    } else {
        widgets.pattern_error_box.setAttribute("collapsed", "true");
    }
}


//---- internal support stuff

// Load the global 'widgets' object, which contains references to
// interesting elements in the dialog.
function _init_widgets()
{
    widgets = new Object();

    widgets.pattern = document.getElementById('pattern');
    widgets.repl_lbl = document.getElementById('repl-lbl');
    widgets.repl = document.getElementById('repl');

    widgets.opt_repl = document.getElementById('opt-repl');

    widgets.pattern_error_box = document.getElementById('pattern-error-box');
    
    widgets.search_in_menu = document.getElementById('search-in-menu');

    widgets.dirs_row = document.getElementById('dirs-row');
    widgets.subdirs_row = document.getElementById('subdirs-row');
    widgets.include_row = document.getElementById('include-row');
    widgets.exclude_row = document.getElementById('exclude-row');

    widgets.find_prev_btn = document.getElementById('find-prev-btn');
    widgets.find_next_btn = document.getElementById('find-next-btn');
    widgets.replace_btn = document.getElementById('replace-btn');
    widgets.find_all_btn = document.getElementById('find-all-btn');
    widgets.replace_all_btn = document.getElementById('replace-all-btn');
    //widgets.mark_all_btn = document.getElementById('mark-all-btn');
    //widgets.close_btn = document.getElementById('close-btn');
    widgets.help_btn = document.getElementById('help-btn');
}

function _toggle_collapse(widget) {
    if (widget.hasAttribute("collapsed")) {
        widget.removeAttribute("collapsed");
    } else {
        widget.setAttribute("collapsed", "true");
    }
}

function _collapse_widget(widget, collapse) {
    if (collapse) {
        widget.setAttribute("collapsed", "true");
    } else {
        widget.removeAttribute("collapsed");
    }
}
