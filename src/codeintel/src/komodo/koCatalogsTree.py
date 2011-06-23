#!python
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
# 
# The contents of this file are subject to the Mozilla Public License
# Version 1.1 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
# 
# Software distributed under the License is distributed on an "AS IS"
# basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
# License for the specific language governing rights and limitations
# under the License.
# 
# The Original Code is Komodo code.
# 
# The Initial Developer of the Original Code is ActiveState Software Inc.
# Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
# ActiveState Software Inc. All Rights Reserved.
# 
# Contributor(s):
#   ActiveState Software Inc
# 
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
# 
# ***** END LICENSE BLOCK *****

"""The nsITreeView/koICodeIntelCatalogsTreeView implementation for the
"API Catalogs" list in the "Code Intelligence" prefs panel.
"""

import os
from os.path import basename, join, exists, normpath, normcase, dirname
import sys
from pprint import pprint, pformat
import logging
import operator
import threading
import traceback
import shutil

from xpcom import components, nsError, ServerException, COMException
from xpcom._xpcom import PROXY_SYNC, PROXY_ALWAYS, PROXY_ASYNC, getProxyForObject
from xpcom.server import UnwrapObject, WrapObject

from koTreeView import TreeView



#---- globals

log = logging.getLogger("koCatalogsTree")
#log.setLevel(logging.DEBUG)



#---- components

class KoCodeIntelCatalogsTreeView(TreeView):
    _com_interfaces_ = [components.interfaces.koICodeIntelCatalogsTreeView,
                        components.interfaces.nsITreeView]
    _reg_clsid_ = "{FD3C5BDF-391E-41CE-9635-7C2504BA5C6F}"
    _reg_contractid_ = "@activestate.com/koCodeIntelCatalogsTreeView;1"
    _reg_desc_ = "Komodo Code Intelligence Catalogs list tree view"

    def __init__(self):
        TreeView.__init__(self) # for debug logging: , debug="catalogs")
        self._rows = []

        koDirSvc = components.classes["@activestate.com/koDirs;1"].\
                   getService(components.interfaces.koIDirs)
        self.norm_user_apicatalogs_dir \
            = normpath(normcase(join(koDirSvc.userDataDir, "apicatalogs")))

        # Atoms for styling the checkboxes.
        self.atomSvc = components.classes["@mozilla.org/atom-service;1"].\
                  getService(components.interfaces.nsIAtomService)
        self._sortColAtom = self.atomSvc.getAtom("sort-column")

    def init(self, ciSvc, prefSet, prefName):
        self.ciSvc = ciSvc
        self.prefSet = prefSet
        self.prefName = prefName
        self.load()
        self._wasChanged = False

    _catalogs_zone_cache = None
    @property
    def catalogs_zone(self):
        if self._catalogs_zone_cache is None:
            self._catalogs_zone_cache \
                = UnwrapObject(self.ciSvc).mgr.db.get_catalogs_zone()
        return self._catalogs_zone_cache

    def load(self):
        prefStr = self.prefSet.getStringPref(self.prefName)
        try:
            self.selections = eval(prefStr)
        except ValueError, ex:
            self.selections = []
        self._sortData = (None, None)
        self._reload(self.selections)

    def _reload(self, selections=None):
        if selections is None: # by default use the current selections data
            selections = [r["selection"] or r["cix_path"] for r in self._rows
                          if r["selected"]]

        old_row_count = len(self._rows)
        self._rows = list( self.catalogs_zone.avail_catalogs(selections) )
        if self._sortData == (None, None):
            self._rows.sort(key=lambda r: (r["lang"], r["name"].lower()))
        else:
            sort_key, sort_is_reversed = self._sortData
            self._rows.sort(key=lambda r: safe_lower(r[sort_key]),
                            reverse=sort_is_reversed)

        if self._tree:
            self._tree.beginUpdateBatch()
            self._tree.rowCountChanged(0, len(self._rows)-old_row_count)
            self._tree.invalidate()
            self._tree.endUpdateBatch()

    def save(self):
        if not self._wasChanged:
            return

        selections = [r["selection"] or r["cix_path"] for r in self._rows
                      if r["selected"]]
        selections.sort()
        self.prefSet.setStringPref(self.prefName, repr(selections))

    def toggleSelection(self, row_idx):
        """Toggle selected state for the given row."""
        self._rows[row_idx]["selected"] = not self._rows[row_idx]["selected"]
        self._wasChanged = True
        if self._tree:
            # Could use .invalidateCell() but don't know how to create
            # column object.
            self._tree.invalidateRow(row_idx)

    def post_add(self, added_cix_paths):
        self._reload()

        # Figure out which rows to select.
        row_idxs = []
        for added_cix_path in added_cix_paths:
            for i, row in enumerate(self._rows):
                if row["cix_path"] == added_cix_path:
                    row_idxs.append(i)
                    break
            else:
                log.warn("could not select `%s': not found in "
                         "available catalogs", added_cix_path)

        # Select and UI-select the added rows.
        self.selection.clearSelection()
        for row_idx in row_idxs:
            self._wasChanged = True
            self._rows[row_idx]["selected"] = True
            if self._tree:
                self._tree.invalidateRow(i)
            self.selection.rangedSelect(row_idx, row_idx, True)

    def addPaths(self, paths):
        proxied_tree_view = getProxyForObject(None,
            components.interfaces.koICodeIntelCatalogsTreeView,
            self, PROXY_ALWAYS | PROXY_SYNC)
        return KoCodeIntelCatalogAdder(paths, proxied_tree_view.post_add)

    def post_remove(self, removed_cix_paths):
        self._reload()

    def removeUISelectedPaths(self):
        paths = []
        for i in range(self.selection.getRangeCount()):
            start, end = self.selection.getRangeAt(i)
            for row_idx in range(start, end+1):
                paths.append(self._rows[row_idx]["cix_path"])
        proxied_tree_view = getProxyForObject(None,
            components.interfaces.koICodeIntelCatalogsTreeView,
            self, PROXY_ALWAYS | PROXY_SYNC)
        return KoCodeIntelCatalogRemover(paths, proxied_tree_view.post_remove)

    def areUISelectedRowsRemovable(self):
        num_sel_ranges = self.selection.getRangeCount()
        if not num_sel_ranges:
            return False
        for i in range(num_sel_ranges):
            start, end = self.selection.getRangeAt(i)
            for row_idx in range(start, end+1):
                try:
                    row = self._rows[row_idx]
                except IndexError, ex:
                    # Selection is screwed up.
                    return False
                norm_cix_path = normpath(normcase(row["cix_path"]))
                if dirname(norm_cix_path) != self.norm_user_apicatalogs_dir:
                    return False
        return True

    def get_sortColId(self):
        sort_key = self._sortData[0]
        if sort_key is None:
            return None
        else:
            return "catalogs-" + sort_key
    def get_sortDirection(self):
        return self._sortData[1] and "descending" or "ascending"


    #---- nsITreeView methods
    if False: # set this to True when have debug logging to silence some methods
        def getImageSrc(self, row, col):
            return ''
        def isContainer(self, index):
            return False
        def getRowProperties(self, col, properties):
            pass
        def getCellProperties(self, row, column, properties):
            pass
        
    def get_rowCount(self):
        return len(self._rows)

    def getCellValue(self, row_idx, col):
        assert col.id == "catalogs-selected"
        return self._rows[row_idx]["selected"] and "true" or "false"

    def setCellValue(self, row_idx, col, value):
        assert col.id == "catalogs-selected"
        self._wasChanged = True
        self._rows[row_idx]["selected"] = (value == "true" and True or False)
        if self._tree:
            self._tree.invalidateRow(row_idx)

    def getCellText(self, row_idx, col):
        if col.id == "catalogs-selected":
            return ""
        else:
            try:
                key = col.id[len("catalogs-"):]
                return self._rows[row_idx][key]
            except KeyError, ex:
                raise ValueError("getCellText: unexpected col.id: %r" % col.id)

    def isEditable(self, row_idx, col):
        if col.id == "catalogs-selected":
            return True
        else:
            return False

    def getColumnProperties(self, col, properties):
        if col.id[len("catalogs-"):] == self._sortData[0]:
            properties.AppendElement(self._sortColAtom)

    def getCellProperties(self, row_idx, col, properties):
        if col.id == "catalogs-lang":
            try:
                lang = self._rows[row_idx]["lang"]
                properties.AppendElement(self.atomSvc.getAtom("Language" + lang))
            except KeyError, ex:
                raise ValueError("getCellText: unexpected col.id: %r" % col.id)

    def isSorted(self):
        return self._sortData != (None, None)

    def cycleHeader(self, col):
        if col.id == "catalogs-selected":
            return
        sort_key = col.id[len("catalogs-"):]
        old_sort_key, old_sort_is_reversed = self._sortData
        if sort_key == old_sort_key:
            sort_is_reversed = not old_sort_is_reversed
            self._rows.reverse()
        else:
            sort_is_reversed = False
            self._rows.sort(key=lambda r: safe_lower(r[sort_key]),
                            reverse=sort_is_reversed)
        self._sortData = (sort_key, sort_is_reversed)
        if self._tree:
            self._tree.invalidate()


class KoCodeIntelCatalogAdder(threading.Thread):
    """Add the given .cix paths to the catalogs zone."""
    _com_interfaces_ = [#components.interfaces.koICodeIntelCatalogAdder,
                        components.interfaces.koIShowsProgress]
    _reg_clsid_ = "{C6935748-1C42-4EB7-83CD-DC450A6650CD}"
    _reg_contractid_ = "@activestate.com/koCodeIntelCatalogAdder;1"
    _reg_desc_ = "Komodo CodeIntel Database API Catalog Adder"

    controller = None
    cancelling = False

    def __init__(self, cix_paths, on_complete=None):
        """
            'on_complete' (optional) is callback called as follows:
                on_complete(<added-cix-paths>). Note that the added
                paths are not the same as the given 'cix_paths' -- the
                files are copyied to an internal location as part of the
                import.
        """
        threading.Thread.__init__(self, name="CodeIntel Catalog Adder")
        self.cix_paths = cix_paths
        self.on_complete = on_complete

    def set_controller(self, controller):
        self.controller = getProxyForObject(None,
            components.interfaces.koIProgressController,
            controller, PROXY_ALWAYS | PROXY_SYNC)
        self.controller.set_progress_mode("undetermined")
        self.start()
    
    def cancel(self):
        self.cancelling = True

    def run(self):
        errmsg = None
        errtext = None
        try:
            koDirSvc = components.classes["@activestate.com/koDirs;1"].\
                       getService(components.interfaces.koIDirs)
            ciSvc = components.classes["@activestate.com/koCodeIntelService;1"].\
                       getService(components.interfaces.koICodeIntelService)
            mgr = UnwrapObject(ciSvc).mgr

            errors = []
            added_cix_paths = []
            for src_path in self.cix_paths:
                if self.cancelling:
                    break
                self.controller.set_stage("Loading '%s'..." % src_path)
                #TODO: use progress_cb to give progress feedback
                try:
                    # Copy to user apicatalogs dir.
                    user_apicatalogs_dir = join(koDirSvc.userDataDir,
                                                "apicatalogs")
                    if not exists(user_apicatalogs_dir):
                        os.makedirs(user_apicatalogs_dir)
                    #TODO: what about possibly overwriting existing file?
                    dst_path = join(user_apicatalogs_dir, basename(src_path))
                    shutil.copy(src_path, dst_path)

                    # Load it into CatalogsZone.
                    mgr.db.get_catalogs_zone().update(selections=[dst_path])

                    added_cix_paths.append(dst_path)
                except Exception, ex:
                    errors.append((
                        "error adding `%s' API catalog: %s" % (src_path, ex),
                        traceback.format_exc()
                    ))
            if errors:
                errmsg = '\n'.join(e[0] for e in errors)
                errtext = '\n---\n'.join(e[1] for e in errors)
            if self.on_complete:
                try:
                    self.on_complete(added_cix_paths)
                except Exception, ex:
                    log.warn("error in on_complete callback (ignoring): %s",
                             ex)
        finally:
            self.controller.done(errmsg, errtext)


class KoCodeIntelCatalogRemover(threading.Thread):
    """Remove the given .cix paths from the catalogs zone."""
    _com_interfaces_ = [components.interfaces.koIShowsProgress]
    _reg_clsid_ = "{90504450-1DC6-4216-B12A-47DB081DF137}"
    _reg_contractid_ = "@activestate.com/koCodeIntelCatalogRemover;1"
    _reg_desc_ = "Komodo CodeIntel Database API Catalog Remover"

    controller = None
    cancelling = False

    def __init__(self, cix_paths, on_complete=None):
        """
            'on_complete' (optional) is callback called as follows:
                on_complete(<added-cix-paths>).
        """
        threading.Thread.__init__(self, name="CodeIntel Catalog Remover")
        self.cix_paths = cix_paths
        self.on_complete = on_complete

    def set_controller(self, controller):
        self.controller = getProxyForObject(None,
            components.interfaces.koIProgressController,
            controller, PROXY_ALWAYS | PROXY_SYNC)
        self.controller.set_progress_mode("undetermined")
        self.start()
    
    def cancel(self):
        self.cancelling = True

    def run(self):
        errmsg = None
        errtext = None
        try:
            koDirSvc = components.classes["@activestate.com/koDirs;1"].\
                       getService(components.interfaces.koIDirs)
            norm_user_apicatalogs_dir \
                = normpath(normcase(join(koDirSvc.userDataDir, "apicatalogs")))

            ciSvc = components.classes["@activestate.com/koCodeIntelService;1"].\
                       getService(components.interfaces.koICodeIntelService)
            mgr = UnwrapObject(ciSvc).mgr

            errors = []
            removed_cix_paths = []
            for cix_path in self.cix_paths:
                if self.cancelling:
                    break
                self.controller.set_stage("Removing '%s'..." % cix_path)
                #TODO: use progress_cb to give progress feedback
                try:
                    # Assert that we are only removing files we should.
                    norm_cix_path = normpath(normcase(cix_path))
                    if dirname(norm_cix_path) != norm_user_apicatalogs_dir:
                        raise RuntimeError("aborting attempt to remove API "
                                           "catalog not under user data dir "
                                           "`%s'" % cix_path)
                    if exists(cix_path):
                        os.remove(cix_path)

                    # Update CatalogsZone accordingly
                    mgr.db.get_catalogs_zone().update(selections=[cix_path])
                    removed_cix_paths.append(cix_path)
                except Exception, ex:
                    errors.append((
                        "error removing `%s' API catalog: %s" % (cix_path, ex),
                        traceback.format_exc()
                    ))
            if errors:
                errmsg = '\n'.join(e[0] for e in errors)
                errtext = '\n---\n'.join(e[1] for e in errors)
            if self.on_complete:
                try:
                    self.on_complete(removed_cix_paths)
                except Exception, ex:
                    log.warn("error in on_complete callback (ignoring): %s",
                             ex)
        finally:
            self.controller.done(errmsg, errtext)


#--- internal support routines

def safe_lower(o):
    try:
        return o.lower()
    except AttributeError:
        return o

