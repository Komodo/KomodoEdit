#!/usr/bin/env python

from xpcom import components, ServerException, COMException, nsError
from xpcom.server import WrapObject, UnwrapObject
from projectUtils import *


import logging
log = logging.getLogger("koProjectService")
log.setLevel(logging.DEBUG)


class KomodoWindowData(object):
    """A class to hold info about a particular top-level Komodo window."""
    
    def __init__(self):
        self._currentProject = None
        self._projects = []
        
        # DEPRECATED - XXX still used though
        self._runningMacro = [None]


    def isCurrent(self, project):
        return project and project in [self._currentProject]

    def set_currentProject(self, project):
        if self._currentProject == project: return
        if self._currentProject:
            self._currentProject.deactivate()
        self._currentProject = project
        if self._currentProject:
            self._currentProject.activate()
            UnwrapObject(components.classes["@activestate.com/koUserEnviron;1"].getService()).addProjectEnvironment(project)
            
        obsSvc = components.classes["@mozilla.org/observer-service;1"].\
                       getService(components.interfaces.nsIObserverService)
        try:
            obsSvc.notifyObservers(project, 'current_project_changed', '')
        except:
            pass

    def get_currentProject(self):
        return self._currentProject

    def addProject(self, project):
        if project not in self._projects:
            self._projects.append(project)
            obsSvc = components.classes["@mozilla.org/observer-service;1"].\
                           getService(components.interfaces.nsIObserverService)
            try:
                obsSvc.notifyObservers(project, 'project_added', '')
            except:
                pass

    def removeProject(self, project):
        if project in self._projects:
            self._projects.remove(project)
            obsSvc = components.classes["@mozilla.org/observer-service;1"].\
                           getService(components.interfaces.nsIObserverService)
            try:
                obsSvc.notifyObservers(project, 'project_removed', '')
            except:
                pass

    def getProjects(self):
        return self._projects

    def getProjectForURL(self, url):
        for p in self._projects:
            if p.belongsToProject(url):
                return p
        else:
            return None

    def getEffectivePrefsForURL(self, url):
        if self._currentProject and self._currentProject.belongsToProject(url):
            return self._currentProject.prefset
        return None

    def getPartById(self, id):
        return findPartById(id)

    def findPartForRunningMacro(self, partType, name, where='*'):
        log.warn("DEPRECATED koIPartService.findPartForRunningMacro, use koIPartService.findPart")
        return self.findPart(partType, name, where, self.runningMacro)

    # **** New tools: verify findPart is used only to find parts, not tools.
    def findPart(self, partType, name, where, part):
	if where != "*":
	    log.error("DEPRECATED: calling koIPartService.findPart with container != '*' (set to %s)", where)
        # See koIProject for details.
        if not part:
            return None
	container = part.project
	if not container:
	    return None
	found = container.getChildWithTypeAndStringAttribute(
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
	if where != "*":
	    log.error("DEPRECATED: calling koIPartService._genParts with container != '*' (set to %s)", where)
	#TODO: Unwrap and use iterators to improve efficiency.
	#      Currently this can be marshalling lots of koIParts.
        if container:
            for part in place.getChildrenByType(type, True):
                if part.getStringAttribute(attrname) == attrvalue:
                    yield part


class KoPartService(object):
    _com_interfaces_ = [components.interfaces.koIPartService]
    _reg_desc_ = "Komodo Part Service Component"
    _reg_contractid_ = "@activestate.com/koPartService;1"
    _reg_clsid_ = "{96DB159A-E772-4985-91B0-55A7FB7FEE19}"

    def __init__(self):
        self._data = {} # Komodo windowId -> KomodoWindowData instance

    __contentUtils = None
    @property
    def _contentUtils(self):
        if self.__contentUtils is None:
            self.__contentUtils = components.classes["@activestate.com/koContentUtils;1"].\
                        getService(components.interfaces.koIContentUtils)
        return self.__contentUtils

    @property
    def project_window_data(self):
        """Returns project-specific toolbox data for the current call stack."""
        window = None

        # Try to use koIContentUtils, which can find the nsIDOMWindow for
        # the calling JavaScript context.
        w = self._contentUtils.GetWindowFromCaller()
        sentinel = 100
        while sentinel:
            if not w:
                break
            elif w.document.documentElement.getAttribute("windowtype") == "Komodo":
                window = w
                break
            elif w.parent == w:
                break
            w = w.parent
            sentinel -= 1
        else:
            log.warn("hit sentinel in KoPartService.project_window_data()!")
        
        # If we do not have a window from caller, then get the most recent
        # window and live with it.
        if not window:
            # Window here is nsIDOMWindowInternal, change it.
            wm = components.classes["@mozilla.org/appshell/window-mediator;1"].\
                            getService(components.interfaces.nsIWindowMediator)
            window = wm.getMostRecentWindow('Komodo')
        if window:
            window_id = window.QueryInterface(components.interfaces.nsIInterfaceRequestor) \
                            .getInterface(components.interfaces.nsIDOMWindowUtils) \
                            .outerWindowID
        else:
            # This is common when running Komodo standalone tests via
            # xpcshell, but should not occur when running Komodo normally.
            log.error("project_window_data:: getMostRecentWindow did not return a window")
            window_id = 1
        data = self._data.get(window_id)
        if data is None:
            data = KomodoWindowData()
            self._data[window_id] = data
        return data

    def _deprecate_runningMacro(self):
        if getattr(self, '_deprecated_runningMacro', None) is None:
            self._deprecated_runningMacro = True
            log.warn("koIPartService.runningMacro is deprecated.  Please use koIToolbox2Service.runningMacro instead.")

    @property
    def toolboxSvc(self):
        if getattr(self, '_toolboxSvc', None) is None:
            self._toolboxSvc = components.classes["@activestate.com/koToolbox2Service;1"]\
                       .getService(components.interfaces.koIToolbox2Service)
        return self._toolboxSvc
    
    @property
    def runningMacro(self):
        self._deprecate_runningMacro()
        return self.toolboxSvc.runningMacro

    @runningMacro.setter
    def set_runningMacro(self, macro):
        self._deprecate_runningMacro()
        self.toolboxSvc.runningMacro = macro
    
    @components.ProxyToMainThread
    def isCurrent(self, project):
        return self.project_window_data.isCurrent(project)

    def set_toolbox(self, project):
        raise ServerException(nsError.NS_ERROR_ILLEGAL_VALUE,
			      "Komodo no longer supports setting the toolbox")

    def get_toolbox(self):
        log.warn("DEPRECATED koIPartService.toolbox, use koIToolbox2Service.getStandardToolbox")
        return components.classes["@activestate.com/koToolbox2Service;1"].\
                       getService(components.interfaces.koIToolbox2Service).\
		       getStandardToolbox()

    def set_sharedToolbox(self, project):
        raise ServerException(nsError.NS_ERROR_ILLEGAL_VALUE,
			      "Komodo no longer supports setting the shared toolbox via the project system.")

    def get_sharedToolbox(self):
        log.error("DEPRECATED koIPartService.toolbox, use koIToolbox2Service.getStandardToolbox")
        return components.classes["@activestate.com/koToolbox2Service;1"].\
                       getService(components.interfaces.koIToolbox2Service).\
		       getSharedToolbox()

    @components.ProxyToMainThread
    def set_currentProject(self, project):
        return self.project_window_data.set_currentProject(project)

    @components.ProxyToMainThread
    def get_currentProject(self):
        return self.project_window_data.get_currentProject()

    @components.ProxyToMainThread
    def addProject(self, project):
        return self.project_window_data.addProject(project)

    @components.ProxyToMainThread
    def removeProject(self, project):
        return self.project_window_data.removeProject(project)

    @components.ProxyToMainThread
    def getProjects(self):
        return self.project_window_data.getProjects()

    @components.ProxyToMainThread
    def getProjectForURL(self, url):
        return self.project_window_data.getProjectForURL(url)

    @components.ProxyToMainThread
    def getEffectivePrefsForURL(self, url):
        return self.project_window_data.getEffectivePrefsForURL(url)

    def getPartById(self, id):
        return findPartById(id)

    @components.ProxyToMainThread
    def findPart(self, partType, name, where, part):
        return self.project_window_data.findPart(partType, name, where, part)

    @components.ProxyToMainThread
    def getPart(self, type, attrname, attrvalue, where, container):
        return self.project_window_data.getPart(type, attrname, attrvalue, where, container)

    @components.ProxyToMainThread
    def getParts(self, type, attrname, attrvalue, where, container):
        return self.project_window_data.getParts(type, attrname, attrvalue, where, container)

    def renameProject(self, oldPath, newPath):
        """
        We want to update the name field of the new project file without
        changing any of the other markup.  Using ElementTree drops the
        comments, and using the koProject serializer is too cumbersome.
        So make a quick white-box change.
        """
        import os, os.path, re
        oldName = os.path.basename(oldPath)
        newName = os.path.basename(newPath)
        fd = open(oldPath, 'rb')
        contents = fd.read()
        newContents = None
        ptn = re.compile(r'''(.*\bname\s*=\s*)(["'])%s\2(.*)''' % (re.escape(oldName),), re.DOTALL)
        m = ptn.match(contents)
        if m:
            newContents = m.group(1) + m.group(2) + newName + m.group(2) + m.group(3)
        else:
            log.warn("Can't find the name attribute %s in file %s", oldName, oldPath)
            ptn = re.compile(r'''(.*?<project[^>]+ \bname\s*=\s*)(["'])[^'"]+\2(.*)$''', re.DOTALL)
            m = ptn.match(contents)
            if m:
                newContents = m.group(1) + m.group(2) + newName + m.group(2) + m.group(3)
            else:
                log.error("Can't find any name attribute in file %s", oldPath)
        if sys.platform.startswith("linux"):
            isSameBasename = newName == oldName
        else:
            isSameBasename = newName.lower() == oldName.lower()
        if newContents:
            fd = open(newPath, 'wb')
            fd.write(newContents)
            fd.close()
            if not isSameBasename:
                os.unlink(oldPath)
        elif not isSameBasename:
            os.rename(oldPath, newPath)

