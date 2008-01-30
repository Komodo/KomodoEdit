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
 * - replace in files support
 * - restore the regex shortcuts
 * - better error message handling (perhaps validate with lexregex.py)
 * - find/replace in project support
 * - "Edit" menu hookup
 * - undo functionality
 * - all spec'd replace in files guards
 * - find results tab enhancements (pin, grouping/view opts, handling
 *   replacement warnings/errors, filter, redo)
 * - replacement for "Display results in Find Results 2 tab" checkbox
 *   (the plan is the 'pin' option)
 * - some key mappings (see find2.xul)
 * - prep new docs for Troy
 * - replacement for smart-case matching?
 * - restore mark all
 */

//---- globals

var log = ko.logging.getLogger("find");
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



//---- public methods for the dialog

function on_load() {
    try {
        gFindSvc = Components.classes["@activestate.com/koFindService;1"].
                   getService(Components.interfaces.koIFindService);
        _init_widgets();

        // Necessary for re-launching (i.e. Ctrl+F when the dialog is already open).
        window.focus();

        _init_ui();
    } catch (ex) {
        log.exception(ex);
    }    
}

function on_unload() {
}

function on_focus(event) {
    if (event.target == document) {  // focus of the *Window*
        reset_find_context();
    }
}

/**
 * Update as appropriate for some change in the dialog.
 *
 * @param changed {string} The name of the thing that changed. If
 *      null or not specified *everything* is updated (used for dialog
 *      initialization).
 */
function update(changed /* =null */) {
    if (typeof(changed) == "undefined") changed = null;
    
    var mode_changed = false;
    var opts = gFindSvc.options;
    
    // "Replace" checkbox state changed.
    if (changed == null || changed == "replace") {
        var repl = widgets.opt_repl.checked;
        _collapse_widget(widgets.repl_row, !repl);

        // Don't muck with the focus for dialog init (changed=null)
        // because we want the pattern widget to get the focus, even
        // in replace mode.
        if (changed == "replace") {
            (repl ? widgets.repl : widgets.pattern).focus();
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
        reset_find_context();
        mode_changed = true;
    }
    
    // The pattern value changed.
    if (changed == null || changed == "pattern") {
        if (widgets.pattern.value && !_g_btns_enabled_for_pattern) {
            // We changed from no pattern string to some pattern string.
            // Enable the relevant buttons.
            _enable_widget(widgets.find_prev_btn);
            _enable_widget(widgets.find_next_btn);
            _enable_widget(widgets.replace_btn);
            _enable_widget(widgets.find_all_btn);
            _enable_widget(widgets.replace_all_btn);
            _enable_widget(widgets.mark_all_btn);
            _g_btns_enabled_for_pattern = true;
        } else if (!widgets.pattern.value && _g_btns_enabled_for_pattern) {
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
    }
    if (changed == null || changed == "case") {
        opts.caseSensitivity = (widgets.opt_case.checked ?
            koIFindOptions.FOC_INSENSITIVE : koIFindOptions.FOC_SENSITIVE);
    }
    if (changed == null || changed == "word") {
        opts.matchWord = widgets.opt_word.checked;
    }
    //if (changed == null || changed == "multiline") {
    //    //...
    //}
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

    if (mode_changed) {
        _update_mode_ui();
        window.sizeToContent();
    }
}

function regex_escape()
{
    try {
        var textbox = widgets.pattern;
        var selection = textbox.value.slice(textbox.selectionStart,
                                            textbox.selectionEnd);
        var escaped;
        if (selection) {
            escaped = gFindSvc.regex_escape_string(selection);
            var selStart = textbox.selectionStart;
            textbox.value = textbox.value.slice(0, selStart)
                + escaped + textbox.value.slice(textbox.selectionEnd);
            textbox.focus();
            textbox.setSelectionRange(selStart,
                                      selStart + escaped.length);
        } else {
            escaped = gFindSvc.regex_escape_string(textbox.value);
            textbox.value = escaped;
            textbox.focus();
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


function find_prev() {
    find_next(true);
}

function find_next(backward /* =false */) {
    if (typeof(backward) == "undefined" || backward == null) backward = false;

    try {
        msg_clear();
        
        var pattern = widgets.pattern.value;
        if (! pattern) {
            return;
        }
    
        // This handles, for example, the context being "search in
        // selection", but there is no selection.
        if (! _g_find_context) {
            // Make one attempt to get the context again: state in the
            // main editor may have changed such that getting a context is
            // possible.
            reset_find_context();
            if (! _g_find_context) {
                return;
            }
        }
    
        ko.mru.addFromACTextbox(widgets.pattern);
    
        //TODO: Icky. The "searchBackward" state being set on the global
        //      object then restored is gross. koIFindOptions should be
        //      an argument to the Find_* functions. The macro versions
        //      of the Find_* functions have to do this same save/restore
        //      dance.
        var old_searchBackward = gFindSvc.options.searchBackward;
        gFindSvc.options.searchBackward = backward;
    
        var mode = (widgets.opt_repl.checked ? "replace" : "find");
        var found_one = Find_FindNext(opener, _g_find_context, pattern, mode,
                                      false,         // quiet
                                      true,          // useMRU
                                      msg_callback); // msgHandler
        gFindSvc.options.searchBackward = old_searchBackward;
    
        if (!found_one) {
            // If no match was hilighted then it is likely that the user will
            // now want to enter a different pattern. (Copying Word's
            // behaviour here.)
            widgets.pattern.focus();
        }
    } catch (ex) {
        log.exception(ex);
    }
}

function find_all() {
    try {
        msg_clear();
        var pattern = widgets.pattern.value;
        if (! pattern) {
            return;
        }
    
        // This handles, for example, the context being "search in
        // selection", but there is no selection.
        if (! _g_find_context) {
            // Make one attempt to get the context again: state in the
            // main editor may have changed such that getting a context is
            // possible.
            reset_find_context();
            if (! _g_find_context) {
                return;
            }
        }

        ko.mru.addFromACTextbox(widgets.pattern);

        if (_g_find_context.type == koIFindContext.FCT_IN_COLLECTION) {
            if (Find_FindAllInCollection(opener, _g_find_context,
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

            if (Find_FindAllInFiles(opener, _g_find_context,
                                    pattern, null,
                                    msg_callback)) {
                window.close();
            }

        } else {
            var found_some = Find_FindAll(opener, _g_find_context, pattern,
                                          null,          // patternAlias
                                          msg_callback); // msgHandler
            if (found_some) {
                window.close();
            } else {
                widgets.pattern.focus();
            }
        }
    } catch(ex) {
        log.exception(ex);
    }
}

function mark_all() {
    try {
        msg_clear();
        
        var pattern = widgets.pattern.value;
        if (! pattern) {
            return;
        }
    
        // This handles, for example, the context being "search in
        // selection", but there is no selection.
        if (! _g_find_context) {
            // Make one attempt to get the context again: state in the
            // main editor may have changed such that getting a context is
            // possible.
            reset_find_context();
            if (! _g_find_context) {
                return;
            }
        }
        if (_g_find_context.type == koIFindContext.FCT_IN_FILES) {
            log.warn("'Mark All' in files (i.e. files not open in "
                     + "Komodo) is not supported.");
            return;
        }

        ko.mru.addFromACTextbox(widgets.pattern);

        var found_some = Find_MarkAll(opener, _g_find_context, pattern,
                                      null,          // patternAlias
                                      msg_callback); // msgHandler
        if (found_some) {
            window.close();
        } else {
            widgets.pattern.focus();
        }
    } catch(ex) {
        log.exception(ex);
    }
}


function replace() {
    try {
        msg_clear();
        
        var pattern = widgets.pattern.value;
        if (! pattern) {
            return;
        }
        var repl = widgets.repl.value;
    
        // This handles, for example, the context being "search in
        // selection", but there is no selection.
        if (! _g_find_context) {
            // Make one attempt to get the context again: state in the
            // main editor may have changed such that getting a context is
            // possible.
            reset_find_context();
            if (! _g_find_context) {
                return;
            }
        }
    
        ko.mru.addFromACTextbox(widgets.pattern);
        if (repl)
            ko.mru.addFromACTextbox(widgets.repl);
    
        var found_one = Find_Replace(opener, _g_find_context,
                pattern, repl, msg_callback);
        if (!found_one) {
            // If no match was hilighted then it is likely that the user will
            // now want to enter a different pattern. (Copying Word's
            // behaviour here.)
            widgets.pattern.focus();
        }
    } catch (ex) {
        log.exception(ex);
    }
}


function replace_all() {
    try {
        msg_clear();
        
        var pattern = widgets.pattern.value;
        if (! pattern) {
            return;
        }
        var repl = widgets.repl.value;
    
        // This handles, for example, the context being "search in
        // selection", but there is no selection.
        if (! _g_find_context) {
            // Make one attempt to get the context again: state in the
            // main editor may have changed such that getting a context is
            // possible.
            reset_find_context();
            if (! _g_find_context) {
                return;
            }
        }
    
        ko.mru.addFromACTextbox(widgets.pattern);
        if (repl)
            ko.mru.addFromACTextbox(widgets.repl);

        if (_g_find_context.type == koIFindContext.FCT_IN_FILES) {
            ko.mru.addFromACTextbox(widgets.dirs);
            if (widgets.includes.value)
                ko.mru.addFromACTextbox(widgets.includes);
            if (widgets.excludes.value)
                ko.mru.addFromACTextbox(widgets.excludes);
            gFindSvc.options.cwd = _g_find_context.cwd;

            if (Find_ReplaceAllInFiles(opener, _g_find_context,
                                       pattern, repl, null,
                                       msg_callback)) {
                window.close();
            }

        } else {
            var found_some = null;
            var found_some = Find_ReplaceAll(
                    opener, _g_find_context, pattern, repl,
                    widgets.show_replace_all_results.checked,
                    msg_callback);
            if (found_some) {
                window.close();
            } else {
                widgets.pattern.focus();
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

    widgets.pattern = document.getElementById('pattern');
    widgets.repl_row = document.getElementById('repl-row');
    widgets.repl_lbl = document.getElementById('repl-lbl');
    widgets.repl = document.getElementById('repl');

    widgets.opt_regex = document.getElementById('opt-regex');
    widgets.opt_case = document.getElementById('opt-case');
    widgets.opt_word = document.getElementById('opt-word');
    //widgets.opt_multiline = document.getElementById('opt-multiline');
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

    widgets.find_prev_btn = document.getElementById('find-prev-btn');
    widgets.find_next_btn = document.getElementById('find-next-btn');
    widgets.replace_btn = document.getElementById('replace-btn');
    widgets.find_all_btn = document.getElementById('find-all-btn');
    widgets.replace_all_btn = document.getElementById('replace-all-btn');
    widgets.show_replace_all_results = document.getElementById('show-replace-all-results');
    widgets.mark_all_btn = document.getElementById('mark-all-btn');
    //widgets.close_btn = document.getElementById('close-btn');
    //widgets.help_btn = document.getElementById('help-btn');
}

/**
 * Initialize the dialog UI from `opener.ko.launch.find2_dialog_args` data.
 */
function _init_ui() {
    var args = opener.ko.launch.find2_dialog_args || {};
    opener.ko.launch.find2_dialog_args = null;

    // If there is selected text then preload the find pattern with it.
    // Unless it spans a line, then set the search context to the
    // selection.
    var scimoz = null;
    var selection = null;
    var use_selection_as_pattern = false;
    var use_selection_as_context = false;
    try {
        scimoz = opener.ko.views.manager.currentView.scintilla.scimoz;
        selection = scimoz.selText;
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
    if (typeof args.pattern != "undefined") {
        default_pattern = args.pattern;
    } else if (use_selection_as_pattern) {
        default_pattern = selection;
    } else if (scimoz) {
        default_pattern = ko.interpolate.getWordUnderCursor(scimoz);
    }

    // Preload with input buffer contents if any and then give focus to
    // the pattern textbox.
    // Notes:
    // - The pattern textbox will automatically select all its contents
    //   on focus. If there are input buffer contents then we do *not*
    //   want this to happen, because this will defeat the purpose of
    //   the input buffer if the user is part way through typing in
    //   characters.
    // - Have to set focus in a timer because this could be called within
    //   an onfocus handler, in which Mozilla does not like .focus()
    //   calls.
    var input_buf = opener.ko.inputBuffer.finish();
    widgets.pattern.value = "";
    if (input_buf) {
        widgets.pattern.value = input_buf;
        _set_pattern_focus(false);
    } else {
        widgets.pattern.value = default_pattern;
        _set_pattern_focus(true);
    }

    // Set other dialog data (from the given args and from the
    // koIFindService.options).
    var opts = gFindSvc.options;
    widgets.repl.value = args.repl || "";
    widgets.opt_regex.checked
        = opts.patternType == koIFindOptions.FOT_REGEX_PYTHON;
    widgets.opt_case.checked
        = opts.caseSensitivity == koIFindOptions.FOC_INSENSITIVE;
    widgets.opt_word.checked = opts.matchWord;
    //widgets.opt_multiline.checked = ...
    widgets.dirs.value = args.dirs || opts.encodedFolders;
    widgets.search_in_subdirs.checked = opts.searchInSubfolders;
    widgets.includes.value = args.includes || opts.encodedIncludeFiletypes;
    widgets.excludes.value = args.excludes || opts.encodedExcludeFiletypes;
    widgets.show_replace_all_results.checked = opts.showReplaceAllResults;

    // Setup the UI for the mode, as appropriate.
    var mode = args.mode || "find";

    // - Setup for there being a current project.
    var koPartSvc = Components.classes["@activestate.com/koPartService;1"]
            .getService(Components.interfaces.koIPartService);
    var curr_proj = koPartSvc.currentProject;
    if (curr_proj) {
        _collapse_widget(widgets.search_in_curr_project, false);
        widgets.search_in_curr_project.label
            = "Current Project ("+curr_proj.name+")";
        _g_curr_project_context = Components.classes["@activestate.com/koCollectionFindContext;1"]
            .createInstance(Components.interfaces.koICollectionFindContext);
        _g_curr_project_context.add_koIContainer(curr_proj);
    } else {
        _collapse_widget(widgets.search_in_curr_project, true);
        _g_curr_project_context = null;
        if (mode == "findincurrproject") {
            msg_warn("No current project.");
            mode = "find";
        }
    }
    
    // - Setup for there a collection having been passed in.
    if (mode == "findincollection") {
        _collapse_widget(widgets.search_in_collection, false);
        _collapse_widget(widgets.search_in_collection_sep, false);
        widgets.search_in_collection.label = args.collection.desc;
        _g_collection_context = args.collection;
    } else {
        _collapse_widget(widgets.search_in_collection, true);
        _collapse_widget(widgets.search_in_collection_sep, true);
        _g_collection_context = null;
    }
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
    case "findincollection":
        widgets.opt_repl.checked = false;
        widgets.search_in_menu.value = "collection";
        break;
    case "findincurrproject":
        widgets.opt_repl.checked = false;
        widgets.search_in_menu.value = "curr-project";
        break;
    default:
        alert("unexpected mode for find dialog: "+mode);
    }
    update(null);

    // The act of opening the find dialog should reset the find session.
    // This is the behaviour of least surprise.
    gFindSession.Reset();
}

function _set_pattern_focus(select_all)
{
    widgets.pattern.focus();
    if (select_all) {
        widgets.pattern.setSelectionRange(0,
                                          widgets.pattern.textLength);
    } else {
        widgets.pattern.setSelectionRange(widgets.pattern.textLength,
                                          widgets.pattern.textLength);
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
            // Replace in Files: Replace All, Close, Help
            _collapse_widget(widgets.find_prev_btn, true);
            _collapse_widget(widgets.find_next_btn, true);
            _collapse_widget(widgets.replace_btn, true);
            _collapse_widget(widgets.find_all_btn, true);
            _collapse_widget(widgets.replace_all_btn, false);
            _collapse_widget(widgets.show_replace_all_results, true);
            _collapse_widget(widgets.mark_all_btn, true);
            default_btn = widgets.replace_all_btn;
            break
        default:
            // Replace: Find Next, Replace*, Replace All, Close, Help
            _collapse_widget(widgets.find_prev_btn, true);
            _collapse_widget(widgets.find_next_btn, false);
            _collapse_widget(widgets.replace_btn, false);
            _collapse_widget(widgets.find_all_btn, true);
            _collapse_widget(widgets.replace_all_btn, false);
            _collapse_widget(widgets.show_replace_all_results, false);
            _collapse_widget(widgets.mark_all_btn, true);
            default_btn = widgets.replace_btn;
        }
    } else {
        switch (widgets.search_in_menu.value) {
        case "curr-project":
        case "collection":
        case "files":
            // Find in Files: Find All*, Close, Help
            _collapse_widget(widgets.find_prev_btn, true);
            _collapse_widget(widgets.find_next_btn, true);
            _collapse_widget(widgets.replace_btn, true);
            _collapse_widget(widgets.find_all_btn, false);
            _collapse_widget(widgets.replace_all_btn, true);
            _collapse_widget(widgets.show_replace_all_results, true);
            _collapse_widget(widgets.mark_all_btn, true);
            default_btn = widgets.find_all_btn;
            break
        default:
            // Find: Find Previous, Find Next*, Find All, Mark All, Close, Help
            _collapse_widget(widgets.find_prev_btn, false);
            _collapse_widget(widgets.find_next_btn, false);
            _collapse_widget(widgets.replace_btn, true);
            _collapse_widget(widgets.find_all_btn, false);
            _collapse_widget(widgets.replace_all_btn, true);
            _collapse_widget(widgets.show_replace_all_results, true);
            _collapse_widget(widgets.mark_all_btn, false);
            default_btn = widgets.find_next_btn;
        }
    }
    
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
 * Can return null if an appropriate context could not be determined.
 */
function reset_find_context() {
    var context = null;
    msg_clear();

    switch (widgets.search_in_menu.value) {
    case "document":
        context = Components.classes["@activestate.com/koFindContext;1"]
            .createInstance(Components.interfaces.koIFindContext);
        context.type = koIFindContext.FCT_CURRENT_DOC;
        //TODO: warn and return null if no curr file in which can search
        break;

    case "selection":
        var scimoz = _get_curr_scimoz();
        if (!scimoz) {
            msg_warn("No current file in which to search.");
        } else if (scimoz.selectionStart == scimoz.selectionEnd) {
            msg_warn("No current selection.");
        } else {
            context = Components.classes["@activestate.com/koRangeFindContext;1"]
                .createInstance(Components.interfaces.koIRangeFindContext);
            context.type = koIFindContext.FCT_SELECTION;
            context.startIndex = scimoz.charPosAtPosition(scimoz.selectionStart);
            context.endIndex = scimoz.charPosAtPosition(scimoz.selectionEnd);
        }
        break;

    case "curr-project":
        context = _g_curr_project_context;
        break;

    case "collection":
        context = _g_collection_context;
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
            view.document.file &&
            view.document.file.isLocal) {
            context.cwd = view.document.file.dirName;
        } else {
            context.cwd = gFindSvc.options.cwd;
        }
        break;

    default:
        log.error("unexpected search-in-menu value: "
                  + widgets.search_in_menu.value);
    }
    
    _g_find_context = context;
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
        widget.setAttribute("hidden", "true");
    } else {
        widget.removeAttribute("collapsed");
        widget.removeAttribute("hidden");
    }
}

function _disable_widget(widget) {
    widget.setAttribute("disabled", "true");
}
function _enable_widget(widget) {
    if (widget.hasAttribute("disabled")) {
        widget.removeAttribute("disabled");
    }
}


