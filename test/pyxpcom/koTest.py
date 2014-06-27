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

from xpcom import components, ServerException, nsError, COMException
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
            "XpcomLib", components.interfaces.nsIFile).path
        extensionsDirs = [join(dirname(componentsDir), "extensions"),
                          join(dirname(componentsDir), "distribution", "bundles")]
        for extensionsDir in extensionsDirs:
            try:
                for f in os.listdir(extensionsDir):
                    p = join(extensionsDir, f)
                    if isdir(p):
                        paths.append(p)
                    else:
                        try:
                            with open(p, "r") as p_data:
                                p = p_data.read().strip()
                                if isdir(p):
                                    paths.append(p)
                        except:
                            pass
            except EnvironmentError:
                # The extensions dir may not exist yet.
                pass
        return paths

    def getFiles(self, prop):
        paths = []
        if prop == "PyxpcomExtDirList":  # Pyxpcom standalone extension dirs
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
    _com_interfaces_ = [components.interfaces.koITestService,
                        components.interfaces.nsIXULAppInfo,
                        components.interfaces.nsIXULRuntime]
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
        try:
            os.makedirs(currUserDataDir)
        except OSError:
            if not os.path.isdir(currUserDataDir):
                raise

        # Register the test directory provider, to pick up the slack from
        # the nsXREDirProvider not having been registered.
        dirSvc = components.classes["@mozilla.org/file/directory_service;1"] \
            .getService(components.interfaces.nsIDirectoryService)
        provider = KoTestDirectoryProvider()
        dirSvc.registerProvider(provider)

        # register components from the extensions (so we can test them)
        enum = provider.getFiles("PyxpcomExtDirList")
        while enum.hasMoreElements():
            d = enum.getNext()
            if os.path.split(d.path)[-1].lower() == "publishing@activestate.com":
                # skip publishing, that causes excessive errors during tests
                # because it gets created on the wrong thread
                continue
            f = d.clone()
            f.append("pylib")
            if f.exists():
                sys.path.append(f.path)
            f = d.clone()
            f.append("chrome.manifest")
            if f.exists():
                components.registrar.autoRegister(f)

        # Register the app info stuff
        appinfo = components.classes["@mozilla.org/xre/app-info;1"] \
                            .getService(components.interfaces.nsIXULRuntime)
        try:
            appinfo.QueryInterface(components.interfaces.nsIXULAppInfo)
        except COMException, e:
            if e.errno != nsError.NS_ERROR_NO_INTERFACE:
                raise
            # need to register our own app info
            self._appinfo = appinfo
            import types
            iim = components.interfaceInfoManager
            nsISupports = iim.GetInfoForName("nsISupports")
            nsIXULRuntime = iim.GetInfoForName("nsIXULRuntime")
            # skip QueryInterface, AddRef, and Release
            for i in range(nsISupports.GetMethodCount(), nsIXULRuntime.GetMethodCount()):
                name = nsIXULRuntime.GetMethodInfo(i)[1]
                if isinstance(getattr(appinfo, name), types.MethodType):
                    # just stash the bound method over
                    setattr(self, name, getattr(appinfo, name))
                else:
                    # assume property and make getters and setters
                    def prop(p):
                        getter = lambda self: getattr(self._appinfo, p, None)
                        setter = lambda self, v: setattr(self._appinfo, p, v)
                        setattr(KoTestService, p, property(getter, setter))
                    prop(name) # force binding

            components.registrar.registerFactory(self._reg_clsid_,
                                                 self._reg_desc_,
                                                 "@mozilla.org/xre/app-info;1",
                                                 None)
            self._infoSvc = components.classes["@activestate.com/koInfoService;1"]\
                .getService(components.interfaces.koIInfoService)
        self.__initialized = True

    # nsIXULAppInfo
    vendor = "ActiveState"
    @property
    def name(self):
        return "Komodo %s" % (self._infoSvc.prettyProductType)
    ID = "{dca9ceb7-9e48-47d5-84a1-a2623764b4cb}"
    @property
    def version(self):
        return self._infoSvc.version
    @property
    def appBuildID(self):
        return self._infoSvc.appBuildID
    platformVersion = "0"
    platformBuildID = ""
