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

var dirname, include, exclude, importType, recursive, flat, itype, dirs, part;
var gNext;

function onLoad() {
try {
    var dialog = document.getElementById("dialog-importfromfs")
    gNext = dialog.getButton("accept");
    gNext.setAttribute('label', 'Next');
    gNext.setAttribute('accesskey', 'N');
    dirname = document.getElementById('dirname');
    include = document.getElementById('inc-filter');
    exclude = document.getElementById('ex-filter');
    recursive = document.getElementById('recursive');
    importType= document.getElementById('import-type');
    flat = document.getElementById('flat');
    dirs = document.getElementById('dirs');
    if (window.arguments && window.arguments[0]) {
        dirname.value = window.arguments[0].dirname;
        include.value=window.arguments[0].include;
        exclude.value=window.arguments[0].exclude;
        part = window.arguments[0].part;
        itype = window.arguments[0].importType;
        if  (itype == 'useFolders') {
            importType.selectedIndex = 0;
        } else if (itype == 'groupByType') {
            importType.selectedIndex = 1;
        } else if (itype == 'makeFlat') {
            importType.selectedIndex = 2;
        } else {
            importType.selectedIndex= 0;
            alert("importType is set to an invalid value: "+itype);
            window.focus();
        }
        if (window.arguments[0].recursive) {
            recursive.checked=true;
        } else {
            recursive.checked=false;
        }
    }
    updateRecursive();
    dirname.focus();
    dirname.select();
} catch (e) {
    log.exception(e);
}
}

function onNext()  {
    try {
        var location = dirname.value;
        if (!location) {
            alert("You must specify a directory to import from");
            window.focus();
            return false;
        }
        // See if this is a remote url
        var RCService = Components.classes["@activestate.com/koRemoteConnectionService;1"].
                        getService(Components.interfaces.koIRemoteConnectionService);
        var remoteImport = RCService.isSupportedRemoteUrl(location);
        if (!remoteImport) {
            var osPathSvc = Components.classes["@activestate.com/koOsPath;1"].getService(Components.interfaces.koIOsPath);
            if (!osPathSvc.isdir(location)) {
                alert("The path '" + location +
                      "' does not exist or is not a directory");
                window.focus();
                return false;
            }
        }
        if (!confirmImport(remoteImport)) {
            return false;
        }

        if (window.arguments && window.arguments[0]) {
            window.arguments[0].dirname=location;
            window.arguments[0].include=include.value;
            window.arguments[0].exclude=exclude.value;
            window.arguments[0].importType=importType.selectedItem.getAttribute('data');
            window.arguments[0].recursive=recursive.checked;
            window.arguments[0].res = true;
        }
        top.window.close()
        return true;
    } catch (e) {
        log.exception(e);
    }
    return false;
}

function confirmImport(remoteImport /* boolean */) {
    window.setCursor("wait");
    var filenames = new Array();
    var _importType = importType.selectedItem.getAttribute('data');
    var dorecursive = recursive.checked == true;
    var importService = Components.classes["@activestate.com/koFileImportingService;1"].
                    getService(Components.interfaces.koIFileImportingService);
    if (part.project == part) {
        // don't import the kpf
        exclude.value = exclude.value+";"+part.name;
    }
    if (remoteImport) {
        importService.findCandidateFilesRemotely(part, dirname.value,
                                         include.value, exclude.value,
                                         dorecursive, filenames, new Object());
    } else {
        importService.findCandidateFiles(part, dirname.value,
                                         include.value, exclude.value,
                                         dorecursive, filenames, new Object());
    }
    filenames = filenames.value;

    window.setCursor("auto");

    if (filenames.length == 0) {
        alert("No changes are needed.");
        window.focus();
        return false;
    }

    var selected = ko.dialogs.selectFromList(
            "Confirm Project Changes", // title
            "Select the files you would like to add to your project:",
            filenames); // items

    window.focus();
    if (selected == null) { // ESC/Cancel was hit
        return false;
    }

    window.setCursor("wait");

    importService.addSelectedFiles(part, _importType, dirname.value, selected, selected.length);

    window.setCursor("auto");
    return true;
}

function onCancel()  {
    window.arguments[0].res= false;
    top.window.close()
}

function updateRecursive()
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

