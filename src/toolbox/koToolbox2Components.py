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
from pprint import pprint
import threading

from xpcom import components, COMException, ServerException, nsError
from xpcom.server import UnwrapObject
from projectUtils import *

import koToolbox2
import koMigrateV5Toolboxes

log = logging.getLogger("koToolbox2Components")
#log.setLevel(logging.DEBUG)


# This is just a singleton for access to the database.
# Python-side code is expected to unwrap the object to get
# at the underlying database object, and JS-code is
# expected to call other methods.

class KoToolboxDatabaseService(object):
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

class RunningMacros(object):
    """A class to hold info about a particular top-level Komodo window."""
    
    def __init__(self):
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


class KoToolInfo(object):
    """A light structure to hold info about a tool.
    Used by `.findTools()` below.
    """
    _com_interfaces_ = [components.interfaces.koIToolInfo]
    def __init__(self, toolMgr, path_id, type, name, subDir, **kwargs):
        self._toolMgr = toolMgr
        self.path_id = path_id
        self.type = type
        self.name = name
        self.subDir = subDir  # subdir in the toolbox tree
        for k,v in kwargs:
            setattr(self, k, v)

    _koTool = None
    @property
    def koTool(self):
        """Lazily retrieved (because it takes one or more DB accesses)
        `koITool` for this tool info.
        """
        if self._koTool is None:
            self._koTool = self._toolMgr.getOrCreateTool(self.type, self.name,
                self.path_id)
        return self._koTool

    @property
    def iconUrl(self):
        return self.koTool.get_iconurl()

    
class KoToolbox2Service(object):
    _com_interfaces_ = [components.interfaces.koIToolbox2Service,
                        components.interfaces.nsIObserver]
    _reg_clsid_ = "{cb9d6082-fc69-2d42-857a-2490e94fa518}"
    _reg_contractid_ = "@activestate.com/koToolbox2Service;1"
    _reg_desc_ = "Similar to the projectService, but for toolbox2"
    
    def __init__(self):
        self._macros = RunningMacros()
        self._standardToolbox = None  # Stores the top-level folder's ID
        self._loadedToolboxes = {}    # Map project uri to top-level folder's id
        self._tbFromExtension = {}    # Map folder ID to a boolean
        self.db = None
        self._inited = False
        
        _observerSvc = components.classes["@mozilla.org/observer-service;1"]\
                .getService(components.interfaces.nsIObserverService)
        _observerSvc.addObserver(self, "project_renamed", False)
        
    def initialize(self):
        if self._inited:
            return
        self._inited = True
        koDirSvc = components.classes["@activestate.com/koDirs;1"].getService()
        self.toolbox_db = UnwrapObject(components.classes["@activestate.com/KoToolboxDatabaseService;1"].\
                       getService(components.interfaces.koIToolboxDatabaseService))
        self._toolsMgrSvc = UnwrapObject(components.classes["@activestate.com/koToolbox2ToolManager;1"].\
                      getService(components.interfaces.koIToolbox2ToolManager));
        self._toolsMgrSvc.initialize(self.toolbox_db)

        self.db_path = os.path.join(koDirSvc.userDataDir, 'toolbox.sqlite')
        schemaFile = os.path.join(koDirSvc.supportDir, 'toolbox', 'koToolbox.sql')
        try:
            self.db = self.toolbox_db.initialize(self.db_path, schemaFile)
            self.loadMainToolboxes()
        except:
            log.exception("Error initializing toolboxes")

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
        toolbox_id = self.toolboxLoader.loadToolboxDirectory("", stdToolboxDir, koToolbox2.DEFAULT_TARGET_DIRECTORY)
        self.notifyAddedToolbox(stdToolboxDir, notifyAllWindows=True)
        t2 = time.time()
        #log.debug("Time to load std-toolbox: %g msec", (t2 - t1) * 1000.0)
        self.registerStandardToolbox(toolbox_id)
        
        from directoryServiceUtils import getExtensionToolboxDirs
        for toolsDir in getExtensionToolboxDirs():
            self.activateExtensionToolbox(toolsDir)
        self.toolboxLoader.deleteUnloadedTopLevelItems()
    
    def registerStandardToolbox(self, id):
        #log.debug("registerStandardToolbox(id:%d)", id)
        self._standardToolbox = id

    def registerUserToolbox(self, uri, id, isFromExtension):
        self._loadedToolboxes[uri] = id
        self._tbFromExtension[id] = isFromExtension

    def unregisterUserToolbox(self, uri):
        try:
            id = self._loadedToolboxes[uri]
        except KeyError:
            log.debug("Didn't find uri %s in self._loadedToolboxes")
            return
        try:
            del self._tbFromExtension[id]
        except KeyError:
            pass
        del self._loadedToolboxes[uri]

    def getLoadedProjectIDs(self):
        """
        Return a list of tuples of (toolID, toolURI) for project tools
        """
        if not self._loadedToolboxes:
            return []
        return [(id, uri)
                for uri, id in self._loadedToolboxes.items()
                if not self._tbFromExtension.get(id, False)]

    def toolbox_id_from_uri(self, uri):
        try:
            return self._loadedToolboxes[uri]
        except KeyError:
            log.debug("Didn't find uri %s in self._loadedToolboxes")
            return None

    def getExtensionToolbox(self, extensionName):
        from directoryServiceUtils import getExtensionToolboxDirs
        results = getExtensionToolboxDirs(extension_id=extensionName)
        if results:
            tbox_id = self.db.get_id_from_path(results[0])
            if tbox_id != -1:
                return self._toolsMgrSvc.getToolById(tbox_id)
        return None

    def getProjectToolboxId(self, uri):
        id = self._loadedToolboxes.get(uri, None)
        if id is None:
            return -1
        return id

    def getProjectURL(self, rootId):
        for url, id in self._loadedToolboxes.iteritems():
            if id == rootId:
                return url
        
    def getStandardToolboxID(self):
        return self._standardToolbox

    def getStandardToolbox(self):
        return self._toolsMgrSvc.getToolById(self._standardToolbox)
    
    def getSharedToolbox(self):
        return self._toolsMgrSvc.getToolById(self._sharedToolbox)

    def _notifyToolboxChanged(self, parentPath):
        observerSvc = components.classes["@mozilla.org/observer-service;1"].\
                       getService(components.interfaces.nsIObserverService)
        try:
            observerSvc.notifyObservers(None, 'toolbox-reload-view', parentPath)
        except:
            log.exception("For notification toolbox-reload-view:%s", parentPath)

    def importDirectory(self, parentPath, pathToImport):
        try:
            self.toolboxLoader.importDirectory(parentPath, pathToImport)
            self._notifyToolboxChanged(parentPath)
        except Exception, ex:
            raise ServerException(nsError.NS_ERROR_ILLEGAL_VALUE, ex)
    
    def importFiles(self, parentPath, toolPaths):
        try:
            self.toolboxLoader.importFiles(parentPath, toolPaths)
            self._notifyToolboxChanged(parentPath)
        except Exception, ex:
            raise ServerException(nsError.NS_ERROR_ILLEGAL_VALUE, ex)
    
    def importFileWithNewName(self, parentPath, srcPath, destPath):
        try:
            self.toolboxLoader.importFileWithNewName(parentPath, srcPath, destPath)
            self._notifyToolboxChanged(parentPath)
        except Exception, ex:
            raise ServerException(nsError.NS_ERROR_ILLEGAL_VALUE, ex)
            
    def importV5Package(self, parentPath, kpzPath):
        try:
            self.importV5Package_aux(parentPath, kpzPath)
            self._notifyToolboxChanged(parentPath)
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
        kpfDirToDelete = basedir
        toolboxDirName = os.path.splitext(os.path.basename(kpzPath))[0]
        tempToolsDir = join(os.path.dirname(kpfFile), ".extract-tools")
        if exists(tempToolsDir):
            try:
                shutil.rmtree(tempToolsDir)
            except:
                log.exception("importV5Package: failed to rmtree %s", tempToolsDir)
                
        try:
            koMigrateV5Toolboxes.expand_toolbox(kpfFile,
                                                tempToolsDir,
                                                toolboxDirName=toolboxDirName,
                                                force=1)
            # Now, where are the tools?
            # Usually the package is wrapped in a directory called "Project"
            childFiles = os.listdir(tempToolsDir)
            kpfDir = None
            if len(childFiles) == 1:
                candidate = join(tempToolsDir, childFiles[0])
                if os.path.isdir(candidate):
                    kpfDir = candidate
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
                    kpfDir = candidate
            if kpfDir is None:
                kpfDir = tempToolsDir
            self.toolboxLoader.importDirectory(parentPath, kpfDir)
        except:
            log.exception("Failed to expand/import package based at %s", parentPath)
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
                zf.close()
                return basedir, os.path.join(dir, name)
        zf.close()
        return basedir, None        

    def get_runningMacro(self):
        return self._macros.runningMacro

    def set_runningMacro(self, macro):
        self._macros.runningMacro = macro
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
            except:
                log.exception("Failed to migrate toolbox %s", toolboxPath)
            finally:
                os.chdir(curDir)
            try:
                f = open(migrateStampPath, "w")
                f.write("migrated %s on %s\n" % (label, time.ctime()))
                f.close()
            except IOError:
                log.exception("Can't write to %s: ", migrateStampPath)
        else:
            log.debug("No need to migrate from %s to %s", toolboxPath, toolboxDir)
            pass

    def migrateVersion5Toolboxes(self):
        if self._inited:
            return
        koDirSvc = components.classes["@activestate.com/koDirs;1"].getService()
        self._checkMigrate(koDirSvc.userDataDir, "user toolbox", koToolbox2.DEFAULT_TARGET_DIRECTORY, kpfName="toolbox.kpf")

    def activateProjectToolbox(self, project):
        projectDir = project.getFile().dirName;
        toolsDir = join(projectDir, koToolbox2.PROJECT_TARGET_DIRECTORY)
        if not exists(toolsDir):
            os.mkdir(toolsDir)
        if os.path.isdir(toolsDir):
            # If there's already a file by that name in the directory,
            # leave it there, and don't show a toolbox.
            toolboxName = os.path.splitext(project.name)[0]
            toolbox_id = self.toolboxLoader.loadToolboxDirectory(toolboxName,
                                                                 projectDir,
                                                                 koToolbox2.PROJECT_TARGET_DIRECTORY)
            self.registerUserToolbox(project.url, toolbox_id, False)
            self.notifyAddedToolbox(projectDir, notifyAllWindows=False)
            self.notifyToolboxTopLevelViewChanged()

    def activateExtensionToolbox(self, toolsDir):
        extensionRootDir = os.path.dirname(toolsDir)
        name = os.path.basename(extensionRootDir)
        folderDataPath = join(toolsDir, ".folderdata")
        if exists(folderDataPath):
            try:
                f = open(folderDataPath)
                data = json.load(f, encoding="utf-8")
                f.close()
                explicitName = data["name"]
                if explicitName:
                    name = explicitName
                    idx = name.find(koToolbox2.PROJECT_FILE_EXTENSION)
                    if idx > 0:
                        name = name[:idx]
            except:
                log.exception("Failed to find a name for toolbox %s", name)
        toolbox_id = self.toolboxLoader.loadToolboxDirectory(name,
                                                             extensionRootDir,
                                                             koToolbox2.DEFAULT_TARGET_DIRECTORY)
        self.registerUserToolbox(extensionRootDir, toolbox_id, True)
        self.notifyAddedToolbox(extensionRootDir, notifyAllWindows=True)
        self.notifyToolboxTopLevelViewChanged()

    # when an extension is disabled, we need to restart

    def deactivateProjectToolbox(self, project):
        projectDir = project.getFile().dirName;
        self.notifyDroppedToolbox(projectDir, notifyAllWindows=False)
        id = self.toolbox_id_from_uri(project.url)
        if id is not None:
            self.toolbox_db.deleteItem(id)
            self.unregisterUserToolbox(project.url)
            self.notifyToolboxTopLevelViewChanged()
        toolsDir = join(projectDir, koToolbox2.PROJECT_TARGET_DIRECTORY)
        if exists(toolsDir) and not os.listdir(toolsDir):
            try:
                os.rmdir(toolsDir)
            except:
                log.exception("Failed to remove %s", toolsDir)

    def notifyAddedToolbox(self, toolboxDir, notifyAllWindows=True):
        _observerSvc = components.classes["@mozilla.org/observer-service;1"]\
                .getService(components.interfaces.nsIObserverService)
        try:
            subject = (notifyAllWindows and 'toolbox-loaded-global') or 'toolbox-loaded-local'
            _observerSvc.notifyObservers(None, subject, toolboxDir)
        except Exception:
            log.exception("notifyAddedToolbox: notify %s failed", subject)
        tools = self._toolsMgrSvc.getToolsWithKeyboardShortcuts(toolboxDir)
        subject = (notifyAllWindows and 'kb-load-global') or 'kb-load'
        for tool in tools:
            try:
                _observerSvc.notifyObservers(tool, subject, str(tool.id))
            except Exception:
                log.exception("notifyAddedToolbox: notify kb-load: failed")
                
    def notifyDroppedToolbox(self, toolboxDir, notifyAllWindows=True):
        _observerSvc = components.classes["@mozilla.org/observer-service;1"]\
                .getService(components.interfaces.nsIObserverService)
        tools = self._toolsMgrSvc.getToolsWithKeyboardShortcuts(toolboxDir)
        subject = (notifyAllWindows and 'kb-unload-global') or 'kb-unload'
        for tool in tools:
            try:
                _observerSvc.notifyObservers(tool, subject, str(tool.id))
            except Exception:
                log.exception("notifyDroppedToolbox: notify kb-unload: failed")
        try:
            subject = (notifyAllWindows and 'toolbox-unloaded-global') or 'toolbox-unloaded-local'
            _observerSvc.notifyObservers(None, subject, toolboxDir)
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

    def findTools(self, query, langs):
        """Find a list of tools matching the given query.
        
        @param query {str} A query string. A space-separated list
            of search terms to match against tool names.
        @param langs {list} An ordering list of language scope names
            to be used for results ordering.
        @returns {list of KoToolInfo}
        
        Dev Notes:
        - TODO: match against subDir, lower sort order
        - case-sensitivity (http://www.sqlite.org/pragma.html#pragma_case_sensitive_like)
          Note that we can't do case-sensitivity per query word,
          as in fastopen if we continue to use multiple LIKEs in
          one SELECT.
        """
        def markup(word):
            escaped = word.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
            return '%' + escaped + '%'

        hits = []
        with self.db.connect() as cu:
            infoFromId = self.db.getInfoFromIdMap(cu=cu)  # id -> (name, subDir)
            sql = [
                "SELECT path_id, type, name FROM common_details",
                "WHERE type != 'folder'",
            ]
            args = []
            for word in query.split():
                sql.append("AND name LIKE ? ESCAPE '\\'")
                args.append(markup(word))
            cu.execute(' '.join(sql), tuple(args))
            # (id, type, name, subdir, matched-in-name)
            hits = [(x[0], x[1], x[2], infoFromId.get(x[0], ['', ''])[1], True)
                for x in cu.fetchall()]
        
            # Add any hits in the subdir.
            # - TODO:PERF This could be made faster by reversing `infoFromId`
            #   and finding all subDirs that have matches. Then get the
            #   corresponding ids. Otherwise we are duplicating "word in subDir"
            #   for the same values of "subDir".
            nameHitIds = set(h[0] for h in hits)
            subDirHitIds = []
            words = [w.lower() for w in query.split()]
            for id, info in infoFromId.items():
                if id in nameHitIds:
                    continue
                name, subDir = info
                nameLower = name.lower()
                subDirLower = subDir.lower()
                for word in words:
                    if word not in subDirLower and word not in nameLower:
                        break
                else:
                    subDirHitIds.append(id)
            if subDirHitIds:
                sql = "SELECT path_id, type, name FROM common_details WHERE type != 'folder'"
                if len(subDirHitIds) == 1:
                    sql += " AND path_id = %s" % subDirHitIds[0]
                else:
                    sql += " AND path_id IN %s" % repr(tuple(subDirHitIds))
                cu.execute(sql)
                hits += [(x[0], x[1], x[2], infoFromId.get(x[0], ['', ''])[1], False)
                    for x in cu.fetchall()]

        # Sorting results:
        # - Prefer matches in the name (vs. a match in the subDir)
        # - Sort tools to the top that are in a toolbox dir that
        #   matches the name of the current cursor sublang.
        def indexof(lst, item):
            try:
                return lst.index(item)
            except ValueError:
                return 999  # higher than anything
        def sortkey(hit):
            subDirParts = hit[3].split('/')
            langIndex = min(indexof(langs, p) for p in subDirParts)
            return (not hit[4], langIndex,)
        hits.sort(key=sortkey)

        return [KoToolInfo(self._toolsMgrSvc, *hit[:-1]) for hit in hits]
    
    def findToolsAsync(self, query, langs, callback):
        t = threading.Thread(target=self._findToolsAsync, args=(query, langs, callback))
        t.start()

    def _findToolsAsync(self, query, langs, callback):
        result = self.findTools(query, langs)
        self._findToolsAsyncCallback(callback, result)

    @components.ProxyToMainThreadAsync
    def _findToolsAsyncCallback(self, callback, result):
        callback.callback(0, result)

    def getAutoAbbreviationNames(self):
        query = ("select cd1.name"
                 + " from common_details as cd1, snippet as s1"
                 + " where s1.auto_abbreviation = 'true'"
                 + " and s1.path_id = cd1.path_id")
        try:
            with self.db.connect() as cu:
                cu.execute(query)
                # Use a set to remove duplicate names
                return list(set([hit[0] for hit in cu.fetchall()]))
        except:
            if self.db is not None:
                log.exception("Failed to run query %s", query)
            # otherwise we're probably running this too early, don't beak
            return []

    def observe(self, subject, topic, data):
        #log.debug("observe: subject:%r, topic:%r, data:%r", subject, topic, data)
        if not subject:
            return
        elif True:
            return
        elif topic == "xpcom-shutdown":
            _observerSvc = components.classes["@mozilla.org/observer-service;1"]\
                .getService(components.interfaces.nsIObserverService)
            _observerSvc.removeObserver(self, "project_renamed")
            _observerSvc.removeObserver(self, "xpcom-shutdown")
