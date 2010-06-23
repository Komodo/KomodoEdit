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
import shutil
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
# at the underlying database object, and JS-code is
# expected to call other methods.

class KoToolboxDatabaseService:
    _com_interfaces_ = [components.interfaces.koIToolboxDatabaseService]
    _reg_clsid_ = "{a68427e7-9180-40b3-89ad-91440714dede}"
    _reg_contractid_ = "@activestate.com/KoToolboxDatabaseService;1"
    _reg_desc_ = "Access the toolbox database"
    
    db = None
    def initialize(self, db_path, schemaFile):
        self.db = koToolbox2.Database(db_path, schemaFile)
        return self.db
        
    def terminate(self):
        self.db = None
    
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

    # NewTools: @@@@ Pull more out of koProjectService.py as needed
    
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
        self._standardToolbox = None  # Stores the top-level folder's ID
        self._loadedToolboxes = {}    # Map project uri to top-level folder's 
        self._db = None
        
        self._wrapped = WrapObject(self, components.interfaces.nsIObserver)
        _observerSvc = components.classes["@mozilla.org/observer-service;1"]\
                .getService(components.interfaces.nsIObserverService)
        _observerSvc.addObserver(self._wrapped,
                                 "project_added", 0)
        _observerSvc.addObserver(self._wrapped,
                                 "project_removed", 0)
        # 
        # _observerSvc.addObserver(self._wrapped, 'toolbox.sqlite')
        
    def initialize(self):
        koDirSvc = components.classes["@activestate.com/koDirs;1"].getService()
        self.toolbox_db = UnwrapObject(components.classes["@activestate.com/KoToolboxDatabaseService;1"].\
                       getService(components.interfaces.koIToolboxDatabaseService))
        toolsMgrSvc = UnwrapObject(components.classes["@activestate.com/koToolbox2ToolManager;1"].\
                      getService(components.interfaces.koIToolbox2ToolManager));
        toolsMgrSvc.initialize(self.toolbox_db)

        self.db_path = os.path.join(koDirSvc.userDataDir, 'toolbox.sqlite')
        schemaFile = os.path.join(koDirSvc.mozBinDir,
                                  'python', 'komodo', 'toolbox',
                                  'koToolbox.sql')
        self.db = self.toolbox_db.initialize(self.db_path, schemaFile)
        self.loadMainToolboxes()

    def loadMainToolboxes(self):
        self.toolboxLoader = koToolbox2.ToolboxLoader(self.db_path, self.db)
        self.toolboxLoader.markAllTopLevelItemsUnloaded()
        koDirSvc = components.classes["@activestate.com/koDirs;1"].getService()
        stdToolboxDir = join(koDirSvc.userDataDir,
                             koToolbox2.DEFAULT_TARGET_DIRECTORY)
        if not os.path.exists(stdToolboxDir):
            try:
                os.mkdir(stdToolboxDir)
            except:
                log.error("Can't create tools dir %s", stdToolboxDir)

        import time
        t1 = time.time()
        toolbox_id = self.toolboxLoader.loadToolboxDirectory("Standard Toolbox", stdToolboxDir, koToolbox2.DEFAULT_TARGET_DIRECTORY)
        self.notifyAddedToolbox(stdToolboxDir)
        t2 = time.time()
        #log.debug("Time to load std-toolbox: %g msec", (t2 - t1) * 1000.0)
        self.registerStandardToolbox(toolbox_id)
        
        extensionDirs = UnwrapObject(components.classes["@python.org/pyXPCOMExtensionHelper;1"].getService(components.interfaces.pyIXPCOMExtensionHelper)).getExtensionDirectories()
        for fileEx in extensionDirs:
            # Does this happen for disabled extensions?
            toolDir = join(fileEx.path, koToolbox2.DEFAULT_TARGET_DIRECTORY)
            if os.path.exists(toolDir):
                self.activateExtensionToolbox(fileEx.path,
                                              koToolbox2.DEFAULT_TARGET_DIRECTORY)
            #else:
            #    log.debug("No tools in %s", fileEx.path)
        self.toolboxLoader.deleteUnloadedTopLevelItems()
    
    def registerStandardToolbox(self, id):
        #log.debug("registerStandardToolbox(id:%d)", id)
        self._standardToolbox = id

    def registerUserToolbox(self, uri, id):
        self._loadedToolboxes[uri] = id

    def unregisterUserToolbox(self, uri):
        try:
            del self._loadedToolboxes[uri]
        except KeyError:
            log.debug("Didn't find uri %s in self._loadedToolboxes")

    def toolbox_id_from_uri(self, uri):
        try:
            return self._loadedToolboxes[uri]
        except KeyError:
            log.debug("Didn't find uri %s in self._loadedToolboxes")
            return None

    def getStandardToolboxID(self):
        return self._standardToolbox
    
    def importDirectory(self, parentPath, pathToImport):
        try:
            return self.toolboxLoader.importDirectory(parentPath, pathToImport)
        except Exception, ex:
            raise ServerException(nsError.NS_ERROR_ILLEGAL_VALUE, ex)
    
    def importFiles(self, parentPath, toolPaths):
        try:
            return self.toolboxLoader.importFiles(parentPath, toolPaths)
        except Exception, ex:
            raise ServerException(nsError.NS_ERROR_ILLEGAL_VALUE, ex)
            
    def importV5Package(self, parentPath, kpzPath):
        try:
            return self.importV5Package_aux(parentPath, kpzPath)
        except Exception, ex:
            raise ServerException(nsError.NS_ERROR_ILLEGAL_VALUE, ex)
        
    def importV5Package_aux(self, parentPath, kpzPath):
        koDirSvc = components.classes["@activestate.com/koDirs;1"].getService()
        userDataDir = koDirSvc.userDataDir
        kpzExtractDir = join(userDataDir, 'extracted-kpz')
        if not os.path.exists(kpzExtractDir):
            os.mkdir(kpzExtractDir)
        startedWithWebResource = kpzPath.startswith("http:/")
        if startedWithWebResource:
            # Copy the web data to a temporary file.
            koResource = components.classes["@activestate.com/koFileEx;1"].\
                createInstance(components.interfaces.koIFileEx)
            koResource.URI = kpzPath
            kpzPath = join(kpzExtractDir, koResource.baseName)
            koTarget = components.classes["@activestate.com/koFileEx;1"].\
                createInstance(components.interfaces.koIFileEx)
            koTarget.path = kpzPath
            koTarget.open('wb')
            koResource.open('rb')
            koTarget.write(koResource.read(-1))
            koResource.close()
            koTarget.close()
        basedir, kpfFile = self._extractPackage(kpzPath, kpzExtractDir)
        toolboxDirName = os.path.splitext(os.path.basename(kpzPath))[0]
        tempToolsDir = join(os.path.dirname(kpfFile), ".extract-tools")
        try:
            koMigrateV5Toolboxes.expand_toolbox(kpfFile,
                                                tempToolsDir,
                                                toolboxDirName=toolboxDirName,
                                                force=1)
            # Now, where are the tools?
            # Usually the package is wrapped in a directory called "Project"
            childFiles = os.listdir(tempToolsDir)
            kpfDir = kpfDirToDelete = None
            if len(childFiles) == 1:
                candidate = join(tempToolsDir, childFiles[0])
                if os.path.isdir(candidate):
                    kpfDirToDelete = kpfDir = candidate
                    # Skip the hardcoded project thing
                    if childFiles[0].lower() != 'project':
                        childFiles = os.listdir(kpfDir)
                        if len(childFiles) == 1 and childFiles[0].lower() == 'project':
                            candidate = join(kpfDir, childFiles[0])
                            if os.path.isdir(candidate):
                                kpfDir = candidate
                            
            if kpfDir is None and 'Project' in childFiles:
                candidate = join(tempToolsDir, 'Project')
                if os.path.isdir(candidate):
                    kpfDirToDelete = kpfDir = candidate
            if kpfDir is None:
                kpfDirToDelete = kpfDir = tempToolsDir
            self.toolboxLoader.importDirectory(parentPath, kpfDir)
        except:
            log.exception("Failed to expand/import")
        finally:
            # Clean up
            if startedWithWebResource:
                try:
                    os.unlink(kpzPath)
                except:
                    log.exception("importV5Package: failed to delete %s", kpzPath)
            try:
                shutil.rmtree(kpfDirToDelete)
            except:
                log.exception("importV5Package: failed to rmtree %s", kpfDirToDelete)
            try:
                os.unlink(kpfFile)
            except:
                log.exception("importV5Package: failed to delete %s", kpfFile)
            
    def _extractPackage(self, file, dir):
        # From the project service, but extracts only the first kpf file it finds.
        import zipfile
        if not dir.endswith(':') and not os.path.exists(dir):
            os.mkdir(dir)

        zf = zipfile.ZipFile(file)
        files = zf.namelist()
        kpf = None
        basedir = os.path.dirname(join(dir, files[0]))
        # extract only the kpf file
        for name in files:
            if os.path.splitext(name)[1] == ".kpf":
                targetFile = join(dir, name)
                basedir = os.path.dirname(targetFile)
                if not os.path.exists(basedir):
                    os.makedirs(basedir)
                outfile = open(targetFile, 'wb')
                outfile.write(zf.read(name))
                outfile.flush()
                outfile.close()
                return basedir, os.path.join(dir, name)
        return basedir, None        

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
    
    def _checkMigrate(self, dataDir, label, targetDirectory, kpfName="toolbox.kpf"):
        toolboxPath = join(dataDir, kpfName)
        if targetDirectory == koToolbox2.PROJECT_TARGET_DIRECTORY:
            # If the project doesn't have any tools, don't extract them
            try:
                f = open(toolboxPath, 'r')
                contents = f.read()
                f.close()
                for tag in ['macro', 'snippet', 'command',
                            'template', 'URL', 'menu', 'toolbar']:
                    if ("<" + tag + " ") in contents:
                        break
                else:
                    #log.debug("No tools to convert in %s", contents)
                    return
            except:
                log.exception("Can't check file %s to see if it contains tools",
                              toolboxPath)
        toolboxDir = join(dataDir, targetDirectory)
        migrateStampPath = join(toolboxDir, ".migrated")
        if (exists(toolboxPath)
            and (not exists(migrateStampPath)
                 or os.stat(toolboxPath).st_mtime > os.stat(migrateStampPath).st_mtime)):
            curDir = os.getcwd()
            try:
                koMigrateV5Toolboxes.expand_toolbox(toolboxPath,
                                                    dataDir,
                                                  toolboxDirName=targetDirectory,
                                                    force=1)
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
        self._checkMigrate(koDirSvc.userDataDir, "user toolbox", koToolbox2.DEFAULT_TARGET_DIRECTORY, kpfName="toolbox.kpf")

    def activateProjectToolbox(self, project):
        projectDir = project.getFile().dirName;
        toolsDir = join(projectDir, koToolbox2.PROJECT_TARGET_DIRECTORY)
        if exists(toolsDir) and os.path.isdir(toolsDir):
            toolbox_id = self.toolboxLoader.loadToolboxDirectory(project.name,
                                                                 projectDir,
                                                                 koToolbox2.PROJECT_TARGET_DIRECTORY)
            self.registerUserToolbox(project.url, toolbox_id)
            self.notifyAddedToolbox(projectDir)
            self.notifyToolboxTopLevelViewChanged()

    def activateExtensionToolbox(self, extensionRootDir):
        toolsDir = join(extensionRootDir, koToolbox2.DEFAULT_TARGET_DIRECTORY)
        if exists(toolsDir) and os.path.isdir(toolsDir):
            name = os.path.basename(extensionRootDir)
            toolbox_id = self.toolboxLoader.loadToolboxDirectory(name,
                                                                 extensionRootDir,
                                                                 koToolbox2.DEFAULT_TARGET_DIRECTORY)
            self.registerUserToolbox(extensionRootDir, toolbox_id)
            self.notifyAddedToolbox(extensionRootDir)
            self.notifyToolboxTopLevelViewChanged()

    # when an extension is disabled, we need to restart

    def deactivateProjectToolbox(self, project):
        projectDir = project.getFile().dirName;
        self.notifyDroppedToolbox(projectDir)
        id = self.toolbox_id_from_uri(project.url)
        if id is not None:
            self.toolbox_db.deleteItem(id)
            self.unregisterUserToolbox(project.url)
            self.notifyToolboxTopLevelViewChanged()

    def notifyAddedToolbox(self, toolboxDir):
        _observerSvc = components.classes["@mozilla.org/observer-service;1"]\
                .getService(components.interfaces.nsIObserverService)
        try:
            _observerSvc.notifyObservers(None, 'toolbox-loaded', toolboxDir)
        except Exception:
            pass

    def notifyDroppedToolbox(self, toolboxDir):
        _observerSvc = components.classes["@mozilla.org/observer-service;1"]\
                .getService(components.interfaces.nsIObserverService)
        try:
            _observerSvc.notifyObservers(None, 'toolbox-unloaded', toolboxDir)
        except Exception:
            pass

    def notifyToolboxTopLevelViewChanged(self):
        _observerSvc = components.classes["@mozilla.org/observer-service;1"]\
                .getService(components.interfaces.nsIObserverService)
        try:
            _observerSvc.notifyObservers(None, 'toolbox-tree-changed', '')
        except Exception:
            pass

    def reloadToolsDirectory(self, toolDir):
        self.toolboxLoader.reloadToolsDirectory(toolDir)

    #Non-xpcom
    def extractToolboxFromKPF_File(self, kpfPath, projectName):
        kpfDir, kpfName = os.path.split(kpfPath)
        kpfPart, _ = os.path.splitext(kpfName)
        self._checkMigrate(kpfDir, projectName,
                           koToolbox2.PROJECT_TARGET_DIRECTORY,
                           kpfName=kpfName)
        

    def observe(self, subject, topic, data):
        #log.debug("observe: subject:%r, topic:%r, data:%r", subject, topic, data)
        if not subject:
            return
        #window = subject.QueryInterface(components.interfaces.nsIDOMWindow)
        #if self._windowTypeFromWindow(window) != "Komodo":
        #    return
        elif topic == "project_added":
            self.activateProjectToolbox(subject)
        elif topic == "project_removed":
            self.deactivateProjectToolbox(subject)
        elif True:
            return
        elif topic == "domwindowopened":
            self._data[window] = KomodoWindowData()
        elif topic == "domwindowclosed":
            if window in self._data:
                del self._data[window]
        elif topic == "xpcom-shutdown":
            _observerSvc.removeObserver(self._wrapped,
                                        "project_added")
            _observerSvc.removeObserver(self._wrapped,
                                        "project_removed")
            return



