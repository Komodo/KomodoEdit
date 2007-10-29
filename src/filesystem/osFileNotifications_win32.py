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

# Watches for file changes through the Windows operating system.
# Uses win32 API's to monitor paths and wait for file change notifications.
# Notifications of changes get sent through the observer service.
#
# Contributors:
# * Todd Whiteman

import os
import sys
import stat
import time
import threading
import logging
import wnd
import ctypes
import koWndWrapper  # Komodo's wrapper for wnd

from koWndWrapper.notify import *
from koWndWrapper.consts import win32con
from koWndWrapper.consts import ntsecuritycon

# Import the common definitions and utility functions
from osFileNotificationUtils import *

log = logging.getLogger("osFileNotifications_win32")
#log.setLevel(logging.DEBUG)

# How often this polling service checks for changes (in seconds)
POLL_PERIOD = 2.0
POLL_PERIOD_MILLISECONDS = int(POLL_PERIOD * 1000)

# We don't know if it is a file or directory, but we know the basic action
WINPATH_CREATED       = 1
WINPATH_DELETED       = 2
WINPATH_MODIFIED      = 3
WINPATH_MOVED_DELETED = 4
WINPATH_MOVED_CREATED = 5
ACTIONS = {
    WINPATH_CREATED       : "Created",
    WINPATH_DELETED       : "Deleted",
    WINPATH_MODIFIED      : "Updated",
    WINPATH_MOVED_DELETED : "Renamed to something",
    WINPATH_MOVED_CREATED : "Renamed from something"
}

#
# Exceptions used internally
#
class NotSupportedException(Exception):
    pass

class Win32Error(Exception):
    pass

class DummyLock:
    def acquire(self):
        pass
    def release(self):
        pass

# Windows directory watcher object
class DirectoryWatcher(object):

    # What we look for in directory changes
    __flags = win32con.FILE_NOTIFY_CHANGE_FILE_NAME | \
                win32con.FILE_NOTIFY_CHANGE_DIR_NAME | \
                win32con.FILE_NOTIFY_CHANGE_ATTRIBUTES | \
                win32con.FILE_NOTIFY_CHANGE_LAST_WRITE | \
                win32con.FILE_NOTIFY_CHANGE_SECURITY
                #win32con.FILE_NOTIFY_CHANGE_SIZE | \

    def __init__(self, directoryname, recursive=False):
        log.debug("Creating DirectoryWatcher for '%s'", directoryname)
        self.__dirname = directoryname
        self.__recursive = recursive
        self.__observerMonitors = []
        self.__statCache = {}
        self.__lock = threading.Lock()
        #self.__lock = DummyLock()
        # win32 variables
        self.__handle = None
        self.__needs_full_reset = False
        self.__needs_samba_reset = False
        self.__new_event_was_created = False
        self.__initWin32Objects()

    def __del__(self):
        log.debug("Deleting watcher for: %s", self.__dirname)
        if self.__handle:
            #print "Closed the handle"
            koWndWrapper.close_handle(self.__handle)

    def __str__(self):
        return "  DirectoryWatcher('%s', r:%r) observers:\n    %s\n" % (
                        self.__dirname,
                        self.__recursive,
                        '\n    '.join([ str(x) for x in self.__observerMonitors[:] ]))

    #def __repr__(self):
    #    return str(self)

    def __len__(self):
        return len(self.__observerMonitors)

    def getdirname(self):
        return self.__dirname
    dirname = property(getdirname, doc="Return the directory name we are watching")

    def getoverlappedObj(self):
        return self.__overlapped_obj
    overlappedObj = property(getoverlappedObj, doc="Return the PyOVERLAPPED object of the file handle")

    def __initWin32Objects(self):
        log.info("Initializing win32 objects for path: %s", self.dirname)
        if self.__handle:
            koWndWrapper.close_handle(self.__handle)
        self.__handle = koWndWrapper.CreateFile (
                                self.__dirname,
                                ntsecuritycon.FILE_LIST_DIRECTORY,
                                  # Allow other process to read this folder
                                win32con.FILE_SHARE_READ |
                                  # Allow other process to write to this folder
                                  win32con.FILE_SHARE_WRITE |
                                  # Allow other process to delete this folder
                                  win32con.FILE_SHARE_DELETE,
                                None, # security desc
                                win32con.OPEN_EXISTING,
                                win32con.FILE_FLAG_BACKUP_SEMANTICS |
                                  win32con.FILE_FLAG_OVERLAPPED,
                                None)
        self.__readBuffer_size = 8192
        self.__readBuffer = create_unicode_buffer(self.__readBuffer_size / 2) # (c_byte * self.__readBuffer_size)()
        self.__overlapped_obj = OVERLAPPED()
        self.__overlapped_obj.hEvent = koWndWrapper.create_event(None, None, 0)
        self.__needs_full_reset = False
        self.__new_event_was_created = True

    def __initCacheForDirectory(self, path):
        # Initialize the cache we know about
        try:
            for filename in os.listdir(path):
                fullpath = path + os.sep + filename
                self.__initCacheForPath(fullpath, checkContents=self.__recursive)
        except OSError:
            # Directory does not exist now
            pass

    def __initCacheForPath(self, path, checkContents=True):
        # Initialize the cache we know about
        try:
            st = os.stat(path)
            fileStat = FileStat(st)
            self.__statCache[path] = fileStat
        except OSError:
            return
        if checkContents and fileStat.isDir():
            self.__initCacheForDirectory(path)

    # Note: Already acquired self.__lock
    def __reset(self):
        """Notify the OS we want to watch this directory
        Note: When the watched directory has changes and notifies us, the
              ReadDirectoryChangesW() setting will automatically be removed, as
              it works as a one-shot setting.
        """
        #
        # ReadDirectoryChangesW takes a previously-created
        #  handle to a directory, a buffer size for results,
        #  a flag to indicate whether to watch subtrees and
        #  a filter of what changes to notify.
        #
        # NB Tim Juchcinski reports that he needed to up
        #  the buffer size to be sure of picking up all
        #  events when a large number of files were
        #  deleted at once.
        #
        log.debug("Resetting %s", self)
        try:
            #print "self.__overlapped_obj:", self.__overlapped_obj
            ReadDirectoryChangesW(self.__handle,
                                  self.__readBuffer,
                                  self.__readBuffer_size,
                                  self.__recursive,  # Watch recursively
                                  self.__flags,
                                  self.__overlapped_obj,
                                  None)
            return 0
        except WindowsError, e:
            log.debug("__reset:: WindowsError: %s", e)
            if e.args[0] == 59: # An unexpected network error occurred
                self.__needs_samba_reset = True
                return 0    # will send FS_UNKNOWN later
            return self.__notifyWatchedPathWasDeleted()
        except ValueError, e:
            if str(e) == "overlapped and overlappedRoutine must be None":
                raise NotSupportedException("OS Notifications not supported. Update the pywin32 package to version >= 209")
            else:
                raise e

    # Notify all observers that this path was deleted
    # All observers will be automatically removed.
    # Note: Already acquired self.__lock
    def __notifyWatchedPathWasDeleted(self):
        # Special case where the watched path was deleted
        pos_count = 1
        for observerMonitor in self.__observerMonitors:
            log.debug("Sending delete notifications to observer %d", pos_count)
            observerMonitor.notifyOwnPathDeleted()
            pos_count += 1
        self.__observerMonitors = []
        return FS_DIR_DELETED

    # Ensure the win32file.ReadDirectoryChangesW() is using the correct
    # recursive watch setting. Returns true when the setting has changed.
    # Note: Already acquired self.__lock
    def __resetRecursiveSetting(self):
        wasRecursive = self.__recursive
        for observerMonitor in self.__observerMonitors:
            if observerMonitor.isRecursive():
                self.__recursive = True
                break
        else:
            self.__recursive = False
        # Changed recursive setting. We need to reset the win32 api call.
        if wasRecursive != self.__recursive:
            log.debug("__resetRecursiveSetting: changed recursive to: %r", self.__recursive)
            self.__needs_full_reset = True

    # Note: Already acquired self.__lock
    def __removeObservedPathFromWatchList(self, observer, path):
        """Remove this file from the monitored file list"""
        for i in range(len(self.__observerMonitors)):
            observerMonitor = self.__observerMonitors[i]
            if observerMonitor.getAliveObserver() == observer and \
               observerMonitor.path == path:
                self.__observerMonitors.pop(i)
                break

    #def isWatchingFile(self, filename):
    #    """Return true/false if this watcher is monitoring this file"""
    #    #print "Watching file '%s'" % (filename)
    #    return self.__watching_files.has_key(filename)

    # See if a new event has been created, need to update the watcher list if
    # this occurs.
    # Note: Automatically resets itself to false through __initWin32Objects()
    def newEventWasCreated(self):
        if self.__new_event_was_created:
            self.__lock.acquire()
            try:
                self.__new_event_was_created = False
                self.__reset()
            finally:
                self.__lock.release()
            return True
        return False

    def validateDirectoryWatcher(self):
        """Return true/false if the watcher is still working correctly
        Note: When the watched directory has been deleted, this will return false.
        """
        self.__lock.acquire()
        try:
            if self.__needs_full_reset:
                log.debug("validateDirectoryWatcher: Needs a full reset")
                self.__initWin32Objects()
                if self.__reset() == FS_DIR_DELETED:
                    return False
            elif self.__needs_samba_reset:
                # This is a samba share, it has problems telling us what has
                # happened in the filesystem.
                # http://bugs.activestate.com/show_bug.cgi?id=57698
                # We raise a FS_UNKNOWN, and let the observer deal with it
                log.debug("validateDirectoryWatcher: Reset due to samba file change")
                self.__needs_samba_reset = False
                for observerMonitor in self.__observerMonitors:
                    observerMonitor.notifyChanges({observerMonitor.path:FS_UNKNOWN})
                if self.__reset() == FS_DIR_DELETED:
                    return False
            observerWasRemoved = False

            # Remove any observers that do not exist (they are weakreferences)
            for i in range(len(self.__observerMonitors) -1, -1, -1):
                observerMonitor = self.__observerMonitors[i]
                if observerMonitor.hasExpired() or \
                   not observerMonitor.getAliveObserver():
                    self.__observerMonitors.pop(i)
                    observerWasRemoved = True
                else:
                    # Ensure path still exists
                    try:
                        st = os.stat(observerMonitor.path)
                    except OSError:
                        observerMonitor.notifyOwnPathDeleted()
                        self.__observerMonitors.pop(i)

            # Check to make sure there are observers
            if len(self.__observerMonitors) == 0:
                return False
            # Reset recursive setting if an observer was removed
            if observerWasRemoved:
                self.__resetRecursiveSetting()
            return True
        finally:
            self.__lock.release()

    def addObservedPathToWatchList(self, observer, path, watch_type, flags):
        """Add this file to the monitored file list"""
        log.debug("addObservedPathToWatchList: watch_type:%d, flags:%x, path:'%s'", watch_type, flags, path)
        self.__lock.acquire()
        try:
            self.__removeObservedPathFromWatchList(observer, path)
            self.__observerMonitors.append( ObserverMonitior( observer, path, watch_type, flags, log) )
            self.__resetRecursiveSetting()
            #if len(self.__observerMonitors) == 1:
            #    # First observer added, make sure win32 objects get initialized
            #    self.__needs_full_reset = True
            self.__initCacheForPath(self.dirname, checkContents=True)
        finally:
            self.__lock.release()

    def removeObservedPathFromWatchList(self, observer, path):
        """Remove this file from the monitored file list"""
        log.debug("removeObservedPathFromWatchList: path:'%s'", path)
        self.__lock.acquire()
        try:
            self.__removeObservedPathFromWatchList(observer, path)
            self.__resetRecursiveSetting()
        finally:
            self.__lock.release()

    # Get the status and changes for this monitored path
    # Returns a tuple ( integer, dict )
    #   The dict contains key:path of change, value:type of change
    def getChanges(self):
        """Get the change notifications for monitored path."""
        changes = {}
        try:
            nbytes = GetOverlappedResult(self.__handle, self.__overlapped_obj, True)
        except WindowsError, e:
            # Check the error code
            log.debug("getChanges:: WindowsError: %s", e)
            if e.args[0] == 59: # An unexpected network error occurred
                # Typically this happens on a samba share, see bug:
                # http://bugs.activestate.com/show_bug.cgi?id=50838
                self.__needs_samba_reset = True
                return ( 0, changes )
            # 'Access is denied.' - Results from path getting deleted.
            self.__notifyWatchedPathWasDeleted()
            return ( FS_DIR_DELETED, changes )
        if nbytes:
            bits = getFILE_NOTIFY_INFORMATION(self.__readBuffer, nbytes)
            # Make sure we keep listening for file changes
            self.__lock.acquire()
            try:
                if self.__reset() == FS_DIR_DELETED:
                    return ( FS_DIR_DELETED, changes )
            finally:
                self.__lock.release()
            # WINPATH_CREATED       = 1
            # WINPATH_DELETED       = 2
            # WINPATH_MODIFIED      = 3
            # WINPATH_MOVED_DELETED = 4
            # WINPATH_MOVED_CREATED = 5
            watcherPathDeleted = False
            for action, filename in bits:
                change = 0
                path = os.path.join(self.__dirname, filename)
                log.debug("action:%s, path:%s", action, path)
                if action == WINPATH_DELETED or action == WINPATH_MOVED_DELETED:
                    oldFileStat = self.__statCache.get(path)
                    # We can't get the current stat of this file (deleted)
                    if oldFileStat:
                        # We know what it used to be, that is enough
                        if oldFileStat.isDir():
                            change = FS_DIR_DELETED
                            # Check if our watcher path is the one gone
                            if path == self.dirname:
                                watcherPathDeleted = True
                                # Any other change no longer matters
                                break
                        elif oldFileStat.isFile():
                            change = FS_FILE_DELETED
                    else:
                        # We guess then
                        log.debug("Couldn't find oldFileStat for path: '%s'", path)
                        change = FS_FILE_DELETED
                else:
                    try:
                        st = os.stat(path)
                        fileStat = FileStat(st)
                        self.__statCache[path] = fileStat
                    except OSError:
                        # Does not exist, try old info then
                        fileStat = self.__statCache.get(path)
                    if fileStat:
                        if action == WINPATH_MODIFIED:
                            if fileStat.isDir():
                                change = FS_DIR_MODIFIED
                            elif fileStat.isFile():
                                change = FS_FILE_MODIFIED
                        else: # action == WINPATH_CREATED or action == WINPATH_MOVED_CREATED
                            if fileStat.isDir():
                                change = FS_DIR_CREATED
                                #print "Dir created: ", path
                                #if self.__recursive:
                                #    # check the contents of this path
                                #    self.__initCacheForDirectory(path)
                            elif fileStat.isFile():
                                change = FS_FILE_CREATED
                if change:
                    #if action == WINPATH_MOVED_CREATED:
                    #    print "WINPATH_MOVED_CREATED, change: %x for path: %s" % (change, path)
                    log.debug("change:%x, path:%s", change, path)
                    changes[path] = changes.get(path, 0) | change
                    #print "Change is %x" % (changes.get(path, 0))
                    parentDir = os.path.dirname(path)
                    changes[parentDir] = changes.get(parentDir, 0) | FS_DIR_MODIFIED

            # Special case where the watched path was deleted
            if watcherPathDeleted:
                self.__lock.acquire()
                try:
                    self.__notifyWatchedPathWasDeleted()
                    return ( FS_DIR_DELETED, {} )
                finally:
                    self.__lock.release()

        return (0, changes)

    # Send change notifications to all the observers
    def notifyChanges(self, changes):
        self.__lock.acquire()
        try:
            doReset = False
            # Loop backwards, so we can delete and still use our i variable
            for i in range(len(self.__observerMonitors) -1, -1, -1):
                log.debug("Sending change notifications to observer %d", i+1)
                observerMonitor = self.__observerMonitors[i]
                doRemoveObserver = observerMonitor.notifyChanges(changes)
                if doRemoveObserver:
                    log.debug("Observer deleted, for path: %s", observerMonitor.path)
                    self.__observerMonitors.pop(i)
                    doReset = True
            if doReset:
                self.__resetRecursiveSetting()
        finally:
            self.__lock.release()

    #def getAndNotifyChanges(self):
    #    """Send change notifications to the observers watching this location."""
    #    changes = {}
    #    nbytes = win32file.GetOverlappedResult(self.__handle, self.__overlapped_obj, True)
    #    if nbytes:
    #        bits = win32file.FILE_NOTIFY_INFORMATION(self.__readBuffer_obj, nbytes)
    #        # Make sure we keep listening for file changes
    #        self.__lock.acquire()
    #        try:
    #            if self.__reset() == FS_DIR_DELETED:
    #                return FS_DIR_DELETED
    #        finally:
    #            self.__lock.release()
    #        # WINPATH_CREATED       = 1
    #        # WINPATH_DELETED       = 2
    #        # WINPATH_MODIFIED      = 3
    #        # WINPATH_MOVED_DELETED = 4
    #        # WINPATH_MOVED_CREATED = 5
    #        watcherPathDeleted = False
    #        for action, filename in bits:
    #            change = 0
    #            path = os.path.join (self.__dirname, filename)
    #            log.debug("action:%s, path:%s", action, path)
    #            if action == WINPATH_DELETED or action == WINPATH_MOVED_DELETED:
    #                oldFileStat = self.__statCache.get(path)
    #                # We can't get the current stat of this file (deleted)
    #                if oldFileStat:
    #                    # We know what it used to be, that is enough
    #                    if oldFileStat.isDir():
    #                        change = FS_DIR_DELETED
    #                        # Check if our watcher path is the one gone
    #                        if path == self.dirname:
    #                            watcherPathDeleted = True
    #                            # Any other change no longer matters
    #                            break
    #                    elif oldFileStat.isFile():
    #                        change = FS_FILE_DELETED
    #                else:
    #                    # We guess then
    #                    log.debug("Couldn't find oldFileStat for path: '%s'", path)
    #                    change = FS_FILE_DELETED
    #            else:
    #                try:
    #                    st = os.stat(path)
    #                    fileStat = FileStat(st)
    #                    self.__statCache[path] = fileStat
    #                except OSError:
    #                    # Does not exist, try old info then
    #                    fileStat = self.__statCache.get(path)
    #                if fileStat:
    #                    if action == WINPATH_MODIFIED:
    #                        if fileStat.isDir():
    #                            change = FS_DIR_MODIFIED
    #                        elif fileStat.isFile():
    #                            change = FS_FILE_MODIFIED
    #                    else: # action == WINPATH_CREATED or action == WINPATH_MOVED_CREATED
    #                        if fileStat.isDir():
    #                            change = FS_DIR_CREATED
    #                            #print "Dir created: ", path
    #                            #if self.__recursive:
    #                            #    # check the contents of this path
    #                            #    self.__initCacheForDirectory(path)
    #                        elif fileStat.isFile():
    #                            change = FS_FILE_CREATED
    #            if change:
    #                #if action == WINPATH_MOVED_CREATED:
    #                #    print "WINPATH_MOVED_CREATED, change: %x for path: %s" % (change, path)
    #                log.debug("change:%x, path:%s", change, path)
    #                changes[path] = changes.get(path, 0) | change
    #                #print "Change is %x" % (changes.get(path, 0))
    #                parentDir = os.path.dirname(path)
    #                changes[parentDir] = changes.get(parentDir, 0) | FS_DIR_MODIFIED
    #
    #        # Special case where the watched path was deleted
    #        if watcherPathDeleted:
    #            self.__lock.acquire()
    #            try:
    #                self.__notifyWatchedPathWasDeleted()
    #            finally:
    #                self.__lock.release()
    #
    #        if changes:
    #            # Without removing the observer here
    #            #for observerMonitor in self.__observerMonitors[:]: # copy
    #            #    log.debug("Sending change notifications to observer")
    #            #    observerMonitor.notifyChanges(changes)
    #            # Removing the observer here if no longer valid
    #            self.__lock.acquire()
    #            try:
    #                doReset = False
    #                # Loop backwards, so we can delete and still use our i variable
    #                for i in range(len(self.__observerMonitors) -1, -1, -1):
    #                    log.debug("Sending change notifications to observer %d", i+1)
    #                    observerMonitor = self.__observerMonitors[i]
    #                    doRemoveObserver = observerMonitor.notifyChanges(changes)
    #                    if doRemoveObserver:
    #                        #print
    #                        #print "*" * 80
    #                        #print "Observer deleted, for path: ", observerMonitor.path
    #                        #print "*" * 80
    #                        self.__observerMonitors.pop(i)
    #                        doReset = True
    #                if doReset:
    #                    self.__resetRecursiveSetting()
    #            finally:
    #                self.__lock.release()
    #    else:
    #        # This is "normal" exit - our 'tearDown' closes the
    #        # handle.
    #        # print "looks like dir handle was closed!"
    #        pass
    #    return 0


class WindowsFileWatcher(threading.Thread):
    """Service to watch multiple files for changes on a Windows OS"""
    def __init__(self):
        threading.Thread.__init__(self, name="File Notifications - Windows")
        self.setDaemon(1)   # If Komodo goes down, we go down

        # Locking object for adding / removing the watchers safely
        self.__lock = threading.Lock()

        # file_watchers contains the class objects that do the watching
        #   The dictionary key being the directory name that is being watched
        self.file_watchers = {}
        self.__file_watchers_changed_event = threading.Event()
        self.__finished_checking_event = threading.Event()
        # _watchers_list and _watcher_events_list are used when querying the
        # events for changes, through koWndWrapper.wait_for_multiple_objects()
        self._watchers_list = []
        self._watcher_events_list = []
        self._internal_event = koWndWrapper.create_event("Internal event",
                                                         None, 0)
        # This is the running state of the thread
        self._isRunning = 0
        # This is used for atomic copying of the _watcher_events_list list
        # It will force an update when the main run() loop does it's next run
        self._needsWatcherUpdate = 0


    #def __str__(self):
    #    return "WindowsFileWatcher threaded object"

    #def __repr__(self):
    #    return str(self)

    # Return the number of file_watcher's we have for this thread
    def __len__(self):
        return len(self.file_watchers)

    # Note: Already has acquired the lock
    def _getOrCreateWatcherForDirectory(self, dirname, recursive):
        dirWatcher = None
        try:
            dirWatcher = self.file_watchers[dirname]
        except KeyError:
            # Create a new watcher then
            try:
                dirWatcher = DirectoryWatcher(dirname, recursive)
            except WindowsError, e:
                # Likely that the directory did not exist
                log.warn("WindowsFileWatcher._getOrCreateWatcherForDirectory(): Could not watch the directory: '%s', win32 exception: %s", dirname, e)
                return None
            # Add the new watcher
            self._addDirectoryWatcher(dirname, dirWatcher)
        return dirWatcher

    # Note: Already has acquired self.__lock
    def _addDirectoryWatcher(self, dirname, watcher_object):
        self.file_watchers[dirname] = watcher_object
        self._needsWatcherUpdate = 1    # run loop will update on next run

    # Note: Already has acquired self.__lock
    def _removeDirectoryWatcher(self, dirname):
        # XXX Throw inicator this directory is not watched anymore??
        del self.file_watchers[dirname]
        self._needsWatcherUpdate = 1    # run loop will update on next run

    # Run loop calls this when _needsWatcherUpdate is set, updates the event list
    def _update_watcher_array(self):
        self._watchers_list = self.file_watchers.values()
        self._watcher_events_list = [ w.overlappedObj.hEvent for w in self._watchers_list ]
        self._watcher_events_list.append(self._internal_event)
        self._needsWatcherUpdate = 0

    # An error occured waiting on the event objects, check all watchers to
    # ensure they are still valid
    # Note: Already has acquired self.__lock
    #def _resetWatchers(self):
    #    for dirname, watcher in self.file_watchers.items():
    #        if watcher.resetDirectoryWatcher() == FS_DIR_DELETED:
    #            self._removeDirectoryWatcher(dirname)

    # Validate all the watchers are okay, remove any bad ones
    # Note: Already has acquired self.__lock
    def _validateWatchers(self):
        for dirname, watcher in self.file_watchers.items():
            if watcher.newEventWasCreated():
                # A new event was created, so we need to update the watcher event list
                self._needsWatcherUpdate = 1
            if not watcher.validateDirectoryWatcher():
                #print "WindowsFileWatcher._validateWatchers(): Removing watcher on: %s", watcher.dirname
                log.info("WindowsFileWatcher._validateWatchers(): Removing watcher on: %s", watcher.dirname)
                # XXX - Raise deleted notification ??
                self._removeDirectoryWatcher(dirname)
                self._needsWatcherUpdate = 1

    def _checkFilesystem(self):
        self.__lock.acquire()
        try:
            self._validateWatchers()
            # Atomic rename for our watcher list
            if self._needsWatcherUpdate:
                # We only need do this when an update occured
                self._update_watcher_array()
                if len(self._watchers_list) == 0:
                    return
            # This can be cleared now
            koWndWrapper.reset_event(self._internal_event)
        finally:
            self.__lock.release()

        total_time_used = 0
        # Whilst there are changes happening quickly, we process them here, as
        # there is a high likelyhood other changes to be processed next loop.
        start_time = time.time()
        _watcher_path_changes = {}
        while total_time_used < POLL_PERIOD:
            # Wait for our event, or timeout after x seconds.
            if _watcher_path_changes:
                rc = koWndWrapper.wait_for_multiple_objects(self._watcher_events_list, 0, 50)
            else:
                rc = koWndWrapper.wait_for_multiple_objects(self._watcher_events_list, 0, POLL_PERIOD_MILLISECONDS)
            #log.debug("Received event: %d", rc)
            # rc == 258 when timeout occurs
            if rc < 0 or rc > len(self._watchers_list):
                break
            if rc == len(self._watchers_list):
                # Our special internal event was fired
                # Either we are shutting down or the watchers were updated
                break

            self.__lock.acquire()
            try:
                dir_watcher = self._watchers_list[rc]
                (status, changes) = dir_watcher.getChanges()
                if status == FS_DIR_DELETED:
                    # The monitored path was deleted
                    break
            finally:
                self.__lock.release()
            if changes:
                _watcher_changes = _watcher_path_changes.get(dir_watcher, {})
                for path, change in changes.items():
                    _watcher_changes[path] = _watcher_changes.get(path, 0) | change
                _watcher_path_changes[dir_watcher] = _watcher_changes
                if len(_watcher_changes) > 20:  # 20 changes for this one path
                    break
            total_time_used = time.time() - start_time
        # Send out the batched changes to the observers for the paths modified
        self.__lock.acquire()
        try:
            for watcher_with_changes, changes in _watcher_path_changes.items():
                watcher_with_changes.notifyChanges(changes)
        finally:
            self.__lock.release()

    # Main loop for the Thread, called when the start() method is called.
    def run(self):
        try:
            self._isRunning = 1
            pending_file_changes = {} # File changes that need to be sent to Komodo
            pending_dir_changes = {}  # Dir changes that need to be sent to Komodo
            log.info("WindowsFileWatcher.run(): Now running in a separate thread.")
            self.__file_watchers_changed_event.clear()
            while self._isRunning:
                try:
                    # Wait until we have something to check
                    while len(self.file_watchers) == 0:
                        if not self._isRunning:
                            return
                        self.__file_watchers_changed_event.wait(POLL_PERIOD)
                        self.__file_watchers_changed_event.clear()
                        #log.debug("WindowsFileWatcher.run(): Waiting for watchers...")
                    if not self._isRunning:
                        return
                    # Check the filesystem
                    self.__finished_checking_event.clear()
                    self._checkFilesystem()
                    self.__finished_checking_event.set()
                except Exception, e:
                    log.error("Windows os file notification service runtime exception:")
                    log.exception(e)
        #except Exception, e:
        #    log.exception(e)
        finally:
            log.info("WindowsFileWatcher.run(): Finished Thread run() call")
            # Remove all of our watchers, makes sure no object references are
            # still lying around
            self.clear(updateWatcherArray=True)

    def stop(self):
        log.info("WindowsFileWatcher.stop(): Stopping the thread.")
        self._isRunning = 0
        self.__file_watchers_changed_event.set()
        # Notify our internal event in case we are in WaitForMultipleObjects()
        koWndWrapper.set_event(self._internal_event)

    def addObserverForPath(self, observer, dirname, path, watch_type, flags):
        """Monitor this path for changes
        Return True on success, False on failure.
        """
        self.__lock.acquire()
        try:
            dirWatcher = self._getOrCreateWatcherForDirectory(dirname, watch_type==WATCH_DIR_RECURSIVE)
            if dirWatcher is None: # Use None here as it has a __len__ that may be 0
                return False
    
            dirWatcher.addObservedPathToWatchList(observer, path, watch_type, flags)
            # Make sure main thread knows there is changes
            if self._needsWatcherUpdate:
                self.__file_watchers_changed_event.set()
                koWndWrapper.set_event(self._internal_event)
            return True
        finally:
            self.__lock.release()

    def removeObserverForPath(self, observer, path):
        self.__lock.acquire()
        try:
            dirWatcher = self.file_watchers.get(path)
            if not dirWatcher:
                # Path might be a file, so use parent directory to get the watcher
                dirWatcher = self.file_watchers.get(os.path.dirname(path))
                if not dirWatcher:
                    return  # Nothing watching this path
            dirWatcher.removeObservedPathFromWatchList(observer, path)
            if len(dirWatcher) == 0:
                self._removeDirectoryWatcher(dirWatcher.dirname)
            # Make sure main thread knows there is changes
            if self._needsWatcherUpdate:
                self.__file_watchers_changed_event.set()
                koWndWrapper.set_event(self._internal_event)
        finally:
            self.__lock.release()

    def isWatchingDirectory(self, dirname):
        return self.file_watchers.has_key(dirname)

    # Clear all the working variables and objects used by this class
    def clear(self, updateWatcherArray=False):
        self.__lock.acquire()
        try:
            self.file_watchers = {}
            if updateWatcherArray:
                self._update_watcher_array()
            else:
                # The watcher_array_list will be updated on next run() loop
                self._needsWatcherUpdate = 1
                self.__file_watchers_changed_event.set()
                koWndWrapper.set_event(self._internal_event)
        finally:
            self.__lock.release()

    # Log some diagnostic information on the watchers
    def dump(self):
        for dirname, watcher in self.file_watchers.items():
            log.debug("WindowsFileWatcher.dump()\n  File Watchers\n%s", "".join( [ str(w) for w in self.file_watchers.values() ] ))   # Use watcher's str and/or repr methods

    def waitTillFinishedRun(self):
        self.__finished_checking_event.wait()


class WindowsFileWatcherService:
    """Service to watch multiple files for changes on a Windows OS"""

    # This is how many watchers we can have per thread. This is due to the
    # WaitForMultipleObjects() call only allowing this many objects to be
    # passed to it (for most machines this is the value 64).
    #_max_watchers_per_thread = win32event.MAXIMUM_WAIT_OBJECTS
    # We subtract one as we use one event for special internal purposes
    _max_watchers_per_thread = koWndWrapper.MAXIMUM_WAIT_OBJECTS - 1

    def __init__(self):
        # Make sure it's available on this machine
        # See if this Windows machine supports the ReadDirectoryChangesW call
        # and that pywin32 extensions support passing of an overlapped object.
        # Only available on WinNT platforms (Windows NT/2000/XP)
        self.available = sys.getwindowsversion()[3] == 2
        if self.available:
            # Check that it works then by creating a new watcher and testing it
            try:
                dirWatcher = DirectoryWatcher(os.curdir, recursive=False)
            except NotSupportedException, e:
                log.warn("WindowsFileWatcherService.__init__(): OS File Notifications are not available in this OS")
                log.warn("WindowsFileWatcherService.__init__(): %s", e)
                self.available = 0

        # _watchers contains the class objects that do the watching
        # We can only watch up to 128 directories per watcher, so we have this
        # list of watchers to be able to monitor more.
        self._watchers = []
        self._isRunning = 0
        self._lock = threading.Lock()

    def _getWatcher(self, dirname):
        # Check if any existing watchers are already monitoring this directory
        wfw = None
        for wfw in self._watchers:
            if wfw.isWatchingDirectory(dirname):
                break
        else:
            # Add a new watcher then, check which thread to add it to
            for wfw in self._watchers:
                if len(wfw) < self._max_watchers_per_thread:
                    break
            else:   # we have to make a new WindowsFileWatcher thread
                wfw = WindowsFileWatcher()
                wfw.start() # It's a thread object, so start it running
                self._watchers.append(wfw)
        # We have a valid wfw now
        return wfw

    def startNotificationService(self):
        """Start the OS file notification service for Windows"""
        if self.available:
            self._lock.acquire()
            try:
                log.info("WindowsFileWatcherService.startNotificationService(): Starting the service")
                if len(self._watchers) == 0:
                    # Create the first file watcher object
                    wfw = WindowsFileWatcher()
                    wfw.start() # It's a thread object, so start it running
                    self._watchers.append(wfw)
                else:
                    for wfw in self._watchers:
                        wfw._isRunning = 1
            finally:
                self._lock.release()

        #else:
        #    raise "Not supported on this platform!"

    def stopNotificationService(self):
        """Stop the OS file notification service for Windows"""
        log.info("WindowsFileWatcherService.stopNotificationService(): Stopping the notification service thread.")
        self._lock.acquire()
        try:
            self._isRunning = 0
            for wfw in self._watchers:
                wfw.stop()
        finally:
            self._lock.release()

    def addObserver(self, observer, path, watch_type, flags):
        """Monitor this file for changes
        Return True on success, False on failure.
        """
        log.debug("WindowsFileWatcherService.addObserver(): path: '%s'", path)
        # XXX - Do we need to add absolute path, or it should already be there?
        if watch_type == WATCH_FILE:
            dirname = os.path.dirname(path)
        else:
            dirname = path

        # XXX - Removed, will do this another way. Send back FS_UNKNOWN, let the
        #       observers deal with the problem.
        ## Does not work with Samba and remote shares (it should poll)
        #dirnameWithSlash = dirname
        ## win32file.GetDriveType() requires the directory path have a trailing
        ## backslash... blah!
        #if not dirnameWithSlash.endswith(os.sep):
        #    dirnameWithSlash += os.sep
        ##print "Path (%d): %r" % (win32file.GetDriveType(dirnameWithSlash),
        ##                          dirnameWithSlash)
        #if win32file.GetDriveType(dirnameWithSlash) == win32con.DRIVE_REMOTE:
        #    # Some type of remote filesystem, I.e. Samba, not supported
        #    return 0

        self._lock.acquire()
        try:
            wfw = self._getWatcher(dirname)
            return wfw.addObserverForPath(observer, dirname, path, watch_type, flags)
        finally:
            self._lock.release()
            log.debug("Number of observers now: %d", self.number_of_observed_locations)

    def removeObserver(self, observer, path):
        """Remove the monitor on this path"""
        self._lock.acquire()
        try:
            log.debug("WindowsFileWatcherService.removeObserver(): path: '%s'", path)
            # Not sure if this is a file or a directory, so let watchers decide that
            for wfw in self._watchers:
                if wfw.removeObserverForPath(observer, path):
                    break
        finally:
            self._lock.release()
            log.debug("Number of observers now: %d", self.number_of_observed_locations)


    #
    # These class methods below are purely for test purposes
    #
    def dump(self):
        self._lock.acquire()
        try:
            for wfw in self._watchers:
                wfw.dump()
        finally:
            self._lock.release()

    def clear(self):
        self._lock.acquire()
        try:
            for wfw in self._watchers:
                wfw.clear()
        finally:
            self._lock.release()

    def _get_number_of_watchers(self):
        count = 0
        for wfw in self._watchers:
            count += len(wfw)
        return count
    number_of_observed_locations = property(_get_number_of_watchers, doc="Return the number of directories that are watched.")

    def get_watcher_for_directory(self, dirname):
        for wfw in self._watchers:
            if wfw.isWatchingDirectory(dirname):
                return wfw
        return None

    def waitTillFinishedRun(self):
        time.sleep(0.2)
        #for wfw in self._watchers:
        #    wfw.waitTillFinishedRun()
