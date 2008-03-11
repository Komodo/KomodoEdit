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

"""
Usage:
    cd SOURCE-BRANCH-DIR
    kointegrate CHANGENUM TARGET-BRANCH-NAMES...

Easily integrate a change from its branch or tree to other active
Komodo branches. This will perform the necessary "p4|svn integrate"s,
resolve the differences, and help create an appropriate checkin.
"""

__version_info__ = (1, 0, 1)
__version__ = '.'.join(map(str, __version_info__))

import os
import sys
import getopt
from os.path import basename, dirname, join, exists, isdir, normpath, \
                    normcase, isabs, abspath, expanduser
from pprint import pprint, pformat
import logging
import textwrap
import optparse
import tempfile
import re
import fnmatch
import subprocess
import shutil
from ConfigParser import SafeConfigParser

import applib
sys.path.insert(0, join(dirname(dirname(abspath(__file__))), "src",
                        "codeintel", "support"))
import eol  # cherry-pick this from codeintel support area



class Error(Exception):
    pass



#---- globals

log = logging.getLogger("kointegrate")
#log.setLevel(logging.DEBUG)



#---- handling of active branches

class Branch(object):
    def __init__(self, name, base_dir):
        self.name = name
        self.base_dir = normpath(base_dir)

class NonExistantBranch(Branch):
    def __repr__(self):
        return "<Branch: %s, base dir `%s' does not exist>" \
               % (self.name, self.base_dir)

class P4Branch(Branch):
    scc_type = "p4"
    def __repr__(self):
        return "<P4Branch: %r at '%s'>" \
               % (self.name, self.base_dir)
    def __str__(self):
        return "%r branch at '%s' (p4)" % (self.name, self.base_dir)

    def edit(self, path):
        log.info("p4 edit %s", path)
        import p4lib
        p4 = p4lib.P4()
        if not isabs(path):
            path = join(self.base_dir, path)
        v = p4.edit(path)
        assert v, "`p4 edit %s` failed" % path
    def add(self, path):
        log.info("p4 add %s", path)
        import p4lib
        p4 = p4lib.P4()
        if not isabs(path):
            path = join(self.base_dir, path)
        v = p4.add(path)
        assert v, "`p4 add %s` failed" % path
    def delete(self, path):
        log.info("p4 delete %s", path)
        import p4lib
        p4 = p4lib.P4()
        if not isabs(path):
            path = join(self.base_dir, path)
        v = p4.delete(path)
        assert v, "`p4 delete %s` failed" % path
    
    def integrate(self, changenum, dst_branches, interactive,
                  exclude_outside_paths, excludes=[], force=False):
        if len(dst_branches) > 1:
            raise Error("Don't yet support integrating from Perforce "
                        "to *multiple* branches.")
        dst_branch = dst_branches[0]
        
        import p4lib
        p4 = p4lib.P4()

        # Gather some info about the change to integrate.
        change = p4.describe(change=changenum, diffFormat='u')
        outside_paths = []
        inside_paths = []
        indeces_to_del = []
        for i, f in enumerate(change["files"]):
            path = p4.fstat(f["depotFile"])[0]["path"]
            rel_path = path[len(self.base_dir)+1:]
            matching_excludes = [e for e in excludes
                                 if fnmatch.fnmatch(rel_path, e)]
            if matching_excludes:
                log.info("skipping `%s' (matches excludes: '%s')",
                         rel_path, "', '".join(matching_excludes))
                indeces_to_del.append(i)
                continue
            if not normcase(path).startswith(normcase(self.base_dir)):
                outside_paths.append(path)
            else:
                inside_paths.append(path)
            # Side-effect: tweak the data structure for convenience later.
            change["files"][i]["path"] = path
            change["files"][i]["rel_path"] = rel_path
        for i in reversed(indeces_to_del): # drop excluded files
            del change["files"][i]
        rel_paths = [p[len(self.base_dir)+1:] for p in inside_paths]
        dst_paths = [join(dst_branch.base_dir, p) for p in rel_paths]

        print "  change: %s" % changenum
        print "    desc: %s" % _one_line_summary_from_text(change["description"], 60)
        print "      by: %s" % change["user"]
        print "      to: %s" % dst_branch.base_dir
        if len(rel_paths) > 7:
            ellipsis = '...and %d other files' % (len(rel_paths)-7)
            print "   files: %s" \
                  % _indent(' '.join(rel_paths[:7] + [ellipsis]), 10, True)
        else:
            print "   files: %s" % _indent(' '.join(rel_paths), 10, True)
        if interactive:
            print
            answer = _query_yes_no("Continue integrating this change?")
            if answer != "yes":
                return False
        print

        # Check if there are files in the change outside of the source
        # branch area.
        if outside_paths:
            if interactive:
                answer = _query_yes_no(textwrap.dedent("""
                    The following files from change %s are outside the %r base dir:
                        %s
                    Would you like to ignore them and continue?""")
                    % (changenum, self.name,
                       "\n    ".join(outside_paths)))
                if answer != "yes":
                    return False
            else:
                log.warn("ignoring files outside the %r dir: '%s'",
                         self.name, "', '".join(outside_paths))
        if not inside_paths:
            log.error("There are no files in change %s that are in %r "
                      "tree. Aborting.", changenum, self.name)
            return False

        # Ensure that none of the target files are modified/opened.
        modified_paths = [p for p in dst_paths if
                          dst_branch.is_modified_or_open(p)]
        if modified_paths:
            print textwrap.dedent("""
                ***
                The following target files that would be part of this
                integration are open and/or modified:
                    %s
    
                This script cannot integrate files that are already open:
                it would pollute the integration. You need to either first
                check these in or revert your changes.
                ***""") \
                % "\n    ".join(modified_paths)
            return False

        # Do the integration, as best as possible.
        if dst_branch.scc_type == "p4":
            raise Error("reinstate the old kointegrate 'p4 integrate' "
                        "logic for this p4->p4 integration")

        # - write out patches for all the edited files
        def _diff_for_file(change, file):
            depotFile = file["depotFile"]
            for diff in change["diff"]:
                if diff["depotFile"] == depotFile:
                    return diff["text"]
            raise RuntimeError("no diff for `%s' in change %s"
                               % (file["rel_path"], change["change"]))
        
        tmp_dir = tempfile.mkdtemp()
        try:
            for i, f in enumerate(change["files"]):
                patch_path = join(tmp_dir, "%d.patch" % i)
                fout = open(patch_path, 'w')
                norm_rel_path = f["rel_path"].replace(os.sep, '/')
                fout.write("Index: %s\n" % norm_rel_path)
                fout.write("--- %s\n" % norm_rel_path)
                fout.write("+++ %s\n" % norm_rel_path)
                diff = _diff_for_file(change, f)
                fout.write(diff)
                if not diff.endswith("\n"):
                    fout.write("\n")  #TODO: not sure about this part
                fout.write("End of Patch.\n\n")
                fout.close()
                f["patch_path"] = patch_path
    
            # - do a dry-run attempt to patch (abort if any fail)
            patch_exe = _getPatchExe()
            for f in change["files"]:
                if "patch_path" not in f:
                    continue
                try:
                    _assertCanApplyPatch(patch_exe, f["patch_path"],
                                         dst_branch.base_dir)
                except Error, ex:
                    if force:
                        log.warn(str(ex))
                    else:
                        raise
    
            # - apply the edits
            changes_made = []
            for f in change["files"]:
                if "patch_path" not in f:
                    continue
                patch_path = f["patch_path"]
                dst_path = join(dst_branch.base_dir, f["rel_path"])
                dst_branch.edit(dst_path)
                eol_before = eol.eol_info_from_path(dst_path)[0]
                try:
                    applied = _applyPatch(patch_exe, dirname(patch_path),
                                          basename(patch_path),
                                          dst_branch.base_dir)
                except Error, ex:
                    if force:
                        log.warn(str(ex))
                        applied = True
                    else:
                        raise
                eol_after = eol.eol_info_from_path(dst_path)[0]
                if eol_after != eol_before:
                    assert eol_before != None
                    log.info("restore EOLs for `%s' (damaged by patch)",
                             dst_path)
                    eol.convert_path_eol(dst_path, eol_before)
                if applied:
                    changes_made.append("patched `%s'" % f["rel_path"])
            
            # - do deletes and adds
            for f in change["files"]:
                action = f["action"]
                rel_path = f["rel_path"]
                if action == "delete":
                    dst_branch.delete(rel_path)
                    changes_made.append("delete `%s'" % rel_path)
                elif action == ("add", "branch"):
                    raise "TODO: really add the file"
                    dst_branch.add(rel_path)
                    changes_made.append("add `%s'" % rel_path)
                elif action in ("edit", "integrate"):
                    pass # already handled above
                else:
                    raise Error("don't know how to handle integrating "
                                "'%s' action" % action)

            # Abort if no actual changes made.
            if not changes_made:
                print textwrap.dedent("""
                    No changes were necessary to integrate this change.
                    Perhaps it has already been integrated?""")
                return False

            # Setup to commit the integration: i.e. create a pending
            # changelist (p4), provide a good checkin message.
            dst_branch.setup_to_commit(changenum, change["user"],
                                       change["description"], self,
                                       dst_paths, interactive)
        finally:
            if exists(tmp_dir) and not log.isEnabledFor(logging.DEBUG):
                shutil.rmtree(tmp_dir)

    def is_modified_or_open(self, path):
        import p4lib
        p4 = p4lib.P4()
        return p4.opened(path) and True or False

    def commit_summary(self, changenum):
        """Return a short single-line summary of a commit with the
        given changenum suitable for posting to a bug log.
        
        Currently ActiveState's bugzilla has auto-linking for the
        following patterns:
            change \d+          -> ActiveState perforce change link
            r\d+                -> svn.activestate.com revision link
            openkomodo r\d+     -> svn.openkomodo.com revision link
        so we try to accomodate that.
        
        Template: PROJECT-NAME change CHANGENUM
        """
        project_name = basename(self.base_dir)
        return "%s change %s" % (project_name, changenum)

    def setup_to_commit(self, changenum, user, desc, src_branch, paths,
                        interactive):
        # Create a changelist with the changes.
        import p4lib
        p4 = p4lib.P4()
        change = p4.change(paths,
                           "Integrate change %d by %s from %r branch:\n%s"
                           % (changenum, user, src_branch.name, desc))
        print textwrap.dedent("""
            Created change %d integrating change %d from %r branch.
            Use 'p4 submit -c %d' to submit this integration.
            PLEASE LOOK AT IT BEFORE YOU DO:
                p4 describe %d | less
                px diff -du -c %d | less""") \
        % (change["change"], changenum, src_branch.name,
           change["change"], change["change"], change["change"])
        return self.commit_summary(change["change"])

class SVNBranch(Branch):
    scc_type = "svn"
    def __repr__(self):
        return "<SVNBranch: %r at '%s'>" \
               % (self.name, self.base_dir)
    def __str__(self):
        return "%r branch at '%s' (svn)" % (self.name, self.base_dir)

    _svn_exe_cache = None
    @property
    def _svn_exe(self):
        if self._svn_exe_cache is None:
            import which
            self._svn_exe_cache = which.which('svn')
        return self._svn_exe_cache

    def _svn_info(self, target):
        stdout = _capture_stdout([self._svn_exe, 'info', target])
        info = {}
        for line in stdout.splitlines(0):
            if not line.strip(): continue
            key, value = line.split(":", 1)
            info[key.strip()] = value.strip()
        return info

    _svn_log_header_re = re.compile(r"""
        ^r(?P<revision>\d+)\s\|\s(?P<author>.*?)\s\|
        """, re.VERBOSE)
    def _svn_log_rev(self, rev):
        stdout = _capture_stdout([self._svn_exe, 'log', '-r', str(rev),
                                  '-v', self.base_dir])
        lines = stdout.splitlines(0)
        data = self._svn_log_header_re.match(lines[1]).groupdict()
        assert lines[2] == "Changed paths:", \
            "3rd svn log line is not as expected: %r" % lines[2]
        files = []
        idx = 3
        while idx < len(lines):
            line = lines[idx].strip()
            if not line:
                break
            action, svnpath = line.split(' ', 1)

            # A *svn mv* looks like this:
            #    A /komodo/trunk/mozilla/patches-new/MOZILLA_1_8_BRANCH/autoupdate_base_dir.patch (from /komodo/trunk/mozilla/patches-new/autoupdate_base_dir.patch:9351)
            #    D /komodo/trunk/mozilla/patches-new/autoupdate_base_dir.patch
            # Limitation: For now we are going to look the "mv"
            # connection and do separate "A" and "D".
            if " (from " in svnpath:
                svnpath = svnpath.split(" (from ", 1)[0]
                log.warn("dropping info that `%s' was *moved* ('add' and "
                         "'delete' will be done separately",
                         self._svn_relpath(svnpath))

            rel_path = self._svn_relpath(svnpath)
            files.append({
                "action": action,
                "rel_path": rel_path,
                "path": join(self.base_dir, rel_path),
            })
            idx += 1
        data["files"] = files
        data["desc"] = '\n'.join(lines[idx+1:-1])
        data["revision"] = int(data["revision"])
        return data

    def _svn_relpath(self, path):
        """Relativize the SVN repo path using a heuristic."""
        parts = path.split('/')
        for i, part in enumerate(parts):
            if part == "trunk":
                return normpath('/'.join(parts[i+1:]))
            elif part in ("branches", "tags"):
                return normpath('/'.join(parts[i+2:]))
        raise Error("couldn't heuristically relativize svn path: %r"
                    % path)

    def edit(self, path):
        pass
    def add(self, path, isdir=False):
        if not isabs(path):
            abs_path = join(self.base_dir, path)
        if isdir:
            log.info("svn mkdir %s", path)
            _patchRun([self._svn_exe, "mkdir", abs_path])
        else:
            log.info("svn add %s", path)
            _patchRun([self._svn_exe, "add", abs_path])
    def delete(self, path):
        log.info("svn delete %s", path)
        if not isabs(path):
            path = join(self.base_dir, path)
        _patchRun([self._svn_exe, "delete", path])

    def integrate(self, changenum, dst_branches, interactive,
                  exclude_outside_paths, excludes=[], force=False):
        # Gather some info about the change to integrate.
        change = self._svn_log_rev(changenum)
        indeces_to_del = []
        for i, f in enumerate(change["files"][:]):
            matching_excludes = [e for e in excludes
                                 if fnmatch.fnmatch(f["rel_path"], e)]
            if matching_excludes:
                log.info("skipping `%s' (matches excludes: '%s')",
                         f["rel_path"], "', '".join(matching_excludes))
                indeces_to_del.append(i)
        for i in reversed(indeces_to_del):
            del change["files"][i]
        rel_paths = [f["rel_path"] for f in change["files"]]
        dst_paths_from_branch_name = {}
        for dst_branch in dst_branches:
            dst_paths_from_branch_name[dst_branch.name] \
                = [join(dst_branch.base_dir, p) for p in rel_paths]

        # Check if there is anything to integrate.
        if not change["files"]:
            log.error("There are no files in change %s to integrate. "
                      "Aborting.", changenum)
            return False

        # Give the user the chance to abort.
        print "  change: %s" % changenum
        print "    desc: %s" % _one_line_summary_from_text(change["desc"], 60)
        print "      by: %s" % change["author"]
        if len(dst_branches) == 1:
            print "      to: %s" % dst_branch.base_dir
        else:
            for i, dst_branch in enumerate(dst_branches):
                if i == 0:
                    print "      to: %d. %s (%s)" % (i+1, dst_branch.base_dir, dst_branch.name)
                else:
                    print "          %d. %s (%s)" % (i+1, dst_branch.base_dir, dst_branch.name)
        if len(rel_paths) > 7:
            ellipsis = '...and %d other files' % (len(rel_paths)-7)
            print "   files: %s" \
                  % _indent(' '.join(rel_paths[:7] + [ellipsis]), 10, True)
        else:
            print "   files: %s" % _indent(' '.join(rel_paths), 10, True)
        if interactive:
            print
            answer = _query_yes_no("Continue integrating this change?")
            if answer != "yes":
                return False
        print

        # Ensure that none of the target files are modified/opened.
        modified_paths = [
            p
            for dst_branch in dst_branches
            for p in dst_paths_from_branch_name[dst_branch.name]
            if dst_branch.is_modified_or_open(p)
               # Dirs give false positives, and we abort handling dirs
               # below anyway.
               and not isdir(p)
        ]
        if modified_paths:
            print textwrap.dedent("""
                ***
                The following target files that would be part of this
                integration are open and/or modified:
                    %s
    
                This script cannot integrate files that are already open:
                it would pollute the integration. You need to either first
                check these in or revert your changes.
                ***""") \
                % "\n    ".join(modified_paths)
            return False

        # Do the integration, as best as possible.
        # - write out patches for all the edited files
        tmp_dir = tempfile.mkdtemp()
        try:
            for i, f in enumerate(change["files"]):
                if f["action"] != "M":
                    continue
                patch_path = join(tmp_dir, "%d.patch" % i)
                fout = open(patch_path, 'w')
                if isdir(f["path"]):
                    raise Error("cannot integrate a directory: `%s' (you "
                        "are probably just editing properties on this dir, "
                        "use the '-x %s' option to skip this path)"
                        % (f["rel_path"], f["rel_path"]))
                diff = _capture_stdout([
                    self._svn_exe, "diff",
                    "-r%d:%d" % (changenum-1, changenum),
                    f["rel_path"]
                ], cwd=self.base_dir)
                fout.write(diff)
                fout.close()
                f["patch_path"] = patch_path
    
            # - do a dry-run attempt to patch (abort if any fail)
            patch_exe = _getPatchExe()
            patching_failures = []
            for dst_branch in dst_branches:
                for f in change["files"]:
                    if "patch_path" not in f:
                        continue
                    try:
                        _assertCanApplyPatch(patch_exe, f["patch_path"],
                                             dst_branch.base_dir)
                    except Error, ex:
                        if force:
                            log.warn(str(ex))
                        else:
                            patching_failures.append(str(ex))
            if patching_failures:
                raise Error("During a dry-run patching attempt there were "
                            "the following failures:\n    %s\n\n"
                            "You could use the `-x SUBPATH` option to skip "
                            "a particular file."
                            % ("\n    ".join(patching_failures)))
    
            # - apply the edits
            changes_made = []
            for dst_branch in dst_branches:
                print "--- making changes to '%s' branch ---" % dst_branch.name
                for f in change["files"]:
                    if "patch_path" not in f:
                        continue
                    patch_path = f["patch_path"]
                    dst_path = join(dst_branch.base_dir, f["rel_path"])
                    dst_branch.edit(dst_path)
                    eol_before = eol.eol_info_from_path(dst_path)[0]
                    try:
                        applied = _applyPatch(patch_exe, dirname(patch_path),
                                              basename(patch_path),
                                              dst_branch.base_dir)
                    except Error, ex:
                        if force:
                            log.warn(str(ex))
                            applied = True
                        else:
                            raise
                    eol_after = eol.eol_info_from_path(dst_path)[0]
                    if eol_after != eol_before:
                        assert eol_before != None
                        log.info("restore EOLs for `%s' (damaged by patch)",
                                 dst_path)
                        eol.convert_path_eol(dst_path, eol_before)
                    if applied:
                        changes_made.append("patched `%s' (%s)" % (
                            f["rel_path"], dst_branch.name))
            
                # - do deletes and adds
                for f in change["files"]:
                    action = f["action"]
                    rel_path = f["rel_path"]
                    if action == "D":
                        dst_branch.delete(rel_path)
                        changes_made.append("delete `%s' (%s)" % (
                            rel_path, dst_branch.name))
                    elif action == "A":
                        src_path = join(self.base_dir, rel_path)
                        if isdir(src_path):
                            dst_branch.add(rel_path, isdir=True)
                            changes_made.append("mkdir `%s' (%s)" % (
                                rel_path, dst_branch.name))
                        else:
                            dst_path = join(dst_branch.base_dir, rel_path)
                            argv = [self._svn_exe, 'cat', '-r', str(changenum),
                                    src_path]
                            log.debug("running: %s", argv)
                            p = subprocess.Popen(argv,
                                                 stderr=subprocess.PIPE,
                                                 stdout=subprocess.PIPE)
                            stdout = p.stdout.read()
                            retval = p.wait()
                            if retval:
                                stderr = p.stderr.read()
                                extra = ""
                                if "has no URL" in stderr:
                                    extra = "\n***\n%s\n***\n" % textwrap.fill(
                                        "The 'svn: ... has no URL' "
                                        "error from subversion typically indicates "
                                        "that you are trying to integrate a file "
                                        "that has since be deleted from the "
                                        "current repo. I know of no easy way to "
                                        "get the original file contents with 'svn' "
                                        "-- hence this file cannot be integrated "
                                        "with this script. You could consider "
                                        "using the '-x' option to exclude this "
                                        "file from the change to integrate.")
                                raise Error("error running `svn cat`:\n"
                                            "argv: %r\n"
                                            "stderr:\n%s%s"
                                            % (argv, _indent(stderr), extra))
                            fout = open(dst_path, 'wb')
                            fout.write(stdout)
                            fout.close()
                            assert exists(dst_path), \
                                "`%s' couldn't be retrieved from svn" % dst_path
                            dst_branch.add(rel_path)
                            changes_made.append("add `%s' (%s)" % (
                                rel_path, dst_branch.name))
                    elif action == "M":
                        pass # already handled above
                    else:
                        raise Error("don't know how to handle integrating "
                                    "'%s' action" % action)

            # Abort if no actual changes made.
            if not changes_made:
                print textwrap.dedent("""
                    No changes were necessary to integrate this change.
                    Perhaps it has already been integrated?""")
                return False

            # Setup to commit the integration: i.e. create a pending
            # changelist (p4), provide a good checkin message.
            commit_summaries = [self.commit_summary(changenum)]
            for dst_branch in dst_branches:
                dst_paths = dst_paths_from_branch_name[dst_branch.name]
                commit_summary = dst_branch.setup_to_commit(
                    changenum, change["author"], change["desc"], self,
                    dst_paths, interactive)
                if commit_summary:
                    commit_summaries.append(commit_summary)

            # Print a summary of commits for use in a bugzilla comment.
            print "\n\n-- Check-in summary (for bugzilla comment):"
            for s in commit_summaries:
                print s
        finally:
            if False and exists(tmp_dir) and not log.isEnabledFor(logging.DEBUG):
                shutil.rmtree(tmp_dir)

    def is_modified_or_open(self, path):
        stdout, stderr, retval = _patchRun(["svn", "status", path])
        if stdout:
            return True
        else:
            return False

    def commit_summary(self, changenum):
        """Return a short single-line summary of a commit with the
        given changenum suitable for posting to a bug log.

        Currently ActiveState's bugzilla has auto-linking for the
        following patterns:
            change \d+          -> ActiveState perforce change link
            r\d+                -> svn.activestate.com revision link
            openkomodo r\d+     -> svn.openkomodo.com revision link
        so we try to accomodate that.
        
        Template: PROJECT-NAME rCHANGENUM (BRANCH-NAME)
        """
        from urlparse import urlparse
        url = self._svn_info(self.base_dir)["URL"]
        path = urlparse(url)[2]
        bits = path.split('/')
        if bits[-1] == "trunk":
            branch_name = "trunk"
            project_name = bits[-2]
        elif bits[-2] == "branches":
            branch_name = "%s branch" % bits[-1]
            project_name = bits[-3]
        elif bits[-2] == "tags":
            branch_name = "%s tag" % bits[-1]
            project_name = bits[-3]
        else:
            branch_name = None
            project_name = bits[-1]
        if branch_name is None:
            return "%s r%s" % (project_name, changenum)
        else:
            return "%s r%s (%s)" % (project_name, changenum, branch_name)

    def setup_to_commit(self, changenum, user, desc, src_branch, paths,
                        interactive):
        """Returns a (string) commit summary if a commit was done,
        else returns None.
        """
        rel_paths = [p[len(self.base_dir)+1:] for p in paths]
        msg = "Integrate change %d by %s from %r branch:\n%s" \
              % (changenum, user, src_branch.name, desc.rstrip())
        print "\n\nReady to commit to '%s' branch:" % self.name
        print _indent(msg, 2)

        auto_commit = True
        if interactive:
            answer = _query_yes_no(
                "\nWould you like this script to automatically commit\n"
                "this integration to the '%s' branch?" % self.name,
                default=None)
            if answer != "yes":
                auto_commit = False
        
        if auto_commit:
            argv = [self._svn_exe, "commit", "-m", msg] + rel_paths
            stdout, stderr, retval = _patchRun(argv, self.base_dir)
            sys.stdout.write(stdout)
            if stderr or retval:
                raise Error("error commiting: %s\n%s"
                            % (retval, _indent(stderr)))
            revision_re = re.compile(r'Committed revision (\d+)\.')
            try:
                revision = revision_re.search(stdout).group(1)
            except AttributeError:
                log.warn("Couldn't determine commited revision from "
                         "'svn commit' output: %r", stdout)
                revision = "???"
            return self.commit_summary(revision)
        else:
            print textwrap.dedent("""
                ***
                You can manually commit the integration with the following
                commands:
                    cd %s
                    svn ci %s
                
                Please use the above commit message.
                ***""") \
                % (self.base_dir, ' '.join(rel_paths))
        


#---- configuration/prefs handling

class Configuration(SafeConfigParser):
    branches = None
    
    def __init__(self):
        SafeConfigParser.__init__(self)
        self._load()
    
    @property
    def cfg_path(self):
        user_data_dir = applib.user_data_dir("komodo-dev", "ActiveState")
        return join(user_data_dir, "kointegrate.ini")

    def _load(self):
        self.read(self.cfg_path)
        self.branches = {}
        if self.has_section("active-branches"):
            for name, base_dir in self.items("active-branches"):
                base_dir = expanduser(base_dir)
                if not exists(base_dir):
                    self.branches[name] = NonExistantBranch(name, base_dir)
                elif isdir(join(base_dir, ".svn")):
                    self.branches[name] = SVNBranch(name, base_dir)
                else:
                    # Presumably a P4 branch.
                    self.branches[name] = P4Branch(name, base_dir)


cfg = Configuration()



#---- main functionality

def kointegrate(changenum, dst_branch_names, interactive=True,
                exclude_outside_paths=False, excludes=None,
                force=False):
    """Returns True if successfully setup the integration."""
    if not cfg.branches:
        raise Error("You haven't configured any Komodo branches. "
                    "See `kointegrate.py --help-ini' for help on "
                    "configuring this script.")

    dst_branches = []
    for dst_branch_name in dst_branch_names:
        try:
            dst_branches.append(cfg.branches[dst_branch_name])
        except KeyError:
            raise Error("`%s' is an unknown active Komodo branch name "
                        "(known branches are: '%s')"
                        % (dst_branch_name,
                           "', '".join(cfg.branches.keys())))

    # Figure out what source branch we are taking about.
    src_branch = None
    norm_cwd_plus_sep = normcase(os.getcwd()) + os.sep
    for branch in cfg.branches.values():
        norm_branch_dir_plus_sep = normcase(branch.base_dir) + os.sep
        if norm_cwd_plus_sep.startswith(norm_branch_dir_plus_sep):
            src_branch = branch
            break
    else:
        raise Error(textwrap.dedent("""\
            The current directory is not in any of your configured Komodo
            branches. You must either update your configuration for this
            script (see `kointegrate --help') or change to an active
            branch working copy directory.
            """))

    log.debug("integrate change %s from %r -> '%s'",
              changenum, src_branch.name,
              "', '".join(b.name for b in dst_branches))
    return src_branch.integrate(
        changenum, dst_branches, interactive=interactive,
        exclude_outside_paths=exclude_outside_paths,
        excludes=excludes, force=force)
        



#---- internal support stuff

def _capture_stdout(argv, cwd=None, ignore_status=False):
    p = subprocess.Popen(argv, cwd=cwd,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    stdout = p.stdout.read()
    stderr = p.stderr.read()
    status = p.wait()  # raise if non-zero status?
    if status and not ignore_status:
        raise OSError("running '%s' failed: %d: %s"
                      % (' '.join(argv), status, stderr))
    return stdout

# Adapted from patchtree.py
def _patchRun(argv, cwd=None, stdin=None):
    p = subprocess.Popen(argv, cwd=cwd, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, stdin=subprocess.PIPE)
    if stdin is not None:
        p.stdin.write(stdin)
    p.stdin.close()
    stdout = p.stdout.read()
    stderr = p.stderr.read()
    retval = p.wait()
    return stdout, stderr, retval

# Adapted from patchtree.py.
def _assertCanApplyPatch(patchExe, patchFile, sourceDir, reverse=0,
                         patchSrcFile=None, patchArgs=[]):
    """Raise an error if the given patch will not apply cleanly (does not
    raise if the patch is already applied).
    
        "patchExe" is a path to a patch executable to use.
        "patchFile" is the path the the patch file.
        "sourceDir" is the base directory of the source tree to patch. All
            patches are presumed to be applicable from this directory.
        "reverse" (optional, default false) is a boolean indicating if the
            patch should be considered in reverse.
        "patchSrcFile" (optional) is the path to the patch _source_ location
            for helpful error messages -- the patch may have been processed.
        "patchArgs" (optional) is a list of patch executable arguments to
            include in invocations.
    """
    inReverse = (reverse and " in reverse" or "")
    log.debug("assert can apply patch%s: %s", inReverse, patchFile)
    baseArgv = [patchExe, "-f", "-p0", "-g0"] + patchArgs
    patchContent = open(patchFile, 'r').read()

    # Avoid this check for now because it can result in false positives
    # (thinking the patch has already been applied when it has not).
    ## Skip out if the patch has already been applied.
    #argv = baseArgv + ["--dry-run"]
    #if not reverse:
    #    argv.append("-R")
    #log.debug("    see if already applied%s: run %s in '%s'", inReverse,
    #          argv, sourceDir)
    #stdout, stderr, retval = _patchRun(argv, cwd=sourceDir, stdin=patchContent)
    #if not retval: # i.e. reverse patch would apply
    #    log.debug("    patch already applied%s: skipping", inReverse)
    #    return

    # Fail if the patch would not apply cleanly.
    argv = baseArgv + ["--dry-run"]
    if reverse:
        argv.append("-R")
    log.debug("    see if will apply cleanly%s: run %s in '%s'", inReverse,
              argv, sourceDir)
    stdout, stderr, retval = _patchRun(argv, cwd=sourceDir, stdin=patchContent)
    if retval:
        errmsg = textwrap.dedent("""\
            patch '%s' will not apply cleanly%s:
              patch source: %s
              argv:         %s
              stdin:        %s
              cwd:          %s
            """) % (patchFile, inReverse, patchSrcFile or patchFile,
                    argv, patchFile, sourceDir)
        if stdout.strip():
            errmsg += "  stdout:\n%s" % _indent(stdout)
        if stderr.strip():
            errmsg += "  stderr:\n%s" % _indent(stderr)
        raise Error(errmsg)

# Adapted from patchtree.py.
def _getPatchExe(patchExe=None):
    import which
    if patchExe is None:
        try:
            patchExe = which.which("patch")
        except which.WhichError:
            raise Error("could not find a 'patch' executable on your PATH")
    # Assert that it exists.
    if not os.path.exists(patchExe):
        raise Error("'%s' does not exist" % patchExe)
    # Assert that this isn't cygwin patch on Windows.
    if re.search("(?i)cygwin", os.path.abspath(patchExe)):
        raise Error("'%s' looks like it is from Cygwin. This patch.exe "
                    "tends to convert EOLs to Unix-style willy-nilly. "
                    "Find a native patch.exe. (Note: Trent and Gsar "
                    "have one.)" % patchExe)
    #XXX Assert that it isn't the sucky default Solaris patch.
    return patchExe

# Adapted from patchtree.py.
def _applyPatch(patchExe, baseDir, patchRelPath, sourceDir, reverse=0,
                dryRun=0, patchArgs=[]):
    """Apply a patch file to the given source directory.
    
        "patchExe" is a path to a patch executable to use.
        "baseDir" is the base directory of the working patch set image.
        "patchRelPath" is the relative path of the patch under the working
            directory.
        "sourceDir" is the base directory of the source tree to patch. All
            patches are presumed to be applicable from this directory.
        "reverse" (optional, default false) is a boolean indicating if the
            patch should be considered in reverse.
        "dryRun" (optional, default false), if true, indicates that
            everything but the actual patching should be done.
        "patchArgs" (optional) is a list of patch executable arguments to
            include in invocations.
    
    Returns True if applied, False if skipped (already applied) and
    raised an error if could not apply.
    """
    inReverse = (reverse and " in reverse" or "")
    baseArgv = [patchExe, "-f", "-p0", "-g0"] + patchArgs
    patchFile = os.path.join(baseDir, patchRelPath)
    patchContent = open(patchFile, 'r').read()

    # Avoid this check for now because it can result in false positives
    # (thinking the patch has already been applied when it has not).
    ## Skip out if the patch has already been applied.
    #argv = baseArgv + ["--dry-run"]
    #if not reverse:
    #    argv.append("-R")
    #stdout, stderr, retval = _patchRun(argv, cwd=sourceDir, stdin=patchContent)
    #if not retval: # i.e. reverse patch would apply
    #    log.debug("skip application of '%s'%s: already applied", patchRelPath,
    #             inReverse)
    #    return False

    # Apply the patch.
    if dryRun:
        log.debug("apply '%s'%s (dry run)", patchRelPath, inReverse)
        argv = baseArgv + ["--dry-run"]
    else:
        log.debug("apply '%s'%s", patchRelPath, inReverse)
        argv = baseArgv
    if reverse:
        argv.append("-R")
    log.debug("run %s in '%s' (stdin '%s')", argv, sourceDir, patchFile)
    stdout, stderr, retval = _patchRun(argv, cwd=sourceDir, stdin=patchContent)
    sys.stdout.write(stdout)
    sys.stdout.flush()
    if retval:
        raise Error("error applying patch '%s'%s: argv=%r, cwd=%r, retval=%r"
                    % (patchFile, inReverse, argv, sourceDir, retval))
    return True

# Recipe: indent (0.2.1)
def _indent(s, width=4, skip_first_line=False):
    """_indent(s, [width=4]) -> 's' indented by 'width' spaces

    The optional "skip_first_line" argument is a boolean (default False)
    indicating if the first line should NOT be indented.
    """
    lines = s.splitlines(1)
    indentstr = ' '*width
    if skip_first_line:
        return indentstr.join(lines)
    else:
        return indentstr + indentstr.join(lines)

# Recipe: text_escape (0.1)
def _escaped_text_from_text(text, escapes="eol"):
    r"""Return escaped version of text.

        "escapes" is either a mapping of chars in the source text to
            replacement text for each such char or one of a set of
            strings identifying a particular escape style:
                eol
                    replace EOL chars with '\r' and '\n', maintain the actual
                    EOLs though too
                whitespace
                    replace EOL chars as above, tabs with '\t' and spaces
                    with periods ('.')
                eol-one-line
                    replace EOL chars with '\r' and '\n'
                whitespace-one-line
                    replace EOL chars as above, tabs with '\t' and spaces
                    with periods ('.')
    """
    #TODO:
    # - Add 'c-string' style.
    # - Add _escaped_html_from_text() with a similar call sig.
    import re
    
    if isinstance(escapes, basestring):
        if escapes == "eol":
            escapes = {'\r\n': "\\r\\n\r\n", '\n': "\\n\n", '\r': "\\r\r"}
        elif escapes == "whitespace":
            escapes = {'\r\n': "\\r\\n\r\n", '\n': "\\n\n", '\r': "\\r\r",
                       '\t': "\\t", ' ': "."}
        elif escapes == "eol-one-line":
            escapes = {'\n': "\\n", '\r': "\\r"}
        elif escapes == "whitespace-one-line":
            escapes = {'\n': "\\n", '\r': "\\r", '\t': "\\t", ' ': '.'}
        else:
            raise ValueError("unknown text escape style: %r" % escapes)

    # Sort longer replacements first to allow, e.g. '\r\n' to beat '\r' and
    # '\n'.
    escapes_keys = escapes.keys()
    escapes_keys.sort(key=lambda a: len(a), reverse=True)
    def repl(match):
        val = escapes[match.group(0)]
        return val
    escaped = re.sub("(%s)" % '|'.join([re.escape(k) for k in escapes_keys]),
                     repl,
                     text)

    return escaped

def _one_line_summary_from_text(text, length=78,
        escapes={'\n':"\\n", '\r':"\\r", '\t':"\\t"}):
    r"""Summarize the given text with one line of the given length.
    
        "text" is the text to summarize
        "length" (default 78) is the max length for the summary
        "escapes" is a mapping of chars in the source text to
            replacement text for each such char. By default '\r', '\n'
            and '\t' are escaped with their '\'-escaped repr.
    """
    if len(text) > length:
        head = text[:length-3]
    else:
        head = text
    escaped = _escaped_text_from_text(head, escapes)
    if len(text) > length:
        summary = escaped[:length-3] + "..."
    else:
        summary = escaped
    return summary


# Recipe: query_yes_no (1.0)
def _query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.
    
    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is one of "yes" or "no".
    """
    valid = {"yes":"yes",   "y":"yes",  "ye":"yes",
             "no":"no",     "n":"no"}
    if default == None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while 1:
        sys.stdout.write(question + prompt)
        choice = raw_input().lower()
        if default is not None and choice == '':
            return default
        elif choice in valid.keys():
            return valid[choice]
        else:
            sys.stdout.write("Please repond with 'yes' or 'no' "\
                             "(or 'y' or 'n').\n")



#---- mainline

class _NoReflowFormatter(optparse.IndentedHelpFormatter):
    """An optparse formatter that does NOT reflow the description."""
    def format_description(self, description):
        return description or ""

def main(argv=sys.argv):
    version = "%prog "+__version__
    desc = __doc__ + "\nConfigured active Komodo branches:\n    "
    if not cfg.branches:
        desc += "(none configured)"
    else:
        desc += "\n    ".join(map(str,
            [b for (n,b) in sorted(cfg.branches.items())]))
    desc += "\n\nUse `kointegrate --help-ini' for help on configuring.\n"

    parser = optparse.OptionParser(usage="",
        version=version, description=desc,
        formatter=_NoReflowFormatter())
    parser.add_option("--help-ini", action="store_true",
                      help="print help on configuring kointegrate")
    parser.add_option("-v", "--verbose", dest="log_level",
                      action="store_const", const=logging.DEBUG,
                      help="more verbose output")
    parser.add_option("-i", "--interactive", action="store_true",
                      help="interactively verify steps of integration "
                           "(default)")
    parser.add_option("--non-interactive", action="store_false",
                      dest="interactive", help="no interaction")
    parser.add_option("-f", "--force", action="store_true",
                      help="force application of patches that won't "
                           "apply cleanly")
    parser.add_option("-X", "--exclude-outside-paths", action="store_true",
                      help="exclude (ignore) paths in the changeset "
                           "outside of the branch")
    parser.add_option("-x", "--exclude", dest="excludes", action="append",
                      metavar="PATTERN",
                      help="Exclude files in the change matching the "
                           "given glob pattern. This is matched against "
                           "the file relative path.")
    parser.set_defaults(log_level=logging.INFO, exclude_outside_paths=False,
                        interactive=True, excludes=[], force=False)
    opts, args = parser.parse_args()
    log.setLevel(opts.log_level)
    
    if opts.help_ini:
        print textwrap.dedent("""
            Configuring kointegrate.py
            --------------------------
            
            This script uses a "kointegrate.ini" file here:
                %s
            
            The "[active-branches]" section of that file (a normal
            INI-syntax file) is used. Each entry in that section should
            be of the form:
            
                <branch-nickname> = <full-path-to-branch-working-copy>
            
            For example,

                [active-branches]
                openkomodo = /home/me/play/openkomodo
                devel      = /home/me/wrk/Komodo-devel
                4.2        = /home/me/wrk/Komodo-4.2
        """ % cfg.cfg_path)
        return

    if len(args) < 2:
        log.error("incorrect number of arguments: %s", args)
        log.error("(See 'kointegrate --help'.)")
        return 1
    try:
        changenum = int(args[0])
    except ValueError, ex:
        log.error("<changenum> must be an integer: %r", args[0])
        log.error("(See 'kointegrate --help'.)")
        return 1
    dst_branch_names = args[1:]

    integrated = kointegrate(
        changenum, dst_branch_names, interactive=opts.interactive,
        exclude_outside_paths=opts.exclude_outside_paths,
        excludes=opts.excludes, force=opts.force)
    if integrated:
        return 0
    else:
        return 1

def _setup_logging():
    logging.basicConfig()

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
        if log.level <= logging.DEBUG:
            import traceback
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



