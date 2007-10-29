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

import copy
import pprint
import os
import logging
log = logging.getLogger('koKeybindingSchemeService')
#log.setLevel(logging.DEBUG)

from xpcom import components, ServerException
from xpcom.server import WrapObject, UnwrapObject

class Scheme:
    _com_interfaces_ = [components.interfaces.koIKeybindingScheme]
    _reg_clsid_ = "{73358FFD-27D3-435A-B89E-C24373AF1807}"
    _reg_contractid_ = "@activestate.com/koKeybindingScheme;1"
    _reg_desc_ = "Keybinding Scheme object"

    def __init__(self, fname, userDefined, unsaved=0):
        self._koDirSvc = components.classes["@activestate.com/koDirs;1"].\
                        getService(components.interfaces.koIDirs)
        self._userSchemeDir = os.path.join(self._koDirSvc.userDataDir, 'schemes')
        namespace = {}
        self.unsaved = unsaved
        self.writeable = userDefined
        if unsaved:
            self.fname = os.path.join(self._userSchemeDir, fname+'.kkf')
            self.name = fname
            self.data = ''
            self.isDirty = 1
        else:
            self.fname = fname
            self.name = os.path.splitext(os.path.basename(fname))[0]
            self.data = open(fname).read()
            self.isDirty = 0

    def revert(self):
        namespace = {}
        self.data = open(self.fname).read()
        self.isDirty = 0

    def clone(self, newname):
        clone = Scheme(newname, 1, 1)
        clone.data = self.data
        schemeService = components.classes['@activestate.com/koKeybindingSchemeService;1'].getService()
        schemeService.addScheme(clone)
        return clone

    def saveAs(self, name):
        if name == "":
            name = "__unnamed__"
        fname = os.path.join(self._userSchemeDir, name+'.ksf')
        if os.path.exists(fname):
            print "Already exists"
            return
        schemeService = components.classes['@activestate.com/koKeybindingSchemeService;1'].getService()
        if self.name == '__unnamed__': # we want to forget about the unnamed one.
            schemeService.removeScheme(self)
        self.name = name
        self.fname = fname
        self.save()
        schemeService.addScheme(self)

    def save(self):
        log.info("Doing save of %r", self.fname)
        f = open(self.fname, 'wt')
        f.write(self.data)
        f.close()
        self.unsaved = 0
        observerSvc = components.classes["@mozilla.org/observer-service;1"].\
                getService(components.interfaces.nsIObserverService);
        observerSvc.notifyObservers(self,'keybinding-scheme-changed', self.name);
        
    def remove(self):
        log.warn("Removing scheme " + self.name)
        schemeService = components.classes['@activestate.com/koKeybindingSchemeService;1'].getService()
        if os.path.exists(self.fname):
            os.remove(self.fname)
        schemeService = components.classes['@activestate.com/koKeybindingSchemeService;1'].getService()
        schemeService.removeScheme(self)

class koKeybindingSchemeService:
    _com_interfaces_ = [components.interfaces.koIKeybindingSchemeService]
    _reg_clsid_ = "{5DEDBA35-45A2-4913-8271-C950CE3C96BE}"
    _reg_contractid_ = "@activestate.com/koKeybindingSchemeService;1"
    _reg_desc_ = "Service used to access, manage and create keybinding  'schemes'"

    def __init__(self):
        self._koDirSvc = components.classes["@activestate.com/koDirs;1"].\
                        getService(components.interfaces.koIDirs)
        self._globalPrefs = components.classes["@activestate.com/koPrefService;1"].\
                            getService(components.interfaces.koIPrefService).prefs
        self._systemSchemeDir = os.path.join(self._koDirSvc.supportDir, 'schemes')
        self._schemes = {}
        #print self._systemSchemeDir, os.path.exists(self._systemSchemeDir)
        if os.path.isdir(self._systemSchemeDir):
            candidates = os.listdir(self._systemSchemeDir)
            schemes = [Scheme(os.path.join(self._systemSchemeDir, candidate), 0) for
                                candidate in candidates if os.path.splitext(candidate)[1] == '.kkf']
            for scheme in schemes:
                self.addScheme(scheme)
        self._userSchemeDir = os.path.join(self._koDirSvc.userDataDir, 'schemes')
        #print self._userSchemeDir
        if not os.path.isdir(self._userSchemeDir):
            os.mkdir(self._userSchemeDir)
        else:
            candidates = os.listdir(self._userSchemeDir)
            schemes += [Scheme(os.path.join(self._userSchemeDir, candidate), 1) for
                                candidate in candidates if os.path.splitext(candidate)[1] == '.kkf']
            for scheme in schemes:
                self.addScheme(scheme)
        if self._globalPrefs.hasStringPref('keybinding-configuration'):
            oldstyleScheme = self._globalPrefs.getStringPref('keybinding-configuration')
            currentScheme = oldstyleScheme[oldstyleScheme.index(': ')+2:]
            self._globalPrefs.setStringPref('keybinding-scheme', currentScheme)
            self._globalPrefs.deletePref('keybinding-configuration')
        else:
            currentScheme = self._globalPrefs.getStringPref('keybinding-scheme')
        if currentScheme not in self._schemes:
            log.error("The scheme specified in prefs (%s) is unknown -- reverting to default", currentScheme)
            currentScheme = self._globalPrefs.getStringPref('default-keybinding-scheme')
            self._globalPrefs.setStringPref('keybinding-scheme', currentScheme)

    def addScheme(self, scheme):
        #print "ADDING ", scheme.name
        self._schemes[scheme.name] = scheme

    def removeScheme(self, scheme):
        if scheme.name not in self._schemes:
            log.error("Couldn't remove scheme named %r, as we don't know about it", scheme.name)
            return
        del self._schemes[scheme.name]

    def getSchemeNames(self):
        names = self._schemes.keys()
        names.sort()
        return names
    
    def getScheme(self, name):
        if name not in self._schemes:
            log.error("asked for scheme by the name of %r, but there isn't one", name)
            return self._schemes['Default']
        return self._schemes[name]
    
    def purgeUnsavedSchemes(self):
        for name in self._schemes.keys():
            if self._schemes[name].unsaved:
                del self._schemes[name]

