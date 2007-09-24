# Copyright (c) 2005-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

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


def redirect_std_handles():
    stdout_log_name = "pystdout.log"
    stderr_log_name = "pystderr.log"

    log_dir = os.environ.get("_KOMODO_HOSTUSERDATADIR", None)
    if log_dir is not None:
        stdout_log_path = os.path.join(log_dir, stdout_log_name)
        stderr_log_path = os.path.join(log_dir, stderr_log_name)
        sys.stdout = open(stdout_log_path, "w")
        sys.stderr = open(stderr_log_path, "w")
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

