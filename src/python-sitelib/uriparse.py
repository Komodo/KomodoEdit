# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
# 
# The contents of this file are subject to the Mozilla Public License
# Version 1.1 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
# 
# Software distributed under the License is distributed on an "AS IS"
# basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
# License for the specific language governing rights and limitations
# under the License.
# 
# The Original Code is Komodo code.
# 
# The Initial Developer of the Original Code is ActiveState Software Inc.
# Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
# ActiveState Software Inc. All Rights Reserved.
# 
# Contributor(s):
#   ActiveState Software Inc
# 
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
# 
# ***** END LICENSE BLOCK *****

"""Provide to Python code what uriparse.js provides to JavaScript code.

As for uriparse.js, koIFileEx is used to handle path/URI conversion.
"""

import os
import sys
import threading
import urlparse
import re

from xpcom import components


#---- globals

mutex = threading.Lock()
_gKoFileEx = None # koFileEx singleton instance



#---- internal support routines

def _getKoFileEx():
    global _gKoFileEx
    if _gKoFileEx is None:
        _gKoFileEx = components.classes["@activestate.com/koFileEx;1"]\
                               .createInstance(components.interfaces.koIFileEx)
    _gKoFileEx.URI = None # clear the instance data
    return _gKoFileEx



#---- public interface

# Get the URI representation of the given local file path.
#
#  "localPath" must be a local file path.
#
# Returns the URI for the given path or raises a ValueError if "localPath" is
# not a local path.
#
# Examples:
#  D:\trentm\foo.txt -> file:///D:/trentm/foo.txt
#  \\planer\d\trentm\tmp\foo.txt -> file://planer/d/trentm/tmp/foo.txt
#  file:///D:/trentm/foo.txt -> throws exception
#  ftp://ftp.activestate.com/ActivePython -> throws exception
#
def localPathToURI(localPath):
    mutex.acquire()
    try:
        koFileEx = _getKoFileEx()
        koFileEx.path = localPath
        if os.path.normpath(koFileEx.path) != os.path.normpath(localPath):
            raise ValueError("'%s' does not appear to be a proper local path [%s]"
                             % (localPath,koFileEx.path))
        return _normalizedPathToURI(localPath, koFileEx)
    finally:
        mutex.release()

# Get the URI representation of the given local file path or URI
#
#  "path" must be a local file path or a URI
#
# Returns the URI for the given path or the URI if one was passed in.
#
# Examples:
#  D:\trentm\foo.txt -> file:///D:/trentm/foo.txt
#  file:///D:/trentm/foo.txt -> file:///D:/trentm/foo.txt
#  ftp://ftp.activestate.com/ActivePython -> ftp://ftp.activestate.com/ActivePython
#
def pathToURI(path):
    mutex.acquire()
    try:
        koFileEx = _getKoFileEx()
        koFileEx.path = path
        return _normalizedPathToURI(path, koFileEx)
    finally:
        mutex.release()

def _normalizedPathToURI(localPath, koFileEx):
    if koFileEx.scheme != "file" or localPath.startswith("file:/"):
        return koFileEx.URI
    fixedPath = os.path.normpath(localPath)
    if localPath and fixedPath != localPath:
        # Preserve trailing slash (Bug 77205).
        trailingSlash = localPath[-1]
        if trailingSlash in '\\/' and not fixedPath[-1] in '\\/':
            fixedPath += trailingSlash
    if fixedPath != localPath:
        koFileEx.path = fixedPath
    return koFileEx.URI


# Get the file path component from the given URI.
#
#  "uri" may be a URI for a local or remote path.
#
# Returns the file path or raises an exception if there is no representation for
# that URI.
#
# Examples:
#  D:\trentm\foo.txt -> D:\trentm\foo.txt
#  file:///D:/trentm/foo.txt -> D:\trentm\foo.txt
#  file://planer/d/trentm/tmp/foo.txt -> file://planer/d/trentm/tmp/foo.txt
#  ftp://ftp.activestate.com/ActivePython -> /ActivePython
#
def URIToPath(uri):
    mutex.acquire()
    try:
        koFileEx = _getKoFileEx()
        koFileEx.URI = uri
        return koFileEx.path;
    finally:
        mutex.release()

# Get the local file path for the given URI.
#
#  "uri" may be a URI for a local file or a local path.
#
# Returns the local file path or raises an exception if there is no local file
# representation for that URI. Note: I would rather this explicitly raised if
# "uri" were a local path, but koIFileEx does not work that way.
#
# Examples:
#  D:\trentm\foo.txt -> D:\trentm\foo.txt
#  file:///D:/trentm/foo.txt -> D:\trentm\foo.txt
#  \\planer\d\trentm\tmp\foo.txt -> file://planer/d/trentm/tmp/foo.txt
#  file://planer/d/trentm/tmp/foo.txt -> file://planer/d/trentm/tmp/foo.txt
#  ftp://ftp.activestate.com/ActivePython -> throws exception
#
def URIToLocalPath(uri):
    mutex.acquire()
    try:
        koFileEx = _getKoFileEx()
        koFileEx.URI = uri
        if koFileEx.scheme != "file":
            raise ValueError("'%s' does not have a local path" % uri)
        return koFileEx.path;
    finally:
        mutex.release()


# Get an appropriate representation of the given URI for display to the user.
#
#  "uri", typically, is a URI, though it can be a local filename as well.
#
# Examples:
#  file:///D:/trentm/foo.txt -> D:\trentm\foo.txt
#  D:\trentm\foo.txt -> D:\trentm\foo.txt
#  ftp://ftp.activestate.com/ActivePython -> ftp://ftp.activestate.com/ActivePython
#
def displayPath(uri):
    mutex.acquire()
    try:
        koFileEx = _getKoFileEx()
        koFileEx.URI = uri
        return koFileEx.displayPath;
    finally:
        mutex.release()


# Fix the URI using Mozilla's URI fixup service.
#
# Known fixes:
#   - quotes spaces in the URI
#       file:///spam and eggs.txt -> file:///spam%20and%20eggs.txt
#   - adds two leading slashes to file URI with only one
#       file:/foo/bar.txt -> file:///foo/bar.txt
#
def fixupURI(uri):
    fixupSvc = components.classes["@mozilla.org/docshell/urifixup;1"]\
                         .getService(components.interfaces.nsIURIFixup)
    try:
        fixupURI = fixupSvc.createFixupURI(uri,
                        components.interfaces.nsIURIFixup.FIXUP_FLAG_NONE);
        if fixupURI.spec:
            uri = fixupURI.spec;
            re.sub("^(file:/+\w)|", "\1:", uri)
    except Exception, ex:
        log.debug("nsIURIFixup could not fixup '%s': %s", uri, ex)
        # Leave uri alone (presumably to fail below!)
    return uri


def _cleanfileURL(url):
    if url.startswith('file:/'):
        if not url.startswith('file:///'):
            url = 'file:///' + url[len('file:/'):]
    return url
    

##
# Return a mapped URI if there is a pref setup to match the given uri,
# else return whatever was passed in.
# Note: If a mapping existed, the return result is *always* a URI.
# @param uri str  URI or path to be mapped
# @param prefs components.interfaces.koIPrefs  komodo preferences (optional)
# @return str  URI if mapped, else uri that was passed in
#
def getMappedURI(uri, prefs=None):
    # XXX project prefs....
    if not prefs:
        prefs = components.classes["@activestate.com/koPrefService;1"].\
            getService(components.interfaces.koIPrefService).effectivePrefs
    mapping = None
    if prefs.hasPrefHere('mappedPaths'):
        mapping = prefs.getStringPref('mappedPaths')
    if not mapping:
        # try all pref layers for a match
        if prefs.parent:
            return getMappedURI(uri, prefs.parent)
        return uri
    paths = mapping.split('::')
    mappeduri = ''
    mappedpath = ''
    
    # we have to look at all the paths, since we could have subdirs mapped
    # to different locations as well.
    # eg.
    # http://test/a/ -> /test/a
    # http://test/a/b -> /test/b
    for path in paths:
        data = path.split('##')
        if uri.find(data[0]) == 0:
            if len(data[0]) > len(mappeduri):
                mappeduri = data[0]
                mappedpath = data[1]

    if not mappedpath:
        # no match, try the parent prefs
        if prefs.parent:
            return getMappedURI(uri, prefs.parent)
        return uri
    # now we need a URI of the mappedpath
    newpath = mappedpath + uri[len(mappeduri):]
    return pathToURI(newpath)

##
# Return a unmapped URI if there is a pref setup to match the given uri,
# else return whatever was passed in.
# Note: If a mapping existed, the return result is *always* a URI.
# @param uri str  URI or path to be mapped
# @param prefs components.interfaces.koIPrefs  komodo preferences (optional)
# @param host str  Specific hostname to be mapped to.
# @return str  URI if mapped, else uri that was passed in
#
def getMappedPath(path, prefs=None, host=None):
    # path         == "file://local/test/b/somedir/file.txt"
    # original uri == "http://test/a/b/somedir/file.txt"
    # mapping used was http://test/a/b -> C:\\local\\test\\b

    # sample 2:
    #   original uri: file://mymachine/usr/tmp.php
    #   pref        : file://mymachine##file:///C:/remote/mymachine
    #   getMappedURI: file:///C:/remote/mymachine/usr/tmp.php
    #   getMappedPath()
    #     path:       file:///C:/remote/mymachine/usr/tmp.php
    #     host:       mymachine
    #          =>     file://mymachine/usr/tmp.php
    # XXX project prefs....
    #print "getMappedPath: %r" % (path, )
    if not prefs:
        prefs = components.classes["@activestate.com/koPrefService;1"].\
            getService(components.interfaces.koIPrefService).effectivePrefs

    mapping = None
    if prefs.hasPrefHere('mappedPaths'):
        mapping = prefs.getStringPref('mappedPaths')
    if not mapping:
        # try all pref layers for a match
        if prefs.parent:
            return getMappedPath(path, prefs.parent, host)
        return path

    # There are mappings, check them now
    paths = mapping.split('::')
    mappeduri = ''
    mappedpath = ''
    # we have to look at all the paths, since we could have subdirs mapped
    # to different locations as well.
    # eg.
    # http://test/a/ -> C:\\test\\a
    # http://test/a/b -> C:\\local\\test\\b
    for data in paths:
        data = data.split('##', 1)
        if len(data) < 2:
            # In case an empty line got into the list of mapped URIs
            continue
        if path.find(data[1]) == 0 and len(data[1]) > len(mappedpath):
            # if there is a host, check to make sure it also matches
            if host:
                koURI = URIlib.URIParser(data[0])
                if koURI.server != host:
                    continue
            mappeduri = data[0]
            mappedpath = data[1]
    if not mappeduri:
        # this layer had mappings, but none matched, look at parent prefs
        if prefs.parent:
            return getMappedPath(path, prefs.parent, host)
        return path
    # now we need a URI of the mappedpath
    return mappeduri + path[len(mappedpath):]

import URIlib

def RelativizeURL(origbaseurl, origurl):
    if not origurl or not origbaseurl:
        return origurl
        
    # verify that both base and full url's are file types, we will
    # not relativize ftp, etc. type url's
    baseURI = URIlib.URIParser(origbaseurl)
    if not baseURI.scheme == 'file':
        return origurl
    fullURI = URIlib.URIParser(origurl)
    if not fullURI.scheme == 'file':
        return origurl

    # Create normalized strings for comparison purposes.
    # Results are returned in terms of the original arguments,
    # not these comparable strings.
    # Can't use os.path.normcase on a file URI on Windows, as it reverses
    # slashes. ("file:///C/xyz" => 'file:\\\\\\c\\xyz')
    if sys.platform == "win32":
        baseURI_URI_comparable = baseURI.URI.lower()
        fullURI_URI_comparable = fullURI.URI.lower()
    else:
        baseURI_URI_comparable = baseURI.URI
        fullURI_URI_comparable = fullURI.URI

    # ensure the base path ends with a slash
    if not baseURI_URI_comparable.endswith('/'):
        baseURI_URI_comparable += '/'

    # handle files with a common prefix.  This handles a full path
    # that is a subdirectory/path of the base path
    baselen = len(baseURI_URI_comparable)
    if baseURI_URI_comparable == fullURI_URI_comparable[:baselen]:
        return fullURI.URI[baselen:]
    elif baseURI_URI_comparable == fullURI_URI_comparable + "/":
        return ""

    # return the original url
    return origurl

def _UnRelativizeURL(baseurl, path):
    if not path:
        return URIlib.URIParser(baseurl)
    if path.find("://") > 0:
        # not relative if it's already a URI
        return URIlib.URIParser(path)
    if len(path) >1 and path[1] == ":":
        # windows path, not relative
        return URIlib.URIParser(path)
    if path[0] == '/' or path[:2] in [r'\\','//']:
        # full path or unc path
        return URIlib.URIParser(path)
    
    # ensure our base ends with a directory slash
    if baseurl[-1] not in ['/','\\']:
        baseurl += '/'
    baseURI = URIlib.URIParser(baseurl)
    # we only handle file base uri's
    if not baseURI.scheme == 'file':
        return URIlib.URIParser(path)
    
    # a simple join
    path = path.replace("\\","/")
    path = os.path.join(baseURI.path,path)
    # normpath handles collapsing "../../" paths
    if sys.platform.startswith("win"):
        path = path.replace("/","\\")
    path = os.path.normpath(path)
    # return a full URI
    return URIlib.URIParser(path)

def UnRelativizeURL(baseurl, path):
    return _UnRelativizeURL(baseurl, path).URI

def UnRelativizePath(basepath, path):
    return _UnRelativizeURL(basepath, path).path

def UnRelativize(basepath, path, type='url'):
    if type == 'url':
        return UnRelativizeURL(basepath, path)
    return UnRelativizePath(basepath, path)

