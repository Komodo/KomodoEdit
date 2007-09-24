#!/usr/bin/env python
# Copyright (c) 2000-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

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
    http://specs.activestate.com/Komodo_Jaguar/tech/commandments.html#supported-commandments
"""

import os
import sys
import re
import types
import socket
import logging

if sys.platform.startswith("win"):
    import wnd.komodo
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
        from wnd.komodo import get_path_by_shell_clsidl
        from wnd.api.shell.consts import CLSIDL_APPDATA
        return os.path.join(
            get_path_by_shell_clsidl(CLSIDL_APPDATA),
            "ActiveState", "Komodo", ver, "host-"+_hostname,
            "commandments.txt")
else:
    def _getStartingLockFileName(ver):
        return os.path.expanduser("~/.komodo/%s/host-%s/starting.lock"
                                  % (ver, _hostname))
    def _getRunningLockFileName(ver):
        return os.path.expanduser("~/.komodo/%s/host-%s/running.lock"
                                  % (ver, _hostname))
    def _getCommandmentsFileName(ver):
        return os.path.expanduser("~/.komodo/%s/host-%s/commandments.fifo"
                                  % (ver, _hostname))


def _acquireStatusLock(ver):
    # No such lock used on Linux.
    lock = None
    if sys.platform.startswith("win"):
        lock = wnd.komodo.create_mutex(_getStatusLockName(ver))
        #XXX Perhaps should have a reasonable timeout?
        wnd.komodo.wait_for_single_object(lock)
    return lock

def _releaseStatusLock(lock, ver):
    # No such lock used on Linux.
    if sys.platform.startswith("win"):
        wnd.komodo.release_mutex(lock)
        wnd.komodo.close_handle(lock)


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
        running = wnd.komodo.create_event(_getRunningEventName(ver))
        try:
            rv = wnd.komodo.wait_for_single_object(running, 0)
            if rv == wnd.komodo.WAIT_OBJECT_0:
                return KS_RUNNING
        finally:
            wnd.komodo.close_handle(running)

        starting = wnd.komodo.create_event(_getStartingEventName(ver))
        try:
            rv = wnd.komodo.wait_for_single_object(starting, 0)
            if rv == wnd.komodo.WAIT_OBJECT_0:
                return KS_STARTING
        finally:
            wnd.komodo.close_handle(starting)

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
        running = wnd.komodo.create_event(_getRunningEventName(ver))
        try:
            rv = wnd.komodo.wait_for_single_object(running)
            if rv == wnd.komodo.WAIT_OBJECT_0:
                retval = 1
            else:
                raise "Error waiting for Komodo to start up: %r" % rv
        finally:
            wnd.komodo.close_handle(running)           

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
        lock = wnd.komodo.create_mutex(_getCommandmentsLockName(ver))
        wnd.komodo.wait_for_single_object(lock)

        # Append the new commandments.
        f = open(_getCommandmentsFileName(ver), 'a')
        for commandment in commandments:
            f.write(commandment)
        f.close()
        
        # Signal Komodo that there are new commandments.
        newCommandments = wnd.komodo.create_event(_getCommandmentsEventName(ver))
        wnd.komodo.set_event(newCommandments)
        wnd.komodo.close_handle(newCommandments)
        
        # Release the lock.
        wnd.komodo.release_mutex(lock)
        wnd.komodo.close_handle(lock)
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


