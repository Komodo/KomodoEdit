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
from xpcom.server import UnwrapObject

import uriparse
from fileStatusUtils import KoDiskFileChecker

log = logging.getLogger('koFileStatusService')
#log.setLevel(logging.DEBUG)
#log.setLevel(logging.INFO)


# Sort according to directory v's file.
# Each item a/b is a tuple of (koIFile, uri, reason)
def sortFileStatus(a, b):
    try:
        if a[0].isDirectory and not b[0].isDirectory:
            return 1
        if b[0].isDirectory and not a[0].isDirectory:
            return -1
    except:
        # koIFile can have problems with some unicode paths
        log.exception("unexpected error from koIFile.isDirectory")
    return cmp(a[1], b[1])

def collate_directories_from_uris(uris):
    """Return a dictionary whose keys are the directories from the uri's
    in the uris list, and whose value is a list of all the uri's with the
    same directory value.
    """
    collatedUris = {}
    os_path_dirname = os.path.dirname
    for uri in uris:
        #print "uri: %r" % (uri, )
        diruri = os_path_dirname(uri)
        uris = collatedUris.get(diruri)
        if not uris:
            collatedUris[diruri] = [uri]
        else:
            collatedUris[diruri].append(uri)
    return collatedUris

class KoFileStatusService:
    _com_interfaces_ = [components.interfaces.koIFileStatusService,
                        components.interfaces.nsIObserver,
                        components.interfaces.koIFileNotificationObserver,
                        components.interfaces.koIPythonMemoryReporter]
    _reg_clsid_ = "{20732408-43DA-4ca2-BC9F-B82437A3CB2B}"
    _reg_contractid_ = "@activestate.com/koFileStatusService;1"
    _reg_desc_ = "Komodo File Status Service"
    _reg_categories_ = [
         ("komodo-startup-service", "koFileStatusService"),
         ("python-memory-reporter", "file_status"),
    ]

    monitoredFileNotifications = ("file_update_now", "file_status_now")

    IDLE_TIMEOUT_SECS = 5 * 60  # 5 minutes (in seconds)
    # Whether the user is currently idle.
    _is_idle = False

    def __init__(self):
        #print "file status created"
        self._observerSvc = components.classes["@mozilla.org/observer-service;1"].\
            getService(components.interfaces.nsIObserverService)
        self._idleSvc = components.classes["@mozilla.org/widget/idleservice;1"].\
            getService(components.interfaces.nsIIdleService)
        self._fileSvc = \
            components.classes["@activestate.com/koFileService;1"] \
            .getService(components.interfaces.koIFileService)

        # The reasons why the status service is checking a file(s).
        self.REASON_BACKGROUND_CHECK = components.interfaces.koIFileStatusChecker.REASON_BACKGROUND_CHECK
        self.REASON_FILE_CHANGED = components.interfaces.koIFileStatusChecker.REASON_FILE_CHANGED
        self.REASON_FORCED_CHECK = components.interfaces.koIFileStatusChecker.REASON_FORCED_CHECK

        # Set of files need to be status checked. Each item is a tuple of
        # (koIFile, url, reason)
        self._items_to_check = set()
        # Reason for why an file status update is occuring.
        self._updateReason = self.REASON_BACKGROUND_CHECK
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
        self._processing_done_event = threading.Event()

    def init(self):
        #print "file status init"
        # Setup notification observers
        for notification in self.monitoredFileNotifications:
            self._observerSvc.addObserver(self, notification, 0)
        self._observerSvc.addObserver(self, 'xpcom-shutdown', False)

        self._idleSvc.addIdleObserver(self, self.IDLE_TIMEOUT_SECS)

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
                log.exception("Unable to load %r status checker: %r", name, cid)

        # Start the file status thread running
        self._tlock.acquire()
        self._thread = threading.Thread(target = KoFileStatusService._process,
                                        name = "File Status Service",
                                        args = (self,))
        self._thread.setDaemon(True)
        self._thread.start()
        self._tlock.release()

    ##
    # Add a file status checker to the list known of in service file checkers.
    # checkerInstance should be a derived object of KoFileCheckerBase. SCC
    # checkers should derive from the specialized KoSCCChecker.
    # @public
    def addFileStatusChecker(self, checkerInstance):
        self._tlock.acquire()
        try:
            log.info("addFileStatusChecker:: added %r", checkerInstance.name)
            # Try to get the native Python checker instance instead of XPCOM
            # one - saves CPU cycles by not having to go through XPCOM.
            try:
                checkerInstance = UnwrapObject(checkerInstance)
            except:
                pass # Keep the XPCOM version then.
            checkerInstance.initialize()
            for i in range(len(self._statusCheckers)):
                checker = self._statusCheckers[i]
                if checkerInstance.ranking_weight < checker.ranking_weight:
                    self._statusCheckers.insert(i, checkerInstance)
                    break
            else:
                self._statusCheckers.append(checkerInstance)
            #print "Order now: %r" % ([x.name for x in self._statusCheckers])
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
    # koIPythonMemoryReporter - tie's into koIMemoryReporter.
    def reportMemory(self, callback, closure):
        """Report memory usage - returns total number of bytes used."""
        total = 0
        for checkerInstance in self._statusCheckers:
            try:
                total += checkerInstance.reportMemory(callback, closure)
            except:
                log.exception("Unable to report memory for %r", checkerInstance)
        return total

    ##
    # koIFileNotificationObserver interface: called on file change events.
    # @private
    def fileNotification(self, uri, flags):
        log.debug("fileNotification received %d for %r", flags, uri)
        # This url has changed, perform a status check
        self._cv.acquire()
        try:
            # Ensure the URI format is the same as used by koIFile.
            # http://bugs.activestate.com/show_bug.cgi?id=79065
            uri = uriparse.pathToURI(uri)
            # We only want to trigger background checking for the files we
            # are actually monitoring. Other file modifications should be
            # ignored.
            if uri in self._monitoredUrls:
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
        #print "file status service observed %r %s %s" % (subject, topic, data)
        try:
            log.debug("status observer received %s:%s", topic, data)
            if topic == 'komodo-startup-service':
                self.init()
                return
            if topic == 'xpcom-shutdown':
                log.debug("file status got xpcom-shutdown, unloading")
                self.unload()
                return
            if topic in ('idle', 'idle-daily'):
                log.info("Idle - take a break kid")
                self._is_idle = True
                return
            if topic in ('active', 'back'):
                log.info("Get back to work")
                self._is_idle = False
                self._cv.acquire()
                self._cv.notify()
                self._cv.release()
                return

            # These are other possible topics, they just force the
            # file status service to update itself immediately
            #elif topic == "file_changed":
            #elif topic == "file_update_now":
    
            self._cv.acquire()
            try:
                if topic in ("file_changed", "file_status_now"):
                    # This notification can come with just about anything for
                    # the subject element, so we need to find the matching
                    # koIFile for the given uri, supplied by the "data" arg.
                    koIFile = self._fileSvc.getFileFromURI(data)
                    self._items_to_check.add((UnwrapObject(koIFile), data, self.REASON_FILE_CHANGED))
                    log.debug("Forced recheck of uri: %r", data)
                    self._cv.notify()
                elif topic in ("file_update_now"):
                    import warnings
                    warnings.warn("'file_update_now' is deprecated, use "
                                  "koIFileStatusService.updateStatusForAllFiles "
                                  "instead.",
                                  DeprecationWarning)
                    self._cv.notify()
            finally:
                self._cv.release()
        except Exception, e:
            log.exception("Unexpected error in observe")

    @components.ProxyToMainThreadAsync
    def notifyObservers(self, subject, topic, data):
        self._observerSvc.notifyObservers(subject, topic, data)

    ##
    # Stop listening to a file notification
    # @private
    def _removeObserver(self, topic):
        try:
            self._observerSvc.removeObserver(self, topic, 0)
        except:
            log.debug("Unable to remove observer %s", topic)

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
    
        for notification in self.monitoredFileNotifications:
            self._removeObserver(notification)

        self._idleSvc.removeIdleObserver(self, self.IDLE_TIMEOUT_SECS)

    def updateStatusForAllFiles(self, updateReason):
        self._cv.acquire()
        try:
            # The update reasons have a priority, and we want to keep the
            # one with the highest priority.
            if updateReason > self._updateReason:
                self._updateReason = updateReason
            self._cv.notify()
        finally:
            self._cv.release()

    def updateStatusForFiles(self, koIFiles, forceRefresh, callback):
        self._cv.acquire()
        try:
            reason = self.REASON_FILE_CHANGED
            if forceRefresh:
                reason = self.REASON_FORCED_CHECK
            items = [(UnwrapObject(koIFile), koIFile.URI, reason) for koIFile in koIFiles]
            for item in items:
                self._items_to_check.add(item)
                log.debug("updateStatusForFiles:: uri: %r", item[1])
            if callback:
                self._processing_done_event.clear()
            self._cv.notify()
        finally:
            self._cv.release()

        if callback:
            def wait_till_done(fileStatusSvc, check_items, callback):
                self._processing_done_event.wait(60)
                @components.ProxyToMainThreadAsync
                def fireCallback():
                    callback.notifyDone()
                fireCallback()

            t = threading.Thread(target=wait_till_done, args=(self, items, callback))
            t.setDaemon(True)
            t.start()

    def updateStatusForUris(self, uris, forceRefresh=False):
        koIFiles = map(self._fileSvc.getFileFromURI, uris)
        self.updateStatusForFiles(koIFiles, forceRefresh, None)

    def _process(self):
        #print "starting file status background thread"
        last_bg_check_time = time.time()
        active_checker_names = []
        fileNotificationSvc = components.classes["@activestate.com/koFileNotificationService;1"].\
                                    getService(components.interfaces.koIFileNotificationService)
        WATCH_DIR = components.interfaces.koIFileNotificationService.WATCH_DIR
        FS_NOTIFY_ALL = components.interfaces.koIFileNotificationService.FS_NOTIFY_ALL
        while not self.shutdown:
            # Give at least a brief respite between loops.
            time.sleep(0.25)
            try:
                # Initialize the working variables, this ensures we don't hold
                # on to any koIFileEx references between runs, allowing the
                # koIFileEx items to be properly garbage collected. See bug:
                # http://bugs.activestate.com/show_bug.cgi?id=68285
                all_local_dirs = None
                all_local_files = None
                file_item = None
                items_to_check = None
                koIFile = None
                set_all_local_urls = None
                updated_items = None
                items_need_to_check = None

                self._cv.acquire()
                try:
                    # Run every 31 seconds, but if there are already more
                    # items to check, process them straight away.
                    time_till_next_run = 31 - (time.time() - last_bg_check_time)
                    if not self._items_to_check and \
                       self._updateReason == self.REASON_BACKGROUND_CHECK and \
                       time_till_next_run > 0:
                        # When idle, use None as wait period, else time_till_next_run.
                        self._cv.wait(None if self._is_idle else time_till_next_run)
                    items_to_check = list(self._items_to_check)
                    self._items_to_check = set()
                    updateReason = self._updateReason
                    #
                    # Either perform a full check or check the items in the
                    # _items_to_check set... decide now.
                    #
                    # If there are any individual files in the _items_to_check
                    # set that have a higher priority than the current
                    # _updateReason, then these items will be updated now, and
                    # the full check will have to wait till the next loop. If
                    # any items in the _items_to_check set have a lower priority
                    # than the _updateReason, then these items will be removed,
                    # as they will get updated (with equal or higher priority)
                    # when the full check is run, if all the items have a lower
                    # priority then a full check will be performed now.
                    for i in range(len(items_to_check) - 1, -1, -1):
                        koIFile, uri, reason = items_to_check[i]
                        if updateReason > self.REASON_BACKGROUND_CHECK and \
                           reason <= updateReason:
                            items_to_check.pop(i)
                    if not items_to_check:
                        # This will count as a background check.
                        last_bg_check_time = time.time()
                        self._updateReason = self.REASON_BACKGROUND_CHECK
                    else:
                        items_to_check.sort(sortFileStatus)
                        # The _updateReason will remain unchanged for next loop.
                finally:
                    self._cv.release()

                if self.shutdown:
                    log.info("file status thread shutting down")
                    return

                log.info("_process:: starting file status check")

                # Maintenance cleanup and addition of observed files.
                #print "doing file status update"
                # XXX - Do we really need to unwrap these puppies?
                all_local_dirs = []
                all_local_files = []
                for koIFile in self._fileSvc.getAllFiles():
                    try:
                        u = UnwrapObject(koIFile)
                        if u.isLocal and not u.isNetworkFile:
                            if u.isFile:
                                all_local_files.append(u)
                            elif u.isDirectory:
                                all_local_dirs.append(u)
                            elif not u.exists:
                                # File was deleted, but something still holds a
                                # reference to it, keep checking it in case it
                                # gets recreated - bug 94121.
                                all_local_files.append(u)
                    except:
                        log.exception("unexpected error from koIFile.isLocal or koIFile.isFile")
                        continue # skip status update for this file
                set_all_local_urls = set([koIFile.URI for koIFile in all_local_files ])

                # We keep track of all the local files by using the file
                # notificiation service (FNS). We add one directory watcher,
                # for each file Komodo's file service knows about, this can
                # give additional notifications for file's we are not watching,
                # but we gain a speedup due to only having to add one directory
                # watcher (for all files onder that directory) instead of adding
                # one file watcher for each and every file.

                all_local_dirs_dict = collate_directories_from_uris(set_all_local_urls)
                all_monitored_dirs_dict = collate_directories_from_uris(self._monitoredUrls)

                newDirs = set(all_local_dirs_dict.keys()).difference(all_monitored_dirs_dict.keys())
                for diruri in newDirs:
                    # Newly added directories.
                    log.info("Adding directory observer for uri: %r", diruri)
                    try:
                        fileNotificationSvc.addObserver(self, diruri,
                                                        WATCH_DIR,
                                                        FS_NOTIFY_ALL)
                    except COMException, ex:
                        # Likely the path does not exist anymore or this diruri
                        # is somehow invalid.
                        # Ensure we remove all the uris for this directory,
                        # this way if it does come into existance in the
                        # future, we will start monitoring it again.
                        log.info("Could not monitor dir uri: %r", diruri)
                        for uri in all_local_dirs_dict[diruri]:
                            set_all_local_urls.remove(uri)
                        if diruri in all_local_dirs:
                            all_local_dirs.remove(diruri)

                expiredDirs = set(all_monitored_dirs_dict.keys()).difference(all_local_dirs_dict.keys())
                for diruri in expiredDirs:
                    # Removed unused directories.
                    log.info("Removing directory observer for uri: %r", diruri)
                    try:
                        fileNotificationSvc.removeObserver(self, diruri)
                    except COMException, ex:
                        # Likely this diruri is somehow invalid.
                        pass

                # Must keep track of all the local urls we are monitoring, so
                # we can correctly add/remove items in the next process loop.
                self._monitoredUrls = set_all_local_urls

                if not items_to_check:
                    # Fall back to background checking of all files.
                    isBackgroundCheck = (updateReason == self.REASON_BACKGROUND_CHECK)
                    items_to_check = [ (koIFile, koIFile.URI, updateReason) for
                                       koIFile in (all_local_files + all_local_dirs) ]
                    #print "updateStatus reason: Background check"
                else:
                    isBackgroundCheck = False
                    #print "updateStatus reason:"
                    #for item in items_to_check:
                    #    print "%d - %s" % (item[2], item[1])

                log.info("num files to check: %d, isBackgroundCheck: %r",
                         len(items_to_check), isBackgroundCheck)
                #from pprint import pprint
                #pprint([x[1] for x in items_to_check])

                # invalidate old status information
                # we do this seperately so that the scc modules can
                # catch full directories of urls
                last_active_checker_names = active_checker_names
                active_checker_names = []
                for checker in self._statusCheckers:
                    #print "checker: %s - %s, active: %s" % (checker.type, checker.name, checker.isActive())
                    #log.debug("try %s", checker.name)
                    # do we need to run this checker?
                    allowCheckerToRunDisabled = False
                    if not checker.isActive():
                        if checker.name in last_active_checker_names:
                            # We let this go through the status checking once
                            # more in order to clean out any old information.
                            allowCheckerToRunDisabled = True
                            log.debug("%s, not active, allowing last cleanup check.", checker.name)
                        else:
                            log.debug("Skipping %s, not active", checker.name)
                            continue
                    else:
                        active_checker_names.append(checker.name)
                    if isBackgroundCheck and not checker.isBackgroundCheckingEnabled():
                        log.debug("Skipping %s, no background checking",
                                  checker.name)
                        continue

                    # Invalidate paths first so they can be re-cached. This
                    # builds a list of files's that we can actually update.
                    items_need_to_check = []
                    for file_item in items_to_check:
                        koIFile, uri, reason = file_item
                        log.debug("examing %r: uri: %r", checker.name, uri)
                        if not checker.needsToReCheckFileStatus(koIFile,
                                                                reason):
                            log.debug("%s: no need to update yet", checker.name)
                            continue
                        items_need_to_check.append(file_item)
                    #print "  got %d urls" % (len(items_need_to_check))

                    # updated - list of files updated by this status checker
                    updated_items = []

                    for file_item in items_need_to_check:
                        # Between urls, check that we're still running and that
                        # the checker is still enabled.
                        if self.shutdown:
                            log.info("file status thread shutting down")
                            return
                        # Check this between files as it may have changed
                        if not checker.isActive() and \
                           not allowCheckerToRunDisabled:
                            log.debug("Checker %s became disabled mid run.",
                                      checker.name)
                            break

                        koIFile, uri, reason = file_item
                        log.debug("%r updating status of uri: %r",
                                  checker.name, uri)

                        # check the status of the koIFile
                        try:
                            #log.debug("%s checking %s %s", checker.name,koIFile.sccType,uri)
                            # Get the status for the file
                            if not checker.updateFileStatus(koIFile,
                                                            reason):
                                log.debug("%s: no change to %r", checker.name,
                                          uri)
                                continue

                            updated_items.append(file_item)
                            log.debug("%r sending changed notification for: %r",
                                      checker.name, uri)
                            try:
                                if len(updated_items) % 10 == 0:
                                    tmpurllist = [file_item[1] for file_item in updated_items[-10:]]
                                    self.notifyObservers(None, 'file_status', '\n'.join(tmpurllist))
                                    #for uri in tmpurllist:
                                    #    print "  %r changed %r" % (checker.name, uri)
                            except COMException, e:
                                if e.errno == nsError.NS_ERROR_FAILURE:
                                    # noone is listening, we get an exception
                                    pass
                        except Exception, ex:
                            log.exception("Exception checking uri: %r", uri)
                            try:
                                log.exception("Exception detail: %r", ex)
                            except:
                                pass
                        
                    # on every checker we notify, since a particular checker
                    # can take some time
                    if updated_items:
                        try:
                            left = len(updated_items) % 10
                            if left > 0:
                                tmpurllist = [file_item[1] for file_item in updated_items[-left:]]
                                #print "file_status sent for:\n  %s" % ('\n  '.join(tmpurllist), )
                                self.notifyObservers(None, 'file_status', '\n'.join(tmpurllist))
                                #for uri in tmpurllist:
                                #    print "  %r changed %r" % (checker.name, uri)
                        except COMException, e:
                            if e.errno == nsError.NS_ERROR_FAILURE:
                                # noone is listening, we get an exception
                                pass
                        log.info("process:: %s: Notified file_status for uris:\n%s",
                                 checker.name,
                                 "\n".join([file_item[1] for file_item in updated_items]))

            except:
                # Ensure there is no tight infinite loop on the periodic
                # background checking.
                last_bg_check_time = time.time()
                
                # we catch any exception so we can clear our thread variable
                # this allows us to restart the thread again later
                # we re raise the exception
                import traceback
                errmsg = ''.join(traceback.format_exception(*sys.exc_info()))
                log.error('KoFileStatusService thread exception %s', errmsg)
            finally:
                self._processing_done_event.set()

        log.info("file status thread shutting down")
