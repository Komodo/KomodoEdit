# Copyright (c) 2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

"""Common definitions for the Citadel parts of codeintel."""

import os
import sys
import md5
import re
import stat
import time
import threading
import logging

from codeintel2.common import *



log = logging.getLogger("codeintel.citadel")



class ScanRequest:
    """A request to scan a file for code intel.
    
    A ScanRequest has the following properties:
        "id" is a unique ID for this request. It is assigned by the
            scheduler when the request is made.
        "path" is the full canonicalized path to the file to scan. The path
            is canonicalized when set in the constructor.
        "language" is the content-type of the file. This determines what
            "Language Engine(s)" are used to scan it. (XXX Specify allowable
            range of languages.)
        "priority" must be one of the PRIORITY_* priorities.
        "force" is a boolean indicating if a scan should be run even if
            the database is already up-to-date for this content.
        "content" is the file content. This can be explicitly given in the
            constructor. This is useful if the current content is not
            saved to disk or if it is difficult to retrieve the content.
            If not specified the loadContent() method will be used to
            get it from the filename.  Subclasses can override
            loadContent() if necessary.
        "md5sum" is the MD5 hexdigest of the content.  If already
            calculated it may be specified in the constructor. Otherwise
            this can be calculated as needed via the calculateMD5()
            method.
        "mtime" is the modified time of the file/content. If this is not
            given, it is determined lazily (if content is NOT specified) or
            defaults to the current time (if content IS specified).
        "scan_imports" is a boolean (default true) indicating that
            imports should be scheduled for scanning when this file is
            loaded into the database.
        "on_complete" (optional) is a callable to call when the scan
            and load is complete.
    """
    def __init__(self, path, language, priority, force=0, content=None,
                 md5sum=None, mtime=None, scan_imports=True,
                 on_complete=None):
        self.id = None
        self.path = path
        self.language = language
        self.priority = priority
        self.force = force
        self.content = content
        if mtime:
            self.mtime = mtime
        elif content is not None:
            # Presumably if the content is being specified rather than having
            # the request's loadContent() determine it, then it is from an
            # editor buffer and may have changed just recently.
            self.mtime = int(time.time())
        else:
            self.mtime = None # determine lazily
        self.md5sum = md5sum
        self.scan_imports = scan_imports
        self.on_complete = on_complete
        self.complete_event = threading.Event() #XXX use a pool
    def __repr__(self):
        return "<ScanRequest id:%r, path:'%s'>" % (self.id, self.path)
    def __str__(self):
        return "scan request '%s' (prio %s)" % (self.path, self.priority)
    def complete(self):
        """Called by scheduler when this scan is complete (whether or
        not it was successful/skipped/whatever).
        """
        log.info("complete %s", self)
        self.complete_event.set()
        if self.on_complete:
            try:
                self.on_complete()
            except:
                log.exception("ignoring exception in ScanRequest "
                              "on_complete callback")
    def wait(self, timeout=None):
        """Can be called by code requesting a scan to wait for completion
        of this particular scan.
        """
        self.complete_event.wait(timeout)
    def loadContent(self):
        """If self.content is not set, load it from self.path.
        
        This also sets self.mtime, if necessary.
        This can raise an EnvironmentError if the file is not accessible.
        """
        if self.content is None:
            self.mtime = os.stat(self.path)[stat.ST_MTIME]
            fin = open(self.path, "r")
            try:
                self.content = fin.read()
            finally:
                fin.close()
    def calculateMD5(self):
        """Calculate and set self.md5sum if is it not already set."""
        if self.md5sum is None:
            self.loadContent()
            self.md5sum = md5.new(self.content).hexdigest()
    def getCanonicalPath(self):
        return canonicalizePath(self.path)

