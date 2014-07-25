#!python
# Copyright (c) 2014-2014 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

# Todo: Cleanup this lib - it's becoming a mess

"""The main PyXPCOM module for Commando's Files scope"""

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

log = logging.getLogger("commando-scope-files-py")
#log.setLevel(10)

class koScopeFiles:

    _com_interfaces_ = [Ci.koIScopeFiles]
    _reg_desc_ = "Commando - Files Scope"
    _reg_clsid_ = "{16265b4a-4323-4250-8ef1-b4f4ee859136}"
    _reg_contractid_ = "@activestate.com/commando/koScopeFiles;1"

    project = None
    _history = None
    activeUuid = None
    walker = None

    @property
    def history(self):
        if not self._history:
            historySvc = Cc["@activestate.com/koHistoryService;1"].getService(Ci.koIHistoryService)
            self._history = UnwrapObject(historySvc)
        return self._history

    def __init__(self):
        self.walker = Walker()

    def search(self, query, uuid, path, opts, callback):
        log.debug("Starting Search: " + query)

        self.activeUuid = uuid
        queryOpts = {}
        queryOpts["numResults"] = 0
        queryOpts["callback"] = callback

        opts = json.loads(opts)

        # Prepare Regex Object
        query = ' '.join(query.split())             # Reduce/trim whitespace
        query = re.escape(query).split("\\ ")       # Escape query and split by whitespace
        queryOpts["words"] = query
        query = "(" + (")(.*?)(".join(query)) + ")" # Add regex groups
        query = re.compile(query, re.IGNORECASE)
        queryOpts["query"] = query

        # Prepare Replacement
        replacement = ""
        for x in range(1,query.groups+1):
            if x % 2 == 0:
                replacement += "\\" + str(x)
            else:
                replacement += "<label class='strong' value=\"\\" + str(x) + "\"/>"
        queryOpts["replacement"] = replacement

        # Prepate Path
        path = os.path.realpath(path)
        queryOpts["path"] = path
        queryOpts["stripPathRe"] = re.compile("^" + re.escape(path) + "/?")

        t = threading.Thread(target=self.walker.start, args=(path, uuid, opts, queryOpts, self.walkCallback, self.walkCallbackComplete))
        t.start()

    def walkCallback(self, path, dirnames, filenames, uuid, opts, queryOpts):
        if (self.activeUuid is not uuid):
            return
        
        self.evaluatePaths(path, dirnames, filenames, uuid, opts, queryOpts)

    @components.ProxyToMainThreadAsync
    def walkCallbackComplete(self, uuid, queryOpts):
        if (uuid is self.activeUuid):
            log.debug(uuid + " End Reached")
            queryOpts["callback"].callback(0, "done")

    def evaluatePaths(self, path, dirnames, filenames, uuid, opts, queryOpts):
        for filename in dirnames + filenames:
            subPath = os.path.join(path, filename)
            if subPath is queryOpts["path"]:
                continue;

            replacement = queryOpts["query"].sub(queryOpts["replacement"], subPath)
            if subPath is not replacement:
                queryOpts["numResults"] = queryOpts["numResults"] + 1
                if queryOpts["numResults"] > opts.get("maxresults", 200):
                    log.debug(uuid + " Max results reached")
                    return self.walker.stop()

                pathEntry = {
                    "filename": filename,
                    "path": queryOpts["stripPathRe"].sub("", subPath) if len(subPath) > 1 else subPath,
                    "fullPath": subPath,
                    "type": "dir" if filename in dirnames else "file"
                }

                self.processResult(replacement, pathEntry, uuid, opts, queryOpts)

    def calculateWeight(self, pathEntry, opts, queryOpts):
        # Todo: figure out a good way to normalize weight numbers
        weight = 0
        depth = pathEntry["path"].count(os.sep) + 1
        weight += (10 / depth) * opts.get("weightDepth", 1)

        matchWeight = 0
        filename = os.path.basename(pathEntry["path"])
        for word in queryOpts["words"]:
            if word in filename:
                matchWeight += 10
        weight += matchWeight * opts.get("weightMatch", 1)

        # cant be accessed outside of main thread
        # we should track our own usage numbers to make this more relevant
        # to the files scope specifically
        #hits = self.history.get_num_visits("file://"+pathEntry["fullPath"], -1)
        #weight += hits * opts.get("weightHits", 1)

        return weight;

    def processResult(self, description, pathEntry, uuid, opts, queryOpts):
        weight = self.calculateWeight(pathEntry, opts, queryOpts)

        result = [
            pathEntry["filename"],
            pathEntry["path"],
            pathEntry["fullPath"],
            pathEntry["type"],
            description,
            weight
        ];

        self.returnResult(result, uuid, queryOpts)

    @components.ProxyToMainThreadAsync
    def returnResult(self, result, uuid, queryOpts):
        if (uuid is self.activeUuid):
            queryOpts["callback"].callback(0, result)

    def buildCache(self, path, opts):
        opts = json.loads(opts)
        t = threading.Thread(target=self.walker.start, args=(path, "build"+path, opts))
        t.start()

class Walker:

    activeUuid = None
    cache = {}

    callback = None
    callbackComplete = None

    activeWalkers = 0

    # Stop the active search
    def stop(self):
        self.activeUuid = None

    # Start a new search
    def start(self, path, uuid, opts, queryOpts = None, callback = None, callbackComplete = None):
        self.activeUuid = uuid
        self.activeWalkers = 0
        self.callback = callback
        self.callbackComplete = callbackComplete

        self.walk(path, uuid, opts, queryOpts)

    def walk(self, path, uuid, opts, queryOpts):
        dirnames = [path]
        while (len(dirnames) > 0):
            _dirnames = []
            for dirname in dirnames:
                self.activeWalkers = self.activeWalkers + 1
                _dirnames = _dirnames + (self.walkCache(dirname, uuid, opts, queryOpts) or [])
                self.activeWalkers = self.activeWalkers - 1

            if opts.get("recursive", True):
                dirnames = _dirnames
            else:
                dirnames = []

        if self.activeWalkers is 0 and self.callbackComplete:
            self.callbackComplete(uuid, queryOpts)

    # Walk our cache for the given path
    def walkCache(self, path, uuid, opts, queryOpts):
        if self.activeUuid is not uuid:
            return # Break out if this search is no longer active
        
        # If the cache for this path does not exist pass it along to the IO walker
        if not self.cache.get(path, False):
            self.activeWalkers = self.activeWalkers + 1
            self.walkIO(path, uuid, opts, queryOpts)
            return

        # Get dirnames, filenames from cache
        [dirnames, filenames] = self.cache[path];
        
        if (self.callback):
            self.callback(path, dirnames, filenames, uuid, opts, queryOpts)

        return [ os.path.join(path,dirname) for dirname in dirnames ]

    def notify(self, path, dirnames, filenames, uuid, opts, queryOpts):
        if not self.cache.get(path, False):
            self.cache[path] = [dirnames, filenames]

        self.activeWalkers = self.activeWalkers - 1
        self.walk(path, uuid, opts, queryOpts)

    def walkIO(self, path, uuid, opts, queryOpts):
        # Invoke the main walker lib
        walker = paths_from_path_patterns([path],
                dirs="always",
                follow_symlinks=True,
                includes=opts.get("includes", []),
                excludes=opts.get("excludes", []),
                yield_structure=True,
                recursive=False)
        for subPath, dirnames, filenames in walker:
            self.notify(subPath, dirnames, filenames, uuid, opts, queryOpts)

