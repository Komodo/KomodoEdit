#!/usr/bin/env python
# Copyright (c) 2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

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


def chcon(path, context):
    """Change the security context of the given file."""
    log.debug("chcon -t %s %s", context, path)
    cmd = 'chcon -t %s --quiet "%s"' % (context, path)
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
        
    
    
    
    
