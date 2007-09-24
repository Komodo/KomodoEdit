# Copyright (c) 2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

# Watches for file changes in the filesystem for this OS. Notifications of
# changes are send through the observer service.
# OS file notifications will be used if available, else polling will be used as
# the fallback.
#
# Contributors:
# * Todd Whiteman

import sys
import logging

from xpcom import components, COMException, ServerException, nsError
from xpcom.client import WeakReference
from xpcom.server import WrapObject, UnwrapObject

import osFilePollingNotifier

log = logging.getLogger("koFileNotificationService")
#log.setLevel(logging.DEBUG)

class koFileNotificationService:
    """An xpcom service for watching files for changes and alerting when
       a change occurs."""

    _com_interfaces_ = [components.interfaces.koIFileNotificationService,
                        components.interfaces.nsIObserver]
    _reg_clsid_ = "{ec1e9ce4-85e7-4be1-a673-b80206322336}"
    _reg_contractid_ = "@activestate.com/koFileNotificationService;1"
    _reg_desc_ = "Komodo file change notification service"

    def __init__(self):
        self.__prefs = components.classes["@activestate.com/koPrefService;1"].\
                         getService(components.interfaces.koIPrefService).prefs
        self.__io_service = components.classes["@mozilla.org/network/protocol;1?name=file"].\
                    getService(components.interfaces.nsIFileProtocolHandler)
        # Service enabled
        self.__enabled = self.__prefs.getBooleanPref("fileNotificationServiceEnabled")
        # Polling enabled
        self.__polling_enabled = True
        if self.__prefs.hasBooleanPref("filePollingServiceEnabled"):
            self.__polling_enabled = self.__prefs.getBooleanPref("filePollingServiceEnabled")

        # Short names for flags
        self.available_file_flags = components.interfaces.koIFileNotificationService.FS_FILE_CREATED | \
                                    components.interfaces.koIFileNotificationService.FS_FILE_DELETED | \
                                    components.interfaces.koIFileNotificationService.FS_FILE_MODIFIED

        # Setup the OS dependant (underlying) services
        self.__polling_notifier = None
        self.__os_file_service = None
        if self.__enabled:
            if self.__polling_enabled:
                # Setup the fallback polling notifier thread
                poll_period = osFilePollingNotifier.DEFAULT_POLL_PERIOD
                if self.__prefs.hasLongPref("filePollingServicePeriod"):
                    poll_period = self.__prefs.getLongPref("filePollingServicePeriod")
                self.__polling_notifier = osFilePollingNotifier.osFilePollingNotifier(poll_period)

            # Setup os file notifications service
            if sys.platform.startswith("win"):
                # Windows
                log.info("Setting up OS File Notifications for Windows")
                import osFileNotifications_win32
                self.__os_file_service = osFileNotifications_win32.WindowsFileWatcherService()
            else:
                # We just poll for now
                self.__os_file_service = koFileNotificationServiceUnavailable()

            if 0:
                # These have not been converted to addObserver, removeObserver format
    
                if sys.platform.startswith("darwin") or sys.platform.startswith("mac"):
                    # Apple / Mac OS
                    log.info("Setting up OS File Notifications for Apple")
                    from osFileNotifications_darwin import DarwinFileWatcherService
                    self.__os_file_service = DarwinFileWatcherService(log)
                elif sys.platform.startswith("linux") or \
                     sys.platform.startswith("sunos") or \
                     sys.platform.startswith("solaris") or \
                     sys.platform.startswith("hp-ux") or \
                     sys.platform.startswith("aix"):
                    # Unix
                    # XXX - Any others here ??
                    log.info("Setting up OS File Notifications for Unix")
                    from osFileNotifications_unix import UnixFileWatcherService
                    self.__os_file_service = UnixFileWatcherService(log)
                else:
                    # XXX - Raise exception?
                    log.warn("Unknown platform: %s", sys.platform)
                    self.__os_file_service = koFileNotificationServiceUnavailable()
    
            self.startNotificationService()

            # Are OS notifications available to use on this machine?
            if self.os_notifications_available:
                log.info("OS file notifications: available.")
            else:
                log.info("OS file notifications: NOT available on this platform: %s", sys.platform)

            # Are file polling notifications enabled
            if self.__polling_enabled:
                log.info("Polling file notifications: available.")
            else:
                log.info("Polling file notifications: DISABLED")
        else:
            log.info("File notification service is disabled.")

        obsSvc = components.classes["@mozilla.org/observer-service;1"].\
                       getService(components.interfaces.nsIObserverService)
        self._wrappedSelf = WrapObject(self,components.interfaces.nsIObserver)
        obsSvc.addObserver(self._wrappedSelf, 'xpcom-shutdown', 1)

    # Return both the URI (string) and nsIFile (xpcom object) for a given URI or
    # a given file path.
    def _getUriAndNSIFileForPath(self, path):
        try:
            log.debug("addObserver: path: %s", path)
            nsIFile = components.classes["@mozilla.org/file/local;1"].\
                                  createInstance(components.interfaces.nsILocalFile);
            nsIFile.initWithPath(path)
            # Convert the local path to a uri
            uri = self.__io_service.getURLSpecFromFile(nsIFile)
        except COMException, e:
            # Try uri then
            log.debug("Could not initialise file with path, trying as URI")
            try:
                uri = path
                nsIFile = self.__io_service.getFileFromURLSpec(uri)
                log.debug("URI initialised okay.")
            except COMException, e:
                log.debug("Could not initialise file with URI")
                raise ServerException(nsError.NS_ERROR_FILE_UNRECOGNIZED_PATH,
                                      "Invalid path format")
        return (uri, nsIFile)

    def observe(self, subject, topic, data):
        if topic == "xpcom-shutdown":
            self.stopNotificationService()

    # long startNotificationService();    // Ready to receiving file change notifications from OS
    def startNotificationService(self):
        if self.__enabled:
            if self.__polling_enabled:
                self.__polling_notifier.startNotificationService()
            if self.os_notifications_available:
                self.__os_file_service.startNotificationService()

    # long stopNotificationService();     // Stop listening to file change notifications from OS
    def stopNotificationService(self):
        if self.__enabled:
            if self.__polling_enabled:
                self.__polling_notifier.stopNotificationService()
            if self.os_notifications_available:
                self.__os_file_service.stopNotificationService()

    # Watch this location and notify when the given flag is changed
    #   observer   - koIFileNotificationObserver to which notifications get sent
    #   path       - the filename or uri of the location to watch
    #   watch_type - what type of watch this is (file, dir, recursive dir)
    #   flags      - notify flags, a notification will be sent when this happens
    def addObserver(self, observer, path, watch_type, flags):
        if not self.__enabled:
            return

        # Parse the path into a file object and validate the parameters.
        uri, nsIFile = self._getUriAndNSIFileForPath(path)

        if not nsIFile.exists():
            raise ServerException(nsError.NS_ERROR_FILE_INVALID_PATH,
                                  "Invalid path, was unable to locate.")
        if watch_type == components.interfaces.koIFileNotificationService.WATCH_FILE:
            if not nsIFile.isFile():
                raise ServerException(nsError.NS_ERROR_FILE_INVALID_PATH,
                                      "The path for a WATCH_FILE type, must be a file.")
            if not flags & self.available_file_flags:
                raise ServerException(nsError.NS_ERROR_INVALID_ARG,
                                      "A WATCH_FILE type must specify flags as a combination of FS_FILE_CREATED, FS_FILE_DELETED, FS_FILE_MODIFIED.")
        else:
            # WATCH_DIR or WATCH_DIR_RECURSIVE
            if not nsIFile.isDirectory():
                raise ServerException(nsError.NS_ERROR_FILE_NOT_DIRECTORY,
                                      "The path for a WATCH_DIR type, must be a directory.")

        # Try using os file notifications, if that fails, then use polling
        if not self.os_notifications_available or \
           not self.__os_file_service.addObserver(observer, nsIFile.path, watch_type, flags):
            if self.__polling_enabled:
                self.__polling_notifier.addObserver(observer, nsIFile.path, watch_type, flags)
        #self.dump()

    # Stop watching this location for the given observer.
    #   observer - koIFileNotificationObserver to which addObserver was called
    #   path     - the filename or uri of the location being watched
    def removeObserver(self, observer, path):
        if not self.__enabled:
            return

        # Try and parse the path into a nsIFile object
        uri, nsIFile = self._getUriAndNSIFileForPath(path)

        # We don't know which service is watching this file, but we can tell
        # them both to stop watching it though!
        if self.os_notifications_available:
            self.__os_file_service.removeObserver(observer, nsIFile.path)
        if self.__polling_enabled:
            self.__polling_notifier.removeObserver(observer, nsIFile.path)
        #self.dump()

    # URI's that are being polled by the file polling service
    def getAllPolledUris(self):
        if not self.__enabled or not self.__polling_enabled:
            return []

        # self.__polling_notifier.polled_files is a list of uri's (strings)
        return self.__polling_notifier.polled_uris

    # XXX - RFU
    # Send observer notification the file has changed
    #   void sendNotification(in wstring uri); 
    #     uri: the Komodo URI for this file
    #def sendNotification(self, uri):
    #    self.__os_file_service.sendNotification(uri)

    def dump(self):
        if not self.__enabled:
            return

        self.__os_file_service.dump()
        if self.__polling_enabled:
            self.__polling_notifier.dump()

    def __are_os_notifications_available(self):
        return self.__os_file_service.available
    os_notifications_available = property(__are_os_notifications_available,
            doc="Does the os supports file notifications from the kernel level")


class koFileNotificationServiceUnavailable:
    """Dummy class for when OS file notifications not available"""
    def __init__(self):
        self.available = False
    def startNotificationService(self):
        pass
    def stopNotificationService(self):
        pass
    def addObserver(self, observer, path, watch_type, flags):
        raise ServerException( nsError.NS_ERROR_NOT_IMPLEMENTED,
                              "No file notifications available" )
    def removeObserver(self, observer, path, watch_type, flags):
        pass
    def dump(self):
        pass
