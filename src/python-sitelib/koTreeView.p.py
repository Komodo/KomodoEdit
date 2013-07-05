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
# Portions created by ActiveState Software Inc are Copyright (C) 2000-2011
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

from xpcom import components, nsError, COMException
import logging
import itertools
import contextlib
import functools

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
            self.log.debug("__init__")
        else:
            self.log = None
        self.selection = None   # nsITreeSelection
        self._tree = None       # set in .setTree()
        self.text = "<TreeView>" # for debugging only, never shown

    def isSeparator(self, index):
        return False
    def get_rowCount(self):
        if self.log:
            self.log.debug("get_rowCount()")
        return False
    def getRowProperties(self, index, properties=None):
        if self.log:
            self.log.debug("getRowProperties(%s, %r)", index, properties)
        pass
    def getCellProperties(self, row, column, properties=None):
        if self.log:
            self.log.debug("getCellProperties()")
        pass
    def getColumnProperties(self, column, properties=None):
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
    def isContainerEmpty(self, index):
        if self.log:
            self.log.debug("isContainerEmpty()")
        return False
    def isSorted(self):
        if self.log:
            self.log.debug("isSorted()")
        return False
    def canDrop(self, index, orientation, dataTransfer):
        if self.log:
            self.log.debug("canDrop()")
        return False
    def drop(self, row, orientation, dataTransfer):
        if self.log:
            self.log.debug("drop()")
        pass
    def getParentIndex(self, rowIndex):
        if self.log:
            self.log.debug("getParentIndex()")
        return -1
    def hasNextSibling(self, rowIndex, afterIndex):
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
    def setCellText(self, row, col, value):
        if self.log:
            self.log.debug("setCellText()")
        pass
    def setCellValue(self, row, col, value):
        if self.log:
            self.log.debug("setCellValue() row: %s, col: %s, value: %r", row, col.id, value)
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
    
    def getAllIndices(self):
        treeSelection = self.selection
        a = []
        if treeSelection is not None:
            numRanges = treeSelection.getRangeCount()
            for i in range(numRanges):
                min_index, max_index = treeSelection.getRangeAt(i)
                a += range(min_index, max_index + 1)
        return a

    def getSelectedIndices(self, rootsOnly=False):
        indices = self.getAllIndices()
        i = 0
        lim = len(indices)
        selectedIndices = []
        while i < lim:
            index = indices[i]
            selectedIndices.append(index)
            assert index is not None
            if rootsOnly and self.isContainerOpen(index):
                nextSiblingIndex = self.getNextSiblingIndex(index)
                if nextSiblingIndex == -1:
                    break
                while i < lim - 1 and indices[i + 1] < nextSiblingIndex:
                    i += 1
            i += 1
        return selectedIndices

    def selectRowByIndex(self, idx):
        """Helper method to select the row at the given index and ensure it is
            visible
            @param idx {int} The row index to select; row 0 is the first row.
            @precondition The tree box object has been set
            """
        self.selection.select(idx)
        # Scroll tree if necessary.
        # - If row 'idx' is already visible, then don't scroll.
        first_visible_idx = self._tree.getFirstVisibleRow()
        last_visible_idx = self._tree.getLastVisibleRow()
        if first_visible_idx <= idx <= last_visible_idx:
            pass
        # - Otherwise, try to ensure parent row (if have one and is
        #   close) is visible too. "close" is defined as less than
        #   half of the num visible rows.
        else:
            parent_idx = self.getParentIndex(idx)
            if parent_idx == -1:
                self._tree.ensureRowIsVisible(idx)
            else:
                page_len = self._tree.getPageLength()
                if idx - parent_idx < page_len/2:
                    self._tree.ensureRowIsVisible(parent_idx)
                    self._tree.ensureRowIsVisible(idx)
                else:
                    self._tree.ensureRowIsVisible(idx)

class ObjectTreeViewItem(object):
    """An item for ObjectTreeView"""

    # public properties

    parent = None
    """The parent of this tree item; for the tree view itself, this will be None.
       (tree items of depth 0 will have the tree view as the parent)
       """
    children = [] # this is overwritten in __init__; it's here for docs
    """The children of this tree item"""
    text = ""
    """The text to display"""
    open = False
    """Whether this item is open (only used if it has children)"""

    if __debug__:
        def _checkState(f):
            """Debug-only decorator to check item children for mismatched parent"""
            @functools.wraps(f)
            def wrapper(*args, **kwargs):
                item = args[0]
                assert isinstance(item, ObjectTreeViewItem), \
                    "@_checkState should be applied to ObjectTreeViewItem member methods"
                for child in item.children:
                    assert child.parent == item, \
                        "mismatched children before entering %r" % (f,)
                try:
                    return f(*args, **kwargs)
                finally:
                    for child in item.children:
                        assert child.parent == item, \
                            "method %r created mismatched children" % (f,)
            return wrapper
    else:
        # in release builds, we don't bother to do any checking
        def _checkState(f):
            return f


    def __init__(self, log=None):
        """Create an item for an ObjectTreeView"""
        self.log = log
        self.children = []
        self._rowCount = None
        self._index_to_children = None
        self._hidden = False
        self._invisible = False
        self._open = True

    def __repr__(self):
        return "<ObjectTreeViewItem (%r::%s)>" % (self.view or "<no view>",
                                                  getattr(self, "text", "<noname>"))

    @property
    def _visibleSubtree(self):
        """Return the visible sub tree (self and children) as a list"""
        result = []
        if self.hidden:
            return result
        if not self.invisible:
            result.append(self.text)
        if self.open:
            for child in self.children:
                result.extend(child._visibleSubtree)
        return result

    @property
    def hidden(self):
        """Whether this item (and all its descendants) is hidden"""
        return self._hidden
    @hidden.setter
    def hidden(self, val):
        if self._hidden != val:
            with self._invalidater:
                change = 0
                if val:
                    # visible -> hidden
                    row_idx = self.rowIndex
                    change = -self.rowCount
                    self._hidden = True
                else:
                    # hidden -> visible
                    # note that we can't just use the row count after setting
                    # hidden here, as that can generate children and cause
                    # double invalidations. (Doing this early works because
                    # this is still hidden right now, and therefore won't cause
                    # invalidations)
                    change = self._descendantRowCount
                    self._hidden = False
                    row_idx = self.rowIndex
                    if not self.invisible:
                        change += 1
                if row_idx is not None:
                    self._rowCountChanged(row_idx, change)
                self.invalidate()

    @property
    def invisible(self):
        """Invisible items do not show up in the tree, but its child nodes are
            visible (unless it is also hidden or not open).
            """
        return self._invisible
    @invisible.setter
    def invisible(self, val):
        if val == self._invisible:
            return
        if self.hidden:
            # this is hidden anyway
            return
        with self._invalidater:

            if self.view and self.view.invalidater:
                self.view.invalidater.check()

            if val:
                # visible -> invisible
                index = self.rowIndex
                if index is not None:
                    assert index >= 0
                    self._rowCountChanged(index, -1, "%s.invisible = %s" % (self.text, val))
            self._invisible = val

            if self.view and self.view.invalidater:
                self.view.invalidater.check()

            if not val:
                # invisible -> visible
                index = self.rowIndex
                if index is not None:
                    assert index >= 0
                    self._rowCountChanged(index, 1, "%s.invisible = %s" % (self.text, val))

            if self.view and self.view.invalidater:
                self.view.invalidater.check()
            self.invalidate()

            if self.view and self.view.invalidater:
                self.view.invalidater.check()

    @property
    def open(self):
        """Whether this item is open (only used if it has children)"""
        return self._open
    @open.setter
    def open(self, val):
        if self._open == val:
            # no change
            return
        if self.hidden:
            # nothing will show up anyway
            self._open = val
            return
        restoreSelection = (self.view.getSelectedItems() == [self])
        with self._invalidater:
            row_index = self.rowIndex
            if row_index is not None:
                # we may need to invalidate
                # the number of children that would be visible if we were open
                child_count = reduce(lambda count, child: count + child.rowCount,
                                     self.children,
                                     0)
                if child_count > 0:
                    # some number of children exist; we need to adjust rows
                    if not val:
                        # children are going away, row count change is negative
                        child_count *= -1
                    if not self.invisible:
                        self._invalidate(row_index, row_index)
                        row_index += 1 # don't consider self
                    self._rowCountChanged(row_index, child_count,
                                          "%s.open=%s" % (self.text, val))
            self._open = val
            self.invalidate(recurse=True)
        if restoreSelection:
            self.view.selectRowByIndex(self.rowIndex)

    @property
    def _index_to_children(self):
        """Map of indices (relative to this item, 0 is the first child) to children
            @note this doesn't contain grandchildren
            @note the indices ignore hidden children, or all children if this
                item is not open
            @note this _does_ include invisible children, but only if it has
                visible descendants
            """
        if self.__index_to_children is None:
            if self.hidden or not self.open:
                self.__index_to_children = {}
            else:
                cache = {}
                index = 0
                for child in self.children:
                    if child.hidden:
                        continue
                    if child.invisible:
                        if child.rowCount < 1:
                            # invisible child with no descendants
                            continue
                    cache[index] = child
                    index += child.rowCount
                self.__index_to_children = cache
        return self.__index_to_children
    @_index_to_children.setter
    def _index_to_children(self, val):
        assert val is None, \
            "Not expecting to actually assign into _index_to_children"
        self.__index_to_children = None

    @_checkState
    def item_from_index(self, index):
        """Get the ObjectTreeViewItem descendant from the given row index
            @param index {int} The row index; 0 is the first row below this
                item
            @returns {ObjectTreeViewItem} The item at the given index, or
                None if it is not found"""
        assert index >= 0, "item_from_index: expecting a non-negative index"

        if index in self._index_to_children:
            # asking about one of the children
            child = self._index_to_children[index]
            if child.invisible:
                # the child is invisible; get its first child instead
                return child.item_from_index(0)
            return child

        # no child found, look for the child that is an ancestor of the target
        child_index = -1
        for i in self._index_to_children.keys():
            if i < index and i > child_index:
                child_index = i

        try:
            child = self._index_to_children[child_index]
            offset = 1 if not child.invisible else 0
            return child.item_from_index(index - child_index - offset)
        except KeyError:
            return None

    @_checkState
    def getSelectedItems(self):
        return [self.item_from_index(i) for i in self.getAllIndices()]

    def invalidate(self, recurse=True):
        """Invalidate re-generatable data about this item - note that this
           does *not* cause nsITreeBoxObject invalidation"""
        self._rowCount = None
        self._index_to_children = None
        if recurse and self.parent:
            self.parent.invalidate(recurse=recurse)

    @_checkState
    def insertChild(self, child, pos=None):
        """Add a child to this item
            @param child {ObjectTreeViewItem} The child to add
            @param pos {int} The index to insert the child at; defaults to adding
                the child at the end (i.e. appendChild)
            """
        if self.view:
            assert self.view.rowCount == self.view.invalidater._count, \
                "count mismatch: actual %r, expected %r, on parent %r child %r" % (
                    self.view.rowCount, self.view.invalidater._count,
                    self, child)
        self._insertChildInternal(child, self.children, pos=pos)
        if self.view:
            assert self.view.rowCount == self.view.invalidater._count, \
                "count mismatch: actual %r, expected %r, on parent %r child %r" % (
                    self.view.rowCount, self.view.invalidater._count,
                    self, child)

    def _insertChildInternal(self, child, child_list, pos=None):
        """Add a child to the given list
            @Note this is the implmentation of insertChild; it exists to aid in
                implementing derived classes where .children is a getter
            """
        assert isinstance(child, ObjectTreeViewItem), \
            "insertChild should have a ObjectTreeViewItem child"
        with self._invalidater:
            if child.parent is not None:
                child.parent.removeChild(child)

            # get the row count before modifying anything, in case it causes
            # invalidations
            child_rowCount = child.rowCount

            # get the would-be row index
            if not self.open:
                # post-insertion, the child won't be visible
                child_rowIndex = None
            else:
                child_rowIndex = self.rowIndex
                if child_rowIndex is not None:
                    for sibling in self.children[:pos]:
                        child_rowIndex += sibling.rowCount
                    if not self.invisible:
                        child_rowIndex += 1

            # do the actual insert
            if pos is None:
                child_list.append(child)
            else:
                child_list.insert(pos, child)
            child.parent = self

            # send invalidation
            if child_rowIndex is not None:
                self._rowCountChanged(child_rowIndex, child_rowCount)
            self.invalidate()

    @_checkState
    def removeChild(self, child):
        """Remove the given child from this item
            @param child {ObjectTreeViewItem} The child to remove
            """
        if self.view:
            assert self.view.rowCount == self.view.invalidater._count, \
                "count mismatch: actual %r, expected %r, on parent %r child %r" % (
                    self.view.rowCount, self.view.invalidater._count,
                    self, child)
        self._removeChildInternal(child, self.children)
        if self.view:
            assert self.view.rowCount == self.view.invalidater._count, \
                "count mismatch: actual %r, expected %r, on parent %r child %r" % (
                    self.view.rowCount, self.view.invalidater._count,
                    self, child)

    def _removeChildInternal(self, child, child_list):
        """Remove a child to the given list
            @Note this is the implmentation of removeChild; it exists to aid in
                implementing derived classes where .children is a getter
            """
        with self._invalidater:
            if child.parent is self:
                self._rowCountChanged(child.rowIndex, -child.rowCount)
                child.parent = None
            try:
                child_list.remove(child)
                self.invalidate()
            except ValueError:
                pass

    @property
    def rowCount(self):
        """The number of *visible* rows, include this one and any children"""
        if self._rowCount is None:
            self_count = 1 if not self.invisible else 0
            if self.hidden:
                self._rowCount = 0
            elif not self.open:
                self._rowCount = self_count
            else:
                self._rowCount = self._descendantRowCount + self_count
        return self._rowCount

    @property
    def _descendantRowCount(self):
        """The row count of descendants, ignoring the state of this row.  This
            can return a number even if this row is hidden or closed.  Note that
            this may be expensive.
            """
        return reduce(lambda count, child: count + child.rowCount,
                      self.children,
                      0)

    @property
    def subTreeIsVisible(self):
        """True if this row or any of its children will be visible"""
        # this is an attempt at optimization - try not to generate children if
        # at all possible.
        if self._rowCount is not None:
            return self._rowCount > 0
        if self.hidden:
            return False
        if not self.invisible:
            return True
        if not self.open:
            return False
        # We need to check the children
        for child in self.children:
            if not child.hidden and not child.invisible:
                # this child is itself visible
                return True
        # no children are immediately visible. check recursively :(
        # we might as well cache the row count on the way down
        return self.rowCount > 0

    @property
    def rowIndex(self):
        """The row index of the current item, in terms of the whole tree
            @note If this row is invisible (but not hidden), the rowIndex is the
                first visible descendant
            @returns None if the current item (or an ancestor) is hidden,
                otherwise a non-negative integer row index"""

        if not self.view:
            # not in a view, there can be no index
            return None

        if self is self.view:
            # root tree view, nothing above this
            return 0

        if not self.parent.open:
            # parent isn't open, we are not visible
            return None

        if self.hidden:
            # we are hidden, no valid index
            return None

        # find the parent index first, we're relative to that
        index = self.parent.rowIndex
        if index is None:
            # not visible
            return None

        # add up all the preceding siblings
        for child in self.parent.children:
            if child is self:
                break
            index += child.rowCount # deals with hidden and invisible for us

        if not self.parent.invisible:
            # we need to offset from the parent
            index += 1

        assert index >= 0
        return index

    @property
    def view(self):
        """Get the view this item is attached to"""
        parent = self
        while parent.parent is not None:
            parent = parent.parent
        if isinstance(parent, ObjectTreeView):
            return parent
        return None

    @_checkState
    def _rowCountChanged(self, row, delta, debug=None):
        """Helper method to call self.view.invalidater.rowCountChanged"""
        view = self.view
        if view:
            with view.invalidater:
                view.invalidater.rowCountChanged(row, delta, debug)
            if self.log:
                self.log.debug("rowCountChanged: item %r row %r delta %r (current %r invalidater %r)",
                    self, row, delta, view.rowCount, view.invalidater._count)

    @_checkState
    def _invalidate(self, start, end, debug=None):
        """Helper method to call self.view.invalidater.invalidate"""
        view = self.view
        if view:
            with view.invalidater:
                view.invalidater.invalidate(start, end, debug)

    @property
    def _invalidater(self):
        view = self.view
        if view is not None:
            return view.invalidater
        @contextlib.contextmanager
        def f():
            yield
        return f()

class InvalidationRange(object):
    """Structure to hold tree invalidation / row count changes"""
    ranges = []
    """Invalid or modified ranges, as a tuple of (start, end, delta), sorted
        by the start index
        @note This is always stored as offsets _before_ any action has applied
        to the tree
        @note The dirty range is [start, end), i.e. half-open
        @note This list should always be merged where possible; the _checkState
            decorator will check that this is so.
        """

    def __init__(self, view, log=None):
        """Initialize the range invalidation tracker
            @param view {ObjectTreeView} The view to manage
            """
        self.view = view
        self.log = log
        self.ranges = []
        self.depth = 0 # the number of nested operations
        self.dirty = False
        self.log_debug("starting with %r rows", view.rowCount)
        self._count = 0 # for debugging: tracks the row count this has seen
        self._broken = False

    if __debug__:
        def _checkState(f):
            """Checks the invalidation ranges for invariant violations"""
            @functools.wraps(f)
            def wrapper(*args, **kwargs):
                self = args[0]
                assert isinstance(self, InvalidationRange), \
                    "@_checkState should be applied to InvalidationRange member methods"
                assert isinstance(self.ranges, list), \
                    "Unexpected type for ranges %r" % (type(self.ranges),)

                if self._broken:
                    # this is known to be broken, no need to check
                    return

                def check(pos):
                    for entry in self.ranges:
                        assert isinstance(entry, list), \
                            "%s %r: ranges %r is inconsistent" % (pos, f, self.ranges)
                        assert len(entry) == 3, \
                            "%s %r: ranges %r is inconsistent" % (pos, f, self.ranges)
                        assert all(map(lambda x: isinstance(x, int), entry)), \
                            "%s %r: ranges %r is inconsistent" % (pos, f, self.ranges)
                        assert entry[0] >= 0, \
                            "%s %r: ranges %r is inconsistent" % (pos, f, self.ranges)
                        assert entry[0] <= entry[1], \
                            "%s %r: ranges %r is inconsistent" % (pos, f, self.ranges)
                    for index in range(0, len(self.ranges) - 1):
                        assert self.ranges[index][1] < self.ranges[index + 1][0], \
                            "%s %r: for ranges %r@%r, range end %r should merge with next range starting at %r" % (
                                pos, f, self.ranges, index, self.ranges[index][1], self.ranges[index + 1][0])
                check("before calling")
                result = f(*args, **kwargs)
                check("after calling")
                return result
            return wrapper
    else:
        # don't do extra state checking in release builds
        def _checkState(f):
            return f

    @_checkState
    def __enter__(self):
        self.depth += 1

    @_checkState
    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type:
            # exception raised, don't clobber it
            return
        if not self._broken:
            # check for consistency, but only if we're not known broken
            self.check()
        self.depth -= 1
        if self.depth < 1 and self.dirty:
            self.commit()

    def _maybeMerge(self, index):
        """Potentially merge ranges at (index) and (index + 1) if they overlap
            @precondition self.ranges[0][0] is less than self.ranges[1][0]
                (or self.ranges[1] does not exist)
            """
        # note that this doesn't use the _checkState decorator, because it's
        # this method's job to maintain the invariants
        if index < 0:
            # not a valid index for our purposes
            return
        if len(self.ranges) < index + 2:
            # no following range, can't merge
            return
        end = self.ranges[index][1]
        if self.ranges[index][2] < 0:
            # the previous range removed rows; we need to extend it
            end -= self.ranges[index][2]
        if end < self.ranges[index + 1][0]:
            # disjoint ranges
            return
        # we should merge the two ranges
        dirty_count = self.ranges[index + 1][1] - self.ranges[index + 1][0]
        if self.ranges[index][2] * self.ranges[index + 1][2] < 0:
            # convert remove-and-add or add-and-remove to invalidate
            dirty_count += max(abs(self.ranges[0][2]), abs(self.ranges[1][2]))
        if dirty_count > 0:
            # there's an invalidation, make sure the dirty count covers the
            # start of the first range as well
            start = min(self.ranges[index][0], self.ranges[index + 1][0])
            dirty_count = self.ranges[index + 1][1] - start
        if self.ranges[index][1] - self.ranges[index][0] < dirty_count:
            # we need to invalidate more rows
            self.ranges[index][1] = self.ranges[index][0] + dirty_count
        self.ranges[index][2] +=  self.ranges[index + 1][2]
        del self.ranges[index + 1]

    @_checkState
    def invalidate(self, start=None, end=None, debug=None):
        """Invalidate a range
            @param start {int} The row index to start invalidation
            @param end {int} The row index to end invalidation (not a count)
            @note The range is inclusive; to invalidate a single row, set start
                and end to the same value. To invalidate two rows, set end to be
                one more than start.
            """
        self.log_debug("invalidate: %r -> %r", (start, end, debug), self.ranges)

        if start is None:
            if end is None:
                # invalidate the whole tree
                self._broken = True
                return
            start = 0
        if end is None:
            end = start

        try:
            end += 1 # convert range to half-open [start, end)
            index = -1 # if we have no existing ranges, insert at start
            for index, entry in enumerate(self.ranges):
                # there are 11 possible situations; let * be start, and
                # the entry be [ ]--> (delta > 0), [ ]<-- (delta < 0), [ ] (=0)
                #
                # (A)
                # * [  ]-->      * [  ]<--     * [  ]
                #   in these cases, the entry is after start and won't affect
                #   it; we insert the new entry before it and check for merging
                #
                # (B)
                # [  *  ]-->     [  *  ]<--    [  *  ]
                #   the new range overlaps the entry and we can insert it after
                #   and merge the two
                #
                # (C)
                # [  ]--*-->
                #   the start position starts somewhere that didn't exist; we
                #   must move it to the end of the delta (and decrease the
                #   length accordingly) and possibly insert it after
                #
                # (D)
                # [  ]<--*--
                #   the start position needs to be adjusted to account for the
                #   now-missing rows, at which point it will be after the entry
                #
                # (E)
                # [  ]-->  *    [  ]<--  *    [  ]  *
                #   the new range is solidly after the entry; adjust the start
                #   by the delta and look at the next entry

                if entry[0] > start:
                    # (A) entry is after the invalidation range
                    index -= 1 # adjust to the entry just before
                    break
                if entry[1] >= start:
                    # (B) entry overlaps; insert new entry and merge
                    break
                if entry[2] > 0 and entry[1] + entry[2] >= start:
                    # (C) starts in the middle of an inserted range
                    insertion_end = entry[1] + entry[2]
                    if insertion_end >= end:
                        # the whole invalidation range is within the inserted area
                        # we don't need to record this invalidation
                        return
                    # there's a chunk after that we need to worry about
                    end -= entry[2]
                    start = entry[1]
                    break
                # (D), (E): the whole range is before start
                start -= entry[2]
                end -= entry[2]

                # go to next entry (for loop)

            # getting here means self.ranges[index] before start, but
            # self.ranges[index + 1] is after; insert new entry at index
            self.ranges.insert(index + 1, [start, end, 0])
            self._maybeMerge(index + 1)
            self._maybeMerge(index)

        except Exception, e:
            self.log_exception(e)
            # mark this is being broken; the next commit will simply refresh
            # the whole tree and discard all changes.
            self._broken = True

    @_checkState
    def rowCountChanged(self, start, count, debug=None):
        """Notify about row count changes
            @param start {int} The index of the first row
            @param count {int} The number of rows changes (positive for
                insertion, negative for deletion)
            @see nsITreeView::rowCountChanged
            """
        if start is None or not count:
            # the element isn't visible, don't do any work
            self.log_debug("rowCountChanged: ignoring %r because it's invisible",
                           (start, count, debug))
            return
        self.log_debug("rowCountChanged: %r -> %r",
                       (start, count, debug), self.ranges)
        self._count += count # for debugging only, not used
        try:
            self.dirty = True
            for index, entry in enumerate(self.ranges):
                if entry[0] <= start:
                    if entry[0] + entry[2] < start:
                        start -= entry[2]
                        continue
                    else:
                        entry[2] += count
                        self._maybeMerge(index)
                        break
                else:
                    self.ranges.insert(index, [start, start, count])
                    # since this is an insertion, we might need to merge both
                    # ends. do the right end first so we won't have to worry
                    # about the index changing.
                    self._maybeMerge(index)
                    self._maybeMerge(index - 1)
                    break
            else:
                # all other entries are before the start; append new entry
                self.ranges.append([start, start, count])
                self._maybeMerge(len(self.ranges) - 2)

        except Exception, e:
            self.log_exception(e)
            # mark this is being broken; the next commit will simply refresh
            # the whole tree and discard all changes.
            self._broken = True

        self.log_debug("rowCountChanged: result: %r -> %r",
                       (start, count, debug), self.ranges)

    @_checkState
    def commit(self):
        """Commit the invalidations / row count changes"""
        if self.view.rowCount != self._count:
            # we got into a broken state without detecting it
            self.log_warn("InvalidationRange::commit: Undetected row count mismatch")
            self.view._tree.rowCountChanged(0, self.view.rowCount - self._count)
            self._count = self.view.rowCount
            self._broken = True
        if self._broken:
            # something's busted! invalidate the whole thing
            # by faking a batch we force the tree to also look up the new row count
            self.view._tree.beginUpdateBatch()
            self.view._tree.endUpdateBatch()
            self.ranges = []
            self._broken = False
        else:
            ranges = self.ranges
            self.ranges = []
            self.log_debug("InvalidationRange::commit: %r", ranges)
            for range in reversed(ranges):
                self.view._tree.invalidateRange(range[0], range[1])
                if range[2] != 0:
                    self.view._tree.rowCountChanged(range[0], range[2])
            self.log_debug("InvalidationRange::committed; view rows %r, "
                           "invalidater rows %r",
                           self.view.rowCount, self._count)
        if self.view and self.view.selection:
            if self.view.selection.currentIndex >= self.view.rowCount:
                # okay, the selection is busted. Not sure what's up here,
                # but continuing results in silly assertions and random bugs.
                self.view.selection.currentIndex = -1

    @_checkState
    def check(self):
        # the _checkState decorator does the hard work here
        pass

    def log_debug(self, *args, **kwargs):
        """Wrapper for self.log.debug"""
        if self.log:
            self.log.debug(*args, **kwargs)
    def log_warn(self, *args, **kwargs):
        """Wrapper for self.log.warn"""
        if self.log:
            self.log.warn(*args, **kwargs)
    def log_exception(self, *args, **kwargs):
        """Wrapper for self.log.exception"""
        if self.log:
            self.log.exception(*args, **kwargs)

class ObjectTreeView(TreeView, ObjectTreeViewItem):
    """A object-oriented tree view implementation, for single-column trees with
       nesting
       """

    def __init__(self, *args, **kwargs):
        TreeView.__init__(self, *args, **kwargs)
        ObjectTreeViewItem.__init__(self, log=self.log)
        self.invalidater = InvalidationRange(self, log=self.log)
        self.data = {} # to look more like ObjectTreeViewItem

    def __repr__(self):
        return "<%s>" % (self.__class__)

    def isContainer(self, index):
        return True

    def isContainerOpen(self, index):
        item = self.item_from_index(index)
        return bool(item and item.open)

    def isContainerEmpty(self, index):
        item = self.item_from_index(index)
        if item is None:
            return True
        result = any(itertools.imap(lambda c: c.subTreeIsVisible, item.children))
        return not result

    def getParentIndex(self, index):
        if index < 0:
            raise COMException(nsError.NS_ERROR_INVALID_ARG,
                "getParentIndex with index %r < 0" % (index,))
        if index >= self.rowCount:
            raise COMException(nsError.NS_ERROR_INVALID_ARG,
                "getParentIndex with index %r >= %r" % (index, self.rowCount))

        original_index = index # the index we started with
        parent = self # the ancestor we're examining
        parent_index = 0 # the index of the ancestor
        # index is now the index relative to the parent-being-examined
        if self.log:
            path = [(index, parent.text)]

        try:
            while not index in parent._index_to_children:
                i = max(filter(lambda k: k < index, parent._index_to_children.keys()))
                # i is the offset of the next parent to use (from the current parent)

                parent_size = 1 if not parent.invisible else 0 # how many rows the parent itself takes
                parent_index = parent_index + parent_size + i
                parent = parent._index_to_children[i]
                child_size = 1 if not parent.invisible else 0 # how many rows the new parent takes
                index = index - i - child_size

                if self.log:
                    path.append((index, parent.text))
        except ValueError:
            # invalid, e.g. index -1
            if self.log:
                self.log.debug("getParentIndex: error getting %r from %r (of %r)"
                               "; original index %r, path %r dirty %r",
                               index, parent, parent.rowCount, original_index, path,
                               self.invalidater.dirty)
            return -1

        if parent == self:
            # the parent is the root element
            parent_index = -1

        if self.log:
            self.log.debug("getParentIndex: %r -> %r=%r",
                           original_index, index, parent_index)

        if parent_index == original_index:
            # ughh... that sounds broken!
            if self.log:
                self.log.error("getParentIndex: parent of %r seems to be %r (%r)",
                               original_index, parent_index, parent)

            raise COMException(nsError.NS_ERROR_UNEXPECTED,
                               "getParentIndex claimed parent of %r is %r" % (
                                    original_index, parent_index))
        return parent_index

    def hasNextSibling(self, rowIndex, afterIndex):
        # used to draw vertical lines in indenting
        item = self.item_from_index(rowIndex)
        if item is None or item.parent is None:
            return False
        index_map = item.parent._index_to_children
        keys = iter(sorted(index_map.keys()))
        try:
            while index_map[next(keys)] != item:
                pass
            # we're right after the target item
            for key in keys:
                item = index_map[key]
                if item.subTreeIsVisible:
                    # something after the target has visible rows
                    return True
            # nothing after the item we wanted, or they are all hidden
            return False
        except StopIteration:
            # no more siblings
            return False

    def getLevel(self, index):
        item = self.item_from_index(index)
        if item is None:
            return -1
        level = 0
        parent = item.parent
        while parent is not None:
            if not parent.invisible:
                level += 1
            parent = parent.parent
        return level

    def getCellText(self, row, column):
        return self.item_from_index(row).text

    def toggleOpenState(self, index):
        item = self.item_from_index(index)
        item.open = not item.open

    #override TreeView.get_rowCount
    def get_rowCount(self):
        # Wrapper for old-style getter - PyXPCOM prefers this version, and we
        # need to override the one in TreeView
        return self.rowCount

    # override ObjectTreeViewItem.invisible
    @property
    def invisible(self):
        # the root item is always invisible
        return True
    @invisible.setter
    def invisible(self, val):
        pass

    def selectRowByItem(self, item):
        """Helper method to select the given item in the tree
            @param item {ObjectTreeViewItem} The item to select
            @note This will silently do nothing if the item has no associated
                row (e.g. it is not in the tree, or is hidden)
            @returns True if a row was selected; False if the item has no row
            """
        idx = item.rowIndex
        if idx is not None and idx < self.rowCount:
            self.selectRowByIndex(idx)
            return True
        return False
