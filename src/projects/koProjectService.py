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
            part = p.getChildByURL(url)
            if part:
                return p
        else:
            return None

    def getEffectivePrefsForURL(self, url):
        if not self._currentProject:
            return None
        part = self._currentProject.getChildByURL(url)
        if not part:
            for p in self._projects:
                part = p.getChildByURL(url)
                if part:
                    break
        if part:
            return part.prefset
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
    _com_interfaces_ = [components.interfaces.koIPartService,
                        components.interfaces.nsIObserver]
    _reg_desc_ = "Komodo Part Service Component"
    _reg_contractid_ = "@activestate.com/koPartService;1"
    _reg_clsid_ = "{96DB159A-E772-4985-91B0-55A7FB7FEE19}"
    _reg_categories_ = [
         ("komodo-startup-service", "koProjectService", True),
         ]

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

    def _deprecate_runningMacro(self):
        if getattr(self, '_deprecated_runningMacro', None) is None:
            self.deprecated_runningMacro = True
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
        return self._data[self.get_window()].isCurrent(project)

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
        return self._data[self.get_window()].set_currentProject(project)

    @components.ProxyToMainThread
    def get_currentProject(self):
        return self._data[self.get_window()].get_currentProject()

    @components.ProxyToMainThread
    def addProject(self, project):
        return self._data[self.get_window()].addProject(project)

    @components.ProxyToMainThread
    def removeProject(self, project):
        return self._data[self.get_window()].removeProject(project)

    @components.ProxyToMainThread
    def getProjects(self):
        return self._data[self.get_window()].getProjects()

    @components.ProxyToMainThread
    def getProjectForURL(self, url):
        return self._data[self.get_window()].getProjectForURL(url)

    @components.ProxyToMainThread
    def getEffectivePrefsForURL(self, url):
        return self._data[self.get_window()].getEffectivePrefsForURL(url)

    def getPartById(self, id):
        return findPartById(id)

    @components.ProxyToMainThread
    def findPart(self, partType, name, where, part):
        return self._data[self.get_window()].findPart(partType, name, where, part)

    @components.ProxyToMainThread
    def getPart(self, type, attrname, attrvalue, where, container):
        return self._data[self.get_window()].getPart(type, attrname, attrvalue, where, container)

    @components.ProxyToMainThread
    def getParts(self, type, attrname, attrvalue, where, container):
        return self._data[self.get_window()].getParts(type, attrname, attrvalue, where, container)

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
        ptn = re.compile(r'''(.*\bname\s*=\s*)(["'])%s\2(.*)''' % (re.escape(oldName),), re.DOTALL)
        m = ptn.match(contents)
        if not m:
            log.error("Can't find the name attribute in file %s", oldPath)
            os.rename(oldPath, newPath)
        else:
            newContents = m.group(1) + m.group(2) + newName + m.group(2) + m.group(3)
            fd = open(newPath, 'wb')
            fd.write(newContents)
            fd.close()
            os.unlink(oldPath)        

