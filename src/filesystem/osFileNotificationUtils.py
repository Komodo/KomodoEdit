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

# osFileNotificationUtils:
#   Utility classes that are common between all the file notification systems.
#
# Contributors:
# * Todd Whiteman

import sys
from os import listdir as os_listdir
from os import sep as os_sep
from os import stat as os_stat
from os.path import dirname as os_path_dirname
from stat import S_IFREG, S_IFDIR

# Setup the common parameters used
try:
    # Using XPCOM, i.e. it is used by Komodo
    from xpcom import components, COMException, ServerException, nsError
    from xpcom.server import UnwrapObject
    from xpcom.client import WeakReference
    WATCH_FILE = components.interfaces.koIFileNotificationService.WATCH_FILE
    WATCH_DIR = components.interfaces.koIFileNotificationService.WATCH_DIR
    WATCH_DIR_RECURSIVE = components.interfaces.koIFileNotificationService.WATCH_DIR_RECURSIVE
    FS_FILE_CREATED = components.interfaces.koIFileNotificationService.FS_FILE_CREATED
    FS_FILE_DELETED = components.interfaces.koIFileNotificationService.FS_FILE_DELETED
    FS_FILE_MODIFIED = components.interfaces.koIFileNotificationService.FS_FILE_MODIFIED
    FS_DIR_CREATED = components.interfaces.koIFileNotificationService.FS_DIR_CREATED
    FS_DIR_DELETED = components.interfaces.koIFileNotificationService.FS_DIR_DELETED
    FS_DIR_MODIFIED = components.interfaces.koIFileNotificationService.FS_DIR_MODIFIED
    FS_UNKNOWN = components.interfaces.koIFileNotificationService.FS_UNKNOWN
    FS_NOTIFY_ALL = components.interfaces.koIFileNotificationService.FS_NOTIFY_ALL
    FS_PATH_WAS_DELETED = components.interfaces.koIFileNotificationService.FS_FILE_DELETED | \
                          components.interfaces.koIFileNotificationService.FS_DIR_DELETED
    haveXPCOM = 1
except ImportError, e:
    # Standalone mode, used for testing
    haveXPCOM = 0
    sys.stderr.write("WARNING: osFileNotificationUtils: Could not import XPCOM components, running as standalone.\n")
    from weakref import ref as WeakReference
    def UnwrapObject(obj): return obj
    class ComException:
        pass
    class components:
        class interfaces:
            koIFileNotificationObserver = None
        @staticmethod
        def ProxyToMainThread(fn):
            return fn
        @staticmethod
        def ProxyToMainThreadAsync(fn):
            return fn
    # Type of watch to perform (used in addObserver below)
    WATCH_FILE          = 0
    WATCH_DIR           = 1
    WATCH_DIR_RECURSIVE = 2
    # Notify flags, a notification will be sent when this happens
    #   (used in addObserver below and the koIFileNotificationObserver above)
    FS_FILE_CREATED     = 0x01
    FS_FILE_DELETED     = 0x02
    FS_FILE_MODIFIED    = 0x04
    # FS_FILE_SPARE       = 0x08
    FS_DIR_CREATED      = 0x10
    FS_DIR_DELETED      = 0x20
    FS_DIR_MODIFIED     = 0x40    # Needed ??
    FS_UNKNOWN          = 0x80
    FS_NOTIFY_ALL       = 0xFF
    FS_PATH_WAS_DELETED = FS_FILE_DELETED | FS_DIR_DELETED

# Actions as strings
FS_ACTIONS = {
    FS_FILE_CREATED  : "File created",
    FS_FILE_DELETED  : "File deleted",
    FS_FILE_MODIFIED : "File modified",
    FS_DIR_CREATED   : "Directory created",
    FS_DIR_DELETED   : "Directory deleted",
    FS_DIR_MODIFIED  : "Directory modified",
    FS_UNKNOWN       : "Unknown change",
}


#
# Convert a local path (string) into a URI (string)
# XXX - Better way to convert filename to URI.
# XXX - Perhaps use an XPCOM nsIFile (example below)
        #try:
        #    nsIFile = components.classes["@mozilla.org/file/local;1"].\
        #                          createInstance(components.interfaces.nsILocalFile);
        #    nsIFile.initWithPath(path)
        #    # Convert the local path to a uri
        #    uri = self.__io_service.getURLSpecFromFile(nsIFile)
        #except COMException, e:
        #    log.exception(e)
if sys.platform.startswith("win"):
    def pathToUri(path):
        # Windows use file:///C:/... yada yada
        return "file:///" + path.replace(os_sep, "/")
else:
    def pathToUri(path):
        # Linux, Mac should already start with a forwardslash
        return "file://" + path


# The idea here is that we don't want to make excessive stat calls. Once
# is enough, then we re-use that stat information as much as possible.
class FileStat:
    """Storage of stat information needed for polling"""
    def __init__(self, stat_info):
        self.st_mode  = stat_info.st_mode
        self.st_size  = stat_info.st_size
        self.st_mtime = stat_info.st_mtime
        m = self.st_mode & 0170000
        self.__isFile = m == S_IFREG
        self.__isDir  = m == S_IFDIR
    def __eq__(self, other_fileStatObject):
        if other_fileStatObject is None:
            return False
        else:
            return (self.st_mode  == other_fileStatObject.st_mode and
                    self.st_size  == other_fileStatObject.st_size and
                    self.st_mtime == other_fileStatObject.st_mtime)
    def __ne__(self, other_fileStatObject):
        return not self == other_fileStatObject
    def __str__(self):
        return "FileStat(d:%r, f:%r, mo:%d, s:%d, mt:%d)" % (self.isDir(),
                                                             self.isFile(),
                                                             self.st_mode,
                                                             self.st_size,
                                                             self.st_mtime)
    #def __repr__(self):
    #    return str(self)
    def isFile(self):
        return self.__isFile
    def isDir(self):
        return self.__isDir


# 
# An observer wrapper class used by all file notification systems.
#   - Wraps the koIFileNotificationObserver and ensures a weakreference used.
#
class ObserverMonitor:
    """Storage of observer information, used by _MonitoredPath"""
    def __init__(self, observer, path, watch_type, flags, log):
        # XXX - WeakRef this observer (xpcom)
        #self.observer = observer
        try:
            self.__observer_weakref = WeakReference(observer)
        except COMException:
            # Not a supported xpcom object
            self.__observer_weakref = observer
        self.path = path
        self.uri = pathToUri(path)
        self.watch_type = watch_type
        self.flags = flags
        self.__recursive = (watch_type == WATCH_DIR_RECURSIVE)
        #log.debug("self.__recursive: %r", self.__recursive)
        self.log = log
        # Initialized:
        #   0 - Just been created
        #   1 - Cache has been initialized through initCache()
        #   2 - Now ready for first check against it's own cache
        #   3 - Own cache cleared. Ready for checking against a global cache
        #   4 - Observed path was deleted
        self.__initalized = 0
        self.__statCache = {}
        self.__dirCache = {}
        self.__shutdown = False ##< Whether we have shut down and should suppress

    def __str__(self):
        return "ObserverMonitor: f:%02x, r:%-5r, path:%s" % (self.flags, self.__recursive, self.path)

    @components.ProxyToMainThread
    def getAliveObserver(self):
        if callable(self.__observer_weakref):
            o = self.__observer_weakref()
        else:
            o = self.__observer_weakref
        return o

    # Return an unwrapped object (if possible) of the observer
    def getUnWrappedObserver(self):
        observer = self.getAliveObserver()
        if observer:
            try:
                observer = UnwrapObject(observer)
            except COMException:
                pass
        return observer

    def isRecursive(self):
        return self.__recursive

    def __initCacheForPath(self, path):
        #self.log.debug("__initCacheForPath: %s", path)
        try:
            st = os_stat(path)
            fileStat = FileStat(st)
            self.__statCache[path] = fileStat
            #self.log.debug("__initCacheForPath: add path to cache: %s %s", fileStat, path)
        except OSError:
            # Path does not exist
            #self.log.debug("__initCacheForPath: Path does not exist: %s", path)
            return

        if fileStat.isDir():
            # Initialise the contents
            paths = os_listdir(path)
            self.__dirCache[path] = paths
            # Need to get a stat of all files in this dir
            sep = os_sep
            for fullpath in [ path + sep + x for x in paths ]:
                if self.__recursive:
                    # Call the function recursively then
                    self.__initCacheForPath(fullpath)
                else:
                    try:
                        st = os_stat(fullpath)
                        fullpathFileStat = FileStat(st)
                        self.__statCache[fullpath] = fullpathFileStat
                        #self.log.debug("__initCacheForPath: add subpath to cache: %s %s", fullpathFileStat, fullpath)
                    except OSError:
                        pass # Path does not exist
                #else:
                #    # We already know about this path

    def initCache(self):
        self.__initCacheForPath(self.path)
        self.__initalized = 1

    def getStatCache(self):
        return self.__statCache

    def getDirCache(self):
        return self.__dirCache

    def justCreated(self):
        return self.__initalized == 1

    def isReady(self):
        return self.__initalized >= 2

    def setReadyForFirstCheck(self):
        self.__initalized = 2

    def mustCheckAgainstOwnCache(self):
        return self.__initalized == 2

    def clearOwnCache(self):
        self.__initalized = 3
        self.__statCache = {}
        self.__dirCache = {}

    # Check whether the path has been deleted (set through notifyChanges)
    def hasExpired(self):
        return self.__initalized == 4

    # Return if this observer is monitoring this path
    # Returns True when it is monitoring the path.
    def monitorsPath(self, path):
        if path == self.path:
            return True
        if self.watch_type == WATCH_FILE:
            return False
        elif self.watch_type == WATCH_DIR:
            if os_path_dirname(path) == self.path:
                return True
        elif len(path) > len(self.path): # and self.watch_type == WATCH_DIR_RECURSIVE
            if path[:len(self.path)] == self.path:
                return True
        return False

    # Check if own watched path is a child path of the one given
    # Returns True when self is a descendant of the supplied path
    def isDecendantOfPath(self, path):
        return (len(path) < len(self.path) and self.path[:len(path)] == self.path)

    # Send a notification that our watched path was deleted.
    def notifyOwnPathDeleted(self):
        if self.watch_type == WATCH_FILE:
            return self.notifyChanges( { self.path: FS_FILE_DELETED } )
        else:
            return self.notifyChanges( { self.path: FS_DIR_DELETED } )

    @components.ProxyToMainThreadAsync
    def sendObserverNotifications(self, observer, uri, change):
        # We must proxy the observer calls to the UI thread since most instances
        # will be modifying UI.
        if not self.__shutdown:
            observer.fileNotification(uri, change)

    # Return True if this monitor is finished and should be deleted
    def notifyChanges(self, changes):
        observer = self.getAliveObserver()
        if not observer:
            # It's been deleted, do not raise notifications
            return True
        isDeleted = False
        #self.log.debug("notifyChanges: changes to path:")
        #print "notifyChanges: changes to path:", self.path
        for path, change in changes.items():
            #self.log.debug("  Checking change: %x, path: %s", change, path )
            # Set isDeleted if we are removing the watched path
            if change & FS_PATH_WAS_DELETED:
                if self.path == path:
                    self.__initalized = 4
                    isDeleted = True
                elif change == FS_DIR_DELETED and self.isDecendantOfPath(path):
                    #self.log.debug("Deleted parent of watched path")
                    #self.log.debug("  Watched path: %s", self.path)
                    #self.log.debug("  Deleted path: %s", path)
                    self.__initalized = 4
                    isDeleted = True
                    if self.watch_type == WATCH_FILE:
                        change = FS_FILE_DELETED
                    self.sendObserverNotifications(ob, self.uri, change)
                    return isDeleted
            elif change & FS_UNKNOWN:
                self.sendObserverNotifications(ob, self.uri, change)
            #elif change == FS_DIR_CREATED:
            #    print "FS_DIR_CREATED, send it on? %r" % (self.flags & change)
            # Check to make sure we are watching for this change
            if self.flags & change and self.monitorsPath(path):
                #if change == FS_DIR_CREATED:
                #    print "FS_DIR_CREATED, did send it on"
                #self.log.debug("  Change met watch criteria and was sent it!")
                # Check to make sure the directory is the one were watching
                uri = pathToUri(path)
                self.log.info("  change: %x, uri: %s", change, uri)
                self.sendObserverNotifications(observer, uri, change)
        return isDeleted

    def shutdown(self):
        """Set the observer to be shut down; this is permanent and cannot be
        reset."""
        self.__shutdown = True
