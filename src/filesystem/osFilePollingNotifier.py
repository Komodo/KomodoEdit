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
#
# Contributors:
# * Todd Whiteman

"""osFilePollingNotifier - Used to watch a file system and poll for file
changes to which notifications will be sent. The polling notifier is a threaded
class that performs a file check every X (DEFAULT_POLL_PERIOD) seconds.
"""

#import os
from os import listdir as os_listdir
from os import sep as os_sep
from os import stat as os_stat
from os import lstat as os_lstat
from os.path import realpath as os_path_realpath
from stat import S_ISLNK, S_IFLNK
import time
import threading
import logging
#import dircache

log = logging.getLogger("osFilePollingNotifier")
#log.setLevel(logging.INFO)
from osFileNotificationUtils import *

# Default for how often this polling service checks for changes (in seconds)
# Can be overridden when creating the osFilePollingNotifier object.
DEFAULT_POLL_PERIOD = 3.0

# _checkDirectoryForChanges
#   oldStatCache:      dict    - previous stats, key:path, value:FileStat object
#   statCache:         dict    - current stats, key:path, value:FileStat object
#   oldDirCache:       dict    - previous os.listdir(), key:path, value:list
#   dirCache:          dict    - current os.listdir(), key:path, value:list
#   checked_locations: dict    - paths already checked, key:path, value:changes
#   realpath:          string  - real absolute path of directory to check
#   directory:         string  - absolute path of directory to check
#   recursive:         bool    - Check recursively
#   depth:             int     - How many directory levels have been checked
#   linked_paths:      dict    - Symlinks, key:path, value:list of links to here
#   dirModifiedSet:    bool    - if FS_DIR_MODIFIED was already set
def _checkDirectoryForChanges(oldStatCache, statCache, oldDirCache, dirCache,
                              checked_locations, realpath, directory, recursive,
                              depth, linked_paths, dirModifiedSet=False):
    #print "_checkDirectoryForChanges: %s" % (directory)
    #print "dirModifiedSet: %r" % (dirModifiedSet)
    changes = {}
    modified = False

    old_paths = oldDirCache.get(realpath, []) # Contents info
    # Use the cached values (i.e. if we've already checked this path this run)
    current_paths = dirCache.get(realpath)
    if not current_paths:
        try:
            # Note: dircache does not notice new or deleted files! Use os.listdir
            #current_paths = dircache.listdir(directory) # The current file/dir paths
            current_paths = os_listdir(realpath) # The current file/dir paths
            dirCache[realpath] = current_paths
        except OSError:
            current_paths = []
    #print "old_paths:", old_paths
    #print "current_paths:", current_paths
    # XXX - Filter current_paths... not for first draft
    old_set       = set(old_paths)
    current_set   = set(current_paths)

    # Ensure we have full paths for these sets
    sep = os_sep
    paths_to_check = [ directory + sep + x for x in current_set.union(old_set) ]
    for path in paths_to_check:
        dir_changes = _checkPathForChanges(oldStatCache, statCache, oldDirCache,
                                           dirCache, checked_locations, path,
                                           recursive, depth, linked_paths)
        for changedpath, change in dir_changes.items():
            changes[changedpath] = changes.get(changedpath, 0) | change

    # The directory itself or one/more files inside the directory have changed
    # dirModifiedSet when True means this was already set previously
    if changes and not dirModifiedSet:
        # Removed for now, we should still send this
        ## We don't send a modified only the directory was modified.
        #for change in changes.values():
        #    if (change - FS_DIR_MODIFIED) > 0:
        #        changes[directory] = changes.get(directory, 0) | FS_DIR_MODIFIED
        #        break
        changes[directory] = changes.get(directory, 0) | FS_DIR_MODIFIED
    return changes

# _checkPathForChanges
#   oldStatCache:      dict    - previous stats, key:path, value:FileStat object
#   statCache:         dict    - current stats, key:path, value:FileStat object
#   oldDirCache:       dict    - previous os.listdir(), key:path, value:list
#   dirCache:          dict    - current os.listdir(), key:path, value:list
#   checked_locations: dict    - paths already checked, key:path, value:changes
#   path:              string  - absolute path to check
#   recursive:         bool    - Check recursively
#   depth:             int     - How many directory levels have been checked
#   linked_paths:      dict    - Symlinks, key:path, value:list of links to here
# Returns a dictionary of paths that have changed. Key of dict is the change type.
# If path is a directory, will check the directory contents as well.
def _checkPathForChanges(oldStatCache, statCache, oldDirCache, dirCache,
                         checked_locations, path, recursive, depth=0,
                         linked_paths=None):
    #print "_checkPathForChanges: %s" % (path)
    # We use realpath to ensure we don't do a second stat or listdir for the same
    # path.
    changes = {}
    modified = False
    oldFileStat = None
    try:
        try:
            lstat = os_lstat(path)
        except Exception, e:
            log.debug("polling _checkPathForChanges unable to lstat [%r] - %s",
                      path, e)
            raise

        #if S_ISLNK(lstat.st_mode):
        if (lstat.st_mode & 0170000) == S_IFLNK:    # Taken from stat module
            realpath = os_path_realpath(path)
            # linked_paths is used to ensure we don't go in a cyclic loop for symlinks
            if not linked_paths:
                linked_paths = {}
            if path != realpath:
                # It's a link
                #log.debug("Link: %s to %s", path, realpath)
                all_links_here = linked_paths.get(realpath, [])
                # We do not support cyclical paths, check if any have been found
                for linkpath in all_links_here:
                    if len(path) >= len(linkpath):
                        largerpath = path
                        smallerpath = linkpath
                    else:
                        largerpath = linkpath
                        smallerpath = path
                    if largerpath.find(smallerpath) == 0:
                        #print "Found cyclical path: %s to %s" % (path, realpath)
                        #log.info("Found cyclical symlink path: %s to %s", path, realpath)
                        return { }
                # It's okay, but we add this link to the known symlink list
                all_links_here.append(path)
                linked_paths[realpath] = all_links_here
            st = os_stat(path)
        else:
            realpath = path
            st = lstat

    except OSError:
        # Does not exist now
        #log.debug("Path deleted: %s", path)
        #print "Path deleted: %s" % (path)
        change = 0
        oldFileStat = oldStatCache.get(path) # Stat info
        if oldFileStat:
            # But it existed before, so it's gone, send the notification
            if oldFileStat.isDir():
                change = FS_DIR_DELETED
            elif oldFileStat.isFile():
                change = FS_FILE_DELETED
        #else:
            # It has never existed and still does not exist, no change
        # Make sure we record the changes made
        checked_locations[path] = change
        if change:
            changes[path] = change
            #statCache.pop(path)
        # Done, cannot check any further as nothing here exists
        return changes

    # We don't have to do any stat information if we've already checked this
    # path, we use the already stated info instead. So we check that first.
    changed = checked_locations.get(path, None)
    if changed is not None:
        if changed > 0:
            changes[path] = changed
            # We don't need to check any further if it's been deleted
            if changed & (FS_DIR_DELETED | FS_FILE_DELETED):
                return changes
        currentFileStat = statCache.get(path) # Stat info
        if not currentFileStat:
            return {}
    else:
        # We have to check it now
        oldFileStat = oldStatCache.get(path) # Stat info
        if oldFileStat is None:
            currentFileStat = FileStat(st)
            # It didn't exist before, but it does now, it's been created
            if currentFileStat.isDir():
                changes[path] = FS_DIR_CREATED
            elif currentFileStat.isFile():
                changes[path] = FS_FILE_CREATED
        elif oldFileStat != st:     # Uses FileStat.__neq__() call
            currentFileStat = FileStat(st)
            if oldFileStat.isDir() and currentFileStat.isDir():
                changes[path] = FS_DIR_MODIFIED
            elif oldFileStat.isFile() and currentFileStat.isFile():
                changes[path] = FS_FILE_MODIFIED
            # XXX - Case where changed from file to a dir?
            # XXX - Or to something else entirely?
            #elif oldFileStat.isFile() and currentFileStat.isDir():
            #    change = FS_FILE_DELETED
            #else:   # It's something else now, that means deleted to me
            #    change = FS_FILE_MODIFIED
            modified = True
        else:
            # They are the same
            currentFileStat = oldFileStat

        statCache[path] = currentFileStat
        # Make sure we record the changes made
        # XXX - Do we need to look this up again??
        checked_locations[path] = changes.get(path, 0)

    # Recurse through directories
    if currentFileStat.isDir() and (recursive or depth < 1):
        # We don't need to check sub-contents for something that used to be a file
        #(not oldFileStat or oldFileStat.isDir()):

        # We need to check contents and possibly sub-directories too
        dir_changes = _checkDirectoryForChanges(oldStatCache, statCache,
                                                oldDirCache, dirCache,
                                                checked_locations,
                                                realpath, path,
                                                recursive, depth + 1,
                                                linked_paths,
                                                dirModifiedSet=modified)
        #for path, change in dir_changes.items():
        #    print "*" * 20
        #    print "Dir change: %x (existing: %x) for path: %s" % (change, changes.get(path, 0), path)
        #    print "*" * 20
        #    changes[path] = changes.get(path, 0) | change
        dir_changes.update(changes)
        changes = dir_changes
    return changes


class _MonitoredPath:
    def __init__(self, path):
        self.path = path
        self.__watch_type = 0
        self.__recursive = False
        self.__observer_monitors = [ ]
        self.__observer_lock = threading.Lock()
        # If any of the observers require recursion, it will be set through
        # self.addObserver()

    ##
    ## Internal functions
    ##

    def __len__(self):
        return len(self.__observer_monitors)

    def __str__(self):
        msgs = [ "Monitored path: %s" % (self.path) ]
        for observerMonitor in self.__observer_monitors[:]: # copy (we're not locked)
            msgs.append("  Type: %d, flags: %x, recursive: %r" % (watch_type, flags, recursive))
        #log.debug('\n'.join(msgs))

    # Add the observerMonitor
    # Note: Already has a lock on self.__observer_monitors
    def __addObserverMonitor(self, observerMonitor):
        if observerMonitor.isRecursive():
            self.__recursive = True
        self.__watch_type = observerMonitor.watch_type
        self.__observer_monitors.append(observerMonitor)

    # Remove the observerMonitor
    # Note: Already has a lock on self.__observer_monitors
    def __removeObserverMonitor(self, observerMonitor):
        for i in range(len(self.__observer_monitors)):
            if observerMonitor == self.__observer_monitors[i]:
                self.__observer_monitors.pop(i)
                break
        # Update own recursive variable accordingly
        if self.isRecursive() and observerMonitor.isRecursive():
            # Need to update our own internal recusive state, it may have changed
            for observerMonitor in self.__observer_monitors:
                if observerMonitor.isRecursive():
                    self.__recursive = True
                    break
            else:
                self.__recursive = False

    ##
    ## Called only from own main monitoring thread
    ##

    # Unused
    #def monitorsLocation(self, path):
    #    # XXX - Better approach needed ..., but what?
    #    #log.debug("monitorsLocation: own path:     %s", self.path)
    #    #log.debug("monitorsLocation: checked path: %s", path)
    #    return (path == self.path or
    #        (self.isRecursive() and path.find(self.path) == 0))

    def initializeNewObservers(self):
        for observerMonitor in self.__observer_monitors[:]: # copy (we're not locked)
            if observerMonitor.justCreated():
                observerMonitor.setReadyForFirstCheck()

    def checkForChanges(self, oldStatCache, statCache, oldDirCache, dirCache,
                        checked_locations):
        changesForPath = None
        for observerMonitor in self.__observer_monitors[:]: # Copy, as we delete
            changes = None
            if not observerMonitor.isReady():
                continue
            if observerMonitor.mustCheckAgainstOwnCache():
                # Use observer's own cache to check against
                #log.debug("checkForChanges: using own cache: recursive: %r",
                #          observerMonitor.isRecursive())
                changes = _checkPathForChanges(observerMonitor.getStatCache(),
                                               statCache,
                                               observerMonitor.getDirCache(),
                                               dirCache,
                                               {},
                                               self.path,
                                               observerMonitor.isRecursive(),
                                               depth=0)
                # Own cache not needed anymore
                observerMonitor.clearOwnCache()
            else:
                #log.debug("checkForChanges: using global cache: recursive: %r",
                #          self.isRecursive())
                if changesForPath is None:
                    # we need to check if there are any changes here
                    changesForPath = _checkPathForChanges(oldStatCache,
                                                          statCache,
                                                          oldDirCache,
                                                          dirCache,
                                                          checked_locations,
                                                          self.path,
                                                          self.isRecursive(),
                                                          depth=0)
                changes = changesForPath
            if changes:
                doRemoveObserver = observerMonitor.notifyChanges(changes)
                if doRemoveObserver:
                    # Remove this observer, it's monitored path is gone
                    # XXX - Send observer removed notification?
                    self.__observer_lock.acquire()
                    try:
                        self.__removeObserverMonitor(observerMonitor)
                    finally:
                        self.__observer_lock.release()

    ##
    ## Called from both main monitoring thread and from other threads
    ##

    # Unused
    #def isFile(self):
    #    return self.__watch_type == WATCH_FILE
    #
    #def isDirectory(self):
    #    return not self.isFile()

    # Does this watch_type == WATCH_DIR_RECURSIVE
    def isRecursive(self):
        return self.__recursive

    # Remove any observers that have been deleted elsewhere (weak-reference check)
    def removeDeadObservers(self):
        self.__observer_lock.acquire()
        try:
            for observerMonitor in self.__observer_monitors[:]: # copy, as we delete
                if not observerMonitor.getAliveObserver():
                    self.__removeObserverMonitor(observerMonitor)
        finally:
            self.__observer_lock.release()

    ##
    ## These are called from outside the main monitoring thread
    ##
    def addObserver(self, observer, watch_type, flags):
        self.__observer_lock.acquire()
        try:
            for i in range(len(self.__observer_monitors)):
                observerMonitor = self.__observer_monitors[i]
                if observerMonitor.getUnWrappedObserver() == UnwrapObject(observer):
                    self.__removeObserverMonitor(observerMonitor)
                    observerMonitor = ObserverMonitor(observer, self.path, watch_type, flags, log)
                    break
            else:
                observerMonitor = ObserverMonitor(observer, self.path, watch_type, flags, log)
            # Initialise the file stats that this monitor watches
            observerMonitor.initCache()
            #log.debug("MonitoredPath: addObserver: type:%s, path:%s", watch_type, self.path)
            self.__addObserverMonitor(observerMonitor)
        finally:
            self.__observer_lock.release()

    def removeObserver(self, observer):
        self.__observer_lock.acquire()
        try:
            for i in range(len(self.__observer_monitors)):
                observerMonitor = self.__observer_monitors[i]
                #print "observer: %r" % (observer)
                #print "observerMonitor.getAliveObserver(): %r" % (observerMonitor.getAliveObserver())
                #print "observerMonitor.getAliveObserver() == observer: %r" % (observerMonitor.getAliveObserver() == observer)
                #print "id %s == id %s" % (id(observerMonitor.getAliveObserver()), id(observer))
                if observerMonitor.getUnWrappedObserver() == UnwrapObject(observer):
                    #print "Found it, removing the observer"
                    self.__removeObserverMonitor(observerMonitor)
                    break
        finally:
            self.__observer_lock.release()


class osFilePollingNotifier(threading.Thread):
    """Class that holds the information concerning the files and directories
    that need to be watched and polled for filesystem changes.
    
    The external systems will tell this class which files and directories to
    monitor, and this class will be polling those files/dirs in a separate
    thread and be able to send notifications to the external systems when one
    of these files or directories changes.

    This class keeps a remebered cache of all the monitored files and
    directories, and when subsequent polls occur (every X seconds) the current
    status of file/directory is checked against the remebered information. If
    this has changed in someway, then a notification must be raised telling the
    external system of the change that has occured.
    """
    def __init__(self, poll_period=DEFAULT_POLL_PERIOD):
        threading.Thread.__init__(self, name="File Notifications - Polling")
        self.setDaemon(1)   # If Komodo goes down, we go down
        self._isRunning = False

        # How often polling occurs
        self.__polling_period = poll_period

        # Lock used to ensure nothing updates the monitored locations whilst in
        # an essential call
        self._shutdown = threading.Condition()
        self.__shutdown_event = threading.Event()
        self.__finished_checking_event = threading.Event()
        self.__lock_observer_changes = threading.Lock()

        # __observers is a dictionary of locations we want to be notified about
        #   key:   location path - absolute path on filesystem
        #   value: _MonitoredPath class object (contains __ObserverMonitor's)
        self.__monitors = {}

        # Stat cache is the last known information concerning the files and
        #      directories watched.
        #   key:   file name - absolute path
        #   value: FileStat object containing os.stat() info
        self.__stat_cache = {}
        self.__last_stat_cache = {}
        # Directory cache is the last known information concerning the directories
        #   key:   directory name - absolute path
        #   value: a os.listdir() value (list of contents)
        self.__directory_cache = {}
        self.__last_directory_cache = {}

    ####################################################
    ##        Internal methods and attributes         ##
    ####################################################

    # Check all the monitored locations to see if anything has changed
    def __checkMonitoredFilesystem(self):
        # Lock the observers, so we don't get any threading problems
        self.__lock_observer_changes.acquire()
        try:
            # Clean out any dead monitors
            self._removeDeadMonitors()
            allMonitorItems = self.__monitors.items()
            for path, monitoredPath in allMonitorItems:
                monitoredPath.initializeNewObservers()
        finally:
            # Release the lock, we have our copy of the monitors
            self.__lock_observer_changes.release()

        # locations_checked gets updated through the call to checkForChanges().
        # It remembers what was checked, so a second checking isn't necessary
        self.__checked_locations = {}
        # We start off with nothing currently cached (we have last cache though)
        self.__stat_cache = {}
        self.__directory_cache = {}
        #log.debug("__checkMonitoredFilesystem: num monitors: %d", len(self.__monitors))

        # Check all the monitored locations
        for path, monitoredPath in allMonitorItems:
            #log.debug("__checking path: %s", path)
            if not self._isRunning:
                return
            monitoredPath.checkForChanges(self.__last_stat_cache,
                                          self.__stat_cache,
                                          self.__last_directory_cache,
                                          self.__directory_cache,
                                          self.__checked_locations)

        # Swap over the caches now (the new becomes the old)
        self.__last_stat_cache = self.__stat_cache
        self.__last_directory_cache = self.__directory_cache

    # Adding an observer, find or create the monitoredPath object, add observer
    #   observer   - koIFileNotificationObserver to which notifications get sent
    #   path       - the local filename of the location to watch
    #   watch_type - what type of watch this is (file, dir, recursive dir)
    #   flags      - notify flags, a notification will be sent when this happens
    def _addObserverForPath(self, observer, path, watch_type, flags):
        monitoredPath = self.__monitors.get(path)
        if not monitoredPath:
            monitoredPath = _MonitoredPath(path)
            self.__monitors[path] = monitoredPath

        monitoredPath.addObserver(observer, watch_type, flags)
        log.debug("_addObserverForPath: num monitors: %d", len(self.__monitors))

    # Stop watching this location for the given observer.
    #   observer - koIFileNotificationObserver to which addObserver was called
    #   path     - the filename or uri of the location being watched
    def _removeObserverForPath(self, observer, path):
        monitoredPath = self.__monitors.get(path)
        if monitoredPath:
            monitoredPath.removeObserver(observer)

    # Remove monitors that have no observers, as no need to poll these locations
    def _removeDeadMonitors(self):
        for path, monitoredPath in self.__monitors.items():
            monitoredPath.removeDeadObservers()
            if len(monitoredPath) == 0:
                # Don't need to watch this path anymore
                self.__monitors.pop(path)

    # Return the number of observers that are watching locations
    def _getNumberObservers(self):
        total_count = 0
        for path, monitoredPath in self.__monitors.items():
            total_count += len(monitoredPath)
        return total_count

    # Unused
    #def isMonitoringPath(self, path):
    #    # There are two approaches here:
    #    #   1 - go through the list of monitors and check to see if each one
    #    #       monitors this path
    #    #   2 - Check if anything monitors this path (O1), then keep getting
    #    #       the parent dirname and check if that is monitored until no
    #    #       parents are left.
    #    # Using 2nd option for now:
    #    previous_path = None
    #    while path and path != previous_path:
    #        monitoredPath = self.__monitors.get(path)
    #        log.debug("isMonitoringPath: checking path: %s", path)
    #        if monitoredPath and monitoredPath.monitorsLocation(path):
    #            return True
    #        log.debug("isMonitoringPath: was not monitored")
    #        previous_path = path
    #        path = os.path.dirname(path)

    # The thread calls this when the start() function is called
    def run(self):
        log.info("Polling watch service started")
        self._isRunning = 1
        # Below is some profiling code, used for testing performance
        #import hotshot, hotshot.stats
        #profiler = hotshot.Profile("%s.prof" % (__file__))
        while 1:
            self.__shutdown_event.wait(self.__polling_period)
            if not self._isRunning:
                break
            self.__finished_checking_event.clear()
            try:
                self.__checkMonitoredFilesystem()
                #profiler.runcall(self.__checkMonitoredFilesystem)
            except Exception, e:
                log.error("Polling service runtime exception:")
                log.exception(e)
            self.__finished_checking_event.set()
            if not self._isRunning:
                break
        self._shutdown.acquire()
        self._shutdown.notify()
        self._shutdown.release()
        log.info("Polling watch service stopped")

    ####################################################
    ##        External methods and attributes         ##
    ####################################################

    def startNotificationService(self):
        pass  # The thread is started lazily through the addObserver call.

    def stopNotificationService(self):
        if self._isRunning:
            self._isRunning = 0
            # Notify the thread to shutdown
            self.__shutdown_event.set()
            self._shutdown.acquire()
            self._shutdown.wait(5)
            self._shutdown.release()

    # Watch this location and notify when the given flag is changed
    #   observer   - koIFileNotificationObserver to which notifications get sent
    #   path       - the local filename of the location to watch
    #   watch_type - what type of watch this is (file, dir, recursive dir)
    #   flags      - notify flags, a notification will be sent when this happens
    def addObserver(self, observer, path, watch_type, flags):
        # We have to wait until the run starts
        self.__lock_observer_changes.acquire()
        try:
            # Lazily start the polling thread.
            if not self._isRunning:
                self.start()
                self._isRunning = 1
            self._removeDeadMonitors()
            self._addObserverForPath(observer, path, watch_type, flags)
            #self.__observers_to_add.append((observer, path, watch_type, flags))
        finally:
            self.__lock_observer_changes.release()
        log.info("addObserver: type: %d, flags: %x, for path %s", watch_type,
                  flags, path)
        #log.debug("Number of observers in total now: %d", self._getNumberObservers())
        return True

    # Stop watching this location for the given observer.
    #   observer - koIFileNotificationObserver to which addObserver was called
    #   path     - the filename or uri of the location being watched
    def removeObserver(self, observer, path):
        self.__lock_observer_changes.acquire()
        try:
            self._removeObserverForPath(observer, path)
            self._removeDeadMonitors()
        finally:
            self.__lock_observer_changes.release()
        log.info("removeObserver: for path %s", path)
        #log.debug("Number of observers in total now: %d", self._getNumberObservers())

    # polled_uris attribute: List of URI's currently being polled
    def __getAllPolledUris(self):
        self.__lock_observer_changes.acquire()
        try:
            self._removeDeadMonitors()
            uri_locations = []
            for path, monitoredPath in self.__monitors.items():
                uri_locations.append(pathToUri(monitoredPath.path))
            return uri_locations
        finally:
            self.__lock_observer_changes.release()
    polled_uris = property(__getAllPolledUris, doc="Return a list of the uri's being watched")

    ####################################################
    ##          Testing and debugging methods         ##
    ####################################################

    def dump(self):
        self.__lock_observer_changes.acquire()
        try:
            log.debug("Watching:")
            self._removeDeadMonitors()
            for monitoredPath in self.__monitors.items():
                log.debug(monitoredPath)
        finally:
            self.__lock_observer_changes.release()

    def waitTillFinishedRun(self):
        self.__finished_checking_event.wait()

    def _get_number_of_observed_locations(self):
        self.waitTillFinishedRun()
        self.__lock_observer_changes.acquire()
        try:
            val = len(self.__monitors)
        finally:
            self.__lock_observer_changes.release()
        log.debug("_get_number_of_observed_locations: %d", val)
        return val
    number_of_observed_locations = property(_get_number_of_observed_locations, doc="Return the number of locations being watched")
