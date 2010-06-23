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
 *      ko.filepicker.openFile(...)        Pick a file for open.
 *      ko.filepicker.openExeFile(...)     Pick an executable file for open.
 *      ko.filepicker.saveFile(...)        Pick a file for saving.
 *      ko.filepicker.openFiles(...)       Pick multiple files for open.
 *      ko.filepicker.getFolder(...)       Pick a folder/directory.
 *
 * Example:
 *  Most of filepicker_*() methods have the same options so this example should
 *  translate to all of them. Say you would like the user to open a saved macro
 *  file. The following might be appropriate:
 *      var path = ko.filepicker.openFile(<macros dir>, // default dir
 *                                     null, // default filename
 *                                     "Open Macro", // title
 *                                     "JavaScript", // default filter name
 *                                     ["JavaScript", "Python", "All"]);
 *
 */
ko.filepicker = {};
(function() {

var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
                .getService(Components.interfaces.nsIStringBundleService)
                .createBundle("chrome://komodo/locale/library.properties");
var _log = ko.logging.getLogger("filepickers");


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
    var langRegistry = Components.classes["@activestate.com/koLanguageRegistryService;1"].
                       getService(Components.interfaces.koILanguageRegistryService);
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
            _log.debug("No filetype patterns registered for '"+
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
    names.push(_bundle.GetStringFromName("komodoProject"));
    filters.push(["*.komodoproject", "*.kpf"]);
    names.push(_bundle.GetStringFromName("komodoPackage"));
    filters.push(["*.kpz"]);
    names.push(_bundle.GetStringFromName("komodoColorScheme"));
    filters.push(["*.ksf"]);
    names.push("Komodo Tool");
    filters.push(["*.komodotool"]);
    names.push("Zip");
    filters.push(["*.zip"]);
    names.push(_bundle.GetStringFromName("codeIntelligenceXml"));
    filters.push(["*.cix"]);
    names.push("All");
    filters.push(Components.interfaces.nsIFilePicker.filterAll);

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
            }
        }
        if (limitedNames.length == 0) {
            var err = "Illegal filter 'limitTo' list, the limited list of "+
                      "filters is empty: names="+names.join(',')+
                      " specialNames="+specialNames.join(',')+
                      " limitTo="+limitTo.join(',');
            _log.error(err);
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
            _log.warn("dropping empty filter list for '"+title+"'");
        } else {
            _appendFilter(fp, title, filter);
        }
    }

    return names;
}


//---- cached file picker initializers

// All caching is done in the _cache dictionary.  The cache looks
// like this:
//    _cache = {
//        "openFile": {
//            "fp": <open file nsIFilePicker>,
//            "title": <current title for file picker>,
//            ...other cached info...
//        }
//        ...other picker caches...
//    }
var _cache = null;

function _getCache(name) {
    if (_cache == null)
        _cache = new Object();
    if (!(name in _cache))
        _cache[name] = new Object();
    return _cache[name];
}


// Get a (possibly cached) file picker.
//
//  "cache" is a cache object for this type of file picker.
//  "mode" is one of the nsIFilePicker.mode* flags.
//  "title" is the title for the dialog. Use 'null' for the default.
//  "defaultFilterName" (optional) is the filter to make the default.
//  "limitTo" (optional) is a list of filter names to which to restrict the
//      filter list.
//
function _getFilePicker(cache, mode, title, defaultFilterName,
                                   limitTo)
{
    if (typeof(defaultFilterName) == 'undefined') defaultFilterName = null;
    if (typeof(limitTo) == 'undefined') limitTo = null;

    // == operator that can handle lists
    function equal(a, b) {
        //ump("equal(a,b): a="+a+" ("+typeof(a)+"), b="+b+" ("+typeof(b)+")\n");
        if (typeof(a) != typeof(b))
            return false;
        else if (a == null && b == null)
            return true;
        else if (a == null || b == null)
            return false;
        // Presume they are arrays. If they are not, then we cannot compare
        // them and an error will be raised.
        else if (a.join(',') ==  b.join(','))
            return true;
        else
            return false;
    }

    if (!("fp" in cache) || (!("limitTo" in cache) || !equal(limitTo, cache.limitTo)))
    {
        // Data point: caching the instance creation makes a HUGE time diff on
        // 10,000 calls.
        var fp = Components.classes["@mozilla.org/filepicker;1"].
                 createInstance(Components.interfaces.nsIFilePicker);
        fp.init(window, title, mode);
        if (mode != Components.interfaces.nsIFilePicker.modeGetFolder) {
            // Data point: caching appending the standard filters makes a
            // significant difference on 10,000 calls (a few seconds).
            var filterNames = _appendFilters(fp, limitTo);
            cache.limitTo = limitTo;
            cache.filterNames = filterNames;
        }
        cache.title = title;
        cache.fp = fp;
    }

    // Data point: caching the title made the difference between 0.439 seconds
    // and 1.109 seconds for 10,000 calls to filepicker_openFile(). Not that
    // big a deal, but better than a kick in the pants.
    if (cache.title != title) {
        cache.fp.init(window, title, mode);
        cache.title = title;
    }

    if (mode != Components.interfaces.nsIFilePicker.modeGetFolder) {
        // Set the filter index to that of the named default filter.
        if (defaultFilterName != null) {
            var foundIt = false;
            for (var i = 0; i < cache.filterNames.length; ++i) {
                if (defaultFilterName == cache.filterNames[i]) {
                    cache.fp.filterIndex = i;
                    foundIt = true;
                    break;
                }
            }
            if (!foundIt) {
                _log.info("Could not find '"+defaultFilterName+
                                    "' filter -- using default.");
                defaultFilterName = null; // trigger next if-block
            }
        }
        if (defaultFilterName == null) {
            // If the list of filters is limited then we default to the first
            // filter. Otherwise we default to the _last_ one ("All Files").
            if (limitTo != null) {
                cache.fp.filterIndex = 0;
            } else {
                cache.fp.filterIndex = cache.filterNames.length - 1;
            }
        }
    }

    return cache.fp;
}


function _getOpenFilePicker(title, defaultFilterName, limitTo) {
    var cache = _getCache("openFile");
    return _getFilePicker(
                cache,
                Components.interfaces.nsIFilePicker.modeOpen,
                title,
                defaultFilterName,
                limitTo);
}


function _getSaveFilePicker(title, defaultFilterName, limitTo) {
    var cache = _getCache("saveFile");
    return _getFilePicker(
                cache,
                Components.interfaces.nsIFilePicker.modeSave,
                title,
                defaultFilterName,
                limitTo);
}


function _getOpenExeFilePicker(title) {
    var cache = _getCache("openExeFile");
    var limitTo;
// #if PLATFORM == "win"
    limitTo = ["Executable", "All"];
// #else
    limitTo = ["All"];
// #endif
    return _getFilePicker(
                cache,
                Components.interfaces.nsIFilePicker.modeOpen,
                title,
                null,
                limitTo);
}


function _getOpenFilesPicker(title, defaultFilterName, limitTo) {
    var cache = _getCache("openFiles");
    return _getFilePicker(
                cache,
                Components.interfaces.nsIFilePicker.modeOpenMultiple,
                title,
                defaultFilterName,
                limitTo);
}


function _getGetFolderPicker(title) {
    var cache = _getCache("getFolder");
    return _getFilePicker(
                cache,
                Components.interfaces.nsIFilePicker.modeGetFolder,
                title);
}



//---- public methods

/**
 * Pick a file for open.
 *
 * @param {String} "defaultDirectory" (optional) is the directory in which to start looking.
 *      If left unspecified (or null) the last directory in which this file
 *      picker was opened is used.
 * @param {String} "defaultFilename" (optional) is a suggested filename for the user to
 *      choose. If "defaultDirectory" is not specified then a fullpath can be
 *      used here to specify a default directory and filename. E.g.,
 *          filepicker_openFile(null, "D:\\trentm\\foo.txt");
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
this.openFile = function filepicker_openFile(defaultDirectory /* =null */,
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
    var fp = _getOpenFilePicker(title, defaultFilterName,
                                           filterNames);

    if (!defaultDirectory && defaultFilename) {
        try {
            defaultDirectory = ko.uriparse.dirName(defaultFilename);
        } catch (ex) { /* do nothing */ }
    }
    if (defaultDirectory) {
        try {
            var localFile = Components.classes["@mozilla.org/file/local;1"]
                            .createInstance(Components.interfaces.nsILocalFile);
            localFile.initWithPath(defaultDirectory);
            fp.displayDirectory = localFile;
        } catch (ex) {
            _log.error("problem setting '"+defaultDirectory+
                                 "' as default directory for file picker");
        }
    }
    if (defaultFilename) {
        fp.defaultString = ko.uriparse.baseName(defaultFilename);
    } else {
        fp.defaultString = null;
    }

    var fv = _unfocus();
    var retval = fp.show();
    _restorefocus(fv);
    if (retval == Components.interfaces.nsIFilePicker.returnOK) {
        //XXX Should we do any special handling if this is a symlink?
        return fp.file.path;
    }
    return null;
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
 *          filepicker_openFile(null, "D:\\trentm\\foo.txt");
 *      will set the default dir and filename to "D:\\trentm" and "foo.txt",
 *      respectively.
 * @param {String} "title" (optional) is the title for the file picker dialog.
 *
 * @returns {String} the full local path the selected file, or null.
 */
this.openExeFile = function filepicker_openExeFile(defaultDirectory /* =null */,
                                defaultFilename /* =null */,
                                title /* ="Open Executable File" */)
{
    if (typeof(defaultDirectory) == 'undefined') defaultDirectory = null;
    if (typeof(defaultFilename) == 'undefined') defaultFilename = null;
    if (typeof(title) == 'undefined' || title == null) title = "Open Executable File";
    var fp = _getOpenExeFilePicker(title);

    if (!defaultDirectory && defaultFilename) {
        try {
            defaultDirectory = ko.uriparse.dirName(defaultFilename);
        } catch (ex) { /* do nothing */ }
    }
    if (defaultDirectory) {
        try {
            var localFile = Components.classes["@mozilla.org/file/local;1"]
                            .createInstance(Components.interfaces.nsILocalFile);
            localFile.initWithPath(defaultDirectory);
            fp.displayDirectory = localFile;
        } catch (ex) {
            _log.error("problem setting '"+defaultDirectory+
                                 "' as default directory for file picker");
        }
    }
    if (defaultFilename) {
        fp.defaultString = ko.uriparse.baseName(defaultFilename);
    } else {
        fp.defaultString = null;
    }

    var fv = _unfocus();
    var retval = fp.show();
    _restorefocus(fv);
    if (retval == Components.interfaces.nsIFilePicker.returnOK) {
        //XXX Should we do any special handling if this is a symlink?
        return fp.file.path;
    }
    return null;
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
 *          filepicker_saveFile(null, "D:\\trentm\\foo.txt");
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
            defaultDirectory = ko.uriparse.dirName(defaultFilename);
        } catch (ex) { /* do nothing */ }
    }
    if (defaultDirectory) {
        try {
            var localFile = Components.classes["@mozilla.org/file/local;1"]
                            .createInstance(Components.interfaces.nsILocalFile);
            localFile.initWithPath(defaultDirectory);
            fp.displayDirectory = localFile;
        } catch (ex) {
            _log.error("problem setting '"+defaultDirectory+
                                 "' as default directory for file picker");
        }
    }
    if (defaultFilename) {
        fp.defaultString = ko.uriparse.baseName(defaultFilename);
    } else {
        fp.defaultString = null;
    }

    var fv = _unfocus();
    var retval = fp.show();
    _restorefocus(fv);
    if (retval == Components.interfaces.nsIFilePicker.returnReplace) {
        // Never attempt to force an extension on an existing file.
        return fp.file.path;
    } else if (retval != Components.interfaces.nsIFilePicker.returnOK) {
        // User cancelled the dialog.
        return null;
    } else {
        var path = fp.file.path;
        // Determine if should ask to force an extension.
        // - If path already has an extension, then no.
        var ext = ko.uriparse.ext(path);
        if (ext) {
            return path;
        }

        // Determine the file extension to append.
        ext = null;
        if (defaultFilename) {
            ext = ko.uriparse.ext(defaultFilename);
            if (!ext) ext = null;
        }
        if (ext == null && defaultFilterName) {
            // Try the first of registered extension for the default filter
            // name (presuming it is a language).
            var langRegistry = Components.classes["@activestate.com/koLanguageRegistryService;1"].
                               getService(Components.interfaces.koILanguageRegistryService);
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
            var basename = ko.uriparse.baseName(path);
            var prompt = _bundle.formatStringFromName("filenameDoesNotHaveAnExtension",
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
 * Pick multiple files for open.
 *
 * @param {String} "defaultDirectory" (optional) is the directory in which to start looking.
 *      If left unspecified (or null) the last directory in which this file
 *      picker was opened is used.
 * @param {String} "defaultFilename" (optional) is a suggested filename for the user to
 *      choose. If "defaultDirectory" is not specified then a fullpath can be
 *      used here to specify a default directory and filename. E.g.,
 *          filepicker_openFile(null, "D:\\trentm\\foo.txt");
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
this.openFiles = function filepicker_openFiles(defaultDirectory /* =null */,
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
            defaultDirectory = ko.uriparse.dirName(defaultFilename);
        } catch (ex) { /* do nothing */ }
    }
    if (defaultDirectory) {
        try {
            var localFile = Components.classes["@mozilla.org/file/local;1"]
                            .createInstance(Components.interfaces.nsILocalFile);
            localFile.initWithPath(defaultDirectory);
            fp.displayDirectory = localFile;
        } catch (ex) {
            _log.error("problem setting '"+defaultDirectory+
                                 "' as default directory for file picker");
        }
    }
    if (defaultFilename) {
        fp.defaultString = ko.uriparse.baseName(defaultFilename);
    } else {
        fp.defaultString = null;
    }

    var fv = _unfocus();
    var retval = fp.show();
    _restorefocus(fv);
    if (retval == Components.interfaces.nsIFilePicker.returnOK) {
        var paths = [];
        var files = fp.files;
        while (files.hasMoreElements()) {
            var file = files.getNext();
            file.QueryInterface(Components.interfaces.nsILocalFile);
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

    if (defaultDirectory) {
        try {
            var localFile = Components.classes["@mozilla.org/file/local;1"]
                            .createInstance(Components.interfaces.nsILocalFile);
            localFile.initWithPath(defaultDirectory);
            fp.displayDirectory = localFile;
        } catch (ex) {
            _log.error("problem setting '"+defaultDirectory+
                                 "' as default directory for file picker");
        }
    }

    var fv = _unfocus();
    var retval = fp.show();
    _restorefocus(fv);
    if (retval == Components.interfaces.nsIFilePicker.returnOK) {
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
       title = _bundle.GetStringFromName("openFile");
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
       mode = Components.interfaces.nsIFilePicker.modeOpen;
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
        "chrome,resizable=yes,close,dependent,modal=yes",
        fileBrowser);
   if (response) {
       if ((fileBrowser.retvals.buttonStatus == Components.interfaces.nsIFilePicker.returnOK) &&
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
 *   Same parameters meanings as "filepicker_remoteFileBrowser" (above)
 * Returns nothing. Note: The files will be opened through this function call
 */
this.openRemoteFiles = function filepicker_openRemoteFiles(defaultUrl, defaultFilename, defaultFilterName, filterNames) {
    var list;
    var fileBrowser = ko.filepicker.remoteFileBrowser(
            defaultUrl, defaultFilename, 
            Components.interfaces.nsIFilePicker.modeOpen,
            _bundle.GetStringFromName("openFiles"),
            defaultFilterName, filterNames,
            _bundle.GetStringFromName("openRemoteFile"));
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
 *   Same parameters meanings as "filepicker_remoteFileBrowser" (above)
 * Returns the remote url of the selected file, or null if the dialog is
 * cancelled.
 */
this.saveAsRemoteFiles = function filepicker_saveAsRemoteFiles(defaultUrl, defaultFilename, defaultFilterName, filterNames) {
    var fileBrowser = ko.filepicker.remoteFileBrowser(
            defaultUrl, defaultFilename,
            Components.interfaces.nsIFilePicker.modeSave,
            _bundle.GetStringFromName("saveFileAs"),
            defaultFilterName, filterNames,
            _bundle.GetStringFromName("saveRemotelyAs"));
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
        var RCService = Components.classes["@activestate.com/koRemoteConnectionService;1"].
                        getService(Components.interfaces.koIRemoteConnectionService);
        // Only set the default url if it's actually a remote url, otherwsie
        // we'll get an erro about an unknown protocol.
        if (RCService.isSupportedRemoteUrl(textbox.value)) {
            defaultUrl = textbox.value;
        }
    }
    var retval = ko.filepicker.remoteFileBrowser(defaultUrl,
                                              "" /* defaultFilename */,
                                              Components.interfaces.nsIFilePicker.modeGetFolder);
    if (retval && retval.file) {
        textbox.value = retval.file;
    }
};

}).apply(ko.filepicker);

// backwards compatibility api
var filepicker_openFile = ko.filepicker.openFile;
var filepicker_openExeFile = ko.filepicker.openExeFile;
var filepicker_saveFile = ko.filepicker.saveFile;
var filepicker_openFiles = ko.filepicker.openFiles;
var filepicker_getFolder = ko.filepicker.getFolder;
var filepicker_remoteFileBrowser = ko.filepicker.remoteFileBrowser;
var filepicker_openRemoteFiles = ko.filepicker.openRemoteFiles;
var filepicker_saveAsRemoteFiles = ko.filepicker.saveAsRemoteFiles;
var filepicker_browseForDir = ko.filepicker.browseForDir;
var filepicker_browseForRemoteDir = ko.filepicker.browseForRemoteDir;
