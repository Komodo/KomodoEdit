#!python

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

# equiv to Komodo's komodo.exe

import os
import sys
import re
import time
if sys.platform.startswith("win"):
    import win32pipe
    import win32api
    import win32file
    SW_SHOWDEFAULT = 10 # from win32con
    import win32process
    import win32event
    from win32com.shell import shellcon, shell
else:
    import fcntl


#---- globals

def _getKomodoVersion():
    """Return a "MAJOR.MINOR" version string for the currently configured
    Komodo.
    """
    sys.path.insert(0, os.path.join(os.path.dirname(sys.argv[0]), os.pardir,
                                                    os.pardir, os.pardir))
    try:
        import bkconfig
        version = bkconfig.version             # '1.9.0-devel'
        version = re.split('\.|-', version)    # ['1', '9', '0', 'devel']
        version = "%s.%s" % tuple(version[:2]) # '1.9'
    except ImportError:
        # fallback
        version = "2.0"
    del sys.path[0]
    return version

# Komodo's status values.
KS_NOTRUNNING, KS_STARTING, KS_RUNNING = range(3)

ver = _getKomodoVersion()
if sys.platform.startswith("win"):
    _gStatusLockName = "komodo-%s-status-lock" % ver
    _gStartingEventName = "komodo-%s-starting" % ver
    _gRunningEventName = "komodo-%s-running" % ver
    _gCommandmentsLockName = "komodo-%s-commandments-lock" % ver
    _gCommandmentsEventName = "komodo-%s-new-commandments" % ver
    _gCommandmentsFileName = os.path.join(
        shell.SHGetFolderPath(0, shellcon.CSIDL_APPDATA, 0, 0),
        "ActiveState", "Komodo", ver, "commandments.txt")
else:
    _gRunningLockFileName = os.path.expanduser("~/.komodo/%s/running.lock" % ver)
    _gCommandmentsFileName = os.path.expanduser("~/.komodo/%s/commandments.fifo" % ver)
del ver



#---- support routines

def startMozilla():
    if sys.platform.startswith("win"):
        si = win32process.STARTUPINFO() 
        si.dwFlags = win32process.STARTF_USESHOWWINDOW
        si.wShowWindow = SW_SHOWDEFAULT

        hProcess, hThread, processId, threadId\
            = win32process.CreateProcess(
                None,           # app name
                "C:\\Python22\\python.exe mozilla.py", # command line 
                None,           # process security attributes 
                None,           # primary thread security attributes 
                0,              # handles are inherited 
                0,              # creation flags 
                None,           # environment
                None,           # current working directory
                si)             # STARTUPINFO pointer 
    else:
        childpid = os.fork()
        if childpid < 0:
            raise "XXX Could not fork"
        elif childpid == 0: # child
            os.execvp("python", ["python", "mozilla.py"])


def issueKomodoCommandments(cmds):
    if not cmds:
        return
    
    if sys.platform.startswith("win"):
        # Grab the lock.
        lock = win32event.CreateMutex(None, 0, _gCommandmentsLockName)
        win32event.WaitForSingleObject(lock, win32event.INFINITE)

        # Append the new commandments.
        f = open(_gCommandmentsFileName, 'a')
        for cmd in cmds:
            f.write(cmd)
        f.close()
        
        # Signal Komodo that there are new commandments.
        newCommandments = win32event.CreateEvent(None, 1, 0,
                                                 _gCommandmentsEventName)
        win32event.SetEvent(newCommandments)
        win32api.CloseHandle(newCommandments)
        
        # Release the lock.
        win32event.ReleaseMutex(lock)
        win32api.CloseHandle(lock)
    else:
        fd = os.open(_gCommandmentsFileName, os.O_WRONLY)
        for cmd in cmds:
            os.write(fd, cmd)
        os.close(fd)


def acquireKomodoStatusLock():
    # No such lock used on Linux.
    lock = None
    if sys.platform.startswith("win"):
        lock = win32event.CreateMutex(None, 0, _gStatusLockName)
        #XXX Perhaps should have a reasonable timeout?
        win32event.WaitForSingleObject(lock, win32event.INFINITE)
    return lock

def releaseKomodoStatusLock(lock):
    # No such lock used on Linux.
    if sys.platform.startswith("win"):
        win32event.ReleaseMutex(lock)
        win32api.CloseHandle(lock)


def getKomodoStatus():
    """Return one of the KS_* contants indicating the status of a Komodo
    executable (a.k.a. mozilla.exe), if any.
    
    Linux:
        - Komodo is running if there is a lock on the running lock file.
        - Otherwise, Komodo is starting if the running lock file exists.
    Windows:
        - Komodo is running if the "Running Event" is signaled;
        - Otherwise, Komodo is starting if the "Starting Event" is
          signaled.
    """
    if sys.platform.startswith("win"):
        running = win32event.CreateEvent(None, 1, 0, _gRunningEventName)
        try:
            rv = win32event.WaitForSingleObject(running, 0)
            if rv == win32event.WAIT_OBJECT_0:
                return KS_RUNNING
        finally:
            win32api.CloseHandle(running)

        starting = win32event.CreateEvent(None, 1, 0, _gStartingEventName)
        try:
            rv = win32event.WaitForSingleObject(starting, 0)
            if rv == win32event.WAIT_OBJECT_0:
                return KS_STARTING
        finally:
            win32api.CloseHandle(starting)

        return KS_NOTRUNNING

    else: # Linux
        # If cannot get a lock on the running lock file then Komodo is running.
        try:
            fd = os.open(_gRunningLockFileName, os.O_RDONLY)
        except OSError, ex:
            # OSError: [Errno 2] No such file or directory: 'running.lock'
            if ex.errno == 2:
                return KS_NOTRUNNING
            else:
                raise

        try:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except IOError, ex:
                # Darwin:
                #   IOError: [Errno 35] Resource temporarily unavailable
                # Elsewhere:
                #   IOError: [Errno 11] Resource temporarily unavailable
                errorid = (sys.platform == "darwin" and 35 or 11)
                if ex.errno == errorid:
                    return KS_RUNNING
                else:
                    raise
            fcntl.flock(fd, fcntl.LOCK_UN | fcntl.LOCK_NB)
            return KS_STARTING
        finally:
            os.close(fd)


def setKomodoStatusToStarting():
    handle = None
    if sys.platform.startswith("win"):
        handle = win32event.CreateEvent(None, 1, 0, _gStartingEventName)
        win32event.SetEvent(handle)
    else:
        f = open(_gRunningLockFileName, 'w')
        f.write('Komodo is starting')
        f.close()
    return handle


def waitUntilKomodoIsRunning():
    """Return when the starting Komodo is up and running.
    
    Returns true if the wait was successful. Returns false otherwise (e.g.
    timed out).
    """
    retval = 1
    
    if sys.platform.startswith("win"):
        running = win32event.CreateEvent(None, 1, 0, _gRunningEventName)
        try:
            rv = win32event.WaitForSingleObject(running, win32event.INFINITE)
            if rv == win32event.WAIT_OBJECT_0:
                retval = 1
            else:
                raise "Error waiting for Komodo to start up: %r" % rv
        finally:
            win32api.CloseHandle(running)           

    else:
        # Try to ensure that a Komodo is actually running and that the
        # running lock file isn't just there because Komodo crashed last
        # time. Otherwise Komodo will never start.
        for i in range(60, 0, -1):
            if getKomodoStatus() == KS_RUNNING:
                break
            print "Waiting for an existing Komodo to finish "\
                  "starting up (timeout in %d sec)." % i
            time.sleep(1)
        else:
            print "WARNING: Either an existing Komodo is locked trying to\n"\
                  "         startup or Komodo did not shutdown properly \n"\
                  "         last time. Recovering and re-starting."
            # Timed out: Komodo has not started up, so start up our own.
            os.unlink(_gRunningLockFileName)
            retval = 0

    return retval


#---- mainline

def main(argv):
    # Determine what action, w.r.t. mozilla.exe, this komodo.exe should take:
    #  KA_NOTHING: Komodo (mozilla.exe) is running already, nothing to do.
    #  KA_WAIT: Komodo is currently starting up. Just wait for it to start
    #      up and then proceed.
    #  KA_STARTANDWAIT: There is no Komodo running or starting. Start Komodo
    #      and wait for it to startup.
    KA_NOTHING, KA_WAIT, KA_STARTANDWAIT = range(3)
    lock = acquireKomodoStatusLock()
    status = getKomodoStatus()
    startingHandle = None
    if status == KS_NOTRUNNING:
        action = KA_STARTANDWAIT
        startingHandle = setKomodoStatusToStarting()
    elif status == KS_STARTING:
        action = KA_WAIT
    elif status == KS_RUNNING:
        action = KA_NOTHING
    else:
        raise "Unexpected Komodo status: %r" % status
    releaseKomodoStatusLock(lock)

    # Perform the appropriate action. After this Komodo is up and running.
    if action == KA_NOTHING:
        pass
    elif action == KA_STARTANDWAIT:
        startMozilla()
        if not waitUntilKomodoIsRunning():
            print "XXX wait was not successful, starting mozilla again"
            startMozilla()
            waitUntilKomodoIsRunning()
    elif action == KA_WAIT:
        if not waitUntilKomodoIsRunning():
            startMozilla()
            waitUntilKomodoIsRunning()
    else:
        raise "Unexpected action for komodo.exe: %r" % action
    if startingHandle and sys.platform.startswith("win"):
        win32api.CloseHandle(startingHandle)

    cmds = ["open\t%s\n" % os.path.abspath(arg) for arg in argv[1:]]
    issueKomodoCommandments(cmds)


if __name__ == "__main__":
    sys.exit( main(sys.argv) )
