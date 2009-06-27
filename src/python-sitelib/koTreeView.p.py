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
# Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
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

from xpcom import components, nsError, ServerException, COMException, _xpcom
import logging

log = logging.getLogger("TreeView")
#log.setLevel(logging.DEBUG)

class TreeView(object):
    """A base implementation of the nsITreeView.
    
    This should be subclassed to get any useful behaviour.
    https://developer.mozilla.org/en/NsITreeView
    """
    _com_interfaces_ = [components.interfaces.nsITreeView]
        
    def __init__(self, debug=None):
        if debug:
            self.log = logging.getLogger("TreeView.%s" % debug)
            self.log.setLevel(logging.DEBUG)
        else:
            self.log = None
        self.selection = None   # nsITreeSelection
        self._tree = None       # set in .setTree()

    def isSeparator(self, index):
        return False
    def get_rowCount(self):
        if self.log:
            self.log.debug("get_rowCount()")
        return False
    def getRowProperties(self, index, properties):
        if self.log:
            self.log.debug("getRowProperties(%s, %r)", index, properties)
        pass
    def getCellProperties(self, row, column, properties):
        if self.log:
            self.log.debug("getCellProperties()")
        pass
    def getColumnProperties(self, column, properties):
        if self.log:
            self.log.debug("getColumnProperties(column=%s, props=%r)",
                column, properties)
    def isContainer(self, index):
        if self.log:
            self.log.debug("isContainer()")
        return False
    def isContainerOpen(self, index):
        if self.log:
            self.log.debug("isContainerOpen()")
        return False
    def isContainerEmpty(self, param0):
        if self.log:
            self.log.debug("isContainerEmpty()")
        return False
    def isSorted(self):
        if self.log:
            self.log.debug("isSorted()")
        return False
    def canDrop(self, index, orientation):
        if self.log:
            self.log.debug("canDrop()")
        return False
    def drop(self, row, orientation):
        if self.log:
            self.log.debug("drop()")
        pass
    def getParentIndex(self, param0):
        if self.log:
            self.log.debug("getParentIndex()")
        return -1
    def hasNextSibling(self, param0, param1):
        if self.log:
            self.log.debug("hasNextSibling()")
        return 0
    def getLevel(self, index):
        if self.log:
            self.log.debug("getLevel()")
        return 0
    def getImageSrc(self, row, column):
        if self.log:
            self.log.debug("getImageSrc(row=%r, colID=%r)", row, column.id)
        return ''
    def getCellValue(self, row, column):
        if self.log:
            self.log.debug("getCellValue() row: %s, col: %s", row, column.id)
        return ""
    def getCellText(self, row, column):
        if self.log:
            self.log.debug("getCellText() row: %s, col: %s", row, column.id)
        return ""
    def setTree(self, tree):
        if self.log:
            self.log.debug("[%s] setTree(tree='%s')", id(self), tree)
        self._tree = tree
    def toggleOpenState(self, index):
        if self.log:
            self.log.debug("toggleOpenState()")
        pass
    def cycleHeader(self, column):
        if self.log:
            self.log.debug("cycleHeader()")
        pass
    def selectionChanged(self):
        if self.log:
            self.log.debug("selectionChanged()")
        pass
    def cycleCell(self, row, column):
        if self.log:
            self.log.debug("cycleCell()")
        pass
    def isEditable(self, row, column):
        if self.log:
            self.log.debug("isEditable()")
        return False
    def setCellText(self, param0, param1, param2):
        if self.log:
            self.log.debug("setCellText()")
        pass
    def setCellValue(self, row_idx, col, value):
        if self.log:
            self.log.debug("setCellValue() row: %s, col: %s, value: %r", row, col.id, vlaue)
    def performAction(self, action):
        if self.log:
            self.log.debug("performAction(%s)" % action)
        pass
    def performActionOnRow(self, action, row):
        if self.log:
            self.log.debug("performActionOnRow(%s, %s)", action, row)
        pass
    def performActionOnCell(self, action, row, column):
        if self.log:
            self.log.debug("performActionOnCell(%s, %s, %r)", action, row, column)
        pass

