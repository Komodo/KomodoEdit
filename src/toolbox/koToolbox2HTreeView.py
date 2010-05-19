from xpcom import components, ServerException, COMException, nsError
from xpcom._xpcom import PROXY_SYNC, PROXY_ALWAYS, PROXY_ASYNC, getProxyForObject
from xpcom.server import WrapObject, UnwrapObject
 
import json, sys, os, re, types, string, threading
from koTreeView import TreeView

import eollib
import koToolbox2

import logging

log = logging.getLogger("Toolbox2HTreeView")
log.setLevel(logging.DEBUG)

eol = None

"""
Manage a hierarchical view of the loaded tools
"""

class _KoTool(object):
    _com_interfaces_ = [components.interfaces.koITool]
    isContainer = False
    def __init__(self, name, id):
        self.name = name
        self.id = id  # path_id in DB
        self.initialized = False
        self._attributes = {}
        self._nondb_attributes = {}
        self._referenced_url = None  # Refers to the URL referenced by the tool, not its location
        
    def init(self, treeView):
        pass

    def getCustomIconIfExists(self, tbdbSvc):
        iconurl = tbdbSvc.getCustomIconIfExists(self.id)
        if iconurl:
            self.set_iconurl(iconurl)
        return iconurl is not None

    def _finishUpdatingSelf(self, info):
        for name in ['value', 'name']:
            if name in info:
                setattr(self, name, info[name])
                del info[name]
        for key, value in info.items():
            self._attributes[key] = value

    # Attributes...
    def get_toolType(self):
        return self.typeName

    def get_value(self):
        return self.value
    
    def hasAttribute(self, name):
        # Keep names out of attributes
        if name == 'name':
            return True
        return self._attributes.has_key(name)

    def getAttribute(self, name):
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
        return int(self._attributes[name])

    def setLongAttribute(self, name, value):
        self.setAttribute(name, int(value))

    def getBooleanAttribute(self, name):
        return self.getLongAttribute(name) and 1 or 0

    def setBooleanAttribute(self, name, value):
        self.setAttribute(name, value and 1 or 0)

    def get_prefset(self):
        #XXX TODO! Work out where prefs live in toolbox2
        prefset = components.classes["@activestate.com/koPreferenceSet;1"] \
                  .createInstance(components.interfaces.koIPreferenceSet)
        return prefset

    def saveToolToDisk(self, tbdbSvc):
        if 'path' not in self._nondb_attributes:
            self._nondb_attributes['path'] = tbdbSvc.getPath(self.id)
        path = self._nondb_attributes['path']
        fp = open(path, 'r')
        data = json.load(fp, encoding="utf-8")
        fp.close()
        data['value'] = self.value.split(eol)
        data['name'] = self.name
        for name in self._attributes:
            data[name] = self._attributes[name]
        fp = open(path, 'w')
        data = json.dump(data, fp, encoding="utf-8")
        fp.close()
        
    def saveContentToDisk(self, tbdbSvc):
        if 'path' not in self._nondb_attributes:
            self._nondb_attributes['path'] = tbdbSvc.getPath(self.id)
        path = self._nondb_attributes['path']
        fp = open(path, 'r')
        data = json.load(fp, encoding="utf-8")
        fp.close()
        data['value'] = self.value.split(eol)
        data['name'] = getattr(self, 'name', data['name'])
        for attr in self._attributes:
            newVal = self._attributes[attr]
            if attr not in data or newVal != data[attr]:
                data[attr] = self._attributes[attr]
        fp = open(path, 'w')
        data = json.dump(data, fp, encoding="utf-8")
        fp.close()

    def save_handle_attributes(self):
        names = ['name', 'value']
        for name in names:
            if name in self._attributes:
                log.debug("Removing self._attributes %s = %s", name,
                          self._attributes[name])
                setattr(self, name, self._attributes[name])
                del self._attributes[name]

    def save(self):
        raise ServerException(nsError.NS_ERROR_ILLEGAL_VALUE,
                              ("save not yet implemented for %s"
                               % self.get_toolType()))

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
    
    def get_keybinding_description(self):
        return self.prettytype + "s: " + self.name

    #TODO: Reinstate handling of relative uri's
    def get_iconurl(self):
        if self._attributes.has_key('icon'):
            return self._attributes['icon']
        else:
            return self._iconurl

    def set_iconurl(self, url):
        if not url or url == self._iconurl:
            self.removeAttribute('icon')
        else:
            self.setAttribute('icon', url)
            
    def get_type(self):
        return self.typeName

    def set_type(self, value):
        self.typeName = value
        
    def set_name(self, name):
        self.name = name

    def get_name(self):
        return self.name

   
class _KoContainer(_KoTool):
    isContainer = True
    def __init__(self, *args):
        self.childNodes = []
        self.isOpen = False
        _KoTool.__init__(self, *args)
        
    def init(self, treeView):
        self.childNodes = treeView.toolbox_db.getChildNodes(self.id)
        self.initialized = True

class _KoFolder(_KoContainer):
    typeName = 'folder'
    prettytype = 'Folder'
    _iconurl = 'chrome://komodo/skin/images/folder-closed-pink.png'

class _KoMenu(_KoContainer):
    typeName = 'menu'
    prettytype = 'Custom Menu'
    _iconurl = 'chrome://komodo/skin/images/menu_icon.png'

class _KoToolbar(_KoContainer):
    typeName = 'toolbar'
    prettytype = 'Custom Toolbar'
    _iconurl = 'chrome://komodo/skin/images/toolbar_icon.png'

class _KoCommandTool(_KoTool):
    typeName = 'command'
    prettytype = 'Run Command'
    _iconurl = 'chrome://komodo/skin/images/run_commands.png'
    keybindable = 1

    def save(self):
        tbdbSvc = UnwrapObject(components.classes["@activestate.com/KoToolboxDatabaseService;1"].\
                       getService(components.interfaces.koIToolboxDatabaseService))
        # Write the changed data to the file system
        self.save_handle_attributes()
        self.saveToolToDisk(tbdbSvc)
        tbdbSvc.saveCommandInfo(self.id, self.name, self.value, self._attributes)
    def updateSelf(self, toolbox_db):
        info = toolbox_db.getCommandInfo(self.id)
        self._finishUpdatingSelf(info)

class _KoURL_LikeTool(_KoTool):
    def setStringAttribute(self, name, value):
        _KoTool.setStringAttribute(self, name, value)
        if name == 'value':
            # Komodo treats the value as a URI to get a koFileEx object.
            _KoTool.setStringAttribute(self, 'url', value)
            
    def save(self):
        tbdbSvc = UnwrapObject(components.classes["@activestate.com/KoToolboxDatabaseService;1"].\
                       getService(components.interfaces.koIToolboxDatabaseService))
        self.save_handle_attributes()
        # Write the changed data to the file system
        self.saveToolToDisk(tbdbSvc)
        tbdbSvc.saveSimpleToolInfo(self.id, self.name, self.value, self._attributes)
    def updateSelf(self, toolbox_db):
        info = toolbox_db.getSimpleToolInfo(self.id)
        self._finishUpdatingSelf(info)

class _KoDirectoryShortcutTool(_KoURL_LikeTool):
    typeName = 'DirectoryShortcut'
    prettytype = 'Open... Shortcut'
    keybindable = 1
    _iconurl = 'chrome://komodo/skin/images/open.png'

class _KoMacroTool(_KoTool):
    _com_interfaces_ = [components.interfaces.koITool]
    typeName = 'macro'
    prettytype = 'Macro'
    _iconurl = 'chrome://komodo/skin/images/macro.png'
    keybindable = 1

    def updateSelf(self, toolbox_db):
        info = toolbox_db.getMacroInfo(self.id)
        #log.debug("macro info: %s", info)
        self._finishUpdatingSelf(info)

    def get_url(self):
        if self._attributes['language'] == 'JavaScript':
            ext = ".js"
        elif self._attributes['language'] == 'Python':
            ext = ".py"
        return "macro2://%s/%s%s" % (self.id, self.name, ext)
        
    def save(self):
        tbdbSvc = UnwrapObject(components.classes["@activestate.com/KoToolboxDatabaseService;1"].\
                       getService(components.interfaces.koIToolboxDatabaseService))
        # Write the changed data to the file system
        self.saveContentToDisk(tbdbSvc)
        tbdbSvc.saveContent(self.id, self.value)
        tbdbSvc.saveMacroInfo(self.id, self.name, self.value, self._attributes)

    def saveProperties(self):
        tbdbSvc = UnwrapObject(components.classes["@activestate.com/KoToolboxDatabaseService;1"].\
                       getService(components.interfaces.koIToolboxDatabaseService))
        # Write the changed data to the file system
        self.saveToolToDisk(tbdbSvc)
        tbdbSvc.saveMacroInfo(self.id, self.name, self.value, self._attributes)

class _KoSnippetTool(_KoTool):
    typeName = 'snippet'
    prettytype = 'Snippet'
    _iconurl = 'chrome://komodo/skin/images/snippet.png'
    keybindable = 1

    def save(self):
        tbdbSvc = UnwrapObject(components.classes["@activestate.com/KoToolboxDatabaseService;1"].\
                       getService(components.interfaces.koIToolboxDatabaseService))
        # Write the changed data to the file system
        self.save_handle_attributes()
        self.saveToolToDisk(tbdbSvc)
        tbdbSvc.saveSnippetInfo(self.id, self.name, self.value, self._attributes)

    def updateSelf(self, toolbox_db):
        info = toolbox_db.getSnippetInfo(self.id)
        self._finishUpdatingSelf(info)

class _KoTemplateTool(_KoURL_LikeTool):
    typeName = 'template'
    prettytype = 'Template'
    _iconurl = 'chrome://komodo/skin/images/newTemplate.png'

class _KoURLTool(_KoURL_LikeTool):
    typeName = 'URL'
    prettytype = 'URL'
    _iconurl = 'chrome://komodo/skin/images/xlink.png'
    keybindable = 1

class KoToolbox2HTreeView(TreeView):
    _com_interfaces_ = [components.interfaces.nsIObserver,
                        components.interfaces.koIToolbox2HTreeView,
                        components.interfaces.nsITreeView]
    _reg_clsid_ = "{7b345b58-bae7-4e0b-9a49-30119a1ffd29}"
    _reg_contractid_ = "@activestate.com/KoToolbox2HTreeView;1"
    _reg_desc_ = "KoToolbox2 Hierarchical TreeView"

    def __init__(self, debug=None):
        TreeView.__init__(self, debug=0)
        self._rows = []
        self._tree = None
        self.toolbox_db = None
        self._tools = {}  # Map a tool's id to a constructed object
        global eol
        if eol is None:
            eol = eollib.eol2eolStr[eollib.EOL_PLATFORM]

    def _getOrCreateTool(self, node_type, name, path_id):
        tool = self._tools.get(path_id, None)
        if tool is not None:
            return tool
        tool = createPartFromType(node_type, name, path_id)
        tool.init(self)
        tool.getCustomIconIfExists(self.toolbox_db)
        self._tools[path_id] = tool
        return tool

    def getToolById(self, path_id):
        path_id = int(path_id)
        if path_id not in self._tools:
            tool_type, name = self.toolbox_db.getValuesFromTableByKey('common_details', ['type', 'name'], 'path_id', path_id)
            tool = createPartFromType(tool_type, name, path_id)
            self._tools[path_id] = tool
        return self._tools[path_id]
    
    def getIndexByTool(self, tool):
        tool = UnwrapObject(tool)
        try:
            return self._rows.index(tool)
        except ValueError, e:
            return -1
        
        
    def initialize(self):
        #XXX Unhardwire this
        db_path = r"c:\Users\ericp\trash\toolbox-test.sqlite"
        schemaFile = r"c:\Users\ericp\svn\apps\komodo\src\toolbox\koToolbox.sql"
        stdToolboxDir = r"c:\Users\ericp\trash\stdToolbox"
        sharedToolboxDir = r"c:\Users\ericp\trash\sharedToolbox"

        toolboxLoader = koToolbox2.ToolboxLoader(db_path, schemaFile)
        toolboxLoader.markAllTopLevelItemsUnloaded()
        import time
        t1 = time.time()
        toolboxLoader.loadToolboxDirectory(stdToolboxDir)
        t2 = time.time()
        log.debug("Time to load std-toolbox: %g msec", (t2 - t1) * 1000.0)
        t1 = time.time()
        toolboxLoader.loadToolboxDirectory(sharedToolboxDir)
        t2 = time.time()
        log.debug("Time to load shared-toolbox: %g msec", (t2 - t1) * 1000.0)
        toolboxLoader.deleteUnloadedTopLevelItems()
        #TODO: For now just get the top-level items
        # Later keep track of how 
        self.toolbox_db = UnwrapObject(components.classes["@activestate.com/KoToolboxDatabaseService;1"].\
                       getService(components.interfaces.koIToolboxDatabaseService))
        self.toolbox_db.initialize(db_path)
        self.toolbox_db.toolManager = self
        top_level_nodes = self.toolbox_db.getTopLevelNodes()
        before_len = len(self._rows)
        for path_id, name, node_type in top_level_nodes:
            toolPart = self._getOrCreateTool(node_type, name, path_id)
            toolPart.level = 1
            self._rows.append(toolPart)
        after_len = len(self._rows)
        self._tree.rowCountChanged(0, after_len - before_len)

    def getTool(self, index):
        try:
            tool = self._rows[index]
        except IndexError:
            log.error("Failed getTool(index:%d)", index)
            return None
        if not tool.initialized:
            tool.updateSelf(self.toolbox_db)
        return tool

    def get_toolType(self, index):
        return self._rows[index].typeName
        
    #---- nsITreeView Methods
    
    def get_rowCount(self):
        return len(self._rows)

    def getCellText(self, index, column):
        col_id = column.id
        assert col_id == "Name"
        #log.debug(">> getCellText:%d, %s", row, col_id)
        try:
            return self._rows[index].name
        except AttributeError:
            log.debug("getCellText: No id %s at row %d", col_id, row)
            return "?"
        
    def getImageSrc(self, index, column):
        col_id = column.id
        assert col_id == "Name"
        try:
            return self._rows[index].get_iconurl()
        except:
            return ""
        
    def isContainer(self, index):
        return self._rows[index].isContainer
        
    def isContainerOpen(self, index):
        node = self._rows[index]
        return node.isContainer and node.isOpen
        
    def isContainerEmpty(self, index):
        node = self._rows[index]
        return node.isContainer and not node.childNodes

    def getParentIndex(self, index):
        if index >= len(self._rows) or index < 0: return -1
        try:
            i = index - 1
            level = self._rows[index].level
            while i >= 0 and self._rows[i].level >= level:
                i -= 1
        except IndexError:
            i = -1
        return i

    def hasNextSibling(self, index, afterIndex):
        if index >= len(self._rows) or index < 0: return 0
        try:
            current_level = self._rows[index].level
            for next_row in self._rows[afterIndex + 1:]:
                next_row_level = next_row.level
                if next_row_level < current_level:
                    return 0
                elif next_row_level == current_level:
                    return 1
        except IndexError:
            pass
        return 0
    
    def getLevel(self, index):
        try:
            return self._rows[index].level
        except IndexError:
            return -1
                                                
    def setTree(self, tree):
        self._tree = tree
        
    def getNextSiblingIndex(self, index):
        """
        @param index {int} points to the node whose next-sibling we want to find.
        @return index of the sibling, or -1 if not found.
        """
        level = self._rows[index].level
        lim = len(self._rows)
        index += 1
        while index < lim:
            if self._rows[index].level <= level:
                return index
            index += 1
        return -1

    def toggleOpenState(self, index):
        rowNode = self._rows[index]
        if rowNode.isOpen:
            nextIndex = self.getNextSiblingIndex(index)
            #qlog.debug("toggleOpenState: index:%d, nextIndex:%d", index, nextIndex)
            if nextIndex == -1:
                # example: index=5, have 13 rows,  delete 7 rows [6:13), 
                numNodesRemoved = len(self._rows) - index - 1
                del self._rows[index + 1:]
            else:
                # example: index=5, have 13 rows, next sibling at index=10
                # delete rows [6:10): 4 rows
                numNodesRemoved = nextIndex - index - 1
                del self._rows[index + 1: nextIndex]
            #qlog.debug("toggleOpenState: numNodesRemoved:%d", numNodesRemoved)
            if numNodesRemoved:
                self._tree.rowCountChanged(index + 1, -numNodesRemoved)
                #log.debug("index:%d, numNodesRemoved:%d, numLeft:%d", index, numNodesRemoved, len(self._rows))
            rowNode.isOpen = False
        else:
            childNodes = sorted(rowNode.childNodes, cmp=self._compareChildNode)
            if childNodes:
                posn = index + 1
                for path_id, name, node_type in childNodes:
                    toolPart = self._getOrCreateTool(node_type, name, path_id)
                    toolPart.level = rowNode.level + 1
                    self._rows.insert(posn, toolPart)
                    posn += 1
                #qlog.debug("rowCountChanged: index: %d, numRowChanged: %d", index, numRowChanged)
                self._tree.rowCountChanged(index, len(childNodes))
                # self._tree.scrollToRow(firstVisibleRow)
                rowNode.isOpen = True
                
            
    def _compareChildNode(self, item1, item2):
        return cmp(item1[1].lower(), item2[1].lower())

_partFactoryMap = {}
for name, value in globals().items():
    if isinstance(value, object) and getattr(value, 'typeName', ''):
        _partFactoryMap[value.typeName] = value

def createPartFromType(type, *args):
    if type == "project":
        project = _partFactoryMap[type]()
        project.create()
        return project
    return _partFactoryMap[type](*args)

