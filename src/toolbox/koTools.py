#!/usr/bin/env python
# Copyright (c) 2010 ActiveState
# See the file LICENSE.txt for licensing information.

"""
Information about the individual tools is stored here.  These
objects act like a cache around the database.
"""

import os
import sys
import re
import json
from os.path import join
import logging
import random

from xpcom import components, ServerException, nsError
from xpcom.server import WrapObject, UnwrapObject
import eollib
import projectUtils
import uriparse
 
import koToolbox2



#---- Globals

log = logging.getLogger("koTools")
#log.setLevel(logging.DEBUG)

eol = None

_toolsManager = None

_icons = {
    'folder'    :   'chrome://komodo/skin/images/folder-closed.png',
    'menu'      :   'chrome://komodo/skin/images/toolbox/menu.svg',
    'toolbar'   :   'chrome://komodo/skin/images/toolbox/toolbar.svg',
    'terminal'  :   'chrome://komodo/skin/images/toolbox/command.svg',
    'macro'     :   'chrome://komodo/skin/images/toolbox/macro.svg',
    'cut'       :   'chrome://komodo/skin/images/toolbox/snippet.svg',
    'template'  :   'chrome://komodo/skin/images/toolbox/template.svg',
    'url'       :   'chrome://komodo/skin/images/toolbox/browser.svg'
}

if sys.platform == 'darwin':
    _icons.update({
        'folder'    :   'chrome://global/skin/dirListing/folder.png'
    })
    
if sys.platform.startswith('linux'):
    _icons.update({
        'folder'    :   'moz-icon://stock/gtk-directory?size=16'
    })

#---- `koITool` class hierarchy

class _KoTool(object):
    _com_interfaces_ = [components.interfaces.koITool]
    isContainer = False
    _observerSvc = None
    def __init__(self, name, id):
        self.name = name
        self.id = id  # path_id in DB
        self.value = ""
        self.saved = False  # Set to True once it's been saved in db and on disk.
        self.initialized = False
        self.temporary = False
        self._attributes = {}
        self._nondb_attributes = {}
        self.flavors = ['text/uri-list',
                        'text/unicode', 'text/plain', 'application/x-komodo-part',
# #if PLATFORM != "win"
                        # XXX for a later release, scintilla needs work in this area
                        'TEXT',#,'COMPOUND_TEXT','STRING','UTF-8' \
# #endif
                        ]

    def __str__(self):
        s = {}
        for name in ['value', 'name']:
            res = getattr(self, name, None)
            if res is not None:
                s[name] = res
        s.update(self._attributes)
        return str(s)
        
    def init(self):
        pass
    
    def _getObserverSvc(self):
        if not self._observerSvc:
            self._observerSvc = components.classes["@mozilla.org/observer-service;1"]\
                .getService(components.interfaces.nsIObserverService)
        return self._observerSvc
    
    def get_keybinding_description(self):
        return self.prettytype + "s: " + self.name

    def getCustomIconIfExists(self):
        iconurl = _tbdbSvc.getCustomIconIfExists(self.id)
        if iconurl:
            self.set_iconurl(iconurl)
        return iconurl is not None

    def get_iconurl(self):
        iconurl = None
        if self._attributes.has_key('icon'):
            iconurl = self._attributes['icon']
        else:
            iconurl = self._iconurl
            
        if iconurl.startswith("chrome://icomoon"):
            iconurl = re.sub(r'chrome:.*\/(.*?).png', r'koicon://ko-svg/chrome/icomoon/skin/\1.svg', iconurl)
            self.set_iconurl(iconurl)
            
        return iconurl

    def set_iconurl(self, url):
        if not url or url == self._iconurl:
            self.removeAttribute('icon')
            #_tbdbSvc.deleteRowByKey('misc_properties', ['path_id', 'prop_name'],
            #                        [self.id, 'icon'])
                                    
        else:
            self.setAttribute('icon', url)
        try:
            self._getObserverSvc().notifyObservers(self, 'part_changed', '')
        except Exception, unused:
            #log.exception("set_iconurl: trying to notify part_changed")
            pass

    def updateKeyboardShortcuts(self):
        res = _tbdbSvc.getValuesFromTableByKey('common_tool_details', ['keyboard_shortcut'], 'path_id', self.id)
        if res is not None:
            self.setStringAttribute('keyboard_shortcut', res[0])

    def _finishUpdatingSelf(self, info):
        for name in ['value', 'name']:
            if name in info:
                setattr(self, name, info[name])
                del info[name]
        for key, value in info.items():
            self._attributes[key] = value
        self.initialized = True

    #non-xpcom
    def fillDetails(self, itemDetailsDict):
        non_attr_names = ['name', 'id']
        for name in non_attr_names:
            res = getattr(self, name, None)
            if res is not None:
                itemDetailsDict[name] = res
        itemDetailsDict['type'] = self.get_type()
        itemDetailsDict['value'] = self.value.splitlines()
        for name in self._attributes:
            itemDetailsDict[name] = self._attributes[name]

    def get_value(self):
        return self.value

    def get_path(self):
        return _tbdbSvc.getPath(self.id)

    @property
    def path(self):
        return _tbdbSvc.getPath(self.id)

    def set_path(self, val):
        raise ServerException(nsError.NS_ERROR_ILLEGAL_VALUE,
                              ("can't call setpath on %s %s (id %r)"
                               % (self.get_type(), self.typeName, self.id)))

    def set_type(self, value):
        self.typeName = value
        
    def set_name(self, name):
        self.name = name
            
    def get_type(self):
        return self.typeName

    def get_parent(self):
        res = _tbdbSvc.getValuesFromTableByKey('hierarchy',
                                               ['parent_path_id'],
                                               'path_id', self.id)
        if res is None or res[0] is None:
            return None
        return _toolsManager.getToolById(res[0])
                                  
    def hasAttribute(self, name):
        # Keep names out of attributes
        if name == 'name':
            return self.name is not None
        return self._attributes.has_key(name)

    def getAttribute(self, name):
        if not self.hasAttribute(name):
            self.updateSelf()
        return self._attributes[name]

    def setAttribute(self, name, value):
        if name not in self._attributes or self._attributes[name] != value: # avoid dirtification when possible.
            self._attributes[name] = value

    def removeAttribute(self, name):
        if name not in self._attributes: return
        del self._attributes[name]

    def getStringAttribute(self, name):
        try:
            return unicode(self._attributes[name])
        except KeyError:
            if name == "name":
                return self.name
            raise

    def setStringAttribute(self, name, value):
        # Keep names out of attributes
        if name == 'name':
            self.name = value
        else:
            self.setAttribute(name, unicode(value))

    def getLongAttribute(self, name):
        return int(self.getAttribute(name))

    def setLongAttribute(self, name, value):
        self.setAttribute(name, int(value))

    def getBooleanAttribute(self, name):
        return self.getLongAttribute(name) and 1 or 0

    def setBooleanAttribute(self, name, value):
        self.setAttribute(name, value and 1 or 0)

    def added(self):
        # This routine checks creation of macros, keybindings, and
        # toolbars, and menus
        """
        If the part is in a menu, send tool, 'menu_changed', <not-used>
        If the part is in a toolbar, send tool, 'toolbar_changed', <not-used>
        If the part has a keyboard_shortcut, send tool, 'kb-load', tool.id
        If the part is a macro with a trigger, send tool, 'macro-load', <not-used>
        """
        requests = []
        typeName = self.typeName
        if typeName == 'macro' and self.getAttribute('trigger_enabled'):
            requests.append([self, 'macro-load', None])
        try:
            if self.getAttribute('keyboard_shortcut'):
                requests.append([self, 'kb-load', str(self.id)])
        except KeyError:
            pass
        if typeName in ('menu', 'toolbar'):
            # menu_created and toolbar_created notifications are done here
            requests.append([self, typeName + "_created", None])
        # Are there any custom menus or toolbars that contain this item?
        id = self.id
        while True:
            parentRes = _tbdbSvc.getParentNode(id)
            if parentRes is None:
                break
            id, name, nodeType = parentRes
            # menu_changed and toolbar_changed notifications are done here
            if nodeType in ('menu', 'toolbar'):
                requests.append([_toolsManager.getToolById(id),
                                 nodeType + "_changed", None])
        if requests:
            self._sendRequests(requests)

    def removed(self):
        # This routine checks deletion of macros, keybindings, and
        # toolbars, and menus
        """
        If the part is in a menu, send tool, 'menu_changed', <not-used>
        If the part is in a toolbar, send tool, 'toolbar_changed', <not-used>
        If the part has a keyboard_shortcut, send tool, 'kb-unload', tool.id
        """
        requests = []
        typeName = self.typeName
        try:
            if self.getAttribute('keyboard_shortcut'):
                requests.append([self, 'kb-unload', str(self.id)])
        except KeyError:
            pass
        # Are there any custom menus or toolbars that contain this item?
        id = self.id
        while True:
            parentRes = _tbdbSvc.getParentNode(id)
            if parentRes is None:
                break
            id, name, nodeType = parentRes
            if nodeType in ('menu', 'toolbar'):
                requests.append([_toolsManager.getToolById(id),
                                 nodeType + "_changed", None])
        if requests:
            self._sendRequests(requests)

    def _sendRequests(self, requests):
        for request in requests:
            try:
                self._getObserverSvc().notifyObservers(*request)
            except Exception:
                pass

    # Drag/drop
    def getDragData(self):
        #print "getDragData ",repr(self.value)
        return self.value
    
    def getDragDataByFlavor(self, flavor):
        if flavor == "application/x-moz-file":
            return self.path
        elif flavor in ("text/x-moz-url", "text/uri-list"):
            return uriparse.localPathToURI(self.path)
        return self.getDragData()

    def getDragFlavors(self):
        return self.flavors
    
    def _saveIconCheck(self, data):
        if ('iconurl' not in self._attributes) and 'icon' in data:
            del data['icon']

    # todo: push these into one routine.
    def saveToolToDisk(self):
        if 'path' not in self._nondb_attributes:
            self._nondb_attributes['path'] = _tbdbSvc.getPath(self.id)
        path = self._nondb_attributes['path']
        fp = open(path, 'r')
        data = json.load(fp, encoding="utf-8")
        fp.close()
        if data.get('name', self.name) != self.name:
            refreshParent = True
            # bug 88228: we're renaming a tool by saving its properties, so do the
            # rename separately.  This updates the DB correctly.
            savePath = _toolsManager._renameObject(self.id, self.name, isContainer=False)
        else:
            refreshParent = False
            savePath = path
        data['value'] = self.value.splitlines()
        data['name'] = self.name
        self._saveIconCheck(data)
        data.update(self._attributes)
        fp = open(savePath, 'w')
        json.dump(data, fp, encoding="utf-8", indent=2)
        fp.close()
        if refreshParent:
            self._refreshParent()

    def saveNewToolToDisk(self, path):
        data = {}
        data['value'] = self.value.splitlines()
        data['type'] = self.typeName
        data['name'] = self.name
        data['version'] = koToolbox2.ToolboxLoader.ITEM_VERSION
        self._saveIconCheck(data)
        data.update(self._attributes)
        fp = open(path, 'w')
        data = json.dump(data, fp, encoding="utf-8", indent=2)
        fp.close()
        
    def saveContentToDisk(self):
        if 'path' not in self._nondb_attributes:
            self._nondb_attributes['path'] = _tbdbSvc.getPath(self.id)
        path = self._nondb_attributes['path']
        fp = open(path, 'r')
        data = json.load(fp, encoding="utf-8")
        fp.close()
        if data.get('name', self.name) != self.name:
            refreshParent = True
            # bug 88228
            savePath = _toolsManager._renameObject(self.id, self.name, isContainer=False)
        else:
            refreshParent = False
            savePath = path
        data['value'] = self.value.splitlines()
        data['type'] = self.typeName
        data['name'] = getattr(self, 'name', data['name'])
        self._saveIconCheck(data)
        for attr in self._attributes:
            newVal = self._attributes[attr]
            if attr not in data or newVal != data[attr]:
                data[attr] = self._attributes[attr]
        fp = open(savePath, 'w')
        data = json.dump(data, fp, encoding="utf-8", indent=2)
        fp.close()
        if refreshParent:
            self._refreshParent()
            
    def _refreshParent(self):
        parentTool = self.get_parent()
        if not parentTool:
            # This should be impossible.
            log.error("Can't find a parent for tool id %d, path %s", self.id, self.path)
            return
        _toolsManager.hierarchicalView.refreshToolView(parentTool)

    def save_handle_attributes(self):
        names = ['name', 'value']
        for name in names:
            if name in self._attributes:
                #log.debug("Removing self._attributes %s = %s", name, self._attributes[name])
                setattr(self, name, self._attributes[name])
                del self._attributes[name]

    def delete(self):
        self.removed()
        path = self.get_path()
        _tbdbSvc.deleteItem(self.id)

        # On Windows this moves the full folder to the recycle bin
        # as an atomic unit, so the user can get it back, but can't
        # examine its contents.  Better than flattening a tree out
        # and putting each item in the bin's top-level.
        sysUtilsSvc = components.classes["@activestate.com/koSysUtils;1"].\
                      getService(components.interfaces.koISysUtils);
        sysUtilsSvc.MoveToTrash(path)

    def save(self):
        raise ServerException(nsError.NS_ERROR_ILLEGAL_VALUE,
                              ("save not yet implemented for %s"
                               % self.get_type()))

    def _postSave(self):
        observerSvc = components.classes["@mozilla.org/observer-service;1"].\
                       getService(components.interfaces.nsIObserverService)
        try:
            observerSvc.notifyObservers(None, 'toolbox-reload-view', self.path)
        except:
            log.exception("For notification toolbox-reload-view:%s", self.path)
        self.initialized = False
        self.temporary = False

    def getFile(self):
        url = self.get_url()
        if url is not None:
            fsvc = components.classes["@activestate.com/koFileService;1"].getService(components.interfaces.koIFileService)
            return fsvc.getFileFromURI(url)
        return None

    def get_url(self):
        if self.hasAttribute('url'):
            return self.getStringAttribute('url')
        return None

    def get_id(self):
        return str(self.id)

    def get_prefset(self):
        return _toolsManager.get_prefset(self.id)

class _KoContainer(_KoTool):
    isContainer = True
    def __init__(self, *args):
        _KoTool.__init__(self, *args)
        
    def saveNewToolToDisk(self, path):
        raise Exception("Not implemented yet")

    def updateSelf(self):
        res = _tbdbSvc.getValuesFromTableByKey('common_details', ['name'], 'path_id', self.id)
        if res:
            self.name = res[0]
        else:
            self.name = "<Unknown item>"
            
class _KoFolder(_KoContainer):
    _com_interfaces_ = [components.interfaces.koIContainerBaseTool]
    typeName = 'folder'
    prettytype = 'Folder'
    _iconurl = _icons.get('folder')

    def trailblazeForPath(self, path):
        os.mkdir(path)
        
    def getChildren(self):
        return [_toolsManager.getToolById(id) for id in self.getChildIDs()]
    
    def getChildIDs(self):
        return _tbdbSvc.getChildIDs(self.id)
    
    def saveNewToolToDisk(self, path):
        path2 = join(path, koToolbox2.UI_FOLDER_FILENAME)
        data = {'id' : self.id,
                'name' : self.name,
                'type' : self.typeName,
                }
        fp = open(path2, 'w')
        data = json.dump(data, fp, encoding="utf-8", indent=2)
        fp.close()

    def save(self):
        # This handles only renames
        metadataPath = join(self.path, koToolbox2.UI_FOLDER_FILENAME)
        if not os.path.exists(metadataPath):
            self.saveNewToolToDisk(self.path)
        else:
            try:
                fp = open(metadataPath, 'r')
                try:
                    data = json.load(fp, encoding="utf-8")
                except:
                    log.exception("Couldn't load json data for path %s", path)
                fp.close()
            except:
                log.error("Couldn't open path %s", metadataPath)
            else:
                if data['name'] != self.name:
                    data['name'] = self.name
                    try:
                        fp = open(metadataPath, 'w')
                        try:
                            json.dump(data, fp, encoding="utf-8", indent=2)
                        except:
                            log.exception("Failed to write json data for path %s", path)
                        fp.close()
                    except:
                        log.exception("Failed to write to file %s", path)
        self._postSave()

    def getChildByName(self, name, recurse):
        id = _tbdbSvc.getChildByName(self.id, name, recurse)
        if id is None:
            return None
        return _toolsManager.getToolById(id)

    def getChildByTypeAndName(self, typeName, itemName, recurse):
        id = _tbdbSvc.getChildByTypeAndName(self.id, typeName, itemName, recurse)
        if id is None:
            return None
        return _toolsManager.getToolById(id)

    def addChild(self, item):
        raise Exception("Not implemented yet")

    def removeChild(self, item):
        # No need to reference the parent anymore.
        # Also, this is called only when the item isn't in the view.
        UnwrapObject(item).delete()
        
    
class _KoComplexContainer(_KoFolder):
    def trailblazeForPath(self, path):
        # Throw an error message if we can't create the file,
        # before we add an entry to the database.  But allow
        # for existing paths that weren't cleared earlier.
        if not os.path.exists(path):
            os.mkdir(path)
        elif not os.path.isdir(path):
            os.unlink(path)
            os.mkdir(path)
        path2 = join(path, koToolbox2.UI_FOLDER_FILENAME)
        fp = open(path2, 'w')
        fp.close()

    def saveNewToolToDisk(self, path):
        path2 = join(path, koToolbox2.UI_FOLDER_FILENAME)
        data = {}
        data['name'] = self.name
        data['type'] = self.typeName
        for name in self._attributes:
            data[name] = self._attributes[name]
        fp = open(path2, 'w')
        data = json.dump(data, fp, encoding="utf-8", indent=2)
        fp.close()

    def delete(self):
        notificationName = self.typeName + "_remove"
        # menu_remove and toolbar_remove notifications are done here
        try:
            self._getObserverSvc().notifyObservers(self, notificationName, notificationName)
        except Exception:
            pass
        _KoTool.delete(self)
        
    def getDragData(self):
        return self.getStringAttribute('name')

class _KoMenu(_KoComplexContainer):
    typeName = 'menu'
    prettytype = 'Custom Menu'
    _iconurl = _icons.get('menu')
    
    def __init__(self, *args):
        _KoComplexContainer.__init__(self, *args)
        self._attributes['accesskey'] = ''
        self._attributes['priority'] = 100

    def save(self):
        self.save_handle_attributes()
        _KoFolder.save(self)
        _tbdbSvc.saveMenuInfo(self.id, self.name, self._attributes)
    
class _KoToolbar(_KoComplexContainer):
    typeName = 'toolbar'
    prettytype = 'Custom Toolbar'
    _iconurl = _icons.get('toolbar')

    def __init__(self, *args):
        _KoComplexContainer.__init__(self, *args)
        self._attributes['priority'] = 100

    def save(self):
        self.save_handle_attributes()
        _KoFolder.save(self)
        _tbdbSvc.saveToolbarInfo(self.id, self.name, self._attributes)

class _KoCommandTool(_KoTool):
    typeName = 'command'
    prettytype = 'Run Command'
    _iconurl = _icons.get('terminal')
    
    def save(self):
        # Write the changed data to the file system
        self.save_handle_attributes()
        self.saveToolToDisk()
        _tbdbSvc.saveCommandInfo(self.id, self.name, self.value, self._attributes)
        self._postSave()
        _toolsManager.removeChangedCachedTool(self.id)

    def updateSelf(self):
        if self.initialized:
            return
        info = _tbdbSvc.getCommandInfo(self.id)
        self._finishUpdatingSelf(info)

class _KoMacroTool(_KoTool):
    _com_interfaces_ = [components.interfaces.koIMacroTool]
    typeName = 'macro'
    prettytype = 'Macro'
    _iconurl = _icons.get('macro')

    def __init__(self, *args):
        _KoTool.__init__(self, *args)
        self.flavors.insert(0, 'text/x-moz-url')
        self.name = "New Macro"
        self._attributes['language'] = 'JavaScript' 
        self._attributes['async'] = False
        self._attributes['trigger_enabled'] = False
        self._attributes['trigger'] = ""

    def delete(self):
        try:
            self._getObserverSvc().notifyObservers(self, 'macro-unload','')
        except Exception:
            pass
        _KoTool.delete(self)
        
    def updateSelf(self):
        if self.initialized:
            return
        info = _tbdbSvc.getMacroInfo(self.id)
        #log.debug("macro info: %s", info)
        self._finishUpdatingSelf(info)

    def get_url(self):
        if self._attributes['language'] == 'JavaScript':
            ext = ".js"
        elif self._attributes['language'] == 'Python':
            ext = ".py"
        # The important parts are the ID and the extension, so the
        # name itself can be sluggified so the autosave routine
        # doesn't get caught up with special characters in the name.
        return "macro2://%s/%s%s" % (self.id, koToolbox2.slugify(self.name), ext)
        
    def save(self):
        # Write the changed data to the file system
        self.saveContentToDisk()
        _tbdbSvc.saveContent(self.id, self.value)
        _tbdbSvc.saveMacroInfo(self.id, self.name, self.value, self._attributes)
        self._postSave()
        _toolsManager.removeChangedCachedTool(self.id)

    def saveProperties(self):
        # Write the changed data to the file system
        self.saveToolToDisk()
        _tbdbSvc.saveMacroInfo(self.id, self.name, self.value, self._attributes)

    def _asyncMacroCheck(self, async):
        if async:
            lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"]\
                .getService(components.interfaces.koILastErrorService)
            err = "Asynchronous python macros not yet implemented"
            lastErrorSvc.setLastError(1, err)
            raise ServerException(nsError.NS_ERROR_ILLEGAL_VALUE, err)

    def evalAsPython(self, domdocument, window, scimoz, koDoc,
                     view, code, async):
        self._asyncMacroCheck(async)
        projectUtils.evalPythonMacro(WrapObject(self,self._com_interfaces_[0]),
                        domdocument, window, scimoz, koDoc, view, code)
        
    def evalAsPythonObserver(self, domdocument, window, scimoz, koDoc,
                             view, code, async, subject, topic, data):
        self._asyncMacroCheck(async)
        projectUtils.evalPythonMacro(WrapObject(self,self._com_interfaces_[0]),
                        domdocument, window, scimoz, koDoc, view, code,
                        subject, topic, data)

    def get_project(self):
        return components.classes["@activestate.com/koPartService;1"]\
                .getService(components.interfaces.koIPartService).currentProject

class _KoSnippetTool(_KoTool):
    typeName = 'snippet'
    prettytype = 'Snippet'
    _iconurl = _icons.get('cut')

    def __init__(self, *args):
        _KoTool.__init__(self, *args)
        self.flavors.insert(0, 'application/x-komodo-snippet')


    def get_url(self):
        """
        See _KoMacroTool.get_url for docs
        """
        return "snippet2://%s/%s.snippet" % (self.id, koToolbox2.slugify(self.name))

    def save(self):
        # Write the changed data to the file system
        self.save_handle_attributes()
        self.saveToolToDisk()
        _tbdbSvc.saveSnippetInfo(self.id, self.name, self.value, self._attributes)
        self._postSave()
        _toolsManager.removeChangedCachedTool(self.id)

    def updateSelf(self):
        if self.initialized:
            return
        info = _tbdbSvc.getSnippetInfo(self.id)
        self._finishUpdatingSelf(info)

    def getDragDataByFlavor(self, flavor):
        if flavor == 'application/x-komodo-snippet':
            return str(self.id)
        elif flavor in ('text/unicode', 'text/plain'):
            return self._getSnippetDragDataAsText()
        else:
            return _KoTool.getDragDataByFlavor(self, flavor)
        
    def getDragData(self):
        return self._getSnippetDragDataAsText()
        
    _ANCHOR_MARKER = '!@#_anchor'
    _CURRENTPOS_MARKER = '!@#_currentPos'
    def _getSnippetDragDataAsText(self):
        # NOTE: IT IS IMPORTANT THAT IF UNICODE COMES IN, UNICODE GOES OUT!
        return self.value.replace(self._ANCHOR_MARKER, "", 1).replace(self._CURRENTPOS_MARKER, "", 1)


class _KoURLToolBase(_KoTool):
    def setStringAttribute(self, name, value):
        _KoTool.setStringAttribute(self, name, value)
        if name == 'value':
            # Komodo treats the value as a URI to get a koFileEx object.
            _KoTool.setStringAttribute(self, 'url', value)
            
    def save(self):
        self.save_handle_attributes()
        # Write the changed data to the file system
        self.saveToolToDisk()
        _tbdbSvc.saveSimpleToolInfo(self.id, self.name, self.value, self._attributes)
        self._postSave()
        _toolsManager.removeChangedCachedTool(self.id)

    def updateSelf(self):
        if self.initialized:
            return
        info = _tbdbSvc.getSimpleToolInfo(self.id)
        self._finishUpdatingSelf(info)
        
class _KoTemplateTool(_KoURLToolBase):
    typeName = 'template'
    prettytype = 'Template'
    _iconurl = _icons.get('template')

class _KoURLTool(_KoURLToolBase):
    typeName = 'URL'
    prettytype = 'URL'
    _iconurl = _icons.get('url')


_koToolClassFromTypeName = {}
for _obj in globals().values():
    if (isinstance(_obj, type) and issubclass(_obj, _KoTool)
        and getattr(_obj, "typeName", None)):
        _koToolClassFromTypeName[_obj.typeName] = _obj



#---- tool manager
    
class KoToolbox2ToolManager(object):
    """
    This singleton class creates new tools, and caches existing
    tools by ID.  It acts as an intermediary between the
    front-end, loaded tools, and the toolbox database.
    """
    _com_interfaces_ = [components.interfaces.nsIObserver,
                        components.interfaces.koIToolbox2ToolManager]
    _reg_clsid_ = "{2db1d469-6745-4691-8657-67118371d866}"
    _reg_contractid_ = "@activestate.com/koToolbox2ToolManager;1"
    _reg_desc_ = "KoToolbox2 Tools Manager"

    def __init__(self, debug=None):
        self.toolbox_db = None
        self._tools = {}  # Map a tool's id to a constructed object
        global eol, _toolsManager
        if eol is None:
            eol = eollib.eol2eolStr[eollib.EOL_PLATFORM]
        _observerSvc = components.classes["@mozilla.org/observer-service;1"].\
            getService(components.interfaces.nsIObserverService)
        _observerSvc.addObserver(self, 'xpcom-shutdown', 0)
        _observerSvc.addObserver(self, 'tool-deleted', 0)
        _toolsManager = self

    def initialize(self, toolbox_db_svc):
        global _tbdbSvc
        _tbdbSvc = self.toolbox_db = toolbox_db_svc
        self._koToolbox2Service = UnwrapObject(components.classes["@activestate.com/koToolbox2Service;1"].getService(components.interfaces.koIToolbox2Service))
        self._koProjectService = UnwrapObject(components.classes["@activestate.com/koPartService;1"].getService(components.interfaces.koIPartService))
        self._globalPrefs = components.classes["@activestate.com/koPrefService;1"].\
                       getService(components.interfaces.koIPrefService).prefs

    def terminate(self):
        pass # placeholder

    def observe(self, subject, topic, data):
        #log.debug("KoToolbox2ToolManager:observe: subject:%r, topic:%r, data:%r", subject, topic, data)
        if topic == 'xpcom-shutdown':
            observerSvc = components.classes["@mozilla.org/observer-service;1"].\
                           getService(components.interfaces.nsIObserverService)
            observerSvc.removeObserver(self, 'xpcom-shutdown')
            observerSvc.removeObserver(self, 'tool-deleted')
        elif topic == 'tool-deleted':
            try:
                id = int(data)
                del self._tools[id]
            except KeyError:
                pass

    def set_hierarchicalView(self, view):
        self.hierarchicalView = view

    #---- Main methods
    #Non-XPCOM -- call from the view
    def addNewItemToParent(self, parent, item, showNewItem=True):
        """
        This code has a model part and a view part.  Call the view
        part if we need to update it.
        """
        #TODO: if parent is null, use the std toolbox node
        item = UnwrapObject(item)
        parent = UnwrapObject(parent)
        parent_path = self.toolbox_db.getPath(parent.id)
        item_name = item.name
        itemIsContainer = item.isContainer
        if itemIsContainer:
            # Bug 96486: Can't create folders named "*" on Windows
            # Now that we're encouraging people to create folders with this name,
            # we need to quietly change the "*"s to "_"s.  I don't
            # remember why I decided not to do this in general.
            system_item_name = item_name.replace("*", "_")
            
            # Don't do anything else to this name.  If there's a dup, or
            # it contains bad characters, give the user the actual
            # error message.  Which is why we need to try creating
            # the folder first, before adding its entry.
            path = join(parent_path, system_item_name)
            if system_item_name != item_name:
                # Make sure it's new
                if os.path.exists(path):
                    for i in range(20):
                        suffix = i + 1
                        new_path = "%s-%d" % (path, suffix)
                        if not os.path.exists(new_path):
                            path = new_path
                            break
            item.trailblazeForPath(path)
        else:
            path = self._prepareUniqueFileSystemName(parent_path, item_name)
        try:
            itemDetailsDict = {}
            item.fillDetails(itemDetailsDict)
            if itemIsContainer:
                new_id = self.toolbox_db.addContainerItem(itemDetailsDict,
                                                          item.typeName,
                                                          path,
                                                          item_name,
                                                          parent.id)
            else:
                new_id = self.toolbox_db.addTool(itemDetailsDict,
                                                 item.typeName,
                                                 path,
                                                 item_name,
                                                 parent.id)
                
            old_id = item.id
            item.id = new_id
            # Even if the old and new IDs are the same, we don't want
            # to keep the old item in the cache.
            try:
                del self._tools[old_id]
            except KeyError:
                log.error("No self._tools[%r]", old_id)
            self._tools[new_id] = item
            item.saveNewToolToDisk(path)
            if showNewItem:
                self._koToolboxHView.addNewItemToParent(parent, item)
            item.added()
        except:
            log.exception("addNewItemToParent: failed")
            raise

    def _prepareUniqueFileSystemName(self, dirName, baseName, ext=None):
        if ext is None:
            ext = koToolbox2.TOOL_EXTENSION
        # "slugify"
        basePart = koToolbox2.truncateAtWordBreak(re.sub(r'[^\w\d\-=\+]+', '_', baseName))
        basePart = join(dirName, basePart)
        candidate = basePart + ext
        if not os.path.exists(candidate):
            return candidate
        for i in range(1, 1000):
            candidate = "%s-%d%s" % (basePart, i, ext)
            if not os.path.exists(candidate):
                #log.debug("Writing out file %s/%s as %s", os.getcwd(), basePart, candidate)
                return candidate
        else:
            raise Exception("File %s exists in directory %s, force is off" %
                            (name, os.getcwd()))
        
    def createToolFromExistingTool(self, targetPath, srcPath):
        try:
            fp = open(srcPath, 'r')
        except:
            log.error("Failed to open %s", srcPath)
            raise
        try:
            data = json.load(fp, encoding="utf-8")
        except:
            log.exception("Failed to json load %s", srcPath)
            raise
        finally:
            fp.close()
        try:
            typeName = data['type']
        except KeyError:
            #XXX: Collect this, alert the user
            log.error("_pasteItemIntoTarget: no type field in tool %s", srcPath)
            return
        try:
            del data['id']
        except KeyError:
            pass
        newItem = self.createToolFromType(data['type'])
        # Value strings in .komodotool files are stored as an array of lines
        # In the database they're stored as a single string.
        # Convert into the database type, as that's what
        # _finishUpdatingSelf expects
        if 'value' in data:
            data['value'] = eol.join(data['value'])
        newItem._finishUpdatingSelf(data)
        return newItem

    def createToolFromType(self, tool_type):
        id = self.toolbox_db.getNextID()
        tool = _koToolClassFromTypeName[tool_type](None, id) # no name yet
        # Should be no worries if the user cancels on this.
        # The tool with this ID won't be in the database or the tree,
        # so the only way to hit this ID again is via this method,
        # and that assigns a new tool to self._tools[id]
        self._tools[id] = tool
        tool.temporary = True
        return tool

    #Non-XPCOM
    def deleteTool(self, tool_id):
        """This was called from the view, so it doesn't need to
        make sure the view is cleaned up."""
        tool = self.getToolById(tool_id)
        try:
            del self._tools[tool_id]
        except KeyError:
            pass
        res = self.toolbox_db.getValuesFromTableByKey('hierarchy',
                                                      ['parent_path_id'],
                                                      'path_id', tool_id)
        if res:
            parent_tool = self._tools.get(res[0], None)
        else:
            parent_tool = None
        tool.delete()
        
    def getToolsByTypeAndName(self, toolType, name):
        ids = self.toolbox_db.getToolsByTypeAndName(toolType, name)
        return [self.getToolById(id) for id in ids]

    def getAbbreviationSnippet(self, abbrev, subnames, isAutoAbbrev):
        id = self.toolbox_db.getAbbreviationSnippetId(abbrev, subnames, isAutoAbbrev)
        if id is None:
            return None
        tool = self.getToolById(id)
        if tool:
            # Snippets need to be fully initialized
            tool.updateSelf()
        return tool

    def getOrCreateTool(self, node_type, name, path_id):
        tool = self._tools.get(path_id, None)
        if tool is not None:
            try:
                tool.updateSelf()
                return tool
            except TypeError:
                # Bug 88571
                log.exception("getOrCreateTool(node_type:%r, name:%s, path_id:%s)",
                              node_type, name, path_id)
                pass
        tool = _koToolClassFromTypeName[node_type](name, path_id)
        tool.getCustomIconIfExists()
        self._tools[path_id] = tool
        return tool
    
    def getToolById(self, path_id):
        path_id = int(path_id)
        if path_id not in self._tools:
            res = self.toolbox_db.getValuesFromTableByKey('common_details', ['type', 'name'], 'path_id', path_id)
            if res is None:
                return None
            tool = _koToolClassFromTypeName[res[0]](res[1], path_id)
            self._cullCache()
            self._tools[path_id] = tool
        else:
            tool = self._tools[path_id]
        if not tool.temporary:
            tool.updateSelf()
        return tool

    MAX_CACHED_TOOL_SIZE = 1000
    def _cullCache(self):
        """
        Until we track the relevance of tools, just randomly select
        5% of them to delete each time.
        """
        if len(self._tools) < self.MAX_CACHED_TOOL_SIZE:
            return
        size = self.MAX_CACHED_TOOL_SIZE // 20 # py3-compatible int-divide
        subset = random.sample(self._tools, size)
        for id in subset:
            del self._tools[id]

    def getToolFromPath(self, path):
        res = self.toolbox_db.getValuesFromTableByKey('paths', ['id'], 'path', path)
        if not res:
            return None
        return self.getToolById(res[0])
    
    def getCustomMenus(self, dbPath):
        ids = self.toolbox_db.getIDsByType('menu', dbPath)
        return self._getFullyRealizedToolById(ids)
    
    def getCustomToolbars(self, dbPath):
        ids = self.toolbox_db.getIDsByType('toolbar', dbPath)
        return self._getFullyRealizedToolById(ids)
        return self.getToolById(res[0])
    
    def getToolsWithKeyboardShortcuts(self, dbPath):
        ids = self.toolbox_db.getIDsForToolsWithKeyboardShortcuts(dbPath)
        return self._getFullyRealizedToolById(ids)
    
    def getTriggerMacros(self, dbPath):
        ids = self.toolbox_db.getTriggerMacroIDs(dbPath)
        return self._getFullyRealizedToolById(ids)

    def _getFullyRealizedToolById(self, ids):
        # We load tools lazily, so make sure these have the keyboard
        # shortcuts and other info in them.
        tools = []
        for id in ids:
            tool = self.getToolById(id)
            if tool:
                # Trigger macros need to be fully initialized,
                # since they can be invoked
                tool.updateSelf()
                tools.append(tool)
        return tools

    def _renameObject(self, id, newName, isContainer):
        tool = self.getToolById(id)
        parentTool = tool.get_parent()
        if parentTool is None:
            raise ServerException(nsError.NS_ERROR_ILLEGAL_VALUE,
                                  "Can't rename a top-level folder")
        oldPath = tool.path
        if isContainer:
            newPathOnDisk = self._prepareUniqueFileSystemName(parentTool.path, newName, ext="")
        else:
            newPathOnDisk = self._prepareUniqueFileSystemName(parentTool.path,
                                                              newName)
        os.rename(oldPath, newPathOnDisk)
        
        # Update the name field in the json tool
        try:
            fp = open(newPathOnDisk, 'r')
            data = json.load(fp, encoding="utf-8")
            fp.close()
            if data['name'] != newName:
                # If these are the same, we're doing a null rename, but
                # treat that as an anomaly.
                pass
            data['name'] = newName;
            fp = open(newPathOnDisk, 'w')
            json.dump(data, fp, encoding="utf-8", indent=2)
            fp.close()
        except:
            log.exception("Failed to update json on old path:%s, newName:%s",
                          newPathOnDisk, newName)
        # There shouldn't be an exception in the database.
        self.toolbox_db.renameTool(id, newName, newPathOnDisk)
        try:
            # Remove this item from the cache, since its name changed.
            del self._tools[id]
        except KeyError:
            pass
        if isContainer:
            # Update the paths of all child nodes.
            ids = self.toolbox_db.updateChildPaths(id, oldPath, newPathOnDisk)
            for id in ids:
                try:
                    # Remove this item from the cache, since its name changed.
                    del self._tools[id]
                except KeyError:
                    pass
        return newPathOnDisk
        

    def renameContainer(self, id, newName):
        self._renameObject(id, newName, isContainer=True)

    def renameItem(self, id, newName):
        self._renameObject(id, newName, isContainer=False)

    def removeChangedCachedTool(self, id):
        try:
            del self._tools[id]
        except:
            pass

    def getToolRoot(self, id):
        return self.toolbox_db.getRootId(id)

    # Commands: get the prefset for a command by getting it either
    # from the current project, if that's who owns the tool,
    # or use the global prefs.

    def get_prefset(self, toolId):
        rootId = self.getToolRoot(toolId)
        projectURL = self._koToolbox2Service.getProjectURL(rootId)
        if projectURL is not None:
            proj = self._koProjectService.getProjectForURL(projectURL)
            if proj is not None:
                return proj.prefset
        return self._globalPrefs
