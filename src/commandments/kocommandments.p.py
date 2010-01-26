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

r"""Komodo Commandments support module.

This module allows you to issue commandments to a running Komodo.

Usage:

    import kocommandments as kc
    kc.issue(<commandment>, [<args>, [<komodo-version>]])

where
    
    <commandment> is a supported commandment name
    <args> is an optional list of arguments for the commandment
    <komodo-version> is the MAJOR.MINOR version number of the Komodo
        with which to communicate.

The authority on supported commandments and their format is the
commandments spec:
    http://specs.tl.activestate.com/kd/kd-0123.html
    (was: http://specs.activestate.com/Komodo_Jaguar/tech/commandments.html#supported-commandments)
"""

import os
import sys
import re
import types
import socket
import logging

if sys.platform.startswith("win"):
    import win32api
    import win32event
    from win32com.shell import shellcon, shell
else:
    import fcntl



#---- exceptions

class KoCommandmentsError(Exception):
    pass



#---- globals

_version_ = (0, 2, 0)
log = logging.getLogger("kocommandments")

# Komodo's status values.
KS_NOTRUNNING, KS_STARTING, KS_RUNNING = range(3)
_ksDesc = {KS_NOTRUNNING: "not running",
           KS_STARTING: "starting",
           KS_RUNNING: "running"}



#---- support routines

_hostname = socket.gethostname()

if sys.platform.startswith("win"):
    def _getRunningEventName(ver):
        return "komodo-%s-running" % ver
    def _getStatusLockName(ver):
        return "komodo-%s-status-lock" % ver
    def _getStartingEventName(ver):
        return "komodo-%s-starting" % ver
    def _getCommandmentsLockName(ver):
        return "komodo-%s-commandments-lock" % ver
    def _getCommandmentsEventName(ver):
        return "komodo-%s-new-commandments" % ver
    def _getCommandmentsFileName(ver):
        return os.path.join(
            shell.SHGetFolderPath(0, shellcon.CSIDL_APPDATA, 0, 0),
            "ActiveState", "Komodo", ver, "commandments.txt")
else:
    def _getStartingLockFileName(ver):
        return os.path.expanduser("~/.komodo/%s/starting.lock"
                                  % (ver, _hostname))
    def _getRunningLockFileName(ver):
        return os.path.expanduser("~/.komodo/%s/running.lock"
                                  % (ver, _hostname))
    def _getCommandmentsFileName(ver):
        return os.path.expanduser("~/.komodo/%s/commandments.fifo"
                                  % (ver, _hostname))


def _acquireStatusLock(ver):
    # No such lock used on Linux.
    lock = None
    if sys.platform.startswith("win"):
        lock = win32event.CreateMutex(None, 0, _getStatusLockName(ver))
        #XXX Perhaps should have a reasonable timeout?
        win32event.WaitForSingleObject(lock, win32event.INFINITE)
    return lock

def _releaseStatusLock(lock, ver):
    # No such lock used on Linux.
    if sys.platform.startswith("win"):
        win32event.ReleaseMutex(lock)
        win32api.CloseHandle(lock)


def _getStatus(ver):
    """Return one of the KS_* contants indicating the status of a Komodo
    executable (a.k.a. mozilla.exe), if any.
    
    "ver" is the Komodo version.
    
    Linux:
        - Komodo is running if there is a lock on the running lock file.
        - Otherwise, Komodo is starting if the running lock file exists.
    Windows:
        - Komodo is running if the "Running Event" is signaled;
        - Otherwise, Komodo is starting if the "Starting Event" is
          signaled.
    """
    if sys.platform.startswith("win"):
        running = win32event.CreateEvent(None, 1, 0,
                                         _getRunningEventName(ver))
        try:
            rv = win32event.WaitForSingleObject(running, 0)
            if rv == win32event.WAIT_OBJECT_0:
                return KS_RUNNING
        finally:
            win32api.CloseHandle(running)

        starting = win32event.CreateEvent(None, 1, 0,
                                          _getStartingEventName(ver))
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
            fd = os.open(_getRunningLockFileName(ver), os.O_RDONLY)
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
                # IOError: [Errno 11] Resource temporarily unavailable
                if ex.errno == 11:
                    return KS_RUNNING
                else:
                    raise
            fcntl.flock(fd, fcntl.LOCK_UN | fcntl.LOCK_NB)
            return KS_STARTING
        finally:
            os.close(fd)


def _waitUntilKomodoIsRunning(ver):
    """Return when the starting Komodo is up and running.
    
    "ver" is the version of Komodo to wait for

    Returns true if the wait was successful. Returns false otherwise (e.g.
    timed out).
    """
    retval = 1
    
    if sys.platform.startswith("win"):
        running = win32event.CreateEvent(None, 1, 0,
                                         _getRunningEventName(ver))
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
            if _getStatus(ver) == KS_RUNNING:
                break
            log.info("Waiting for an existing Komodo to finish "
                     "starting up (timeout in %d sec).", i)
            time.sleep(1)
        else:
            log.warn("Either an existing Komodo is locked trying to startup "
                     "or Komodo did not shutdown properly last time.")
            # Timed out: Komodo has not started up, so start up our own.
            os.unlink(_getRunningLockFileName(ver))
            retval = 0

    return retval


def _issueCommandments(commandments, ver):
    """Issue the given commandments to the running Komodo.
    
    "commandments" is a list of commandment strings
    "ver" is the version of Komodo to talk to
    """
    if not commandments:
        return

    if sys.platform.startswith("win"):
        # Grab the lock.
        lock = win32event.CreateMutex(None, 0, _getCommandmentsLockName(ver))
        win32event.WaitForSingleObject(lock, win32event.INFINITE)

        # Append the new commandments.
        f = open(_getCommandmentsFileName(ver), 'a')
        for commandment in commandments:
            f.write(commandment)
        f.close()
        
        # Signal Komodo that there are new commandments.
        newCommandments = win32event.CreateEvent(None, 1, 0,
            _getCommandmentsEventName(ver))
        win32event.SetEvent(newCommandments)
        win32api.CloseHandle(newCommandments)
        
        # Release the lock.
        win32event.ReleaseMutex(lock)
        win32api.CloseHandle(lock)
    else:
        fd = os.open(_getCommandmentsFileName(ver), os.O_WRONLY)
        for commandment in commandments:
            os.write(fd, commandment)
        os.close(fd)



#---- module interface

# #ifndef KOMODO_MAJOR_MINOR
# #error "kocommandments.py cannot be preprocessed by 'bk build quick'"
# #endif
def issue(commandment, args=[], ver="KOMODO_MAJOR_MINOR"):
    """Issue a Komodo commandment.
    
    "commandment" is the name of the commandment to issue
    "args" is an optional list of arguments for the commandment
    "ver" is the Komodo <major>.<minor> version to which to send
        commandments.

    If Komodo is not running an error is raised. If Komodo is starting
    up this will wait until Komodo has started before issuing the
    commandment.
    """
    if not commandment:
        raise ValueError("given commandment is empty")
    pattern = re.compile("^\d+\.\d+$")
    if not pattern.search(ver):
        raise ValueError("Illegal 'ver' value, '%s'. It must match '%s'"
                         % (ver, pattern.pattern))

    # Get Komodo's current status.
    lock = _acquireStatusLock(ver)
    status = _getStatus(ver)
    _releaseStatusLock(lock, ver)
    log.info("Komodo %s is %s (status=%d)", ver, _ksDesc[status], status)

    # Wait for Komodo to startup, or bail out if there is no Komodo running.
    if status == KS_NOTRUNNING:
        raise KoCommandmentsError("Komodo %s is not running" % ver)
    elif status == KS_STARTING:
        if not _waitUntilKomodoIsRunning(ver):
            raise KoCommandmentsError("waiting for Komodo %s to start failed"\
                                      % ver)
    elif status == KS_RUNNING:
        pass
    else:
        raise KoCommandmentsError("invalid status: %r" % status)

    # Issue the command.
    cmdstr = "%s%s\n" % (commandment, '\t'+ '\t'.join(args))
    _issueCommandments([cmdstr], ver)


