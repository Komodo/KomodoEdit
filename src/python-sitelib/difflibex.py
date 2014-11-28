#!/usr/bin/env python
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

"""difflibex -- some diff-related additions to difflib

Notes:
- Eventually it would be nice to have generic parsing of patch/diff content
  of many formats.

"""

__version_info__ = (0, 1, 0)
__version__ = '.'.join(map(str, __version_info__))

import os
from os.path import join, isfile
import sys
import re
from pprint import pprint, pformat
import glob
import traceback
import time
import logging
import optparse
import difflib
from difflib import SequenceMatcher # For getUnsavedChangeInstructions
from hashlib import md5

from zope.cachedescriptors.property import LazyClassAttribute
import textinfo
from fileutils import walk_avoiding_cycles


#---- exceptions

class DiffLibExError(Exception):
    pass



#---- globals

log = logging.getLogger("difflibex")
#log.setLevel(logging.DEBUG)


#---- main functions and classes

def unified_diff(a, b, fromfile='', tofile='', fromfiledate='',
                 tofiledate='', n=3, lineterm='\n'):
    """An slight extension of `difflib.unified_diff()` that properly
    handles the compared files not having an end-of-line char at the
    end of the file and the diff including those lines.
    """
    for line in difflib.unified_diff(
                    a, b,
                    fromfile=fromfile, tofile=tofile,
                    fromfiledate=fromfiledate, tofiledate=tofiledate,
                    n=n, lineterm=lineterm):
        if not line.endswith(lineterm):
            # Handle not having an EOL at end of file
            # (see Komodo Bug 74398).
            yield line + lineterm
            yield "\ No newline at end of file" + lineterm
        else:
            yield line


def infer_cwd_and_strip_from_path(path_in_diff, actual_path):
    """Try to infer an appropriate cwd and strip number given the starting
    path in a diff and the actual path to the file.

    This is useful when one wants to associate diff content with an actual file
    on disk (e.g. to patch the file or jump to a corresponding line).

    Returns (<cwd>, <strip>) where <strip> is a number as would be used for
    the -p|--strip option to patch.exe. Raises DiffLibExError if could not
    infer cwd & strip (with a reason why).
    """
    # E.g. these:
    #   path_in_diff = blah/mozilla/config/milestone.pl
    #   actual_path  = /home/trentm/moz/1.8.0/mozilla/config/milestone.pl
    # should result in:
    #   commonsuffix = mozilla/config/milestone.pl
    commonsuffix = _commonsuffix([path_in_diff, actual_path])
    if not commonsuffix:
        raise DiffLibExError("no common path suffix between '%s' and '%s'"
                             % (path_in_diff, actual_path))
    #   cwd          = /home/trentm/moz/1.8.0
    #   strip        = 1
    cwd = _rstrippath(actual_path, len(_splitall(commonsuffix)))
    strip = len(_splitall(path_in_diff)) - len(_splitall(commonsuffix))
    return (cwd, strip)


def diff_file_contents(left_content, right_content,
                       left_filepath='', right_filepath=''):
    """Return a unified diff between the left and right contents."""
    # See if the content differs.
    if left_content == right_content:
        # The content is the same.
        return ""
    # Perform unified diff of contents.
    result = unified_diff(left_content.splitlines(1),
                          right_content.splitlines(1),
                          left_filepath, right_filepath)
    return "".join(result)


def diff_local_directories(left_dirpath, right_dirpath):
    """Return a unified diff between the files in the left and right dirs.

    If a path only exists on one side it will be assumed that the file on the
    other side has zero content.
    """
    left_relpaths = set()
    left_dirpath_len = len(left_dirpath.rstrip(os.sep)) + 1
    for dirpath, dirs, files in walk_avoiding_cycles(left_dirpath):
        relpath = dirpath[left_dirpath_len:]
        left_relpaths.update([join(relpath, name) for name in files])

    right_relpaths = set()
    right_dirpath_len = len(right_dirpath.rstrip(os.sep)) + 1
    for dirpath, dirs, files in walk_avoiding_cycles(right_dirpath):
        relpath = dirpath[right_dirpath_len:]
        right_relpaths.update([join(relpath, name) for name in files])

    common_relpaths = left_relpaths.intersection(right_relpaths)
    # Files deleted (i.e. on the left but not on the right)
    removed_relpaths = left_relpaths.difference(right_relpaths)
    # Files added (i.e. on the right but not on the left)
    added_relpaths = right_relpaths.difference(left_relpaths)

    # Make one sorted list of the paths and their respective change types.
    change_list = [(relpath, "common") for relpath in common_relpaths ] + \
                  [(relpath, "removed") for relpath in removed_relpaths ] + \
                  [(relpath, "added") for relpath in added_relpaths ]
    change_list.sort()

    result = []
    for relpath, changetype in change_list:
        left_path = join(left_dirpath, relpath)
        right_path = join(right_dirpath, relpath)
        left_filedata = ''
        right_filedata = ''
        hasBinaryContent = False

        if changetype == "common" or changetype == "removed":
            left_ti = textinfo.TextInfo.init_from_path(left_path,
                                                       follow_symlinks=True)
            if left_ti.is_text:
                left_filedata = left_ti.text
            else:
                hasBinaryContent = True

        if changetype == "common" or changetype == "added":
            right_ti = textinfo.TextInfo.init_from_path(right_path,
                                                        follow_symlinks=True)
            if right_ti.is_text:
                right_filedata = right_ti.text
            else:
                hasBinaryContent = True

        if hasBinaryContent:
            result.append("===================================================================\n"
                          "--- %s\n"
                          "+++ %s\n"
                          "Binary files differ\n"
                          % (left_path, right_path))
            continue

        # See if the files differ.
        if (changetype == "common" and
            md5(left_filedata).hexdigest() == md5(right_filedata).hexdigest()):
            # The files are the same.
            continue

        # Perform unified diff of contents.
        difflines = unified_diff(left_filedata.splitlines(1),
                                 right_filedata.splitlines(1),
                                 left_path, right_path)
        result += difflines
    return "".join(result)


def diff_multiple_local_filepaths(left_filepaths, right_filepaths,
                                  left_displaypaths=None,
                                  right_displaypaths=None):
    """Return a unified diff between the left and right filepaths.

    If a filepath does not exist, it will be assumed that it is a file
    of zero content.
    """
    assert left_filepaths
    assert right_filepaths
    assert len(left_filepaths) == len(right_filepaths)
    if left_displaypaths is None:
        left_displaypaths = left_filepaths
    if right_displaypaths is None:
        right_displaypaths = right_filepaths
    assert len(left_displaypaths) == len(right_displaypaths)

    result = []
    for left_path, right_path, left_display, right_display in zip(left_filepaths, right_filepaths,
                                                                  left_displaypaths, right_displaypaths):
        hasBinaryContent = False
        left_filedata = ''
        right_filedata = ''

        if isfile(left_path):
            ti = textinfo.TextInfo.init_from_path(left_path,
                    follow_symlinks=True)
            if ti.is_text:
                left_filedata = ti.text
            else:
                hasBinaryContent = True
        if isfile(right_path):
            ti = textinfo.TextInfo.init_from_path(right_path,
                    follow_symlinks=True)
            if ti.is_text:
                right_filedata = ti.text
            else:
                hasBinaryContent = True
        if hasBinaryContent:
            result.append("===================================================================\n"
                          "--- %s\n"
                          "+++ %s\n"
                          "Binary files differ\n"
                          % (left_path, right_path))
            continue

        # See if the files differ.
        if (md5(left_filedata).hexdigest() == md5(right_filedata).hexdigest()):
            # The files are the same.
            continue
        # Perform unified diff of contents.
        result += unified_diff(left_filedata.splitlines(1),
                               right_filedata.splitlines(1),
                               left_display, right_display)
    return "".join(result)

class Hunk:
    def __init__(self, start_line, lines):
        end_line = start_line + len(lines)
        log.debug("lines %d-%d: hunk", start_line, end_line)
        self.start_line = start_line
        self.end_line = end_line
        self.lines = lines
    def pprint(self, indent=' '*8):
        print "%shunk: lines %d-%d"\
              % (indent, self.start_line, self.end_line)

class FileDiff:
    """A FileDiff represents diff content for one file. It is made up of one
    or more chunks."""

    def __init__(self, paths, header_start_line):
        log.debug("line %s: create FileDiff, paths=%r",
                  header_start_line is None and '?' or header_start_line,
                  paths)
        self.paths = paths
        self.lines = None
        self.header_start_line = header_start_line
        self.hunks = []
        self.diff_type = None

    def __repr__(self):
        return "<FileDiff: %d hunks, '%s' best path>" % (
            len(self.hunks), self.best_path())

    @property
    def diff(self):
        return "\n".join(self.lines)

    def add_hunk(self, start_line, lines):
        self.hunks.append(
            Hunk(start_line, lines)
        )

    def best_path(self, cwd=None):
        #XXX How to pick the best path?
        if "p4 diff header" in self.paths:
            path = self.paths["p4 diff header"]
        elif "index" in self.paths:
            path = self.paths["index"]
        elif self.diff_type == "unified" and "+++" in self.paths:
            path = self.paths["+++"]
        elif self.diff_type == "context" and "---" in self.paths:
            path = self.paths["---"]
        elif self.paths:
            path = self.paths.values()[0]
        else:
            return None
        if not path or not cwd or os.path.isabs(path):
            return path
        return os.path.join(cwd, path)

    def all_paths(self, cwd=None):
        """Return a list of possible paths for this hunk."""
        best_path = self.best_path(cwd=cwd)
        all_paths = [best_path]
        for path in self.paths.values():
            if path == best_path:
                continue
            if path and cwd and not os.path.isabs(path):
                path = os.path.join(cwd, path)
            all_paths.append(path)
        return all_paths

    def pprint(self, indent=' '*4):
        best_path = self.best_path()
        if best_path is None:
            best_path = "???"
        print "%s%s file diff of '%s' (%d hunks)"\
              % (indent,
                 self.diff_type,
                 best_path,
                 len(self.hunks))
        for hunk in self.hunks:
            hunk.pprint(indent*2)

class Diff:
    """A Diff represents some diff/patch content. At its most generic it is made
    up of multiple FileDiff's.
    """

    @LazyClassAttribute
    def _patterns(self):
        return {
            "index":
                re.compile(r"^Index:\s+(?P<path>.*?)\s*$"),
            "p4 diff header":
                # ==== //depot/foo.css#42 - c:\clientview\foo.css ====
                # ==== //depot/foo.js#22 (xtext) ====
                re.compile(r"^==== (?P<depotpath>.*?)#\d+ "
                            "(- (?P<path>.*?)|\(.*?\)) ====$"),
            "---":
                re.compile(r"(\+\+\+|---|\*\*\*)(\s+(?P<path>.*?)(\t.*?)?)?\s*$"),
            "plain hunk header":
                # E.g., '9c9', '185,187c185'
                re.compile(r"^(?P<beforestartline>\d+)(,\d+)?"
                            "(?P<type>[acd])"
                            "(?P<afterstartline>\d+)(,\d+)?$"),
            "context hunk header":
                # E.g., '*** 32,37 ****', '--- 32,39 ----', '*** 1 ****'
                re.compile(r"^([\*-]){3} (?P<startline>\d+)(,(?P<endline>\d+))? \1{4}$"),
            "unified hunk header":
                # E.g., '@@ -296,7 +296,8 @@'
                # E.g., '@@ -1 +0,0 @@'
                re.compile(r"^@@\s-(?P<beforestartline>\d+)(,(\d+))?\s"
                            "\+(?P<afterstartline>\d+)(,(\d+))?\s@@"),
        }

    def __init__(self, content):
        self.file_diffs = []
        self.parse(content)

    def __repr__(self):
        return "<Diff: %d files, %d hunks>"\
               % (len(self.file_diffs),
                  sum([len(f.hunks) for f in self.file_diffs]))

    def pprint(self):
        print "diff (%s files)" % (len(self.file_diffs))
        for file_diff in self.file_diffs:
            file_diff.pprint(indent=' '*4)

    def parse(self, content):
        r"""

        p4 diff -du:
            ==== //depot/foo.css#42 - c:\clientview\foo.css ====
            @@ ... @@
            ...

        p4 diff -dc:
            ==== //depot/foo.css#42 - c:\clientview\foo.css ====
            ***************
            *** 182,196 ****
            ...

        p4 diff:
            ==== //depot/foo.css#42 - c:\clientview\foo.css ====
            185,187c185
            ...

        cvs diff -u:
            Index: toolkit/xre/nsCommandLineServiceMac.cpp
            ===================================================================
            RCS file: /cvsroot/mozilla/toolkit/xre/nsCommandLineServiceMac.cpp,v
            retrieving revision 1.3
            diff -d -u -r1.3 nsCommandLineServiceMac.cpp
            --- toolkit/xre/nsCommandLineServiceMac.cpp	19 Feb 2005 22:41:59 -0000	1.3
            +++ toolkit/xre/nsCommandLineServiceMac.cpp	19 Sep 2005 22:34:10 -0000
            @@ -6,12 +6,12 @@
            ...

        cvs diff -c:
            Index: setup.py
            ===================================================================
            RCS file: /cvsroot/pywin32/pywin32/setup.py,v
            retrieving revision 1.31
            diff -c -r1.31 setup.py
            *** setup.py    11 Jan 2006 01:31:41 -0000      1.31
            --- setup.py    3 Mar 2006 02:35:39 -0000
            ***************
            ...

        cvs diff:
            Index: setup.py
            ===================================================================
            RCS file: /cvsroot/pywin32/pywin32/setup.py,v
            retrieving revision 1.31
            diff -r1.31 setup.py
            9c9
            ...

        svn:
            Index: ref/foo.txt
            ===================================================================
            --- ref/foo.txt    (revision 897)
            +++ ref/foo.txt    (working copy)
            ...

        Komodo's "Show Unsaved Changes":
            Index: C:\trentm\as\Komodo-devel\src\codeintel\ci2.py
            --- C:\trentm\as\Komodo-devel\src\codeintel\ci2.py
            +++ C:\trentm\as\Komodo-devel\src\codeintel\ci2.py (unsaved)
            @@ -360,7 +360,7 @@
            ...
        """
        state = None
        file_diff = None
        paths = {}
        lines = self.lines = content.splitlines(0)
        idx = 0
        while idx < len(lines):
            line = lines[idx]
            #print "%3d: %r" % (idx, line)

            if state is None: # looking for diff header lines
                first_tokens = line.split(None, 1)
                if first_tokens:
                    first_token = first_tokens[0]
                else:
                    first_token = ''

                if line.startswith("Index:"):
                    match = self._patterns["index"].match(line)
                    if match:
                        paths["index"] = match.group("path")
                        log.debug("line %d: 'Index: ' line, path=%r",
                                  idx, paths["index"])
                        if file_diff is None:
                            file_diff = FileDiff(paths, idx)
                elif first_token == "diff":
                    # Note: Could parse the filename out of here, but
                    #       that involves skipping cmdln switches. Punt
                    #       for now.
                    # A "plain" hunk header sometimes follows a "diff "
                    # line.
                    log.debug("line %d: 'diff ' line", idx)
                    if file_diff is None:
                        file_diff = FileDiff(paths, idx)
                    if idx+1 < len(lines) \
                       and self._patterns["plain hunk header"]\
                            .match(lines[idx+1].rstrip()):
                        state = "plain"
                elif line.startswith("==== "):
                    # Likely a 'p4 diff ...' header line.
                    match = self._patterns["p4 diff header"].match(line)
                    if match:
                        log.debug("line %d: p4 diff header line", idx)
                        paths["p4 diff header"] = match.group("path")
                        log.debug("line %d: p4 diff header line, path=%r",
                                  idx, paths["p4 diff header"])
                        if file_diff is None:
                            file_diff = FileDiff(paths, idx)
                        # You can always tell the diff type from the
                        # line after the p4 diff header.
                        #XXX This is wrong. Sometimes there is *no*
                        #    subsequent diff content.
                        if idx+1 < len(lines) and not lines[idx+1].strip():
                            # 'p4 describe' output includes an extra
                            # blank separation line here.
                            idx += 1
                        if idx+1 < len(lines):
                            if lines[idx+1].rstrip() == "*"*15:
                                state = "context"
                            elif lines[idx+1].startswith("@@"):
                                state = "unified"
                            else:
                                state = "plain"
                elif first_token in ("---", "+++", "***"):
                    match = self._patterns["---"].match(line)
                    if match:
                        paths[first_token] = match.group("path")
                        log.debug("line %d: '%s ' line, path=%r",
                                  idx, first_token, paths[first_token])
                        if file_diff is None:
                            file_diff = FileDiff(paths, idx)
                        if first_token == "+++":
                            state = "unified"
                        elif first_token == "---" \
                             and idx > 0 \
                             and lines[idx-1].strip() \
                             and lines[idx-1].split(None, 1)[0] == "***":
                            state = "context"
                elif self._patterns["plain hunk header"].match(line.rstrip()):
                    if file_diff is None:
                        file_diff = FileDiff(paths, None)
                    state = "plain"
                    idx -= 1 # compensation for the subsequent increment
                idx += 1

            elif state == "plain":
                log.debug("line %s: 'plain' file diff", idx)
                file_diff.diff_type = "plain"

                while idx < len(lines): # read in plain hunks
                    match = self._patterns["plain hunk header"].match(lines[idx])
                    if not match:
                        break
                    hunk_start_line = idx
                    idx += 1

                    hunk_type = match.group("type")
                    if hunk_type == 'a':
                        # HEADER
                        # > ...
                        # > ...
                        while idx < len(lines) and lines[idx].startswith("> "):
                            idx += 1
                    elif hunk_type == 'd':
                        # HEADER
                        # < ...
                        # < ...
                        while idx < len(lines) and lines[idx].startswith("< "):
                            idx += 1
                    elif hunk_type == 'c':
                        # HEADER
                        # < ...
                        # < ...
                        # ---
                        # > ...
                        # > ...
                        while idx < len(lines) and lines[idx].startswith("< "):
                            idx += 1
                        if idx >= len(lines) \
                           or not lines[idx].rstrip() == "---":
                            log.warn("unexpected line in middle of plain hunk: "
                                     "%r (line %d)", lines[idx], idx)
                            break
                        idx += 1
                        while idx < len(lines) and lines[idx].startswith("> "):
                            idx += 1
                    else:
                        raise DiffLibExError("unexpected plain hunk header "
                                             "type: '%s'" % hunk_type)
                    file_diff.add_hunk(hunk_start_line, lines[hunk_start_line:idx])

                file_diff.lines = lines[file_diff.header_start_line:idx]
                self.file_diffs.append(file_diff)
                state = None
                file_diff = None
                paths = {}

            elif state == "unified":
                log.debug("line %d: 'unified' file diff", idx)
                file_diff.diff_type = "unified"

                while idx < len(lines): # read in unified hunks
                    if not lines[idx].startswith("@@ "): break
                    hunk_start_line = idx
                    idx += 1

                    while idx < len(lines) \
                          and (lines[idx].startswith("+")
                               or lines[idx].startswith("-")
                               or lines[idx].startswith(" ")
                               # Guard against "empty diff hunk line" + Komodo's
                               # "remove trailing whitespace on save" causing
                               # the leading ' ' to have been removed.
                               or not lines[idx]):
                        idx += 1

                    file_diff.add_hunk(hunk_start_line, lines[hunk_start_line:idx])

                file_diff.lines = lines[file_diff.header_start_line:idx]
                self.file_diffs.append(file_diff)
                state = None
                file_diff = None
                paths = {}

            elif state == "context":
                log.debug("line %d: 'context' file diff", idx)
                file_diff.diff_type = "context"

                while idx < len(lines): # read in context hunks
                    if not lines[idx].rstrip() == "*"*15:
                        break
                    hunk_start_line = idx
                    idx += 1

                    if idx >= len(lines) \
                       or not lines[idx].startswith("*** "):
                        break
                    # Parse the header line.
                    idx += 1

                    while idx < len(lines) \
                          and (lines[idx].startswith("! ")
                               or lines[idx].startswith("+ ")
                               or lines[idx].startswith("- ")
                               or lines[idx].startswith("  ")
                               # Guard against "empty diff hunk line" + Komodo's
                               # "remove trailing whitespace on save" causing
                               # the leading '  ' to have been removed.
                               or not lines[idx]):
                        idx += 1

                    if idx >= len(lines) \
                       or not lines[idx].startswith("--- "):
                        break
                    idx += 1

                    while idx < len(lines) \
                          and (lines[idx].startswith("! ")
                               or lines[idx].startswith("+ ")
                               or lines[idx].startswith("- ")
                               or lines[idx].startswith("  ")
                               # Guard against "empty diff hunk line" + Komodo's
                               # "remove trailing whitespace on save" causing
                               # the leading '  ' to have been removed.
                               or not lines[idx]):
                        idx += 1

                    file_diff.add_hunk(hunk_start_line, lines[hunk_start_line:idx])

                file_diff.lines = lines[file_diff.header_start_line:idx]
                self.file_diffs.append(file_diff)
                state = None
                file_diff = None
                paths = {}

            else:
                raise ValueError("unknown state: '%s'" % state)

    def file_diff_and_hunk_from_pos(self, diff_line, diff_col):
        """Return the file_diff and hunk that this diff_line applies to."""
        # We are generous here, allowing a line outside of the strict diff
        # hunk area to apply to the following hunk.
        if not self.file_diffs:
            raise DiffLibExError("No file diffs are available")
        for file_diff in self.file_diffs:
            for hunk in file_diff.hunks:
                if diff_line < hunk.end_line:
                    break
            else:
                continue
            break
        else:
            # A generosity: if diff_line is *just* past the last diff hunk,
            # then pretend it is in-range. Otherwise a common case in Komodo
            # is to highlight a diff on the last line of a file an place the
            # cursor on column 0 of the next line (to select the whole line).
            # This technically place the cursor out of range.
            if (diff_col == 0 and self.file_diffs and self.file_diffs[-1].hunks
                and diff_line == self.file_diffs[-1].hunks[-1].end_line
               ):
                file_diff = self.file_diffs[-1]
                hunk = file_diff.hunks[-1]
                diff_line -= 1
                diff_col = len(self.lines[diff_line])
            else:
                raise DiffLibExError("(this one) line %s is not in a diff hunk"
                                     % (diff_line+1))
        return file_diff, hunk

    def file_pos_from_diff_pos(self, diff_line, diff_col):
        """Return a file position for the given position in the diff content.

        Where to set the file position isn't always obvious. The most literal
        result would just be a simple line count into the diff hunk offset
        by the start line from the hunk header. Eventually this could get
        smarter and try to account for patch-like fuzz and offsets.

        All line and column values are 0-based.

        Returns a 3-tuple:
            (<file-path>, <file-line>, <file-col>)
        If a file position could not be found, then a DiffLibExError is raised
        giving the reason (e.g. the diff position might not be in a diff hunk).
        """
        file_diff, hunk = self.file_diff_and_hunk_from_pos(diff_line, diff_col)
        file_path = file_diff.best_path()
        log.debug("diff pos (%d, %d) is in a '%s' hunk", diff_line, diff_col,
                  file_path)

        # Work down from the top of the hunk to find the file position.
        # (Could move this out to format-specific Hunk sub-classes.)
        if file_diff.diff_type == "unified":
            # First line is the hunk header:
            #   @@ -A,B +C,D @@
            # where,
            #   A is the file_before_line_start (1-based)
            #   B is the file_after_line_start (1-based)
            # Subtract 1 to convert to 0-based line nums.
            m = self._patterns["unified hunk header"].match(
                    self.lines[hunk.start_line])
            # -1 to convert to 0-based
            file_before_line = int(m.group("beforestartline")) - 1
            file_after_line = int(m.group("afterstartline")) - 1
            # range start:  +1 to skip header
            # range end:    +1 to include diff_line bound
            if diff_line < hunk.start_line+1:
                # Not in the diff hunk content, just default to the first
                # diff hunk line.
                file_line = file_after_line
                file_col = 0
            else:
                # -1 because the counting will add it back on the first line
                file_before_line -= 1
                file_after_line -= 1
                for i in range(hunk.start_line+1, diff_line+1):
                    line = self.lines[i]
                    if not line or line[0] == ' ':
                        # 'not line' because Komodo's "remove trailing whitespace
                        # on save" might have removed it.
                        file_before_line += 1
                        file_after_line += 1
                    elif line[0] == '-':
                        file_before_line += 1
                    elif line[0] == '+':
                        file_after_line += 1
                    else:
                        # This is junk lines after the diff hunk.
                        raise DiffLibExError("line %s is not in a diff hunk"
                                             % (diff_line+1))
                if line and line[0] == '-':
                    file_line = file_before_line
                else:
                    file_line = file_after_line
                file_col = max(diff_col - 1, 0) # unified-diff prefix is 1 char

        elif file_diff.diff_type == "context":
            hunk_header_pat = self._patterns["context hunk header"]
            file_col = max(diff_col - 2, 0) # context-diff prefix is 2 chars

            state = "all stars"
            i = hunk.start_line
            while i < hunk.end_line:
                line = self.lines[i]
                log.debug("%3d: %r", i, line)
                if state == "all stars":
                    # First line of hunk header: '***************'
                    if i >= diff_line:
                        # Use the file_before start line.
                        m = hunk_header_pat.match(self.lines[i+1])
                        file_line = int(m.group("startline")) - 1
                        file_col = 0
                        break
                    state = "before header"
                elif state == "before header":
                    m = hunk_header_pat.match(line)
                    file_line = int(m.group("startline")) - 1
                    if i == diff_line:
                        file_col = 0
                        break
                    else:
                        file_line -= 1 # will be added back on first content line
                        state = "before content"
                elif state == "before content":
                    if line[:2] in ("  ", "! ", "- "):
                        file_line += 1
                        if i == diff_line:
                            break
                    elif line.startswith("--- "):
                        state = "after header"
                        i -= 1
                    else:
                        raise DiffLibExError("unexpected line in context "
                                             "diff: %r" % line)
                elif state == "after header":
                    m = hunk_header_pat.match(line)
                    file_line = int(m.group("startline")) - 1
                    if i == diff_line:
                        file_col = 0
                        break
                    else:
                        file_line -= 1 # will be added back on first content line
                        state = "after content"
                elif state == "after content":
                    if line[:2] in ("  ", "! ", "+ "):
                        file_line += 1
                        if i == diff_line:
                            break
                    else:
                        raise DiffLibExError("unexpected line in context "
                                             "diff: %r" % line)
                i += 1

        elif file_diff.diff_type == "plain":
            hunk_header_pat = self._patterns["plain hunk header"]
            file_col = max(diff_col - 2, 0) # plain-diff prefix is 2 chars

            state = "header"
            i = hunk.start_line
            while i < hunk.end_line:
                line = self.lines[i]
                log.debug("%3d: %r", i, line)
                if state == "header":
                    m = hunk_header_pat.match(line)
                    file_before_line = int(m.group("beforestartline")) - 1
                    hunk_type = m.group("type")
                    file_after_line = int(m.group("afterstartline")) - 1
                    if i >= diff_line:
                        file_line = file_after_line
                        file_col = 0
                        break
                    else:
                        # -1 because will be added back on first content line.
                        if hunk_type == "a":
                            file_line = file_after_line - 1
                            state = "after content"
                        else: # hunk_type in ('c', 'd')
                            file_line = file_before_line - 1
                            state = "before content"
                elif state == "before content":
                    if line[:2] == "< ":
                        file_line += 1
                        if i == diff_line:
                            break
                    elif line.rstrip() == "---":
                        state = "divider"
                        i -= 1
                    else:
                        raise DiffLibExError("unexpected line in plain "
                                             "diff: %r" % line)
                elif state == "divider":
                    if i == diff_line:
                        file_line = file_after_line
                        file_col = 0
                        break
                    else:
                        # -1 because will be added back on first content line.
                        file_line = file_after_line - 1
                        state = "after content"
                elif state == "after content":
                    if line[:2] == "> ":
                        file_line += 1
                        if i == diff_line:
                            break
                    else:
                        raise DiffLibExError("unexpected line in plain "
                                             "diff: %r" % line)
                i += 1

        else:
            raise DiffLibExError("unrecognized diff type: '%s'"
                                 % file_diff.diff_type)

        return (file_path, file_line, file_col)

    def get_changed_line_numbers_by_filepath(self):
        """A dict of filepaths and their changed line numbers (0 based)"""
        result = {}
        for file_diff in self.file_diffs:
            file_path = file_diff.best_path()
            result[file_path] = linenums = []
            _, file_line, _ = self.file_pos_from_diff_pos(file_diff.header_start_line, 0)
            for hunk in file_diff.hunks:
                for line in hunk.lines:
                    if line.startswith(" "):
                        file_line += 1
                    elif line.startswith("+"):
                        linenums.append(file_line)
                        file_line += 1
        return result

    def possible_paths_from_diff_pos(self, diff_line, diff_col):
        """Return a list of all possible file paths for the given position.

        If a file position could not be found, then a DiffLibExError is raised
        giving the reason (e.g. the diff position might not be in a diff hunk).
        """
        file_diff, hunk = self.file_diff_and_hunk_from_pos(diff_line, diff_col)
        return file_diff.all_paths()

def _max_acceptable_edit_dist(s):
    # Found this value largely by pulling it out of a hat.  Replacements occupy
    # a grey area between equal and replace/delete, so we say that any string
    # with a levenstein value < 1/4 its length qualifies as a replacement.
    return len(s) / 4.0

_split_opcodes_diffs = {} # Map md5(a) + md5(b) => {time:time, opcodes:list of opcodes}

def _get_hash_for_arrays(a, b):
    key = md5("".join(a)).hexdigest() + md5("".join(b)).hexdigest()
    currTime = time.time()
    if key in _split_opcodes_diffs:
        h = _split_opcodes_diffs[key]
        h['time'] = currTime
        return key
    if len(_split_opcodes_diffs) >= 1000:
        # If we have more than 1000 keys, remove the least recently used.
        oldest_item = min([(x[1]['time'], x[0]) for x in _split_opcodes_diffs.items()])
        del _split_opcodes_diffs[oldest_item[1]]
    _split_opcodes_diffs[key] = {'time':currTime, 'opcodes':None}
    return key


def split_opcodes(opcode, a, b, forceCalc=False):
    """
    @param opcode: tuple of (tag:string="replace", 
                   i1: start index of change to a,
                   i2: end index of change to a,
                   j1: start index of change to b,
                   j1: end index of change to b)
        This function is called when i2 - i1 != j2 - j1, or in other words
        unified-diff has decided we're replacing m lines with n != m lines.
        We want to find out which lines are true replacements (similar), and
        which are insertions or deletions.
        
    @param a: list of strings (original values) 
    @param b: list of strings (current values)
    @return: an array of new opcodes
    
    Implement a modified Wagner-Fischer algorithm
    to try to determine how these lines actually match up
    
    References:
    https://en.wikipedia.org/wiki/Wagner%E2%80%93Fischer_algorithm
    
    If Wikipedia dies:
    R.A. Wagner and M.J. Fischer. 1974. The String-to-String Correction Problem. Journal of the ACM, 21(1):168-173.
    
    Overview:
    Build a matrix of edit_distance levenshtein values from all possible paths
    from line[i] in a to line[j] to b.  a is the starting text, b is the
    final text, and we want to determine a sequence of transformations from a
    to b.
    
    Given m = len(a) and n = len(b),
    this is an m x n matrix, D.  We want to find a path through the matrix
    moving through the first dimension (corresponding to lines in a),
    starting at D[0][0].  We also never backtrack on j.
    
    If we find an entry d[i][j] = 0, this means lines a[i] and b[j] match.
    Advance both i and j.
    
    If d[i][j] <= some max value X (which normally depends on a[i]), it means
    b[j] is a replacement for a[j].
    
    If d[i][j] > X, then is there a value d[i][j'] <= X for j' > j?
    If yes, treat b[j:j'] as inserted lines relative to a[i], and process d[i][j'] as above.
    Otherwise, treat a[i] as a deleted line relative to b[j].
    
    Remember to look for a run of inserted or deleted text at the end as well.
    
    Now we could use a dynamic programming algorithm to determine the minimum
    cost for going from a to b, but let's assume this result will be good enough,
    since its main purpose is to show diffs visually in the editor.
    
    """
    m = len(a)
    n = len(b)
    if (not forceCalc) and m * n > 500:
        # Don't waste time trying to split up big hunks
        return [opcode]
    
    _split_opcodes_diffs_key = _get_hash_for_arrays(a, b)
    if _split_opcodes_diffs[_split_opcodes_diffs_key]['opcodes']:
        return _split_opcodes_diffs[_split_opcodes_diffs_key]['opcodes']
    # We don't need all possible edit-distances from a[i] to b[j],
    # because once we advance j at row i, we never look at any entries
    # in d[ix][jx] for ix > i, jx < j.  So just initialize the matrix with None's.
    d = [[None for j in range(n)] for i in range(m)]
    tag, i1, i2, j1, j2 = opcode # assert tag == 'replace'
    opcodes = []
    j = 0
    for i in range(m):
        # Update levenshtein distances for d[i][j:]
        max_lev = _max_acceptable_edit_dist(a[i])
        for j_idx in range(j, n):
            dval = edit_distance(a[i], b[j_idx])
            d[i][j_idx] = dval
            if dval <= max_lev:
                # Once we find something suitable there's no need to look further.
                break
        curr_slice = d[i][j:]
        if 0 in curr_slice:
            next_zero = curr_slice.index(0)
        else:
            next_zero = -1
            
        if next_zero == 0:
            next_posn = next_zero
            match_type = "equal"
        else:
            for next_low_idx, next_low_val in enumerate(curr_slice):
                if next_low_val <= max_lev:
                    break
            else:
                next_low_idx = -1
            
            if next_low_idx < 0:
                if next_zero < 0:
                    # It's a deletion
                    match_type = "delete"
                    next_posn = None
                else:
                    next_posn = next_zero
                    match_type = "equal"
            elif next_zero < 0:
                next_posn = next_low_idx
                match_type = "replace"
            else:
                if next_zero <= next_low_idx:
                    next_posn = next_zero
                    match_type = "equal"
                else:
                    next_posn = next_low_idx
                    match_type = "replace"
        # Now advance through the distance matrix
        if next_posn is not None:
            if next_posn > 0:
                opcodes.append(('insert', i + i1, i + i1, j + j1, j + j1 + next_posn))
                j += next_posn
            opcodes.append((match_type, i + i1, i + i1 + 1, j + j1, j + j1 + 1))
            j += 1
        else:
            # We have a deletion - don't advance j
            opcodes.append((match_type, i + i1, i + i1 + 1, j + j1, j + j1))
        if j == n:
            # Delete the rest of the lines and leave this loop.
            if i < m - 1:
                opcodes.append(('delete', i + i1 + 1, m + i1, n + j1, n + j1))
            break
    if j < n:
        opcodes.append(('insert', m + i1, m + i1, j + j1, n + j1))
    
    _split_opcodes_diffs[_split_opcodes_diffs_key]['opcodes'] = opcodes
    return opcodes
        
def edit_distance(s, t):
    """ Levenshtein distance: http://en.wikipedia.org/wiki/Levenshtein_distance
           or:
        Navarro, Gonzalo (March 2001). "A guided tour to approximate string matching".
        ACM Computing Surveys 33 (1): 31-88. doi:10.1145/375360.375365.
    """
    edDict = {} # For memoizing costs between s[i:] and t[j:]
    def _edit_distance_aux(spos, tpos):
        k = (spos, tpos)
        if k in edDict:
            return edDict[k]
        if spos == 0:
            return tpos
        if tpos == 0:
            return spos
        cost = s[spos - 1] != t[tpos - 1] and 1 or 0
        v = min(_edit_distance_aux(spos - 1, tpos    ) + 1,
                _edit_distance_aux(spos    , tpos - 1) + 1,
                _edit_distance_aux(spos - 1, tpos - 1) + cost)
        edDict[k] = v
        return v
    return _edit_distance_aux(len(s), len(t))

#---- internal support stuff

def _unique(s):
    """Return a list of the elements in s, in arbitrary order, but without
    duplicates. (_Part_ of the Python Cookbook recipe.)
    """
    # get the special case of an empty s out of the way, very rapidly
    n = len(s)
    if n == 0:
        return []

    # Try using a dict first, as that's the fastest and will usually work.
    u = {}
    try:
        for x in s:
            u[x] = 1
    except TypeError:
        del u  # move on to the next method
    else:
        return u.keys()

def _splitall(path):
    """Split the given path into all its directory parts and return the list
    of those parts (see Python Cookbook recipe for test suite).
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
    return allparts

#XXX Add this to recipes.
def _commonsuffix(paths):
    """Return the common path suffix (if any) for the given paths.

        >>> _commonsuffix(["/home/trentm/1.8.0/mozilla/config/milestone.pl",
        ...                "mozilla/config/milestone.pl",
        ...                "config/milestone.pl"])
        'config/milestone.pl'
        >>> _commonsuffix(["/home/trentm/1.8.0/mozilla/config/milestone.pl",
        ...                "mozilla/config/milestone.pl"])
        'mozilla/config/milestone.pl'
        >>> _commonsuffix(["/home/trentm/1.8.0/mozilla/config/milestone.pl",
        ...                "mozilla/config/foo.bar"])
        None

    It only compares on directory boundaries. Returns None if there is no
    common suffix.
    """
    if not paths:
        return None
    splitpaths = [list(reversed(_splitall(path))) for path in paths]
    commonsuffix = []
    for set in zip(*splitpaths):
        # This path element is part of the common suffix if it is the same
        # for every give path.
        elem = set[0]
        if sys.platform.startswith("win"):
            # Case-insensitive comparison on Windows. (XXX For Mac OS X too?)
            set = [p.lower() for p in set]
        if len(_unique(set)) == 1:
            commonsuffix.append(elem)
        else:
            break
    if commonsuffix:
        retval = os.path.join(*reversed(commonsuffix))
    else:
        retval = None
    #print "_commonsuffix(%r) -> %r" % (paths, retval)
    return retval

#XXX Add this to recipes
def _lstrippath(path, n):
    parts = _splitall(path)
    # '' for first arg is to prevent TypeError if n > len(parts).
    return os.path.join('', *parts[n:])

#XXX Add this to recipes
def _rstrippath(path, n):
    if n == 0:
        return path
    parts = _splitall(path)
    # '' for first arg is to prevent TypeError if n > len(parts).
    return os.path.join('', *parts[:-n])



#---- mainline and testsuite

def _test():
    raise "difflibex self-test"

def _print_file_position(diff, path, diff_pos):
    diff_line, diff_col = map(int, diff_pos.split(','))
    try:
        file_path, file_line, file_col \
            = diff.file_pos_from_diff_pos(diff_line-1, diff_col-1)
    except DiffLibExError, ex:
        print "%s:%s -> unknown (%s)" % (path, diff_pos, ex)
    else:
        print "%s:%s -> %s:%s,%s" % (path, diff_pos, file_path, file_line+1,
                                     file_col+1)


def main(argv):
    usage = "usage: %prog [DIFFS...]"
    version = "%prog "+__version__
    parser = optparse.OptionParser(prog="make", usage=usage, version=version,
                                   description=__doc__)
    parser.add_option("-v", "--verbose", dest="log_level",
                      action="store_const", const=logging.DEBUG,
                      help="more verbose output")
    parser.add_option("-q", "--quiet", dest="log_level",
                      action="store_const", const=logging.WARNING,
                      help="quieter output")
    parser.add_option("-T", "--self-test", action="store_true",
                      help="run self-test")
    parser.add_option("-F", "--file-pos", action="store", dest="diff_pos",
                      help="find corresponding file position for the given "
                           "diff posiition: <line>[,<column>] (1-based)")
    parser.set_defaults(log_level=logging.INFO, self_test=False, diff_pos=None)
    opts, args = parser.parse_args()
    log.setLevel(opts.log_level)

    diff_pos = opts.diff_pos
    if diff_pos and ',' not in diff_pos:
        diff_pos += ",1"  # default to first column

    if opts.self_test:
        _test()
    elif args:
        for path in args:
            d = Diff(open(path, 'r').read())
            if diff_pos:
                _print_file_position(d, path, diff_pos)
            else:
                print path + ':',
                d.pprint()

    else: # read from stdin
        d = Diff(sys.stdin.read())
        if diff_pos:
            _print_file_position('<stdin>', diff_pos)
        else:
            d.pprint()

if __name__ == "__main__":
    logging.basicConfig()
    try:
        retval = main(sys.argv)
    except SystemExit:
        pass
    except KeyboardInterrupt:
        sys.exit(1)
    except:
        exc_info = sys.exc_info()
        if log.isEnabledFor(logging.DEBUG):
            print
            traceback.print_exception(*exc_info)
        else:
            if hasattr(exc_info[0], "__name__"):
                #log.error("%s: %s", exc_info[0].__name__, exc_info[1])
                log.error(exc_info[1])
            else:  # string exception
                log.error(exc_info[0])
        sys.exit(1)
    else:
        sys.exit(retval)
