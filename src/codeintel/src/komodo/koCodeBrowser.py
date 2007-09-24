#!python
# Copyright (c) 2004-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

"""Komodo Code Browser (the "Code" tab in the left side pane) tree view 
implementation using codeintel.
"""

import os
from os.path import basename
import threading
import logging
import re
from pprint import pprint, pformat
import weakref
from bisect import bisect_left
import operator

from xpcom import components, nsError, ServerException, COMException
from xpcom.server import UnwrapObject
from koTreeView import TreeView

from codeintel2.common import *



#---- globals

log = logging.getLogger("koCodeBrowser")
#log.setLevel(logging.DEBUG)



#---- Code Browser impl

class KoCodeBrowserTreeView(TreeView):
    _com_interfaces_ = [components.interfaces.koICodeBrowserTreeView,
                        components.interfaces.nsITreeView]
    _reg_clsid_ = "{E9E7E7EB-2DED-479B-AA1C-D8AF0E1347EA}"
    _reg_contractid_ = "@activestate.com/koCodeBrowserTreeView;1"
    _reg_desc_ = "Komodo Code Browser Tree View"

    _mgr = None

    def __init__(self):
        TreeView.__init__(self) # for debugging: , debug="cb")
        # The set of bufs to show in the tree. buf id: (<lang>, <path>).
        self.buf_from_id = weakref.WeakValueDictionary()

        self._ignoreNextToggleOpenState = False

        self._rows = None # flat list of visible rows
        # List of [<buf-id>, <start-row-idx>]. Only valid if _filter
        # is None.
        self._buf_row_starts = []
        self._num_top_nodes_open_by_default = 2
        self._is_open_from_scope = {}
        self._dataLock = threading.RLock()
        self._sortedBy = "name"
        self._filter = None
        self._filter_re = None

        # Data for controlling the display of node detail when the mouse is
        # hovering over that row's icon.
        self._showDetailForRow = -1  # -1 means don't show for any row
        atomSvc = components.classes["@mozilla.org/atom-service;1"].\
                  getService(components.interfaces.nsIAtomService)
        self._showDetailAtom = atomSvc.getAtom("showDetail")
        self._notMatchResultAtom = atomSvc.getAtom("notMatchResult")

    def activate(self, mgr, codeBrowserMgr):
        self._mgr = mgr
        self._codeBrowserMgr = codeBrowserMgr
        #XXX Call .refresh() here?

    is_open_pref_name = "codeintel_open_codebrowser_nodes"
    def restorePrefs(self):
        prefSvc = components.classes["@activestate.com/koPrefService;1"]\
                            .getService().prefs
        #TODO Put a timestamp into this datastruct and time out
        #     things after a week or so (to keep it small).
        #     A lighter (but not perfect) soln would be to just drop
        #     half the keys when they reach a certain limit.
        if prefSvc.hasStringPref(self.is_open_pref_name):
            pref_str = prefSvc.getStringPref(self.is_open_pref_name)
            try:
                pref_val = eval(pref_str)
            except SyntaxError, ex:
                log.debug("drop '%s' pref value: %s",
                          self.is_open_pref_name, ex)
            else:
                if pref_val and not isinstance(pref_val.keys()[0], tuple):
                    # This is the old format for this pref (strings
                    # as keys). Drop it.
                    pass
                else:
                    self._is_open_from_scope = pref_val

    def savePrefs(self):
        prefSvc = components.classes["@activestate.com/koPrefService;1"]\
                            .getService().prefs # global prefs
        prefSvc.setStringPref(self.is_open_pref_name,
                              repr(self._is_open_from_scope))

    # Mapping of which container nodes are open/closed.
    #   {<scope>: <is-open>, ...}
    # where <scope> is a full scope path tuple to the node in the
    # tree.
    def is_open_from_scope(self, scope):
        try:
            return self._is_open_from_scope[scope]
        except KeyError:
            return len(scope) <= self._num_top_nodes_open_by_default

    def update_buf(self, buf):
        buf = UnwrapObject(buf)
        buf_id = (buf.lang, buf.path)
        if buf_id not in self.buf_from_id:
            return # guard against .update_buf() after .remove_buf()

        log.debug("update_buf: %r", buf)
        if self._filter:
            self.refresh()
        else:
            self._dataLock.acquire()
            try:
                # Find the row index bounds for this buf.
                cache_idx = bisect_left(self._buf_row_starts, [buf_id, 0])
                start_idx = self._buf_row_starts[cache_idx][1]
                try:
                    end_idx = self._buf_row_starts[cache_idx+1][1]
                except IndexError:
                    end_idx = len(self._rows)
                log.debug("update_buf: buf row range in code browser: %d-%d",
                          start_idx, end_idx)

                # Generate the new rows and insert them.
                new_rows = list( self.rows_from_buf(buf) )
                #if log.isEnabledFor(logging.DEBUG):
                #    log.debug("update_buf: new rows:\n%s", pformat(new_rows))
                self._rows[start_idx:end_idx] = new_rows
                row_count_change = len(new_rows) - (end_idx-start_idx)

                # Update _buf_row_starts cache.
                if row_count_change:
                    for i in range(cache_idx+1, len(self._buf_row_starts)):
                        self._buf_row_starts[i][1] += row_count_change
                #self._buf_row_starts_sanity_check()

                # Invalidate the relevant sections of the tree.
                self._tree.beginUpdateBatch()
                if row_count_change:
                    self._tree.rowCountChanged(start_idx, row_count_change)
                self._tree.invalidateRange(start_idx, len(self._rows))
                self._tree.endUpdateBatch()
            finally:
                self._dataLock.release()

    def add_buf(self, buf):
        buf = UnwrapObject(buf)
        if buf is None:
            return # guard against buffer already having been closed

        log.debug("add_buf: %r", buf)
        self._dataLock.acquire()
        try:
            adding_first_file = len(self.buf_from_id) == 0
            self.buf_from_id[(buf.lang, buf.path)] = buf
            if adding_first_file:
                self._codeBrowserMgr.haveFilesInWS(True)

            if self._filter:
                self.refresh()
            else:
                # Find the row index bounds for this buf.
                buf_id = (buf.lang, buf.path)
                cache_idx = bisect_left(self._buf_row_starts, [buf_id, 0])
                try:
                    start_idx = self._buf_row_starts[cache_idx][1]
                except IndexError:
                    start_idx = len(self._rows)

                # Generate the new rows and insert them.
                new_rows = list( self.rows_from_buf(buf) )
                self._rows[start_idx:start_idx] = new_rows
                row_count_change = len(new_rows)

                # Update _buf_row_starts cache.
                self._buf_row_starts.insert(cache_idx, [buf_id, start_idx])
                for i in range(cache_idx+1, len(self._buf_row_starts)):
                    self._buf_row_starts[i][1] += row_count_change
                #self._buf_row_starts_sanity_check()

                # Invalidate the relevant sections of the tree.
                if self._tree:
                    self._tree.beginUpdateBatch()
                    self._tree.rowCountChanged(start_idx, row_count_change)
                    self._tree.invalidateRange(start_idx, len(self._rows))
                    self._tree.endUpdateBatch()
        finally:
            self._dataLock.release()

    def change_buf_lang(self, buf, path):
        # The way the 'switched_current_language' IDE event current
        # works in Komodo we don't know what the old language was.
        for existing_lang, existing_path in self.buf_from_id:
            if path == existing_path:
                self._remove_buf_id((existing_lang, existing_path))
                break
        if buf:
            buf = UnwrapObject(buf)
            if self._mgr.is_citadel_lang(buf.lang):
                self.add_buf(buf)

    def remove_buf(self, buf):
        buf = UnwrapObject(buf)
        buf_id = (buf.lang, buf.path)
        if buf_id in self.buf_from_id:
            log.debug("remove_buf: %r", buf)
            self._remove_buf_id(buf_id)

    def _remove_buf_id(self, buf_id):
        self._dataLock.acquire()
        try:
            try:
                del self.buf_from_id[buf_id]
            except KeyError:
                pass
            if not self.buf_from_id:
                self._codeBrowserMgr.haveFilesInWS(False)
            
            if self._filter:
                self.refresh()
            else:
                # Find the row index bounds for this buf.
                cache_idx = bisect_left(self._buf_row_starts, [buf_id, 0])
                assert self._buf_row_starts[cache_idx][0] == buf_id
                start_idx = self._buf_row_starts[cache_idx][1]
                try:
                    end_idx = self._buf_row_starts[cache_idx+1][1]
                except IndexError:
                    end_idx = len(self._rows)

                # Remove this buf's rows.
                del self._rows[start_idx:end_idx]
                row_count_change = end_idx - start_idx

                # Update _buf_row_starts cache.
                for i in range(cache_idx+1, len(self._buf_row_starts)):
                    self._buf_row_starts[i][1] -= row_count_change
                del self._buf_row_starts[cache_idx]
                #self._buf_row_starts_sanity_check()

                # Invalidate the relevant sections of the tree.
                if self._tree:
                    self._tree.beginUpdateBatch()
                    self._tree.rowCountChanged(start_idx, -row_count_change)
                    self._tree.invalidateRange(start_idx, len(self._rows))
                    self._tree.endUpdateBatch()
        finally:
            self._dataLock.release()

    def mouseOverNode(self, row, element):
        invalids = [] # rows that need redrawing
        if element == "image" and self._showDetailForRow != row:
            # The mouse is now over a new node's image: show details for
            # that node.
            invalids = [i for i in (self._showDetailForRow, row)
                        if i != -1]
            self._showDetailForRow = row
        elif (self._showDetailForRow != -1 and element != "image"
              and self._showDetailForRow != row):
            # The mouse is over a row for which we are not showing detail:
            # we should remove any special detail UI for other rows.
            invalids = [self._showDetailForRow]
            self._showDetailForRow = -1

        if invalids:
            self._tree.beginUpdateBatch()
            for invalid in invalids:
                column = self._tree.columns.getNamedColumn("codebrowser-tree-node")
                self._tree.invalidateCell(invalid, column)
            self._tree.endUpdateBatch()

    def refine_filter(self):
        """Refine the current filter results."""
        self._dataLock.acquire()
        try:
            old_row_count = len(self._rows)
            rows = list( self._filtered(self._rows) )
            self._rows = rows
        finally:
            self._dataLock.release()

        if self._tree:
            self._tree.beginUpdateBatch()
            if len(self._rows) != old_row_count:
                self._tree.rowCountChanged(0, len(self._rows)-old_row_count)
            self._tree.invalidate()
            self._tree.endUpdateBatch()

    def refresh(self):
        self._dataLock.acquire()
        try:
            old_row_count = self._rows and len(self._rows) or 0
            rows = []
            if self._filter:
                for buf_id, buf in sorted(self.buf_from_id.items()):
                    for row in self._filtered(self.rows_from_buf(buf)):
                        rows.append(row)
            else:
                self._buf_row_starts = [] # list of [<buf-id>, <start-row-idx>]
                for buf_id, buf in sorted(self.buf_from_id.items()):
                    self._buf_row_starts.append([buf_id, len(rows)])
                    rows += list( self.rows_from_buf(buf) )
            self._rows = rows
        finally:
            self._dataLock.release()

        if self._tree:
            self._tree.beginUpdateBatch()
            if len(self._rows) != old_row_count:
                self._tree.rowCountChanged(0, len(self._rows)-old_row_count)
            self._tree.invalidate()
            self._tree.endUpdateBatch()

    def rows_from_buf(self, buf):
        """Generate all the rows for this buffer."""
        scope = (buf.path,)
        base = basename(buf.path)
        level = 0
        log.debug("rows_from_buf: buf=%r, buf.blob_from_lang=%r",
                  buf, buf.blob_from_lang)
        have_blob_data = operator.truth(
            [b for b in buf.blob_from_lang.values() if len(b)])
        if not have_blob_data and buf.scan_error:
            # I.e. there was an error scanning the thing.
            detail = "error scanning '%s'" % base
            if buf.scan_error:
                detail += ": "+str(buf.scan_error)
            error_row = {"level": level,
                         "elem": None, 
                         "name": base,
                         "img": "error",
                         "detail": detail,
                         "artificial": True,
                         "is-container": False,
                         "buf": buf,
                         "scope": scope}
            yield error_row
        elif not have_blob_data and not buf.cb_show_if_empty:
            # If there is no blob data (i.e. no code) in this file, then
            # don't show anything in the Code Browser for it. This is
            # mainly to not have a bunch of single-row trees for things
            # like HTML files with *sometimes* have code but often not.
            pass
        else:
            if len(buf.blob_from_lang) > 1:
                # Put blob (aka module) nodes under a file node.
                file_row = {"level": level,
                            "elem": None, 
                            "name": base,
                            "img": buf.lang,
                            "detail": "%s (%s)" % (basename(buf.path),
                                                   dirname(buf.path)),
                            "is-container": True,
                            "buf": buf,
                            "scope": scope}
                if buf.scan_error:
                    file_row["img"] = "error"
                    file_row["detail"] = "error scanning '%s': %s"\
                                         % (base, buf.scan_error)
                yield file_row
                level += 1
            #XXX if yielded file_row and not self.is_open(scope) and not self._filter:
            #       don't continue
            for lang, blob in sorted(buf.blob_from_lang.items()):
                langintel = self._mgr.langintel_from_lang(lang)
                for row in self.rows_from_elem(blob, buf, langintel,
                                               level=level,
                                               parent_scope=scope):
                   yield row

    def _matches_filter(self, row):
        # Note: If this changes to anything more fancy that
        # string-contains comparison then revisit whether
        # refine_filter() optimization in .setFilter() is possible.
        if row.get("artificial"):
            # Artificial rows (i.e. those that don't represent
            # actual data, but are just there for grouping) should
            # never match.
            return False
        return self._filter_re.search(row["name"])

    def _filtered(self, gen):
        """Filter tree rows generated by 'gen' against the current
        match filter.
        """
        on_deck = {}
        for row in gen:
            level = row["level"]
            on_deck[level] = row
            if self._matches_filter(row):
                row["match"] = True
                for i in range(level+1):
                    if on_deck[i] is not None:
                        yield on_deck[i]
                        on_deck[i] = None
            else:
                row["match"] = False

    def rows_from_elem(self, elem, buf, langintel, level=0, parent_scope=()):
        """Generate the rows for this element and its children."""
        row = langintel.cb_data_from_elem_and_buf(elem, buf)
        ilk = elem.get("ilk")
        if ilk == "blob" and level == 1:
            # This is one of many blobs under a file row.
            row["name"] = "%s Code" % elem.get("lang")
            row["detail"] = "%s Code in '%s'" % (elem.get("lang"), buf.path)
        elif "name" not in row:
            row["name"] = repr(elem)
        if ilk == "blob" and elem.tag == "scope" and buf.scan_error:
            row["detail"] = "error scanning '%s': %s" \
                            % (basename(buf.path), buf.scan_error)
            row["img"] = "error"
        scope = parent_scope + (row["name"],)
        detail = row.get("detail", row["name"])
        row.update({"level": level,
                    "elem": elem,
                    "buf": buf,
                    "langintel": langintel,
                    "detail": detail,
                    #PERF: could cache child-rows as below
                    "scope": scope})
        yield row
        if self._filter or self.is_open_from_scope(scope):
            level += 1
            sort_key = self._get_row_and_data_sort_key()
            is_module_scope = len(scope) == 2

            # We extract the first generation for child row
            # generator so we can sort that level.
            group_global_vars = is_module_scope \
                                and langintel.cb_group_global_vars
            import_row_genners = []
            global_var_row_genners = []
            instance_var_row_genners = []
            symbol_row_genners = []
            for child in elem:
                if child.tag == "import":
                    import_row_genners.append(
                        self.rows_from_elem(child, buf, langintel,
                                            level+1, scope))
                elif group_global_vars and child.tag == "variable":
                    global_var_row_genners.append(
                        self.rows_from_elem(child, buf, langintel,
                                            level+1, scope))
                elif child.tag == "variable" \
                     and "__instancevar__" in child.get("attributes", ""):
                    instance_var_row_genners.append(
                        self.rows_from_elem(child, buf, langintel,
                                            level+1, scope))
                else:
                    symbol_row_genners.append(
                        self.rows_from_elem(child, buf, langintel,
                                            level, scope))

            if import_row_genners:
                child_rows = []
                imp_scope = scope + ("[imports]",)
                yield {"level": level,
                       "elem": None,
                       "name": langintel.cb_import_group_title,
                       "img": "import",
                       "buf": buf,
                       "langintel": langintel,
                       "child-rows": child_rows,
                       "artificial": True, # indicates this is a fakey row
                       "is-container": True,
                       "scope": imp_scope}
                imp_is_open = self.is_open_from_scope(imp_scope)
                # Even if closed we still need to calculate and
                # cache these rows because .toggleOpenState() below
                # depends on the "child-rows" being filled.
                children = [(g.next(), g) for g in import_row_genners]
                for row, genner in sorted(children, key=sort_key):
                    child_rows.append(row)
                    if imp_is_open:
                        yield row
                        for subrow in genner:
                            yield subrow

            if global_var_row_genners:
                child_rows = []
                globvar_scope = scope + ("[globalvars]",)
                yield {"level": level,
                       "elem": None,
                       "name": langintel.cb_globalvar_group_title,
                       "img": "variable",
                       "buf": buf,
                       "langintel": langintel,
                       "child-rows": child_rows,
                       "artificial": True, # indicates this is a fakey row
                       "is-container": True,
                       "scope": globvar_scope}
                globvar_is_open = self.is_open_from_scope(globvar_scope)
                # Even if closed we still need to calculate and
                # cache these rows because .toggleOpenState() below
                # depends on the "child-rows" being filled.
                children = [(g.next(), g) for g in global_var_row_genners]
                for row, genner in sorted(children, key=sort_key):
                    child_rows.append(row)
                    if globvar_is_open:
                        yield row
                        for subrow in genner:
                            yield subrow

            if instance_var_row_genners:
                child_rows = []
                instvar_scope = scope + ("[instancevars]",)
                yield {"level": level,
                       "elem": None,
                       "name": "Instance Variables",
                       "img": "instance-variable",
                       "buf": buf,
                       "langintel": langintel,
                       "child-rows": child_rows,
                       "artificial": True, # indicates this is a fakey row
                       "is-container": True,
                       "scope": instvar_scope}
                instvar_is_open = self.is_open_from_scope(instvar_scope)
                # Even if closed we still need to calculate and
                # cache these rows because .toggleOpenState() below
                # depends on the "child-rows" being filled.
                children = [(g.next(), g) for g in instance_var_row_genners]
                for row, genner in sorted(children, key=sort_key):
                    child_rows.append(row)
                    if instvar_is_open:
                        yield row
                        for subrow in genner:
                            yield subrow

            children = [(g.next(), g) for g in symbol_row_genners]
            for row, genner in sorted(children, key=sort_key):
                yield row
                for subrow in genner:
                    yield subrow

    def _get_row_and_data_sort_key(self):
        """Return a sort key generator for sorting a list of (row,
        data) tuples as appropriate for the current sort-type.
            sort(rows, key=FOO)
        """
        if self._sortedBy == "file-order":
            return lambda r_d: int(r_d[0]["elem"].get("line", 0))
        elif self._sortedBy == "name":
            return lambda r_d: r_d[0]["name"]
        else:
            raise ValueError("unknown sort order name: %r"
                             % self._sortedBy)

    def sortBy(self, key):
        self._dataLock.acquire()
        try:
            if self._sortedBy != key:
                self._sortedBy = key
                if not self._filter:
                    self.refresh()
        finally:
            self._dataLock.release()

    def setFilter(self, filter):
        self._dataLock.acquire()
        try:
            if self._filter != filter:
                try:
                    filter_re = re.compile(filter, re.I)
                except re.error, ex:
                    raise ServerException(nsError.NS_ERROR_FAILURE, str(ex))

                if self._filter and self._filter in filter \
                   and re.escape(filter) == filter:
                    # As long as our filtering is a simple string-contains
                    # check, then we need only refine the current hits.
                    self._filter = filter
                    self._filter_re = filter_re
                    self.refine_filter()
                else:
                    self._filter = filter
                    self._filter_re = filter_re
                    self.refresh()
        finally:
            self._dataLock.release()

    def _first_row_idx_for_buf(self, buf):
        buf_id = (buf.lang, buf.path)
        idx = bisect_left(self._buf_row_starts, [buf_id, 0])
        if self._buf_row_starts[idx][0] != buf_id:
            raise CodeIntelError("%s not found in Code Browser rows", buf)
        return self._buf_row_starts[idx][1]
    
    def locateScope(self, buf, pos):
        buf = UnwrapObject(buf)

        if self._filter:
            self._filter = None
            self.refresh()

        scoperef = buf.scoperef_from_pos(pos)
        if scoperef is None:
            # Just find the file node for this language.
            try:
                idx = self._first_row_idx_for_buf(buf)
            except CodeIntelError, ex:
                log.warn(str(ex))
                return False
            if self._tree:
                self._tree.view.selection.select(idx)
                self._tree.ensureRowIsVisible(idx)
            return True

        log.debug("locate-scope: %r", scoperef)
        blob, lpath = scoperef

        self._dataLock.acquire()
        try:
            # - Find first row for this buf.
            try:
                idx = self._first_row_idx_for_buf(buf)
            except CodeIntelError, ex:
                log.warn(str(ex))
                return False
            row = self._rows[idx]
            curr_level = row["level"]
            assert curr_level == 0

            # - Find the blob (aka module) row.
            if row["elem"] is None:
                # Looks like a file row for a multi-lang buf. Need
                # to find the blob (aka module) row.
                curr_level += 1
                if self.isContainer(idx) and not self.isContainerOpen(idx):
                    log.debug("open container row %d", idx)
                    self.toggleOpenState(idx)
                for idx in range(idx+1, len(self._rows)):
                    row = self._rows[idx]
                    if row["level"] < curr_level:
                        log.warn("couldn't find Code Browser row for "
                                 "%r scope in %r", blob, buf)
                    if row["elem"] is blob:
                        assert row["level"] == curr_level
                        break
                else:
                    log.warn("couldn't find Code Browser row for "
                             "%r scope in %r", blob, buf)
            log.debug("located blob row at idx %d: %r", idx, row)

            # - For each element in the scope stack work forward to the
            #   appropriate sub-row -- generating rows for closed nodes
            #   as necessary.
            if lpath and self.isContainer(idx) \
               and not self.isContainerOpen(idx):
                log.debug("open container row %d", idx)
                self.toggleOpenState(idx)
            while lpath:
                name = lpath.pop(0)
                curr_level += 1
                for idx in range(idx+1, len(self._rows)):
                    row = self._rows[idx]
                    if row["level"] < curr_level:
                        log.warn("couldn't find Code Browser row for "
                                 "%r scope in %r", name, buf)
                    if row["elem"] is not None \
                       and row["elem"].get("name") == name:
                        assert row["level"] == curr_level
                        break
                else:
                    log.warn("couldn't find Code Browser row for %r "
                             "scope in %r", name, buf)
                if lpath and self.isContainer(idx) \
                   and not self.isContainerOpen(idx):
                    log.debug("open container row %d", idx)
                    self.toggleOpenState(idx)
                log.debug("located '%s' row at idx %d: %r", name, idx, row)

            if self._tree:
                self._tree.view.selection.select(idx)
                # Scroll tree if necessary.
                # - If row 'idx' is already visible, then don't scroll.
                first_visible_idx = self._tree.getFirstVisibleRow()
                last_visible_idx = self._tree.getLastVisibleRow()
                if first_visible_idx <= idx <= last_visible_idx:
                    pass
                # - Otherwise, try to ensure parent row (if have one and is
                #   close) is visible too. "close" is defined as less than
                #   half of the num visible rows.
                else:
                    parent_idx = self.getParentIndex(idx)
                    if parent_idx == -1:
                        self._tree.ensureRowIsVisible(idx)
                    else:
                        page_len = self._tree.getPageLength()
                        if idx - parent_idx < page_len/2:
                            self._tree.ensureRowIsVisible(parent_idx)
                            self._tree.ensureRowIsVisible(idx)
                        else:
                            self._tree.ensureRowIsVisible(idx)
        finally:
            self._dataLock.release()

        return True

    def _buf_row_starts_sanity_check(self):
        #log.debug("checking self._buf_row_starts\n%s",
        #          pformat(self._buf_row_starts))
        assert len(self._buf_row_starts) == len(self.buf_from_id)
        for buf_id, row_start in self._buf_row_starts:
            row = self._rows[row_start]
            buf = row["buf"]
            assert (buf.lang, buf.path) == buf_id
            assert row["level"] == 0
            if row_start > 0:
                prev_row_buf = self._rows[row_start-1]["buf"]
                assert (prev_row_buf.lang, prev_row_buf.path) != buf_id
        log.debug("self._buf_row_starts is a-ok")


    #---- nsITreeView methods

    def get_rowCount(self):
        if self._rows is None:
            self.refresh()
        return len(self._rows)

    def getCellText(self, row_idx, col):
        assert col.id == "codebrowser-tree-node"
        row = self._rows[row_idx]
        if row_idx == self._showDetailForRow and "detail" in row:
            return row["detail"]
        else:
            return row["name"]
        return self._rows[row_idx]["name"]

    def getCellProperties(self, row_idx, col, properties):
        #assert col.id == "codebrowser-tree-node"
        if row_idx == self._showDetailForRow:
            properties.AppendElement(self._showDetailAtom)
        if self._filter and not self._rows[row_idx].get("match"):
            properties.AppendElement(self._notMatchResultAtom)

    def getLevel(self, row):
        return self._rows[row]["level"]

    def getParentIndex(self, row_idx):
        try:
            i = row_idx - 1
            self._dataLock.acquire()
            try:
                level = self._rows[row_idx]['level']
                while i > 0 and self._rows[i]['level'] >= level:
                    i -= 1
            finally:
                self._dataLock.release()
        except IndexError, ex:
            i = -1
        return i

    def hasNextSibling(self, row, after_row):
        curr_row_level = self._rows[row]["level"]
        for r in range(after_row+1, len(self._rows)):
            if curr_row_level > self._rows[r]["level"]:
                return False
            if curr_row_level == self._rows[r]["level"]:
                return True
        return False

    img_url_from_img_name = {
        "Python" : "chrome://komodo/skin/images/lang_python.png",
        "Perl": "chrome://komodo/skin/images/lang_perl.png",
        "PHP": "chrome://komodo/skin/images/lang_php.png",
        "Tcl": "chrome://komodo/skin/images/lang_tcl.png",
        "JavaScript": "chrome://komodo/content/icons/internet.png",
        "HTML": "chrome://komodo/content/icons/insert_url.png",
        "XML": "chrome://komodo/skin/images/lang_xml.png",
        "Ruby": "chrome://komodo/skin/images/lang_ruby.png",
        "function-private": "chrome://komodo/skin/images/cb_function_private.png",
        "function-protected": "chrome://komodo/skin/images/cb_function_protected.png",
        "function": "chrome://komodo/skin/images/cb_function.png",
        "interface-private": "chrome://komodo/skin/images/cb_interface_private.png",
        "interface-protected": "chrome://komodo/skin/images/cb_interface_protected.png",
        "interface": "chrome://komodo/skin/images/cb_interface.png",
        "namespace": "chrome://komodo/skin/images/cb_namespace.png",
        "class-private": "chrome://komodo/skin/images/cb_class_private.png",
        "class-protected": "chrome://komodo/skin/images/cb_class_protected.png",
        "class": "chrome://komodo/skin/images/cb_class.png",
        "instance-variable-private": "chrome://komodo/skin/images/cb_instance_variable_private.png",
        "instance-variable-protected": "chrome://komodo/skin/images/cb_instance_variable_protected.png",
        "instance-variable": "chrome://komodo/skin/images/cb_instance_variable.png",
        "variable-private": "chrome://komodo/skin/images/cb_variable_private.png",
        "variable-protected": "chrome://komodo/skin/images/cb_variable_protected.png",
        "variable": "chrome://komodo/skin/images/cb_variable.png",
        "argument-private": "chrome://komodo/skin/images/cb_argument_private.png",
        "argument-protected": "chrome://komodo/skin/images/cb_argument_protected.png",
        "argument": "chrome://komodo/skin/images/cb_argument.png",
        "import": "chrome://komodo/skin/images/cb_import.png",
        "scanning": "chrome://komodo/skin/images/cb_scanning.png",
        "error": "chrome://komodo/skin/images/cb_error.png",
        "container": "chrome://komodo/content/icons/open.png",
    }
    default_img_url = "chrome://komodo/skin/images/cb_variable.png"

    def getImageSrc(self, row, col):
        if col.id != "codebrowser-tree-node":
            return ""
        img_name = self._rows[row].get("img")
        img_url = self.img_url_from_img_name.get(
            img_name, self.default_img_url)
        return img_url

    def isContainer(self, row_idx):
        row = self._rows[row_idx]
        if row["elem"] is None:
            return row["is-container"]
        else:
            return len(row["elem"]) != 0

    def isContainerEmpty(self, row_idx):
        return False

    def isContainerOpen(self, row_idx):
        if self._filter:
            return True
        return self.is_open_from_scope(self._rows[row_idx]["scope"])

    def ignoreNextToggleOpenState(self):
        self._ignoreNextToggleOpenState = True

    def toggleOpenState(self, row_idx):
        if self._ignoreNextToggleOpenState:
            log.debug("ignoring this toggleOpenState(row_idx=%r)", row_idx)
            self._ignoreNextToggleOpenState = False
            return
        if self._filter:
            return

        self._dataLock.acquire()
        try:
            row = self._rows[row_idx]
            scope = row["scope"]
            is_open = self._is_open_from_scope[scope] \
                = not self.is_open_from_scope(scope)

            level = row["level"]
            if is_open:
                # Will be adding some rows.
                if "child-rows" in row: # get from cache
                    new_rows = [row] + row["child-rows"]
                else:
                    new_rows = list(self.rows_from_elem(
                        row["elem"], row["buf"], row["langintel"],
                        level=level, parent_scope=scope[:-1]))
                self._rows[row_idx:row_idx+1] = new_rows
                row_count_change = len(new_rows)-1

                # Update _buf_row_starts cache.
                buf = row["buf"]
                buf_id = (buf.lang, buf.path)
                idx = bisect_left(self._buf_row_starts, [buf_id, 0])
                for i in range(idx+1, len(self._buf_row_starts)):
                    self._buf_row_starts[i][1] += row_count_change

                self._tree.beginUpdateBatch()
                self._tree.rowCountChanged(row_idx+1, row_count_change)
                self._tree.invalidateRange(row_idx, len(self._rows))
                self._tree.endUpdateBatch()
                
            else:
                # Remove this guys' children.
                one_past_last_child_row = row_idx+1
                while one_past_last_child_row < len(self._rows) \
                      and self._rows[one_past_last_child_row]["level"] > level:
                    one_past_last_child_row += 1
                num_child_rows = one_past_last_child_row - row_idx - 1    

                old_row_count = len(self._rows)
                del self._rows[row_idx+1 : row_idx+num_child_rows+1]

                # Update _buf_row_starts cache.
                row_count_change = -num_child_rows
                buf = row["buf"]
                buf_id = (buf.lang, buf.path)
                idx = bisect_left(self._buf_row_starts, [buf_id, 0])
                for i in range(idx+1, len(self._buf_row_starts)):
                    self._buf_row_starts[i][1] += row_count_change

                self._tree.beginUpdateBatch()
                self._tree.rowCountChanged(row_idx+1, row_count_change)
                self._tree.invalidateRange(row_idx, old_row_count)
                self._tree.endUpdateBatch()

            self.selection.currentIndex = row_idx
            self.selection.select(row_idx)
            #self._buf_row_starts_sanity_check()
        finally:
            self._dataLock.release()

    #XXX handle canDropOn(), canDropBeforeAfter(), drop()
    #XXX What about the performAction[on{Row|Cell}]() methods?
    if True:
        # Turn this on to silence TreeView logging, if enabled,
        # for these specific methods.
        def isSorted(self):
            return 0
        def getRowProperties(self, row, properties):
            pass
        def getColumnProperties(self, column, properties):
            pass


    #---- current node accessor attributes
    def _getCurrentRow(self):
        idx = self._tree.view.selection.currentIndex
        if idx == -1 or idx >= len(self._rows):
            return None
        return self._rows[idx]

    def get_currentNodeFilePath(self):
        row = self._getCurrentRow()
        if row is None:
            return None
        else:
            return row["buf"].path

    def get_currentNodeLine(self):
        # Special case: if this is a module node and the line is 1,
        # then don't specify to jump to line 1, this might be
        # changing the current line if the module is already open. A
        # module line of 1 usually indicates that this is a language
        # where file===module, i.e. the line number is essentially
        # meaningless.
        row = self._getCurrentRow()
        if not row or row["elem"] is None:
            return 0
        elem = row["elem"]
        line = elem.get("line")
        if line is not None:
            return line
        if elem.get('ilk') == 'argument':
            # for arguments, jump to the line indicated by the parent function
            parent_idx = self.getParentIndex(self._tree.view.selection.currentIndex)
            parent_row = self._rows[parent_idx]
            if not parent_row or parent_row["elem"] is None:
                return 0
            return parent_row["elem"].get("line", 0)
        else:
            return 0

    def get_currentNodeLanguage(self):
        row = self._getCurrentRow()
        if row is None:
            return None
        else:
            return row["buf"].lang

    def get_currentNodeSymbolPattern(self):
        row = self._getCurrentRow()
        if row is None:
            return None
        elem = row["elem"]
        if elem.type == "import":
            if elem.symbol in ("*", "**"): # special signifiers
                symbol = None
            else:
                symbol = elem.symbol
        else:
            symbol = elem.name
        return symbol

    def get_currentNodeModulePattern(self):
        row = self._getCurrentRow()
        if row is None:
            return None
        elem = row["elem"]
        if elem.type == "import":
            return elem.module
        else:
            return None


