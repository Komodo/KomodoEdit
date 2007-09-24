/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

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
