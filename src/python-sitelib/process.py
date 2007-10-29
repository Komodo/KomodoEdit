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
import sys
import signal  # used by kill() method on Linux/Mac
import ctypes  # used by kill() method on Windows
import logging
import threading
from subprocess import Popen, PIPE


#-------- Globals -----------#

log = logging.getLogger("process")
#log.setLevel(logging.DEBUG)

CREATE_NEW_CONSOLE = 0x10 # same as win32process.CREATE_NEW_CONSOLE


#-------- Classes -----------#

# XXX - TODO: Work out what exceptions raised by SubProcess and turn into
#       ProcessError?
class ProcessError(Exception):
    def __init__(self, msg, errno=-1):
        Exception.__init__(self, msg)
        self.errno = errno

class Process(Popen):
    def __init__(self, cmd, cwd=None, env=None, flags=0,
                 stdin=None, stdout=None, stderr=None,
                 universal_newlines=False):
        """Create a child process.

        "cmd" is the command to run, either a list of arguments or a string.
        "cwd" is a working directory in which to start the child process.
        "env" is an environment dictionary for the child.
        "flags" are system-specific process creation flags. On Windows
            this can be a bitwise-OR of any of the win32process.CREATE_*
            constants (Note: win32process.CREATE_NEW_PROCESS_GROUP is always
            OR'd in). On Unix, this is currently ignored.
        "universal_newlines": turn off \r output on Windows (see process.Popen
            for more info).
        """
        shell = False
        if not isinstance(cmd, (list, tuple)):
            # The cmd is the already formatted, ready for the shell. Otherwise
            # subprocess.Popen will treat this as simply one command with
            # no arguments, resulting in an unknown command.
            shell = True
        if sys.platform.startswith("win"):
            # XXX - subprocess needs to be updated to use the wide string API.
            # subprocess uses a Windows API that does not accept unicode, so
            # we need to convert all the environment variables to strings
            # before we make the call. Temporary fix to bug:
            #   http://bugs.activestate.com/show_bug.cgi?id=72311
            if env:
                encoding = sys.getfilesystemencoding()
                _enc_env = {}
                for key, value in env.items():
                    try:
                        _enc_env[key.encode(encoding)] = value.encode(encoding)
                    except UnicodeEncodeError:
                        # Could not encode it, warn we are dropping it.
                        log.warn("Could not encode environment variable %r "
                                 "so removing it", key)
                env = _enc_env
        else:
            # subprocess raises an exception otherwise.
            flags = 0
        Popen.__init__(self, cmd, cwd=cwd, env=env, shell=shell,
                       stdin=stdin, stdout=stdout, stderr=stderr,
                       universal_newlines=universal_newlines,
                       creationflags=flags)

        self.__cmd = cmd
        self.__retval = None
        self.__hasTerminated = threading.Condition()

    # Setup the retval handler. Used to keep track of process state.
    def _getRetval(self):
        return self.__retval
    def _setRetval(self, value):
        self.__retval = value
        if value is not None:
            # Notify that the process is done.
            self.__hasTerminated.acquire()
            self.__hasTerminated.notifyAll()
            self.__hasTerminated.release()
    retval = property(fget=_getRetval, fset=_setRetval)

    def wait(self, timeout=None):
        """Wait for the started process to complete.
        
        "timeout" is a floating point number of seconds after
            which to timeout.  Default is None, which is to never timeout.

        If the wait time's out it will raise a ProcessError. Otherwise it
        will return the child's exit value. Note that in the case of a timeout,
        the process is still running. Use kill() to forcibly stop the process.
        """
        # If it's already finished, return with the result.
        if self.retval is not None:
            return self.retval

        if timeout is None or timeout < 0:
            # Use the parent call.
            return Popen.wait(self)
        else:
            # Wait for the retval set event.
            self.__hasTerminated.acquire()
            self.__hasTerminated.wait(timeout)
            try:
                if self.__retval is None:
                    # 258 means timeout, defined in koIRunService.idl
                    raise ProcessError("Process timeout: waited %d seconds, "
                                       "process not yet finished." % (timeout,),
                                       258)
                else:
                    return self.__retval
            finally:
                self.__hasTerminated.release()

    # For backward compatibility with older process.py
    def close(self):
        pass

    # For backward compatibility with older process.py
    def kill(self, exitCode=-1, gracePeriod=None, sig=None):
        """Kill process.
        
        "exitCode" this sets what the process return value will be.
        "gracePeriod" [deprecated, not supported]
        "sig" (Unix only) is the signal to use to kill the process. Defaults
            to signal.SIGKILL. See os.kill() for more information.
        """
        if gracePeriod is not None:
            import warnings
            warnings.warn("process.kill() gracePeriod is no longer used",
                          DeprecationWarning)

        # Need to ensure stdin is closed, makes it easier to end the process.
        if self.stdin is not None:
            self.stdin.close()

        if sys.platform.startswith("win"):
            ctypes.windll.kernel32.TerminateProcess(int(self._handle), exitCode)
            self.retval = exitCode
        else:
            if sig is None:
                sig = signal.SIGKILL
            try:
                # XXX - Use os.killpg() instead to kill all subprocesses?
                os.kill(self.pid, sig)
            except OSError, ex:
                if ex.errno != 3:
                    # Ignore:   OSError: [Errno 3] No such process
                    raise
            self.retval = exitCode

class ProcessOpen(Process):
    """Create a process and setup pipes to it standard handles.

    This is a super popen3.
    """
    def __init__(self, cmd, mode='t', cwd=None, env=None,
                 universal_newlines=False):
        """Create a Process with proxy threads for each std handle.

        "cmd" is the command to run, either a list of arguments or a string.
        "mode" (Windows only) specifies whether the pipes used to communicate
            with the child are openned in text, 't', or binary, 'b', mode.
            This is ignored on platforms other than Windows. Default is 't'.
        "cwd" optionally specifies the directory in which the child process
            should be started. Default is None, a.k.a. inherits the cwd from
            the parent.
        "env" is optionally a mapping specifying the environment in which to
            start the child. Default is None, a.k.a. inherits the environment
            of the parent.
        "universal_newlines": same as in subprocess.Popen
        """
        # XXX - Ignoring "mode". Perhaps it can be used to set universal
        #       newlines?
        Process.__init__(self, cmd, cwd=cwd, env=env,
                         stdin=PIPE, stdout=PIPE, stderr=PIPE,
                         universal_newlines=universal_newlines)
        log.info("ProcessOpen.__init__(cmd=%r, mode=%r, cwd=%r, env=%r)",
                 cmd, mode, cwd, env)

class ProcessProxy(Process):
    """Create a process and proxy communication via the standard handles.
    """
    def __init__(self, cmd, mode='t', cwd=None, env=None,
                 stdin=None, stdout=None, stderr=None):
        """Create a Process with proxy threads for each std handle.

        "cmd" is the command string or argument vector to run.
        "mode" (Windows only) specifies whether the pipes used to communicate
            with the child are openned in text, 't', or binary, 'b', mode.
            This is ignored on platforms other than Windows. Default is 't'.
        "cwd" optionally specifies the directory in which the child process
            should be started. Default is None, a.k.a. inherits the cwd from
            the parent.
        "env" is optionally a mapping specifying the environment in which to
            start the child. Default is None, a.k.a. inherits the environment
            of the parent.
        "stdin", "stdout", "stderr" can be used to specify objects with
            file-like interfaces to handle read (stdout/stderr) and write
            (stdin) events from the child. By default a process.IOBuffer
            instance is assigned to each handler.
        """
        # XXX - Ignoring "mode". Perhaps it can be used to set universal
        #       newlines?
        if stdin is None:
            stdin = PIPE
        if stdout is None:
            stdout = PIPE
        if stderr is None:
            stderr = PIPE
        Process.__init__(self, cmd, cwd=cwd, env=env,
                         stdin=stdin, stdout=stdout, stderr=stderr)
        log.info("ProcessProxy.__init__(cmd=%r, mode=%r, cwd=%r, env=%r, "\
                 "stdin=%r, stdout=%r, stderr=%r)",
                 cmd, mode, cwd, env, stdin, stdout, stderr)
