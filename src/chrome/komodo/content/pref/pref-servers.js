/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

// Constants and global variables

var prefServersLog = ko.logging.getLogger('prefs.servers');

var cellparent, cellparent_value;
const VK_ENTER = 13;  // the keycode for the "Enter" key
var servers;
var dialog = {}; //XXX used both for easy access to named XUL elements and to keep
// a handle on functions that we need in PrefAssociation_OkCallback(). Every
// reference to one of these functions that might be called, directly or
// indirectly, from PrefAssociation_OkCallback() must be accessed through
// the dialog object, or this will break.  For consistency, we always call
// these functions through the dialog object.
const XUL_NS = "http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul";
var data = new Object();

// Classes

function Server(type, alias, hostname, port, path, username, password) {
    this.type = type;
    this.alias = alias;
    this.hostname = hostname;
    this.port = port;
    this.path = path;
    this.username = username;
    this.password = password;
    this.id = Server._generateId();
}

// Each Association object has a unique identifier.  This is used to
// establish a relationship between the association object and the
// items in the tree that represent it.

Server._index = 0;  // used for generating ids
Server._generateId = function() {
    return "server" + Server._index++;
}


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
    dialog.alias = document.getElementById("alias");
    dialog.alias = document.getElementById("alias");
    dialog.buttonDelete = document.getElementById("buttonDelete");
    dialog.buttonAdd = document.getElementById("buttonAdd");
    dialog.anonymousCheckbox = document.getElementById("anonymousCheckbox");
    dialog.buttonDelete.setAttribute('disabled', 'true');
    dialog.buttonAdd.setAttribute('disabled', 'true');

    parent.hPrefWindow.onpageload();
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
            onAddServerEntry();
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
      var passwordmanager = Components.classes["@mozilla.org/passwordmanager;1"].getService(Components.interfaces.nsIPasswordManager);
      // just remove all old servers and add all new servers
      for (var i = 0; i < oldServers.length; i++) {
          var hostdata = oldServers[i].type+":"+oldServers[i].alias+":"+
                          oldServers[i].hostname+":"+oldServers[i].port+":"+
                          oldServers[i].path;
          //dump("removing "+hostdata+"\n");
          passwordmanager.removeUser(hostdata, oldServers[i].username);
      }
      for (var i = 0; i < newServers.length; i++) {
          var hostdata = newServers[i].type+":"+newServers[i].alias+":"+
                          newServers[i].hostname+":"+newServers[i].port+":"+
                          newServers[i].path;
          //dump("adding "+hostdata+"\n");
          passwordmanager.addUser(hostdata, newServers[i].username, newServers[i].password);
      }
    }
    return true;
}

function OnPreferencePageInitalize(prefset) {
    data.servers = getServerListFromPreference(prefset);
    data.original = getServerListFromPreference(prefset);
}

function OnPreferencePageLoading(prefset) {
    document.getElementById("buttonDelete").setAttribute('disabled', 'true');
    document.getElementById("buttonAdd").setAttribute('disabled', 'true');
    servers = data.servers;
    // fill out the associations tree - should cache this entire tree.
    _setMenuList(null);
}


function _strcmp(a,b) {
    if (a==b) return 0;
    if (a<b) return -1;
    return 1;
}
// Return an array of Association objects, built from the fileAssociations
// preference.
function getServerListFromPreference(prefset) {
  try {
  var list = new Array();
  var passwordmanager = Components.classes["@mozilla.org/passwordmanager;1"].getService(Components.interfaces.nsIPasswordManager);
  var e = passwordmanager.enumerator;
  while (e.hasMoreElements()) {
      //dump("dumping password manager data...\n");
      // server is nsIPassword, which has host, user and password members
      var nspassword = e.getNext().QueryInterface(Components.interfaces.nsIPassword);
      //dump("    "+nspassword.host+", ["+nspassword.user+", "+nspassword.password+"]\n");
      var server_info = new String(nspassword.host).split(":")
      list.push(new Server(server_info[0], server_info[1],
              server_info[2], server_info[3], server_info[4],
              new String(nspassword.user), new String(nspassword.password)));
  }
  } catch(e) {
      log.exception(e);
  }
  list.sort(function (a,b) { return _strcmp(a.alias,b.alias); });
  return list;
}

// Return true if the arrays of Association objects, a and b, correspond to
// the same underlying representation as a preference.
function areServerListsEquivalent(a, b) {
  if (a.length != b.length) return false;

  for (var i = 0; i < a.length; i++) {
    // we don't care about the IDs
    if (a[i].type != b[i].type ||
        a[i].alias != b[i].alias ||
        a[i].hostname != b[i].hostname ||
        a[i].port != b[i].port ||
        a[i].path != b[i].path ||
        a[i].username != b[i].username ||
        a[i].password != b[i].password) {
      return false;
    }
  }

  return true;
}

function _setMenuList(selectedServer) {
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
        if (servers[i].alias == selectedServer)
            indexSelect = i;
    }
    if (servers.length > 0)  {
        if (indexSelect == -1)
            indexSelect = 0;
        menulist.selectedIndex = indexSelect;
        onEditServerEntry(servers[indexSelect].id, null, menulist.selectedItem);
    }
}

function checkAddButtonStatus() {
    var alias = dialog.alias.value;
    var hostname = dialog.hostname.value;
    if (alias && hostname) {
        // enable add button
        document.getElementById("buttonAdd").removeAttribute('disabled');
    } else {
        // dissable add button
        document.getElementById("buttonAdd").setAttribute('disabled', 'true');
    }
}

var current_server_idx = -1;
var current_server_cell = null;
function onAddServerEntry() {
    var type = dialog.server_types.selectedItem.getAttribute("label");
    var alias = dialog.alias.value;
    var hostname = dialog.hostname.value;
    var port = dialog.port.value;
    var path = dialog.path.value;
    var username = dialog.username.value;
    var password = dialog.password.value;
    // prevent adding empty entries
    if (!alias || !hostname || !username) {
        prefServersLog.warn("Missing a required field. Name, Host Name and User Name are required fields.");
        return;
    }
    // Ensure that no ":" chars are used in any of the fields. ":" is used
    // uncarefully as a delimiter in the server saving code.
    var fieldWithColon = null;
    if (alias.indexOf(":") != -1) {
        fieldWithColon = "alias";
    } else if (hostname.indexOf(":") != -1) {
        fieldWithColon = "hostname";
    } else if (port.indexOf(":") != -1) {
        fieldWithColon = "port";
    } else if (path.indexOf(":") != -1) {
        fieldWithColon = "path";
    } else if (username.indexOf(":") != -1) {
        fieldWithColon = "username";
    }
    if (fieldWithColon) {
        alert("The " + fieldWithColon +
              " field cannot contain a ':' character");
        var textbox = document.getElementById(fieldWithColon);
        textbox.focus();
        textbox.setSelectionRange(0, textbox.value.length);
        return;
    }
    if (((type == "SFTP" || type == "SCP") && parseInt(port) == 21) ||
        (type == "FTP" && parseInt(port) == 22)) {
        var message = "You may have specified the wrong port. " +
                      "FTP uses port 21 by default. " +
                      "SFTP and SCP use port 22 by default. " +
                      "Do you wish to keep this setting?";
        if (ko.dialogs.yesNo(message,
                             "No" /* response */,
                             null /* text */,
                             "WARNING: Incorrect port?" /* title */) == "No") {
            return;
        }
    }

    var server;

    if (current_server_idx > -1) {
        server = servers[current_server_idx];
        server.type = type;
        server.alias = alias;
        server.hostname = hostname;
        server.port = port;
        server.path = path
        server.username = username;
        server.password = password;
        servers[current_server_idx] = server;
        current_server_cell.setAttribute('label', server.alias);
        document.getElementById("serversList").setAttribute('label', server.alias);
    } else {
        if (getAliasIndex(alias) > -1) {
            alert("The entry name is not unique, please correct this.\n");
            return;
        }
        server = new Server(type, alias, hostname, port, path, username, password);
        servers.push(server);
        servers.sort(function (a,b) { return _strcmp(a.alias,b.alias); } );
        _setMenuList(server.alias);
    }
    setMenuSelection("serversList",server.alias);
    dialog.buttonAdd.setAttribute('disabled', 'true');
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

function onEditServerEntry(id, item, event) {
    var server_idx = getIdIndex(id);
    if (server_idx < 0) return;
    var server = servers[server_idx];
    setMenuSelection("server_types",server.type);
    dialog.alias.value = server.alias;
    dialog.hostname.value = server.hostname;
    dialog.port.value = server.port;
    dialog.path.value = server.path;
    dialog.username.value = server.username;

    dialog.password.value = server.password;

    current_server_idx = server_idx;
    if (item != null)
        current_server_cell = event.target;
    else
        current_server_cell = event;
    dialog.buttonDelete.removeAttribute('disabled');
    dialog.buttonAdd.setAttribute('disabled','true');
    dialog.buttonAdd.setAttribute('label', 'Update');
    if (dialog.username.value == 'anonymous')
        dialog.anonymousCheckbox.checked = true;
    else
        dialog.anonymousCheckbox.checked = false;
}

function onDeleteServerEntry() {
    if (current_server_idx > -1) {
        servers.splice(current_server_idx, 1);
        dialog.serversPopup.removeChild(current_server_cell);
        onClearServerEntry();
        if (servers.length > 0) {
            var menulist = document.getElementById("serversList");
            menulist.selectedIndex = 0;
            onEditServerEntry(servers[0].id, null, menulist.selectedItem);
        }
    }
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
    current_server_idx = -1;
    current_server_cell = null;
    dialog.buttonDelete.setAttribute('disabled', 'true');
    dialog.buttonAdd.setAttribute('disabled', 'true');
    dialog.buttonAdd.setAttribute('label', 'Add');
    dialog.anonymousCheckbox.checked = false;
}

// DOM construction helpers

function createServersMenuItem(server) {
    var cell = document.createElementNS(XUL_NS, 'menuitem');
    cell.setAttribute('id', server.id);
    cell.setAttribute('label', server.alias);
    cell.setAttribute('assocId', server.id);
    cell.setAttribute("onclick", "onEditServerEntry('"+server.id+"',this, event)");
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
