#!python
# Copyright (c) 2004-2011 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

"""Shared base class for LangDirsLib / MultiLangDirsLib
See langlib.py / multilanglib.py
"""

import logging
from os.path import join
from contextlib import contextmanager
from codeintel2.common import *

#---- globals
log = logging.getLogger("codeintel.db")
#log.setLevel(logging.DEBUG)

#---- Base lang lib implementation
class LangDirsLibBase(object):
    def __init__(self):
        self._have_ensured_scanned_from_dir_cache = set()

    def ensure_all_dirs_scanned(self, ctlr=None):
        """Ensure that all importables in this dir have been scanned
        into the db at least once.
        """
        # TODO: Wrap with a progress notification - we know how many directories
        #       are going to be scanned. We should be tieing the notification
        #       with the controller/ui_handler somehow - as it's going to be
        #       window specific.
        #progressEvent = createProgressEvent(len(self.dirs))
        #try:
        for dir in self.dirs:
            if ctlr and ctlr.is_aborted():
                log.debug("ctlr aborted")
                break
            self.ensure_dir_scanned(dir, ctlr)
            #progressEvent.incrementProgress(1)
        #finally:
        #    progressEvent.finished()

    def ensure_dir_scanned(self, dir, ctlr=None):
        """Ensure that all importables in this dir have been scanned
        into the db at least once.
        """
        #TODO: should "self.lang" in this function be "self.sublang" for
        # the MultiLangDirsLib case?
        if dir not in self._have_ensured_scanned_from_dir_cache:
            event_reported = False
            res_index = self.lang_zone.load_index(dir, "res_index", {})
            importables = self._importables_from_dir(dir)
            importable_values = [i[0] for i in importables.values()
                                 if i[0] is not None]
            for base in importable_values:
                if ctlr and ctlr.is_aborted():
                    log.debug("ctlr aborted")
                    return
                if base not in res_index:
                    if not event_reported:
                        self.lang_zone.db.report_event(
                            "scanning %s files in '%s'" % (self.lang, dir))
                        event_reported = True
                    try:
                        buf = self.mgr.buf_from_path(join(dir, base),
                                                     lang=self.lang)
                    except (EnvironmentError, CodeIntelError), ex:
                        # This can occur if the path does not exist, such as a
                        # broken symlink, or we don't have permission to read
                        # the file, or the file does not contain text.
                        continue
                    if ctlr is not None:
                        ctlr.info("load %r", buf)
                    buf.scan_if_necessary()

            # Remove scanned paths that don't exist anymore.
            removed_values = set(res_index.keys()).difference(importable_values)
            for base in removed_values:
                if ctlr and ctlr.is_aborted():
                    log.debug("ctlr aborted")
                    return
                if not event_reported:
                    self.lang_zone.db.report_event(
                        "scanning %s files in '%s'" % (self.lang, dir))
                    event_reported = True
                basename = join(dir, base)
                self.lang_zone.remove_path(basename)

            self._have_ensured_scanned_from_dir_cache.add(dir)
