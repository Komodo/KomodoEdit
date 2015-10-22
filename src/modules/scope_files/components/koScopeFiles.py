#!python
# Copyright (c) 2014-2014 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

# Todo: Cleanup this lib - it's becoming a mess

"""The main PyXPCOM module for Commando's Files scope"""

from os.path import abspath, dirname, exists, expanduser, join
import sys
from xpcom.components import interfaces as Ci
from xpcom.components import classes as Cc
from xpcom import components
from xpcom.server import UnwrapObject
from findlib2 import paths_from_path_patterns
import json
import scandir
import re
import os
import logging
import threading


prefs = Cc["@activestate.com/koPrefService;1"].getService(Ci.koIPrefService).prefs
log = logging.getLogger("commando-scope-files-py")
#log.setLevel(10)

class koScopeFiles:

    _com_interfaces_ = [Ci.koIScopeFiles]
    _reg_desc_ = "Commando - Files Scope"
    _reg_clsid_ = "{16265b4a-4323-4250-8ef1-b4f4ee859136}"
    _reg_contractid_ = "@activestate.com/commando/koScopeFiles;1"

    _history = None
    activeUuid = None
    searches = {}

    # Cache Data
    cache = {}
    observers = 0

    @property
    def history(self):
        if not self._history:
            historySvc = Cc["@activestate.com/koHistoryService;1"].getService(Ci.koIHistoryService)
            self._history = UnwrapObject(historySvc)
        return self._history

    def stopExpiredSearches(self):
        for uuid in self.searches.keys():
            if uuid is not self.activeUuid:
                self.searches[uuid].stop()
                del self.searches[uuid]

    def search(self, query, uuid, paths, opts, callback):
        log.debug(uuid + " - Starting Search: " + query)
        
        paths = paths.split(",")

        self.activeUuid = uuid
        self.stopExpiredSearches()
        
        opts = json.loads(opts)
        opts["uuid"] = uuid
        opts["callback"] = callback
        opts["getShortcuts"] = self.getShortcuts

        self.searches[uuid] = Searcher(self, opts, self.onSearchResults, self.onSearchComplete)
        t = threading.Thread(target=self.searches[uuid].start, args=(query, paths),
                             name="Scope files search")
        t.setDaemon(True)
        t.start()

    @components.ProxyToMainThreadAsync
    def onSearchResults(self, results, opts):
        if opts["uuid"] is self.activeUuid:
            log.debug(self.activeUuid + " - Passing back results")
            opts["callback"].callback(0, results)

    @components.ProxyToMainThreadAsync
    def onSearchComplete(self, opts):
        if opts["uuid"] is self.activeUuid:
            log.debug(self.activeUuid + " - Done")
            opts["callback"].callback(0, "done")

    def buildCache(self, path, opts):
        opts = json.loads(opts)
        opts["uuid"] = "cache-builder"
        walker = Walker(self, opts)
        t = threading.Thread(target=walker.start, args=(path, ""),
                             name="Scope files build cache")
        t.setDaemon(True)
        t.start()

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
            godir = applib.roaming_user_data_dir("Go", "TrentMick")
            path = join(godir, "shortcuts.xml")
        return path

    def onShortcutFileModified(self, *args):
        self.shortcutsVersion += 1
        self._shortcutsCache = None

    shortcutsVersion = 1
    _shortcutsCache = None
    _shortcutsObserverAdded = False
    def getShortcuts(self):
        if self._shortcutsCache is None:
            from xml.etree import ElementTree as ET
            path = self.getShortcutsFile()
            shortcuts = { "~": expanduser("~") }
            if not path or not exists(path):
                return shortcuts
            try:
                fin = open(path)
            except IOError:
                log.exception("Unable to open shortcuts file: %r", path)
                return shortcuts
            try:
                shortcuts_elem = ET.parse(fin).getroot()
                for child in shortcuts_elem:
                    shortcuts[child.get("name")] = child.get("value")
            finally:
                fin.close()
            self._shortcutsCache = shortcuts

            # Watch for changes to the shortcut file and reload it when changed.
            if not self._shortcutsObserverAdded:
                self._shortcutsObserverAdded = True
                fileNotificationSvc = Cc["@activestate.com/koFileNotificationService;1"].getService(Ci.koIFileNotificationService)
                fileNotificationSvc.addObserver(self.onShortcutFileModified,
                                                path,
                                                fileNotificationSvc.WATCH_FILE,
                                                fileNotificationSvc.FS_NOTIFY_ALL)

        return self._shortcutsCache

    def getShortcutsAsJson(self):
        return json.dumps(self.getShortcuts())

    def deleteCachePath(self, path):
        log.debug("Deleting cached path: " + path)

        if self.cache.get(path):
            del self.cache[path]

    def emptyCache(self):
        log.debug("Emptying Cache")

        self.cache = {}

class Searcher:

    def __init__(self, koScopeFiles, opts, callback, callbackComplete):
        self._stop = False

        self.scopeFiles = koScopeFiles
        self.opts = opts
        self.callback = callback
        self.callbackComplete = callbackComplete

        self.resultsPending = []
        self.resultTimer = None

        self.walkers = {}
        self.searchComplete = False
        
        self.stripPathRe = {}

    def stop(self, soft = False):
        log.debug(self.opts["uuid"] + " Stopping Searcher")
        
        if not soft:
            self._stop = True

        for walker in self.walkers.itervalues():
            walker.stop()

    def start(self, query, paths):
        self.opts["numResults"] = 0
        self.opts["queryOriginal"] = query
        self.opts["query"] = []
        self.paths = paths
        self.pathsCompleted = 0
        
        log.debug(self.opts["uuid"] + " Searching for " + query + " under " + ", ".join(paths))

        if self.opts["queryOriginal"] != "":
            # Prepare Regex Object
            self.opts["query"] = query.lower().split()

            words = []
            for word in self.opts["query"]:
                words.append(re.escape(word))

        # Check shortcuts - and we only care about the first word.
        if self.opts.get("allowShortcuts") and len(self.opts["query"]) == 1:
            self.searchShortcuts(self.opts["query"][0])
            
        for path in paths:
            self.searchPath(query, path)

    def searchPath(self, query, path):
        _path = os.path.realpath(path)
        
        log.debug(self.opts["uuid"] + " Searching for " + query + " under " + _path)
        
        self.stripPathRe[path] = re.compile("^" + re.escape(_path) + "/??")
        
        self.walkers[path] = Walker(self.scopeFiles, self.opts, self.onWalk, self.onWalkComplete)
        t = threading.Thread(target=self.walkers[path].start, args=(_path, path),
                             name="Path Walker " + path)
        t.setDaemon(True)
        t.start()

    def searchShortcuts(self, word):
        getShortcuts = self.opts.get("getShortcuts")
        if getShortcuts:
            shortcuts = getShortcuts()
            log.debug("%d shortcuts loaded", len(shortcuts))
            for name, path in shortcuts.items():
                if not name.startswith(word):
                    continue
                log.debug("shortcut name matched: %r - %r", name, path)
                resulttype = "dir"
                if os.path.isfile(path):
                    resulttype = "file"
                description = "Komodo shortcut - " + path
                result = [
                    name,
                    path,
                    name,        # relative path
                    resulttype,  # type
                    description, # description
                    200,         # score, shortcuts are always relevant
                ]
                self.returnResult(result)

    def onWalk(self, path, parentPath, dirnames, filenames):
        for filename in dirnames + filenames:
            if self._stop:
                return

            subPath = os.path.join(path, filename)
            if subPath is parentPath:
                continue;

            matchScore = 0
            if self.opts["queryOriginal"] != "":
                matchScore = self._matchScore(subPath.lower(), self.opts["query"], 75)

            if self.opts["queryOriginal"] == "" or matchScore > 0:
                if matchScore > 0:
                    matchScore += self._matchScore(os.path.basename(subPath).lower(), self.opts["query"], 25, lazyMatch = True)

                pathEntry = {
                    "filename": filename,
                    "path": subPath,
                    "type": "dir" if filename in dirnames else "file",
                    "score": matchScore
                }

                self.processResult(pathEntry, parentPath)

                self.opts["numResults"] += 1
                if self.opts["numResults"] >= self.opts.get("maxresults", 200):
                    log.debug(self.opts["uuid"] + " Max results reached")
                    return self.stop(True)
                
    def _matchScore(self, string, words, weight = 100, lazyMatch = False):
        # Doing a loop for some reason is faster than all()
        # This isn't part of the main loop as this will be triggered far
        # more often than an actual match
        if not lazyMatch:
            for word in words:
                if word not in string:
                    return 0

        matchScore = 0
        sequence = False

        # Calculate how heavily each matched word affects the score
        if not lazyMatch:
            matchWeight = (weight * 0.25) / len(words)
        else:
            matchWeight = weight / len(words)

        for word in words:
            if word not in string:
                return 0

            # If sequence matter, record whether
            if not lazyMatch:
                index = string.index(word)
                if not sequence or index > sequence:
                    sequence = index
                else:
                    sequence = False

            matchScore += string.count(word) * matchWeight

        if not lazyMatch:
            if sequence and matchScore > 0:
                matchScore += weight * 0.25

            basename = os.path.basename(string)
            if word in basename and basename.index(words[-1]) == 0:
                matchScore += weight * 0.50

        if matchScore > weight:
            matchScore = weight

        return matchScore

    def processResult(self, pathEntry, parentPath):
        relativePath = pathEntry["path"]
        description = pathEntry["path"]

        if not self.opts.get("fullpath", False):
            description = self.stripPathRe[parentPath].sub("", description)

        # cant be accessed outside of main thread
        # we should track our own usage numbers to make this more relevant
        # to the files scope specifically
        #hits = self.history.get_num_visits("file://"+pathEntry["fullPath"], -1)
        #weight += hits * opts.get("weightHits", 1)

        result = [
            pathEntry["filename"],
            pathEntry["path"],
            pathEntry["type"],
            os.path.basename(parentPath) or "",
            description,
            pathEntry["score"]
        ];

        self.returnResult(result)
        
    def returnResult(self, result):
        self.resultsPending.append(result)

        if not self.resultTimer:
            self.resultTimer = threading.Timer(0.05, self._returnResults)
            self.resultTimer.start()

    def _returnResults(self):
        self.resultTimer = None
        
        results = self.resultsPending
        self.resultsPending = []
        log.debug(self.opts["uuid"] + " - Returning " + str(len(results)) + " results")
        self.callback(results, self.opts)

        if self.searchComplete:
            self.onWalkComplete()

    def onWalkComplete(self, path = "forced"):
        log.debug(self.opts["uuid"] + " - Walk complete for " + path);
        self.pathsCompleted = self.pathsCompleted + 1
        if (self.pathsCompleted < len(self.paths)):
            return
        
        self.searchComplete = True
        
        if self._stop or self.resultsPending:
            return

        log.debug(self.opts["uuid"] + " - sending callbackComplete");
        self.callbackComplete(self.opts)


class Walker:

    def __init__(self, koScopeFiles, opts, callback = None, callbackComplete = None):
        self.scopeFiles = koScopeFiles

        self._stop = False

        self.opts = opts
        self.callback = callback
        self.callbackComplete = callbackComplete

    # Stop the active search
    def stop(self):
        self._stop = True

        if self.callbackComplete:
            log.debug(self.opts["uuid"] + " Walker Stop called, forcing callbackComplete")
            self.callbackComplete(self.parentPath)
            self.callbackComplete = False

    # Start a new search
    def start(self, path, parentPath):
        self.parentPath = parentPath
        log.debug(self.opts["uuid"] + " Scanning path: " + path)
        self.walk(path)

    def walk(self, path):
        dirnames = [path]
        depth = 0
        maxDepth = prefs.getLong("commando_files_max_depth")
        while (len(dirnames) > 0):
            if self._stop:
                return 

            _dirnames = []
            for dirname in dirnames:
                _dirnames = _dirnames + (self.walkCache(dirname) or [])

            depth += 1
            if self.opts.get("recursive", True) and depth < maxDepth:
                dirnames = _dirnames
            else:
                dirnames = []

        if self.callbackComplete:
            log.debug(self.opts["uuid"] + " Done walking directory structure")
            self.callbackComplete(self.parentPath)
            self.callbackComplete = False

    # Walk our cache for the given path
    def walkCache(self, path):
        result = None

        if self.opts.get("usecache", True):
            result = self.scopeFiles.cache.get(path, False)

        if not result:
            result = self.scandir(path)

            if self.opts.get("cacheable", False):
                self.scopeFiles.cache[path] = result

        # Get dirnames, filenames from cache
        [dirnames, filenames] = result;
        
        if self.callback:
            self.callback(path, self.parentPath, dirnames, filenames)

        return [ os.path.join(path,dirname) for dirname in dirnames ]

    def scandir(self, path):
        # Invoke the main walker lib
        try:
            
            walker = paths_from_path_patterns([path],
                    dirs="always",
                    follow_symlinks=True,
                    includes=self.opts.get("includes", []),
                    excludes=self.opts.get("excludes", []),
                    yield_structure=True,
                    recursive=False)
            for subPath, dirnames, filenames in walker: # recursive=false means we only get 1 result
                return [dirnames, filenames]
            
        except OSError, e:
            log.error("OSError while walking path: " + path)
        except Exception, e:
            log.warn("Exception occurred while walking path: " + path + ", returning empty list")
            
        return [[],[]]

