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

import os
from os.path import islink, realpath, join
import shutil
import sys
import tempfile
import codecs

# Modified recipe: paths_from_path_patterns (0.5)
def should_include_path(path, includes=None, excludes=None, isRemotePath=False):
    """Return True iff the given path should be included."""
    from os.path import basename
    from fnmatch import fnmatch, fnmatchcase

    if isRemotePath:
        # Always perform a case sensitive comparison.
        fnmatch = fnmatchcase
    base = basename(path)
    if includes:
        for include in includes:
            if fnmatch(base, include):
                #try:
                #    log.debug("include `%s' (matches `%s')", path, include)
                #except (NameError, AttributeError):
                #    pass
                break
        else:
            #try:
            #    log.debug("exclude `%s' (matches no includes)", path)
            #except (NameError, AttributeError):
            #    pass
            return False
    if excludes:
        for exclude in excludes:
            if fnmatch(base, exclude):
                #try:
                #    log.debug("exclude `%s' (matches `%s')", path, exclude)
                #except (NameError, AttributeError):
                #    pass
                return False
    return True

def _walk_avoiding_cycles(top, topdown=True, onerror=None, followlinks=False,
                          includes=None, excludes=None):
    seen_rpaths = {top: 1}
    for root, dirs, files in os.walk(top, topdown, onerror, followlinks):
        # We modify the original "dirs" list, so that os.walk will then ignore
        # the directories we've removed.
        for dir in dirs[:]:  # a copy, so we can modify in-place.
            dirpath = join(root, dir)
            if islink(dirpath):
                rpath = realpath(dirpath)
                if rpath in seen_rpaths:
                    #print "Found cyclical path: %s to %s" % (dirpath, rpath)
                    dirs.remove(dir)
                    continue
                seen_rpaths[rpath] = 1
        if includes or excludes:
            # The dirs must be modified in place (see comment above)!
            dirs[:] = [dir for dir in dirs if should_include_path(dir, includes, excludes)]
            files = [f for f in files if should_include_path(f, includes, excludes)]
        yield (root, dirs, files)

def walk_avoiding_cycles(top, topdown=True, onerror=None, followlinks=False,
                         includes=None, excludes=None):
    """Modified os.walk, one that will keep track of followed symlinks in order
    to avoid cyclical links. Cyclical symlinks often need to be avoided,
    otherwise os.walk can walk forever.

    Note: This does not avoid duplicates, example:

        subdir
        subdir/a
        subdir/b => ../subdir   # avoid this
        subdir/c => ./a         # allow this (as it's not cyclical)
    """

    if not followlinks:
        if includes or excludes:
            raise Exception("walk_avoiding_cycles can only use includes/excludes when "
                            "followlinks is True")
        return os.walk(top, topdown, onerror, followlinks)
    else:
        # Can only avoid cycles if topdown is True.
        if not topdown:
            raise Exception("walk_avoiding_cycles can only avoid cycles when "
                            "topdown is True")
        return _walk_avoiding_cycles(top, topdown, onerror, followlinks,
                                     includes, excludes)

#---- Local tree copying: shutil.copytree works when only target doesn't exist,
#     so copy parts manually, and use shutil.copytree for new sub-parts.
def copyLocalFolder(srcPath, targetDirPath):
    targetFinalPath = os.path.join(targetDirPath, os.path.basename(srcPath))
    if not os.path.exists(targetFinalPath):
        shutil.copytree(srcPath, targetFinalPath, symlinks=True)
    else:
        for d in os.listdir(srcPath):
            candidate = os.path.join(srcPath, d)
            if os.path.isdir(candidate):
                copyLocalFolder(candidate, targetFinalPath)
            else:
                shutil.copy(candidate, os.path.join(targetFinalPath, d))

if sys.platform == "win32":
    import ctypes
    kernel32 = ctypes.WinDLL("kernel32")
    GetFileAttributes = kernel32.GetFileAttributesW
    GetFileAttributes.rettype = ctypes.c_uint32
    GetFileAttributes.argtypes = [ctypes.c_wchar_p]
    minus_one = ctypes.c_uint32(-1)
    def isHiddenFile(path):
        try:
            result = GetFileAttributes(path)
            if result == minus_one:
                # Error getting attributes
                # Assume if we can't access <path>, nothing else should either.
                return True
            return result & 0x02
        except:
            import logging
            log = logging.getLogger("fileutils")
            log.exception("Internal error: Unexpected exception while trying to access file %s", path)
            return True
else:
    def isHiddenFile(path):
        return False


class AtomicFileWriter(object):
    """A contextual utility class to give atomic write operations.
    
    Writes to a temporary file and then performs an atomic move when completed.
    """
    def __init__(self, filename, mode, encoding=None):
        self.filename = filename
        self.mode = mode
        self.encoding = encoding
    def __enter__(self):
        (temp_fd, self.temp_filename) = tempfile.mkstemp(".komodo")
        os.close(temp_fd)
        if self.encoding:
            self.file = codecs.open(self.temp_filename, self.mode, self.encoding)
        else:
            self.file = open(self.temp_filename, self.mode)
        return self.file
    def __exit__(self, exc_type, exc_value, exc_tb):
        if exc_type:
            return
        if not self.file.closed:
            self.file.close()
        self.file = None
        try:
            shutil.move(self.temp_filename, self.filename)
        except OSError, details:
            # Could not move, resort to a copy then.
            shutil.copy(self.temp_filename, self.filename)

