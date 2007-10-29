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
    http://www.xulplanet.com/references/xpcomref/ifaces/nsITreeView.html    
    """
    #XXX This should be placed in an 'tree.py' or something with
    #    documentation and examples of use.
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
        return 0
    
    def get_rowCount( self ):
        # Result: int32
        if self.log:
            self.log.debug("get_rowCount()")
        return 0
    def getRowProperties( self, index, properties ):
        # Result: void - None
        # In: param0: int32
        # In: param1: nsISupportsArray
        if self.log:
            self.log.debug("getRowProperties(%s, %r)", index, properties)
        pass
    def getCellProperties(self, row, column, properties):
        # Result: void - None
        # In: param0: int32
        # In: param1: wstring
        # In: param2: nsISupportsArray
        if self.log:
            self.log.debug("getCellProperties()")
        pass
    # in nsITreeColumn col, in nsISupportsArray properties
    def getColumnProperties(self, 
                            column,
                            properties):
        # Result: void - None
        # In: param0: wstring
        # In: param1: nsIDOMElement
        # In: param2: nsISupportsArray
        if self.log:
            self.log.debug("getColumnProperties(column=%s, props=%r)",
                           column, properties)

    def isContainer(self, index):
        # Result: boolean
        # In: param0: int32
        if self.log:
            self.log.debug("isContainer()")
        return 0
    def isContainerOpen(self, index):
        # Result: boolean
        # In: param0: int32
        if self.log:
            self.log.debug("isContainerOpen()")
        return 0
    def isContainerEmpty( self, param0 ):
        # Result: boolean
        # In: param0: int32
        if self.log:
            self.log.debug("isContainerEmpty()")
        return 0
    def isSorted( self ):
        # Result: boolean
        if self.log:
            self.log.debug("isSorted()")
        return 0
    def canDrop(self, index, orientation):
        if self.log:
            self.log.debug("canDrop()")
        return False
    def drop(self, row, orientation):
        if self.log:
            self.log.debug("drop()")
        pass
    def getParentIndex( self, param0 ):
        # Result: int32
        # In: param0: int32
        if self.log:
            self.log.debug("getParentIndex()")
        return -1
    def hasNextSibling( self, param0, param1 ):
        # Result: boolean
        # In: param0: int32
        # In: param1: int32
        if self.log:
            self.log.debug("hasNextSibling()")
        return 0
    def getLevel(self, index):
        # Result: int32
        # In: param0: int32
        if self.log:
            self.log.debug("getLevel()")
        return 0
    def getImageSrc(self, row, column):
        if self.log:
            self.log.debug("getImageSrc(row=%r, colID=%r)", row, column.id)
        return ''
    def getCellValue(self, row, column):
        # Result: wstring
        # In: param0: int32
        # In: param1: wstring
        if self.log:
            self.log.debug("getCellValue() row: %s, col: %s", row, column.id)
        return ""
    def getCellText(self, row, column):
        col = column.id
        # Result: wstring
        # In: param0: int32
        # In: param1: wstring
        if self.log:
            self.log.debug("getCellText() row: %s, col: %s", row, col)
        return ""
    def setTree(self, tree):
        # Result: void - None
        # In: param0: nsITreeBoxObject
        #XXX may move to be an attribute.
        if self.log:
            self.log.debug("[%s] setTree(tree='%s')", id(self), tree)
        self._tree = tree
    def toggleOpenState(self, index):
        # Result: void - None
        # In: param0: int32
        if self.log:
            self.log.debug("toggleOpenState()")
        pass
    def cycleHeader(self, column):
        # Result: void - None
        # In: param0: wstring
        # In: param1: nsIDOMElement
        if self.log:
            self.log.debug("cycleHeader()")
        pass
    def selectionChanged(self):
        # Result: void - None
        if self.log:
            self.log.debug("selectionChanged()")
        pass
    def cycleCell(self, row, column):
        # Result: void - None
        # In: param0: int32
        # In: param1: wstring
        if self.log:
            self.log.debug("cycleCell()")
        pass
    def isEditable(self, row, column):
        # Result: boolean
        # In: param0: int32
        # In: param1: wstring
        if self.log:
            self.log.debug("isEditable()")
        return 0
    def setCellText( self, param0, param1, param2 ):
        # Result: void - None
        # In: param0: int32
        # In: param1: wstring
        # In: param2: wstring
        if self.log:
            self.log.debug("setCellText()")
        pass
    def performAction(self, action):
        # Result: void - None
        # In: param0: wstring
        if self.log:
            self.log.debug("performAction(%s)" % action)
        pass
    def performActionOnRow(self, action, row):
        # Result: void - None
        # In: param0: wstring
        # In: param1: int32
        if self.log:
            self.log.debug("performActionOnRow(%s, %s)", action, row)
        pass
    def performActionOnCell(self, action, row, column):
        # Result: void - None
        # In: param0: wstring
        # In: param1: int32
        # In: param2: wstring
        if self.log:
            self.log.debug("performActionOnCell(%s, %s, %r)", action, row, column)
        pass

