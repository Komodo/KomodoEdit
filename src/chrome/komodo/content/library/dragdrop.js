/* Copyright (c) 2000-2010 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

// Handle drag-drop of files onto the main Workspace window.
//
// Drag + Drop documentation:
// https://developer.mozilla.org/En/DragDrop/Drag_Operations

if (typeof(ko)=='undefined') {
    var ko = {};
}

if (typeof(ko.dragdrop)=='undefined') {
    ko.dragdrop = {};
} else {
    dump("WARNING: ko.dragDrop was already loaded - reloading it.\n");
}

(function() {

    const Cc = Components.classes;
    const Ci = Components.interfaces;
    Components.utils.import("resource://gre/modules/XPCOMUtils.jsm");
    
    var local = {};
    
    XPCOMUtils.defineLazyGetter(local, "log", function() ko.logging.getLogger("ko.dragDrop"));
    //local.log.setLevel(ko.logging.LOG_DEBUG);
    
    XPCOMUtils.defineLazyGetter(local, "bundle", function() Cc["@mozilla.org/intl/stringbundle;1"]
                                                            .getService(Ci.nsIStringBundleService)
                                                            .createBundle("chrome://komodo/locale/library.properties"));

    XPCOMUtils.defineLazyGetter(local, "fileProtocolHandler", function() Cc["@mozilla.org/network/io-service;1"]
                                                            .getService(Ci.nsIIOService)
                                                            .getProtocolHandler("file")
                                                            .QueryInterface(Ci.nsIFileProtocolHandler));

    /* ko.dragdrop items */

    this.focusWindow = function() {
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
            baseWin = window.QueryInterface(Ci.nsIInterfaceRequestor)
                            .getInterface(Ci.nsIWebNavigation)
                            .QueryInterface(Ci.nsIDocShellTreeItem)
                            .treeOwner
                            .QueryInterface(Ci.nsIInterfaceRequestor)
                            .getInterface(Ci.nsIBaseWindow);
            baseWin.setFocus();
        } catch(ex) {
            local.log.exception(ex,'Unable to get base window');
        }
        */
    };

    this.genericSupportedFlavours = [
            "application/x-moz-file",
            "application/x-moz-url",
            "text/x-moz-url",
            "text/uri-list",
            "text/unicode",
            "text/plain",
    ];

    this.windowSupportedFlavours = this.genericSupportedFlavours.concat([
            "komodo/tab",
    ]);

    this.isSupportedDropFlavour = function isSupportedDropFlavour(flavour) {
        switch(flavour) {
            case "application/x-moz-file":
            case "application/x-moz-url":
            case "text/x-moz-url":
            case "text/uri-list":
            case "text/html":
            case "text/plain":
                return true;
        }
        return false;
    };

    this.canDrop = function(event, session) {
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
    };

    this.onDragOver = function(event) {
        // If you want to allow a drop, you must prevent the default handling by
        // cancelling the event, or by returning false.
        return false;
    };

    this.onDrop = function(event) {
        var dataTransfer = event.dataTransfer;
        local.log.debug('onDrop:: mozItemCount: ' + dataTransfer.mozItemCount);

        var koDropDataList = ko.dragdrop.unpackDropData(event.dataTransfer);

        // Dropped text or cancelled the drop - we still want to focus on
        // Komodo.
        this.focusWindow();

        // Open any dropped URLs.
        var unhandledDropData = this.openDroppedUrls(koDropDataList);
        if (koDropDataList && koDropDataList.length != unhandledDropData.length) {
            // We're handling all (or at least part) of this drop data.
            event.preventDefault();
            return true;
        }

        return false;
    };

    /**
     * Class instance to hold dropped data information.
     */
    function KomodoDropData(dragType, dragData) {
        this.dragType = dragType;
        this.dragData = dragData;
        this.alternatives = {};

        this.isURL = false;
        this.isHTML = false;
        this.isSnippet = false;
        this.treatAsFileURL = false;  // Used to treat a http url as a file.

        // Helper variables for the getter functions.
        this._value = null;
        this._localPath = null;
        this._isRemoteFileURL = null;

        // Extract the dropped information.
        this.unpack(dragType, dragData);
    };

    KomodoDropData.prototype.__defineGetter__("value",
        function KoDropData_get_value() {
            return this._value;
        }
    );
    KomodoDropData.prototype.__defineSetter__("value",
        function KoDropData_set_value(val) {
            this._value = val;
            this._localPath = null;
            this._isRemoteFileURL = null;
        }
    );

    KomodoDropData.prototype.__defineGetter__("isFileURL",
        function KoDropData_get_isFileURL() {
            return this.isURL && (this.value.match(/^file:\/\//) ||
                                  this.treatAsFileURL);
        }
    );

    KomodoDropData.prototype.__defineGetter__("isRemoteFileURL",
        function KoDropData_get_isRemoteFileURL() {
            if (this._isRemoteFileURL == null) {
                this._isRemoteFileURL = (this.value.match(/^ftp:\/\//)) ||
                                        (this.value.match(/^ftps:\/\//)) ||
                                        (this.value.match(/^sftp:\/\//)) ||
                                        (this.value.match(/^scp:\/\//));
            }
            return this._isRemoteFileURL;
        }
    );

    KomodoDropData.prototype.__defineGetter__("isHttpURL",
        function KoDropData_get_isHttpURL() {
            return this.isURL && this.value.match(/^https?:\/\//);
        }
    );

    KomodoDropData.prototype.__defineGetter__("isImageURL",
        function KoDropData_get_isImageURL() {
            return this.isURL && this.value.match(/\.(png|jpe?g|gif)(\?.*)?$/i);
        }
    );

    KomodoDropData.prototype.__defineGetter__("isXpiURL",
        function KoDropData_get_isXpiURL() {
            return this.isURL && this.value.match(/\.xpi(\?.*)?$/i);
        }
    );

    KomodoDropData.prototype.__defineGetter__("isKpfURL",
        function KoDropData_get_isKpfURL() {
            return this.isURL && this.value.match(/\.kpf(\?.*)?$/i);
        }
    );

    KomodoDropData.prototype.__defineGetter__("isKsfURL",
        function KoDropData_get_isKsfURL() {
            return this.isURL && this.value.match(/\.ksf(\?.*)?$/i);
        }
    );

    KomodoDropData.prototype.__defineGetter__("isKpzURL",
        function KoDropData_get_isKpzURL() {
            return this.isURL && this.value.match(/\.kpz(\?.*)?$/i);
        }
    );

    KomodoDropData.prototype.__defineGetter__("isKomodoProjectURL",
        function KoDropData_get_isKomodoProjectURL() {
            return this.isURL && this.value.match(/\.komodoproject(\?.*)?$/i);
        }
    );

    KomodoDropData.prototype.__defineGetter__("isKomodoToolURL",
        function KoDropData_get_isKomodoToolURL() {
            return this.isURL && this.value.match(/\.komodotool(\?.*)?$/i);
        }
    );

    KomodoDropData.prototype.__defineGetter__("isText",
        function KoDropData_get_isText() {
            return ['text/plain', 'text/unicode'].indexOf(this.dragType) != -1;
        }
    );

    KomodoDropData.prototype.__defineGetter__("isZipURL",
        function KoDropData_get_isZipURL() {
            return this.isURL && this.value.match(/\.zip(\?.*)?/i);
        }
    );

    KomodoDropData.prototype.__defineGetter__("isDirectoryURL",
         function () {
            var uri = this.value;
            var koFileEx = Cc["@activestate.com/koFileEx;1"]
                .createInstance(Ci.koIFileEx);
            koFileEx.URI = this.value;
            return koFileEx.isDirectory;
        }
    );

    KomodoDropData.prototype.__defineGetter__("isDebuggerURL",
        function KoDropData_get_isDebuggerURL() {
            return this.isURL && this.value.match(/^dbgp:\/\//);
        }
    );
    KomodoDropData.prototype.__defineGetter__("isDebuggerFile",
        // Same as isDebuggerURL
        function KoDropData_get_isDebuggerFile() { return this.isDebuggerURL; }
    );

    KomodoDropData.prototype.__defineGetter__("isMacroURL",
        function KoDropData_get_isFileURL() {
            return this.isURL && this.value.match(/^macro:\/\//);
        }
    );

    KomodoDropData.prototype.__defineGetter__("localPath",
        function KoDropData_get_localPath() {
            if (this.isURL) {
                if (this._localPath == null) {
                    this._localPath = ko.uriparse.URIToLocalPath(this.value);
                }
                return this._localPath;
            }
            throw new Error("No path, as dropped data is not a URL!");
        }
    );

    KomodoDropData.prototype.__defineGetter__("localPathExists",
        function KoDropData_get_localPathExists() {
            try {
                return osSvc.path.exists(this.localPath());
            } catch (ex) {
                // Do nothing.
            }
            return false;
        }
    );
    KomodoDropData.prototype.__defineGetter__("isExistingFile",
        // Same as localPathExists
        function KoDropData_get_isDebuggerFile() { return this.localPathExists; }
    );


    KomodoDropData.prototype.__defineGetter__("isDir",
        function KoDropData_get_isDir() {
            try {
                return this.localPathExists() && osSvc.path.isdir(this.localPath());
            } catch (ex) {
                // Do nothing.
            }
            return false;
        }
    );

    KomodoDropData.prototype.__defineGetter__("isFileOrDir",
        function KoDropData_get_isFileOrDir() {
            return this.isURL && (this.isFileURL ||
                                  this.isRemoteFileURL ||
                                  this.isMacroURL /* not sure why macro is here */);
        }
    );

    /**
     * Add alternative KomodoDropData flavours.
     * @param {object} alternatives - a map of flavour to the alt KomodoDropData.
     */
    KomodoDropData.prototype.addAlternatives = function KomodoDropData_addAlternatives(alternatives) {
        this.alternatives = alternatives;
    };

    /**
     * Unpack the dropped data into something Komodo can use.
     *
     * @param {string} dragType - The type of data.
     * @param {object} dragData - The dropped Mozilla data.
     */
    KomodoDropData.prototype.unpack = function KoDropData_unpack(dragType, dragData) {
        switch(dragType) {
            case "komodo/tab":
                local.log.debug("unpack:: komodo/tab: " + dragData);
                // If it's dropped on a different Komodo window, then
                // move that tab to the target window.
                var sourceTab = dragData;
                var sourceTabbox = sourceTab.parentNode;
                while (sourceTabbox && sourceTabbox.localName != "tabbox") {
                    sourceTabbox = sourceTabbox.parentNode;
                }
                if (!sourceTabbox) {
                    return;
                }
                // Must hide the source drop indicator.
                sourceTabbox.tabs.dropIndicatorBar.collapsed = true;

                // Gather the data we need to open the view in the
                // target window.
                var sourceView = sourceTabbox.parentNode.currentView;
                var uri = sourceView.koDoc.file.URI;
                if (sourceTab.ownerDocument != document) {
                    // Moving a tab from one Komodo window to another.
                    var viewType = sourceView.getAttribute("type");
                    var line = (viewType == "editor" ? sourceView.currentLine : null);

                    // Close the source view first to ensure unsaved
                    // changes, etc. get handled first.
                    if (!sourceView.close()) {
                        return;
                    }

                    // Open the new view, maintaining cursor position.
                    if (line != null) {
                        ko.views.manager.doFileOpenAtLineAsync(
                            uri, line, viewType);
                    } else {
                        ko.views.manager.doFileOpenAsync(uri, viewType);
                    }
                    window.focus();
                } else {
                    this.value = uri;
                    this.isURL = true;
                }
                break;
            case "application/x-moz-file":
                local.log.debug("unpack:: x-moz-file: " + dragData);
                // Ensure we decode the URI, bug 72873.
                this.value = decodeURI(fileProtocolHandler.getURLSpecFromFile(dragData));
                this.isURL = true;
                break;
            case "application/x-moz-url":
            case "text/x-moz-url":
            case "text/uri-list":
                local.log.debug("unpack:: x-moz-url: " + dragData);
                // Ensure we decode the URI, bug 72873.
                // Note: x-moz-url has the format: "Url\nTitle\n"
                this.value = decodeURI(dragData.split("\n")[0]);
                this.isURL = true;
                break;
            case "application/x-komodo-snippet":
                var snippet_id = dragData;
                this.snippet = ko.toolbox2.findToolById(snippet_id);
                this.isSnippet = true;
                break;
            case "text/html":
            case "text/plain":
                this.value = dragData;
                if (dragType == "text/html") {
                    this.isHTML = true;
                }
                local.log.debug('dropped data is ['+dragData+']');
                // See if it looks like a file or a URL.
                var is_windows = (navigator.platform == 'Win32');
                if (dragData.search("://") >= 0) {
                    // Looks like a URL to me.
                    this.isURL = true;
                // Other file or URL types.
                } else if (dragData.match(/^file:\/[\w|\.]/)) {
                    // unix style file:/home.... url from drag/drop
                    this.isURL = true;
                    this.value = ko.uriparse.pathToURI(dragData.slice(5));
                } else if ((is_windows && dragData.match(/^(\\|[a-z]:)\\\w+/i)) ||
                           (!is_windows && dragData.match(/^\/\w+/i))) {
                    // Windows or Unix style filepaths.
                    try {
                        this.value = ko.uriparse.localPathToURI(dragData);
                        this.isURL = true;
                    } catch (e) {
                        local.log.debug('this is not a file path: ['+this.value+']');
                        return;
                    }
                }
                if (this.isURL) {
                    // Ensure the URI is properly decoded. Fixes bug:
                    // http://bugs.activestate.com/show_bug.cgi?id=72873
                    this.value = decodeURI(this.value);
                }
                break;
            default:
                local.log.warn("KoDropData:: Unexpected drag flavour: " + dragType);
                break;
        }
    };

    /**
     * Class instance to hold dropped Komodo data.
     */
    this.KoDropData = KomodoDropData;

    /**
     * Unpack the dropped data into a Komodo specific data structure.
     * 
     * @param dataTransfer {Ci.nsIDOMDataTransfer} - The data.
     * @param {array} acceptedFlavours - Optional - list of supported data types.
     * @returns {array} - Returns an array of {ko.dragdrop.KoDropData}
     */
    this.unpackDropData = function unpackDropData(dataTransfer, acceptedFlavours) {
        if (typeof(acceptedFlavours) == 'undefined' || acceptedFlavours == null) {
            acceptedFlavours = ko.dragdrop.windowSupportedFlavours;
        }

        var ko_drop_data = [];
        for (var i=0; i < dataTransfer.mozItemCount; i++) {
            var mozTypes = dataTransfer.mozTypesAt(i);
            if (!mozTypes.length) {
                continue;
            }
            var supportedTypes = acceptedFlavours.filter(
                         function(value) mozTypes.contains(value));
            if (!supportedTypes.length) {
                local.log.info("unpackDropData:: no supported flavours for item  " + i
                          + ":" + mozTypes);
                continue;
            }
            // Take the first type - as it's the best of the types we wanted.
            var mozType;
            var mozDragData;
            var alternatives = null;
            var koDropData = null;
            for (var j=0; j < supportedTypes.length; j++) {
                mozType = supportedTypes[j];
                // get flavor j for item i
                mozDragData = dataTransfer.mozGetDataAt(mozType, i);
                try {
                    if (koDropData == null) {
                        koDropData = new KomodoDropData(mozType, mozDragData);
                        local.log.debug("unpackDropData:: best flavour: " + mozType);
                        ko_drop_data.push(koDropData);
                    } else {
                        if (alternatives == null) {
                            alternatives = {};
                        }
                        alternatives[mozType] = new KomodoDropData(mozType, mozDragData);
                        local.log.debug("unpackDropData:: alternative flavour: " + mozType);
                    }
                } catch (ex) {
                    // Was not valid drop data.
                    local.log.info("unpackDropData:: could not unpack: " + mozType + ": " + mozDragData);
                }
            }
            if (alternatives) {
                koDropData.addAlternatives(alternatives);
            }
        }
        return ko_drop_data;
    };


    /**
     * Convert the Komodo dropped data - this may involve:
     *   o viewing the source of HTTP urls
     *   o converting mapped urls
     *   o treating dropped URLs as text
     *
     * @param {array} koDropDataList - Array of KomodoDropData items.
     * @returns {array} - Array of converted KomodoDropData items.
     */
    this.convertKoDropData = function convertKoDropData(koDropDataList) {
        var koDropData;
        var newDropDataList = [];
        var uri;
        for (var i=0; i < koDropDataList.length; i++) {
            koDropData = koDropDataList[i];
            if (!koDropData.isURL) {
                // We only care about dropped URLs - leave the rest as is.
                newDropDataList.push(koDropData);
                continue;
            }
            local.log.debug('dropped URL is ['+koDropData.value+']');
            // See if this is a mapped uri.
            while (1) {
                koDropData.value = ko.uriparse.getMappedURI(koDropData.value);
                local.log.debug('mapped URL is ['+koDropData.value+']');
                if (koDropData.isHttpURL &&
                    !koDropData.isXpiURL &&
                    !koDropData.isKpzURL &&
                    !koDropData.isKpfURL &&
                    !koDropData.isKsfURL &&
                    !koDropData.isKomodoProjectURL) {
                    // Ask the user to if they'd like to:
                    //   * view the URL source
                    //   * add a uri mapping
                    //   * drop the URL as text
                    var title = local.bundle.GetStringFromName("youHaveDroppedAUrlOntoKomodo.title");
                    var prompt = local.bundle.GetStringFromName("youHaveDroppedAUrlOntoKomodo.prompt");
                    var cancel = local.bundle.GetStringFromName("cancelButton.label");
                    var viewsource = local.bundle.GetStringFromName("viewSourceButton.label");
                    var viewsourceAccesskey = local.bundle.GetStringFromName("viewSourceButton.accesskey");
                    var viewsourceTooltiptext = local.bundle.GetStringFromName("viewSourceButton.tooltiptext");
                    var mapthisuri = local.bundle.GetStringFromName("mapThisUriButton.label");
                    var mapthisuriAccesskey = local.bundle.GetStringFromName("mapThisUriButton.accesskey");
                    var mapthisuriTooltiptext = local.bundle.GetStringFromName("mapThisUriButton.tooltiptext");
                    var dropastext = local.bundle.GetStringFromName("dropAsTextButton.label");
                    var dropastextAccesskey = local.bundle.GetStringFromName("dropAsTextButton.accesskey");
                    var dropastextTooltiptext = local.bundle.GetStringFromName("dropAsTextButton.tooltiptext");
                    var response = ko.dialogs.customButtons(prompt,
                                                            [[viewsource, viewsourceAccesskey, viewsourceTooltiptext],
                                                             [mapthisuri, mapthisuriAccesskey, mapthisuriTooltiptext],
                                                             [dropastext, dropastextAccesskey, dropastextTooltiptext]],
                                                            viewsource,
                                                            null,
                                                            title,
                                                            "dragdrop_uri");
                    if (!response || response == cancel) {
                        // Returning an empty list will effectively cancel the drop.
                        return [];
                    } else if (response == mapthisuri) {
                        if (ko.uriparse.addMappedURI(koDropData.value)) {
                            // allow another loop in the while
                            continue;
                        }
                    } else if (response == viewsource) {
                        // Mark it as a URL that should be opened as a file view.
                        koDropData.treatAsFileURL = true;
                    } else if (response == dropastext) {
                        koDropData.isURL = false;
                    } else {
                        local.log.error("convertMappedURIs:: unexpected response of "
                                   + response);
                        return [];
                    }
                }
                break;
            }
            newDropDataList.push(koDropData);
        }
        return newDropDataList;
    };


    /**
     * Open all Komodo dropped files or URLs and then return the unhandled
     * list of koDropData items.
     *
     * @param {array} koDropDataList - Array of KomodoDropData items.
     * @returns {array} - Array of unhandled (unopened) KomodoDropData items.
     */
    this.openDroppedUrls = function openDroppedUrls(koDropDataList) {
        // Convert the data (uri mapping, treat as text, etc...).
        koDropDataList = ko.dragdrop.convertKoDropData(koDropDataList);

        var open_list = [];
        var unhandled_list = [];
        var koDropData;

        for (var i=0; i < koDropDataList.length; i++) {
            koDropData = koDropDataList[i];
            //dump('koDropData.isURL: ' + koDropData.isURL + '\n');
            //dump('koDropData.isFileURL: ' + koDropData.isFileURL + '\n');
            if (koDropData.isURL) {
                if ((koDropData.isFileURL) ||
                    (koDropData.isRemoteFileURL) ||
                    (koDropData.isKsfURL) ||
                    (koDropData.isKpzURL) ||
                    (koDropData.isXpiURL)) {
                    open_list.push(koDropData);
                    continue;
                }
            }
            unhandled_list.push(koDropData);
        }

        if (open_list.length) {
            local.log.info('openDroppedUrls:: opening ' + open_list.length + ' items');
            // Open the editor views.
            var editor_list = open_list.filter(function(element) { return !element.isImageURL });
            if (editor_list) {
                var editor_uris = editor_list.map(function(element) { return element.value; });
                ko.open.multipleURIs(editor_uris);
            }
            // Open any images in a browser view.
            var browser_list = open_list.filter(function(element) { return element.isImageURL });
            if (browser_list) {
                var browser_uris = browser_list.map(function(element) { return element.value; });
                ko.open.multipleURIs(browser_uris, "browser");
            }
        }

        return unhandled_list;
    };

}).apply(ko.dragdrop);
