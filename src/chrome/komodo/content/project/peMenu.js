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

// start the extension


if (typeof(ko)=='undefined') {
    var ko = {};
}
if (typeof(ko.projects)=='undefined') {
    ko.projects = {};
}

(function() {

function peMenu() {
    try {
        this.name = 'peMenu';
        this.log = ko.logging.getLogger('peMenu');
        var obsSvc = Components.classes["@mozilla.org/observer-service;1"].
                           getService(Components.interfaces.nsIObserverService);
        obsSvc.addObserver(this, 'menu_create', false);
        obsSvc.addObserver(this, 'menu_changed', false);
        obsSvc.addObserver(this, 'menu_remove', false);
        obsSvc.addObserver(this, 'toolbar_create', false);
        obsSvc.addObserver(this, 'toolbar_remove', false);
        obsSvc.addObserver(this, 'toolbar_changed', false);
        obsSvc.addObserver(this, 'part_changed', false);
    } catch (e) {
        this.log.exception(e);
    }
}

// The following two lines ensure proper inheritance (see Flanagan, p. 144).
peMenu.prototype.constructor = peMenu;

peMenu.prototype.init = function() {
}

peMenu.prototype.registerCommands = function() {
}

peMenu.prototype.registerEventHandlers = function() {
    try {
        ko.projects.extensionManager.registerCommand('cmd_viewCustomToolbar', this);
    } catch (e) {
        this.log.exception(e);
    }
}

peMenu.prototype.registerMenus = function() {
    var menupopup = document.getElementById('folder_context');
    ko.projects.extensionManager.addMenuItem(Components.interfaces.koIPart_menu, menupopup);
    ko.projects.extensionManager.addMenuItem(Components.interfaces.koIPart_toolbar, menupopup);
}

peMenu.prototype.ondblclick = function(part,event) {
}

peMenu.prototype.supportsCommand = function(command, part) {
    if (command == 'cmd_viewCustomToolbar') return true;
    return false;
}

peMenu.prototype.isCommandEnabled = peMenu.prototype.supportsCommand;

peMenu.prototype.doCommand = function(command) {
    if (command == 'cmd_viewCustomToolbar') {
        // which toolbar is being changed?
        //ko.uilayout.toggleToolbarVisibility('standardToolbar');
    }
}

peMenu.prototype.observe = function(part, topic, dummy)
{
    try {
        //dump("peMenu observer "+part+", "+topic+", "+dummy+"\n");
        var menu;
        switch (topic) {
            case 'toolbar_remove':
                ko.projects.removeToolbarForPart(part);
                break;
            case 'toolbar_changed':
                ko.projects.updateToolbarForPart(part);
                break;
            case 'toolbar_create':
                ko.projects.addToolbarFromPart(part);
                break;
            case 'menu_remove':
                try {
                    // First get rid of the old menu
                    menu = document.getElementById(part.id);
                    if (!menu) {
                        log.warning("Couldn't delete menu with id: " + part.id);
                        break;
                    }
                    menu.parentNode.removeChild(menu);
                } catch (e) {
                    log.exception(e);
                }
                break;
            case 'part_changed':
                try {
                    var xulelt = document.getElementById(part.id);
                    if (xulelt) {
                        xulelt.setAttribute('image', part.iconurl)
                        xulelt.setAttribute('label', part.name)
                    }
                } catch (e) {
                    log.exception(e);
                }
                break;
            case 'menu_changed':
                try {
                    // First get rid of the old menu
                    menu = document.getElementById(part.id);
                    if (!menu) {
                        break;
                    }
                    menu.parentNode.removeChild(menu);
                    ko.projects.addMenuFromPart(part);
                } catch (e) {
                    log.exception(e);
                }
                break;
            case 'menu_create':
                ko.projects.addMenuFromPart(part);
                break;
        }
    } catch (e) {
        log.exception(e);
    }
};

// this is hidden away now, no namespce, the registration keeps the reference
// we need
ko.projects.registerExtension(new peMenu());
}).apply();



(function() { // ko.projects
var prefSvc = Components.classes['@activestate.com/koPrefService;1'].
                getService(Components.interfaces.koIPrefService);


this.partAcceptsMenuToolbar = function peMenu_partAcceptsMenuToolbar(part) {
    // Used to check early whether a part can be added
    while (part && part.type != 'project') {
        if (part.type == 'menu') return false;
        if (part.type == 'toolbar') return false;
        part = part.parent;
    }
    return true;
}

this.addMenu = function peMenu_addMenu(/*koIPart*/ parent) {
    // Ensure that the item being added to isn't a menu/toolbar or a
    // child of a menu/toolbar
    if (parent && ! ko.projects.partAcceptsMenuToolbar(parent)) {
        ko.dialogs.alert("Sorry, you can't add menus to menus, toolbars or children "+
                     "of menus or toolbars. If you want to add a sub-menu "+
                     "add a Folder item.");
        return;
    }
    var name = ko.dialogs.prompt("Enter menu name:");
    if (!name) return;
    var menu = parent.project.createPartFromType('menu');
    menu.name = name;
    ko.projects.addItem(menu,parent);
}

this.addMenuFromPart = function peMenu_addMenuFromPart(part) {
    try {
        var base_ordinal = 100;

        var name = part.name;
        var menubar = document.getElementById('menubar_main')
        var menu = document.createElement('menu');
        menu.setAttribute('label', name);
        var accesskey = part.getStringAttribute('accesskey');
        if (accesskey) {
            menu.setAttribute('accesskey', accesskey);
        }
        menu.setAttribute('id', part.id);
        var menupopup = document.createElement('menupopup');
        menu.appendChild(menupopup);
        menu.ordinal = base_ordinal + part.getLongAttribute('priority');
        menubar.appendChild(menu);

        _fillMenupopupFromPart(menupopup, part);
    } catch (e) {
        log.exception(e);
    }
}

this.removeToolbarForPart = function peMenu_removeToolbarForPart(part) {
    try {
        // First get rid of the old menu
        var toolbar = document.getElementById(part.id);
        if (!toolbar) {
            log.error("Couldn't find toolbar with id: '" + part.id + "'");
            return;
        }
        toolbar.parentNode.removeChild(toolbar)

        var menuitem = document.getElementById('context_custom_toolbar_'+part.id)
        menuitem.parentNode.removeChild(menuitem);

        menuitem = document.getElementById('menu_custom_toolbar_'+part.id)
        menuitem.parentNode.removeChild(menuitem);

        var broadcaster = document.getElementById('cmd_custom_toolbar_'+part.id)
        broadcaster.parentNode.removeChild(broadcaster);

        var context = document.getElementById("context-toolbox-menu");
        var menu = document.getElementById("popup_toolbars");
        if (context.lastChild.nodeName == 'menuseparator') {
            context.lastChild.setAttribute('collapsed', 'true');
            menu.lastChild.setAttribute('collapsed', 'true');
        }

    } catch(e) {
        log.exception(e);
    }
}

this.addToolbarFromPart = function peMenu_addToolbarFromPart(part) {
    try {
        // uncollapse the seperator if necessary
        var context = document.getElementById("context-toolbox-menu");
        var menu = document.getElementById("popup_toolbars");
        if (context.lastChild.nodeName == 'menuseparator') {
            context.lastChild.removeAttribute('collapsed');
            menu.lastChild.removeAttribute('collapsed');
        }

        // minimal display ordinal an element will have
        var base_ordinal = 100;
        var cmd_id = 'cmd_custom_toolbar_'+part.id;
        var visible = ! ko.projects.isToolbarRememberedAsHidden(part.id);

        var toolbox = document.getElementById('toolbox_main');
        var toolbar = document.createElement('toolbar');
        toolbar.setAttribute('id', part.id);
        toolbar.setAttribute('class', "chromeclass-toolbar");
        // We need the last custom toolbox to have a flex of one
        toolbar.setAttribute('buttonstyle', "pictures");
        toolbar.setAttribute('grippyhidden', "true");
        toolbar.setAttribute('broadcaster', cmd_id);
        if (! visible) {
            toolbar.setAttribute('hidden', 'true');
        }
        var ordinal = base_ordinal + part.getLongAttribute('priority');
        toolbar.ordinal = ordinal;

        toolbox.appendToolbar(toolbar);

        _fillToolbarFromPart(toolbar, part);

        // append the toolboar to the toolbar context and view->toolbar menues
        var broadcasterset = document.getElementById("broadcasterset_global");
        var broadcaster = document.createElement("broadcaster");
        //<broadcaster
        //    id="cmd_viewedittoolbar"
        //    autoCheck="false"
        //    checked="true"
        //    persist="checked"
        //    oncommand="ko.uilayout.toggleToolbarVisibility('standardToolbar')"/>
        broadcaster.setAttribute('id', cmd_id);
        broadcaster.setAttribute('autoCheck', 'false');
        broadcaster.setAttribute('persist', 'checked');
        if (visible) {
            broadcaster.setAttribute('checked', 'true');
        } else {
            broadcaster.setAttribute('checked', 'false');
        }
        broadcaster.setAttribute('oncommand', 'ko.uilayout.toggleToolbarVisibility("'+part.id+'"); ko.projects.toggleToolbarHiddenStateInPref("' + part.id + '")');
        broadcasterset.appendChild(broadcaster);


        var menuitem = document.createElement('menuitem');
        //<menuitem id="context_viewStandardToolbar"
        //          label="Standard Toolbar"
        //          type="checkbox"
        //          observes="cmd_viewedittoolbar"
        //          key="key_viewToolbarEdit"/>
        menuitem.setAttribute('id', 'context_custom_toolbar_'+part.id);
        menuitem.setAttribute('label', part.name);
        menuitem.setAttribute('type', 'checkbox');
        if (visible) {
            menuitem.setAttribute('checked', 'true');
        } else {
            menuitem.setAttribute('checked', 'false');
        }
        menuitem.setAttribute('observes', cmd_id);
        //menuitem.setAttribute('oncommand', 'ko.uilayout.toggleToolbarVisibility("'+part.id+'");');
        menuitem.ordinal = ordinal;
        context.appendChild(menuitem);

        //<menuitem label="Standard"
        //          id="menu_viewedittoolbar"
        //          observes="cmd_viewedittoolbar"
        //          persist="checked"
        //          checked="true"
        //          type="checkbox"
        //          />
        menuitem = document.createElement('menuitem');
        menuitem.setAttribute('id', 'menu_custom_toolbar_'+part.id);
        menuitem.setAttribute('label', part.name);
        menuitem.setAttribute('type', 'checkbox');
        menuitem.setAttribute('persist', 'checkbox');
        if (visible) {
            menuitem.setAttribute('checked', 'true');
        } else {
            menuitem.setAttribute('checked', 'false');
        }
        menuitem.setAttribute('observes', cmd_id);
        //menuitem.setAttribute('oncommand', 'ko.uilayout.toggleToolbarVisibility("'+part.id+'");');
        menuitem.ordinal = ordinal;
        menu.appendChild(menuitem);


    } catch (e) {
        log.exception(e);
    }
}

this.updateToolbarForPart = function(part) {
    // First get rid of the old menu
    var toolbar = document.getElementById(part.id);
    if (!toolbar) {
        return;
    }
    // remove the children
    while (toolbar.lastChild) {
        toolbar.removeChild(toolbar.lastChild);
    }
    _fillToolbarFromPart(toolbar, part);
}

this.isToolbarRememberedAsHidden = function peMenu_isToolbarRememberedAsHidden(id) {
        try {
        var prefs = prefSvc.prefs
        if (!prefs.hasStringPref('hidden_toolbars')) {
            return false;
        }
        var hidden_toolbar_ids = prefs.getStringPref('hidden_toolbars')
        var ids = hidden_toolbar_ids.split(',');
        var found = false;
        for (var i = 0; i < ids.length; i++) {
            if (ids[i] == id) {
                return true;
            }
        }
    } catch (e) {
        log.exception(e);
    }
    return false;
}
this.toggleToolbarHiddenStateInPref = function peMenu_toggleToolbarHiddenStateInPref(id) {
    try {
        var prefs = prefSvc.prefs
        var hidden_toolbar_ids = '';
        if (prefs.hasStringPref('hidden_toolbars')) {
            hidden_toolbar_ids = prefs.getStringPref('hidden_toolbars')
        }
        var ids = hidden_toolbar_ids.split(',');
        var found = false;
        for (var i = 0; i < ids.length; i++) {
            if (ids[i] == id) {
                // take it out
                ids.splice(i,1);
                found = true;
                break;
            }
        }
        if (!found) { // must add it instead
            ids.push(id);
        }
        hidden_toolbar_ids = ids.join(',');
        prefs.setStringPref('hidden_toolbars', hidden_toolbar_ids)
    } catch (e) {
        log.exception(e);
    }
}

this.addToolbar = function peMenu_addToolbar(/*koIPart*/ parent)
{
    // Ensure that the item being added to isn't a menu/toolbar or a
    // child of a menu/toolbar
    if (parent && ! ko.projects.partAcceptsMenuToolbar(parent)) {
        ko.dialogs.alert("Sorry, you can't add toolbars to menus, toolbars or children of menus or toolbars.");
        return;
    }
    var name = ko.dialogs.prompt("Enter toolbar name:");
    if (!name) return;
    var toolbar = parent.project.createPartFromType('toolbar');
    toolbar.name = name;
    ko.projects.addItem(toolbar,parent);
}


function _createToolbaritemFromPart(toolbar, part)
{
  try {
    var button, name, id;
    button = document.createElement('toolbarbutton');
    if (!ko.uilayout.isButtonTextShowing()) {
        button.setAttribute('buttonstyle', 'pictures');
    }

    name = part.name;
    switch (part.type) {
        case 'ProjectRef':
            // same as file
        case 'file':
            var url = part.getStringAttribute('url');
            button.setAttribute('oncommand', "try { ko.open.URI('" + url + "') } catch (e) { log.exception(e); };");
            break;
        case 'folder':
            button.setAttribute('type', 'menu');
            button.setAttribute('class', 'rightarrow-button-a');
            button.setAttribute('orient', 'horizontal');
            var menupopup = document.createElement('menupopup');
            button.appendChild(menupopup);
            var i, childitem;
            var children = new Array();
            part.getChildren(children, new Object());
            children = children.value;
            children.sort(_sortItems);
            for (i = 0; i < children.length; i++) {
                childitem = _createMenuItemFromPart(menupopup,children[i]);
                menupopup.appendChild(childitem);
            }
            break;
        default:
            button.setAttribute('oncommand', "ko.projects.invokePartById('" + part.id + "');");
            break;
        }
    button.setAttribute('image', part.iconurl);
    button.setAttribute('tooltiptext', name);
    button.setAttribute('tooltip', 'aTooltip');
    button.setAttribute('label', name);
    button.setAttribute('id', part.id);
    return button;
  } catch (e) {
    log.exception(e);
  }
  return null;
}

function _createMenuItemFromPart(menupopup, part)
{
    var menuitem, name;
    switch (part.type) {
        case 'ProjectRef':
            // same as file
        case 'file':
            var url = part.getStringAttribute('url');
            name = part.name;
            menuitem = document.createElement('menuitem');
            menuitem.setAttribute('class', 'menuitem-iconic-wide');
            menuitem.setAttribute('oncommand', "try { ko.open.URI('" + url + "') } catch (e) { log.exception(e); };");
            break;
        case 'folder':
            name = part.name;
            menuitem = document.createElement('menu');
            menuitem.setAttribute('class', 'menu-iconic');
            menupopup = document.createElement('menupopup');
            menuitem.appendChild(menupopup);
            var i, childitem;
            var children = new Array();
            part.getChildren(children, new Object());
            children = children.value;
            children.sort(_sortItems);
            for (i = 0; i < children.length; i++) {
                childitem = _createMenuItemFromPart(menupopup,children[i]);
                menupopup.appendChild(childitem);
            }
            break;
        default:
            name = part.name;
            menuitem = document.createElement('menuitem');
            menuitem.setAttribute('class', 'menuitem-iconic-wide');
            menuitem.setAttribute('oncommand', "ko.projects.invokePartById('" + part.id + "');");
            break;
        }
    menuitem.setAttribute('id', part.id);
    menuitem.setAttribute('image', part.iconurl);
    menuitem.setAttribute('label', name);
    if (part.hasAttribute('keyboard_shortcut')) {
        var shortcut = part.getStringAttribute('keyboard_shortcut');
        if (shortcut) {
            menuitem.setAttribute('acceltext', shortcut);
        }
    }
    return menuitem;
}

function _fillMenupopupFromPart(menupopup, part)
{
    var children = new Array();
    part.getChildren(children, new Object());
    children = children.value;
    children.sort(_sortItems);
    var i, child, menuitem;
    for (i = 0; i < children.length; i++) {
        child = children[i];
        menuitem = _createMenuItemFromPart(menupopup, child);
        menupopup.appendChild(menuitem);
    }
}

function _fillToolbarFromPart(toolbar, part)
{
    var children = new Array();
    part.getChildren(children, new Object());
    var button;
    children = children.value;
    children.sort(_sortItems);
    var i;
    for (i = 0; i < children.length; i++) {
        part = children[i];
        button = _createToolbaritemFromPart(toolbar, part);
        toolbar.appendChild(button);
    }
}

function _sortItems(a,b) {
    // sort folders first
    if (a.type == 'folder' && b.type !='folder')
        return -1;
    if (a.type != 'folder' && b.type =='folder')
        return 1;
    // sort other types alphabeticaly
    if (a.type != b.type) {
        if (a.type < b.type)
            return -1;
        else if (a.type > b.type)
            return 1;
    }
    if (a.hasAttribute('name') && b.hasAttribute('name')) {
        var aname = a.getStringAttribute('name').toLowerCase();
        var bname = b.getStringAttribute('name').toLowerCase();
        if (aname < bname )
            return -1;
        else if (aname > bname )
            return 1;
    }
    return 0;
}

this.menuProperties = function peMenu_editProperties(item, rank) {
    var obj = new Object();
    obj.item = item;
    obj.task = 'edit';
    obj.imgsrc = 'chrome://komodo/skin/images/open.png';
    if (item.type == 'menu') {
        obj.type = 'menu';
        obj.prettytype = 'Custom Menu';
    } else {
        obj.type = 'toolbar';
        obj.prettytype = 'Custom Toolbar';
    }
    window.openDialog(
        "chrome://komodo/content/project/customMenuProperties.xul",
        "Komodo:CustomMenuProperties",
        "chrome,close=yes,dependent=yes,modal=yes,resizable=yes", obj);
}

}).apply(ko.projects);

var peMenu_addMenu = ko.projects.addMenu;
var peMenu_addMenuFromPart = ko.projects.addMenuFromPart;
var peMenu_addToolbar = ko.projects.addToolbar;
var peMenu_addToolbarFromPart = ko.projects.addToolbarFromPart;
var peMenu_editProperties = ko.projects.menuProperties;
var peMenu_partAcceptsMenuToolbar = ko.projects.partAcceptsMenuToolbar;
var peMenu_removeToolbarForPart = ko.projects.removeToolbarForPart;
var peMenu_toggleToolbarHiddenStateInPref = ko.projects.toggleToolbarHiddenStateInPref;
