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

"""mozupdate -- a tool for working with Mozilla update system packages

"Mozilla update packages" are the packages used by Firefox and other Mozilla
tools for app updates. Mozilla has some scripts in
    http://lxr.mozilla.org/mozilla/source/tools/update-packaging/
This is an improved version of those.

Dev Notes:
- The placement of 'removed-files' in Contents/MacOS/ on Mac OS X doesn't
  really fly, because it doesn't allow removing files in other paths.
  On Mac OS X it should be 'Contents/removed-files'. This script supports
  'removed-files' being anywhere (first one found wins).

TODO:
- propose this for https://bugzilla.mozilla.org/show_bug.cgi?id=375752
  (need to publish cmdln.py first) and ditch the Komodo-specific bits
"""

import os
from os.path import exists, isdir, isfile, abspath, basename, splitext, \
                    dirname, normpath, expanduser, join, islink
import sys
import re
from pprint import pprint
from glob import glob
import traceback
import stat
import logging
import posixpath
import tempfile
import shutil
import bz2
from optparse import OptionParser

import which
import cmdln



#---- exceptions

class Error(Exception):
    pass



#---- global data

__version__ = (0, 1, 0)
log = logging.getLogger("mozupdate")
#log.setLevel(logging.DEBUG)

g_update_manifest_filename = "updatev3.manifest"


def isValidPathEncoding(path):
    # Check that it's decode-able, otherwise we've got a
    # strange file.
    try:
        path.decode("utf8")
    except UnicodeDecodeError:
        log.error("Invalid path: %r", path)
        return False
    return True


#---- command-line interface

class Shell(cmdln.Cmdln):
    """mozupdate -- tool for working with Mozilla update packages

    Usage:
        mozupdate [<options>...] <command> [<args>...]
        mozupdate help <command>       # help on a specific command

    ${option_list}
    ${command_list}
    ${help_list}
    
    A Mozilla update package is a special '.mar' file used by the Mozilla
    update system.
    """
    name = 'mozupdate'

    @property
    def version(self):
        return '.'.join(map(str, __version__))

    def get_optparser(self):
        p = cmdln.Cmdln.get_optparser(self)
        p.add_option("-v", "--verbose", dest="log_level",
                     action="store_const", const=logging.DEBUG,
                     help="more verbose output")
        p.add_option("-q", "--quiet", dest="log_level",
                     action="store_const", const=logging.WARNING,
                     help="quieter output")
        p.set_defaults(log_level=logging.INFO)
        return p

    def postoptparse(self):
        log.setLevel(self.options.log_level)

    def do_list(self, subcmd, opts, mar_path):
        """${cmd_name}: List the contents of a mozilla update package

        ${cmd_usage}
        ${cmd_option_list}
        """
        mar = _get_mar()
        _run('%s -t "%s"' % (mar, mar_path))

    @cmdln.option("-d", dest="dir", default=os.curdir,
                  help="directory into which to unpack (default is cwd)")
    def do_unpack(self, subcmd, opts, mar_path):
        """${cmd_name}: Unpack a mozilla update package in the current dir.

        ${cmd_usage}
        ${cmd_option_list}
        Should be equivalent to 'unwrap_full_update.pl'
        <http://tinyurl.com/2ehfus>.
        """
        mar = _get_mar()
        
        manifest = []
        output = _capture_output('%s -t "%s"' % (mar, mar_path))
        for i, line in enumerate(output.splitlines(0)):
            if i == 0: continue  # skip first line (it is a header)
            path = normpath(line.split('\t')[-1])
            manifest.append(path)
        
        if not exists(opts.dir):
            os.makedirs(opts.dir)

        try:
            _run_in_dir('%s -x "%s"' % (mar, abspath(mar_path)), opts.dir)
        except OSError, ex:
            # A -1 from mar.exe can indicate a path that is too long
            # (the _open() call used internally on Windows seems to fail
            # with ENOENT if the file path is >= ~256 characters).
            if sys.platform == "win32" and ex.errno == -1:
                log.warn("A -1 from 'mar' on Windows sometimes indicates "
                         "a path that too long (>=256 chars for the "
                         "_open() call used). Using a shorter dir to "
                         "which to unpack might help.")
            raise

        for path in manifest:
            dst_path = normpath(join(opts.dir, path))
            log.info("uncompress `%s'", dst_path)
            bzip_uncompress_file(dst_path, dst_path)

    _is_extension_path_re = re.compile("((.*/)?extensions)/.*?/")

    def _manifest_add(self, manifest, pkg_path):
        """Add a 'add' or 'add-if' item to the update manifest."""
        is_extension = self._is_extension_path_re.search(pkg_path)
        if is_extension:
            manifest.append('add-if "%s" "%s"'
                            % (is_extension.group(1), pkg_path))
        else:
            manifest.append('add "%s"' % pkg_path)

    def _manifest_patch(self, manifest, patch_pkg_path, pkg_path):
        """Add a 'patch' or 'patch-if' item to the update manifest."""
        is_extension = self._is_extension_path_re.search(pkg_path)
        if is_extension:
            manifest.append('patch-if "%s" "%s" "%s"'
                            % (is_extension.group(1), patch_pkg_path,
                               pkg_path))
        else:
            manifest.append('patch "%s" "%s"' % (patch_pkg_path, pkg_path))

    @cmdln.option("--manifest-extra",
                  help="path to file containing extra lines to append "
                       "to update manifest")
    @cmdln.option("--force", action="store_true", default=False,
                  help="force overwriting existing MAR_PATH and/or temp "
                       "working dir")
    @cmdln.option("--no-cleanup", action="store_true", default=False,
                  help="do not remove temp working dir (for debugging)")
    @cmdln.option("--removed-files-candidates", action="store",
                  help="Specify a path to the list of files that might have "
                       "been removed")
    @cmdln.alias("full")
    def do_complete(self, subcmd, opts, mar_path, dir):
        """${cmd_name}: create a complete Mozilla update package

        ${cmd_usage}
        ${cmd_option_list}
        Should be equivalent to 'make_full_update.sh'
        <http://tinyurl.com/2uao9v>, including the exclusion of
        channel-prefs.js (see mozilla bug 306077).
        """
        mar = _get_mar()

        # Validate args.
        if not exists(dir):
            raise Error("`%s' does not exist" % dir)
        elif not isdir(dir):
            raise Error("`%s' is not a directory" % dir)
        if exists(mar_path):
            if opts.force:
                log.debug("rm `%s'", mar_path)
                os.remove(mar_path)
            else:
                raise Error("`%s' exists (use --force to allow overwrite)"
                            % mar_path)

        # Get a working directory.
        wrk_dir = tempfile.mkdtemp()
        img_dir = join(wrk_dir, "image")
        log.debug("mkdir `%s'", img_dir)
        os.makedirs(img_dir)
        
        try:
            manifest = []  # update manifest instructions
            paths_to_mar = []
            seen_files = set()
            for dname, dirnames, filenames in os.walk(dir):
                for f in filenames:
                    src_path = join(dname, f)
                    dst_path = img_dir + src_path[len(dir):]
                    pkg_path = src_path[len(dir)+1:]
                    if sys.platform == "win32":
                        pkg_path = pkg_path.replace('\\', '/')

                    seen_files.add(pkg_path)

                    if f in ("channel-prefs.js", g_update_manifest_filename):
                        log.info("skipping `%s'", pkg_path)
                        continue
                    if islink(src_path):
                        log.warn("skipping symlink `%s' (symlinks aren't "
                                 "supported by mar)", pkg_path)
                        continue

                    log.info("archive `%s'", pkg_path)
                    if not exists(dirname(dst_path)):
                        os.makedirs(dirname(dst_path))
                    bzip_compress_file(src_path, dst_path)
                    _assert_mode_equal(src_path, dst_path)
                    paths_to_mar.append(pkg_path)
                    self._manifest_add(manifest, pkg_path)

            self._manifest_handle_removed_files(manifest, dir, seen_files)
            self._manifest_handle_extra(manifest, opts.manifest_extra)

            if opts.removed_files_candidates:
                removed_files = set()
                for line in open(opts.removed_files_candidates, "r"):
                    if not isValidPathEncoding(line):
                        continue
                    removed_files.add(line.strip())

                actually_removed_files = sorted(removed_files - seen_files)
                if actually_removed_files:
                    # Write 'removed-files'.
                    # This will be used by Komodo for the next update to determine
                    # what files we fill need to delete in the future (things that
                    # we used to ship, but don't any more).  This is only relevant
                    # for complete updates: We might ship a file in Komodo 8.0.0,
                    # delete it for 8.0.1, and then have a complete update for 8.0.2
                    # which also needs to know to delete it.
                    removed_path = join(img_dir, "removed-files")
                    log.info("write `removed-files`")
                    paths_to_mar.append("removed-files")
                    manifest_str = '\n'.join(actually_removed_files) + '\n'
                    open(removed_path, 'wb').write(bz2.compress(manifest_str))
                    for path in actually_removed_files:
                        # Add remove instructions, but only if they aren't there
                        if not isValidPathEncoding(path):
                            continue
                        instruction = 'remove "%s"' % (path,)
                        if instruction not in manifest:
                            manifest.append(instruction)

            # Write 'update manifest'.
            #
            # 'updater.exe' parses this (see ::Parse() methods in
            # "toolkit\mozapps\update\src\updater\updater.cpp"). It can be
            # picky:
            # - The file must end with a newline.
            # - It *might* require '\n' EOLs (i.e. not '\r\n' EOLs) but I
            #   don't know this for sure.
            manifest_path = join(img_dir, g_update_manifest_filename)
            log.info("write %r", g_update_manifest_filename)
            paths_to_mar.append(g_update_manifest_filename)
            manifest_str = '\n'.join(manifest) + '\n'
            open(manifest_path, 'wb').write(bz2.compress(manifest_str))

            log.info("create `%s'", mar_path)
            file_list_path = join(wrk_dir, "files")
            fout = open(file_list_path, 'w')
            fout.write('\n'.join(paths_to_mar))
            fout.close()
            _run_in_dir('%s -c "%s" - < %s'
                        % (mar, abspath(mar_path), abspath(file_list_path)),
                        img_dir)
        finally:
            if not opts.no_cleanup:
                log.debug("rm `%s'", wrk_dir)
                _rmtree(wrk_dir)


    @cmdln.option("--manifest-extra",
                  help="path to file containing extra lines to append "
                       "to update manifest")
    @cmdln.option("-c", "--clobber", action="append", default=[],
                  metavar="PATH",
                  help="Force including the full file (instead of a binary "
                       "diff) of the given files. Use this option more "
                       "than once for multiple such files. The argument "
                       "must (a) use Unix dir separators and (b) be a path "
                       "*relative to the package base dir*.")
    @cmdln.option("-x", "--exclude", dest="exclude_patterns",
                  metavar="REGEX", action="append", default=[],
                  help="Specify a path to exclude from the "
                       "partial update. Can be given more than once to "
                       "specify multiple patterns. The *regex* pattern "
                       "is matched against the relative path that "
                       "appears in 'update manifest'. Note: "
                       "'update manifest' and 'channel-prefs.js' are "
                       "always skipped.")
    @cmdln.option("--force", action="store_true", default=False,
                  help="force overwriting existing MAR_PATH and/or temp "
                       "working dir")
    @cmdln.option("--no-cleanup", action="store_true", default=False,
                  help="do not remove temp working dir (for debugging)")
    @cmdln.option("--removed-files-candidates", action="store",
                  help="Specify a path to the list of files that might have "
                       "been removed; this list will be updated with new files")
    @cmdln.alias("incremental")
    def do_partial(self, subcmd, opts, mar_path, fromdir, todir):
        """${cmd_name}: create an incremental Mozilla update package

        ${cmd_usage}
        ${cmd_option_list}
        Create a Mozilla update package, MAR_PATH, that contains the
        differences between FROMDIR and TODIR.

        Should be equivalent to 'make_incremental_update.sh'
        <http://tinyurl.com/yqc5uw>. Files named "channel-prefs.js" are
        excluded (see mozilla bug 306077).

        TODO: add 'searchplugin' hacks for 'patch-if' (in _manifest_patch()).
        """
        mar = _get_mar()
        mbsdiff = _get_mbsdiff()
        exclude_regexes = [re.compile(p) for p in opts.exclude_patterns]

        # Validate args.
        if not exists(fromdir):
            raise Error("`%s' does not exist" % fromdir)
        elif not isdir(fromdir):
            raise Error("`%s' is not a directory" % fromdir)
        if not exists(todir):
            raise Error("`%s' does not exist" % todir)
        elif not isdir(todir):
            raise Error("`%s' is not a directory" % todir)
        if exists(mar_path):
            if opts.force:
                log.debug("rm `%s'", mar_path)
                os.remove(mar_path)
            else:
                raise Error("`%s' exists (use --force to allow overwrite)"
                            % mar_path)

        # Get a working directory.
        wrk_dir = tempfile.mkdtemp()
        img_dir = join(wrk_dir, "image")
        log.debug("mkdir `%s'", img_dir)
        os.makedirs(img_dir)
        removed_files = set() # using forward slashes, e.g. "lib/mozilla/ko.exe"

        try:
            manifest = []  # update manifest instructions
            paths_to_mar = []

            try:
                # read the previous removed-files and add it to our set
                # (to cover files that were previously removed)
                with open(join(fromdir, "removed-files")) as old_list:
                    for line in old_list:
                        if not isValidPathEncoding(line):
                            continue
                        removed_files.add(line.strip())
            except IOError:
                log.warn("removed-files list not found from previous update")

            # Walk the "fromdir" to find updated and removed files.
            from_pkg_paths = set()
            for dname, dirnames, filenames in os.walk(fromdir):
                for f in filenames:
                    from_path = join(dname, f)
                    to_path = todir + from_path[len(fromdir):]
                    img_path = img_dir + from_path[len(fromdir):]
                    pkg_path = from_path[len(fromdir)+1:]
                    if sys.platform == "win32":
                        pkg_path = pkg_path.replace('\\', '/')
                    from_pkg_paths.add(pkg_path)
                    
                    if f in ("channel-prefs.js", g_update_manifest_filename):
                        log.info("skipping `%s' (hardcoded)", pkg_path)
                        continue
                    matching_regexs = [r for r in exclude_regexes
                                       if r.search(pkg_path)]
                    if matching_regexs:
                        log.info("skipping `%s' (matches /%s/)", pkg_path,
                                 "/, /".join([r.pattern for r in matching_regexs]))
                        continue

                    if not exists(to_path):
                        log.info("`%s' was removed", pkg_path)
                        manifest.append('remove "%s"' % pkg_path)
                        removed_files.add(pkg_path)
                        continue
                    if not _is_different(from_path, to_path):
                        log.debug("`%s' is unchanged", pkg_path)
                        continue
                    if islink(from_path):
                        log.warn("skipping symlink `%s' (symlinks aren't "
                                 "supported by mar)", pkg_path)
                        continue

                    # Use the smaller of the compressed binary diff and the
                    # compressed new file. (Use of the new file over the
                    # patch can be forced with "-c <pkg_path>".)
                    if not exists(dirname(img_path)):
                        os.makedirs(dirname(img_path))
                    bzip_compress_file(to_path, img_path)

                    if pkg_path in opts.clobber:
                        log.info("`%s' was updated (including full "
                                 "replacement, forced)", pkg_path)
                        paths_to_mar.append(pkg_path)
                        self._manifest_add(manifest, pkg_path)
                        continue

                    patch_filepath = '%s.patch' % (img_path, )
                    _run('%s "%s" "%s" "%s"'
                         % (mbsdiff, from_path, to_path, patch_filepath))
                    diff_content = open(patch_filepath, "rb").read()
                    open(patch_filepath, "wb").write(bz2.compress(diff_content))
                    
                    patch_file_size = os.stat(img_path+".patch").st_size
                    full_file_size = os.stat(img_path).st_size
                    if patch_file_size < full_file_size:
                        size_reduction = ((full_file_size - patch_file_size)
                                          * 100 / full_file_size)
                        log.info("`%s' was updated (including binary "
                                 "patch -- %d%% reduction)",
                                 pkg_path, int(size_reduction))
                        paths_to_mar.append(pkg_path+".patch")
                        self._manifest_patch(manifest, pkg_path+".patch",
                                             pkg_path)
                        os.remove(img_path)
                    else:
                        log.info("`%s' was updated (including full "
                                 "replacement)", pkg_path)
                        paths_to_mar.append(pkg_path)
                        self._manifest_add(manifest, pkg_path)
                        os.remove(img_path+".patch")

            seen_files = set()

            # Walk the "todir" to find newly added files.
            for dname, dirnames, filenames in os.walk(todir):
                for f in filenames:
                    to_path = join(dname, f)
                    from_path = todir + to_path[len(todir):]
                    img_path = img_dir + to_path[len(todir):]
                    pkg_path = to_path[len(todir)+1:]
                    if sys.platform == "win32":
                        pkg_path = pkg_path.replace('\\', '/')

                    seen_files.add(pkg_path)

                    if pkg_path in from_pkg_paths:
                        continue

                    if f in ("channel-prefs.js", g_update_manifest_filename):
                        log.info("skipping `%s' (hardcoded)", pkg_path)
                        continue
                    matching_regexs = [r for r in exclude_regexes
                                       if r.search(pkg_path)]
                    if matching_regexs:
                        log.info("skipping `%s' (matches /%s/)", pkg_path,
                                 "/, /".join([r.pattern for r in matching_regexs]))
                        continue

                    if islink(to_path):
                        log.warn("skipping symlink `%s' (symlinks aren't "
                                 "supported by mar)", pkg_path)
                        continue

                    if not exists(dirname(img_path)):
                        os.makedirs(dirname(img_path))
                    bzip_compress_file(to_path, img_path)
                    log.info("`%s' was added", pkg_path)
                    paths_to_mar.append(pkg_path)
                    self._manifest_add(manifest, pkg_path)

            if opts.removed_files_candidates:
                # Read in the list of files that might have been removed
                try:
                    with open(opts.removed_files_candidates, "r") as old_list:
                        for path in old_list:
                            if not isValidPathEncoding(path):
                                continue
                            removed_files.add(path.strip())
                except IOError:
                    log.warn("removed files candidates list %s is missing",
                             opts.removed_files_candidates)

            removed_files.update(self._manifest_handle_removed_files(manifest, todir, seen_files))
            self._manifest_handle_extra(manifest, opts.manifest_extra)

            actually_removed_files = sorted(removed_files - seen_files)
            if actually_removed_files:
                # Write 'removed-files'.
                # This will be used by Komodo for the next update to determine
                # what files we fill need to delete in the future (things that
                # we used to ship, but don't any more).  This is only relevant
                # for complete updates: We might ship a file in Komodo 8.0.0,
                # delete it for 8.0.1, and then have a complete update for 8.0.2
                # which also needs to know to delete it.
                removed_path = join(img_dir, "removed-files")
                log.info("write `removed-files`")
                paths_to_mar.append("removed-files")
                manifest_str = '\n'.join(actually_removed_files) + '\n'
                open(removed_path, 'wb').write(bz2.compress(manifest_str))
                for path in actually_removed_files:
                    # Add remove instructions, but only if they aren't there
                    instruction = 'remove "%s"' % (path,)
                    if instruction not in manifest:
                        manifest.append(instruction)

            if opts.removed_files_candidates:
                # also update the candidates list
                with open(opts.removed_files_candidates, "w") as new_list:
                    for path in sorted(removed_files):
                        if not isValidPathEncoding(path):
                            continue
                        new_list.write(path + "\n")

            # Write 'update manifest'.
            #
            # 'updater.exe' parses this (see ::Parse() methods in
            # "toolkit\mozapps\update\src\updater\updater.cpp"). It can be
            # picky:
            # - The file must end with a newline.
            # - It *might* require '\n' EOLs (i.e. not '\r\n' EOLs) but I
            #   don't know this for sure.
            manifest_path = join(img_dir, g_update_manifest_filename)
            log.info("write %r", g_update_manifest_filename)
            paths_to_mar.append(g_update_manifest_filename)
            manifest_str = '\n'.join(manifest) + '\n'
            open(manifest_path, 'wb').write(bz2.compress(manifest_str))

            log.info("create `%s'", mar_path)
            file_list_path = join(wrk_dir, "files")
            fout = open(file_list_path, 'w')
            fout.write('\n'.join(paths_to_mar))
            fout.close()
            _run_in_dir('%s -c "%s" - < %s'
                        % (mar, abspath(mar_path), abspath(file_list_path)),
                        img_dir)

        finally:
            if not opts.no_cleanup:
                log.debug("rm `%s'", wrk_dir)
                _rmtree(wrk_dir)

    def _manifest_handle_extra(self, manifest, extra_path):
        if extra_path is None:
            return
        if not exists(extra_path):
            raise Error("manifest-extra path `%s' does not exist"
                        % extra_path)
        for line in open(extra_path, 'r'):
            manifest.append(line)

    def _manifest_handle_removed_files(self, manifest, srcdir, seen_set):
        """Add 'remove' entries to the manifest as per the
        'removed-files' file (if any) in the srcdir.
        @param manifest {list} The manifest to write
        @param srcdir {basestring} The directory containing the image tree
        @param seen_set {set} Files that are known to exist
        @returns The removed files entries found
        """
        # Find the 'removed-files' to use (first one wins).
        removed_files = set()
        removed_files_path = None
        removed_files_pkg_prefix = None
        for dname, dirnames, filenames in os.walk(srcdir):
            if "removed-files" in filenames:
                removed_files_path = join(dname, "removed-files")
                removed_files_pkg_prefix = dname[len(srcdir)+1:]
                if sys.platform == "win32":
                    removed_files_pkg_prefix \
                        = removed_files_pkg_prefix.replace('\\', '/')
                break
        else:
            # No 'removed-files' path.
            return removed_files
        
        for line in open(removed_files_path, 'r'):
            line = line.strip()
            if not line: continue # skip blank lines
            if not isValidPathEncoding(line):
                continue
            if '\\' in line:
                raise Error("`%s' is using Windows-style path seps: "
                            "I'm not positive, but I suspect the "
                            "updater doesn't support this"
                            % removed_files_path)
            if line.endswith('/'):
                # Skip dirs. The updater doesn't yet know how to
                # remove entire directories.
                log.info("ignoring remove instruction for dir `%s'", line)
                continue
            path = posixpath.join(removed_files_pkg_prefix, line)
            if path not in seen_set:
                manifest.append('remove "%s"' % path)
                removed_files.add(path)

        return removed_files


    def _do_mar(self, argv):
        mar = _get_mar()
        args = [mar]
        for arg in argv[1:]:
            if ' ' in arg:
                args.append('"%s"' % arg)
            else:
                args.append(arg)
        cmd = ' '.join(args)
        return os.system(cmd)


#---- internal support functions

def bzip_compress_file(src_path, dst_path):
    """Compress the source file using bzip2 and write to the destination."""
    st_mode = os.stat(src_path).st_mode
    data = open(src_path, "rb").read()
    open(dst_path, "wb").write(bz2.compress(data))
    os.chmod(dst_path, st_mode)

def bzip_uncompress_file(src_path, dst_path):
    """Uncompress the source file using bunzip2 and write to the destination."""
    st_mode = os.stat(src_path).st_mode
    data = open(src_path, "rb").read()
    # If the destination file already exists, remove it first.
    if exists(dst_path):
        os.remove(dst_path)
    open(dst_path, "wb").write(bz2.decompress(data))
    os.chmod(dst_path, st_mode)

def _od_path_from_path(path, od_opts=["-c"]):
    """Calculate and cache `od $od_opts $path` and return the cached path."""
    from hashlib import md5
    import applib
    import buildutils
    import which
    from os.path import exists
    cache_dir = join(
        applib.user_cache_dir("komodo-dev", "ActiveState"), "od")
    od_dir = join(cache_dir, md5(dirname(path)).hexdigest())
    od_path = join(od_dir, basename(path)+".od")
    if not exists(od_dir):
        os.makedirs(od_dir)
    od = "od"
    if sys.platform == "win32":
        od = r"C:\mozilla-build\msys\bin\od.exe" # HACK for Trent's machine.
    argv = [od] + od_opts + [path]
    stdout = buildutils.capture_stdout(argv)
    fout = open(od_path, 'w')
    fout.write(stdout)
    fout.close()
    return od_path


def _strings_path_from_path(path):
    """Calculate and cache `strings $path` and return the cached path."""
    from hashlib import md5
    import applib
    import buildutils
    from os.path import exists
    cache_dir = join(
        applib.user_cache_dir("komodo-dev", "ActiveState"), "strings")
    strings_dir = join(cache_dir, md5(dirname(path)).hexdigest())
    strings_path = join(strings_dir, basename(path)+".strings")
    if not exists(strings_dir):
        os.makedirs(strings_dir)
    stdout = buildutils.capture_stdout(["strings", path])
    fout = open(strings_path, 'w')
    fout.write(stdout)
    fout.close()
    return strings_path

def _get_mar():
    """Return path to a mar executable."""
    if "MAR" in os.environ:
        return os.environ["MAR"]

    # If this is a komodo dev tree, attempt to use the configured
    # mozilla build's mar.exe.
    build_mar_instructions = ""
    config_path = join(dirname(dirname(abspath(__file__))), "bkconfig.py")
    if exists(config_path):
        try:
            config = _module_from_path(config_path)
        except ImportError, ex:
            pass
        else:
            exe = (sys.platform == "win32" and ".exe" or "")
            mar = join(config.mozObjDir, "dist", "host", "bin", "mar"+exe)
            if exists(mar):
                return mar
            build_mar_instructions = '\n'.join([
                "- build mar in your mozilla build:",
                "    cd %s" % join(config.mozObjDir, "modules", "libmar"),
                "    make"
                ])

    # Use the first one found on the path, if any.
    try:
        return which.which("mar")
    except which.WhichError, ex:
        pass

    raise Error(_dedent("""\
        No 'mar' (Mozilla ARchiver) executable could be found. You can:
        - set a MAR envvar pointing to one
        - put a mar executable directory on your PATH
        %s
        """) % build_mar_instructions)

def _get_mbsdiff():
    """Return path to a mbsdiff executable."""
    if "MBSDIFF" in os.environ:
        return os.environ["MBSDIFF"]

    try:
        return which.which("mbsdiff")
    except which.WhichError, ex:
        pass

    # If this is a Komodo-devel tree, attempt to use the configured
    # Mozilla build's mbsdiff.exe.
    config_path = join(dirname(dirname(abspath(__file__))), "bkconfig.py")
    if exists(config_path):
        try:
            config = _module_from_path(config_path)
        except ImportError, ex:
            pass
        else:
            exe = (sys.platform == "win32" and ".exe" or "")
            mbsdiff = join(config.mozObjDir, "dist", "host", "bin",
                           "mbsdiff"+exe)
            if exists(mbsdiff):
                return mbsdiff

    raise Error(_dedent("""\
        No 'mbsdiff' executable could be found on your PATH.
        Add mbsdiff to your PATH or define a MBSDIFF environment
        variable pointing to one.
        
        'mbsdiff' is the Mozilla-tweaked bsdiff binary-differ. It can be
        built from source in 'mozilla/other-licenses/bsdiff'."""))


def _is_different(a, b):
    """Return true iff the content of the given paths differ.
    
    'make_incremental_update.sh' just uses 'diff' for this. Perhaps that
    would be faster. Adds a dep on Windows, tho.
    """
    fin_a = open(a, 'rb')
    fin_b = open(b, 'rb')
    try:
        CHUNKSIZE = 1024
        while True:
            chunk_a = fin_a.read(CHUNKSIZE)
            chunk_b = fin_b.read(CHUNKSIZE)
            if chunk_a != chunk_b:
                return True
            if len(chunk_a) < CHUNKSIZE:
                break
        return False
    finally:
        fin_a.close()
        fin_b.close()

def _assert_mode_equal(a, b):
    """Assert that the mode of the two given paths are equal."""
    mode_a = stat.S_IMODE(os.stat(a).st_mode)
    mode_b = stat.S_IMODE(os.stat(b).st_mode)
    if mode_a != mode_b:
        raise Error("the permissions on `%s' (%s) and `%s' (%s) differ"
                    % (a, oct(mode_a), b, oct(mode_b)))

# Recipe: module_from_path (1.0.1)
def _module_from_path(path):
    import imp, os
    dir = os.path.dirname(path) or os.curdir
    name = os.path.splitext(os.path.basename(path))[0]
    iinfo = imp.find_module(name, [dir])
    return imp.load_module(name, *iinfo)

# Recipe: rmtree (0.5)
def _rmtree_OnError(rmFunction, filePath, excInfo):
    if excInfo[0] == OSError:
        # presuming because file is read-only
        os.chmod(filePath, 0777)
        rmFunction(filePath)
def _rmtree(dirname):
    import shutil
    shutil.rmtree(dirname, 0, _rmtree_OnError)


def _capture_output(cmd):
    o = os.popen(cmd)
    output = o.read()
    retval = o.close()
    if retval:
        raise Error("error capturing output of `%s': %r" % (cmd, retval))
    return output

# Recipe: dedent (0.1.2)
def _dedentlines(lines, tabsize=8, skip_first_line=False):
    """_dedentlines(lines, tabsize=8, skip_first_line=False) -> dedented lines
    
        "lines" is a list of lines to dedent.
        "tabsize" is the tab width to use for indent width calculations.
        "skip_first_line" is a boolean indicating if the first line should
            be skipped for calculating the indent width and for dedenting.
            This is sometimes useful for docstrings and similar.
    
    Same as dedent() except operates on a sequence of lines. Note: the
    lines list is modified **in-place**.
    """
    DEBUG = False
    if DEBUG: 
        print "dedent: dedent(..., tabsize=%d, skip_first_line=%r)"\
              % (tabsize, skip_first_line)
    indents = []
    margin = None
    for i, line in enumerate(lines):
        if i == 0 and skip_first_line: continue
        indent = 0
        for ch in line:
            if ch == ' ':
                indent += 1
            elif ch == '\t':
                indent += tabsize - (indent % tabsize)
            elif ch in '\r\n':
                continue # skip all-whitespace lines
            else:
                break
        else:
            continue # skip all-whitespace lines
        if DEBUG: print "dedent: indent=%d: %r" % (indent, line)
        if margin is None:
            margin = indent
        else:
            margin = min(margin, indent)
    if DEBUG: print "dedent: margin=%r" % margin

    if margin is not None and margin > 0:
        for i, line in enumerate(lines):
            if i == 0 and skip_first_line: continue
            removed = 0
            for j, ch in enumerate(line):
                if ch == ' ':
                    removed += 1
                elif ch == '\t':
                    removed += tabsize - (removed % tabsize)
                elif ch in '\r\n':
                    if DEBUG: print "dedent: %r: EOL -> strip up to EOL" % line
                    lines[i] = lines[i][j:]
                    break
                else:
                    raise ValueError("unexpected non-whitespace char %r in "
                                     "line %r while removing %d-space margin"
                                     % (ch, line, margin))
                if DEBUG:
                    print "dedent: %r: %r -> removed %d/%d"\
                          % (line, ch, removed, margin)
                if removed == margin:
                    lines[i] = lines[i][j+1:]
                    break
                elif removed > margin:
                    lines[i] = ' '*(removed-margin) + lines[i][j+1:]
                    break
            else:
                if removed:
                    lines[i] = lines[i][removed:]
    return lines

def _dedent(text, tabsize=8, skip_first_line=False):
    """_dedent(text, tabsize=8, skip_first_line=False) -> dedented text

        "text" is the text to dedent.
        "tabsize" is the tab width to use for indent width calculations.
        "skip_first_line" is a boolean indicating if the first line should
            be skipped for calculating the indent width and for dedenting.
            This is sometimes useful for docstrings and similar.
    
    textwrap.dedent(s), but don't expand tabs to spaces
    """
    lines = text.splitlines(1)
    _dedentlines(lines, tabsize=tabsize, skip_first_line=skip_first_line)
    return ''.join(lines)


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


# Recipe: run (0.7+)
_RUN_DEFAULT_LOGSTREAM = ("RUN", "DEFAULT", "LOGSTREAM")
def __run_log(logstream, msg, *args, **kwargs):
    if logstream is None:
        pass
    elif logstream is _RUN_DEFAULT_LOGSTREAM:
        try:
            log
        except NameError:
            pass
        else:
            if hasattr(log, "debug"):
                log.debug(msg, *args, **kwargs)
    else:
        logstream(msg, *args, **kwargs)

def _run(cmd, logstream=_RUN_DEFAULT_LOGSTREAM, dry_run=False):
    """Run the given command.

        "cmd" is the command to run
        "logstream" is an optional logging stream on which to log the 
            command. If None, no logging is done. If unspecifed, this 
            looks for a Logger instance named 'log' and logs the command 
            on log.debug().

    Raises OSError is the command returns a non-zero exit status.
    """
    __run_log(logstream, "running '%s'", cmd)
    if dry_run:
        return
    fixed_cmd = cmd
    if sys.platform == "win32" and cmd.count('"') > 2:
        fixed_cmd = '"' + cmd + '"'
    retval = os.system(fixed_cmd)
    if hasattr(os, "WEXITSTATUS"):
        status = os.WEXITSTATUS(retval)
    else:
        status = retval
    if status:
        raise OSError(status, "error running '%s'" % cmd)

def _run_in_dir(cmd, cwd, logstream=_RUN_DEFAULT_LOGSTREAM, dry_run=False):
    """Run the given command in the given working directory.

        "cmd" is the command to run
        "cwd" is the directory in which the commmand is run.
        "logstream" is an optional logging stream on which to log the 
            command. If None, no logging is done. If unspecifed, this 
            looks for a Logger instance named 'log' and logs the command 
            on log.debug().

    Raises OSError is the command returns a non-zero exit status.
    """
    old_dir = os.getcwd()
    try:
        if not dry_run:
            os.chdir(cwd)
        __run_log(logstream, "running '%s' in '%s'", cmd, cwd)
        if dry_run:
            return
        _run(cmd, logstream=None)
    finally:
        if not dry_run:
            os.chdir(old_dir)

# Recipe: pretty_logging (0.1)
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
        record.levelname = record.levelname.lower()
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

def _setup_logging():
    hdlr = logging.StreamHandler()
    defaultFmt = "%(name)s: %(levelname)s: %(message)s"
    infoFmt = "%(name)s: %(message)s"
    fmtr = _PerLevelFormatter(fmt=defaultFmt,
                              fmtFromLevel={logging.INFO: infoFmt})
    hdlr.setFormatter(fmtr)
    logging.root.addHandler(hdlr)
    log.setLevel(logging.INFO)


#---- mainline

def main(argv):
    shell = Shell()
    return shell.main(argv, loop=cmdln.LOOP_NEVER)

if __name__ == "__main__":
    if sys.version_info[:2] <= (2,2): __file__ = sys.argv[0]
    _setup_logging()
    try:
        retval = main(sys.argv)
    except KeyboardInterrupt:
        sys.exit(1)
    except SystemExit:
        raise
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


