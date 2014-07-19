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

class koScopeFiles():

    _com_interfaces_ = [Ci.koIScopeFiles]
    _reg_desc_ = "Commando - Files Scope"
    _reg_clsid_ = "{16265b4a-4323-4250-8ef1-b4f4ee859136}"
    _reg_contractid_ = "@activestate.com/commando/koScopeFiles;1"

    project = None
    cache = {}
    _history = None
    activeUuid = None

    def search(self, query, uuid, path, opts, callback):
        self.activeUuid = uuid
        t = threading.Thread(target=self._search, args=(query, uuid, path, opts, callback))
        t.start()
        
    def _search(self, query, uuid, path, opts, callback):
        log.debug("Starting Search: " + query)

        opts = json.loads(opts)

        # Prepare Regex Object
        query = ' '.join(query.split())             # Reduce/trim whitespace
        query = re.escape(query).split("\\ ")       # Escape query and split by whitespace
        words = query
        query = "(" + (")(.*?)(".join(query)) + ")" # Add regex groups
        query = re.compile(query, re.IGNORECASE)

        # Prepare Replacement
        replacement = ""
        for x in range(1,query.groups+1):
            if x % 2 == 0:
                replacement += "\\" + str(x)
            else:
                replacement += "<label class='strong' value=\"\\" + str(x) + "\"/>"

        # Iterate over project paths and attempt to match them agains our query
        numResults = 0
        walker = self.walkPaths(path, opts)

        try:
            numResults = 0
            while numResults is not False:
                numResults = self.processEntry(walker, query, uuid, path, opts, words,
                                         replacement, callback, numResults)

            log.debug(uuid + " - Directory walk complete")

        except StopIteration:
            log.debug(uuid + " - iteration stopped")

        if numResults is 0:
            self.doCallback(callback, "done")

    def processEntry(self, walker, query, uuid, path, opts, words, replacement, callback, numResults=0):
        if numResults is 0:
            pathEntry = walker.send(None)
        else:
            maxResultsReached = numResults is opts.get("maxresults", 200)
            if maxResultsReached:
                log.debug(uuid + " Max results reached")

            pathEntry = walker.send(maxResultsReached)

        if (self.activeUuid is not uuid):
            log.debug(uuid + " No longer active, stopping")
            walker.send(True) # Stop iteration
            return False

        description = query.sub(replacement, pathEntry["path"])
        if pathEntry["path"] is not description:
            # Todo: figure out a good way to normalize weight numbers
            weight = 0
            depth = pathEntry["path"].count(os.sep) + 1
            weight += (10 / depth) * opts.get("weightDepth", 1)

            matchWeight = 0
            filename = os.path.basename(pathEntry["path"])
            for word in words:
                if word in filename:
                    matchWeight += 10
            weight += matchWeight * opts.get("weightMatch", 1)

            self.processResult(pathEntry, path, filename, description, weight, opts, callback)
            numResults+=1
            
        return numResults
        
    @components.ProxyToMainThreadAsync
    def processResult(self, pathEntry, path, filename, description, weight, opts, callback):
        # history.get_num_visits must happen on the main thread
        hits = self.history.get_num_visits("file://"+path+pathEntry["path"], -1)
        weight += hits * opts.get("weightHits", 1)

        result = [
            filename,
            pathEntry["path"],
            pathEntry["fullPath"],
            pathEntry["type"],
            description,
            weight
        ];
        callback.callback(0, result)
                
    @components.ProxyToMainThreadAsync
    def doCallback(self, callback, arg):
        callback.callback(0, arg)

    # Todo: Refactor to have separate generator / consumer logic
    def walkPaths(self, path, opts):
        if path in self.cache and opts.get("recursive", True) is True:
            for pathEntry in self.cache[path]:
                shouldStop = yield pathEntry
                if shouldStop:
                    break
        else:
            if opts.get("recursive", True):
                cache = []

            if len(path) > 1:
                stripPathRe = re.compile("^" + re.escape(path) + "/?")

            walker = paths_from_path_patterns([path],
                    dirs="always",
                    follow_symlinks=True,
                    includes=opts.get("includes", []),
                    excludes=opts.get("excludes", []),
                    yield_filetype=True,
                    recursive=opts.get("recursive", True))
            for subPath, fileType in walker:
                
                if subPath is path:
                    continue

                subPath = os.path.realpath(subPath)

                pathEntry = {
                    "path": stripPathRe.sub("", subPath) if len(path) > 1 else subPath,
                    "fullPath": subPath,
                    "type": fileType
                }

                if opts.get("recursive", True):
                    cache.append(pathEntry)

                shouldStop = yield pathEntry
                if shouldStop:
                    log.debug("Stopping directory walk (max results reached?)")
                    raise StopIteration

            # Append to cache only when it is completely done
            if opts.get("recursive", True):
                log.debug("Cache size: " + str(len(cache)))
                self.cache[path] = cache

    def buildCache(self, path, opts):
        t = threading.Thread(target=self._buildCache, args=(path, opts))
        t.start()

    def _buildCache(self, path, opts):
        opts = json.loads(opts)
        for x in self.walkPaths(path, opts):
            None

    @property
    def history(self):
        if self._history:
            return self._history

        historySvc = Cc["@activestate.com/koHistoryService;1"].getService(Ci.koIHistoryService)
        self._history = UnwrapObject(historySvc)
        return self._history
