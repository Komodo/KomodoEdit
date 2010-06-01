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

var gPriority, gPriorityLabel, gOKButton, gPart, gItem;
var gAccessKey = null;
var tabs, gApplyButton;
var gPartType;
var gObserverSvc;
var partname;

function onLoad() {
    try {
        var dialog = document.getElementById("dialog-custommenuproperties");
        gOKButton = dialog.getButton("accept");
        gApplyButton = dialog.getButton("extra1");
        gApplyButton.setAttribute('label', 'Apply');
        gApplyButton.setAttribute('accesskey', 'a');
        gItem = window.arguments[0].item;
        gPartType = window.arguments[0].type;
        var prettyType = window.arguments[0].prettytype;
        gPart = gItem;
        document.getElementById('propertiestab_icon').setAttribute('src', gPart.iconurl);
        gObserverSvc = Components.classes["@mozilla.org/observer-service;1"].
                  getService(Components.interfaces.nsIObserverService);
        if (window.arguments[0].task == 'new') {
            document.title = "Create New " + prettyType;
            gApplyButton.setAttribute('collapsed', 'true');
        } else {
            document.title = prettyType + " Properties";
        }
        if (gPartType == 'menu') {
            document.getElementById('accessbox').removeAttribute('collapsed');
            gAccessKey = document.getElementById('accesskey');
            gAccessKey.value = gPart.getStringAttribute('accesskey');
        }
        tabs = document.getElementById('tabs');
        partname = document.getElementById('partname');
        partname.value = gPart.getStringAttribute('name');
        gPriority = document.getElementById('priority');
        gPriority.value = String(gPart.getLongAttribute('priority'));
        var tooltip = "A number - the lower it is, the further to the left the " +
            gPartType + " is.";
        gPriority.setAttribute('tooltiptext', tooltip);
        gPriorityLabel = document.getElementById('priority_label');
        gPriorityLabel.setAttribute('tooltiptext', tooltip);

        UpdateField('name', true);
        partname.focus();
        partname.select();
        UpdateOK();
    } catch (e) {
        log.error(e);
    }
};

function OK()  {
    if (_Apply()) {
        window.arguments[0].res = true;
        window.close();
    }
};

function Apply() {
    _Apply();
    gApplyButton.setAttribute('disabled', 'true');
    return false;
}

function _Apply()  {
    try {
        gPart.setLongAttribute('priority', Number(gPriority.value));
        if (gAccessKey) {
            switch (gAccessKey.value.toLowerCase()) {
                case 'f':
                case 'e':
                case 'v':
                case 'd':
                case 'p':
                case 'o':
                case 't':
                case 'w':
                case 'h':
                    alert("The access key '" + gAccessKey.value +
                          "' is reserved by Komodo for its core menus.  Please choose another.");
                    return false;
            }
            gPart.setStringAttribute('accesskey', gAccessKey.value);
        }
        gItem.name = partname.value;
        if (gPartType == 'menu') {
            gObserverSvc.notifyObservers(gPart, 'menu_changed', 'part changed')
        } else {
            gObserverSvc.notifyObservers(gPart, 'toolbar_changed', 'part changed')
        }
        gPart.setStringAttribute('name', partname.value);
        gItem.save();
    } catch (e) {
        log.exception(e);
    }
    return true;
};

function UpdateOK() {
    if (partname.value == '' || gPriority.value== '') {
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
                    document.title = "Unnamed " + gPart.prettytype + " Properties";
                }
                changed = true;
                break;
            case 'priority':
            case 'accesskey':
                changed = true;
                break;
        }

        if (!initializing && changed) {
            UpdateOK();
        }
    } catch (e) {
        log.exception(e);
    }
}

function Cancel()  {
    window.arguments[0].res= false;
    window.close();
};


function keypressForPriority(event) {
    // Filter out all characters except for digits
    if (event.charCode) {
        if (event.charCode < '0'.charCodeAt(0) ||
            event.charCode > '9'.charCodeAt(0)) {
            event.preventDefault();
            event.cancelBubble = true;
        }
    }
}
