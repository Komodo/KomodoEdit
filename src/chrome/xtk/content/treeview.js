/* ***** BEGIN LICENSE BLOCK *****
 * Version: MPL 1.1/GPL 2.0/LGPL 2.1
 * 
 * The contents of this file are subject to the Mozilla Public License
 * Version 1.1 (the "License"); you may not use this file except in
 * compliance with the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 * 
 * Software distributed under the License is distributed on an "AS IS"
 * basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
 * License for the specific language governing rights and limitations
 * under the License.
 * 
 * The Original Code is Komodo code.
 * 
 * The Initial Developer of the Original Code is ActiveState Software Inc.
 * Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
 * ActiveState Software Inc. All Rights Reserved.
 * 
 * Contributor(s):
 *   ActiveState Software Inc
 * 
 * Alternatively, the contents of this file may be used under the terms of
 * either the GNU General Public License Version 2 or later (the "GPL"), or
 * the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
 * in which case the provisions of the GPL or the LGPL are applicable instead
 * of those above. If you wish to allow use of your version of this file only
 * under the terms of either the GPL or the LGPL, and not to allow others to
 * use your version of this file under the terms of the MPL, indicate your
 * decision by deleting the provisions above and replace them with the notice
 * and other provisions required by the GPL or the LGPL. If you do not delete
 * the provisions above, a recipient may use your version of this file under
 * the terms of any one of the MPL, the GPL or the LGPL.
 * 
 * ***** END LICENSE BLOCK ***** */

/* * *
 * Contributors:
 *   Shane Caraveo <shanec@activestate.com>
 *   Todd Whitemane <toddw@activestate.com>
 */


if (typeof(xtk) == 'undefined') {
    var xtk = {};
}

/*
 base tree view class in js
*/


xtk.baseTreeView = function treeView() {
  this.mSingleSelect = false;
  this.mSelectionCallback = null;
  this.mSelection = null;
  this.mTree = null;
  this.mSortType = 0;
  this.mTotalRows = 0;
  this.debug = 0;
};

xtk.baseTreeView.prototype = {

  /* readonly attribute long rowCount; */
  set rowCount(c) { throw "readonly property"; },
  get rowCount() { return this.mTotalRows; },

  /* attribute nsITreeSelection selection; */
  set selection(s) { this.mSelection = s; },
  get selection() { return this.mSelection; },

  set selectionCallback(f) { this.mSelectionCallback = f; },
  get selectionCallback() { return this.mSelectionCallback; },

  set singleSelect(f) { this.mSingleSelect = f; },
  get singleSelect() { return this.mSingleSelect; },

  /* nsISupports methods */

  /* void QueryInterface(in nsIIDRef uuid,
     [iid_is(uuid),retval] out nsQIResult result); */
  QueryInterface: function(iid) {
    if (!iid.equals(Components.interfaces.nsITreeView) &&
        !iid.equals(Components.interfaces.nsISupports)) {
          throw Components.results.NS_ERROR_NO_INTERFACE;
        }
    return this;
  },

  /* nsITreeView methods */

  /* AString getRowProperties(in long index); // mozilla 22+ */
  /* void getRowProperties(in long index, in nsISupportsArray properties); */
  getRowProperties: function(index, properties) {
  },

  /* AString getCellProperties(in long row, in nsIDOMElement colElt); // mozilla 22+ */
  /* void getCellProperties(in long row, in nsIDOMElement colElt,
                            in nsISupportsArray properties); */
  getCellProperties: function(row, colElt, properties) {
  },

  /* AString getColumnProperties(nsIDOMElement colElt); // for mozilla 22+ */
  /* void getColumnProperties(in nsIDOMElement colElt,
                              in nsISupportsArray properties); */
  getColumnProperties: function(colElt, properties) {
  },

  /* boolean isContainer(in long index); */
  isContainer: function(index) { return false; },

  /* boolean isContainerOpen(in long index); */
  isContainerOpen: function(index) { return false;},

  /* boolean isContainerEmpty(in long index); */
  isContainerEmpty: function(index) {
      if (this.debug) dump("treeView:isContainerEmpty("+index+")\n");
      return false; },

  /* boolean isSorted (); */
  isSorted: function() { return (this.mSortType > 0); },

  /* boolean canDrop (in long index, in long orientation); */
  canDrop: function(index, orientation) { return false; },

  /* void drop (in long row, in long orientation); */
  drop: function(row, orientation) { },

  /* long getParentIndex(in long rowIndex); */
  getParentIndex: function(rowIndex) {
    if (this.debug) {
          dump("treeView:getParentIndex("+rowIndex+")\n");
      }
      return -1; },

  /* boolean hasNextSibling(in long rowIndex, in long afterIndex); */
  hasNextSibling: function(rowIndex, afterIndex) {
    if (this.debug) {
          dump("treeView:hasNextSibling("+rowIndex+" ,"+afterIndex+")\n");
      }
    return (afterIndex < (this.mTotalRows - 1));
  },

  /* long getLevel(in long index); */
  getLevel: function(index) {
    if (this.debug) {
          dump("treeView:getLevel("+index+")\n");
      }
      return 0; },

  /* boolean isSeparator(in long index); */
  isSeparator: function(index) { return 0; },

  /* wstring getCellText(in long row, in wstring colID); */
  getCellText: function(row, colID) {
    return "";
  },

  /* void setTree(in nsITreeBoxObject tree); */
  setTree: function(tree) { this.mTree = tree; },

  /* void toggleOpenState(in long index); */
  toggleOpenState: function(index) { },

  /* void cycleHeader(in wstring colID, in nsIDOMElement elt); */
  cycleHeader: function(colID, elt) { },

  /* void selectionChanged(); */
  selectionChanged: function() {  },

  /* void cycleCell(in long row, in wstring colID); */
  cycleCell: function(row, colID) { },

  /* boolean isEditable(in long row, in wstring colID); */
  isEditable: function(row, colID) {  return false; },

  /* void setCellText(in long row, in wstring colID, in wstring value); */
  setCellText: function(row, colID, value) {},

  /* void performAction(in wstring action); */
  performAction: function(action) {
    if (this.debug) {
          dump("treeView:performAction("+action+")\n");
      }
  },

  /* void performActionOnRow(in wstring action, in long row); */
  performActionOnRow: function(action, row) {
    if (this.debug) {
          dump("treeView:performActionOnRow("+action+" ,"+row+")\n");
      }
  },

  /* void performActionOnCell(in wstring action, in long row, in wstring colID); */
  performActionOnCell: function(action, row, colID) {
    if (this.debug) {
          dump("treeView:performActionOnCell("+action+" ,"+row+", "+colID+")\n");
      }
  },

  /* AString getImageSrc(in long row, in wstring colID); */
  getImageSrc: function(row, colID) {}
};



/**
 * A flat tree implementation.
 * 
 * Sample Usage:

XUL:

    <tree id="sample_tree" flex="1">
        <treecols>
          <treecol id="sample_treecol_name" flex="1" label="Name"/>
          <splitter class="tree-splitter"/>
          <treecol id="sample_treecol_value" flex="1" label="Name"/>
        </treecols>
        <!-- Tree children are dynamically generated, from our own custom tree view -->
        <treechildren/>
    </tree>


JavaScript:

    function SampleTreeView(initial_rows) {
        if (!initial_rows) {
            // Default value then
            this._rows = [];
        } else {
            this._rows = initial_rows;
        }
    }
    // The following two lines ensure proper inheritance (see Flanagan, p. 144).
    SampleTreeView.prototype = new xtk.dataTreeView();
    SampleTreeView.prototype.constructor = SampleTreeView;

    // Override getCellText method for assigning the celltext
    SampleTreeView.prototype.getCellText = function(row, column) {
        // forRow is an item of the _rows array
        var forRow = this._rows[row];
        switch (column.id) {
            case 'sample_treecol_name':
                return forRow[0];
            case 'sample_treecol_value':
                return forRow[1];
        }
        return "(Unknown column: " + column.id + ")";
    };


    // Load the tree view and assign it to a tree element
    var sampleTreeView = new SampleTreeView();
    var sampleTree = document.getElementById("sample_tree");
    sampleTree.treeBoxObject.view = sampleTreeView;
 

    // SORTING:
    // Sorting capabilitilies are automatically included (string sorting by
    // default). These are all of the sort specific attributes:
    //   <treecol sortActive="true|false" />  - marks the default sort column
    //   <treecol sortDirection="ascending|descending|natural" />
    //   <treecol sortType="string" />   - String sorting (default when not specified)
    //   <treecol sortType="numeric" />  - Numerical sorting
    //   <treecol sortType="function:func_name" /> - Custom sort function:
    //      where "func_name" is a function in the SampleTreeView class. The
    //      signature looks like: "func_name(compare1, compare2)". Each
    //      compare argument is an object that contains these attributes:
    //          compare1.data      ->  data (string) return by getCellText.
    //          compare1.row       ->  the real underlying row object.
    //          compare1.oldindex  ->  original row index before the sort.
    //      See the "_doDataCompare" function below for an example.
    //
 */

xtk.dataTreeView = function dataTreeView(initial_rows) {
    if (!initial_rows) {
        // Default value then
        this._rows = [];
    } else {
        this._rows = initial_rows;
    }
    this._unfilteredRows = this._rows;
    this._debug = 0;
};

xtk.dataTreeView.SORT_DESCENDING = 0;
xtk.dataTreeView.SORT_ASCENDING = 1;

xtk.dataTreeView.prototype = {
  // The nsITreeView object for the tree view
    /* void QueryInterface(in nsIIDRef uuid,
       [iid_is(uuid),retval] out nsQIResult result); */
    QueryInterface: function(iid) {
        if (!iid.equals(Components.interfaces.nsITreeView) &&
            !iid.equals(Components.interfaces.nsISupports)) {
                throw Components.results.NS_ERROR_NO_INTERFACE;
            }
        return this;
    },

    // Necessary function the child class must override and implement
    getCellText : function(row, column) {
        return "(Child class must implement this)";
    },

    // Everything below here is just to satisfy the interface, override as
    // needed.
    get rowCount() { return this._rows.length; },
    tree : null,
    isSeparator : function(index) {return false;},
    setTree : function(out) { this.tree = out; },
    getRowProperties : function(row,prop) {},
    getColumnProperties : function(column,prop){},
    getCellProperties : function(row,column,properties) {},
    isContainer : function(row) {return false;},
    isContainerOpen: function(index) { return false;},
    isContainerEmpty: function(index) { return false; },
    getLevel: function(row) { return 0; },
    cycleCell: function(row, colId) {},
    selectionChanged : function() {},
    performAction : function(action) {},
    isSorted : function() {return false;},
    getImageSrc : function() {return null;},
    cycleHeader : function(col) {
        if (this.enableSorting) {
            this.sortByColumn(col.element);
        }
    },
    /* The three functions below are used for tree cell checkboxes */
    isEditable : function(row, column) {return false;},
    getCellValue : function(row, column) {},
    setCellValue : function(row, column, value) {},

    /* Own defined methods */

    get rows() { return this._rows },
    // Setter for the rows needs to do some additional work.
    set rows(theRows) { this.setTreeRows(theRows); },

    _setTreeRows : function(rows, doReSort /* false */) {
        if (this.tree) {
            // Clearing the selection
            this.selection.clearSelection();
            // Using rowCountChanged to notify rows were removed
            this.tree.rowCountChanged(0, -this._rows.length);
            this._rows = rows;
            // Using rowCountChanged to notify rows were added
            this.tree.rowCountChanged(0, this._rows.length);
            if (this.enableSorting && doReSort) {
                this.reSort();
            }
        } else {
            // No tree yet, just assign it.
            this._rows = rows;
        }
    },
    /*
     * Function for updating the tree rows, must be called to set what the
     * tree contains in order to then display tree information.
     * 
     * @param {Array} rows The array of items/rows for the tree.
     * @param {bool} doReSort Whether to sort the data after it's set.
     */
    setTreeRows : function(rows, doReSort /* false */) {
        this._unfilteredRows = rows;
        this._setTreeRows(rows, doReSort);
    },

    /* Sorting */
    enableSorting: true,
    _sortColumn : null,
    _sortDirection : -1,
    _sortCaseInsensitive : true,
    _reverseRowSortOrder: function(rows) {
        var newCurrentIndex = (rows.length - this.selection.currentIndex) - 1;
        this._setTreeRows(rows.reverse(), /* doReSort */ false);
        this.selection.currentIndex = newCurrentIndex;
        this.tree.ensureRowIsVisible(newCurrentIndex);
    },
    setSortDirection: function(column, newSortDirection) {
        // Remove old sort direction
        if (this._sortColumn && this._sortColumn != column) {
            this._sortColumn.removeAttribute("sortDirection");
        }

        // Update the sort direction on the sorted column.
        // Note: xtk sort values are opposite to the actual tree indicators.
        if (newSortDirection == xtk.dataTreeView.SORT_ASCENDING) {
            column.setAttribute("sortDirection", "descending");
        } else {
            column.setAttribute("sortDirection", "ascending");
        }
        this._sortColumn = column;
        this._sortDirection = newSortDirection;
    },
    clearSortIndicators : function() {
        var colElem;
        for (var i=0 ; i < this.tree.columns.count; i++) {
            colElem = this.tree.columns.getColumnAt(i).element;
            if (colElem.getAttribute("sortActive")) {
                colElem.removeAttribute("sortActive");
            }
            if (colElem.getAttribute("sortDirection")) {
                colElem.removeAttribute("sortDirection");
            }
        }
    },
    sortByColumn : function(col, sortDirection)
    {
        if (!col || typeof(sortDirection) == 'undefined') {
            // Get the settings from the treecolumns then.
            var colElem;
            var sortSetting;
            for (var i=0 ; i < this.tree.columns.count; i++) {
                colElem = this.tree.columns.getColumnAt(i).element;
                if (!col && colElem.getAttribute("sortActive")) {
                    col = colElem;
                }
                sortSetting = colElem.getAttribute("sortDirection");
                if (sortSetting == "ascending") {
                    sortDirection = xtk.dataTreeView.SORT_ASCENDING;
                    break;
                } else if (sortSetting == "descending") {
                    sortDirection = xtk.dataTreeView.SORT_DESCENDING;
                    break;
                }
            }
            // No sortDirection setting in the column headers, go ascending
            if (typeof(sortDirection) == 'undefined') {
                sortDirection = xtk.dataTreeView.SORT_ASCENDING;
            } else if (!col && colElem) {
                // No sortActive setting in the column header, but we do
                // have a sortDirection, take that column then!
                col = colElem;
            }
        }
        if (!col) {
            // No sortDirection or sortActive settings, choose the first column.
            col = this.tree.columns.getFirstColumn().element;
        }

        /* if it's the same as last sorted column, just reverse the order */
        if (this._sortColumn == col) {
            //dump("Just reversing sort order for existing column.\n");
            this._reverseRowSortOrder(this._rows);
            if (this._sortDirection == xtk.dataTreeView.SORT_ASCENDING) {
                this.setSortDirection(col, xtk.dataTreeView.SORT_DESCENDING);
            } else {
                this.setSortDirection(col, xtk.dataTreeView.SORT_ASCENDING);
            }
            return;
        }

        // Function to compare two row values, compare objects are:
        //  { "data":     Text to compare,
        //    "row":      The original row the text came from
        //    "oldindex": Old selected row index
        //  }
        function _doDataCompare(compare1, compare2)
        {
            if (compare1 && compare2) {
                if (compare1.data > compare2.data) {
                    return 1;
                } else if (compare1.data == compare2.data) {
                    // Keep the sort order as uniform as possible.
                    return compare1.oldindex - compare2.oldindex;
                }
            }
            return -1;
        };

        //dump("Sorting direction: " + this._sortDirection + "\n");
        //dump("Sorting by column: " + col.id + "\n");

        if (typeof(sortDirection) == 'undefined') {
            sortDirection = xtk.dataTreeView.SORT_ASCENDING;
        }

        // Get all the row data we need to compare with
        var unsorted_row_data = [];
        // Convert all fields to a string value
        var data;
        for (var i=0; i < this._rows.length; i++) {
            if (this._sortCaseInsensitive) {
                data = this.getCellText(i, col);
                unsorted_row_data[i] = { "data": data ? data.toLowerCase() : "",
                                         "row": this._rows[i],
                                         "oldindex": i };
            } else {
                unsorted_row_data[i] = { "data": data,
                                         "row": this._rows[i],
                                         "oldindex": i };
            }
        }

        // Sort the rows, using our own customized sorting function
        //dump("Beginning sort of " + unsorted_row_values.length + " rows...\n");
        var sortType = col.getAttribute("sortType");
        var sortTypeCaseInsenitive = sortType && sortType.toLowerCase();
        var sortFunction = _doDataCompare;
        if (sortTypeCaseInsenitive == "numeric") {
            for (var i=0; i < this._rows.length; i++) {
                unsorted_row_data[i].data = parseFloat(unsorted_row_data[i].data);
            }
        } else if (sortTypeCaseInsenitive.substring(0, 9)  == "function:") {
            var sortFunction = this[sortType.substring(9)];
            if (!sortFunction) {
                log.error("sortByColumn:: Function '" + sortType +
                          "' defined by the sortType attribute doesn't exist.");
                sortFunction = _doDataCompare;
            }
        }
        unsorted_row_data.sort(sortFunction);

        if (sortDirection == xtk.dataTreeView.SORT_DESCENDING) {
            // Reverse the sorted order
            unsorted_row_data.reverse();
        }

        // Dump sorted rows back into self._rows
        var newCurrentIndex = -1;
        var oldCurrentIndex = this.selection.currentIndex;
        var sorted_rows = [];
        for (var i=0; i < unsorted_row_data.length; i++) {
            sorted_rows.push(unsorted_row_data[i].row);
            // Keep track of the current row selected
            if (oldCurrentIndex == sorted_rows[i].oldindex) {
                newCurrentIndex = i;
            }
        }
        this._setTreeRows(sorted_rows, /* doReSort */ false);

        this.selection.currentIndex = newCurrentIndex;
        this.tree.ensureRowIsVisible(newCurrentIndex);
        this.setSortDirection(col, sortDirection);
    },
    reSort: function() {
        var sortcol = this._sortColumn;
        this._sortColumn = null;
        this.sortByColumn(sortcol);
    },
    sortAscending: function(column) {
        this.sortByColumn(column, xtk.dataTreeView.SORT_ASCENDING);
    },
    sortDescending: function(column) {
        this.sortByColumn(column, xtk.dataTreeView.SORT_DESCENDING);
    },

    /* filtering - case insentive matching against the text in any of the
                   visible columns/rows.
     */
    filter: function(text) {
        var filtered_rows = [];
        if (text) {
            text = text.toLowerCase();
            var rows = this._unfilteredRows;
            // Temporarily restore the original rows, this is required for the
            // getCellText call below.
            var original_rows = this._rows;
            this._rows = rows;
            try {
                var col;
                var visible_columns = [];
                for (var i=0 ; i < this.tree.columns.count; i++) {
                    col = this.tree.columns.getColumnAt(i);
                    if (col.element.getAttribute("visible") != "false") {
                        visible_columns.push(this.tree.columns.getColumnAt(i));
                    }
                }
                var words = text.split(" ");
                var word;
                var matched_word;
                var matched_all;
                for (var i=0; i < rows.length; i++) {
                    matched_all = true;
                    for (var j=0; j < words.length; j++) {
                        matched_word = false;
                        word = words[j];
                        if (!word)
                            continue;
                        for (var col_idx=0 ; col_idx < visible_columns.length; col_idx++) {
                            col = visible_columns[col_idx];
                            if (this.getCellText(i, col).toLowerCase().indexOf(word) != -1) {
                                matched_word = true;
                                break
                            }
                        }
                        if (!matched_word) {
                            matched_all = false;
                            break;
                        }
                    }
                    if (matched_all)
                        filtered_rows.push(rows[i]);
                }
            } finally {
                // Replace the rows as they were - otherwise the setTreeRows
                // call will not have the correct row count.
                this._rows = original_rows;
            }
        } else {
            filtered_rows = this._unfilteredRows;
        }

        // Call the private "_setTreeRows" method, as it does not update the
        // special "_unfilteredRows" property.
        this._setTreeRows(filtered_rows, true);
    }

};

// Alternative name.
xtk.flatTreeView = xtk.dataTreeView;



/**
 * A hierarchical tree implementation (where each row may contain child nodes).
 *
 * Each tree row must be an object that has the following properties:
 *   attribute isContainer {bool} - whether it can have child nodes
 *   attribute hasChildren {bool} - whether the container is empty or not
 *   method getChildren() {array} - retrieve the child row nodes (children must be objects that meet the same tree requirements)
 *   attribute state {int}        - tree flags, such as whether opened/closed (managed by the tree), should be 0 by default
 *   attribute level {int}        - the depth of the row (managed by the tree), should be 0 by default
 */

/**
 * Custom treeview for showing hierachical tree data.
 */
xtk.hierarchicalTreeView = function hierarchicalTreeView(initial_rows) {
        // Call the parent initializer.
    xtk.dataTreeView.apply(this, [initial_rows]);
    this._sortFunction = null;
    this._sortPropertyName = null;
};
xtk.hierarchicalTreeView.STATE_CLOSED = 0;
xtk.hierarchicalTreeView.STATE_OPENED = 1;
xtk.hierarchicalTreeView.prototype = new xtk.dataTreeView();
xtk.hierarchicalTreeView.prototype.contructor = xtk.hierarchicalTreeView;

xtk.hierarchicalTreeView.prototype.isContainer = function(row) { return this.rows[row].isContainer; };
xtk.hierarchicalTreeView.prototype.isContainerOpen = function(row) {return this.rows[row].state == xtk.hierarchicalTreeView.STATE_OPENED;};
xtk.hierarchicalTreeView.prototype.isContainerEmpty = function(row) {return !this.rows[row].hasChildren;};
xtk.hierarchicalTreeView.prototype.getLevel = function(row) {return this.rows[row].level;};
xtk.hierarchicalTreeView.prototype.getParentIndex = function(row) {
    var level = this._rows[row].level;
    row--;
    while (row >= 0 && this._rows[row].level >= level) {
        row--;
    }
    return row;
};
xtk.hierarchicalTreeView.prototype.hasNextSibling = function(row, afterIndex) {
    var level = this._rows[row].level;
    row = afterIndex+1;
    var end = this._rows.length;
    while (row < end) {
        if (this._rows[row].level < level)
            return false;
        elif (this._rows[row].level == level)
            return true;
        row++;
    }
    return false;
};

xtk.hierarchicalTreeView.prototype._expand_and_sort_child_rows = function(rowItem, sortPropertyName, sortFunction, sortDir) {
    var rows = [];
    var child;
    var children = rowItem.getChildren();
    children = this._sort_rows_of_same_depth(children, this._sortPropertyName,
                                             this._sortFunction, this._sortDirection);
    var child_level = rowItem.level + 1;
    for (var i=0; i < children.length; i++) {
        child = children[i];
        child.level = child_level;
        rows.push(child);
        if (child.state == xtk.hierarchicalTreeView.STATE_OPENED && child.hasChildren) {
            rows = rows.concat(this._expand_and_sort_child_rows(child, sortPropertyName, sortFunction, sortDir));
        }
    }
    return rows;
};

/**
 * Sort sibling rows. This should be overridden by implementations that wish to
 * implement useful sorting.
 * 
 * @param   {Array of rows} children  The row data to sort; see the hierarchicalTreeView constructor for a description.
 * @param   {String} sortPropertyName The name of the property to sort by
 * @param   {Function} sortFunction   The function callback for sorting
 * @param   {Number} sortDir          The directory to sort in; may be either xtk.dataTreeView.SORT_DESCENDING or xtk.dataTreeView.SORT_ASCENDING
 * 
 * @returns {Array of rows} The sorted rows
 */
xtk.hierarchicalTreeView.prototype._sort_rows_of_same_depth = function(children, sortPropertyName, sortFunction, sortDir) {
    return Array.slice(children);
};

xtk.hierarchicalTreeView.prototype.toggleOpenState = function(row) {
    var item = this._rows[row];
    if (!item.hasChildren) return;
    var old_row_length = this._rows.length;
    var new_rows;

    if (item.state == xtk.hierarchicalTreeView.STATE_CLOSED) {
        var children = this._expand_and_sort_child_rows(item, this._sortPropertyName, this._sortFunction, this._sortDirection);
        new_rows = this._rows.slice(0, row+1);
        new_rows = new_rows.concat(children);
        new_rows = new_rows.concat(this._rows.slice(row+1));
        item.state = xtk.hierarchicalTreeView.STATE_OPENED;

    } else {
        var level = this._rows[row].level;
        var r = row+1;
        var end = this._rows.length;
        while (r < end && this._rows[r].level > level) {
            if (this._rows[r].level <= level)
                break;
            r++;
        }
        new_rows = this._rows.slice(0, row+1);
        new_rows = new_rows.concat(this._rows.slice(r));
        item.state = xtk.hierarchicalTreeView.STATE_CLOSED;
    }

    var num_rows_changed = new_rows.length - this._rows.length;
    this._rows = new_rows;
    // Using rowCountChanged to notify rows were added
    this.tree.rowCountChanged(row+1, num_rows_changed);
    this.tree.invalidateRow(row); // To redraw the twisty.
};
