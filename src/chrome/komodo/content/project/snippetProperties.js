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

/*
 *
 * Komodo's Snippet Properties and "Add Snippet" dialog.
 *
 */

xtk.include("domutils");

var log = ko.logging.getLogger("snippetProperties");

var snippetname, snippetvalue, snippetnamelabel;
var gApplyButton, gOKButton;
var indentCheckbox, autoAbbreviation, treatAsEJS, keybinding, gItem;
var gCaretPos;
var gSetSelectionCheckbox;
var scin;
var encodingSvc = Components.classes["@activestate.com/koEncodingServices;1"].
                    getService(Components.interfaces.koIEncodingServices);
var ANCHOR_MARKER = '!@#_anchor';
var CURRENTPOS_MARKER = '!@#_currentPos';
var gChromeWindowView = null;

function onLoad(event) {
    try {
        scintillaOverlayOnLoad()
        var dialog = document.getElementById("dialog-snippetproperties");
        gChromeWindowView = event.view;

        gApplyButton = dialog.getButton("extra1");
        gApplyButton.setAttribute('label', 'Apply');
        gApplyButton.setAttribute('accesskey', 'A');
        gOKButton = dialog.getButton("accept");

        gItem = window.arguments[0].item;

        if (window.arguments[0].task == 'new') {
            document.title = "Create New snippet";
            gApplyButton.setAttribute('collapsed', 'true');
        } else {
            document.title = "Snippet Properties";
        }

        snippetname = document.getElementById('snippetname');
        snippetnamelabel = document.getElementById('snippetnamelabel');
        snippetvalue = document.getElementById('snippetvalue');
        indentCheckbox = document.getElementById('indent_relative');
        autoAbbreviation = document.getElementById('auto_abbreviation');
        treatAsEJS = document.getElementById('treat_as_ejs');
        gSetSelectionCheckbox = document.getElementById('set_selection');


        snippetname.value = gItem.getStringAttribute('name');

        keybinding = document.getElementById('keybindings');
        keybinding.gKeybindingMgr = opener.ko.keybindings.manager;
        keybinding.part = gItem;

        keybinding.commandParam = gItem.id;
        var text = gItem.value;
        var language = 'Text';

        snippetvalue.initWithBuffer(text, language);
        
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

        scin = snippetvalue.scimoz;

        scin.caretFore = 0x0000ff;
        scin.setSelBack(1, 11184895);
        scin.caretWidth = 2;
        var prefs = (Components.classes["@activestate.com/koPrefService;1"]
                     .getService(Components.interfaces.koIPrefService).prefs);
        scin.useTabs = true;
        scin.indent = scin.tabWidth = prefs.getLongPref('indentWidth');
        gSetSelectionCheckbox.setAttribute('checked',
                                           gItem.getStringAttribute('indent_relative'));
        var anchor = text.indexOf(ANCHOR_MARKER);
        var currentPos = text.indexOf(CURRENTPOS_MARKER);
        if (anchor < currentPos) {
            anchor = text.indexOf(ANCHOR_MARKER);
            text = text.replace(ANCHOR_MARKER, '');
            currentPos = text.indexOf(CURRENTPOS_MARKER);
            text = text.replace(CURRENTPOS_MARKER, '');
        } else {
            currentPos = text.indexOf(CURRENTPOS_MARKER);
            text = text.replace(CURRENTPOS_MARKER, '');
            anchor = text.indexOf(ANCHOR_MARKER);
            text = text.replace(ANCHOR_MARKER, '');
        }
        snippetvalue.setBufferText(text);
        scin.anchor = scin.positionAtChar(0,anchor);
        scin.currentPos = scin.positionAtChar(0,currentPos);
        indentCheckbox.setAttribute('checked', gItem.getStringAttribute('indent_relative'));
        autoAbbreviation.setAttribute('checked', gItem.getStringAttribute('auto_abbreviation'));
        treatAsEJS.setAttribute('checked', gItem.getStringAttribute('treat_as_ejs'));
        gSetSelectionCheckbox.setAttribute('checked', gItem.getStringAttribute('set_selection'));
        keybinding.init();
        keybinding.updateCurrentKey();

        update_icon(gItem.iconurl);

        snippetname.focus();
        scin.isFocused = true; // show the caret
        scin.caretPeriod = 0;
        snippetname.select();
        //centerWindowOnScreen();

        UpdateField('name', true);
        updateOK();
    } catch (e) {
        log.exception(e);
    }
}


function onUnload(event) {
    try {
        // The "close" method ensures the scintilla view is properly cleaned up.
        snippetvalue.close();
        scintillaOverlayOnUnload();
    } catch (e) {
        log.exception(e);
    }
}


function OK()  {
    if (Apply()) {
        window.arguments[0].res = true;
        if (window.arguments[0].task == 'new') {
            var parentitem = window.arguments[0].parentitem;
            var item = window.arguments[0].item;
            opener.ko.toolbox2.addNewItemToParent(item, parentitem);
            //XXX: NewTools @@@@ Can item.active be dropped in peSnippet.js ?
        }
        return true;
    }
    return false;
}


// Return true iff the current position and anchor position are valid.
//
// If the selection position(s) are to be maintain for snippet insertion
// they must not be within an interpolation code block because the final
// position is then ambiguous.
//
// If the positions are not valid an alert dialog is raised and the
// positions are automatically moved to appropriate valid positions.
//
function _validateSelection()
{
    var text = scin.text;
    var anchor = scin.anchor;
    var currentPos = scin.currentPos;
    var blockOffsets = ko.interpolate.getBlockOffsets(text, true);

    // Detemine if the positions are valid. If not, determine appropriate
    // relocations for them.
    var i, start, end;
    var valid = true;
    for (i=0; i+1 < blockOffsets.length; i+=2) {
        start = blockOffsets[i];
        end = blockOffsets[i+1];
        if (start < currentPos && currentPos < end) {
            valid = false;
            if (currentPos < anchor) { // move back
                currentPos = start;
            } else if (currentPos == anchor) { // move both back
                currentPos = start;
                anchor = start;
            } else { // move forward
                currentPos = end;
            }
        }
        if (start < anchor && anchor < end) {
            valid = false;
            if (anchor < currentPos) { // move back
                anchor = start;
            } else if (anchor == currentPos) { // move both back
                anchor = start;
                currentPos = start;
            } else { // move forward
                anchor = end;
            }
        }
    }

    // If not valid, ask the user if should readjust.
    if (!valid) {
        var query = null;
        if (anchor == currentPos) {
            query = "The cursor is in the middle of a shortcut block. " +
                    "This is not allowed. Would you like Komodo to " +
                    "adjust the cursor position to an appropriate position?";
        } else {
            query = "The selection partially overlapped with a shortcut " +
                    "block. This is not allowed. Would you like Komodo to " +
                    "adjust the selection appropriatly?";
        }
        var readjust = ko.dialogs.okCancel(query,
                                       null, // default
                                       null, // extra text
                                       null, // title
                                       "readjust_snippet_selection");
        if (readjust == "OK") {
            scin.currentPos = currentPos;
            scin.anchor = anchor;
            valid = true;
        }
    }

    return valid;
}


// Apply the current changes and return true iff successful. Otherwise return
// false.
function Apply() {
    // Validate snippet data.
    if (gSetSelectionCheckbox.getAttribute('checked') == 'true') {
        var valid = _validateSelection();
        if (!valid) {
            return false;
        }
    }

    // Apply the keybinding.
    try {
        var retval = keybinding.apply(); // This may return false if a keybinding is partially entered
        if (!retval) return retval;
    } catch (e) {
        log.error(e);
        return false;
    }

    gItem.name = snippetname.value;
    opener.ko.projects.invalidateItem(gItem);
    gItem.setStringAttribute('name', snippetname.value);
    var indent_relative = indentCheckbox.getAttribute('checked') == 'true';
    if (indent_relative) {
        gItem.setStringAttribute('indent_relative', 'true');
    } else {
        gItem.setStringAttribute('indent_relative', 'false');
    }
    var isAutoAbbreviation = autoAbbreviation.getAttribute('checked') == 'true';
    gItem.setStringAttribute('auto_abbreviation', isAutoAbbreviation ? 'true' : 'false');
    var updatedTreatAsEJS = treatAsEJS.getAttribute('checked') == 'true';
    gItem.setStringAttribute('treat_as_ejs', updatedTreatAsEJS ? 'true' : 'false');
    var setSelection = gSetSelectionCheckbox.getAttribute('checked') == 'true';
    if (setSelection) {
        gItem.setStringAttribute('set_selection', 'true');
    } else {
        gItem.setStringAttribute('set_selection', 'false');
        scin.documentEnd();
    }
    // Insert anchor/column markers
    var text = scin.text;
    var anchor = ko.stringutils.charIndexFromPosition(text,scin.anchor);
    var currentPos = ko.stringutils.charIndexFromPosition(text,scin.currentPos);
    if (anchor < currentPos) {
        text = text.slice(0, anchor) + ANCHOR_MARKER +
               text.slice(anchor, currentPos) + CURRENTPOS_MARKER +
               text.slice(currentPos);
    } else {
        text = text.slice(0, currentPos) + CURRENTPOS_MARKER +
               text.slice(currentPos, anchor) + ANCHOR_MARKER +
               text.slice(anchor);
    }
    
    if (text.indexOf("<%") == -1) {
        // No point checking syntax of a dynamic snippet.
        var snippetParser = new opener.ko.tabstops.LiveTextParser();
        try {
            snippetParser.parse(text); // Ignore the result.
        } catch(ex) {
            ko.dialogs.alert(ex.message, ex.snippet);
            log.exception(ex);
            // Save it anyway, because snippets can be edited in a view now.
        }
    }
    
    gItem.value = text;

    var iconuri = document.getElementById('snippettab_icon').getAttribute('src');
    gItem.iconurl = iconuri;

    if (window.arguments[0].task != 'new') {
        gItem.save();
    }
    gApplyButton.setAttribute('disabled', 'true');
    return true;
}


function updateOK() {
    if (snippetname.value == '' || scin.text == '') {
        gOKButton.setAttribute('disabled', 'true');
        gApplyButton.setAttribute('disabled', 'true');
    } else {
        if (gOKButton.hasAttribute('disabled')) {
            gOKButton.removeAttribute('disabled');
        }
        if (gApplyButton.hasAttribute('disabled')) {
            gApplyButton.removeAttribute('disabled');
        }
    }
}

// Do the proper UI updates for a user change.
//  "field" (string) indicates the field to update.
//  "initializing" (boolean, optional) indicates that the dialog is still
//      initializing so some updates, e.g. enabling the <Apply> button, should
//      not be done.
function UpdateField(field, initializing /* =false */)
{
    try {
        if (typeof(initializing) == "undefined" || initializing == null) initializing = false;

        // Only take action if there was an actual change. Otherwise things like
        // the <Alt-A> shortcut when in a textbox will cause a cycle in reenabling
        // the apply button.
        var changed = false;

        switch (field) {
            case 'name':
                var name = snippetname.value;
                if (name) {
                    document.title = "'"+name+"' Properties";
                } else {
                    document.title = "Unnamed " + gItem.prettytype + " Properties";
                }
                snippetnamelabel.value = name;
                changed = true;
                break;
            case 'icon':
                changed = true;
                break;
        }

        if (!initializing && changed) {
            updateOK();
        }
    } catch (e) {
        log.exception(e);
    }
}

function Cancel()  {
    if (snippetvalue.scimoz.modify) {
        var resp = ko.dialogs.yesNoCancel("Do you wish to save your changes?",
                               "No", // default response
                               null, // text
                               "Snippet was modified" //title
                               );
        if (resp == "Cancel") {
            return false;
        }
        if (resp == "Yes") {
            return OK();
        }
    }
    window.arguments[0].res= false;
    return true;
}

function scintillaBlur() {
    scin.isFocused = true;  /* continue to show the caret */
    scin.caretPeriod = 0;
}


function scintillaFocus() {
    scin.caretPeriod = 500;
    snippetvalue.setFocus(); // needed to fix bug 87311
}

function InsertShortcut(shortcutWidget) {
    // Get the shortcut string from the menuitem widget and insert it into
    // the current snippet text. Also, if the menuitem has a "select"
    // attribute select the identified part of the inserted snippet.
    var shortcut = shortcutWidget.getAttribute("shortcut");
    var select = shortcutWidget.getAttribute("select");
    scin.replaceSel(shortcut);
    if (select && shortcut.indexOf(select) != -1) {
        // Current position will be at the end of the inserted shortcut.
        var offset = shortcut.indexOf(select);
        scin.anchor = scin.currentPos - shortcut.length + offset;
        scin.currentPos = scin.anchor + select.length;
    }
    updateOK();
    snippetvalue.setFocus();
}

function update_icon(URI)
{
    try {
        if (URI == 'chrome://komodo/skin/images/toolbox/snippet.svg') {
            document.getElementById('reseticon').setAttribute('disabled', 'true');
        } else {
            if (document.getElementById('reseticon').hasAttribute('disabled')) {
                document.getElementById('reseticon').removeAttribute('disabled');
            }
        }
        document.getElementById('keybindingtab_icon').setAttribute('src', URI);
        document.getElementById('snippettab_icon').setAttribute('src', URI);
        if (URI.indexOf('_missing.png') != -1) {
            document.getElementById('snippettab_icon').setAttribute('tooltiptext', "The custom icon specified for this snippet is missing. Please choose another.");
        } else {
            document.getElementById('snippettab_icon').removeAttribute('tooltiptext');
        }
    } catch (e) {
        log.exception(e);
    }
}

function pick_icon(useDefault /* false */)
{
    try {
        var URI
        if (! useDefault) {
            URI = ko.dialogs.pickIcon();
            if (!URI) return;
        } else {
            URI = 'chrome://komodo/skin/images/toolbox/snippet.svg';
        }
        update_icon(URI);
        updateOK();
    } catch (e) {
        log.exception(e);
    }
}

