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
