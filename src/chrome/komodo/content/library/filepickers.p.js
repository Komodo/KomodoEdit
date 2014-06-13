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

/* Interface functions for using nsIFilePicker in Komodo.
 *
 * Methods:
 *      ko.filepicker.browseForFile(...)      Pick an existing file.
 *      ko.filepicker.browseForExeFile(...)   Pick an existing executable file.
 *      ko.filepicker.browseForFiles(...)     Pick multiple existing files.
 *      ko.filepicker.saveFile(...)           Pick an existing or new file.
 *      ko.filepicker.getFolder(...)          Pick an existing folder/directory.
 *
 * Example:
 *  Most of filepicker_*() methods have the same options so this example should
 *  translate to all of them. Say you would like the user to open a saved macro
 *  file. The following might be appropriate:
 *      var path = ko.filepicker.browseForFile(<macros dir>, // default dir
 *                                     null, // default filename
 *                                     "Open Macro", // title
 *                                     "JavaScript", // default filter name
 *                                     ["JavaScript", "Python", "All"]);
 *
 */
ko.filepicker = {};
(function() {

const Cc = Components.classes;
const Ci = Components.interfaces;
Components.utils.import("resource://gre/modules/XPCOMUtils.jsm");

var local = {};

XPCOMUtils.defineLazyGetter(local, "log", function() ko.logging.getLogger("filepickers"));

XPCOMUtils.defineLazyGetter(local, "bundle", function() Cc["@mozilla.org/intl/stringbundle;1"]
                                                        .getService(Ci.nsIStringBundleService)
                                                        .createBundle("chrome://komodo/locale/library.properties"));

XPCOMUtils.defineLazyGetter(local, "globalPrefs", function() Cc["@activestate.com/koPrefService;1"]
                                                             .getService(Ci.koIPrefService).prefs);

XPCOMUtils.defineLazyGetter(local, "prefs", function() local.globalPrefs.getPref("filepickers.defaultDirs"));

XPCOMUtils.defineLazyGetter(local, "osPathSvc", function() Cc["@activestate.com/koOsPath;1"]
                                                            .getService(Ci.koIOsPath));

//---- internal support stuff

/* if scimoz has focus, it will fight the native windows dialogs
  for control of the focus, and we end up with bad cursor behaviour
  in our file dialogs.  Here we save then restore the focus to work
  around this problem. */
function _unfocus() {
// #if PLATFORM == "win"
    try {
        var fv = ko.window && ko.window.focusedScintilla();
        if (fv) {
            fv.scimoz.isFocused = false;
        }
        return fv;
    } catch(e) { /* ignore */ }
// #endif
    return null;
}

function _restorefocus(fv) {
// #if PLATFORM == "win"
    try {
        if (fv)
            fv.scimoz.isFocused = true;
    } catch(e) { /* ignore */ }
// #endif
}

// Append a file filter to the given file picker.
//
//  "fp" is the nsIFilePicker instance
//  "title" is a name for the list of filetypes
//  "types" is a list of filetypes, e.g. ["*.exe", "*.com"]
//
function _appendFilter(fp, title, types) {
    // If no filters, Windows gets upset and truncates the list
    // (see http://bugs.activestate.com/show_bug.cgi?id=18815)
    if (types.length == 0)
        return;

// #if PLATFORM == "win"
    // Linux adds the types to the title automatically; Windows doesn't.
    title += ' (' + types.join(',') + ')';
// #endif
    fp.appendFilter(title, types.join('; '));
}

// Some languages map to the same extension, and this isn't
// reflected in the language registry.
var _altLanguageNames = {
    "Python3": "Python",
}
var _reverseAltLanguageNames = {
    "Python": "Python3"
}

/**
 * Append Komodo's standard set of file filters to the given filepicker.
 *
 *  "fp" is the nsIFilePicker instance
 *  "limitTo" (optional) is a list of filter names to which to limit the
 *      filters.
 *
 * The "standard" set of file filters is basically a set for each language in
 * Komodo's language registry plus a couple special categories.
 *
 * Returns the list of filter names appended.
 */
function _appendFilters(fp, limitTo /* =null */) {
    if (typeof(limitTo) == 'undefined') limitTo = null;
    var i, title, filter;

    // Get a list of special filters.
    // These are filters that are only included if asked for in 'limitTo'.
    // I.e., they should only be available under special circumstances.
    var specialNames = [];
    var specialFilters = [];
// #if PLATFORM == "win"
    specialNames.push("Executable");
    specialFilters.push(["*.exe", "*.com", "*.bat", "*.cmd"]);
// #endif
    specialNames.push("INI");
    specialFilters.push(["*.ini"]);
    specialNames.push("Icon");
    specialFilters.push(["*.png", "*.gif", "*.ico", "*.bmp", "*.xbm", ".xpm", ".jpg", ".jpeg"]);

    // Get a list of standard filters.
    var langRegistry = Cc["@activestate.com/koLanguageRegistryService;1"].
                       getService(Ci.koILanguageRegistryService);
    var countObj = new Object();
    var langsObj = new Object();
    langRegistry.getLanguageNames(langsObj, countObj);
    var languageNames = langsObj.value;

    var names = [];
    var filters = [];
    for (i = 0; i < languageNames.length; i++) {
        var filetypesObj = new Object();
        langRegistry.patternsFromLanguageName(languageNames[i], filetypesObj,
                                              countObj);
        var filetypes = filetypesObj.value;
        if (filetypes.length == 0) {
            // The nsIFilePicker stuff does NOT like one adding empty filter
            // lists.
            local.log.debug("No filetype patterns registered for '"+
                                 languageNames[i]+"' language. It is possible "+
                                 "that your language associations registry "+
                                 "is corrupted.");
        } else {
            names.push(languageNames[i]);
            filters.push(filetypesObj.value);
        }
    }
    names.push("Web");
    filters.push(["*.html", "*.htm", "*.css", "*.dtd", "*.xml", "*.xul",
                  "*.js"]);
    names.push(local.bundle.GetStringFromName("komodoProject"));
    filters.push(["*.komodoproject", "*.kpf"]);
    names.push(local.bundle.GetStringFromName("komodoPackage"));
    filters.push(["*.kpz"]);
    names.push(local.bundle.GetStringFromName("komodoColorScheme"));
    filters.push(["*.ksf"]);
    names.push("Komodo Tool");
    filters.push(["*.komodotool"]);
    names.push("Zip");
    filters.push(["*.zip"]);
    names.push(local.bundle.GetStringFromName("codeIntelligenceXml"));
    filters.push(["*.cix"]);
    names.push("All");
    filters.push(Ci.nsIFilePicker.filterAll);

    // Filter out some filters if 'limitTo' was specified.
    if (limitTo != null) {
        var limitToDict = {}; // use dictionary to optimize lookup
        for (i = 0; i < limitTo.length; ++i) {
            limitToDict[limitTo[i]] = true;
        }

        var limitedNames = [];
        var limitedFilters = [];
        for (i = 0; i < specialNames.length; ++i) {
            if (specialNames[i] in limitToDict) {
                limitedNames.push(specialNames[i]);
                limitedFilters.push(specialFilters[i]);
            }
        }
        for (i = 0; i < names.length; ++i) {
            if (names[i] in limitToDict) {
                limitedNames.push(names[i]);
                limitedFilters.push(filters[i]);
            } else if ((names[i] in _reverseAltLanguageNames)
                       && (_reverseAltLanguageNames[names[i]] in limitToDict)) {
                limitedNames.push(_reverseAltLanguageNames[names[i]]);
                limitedFilters.push(filters[i]);
            }
        }
        if (limitedNames.length == 0) {
            var err = "Illegal filter 'limitTo' list, the limited list of "+
                      "filters is empty: names="+names.join(',')+
                      " specialNames="+specialNames.join(',')+
                      " limitTo="+limitTo.join(',');
            local.log.error(err);
            throw(err);
        }
        names = limitedNames;
        filters = limitedFilters;
    }


    // Append all the filters.
    for (i = 0; i < names.length; ++i) {
        title = names[i] + " Files";
        filter = filters[i];
        if (typeof(filter) == "number") {
            fp.appendFilters(filter);
        } else if (filter.length == 0) {
            local.log.warn("dropping empty filter list for '"+title+"'");
        } else {
            _appendFilter(fp, title, filter);
        }
    }

    return names;
}

function _get_localDirFromPossibleURIDir(uri) {
    if (uri && uri.substr(0, 7) === "file://") {
        // ko.uriparse not always available when this is called from
        // dialog boxes, so go with xpcom.
        var koFileEx = Cc["@activestate.com/koFileEx;1"]
                             .createInstance(Ci.koIFileEx);
        koFileEx.URI = uri;
        return koFileEx.path;
    }
    return null;
}

var _dispatchTable = {
        // Some clients prefer project or place to the current view,
        // but saveAs should prefer the current view
    'project': function() {
        var dir, uri;
        if (ko.projects) {
            var project = ko.projects.manager.currentProject;
            if (project) {
                return _get_localDirFromPossibleURIDir(project.importDirectoryURI);
            }
        }
        return null;
    },
    'place': function() {
        var dir, uri;
        if (ko.places) {
            return _get_localDirFromPossibleURIDir(ko.places.manager.currentPlace);
        }
        return null;
    },
    'view': function() {
        var dir, uri;
        if (ko.views) {
            var view = ko.views.manager.currentView;
            if (view && view.getAttribute("type") === "editor") {
                var koFileEx = view.koDoc.file;
                if (koFileEx && koFileEx.isLocal) {
                    return koFileEx.dirName;
                }
            }
        }
        return null;
    }
};
function _get_defaultDirectory(dirTypes) {
    // Defaults, in this order: 
    // current project (if has local dir)
    // current place (if local)
    // current file (if editor)
    // leave null, do default.
    var dir, project, place, uri, view, i, lookupType;
    if (typeof(dirTypes) === "undefined") {
        dirTypes = ["view", "project", "place"];
    }
    for (var i = 0; i < dirTypes.length; i++) {
        lookupType = dirTypes[i];
        try {
            dir = _dispatchTable[lookupType]();
            if (dir) {
                return dir;
            }
        } catch(ex) {
            local.log.exception(ex, ("lookupType: "
                                + lookupType
                                + ": Problem finding current directory"));

        }
    }
    return null;
}

// Get a file picker.
//
//  "mode" is one of the nsIFilePicker.mode* flags.
//  "title" is the title for the dialog. Use 'null' for the default.
//  "defaultFilterName" (optional) is the filter to make the default.
//  "limitTo" (optional) is a list of filter names to which to restrict the
//      filter list.
//
function _getFilePicker(mode, title, defaultFilterName, limitTo)
{
    var fp = Cc["@mozilla.org/filepicker;1"].
             createInstance(Ci.nsIFilePicker);
    fp.init(window, title, mode);
    if (mode != Ci.nsIFilePicker.modeGetFolder) {
        if (limitTo == null && defaultFilterName != null) {
            var langRegistry = Cc["@activestate.com/koLanguageRegistryService;1"].
                getService(Ci.koILanguageRegistryService);
            var filetypesObj = {};
            var countObj = {};
            var altLanguageName;
            langRegistry.patternsFromLanguageName(defaultFilterName,
                                                  filetypesObj, countObj);
            if (countObj.value == 0
                && !!(altLanguageName = _altLanguageNames[defaultFilterName])) {
                langRegistry.patternsFromLanguageName(altLanguageName,
                                                      filetypesObj, countObj);
            }
            if (countObj.value > 0) {
                limitTo = [defaultFilterName, "All"];
            }
        }
        var filterNames = _appendFilters(fp, limitTo);

        // Set the filter index to that of the named default filter.
        if (defaultFilterName != null) {
            var filterIndex = filterNames.indexOf(defaultFilterName);
            if (filterIndex != -1) {
                fp.filterIndex = filterIndex;
            } else {
                local.log.info("Could not find '" + defaultFilterName +
                                    "' filter -- using default.");
                defaultFilterName = null; // trigger next if-block
            }
        }
        if (defaultFilterName == null) {
            // If the list of filters is limited then we default to the first
            // filter. Otherwise we default to the _last_ one ("All Files").
            if (limitTo != null) {
                fp.filterIndex = 0;
            } else {
                fp.filterIndex = filterNames.length - 1;
            }
        }
    }

    return fp;
}


function _getOpenFilePicker(title, defaultFilterName, limitTo) {
    return _getFilePicker(Ci.nsIFilePicker.modeOpen, title, defaultFilterName,
                          limitTo);
}


function _getSaveFilePicker(title, defaultFilterName, limitTo) {
    return _getFilePicker(Ci.nsIFilePicker.modeSave, title, defaultFilterName,
                          limitTo);
}


function _getOpenExeFilePicker(title) {
    var limitTo;
// #if PLATFORM == "win"
    limitTo = ["Executable", "All"];
// #else
    limitTo = ["All"];
// #endif
    return _getFilePicker(Ci.nsIFilePicker.modeOpen, title, null, limitTo);
}


function _getOpenFilesPicker(title, defaultFilterName, limitTo) {
    return _getFilePicker(Ci.nsIFilePicker.modeOpenMultiple, title,
                          defaultFilterName, limitTo);
}


function _getGetFolderPicker(title) {
    return _getFilePicker(Ci.nsIFilePicker.modeGetFolder, title);
}


function _browseForFile(pickerFn,
                        defaultDirectory /* =null */,
                        defaultFilename /* =null */,
                        title /* ="Open File" */,
                        defaultFilterName /* ="All" */,
                        filterNames /* =null */)
{
    if (typeof(defaultDirectory) == 'undefined') defaultDirectory = null;
    if (typeof(defaultFilename) == 'undefined') defaultFilename = null;
    if (typeof(title) == 'undefined' || title == null) title = "Open File";
    if (typeof(defaultFilterName) == 'undefined') defaultFilterName = null;
    if (typeof(filterNames) == 'undefined') filterNames = null;
    var fp = pickerFn(title, defaultFilterName, filterNames);

    if (!defaultDirectory && defaultFilename) {
        try {
            defaultDirectory = local.osPathSvc.dirname(defaultFilename);
        } catch (ex) { /* do nothing */ }
    }
    if (!defaultDirectory) {
        defaultDirectory = _get_defaultDirectory();
    }
    if (defaultDirectory) {
        try {
            var localFile = Cc["@mozilla.org/file/local;1"]
                            .createInstance(Ci.nsILocalFile);
            localFile.initWithPath(defaultDirectory);
            fp.displayDirectory = localFile;
        } catch (ex) {
            local.log.warn("problem setting '"+defaultDirectory+
                                 "' as default directory, defaulting to home directory.");
            var localFile = Cc["@mozilla.org/file/local;1"]
                            .createInstance(Ci.nsILocalFile);
            defaultDirectory = local.osPathSvc.expanduser("~");
            localFile.initWithPath(defaultDirectory);
            fp.displayDirectory = localFile;
        }
    }
    if (defaultFilename) {
        fp.defaultString = local.osPathSvc.basename(defaultFilename);
    } else {
        fp.defaultString = null;
    }

    var fv = _unfocus();
    var retval = fp.show();
    _restorefocus(fv);
    if (retval == Ci.nsIFilePicker.returnOK) {
        //XXX Should we do any special handling if this is a symlink?
        return fp.file.path;
    }
    return null;
}

//---- public methods

/**
 * Browse for a file.
 *
 * @param {String} "defaultDirectory" (optional) is the directory in which to start looking.
 *      If left unspecified (or null) the last directory in which this file
 *      picker was opened is used.
 * @param {String} "defaultFilename" (optional) is a suggested filename for the user to
 *      choose. If "defaultDirectory" is not specified then a fullpath can be
 *      used here to specify a default directory and filename. E.g.,
 *          ko.filepicker.openFile(null, "D:\\trentm\\foo.txt");
 *      will set the default dir and filename to "D:\\trentm" and "foo.txt",
 *      respectively.
 * @param {String} "title" (optional) is the title for the file picker dialog.
 * @param {String} "defaultFilterName" (optional) is the name of a filter which should be
 *      selected by default in the file picker dialog. By default the "All"
 *      File filter is the default. Other filters are any of Komodo's supported
 *      languages, e.g. "Python", "PHP", plus some special filters like "Komodo
 *      Project" and "Web".
 * @param {Array} "filterNames" (optional) is a list of filter names to which to restrict the
 *      file picker.  If this is not specified (or null) the whole set of
 *      standard filters is used.  It is recommended that "All" always be
 *      included, and included last.  For example, the following might be
 *      appropriate for picking a Komodo macro file:
 *          ["Python", "JavaScript", "All"]
 *
 * @returns {String} the full local path the selected file, or null if the dialog is
 * cancelled.
 */
this.browseForFile = function filepicker_openFile(defaultDirectory /* =null */,
                             defaultFilename /* =null */,
                             title /* ="Open File" */,
                             defaultFilterName /* ="All" */,
                             filterNames /* =null */)
{
    return _browseForFile(_getOpenFilePicker, defaultDirectory,
                          defaultFilename, title, defaultFilterName, filterNames);
}

/**
 * Pick an executable file for open.
 *
 * @param {String} "defaultDirectory" (optional) is the directory in which to start looking.
 *      If left unspecified (or null) the last directory in which this file
 *      picker was openned in used.
 * @param {String} "defaultFilename" (optional) is a suggested filename for the user to
 *      choose. If "defaultDirectory" is not specified then a fullpath can be
 *      used here to specify a default directory and filename. E.g.,
 *          ko.filepicker.openFile(null, "D:\\trentm\\foo.txt");
 *      will set the default dir and filename to "D:\\trentm" and "foo.txt",
 *      respectively.
 * @param {String} "title" (optional) is the title for the file picker dialog.
 *
 * @returns {String} the full local path the selected file, or null.
 */
this.browseForExeFile = function filepicker_openExeFile(defaultDirectory /* =null */,
                                defaultFilename /* =null */,
                                title /* ="Open Executable File" */)
{
    // Same as browseForFile, but with less arguments.
    if (typeof(title) == 'undefined' || title == null) title = "Open Executable File";
    return ko.filepicker.browseForFile(defaultDirectory, defaultFilename, title,
                                       null, null,
                                       _getOpenFilePicker);
}

/**
 * Pick a file for save.
 *
 * @param {String} "defaultDirectory" (optional) is the directory in which to start looking.
 *      If left unspecified (or null) the last directory in which this file
 *      picker was opened is used.
 * @param {String} "defaultFilename" (optional) is a suggested filename for the user to
 *      choose. If "defaultDirectory" is not specified then a fullpath can be
 *      used here to specify a default directory and filename. E.g.,
 *          ko.filepicker.saveFile(null, "D:\\trentm\\foo.txt");
 *      will set the default dir and filename to "D:\\trentm" and "foo.txt",
 *      respectively.
 * @param {String} "title" (optional) is the title for the file picker dialog.
 * @param {String} "defaultFilterName" (optional) is the name of a filter which should be
 *      selected by default in the file picker dialog. By default the "All"
 *      File filter is the default. Other filters are any of Komodo's supported
 *      languages, e.g. "Python", "PHP", plus some special filters like "Komodo
 *      Project" and "Web".
 * @param {String} "filterNames" (optional) is a list of filter names to which to restrict the
 *      file picker.  If this is not specified (or null) the whole set of
 *      standard filters is used.  It is recommended that "All" always be
 *      included, and included last.  For example, the following might be
 *      appropriate for picking a Komodo macro file:
 *          ["Python", "JavaScript", "All"]
 *
 * If the selected filename does not have an extension the user *may* be asked
 * if one should be added. See the code below for the gory details of when and
 * what extension is added.
 *
 * @returns {String} the full local path the selected file, or null if the dialog is
 * cancelled.
 */
this.saveFile = function filepicker_saveFile(defaultDirectory /* =null */,
                             defaultFilename /* =null */,
                             title /* ="Save File" */,
                             defaultFilterName /* ="All" */,
                             filterNames /* =null */)
{
    if (typeof(defaultDirectory) == 'undefined') defaultDirectory = null;
    if (typeof(defaultFilename) == 'undefined') defaultFilename = null;
    if (typeof(title) == 'undefined' || title == null) title = "Save File";
    if (typeof(defaultFilterName) == 'undefined') defaultFilterName = null;
    if (typeof(filterNames) == 'undefined') filterNames = null;
    var i;
    var fp = _getSaveFilePicker(title, defaultFilterName,
                                           filterNames);

    if (!defaultDirectory && defaultFilename) {
        try {
            defaultDirectory = local.osPathSvc.dirname(defaultFilename);
        } catch (ex) { /* do nothing */ }
    }
    if (!defaultDirectory) {
        defaultDirectory = _get_defaultDirectory(["view", "project", "place"]);
    }
    if (defaultDirectory) {
        try {
            var localFile = Cc["@mozilla.org/file/local;1"]
                            .createInstance(Ci.nsILocalFile);
            localFile.initWithPath(defaultDirectory);
            fp.displayDirectory = localFile;
        } catch (ex) {
            local.log.error("problem setting '"+defaultDirectory+
                                 "' as default directory for file picker");
        }
    }
    if (defaultFilename) {
        fp.defaultString = local.osPathSvc.basename(defaultFilename);
    } else {
        fp.defaultString = null;
    }

    var fv = _unfocus();
    var retval = fp.show();
    _restorefocus(fv);
    if (retval == Ci.nsIFilePicker.returnReplace) {
        // Never attempt to force an extension on an existing file.
        return fp.file.path;
    } else if (retval != Ci.nsIFilePicker.returnOK) {
        // User cancelled the dialog.
        return null;
    } else {
        var path = fp.file.path;
        // Determine if should ask to force an extension.
        // - If path already has an extension, then no.
        var ext = local.osPathSvc.getExtension(path);
        if (ext) {
            return path;
        }

        // Determine the file extension to append.
        ext = null;
        if (defaultFilename) {
            ext = local.osPathSvc.getExtension(defaultFilename);
            if (!ext) ext = null;
        }
        if (ext == null && defaultFilterName) {
            // Try the first of registered extension for the default filter
            // name (presuming it is a language).
            var langRegistry = Cc["@activestate.com/koLanguageRegistryService;1"].
                               getService(Ci.koILanguageRegistryService);
            var langFiltersObj = new Object();
            var countObj = new Object();
            langRegistry.patternsFromLanguageName(defaultFilterName,
                                                  langFiltersObj,
                                                  countObj);
            var langFilters = langFiltersObj.value;
            for (i = 0; i < langFilters.length; ++i) {
                // Look for "*.foo"-type file associations.
                var matches = langFilters[i].match(/^\*(\.\w+)$/);
                if (matches) {
                    ext = matches[1];
                    break;
                }
            }
        }

        // Ask the user
        if (ext != null) {
            var basename = local.osPathSvc.basename(path);
            var prompt = local.bundle.formatStringFromName("filenameDoesNotHaveAnExtension",
                                                      [basename, ext],
                                                      2);
            var answer = ko.dialogs.yesNoCancel(prompt, "Yes", null, null,
                                            "ensure_filename_has_ext");
            if (answer == "Yes") {
                path = path+ext;
            } else if (answer == "Cancel") {
                return null;
            } // else "No": leave path alone.
        }
        return path;
    }

    return null;
}

/**
 * Pick multiple files.
 *
 * @param {String} "defaultDirectory" (optional) is the directory in which to start looking.
 *      If left unspecified (or null) the last directory in which this file
 *      picker was opened is used.
 * @param {String} "defaultFilename" (optional) is a suggested filename for the user to
 *      choose. If "defaultDirectory" is not specified then a fullpath can be
 *      used here to specify a default directory and filename. E.g.,
 *          ko.filepicker.openFile(null, "D:\\trentm\\foo.txt");
 *      will set the default dir and filename to "D:\\trentm" and "foo.txt",
 *      respectively.
 * @param {String} "title" (optional) is the title for the file picker dialog.
 * @param {String} "defaultFilterName" (optional) is the name of a filter which should be
 *      selected by default in the file picker dialog. By default the "All"
 *      File filter is the default. Other filters are any of Komodo's supported
 *      languages, e.g. "Python", "PHP", plus some special filters like "Komodo
 *      Project" and "Web".
 * @param {String} "filterNames" (optional) is a list of filter names to which to restrict the
 *      file picker.  If this is not specified (or null) the whole set of
 *      standard filters is used.  It is recommended that "All" always be
 *      included, and included last.  For example, the following might be
 *      appropriate for picking a Komodo macro file:
 *          ["Python", "JavaScript", "All"]
 *
 * @returns {Array} a list of the paths selected or null if the dialog is cancelled.
 */
this.browseForFiles = function filepicker_openFiles(defaultDirectory /* =null */,
                              defaultFilename /* =null */,
                              title /* ="Open File" */,
                              defaultFilterName /* ="All" */,
                              filterNames /* =null */)
{
    if (typeof(defaultDirectory) == 'undefined') defaultDirectory = null;
    if (typeof(defaultFilename) == 'undefined') defaultFilename = null;
    if (typeof(title) == 'undefined' || title == null) title = "Open File";
    if (typeof(defaultFilterName) == 'undefined') defaultFilterName = null;
    if (typeof(filterNames) == 'undefined') filterNames = null;
    var fp = _getOpenFilesPicker(title, defaultFilterName,
                                            filterNames);

    if (!defaultDirectory && defaultFilename) {
        try {
            defaultDirectory = local.osPathSvc.dirname(defaultFilename);
        } catch (ex) { /* do nothing */ }
    }
    if (!defaultDirectory) {
        defaultDirectory = _get_defaultDirectory();
    }
    if (defaultDirectory) {
        try {
            var localFile = Cc["@mozilla.org/file/local;1"]
                            .createInstance(Ci.nsILocalFile);
            localFile.initWithPath(defaultDirectory);
            fp.displayDirectory = localFile;
        } catch (ex) {
            local.log.warn("problem setting '"+defaultDirectory+
                                 "' as default directory, defaulting to home directory.");
            var localFile = Cc["@mozilla.org/file/local;1"]
                            .createInstance(Ci.nsILocalFile);
            defaultDirectory = local.osPathSvc.expanduser("~");
            localFile.initWithPath(defaultDirectory);
            fp.displayDirectory = localFile;
        }
    }
    if (defaultFilename) {
        fp.defaultString = local.osPathSvc.basename(defaultFilename);
    } else {
        fp.defaultString = null;
    }

    var fv = _unfocus();
    var retval = fp.show();
    _restorefocus(fv);
    if (retval == Ci.nsIFilePicker.returnOK) {
        var paths = [];
        var files = fp.files;
        while (files.hasMoreElements()) {
            var file = files.getNext();
            file.QueryInterface(Ci.nsILocalFile);
            paths.push(file.path);
        }
        return paths;
    }
    return null;
}

/**
 * Pick a directory/folder.
 *
 * @param {String} "defaultDirectory" (optional) is the directory in which to start looking.
 *      If left unspecified (or null) the last directory in which this file
 *      picker was opened is used.
 * @param {String} "prompt" (optional) is some text that is displayed at the top of the dir
 *      selection dialog (on Windows at least).
 *
 * @returns {String} the full local path the selected directory, or null if the dialog is
 * cancelled.
 */
this.getFolder = function filepicker_getFolder(defaultDirectory /* =null */,
                              prompt /* =null */)
{
    if (typeof(defaultDirectory) == 'undefined') defaultDirectory = null;
    if (typeof(prompt) == 'undefined') prompt = null;
    var fp = _getGetFolderPicker(prompt);

    if (!defaultDirectory) {
        defaultDirectory = _get_defaultDirectory();
    }
    if (defaultDirectory) {
        try {
            var localFile = Cc["@mozilla.org/file/local;1"]
                            .createInstance(Ci.nsILocalFile);
            localFile.initWithPath(defaultDirectory);
            fp.displayDirectory = localFile;
        } catch (ex) {
            local.log.error("problem setting '"+defaultDirectory+
                                 "' as default directory for file picker");
        }
    }

    var fv = _unfocus();
    var retval = fp.show();
    _restorefocus(fv);
    if (retval == Ci.nsIFilePicker.returnOK) {
        var path = fp.file.path;
// #if PLATFORM == "win"
        // Fix http://bugs.activestate.com/show_bug.cgi?id=23185
        // The problem is that select a drive root on Windows returns "C:",
        // withOUT the trailing slash. This means the actual dir use depends on
        // the current dir for that drive on the user's machine.
        if (path.length == 2 && path[1] == ":") {
            path += "\\";
        }
// #endif
        return path;
    }
    return null;
}

/**
 * Private variable for remembering what the last remote file location used
 * was, we can uses this as the default location on subsequent remote file
 * dialog openings.
 * @private
 */
var _lastRemoteLocation = "";

/**
 * Browse for remote file(s)
 *
 * @param {String} "defaultUrl" (optional) is the remote url specifiying -
 *      XXX - This is ugly, perhaps pass in as seperate parameters??
 *      Format: "protocol: *[username:password@]servername:port/path_to_directory"
 *      Format: "protocol: *server_alias/path_to_directory"
 *          Protocol used (ex. "ftp", "sftp", "scp")
 *          Remote server username and password (optional)
 *          Remote server name and port (ex. "testserver:22")
 *          Server alias can be used instead of full username, password, host...
 *          Initial directory path
 *          Example1: "sftp: *testserver:22/home/testuser"
 *          Example2: "sftp: *testuser:testing@testserver:22/~/"
 *          Example3: "sftp: *test_server/dir1/"    # Server alias used
 *      If left unspecified (or null) then the user will need to select the
 *      server alias (via dropdown) before the remote file dialog is populated.
 * @param {String} "defaultFilename" (optional) is a suggested filename for the user to choose
 * @param {String} "mode" (optional) use of the file picker dialog (open/save).
 * @param {String} "title" (optional) is the title for the file picker dialog.
 * @param {String} "defaultFilterName" (optional) is the name of a filter which should be
 *      selected by default in the file picker dialog. By default the "All"
 *      File filter is the default. Other filters are any of Komodo's supported
 *      languages, e.g. "Python", "PHP", plus some special filters like "Komodo
 *      Project" and "Web".
 * @param {Array} "filterNames" (optional) is a list of filter names to which to restrict the
 *      file picker.  If this is not specified (or null) the whole set of
 *      standard filters is used.  It is recommended that "All" always be
 *      included, and included last.  For example, the following might be
 *      appropriate for picking a Komodo macro file:
 *          ["Python", "JavaScript", "All"]
 * @param {String} "helpTag" (optional) html context for komodo remote file help.
 *
 * @returns {Object} containing the selected file(s) info.
 *   Object (retval) structure is below:
 *    retval.filepaths      : array of the selected urls
 *    retval.directory      : directory url, if selecting a dir
 *    retval.file           : file object for selected file
 *    retval.buttonStatus   : returned result from file browser dialog
 *    retval.server         : server alias/name
 */
this.remoteFileBrowser = function filepicker_remoteFileBrowser(defaultUrl /*=""*/,
                                      defaultFilename /*=""*/,
                                      mode /*=nsIFilePicker.modeOpen*/,
                                      title /*="Open File"*/,
                                      defaultFilterName /*=["All Files"]*/,
                                      filterNames /*=["*.*"]*/,
                                      helpTag /*="Open Remote File"*/)
{
   var fileBrowser = new Object();
   fileBrowser.filters = new Object();
   fileBrowser.displayDirectory = new Object();

   if (typeof(title) == "undefined" || !title)
       title = local.bundle.GetStringFromName("openFile");
   fileBrowser.title = title;

   if (typeof(defaultUrl) == "undefined" || !defaultUrl) {
      defaultUrl = _lastRemoteLocation;
      // Note: ko.views may be empty when used from a Komodo dialog.
      if (ko.views) {
         // If the current file is a remote file, use that location, else fall
         // back to the last opened remote location.
         var currentView = ko.views.manager.currentView;
         if (currentView && currentView.koDoc && currentView.koDoc.file &&
             currentView.koDoc.file.isRemoteFile) {
            defaultUrl = currentView.koDoc.file.URI;
         }
      }
   }
   fileBrowser.displayDirectory.path = defaultUrl;

   // get the default filename
   if (typeof(defaultFilename) == "undefined" || !defaultFilename)
       defaultFilename = "";
   fileBrowser.defaultString = defaultFilename;

   // get the mode
   if (typeof(mode) == "undefined" || !mode)
       mode = Ci.nsIFilePicker.modeOpen;
   fileBrowser.mode = mode;

   // set up the types
   if (typeof(defaultFilterName) == "undefined" || !defaultFilterName) {
       defaultFilterName = ["All Files"];
       filterNames = ["*.*"];
   }

   // set up the types
   if (typeof(helpTag) == "undefined" || !helpTag) {
       helpTag = "opening_remote_files";
   }
   fileBrowser.helpTag = helpTag;

   fileBrowser.filters.titles = defaultFilterName;
   fileBrowser.filters.types = filterNames;

   // The retvals object will be returned
   fileBrowser.retvals = new Object();
   fileBrowser.retvals.filepaths = null;
   fileBrowser.retvals.directory = null;
   fileBrowser.retvals.file = null;
   fileBrowser.retvals.buttonStatus = null;
   fileBrowser.retvals.server = null;

   var response = ko.windowManager.openDialog(
        "chrome://komodo/content/dialogs/filebrowser/filebrowser.xul",
        "Komodo:OpenRemote",
        "chrome,centerscreen,resizable=yes,close,dependent,modal=yes",
        fileBrowser);
   if (response) {
       if ((fileBrowser.retvals.buttonStatus == Ci.nsIFilePicker.returnOK) &&
           fileBrowser.retvals.file) {
          // Save the lastRemoteLocation
          var pos = fileBrowser.retvals.file.lastIndexOf('/')
          if (pos > 0)
             _lastRemoteLocation = fileBrowser.retvals.file.substring(0, pos);
       }
       return fileBrowser.retvals;
   }
   return null;
}

/**
 * Open remote file(s)
 *   Same parameters meanings as "ko.filepicker.remoteFileBrowser" (above)
 * Returns nothing. Note: The files will be opened through this function call
 */
this.openRemoteFiles = function filepicker_openRemoteFiles(defaultUrl, defaultFilename, defaultFilterName, filterNames) {
    var list;
    var fileBrowser = ko.filepicker.remoteFileBrowser(
            defaultUrl, defaultFilename, 
            Ci.nsIFilePicker.modeOpen,
            local.bundle.GetStringFromName("openFiles"),
            defaultFilterName, filterNames,
            local.bundle.GetStringFromName("openRemoteFile"));
    if (fileBrowser) {
        if (fileBrowser.filepaths && fileBrowser.filepaths.length > 0) {
            // One or more files selected, list of remote urls
            //if (fileBrowser.server) dump(fileBrowser.server.alias+": ");
            //dump("file selection is "+fileBrowser.filepaths[i]+"\n");
            list = fileBrowser.filepaths;
        } else if (fileBrowser.file) {
            // One file selected, this is a remote url
            //if (fileBrowser.server) dump(fileBrowser.server.alias+": ");
            //dump("file selection is "+fileBrowser.file+"\n");
            list = new Array();
            list.push(fileBrowser.file);
        } else if (fileBrowser.directory) {
            // One directory selected, this is NOT a remote url
            //if (fileBrowser.server) dump(fileBrowser.server.alias+": ");
            //dump("directory selection is "+fileBrowser.directory+"\n");
            list = new Array();
            list.push(fileBrowser.directory);
        } else {
            //dump("There was no selection!\n");
        }
    }
    if (list)
        ko.open.multipleURIs(list);
}

/**
 * Choose remote filename to save as
 *   Same parameters meanings as "ko.filepicker.remoteFileBrowser" (above)
 * Returns the remote url of the selected file, or null if the dialog is
 * cancelled.
 */
this.saveAsRemoteFiles = function filepicker_saveAsRemoteFiles(defaultUrl, defaultFilename, defaultFilterName, filterNames) {
    var fileBrowser = ko.filepicker.remoteFileBrowser(
            defaultUrl, defaultFilename,
            Ci.nsIFilePicker.modeSave,
            local.bundle.GetStringFromName("saveFileAs"),
            defaultFilterName, filterNames,
            local.bundle.GetStringFromName("saveRemotelyAs"));
    if (fileBrowser) {
        return fileBrowser.file;
    }
    return null;
}

/**
 * A dialog to pick a directory, and put the directory path into a XUL
 * textbox.
 *
 * @param {Element} textbox
 */
this.browseForDir = function filepicker_browseForDir(textbox) {
    var dir = ko.filepicker.getFolder(textbox.value);
    if (dir) {
        textbox.value = dir;
    }
};

/**
 * A dialog to pick a remote directory and put the path into a XUL textbox.
 *
 * @param {Element} textbox
 */
this.browseForRemoteDir = function filepicker_browseForRemoteDir(textbox) {
    var defaultUrl = "";
    if (textbox.value) {
        var RCService = Cc["@activestate.com/koRemoteConnectionService;1"].
                        getService(Ci.koIRemoteConnectionService);
        // Only set the default url if it's actually a remote url, otherwsie
        // we'll get an erro about an unknown protocol.
        if (RCService.isSupportedRemoteUrl(textbox.value)) {
            defaultUrl = textbox.value;
        }
    }
    var retval = ko.filepicker.remoteFileBrowser(defaultUrl,
                                              "" /* defaultFilename */,
                                              Ci.nsIFilePicker.modeGetFolder);
    if (retval && retval.file) {
        textbox.value = retval.file;
    }
};

/**
 * Same as ko.filepicker.browseForFile.
 *
 * @deprecated since Komodo 6.0.0
 */
this.openFile = function filepicker_openFile(defaultDirectory /* =null */,
                             defaultFilename /* =null */,
                             title /* ="Open File" */,
                             defaultFilterName /* ="All" */,
                             filterNames /* =null */) {
    local.log.deprecated('`ko.filepicker.openFile` is deprecated, use `ko.filepicker.browseForFile`');
    return ko.filepicker.browseForFile.apply(this, arguments);
}

/**
 * Same as ko.filepicker.browseForExeFile.
 *
 * @deprecated since Komodo 6.0.0
 */
this.openExeFile = function filepicker_openExeFile(defaultDirectory /* =null */,
                             defaultFilename /* =null */,
                             title /* ="Open Executable File" */) {
    local.log.deprecated('`ko.filepicker.openExeFile` is deprecated, use `ko.filepicker.browseForExeFile`');
    return ko.filepicker.browseForFile.apply(this, arguments);
}

/**
 * Same as ko.filepicker.browseForFiles.
 *
 * @deprecated since Komodo 6.0.0
 */
this.openFiles = function filepicker_openFiles(defaultDirectory /* =null */,
                              defaultFilename /* =null */,
                              title /* ="Open File" */,
                              defaultFilterName /* ="All" */,
                              filterNames /* =null */)
{
    local.log.deprecated('`ko.filepicker.openFiles` is deprecated, use `ko.filepicker.browseForFiles`');
    return ko.filepicker.browseForFiles.apply(this, arguments);
}

/**
 * Use the prefs system to track default dirs for particular calls
 * to the various file-pickers.  Goal: avoid defaulting to the
 * last dir used by a different file-picker client.
 
 * @param {String} label
 * @param {String} dir
 * @returns {String} last stored directory if dir is null, dir if dir isn't null
 */
this.internDefaultDir = function internDefaultDir(label, dir) {
    if (!dir) {
        dir = local.prefs.getString(label, "");
        if (dir && local.osPathSvc.isdir(dir)) {
            return dir;
        }
        return null;
    }
    local.prefs.setStringPref(label, dir);
    // This has to be done each time to make sure new pref settings stick
    local.globalPrefs.setPref("filepickers.defaultDirs", local.prefs);
    return dir;
};

/**
 * Use the prefs system to track default dirs for particular calls
 * to the various file-pickers.  Goal: avoid defaulting to the
 * last dir used by a different file-picker client.
 
 * @param {String} label
 * @param {String} path
 * @returns {String} last stored directory if dir is null, dir if dir isn't null
 */
this.updateDefaultDirFromPath = function updateDefaultDirFromPath(label, path) {
    if (!path) {
        return null;
    }
    var newDir = local.osPathSvc.dirname(path);
    ko.filepicker.internDefaultDir(label, newDir);
    return newDir;
};

this.getExistingDirFromPathOrPref = function getExistingDirFromPath(path, label) {
    if (!path) {
        return ko.filepicker.internDefaultDir(label);
    }
    if (local.osPathSvc.exists(path)) {
        if (local.osPathSvc.isdir(path)) {
            return path;
        }
        return local.osPathSvc.dirname(path);
    }
    path = local.osPathSvc.dirname(path);
    return local.osPathSvc.exists(path) ? path : ko.filepicker.internDefaultDir(label);
};

}).apply(ko.filepicker);
