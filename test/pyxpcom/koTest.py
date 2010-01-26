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

    def __getExtensionDirs(self):
        paths = []
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
        return paths
        
    def getFiles(self, prop):
        paths = []
        if prop == "XREExtDL":  # XRE extension dirs list
            paths = self.__getExtensionDirs()
        elif prop == "ComsDL":  # extension/component dirs list
            extension_paths = self.__getExtensionDirs()
            for ext_dir in extension_paths:
                p = join(ext_dir, "components")
                if isdir(p):
                    paths.append(p)
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

        # Ensure that the Komodo profile directories exist. This is normally
        # done by the Komodo xre_main handling, which does not get called
        # when running the pyxpcom tests. Without this, some Komodo xpcom
        # services (like the koIHistory service) will fail.
        koDirSvc = components.classes["@activestate.com/koDirs;1"].getService()
        currUserDataDir = koDirSvc.userDataDir
        if not os.path.exists(currUserDataDir):                 # 5.2
            if not os.path.exists(dirname(currUserDataDir)):    # KomodoIDE
                os.mkdir(dirname(currUserDataDir))
            os.mkdir(currUserDataDir)

        # Register the test directory provider, to pick up the slack from
        # the nsXREDirProvider not having been registered.
        dirSvc = components.classes["@mozilla.org/file/directory_service;1"] \
            .getService(components.interfaces.nsIDirectoryService)
        dirSvc.registerProvider(KoTestDirectoryProvider())

        self.__initialized = True

