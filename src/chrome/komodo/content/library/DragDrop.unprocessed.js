/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

// Handle drag-drop of files onto the main Workspace window.
// this relies on using nsDragDrop.js

if (typeof(ko)=='undefined') {
    var ko = {};
}
ko.dragDrop = {};

(function() {
var _log = ko.logging.getLogger('ko.dragDrop');

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
    canDrop: function(event,session) {
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
