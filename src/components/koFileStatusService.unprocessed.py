#!python
# Copyright (c) 2000-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.
#
# Shane Caraveo
#
# Provide file status information
# runs background thread to periodicaly update status on a file
# has plugin capability to add new types of status retreivers, i.e.
# (CVS, Perforce, Subversion)
#
# the status service gets all file information from the
# file service, and updates it with scc information
#
# observer notifications:
#   file_status (url)
#   file_status_updated (None)
#
# when a file status changes, the service sends a notification file_status_update.
# any observer that listens for this will receive the url of the file that has
# been updated.  It must then call back to the service to get the status
# array.
#

import os
import sys
import time
import stat
import string
import logging
import threading
import copy
from pprint import pprint

from xpcom import components, nsError, ServerException, COMException
from xpcom._xpcom import PROXY_SYNC, PROXY_ALWAYS, PROXY_ASYNC
from xpcom.server import WrapObject, UnwrapObject

import koprocessutils
import timeline
import uriparse

log = logging.getLogger('koFileStatusService')
#log.setLevel(logging.DEBUG)

def sortFileStatus(a, b):
    if a.isDirectory and not b.isDirectory:
        return 1
    if b.isDirectory and not a.isDirectory:
        return -1
    return cmp(a.URI,b.URI)

class KoFileStatusService:
    _com_interfaces_ = [components.interfaces.koIFileStatusService, components.interfaces.nsIObserver]
    _reg_clsid_ = "{20732408-43DA-4ca2-BC9F-B82437A3CB2B}"
    _reg_contractid_ = "@activestate.com/koFileStatusService;1"
    _reg_desc_ = "Komodo File Status Service"

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
        
        # set up data cache
        self._urllist = {}
        self._statusCheckers = []
        self.shutdown = 0
        self._continue = 0
        self._background = 0
        self._diskChecker = None
        
        # set up the background thread
        self._thread = None
        self._tlock = threading.Lock()
        self._cv = threading.Condition()
        self._shutdown = threading.Condition()
        timeline.leave('koFileStatusService.__init__')

    def init(self):
        timeline.enter('koFileStatusService.init')

        self._observerSvc.addObserver(self, "file_changed",0)
        self._observerSvc.addObserver(self, "file_status_now",0)
        self._observerSvc.addObserver(self, "file_update_now",0)
        self._observerSvc.addObserver(self, 'xpcom-shutdown', 1)
        
        self._fileSvc.observerService.addObserver(self,'',0)
        
        self._diskChecker = KoDiskFileChecker()
        self._statusCheckers.append(self._diskChecker)
        
        for checker in self._statusCheckers:
            self._globalPrefs.prefObserverService.addObserver(self,checker.enabledPrefName,0)
            self._globalPrefs.prefObserverService.addObserver(self,checker.backgroundPrefName,0)

        self._tlock.acquire()
        self._thread = threading.Thread(target = KoFileStatusService._process,
                                        name = "File Status Service",
                                        args = (self,))
        self._thread.start()
        self._tlock.release()
        timeline.leave('koFileStatusService.init')

    def _removeObserver(self, topic):
        try:
            self._observerSvc.removeObserver(self, topic)
        except:
            log.debug("Unable to remove observer %s"%topic)

    def unload(self):
        self.shutdown = 1;
        if self._thread.isAlive():
            self._cv.acquire()
            self._cv.notify()
            self._cv.release()
            self._shutdown.acquire()
            self._shutdown.wait(5)
            self._shutdown.release()

        for checker in self._statusCheckers:
            try:
                self._globalPrefs.prefObserverService.removeObserver(self,checker.enabledPrefName)
                self._globalPrefs.prefObserverService.removeObserver(self,checker.backgroundPrefName)
            except:
                # prefs shutdown already?
                log.debug("Unable to remove prefs observers")
    
        self._removeObserver("file_changed")
        self._removeObserver("file_status_now")
        self._removeObserver("file_update_now")

        try:
            self._fileSvc.observerService.removeObserver(self,'')
        except:
            # file service shutdown before us?
            log.debug("Unable to remove file service observers")
    
    def notifyError(self, error, detail):
        # XXX 'scc_status_message' is evil (see bug 20568). In addition, it
        #     is poorly named because the code is structured such that the
        #     non-scc checkers here could set an error.
        if error:
            #print "attempting to send notification"
            try:
                self._observerProxy.notifyObservers(error, 'scc_status_message', detail)
            except COMException, e:
                pass
        
    def notifyWarning(self, warningTitle, warningDetail):
        # XXX 'scc_status_message' is evil (see bug 20568).
        warning = components.classes["@activestate.com/koStatusMessage;1"]\
                .createInstance(components.interfaces.koIStatusMessage)
        warning.category = "scc_warning_message"
        warning.msg = warningTitle
        warning.timeout = 5000
        warning.highlight = 1
        #print "attempting to send scc warning notification"
        try:
            self._observerProxy.notifyObservers(warning, 'scc_status_message', warningDetail)
        except COMException, e:
            pass
        
    def _getFileStatusNow(self, URI, forceRefresh=False):
        url = self._fileSvc.getFileFromURI(URI)
        self._getFileStatusNowWithFile(url, forceRefresh)
    
    def _getFileStatusNowWithFile(self, url, forceRefresh=False):
        url = UnwrapObject(url)
        lasterror = None
        # force an update to the status
        urllist = self._fileSvc.getFilesInBaseURI(url.URI)
        urllist = [UnwrapObject(_url) for _url in urllist]
        for checker in self._statusCheckers:
            if not checker.isActive():
                continue
            if checker.executablePrefName:
                checker.setExecutable(self._globalPrefs.getStringPref(checker.executablePrefName))

            if checker.scc and (not url.isLocal or \
                (url.sccDirType and url.sccDirType != checker.scc) or\
                (url.sccType and url.sccType != checker.scc)):
                continue

            # invalidate all the url's if it's a directory
            checker.invalidatePath(url,1)

            # Clear the paths checked from previous run
            checker.clearRunStatusHistory()

            # No warnings or errors yet
            checker.warning = None
            checker.error = None

            # only check for the primary url.  if it is a directory
            # getFileStatus will get status for all files in that
            # directory, but not recursivly
            checker.getFileStatus(url, not url.isDirectory,
                                  forceRefresh=forceRefresh)
            if checker.error and (not lasterror or checker.error.msg != lasterror.msg):
                lasterror = checker.error
                self.notifyError(checker.error,checker.error_detail)
                checker.error = None
            else:
                if checker.warning:
                    self.notifyWarning(checker.warning, checker.warning_detail)
                    checker.warning = None
                # reset the status indicators
                # we don't do error checking here, these are associated uri's
                for _url in urllist:
                    if _url != url:
                        checker.getFileStatus(_url, not _url.isDirectory,
                                              forceRefresh=forceRefresh)
                    #else:
                    #    print "Not running getFileStatus() twice for the same url"
        
        # send notifications of status updates
        for _url in urllist:
            try:
                self._observerSvc.notifyObservers(_url, 'file_status', _url.URI)
            except COMException, e:
                if e.errno == nsError.NS_ERROR_FAILURE:
                    # if noone is listening, we get an exception
                    pass
                else:
                    #print "caught unknown exception in notify"
                    raise
        try:
            self._observerSvc.notifyObservers(self, 'file_status_updated',None)
        except COMException, e:
            if e.errno == nsError.NS_ERROR_FAILURE:
                # if noone is listening, we get an exception
                pass
            else:
                #print "caught unknown exception in notify"
                raise

    def getStatusForFile(self, kofile, forceRefresh):
        #print "getStatusForFile: %r" % (kofile.URI)
        self._getFileStatusNowWithFile(kofile, forceRefresh)

    def getStatusForUri(self, URI, forceRefresh):
        #print "getStatusForUri: %r" % (URI)
        self._getFileStatusNow(URI, forceRefresh)

    def isRepository(self, URI):
        url = self._fileSvc.getFileFromURI(URI)
        if not url or not url.isLocal or not url.exists:
            return ''
        
        if url.sccType:
            return url.sccType
        if url.sccDirType:
            return url.sccDirType
            
        for checker in self._statusCheckers:
            if not checker.isActive() or not checker.scc:
                continue
            if checker.isRepository(url.path):
                return checker.scc

        return ''
    
    # nsIObserver interface
    def observe(self, subject, topic, data):
        log.debug("status observer received %s:%s"%(topic,data))
        if topic == 'xpcom-shutdown':
            log.debug("file status got xpcom-shutdown, unloading");
            self.unload()
            return

        if topic == self._globalPrefs.id:
            # url is actually the pref name that was changed
            for checker in self._statusCheckers:
                if data == checker.enabledPrefName or \
                   data == checker.backgroundPrefName:
                    enabled = self._globalPrefs.getBooleanPref(checker.enabledPrefName)
                    background = self._globalPrefs.getBooleanPref(checker.backgroundPrefName)
                    if enabled != checker.enabled or background != checker.background:
                        checker.enabled = enabled
                        checker.background = background
                        self._cv.acquire()
                        self._cv.notify()
                        self._cv.release()
                        break
            # we don't continue in this observer for pref changes
            return
        
        elif topic == "file_status_now":
            #_url.update = 0
            self._getFileStatusNow(data)
            return
        elif topic == "file_changed":
            _url = self._fileSvc.getFileFromURI(data)
            _url = UnwrapObject(_url)
            _url.update = 0
            _url.dofileupdate = 1
        # These are other possible topics, they just force the
        # file status service to update itself immediately
        #elif topic == "file_added":
        #elif topic == "file_update_now":

        self._cv.acquire()
        # notify is an immediate release, but we want the thread
        # to continue until there is no more activity, so we flag
        # it to do so
        self._continue = 1
        self._cv.notify()
        self._cv.release()

    def _process(self):
        #print "starting file status background thread"
        urllist = []
        lasterror = None
        while 1:
            try:
                # if we have more url's than we checked last
                # time, lets do them now so the user doesn't
                # have to wait 30 seconds
                if not self._continue:
                    self._cv.acquire()
                    self._cv.wait(30)
                    # if self._continue is set, this is not a timeout
                    self._background = not self._continue
                    self._cv.release()
                # reset flag, see Observer for more info
                self._continue = 0
                
                if self.shutdown:
                    self._shutdown.acquire()
                    self._shutdown.notify()
                    self._shutdown.release()
                    log.info("file status thread shutting down")
                    return
                
                #print "doing file status update"
                urllist = self._fileSvc.getAllFiles()
                urllist = [UnwrapObject(_url) for _url in urllist]
                # all_updated - set of files updated by any status checker
                all_updated_urls = set()

                start = time.time()
                
                # invalidate old status information
                # we do this seperately so that the scc modules can
                # catch full directories of urls
                for checker in self._statusCheckers:
                    # updated - list of files updated by this status checker
                    updated = []
                    #print "checker: %s - %s, active: %s" % (checker.type, checker.name, checker.isActive())
                    #log.debug("try %s"%checker.scc)
                    # do we need to run this checker?
                    if not checker.isActive():
                        #log.debug("Skipping %s, not active"%checker.scc)
                        continue
                    if checker.executablePrefName:
                        checker.setExecutable(self._globalPrefs.getStringPref(checker.executablePrefName))
                    checker.background = self._globalPrefs.getBooleanPref(checker.backgroundPrefName)
                    checker.recursive = checker.recursivePrefName and self._globalPrefs.getBooleanPref(checker.recursivePrefName)
                    checker.duration = self._globalPrefs.getLongPref(checker.durationPrefName)
                    if self._background and not checker.background:
                        #log.debug("Skipping %s, no background checking"%checker.scc)
                        continue
                    
                    # We start off with nothing already checked for this checker
                    checker.clearRunStatusHistory()

                    urls = []
                    # invalidate paths first so they can be re-cached.
                    # build a list of url's that we can actually update
                    for url in urllist:
                        if url.isLocal and (url.update == 0 or \
                           (checker.background and checker.invalidatePath(url))):
                            # if this file is marked to have scc, and it's scc does
                            # not match the checker, then skip passing the file to the checker
                            if not checker.scc or (checker.scc and \
                                ((url.sccType and (url.sccType == checker.scc)) or \
                                (not url.sccDirType or (url.sccDirType == checker.scc)))):
                                urls.append(url)
                            #else:
                            #    log.debug('skipping %s, type [%s] dirType [%s]'%(url.URI, url.sccType, url.sccDirType))

                    urls.sort(sortFileStatus)
                    for url in urls:
                        # if we're in process, but a shutdown is requested, do it
                        if self.shutdown:
                            self._shutdown.acquire()
                            self._shutdown.notify()
                            self._shutdown.release()
                            #log.debug("status thread shutting down")
                            log.info("file status thread shutting down")
                            return

                        # Check this between urls as it may have changed
                        if not checker.enabled:
                            #log.debug("Skipping %s, not enabled"%checker.scc)
                            break

                        # check the status of the url
                        done = 0
                        #print "url time is %d, now is %d" %(self._urllist[url].update, time.time())
                        
                        try:
                            #log.debug("%s checking %s %s" %(checker.scc,url.sccType,url.URI))
                            oldscc = copy.deepcopy(url.scc)
                            oldstat = copy.deepcopy(url.stats)
                            
                            if url.dofileupdate:
                                checker.invalidatePath(url,force=1)
                                
                            if not checker.getFileStatus(url, url.dofileupdate,
                                                         forceRefresh=False):
                                if checker.error and (not lasterror or checker.error.msg != lasterror.msg):
                                    lasterror = checker.error
                                    self.notifyError(checker.error,checker.error_detail)
                                    checker.error = None
                                #log.debug("Check Failed %s %s"%(checker.scc,checker.error))
                                continue
                            # this avoids making the notification below if the status has
                            # not changed.  The notification interupts and updates the UI
                            # taking an enormous amount of cpu usage
                            if oldscc == url.scc and \
                                oldstat == url.stats: continue
                            updated.append(url)
    
                            try:
                                if len(updated) % 10 == 0:
                                    tmpurllist = [u.URI for u in updated[-10:]]
                                    self._observerProxy.notifyObservers(None, 'file_status',
                                                                        string.join(tmpurllist, '\n'))
                            except COMException, e:
                                if e.errno == nsError.NS_ERROR_FAILURE:
                                    # noone is listening, we get an exception
                                    pass
                        except Exception, e:
                            log.exception("Unknown Exception %s" % repr(e))
                        
                    # on every checker we notify, since a particular checker
                    # can take some time
                    if updated:
                        try:
                            left = len(updated) % 10
                            if left > 0:
                                tmpurllist = [u.URI for u in updated[left * -1:]]
                                self._observerProxy.notifyObservers(None, 'file_status',
                                                                    string.join(tmpurllist, '\n'))
                        except COMException, e:
                            if e.errno == nsError.NS_ERROR_FAILURE:
                                # noone is listening, we get an exception
                                pass
                        try:
                            # this call is proxied to the UI thread.  The trees are invalidated
                            # in the observer for this call
                            self._observerProxy.notifyObservers(self, 'file_status_updated',None)
                        except COMException, e:
                            if e.errno == nsError.NS_ERROR_FAILURE:
                                # noone is listening, we get an exception
                                pass
                        all_updated_urls.update(updated)
                
                lasterror = None
                
                for url in urls:
                    url.dofileupdate = 0
                        
                end =  time.time()
                for url in all_updated_urls:
                    url.update = end

                for url in urllist:
                    if url.update == 0:
                        url.update = end
            except:
                # we catch any exception so we can clear our thread variable
                # this allows us to restart the thread again later
                # we re raise the exception
                import traceback
                errmsg = ''.join(traceback.format_exception(*sys.exc_info()))
                log.error('KoFileStatusService thread exception %s' % errmsg)

        log.info("file status thread shutting down")

class KoFileCheckerBase:
    def __init__(self):
        self.type = None
        self.name = "File checker base"
        self.scc = None
        self.duration = 15
        self.durationPrefName = None
        self.enabledPrefName = None
        self.enabled = 0
        self.backgroundPrefName = None
        self.background = 0
        self.recursivePrefName = None
        self.recursive = 0
        self.error = None
        self.error_detail = None
        self.warning = None
        self.warning_detail = None
        self.executable = None
        self.executablePrefName = None
        # _runStatusHistory is what has been processed already by this checker.
        # The paths that have been checked will be placed into this dictionary,
        # if the path has been already checked, then there is no need to check
        # it again. This should be cleared every background run by the file
        # status checker.
        self._runStatusHistory = {}
        self._globalPrefs = components.classes["@activestate.com/koPrefService;1"].\
            getService(components.interfaces.koIPrefService).prefs
    
    def setExecutable(self, executable):
        self.executable = executable
        
    def setError(self, msg='', detail=''):
        self.error = None
        if not msg: return
        
        self.error = components.classes["@activestate.com/koStatusMessage;1"]\
                .createInstance(components.interfaces.koIStatusMessage)
        self.error.category = "scc_error_message"
        self.error.msg = msg
        self.error.timeout = 5000
        self.error.highlight = 1
        self.error_detail = str(detail)
    
    def setWarning(self, msg='', detail=''):
        self.warning = msg
        self.warning_detail = detail
    
    def isRepository(self, path):
        return 0
    
    def isActive(self):
        self.enabled = self._globalPrefs.getBooleanPref(self.enabledPrefName)
        return self.enabled

    def invalidatePath(self, url,force=0):
        return 0

    def getFileStatus(self, url, dofile=1, forceRefresh=False):
        return None

    def clearRunStatusHistory(self):
        self._runStatusHistory = {}

class KoDiskFileChecker(KoFileCheckerBase):
    def __init__(self):
        timeline.enter('KoDiskFileChecker.__init__')
        KoFileCheckerBase.__init__(self)
        self.type = 'disk'
        self.name = "Disk"
        self.durationPrefName = 'diskBackgroundMinutes'
        self.enabledPrefName = 'diskStatusEnabled'
        self.backgroundPrefName = 'diskBackgroundCheck'
        timeline.leave('KoDiskFileChecker.__init__')

    def invalidatePath(self, url,force=0):
        return force or url.update < time.time() - (self.duration * 60)

    def getFileStatus(self, url, dofile=1, forceRefresh=False):
        self.setError()
        changed = url.hasChanged
        # we mark dofileupdate to force
        # an scc update to occure
        if changed:
            url.dofileupdate = 1
        return changed

