/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */


if (typeof(ko)=='undefined') {
    var ko = {};
}
if (typeof(ko.projects)=='undefined') {
    ko.projects = {};
}

(function() {

function peTemplate() {
    this.name = 'peTemplate';
}

// The following two lines ensure proper inheritance (see Flanagan, p. 144).
peTemplate.prototype.constructor = peTemplate;

peTemplate.prototype.init = function() {
}

peTemplate.prototype.registerCommands = function() {
    ko.projects.extensionManager.registerCommand('cmd_openTemplatePart', this);
}

peTemplate.prototype.registerEventHandlers = function() {
    ko.projects.extensionManager.addEventHandler(Components.interfaces.koIPart_template,'ondblclick',this);
}

peTemplate.prototype.registerMenus = function() {
    ko.projects.extensionManager.createMenuItem(Components.interfaces.koIPart_template,
                                    'Open Template','cmd_openTemplatePart');
}

peTemplate.prototype.supportsCommand = function(command, part) {
    var view = ko.projects.active;
    if (!view) return false;
    switch (command) {
    case 'cmd_openTemplatePart':
        return true;
    default:
        break;
    }
    return false;
}

peTemplate.prototype.isCommandEnabled = peTemplate.prototype.supportsCommand

peTemplate.prototype.ondblclick = function(part,event) {
    this.openTemplate(part)
}

peTemplate.prototype.doCommand = function(command) {
    switch (command) {
    case 'cmd_openTemplatePart':
        var items = ko.projects.active.getSelectedItems();
        for (var i = 0; i < items.length; i++) {
            if (items[i].type == 'template') this.openTemplate(items[i]);
        }
        break;
    default:
        break;
    }
}

peTemplate.prototype.openTemplate = function(item)
{
    ko.views.manager.doFileNewFromTemplate(item.url);
}

// this is hidden away now, no namespce, the registration keeps the reference
// we need
ko.projects.registerExtension(new peTemplate());

this.addTemplate = function peTemplate_addTemplate(/*koIPart*/ parent)
{
    if (typeof(parent)=='undefined' || !parent)
        parent = ko.projects.active.getSelectedItem();

    // Get template selection from the user.
    var obj = new Object();
    obj.type = "file";
    obj.templateOnly = true;
    window.openDialog("chrome://komodo/content/templates/new.xul",
                      "_blank",
                      "chrome,modal,titlebar",
                      obj);
    if (obj.template == null) return;

    var url = ko.uriparse.localPathToURI(obj.template);
    var templateName = ko.uriparse.baseName(obj.template);
    var part = parent.project.createPartFromType('template');

    part.setStringAttribute('name', templateName);
    part.url = url;

    ko.projects.addItem(part,parent);
}

}).apply(ko.projects);

