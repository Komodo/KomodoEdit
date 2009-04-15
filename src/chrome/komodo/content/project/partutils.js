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

if (typeof(ko)=='undefined') {
    var ko = {};
}
if (typeof(ko.projects)=='undefined') {
    ko.projects = {};
}

(function() {
var log = ko.logging.getLogger("ko.projects");
/**
 * Given a koIPart, invoke it (do it's "double-click" action) through
 * whatever code path is appropriate for that part -- i.e. snippets
 * get inserted, commands get run, etc.
 */
this.invokePart = function part_invokePart(part) {
    switch (part.type) {
        case 'URL':
            ko.browse.openUrlInDefaultBrowser(part.value);
            break;
        case 'command':
            ko.projects.runCommand(part);
            break;
        case 'snippet':
            ko.projects.snippetInsert(part);
            break;
        case 'file':
            ko.open.URI(part.url);
            break;
        case 'template':
            ko.views.manager.doFileNewFromTemplateAsync(part.value);
            break;
        case 'DirectoryShortcut':
            ko.projects.openDirectoryShortcut(part);
            break;
        case 'macro':
            ko.projects.executeMacro(part);
            break;
        default:
            ko.dialogs.alert("Don't know how to launch items of type " + part.type);
            break;
    }}

/**
 * Given the ID of a part, find it and invoke it.
 */
this.invokePartById = function part_invokePartById(id) {
    try {
        var part = ko.projects.findPartById(id);
        if (!part) {
            log.error("Couldnt' find part with id: " + id);
            return;
        }
        ko.projects.invokePart(part);
    } catch (e) {
        log.error(e);
    }
}

var gPartSvc = Components.classes["@activestate.com/koPartService;1"].
        getService(Components.interfaces.koIPartService);

/**
 * Given a ID, look in the projects and toolboxes until you find
 * the first part with that id (the id allocation scheme guarantees there
 * will be at most one) and return it.  Return null on failure to find such
 * a part.
 */
this.findPartById = function part_findPartById(id) {
    return gPartSvc.getPartById(id);
}

function _getPartURL(part) {
    if (part.hasAttribute('url')) {
        // Is it a project or a folder?
        var url = part.getStringAttribute('url')
        var pathSvc = Components.classes["@activestate.com/koOsPath;1"]
                                .getService(Components.interfaces.koIOsPath);
        var dirname = ko.uriparse.URIToLocalPath(url);
        if (part.type == 'project') {
            dirname = pathSvc.dirname(dirname);
        }
        return dirname;
    } else if (part.parent) {
        return _getPartURL(part.parent);
    }
    return null;
}

this.importFromFileSystem = function part_ImportFromFS(part, baseURL) {
    try {
    if (!part) return false;
    if (typeof(baseURL) == undefined) {
        baseURL = null;
    }

    var resp = new Object();
    resp.include = part.prefset.getStringPref("import_include_matches");
    resp.exclude = part.prefset.getStringPref("import_exclude_matches");
    resp.recursive= part.prefset.getBooleanPref("import_recursive");
    resp.importType= part.prefset.getStringPref("import_type");
    if (part.prefset.hasPrefHere("import_dirname")) {
        resp.dirname = part.prefset.getStringPref("import_dirname");
    } else {
        if (baseURL) {
            resp.dirname = ko.uriparse.URIToLocalPath(baseURL);
        } else {
            resp.dirname = _getPartURL(part);
            if (!resp.dirname) {
                var os = Components.classes["@activestate.com/koOs;1"].getService();
                resp.dirname = os.getcwd();
            }
        }
    }
    resp.res = '';
    resp.part = part;
    resp.global = window;

    ko.windowManager.openOrFocusDialog(
            "chrome://komodo/content/project/importFromFS.xul",
        'komodo_import',
        "chrome,modal,dependent,close=yes",
        resp);
    if (resp.res != true) {
        return false;
    }
    if (resp.include != part.prefset.getStringPref("import_include_matches")) {
        part.prefset.setStringPref("import_include_matches", resp.include);
    }
    if (resp.exclude != part.prefset.getStringPref("import_exclude_matches")) {
        part.prefset.setStringPref("import_exclude_matches", resp.exclude);
    }
    if (resp.recursive != part.prefset.getBooleanPref("import_recursive")) {
        part.prefset.setBooleanPref("import_recursive", resp.recursive);
    }
    if (resp.importType != part.prefset.getStringPref("import_type")) {
        part.prefset.setStringPref("import_type", resp.importType);
    }
    if (resp.dirname != part.prefset.getStringPref("import_dirname")) {
        part.prefset.setStringPref("import_dirname", resp.dirname);
    }
    } catch(e) {
        log.exception(e);
    }
    return true;
}

/**
 * Recursively removes virtual files and folders, but does not
 * remove any folders that have been added manually or parts
 * that are not files or folders (i.e. snippets, macros, etc...).
 * This function will also remove any manually added files, that
 * were not added as part of the import process, because there
 * is not way to tell manually added files and imported files
 * apart.
 */
this.removeImportedVirtualFilesAndFolders =
function part_RemoveImportedVirtualFilesAndFolders(part) {
    // Get the children
    var children = new Array();
    part.getChildren(children, new Object());
    children = children.value;
    var childpart;
    for (var i=children.length-1; i >=0; i--) {
        // Only remove non-live files and folders
        childpart = children[i];
        if (!childpart.live) {
            if (childpart.type == "folder") {
                // Folder parts without urls were added separately (manually)
                if (part.url) {
                    this.removeVirtualFilesAndFolders(childpart);
                    // Only remove the foler if it's empty
                    if (childpart.isEmpty()) {
                        part.removeChild(childpart);
                    }
                }
            } else if (childpart.type == "file") {
                // All files can be deleted (there is currently no way to
                // tell if was manually added)
                part.removeChild(childpart);
            }
        }
    }
}

this.reimportFromFileSystem = function part_ReImportFromFS(part) {
    try {
        if (!part) {
            // Need a part to work on at the least
            return false;
        }

        var imp = new Object();
        imp.include = part.prefset.getStringPref("import_include_matches");
        imp.exclude = part.prefset.getStringPref("import_exclude_matches");
        imp.recursive= part.prefset.getBooleanPref("import_recursive");
        imp.importType= part.prefset.getStringPref("import_type");
        imp.part = part;
        imp.global = window;

        //part.dump(2);
        if (part.prefset.hasPrefHere("import_dirname")) {
            imp.dirname = part.prefset.getStringPref("import_dirname");
        } else {
            imp.dirname = _getPartURL(part);
            if (!imp.dirname) {
                return false;
            }
        }

        // See if this is a remote url
        var RCService = Components.classes["@activestate.com/koRemoteConnectionService;1"].
                        getService(Components.interfaces.koIRemoteConnectionService);
        var remoteImport = RCService.isSupportedRemoteUrl(imp.dirname);
        if (!remoteImport) {
            var osPathSvc = Components.classes["@activestate.com/koOsPath;1"].getService(Components.interfaces.koIOsPath);
            if (!osPathSvc.isdir(imp.dirname)) {
                alert("The path '" + imp.dirname +
                      "' does not exist or is not a directory");
                window.focus();
                return false;
            }
        }

        // Now get the files to import (may be slow for remote systems)
        window.setCursor("wait");

        var filenames = new Array();
        try {
            // Remove all the old entries, not doing this as it may
            // inadvertently remove manually added files!
            //this.removeVirtualFilesAndFolders(part);

            // Find importable files
            var importService = Components.classes["@activestate.com/koFileImportingService;1"].
                            getService(Components.interfaces.koIFileImportingService);
            if (part.project == part) {
                // don't import the kpf
                imp.exclude += ";" + part.name;
            }
            if (remoteImport) {
                importService.findCandidateFilesRemotely(part, imp.dirname,
                                                 imp.include, imp.exclude,
                                                 imp.recursive, filenames,
                                                 new Object());
            } else {
                importService.findCandidateFiles(part, imp.dirname,
                                                 imp.include, imp.exclude,
                                                 imp.recursive, filenames,
                                                 new Object());
            }
            filenames = filenames.value;
            //dump("reimportFromFileSystem:: Filenames\n");
            //for (var i=0; i < filenames.length; i++) {
            //    dump("    " + filenames[i] + "\n");
            //}
            if (filenames.length == 0) {
                // No changes are needed
                return false;
            }

            // Add the importable files
            importService.addSelectedFiles(part, imp.importType, imp.dirname,
                                           filenames, filenames.length);
        } finally {
            window.setCursor("auto");
        }
        return true;

    } catch(e) {
        log.exception(e);
    }
    return true;
}

/**
 * Import a Komodo package (filename) into the given part.
 *
 * @param part {Components.interfaces.koIPart} - The part to import into.
 * @param filename {string} - The filename of the package to import.
 * @returns {Components.interfaces.koIPart} - The part that was created to hold
 *          the imported contents.
 */
this.importFromPackage = function part_ImportFromPackage(part, filename) {
    if (!filename) {
        filename = ko.filepicker.openFile(
            null, null, // default dir and filename
            "Select Package to Import", // title
            "Komodo Package", // default filter
            ["Komodo Package", "All"]); // filters
            // When have .ktf files changes to this:
            //"Komodo Toolbox", // default filter
            //["Komodo Toolbox", "Komodo Project", "All"]);
    }
    if (!filename) return null;

    // Use the default toolbox package extraction folder. The importPackage
    // call will automaticaly create a sub-folder underneath this directory:
    // .../extracted-kpz/${basename}/
    var koDirs = Components.classes["@activestate.com/koDirs;1"].
            getService(Components.interfaces.koIDirs);
    var os = Components.classes["@activestate.com/koOs;1"].
            getService(Components.interfaces.koIOs);
    var userDataDir = koDirs.userDataDir;
    var kpzExtractFolder = os.path.join(userDataDir, 'extracted-kpz');
    if (!os.path.exists(kpzExtractFolder)) {
        os.mkdir(kpzExtractFolder);
    }

    var basename = os.path.withoutExtension(os.path.basename(filename));
    var extractedPart = part.project.createPartFromType('folder');
    extractedPart.setStringAttribute('name', basename);
    part.addChild(extractedPart);

    var packager = Components.classes["@activestate.com/koProjectPackageService;1"]
                      .getService(Components.interfaces.koIProjectPackageService);
    packager.importPackage(filename, kpzExtractFolder, extractedPart);

    // Remove the extracted kpz folder if it is empty.
    var nsFolder = Components.classes["@mozilla.org/file/local;1"].
                 createInstance(Components.interfaces.nsILocalFile);
    nsFolder.initWithPath(os.path.join(kpzExtractFolder, basename));
    if (nsFolder.exists()) {
        try {
            nsFolder.remove(false);
        } catch (ex) {
            // Not empty, leave the folder there.
        }
    }

    return extractedPart;
}

}).apply(ko.projects);

// backwards compat api
var part_invokePart = ko.projects.invokePart;
var part_invokePartById = ko.projects.invokePartById;
var part_findPartById = ko.projects.findPartById;
var part_ImportFromFS = ko.projects.importFromFileSystem;
var part_ImportFromPackage = ko.projects.importFromPackage;
