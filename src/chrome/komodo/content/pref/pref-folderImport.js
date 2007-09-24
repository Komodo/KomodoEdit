/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

/* A wizard to import files from disk into an existing Komodo project. */

var dirname, include, exclude, importType, recursive, flat, itype, dirs, part, importLive;
var dialog;

function PrefFolderImport_OnLoad() {
    parent.hPrefWindow.onpageload();
}

function OnPreferencePageLoading(prefset) {
    dirname = document.getElementById('import_dirname');
    include = document.getElementById('import_include_matches');
    exclude = document.getElementById('import_exclude_matches');
    importLive = document.getElementById('import_live');
    recursive = document.getElementById('recursive');
    importType= document.getElementById('import_type');
    flat = document.getElementById('flat');
    dirs = document.getElementById('dirs');

    // set the dirname if the pref is not already set
    if (!prefset.hasPrefHere("import_live") && typeof(parent.part) != 'undefined' && parent.part) {
        // get real value from project itself
        importLive.checked = parent.part.live;
        if (parent.part.live) {
            dirname.value = parent.part.liveDirectory;
        }
    }
    PrefFolderImport_updateLive();
    PrefFolderImport_updateRecursive();
}

function OnPreferencePageOK(prefset) {
    if (typeof(parent.part) != 'undefined' && parent.part) {
        // if the pref was not previously set, and the dirname is unchanged,
        // do not set the pref
        if (!importLive.checked || dirname.value == parent.part.liveDirectory) {
            prefset.deletePref("import_dirname");
        }
    }
    return true;
}

// Utility functions for the various panels.
function PrefFolderImport_doBrowseForDir() {
    var dir = ko.filepicker.getFolder(dirname.value);
    if (dir) dirname.value = dir;
};

function PrefFolderImport_updateRecursive()
{
    if (recursive.checked)  {
        dirs.removeAttribute('disabled');
    } else {
        if (importType.selectedIndex == 0) {
            importType.selectedIndex = 2;  /* Gotta change it if we're disabling recursive */
        };
        dirs.setAttribute('disabled', 'true');
    }
};

function PrefFolderImport_updateLive() {
    if (importLive.checked) {
        // disable items that are not used with live folders
        recursive.setAttribute('disabled','true');
        importType.setAttribute('disabled','true');
        if (!dirname.value && parent.part) {
            dirname.value = parent.part.liveDirectory;
        }
    } else {
        recursive.removeAttribute('disabled');
        importType.removeAttribute('disabled');
    }
}
