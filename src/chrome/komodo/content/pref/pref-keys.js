/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

// Constants and global variables
var dialog  = {};

var log = ko.logging.getLogger("pref-keys");

// Handlers

function PrefKeys_OnLoad() {
    try {
        dialog.tree = document.getElementById('keybinding-tree');
        dialog.deck = document.getElementById('deck');
        dialog.nohits = document.getElementById('nohits');
        dialog.configurations= document.getElementById('configurations');
        dialog.configpopup= document.getElementById('configpopup');
        dialog.filter = document.getElementById('commands-filter-textbox');
        dialog.gKeybindingMgr = parent.opener.gKeybindingMgr;
        dialog.editkeybinding = document.getElementById('keybinding');
        dialog.editkeybinding.gKeybindingMgr = dialog.gKeybindingMgr;
        dialog.mainwindow = dialog.editkeybinding.mainwindow = parent.opener;
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
    }
    return false;
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
    for (i in configs) {
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
        log.exception(e);
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
        dialog.editkeybinding.updateCurrentKey();
    }
}

function ensureSelectedUsedbyKeyIsVisible(event) {
    // originalTarget should be the listbox defined in keybindings.xml
    var listbox = event.originalTarget;
    // Ensure it's coming from the listbox, not some other xul element
    if (listbox && listbox.nodeName == "xul:listbox" &&
        listbox.selectedIndex >= 0) {
        // commandAndKeyname contains the description and the key bindings
        // Example: "Find: Find... [Ctrl-F]"
        var commandAndKeyname = listbox.selectedItem.label;
        //dump("commandAndKeyname: " + commandAndKeyname + "\n");
	var numrows = dialog.tree.getRowCount();
        var listitem;
        // commandName will just contain the description
        // Example: "Find: Find..."
        var commandName;
        var i;
	for (i = 0; i < numrows ; i++) {
	    listitem = dialog.tree.childNodes[i];
            commandName = listitem.getAttribute('data');
            if (commandName && commandAndKeyname.indexOf(commandName) == 0) {
                //dump("Found commandName: " + commandName + "at row: " + i + "\n");
                if (i == 0) {
                    dialog.tree.ensureIndexIsVisible(i);
                } else {
                    // Was not correct offset sometimes... not sure why needs -1
                    dialog.tree.ensureIndexIsVisible(i-1);
                }
                break;
            }
	}
    }
}

var _updateTimer = 0;

function scheduleUpdateCommandList() {
    if (_updateTimer) {
	window.clearTimeout(_updateTimer);
    }
    _updateTimer = window.setTimeout("updateCommandList()", 100);
}

function updateCommandList() {
    try {
	_updateTimer = 0;
	// Add treeitems to the tree based on the information from the keybinding manager.
	// This is slow, which is why it's inlined.
	var i, command;
	var filter = dialog.filter.value.toLowerCase();
	var commanditems = dialog.gKeybindingMgr.commanditems
	var numrows = dialog.tree.getRowCount();
	for (i = numrows-1; i >= 0 ; i--) {
	    dialog.tree.removeItemAt(i);
	}
	var item;
	var count = 0;
	for (i in commanditems) {
	    command = commanditems[i];
	    if (command.desc &&
                (filter == '' || command.desc.toLowerCase().indexOf(filter) != -1)) {
		item = dialog.tree.appendItem(command.desc,command);
		item.setAttribute('name', command.name);
		item.setAttribute('data', command.desc);
		count ++;
	    }
	}
	if (count == 0) {
	    dialog.deck.selectedIndex = 0;
	    // to avoid bad resizing on empty lists
	    dialog.tree.appendItem('', '');
	} else {
	    dialog.deck.selectedIndex = 1;
	}
    } catch (e) {
	log.exception(e);
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
    while (1) {
        newSchemeName = ko.dialogs.prompt("Enter a new scheme name.  The new scheme will be based on the currently selected '" +
                                      shortname + "' scheme.", "New Scheme Name:",
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
    switchConfig(newSchemeName);
    return true;
}

function onFilterKeypress(event) {
    try {
        if (event.keyCode == event.DOM_VK_RETURN ||
	    event.keyCode == event.DOM_VK_ENTER ||
	    (event.keyCode == event.DOM_VK_TAB && !event.ctrlKey)) {
            event.cancelBubble = true;
            event.stopPropagation();
            event.preventDefault();
            dialog.tree.focus();
	    if (dialog.tree.selectedIndex == -1) {
		dialog.tree.selectedIndex = 0;
	    }
            return;
        }
        if (event.keyCode == event.DOM_VK_ESCAPE) {
            if (dialog.filter.value != '') {
                dialog.filter.value = '';
                scheduleUpdateCommandList();
                event.cancelBubble = true;
                event.stopPropagation();
                event.preventDefault();
            }
            return;
        }
        if ((event.ctrlKey || event.metaKey) && event.charCode == 'z'.charCodeAt(0)) {
            // ctrl-z doesn't do the right thing w.r.t. calling 'oninput',
            // so we do it ourselves.
	    scheduleUpdateCommandList();
        }
    } catch (e) {
        log.exception(e);
    }

}
