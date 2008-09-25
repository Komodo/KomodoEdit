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

// Handle drag-drop of files onto the main Workspace window.
// this relies on using nsDragDrop.js

if (typeof(ko)=='undefined') {
    var ko = {};
}
ko.dragDrop = {};

(function() {
var _log = ko.logging.getLogger('ko.dragDrop');
//_log.setLevel(ko.logging.LOG_DEBUG);

this.dragObserver = {
    canHandleMultipleItems: true,
    focusWindow: function() {
        window.focus();
        window.getAttention();
        /*
          This function needs to make the window be active and focused
          to fix problems with dropping objects onto komodo from outside
          applications.

          XXX this should work to activeate the window, but
          setFocus is not implemented in nsXULWindow.cpp.  The code
          below is taken partly from filepicker.js in xpfe

        var baseWin = null;
        try {
            baseWin = window.QueryInterface(Components.interfaces.nsIInterfaceRequestor)
                            .getInterface(Components.interfaces.nsIWebNavigation)
                            .QueryInterface(Components.interfaces.nsIDocShellTreeItem)
                            .treeOwner
                            .QueryInterface(Components.interfaces.nsIInterfaceRequestor)
                            .getInterface(Components.interfaces.nsIBaseWindow);
            baseWin.setFocus();
        } catch(ex) {
            _log.exception(ex,'Unable to get base window');
        }
        */
    },
    getSupportedFlavours: function() {
        var flavours = new FlavourSet();
        flavours.appendFlavour("text/unicode");
// #if PLATFORM != "win"
        flavours.appendFlavour("TEXT");
// #endif
        flavours.appendFlavour("text/x-moz-url");
        flavours.appendFlavour("application/x-moz-file", "nsIFile");
        return flavours;
    },
    canDrop: function(event, session) {
        if (session.sourceNode
            && session.sourceNode.localName == 'tab'
            && session.sourceNode.ownerDocument != document)
        {
            // This session represents a view from another Komodo window:
            // ask that view if it can be moved to another Komodo window.
            // - Find the tabbed-view list to which this tab belongs.
            var viewList = session.sourceNode;
            while (viewList && viewList != this) {
                if (viewList.localName == 'view') {
                    break;
                }
                viewList = viewList.parentNode;
            }
            // - Ask the view if it can be moved.
            if (viewList && !viewList.currentView.canBeOpenedInAnotherWindow()) {
                return false;
            }
        }
        
        return true;
    },
    onDragOver: function(event,flavour,session) {
        return true;
    },
    onDrop: function(event, transferDataSet, dragSession) {
        var num_items = 0;
        var uri_open_list = [];
        _log.debug('dragObserver.onDrop items: ['+transferDataSet.dataList.length+']');
        for ( var i = 0; i < transferDataSet.dataList.length; ++i ) {
            var transferData = transferDataSet.dataList[i];
            var desc = new Object();
            // from DragDrop.js
            ko.dragDrop.unpackData(transferData.dataList[0], desc)
            desc.dragAction = dragSession.dragAction;
            _log.debug('dragObserver data: ['+desc.text+']');
            if (desc.isFileURL || desc.isRemoteFileURL || desc.text.match(/\.xpi$/i)) {
                _log.debug('dragObserver opening files');
                uri_open_list.push(desc.text);
                num_items++;
            }
        } // foreach drag item
        if (uri_open_list.length)
            ko.open.multipleURIs(uri_open_list);
        if (num_items < 1) {
            return desc;
        }
        // force a focus onto the window after having files dropped on it
        this.focusWindow();
        return null;
    },
    doDragOverEvent: function(event) {
        _log.debug('dragObserver.doDragOverEvent');
        try {
            nsDragAndDrop.dragOver(event,this);
        } catch(e) {
            _log.exception(e,'dragObserver dragOver exception:');
        }
    },
    doDropEvent: function(event) {
        _log.debug('dragObserver.doDropEvent');
        try {
            nsDragAndDrop.drop(event,this);
        } catch(e) {
            _log.error(e,'dragObserver drop exception:');
        }
    }
}

this.unpackData = function(flavourData, ret) {
    var os = Components.classes["@activestate.com/koOs;1"].
          getService(Components.interfaces.koIOs);
    var fname = null;
    var url = null;
    var ioService, fileHandler;
    ret.text = flavourData.data;
    ret.flavour = flavourData.flavour.contentType;
    ret.isURL = false;
    ret.isFileURL = false;
    ret.isRemoteFileURL= false; // true for ftp:// ftps:// sftp:// and scp://
    ret.isFileOrDir = false;    // true for both file:// and remote file urls
    ret.isExistingFile = false;
    ret.isDir = false;
    _log.debug('flavour is '+ret.flavour);
    switch (ret.flavour) {
    case "application/x-moz-file":
        _log.debug("x-moz-file: flavourData.data["+flavourData.data+"]");
        try { // XXX don't know when this is true ...
            ioService = Components.classes["@mozilla.org/network/io-service;1"]
                                   .getService(Components.interfaces.nsIIOService);
            fileHandler = ioService.getProtocolHandler("file")
                                    .QueryInterface(Components.interfaces.nsIFileProtocolHandler);
            ret.text = fileHandler.getURLSpecFromFile(flavourData.data);
        } catch(e) {
            return;
        }
        break;
    default: // we try this as a url irregardless of type
        break;
    }
    _log.debug('dropped data is ['+ret.text+']');
    var origdata = flavourData.data;
    if (ret.text.search("://") == -1) { // Disqualify things that don't come close to looking like URLs
// #if PLATFORM != "win"
        if (ret.text.match(/^file:\/[\w|\.]/)) {
            // unix file:/home.... url from drag/drop
            ret.text = 'file://'+ret.text.slice(5);
            _log.debug('unix file url is now ['+ret.text+']');
        } else {
// #endif
            //dump('dropped data is '+ret.text+'\n');
            try {
                ioService = Components.classes["@mozilla.org/network/io-service;1"]
                                          .getService(Components.interfaces.nsIIOService);
                fileHandler = ioService.getProtocolHandler("file")
                                           .QueryInterface(Components.interfaces.nsIFileProtocolHandler);
                ret.text = fileHandler.getURLSpecFromFile(origdata);
                // fall through, magic presto it's now a URL
            } catch (e) {
                _log.debug('this is not a url: ['+ret.text+']');
                return;
            }
// #if PLATFORM != "win"
        }
// #endif
    }
    // remove any newlines from dropped url's
    if (ret.text.search("\n") >= 0) {
        // get the first line
        ret.text = ret.text.split('\n')[0];
        // strip the line
        ret.text = ret.text.replace(/(^\s*|\s*$)/g, '');
    }

    // Ensure the URI is properly decoded. Fixes bug:
    // http://bugs.activestate.com/show_bug.cgi?id=72873
    ret.text = decodeURI(ret.text);

    _log.debug('dropped URL is ['+ret.text+']');
    ret.isURL = true;
    // see if this is a mappable url
    while (1) {
        ret.text = ko.uriparse.getMappedURI(ret.text);
        _log.debug('mapped URL is ['+ret.text+']');
        if (ret.text.search('file://') == 0) {
            ret.isFileOrDir = true;
            ret.isFileURL = true;
            try {
                var path = ko.uriparse.URIToLocalPath(ret.text);
                ret.isExistingFile = os.path.exists(path);
                //dump("after exists test\n");
                if (ret.isExistingFile) {
                    ret.isDir = os.path.isdir(path);
                }
            } catch (e) {
                ret.isExistingFile = false;
            }
            return;
        } else
        if ((ret.text.search('ftp://') == 0) ||
            (ret.text.search('ftps://') == 0) ||
            (ret.text.search('sftp://') == 0) ||
            (ret.text.search('scp://') == 0)) {
            ret.isFileOrDir = true;
            ret.isRemoteFileURL = true;
            // XXX should find out if it is a file on one of the servers we know about?
            // XXX should find out if it's a dir (hard?)
            return;
        } else
        if (ret.text.search('https?://') == 0 &&
            ret.text.search('\.xpi$') < 0) {
            // ask the user to add a uri mapping
            if (dialog_yesNo("You have dropped a URL onto Komodo, would you like "+
                             "to setup a Mapped URL?  A Mapped URL "+
                             "will translate a remote URL to a local file.  " +
                             "You can edit this later in the Mapped URI "+
                             "Preferences panel.",
                             "Yes", null, null,
                             "dragdrop_mapped_uri") == "Yes") {
                if (ko.uriparse.addMappedURI(ret.text))
                    // allow another loop in the while
                    continue;
            }
        } else
        if (ret.text.search('macro://') == 0) {
            ret.isFileOrDir = true;
            ret.isFileURL = true;
            return;
        }
        break;
    }
    // not a url after all
    ret.text = origdata;
    ret.isURL = false;
}

}).apply(ko.dragDrop);
