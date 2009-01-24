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
import sys
import logging
from contextlib import contextmanager
import sqlite3
from collections import deque
from pprint import pprint, pformat

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

    # Core location fields, typically set in the constructor.
    uri = None
    line = None
    col = None
    
    # Editor/Komodo-specific fields.
    view_type = None
    # Scintilla handle from SCI_MARKERGET. "0" (zero) indicates an empty value.
    marker_handle = 0
    window_name = None
    # Numeric ID identifying which tabbed-view the editor view was open in:
    # left/top or right/bottom. "-1" indicates, an empty value.
    multiview_id = -1
    
    # Fields set by the database on insertion.
    id = None
    uri_id = None
    referer_id = None

    def __init__(self, uri, line, col, view_type="editor",
                 id=None, uri_id=None, referer_id=None,
                 marker_handle=0, window_name=None, multiview_id=-1):
        #XXX:TODO: URI canonicalization.
        self.uri = uri
        self.line = line
        self.col = col
        self.view_type = view_type
        self.id = id
        self.uri_id = uri_id
        self.referer_id = referer_id
        self.marker_handle = marker_handle
        self.window_name = window_name
        self.multiview_id = multiview_id

    def __repr__(self):
        extras = []
        if self.id is not None:
            extras.append("id=%s" % self.id)
        if self.referer_id is not None:
            extras.append("ref=%s" % self.referer_id)
        #extras.append("multiview_id=%r" % self.multiview_id)
        if self.view_type != "editor":
            extras.append(self.view_type)
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
    # db change log:
    # - 1.0.0: initial version
    VERSION = "1.0.0"

    path = None
    
    LOC_MARKER_UPDATE_LIMIT = 100

    @classmethod
    def _default_path(cls):
        return expanduser("~/tmp/history.sqlite")

    def __init__(self, path=None):
        self.path = path or self._default_path()
        
        # Performance note: This cache can dramatically speed up
        # `uri_id_from_uri`, but only if N is greater than the typical
        # working set of URIs for which it is being called. The working set
        # should, I believe, correspond to the number of files the Komodo
        # user is jumping around in.
        # See `perf.py::perf_uris()`. 
        self._uri_id_from_uri_cache = _RecentsDict(10)
        
        if not exists(self.path):
            self.create()
        #TODO: setup upgrade/reset code (following codeintel's lead)

    def __repr__(self):
        return "<Database %s>" % self.path

    @contextmanager
    def connect(self, commit=False, cu=None):
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
        @param cu {sqlite3.Cursor} An existing cursor to use. This allows
            callers to avoid the overhead of another db connection when
            already have one, while keeping the same "with"-statement
            call structure.
        """
        if cu is not None:
            yield cu
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
        with self.connect(True) as cu:
            cu.executescript(_g_database_schema)
            cu.execute("INSERT INTO history_meta(key, value) VALUES (?, ?)", 
                ("version", self.VERSION))

    @property
    def version(self):
        """Return the version of the db on disk (or None if cannot
        determine).
        """
        #TODO: error handling?
        return self.get_meta("version")

    def uri_id_from_uri(self, uri, cu=None):
        """Get a `uri_id` for the given URI, possibly inserting a new row
        in the `history_uri` table if new.
        
        @param uri {str} The URI for which to get an id
        @param cu {sqlite3.Cursor} An existing db cursor to use. Optional.
        @returns {int} An ID for this URI.
        """
        cache = self._uri_id_from_uri_cache
        if uri in cache:
            return cache[uri]
        
        with self.connect(cu=cu) as cu:
            cu.execute("SELECT id FROM history_uri WHERE uri=?", (uri,))
            row = cu.fetchone()
            if row:
                uri_id = int(row[0])
            else:
                cu.execute("INSERT INTO history_uri(uri) VALUES (?)", (uri,))
                cu.connection.commit()
                uri_id = cu.lastrowid
        cache[uri] = uri_id
        return uri_id

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
        with self.connect(True, cu=cu) as cu:
            uri_id = self.uri_id_from_uri(loc.uri, cu=cu)
            cu.execute("""
                INSERT INTO history_visit(referer_id, uri_id, line, col, view_type, marker_handle)
                VALUES (?, ?, ?, ?, ?, ?)
                """, 
                (referer_id, uri_id, loc.line, loc.col, loc.view_type, loc.marker_handle))
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
        with self.connect(True, cu=cu) as cu:
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

    def visit_from_id(self, id, session_name=None, cu=None):
        """Load the given visit from `history_visit` table.
        
        @param id {int} The id of the visit to load. If None, the *latest*
            visit is returned.
        @param session_name {str} Optional. Ignored for now.
        @param cu {sqlite3.Cursor} An existing cursor to use.
        @returns {Location} A location instance.
        @raises `HistoryError` if no such location exists.
        """
        with self.connect(cu=cu) as cu:
            if id is None:
                cu.execute("""
                    SELECT id, datetime(timestamp) FROM history_visit
                    ORDER BY timestamp DESC LIMIT 1;
                    """)
                row = cu.fetchone()
                if row is None:
                    raise HistoryNoLatestVisitError(
                        "cannot get latest visit: there are no visits in the db")
                id = int(row[0])
            cu.execute("""
                SELECT referer_id, uri_id, line, col, view_type, content,
                       section, marker_handle, window_name, multiview_id
                FROM history_visit
                WHERE id=?
                """, (id,))
            row = cu.fetchone()
            if row is None:
                raise HistoryError("cannot get visit %r: id does not exist" % id)
            
            uri_id = int(row[1])
            uri = self.uri_from_id(uri_id)
            loc = Location(
                uri=uri,
                line=int(row[2]),
                col=int(row[3]),
                view_type=row[4],
                id=id,
                uri_id=uri_id,
                referer_id=_int_or_none(row[0]),
                marker_handle=row[7],
                window_name=row[8],
                multiview_id=row[9],
            )

        return loc
            
    def update_marker_handles_on_close(self, uri, scimoz, forward_visits, back_visits):
        if not uri:
            log.info("Can't update markers on a null URI (untitled)")
            return
        new_rows = []
        with self.connect(commit=True) as cu:
            uri_id = self.uri_id_from_uri(uri, cu)
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
            cu.execute("SELECT timestamp"
                       + " FROM history_visit"
                       + " WHERE uri_id=? and marker_handle != -1"
                       + " ORDER BY timestamp DESC LIMIT ?",
                       (uri_id, self.LOC_MARKER_UPDATE_LIMIT))
            row = cu.fetchone()
            if row is None:
                cu.execute("UPDATE history_visit SET marker_handle=?"
                           + " WHERE uri_id=? and marker_handle != -1",
                           (-1, uri_id))
            else:
                cu.execute("UPDATE history_visit SET marker_handle=?"
                           + " WHERE uri_id=? and marker_handle != -1 and timestamp <= ?",
                           (-1, uri_id, row[0]))
            for loc in local_locs_by_id.values():
                loc.marker_handle = -1
    
    def get_meta(self, key, default=None, cu=None):
        """Get a value from the meta table.
        
        @param key {str} The meta key.
        @param default {str} Default value if the key is not found in the db.
        @param cu {sqlite3.Cursor} An existing cursor to use.
        @returns {str} The value in the database for this key, or `default`.
        """
        with self.connect(cu=cu) as cu:
            cu.execute("SELECT value FROM history_meta WHERE key=?", (key,))
            row = cu.fetchone()
            if row is None:
                return default
            return row[0]
    
    def set_meta(self, key, value, cu=None):
        """Set a value into the meta table.
        
        @param key {str} The meta key.
        @param default {str} Default value if the key is not found in the db.
        @param cu {sqlite3.Cursor} An existing cursor to use.
        @returns {str} The value in the database for this key, or `default`.
        """
        with self.connect(True, cu=cu) as cu:
            cu.execute("INSERT INTO history_meta(key, value) VALUES (?, ?)", 
                (key, value))

    def del_meta(self, key):
        """Delete a key/value pair from the meta table.
        
        @param key {str} The meta key.
        """
        with self.connect(True) as cu:
            cu.execute("DELETE FROM history_meta WHERE key=?", (key,))
        


class History(object):
    """The main manager object for the editor history."""
    # Number of seconds after which to expire 'visit' entries (default: 1 year).
    DEFAULT_EXPIRE_ARG = 365 * 24 * 60 * 60
    RECENT_BACK_VISITS_LENGTH = 10
    # This cache length limits the max allowable value of 'n' for
    # `go_back(..., n)`, so let's make it reasonably large.
    RECENT_BACK_VISITS_CACHE_LENGTH = 10 * RECENT_BACK_VISITS_LENGTH
    RECENT_BACK_VISITS_DEPLETION_LENGTH = RECENT_BACK_VISITS_LENGTH + 2

    closed = False

    def __init__(self, db_path=None, expire_age=None):
        self.db = Database(db_path)

        #XXX:TODO: Expiring visits/uris.
        assert expire_age is None or isinstance(expire_age, int)
        self.expire_age = expire_age or self.DEFAULT_EXPIRE_ARG

        # Recent history: We cache the last few "back" visits and all forward
        # visits -- those resulting from the user jumping back in the history
        # one or more times.
        #   recent_back_visits: most recent first. We cache more than
        #       "recent" length to try to limit the need to hit the database
        #       when the user goes back and forth a lot.
        self.recent_back_visits = deque(maxlen=self.RECENT_BACK_VISITS_CACHE_LENGTH)
        #   forward_visits: furthest forward first, i.e. the location for the
        #       next "go_forward" is at the end
        self.forward_visits = deque()
        # The last visit returned by `go_back` or `go_forward`.
        self._last_visit = None
        
        self.load()

        self.closed = False

    def __del__(self):
        if not self.closed:
            self.close()

    def close(self):
        if self.closed:
            return
        self.save()
        self.closed = True

    def load(self):
        """Load recent history from the database."""
        with self.db.connect(True) as cu:
            # `num_forward_visits` and `top_loc_id` in the meta table help
            # us reconstruct the back/forward state. `num_forward_visits == -1`
            # indicates that these weren't saved (e.g. if Komodo crashed). In
            # this case we do the best we can by using the *latest* visit as
            # the top of the stack and presuming `num_forward_visits == 0`.
            num_forward_visits = int(self.db.get_meta("num_forward_visits", -1, cu=cu))
            if num_forward_visits == -1:
                have_state_info = False
                num_forward_visits = 0
                top_loc_id = None
            else:
                have_state_info = True
                # Set to `-1` so we'll be able to tell on next start
                # if it was set.
                self.db.set_meta("num_forward_visits", -1, cu=cu)
                top_loc_id = _int_or_none(self.db.get_meta("top_loc_id", cu=cu))

            n = 2 * self.RECENT_BACK_VISITS_LENGTH + num_forward_visits + 1
            id = top_loc_id
            for i in range(n):
                try:
                    loc = self.db.visit_from_id(id, cu=cu)
                except HistoryNoLatestVisitError, ex:
                    break
                if i < num_forward_visits:
                    self.forward_visits.appendleft(loc)
                elif have_state_info and i == num_forward_visits:
                    self._last_visit = loc
                else:
                    self.recent_back_visits.append(loc)
                id = loc.referer_id
                if id is None:
                    break

    def save(self):
        """Save some recent history meta-data.
        
        Most history information (namely the "visit" entries in the visit
        and uri tables) is saved on the fly. However, some meta data is not,
        to save unnecessary writing to the db. We save that meta data here
        to restore the back/forward state for the next session.
        """
        with self.db.connect(True) as cu:
            self.db.set_meta("num_forward_visits",
                             str(len(self.forward_visits)), cu=cu)
            # The ID for the "top" location in the back/forward stack.
            if self.forward_visits:
                top_loc_id = self.forward_visits[0].id
            elif self.recent_back_visits:
                top_loc_id = self.recent_back_visits[0].id
            else:
                top_loc_id = None
            self.db.set_meta("top_loc_id", top_loc_id, cu=cu)

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
        log.debug("note loc: %r", loc)
        referer_id = (self.recent_back_visits
            and self.recent_back_visits[0].id or None)
        self.db.add_loc(loc, referer_id)
        self.recent_back_visits.appendleft(loc)
        self.forward_visits.clear()
        return loc

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

    def go_back(self, curr_loc, n=1):
        """Go back N steps (default 1) in the history.
        
        @param curr_loc {Location} The current editor location.
        @param n {int} The number of steps in the history to go back.
        @returns {Location} The location N steps back.
        @raises `HistoryError` if falls off the end of the history.
        """
        if _xpcom_:
            curr_loc = UnwrapObject(curr_loc)
        assert isinstance(curr_loc, Location)
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
            # The `recent_back_visits` cache is getting depleted. Need
            # to replenish from the db.
            num_to_load = (self.RECENT_BACK_VISITS_CACHE_LENGTH
                - len(self.recent_back_visits))
            id_ = self.recent_back_visits[-1].referer_id
            with self.db.connect() as cu:
                for i in range(num_to_load):
                    if id_ is None:
                        break
                    loc_ = self.db.visit_from_id(id_, cu=cu)
                    self.recent_back_visits.append(loc_)
                    id_ = loc_.referer_id
        if n > len(self.recent_back_visits):
            raise HistoryError(
                "cannot go back %d step%s: not enough back history (%d)"
                % (n, ("" if len(n)==1 else "s"), len(self.recent_back_visits)))
        
        # Go back.
        for i in range(n):
            rv = loc = self.recent_back_visits.popleft()
            if i == 0:
                if curr_loc == self._last_visit:
                    loc = self._last_visit
                else:
                    # The user's position has changed since the last jump.
                    # We have to do some more bookeeping for the back/forward
                    # stack.
                    with self.db.connect(True) as cu:
                        old_loc = loc
                        loc = self.db.add_loc(curr_loc, referer_id=old_loc.id, cu=cu)
                        if self.forward_visits:
                            # The preceding visit in the stack must now refer
                            # to this new one.
                            self.db.update_referer_id(self.forward_visits[-1], loc.id, cu=cu)
            self.forward_visits.append(loc)
        self._last_visit = rv
        return rv

    def go_forward(self, curr_loc, n=1):
        """Go forward N steps (default 1) in the history.
        
        @param curr_loc {Location} The current editor location.
        @param n {int} The number of steps in the history to go forward.
        @returns {Location} The location N steps forward.
        @raises `HistoryError` if falls of the end of the history.
        """
        if _xpcom_:
            curr_loc = UnwrapObject(curr_loc)
        assert isinstance(curr_loc, Location)
        assert n > 0, "invalid `n` value for `go_forward(n)`: %r" % n
        if n > len(self.forward_visits):
            raise HistoryError("cannot go forward %d steps: there are only %d "
                               "forward visits in the current history"
                               % (n, len(self.forward_visits)))
        for i in range(n):
            rv = loc = self.forward_visits.pop()
            if i == 0:
                if curr_loc == self._last_visit:
                    loc = self._last_visit
                else:
                    with self.db.connect(True) as cu:
                        old_loc = loc
                        referer_id = (self.recent_back_visits
                                      and self.recent_back_visits[0].id or None)
                        loc = self.db.add_loc(curr_loc, referer_id=referer_id, cu=cu)
                        # The preceding visit in the stack must now refer
                        # to this new one.
                        self.db.update_referer_id(old_loc, loc.id, cu=cu)
            self.recent_back_visits.appendleft(loc)
        self._last_visit = rv
        return rv

    def recent_history(self, curr_loc=None):
        """Generate Locations that summarizes the current Back/Forward state,
        e.g. useful for displaying a list to the user. This typically looks like
        this:
        
            ... forward visit locations (if any, furthest forward first) ...
            `curr_loc` or None (a placeholder for the current location)
            ... recent back visit locations (most recent first) ...
        
        @param curr_loc {Location} The current location. If given and this
            matches one of the bounding visits, then `is-curr` will be True.
            Otherwise, the placeholder will be yielded as above.
        @yields 2-tuples (<is-curr>, <loc>)
        """
        if _xpcom_ and curr_loc:
            curr_loc = UnwrapObject(curr_loc)
        curr_handled = False
        for i, loc in enumerate(self.forward_visits):
            is_curr = (curr_loc is not None
                       and i == len(self.forward_visits) - 1
                       and loc == curr_loc)
            if is_curr:
                curr_handled = True
            yield is_curr, loc
        if not curr_handled and len(self.recent_back_visits) == 0:
            yield True, curr_loc
        for i, loc in enumerate(self.recent_back_visits):
            is_curr = (not curr_handled 
                       and curr_loc is not None
                       and i == 0
                       and loc == curr_loc)
            if not curr_handled and not is_curr and i == 0:
                yield True, curr_loc
            if i >= self.RECENT_BACK_VISITS_LENGTH:
                break
            yield is_curr, loc
                    
    def update_marker_handles_on_close(self, uri, scimoz):
        self.db.update_marker_handles_on_close(uri, scimoz,
                                               self.forward_visits,
                                               self.recent_back_visits)
    
    def debug_dump_recent_history(self, curr_loc=None):
        print "-- recent history"
        for is_curr, loc in self.recent_history(curr_loc):
            print ("  *" if is_curr else "   "),
            if not loc:
                print "(current location)"
            else:
                print repr(loc)
        print "--"
        


#---- internal support stuff

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
                del self[k]
        else:
            del self.recent_keys[idx]
            self.recent_keys.append(key)

    def __getitem__(self, key):
        value = dict.__getitem__(self, key)
        idx = self.recent_keys.index(key)
        del self.recent_keys[idx]
        self.recent_keys.append(key)
        return value

    def __repr__(self):
        return "_RecentsDict(%d, %s)" % (self.limit, dict.__repr__(self))


_g_database_schema = """
    CREATE TABLE history_meta (
       key TEXT UNIQUE ON CONFLICT REPLACE,
       value TEXT
    );
    
    CREATE TABLE history_uri (
        id INTEGER NOT NULL PRIMARY KEY,
        uri TEXT UNIQUE,
        visit_count INTEGER DEFAULT 0
    );
    
    CREATE TABLE history_visit (
        id INTEGER NOT NULL PRIMARY KEY,
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
        window_name TEXT,
        multiview_id INTEGER NOT NULL DEFAULT -1,
        
        -- These are used for display and search via an awesome-bar.
        -- Whether to include "section" is still undecided.
        content TEXT,   -- Up to 100 chars of the current line.
        section TEXT    -- The name of the section containing this line.
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

