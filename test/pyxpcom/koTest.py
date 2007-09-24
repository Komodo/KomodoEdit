#!python
# Copyright (c) 2007 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.


import os
from os.path import isdir, dirname, join, isfile, normpath
import sys
import re
import logging

from xpcom import components, ServerException, nsError
from xpcom.server.enumerator import SimpleEnumerator

log = logging.getLogger("koTest")


#---- component implementation

class KoTestDirectoryProvider:
    _com_interfaces_ = [components.interfaces.nsIDirectoryServiceProvider,
                        components.interfaces.nsIDirectoryServiceProvider2]
    _reg_clsid_ = "{12e2e502-ccb3-4d92-985a-28a0c24cf7f2}"
    _reg_contractid_ = "@activestate.com/koTestDirectoryProvider;1"
    _reg_desc_ = "Komodo Test Directory Provider"

    def __init__(self):
        self._dirSvc = components.classes["@mozilla.org/file/directory_service;1"] \
            .getService(components.interfaces.nsIProperties)
    
    def getFile(self, prop):
        path = None
        persistent = True
        raise ServerException(nsError.NS_ERROR_FAILURE)
        
        # http://plow.activestate.com/source/xref/mozilla/1.8/xpcom/io/nsIDirectoryService.idl
        # API is:
        #  int8 getFile(in string prop,
        #               out boolean persistent,
        #               out retval nsISomething file)
        # This translates (I believe, via experimentation) to:
        #   (<file>, <persistent>)
        nsifile = components.classes["@mozilla.org/file/local;1"] \
            .createInstance(components.interfaces.nsILocalFile)
        nsifile.initWithPath(path)
        return nsifile, persistent

    def getFiles(self, prop):
        paths = []
        if prop == "XREExtDL":  # XRE extension dirs list
            componentsDir = self._dirSvc.get(
                "ComsD", components.interfaces.nsIFile).path
            extensionsDir = join(dirname(componentsDir), "extensions")
            try:
                for f in os.listdir(extensionsDir):
                    p = join(extensionsDir, f)
                    if isdir(p):
                        paths.append(p)
            except EnvironmentError:
                # The extensions dir may not exist yet.
                pass
        else:
            raise ServerException(nsError.NS_ERROR_FAILURE)
        
        nsifiles = []
        for path in paths:
            nsifile = components.classes["@mozilla.org/file/local;1"] \
                .createInstance(components.interfaces.nsILocalFile)
            nsifile.initWithPath(path)
            nsifiles.append(nsifile)
        return SimpleEnumerator(nsifiles)


class KoTestService:
    _com_interfaces_ = [components.interfaces.koITestService]
    _reg_clsid_ = "{7f720f03-312f-4d51-8dbe-7701eabd6f0b}"
    _reg_contractid_ = "@activestate.com/koTestService;1"
    _reg_desc_ = "Komodo Test Support Service"

    __initialized = False
    def init(self):
        if self.__initialized:
            return

        # Register the test directory provider, to pick up the slack from
        # the nsXREDirProvider not having been registered.
        dirSvc = components.classes["@mozilla.org/file/directory_service;1"] \
            .getService(components.interfaces.nsIDirectoryService)
        dirSvc.registerProvider(KoTestDirectoryProvider())

        self.__initialized = True

