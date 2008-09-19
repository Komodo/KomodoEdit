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
import time
if sys.platform == "win32":
    import ctypes  # used by kill() method on Windows
else:
    import signal  # used by kill() method on Linux/Mac
import logging
import threading
import warnings
from subprocess import Popen, PIPE


#-------- Globals -----------#

log = logging.getLogger("process")
#log.setLevel(logging.DEBUG)

CREATE_NEW_CONSOLE = 0x10 # same as win32process.CREATE_NEW_CONSOLE
CREATE_NO_WINDOW = 0x8000000 # same as win32process.CREATE_NO_WINDOW
WAIT_TIMEOUT = 258 # same as win32event.WAIT_TIMEOUT


#-------- Classes -----------#

# XXX - TODO: Work out what exceptions raised by SubProcess and turn into
#       ProcessError?
class ProcessError(Exception):
    def __init__(self, msg, errno=-1):
        Exception.__init__(self, msg)
        self.errno = errno

class ProcessOpen(Popen):
    def __init__(self, cmd, cwd=None, env=None, flags=None,
                 stdin=PIPE, stdout=PIPE, stderr=PIPE,
                 universal_newlines=True):
        """Create a child process.

        "cmd" is the command to run, either a list of arguments or a string.
        "cwd" is a working directory in which to start the child process.
        "env" is an environment dictionary for the child.
        "flags" are system-specific process creation flags. On Windows
            this can be a bitwise-OR of any of the win32process.CREATE_*
            constants (Note: win32process.CREATE_NEW_PROCESS_GROUP is always
            OR'd in). On Unix, this is currently ignored.
        "stdin", "stdout", "stderr" can be used to specify file objects
            to handle read (stdout/stderr) and write (stdin) events from/to
            the child. By default a file handle will be created for each
            io channel automatically, unless set explicitly to None. When set
            to None, the parent io handles will be used, which can mean the
            output is redirected to Komodo's log files.
        "universal_newlines": On by default (the opposite of subprocess).
        """
        auto_piped_stdin = False
        shell = False
        if not isinstance(cmd, (list, tuple)):
            # The cmd is the already formatted, ready for the shell. Otherwise
            # subprocess.Popen will treat this as simply one command with
            # no arguments, resulting in an unknown command.
            shell = True
        if sys.platform.startswith("win"):
            # On Windows, cmd requires some special handling of multiple quoted
            # arguments, as this is what cmd will do:
            #    See if the first character is a quote character and if so,
            #    strip the leading character and remove the last quote character
            #    on the command line, preserving any text after the last quote
            #    character.
            if cmd and shell and cmd.count('"') > 2:
                if not cmd.startswith('""') or not cmd.endswith('""'):
                    # Needs to be a re-quoted with additional double quotes.
                    # http://bugs.activestate.com/show_bug.cgi?id=75467
                    cmd = '"%s"' % (cmd, )

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

            if flags is None:
                flags = CREATE_NO_WINDOW

            # If we don't have standard handles to pass to the child process
            # (e.g. we don't have a console app), then
            # `subprocess.GetStdHandle(...)` will return None. `subprocess.py`
            # handles that (http://bugs.python.org/issue1124861)
            #
            # However, if Komodo is started from the command line, then
            # the shell's stdin handle is inherited, i.e. in subprocess.py:
            #      p2cread = GetStdHandle(STD_INPUT_HANDLE)   # p2cread == 3
            # A few lines later this leads to:
            #    Traceback (most recent call last):
            #      ...
            #      File "...\lib\mozilla\python\komodo\process.py", line 130, in __init__
            #        creationflags=flags)
            #      File "...\lib\python\lib\subprocess.py", line 588, in __init__
            #        errread, errwrite) = self._get_handles(stdin, stdout, stderr)
            #      File "...\lib\python\lib\subprocess.py", line 709, in _get_handles
            #        p2cread = self._make_inheritable(p2cread)
            #      File "...\lib\python\lib\subprocess.py", line 773, in _make_inheritable
            #        DUPLICATE_SAME_ACCESS)
            #    WindowsError: [Error 6] The handle is invalid
            #
            # I suspect this indicates that the stdin handle inherited by
            # the subsystem:windows komodo.exe process is invalid -- perhaps
            # because of mis-used of the Windows API for passing that handle
            # through. The same error can be demonstrated in PythonWin:
            #   from _subprocess import *
            #   from subprocess import *
            #   h = GetStdHandle(STD_INPUT_HANDLE)
            #   p = Popen("python -c '1'")
            #   p._make_interitable(h)
            #
            # I don't understand why the inherited stdin is invalid for
            # `DuplicateHandle`, but here is how we are working around this:
            # If we detect the condition where this can fail, then work around
            # it by setting the handle to `subprocess.PIPE`, resulting in
            # a different and workable code path.
            if self._needToHackAroundStdHandles() \
               and not (flags & CREATE_NEW_CONSOLE):
                if stdin is None and sys.stdin \
                   and sys.stdin.fileno() not in (0,1,2):
                    stdin = PIPE
                    auto_piped_stdin = True
                if stdout is None and sys.stdout \
                   and sys.stdout.fileno() not in (0,1,2):
                    stdout = PIPE
                if stderr is None and sys.stderr \
                   and sys.stderr.fileno() not in (0,1,2):
                    stderr = PIPE
        else:
            # subprocess raises an exception otherwise.
            flags = 0

        # Internal attributes.
        self.__cmd = cmd
        self.__retval = None
        self.__hasTerminated = threading.Condition()

        # Launch the process.
        #print "Process: %r in %r" % (cmd, cwd)
        Popen.__init__(self, cmd, cwd=cwd, env=env, shell=shell,
                       stdin=stdin, stdout=stdout, stderr=stderr,
                       universal_newlines=universal_newlines,
                       creationflags=flags)
        if auto_piped_stdin:
            self.stdin.close()

    __needToHackAroundStdHandles = None
    @classmethod
    def _needToHackAroundStdHandles(cls):
        if cls.__needToHackAroundStdHandles is None:
            if sys.platform != "win32":
                cls.__needToHackAroundStdHandles = False
            else:
                from _subprocess import GetStdHandle, STD_INPUT_HANDLE
                stdin_handle = GetStdHandle(STD_INPUT_HANDLE)
                if stdin_handle is not None:
                    cls.__needToHackAroundStdHandles = True
                    if stdin_handle != 3:
                        log.warn("`GetStdHandle(STD_INPUT_HANDLE)` != 3: "
                                 "something has changed w.r.t. std handle "
                                 "inheritance in Komodo that may affect "
                                 "subprocess launching")
                else:
                    cls.__needToHackAroundStdHandles = False
        return cls.__needToHackAroundStdHandles

    # Override the returncode handler (used by subprocess.py), this is so
    # we can notify any listeners when the process has finished.
    def _getReturncode(self):
        return self.__returncode
    def _setReturncode(self, value):
        self.__returncode = value
        if value is not None:
            # Notify that the process is done.
            self.__hasTerminated.acquire()
            self.__hasTerminated.notifyAll()
            self.__hasTerminated.release()
    returncode = property(fget=_getReturncode, fset=_setReturncode)

    # Setup the retval handler. This is a readonly wrapper around returncode.
    def _getRetval(self):
        # Ensure the returncode is set by subprocess if the process is finished.
        self.poll()
        return self.returncode
    retval = property(fget=_getRetval)

    def wait(self, timeout=None):
        """Wait for the started process to complete.
        
        "timeout" is a floating point number of seconds after
            which to timeout.  Default is None, which is to never timeout.

        If the wait time's out it will raise a ProcessError. Otherwise it
        will return the child's exit value. Note that in the case of a timeout,
        the process is still running. Use kill() to forcibly stop the process.
        """
        if timeout is None or timeout < 0:
            # Use the parent call.
            return Popen.wait(self)

        # We poll for the retval, as we cannot rely on self.__hasTerminated
        # to be called, as there are some code paths that do not trigger it.
        # The accuracy of this wait call is roughly within 1 seconds.
        time_now = time.time()
        time_end = time_now + timeout
        while time_now < time_end:
            result = self.poll()
            if result is not None:
                return result
            # We use hasTerminated here to get a faster notification.
            self.__hasTerminated.acquire()
            # XXX - Not sure what good timeout value for this is...
            self.__hasTerminated.wait(1.0)
            self.__hasTerminated.release()
            time_now = time.time()
        # last chance
        result = self.poll()
        if result is not None:
            return result

        raise ProcessError("Process timeout: waited %d seconds, "
                           "process not yet finished." % (timeout,),
                           WAIT_TIMEOUT)

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
            self.returncode = exitCode
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
            self.returncode = exitCode



class AbortableProcessHelper(object):
    """A helper class that is able to run a process and have the process be
    killed/aborted (possibly by another thread) if it is still running.
    """
    STATUS_INITIALIZED = 0         # Ready to run.
    STATUS_RUNNING = 1             # A process is running.
    STATUS_FINISHED_NORMALLY = 2   # The command/process finished normally.
    STATUS_ABORTED = 3             # The command/process was aborted.

    def __init__(self):
        self._process = None
        self._process_status = self.STATUS_INITIALIZED
        self._process_status_lock = threading.Lock()

    def ProcessOpen(self, *args, **kwargs):
        """Create a new process and return it."""
        self._process_status_lock.acquire()
        try:
            self._process_status = self.STATUS_RUNNING
            self._process = ProcessOpen(*args, **kwargs)
            return self._process
        finally:
            self._process_status_lock.release()

    def ProcessDone(self):
        """Mark the process as being completed, does not need to be aborted."""
        self._process_status_lock.acquire()
        try:
            self._process = None
            self._process_status = self.STATUS_FINISHED_NORMALLY
        finally:
            self._process_status_lock.release()

    def ProcessAbort(self):
        """Kill the process if it is still running."""
        self._process_status_lock.acquire()
        try:
            self._process_status = self.STATUS_ABORTED
            if self._process:
                self._process.kill()
                self._process = None
        finally:
            self._process_status_lock.release()



## Deprecated process classes ##

class Process(ProcessOpen):
    def __init__(self, *args, **kwargs):
        warnings.warn("'process.%s' is now deprecated. Please use 'process.ProcessOpen'." % (self.__class__.__name__))
        ProcessOpen.__init__(self, *args, **kwargs)

class ProcessProxy(Process):
    pass
