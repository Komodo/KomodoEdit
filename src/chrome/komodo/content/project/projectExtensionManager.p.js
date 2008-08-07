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

// Manage "project extensions" ('pe's for short).
//
//                  HOW TO WRITE A PROJECT EXTENSION
//
// A project extension is a singleton instance of a JS class. Currently (at
// least) pe's are defined in pe*.js files in the same directory as this file
// (e.g. the "command" pe is coded in "peCommand.js").
//
// A pe is registered and initialized as follows:
//  - The pe*.js file is included in komodo.xul like so:
//      <script type="application/x-javascript"
//              src="chrome://komodo/content/project/peCommand.js"/>
//  - Top level code in the pe*.js file adds a singleton instance of the class
//    to the global 'registeredExtensions' (defined here).
//      registeredExtensions[registeredExtensions.length] = new peCommand();
//  - The project extension manager's init() calls .init() on each registered
//    extension.
//
// A project extension's initialization can do the following:
//  - Register right-click context menu entries:
//      ko.projects.extensionManager.addCommandMenu(this,       // handler
//          Components.interfaces.koIPart_command,  // part-type interface
//          'Open Command',                         // text on right-click menu
//          'cmd_runCommand');      // command to run when selected
//  - Register self as a command handler for appropriate std commands:
//      ko.projects.extensionManager.registerCommand('cmd_cut', this);
//  - Register for the GUI events. E.g. 'ondblclick'. For each registered event
//    the pe must define a .<eventname>() method.
//
// If a project extension registers to handle any commands it must implement
// the usual command interface: .supportsCommand(), .isCommandEnabled() and
// .doCommand() methods.
//

if (typeof(ko)=='undefined') {
    var ko = {};
}
if (typeof(ko.projects)=='undefined') {
    ko.projects = {};
}

(function() {
const XUL_NS = "http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul";
var log = ko.logging.getLogger('ko.projects.extensionManager');

function projectExtensionManager() {
    ko.trace.get().enter('projectExtensionManager()');
    /* maps an interface string to an array of menuItem XUL elements */
    this.menus = {};
    /* when we store an interface into a map, javascript turns it into a string.
     * Since we need the actual interface value, we need an additional map to
     * map the interface string to the interface value. interfaceMap maps the
     * string to value. menus (above) maps the interface string to the
    */
    this.interfaceMap = {};
    /* maps an event to an extension, the extension must implement the even
     * handler */
    this.handlers = {};
    /* maps a command name to a function */
    this._commands = {};
    /* used to store regex matches on command names */
    this._commandsMatches = {};

    /* datapoints are elements that an extension might fill on in a wrapped part
     * a view can use this list to create new columns for the data this is a
     * PUBLIC property, but setting a value should use setDatapoint()
    */
    this.datapoints = {};

    /* the extension manager is the primary controller, and delegates to
     * extensions we use 'insertControllerAt(0,...' to be hit before the
     * scintilla cut/copy/paste controller */
    window.controllers.insertControllerAt(0, this);
    ko.main.addWillCloseHandler(function() {
        try {
            window.controllers.removeController(this);
        } catch(ex) {
            log.exception(ex);
        }
    }, this, 10);
    ko.trace.get().leave('projectExtensionManager()');
}

projectExtensionManager.prototype.constructor = projectExtensionManager;

projectExtensionManager.prototype.init = function() {
    ko.trace.get().enter('projectExtensionManager.init');
    var i, extension;
    for (i = 0; i < registeredExtensions.length; i++)
    {
        extension = registeredExtensions[i]
        this.registerExtension(extension);
    }
    ko.trace.get().leave('projectExtensionManager.init');
}

projectExtensionManager.prototype.registerExtension = function(extension) {
    try {
        log.info("initializing extension: " + extension.name)
        extension.init();
    } catch(e) { log.error("Error initializing " + extension.name + " " + e); }
    try {
        log.info("registering commands for: " + extension.name)
        extension.registerCommands();
    } catch(e) { log.error("Error registering commands for: " + extension.name + " " + e); }
    try {
        log.info("registering event handler for : " + extension.name)
        extension.registerEventHandlers();
    } catch(e) { log.error("Error registering event handlers for " + extension.name + " " + e); }
    try {
        log.info("registering menus for: " + extension.name)
        extension.registerMenus();
    } catch(e) { log.error("Error registering menus for " + extension.name + " " + e); }
}

projectExtensionManager.prototype.setDatapoint = function(columnname,fieldname) {
    this.datapoints[columnname] = fieldname;
}

/* handles everything necessary to add a menu item and command */
projectExtensionManager.prototype.addCommandMenu = function(handler,
                                                            partInterface,
                                                            label,
                                                            commandName,
                                                            key /* =null */,
                                                            id /* =null */) {
    this.createMenuItem(partInterface,label,commandName,key,id);
    this.registerCommand(commandName,handler);
}

/* addCommand
 * adds a command element to the command controller */
projectExtensionManager.prototype.addCommand = function(commandName) {
    var commandset = document.getElementById('cmdset_parts');
    if (!commandset) {
        log.error('extension manager unable to get element: cmdset_parts');
        return false;
    }

    // if it already exists, exit
    if (commandset.getElementsByAttribute('id', commandName).length > 0) return true;

    var commandEl = document.createElementNS(XUL_NS, 'command');
    commandEl.setAttribute('id',commandName);
    commandEl.setAttribute('oncommand','window.setTimeout("ko.commands.doCommand(\''+commandName+'\');",1);');
    commandset.appendChild(commandEl);
    return true;
}

projectExtensionManager.prototype.createMenuItem = function(partInterface,label,commandName,key,id,primary) {
    if (typeof(id) == 'undefined' || !id) {
        id = 'menu_'+ commandName;
    }
    var mi = document.getElementById(id);
    if (!mi) {
        mi = document.createElementNS(XUL_NS, 'menuitem');
        if (primary) {
            mi.setAttribute('class','primary_menu_item menuitem-iconic-wide');
        } else {
            mi.setAttribute('class','menuitem-iconic-wide');
        }
        mi.setAttribute('id',id);
        mi.setAttribute('label',label);
        mi.setAttribute('command',commandName);
        if (key) mi.setAttribute('accesskey',key);
        return this.addMenuItem(partInterface, mi);
    }
    return true;
}

projectExtensionManager.prototype.addMenuItem = function(partInterface,newmenu) {
    var menupopup;
    if (!newmenu) {
        log.error("projectExtensionManager.addMenuItem called with a false 'newmenu' argument");
    }
    var t = typeof(this.menus[partInterface]);
    if (t == 'undefined') {
        this.interfaceMap[partInterface] = partInterface;
        if (newmenu.nodeName == 'menupopup') {
            this.menus[partInterface] = newmenu.childNodes;
            return true;
        } else {
            // create a new menu for this node type
            this.menus[partInterface] = new Array();
            this.menus[partInterface][0] = newmenu;
        }
    } else {
        if (newmenu.nodeName == 'menupopup') {
            this.menus[partInterface] = this.menus[partInterface].concat(newmenu.childNodes);
        } else {
            this.menus[partInterface][this.menus[partInterface].length] = newmenu;
        }
    }
    return true;
}

projectExtensionManager.prototype._commonCommands = function(command, items) {
    for (var i = 0; i < items.length; i++) {
        if (!this._commands[command].supportsCommand(command, items[i])) return false;
    }
    return true;
}

projectExtensionManager.prototype._commonInterface = function(partInterface, items) {
    var i, qi;
    for (i = 0; i < items.length; i++) {
        try {
            qi = items[i].QueryInterface(this.interfaceMap[partInterface]);
        } catch (e) {
            return false;
        }
        if (qi) continue;
        return false;
    }
    return true;
}

projectExtensionManager.prototype.updateToplevelMenu = function(menupopupid, event, viewid)
{
    // This code updates the toplevel "Project" or "Toolbox" menus to have as a
    // first element a hierarchical menu with the "primary" commands for the
    // selected item, if there is only one selected item. If there are multiple
    // items selected (or none), then the first menu and the corresponding
    // menuseparator are collapsed.
    try {
        var menu = null;
        var menupopup = document.getElementById(menupopupid);
        if (event.eventPhase != 2) return true;
        var partviewer = document.getElementById(viewid);
        var contextMenuName = partviewer.getAttribute('viewcontext');
        var items = partviewer.getSelectedItems();
        if (items.length != 1) {
            // make sure the placeholder and the separator are
            // collapsed
            menupopup.firstChild.setAttribute('label', 'No Selection');
            menupopup.firstChild.setAttribute('disabled', 'true');
            return true;
        } else {
            if (menupopup.firstChild.hasAttribute('disabled'))
                menupopup.firstChild.removeAttribute('disabled');
            menu = menupopup.firstChild;
            while (menu.childNodes.length) {
                menu.removeChild(menu.firstChild);
            }
        }
        menu.setAttribute('label', items[0].name);
// #if PLATFORM != "darwin"
        // XXX bug 65281 crash on darwin when updating menu icon in onpopupshowing
        var iconurl = items[0].iconurl;
        if (iconurl) {
            menu.setAttribute('image', iconurl);
        } else {
            menu.removeAttribute('image');
        }
// #endif
        var contextmenu = document.getElementById(contextMenuName);
        var newmenu = document.createElement('menupopup');
        var children = contextmenu.childNodes;
        var c2, cmd, c;
        for (var i = 0; i < children.length; i++) {
            c = children[i];
            if (c.hasAttribute('keep') &&
                ! c.getAttribute('intoplevel'))
                continue;
            c2 = document.createElement(c.nodeName);
            if (c.hasAttribute('label')) {
                c2.setAttribute('label', c.getAttribute('label'));
            }
            if (c.hasAttribute('command') && !c.hasAttribute('disabled')) {
                cmd = c.getAttribute('command');
                c2.setAttribute('oncommand', 'ko.projects.extensionManager.dispatchCommand("'+cmd+'", "'+viewid+'");');
            } else if (c.hasAttribute('oncommand')) {
                c2.setAttribute('oncommand', c.getAttribute('oncommand'));
            } else if (c.nodeName == 'menu') {
                c2 = c.cloneNode(1); // it's a hierarchical menu
            }
            newmenu.appendChild(c2);
        }
        menu.appendChild(newmenu);
        return true;
    } catch (e) {
        log.exception(e);
    }
    return false;
}

projectExtensionManager.prototype.dispatchCommand = function(command, viewid) {
    document.getElementById(viewid).focus();
    window.setTimeout("ko.commands.doCommand('"+command+"');",0);
}

projectExtensionManager.prototype.updateMenu = function(items, partviewer) {
    // This function is called whenever the selection changes in the part
    // viewers to make sure that the context menu for the parts is appropriate
    // for the currently selected files. (This is modulated by some trickery in
    // the case of right-clicks, to make sure that the context menu is
    // _immediately_ available in those cases.
    //
    // The function is called with a list of items (wrapped parts)), and needs
    // to figure out 1) what commands are 'primary' (show up before the
    // cut/copy/paste "transfer" menu items), which are secondary, and which are
    // enabled.
    //
    // (search MSDN for the guidelines as to what the order of context menus
    // should be if you want more details on this).
    //
    // The function must also deal properly with some of the 'persistent' menu
    // items such as cut/copy/paste/delete/properties, which are hard-coded in
    // the XUL static menu and marked with a 'keep' attribute.
    //
    // There is a notion of a 'primary interface', which defines what function
    // show up first, and which is the interface of the first selection.

    // If there are no selections there is nothing to do.
    if (items.length == 0) return false;

    // To be efficient, this function updates commands as their corresponding
    // menu items are added to the menu. It also needs to keep track of which
    // commands _used to be_ in the menu but aren't, since those need to be
    // updated too. Those commands and events are stored in the class variables
    // this.lastUpdatedEvents and this.lastUpdatedCommands.
    //
    // (note that efficiency here is important, since this function can affect
    // UI responsiveness when doing context menus in the parts.

    var updatedCommands = {};
    var updatedEvents = {};
    // We always want to update the part_selection commands to enable the
    // cut/copy/delete menu items
    window.updateCommands('part_selection');
    
    var contextMenuName = partviewer.getAttribute('viewcontext');
    var popup = document.getElementById(contextMenuName);

    var primaryInterface = null;
    var primaryMenu = [];
    if (items.length >= 1) {
        primaryInterface = items[0].primaryInterface;
    }
    var menuitems = [];
    var sep;
    for (var partInterface in this.interfaceMap) {
        if (typeof(this.menus[partInterface]) != 'undefined' &&
            this._commonInterface(this.interfaceMap[partInterface],items)) {
            if (primaryInterface == new String(this.interfaceMap[partInterface])) {
                primaryMenu = primaryMenu.concat(this.menus[partInterface]);
                continue;
            }
            menuitems = menuitems.concat(this.menus[partInterface]);
        }
    }
    var primaryCommandSeparator = popup.getElementsByAttribute("anonid", "primaryseparator")[0];
    var secondaryCommandSeparator = popup.getElementsByAttribute("anonid", "secondaryseparator")[0];
    if (primaryMenu.length == 0) {
        // If there are no primary commands, then we don't want to start with
        // a menu separator
        primaryCommandSeparator.setAttribute('hidden', 'true');
    } else {
        menuitems = primaryMenu.concat(menuitems);
        if (primaryCommandSeparator.hasAttribute('hidden')) {
            // see above -- this undoes that.
            primaryCommandSeparator.removeAttribute('hidden');
        }
    }
    var children = popup.childNodes;
    var i, child
    // We start by cleaning out old menu items (keeping the 'keep' marked ones)
    for (i = children.length-1; i >= 0; i--) {
        child = children[i];
        if (! child.hasAttribute('keep') ||
            child.getAttribute('keep') == 'false') {
            popup.removeChild(child);
        }
        // The updateMenuInterface() function can collapse -- we undo that.
        if (child.hasAttribute('collapsed')) {
            child.removeAttribute('collapsed');
        }
    }

    var command;
    var retval = false;
    if (menuitems.length > 0) {
        var clone, menuitem, events;
        if (menuitems.length > primaryMenu.length) {
            sep = document.createElementNS(XUL_NS, 'menuseparator');
            popup.insertBefore(sep, secondaryCommandSeparator);
        }
        var commandId;
        for (i = 0; i < menuitems.length; i++) {
            menuitem = menuitems[i].cloneNode(1);
            command = menuitem.getAttribute('command');

            if (!command || this._commonCommands(command, items)) {
                if (i < primaryMenu.length) {
                    popup.insertBefore(menuitem, primaryCommandSeparator);
                } else {
                    popup.insertBefore(menuitem, secondaryCommandSeparator);
                }
                if (menuitem.hasAttribute('collapsed')) {
                    menuitem.removeAttribute('collapsed');
                }
                if (menuitem.nodeName == 'menu') {
                    events = menuitem.getAttribute('events');
                    if (events) {
                        window.updateCommands(events);
                        updatedEvents[events] = true;
                    }
                } else if (menuitem.nodeName == 'menuitem') {
                    commandId = menuitem.getAttribute('command')
                    try {
                        ko.commands.updateCommand(commandId);
                        updatedCommands[commandId] = true;
                    } catch(e) {
                        log.exception(e);
                    }
                }
            }
        }
        retval = true;
    }
    // Now update those commands which were updated the last time but not this time.
    if (popup.lastUpdatedCommands) {
        for (command in popup.lastUpdatedCommands) {
            if (command in updatedCommands) continue;
            ko.commands.updateCommand(command);
        }
    }
    if (popup.lastUpdatedEvents) {
        for (var event in popup.lastUpdatedEvents) {
            if (event in updatedEvents) continue;
            window.updateCommands(event);
        }
    }
    popup.lastUpdatedEvents = updatedEvents;
    popup.lastUpdatedCommands = updatedCommands;
    return retval;
}

projectExtensionManager.prototype.addEventHandler = function(partInterface,eventType,eventHandler)
{
    if (typeof(this.handlers[partInterface]) == 'undefined') {
        this.interfaceMap[partInterface] = partInterface;
        this.handlers[partInterface] = {};
    }
    if (typeof(this.handlers[partInterface][eventType]) == 'undefined') {
        this.handlers[partInterface][eventType] = new Array();
    }
    this.handlers[partInterface][eventType].push(eventHandler);
}

projectExtensionManager.prototype.callHandler = function(part,eventType,event) {
    for (var partInterface in this.interfaceMap) {
        try {
            if (part.QueryInterface(this.interfaceMap[partInterface]) &&
                typeof(this.handlers[partInterface]) != 'undefined' &&
                typeof(this.handlers[partInterface][eventType]) != 'undefined') {
                    var handlers = this.handlers[partInterface][eventType];
                    for (var i = 0; i < handlers.length; i++) {
                        try {
                            handlers[i][eventType].apply(handlers[i],[part,event]);
                        } catch(e) {
                            log.warn("exception calling "+eventType+"\n"+e+"\n");
                        }
                    }
            }
        } catch(e) { /* no interface */ }
    }
}

//----------------------------------------------------------------------------------------------
// Controller functions

projectExtensionManager.prototype.registerCommand = function(command, extension) {
    this.addCommand(command);
    this._commands[command] = extension;
}

projectExtensionManager.prototype.supportsCommand = function(command) {
    return typeof(this._commands[command]) != 'undefined';
}

projectExtensionManager.prototype.isCommandEnabled = function(command) {
    //dump("projectExtensionManager.isCommandEnabled("+ command + ") --> ");
    if (typeof(this._commands[command]) == 'undefined') {
        return false;
    }
    return this._commands[command].isCommandEnabled(command);
    //XXX - Remove rest of code here.
    //dump("isCommandEnabled command "+cmd+"\n");
    try {
        return this._commands[command].isCommandEnabled(command);
    } catch(ex) {
        // Sometimes this fails at shutdown.  Dump for development only.
        dump(ex + "\n");
        return false;
    }
}

projectExtensionManager.prototype.doCommand = function(command) {
    if (typeof(this._commands[command]) == 'undefined') {
        return false;
    }
    //dump("doCommand command "+cmd+"\n");
    return this._commands[command].doCommand(command);
}

projectExtensionManager.prototype.onEvent = function(event) {
    // XXX remove if possible
}

this.extensionManager = new projectExtensionManager();
var registeredExtensions = [];

this.registerExtension = function(ext) {
    registeredExtensions.push(ext);
}

}).apply(ko.projects);

var extensionManager = ko.projects.extensionManager;

