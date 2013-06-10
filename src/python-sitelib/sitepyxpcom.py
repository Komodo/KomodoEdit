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

"""Komodo's sitepyxpcom: loaded by the PyXPCOM Component Loader
(pyloader) during XPCOM initialization.

Redirect Python's stdout/stderr to log files in Komodo user app data
dir. This is necessary on Windows if running without a console
(subsystem:windows). Otherwise Python output during PyXPCOM registration
can choke, fail, result in borked PyXPCOM and result in faulty Komodo
startup.

As well, these log files might be useful for debugging.

Note: this is only done for non-verbose mode. I.e. if "-v" is used the
output is written to the console.
"""

import os
import sys
import codecs

def redirect_std_handles():
    stdout_log_name = "pystdout.log"
    stderr_log_name = "pystderr.log"

    # Save the old handles.
    sys.stderr_orig = sys.stderr
    sys.stdout_orig = sys.stdout

    log_dir = None
    if sys.platform.startswith("win"):
        # on Windows, os.environ uses the ANSI (MBCS) APIs; that falls on its
        # face if the environment variable we want contains Unicode.  Use ctypes
        # to fetch what we want instead.  See bug 94439.
        # Note that sometimes this will fail; just fall back to os.environ in
        # that case.  See bug 95367.
        import ctypes
        _wgetenv = ctypes.cdll.msvcrt._wgetenv
        _wgetenv.argtypes = [ctypes.c_wchar_p]
        _wgetenv.restype = ctypes.c_wchar_p
        log_dir = _wgetenv("_KOMODO_VERUSERDATADIR")

    if log_dir is None:
        log_dir = os.environ.get("_KOMODO_VERUSERDATADIR", None)

    if log_dir is not None:
        stdout_log_path = os.path.join(log_dir, stdout_log_name)
        stderr_log_path = os.path.join(log_dir, stderr_log_name)
        sys.stdout = codecs.open(stdout_log_path, "w", "UTF-8")
        sys.stderr = codecs.open(stderr_log_path, "w", "UTF-8")
    else:
        # Fallback to "writing" to /dev/null.
        class NullWriter:
            def __init__(self, name):
                self.name = name
            def write(self, s): pass
            def writelines(self, s): pass
            def flush(self): pass
            def close(self):
                self.closed = True
        sys.stdout = NullWriter("<stdout>")
        sys.stderr = NullWriter("<stderr>")


#---- mainline

if not os.environ.has_key("KOMODO_VERBOSE"):
    redirect_std_handles()

if __debug__ or os.environ.has_key("KOMODO_DEVELOPER"):
    import thread_helper
