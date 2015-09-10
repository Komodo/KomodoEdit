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
 * TODO: document usage, esp. allowed 'mode' window.arguments
 *
 * TODOs:
 * - better error message handling (perhaps validate with lexregex.py)
 * - all spec'd replace in files guards
 * - find results tab enhancements (grouping/view opts, handling
 *   replacement warnings/errors, filter, redo)
 */

//---- globals

var { classes: Cc, interfaces: Ci, utils: Cu } = Components;

var log = ko.logging.getLogger("find.dialog");
//log.setLevel(ko.logging.LOG_DEBUG);

var koIFindContext = Components.interfaces.koIFindContext;
var koIFindOptions = Components.interfaces.koIFindOptions;

var widgets = null; // object storing interesting XUL element references
var gFindSvc = null;
var _g_find_context; // the context in which to search
var _g_collection_context; // cache of 'collection' arg passed in, if any
var _g_curr_project_context; // find context for curr proj, if any

var _g_btns_enabled_for_pattern = true;    // cache for update("pattern")
var _g_curr_default_btn = null;         // cache for _update_mode_ui()


var _g_prefs = null;
var _g_save_in_files_context = false; // Whether to save "in files" context on exit.

var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
      .getService(Components.interfaces.nsIStringBundleService)
      .createBundle("chrome://komodo/locale/find/find2.properties");


//---- public methods for the dialog

if ( ! opener) opener = require("ko/windows").getMain();

function on_load() {
    try {
        _g_prefs = Components.classes["@activestate.com/koPrefService;1"]
            .getService(Components.interfaces.koIPrefService).prefs;
        gFindSvc = Components.classes["@activestate.com/koFindService;1"].
                   getService(Components.interfaces.koIFindService);
        _init_widgets();

        // Necessary for re-launching (i.e. Ctrl+F when the dialog is already open).
        window.focus();

        _init();
        
        document.addEventListener("keyup", function(e) {
            if (e.keyCode == KeyEvent.DOM_VK_ESCAPE)
                opener.document.getElementById("findReplaceWrap").setAttribute("collapsed", "true");
        });
    } catch (ex) {
        log.exception(ex);
    }
}

function on_unload() {
    if (_g_save_in_files_context) {
        var value = widgets.search_in_menu.value;
        if (value == "files"
            || value == "open-files"
            //TODO: Can't restore collection unless we save the 'collection
            //      context instance.
            //|| value == "collection"
            || value == "curr-project"
            ) {
            _g_prefs.setStringPref("find-lastInFilesContext", value);
        }
    }
}

function on_focus(event) {
    //TODO: Change to only do this for one phase. Currently this is
    //      calling reset_find_context() for AT_TARGET and BUBBLING_PHASE
    //      phases.
    if (event.target == document) {  // focus of the *Window*
        reset_find_context("on_focus");
    }
}

/**
 * Update as appropriate for some change in the dialog.
 *
 * @param {string} changed The name of the thing that changed. If
 *      null or not specified *everything* is updated (used for dialog
 *      initialization).
 */
function update(changed /* =null */) {
    if (typeof(changed) == "undefined") changed = null;
    
    var mode_changed = false;
    var ui_changed = false;
    var opts = gFindSvc.options;

    // "Multiline" checkbox state changed.
    if (changed == null || changed == "multiline") {
        opts.multiline = widgets.opt_multiline.checked;
        if (widgets.opt_multiline.checked) {
            _collapse_widget(widgets.pattern, true);
            _collapse_widget(widgets.multiline_pattern, false);
            widgets.pattern_deck.selectedIndex = 1;
            if (widgets.curr_pattern) {
                widgets.multiline_pattern.value = widgets.curr_pattern.value;
            }
            widgets.curr_pattern = widgets.multiline_pattern;

            _collapse_widget(widgets.repl, true);
            _collapse_widget(widgets.multiline_repl, false);
            widgets.repl_deck.selectedIndex = 1;
            if (widgets.curr_repl) {
                widgets.multiline_repl.value = widgets.curr_repl.value;
            }
            widgets.curr_repl = widgets.multiline_repl;
        } else {
            _collapse_widget(widgets.pattern, false);
            _collapse_widget(widgets.multiline_pattern, true);
            widgets.pattern_deck.selectedIndex = 0;
            if (widgets.curr_pattern) {
                widgets.pattern.value = widgets.curr_pattern.value;
            }
            widgets.curr_pattern = widgets.pattern;

            _collapse_widget(widgets.repl, false);
            _collapse_widget(widgets.multiline_repl, true);
            widgets.repl_deck.selectedIndex = 0;
            if (widgets.curr_repl) {
                widgets.repl.value = widgets.curr_repl.value;
            }
            widgets.curr_repl = widgets.repl;
        }
        ui_changed = true;

        // Don't muck with the focus for dialog init (changed=null).
        if (changed == "multiline") {
            widgets.curr_pattern.focus();
        }
    }
    
    // "Replace" checkbox state changed.
    if (changed == null || changed == "replace") {
        var repl = widgets.opt_repl.checked;
        if (repl) {
            _enable_widget(widgets.repl, !repl);
            _enable_widget(widgets.multiline_repl, !repl);
        } else {
            _disable_widget(widgets.repl, !repl);
            _disable_widget(widgets.multiline_repl, !repl);
        }
        
        if (repl) {
            document.documentElement.classList.add("mode-replace");
        } else {
            document.documentElement.classList.remove("mode-replace");
        }

        // Don't muck with the focus for dialog init (changed=null)
        // because we want the pattern widget to get the focus, even
        // in replace mode.
        if (changed == "replace") {
            if (repl) {
                //HACK: Not sure why this needs to be in setTimeout to work.
                window.setTimeout(
                    function() { widgets.curr_repl.focus(); },
                    100);
            } else {
                widgets.curr_pattern.focus();
            }
        }
        mode_changed = true;
    }

    // "Search in" menulist selection changed.
    if (changed == null || changed == "search-in") {
        var search_in = widgets.search_in_menu.value;
        switch (search_in) {
        case "files":
            _collapse_widget(widgets.dirs_row, false);
            _collapse_widget(widgets.subdirs_row, false);
            _collapse_widget(widgets.includes_row, false);
            _collapse_widget(widgets.excludes_row, false);
            break;
        default:
            _collapse_widget(widgets.dirs_row, true);
            _collapse_widget(widgets.subdirs_row, true);
            _collapse_widget(widgets.includes_row, true);
            _collapse_widget(widgets.excludes_row, true);

            // Persist the context type in some cases. This is used
            // to tell cmd_findNext and cmd_findPrevious whether to
            // cycle through the current doc or all open docs.
            if (search_in == "document" || search_in == "selection") {
                gFindSvc.options.preferredContextType = koIFindContext.FCT_CURRENT_DOC;
            } else if (search_in == "open-files") {
                gFindSvc.options.preferredContextType = koIFindContext.FCT_ALL_OPEN_DOCS;
            }
        }
        mode_changed = true;
    }
    
    // The pattern value changed.
    if (changed == null || changed == "pattern") {
        if (widgets.curr_pattern.value && !_g_btns_enabled_for_pattern) {
            // We changed from no pattern string to some pattern string.
            // Enable the relevant buttons.
            _enable_widget(widgets.find_prev_btn);
            _enable_widget(widgets.find_next_btn);
            _enable_widget(widgets.replace_btn);
            _enable_widget(widgets.find_all_btn);
            _enable_widget(widgets.replace_all_btn);
            _enable_widget(widgets.mark_all_btn);
            _g_btns_enabled_for_pattern = true;
        } else if (!widgets.curr_pattern.value && _g_btns_enabled_for_pattern) {
            // We changed from a pattern string to no pattern string.
            // Disable the relevant buttons.
            _disable_widget(widgets.find_prev_btn);
            _disable_widget(widgets.find_next_btn);
            _disable_widget(widgets.replace_btn);
            _disable_widget(widgets.find_all_btn);
            _disable_widget(widgets.replace_all_btn);
            _disable_widget(widgets.mark_all_btn);
            _g_btns_enabled_for_pattern = false;
        }
    }
    
    if (changed == null || changed == "regex") {
        opts.patternType = (widgets.opt_regex.checked ?
            koIFindOptions.FOT_REGEX_PYTHON : koIFindOptions.FOT_SIMPLE);
        
        //_collapse_widget(widgets.pattern_btn, !widgets.opt_regex.checked);
    }
    if (changed == "case") {
        // Skip this for initialization (changed=null).

        // Advance the checkbox to the next state.
        switch (widgets.opt_case.value) {
        case "ignore-case":
            _set_case_widget("match-case");
            break;
        case "match-case":
            _set_case_widget("smart-case");
            break;
        case "smart-case":
            _set_case_widget("ignore-case");
            break;
        }

        // Save the current state on the global find options.
        switch (widgets.opt_case.value) {
        case "ignore-case":
            opts.caseSensitivity = koIFindOptions.FOC_INSENSITIVE;
            break;
        case "match-case":
            opts.caseSensitivity = koIFindOptions.FOC_SENSITIVE;
            break;
        case "smart-case":
            opts.caseSensitivity = koIFindOptions.FOC_SMART;
            break;
        }
    }
    if (changed == null || changed == "word") {
        opts.matchWord = widgets.opt_word.checked;
    }
    if (changed == null || changed == "dirs") {
        opts.encodedFolders = widgets.dirs.value;
    }
    if (changed == null || changed == "search-in-subdirs") {
        opts.searchInSubfolders = widgets.search_in_subdirs.checked;
    }
    if (changed == null || changed == "includes") {
        opts.encodedIncludeFiletypes = widgets.includes.value;
    }
    if (changed == null || changed == "excludes") {
        opts.encodedExcludeFiletypes = widgets.excludes.value;
    }
    if (changed == null || changed == "show-replace-all-results") {
        opts.showReplaceAllResults = widgets.show_replace_all_results.checked;
    }
    if (changed == null || changed == "confirm-replacements") {
        opts.confirmReplacementsInFiles = widgets.confirm_replacements_in_files.checked;
    }

    if (mode_changed) {
        reset_find_context("update: mode_changed");
        _update_mode_ui();
    }
    if (mode_changed || ui_changed) {
        window.sizeToContent();
    }
}

function regex_escape_ignoring_whitespace(text) {
    var specials = [
          '/', '\\', '.', '*', '+', '?', '|',
          '(', ')', '[', ']', '{', '}', '$', '^',
    ];
    var escape_re = new RegExp('(\\' + specials.join('|\\') + ')', 'g');
    return text.replace(escape_re, '\\$1');
}

function regex_escape(ignore_whitespace /* false */)
{
    try {
        var textbox = widgets.curr_pattern;
        var selection = textbox.value.slice(textbox.selectionStart,
                                            textbox.selectionEnd);
        var escaped;
        if (selection) {
            if (ignore_whitespace) {
                escaped = regex_escape_ignoring_whitespace(selection);
            } else {
                escaped = gFindSvc.regex_escape_string(selection);
            }
            var selStart = textbox.selectionStart;
            textbox.value = textbox.value.slice(0, selStart)
                + escaped + textbox.value.slice(textbox.selectionEnd);
            textbox.focus();
            textbox.setSelectionRange(selStart,
                                      selStart + escaped.length);
        } else {
            if (ignore_whitespace) {
                escaped = regex_escape_ignoring_whitespace(textbox.value);
            } else {
                escaped = gFindSvc.regex_escape_string(textbox.value);
            }
            textbox.value = escaped;
            textbox.focus();
        }
    } catch (ex) {
        log.exception(ex);
    }
}

// Insert the given "shortcut" into the given "textbox" widget, focus it,
// and select the inserted text.
function _insert(textbox, shortcut)
{
    var sel_start = textbox.selectionStart;
    var value = textbox.value.slice(0, sel_start);
    value += shortcut;
    value += textbox.value.slice(textbox.selectionEnd);
    textbox.value = value;
    textbox.focus();
    textbox.setSelectionRange(sel_start,
                              sel_start + shortcut.length);
}

function regex_insert_shortcut(widget)
{
    try {
        var shortcut = widget.getAttribute("shortcut");
        var ellipsis_idx = shortcut.indexOf("...");
        var textbox = widgets.curr_pattern;

        // For bounding shortcuts (e.g., '(...)' is a bounding shortcut):
        // if there is a selection put it in as the '...' part, otherwise
        // insert and select the '...'.
        if (ellipsis_idx != -1) {
            var selection = textbox.value.slice(textbox.selectionStart,
                                                textbox.selectionEnd);
            if (selection) {
                shortcut = shortcut.replace(/\.\.\./, selection);
                _insert(textbox, shortcut);
            } else {
                _insert(textbox, shortcut);
                textbox.setSelectionRange(
                    textbox.selectionStart + ellipsis_idx,
                    textbox.selectionStart + ellipsis_idx + 3);
            }
        }
        // For non-bounding shortcuts (e.g., '^' is a non-bounding
        // shortcut) replace the selection if there is one or just insert
        // at the current pos.
        else {
            _insert(textbox, shortcut);
        }
    } catch (ex) {
        log.exception(ex);
    }
}



/**
 * Functions to adding info/warn/error level message notifications to
 * the dialog.
 */
function msg_clear() {
    _msg_erase();
    widgets.msg_deck.selectedIndex = 0;
}
function msg_callback(level, context, msg) {
    switch (level) {
    case "info":
        msg_info(msg);
        break;
    case "warn":
        msg_warn(msg);
        break;
    case "error":
        msg_error(msg);
        break;
    default:
        log.error("unexpected msg level: "+level);
    }
}
function _msg_erase() {
    widgets.msg_deck.parentNode.classList.add("collapsed");
    // Clear text nodes from the current panel <description>.
    if (widgets.msg_deck.selectedIndex != 0) {
        var elem = widgets.msg_deck.selectedPanel;
        elem = document.getElementsByTagName("description")[0];
        while (elem.firstChild) {
            elem.removeChild(elem.firstChild);
        }
        // Intentionally put some "empty" content in here because
        // window.sizeToContent() on "<description/>" is slightly shorter
        // than on "<description>blank</description>" and we don't want
        // the dialog size jitter.
        elem.appendChild(document.createTextNode("blank"));
    }
}
function _msg_write(deck_idx, desc, msg) {
    _msg_erase();
    widgets.msg_deck.parentNode.classList.remove("collapsed");
    desc.removeChild(desc.firstChild); // remove the "blank" text node
    desc.appendChild(document.createTextNode(msg));
    widgets.msg_deck.selectedIndex = deck_idx;
    window.sizeToContent();
}
function msg_info(msg) {
    try {
        _msg_write(1, widgets.msg_info, msg);
    } catch (ex) {
        log.exception(ex);
    }
}
function msg_warn(msg) {
    try {
        _msg_write(2, widgets.msg_warn, msg);
    } catch (ex) {
        log.exception(ex);
    }
}
function msg_error(msg) {
    try {
        _msg_write(3, widgets.msg_error, msg);
    } catch (ex) {
        log.exception(ex);
    }
}


/**
 * Change the "Search in:" menulist to the given value.
 */
function search_in(value)
{
    try {
        widgets.search_in_menu.value = value;
        update('search-in');
    } catch(ex) {
        log.exception(ex);
    }
}


/**
 * Handle the onfocus event on the 'dirs' textbox.
 */
function dirs_on_focus(widget, event)
{
    try {
        widget.setSelectionRange(0, widget.textLength);
        // For textbox-autocomplete (TAC) of directories on this widget we
        // need a cwd with which to interpret relative paths. The chosen
        // cwd is that of the current file in the main editor window.
        if (event.target.nodeName == 'html:input') { 
            var textbox = widget.parentNode.parentNode.parentNode;
            var cwd = ko.windowManager.getMainWindow().ko.window.getCwd();
            textbox.searchParam = ko.stringutils.updateSubAttr(
                textbox.searchParam, 'cwd', cwd);            
        }
    } catch(ex) {
        log.exception(ex);
    }
}


function browse_for_dirs() {
    try {
        var obj = new Object();
        obj.encodedFolders = widgets.dirs.value;
        var origWindow = ko.windowManager.getMainWindow();
        obj.cwd = origWindow.ko.window.getCwd();
        window.openDialog("chrome://komodo/content/find/browseForDirs.xul",
                          "_blank",
                          "chrome,modal,titlebar,resizable",
                          obj);
        if (obj.retval != "Cancel") {
            widgets.dirs.value = obj.encodedFolders;
            update("dirs");
        }
    } catch(ex) {
        log.exception(ex);
    }
}


function find_prev() {
    find_next(true);
}

function find_next(backward /* =false */) {
    if (typeof(backward) == "undefined" || backward == null) backward = false;

    try {
        msg_clear();
        
        var pattern = widgets.curr_pattern.value;
        if (! pattern) {
            return;
        }
    
        // This handles, for example, the context being "search in
        // selection", but there is no selection.
        if (! _g_find_context) {
            // Make one attempt to get the context again: state in the
            // main editor may have changed such that getting a context is
            // possible.
            reset_find_context("find_next");
            if (! _g_find_context) {
                return;
            }
        }
    
        if (widgets.opt_multiline.checked) {
            widgets.pattern.value = widgets.curr_pattern.value;
        }
        ko.mru.addFromACTextbox(widgets.pattern);
    
        //TODO: Icky. The "searchBackward" state being set on the global
        //      object then restored is gross. koIFindOptions should be
        //      an argument to the Find_* functions. The macro versions
        //      of the Find_* functions have to do this same save/restore
        //      dance.
        gFindSvc.options.searchBackward = backward;
    
        var mode = (widgets.opt_repl.checked ? "replace" : "find");
        var found_one = ko.find.findNext(opener, _g_find_context, pattern, mode,
                                      false,         // quiet
                                      true,          // useMRU
                                      msg_callback); // msgHandler
        // Bug 75574: never want to save searchBackward=true to prefs.
        gFindSvc.options.searchBackward = false;
    
        if (!found_one) {
            // If no match was hilighted then it is likely that the user will
            // now want to enter a different pattern. (Copying Word's
            // behaviour here.)
            widgets.curr_pattern.focus();
        }
    } catch (ex) {
        log.exception(ex);
    }
}

function find_all() {
    try {
        msg_clear();
        var pattern = widgets.curr_pattern.value;
        if (! pattern) {
            return;
        }
    
        // This handles, for example, the context being "search in
        // selection", but there is no selection.
        if (! _g_find_context) {
            // Make one attempt to get the context again: state in the
            // main editor may have changed such that getting a context is
            // possible.
            reset_find_context("find_all");
            if (! _g_find_context) {
                return;
            }
        }

        if (widgets.opt_multiline.checked) {
            widgets.pattern.value = widgets.curr_pattern.value;
        }
        ko.mru.addFromACTextbox(widgets.pattern);

        // Always reset the find session for find all
        var findSessionSvc = Components.classes["@activestate.com/koFindSession;1"].
                                getService(Components.interfaces.koIFindSession);
        findSessionSvc.Reset();

        if (_g_find_context.type == koIFindContext.FCT_IN_COLLECTION) {
            if (ko.find.findAllInFiles(opener, _g_find_context,
                                    pattern, null,
                                    msg_callback)) {
                window.close();
            }
            
        } else if (_g_find_context.type == koIFindContext.FCT_IN_FILES) {
            ko.mru.addFromACTextbox(widgets.dirs);
            if (widgets.includes.value)
                ko.mru.addFromACTextbox(widgets.includes);
            if (widgets.excludes.value)
                ko.mru.addFromACTextbox(widgets.excludes);
            gFindSvc.options.cwd = _g_find_context.cwd;

            if (ko.find.findAllInFiles(opener, _g_find_context,
                                    pattern, null,
                                    msg_callback)) {
                window.close();
            }

        } else {
            var found_some = ko.find.findAll(opener, _g_find_context, pattern,
                                          null,          // patternAlias
                                          msg_callback); // msgHandler
            if (found_some) {
                window.close();
            } else {
                widgets.curr_pattern.focus();
            }
        }
    } catch(ex) {
        log.exception(ex);
    }
}

function mark_all() {
    try {
        msg_clear();
        
        var pattern = widgets.curr_pattern.value;
        if (! pattern) {
            return;
        }
    
        // This handles, for example, the context being "search in
        // selection", but there is no selection.
        if (! _g_find_context) {
            // Make one attempt to get the context again: state in the
            // main editor may have changed such that getting a context is
            // possible.
            reset_find_context("mark_all");
            if (! _g_find_context) {
                return;
            }
        }
        if (_g_find_context.type == koIFindContext.FCT_IN_FILES
            || _g_find_context.type == koIFindContext.FCT_IN_COLLECTION) {
            log.warn("'Mark All' in files (i.e. files not open in "
                     + "Komodo) is not supported.");
            return;
        }

        if (widgets.opt_multiline.checked) {
            widgets.pattern.value = widgets.curr_pattern.value;
        }
        ko.mru.addFromACTextbox(widgets.pattern);

        // Always reset the find session for mark all
        var findSessionSvc = Components.classes["@activestate.com/koFindSession;1"].
                                getService(Components.interfaces.koIFindSession);
        findSessionSvc.Reset();

        var found_some = ko.find.markAll(opener, _g_find_context, pattern,
                                      null,          // patternAlias
                                      msg_callback); // msgHandler
        if (found_some) {
            window.close();
        } else {
            widgets.curr_pattern.focus();
        }
    } catch(ex) {
        log.exception(ex);
    }
}


function replace() {
    try {
        msg_clear();
        
        var pattern = widgets.curr_pattern.value;
        if (! pattern) {
            return;
        }
        var repl = widgets.curr_repl.value;
    
        // This handles, for example, the context being "search in
        // selection", but there is no selection.
        if (! _g_find_context) {
            // Make one attempt to get the context again: state in the
            // main editor may have changed such that getting a context is
            // possible.
            reset_find_context("replace");
            if (! _g_find_context) {
                return;
            }
        }
    
        if (widgets.opt_multiline.checked) {
            widgets.pattern.value = widgets.curr_pattern.value;
            widgets.repl.value = widgets.curr_repl.value;
        }
        ko.mru.addFromACTextbox(widgets.pattern);
        if (repl)
            ko.mru.addFromACTextbox(widgets.repl);
    
        gFindSvc.options.searchBackward = false;
        var found_one = ko.find.replace(opener, _g_find_context,
                pattern, repl, msg_callback);
        if (!found_one) {
            // If no match was hilighted then it is likely that the user will
            // now want to enter a different pattern. (Copying Word's
            // behaviour here.)
            widgets.curr_pattern.focus();
        }
    } catch (ex) {
        log.exception(ex);
    }
}


function replace_all() {
    try {
        msg_clear();
        
        var pattern = widgets.curr_pattern.value;
        if (! pattern) {
            return;
        }
        var repl = widgets.curr_repl.value;
    
        // This handles, for example, the context being "search in
        // selection", but there is no selection.
        if (! _g_find_context) {
            // Make one attempt to get the context again: state in the
            // main editor may have changed such that getting a context is
            // possible.
            reset_find_context("replace_all");
            if (! _g_find_context) {
                return;
            }
        }

        if (widgets.opt_multiline.checked) {
            widgets.pattern.value = widgets.curr_pattern.value;
            widgets.repl.value = widgets.curr_repl.value;
        }
        ko.mru.addFromACTextbox(widgets.pattern);
        if (repl)
            ko.mru.addFromACTextbox(widgets.repl);

        // Always reset the find session for replace all
        var findSessionSvc = Components.classes["@activestate.com/koFindSession;1"].
                                getService(Components.interfaces.koIFindSession);
        findSessionSvc.Reset();

        if (_g_find_context.type == koIFindContext.FCT_IN_COLLECTION) {
            if (ko.find.replaceAllInFiles(opener, _g_find_context,
                                       pattern, repl,
                                       gFindSvc.options.confirmReplacementsInFiles,
                                       msg_callback)) {
                window.close();
            }
        } else if (_g_find_context.type == koIFindContext.FCT_IN_FILES) {
            ko.mru.addFromACTextbox(widgets.dirs);
            if (widgets.includes.value)
                ko.mru.addFromACTextbox(widgets.includes);
            if (widgets.excludes.value)
                ko.mru.addFromACTextbox(widgets.excludes);
            gFindSvc.options.cwd = _g_find_context.cwd;

            if (ko.find.replaceAllInFiles(opener, _g_find_context,
                                       pattern, repl,
                                       gFindSvc.options.confirmReplacementsInFiles,
                                       msg_callback)) {
                window.close();
            }
        } else {
            var found_some = null;
            var found_some = ko.find.replaceAll(
                    opener, _g_find_context, pattern, repl,
                    widgets.show_replace_all_results.checked,
                    false,  /* firstOnLine */
                    msg_callback);
            if (found_some) {
                window.close();
            } else {
                widgets.curr_pattern.focus();
            }
        }
    } catch (ex) {
        log.exception(ex);
    }
}



//---- internal support stuff

// Load the global 'widgets' object, which contains references to
// interesting elements in the dialog.
function _init_widgets()
{
    if (widgets != null) {
        return; // was already called
    }
    widgets = new Object();

    widgets.pattern_deck = document.getElementById('pattern-deck');
    widgets.pattern = document.getElementById('pattern');
    widgets.pattern_btn = document.getElementById('pattern-shortcuts');
    widgets.multiline_pattern = document.getElementById('multiline-pattern');
    widgets.curr_pattern = widgets.pattern;
    widgets.repl_row = document.getElementById('repl-row');
    widgets.repl_deck = document.getElementById('repl-deck');
    widgets.repl = document.getElementById('repl');
    widgets.multiline_repl = document.getElementById('multiline-repl');
    widgets.curr_repl = widgets.repl;

    widgets.opt_regex = document.getElementById('opt-regex');
    widgets.opt_case = document.getElementById('opt-case');
    widgets.opt_word = document.getElementById('opt-word');
    widgets.opt_multiline = document.getElementById('opt-multiline');
    widgets.opt_repl = document.getElementById('opt-repl');

    widgets.msg_deck = document.getElementById('msg-deck');
    widgets.msg_info = document.getElementById('msg-info');
    widgets.msg_warn = document.getElementById('msg-warn');
    widgets.msg_error = document.getElementById('msg-error');
    
    widgets.search_in_menu = document.getElementById('search-in-menu');
    widgets.search_in_curr_project = document.getElementById('search-in-curr-project');
    widgets.search_in_collection = document.getElementById('search-in-collection');
    widgets.search_in_collection_sep = document.getElementById('search-in-collection-sep');

    widgets.dirs_row = document.getElementById('dirs-row');
    widgets.dirs = document.getElementById('dirs');
    widgets.subdirs_row = document.getElementById('subdirs-row');
    widgets.search_in_subdirs = document.getElementById('search-in-subdirs');
    widgets.includes_row = document.getElementById('includes-row');
    widgets.includes = document.getElementById('includes');
    widgets.excludes_row = document.getElementById('excludes-row');
    widgets.excludes = document.getElementById('excludes');

    widgets.find_btn_wrap = document.getElementById('find-buttons');
    widgets.find_prev_btn = document.getElementById('find-prev-btn');
    widgets.find_next_btn = document.getElementById('find-next-btn');
    widgets.replace_btn = document.getElementById('replace-btn');
    widgets.find_all_btn = document.getElementById('find-all-btn');
    widgets.replace_all_btn = document.getElementById('replace-all-btn');
    widgets.confirm_replacements_in_files = document.getElementById('confirm-replacements-in-files');
    widgets.show_replace_all_results = document.getElementById('show-replace-all-results');
    widgets.mark_all_btn = document.getElementById('mark-all-btn');
    //widgets.close_btn = document.getElementById('close-btn');
    //widgets.help_btn = document.getElementById('help-btn');
}

/**
 * Initialize the dialog from `opener.ko.launch.find2_dialog_args` data.
 */
function _init() {
    if (window.arguments) {
        var [args] = window.arguments;
    } else {
        args = opener.ko.launch.find2_dialog_args || {};
        opener.ko.launch.find2_dialog_args = null;
    }

    // Close this dialog when the opener goes away
    opener.addEventListener("unload", function unload(event) {
        window.close();
        event.target.removeEventListener(event.type, unload, false);
    }, false);

    // If there is selected text then preload the find pattern with it.
    // Unless it spans a line, then set the search context to the
    // selection.
    var scimoz = null;
    var selection = null;
    var use_selection_as_pattern = false;
    var use_selection_as_context = false;
    try {
        var curr_view = opener.ko.views.manager.currentView;
        if (curr_view && curr_view.scintilla) {
            scimoz = curr_view.scintilla.scimoz;
            selection = scimoz.selText;
        }
    } catch(ex) {
        /* pass: just don't have a current editor view */
    }
    if (selection) {
        // If the selected text has newline characters in it or *is* an entire
        // line (without the end-of-line) then "search within selection".
        // Warning: ISciMoz.getCurLine() returns the whole line minus the
        // last char. If the EOL is two chars then you only get last part.
        // I.e. 'foo\r\n' -> 'foo\r'.
        var curr_line_obj = new Object;
        scimoz.getCurLine(curr_line_obj);
        var curr_line = curr_line_obj.value;
        if (selection.search(/\n/) != -1
            || selection == curr_line.substring(0, curr_line.length-1))
        {
            use_selection_as_context = true;
            // If a user does a search within a selection then the
            // "preferred" context is the current document (rather than
            // across multiple docs).
            gFindSvc.options.preferredContextType = koIFindContext.FCT_CURRENT_DOC;
        } else {
            // Otherwise, use the current selection as the first search
            // pattern completion.
            use_selection_as_pattern = true;
        }
    }

    // Determine the default pattern.
    var default_pattern = "";
    var escape_default_pattern = false;
    if (args.pattern != null) {   /* null or undefined */
        default_pattern = args.pattern;
        escape_default_pattern = false;
    } else if (use_selection_as_pattern) {
        default_pattern = selection;
        escape_default_pattern = true;
    } else {
        // Use the last searched for pattern.
        default_pattern = ko.mru.get("find-patternMru", 0);
        escape_default_pattern = false;
    }

    // Preload with input buffer contents if any and then give focus to
    // the pattern textbox.
    // Notes:
    // - The pattern textbox will automatically select all its contents
    //   on focus. If there are input buffer contents then we do *not*
    //   want this to happen, because this will defeat the purpose of
    //   the input buffer if the user is part way through typing in
    //   characters.
    var input_buf = opener.ko.inputBuffer.finish();
    var select_all_pattern = null;
    widgets.curr_pattern.value = "";
    if (input_buf) {
        widgets.curr_pattern.value = input_buf;
        select_all_pattern = false;
    } else {
        widgets.curr_pattern.value = default_pattern;
        select_all_pattern = true;
    }

    // Set other dialog data (from the given args and from the
    // koIFindService.options).
    var opts = gFindSvc.options;
    widgets.repl.value = args.repl || "";
    widgets.opt_regex.checked
        = opts.patternType == koIFindOptions.FOT_REGEX_PYTHON;
    widgets.opt_word.checked = opts.matchWord;
    widgets.opt_multiline.checked = opts.multiline;
    widgets.dirs.value = args.dirs || opts.encodedFolders;
    widgets.search_in_subdirs.checked = opts.searchInSubfolders;
    widgets.includes.value = args.includes || opts.encodedIncludeFiletypes;
    widgets.excludes.value = args.excludes || opts.encodedExcludeFiletypes;
    widgets.show_replace_all_results.checked = opts.showReplaceAllResults;
    widgets.confirm_replacements_in_files.checked = opts.confirmReplacementsInFiles;

    if (escape_default_pattern && widgets.opt_regex.checked) {
        /* The user wants to use a regex find/eplace from a selection (or
           current word) in the editor, so we escape the text for them.
           Bug 85619. */
        regex_escape(/* ignore_whitespace */ true);
    }

    switch (opts.caseSensitivity) {
    case koIFindOptions.FOC_INSENSITIVE:
        _set_case_widget("ignore-case");
        break
    case koIFindOptions.FOC_SENSITIVE:
        _set_case_widget("match-case");
        break
    case koIFindOptions.FOC_SMART:
        _set_case_widget("smart-case");
        break
    }
    widgets.opt_case.accessKey = "c";

    // Setup the UI for the mode, as appropriate.
    var mode = args.mode || "find";
    var verb;
    if (mode.slice(0, 7) === "replace") {
        verb = "replace";
    } else {
        verb = "find";
    }

    if (verb == "replace") {
        // When in replace mode - restore the last replaced text.
        widgets.repl.value = ko.mru.get("find-replacementMru", 0);
    }

    // - Setup for there being a current project.
    var curr_proj = opener.ko.projects.manager.currentProject;
    if (curr_proj) {
        _collapse_widget(widgets.search_in_curr_project, false);
        _hide_widget(widgets.search_in_curr_project, false);
        widgets.search_in_curr_project.label
            = "Project ("+curr_proj.name+")";
        _g_curr_project_context = Components.classes["@activestate.com/koCollectionFindContext;1"]
            .createInstance(Components.interfaces.koICollectionFindContext);
        _g_curr_project_context.add_koIContainer(curr_proj);
    } else {
        _collapse_widget(widgets.search_in_curr_project, true);
        _hide_widget(widgets.search_in_curr_project, true);
        _g_curr_project_context = null;
        if (mode == "findincurrproject" || mode == "replaceincurrproject") {
            msg_warn("No current project.");
            mode = "find";
        }
    }
    
    // - Setup for a collection having been passed in.
    if (mode == "findincollection" || mode == "replaceincollection") {
        _collapse_widget(widgets.search_in_collection, false);
        _hide_widget(widgets.search_in_collection, false);
        _collapse_widget(widgets.search_in_collection_sep, false);
        _hide_widget(widgets.search_in_collection_sep, false);
        widgets.search_in_collection.label = args.collection.desc;
        _g_collection_context = args.collection;
    } else {
        _collapse_widget(widgets.search_in_collection, true);
        _hide_widget(widgets.search_in_collection, true);
        _collapse_widget(widgets.search_in_collection_sep, true);
        _hide_widget(widgets.search_in_collection_sep, true);
        _g_collection_context = null;
    }
    
    // - If the mode is a generic '*inlastfiles', try to do the same
    // search as before.  Possibly restore a previous "in files" mode.
    var in_files_modes = {
        "findinlastfiles": true,
        "replaceinlastfiles": true
    };
    if (mode in in_files_modes) {
        var lastInFilesContext = _g_prefs.getStringPref("find-lastInFilesContext");
        var mode_context_from_pref = {
            // The 'mode' and 'find-lastInFilesContext' (same as <menulist>
            // values) annoyingly use slightly different spellings.
            "files": "infiles",
            "open-files": "inopenfiles",
            "curr-project": (curr_proj ? "incurrproject" : "infiles")
        };
        mode = verb + mode_context_from_pref[lastInFilesContext];
        _g_save_in_files_context = true;
    }
    
    // - Switch to the appropriate mode.
    switch (mode) {
    case "find":
        widgets.opt_repl.checked = false;
        widgets.search_in_menu.value
            = (use_selection_as_context ? "selection" : "document");
        break;
    case "replace":
        widgets.opt_repl.checked = true;
        widgets.search_in_menu.value
            = (use_selection_as_context ? "selection" : "document");
        break;
    case "findinfiles":
        widgets.opt_repl.checked = false;
        widgets.search_in_menu.value = "files";
        break;
    case "replaceinfiles":
        widgets.opt_repl.checked = true;
        widgets.search_in_menu.value = "files";
        break;
    case "findinopenfiles":
        widgets.opt_repl.checked = false;
        widgets.search_in_menu.value = "open-files";
        break;
    case "replaceinopenfiles":
        widgets.opt_repl.checked = true;
        widgets.search_in_menu.value = "open-files";
        break;
    case "findincollection":
        widgets.opt_repl.checked = false;
        widgets.search_in_menu.value = "collection";
        break;
    case "replaceincollection":
        widgets.opt_repl.checked = true;
        widgets.search_in_menu.value = "collection";
        break;
    case "findincurrproject":
        widgets.opt_repl.checked = false;
        widgets.search_in_menu.value = "curr-project";
        break;
    case "replaceincurrproject":
        widgets.opt_repl.checked = true;
        widgets.search_in_menu.value = "curr-project";
        break;
    default:
        opener.alert("unexpected mode for find dialog: "+mode);
    }
    update(null);

    _set_pattern_focus(select_all_pattern);

    // The act of opening the find dialog should reset the find session.
    // This is the behaviour of least surprise.
    var findSessionSvc = Components.classes["@activestate.com/koFindSession;1"].
                            getService(Components.interfaces.koIFindSession);
    findSessionSvc.Reset();
    
    setTimeout(function() {
        window.focus(); // focus hack
    }, 50);
}

function _set_pattern_focus(select_all)
{
    widgets.curr_pattern.focus();
    if (select_all) {
        widgets.curr_pattern.setSelectionRange(
            0, widgets.curr_pattern.textLength);
    } else {
        widgets.curr_pattern.setSelectionRange(
            widgets.curr_pattern.textLength, widgets.curr_pattern.textLength);
    }
}


function _get_curr_scimoz() {
    var scimoz = null;
    try {
        scimoz = opener.ko.views.manager.currentView.scintilla.scimoz;
    } catch(ex) {
        /* pass: just don't have a current editor view */
    }
    return scimoz;
}


/**
 * Update the UI as appropriate for the current mode.
 */
function _update_mode_ui() {
    var default_btn = null;
    
    if (widgets.opt_repl.checked) {
        switch (widgets.search_in_menu.value) {
        case "curr-project":
        case "collection":
        case "files":
            // Replace in Files: *Replace All*
            _collapse_widget(widgets.find_prev_btn, true);
            _collapse_widget(widgets.find_next_btn, true);
            _collapse_widget(widgets.replace_btn, true);
            _collapse_widget(widgets.find_all_btn, true);
            _collapse_widget(widgets.replace_all_btn, false);
            _collapse_widget(widgets.confirm_replacements_in_files, false);
            _collapse_widget(widgets.show_replace_all_results, true);
            _collapse_widget(widgets.mark_all_btn, true);
            default_btn = widgets.replace_all_btn;
            break
        default:
            // Replace: Find Next, *Replace*, Replace All
            _collapse_widget(widgets.find_prev_btn, false);
            _collapse_widget(widgets.find_next_btn, false);
            _collapse_widget(widgets.replace_btn, false);
            _collapse_widget(widgets.find_all_btn, true);
            _collapse_widget(widgets.replace_all_btn, false);
            _collapse_widget(widgets.confirm_replacements_in_files, true);
            _collapse_widget(widgets.show_replace_all_results, false);
            _collapse_widget(widgets.mark_all_btn, true);
            default_btn = widgets.replace_btn;
        }
    } else {
        switch (widgets.search_in_menu.value) {
        case "curr-project":
        case "collection":
        case "files":
            // Find in Files: *Find All*
            _collapse_widget(widgets.find_prev_btn, true);
            _collapse_widget(widgets.find_next_btn, true);
            _collapse_widget(widgets.replace_btn, true);
            _collapse_widget(widgets.find_all_btn, false);
            _collapse_widget(widgets.replace_all_btn, true);
            _collapse_widget(widgets.confirm_replacements_in_files, true);
            _collapse_widget(widgets.show_replace_all_results, true);
            _collapse_widget(widgets.mark_all_btn, true);
            default_btn = widgets.find_all_btn;
            break
        default:
            // Find: Find Previous, *Find Next*, Find All, Mark All
            _collapse_widget(widgets.find_prev_btn, false);
            _collapse_widget(widgets.find_next_btn, false);
            _collapse_widget(widgets.replace_btn, true);
            _collapse_widget(widgets.find_all_btn, false);
            _collapse_widget(widgets.replace_all_btn, true);
            _collapse_widget(widgets.confirm_replacements_in_files, true);
            _collapse_widget(widgets.show_replace_all_results, true);
            _collapse_widget(widgets.mark_all_btn, false);
            default_btn = widgets.find_next_btn;
        }
    }
    
    //_collapse_widget(widgets.pattern_btn, !widgets.opt_regex.checked);
    
    // Set the default button.
    if (_g_curr_default_btn == default_btn) {
        /* do nothing */
    } else {
        if (_g_curr_default_btn) {
            _g_curr_default_btn.removeAttribute("default");
        }
        default_btn.setAttribute("default", "true");
    }
    _g_curr_default_btn = default_btn;
    
    // Setup re-used accesskeys.
    // Because of mode changes and limited letters, we are re-using some
    // accesskeys. The working set is defined by elements that have a
    // uses-accesskey="true" attribute. The data is in that element's
    // _accesskey attribute.
    var elem;
    var working_set = document.getElementsByAttribute(
            "uses-accesskey", "true");
    for (var j = 0; j < working_set.length; ++j) {
        elem = working_set[j];
        if (elem.getAttribute("collapsed")) {
            elem.removeAttribute("accesskey");
        } else {
            elem.setAttribute("accesskey",
                              elem.getAttribute("_accesskey"));
        }
    }
}


/**
 * Determine an appropriate koIFindContext instance for
 * searching/replacing, and set it to the `_g_find_context` global.
 *
 * @param {string} reason gives the reason for resetting the find context.
 *      This is only used for debugging.
 * 
 * Can return null if an appropriate context could not be determined.
 */
function reset_find_context(reason /* =null */) {
    if (typeof(reason) == "undefined" || reason == null) reason = "(no reason given)";
    
    var context = null;
    msg_clear();

    switch (widgets.search_in_menu.value) {
    case "document":
        var curr_view = opener.ko.views.manager.currentView;
        if (curr_view == null) {
            msg_warn(_bundle.GetStringFromName("noCurrentFileInWhichToSearch"));
        } else {
            var type = curr_view.getAttribute("type");
            switch (type) {
            case "browser":
                msg_warn(_bundle.GetStringFromName("cannotSearchInABrowserPreviewTab"));
                break;
            case "editor":
            case "buffer":
            case "diff":
            default:
                context = Components.classes["@activestate.com/koFindContext;1"]
                    .createInstance(Components.interfaces.koIFindContext);
                context.type = koIFindContext.FCT_CURRENT_DOC;
                break;
            }
        }
        break;

    case "selection":
        var scimoz = _get_curr_scimoz();
        if (!scimoz) {
            msg_warn(_bundle.GetStringFromName("noCurrentFileInWhichToSearch"));
        } else if (scimoz.selectionStart == scimoz.selectionEnd) {
            msg_warn(_bundle.GetStringFromName("noCurrentSelection"));
        } else {
            context = Components.classes["@activestate.com/koRangeFindContext;1"]
                .createInstance(Components.interfaces.koIRangeFindContext);
            context.type = koIFindContext.FCT_SELECTION;
            context.startIndex = scimoz.charPosAtPosition(scimoz.selectionStart);
            context.endIndex = scimoz.charPosAtPosition(scimoz.selectionEnd);
            // Update the positions if the selection is a line selection, such
            // as vi visual line mode, bug 81570.
            if (scimoz.selectionMode == scimoz.SC_SEL_LINES) {
                var startLineNo = scimoz.lineFromPosition(context.startIndex);
                var endLineNo = scimoz.lineFromPosition(context.endIndex);
                context.startIndex = scimoz.getLineSelStartPosition(startLineNo);
                context.endIndex = scimoz.getLineSelEndPosition(endLineNo);
            }
        }
        break;

    case "curr-project":
        context = _g_curr_project_context;
        msg_clear();
        break;

    case "collection":
        context = _g_collection_context;
        msg_clear();
        break;

    case "open-files":
        context = Components.classes["@activestate.com/koFindContext;1"]
            .createInstance(Components.interfaces.koIFindContext);
        context.type = koIFindContext.FCT_ALL_OPEN_DOCS;
        //TODO: warn if no open files?
        break;

    case "files":
        context = Components.classes[
            "@activestate.com/koFindInFilesContext;1"]
            .createInstance(Components.interfaces.koIFindInFilesContext);
        context.type = Components.interfaces.koIFindContext.FCT_IN_FILES;

        // Use the current view's cwd for interpreting relative paths.
        var view = opener.ko.views.manager.currentView;
        if (view != null &&
            view.getAttribute("type") == "editor" &&
            view.koDoc.file &&
            view.koDoc.file.isLocal) {
            context.cwd = view.koDoc.file.dirName;
        } else {
            context.cwd = gFindSvc.options.cwd;
        }

        msg_clear();
        break;

    default:
        log.error("unexpected search-in-menu value: "
                  + widgets.search_in_menu.value);
    }
    
    _g_find_context = context;
}


function _set_case_widget(value) {
    var w = widgets.opt_case;
    switch (value) {
    case "ignore-case":
        w.value = "ignore-case";
        w.label = _bundle.GetStringFromName("matchCase");
        w.checked = false;
        w.setAttribute("tooltiptext", _bundle.GetStringFromName("ignoreCase"));
        break;
    case "match-case":
        w.value = "match-case";
        w.label = _bundle.GetStringFromName("matchCase");
        w.checked = true;
        w.setAttribute("tooltiptext", _bundle.GetStringFromName("matchCase"));
        break;
    case "smart-case":
        w.value = "smart-case";
        w.label = _bundle.GetStringFromName("smartCase");
        w.checked = true;
        w.setAttribute("tooltiptext",
            _bundle.GetStringFromName("smartCase.tooltip"));
        break;
    default:
        throw new Error("invalid case widget value: "+value);
    }
    w.accessKey = _bundle.GetStringFromName("caseCheckbox.accesskey");
}


function _toggle_collapse(widget) {
    if (widget.hasAttribute("collapsed")) {
        widget.removeAttribute("collapsed");
    } else {
        widget.setAttribute("collapsed", "true");
    }
    
    updateWrapperHeight();
}

function _collapse_widget(widget, collapse) {
    if (collapse) {
        widget.setAttribute("collapsed", "true");
    } else {
        if (widget.hasAttribute("collapsed"))
            widget.removeAttribute("collapsed");
    }
    
    updateWrapperHeight();
}

function _hide_widget(widget, hide) {
    if (hide) {
        widget.setAttribute("hidden", "true");
    } else {
        if (widget.hasAttribute("hidden"))
            widget.removeAttribute("hidden");
    }
    
    updateWrapperHeight();
}

function _disable_widget(widget) {
    widget.setAttribute("disabled", "true");
    updateWrapperHeight();
}
function _enable_widget(widget) {
    if (widget.hasAttribute("disabled")) {
        widget.removeAttribute("disabled");
    }
    updateWrapperHeight();
}

function updateWrapperHeight()
{
    var elem = opener.document.getElementById("findReplaceWrap");
    var bo = document.getElementById('find-box-wrap').boxObject;
    elem.setAttribute("height", bo.height);
}
 
