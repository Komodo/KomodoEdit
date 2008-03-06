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
from xpcom._xpcom import PROXY_SYNC, PROXY_ALWAYS, PROXY_ASYNC
from xpcom.server import UnwrapObject

import timeline
from fileStatusUtils import KoDiskFileChecker

log = logging.getLogger('koFileStatusService')
#log.setLevel(logging.DEBUG)


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

class KoFileStatusService:
    _com_interfaces_ = [components.interfaces.koIFileStatusService,
                        components.interfaces.nsIObserver,
                        components.interfaces.koIFileNotificationObserver]
    _reg_clsid_ = "{20732408-43DA-4ca2-BC9F-B82437A3CB2B}"
    _reg_contractid_ = "@activestate.com/koFileStatusService;1"
    _reg_desc_ = "Komodo File Status Service"

    monitoredFileNotifications = ("file_update_now", "file_status_now",
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
                log.exception("Unable to load %r status checker: %r", name, cid)

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
                # File was deleted, remove it from our list of paths checked.
                # The file notification system observer automatically removes
                # our observer for this file. The uri may not be yet monitored
                # through the file status service though:
                #   http://bugs.activestate.com/show_bug.cgi?id=72865
                if uri in self._monitoredUrls:
                    self._monitoredUrls.remove(uri)
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

    ##
    # Stop listening to a file notification
    # @private
    def _removeObserver(self, topic):
        try:
            self._observerSvc.removeObserver(self, topic, 0)
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
    
        for notification in self.monitoredFileNotifications:
            self._removeObserver(notification)

        try:
            self._fileSvc.observerService.removeObserver(self,'')
        except:
            # file service shutdown before us?
            log.debug("Unable to remove file service observers")

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

    def updateStatusForFiles(self, koIFiles, forceRefresh):
        self._cv.acquire()
        try:
            reason = self.REASON_FILE_CHANGED
            if forceRefresh:
                reason = self.REASON_FORCED_CHECK
            for koIFile in koIFiles:
                uri = koIFile.URI
                self._items_to_check.add((UnwrapObject(koIFile), uri, reason))
                log.debug("Forced recheck of uri: %r", uri)
            self._cv.notify()
        finally:
            self._cv.release()

    def updateStatusForUris(self, uris, forceRefresh):
        koIFiles = map(self._fileSvc.getFileFromURI, uris)
        self.updateStatusForFiles(koIFiles, forceRefresh)

    ##
    # These two have been deprecated in favour of the two functions above.
    #
    def getStatusForFile(self, koIFile, forceRefresh, reportWarning=True):
        import warnings
        warnings.warn("koIFileStatusService.getStatusForFile() is deprecated, "
                      "use updateStatusForFiles instead.",
                      DeprecationWarning)
        self.updateStatusForFiles([koIFile], forceRefresh)
    def getStatusForUri(self, URI, forceRefresh):
        import warnings
        warnings.warn("koIFileStatusService.getStatusForUri() is deprecated, "
                      "use updateStatusForUris instead.",
                      DeprecationWarning)
        self.updateStatusForUris([URI], forceRefresh)

    def _process(self):
        #print "starting file status background thread"
        last_bg_check_time = time.time()
        while not self.shutdown:
            try:
                # Initialize the working variables, this ensures we don't hold
                # on to any koIFileEx references between runs, allowing the
                # koIFileEx items to be properly garbage collected. See bug:
                # http://bugs.activestate.com/show_bug.cgi?id=68285
                all_local_files = None
                file_item = None
                items_to_check = None
                koIFile = None
                set_all_local_urls = None
                updated_items = None

                self._cv.acquire()
                try:
                    # Run every 31 seconds, but if there are already more
                    # items to check, process them straight away.
                    time_till_next_run = 31 - (time.time() - last_bg_check_time)
                    if not self._items_to_check and \
                       self._updateReason == self.REASON_BACKGROUND_CHECK and \
                       time_till_next_run > 0:
                        self._cv.wait(time_till_next_run)
                    items_to_check = list(self._items_to_check)
                    if not items_to_check:
                        last_bg_check_time = time.time()
                    self._items_to_check = set()
                    # Sort the items.
                    items_to_check.sort(sortFileStatus)
                    # Get the default update reason. Is set by
                    # a direct call to updateStatusForAllFiles.
                    updateReason = self._updateReason
                    self._updateReason = self.REASON_BACKGROUND_CHECK
                finally:
                    self._cv.release()

                if self.shutdown:
                    log.info("file status thread shutting down")
                    return

                # Maintenance cleanup and addition of observed files.
                #print "doing file status update"
                # XXX - Do we really need to unwrap these puppies?
                all_local_files = []
                for koIFile in self._fileSvc.getAllFiles():
                    try:
                        if koIFile.isLocal and koIFile.isFile:
                            all_local_files.append(UnwrapObject(koIFile))
                    except:
                        log.exception("unexpected error from koIFile.isLocal or koIFile.isFile")
                        continue # skip status update for this file
                set_all_local_urls = set([koIFile.URI for koIFile in all_local_files ])
                for uri in set_all_local_urls.difference(self._monitoredUrls):
                    # Newly added files.
                    log.debug("Adding a file observer for uri: %r", uri)
                    try:
                        self._fileNotificationSvc.addObserver(self, uri,
                                                              self.FNS_WATCH_FILE,
                                                              self.FNS_NOTIFY_ALL)
                    except COMException, ex:
                        # Likely the path does not exist anymore.
                        # Ensure we remove the uri, this way if it does come
                        # into existance, we can start monitoring it again.
                        log.debug("Could not monitor file uri: %r", uri)
                        set_all_local_urls.remove(uri)
                for uri in self._monitoredUrls.difference(set_all_local_urls):
                    # Removed unused files.
                    self._fileNotificationSvc.removeObserver(self, uri)
                self._monitoredUrls = set_all_local_urls

                if not items_to_check:
                    # Fall back to background checking of all files.
                    isBackgroundCheck = (updateReason == self.REASON_BACKGROUND_CHECK)
                    items_to_check = [ (koIFile, koIFile.URI, updateReason) for
                                       koIFile in all_local_files ]
                    #print "updateStatus reason: Background check"
                else:
                    isBackgroundCheck = False
                    #print "updateStatus reason:"
                    #for item in items_to_check:
                    #    print "%d - %s" % (item[2], item[1])

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
                            log.debug("%r sending changed notification for: %r",
                                      checker.name, uri)
                            try:
                                if len(updated_items) % 10 == 0:
                                    tmpurllist = [file_item[1] for file_item in updated_items[-10:]]
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
                                tmpurllist = [file_item[1] for file_item in updated_items[-left:]]
                                #print "file_status sent for:\n  %s" % ('\n  '.join(tmpurllist), )
                                self._observerProxy.notifyObservers(None, 'file_status',
                                                                    '\n'.join(tmpurllist))
                        except COMException, e:
                            if e.errno == nsError.NS_ERROR_FAILURE:
                                # noone is listening, we get an exception
                                pass
                
                #for koIFile in files:
                #    koIFile.dofileupdate = 0

            except:
                # Ensure there is no tight infinite loop on the periodic
                # background checking.
                last_bg_check_time = time.time()
                
                # we catch any exception so we can clear our thread variable
                # this allows us to restart the thread again later
                # we re raise the exception
                import traceback
                errmsg = ''.join(traceback.format_exception(*sys.exc_info()))
                log.error('KoFileStatusService thread exception %s' % errmsg)

        log.info("file status thread shutting down")
