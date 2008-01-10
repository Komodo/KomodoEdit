#!/usr/bin/env python
#
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
#
# Notes on logging levels and verbosity
# -------------------------------------
# 
# How loud this script is depends on these options (the last one given wins):
#     (none given)        default verbosity (logging.INFO level)
#     -v, --verbose       more verbose (logging.INFO-1 level)
#     -q, --quiet         less verbose (logging.WARN level)
#     -d, --debug         debugging output (logging.DEBUG level)
# 
# Full tracebacks on errors are shown on the command-line with -d|--debug.
# '-v|--verbose' is useful for some commands that have normal and more
# verbose output modes.
#
# TODOs for frep.py
# -----------------
# - !!! Don't replace in if can't identify the lang
# - test suite !
# - See about necessary changes for one-shot confirmation
#   and other integration issues with Komodo
# - EOL tests (should use universal newlines?) I'm okay with not
#   supporting mixed newlines.
# - unicode content tests
# - unicode path tests
# - 'frep foo bar.txt' for one input file only: output differs from grep
#   (prefixing with filename). Should frep copy grep here?
# - findlib.replaceall() -- and probably others -- has some handling for
#   nicer error messages for a bogus regex or repl.
#
# TODOs for findlib
# -----------------
# - remove unused/deprecated stuff where possible
# - optparse
# - drop 'verbosity' and out, use logging
# - command line usage using the separate thread
# - replace in files on command line
# - good unicode tests

"""A Python script for doing find-and-replace stuff (a la grep/sed).
Primarily this exists to exercise the backend for Komodo's Find/Replace
functionality.
    
Example Usage:
  # grep-like
  frep foo *.txt           # grep for 'foo' in .txt files
  frep -r foo .            # grep for 'foo' in all text files (recursively)
  frep /f[ei]/i *.txt      # grep for 'fe', 'fi' (ignore case) in .txt files
  frep -l foo *.txt        # list .txt files matching 'foo'

  # sed-like
  frep s/foo/bar/ *.txt    # replace 'foo' with 'bar' in .txt files
  frep -u|--undo           # list replacements that can be undone
  frep -u ID               # undo replacement with id 'ID'

  # find-like
  frep . -i "foo*"         # list paths matching "foo*"
  frep . -i lang:Perl      # list Perl paths
  frep . -x lang:Python    # list all but Python paths

Undo notes:
  A replacement will log an id that can be used for subsequent undo.
  By default only the last 5 replacements are remembered. As well, the
  undo is far from perfect: if any of the changed files have been
  subsequently changed the undo might fail (or at least fail to undo
  that particular file).
"""

__version_info__ = (1, 0, 0)
__version__ = '.'.join(map(str, __version_info__))

import os
from os.path import (expanduser, join, basename, splitext, exists, dirname,
                     abspath)
import time
import sys
import re
import traceback
import datetime
import optparse
import logging
from pprint import pprint, pformat
from glob import glob
import cPickle as pickle
import codecs
import md5
import difflib

ko_dir = dirname(dirname(abspath(__file__)))
try:
    import textinfo
except ImportError:
    sys.path.insert(0, join(ko_dir, "src", "python-sitelib"))
    import textinfo
try:
    import findlib2
except ImportError:
    sys.path.insert(0, join(ko_dir, "src", "find"))
    import findlib2


#---- exceptions

class FindError(Exception):
    pass



#---- globals

log = logging.getLogger("frep")



#---- public functionality

def find(paths, includes=None, excludes=None):
    """List paths matching the given filters (a la GNU find).

    @param paths {sequence|iterator} is a sequence of paths to search.
    @param includes {list} is a sequence of 2-tuples defining include
        filters on textinfo data: (<textinfo-field>, <value>).
    @param excludes {list} is a sequence of 2-tuples defining exclude
        filters on textinfo data: (<textinfo-field>, <value>).
    """
    if not includes and not excludes: # Quick case.
        for path in paths:
            yield path
    else:
        all_fields = set(k for k,v in includes)
        all_fields.update(k for k,v in excludes)
        quick_determine_lang = False
        if all_fields == set('lang'):  # Special quick case.
            quick_determine_lang = True

        lidb = textinfo.get_default_lidb()
        for path in paths:
            ti = textinfo.TextInfo.init_from_path(path, lidb=lidb,
                    quick_determine_lang=quick_determine_lang)

            if includes:
                unmatched_includes = [field for field, value in includes
                                      if getattr(ti, field, None) != value]
                if unmatched_includes:
                    #log.debug("excluding path not matching '%s' include(s): %r",
                    #          "', '".join(unmatched_includes), path)
                    continue
            if excludes:
                matched_excludes = [field for field, value in excludes
                                    if getattr(ti, field, None) == value]
                if matched_excludes:
                    #log.debug("excluding path matching '%s' exclude(s): %r",
                    #          "', '".join(matched_excludes), path)
                    continue
            
            yield path


def grep(regex, paths, files_with_matches=False,
         treat_binary_files_as_text=False,
         skip_unknown_lang_paths=False,
         includes=None, excludes=None):
    """Grep for `regex` in the given paths.

    @param regex {regex} is the regular expression to search for.
    @param paths {sequence|iterator} is a sequence of paths to search.
    @param files_with_matches {boolean} if true indicates that only
        a hit for each file with one or more matches should be returned.
        Default is false.
    @param treat_binary_files_as_text {boolean} indicates that binary files
        should be search. By default they are skipped.
    @param skip_unknown_lang_paths {boolean} can be set True to skip
        grepping in files for which the lang could not be determined.
        This is useful when doing *replacements* to be safe about not
        wrecking havoc in binary files that happen to look like plain
        text.
    @param includes {list} is a sequence of 2-tuples defining include
        filters on textinfo data: (<textinfo-field>, <value>).
    @param excludes {list} is a sequence of 2-tuples defining exclude
        filters on textinfo data: (<textinfo-field>, <value>).
    """
    for path in paths:
        ti = textinfo.textinfo_from_path(path)

        if skip_unknown_lang_paths and ti.lang is None:
            yield SkipUnknownLangPath(path)
            continue
        if includes:
            unmatched_includes = [field for field, value in includes
                                  if getattr(ti, field, None) != value]
            if unmatched_includes:
                #log.debug("excluding path not matching '%s' include(s): %r",
                #          "', '".join(unmatched_includes), path)
                continue
        if excludes:
            matched_excludes = [field for field, value in excludes
                                if getattr(ti, field, None) == value]
            if matched_excludes:
                #log.debug("excluding path matching '%s' exclude(s): %r",
                #          "', '".join(matched_excludes), path)
                continue

        if ti.is_text:
            text = ti.text
        elif treat_binary_files_as_text:
            f = open(path, 'rb')
            text = f.read()
            f.close()
        else:
            yield SkipBinaryPath(path)
            continue
        
        accessor = _TextAccessor(text)
        for match in findlib2.find_all(regex, text, start=0, end=None):
            if files_with_matches:
                yield PathHit(path)
                break
            yield FindHit(path, ti.encoding, match, accessor)


def replace(regex, repl, paths, include_diff_events=False, 
            includes=None, excludes=None, dry_run=False):
    """Make the given regex replacement in the given paths.

    @param regex {regular expression} is the regex with which to search
    @param repl {string} is the replacement string
    @param paths {generator} is the list of paths to process
    @param include_diff_events {boolean} indicated whether to yield
        ReplaceDiff events. If true, one of these events is yielded for
        each changed path *before* the changes are saved.  This will
        allow for a confirmation process (TODO). False by default
        because there is a significant perf cost in calculating the diff.
    @param includes {list} is a sequence of 2-tuples defining include
        filters on textinfo data: (<textinfo-field>, <value>).
    @param excludes {list} is a sequence of 2-tuples defining exclude
        filters on textinfo data: (<textinfo-field>, <value>).
    @param dry_run {boolean} if True will result in going through the
        motions but not actually saving results (or generating a
        journal).
    """
    journal = None
    try:
        grepper = grep(regex, paths, skip_unknown_lang_paths=True,
                       includes=includes, excludes=excludes)
        for group in _grouped_by_path(grepper):
            if not isinstance(group[0], Hit):
                yield group[0]
                continue
            # 'group' is a list of FindHits for a single path.

            path = group[0].path
            encoding = group[0].encoding

            # Calculate the change.
            before_text = group[0].accessor.text
            after_text = regex.sub(repl, before_text)
            if before_text == after_text:
                continue
            accessor = _TextAccessor(after_text)

            if include_diff_events:
                diff_lines = difflib.unified_diff(
                        before_text.splitlines(1),
                        after_text.splitlines(1),
                        "%s (before)" % path,
                        "%s (after)" % path)
                diff = ''.join(diff_lines)
                #TODO: respond to signal to this event
                yield ReplaceDiff(path, diff)

            # If this is the first path, start the journal for this
            # replacment (for undo).
            if not dry_run and journal is None:
                #TODO: this isn't good enough for a summary
                summary = _str_from_regex_info(regex, repl)
                journal = Journal.create(summary)
                yield StartJournal(journal.id)

            # Gather and log (to the journal) the data needed for undo:
            # - The file encoding (encoding).
            # - The md5sum of the file before replacements
            #   (before_md5sum), allows for a sanity check if there
            #   weren't any subsequent changes.
            # - The md5sum of the file after replacements
            #   (after_md5sum), so we can know if we might have
            #   difficulties undoing later because of subsequent
            #   changes.
            # - For each hit: the string replaced (before), the
            #   replacement string (after), the char pos range
            #   (start_pos, end_pos), the start line (start_line,
            #   0-based).
            before_md5sum = md5.md5(before_text.encode(encoding)).hexdigest()
            after_md5sum = md5.md5(after_text.encode(encoding)).hexdigest()
            rhits = []
            pos_offset = 0
            line_offset = 0
            for fhit in group:
                m = fhit.match
                before = m.group(0)
                after = m.expand(repl)
                start_pos = fhit.start_pos + pos_offset
                pos_offset += len(after) - len(before)
                end_pos = fhit.end_pos + pos_offset
                start_line = fhit.line_num_range[0] + line_offset
                line_offset += after.count('\n') - before.count('\n')

                rhit = ReplaceHit(path, before, after,
                                  start_pos, end_pos, start_line,
                                  fhit, accessor)
                rhits.append(rhit)
            group = ReplaceHitGroup(path, encoding, before_md5sum,
                                    after_md5sum, rhits)
            if not dry_run:
                journal.add_replace_group(group)

            # Apply the changes.
            if not dry_run:
                #TODO: catch any exception and restore file (or
                #      create a backup somewhere) if write fails
                f = codecs.open(path, 'wb', encoding)
                try:
                    f.write(after_text)
                finally:
                    f.close()

            # Yield the hits.
            yield group
    finally:
        # Ensure the journal gets saved properly: essential for undo.
        if journal is not None:
            journal.close()


def undo_replace(journal_id, dry_run=False):
    """Undo the given replacement.

    For now the undo ability is the easy way out: it only works if none
    of the files in the replacement have been subsequently modified.

    Undo process:
    1. Get the journal.
    2. Ensure that none of the files to be reverted have been
       subsequently modified (via MD5 check).
    3. Undo each replacement. 
    4. Sanity check that the undo works (can compare MD5 via journaled
       value).
    5. Remove the journal.

    TODO: Support undo on modified files if the subsequent modifications
          are not on the same lines as any of the replacements.
    TODO: (future) Support undo on subsequent modification, skipping only
          those lines where there are conflicts.
    """
    journal = Journal.load(journal_id)

    # 2. Ensure can complete the undo.
    changed_paths = []
    for group in journal:
        f = open(group.path, 'rb') #TODO: handle path being missing
        bytes = f.read()
        f.close()
        md5sum = md5.md5(bytes).hexdigest()
        if md5sum != group.after_md5sum:
            changed_paths.append(group.path)
    if changed_paths:
        raise FindError("cannot undo replacement '%s' because the following "
                        "files have been subsequently modified: '%s'" 
                        % (journal_id, "', '".join(changed_paths)))

    # 3. Undo each replacement.
    #TODO: Bullet-proof backups to '~/.frep/backups/<id>/<hash>' and
    #      restoration on any failure.
    paths_failing_sanity_check = []
    for group in journal:
        f = codecs.open(group.path, 'rU', group.encoding)
        text = f.read()
        f.close()
        
        # Algoritm: Walk backwards through the replacements, appending
        #   unmodified-bit, original, unmodified-bit, ...
        # in reversed order, then reverse and join the pieces.
        # Perf notes:
        # (a) Building a list and joining once is much faster than
        #     joining a string many times.
        # (b) `lst.append(item)` is much faster than `lst.insert(0, item)`.
        bits = [] # list of tail-end bits of the file
        idx = len(text)
        for hit in reversed(group.replace_hits):
            bits.append(text[hit.end_pos:idx])
            bits.append(hit.before)
            idx = hit.start_pos
        bits.append(text[:idx])
        text = ''.join(reversed(bits))

        # 4. Sanity check.
        bytes = text.encode(group.encoding)
        md5sum = md5.md5(bytes).hexdigest()
        if md5sum != group.before_md5sum:
            paths_failing_sanity_check.append(group.path)

        # Write out the reverted content.
        if not dry_run:
            f = open(group.path, 'w')
            f.write(bytes)
            f.close()

        yield group

    # 4. Sanity check.
    #TODO: Something more useful than just warning. Yield event?
    if paths_failing_sanity_check:
        log.warn("sanity check failure: the following file(s) weren't "
                 "restored to their exact state before the replacement: '%s'",
                 "', '".join(paths_failing_sanity_check))

    # 5. Remove the journal.
    if not dry_run:
        try:
            os.remove(journal.path)
        except EnvironmentError, ex:
            log.warn("couldn't remove journal '%s': %s", journal.path, ex)
        if exists(journal.summary_path):
            try:
                os.remove(journal.summary_path)
            except EnvironmentError, ex:
                log.warn("couldn't remove journal summary '%s': %s", 
                         journal.summary_path, ex)

#---- replace Journal stuff

class Journal(list):
    """A replacement journal.
    
    >> j = Journal.create("s/foo/bar/ in *.py")  # create a new journal 
    >> j.add_replace_group(...) # add replacements for a path
    >> j.close()                # save (as a pickle) and close the file

    The created journal file is a pickle file in the journal dir
    (as returned by the _get_journal_dir() static method). The path is
    stored in `j.path`.

    >> k = Journal.load(j.path)    # open and load the saved journal
    >> k[0]
    ...hits for 'path'...

    There is also a journal id (it is part of the file path) that can be
    used to open.

    >> m = Journal.load(j.id)
    >> m[0]
    ...hits for 'path'...
    """
    id = None
    path = None
    summary_path = None
    summary = None   # prose description of the replacement

    @staticmethod
    def get_journal_dir():
        try:
            import applib
        except ImportError:
            d = expanduser("~/.frep")
        else:
            d = applib.user_cache_dir("frep", "ActiveState")
        return d

    @staticmethod
    def get_new_id(journal_dir):
        existing_ids = set(p[8:-7] for p in os.listdir(journal_dir)
            if p.startswith("journal-") and p.endswith(".pickle"))

        SENTINEL = 100
        for i in range(SENTINEL):
             id = _get_friendly_id()
             if id not in existing_ids:
                return id
        else:
            raise FindError("could not find a unique journal id in "
                            "%d attempts" % SENTINEL)

    NUM_JOURNALS_TO_KEEP = 5
    @classmethod
    def remove_old_journals(cls, journal_dir):
        """By default creating a replacement journal will remove all but
        the last 10 journals. Otherwise space consumption could get
        huge after long usage.
        """
        try:
            mtimes_and_journal_ids = [
                (os.stat(p).st_mtime, p[8:-7])
                for p in glob(join(journal_dir, "journal-*.pickle"))
            ]
            mtimes_and_journal_ids.sort()
            for mtime, id in mtimes_and_journal_ids[:-cls.NUM_JOURNALS_TO_KEEP]:
                log.debug("rm old journal `%s'", id)
                for path in glob(join(journal_dir, "*-%s.*" % id)):
                    os.remove(path)
        except EnvironmentError, ex:
            log.warn("error removing old journals: %s (ignored)", ex)

    @classmethod
    def journals(cls):
        """Generate the list of current journals.

        Yields tuples of the form (most recent first):
            (<mtime>, <id>, <summary>)
        """
        journal_dir = cls.get_journal_dir()
        mtimes_and_paths = [
            (os.stat(p).st_mtime, p)
            for p in glob(join(journal_dir, "journal-*.pickle"))
        ]
        mtimes_and_paths.sort(reverse=True)

        for mtime, path in mtimes_and_paths:
            id = basename(path)[8:-7]  # len("journal") == 8, ...
            summary_path = join(dirname(path), "summary-%s.txt" % id)
            try:
                f = codecs.open(summary_path, 'r', "utf-8")
                summary = f.read()
                f.close()
            except EnvironmentError:
                summary = "(no summary)"
            yield mtime, id, summary

    @classmethod
    def create(cls, summary):
        journal_dir = cls.get_journal_dir()
        if not exists(journal_dir):
            os.makedirs(journal_dir)
        else:
            cls.remove_old_journals(journal_dir)

        id = cls.get_new_id(journal_dir)
        path = join(journal_dir, "journal-%s.pickle" % id)

        summary_path = join(journal_dir, "summary-%s.txt" % id)
        f = codecs.open(summary_path, 'w', "utf-8")
        try:
            f.write(summary)
        finally:
            f.close()

        file = open(path, 'wb')
        instance = cls(id, path, file)
        instance.summary_path = summary_path
        instance.summary = summary
        return instance

    @classmethod
    def load(cls, path_or_id):
        if os.sep in path_or_id or os.altsep and os.altsep in path_or_id:
            path = path_or_id
            id = basename(path_or_id)[8:-7]
        else:
            id = path_or_id
            journal_dir = cls.get_journal_dir()
            path = join(journal_dir, "journal-%s.pickle" % id)

        summary_path = join(journal_dir, "summary-%s.txt" % id)
        f = codecs.open(summary_path, 'r', "utf-8")
        try:
            summary = f.read()
        finally:
            f.close()

        file = open(path, 'rb')
        instance = cls(id, path, file)
        instance.summary_path = summary_path
        instance.summary = summary
        try:
            instance += pickle.load(file)
        finally:
            file.close()
        return instance

    def __init__(self, id, path, file):
        list.__init__(self)
        self.id = id
        self.path = path
        self.file = file

    def __del__(self):
        self.close()

    def add_replace_group(self, group):
        #TODO: Do I need eol-style here as well? Yes, I think so. Add a
        #      test case for this!
        self.append(group)

    def close(self):
        if not self.file.closed:
            # Dump data to pickle.
            pickle.dump(list(self), self.file)
            self.file.close()


#---- internal hit classes

class _memoized(object):
   """Decorator that caches a function's return value each time it is called.
   If called later with the same arguments, the cached value is returned, and
   not re-evaluated.

   http://wiki.python.org/moin/PythonDecoratorLibrary
   """
   def __init__(self, func):
      self.func = func
      self.cache = {}
   def __call__(self, *args):
      try:
         return self.cache[args]
      except KeyError:
         self.cache[args] = value = self.func(*args)
         return value
      except TypeError:
         # uncachable -- for instance, passing a list as an argument.
         # Better to not cache than to blow up entirely.
         return self.func(*args)
   def __repr__(self):
      """Return the function's docstring."""
      return self.func.__doc__

class Event(object):
    pass

class SkipBinaryPath(Event):
    """Event yielded when skipping a binary path during grep() or replace()."""
    def __init__(self, path):
        self.path = path
    def __repr__(self):
        return "<SkipBinaryPath %s>" % self.path

class SkipUnknownLangPath(Event):
    """Event yielded when skipping a path because its lang could not be
    identified.
    """
    def __init__(self, path):
        self.path = path
    def __repr__(self):
        return "<SkipUnknownLangPath %s>" % self.path

class ReplaceDiff(Event):
    """Event giving the diff for an impending replacement."""
    def __init__(self, path, diff):
        self.path = path
        self.diff = diff
    def __repr__(self):
        return "<ReplaceDiff %s>" % self.path

class StartJournal(Event):
    """Event signalling the creation of a replacement journal."""
    def __init__(self, id):
        self.id = id
    def __repr__(self):
        return "<StartJournal %s>" % self.id

class Hit(Event):
    path = None

class PathHit(Hit):
    def __init__(self, path):
        self.path = path

class _HitWithAccessorMixin(object):
    """Provide some utilities for getting text context information given
    a `self.accessor'.
    """
    @property
    @_memoized
    def line_num_range(self):
        start = self.accessor.line_from_pos(self.start_pos)
        end   = self.accessor.line_from_pos(self.end_pos)
        return start, end

    @property
    @_memoized
    def line_and_col_num_range(self):
        start = self.accessor.line_and_col_from_pos(self.start_pos)
        end   = self.accessor.line_and_col_from_pos(self.end_pos)
        return start, end

    @property
    def lines(self):
        start, end = self.line_num_range
        for line_num in range(start, end+1):
            start_pos = self.accessor.pos_from_line_and_col(line_num, 0)
            end_pos = self.accessor.pos_from_line_and_col(line_num+1, 0)
            yield self.accessor.text_range(start_pos, end_pos)

    def lines_with_context(self, n):
        start, end = self.line_num_range
        context_start = max(0, start - n)
        context_end   = max(0, end + n)
        for line_num in range(context_start, context_end+1):
            type = (start <= line_num <= end and "hit" or "context")
            start_pos = self.accessor.pos_from_line_and_col(line_num, 0)
            end_pos = self.accessor.pos_from_line_and_col(line_num+1, 0)
            yield type, self.accessor.text_range(start_pos, end_pos)


class FindHit(Hit, _HitWithAccessorMixin):
    def __init__(self, path, encoding, match, accessor):
        self.path = path
        self.encoding = encoding
        self.match = match
        self.accessor = accessor

    def __repr__(self):
        hit_summary = repr(self.match.group(0))
        if len(hit_summary) > 20:
            hit_summary = hit_summary[:16] + "...'"
        return "<FindHit %s at %s#%s>"\
               % (hit_summary, self.path, self.line_num_range[0]+1)

    @property
    def start_pos(self):
        return self.match.start()
    @property
    def end_pos(self):
        return self.match.end()


class ReplaceHit(Hit, _HitWithAccessorMixin):
    def __init__(self, path, before, after, start_pos, end_pos, start_line,
                 find_hit=None, accessor=None):
        self.path = path
        self.before = before
        self.after = after
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.start_line = start_line

        # These will be None for ReplaceHits restore from a journal.
        self.find_hit = find_hit
        self.accessor = accessor

    def __getstate__(self):
        """Don't pickle some attrs."""
        d = self.__dict__.copy()
        del d["find_hit"]
        del d["accessor"]
        return d

    def __repr__(self):
        before_summary = repr(self.before)
        if len(before_summary) > 20:
            before_summary = before_summary[:16] + "...'"
        after_summary = repr(self.after)
        if len(after_summary) > 20:
            after_summary = after_summary[:16] + "...'"
        return "<ReplaceHit %s -> %s at %s#%s>" \
               % (before_summary, after_summary, self.path, self.start_line+1)

class ReplaceHitGroup(Hit):
    """A group of ReplaceHit's for a single path."""
    def __init__(self, path, encoding, before_md5sum, after_md5sum,
                 replace_hits):
        self.path = abspath(path)           # Need abspath for journal for undo.
        self.encoding = encoding
        self.before_md5sum = before_md5sum  # MD5 of path before replacements
        self.after_md5sum = after_md5sum    # MD5 of path after replacements
        self.replace_hits = replace_hits

    def __repr__(self):
        return "<ReplaceHitGroup %s (%d replacements)>" \
               % (self.nicepath, len(self.replace_hits))

    @property
    def nicepath(self):
        r = _relpath(self.path)
        a = self.path
        if not sys.platform == "win32":
            home = os.environ["HOME"]
            if a.startswith(home):
                a = "~" + a[len(home):]
        if len(r) < len(a):
            return r
        else:
            return a


#---- internal accessor stuff

class _TextAccessor(object):
    """An API for accessing some text (allowing for a nicer API and cachine).

    This is based on codeintel's accessor classes, but drops the lexing info
    and is otherwise simplified.
    """
    def __init__(self, text):
        self.text = text

    def line_and_col_from_pos(self, pos):
        #TODO: Fix this. This is busted for line 0 (at least).
        line = self.line_from_pos(pos)
        col = pos - self.__start_pos_from_line[line]
        return line, col
    
    __start_pos_from_line = None
    def line_from_pos(self, pos):
        r"""
            >>> sa = _TextAccessor(
            ...         #0         1           2         3
            ...         #01234567890 123456789 01234567890 12345
            ...         'import sys\nif True:\nprint "hi"\n# bye')
            >>> sa.line_from_pos(0)
            0
            >>> sa.line_from_pos(9)
            0
            >>> sa.line_from_pos(10)
            0
            >>> sa.line_from_pos(11)
            1
            >>> sa.line_from_pos(22)
            2
            >>> sa.line_from_pos(34)
            3
            >>> sa.line_from_pos(35)
            3
        """
        # Lazily build the line -> start-pos info.
        if self.__start_pos_from_line is None:
            self.__start_pos_from_line = [0]
            for line_str in self.text.splitlines(True):
                self.__start_pos_from_line.append(
                    self.__start_pos_from_line[-1] + len(line_str))

        # Binary search for line number.
        lower, upper = 0, len(self.__start_pos_from_line)
        sentinel = 25
        while sentinel > 0:
            line = ((upper - lower) / 2) + lower
            #print "LINE %d: limits=(%d, %d) start-pos=%d (sentinel %d)"\
            #      % (line, lower, upper, self.__start_pos_from_line[line], sentinel)
            if pos < self.__start_pos_from_line[line]:
                upper = line
            elif line+1 == upper or self.__start_pos_from_line[line+1] > pos:
                return line
            else:
                lower = line
            sentinel -= 1
        else:
            raise FindError("line_from_pos binary search sentinel hit: there "
                            "is likely a logic problem here!")

    def pos_from_line_and_col(self, line, col):
        if not self.__start_pos_from_line:
            self.line_from_pos(len(self.text)) # force init
        return self.__start_pos_from_line[line] + col

    def text_range(self, start, end):
        return self.text[start:end]



#---- internal support stuff

def _grouped_by_path(events):
    """Group "Hit" events in the given find event stream by path
    
    Non-Hits are in their own group. Hits are grouped by path. 
    """
    group_path = None
    group = []  # group of FindHits for a single path

    for event in events:
        if not isinstance(event, Hit):
            if group:
                yield group
                group_path = None
                group = []
            yield [event]
            continue

        if group_path is None:
            group_path = event.path
            group = []
        elif event.path != group_path:
            yield group
            group_path = event.path
            group = []
        group.append(event)

    if group:
        yield group

def _get_friendly_id():
    """Create an ID string we can recognise.
    (Think Italian or Japanese or Native American.)

    from http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/526619
    """
    from random import choice
    v = 'aeiou'
    c = 'bdfghklmnprstvw'
    
    return ''.join([choice(v if i%2 else c) for i in range(8)])


# Recipe: relpath (0.2)
def _relpath(path, relto=None):
    """Relativize the given path to another (relto).

    "relto" indicates a directory to which to make "path" relative.
        It default to the cwd if not specified.
    """
    if not os.path.isabs(path):
        path = os.path.abspath(path)
    if relto is None:
        relto = os.getcwd()
    else:
        relto = os.path.abspath(relto)

    if sys.platform.startswith("win"):
        def _equal(a, b): return a.lower() == b.lower()
    else:
        def _equal(a, b): return a == b

    pathDrive, pathRemainder = os.path.splitdrive(path)
    if not pathDrive:
        pathDrive = os.path.splitdrive(os.getcwd())[0]
    relToDrive, relToRemainder = os.path.splitdrive(relto)
    if not _equal(pathDrive, relToDrive):
        # Which is better: raise an exception or return ""?
        return ""
        #raise OSError("Cannot make '%s' relative to '%s'. They are on "\
        #              "different drives." % (path, relto))

    pathParts = _splitall(pathRemainder)[1:] # drop the leading root dir
    relToParts = _splitall(relToRemainder)[1:] # drop the leading root dir
    #print "_relpath: pathPaths=%s" % pathParts
    #print "_relpath: relToPaths=%s" % relToParts
    for pathPart, relToPart in zip(pathParts, relToParts):
        if _equal(pathPart, relToPart):
            # drop the leading common dirs
            del pathParts[0]
            del relToParts[0]
    #print "_relpath: pathParts=%s" % pathParts
    #print "_relpath: relToParts=%s" % relToParts
    # Relative path: walk up from "relto" dir and walk down "path".
    relParts = [os.curdir] + [os.pardir]*len(relToParts) + pathParts
    #print "_relpath: relParts=%s" % relParts
    relPath = os.path.normpath( os.path.join(*relParts) )
    return relPath


# Recipe: splitall (0.2)
def _splitall(path):
    r"""Split the given path into all constituent parts.

    Often, it's useful to process parts of paths more generically than
    os.path.split(), for example if you want to walk up a directory.
    This recipe splits a path into each piece which corresponds to a
    mount point, directory name, or file.

    (From the Python Cookbook, Files section, Recipe 99.)
    """
    allparts = []
    while 1:
        parts = os.path.split(path)
        if parts[0] == path:  # sentinel for absolute paths
            allparts.insert(0, parts[0])
            break
        elif parts[1] == path: # sentinel for relative paths
            allparts.insert(0, parts[1])
            break
        else:
            path = parts[0]
            allparts.insert(0, parts[1])
    allparts = [p for p in allparts if p] # drop empty strings 
    return allparts


# Recipe: regex_from_str (2.1.0)
def _str_from_regex_info(regex, repl=None):
    r"""Generate a string representing the regex (and optional replacement).

        >>> _str_from_regex_info(re.compile('foo'))
        '/foo/'
        >>> _str_from_regex_info(re.compile('foo', re.I))
        '/foo/i'
        >>> _str_from_regex_info(re.compile('foo'), 'bar')
        's/foo/bar/'
        >>> _str_from_regex_info(re.compile('foo/bar', re.M), 'bar')
        's/foo\\/bar/bar/m'

    Note: this is intended to round-trip with _regex_info_from_str().
    """
    ch_from_flag = {
        re.IGNORECASE: "i",
        re.LOCALE: "l",
        re.DOTALL: "s",
        re.MULTILINE: "m",
        re.UNICODE: "u",
    }
    def _str_from_flags(flags):
        if not flags:
            return ""
        chars = []
        for flag, ch in ch_from_flag.items():
            if flags & flag:
                chars.append(ch)
        chars.sort()
        return ''.join(chars)
    def _escape(s):
        return s.replace('/', r'\/')

    pattern = _escape(regex.pattern)
    flags_str = _str_from_flags(regex.flags)
    if repl is None:
        s = "/%s/%s" % (pattern, flags_str)
    else:
        s = "s/%s/%s/%s" % (pattern, _escape(repl), flags_str)
    return s

def _regex_info_from_str(s, allow_replace=True, word_match=False):
    r"""Interpret a regex match or substitution string.

        >>> _regex_info_from_str("foo") \
        ...   == (re.compile('foo'), None)
        True
        >>> _regex_info_from_str("/foo/") \
        ...   == (re.compile('foo'), None)
        True
        >>> _regex_info_from_str("/foo/i") \
        ...   == (re.compile('foo', re.I), None)
        True
        >>> _regex_info_from_str("s/foo/bar/i") \
        ...   == (re.compile('foo', re.I), "bar")
        True

    The `word_match` boolean modifies the pattern to match at word
    boundaries.

        >>> _regex_info_from_str("/foo/", word_match=True) \
        ...   == (re.compile(r'(?<!\w)foo(?!\w)'), None)
        True

    Note: this is intended to round-trip with _str_from_regex_info().
    """
    flag_from_ch = {
        "i": re.IGNORECASE,
        "l": re.LOCALE,
        "s": re.DOTALL,
        "m": re.MULTILINE,
        "u": re.UNICODE,
    }
    def _flags_from_str(flags_str):
        flags = 0
        for ch in flags_str:
            try:
                flags |= flag_from_ch[ch]
            except KeyError:
                raise ValueError("unsupported regex flag: '%s' in '%s' "
                                 "(must be one of '%s')"
                                 % (ch, flags_str, ''.join(flag_from_ch.keys())))
        return flags

    if s.startswith('/') and s.rfind('/') != 0:
        # Parse it: /PATTERN/FLAGS
        idx = s.rfind('/')
        pattern, flags_str = s[1:idx], s[idx+1:]
        if word_match:
            # Komodo Bug 33698: "Match whole word" doesn't work as
            # expected Before this the transformation was "\bPATTERN\b"
            # where \b means:
            #   matches a boundary between a word char and a non-word char
            # However what is really wanted (and what VS.NET does) is to
            # match if there is NOT a word character to either immediate
            # side of the pattern.
            pattern = r"(?<!\w)" + pattern + r"(?!\w)"
        flags = _flags_from_str(flags_str)
        return (re.compile(pattern, flags), None)
    elif allow_replace and s.startswith("s/") and s.count('/') >= 3:
        # Parse it: s/PATTERN/REPL/FLAGS
        #TODO: test with '\' in pattern and repl
        repl_re = re.compile(r"^s/(.*?)(?<!\\)/(.*?)(?<!\\)/([ilsmu]*)$")
        m = repl_re.match(s)
        if not m:
            raise ValueError("invalid replacement syntax: %r" % s)
        pattern, repl, flags_str = m.groups()
        if word_match:
            pattern = r"(?<!\w)" + pattern + r"(?!\w)"
        flags = _flags_from_str(flags_str)
        return (re.compile(pattern, flags), repl)
    else: # not an encoded regex
        pattern = re.escape(s)
        if word_match:
            pattern = r"(?<!\w)" + pattern + r"(?!\w)"
        return (re.compile(pattern), None)


# Recipe: paths_from_path_patterns (0.3.7+)
def _should_include_path(path, includes, excludes):
    """Return True iff the given path should be included."""
    from os.path import basename
    from fnmatch import fnmatch

    base = basename(path)
    if includes:
        for include in includes:
            if fnmatch(base, include):
                try:
                    log.debug("include `%s' (matches `%s')", path, include)
                except (NameError, AttributeError):
                    pass
                break
        else:
            try:
                log.debug("exclude `%s' (matches no includes)", path)
            except (NameError, AttributeError):
                pass
            return False
    for exclude in excludes:
        if fnmatch(base, exclude):
            try:
                log.debug("exclude `%s' (matches `%s')", path, exclude)
            except (NameError, AttributeError):
                pass
            return False
    return True

_NOT_SPECIFIED = ("NOT", "SPECIFIED")
def _paths_from_path_patterns(path_patterns, files=True, dirs="never",
                              recursive=True, includes=[], excludes=[],
                              on_error=_NOT_SPECIFIED):
    """_paths_from_path_patterns([<path-patterns>, ...]) -> file paths

    Generate a list of paths (files and/or dirs) represented by the given path
    patterns.

        "path_patterns" is a list of paths optionally using the '*', '?' and
            '[seq]' glob patterns.
        "files" is boolean (default True) indicating if file paths
            should be yielded
        "dirs" is string indicating under what conditions dirs are
            yielded. It must be one of:
              never             (default) never yield dirs
              always            yield all dirs matching given patterns
              if-not-recursive  only yield dirs for invocations when
                                recursive=False
            See use cases below for more details.
        "recursive" is boolean (default True) indicating if paths should
            be recursively yielded under given dirs.
        "includes" is a list of file patterns to include in recursive
            searches.
        "excludes" is a list of file and dir patterns to exclude.
            (Note: This is slightly different than GNU grep's --exclude
            option which only excludes *files*.  I.e. you cannot exclude
            a ".svn" dir.)
        "on_error" is an error callback called when a given path pattern
            matches nothing:
                on_error(PATH_PATTERN)
            If not specified, the default is look for a "log" global and
            call:
                log.error("`%s': No such file or directory")
            Specify None to do nothing.

    Typically this is useful for a command-line tool that takes a list
    of paths as arguments. (For Unix-heads: the shell on Windows does
    NOT expand glob chars, that is left to the app.)

    Use case #1: like `grep -r`
      {files=True, dirs='never', recursive=(if '-r' in opts)}
        script FILE     # yield FILE, else call on_error(FILE)
        script DIR      # yield nothing
        script PATH*    # yield all files matching PATH*; if none,
                        # call on_error(PATH*) callback
        script -r DIR   # yield files (not dirs) recursively under DIR
        script -r PATH* # yield files matching PATH* and files recursively
                        # under dirs matching PATH*; if none, call
                        # on_error(PATH*) callback

    Use case #2: like `file -r` (if it had a recursive option)
      {files=True, dirs='if-not-recursive', recursive=(if '-r' in opts)}
        script FILE     # yield FILE, else call on_error(FILE)
        script DIR      # yield DIR, else call on_error(DIR)
        script PATH*    # yield all files and dirs matching PATH*; if none,
                        # call on_error(PATH*) callback
        script -r DIR   # yield files (not dirs) recursively under DIR
        script -r PATH* # yield files matching PATH* and files recursively
                        # under dirs matching PATH*; if none, call
                        # on_error(PATH*) callback

    Use case #3: kind of like `find .`
      {files=True, dirs='always', recursive=(if '-r' in opts)}
        script FILE     # yield FILE, else call on_error(FILE)
        script DIR      # yield DIR, else call on_error(DIR)
        script PATH*    # yield all files and dirs matching PATH*; if none,
                        # call on_error(PATH*) callback
        script -r DIR   # yield files and dirs recursively under DIR
                        # (including DIR)
        script -r PATH* # yield files and dirs matching PATH* and recursively
                        # under dirs; if none, call on_error(PATH*)
                        # callback
    """
    from os.path import basename, exists, isdir, join
    from glob import glob

    assert not isinstance(path_patterns, basestring), \
        "'path_patterns' must be a sequence, not a string: %r" % path_patterns
    GLOB_CHARS = '*?['

    for path_pattern in path_patterns:
        # Determine the set of paths matching this path_pattern.
        for glob_char in GLOB_CHARS:
            if glob_char in path_pattern:
                paths = glob(path_pattern)
                break
        else:
            paths = exists(path_pattern) and [path_pattern] or []
        if not paths:
            if on_error is None:
                pass
            elif on_error is _NOT_SPECIFIED:
                try:
                    log.error("`%s': No such file or directory", path_pattern)
                except (NameError, AttributeError):
                    pass
            else:
                on_error(path_pattern)

        for path in paths:
            if isdir(path):
                # 'includes' SHOULD affect whether a dir is yielded.
                if (dirs == "always"
                    or (dirs == "if-not-recursive" and not recursive)
                   ) and _should_include_path(path, includes, excludes):
                    yield path

                # However, if recursive, 'includes' should NOT affect
                # whether a dir is recursed into. Otherwise you could
                # not:
                #   script -r --include="*.py" DIR
                if recursive and _should_include_path(path, [], excludes):
                    for dirpath, dirnames, filenames in os.walk(path):
                        dir_indeces_to_remove = []
                        for i, dirname in enumerate(dirnames):
                            d = join(dirpath, dirname)
                            if dirs == "always" \
                               and _should_include_path(d, includes, excludes):
                                yield d
                            if not _should_include_path(d, [], excludes):
                                dir_indeces_to_remove.append(i)
                        for i in reversed(dir_indeces_to_remove):
                            del dirnames[i]
                        if files:
                            for filename in sorted(filenames):
                                f = join(dirpath, filename)
                                if _should_include_path(f, includes, excludes):
                                    yield f

            elif files and _should_include_path(path, includes, excludes):
                yield path

def _chomp(s):
    return s.rstrip('\r\n')

class _NoReflowFormatter(optparse.IndentedHelpFormatter):
    """An optparse formatter that does NOT reflow the description."""
    def format_description(self, description):
        return description or ""

# Recipe: pretty_logging (0.1) in C:\trentm\tm\recipes\cookbook
class _PerLevelFormatter(logging.Formatter):
    """Allow multiple format string -- depending on the log level.

    A "fmtFromLevel" optional arg is added to the constructor. It can be
    a dictionary mapping a log record level to a format string. The
    usual "fmt" argument acts as the default.
    """
    def __init__(self, fmt=None, datefmt=None, fmtFromLevel=None):
        logging.Formatter.__init__(self, fmt, datefmt)
        if fmtFromLevel is None:
            self.fmtFromLevel = {}
        else:
            self.fmtFromLevel = fmtFromLevel
    def format(self, record):
        record.lowerlevelname = record.levelname.lower()
        if record.levelno in self.fmtFromLevel:
            #XXX This is a non-threadsafe HACK. Really the base Formatter
            #    class should provide a hook accessor for the _fmt
            #    attribute. *Could* add a lock guard here (overkill?).
            _saved_fmt = self._fmt
            self._fmt = self.fmtFromLevel[record.levelno]
            try:
                return logging.Formatter.format(self, record)
            finally:
                self._fmt = _saved_fmt
        else:
            return logging.Formatter.format(self, record)

def _setup_logging(stream=None):
    """Do logging setup:

    We want a prettier default format:
         do: level: ...
    Spacing. Lower case. Skip " level:" if INFO-level. 
    """
    hdlr = logging.StreamHandler(stream)
    defaultFmt = "%(name)s: %(levelname)s: %(message)s"
    infoFmt = "%(message)s"
    fmtr = _PerLevelFormatter(fmt=defaultFmt,
                              fmtFromLevel={logging.INFO: infoFmt})
    hdlr.setFormatter(fmtr)
    logging.root.addHandler(hdlr)
    log.setLevel(logging.INFO)


def _optparse_undo_arg(option, opt_str, value, parser):
    """Add optparse option callback that will gobble the next token if
    it looks like an arg to -u|--undo (8 letter chars).

    Based on recipe zero_or_one_arg (0.1).

    After parsing, 'options.undo' will be:
        None        option was not specified
        True        option was specified, no argument
        <string>    option was specified, the value is the argument string
    """
    value = True
    if parser.rargs:
        arg = parser.rargs[0]
        if re.match("^[a-z]{8}$", arg):
            value = arg
            del parser.rargs[0]
    setattr(parser.values, option.dest, value)

def _safe_print(u):
    s = u.encode(sys.stdout.encoding or "utf-8", 'replace')
    print s

_bool_from_str = {
    "true": True, "True": True,
    "false": False, "False": False,
}
def _value_from_str(s):
    try:
        return int(s)
    except ValueError:
        if s in _bool_from_str:
            return _bool_from_str[s]
        else:
            return s


#---- mainline

def main_list_journals(opts):
    for mtime, id, summary in Journal.journals():
        dt = datetime.datetime.fromtimestamp(mtime)
        if log.isEnabledFor(logging.DEBUG):
            print "-- [%s, %s] %s" % (id, dt, summary)
            j = Journal.load(id)
            for replace_group in j:
                print repr(replace_group)
                for hit in replace_group.replace_hits:
                    print "  %r" % hit
        else:
            print "%s  %s (at %s)" % (id, summary, dt)

def main_find(paths, includes, excludes, opts):
    for path in find(paths, includes=includes, excludes=excludes):
        print path

def main_find_matching_files(regex, paths, includes, excludes, opts):
    for event in grep(regex, paths, files_with_matches=True,
                      includes=includes, excludes=excludes):
        if isinstance(event, Hit):
            print event.path

def main_grep(regex, paths, includes, excludes, opts):
    last_line_nums = None
    for hit in grep(regex, paths, includes=includes, excludes=excludes):
        if not isinstance(hit, Hit):
            continue

        # Skip reporting a hit if it is on a line (or lines) that
        # has already been printed (a la grep).
        start, end = hit.line_num_range
        line_nums = set(range(start, end+1))
        if last_line_nums and line_nums.issubset(last_line_nums):
            continue
        last_line_nums = line_nums

        lines = list(hit.lines)
        if len(lines) > 1:
            if opts.show_line_number:
                start, end = hit.line_num_range
                _safe_print("%s:%d-%d:" % (hit.path, start+1, end+1))
            else:
                _safe_print("%s:" % hit.path)
            for line in lines:
                _safe_print("  " + _chomp(line))
        else:
            if opts.show_line_number:
                _safe_print("%s:%d:%s" % (hit.path, hit.line_num_range[0]+1,
                                          _chomp(lines[0])))
            else:
                _safe_print("%s:%s" % (hit.path, _chomp(lines[0])))

def main_replace(regex, repl, paths, includes, excludes, argv, opts):
    start_time = time.time()
    num_repls = 0
    journal_id = None
    include_diff_events = log.isEnabledFor(logging.INFO-1) # if '-v|--verbose'
    dry_run_str = (opts.dry_run and " (dry-run)" or "")

    for event in replace(regex, repl, paths,
                         include_diff_events=include_diff_events,
                         includes=includes, excludes=excludes,
                         dry_run=opts.dry_run):
        if isinstance(event, StartJournal):
            journal_id = event.id
        elif isinstance(event, SkipUnknownLangPath):
            log.info("Skip `%s' (don't know language).", event.path)
        elif isinstance(event, ReplaceDiff) and event.diff:
            sys.stdout.write(event.diff)
        if not isinstance(event, Hit):
            continue
        assert isinstance(event, ReplaceHitGroup)

        num_repls += len(event.replace_hits)
        if not include_diff_events:
            s_str = (len(event.replace_hits) > 1 and "s" or "")
            log.info("%s: %s replacement%s%s", event.nicepath, 
                     len(event.replace_hits), s_str, dry_run_str)

    if num_repls:
        print
        if log.isEnabledFor(logging.DEBUG):
            s_str = (num_repls > 1 and "s" or "")
            log.debug("Completed %d replacement%s in %.2fs%s.", num_repls,
                      s_str, (time.time() - start_time), dry_run_str)
        if journal_id is not None:
            log.info("Use `%s --undo %s' to undo.", argv[0], journal_id)

def main_undo(opts):
    """Undo the given replacement."""
    dry_run_str = (opts.dry_run and " (dry-run)" or "")
    for event in undo_replace(opts.undo, dry_run=opts.dry_run):
        if not isinstance(event, Hit):
            continue
        assert isinstance(event, ReplaceHitGroup)
        s_str = (len(event.replace_hits) > 1 and "s" or "")
        log.info("%s: undo %s replacement%s%s",
                 event.nicepath, len(event.replace_hits), s_str, dry_run_str)


def main(argv):
    if "--test" in argv:  # Quick self-test.
        import doctest
        nerrors, ntests = doctest.testmod()
        return nerrors

    usage = "usage: %prog PATTERN FILES..."
    version = "%prog "+__version__
    parser = optparse.OptionParser(usage=usage,
        version=version, description=__doc__,
        formatter=_NoReflowFormatter())
    parser.add_option("-q", "--quiet", dest="log_level",
        action="store_const", const=logging.WARNING,
        help="quieter output")
    parser.add_option("-v", "--verbose", dest="log_level",
        action="store_const", const=logging.INFO-1,
        help="more verbose output")
    parser.add_option("-d", "--debug", dest="log_level",
        action="store_const", const=logging.DEBUG,
        help="verbose debugging output")
    parser.add_option("-w", "--word", action="store_true",
        help="restrict pattern match to whole words")
    parser.add_option("-l", "--list", action="store_true",
        help="list matching files (instead of the matches within them)")
#TODO: Need to handle grouping contiguous blocks for this. Use the
#      Provided hit.lines_with_context(n) for this.
#    parser.add_option("-C", "--context", type="int", metavar="NUM",
#         help="Print NUM lines of context.")
    parser.add_option("-r", "--recursive", action="store_true",
        help="find files recursively")
    parser.add_option("-n", dest="show_line_number", action="store_true",
        help="show line numbers for each hit")
    parser.add_option("-u", "--undo", metavar="[ID]", dest="undo",
        action="callback", callback=_optparse_undo_arg,
        help="Without an argument this will list replacements that can "
             "be undone (the last 5, most recent first). Specify a "
             "replacement id to undo it.")
    parser.add_option("-i", "--include", dest="includes",
        action="append", metavar="PATTERN",
        help="Path patterns to include. Alternatively, the argument can "
             "be of the form FIELD:VALUE to filter based on textinfo "
             "attributes of a file; for example, '-i lang:Python'.")
    parser.add_option("-x", "--exclude", dest="excludes",
        action="append", metavar="PATTERN",
        help="Path patterns to exclude. Alternatively, the argument can "
             "be of the form FIELD:VALUE to filter based on textinfo "
             "attributes of a file; for example, '-x encoding:ascii'.")
    parser.add_option("--dry-run", action="store_true",
        help="Do a dry-run replacement.")
    parser.set_defaults(log_level=logging.INFO, recursive=False,
        show_line_number=False, word=False, list=False, context=0,
        includes=[], excludes=[], dry_run=False)
    opts, args = parser.parse_args()
    log.setLevel(opts.log_level)

    # The -u|--undo actions don't use and args. Handle them first.
    if opts.undo is True:
        return main_list_journals(opts)
    elif opts.undo is not None:
        return main_undo(opts)

    # Process includes and excludes.
    path_includes = []
    textinfo_includes = []
    for i in opts.includes:
        if '=' in i:
            field, value = i.split('=', 1)
            textinfo_includes.append( (field, _value_from_str(value)) )
        elif ':' in i:
            field, value = i.split(':', 1)
            textinfo_includes.append( (field, _value_from_str(value)) )
        else:
            path_includes.append(i)
    path_excludes = []
    textinfo_excludes = []
    for i in opts.excludes:
        if '=' in i:
            field, value = i.split('=', 1)
            textinfo_excludes.append( (field, _value_from_str(value)) )
        elif ':' in i:
            field, value = i.split(':', 1)
            textinfo_excludes.append( (field, _value_from_str(value)) )
        else:
            path_excludes.append(i)

    # Validate and prepare the args.
    if len(args) < 1:
        log.error("incorrect number of arguments (see `%s --help')", argv[0])
        return 1
    elif len(args) == 1:
        # GNU find-like functionality uses one arg.
        action = "find"
        path_patterns = args
        recursive = True    # -r is implied for find functionality
    else:
        pattern_str, path_patterns = args[0], args[1:]
        regex, repl = _regex_info_from_str(pattern_str, word_match=opts.word)
        action = (repl is None and "grep" or "replace")
        if opts.list:
            if action == "replace":
                raise FindError("cannot use -l|--list for a replacement")
            action = "grep-list"
        recursive = opts.recursive

    # Dispatch to the appropriate action.
    paths = _paths_from_path_patterns(path_patterns, recursive=recursive,
                includes=path_includes, excludes=path_excludes)
    if action == "find":
        return main_find(paths, textinfo_includes, textinfo_excludes, opts)
    if action == "grep-list":
        return main_find_matching_files(regex, paths,
            textinfo_includes, textinfo_excludes, opts)
    elif action == "grep":
        return main_grep(regex, paths,
            textinfo_includes, textinfo_excludes, opts)
    elif action == "replace":
        return main_replace(regex, repl, paths,
            textinfo_includes, textinfo_excludes, argv, opts)
    else:
        raise FindError("unexpected action: %r" % action)


if __name__ == "__main__":
    _setup_logging()
    try:
        retval = main(sys.argv)
    except SystemExit:
        pass
    except KeyboardInterrupt:
        sys.exit(1)
    except:
        exc_info = sys.exc_info()
        if hasattr(exc_info[0], "__name__"):
            exc_class, exc, tb = exc_info
            exc_str = str(exc_info[1])
            sep = ('\n' in exc_str and '\n' or ' ')
            where_str = ""
            tb_path, tb_lineno, tb_func = traceback.extract_tb(tb)[-1][:3]
            in_str = (tb_func != "<module>"
                      and " in %s" % tb_func
                      or "")
            where_str = "%s(%s#%s%s)" % (sep, tb_path, tb_lineno, in_str)
            log.error("%s%s", exc_str, where_str)
        else:  # string exception
            log.error(exc_info[0])
        if log.isEnabledFor(logging.INFO-1):
            print
            traceback.print_exception(*exc_info)
        sys.exit(1)
    else:
        sys.exit(retval)

