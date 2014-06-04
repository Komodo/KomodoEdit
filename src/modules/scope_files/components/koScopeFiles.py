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

    def search(self, query, path, opts, callback):
        log.debug("Starting Search: " + query)
        opts = json.loads(opts)

        # Prepare Regex Object
        query = ' '.join(query.split())             # Reduce/trim whitespace
        query = re.escape(query).split("\\ ")       # Escape query and split by whitespace
        query = "(" + (")(.*?)(".join(query)) + ")" # Add regex groups
        query = re.compile(query, re.IGNORECASE)

        # Prepare Replacement
        replacement = ""
        for x in range(1,query.groups+1):
            if x % 2 == 0:
                replacement += "\\" + str(x)
            else:
                replacement += "<strong>\\" + str(x) + "</strong>"

        # Iterate over project paths and attempt to match them agains our query
        numResults = 0
        walker = self.walkPaths(path, opts)

        try:
            for pathEntry in walker:
                description = query.sub(replacement, pathEntry["path"])
                if pathEntry["path"] is not description:
                    callback.callback(0, [
                        os.path.basename(pathEntry["path"]),
                        pathEntry["path"],
                        pathEntry["type"],
                        pathEntry["path"].count(os.sep),
                        description])

                    numResults+=1
                    walker.send(numResults is opts.get("maxresults", 50))
        except StopIteration:
            log.debug("Result limit reached")

        if numResults is 0:
            callback.callback(0, "done");

    def walkPaths(self, path, opts):
        if path in self.cache:
            for pathEntry in self.cache[path]:
                shouldStop = yield pathEntry
                if shouldStop:
                    break
        else:
            self.cache[path] = []
            for subPath, fileType in paths_from_path_patterns([path],
                    dirs="always",
                    follow_symlinks=True,
                    includes=opts.get("includes", []),
                    excludes=opts.get("excludes", []),
                    yield_filetype=True):
                
                if subPath is path:
                    continue

                pathEntry = {
                    "path": subPath[len(path):],
                    "type": fileType
                }
                self.cache[path].append(pathEntry)
                yield pathEntry
