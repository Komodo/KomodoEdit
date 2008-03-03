#!/usr/bin/env python

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
# Portions created by ActiveState Software Inc are Copyright (C) 2000-2008
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
import sys
import re

from xpcom import components, ServerException, nsError
from xpcom._xpcom import PROXY_SYNC, PROXY_ALWAYS, PROXY_ASYNC
from xpcom.server import WrapObject

import koprocessutils
import which
import logging

log = logging.getLogger('koTclAppInfo')

# XXX - Copied from koAppInfo, as we cannot import this module because it's
#       in the components directory.
class KoAppInfoEx:
    def __init__(self):
        self.installationPath = ''
        self.executablePath = ''
        self.haveLicense = 0
        self.buildNumber = 0
        self.localHelpFile = ''
        self.webHelpURL = ''
        self._configPath = ''
        self.installed = 0

        self._proxyMgr = components.classes["@mozilla.org/xpcomproxy;1"].\
            getService(components.interfaces.nsIProxyObjectManager)
        self._prefSvc = components.classes["@activestate.com/koPrefService;1"].\
            getService(components.interfaces.koIPrefService)
        self.prefService = self._proxyMgr.getProxyForObject(None,
            components.interfaces.koIPrefService, self._prefSvc,
            PROXY_ALWAYS | PROXY_SYNC)

    def FindInstallationPaths(self):
        return []
    
    def getInstallationPathFromBinary(self, binaryPath):
        return ''
    
    def set_installationPath(self, path):
        self.installationPath = path
        self.executablePath = ''
    
    # pulled over from koIInterpreterLanguageService for BC
    def get_interpreterPath(self):
        return self.get_executablePath()
    
    # pulled over from koIInterpreterLanguageService for BC
    def get_includePath(self):
        return self._configPath

class KoTclInfoEx(KoAppInfoEx):
    _com_interfaces_ = [components.interfaces.koITclInfoEx,
                        components.interfaces.nsIObserver]
    _reg_clsid_ = "06c4f67c-fab1-42c8-8eee-930f760300ca"
    _reg_contractid_ = "@activestate.com/koAppInfoEx?app=Tcl;1"
    _reg_desc_ = "Extended Tcl Information"

    def __init__(self):
        KoAppInfoEx.__init__(self)
        self._initalize_prefs()
        self._userPath = koprocessutils.getUserEnv()["PATH"].split(os.pathsep)
        try:
            self._wrapped = WrapObject(self,components.interfaces.nsIObserver)
            self._prefSvc.prefs.prefObserverService.addObserver(self._wrapped, "tclshDefaultInterpreter", 0)
        except Exception, e:
            print e

    def _initalize_prefs(self):
        globalPrefs = components.classes["@activestate.com/koPrefService;1"].\
                getService(components.interfaces.koIPrefService).prefs
        if not globalPrefs.hasStringPref('tclshDefaultInterpreter'):
            globalPrefs.setStringPref('tclshDefaultInterpreter', '')
        if not globalPrefs.hasStringPref('wishDefaultInterpreter'):
            globalPrefs.setStringPref('wishDefaultInterpreter', '')

    def observe(self, subject, topic, data):
        if topic == "tclshDefaultInterpreter":
            self.installationPath = None

    def get_executablePath(self):
        # XXX invoke interpreters has logic for using wish, do we need
        # it here also?
        if not self.installationPath:
            tclExe = self.prefService.prefs.\
                     getStringPref("tclshDefaultInterpreter")
            if tclExe: return tclExe
            paths = self.FindInstallationPaths()
            if not paths:
                return None
            self.installationPath = paths[0]
        assert self.installationPath is not None

        if sys.platform.startswith("win"):
            return os.path.join(self.installationPath, "tclsh.exe")
        else:
           return os.path.join(self.installationPath, "bin", "tclsh")

    def _getTclshExeName(self):
        if sys.platform.startswith('win'):
            return 'tclsh.exe'
        else:
            return 'tclsh'

    def _getWishExeName(self):
        if sys.platform.startswith('win'):
            return 'wish.exe'
        else:
            return 'wish'

    # koIAppInfoEx routines
    def FindInstallationPaths(self):
        if sys.platform.startswith('win'):
            exts = ['.exe']
        else:
            exts = None
        tclshs = which.whichall("tclsh", exts=exts, path=self._userPath)
        installPaths = [self.getInstallationPathFromBinary(tclsh)\
                        for tclsh in tclshs]
        uniqueInstallPaths = {}
        for installPath in installPaths:
            uniqueInstallPaths[installPath] = 1
        installPaths = uniqueInstallPaths.keys()
        installPaths.sort()
        return installPaths

    def _isInstallationLicensed(self, installationPath):
        return 1
    
    def get_haveLicense(self):
        return self._isInstallationLicensed(self.installationPath)

    def get_version(self):
        raise ServerException(nsError.NS_ERROR_NOT_IMPLEMENTED)
 
    def get_buildNumber(self):
        raise ServerException(nsError.NS_ERROR_NOT_IMPLEMENTED)
 
    def get_localHelpFile(self):
        """Return a path to a launchable local help file, else return None.
        Windows:
            If there is a 'HKLM\Software\ActiveState\ActiveTcl\<CurVer>\Help'
            and if the identified file exists.
        Linux/Solaris:
            Nada. Just man files, which I don't consider "launchable" in a
            browser context. XXX Perhaps they *are* in Nautilus? 
        """
        if sys.platform.startswith("win"):
            import _winreg
            # get the base ActiveTcl registry key
            try:
                activeTclKey = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE,
                                               "SOFTWARE\\ActiveState\\ActiveTcl")
            except EnvironmentError:
                return None
            # get a list of each installed version 
            versions = []
            index = 0
            while 1:
                try:
                    versions.append(_winreg.EnumKey(activeTclKey, index))
                except EnvironmentError:
                    break
                index += 1
            # try to find a existing help file (prefering the latest
            # installed version)
            versions.sort()
            versions.reverse()
            for version in versions:
                try:
                    helpFileKey = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE,
                        "SOFTWARE\\ActiveState\\ActiveTcl\\%s\\Help" % version)
                    helpFile, keyType = _winreg.QueryValueEx(helpFileKey, "")
                    if os.path.isfile(helpFile):
                        return helpFile
                except EnvironmentError:
                    pass
        return None

    def get_webHelpURL(self):
        return "http://aspn.activestate.com/ASPN/Products/ASPNTOC-ACTIVETCL_"

    def getInstallationPathFromBinary(self, binaryPath):
        return os.path.dirname(os.path.dirname(binaryPath))

    def selectDefault(self):
        paths = self.FindInstallationPaths()
        
        for installationPath in paths: 
            if self._isInstallationLicensed(installationPath):
                self.installationPath = installationPath
                return 1
        
        # Otherwise use whatever is left
        if paths:
            self.installationPath = paths[0]
            return 1
        else:
            self.installationPath = None
            return 0
            
    def get_tclsh_path(self):
        if not self.installationPath and not self.selectDefault():
            return None
        exe = os.path.join(self.installationPath, "bin",
                            self._getTclshExeName())
        if exe and os.path.exists(exe):
            return exe
        return None
        
    def get_wish_path(self):
        if not self.installationPath and not self.selectDefault():
            return None
        exe = os.path.join(self.installationPath, "bin",
                            self._getWishExeName())
        if exe and os.path.exists(exe):
            return exe
        return None
