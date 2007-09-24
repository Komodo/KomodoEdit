#!python
# Copyright (c) 2000-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

# Support for Find in Files' "Browse for dirs" dialog.

import sys
import os
import types
import pprint

from xpcom import components, nsError, ServerException, COMException
import logging
from koTreeView import TreeView


log = logging.getLogger("koFindBrowseForDirs")
#log.setLevel(logging.DEBUG)


class KoFindAvailableDirsView(TreeView):
    _com_interfaces_ = [components.interfaces.koIFindAvailableDirsView,
                        components.interfaces.nsITreeView]
    _reg_clsid_ = "{3C9B3E51-C784-4E21-9AD6-55F584925005}"
    _reg_contractid_ = "@activestate.com/koFindAvailableDirsView;1"
    _reg_desc_ = "Komodo Find in Files Available Dirs View"

    def __init__(self):
        TreeView.__init__(self, debug=0)
        self._data = []
        self._tree = None
        self._sortedBy = None
        self.currentDir = None
        self._dirs = []
    
    def changeDir(self, newDir):
        log.debug("KoFindAvailableDirsView.changeDir(newDir=%r)", newDir)
        if os.path.isabs(newDir):
            self.currentDir = newDir
        elif self.currentDir is None:
            log.error("Cannot change to a relative dir before the "
                      "current dir has been set.")
            raise ServerException(nsError.NS_ERROR_NOT_INITIALIZED)
        else:
            self.currentDir = os.path.join(self.currentDir, newDir)
        self.currentDir = os.path.normpath(self.currentDir)
        
        preLength = len(self._dirs)
        try:
            basenames = os.listdir(self.currentDir)
        except EnvironmentError, ex:
            log.debug("'%s' does not exist, emptying available dirs view")
            self._dirs = []
        else:
            self._dirs = [b for b in basenames
                          if os.path.isdir(os.path.join(self.currentDir, b))]
        #pprint.pprint(self._dirs)
        self._tree.beginUpdateBatch()
        self._tree.rowCountChanged(0, len(self._dirs)-preLength)
        self._tree.invalidate()
        self._tree.endUpdateBatch()

    def getSelectedDir(self):
        if not self.selection.count:
            log.error("no dir is currently selected")
            raise ServerException(nsError.NS_ERROR_UNEXPECTED)
        subDir = self._dirs[self.selection.currentIndex]
        return os.path.join(self.currentDir, subDir)

    def getDirAt(self, index):
        subDir = self._dirs[index]
        return os.path.join(self.currentDir, subDir)

    def getIndexOfDir(self, baseName):
        try:
            return self._dirs.index(baseName)
        except ValueError, ex:
            return -1

    def get_rowCount(self):
        return len(self._dirs)

    def getCellText(self, row, column):
        if column.id != "available-dirs-name":
            log.error("unexpected koFindAvailableDirsView column name: %r",
                      column.id)
            return ""
        try:
            cell = self._dirs[row]
        except IndexError:
            # Silence this, it is too annoying.
            # c.f. http://bugs.activestate.com/Komodo/show_bug.cgi?id=27487
            #log.error("no %sth item" % row)
            return ""
        if type(cell) not in (types.StringType, types.UnicodeType):
            cell = str(cell)
        return cell

    def getImageSrc(self, row, column):
        return "chrome://komodo/skin/images/folder-closed.png"


class KoFindSelectedDirsView(TreeView):
    _com_interfaces_ = [components.interfaces.koIFindSelectedDirsView,
                        components.interfaces.nsITreeView]
    _reg_clsid_ = "{68E3F0AF-2F58-4946-99D1-628FE9AF8C89}"
    _reg_contractid_ = "@activestate.com/koFindSelectedDirsView;1"
    _reg_desc_ = "Komodo Find in Files Selected Dirs View"

    def __init__(self):
        TreeView.__init__(self, debug=0)
        self._tree = None
        self._sortedBy = None
        self._dirs = []

    def setEncodedFolders(self, encodedFolders):
        preCount = len(self._dirs)
        self._dirs = encodedFolders.split(os.pathsep)
        self._dirs = [f for f in self._dirs if f] # drop empties
        self._tree.beginUpdateBatch()
        self._tree.rowCountChanged(0, len(self._dirs)-preCount) # XXX is this more correct usage?
        self._tree.invalidate()
        self._tree.endUpdateBatch()

    def getEncodedFolders(self):
        return os.pathsep.join(self._dirs)

    def addDir(self, dir):
        if dir in self._dirs: # don't add duplicates
            raise ServerException(nsError.NS_ERROR_FILE_ALREADY_EXISTS)
        self._dirs.append(dir)
        self._tree.beginUpdateBatch()
        self._tree.rowCountChanged(len(self._dirs)-1, 1)
        self._tree.invalidate()
        self._tree.endUpdateBatch()

    def removeSelectedDirs(self):
        if self.selection.count == 0:
            log.error("no dir is currently selected")
            raise ServerException(nsError.NS_ERROR_UNEXPECTED)
        elif self.selection.count == 1:
            index = self.selection.currentIndex
            del self._dirs[index]
            self._tree.beginUpdateBatch()
            self._tree.rowCountChanged(index, -1)
            self._tree.invalidate()
            self._tree.endUpdateBatch()
        else:
            indicesToRemove = []
            for i in range(self.selection.getRangeCount()):
                min, max = self.selection.getRangeAt(i)
                for j in range(min, max+1):  # inclusive
                    indicesToRemove.append(j)
            indicesToRemove.reverse()
            for i in indicesToRemove:
                del self._dirs[i]
            self._tree.beginUpdateBatch()
            self._tree.rowCountChanged(indicesToRemove[-1],
                                       -len(indicesToRemove))
            self._tree.invalidate()
            self._tree.endUpdateBatch()

    def moveSelectedDirUp(self):
        if not self.selection.count:
            log.error("no dir is currently selected")
            raise ServerException(nsError.NS_ERROR_UNEXPECTED)
        elif self.selection.currentIndex == 0:
            log.error("cannot move top item up")
            raise ServerException(nsError.NS_ERROR_UNEXPECTED)
        index = self.selection.currentIndex
        folder = self._dirs[index]
        del self._dirs[index]
        self._dirs.insert(index-1, folder)
        self._tree.beginUpdateBatch()
        self._tree.invalidate()
        self._tree.endUpdateBatch()

    def moveSelectedDirDown(self):
        if not self.selection.count:
            log.error("no dir is currently selected")
            raise ServerException(nsError.NS_ERROR_UNEXPECTED)
        elif self.selection.currentIndex == self.get_rowCount:
            log.error("cannot move botton item down")
            raise ServerException(nsError.NS_ERROR_UNEXPECTED)
        index = self.selection.currentIndex
        folder = self._dirs[index]
        del self._dirs[index]
        self._dirs.insert(index+1, folder)
        self._tree.beginUpdateBatch()
        self._tree.invalidate()
        self._tree.endUpdateBatch()

    def get_rowCount(self):
        return len(self._dirs)

    def getCellText(self, row, column):
        if column.id != "selected-dirs-name":
            log.error("unexpected koFindSelectedDirsView column name: %r",
                      column.id)
            return ""
        try:
            cell = self._dirs[row]
        except IndexError:
            # Silence this, it is too annoying.
            # c.f. http://bugs.activestate.com/Komodo/show_bug.cgi?id=27487
            #log.error("no %sth item" % row)
            return ""
        if type(cell) not in (types.StringType, types.UnicodeType):
            cell = str(cell)
        return cell


