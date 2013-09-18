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
        ko.main.addWillCloseHandler(this.finalize, this);

        this.name = 'peMenu';
        this.log = ko.logging.getLogger('peMenu');
        var obsSvc = Components.classes["@mozilla.org/observer-service;1"].
                           getService(Components.interfaces.nsIObserverService);
        this.observables = {
            'menu_create': true,
            'menu_changed': true,
            'menu_remove': false,
            'toolbar_create': true,
            'toolbar_remove': false,
            'toolbar_changed': true,
            'part_changed': true,
            'toolbox-loaded': true,
            'toolbox-loaded-local': true,
            'toolbox-loaded-global': true,
            'toolbox-unloaded': false,
            'toolbox-unloaded-local': false,
            'toolbox-unloaded-global': false};
        for (var name in this.observables) {
            obsSvc.addObserver(this, name, false);
        }
    } catch (e) {
        this.log.exception(e);
    }
}

peMenu.prototype.finalize = function() {
    var obsSvc = Components.classes["@mozilla.org/observer-service;1"].
                       getService(Components.interfaces.nsIObserverService);
    for (var name in this.observables) {
        obsSvc.removeObserver(this, name);
    }
}

peMenu.prototype.observe = function(part, topic, data)
{
    // Notifications can be deferred if they're waiting for
    // an addition  or change to the database.  Others need
    // to fire before a deletion occurs, so we do them right away.
    if (!this.observables[topic]) {
        this.observe_aux(part, topic, data);
    } else {
        setTimeout(function(this_) {
                this_.observe_aux(part, topic, data);
            }, 300, this);
    }
}

peMenu.prototype.observe_aux = function(part, topic, data)
{
    try {
        //dump("peMenu observer "+part+", "+topic+", "+data+"\n");
        var menu, id;
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
                ko.projects.removeMenuForPart(part);
                break;
            case 'part_changed':
                try {
                    id = ko.projects.customIdFromPart(part);
                    var xulelt = document.getElementById(id);
                    if (xulelt) {
                        xulelt.setAttribute('image', part.iconurl)
                        xulelt.setAttribute('label', part.name)
                    }
                } catch (e) {
                    this.log.exception(e);
                }
                break;
            case 'menu_changed':
                try {
                    // First get rid of the old menu
                    id = ko.projects.customIdFromPart(part);
                    menu = document.getElementById(id);
                    if (!menu) {
                        break;
                    }
                    menu.parentNode.removeChild(menu);
                    ko.projects.addMenuFromPart(part);
                } catch (e) {
                    this.log.exception(e);
                }
                break;
            case 'menu_create':
                ko.projects.addMenuFromPart(part);
                break;
            case 'toolbox-loaded':
            case 'toolbox-loaded-local':
            case 'toolbox-loaded-global':
                if (topic != 'toolbox-loaded-global'
                    && ko.windowManager.getMainWindow() != window) {
                    return;
                }
                ko.projects.onToolboxLoaded(data);
                break;
            case 'toolbox-unloaded':
            case 'toolbox-unloaded-local':
            case 'toolbox-unloaded-global':
                if (topic != 'toolbox-unloaded-global'
                    && ko.windowManager.getMainWindow() != window) {
                    return;
                }
                // Called when we're about to remove commands.
                ko.projects.onToolboxUnloaded(data);
                break;
        }
    } catch (e) {
        this.log.exception(e);
    }
};

// Probably no need to hold onto a reference.  v5 code didn't.
ko.projects.peMenu = new peMenu();
})();

(function() { // ko.projects

var prefSvc = Components.classes['@activestate.com/koPrefService;1'].
                getService(Components.interfaces.koIPrefService);
var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
      .getService(Components.interfaces.nsIStringBundleService)
      .createBundle("chrome://komodo/locale/project/peMenu.properties");
var log = ko.logging.getLogger('peMenu');

/**
 * Return a custom id that can be used for the part's menu or toolbar element.
 * 
 * @param   {Components.interfaces.koIPart} part  The toolbox part.
 * @returns {String} The id for a DOM element.
 */
this.customIdFromPart = function _IDFromPart(part) {
    return "ko_custom_" + part.type + "_" + part.id;
};

this.partAcceptsMenuToolbar = function peMenu_partAcceptsMenuToolbar(part) {
    // Used to check early whether a part can be added
    while (part) {
        if (part.type == 'menu') return false;
        if (part.type == 'toolbar') return false;
        part = part.parent;
    }
    return true;
}

this.addMenu = function peMenu_addMenu(/*koITool*/ parent, /*koITool*/ menu) {
    // Ensure that the item being added to isn't a menu/toolbar or a
    // child of a menu/toolbar
    if (parent && ! ko.projects.partAcceptsMenuToolbar(parent)) {
        ko.dialogs.alert(_bundle.GetStringFromName("cannotAddMenusToMenus"));
        return;
    }
    var name = ko.dialogs.prompt(_bundle.GetStringFromName("enterMenuName"));
    if (!name) return;
    menu.name = name;
    ko.toolbox2.addItem(menu, parent);
    ko.projects.addMenuFromPart(menu);
}

this.addMenuFromPart = function peMenu_addMenuFromPart(part) {
    try {
        var base_ordinal = 100;

        var name = part.name;
        var id = ko.projects.customIdFromPart(part);
        var menubar = document.getElementById('menubar_main');
        if (menubar.getElementsByAttribute('id', id).length >= 1) {
            // Multi-window filter.
            //dump("peMenu.js -- already have menu item "
            //     + part.name
            //     + " in this menu, rejecting the new one\n");
            return;
        }
        var menu = document.createElement('menu');
        menu.setAttribute('label', name);
        var accesskey = part.getStringAttribute('accesskey');
        if (accesskey) {
            menu.setAttribute('accesskey', accesskey);
        }
        menu.setAttribute('id', id);
        var menupopup = document.createElement('menupopup');
        menu.appendChild(menupopup);
        menu.ordinal = base_ordinal + part.getLongAttribute('priority');
        menubar.appendChild(menu);

        _fillMenupopupFromPart(menupopup, part);
    } catch (e) {
        log.exception(e);
    }
}

this.removeMenuForPart = function peMenu_removeMenuForPart(part) {
    try {
        // First get rid of the old menu
        var id = ko.projects.customIdFromPart(part);
        var menu = document.getElementById(id);
        if (!menu) {
            log.warn("removeMenuForPart: can't find menu with id: " + id);
            return;
        }
        menu.parentNode.removeChild(menu);
    } catch (e) {
        log.exception(e);
    }
}

this.removeToolbarForPart = function peMenu_removeToolbarForPart(part) {
    try {
        // First get rid of the old menu
        var id = ko.projects.customIdFromPart(part);
        var toolbar = document.getElementById(id);
        if (!toolbar) {
            log.error("Couldn't find toolbar with id: '" + id + "'");
            return;
        }
        toolbar.parentNode.removeChild(toolbar)

        var menuitem = document.getElementById('menu_custom_toolbar_'+id)
        menuitem.parentNode.removeChild(menuitem);

        var broadcaster = document.getElementById('cmd_custom_toolbar_'+id)
        broadcaster.parentNode.removeChild(broadcaster);

        var separator = document.getElementById("popup_toolbars_custom_separator");
        var next = separator.nextSibling;
        if (!next || !/^menu_custom_toolbar_/.test(next.id)) {
            // nothing after the separator, or the thing after it is not a
            // menu for a custom toolbar
            separator.collapsed = true;
        }

    } catch(e) {
        log.exception(e);
    }
}

this.addToolbarFromPart = function peMenu_addToolbarFromPart(part) {
    try {
        // uncollapse the seperator if necessary
        var menu = document.getElementById("popup_toolbars");
        var separator = document.getElementById("popup_toolbars_custom_separator");
        separator.collapsed = false;

        // minimal display ordinal an element will have
        var base_ordinal = 100;
        var id = ko.projects.customIdFromPart(part);
        var cmd_id = 'cmd_custom_toolbar_'+id;
        var visible = ! ko.projects.isToolbarRememberedAsHidden(id);

        var toolbox = document.getElementById('main-toolboxrow');
        if (toolbox.getElementsByAttribute('id', id).length >= 1) {
            // dump("peMenu.js -- Already have toolbox " + part.name + "\n");
            return;
        }
        
        var toolbar = document.createElement('toolbar');
        toolbar.setAttribute('id', id);
        toolbar.setAttribute('class', "chromeclass-toolbar custom-toolbar");
        
        if (ko.prefs.getBoolean('custom_toolbar_svg_filters', false))
        {
            toolbar.classList.add("enable-svg-filters");
        }
        
        // We need the last custom toolbox to have a flex of one
        toolbar.setAttribute('buttonstyle', "pictures");
        toolbar.setAttribute('grippyhidden', "true");
        toolbar.setAttribute('customizable', "true");
        toolbar.setAttribute('toolboxid', "toolbox_main");
        toolbar.setAttribute('tooltiptext', part.name);
        toolbar.setAttribute('broadcaster', cmd_id);
        if (! visible) {
            toolbar.setAttribute('kohidden', 'true');
        }
        toolbar.setAttribute('mode', toolbox.getAttribute('mode'));
        var ordinal = base_ordinal + part.getLongAttribute('priority');
        toolbar.ordinal = ordinal;
        
        // Append toolbaritem wrapper to which all children are appended
        // The toolbaritem wrapper is used primarily for styling
        var toolbaritem = document.createElement('toolbaritem');
        toolbar.appendChild(toolbaritem);

        toolbox.appendChild(toolbar);

        _fillToolbarFromPart(toolbar, part);

        // append the toolboar to the view->toolbar menu
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
        broadcaster.setAttribute('oncommand', 'ko.uilayout.toggleToolbarVisibility("'+id+'"); ko.projects.toggleToolbarHiddenStateInPref("' + id + '")');
        broadcasterset.appendChild(broadcaster);


        //<menuitem label="Standard"
        //          id="menu_viewedittoolbar"
        //          observes="cmd_viewedittoolbar"
        //          persist="checked"
        //          checked="true"
        //          type="checkbox"
        //          />
        var menuitem = document.createElement('menuitem');
        menuitem.setAttribute('id', 'menu_custom_toolbar_'+id);
        menuitem.setAttribute('label', part.name);
        menuitem.setAttribute('type', 'checkbox');
        menuitem.setAttribute('persist', 'checkbox');
        if (visible) {
            menuitem.setAttribute('checked', 'true');
        }
        menuitem.setAttribute('observes', cmd_id);
        menuitem.ordinal = ordinal;
        menu.insertBefore(menuitem, separator.nextSibling);
        
        ko.uilayout._updateToolbarViewStates();

    } catch (e) {
        log.exception(e);
    }
}

this.onToolboxLoaded = function(toolboxDir) {
    var this_ = this;
    var tools;
// #if PLATFORM != "darwin"
    // See bug 80697
    tools = ko.toolbox2.getCustomMenus(toolboxDir);
    tools.map(function(part) {
            this_.addMenuFromPart(part);
        });
// #endif
    tools = ko.toolbox2.getCustomToolbars(toolboxDir);
    tools.map(function(part) {
            this_.addToolbarFromPart(part);
        });
    // Bug 100445: update any views on custom toolbars
    ko.uilayout.updateToolbarArrangement();
}

this.onToolboxUnloaded = function(toolboxDir) {
    var this_ = this;
    var tools = ko.toolbox2.getCustomMenus(toolboxDir);
    tools.map(function(part) {
            this_.removeMenuForPart(part);
        });
    tools = ko.toolbox2.getCustomToolbars(toolboxDir);
    tools.map(function(part) {
            this_.removeToolbarForPart(part);
        });
}

this.updateToolbarForPart = function(part) {
    // First get rid of the old menu
    var toolbar = document.getElementById(ko.projects.customIdFromPart(part));
    if (!toolbar) {
        return;
    }
    // remove the children
    while (toolbar.firstChild.lastChild) { // First child is always toolbaritem wrapper
        toolbar.firstChild.removeChild(toolbar.firstChild.lastChild);
    }
    _fillToolbarFromPart(toolbar, part);
}

this.isToolbarRememberedAsHidden = function peMenu_isToolbarRememberedAsHidden(id) {
        try {
        var prefs = prefSvc.prefs
        var hidden_toolbar_ids = prefs.getString('hidden_toolbars', '');
        if (!hidden_toolbar_ids) {
            return false;
        }
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
        var hidden_toolbar_ids = prefs.getString('hidden_toolbars', '');
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

this.addToolbar = function peMenu_addToolbar(/*koITool*/ parent, /*koITool*/ toolbar) {
    // Ensure that the item being added to isn't a menu/toolbar or a
    // child of a menu/toolbar
    if (parent && ! ko.projects.partAcceptsMenuToolbar(parent)) {
        ko.dialogs.alert(_bundle.GetStringFromName("cannotAddToolbarsToMenus"));
        return;
    }
    var name = ko.dialogs.prompt(_bundle.GetStringFromName("enterToolbarName"));
    if (!name) return;
    toolbar.name = name;
    ko.toolbox2.addItem(toolbar, parent);
    ko.projects.addToolbarFromPart(toolbar);
}


function _createToolbaritemFromPart(toolbar, part)
{
  try {
    var button, name;
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
            var idPart = 
            button.setAttribute('oncommand',
                                "ko.projects.invokePartById('" + part.id + "');");
            break;
        }
    button.setAttribute('image', part.iconurl);
    button.setAttribute('tooltiptext', name);
    button.setAttribute('tooltip', 'aTooltip');
    button.setAttribute('label', name);
    button.setAttribute('id', ko.projects.customIdFromPart(part));
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
            menuitem.setAttribute('class', 'menuitem-iconic');
            menuitem.setAttribute('oncommand', "ko.projects.invokePartById('" + part.id + "');");
            break;
        }
    menuitem.setAttribute('id', ko.projects.customIdFromPart(part));
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
        toolbar.firstChild.appendChild(button);
    }

    var toolboxRow = document.getElementById("main-toolboxrow");
    if (toolboxRow) {
        toolboxRow.dirty = true;
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

this.menuProperties = function peMenu_editProperties(item) {
    var obj = new Object();
    obj.item = item;
    obj.task = 'edit';
    obj.imgsrc = 'chrome://komodo/skin/images/open.png';
    if (item.type == 'menu') {
        obj.type = 'menu';
        obj.prettytype = _bundle.GetStringFromName("customMenu");
    } else {
        obj.type = 'toolbar';
        obj.prettytype = _bundle.GetStringFromName("customToolbar");
    }
    window.openDialog(
        "chrome://komodo/content/project/customMenuProperties.xul",
        "Komodo:CustomMenuProperties",
        "chrome,close=yes,dependent=yes,modal=yes,resizable=yes", obj);
}

}).apply(ko.projects);
