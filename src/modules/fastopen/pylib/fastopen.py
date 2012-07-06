#!/usr/bin/env python
# Copyright (c) 2009 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

"""Backend for Komodo's "fast open" system to quickly open (or switch to already
open) files.

Mainly the backend here is responsible for handling:
- gathering available paths from a set of gatherers (as determined by some
  config data)
- filtering down those paths/hits given a query string; and
- returning those results
all in a performant way.

# Basic Usage

Get a single Driver() instance (this is thread on which searches will be
done).
    
    d = Driver()

Get a configured list of gatherers. This is one or more `Gatherer` subclass
instances appended to a `Gatherers` class.
    
    gatherers = Gatherers()
    gatherers.append(DirGatherer("cwd", os.getcwd()))

Make a search (first argument is the query string):

    d.search("foo", gatherers)

This will print hits to stdout. To get and handle results directly, pass a
`resultsView` class (see `StreamResultsView` for example):

    d.search("foo", gatherers, resultsView=myResultsView)

Be sure to stop the driver thread when done:

    d.stop()
"""

import os
from os.path import (exists, expanduser, join, isdir, dirname, abspath,
    splitext, split, isabs, normcase, normpath)
import sys
import re
import logging
import threading
from pprint import pprint, pformat
import time
from hashlib import md5
import Queue

try:
    from xpcom import components
    from xpcom.server import UnwrapObject
    _xpcom_ = True
except ImportError:
    _xpcom_ = False



#---- globals

log = logging.getLogger("fastopen")
log.setLevel(logging.INFO)
#log.setLevel(logging.DEBUG)

MDASH = u"\u2014"

# Default path search exclusions used by `DirGatherer`.
DEFAULT_PATH_EXCLUDES = ["*.pyc", "*.pyo", "*.gz", "*.exe", "*.obj",
    ".DS_Store",
    ".svn", "_svn", ".git", "CVS", ".hg", ".bzr", "__pycache__"]

KOMODO_PROJECT_EXT = ".komodoproject"



#---- errors

class FastOpenError(Exception):
    pass

class FastOpenDriverTimeout(FastOpenError):
    """Waiting for the driver thread to stop timed-out."""
    pass


#---- main module classes

class Hit(object):
    """Virtual base class for fastopen "hits", typically a path and other info
    with which to open a file.
    """
    if _xpcom_:
        _com_interfaces_ = [components.interfaces.koIFastOpenHit]
    type = None  # all base classes must set this to some short string
    isdir = False
    
class PathHit(Hit):
    type = "path"
    
    # Whether to filter out duplicate hits based on the `path` attribute.
    filterDupePaths = True

    def __init__(self, path):
        self.path = path
        self.dir, base = split(path)
        self.dir_normcase = normcase(self.dir)
        self.base = base
        self.ibase = base.lower()
        self.ext = splitext(base)[1]  #TODO: use smart-splitext from astools
        if self.ext == base:  # a dot file, e.g. ".cvspass"
            self.ext = ""
    def __str__(self):
        return self.path
    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__,
            self.label.replace(MDASH, "--"))
    def __cmp__(self, other):
        """Comparison for path hits.
        
        We want to have:
            1) directories listed before files
            2) ".xxx" names listed after regular names
            3) case-insensitive sorting
        """
        # Compare by directory/file.
        if self.isdir:
            if not other.isdir:
                return -1
        elif other.isdir:
            return 1
        if self.dir != other.dir:
            return cmp(self.path, other.path)
        # Compare by base path then.
        if self.base.startswith("."):
            if not other.base.startswith("."):
                return 1
        elif other.base.startswith("."):
            return -1
        # Regular case-insensitive comparison.
        return cmp(self.ibase, other.ibase)

    _labelCache = None
    @property
    def label(self):
        if self._labelCache is None:
            self._labelCache = u"%s %s %s" % (self.base, MDASH, self.nicedir)
        return self._labelCache

    _nicedirCache = None
    @property
    def nicedir(self):
        if self._nicedirCache is None:
            d = self.dir
            if isabs(d) and "HOME" in os.environ:
                home = os.environ["HOME"]
                if self.dir_normcase.startswith(home):
                    d = "~" + d[len(home):]
            self._nicedirCache = d
        return self._nicedirCache

    _isdirCache = None
    @property
    def isdir(self):
        if self._isdirCache is None:
            self._isdirCache = isdir(self.path)
        return self._isdirCache

    def match(self, queryWords):
        """Return true if the given query matches this hit.
        
        @param queryWords {list} A list of 3-tuples of the form
            (query-word, is-case-sensitive, startswith), one for each query
            word.
        """
        for word, caseSensitive, startswith in queryWords:
            path = caseSensitive and self.label or self.label.lower()
            if startswith:
                if not path.startswith(word):
                    return False
            elif word not in path:
                return False
        return True

class GoHit(PathHit):
    type = "go"
    isdir = True
    def __init__(self, shortcut, dir):
        self.shortcut = shortcut
        self.dir = dir
        # Setup attributes expected by the inherited PathHit methods.
        self.path = dir
        self.dir_normcase = normcase(dir)
        self.base = shortcut
        self.ibase = shortcut.lower()

class ProjectHit(PathHit):
    type = "project-path"
    def __init__(self, path, project_name, project_base_dir):
        self.project_name = project_name
        self.project_base_dir = project_base_dir
        super(ProjectHit, self).__init__(path)

    _labelCache = None
    @property
    def label(self):
        if self._labelCache is None:
            if self.project_base_dir:
                if self.dir == self.project_base_dir:
                    self._labelCache = u"%s %s {%s}%s" % (self.base, MDASH,
                            self.project_name, os.sep)
                else:
                    self._labelCache = u"%s %s {%s}%s%s" % (self.base, MDASH,
                            self.project_name, os.sep,
                            self.dir[len(self.project_base_dir)+1:])
            else:
                self._labelCache = u"%s %s %s" % (self.base, MDASH, self.nicedir)
        return self._labelCache


class ResultsView(object):
    """A base implementation of the API required by 
    `Driver.search(..., resultsView)` for reporting results from a search.
    """
    def resetHits(self):
        pass
    def addHit(self, hit):
        pass
    def addHits(self, hits):
        pass
    def searchStarted(self):
        pass
    def searchAborted(self):
        pass
    def searchCompleted(self):
        pass

class CaptureResultsView(ResultsView):
    """A results view that just captures its hits."""
    def __init__(self):
        self.hits = []
    def addHit(self, hit):
        self.hits.append(hit)
    def addHits(self, hits):
        self.hits += hits

class StreamResultsView(ResultsView):
    """A results view that logs hits to stdout."""
    def __init__(self, stream=sys.stdout):
        self.stream = stream
    def resetHits(self):
        self.count = 0
    def addHit(self, hit):
        self.stream.write("%3d: %r\n" % (self.count, hit))
        self.count += 1
    def addHits(self, hits):
        for hit in hits:
            self.addHit(hit)


class Request(object):
    """Virtual base class for requests put on the `Driver` queue."""

class StopRequest(Request):
    """Request to stop the driver thread altogether."""

class SearchRequest(Request):
    """A light object to represent a fastopen search request.
    
    One of these is returned by `Driver.search(...)` and it has a `.wait()`
    method on which one can wait for the request to complete.
    """
    def __init__(self, query, gatherers, cwds, pathExcludes, dirShortcuts,
            resultsView, stopAtNHits=None):
        """
        ...
        @param stopAtNHits {int} If given, is a number of hits at which to
            stop the search. This can be used to have the search not bother
            wasting time on results that ultimately will not be used.
        """        
        self.query = query
        self.gatherers = gatherers
        self.cwds = cwds
        self.pathExcludes = pathExcludes
        self.dirShortcuts = dirShortcuts
        self.resultsView = resultsView
        self.stopAtNHits = stopAtNHits
        self._event = threading.Event()
    def wait(self, timeout=None):
        self._event.wait(timeout)
    def complete(self):
        self._event.set()
    def expandProjectPath(self, path):
        m = re.match("^\{(.*?)\}(.*)$", path)
        if m is not None:
            project_name, relpath = m.groups()
            relpath = relpath.lstrip(os.sep)
            for gather in self.gatherers:
                if isinstance(gather, CachingKomodoProjectGatherer):
                    if gather.project_name == project_name:
                        return join(gather.base_dir, relpath)
        return path

class AbortSearchRequest(Request):
    """Request to abort a running search."""


class Driver(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self, name="fastopen driver")
        self._queue = Queue.Queue()  # internal queue of search requests
        self.start()

    def __del__(self):
        self.stop(False)

    def stop(self, wait=False):
        """Stop the driver thread.
        
        @param wait {bool} Whether to block on the driver thread completing.
            Default is false.
        """
        if self.isAlive():
            self._queue.put(StopRequest())
            if wait:
                self.join()

    def abortSearch(self):
        self._queue.put(AbortSearchRequest())

    def search(self, query, gatherers, cwds=None, pathExcludes=None,
            dirShortcuts=None, resultsView=None):
        """Start a search for files. This cancels a currently running search.

        @param query {str} A query string.
        @param gatherers {Gatherers} The gatherers from which to get files.
        @param cwds {list} A list of current working directories. Used for
            relative path queries.
        @param pathExcludes {list} A list of path patterns to exclude. If not
            given, default is `DEFAULT_PATH_EXCLUDES`.
        @param dirShortcuts {dict} A mapping of shortcut strings to
            directories.
        @param resultsView {object} An object conforming to the following API
            on which results will be reported:
                resetHits()         called first thing
                addHit(hit)         add a single hit
                addHits(hits)       add a list of hits
                searchStarted()
                searchAborted()
                searchCompleted()
            If not given, results will be written to `sys.stdout` by using
            a `StreamResultsView`.
        @returns {Request} The search request. One can call `.wait()` on it
            to wait for it to finish.
        """
        if pathExcludes is None:
            pathExcludes = DEFAULT_PATH_EXCLUDES
        r = SearchRequest(query, gatherers, cwds or [], pathExcludes,
            dirShortcuts, resultsView or StreamResultsView())
        self._queue.put(r)
        return r

    def searchOne(self, query, gatherers, cwds=None, pathExcludes=None,
            dirShortcuts=None, timeout=None):
        """A synchonous version of `search()` that just searches for and
        returns the top hit.
        
        ...
        @param dirShortcuts {dict} A mapping of shortcut strings to
            directories.
        @param timeout {float} A number of seconds to wait for that first hit.
            If None (or not given), then don't timeout.
        @returns {Hit} The top hit or, if there isn't one, None.
        
        TODO: raise if timeout?
        """
        if pathExcludes is None:
            pathExcludes = DEFAULT_PATH_EXCLUDES
        resultsView = CaptureResultsView()
        request = SearchRequest(query, gatherers, cwds or [], pathExcludes,
            dirShortcuts, resultsView, 1)
        self._queue.put(request)
        request.wait(timeout)
        return (resultsView.hits[0] if resultsView.hits else None)

    def run(self):
        while True:
            # Get the latest request on the queue (last one wins, with the
            # exception that a "StopRequest" trumps).
            request = self._queue.get()
            if isinstance(request, StopRequest):
                return
            while True:
                try:
                    request = self._queue.get_nowait()
                except Queue.Empty:
                    break
                else:
                    if isinstance(request, StopRequest):
                        return

            # Handle the request.
            log.debug("driver request: %r", request)
            try:
                if isinstance(request, SearchRequest):
                    self._handleSearchRequest(request)
                elif isinstance(request, AbortSearchRequest):
                    pass
                else:
                    log.error("unknown fastopen request type: %r", request)
            except:
                log.exception("error handling request: %r", request)
    
    def _handleSearchRequest(self, request):
        from os.path import isabs, split, join, normpath
        from fnmatch import fnmatch
        
        aborted = True
        resultsView = request.resultsView
        resultsView.searchStarted()
        try:
            resultsView.resetHits()
            query = request.query.strip()

            stopAtNHits = request.stopAtNHits

            # See if this is a path query, i.e. a search for an absolute or
            # relative path.
            dirQueries = []
            if isabs(query):
                dirQueries.append(query)
            elif query.startswith("~"):
                expandedQuery = expanduser(query)
                if isabs(expandedQuery):
                    dirQueries.append(expandedQuery)
            elif query.startswith("{") and "}" in query:
                expandedQuery = request.expandProjectPath(query)
                if expandedQuery != query:
                    dirQueries.append(expandedQuery)
            elif '/' in query:
                dirQueries += [join(d, query) for d in request.cwds]
                shortcut, subpath = query.split('/', 1)
                if request.dirShortcuts and shortcut in request.dirShortcuts:
                    dirQueries.append(join(request.dirShortcuts[shortcut], subpath))
            elif sys.platform == "win32" and '\\' in query:
                dirQueries += [join(d, query) for d in request.cwds]
                shortcut, subpath = query.split('\\', 1)
                if request.dirShortcuts and shortcut in request.dirShortcuts:
                    dirQueries.append(join(request.dirShortcuts[shortcut], subpath))

            hitPaths = set()
            pathExcludes = request.pathExcludes
            if dirQueries:
                hitPaths = set()
                for dirQuery in dirQueries:
                    dir, baseQuery = split(dirQuery)
                    try:
                        names = os.listdir(dir)
                    except OSError:
                        pass
                    else:
                        hits = []
                        baseQueryWords = []
                        for i, w in enumerate(baseQuery.strip().split()):
                            startswith = (i == 0 and not baseQuery.startswith(' '))
                            baseQueryWords.append((w, w.lower() != w, startswith))
                        for name in names:
                            try:
                                path = normpath(join(dir, name))
                            except UnicodeDecodeError:
                                # Hit a filename that cannot be encoded in the
                                # default encoding. Just skip it. (Bug 82268)
                                continue
                            hit = PathHit(path)
                            if name.startswith('.') and hit.isdir \
                               and not baseQuery.startswith('.'):
                                # Only show dot-dirs if baseQuery startswith a dot.
                                continue
                            if not hit.match(baseQueryWords) or path in hitPaths:
                                continue
                            for exclude in pathExcludes:
                                if fnmatch(name, exclude):
                                    break
                            else:
                                hits.append(hit)
                                hitPaths.add(path)
                        #log.debug("adding %d hits from %r (path mode)", len(hits), dirQuery)
                        if hits:
                            resultsView.addHits(sorted(hits))
                            if stopAtNHits and len(hitPaths) >= stopAtNHits:
                                aborted = False
                                return
        
            else:
                # Second value is whether to be case-sensitive in filtering.
                queryWords = [(w, w.lower() != w, False) for w in query.split()]
                
                BLOCK_SIZE = 50  #TODO: ask gatherer if can just get all?
                if stopAtNHits:
                    BLOCK_SIZE = min(stopAtNHits, BLOCK_SIZE)
                generators = [(g, g.gather()) for g in request.gatherers]
                while generators:
                    exhausted = []
                    for i, (gatherer, generator) in enumerate(generators):
                        hits = []
                        for j, hit in enumerate(generator):
                            path = hit.path
                            if hit.filterDupePaths and path in hitPaths:
                                pass
                            elif hit.match(queryWords):
                                for exclude in pathExcludes:
                                    if fnmatch(path, exclude):
                                        break
                                else:
                                    hits.append(hit)
                                    hitPaths.add(path)
                            if j >= BLOCK_SIZE - 1:
                                break
                        else:
                            exhausted.append(i)
                        if not self._queue.empty():  # Another request, abort this one.
                            return
                        #log.debug("adding %d hits from %r", len(hits), gatherer)
                        if hits:
                            resultsView.addHits(hits)
                            if stopAtNHits and len(hitPaths) >= stopAtNHits:
                                aborted = False
                                return
                    if exhausted:
                        for i in reversed(exhausted):
                            del generators[i]
            
            hits = []
            if hits:
                resultsView.addHits(hits)
                if stopAtNHits and len(hitPaths) >= stopAtNHits:
                    aborted = False
                    return
            
            aborted = False
        finally:
            try:
                if aborted:
                    resultsView.searchAborted()
                else:
                    resultsView.searchCompleted()
            except:
                log.error("error signalling end of fastopen search")
            request.complete()
            

class Gatherers(list):
    """A priority-ordered list of path hit gatherers.
    
    TODO: If a plain list will do, then switch to that.
    """
    pass

class Gatherer(object):
    """Virtual base class for path hit gatherers."""
    name = None
    
    def __repr__(self):
        return "<Gatherer %s>" % self.name
    
    def gather(self):
        """Generates hits."""
        if False:
            yield None  # force this to be a generator
        raise NotImplementedError("virtual method")


class DirGatherer(Gatherer):
    """Gather files in a given directory or directories (non-recursive).
    
    @param name {str} Name of this gatherer.
    @param dirs {list} List of directories from which to gather.
    @param includeDirs {boolean} Whether to include subdirectories.
        Default false.
    @param excludes {list} Path patterns to exclude. Default is
        `DEFAULT_PATH_EXCLUDES`.
    """
    def __init__(self, name, dirs, includeDirs=False, excludes=None):
        self.name = name
        if isinstance(dirs, basestring):
            self.dirs = [dirs]
        else:
            self.dirs = dirs
        self.includeDirs = includeDirs
        self.excludes = excludes or DEFAULT_PATH_EXCLUDES
    def gather(self):
        from fnmatch import fnmatch
        from operator import methodcaller
        for dir in self.dirs:
            try:
                names = os.listdir(dir)
            except EnvironmentError, ex:
                log.warn("couldn't read `%s' dir: %s", dir, ex)
            else:
                for name in sorted(names, key=methodcaller('lower')):
                    try:
                        path = join(dir, name)
                    except UnicodeDecodeError:
                        # Hit a filename that cannot be encoded in the
                        # default encoding. Just skip it. (Bug 82268)
                        continue
                    for exclude in self.excludes:
                        if fnmatch(name, exclude):
                            break
                    else:
                        if self.includeDirs or not isdir(path):
                            yield PathHit(path)

class GoGatherer(Gatherer):
    """Gather for go-tool (http://code.google.com/p/go-tool) settings."""
    name = "go"
    
    # Based on the equiv in go.py.
    def getShortcutsFile(self):
        """Return the path to the shortcuts file."""
        fname = "shortcuts.xml"
        # Find go's shortcuts data file.
        # - Favour ~/.go if shortcuts.xml already exists there.
        path = None
        candidate = expanduser("~/.go/shortcuts.xml")
        if exists(candidate):
            path = candidate
        
        try:
            import applib
        except ImportError:
            # Probably running directly in source tree.
            sys.path.insert(0, join(dirname(dirname(dirname(dirname(abspath(__file__))))),
                "python-sitelib"))
            import applib
        if path is None:
            dir = applib.roaming_user_data_dir("Go", "TrentMick")
            path = join(dir, "shortcuts.xml")
        return path
    
    # Based on equiv in go.py.
    _shortcutsCache = None
    def getShortcuts(self):
        if self._shortcutsCache is None:
            from xml.etree import ElementTree as ET
            path = self.getShortcutsFile()
            if not path or not exists(path):
                return {}
            fin = open(path)
            try:
                shortcuts = {}
                shortcuts_elem = ET.parse(fin).getroot()
                for child in shortcuts_elem:
                    shortcuts[child.get("name")] = child.get("value")
            finally:
                fin.close()
            self._shortcutsCache = shortcuts
        return self._shortcutsCache
    
    def gather(self):
        shortcuts = self.getShortcuts()
        for name, value in shortcuts.items():
            yield GoHit(name, value)

class KomodoProjectGatherer(Gatherer):
    """A gatherer of files in a Komodo project."""
    def __init__(self, project):
        self.project = project
        self.name = "project '%s'" % project.get_name()
        self.base_dir = project.get_importDirectoryLocalPath()
    def gather(self):
        #XXX:TODO the cached/indexed version
        project_name = self.project.get_name()
        if project_name.endswith(KOMODO_PROJECT_EXT):
            project_name = project_name[:-len(KOMODO_PROJECT_EXT)]
        base_dir = self.base_dir
        i = 0
        for path in self.project.genLocalPaths():
            yield ProjectHit(path, project_name, base_dir)

class CachingKomodoProjectGatherer(Gatherer):
    """A gatherer of files in a Komodo project."""
    def __init__(self, project, gatherDirs=False, follow_symlinks=True):
        self.project = project
        self.gatherDirs = gatherDirs
        self.follow_symlinks = follow_symlinks
        self.name = "project '%s'" % project.get_name()
        self.base_dir = project.get_importDirectoryLocalPath()
        project_name = self.project.get_name()
        if project_name.endswith(KOMODO_PROJECT_EXT):
            project_name = project_name[:-len(KOMODO_PROJECT_EXT)]
        self.project_name = project_name
        self._hits = []  # cache of already generated hits
    
    _raw_generator = None
    def gather(self):
        # First yield any hits we've already gathered and cached.
        for hit in self._hits:
            yield hit
        
        # Then, yield and cache any remaining ones.
        if self._raw_generator is None:
            self._raw_generator = self.project.genLocalPaths(self.gatherDirs, self.follow_symlinks)
        project_name = self.project_name
        base_dir = self.base_dir
        for path in self._raw_generator:
            hit = ProjectHit(path, project_name, base_dir)
            self._hits.append(hit)
            yield hit



#---- internal support stuff

#TODO: put this in a generate shared module and share with editorhistory.py
class _RecentsDict(dict):
    """A dict that just keeps the last N most recent referred-to keys around,
    where "referring to" means both adds and gets.
    
    Note: No effort has yet gone into this to make it fully generic. For
    example, it doesn't notice explicit removal of keys. Basically it presumes
    the user only ever adds and looks-up.
    """
    def __init__(self, limit, *args):
        self.limit = limit
        self.recent_keys = []   # most recent last
        dict.__init__(self, *args)
    
    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)
        try:
            idx = self.recent_keys.index(key)
        except ValueError:
            self.recent_keys.append(key)
            if len(self.recent_keys) > self.limit:
                k = self.recent_keys.pop(0)
                dict.__delitem__(self, k)
        else:
            del self.recent_keys[idx]
            self.recent_keys.append(key)

    def __getitem__(self, key):
        value = dict.__getitem__(self, key)
        idx = self.recent_keys.index(key)
        del self.recent_keys[idx]
        self.recent_keys.append(key)
        return value

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        self.recent_keys.remove(key)

    def __repr__(self):
        return "_RecentsDict(%d, %s)" % (self.limit, dict.__repr__(self))


#---- mainline and self-testing

class MockKomodoPrefset(dict):
    def hasBooleanPref(self, name):
        return name in self and isinstance(self[name], bool)
    def getBooleanPref(self, name):
        assert isinstance(self[name], bool)
        return self[name]

class MockKomodoProject(object):
    """A mock Komodo koIProject class that implements just enough of its
    API for testing of KomodoProjectGatherer.
    """
    def __init__(self, name, base_dir, includes=None, excludes=None,
            is_live=True, slow=False):
        """
        @param slow {bool} Whether to be slow in returning results from
            genLocalPaths. Default is false.
        """
        # Really the 'id' in the .komodoproject file, but we'll fake it well
        # enough for here.
        self.id = md5(name).hexdigest()
        self._name = name
        self._base_dir = base_dir
        if includes is None:
            self._includes = []
        else:
            self._includes = includes
        if excludes is None:
            self._excludes = "*.*~;*.bak;*.tmp;CVS;.#*;*.pyo;*.pyc;.svn;.hg;.git;.bzr;*%*;*.kpf;*.komodoproject;__pycache__".split(';')
        else:
            self._excludes = excludes
        self._prefset = MockKomodoPrefset(import_live=is_live)
        self._slow = slow

    def get_prefset(self):
        return self._prefset

    def get_name(self):
        return self._name

    def get_importDirectoryLocalPath(self):
        if self._prefset["import_live"]:
            return self._base_dir
        else:
            raise AttributeError("no 'liveDirectory' attribute (project "
                "isn't a live folder)")

    def genLocalPaths(self, gatherDirs=False, follow_symlinks=True):
        sys.path.insert(0, join(dirname(dirname(dirname(dirname(
            abspath(__file__))))), "find"))
        try:
            import findlib2
        finally:
            del sys.path[0]
        paths = findlib2.paths_from_path_patterns(
            [self._base_dir],
            dirs=(gatherDirs and "always" or "never"),
            recursive=True,
            includes=self._includes,
            excludes=self._excludes,
            on_error=None,
            follow_symlinks=follow_symlinks,
            skip_dupe_dirs=True)
        for path in paths:
            yield path
            if self._slow:
                time.sleep(0.1)

def _test1(query):
    driver = Driver()
    
    try:
        gatherers = Gatherers()
        gatherers.append(DirGatherer("cwd", os.getcwd()))
        gatherers.append(CachingKomodoProjectGatherer(
            MockKomodoProject("fastopen" + KOMODO_PROJECT_EXT,
                expanduser("~/as/komodo/src/modules/fastopen"),
                excludes=["build", "tmp", "*.xpi", "*.pyc", "*.pyo", ".svn"],
                slow=False)))
        
        print "-- search 'f'"
        request = driver.search("f", gatherers)
        request.wait(1)
    
        print "-- search 'fast'"
        request = driver.search("fast", gatherers)
        request.wait(0.5)
        
        print "-- search 'fest'"
        request = driver.search("fest", gatherers)
        request.wait()
        
        print "-- search 'fast'"
        request = driver.search("fast", gatherers)
        request.wait()
        print "-- search 'fasty'"
        request = driver.search("fasty", gatherers)
        request.wait()
        print "-- search 'fast'"
        request = driver.search("fast", gatherers)
        request.wait()
    finally:
        driver.stop(True)  # wait for termination

def _test2(query):
    driver = Driver()
    
    try:
        gatherers = Gatherers()
        gatherers.append(DirGatherer("cwd", os.getcwd()))
        gatherers.append(CachingKomodoProjectGatherer(
            MockKomodoProject("komodo" + KOMODO_PROJECT_EXT,
                expanduser("~/as/komodo"),
                excludes=["build", "tmp", "log", "contrib",
                    "*.xpi", "*.pyc", "*.pyo", ".svn"],
                slow=False)))
        
        print "-- search 'find2'"
        request = driver.search('find2', gatherers)
        request.wait(3)
        print "-- search 'find'"
        request = driver.search('find', gatherers)
        request.wait(2)
        print "-- search 'find2'"
        request = driver.search('find2', gatherers)
        request.wait()
    finally:
        driver.stop(True)  # wait for termination

def _test3(query):
    driver = Driver()
    
    try:
        gatherers = Gatherers()
        gatherers.append(DirGatherer("cwd", os.getcwd()))
        gg = GoGatherer()
        gatherers.append(gg)
        
        print "-- search '%s'" % query
        request = driver.search(query, gatherers, cwds=[os.getcwd()],
            dirShortcuts=gg.getShortcuts())
        request.wait(5)
    finally:
        driver.stop(True)  # wait for termination


def main(argv):
    logging.basicConfig()
    query = ' '.join(argv[1:])
    _test3(query)

if __name__ == "__main__":
    sys.exit(main(sys.argv))

