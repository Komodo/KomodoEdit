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

var bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
    .getService(Components.interfaces.nsIStringBundleService)
    .createBundle("chrome://komodo/locale/dialogs/filebrowser/filebrowser.properties");

// Globals
var globalPrefService;//defined in koGlobalOverlay.js
var globalPrefs = null;

var log = ko.logging.getLogger('filepicker.remote');
//log.setLevel(ko.logging.LOG_DEBUG);

var timeSvc = Components.classes["@activestate.com/koTime;1"].
              getService(Components.interfaces.koITime);

const XUL_NS = "http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul";

const nsILocalFile = Components.interfaces.nsILocalFile;
const nsLocalFile_CONTRACTID = "@mozilla.org/file/local;1";
const nsIFile = Components.interfaces.nsIFile;

const nsIFilePicker     = Components.interfaces.nsIFilePicker;
const modeGetFolder = nsIFilePicker.modeGetFolder;
const modeOpen      = nsIFilePicker.modeOpen;
const modeSave      = nsIFilePicker.modeSave;
const returnCancel      = nsIFilePicker.returnCancel;
const returnOK      = nsIFilePicker.returnOK;
const returnReplace      = nsIFilePicker.returnReplace;

const nsIDirectoryServiceProvider = Components.interfaces.nsIDirectoryServiceProvider;
const nsIDirectoryServiceProvider_CONTRACTID = "@mozilla.org/file/directory_service;1";
const nsITreeBoxObject = Components.interfaces.nsITreeBoxObject;

const remotefile_scheme_types = [ "ftp",
                                  "ftps",
                                  "sftp",
                                  "scp",
                                ];

// for now, we're only doing remote file browsing with this file browser
var RemoteFileBrowserOnly = true;
const localDrives = bundle.GetStringFromName("localDrives.label");
var _fileListSep = "; ";
var sfile = null;
var retvals;
var filePickerMode;
var treeView;
var helpTag;

var textInput;
var okButton;
var labelStatus;

function localFile(path) {
    this._sfile = Components.classes[nsLocalFile_CONTRACTID].createInstance(nsILocalFile);
    this._haveChildren = 0;
    this._directories = [];
    this._filelist = [];
    this._parent = null;
    if (path) this.init(path);
}

localFile.prototype = {
    get URL() {
        return this._sfile.URL;
    },

    get path() { return this._sfile.path; },

    get parent() {
        if (!this._parent && this._sfile.parent) {
            this._parent = new localFile();
            this._parent._sfile = this._sfile.parent;
        }
        return this._parent;
    },

    get isDirectory() { return this.exists() && this._sfile.isDirectory(); },

    get isFile() { return this.exists() && this._sfile.isFile(); },

    get isSymlink() { return this.exists() && this._sfile.isSymlink(); },

    get fileSize() { return this._sfile.fileSize; },

    get lastModifiedTime() {return this._sfile.lastModifiedTime; },

    get target() { return this._sfile.target; },

    get leafName() { return this._sfile.leafName; },

    set followLinks(v) { this._sfile.followLinks = v; },
    get followLinks() { return this._sfile.followLinks; },

    get directories() {
        if (!this._haveChildren) this.initChildren();
        return this._directories;
    },
    get filelist() {
        if (!this._haveChildren) this.initChildren();
        return this._filelist;
    },
    createDirectory: function(dirName) {
        // what are the correct permissions to create a directory with?
        if (!this.isDirectory) return false;
        try {
            log.debug("createDirectory: current dir: "+this.path+", making "+dirName);
            // XXX funky nsIFile behaviour, you must append the new directory name
            // first, then call createUnique with the same directory name again!
            var file = this.clone();
            file._sfile.append(dirName);
            file._sfile.createUnique(file._sfile.DIRECTORY_TYPE, /*0755*/493);
        } catch (e) {
            //alert(e);
            ko.dialogs.alert(bundle.formatStringFromName("unableToCreateDirectory.alert",
                [this.lastError()], 1));
            return false;
        }
        return true;
    },
    remove: function(recursive) {
        try {
            this._sfile.remove(recursive);
            return true;
        } catch (e) {
            ko.dialogs.alert(bundle.formatStringFromName("unableToRemove.alert",
                [this.path, this.lastError()], 2));
            return false;
        }
    },
    initChildren: function() {
        this._directories = [];
        this._filelist = [];
        var dirEntries = this._sfile.QueryInterface(nsIFile).directoryEntries;
        var nextFile = null;
        while (dirEntries.hasMoreElements()) {
          nextFile = dirEntries.getNext().QueryInterface(nsIFile);
          // XXXjag hack for bug 82355 till symlink handling is fixed (bug 57995)
          var isDir = false;
          try {
            isDir = nextFile.isDirectory();
          } catch (e) {
            // this here to fool the rest of the code into thinking
            // this is a nsIFile object
            log.debug("initChildren: nextfile : "+nextFile.leafName);
            nextFile = { leafName : nextFile.leafName,
                         fileSize : 0,
                         lastModifiedTime : 0,
                         isHidden: function() { return false; } };
          }
          // end of hack
          var fileobj = new Object();
          fileobj.file = new localFile();
          fileobj.file._parent = this;
          fileobj.file._sfile = nextFile;
          if (isDir) {
            this._directories[this._directories.length] = fileobj;
          } else {
            this._filelist[this._filelist.length] = fileobj;
          }
        }
        this._haveChildren = 1;
    },

    init: function(path) {
        this._sfile.initWithPath(path);
        this._sfile.normalize();
    },
    isHidden: function() {
        return this._sfile.isHidden();
    },
    exists: function() {
        return this._sfile.exists();
    },
    clone: function() {
        var newfile = new localFile();
        newfile._sfile = this._sfile.clone().QueryInterface(nsILocalFile);
        newfile._parent = this._parent;
        newfile._directories = this._directories;
        newfile._filelist = this._filelist;
        return newfile;
    },
    equals: function(file) {
        return this._sfile.equals(file._sfile);
    },
    getChild: function(URL) {
        var i;
        for (i = 0; i < this._directories.length; i++) {
            if (this._directories[i].file.URL == URL) return this._directories[i].file;
        }
        for (i = 0; i < this._filelist.length; i++) {
            if (this._filelist[i].file.URL == URL) return this._filelist[i].file;
        }
        return null;
    },
    appendRelativePath: function(input) {
        this._sfile.appendRelativePath(input);
    },
    moveTo: function(parent, newname) {
        try {
            this._sfile.moveTo(parent, newname);
            return true;
        } catch (e) {
            ko.dialogs.alert(bundle.formatStringFromName("unableToRenameFile.alert",
                [this.lastError()], 1));
            return false;
        }
    },
    disconnect: function() {
    },
    refresh: function() {
    },
    lastError: function() {return "";}
}



// Wrapper class for providing nsILocalFile functionality for the
// RemoteFile object
function RemoteFileInfo(rfinfo) {
    this._rfinfo = rfinfo;
    this._followLinks = 1;
}
RemoteFileInfo.prototype = {
    get URL()                     { return getUriForPath(this.path, 0) },
    get path()                    { return this._rfinfo.getFilepath(); },
    get leafName()                { return this._rfinfo.getFilename(); },
    get fileSize()                { return this._rfinfo.getFileSize(); },
    // our RemoteFileInfo returns seconds rather than milliseconds, which is
    // contrary to nsIFile idl, but eases use in the rest of komodo which is
    // written to use seconds.  However, our treeview expects milliseconds
    // so we make the tranformation here.
    get lastModifiedTime()        { return this._rfinfo.getModifiedTime() * 1000; },
    get timeLastRefreshed()       { return this._rfinfo.getTimeRefreshed(); },
    get target()                  { return this._rfinfo.getLinkTarget(); },
    exists: function()            { return (this._rfinfo != null); },
    isDirectory: function()       { return this._rfinfo.isDirectory(); },
    isFile: function()            { return this._rfinfo.isFile(); },
    isSymlink: function()         { return this._rfinfo.isSymlink(); },
    isHidden: function()          { return this._rfinfo.isHidden(); },
    equals: function(compareObj)  { return this.path == compareObj.path; },

    // getChildren returns an array of koIRemoteFileInfo objects
    getChildren: function()       {
        var tempObj = new Object(); // Holds the array size (not needed)
        return this._rfinfo.getChildren(tempObj);
    },
    needsDirectoryListing: function() { return this._rfinfo.needsDirectoryListing(); },

    set followLinks(v) { this._followLinks = v; },
    get followLinks() { return this._followLinks; }
}

// This Dummy class is used for files that do not exist yet, but we still want to
// have a RemoteFile object that represents the path in the remote server.
// Used when saving to a new file that does not exist.
function DummyRemoteFileInfo(path) {
    this._path = path;
}
DummyRemoteFileInfo.prototype = {
    get URL()                     { return getUriForPath(this.path, 0) },
    get path()                    { return this._path; },
    get leafName() {
        var rpos = this.path.lastIndexOf('/');
        if (rpos >= 0)
            return this.path.substring(rpos+1);
        return this.path;
    },
    get fileSize()                { return 0; },
    get lastModifiedTime()        { return 0; },
    get timeLastRefreshed()       { return 0; },
    get target()                  { return ""; },
    exists: function()            { return 0; },
    isDirectory: function()       { return 0; },
    isFile: function()            { return 0; },
    isSymlink: function()         { return 0; },
    equals: function(compareObj)  { return this == compareObj; },
    isHidden: function()          { return 0; },
    getChildren: function()       { return null; },
    needsDirectoryListing: function() { return false; },
    set followLinks(v) {  },
    get followLinks() {  }
}

function RemoteFile(path) {
    log.debug("RemoteFile.constructor("+path+")");
    if (path && typeof(path)!="undefined")
        this.init(path);
}

// The following two lines ensure proper inheritance (see Flanagan, p. 144).
RemoteFile.prototype = new localFile();
RemoteFile.prototype.constructor = RemoteFile;

RemoteFile.prototype.__defineGetter__("parent",
function()
{
    if (!this._parent) {
        this._parent = new RemoteFile(serverInfo.connection.getParentPath(this.path));
    }
    return this._parent;
});

RemoteFile.prototype.init = function(path) {
    log.debug("RemoteFile.init: path '"+path+"'");
    var rfinfo = serverInfo.connection.list(path, 0);
    if (rfinfo) {
        this.initWithRFInfo(rfinfo);
    } else {
        // Note: This path does not exist, create a dummy object for it
        this._sfile = new DummyRemoteFileInfo(path);
    }
}
RemoteFile.prototype.initWithRFInfo = function(rfinfo) {
    log.debug("RemoteFile.initWithRFInfo");
    this._sfile = new RemoteFileInfo(rfinfo);
}
RemoteFile.prototype.initChildren = function() {
    this._directories = [];
    this._filelist = [];
    var nextFile;
    var file_rfinfo;
    // Ensure the directory has been populated
    if (this.isDirectory && this._sfile.needsDirectoryListing()) {
        log.debug("initChildren: directory needsDirectoryListing");
        this.refresh();
    }
    // Note: dirEntries is a list of koIRemoteFileInfo objects
    var dirEntries = this._sfile.getChildren();
    log.debug("RemoteFile.initChildren: num children is "+dirEntries.length);
    for (var i = 0; i < dirEntries.length; i++) {
      file_rfinfo = dirEntries[i];
      log.debug("RemoteFile.initChildren: child is "+file_rfinfo.getFilepath());
      var fileobj               = new Object();
      fileobj.file              = new RemoteFile(file_rfinfo.getFilepath());
      fileobj.file._parent      = this;
      //fileobj.file._sfile       = nextFile;
      fileobj.cachedName        = fileobj.file.leafName;
      fileobj.cachedDate        = fileobj.file.lastModifiedTime;
      fileobj.cachedDateText    = formatDate(fileobj.cachedDate);
      fileobj.cachedSize        = fileobj.file.fileSize;
      if (fileobj.file.isDirectory) {
        this._directories[this._directories.length] = fileobj;
      } else {
        this._filelist[this._filelist.length] = fileobj;
      }
    }
    this._haveChildren = 1;
}
RemoteFile.prototype.clone = function() {
    var newfile = new RemoteFile(this.path);
    newfile._parent = this._parent;
    newfile._directories = this._directories;
    newfile._filelist = this._filelist;
    return newfile;
}
RemoteFile.prototype.refresh = function() {
    log.debug("RemoteFile.refresh "+this.path);
    // 1 Ensures we get refreshed
    this.initWithRFInfo(serverInfo.connection.list(this.path, 1));
}
RemoteFile.prototype.createDirectory = function(dirName) {
    // what are the correct permissions to create a directory with?
    if (!this.isDirectory) return false;
    try {
        log.debug("RemoteFile.createDirectory: current dir: "+this.path+", making "+dirName);
        serverInfo.connection.createDirectory(this.path+"/"+dirName, /*0755*/493);
    } catch (e) {
        ko.dialogs.alert(bundle.formatStringFromName("unableToCreateDirectory.alert",
            [this.lastError()], 1));
        return false;
    }
    return true;
}

// Remove the contents of a directory and all it's sub-directories
function removeRemoteFilesRecursively(path)
{
    log.debug("removeRecursively: path '"+path+"'");
    var file_rfinfo;
    var directory_rfinfo = serverInfo.connection.list(path, 1);
    if (!directory_rfinfo) {
        log.debug("removeRecursively: Path does not exist!");
        return;
    }
    var tempObj = new Object(); // Holds the array size (not needed)
    var dirEntries = directory_rfinfo.getChildren(tempObj);

    // Note: dirEntries is a list of koIRemoteFileInfo objects
    if (dirEntries.length > 0) {
        log.debug("removeRecursively: Removing sub contents ("+dirEntries.length+" entries).");
        for (var i = 0; i < dirEntries.length; i++) {
            file_rfinfo = dirEntries[i];
            if (!file_rfinfo.isDirectory()) {
                serverInfo.connection.removeFile(file_rfinfo.getFilepath());
            } else {
                removeRemoteFilesRecursively(file_rfinfo.getFilepath());
            }
        }
    }
    serverInfo.connection.removeDirectory(path);
}

RemoteFile.prototype.remove = function(recursive) {
    try {
        if (this.isDirectory) {
            log.debug("RemoteFile.remove: dir '"+this.path+"'");
            removeRemoteFilesRecursively(this.path);
        } else {
            log.debug("RemoteFile.remove: file '"+this.path+"'");
            serverInfo.connection.removeFile(this.path);
        }
        return true;
    } catch (e) {
        ko.dialogs.alert(bundle.formatStringFromName("unableToRemove.alert",
            [this.path, this.lastError()], 2));
        return false;
    }
}
RemoteFile.prototype.moveTo = function(parent, newname) {
    // Also known as 'Rename'
    if (!parent) {
        parent = this.parent;
    }
    var newPath = this.parent.path+"/"+newname;
    try {
        serverInfo.connection.rename(this.path, newPath);
        return true;
    } catch (e) {
        ko.dialogs.alert(bundle.formatStringFromName("unableToRenameFile.alert",
            [this.lastError()], 1));
        return false;
    }
},
RemoteFile.prototype.lastError = function() {return serverInfo.connection.lastError;}


function filebrowserLoad() {
  globalPrefService = Components.classes["@activestate.com/koPrefService;1"].
    getService(Components.interfaces.koIPrefService);
  globalPrefs = globalPrefService.prefs;

  textInput = document.getElementById("textInput");
  okButton = document.getElementById("ok");
  labelStatus = document.getElementById("labelStatus");

  treeView = new filebrowseview();
  treeView.selectionCallback = onSelect;

  if (window.arguments) {
    var o = window.arguments[0];
    retvals = o.retvals; /* set this to a global var so we can set return values */
    const title = o.title;
    filePickerMode = o.mode;
    if (o.displayDirectory) {
      const directory = o.displayDirectory.path;
    }
    const initialText = o.defaultString;
    const filterTitles = o.filters.titles;
    const filterTypes = o.filters.types;
    const numFilters = filterTitles.length;
    helpTag = o.helpTag;

    document.title = title;

    if (initialText && filePickerMode == modeSave) {
      textInput.value = initialText;
    }
  }

  if ((filePickerMode == modeOpen) ||
      (filePickerMode == modeSave)) {

    if (filePickerMode == modeSave)
        treeView.singleSelect = true;

    treeView.setFilter(filterTypes[0]);

    /* build filter popup */
    var filterPopup = document.getElementById("filterMenu");//document.createElement("menupopup");

    for (var i = 0; i < numFilters; i++) {
      var menuItem = document.createElement("menuitem");
      menuItem.setAttribute("label", filterTitles[i] + " (" + filterTypes[i] + ")");
      menuItem.setAttribute("filters", filterTypes[i]);
      filterPopup.appendChild(menuItem);
    }

    var filterMenuList = document.getElementById("filterMenuList");
    //filterMenuList.appendChild(filterPopup);
    if (numFilters > 0)
      filterMenuList.selectedIndex = 0;
    var filterBox = document.getElementById("filterBox");
    filterBox.removeAttribute("hidden");
  } else if (filePickerMode == modeGetFolder) {
    treeView.singleSelect = true;
    treeView.showOnlyDirectories = true;
    document.title = bundle.GetStringFromName("openRemoteFolder");
    document.getElementById("fileName.label").value = bundle.GetStringFromName("folderName");
  }

  // start out with a filename sort
  handleColumnClick("FilenameColumn");

  try {
    var buttonLabel = getOKAction();
    okButton.setAttribute("label", buttonLabel);
  } catch (exception) {
    // keep it set to "OK"
  }

  // setup the dialogOverlay.xul button handlers
  doSetOKCancel(onOK, onCancel);
  retvals.buttonStatus = returnCancel;

  var tree = document.getElementById("directoryTree");
  tree.treeBoxObject.view = treeView;

  // Start out with the ok button disabled since nothing will be
  // selected and nothing will be in the text field.
  okButton.disabled = true;
  textInput.focus();

  // Load the server information from preferences into the servers object
  loadServerPrefs();

  // Copy server details from uri into serverInfo
  if (directory) {
    
    //url_parts = setServerInfoFromUri(directory);
    setServerInfoUsingUri(directory);

    // Load the servers menulist, and select the one with this alias
    setupServerMenuList(serverInfo.serveralias);
  
    // Set the current server variable from what we know about the server info
    // setCurrentServerFromServerInfo();

    try {
        connectToServer();
        // This allows the window to show onscreen before we begin
        // loading the file list
        setTimeout(setInitialDirectory, 0, serverInfo.initial_path);
    } catch (e) {
        var lastErrorSvc = Components.classes["@activestate.com/koLastErrorService;1"].
                                       getService(Components.interfaces.koILastErrorService);
        if (lastErrorSvc.getLastErrorMessage() != 'Login cancelled by user.')
            alert(bundle.formatStringFromName("error.alert",
                [lastErrorSvc.getLastErrorMessage()], 1));
    }
  } else {
    setupServerMenuList();
  }
}

function filebrowserClose() {
    closeFTP();
}


// Split the URI into seperate components
// "uri" is the remote url specifiying the server connetion details
//    Format: "protocol://[username:password@]servername:port/path_to_directory"
// or Format: "protocol://server_alias/path_to_directory"
//  - Protocol used (ex. "ftp", "ftps", "sftp", "scp")
//  - Remote server username and password (optional)
//  - Remote server name and port (ex. "testserver:22")
//  - Server alias can be used instead of username, password, host, port...
//  - Initial directory path
// Example1: "ftp://testserver:21/home/testuser"
// Example2: "sftp://testuser:testing@testserver:22/~/"
// Example3: "scp://test_server/dir1/"    # Server alias used
function getURIInfo(uri) {
    var uriparts = new Array();
    uriparts["protocol"]="";
    uriparts["hostname"]="";
    uriparts["port"]="";
    uriparts["username"]="";
    uriparts["password"]="";
    uriparts["path"]="";
    uriparts["serveralias"]="";
    uriparts["base_uri"]="";
    var user = "";
    var hostname = "";
    var site=null;

    log.debug("getURIInfo uri : "+uri);

    for (var i = 0; i < remotefile_scheme_types.length; i++) {
        if (uri.indexOf(remotefile_scheme_types[i] + "://") == 0) {
            uri = uri.substr(3 + remotefile_scheme_types[i].length); // remove 'ftp://'
            uriparts["protocol"] = remotefile_scheme_types[i];
        }
    }
    if (uriparts["protocol"].length == 0) {
        log.info("getURIInfo() ignoring unknown scheme type for url: "+uri);
        return null;
    }

    // now have: userinfo@siteinfo/pathinfo
    //    or   : server_alias/pathinfo
    var delim = uri.indexOf("/");
    if (delim > 0) {
        site = uri.substr(0,delim);
        if (delim < uri.length) {
            uriparts["path"] = uri.substr(delim);
            //// Path /~ isn't a nice path to work with
            //if (uriparts["path"].substring(0, 2) == '/~') {
            //    uriparts["path"] = uriparts["path"].substr(1);
            //}
        }
    } else {
        site=uri;
    }
    uriparts["base_uri"] = uriparts["protocol"] + "://" + site;

    // we've received a string that can be contain any combination of parts of
    // the following: "user:pass@hostname.com:port" or "server_alias"

    // Check if it's a server alias
    var server = getServerWithAlias(site);
    if (server) {
        uriparts["serveralias"] = site;
    } else {
        delim = site.lastIndexOf("@");
        if (delim < 0) {
            hostname = site;
        } else {
            user = site.substr(0,delim);
            hostname = site.substr(delim+1);
        }
    
        // create hostname and port
        var hparts = hostname.split(":");
        uriparts["hostname"]=hparts[0];
        if (hparts.length > 1) uriparts["port"] = hparts[1];
    
        delim = user.indexOf(":");
        if (delim < 0) {
            uriparts["username"] = user;
        } else {
            uriparts["username"] = user.substr(0,delim);
            uriparts["password"] = user.substr(delim+1);
        }
    }

    log.debug("getURIInfo serveralias : "+uriparts["serveralias"]);
    log.debug("getURIInfo protocol    : "+uriparts["protocol"]);
    log.debug("getURIInfo hostname    : "+uriparts["hostname"]);
    log.debug("getURIInfo port        : "+uriparts["port"]);
    log.debug("getURIInfo username    : "+uriparts["username"]);
    log.debug("getURIInfo password    : "+uriparts["password"]);
    log.debug("getURIInfo path        : "+uriparts["path"]);
    log.debug("getURIInfo base_uri    : "+uriparts["base_uri"]);

    return uriparts;
}

function getUriForPath(path, includePassword) {
    log.debug('getUriForPath dirPath: '+path);
    if (!path) return null;

    var url = serverInfo.protocol + "://";
    // Now we either use the server alias, or all the server details
    if (serverInfo.serveralias) {
        url += serverInfo.serveralias;
    } else {
        if (serverInfo.username) {
            url += serverInfo.username;
            if (typeof(includePassword) != 'undefined' && includePassword &&
                serverInfo.password) {
                url += ":"+serverInfo.password;
            }
            url += "@";
        }
        url += serverInfo.hostname;
        if (serverInfo.port)
            url += ":"+serverInfo.port;
    }

    if (path[0] != "/")
        url += "/";
    url += path;

    log.debug('getUriForPath uri: '+url);
    return url;
}

function RemoteServerInfo() {
    this.serveralias    = null;
    this.serverprefs    = null;
    this.protocol       = null;
    this.username       = null;
    this.password       = null;
    this.hostname       = null;
    this.port           = null;
    this.privatekey     = null;
    this.connection     = null;
    this.initial_path   = null;
    this.base_uri       = null;
    this.passive        = null;
}

RemoteServerInfo.prototype.constructor = RemoteServerInfo;

var remoteFileBrowser = false;
var serverInfo = new RemoteServerInfo();

// Create a new file object for the given directory
// Re-use existing connection if we have one, otherwise go and connect
// to the server specified in serverInfo.
// Returns RemoteFile/LocalFile object
// Note: Can raise ServerException from the connection layer
function newFile(directory)
{
    log.debug("newFile: creating new file for '"+directory+"'");
    var file = null;

    if (remoteFileBrowser) {
        if (!serverInfo.connection) {
            // We should always have a connection, what gives!
            alert(bundle.GetStringFromName("noConnectionAvailable.alert"));
            return null;
        }
        // maintain a single connection by passing our connection around
        log.debug('newFile: create RemoteFile using existing connection '+directory);
        file = new RemoteFile(directory);
        return file;
    }
    if (RemoteFileBrowserOnly) {
        return null;
    }

    // Only for nsILocalFile
    log.debug('newFile: using nsILocalFile: '+directory);
    serverInfo.connection = null;
    return new localFile(directory)
}

function closeFTP()
{
    if (remoteFileBrowser) {
        log.debug('closeFTP');
        remoteFileBrowser = false;
        if (serverInfo.connection) {
            serverInfo.connection.close();
            serverInfo.connection = null;
        }
    }
}

function setInitialDirectory(dirPath)
{
  // get the home dir
  log.debug("setInitialDirectory: ["+dirPath+"]");
  clearHistoryList();
  var dirServiceProvider = Components.classes[nsIDirectoryServiceProvider_CONTRACTID]
                                     .getService(nsIDirectoryServiceProvider);
  sfile = null;

  try {
    if (dirPath) {
      sfile = newFile(dirPath);
      if (sfile) {
          log.debug("setInitialDirectory: file: "+sfile.leafName+" exists: "+sfile.exists()+" isDir "+sfile.isDirectory);
          if (!sfile.isDirectory) {
              log.debug("setInitialDirectory: was not a directory, using file parent");
              sfile = sfile.parent;
          }
      } else
          log.debug("setInitialDirectory: no file produced for "+dirPath);
    } else if (!RemoteFileBrowserOnly && sfile && !sfile.isDirectory) {
      // Start in the user's home directory
      var persistent = new Object();
      var homeDir = dirServiceProvider.getFile("Home", persistent);
      log.debug("setInitialDirectory: initialize new file with homeDir "+homeDir.path);
      sfile = newFile(homeDir.path);
    }
    if (!sfile) {
        treeView.clearList();
        return;
    }
    gotoDirectory(sfile);
  } catch (e) {
    //alert(e);
    var lastErrorSvc = Components.classes["@activestate.com/koLastErrorService;1"].
                                   getService(Components.interfaces.koILastErrorService);
    alert(bundle.formatStringFromName("error.alert",
        [lastErrorSvc.getLastErrorMessage()], 1));
  }
}

function onFilterChanged(target)
{
  // Do this on a timeout callback so the filter list can roll up
  // and we don't keep the mouse grabbed while we are refiltering.

  setTimeout(changeFilter, 0, target.getAttribute("filters"));
}

function changeFilter(filterTypes)
{
    window.setCursor("wait");
    try {
        treeView.setFilter(filterTypes);
    } catch (ex) {
        alert(bundle.formatStringFromName("couldNotChangeTheFilter.alert", [ex], 1));
    }
    window.setCursor("auto");
}

function onOK()
{
  var errorTitle, errorMessage, promptService;
  var ret = returnCancel;
  var file;
  var url;
  var i=0;
  // get the files from the tree
  var files = treeView.getSelectedFiles();
  // get the filenames from the textbox
  var input = textInput.value;
  var inputFiles = input.split(_fileListSep);
  var dir_path = sfile.path;
  var file_path;

  log.debug("onOK: number of files: "+files.length);
  log.debug("onOK: input is: "+input);
  log.debug("onOK: inputFiles.length: "+inputFiles.length);
  log.debug("onOK: inputFiles: "+inputFiles);
  log.debug("onOK: using basedir from: "+sfile.URL);

  if (input && (filePickerMode == modeSave)) {
    // dump any select files since we have an input filename
    files = new Array();
  }

  // Use the textInput field and make sure we get files that were typed in by the user
  for (i = 0; i < inputFiles.length; i++) {
      log.debug("checking input "+inputFiles[i]);
      input = inputFiles[i];
      // Sanitize the input
      if (!input) {
          if (filePickerMode == modeGetFolder) {
              // Use the current directory then.
              files.push(sfile);
          }
          continue;
      }
      if (input[0] == '~' || input[0] == '/') { // XXX XP?
          file_path = input;
      } else {
          if (dir_path[dir_path.length-1] != "/" && input[0] != "/") file_path = dir_path + "/"+ input;
          else file_path = dir_path + input;
      }
      file = newFile(file_path);

      // look to see if we already have this file by selection
      if (file.exists()) {
          var haveFile = false;
          for (i = 0; i < files.length; i++) {
            // make sure we have a slash!
              log.debug("checking "+files[i].path+" == "+file.path);
              if (files[i].path == file.path) {
                  haveFile = true;
                  break;
              }
          }
          if (haveFile) continue;
      } else if (filePickerMode != modeSave) {
        alert(bundle.formatStringFromName("filePathDoesNotExist.alert", [file_path], 1));
        continue;
      }
      // Else, add to the list of files that we need to open
      files.push(file);
  }

  if (files.length == 0) {
    return false;
  }

  // unless we are in modeOpen, we will not have more than one file
  file = files[0];
  var filepaths = new Array();
  retvals.filepaths = filepaths; // set an empty return array
  // return the server object so we don't have to look it up again!
  if (serverInfo.serverprefs)
    retvals.server = serverInfo.serverprefs;

  switch(filePickerMode) {
  case modeOpen:
    if (file.isFile) {
        // if the first file is a file, all files 'should' be files
        for (i=0; i < files.length; i++) {
            // build an array of full file paths
            log.debug("adding path "+files[i].URL);

            // get the remote url
            url = files[i].URL;
            log.debug("path added "+url);
            filepaths.push(url);
        }
        retvals.filepaths = filepaths;
        // single selection support
        retvals.directory = file.parent.path;
        ret = returnOK;
    } else if (file.isDirectory) {
      if (!sfile.equals(file)) {
        gotoDirectory(file);
      }
      textInput.value = "";
      doEnabling();
      return false;
    }
    break;
  case modeSave:
    if (file.isFile) { // can only be true if file.exists()
      // we need to pop up a dialog asking if you want to save
      var message = bundle.formatStringFromName("fileAlreadyExistsReplaceIt.message",
            [file.path], 1);
      var rv = window.confirm(message);
      if (rv) {
        ret = returnReplace;
        retvals.directory = file.parent.path;
      } else {
        ret = returnCancel;
      }
    } else if (file.isDirectory) {
      if (!sfile.equals(file)) {
        gotoDirectory(file);
      }
      // textInput.value = "";
      doEnabling();
      ret = returnCancel;
    } else {
      var parent = sfile;
      if (parent.exists() && parent.isDirectory) {
        ret = returnOK;
        retvals.directory = parent.path;
      } else {
        var oldParent = parent;
        while (!parent.exists() && parent != parent.parent) {
          oldParent = parent;
          parent = parent.parent;
        }
        errorTitle = bundle.formatStringFromName("errorSaving.title", [file.path], 1);
        if (parent.isFile) {
          errorMessage = bundle.formatStringFromName("isFileCantSave.alert",
            [parent.path, file.path], 2);
        } else {
          errorMessage = bundle.formatStringFromName("pathDoesntExistCantSave.alert",
            [oldParent.path, file.path], 2);
        }
        promptService = Components.classes["@mozilla.org/embedcomp/prompt-service;1"]
                                  .getService(Components.interfaces.nsIPromptService);
        promptService.alert(window, errorTitle, errorMessage);
        ret = returnCancel;
      }
    }
    break;
  case modeGetFolder:
    if (file.isDirectory) {
      retvals.directory = file.path;
    } else { // if nothing selected, the current directory will be fine
      retvals.directory = sfile.path;
    }
    ret = returnOK;
    break;
  }

  //retvals.file = file.path;
  retvals.file = file.URL;
  retvals.buttonStatus = ret;

  if (ret == returnCancel) {
    return false;
  } else {
    return true;
  }
}

function onCancel()
{
  closeFTP(); // in case it's open
  // Close the window.
  retvals.buttonStatus = returnCancel;
  retvals.file = null;
  return true;
}

function textInputOnOK()
{
    if (textInput.value != "") {
        // XXX - This is a bit of a hack, eventually need something cleaner.
        // Unselect anything in the tree, as the tree selection takes priority
        // over the text input in onOK(). Note: We disable the callback, as we
        // don't want it updating the textbox value when things get unselected.
        treeView.selectionCallback = null;
        treeView.unSelectAll();
        treeView.selectionCallback = onSelect;
        // Pass to the onOK function, same as button OK being clicked
        doOKButton();
    }
}

function onDblClick(e) {
  var t = e.originalTarget;
  if (t.localName != "treechildren")
    return;

  openSelectedFile();
}

function openSelectedFile() {
  var files = treeView.getSelectedFiles();
  if (!files.length)
    return;
  var hasDirectory = false;
  for (var i=0; i< files.length; i++) {
      var file = files[i];
      if (file.isDirectory) {
        gotoDirectory(file);
        hasDirectory = true;
        break;
      }
      if (file.isSymlink) {
        file.init(file.target);
      }
  }

  if (hasDirectory) return;

  // finish up!
  doOKButton();
}

function onClick(e) {
  var t = e.originalTarget;
  if (t.localName == "treecol")
    handleColumnClick(t.id);
}

function convertColumnIDtoSortType(columnID) {
  var sortKey;

  switch (columnID) {
  case "FilenameColumn":
    sortKey = filebrowseview.SORTTYPE_NAME;
    break;
  case "FileSizeColumn":
    sortKey = filebrowseview.SORTTYPE_SIZE;
    break;
  case "LastModifiedColumn":
    sortKey = filebrowseview.SORTTYPE_DATE;
    break;
  default:
    dump("unsupported sort column: " + columnID + "\n");
    sortKey = 0;
    break;
  }

  return sortKey;
}

function handleColumnClick(columnID) {
  var sortType = convertColumnIDtoSortType(columnID);
  var sortOrder = (treeView.sortType == sortType) ? !treeView.reverseSort : false;
  treeView.sort(sortType, sortOrder, false);

  // set the sort indicator on the column we are sorted by
  var sortedColumn = document.getElementById(columnID);
  if (treeView.reverseSort) {
    sortedColumn.setAttribute("sortDirection", "descending");
  } else {
    sortedColumn.setAttribute("sortDirection", "ascending");
  }

  // remove the sort indicator from the rest of the columns
  var currCol = document.getElementById("directoryTree").firstChild;
  while (currCol) {
    while (currCol && currCol.localName != "treecol")
      currCol = currCol.nextSibling;
    if (currCol) {
      if (currCol != sortedColumn) {
        currCol.removeAttribute("sortDirection");
      }
      currCol = currCol.nextSibling;
    }
  }
}

function doSort(sortType) {
  treeView.sort(sortType, false);
}

function onKeypress(e) {
  //dump("onKeypress:: " + e.keyCode + "\n");
  if (e.keyCode == 8) { /* backspace */
    goUp();
  } else if (e.keyCode == 13) { /* enter */
    //dump("onKeypress:: enter\n");
    var file = treeView.getSelectedFile();
    if (file) {
      doOKButton();
    }
  }
}

function doEnabling() {
  // Maybe add check if textInput.value would resolve to an existing
  // file or directory in .modeOpen. Too costly I think.
  var enable = (textInput.value != "");
  if (!enable && filePickerMode == modeGetFolder && sfile && sfile.path) {
    // If we have a directory listing, allow selection of the current folder,
    // bug 97991.
    enable = true;
  }

  okButton.disabled = !enable;
}

function getOKAction(file) {
  if (file && file.isDirectory && filePickerMode != modeGetFolder)
    return 'Open';

  switch(filePickerMode) {
  case modeGetFolder:
    return 'Select';
    break;
  case modeOpen:
    return 'Open';
    break;
  case modeSave:
    return 'Save';
    break;
  }
  return ""; // js strict
}

function onSelect(files) {
    var filesText = "";
    var file = null;
    for (var i = 0; i < files.length; i++) {
        file = files[i];
        if (file) {
            var path = file.leafName;

            // break out on the first directory
            if (file.isDirectory) {
                if (filePickerMode == modeGetFolder) filesText = path;
                break;
            } else if (!(filePickerMode == modeGetFolder)) {
                if (path) {
                    if (filesText != "") {
                        filesText += _fileListSep + path;
                    } else {
                        filesText = path;
                    }
                }
            }
        }
    }
    var buttonLabel = '';
    if (filesText != "") {
        buttonLabel = getOKAction(file);
        okButton.setAttribute("label", buttonLabel);
        textInput.value = filesText;
    }

    if (textInput.value.length == 0) {
        okButton.disabled = true;
    } else {
        okButton.disabled = false;
    }
}

function onTextFieldFocus() {
  var buttonLabel = getOKAction(null);
  okButton.setAttribute("label", buttonLabel);
  doEnabling();
}

function onDirectoryChanged(target)
{
  var path = target.getAttribute("label");
  log.debug("onDirectoryChanged("+path+")");
  try {
    var file = newFile(path);

    if (sfile.path != file.path) {
      // Do this on a timeout callback so the directory list can roll up
      // and we don't keep the mouse grabbed while we are loading.
      setTimeout(gotoDirectory, 0, file);
    }
  } catch (e) {
    var lastErrorSvc = Components.classes["@activestate.com/koLastErrorService;1"].
                                   getService(Components.interfaces.koILastErrorService);
    alert(bundle.formatStringFromName("error.alert",
        [lastErrorSvc.getLastErrorMessage()], 1));
  }
}

function addToHistory(directoryName) {
  var menu = document.getElementById("lookInMenu");
  var menuList = document.getElementById("lookInMenuList");
  var children = menu.childNodes;

  if (!children || children.length == 0) {
    var menuItem = document.createElement("menuitem");
    menuItem.setAttribute("label", directoryName);
    menu.appendChild(menuItem);
    menuList.selectedIndex = 0;
    return;
  }

  var i;
  for (i=0; i < children.length; i++) {
    if (children[i].getAttribute("label") == directoryName)
      break;
  }

  if (i < children.length) {
    if (i != 0) {
      var node = children[i];
      menu.removeChild(node);
      menu.insertBefore(node, children[0]);
    }
  } else {
    var menuItem = document.createElement("menuitem");
    menuItem.setAttribute("label", directoryName);
    menu.insertBefore(menuItem, children[0]);
  }

  menuList.selectedIndex = 0;
}

function goLast() {
  var menu = document.getElementById("lookInMenu");
  var children = menu.childNodes;
  var dir = null;
  if (children.length > 1) {
      dir = children[1];
      // move current history item to last history item
      var node = children[0];
      menu.appendChild(node, children[children.length-1]);
      onDirectoryChanged(dir);
  }
}

// Called when the filebrowser dialog "Create Directory" icon is selected
function doMKDIR() {
    if (!sfile) return false;
    var dirName = ko.dialogs.prompt(bundle.GetStringFromName("enterTheNameNewDirectory.message"));
    if (!dirName) return false;

    log.debug("current dir "+sfile.path+" isdir: "+sfile.isDirectory);
    log.debug("doMKDIR: "+dirName);

    var ret = false;
    window.setCursor("wait");
    try {
        var e = new Object();
        if (sfile.createDirectory(dirName)) {
            log.debug("name of new folder is "+sfile.path+"/"+dirName);
            sfile.refresh();
            gotoDirectory(sfile);
            // select the new folder in the tree
            /* until we can edit cells in an ouliner, this does nothing
            if (treeView.selectEntryByNameType(dirName, 1)) {
                // make the cell editable, and edit it!
                doRename();
            }
            */
            ret = true;
        }
    } catch (ex) {
        alert(bundle.formatStringFromName("cannotMakeNewDirectory.alert",
            [sfile.lastError], 1));
    }
    window.setCursor("auto");
    return ret;
}

function doRename() {
    var newName = ko.dialogs.prompt(bundle.GetStringFromName("newNameFileorDirectory.message"),
            null, textInput.value)
    if (!newName || newName == textInput.value) return false;

    var file = treeView.getSelectedFile();
    log.debug("doRename called on "+file.path);
    if (file.moveTo(null, newName)) {
        sfile.refresh();
        gotoDirectory(sfile);
        return true;
    } else {
        return false;
    }
}

function doDelete() {
    var files = treeView.getSelectedFiles();
    if (ko.dialogs.yesNo(bundle.GetStringFromName("areYouSureDeleteSelectedFiles.message"), "No") == "No") {
      return;
    }
    for (var i=0; i< files.length; i++) {
        log.debug("doDelete called on "+files[i].path);
        var recurse = false;
        if (files[i].isDirectory) {
            var prompt_message = bundle.formatStringFromName("theFileIsADirectory.message"
                ,[files[i].leafName], 1);
            var title = bundle.GetStringFromName("directoryDeletion.title");
            if (ko.dialogs.okCancel(prompt_message, "OK", null, title) != "OK") {
                continue;
            }
        }
        files[i].remove(recurse);
        // XXX TODO remove from history if its in there
    }
    var tree = document.getElementById("directoryTree");
    tree.treeBoxObject.scrollToRow(0);
    sfile.refresh();
    gotoDirectory(sfile);
}

function doRefresh() {
    if (!sfile) return;
    window.setCursor("wait");
    try {
        sfile.refresh();
        gotoDirectory(sfile);
        labelStatus.value = "";
    } catch (ex) {
        alert(bundle.formatStringFromName("cannotRefreshPath.alert", [sfile.lastError()], 1));
    }
    window.setCursor("auto");
}

function goUp() {
  try {
    var parent = sfile.parent;
  } catch(ex) { dump("can't get parent directory\n"); }

  if (parent) {
    gotoDirectory(parent);
  }
}

function gotoDirectory(remoteDir) {
    var path = remoteDir.path;
    log.debug("gotoDirectory '"+path+"'");
    window.setCursor("wait");
    try {
        treeView.setDirectory(path);
        if (filePickerMode != modeSave) {
            // See bug 89373 which always clears this field,
            // bug 92099 complains that the filename is cleared when
            //           trying to save a file with a different name.
            textInput.value = "";
        }
        doEnabling();
        addToHistory(path);
    
        sfile = remoteDir;
        var listUpdateTime = sfile._sfile.timeLastRefreshed;
        if ((listUpdateTime > 0) &&
            (listUpdateTime < (timeSvc.time() - 5))) {    // Older than 5 seconds
            var timeTuple = timeSvc.localtime(listUpdateTime, new Object());
            var date = timeSvc.strftime("%H:%M:%S", timeTuple.length, timeTuple);
            labelStatus.value = bundle.formatStringFromName("cachedAt.label", [date], 1);
        } else
            labelStatus.value = "";
    } catch (e) {
        //alert(e);
        alert(bundle.formatStringFromName("cannotChangeDirectory.alert",
            [sfile.lastError()], 1));
    }
    window.setCursor("auto");
}


var servers = null;

function loadServerPrefs()
{
    //servers = getServerListFromPreference(globalPrefs);
    var RCService = Components.classes["@activestate.com/koRemoteConnectionService;1"].
                    getService(Components.interfaces.koIRemoteConnectionService);
    var server_count = {};
    servers = RCService.getServerInfoList(server_count);
}

function createServersMenuItem(server) {
  var cell = document.createElementNS(XUL_NS, 'menuitem');
  cell.setAttribute('label', server.alias);
  return cell;
}

function setupServerMenuList(selectServerWithAlias)
{
    log.debug("setupServerMenuList, selectServerWithAlias: "+selectServerWithAlias);
    var menubox = document.getElementById("serversList");
    menubox.removeAttribute("collapsed");

    var menulist = document.getElementById("serverMenu");
    var menuitem;

    // add the default entry
    menuitem = document.createElementNS(XUL_NS, 'menuitem');
    if (RemoteFileBrowserOnly) {
        menuitem.setAttribute('id', "blank_entry");
        menuitem.setAttribute('label', "");
    } else {
        menuitem.setAttribute('id', localDrives);
        menuitem.setAttribute('label', localDrives);
    }
    menulist.appendChild(menuitem);

    // add the deployment servers
    var selectedServerIndex = -1;
    for (var i = 0; i < servers.length; i++) {
        menuitem = createServersMenuItem(servers[i]);
        menulist.appendChild(menuitem);
        if (selectServerWithAlias &&
            (selectServerWithAlias == servers[i].alias))
            selectedServerIndex = i+1;
    }
    if (selectedServerIndex >= 0)
        document.getElementById("serverMenuList").selectedIndex = selectedServerIndex;
    else if (serverInfo.base_uri)
        document.getElementById("serverMenuList").label = serverInfo.base_uri;
    log.debug("setupServerMenuList done");
}

function clearHistoryList()
{
    var menulist = document.getElementById("lookInMenu");
    while (menulist.childNodes.length) {
        menulist.removeChild(menulist.firstChild);
    }
}

function clearServerList()
{
    var menulist = document.getElementById("serverMenu");
    while (menulist.childNodes.length) {
        menulist.removeChild(menulist.firstChild);
    }
}

function getAliasIndex(alias) {
  log.debug("getting the server object for "+alias);
  if (servers) {
  for (var i = 0; i < servers.length; i++) {
    if (alias == servers[i].alias) return i;
  }
  }
  return -1;
}

function getServerWithAlias(alias) {
    var idx = getAliasIndex(alias);
    // alias can be null
    if (!alias || idx == -1)
        return null;

    return servers[idx];
}

function changeServerInfo(alias) {
    log.debug('changeServerInfo='+alias);
    serverInfo.connection = null;
    var server = getServerWithAlias(alias);
    if (server) {
        serverInfo.serveralias  = alias;
        serverInfo.serverprefs  = server;
        serverInfo.protocol     = server.protocol.toLowerCase();
        serverInfo.username     = server.username;
        serverInfo.password     = server.password;
        serverInfo.hostname     = server.hostname;
        serverInfo.port         = server.port;
        serverInfo.initial_path = server.path;
        serverInfo.passive      = server.passive;
        serverInfo.privatekey   = server.privatekey;
        // Set to FTP browser if our protocol is 'ftp', 'sftp' etc...
        for (var i = 0; i < remotefile_scheme_types.length; i++) {
            if (serverInfo.protocol == remotefile_scheme_types[i]) {
                remoteFileBrowser = true;
            }
        }
    }
    return server;
}

function setServerInfoUsingUri(uri) {
    var parts = getURIInfo(uri);
    if (!parts) {
        log.warn("setServerInfoUsingUri: Could not parse uri: " + uri);
        return false;
    }
    serverInfo.base_uri = parts["base_uri"];
    serverInfo.serveralias = parts["serveralias"];
    if (serverInfo.serveralias) {
        // Setup the server information using the alias
        changeServerInfo(serverInfo.serveralias);
        serverInfo.initial_path = null;
    }
    // Copy over the uri information if it's available
    if (parts["protocol"])  serverInfo.protocol     = parts["protocol"].toLowerCase();
    if (parts["hostname"])  serverInfo.hostname     = parts["hostname"];
    if (parts["port"])      serverInfo.port         = parts["port"];
    if (parts["username"])  serverInfo.username     = parts["username"];
    if (parts["password"])  serverInfo.password     = parts["password"];
    if (parts["path"])      serverInfo.initial_path = parts["path"];

    // Set to remote file browser if our protocol matches a remote scheme
    for (var i = 0; i < remotefile_scheme_types.length; i++) {
        if (serverInfo.protocol == remotefile_scheme_types[i]) {
            remoteFileBrowser = true;
        }
    }
    return true;
}

function getServerPathAsUrl(server) {
    // build url!
    var url = server.protocol.toLowerCase()+"://";
    if (server.username) {
        url += server.username;
        if (server.password) url += ":"+server.password;
        url += "@";
    }
    url += server.hostname;
    if (server.port) url += ":"+server.port;
    if (server.path[0] != "/") url += "/"+server.path;
    else url += server.path;
    log.debug('getServerPathAsUrl: '+url)
    return url;
}

function connectToServer() {
    // Try and connect to this server now
    var lastErrorSvc = Components.classes["@activestate.com/koLastErrorService;1"].
                                   getService(Components.interfaces.koILastErrorService);
    // Clear the last error
    lastErrorSvc.setLastError(0, "")
    var RCService = Components.classes["@activestate.com/koRemoteConnectionService;1"].
                    getService(Components.interfaces.koIRemoteConnectionService);
    var connection = RCService.getConnection2(serverInfo.protocol,
                                              serverInfo.hostname,
                                              serverInfo.port,
                                              serverInfo.username,
                                              serverInfo.password,
                                              "",
                                              serverInfo.passive,
                                              serverInfo.privatekey)
    serverInfo.connection = connection;
    // Connection may have changed the username in the process of connecting,
    // ensure we keep it current
    serverInfo.username = connection.username;
}

function onServerChanged(alias) {
    log.debug("onServerChanged("+alias+")");
    // just to allow closing the connection...
    closeFTP();

    serverInfo = new RemoteServerInfo();

    // Clear the contents of the file browser dialog
    labelStatus.value = "";
    treeView.clearList();

    var server = changeServerInfo(alias);
    if (!alias || !server) {
        if (!setServerInfoUsingUri(alias) || (!remoteFileBrowser)) {
             alert(bundle.formatStringFromName("urlMustBeginWith.alert",
                [remotefile_scheme_types.join("://, ")], 1));
            setInitialDirectory(null);
            return;
        }
        server = new Server(serverInfo.protocol, "", serverInfo.hostname,
                            serverInfo.port, serverInfo.initial_path,
                            serverInfo.username, serverInfo.password,
                            serverInfo.passive, serverInfo.privatekey);
    }

    try {
        connectToServer();
        var initial_path = server.path;
        if (!initial_path) {
            // Go to home directory then
            initial_path = serverInfo.connection.getHomeDirectory();
        }
        setInitialDirectory(initial_path);
    } catch (e) {
        var lastErrorSvc = Components.classes["@activestate.com/koLastErrorService;1"].
                                       getService(Components.interfaces.koILastErrorService);
        var errormsg = lastErrorSvc.getLastErrorMessage()
        if (!errormsg) {
            errormsg = e; // Use the exception then;
            // Unexpected exception, log it
            log.exception(e);
        }
        if (errormsg != 'Login cancelled by user.')
            alert(bundle.formatStringFromName("error.alert", [errormsg], 1));
    }
}

function setCurrentServerFromServerInfo() {
    log.debug("setCurrentServerFromServerInfo: serveralias:"+serverInfo.serveralias);
    log.debug("setCurrentServerFromServerInfo: p:"+serverInfo.protocol+
              " s: "+serverInfo.hostname+":"+serverInfo.port+
              " u: "+serverInfo.username);
    if (serverInfo.serveralias) {
        try {
            return setCurrentServer(serverInfo.serveralias);
        } catch (e) {
            // Try setting from the serverInfo.connection variable then
        }
    }
    if (servers && serverInfo.connection) {
        log.debug("We have servers: "+servers.length);
        var conn = serverInfo.connection;
        //log.debug("p:"+conn.protocol+" s:"+conn.server+":"+conn.port+ " u:"+conn.username);
        for (var i = 0; i < servers.length; i++) {
            if ((servers[i].protocol.toLowerCase() == conn.protocol) &&
                (servers[i].hostname == conn.server) &&
                (!servers[i].port || (servers[i].port == conn.port)) &&
                (servers[i].username == conn.username)) {
                log.debug("Found a match!");
                serverInfo.serveralias = servers[i].alias;
                serverInfo.serverprefs = servers[i].alias;
                return servers[i];
            }
        }
    }
    // Server was NOT found
    var err = "setCurrentServerFromServerInfo: Unknown server";
    log.error(err);
    throw(err);
}

function goServerPrefs() {
    // just load up prefs so they can add servers
    ko.windowManager.getMainWindow().prefs_doGlobalPrefs("serversItem", false, window);
}

function refreshServerMenu() {
    // Refresh the server list
    clearServerList();
    loadServerPrefs();
    setupServerMenuList(null);
}

function goHelp() {
    ko.windowManager.getMainWindow().ko.help.open(helpTag);
}
