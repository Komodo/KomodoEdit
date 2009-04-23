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
    splitext, split, isabs, normcase)
import sys
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
    ".svn", "_svn", ".git", "CVS", ".hg", ".bzr"]



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
    @property
    def label(self):
        return u"%s %s %s" % (self.base, MDASH, self.nicedir)
    @property
    def nicedir(self):
        d = self.dir
        if isabs(d) and "HOME" in os.environ:
            home = os.environ["HOME"]
            if self.dir_normcase.startswith(home):
                d = "~" + d[len(home):]
        return d
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
            if startswith:
                if caseSensitive:
                    if not self.base.startswith(word):
                        return False
                else:
                    if not self.ibase.startswith(word):
                        return False
            else:
                if caseSensitive:
                    if word not in self.base:
                        return False
                else:
                    if word not in self.ibase:
                        return False
        return True

class ProjectHit(PathHit):
    type = "project-path"
    def __init__(self, path, project_name, project_base_dir):
        self.project_name = project_name
        self.project_base_dir = project_base_dir
        super(ProjectHit, self).__init__(path)
    @property
    def label(self):
        if self.project_base_dir:
            if self.dir == self.project_base_dir:
                return u"%s %s {%s}%s" % (self.base, MDASH, self.project_name, os.sep)
            else:
                return u"%s %s {%s}%s%s" % (self.base, MDASH, self.project_name,
                    os.sep, self.dir[len(self.project_base_dir)+1:])
        else:
            return u"%s %s %s" % (self.base, MDASH, self.nicedir)

class StreamResultsView(object):
    """A base implementation of the API required by 
    `Driver.search(..., resultsView)` for reporting results from a search.
    """
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
    def searchStarted(self):
        pass
    def searchAborted(self):
        pass
    def searchCompleted(self):
        pass


class Request(object):
    """Virtual base class for requests put on the `Driver` queue."""

class StopRequest(Request):
    """Request to stop the driver thread altogether."""

class SearchRequest(Request):
    """A light object to represent a fastopen search request.
    
    One of these is returned by `Driver.search(...)` and it has a `.wait()`
    method on which one can wait for the request to complete.
    """
    def __init__(self, query, gatherers, cwds, pathExcludes, resultsView):
        self.query = query
        self.gatherers = gatherers
        self.cwds = cwds
        self.pathExcludes = pathExcludes
        self.resultsView = resultsView
        self._event = threading.Event()
    def wait(self, timeout=None):
        self._event.wait(timeout)
    def complete(self):
        self._event.set()

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
            resultsView=None):
        """Start a search for files. This cancels a currently running search.

        @param query {str} A query string.
        @param gatherers {Gatherers} The gatherers from which to get files.
        @param cwds {list} A list of current working directories. Used for
            relative path queries.
        @param pathExcludes {list} A list of path patterns to exclude. If not
            given, default is `DEFAULT_PATH_EXCLUDES`.
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
            resultsView or StreamResultsView())
        self._queue.put(r)
        return r

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
            
            # See if this is a path query, i.e. a search for an absolute or
            # relative path.
            dirQueries = []
            if isabs(query):
                dirQueries.append(query)
            elif query.startswith("~"):
                expandedQuery = expanduser(query)
                if isabs(expandedQuery):
                    dirQueries.append(expandedQuery)
            elif ('/' in query or (sys.platform == "win32" and '\\' in query)):
                dirQueries += [join(d, query) for d in request.cwds]

            if dirQueries:
                hitPaths = set()
                pathExcludes = request.pathExcludes
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
                            resultsView.addHits(hits)
        
            else:
                # Second value is whether to be case-sensitive in filtering.
                queryWords = [(w, w.lower() != w, False) for w in query.split()]
                
                BLOCK_SIZE = 50 - 1  #TODO: ask gatherer if can just get all?
                hitPaths = set()
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
                                hits.append(hit)
                                hitPaths.add(path)
                            if j >= BLOCK_SIZE:
                                break
                        else:
                            exhausted.append(i)
                        if not self._queue.empty():  # Another request, abort this one.
                            return
                        #log.debug("adding %d hits from %r", len(hits), gatherer)
                        if hits:
                            resultsView.addHits(hits)
                    if exhausted:
                        for i in reversed(exhausted):
                            del generators[i]
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
        for dir in self.dirs:
            try:
                names = os.listdir(dir)
            except EnvironmentError, ex:
                log.warn("couldn't read `%s' dir: %s", dir, ex)
            else:
                for name in names:
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


class KomodoProjectGatherer(Gatherer):
    """A gatherer of files in a Komodo project."""
    def __init__(self, project):
        self.project = project
        self.name = "project '%s'" % project.get_name()
        self.base_dir = (project.get_liveDirectory()
            if self._is_project_live(project) else None)
    def _is_project_live(self, project):
        prefset = project.get_prefset()
        return (prefset.hasBooleanPref("import_live")
                and prefset.getBooleanPref("import_live"))
    def gather(self):
        #XXX:TODO the cached/indexed version
        project_name = self.project.get_name()
        if project_name.endswith(".kpf"):
            project_name = project_name[:-4]
        base_dir = self.base_dir
        i = 0
        for path in self.project.genLocalPaths():
            yield ProjectHit(path, project_name, base_dir)

class CachingKomodoProjectGatherer(Gatherer):
    """A gatherer of files in a Komodo project."""
    def __init__(self, project):
        self.project = project
        self.name = "project '%s'" % project.get_name()
        self.base_dir = (project.get_liveDirectory()
            if self._is_project_live(project) else None)
        project_name = self.project.get_name()
        if project_name.endswith(".kpf"):
            project_name = project_name[:-4]
        self.project_name = project_name
        self._hits = []  # cache of already generated hits
    
    def _is_project_live(self, project):
        prefset = project.get_prefset()
        return (prefset.hasBooleanPref("import_live")
                and prefset.getBooleanPref("import_live"))
    
    _raw_generator = None
    def gather(self):
        # First yield any hits we've already gathered and cached.
        for hit in self._hits:
            yield hit
        
        # Then, yield and cache any remaining ones.
        if self._raw_generator is None:
            self._raw_generator = self.project.genLocalPaths()
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
        # Really the 'id' in the .kpf file, but we'll fake it well
        # enough for here.
        self.id = md5(name).hexdigest()
        self._name = name
        self._base_dir = base_dir
        if includes is None:
            self._includes = []
        else:
            self._includes = includes
        if excludes is None:
            self._excludes = "*.*~;*.bak;*.tmp;CVS;.#*;*.pyo;*.pyc;.svn;*%*;*.kpf".split(';')
        else:
            self._excludes = excludes
        self._prefset = MockKomodoPrefset(import_live=is_live)
        self._slow = slow

    def get_prefset(self):
        return self._prefset

    def get_name(self):
        return self._name

    def get_liveDirectory(self):
        if self._prefset["import_live"]:
            return self._base_dir
        else:
            raise AttributeError("no 'liveDirectory' attribute (project "
                "isn't a live folder)")

    def genLocalPaths(self):
        sys.path.insert(0, join(dirname(dirname(dirname(dirname(
            abspath(__file__))))), "find"))
        try:
            import findlib2
        finally:
            del sys.path[0]
        paths = findlib2.paths_from_path_patterns(
            [self._base_dir],
            recursive=True,
            includes=self._includes,
            excludes=self._excludes,
            on_error=None,
            follow_symlinks=True,
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
            MockKomodoProject("fastopen.kpf",
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
            MockKomodoProject("komodo.kpf",
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


def main(argv):
    logging.basicConfig()
    query = ' '.join(argv[1:])
    _test2(query)

if __name__ == "__main__":
    sys.exit(main(sys.argv))

