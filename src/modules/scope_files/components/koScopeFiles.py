#!python
# Copyright (c) 2014-2014 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

"""The main PyXPCOM module for Commando's Files scope"""

from xpcom.components import interfaces as Ci
from xpcom.components import classes as Cc
from xpcom.server import UnwrapObject
from findlib2 import paths_from_path_patterns
import json
import scandir
import re
import os
import logging

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

    def search(self, query, path, opts, callback):
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
            for pathEntry in walker:
                description = query.sub(replacement, pathEntry["path"])
                if pathEntry["path"] is not description:

                    # Todo: figure out a good way to normalize weight numbers
                    weight = 0
                    hits = self.history.get_num_visits("file://"+path+pathEntry["path"], -1)
                    depth = pathEntry["path"].count(os.sep) + 1

                    weight += hits * opts.get("weightHits", 1)
                    weight += (10 / depth) * opts.get("weightDepth", 1)

                    matchWeight = 0
                    filename = os.path.basename(pathEntry["path"])
                    for word in words:
                        if word in filename:
                            matchWeight += 10

                    weight += matchWeight * opts.get("weightMatch", 1)

                    callback.callback(0, [
                        filename,
                        pathEntry["path"],
                        pathEntry["fullPath"],
                        pathEntry["type"],
                        description,
                        weight
                    ])

                    numResults+=1
                    walker.send(numResults is opts.get("maxresults", 50))
        except StopIteration:
            log.debug("Result limit reached")

        if numResults is 0:
            callback.callback(0, "done");

    def walkPaths(self, path, opts):
        if path in self.cache and opts.get("recursive", True) is True:
            for pathEntry in self.cache[path]:
                shouldStop = yield pathEntry
                if shouldStop:
                    break
        else:
            if opts.get("recursive", True):
                self.cache[path] = []

            if len(path) > 1:
                stripPathRe = re.compile("^" + re.escape(path) + "/?")
            for subPath, fileType in paths_from_path_patterns([path],
                    dirs="always",
                    follow_symlinks=True,
                    includes=opts.get("includes", []),
                    excludes=opts.get("excludes", []),
                    yield_filetype=True,
                    recursive=opts.get("recursive", True)):
                
                if subPath is path:
                    continue

                subPath = os.path.realpath(subPath)

                pathEntry = {
                    "path": stripPathRe.sub("", subPath) if len(path) > 1 else subPath,
                    "fullPath": subPath,
                    "type": fileType
                }

                if opts.get("recursive", True):
                    self.cache[path].append(pathEntry)

                yield pathEntry

    def buildCache(self, path, opts):
        opts = json.loads(opts)
        self.walkPaths(path, opts)

    @property
    def history(self):
        if self._history:
            return self._history

        historySvc = Cc["@activestate.com/koHistoryService;1"].getService(Ci.koIHistoryService)
        self._history = UnwrapObject(historySvc)
        return self._history
