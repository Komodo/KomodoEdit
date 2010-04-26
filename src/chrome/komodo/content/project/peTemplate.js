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
    ko.views.manager.doFileNewFromTemplateAsync(item.url);
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
    ko.launch.newTemplate(obj);
    if (obj.template == null) return;

    var url = ko.uriparse.localPathToURI(obj.template);
    var templateName = ko.uriparse.baseName(obj.template);
    var part = parent.project.createPartFromType('template');

    part.setStringAttribute('name', templateName);
    part.url = url;

    ko.projects.addItem(part,parent);
}

}).apply(ko.projects);

