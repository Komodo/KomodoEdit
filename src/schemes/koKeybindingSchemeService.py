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

from zope.cachedescriptors.property import LazyClassAttribute

from xpcom import components

from schemebase import SchemeBase, SchemeServiceBase

log = logging.getLogger('koKeybindingSchemeService')
#log.setLevel(logging.DEBUG)

class Scheme(SchemeBase):
    _com_interfaces_ = [components.interfaces.koIKeybindingScheme]
    _reg_clsid_ = "{73358FFD-27D3-435A-B89E-C24373AF1807}"
    _reg_contractid_ = "@activestate.com/koKeybindingScheme;1"
    _reg_desc_ = "Keybinding Scheme object"

    ext = '.kkf'

    def __init__(self, fname, userDefined, unsaved=0):
        SchemeBase.__init__(self, fname, userDefined, unsaved=unsaved)
        if unsaved:
            self.data = ''
        else:
            self.data = open(fname).read()

    def revert(self):
        SchemeBase.revert(self)
        self.data = open(self.fname).read()

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
        if os.path.exists(self.fname):
            os.remove(self.fname)
        schemeService = components.classes['@activestate.com/koKeybindingSchemeService;1'].getService()
        schemeService.removeScheme(self)

class koKeybindingSchemeService(SchemeServiceBase):
    _com_interfaces_ = [components.interfaces.koIKeybindingSchemeService]
    _reg_clsid_ = "{5DEDBA35-45A2-4913-8271-C950CE3C96BE}"
    _reg_contractid_ = "@activestate.com/koKeybindingSchemeService;1"
    _reg_desc_ = "Service used to access, manage and create keybinding  'schemes'"

    ext = '.kkf'

    def __init__(self):
        SchemeServiceBase.__init__(self)

        currentScheme = self._globalPrefs.getString('keybinding-scheme', '')
        if currentScheme not in self._scheme_details:
            log.error("The scheme specified in prefs (%s) is unknown -- reverting to default", currentScheme)
            currentScheme = self._globalPrefs.getString('default-keybinding-scheme', 'Default')
            self._globalPrefs.setStringPref('keybinding-scheme', currentScheme)

    @classmethod
    def _makeScheme(cls, fname, userDefined, unsaved=0):
        """Factory method for creating an initialized scheme object

        @param fname {str} Either the full path to a scheme file, or a scheme name (see unsaved)
        @param userDefined {bool} False if it's a Komodo-defined scheme
        @param unsaved {bool} True: fname is the name of a scheme, False: fname is a full path
        @returns an initialized Scheme object
        """
        return Scheme(fname, userDefined, unsaved)

