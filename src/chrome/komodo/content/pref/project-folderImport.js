/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

/* A wizard to import files from disk into an existing Komodo project. */

var dirname, include, exclude, importLive, project;
var last_local_directory;
var last_remote_directory;

// "pfi" : project-folderImport prefix for global functions
//         that might collide with function names in file-properties.p.js

function pfi_OnPreferencePageLoading(prefset) {
    dirname = document.getElementById('import_dirname');
    include = document.getElementById('import_include_matches');
    exclude = document.getElementById('import_exclude_matches');
    if (prefset.hasPref('last_local_directory')) {
        last_local_directory = prefset.getStringPref('last_local_directory');
    } else {
        last_local_directory = null;
    }
    if (prefset.hasPref('last_remote_directory')) {
        last_remote_directory = prefset.getStringPref('last_remote_directory');
    } else {
        last_remote_directory = null;
    }

    // set the dirname if the pref is not already set
    project = ((typeof(parent.part) != 'undefined' && parent.part)
               ? parent.part.project : null);
    dirname.value = (project
                     && (project.importDirectoryLocalPath || project.importDirectoryURI)
                     || "");
}

function pfi_OnPreferencePageOK(prefset) {
    prefset.setStringPref('last_local_directory', last_local_directory);
    prefset.setStringPref('last_remote_directory', last_remote_directory);
    return true;
}

function PrefFolderImport_doBrowseForDir() {
    var currentUrl = dirname.value;
    if (currentUrl.indexOf("://") > -1) {
        currentUrl = last_local_directory;
    }
    var dir = ko.filepicker.getFolder(currentUrl);
    if (dir) {
        dirname.value = last_local_directory = dir;
    }
};

function PrefFolderImport_doBrowseForRemoteDir() {
    // No need for defaults here?
    var currentUrl = dirname.value;
    if (currentUrl.indexOf("://") == -1) {
        currentUrl = last_remote_directory;
    }
    var fileBrowserRetvals = ko.filepicker.remoteFileBrowser(currentUrl, 
                                          "" /* defaultFilename */,
                                          Components.interfaces.nsIFilePicker.modeGetFolder);
    var uri = fileBrowserRetvals.file;
    if (!uri) {
        return;
    }
    var RCService = Components.classes["@activestate.com/koRemoteConnectionService;1"].
        getService(Components.interfaces.koIRemoteConnectionService);
    if (!RCService.isSupportedRemoteUrl(uri)) {
        ko.dialogs.alert(
           "Project internal error: browseForRemoteDir returned remote uri "
           + uri
           + ", but can't process it with the RemoteConnectionService");
        return;
    }
    dirname.value = last_remote_directory = uri;
};
