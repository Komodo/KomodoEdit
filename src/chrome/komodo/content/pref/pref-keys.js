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

// Constants and global variables
var dialog  = {};

// Handlers

function PrefKeys_OnLoad() {
    try {
        dialog.tree = document.getElementById('keybinding-tree');
        dialog.deck = document.getElementById('deck');
        dialog.nohits = document.getElementById('nohits');
        dialog.configurations= document.getElementById('configurations');
        dialog.configpopup= document.getElementById('configpopup');
        dialog.filter = document.getElementById('commands-filter-textbox');
        dialog.gKeybindingMgr = getKoObject('keybindings').manager;
        dialog.editkeybinding = document.getElementById('keybinding');
        dialog.editkeybinding.gKeybindingMgr = dialog.gKeybindingMgr;
        dialog.mainwindow = dialog.editkeybinding.mainwindow =
	    (('prefs' in parent.opener.ko) ? parent.opener
	     : parent.opener.ko.windowManager.getMainWindow());
        dialog.gKeybindingMgr.parseGlobalData();
        dialog.deleteButton = document.getElementById('deleteConfiguration');
        dialog.viCheckbox = document.getElementById('enableViKeybindings');
        updateUI();
        dialog.editkeybinding.updateCurrentKey();
        updateConfigMenu();
        updateCommandList()
        parent.hPrefWindow.onpageload();
    } catch (e) {
        parent.prefLog.error(e)
    }
}

function OnPreferencePageInitalize(prefset)
{
    dialog.prefset = prefset;
    dialog.originalConfiguration = dialog.gKeybindingMgr.currentConfiguration;
}

// Start up & returning to this panel in a session
function OnPreferencePageLoading(prefset)
{
    dialog.prefset = prefset;
}

function OnPreferencePageCancel(prefset) {
    try {
        if (typeof(dialog) != 'undefined' && dialog && dialog.gKeybindingMgr) {
            dialog.gKeybindingMgr.revertToPref(dialog.originalConfiguration);
        }
    } catch (e) {
        parent.prefLog.error("Error in PrefKeys_CancelCallback" + e);
    }
    return true;
}

function OnPreferencePageOK(prefset) {
    try {
        if (typeof(dialog) != 'undefined' && dialog && dialog.gKeybindingMgr) {
            dialog.gKeybindingMgr.saveAndApply(prefset);
        }
        return true;
    } catch (e) {
        parent.prefLog.exception(e);
        var bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
            .getService(Components.interfaces.nsIStringBundleService)
            .createBundle("chrome://komodo/locale/pref/pref-languages.properties");
        return ignorePrefPageOKFailure(prefset,
                bundle.GetStringFromName("savingKeyBindingsFailed"),
                                       e.toString());
    }
}

// Callbacks and global functions having to do with configuration handling

function updateConfigMenu() {
    // Update the configuration menu based on the list of known configurations

    var configs = dialog.gKeybindingMgr.getConfigurations();
    var currentConfig = dialog.gKeybindingMgr.currentConfiguration;
    var menuitem;
    while (dialog.configpopup.hasChildNodes()) {
        dialog.configpopup.removeChild(dialog.configpopup.lastChild);
    }
    var c;
    var selectedmenuitem = null;
    for (var i in configs) {
        c = configs[i];
        if (c == "_vi") {
            // Vi is not a visible choice, it's added on to existing bindings
            continue;
        }
        menuitem = document.createElement('menuitem');
        menuitem.setAttribute('label', c);
        menuitem.setAttribute('id', c);
        if (! dialog.gKeybindingMgr.configurationWriteable(c)) {
            menuitem.setAttribute('class','primary_menu_item');
        }
        menuitem.setAttribute('oncommand', "return switchConfig(\""+configs[i]+"\");");
        dialog.configpopup.appendChild(menuitem);
        if (c == currentConfig) {
            selectedmenuitem = menuitem;
        }
    }
    if (selectedmenuitem) {
        dialog.configurations.selectedItem = selectedmenuitem;
    } else {
        dialog.configurations.selectedItem = dialog.configpopup.firstChild;
    }
    dialog.configurations.setAttribute("label", dialog.gKeybindingMgr.currentConfiguration);
}


// called when users switch to another configuration from the menulist
function switchConfig(configname) {
    // Set callback to update the UI once vi is loaded, see:
    //   http://bugs.activestate.com/show_bug.cgi?id=69623
    dialog.mainwindow.gVimController.enabledCallback = _viLoadCallback;
    // XXX - switchConfiguration only takes one argument!?
    dialog.gKeybindingMgr.switchConfiguration(configname, dialog.prefset);
    updateCommandList();
    updateUI();
}

function updateUI() {
    try {
        var configname = dialog.gKeybindingMgr.currentConfiguration;
        dialog.configurations.selectedItem = document.getElementById(configname)
        if (dialog.gKeybindingMgr.configurationWriteable(configname)) {
            dialog.deleteButton.removeAttribute('disabled');
        } else {
            dialog.deleteButton.setAttribute('disabled', 'true');
        }
        dialog.viCheckbox.checked = dialog.mainwindow.gVimController.enabled;
        if (dialog.viCheckbox.checked) {
            dialog.viCheckbox.setAttribute('disabled', 'true');
        } else {
            dialog.viCheckbox.removeAttribute('disabled');
        }
    } catch (e) {
        ko.logging.getLogger("pref-keys").exception(e);
    }
}

function deleteConfiguration()  {
    // called by the Delete button next to the configuration menu list.
    var configname = dialog.configurations.selectedItem.getAttribute('id');
    if (typeof(configname) == 'undefined') {
        parent.prefLog.error("SelectedItem doesn't have a data attribute");
        ko.dialogs.alert("There was a problem delete the configuration.");
        return;
    }
    var shortname = configname;
    if (ko.dialogs.yesNo("Are you sure you want to delete the scheme '" + shortname +"'?  This action cannot be undone.") == 'No') {
        return;
    }
    dialog.gKeybindingMgr.deleteConfiguration(configname, dialog.prefset);
    updateConfigMenu();
    updateUI();
}

function _viLoadCallback()
{
    //dump("_viLoadCallback called\n");
    updateCommandList();
    updateUI();
}

function setViKeybindings(checkbox)
{
    dialog.tree.selectedIndex = -1;
    // Callback for when document.loadOverlay() is finished.
    //dump("setViKeybindings\n");
    if (checkbox.checked) {
        // Enable vi keybindings - check if we need to create a new config
        var success = newConfiguration();
        if (!success) {
            updateUI();
            return;
        }
        dialog.mainwindow.gVimController.enabledCallback = _viLoadCallback;
        dialog.gKeybindingMgr.mergeSchemeConfiguration('_vi');
    }
}

function selectKey(event, treeitem)  {
    // Called by the handler in the command list tree.
    var item = null;
    if (typeof(treeitem) != 'undefined' && treeitem)
        item = treeitem;
    else {
        item = dialog.tree.selectedItem;
    }
    if (item) {
        dialog.editkeybinding.commandId = item.getAttribute('name');
        dialog.editkeybinding.clearUsedBys();
        dialog.editkeybinding.updateCurrentKey();
    }
}

function selectCommandFromSelectedUseBy(event) {
    // originalTarget should be the listbox defined in keybindings.xml
    var listbox = event.originalTarget;
    // Ensure it's coming from the listbox, not some other xul element
    if (listbox && listbox.nodeName == "xul:listbox" &&
        listbox.selectedIndex >= 0) {
        var commandname = listbox.selectedItem.getAttribute('name');
	var numrows = dialog.tree.getRowCount();
        var listitem;
        var listitem_commandname;
        var i;
	for (i = 0; i < numrows ; i++) {
	    listitem = dialog.tree.childNodes[i];
            listitem_commandname = listitem.getAttribute('name');
            if (commandname == listitem_commandname) {
                var tree_index = i;
                if (i > 0) {
                    // Was not correct offset sometimes... not sure why needs -1
                    tree_index -= 1;
                }
                dialog.tree.ensureIndexIsVisible(tree_index);
                dialog.tree.selectedIndex = tree_index;
                dialog.editkeybinding.commandId = listitem_commandname;
                dialog.editkeybinding.updateCurrentKey();
                break;
            }
	}
    }
}

function updateCommandList() {
    try {
	// Add treeitems to the tree based on the information from the keybinding manager.
	// This is slow, which is why it's inlined.
	var i, command;
	var filter = dialog.filter.value.toLowerCase();
	var filter_words = filter.split(" ");
	var commanditems = dialog.gKeybindingMgr.commanditems
	var numrows = dialog.tree.getRowCount();
	for (i = numrows-1; i >= 0 ; i--) {
	    dialog.tree.removeItemAt(i);
	}
	var item;
	var count = 0;
	var desc;
	for (i in commanditems) {
	    command = commanditems[i];
	    if (!command.desc)
		continue;
	    if (filter) {
		var matched = true;
		desc = command.desc.toLowerCase();
		for (var j=0; j < filter_words.length; j++) {
		    if (desc.indexOf(filter_words[j]) == -1) {
			matched = false;
			break;
		    }
		}
		if (!matched)
		    continue;
	    }
	    item = dialog.tree.appendItem(command.desc, command);
	    item.setAttribute('name', command.name);
	    item.setAttribute('data', command.desc);
	    count ++;
	}
	if (count == 0) {
	    dialog.deck.selectedIndex = 0;
	    // to avoid bad resizing on empty lists
	    dialog.tree.appendItem('', '');
	} else {
	    dialog.deck.selectedIndex = 1;
	}
    } catch (e) {
	ko.logging.getLogger("pref-keys").exception(e);
    }
}

function newConfiguration()
{
    var currentConfig = dialog.gKeybindingMgr.currentConfiguration;
    var shortname = currentConfig;
    var newSchemeName;
    var i, ok;
    var fnameRe = /^[\w\d ]*$/;
    var knownConfigs = dialog.gKeybindingMgr.getConfigurations();
    var _viewsBundle = Components.classes["@mozilla.org/intl/stringbundle;1"].
        getService(Components.interfaces.nsIStringBundleService).
        createBundle("chrome://komodo/locale/views.properties");
    while (1) {
        newSchemeName = ko.dialogs.prompt(
                          _viewsBundle.formatStringFromName(
                                    "enterNewSchemeNameBasedOnScheme.template",
                                    [shortname], 1),
                          _viewsBundle.GetStringFromName("newSchemeName.label"),
                          newSchemeName // default value
                                          );
        if (!newSchemeName) {
            return false;
        }
        ok = true;
        // Check to make sure that the name isn't already taken and that it can be written to disk.
        for (i = 0; i < knownConfigs.length; i++) {
            if (knownConfigs[i] == newSchemeName) {
                ko.dialogs.alert("The scheme name '" + newSchemeName + "' is already used.  Please choose another.")
                ok = false;
                break;
            }
        }
        if (!ok) continue;
        if (fnameRe.test(newSchemeName)) {
            ok = true;
            break;
        }
        ko.dialogs.alert("Scheme names must contain alphanumeric characters, spaces or underscores only.  Please choose another name.");
    }
    newSchemeName = dialog.gKeybindingMgr.makeNewConfiguration(newSchemeName, dialog.prefset);
    updateConfigMenu();
    switchConfig(newSchemeName);
    return true;
}
