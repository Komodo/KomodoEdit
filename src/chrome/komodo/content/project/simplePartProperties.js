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


//Arguments to window.arguments[0] are:
//    Required:
//        item: the item being edited
//        task: 'new' or 'edit'
//        type: the type of the part ('URL', 'template', etc...)
//        src:  the chrome of the image to be used in the dialog
//    Optional:
//        valueToTextConverter: function that takes the part's 'value'
//                              and converts it to the text which is
//                              stuffed in the 'value' textbox.
//
//        textToValueConverter: function that takes the contents of the
//                              'value' textbox and converts it to what
//                              will be stuffed in the part's value.

var log = ko.logging.getLogger("simplePartProperties");

var partname, partvalue, gOKButton, keybinding, gItem, gItem;
var shortcut_tab, part_tab, tabs, partnamelabel, gApplyButton;
var partViewManager;
var gItemType;
var textToValueConverter = null;
var valueToTextConverter = null;
var gDefaultPartIconURL = null;

function onLoad() {
    try {
        var dialog = document.getElementById("dialog-simplepartproperties");
        gOKButton = dialog.getButton("accept");
        gApplyButton = dialog.getButton("extra1");
        gApplyButton.setAttribute('label', 'Apply');
        gApplyButton.setAttribute('accesskey', 'a');

        gItem = window.arguments[0].item;
        gItemType = gItem.type;
        if ('textToValueConverter' in window.arguments[0]) {
            textToValueConverter = window.arguments[0].textToValueConverter;
        }
        if ('valueToTextConverter' in window.arguments[0]) {
            valueToTextConverter = window.arguments[0].valueToTextConverter;
        }
        gDefaultPartIconURL = window.arguments[0].imgsrc;
        update_icon(gItem.iconurl);

        if (window.arguments[0].task == 'new') {
            document.title = "Create New " + gItem.prettytype;
            gApplyButton.setAttribute('collapsed', 'true');
        } else {
            document.title =  gItem.prettytype + " Properties";
        }

        tabs = document.getElementById('tabs');
        shortcut_tab = document.getElementById('shortcut_tab');
        part_tab = document.getElementById('part_tab');
        partname = document.getElementById('partname');
        partname.value = gItem.getStringAttribute('name');
        partvalue = document.getElementById('partvalue');
        partnamelabel = document.getElementById('partnamelabel');
        tabs.selectedTab = part_tab; // we may want to change this sometimes.

        keybinding = document.getElementById('keybindings');
        keybinding.gKeybindingMgr = opener.ko.keybindings.manager;
        keybinding.part = gItem;

        keybinding.commandParam = gItem.id;
        var value = gItem.value;
        if (valueToTextConverter) {
            value = valueToTextConverter.call(this, value);
        }
        partvalue.value = value;

        keybinding.init();
        keybinding.updateCurrentKey();
        UpdateField('name', true);
        partname.focus();
        partname.select();
        updateOK();
    } catch (e) {
        log.error(e);
    }
};

function OK()  {
    if (_Apply()) {
        window.arguments[0].res = true;
    }
    if (window.arguments[0].task == 'new') {
        var parent = window.arguments[0].parent;
        opener.ko.toolbox2.addNewItemToParent(gItem, parent);
    }
    window.close();
};

function Apply() {
    _Apply();
    gApplyButton.setAttribute('disabled', 'true');
    return false;
}

function _Apply()  {
    try {
        // The keybinding needs the commandparam to be set before the application would ever work.
        var retval = keybinding.apply(); // This may return false if a keybinding is partially entered
        if (!retval) return retval;
    } catch (e) {
        opener.log.error(e);
        log.exception(e);
        dump(e + "\n");
        return false;
    }
    try {

    var value = partvalue.value;
    if (textToValueConverter) {
        value = textToValueConverter.call(this, value);
    }
    gItem.value = value;
    gItem.name = partname.value;

    var iconuri = document.getElementById('propertiestab_icon').getAttribute('src');
    gItem.iconurl = iconuri;

    opener.ko.projects.invalidateItem(gItem);
    if (window.arguments[0].task != "new") {
        gItem.save();
    }
    } catch (e) {
        opener.log.error(e);
        log.exception(e);
        alert("Internal error: " + e.message);
        return false;
    }
    return true;
};

function updateOK() {
    if (partname.value == '' || partvalue.value== '') {
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
                var name = partname.value;
                if (name) {
                    document.title = "'"+name+"' Properties";
                } else {
                    document.title = "Unnamed " + gItem.prettytype + " Properties";
                }
                partnamelabel.value = name;
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
    window.arguments[0].res= false;
    window.close();
};

function Help() {
    switch (gItemType) {
    case "url":
    case "URL":
        ko.help.open("url_shortcut_options");
        break;
    case "template":
        ko.help.open("template_options");
        break;
    default:
        log.error("cannot launch help: unknown part type: '"+gItemType+"'\n");
    }
};

function update_icon(URI)
{
    try {
        if (URI == gDefaultPartIconURL) {
            document.getElementById('reseticon').setAttribute('disabled', 'true');
        } else {
            if (document.getElementById('reseticon').hasAttribute('disabled')) {
                document.getElementById('reseticon').removeAttribute('disabled');
            }
        }
        document.getElementById('keybindingtab_icon').setAttribute('src', URI);
        document.getElementById('propertiestab_icon').setAttribute('src', URI);
        if (URI.indexOf('_missing.png') != -1) {
            document.getElementById('propertiestab_icon').setAttribute('tooltiptext', "The custom icon specified for this " + gItem.prettytype + " is missing. Please choose another.");
        } else {
            document.getElementById('propertiestab_icon').removeAttribute('tooltiptext');
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
            URI = gDefaultPartIconURL;
        }
        update_icon(URI);
        updateOK();
    } catch (e) {
        log.exception(e);
    }
}
