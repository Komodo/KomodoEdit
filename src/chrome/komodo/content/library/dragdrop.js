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

    var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
                    .getService(Components.interfaces.nsIStringBundleService)
                    .createBundle("chrome://komodo/locale/library.properties");
    var _log = ko.logging.getLogger('ko.dragDrop');
    //_log.setLevel(ko.logging.LOG_DEBUG);

    var ioService = Components.classes["@mozilla.org/network/io-service;1"]
                           .getService(Components.interfaces.nsIIOService);
    var fileProtocolHandler = ioService.getProtocolHandler("file");
    fileProtocolHandler.QueryInterface(Components.interfaces.nsIFileProtocolHandler);

    /* ko.dragdrop items */

    this.canHandleMultipleItems = true;

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
    };

    this.genericSupportedFlavours = [
            "application/x-moz-file",
            "text/x-moz-url",
            "text/uri-list",
            "text/plain",
    ];

    this.isSupportedDropFlavour = function isSupportedDropFlavour(flavour) {
        switch(flavour) {
            case "application/x-moz-file":
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
        _log.debug('onDrop:: mozItemCount: ' + dataTransfer.mozItemCount);

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
            return this.isURL && this.value.match(/\.(png|jpe?g|gif)$/i);
        }
    );

    KomodoDropData.prototype.__defineGetter__("isXpiURL",
        function KoDropData_get_isXpiURL() {
            return this.isURL && this.value.match(/\.xpi$/i);
        }
    );

    KomodoDropData.prototype.__defineGetter__("isKpfURL",
        function KoDropData_get_isKpfURL() {
            return this.isURL && this.value.match(/\.kpf$/i);
        }
    );

    KomodoDropData.prototype.__defineGetter__("isKsfURL",
        function KoDropData_get_isKsfURL() {
            return this.isURL && this.value.match(/\.ksf$/i);
        }
    );

    KomodoDropData.prototype.__defineGetter__("isKpzURL",
        function KoDropData_get_isKpzURL() {
            return this.isURL && this.value.match(/\.kpz$/i);
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
     * @param alternatives {object} - a map of flavour to the alt KomodoDropData.
     */
    KomodoDropData.prototype.addAlternatives = function KomodoDropData_addAlternatives(alternatives) {
        this.alternatives = alternatives;
    };

    /**
     * Unpack the dropped data into something Komodo can use.
     *
     * @param dragType {string} - The type of data.
     * @param dragData {object} - The dropped Mozilla data.
     */
    KomodoDropData.prototype.unpack = function KoDropData_unpack(dragType, dragData) {
        switch(dragType) {
            case "application/x-moz-file":
                _log.debug("onDrop:: x-moz-file: " + dragData);
                this.value = fileProtocolHandler.getURLSpecFromFile(dragData);
                this.isURL = true;
                break;
            case "application/x-komodo-snippet":
                try {
                    var nativeJSON = Components.classes["@mozilla.org/dom/json;1"]
                                        .createInstance(Components.interfaces.nsIJSON);
                    var data = nativeJSON.decode(dragData);
                    var projectType = data.toolboxType;
                    var project = null;
                    if (projectType == 'project') {
                        project = ko.projects.manager.getProjectByURL(data.projectURL);
                    } else {
                        var psvc = Components.classes["@activestate.com/koPartService;1"]
                            .getService(Components.interfaces.koIPartService);
                        project = projectType == 'toolbox' ? psvc.toolbox : psvc.sharedToolbox;
                    }
                    if (project) {
                        this.value = project.getChildById(data.snippetID);
                        this.isSnippet = true;
                    }
                } catch(e) {
                    _log.debug("DragDrop.js::unpackData: application/x-komodo-snippet: " + e);
                }
                break;
            case "text/html":
            case "text/plain":
                this.value = dragData;
                if (dragType == "text/html") {
                    this.isHTML = true;
                }
                _log.debug('dropped data is ['+dragData+']');
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
                        _log.debug('this is not a file path: ['+this.value+']');
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
                _log.warn("KoDropData:: Unexpected drag flavour: " + dragType);
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
     * @param dataTransfer {Components.interfaces.nsIDOMDataTransfer} - The data.
     * @param acceptedFlavours {array} - Optional - list of supported data types.
     * @returns {array} - Returns an array of {ko.dragdrop.KoDropData}
     */
    this.unpackDropData = function unpackDropData(dataTransfer, acceptedFlavours) {
        if (typeof(acceptedFlavours) == 'undefined' || acceptedFlavours == null) {
            acceptedFlavours = ko.dragdrop.genericSupportedFlavours;
        }

        var ko_drop_data = [];
        for (var i=0; i < dataTransfer.mozItemCount; i++) {
            var mozTypes = dataTransfer.mozTypesAt(i);
            if (!mozTypes.length) {
                continue;
            }
            // Take the first type - as it's the best of the types we wanted.
            var mozType;
            var mozDragData;
            var alternatives = null;
            var koDropData = null;
            for (var j=0; j < mozTypes.length; j++) {
                mozType = mozTypes[j];
                if (acceptedFlavours.indexOf(mozType) < 0) {
                    _log.info("onDrop:: unsupported flavour: " + mozType);
                    continue;
                }
                mozDragData = dataTransfer.mozGetDataAt(mozType, i);
                try {
                    if (koDropData == null) {
                        koDropData = new KomodoDropData(mozType, mozDragData);
                        _log.debug("onDrop:: best flavour: " + mozType);
                        ko_drop_data.push(koDropData);
                    } else {
                        if (alternatives == null) {
                            alternatives = {};
                        }
                        alternatives[mozType] = new KomodoDropData(mozType, mozDragData);
                        _log.debug("onDrop:: alternative flavour: " + mozType);
                    }
                } catch (ex) {
                    // Was not valid drop data.
                    _log.info("onDrop:: could not unpack: " + mozType + ": " + mozDragData);
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
     * @param koDropDataList {array} - Array of KomodoDropData items.
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
            _log.debug('dropped URL is ['+koDropData.value+']');
            // See if this is a mapped uri.
            while (1) {
                koDropData.value = ko.uriparse.getMappedURI(koDropData.value);
                _log.debug('mapped URL is ['+koDropData.value+']');
                if (koDropData.isHttpURL &&
                    !koDropData.isXpiURL &&
                    !koDropData.isKpzURL &&
                    !koDropData.isKpfURL) {
                    // Ask the user to if they'd like to:
                    //   * view the URL source
                    //   * add a uri mapping
                    //   * drop the URL as text
                    var title = _bundle.GetStringFromName("youHaveDroppedAUrlOntoKomodo.title");
                    var prompt = _bundle.GetStringFromName("youHaveDroppedAUrlOntoKomodo.prompt");
                    var cancel = _bundle.GetStringFromName("cancelButton.label");
                    var viewsource = _bundle.GetStringFromName("viewSourceButton.label");
                    var viewsourceAccesskey = _bundle.GetStringFromName("viewSourceButton.accesskey");
                    var viewsourceTooltiptext = _bundle.GetStringFromName("viewSourceButton.tooltiptext");
                    var mapthisuri = _bundle.GetStringFromName("mapThisUriButton.label");
                    var mapthisuriAccesskey = _bundle.GetStringFromName("mapThisUriButton.accesskey");
                    var mapthisuriTooltiptext = _bundle.GetStringFromName("mapThisUriButton.tooltiptext");
                    var dropastext = _bundle.GetStringFromName("dropAsTextButton.label");
                    var dropastextAccesskey = _bundle.GetStringFromName("dropAsTextButton.accesskey");
                    var dropastextTooltiptext = _bundle.GetStringFromName("dropAsTextButton.tooltiptext");
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
                        _log.error("convertMappedURIs:: unexpected response of "
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
     * @param koDropDataList {array} - Array of KomodoDropData items.
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
            dump('koDropData.isURL: ' + koDropData.isURL + '\n');
            dump('koDropData.isFileURL: ' + koDropData.isFileURL + '\n');
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
            _log.info('onDrop:: opening ' + open_list.length + ' items');
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

// Make an easier to use namespace alias.
ko.dd = ko.dragdrop;
