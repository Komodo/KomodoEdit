from xpcom import components, COMException
from xpcom._xpcom import PROXY_SYNC, PROXY_ALWAYS, PROXY_ASYNC, getProxyForObject
from xpcom.server import WrapObject, UnwrapObject
 
import sys, os, re, types, string, threading
from koTreeView import TreeView

import koToolbox2

import logging

log = logging.getLogger("Toolbox2HTreeView")
log.setLevel(logging.DEBUG)

"""
Manage a hierarchical view of the loaded tools
"""

class _KoTool(object):
    isContainer = False
    def __init__(self, name, id, level):
        self.name = name
        self.id = id  # path_id in DB
        self.level = level
        self.initialized = False
        
    def init(self, treeView):
        pass
        
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
    type = 'folder'
    prettytype = 'Folder'
    _iconurl = 'chrome://komodo/skin/images/folder-closed.png'

class _KoMenu(_KoContainer):
    type = 'menu'
    prettytype = 'Custom Menu'
    _iconurl = 'chrome://komodo/skin/images/menu_icon.png'

class _KoToolbar(_KoContainer):
    type = 'toolbar'
    prettytype = 'Custom Toolbar'
    _iconurl = 'chrome://komodo/skin/images/toolbar_icon.png'

class _KoCommandTool(_KoTool):
    type = 'command'
    prettytype = 'Run Command'
    _iconurl = 'chrome://komodo/skin/images/run_commands.png'
    keybindable = 1

class _KoDirectoryShortcutTool(_KoTool):
    type = 'DirectoryShortcut'
    prettytype = 'Open... Shortcut'
    keybindable = 1
    _iconurl = 'chrome://komodo/skin/images/open.png'

class _KoMacroTool(_KoTool):
    type = 'macro'
    prettytype = 'Macro'
    _iconurl = 'chrome://komodo/skin/images/macro.png'
    keybindable = 1

class _KoSnippetTool(_KoTool):
    type = 'snippet'
    prettytype = 'Snippet'
    _iconurl = 'chrome://komodo/skin/images/snippet.png'
    keybindable = 1

class _KoURLTool(_KoTool):
    type = 'URL'
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
        
    def initialize(self):
        # For now just get the top-level items
        #XXX Unhardwire this
        log.debug(">> initialize")
        self.toolbox_db = koToolbox2.ToolboxAccessor(r"c:\Users\ericp\trash\toolbox-test.sqlite")
        top_level_nodes = self.toolbox_db.getTopLevelNodes()
        before_len = len(self._rows)
        for path_id, name, node_type in top_level_nodes:
            toolPart = createPartFromType(node_type, name, path_id, 0)
            toolPart.init(self)
            self._rows.append(toolPart)
        after_len = len(self._rows)
        self._tree.rowCountChanged(0, after_len - before_len)
        
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
            return self._rows[index]._iconurl
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
                    toolPart = createPartFromType(node_type, name, path_id, rowNode.level + 1)
                    toolPart.init(self)
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
    if isinstance(value, object) and getattr(value, 'type', ''):
        _partFactoryMap[value.type] = value

def createPartFromType(type, *args):
    if type == "project":
        project = _partFactoryMap[type]()
        project.create()
        return project
    return _partFactoryMap[type](*args)

