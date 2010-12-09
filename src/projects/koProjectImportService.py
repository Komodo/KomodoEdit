#!/usr/bin/env python

from xpcom import components, ServerException, COMException, nsError
from xpcom.server import WrapObject, UnwrapObject

import os
import uriparse, fnmatch
from URIlib import URIParser, RemoteURISchemeTypes

import logging
log = logging.getLogger("koProjectImportService")

class KoFileImportingService:
    _com_interfaces_ = [components.interfaces.koIFileImportingService]
    _reg_clsid_ = "{DC2BBD9F-A575-4ddc-8A22-D345B5413874}"
    _reg_contractid_ = "@activestate.com/koFileImportingService;1"
    _reg_desc_ = "Service to import files into folders"

    def __init__(self):
        self.lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"]\
            .getService(components.interfaces.koILastErrorService)
        self.lastErrorSvc.setLastError(0, '')

    def getCandidatesForDir(self, dirname, live, include_pats, exclude_pats):
        # start with current directory contents
        # clean up to deal with some samba problems
        # http://bugs.activestate.com/Komodo/show_bug.cgi?id=23097
        dirname = os.path.normpath(os.path.abspath(dirname))
        try:
            allnames = os.listdir(dirname)
        except OSError, e:
            if e.errno == 13: # permission denied
                self.lastErrorSvc.setLastError(13, 'Permission denied')
            raise
# #if PLATFORM == "win"
        except WindowsError, e:
            if e.errno in (5, 32) and not os.path.exists(dirname):
                # Looks like the directory was deleted between the
                # time the request was initiated and when it was handled
                return []
            else:
                raise
# #endif

        dirsonly = [name for name in allnames\
                if os.path.isdir(os.path.join(dirname, name))]
        # Files have import patterns, directories do not
        filesonly = set(allnames).difference(dirsonly)
        if live:
            allnames = _filterFiles(dirsonly, None, exclude_pats)
            allnames = allnames.union(_filterFiles(filesonly, include_pats, exclude_pats))
        else:
            allnames = _filterFiles(filesonly, include_pats, exclude_pats)
        # was a set, now we go back to a list
        return [os.path.join(dirname, name) for name in sorted(allnames)]

    def findCandidateFiles(self, part, dirname, include, exclude, recursive):
        self.lastErrorSvc.setLastError(0, '')
        try:
            if include != '':
                include_pats = include.split(';')
            else:
                include_pats = None
            if exclude != '':
                exclude_pats = exclude.split(';')
            else:
                exclude_pats = None
            part = UnwrapObject(part)
            allnames = self.getCandidatesForDir(dirname, False,
                                                include_pats, exclude_pats)

            # now look at children
            if recursive:
                for subdirname in _dirwalker(dirname, exclude_pats):
                    names = self.getCandidatesForDir(subdirname, part.live,
                                                     include_pats, exclude_pats)
                    names = [os.path.join(subdirname, name) for name in names\
                                if part.live or os.path.isfile(os.path.join(subdirname, name))]
                    allnames.extend(names)

            #print "part._project._urlmap:", part._project._urlmap
            if not part.live:
                # XXX REMOVE ME when livefolder == folder
                # for now, support the js dialog for importing
                newfiles = []
                for name in allnames:
                    name = os.path.abspath(name)
                    url = uriparse.localPathToURI(name)
                    if not part._project._urlmap.get(url, None):
                        newfiles.append(name)
                return newfiles
            # live folder import wants all the matching files
            return allnames
        except:
            # TODO: Catch OSError or appropriate specific exception
            log.exception("failed scanning file system")
            return []

    def findCandidateFilesRemotely(self, part, dirname, include, exclude, recursive, connection=None, serverUri=None):
        self.lastErrorSvc.setLastError(0, '')
        try:
            if include != '':
                include_pats = include.split(';')
            else:
                include_pats = None
            if exclude != '':
                exclude_pats = exclude.split(';')
            else:
                exclude_pats = None
            part = UnwrapObject(part)
            if connection is None:
                # Setup the connection for the given url
                # Note: dirname is a url for the first call, but sebsequent
                #       recursive calls it will just be the remote path/directory.
                RFService = components.classes["@activestate.com/koRemoteConnectionService;1"].\
                            getService(components.interfaces.koIRemoteConnectionService)
                connection = RFService.getConnectionUsingUri(dirname)
                if not connection:
                    self.lastErrorSvc.setLastError(1, 'Could not obtain remote file connection')
                    return []
                # Parse up the url, so we get the remote directory path
                URI = URIParser()
                URI.URI = dirname
                remoteDir = URI.path
                # Base URI for the remote filesystem
                serverUri = "%s://%s" % (URI.scheme, URI.server)
            else:
                remoteDir = dirname

            # Get the remote directory listing
            #print "Getting connection listing for: %s" % (remoteDir)
            koRemoteInfo = connection.list(remoteDir, 1)  # Refresh it
            if koRemoteInfo is None:
                self.lastErrorSvc.setLastError(1, 'Could not locate the remote file path: %r' % (remoteDir))
                return []
            koRemoteInfo = koRemoteInfo.getChildren()
            #print "koRemoteInfo:", koRemoteInfo

            filesonly = [f for f in koRemoteInfo if f.isFile()]
            filenames = [f.getFilename() for f in filesonly]
            if filenames:
                # Filter them. Note: Files have include and exclude patterns
                # Note2: _filterFiles works on basenames only
                filteredFilenames = _filterFiles(filenames, include_pats, exclude_pats)
                # Convert back to list of full path filenames
                filenames = ["%s/%s" % (remoteDir, name) for name in filteredFilenames]

            # now look at children for recursive imports
            if recursive:
                # Determine the directories
                dirnames = [f.getFilename() for f in koRemoteInfo if f.isDirectory()]
                # Directories only have an exclude pattern
                # Note: _filterFiles works on basenames only
                filteredDirnames = _filterFiles(dirnames, None, exclude_pats)
                # Turn into full path
                filteredDirnames = ["%s/%s" % (remoteDir, name) for name in filteredDirnames]
                for subdirname in filteredDirnames:
                    filenames += self.findCandidateFilesRemotely(part, subdirname, include, exclude, recursive, connection, serverUri)

            # Don't add files that already exist in the project
            if not part.live:
                # XXX REMOVE ME when livefolder == folder
                # for now, support the js dialog for importing
                newfiles = []
                for name in filenames:
                    uri = "%s%s" % (serverUri, name)
                    if not part._project._urlmap.get(uri, None):
                        newfiles.append(name)
                return newfiles

            return filenames
        except:
            # TODO: Catch OSError or appropriate specific exception
            log.exception("failed scaning remote file system")
            return []

    def addSelectedFiles(self, folder, importType, basedir, filenames):
        #import time
        #t1 = time.clock()
        # XXX bug 38793
        if basedir[-1]=='/':
            basedir = basedir[:-1]

        folder = UnwrapObject(folder)
        project = folder._project
        _folderCache = {}

        # See what type of import this is
        #print "basedir: %r" % (basedir)
        URI = URIParser()
        URI.URI = basedir
        if URI.scheme in RemoteURISchemeTypes:
            isRemote = True
            # Convert all filenames into remote URI's
            remotePrefix = "%s://%s" % (URI.scheme, URI.server)
            # XXX - This hack may be needed on Windows ??
            #if sys.platform.startswith("win"):
            #    # Windows, convert the filenames to a windows format
            #    filenames_and_urls = [(os.path.normpath(filename), remotePrefix + filename) for filename in filenames]
            #else:
            filenames_and_urls = [(filename, remotePrefix + filename) for filename in filenames]
        else:
            isRemote = False
            # Convert all filenames into local URI's
            filenames_and_urls = [(filename, uriparse.localPathToURI(str(filename))) for filename in filenames]
        data = [(project.getPart(filename, url, project, folder.live), filename, url) for (filename,url) in filenames_and_urls]

        #c1 = time.clock()
        #print "addSelectedFiles c1 ", c1-t1

        if importType == 'makeFlat':
            for part, filename, url in data:
                part.live = folder.live
                folder.children.append(part)
                part._parent = folder
                project._urlmap[url] = part
                part.assignId()
        elif importType == 'groupByType':
            registry = components.classes["@activestate.com/koLanguageRegistryService;1"].\
                getService(components.interfaces.koILanguageRegistryService)
            for part, filename, url in data:
                language = registry.suggestLanguageForFile(filename)
                if not language: language = 'Other'
                if language in _folderCache and _folderCache[subdirname]:
                    subfolder = _folderCache[language]
                else:
                    subfolder = _folderCache[language] = folder.getLanguageFolder(language)
                part.live = subfolder.live
                subfolder.children.append(part)
                part._parent = subfolder
                project._urlmap[url] = part
                part.assignId()
        elif importType == 'useFolders':
            if not isRemote:
                basedir = uriparse.localPathToURI(basedir)
            baseuri = basedir
            for part, filename, url in data:
                diruri = os.path.dirname(url)
                if diruri in _folderCache and _folderCache[diruri]:
                    subfolder = _folderCache[diruri]
                else:
                    subfolder = _folderCache[diruri] = folder.getDirFolder(baseuri, diruri)
                if not subfolder:
                    log.error("Unable to get subfolder for %s: %s", baseuri, diruri)
                part.live = subfolder.live
                subfolder.children.append(part)
                part._parent = subfolder
                project._urlmap[url] = part
                part.assignId()
        #c2 = time.clock()
        #print "addSelectedFiles c2 ", c2-c1
        try:
            # let the file status service know we need to get status info
            obSvc = components.classes["@mozilla.org/observer-service;1"]\
                .getService(components.interfaces.nsIObserverService)
            obSvc.notifyObservers(self,'file_changed',basedir)
        except:
            pass # no listener
        project.set_isDirty(len(data) > 0)
        #t2 = time.clock()
        #print "addSelectedFiles ", t2-t1

def _isOk(fullpath, exclude_pats):
    if exclude_pats:
        base = os.path.basename(fullpath)
        for pat in exclude_pats:
            if fnmatch.fnmatch(base, pat):
                return 0
    return 1

def _dirwalker(dirname, exclude_pats):
    """Generate all subdirectories of the given directory."""
    try:
        contents = os.listdir(os.path.normpath(dirname))
    except OSError, e:
        if e.errno != 13: # permission denied
            raise
        contents = []
    for f in contents:
        fullpath = os.path.join(dirname, f)
        if os.path.isdir(fullpath) and _isOk(fullpath, exclude_pats):
            yield fullpath
            for subdirname in _dirwalker(fullpath, exclude_pats):
                if _isOk(subdirname, exclude_pats):
                    yield subdirname

def _filterFiles(names, include_pats, exclude_pats):
    """Filter the names array for filenames which match any of the
    patterns in include_pats and match none of the patterns in
    exclude_pats -- returns a list containing a selection of the input
    names.

    if include_pats is None then all files match are considered by
    default

    if exclude_pats is None then no files are excluded explicitly
    """
    # Simplest case, get back right away
    if include_pats is None and exclude_pats is None:
        return set(names)
    # Else, lets go through the names
    # Note: Exclude gets priority over include

    # Check include_pats first, then check exclude_pats
    if include_pats:
        oknames = set()
        # Go through every include pattern and find a match
        for pat in include_pats:
            oknames = oknames.union(fnmatch.filter(names, pat))
    else:
        oknames = set(names)

    # Check excludes, it gets priority over include_pats
    if exclude_pats and oknames:
        # Go through every exclude pattern and find a match
        for pat in exclude_pats:
            oknames = oknames.difference(fnmatch.filter(oknames, pat))
    return oknames
