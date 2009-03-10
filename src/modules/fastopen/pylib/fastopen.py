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

Make a search (second argument is the query string):

    d.search(gatherers, "foo")

This will print hits to stdout. To get and handle results directly, pass a
`resultsView` class (see `StreamResultsView` for example):

    d.search(gatherers, "foo", myResultsView)

Be sure to stop the driver thread when done:

    d.stop()
"""

import os
from os.path import (exists, expanduser, join, isdir, dirname, abspath,
    splitext, split, isabs)
import sys
import logging
import threading
from pprint import pprint, pformat
import time
from hashlib import md5
import Queue



#---- globals

log = logging.getLogger("fastopen")
log.setLevel(logging.INFO)

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
    """Represents a fast-find path (or open Komodo tab) "hit"."""
    def __init__(self, path):
        self.path = path
        self.dir, base = split(path)
        self.base = base
        self.ibase = base.lower()
        self.ext = splitext(base)[1]  #TODO: use smart-splitext from astools
        if self.ext == base:  # a dot file, e.g. ".cvspass"
            self.ext = ""
    def __str__(self):
        return self.path
    def __repr__(self):
        return "<Hit: %s>" % self.label.replace(MDASH, "--")
    @property
    def label(self):
        return u"%s %s %s" % (self.base, MDASH, self.nicedir)
    @property
    def nicedir(self):
        d = self.dir
        if isabs(d):
            home = os.environ["HOME"]
            if d.startswith(home):
                d = "~" + d[len(home):]
        return d
    def match(self, queryWords):
        """Return true if the given query matches this hit.
        
        @param queryWords {list} A list of 2-tuples of the form
            (query-word, is-case-sensitive), one for each query word.
        """
        for word, caseSensitive in queryWords:
            if (caseSensitive and word not in self.base
                or not caseSensitive and word not in self.ibase):
                return False
        return True

class ProjectHit(Hit):
    def __init__(self, path, project_name, project_base_dir):
        self.project_name = project_name
        self.project_base_dir = project_base_dir
        super(ProjectHit, self).__init__(path)
    @property
    def label(self):
        if self.project_base_dir:
            if self.dir == self.project_base_dir:
                return u"%s %s {%s}/" % (self.base, MDASH, self.project_name)
            else:
                return u"%s %s {%s}/%s" % (self.base, MDASH, self.project_name,
                    self.dir[len(self.project_base_dir)+1:])
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
            self._queue.put(None)
            if wait:
                self.join()

    def search(self, gatherers, query, resultsView=None):
        """Start a search for files. This cancels a currently running search.

        @param gatherers {Gatherers} The gatherers from which to get files.
        @param query,
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
        """
        self._queue.put((gatherers, query, resultsView or StreamResultsView()))

    def run(self):
        while True:
            # Get the latest request on the queue.
            request = self._queue.get()
            if request is None:  # signal from `.stop()` to exit
                return
            while True:
                try:
                    request = self._queue.get_nowait()
                except Queue.Empty:
                    break
                else:
                    if request is None:  # signal from `.stop()` to exit
                        return

            # Handle the request.
            log.debug("driver request: %r", request)
            try:
                self._handleRequest(request)
            except:
                log.exception("error handling request: %r", request)
    
    def _handleRequest(self, request):
        gatherers, query, resultsView = request
        resultsView.searchStarted()
        resultsView.resetHits()
        
        # Second value is whether to be case-sensitive in filtering.
        queryWords = [(w, w.lower() != w) for w in query.strip().split()]
        
        BLOCK_SIZE = 10 - 1  #TODO: bigger?
        hitPaths = set()
        generators = [(g, g.gather()) for g in gatherers]
        while generators:
            exhausted = []
            for i, (gatherer, generator) in enumerate(generators):
                hits = []
                for j, hit in enumerate(generator):
                    path = hit.path
                    if path not in hitPaths and hit.match(queryWords):
                        hits.append(hit)
                        hitPaths.add(path)
                    if j >= BLOCK_SIZE:
                        break
                else:
                    exhausted.append(i)
                if not self._queue.empty():  # Another request, abort this one.
                    resultsView.searchAborted()
                    return
                #log.debug("adding %d hits from %r", len(hits), gatherer)
                resultsView.addHits(hits)
            if exhausted:
                for i in reversed(exhausted):
                    del generators[i]

        resultsView.searchCompleted()

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
    """Gather files (excluding directories) in a given directory
    (non-recursive).
    """
    def __init__(self, name, dir, excludes=None):
        self.name = name
        self.dir = dir
        self.excludes = excludes or DEFAULT_PATH_EXCLUDES
    def gather(self):
        from fnmatch import fnmatch
        try:
            names = os.listdir(self.dir)
        except EnvironmentError, ex:
            log.warn("couldn't read `%s' dir: %s", dir, ex)
        else:
            for name in names:
                path = join(self.dir, name)
                for exclude in self.excludes:
                    if fnmatch(name, exclude):
                        break
                else:
                    if not isdir(path):
                        yield Hit(path)

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
        for path in self.project.genLocalPaths():
            yield ProjectHit(path, project_name, base_dir)


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
            is_live=True):
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

def _test(query):
    driver = Driver()
    
    try:
        gatherers = Gatherers()
        gatherers.append(DirGatherer("cwd", os.getcwd()))
        gatherers.append(KomodoProjectGatherer(
            MockKomodoProject("fastopen.kpf",
                expanduser("~/as/komodo/src/modules/fastopen"))))
        
        print "-- search 'foo'"
        driver.search(gatherers, "foo")
        time.sleep(0.1)
    
        print "-- search %r" % query
        driver.search(gatherers, query)
    
        time.sleep(2)
    finally:
        driver.stop(True)  # wait for termination

def main(argv):
    logging.basicConfig()
    query = ' '.join(argv[1:])
    _test(query)

if __name__ == "__main__":
    sys.exit(main(sys.argv))

