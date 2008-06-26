#!/usr/bin/env python

from xpcom import components, ServerException, COMException, nsError
from xpcom.server import WrapObject, UnwrapObject
from projectUtils import *


import logging
log = logging.getLogger("koProjectService")

class KoPartService(object):
    _com_interfaces_ = [components.interfaces.koIPartService,
                        components.interfaces.nsIObserver]
    _reg_desc_ = "Komodo Part Service Component"
    _reg_contractid_ = "@activestate.com/koPartService;1"
    _reg_clsid_ = "{96DB159A-E772-4985-91B0-55A7FB7FEE19}"

    def __init__(self):
        self.lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"].\
            getService(components.interfaces.koILastErrorService)
        self.wm = components.classes["@mozilla.org/appshell/window-mediator;1"].\
            getService(components.interfaces.nsIWindowMediator)

        obsSvc = components.classes["@mozilla.org/observer-service;1"].\
                       getService(components.interfaces.nsIObserverService);
        obsSvc.addObserver(WrapObject(self,components.interfaces.nsIObserver), 'python_macro', 0);
        self._toolbox = None
        self._sharedToolbox = None
        self._currentProject = None
        self._projects = []
        
        # DEPRECATED
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
        if self._toolbox:
            self._toolbox.deactivate()
        self._toolbox = project
        if self._toolbox:
            self._toolbox.activate()

    def get_toolbox(self):
        return self._toolbox

    def set_sharedToolbox(self, project):
        if self._sharedToolbox:
            self._sharedToolbox.deactivate()
        self._sharedToolbox = project
        if self._sharedToolbox:
            self._sharedToolbox.activate()

    def get_sharedToolbox(self):
        return self._sharedToolbox

    def set_currentProject(self, project):
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

    def observe(self, subject, topic, data):
        #XXX This routine is never invoked from within Komodo
        if topic != 'python_macro':
            return
        window = self.wm.getMostRecentWindow('Komodo');
        #XXX Wrong number of arguments in this call
        evalPythonMacro(None, None, window, None, data)
