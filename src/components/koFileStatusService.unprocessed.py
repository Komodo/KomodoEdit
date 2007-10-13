#!python
# Copyright (c) 2000-2007 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.
#
# Contributors:
#   Shane Caraveo
#   Todd Whiteman
#
# Overview:
#   This service is used to maintain up-to-date file status information. A
#   background thread is used to periodicaly check and update the status of
#   all Komodo files for all the registered file status checkers. This
#   service has plugin capability to be able to add new types of status
#   checkers (i.e. CVS, Perforce, Subversion).
#
#   The file status service obtains the list of all files (koIFile's) to
#   check by querying the koIFileService. Each registered file
#   status checker will be asked to update the status of the koIFile
#   on demand (due to events such as file modification, focus events).
#   It is the responsibility of the file status checker to update the
#   necessary koIFile information and return the status change result to
#   the file status service. When the file status checker returns a
#   result that indicates the file status has changed, a
#   "file_status_changed" notification will be sent through the global
#   notification service.
#
# Incoming observer notifications:
#   XXX - Move this into a koIFileStatusService call.
#   "update_file_status" - (containing the url of file to update)
#
# Outgoing observer notifications:
#   "file_status_changed" - (containing the updated koIFile and it's url)
#

import os
import sys
import time
import logging
import threading

from xpcom import components, nsError, COMException
from xpcom._xpcom import PROXY_SYNC, PROXY_ALWAYS, PROXY_ASYNC
from xpcom.server import UnwrapObject

import timeline
from fileStatusUtils import KoDiskFileChecker

log = logging.getLogger('koFileStatusService')
#log.setLevel(logging.DEBUG)


# Sort according to directory v's file.
# Each item a/b is a tuple of (koIFile, uri, reason)
def sortFileStatus(a, b):
    if a[0].isDirectory and not b[0].isDirectory:
        return 1
    if b[0].isDirectory and not a[0].isDirectory:
        return -1
    return cmp(a[1], b[1])

class KoFileStatusService:
    _com_interfaces_ = [components.interfaces.koIFileStatusService,
                        components.interfaces.nsIObserver,
                        components.interfaces.koIFileNotificationObserver]
    _reg_clsid_ = "{20732408-43DA-4ca2-BC9F-B82437A3CB2B}"
    _reg_contractid_ = "@activestate.com/koFileStatusService;1"
    _reg_desc_ = "Komodo File Status Service"

    monitoredFileNotifications = ("file_status", "file_status_now",
                                  "file_changed", )

    def __init__(self):
        timeline.enter('koFileStatusService.__init__')
        self._proxyMgr = components.classes["@mozilla.org/xpcomproxy;1"].\
            getService(components.interfaces.nsIProxyObjectManager)
        self._observerSvc = components.classes["@mozilla.org/observer-service;1"].\
            getService(components.interfaces.nsIObserverService)
        self._observerProxy = self._proxyMgr.getProxyForObject(None,
            components.interfaces.nsIObserverService, self._observerSvc,
            PROXY_ALWAYS | PROXY_SYNC)
        self._globalPrefs = components.classes["@activestate.com/koPrefService;1"].\
            getService(components.interfaces.koIPrefService).prefs
        self._fileSvc = \
            components.classes["@activestate.com/koFileService;1"] \
            .getService(components.interfaces.koIFileService)
        self._fileNotificationSvc = \
            components.classes["@activestate.com/koFileNotificationService;1"].\
            getService(components.interfaces.koIFileNotificationService)
        self.FNS_WATCH_FILE = components.interfaces.koIFileNotificationService.WATCH_FILE
        self.FNS_NOTIFY_ALL = components.interfaces.koIFileNotificationService.FS_NOTIFY_ALL
        self.FNS_FILE_DELETED = components.interfaces.koIFileNotificationService.FS_FILE_DELETED

        # The reasons why the status service is checking a file(s).
        self.REASON_BACKGROUND_CHECK = components.interfaces.koIFileStatusChecker.REASON_BACKGROUND_CHECK
        self.REASON_ONFOCUS_CHECK = components.interfaces.koIFileStatusChecker.REASON_ONFOCUS_CHECK
        self.REASON_FILE_CHANGED = components.interfaces.koIFileStatusChecker.REASON_FILE_CHANGED
        self.REASON_FORCED_CHECK = components.interfaces.koIFileStatusChecker.REASON_FORCED_CHECK

        # Set of files need to be status checked. Each item is a tuple of
        # (koIFile, url, reason)
        self._items_to_check = set()
        # Set up the set of monitored urls
        self._monitoredUrls = set()
        # List of status checkers (file and SCC checkers).
        self._statusCheckers = []
        # Shutdown is used to tell the background status checking thread to stop
        self.shutdown = 0
        
        # set up the background thread
        self._thread = None
        self._tlock = threading.Lock()
        self._cv = threading.Condition()
        timeline.leave('koFileStatusService.__init__')

    def init(self):
        timeline.enter('koFileStatusService.init')

        # Setup notification observers
        for notification in self.monitoredFileNotifications:
            self._observerSvc.addObserver(self, notification, 0)
        self._observerSvc.addObserver(self, 'xpcom-shutdown', 1)
        self._fileSvc.observerService.addObserver(self, '', 0)

        # Add file status checker services
        self.addFileStatusChecker(KoDiskFileChecker())
        # Add the dynamically created file status extensions.
        catman = components.classes["@mozilla.org/categorymanager;1"].\
                        getService(components.interfaces.nsICategoryManager)
        category = 'category-komodo-file-status'
        names = catman.enumerateCategory(category)
        while names.hasMoreElements():
            nameObj = names.getNext()
            nameObj.QueryInterface(components.interfaces.nsISupportsCString)
            name = nameObj.data
            cid = catman.getCategoryEntry(category, name)
            log.info("Adding file status checker for %r: %r", name, cid)
            try:
                checker = components.classes[cid].\
                    createInstance(components.interfaces.koIFileStatusChecker)
                self.addFileStatusChecker(checker)
            except Exception, e:
                log.error("Unable to load %r status checker: %r", name, cid)

        # Start the file status thread running
        self._tlock.acquire()
        self._thread = threading.Thread(target = KoFileStatusService._process,
                                        name = "File Status Service",
                                        args = (self,))
        self._thread.start()
        self._tlock.release()
        timeline.leave('koFileStatusService.init')

    ##
    # Add a file status checker to the list known of in service file checkers.
    # checkerInstance should be a derived object of KoFileCheckerBase. SCC
    # checkers should derive from the specialized KoSCCChecker.
    # @public
    def addFileStatusChecker(self, checkerInstance):
        self._tlock.acquire()
        try:
            log.info("addFileStatusChecker:: added %r", checkerInstance.name)
            checkerInstance.initialize()
            self._statusCheckers.append(checkerInstance)
        finally:
            self._tlock.release()

    ##
    # Remove a file status checker from the list of in service file checkers.
    # @param checkerInstance Previously added by addFileStatusChecker()
    # @public
    def removeFileStatusChecker(self, checkerInstance):
        self._tlock.acquire()
        try:
            if checkerInstance in self._statusCheckers:
                self._statusCheckers.remove(checkerInstance)
                checkerInstance.shutdown()
        finally:
            self._tlock.release()

    ##
    # koIFileNotificationObserver interface: called on file change events.
    # @private
    def fileNotification(self, uri, flags):
        log.debug("fileNotification received %d for %r" % (flags, uri))
        # This url has changed, perform a status check
        self._cv.acquire()
        try:
            if flags & self.FNS_FILE_DELETED:
                # The file was deleted, remove it from our list of paths checked.
                # The file notification system observer is automatically removed.
                self._monitoredUrls.pop(uri)
            else:
                self._items_to_check.add((UnwrapObject(self._fileSvc.getFileFromURI(uri)),
                                          uri, self.REASON_FILE_CHANGED))
            self._cv.notify()
        finally:
            self._cv.release()

    ##
    # nsIObserver interface: listens for preference changes, file notification
    # events and fileSvc notifications.
    # @private
    def observe(self, subject, topic, data):
        try:
            log.debug("status observer received %s:%s" % (topic, data))
            if topic == 'xpcom-shutdown':
                log.debug("file status got xpcom-shutdown, unloading");
                self.unload()
                return
    
            # These are other possible topics, they just force the
            # file status service to update itself immediately
            #elif topic == "file_added":
            #elif topic == "file_changed":
            #elif topic == "file_update_now":
    
            self._cv.acquire()
            try:
                if topic in ("file_added", "file_status_now"):
                    self._items_to_check.add((UnwrapObject(subject), data, self.REASON_FORCED_CHECK))
                    log.debug("Forced recheck of uri: %r", data)
                elif topic in ("file_changed"):
                    # This notification can come with just about anything for
                    # the subject element, so we need to find the matching
                    # koIFile for the given uri.
                    koIFile = self._fileSvc.getFileFromURI(data)
                    self._items_to_check.add((UnwrapObject(koIFile), data, self.REASON_FILE_CHANGED))
                    log.debug("Forced recheck of uri: %r", data)
                self._cv.notify()
            finally:
                self._cv.release()
        except Exception, e:
            log.exception("Unexpected error in observe")

    ##
    # Stop listening to a file notification
    # @private
    def _removeObserver(self, topic):
        try:
            self._observerSvc.removeObserver(self, topic)
        except:
            log.debug("Unable to remove observer %s"%topic)

    ##
    # Stop the file status service, remove all notification observers
    # @private
    def unload(self):
        self.shutdown = 1
        if self._thread.isAlive():
            self._cv.acquire()
            self._cv.notify()
            self._cv.release()

        for checker in self._statusCheckers:
            self.removeFileStatusChecker(checker)
    
        self._removeObserver("file_changed")
        self._removeObserver("file_status_now")
        self._removeObserver("file_update_now")

        try:
            self._fileSvc.observerService.removeObserver(self,'')
        except:
            # file service shutdown before us?
            log.debug("Unable to remove file service observers")

    def _getFileStatusNow(self, URI, forceRefresh=False):
        url = self._fileSvc.getFileFromURI(URI)
        self._getFileStatusNowWithFile(url, forceRefresh)
    
    def _getFileStatusNowWithFile(self, url, forceRefresh=False):
        url = UnwrapObject(url)
        # force an update to the status
        urllist = self._fileSvc.getFilesInBaseURI(url.URI)
        urllist = [UnwrapObject(_url) for _url in urllist]
        updatedUrls = set()
        for checker in self._statusCheckers:
            if not checker.isActive():
                continue

            # only check for the primary url.  if it is a directory
            # updateFileStatus will get status for all files in that
            # directory, but not recursivly
            if forceRefresh:
                reason = self.REASON_FORCED_CHECK
            else:
                reason = self.REASON_ONFOCUS_CHECK
            if checker.updateFileStatus(url, reason):
                updatedUrls.add(url)
            for _url in urllist:
                if _url != url:
                    if checker.updateFileStatus(_url, reason):
                        updatedUrls.add(url)
                #else:
                #    print "Not running updateFileStatus() twice for the same url"
        
        # send notifications of status updates
        for _url in updatedUrls:
            try:
                self._observerSvc.notifyObservers(_url, 'file_status', _url.URI)
            except COMException, e:
                # if noone is listening, we get an exception
                if e.errno != nsError.NS_ERROR_FAILURE:
                    #print "caught unknown exception in notify"
                    raise

    def getStatusForFile(self, kofile, forceRefresh):
        #print "getStatusForFile: %r" % (kofile.URI)
        self._getFileStatusNowWithFile(kofile, forceRefresh)

    def getStatusForUri(self, URI, forceRefresh):
        #print "getStatusForUri: %r" % (URI)
        self._getFileStatusNow(URI, forceRefresh)

    def _process(self):
        #print "starting file status background thread"
        last_bg_check_time = time.time()
        while not self.shutdown:
            try:
                self._cv.acquire()
                try:
                    # Run every 31 seconds, but if there are already more
                    # items to check, process them straight away.
                    time_till_next_run = 31 - (time.time() - last_bg_check_time)
                    if not self._items_to_check and time_till_next_run > 0:
                        self._cv.wait(time_till_next_run)
                    items_to_check = list(self._items_to_check)
                    self._items_to_check = set()
                    # Sort the items.
                    items_to_check.sort(sortFileStatus)
                finally:
                    self._cv.release()

                if self.shutdown:
                    log.info("file status thread shutting down")
                    return

                # Maintenance cleanup and addition of observed files.
                #print "doing file status update"
                # XXX - Do we really need to unwrap these puppies?
                all_local_files = [UnwrapObject(koIFile) for koIFile in self._fileSvc.getAllFiles() if koIFile.isLocal and koIFile.isFile ]
                set_all_local_urls = set([koIFile.URI for koIFile in all_local_files ])
                for uri in set_all_local_urls.difference(self._monitoredUrls):
                    # Newly added files.
                    log.debug("Adding a file observer for uri: %r", uri)
                    self._fileNotificationSvc.addObserver(self, uri,
                                                          self.FNS_WATCH_FILE,
                                                          self.FNS_NOTIFY_ALL)
                for uri in self._monitoredUrls.difference(set_all_local_urls):
                    # Removed unused files.
                    self._fileNotificationSvc.removeObserver(self, uri)
                self._monitoredUrls = set_all_local_urls

                if not items_to_check:
                    # Fall back to background checking of all files.
                    isBackgroundCheck = True
                    last_bg_check_time = time.time()
                    reason = self.REASON_BACKGROUND_CHECK
                    items_to_check = [ (koIFile, koIFile.URI, reason) for
                                       koIFile in all_local_files ]
                    #print "updateStatus reason: Background check"
                else:
                    isBackgroundCheck = False
                    #print "updateStatus reason:"
                    #for item in items_to_check:
                    #    print "%d - %s" % (item[2], item[1])

                # all_updated - set of files updated by any status checker
                all_updated_items = set()
                
                # invalidate old status information
                # we do this seperately so that the scc modules can
                # catch full directories of urls
                for checker in self._statusCheckers:
                    #print "checker: %s - %s, active: %s" % (checker.type, checker.name, checker.isActive())
                    #log.debug("try %s", checker.name)
                    # do we need to run this checker?
                    if not checker.isActive():
                        log.debug("Skipping %s, not active"%checker.name)
                        continue
                    if isBackgroundCheck and not checker.isBackgroundCheckingEnabled():
                        log.debug("Skipping %s, no background checking",
                                  checker.name)
                        continue
                    
                    # updated - list of files updated by this status checker
                    updated_items = []

                    # invalidate paths first so they can be re-cached.
                    # build a list of files's that we can actually update
                    for file_item in items_to_check:
                        # Between urls, check that we're still running and that
                        # the checker is still enabled.
                        if self.shutdown:
                            log.info("file status thread shutting down")
                            return
                        # Check this between files as it may have changed
                        if not checker.isActive():
                            log.debug("Checker %s became disabled mid run.",
                                      checker.name)
                            break

                        koIFile, uri, reason = file_item
                        log.debug("examing %r: uri: %r", checker.name, uri)

                        # check the status of the koIFile
                        try:
                            #log.debug("%s checking %s %s" %(checker.name,koIFile.sccType,uri))
                            # Get the status for the file
                            if not checker.updateFileStatus(koIFile,
                                                            reason):
                                log.debug("%s: no change to %r", checker.name,
                                          uri)
                                continue

                            updated_items.append(file_item)
                            try:
                                if len(updated_items) % 10 == 0:
                                    tmpurllist = [item[1] for item in updated_items[-10:]]
                                    self._observerProxy.notifyObservers(None, 'file_status',
                                                                        '\n'.join(tmpurllist))
                            except COMException, e:
                                if e.errno == nsError.NS_ERROR_FAILURE:
                                    # noone is listening, we get an exception
                                    pass
                        except Exception, e:
                            log.exception("Unknown Exception %s" % repr(e))
                        
                    # on every checker we notify, since a particular checker
                    # can take some time
                    if updated_items:
                        try:
                            left = len(updated_items) % 10
                            if left > 0:
                                tmpurllist = [item[1] for item in updated_items[-left:]]
                                #print "file_status sent for:\n  %s" % ('\n  '.join(tmpurllist), )
                                self._observerProxy.notifyObservers(None, 'file_status',
                                                                    '\n'.join(tmpurllist))
                        except COMException, e:
                            if e.errno == nsError.NS_ERROR_FAILURE:
                                # noone is listening, we get an exception
                                pass
                        all_updated_items.update(updated_items)
                
                #for koIFile in files:
                #    koIFile.dofileupdate = 0
            except:
                # we catch any exception so we can clear our thread variable
                # this allows us to restart the thread again later
                # we re raise the exception
                import traceback
                errmsg = ''.join(traceback.format_exception(*sys.exc_info()))
                log.error('KoFileStatusService thread exception %s' % errmsg)

        log.info("file status thread shutting down")
