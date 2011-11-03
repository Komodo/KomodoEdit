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

/*

base Manager

base class for all 'project' viewer manager classes

*/
if (typeof(ko)=='undefined') {
    var ko = {};
}
if (typeof(ko.projects)=='undefined') {
    ko.projects = {};
}

(function() {
    
this.managers = [];
    
function BaseManager(command_name) {
    this.viewMgr = null; // set in subclasses
    this._command_name = null;
    if (typeof(command_name) != 'undefined')
        this._command_name = command_name;
    this.batchUpdate = false;
}

BaseManager.prototype.constructor = BaseManager;

BaseManager.prototype.addItem = function(/* koIPart */ part, index) {
    this.log.error('BaseManager.prototype.addItem not implemented');
}

BaseManager.prototype.removeItem = function(item, skipdialog) {
    if (typeof(skipdialog)=='undefined') skipdialog = false;
    if (!skipdialog) {
        if (!item.project) {
            return false;
        }
        var container = " project '" + item.project.name + "'";
        var question = "Do you want to remove the " + item.type +
                       " '" +
                       item.name + "' from the " + container + "?";
        skipdialog = ko.dialogs.yesNo(question) == "Yes";
    }
    if (skipdialog) {
        try {
            var parent = item.parent;
            parent.removeChild(item);
            if (!this.batchUpdate && this.viewMgr)
                this.viewMgr.refreshRow(parent);
        } catch (e) {
            this.log.exception(e);
        }
        return true;
    }
    return false;
}


BaseManager.prototype.removeItems = function(items, trash) {
    var sysUtilsSvc = Components.classes["@activestate.com/koSysUtils;1"].
                getService(Components.interfaces.koISysUtils);
    this.batchUpdate = items.length > 1;
    try {
        var item;
        var projects = [];
        for (var i = 0; i < items.length; i++) {
            item = items[i];
            if (item.parent) {
                // If we're removing a group, all of its contents are
                // also removed from the project.
                item.parent.removeChild(item);
            }
            if (trash) {
                var file = item.getFile();
                if (file && file.isLocal) {
                    // move to trash
                    sysUtilsSvc.MoveToTrash(file.path);
                }
            }
        }
        if (this.viewMgr) {
            this.viewMgr.removeSelectedItems(items);
        }
    } catch(e) {
        this.log.exception(e);
    }
    this.batchUpdate = false;
}

BaseManager.prototype.renameItem = function(item) {
    var resp = new Object ();
    resp.name= item.name;
    resp.value = item.value;
    resp.res = '';

    if (resp.value) {
        ko.windowManager.openOrFocusDialog("chrome://komodo/content/project/renamePart.xul",
                'komodo_renamePart',
                "chrome,dialog,modal,resizable=yes",
                resp);
        if (resp.res != true) {
            return false;
        }
    } else {
        resp.name = ko.dialogs.prompt(
            "Enter the new name.", // prompt
            null, // label
            item.name, // default
            "New Name"); // title
        if (!resp.name) return false;
    }
    /* Modify the project attribute and the wrapped attribute */
    item.name = resp.name;
    return true;
}

BaseManager.prototype.getItemsByURL = function(url) {
    this.log.error('BaseManager.prototype.getItemsByURL not implemented');
}

BaseManager.prototype.refreshView = function() {
    if (this.viewMgr && this.viewMgr.tree.treeBoxObject) {
        this.viewMgr.tree.treeBoxObject.beginUpdateBatch();
        this.viewMgr.tree.treeBoxObject.invalidate();
        this.viewMgr.tree.treeBoxObject.endUpdateBatch();
    }
}

BaseManager.prototype.invalidateItem = function(item) {
    var viewMgr, index;
    if ('save' in item) {
        //!!!! v6 difference
        viewMgr = ko.toolbox2.manager;
        index = viewMgr.getIndexByTool(item);
    } else {
        viewMgr = this.viewMgr;
        if (viewMgr) {
            index = viewMgr.getIndexByPart(item);
        }
    }
    if (index >= 0) {
        viewMgr.tree.treeBoxObject.invalidateRow(index);
        return true;
    }
    return false;
}

BaseManager.prototype.findChildByAttributeValue = function (item, attribute, value) {
    try {
        return item.getChildByAttributeValue(attribute, value, true);
    } catch(e) {
        // not a container
        this.log.exception(e);
    }
    return null;
}


BaseManager.prototype.isChildOf = function (parent, child) {
    try {
        return parent.hasChild(child);
    } catch(e) {
        this.log.exception(e);
    }
    return false;
}

BaseManager.prototype.findItemByURL = function (parent, type, url) {
    var child = parent.getChildWithTypeAndStringAttribute(type, "url", url, true);
    if (child) return child;
    if (parent.url == url) {
        return parent;
    }
    return null;
}

BaseManager.prototype.applyPartKeybindings = function () {
    // No default implementation -- up to each partManager to define it,
    // using the callback in the wrappedPart.
}

BaseManager.prototype.writeable = function () {
    // No default implementation -- up to each partManager to define it,
}

BaseManager.prototype.onDrop = function(event, transferDataSet, session, index) {
    // detect if being draged from a projectviewer, which implies we have a komodo part
    var sourceNode = session.sourceNode;
    var sourceNodeName = null;
    var elementId = null;
    var viewer = null;
    var dragged = null;
    //this.log.setLevel(ko.logging.LOG_DEBUG);
    this.log.debug("session.sourceNode " + session.sourceNode);
    if (session.sourceNode)
        this.log.debug("session.sourceNode.nodeName " + session.sourceNode.nodeName);
    this.log.debug("session.numDropItems " + session.numDropItems);
    if (sourceNode && (sourceNode.localName == 'partviewer' ||
                       sourceNode.localName == 'treechildren')) {
        if (sourceNode.localName == 'treechildren') {
            sourceNode = sourceNode.parentNode.parentNode.parentNode;
        }
        try {
            sourceNodeName = sourceNode.localName;
            this.log.debug("  sourceNodeName = " + sourceNodeName);
            elementId = sourceNode.id;
            this.log.debug("  elementId = " + elementId+'\n');
            viewer = document.getElementById(elementId);
            this.log.debug("  viewer = " + viewer.getAttribute('id'));
            dragged = viewer.getSelectedItems();
            this.log.debug("  dragged = " + dragged);
        } catch(e) {
            this.log.debug(e);
            // it was not a projectviewer
            sourceNodeName = null;
            elementId = null;
            viewer = null;
            dragged = null;
        }
    }
    this.viewMgr.focus();
    var part;

    var droppedon = this.viewMgr.view.getRowItem(index);
    var droppedonIsContainer = this.viewMgr.view.isContainer(index);
    if (!droppedonIsContainer && droppedon) {
        droppedon = droppedon.parent;
    } else if (!droppedon && this != ko.projects.manager) {
        droppedon = this.toolbox;
        droppedonIsContainer = true;
    }

    // loop through dragged elements
    for ( var i = 0; i < transferDataSet.dataList.length; ++i ) {
        var transferData = transferDataSet.dataList[i];
        // handle the data now
        if (dragged && dragged.length > 0 && sourceNodeName == 'partviewer') {
            // we can only drag from one place at a time, so we should match the returned index!
            var dragpart = dragged[i];

            if (session.dragAction == Components.interfaces.nsIDragService.DRAGDROP_ACTION_COPY) {
                this.log.debug('copying a part of type '+dragpart.type);
                part = dragpart.clone();
                this.addItem(part, droppedon);
            } else {
                if (droppedon == dragpart) continue;
                // if what we are dropping on is not a container, then make
                // sure that it's parent does not already have
                // the part we're dragging as a direct child
                if (droppedon.hasChild(dragpart)) continue;

                // if we're dropping on a container, make sure
                // that we are not already a child of that
                // container, and that the dropon point is not
                // a child of the drag part
                if (droppedon.isAncestor(dragpart)) continue;
                this.log.debug('moving a part of type '+dragpart.type+":"+dragpart.name+" onto "+droppedon.type+":"+droppedon.name);

                // remove the part from it's old parent if we can add it to the
                // new view.  do not remove children of a live folder, but allow
                // a top level live folder to be moved in a project.
                part = dragpart.clone();
                if (this.addItem(part, droppedon) && !(dragpart.parent.live && dragpart.live))
                    viewer.manager.removeItem(dragpart,true);
            }
        } else {
            // XXX this is hardcoded to file or snippet, should be refactored to allow
            // any extension to examine the dropped data.
            var desc = new Object();
            // from DragDrop.js
            this.log.debug('unpacking the dropped data...');
            ko.dragDrop.unpackData(transferData.dataList[0], desc)

            //dump ("data = " + desc.text +'\n');
            //ko.logging.dumpObject(desc);
            if (desc.isDebuggerFile) return false;

            if (!desc.isURL) {
                ko.projects.addSnippetFromText(desc.text,droppedon);
                continue;
            }
            // If we're here, it is a URL
            if (desc.text.match(/\.kpz$/)) {
                ko.projects.importFromPackage(this.viewMgr, droppedon, desc.text);
                continue;
            } else if (!desc.isFileOrDir) {
                //dump("Adding URL "+desc.text+"\n");
                ko.projects.addURLFromText(desc.text,droppedon);
                continue;
            }
            // if we're here, it's a URL to something we can open (file or folder)
            //dump("is URL\n");
            if (! desc.isExistingFile) {
                // XXX should do something about "missing files?"
                // for now, fall through.
            }
            //dump("is Existing File\n");

            // handle new lines in droped file uri's
            if (desc.text.search("\n")) {
                var s = desc.text.split("\n");
                desc.name = typeof(s[1])!='undefined'?s[1]:s[0];
                desc.text = s[0];
            }

            if (desc.isDir) {
                // for projects, add a live folder, for toolbox, add a shortcut
                if (typeof(this.toolbox) == 'undefined') {
                    ko.projects.addLiveFolder(ko.uriparse.URIToLocalPath(desc.text), droppedon);
                }
            } else if (desc.isFileURL && desc.text.match(/\.komodoproject$/)) {
                ko.projects.open(desc.text);
            } else {
                // XXX should check that the project doesn't already have the URL
                part = droppedon.project.createPartFromType('file');
                part.setStringAttribute('url', desc.text);
                part.setStringAttribute('name', ko.uriparse.baseName(desc.text));
                this.addItem(part, droppedon);
            }
        }
    } // foreach drag item
    return true;
}
this.BaseManager = BaseManager;

/* looks in all managers for items related to the url so it can update them */
this.findItemsByURL = function findItemsByURL(url)
{
    var managers = ko.projects.managers;
    var items = [];
    var list;
    for (var i=0; i < managers.length; i++) {
        list = managers[i].getItemsByURL(url);
        items = items.concat(list);
    }
    return items;
}

this.removeItemsByURL = function removeItemsByURL(url, skipDialog)
{
    var managers = ko.projects.managers;
    var items = [];
    var i, j, list;
    for (i=0; i < managers.length; i++) {
        list = managers[i].getItemsByURL(url);
        for (j = 0; j < list.length; j++) {
            managers[i].removeItem(list[j], skipDialog);
        }
    }
    return items;
}

this.removeItemsByURLList = function(urls, skipDialog)
{
    var managers = ko.projects.managers;
    for (var i = 0; i < urls.length; i++) {
        for (var j=0; j < managers.length; j++) {
            var list = managers[j].getItemsByURL(urls[i]);
            for (var k = 0; k < list.length; k++) {
                managers[j].removeItem(list[k], skipDialog);
            }
        }
    }
}

/* looks in all managers for _parts_ related to the url so it can update them */
this.findPartsByURL = function findPartsByURL(url)
{
    var parts = []
    var managers = ko.projects.managers;
    for (var i=0; i < managers.length; i++) {
        var list = managers[i].getPartsByURL(url);
        parts = parts.concat(list);
    }
    return parts;
}

this.hasURL = function(url)
{
    var managers = ko.projects.managers;
    for (j=0; j < managers.length; j++) {
        list = managers[j].getItemsByURL(result[3]);
        if (list.length > 0 || managers[j].isLivePath(result[3])) {
            return true;
        }
    }
    return false;
}

this.invalidateItem = function invalidateItem(item)
{
    var managers = ko.projects.managers;
    for (var i=0; i < managers.length; i++) {
        if (managers[i].invalidateItem(item)) continue;
    }
}

this.addItem = function(item, parent) {
    var manager = ko.projects.manager;
    manager.addItem(item,parent);
}

this._toolboxParts = ['macro', 'snippet', 'command', 'template',
                      'menu','toolbar', 'URL'];

/**
 * findPart
 *
 * find a part in the toolboxes and/or a specifid part's project
 *
 * @param {string} type
 * @param {string} name
 * @param {string} where one of "container", "toolbox", "shared toolbox",
 *                       "toolboxes" or "*" where "*" means
 *                       "current part project, toolbox, shared toolbox"
 * @param {koIPart} part defaults to the running macro if available
 * @returns {koIPart}
 *
 * This method is left in for v5 compatibility.
 */
this.findPart = function macro_findPart(type, name, where, /*koIPart*/ part) {
    var _partSvc = Components.classes["@activestate.com/koPartService;1"]
            .getService(Components.interfaces.koIPartService);
    if (!part) {
        part = _partSvc.runningMacro;
    }
    var foundPart = _partSvc.findPart(type, name, where, part);
    if (foundPart) {
        return foundPart;
    }
    // Try the version 6 API
    if (this._toolboxParts.indexOf(type) != -1) {
        foundPart = ko.toolbox2.getToolsByTypeAndName(type, name);
        if (foundPart && foundPart.length) {
            return foundPart[0];
        }
    }
    return null;
}

}).apply(ko.projects);
