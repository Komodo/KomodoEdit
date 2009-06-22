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

Notes:
- Limitation: This does NOT handle svn properties!
- Changes to files outside of the source tree dir are *ignored*.
"""

__version_info__ = (1, 2, 2)
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
from operator import itemgetter
import subprocess
import shutil
from urlparse import urlparse
from ConfigParser import SafeConfigParser
from xml.etree import cElementTree as ET


import applib
sys.path.insert(0, join(dirname(dirname(abspath(__file__))), "src",
                        "codeintel", "support"))
import eol as eollib # cherry-pick this from codeintel support area



class Error(Exception):
    pass
class OutsidePathError(Error):
    """Error indicating that the given svn path is not under the
    working tree base directory.
    """
    def __init__(self, path):
        self.path = path



#---- globals

log = logging.getLogger("kointegrate")
#log.setLevel(logging.DEBUG)



#---- handling of active branches

class Branch(object):
    def __init__(self, name, base_dir):
        self.name = name
        self.base_dir = normpath(base_dir)
    
    @property
    def desc(self):
        return self.name

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

    @property
    def desc(self):
        return basename(self.base_dir)

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
                
                # Awful HACK around the "$Id: kointegrate.py 3754 2009-06-15 19:57:11Z trentm $" (et al) keyword expansion
                # problem: If "$Id: kointegrate.py 3754 2009-06-15 19:57:11Z trentm $" is in the patch content but it is
                # exanded in target file, then `patch` won't be able to
                # apply.
                #TODO: Better soln is to modify the *patch*, but that's harder.
                f = open(f["patch_path"], 'rb')
                try:
                    patchContent = f.read()
                finally:
                    f.close()
                if "$Id: kointegrate.py 3754 2009-06-15 19:57:11Z trentm $" in patchContent:
                    XXX
                    dst_path = join(dst_branch.base_dir, f["rel_path"])
                    origDstContent = open(dst_path, 'rb').read()
                    newDstContent = re.sub(r"\$Id: [^$]+\$", "$Id: kointegrate.py 3754 2009-06-15 19:57:11Z trentm $", origDstContent)
                    if newDstContent != origDstContent:
                        open(dst_path, 'wb').write(newDstContent)
                
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
                eol_before = eollib.eol_info_from_path(dst_path)[0]
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
                eol_after = eollib.eol_info_from_path(dst_path)[0]
                if eol_after != eol_before:
                    assert eol_before != None
                    log.info("restore EOLs for `%s' (damaged by patch)",
                             dst_path)
                    eollib.convert_path_eol(dst_path, eol_before)
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

    def commit_summary(self, changenum=None):
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
        changenum_str = changenum is not None and " %s" % changenum or ""
        return "%s change%s" % (project_name, changenum_str)

    def setup_to_commit(self, changenum, user, desc, src_branch, paths,
                        interactive):
        # Create a changelist with the changes.
        import p4lib
        p4 = p4lib.P4()
        change = p4.change(paths,
                           "%s\n\n(integrated from %s change %d by %s)"
                           % (desc.rstrip(), src_branch.desc, changenum, user))
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
    
    _base_dir_info_cache = None
    @property
    def base_dir_info(self):
        if self._base_dir_info_cache is None:
            self._base_dir_info_cache = self._svn_info(self.base_dir)
        return self._base_dir_info_cache

    _desc_cache = None
    @property
    def desc(self):
        if self._desc_cache is None:
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
                self._desc_cache = project_name
            else:
                self._desc_cache = "%s (%s)" % (project_name, branch_name)
        return self._desc_cache

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

    def _svn_is_binary(self, file_dict, changenum=None):
        repo_path = self.base_dir_info["Repository Root"] + file_dict["svnpath"]
        if changenum is not None:
            repo_path += "@%s" % changenum
        argv = [self._svn_exe, 'propget', 'svn:mime-type', repo_path]
        stdout = _capture_stdout(argv)
        return "application/octet-stream" in stdout

    def _svn_log_rev(self, rev, gather_kind=False):
        """ ...
        @param gather_kind {bool} Whether to issue extra 'svn info' calls
            to get fill in the 'kind' field.
        """
        xml = _capture_stdout([self._svn_exe, 'log', '-r', str(rev),
            '-v', self.base_dir, '--xml'])
        logentry = ET.fromstring(xml)[0]
        files = []
        data = {
            "author": logentry.findtext("author"),
            "desc": logentry.findtext("msg"),
            "revision": int(logentry.get("revision")),
            "files": files,
        }
        for path_elem in logentry.find("paths"):
            d = dict(path_elem.items())
            d["svnpath"] = svnpath = path_elem.text
            try:
                rel_path = self._svn_relpath(svnpath)
            except OutsidePathError, ex:
                log.warn("ignoring `%s' (outside `%s' base dir)", svnpath,
                    self.name)
                continue
            if "copyfrom-path" in d:
                p = d["copyfrom-path"]
                rel_cfpath = self._svn_relpath(p)
                d["copyfrom-svnpath"] = p
                d["copyfrom-path"] = join(self.base_dir, rel_cfpath)
                d["copyfrom-relpath"] = rel_cfpath
            d["rel_path"] = rel_path
            d["path"] = join(self.base_dir, rel_path)
            if gather_kind and not d.get("kind") and not d["action"] == "D":
                # Don't do this for a "D" action because I get errors:
                #   info:  (Not a versioned resource)
                #   file:///Users/trentm/tm/tmp/svn/check/trunk/checklib/content.types@1288:  (Not a valid URL)
                #   svn: A problem occurred; see other errors for details
                url = "%s%s@%s" % (self.base_dir_info["Repository Root"],
                    d["svnpath"], rev)
                d["kind"] = self._svn_info(url)["Node Kind"]
            files.append(d)
        return data
    
    def _svn_up(self, path):
        argv = [self._svn_exe, 'up', path]
        log.debug("running: %s", argv)
        p = subprocess.Popen(argv,
                             stderr=subprocess.PIPE,
                             stdout=subprocess.PIPE)
        stdout = p.stdout.read()
        retval = p.wait()
        if retval:
            stderr = p.stderr.read()
            raise Error("error running `svn up`:\n"
                        "argv: %r\n"
                        "stderr:\n%s"
                        % (argv, _indent(stderr)))

    def _svn_cat(self, url):
        argv = [self._svn_exe, 'cat', url]
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
        return stdout

    def _svn_relpath(self, path):
        bdi = self.base_dir_info
        assert bdi["URL"].startswith(bdi["Repository Root"])
        base_url = bdi["URL"][len(bdi["Repository Root"]):]
        if not path.startswith(base_url):
            raise OutsidePathError(path)
        return path[len(base_url)+1:]

    def last_rev(self, curr_user=False):
        """Return the head revision number.
        
        @param curr_user {bool} Limit to the current user.
        """
        import getpass
        rev = "HEAD"
        if curr_user:
            username = getpass.getuser()
        SENTINEL = 10
        for i in range(SENTINEL):
            rev_info = self._svn_log_rev(rev)
            if not curr_user:
                return rev_info["revision"]
            elif rev_info["author"] == username:
                return rev_info["revision"]
            else:
                rev = rev_info["revision"] - 1
        else:
            raise RuntimeError("couldn't find last rev by `%s' in last %d"
                % (username, SENTINEL))
    
    def changenums(self):
        """Generate all changenums in this branch."""
        xml = _capture_stdout([self._svn_exe, 'log',
            self.base_dir, '--xml'])
        log_elem = ET.fromstring(xml)
        for logentry in log_elem:
            yield int(logentry.get("revision"))

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

    def move(self, src_path, dst_path):
        if not isabs(src_path):
            abs_src_path = join(self.base_dir, src_path)
        if not isabs(dst_path):
            abs_dst_path = join(self.base_dir, dst_path)
        log.info("svn mv %s %s", src_path, dst_path)
        _patchRun([self._svn_exe, "mv", abs_src_path, abs_dst_path])

    def copy(self, src_path, dst_path):
        if not isabs(src_path):
            abs_src_path = join(self.base_dir, src_path)
        if not isabs(dst_path):
            abs_dst_path = join(self.base_dir, dst_path)
        log.info("svn cp %s %s", src_path, dst_path)
        _patchRun([self._svn_exe, "cp", abs_src_path, abs_dst_path])

    def integrate(self, changenum, dst_branches, interactive,
                  exclude_outside_paths, excludes=[], force=False):
        # Gather some info about the change to integrate.
        change = self._svn_log_rev(changenum, gather_kind=True)
        
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

        # If any of the files to integrate are binary, then ensure it is
        # okay to integrate them (because can't detect conflicts).
        for file_dict in change["files"]:
            if file_dict["action"] == "D":
                # The source file will have been deleted, so can't easily
                # check it if was binary. However, it won't matter for the
                # integration.
                file_dict["is_binary"] = False
            else:
                file_dict["is_binary"] = self._svn_is_binary(
                    file_dict, changenum)
        binary_paths = [f["rel_path"] for f in change["files"]
                        if f["is_binary"]]
        if binary_paths:
            log.info(textwrap.dedent("""
                ***
                The following source files are binary:
                    %s
    
                Integrating these files just copies the whole file over to
                the target. This could result in lost changes in the target.
                ***""") \
                % "\n    ".join(binary_paths))
            if interactive:
                answer = _query_yes_no("Continue integrating this change?")
                if answer != "yes":
                    return False

        # Do the integration, as best as possible.
        tmp_dir = tempfile.mkdtemp()
        try:
            # - write out patches for all the edited files
            diff_idx = 0
            for f in change["files"]:
                action = f["action"]
                if not f["is_binary"] and (
                    action == "M"
                    or (action == "A" and "copyfrom-svnpath" in f)):
                    pass
                else:
                    # Not a change that could result in a patch.
                    continue
                
                if f["kind"] == "directory":
                    if f["action"] in ("A", "D"):
                        continue
                    msg = ("cannot integrate directory modifications (rev %s): `%s' (you "
                        "are probably just editing properties on this dir, "
                        "use the '-x %s' option to skip this path)"
                        % (changenum, f["rel_path"], f["rel_path"]))
                    if interactive:
                        raise Error(msg)
                    else:
                        log.warn(msg)
                        continue

                elif f["action"] == "M":
                    diff = _capture_stdout([
                        self._svn_exe, "diff",
                        "-r%d:%d" % (changenum-1, changenum),
                        "%s%s@%s" % (self.base_dir_info["Repository Root"],
                            f["svnpath"], changenum)
                    ], cwd=self.base_dir)
                    if "Index:" not in diff:
                        # Guessing this is just a property change on the file.
                        # We don't handle properies yet, so skip it. Trying
                        # to use this patch content will break the
                        # integration when applying the patch.
                        log.warn("skipping property-only diff on `%s'",
                            f["svnpath"])
                        continue
                    # Fix up index marker.
                    diff = diff.replace("\r\n", "\n")
                    diff = diff.replace("Index: %s" % basename(f["rel_path"]),
                        "Index: %s" % f["rel_path"])
                    diff = diff.replace("\n--- %s" % basename(f["rel_path"]),
                        "\n--- %s" % f["rel_path"])
                    diff = diff.replace("\n+++ %s" % basename(f["rel_path"]),
                        "\n+++ %s" % f["rel_path"])
                    diff = diff.replace("\r\n", "\n")

                elif f["action"] == "A" and "copyfrom-svnpath" in f:
                    # Sometimes an add (action == "A") has a patch too, e.g.
                    # modifications after an "svn mv" or "svn cp".
                    # If it is an 'svn mv' it is quite a PITA (AFAICT) to get
                    # the patch from svn.
                    repo_root = self.base_dir_info["Repository Root"]
                    diff = _capture_stdout([
                        self._svn_exe, "diff",
                        "%s%s@%s" % (repo_root, f["copyfrom-svnpath"], f["copyfrom-rev"]),
                        "%s%s@%s" % (repo_root, f["svnpath"], change["revision"]) ])
                    # The index in the diff header is for the *old* file (and
                    # just the basename). To be able to apply the patch later
                    # we need to update that header. We also need one in
                    # terms of the old file for the dry-run patching.
                    #XXX eol = "\r\n" in diff and "\r\n" or "\n"
                    eol = "\n" #XXX
                    diff_lines = diff.splitlines(0)
                    if diff_lines[4:]:
                        copyfrom_diff_lines = [
                            "Index: %s" % f["copyfrom-relpath"],
                            "===================================================================",
                            "--- %s" % f["copyfrom-relpath"],
                            "+++ %s" % f["copyfrom-relpath"],
                            ] + diff_lines[4:]
                        copyfrom_patch_path = join(tmp_dir, "%d.patch" % diff_idx)
                        diff_idx += 1
                        fout = open(copyfrom_patch_path, 'w')
                        fout.write(eol.join(copyfrom_diff_lines) + eol)
                        fout.close()
                        f["copyfrom_patch_path"] = copyfrom_patch_path
                    if diff_lines[4:]:
                        new_diff_lines = [
                            "Index: %s" % f["rel_path"],
                            "===================================================================",
                            "--- %s" % f["rel_path"],
                            "+++ %s" % f["rel_path"],
                            ] + diff_lines[4:]
                        diff = eol.join(new_diff_lines) + eol

                patch_path = join(tmp_dir, "%d.patch" % diff_idx)
                diff_idx += 1
                fout = open(patch_path, 'w')
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
                    dryrun_patch_path = f.get("copyfrom_patch_path") or f["patch_path"]

                    # Awful HACK around the "$Id: kointegrate.py 3754 2009-06-15 19:57:11Z trentm $" (et al) keyword expansion
                    # problem: If "$Id: kointegrate.py 3754 2009-06-15 19:57:11Z trentm $" is in the patch content but it is
                    # exanded in target file, then `patch` won't be able to
                    # apply.
                    #TODO: Better soln is to modify the *patch*, but that's harder.
                    fin = open(dryrun_patch_path, 'rb')
                    try:
                        patchContent = fin.read()
                    finally:
                        fin.close()
                    if "$Id: kointegrate.py 3754 2009-06-15 19:57:11Z trentm $" in patchContent:
                        dst_path = join(dst_branch.base_dir, f["rel_path"])
                        origDstContent = open(dst_path, 'rb').read()
                        newDstContent = re.sub(r"\$Id: [^$]+\$", "$Id: kointegrate.py 3754 2009-06-15 19:57:11Z trentm $", origDstContent)
                        if newDstContent != origDstContent:
                            open(dst_path, 'wb').write(newDstContent)

                    try:
                        _assertCanApplyPatch(patch_exe, dryrun_patch_path,
                                             dst_branch.base_dir)
                    except Error, ex:
                        if force:
                            log.warn(str(ex))
                        else:
                            patching_failures.append((str(ex), f))
            if patching_failures:
                raise Error("During a dry-run patching attempt there were "
                            "the following failures:\n--\n%s\n\n"
                            "You could use the `-x SUBPATH` option to skip "
                            "a particular file."
                            % ("\n--\n".join("file: %s\n%s" % (f["rel_path"], ex)
                                             for ex,f in patching_failures)))
    
            changes_made = []
            for dst_branch in dst_branches:
                log.info("--- making changes to '%s' branch ---", dst_branch.name)
                
                adds = [f for f in change["files"] if f["action"] in "A"]
                deletes = [f for f in change["files"] if f["action"] in "D"]
                others = [f for f in change["files"] if f["action"] not in "MAD"]
                if others:
                    raise Error("don't know how to handle integrating "
                                "'%s' action" % action)
                
                # - HACK:'svn up' the *whole* tree in attempt to
                #   avoid the inscrutable 'svn ci' error about the dir
                #   being out of date (and tree conflicts).
                #   TODO: see if can get away with (a) only doing this for
                #   certain types of changes (added dirs?) and (b) only
                #   running 'svn up' are part of the working tree.
                self._svn_up(dst_branch.base_dir)
                
                # - do deletes and adds (and copies and moves)
                for f in sorted(adds, key=itemgetter("rel_path")):
                    rel_path = f["rel_path"]
                    src_path = join(self.base_dir, rel_path)
                    if "copyfrom-svnpath" in f:
                        # Figure out if this is an 'svn cp' or an 'svn mv'.
                        for i, df in enumerate(deletes):
                            if df["svnpath"] == f["copyfrom-svnpath"]:
                                # It is a 'svn mv'.
                                df = deletes.pop(i)
                                break
                        else:
                            # It is a 'svn cp'
                            df = None
                        
                        if df is None: # 'svn cp'
                            dst_branch.copy(f["copyfrom-relpath"], rel_path,
                                isdir=(f["kind"] == "directory"))
                            changes_made.append("cp `%s' `%s' (%s)" % (
                                f["copyfrom-relpath"], rel_path, dst_branch.name))
                        else: # 'svn mv'
                            dst_branch.move(f["copyfrom-relpath"], rel_path)
                            changes_made.append("mv `%s' `%s' (%s)" % (
                                f["copyfrom-relpath"], rel_path, dst_branch.name))
                    else:
                        # Just a regular 'svn add'.
                        if f["kind"] == "directory":
                            dst_branch.add(rel_path, isdir=True)
                            changes_made.append("mkdir `%s' (%s)" % (
                                rel_path, dst_branch.name))
                        else:
                            contents = self._svn_cat("%s%s@%s" % (
                                self.base_dir_info["Repository Root"],
                                f["svnpath"], changenum))
                            dst_path = join(dst_branch.base_dir, rel_path)
                            fout = open(dst_path, 'wb')
                            fout.write(contents)
                            fout.close()
                            assert exists(dst_path), \
                                "`%s' couldn't be retrieved from svn" % dst_path
                            dst_branch.add(rel_path)
                            changes_made.append("add `%s' (%s)" % (
                                rel_path, dst_branch.name))
                for f in deletes:
                    rel_path = f["rel_path"]
                    dst_branch.delete(rel_path)
                    changes_made.append("delete `%s' (%s)" % (
                        rel_path, dst_branch.name))

                # - apply the edits
                for f in change["files"]:
                    if "patch_path" in f:
                        patch_path = f["patch_path"]
                        dst_path = join(dst_branch.base_dir, f["rel_path"])
                        dst_branch.edit(dst_path)
                        eol_before = eollib.eol_info_from_path(dst_path)[0]
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
                        eol_after = eollib.eol_info_from_path(dst_path)[0]
                        if eol_after != eol_before:
                            assert eol_before != None
                            log.info("restore EOLs for `%s' (damaged by patch)",
                                     dst_path)
                            eollib.convert_path_eol(dst_path, eol_before)
                        if applied:
                            changes_made.append("patched `%s' (%s)" % (
                                f["rel_path"], dst_branch.name))
                    elif f["action"] == "M" and f["is_binary"]:
                        # This is a binary file to copy over.
                        contents = self._svn_cat("%s%s@%s" % (
                            self.base_dir_info["Repository Root"],
                            f["svnpath"], changenum))
                        dst_path = join(dst_branch.base_dir, f["rel_path"])
                        dst_branch.edit(dst_path)
                        fout = open(dst_path, 'wb')
                        fout.write(contents)
                        fout.close()
                        assert exists(dst_path), \
                            "`%s' couldn't be retrieved from svn" % dst_path
                        changes_made.append("copied `%s' (%s)" % (
                            f["rel_path"], dst_branch.name))

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
            if log.isEnabledFor(logging.INFO):
                log.info("\n\n-- Check-in summary (for bugzilla comment):")
                for s in commit_summaries:
                    log.info(s)
                log.info("--\n")
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
        msg = "%s\n\n(integrated from %s change %d by %s)" % (
              desc.rstrip(), src_branch.desc, changenum, user)
        log.info("\n\nReady to commit to '%s' branch:", self.name)
        log.info(_banner("commit message", '-'))
        log.info(msg)
        log.info(_banner(None, '-'))

        auto_commit = True
        if interactive:
            answer = _query_yes_no(
                "\nWould you like this script to automatically commit\n"
                "this integration to the '%s' branch?" % self.name,
                default=None)
            if answer != "yes":
                auto_commit = False
        
        if auto_commit:
            argv = [self._svn_exe, "commit"]
            if not log.isEnabledFor(logging.INFO):
                argv += ["-q"]
            argv += ["-m", msg] + rel_paths
            stdout, stderr, retval = _patchRun(argv, self.base_dir)
            sys.stdout.write(stdout)
            if stderr or retval:
                raise Error("error commiting: %s\n%s"
                            % (retval, _indent(stderr)))
            if log.isEnabledFor(logging.INFO):
                revision_re = re.compile(r'Committed revision (\d+)\.')
                try:
                    revision = revision_re.search(stdout).group(1)
                except AttributeError:
                    log.warn("Couldn't determine commited revision from "
                             "'svn commit' output: %r", stdout)
                    revision = "???"
            else:
                revision = None
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

def kointegrate_all_changes(dst_branch_names, interactive=True,
        exclude_outside_paths=False, excludes=None,
        force=False):
    """Call `kointegrate' for every change in the source branch."""
    src_branch = _get_curr_branch()
    for changenum in sorted(src_branch.changenums()):
        kointegrate(changenum, dst_branch_names, interactive,
            exclude_outside_paths, excludes, force)

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

    src_branch = _get_curr_branch()

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

    # HACK normalize EOLs in targets.
    # Assumptions: have "Index:" markers in the patch.
    normedPaths = []
    native_eol = (sys.platform == "win32" and "\r\n" or "\n")
    other_eol = (sys.platform == "win32" and "\n" or "\r\n")
    patchContent = patchContent.replace(other_eol, native_eol)
    for line in patchContent.splitlines(False):
        if not line.startswith("Index:"):
            continue
        index, relpath = line.split(None, 1)
        path = join(sourceDir, relpath)
        content = open(path, 'rb').read()
        if other_eol not in content:
            continue
        content = content.replace(other_eol, native_eol)
        open(path, 'wb').write(content)
        normedPaths.append(path)
    
    try:
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
            headOfPatch = '\n    '.join(patchContent.splitlines(False)[:4])
            errmsg = textwrap.dedent("""\
                patch '%s' will not apply cleanly%s:
                  patch source:  %s
                  argv:          %s
                  stdin:         %s
                  cwd:           %s
                  head of patch:
                    %s
                """) % (patchFile, inReverse, patchSrcFile or patchFile,
                        argv, patchFile, sourceDir, headOfPatch)
            if stdout.strip():
                errmsg += "  stdout:\n%s" % _indent(stdout)
            if stderr.strip():
                errmsg += "  stderr:\n%s" % _indent(stderr)
            raise Error(errmsg)
    finally:
        # HACK continued... unnormalize EOLs.
        #for path in normedPaths:
        #    content = open(path, 'rb').read()
        #    content = content.replace(native_eol, other_eol)
        #    open(path, 'wb').write(content)
        pass

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
    if not log.isEnabledFor(logging.INFO):
        baseArgv += ["--quiet"]
    patchFile = os.path.join(baseDir, patchRelPath)
    patchContent = open(patchFile, 'r').read()

    # HACK normalize EOLs in targets.
    # Assumptions: have "Index:" markers in the patch.
    normedPaths = []
    native_eol = (sys.platform == "win32" and "\r\n" or "\n")
    other_eol = (sys.platform == "win32" and "\n" or "\r\n")
    for line in patchContent.splitlines(False):
        if not line.startswith("Index:"):
            continue
        index, relpath = line.split(None, 1)
        path = join(sourceDir, relpath)
        content = open(path, 'rb').read()
        if other_eol not in content:
            continue
        content = content.replace(other_eol, native_eol)
        open(path, 'wb').write(content)
        normedPaths.append(path)
    
    try:
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
    finally:
        # HACK continued... unnormalize EOLs.
        #for path in normedPaths:
        #    content = open(path, 'rb').read()
        #    content = content.replace(native_eol, other_eol)
        #    open(path, 'wb').write(content)
        pass


# Recipe: banner (1.0.1)
def _banner(text, ch='=', length=78):
    """Return a banner line centering the given text.

        "text" is the text to show in the banner. None can be given to have
            no text.
        "ch" (optional, default '=') is the banner line character (can
            also be a short string to repeat).
        "length" (optional, default 78) is the length of banner to make.

    Examples:
        >>> _banner("Peggy Sue")
        '================================= Peggy Sue =================================='
        >>> _banner("Peggy Sue", ch='-', length=50)
        '------------------- Peggy Sue --------------------'
        >>> _banner("Pretty pretty pretty pretty Peggy Sue", length=40)
        'Pretty pretty pretty pretty Peggy Sue'
    """
    if text is None:
        return ch * length
    elif len(text) + 2 + len(ch)*2 > length:
        # Not enough space for even one line char (plus space) around text.
        return text
    else:
        remain = length - (len(text) + 2)
        prefix_len = remain / 2
        suffix_len = remain - prefix_len
        if len(ch) == 1:
            prefix = ch * prefix_len
            suffix = ch * suffix_len
        else:
            prefix = ch * (prefix_len/len(ch)) + ch[:prefix_len%len(ch)]
            suffix = ch * (suffix_len/len(ch)) + ch[:suffix_len%len(ch)]
        return prefix + ' ' + text + ' ' + suffix

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

def _get_last_changenum():
    curr_branch = _get_curr_branch()
    return curr_branch.last_rev(curr_user=True)

def _get_curr_branch():
    curr_branch = None
    norm_cwd_plus_sep = normcase(os.getcwd()) + os.sep
    for branch in cfg.branches.values():
        norm_branch_dir_plus_sep = normcase(branch.base_dir) + os.sep
        if norm_cwd_plus_sep.startswith(norm_branch_dir_plus_sep):
            curr_branch = branch
            break
    else:
        raise Error(textwrap.dedent("""\
            The current directory is not in any of your configured Komodo
            branches. You must either update your configuration for this
            script (see `kointegrate --help') or change to an active
            branch working copy directory.
            """))
    return curr_branch


#---- mainline

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
        $name: level: ...
    Spacing. Lower case. Drop the prefix for INFO-level. 
    """
    hdlr = logging.StreamHandler(stream)
    defaultFmt = "%(name)s: %(levelname)s: %(message)s"
    infoFmt = "%(message)s"
    fmtr = _PerLevelFormatter(fmt=defaultFmt,
                              fmtFromLevel={logging.INFO: infoFmt})
    hdlr.setFormatter(fmtr)
    logging.root.addHandler(hdlr)
    log.setLevel(logging.INFO)




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
    parser.add_option("-q", "--quiet", dest="log_level",
                      action="store_const", const=logging.WARN,
                      help="more verbose output")
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
        rev_str = args[0]
        if rev_str.startswith('r'):
            rev_str = rev_str[1:]
        if rev_str in ("LAST", "HEAD"):
            changenum = _get_last_changenum()
        elif rev_str == "ALL":
            changenum = "ALL"
        else:
            changenum = int(rev_str)
    except ValueError, ex:
        log.error("<changenum> must be an integer: %r", args[0])
        log.error("(See 'kointegrate --help'.)")
        return 1
    dst_branch_names = args[1:]

    if changenum == "ALL":
        kointegrate_all_changes(
            dst_branch_names, interactive=opts.interactive,
            exclude_outside_paths=opts.exclude_outside_paths,
            excludes=opts.excludes, force=opts.force)
        return 0
    else:
        integrated = kointegrate(
            changenum, dst_branch_names, interactive=opts.interactive,
            exclude_outside_paths=opts.exclude_outside_paths,
            excludes=opts.excludes, force=opts.force)
        if integrated:
            return 0
        else:
            return 1

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



