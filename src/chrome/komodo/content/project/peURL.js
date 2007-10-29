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

if (typeof(ko)=='undefined') {
    var ko = {};
}
if (typeof(ko.projects)=='undefined') {
    ko.projects = {};
}

(function() {
var _log = ko.logging.getLogger('peURL');

function peURL() {
    this.name = 'peURL';
}

// The following two lines ensure proper inheritance (see Flanagan, p. 144).
peURL.prototype.constructor = peURL;

peURL.prototype.init = function() {
}

peURL.prototype.registerCommands = function() {
    ko.projects.extensionManager.registerCommand('cmd_openSpecifiedURL', this);
    ko.projects.extensionManager.registerCommand('cmd_openSpecifiedURLinTab', this);
}

peURL.prototype.registerEventHandlers = function() {
    ko.projects.extensionManager.addEventHandler(Components.interfaces.koIPart_URL,'ondblclick',this);
}

peURL.prototype.registerMenus = function() {
    ko.projects.extensionManager.createMenuItem(Components.interfaces.koIPart_URL,
                                    'Open URL in browser',
                                    'cmd_openSpecifiedURL',
                                    null,
                                    null,
                                    true);
    ko.projects.extensionManager.createMenuItem(Components.interfaces.koIPart_URL,
                                    'Open URL in tab',
                                    'cmd_openSpecifiedURLinTab');
}

peURL.prototype.ondblclick = function(/*koIPart*/ part, event) {
    if (part.type != 'URL' && part.type != 'webservice') return;
    this.openURL(part)
}

peURL.prototype.supportsCommand = function(command, /*koIPart*/ part) {
    var items = ko.projects.active.getSelectedItems();
    if (items.length > 1) return false;

    var view = ko.projects.active;
    if (!view) return false;
    //dump("supportsCommand for " + command +'\n');
    switch (command) {
    case 'cmd_openSpecifiedURLinTab':
    case 'cmd_openSpecifiedURL':
        return true;
    default:
        break;
    }
    return false;
}

peURL.prototype.isCommandEnabled = peURL.prototype.supportsCommand;

peURL.prototype.doCommand = function(command) {
    var view, part;
    switch (command) {
    case 'cmd_openSpecifiedURLinTab':
        view = ko.projects.active;
        var item = view.getSelectedItem();
        var docSvc = Components.classes['@activestate.com/koDocumentService;1']
                    .getService(Components.interfaces.koIDocumentService);
        var doc = docSvc.createDocumentFromURI(item.value);
        ko.views.manager.topView.createViewFromDocument(doc,'browser');
        break;
    case 'cmd_openSpecifiedURL':
        view = ko.projects.active;
        part = view.getSelectedItem();
        this.openURL(part);
        break;
    default:
        break;
    }
}

peURL.prototype.openURL= function(/*koIPart*/ item) {
    //dump("part = " + part + " type = " + typeof(part) +'\n');
    //dump("URL = " + item.value + ' type = ' + typeof(item.value) +'\n');
    try {
        ko.browse.openUrlInDefaultBrowser(item.value);
    } catch (e) {
        _log.exception(e);
    }
}

// this is hidden away now, no namespce, the registration keeps the reference
// we need
ko.projects.registerExtension(new peURL());

this.URLProperties = function peURL_editProperties(/*koIPart*/ item)
{
    var obj = new Object();
    obj.item = item;
    obj.task = 'edit';
    obj.imgsrc = 'chrome://komodo/skin/images/xlink.png';
    obj.type = 'url';
    obj.prettytype = 'URL';
    window.openDialog(
        "chrome://komodo/content/project/simplePartProperties.xul",
        "Komodo:URLProperties",
        "chrome,centerscreen,close=yes,dependent=yes,modal=yes,resizable=yes", obj);
}

this.addURLFromText = function peURL_addURL(URLtext, /*koIPart*/ parent) {
    if (typeof(parent) == 'undefined' || !parent)
        parent = ko.projects.active.manager.getCurrentProject();
    try {
        var URL = parent.project.createPartFromType('URL');
        var name = URLtext;
        var value = URLtext;
        if (URLtext.search("\n")) {
            var s = URLtext.split("\n");
            name = typeof(s[1])!='undefined'?s[1]:s[0];
            value = s[0];
        }
        URL.setStringAttribute('name', name);
        URL.value = value;
        ko.projects.addItem(URL,parent);
        //dump("leaving AddURL\n");
    } catch (e) {
        _log.exception(e);
    }
}

this.addURL = function peURL_newURL(/*koIPart*/ parent)
{
    var part = parent.project.createPartFromType('URL');
    part.setStringAttribute('name', 'New URL');
    part.value = '';
    var obj = new Object();
    obj.item = part;
    obj.task = 'new';
    obj.imgsrc = 'chrome://komodo/skin/images/xlink.png';
    obj.type = 'url';
    obj.prettytype = 'URL';
    obj.parent = parent;
    window.openDialog(
        "chrome://komodo/content/project/simplePartProperties.xul",
        "Komodo:URLProperties",
        "chrome,centerscreen,close=yes,modal=yes,resizable=yes", obj);
}

}).apply(ko.projects);

// backwards compat api's
var peURL_editProperties = ko.projects.URLProperties;
var peURL_addURL = ko.projects.addURLFromText;
var peURL_newURL = ko.projects.addURL;
