#!/usr/bin/env python
# Copyright (c) 2009 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

"""Backend for browser-like history support for an editor -- in particular,
for Komodo.

See KD 218 for details.

Dev Notes:
- Requires Python 2.6: for `with` statement, and `maxlen` argument to `deque`.
"""

import os
from os.path import exists, expanduser
import re
import sys
import shutil
import logging
from contextlib import contextmanager
import sqlite3
from collections import deque
from itertools import islice
from pprint import pprint, pformat
import time

import uriparse

try:
    from xpcom import components
    from xpcom.server import UnwrapObject
    _xpcom_ = True
except ImportError:
    _xpcom_ = False



#---- globals

log = logging.getLogger("editorhistory")
#log.setLevel(logging.DEBUG)



#---- errors

class HistoryError(Exception):
    pass

class HistoryNoLatestVisitError(HistoryError):
    """An error raised by `Database.visit_from_id(None)` indicating that
    there is no latest visit in the db.
    """

class HistoryDatabaseError(HistoryError):
    """An internal error in the history database."""



#---- main module classes

class Location(object):
    """Represents an editor location. These are, effectively, what is
    stored in the "history_visit" database table.
    """
    if _xpcom_:
        _com_interfaces_ = [components.interfaces.koIHistoryLocation]
        #TODO: drop these if not necessary
        #_reg_desc_ = "Editor History Location"
        #_reg_contractid_ = "@activestate.com/koHistoryLocation;1"
        #_reg_clsid_ = "{b9aa6fcc-52d6-4643-a8cf-e810755d9815}"
    
    def __init__(self, uri, line, col, view_type="editor",
                 id=None, uri_id=None, referer_id=None,
                 marker_handle=0, session_name="", window_num=0,
                 tabbed_view_id=0,
                 section_title=None, is_obsolete=False):
        """
        Core location fields:
        @param uri {str} #XXX:TODO: URI canonicalization.
        @param line {int} 1-based line of current pos
        @param col {int}  0-based column
        @param view_type {str} Editor/Komodo-specific fields.

        # Fields set by the database on insertion.
        @param id {int}
        @param uri_id {int}
        @param referer_id {int} - id of the Location before this one
        
        @param marker_handle {int} - scintilla marker handle for tracking lines
               -1 indicates no handle
        @param session {str} Komodo-specific session name.  Default is empty string
        @param window_num {int} Komodo-specific window num.  Default is "0"
        @param tabbed_view_id {int} - Komodo-specific tab group #
        @param section_title {str} - Komodo-specific session name, used to distinguish separate history threads.
        @param is_obsolete {bool} - Indicates the location no longer exists, and can't be recreated
        """

        self.uri = uri
        self.line = line
        self.col = col
        self.view_type = view_type
        self.id = id
        self.uri_id = uri_id
        self.referer_id = referer_id
        self.marker_handle = marker_handle
        self.session_name = session_name
        self.window_num = window_num
        self.tabbed_view_id = tabbed_view_id
        self.section_title = section_title
        self.is_obsolete = is_obsolete

    def clone(self):
        return Location(self.uri, self.line, self.col, view_type=self.view_type,
            session_name=self.session_name,
            window_num=self.window_num, tabbed_view_id=self.tabbed_view_id,
            section_title=self.section_title, is_obsolete=self.is_obsolete)

    def __repr__(self):
        extras = []
        if self.id is not None:
            extras.append("id=%s" % self.id)
        if self.referer_id is not None:
            extras.append("ref=%s" % self.referer_id)
        #extras.append("tabbed_view_id=%r" % self.tabbed_view_id)
        if self.view_type != "editor":
            extras.append(self.view_type)
        if self.marker_handle:
            extras.append("mh=%d" % self.marker_handle)
        if self.section_title:
            extras.append("section_title=%s" % self.section_title)
        if self.is_obsolete:
            extras.append("obsolete!")
        extra = extras and (" (%s)" % ", ".join(extras)) or ""
        return "<Location %s#%s,%s%s>" % (
            self.uri, self.line, self.col, extra)

    def __eq__(self, other):
        if not isinstance(other, Location):
            return False
        elif self.uri != other.uri:
            return False
        elif self.line != other.line:
            return False
        elif self.col != other.col:
            return False
        return True
    def __ne__(self, other):
        return not self.__eq__(other)


class Database(object):
    """Wrapper API for the sqlite database of the history."""
    # Database version.
    # VERSION is the version of this Database code. The property
    # "version" is the version of the database on disk. The patch-level
    # version number should be used for small upgrades to the database.
    #
    # How to update version:
    # (a) change VERSION,
    # (b) add a change log comment here, and
    # (c) add an entry to `_upgrade_info_from_curr_ver`.
    #
    # db change log:
    # - 1.0.0: initial version
    # - 1.0.1: change in history_visit: window_name TEXT => window_num INT DEF 0
    # - 1.0.2: name change in history_visit: s/multiview_id/tabbed_view_id/
    # - 1.0.3: add `is_obsolete` columns
    # - 1.0.4: history is now per-session, database should be reset
    # - 1.0.5: s/section/section_title/ in the database
    VERSION = "1.0.5"

    path = None
    
    LOC_MARKER_UPDATE_LIMIT = 100
    
    URIS_TO_KEEP = 500

    def __init__(self, path):
        self.path = path
        
        # Performance note: This cache can dramatically speed up
        # `uri_id_from_uri`, but only if N is greater than the typical
        # working set of URIs for which it is being called. The working set
        # should, I believe, correspond to the number of files the Komodo
        # user is jumping around in.
        # See `perf.py::perf_uris()`. 
        self._uri_id_from_uri_cache = _RecentsDict(10)
        
        if not exists(self.path):
            update_version = True
            self.create()
        else:
            update_version = False
            try:
                self.upgrade()
            except Exception, ex:
                log.exception("error upgrading `%s': %s", self.path, ex)
                self.reset(backup=False)
        try:
            self._read_db_from_disk()
        except sqlite3.DatabaseError:
            # Bug 101551: recover from a corrupted database
            try:
                self.reset(backup=False)
                self._read_db_from_disk()
            except:
                log.error("History is broken: please delete <profile>/history.sqlite and restart")
                return
        if update_version:
            self.set_meta("version", self.VERSION)

    def __repr__(self):
        return "<Database %s>" % self.path

    @contextmanager
    def connect(self, commit=False, inMemory=True, cu=None):
        """A context manager for a database connection/cursor. It will automatically
        close the connection and cursor.

        Usage:
            with self.connect() as cu:
                # Use `cu` (a database cursor) ...

        @param commit {bool} Whether to explicitly commit before closing.
            Default false. Often SQLite's autocommit mode will
            automatically commit for you. However, not always. One case
            where it doesn't is with a SELECT after a data modification
            language (DML) statement (i.e.  INSERT/UPDATE/DELETE/REPLACE).
            The SELECT won't see the modifications. If you will be
            making modifications, probably safer to use `self.connect(True)`.
            See "Controlling Transations" in Python's sqlite3 docs for
            details.
        @param inMemory {bool} Whether to use an in-memory database, or
            a disk-based database.
        @param cu {sqlite3.Cursor} An existing cursor to use. This allows
            callers to avoid the overhead of another db connection when
            already have one, while keeping the same "with"-statement
            call structure.
        """
        if cu is not None:
            yield cu
        elif inMemory:
            cu = self.dbmem_cx.cursor()
            try:
                yield cu
            finally:
                if commit:
                    self.dbmem_cx.commit()
        else:
            cx = sqlite3.connect(self.path)
            cu = cx.cursor()
            try:
                yield cu
            finally:
                if commit:
                    cx.commit()
                cu.close()
                cx.close()

    def create(self):
        """Create the database file."""
        #TODO: error handling?
        with self.connect(commit=True, inMemory=False) as cu:
            cu.executescript(_g_database_schema)
            self.set_meta("version", self.VERSION, cu=cu)

    def reset(self, backup=True):
        """Remove the current database (possibly backing it up) and create
        a new empty one.

        @param backup {bool} Should the original database be backed up.
            If so, the backup is $database_file+".bak". Default true.
        """
        if backup:
            backup_path = self.path + ".bak"
            if exists(backup_path):
                _rm_file(backup_path)
            if exists(backup_path): # couldn't remove it
                log.warn("couldn't remove old '%s' (skipping backup)",
                         backup_path)
                _rm_file(self.path)
            else:
                os.rename(self.path, backup_path)
        else:
            _rm_file(self.path)
        self.create()

    def upgrade(self):
        """Upgrade the current database."""
        # 'version' is the DB ver on disk, 'VERSION' is the target ver.
        curr_ver = self.version
        while curr_ver != self.VERSION:
            try:
                result_ver, upgrader, upgrader_arg \
                    = self._upgrade_info_from_curr_ver[curr_ver]
            except KeyError:
                raise HistoryDatabaseError(
                    "cannot upgrade from db v%s: no upgrader for this version"
                    % curr_ver)
            log.info("upgrading from db v%s to db v%s ...",
                     curr_ver, result_ver)
            if upgrader_arg is not None:
                upgrader(self, curr_ver, result_ver, upgrader_arg)
            else:
                upgrader(self, curr_ver, result_ver)
            curr_ver = result_ver

    def _upgrade_reset_db(self, curr_ver, result_ver):
        """Upgrader that just starts over."""
        assert result_ver == self.VERSION
        self.reset()

    _upgrade_info_from_curr_ver = {
        # <current version>: (<resultant version>, <upgrader method>, <upgrader args>)
        "1.0.0": (VERSION, _upgrade_reset_db, None),
        "1.0.1": (VERSION, _upgrade_reset_db, None),
        "1.0.2": (VERSION, _upgrade_reset_db, None),
        "1.0.3": (VERSION, _upgrade_reset_db, None),
        "1.0.4": (VERSION, _upgrade_reset_db, None),
    }

    @property
    def version(self):
        """Return the version of the db on disk (or None if cannot
        determine).
        """
        #TODO: error handling?
        ver = self.get_meta("version")
        if ver is None:
            ver = self.get_meta("version", inMemory=False)
        return ver

    def uri_id_from_uri(self, uri, create_if_new=True, cu=None):
        """Get a `uri_id` for the given URI, possibly inserting a new row
        in the `history_uri` table if new.
        
        @param uri {str} The URI for which to get an id
        @param create_if_new {bool} Whether to create an entry for this URI
            if is doesn't exist. Default is True. Note: If true this will
            revive obsoleted URIs.
        @param cu {sqlite3.Cursor} An existing db cursor to use. Optional.
        @returns {int} An ID for this URI, or None if didn't exist and
            `create_if_new=False`.
        """
        cache = self._uri_id_from_uri_cache
        if uri in cache and cache[uri]:
            return cache[uri]
        
        uri_id = None
        with self.connect(commit=True, cu=cu) as cu:
            cu.execute("SELECT id, is_obsolete FROM history_uri WHERE uri=?", (uri,))
            row = cu.fetchone()
            if row:
                uri_id = int(row[0])
                is_obsolete = bool(row[1])
            else:
                uri_id = is_obsolete = None
            
            if is_obsolete is False:
                pass
            elif create_if_new:
                if is_obsolete:
                    cu.execute("UPDATE history_uri SET is_obsolete=? WHERE id=?",
                               (False, uri_id))
                else:
                    cu.execute("INSERT INTO history_uri(uri) VALUES (?)", (uri,))
                    uri_id = cu.lastrowid
                cu.connection.commit()
            else:
                uri_id = None
        
        if uri_id:
            cache[uri] = uri_id
        return uri_id

    def obsolete_uri(self, uri, uri_id, cu=None):
        """Mark this URI and all its visits as obsolete.
        
        @param uri {str} The URI to mark obsolete.
        @param uri_id {int} The ID for this URI in the database.
        @param cu {sqlite3.Cursor} An existing cursor to use.
        """
        if uri in self._uri_id_from_uri_cache:
            del self._uri_id_from_uri_cache[uri]
        with self.connect(commit=True, cu=cu) as cu:
            cu.execute("UPDATE history_visit SET is_obsolete=? WHERE uri_id=?",
                       (True, uri_id))
            cu.execute("UPDATE history_uri SET is_obsolete=? WHERE id=?",
                       (True, uri_id))

    def add_loc(self, loc, referer_id=None, cu=None):
        """Add a location to the visits table of the db.
        
        @param loc {Location} The location to add.
        @param referer_id {int} The id of the preceding visit (i.e. the
            location to which to jump back.
        @param cu {sqlite3.Cursor} An existing cursor to use.
        @returns {Location} The updated `loc` (see Side-effects below).
        
        **Side-effects:** The following fields on `loc` are set:
            `id`            The db id for this visit.
            `referer_id`    The given referer_id.
            `uri_id`        The id for `loc.uri` in the `history_uri` table.
        As well, the `visit_count` of the URI in the `history_uri` table is
        incremented.
        """
        assert loc.id is None, "adding existing loc: %r" % loc
        with self.connect(commit=True, cu=cu) as cu:
            uri_id = self.uri_id_from_uri(loc.uri, cu=cu)
            cu.execute("""
                INSERT INTO history_visit(referer_id, uri_id, line, col, view_type,
                    session_name, marker_handle, section_title,
                    window_num, tabbed_view_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, 
                (referer_id, uri_id, loc.line, loc.col, loc.view_type,
                 loc.session_name, loc.marker_handle, loc.section_title,
                 loc.window_num, loc.tabbed_view_id))
            loc.id = cu.lastrowid
            loc.referer_id = referer_id
            loc.uri_id = uri_id
        return loc
                            
    def update_referer_id(self, loc, referer_id, cu=None):
        """Update the referer_id for the given location.
        
        @param loc {Location} The location to update.
        @param referer_id {int} The new referer_id.
        @param cu {sqlite3.Cursor} An existing cursor to use.
        """
        assert loc.referer_id != referer_id
        with self.connect(commit=True, cu=cu) as cu:
            loc.referer_id = referer_id
            cu.execute("UPDATE history_visit SET referer_id=? WHERE id=?",
                       (referer_id, loc.id))

    def uri_from_id(self, id, cu=None):
        with self.connect(cu=cu) as cu:
            cu.execute("SELECT uri FROM history_uri WHERE id=?", (id,))
            row = cu.fetchone()
            if row is None:
                raise HistoryError("cannot get uri %r: id does not exist" % id)
            return row[0]

    def visit_from_id(self, id, session_name="", cu=None):
        """Load the given visit from `history_visit` table.
        
        @param id {int} The id of the visit to load. If None, the *latest*
            visit is returned.
        @param session_name {str} Optional. The session on which to look for
            the latest visit if `id is None`.
        @param cu {sqlite3.Cursor} An existing cursor to use.
        @returns {Location} A location instance.
        @raises `HistoryError` if no such location exists.
        """
        with self.connect(commit=True, cu=cu) as cu:
            if id is None:
                cu.execute("""
                    SELECT id, datetime(timestamp) FROM history_visit
                    WHERE session_name = ?
                    ORDER BY timestamp DESC LIMIT 1;
                    """,
                    (session_name, ))
                row = cu.fetchone()
                if row is None:
                    raise HistoryNoLatestVisitError(
                        "cannot get latest visit: there are no visits in the db")
                id = int(row[0])
            cu.execute("""
                SELECT referer_id, uri_id, line, col, view_type, content,
                       session_name, marker_handle, window_num,
                       tabbed_view_id, section_title, is_obsolete
                FROM history_visit
                WHERE id=?
                """, (id,))
            row = cu.fetchone()
            if row is None:
                raise HistoryError("cannot get visit %r: id does not exist" % id)
            
            try:
                uri_id = int(row[1])
                uri = self.uri_from_id(uri_id, cu=cu)
                loc = Location(
                    uri=uri,
                    line=int(row[2]),
                    col=int(row[3]),
                    view_type=row[4],
                    id=id,
                    uri_id=uri_id,
                    referer_id=_int_or_none(row[0]),
                    session_name=row[6],
                    marker_handle=row[7],
                    window_num=row[8],
                    tabbed_view_id=row[9],
                    section_title=row[10],
                    is_obsolete=row[11]
                )
            except TypeError:
                # Bug 93488 -- a corrupted/invalid history database can
                # prevent Komodo from opening new tabs.  So delete it.
                log.exception("Internal error: found invalid data in the history database, deleting...")
                try:
                    num_nulls = cu.execute('select count(*) from history_visit WHERE uri_id is null').fetchone()[0]
                    if num_nulls > 0:
                        cu.execute("DELETE FROM history_visit WHERE uri_id is null")
                    else:
                        log.error("Corrupted history.sqlite: invalid record but with non-null uri_id")
                except:
                    log.exception("Error trying to delete null uri_id entries")
                raise HistoryError("cannot finish getting info on visit %r" % id)
        return loc
            
    def update_marker_handles_on_close(self, uri, scimoz, forward_visits, back_visits):
        if not uri:
            log.info("Can't update markers on a null URI (untitled)")
            return
        new_rows = []
        with self.connect(commit=True) as cu:
            uri_id = self.uri_id_from_uri(uri, cu=cu)
            #XXX Test perf on this.  Speed diff by dropping marker_handle test?
            cu.execute("SELECT id, line, marker_handle"
                       + " FROM history_visit"
                       + " WHERE uri_id=? and marker_handle != -1"
                       + " ORDER BY timestamp DESC LIMIT ?",
                       (uri_id, self.LOC_MARKER_UPDATE_LIMIT))
            for id, line, marker_handle in cu:
                new_line = scimoz.markerLineFromHandle(marker_handle)
                if new_line != -1 and new_line != line:
                    new_rows.append([id, new_line])
            local_locs_by_id = {}
            # The same uri_id can appear multiple times in both caches,
            # so find them for quick access
            for loc in forward_visits:
                if loc.uri_id == uri_id:
                    local_locs_by_id[loc.id] = loc
            for loc in back_visits:
                if loc.uri_id == uri_id:
                    local_locs_by_id[loc.id] = loc
            
            for id, line in new_rows:
                cu.execute("UPDATE history_visit SET line=? WHERE id=?",
                           (line, id))
                if id in local_locs_by_id:
                    local_locs_by_id[id].line = line
                    
            # Finally set all the recent marker_handles on this URI to -1,
            # in the database and in the caches
            # TODO PERF - Check timestamp > julianday() - 1
            cu.execute("UPDATE history_visit SET marker_handle=?"
                       " WHERE uri_id=? and marker_handle != -1",
                       (-1, uri_id))
            for loc in local_locs_by_id.values():
                loc.marker_handle = -1
    
    def get_meta(self, key, default=None, inMemory=None, cu=None):
        """Get a value from the meta table.
        
        @param key {str} The meta key.
        @param default {str} Default value if the key is not found in the db.
        @param inMemory {str} Whether to use the in-memory or the disk-based database.
        @param cu {sqlite3.Cursor} An existing cursor to use.
        @returns {str} The value in the database for this key, or `default`.
        """
        if cu is None and inMemory is None:
            inMemory = hasattr(self, 'dbmem_cx')
            # cu has priority over inMemory
        with self.connect(inMemory=inMemory, cu=cu) as cu:
            cu.execute("SELECT value FROM history_meta WHERE key=?", (key,))
            row = cu.fetchone()
            if row is None:
                return default
            return row[0]
    
    def set_meta(self, key, value, cu=None):
        """Set a value into the meta table.
        
        @param key {str} The meta key.
        @param value {str} The value to associate with the key.
        @param cu {sqlite3.Cursor} An existing cursor to use.
        @returns {None}
        """
        with self.connect(commit=True, cu=cu) as cu:
            cu.execute("INSERT INTO history_meta(key, value) VALUES (?, ?)", 
                (key, value))

    def get_num_visits(self, uri, default=None, inMemory=None, cu=None):
        """Get a visit_count from the history_uri table.

        @param uri {str} The uri.
        @param default {str} Default value if the key is not found in the db.
        @param inMemory {str} Whether to use the in-memory or the disk-based database.
        @param cu {sqlite3.Cursor} An existing cursor to use.
        @returns {int} The value in the database for visit_count `default`.
        """
        if cu is None and inMemory is None:
            inMemory = hasattr(self, 'dbmem_cx')
            # cu has priority over inMemory
        with self.connect(inMemory=inMemory, cu=cu) as cu:
            cu.execute("SELECT visit_count FROM history_uri WHERE uri=?", (uri,))
            row = cu.fetchone()
            if row is None:
                return default
            return row[0]

    def close(self):
        self.dbmem_cx.commit()
        self._write_db_to_disk()
        self.dbmem_cu.close()
        self.dbmem_cx.close()

    def del_meta(self, key):
        """Delete a key/value pair from the meta table.
        
        @param key {str} The meta key.
        """
        with self.connect(commit=True) as cu:
            cu.execute("DELETE FROM history_meta WHERE key=?", (key,))


    def _read_db_from_disk(self):
        self.dbmem_cx = sqlite3.connect(":memory:")
        self.dbmem_cu = self.dbmem_cx.cursor()
        self.dbmem_cu.executescript(_g_database_schema)
        # Manually copy the on-disk db into the memory one in order
        # to preserve all the triggers, indices, etc.
        tables = re.compile(r'CREATE \s+ TABLE \s+ (.*?) \s* \(',
                            re.I|re.X).findall(_g_database_schema)
        with self.connect(inMemory=False) as cu:
            for table in tables:
                placeholders = None
                cu.execute('select * from %s' % (table,))
                for row in cu:
                    if placeholders is None:
                        placeholders = ",  ".join(list("?" * len(row)))
                    self.dbmem_cu.execute('INSERT into %s VALUES (%s)' % (table, placeholders),
                                          (list(row)))
        self.dbmem_cx.commit()
        
    def _write_db_to_disk(self):
        self._backup_database()
        
        # First remove soon-to-be obsolete URIs
        with self.connect(commit=True) as cu:
            dbmem_cu = self.dbmem_cu.execute('select count(*) from history_visit')
            if dbmem_cu.fetchone()[0] <= self.URIS_TO_KEEP:
                limiting_id = None
            else:
                dbmem_cu = self.dbmem_cu.execute('select id from history_visit order by id desc limit 1 offset %d' %
                                                 (self.URIS_TO_KEEP,))
                limiting_id = dbmem_cu.fetchone()[0]
                
                # Determine which URIs are in the last set but aren't
                # in the first set, and remove them from history_uri
                cu.execute("SELECT distinct uri_id FROM history_visit WHERE id > ?", (limiting_id,))
                recent_uris = [x[0] for x in cu.fetchall()]
                cu.execute("SELECT distinct uri_id FROM history_visit WHERE id <= ?", (limiting_id,))
                older_uris = [x[0] for x in cu.fetchall()]
                uris_to_drop = set(older_uris).difference(recent_uris)
                if uris_to_drop:
                    cmp_stmts = ["id = %d" % uri_id for uri_id in uris_to_drop]
                    cu.execute("DELETE from history_uri where " + " OR ".join(cmp_stmts))
               
        tables = re.compile(r'CREATE \s+ TABLE \s+ (.*?) \s* \(',
                            re.I|re.X).findall(_g_database_schema)     
        with self.connect(commit=True, inMemory=False) as cu:
            for table in tables:
                cu.execute("delete from %s" % (table,))
                if table == "history_visit" and limiting_id: continue
                dbmem_cu = self.dbmem_cu.execute('select * from %s' % (table,))
                placeholders = None
                for row in dbmem_cu.fetchall():
                    if placeholders is None:
                        placeholders = ",  ".join(list("?" * len(row)))
                    cu.execute('INSERT into %s VALUES (%s)' % (table, placeholders),
                               (list(row)))
            if limiting_id:
                dbmem_cu = self.dbmem_cu.execute('select * from history_visit where id > ?', (limiting_id,))
                placeholders = None
                for row in dbmem_cu.fetchall():
                    if placeholders is None:
                        placeholders = ",  ".join(list("?" * len(row)))
                    cu.execute('INSERT into %s VALUES (%s)' % (table, placeholders),
                               (list(row)))
            
                
    def _backup_database(self):
        backup_path = self.path + ".bak"
        shutil.copyfile(self.path, backup_path)
                
class HistorySession(object):
    """History handling for a single session (as identified by a
    `session_name`).
    """
    RECENT_BACK_VISITS_LENGTH = 10
    # This cache length limits the max allowable value of 'n' for
    # `go_back(..., n)`, so let's make it reasonably large.
    RECENT_BACK_VISITS_CACHE_LENGTH = 10 * RECENT_BACK_VISITS_LENGTH
    RECENT_BACK_VISITS_DEPLETION_LENGTH = RECENT_BACK_VISITS_LENGTH + 2
    
    def __init__(self, session_name, db):
        self.session_name = session_name
        self.db = db
    
        # Recent history: We cache the last few "back" visits and all forward
        # visits -- those resulting from the user jumping back in the history
        # one or more times. For both deques, newest item is at deque[0], oldest
        # at deque[-1].
        #   recent_back_visits: most recent first. We cache more than
        #       "recent" length to try to limit the need to hit the database
        #       when the user goes back and forth a lot.
        #       The location for the next "go_back" is at the start.
        #   forward_visits: furthest forward first:
        #       The location for the next "go_forward" is at the end.
        self.recent_back_visits = None
        self.forward_visits = None
        
        # The last visit returned by `go_back` or `go_forward`.
        self._last_visit = None
        self.load()
        self.closed = False

    def close(self):
        if self.closed:
            return
        self.save()
        self.closed = True

    def _ns_meta_key(self, key):
        """Add a namespace prefix, as appropriate, for the given key for the
        'history_meta' table.
        """
        if self.session_name:
            return "%s:%s" % (self.session_name, key)
        else:
            return key
        
    def load(self, cu=None):
        """Load recent history from the database."""
        with self.db.connect(commit=True, cu=cu) as cu:
            # `num_forward_visits` and `top_loc_id` in the meta table help
            # us reconstruct the back/forward state. `num_forward_visits == -1`
            # indicates that these weren't saved (e.g. if Komodo crashed). In
            # this case we do the best we can by using the *latest* visit as
            # the top of the stack and presuming `num_forward_visits == 0`.
            ns_num_forward_visits = self._ns_meta_key("num_forward_visits")
            num_forward_visits = int(self.db.get_meta(ns_num_forward_visits, -1, cu=cu))
            if num_forward_visits == -1:
                top_loc_id = None
            else:
                # Set to `-1` so we'll be able to tell on next start
                # if it was set.
                self.db.set_meta(ns_num_forward_visits, -1, cu=cu)
                top_loc_id = _int_or_none(self.db.get_meta(
                    self._ns_meta_key("top_loc_id"), cu=cu))

            self._load_recent_history_cache(top_loc_id, num_forward_visits, cu=cu)

    def _load_recent_history_cache(self, top_loc_id, num_forward_visits, cu=None):
        """Reload the recent history cache.
        
        @param top_loc_id {int} Is the ID at the top of the history.
        @param num_forward_visits {int} Is the number of visits for
            `self.forward_visits`. `-1` indicates that we don't know (see
            example in `load()`).
        """
        self.recent_back_visits = deque(maxlen=self.RECENT_BACK_VISITS_CACHE_LENGTH)
        self.forward_visits = deque()
        self._last_visit = None
        
        num_to_load = 2 * self.RECENT_BACK_VISITS_LENGTH + 1
        if num_forward_visits != -1:
            num_to_load += num_forward_visits
        
        SENTINEL = 1000   # sanity check for huge block of obsoleted locs
        id = top_loc_id
        i = 0
        last_good_loc = None
        while i < num_to_load:
            try:
                loc = self.db.visit_from_id(id, session_name=self.session_name, cu=cu)
            except HistoryNoLatestVisitError, ex:
                break
            except HistoryError, ex:
                # This loc was most likely deleted via expiry, so all earlier
                # locs were deleted too.  We can break here.
                # No need to worry about overflow -- the largest
                # sqlite3 integer value is 9,223,372,036,854,775,807
                # At one history event/second, that's good for
                # about 2.9E14 years of uninterrupted Komodo editing.
                SENTINEL -= 1
                i += 1
                break
            if not loc.is_obsolete:
                SENTINEL = 1000  # reset
                if last_good_loc:
                    # Fix up referer_id in case there were obsolete locs
                    # between this and the last good one.
                    last_good_loc.referer_id = loc.id
                if i < num_forward_visits:
                    self.forward_visits.append(loc)
                elif i == num_forward_visits:
                    self._last_visit = loc
                else:
                    self.recent_back_visits.append(loc)
                last_good_loc = loc
                i += 1
            else:
                SENTINEL -= 1
            id = loc.referer_id
            if id is None or SENTINEL <= 0:
                break
        if last_good_loc:
            last_good_loc.referer_id = None

    def _replenish_recent_back_visits(self):
        """Replenish `self.recent_back_visits` back up to its full
        cache size.
        """
        assert self.recent_back_visits
        num_to_load = (self.RECENT_BACK_VISITS_CACHE_LENGTH
            - len(self.recent_back_visits))
        last_good_loc = self.recent_back_visits[-1]
        id = self.recent_back_visits[-1].referer_id
        SENTINEL = 1000   # sanity check for huge block of obsoleted locs
        with self.db.connect() as cu:
            i = 0
            while i < num_to_load:
                if id is None or SENTINEL <= 0:
                    last_good_loc.referer_id = None
                    break
                loc = self.db.visit_from_id(id, cu=cu)
                if not loc.is_obsolete:
                    SENTINEL = 1000 # reset
                    # Fix up referer_id in case there were obsolete locs
                    # between this and the last good one.
                    last_good_loc.referer_id = loc.id
                    self.recent_back_visits.append(loc)
                    i += 1
                else:
                    SENTINEL -= 1
                id = loc.referer_id

    def save(self):
        """Save some recent history meta-data.
        
        Most history information (namely the "visit" entries in the visit
        and uri tables) is saved on the fly. However, some meta data is not,
        to save unnecessary writing to the db. We save that meta data here
        to restore the back/forward state for the next session.
        """
        with self.db.connect(True) as cu:
            self.db.set_meta(self._ns_meta_key("num_forward_visits"),
                str(len(self.forward_visits)), cu=cu)
            # The ID for the "top" location in the back/forward stack.
            if self.forward_visits:
                top_loc_id = self.forward_visits[0].id
            elif self.recent_back_visits:
                top_loc_id = self.recent_back_visits[0].id
            else:
                top_loc_id = None
            self.db.set_meta(self._ns_meta_key("top_loc_id"),
                top_loc_id, cu=cu)
            
    def note_loc(self, loc):
        """Note the given location (i.e. make it part of the history).

        @param loc {Location} The location to note.
        @returns {Location} The noted location. Primarily this is as a
            convenience for testing. However `loc` will have been modified
            in place as a side-effect of being added to the db.
        """
        #TODO: This needs to a be a no-op if the location to note is
        #      the exact same location as we just jumped to. Example:
        #      - Komodo's doFileOpen will include the ko.history.note_loc()
        #        code (esp. when handling doFileOpenAtLine)
        #      - When doing "Back" or "Forward" and the target file isn't
        #        open, this will result in doFileOpen being called; and hence
        #        a call to note_loc() that we don't want to have effect.
        #      XXX Is my logic correct here?
        #      TODO: get the notes worked through with Eric.
        if _xpcom_:
            loc = UnwrapObject(loc)
        #log.debug("note loc: %r", loc)
        referer_id = (self.recent_back_visits
            and self.recent_back_visits[0].id or None)
        self.db.add_loc(loc, referer_id)
        self.recent_back_visits.appendleft(loc)
        self.forward_visits.clear()
        return loc
    
    def obsolete_uri(self, uri, undo_delta=0, orig_dir_was_back=True):
        """Mark this URI and all its visits as obsolete -- it will no longer be
        included in history movements.
        
        This call needs to follow calls to history.go_forward or
        history.go_back where the jump led to an unreachable URI.
        
        @param uri {str} The URI to mark obsolete.
        @param undo_delta {int} offset between the previous current loc
            and the new current loc (whose URI is being obsoleted here)
            - value is absolute
        @param orig_dir_was_back {bool} True if we tried to move back, False if forward
        
        Examples:
        loc = hist.go_back(1, curr_loc)
        # loc is bogus
        hist.obsolete_uri(loc.uri, 1, True)
        # Keep using curr_loc

        loc = hist.go_forward(2, curr_loc)
        # loc is bogus
        hist.obsolete_uri(loc.uri, 2, False)

        """
        with self.db.connect(commit=True) as cu:
            uri_id = self.db.uri_id_from_uri(uri, create_if_new=False, cu=cu)
            if not uri_id:
                return
            self.db.obsolete_uri(uri, uri_id, cu=cu)
            self.reload_recent_history_cache(cu, uri, undo_delta, orig_dir_was_back)

    def reload_recent_history_cache(self, cu, obsoleted_uri=None, undo_delta=0,
            orig_dir_was_back=True):
        """Reload the cache of recent history items (`self.forward_visits`,
        `self.recent_back_visits` and `self._last_visit`) if visits in that
        cache might have become invalid: via `obsolete_uri()` or expiry of
        visits.
        
        A pattern is this:
        - User attempts to go back N locations in the history, and hits a
          URI that is invalid.
        - The editor then obsoletes that URI (`.obsolete_uri()`) which calls
          this method.
        In this case we need to properly update the appropriate remaining
        size of `self.forward_visits`. This is what the `obsoleted_uri`,
        `undo_delta` and `orig_dir_was_back` arguments are used for.
        
        @param cu {sqlite3.Cursor} A db cursor to use.
        @param obsoleted_uri {str} If given, a URI that was just obsoleted.
            Default None.
        @param undo_delta {int} The size of the jump in the pattern described
            above. Default 0.
        @param orig_dir_was_back {bool} Whether the jump in the pattern
            described above was forward or back. Default True.
        """
        # Regenerate the recent history cache.
        if self.forward_visits:
            top_loc = self.forward_visits[0]
        elif self._last_visit:
            top_loc = self._last_visit
        elif not self.recent_back_visits:
            # The cache is empty, and since this is called when
            # we've removed items, there's nothing left to do.
            return
        else:
            top_loc = self.recent_back_visits[0]
                
        # Determine `num_forward_visits` for the restored cache. This is
        # complicated if a URI in the cache was just obosoleted and what
        # kind of jump resulted in getting to that URI. See the pattern
        # described in the docstring.
        if undo_delta == 0:
            if obsoleted_uri is None:
                num_forward_visits = len(self.forward_visits)
            else:
                num_forward_visits = len([x for x in self.forward_visits
                                          if x.uri != obsoleted_uri])
        else:
            if orig_dir_was_back:
                # The undo will move forward, so we don't care about
                # what's in the back visits, nor in the older part of the
                # forward visits, so we just examine the newest delta items.
                # Newest items are at the left side (queue part) of the deque.
                if len(self.forward_visits) < undo_delta:
                    # This happens when we are obsoleting a URI with no
                    # tabs loaded in the editor, so by definition there are no
                    # forward visits to keep.
                    num_forward_visits = 0
                else:
                    num_forward_visits = len(
                        [x for x in
                         islice(self.forward_visits,
                                0,
                                len(self.forward_visits) - undo_delta)
                         if x.uri != obsoleted_uri])
            else:
                # The undo will move back.  Prune the current forward visits,
                # and the newest <delta - 1> back visits.
                num_forward_visits = (
                      len([x for x in self.forward_visits if x.uri != obsoleted_uri])
                    + len([x for x in
                           islice(self.recent_back_visits, 0, undo_delta - 1)
                           if x.uri != obsoleted_uri])
                )
        self._load_recent_history_cache(top_loc.id, num_forward_visits, cu=cu)

    def can_go_back(self):
        """Returns a boolean indicating whether there is any back history.
        
        @returns {boolean}
        """
        return len(self.recent_back_visits) > 0

    def can_go_forward(self):
        """Returns a boolean indicating whether there is any forward history.
        
        @returns {boolean}
        """
        return len(self.forward_visits) > 0
        
    def have_recent_history(self):
        """Returns a boolean indicating whether there are any recent locations.
        
        @returns {boolean}
        """
        return len(self.recent_back_visits) > 0 or len(self.forward_visits) > 0

    def go_back(self, curr_loc, n=1):
        """Go back N steps (default 1) in this history session.
        
        @param curr_loc {Location} The current editor location.
        @param n {int} The number of steps in the history to go back.
        @returns {Location} The location N steps back.
        @raises `HistoryError` if falls off the end of the history.
        """
        if _xpcom_:
            curr_loc = UnwrapObject(curr_loc)
        assert curr_loc is None or isinstance(curr_loc, Location)
        assert n > 0, "invalid `n` value for `go_back(n)`: %r" % n
        if n > self.RECENT_BACK_VISITS_CACHE_LENGTH:
            # Without this guard the block below that replenishes
            # `recent_back_visits` would overflow that data structures
            # `maxlen`, resulting in a dropped history visits.
            raise HistoryError("cannot go back %d steps: implementation is "
                               "limited to going back a maximum of %d steps "
                               "in one jump"
                               % (n, self.RECENT_BACK_VISITS_CACHE_LENGTH))
        
        # Ensure have the back visits we need to go back.
        if not self.recent_back_visits:
            raise HistoryError("cannot go back: no more back history")
        if ((n > len(self.recent_back_visits)
             or len(self.recent_back_visits) <= self.RECENT_BACK_VISITS_DEPLETION_LENGTH)
            and self.recent_back_visits[-1].referer_id is not None):
            # The `recent_back_visits` cache is getting depleted.
            self._replenish_recent_back_visits()
        if n > len(self.recent_back_visits):
            raise HistoryError(
                "cannot go back %d step%s: not enough back history (%d)"
                % (n, ("" if n == 1 else "s"), len(self.recent_back_visits)))
        
        # Go back.
        if curr_loc is not None:
            if curr_loc == self._last_visit:
                # Do we need to add a new forward_visit, or reuse the
                # current loc?
                loc = self._last_visit
            else:
                # The user's position has changed since the last jump.
                # Update the referer_id's to point correctly.
                with self.db.connect(commit=True) as cu:
                    loc = self.db.add_loc(curr_loc, referer_id=self.recent_back_visits[0].id, cu=cu)
                    if self.forward_visits:
                        # The newest loc in forward_visits must now refer
                        # to the new loc.
                        self.db.update_referer_id(self.forward_visits[-1], loc.id, cu=cu)
        
            self.forward_visits.append(loc)
        
        # Shift the intermediate loc's from back_visits to forward_visits
        for i in range(n - 1):
            loc = self.recent_back_visits.popleft()
            self.forward_visits.append(loc)
        
        self._last_visit = self.recent_back_visits.popleft()
        return self._last_visit
        

    def go_forward(self, curr_loc, n=1):
        """Go forward N steps (default 1) in this history session.
        
        @param curr_loc {Location} The current editor location.
        @param n {int} The number of steps in the history to go forward.
        @returns {Location} The location N steps forward.
        @raises `HistoryError` if falls of the end of the history.
        """
        if _xpcom_:
            curr_loc = UnwrapObject(curr_loc)
        assert curr_loc is None or isinstance(curr_loc, Location)
        assert n > 0, "invalid `n` value for `go_forward(n)`: %r" % n
        if n > len(self.forward_visits):
            raise HistoryError("cannot go forward %d steps: there are only %d "
                               "forward visits in the current history"
                               % (n, len(self.forward_visits)))

        # Go forward.
        # Do we need to add a new back_visit, or reuse the
        # current loc?
        if curr_loc is not None:
            if curr_loc == self._last_visit:
                loc = self._last_visit
            else:
                # The user's position has changed since the last jump.
                # We have to do some more bookeeping for the back/forward
                # stack.
                with self.db.connect(commit=True) as cu:
                    referer_id = (self.recent_back_visits
                                  and self.recent_back_visits[0].id or None)
                    loc = self.db.add_loc(curr_loc, referer_id=referer_id, cu=cu)
                    if self.forward_visits:
                        # The preceding visit in the stack must now refer
                        # to this new one.
                        self.db.update_referer_id(self.forward_visits[-1], loc.id, cu=cu)
                    
            self.recent_back_visits.appendleft(loc)
        
        # Shift the intermediate locs from forward to back
        for i in range(n - 1):
            loc = self.forward_visits.pop()
            self.recent_back_visits.appendleft(loc)
            
        self._last_visit = self.forward_visits.pop()
        return self._last_visit
    
    def recent_history(self, curr_loc=None, merge_curr_loc=True):
        """Generate Locations that summarizes the current Back/Forward state,
        e.g. useful for displaying a list to the user. This typically looks like
        this:
        
            ... forward visit locations (if any, furthest forward first) ...
            `curr_loc` or None (a placeholder for the current location)
            ... recent back visit locations (most recent first) ...
        
        @param curr_loc {Location} The current location. If given and this
            matches one of the bounding visits, then `is-curr` will be True.
            Otherwise, the placeholder will be yielded as above.
        @param merge_curr_loc {bool} TODO: document this
        @yields 2-tuples (<is-curr>, <loc>)
        """
        if _xpcom_:
            curr_loc = UnwrapObject(curr_loc)
        curr_handled = False
        for i, loc in enumerate(self.forward_visits):
            is_curr = (merge_curr_loc
                       and curr_loc is not None
                       and i == len(self.forward_visits) - 1
                       and loc == curr_loc)
            if is_curr:
                curr_handled = True
            yield is_curr, loc
        if (not curr_handled
            and len(self.recent_back_visits) == 0
            and len(self.forward_visits) > 0):
            curr_handled = True
            yield True, curr_loc
        for i, loc in enumerate(self.recent_back_visits):
            #TODO: duplicated logic here, fix it
            is_curr = (not curr_handled 
                       and curr_loc is not None
                       and i == 0
                       and loc == curr_loc)
            if (not curr_handled
                and not is_curr
                and i == 0):
                yield True, curr_loc
            if i >= self.RECENT_BACK_VISITS_LENGTH:
                break
            yield is_curr, loc

    def update_marker_handles_on_close(self, uri, scimoz):
        self.db.update_marker_handles_on_close(uri, scimoz,
                                               self.forward_visits,
                                               self.recent_back_visits)
        
    def debug_dump_recent_history(self, curr_loc=None, merge_curr_loc=True):
        merge_str = "" if merge_curr_loc else " (curr loc not merged)"
        print "-- recent history%s" % merge_str
        for is_curr, loc in self.recent_history(curr_loc,
                merge_curr_loc=merge_curr_loc):
            print ("  *" if is_curr else "   "),
            if not loc:
                print "(current location)"
            else:
                print repr(loc)
        if self._last_visit is not None:
            print "self._last_visit: %r" % self._last_visit
        print "--"

    def recent_uris(self, n=100, show_all=False):
        """Generate the most recent N uris.
        
        @param n {int} The number of URIs to look back for. Default 100.
        """
        PAGE_SIZE = 100
        uri_id_set = set()
        with self.db.connect() as cu:
            # Just one page for starters.
            offset = 0
            while True:
                num_remaining = n - len(uri_id_set)
                new_uri_ids = []
                sql = "SELECT uri_id  FROM history_visit WHERE session_name=?"
                vals = [self.session_name]
                if not show_all:
                    sql += " and is_obsolete=?"
                    vals.append(False)
                sql += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
                vals += (PAGE_SIZE, offset)
                cu.execute(sql, tuple(vals))
                rows = cu.fetchall()
                for row in rows:
                    uri_id = row[0]
                    if uri_id in uri_id_set:
                        continue
                    uri_id_set.add(uri_id)
                    new_uri_ids.append(uri_id)
                #TODO:PERF: Bulk get of URI. Need Database.uris_from_uri_ids.
                for uri_id in new_uri_ids[:num_remaining]:
                    uri = self.db.uri_from_id(uri_id, cu=cu)
                    if not show_all:
                        # Filter out any that don't exist
                        if uri.startswith("file:/"):
                            fname = uriparse.URIToLocalPath(uri)
                            if not exists(fname):
                                continue
                    yield uri
                if len(uri_id_set) > n or len(rows) < PAGE_SIZE:
                    break
                offset += PAGE_SIZE
        

    def debug_dump_recent_uris(self, n=100):
        """Dump the most recent N uris.
        
        @param n {int} The number of URIs to look back for. Default 100.
        """
        print "-- recent URIs (session %s)" % self.session_name
        for uri in self.recent_uris(n, True):
            print uri

class History(object):
    """The main manager object for the editor history.
    
    Most of the interesting stuff happens on lazily created HistorySession
    instances. All the relevant methods here take an optional `session_name`
    argument (the default is the empty string).
    """
    # Number of days after which to expire 'visit' entries (default: 60).
    DEFAULT_LOC_EXPIRY_DAYS = 60

    closed = False

    def __init__(self, db_path=None, loc_expiry_days=None):
        self.db = Database(db_path)
        
        # session name -> HistorySession instance (lazily created)
        self.sessions = {}

    ####def __del__(self):
    #    if not self.closed:
    #        self.close()

    def close(self):
        """Close this history manager and all its sessions."""
        if self.closed:
            return
        for session in self.sessions.values():
            session.close()
        self.sessions = None
        self.db.close()
        self.closed = True

    #TODO: consider dropping this, not used
    def save(self):
        """Shortcut for telling all sessions to save cached data to the
        database. In general it shouldn't be necessary to call this directly,
        it is handled by calling `.close()`.
        """
        for session in self.sessions.values():
            session.save()
    
    def get_session(self, session_name=""):
        """Lazily create a session when first needed.
        
        @param session_name {str} A name for this session. Optional, default
            is the empty string.
        """
        if session_name not in self.sessions:
            self.sessions[session_name] = HistorySession(session_name, self.db)
        return self.sessions[session_name]

    def note_loc(self, loc):
        return self.get_session(loc.session_name).note_loc(loc)
    
    def obsolete_uri(self, uri, undo_delta=0, orig_dir_was_back=True,
                     session_name=""):
        """Mark the given URI as obsolete.
        
        *Currently* the only kind of URIs that are obsoleted in Komodo (dbgp://
        URLs for expired debug sessions) can only exist in a single session, so
        can call this on just one session.
        """
        self.get_session(session_name).obsolete_uri(
            uri, undo_delta, orig_dir_was_back)

    def can_go_back(self, session_name=""):
        return self.get_session(session_name).can_go_back()

    def can_go_forward(self, session_name=""):
        return self.get_session(session_name).can_go_forward()

    def have_recent_history(self, session_name=""):
        return self.get_session(session_name).have_recent_history()

    def go_back(self, curr_loc, n=1, session_name=""):
        """Go back N steps (default 1) in this history session.
        @param curr_loc {Location} 
        @param n {int}
        @param session_name {str} The session name. Only used if curr_loc
            is None
        @returns {Location} The location N steps back.
        @raises `HistoryError' if falls off the end of this history.
        """
        if curr_loc:
            session_name = curr_loc.session_name
        return self.get_session(session_name).go_back(curr_loc, n)

    def go_forward(self, curr_loc, n=1, session_name=""):
        """Go forward N steps (default 1) in this history session.
        @param curr_loc {Location} 
        @param n {int}
        @param session_name {str} The session name. Only used if curr_loc
            is None
        @returns {Location} The location N steps forward.
        @raises `HistoryError' if falls off the end of this history.
        """
        if curr_loc:
            session_name = curr_loc.session_name
        return self.get_session(session_name).go_forward(curr_loc, n)

    def recent_history(self, curr_loc=None, merge_curr_loc=True, session_name=""):
        return self.get_session(session_name).recent_history(
            curr_loc, merge_curr_loc)
            
    def update_marker_handles_on_close(self, uri, scimoz):
        for session in self.sessions.values():
            session.update_marker_handles_on_close(uri, scimoz)

    def debug_dump_recent_uris(self, session_name=""):
        self.sessions[session_name].debug_dump_recent_uris(True)

    def recent_uris(self, n=100, session_name="", show_all=False):
        """Generate the most recent N uris.
        
        @param n {int} The number of URIs to look back for. Default 100.
        @param session_name {str} Current history session name. Optional.
        """
        return self.get_session(session_name).recent_uris(n, show_all)
    
    def recent_uris_as_array(self, n=100, session_name="", show_all=False):
        return list(self.recent_uris(n, session_name, show_all))
    
    def debug_dump_recent_history(self, curr_loc=None, merge_curr_loc=True,
                                  session_name=""):
        if session_name is None:
            for session in self.sessions.values():
                session.debug_dump_recent_history(curr_loc, merge_curr_loc)
        else:
            self.sessions[session_name].\
                debug_dump_recent_history(curr_loc, merge_curr_loc)

    def get_num_visits(self, uri, default=None):
        return self.db.get_num_visits(uri, default)



#---- internal support stuff

def _rm_file(path):
    """Remove the given file path.
    
    @param path {str} The file path.

    This attempts to robustly delete the given file path.
    Note: This doesn't handle directories.
    """
    from os.path import exists
    os.remove(path)
    for i in range(10): # Try to avoid OSError from slow-deleting NTFS
        if not exists(path):
            break
        time.sleep(1)

def _int_or_none(s):
    if s is None:
        return s
    return int(s)

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


_g_database_schema = """
    CREATE TABLE history_meta (
       key TEXT UNIQUE ON CONFLICT REPLACE,
       value TEXT
    );
    
    CREATE TABLE history_uri (
        id INTEGER NOT NULL PRIMARY KEY,
        is_obsolete INTEGER DEFAULT 0,
        uri TEXT UNIQUE,
        visit_count INTEGER DEFAULT 0
    );
    
    CREATE TABLE history_visit (
        id INTEGER NOT NULL PRIMARY KEY,
        is_obsolete INTEGER DEFAULT 0,
        
        -- refers to a another "visit" row, providing a linked-list of "back" history
        referer_id INTEGER,
        timestamp REAL,                 -- Julian time (UTC)
        session_name TEXT DEFAULT NULL, -- for history sessions, typically the empty string, see details below

        -- These represent the location.
        uri_id INTEGER,
        line INTEGER,
        col INTEGER,  -- not using 'column' because that needs to be quoted
        view_type TEXT,

        -- These are transient values that only make sense for a visit added
        -- for document and view currently open in Komodo.
        marker_handle INTEGER DEFAULT 0,
        window_num INTEGER DEFAULT 0,
        tabbed_view_id INTEGER NOT NULL DEFAULT 0,
        
        -- These are used for display and search via an awesome-bar.
        content TEXT,   -- Up to 100 chars of the current line.
        section_title TEXT    -- The name of the section containing this line.
    );
    CREATE INDEX history_visit_uri_id ON history_visit(uri_id);

    -- See http://eusqlite.wikispaces.com/dates+and+times
    CREATE TRIGGER history_visit_set_timestamp AFTER INSERT ON history_visit
    BEGIN
        UPDATE history_visit SET timestamp = julianday('now') WHERE rowid = new.rowid;
    END;
    CREATE INDEX history_visit_timestamp ON history_visit(timestamp);

    CREATE TRIGGER history_uri_incr_visit_count INSERT ON history_visit
    FOR EACH ROW
    BEGIN
        UPDATE history_uri SET visit_count = visit_count + 1 WHERE id=new.uri_id;
    END;
    
    CREATE TRIGGER history_uri_decr_visit_count DELETE ON history_visit
    FOR EACH ROW
    BEGIN
        UPDATE history_uri SET visit_count = visit_count - 1 WHERE id=old.uri_id;
    END;
    -- TODO: trigger to remove URI from table if visit_count drops to zero? Look into perf.
"""

