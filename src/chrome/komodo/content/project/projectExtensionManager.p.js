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

var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
      .getService(Components.interfaces.nsIStringBundleService)
      .createBundle("chrome://komodo/locale/project/projectExtensionManager.properties");
      
function projectExtensionManager() {
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
}

projectExtensionManager.prototype.constructor = projectExtensionManager;

projectExtensionManager.prototype.init = function() {
    var i, extension;
    for (i = 0; i < registeredExtensions.length; i++)
    {
        extension = registeredExtensions[i]
        this.registerExtension(extension);
    }
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
            mi.setAttribute('class','primary_menu_item');
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

projectExtensionManager.prototype.dispatchCommand = function(command, viewid) {
    document.getElementById(viewid).focus();
    window.setTimeout("ko.commands.doCommand('"+command+"');",0);
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

