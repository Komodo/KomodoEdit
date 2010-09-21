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

/* A wizard to import files from disk into an existing Komodo project. */

var dirname, include, exclude, importLive, project;
var last_local_directory;
var last_remote_directory;

function PrefFolderImport_OnLoad() {
    parent.hPrefWindow.onpageload();
}

function OnPreferencePageLoading(prefset) {
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
    if (!project) {
        dump("**************** pref-folderImport.js -- no project found\n");
    } else {
        dirname.value = project.importDirectory;
    }
}

function OnPreferencePageOK(prefset) {
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
