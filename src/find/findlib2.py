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

"""A find/replace backend for Komodo."""

import os
from os.path import (expanduser, join, basename, exists, dirname,
                     abspath, isdir, islink, lexists, normpath, realpath)
import time
import sys
import re
import logging
import codecs
from glob import glob
import cPickle as pickle
from hashlib import md5
from pprint import pprint, pformat

try:
    from scandir import walk as os_walk
except (ImportError, IOError):
    logging.getLogger("findlib2").warn("Unable to import scandir - defaulting to os.walk")
    os_walk = os.walk

try:
    import textinfo
except ImportError:
    kopylib_dir = join(dirname(dirname(abspath(__file__))),
                       "python-sitelib")
    sys.path.insert(0, kopylib_dir)
    import textinfo
import difflibex

import warnings
warnings.simplefilter("ignore", textinfo.ChardetImportWarning) # bug 77562


#---- exceptions and globals

class FindError(Exception):
    pass

log = logging.getLogger("findlib2")
#log.setLevel(logging.DEBUG)



#---- primary API methods

def find(paths, includes=None, excludes=None, env=None):
    """List paths matching the given filters (a la GNU find).

    @param paths {sequence|iterator} is a sequence of paths to search.
    @param includes {list} is a sequence of 2-tuples defining include
        filters on textinfo data: (<textinfo-field>, <value>).
    @param excludes {list} is a sequence of 2-tuples defining exclude
        filters on textinfo data: (<textinfo-field>, <value>).
    @param env {runtime environment}
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
                    follow_symlinks=True,
                    quick_determine_lang=quick_determine_lang,
                    env=env)

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
         skip_filesizes_larger_than=None,
         first_on_line=False,
         includes=None, excludes=None,
         textInfoFactory=None,
         env=None):
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
    @param skip_filesizes_larger_than {int} in bytes, if set this is used
        to skip files that are larger in size than this value.
    @param first_on_line {boolean} A boolean indicating, if True, that only
        the first hit on a line should be replaced. Default is False. (This
        is to support Vi's replace with the 'g' flag.)
    @param includes {list} is a sequence of 2-tuples defining include
        filters on textinfo data: (<textinfo-field>, <value>).
    @param excludes {list} is a sequence of 2-tuples defining exclude
        filters on textinfo data: (<textinfo-field>, <value>).
    @param textInfoFactory {object}
        either a standard textinfo.TextInfo object, or a
        duck-type-equivalent object based on a loaded, modified document.
    @param env {runtime environment}
    """
    if log.isEnabledFor(logging.DEBUG):
        log.debug("grep %r", str_from_regex_info(regex))

    for path in paths:
        path = normpath(path)
        if skip_filesizes_larger_than:
            try:
                statinfo = os.stat(path)
                if statinfo.st_size > skip_filesizes_larger_than:
                    yield SkipLargeFilePath(path, statinfo.st_size)
                    continue
            except EnvironmentError, ex:
                yield SkipPath(path, "error determining file info: %s" % ex)
                continue
        try:
            if textInfoFactory:
                ti = textInfoFactory.init_from_path(path, follow_symlinks=True, env=env)
            else:
                ti = textinfo.TextInfo.init_from_path(path,
                        follow_symlinks=True, env=env)
                ti.is_loaded_path = False
        except EnvironmentError, ex:
            yield SkipPath(path, "error determining file info: %s" % ex)
            continue

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
            if ti.text is None:
                yield SkipPath(path, "couldn't decode '%s' text" % ti.encoding)
                continue
            text = ti.text
        elif treat_binary_files_as_text:
            f = open(path, 'rb')
            text = f.read()
            f.close()
        else:
            yield SkipBinaryPath(path)
            continue

        accessor = _TextAccessor(text)
        have_hits_in_path = False
        last_hit_line = None
        for match in find_all_matches(regex, text, start=0, end=None):
            if files_with_matches:
                yield PathHit(path)
                break
            hit = FindHit(path, ti, match, accessor)
            if first_on_line:
                line, _ = hit.line_num_range
                if line == last_hit_line:
                    continue
                last_hit_line = line
            yield hit
            have_hits_in_path = True
        if not have_hits_in_path:
            yield SkipNoHitsInPath(path)



def replace(regex, repl, paths,
            skip_filesizes_larger_than=None,
            first_on_line=False,
            includes=None, excludes=None,
            do_smart_replace=False,
            textInfoFactory=None,
            summary=None, env=None):
    """Make the given regex replacement in the given paths.

    This generates a stream of `Event`s. The main such event is
    `ReplaceHitGroup` which is a grouping of all replacements for a
    single path. **Note:** To actually make the change you must call
    `event.commit()` on these hits. This allows one to manage
    confirmation of replacements.
    
    Example usage:

        journal = None
        try:
            for event in replace2(re.compile('foo'), 'bar', ['blah.txt']):
                if isinstance(event, StartJournal):
                    journal = event.journal
                elif not isinstance(event, ReplaceHitGroup):
                    # "SkipPath" events are sent for files with no hits, etc.
                    log.debug(event)
                #... possibly confirm replacement with user
                event.commit()
        finally:
            journal.close()

    @param regex {regular expression} is the regex with which to search
    @param repl {string} is the replacement string
    @param paths {generator} is the list of paths to process
    @param skip_filesizes_larger_than {int} in bytes, if set this is used
        to skip files that are larger in size than this value.
    @param first_on_line {boolean} A boolean indicating, if True, that only
        the first hit on a line should be replaced. Default is False. (This
        is to support Vi's replace with the 'g' flag.)
    @param includes {list} is a sequence of 2-tuples defining include
        filters on textinfo data: (<textinfo-field>, <value>).
    @param excludes {list} is a sequence of 2-tuples defining exclude
        filters on textinfo data: (<textinfo-field>, <value>).
    @param textInfoFactory {object}
        returns either a standard textinfo.TextInfo object, or returns a
        duck-type-equivalent object based on a loaded, modified document.
    @param do_smart_replace {boolean}
        preserve case for initial cap match, and all-caps match
    @param summary {str} an optional summary string for the replacement
        journal.
    @param env {runtime environment}

    """
    journal = None
    grepper = grep(regex, paths, skip_unknown_lang_paths=True,
                   skip_filesizes_larger_than=skip_filesizes_larger_than,
                   first_on_line=first_on_line,
                   includes=includes, excludes=excludes,
                   textInfoFactory=textInfoFactory,
                   env=env)
    for fhits in grouped_by_path(grepper):
        if not isinstance(fhits[0], Hit):
            yield fhits[0]
            continue
        # 'fhits' is a list of FindHits for a single path.

        path = fhits[0].path
        encoding = fhits[0].encoding_with_bom
        
        # Calculate the change.
        before_text = fhits[0].accessor.text
        if first_on_line:
            # Need to manually calculate the change from each find hit.
            # Algoritm: Walk backwards through the find hits, appending
            #   unmodified-bit, replacement, unmodified-bit, ...
            # in reversed order, then reverse and join the pieces.
            # Perf notes:
            # (a) Building a list and joining once is much faster than
            #     joining a string many times.
            # (b) `lst.append(item)` is much faster than `lst.insert(0, item)`.
            bits = [] # list of tail-end bits of the file
            idx = len(before_text)
            for hit in reversed(fhits):
                bits.append(before_text[hit.end_pos:idx])
                expanded_repl = hit.match.expand(repl)
                if do_smart_replace:
                    bits.append(do_smart_conversion(expanded_repl, repl))
                else:
                    bits.append(expanded_repl)
                idx = hit.start_pos
            bits.append(before_text[:idx])
            after_text = ''.join(reversed(bits))
        else:
            if do_smart_replace:
                # The pattern was plain text, not a regex or glob, so we can
                # safely wrap it with parens. It might have \b wrappers,
                # but we can safely add capture-parens, so the split works
                fixed_regex = re.compile("(%s)" % regex.pattern, regex.flags)
                pieces = fixed_regex.split(before_text)
                final_pieces = []
                for before_part, matched_part in zip(pieces[0::2], pieces[1::2]):
                    final_pieces.append(before_part)
                    final_pieces.append(do_smart_conversion(matched_part, repl))
                final_pieces.append(pieces[-1])
                after_text = "".join(final_pieces)
            else:
                after_text = regex.sub(repl, before_text)
        if before_text == after_text:
            continue
            

        # If this is the first path, start the journal for this
        # replacment (for undo).
        if journal is None:
            if summary is None:
                summary = str_from_regex_info(regex, repl)
            journal = Journal.create(summary)
            yield StartJournal(journal)

        yield ReplaceHitGroup(regex, repl, 
                              path, encoding, before_text,
                              fhits, after_text, journal)


def undo_replace(journal_id, dry_run=False, loadedFileManager=None):
    """Undo the given replacement.

    For now the undo ability is the easy way out: it only works if none
    of the files in the replacement have been subsequently modified.

    Undo process:
    1. Get the journal (yields a LoadJournal event with the loaded
       journal).
    2. Ensure that none of the files to be reverted have been
       subsequently modified (via MD5 check).
    3. Undo each replacement (yields a JournalReplaceRecord event for
       each replacement).
    4. Sanity check that the undo works (can compare MD5 via journaled
       value).
    5. Remove the journal.

    TODO: Support undo on modified files if the subsequent modifications
          are not on the same lines as any of the replacements.
    TODO: (future) Support undo on subsequent modification, skipping only
          those lines where there are conflicts.
    """
    journal = Journal.load(journal_id)
    log.debug("undo replace `%s'", journal.id)
    yield LoadJournal(journal)

    # 2. Ensure can complete the undo.
    changed_paths = []

    if loadedFileManager is None:
        disk_based_groups = journal
        dirty_buffer_groups = []
    else:
        disk_based_groups = []
        dirty_buffer_groups = []
        for group in journal:
            if isinstance(group, JournalReplaceLoadedBufferRecord):
                dirty_buffer_groups.append(group)
            elif isinstance(group, JournalReplaceRecord):
                disk_based_groups.append(group)
            else:
                raise FindError("Unknown kind of group")
            
    for group in dirty_buffer_groups:
        if loadedFileManager.bufferHasChanged(group.path,
                                              group.after_md5sum):
            changed_paths.append(group.path)
    for group in disk_based_groups:
        f = open(group.path, 'rb') #TODO: handle path being missing
        bytes = f.read()
        f.close()
        md5sum = md5(bytes).hexdigest()
        if md5sum != group.after_md5sum:
            changed_paths.append(group.path)
    if changed_paths:
        raise FindError("Cannot undo replacement because the following "
                        "files have been subsequently modified: '%s'" 
                        % "', '".join(changed_paths))

    # 3. Undo each replacement.
    #TODO: Bullet-proof backups to '~/.frep/backups/<id>/<hash>' and
    #      restoration on any failure.
    paths_failing_sanity_check = []
    for group in dirty_buffer_groups:
        loadedFileManager.undoChanges(group.path)
        yield group
            
    for group in disk_based_groups:
        log.debug("undo changes to `%s'", group.path)
        f = codecs.open(group.path, 'rb', group.encoding)
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
        for hit in reversed(group.rhits):
            bits.append(text[hit.end_pos:idx])
            bits.append(hit.before)
            idx = hit.start_pos
        bits.append(text[:idx])
        text = ''.join(reversed(bits))

        # 4. Sanity check.
        bytes = text.encode(group.encoding)
        md5sum = md5(bytes).hexdigest()
        log.debug("undo md5 check: before=%s, after undo=%s",
                  group.before_md5sum, md5sum)
        if md5sum != group.before_md5sum:
            paths_failing_sanity_check.append(group.path)

        # Write out the reverted content.
        if not dry_run:
            f = open(group.path, 'wb')
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


#---- public API functions the generally deal in re MatchObject's

def find_all_matches(regex, text, start=0, end=None):
    """Generate a regex `MatchObject` for each match of `regex` in the
    given `text`.
    """
    if end is None:
        end = len(text)
    while True:
        match = regex.search(text, start, end)
        if match:
            yield match
            if match.start() - match.end() == 0:
                start = match.end() + 1
                if start > end:
                    break
            else:
                start = match.end()
        else:
            break

def find_all_matches_bwd(regex, text, start=0, end=None):
    """Generate a regex `MatchObject` for each match of `regex` in the
    given `text` *backwards* from `end` to `start`.
    """
    matches = [m for m in find_all_matches(regex, text, start, end)]
    for match in reversed(matches):
        yield match


#---- event/hit class hierarchy
# In general the primary methods (grep(), find(), replace()) generate
# a stream of Event subclass instances. The general hierarchy is:
#
#   Event               # virtual base class
#       Hit             # base class for a "hit", i.e. found something
#           FindHit
#           ReplaceHit
#           ...
#       # Other non-hit events.
#       SkipPath
#       StartJournal

def grouped_by_path(events):
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



class Event(object):
    pass

class SkipPath(Event):
    def __init__(self, path, reason):
        self.path = path
        self.reason = reason
    def __repr__(self):
        SUMMARY_LEN = 40
        reason_summary = self.reason
        if len(reason_summary) > SUMMARY_LEN:
            reason_summary = reason_summary[:SUMMARY_LEN-3] + "..."
        return "<SkipPath %s (%s)>" % (self.path, reason_summary)
    def __str__(self):
        SUMMARY_LEN = 40
        reason_summary = self.reason
        if len(reason_summary) > SUMMARY_LEN:
            reason_summary = reason_summary[:SUMMARY_LEN-3] + "..."
        return "skipped `%s' (%s)" % (self.path, reason_summary)

class SkipBinaryPath(SkipPath):
    """Event yielded when skipping a binary path during grep() or replace()."""
    def __init__(self, path):
        SkipPath.__init__(self, path, "binary")

class SkipUnknownLangPath(SkipPath):
    """Event yielded when skipping a path because its lang could not be
    identified.
    """
    def __init__(self, path):
        SkipPath.__init__(self, path, "unknown language")

class SkipLargeFilePath(SkipPath):
    """Event yielded when skipping a path because its filesize is too large."""
    def __init__(self, path, size):
        SkipPath.__init__(self, path, "too large: %d bytes" % (size))
        self.size = size

class SkipNoHitsInPath(SkipPath):
    """Event yielded when skipping a path with no hits during grep()
    or replace().
    """
    def __init__(self, path):
        SkipPath.__init__(self, path, "no hits")

class ReplaceDiff(Event):
    """Event giving the diff for an impending replacement."""
    def __init__(self, path, diff):
        self.path = path
        self.diff = diff
    def __repr__(self):
        return "<ReplaceDiff %s>" % self.path

class StartJournal(Event):
    """Event signalling the creation of a replacement journal."""
    def __init__(self, journal):
        self.journal = journal
    def __repr__(self):
        return "<StartJournal %s>" % self.journal.id

class LoadJournal(Event):
    """First event emitted by undo_replace() after load of the journal."""
    def __init__(self, journal):
        self.journal = journal
    def __repr__(self):
        return "<LoadJournal %s>" % self.journal.id
    

class Hit(Event):
    path = None

class PathHit(Hit):
    def __init__(self, path):
        self.path = path

class _HitWithAccessorMixin(object):
    """Provide some utilities for getting text context information given
    a `self.accessor'.
    """
    __line_num_range_cache = None
    @property
    def line_num_range(self):
        if self.__line_num_range_cache is None:
            start = self.accessor.line_from_pos(self.start_pos)
            end   = self.accessor.line_from_pos(self.end_pos)
            self.__line_num_range_cache = (start, end)
        return self.__line_num_range_cache

    __line_and_col_num_range_cache = None
    @property
    def line_and_col_num_range(self):
        if self.__line_and_col_num_range_cache is None:
            start = self.accessor.line_and_col_from_pos(self.start_pos)
            end   = self.accessor.line_and_col_from_pos(self.end_pos)
            self.__line_and_col_num_range_cache = (start, end)
        return self.__line_and_col_num_range_cache

    __start_line_and_col_num_cache = None
    @property
    def start_line_and_col_num(self):
        if self.__start_line_and_col_num_cache is None:
            self.__start_line_and_col_num_cache \
                = self.accessor.line_and_col_from_pos(self.start_pos)
        return self.__start_line_and_col_num_cache

    @property
    def lines(self):
        start, end = self.line_num_range
        for line_num in range(start, end+1):
            start_pos = self.accessor.pos_from_line_and_col(line_num, 0)
            try:
                end_pos = self.accessor.pos_from_line_and_col(line_num+1, 0)
            except IndexError:
                end_pos = len(self.accessor.text)
            yield self.accessor.text_range(start_pos, end_pos)

    def lines_with_context(self, n):
        start, end = self.line_num_range
        context_start = max(0, start - n)
        context_end   = max(0, end + n)
        for line_num in range(context_start, context_end+1):
            type = (start <= line_num <= end and "hit" or "context")
            start_pos = self.accessor.pos_from_line_and_col(line_num, 0)
            try:
                end_pos = self.accessor.pos_from_line_and_col(line_num+1, 0)
            except IndexError:
                end_pos = len(self.accessor.text)
            yield type, self.accessor.text_range(start_pos, end_pos)


class FindHit(Hit, _HitWithAccessorMixin):
    def __init__(self, path, textInfo, match, accessor):
        self.path = path
        self.textInfo = textInfo
        self.match = match
        self.accessor = accessor

    def __repr__(self):
        hit_summary = repr(self.match.group(0))
        if len(hit_summary) > 20:
            hit_summary = hit_summary[:16] + "...'"
        return "<FindHit %s at %s#%s>"\
               % (hit_summary, self.path, self.line_num_range[0]+1)

    @property
    def encoding(self):
        # bug 93985 -- this method currently not used, but available for
        # any future use. Arguably we should drop this, and just
        # return encoding_with_bom
        return self.textInfo.encoding

    @property
    def encoding_with_bom(self):
        _encoding = self.textInfo.encoding
        # bug 93985 -- make sure we preserve the BOM for utf-8 files with BOM
        if _encoding == "utf-8" and self.textInfo.has_bom:
            return "utf-8-sig"
        else:
            return _encoding

    @property
    def is_loaded_path(self):
        return self.textInfo.is_loaded_path

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

    def cull_mem(self):
        """Can be called with done with the line/col calculation-related
        methods on this object. It will release some of the larger memory
        consumption for this object.
        
        This can be useful to keep memory usage low for a large replace
        operation over many many files.
        """
        del self.find_hit
        del self.accessor
    
    def __getstate__(self):
        """Don't pickle some attrs."""
        d = self.__dict__.copy()
        try:
            del d["find_hit"]
        except KeyError:
            pass
        try:
            del d["accessor"]
        except KeyError:
            pass
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

class ChangeHit(object):
    def __init__(self, findHit, replaceHit):
        self.start_pos = findHit.start_pos
        self.end_pos = findHit.end_pos
        self.start_line = replaceHit.start_line
        self.before = replaceHit.before
        self.after = replaceHit.after

class ReplaceHitGroup(Hit):
    """A group of ReplaceHit's for a single path. This class knows how
    to do the actual replacements on disk and to log to the replacement
    journal.
    """
    def __init__(self, regex, repl, path, encoding, before_text,
                 fhits, after_text, journal):
        self.regex = regex
        self.repl = repl
        self.path = abspath(path)           # Need abspath for journal for undo.
        self.encoding = encoding
        self.before_text = before_text
        self.fhits = fhits
        self.after_text = after_text
        self.journal = journal

        #self._calculated_rhits = False  # whether lazy calculations have been done

    def __repr__(self):
        return "<ReplaceHitGroup %s (%d replacements)>" \
               % (self.nicepath, self.length)

    @property
    def nicepath(self):
        r = _relpath(self.path)
        a = self.path
        if not sys.platform == "win32":
            home = os.environ["HOME"]
            if a.startswith(home + os.sep):
                a = "~" + a[len(home):]
        if len(r) < len(a):
            return r
        else:
            return a

    @property
    def length(self):
        return len(self.fhits)

    _diff_cache = None
    @property
    def diff(self):
        if self._diff_cache is None:
            diff_lines = ["Index: %s\n" % self.path]
            diff_lines += difflibex.unified_diff(
                    self.before_text.splitlines(1),
                    self.after_text.splitlines(1),
                    "%s (before)" % self.path,
                    "%s (after)" % self.path)
            self._diff_cache = ''.join(diff_lines)
        return self._diff_cache

    def commit(self, loadedFileManager=None):
        """Log changes to the journal and make the replacements."""
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
        #TODO: get before_md5sum from the TextInfo
        before_md5sum = md5(
            self.before_text.encode(self.encoding)).hexdigest()
        after_md5sum = md5(
            self.after_text.encode(self.encoding)).hexdigest()

        self.rhits = []
        accessor = _TextAccessor(self.after_text)
        pos_offset = 0
        line_offset = 0
        for fhit in self.fhits:
            m = fhit.match
            before = m.group(0)
            #TODO: Need to, at least, do EOL-normalization on 'after'.
            after = m.expand(self.repl)
            start_pos = fhit.start_pos + pos_offset
            pos_offset += len(after) - len(before)
            end_pos = fhit.end_pos + pos_offset
            start_line = fhit.line_num_range[0] + line_offset
            line_offset += after.count('\n') - before.count('\n')
            rhit = ReplaceHit(self.path, before, after,
                              start_pos, end_pos, start_line,
                              fhit, accessor)
            self.rhits.append(rhit)

        # Apply the changes.
        #TODO: catch any exception and restore file (or
        #      create a backup somewhere) if write fails
        if not self.fhits[0].is_loaded_path:
            self.journal.add_replace_group(self.path, self.encoding,
                                           before_md5sum, after_md5sum,
                                           self.rhits)
            f = codecs.open(self.path, 'wb', self.encoding)
            try:
                f.write(self.after_text)
            finally:
                f.close()
        else:
            if not loadedFileManager:
                raise FindError("Can't apply changes to loaded dirty file %s", self.path)
            changeHits = []
            for fhit, rhit in zip(self.fhits, self.rhits):
                changeHit = ChangeHit(fhit, rhit)
                changeHits.append(changeHit)
            self.journal.add_replace_loaded_file_group(self.path,
                                                       self.encoding,
                                                       before_md5sum, after_md5sum,
                                                       changeHits)
            loadedFileManager.applyChanges(self.path, self.after_text, changeHits)

    #TODO: Figure out how this works with the other data bits.
    #      E.g., do we calc the diff before caching?
    #def cache(self):
    #    """Can be called to have memory-heavy state be stored to a cache
    #    area and dropped.
    #    """



#---- replace journaling stuff

class JournalReplaceRecord(Event):
    """A record of a replacements to a single path in a Journal.
    
    These are pickled in a Journal and are used by `undo_replace()`.
    """
    def __init__(self, path, encoding, before_md5sum, after_md5sum,
                 rhits):
        self.path = abspath(path)           # Need abspath for journal for undo.
        self.encoding = encoding
        self.before_md5sum = before_md5sum  # MD5 of path before replacements
        self.after_md5sum = after_md5sum    # MD5 of path after replacements
        self.rhits = rhits

    def __repr__(self):
        return "<JournalReplaceRecord %s (%d replacements)>" \
               % (self.nicepath, len(self.rhits))

    @property
    def length(self):
        return len(self.rhits)

    @property
    def nicepath(self):
        r = _relpath(self.path)
        a = self.path
        if not sys.platform == "win32":
            home = os.environ["HOME"]
            if a.startswith(home + os.sep):
                a = "~" + a[len(home):]
        if len(r) < len(a):
            return r
        else:
            return a

class JournalReplaceLoadedBufferRecord(JournalReplaceRecord):
    pass

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

    _journal_dir = None
    @classmethod
    def set_journal_dir(cls, dir):
        """Call this to configure where the Journal class stores
        journals.
        """
        cls._journal_dir = dir

    @classmethod
    def get_journal_dir(cls):
        if cls._journal_dir is None:
            try:
                import applib
            except ImportError:
                d = expanduser("~/.findlib2")
            else:
                d = applib.user_cache_dir("findlib2", "ActiveState")
            cls._journal_dir = d
        return cls._journal_dir

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
        the last {NUM_JOURNALS_TO_KEEP} journals.
        Otherwise space consumption could get huge after long usage.
        """
        try:
            prefix_len = len(join(journal_dir, "journal-"))
            suffix_len = len(".pickle")
            mtimes_and_journal_ids = [
                (os.stat(p).st_mtime, p[prefix_len:-suffix_len])
                for p in glob(join(journal_dir, "journal-*.pickle"))
            ]
            mtimes_and_journal_ids.sort()
            for mtime, id in mtimes_and_journal_ids[:-cls.NUM_JOURNALS_TO_KEEP]:
                jpath = join(journal_dir, "journal-%s.pickle" % (id,))
                log.debug("rm old journal %s", jpath)
                try:
                    os.remove(jpath)
                except:
                    log.error("Can't remove journal %s", jpath)
                spath = join(journal_dir, "summary-%s.txt" % (id,))
                log.debug("rm old summary %s", spath)
                try:
                    os.remove(spath)
                except:
                    log.error("Can't remove remove %s", spath)
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

    def add_replace_group(self, path, encoding, before_md5sum, after_md5sum, 
                          rhits):
        #TODO: Do I need eol-style here as well? Yes, I think so. Add a
        #      test case for this!
        record = JournalReplaceRecord(path, encoding, before_md5sum,
                                      after_md5sum, rhits)
        self.append(record)

    def add_replace_loaded_file_group(self, path, encoding,
                                      before_md5sum, after_md5sum, 
                                      changeHits):
        #TODO: Do I need eol-style here as well? Yes, I think so. Add a
        #      test case for this!
        record = JournalReplaceLoadedBufferRecord(path, encoding, before_md5sum,
                                                  after_md5sum, changeHits)
        self.append(record)

    def close(self):
        if not self.file.closed:
            if len(self):
                # Dump data to pickle.
                pickle.dump(list(self), self.file)
                self.file.close()
            else:
                self.file.close()
                _rm(self.path)
                _rm(self.summary_path)


#---- more generic utils

def _rm(path, log=None):
    """Forcefully and silently remove the given file, if can."""
    if log:
        log("rm `%s'", path)
    if not exists(path):
        return
    try:
        os.remove(path)
    except EnvironmentError:
        pass

# Recipe: regex_from_str (2.2.1)
def str_from_regex_info(regex, repl=None):
    r"""Generate a string representing the regex (and optional replacement).

        >>> str_from_regex_info(re.compile('foo'))
        '/foo/'
        >>> str_from_regex_info(re.compile('foo', re.I))
        '/foo/i'
        >>> str_from_regex_info(re.compile('foo'), 'bar')
        's/foo/bar/'
        >>> str_from_regex_info(re.compile('foo/bar', re.M), 'bar')
        's/foo\\/bar/bar/m'

    Note: this is intended to round-trip with regex_info_from_str().
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

def regex_info_from_str(s, allow_replace=True, word_match=False,
                         universal_newlines=False):
    r"""Interpret a regex match or substitution string.

        >>> regex_info_from_str("foo") \
        ...   == (re.compile('foo'), None)
        True
        >>> regex_info_from_str("/foo/") \
        ...   == (re.compile('foo'), None)
        True
        >>> regex_info_from_str("/foo/i") \
        ...   == (re.compile('foo', re.I), None)
        True
        >>> regex_info_from_str("s/foo/bar/i") \
        ...   == (re.compile('foo', re.I), "bar")
        True

    The `word_match` boolean modifies the pattern to match at word
    boundaries.

        >>> regex_info_from_str("/foo/", word_match=True) \
        ...   == (re.compile(r'(?<!\w)foo(?!\w)'), None)
        True

    The `universal_newlines` boolean modifies the pattern such that the
    '$' anchor will match at '\r\n' and '\r'-style EOLs.
    
        >>> regex_info_from_str("/foo$/", universal_newlines=True) \
        ...   == (re.compile(r'foo(?=\r\n|(?<!\r)\n|\r(?!\n)|\Z)'), None)
        True
        >>> regex_info_from_str(r"/foo\$/", universal_newlines=True) \
        ...   == (re.compile(r'foo\$'), None)
        True
        >>> regex_info_from_str(r"/foo[$]/", universal_newlines=True) \
        ...   == (re.compile(r'foo[$]'), None)
        True

    Note: this is intended to round-trip with str_from_regex_info().
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

    plain = False
    if s.startswith('/') and s.rfind('/') != 0:
        # Parse it: /PATTERN/FLAGS
        idx = s.rfind('/')
        pattern, flags_str = s[1:idx], s[idx+1:]
        flags = _flags_from_str(flags_str)
        repl = None
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
    else: # not an encoded regex
        plain = True
        pattern = re.escape(s)
        if word_match:
            pattern = r"(?<!\w)" + pattern + r"(?!\w)"
        flags = 0
        repl = None
    
    if not plain:
        if word_match:
            # Komodo Bug 33698: "Match whole word" doesn't work as
            # expected Before this the transformation was "\bPATTERN\b"
            # where \b means:
            #   matches a boundary between a word char and a non-word char
            # However what is really wanted (and what VS.NET does) is to
            # match if there is NOT a word character to either immediate
            # side of the pattern.
            pattern = r"(?<!\w)" + pattern + r"(?!\w)"
        if universal_newlines and '$' in pattern:
            # Modifies the pattern such that the '$' anchor will match
            # at '\r\n' and '\r'-style EOLs. To do this we replace
            # occurrences '$' with a pattern that properly matches all
            # EOL styles, being careful to skip escaped dollar signs.
            chs = []
            STATE_DEFAULT, STATE_ESCAPE, STATE_CHARCLASS = range(3)
            state = STATE_DEFAULT
            for ch in pattern:
                chs.append(ch)
                if state == STATE_DEFAULT:
                    if ch == '\\':
                        state = STATE_ESCAPE
                    elif ch == '$':
                        chs[-1] = r"(?=\r\n|(?<!\r)\n|\r(?!\n)|\Z)"
                    elif ch == '[':
                        state = STATE_CHARCLASS
                elif state == STATE_ESCAPE:
                    state = STATE_DEFAULT
                elif state == STATE_CHARCLASS:
                    if ch == ']':
                        state = STATE_DEFAULT
            pattern = ''.join(chs)
    
    return (re.compile(pattern, flags), repl)


# Recipe: paths_from_path_patterns (0.5)
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

def _walk(top, topdown=True, onerror=None, follow_symlinks=False):
    """A version of `os.walk()` with a couple differences regarding symlinks.
    
    1. follow_symlinks=False (the default): A symlink to a dir is
       returned as a *non*-dir. In `os.walk()`, a symlink to a dir is
       returned in the *dirs* list, but it is not recursed into.
    2. follow_symlinks=True: A symlink to a dir is returned in the
       *dirs* list (as with `os.walk()`) but it *is conditionally*
       recursed into (unlike `os.walk()`).

    TODO: put as a separate recipe
    """
    from os.path import join, isdir, islink, abspath

    # We may not have read permission for top, in which case we can't
    # get a list of the files the directory contains.  os.path.walk
    # always suppressed the exception then, rather than blow up for a
    # minor reason when (say) a thousand readable directories are still
    # left to visit.  That logic is copied here.
    try:
        names = os.listdir(top)
    except OSError, err:
        if onerror is not None:
            onerror(err)
        return

    dirs, nondirs = [], []
    if follow_symlinks:
        for name in names:
            if isdir(join(top, name)):
                dirs.append(name)
            else:
                nondirs.append(name)
    else:
        for name in names:
            path = join(top, name)
            if islink(path):
                nondirs.append(name)
            elif isdir(path):
                dirs.append(name)
            else:
                nondirs.append(name)

    if topdown:
        yield top, dirs, nondirs
    for name in dirs:
        path = join(top, name)
        for x in os_walk(path, topdown, onerror, followlinks=follow_symlinks):
            yield x
    if not topdown:
        yield top, dirs, nondirs

_NOT_SPECIFIED = ("NOT", "SPECIFIED")
def paths_from_path_patterns(path_patterns, files=True, dirs="never",
                              recursive=True, includes=[], excludes=[],
                              skip_dupe_dirs=False,
                              follow_symlinks=False,
                              yield_structure=False,
                              on_error=_NOT_SPECIFIED):
    """paths_from_path_patterns([<path-patterns>, ...]) -> file paths

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
        "skip_dupe_dirs" can be set True to watch for and skip
            descending into a dir that has already been yielded.
        "follow_symlinks" is a boolean indicating whether to follow
            symlinks (default False). Use "skip_dupe_dirs" to guard
            against infinite loops with circular dir symlinks.
        "yield_structure" whether to yield entries the os.walk way (rather than
            one path at a time).
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

    TODO: perf improvements (profile, stat just once)
    """

    assert not isinstance(path_patterns, basestring), \
        "'path_patterns' must be a sequence, not a string: %r" % path_patterns
    GLOB_CHARS = '*?['

    if skip_dupe_dirs:
        searched_dirs = set()

    for path_pattern in path_patterns:
        # Determine the set of paths matching this path_pattern.
        for glob_char in GLOB_CHARS:
            if glob_char in path_pattern:
                paths = glob(path_pattern)
                break
        else:
            if follow_symlinks:
                paths = exists(path_pattern) and [path_pattern] or []
            else:
                paths = lexists(path_pattern) and [path_pattern] or []
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
            if (follow_symlinks or not islink(path)) and isdir(path):
                if skip_dupe_dirs:
                    canon_path = normpath(abspath(path))
                    if follow_symlinks:
                        canon_path = realpath(canon_path)
                    if canon_path in searched_dirs:
                        continue
                    else:
                        searched_dirs.add(canon_path)

                # 'includes' SHOULD affect whether a dir is yielded.
                if (dirs == "always"
                    or (dirs == "if-not-recursive" and not recursive)
                   ) and _should_include_path(path, includes, excludes):
                    if not yield_structure:
                        yield path

                # However, if recursive, 'includes' should NOT affect
                # whether a dir is recursed into. Otherwise you could
                # not:
                #   script -r --include="*.py" DIR
                if recursive and _should_include_path(path, [], excludes):
                    for dirpath, dirnames, filenames in os_walk(path,
                            followlinks=follow_symlinks):
                        _filenames = []
                        _dirnames = []
                        dir_indeces_to_remove = []
                        for i, dirname in enumerate(dirnames):
                            d = join(dirpath, dirname)
                            if skip_dupe_dirs:
                                canon_d = normpath(abspath(d))
                                if follow_symlinks:
                                    canon_d = realpath(canon_d)
                                if canon_d in searched_dirs:
                                    dir_indeces_to_remove.append(i)
                                    continue
                                else:
                                    searched_dirs.add(canon_d)
                            if dirs == "always" \
                               and _should_include_path(d, includes, excludes):
                                if yield_structure:
                                    _dirnames.append(dirname)
                                else:
                                    yield d
                            if not _should_include_path(d, [], excludes):
                                dir_indeces_to_remove.append(i)
                        for i in reversed(dir_indeces_to_remove):
                            del dirnames[i]
                        if files:
                            for filename in sorted(filenames):
                                f = join(dirpath, filename)
                                if _should_include_path(f, includes, excludes):
                                    if yield_structure:
                                        _filenames.append(filename)
                                    else:
                                        yield f

                    if yield_structure:
                        yield dirpath, _dirnames, _filenames

                elif not recursive:
                    _filenames = []
                    _dirnames = []
                    for filename in os.listdir(path):
                        filepath = os.path.join(path,filename)
                        if _should_include_path(filepath, includes, excludes):
                            filetype = "dir" if os.path.isdir(filepath) else "file"

                            if yield_structure:
                                if filetype is "dir":
                                    _dirnames.append(filename)
                                else:
                                    _filenames.append(filename)
                            else:
                                yield filepath

                    if yield_structure:
                        yield path, _dirnames, _filenames

            elif files and _should_include_path(path, includes, excludes):
                if not yield_structure:
                    yield path




#---- internal accessor stuff

class _TextAccessor(object):
    """An API for accessing some text (allowing for a nicer API and caching).

    This is based on codeintel's accessor classes, but drops the lexing info
    and is otherwise simplified.
    """
    def __init__(self, text):
        self.text = text

    def line_and_col_from_pos(self, pos):
        #TODO: Fix this. This is busted for line 0 (at least). Really?
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
        # Build the line -> start-pos info.
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


#TODO: Make a personal recipe of this.
def _get_friendly_id():
    """Create an ID string we can recognise.
    (Think Italian or Japanese or Native American.)

    from http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/526619
    """
    from random import choice
    v = 'aeiou'
    c = 'bdfghklmnprstvw'
    
    return ''.join([choice(v if i%2 else c) for i in range(8)])

#---- If we have smart case-sensitivity, and the search-string is all
#     lower-case, preserve all-caps and initial-caps matches
def do_smart_conversion(foundText, replText):
    """
    If found is all lower-case, return replText as is
    If FOUND is all upper-case, return replText.upper()
    If Found is capitalized and return replText.capitalize()
    """
    if foundText.lower() == foundText:
        return replText # as is
    if foundText.upper() == foundText:
        return replText.upper()
    if foundText[0].isupper() and replText[0].islower():
        # Capitalize the first letter, leave the rest as is
        return replText[0].upper() + replText[1:]
    # There are no other templates that make sense.
    return replText


#---- self-test mainline

def _test():
    r"""Some extra doctests:

    Bug 80881:
    
        >>> regex_info_from_str("/[w-z]$/", universal_newlines=True) \
        ...   == (re.compile(r'[w-z](?=\r\n|(?<!\r)\n|\r(?!\n)|\Z)'), None)
        True
    """
    import doctest
    doctest.testmod()

if __name__ == "__main__":
    _test()
