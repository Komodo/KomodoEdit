#!/usr/bin/env python

from xpcom import components, ServerException, COMException, nsError
from xpcom.server import WrapObject, UnwrapObject
from projectUtils import *


import logging
log = logging.getLogger("koProjectService")


class KomodoWindowData(object):
    """A class to hold info about a particular top-level Komodo window."""
    
    def __init__(self):
        self._toolbox = None
        self._sharedToolbox = None
        self._currentProject = None
        self._projects = []
        
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
        return project and project in [self._currentProject, self._toolbox, self._sharedToolbox]

    def set_toolbox(self, project):
        if self._toolbox == project: return
        if self._toolbox:
            self._toolbox.deactivate()
        self._toolbox = project
        if self._toolbox:
            self._toolbox.activate()

    def get_toolbox(self):
        return self._toolbox

    def set_sharedToolbox(self, project):
        if self._sharedToolbox == project: return
        if self._sharedToolbox:
            self._sharedToolbox.deactivate()
        self._sharedToolbox = project
        if self._sharedToolbox:
            self._sharedToolbox.activate()

    def get_sharedToolbox(self):
        return self._sharedToolbox

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

    def findPart(self, partType, name, where, part):
        # See koIProject for details.
        if part:
            container = part.project
        else:
            container = None
        if where == '*':
            places = [container, self._toolbox, self._sharedToolbox]
        elif where == 'container':
            places = [container]
        elif where == 'toolbox':
            places = [self._toolbox]
        elif where == 'shared toolbox':
            places = [self._sharedToolbox]
        elif where == 'toolboxes':
            places = [self._toolbox, self._sharedToolbox]
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
            places = [container, self._toolbox, self._sharedToolbox]
        elif where == 'container':
            places = [container]
        elif where == 'current project':
            places = [self._currentProject]
        elif where == 'projects':
            places = self._projects
        elif where == 'toolbox':
            places = [self._toolbox]
        elif where == 'shared toolbox':
            places = [self._sharedToolbox]
        elif where == 'toolboxes':
            places = [self._toolbox, self._sharedToolbox]

        # Search them.
        for place in places:
            if not place:
                continue
            #TODO: Unwrap and use iterators to improve efficiency.
            #      Currently this can be marshalling lots of koIParts.
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
        self._toolboxSvc = None

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

    deprecated_runningMacro = False
    def _deprecate_runningMacro(self):
        if not self.deprecated_runningMacro:
            self.deprecated_runningMacro = True
            log.warn("koIPartService.runningMacro is deprecated.  Please use koIToolBox2Service.runningMacro instead.")

    def get_runningMacro(self):
        # Trying to set self._toolboxSvc in __init__ triggers an
        # xpcom exception with no info.
        if self._toolboxSvc is None:
            self._deprecate_runningMacro()
            self._toolboxSvc = components.classes["@activestate.com/koToolBox2Service;1"]\
                       .getService(components.interfaces.koIToolBox2Service)
        return self._toolboxSvc.runningMacro

    def set_runningMacro(self, macro):
        if self._toolboxSvc is None:
            self._deprecate_runningMacro()
            self._toolboxSvc = components.classes["@activestate.com/koToolBox2Service;1"]\
                       .getService(components.interfaces.koIToolBox2Service)
        self._toolboxSvc.runningMacro = macro
    runningMacro = property(get_runningMacro, set_runningMacro)
    
    def isCurrent(self, project):
        return self._data[self.get_window()].isCurrent(project)

    def set_toolbox(self, project):
        return self._data[self.get_window()].set_toolbox(project)

    def get_toolbox(self):
        return self._data[self.get_window()].get_toolbox()

    def setToolboxForWindow(self, project, window):
        data = self.get_data_for_window(window)
        return data.set_toolbox(project)

    def set_sharedToolbox(self, project):
        return self._data[self.get_window()].set_sharedToolbox(project)

    def get_sharedToolbox(self):
        return self._data[self.get_window()].get_sharedToolbox()

    def setSharedToolboxForWindow(self, project, window):
        data = self.get_data_for_window(window)
        return data.set_sharedToolbox(project)

    def set_currentProject(self, project):
        return self._data[self.get_window()].set_currentProject(project)

    def get_currentProject(self):
        return self._data[self.get_window()].get_currentProject()

    def addProject(self, project):
        return self._data[self.get_window()].addProject(project)

    def removeProject(self, project):
        return self._data[self.get_window()].removeProject(project)

    def getProjects(self):
        return self._data[self.get_window()].getProjects()

    def getProjectForURL(self, url):
        return self._data[self.get_window()].getProjectForURL(url)

    def getEffectivePrefsForURL(self, url):
        return self._data[self.get_window()].getEffectivePrefsForURL(url)

    def getPartById(self, id):
        return findPartById(id)

    def findPart(self, partType, name, where, part):
        return self._data[self.get_window()].findPart(partType, name, where, part)

    def getPart(self, type, attrname, attrvalue, where, container):
        return self._data[self.get_window()].getPart(type, attrname, attrvalue, where, container)

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

