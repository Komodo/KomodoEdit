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

# An implementation of a file object for Mozilla/xpcom.

from xpcom import components, nsError, ServerException, COMException
from xpcom.server import WrapObject
from xpcom.client import WeakReference
from URIlib import URIParser
import tempfile, os

import logging
log = logging.getLogger('koFileService')

# Temp File support
class koFileService(object):
    _com_interfaces_ = [components.interfaces.koIFileService,
                        components.interfaces.nsIObserver]
    _reg_desc_ = "Komodo File Service Component"
    _reg_contractid_ = "@activestate.com/koFileService;1"
    _reg_clsid_ = "{32129770-2756-4496-A1DF-5218B1CE115F}"
    
    def __init__(self):
        self._files = {}
        self._tmpfiles = {}
        self._uriParser = URIParser()
        self.obsSvc = components.classes["@mozilla.org/observer-service;1"].getService(components.interfaces.nsIObserverService)
        self.obsSvc.addObserver(WrapObject(self,components.interfaces.nsIObserver), "xpcom-shutdown", 0)
        self._fileStatusSvc = None

    @property
    def fileStatusSvc(self):
        if self._fileStatusSvc is None:
            self._fileStatusSvc = components.classes["@activestate.com/koFileStatusService;1"].\
                    getService(components.interfaces.koIFileStatusService)
        return self._fileStatusSvc

    #koIFileEx getFileFromURI(in wstring URI);
    def getFileFromURI(self, uri):
        return self._getFileFromURI(uri)

    def _getFileFromURI(self, uri, doNotification=True):
        # first cleanup the uri by passing it through the parser
        try:
            self._uriParser.URI = uri
            uri = self._uriParser.URI
            
            file = self.findFileByURI(uri)
            if file:
                return file
        
            file = \
                components.classes["@activestate.com/koFileEx;1"] \
                .createInstance(components.interfaces.koIFileEx)
            file.URI = uri
        except Exception, e:
            log.error("Invalid URL parsed: %r", uri)
            raise ServerException(nsError.NS_ERROR_FAILURE, str(e))
        self._files[uri] = WeakReference(file)

        if doNotification:
            forceRefresh = False
            self.fileStatusSvc.updateStatusForFiles([file], forceRefresh)
        
        return file
    
    def getFilesInBaseURI(self, baseURI):
        L = []
        for uri,wr in self._files.items():
            if uri.startswith(baseURI):
                o = wr()
                if o is not None:
                    L.append(o)
                else:
                    try:
                        del self._files[uri]
                    except KeyError, e:
                        # expect this sometimes with weakref
                        pass
        return L
        
    #void getAllFiles([array, size_is(count)] out koIFileEx files,
    #                 out PRUint32 count);
    def getAllFiles(self):
        L = []
        for uri,wr in self._files.items():
            o = wr()
            if o is not None:
                L.append(o)
            else:
                try:
                    del self._files[uri]
                except KeyError, e:
                    # expect this sometimes with weakref
                    pass
        return L
    
    # performance is critical for this function, since it
    # is called by getFileFromURI above, which is called
    # by every partWrapper's constructor
    #koIFileEx findFileByURI(in wstring URI);
    def findFileByURI(self, uri):
        uri = self._uriParser.URI = uri
        if uri in self._files:
            file = self._files[uri]()
            if file:
                return file
            else:
                try:
                    del self._files[uri]
                except KeyError, e:
                    # expect this sometimes with weakref
                    pass
        return None
    
    def deleteTempFile(self, fname, remove_fname = 1):
        if os.path.isfile(fname):
            log.debug("TempFile: Removing '%s'", fname)
            error_message = "no error available"
            try:
                os.unlink(fname)
            except OSError, error_message:
                pass
            if os.path.exists(fname):
                msg = "TempFile: File still exists after deleting '%s' - '%s'" % (fname,error_message)
                if remove_fname:
                    msg += " - flagging for cleanup at shutdown"
                _safeLog(log.warn,msg)
                remove_fname = 0
        if remove_fname:
            try:
                del self._tmpfiles[fname]
            except KeyError:
                _safeLog(log.debug, "TempFile: '%s' is not in the map of temp filenames" % (fname,))
    
    def deleteAllTempFiles(self):
         for fname in self._tmpfiles.keys():
                self.deleteTempFile(fname, 0)
    
    def observe(self, service, topic, extra):
        if topic == "xpcom-shutdown":
            self.deleteAllTempFiles()
    
    def makeTempName(self, suffix):
        ret = tempfile.mktemp(suffix)
        self._tmpfiles[ret] = 1
        return ret
    
    def makeTempNameInDir(self, dir, suffix):
        oldtmp = tempfile.tempdir
        tempfile.tempdir = dir
        fname = self.makeTempName(suffix)
        tempfile.tempdir = oldtmp
        self._tmpfiles[fname] = 1
        return fname

    def makeTempFile(self, suffix, mode):
        fname = self.makeTempName(suffix)
        self._tmpfiles[fname] = 1
        # With doNotification=True, it sends a "file_added" notification to the
        # koFileStatusService, which results in a update status check, which
        # we don't need to happen for just a temporary file.
        # Note: When set True, it can stuff up CVS and SVN commit actions, as
        # the file status service and the commit action occur near
        # simultaneously.
        f = self._getFileFromURI(fname, doNotification=False)
        f.open(mode)
        return f
    
    def makeTempFileInDir(self, dir, suffix, mode):
        fname = self.makeTempNameInDir(dir, suffix)
        # With doNotification=True, it sends a "file_added" notification to the
        # koFileStatusService, which results in a update status check, which
        # we don't need to happen for just a temporary file.
        f = self._getFileFromURI(fname, doNotification=False)
        f.open(mode)
        return f


