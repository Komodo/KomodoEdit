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

var prefServersLog = ko.logging.getLogger('prefs.servers');

var cellparent, cellparent_value;
var servers;
var dialog = {}; //XXX used both for easy access to named XUL elements and to keep
// a handle on functions that we need in PrefAssociation_OkCallback(). Every
// reference to one of these functions that might be called, directly or
// indirectly, from PrefAssociation_OkCallback() must be accessed through
// the dialog object, or this will break.  For consistency, we always call
// these functions through the dialog object.
const XUL_NS = "http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul";
var data = new Object();

// Handlers

function PrefServers_OnLoad() {
    dialog = {};
    dialog.server_types = document.getElementById("server_types");
    dialog.serversList = document.getElementById("serversList");
    dialog.serversPopup = document.getElementById("serversPopup");
    dialog.alias = document.getElementById("alias");
    dialog.hostname = document.getElementById("hostname");
    dialog.port = document.getElementById("port");
    dialog.path = document.getElementById("path");
    dialog.username = document.getElementById("username");
    dialog.password = document.getElementById("password");
    dialog.privatekeyBox = document.getElementById("ssh_privatekey_vbox");
    dialog.privatekeyTextbox = document.getElementById("privatekey");
    dialog.ftp_passive_mode = document.getElementById("ftp_passive_mode");
    dialog.buttonDelete = document.getElementById("buttonDelete");
    dialog.buttonAdd = document.getElementById("buttonAdd");
    dialog.anonymousCheckbox = document.getElementById("anonymousCheckbox");
    dialog.buttonDelete.setAttribute('disabled', 'true');
    dialog.buttonAdd.setAttribute('disabled', 'true');

    parent.hPrefWindow.onpageload();
    checkAddButtonStatus();
    
    // fill out the associations tree - should cache this entire tree.
    _setMenuList(null);
}

function OnPreferencePageOK(prefset) {
    var oldServers = data.original;
    var newServers = data.servers;

    // Check if there are any unsaved changes for the server prefs.
    if (!dialog.buttonAdd.hasAttribute('disabled') ||
        dialog.buttonAdd.getAttribute('disabled') == 'false') {
        // Unsaved changes, prompt to see if they want these changes saved
        // XXX: Cannot use ko.dialogs.yesNoCancel(), as this will result in error
        //      messages in koPrefWindow.onOK(), which is calling this guy.
        //      Using ko.dialogs.yesNo() for now.
        //var answer = ko.dialogs.yesNoCancel(
        var answer = ko.dialogs.yesNo(
            "Do you wish to save changes to server '"+dialog.alias.value+"'?", // prompt
            "Yes", // default answer
            null, // text
            "Server preferences"); // title
        if (answer == "Cancel") {
            // XXX: This will never occur using ko.dialogs.yesNo()
            return false;
        } else if (answer == "Yes") {
            if (!onAddServerEntry()) {
                return false;
            }
        } // else we just continue on normally
    }

    // Ensure the timeout checkbox is valid
    var timeoutTextbox = document.getElementById("remotefiles_defaultConnectionTimeout");
    if (timeoutTextbox) {
      var timeoutAsInt = parseInt(timeoutTextbox.value);
      if (timeoutAsInt <= 0) {
        ko.dialogs.alert("Servers: The default connection timeout field must be an integer greater than zero.");
        return false;
      }
    }

    // only write out the prefs if they have actually changed
    if (!areServerListsEquivalent(oldServers, newServers)) {
        var RCService = Components.classes["@activestate.com/koRemoteConnectionService;1"].
                        getService(Components.interfaces.koIRemoteConnectionService);
        RCService.saveServerInfoList(newServers.length, newServers);
    }
    return true;
}

function OnPreferencePageInitalize(prefset) {
    var RCService = Components.classes["@activestate.com/koRemoteConnectionService;1"].
                    getService(Components.interfaces.koIRemoteConnectionService);
    var server_count = {};
    data.servers = RCService.getServerInfoList(server_count);
    // Make a copy, to later compare to the modified servers.
    data.original = RCService.getServerInfoList(server_count);
}

function OnPreferencePageLoading(prefset) {
    document.getElementById("buttonDelete").setAttribute('disabled', 'true');
    document.getElementById("buttonAdd").setAttribute('disabled', 'true');
    servers = data.servers;
}


function _strcmp(a,b) {
    if (a==b) return 0;
    if (a<b) return -1;
    return 1;
}

// Return true if the arrays of Association objects, a and b, correspond to
// the same underlying representation as a preference.
function areServerListsEquivalent(a, b) {
  if (a.length != b.length) return false;

  for (var i = 0; i < a.length; i++) {
    // we don't care about the IDs
    if (a[i].protocol != b[i].protocol ||
        a[i].alias != b[i].alias ||
        a[i].hostname != b[i].hostname ||
        a[i].port != b[i].port ||
        a[i].path != b[i].path ||
        a[i].passive != b[i].passive ||
        a[i].username != b[i].username ||
        a[i].password != b[i].password ||
        a[i].privatekey != b[i].privatekey) {
      return false;
    }
  }

  return true;
}

function _setMenuList(selectedServerAlias) {
    var menulist = document.getElementById("serversList");
    var menupopup = document.getElementById("serversPopup");
    var menuitem;
    var indexSelect = -1;
    var children = menupopup.childNodes;
    var i;
    while (menupopup.hasChildNodes()) {
        menupopup.removeChild(menupopup.firstChild);
    }
    for (i = 0; i < servers.length; i++) {
        menuitem = createServersMenuItem(servers[i]);
        menupopup.appendChild(menuitem);
        if (servers[i].alias == selectedServerAlias)
            indexSelect = i;
    }
    if (servers.length > 0)  {
        if (indexSelect == -1) {
            indexSelect = 0;
            selectedServerAlias = servers[0].alias;
        }
        menulist.selectedIndex = indexSelect;
        loadServerEntryWithAlias(selectedServerAlias);
    }
}

function togglePassiveFTPSettings() {
    if (dialog.server_types.selectedIndex <= 1) {
        // FTP servers, show the passive
        document.getElementById("ftp_passive_mode_vbox").setAttribute('collapsed', 'false');
    } else {
        document.getElementById("ftp_passive_mode_vbox").setAttribute('collapsed', 'true');
    }
}

function toggleSshPrivatekeySettings() {
    var server_type = dialog.server_types.selectedItem.getAttribute("label");
    if (server_type == "SFTP" || server_type == "SCP") {
        dialog.privatekeyBox.removeAttribute("collapsed");
    } else {
        dialog.privatekeyBox.setAttribute("collapsed", "true");
    }
}

function checkAddButtonStatus() {
    var alias = dialog.alias.value;
    var hostname = ko.stringutils.strip(dialog.hostname.value);
    if (alias && hostname) {
        // enable add button
        document.getElementById("buttonAdd").removeAttribute('disabled');
    } else {
        // dissable add button
        document.getElementById("buttonAdd").setAttribute('disabled', 'true');
    }
    togglePassiveFTPSettings();
    toggleSshPrivatekeySettings();
}

var current_server_idx = -1;
function onAddServerEntry() {
    var protocol = dialog.server_types.selectedItem.getAttribute("label");
    var alias = dialog.alias.value;
    var hostname = ko.stringutils.strip(dialog.hostname.value);
    var port = dialog.port.value;
    if (!port)
        port = -1;
    var path = dialog.path.value;
    var username = dialog.username.value;
    var password = dialog.password.value;
    var passive =  dialog.ftp_passive_mode.selectedIndex;
    var privatekey = dialog.privatekeyTextbox.value;
    // prevent adding empty entries
    if (!alias || !hostname || !username) {
        prefServersLog.warn("Missing a required field. Name, Host Name and User Name are required fields.");
        return false;
    }
    if (((protocol == "SFTP" || protocol == "SCP") && parseInt(port) == 21) ||
        (protocol == "FTP" && parseInt(port) == 22)) {
        var message = "You may have specified the wrong port. " +
                      "FTP uses port 21 by default. " +
                      "SFTP and SCP use port 22 by default. " +
                      "Do you wish to keep this setting?";
        if (ko.dialogs.yesNo(message,
                             "No" /* response */,
                             null /* text */,
                             "WARNING: Incorrect port?" /* title */) == "No") {
            return false;
        }
    }

    var serverInfo = Components.classes["@activestate.com/koServerInfo;1"].
                        createInstance(Components.interfaces.koIServerInfo);
    if (current_server_idx > -1) {
        var oldServerInfo = servers[current_server_idx];
        // Preserving the GUID allows us to perform an update more easily
        serverInfo.init(oldServerInfo.guid, protocol, alias, hostname, port,
                        username, password, path, passive, privatekey);
        servers[current_server_idx] = serverInfo;
        // Update the menuitem label, in case the alias was changed.
        dialog.serversList.selectedItem.setAttribute('label', serverInfo.alias);
        dialog.serversList.setAttribute('label', serverInfo.alias);
    } else {
        if (getAliasIndex(alias) > -1) {
            alert("The entry name must be unique, please correct this.\n");
            return false;
        }
        // LoginManagerStorage will create a GUID when null
        serverInfo.init(null, protocol, alias, hostname, port, username, password, path,
                        passive, privatekey);
        servers.push(serverInfo);
        servers.sort(function (a,b) { return _strcmp(a.alias,b.alias); } );
        _setMenuList(serverInfo.alias);
    }
    setMenuSelection("serversList",serverInfo.alias);
    dialog.buttonAdd.setAttribute('disabled', 'true');
    return true;
}

function setMenuSelection(id, label) {
    var menu = document.getElementById(id);
    var items = menu.getElementsByTagName("menuitem");
    for (var i=0;i<items.length;i++) {
        if (items[i].getAttribute("label") == label) {
            menu.selectedIndex = i
            return;
        }
    }
}

function loadServerEntryWithAlias(server_alias) {
    var server_idx = getAliasIndex(server_alias);
    if (!server_idx < 0) {
        return;
    }
    var server = servers[server_idx];
    setMenuSelection("server_types", server.protocol);

    dialog.alias.value = server.alias;
    dialog.hostname.value = server.hostname;
    if (server.port < 0)
        dialog.port.value = "";
    else
        dialog.port.value = server.port;
    dialog.path.value = server.path;
    dialog.username.value = server.username;
    dialog.password.value = server.password;
    dialog.ftp_passive_mode.selectedIndex = server.passive ? 1: 0;
    dialog.privatekeyTextbox.value = server.privatekey;

    toggleSshPrivatekeySettings();

    current_server_idx = server_idx;
    dialog.buttonDelete.removeAttribute('disabled');
    dialog.buttonAdd.setAttribute('disabled','true');
    dialog.buttonAdd.setAttribute('label', 'Update');
    if (dialog.username.value == 'anonymous')
        dialog.anonymousCheckbox.checked = true;
    else
        dialog.anonymousCheckbox.checked = false;
    togglePassiveFTPSettings();
}

function onDeleteServerEntry() {
    if (current_server_idx > -1) {
        servers.splice(current_server_idx, 1);
        dialog.serversPopup.removeChild(dialog.serversList.selectedItem);
        onClearServerEntry();
        if (servers.length > 0) {
            var menulist = document.getElementById("serversList");
            menulist.selectedIndex = 0;
            loadServerEntryWithAlias(servers[0].alias);
        }
    }
    togglePassiveFTPSettings();
}

function onClearServerEntry() {
    dialog.server_types.selectedIndex = 0;
    dialog.serversList.selectedIndex = -1;
    dialog.alias.value = "";
    dialog.hostname.value = "";
    dialog.port.value = "";
    dialog.path.value = "";
    dialog.username.value = "";
    dialog.password.value = "";
    dialog.ftp_passive_mode.selectedIndex = 1;
    current_server_idx = -1;
    dialog.buttonDelete.setAttribute('disabled', 'true');
    dialog.buttonAdd.setAttribute('disabled', 'true');
    dialog.buttonAdd.setAttribute('label', 'Add');
    dialog.anonymousCheckbox.checked = false;
    dialog.privatekeyTextbox.value = "";

    togglePassiveFTPSettings();
    toggleSshPrivatekeySettings();
}

// DOM construction helpers

function createServersMenuItem(server) {
    var cell = document.createElementNS(XUL_NS, 'menuitem');
    cell.setAttribute('label', server.alias);
    cell.setAttribute("oncommand", "loadServerEntryWithAlias(this.getAttribute('label'))");
    return cell;
}

function getIdIndex(id) {
    for (var i = 0; i < servers.length; i++) {
        if (id == servers[i].id)
            return i;
    }
    return -1;
}

function getAliasIndex(alias) {
    for (var i = 0; i < servers.length; i++) {
        if (alias == servers[i].alias)
            return i;
    }
    return -1;
}

function browseForSSHKeyfile() {
    var osSvc = Components.classes["@activestate.com/koOs;1"].
                 getService(Components.interfaces.koIOs);
    var path = "";
    var starting_path = "";
    // If a key is already specified, use the directory of the key path.
    if (dialog.privatekeyTextbox.value) {
        path = osSvc.path.dirname(dialog.privatekeyTextbox.value);
        if (osSvc.path.exists(path)) {
            starting_path = path;
        }
    }
    // Else, try the user's home directory, in the ".ssh" folder.
    if (!starting_path) {
        path = osSvc.path.join(osSvc.path.expanduser("~"), ".ssh");
        if (osSvc.path.exists(path)) {
            starting_path = path;
        }
    }
    var filepath = ko.filepicker.browseForFile(starting_path);
    if (!filepath) {
        return;
    }
    dialog.privatekeyTextbox.value = filepath;
}

// Not used anywhere, commenting out for now -- ToddW
// Remove whitespace from both ends of a string
//function trimString(string)
//{
//    if (!string)
//        return "";
//    return string.replace(/(^\s+)|(\s+$)/g, '');
//}


// Not used anywhere, commenting out for now -- ToddW
//function onBrowseFTP() {
//    // get all the info we want to use
//    var type = dialog.server_types.value;
//    var alias = dialog.alias.value;
//    var hostname = dialog.hostname.value;
//    var port = dialog.port.value;
//    var path = dialog.path.value;
//    var username = dialog.username.value;
//    var password = dialog.password.value;
//    if (password != null && password != "") {
//        // this was already saved, get the password
//        var idx = getAliasIndex(alias);
//        var server = servers[idx];
//        password = server.password;
//    }
//    // build an explicit path
//    var url = type+"://";
//    if (username) {
//        url += username
//        if (password) url += ":"+password;
//        url += "@";
//    }
//    url+=hostname
//    if (port) url+= ":"+port;
//    url+=path;
//
//    var fileBrowser = doFilebrowser("Pick Directory", url,
//            Components.interfaces.nsIFilePicker.modeGetFolder);
//    if (fileBrowser) {
//        //dump("selected "+fileBrowser.directory+"\n");
//        dialog.path.value = fileBrowser.directory;
//    }
//}

function fillAnonymous()  {
    var loginUserBox = document.getElementById('username');
    var loginPwdBox = document.getElementById('password');
    loginUserBox.value = 'anonymous';
    loginPwdBox.value = 'user@anon.org';
}
