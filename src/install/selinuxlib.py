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

"""Some tools for working with an SELinux installation."""

import os
import sys
import logging
from glob import glob
import re


#---- exceptions

class SELinuxError(Exception):
    pass


#---- globals

log = logging.getLogger("selinuxlib")


#---- public interface

class SELinux:
    """A class for working with an SELinux installation."""

    def __init__(self):
        self._file_context_config = None # loaded lazily

    def is_installed(self):
        """Return True iff SELinux extensions are installed (whether or not
        they are enabled).
        """
        if not sys.platform.startswith("linux"):
            log.debug("SELinux is not installed: this is not Linux")
            return False
    
        # Determine if SELinux-extensions are installed.
        landmarks = [
            "/usr/sbin/selinuxenabled",
            "/etc/selinux/config",
            "/sbin/selinuxenabled",
        ]
        for landmark in landmarks:
            if os.path.exists(landmark):
                log.debug("SELinux is installed: `%s' exists", landmark)
                return True
        else:
            import which
            try:
                selinuxenabled_path = which.which("selinuxenabled")
            except which.WhichError:
                pass
            else:
                log.debug("SELinux is installed: `%s' exists",
                          selinuxenabled_path)
                return True
        log.debug("SELinux is not installed: could not find any of its "
                  "landmarks")

    def is_enabled(self):
        """Return True iff SELinux is enabled."""
        candidates = [
            "/usr/sbin/selinuxenabled",
            "/sbin/selinuxenabled",
        ]
        for candidate in candidates:
            if os.path.exists(candidate):
                selinuxenabled_path = candidate
                break
        else:
            import which
            try:
                selinuxenabled_path = which.which("selinuxenabled")
            except which.WhichError:
                log.warn("couldn't find 'selinuxenabled' to "
                         "determine if SELinux is enabled (presuming not)")
                return False
        retval = os.system(selinuxenabled_path)
        status = os.WEXITSTATUS(retval)
        return status == 0

    def is_path_labeled(self, path):
        """Return True if the given path is "labeled" for security contexts

        This is related to the error you'll get trying to 'chcon' a path when
        SELinux things aren't setup:
            $ chcon -t shlib_t /home/trentm/foo.so
            chcon: can't apply partial context to unlabeled file /home/trentm/foo.so

        You'll also get this:
            $ ls --context /home/trentm/foo.so
            Sorry, this option can only be used on a SELinux kernel.
        So we'll use that as the check.

        Note: A cleaner solution to the general problem here (chcon when
        necessary, but don't unnecessarily die) might be to have pattern
        matching for known and acceptable failure on the `chcon` call).
        """
        cmd = 'ls --context "%s" 2>/dev/null 1>/dev/null' % path
        retval = os.system(cmd)
        if hasattr(os, "WEXITSTATUS"):
            status = os.WEXITSTATUS(retval)
        else:
            status = retval
        return not status  # status 0 -> True, status non-0 -> False

    def _get_file_context_config(self):
        """Lazily get the file context config."""
        if self._file_context_config is None:
            self._file_context_config = self._load_file_context_config()
        return self._file_context_config

    def _load_file_context_config(self):
        config = []
        file_contexts_paths \
            = "/etc/selinux/targeted/contexts/files/file_contexts*"
        for context_file in glob(file_contexts_paths):
            log.debug("read file context config: `%s'", context_file)
            for line in open(context_file, 'r'):
                if '#' in line:
                    line = line[:line.index('#')].strip()
                if not line.strip():
                    continue
                parts = line.split()
                if len(parts) == 2:
                    filter = None
                elif len(parts) == 3:
                    filter = {"--": "file", # only match to regular files
                              "-d": "dir",  # only match to directories
                             }.get(parts[1], None)
                else:
                    log.warn("unexpected line in `%s': %r (ignoring)",
                             context_file, line)
                try:
                    config.append( (re.compile('^'+parts[0]+'$'),
                                    filter,
                                    parts[-1]) )
                except re.error:
                    log.warn("error compiling %r regex from `%s': skipping",
                             parts[0], context_file)
        return config

    def context_from_path(self, path):
        # As per docs in /etc/selinux/targeted/contexts/files/file_contexts
        # the *last* one wins.
        matching_context = None
        is_path_dir = os.path.isdir(path)
        is_path_file = os.path.isfile(path)
        for pattern, filter, context in self._get_file_context_config():
            if filter is None:
                pass
            elif filter == "dir":
                if not is_path_dir:
                    continue
            elif filter == "file":
                if not is_path_file:
                    continue
            if pattern.match(path):
                log.debug("`%s' matches `%s' -> context `%s'", path,
                          pattern.pattern, context)
                matching_context = context
        return matching_context

    def allow_stack_execution(self, path):
        # Ensure the path is allowed to have stack execution priviliges.
        import which
        try:
            execstack_path = which.which("execstack")
        except which.WhichError:
            # Not found - nothing to do then.
            return

        log.debug("Adding stack execution priviliges for: %r", path)
        cmd = '%s -s "%s"' % (execstack_path, path)
        retval = os.system(cmd)
        if retval:
            log.warn("selinux: setting stack execution failed: %r", cmd)

def chcon(path, context):
    """Change the security context of the given file."""
    log.debug("chcon -t %s %s", context, path)
    cmd = 'chcon -t %s "%s"' % (context, path)
    retval = os.system(cmd)
    if retval:
        raise SELinuxError("running `%s' failed", cmd)



#---- mainline (primarily for testing)

def main():
    if '-v' in sys.argv:
        log.setLevel(logging.DEBUG)

    selinux = SELinux()
    if not selinux.is_installed():
        print "SELinux is not installed. Done."
        return
    
    for path in sys.argv[1:]:
        context = selinux.context_from_path(path)
        print "%s: %s" % (path, context)
    

if __name__ == "__main__":
    logging.basicConfig()
    sys.exit(main())
        
    
    
    
    
