/* Copyright (c) 2000-2007 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

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
            ko.views.manager.doFileNewFromTemplate(part.value);
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

this.importFromPackage = function part_ImportFromPackage(part, filename) {
    if (!filename)
        filename = ko.filepicker.openFile(
            null, null, // default dir and filename
            "Select Package to Import", // title
            "Komodo Package", // default filter
            ["Komodo Package", "All"]); // filters
            // When have .ktf files changes to this:
            //"Komodo Toolbox", // default filter
            //["Komodo Toolbox", "Komodo Project", "All"]);
    if (!filename) return;

    var basename = ko.uriparse.baseName(filename);
    var directory = ko.filepicker.getFolder(null /* =defaultDirectory */,
                              "Select Directory to extract "+basename+" to" /* =null */);
    if (!directory) return;

    var packager = Components.classes["@activestate.com/koProjectPackageService;1"]
                      .getService(Components.interfaces.koIProjectPackageService);
    packager.importPackage(filename, directory, part)
}

}).apply(ko.projects);

// backwards compat api
var part_invokePart = ko.projects.invokePart;
var part_invokePartById = ko.projects.invokePartById;
var part_findPartById = ko.projects.findPartById;
var part_ImportFromFS = ko.projects.importFromFileSystem;
var part_ImportFromPackage = ko.projects.importFromPackage;
