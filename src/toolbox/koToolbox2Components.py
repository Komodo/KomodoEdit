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
# Portions created by ActiveState Software Inc are Copyright (C) 2000-2010
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

"""KoToolboxDatabaseService - A service for
accessing the new toolbox service.
"""

import json
import os
import os.path
from os.path import join, exists
import re
import sys
import time
import logging
from xpcom import components, COMException, ServerException, nsError
from xpcom.server import WrapObject, UnwrapObject
from projectUtils import *

import koToolbox2
import koMigrateV5Toolboxes

log = logging.getLogger("koToolbox2Components")
#log.setLevel(logging.DEBUG)


# This is just a singleton for access to the database.
# Python-side code is expected to unwrap the object to get
# at the underlying database object, while
# JS-side code will have to go through the interface.

class KoToolboxDatabaseService:
    _com_interfaces_ = [components.interfaces.koIToolboxDatabaseService]
    _reg_clsid_ = "{a68427e7-9180-40b3-89ad-91440714dede}"
    _reg_contractid_ = "@activestate.com/KoToolboxDatabaseService;1"
    _reg_desc_ = "Access the toolbox database"
    
    db = None
    toolManager = None
    def initialize(self, db_path):
        self.db = koToolbox2.Database(db_path)
        
    def terminate(self):
        self.db = self.toolManager = None
    
    # Python-side methods only:
    
    def getToolById(self, id):
        return self.toolManager.getToolById(id)    
    
    def __getattr__(self, attr):
        return getattr(self.db, attr)

# Taken from koProjectService.py

class KomodoWindowData(object):
    """A class to hold info about a particular top-level Komodo window."""
    
    def __init__(self):
        self._currentProject = None
        
        # DEPRECATED - XXX still used though
        self._runningMacro = [None]


    def get_runningMacro(self):
        return self._runningMacro[-1]
    def set_runningMacro(self, macro):
        if macro:
            self._runningMacro.append(macro)
        elif len(self._runningMacro) > 1:
            self._runningMacro.pop()
    runningMacro = property(get_runningMacro, set_runningMacro)
    
    def isCurrent(self, project):
        return project and project in [self._currentProject]

    def set_currentProject(self, project):
        if self._currentProject == project: return
        if self._currentProject:
            self._currentProject.deactivate()
        self._currentProject = project
        if self._currentProject:
            self._currentProject.activate()
        obsSvc = components.classes["@mozilla.org/observer-service;1"].\
                       getService(components.interfaces.nsIObserverService)
        try:
            obsSvc.notifyObservers(project, 'current_project_changed', '')
        except:
            pass

    def get_currentProject(self):
        return self._currentProject

    def getEffectivePrefsForURL(self, url):
        if not self._currentProject:
            return None
        part = self._currentProject.getChildByURL(url)
        if part:
            return part.prefset
        return None

    def getPartById(self, id):
        return findPartById(id)

    def findPartForRunningMacro(self, partType, name, where='*'):
        log.warn("DEPRECATED koIPartService.findPartForRunningMacro, use koIPartService.findPart")
        return self.findPart(partType, name, where, self.runningMacro)

    def findPart(self, partType, name, where, part):
        # See koIProject for details.
        if part:
            container = part.project
        else:
            container = None
        if where == '*':
            places = [container]
        elif where == 'container':
            places = [container]
        for place in places:
            if place:
                found = place.getChildWithTypeAndStringAttribute(
                            partType, 'name', name, 1)
                if found:
                    return found
        return None

    def getPart(self, type, attrname, attrvalue, where, container):
        for part in self._genParts(type, attrname, attrvalue,
                                   where, container):
            return part

    def getParts(self, type, attrname, attrvalue, where, container):
        return list(
            self._genParts(type, attrname, attrvalue, where, container)
        )

    def _genParts(self, type, attrname, attrvalue, where, container):
        # Determine what koIProject's to search.
        if where == '*':
            places = [container]
        elif where == 'container':
            places = [container]
        elif where == 'current project':
            places = [self._currentProject]

        # Search them.
        for place in places:
            if not place:
                continue
            #TODO: Unwrap and use iterators to improve efficiency.
            #      Currently this can be marshalling lots of koIParts.
            for part in place.getChildrenByType(type, True):
                if part.getStringAttribute(attrname) == attrvalue:
                    yield part

        
class KoToolBox2Service:
    _com_interfaces_ = [components.interfaces.koIToolBox2Service,
                        components.interfaces.nsIObserver]
    _reg_clsid_ = "{c9452cf9-98ec-4ab9-b730-69156c2cec53}"
    _reg_contractid_ = "@activestate.com/koToolBox2Service;1"
    _reg_desc_ = "Similar to the projectService, but for toolbox2"
    
    def __init__(self):
        self.wrapped = WrapObject(self, components.interfaces.nsIObserver)

        self.ww = components.classes["@mozilla.org/embedcomp/window-watcher;1"].\
                        getService(components.interfaces.nsIWindowWatcher);
        self.ww.registerNotification(self.wrapped)

        self.wm = components.classes["@mozilla.org/appshell/window-mediator;1"].\
                        getService(components.interfaces.nsIWindowMediator);

        self._contentUtils = components.classes["@activestate.com/koContentUtils;1"].\
                    getService(components.interfaces.koIContentUtils)

        self._data = {} # Komodo nsIDOMWindow -> KomodoWindowData instance

    def _windowTypeFromWindow(self, window):
        if not window:
            return None
        return window.document.documentElement.getAttribute("windowtype")

    def get_window(self):
        """Return the appropriate top-level Komodo window for this caller."""
        window = None

        # Try to use koIContentUtils, which can find the nsIDOMWindow for
        # the calling JavaScript context.
        w = self._contentUtils.GetWindowFromCaller()
        sentinel = 100
        while sentinel:
            if not w:
                break
            elif self._windowTypeFromWindow(w) == "Komodo":
                window = w
                break
            elif w.parent == w:
                break
            w = w.parent
            sentinel -= 1
        else:
            log.warn("hit sentinel in KoPartService.get_window()!")
        
        # If we do not have a window from caller, then get the most recent
        # window and live with it.
        if not window:
            # Window here is nsIDOMWindowInternal, change it.
            window = self.wm.getMostRecentWindow('Komodo')
            if window:
                window.QueryInterface(components.interfaces.nsIDOMWindow)
            else:
                # This is common when running Komodo standalone tests via
                # xpcshell, but should not occur when running Komodo normally.
                log.error("get_window:: getMostRecentWindow did not return a window")
        if window not in self._data:
            self._data[window] = KomodoWindowData()
        return window

    def get_data_for_window(self, window):
        if not window:
            return None
        data = self._data.get(window)
        if data is None:
            data = KomodoWindowData()
            self._data[window] = data
        return data

    def get_runningMacro(self):
        return self._data[self.get_window()].runningMacro

    def set_runningMacro(self, macro):
        self._data[self.get_window()].runningMacro = macro
    runningMacro = property(get_runningMacro, set_runningMacro)
    
    def _checkMigrate(self, dataDir, label):
        toolboxPath = join(dataDir, "toolbox.kpf")
        toolboxDir = join(dataDir, koToolbox2.DEFAULT_TARGET_DIRECTORY)
        migrateStampPath = join(toolboxDir, ".migrated")
        if (exists(toolboxPath)
            and (not exists(migrateStampPath)
                 or os.stat(toolboxPath).st_mtime > os.stat(migrateStampPath).st_mtime)):
            curDir = os.getcwd()
            try:
                koMigrateV5Toolboxes.expand_toolbox(toolboxPath, dataDir, force=1)
            finally:
                os.chdir(curDir)
            f = open(migrateStampPath, "w")
            f.write("migrated %s on %s\n" % (label, time.ctime()))
            f.close()
        else:
            log.debug("No need to migrate from %s to %s", toolboxPath, toolboxDir)
            pass

    def migrateVersion5Toolboxes(self):
        koDirSvc = components.classes["@activestate.com/koDirs;1"].getService()
        self._checkMigrate(koDirSvc.userDataDir, "user toolbox")

    def observe(self, subject, topic, data):
        if not subject:
            return
        window = subject.QueryInterface(components.interfaces.nsIDOMWindow)
        if self._windowTypeFromWindow(window) != "Komodo":
            return
        if topic == "domwindowopened":
            self._data[window] = KomodoWindowData()
        elif topic == "domwindowclosed":
            if window in self._data:
                del self._data[window]

