/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

if (typeof(ko)=='undefined') {
    var ko = {};
}


/**
 * ko.uriparse
 *
 * Functions to convert/parse strings representing URLs, files, etc.
 *
 * This is basically a loose shim around class URIParser in URIlib.py (somewhat
 * obtusely via koIFileEx).
 *
 * Routines:
 *      ko.uriparse.localPathToURI(<localPath>)
 *      ko.uriparse.pathToURI(<URI or localPath>)
 *      ko.uriparse.URIToLocalPath(<URI or localPath>)
 *      ko.uriparse.displayPath(<localPath or URI>)
 *      ko.uriparse.baseName(<localPath or URI>)
 *      ko.uriparse.dirName(<localPath or URI>)
 *      ko.uriparse.ext(<localPath or URI>)
 *
 * Dev Notes:
 *  - This module caches a single koIFileEx instance to, presumably, speed
 *    things up.
 */
ko.uriparse = {};

(function() {

var _koFileEx = null; // koFileEx singleton instance
function _getKoFileEx() {
    if (_koFileEx == null) {
        _koFileEx = Components.classes["@activestate.com/koFileEx;1"]
                             .createInstance(Components.interfaces.koIFileEx);
    }
    _koFileEx.URI = null; // clear the instance data
    return _koFileEx;
}


/**
 * localPathToURI
 * 
 * Get the URI representation of the given local file path.
 *
 *  "localPath" must be a local file path.
 *
 * Returns the URI for the given path or raises an exception if "localPath" is
 * not a local path.
 *
 * Examples:
 *  D:\trentm\foo.txt -> file:///D:/trentm/foo.txt
 *  \\planer\d\trentm\tmp\foo.txt -> file://planer/d/trentm/tmp/foo.txt
 *  file:///D:/trentm/foo.txt -> throws exception
 *  ftp://ftp.activestate.com/ActivePython -> throws exception
 */
this.localPathToURI = function(localPath) {
    var koFileEx = _getKoFileEx();
    koFileEx.path = localPath;
    var os = Components.classes["@activestate.com/koOs;1"].getService();
    if (os.path.normpath(koFileEx.path) != os.path.normpath(localPath)) {
        // ...then this was not a proper local path (probably a URI)
        throw("'"+localPath+"' does not appear to be a proper local path");
    }
    return koFileEx.URI;
}


/**
 * fixupURI DEPRECATED, remains for compatibility
 */
this.fixupURI = function(uri) {
    ko.main.log("DEPRECATED ko.uriparse.fixupURI should not be used");
    return uri;
}

/**
 * pathToURI
 * 
 * Get the URI representation of the given local file path or URI
 *
 *  "path" must be a local file path or a URI
 *
 * Returns the URI for the given path or the URI if one was passed in.
 *
 * Examples:
 *  D:\trentm\foo.txt -> file:///D:/trentm/foo.txt
 *  file:///D:/trentm/foo.txt -> file:///D:/trentm/foo.txt
 *  ftp://ftp.activestate.com/ActivePython -> ftp://ftp.activestate.com/ActivePython
 */
this.pathToURI = function(path) {
    var koFileEx = _getKoFileEx();
    koFileEx.path = path;
    return koFileEx.URI;
}

/**
 * URIToLocalPath
 * 
 * Get the local file path for the given URI.
 *
 *  "uri" may be a URI for a local file or a local path.
 *
 * Returns the local file path or raises an exception if there is no local file
 * representation for that URI. Note: I would rather this explicitly raised if
 * "uri" were a local path, but koIFileEx does not work that way.
 *
 * Examples:
 *  D:\trentm\foo.txt -> D:\trentm\foo.txt
 *  file:///D:/trentm/foo.txt -> D:\trentm\foo.txt
 *  ftp://ftp.activestate.com/ActivePython -> throws exception
 */
this.URIToLocalPath = function(uri) {
    var koFileEx = _getKoFileEx();
    koFileEx.URI = uri;
    if (koFileEx.scheme != "file") {
        throw("'"+uri+"' does not have a local path");
    }
    return koFileEx.path;
}

/**
 * displayPath
 * 
 * Get an appropriate representation of the given URI for display to the user.
 *
 *  "uri", typically, is a URI, though it can be a local filename as well.
 *
 * Examples:
 *  file:///D:/trentm/foo.txt -> D:\trentm\foo.txt
 *  D:\trentm\foo.txt -> D:\trentm\foo.txt
 *  ftp://ftp.activestate.com/ActivePython -> ftp://ftp.activestate.com/ActivePython
 */
this.displayPath = function(uri) {
    var koFileEx = _getKoFileEx();
    koFileEx.URI = uri;
    return koFileEx.displayPath;
}

/**
 * baseName
 * 
 * Get the basename (a.k.a. leafName) of the given file.
 *
 *  "file" can be a local filename or URI.
 *
 * Examples:
 *  file:///D:/trentm/foo.txt -> foo.txt
 *  D:\trentm\foo.txt -> foo.txt
 *  ftp://ftp.activestate.com/ActivePython -> ActivePython
 */
this.baseName = function(file) {
    var koFileEx = _getKoFileEx();
    koFileEx.URI = file;
    return koFileEx.baseName;
}

/**
 * dirName
 * 
 * Get the dirname of the given file.
 *
 *  "file" can be a local filename or URI referring to a local file.
 *
 * Examples:
 *  file:///D:/trentm/foo.txt -> D:\trentm
 *  D:\trentm\foo.txt -> D:\trentm
 *  ftp://ftp.activestate.com/ActivePython -> throws exception
 */
this.dirName = function(file) {
    var koFileEx = _getKoFileEx();
    koFileEx.URI = file;
    if (koFileEx.scheme != "file") {
        throw("'"+file+"' does not have a local dir name");
    }
    return koFileEx.dirName;
}

/**
 * ext
 * 
 * Get the extension of the given file.
 *
 *  "file" can be a local filename or URI
 */
this.ext = function(file) {
    var koFileEx = _getKoFileEx();
    koFileEx.URI = file;
    return koFileEx.ext;
}

this.getMappedURI = function(uri, prefs)
{
    // XXX project prefs....
    if (!prefs) {
	prefs = Components.classes["@activestate.com/koPrefService;1"].
                    getService(Components.interfaces.koIPrefService).effectivePrefs;
    }
    var mapping = null;
    if (prefs.hasPrefHere('mappedPaths'))
        mapping = prefs.getStringPref('mappedPaths');
    if (!mapping) {
	// try all pref layers for a match
	if (prefs.parent) {
	    return ko.uriparse.getMappedURI(uri, prefs.parent);
	}
	return uri;
    }
    var paths = mapping.split('::');
    var mappeduri = '', mappedpath = '';
    // we have to look at all the paths, since we could have subdirs mapped
    // to different locations as well.
    // eg.
    // http://test/a/ -> /test/a
    // http://test/a/b -> /test/b
    for (var i = 0; i < paths.length; i++) {
        var data = paths[i].split('##');
        if (uri.indexOf(data[0]) == 0) {
            if (data[0].length > mappeduri.length) {
                mappeduri = data[0];
                mappedpath = data[1];
            }
        }
    }
    if (!mappedpath) {
	// this layer had mappings, but none matched, look at parent prefs
	if (prefs.parent)
	    return ko.uriparse.getMappedURI(uri, prefs.parent);
        return uri;
    }
    // now we need a URI of the mappedpath
    var newpath = mappedpath + uri.slice(mappeduri.length);
    return ko.uriparse.pathToURI(newpath);
}

// used from drag/drop if an unhandled uri is dropped on komodo
this.addMappedURI = function(uri, path)
{
    if (typeof(path) == 'undefined') path=null;
    var info = {
	uri: uri,
	path: path,
        project: "false",
        project_name: null
    };
    if (ko.projects.manager.currentProject) {
        info.project_name =ko.projects.manager.currentProject.name;
    }
    window.openDialog('chrome://komodo/content/dialogs/editPathMap.xul', '_blank', 'chrome,modal,titlebar,resizable,centerscreen', info);
    if (!info.uri || !info.path) return false;
    // add this to the uri mapping
    var prefSvc = Components.classes["@activestate.com/koPrefService;1"].
		getService(Components.interfaces.koIPrefService);
    var prefs = prefSvc.prefs;
    if (info.project == "true" && ko.projects.manager.currentProject) {
        prefs = ko.projects.manager.currentProject.prefset;
    }
    var mapping = prefs.getStringPref('mappedPaths');
    mapping = mapping + "::" + info.uri + "##" + info.path;
    prefs.setStringPref('mappedPaths', mapping);
    return true;
}

this.getMappedPath = function(path, prefs)
{
    // XXX project prefs....
    if (!prefs) {
	prefs = Components.classes["@activestate.com/koPrefService;1"].
                    getService(Components.interfaces.koIPrefService).effectivePrefs;
    }
    var mapping = null;
    if (prefs.hasPrefHere('mappedPaths'))
        mapping = prefs.getStringPref('mappedPaths');
    if (!mapping) {
	// try all pref layers for a match
	if (prefs.parent) {
	    return ko.uriparse.getMappedPath(path, prefs.parent);
	}
	return path;
    }
    var paths = mapping.split('::');
    var mappeduri = '', mappedpath = '';
    // we have to look at all the paths, since we could have subdirs mapped
    // to different locations as well.
    // eg.
    // http://test/a/ -> /test/a
    // http://test/a/b -> /test/b
    for (var i = 0; i < paths.length; i++) {
        var data = paths[i].split('##');
        if (path.indexOf(data[1]) == 0) {
            if (data[1].length > mappedpath.length) {
                mappeduri = data[0];
                mappedpath = data[1];
            }
        }
    }
    if (!mappeduri) {
	// this layer had mappings, but none matched, look at parent prefs
	if (prefs.parent)
	    return ko.uriparse.getMappedPath(path, prefs.parent);
        return path;
    }
    // now we need a URI of the mappedpath
    return mappeduri + path.slice(mappedpath.length);
}
}).apply(ko.uriparse);


// backwards compatibility API
var uriparse_addMappedURI = ko.uriparse.addMappedURI;
var uriparse_getMappedURI = ko.uriparse.getMappedURI;
var uriparse_localPathToURI = ko.uriparse.localPathToURI;
var uriparse_pathToURI = ko.uriparse.pathToURI;
var uriparse_URIToLocalPath = ko.uriparse.URIToLocalPath;
var uriparse_displayPath = ko.uriparse.displayPath;
var uriparse_baseName = ko.uriparse.baseName;
var uriparse_dirName = ko.uriparse.dirName;
var uriparse_ext = ko.uriparse.ext;
var uriparse_fixupURI = ko.uriparse.fixupURI;
